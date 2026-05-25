from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils.text import slugify

from .models import Commune, Departement


class LandingSitemap(Sitemap):
    changefreq = "weekly"
    priority = 1.0

    def items(self):
        return ["landing"]

    def location(self, item):
        return reverse(item)


class DepartementSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Departement.objects.all()

    def location(self, item):
        return reverse("departement", kwargs={"dep_slug": slugify(item.nom)})


class CommuneSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Commune.objects.select_related("departement").all()

    def location(self, item):
        return reverse(
            "commune",
            kwargs={
                "dep_slug": slugify(item.departement.nom),
                "commune_slug": slugify(item.nom),
            },
        )


sitemaps = {
    "landing": LandingSitemap,
    "departements": DepartementSitemap,
    "communes": CommuneSitemap,
}
