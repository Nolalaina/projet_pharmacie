from datetime import datetime, time, timedelta
from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Coalesce
from django.forms import formset_factory, inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import (
    AjustementStockForm,
    CategorieForm,
    ClientForm,
    CommandeAchatForm,
    ConnexionForm,
    FournisseurForm,
    LigneAchatForm,
    LigneVenteForm,
    MedicamentForm,
    MotDePasseForm,
    PeriodeForm,
    ReinitialiserMotDePasseForm,
    RetourVenteForm,
    UtilisateurCreationForm,
    UtilisateurModificationForm,
    VenteForm,
)
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
    journaliser,
)
from .pdf import (
    pdf_bon_commande,
    pdf_bon_reception,
    pdf_facture,
    pdf_rapport_achats,
    pdf_rapport_peremptions,
    pdf_rapport_stock,
    pdf_rapport_ventes,
    pdf_recu,
)

ROLE = Utilisateur.Role
TOUS = tuple(ROLE.values)
CATALOGUE = (ROLE.PHARMACIEN, ROLE.GESTIONNAIRE)
ACHATS = (ROLE.PHARMACIEN, ROLE.GESTIONNAIRE)
GESTION_STOCK = (ROLE.PHARMACIEN, ROLE.GESTIONNAIRE)
VENTE = (ROLE.PHARMACIEN, ROLE.CAISSIER)
RAPPORTS = (ROLE.PHARMACIEN, ROLE.RESPONSABLE)

LigneAchatFormSet = inlineformset_factory(
    CommandeAchat, LigneAchat, form=LigneAchatForm, extra=4, can_delete=True
)
LigneVenteFormSet = formset_factory(LigneVenteForm, extra=4, can_delete=True)


class RoleRequisMixin(LoginRequiredMixin):
    roles_autorises = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (
            request.user.est_admin or request.user.role in self.roles_autorises
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def role_requis(*roles):
    def decorateur(vue):
        @login_required
        @wraps(vue)
        def protegee(request, *args, **kwargs):
            if not (request.user.est_admin or request.user.role in roles):
                raise PermissionDenied
            return vue(request, *args, **kwargs)

        return protegee

    return decorateur


class ConnexionView(LoginView):
    template_name = "gestion/connexion.html"
    authentication_form = ConnexionForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        journaliser(
            self.request,
            "Connexion",
            "Utilisateur",
            self.request.user.pk,
            f"Connexion de {self.request.user.username}",
        )
        messages.success(
            self.request, f"Bienvenue {self.request.user.nom_complet}."
        )
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Identifiants incorrects ou compte désactivé.")
        return super().form_invalid(form)


class DeconnexionView(LogoutView):
    next_page = reverse_lazy("gestion:connexion")

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            journaliser(
                request,
                "Déconnexion",
                "Utilisateur",
                request.user.pk,
                f"Déconnexion de {request.user.username}",
            )
        return super().post(request, *args, **kwargs)


class ModifierMotDePasseView(LoginRequiredMixin, PasswordChangeView):
    template_name = "gestion/mot_de_passe.html"
    form_class = MotDePasseForm
    success_url = reverse_lazy("gestion:tableau_bord")

    def form_valid(self, form):
        journaliser(
            self.request,
            "Modification du mot de passe",
            "Utilisateur",
            self.request.user.pk,
        )
        messages.success(self.request, "Votre mot de passe a été modifié.")
        return super().form_valid(form)


class TableauBordView(LoginRequiredMixin, View):
    def get(self, request):
        aujourd_hui = timezone.localdate()
        debut_jour = timezone.make_aware(datetime.combine(aujourd_hui, time.min))
        fin_jour = debut_jour + timedelta(days=1)
        debut_mois = aujourd_hui.replace(day=1)
        debut_30 = aujourd_hui - timedelta(days=30)

        ventes_jour = Vente.objects.filter(
            statut=Vente.Statut.VALIDEE,
            date_validation__gte=debut_jour,
            date_validation__lt=fin_jour,
        )
        montant_jour = sum((v.total for v in ventes_jour), Decimal("0.00"))

        medicaments_actifs = Medicament.objects.filter(
            statut=Medicament.Statut.ACTIF
        ).count()
        stocks_faibles = (
            Medicament.objects.filter(statut=Medicament.Statut.ACTIF)
            .annotate(stock=Coalesce(Sum("lots__quantite"), 0))
            .filter(stock__lte=F("seuil_alerte"))
            .order_by("stock")
        )
        limite = aujourd_hui + timedelta(days=settings.SEUIL_PEREMPTION_JOURS)
        lots_alerte = (
            LotStock.objects.filter(quantite__gt=0, date_peremption__lte=limite)
            .select_related("medicament")
            .order_by("date_peremption")
        )

        ventes_recentes = (
            Vente.objects.select_related("client", "utilisateur")
            .prefetch_related("lignes")
            .order_by("-date_vente")[:8]
        )

        top_produits = (
            LigneVente.objects.filter(
                vente__statut=Vente.Statut.VALIDEE,
                vente__date_validation__date__gte=debut_30,
            )
            .values("medicament__nom_commercial")
            .annotate(
                quantite_vendue=Sum("quantite"),
                chiffre=Sum(
                    ExpressionWrapper(
                        F("prix_unitaire") * F("quantite"),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ),
            )
            .order_by("-quantite_vendue")[:5]
        )

        serie = []
        maximum = 0
        for decalage in range(6, -1, -1):
            jour = aujourd_hui - timedelta(days=decalage)
            ventes = Vente.objects.filter(
                statut=Vente.Statut.VALIDEE, date_validation__date=jour
            )
            nombre = ventes.count()
            montant = sum((v.total for v in ventes), Decimal("0.00"))
            maximum = max(maximum, montant)
            serie.append(
                {
                    "jour": jour,
                    "nombre": nombre,
                    "montant": montant,
                }
            )
        for point in serie:
            point["largeur"] = (
                float(point["montant"] / maximum * 100) if maximum else 0
            )

        ca_mois = (
            LigneVente.objects.filter(
                vente__statut=Vente.Statut.VALIDEE,
                vente__date_validation__date__gte=debut_mois,
            ).aggregate(
                total=Sum(
                    ExpressionWrapper(
                        F("prix_unitaire") * F("quantite"),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                )
            )["total"]
            or Decimal("0.00")
        )
        achats_mois = (
            CommandeAchat.objects.filter(
                statut__in=[
                    CommandeAchat.Statut.PARTIELLE,
                    CommandeAchat.Statut.RECEPTIONNEE,
                ],
                date_creation__date__gte=debut_mois,
            ).count()
        )

        return render(
            request,
            "gestion/tableau_bord.html",
            {
                "medicaments_actifs": medicaments_actifs,
                "ventes_jour": ventes_jour.count(),
                "montant_jour": montant_jour,
                "ca_mois": ca_mois,
                "achats_mois": achats_mois,
                "stocks_faibles": stocks_faibles[:8],
                "nombre_stocks_faibles": stocks_faibles.count(),
                "lots_alerte": lots_alerte[:8],
                "nombre_lots_alerte": lots_alerte.count(),
                "ventes_recentes": ventes_recentes,
                "top_produits": top_produits,
                "serie": serie,
                "maximum_serie": maximum,
                "mouvements_recents": MouvementStock.objects.select_related(
                    "medicament", "utilisateur"
                )[:6],
            },
        )


class MedicamentListView(LoginRequiredMixin, ListView):
    model = Medicament
    template_name = "gestion/medicament_liste.html"
    context_object_name = "medicaments"
    paginate_by = 12

    def get_queryset(self):
        queryset = Medicament.objects.select_related("categorie")
        recherche = self.request.GET.get("q", "").strip()
        categorie = self.request.GET.get("categorie", "").strip()
        statut = self.request.GET.get("statut", "").strip()
        tri = self.request.GET.get("tri", "nom")
        if recherche:
            queryset = queryset.filter(
                Q(nom_commercial__icontains=recherche)
                | Q(denomination_generique__icontains=recherche)
                | Q(code_barres__icontains=recherche)
            )
        if categorie:
            queryset = queryset.filter(categorie_id=categorie)
        if statut:
            queryset = queryset.filter(statut=statut)
        tris = {
            "nom": "nom_commercial",
            "-nom": "-nom_commercial",
            "prix": "prix_vente",
            "-prix": "-prix_vente",
            "recent": "-date_creation",
        }
        return queryset.order_by(tris.get(tri, "nom_commercial"))

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["categories"] = Categorie.objects.all()
        contexte["q"] = self.request.GET.get("q", "")
        contexte["categorie_selectionnee"] = self.request.GET.get("categorie", "")
        contexte["statut_selectionne"] = self.request.GET.get("statut", "")
        contexte["tri_selectionne"] = self.request.GET.get("tri", "nom")
        return contexte


class MedicamentDetailView(LoginRequiredMixin, DetailView):
    model = Medicament
    template_name = "gestion/medicament_detail.html"
    context_object_name = "medicament"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["lots"] = self.object.lots.select_related("medicament").order_by(
            "date_peremption"
        )
        contexte["mouvements"] = self.object.mouvements.select_related(
            "lot", "utilisateur"
        )[:20]
        contexte["lignes_vente"] = (
            self.object.lignes_vente.select_related("vente")
            .order_by("-vente__date_vente")[:10]
        )
        return contexte


class MedicamentCreateView(RoleRequisMixin, CreateView):
    model = Medicament
    form_class = MedicamentForm
    template_name = "gestion/formulaire.html"
    roles_autorises = CATALOGUE

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["titre"] = "Nouveau médicament"
        contexte["sous_titre"] = "Ajouter une fiche produit avec photo et prix."
        contexte["annuler_url"] = reverse("gestion:medicament_liste")
        return contexte

    def form_valid(self, form):
        response = super().form_valid(form)
        journaliser(
            self.request,
            "Création médicament",
            "Medicament",
            self.object.pk,
            str(self.object),
        )
        messages.success(self.request, "Le médicament a été enregistré.")
        return response


class MedicamentUpdateView(RoleRequisMixin, UpdateView):
    model = Medicament
    form_class = MedicamentForm
    template_name = "gestion/formulaire.html"
    roles_autorises = CATALOGUE

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["titre"] = f"Modifier {self.object.nom_commercial}"
        contexte["sous_titre"] = "Mettre à jour les informations du produit."
        contexte["annuler_url"] = self.object.get_absolute_url()
        return contexte

    def form_valid(self, form):
        response = super().form_valid(form)
        journaliser(
            self.request,
            "Modification médicament",
            "Medicament",
            self.object.pk,
            str(self.object),
        )
        messages.success(self.request, "Les informations ont été mises à jour.")
        return response


class MedicamentSupprimerView(RoleRequisMixin, View):
    roles_autorises = CATALOGUE
    template_name = "gestion/confirmer_suppression.html"

    def get(self, request, pk):
        medicament = get_object_or_404(Medicament, pk=pk)
        return render(
            request,
            self.template_name,
            {
                "objet": medicament,
                "titre": "Supprimer ou archiver le médicament",
                "message": (
                    "Si le médicament possède un historique, il sera archivé au lieu "
                    "d'être supprimé afin de protéger les ventes et achats existants."
                ),
                "annuler_url": medicament.get_absolute_url(),
            },
        )

    def post(self, request, pk):
        medicament = get_object_or_404(Medicament, pk=pk)
        supprime = medicament.supprimer_ou_archiver()
        journaliser(
            request,
            "Suppression médicament" if supprime else "Archivage médicament",
            "Medicament",
            medicament.pk,
            str(medicament),
        )
        messages.success(
            request,
            "Le médicament a été supprimé."
            if supprime
            else "Le médicament a été archivé (historique conservé).",
        )
        return redirect("gestion:medicament_liste")


class CategorieListView(LoginRequiredMixin, ListView):
    model = Categorie
    template_name = "gestion/categorie_liste.html"
    context_object_name = "categories"
    paginate_by = 20

    def get_queryset(self):
        queryset = Categorie.objects.all()
        recherche = self.request.GET.get("q", "").strip()
        if recherche:
            queryset = queryset.filter(nom__icontains=recherche)
        return queryset

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["q"] = self.request.GET.get("q", "")
        return contexte


class CategorieCreateView(RoleRequisMixin, CreateView):
    model = Categorie
    form_class = CategorieForm
    template_name = "gestion/formulaire.html"
    success_url = reverse_lazy("gestion:categorie_liste")
    roles_autorises = CATALOGUE

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["titre"] = "Nouvelle catégorie"
        contexte["annuler_url"] = reverse("gestion:categorie_liste")
        return contexte

    def form_valid(self, form):
        response = super().form_valid(form)
        journaliser(
            self.request, "Création catégorie", "Categorie", self.object.pk, str(self.object)
        )
        messages.success(self.request, "La catégorie a été créée.")
        return response


class CategorieUpdateView(RoleRequisMixin, UpdateView):
    model = Categorie
    form_class = CategorieForm
    template_name = "gestion/formulaire.html"
    success_url = reverse_lazy("gestion:categorie_liste")
    roles_autorises = CATALOGUE

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["titre"] = f"Modifier {self.object.nom}"
        contexte["annuler_url"] = reverse("gestion:categorie_liste")
        return contexte

    def form_valid(self, form):
        response = super().form_valid(form)
        journaliser(
            self.request, "Modification catégorie", "Categorie", self.object.pk, str(self.object)
        )
        messages.success(self.request, "La catégorie a été mise à jour.")
        return response


class CategorieSupprimerView(RoleRequisMixin, View):
    roles_autorises = CATALOGUE
    template_name = "gestion/confirmer_suppression.html"

    def get(self, request, pk):
        categorie = get_object_or_404(Categorie, pk=pk)
        return render(
            request,
            self.template_name,
            {
                "objet": categorie,
                "titre": "Supprimer la catégorie",
                "message": "La suppression est refusée si des médicaments utilisent cette catégorie.",
                "annuler_url": reverse("gestion:categorie_liste"),
                "suppression_bloquee": not categorie.peut_supprimer,
            },
        )

    def post(self, request, pk):
        categorie = get_object_or_404(Categorie, pk=pk)
        try:
            categorie.supprimer()
        except (ValidationError, ProtectedError):
            messages.error(
                request,
                "Impossible de supprimer une catégorie utilisée par des médicaments.",
            )
            return redirect("gestion:categorie_liste")
        journaliser(
            request, "Suppression catégorie", "Categorie", categorie.pk, str(categorie)
        )
        messages.success(request, "La catégorie a été supprimée.")
        return redirect("gestion:categorie_liste")


class FournisseurListView(LoginRequiredMixin, ListView):
    model = Fournisseur
    template_name = "gestion/fournisseur_liste.html"
    context_object_name = "fournisseurs"
    paginate_by = 15

    def get_queryset(self):
        queryset = Fournisseur.objects.all()
        recherche = self.request.GET.get("q", "").strip()
        statut = self.request.GET.get("statut", "").strip()
        if recherche:
            queryset = queryset.filter(
                Q(raison_sociale__icontains=recherche)
                | Q(telephone__icontains=recherche)
                | Q(email__icontains=recherche)
            )
        if statut:
            queryset = queryset.filter(statut=statut)
        return queryset

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["q"] = self.request.GET.get("q", "")
        contexte["statut_selectionne"] = self.request.GET.get("statut", "")
        return contexte


class FournisseurDetailView(LoginRequiredMixin, DetailView):
    model = Fournisseur
    template_name = "gestion/fournisseur_detail.html"
    context_object_name = "fournisseur"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["commandes"] = self.object.commandes.select_related(
            "fournisseur"
        ).order_by("-date_creation")[:20]
        return contexte


class FournisseurCreateView(RoleRequisMixin, CreateView):
    model = Fournisseur
    form_class = FournisseurForm
    template_name = "gestion/formulaire.html"
    roles_autorises = ACHATS

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["titre"] = "Nouveau fournisseur"
        contexte["annuler_url"] = reverse("gestion:fournisseur_liste")
        return contexte

    def form_valid(self, form):
        response = super().form_valid(form)
        journaliser(
            self.request, "Création fournisseur", "Fournisseur", self.object.pk, str(self.object)
        )
        messages.success(self.request, "Le fournisseur a été créé.")
        return response


class FournisseurUpdateView(RoleRequisMixin, UpdateView):
    model = Fournisseur
    form_class = FournisseurForm
    template_name = "gestion/formulaire.html"
    roles_autorises = ACHATS

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["titre"] = f"Modifier {self.object.raison_sociale}"
        contexte["annuler_url"] = self.object.get_absolute_url()
        return contexte

    def form_valid(self, form):
        response = super().form_valid(form)
        journaliser(
            self.request, "Modification fournisseur", "Fournisseur", self.object.pk, str(self.object)
        )
        messages.success(self.request, "Le fournisseur a été mis à jour.")
        return response


@role_requis(*ACHATS)
def basculer_fournisseur(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    if request.method != "POST":
        return redirect("gestion:fournisseur_detail", pk=fournisseur.pk)
    if fournisseur.est_actif:
        fournisseur.desactiver()
        message = "Le fournisseur a été désactivé. Son historique reste conservé."
    else:
        fournisseur.statut = Fournisseur.Statut.ACTIF
        fournisseur.save(update_fields=["statut"])
        message = "Le fournisseur a été réactivé."
    journaliser(
        request, "Changement statut fournisseur", "Fournisseur", fournisseur.pk, message
    )
    messages.success(request, message)
    return redirect("gestion:fournisseur_detail", pk=fournisseur.pk)


class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = "gestion/client_liste.html"
    context_object_name = "clients"
    paginate_by = 15

    def get_queryset(self):
        queryset = Client.objects.all()
        recherche = self.request.GET.get("q", "").strip()
        if recherche:
            queryset = queryset.filter(
                Q(nom__icontains=recherche) | Q(telephone__icontains=recherche)
            )
        return queryset

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["q"] = self.request.GET.get("q", "")
        return contexte


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = "gestion/client_detail.html"
    context_object_name = "client"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["ventes"] = self.object.ventes.select_related("utilisateur").order_by(
            "-date_vente"
        )[:20]
        return contexte


class ClientCreateView(RoleRequisMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = "gestion/formulaire.html"
    roles_autorises = (ROLE.PHARMACIEN, ROLE.CAISSIER)

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["titre"] = "Nouveau client"
        contexte["annuler_url"] = reverse("gestion:client_liste")
        return contexte

    def form_valid(self, form):
        response = super().form_valid(form)
        journaliser(
            self.request, "Création client", "Client", self.object.pk, str(self.object)
        )
        messages.success(self.request, "Le client a été créé.")
        return response


class ClientUpdateView(RoleRequisMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "gestion/formulaire.html"
    roles_autorises = (ROLE.PHARMACIEN, ROLE.CAISSIER)

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["titre"] = f"Modifier {self.object.nom_affichage}"
        contexte["annuler_url"] = self.object.get_absolute_url()
        return contexte

    def form_valid(self, form):
        response = super().form_valid(form)
        journaliser(
            self.request, "Modification client", "Client", self.object.pk, str(self.object)
        )
        messages.success(self.request, "Le client a été mis à jour.")
        return response


@role_requis(ROLE.PHARMACIEN)
def supprimer_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        try:
            client.delete()
        except ProtectedError:
            messages.error(
                request,
                "Ce client possède un historique de ventes : désactivez-le au lieu de le supprimer.",
            )
            return redirect("gestion:client_detail", pk=client.pk)
        journaliser(request, "Suppression client", "Client", pk, str(client))
        messages.success(request, "Le client a été supprimé.")
        return redirect("gestion:client_liste")
    return render(
        request,
        "gestion/confirmer_suppression.html",
        {
            "objet": client,
            "titre": "Supprimer le client",
            "message": "La suppression est refusée si des ventes sont associées à ce client.",
            "annuler_url": reverse("gestion:client_detail", args=[client.pk]),
        },
    )


class CommandeListView(RoleRequisMixin, ListView):
    model = CommandeAchat
    template_name = "gestion/commande_liste.html"
    context_object_name = "commandes"
    paginate_by = 15
    roles_autorises = (ROLE.PHARMACIEN, ROLE.GESTIONNAIRE, ROLE.RESPONSABLE)

    def get_queryset(self):
        queryset = CommandeAchat.objects.select_related("fournisseur", "utilisateur")
        recherche = self.request.GET.get("q", "").strip()
        statut = self.request.GET.get("statut", "").strip()
        if recherche:
            queryset = queryset.filter(
                Q(numero__icontains=recherche)
                | Q(fournisseur__raison_sociale__icontains=recherche)
            )
        if statut:
            queryset = queryset.filter(statut=statut)
        return queryset

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["q"] = self.request.GET.get("q", "")
        contexte["statut_selectionne"] = self.request.GET.get("statut", "")
        contexte["statuts"] = CommandeAchat.Statut.choices
        return contexte


class CommandeDetailView(RoleRequisMixin, DetailView):
    model = CommandeAchat
    template_name = "gestion/commande_detail.html"
    context_object_name = "commande"
    roles_autorises = (ROLE.PHARMACIEN, ROLE.GESTIONNAIRE, ROLE.RESPONSABLE)

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["lignes"] = self.object.lignes.select_related("medicament")
        contexte["receptions"] = self.object.receptions.select_related(
            "utilisateur"
        ).order_by("-date_creation")
        return contexte


class CommandeCreateView(RoleRequisMixin, View):
    roles_autorises = ACHATS
    template_name = "gestion/commande_form.html"

    def get(self, request):
        form = CommandeAchatForm()
        formset = LigneAchatFormSet(instance=CommandeAchat())
        return render(
            request,
            self.template_name,
            {"form": form, "formset": formset, "titre": "Nouvelle commande d'achat"},
        )

    def post(self, request):
        commande = CommandeAchat()
        form = CommandeAchatForm(request.POST)
        formset = LigneAchatFormSet(request.POST, instance=commande)
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    commande = form.save(commit=False)
                    commande.utilisateur = request.user
                    commande.save()
                    formset.instance = commande
                    formset.save()
                    if not commande.lignes.exists():
                        raise ValidationError(
                            "Ajoutez au moins un médicament à la commande."
                        )
                    journaliser(
                        request,
                        "Création commande",
                        "CommandeAchat",
                        commande.pk,
                        str(commande),
                    )
                messages.success(
                    request, "La commande a été créée en brouillon."
                )
                return redirect("gestion:commande_detail", pk=commande.pk)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
        else:
            messages.error(request, "Corrigez les erreurs du formulaire.")
        return render(
            request,
            self.template_name,
            {"form": form, "formset": formset, "titre": "Nouvelle commande d'achat"},
        )


class CommandeUpdateView(RoleRequisMixin, View):
    roles_autorises = ACHATS
    template_name = "gestion/commande_form.html"

    def get(self, request, pk):
        commande = get_object_or_404(CommandeAchat, pk=pk)
        if not commande.modifiable:
            messages.error(request, "Seule une commande en brouillon est modifiable.")
            return redirect("gestion:commande_detail", pk=commande.pk)
        form = CommandeAchatForm(instance=commande)
        formset = LigneAchatFormSet(instance=commande)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "commande": commande,
                "titre": f"Modifier {commande.numero}",
            },
        )

    def post(self, request, pk):
        commande = get_object_or_404(CommandeAchat, pk=pk)
        if not commande.modifiable:
            messages.error(request, "Seule une commande en brouillon est modifiable.")
            return redirect("gestion:commande_detail", pk=commande.pk)
        form = CommandeAchatForm(request.POST, instance=commande)
        formset = LigneAchatFormSet(request.POST, instance=commande)
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    formset.save()
                    if not commande.lignes.exists():
                        raise ValidationError(
                            "Ajoutez au moins un médicament à la commande."
                        )
                    journaliser(
                        request,
                        "Modification commande",
                        "CommandeAchat",
                        commande.pk,
                        str(commande),
                    )
                messages.success(request, "La commande a été mise à jour.")
                return redirect("gestion:commande_detail", pk=commande.pk)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
        else:
            messages.error(request, "Corrigez les erreurs du formulaire.")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "commande": commande,
                "titre": f"Modifier {commande.numero}",
            },
        )


@role_requis(*ACHATS)
def valider_commande(request, pk):
    commande = get_object_or_404(CommandeAchat, pk=pk)
    if request.method == "POST":
        try:
            commande.valider()
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            journaliser(
                request, "Validation commande", "CommandeAchat", commande.pk, str(commande)
            )
            messages.success(request, "La commande a été validée.")
    return redirect("gestion:commande_detail", pk=commande.pk)


@role_requis(*ACHATS)
def annuler_commande(request, pk):
    commande = get_object_or_404(CommandeAchat, pk=pk)
    if request.method == "POST":
        try:
            commande.annuler()
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            journaliser(
                request, "Annulation commande", "CommandeAchat", commande.pk, str(commande)
            )
            messages.success(request, "La commande a été annulée.")
    return redirect("gestion:commande_detail", pk=commande.pk)


@role_requis(*ACHATS)
def receptionner_commande(request, pk):
    commande = get_object_or_404(CommandeAchat, pk=pk)
    lignes = list(commande.lignes.select_related("medicament"))
    if request.method == "POST":
        try:
            with transaction.atomic():
                if not commande.receptionnable:
                    raise ValidationError(
                        "Cette commande n'est pas dans un état permettant une réception."
                    )
                date_reception = parse_date(
                    request.POST.get("date_reception", "")
                ) or timezone.localdate()
                reception = ReceptionAchat.objects.create(
                    commande=commande,
                    utilisateur=request.user,
                    date_reception=date_reception,
                    notes=request.POST.get("notes", "").strip(),
                )
                nombre = 0
                for ligne in lignes:
                    valeur = request.POST.get(f"quantite_{ligne.id}", "").strip()
                    if not valeur:
                        continue
                    try:
                        quantite = int(valeur)
                    except ValueError:
                        raise ValidationError(
                            f"Quantité invalide pour {ligne.medicament}."
                        )
                    if quantite <= 0:
                        continue
                    numero_lot = request.POST.get(f"lot_{ligne.id}", "").strip()
                    peremption = parse_date(
                        request.POST.get(f"peremption_{ligne.id}", "")
                    )
                    if not numero_lot:
                        raise ValidationError(
                            f"Le numéro de lot est obligatoire pour {ligne.medicament}."
                        )
                    if not peremption:
                        raise ValidationError(
                            f"La date de péremption est obligatoire pour {ligne.medicament}."
                        )
                    LigneReception.objects.create(
                        reception=reception,
                        ligne_achat=ligne,
                        quantite=quantite,
                        numero_lot=numero_lot,
                        date_peremption=peremption,
                    )
                    nombre += 1
                if nombre == 0:
                    raise ValidationError(
                        "Indiquez au moins une quantité reçue."
                    )
                reception.valider(request.user)
                journaliser(
                    request,
                    "Réception commande",
                    "ReceptionAchat",
                    reception.pk,
                    f"{reception.numero} pour {commande.numero}",
                )
            messages.success(
                request,
                "La réception a été validée : le stock a été mis à jour.",
            )
            return redirect("gestion:reception_detail", pk=reception.pk)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
    return render(
        request,
        "gestion/reception_form.html",
        {
            "commande": commande,
            "lignes": lignes,
            "aujourd_hui": timezone.localdate(),
            "peremption_defaut": timezone.localdate() + timedelta(days=730),
        },
    )


class ReceptionListView(RoleRequisMixin, ListView):
    model = ReceptionAchat
    template_name = "gestion/reception_liste.html"
    context_object_name = "receptions"
    paginate_by = 15
    roles_autorises = (ROLE.PHARMACIEN, ROLE.GESTIONNAIRE, ROLE.RESPONSABLE)

    def get_queryset(self):
        return ReceptionAchat.objects.select_related(
            "commande__fournisseur", "utilisateur"
        ).order_by("-date_creation")


class ReceptionDetailView(RoleRequisMixin, DetailView):
    model = ReceptionAchat
    template_name = "gestion/reception_detail.html"
    context_object_name = "reception"
    roles_autorises = (ROLE.PHARMACIEN, ROLE.GESTIONNAIRE, ROLE.RESPONSABLE)

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["lignes"] = self.object.lignes.select_related(
            "ligne_achat__medicament"
        )
        return contexte


class StockListView(LoginRequiredMixin, ListView):
    model = LotStock
    template_name = "gestion/stock_liste.html"
    context_object_name = "lots"
    paginate_by = 20

    def get_queryset(self):
        queryset = LotStock.objects.select_related("medicament", "medicament__categorie")
        recherche = self.request.GET.get("q", "").strip()
        etat = self.request.GET.get("etat", "").strip()
        if recherche:
            queryset = queryset.filter(
                Q(medicament__nom_commercial__icontains=recherche)
                | Q(medicament__code_barres__icontains=recherche)
                | Q(numero_lot__icontains=recherche)
            )
        aujourd_hui = timezone.localdate()
        if etat == "perime":
            queryset = queryset.filter(date_peremption__lt=aujourd_hui)
        elif etat == "proche":
            queryset = queryset.filter(
                date_peremption__gte=aujourd_hui,
                date_peremption__lte=aujourd_hui
                + timedelta(days=settings.SEUIL_PEREMPTION_JOURS),
            )
        elif etat == "bloque":
            queryset = queryset.filter(bloque=True)
        elif etat == "faible":
            queryset = queryset.filter(quantite__lte=F("medicament__seuil_alerte"))
        return queryset.order_by("medicament__nom_commercial", "date_peremption")

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["q"] = self.request.GET.get("q", "")
        contexte["etat_selectionne"] = self.request.GET.get("etat", "")
        contexte["total_lots"] = LotStock.objects.aggregate(
            total=Coalesce(Sum("quantite"), 0)
        )["total"]
        return contexte


class MouvementListView(LoginRequiredMixin, ListView):
    model = MouvementStock
    template_name = "gestion/mouvement_liste.html"
    context_object_name = "mouvements"
    paginate_by = 30

    def get_queryset(self):
        queryset = MouvementStock.objects.select_related(
            "medicament", "lot", "utilisateur"
        )
        type_mouvement = self.request.GET.get("type", "").strip()
        recherche = self.request.GET.get("q", "").strip()
        if type_mouvement:
            queryset = queryset.filter(type=type_mouvement)
        if recherche:
            queryset = queryset.filter(
                Q(medicament__nom_commercial__icontains=recherche)
                | Q(reference__icontains=recherche)
            )
        return queryset

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["types"] = MouvementStock.Type.choices
        contexte["type_selectionne"] = self.request.GET.get("type", "")
        contexte["q"] = self.request.GET.get("q", "")
        return contexte


@login_required
def alertes(request):
    aujourd_hui = timezone.localdate()
    limite = aujourd_hui + timedelta(days=settings.SEUIL_PEREMPTION_JOURS)
    stocks_faibles = (
        Medicament.objects.filter(statut=Medicament.Statut.ACTIF)
        .annotate(stock=Coalesce(Sum("lots__quantite"), 0))
        .filter(stock__lte=F("seuil_alerte"))
        .select_related("categorie")
        .order_by("stock")
    )
    lots_perimes = (
        LotStock.objects.filter(date_peremption__lt=aujourd_hui)
        .select_related("medicament")
        .order_by("date_peremption")
    )
    lots_proches = (
        LotStock.objects.filter(
            date_peremption__gte=aujourd_hui, date_peremption__lte=limite
        )
        .select_related("medicament")
        .order_by("date_peremption")
    )
    return render(
        request,
        "gestion/alertes.html",
        {
            "stocks_faibles": stocks_faibles,
            "lots_perimes": lots_perimes,
            "lots_proches": lots_proches,
            "limite": limite,
        },
    )


@role_requis(*GESTION_STOCK)
def inventaire(request):
    form = AjustementStockForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        lot = form.cleaned_data["lot"]
        nouvelle = form.cleaned_data["nouvelle_quantite"]
        motif = form.cleaned_data["motif"]
        delta = nouvelle - lot.quantite
        try:
            with transaction.atomic():
                lot.quantite = nouvelle
                lot.save(update_fields=["quantite"])
                MouvementStock.objects.create(
                    medicament=lot.medicament,
                    lot=lot,
                    type=MouvementStock.Type.CORRECTION,
                    quantite=delta,
                    stock_apres=nouvelle,
                    reference=f"Inventaire lot {lot.numero_lot}",
                    motif=motif,
                    utilisateur=request.user,
                )
                journaliser(
                    request,
                    "Correction inventaire",
                    "LotStock",
                    lot.pk,
                    f"{lot.medicament} : {delta:+d} (nouveau stock {nouvelle})",
                )
            messages.success(
                request, "La correction d'inventaire a été enregistrée."
            )
            return redirect("gestion:stock_liste")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
    return render(
        request,
        "gestion/inventaire.html",
        {
            "form": form,
            "lots": LotStock.objects.select_related("medicament").order_by(
                "medicament__nom_commercial", "date_peremption"
            )[:200],
        },
    )


@role_requis(*GESTION_STOCK)
def basculer_lot(request, pk):
    lot = get_object_or_404(LotStock, pk=pk)
    if request.method == "POST":
        lot.bloque = not lot.bloque
        lot.save(update_fields=["bloque"])
        etat = "bloqué" if lot.bloque else "débloqué"
        journaliser(
            request,
            f"Lot {etat}",
            "LotStock",
            lot.pk,
            f"{lot.medicament} lot {lot.numero_lot}",
        )
        messages.success(request, f"Le lot a été {etat}.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("gestion:stock_liste"))


@role_requis(*VENTE)
def caisse(request):
    if request.method == "POST":
        form = VenteForm(request.POST)
        formset = LigneVenteFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            lignes_valides = [
                f
                for f in formset.forms
                if f.cleaned_data
                and not f.cleaned_data.get("DELETE")
                and f.cleaned_data.get("lot")
                and f.cleaned_data.get("quantite")
            ]
            if not lignes_valides:
                messages.error(request, "Ajoutez au moins un médicament à la vente.")
            else:
                try:
                    with transaction.atomic():
                        vente = Vente.objects.create(
                            client=form.cleaned_data["client"],
                            utilisateur=request.user,
                            remise=form.cleaned_data["remise"] or Decimal("0.00"),
                        )
                        for ligne_form in lignes_valides:
                            lot = ligne_form.cleaned_data["lot"]
                            quantite = ligne_form.cleaned_data["quantite"]
                            LigneVente.objects.create(
                                vente=vente,
                                medicament=lot.medicament,
                                lot=lot,
                                quantite=quantite,
                                prix_unitaire=lot.medicament.prix_vente,
                            )
                        if vente.total <= 0:
                            raise ValidationError(
                                "Le montant de la vente doit être supérieur à zéro."
                            )
                        mode = form.cleaned_data["mode_paiement"]
                        Paiement.objects.create(
                            vente=vente,
                            montant=vente.total,
                            mode=mode,
                            statut=Paiement.Statut.CONFIRME,
                            reference=form.cleaned_data["reference_paiement"],
                            confirme_par=request.user,
                            date_confirmation=timezone.now(),
                        )
                        vente.valider(request.user)
                        journaliser(
                            request,
                            "Vente validée",
                            "Vente",
                            vente.pk,
                            f"{vente.numero} - {vente.total} Ar",
                        )
                    messages.success(
                        request, f"Vente {vente.numero} validée avec succès."
                    )
                    return redirect("gestion:vente_detail", pk=vente.pk)
                except ValidationError as exc:
                    messages.error(request, "; ".join(exc.messages))
        else:
            messages.error(request, "Corrigez les erreurs du formulaire de vente.")
    else:
        form = VenteForm()
        formset = LigneVenteFormSet()
    return render(
        request,
        "gestion/caisse.html",
        {"form": form, "formset": formset, "titre": "Nouvelle vente (caisse)"},
    )


class VenteListView(LoginRequiredMixin, ListView):
    model = Vente
    template_name = "gestion/vente_liste.html"
    context_object_name = "ventes"
    paginate_by = 20

    def get_queryset(self):
        queryset = Vente.objects.select_related("client", "utilisateur").prefetch_related(
            "lignes"
        )
        recherche = self.request.GET.get("q", "").strip()
        statut = self.request.GET.get("statut", "").strip()
        if recherche:
            queryset = queryset.filter(
                Q(numero__icontains=recherche)
                | Q(client__nom__icontains=recherche)
            )
        if statut:
            queryset = queryset.filter(statut=statut)
        return queryset

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["q"] = self.request.GET.get("q", "")
        contexte["statut_selectionne"] = self.request.GET.get("statut", "")
        contexte["statuts"] = Vente.Statut.choices
        return contexte


class VenteDetailView(LoginRequiredMixin, DetailView):
    model = Vente
    template_name = "gestion/vente_detail.html"
    context_object_name = "vente"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["lignes"] = self.object.lignes.select_related(
            "medicament", "lot"
        )
        contexte["paiements"] = self.object.paiements.select_related("confirme_par")
        contexte["retours"] = self.object.retours.prefetch_related(
            "lignes__ligne_vente__medicament"
        )
        return contexte


@role_requis(ROLE.PHARMACIEN)
def annuler_vente(request, pk):
    vente = get_object_or_404(Vente, pk=pk)
    if request.method == "POST":
        motif = request.POST.get("motif", "").strip()
        try:
            vente.annuler(motif, request.user)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            journaliser(
                request,
                "Annulation vente",
                "Vente",
                vente.pk,
                f"{vente.numero} : {motif}",
            )
            messages.success(
                request, "La vente a été annulée par compensation traçable."
            )
            return redirect("gestion:vente_detail", pk=vente.pk)
    return render(
        request,
        "gestion/vente_annuler.html",
        {"vente": vente},
    )


@role_requis(*VENTE)
def retour_vente(request, pk):
    vente = get_object_or_404(Vente, pk=pk)
    lignes = list(vente.lignes.select_related("medicament", "lot"))
    form = RetourVenteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                if vente.statut != Vente.Statut.VALIDEE:
                    raise ValidationError(
                        "Un retour ne peut être enregistré que pour une vente validée."
                    )
                retour = RetourVente.objects.create(
                    vente=vente,
                    utilisateur=request.user,
                    motif=form.cleaned_data["motif"],
                    remis_en_stock=form.cleaned_data["remis_en_stock"],
                    remboursement=form.cleaned_data["remboursement"] or Decimal("0.00"),
                )
                nombre = 0
                for ligne in lignes:
                    valeur = request.POST.get(f"quantite_{ligne.id}", "").strip()
                    if not valeur:
                        continue
                    try:
                        quantite = int(valeur)
                    except ValueError:
                        raise ValidationError(
                            f"Quantité de retour invalide pour {ligne.medicament}."
                        )
                    if quantite <= 0:
                        continue
                    if quantite > ligne.quantite_retournable:
                        raise ValidationError(
                            f"La quantité retournée dépasse la quantité vendue pour "
                            f"{ligne.medicament}."
                        )
                    LigneRetour.objects.create(
                        retour=retour, ligne_vente=ligne, quantite=quantite
                    )
                    nombre += 1
                if nombre == 0:
                    raise ValidationError(
                        "Indiquez au moins une quantité à retourner."
                    )
                retour.traiter(request.user)
                journaliser(
                    request,
                    "Retour de vente",
                    "RetourVente",
                    retour.pk,
                    f"Vente {vente.numero}",
                )
            messages.success(request, "Le retour a été enregistré.")
            return redirect("gestion:vente_detail", pk=vente.pk)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
    return render(
        request,
        "gestion/retour_form.html",
        {"vente": vente, "lignes": lignes, "form": form},
    )


@role_requis(*VENTE)
def confirmer_paiement(request, pk):
    paiement = get_object_or_404(Paiement, pk=pk)
    if request.method == "POST":
        try:
            paiement.confirmer(request.user)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            journaliser(
                request,
                "Confirmation paiement",
                "Paiement",
                paiement.pk,
                f"{paiement.montant} Ar - {paiement.get_mode_display()}",
            )
            messages.success(request, "Le paiement a été confirmé.")
    return redirect("gestion:vente_detail", pk=paiement.vente_id)


class UtilisateurListView(RoleRequisMixin, ListView):
    model = Utilisateur
    template_name = "gestion/utilisateur_liste.html"
    context_object_name = "utilisateurs"
    paginate_by = 20
    roles_autorises = ()

    def get_queryset(self):
        queryset = Utilisateur.objects.all()
        recherche = self.request.GET.get("q", "").strip()
        if recherche:
            queryset = queryset.filter(
                Q(username__icontains=recherche)
                | Q(first_name__icontains=recherche)
                | Q(last_name__icontains=recherche)
                | Q(email__icontains=recherche)
            )
        return queryset.order_by("username")

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["q"] = self.request.GET.get("q", "")
        return contexte


class UtilisateurCreateView(RoleRequisMixin, CreateView):
    model = Utilisateur
    form_class = UtilisateurCreationForm
    template_name = "gestion/formulaire.html"
    success_url = reverse_lazy("gestion:utilisateur_liste")
    roles_autorises = ()

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["titre"] = "Nouvel utilisateur"
        contexte["annuler_url"] = reverse("gestion:utilisateur_liste")
        return contexte

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.groups.set(
            Group.objects.filter(name=f"Role {self.object.role}")
        )
        journaliser(
            self.request,
            "Création utilisateur",
            "Utilisateur",
            self.object.pk,
            f"{self.object.username} / {self.object.get_role_display()}",
        )
        messages.success(self.request, "Le compte utilisateur a été créé.")
        return response


class UtilisateurUpdateView(RoleRequisMixin, UpdateView):
    model = Utilisateur
    form_class = UtilisateurModificationForm
    template_name = "gestion/formulaire.html"
    success_url = reverse_lazy("gestion:utilisateur_liste")
    roles_autorises = ()

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["titre"] = f"Modifier {self.object.username}"
        contexte["annuler_url"] = reverse("gestion:utilisateur_liste")
        return contexte

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.groups.set(
            Group.objects.filter(name=f"Role {self.object.role}")
        )
        journaliser(
            self.request,
            "Modification utilisateur",
            "Utilisateur",
            self.object.pk,
            f"{self.object.username} / {self.object.get_role_display()}",
        )
        messages.success(self.request, "Le compte utilisateur a été mis à jour.")
        return response


class ReinitialiserMotDePasseView(RoleRequisMixin, View):
    roles_autorises = ()
    template_name = "gestion/reinitialiser_mot_de_passe.html"

    def get(self, request, pk):
        utilisateur = get_object_or_404(Utilisateur, pk=pk)
        form = ReinitialiserMotDePasseForm(user=utilisateur)
        return render(
            request, self.template_name, {"form": form, "utilisateur": utilisateur}
        )

    def post(self, request, pk):
        utilisateur = get_object_or_404(Utilisateur, pk=pk)
        form = ReinitialiserMotDePasseForm(user=utilisateur, data=request.POST)
        if form.is_valid():
            form.save()
            journaliser(
                request,
                "Réinitialisation mot de passe",
                "Utilisateur",
                utilisateur.pk,
                utilisateur.username,
            )
            messages.success(
                request, "Le mot de passe a été réinitialisé de façon sécurisée."
            )
            return redirect("gestion:utilisateur_liste")
        return render(
            request, self.template_name, {"form": form, "utilisateur": utilisateur}
        )


@role_requis(ROLE.ADMIN)
def basculer_utilisateur(request, pk):
    utilisateur = get_object_or_404(Utilisateur, pk=pk)
    if request.method == "POST":
        if utilisateur == request.user:
            messages.error(request, "Vous ne pouvez pas désactiver votre propre compte.")
        else:
            utilisateur.is_active = not utilisateur.is_active
            utilisateur.save(update_fields=["is_active"])
            etat = "activé" if utilisateur.is_active else "désactivé"
            journaliser(
                request,
                f"Compte {etat}",
                "Utilisateur",
                utilisateur.pk,
                utilisateur.username,
            )
            messages.success(request, f"Le compte a été {etat}.")
    return redirect("gestion:utilisateur_liste")


class JournalAuditListView(RoleRequisMixin, ListView):
    model = JournalAudit
    template_name = "gestion/journal_liste.html"
    context_object_name = "entrees"
    paginate_by = 40
    roles_autorises = (ROLE.PHARMACIEN, ROLE.RESPONSABLE)

    def get_queryset(self):
        queryset = JournalAudit.objects.select_related("utilisateur")
        recherche = self.request.GET.get("q", "").strip()
        if recherche:
            queryset = queryset.filter(
                Q(action__icontains=recherche)
                | Q(details__icontains=recherche)
                | Q(utilisateur__username__icontains=recherche)
            )
        return queryset

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["q"] = self.request.GET.get("q", "")
        return contexte


@role_requis(*RAPPORTS)
def rapports(request):
    form = PeriodeForm(request.GET or None)
    debut, fin = _periode_depuis_requete(request)
    return render(
        request,
        "gestion/rapports.html",
        {"form": form, "date_debut": debut, "date_fin": fin},
    )


def _periode_depuis_requete(request):
    form = PeriodeForm(request.GET or None)
    if form.is_valid():
        return form.cleaned_data["date_debut"], form.cleaned_data["date_fin"]
    aujourd_hui = timezone.localdate()
    return aujourd_hui.replace(day=1), aujourd_hui


@login_required
def recu_pdf(request, pk):
    vente = get_object_or_404(
        Vente.objects.select_related("client", "utilisateur").prefetch_related(
            "lignes__medicament", "lignes__lot", "paiements"
        ),
        pk=pk,
    )
    return pdf_recu(vente)


@login_required
def facture_pdf(request, pk):
    vente = get_object_or_404(
        Vente.objects.select_related("client", "utilisateur").prefetch_related(
            "lignes__medicament", "lignes__lot", "paiements"
        ),
        pk=pk,
    )
    return pdf_facture(vente)


@role_requis(*ACHATS)
def bon_commande_pdf(request, pk):
    commande = get_object_or_404(
        CommandeAchat.objects.select_related("fournisseur", "utilisateur").prefetch_related(
            "lignes__medicament"
        ),
        pk=pk,
    )
    return pdf_bon_commande(commande)


@role_requis(*ACHATS)
def bon_reception_pdf(request, pk):
    reception = get_object_or_404(
        ReceptionAchat.objects.select_related(
            "commande__fournisseur", "utilisateur"
        ).prefetch_related("lignes__ligne_achat__medicament"),
        pk=pk,
    )
    return pdf_bon_reception(reception)


@role_requis(*RAPPORTS)
def rapport_stock_pdf(request):
    lots = (
        LotStock.objects.select_related("medicament")
        .filter(quantite__gt=0)
        .order_by("medicament__nom_commercial", "date_peremption")
    )
    return pdf_rapport_stock(lots)


@role_requis(*RAPPORTS)
def rapport_ventes_pdf(request):
    debut, fin = _periode_depuis_requete(request)
    ventes = (
        Vente.objects.filter(
            statut=Vente.Statut.VALIDEE,
            date_validation__date__range=(debut, fin),
        )
        .select_related("client", "utilisateur")
        .prefetch_related("lignes")
        .order_by("date_validation")
    )
    return pdf_rapport_ventes(ventes, debut, fin)


@role_requis(*RAPPORTS)
def rapport_achats_pdf(request):
    debut, fin = _periode_depuis_requete(request)
    commandes = (
        CommandeAchat.objects.filter(date_creation__date__range=(debut, fin))
        .select_related("fournisseur")
        .prefetch_related("lignes")
        .order_by("date_creation")
    )
    return pdf_rapport_achats(commandes, debut, fin)


@role_requis(*RAPPORTS)
def rapport_peremptions_pdf(request):
    aujourd_hui = timezone.localdate()
    limite = aujourd_hui + timedelta(days=settings.SEUIL_PEREMPTION_JOURS)
    lots = (
        LotStock.objects.filter(
            quantite__gt=0, date_peremption__lte=limite
        )
        .select_related("medicament")
        .order_by("date_peremption")
    )
    return pdf_rapport_peremptions(lots, aujourd_hui, limite)
