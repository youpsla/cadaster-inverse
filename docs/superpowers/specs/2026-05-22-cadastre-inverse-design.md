# Spécification : Cadastre Inversé

**Date :** 2026-05-22
**Version :** 1.0
**Périmètre :** Département pilote 01 (Ain), extensible France entière

---

## 1. Objectif

Application web de **recherche cadastrale inversée** : l'utilisateur sélectionne un département, une commune, et une plage de surface (m²). Le système retourne les parcelles correspondantes avec leur adresse postale, affichées sur un fond de carte OpenStreetMap.

---

## 2. Stack technique

| Composant | Choix |
|-----------|-------|
| Backend | Django 5.x + Python 3.12 |
| Base de données | PostgreSQL 16 + PostGIS 3.5 |
| Gestionnaire de paquets | uv (pyproject.toml) |
| Conteneurisation | Docker (docker-compose, 2 services) |
| Frontend interactif | HTMX 2.x |
| Carte | Leaflet 1.9.x + OpenStreetMap tiles |
| CSS | Minimal, responsive (pas de framework lourd) |
| Serveur WSGI | Gunicorn + Whitenoise (statics) |

---

## 3. Modèle de données

### Tables

**Departement**
- `code` : CharField(2 ou 3) — ex. "01"
- `nom` : CharField — ex. "Ain"

**Commune**
- `code_insee` : CharField(5) PK — ex. "01001"
- `nom` : CharField — ex. "L'Abergement-Clémenciat"
- `code_postal` : CharField(5)
- `departement` : FK → Departement

**Parcelle**
- `idu` : CharField(14) PK — ex. "010010000A0842"
- `geometry` : PolygonField (PostGIS) — index GIST
- `contenance` : IntegerField — surface en m², index B-tree
- `prefixe` : CharField(3), `section` : CharField(2), `numero` : CharField(4)
- `arpente` : BooleanField
- `commune` : FK → Commune
- `created`, `updated` : DateField

**Adresse** (issue de la BAN)
- `id_ban` : CharField PK — clé d'interopérabilité BAL 1.3
- `numero` : CharField, `rep` : CharField (bis, a...)
- `nom_voie` : CharField
- `code_postal` : CharField(5)
- `code_insee` : CharField(5) — commune de rattachement
- `nom_commune` : CharField
- `lon`, `lat` : FloatField — coordonnées WGS-84
- `cad_parcelles` : TextField — liste d'IDU séparés par `|` (brut, import)

**ParcelleAdresse** (table de liaison M2M)
- `parcelle_idu` : FK → Parcelle
- `adresse_id` : FK → Adresse

---

## 4. Sources de données & Import

### Sources publiques

| Source | URL | Format |
|--------|-----|--------|
| Cadastre | `cadastre.data.gouv.fr` → `/geojson/communes/{dep}/{com}/` | `cadastre-{dep}{com}-parcelles.json.gz` (GeoJSON) |
| BAN | `adresse.data.gouv.fr` | `adresses-{dep}.csv` (CSV, séparateur `;`, UTF-8) |

### Lien Parcelle ↔ Adresse

Le champ BAN `cad_parcelles` (expérimental, en cours de fiabilisation) liste les IDU des parcelles rattachées à chaque adresse, séparés par `|`. C'est ce champ qui fait le pont.

### Management commands

**`python manage.py import_parcelles`**
- Parcourt `/data/parcelles/*.json.gz`
- Extrait chaque Feature : `id`, `geometry`, `properties.*`
- Déduit le code commune des 5 premiers caractères de l'IDU
- Upsert sur `Parcelle` (par IDU) et `Commune`
- Lecture streaming (pas de chargement complet en mémoire)

**`python manage.py import_adresses_ban`**
- Lit `/data/adresses/*.csv` (séparateur `;`, UTF-8)
- Crée/met à jour `Adresse` (par `id_ban`)
- Parse `cad_parcelles` (`|`-séparé) → peuple `ParcelleAdresse`

### Mise à jour

Les données sont mises à jour ~1x/an. Processus : télécharger les nouveaux fichiers dans `/data/`, relancer les 2 commands. Upsert = pas de suppression/re-création massive.

---

## 5. API & Flux de recherche

### Endpoints

| URL | Méthode | Rôle | Réponse |
|-----|---------|------|---------|
| `/` | GET | Page principale | Template complet |
| `/communes/?departement=01` | GET | Cascade HTMX | `<option>` HTML partiel |
| `/search/?commune=01001&surface_min=500&surface_max=2000` | GET | Recherche | HTML partiel + GeoJSON |

### Flow

1. L'utilisateur arrive sur `/` → carte plein écran + sidebar avec formulaire
2. Sélection du département → `GET /communes/?departement=01` → le `<select>` commune se remplit via HTMX
3. Saisie surface min/max + soumission → `GET /search/?commune=01001&surface_min=500&surface_max=2000`
4. Réponse serveur :
   - **Corps HTML** : liste des résultats (sidebar) — swap HTMX
   - **Header `HX-Trigger`** : contient le GeoJSON des parcelles trouvées → le JS bridge met à jour la carte Leaflet

### Requête SQL

```sql
SELECT p.*, a.numero, a.rep, a.nom_voie, a.code_postal,
       ST_AsGeoJSON(p.geometry)
FROM cadastre_parcelle p
JOIN cadastre_parcelleadresse pa ON p.idu = pa.parcelle_idu_id
JOIN cadastre_adresse a ON pa.adresse_id = a.id_ban
WHERE p.commune_id = %s
  AND p.contenance BETWEEN %s AND %s
```

---

## 6. Frontend

### Layout

```
┌────────────┬────────────────────────────────────┐
│  Sidebar   │                                    │
│  (30%)     │      Carte Leaflet (70%)            │
│            │      OpenStreetMap tiles            │
│  [form]    │      Polygones parcelles            │
│  [résults] │      Marqueurs adresses             │
└────────────┴────────────────────────────────────┘
```

### Templates Django

- `cadastre/base.html` — layout principal (sidebar + carte), charge Leaflet + HTMX + `app.js`
- `cadastre/partials/communes.html` — `<option>` pour cascade département → commune
- `cadastre/partials/results.html` — liste résultats + `<script type="application/json">` contenant le GeoJSON

### JavaScript (~30 lignes, vanilla)

`static/app.js` — écoute `htmx:afterSwap` sur le conteneur résultats, extrait le GeoJSON, appelle `L.geoJSON(data).addTo(map)`.

### Dépendances CDN

- HTMX 2.x
- Leaflet 1.9.x + CSS
- OpenStreetMap tiles

---

## 7. Structure du projet

```
cadaster_inversé/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── manage.py
├── config/                    # Projet Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── cadastre/                  # App Django
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── management/commands/
│   │   ├── import_parcelles.py
│   │   └── import_adresses_ban.py
│   └── templates/cadastre/
│       ├── base.html
│       └── partials/
│           ├── communes.html
│           └── results.html
├── static/
│   └── app.js
└── data/                      # Volume Docker
    ├── parcelles/
    └── adresses/
```

### Docker Compose

```yaml
services:
  db:
    image: postgis/postgis:16-3.5
    volumes: [pgdata:/var/lib/postgresql/data]
    environment: [POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD]

  web:
    build: .
    command: gunicorn config.wsgi -b 0.0.0.0:8000
    volumes: [./data:/data]
    ports: ["8000:8000"]
    depends_on: [db]
    env_file: .env

volumes:
  pgdata:
```

### Dépendances Python (pyproject.toml)

```
django>=5.0
psycopg[binary]>=3.0
gunicorn
django-htmx
whitenoise
```

---

## 8. Hors périmètre (v1)

- Authentification / comptes utilisateurs
- Upload de fichiers par l'utilisateur
- Export CSV/PDF des résultats
- Recherche multi-communes
- Filtres avancés (arpenté, date de mise à jour...)
- Interface d'administration custom (Django admin suffit pour le debug)
