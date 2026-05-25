from django.core.management.base import BaseCommand
from django.db.models import Count

from cadastre.models import Departement, Parcelle


class Command(BaseCommand):
    help = "Recompute nb_parcelles_adresse on Departement"

    def add_arguments(self, parser):
        parser.add_argument(
            "dep_codes", nargs="*", type=str, help="Department code(s) to recompute"
        )

    def handle(self, *args, **options):
        qs = Departement.objects.all()
        if options["dep_codes"]:
            qs = qs.filter(code__in=options["dep_codes"])

        for dep in qs.iterator():
            count = (
                Parcelle.objects.filter(
                    commune__departement=dep, has_address=True
                ).count()
            )
            dep.nb_parcelles_adresse = count
            dep.save(update_fields=["nb_parcelles_adresse"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"{dep.code} {dep.nom}: {count} parcelles avec adresses"
                )
            )
