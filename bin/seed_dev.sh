#!/usr/bin/env bash
set -euo pipefail

COMMUNE="${1:?Usage: seed_dev.sh <commune_code>  (e.g. 01001 for Bourg-en-Bresse)}"
DEP="${COMMUNE:0:2}"

echo "=== Seeding commune $COMMUNE (dep $DEP) ==="

mkdir -p data/parcelles data/adresses

# 1. Download commune-level parcelles GeoJSON
echo "[1/5] Downloading parcelles for commune $COMMUNE..."
curl -L -o "data/parcelles/cadastre-${COMMUNE}-parcelles.json.gz" \
  "https://cadastre.data.gouv.fr/data/etalab-cadastre/2026-03-01/geojson/communes/${DEP}/${COMMUNE}/cadastre-${COMMUNE}-parcelles.json.gz"

# Copy to dep-level path (import_parcelles.py reads a dep-level path)
cp "data/parcelles/cadastre-${COMMUNE}-parcelles.json.gz" "data/parcelles/cadastre-${DEP}-parcelles.json.gz"

# 2. Import parcelles
echo "[2/5] Importing parcelles..."
uv run python import_parcelles.py "$DEP" | docker compose exec -T db psql -U cadastre -v ON_ERROR_STOP=1

# 3. Download and filter BAN CSV
echo "[3/5] Downloading BAN addresses..."
rm -f "data/adresses/adresses-${DEP}.csv"
curl -L -o "data/adresses/adresses-${DEP}.csv.gz" \
  "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-${DEP}.csv.gz"
echo "Filtering to commune $COMMUNE..."
gunzip -f "data/adresses/adresses-${DEP}.csv.gz"
awk -F';' -v code="$COMMUNE" 'NR==1 || $6 == code' \
  "data/adresses/adresses-${DEP}.csv" > /tmp/adresses-filtered.csv
mv /tmp/adresses-filtered.csv "data/adresses/adresses-${DEP}.csv"
uv run python import_ban.py "$DEP" | docker compose exec -T db psql -U cadastre -v ON_ERROR_STOP=1

# 4. BAN-PLUS address-parcel links
echo "[4/5] Creating address-parcel links (BAN-PLUS)..."
uv run python download_banplus.py "$DEP" | docker compose exec -T db psql -U cadastre -v ON_ERROR_STOP=1

# 5. Post-import updates
echo "[5/5] Post-import updates..."
docker compose exec -T db psql -U cadastre -c "
UPDATE cadastre_commune c SET nom = a.nom_commune
FROM (SELECT DISTINCT code_insee, nom_commune FROM cadastre_adresse WHERE nom_commune != '') a
WHERE c.code_insee = a.code_insee AND c.nom = c.code_insee;
"
docker compose exec -T db psql -U cadastre -c "
UPDATE cadastre_parcelle SET has_address = true
WHERE idu IN (SELECT DISTINCT parcelle_id FROM cadastre_parcelleadresse);
"

echo ""
echo "=== Done: commune $COMMUNE ==="
docker compose exec -T db psql -U cadastre -c "
SELECT 'Parcelles' t, count(*) FROM cadastre_parcelle
UNION ALL SELECT 'Adresses', count(*) FROM cadastre_adresse
UNION ALL SELECT 'Liens', count(*) FROM cadastre_parcelleadresse
UNION ALL SELECT 'Communes', count(*) FROM cadastre_commune;
"
