import gzip
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry

from cadastre.models import Commune, Departement, Parcelle


class Command(BaseCommand):
    help = "Import parcel data from GeoJSON files in /data/parcelles/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default="/data/parcelles",
            help="Directory containing .json.gz files",
        )

    def handle(self, *args, **options):
        data_dir = Path(options["dir"])
        if not data_dir.exists():
            self.stderr.write(f"Directory not found: {data_dir}")
            return

        files = list(data_dir.glob("*.json.gz"))
        self.stdout.write(f"Found {len(files)} files to process")

        total_created = 0
        total_updated = 0

        for filepath in sorted(files):
            created, updated = self._process_file(filepath)
            total_created += created
            total_updated += updated

        self.stdout.write(f"Done. Created: {total_created}, Updated: {total_updated}")

    def _process_file(self, filepath):
        self.stdout.write(f"Processing {filepath.name}...")
        created = 0
        updated = 0

        with gzip.open(filepath, "rt", encoding="utf-8") as f:
            data = json.load(f)

        for feature in data.get("features", []):
            props = feature["properties"]
            idu = props["id"]
            commune_code = idu[:5]
            dep_code = idu[:2]

            departement, _ = Departement.objects.update_or_create(
                code=dep_code,
                defaults={"nom": dep_code},
            )

            commune, _ = Commune.objects.update_or_create(
                code_insee=commune_code,
                defaults={
                    "departement": departement,
                    "code_postal": commune_code[:2] + "000",
                    "nom": commune_code,
                },
            )

            geometry = GEOSGeometry(json.dumps(feature["geometry"]))

            _, was_created = Parcelle.objects.update_or_create(
                idu=idu,
                defaults={
                    "geometry": geometry,
                    "contenance": props.get("contenance", 0),
                    "prefixe": props.get("prefixe", ""),
                    "section": props.get("section", ""),
                    "numero": props.get("numero", ""),
                    "arpente": props.get("arpente", False),
                    "commune": commune,
                    "created": props.get("created"),
                    "updated": props.get("updated"),
                },
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(f"  {filepath.name}: +{created} ~{updated}")
        return created, updated
