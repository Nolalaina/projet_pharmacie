from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    Categorie,
    Client,
    CommandeAchat,
    Fournisseur,
    LigneAchat,
    LigneReception,
    LigneRetour,
    LigneVente,
    LotStock,
    Medicament,
    MouvementStock,
    Paiement,
    ReceptionAchat,
    RetourVente,
    Utilisateur,
    Vente,
)


class DonneesTestMixin:
    def creer_donnees(self):
        self.aujourd_hui = timezone.localdate()
        self.categorie = Categorie.objects.create(nom="Antalgiques")
        self.medicament = Medicament.objects.create(
            nom_commercial="Doliprane",
            categorie=self.categorie,
            dosage="500 mg",
            prix_achat=Decimal("3000.00"),
            prix_vente=Decimal("4500.00"),
            seuil_alerte=5,
        )
        self.lot = LotStock.objects.create(
            medicament=self.medicament,
            numero_lot="LOT-001",
            date_peremption=self.aujourd_hui + timedelta(days=365),
            quantite=50,
            quantite_recue=50,
        )
        self.fournisseur = Fournisseur.objects.create(raison_sociale="Somapharm")
        self.client_pharmacie = Client.objects.create(nom="Client Test")
        self.admin = Utilisateur.objects.create_user(
            username="admin",
            password="motdepasse123",
            role=Utilisateur.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.pharmacien = Utilisateur.objects.create_user(
            username="pharmacien",
            password="motdepasse123",
            role=Utilisateur.Role.PHARMACIEN,
        )
        self.caissier = Utilisateur.objects.create_user(
            username="caissier",
            password="motdepasse123",
            role=Utilisateur.Role.CAISSIER,
        )
        self.responsable = Utilisateur.objects.create_user(
            username="responsable",
            password="motdepasse123",
            role=Utilisateur.Role.RESPONSABLE,
        )

    def creer_vente(self, quantite=2):
        vente = Vente.objects.create(client=self.client_pharmacie, utilisateur=self.caissier)
        LigneVente.objects.create(
            vente=vente,
            medicament=self.medicament,
            lot=self.lot,
            quantite=quantite,
            prix_unitaire=self.medicament.prix_vente,
        )
        Paiement.objects.create(
            vente=vente,
            montant=vente.total,
            mode=Paiement.Mode.ESPECES,
            statut=Paiement.Statut.CONFIRME,
            confirme_par=self.caissier,
            date_confirmation=timezone.now(),
        )
        vente.valider(self.caissier)
        return vente

    def creer_commande(self, quantite=20):
        commande = CommandeAchat.objects.create(
            fournisseur=self.fournisseur, utilisateur=self.pharmacien
        )
        ligne = LigneAchat.objects.create(
            commande=commande,
            medicament=self.medicament,
            quantite_commandee=quantite,
            prix_achat=self.medicament.prix_achat,
        )
        commande.valider()
        return commande, ligne


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class StockEtVenteTests(DonneesTestMixin, TestCase):
    def setUp(self):
        self.creer_donnees()

    def test_stock_total_et_vendable(self):
        self.assertEqual(self.medicament.stock_total, 50)
        self.assertEqual(self.medicament.stock_vendable, 50)
        self.lot.bloque = True
        self.lot.save(update_fields=["bloque"])
        self.assertEqual(self.medicament.stock_total, 50)
        self.assertEqual(self.medicament.stock_vendable, 0)

    def test_lot_perime_non_vendable(self):
        self.lot.date_peremption = self.aujourd_hui - timedelta(days=1)
        self.lot.save(update_fields=["date_peremption"])
        self.assertTrue(self.lot.perime)
        self.assertEqual(self.medicament.stock_vendable, 0)

    def test_validation_vente_decremente_le_stock(self):
        vente = self.creer_vente(quantite=3)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 47)
        self.assertEqual(vente.statut, Vente.Statut.VALIDEE)
        self.assertTrue(
            MouvementStock.objects.filter(
                lot=self.lot, type=MouvementStock.Type.SORTIE, quantite=-3
            ).exists()
        )

    def test_vente_non_validable_deux_fois(self):
        vente = self.creer_vente()
        with self.assertRaises(ValidationError):
            vente.valider(self.caissier)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 48)

    def test_vente_refusee_si_stock_insuffisant(self):
        vente = Vente.objects.create(utilisateur=self.caissier)
        LigneVente.objects.create(
            vente=vente,
            medicament=self.medicament,
            lot=self.lot,
            quantite=100,
            prix_unitaire=self.medicament.prix_vente,
        )
        with self.assertRaises(ValidationError):
            vente.valider(self.caissier)

    def test_vente_refusee_si_lot_perime(self):
        self.lot.date_peremption = self.aujourd_hui - timedelta(days=1)
        self.lot.save(update_fields=["date_peremption"])
        vente = Vente.objects.create(utilisateur=self.caissier)
        LigneVente.objects.create(
            vente=vente,
            medicament=self.medicament,
            lot=self.lot,
            quantite=1,
            prix_unitaire=self.medicament.prix_vente,
        )
        with self.assertRaises(ValidationError):
            vente.valider(self.caissier)

    def test_annulation_vente_reintegre_le_stock(self):
        vente = self.creer_vente(quantite=4)
        vente.annuler("Erreur de saisie", self.pharmacien)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 50)
        self.assertEqual(vente.statut, Vente.Statut.ANNULEE)

    def test_retour_avec_remise_en_stock(self):
        vente = self.creer_vente(quantite=5)
        retour = RetourVente.objects.create(
            vente=vente,
            utilisateur=self.caissier,
            motif="Retour client",
            remis_en_stock=True,
            remboursement=Decimal("4500.00"),
        )
        ligne_vente = vente.lignes.first()
        LigneRetour.objects.create(
            retour=retour, ligne_vente=ligne_vente, quantite=2
        )
        retour.traiter(self.caissier)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 47)
        self.assertTrue(retour.traite)

    def test_retour_superieur_a_la_quantite_vendue_refuse(self):
        vente = self.creer_vente(quantite=2)
        retour = RetourVente.objects.create(
            vente=vente, utilisateur=self.caissier, motif="Test"
        )
        LigneRetour.objects.create(
            retour=retour, ligne_vente=vente.lignes.first(), quantite=3
        )
        with self.assertRaises(ValidationError):
            retour.traiter(self.caissier)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ReceptionTests(DonneesTestMixin, TestCase):
    def setUp(self):
        self.creer_donnees()

    def test_reception_validee_augmente_le_stock(self):
        commande, ligne = self.creer_commande(quantite=20)
        reception = ReceptionAchat.objects.create(
            commande=commande, utilisateur=self.pharmacien
        )
        LigneReception.objects.create(
            reception=reception,
            ligne_achat=ligne,
            quantite=20,
            numero_lot="LOT-NEW",
            date_peremption=self.aujourd_hui + timedelta(days=300),
        )
        reception.valider(self.pharmacien)
        lot = LotStock.objects.get(numero_lot="LOT-NEW")
        self.assertEqual(lot.quantite, 20)
        commande.refresh_from_db()
        self.assertEqual(commande.statut, CommandeAchat.Statut.RECEPTIONNEE)

    def test_reception_non_validable_deux_fois(self):
        commande, ligne = self.creer_commande(quantite=10)
        reception = ReceptionAchat.objects.create(commande=commande)
        LigneReception.objects.create(
            reception=reception,
            ligne_achat=ligne,
            quantite=10,
            numero_lot="LOT-DOUBLE",
            date_peremption=self.aujourd_hui + timedelta(days=100),
        )
        reception.valider()
        with self.assertRaises(ValidationError):
            reception.valider()

    def test_reception_partielle_met_a_jour_le_statut(self):
        commande, ligne = self.creer_commande(quantite=10)
        reception = ReceptionAchat.objects.create(commande=commande)
        LigneReception.objects.create(
            reception=reception,
            ligne_achat=ligne,
            quantite=4,
            numero_lot="LOT-PARTIEL",
            date_peremption=self.aujourd_hui + timedelta(days=100),
        )
        reception.valider()
        commande.refresh_from_db()
        self.assertEqual(commande.statut, CommandeAchat.Statut.PARTIELLE)
        self.assertEqual(commande.reste_a_recevoir, 6)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class VuesEtPermissionsTests(DonneesTestMixin, TestCase):
    def setUp(self):
        self.creer_donnees()

    def test_page_connexion(self):
        reponse = self.client.get(reverse("gestion:connexion"))
        self.assertEqual(reponse.status_code, 200)
        contenu = reponse.content.decode()
        self.assertIn('autocomplete="username"', contenu)
        self.assertIn('autocomplete="current-password"', contenu)
        self.assertIn("favicon.svg", contenu)

    def test_connexion_utilisateur(self):
        reponse = self.client.post(
            reverse("gestion:connexion"),
            {"username": "pharmacien", "password": "motdepasse123"},
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("gestion:tableau_bord"))
        self.assertEqual(
            int(self.client.session["_auth_user_id"]), self.pharmacien.pk
        )

    def test_connexion_obligatoire(self):
        reponse = self.client.get(reverse("gestion:tableau_bord"))
        self.assertEqual(reponse.status_code, 302)
        self.assertIn(reverse("gestion:connexion"), reponse.url)

    def test_caissier_ne_peut_pas_gerer_les_utilisateurs(self):
        self.client.force_login(self.caissier)
        reponse = self.client.get(reverse("gestion:utilisateur_liste"))
        self.assertEqual(reponse.status_code, 403)

    def test_caissier_peut_acceder_a_la_caisse(self):
        self.client.force_login(self.caissier)
        self.assertEqual(
            self.client.get(reverse("gestion:caisse")).status_code, 200
        )

    def test_caisse_expose_les_donnees_de_calcul(self):
        self.client.force_login(self.caissier)
        reponse = self.client.get(reverse("gestion:caisse"))
        contenu = reponse.content.decode()
        self.assertIn('data-prix="', contenu)
        self.assertIn('data-stock="50"', contenu)
        self.assertIn('data-code="', contenu)
        self.assertIn("data-scan-code", contenu)

    def test_caisse_enregistre_une_vente(self):
        self.client.force_login(self.caissier)
        reponse = self.client.post(
            reverse("gestion:caisse"),
            {
                "client": self.client_pharmacie.pk,
                "remise": "0.00",
                "mode_paiement": Paiement.Mode.ESPECES,
                "reference_paiement": "",
                "paiement_confirme": "",
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-lot": self.lot.pk,
                "form-0-quantite": "2",
            },
        )
        self.assertEqual(reponse.status_code, 302)
        vente = Vente.objects.get()
        self.assertEqual(vente.statut, Vente.Statut.VALIDEE)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 48)

    def test_caisse_refuse_une_quantite_superieure_au_stock(self):
        self.client.force_login(self.caissier)
        reponse = self.client.post(
            reverse("gestion:caisse"),
            {
                "client": "",
                "remise": "0.00",
                "mode_paiement": Paiement.Mode.ESPECES,
                "reference_paiement": "",
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-lot": self.lot.pk,
                "form-0-quantite": "99",
            },
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(Vente.objects.exists())
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 50)

    def test_creation_commande_via_vue(self):
        self.client.force_login(self.pharmacien)
        reponse = self.client.post(
            reverse("gestion:commande_ajouter"),
            {
                "fournisseur": self.fournisseur.pk,
                "notes": "Commande test",
                "lignes-TOTAL_FORMS": "1",
                "lignes-INITIAL_FORMS": "0",
                "lignes-MIN_NUM_FORMS": "0",
                "lignes-MAX_NUM_FORMS": "1000",
                "lignes-0-medicament": self.medicament.pk,
                "lignes-0-quantite_commandee": "12",
                "lignes-0-prix_achat": "3000.00",
            },
        )
        self.assertEqual(reponse.status_code, 302)
        commande = CommandeAchat.objects.get(notes="Commande test")
        self.assertEqual(commande.statut, CommandeAchat.Statut.BROUILLON)
        self.assertEqual(commande.lignes.count(), 1)

    def test_reception_via_vue_met_a_jour_le_stock(self):
        commande, ligne = self.creer_commande(quantite=10)
        self.client.force_login(self.pharmacien)
        peremption = (self.aujourd_hui + timedelta(days=200)).isoformat()
        reponse = self.client.post(
            reverse("gestion:commande_receptionner", args=[commande.pk]),
            {
                "date_reception": self.aujourd_hui.isoformat(),
                "notes": "Livraison test",
                f"quantite_{ligne.pk}": "10",
                f"lot_{ligne.pk}": "LOT-VUE",
                f"peremption_{ligne.pk}": peremption,
            },
        )
        self.assertEqual(reponse.status_code, 302)
        lot = LotStock.objects.get(numero_lot="LOT-VUE")
        self.assertEqual(lot.quantite, 10)
        commande.refresh_from_db()
        self.assertEqual(commande.statut, CommandeAchat.Statut.RECEPTIONNEE)

    def test_inventaire_cree_un_mouvement_de_correction(self):
        self.client.force_login(self.pharmacien)
        reponse = self.client.post(
            reverse("gestion:inventaire"),
            {
                "lot": self.lot.pk,
                "nouvelle_quantite": "40",
                "motif": "Comptage physique",
            },
        )
        self.assertEqual(reponse.status_code, 302)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 40)
        self.assertTrue(
            MouvementStock.objects.filter(
                lot=self.lot,
                type=MouvementStock.Type.CORRECTION,
                quantite=-10,
            ).exists()
        )

@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class RenduDesPagesTests(DonneesTestMixin, TestCase):
    def setUp(self):
        self.creer_donnees()
        self.commande, self.ligne_achat = self.creer_commande(quantite=20)
        self.commande_brouillon = CommandeAchat.objects.create(
            fournisseur=self.fournisseur, utilisateur=self.pharmacien
        )
        LigneAchat.objects.create(
            commande=self.commande_brouillon,
            medicament=self.medicament,
            quantite_commandee=5,
            prix_achat=self.medicament.prix_achat,
        )
        self.reception = ReceptionAchat.objects.create(
            commande=self.commande, utilisateur=self.pharmacien
        )
        LigneReception.objects.create(
            reception=self.reception,
            ligne_achat=self.ligne_achat,
            quantite=10,
            numero_lot="LOT-RECU",
            date_peremption=self.aujourd_hui + timedelta(days=280),
        )
        self.reception.valider(self.pharmacien)
        self.vente = self.creer_vente(quantite=2)
        self.client.force_login(self.admin)

    def test_pages_principales(self):
        urls = [
            reverse("gestion:tableau_bord"),
            reverse("gestion:medicament_liste"),
            reverse("gestion:medicament_ajouter"),
            reverse("gestion:medicament_detail", args=[self.medicament.pk]),
            reverse("gestion:medicament_modifier", args=[self.medicament.pk]),
            reverse("gestion:medicament_supprimer", args=[self.medicament.pk]),
            reverse("gestion:categorie_liste"),
            reverse("gestion:categorie_ajouter"),
            reverse("gestion:categorie_modifier", args=[self.categorie.pk]),
            reverse("gestion:categorie_supprimer", args=[self.categorie.pk]),
            reverse("gestion:fournisseur_liste"),
            reverse("gestion:fournisseur_detail", args=[self.fournisseur.pk]),
            reverse("gestion:fournisseur_modifier", args=[self.fournisseur.pk]),
            reverse("gestion:client_liste"),
            reverse("gestion:client_detail", args=[self.client_pharmacie.pk]),
            reverse("gestion:client_modifier", args=[self.client_pharmacie.pk]),
            reverse("gestion:client_supprimer", args=[self.client_pharmacie.pk]),
            reverse("gestion:commande_liste"),
            reverse("gestion:commande_ajouter"),
            reverse("gestion:commande_detail", args=[self.commande.pk]),
            reverse(
                "gestion:commande_modifier", args=[self.commande_brouillon.pk]
            ),
            reverse("gestion:reception_liste"),
            reverse("gestion:reception_detail", args=[self.reception.pk]),
            reverse("gestion:stock_liste"),
            reverse("gestion:mouvement_liste"),
            reverse("gestion:alertes"),
            reverse("gestion:inventaire"),
            reverse("gestion:vente_liste"),
            reverse("gestion:caisse"),
            reverse("gestion:vente_detail", args=[self.vente.pk]),
            reverse("gestion:vente_annuler", args=[self.vente.pk]),
            reverse("gestion:retour_vente", args=[self.vente.pk]),
            reverse("gestion:utilisateur_liste"),
            reverse("gestion:utilisateur_ajouter"),
            reverse("gestion:utilisateur_modifier", args=[self.caissier.pk]),
            reverse(
                "gestion:utilisateur_mot_de_passe", args=[self.caissier.pk]
            ),
            reverse("gestion:journal_liste"),
            reverse("gestion:rapports"),
            reverse("gestion:mot_de_passe"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_exports_pdf(self):
        urls = [
            reverse("gestion:recu_pdf", args=[self.vente.pk]),
            reverse("gestion:facture_pdf", args=[self.vente.pk]),
            reverse("gestion:bon_commande_pdf", args=[self.commande.pk]),
            reverse("gestion:bon_reception_pdf", args=[self.reception.pk]),
            reverse("gestion:rapport_stock_pdf"),
            reverse("gestion:rapport_ventes_pdf"),
            reverse("gestion:rapport_achats_pdf"),
            reverse("gestion:rapport_peremptions_pdf"),
        ]
        for url in urls:
            with self.subTest(url=url):
                reponse = self.client.get(url)
                self.assertEqual(reponse.status_code, 200, url)
                self.assertEqual(reponse["Content-Type"], "application/pdf")
