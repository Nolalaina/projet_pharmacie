from datetime import timedelta

from django.conf import settings
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import LotStock, Medicament


def pharmacie(request):
    alertes = 0
    if getattr(request, "user", None) and request.user.is_authenticated:
        aujourd_hui = timezone.localdate()
        limite = aujourd_hui + timedelta(days=settings.SEUIL_PEREMPTION_JOURS)
        stocks_faibles = (
            Medicament.objects.filter(statut=Medicament.Statut.ACTIF)
            .annotate(stock=Coalesce(Sum("lots__quantite"), 0))
            .filter(stock__lte=F("seuil_alerte"))
            .count()
        )
        perimes = LotStock.objects.filter(
            quantite__gt=0, date_peremption__lt=aujourd_hui
        ).count()
        proches = LotStock.objects.filter(
            quantite__gt=0,
            date_peremption__gte=aujourd_hui,
            date_peremption__lte=limite,
        ).count()
        alertes = stocks_faibles + perimes + proches
    return {
        "pharmacie_nom": settings.PHARMACIE_NOM,
        "pharmacie_adresse": settings.PHARMACIE_ADRESSE,
        "pharmacie_telephone": settings.PHARMACIE_TELEPHONE,
        "pharmacie_email": settings.PHARMACIE_EMAIL,
        "pharmacie_nif": settings.PHARMACIE_NIF,
        "pharmacie_stat": settings.PHARMACIE_STAT,
        "alertes_globales": alertes,
    }
