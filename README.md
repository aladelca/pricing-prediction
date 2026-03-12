# pricing-prediction

Backend Flask para ejecutar corridas de scraping sobre Falabella Peru y persistir snapshots de productos en Postgres compatible con Supabase.

## Stack

- Flask
- SQLAlchemy
- Alembic
- httpx
- BeautifulSoup
- Pydantic
- CatBoost
- pandas / scikit-learn
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
- `POST /api/v1/predictions/current-price`

## Ejecutar una corrida por CLI

```bash
uv run pricing-prediction scrape-falabella --query "ropa mujer" --max-pages 30
```

## Entrenar el modelo de `current_price`

El pipeline productivo implementa el ganador leakage-free `cb_leakfree_title_tfidf_deeper`. Usa `GroupKFold(5)` por `sku_id`, hace feature engineering sobre metadata del listing e incorpora `TF-IDF + SVD` sobre `title`.

Los artefactos se escriben por defecto en `instance/models/current_price/dev`, o en el directorio indicado por `CURRENT_PRICE_MODEL_DIR`.

```bash
uv run pricing-prediction train-current-price-model \
  --output-dir instance/models/current_price/dev
```

Variables y restricciones relevantes:

- `CURRENT_PRICE_MODEL_DIR`: directorio activo del bundle para inferencia.
- El pipeline bloquea columnas con leakage: `current_price_text`, `original_price`, `original_price_text`, `discount_text`, `raw_text`, `raw_prices`, `price`, `prices`.
- La primera API de producción no carga PyTorch ni embeddings visuales; la rama de imágenes no superó al campeón leakage-free.

Bundle generado:

- `model.cbm`
- `title_vectorizer.pkl`
- `title_svd.pkl`
- `metadata.json`
- `feature_contract.json`

## Consumir la API de predicción

```bash
curl -X POST http://127.0.0.1:5000/api/v1/predictions/current-price \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "ropa mujer",
    "page_number": 1,
    "position": 10,
    "title": "Polera mujer sport essentials",
    "brand": "Adidas",
    "seller": "Falabella",
    "rating": 4.7,
    "review_count": 44,
    "gsc_category_id": "G08020208",
    "availability": {"internationalShipping": ""},
    "image_urls": ["https://media.falabella.com.pe/falabellaPE/20738858_01/public"]
  }'
```

Respuesta esperada:

```json
{
  "data": {
    "predicted_current_price": 179.42,
    "currency": "PEN",
    "model_name": "cb_leakfree_title_tfidf_deeper",
    "model_version": "20260312-01",
    "target": "current_price",
    "features_version": "v1",
    "warnings": []
  }
}
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
