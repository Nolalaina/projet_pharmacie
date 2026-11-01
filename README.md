# PharmaGest

Application web de gestion d'officine développée avec Django, SQLite et Bootstrap 5, conformément au cahier des charges du projet pharmacie.

## Fonctionnalités

- Authentification et rôles : administrateur, pharmacien, gestionnaire de stock, caissier, responsable.
- Catalogue : catégories, médicaments, photos, prix d'achat/vente et seuils d'alerte.
- Fournisseurs et clients avec historique.
- Commandes d'achat, réceptions partielles ou totales et mise à jour atomique du stock.
- Lots, mouvements traçables, blocage de lot, inventaire et alertes de stock/péremption.
- Caisse avec recherche par code-barres ou nom, ventes multi-lignes, paiements (espèces, mobile money, carte), annulation et retours.
- Tableau de bord, journal d'audit et rapports PDF (stock, ventes, achats, péremptions, reçus, factures, bons).
- Interface française responsive avec Bootstrap 5.

## Installation

Prérequis : Python 3.12 ou supérieur.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Ouvrir <http://127.0.0.1:8000/>.

## Comptes de démonstration

| Identifiant | Mot de passe | Rôle |
| --- | --- | --- |
| `admin` | `admin123` | Administrateur |
| `pharmacien` | `pharma123` | Pharmacien responsable |
| `gestionnaire` | `gest123` | Gestionnaire de stock |
| `caissier` | `caisse123` | Caissier |
| `responsable` | `resp123` | Responsable de gestion |

La commande `seed_demo` est idempotente : elle peut être relancée sans dupliquer les données.

## Tests

```powershell
python manage.py test
python manage.py check
```

Les tests couvrent la validation des ventes, la sortie de stock, les réceptions, les retours, les annulations, les permissions par rôle, le rendu des pages et les exports PDF.

## Guide rapide

1. Connectez-vous avec le compte correspondant au rôle souhaité.
2. Catalogue : créez les catégories, puis les médicaments avec leurs prix et photos.
3. Approvisionnement : créez une commande, validez-la, puis enregistrez la réception. Le stock n'augmente qu'à la validation de la réception.
4. Caisse : scannez ou saisissez un code-barres, vérifiez la quantité et le total, puis encaissez. Le reçu PDF est disponible depuis la fiche de vente.
5. Stock : consultez les lots, les alertes et les mouvements. Utilisez l'inventaire pour corriger un écart avec un motif.
6. Retours : ouvrez une vente validée, choisissez les quantités retournées et indiquez si le produit est remis en stock.
7. Pilotage : générez les rapports PDF sur la période sélectionnée et consultez le journal d'audit.

## Sauvegarde et restauration

La base de développement est le fichier `db.sqlite3`. Pour sauvegarder l'application :

```powershell
Copy-Item db.sqlite3 "sauvegarde-pharmagest-$(Get-Date -Format yyyyMMdd-HHmmss).sqlite3"
Copy-Item media "sauvegarde-media-$(Get-Date -Format yyyyMMdd-HHmmss)" -Recurse
```

Pour restaurer, arrêtez le serveur, replacez le fichier sauvegardé sous le nom `db.sqlite3`, puis redémarrez. Testez régulièrement la restauration sur une copie avant toute mise en production.

## Structure

- `config/` : réglages et routage du projet.
- `gestion/` : modèles, formulaires, vues, administration, PDF, tests, commande `seed_demo`.
- `templates/gestion/` : interface Bootstrap.
- `static/css/pharmagest.css`, `static/js/pharmagest.js` et `static/img/` : thème, interactions et favicon.

## Configuration

Les paramètres de la pharmacie sont modifiables par variables d'environnement :

```text
DJANGO_SECRET_KEY
DJANGO_DEBUG
DJANGO_ALLOWED_HOSTS
PHARMACIE_NOM
PHARMACIE_ADRESSE
PHARMACIE_TELEPHONE
PHARMACIE_EMAIL
PHARMACIE_NIF
PHARMACIE_STAT
SEUIL_PEREMPTION_JOURS
```

En production, définir `DJANGO_DEBUG=0`, une clé secrète robuste et servir les fichiers statiques avec `python manage.py collectstatic`.
