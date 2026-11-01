from django.contrib.auth.models import Group, Permission

from .models import Utilisateur

ROLES = Utilisateur.Role

GROUPES = {
    ROLES.ADMIN: "__toutes__",
    ROLES.PHARMACIEN: {
        "categorie": {"add", "change", "delete", "view"},
        "medicament": {"add", "change", "delete", "view"},
        "fournisseur": {"add", "change", "view"},
        "client": {"add", "change", "view"},
        "lotstock": {"add", "change", "view"},
        "mouvementstock": {"view"},
        "commandeachat": {"add", "change", "view"},
        "ligneachat": {"add", "change", "delete", "view"},
        "receptionachat": {"add", "change", "view"},
        "lignereception": {"add", "change", "delete", "view"},
        "vente": {"add", "change", "view"},
        "lignevente": {"add", "change", "delete", "view"},
        "paiement": {"add", "change", "view"},
        "retourvente": {"add", "change", "view"},
        "ligneretour": {"add", "change", "delete", "view"},
        "journalaudit": {"view"},
    },
    ROLES.GESTIONNAIRE: {
        "categorie": {"add", "change", "view"},
        "medicament": {"add", "change", "view"},
        "fournisseur": {"add", "change", "view"},
        "client": {"view"},
        "lotstock": {"add", "change", "view"},
        "mouvementstock": {"view"},
        "commandeachat": {"add", "change", "view"},
        "ligneachat": {"add", "change", "delete", "view"},
        "receptionachat": {"add", "change", "view"},
        "lignereception": {"add", "change", "delete", "view"},
        "retourvente": {"view"},
        "journalaudit": {"view"},
    },
    ROLES.CAISSIER: {
        "categorie": {"view"},
        "medicament": {"view"},
        "lotstock": {"view"},
        "client": {"add", "change", "view"},
        "vente": {"add", "change", "view"},
        "lignevente": {"add", "change", "delete", "view"},
        "paiement": {"add", "view"},
        "retourvente": {"add", "view"},
        "ligneretour": {"add", "delete", "view"},
    },
    ROLES.RESPONSABLE: {
        "categorie": {"view"},
        "medicament": {"view"},
        "fournisseur": {"view"},
        "client": {"view"},
        "lotstock": {"view"},
        "mouvementstock": {"view"},
        "commandeachat": {"view"},
        "ligneachat": {"view"},
        "receptionachat": {"view"},
        "lignereception": {"view"},
        "vente": {"view"},
        "lignevente": {"view"},
        "paiement": {"view"},
        "retourvente": {"view"},
        "ligneretour": {"view"},
        "journalaudit": {"view"},
    },
}


def initialiser_groupes(sender=None, app_config=None, **kwargs):
    toutes = Permission.objects.filter(content_type__app_label="gestion")
    for role, definition in GROUPES.items():
        groupe, _ = Group.objects.get_or_create(name=f"Role {role}")
        if definition == "__toutes__":
            groupe.permissions.set(toutes)
            continue
        permissions = []
        for modele, actions in definition.items():
            codenames = [f"{action}_{modele}" for action in actions]
            permissions.extend(
                Permission.objects.filter(
                    content_type__app_label="gestion",
                    content_type__model=modele,
                    codename__in=codenames,
                )
            )
        groupe.permissions.set(permissions)
