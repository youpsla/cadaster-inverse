"""Import parcel GeoJSON files.

For the initial bulk import, use the one-time script:
    uv run python import_parcelles_bulk.py | docker compose exec -T db psql -U cadastre

For incremental updates with small .json.gz files, this command works with Django ORM.
"""

import gzip
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry

from cadastre.models import Commune, Departement, Parcelle


class Command(BaseCommand):
    help = "Import small parcel GeoJSON files"

    def add_arguments(self, parser):
        parser.add_argument("--dir", type=str, default="/data/parcelles")

    def handle(self, *args, **options):
        data_dir = Path(options["dir"])
        if not data_dir.exists():
            self.stderr.write(f"Directory not found: {data_dir}")
            return

        files = list(data_dir.glob("*.json.gz"))
        self.stdout.write(f"Found {len(files)} files")

        for filepath in sorted(files):
            self._process_file(filepath)

    def _process_file(self, filepath):
        self.stdout.write(f"Processing {filepath.name}...")
        with gzip.open(filepath, "rt", encoding="utf-8") as f:
            data = json.load(f)

        features = data.get("features", [])
        created = 0

        for feature in features:
            props = feature["properties"]
            idu = props["id"]
            commune_code = idu[:5]
            dep_code = idu[:2]

            Departement.objects.get_or_create(
                code=dep_code, defaults={"nom": dep_code}
            )

            Commune.objects.get_or_create(
                code_insee=commune_code,
                defaults={
                    "departement_id": dep_code,
                    "code_postal": commune_code[:2] + "000",
                    "nom": commune_code,
                },
            )

            _, was_created = Parcelle.objects.update_or_create(
                idu=idu,
                defaults={
                    "geometry": GEOSGeometry(json.dumps(feature["geometry"])),
                    "contenance": props.get("contenance", 0),
                    "section": props.get("section", ""),
                    "numero": props.get("numero", ""),
                    "commune_id": commune_code,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(f"  {filepath.name}: +{created}")
