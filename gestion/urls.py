from django.urls import path

from . import views

app_name = "gestion"

urlpatterns = [
    path("", views.TableauBordView.as_view(), name="tableau_bord"),
    path("connexion/", views.ConnexionView.as_view(), name="connexion"),
    path("deconnexion/", views.DeconnexionView.as_view(), name="deconnexion"),
    path("mot-de-passe/", views.ModifierMotDePasseView.as_view(), name="mot_de_passe"),
    path("medicaments/", views.MedicamentListView.as_view(), name="medicament_liste"),
    path(
        "medicaments/ajouter/",
        views.MedicamentCreateView.as_view(),
        name="medicament_ajouter",
    ),
    path(
        "medicaments/<int:pk>/",
        views.MedicamentDetailView.as_view(),
        name="medicament_detail",
    ),
    path(
        "medicaments/<int:pk>/modifier/",
        views.MedicamentUpdateView.as_view(),
        name="medicament_modifier",
    ),
    path(
        "medicaments/<int:pk>/supprimer/",
        views.MedicamentSupprimerView.as_view(),
        name="medicament_supprimer",
    ),
    path("categories/", views.CategorieListView.as_view(), name="categorie_liste"),
    path(
        "categories/ajouter/",
        views.CategorieCreateView.as_view(),
        name="categorie_ajouter",
    ),
    path(
        "categories/<int:pk>/modifier/",
        views.CategorieUpdateView.as_view(),
        name="categorie_modifier",
    ),
    path(
        "categories/<int:pk>/supprimer/",
        views.CategorieSupprimerView.as_view(),
        name="categorie_supprimer",
    ),
    path("fournisseurs/", views.FournisseurListView.as_view(), name="fournisseur_liste"),
    path(
        "fournisseurs/ajouter/",
        views.FournisseurCreateView.as_view(),
        name="fournisseur_ajouter",
    ),
    path(
        "fournisseurs/<int:pk>/",
        views.FournisseurDetailView.as_view(),
        name="fournisseur_detail",
    ),
    path(
        "fournisseurs/<int:pk>/modifier/",
        views.FournisseurUpdateView.as_view(),
        name="fournisseur_modifier",
    ),
    path(
        "fournisseurs/<int:pk>/basculer/",
        views.basculer_fournisseur,
        name="fournisseur_basculer",
    ),
    path("clients/", views.ClientListView.as_view(), name="client_liste"),
    path("clients/ajouter/", views.ClientCreateView.as_view(), name="client_ajouter"),
    path("clients/<int:pk>/", views.ClientDetailView.as_view(), name="client_detail"),
    path(
        "clients/<int:pk>/modifier/",
        views.ClientUpdateView.as_view(),
        name="client_modifier",
    ),
    path("clients/<int:pk>/supprimer/", views.supprimer_client, name="client_supprimer"),
    path("achats/", views.CommandeListView.as_view(), name="commande_liste"),
    path(
        "achats/ajouter/", views.CommandeCreateView.as_view(), name="commande_ajouter"
    ),
    path(
        "achats/<int:pk>/",
        views.CommandeDetailView.as_view(),
        name="commande_detail",
    ),
    path(
        "achats/<int:pk>/modifier/",
        views.CommandeUpdateView.as_view(),
        name="commande_modifier",
    ),
    path("achats/<int:pk>/valider/", views.valider_commande, name="commande_valider"),
    path("achats/<int:pk>/annuler/", views.annuler_commande, name="commande_annuler"),
    path(
        "achats/<int:pk>/receptionner/",
        views.receptionner_commande,
        name="commande_receptionner",
    ),
    path("receptions/", views.ReceptionListView.as_view(), name="reception_liste"),
    path(
        "receptions/<int:pk>/",
        views.ReceptionDetailView.as_view(),
        name="reception_detail",
    ),
    path("stock/", views.StockListView.as_view(), name="stock_liste"),
    path("stock/mouvements/", views.MouvementListView.as_view(), name="mouvement_liste"),
    path("stock/alertes/", views.alertes, name="alertes"),
    path("stock/inventaire/", views.inventaire, name="inventaire"),
    path("stock/lots/<int:pk>/basculer/", views.basculer_lot, name="lot_basculer"),
    path("ventes/", views.VenteListView.as_view(), name="vente_liste"),
    path("ventes/caisse/", views.caisse, name="caisse"),
    path("ventes/<int:pk>/", views.VenteDetailView.as_view(), name="vente_detail"),
    path("ventes/<int:pk>/annuler/", views.annuler_vente, name="vente_annuler"),
    path("ventes/<int:pk>/retour/", views.retour_vente, name="retour_vente"),
    path(
        "paiements/<int:pk>/confirmer/",
        views.confirmer_paiement,
        name="paiement_confirmer",
    ),
    path("utilisateurs/", views.UtilisateurListView.as_view(), name="utilisateur_liste"),
    path(
        "utilisateurs/ajouter/",
        views.UtilisateurCreateView.as_view(),
        name="utilisateur_ajouter",
    ),
    path(
        "utilisateurs/<int:pk>/modifier/",
        views.UtilisateurUpdateView.as_view(),
        name="utilisateur_modifier",
    ),
    path(
        "utilisateurs/<int:pk>/mot-de-passe/",
        views.ReinitialiserMotDePasseView.as_view(),
        name="utilisateur_mot_de_passe",
    ),
    path(
        "utilisateurs/<int:pk>/basculer/",
        views.basculer_utilisateur,
        name="utilisateur_basculer",
    ),
    path("journal/", views.JournalAuditListView.as_view(), name="journal_liste"),
    path("rapports/", views.rapports, name="rapports"),
    path("rapports/stock.pdf", views.rapport_stock_pdf, name="rapport_stock_pdf"),
    path("rapports/ventes.pdf", views.rapport_ventes_pdf, name="rapport_ventes_pdf"),
    path("rapports/achats.pdf", views.rapport_achats_pdf, name="rapport_achats_pdf"),
    path(
        "rapports/peremptions.pdf",
        views.rapport_peremptions_pdf,
        name="rapport_peremptions_pdf",
    ),
    path("ventes/<int:pk>/recu.pdf", views.recu_pdf, name="recu_pdf"),
    path("ventes/<int:pk>/facture.pdf", views.facture_pdf, name="facture_pdf"),
    path(
        "achats/<int:pk>/bon-commande.pdf",
        views.bon_commande_pdf,
        name="bon_commande_pdf",
    ),
    path(
        "receptions/<int:pk>/bon-reception.pdf",
        views.bon_reception_pdf,
        name="bon_reception_pdf",
    ),
]
