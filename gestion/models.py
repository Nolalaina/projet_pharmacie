import secrets
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone

from .validators import valider_taille_image


def generer_numero(prefixe):
    horodatage = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    alea = secrets.token_hex(2).upper()
    return f"{prefixe}-{horodatage}-{alea}"


def numero_commande():
    return generer_numero("CA")


def numero_reception():
    return generer_numero("RE")


def numero_vente():
    return generer_numero("VE")


class Utilisateur(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrateur"
        PHARMACIEN = "PHARMACIEN", "Pharmacien responsable"
        GESTIONNAIRE = "GESTIONNAIRE", "Gestionnaire de stock"
        CAISSIER = "CAISSIER", "Caissier"
        RESPONSABLE = "RESPONSABLE", "Responsable de gestion"

    role = models.CharField(
        "rôle", max_length=20, choices=Role.choices, default=Role.CAISSIER
    )
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    cree_le = models.DateTimeField("créé le", auto_now_add=True)

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["username"]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def nom_complet(self):
        return self.get_full_name() or self.username

    @property
    def est_admin(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def peut_gerer_utilisateurs(self):
        return self.est_admin

    @property
    def peut_gerer_catalogue(self):
        return self.est_admin or self.role in {
            self.Role.PHARMACIEN,
            self.Role.GESTIONNAIRE,
        }

    @property
    def peut_gerer_achats(self):
        return self.est_admin or self.role in {
            self.Role.PHARMACIEN,
            self.Role.GESTIONNAIRE,
        }

    @property
    def peut_vendre(self):
        return self.est_admin or self.role in {
            self.Role.PHARMACIEN,
            self.Role.CAISSIER,
        }

    @property
    def peut_voir_rapports(self):
        return self.est_admin or self.role in {
            self.Role.PHARMACIEN,
            self.Role.RESPONSABLE,
        }


class JournalAudit(models.Model):
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="utilisateur",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journal",
    )
    action = models.CharField("action", max_length=120)
    modele = models.CharField("modèle", max_length=80, blank=True)
    objet_id = models.CharField("identifiant objet", max_length=64, blank=True)
    details = models.TextField("détails", blank=True)
    adresse_ip = models.GenericIPAddressField("adresse IP", null=True, blank=True)
    date = models.DateTimeField("date", auto_now_add=True)

    class Meta:
        verbose_name = "journal d'audit"
        verbose_name_plural = "journal d'audit"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date:%d/%m/%Y %H:%M} - {self.action}"


def journaliser(request, action, modele="", objet_id="", details=""):
    utilisateur = getattr(request, "user", None)
    adresse_ip = None
    if request is not None:
        adresse_ip = (
            request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR")
        )
    JournalAudit.objects.create(
        utilisateur=utilisateur if getattr(utilisateur, "is_authenticated", False) else None,
        action=action,
        modele=modele,
        objet_id=str(objet_id),
        details=details,
        adresse_ip=adresse_ip,
    )


class Categorie(models.Model):
    nom = models.CharField("nom", max_length=120, unique=True)
    description = models.TextField("description", blank=True)
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"
        ordering = ["nom"]

    def __str__(self):
        return self.nom

    @property
    def peut_supprimer(self):
        return not self.medicaments.exists()

    def supprimer(self):
        if not self.peut_supprimer:
            raise ValidationError(
                "Cette catégorie est utilisée par des médicaments et ne peut pas être supprimée."
            )
        self.delete()


class Fournisseur(models.Model):
    class Statut(models.TextChoices):
        ACTIF = "ACTIF", "Actif"
        INACTIF = "INACTIF", "Inactif"

    raison_sociale = models.CharField("raison sociale", max_length=180)
    adresse = models.TextField("adresse", blank=True)
    telephone = models.CharField("téléphone", max_length=40, blank=True)
    email = models.EmailField("adresse e-mail", blank=True)
    numero_fiscal = models.CharField("numéro fiscal", max_length=60, blank=True)
    contact_principal = models.CharField("contact principal", max_length=120, blank=True)
    statut = models.CharField(
        "statut", max_length=10, choices=Statut.choices, default=Statut.ACTIF
    )
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "fournisseur"
        verbose_name_plural = "fournisseurs"
        ordering = ["raison_sociale"]

    def __str__(self):
        return self.raison_sociale

    @property
    def est_actif(self):
        return self.statut == self.Statut.ACTIF

    @property
    def total_achats(self):
        return (
            self.commandes.filter(statut=CommandeAchat.Statut.RECEPTIONNEE).aggregate(
                total=models.Sum(
                    models.F("lignes__quantite_recue")
                    * models.F("lignes__prix_achat"),
                    output_field=models.DecimalField(max_digits=14, decimal_places=2),
                )
            )["total"]
            or Decimal("0.00")
        )

    def desactiver(self):
        self.statut = self.Statut.INACTIF
        self.save(update_fields=["statut"])

    def get_absolute_url(self):
        return reverse("gestion:fournisseur_detail", args=[self.pk])


class Client(models.Model):
    class Statut(models.TextChoices):
        ACTIF = "ACTIF", "Actif"
        INACTIF = "INACTIF", "Inactif"

    nom = models.CharField("nom", max_length=180, blank=True)
    telephone = models.CharField("téléphone", max_length=40, blank=True)
    email = models.EmailField("adresse e-mail", blank=True)
    adresse = models.TextField("adresse", blank=True)
    statut = models.CharField(
        "statut", max_length=10, choices=Statut.choices, default=Statut.ACTIF
    )
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "client"
        verbose_name_plural = "clients"
        ordering = ["nom"]

    def __str__(self):
        return self.nom or "Client comptoir"

    @property
    def nom_affichage(self):
        return self.nom or "Client comptoir"

    def get_absolute_url(self):
        return reverse("gestion:client_detail", args=[self.pk])


class Medicament(models.Model):
    class Statut(models.TextChoices):
        ACTIF = "ACTIF", "Actif"
        ARCHIVE = "ARCHIVE", "Archivé"

    nom_commercial = models.CharField("nom commercial", max_length=180)
    denomination_generique = models.CharField(
        "dénomination générique", max_length=180, blank=True
    )
    categorie = models.ForeignKey(
        Categorie,
        verbose_name="catégorie",
        on_delete=models.PROTECT,
        related_name="medicaments",
    )
    forme_pharmaceutique = models.CharField(
        "forme pharmaceutique", max_length=80, blank=True
    )
    dosage = models.CharField("dosage", max_length=80, blank=True)
    laboratoire = models.CharField("laboratoire", max_length=160, blank=True)
    code_barres = models.CharField(
        "code-barres", max_length=80, unique=True, null=True, blank=True
    )
    photo = models.ImageField(
        "photo",
        upload_to="medicaments/%Y/%m/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            valider_taille_image,
        ],
    )
    prix_achat = models.DecimalField(
        "prix d'achat",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    prix_vente = models.DecimalField(
        "prix de vente",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    seuil_alerte = models.PositiveIntegerField("seuil d'alerte", default=10)
    statut = models.CharField(
        "statut", max_length=10, choices=Statut.choices, default=Statut.ACTIF
    )
    date_creation = models.DateTimeField("date de création", auto_now_add=True)
    date_modification = models.DateTimeField("date de modification", auto_now=True)

    class Meta:
        verbose_name = "médicament"
        verbose_name_plural = "médicaments"
        ordering = ["nom_commercial"]
        indexes = [
            models.Index(fields=["nom_commercial"]),
            models.Index(fields=["code_barres"]),
        ]

    def __str__(self):
        details = " ".join(v for v in [self.dosage, self.forme_pharmaceutique] if v)
        return f"{self.nom_commercial} {details}".strip()

    def clean(self):
        if self.prix_achat is not None and self.prix_achat <= 0:
            raise ValidationError({"prix_achat": "Le prix d'achat doit être positif."})
        if self.prix_vente is not None and self.prix_vente <= 0:
            raise ValidationError({"prix_vente": "Le prix de vente doit être positif."})
        if self.code_barres == "":
            self.code_barres = None

    def save(self, *args, **kwargs):
        if self.code_barres == "":
            self.code_barres = None
        super().save(*args, **kwargs)

    @property
    def stock_total(self):
        return self.lots.aggregate(total=models.Sum("quantite"))["total"] or 0

    @property
    def stock_vendable(self):
        return (
            self.lots.filter(
                quantite__gt=0,
                bloque=False,
                date_peremption__gte=timezone.localdate(),
            ).aggregate(total=models.Sum("quantite"))["total"]
            or 0
        )

    @property
    def est_stock_faible(self):
        return self.statut == self.Statut.ACTIF and self.stock_total <= self.seuil_alerte

    @property
    def est_en_rupture(self):
        return self.statut == self.Statut.ACTIF and self.stock_vendable <= 0

    @property
    def valeur_stock(self):
        return (self.prix_achat or Decimal("0.00")) * self.stock_total

    def lots_vendables(self):
        return self.lots.filter(
            quantite__gt=0,
            bloque=False,
            date_peremption__gte=timezone.localdate(),
        ).order_by("date_peremption", "date_reception")

    def archiver(self):
        self.statut = self.Statut.ARCHIVE
        self.save(update_fields=["statut", "date_modification"])

    def supprimer_ou_archiver(self):
        reference = (
            self.lignes_vente.exists()
            or self.lignes_achat.exists()
            or self.mouvements.exists()
            or self.lots.exists()
        )
        if reference:
            self.archiver()
            return False
        self.delete()
        return True

    def get_absolute_url(self):
        return reverse("gestion:medicament_detail", args=[self.pk])


class LotStock(models.Model):
    medicament = models.ForeignKey(
        Medicament,
        verbose_name="médicament",
        on_delete=models.PROTECT,
        related_name="lots",
    )
    numero_lot = models.CharField("numéro de lot", max_length=80)
    date_peremption = models.DateField("date de péremption")
    quantite = models.PositiveIntegerField("quantité disponible", default=0)
    quantite_recue = models.PositiveIntegerField("quantité reçue", default=0)
    date_reception = models.DateField("date de réception", default=timezone.localdate)
    bloque = models.BooleanField("bloqué", default=False)
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "lot de stock"
        verbose_name_plural = "lots de stock"
        ordering = ["date_peremption", "numero_lot"]
        constraints = [
            models.UniqueConstraint(
                fields=["medicament", "numero_lot", "date_peremption"],
                name="lot_unique_par_medicament",
            )
        ]

    def __str__(self):
        return f"{self.medicament.nom_commercial} - lot {self.numero_lot}"

    @property
    def perime(self):
        return self.date_peremption < timezone.localdate()

    @property
    def jours_avant_peremption(self):
        return (self.date_peremption - timezone.localdate()).days

    @property
    def proche_peremption(self):
        return (
            not self.perime
            and self.jours_avant_peremption <= settings.SEUIL_PEREMPTION_JOURS
        )

    @property
    def est_vendable(self):
        return self.quantite > 0 and not self.bloque and not self.perime

    @property
    def valeur_stock(self):
        return self.medicament.prix_achat * self.quantite


class MouvementStock(models.Model):
    class Type(models.TextChoices):
        ENTREE = "ENTREE", "Entrée (réception)"
        SORTIE = "SORTIE", "Sortie (vente)"
        RETOUR = "RETOUR", "Retour / réintégration"
        CORRECTION = "CORRECTION", "Correction d'inventaire"
        PERTE = "PERTE", "Perte / destruction"

    medicament = models.ForeignKey(
        Medicament,
        verbose_name="médicament",
        on_delete=models.PROTECT,
        related_name="mouvements",
    )
    lot = models.ForeignKey(
        LotStock,
        verbose_name="lot",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="mouvements",
    )
    type = models.CharField("type", max_length=12, choices=Type.choices)
    quantite = models.IntegerField("quantité (+ entrée / - sortie)")
    stock_apres = models.IntegerField("stock après mouvement", null=True, blank=True)
    reference = models.CharField("référence", max_length=120, blank=True)
    motif = models.TextField("motif", blank=True)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="utilisateur",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mouvements",
    )
    date = models.DateTimeField("date", auto_now_add=True)

    class Meta:
        verbose_name = "mouvement de stock"
        verbose_name_plural = "mouvements de stock"
        ordering = ["-date"]
        indexes = [models.Index(fields=["type", "date"])]

    def __str__(self):
        return f"{self.get_type_display()} {self.quantite:+d} - {self.medicament}"


class CommandeAchat(models.Model):
    class Statut(models.TextChoices):
        BROUILLON = "BROUILLON", "Brouillon"
        COMMANDEE = "COMMANDEE", "Commandée"
        PARTIELLE = "PARTIELLE", "Partiellement réceptionnée"
        RECEPTIONNEE = "RECEPTIONNEE", "Entièrement réceptionnée"
        ANNULEE = "ANNULEE", "Annulée"

    numero = models.CharField(
        "numéro", max_length=40, unique=True, default=numero_commande, editable=False
    )
    fournisseur = models.ForeignKey(
        Fournisseur,
        verbose_name="fournisseur",
        on_delete=models.PROTECT,
        related_name="commandes",
    )
    statut = models.CharField(
        "statut", max_length=20, choices=Statut.choices, default=Statut.BROUILLON
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="créée par",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commandes",
    )
    date_creation = models.DateTimeField("date de création", auto_now_add=True)
    date_commande = models.DateTimeField("date de commande", null=True, blank=True)
    notes = models.TextField("notes", blank=True)

    class Meta:
        verbose_name = "commande d'achat"
        verbose_name_plural = "commandes d'achat"
        ordering = ["-date_creation"]

    def __str__(self):
        return f"{self.numero} - {self.fournisseur}"

    @property
    def total(self):
        return sum((ligne.sous_total for ligne in self.lignes.all()), Decimal("0.00"))

    @property
    def reste_a_recevoir(self):
        return sum(
            max(ligne.quantite_commandee - ligne.quantite_recue, 0)
            for ligne in self.lignes.all()
        )

    @property
    def modifiable(self):
        return self.statut == self.Statut.BROUILLON

    @property
    def receptionnable(self):
        return (
            self.statut in {self.Statut.COMMANDEE, self.Statut.PARTIELLE}
            and self.reste_a_recevoir > 0
        )

    def valider(self):
        if self.statut != self.Statut.BROUILLON:
            raise ValidationError("Seule une commande en brouillon peut être validée.")
        if not self.lignes.exists():
            raise ValidationError("Une commande doit contenir au moins une ligne.")
        self.statut = self.Statut.COMMANDEE
        self.date_commande = timezone.now()
        self.save(update_fields=["statut", "date_commande"])

    def annuler(self):
        if self.statut == self.Statut.RECEPTIONNEE:
            raise ValidationError(
                "Une commande entièrement réceptionnée ne peut pas être annulée."
            )
        if self.statut == self.Statut.ANNULEE:
            raise ValidationError("Cette commande est déjà annulée.")
        self.statut = self.Statut.ANNULEE
        self.save(update_fields=["statut"])

    def maj_statut_reception(self):
        if self.statut in {self.Statut.ANNULEE, self.Statut.BROUILLON}:
            return
        if self.reste_a_recevoir <= 0:
            nouveau = self.Statut.RECEPTIONNEE
        elif self.lignes.filter(quantite_recue__gt=0).exists():
            nouveau = self.Statut.PARTIELLE
        else:
            nouveau = self.Statut.COMMANDEE
        if nouveau != self.statut:
            self.statut = nouveau
            self.save(update_fields=["statut"])


class LigneAchat(models.Model):
    commande = models.ForeignKey(
        CommandeAchat,
        verbose_name="commande",
        on_delete=models.CASCADE,
        related_name="lignes",
    )
    medicament = models.ForeignKey(
        Medicament,
        verbose_name="médicament",
        on_delete=models.PROTECT,
        related_name="lignes_achat",
    )
    quantite_commandee = models.PositiveIntegerField(
        "quantité commandée", validators=[MinValueValidator(1)]
    )
    quantite_recue = models.PositiveIntegerField("quantité reçue", default=0)
    prix_achat = models.DecimalField(
        "prix d'achat unitaire",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        verbose_name = "ligne de commande"
        verbose_name_plural = "lignes de commande"
        ordering = ["id"]

    def __str__(self):
        return f"{self.medicament} x {self.quantite_commandee}"

    @property
    def sous_total(self):
        return self.prix_achat * self.quantite_commandee

    @property
    def reste_a_recevoir(self):
        return max(self.quantite_commandee - self.quantite_recue, 0)

    def clean(self):
        if self.quantite_recue > self.quantite_commandee:
            raise ValidationError(
                {"quantite_recue": "La quantité reçue dépasse la quantité commandée."}
            )


class ReceptionAchat(models.Model):
    numero = models.CharField(
        "numéro", max_length=40, unique=True, default=numero_reception, editable=False
    )
    commande = models.ForeignKey(
        CommandeAchat,
        verbose_name="commande",
        on_delete=models.PROTECT,
        related_name="receptions",
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="réceptionnée par",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receptions",
    )
    date_reception = models.DateField("date de réception", default=timezone.localdate)
    notes = models.TextField("notes", blank=True)
    validee = models.BooleanField("validée", default=False)
    date_validation = models.DateTimeField("date de validation", null=True, blank=True)
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "réception d'achat"
        verbose_name_plural = "réceptions d'achat"
        ordering = ["-date_creation"]

    def __str__(self):
        return f"{self.numero} - {self.commande.numero}"

    @property
    def total(self):
        return sum(
            (ligne.quantite * ligne.ligne_achat.prix_achat for ligne in self.lignes.all()),
            Decimal("0.00"),
        )

    @transaction.atomic
    def valider(self, utilisateur=None):
        if self.validee:
            raise ValidationError("Cette réception a déjà été validée.")
        commande = CommandeAchat.objects.select_for_update().get(pk=self.commande_id)
        if commande.statut in {
            CommandeAchat.Statut.BROUILLON,
            CommandeAchat.Statut.ANNULEE,
        }:
            raise ValidationError(
                "La commande doit être commandée avant de pouvoir être réceptionnée."
            )
        lignes = list(self.lignes.select_related("ligne_achat__medicament"))
        if not lignes:
            raise ValidationError("La réception ne contient aucune ligne.")
        for ligne in lignes:
            if ligne.quantite <= 0:
                raise ValidationError("Les quantités reçues doivent être positives.")
            if not ligne.numero_lot or not ligne.date_peremption:
                raise ValidationError(
                    "Chaque ligne de réception doit indiquer un lot et une date de péremption."
                )
            ligne_achat = LigneAchat.objects.select_for_update().get(
                pk=ligne.ligne_achat_id
            )
            if ligne.quantite > ligne_achat.reste_a_recevoir:
                raise ValidationError(
                    f"La quantité reçue pour {ligne_achat.medicament} dépasse le reste à recevoir."
                )
            lot = (
                LotStock.objects.select_for_update()
                .filter(
                    medicament=ligne_achat.medicament,
                    numero_lot=ligne.numero_lot,
                    date_peremption=ligne.date_peremption,
                )
                .first()
            )
            if lot is None:
                lot = LotStock(
                    medicament=ligne_achat.medicament,
                    numero_lot=ligne.numero_lot,
                    date_peremption=ligne.date_peremption,
                    quantite=0,
                    quantite_recue=0,
                    date_reception=self.date_reception,
                )
            lot.quantite += ligne.quantite
            lot.quantite_recue += ligne.quantite
            lot.save()
            ligne_achat.quantite_recue += ligne.quantite
            ligne_achat.save(update_fields=["quantite_recue"])
            MouvementStock.objects.create(
                medicament=ligne_achat.medicament,
                lot=lot,
                type=MouvementStock.Type.ENTREE,
                quantite=ligne.quantite,
                stock_apres=lot.quantite,
                reference=f"Réception {self.numero}",
                motif=f"Réception de la commande {commande.numero}",
                utilisateur=utilisateur,
            )
        self.validee = True
        self.date_validation = timezone.now()
        self.save(update_fields=["validee", "date_validation"])
        commande.maj_statut_reception()
        return self


class LigneReception(models.Model):
    reception = models.ForeignKey(
        ReceptionAchat,
        verbose_name="réception",
        on_delete=models.CASCADE,
        related_name="lignes",
    )
    ligne_achat = models.ForeignKey(
        LigneAchat,
        verbose_name="ligne de commande",
        on_delete=models.PROTECT,
        related_name="receptions",
    )
    quantite = models.PositiveIntegerField(
        "quantité reçue", validators=[MinValueValidator(1)]
    )
    numero_lot = models.CharField("numéro de lot", max_length=80)
    date_peremption = models.DateField("date de péremption")

    class Meta:
        verbose_name = "ligne de réception"
        verbose_name_plural = "lignes de réception"
        ordering = ["id"]

    def __str__(self):
        return f"{self.ligne_achat.medicament} x {self.quantite}"


class Vente(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente de validation"
        VALIDEE = "VALIDEE", "Validée"
        ANNULEE = "ANNULEE", "Annulée"

    numero = models.CharField(
        "numéro", max_length=40, unique=True, default=numero_vente, editable=False
    )
    client = models.ForeignKey(
        Client,
        verbose_name="client",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ventes",
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="vendeur",
        on_delete=models.PROTECT,
        related_name="ventes",
    )
    statut = models.CharField(
        "statut", max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE
    )
    remise = models.DecimalField(
        "remise",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    motif_annulation = models.TextField("motif d'annulation", blank=True)
    annulee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="annulée par",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventes_annulees",
    )
    date_vente = models.DateTimeField("date de vente", auto_now_add=True)
    date_validation = models.DateTimeField("date de validation", null=True, blank=True)
    date_annulation = models.DateTimeField("date d'annulation", null=True, blank=True)

    class Meta:
        verbose_name = "vente"
        verbose_name_plural = "ventes"
        ordering = ["-date_vente"]
        indexes = [models.Index(fields=["statut", "date_vente"])]

    def __str__(self):
        return f"{self.numero} - {self.total} Ar"

    @property
    def sous_total(self):
        return sum((ligne.sous_total for ligne in self.lignes.all()), Decimal("0.00"))

    @property
    def total(self):
        return max(self.sous_total - self.remise, Decimal("0.00"))

    @property
    def montant_confirme(self):
        return (
            self.paiements.filter(statut=Paiement.Statut.CONFIRME).aggregate(
                total=models.Sum("montant")
            )["total"]
            or Decimal("0.00")
        )

    @property
    def reste_a_payer(self):
        return max(self.total - self.montant_confirme, Decimal("0.00"))

    @transaction.atomic
    def valider(self, utilisateur=None):
        if self.statut == self.Statut.VALIDEE:
            raise ValidationError("Cette vente est déjà validée.")
        if self.statut == self.Statut.ANNULEE:
            raise ValidationError("Une vente annulée ne peut pas être validée.")
        lignes = list(self.lignes.select_related("lot", "medicament"))
        if not lignes:
            raise ValidationError("Une vente doit contenir au moins une ligne.")
        for ligne in lignes:
            if ligne.quantite <= 0:
                raise ValidationError("La quantité vendue doit être positive.")
            lot = LotStock.objects.select_for_update().get(pk=ligne.lot_id)
            if lot.medicament_id != ligne.medicament_id:
                raise ValidationError("Le lot ne correspond pas au médicament.")
            if lot.bloque:
                raise ValidationError(f"Le lot {lot.numero_lot} est bloqué.")
            if lot.perime:
                raise ValidationError(f"Le lot {lot.numero_lot} est périmé.")
            if ligne.quantite > lot.quantite:
                raise ValidationError(
                    f"Stock insuffisant pour {ligne.medicament} (lot {lot.numero_lot})."
                )
        for ligne in lignes:
            lot = LotStock.objects.select_for_update().get(pk=ligne.lot_id)
            lot.quantite -= ligne.quantite
            lot.save(update_fields=["quantite"])
            MouvementStock.objects.create(
                medicament=ligne.medicament,
                lot=lot,
                type=MouvementStock.Type.SORTIE,
                quantite=-ligne.quantite,
                stock_apres=lot.quantite,
                reference=f"Vente {self.numero}",
                motif="Sortie de stock pour vente",
                utilisateur=utilisateur or self.utilisateur,
            )
        self.statut = self.Statut.VALIDEE
        self.date_validation = timezone.now()
        self.save(update_fields=["statut", "date_validation"])
        return self

    @transaction.atomic
    def annuler(self, motif, utilisateur=None):
        if self.statut == self.Statut.ANNULEE:
            raise ValidationError("Cette vente est déjà annulée.")
        if self.statut != self.Statut.VALIDEE:
            raise ValidationError("Seule une vente validée peut être annulée.")
        if not motif:
            raise ValidationError("Le motif d'annulation est obligatoire.")
        for ligne in self.lignes.select_related("lot"):
            lot = LotStock.objects.select_for_update().get(pk=ligne.lot_id)
            lot.quantite += ligne.quantite
            lot.save(update_fields=["quantite"])
            MouvementStock.objects.create(
                medicament=ligne.medicament,
                lot=lot,
                type=MouvementStock.Type.RETOUR,
                quantite=ligne.quantite,
                stock_apres=lot.quantite,
                reference=f"Annulation vente {self.numero}",
                motif=motif,
                utilisateur=utilisateur,
            )
        self.statut = self.Statut.ANNULEE
        self.motif_annulation = motif
        self.annulee_par = utilisateur
        self.date_annulation = timezone.now()
        self.save(
            update_fields=[
                "statut",
                "motif_annulation",
                "annulee_par",
                "date_annulation",
            ]
        )
        for paiement in self.paiements.all():
            paiement.statut = Paiement.Statut.REMBOURSE
            paiement.save(update_fields=["statut"])
        return self


class LigneVente(models.Model):
    vente = models.ForeignKey(
        Vente,
        verbose_name="vente",
        on_delete=models.CASCADE,
        related_name="lignes",
    )
    medicament = models.ForeignKey(
        Medicament,
        verbose_name="médicament",
        on_delete=models.PROTECT,
        related_name="lignes_vente",
    )
    lot = models.ForeignKey(
        LotStock,
        verbose_name="lot",
        on_delete=models.PROTECT,
        related_name="lignes_vente",
    )
    quantite = models.PositiveIntegerField(
        "quantité", validators=[MinValueValidator(1)]
    )
    prix_unitaire = models.DecimalField(
        "prix unitaire appliqué",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        verbose_name = "ligne de vente"
        verbose_name_plural = "lignes de vente"
        ordering = ["id"]

    def __str__(self):
        return f"{self.medicament} x {self.quantite}"

    @property
    def sous_total(self):
        return self.prix_unitaire * self.quantite

    @property
    def quantite_retournee(self):
        return (
            self.retours.filter(retour__traite=True).aggregate(
                total=models.Sum("quantite")
            )["total"]
            or 0
        )

    @property
    def quantite_retournable(self):
        return max(self.quantite - self.quantite_retournee, 0)

    def clean(self):
        if self.lot_id and self.medicament_id:
            if self.lot.medicament_id != self.medicament_id:
                raise ValidationError(
                    "Le lot sélectionné n'appartient pas à ce médicament."
                )


class Paiement(models.Model):
    class Mode(models.TextChoices):
        ESPECES = "ESPECES", "Espèces"
        MOBILE_MONEY = "MOBILE_MONEY", "Mobile money"
        CARTE = "CARTE", "Carte bancaire"

    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        CONFIRME = "CONFIRME", "Confirmé"
        ECHEC = "ECHEC", "Échec"
        REMBOURSE = "REMBOURSE", "Remboursé"

    vente = models.ForeignKey(
        Vente,
        verbose_name="vente",
        on_delete=models.CASCADE,
        related_name="paiements",
    )
    montant = models.DecimalField(
        "montant",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    mode = models.CharField("mode", max_length=20, choices=Mode.choices)
    statut = models.CharField(
        "statut", max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE
    )
    reference = models.CharField("référence", max_length=120, blank=True)
    confirme_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="confirmé par",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paiements_confirmes",
    )
    date_paiement = models.DateTimeField("date de paiement", auto_now_add=True)
    date_confirmation = models.DateTimeField("date de confirmation", null=True, blank=True)

    class Meta:
        verbose_name = "paiement"
        verbose_name_plural = "paiements"
        ordering = ["-date_paiement"]

    def __str__(self):
        return f"{self.get_mode_display()} - {self.montant} Ar ({self.get_statut_display()})"

    @property
    def est_confirme(self):
        return self.statut == self.Statut.CONFIRME

    def confirmer(self, utilisateur=None):
        if self.statut == self.Statut.CONFIRME:
            raise ValidationError("Ce paiement est déjà confirmé.")
        if self.statut == self.Statut.REMBOURSE:
            raise ValidationError("Ce paiement a été remboursé.")
        self.statut = self.Statut.CONFIRME
        self.confirme_par = utilisateur
        self.date_confirmation = timezone.now()
        self.save(update_fields=["statut", "confirme_par", "date_confirmation"])


class RetourVente(models.Model):
    vente = models.ForeignKey(
        Vente,
        verbose_name="vente d'origine",
        on_delete=models.PROTECT,
        related_name="retours",
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="enregistré par",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="retours",
    )
    motif = models.TextField("motif")
    remboursement = models.DecimalField(
        "remboursement",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    remis_en_stock = models.BooleanField("remis en stock", default=False)
    traite = models.BooleanField("traité", default=False)
    date_retour = models.DateTimeField("date du retour", auto_now_add=True)
    date_traitement = models.DateTimeField("date de traitement", null=True, blank=True)

    class Meta:
        verbose_name = "retour de vente"
        verbose_name_plural = "retours de vente"
        ordering = ["-date_retour"]

    def __str__(self):
        return f"Retour {self.vente.numero}"

    @property
    def total(self):
        return sum((ligne.sous_total for ligne in self.lignes.all()), Decimal("0.00"))

    @transaction.atomic
    def traiter(self, utilisateur=None):
        if self.traite:
            raise ValidationError("Ce retour a déjà été traité.")
        if self.vente.statut != Vente.Statut.VALIDEE:
            raise ValidationError("Le retour concerne une vente non validée.")
        lignes = list(self.lignes.select_related("ligne_vente__lot"))
        if not lignes:
            raise ValidationError("Le retour ne contient aucune ligne.")
        for ligne in lignes:
            if ligne.quantite <= 0:
                raise ValidationError("La quantité retournée doit être positive.")
            if ligne.quantite > ligne.ligne_vente.quantite_retournable:
                raise ValidationError(
                    f"Quantité retournée supérieure à la quantité vendue pour "
                    f"{ligne.ligne_vente.medicament}."
                )
            if self.remis_en_stock:
                lot = LotStock.objects.select_for_update().get(
                    pk=ligne.ligne_vente.lot_id
                )
                if lot.bloque or lot.perime:
                    raise ValidationError(
                        f"Le lot {lot.numero_lot} n'est pas éligible à la remise en stock."
                    )
                lot.quantite += ligne.quantite
                lot.save(update_fields=["quantite"])
                MouvementStock.objects.create(
                    medicament=ligne.ligne_vente.medicament,
                    lot=lot,
                    type=MouvementStock.Type.RETOUR,
                    quantite=ligne.quantite,
                    stock_apres=lot.quantite,
                    reference=f"Retour {self.pk}",
                    motif=self.motif,
                    utilisateur=utilisateur,
                )
        self.traite = True
        self.date_traitement = timezone.now()
        self.save(update_fields=["traite", "date_traitement"])
        return self


class LigneRetour(models.Model):
    retour = models.ForeignKey(
        RetourVente,
        verbose_name="retour",
        on_delete=models.CASCADE,
        related_name="lignes",
    )
    ligne_vente = models.ForeignKey(
        LigneVente,
        verbose_name="ligne de vente",
        on_delete=models.PROTECT,
        related_name="retours",
    )
    quantite = models.PositiveIntegerField(
        "quantité retournée", validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = "ligne de retour"
        verbose_name_plural = "lignes de retour"
        ordering = ["id"]

    def __str__(self):
        return f"{self.ligne_vente.medicament} x {self.quantite}"

    @property
    def sous_total(self):
        return self.ligne_vente.prix_unitaire * self.quantite
