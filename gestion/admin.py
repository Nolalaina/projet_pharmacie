from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import (
    Categorie,
    Client,
    CommandeAchat,
    Fournisseur,
    JournalAudit,
    LigneAchat,
    LigneReception,
    LigneRetour,
    LigneVente,
    LotStock,
    Medicament,
    MouvementStock,
    Paiement,
    ReceptionAchat,
    RetourVente,
    Utilisateur,
    Vente,
)


@admin.register(Utilisateur)
class UtilisateurAdmin(BaseUserAdmin):
    list_display = ("username", "nom_complet", "role", "telephone", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Pharmacie", {"fields": ("role", "telephone")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Pharmacie", {"fields": ("role", "telephone")}),
    )


class LigneAchatInline(admin.TabularInline):
    model = LigneAchat
    extra = 0


class LigneReceptionInline(admin.TabularInline):
    model = LigneReception
    extra = 0


class LigneVenteInline(admin.TabularInline):
    model = LigneVente
    extra = 0


class PaiementInline(admin.TabularInline):
    model = Paiement
    extra = 0


class LigneRetourInline(admin.TabularInline):
    model = LigneRetour
    extra = 0


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ("nom", "description")
    search_fields = ("nom",)


@admin.register(Medicament)
class MedicamentAdmin(admin.ModelAdmin):
    list_display = (
        "nom_commercial",
        "categorie",
        "dosage",
        "prix_vente",
        "stock_total",
        "seuil_alerte",
        "statut",
    )
    list_filter = ("statut", "categorie", "forme_pharmaceutique")
    search_fields = ("nom_commercial", "denomination_generique", "code_barres")
    readonly_fields = ("apercu_photo",)

    @admin.display(description="photo")
    def apercu_photo(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-height:120px" />', obj.photo.url
            )
        return "—"


@admin.register(LotStock)
class LotStockAdmin(admin.ModelAdmin):
    list_display = (
        "medicament",
        "numero_lot",
        "date_peremption",
        "quantite",
        "bloque",
    )
    list_filter = ("bloque", "date_peremption")
    search_fields = ("medicament__nom_commercial", "numero_lot")


@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "type",
        "medicament",
        "lot",
        "quantite",
        "stock_apres",
        "utilisateur",
    )
    list_filter = ("type", "date")
    search_fields = ("medicament__nom_commercial", "reference")
    readonly_fields = (
        "medicament",
        "lot",
        "type",
        "quantite",
        "stock_apres",
        "reference",
        "motif",
        "utilisateur",
        "date",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ("raison_sociale", "telephone", "email", "statut")
    list_filter = ("statut",)
    search_fields = ("raison_sociale", "telephone")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "email", "statut")
    list_filter = ("statut",)
    search_fields = ("nom", "telephone")


@admin.register(CommandeAchat)
class CommandeAchatAdmin(admin.ModelAdmin):
    list_display = ("numero", "fournisseur", "statut", "date_creation", "total")
    list_filter = ("statut", "fournisseur")
    search_fields = ("numero", "fournisseur__raison_sociale")
    inlines = [LigneAchatInline]
    readonly_fields = ("numero", "date_creation")


@admin.register(ReceptionAchat)
class ReceptionAchatAdmin(admin.ModelAdmin):
    list_display = ("numero", "commande", "date_reception", "validee")
    list_filter = ("validee", "date_reception")
    search_fields = ("numero", "commande__numero")
    inlines = [LigneReceptionInline]
    readonly_fields = ("numero", "date_creation", "date_validation")


@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = ("numero", "client", "utilisateur", "statut", "total", "date_vente")
    list_filter = ("statut", "date_vente")
    search_fields = ("numero", "client__nom")
    inlines = [LigneVenteInline, PaiementInline]
    readonly_fields = ("numero", "date_vente", "date_validation", "date_annulation")

    def has_delete_permission(self, request, obj=None):
        return obj is None or obj.statut != Vente.Statut.VALIDEE


@admin.register(RetourVente)
class RetourVenteAdmin(admin.ModelAdmin):
    list_display = ("vente", "motif", "remboursement", "remis_en_stock", "traite")
    list_filter = ("traite", "remis_en_stock")
    inlines = [LigneRetourInline]


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ("date", "utilisateur", "action", "modele", "objet_id")
    list_filter = ("modele", "date")
    search_fields = ("action", "details", "utilisateur__username")
    readonly_fields = tuple(
        field.name for field in JournalAudit._meta.fields
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
