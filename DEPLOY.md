# Déploiement production — Cadastre Inversé

## Prérequis VPS

- Docker et Docker Compose (ou Docker Engine avec plugin compose)
- Git
- Un nom de domaine pointant vers l'IP du VPS (ports 80 et 443)
- **Aucun autre service** à installer sur l'hôte — tout tourne dans Docker

## 1. Récupérer le projet

```bash
git clone https://github.com/youpsla/cadaster-inverse.git
cd cadaster-inverse
```

## 2. Configurer l'environnement

```bash
cp .env.prod.example .env.prod
```

Éditer `.env.prod` :

```
DEBUG=false
SECRET_KEY=<à générer>
ALLOWED_HOSTS=cadastre.votre-domaine.com
CSRF_TRUSTED_ORIGINS=https://cadastre.votre-domaine.com
POSTGRES_DB=cadastre
POSTGRES_USER=cadastre
POSTGRES_PASSWORD=<mot de passe fort>
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

Générer une SECRET_KEY et un mot de passe DB :

```bash
docker compose run --rm web uv run python -c \
  "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 3. Lancer la stack

```bash
DOMAIN=cadastre.votre-domaine.com \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

La première fois, Docker va :
- Télécharger PostGIS 16 et Caddy 2
- Build l'image Django (installation des dépendances, collectstatic)
- Démarrer la base de données
- Lancer les migrations Django
- Démarrer Caddy qui obtiendra automatiquement un certificat Let's Encrypt

## 4. Créer les tables (première fois uniquement)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  exec web uv run python manage.py migrate
```

## 5. Importer les données

```bash
DOMAIN=cadastre.votre-domaine.com \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  exec web bash download_data.sh 01
```

Remplacer `01` par le code du département souhaité.

## 6. Vérifier

```bash
# Logs Caddy
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f caddy

# Logs Django
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web

# Healthcheck
curl -f https://cadastre.votre-domaine.com/
```

## Commandes utiles

### Rebuild après modification du code

```bash
DOMAIN=cadastre.votre-domaine.com \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  up -d --build web
```

### Redémarrer un service

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart web
```

### Voir les logs

```bash
# Temps réel
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# 100 dernières lignes
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100 web
```

### Exécuter une commande Django

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  exec web uv run python manage.py shell
```

### Sauvegarder / restaurer la base

```bash
# Sauvegarde
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  exec db pg_dump -U cadastre cadastre > backup-$(date +%Y%m%d).sql

# Restauration
cat backup.sql | docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  exec -T db psql -U cadastre
```

## Architecture production

```
                    Port 80/443
                         │
                    ┌────▼────┐
                    │  Caddy  │  ← HTTPS automatique (Let's Encrypt)
                    │  :443   │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │ Django  │  ← 2 workers gunicorn, WhiteNoise (statiques)
                    │  :8000  │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │ PostGIS │
                    │  :5432  │
                    └─────────┘
```

### Services

| Service | Image | Port exposé | Redémarrage |
|---------|-------|-------------|-------------|
| `caddy` | `caddy:2-alpine` | 80/443 → hôte | `unless-stopped` |
| `web` | Build local | — | `unless-stopped` |
| `db` | `postgis/postgis:16-3.5` | 127.0.0.1:5432 | `unless-stopped` |

La base de données n'est accessible **que depuis le VPS** (bind sur 127.0.0.1).

## Dépannage

### "502 Bad Gateway" de Caddy

Le web n'a pas encore démarré (les migrations prennent du temps). Attendre 10-20s, Caddy réessaie automatiquement.

### Permission denied sur les volumes

```bash
# Si les données importées ne sont pas accessibles
sudo chown -R 1000:1000 data/
```

### OOM Kill (mémoire insuffisante)

Le VPS doit avoir au moins **2 Go de RAM** pour l'import des données (PostGIS est gourmand). Pour un VPS à 1 Go, importer département par département.

### Erreur CSRF

Vérifier que `CSRF_TRUSTED_ORIGINS` dans `.env.prod` correspond exactement au domaine (avec `https://`).
