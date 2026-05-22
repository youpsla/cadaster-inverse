#!/usr/bin/env bash
set -euo pipefail

echo "=== Download cadastre and BAN data for department 01 (Ain) ==="

mkdir -p data/parcelles data/adresses

echo "1/2 Downloading parcelles GeoJSON..."
curl -L -o data/parcelles/cadastre-01-parcelles.json.gz \
  "https://cadastre.data.gouv.fr/data/etalab-cadastre/2026-03-01/geojson/departements/01/cadastre-01-parcelles.json.gz"

echo "2/2 Downloading BAN addresses..."
curl -L -o data/adresses/adresses-01.csv.gz \
  "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-01.csv.gz"

echo ""
echo "=== Import parcelles (bulk SQL via psql) ==="
gunzip -c data/parcelles/cadastre-01-parcelles.json.gz | \
uv run python -c "
import gzip, json, sys
BATCH = 1000
with gzip.open('data/parcelles/cadastre-01-parcelles.json.gz', 'rt') as f:
    data = json.load(f)
features = data['features']
seen_deps, seen_coms, rows = set(), set(), []
count = 0
def flush():
    global rows
    if not rows: return
    vals = ',\n'.join(rows)
    print(f'INSERT INTO cadastre_parcelle (idu, geometry, contenance, prefixe, section, numero, arpente, commune_id, created, updated) VALUES\n{vals}\nON CONFLICT (idu) DO NOTHING;')
    rows = []
for feat in features:
    p = feat['properties']; idu = p['id']; com_code = idu[:5]; dep_code = idu[:2]
    if dep_code not in seen_deps:
        print(f\"INSERT INTO cadastre_departement (code, nom) VALUES ('{dep_code}', '{dep_code}') ON CONFLICT DO NOTHING;\")
        seen_deps.add(dep_code)
    if com_code not in seen_coms:
        print(f\"INSERT INTO cadastre_commune (code_insee, nom, code_postal, departement_id) VALUES ('{com_code}', '{com_code}', '{com_code[:2]}000', '{dep_code}') ON CONFLICT DO NOTHING;\")
        seen_coms.add(com_code)
    g = json.dumps(feat['geometry']).replace(\"'\", \"''\")
    c = p.get('contenance', 0); pre = (p.get('prefixe') or '').replace(\"'\", \"''\")
    sec = (p.get('section') or '').replace(\"'\", \"''\"); num = (p.get('numero') or '').replace(\"'\", \"''\")
    arp = 'true' if p.get('arpente') else 'false'
    cr = f\"'{p['created']}'::date\" if p.get('created') else 'NULL'
    up = f\"'{p['updated']}'::date\" if p.get('updated') else 'NULL'
    rows.append(f\"('{idu}', ST_GeomFromGeoJSON('{g}'), {c}, '{pre}', '{sec}', '{num}', {arp}, '{com_code}', {cr}, {up})\")
    if len(rows) >= BATCH: flush(); count += BATCH; print(f'-- {count}/{len(features)}', file=sys.stderr, flush=True)
flush(); print(f'-- Done: {count + len(rows)} parcelles', file=sys.stderr)
" | docker compose exec -T db psql -U cadastre -v ON_ERROR_STOP=1

echo ""
echo "=== Import adresses BAN ==="
gunzip -f data/adresses/adresses-01.csv.gz
uv run python -c "
import csv, sys
BATCH = 1000
with open('data/adresses/adresses-01.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    rows = []; count = 0
    def flush():
        global rows
        if not rows: return
        vals = ',\n'.join(rows)
        print(f'INSERT INTO cadastre_adresse (id_ban, numero, rep, nom_voie, code_postal, code_insee, nom_commune, lon, lat, cad_parcelles) VALUES\n{vals}\nON CONFLICT (id_ban) DO NOTHING;')
        rows = []
    for row in reader:
        id_ban = row.get('id', '').replace(\"'\", \"''\")
        if not id_ban: continue
        nu = row.get('numero', '').replace(\"'\", \"''\"); rep = row.get('rep', '').replace(\"'\", \"''\")
        nv = row.get('nom_voie', '').replace(\"'\", \"''\"); cp = row.get('code_postal', '').replace(\"'\", \"''\")
        ci = row.get('code_insee', '').replace(\"'\", \"''\"); nc = row.get('nom_commune', '').replace(\"'\", \"''\")
        cad = row.get('cad_parcelles', '').replace(\"'\", \"''\")
        lon = row.get('lon', '') or 'NULL'; lat = row.get('lat', '') or 'NULL'
        rows.append(f\"('{id_ban}', '{nu}', '{rep}', '{nv}', '{cp}', '{ci}', '{nc}', {lon}, {lat}, '{cad}')\")
        if len(rows) >= BATCH: flush(); count += BATCH
    flush()
    print(f'-- Done: {count + len(rows)} adresses', file=sys.stderr)
" | docker compose exec -T db psql -U cadastre -v ON_ERROR_STOP=1

echo ""
echo "=== Creating parcel-address links ==="
docker compose exec -T db psql -U cadastre -c "
INSERT INTO cadastre_parcelleadresse (parcelle_id, adresse_id)
SELECT p.parcelle_id, p.adresse_id
FROM (
  SELECT trim(unnest(string_to_array(a.cad_parcelles, '|'))) AS parcelle_id, a.id_ban AS adresse_id
  FROM cadastre_adresse a
  WHERE a.cad_parcelles != ''
) p
WHERE p.parcelle_id IN (SELECT idu FROM cadastre_parcelle)
ON CONFLICT DO NOTHING;
"

echo ""
echo "=== Done ==="
docker compose exec -T db psql -U cadastre -c "
SELECT 'Parcelles' t, count(*) FROM cadastre_parcelle
UNION ALL SELECT 'Adresses', count(*) FROM cadastre_adresse
UNION ALL SELECT 'Liens', count(*) FROM cadastre_parcelleadresse
UNION ALL SELECT 'Communes', count(*) FROM cadastre_commune;
"
