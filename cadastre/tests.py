from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.gis.geos import Polygon

from .models import Departement, Commune, Parcelle, Adresse, ParcelleAdresse


def _make_polygon():
    return Polygon(((0, 0), (0, 0.01), (0.01, 0.01), (0.01, 0), (0, 0)))


class TestModels(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dep = Departement.objects.create(code="01", nom="Ain")
        cls.com = Commune.objects.create(
            code_insee="01001",
            nom="Bourg-en-Bresse",
            code_postal="01000",
            departement=cls.dep,
        )
        cls.par = Parcelle.objects.create(
            idu="010010000A0001",
            geometry=_make_polygon(),
            contenance=1000,
            section="A",
            numero="0001",
            has_address=True,
            commune=cls.com,
        )
        cls.adr = Adresse.objects.create(
            id_ban="01001_0001_00001",
            numero="1",
            nom_voie="Rue de la Paix",
            code_postal="01000",
            code_insee="01001",
            nom_commune="Bourg-en-Bresse",
        )
        cls.lien = ParcelleAdresse.objects.create(
            parcelle=cls.par, adresse=cls.adr
        )

    def test_departement_str(self):
        self.assertEqual(str(self.dep), "01 - Ain")

    def test_commune_str(self):
        self.assertEqual(str(self.com), "Bourg-en-Bresse (01001)")

    def test_parcelle_str(self):
        self.assertEqual(str(self.par), "010010000A0001")

    def test_adresse_str(self):
        self.assertEqual(
            str(self.adr), "1 Rue de la Paix 01000 Bourg-en-Bresse"
        )

    def test_parcelleadresse_str(self):
        self.assertEqual(
            str(self.lien),
            "010010000A0001 <-> 01001_0001_00001",
        )


class TestLandingView(TestCase):
    @classmethod
    def setUpTestData(cls):
        Departement.objects.create(code="01", nom="Ain")

    def setUp(self):
        self.client = Client()

    def test_returns_200(self):
        response = self.client.get(reverse("landing"))
        self.assertEqual(response.status_code, 200)

    def test_uses_correct_template(self):
        response = self.client.get(reverse("landing"))
        self.assertTemplateUsed(response, "cadastre/landing.html")

    def test_departements_in_context(self):
        response = self.client.get(reverse("landing"))
        self.assertIn("departements", response.context)
        self.assertEqual(len(response.context["departements"]), 1)

    def test_has_meta(self):
        response = self.client.get(reverse("landing"))
        self.assertIn("meta", response.context)
        self.assertIsNotNone(response.context["meta"])
        self.assertIn("Cadastre Inversé", response.context["meta"]["title"])

    def test_has_parcelle_count(self):
        response = self.client.get(reverse("landing"))
        self.assertIn("nb_parcelles", response.context)
        self.assertEqual(response.context["nb_parcelles"], 0)


class TestLandingSEO(TestCase):
    @classmethod
    def setUpTestData(cls):
        Departement.objects.create(code="01", nom="Ain")
        Departement.objects.create(code="78", nom="Yvelines")

    def setUp(self):
        self.client = Client()

    def test_links_to_departements(self):
        response = self.client.get(reverse("landing"))
        self.assertContains(response, 'href="/departement/ain/"')
        self.assertContains(response, 'href="/departement/yvelines/"')

    def test_departement_links_are_get(self):
        for dep_slug in ["ain", "yvelines"]:
            url = reverse("departement", kwargs={"dep_slug": dep_slug})
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200)


class TestDepartementView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dep = Departement.objects.create(code="01", nom="Ain")
        Commune.objects.create(
            code_insee="01001",
            nom="Bourg-en-Bresse",
            code_postal="01000",
            departement=cls.dep,
        )
        Commune.objects.create(
            code_insee="01002",
            nom="Ambérieu-en-Bugey",
            code_postal="01500",
            departement=cls.dep,
        )

    def setUp(self):
        self.client = Client()

    def test_returns_200(self):
        url = reverse("departement", kwargs={"dep_slug": "ain"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_uses_correct_template(self):
        url = reverse("departement", kwargs={"dep_slug": "ain"})
        response = self.client.get(url)
        self.assertTemplateUsed(response, "cadastre/departement.html")

    def test_communes_in_context(self):
        url = reverse("departement", kwargs={"dep_slug": "ain"})
        response = self.client.get(url)
        self.assertEqual(len(response.context["communes"]), 2)

    def test_404_for_invalid_dep_slug(self):
        url = reverse("departement", kwargs={"dep_slug": "inexistant"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_has_meta(self):
        url = reverse("departement", kwargs={"dep_slug": "ain"})
        response = self.client.get(url)
        self.assertIn("meta", response.context)
        self.assertIn("Ain", response.context["meta"]["title"])

    def test_has_breadcrumbs(self):
        url = reverse("departement", kwargs={"dep_slug": "ain"})
        response = self.client.get(url)
        self.assertIn("breadcrumbs", response.context)
        self.assertEqual(len(response.context["breadcrumbs"]), 2)

    def test_selected_dep_in_context(self):
        url = reverse("departement", kwargs={"dep_slug": "ain"})
        response = self.client.get(url)
        self.assertEqual(response.context["selected_dep"], "01")

    def test_links_to_communes(self):
        url = reverse("departement", kwargs={"dep_slug": "ain"})
        response = self.client.get(url)
        self.assertContains(response, "/departement/ain/bourg-en-bresse/")
        self.assertContains(response, "/departement/ain/amberieu-en-bugey/")


class TestCommuneView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dep = Departement.objects.create(code="01", nom="Ain")
        cls.com = Commune.objects.create(
            code_insee="01001",
            nom="Bourg-en-Bresse",
            code_postal="01000",
            departement=cls.dep,
        )
        Parcelle.objects.create(
            idu="010010000A0001",
            geometry=_make_polygon(),
            contenance=1000,
            section="A",
            numero="0001",
            has_address=True,
            commune=cls.com,
        )

    def setUp(self):
        self.client = Client()

    def test_returns_200(self):
        url = reverse(
            "commune",
            kwargs={"dep_slug": "ain", "commune_slug": "bourg-en-bresse"},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_uses_correct_template(self):
        url = reverse(
            "commune",
            kwargs={"dep_slug": "ain", "commune_slug": "bourg-en-bresse"},
        )
        response = self.client.get(url)
        self.assertTemplateUsed(response, "cadastre/commune.html")

    def test_404_for_invalid_commune_slug(self):
        url = reverse(
            "commune",
            kwargs={"dep_slug": "ain", "commune_slug": "inexistant"},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_404_for_wrong_dep(self):
        url = reverse(
            "commune",
            kwargs={"dep_slug": "yvelines", "commune_slug": "bourg-en-bresse"},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_has_meta(self):
        url = reverse(
            "commune",
            kwargs={"dep_slug": "ain", "commune_slug": "bourg-en-bresse"},
        )
        response = self.client.get(url)
        self.assertIn("meta", response.context)
        self.assertIn("Bourg-en-Bresse", response.context["meta"]["title"])

    def test_has_breadcrumbs(self):
        url = reverse(
            "commune",
            kwargs={"dep_slug": "ain", "commune_slug": "bourg-en-bresse"},
        )
        response = self.client.get(url)
        self.assertIn("breadcrumbs", response.context)
        self.assertEqual(len(response.context["breadcrumbs"]), 3)

    def test_selected_com_in_context(self):
        url = reverse(
            "commune",
            kwargs={"dep_slug": "ain", "commune_slug": "bourg-en-bresse"},
        )
        response = self.client.get(url)
        self.assertEqual(response.context["selected_com"], "01001")

    def test_nb_parcelles_in_context(self):
        url = reverse(
            "commune",
            kwargs={"dep_slug": "ain", "commune_slug": "bourg-en-bresse"},
        )
        response = self.client.get(url)
        self.assertEqual(response.context["nb_parcelles"], 1)

    def test_has_search_form(self):
        url = reverse(
            "commune",
            kwargs={"dep_slug": "ain", "commune_slug": "bourg-en-bresse"},
        )
        response = self.client.get(url)
        self.assertContains(response, 'name="departement"')
        self.assertContains(response, 'name="commune"')
        self.assertContains(response, 'name="surface"')


class TestSitemap(TestCase):
    @classmethod
    def setUpTestData(cls):
        dep = Departement.objects.create(code="01", nom="Ain")
        Commune.objects.create(
            code_insee="01001",
            nom="Bourg-en-Bresse",
            code_postal="01000",
            departement=dep,
        )
        Commune.objects.create(
            code_insee="01002",
            nom="Ambérieu-en-Bugey",
            code_postal="01500",
            departement=dep,
        )

    def setUp(self):
        self.client = Client()

    def test_sitemap_index(self):
        response = self.client.get(reverse("sitemap-index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "sitemap-departements")
        self.assertContains(response, "sitemap-communes")

    def test_departement_sitemap(self):
        response = self.client.get(
            reverse("django.contrib.sitemaps.views.sitemap", kwargs={"section": "departements"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "departement/ain/")

    def test_commune_sitemap(self):
        response = self.client.get(
            reverse("django.contrib.sitemaps.views.sitemap", kwargs={"section": "communes"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "departement/ain/bourg-en-bresse/")
        self.assertContains(response, "departement/ain/amberieu-en-bugey/")


class TestRobotsTxt(TestCase):
    def setUp(self):
        self.client = Client()

    def test_robots_txt_returns_200(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)

    def test_robots_txt_contains_sitemap(self):
        response = self.client.get("/robots.txt")
        self.assertContains(response, "sitemap")
        self.assertContains(response, "sitemap.xml")


class TestCommunesView(TestCase):
    @classmethod
    def setUpTestData(cls):
        dep = Departement.objects.create(code="01", nom="Ain")
        Commune.objects.create(
            code_insee="01001",
            nom="Bourg-en-Bresse",
            code_postal="01000",
            departement=dep,
        )
        Commune.objects.create(
            code_insee="01002",
            nom="Ambérieu-en-Bugey",
            code_postal="01500",
            departement=dep,
        )
        dep78 = Departement.objects.create(code="78", nom="Yvelines")
        Commune.objects.create(
            code_insee="78350",
            nom="Jouy-en-Josas",
            code_postal="78350",
            departement=dep78,
        )

    def setUp(self):
        self.client = Client()

    def test_returns_200(self):
        response = self.client.get(reverse("communes"), {"departement": "01"})
        self.assertEqual(response.status_code, 200)

    def test_uses_partial_template(self):
        response = self.client.get(reverse("communes"), {"departement": "01"})
        self.assertTemplateUsed(response, "cadastre/partials/communes.html")

    def test_filters_by_departement(self):
        response = self.client.get(reverse("communes"), {"departement": "01"})
        communes = response.context["communes"]
        self.assertEqual(len(communes), 2)
        for c in communes:
            self.assertEqual(c.departement_id, "01")

    def test_empty_dep_returns_no_communes(self):
        response = self.client.get(reverse("communes"), {"departement": ""})
        communes = response.context["communes"]
        self.assertEqual(len(communes), 0)


class TestSearchView(TestCase):
    @classmethod
    def setUpTestData(cls):
        dep = Departement.objects.create(code="01", nom="Ain")
        com = Commune.objects.create(
            code_insee="01001",
            nom="Bourg-en-Bresse",
            code_postal="01000",
            departement=dep,
        )
        cls.p1 = Parcelle.objects.create(
            idu="010010000A0001",
            geometry=_make_polygon(),
            contenance=1000,
            section="A",
            numero="0001",
            has_address=True,
            commune=com,
        )
        Parcelle.objects.create(
            idu="010010000A0002",
            geometry=_make_polygon(),
            contenance=2000,
            section="A",
            numero="0002",
            has_address=True,
            commune=com,
        )
        Parcelle.objects.create(
            idu="010010000A0003",
            geometry=_make_polygon(),
            contenance=1500,
            section="B",
            numero="0001",
            has_address=False,
            commune=com,
        )
        cls.adr = Adresse.objects.create(
            id_ban="01001_0001_00001",
            numero="1",
            nom_voie="Rue de la Paix",
            code_postal="01000",
            code_insee="01001",
            nom_commune="Bourg-en-Bresse",
        )
        ParcelleAdresse.objects.create(parcelle=cls.p1, adresse=cls.adr)

    def setUp(self):
        self.client = Client()

    def _search(self, extra):
        params = {"commune": "01001"}
        params.update(extra)
        return self.client.get(reverse("search"), params)

    def test_requires_commune(self):
        response = self.client.get(reverse("search"), {"commune": ""})
        self.assertIn("error", response.context)
        self.assertContains(response, "Veuillez remplir tous les champs")

    def test_exact_surface_finds_parcels(self):
        response = self._search({"surface": "1000", "surface_mode": "exact"})
        results = response.context["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["idu"], "010010000A0001")

    def test_exact_surface_uses_default_mode(self):
        response = self._search({"surface": "1000"})
        results = response.context["results"]
        self.assertEqual(len(results), 1)

    def test_requires_surface_in_exact_mode(self):
        response = self._search({"surface": "", "surface_mode": "exact"})
        self.assertContains(response, "Veuillez saisir une surface")

    def test_requires_surface_min_in_range_mode(self):
        response = self._search({
            "surface_mode": "range",
            "surface_min": "",
            "surface_max": "2000",
        })
        self.assertContains(response, "Veuillez saisir les surfaces min et max")

    def test_requires_surface_max_in_range_mode(self):
        response = self._search({
            "surface_mode": "range",
            "surface_min": "500",
            "surface_max": "",
        })
        self.assertContains(response, "Veuillez saisir les surfaces min et max")

    def test_range_surface_finds_parcels(self):
        response = self._search({
            "surface_mode": "range",
            "surface_min": "500",
            "surface_max": "1500",
        })
        results = response.context["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["idu"], "010010000A0001")

    def test_range_surface_upper_bound_inclusive(self):
        response = self._search({
            "surface_mode": "range",
            "surface_min": "1500",
            "surface_max": "2000",
        })
        results = response.context["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["idu"], "010010000A0002")

    def test_invalid_surface_value(self):
        response = self._search({"surface": "abc", "surface_mode": "exact"})
        self.assertContains(response, "Surface invalide")

    def test_invalid_surface_min_value(self):
        response = self._search({
            "surface_mode": "range",
            "surface_min": "abc",
            "surface_max": "2000",
        })
        self.assertContains(response, "Surfaces invalides")

    def test_filters_has_address_only(self):
        response = self._search({"surface": "1500", "surface_mode": "exact"})
        results = response.context["results"]
        for r in results:
            self.assertNotEqual(r["idu"], "010010000A0003")

    def test_no_results_shows_empty_message(self):
        response = self._search({"surface": "99999", "surface_mode": "exact"})
        self.assertContains(response, "Aucune parcelle trouvée")

    def test_commune_name_in_context(self):
        response = self._search({"surface": "1000", "surface_mode": "exact"})
        self.assertEqual(response.context["commune"], "Bourg-en-Bresse")

    def test_surface_label_in_context(self):
        response = self._search({"surface": "1000", "surface_mode": "exact"})
        self.assertEqual(response.context["surface_label"], "1000")

    def test_surface_label_range_in_context(self):
        response = self._search({
            "surface_mode": "range",
            "surface_min": "500",
            "surface_max": "1500",
        })
        self.assertEqual(response.context["surface_label"], "500–1500")

    def test_geojson_in_context(self):
        response = self._search({"surface": "1000", "surface_mode": "exact"})
        self.assertIn("geojson", response.context)
        self.assertIn("FeatureCollection", response.context["geojson"])

    def test_geojson_script_in_response(self):
        response = self._search({"surface": "1000", "surface_mode": "exact"})
        self.assertContains(response, 'id="parcels-data"')

    def test_uses_partial_template(self):
        response = self._search({"surface": "1000", "surface_mode": "exact"})
        self.assertTemplateUsed(response, "cadastre/partials/results.html")
