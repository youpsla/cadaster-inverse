# Cadastre Inversé

## Stack
Django 6, PostgreSQL 16 + PostGIS, HTMX (+ django-htmx), Leaflet/OSM, uv, Docker, gunicorn
Nothing installed on host — everything runs in Docker

## Quick Start
docker compose up -d            # start PostGIS + web
docker compose exec web uv run python manage.py migrate  # first time / after model changes
http://localhost:8000/            # open app
docker compose up -d --build web  # rebuild web after changes
# Static/template changes need --build; ./data and ./static are volume-mounted
# uv.lock is committed for reproducible builds

## Routes
/                   → index (departement selector + search form)
/communes/          → HTMX partial (commune <select> by departement)
/search/            → HTMX partial (results list + embedded GeoJSON for Leaflet)

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
- Address ↔ Parcel linkage: ParcelleAdresse junction table from BAN-PLUS WFS (not BAN CSV cad_parcelles)
- Parcelle.has_address boolean flag; set via UPDATE after import, used to filter habitat-only parcels
- Data files in ./data/ volume; gitignored for large CSVs/GeoJSON
- Current import scope: 10 departments, ~9M parcelles, ~1.7M adresses, ~1.8M liens

## Dev Environment

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
