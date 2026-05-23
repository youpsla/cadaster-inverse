#!/usr/bin/env python3
"""Import BAN CSV addresses for a department. Reads data/adresses/adresses-{dep}.csv"""
import csv
import os
import sys

BATCH = 1000
dep = sys.argv[1]
path = f"data/adresses/adresses-{dep}.csv"

rows = []
count = 0


def flush():
    global rows
    if not rows:
        return
    vals = ",\n".join(rows)
    print(
        "INSERT INTO cadastre_adresse "
        "(id_ban, numero, rep, nom_voie, code_postal, code_insee, nom_commune) "
        "VALUES\n"
        f"{vals}\n"
        "ON CONFLICT (id_ban) DO NOTHING;"
    )
    rows = []


with open(path, encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter=";")
    for row in reader:
        id_ban = row.get("id", "").replace("'", "''")
        if not id_ban:
            continue
        nu = row.get("numero", "").replace("'", "''")
        rep = row.get("rep", "").replace("'", "''")
        nv = row.get("nom_voie", "").replace("'", "''")
        cp = row.get("code_postal", "").replace("'", "''")
        ci = row.get("code_insee", "").replace("'", "''")
        nc = row.get("nom_commune", "").replace("'", "''")
        rows.append(
            f"('{id_ban}', '{nu}', '{rep}', '{nv}', '{cp}', '{ci}', '{nc}')"
        )
        if len(rows) >= BATCH:
            flush()
            count += BATCH

flush()
print(f"-- Done: {count + len(rows)} adresses", file=sys.stderr)
