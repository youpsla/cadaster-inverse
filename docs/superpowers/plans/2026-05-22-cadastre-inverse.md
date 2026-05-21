# Cadastre Inversé Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web application for reverse cadastre search — users select department, commune, and surface range, and get matching parcels with postal addresses displayed on an OpenStreetMap map.

**Architecture:** Django monolith with PostGIS, HTMX for interactivity, Leaflet.js for map rendering. Two Docker services (db + web). Data imported via management commands from public open data files.

**Tech Stack:** Django 5.x, Python 3.12, PostgreSQL 16/PostGIS 3.5, Docker, uv, HTMX 2.x, Leaflet 1.9.x

**Spec:** `docs/superpowers/specs/2026-05-22-cadastre-inverse-design.md`

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `manage.py`
- Create: `config/__init__.py`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`
- Create: `cadastre/__init__.py`, `cadastre/apps.py`

- [ ] **Step 1: Initialize uv project and install Django**

```bash
uv init --app cadaster_inversé
cd cadaster_inversé
uv add django psycopg[binary] gunicorn django-htmx whitenoise
```

Expected: `pyproject.toml` created with dependencies listed.

- [ ] **Step 2: Create Django project config**

```bash
uv run django-admin startproject config .
```

Expected: `config/` directory with `settings.py`, `urls.py`, `wsgi.py`, `manage.py` at root.

- [ ] **Step 3: Create cadastre Django app**

```bash
uv run python manage.py startapp cadastre
```

Expected: `cadastre/` directory with `models.py`, `views.py`, `urls.py`, `apps.py`.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock manage.py config/ cadastre/
git commit -m "feat: scaffold Django project with uv"
```

---

### Task 2: Django Settings for PostGIS

**Files:**
- Modify: `config/settings.py`

- [ ] **Step 1: Configure DATABASES for PostGIS**

In `config/settings.py`, replace the default DATABASES with:

```python
import os

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("POSTGRES_DB", "cadastre"),
        "USER": os.environ.get("POSTGRES_USER", "cadastre"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "cadastre"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}
```

- [ ] **Step 2: Add required apps to INSTALLED_APPS**

Append to `INSTALLED_APPS`:

```python
INSTALLED_APPS += [
    "django.contrib.gis",
    "django_htmx",
    "cadastre",
]
```

- [ ] **Step 3: Configure templates and static files**

```python
TEMPLATES[0]["DIRS"] = []
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
```

- [ ] **Step 4: Commit**

```bash
git add config/settings.py
git commit -m "feat: configure Django for PostGIS, add cadastre and django_htmx apps"
```

---

### Task 3: Data Models

**Files:**
- Create: `cadastre/models.py` (full rewrite)
- Create: `cadastre/migrations/` (generated)

- [ ] **Step 1: Write models**

Write `cadastre/models.py`:

```python
from django.contrib.gis.db import models


class Departement(models.Model):
    code = models.CharField(max_length=3, primary_key=True)
    nom = models.CharField(max_length=100)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.nom}"


class Commune(models.Model):
    code_insee = models.CharField(max_length=5, primary_key=True)
    nom = models.CharField(max_length=200)
    code_postal = models.CharField(max_length=5)
    departement = models.ForeignKey(
        Departement, on_delete=models.CASCADE, related_name="communes"
    )

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return f"{self.nom} ({self.code_insee})"


class Parcelle(models.Model):
    idu = models.CharField(max_length=14, primary_key=True)
    geometry = models.PolygonField(spatial_index=True)
    contenance = models.IntegerField(db_index=True)
    prefixe = models.CharField(max_length=3)
    section = models.CharField(max_length=2)
    numero = models.CharField(max_length=4)
    arpente = models.BooleanField(default=False)
    commune = models.ForeignKey(
        Commune, on_delete=models.CASCADE, related_name="parcelles"
    )
    created = models.DateField(null=True, blank=True)
    updated = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["commune", "contenance"]),
        ]

    def __str__(self):
        return self.idu


class Adresse(models.Model):
    id_ban = models.CharField(max_length=50, primary_key=True)
    numero = models.CharField(max_length=10, blank=True, default="")
    rep = models.CharField(max_length=10, blank=True, default="")
    nom_voie = models.CharField(max_length=300, blank=True, default="")
    code_postal = models.CharField(max_length=5, blank=True, default="")
    code_insee = models.CharField(max_length=5, blank=True, default="")
    nom_commune = models.CharField(max_length=200, blank=True, default="")
    lon = models.FloatField(null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    cad_parcelles = models.TextField(blank=True, default="")

    def __str__(self):
        parts = [self.numero, self.nom_voie, self.code_postal, self.nom_commune]
        return " ".join(p for p in parts if p)


class ParcelleAdresse(models.Model):
    parcelle = models.ForeignKey(
        Parcelle, on_delete=models.CASCADE, related_name="adresses_rel"
    )
    adresse = models.ForeignKey(
        Adresse, on_delete=models.CASCADE, related_name="parcelles_rel"
    )

    class Meta:
        unique_together = ["parcelle", "adresse"]

    def __str__(self):
        return f"{self.parcelle_id} <-> {self.adresse_id}"
```

- [ ] **Step 2: Generate and run migrations**

```bash
uv run python manage.py makemigrations cadastre
uv run python manage.py migrate
```

Expected: Migrations created and applied successfully.

- [ ] **Step 3: Commit**

```bash
git add cadastre/models.py cadastre/migrations/
git commit -m "feat: add Departement, Commune, Parcelle, Adresse, ParcelleAdresse models"
```

---

### Task 4: Import Command — Parcelles

**Files:**
- Create: `cadastre/management/__init__.py`
- Create: `cadastre/management/commands/__init__.py`
- Create: `cadastre/management/commands/import_parcelles.py`

- [ ] **Step 1: Write the import command**

Write `cadastre/management/commands/import_parcelles.py`:

```python
import gzip
import json
from pathlib import Path

from django.core.management.base import BaseCommand
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

        self.stdout.write(
            f"Done. Created: {total_created}, Updated: {total_updated}"
        )

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

            geometry = json.dumps(feature["geometry"])

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
```

- [ ] **Step 2: Commit**

```bash
git add cadastre/management/
git commit -m "feat: add import_parcelles management command"
```

---

### Task 5: Import Command — Adresses BAN

**Files:**
- Create: `cadastre/management/commands/import_adresses_ban.py`

- [ ] **Step 1: Write the import command**

Write `cadastre/management/commands/import_adresses_ban.py`:

```python
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

        self.stdout.write(f"  {filepath.name}: {adresses_count} adresses, {links_count} links")
        return adresses_count, links_count

    def _safe_float(self, value):
        try:
            return float(value) if value else None
        except (ValueError, TypeError):
            return None
```

- [ ] **Step 2: Commit**

```bash
git add cadastre/management/commands/import_adresses_ban.py
git commit -m "feat: add import_adresses_ban management command"
```

---

### Task 6: URL Configuration

**Files:**
- Modify: `config/urls.py`
- Create: `cadastre/urls.py`

- [ ] **Step 1: Configure main URL conf**

Replace `config/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("cadastre.urls")),
]
```

- [ ] **Step 2: Create cadastre URL conf**

Write `cadastre/urls.py`:

```python
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("communes/", views.communes, name="communes"),
    path("search/", views.search, name="search"),
]
```

- [ ] **Step 3: Commit**

```bash
git add config/urls.py cadastre/urls.py
git commit -m "feat: add URL routing for index, communes, search endpoints"
```

---

### Task 7: Views

**Files:**
- Create: `cadastre/views.py`

- [ ] **Step 1: Write views**

Write `cadastre/views.py`:

```python
import json

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.db.models.functions import AsGeoJSON

from .models import Commune, Departement, Parcelle, ParcelleAdresse, Adresse


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
    surface_min = request.GET.get("surface_min", "")
    surface_max = request.GET.get("surface_max", "")

    if not commune_code or not surface_min or not surface_max:
        return render(
            request,
            "cadastre/partials/results.html",
            {"results": [], "error": "Veuillez remplir tous les champs."},
        )

    try:
        surface_min = int(surface_min)
        surface_max = int(surface_max)
    except (ValueError, TypeError):
        return render(
            request,
            "cadastre/partials/results.html",
            {"results": [], "error": "Surfaces invalides."},
        )

    parcelles = Parcelle.objects.filter(
        commune_id=commune_code,
        contenance__gte=surface_min,
        contenance__lte=surface_max,
    ).select_related("commune__departement")

    results = []
    geojson_features = []

    for parcelle in parcelles:
        adresses = Adresse.objects.filter(
            parcelles_rel__parcelle_id=parcelle.idu
        )
        adresses_list = [
            f"{a.numero} {a.rep} {a.nom_voie}".strip().replace("  ", " ")
            + f", {a.code_postal} {a.nom_commune}"
            for a in adresses
        ]
        adresse_str = adresses_list[0] if adresses_list else "Adresse inconnue"

        results.append({
            "idu": parcelle.idu,
            "section": parcelle.section,
            "numero": parcelle.numero,
            "contenance": parcelle.contenance,
            "adresse": adresse_str,
            "commune": parcelle.commune.nom,
        })

        geometry = GEOSGeometry(parcelle.geometry)
        centroid = geometry.centroid if geometry else None

        geojson_features.append({
            "type": "Feature",
            "properties": {
                "idu": parcelle.idu,
                "adresse": adresse_str,
                "contenance": parcelle.contenance,
            },
            "geometry": json.loads(geometry.geojson),
        })

    geojson = json.dumps({
        "type": "FeatureCollection",
        "features": geojson_features,
    })

    response = render(
        request,
        "cadastre/partials/results.html",
        {
            "results": results,
            "commune": commune_code,
            "surface_min": surface_min,
            "surface_max": surface_max,
            "geojson": geojson,
        },
    )

    response["HX-Trigger"] = json.dumps({
        "mapUpdate": {"geojson": geojson}
    })

    return response
```

- [ ] **Step 2: Commit**

```bash
git add cadastre/views.py
git commit -m "feat: add index, communes cascade, and search views"
```

---

### Task 8: Templates — Base Layout

**Files:**
- Create: `cadastre/templates/cadastre/base.html`

- [ ] **Step 1: Write base template**

Write `cadastre/templates/cadastre/base.html`:

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cadastre Inversé</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
  {% load static %}
  <script src="{% static 'app.js' %}" defer></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { height: 100%; font-family: system-ui, sans-serif; }
    #layout { display: flex; height: 100vh; }
    #sidebar {
      width: 330px; min-width: 330px;
      overflow-y: auto; padding: 16px;
      border-right: 1px solid #ddd; background: #fafafa;
    }
    #map { flex: 1; height: 100vh; }
    .form-group { margin-bottom: 12px; }
    label { display: block; font-weight: 600; margin-bottom: 4px; font-size: 13px; color: #555; }
    select, input { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
    button { width: 100%; padding: 10px; background: #2563eb; color: #fff; border: none; border-radius: 4px; font-size: 15px; cursor: pointer; }
    button:hover { background: #1d4ed8; }
    h1 { font-size: 18px; margin-bottom: 16px; }
    #results { margin-top: 16px; }
    .result-item {
      padding: 10px 12px; margin-bottom: 8px;
      border: 1px solid #e5e7eb; border-radius: 6px;
      background: #fff; font-size: 13px; line-height: 1.5;
    }
    .result-item strong { font-size: 14px; }
    .result-meta { color: #6b7280; font-size: 12px; }
    .error { color: #dc2626; font-size: 14px; }
    .count { color: #6b7280; font-size: 13px; margin-bottom: 8px; }
  </style>
</head>
<body>
  <div id="layout">
    <div id="sidebar">
      <h1>Cadastre Inversé</h1>
      <form id="search-form"
            hx-get="{% url 'search' %}"
            hx-target="#results"
            hx-trigger="submit">
        <div class="form-group">
          <label for="departement">Département</label>
          <select id="departement" name="departement"
                  hx-get="{% url 'communes' %}"
                  hx-target="#commune-container"
                  hx-trigger="change">
            <option value="">-- Choisir --</option>
            {% for dep in departements %}
              <option value="{{ dep.code }}">{{ dep.nom }} ({{ dep.code }})</option>
            {% endfor %}
          </select>
        </div>
        <div class="form-group">
          <label for="commune">Commune</label>
          <div id="commune-container">
            <select id="commune" name="commune">
              <option value="">-- Sélectionnez un département --</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label for="surface_min">Surface min (m²)</label>
          <input type="number" id="surface_min" name="surface_min" min="0" placeholder="ex: 500" required>
        </div>
        <div class="form-group">
          <label for="surface_max">Surface max (m²)</label>
          <input type="number" id="surface_max" name="surface_max" min="0" placeholder="ex: 2000" required>
        </div>
        <button type="submit">Rechercher</button>
      </form>
      <div id="results"></div>
    </div>
    <div id="map"></div>
  </div>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
mkdir -p cadastre/templates/cadastre
git add cadastre/templates/cadastre/base.html
git commit -m "feat: add base template with sidebar form and Leaflet map container"
```

---

### Task 9: Templates — HTMX Partials

**Files:**
- Create: `cadastre/templates/cadastre/partials/communes.html`
- Create: `cadastre/templates/cadastre/partials/results.html`

- [ ] **Step 1: Write communes partial**

Write `cadastre/templates/cadastre/partials/communes.html`:

```html
<select id="commune" name="commune">
  <option value="">-- Choisir une commune --</option>
  {% for commune in communes %}
    <option value="{{ commune.code_insee }}">{{ commune.nom }}</option>
  {% endfor %}
</select>
```

- [ ] **Step 2: Write results partial**

Write `cadastre/templates/cadastre/partials/results.html`:

```html
{% if error %}
  <div class="error">{{ error }}</div>
{% else %}
  <div class="count">{{ results|length }} résultat(s) pour la commune {{ commune }} ({{ surface_min }}–{{ surface_max }} m²)</div>
  {% for r in results %}
    <div class="result-item">
      <strong>{{ r.adresse }}</strong><br>
      <span class="result-meta">
        Section {{ r.section }} n°{{ r.numero }} — {{ r.contenance }} m² — IDU {{ r.idu }}
      </span>
    </div>
  {% empty %}
    <div>Aucune parcelle trouvée.</div>
  {% endfor %}
{% endif %}
{% if geojson %}
<script id="parcels-data" type="application/json">{{ geojson|safe }}</script>
{% endif %}
```

- [ ] **Step 3: Commit**

```bash
mkdir -p cadastre/templates/cadastre/partials
git add cadastre/templates/cadastre/partials/
git commit -m "feat: add HTMX partials for communes dropdown and search results"
```

---

### Task 10: JavaScript Bridge (HTMX ↔ Leaflet)

**Files:**
- Create: `static/app.js`

- [ ] **Step 1: Write the JS bridge**

Write `static/app.js`:

```javascript
(function () {
  var map = L.map("map").setView([46.2, 5.2], 10);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(map);

  var geoLayer = null;

  function updateMap(geojson) {
    if (geoLayer) {
      map.removeLayer(geoLayer);
    }
    var data = typeof geojson === "string" ? JSON.parse(geojson) : geojson;
    geoLayer = L.geoJSON(data, {
      style: { color: "#2563eb", weight: 2, fillOpacity: 0.15 },
      onEachFeature: function (feature, layer) {
        var p = feature.properties;
        layer.bindPopup(
          "<b>" + (p.adresse || "Adresse inconnue") + "</b><br>" +
          "Surface: " + p.contenance + " m²<br>" +
          "IDU: " + p.idu
        );
      },
    }).addTo(map);
    if (data.features && data.features.length > 0) {
      map.fitBounds(geoLayer.getBounds(), { padding: [30, 30] });
    }
  }

  document.body.addEventListener("htmx:afterSwap", function (evt) {
    if (evt.detail.target.id === "results") {
      var script = document.getElementById("parcels-data");
      if (script) {
        updateMap(script.textContent);
      }
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    var existing = document.getElementById("parcels-data");
    if (existing) {
      updateMap(existing.textContent);
    }
  });
})();
```

- [ ] **Step 2: Commit**

```bash
mkdir -p static
git add static/app.js
git commit -m "feat: add Leaflet map with HTMX bridge to display search results"
```

---

### Task 11: Docker Configuration

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1: Write Dockerfile**

Write `Dockerfile`:

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    gdal-bin libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

COPY . .

RUN uv run python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["uv", "run", "gunicorn", "config.wsgi", "-b", "0.0.0.0:8000"]
```

- [ ] **Step 2: Write docker-compose.yml**

Write `docker-compose.yml`:

```yaml
services:
  db:
    image: postgis/postgis:16-3.5
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: cadastre
      POSTGRES_USER: cadastre
      POSTGRES_PASSWORD: cadastre
    ports:
      - "5432:5432"

  web:
    build: .
    command: uv run gunicorn config.wsgi -b 0.0.0.0:8000
    volumes:
      - ./data:/data
    ports:
      - "8000:8000"
    depends_on:
      - db
    env_file:
      - .env

volumes:
  pgdata:
```

- [ ] **Step 3: Write .env.example**

Write `.env.example`:

```
DEBUG=true
SECRET_KEY=change-me-in-production
POSTGRES_DB=cadastre
POSTGRES_USER=cadastre
POSTGRES_PASSWORD=cadastre
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

- [ ] **Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml .env.example
git commit -m "feat: add Docker configuration with PostGIS and Django services"
```

---

### Task 12: Verify with Docker

- [ ] **Step 1: Build and start services**

```bash
cp .env.example .env
docker compose up -d --build
```

Expected: Both services start. `docker compose ps` shows `db` and `web` as healthy.

- [ ] **Step 2: Run migrations inside container**

```bash
docker compose exec web uv run python manage.py migrate
```

Expected: All migrations applied.

- [ ] **Step 3: Verify app responds**

Open `http://localhost:8000` in browser. Expected: page loads with sidebar form and empty map.

- [ ] **Step 4: Test import with sample data**

Copy the sample file into the data volume:
```bash
cp cadastre-01001-parcelles.json data/parcelles/
gzip data/parcelles/cadastre-01001-parcelles.json
docker compose exec web uv run python manage.py import_parcelles
```

Expected: Parcels and commune created. Verify:
```bash
docker compose exec web uv run python manage.py shell -c "from cadastre.models import Parcelle; print(Parcelle.objects.count())"
```

Should output a count > 0.

- [ ] **Step 5: Commit (if any changes)**

```bash
git add .env  # if created
git commit -m "chore: add .env and verify Docker setup"
```
