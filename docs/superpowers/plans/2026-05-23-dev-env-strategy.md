# Dev Environment Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create snapshot/restore tools and a dev seed script for fast database iteration.

**Architecture:** Three shell scripts in `bin/` that reuse existing Docker and Python tooling. Snapshots use `pg_dump`/`pg_restore` via docker compose exec. Dev seed downloads commune-level cadastre data and filters BAN CSVs by commune code — all existing Python scripts work unchanged.

**Tech Stack:** bash, pg_dump/pg_restore, Docker, curl, awk

---

### Task 1: Create `bin/` directory and `.gitignore` update

**Files:**
- Create: `bin/.gitkeep`
- Modify: `.gitignore`

- [ ] **Step 1: Create `bin/` directory**

```bash
mkdir -p bin
```

- [ ] **Step 2: Add `.gitkeep` to track empty directory**

```bash
touch bin/.gitkeep
```

- [ ] **Step 3: Add `data/snapshots/` to `.gitignore`**

Edit `.gitignore` — append after the last line:

```
data/snapshots/
```

- [ ] **Step 4: Commit**

```bash
git add bin/.gitkeep .gitignore
git commit -m "chore: add bin/ dir and ignore data/snapshots/"
```

---

### Task 2: `bin/pg_snapshot.sh`

**Files:**
- Create: `bin/pg_snapshot.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
set -euo pipefail

NAME="${1:?Usage: pg_snapshot.sh <name>}"
mkdir -p data/snapshots

docker compose exec db pg_dump -U cadastre --format=custom --compress=9 -f /tmp/snapshot.dump cadastre
docker compose cp db:/tmp/snapshot.dump "data/snapshots/${NAME}.dump"

echo "Snapshot saved to data/snapshots/${NAME}.dump"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x bin/pg_snapshot.sh
```

- [ ] **Step 3: Commit**

```bash
git add bin/pg_snapshot.sh
git commit -m "feat: add pg_snapshot.sh for dumping DB"
```

---

### Task 3: `bin/pg_restore_snapshot.sh`

**Files:**
- Create: `bin/pg_restore_snapshot.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
set -euo pipefail

NAME="${1:?Usage: pg_restore_snapshot.sh <name>}"
SNAPSHOT="data/snapshots/${NAME}.dump"

if [ ! -f "$SNAPSHOT" ]; then
  echo "Snapshot not found: $SNAPSHOT"
  exit 1
fi

docker compose cp "$SNAPSHOT" db:/tmp/snapshot.dump
docker compose exec db pg_restore -U cadastre --clean --if-exists --dbname=cadastre /tmp/snapshot.dump

echo "Restored from data/snapshots/${NAME}.dump"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x bin/pg_restore_snapshot.sh
```

- [ ] **Step 3: Commit**

```bash
git add bin/pg_restore_snapshot.sh
git commit -m "feat: add pg_restore_snapshot.sh for restoring DB snapshots"
```

---

### Task 4: `bin/seed_dev.sh`

**Files:**
- Create: `bin/seed_dev.sh`

- [ ] **Step 1: Write the script**

```bash
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
```

- [ ] **Step 2: Make executable**

```bash
chmod +x bin/seed_dev.sh
```

- [ ] **Step 3: Commit**

```bash
git add bin/seed_dev.sh
git commit -m "feat: add seed_dev.sh for single-commune import"
```

---

### Task 5: Update AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Add dev environment section to AGENTS.md**

Append to the end of AGENTS.md:

```markdown
## Dev Environment

### Snapshots (save/restore DB state)
```bash
bash bin/pg_snapshot.sh base-78-91        # save current DB
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
```

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: document dev environment tools in AGENTS.md"
```
