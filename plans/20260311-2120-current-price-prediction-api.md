# Productionizar pipeline de current_price + API de prediccion

## Goal

- Implementar un pipeline reproducible de procesamiento de datos, entrenamiento, serializacion e inferencia para el modelo leakage-free ganador de `current_price`.
- Exponer una API Flask para generar predicciones sin depender del notebook, con un contrato estable y apto para despliegue.
- Dejar un flujo local y de despliegue donde el backend pueda cargar artefactos versionados del modelo desde disco y responder predicciones de forma sincronica.

## Request Snapshot

- User request: "basado en el modelo ganador, crea un pipeline de procesamiento de datos, entrenamiento e inferencia, voy a comenzar a desplegar este modelo. quiero que crees una api para generar predicciones"
- Owner or issue: `pricing-prediction-ws0`
- Plan file: `plans/20260311-2120-current-price-prediction-api.md`

## Current State

- El backend actual solo soporta scraping. `src/pricing_prediction/app.py` registra `health_bp` y `api_v1`; `src/pricing_prediction/api/__init__.py` solo monta `scrape_runs_bp`; `src/pricing_prediction/api/scrape_runs.py` expone `POST /api/v1/scrape-runs`, `GET /api/v1/scrape-runs/<run_id>` y `GET /api/v1/scrape-runs/<run_id>/items`.
- `src/pricing_prediction/cli.py` solo tiene el subcomando `scrape-falabella`; no existe pipeline de entrenamiento, comando de build de artefactos ni flujo de inferencia.
- `src/pricing_prediction/config.py` solo configura scraping y SQLite/Postgres. No existe path de artefactos de modelo ni directorios runtime para modelos.
- `src/pricing_prediction/errors.py` solo define `ApiError`, `NotFoundError` y `DomainValidationError`; no hay un error estandar para artefacto faltante o servicio de prediccion no disponible.
- `pyproject.toml` no incluye `numpy`, `pandas`, `scikit-learn` ni `catboost`, por lo que el runtime actual no puede entrenar ni cargar el modelo ganador.
- La evidencia mas reciente del modelo vive en `notebook/20260312-current-price-no-leakage.ipynb`. El ganador corregido es `cb_leakfree_title_tfidf_deeper` con `RMSE 54.6126`, `MAE 27.1999` y `R2 0.7822`, usando `GroupKFold(5)` por `sku_id`.
- Ese notebook tambien confirma leakage en `original_price`, `discount_text`, `current_price_text`, `raw_text` y `raw_payload["prices"]`. El pipeline productivo no puede usar ninguno de esos campos.
- La base de datos ya contiene la materia prima del feature. `product_snapshots`, `products` y `product_images` guardan `query`, ranking en pagina, `brand`, `seller`, `rating`, `review_count`, `title`, `raw_payload` e imagenes URL.
- Las pruebas existentes usan Flask app factory + SQLite temporal en `tests/conftest.py`, y el patron actual es `schema -> blueprint -> service -> repository`.

## Findings

- El modelo ganador productivo no usa la rama de imagenes. En el notebook leakage-free, la rama `cb_subset_leakfree_title_tfidf_image` no supera a `cb_subset_leakfree_title_tfidf`, por lo que PyTorch e inferencia visual no son requeridos para la primera API.
- El mayor lift leakage-free viene del texto limpio del producto. El salto de `cb_leakfree_structured` a `cb_leakfree_title_tfidf_deeper` muestra que `title` transformado con `TF-IDF + SVD` es parte central del feature contract.
- `ProductSnapshot.raw_payload` contiene `GSCCategoryId`, `sellerId`, `availability`, `providerName`, `mediaUrls`, flags tipo `isBestSeller`/`isFrequentProduct` y `multipurposeBadges`, suficientes para reproducir las features leakage-free sin PDP adicional.
- `topSpecifications` y descripciones largas casi no existen en los listings actuales; por eso la primera version del pipeline debe basarse en metadata de listing y `title`, no en descripciones PDP.
- `instance/` ya esta ignorado por git en `.gitignore`, asi que es un lugar razonable para artefactos locales del modelo. No conviene commitear binarios del modelo al repo.
- La API actual ya devuelve snapshots scrappeados, pero no existe contrato de prediccion ni servicio para cargar artefactos. Eso obliga a agregar un paquete ML y un servicio de inferencia propio.
- El repo ya tiene validaciones estandarizadas con `uv run ruff format --check src tests`, `uv run ruff check src tests`, `uv run mypy src` y `uv run pytest`, asi que el feature debe integrarse a ese flujo.

## Scope

### In scope

- Agregar dependencias de runtime para entrenamiento e inferencia del ganador leakage-free: `numpy`, `pandas`, `scikit-learn` y `catboost`.
- Implementar un paquete de ML para `current_price` con extraccion de dataset desde DB, feature engineering leakage-free, entrenamiento CatBoost, `TF-IDF + SVD`, evaluacion con `GroupKFold(5)` y serializacion de artefactos.
- Implementar una CLI para entrenar y guardar artefactos del modelo en un directorio versionado.
- Implementar un servicio de inferencia que cargue artefactos desde disco, derive exactamente las mismas features del entrenamiento y emita una prediccion de `current_price`.
- Exponer `POST /api/v1/predictions/current-price` con contrato de request/response validado por Pydantic.
- Agregar pruebas unitarias, de servicio y API para el pipeline, el guard anti-leakage y la inferencia.
- Documentar setup, comando de entrenamiento y uso de la API.

### Out of scope

- Servir la rama de imagenes o incluir PyTorch en la primera API de produccion.
- Entrenamiento automatico en background, scheduler, retraining periodico o registro historico de experimentos.
- Persistir predicciones en nuevas tablas, auditar requests o versionar modelos en una base externa.
- Endpoints batch asincronicos, colas de inferencia o optimizaciones de throughput multiproceso.
- Cambiar el scraper para extraer PDPs ricos en descripcion; ese trabajo ya quedo como follow-up separado.

## File Plan

| Path | Action | Details |
| --- | --- | --- |
| `plans/20260311-2120-current-price-prediction-api.md` | create | Registrar el plan detallado del feature y el contrato propuesto. |
| `pyproject.toml` | modify | Agregar dependencias runtime de ML (`numpy`, `pandas`, `scikit-learn`, `catboost`) y mantener las validaciones existentes. |
| `README.md` | modify | Documentar entrenamiento del modelo, path de artefactos, variables de entorno y endpoint de prediccion. |
| `src/pricing_prediction/config.py` | modify | Agregar `CURRENT_PRICE_MODEL_DIR` y cualquier flag minima para cargar artefactos del modelo en runtime. |
| `src/pricing_prediction/errors.py` | modify | Agregar un error tipo `ServiceUnavailableError` o equivalente para responder `503` cuando falten artefactos o el modelo no pueda cargarse. |
| `src/pricing_prediction/api/__init__.py` | modify | Registrar un nuevo blueprint de predicciones dentro de `api_v1`. |
| `src/pricing_prediction/api/predictions.py` | create | Exponer `POST /api/v1/predictions/current-price` y delegar a un servicio de inferencia. |
| `src/pricing_prediction/schemas/prediction.py` | create | Definir `PredictCurrentPriceRequest`, `PredictCurrentPriceResponse` y validaciones de payload. |
| `src/pricing_prediction/schemas/__init__.py` | modify | Exportar los nuevos schemas si el repo mantiene exports explicitos. |
| `src/pricing_prediction/services/current_price_predictions.py` | create | Cargar artefactos, construir features leakage-free desde el request, ejecutar inferencia y devolver metadata de respuesta. |
| `src/pricing_prediction/ml/__init__.py` | create | Declarar namespace del paquete ML. |
| `src/pricing_prediction/ml/current_price/__init__.py` | create | Declarar el subpaquete del modelo `current_price`. |
| `src/pricing_prediction/ml/current_price/data.py` | create | Construir el dataset de entrenamiento desde `product_snapshots`, `products` y `product_images`, omitiendo campos con leakage. |
| `src/pricing_prediction/ml/current_price/features.py` | create | Implementar transformaciones leakage-free compartidas entre entrenamiento e inferencia: query roots/audience, ranking, title stats, availability bucket, media features y `TF-IDF + SVD`. |
| `src/pricing_prediction/ml/current_price/training.py` | create | Entrenar CatBoost, correr `GroupKFold(5)`, calcular metricas, elegir el mejor set de hiperparametros y exportar artefactos + metadata. |
| `src/pricing_prediction/ml/current_price/artifacts.py` | create | Guardar/cargar `CatBoost`, vectorizer, SVD y manifest/metadata con version, metricas y contractos de features. |
| `src/pricing_prediction/cli.py` | modify | Agregar subcomando `train-current-price-model` para entrenar y emitir un directorio de artefactos. |
| `tests/conftest.py` | modify | Agregar fixtures para artefactos falsos o paths temporales del modelo, sin romper las pruebas actuales del scraper. |
| `tests/ml/test_current_price_training.py` | create | Cubrir extraccion de dataset, guard anti-leakage, entrenamiento en muestra pequena y round-trip de artefactos. |
| `tests/services/test_current_price_predictions.py` | create | Validar carga de artefactos, defaults de features faltantes, error por artefacto ausente y prediccion deterministica con artefacto fake o fixture. |
| `tests/api/test_predictions_api.py` | create | Validar contrato HTTP, 422 por payload invalido, 503 por artefacto ausente y 200 con prediccion cuando el modelo esta disponible. |

## Data and Contract Changes

- Nueva variable de entorno:
  - `CURRENT_PRICE_MODEL_DIR`
    - Directorio que contiene el artefacto versionado del modelo activo.
    - Valor sugerido local: `instance/models/current_price/dev`
- Artefactos generados por entrenamiento:
  - `instance/models/current_price/<version>/model.cbm`
  - `instance/models/current_price/<version>/title_vectorizer.pkl`
  - `instance/models/current_price/<version>/title_svd.pkl`
  - `instance/models/current_price/<version>/metadata.json`
  - `instance/models/current_price/<version>/feature_contract.json`
- Nuevo comando CLI:
  - `uv run pricing-prediction train-current-price-model --output-dir instance/models/current_price/dev`
- Nuevo endpoint:
  - `POST /api/v1/predictions/current-price`
  - Body sugerido:
    ```json
    {
      "query": "ropa mujer",
      "page_number": 1,
      "position": 10,
      "title": "Polo casual hombre Essentials",
      "brand": "ADIDAS",
      "seller": "FALABELLA",
      "seller_id": "FALABELLA_PERU",
      "source_domain": "www.falabella.com.pe",
      "rating": 4.79,
      "review_count": 128,
      "sponsored": false,
      "gsc_category_id": "G08020208",
      "provider_name": null,
      "availability": {
        "internationalShipping": ""
      },
      "image_urls": [
        "https://media.falabella.com.pe/falabellaPE/20738858_01/public"
      ],
      "is_best_seller": false,
      "is_frequent_product": false,
      "multipurpose_badges_count": 0
    }
    ```
  - Derivaciones server-side:
    - `query_root`, `query_audience`
    - `rank_position`
    - `image_count`, `media_url_count`, `image_namespace`
    - `title_word_count`, `title_char_count`, `title_digit_count`, `title_has_pack`, `title_has_kids_token`, `title_has_sport_token`, `brand_in_title`
    - `availability_bucket`
    - `title_text` para `TF-IDF + SVD`
  - Response sugerida:
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
- Cambios de base de datos:
  - `None`
  - La primera version no requiere migraciones ni tablas nuevas.

## Implementation Steps

1. Agregar dependencias ML al runtime y documentar que el backend ahora tambien sirve inferencia, no solo scraping.
2. Introducir `CURRENT_PRICE_MODEL_DIR` en `Config` y crear el wiring minimo para que el backend conozca el directorio de artefactos activo.
3. Implementar `src/pricing_prediction/ml/current_price/data.py` con una consulta leakage-free sobre `product_snapshots`, `products` y `product_images`, evitando `original_price`, `discount_text`, `current_price_text`, `raw_text` y cualquier lectura de `raw_payload["prices"]`.
4. Implementar `src/pricing_prediction/ml/current_price/features.py` para encapsular toda la transformacion leakage-free usada en el notebook: metadata de listing, parsing seguro de `availability`, features derivadas de `title` y pipeline `TF-IDF + SVD`.
5. Implementar `src/pricing_prediction/ml/current_price/training.py` para:
   - entrenar sobre `log1p(current_price)`
   - usar `GroupKFold(n_splits=5)` por `sku_id`
   - calcular `RMSE`, `MAE` y `R2`
   - persistir el modelo ganador con su metadata
   - rechazar automaticamente features prohibidas por leakage
6. Implementar `src/pricing_prediction/ml/current_price/artifacts.py` para serializar y deserializar la combinacion `CatBoost + vectorizer + SVD + metadata`, sin depender del notebook.
7. Extender `src/pricing_prediction/cli.py` con `train-current-price-model`, ejecutado dentro de `app.app_context()`, para construir el dataset desde la DB configurada y escribir artefactos al `--output-dir`.
8. Implementar `src/pricing_prediction/services/current_price_predictions.py` para cargar artefactos una sola vez por proceso, transformar requests al mismo contrato de features del entrenamiento y emitir `predicted_current_price` en escala original.
9. Agregar `src/pricing_prediction/schemas/prediction.py` y `src/pricing_prediction/api/predictions.py` para validar payloads, responder `422` por requests invalidos y `503` cuando el artefacto no exista o no se pueda cargar.
10. Registrar el blueprint nuevo en `src/pricing_prediction/api/__init__.py` y documentar el endpoint en `README.md`.
11. Agregar pruebas especificas de:
    - guard anti-leakage
    - round-trip de artefactos
    - inferencia reproducible desde un request
    - comportamiento HTTP del endpoint de prediccion
12. Ejecutar entrenamiento local contra la DB del repo para generar un artefacto smoke-test y confirmar que la API responde usando ese bundle.

## Tests

- Unit: `tests/ml/test_current_price_training.py` cubrir:
  - que el dataset builder no expone campos prohibidos (`original_price`, `discount_text`, `current_price_text`, `raw_text`, `prices`)
  - que `query_root`, `query_audience`, `rank_position`, `availability_bucket` y features de `title` se calculan correctamente
  - que el bundle de artefactos se guarda y se vuelve a cargar sin perder metadata
- Unit: `tests/services/test_current_price_predictions.py` cubrir:
  - prediccion con artefacto fake o fixture
  - defaults cuando faltan campos opcionales
  - `503` cuando `CURRENT_PRICE_MODEL_DIR` no existe o el bundle esta incompleto
- Integration: `tests/api/test_predictions_api.py` validar:
  - `POST /api/v1/predictions/current-price` con payload valido
  - error `422` por `query`, `title`, `page_number` o `position` invalidos
  - error `503` por artefacto ausente
  - shape estable de la respuesta con `predicted_current_price`, `model_name`, `model_version` y `warnings`
- Regression: agregar un test dedicado al leakage para que futuras ediciones del pipeline fallen si alguien reintroduce features prohibidas.

## Validation

- Format: `uv run ruff format --check src tests`
- Lint: `uv run ruff check src tests`
- Types: `uv run mypy src`
- Tests: `uv run pytest tests/api/test_predictions_api.py tests/services/test_current_price_predictions.py tests/ml/test_current_price_training.py`
- Training smoke test: `uv run pricing-prediction train-current-price-model --output-dir instance/models/current_price/dev`
- API smoke test: `uv run flask --app pricing_prediction.app:create_app run --debug` y luego `POST /api/v1/predictions/current-price` con un payload minimo valido

## Risks and Mitigations

- El pipeline puede reintroducir leakage al reutilizar columnas del snapshot sin un guard formal -> Mitigar con una lista explicita de campos prohibidos y tests que fallen si aparecen en el dataset builder o en el feature contract.
- CatBoost + `TF-IDF/SVD` exige artefactos multiparte, no solo un `.cbm` -> Mitigar empaquetando manifest y artefactos auxiliares en un directorio versionado con contrato fijo y loader centralizado.
- El backend podria arrancar sin artefactos y fallar en runtime -> Mitigar con `503 Service Unavailable` claro y validacion temprana del bundle al primer uso.
- El contrato de request puede pedir metadata que un caller externo no tenga -> Mitigar dejando defaults seguros (`unknown`, `0`, `False`) y documentando que la mejor calidad se obtiene con el payload enriquecido del listing.
- Incluir PyTorch por la rama de imagenes encarece el deploy sin lift de metrica -> Mitigar dejando esa rama fuera de la primera API productiva.
- Los artefactos no deben vivir en git -> Mitigar escribiendolos bajo `instance/models/...`, documentando el flujo de build y usando `CURRENT_PRICE_MODEL_DIR` para seleccionar la version activa.

## Open Questions

- None

## Acceptance Criteria

- Existe un comando reproducible para entrenar el modelo leakage-free ganador y escribir artefactos versionados fuera del repo.
- El backend puede cargar esos artefactos y exponer `POST /api/v1/predictions/current-price`.
- El endpoint responde una prediccion de `current_price` usando el mismo contrato de features del entrenamiento, sin depender del notebook.
- El pipeline bloquea explicitamente cualquier reintroduccion de leakage por columnas de precio o textos contaminados.
- Ruff, mypy y pytest siguen ejecutables desde la raiz del repo con cobertura nueva para pipeline e API.

## Definition of Done

- Pipeline de datos, entrenamiento, artefactos e inferencia implementado para el ganador leakage-free.
- CLI de entrenamiento agregada y documentada.
- API de prediccion agregada con schemas y servicio dedicados.
- Tests de unidad, servicio y API agregados o actualizados.
- `uv run ruff format --check src tests`, `uv run ruff check src tests`, `uv run mypy src` y `uv run pytest tests/api/test_predictions_api.py tests/services/test_current_price_predictions.py tests/ml/test_current_price_training.py` en verde.
- Plan actualizado si durante la implementacion cambia el contrato de features, el endpoint o la estrategia de artefactos.
