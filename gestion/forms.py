
from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    Categorie,
    Client,
    CommandeAchat,
    Fournisseur,
    LigneAchat,
    LigneVente,
    LotStock,
    Medicament,
    Paiement,
    Utilisateur,
)


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            widget = champ.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")
            if isinstance(widget, (forms.DateInput, forms.DateTimeInput)):
                widget.attrs.setdefault("type", "date")


class ConnexionForm(BootstrapMixin, AuthenticationForm):
    username = forms.CharField(
        label="Nom d'utilisateur",
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class UtilisateurCreationForm(BootstrapMixin, UserCreationForm):
    class Meta:
        model = Utilisateur
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "telephone",
            "role",
            "is_active",
        )


class UtilisateurModificationForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Utilisateur
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "telephone",
            "role",
            "is_active",
        )


class MotDePasseForm(BootstrapMixin, PasswordChangeForm):
    pass


class ReinitialiserMotDePasseForm(BootstrapMixin, SetPasswordForm):
    pass


class CategorieForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ("nom", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class MedicamentForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Medicament
        fields = (
            "nom_commercial",
            "denomination_generique",
            "categorie",
            "forme_pharmaceutique",
            "dosage",
            "laboratoire",
            "code_barres",
            "photo",
            "prix_achat",
            "prix_vente",
            "seuil_alerte",
            "statut",
        )
        widgets = {
            "photo": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "prix_achat": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "prix_vente": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
        }

    def clean_code_barres(self):
        valeur = (self.cleaned_data.get("code_barres") or "").strip()
        return valeur or None


class FournisseurForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = (
            "raison_sociale",
            "adresse",
            "telephone",
            "email",
            "numero_fiscal",
            "contact_principal",
            "statut",
        )
        widgets = {"adresse": forms.Textarea(attrs={"rows": 2})}


class ClientForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Client
        fields = ("nom", "telephone", "email", "adresse", "statut")
        widgets = {"adresse": forms.Textarea(attrs={"rows": 2})}


class CommandeAchatForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = CommandeAchat
        fields = ("fournisseur", "notes")
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fournisseur"].queryset = Fournisseur.objects.filter(
            statut=Fournisseur.Statut.ACTIF
        )


class LigneAchatForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = LigneAchat
        fields = ("medicament", "quantite_commandee", "prix_achat")
        widgets = {
            "quantite_commandee": forms.NumberInput(attrs={"min": "1"}),
            "prix_achat": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["medicament"].queryset = Medicament.objects.filter(
            statut=Medicament.Statut.ACTIF
        )


class LotSelect(forms.Select):
    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        instance = getattr(value, "instance", None)
        if instance is not None:
            option["attrs"]["data-prix"] = str(instance.medicament.prix_vente)
            option["attrs"]["data-stock"] = str(instance.quantite)
            option["attrs"]["data-code"] = instance.medicament.code_barres or ""
        return option


class LotChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return (
            f"{obj.medicament.nom_commercial} — lot {obj.numero_lot} — "
            f"exp. {obj.date_peremption:%d/%m/%Y} — "
            f"{obj.quantite} dispo — {obj.medicament.prix_vente} Ar"
        )


class LigneVenteForm(BootstrapMixin, forms.ModelForm):
    lot = LotChoiceField(
        queryset=LotStock.objects.none(),
        label="Lot / produit",
        empty_label="— Choisir un lot —",
        widget=LotSelect,
    )

    class Meta:
        model = LigneVente
        fields = ("lot", "quantite")
        widgets = {"quantite": forms.NumberInput(attrs={"min": "1"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aujourd_hui = timezone.localdate()
        self.fields["lot"].queryset = (
            LotStock.objects.filter(
                quantite__gt=0,
                bloque=False,
                date_peremption__gte=aujourd_hui,
                medicament__statut=Medicament.Statut.ACTIF,
            )
            .select_related("medicament")
            .order_by("medicament__nom_commercial", "date_peremption")
        )

    def clean(self):
        cleaned = super().clean()
        lot = cleaned.get("lot")
        quantite = cleaned.get("quantite")
        if lot and quantite:
            if quantite > lot.quantite:
                self.add_error(
                    "quantite",
                    f"Stock insuffisant : {lot.quantite} unité(s) disponible(s) dans ce lot.",
                )
            if lot.perime:
                self.add_error("lot", "Ce lot est périmé.")
            if lot.bloque:
                self.add_error("lot", "Ce lot est bloqué.")
        return cleaned


class VenteForm(BootstrapMixin, forms.Form):
    client = forms.ModelChoiceField(
        queryset=Client.objects.filter(statut=Client.Statut.ACTIF),
        required=False,
        empty_label="Client comptoir (non identifié)",
        label="Client",
    )
    remise = forms.DecimalField(
        label="Remise (Ar)",
        min_value=0,
        initial=0,
        max_digits=12,
        decimal_places=2,
        required=False,
    )
    mode_paiement = forms.ChoiceField(
        label="Mode de paiement", choices=Paiement.Mode.choices
    )
    reference_paiement = forms.CharField(
        label="Référence du paiement",
        required=False,
        help_text="N° de transaction mobile money ou de carte.",
    )
    paiement_confirme = forms.BooleanField(
        label="Paiement électronique vérifié et confirmé",
        required=False,
        help_text="Obligatoire pour un paiement mobile money ou carte.",
    )

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get("mode_paiement")
        confirme = cleaned.get("paiement_confirme")
        if mode in {Paiement.Mode.MOBILE_MONEY, Paiement.Mode.CARTE} and not confirme:
            raise ValidationError(
                "Un paiement électronique doit être vérifié avant validation de la vente."
            )
        return cleaned


class RetourVenteForm(BootstrapMixin, forms.Form):
    motif = forms.CharField(
        label="Motif du retour", widget=forms.Textarea(attrs={"rows": 2})
    )
    remis_en_stock = forms.BooleanField(label="Réintégrer au stock", required=False)
    remboursement = forms.DecimalField(
        label="Montant remboursé (Ar)",
        min_value=0,
        max_digits=12,
        decimal_places=2,
        required=False,
        initial=0,
    )


class AjustementStockForm(BootstrapMixin, forms.Form):
    lot = forms.ModelChoiceField(
        queryset=LotStock.objects.select_related("medicament").all(),
        label="Lot",
    )
    nouvelle_quantite = forms.IntegerField(
        label="Quantité constatée", min_value=0
    )
    motif = forms.CharField(
        label="Motif de la correction",
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def clean(self):
        cleaned = super().clean()
        lot = cleaned.get("lot")
        nouvelle = cleaned.get("nouvelle_quantite")
        if lot and nouvelle is not None and nouvelle == lot.quantite:
            raise ValidationError("La quantité constatée est identique au stock actuel.")
        return cleaned


class PeriodeForm(BootstrapMixin, forms.Form):
    date_debut = forms.DateField(
        label="Du",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    date_fin = forms.DateField(
        label="Au",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aujourd_hui = timezone.localdate()
        self.fields["date_debut"].initial = aujourd_hui.replace(day=1)
        self.fields["date_fin"].initial = aujourd_hui

    def clean(self):
        cleaned = super().clean()
        debut = cleaned.get("date_debut")
        fin = cleaned.get("date_fin")
        if debut and fin and debut > fin:
            raise ValidationError("La date de début doit précéder la date de fin.")
        return cleaned
