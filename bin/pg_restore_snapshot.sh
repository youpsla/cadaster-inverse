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
