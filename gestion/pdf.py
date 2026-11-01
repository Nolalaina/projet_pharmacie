import io
from datetime import date, datetime
from decimal import Decimal
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BLEU = colors.HexColor("#1f6f5c")
BLEU_CLAIR = colors.HexColor("#e7f3ef")
GRIS = colors.HexColor("#5f6b73")

STYLES = getSampleStyleSheet()
STYLES.add(
    ParagraphStyle(
        name="PharmaTitre",
        parent=STYLES["Title"],
        fontSize=17,
        leading=20,
        textColor=BLEU,
        alignment=0,
        spaceAfter=2,
    )
)
STYLES.add(
    ParagraphStyle(
        name="PharmaSous",
        parent=STYLES["Normal"],
        fontSize=8,
        leading=11,
        textColor=GRIS,
    )
)
STYLES.add(
    ParagraphStyle(
        name="PharmaDoc",
        parent=STYLES["Heading2"],
        fontSize=13,
        leading=16,
        alignment=TA_RIGHT,
        textColor=BLEU,
        spaceAfter=2,
    )
)
STYLES.add(
    ParagraphStyle(
        name="PharmaPetit",
        parent=STYLES["Normal"],
        fontSize=7.5,
        leading=10,
    )
)
STYLES.add(
    ParagraphStyle(
        name="PharmaCellule",
        parent=STYLES["Normal"],
        fontSize=7.5,
        leading=9.5,
    )
)
STYLES.add(
    ParagraphStyle(
        name="PharmaCelluleDroite",
        parent=STYLES["PharmaCellule"],
        alignment=TA_RIGHT,
    )
)
STYLES.add(
    ParagraphStyle(
        name="PharmaEntete",
        parent=STYLES["PharmaCellule"],
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
)


def montant(valeur):
    valeur = Decimal(valeur or 0)
    texte = f"{valeur:,.2f}".replace(",", " ").replace(".", ",")
    return f"{texte} Ar"


def date_courte(valeur):
    if not valeur:
        return "—"
    if isinstance(valeur, datetime):
        if timezone.is_aware(valeur):
            valeur = timezone.localtime(valeur)
        return valeur.strftime("%d/%m/%Y")
    if isinstance(valeur, date):
        return valeur.strftime("%d/%m/%Y")
    return str(valeur)


def date_longue(valeur):
    if not valeur:
        return "—"
    if isinstance(valeur, datetime):
        if timezone.is_aware(valeur):
            valeur = timezone.localtime(valeur)
        return valeur.strftime("%d/%m/%Y à %H:%M")
    if isinstance(valeur, date):
        return valeur.strftime("%d/%m/%Y")
    return str(valeur)


def _p(texte, style="PharmaCellule"):
    return Paragraph(escape(str(texte)), STYLES[style])


def _h(texte):
    return _p(texte, "PharmaEntete")


def _entete(titre, reference, date_texte, largeur, complement=""):
    gauche = [
        Paragraph(escape(settings.PHARMACIE_NOM), STYLES["PharmaTitre"]),
        Paragraph(escape(settings.PHARMACIE_ADRESSE), STYLES["PharmaSous"]),
        Paragraph(
            f"Tél. {escape(settings.PHARMACIE_TELEPHONE)} — {escape(settings.PHARMACIE_EMAIL)}",
            STYLES["PharmaSous"],
        ),
        Paragraph(
            f"NIF {escape(settings.PHARMACIE_NIF)} — STAT {escape(settings.PHARMACIE_STAT)}",
            STYLES["PharmaSous"],
        ),
    ]
    droite = [
        Paragraph(escape(titre), STYLES["PharmaDoc"]),
        Paragraph(f"N° {escape(str(reference))}", STYLES["PharmaPetit"]),
        Paragraph(escape(date_texte), STYLES["PharmaPetit"]),
    ]
    if complement:
        droite.append(Paragraph(escape(complement), STYLES["PharmaPetit"]))
    table = Table([[gauche, droite]], colWidths=[largeur * 0.58, largeur * 0.42])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, -1), 1.2, BLEU),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _pied(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRIS)
    canvas.drawString(
        14 * mm,
        9 * mm,
        f"{settings.PHARMACIE_NOM} — {settings.PHARMACIE_ADRESSE}",
    )
    canvas.drawRightString(
        doc.pagesize[0] - 14 * mm, 9 * mm, f"Page {doc.page}"
    )
    canvas.restoreState()


def _construire(elements, nom_fichier, paysage=False):
    buffer = io.BytesIO()
    pagesize = landscape(A4) if paysage else A4
    document = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
        title=nom_fichier,
        author=settings.PHARMACIE_NOM,
    )
    document.build(elements, onFirstPage=_pied, onLaterPages=_pied)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{nom_fichier}"'
    return response


def _largeur(paysage=False):
    return (297 if paysage else 210) * mm - 28 * mm


def _tableau(donnees, largeurs, alignements=None):
    table = Table(donnees, colWidths=largeurs, repeatRows=1)
    commandes = [
        ("BACKGROUND", (0, 0), (-1, 0), BLEU),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c9d5d0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BLEU_CLAIR]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if alignements:
        for colonne, alignement in alignements.items():
            commandes.append(("ALIGN", (colonne, 0), (colonne, -1), alignement))
    table.setStyle(TableStyle(commandes))
    return table


def _resume(lignes, largeur):
    donnees = [[_p(libelle, "PharmaCelluleDroite"), _p(valeur, "PharmaCelluleDroite")] for libelle, valeur in lignes]
    table = Table(donnees, colWidths=[largeur * 0.22, largeur * 0.22])
    table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("LINEABOVE", (0, 0), (-1, 0), 0.8, BLEU),
                ("LINEBELOW", (0, -1), (-1, -1), 0.8, BLEU),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _bloc(contenu):
    return contenu


def pdf_recu(vente):
    largeur = _largeur()
    elements = [
        _entete(
            "REÇU DE VENTE",
            vente.numero,
            date_longue(vente.date_validation or vente.date_vente),
            largeur,
            "Document non fiscal",
        ),
        Spacer(1, 6 * mm),
    ]
    infos = [
        [
            _p("Client", "PharmaPetit"),
            _p(vente.client.nom_affichage if vente.client else "Client comptoir"),
            _p("Vendeur", "PharmaPetit"),
            _p(vente.utilisateur.nom_complet if vente.utilisateur else "—"),
        ],
        [
            _p("Statut", "PharmaPetit"),
            _p(vente.get_statut_display()),
            _p("Paiement", "PharmaPetit"),
            _p(
                ", ".join(
                    f"{p.get_mode_display()} ({p.get_statut_display()})"
                    for p in vente.paiements.all()
                )
                or "—"
            ),
        ],
    ]
    table_infos = Table(infos, colWidths=[largeur * 0.12, largeur * 0.38, largeur * 0.12, largeur * 0.38])
    table_infos.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), BLEU_CLAIR),
                ("BACKGROUND", (2, 0), (2, -1), BLEU_CLAIR),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d5d0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dbe6e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements += [table_infos, Spacer(1, 5 * mm)]

    donnees = [[
        _h("#"),
        _h("Médicament"),
        _h("Lot"),
        _h("Qté"),
        _h("Prix unitaire"),
        _h("Total"),
    ]]
    for index, ligne in enumerate(vente.lignes.all(), start=1):
        donnees.append(
            [
                _p(index),
                _p(ligne.medicament),
                _p(ligne.lot.numero_lot),
                _p(ligne.quantite),
                _p(montant(ligne.prix_unitaire)),
                _p(montant(ligne.sous_total)),
            ]
        )
    elements.append(
        _tableau(
            donnees,
            [largeur * 0.05, largeur * 0.39, largeur * 0.16, largeur * 0.08, largeur * 0.16, largeur * 0.16],
            {3: "RIGHT", 4: "RIGHT", 5: "RIGHT"},
        )
    )
    elements.append(Spacer(1, 4 * mm))
    resume = [
        ("Sous-total", montant(vente.sous_total)),
        ("Remise", montant(vente.remise)),
        ("Net à payer", montant(vente.total)),
        ("Montant payé", montant(vente.montant_confirme)),
        ("Reste à payer", montant(vente.reste_a_payer)),
    ]
    elements.append(_resume(resume, largeur))
    elements += [
        Spacer(1, 8 * mm),
        Paragraph(
            "Merci de votre confiance. Conservez ce reçu pour tout retour "
            "ou réclamation dans les conditions autorisées par la pharmacie.",
            STYLES["PharmaSous"],
        ),
    ]
    return _construire(elements, f"recu-{vente.numero}.pdf")


def pdf_facture(vente):
    largeur = _largeur()
    elements = [
        _entete(
            "FACTURE",
            vente.numero,
            date_longue(vente.date_validation or vente.date_vente),
            largeur,
            "Facture commerciale",
        ),
        Spacer(1, 6 * mm),
    ]
    client = vente.client
    infos = [
        [
            _p("Client", "PharmaPetit"),
            _p(client.nom_affichage if client else "Client comptoir"),
            _p("Téléphone", "PharmaPetit"),
            _p(client.telephone if client else "—"),
        ],
        [
            _p("Adresse", "PharmaPetit"),
            _p(client.adresse if client else "—"),
            _p("NIF / STAT", "PharmaPetit"),
            _p(f"{settings.PHARMACIE_NIF} / {settings.PHARMACIE_STAT}"),
        ],
    ]
    table_infos = Table(infos, colWidths=[largeur * 0.12, largeur * 0.38, largeur * 0.12, largeur * 0.38])
    table_infos.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), BLEU_CLAIR),
                ("BACKGROUND", (2, 0), (2, -1), BLEU_CLAIR),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d5d0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dbe6e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements += [table_infos, Spacer(1, 5 * mm)]
    donnees = [[
        _h("#"),
        _h("Désignation"),
        _h("Lot"),
        _h("Qté"),
        _h("P.U."),
        _h("Montant"),
    ]]
    for index, ligne in enumerate(vente.lignes.all(), start=1):
        donnees.append(
            [
                _p(index),
                _p(ligne.medicament),
                _p(ligne.lot.numero_lot),
                _p(ligne.quantite),
                _p(montant(ligne.prix_unitaire)),
                _p(montant(ligne.sous_total)),
            ]
        )
    elements.append(
        _tableau(
            donnees,
            [largeur * 0.06, largeur * 0.40, largeur * 0.16, largeur * 0.08, largeur * 0.15, largeur * 0.15],
            {3: "RIGHT", 4: "RIGHT", 5: "RIGHT"},
        )
    )
    elements.append(Spacer(1, 4 * mm))
    elements.append(
        _resume(
            [
                ("Total HT", montant(vente.sous_total)),
                ("Remise", montant(vente.remise)),
                ("Total à payer", montant(vente.total)),
                ("Payé", montant(vente.montant_confirme)),
            ],
            largeur,
        )
    )
    elements += [
        Spacer(1, 6 * mm),
        Paragraph(
            "Mentions légales : les informations fiscales et comptables de cette "
            "facture doivent être adaptées aux obligations applicables à Madagascar. "
            "La délivrance des médicaments reste soumise aux règles professionnelles en vigueur.",
            STYLES["PharmaSous"],
        ),
    ]
    return _construire(elements, f"facture-{vente.numero}.pdf")


def pdf_bon_commande(commande):
    largeur = _largeur()
    elements = [
        _entete(
            "BON DE COMMANDE",
            commande.numero,
            date_longue(commande.date_commande or commande.date_creation),
            largeur,
            commande.get_statut_display(),
        ),
        Spacer(1, 6 * mm),
        Paragraph(
            f"<b>Fournisseur :</b> {escape(commande.fournisseur.raison_sociale)}", STYLES["Normal"]
        ),
        Paragraph(
            f"{escape(commande.fournisseur.adresse or '')} — Tél. "
            f"{escape(commande.fournisseur.telephone or '—')}",
            STYLES["PharmaSous"],
        ),
        Spacer(1, 5 * mm),
    ]
    donnees = [[
        _h("#"),
        _h("Médicament"),
        _h("Qté commandée"),
        _h("Qté reçue"),
        _h("Prix achat"),
        _h("Total"),
    ]]
    for index, ligne in enumerate(commande.lignes.select_related("medicament"), start=1):
        donnees.append(
            [
                _p(index),
                _p(ligne.medicament),
                _p(ligne.quantite_commandee),
                _p(ligne.quantite_recue),
                _p(montant(ligne.prix_achat)),
                _p(montant(ligne.sous_total)),
            ]
        )
    elements.append(
        _tableau(
            donnees,
            [largeur * 0.06, largeur * 0.42, largeur * 0.12, largeur * 0.12, largeur * 0.14, largeur * 0.14],
            {2: "RIGHT", 3: "RIGHT", 4: "RIGHT", 5: "RIGHT"},
        )
    )
    elements.append(Spacer(1, 4 * mm))
    elements.append(_resume([("Total commande", montant(commande.total))], largeur))
    if commande.notes:
        elements += [Spacer(1, 5 * mm), Paragraph(f"Notes : {escape(commande.notes)}", STYLES["PharmaSous"])]
    return _construire(elements, f"bon-commande-{commande.numero}.pdf")


def pdf_bon_reception(reception):
    largeur = _largeur()
    elements = [
        _entete(
            "BON DE RÉCEPTION",
            reception.numero,
            date_longue(reception.date_validation or reception.date_reception),
            largeur,
            reception.commande.get_statut_display(),
        ),
        Spacer(1, 6 * mm),
        Paragraph(
            f"<b>Commande :</b> {escape(reception.commande.numero)} — "
            f"<b>Fournisseur :</b> {escape(reception.commande.fournisseur.raison_sociale)}",
            STYLES["Normal"],
        ),
        Spacer(1, 5 * mm),
    ]
    donnees = [[
        _h("#"),
        _h("Médicament"),
        _h("Lot"),
        _h("Péremption"),
        _h("Qté reçue"),
        _h("Prix achat"),
        _h("Total"),
    ]]
    for index, ligne in enumerate(
        reception.lignes.select_related("ligne_achat__medicament"), start=1
    ):
        donnees.append(
            [
                _p(index),
                _p(ligne.ligne_achat.medicament),
                _p(ligne.numero_lot),
                _p(date_courte(ligne.date_peremption)),
                _p(ligne.quantite),
                _p(montant(ligne.ligne_achat.prix_achat)),
                _p(montant(ligne.quantite * ligne.ligne_achat.prix_achat)),
            ]
        )
    elements.append(
        _tableau(
            donnees,
            [largeur * 0.05, largeur * 0.36, largeur * 0.15, largeur * 0.13, largeur * 0.09, largeur * 0.11, largeur * 0.11],
            {4: "RIGHT", 5: "RIGHT", 6: "RIGHT"},
        )
    )
    elements.append(Spacer(1, 4 * mm))
    elements.append(_resume([("Total réception", montant(reception.total))], largeur))
    return _construire(elements, f"bon-reception-{reception.numero}.pdf")


def pdf_rapport_stock(lots):
    largeur = _largeur(paysage=True)
    elements = [
        _entete(
            "RAPPORT DE STOCK",
            "STOCK",
            date_longue(timezone.now()),
            largeur,
            "État des lots disponibles",
        ),
        Spacer(1, 5 * mm),
    ]
    donnees = [[
        _h("Médicament"),
        _h("Lot"),
        _h("Péremption"),
        _h("Qté"),
        _h("Prix achat"),
        _h("Valeur"),
        _h("État"),
    ]]
    total_quantite = 0
    total_valeur = Decimal("0.00")
    for lot in lots:
        total_quantite += lot.quantite
        total_valeur += lot.valeur_stock
        etat = "Périmé" if lot.perime else ("Bloqué" if lot.bloque else "Valide")
        donnees.append(
            [
                _p(lot.medicament),
                _p(lot.numero_lot),
                _p(date_courte(lot.date_peremption)),
                _p(lot.quantite),
                _p(montant(lot.medicament.prix_achat)),
                _p(montant(lot.valeur_stock)),
                _p(etat),
            ]
        )
    elements.append(
        _tableau(
            donnees,
            [largeur * 0.30, largeur * 0.16, largeur * 0.12, largeur * 0.08, largeur * 0.12, largeur * 0.13, largeur * 0.09],
            {3: "RIGHT", 4: "RIGHT", 5: "RIGHT"},
        )
    )
    elements.append(Spacer(1, 4 * mm))
    elements.append(
        _resume(
            [
                ("Quantité totale", f"{total_quantite}"),
                ("Valeur totale", montant(total_valeur)),
            ],
            largeur,
        )
    )
    return _construire(elements, "rapport-stock.pdf", paysage=True)


def pdf_rapport_ventes(ventes, debut, fin):
    largeur = _largeur(paysage=True)
    elements = [
        _entete(
            "RAPPORT DES VENTES",
            f"{debut:%d/%m/%Y} au {fin:%d/%m/%Y}",
            date_longue(timezone.now()),
            largeur,
            "Ventes validées",
        ),
        Spacer(1, 5 * mm),
    ]
    donnees = [[
        _h("Date"),
        _h("N° vente"),
        _h("Client"),
        _h("Vendeur"),
        _h("Paiement"),
        _h("Total"),
    ]]
    total = Decimal("0.00")
    nombre = 0
    for vente in ventes:
        total += vente.total
        nombre += 1
        donnees.append(
            [
                _p(date_courte(vente.date_validation or vente.date_vente)),
                _p(vente.numero),
                _p(vente.client.nom_affichage if vente.client else "Client comptoir"),
                _p(vente.utilisateur.nom_complet if vente.utilisateur else "—"),
                _p(", ".join(p.get_mode_display() for p in vente.paiements.all()) or "—"),
                _p(montant(vente.total)),
            ]
        )
    elements.append(
        _tableau(
            donnees,
            [largeur * 0.12, largeur * 0.20, largeur * 0.20, largeur * 0.18, largeur * 0.15, largeur * 0.15],
            {5: "RIGHT"},
        )
    )
    elements.append(Spacer(1, 4 * mm))
    elements.append(
        _resume(
            [("Nombre de ventes", str(nombre)), ("Chiffre d'affaires", montant(total))],
            largeur,
        )
    )
    return _construire(
        elements, f"rapport-ventes-{debut}-{fin}.pdf", paysage=True
    )


def pdf_rapport_achats(commandes, debut, fin):
    largeur = _largeur(paysage=True)
    elements = [
        _entete(
            "RAPPORT DES ACHATS",
            f"{debut:%d/%m/%Y} au {fin:%d/%m/%Y}",
            date_longue(timezone.now()),
            largeur,
            "Commandes et réceptions",
        ),
        Spacer(1, 5 * mm),
    ]
    donnees = [[
        _h("Date"),
        _h("N° commande"),
        _h("Fournisseur"),
        _h("Statut"),
        _h("Reste à recevoir"),
        _h("Total"),
    ]]
    total = Decimal("0.00")
    for commande in commandes:
        total += commande.total
        donnees.append(
            [
                _p(date_courte(commande.date_creation)),
                _p(commande.numero),
                _p(commande.fournisseur.raison_sociale),
                _p(commande.get_statut_display()),
                _p(commande.reste_a_recevoir),
                _p(montant(commande.total)),
            ]
        )
    elements.append(
        _tableau(
            donnees,
            [largeur * 0.12, largeur * 0.20, largeur * 0.28, largeur * 0.18, largeur * 0.10, largeur * 0.12],
            {4: "RIGHT", 5: "RIGHT"},
        )
    )
    elements.append(Spacer(1, 4 * mm))
    elements.append(
        _resume(
            [
                ("Nombre de commandes", str(len(commandes))),
                ("Montant total", montant(total)),
            ],
            largeur,
        )
    )
    return _construire(
        elements, f"rapport-achats-{debut}-{fin}.pdf", paysage=True
    )


def pdf_rapport_peremptions(lots, aujourd_hui, limite):
    largeur = _largeur(paysage=True)
    elements = [
        _entete(
            "PRODUITS PÉRIMÉS OU PROCHE PÉREMPTION",
            f"Au {aujourd_hui:%d/%m/%Y}",
            date_longue(timezone.now()),
            largeur,
            f"Seuil d'alerte : {settings.SEUIL_PEREMPTION_JOURS} jours",
        ),
        Spacer(1, 5 * mm),
    ]
    donnees = [[
        _h("Médicament"),
        _h("Lot"),
        _h("Péremption"),
        _h("Jours restants"),
        _h("Qté"),
        _h("Valeur"),
        _h("État"),
    ]]
    valeur_totale = Decimal("0.00")
    for lot in lots:
        valeur_totale += lot.valeur_stock
        if lot.perime:
            etat = "Périmé"
        else:
            etat = "Proche péremption"
        donnees.append(
            [
                _p(lot.medicament),
                _p(lot.numero_lot),
                _p(date_courte(lot.date_peremption)),
                _p(lot.jours_avant_peremption),
                _p(lot.quantite),
                _p(montant(lot.valeur_stock)),
                _p(etat),
            ]
        )
    elements.append(
        _tableau(
            donnees,
            [largeur * 0.32, largeur * 0.14, largeur * 0.12, largeur * 0.10, largeur * 0.08, largeur * 0.12, largeur * 0.12],
            {3: "RIGHT", 4: "RIGHT", 5: "RIGHT"},
        )
    )
    elements.append(Spacer(1, 4 * mm))
    elements.append(
        _resume(
            [
                ("Lots concernés", str(len(lots))),
                ("Valeur totale", montant(valeur_totale)),
            ],
            largeur,
        )
    )
    return _construire(elements, "rapport-peremptions.pdf", paysage=True)
