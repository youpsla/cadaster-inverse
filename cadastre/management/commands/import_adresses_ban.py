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

                lon = self._safe_float(row.get("lon"))
                lat = self._safe_float(row.get("lat"))

                Adresse.objects.update_or_create(
                    id_ban=id_ban,
                    defaults={
                        "numero": row.get("numero", ""),
                        "rep": row.get("rep", ""),
                        "nom_voie": row.get("nom_voie", ""),
                        "code_postal": row.get("code_postal", ""),
                        "code_insee": row.get("code_insee", ""),
                        "nom_commune": row.get("nom_commune", ""),
                        "lon": lon,
                        "lat": lat,
                        "cad_parcelles": row.get("cad_parcelles", ""),
                    },
                )
                adresses_count += 1

                cad_parcelles_raw = row.get("cad_parcelles", "")
                if cad_parcelles_raw:
                    idu_list = [
                        idu.strip()
                        for idu in cad_parcelles_raw.split("|")
                        if idu.strip()
                    ]
                    for idu in idu_list:
                        parcel_exists = Parcelle.objects.filter(idu=idu).exists()
                        if parcel_exists:
                            _, created = ParcelleAdresse.objects.get_or_create(
                                parcelle_id=idu,
                                adresse_id=id_ban,
                            )
                            if created:
                                links_count += 1

        self.stdout.write(
            f"  {filepath.name}: {adresses_count} adresses, {links_count} links"
        )
        return adresses_count, links_count

    def _safe_float(self, value):
        try:
            return float(value) if value else None
        except (ValueError, TypeError):
            return None
