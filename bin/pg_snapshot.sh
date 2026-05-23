#!/usr/bin/env bash
set -euo pipefail

NAME="${1:?Usage: pg_snapshot.sh <name>}"
mkdir -p data/snapshots

docker compose exec db pg_dump -U cadastre --format=custom --compress=9 -f /tmp/snapshot.dump cadastre
docker compose cp db:/tmp/snapshot.dump "data/snapshots/${NAME}.dump"

echo "Snapshot saved to data/snapshots/${NAME}.dump"
