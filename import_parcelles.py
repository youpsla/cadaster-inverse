#!/usr/bin/env python3
"""Import cadastre parcelles GeoJSON for a department.
Streams the gzipped FeatureCollection to avoid loading the entire file in memory.
Reads data/parcelles/cadastre-{dep}-parcelles.json.gz
"""
import gzip
import json
import sys

BATCH = 1000
TOTAL_ESTIMATES = {
    "01": 375000, "02": 480000, "03": 380000, "04": 250000, "05": 200000,
    "06": 310000, "07": 280000, "08": 260000, "09": 260000, "10": 250000,
    "11": 370000, "12": 400000, "13": 540000, "14": 390000, "15": 260000,
    "16": 330000, "17": 440000, "18": 250000, "19": 230000, "21": 330000,
    "22": 500000, "23": 190000, "24": 400000, "25": 300000, "26": 300000,
    "27": 735000, "28": 589000, "29": 960000, "2A": 150000, "2B": 200000,
    "30": 530000, "31": 520000, "32": 330000, "33": 680000, "34": 460000,
    "35": 620000, "36": 220000, "37": 310000, "38": 410000, "39": 230000,
    "40": 310000, "41": 240000, "42": 280000, "43": 210000, "44": 610000,
    "45": 280000, "46": 250000, "47": 250000, "48": 110000, "49": 480000,
    "50": 340000, "51": 290000, "52": 190000, "53": 240000, "54": 300000,
    "55": 210000, "56": 520000, "57": 530000, "58": 200000, "59": 710000,
    "60": 380000, "61": 290000, "62": 530000, "63": 380000, "64": 370000,
    "65": 200000, "66": 200000, "67": 390000, "68": 270000, "69": 380000,
    "70": 190000, "71": 350000, "72": 310000, "73": 220000, "74": 280000,
    "75": 130000, "76": 510000, "77": 420000, "78": 360000, "79": 270000,
    "80": 410000, "81": 300000, "82": 250000, "83": 470000, "84": 280000,
    "85": 450000, "86": 280000, "87": 180000, "88": 260000, "89": 280000,
    "90": 35000, "91": 350000, "92": 150000, "93": 70000, "94": 110000,
    "95": 280000,
}

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


def stream_features(path):
    """Yield individual feature dicts from a gzipped GeoJSON FeatureCollection,
    without loading the entire file into memory."""
    with gzip.open(path, "rt") as f:
        state = "before_features"
        array_depth = 0
        buf = ""
        brace_depth = 0
        in_string = False
        escape = False
        for ch in iter(lambda: f.read(1), ""):
            if state == "before_features":
                buf += ch
                if '"features"' in buf or "'features'" in buf:
                    state = "in_array"
                    buf = ""
                continue
            if state == "in_array":
                if ch == "[" and array_depth == 0:
                    array_depth = 1
                elif ch == "[" and array_depth > 0:
                    array_depth += 1
                elif ch == "]":
                    array_depth -= 1
                    if array_depth == 0:
                        return
                if ch == "{":
                    state = "in_feature"
                    buf = ch
                    brace_depth = 1
                    in_string = False
                    escape = False
                continue
            if state == "in_feature":
                if escape:
                    buf += ch
                    escape = False
                    continue
                if ch == "\\":
                    buf += ch
                    escape = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    buf += ch
                    continue
                if in_string:
                    buf += ch
                    continue
                if ch == "{":
                    brace_depth += 1
                elif ch == "}":
                    brace_depth -= 1
                    if brace_depth == 0:
                        buf += ch
                        yield json.loads(buf)
                        state = "in_array"
                        buf = ""
                        continue
                buf += ch


dep = sys.argv[1]
path = f"data/parcelles/cadastre-{dep}-parcelles.json.gz"
total = TOTAL_ESTIMATES.get(dep, 1000000)

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


for feat in stream_features(path):
    p = feat["properties"]
    idu = p["id"]
    com_code = idu[:5]
    dep_code = idu[:2]
    if dep_code not in seen_deps:
        dep_name = DEPT_NAMES.get(dep_code, dep_code).replace("'", "''")
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
    g = json.dumps(feat["geometry"])
    c = p.get("contenance", 0)
    sec = (p.get("section") or "").replace("'", "''")
    num = (p.get("numero") or "").replace("'", "''")
    rows.append(
        f"('{idu}', ST_GeomFromGeoJSON($g${g}$g$), {c}, '{sec}', "
        f"'{num}', '{com_code}', false)"
    )
    if len(rows) >= BATCH:
        flush()
        count += BATCH
        print(f"\r-- {count}/{total} parcelles   ", file=sys.stderr, end="", flush=True)

flush()
print(file=sys.stderr)
