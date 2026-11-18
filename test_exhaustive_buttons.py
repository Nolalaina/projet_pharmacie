import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append("testserver")

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from gestion.models import (
    Medicament, Categorie, Fournisseur, LotStock, Vente, LigneVente,
    CommandeAchat, LigneAchat, Client as ClientModel,
    Utilisateur, MouvementStock, Paiement
)
from datetime import date, timedelta
from decimal import Decimal

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.filter(role=Utilisateur.Role.PHARMACIEN).first()

client = Client()
client.force_login(admin_user)

results = []

def record(category, button_name, method, url, status_code, passed, details=""):
    results.append({
        "category": category,
        "button": button_name,
        "method": method,
        "url": url,
        "status": status_code,
        "passed": passed,
        "details": details
    })
    mark = "✅ PASS" if passed else "❌ FAIL"
    print(f"[{mark}] [{category}] '{button_name}' ({method} {url}) -> {status_code} | {details}")

print("=======================================================================")
print(f"LANCEMENT DU TEST EXHAUSTIF DES BOUTONS (Utilisateur: {admin_user.username})")
print("=======================================================================\n")

# 1. NAVIGATION & DASHBOARD
resp = client.get(reverse("gestion:tableau_bord"))
record("Tableau de bord", "Accès Dashboard", "GET", reverse("gestion:tableau_bord"), resp.status_code, resp.status_code == 200)

for p in ["aujourdhui", "semaine", "mois", "annee"]:
    resp = client.get(reverse("gestion:tableau_bord") + f"?periode={p}")
    record("Tableau de bord", f"Bouton filtre période: {p}", "GET", f"?periode={p}", resp.status_code, resp.status_code == 200)

# 2. MÉDICAMENTS
resp = client.get(reverse("gestion:medicament_liste"))
record("Médicaments", "Bouton Liste Médicaments", "GET", reverse("gestion:medicament_liste"), resp.status_code, resp.status_code == 200)

resp = client.get(reverse("gestion:medicament_ajouter"))
record("Médicaments", "Bouton + Nouveau Médicament (page)", "GET", reverse("gestion:medicament_ajouter"), resp.status_code, resp.status_code == 200)

cat = Categorie.objects.first()
fourn = Fournisseur.objects.first()
post_data = {
    "nom_commercial": "TestMed Automate",
    "denomination_generique": "Test DCI",
    "categorie": cat.pk,
    "forme_pharmaceutique": "Comprimé",
    "dosage": "500 mg",
    "laboratoire": "Laboratoire Test",
    "code_barres": "999888777666",
    "prix_achat": "1500.00",
    "prix_vente": "2200.00",
    "seuil_alerte": 10,
    "statut": "ACTIF",
}
resp = client.post(reverse("gestion:medicament_ajouter"), post_data)
new_med = Medicament.objects.filter(code_barres="999888777666").first()
passed = resp.status_code in [302, 200] and new_med is not None
record("Médicaments", "Bouton Enregistrer Nouveau Médicament", "POST", reverse("gestion:medicament_ajouter"), resp.status_code, passed, f"ID: {getattr(new_med, 'pk', None)}")

if new_med:
    resp = client.get(reverse("gestion:medicament_detail", args=[new_med.pk]))
    record("Médicaments", "Bouton Fiche Médicament", "GET", reverse("gestion:medicament_detail", args=[new_med.pk]), resp.status_code, resp.status_code == 200)

    # Modifier
    mod_data = post_data.copy()
    mod_data["nom_commercial"] = "TestMed Automate MODIFIE"
    resp = client.post(reverse("gestion:medicament_modifier", args=[new_med.pk]), mod_data)
    new_med.refresh_from_db()
    passed = resp.status_code in [302, 200] and new_med.nom_commercial == "TestMed Automate MODIFIE"
    record("Médicaments", "Bouton Modifier Médicament", "POST", reverse("gestion:medicament_modifier", args=[new_med.pk]), resp.status_code, passed)

    # Supprimer
    resp = client.post(reverse("gestion:medicament_supprimer", args=[new_med.pk]))
    passed = resp.status_code in [302, 200] and not Medicament.objects.filter(pk=new_med.pk).exists()
    record("Médicaments", "Bouton Supprimer Médicament", "POST", reverse("gestion:medicament_supprimer", args=[new_med.pk]), resp.status_code, passed)

# 3. CATÉGORIES
resp = client.get(reverse("gestion:categorie_liste"))
record("Catégories", "Bouton Liste Catégories", "GET", reverse("gestion:categorie_liste"), resp.status_code, resp.status_code == 200)

resp = client.get(reverse("gestion:categorie_ajouter"))
record("Catégories", "Bouton + Nouvelle Catégorie (page)", "GET", reverse("gestion:categorie_ajouter"), resp.status_code, resp.status_code == 200)

cat_post = {"nom": "Test Catégorie Bouton", "description": "Description test"}
resp = client.post(reverse("gestion:categorie_ajouter"), cat_post)
test_cat = Categorie.objects.filter(nom="Test Catégorie Bouton").first()
passed = resp.status_code in [302, 200] and test_cat is not None
record("Catégories", "Bouton Enregistrer Catégorie", "POST", reverse("gestion:categorie_ajouter"), resp.status_code, passed)
if test_cat:
    resp = client.post(reverse("gestion:categorie_supprimer", args=[test_cat.pk]))
    record("Catégories", "Bouton Supprimer Catégorie", "POST", reverse("gestion:categorie_supprimer", args=[test_cat.pk]), resp.status_code, resp.status_code in [302, 200])

# 4. STOCK & LOTS
resp = client.get(reverse("gestion:stock_liste"))
record("Stock & Lots", "Bouton Vue Stock", "GET", reverse("gestion:stock_liste"), resp.status_code, resp.status_code == 200)

# Filtres stock
for filtre in ["?etat=perime", "?etat=proche", "?etat=valide", "?statut_stock=disponible", "?statut_stock=faible"]:
    resp = client.get(reverse("gestion:stock_liste") + filtre)
    record("Stock & Lots", f"Bouton filtre: {filtre}", "GET", filtre, resp.status_code, resp.status_code == 200)

# Bouton Bloquer / Débloquer Lot
lot = LotStock.objects.first()
if lot:
    initial_bloque = lot.bloque
    resp = client.post(reverse("gestion:lot_basculer", args=[lot.pk]))
    lot.refresh_from_db()
    passed = resp.status_code in [302, 200] and lot.bloque != initial_bloque
    record("Stock & Lots", "Bouton Bloquer/Débloquer Lot", "POST", reverse("gestion:lot_basculer", args=[lot.pk]), resp.status_code, passed, f"bloque: {initial_bloque} -> {lot.bloque}")
    # restore
    client.post(reverse("gestion:lot_basculer", args=[lot.pk]))

# Inventaire physique (Ajustement stock)
resp = client.get(reverse("gestion:inventaire"))
record("Stock & Lots", "Bouton Inventaire Physique (page)", "GET", reverse("gestion:inventaire"), resp.status_code, resp.status_code == 200)

if lot:
    old_qty = lot.quantite
    new_qty = old_qty + 5
    ajust_data = {
        "lot": lot.pk,
        "nouvelle_quantite": new_qty,
        "motif": "Vérification automatisée des boutons",
    }
    resp = client.post(reverse("gestion:inventaire"), ajust_data)
    lot.refresh_from_db()
    passed = resp.status_code in [302, 200] and lot.quantite == new_qty
    record("Stock & Lots", "Bouton Valider Ajustement Inventaire", "POST", reverse("gestion:inventaire"), resp.status_code, passed, f"qte: {old_qty} -> {new_qty}")
    # revert
    lot.quantite = old_qty
    lot.save(update_fields=["quantite"])

# 5. CAISSE & VENTES
resp = client.get(reverse("gestion:caisse"))
record("Caisse", "Bouton Ouvrir la Caisse", "GET", reverse("gestion:caisse"), resp.status_code, resp.status_code == 200)

# API recherche code-barres / FEFO
med_sample = Medicament.objects.filter(lots__quantite__gt=0, lots__bloque=False, lots__date_peremption__gt=date.today()).first()
if med_sample:
    api_url = reverse("gestion:api_medicament") + f"?q={med_sample.code_barres or med_sample.nom_commercial}"
    resp = client.get(api_url)
    lots_found = resp.json().get("lots", [])
    passed = resp.status_code == 200 and len(lots_found) > 0
    record("Caisse", "Recherche AJAX / Scan Code-barres FEFO", "GET", api_url, resp.status_code, passed, f"{len(lots_found)} lot(s) éligible(s)")

# Encaisser une vente
valid_lot = LotStock.objects.filter(quantite__gte=2, bloque=False, date_peremption__gt=date.today()).first()
if valid_lot:
    client_obj = ClientModel.objects.first()
    vente_post = {
        "client": client_obj.pk if client_obj else "",
        "mode_paiement": "ESPECES",
        "remise": "0.00",
        "reference_paiement": "TEST-BOUTON-CAISSE",
        "paiement_confirme": "on",
        "form-TOTAL_FORMS": "1",
        "form-INITIAL_FORMS": "0",
        "form-MIN_NUM_FORMS": "1",
        "form-MAX_NUM_FORMS": "100",
        "form-0-lot": valid_lot.pk,
        "form-0-quantite": "1",
    }
    ventes_count_before = Vente.objects.count()
    resp = client.post(reverse("gestion:caisse"), vente_post)
    latest_vente = Vente.objects.order_by("-date_vente").first()
    passed = resp.status_code in [302, 200] and Vente.objects.count() > ventes_count_before
    record("Caisse", "Bouton Encaisser la Vente", "POST", reverse("gestion:caisse"), resp.status_code, passed, f"Facture: {getattr(latest_vente, 'numero', None)}")

    if latest_vente:
        # Facture PDF
        pdf_url = reverse("gestion:facture_pdf", args=[latest_vente.pk])
        resp = client.get(pdf_url)
        passed = resp.status_code == 200 and resp.get("Content-Type") == "application/pdf"
        record("Ventes", "Bouton Télécharger Facture PDF", "GET", pdf_url, resp.status_code, passed, f"{len(resp.content)} octets")

        # Ticket reçu PDF
        recu_url = reverse("gestion:recu_pdf", args=[latest_vente.pk])
        resp = client.get(recu_url)
        passed = resp.status_code == 200 and resp.get("Content-Type") == "application/pdf"
        record("Ventes", "Bouton Imprimer Reçu Ticket PDF", "GET", recu_url, resp.status_code, passed, f"{len(resp.content)} octets")

# 6. FOURNISSEURS & ACHATS
resp = client.get(reverse("gestion:fournisseur_liste"))
record("Fournisseurs", "Bouton Liste Fournisseurs", "GET", reverse("gestion:fournisseur_liste"), resp.status_code, resp.status_code == 200)

resp = client.get(reverse("gestion:fournisseur_ajouter"))
record("Fournisseurs", "Bouton + Nouveau Fournisseur (page)", "GET", reverse("gestion:fournisseur_ajouter"), resp.status_code, resp.status_code == 200)

# Toggle fournisseur actif/inactif
if fourn:
    statut_before = fourn.statut
    resp = client.post(reverse("gestion:fournisseur_basculer", args=[fourn.pk]))
    fourn.refresh_from_db()
    passed = resp.status_code in [302, 200] and fourn.statut != statut_before
    record("Fournisseurs", "Bouton Activer/Désactiver Fournisseur", "POST", reverse("gestion:fournisseur_basculer", args=[fourn.pk]), resp.status_code, passed)
    # restore
    client.post(reverse("gestion:fournisseur_basculer", args=[fourn.pk]))

# Commandes d'achat
resp = client.get(reverse("gestion:commande_liste"))
record("Achats", "Bouton Liste Commandes Achat", "GET", reverse("gestion:commande_liste"), resp.status_code, resp.status_code == 200)

resp = client.get(reverse("gestion:commande_ajouter"))
record("Achats", "Bouton + Nouvelle Commande Achat (page)", "GET", reverse("gestion:commande_ajouter"), resp.status_code, resp.status_code == 200)

commande_sample = CommandeAchat.objects.first()
if commande_sample:
    pdf_cmd_url = reverse("gestion:bon_commande_pdf", args=[commande_sample.pk])
    resp = client.get(pdf_cmd_url)
    passed = resp.status_code == 200 and resp.get("Content-Type") == "application/pdf"
    record("Achats", "Bouton Bon de Commande PDF", "GET", pdf_cmd_url, resp.status_code, passed, f"{len(resp.content)} octets")

# 7. CLIENTS
resp = client.get(reverse("gestion:client_liste"))
record("Clients", "Bouton Liste Clients", "GET", reverse("gestion:client_liste"), resp.status_code, resp.status_code == 200)

resp = client.get(reverse("gestion:client_ajouter"))
record("Clients", "Bouton + Nouveau Client (page)", "GET", reverse("gestion:client_ajouter"), resp.status_code, resp.status_code == 200)

client_post = {"nom": "Client Test Bouton", "telephone": "0340011229", "email": "client@test.mg", "statut": "ACTIF"}
resp = client.post(reverse("gestion:client_ajouter"), client_post)
new_cl = ClientModel.objects.filter(telephone="0340011229").first()
passed = resp.status_code in [302, 200] and new_cl is not None
record("Clients", "Bouton Enregistrer Nouveau Client", "POST", reverse("gestion:client_ajouter"), resp.status_code, passed)
if new_cl:
    resp = client.post(reverse("gestion:client_supprimer", args=[new_cl.pk]))
    record("Clients", "Bouton Supprimer Client", "POST", reverse("gestion:client_supprimer", args=[new_cl.pk]), resp.status_code, resp.status_code in [302, 200])

# 8. UTILISATEURS
resp = client.get(reverse("gestion:utilisateur_liste"))
record("Utilisateurs", "Bouton Liste Utilisateurs", "GET", reverse("gestion:utilisateur_liste"), resp.status_code, resp.status_code == 200)

# Toggle utilisateur
target_user = User.objects.filter(is_superuser=False).first()
if target_user:
    actif_before = target_user.is_active
    resp = client.post(reverse("gestion:utilisateur_basculer", args=[target_user.pk]))
    target_user.refresh_from_db()
    passed = resp.status_code in [302, 200] and target_user.is_active != actif_before
    record("Utilisateurs", "Bouton Activer/Désactiver Utilisateur", "POST", reverse("gestion:utilisateur_basculer", args=[target_user.pk]), resp.status_code, passed)
    # restore
    client.post(reverse("gestion:utilisateur_basculer", args=[target_user.pk]))

# 9. RAPPORTS & EXPORTS PDF
resp = client.get(reverse("gestion:rapports"))
record("Rapports", "Bouton Page Statistiques & Rapports", "GET", reverse("gestion:rapports"), resp.status_code, resp.status_code == 200)

pdf_endpoints = [
    ("Bouton Télécharger Rapport Stock PDF", reverse("gestion:rapport_stock_pdf")),
    ("Bouton Télécharger Rapport Ventes PDF", reverse("gestion:rapport_ventes_pdf")),
    ("Bouton Télécharger Rapport Achats PDF", reverse("gestion:rapport_achats_pdf")),
    ("Bouton Télécharger Rapport Péremptions PDF", reverse("gestion:rapport_peremptions_pdf")),
]
for name, url in pdf_endpoints:
    resp = client.get(url)
    passed = resp.status_code == 200 and resp.get("Content-Type") == "application/pdf"
    record("Rapports", name, "GET", url, resp.status_code, passed, f"{len(resp.content)} octets")

# 10. AUDIT & ALERTES
resp = client.get(reverse("gestion:journal_liste"))
record("Journal d'Audit", "Bouton Vue Journal d'Audit", "GET", reverse("gestion:journal_liste"), resp.status_code, resp.status_code == 200)

resp = client.get(reverse("gestion:alertes"))
record("Alertes", "Bouton Alertes Stocks & Péremptions", "GET", reverse("gestion:alertes"), resp.status_code, resp.status_code == 200)

print("\n=======================================================================")
total = len(results)
passed_count = sum(1 for r in results if r["passed"])
failed_count = total - passed_count
print(f"RÉSULTAT DU CONTRÔLE DES BOUTONS : {passed_count}/{total} SUCCÈS ({failed_count} ÉCHECS)")
print("=======================================================================")
