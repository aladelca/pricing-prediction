# pricing-prediction

Backend Flask para ejecutar corridas de scraping sobre Falabella Peru y persistir snapshots de productos en Postgres compatible con Supabase.

## Stack

- Flask
- SQLAlchemy
- Alembic
- httpx
- BeautifulSoup
- Pydantic
- Selenium como fallback opcional

## Setup

```bash
uv sync --extra dev
cp -f .env.example .env
uv run alembic upgrade head
```

## Ejecutar la API

```bash
uv run flask --app pricing_prediction.app:create_app run --debug
```

Endpoints principales:

- `GET /health`
- `POST /api/v1/scrape-runs`
- `GET /api/v1/scrape-runs/<run_id>`
- `GET /api/v1/scrape-runs/<run_id>/items`

## Ejecutar una corrida por CLI

```bash
uv run pricing-prediction scrape-falabella --query "ropa mujer" --max-pages 30
```

## Persistencia de imagenes

La primera version guarda URLs de imagen en Postgres. Si luego necesitas almacenar binarios, usa Supabase Storage y agrega una referencia `storage_path` en la tabla de imagenes.

## Validaciones

```bash
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src
uv run pytest
```
