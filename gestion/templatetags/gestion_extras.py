from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()

COULEURS_STATUT = {
    "ACTIF": "green",
    "ARCHIVE": "gray",
    "INACTIF": "gray",
    "BROUILLON": "gray",
    "COMMANDEE": "blue",
    "PARTIELLE": "amber",
    "RECEPTIONNEE": "green",
    "ANNULEE": "red",
    "VALIDEE": "green",
    "EN_ATTENTE": "amber",
    "CONFIRME": "green",
    "ECHEC": "red",
    "REMBOURSE": "gray",
    "ENTREE": "green",
    "SORTIE": "red",
    "RETOUR": "amber",
    "CORRECTION": "blue",
    "PERTE": "red",
}


@register.filter
def ariary(valeur):
    try:
        nombre = Decimal(valeur or 0)
    except (InvalidOperation, TypeError, ValueError):
        return valeur
    texte = f"{nombre:,.2f}".replace(",", " ").replace(".", ",")
    return f"{texte} Ar"


@register.filter
def mul(gauche, droite):
    try:
        return Decimal(gauche or 0) * Decimal(droite or 0)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


@register.filter
def couleur_statut(statut):
    return COULEURS_STATUT.get(str(statut), "gray")


@register.filter
def initiales(utilisateur):
    if hasattr(utilisateur, "nom_complet"):
        nom = utilisateur.nom_complet
    else:
        nom = str(utilisateur)
    morceaux = [m for m in nom.replace("-", " ").split(" ") if m]
    if not morceaux:
        return "?"
    if len(morceaux) == 1:
        return morceaux[0][:2].upper()
    return (morceaux[0][0] + morceaux[-1][0]).upper()


@register.filter
def sens_mouvement(quantite):
    try:
        return "positive" if int(quantite) >= 0 else "negative"
    except (TypeError, ValueError):
        return "neutral"
