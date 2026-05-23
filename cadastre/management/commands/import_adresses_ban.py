import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from cadastre.models import Adresse, Parcelle, ParcelleAdresse


class Command(BaseCommand):
    help = "Import BAN addresses from CSV files in /data/adresses/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default="/data/adresses",
            help="Directory containing BAN CSV files",
        )

    def handle(self, *args, **options):
        data_dir = Path(options["dir"])
        if not data_dir.exists():
            self.stderr.write(f"Directory not found: {data_dir}")
            return

        files = list(data_dir.glob("*.csv"))
        self.stdout.write(f"Found {len(files)} files to process")

        total_adresses = 0
        total_links = 0

        for filepath in sorted(files):
            ads, links = self._process_file(filepath)
            total_adresses += ads
            total_links += links

        self.stdout.write(
            f"Done. Addresses: {total_adresses}, Parcelle links: {total_links}"
        )

    def _process_file(self, filepath):
        self.stdout.write(f"Processing {filepath.name}...")
        adresses_count = 0
        links_count = 0

        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")

            for row in reader:
                id_ban = row.get("id", "")
                if not id_ban:
                    continue



                Adresse.objects.update_or_create(
                    id_ban=id_ban,
                    defaults={
                        "numero": row.get("numero", ""),
                        "rep": row.get("rep", ""),
                        "nom_voie": row.get("nom_voie", ""),
                        "code_postal": row.get("code_postal", ""),
                        "code_insee": row.get("code_insee", ""),
                        "nom_commune": row.get("nom_commune", ""),
                    },
                )
                adresses_count += 1

        self.stdout.write(
            f"  {filepath.name}: {adresses_count} adresses, {links_count} links"
        )
        return adresses_count, links_count


