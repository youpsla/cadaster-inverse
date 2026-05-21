FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    gdal-bin libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv sync

COPY . .
RUN uv run python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["uv", "run", "gunicorn", "config.wsgi", "-b", "0.0.0.0:8000"]
