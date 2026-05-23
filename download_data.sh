#!/usr/bin/env bash
set -euo pipefail

DEP="${1:-01}"

_dept_name() {
  case "$1" in
    01) echo "Ain";; 02) echo "Aisne";; 03) echo "Allier";;
    04) echo "Alpes-de-Haute-Provence";; 05) echo "Hautes-Alpes";;
    06) echo "Alpes-Maritimes";; 07) echo "Ardèche";; 08) echo "Ardennes";;
    09) echo "Ariège";; 10) echo "Aube";;
    *) echo "$1";;
  esac
}

DEPT_NAME=$(_dept_name "$DEP")
echo "=== [$DEP] $DEPT_NAME — Download and import ==="

mkdir -p data/parcelles data/adresses

echo "[$DEP] 1/2 Downloading parcelles GeoJSON..."
curl -L -o "data/parcelles/cadastre-${DEP}-parcelles.json.gz" \
  "https://cadastre.data.gouv.fr/data/etalab-cadastre/2026-03-01/geojson/departements/${DEP}/cadastre-${DEP}-parcelles.json.gz"

echo "[$DEP] 2/2 Downloading BAN addresses..."
curl -L -o "data/adresses/adresses-${DEP}.csv.gz" \
  "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-${DEP}.csv.gz"

echo ""
echo "[$DEP] Importing parcelles (bulk SQL via psql)..."
uv run python import_parcelles.py "$DEP" | docker compose exec -T db psql -U cadastre -v ON_ERROR_STOP=1

echo ""
echo "[$DEP] Importing BAN addresses..."
gunzip -f "data/adresses/adresses-${DEP}.csv.gz"
uv run python import_ban.py "$DEP" | docker compose exec -T db psql -U cadastre -v ON_ERROR_STOP=1

echo ""
echo "[$DEP] Creating parcel-address links via BAN-PLUS WFS..."
uv run python download_banplus.py "$DEP" | docker compose exec -T db psql -U cadastre -v ON_ERROR_STOP=1

echo ""
echo "[$DEP] Updating commune names from BAN data..."
docker compose exec -T db psql -U cadastre -c "
UPDATE cadastre_commune c
SET nom = a.nom_commune
FROM (
  SELECT DISTINCT code_insee, nom_commune
  FROM cadastre_adresse
  WHERE nom_commune != ''
) a
WHERE c.code_insee = a.code_insee
  AND c.nom = c.code_insee;
"

echo "[$DEP] Marking parcels with addresses..."
docker compose exec -T db psql -U cadastre -c "
UPDATE cadastre_parcelle
SET has_address = true
WHERE idu IN (
  SELECT DISTINCT parcelle_id FROM cadastre_parcelleadresse
);
"

echo ""
echo "[$DEP] Done ==="
docker compose exec -T db psql -U cadastre -c "
SELECT 'Parcelles' t, count(*) FROM cadastre_parcelle
UNION ALL SELECT 'Adresses', count(*) FROM cadastre_adresse
UNION ALL SELECT 'Liens', count(*) FROM cadastre_parcelleadresse
UNION ALL SELECT 'Communes', count(*) FROM cadastre_commune;
"
