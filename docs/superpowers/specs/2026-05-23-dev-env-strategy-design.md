# Dev Environment Strategy

## Context

Working with a full production-like database (~9M parcelles, ~1.7M adresses) is slow for iterative development and feature exploration. We need two complementary tools:

1. **Snapshots** — freeze a known-good state and restore it instantly
2. **Dev seed** — import a tiny subset (1 commune) for fast iteration

## Design

### 1. Snapshot system (`bin/pg_snapshot.sh` / `bin/pg_restore_snapshot.sh`)

- `pg_snapshot.sh <name>` — runs `pg_dump --format=custom --compress=9` inside the db container, copies the dump to `data/snapshots/<name>.dump`
- `pg_restore_snapshot.sh <name>` — copies the dump back into the container, runs `pg_restore --clean --if-exists --dbname=cadastre`, effectively replacing the entire database content
- Snapshots are gitignored (in `data/snapshots/`) — downloaded via `download_snapshot.sh` or created locally

**Use cases:**
- `bash bin/pg_snapshot.sh base-78-91` after importing 2 departments
- Experiment with features, mutate data, break things
- `bash bin/pg_restore_snapshot.sh base-78-91` → back to clean state in seconds

### 2. Dev seed (`bin/seed_dev.sh <commune_code>`)

Imports a single commune (~few thousand parcels) for daily development:

- Downloads commune-level GeoJSON from cadastre.data.gouv.fr (URL pattern: `.../geojson/communes/{dep}/{commune}/cadastre-{commune}-parcelles.json.gz`)
- Filters department-level BAN CSV by `code_insee` for matching addresses
- Runs BAN-PLUS WFS import filtered to the commune
- Output: a working database with real geometries, addresses, and links, but tiny

**Use cases:**
- `bash bin/seed_dev.sh 01001` → Bourg-en-Bresse ready in seconds
- Iterate on search queries, map interactions, UI — without waiting

### 3. File layout

```
bin/
  pg_snapshot.sh          # dump DB to data/snapshots/<name>.dump
  pg_restore_snapshot.sh  # restore DB from data/snapshots/<name>.dump
  seed_dev.sh             # import a single commune
data/
  snapshots/              # gitignored, managed via scripts
.gitignore                # add data/snapshots/
AGENTS.md                 # document both tools
```

### 4. Dependencies

- Docker running with `db` service up
- `pg_dump` / `pg_restore` available inside the `postgis/postgis:16-3.5` image (std)
- `curl` inside the container (std) or on host (for download)
- No new Python dependencies
