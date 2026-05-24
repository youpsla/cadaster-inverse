#!/usr/bin/env python3
"""Import cadastre parcelles GeoJSON for a department. Reads data/parcelles/cadastre-{dep}-parcelles.json.gz"""
import gzip
import json
import os
import sys

BATCH = 1000

DEPT_NAMES = {
    "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence",
    "05": "Hautes-Alpes", "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes",
    "09": "Ariège", "10": "Aube", "11": "Aude", "12": "Aveyron", "13": "Bouches-du-Rhône",
    "14": "Calvados", "15": "Cantal", "16": "Charente", "17": "Charente-Maritime",
    "18": "Cher", "19": "Corrèze", "21": "Côte-d'Or", "22": "Côtes-d'Armor",
    "23": "Creuse", "24": "Dordogne", "25": "Doubs", "26": "Drôme", "27": "Eure",
    "28": "Eure-et-Loir", "29": "Finistère", "2A": "Corse-du-Sud", "2B": "Haute-Corse",
    "30": "Gard", "31": "Haute-Garonne", "32": "Gers", "33": "Gironde",
    "34": "Hérault", "35": "Ille-et-Vilaine", "36": "Indre", "37": "Indre-et-Loire",
    "38": "Isère", "39": "Jura", "40": "Landes", "41": "Loir-et-Cher", "42": "Loire",
    "43": "Haute-Loire", "44": "Loire-Atlantique", "45": "Loiret", "46": "Lot",
    "47": "Lot-et-Garonne", "48": "Lozère", "49": "Maine-et-Loire", "50": "Manche",
    "51": "Marne", "52": "Haute-Marne", "53": "Mayenne", "54": "Meurthe-et-Moselle",
    "55": "Meuse", "56": "Morbihan", "57": "Moselle", "58": "Nièvre", "59": "Nord",
    "60": "Oise", "61": "Orne", "62": "Pas-de-Calais", "63": "Puy-de-Dôme",
    "64": "Pyrénées-Atlantiques", "65": "Hautes-Pyrénées", "66": "Pyrénées-Orientales",
    "67": "Bas-Rhin", "68": "Haut-Rhin", "69": "Rhône", "70": "Haute-Saône",
    "71": "Saône-et-Loire", "72": "Sarthe", "73": "Savoie", "74": "Haute-Savoie",
    "75": "Paris", "76": "Seine-Maritime", "77": "Seine-et-Marne", "78": "Yvelines",
    "79": "Deux-Sèvres", "80": "Somme", "81": "Tarn", "82": "Tarn-et-Garonne",
    "83": "Var", "84": "Vaucluse", "85": "Vendée", "86": "Vienne", "87": "Haute-Vienne",
    "88": "Vosges", "89": "Yonne", "90": "Territoire de Belfort", "91": "Essonne",
    "92": "Hauts-de-Seine", "93": "Seine-Saint-Denis", "94": "Val-de-Marne",
    "95": "Val-d'Oise",
}

dep = sys.argv[1]
path = f"data/parcelles/cadastre-{dep}-parcelles.json.gz"

with gzip.open(path, "rt") as f:
    data = json.load(f)
features = data["features"]
seen_deps, seen_coms, rows = set(), set(), []
count = 0


def flush():
    global rows
    if not rows:
        return
    vals = ",\n".join(rows)
    print(
        "INSERT INTO cadastre_parcelle "
        "(idu, geometry, contenance, section, numero, commune_id, has_address) "
        "VALUES\n"
        f"{vals}\n"
        "ON CONFLICT (idu) DO NOTHING;"
    )
    rows = []


for feat in features:
    p = feat["properties"]
    idu = p["id"]
    com_code = idu[:5]
    dep_code = idu[:2]
    if dep_code not in seen_deps:
        dep_name = DEPT_NAMES.get(dep_code, dep_code)
        print(
            f"INSERT INTO cadastre_departement (code, nom) VALUES "
            f"('{dep_code}', '{dep_name}') ON CONFLICT DO NOTHING;"
        )
        seen_deps.add(dep_code)
    if com_code not in seen_coms:
        print(
            f"INSERT INTO cadastre_commune (code_insee, nom, code_postal, departement_id) VALUES "
            f"('{com_code}', '{com_code}', '{com_code[:2]}000', '{dep_code}') ON CONFLICT DO NOTHING;"
        )
        seen_coms.add(com_code)
    g = json.dumps(feat["geometry"]).replace("'", "''")
    c = p.get("contenance", 0)
    sec = (p.get("section") or "").replace("'", "''")
    num = (p.get("numero") or "").replace("'", "''")
    rows.append(
        f"('{idu}', ST_GeomFromGeoJSON('{g}'), {c}, '{sec}', "
        f"'{num}', '{com_code}', false)"
    )
    if len(rows) >= BATCH:
        flush()
        count += BATCH
        print(f"\r-- {count}/{len(features)} parcelles   ", file=sys.stderr, end="", flush=True)

flush()
print(file=sys.stderr)
print(f"-- Done: {count + len(rows)} parcelles", file=sys.stderr)
