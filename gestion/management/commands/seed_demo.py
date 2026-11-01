from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from gestion.models import (
    Categorie,
    Client,
    CommandeAchat,
    Fournisseur,
    LigneAchat,
    LotStock,
    Medicament,
    Utilisateur,
)


COMPTES = [
    ("admin", "admin123", "ADMIN", "Admin", "PharmaGest"),
    ("pharmacien", "pharma123", "PHARMACIEN", "Naina", "Rakoto"),
    ("gestionnaire", "gest123", "GESTIONNAIRE", "Fara", "Rabe"),
    ("caissier", "caisse123", "CAISSIER", "Tahina", "Randria"),
    ("responsable", "resp123", "RESPONSABLE", "Lova", "Rasoa"),
]


class Command(BaseCommand):
    help = "Crée des données de démonstration pour PharmaGest."

    def handle(self, *args, **options):
        aujourd_hui = timezone.localdate()

        for identifiant, mot_de_passe, role, prenom, nom in COMPTES:
            utilisateur, cree = Utilisateur.objects.get_or_create(
                username=identifiant,
                defaults={
                    "first_name": prenom,
                    "last_name": nom,
                    "role": role,
                    "email": f"{identifiant}@pharmagest.mg",
                    "is_staff": role == "ADMIN",
                    "is_superuser": role == "ADMIN",
                },
            )
            if cree:
                utilisateur.set_password(mot_de_passe)
                utilisateur.save(update_fields=["password"])
            utilisateur.groups.set(Group.objects.filter(name=f"Role {role}"))

        categories = {}
        for nom, description in [
            ("Antalgiques", "Douleur et fièvre"),
            ("Antibiotiques", "Traitements anti-infectieux"),
            ("Antipaludiques", "Prévention et traitement du paludisme"),
            ("Vitamines", "Compléments et vitamines"),
            ("Hygiène", "Soins et hygiène quotidienne"),
        ]:
            categories[nom], _ = Categorie.objects.get_or_create(
                nom=nom, defaults={"description": description}
            )

        fournisseurs = {}
        for raison, telephone, email in [
            ("Somapharm", "+261 20 22 000 01", "contact@somapharm.mg"),
            ("Opham", "+261 20 22 000 02", "contact@opham.mg"),
            ("Pmi Distribution", "+261 20 22 000 03", "contact@pmi.mg"),
        ]:
            fournisseurs[raison], _ = Fournisseur.objects.get_or_create(
                raison_sociale=raison,
                defaults={
                    "telephone": telephone,
                    "email": email,
                    "adresse": "Antananarivo, Madagascar",
                },
            )

        clients = []
        for nom, telephone in [
            ("Rasoanaivo Hery", "+261 34 11 000 01"),
            ("Rakotondrabe Soa", "+261 34 11 000 02"),
            ("Andrianina Fanja", "+261 34 11 000 03"),
        ]:
            client, _ = Client.objects.get_or_create(
                nom=nom, defaults={"telephone": telephone}
            )
            clients.append(client)

        produits = [
            (
                "Doliprane",
                "Paracétamol",
                "Antalgiques",
                "Comprimé",
                "500 mg",
                "Sanofi",
                "3000.00",
                "4500.00",
                20,
            ),
            (
                "Amoxil",
                "Amoxicilline",
                "Antibiotiques",
                "Gélule",
                "500 mg",
                "GSK",
                "6000.00",
                "8500.00",
                15,
            ),
            (
                "Coartem",
                "Artéméther/Luméfantrine",
                "Antipaludiques",
                "Comprimé",
                "20/120 mg",
                "Novartis",
                "9000.00",
                "12500.00",
                10,
            ),
            (
                "Vitamine C",
                "Acide ascorbique",
                "Vitamines",
                "Comprimé effervescent",
                "1000 mg",
                "Laprophan",
                "4000.00",
                "6000.00",
                12,
            ),
            (
                "Bétadine",
                "Povidone iodée",
                "Hygiène",
                "Solution",
                "10 %",
                "Meda",
                "7000.00",
                "10000.00",
                8,
            ),
        ]

        medicaments = {}
        for index, (
            nom,
            generique,
            categorie,
            forme,
            dosage,
            laboratoire,
            prix_achat,
            prix_vente,
            seuil,
        ) in enumerate(produits, start=1):
            medicament, _ = Medicament.objects.get_or_create(
                nom_commercial=nom,
                defaults={
                    "denomination_generique": generique,
                    "categorie": categories[categorie],
                    "forme_pharmaceutique": forme,
                    "dosage": dosage,
                    "laboratoire": laboratoire,
                    "code_barres": f"MG{index:06d}",
                    "prix_achat": Decimal(prix_achat),
                    "prix_vente": Decimal(prix_vente),
                    "seuil_alerte": seuil,
                },
            )
            medicaments[nom] = medicament

        lots = [
            ("Doliprane", "LOT-DOL-001", 90, 120, aujourd_hui + timedelta(days=400)),
            ("Doliprane", "LOT-DOL-002", 25, 60, aujourd_hui + timedelta(days=18)),
            ("Amoxil", "LOT-AMX-001", 45, 80, aujourd_hui + timedelta(days=220)),
            ("Coartem", "LOT-COA-001", 8, 40, aujourd_hui + timedelta(days=150)),
            ("Vitamine C", "LOT-VIT-001", 60, 100, aujourd_hui + timedelta(days=300)),
            ("Bétadine", "LOT-BET-001", 30, 50, aujourd_hui + timedelta(days=25)),
            ("Doliprane", "LOT-DOL-OLD", 12, 40, aujourd_hui - timedelta(days=10)),
        ]
        for nom, numero, quantite, quantite_recue, peremption in lots:
            LotStock.objects.get_or_create(
                medicament=medicaments[nom],
                numero_lot=numero,
                date_peremption=peremption,
                defaults={
                    "quantite": quantite,
                    "quantite_recue": quantite_recue,
                    "date_reception": aujourd_hui - timedelta(days=30),
                },
            )

        pharmacien = Utilisateur.objects.get(username="pharmacien")
        commande, cree = CommandeAchat.objects.get_or_create(
            fournisseur=fournisseurs["Somapharm"],
            statut=CommandeAchat.Statut.BROUILLON,
            notes="Commande de démonstration",
            defaults={"utilisateur": pharmacien},
        )
        if cree:
            LigneAchat.objects.create(
                commande=commande,
                medicament=medicaments["Doliprane"],
                quantite_commandee=100,
                prix_achat=Decimal("3000.00"),
            )
            LigneAchat.objects.create(
                commande=commande,
                medicament=medicaments["Amoxil"],
                quantite_commandee=50,
                prix_achat=Decimal("6000.00"),
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Données de démonstration prêtes. "
                "Comptes : admin/admin123, pharmacien/pharma123, "
                "gestionnaire/gest123, caissier/caisse123, responsable/resp123."
            )
        )
