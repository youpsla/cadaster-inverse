import json

from django.db.models import Sum
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.cache import cache_page
from django.contrib.gis.geos import GEOSGeometry

from .models import Adresse, Commune, Departement, Parcelle


def _get_departement_by_slug(slug):
    for dep in Departement.objects.all():
        if slugify(dep.nom) == slug:
            return dep
    return None


def _get_commune_by_slug(dep, slug):
    for com in Commune.objects.filter(departement=dep):
        if slugify(com.nom) == slug:
            return com
    return None


def _meta(title, description, og_title=None, url=None):
    return {
        "title": title,
        "description": description,
        "og_title": og_title or title,
        "og_type": "website",
        "og_locale": "fr_FR",
        "og_site_name": "Cadastre Inversé",
        "og_url": url or "",
        "twitter_card": "summary_large_image",
    }


@cache_page(60 * 60)
def landing(request):
    departements = Departement.objects.all()
    nb_parcelles = Departement.objects.aggregate(total=Sum("nb_parcelles_adresse"))["total"] or 0
    nb_communes = Commune.objects.count()
    context = {
        "departements": departements,
        "nb_parcelles": nb_parcelles,
        "nb_communes": nb_communes,
        "meta": _meta(
            title="Cadastre Inversé — Trouvez un bien par la surface de sa parcelle",
            description=(
                f"Recherchez une parcelle cadastrale par sa surface. "
                f"{nb_parcelles:,} parcelles avec adresses référencées "
                f"dans {nb_communes:,} communes."
            ),
            url=request.build_absolute_uri(),
        ),
    }
    return render(request, "cadastre/landing.html", context)


@cache_page(60 * 60)
def departement(request, dep_slug):
    dep = _get_departement_by_slug(dep_slug)
    if dep is None:
        raise Http404
    communes = Commune.objects.filter(departement=dep)
    nb_parcelles = dep.nb_parcelles_adresse
    context = {
        "departement": dep,
        "communes": communes,
        "nb_parcelles": nb_parcelles,
        "meta": _meta(
            title=f"Recherche de parcelles par surface du département {dep.nom}",
            description=(
                f"Recherchez une parcelle cadastrale par sa surface "
                f"dans le département {dep.nom} ({dep.code}). "
                f"{nb_parcelles:,} parcelles avec adresses "
                f"dans {communes.count()} communes."
            ),
            url=request.build_absolute_uri(),
        ),
        "breadcrumbs": [
            {"name": "Accueil", "url": request.build_absolute_uri(reverse("landing"))},
            {"name": dep.nom, "url": request.build_absolute_uri()},
        ],
        "selected_dep": dep.code,
        "selected_dep_communes": communes,
        "departements": Departement.objects.all(),
    }
    return render(request, "cadastre/departement.html", context)


@cache_page(60 * 60)
def commune(request, dep_slug, commune_slug):
    dep = _get_departement_by_slug(dep_slug)
    if dep is None:
        raise Http404
    com = _get_commune_by_slug(dep, commune_slug)
    if com is None:
        raise Http404
    communes = Commune.objects.filter(departement=dep)
    nb_parcelles = Parcelle.objects.filter(commune=com, has_address=True).count()
    context = {
        "commune": com,
        "departement": dep,
        "nb_parcelles": nb_parcelles,
        "meta": _meta(
            title=f"Recherche de parcelles par surface à {com.nom} ({com.code_postal})",
            description=(
                f"Recherchez une parcelle cadastrale par sa surface "
                f"à {com.nom} ({com.code_postal}). "
                f"{nb_parcelles:,} parcelles avec adresses référencées."
            ),
            url=request.build_absolute_uri(),
        ),
        "breadcrumbs": [
            {"name": "Accueil", "url": request.build_absolute_uri(reverse("landing"))},
            {
                "name": dep.nom,
                "url": request.build_absolute_uri(
                    reverse("departement", kwargs={"dep_slug": dep_slug})
                ),
            },
            {"name": com.nom, "url": request.build_absolute_uri()},
        ],
        "selected_dep": dep.code,
        "selected_dep_communes": communes,
        "selected_com": com.code_insee,
        "departements": Departement.objects.all(),
    }
    return render(request, "cadastre/commune.html", context)


def communes(request):
    dep_code = request.GET.get("departement", "")
    communes_qs = Commune.objects.filter(departement_id=dep_code).order_by("nom")
    return render(
        request,
        "cadastre/partials/communes.html",
        {"communes": communes_qs},
    )


def search(request):
    commune_code = request.GET.get("commune", "")
    surface_mode = request.GET.get("surface_mode", "exact")

    if not commune_code:
        return render(
            request,
            "cadastre/partials/results.html",
            {"results": [], "error": "Veuillez remplir tous les champs."},
        )

    filter_kwargs = {"commune_id": commune_code, "has_address": True}
    surface_label = ""

    if surface_mode == "range":
        surface_min = request.GET.get("surface_min", "")
        surface_max = request.GET.get("surface_max", "")
        if not surface_min or not surface_max:
            return render(
                request,
                "cadastre/partials/results.html",
                {"results": [], "error": "Veuillez saisir les surfaces min et max."},
            )
        try:
            filter_kwargs["contenance__gte"] = int(surface_min)
            filter_kwargs["contenance__lte"] = int(surface_max)
        except (ValueError, TypeError):
            return render(
                request,
                "cadastre/partials/results.html",
                {"results": [], "error": "Surfaces invalides."},
            )
        surface_label = f"{surface_min}–{surface_max}"
    else:
        surface = request.GET.get("surface", "")
        if not surface:
            return render(
                request,
                "cadastre/partials/results.html",
                {"results": [], "error": "Veuillez saisir une surface."},
            )
        try:
            filter_kwargs["contenance"] = int(surface)
        except (ValueError, TypeError):
            return render(
                request,
                "cadastre/partials/results.html",
                {"results": [], "error": "Surface invalide."},
            )
        surface_label = f"{surface}"

    commune_name = Commune.objects.filter(code_insee=commune_code).values_list("nom", flat=True).first() or commune_code

    parcelles = Parcelle.objects.filter(**filter_kwargs).select_related("commune__departement")

    results = []
    geojson_features = []

    for parcelle in parcelles:
        adresses = Adresse.objects.filter(parcelles_rel__parcelle_id=parcelle.idu)
        adresses_list = [
            f"{a.numero} {a.nom_voie}".strip()
            + f", {a.code_postal} {a.nom_commune}"
            for a in adresses
        ]
        adresse_str = adresses_list[0] if adresses_list else "Adresse inconnue"

        results.append(
            {
                "idu": parcelle.idu,
                "section": parcelle.section,
                "numero": parcelle.numero,
                "contenance": parcelle.contenance,
                "adresse": adresse_str,
                "commune": parcelle.commune.nom,
            }
        )

        geometry = GEOSGeometry(parcelle.geometry.wkt if hasattr(parcelle.geometry, 'wkt') else parcelle.geometry)

        geojson_features.append(
            {
                "type": "Feature",
                "properties": {
                    "idu": parcelle.idu,
                    "adresse": adresse_str,
                    "contenance": parcelle.contenance,
                },
                "geometry": json.loads(geometry.geojson),
            }
        )

    geojson = json.dumps(
        {
            "type": "FeatureCollection",
            "features": geojson_features,
        }
    )

    response = render(
        request,
        "cadastre/partials/results.html",
        {
            "results": results,
            "commune": commune_name,
            "surface_label": surface_label,
            "geojson": geojson,
        },
    )

    return response
