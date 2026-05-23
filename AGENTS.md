# Cadastre Inversé

## Stack
Django 6, PostgreSQL 16 + PostGIS, HTMX (+ django-htmx), Leaflet/OSM, uv, Docker, gunicorn
Nothing installed on host — everything runs in Docker

## Quick Start
docker compose up -d            # start PostGIS + web
docker compose exec web uv run python manage.py migrate  # first time / after model changes
docker compose exec web uv run python manage.py makemigrations  # after model field changes
http://localhost:8000/            # open app
docker compose up -d         # start (rebuild only after pyproject.toml changes)
# No need to rebuild for Python/template/static changes — they are volume-mounted
# Rebuild only when pyproject.toml or Dockerfile changes
# uv.lock is committed for reproducible builds
# Gotcha: compose runs `migrate` before `gunicorn` at startup — if a migration fails,
# the web container exits immediately. Use `docker compose run --rm web` for one-off commands.

## Routes
/                            → Landing page SEO (départements links + search form)
/communes/                   → HTMX partial (commune <select> by departement)
/search/                     → HTMX partial (results list + embedded GeoJSON for Leaflet)
/departement/<slug_dep>/     → SEO landing page for a département (ex: /departement/ain/)
/departement/<slug_dep>/<slug_commune>/  → SEO landing page for a commune (ex: /departement/ain/bourg-en-bresse/)
/robots.txt                  → Crawl directives (disallow /admin/, /communes/, /search/)
/sitemap.xml                 → Sitemap index
/sitemap-<section>.xml       → Per-section sitemap (departements, communes)

### URL Format
- **Department slug**: `slugify(nom)` — ex: `ain`, `yvelines`, `alpes-de-haute-provence`
- **Commune slug**: `slugify(nom)` — ex: `bourg-en-bresse`, `acheres`
- No INSEE codes in URLs — slug-based for SEO
- Slugs resolved via O(n) scan of Departement.objects.all() and Commune.filter(departement=dep) (11 dep, ~400 com/dep — negligible, optimize with caching if scale grows)
- Ambiguous commune names (e.g. "Aiglun" in 04 and 06) disambiguated by /departement/<slug>/ prefix

## Data Import
bash download_data.sh <dep>       # download + bulk-import a department (default: 01)
# Standalone Python scripts used for each phase (avoid inline -c quoting issues):
#   Management commands in cadastre/management/commands/ also available
#   import_parcelles.py — reads GeoJSON, outputs INSERTs (has_address=false)
#   import_ban.py — reads BAN CSV, outputs INSERTs
#   download_banplus.py — queries WFS, outputs INSERTs for lien_adresse_parcelle
# Pipeline tip: DO NOT pipe gunzip -c into import_parcelles.py (it opens the file directly);
#   the extra pipe causes SIGPIPE when combined with set -o pipefail.
# BAN CSV uses ';' delimiter — kept for address text data (numero, nom_voie, etc.)
# BAN-PLUS WFS (BAN-PLUS:lien_adresse_parcelle) used for address↔parcel linkage
#   WFS endpoint: https://data.geopf.fr/wfs/wfs
#   Pagination: STARTINDEX offset, maxFeatures=5000, increment by 5000
#   download_banplus.py uses stdlib only (urllib + xml.etree.ElementTree) — zero external deps
#   Filters via WHERE parcelle_id/adresse_id IN (SELECT ... FROM cadastre_*) to avoid FK errors
#   Some BAN-PLUS id_adr don't exist in cadastre_adresse (newer data) — silently filtered
# after import: UPDATE cadastre_parcelle SET has_address=true (marks urbanized parcels)
# Large files (>100MB) tracked via download script, NOT committed to git

## Key Patterns
- PostGIS image: postgis/postgis:16-3.5 with platform: linux/amd64 (Apple Silicon)
- Bulk SQL pipe: standalone Python script | docker compose exec -T db psql -U cadastre
- HTMX search returns GeoJSON in <script> tag; JS listens to htmx:afterSwap for Leaflet
- List→map highlight: map idu→L.layer in onEachFeature; toggle style via setStyle
- Event listeners on HTMX-swapped content: use document.body delegation, not direct DOM attachment
- Reset selection state (selectedIdu, layerMap) on every updateMap() call
- Models: Departement, Commune, Parcelle (PolygonField), Adresse, ParcelleAdresse (M2M)
- Parcelle.idu is CharField(max_length=14) — test data must not exceed 14 chars
- Address ↔ Parcel linkage: ParcelleAdresse junction table from BAN-PLUS WFS (not BAN CSV cad_parcelles)
- Parcelle.has_address boolean flag; set via UPDATE after import, used to filter habitat-only parcels
- Data files in ./data/ volume; gitignored for large CSVs/GeoJSON
- Current import scope: 10 departments, ~9M parcelles, ~1.7M adresses, ~1.8M liens
- SEO: meta tags via template blocks (no external pkg), robots.txt via TemplateView, slugs via slugify(nom)
- Sitemap URL pattern must be named `django.contrib.sitemaps.views.sitemap` (Django's index view reverses this internally)

## Tests

```bash
docker compose exec web uv run python manage.py test cadastre          # run all tests
docker compose exec web uv run python manage.py test cadastre.tests.TestModels   # models only
docker compose exec web uv run python manage.py test cadastre.tests.TestSearchView  # search view only
docker compose exec web uv run python manage.py test cadastre.tests.TestLandingView  # SEO landing
docker compose exec web uv run python manage.py test cadastre.tests.TestDepartementView  # SEO departement
docker compose exec web uv run python manage.py test cadastre.tests.TestCommuneView  # SEO commune
docker compose exec web uv run python manage.py test cadastre.tests.TestSitemap  # sitemap
docker compose exec web uv run python manage.py test cadastre.tests.TestRobotsTxt  # robots.txt

# Gotchas:
# - setUpTestData() must be decorated with @classmethod
# - After adding a model field, run makemigrations (not auto-detected)
# - CSRF_TRUSTED_ORIGINS values must start with a scheme; filter empty: [o for o in env.split(',') if o]
# - django.contrib.sites is required for sitemaps; update Site domain after deploy:
#     docker compose exec web uv run python manage.py shell -c "from django.contrib.sites.models import Site; s=Site.objects.get_current(); s.domain='<domain>'; s.save()"
#     docker compose restart web  # clear Site cache in gunicorn workers

Tests use Django TestCase with PostGIS test database. Created automatically.
GDAL/PostGIS not available on host — tests must run inside Docker.

## Production Deployment

```bash
# 0. Set your domain once, reuse in all commands
DOMAIN=cadastre.votre-domaine.com

# 1. Copy and edit env file with your domain and secrets
cp .env.prod.example .env.prod
# Générer SECRET_KEY : uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 2. Deploy with your domain
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 3. First-time only: create DB schema
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web uv run python manage.py migrate

# 4. Import data
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web bash download_data.sh 01

# 5. Check logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f caddy

# 6. Rebuild after code changes
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build web
```

Static files are collected at build time by the Dockerfile via `collectstatic --noinput`.
WhiteNoise serves them behind Caddy. No nginx needed for static files.

Caddy handles HTTPS (Let's Encrypt) automatically on ports 80/443.
The Caddyfile uses `{$DOMAIN:localhost}` — empty `$DOMAIN` = localhost (no TLS).

## Dev Environment

### Verify Docker configs
```bash
docker compose config                       # validate dev compose
docker compose -f docker-compose.yml -f docker-compose.prod.yml config  # validate prod merge
docker compose build web                    # verify Dockerfile builds cleanly
```

### Snapshots (save/restore DB state)
```bash
bash bin/pg_snapshot.sh base-78-91          # save current DB
bash bin/pg_restore_snapshot.sh base-78-91  # restore to saved state
```
Snapshots stored in `data/snapshots/` (gitignored). Create after importing
a known-good set of departments, then freely experiment and restore in seconds.

### Dev seed (tiny dataset for fast iteration)
```bash
bash bin/seed_dev.sh 01001   # import Bourg-en-Bresse only (~few K parcelles)
bash bin/seed_dev.sh 78350   # import a Yvelines commune
```
Downloads commune-level cadastre GeoJSON, filters BAN CSV by code_insee,
runs BAN-PLUS WFS (FK-guarded). Works with any commune code.
