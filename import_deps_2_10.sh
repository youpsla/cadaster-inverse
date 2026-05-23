#!/usr/bin/env bash
set -euo pipefail

DEPS=(03 04 05 06 07 08 09 10)
# 02 already done manually
TOTAL=${#DEPS[@]}
i=0

for DEP in "${DEPS[@]}"; do
  i=$((i + 1))
  echo ""
  echo "========================================================================"
  echo "  [$i/$TOTAL] Importing department $DEP"
  echo "========================================================================"
  echo ""

  bash download_data.sh "$DEP"
done

echo ""
echo "==============================================================================="
echo "  All departments imported successfully!"
echo "==============================================================================="
docker compose exec -T db psql -U cadastre -c "
SELECT 'Parcelles' t, count(*) FROM cadastre_parcelle
UNION ALL SELECT 'Adresses', count(*) FROM cadastre_adresse
UNION ALL SELECT 'Liens', count(*) FROM cadastre_parcelleadresse
UNION ALL SELECT 'Communes', count(*) FROM cadastre_commune
UNION ALL SELECT 'Departements', count(*) FROM cadastre_departement;
"
