#!/usr/bin/env python3
"""Download BAN-PLUS lien_adresse_parcelle for a department and output SQL INSERTs.

Usage:
    uv run python download_banplus.py 01 | docker compose exec -T db psql -U cadastre
"""

import sys
import time
import xml.etree.ElementTree as ET
from urllib.request import urlopen, Request
from urllib.parse import urlencode

WFS_URL = "https://data.geopf.fr/wfs/wfs"
PAGE_SIZE = 5000
BATCH_SIZE = 1000
NS = {"bp": "http://BAN-PLUS"}


def build_url(dep_code: str, startindex: int) -> str:
    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAME": "BAN-PLUS:lien_adresse_parcelle",
        "CQL_FILTER": f"idu LIKE '{dep_code}%'",
        "COUNT": str(PAGE_SIZE),
        "STARTINDEX": str(startindex),
    }
    return f"{WFS_URL}?{urlencode(params)}"


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python download_banplus.py <dep_code>", file=sys.stderr)
        sys.exit(1)

    dep_code = sys.argv[1]
    startindex = 0
    total = 0
    rows = []

    def flush():
        nonlocal rows
        if not rows:
            return
        vals = ",\n".join(rows)
        print(
            "INSERT INTO cadastre_parcelleadresse (parcelle_id, adresse_id)\n"
            "SELECT v.parcelle_id, v.adresse_id\n"
            "FROM (VALUES\n"
            f"{vals}\n"
            ") AS v(parcelle_id, adresse_id)\n"
            "WHERE v.parcelle_id IN (SELECT idu FROM cadastre_parcelle)\n"
            "AND v.adresse_id IN (SELECT id_ban FROM cadastre_adresse)\n"
            "ON CONFLICT DO NOTHING;"
        )
        rows = []

    print(f"-- Downloading BAN-PLUS lien_adresse_parcelle for dep {dep_code}", file=sys.stderr)

    while True:
        url = build_url(dep_code, startindex)
        print(f"-- Page: startindex={startindex}", file=sys.stderr, flush=True)

        req = Request(url, headers={"User-Agent": "opencode-cadastre/1.0"})
        resp = urlopen(req)
        data = resp.read()
        root = ET.fromstring(data)

        number_returned = int(root.get("numberReturned", 0))
        number_matched = int(root.get("numberMatched", 0))

        if startindex == 0:
            print(f"-- Total liens: {number_matched}", file=sys.stderr)

        for lien in root.findall(".//{http://BAN-PLUS}lien_adresse_parcelle"):
            idu_el = lien.find("bp:idu", NS)
            id_adr_el = lien.find("bp:id_adr", NS)
            if idu_el is not None and id_adr_el is not None:
                idu = idu_el.text or ""
                id_adr = id_adr_el.text or ""
                if idu and id_adr:
                    idu_esc = idu.replace("'", "''")
                    id_adr_esc = id_adr.replace("'", "''")
                    rows.append(f"('{idu_esc}', '{id_adr_esc}')")
                    if len(rows) >= BATCH_SIZE:
                        flush()

        flush()

        total += number_returned
        print(f"--  {total}/{number_matched} liens processed", file=sys.stderr, flush=True)

        if number_returned < PAGE_SIZE:
            break

        startindex += PAGE_SIZE
        time.sleep(0.3)

    print(f"-- Done: {total} liens for dep {dep_code}", file=sys.stderr)


if __name__ == "__main__":
    main()
