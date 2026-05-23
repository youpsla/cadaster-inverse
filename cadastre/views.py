import json

from django.shortcuts import render
from django.contrib.gis.geos import GEOSGeometry

from .models import Adresse, Commune, Departement, Parcelle


def index(request):
    departements = Departement.objects.all()
    context = {
        "departements": departements,
    }
    return render(request, "cadastre/base.html", context)


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
