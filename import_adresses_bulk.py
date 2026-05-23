#!/usr/bin/env python3
"""Import BAN addresses: parse CSV on host, pipe SQL into Docker psql.

Usage: python import_adresses_bulk.py | docker compose exec -T db psql -U cadastre
"""

import csv
import sys
from pathlib import Path

BATCH_SIZE = 1000


def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else "data/adresses/adresses-01.csv"

    print(f"-- Importing {filepath}...", file=sys.stderr, flush=True)

    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = []
        count = 0

        def flush_rows():
            nonlocal rows
            if not rows:
                return
            vals = ",\n".join(rows)
            print(
                f"INSERT INTO cadastre_adresse "
                f"(id_ban, numero, rep, nom_voie, code_postal, code_insee, "
                f"nom_commune) "
                f"VALUES\n{vals}\nON CONFLICT (id_ban) DO NOTHING;"
            )
            rows = []

        for row in reader:
            id_ban = row.get("id", "").replace("'", "''")
            if not id_ban:
                continue

            numero = row.get("numero", "").replace("'", "''")
            rep = row.get("rep", "").replace("'", "''")
            nom_voie = row.get("nom_voie", "").replace("'", "''")
            code_postal = row.get("code_postal", "").replace("'", "''")
            code_insee = row.get("code_insee", "").replace("'", "''")
            nom_commune = row.get("nom_commune", "").replace("'", "''")

            rows.append(
                f"('{id_ban}', '{numero}', '{rep}', '{nom_voie}', "
                f"'{code_postal}', '{code_insee}', '{nom_commune}')"
            )

            if len(rows) >= BATCH_SIZE:
                flush_rows()
                count += BATCH_SIZE
                if count % 10000 == 0:
                    print(f"-- {count} adresses...", file=sys.stderr, flush=True)

        flush_rows()
        count += len(rows)
        print(f"-- Done: {count} adresses imported", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
