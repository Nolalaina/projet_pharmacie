from django.conf import settings
from django.core.exceptions import ValidationError


def valider_taille_image(fichier):
    """Refuse les images dépassant la taille maximale configurée."""
    taille_max = settings.TAILLE_MAX_PHOTO_MO * 1024 * 1024
    if fichier.size > taille_max:
        raise ValidationError(
            f"L'image ne doit pas dépasser {settings.TAILLE_MAX_PHOTO_MO} Mo."
        )
