# Cadastre Inversé

## Stack
Django 5, PostgreSQL 16 + PostGIS, HTMX, Leaflet/OSM, uv, Docker, gunicorn
Nothing installed on host — everything runs in Docker

## Quick Start
docker compose up -d            # start PostGIS + web
http://localhost:8000/            # open app
docker compose up -d --build web  # rebuild web after changes

## Data Import
bash download_data.sh             # download + bulk-import Ain (01) data
# 1.3M+ parcelles: Python generates SQL, piped to psql (ORM too slow)
# BAN CSV uses ';' delimiter; cad_parcelles field links parcels|addresses
# Large files (>100MB) tracked via download script, NOT committed to git

## Key Patterns
- PostGIS image: postgis/postgis:16-3.5 with platform: linux/amd64 (Apple Silicon)
- Bulk SQL pipe: python generate_sql.py | docker compose exec -T db psql -U cadastre
- HTMX search returns GeoJSON in <script> tag; JS listens to htmx:afterSwap for Leaflet
- Models: Departement, Commune, Parcelle (PolygonField), Adresse, ParcelleAdresse (M2M)
- Address ↔ Parcel linkage: ParcelleAdresse junction table from BAN cad_parcelles field
- Data files in ./data/ volume; gitignored for large CSVs/GeoJSON
