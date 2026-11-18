import os
import django
from decimal import Decimal
from datetime import date, timedelta
from PIL import Image, ImageDraw

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from gestion.models import (
    Categorie, Fournisseur, Medicament, LotStock, Client, Vente,
    LigneVente, Paiement, MouvementStock, CommandeAchat, LigneAchat
)

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
pharmacien = User.objects.filter(role="PHARMACIEN").first() or admin_user
caissier = User.objects.filter(role="CAISSIER").first() or admin_user

print("═══════════════════════════════════════════════════════════════════════")
print("  PHARMAGEST — SEEDING DE DONNÉES RÉELLES & COMPLÈTES DE PHARMACIE")
print("═══════════════════════════════════════════════════════════════════════\n")

# 1. CATÉGORIES
categories_data = [
    ("Antalgiques & Antipyrétiques", "Traitement de la douleur, fièvre, céphalées et maux courants."),
    ("Antibiotiques & Antibactériens", "Médicaments anti-infectieux soumis à prescription médicale stricte."),
    ("Anti-inflammatoires (AINS)", "Soulagement des inflammations articulaires, musculaires et dentaires."),
    ("Cardiologie & Hypertension", "Traitements des pathologies cardiovasculaires et de la tension artérielle."),
    ("Gastro-entérologie", "Troubles digestifs, reflux gastro-œsophagien, antispasmodiques et antidiarrhéiques."),
    ("Pneumologie & Allergologie", "Bronchodilatateurs, antihistaminiques et soins des voies respiratoires."),
    ("Dermatologie & Antiseptiques", "Désinfectants cutanés, crèmes cicatrisantes et soins dermatologiques."),
    ("Vitamines & Compléments", "Vitamines, oligo-éléments, toniques généraux et stimulants immunitaires."),
]

categories = {}
for nom, desc in categories_data:
    cat, created = Categorie.objects.get_or_create(nom=nom, defaults={"description": desc})
    categories[nom] = cat
    print(f"  [Catégorie] {nom} ({'créée' if created else 'existante'})")

# 2. FOURNISSEURS
fournisseurs_data = [
    ("SALAMA Madagascar", "Anosivavaka, BP 3822, Antananarivo", "020 22 400 12", "contact@salama.mg", "NIF-100200300", "Dr. Ratsimba Alain"),
    ("Sanofi Pasteur Océan Indien", "Zone Industrielle Forello, Tanjombato", "020 22 355 80", "commandes@sanofi.mg", "NIF-200300400", "Mme. Ravololona Sylvie"),
    ("Laboratoires Médi-Pharma", "Boulevard de l'Europe, Ankorondrano", "034 05 112 40", "distribution@medipharma.mg", "NIF-300400500", "M. Rakotonirina Hery"),
    ("Pharmalab International", "Route Circulaire, Antsakaviro", "032 07 889 00", "ventes@pharmalab.mg", "NIF-400500600", "Dr. Rabeharisoa Patrick"),
    ("Biogaran Afrique Francophone", "Rue Rainizanabololona, Antanimena", "033 11 445 20", "contact@biogaran.mg", "NIF-500600700", "Mme. Andriamihaja Fara"),
]

fournisseurs = {}
for rs, adr, tel, email, nif, cp in fournisseurs_data:
    f, created = Fournisseur.objects.get_or_create(
        raison_sociale=rs,
        defaults={
            "adresse": adr,
            "telephone": tel,
            "email": email,
            "numero_fiscal": nif,
            "contact_principal": cp,
            "statut": Fournisseur.Statut.ACTIF
        }
    )
    fournisseurs[rs] = f
    print(f"  [Fournisseur] {rs}")

# Helper to generate box image
os.makedirs("media/medicaments", exist_ok=True)
def ensure_box_image(filename, brand, dosage, color_rgb):
    filepath = os.path.join("media/medicaments", filename)
    if os.path.exists(filepath):
        return filepath
    im = Image.new("RGB", (320, 240), color=color_rgb)
    draw = ImageDraw.Draw(im)
    draw.rectangle([12, 12, 308, 228], fill=(255, 255, 255), outline=color_rgb, width=2)
    draw.rectangle([12, 12, 308, 65], fill=color_rgb)
    draw.rectangle([25, 28, 45, 48], fill=(255, 255, 255))
    draw.rectangle([31, 22, 39, 54], fill=(255, 255, 255))
    draw.text((60, 30), brand[:18], fill=(255, 255, 255))
    draw.text((30, 90), brand, fill=(15, 23, 42))
    draw.text((30, 125), f"Dosage : {dosage}", fill=(71, 85, 105))
    draw.text((30, 155), "Usage pharmaceutique certifié", fill=(148, 163, 184))
    for bx in range(30, 290, 6):
        draw.line([(bx, 190), (bx, 218)], fill=(15, 23, 42), width=3)
    im.save(filepath, quality=92)
    return filepath

# 3. MÉDICAMENTS RÉELS & PHOTOS
medicaments_data = [
    # Antalgiques
    {
        "nom": "Doliprane 1000 mg", "dci": "Paracétamol", "cat": "Antalgiques & Antipyrétiques",
        "forme": "Comprimé", "dosage": "1000 mg", "labo": "Sanofi", "code": "3400935898394",
        "pa": "2800.00", "pv": "3800.00", "seuil": 15, "photo": "doliprane.jpg", "color": (16, 185, 129)
    },
    {
        "nom": "Efferalgan 500 mg", "dci": "Paracétamol", "cat": "Antalgiques & Antipyrétiques",
        "forme": "Comprimé effervescent", "dosage": "500 mg", "labo": "UPSA", "code": "3400930353133",
        "pa": "2400.00", "pv": "3200.00", "seuil": 12, "photo": "efferalgan.jpg", "color": (14, 165, 233)
    },
    {
        "nom": "Advil 400 mg", "dci": "Ibuprofène", "cat": "Anti-inflammatoires (AINS)",
        "forme": "Comprimé enrobé", "dosage": "400 mg", "labo": "Pfizer Santé", "code": "3400934098924",
        "pa": "4500.00", "pv": "6200.00", "seuil": 10, "photo": "advil.jpg", "color": (239, 68, 68)
    },
    {
        "nom": "Bi-Profenid 100 mg", "dci": "Kétoprofène", "cat": "Anti-inflammatoires (AINS)",
        "forme": "Comprimé sécable", "dosage": "100 mg", "labo": "Sanofi Aventis", "code": "3400933519826",
        "pa": "7800.00", "pv": "10500.00", "seuil": 8, "photo": "biprofenid.jpg", "color": (220, 38, 38)
    },
    # Antibiotiques
    {
        "nom": "Amoxil 500 mg", "dci": "Amoxicilline trihydratée", "cat": "Antibiotiques & Antibactériens",
        "forme": "Gélule", "dosage": "500 mg", "labo": "GSK", "code": "3400932204914",
        "pa": "6200.00", "pv": "8500.00", "seuil": 15, "photo": "amoxil.jpg", "color": (37, 99, 235)
    },
    {
        "nom": "Augmentin 1 g / 125 mg", "dci": "Amoxicilline + Acide clavulanique", "cat": "Antibiotiques & Antibactériens",
        "forme": "Poudre pour suspension orale", "dosage": "1 g", "labo": "GlaxoSmithKline", "code": "3400934383181",
        "pa": "14000.00", "pv": "18900.00", "seuil": 10, "photo": "augmentin.jpg", "color": (30, 64, 175)
    },
    {
        "nom": "Zithromax 250 mg", "dci": "Azithromycine", "cat": "Antibiotiques & Antibactériens",
        "forme": "Comprimé pelliculé", "dosage": "250 mg", "labo": "Pfizer", "code": "3400933758256",
        "pa": "12500.00", "pv": "16800.00", "seuil": 6, "photo": "zithromax.jpg", "color": (59, 130, 246)
    },
    # Gastro
    {
        "nom": "Mopral 20 mg", "dci": "Oméprazole", "cat": "Gastro-entérologie",
        "forme": "Gélule gastro-résistante", "dosage": "20 mg", "labo": "AstraZeneca", "code": "3400933718915",
        "pa": "5100.00", "pv": "7200.00", "seuil": 12, "photo": "mopral.jpg", "color": (168, 85, 247)
    },
    {
        "nom": "Spasfon Lyoc", "dci": "Phloroglucinol", "cat": "Gastro-entérologie",
        "forme": "Lyophilisat oral", "dosage": "80 mg", "labo": "Teva Santé", "code": "3400935572621",
        "pa": "3600.00", "pv": "4900.00", "seuil": 15, "photo": "spasfon.jpg", "color": (192, 132, 252)
    },
    {
        "nom": "Smecta 3 g", "dci": "Diosmectite", "cat": "Gastro-entérologie",
        "forme": "Poudre pour suspension buvable", "dosage": "3 g", "labo": "Ipsen Consumer", "code": "3400935402928",
        "pa": "2900.00", "pv": "3950.00", "seuil": 20, "photo": "smecta.jpg", "color": (217, 119, 6)
    },
    {
        "nom": "Gaviscon Suspension", "dci": "Alginate de sodium + Bicarbonate", "cat": "Gastro-entérologie",
        "forme": "Suspension buvable en sachet", "dosage": "10 ml", "labo": "Reckitt Benckiser", "code": "3400935706910",
        "pa": "4200.00", "pv": "5800.00", "seuil": 15, "photo": "gaviscon.jpg", "color": (180, 83, 9)
    },
    # Pneumologie & Allergologie
    {
        "nom": "Ventoline 100 µg", "dci": "Salbutamol", "cat": "Pneumologie & Allergologie",
        "forme": "Suspension pour inhalation", "dosage": "100 µg / dose", "labo": "GSK Glaxo", "code": "3400932599720",
        "pa": "11200.00", "pv": "15400.00", "seuil": 8, "photo": "ventoline.jpg", "color": (13, 148, 136)
    },
    {
        "nom": "Zyrtec 10 mg", "dci": "Cétirizine dichlorhydrate", "cat": "Pneumologie & Allergologie",
        "forme": "Comprimé pelliculé sécable", "dosage": "10 mg", "labo": "UCB Pharma", "code": "3400934149817",
        "pa": "4800.00", "pv": "6500.00", "seuil": 10, "photo": "zyrtec.jpg", "color": (20, 184, 166)
    },
    # Cardiologie
    {
        "nom": "Amlor 5 mg", "dci": "Amlodipine bésylate", "cat": "Cardiologie & Hypertension",
        "forme": "Gélule", "dosage": "5 mg", "labo": "Pfizer PFE", "code": "3400933596544",
        "pa": "8900.00", "pv": "12200.00", "seuil": 10, "photo": "amlor.jpg", "color": (225, 29, 72)
    },
    {
        "nom": "Glucophage 850 mg", "dci": "Metformine chlorhydrate", "cat": "Cardiologie & Hypertension",
        "forme": "Comprimé pelliculé", "dosage": "850 mg", "labo": "Merck Santé", "code": "3400932782788",
        "pa": "5300.00", "pv": "7400.00", "seuil": 12, "photo": "glucophage.jpg", "color": (190, 18, 60)
    },
    # Dermatologie
    {
        "nom": "Bétadine Dermique 10%", "dci": "Povidone iodée", "cat": "Dermatologie & Antiseptiques",
        "forme": "Solution pour application locale", "dosage": "Flacon 125 ml", "labo": "Mylan Viatris", "code": "3400931210879",
        "pa": "6500.00", "pv": "8900.00", "seuil": 15, "photo": "betadine.jpg", "color": (180, 83, 9)
    },
    {
        "nom": "Bépanthène 5% Pommade", "dci": "Dexpanthénol", "cat": "Dermatologie & Antiseptiques",
        "forme": "Pommade en tube", "dosage": "100 g", "labo": "Bayer Healthcare", "code": "3400932403614",
        "pa": "9500.00", "pv": "13200.00", "seuil": 8, "photo": "bepanthene.jpg", "color": (2, 132, 199)
    },
    # Vitamines
    {
        "nom": "Laroscorbine 1 g", "dci": "Acide ascorbique (Vitamine C)", "cat": "Vitamines & Compléments",
        "forme": "Comprimé effervescent", "dosage": "1000 mg", "labo": "Bayer Consumer", "code": "3400931124503",
        "pa": "5800.00", "pv": "7900.00", "seuil": 20, "photo": "vitamine_c.jpg", "color": (245, 158, 11)
    },
    {
        "nom": "Coartem 20/120 mg", "dci": "Artéméther + Luméfantrine", "cat": "Antibiotiques & Antibactériens",
        "forme": "Comprimé", "dosage": "20 mg / 120 mg", "labo": "Novartis", "code": "3400938459202",
        "pa": "11500.00", "pv": "15800.00", "seuil": 15, "photo": "coartem.jpg", "color": (16, 185, 129)
    },
    {
        "nom": "Daflon 500 mg", "dci": "Fraction flavonoïque purifiée", "cat": "Cardiologie & Hypertension",
        "forme": "Comprimé pelliculé", "dosage": "500 mg", "labo": "Servier", "code": "3400933100512",
        "pa": "13500.00", "pv": "18200.00", "seuil": 10, "photo": "daflon.jpg", "color": (79, 70, 229)
    },
]

medicaments = {}
for m_data in medicaments_data:
    cat = categories[m_data["cat"]]
    img_path = ensure_box_image(m_data["photo"], m_data["nom"], m_data["dosage"], m_data["color"])
    photo_rel = f"medicaments/{m_data['photo']}"
    
    med, created = Medicament.objects.get_or_create(
        nom_commercial=m_data["nom"],
        defaults={
            "denomination_generique": m_data["dci"],
            "categorie": cat,
            "forme_pharmaceutique": m_data["forme"],
            "dosage": m_data["dosage"],
            "laboratoire": m_data["labo"],
            "code_barres": m_data["code"],
            "prix_achat": Decimal(m_data["pa"]),
            "prix_vente": Decimal(m_data["pv"]),
            "seuil_alerte": m_data["seuil"],
            "statut": Medicament.Statut.ACTIF,
            "photo": photo_rel
        }
    )
    medicaments[m_data["nom"]] = med
    print(f"  [Médicament] {med.nom_commercial} ({'créé' if created else 'existant'})")

# 4. LOTS DE STOCK RÉELS (Valides, Proches FEFO, Périmés, Bloqués)
aujourd_hui = timezone.localdate()
lots_specs = [
    # Doliprane
    ("Doliprane 1000 mg", "LOT-DOL-2026A", aujourd_hui + timedelta(days=22), 35, False),  # Proche péremption J-22 (FEFO)
    ("Doliprane 1000 mg", "LOT-DOL-2027B", aujourd_hui + timedelta(days=420), 80, False), # Valide
    # Efferalgan
    ("Efferalgan 500 mg", "LOT-EFF-2026A", aujourd_hui + timedelta(days=18), 24, False),  # Proche péremption J-18 (FEFO)
    ("Efferalgan 500 mg", "LOT-EFF-2027C", aujourd_hui + timedelta(days=360), 65, False), # Valide
    # Advil
    ("Advil 400 mg", "LOT-ADV-2026B", aujourd_hui + timedelta(days=300), 50, False),      # Valide
    ("Advil 400 mg", "LOT-ADV-PERIM", aujourd_hui - timedelta(days=45), 12, False),       # Périmé (-45j)
    # Bi-Profenid
    ("Bi-Profenid 100 mg", "LOT-BIP-2027A", aujourd_hui + timedelta(days=520), 40, False),
    # Amoxil
    ("Amoxil 500 mg", "LOT-AMX-FEFO", aujourd_hui + timedelta(days=15), 18, False),       # Proche péremption J-15 (FEFO)
    ("Amoxil 500 mg", "LOT-AMX-2027A", aujourd_hui + timedelta(days=480), 75, False),     # Valide
    ("Amoxil 500 mg", "LOT-AMX-BLOQ", aujourd_hui + timedelta(days=200), 10, True),       # Bloqué sanitaire
    # Augmentin
    ("Augmentin 1 g / 125 mg", "LOT-AUG-2026X", aujourd_hui + timedelta(days=210), 30, False),
    # Zithromax
    ("Zithromax 250 mg", "LOT-ZIT-2027B", aujourd_hui + timedelta(days=380), 25, False),
    # Mopral
    ("Mopral 20 mg", "LOT-MOP-2026A", aujourd_hui + timedelta(days=25), 15, False),       # Proche péremption J-25 (FEFO)
    ("Mopral 20 mg", "LOT-MOP-2027D", aujourd_hui + timedelta(days=390), 55, False),
    # Spasfon
    ("Spasfon Lyoc", "LOT-SPA-2026C", aujourd_hui + timedelta(days=280), 60, False),
    # Smecta
    ("Smecta 3 g", "LOT-SME-2026A", aujourd_hui + timedelta(days=340), 90, False),
    ("Smecta 3 g", "LOT-SME-PERIM", aujourd_hui - timedelta(days=30), 15, False),         # Périmé (-30j)
    # Gaviscon
    ("Gaviscon Suspension", "LOT-GAV-2027A", aujourd_hui + timedelta(days=410), 45, False),
    # Ventoline
    ("Ventoline 100 µg", "LOT-VEN-2026F", aujourd_hui + timedelta(days=290), 28, False),
    # Zyrtec
    ("Zyrtec 10 mg", "LOT-ZYR-2026B", aujourd_hui + timedelta(days=310), 35, False),
    # Amlor
    ("Amlor 5 mg", "LOT-AML-2027A", aujourd_hui + timedelta(days=500), 40, False),
    # Glucophage
    ("Glucophage 850 mg", "LOT-GLU-2026E", aujourd_hui + timedelta(days=360), 50, False),
    # Bétadine
    ("Bétadine Dermique 10%", "LOT-BET-2026A", aujourd_hui + timedelta(days=260), 32, False),
    # Bépanthène
    ("Bépanthène 5% Pommade", "LOT-BEP-2027C", aujourd_hui + timedelta(days=440), 20, False),
    # Laroscorbine
    ("Laroscorbine 1 g", "LOT-LAR-2026A", aujourd_hui + timedelta(days=20), 22, False),    # Proche péremption J-20 (FEFO)
    ("Laroscorbine 1 g", "LOT-LAR-2027B", aujourd_hui + timedelta(days=400), 60, False),
    # Coartem
    ("Coartem 20/120 mg", "LOT-COA-2026X", aujourd_hui + timedelta(days=330), 45, False),
    # Daflon
    ("Daflon 500 mg", "LOT-DAF-2027M", aujourd_hui + timedelta(days=460), 30, False),
]

created_lots_count = 0
for med_name, num_lot, d_peremp, qty, is_bloq in lots_specs:
    med = medicaments.get(med_name)
    if not med:
        continue
    lot, created = LotStock.objects.get_or_create(
        medicament=med,
        numero_lot=num_lot,
        defaults={
            "date_peremption": d_peremp,
            "quantite": qty,
            "quantite_recue": qty + 10,
            "date_reception": aujourd_hui - timedelta(days=40),
            "bloque": is_bloq
        }
    )
    if created:
        created_lots_count += 1
        MouvementStock.objects.create(
            medicament=med,
            lot=lot,
            type=MouvementStock.Type.ENTREE,
            quantite=qty,
            stock_apres=qty,
            reference=f"INIT-{num_lot}",
            motif="Initialisation stock catalogue",
            utilisateur=admin_user,
            date=timezone.now() - timedelta(days=40)
        )

print(f"  [Lots de stock] {created_lots_count} nouveaux lots créés (Total en base: {LotStock.objects.count()})")

# 5. CLIENTS
clients_data = [
    ("Rakotoarisoa Jean-Baptiste", "034 11 223 34", "jb.rakoto@gmail.com", "Lot II M 45 Andravoahangy"),
    ("Rasoamanana Marie-Hélène", "032 55 667 78", "marie.raso@moov.mg", "Logement 14 Cité Ampefiloha"),
    ("Randrianarivelo Eric", "033 44 889 90", "eric.randria@yahoo.fr", "Villa Soa, Ivato Aéroport"),
    ("Ramanandraibe Sahondra", "034 77 112 23", "sahondra.ram@gmail.com", "Lot IV G 12 Isoraka"),
    ("Andriamparany Michel", "032 99 334 45", "michel.andry@orange.mg", "Rue Pasteur, Mahamasina Sud"),
    ("Razafindrakoto Hery", "033 22 556 67", "hery.razaf@gmail.com", "Enceinte Ostie, Behoririka"),
]

clients_list = []
for nom, tel, email, adr in clients_data:
    cl, created = Client.objects.get_or_create(
        telephone=tel,
        defaults={"nom": nom, "email": email, "adresse": adr}
    )
    clients_list.append(cl)

print(f"  [Clients] {Client.objects.count()} clients disponibles")

# 6. HISTORIQUE DE VENTES
ventes_specs = [
    (1, [("Doliprane 1000 mg", 2), ("Laroscorbine 1 g", 1)], Paiement.Mode.ESPECES, Decimal("0.00")),
    (2, [("Amoxil 500 mg", 1), ("Doliprane 1000 mg", 1)], Paiement.Mode.MOBILE_MONEY, Decimal("500.00")),
    (3, [("Spasfon Lyoc", 2), ("Smecta 3 g", 2)], Paiement.Mode.ESPECES, Decimal("0.00")),
    (5, [("Advil 400 mg", 1), ("Mopral 20 mg", 1)], Paiement.Mode.CARTE, Decimal("0.00")),
    (7, [("Augmentin 1 g / 125 mg", 1), ("Doliprane 1000 mg", 2)], Paiement.Mode.MOBILE_MONEY, Decimal("1000.00")),
    (9, [("Ventoline 100 µg", 1), ("Zyrtec 10 mg", 1)], Paiement.Mode.ESPECES, Decimal("0.00")),
    (12, [("Bétadine Dermique 10%", 1), ("Bépanthène 5% Pommade", 1)], Paiement.Mode.ESPECES, Decimal("0.00")),
    (15, [("Coartem 20/120 mg", 1), ("Laroscorbine 1 g", 2)], Paiement.Mode.MOBILE_MONEY, Decimal("0.00")),
    (18, [("Amlor 5 mg", 1), ("Glucophage 850 mg", 1)], Paiement.Mode.CARTE, Decimal("0.00")),
    (22, [("Daflon 500 mg", 1), ("Doliprane 1000 mg", 1)], Paiement.Mode.ESPECES, Decimal("0.00")),
]

created_ventes_count = 0
for idx, (days_ago, items, mode_pay, rem) in enumerate(ventes_specs):
    date_v = timezone.now() - timedelta(days=days_ago, hours=idx*2)
    cl = clients_list[idx % len(clients_list)]
    
    lines_to_add = []
    for med_name, qty in items:
        med = medicaments.get(med_name)
        if med:
            lot = med.lots.filter(bloque=False, date_peremption__gt=timezone.localdate(), quantite__gte=qty).first()
            if lot:
                lines_to_add.append((med, lot, qty))
                
    if not lines_to_add:
        continue
        
    v = Vente.objects.create(
        client=cl,
        utilisateur=caissier,
        remise=rem,
        date_vente=date_v,
    )
    
    total_vente = Decimal("0.00")
    for med, lot, qty in lines_to_add:
        pu = med.prix_vente
        LigneVente.objects.create(
            vente=v,
            medicament=med,
            lot=lot,
            quantite=qty,
            prix_unitaire=pu
        )
        lot.quantite = max(0, lot.quantite - qty)
        lot.save(update_fields=["quantite"])
        total_vente += pu * qty
        
        MouvementStock.objects.create(
            medicament=med,
            lot=lot,
            type=MouvementStock.Type.SORTIE,
            quantite=qty,
            stock_apres=lot.quantite,
            reference=f"VENTE-{v.numero}",
            motif=f"Délivrance caisse {v.numero}",
            utilisateur=caissier,
            date=date_v
        )
        
    v.valider(caissier)
    Paiement.objects.create(
        vente=v,
        montant=v.total,
        mode=mode_pay,
        statut=Paiement.Statut.CONFIRME,
        reference=f"PAY-{v.numero}",
        confirme_par=caissier,
        date_paiement=date_v,
        date_confirmation=date_v
    )
    created_ventes_count += 1

print(f"  [Ventes] {created_ventes_count} ventes historiques validées (Total en base: {Vente.objects.count()})")

# 7. COMMANDES FOURNISSEURS
fourn_salama = fournisseurs["SALAMA Madagascar"]
cmd1 = CommandeAchat.objects.filter(fournisseur=fourn_salama).first()
if not cmd1:
    cmd1 = CommandeAchat.objects.create(
        fournisseur=fourn_salama,
        utilisateur=pharmacien,
        statut=CommandeAchat.Statut.RECEPTIONNEE,
        date_commande=aujourd_hui - timedelta(days=20),
        notes="Commande annuelle vaccins et antibiotiques"
    )
    LigneAchat.objects.create(
        commande=cmd1,
        medicament=medicaments["Doliprane 1000 mg"],
        quantite_commandee=100,
        quantite_recue=100,
        prix_achat=Decimal("2800.00")
    )
    LigneAchat.objects.create(
        commande=cmd1,
        medicament=medicaments["Amoxil 500 mg"],
        quantite_commandee=80,
        quantite_recue=80,
        prix_achat=Decimal("6200.00")
    )

fourn_sanofi = fournisseurs["Sanofi Pasteur Océan Indien"]
cmd2 = CommandeAchat.objects.filter(fournisseur=fourn_sanofi).first()
if not cmd2:
    cmd2 = CommandeAchat.objects.create(
        fournisseur=fourn_sanofi,
        utilisateur=pharmacien,
        statut=CommandeAchat.Statut.COMMANDEE,
        date_commande=aujourd_hui - timedelta(days=3),
        notes="Réapprovisionnement Augmentin et Ventoline"
    )
    LigneAchat.objects.create(
        commande=cmd2,
        medicament=medicaments["Augmentin 1 g / 125 mg"],
        quantite_commandee=50,
        quantite_recue=0,
        prix_achat=Decimal("14000.00")
    )
    LigneAchat.objects.create(
        commande=cmd2,
        medicament=medicaments["Ventoline 100 µg"],
        quantite_commandee=40,
        quantite_recue=0,
        prix_achat=Decimal("11200.00")
    )

print(f"  [Commandes Achats] {CommandeAchat.objects.count()} commandes fournisseurs enregistrées")

print("\n═══════════════════════════════════════════════════════════════════════")
print("  BASE DE DONNÉES ENRICHIE AVEC SUCCÈS !")
print(f"  - Catégories : {Categorie.objects.count()}")
print(f"  - Fournisseurs : {Fournisseur.objects.count()}")
print(f"  - Médicaments : {Medicament.objects.count()} (avec photos réelles)")
print(f"  - Lots de stock : {LotStock.objects.count()} (FEFO / périmés / valides)")
print(f"  - Clients : {Client.objects.count()}")
print(f"  - Ventes validées : {Vente.objects.count()}")
print(f"  - Commandes : {CommandeAchat.objects.count()}")
print("═══════════════════════════════════════════════════════════════════════")
