# Implementacion de scraper Falabella + Supabase

## Goal

- Construir desde cero un servicio Flask que reciba una query, recorra al menos las primeras 30 paginas de `falabella.com.pe`, extraiga productos y persista corridas y snapshots en Postgres de Supabase.
- Dejar un entry point reutilizable por API y CLI, con una base que luego permita ampliar paginas, retailers o campos sin rehacer la arquitectura.

## Request Snapshot

- User request: "quiero implementar un scrapping de la pagina falabella.com, que me permita traer los datos de los nombres de los productos, las imagenes, las marcas y los diferentes precios ... la idea es que tenga como input una query ... quiero guardarlo todo en una bbdd postgres de supabase" + aclaracion posterior: "tienes que partir desde cero" y "al menos las primeras 30" paginas.
- Owner or issue: `pricing-prediction-8fi`
- Plan file: `plans/20260309-2101-falabella-scraper-supabase.md`

## Current State

- El repo no tiene codigo de aplicacion; hoy solo existen `AGENTS.md`, `plans/.gitkeep`, `.beads/` y archivos de skills.
- No existe `pyproject.toml`, app factory Flask, config, migraciones, tests, ni configuracion de Ruff o mypy.
- La exploracion de Falabella se hizo sobre `https://www.falabella.com.pe/falabella-pe/search?Ntt=ropa+mujer` y `https://www.falabella.com.pe/falabella-pe/search?Ntt=ropa+mujer&page=30`.

## Findings

- `GET https://www.falabella.com.pe/falabella-pe/search?Ntt=<query>&page=<n>` devuelve HTML SSR con script `#__NEXT_DATA__`; no es necesario renderizar el DOM completo para obtener resultados.
- `pageProps.results[]` contiene `productId`, `skuId`, `displayName`, `brand`, `sellerName`, `prices`, `mediaUrls`, `url`, `discountBadge`, `rating` e `isSponsored`.
- La paginacion usa el query param `page`; la pagina 30 mantuvo `currentPage: 30` y 48 resultados, por lo que el alcance minimo de 30 paginas es viable.
- La pagina 1 puede devolver 49 resultados aunque `perPage` sea 48 por slots patrocinados; no se debe asumir una cardinalidad fija por pagina.
- Hay banner de cookies con boton `Aceptar` y una UI con lazy loading; esto importa para un fallback browser, pero no bloquea la extraccion HTTP del HTML inicial.
- Recomendacion principal: usar `httpx` + parseo de `__NEXT_DATA__` como extractor productivo y mantener Selenium solo como fallback y mecanismo de debugging.
- Recomendacion de persistencia: guardar URLs de imagen en Postgres; si luego necesitas binarios, usar Supabase Storage y persistir el `storage_path` en la base, no blobs en Postgres.
- Recomendacion de ejecucion: no hacer una corrida completa de 30 paginas dentro de una request HTTP bloqueante; usar una corrida registrada (`scrape_run`) y ejecutar el scraping desde un servicio reutilizable invocable por CLI y por backend.

## Scope

### In scope

- Scaffolding completo desde cero del proyecto Python con Flask, SQLAlchemy, Alembic, pytest, Ruff, mypy y `uv`.
- Cliente Falabella basado en HTTP, parser de `__NEXT_DATA__`, normalizacion de precios, imagenes y metadatos, y crawl paginado de al menos 30 paginas.
- Persistencia en Supabase Postgres para corridas, productos, imagenes y snapshots por corrida/query/pagina.
- API minima y CLI para crear corridas, ejecutarlas y consultar resultados.
- Fixtures y pruebas basadas en HTML real de la pagina 1 y la pagina 30.

### Out of scope

- Descargar y almacenar binarios de imagenes en la primera entrega.
- Scraping de PDP para descripcion larga, atributos extendidos, stock o variantes por talla/color.
- Scheduler distribuido, Celery, RQ o workers separados; la primera version debe quedar lista para integrarlo luego, pero no incluirlo.
- Dashboard o interfaz web para disparar corridas.
- Garantizar scraping de las 200 paginas disponibles; la primera entrega debe garantizar al menos 30 y dejar el limite configurable.

## File Plan

| Path | Action | Details |
| --- | --- | --- |
| `pyproject.toml` | create | Definir dependencias y tooling: `flask`, `sqlalchemy`, `alembic`, `psycopg[binary]`, `httpx`, `beautifulsoup4`, `pydantic`, `tenacity`, `selenium`, `pytest`, `ruff`, `mypy`. |
| `.env.example` | create | Documentar `DATABASE_URL`, `FLASK_ENV`, `SCRAPER_DEFAULT_MAX_PAGES`, `SCRAPER_MAX_ALLOWED_PAGES`, `SCRAPER_REQUEST_TIMEOUT`, `SCRAPER_REQUEST_DELAY_MS`, `SCRAPER_RETRY_ATTEMPTS`, `SCRAPER_USER_AGENT`. |
| `README.md` | create | Setup local, migraciones, comandos de scrape, consultas a la API y decision de almacenar URLs de imagen. |
| `src/pricing_prediction/__init__.py` | create | Declarar package. |
| `src/pricing_prediction/app.py` | create | Implementar `create_app` y registrar blueprints y extensiones. |
| `src/pricing_prediction/config.py` | create | Config por entorno y limites del scraper. |
| `src/pricing_prediction/extensions.py` | create | Inicializar `SQLAlchemy` y `Migrate`. |
| `src/pricing_prediction/api/__init__.py` | create | Registrar blueprint `api_v1`. |
| `src/pricing_prediction/api/health.py` | create | Exponer `GET /health`. |
| `src/pricing_prediction/api/scrape_runs.py` | create | Exponer `POST /api/v1/scrape-runs`, `GET /api/v1/scrape-runs/<run_id>` y `GET /api/v1/scrape-runs/<run_id>/items`. |
| `src/pricing_prediction/schemas/scrape.py` | create | Validar request/response de corridas y resultados. |
| `src/pricing_prediction/db/models.py` | create | Modelos `ScrapeRun`, `Product`, `ProductImage` y `ProductSnapshot`. |
| `src/pricing_prediction/db/repositories.py` | create | Upserts, consultas paginadas y escritura idempotente por corrida. |
| `src/pricing_prediction/services/scrape_runs.py` | create | Orquestar una corrida: crear run, iterar paginas, persistir estado y errores. |
| `src/pricing_prediction/clients/falabella_client.py` | create | Construir URLs `Ntt`/`page`, ejecutar requests con timeouts, retries y rate limiting suave. |
| `src/pricing_prediction/scraper/falabella/next_data.py` | create | Extraer `#__NEXT_DATA__` del HTML y convertirlo en un payload estructurado. |
| `src/pricing_prediction/scraper/falabella/normalize.py` | create | Normalizar `prices`, `discountBadge`, `rating`, `mediaUrls`, `sellerName`, `source_url` y `product_url`. |
| `src/pricing_prediction/scraper/falabella/browser_fallback.py` | create | Fallback Selenium para campañas donde el HTML server-side no traiga el payload esperado; incluir captura de screenshot y HTML debug. |
| `src/pricing_prediction/cli.py` | create | Entry point `python -m pricing_prediction.cli scrape-falabella --query ... --max-pages ...`. |
| `migrations/env.py` | create | Wiring Alembic/Flask-Migrate. |
| `migrations/versions/20260310_01_create_scrape_tables.py` | create | Crear tablas iniciales, constraints e indices. |
| `tests/conftest.py` | create | Fixtures de app, base de datos de prueba y client HTTP. |
| `tests/fixtures/falabella/search_page_1.html` | create | Fixture SSR real para query `ropa mujer`, pagina 1. |
| `tests/fixtures/falabella/search_page_30.html` | create | Fixture SSR real para query `ropa mujer`, pagina 30. |
| `tests/scraper/falabella/test_next_data_parser.py` | create | Verificar extraccion del payload, pagina actual y conteo de resultados. |
| `tests/scraper/falabella/test_normalize.py` | create | Cubrir precios actuales/originales, sponsored, ratings, seller e imagenes. |
| `tests/services/test_scrape_runs.py` | create | Probar corrida de multiples paginas, upserts y persistencia. |
| `tests/api/test_scrape_runs.py` | create | Validar contratos API, errores de validacion y consulta de resultados. |

## Data and Contract Changes

- API request para crear corridas:
  - `POST /api/v1/scrape-runs`
  - Body:
    ```json
    {
      "query": "ropa mujer",
      "max_pages": 30,
      "source": "falabella_pe"
    }
    ```
  - Respuesta recomendada: `202 Accepted` con `run_id`, `status` y `requested_pages`.
- API de consulta:
  - `GET /api/v1/scrape-runs/<run_id>`
  - `GET /api/v1/scrape-runs/<run_id>/items?limit=50&offset=0`
- Tabla `scrape_runs`:
  - `id uuid pk`
  - `source text`
  - `query text`
  - `requested_pages integer`
  - `scraped_pages integer`
  - `scraped_items integer`
  - `status text`
  - `error_message text nullable`
  - `started_at timestamptz`
  - `finished_at timestamptz nullable`
  - `created_at timestamptz`
- Tabla `products`:
  - `sku_id text unique`
  - `product_id text`
  - `canonical_url text`
  - `source_domain text`
  - `brand text`
  - `title text`
  - `seller text`
  - `first_seen_at timestamptz`
  - `last_seen_at timestamptz`
  - `raw_payload jsonb`
- Tabla `product_images`:
  - `id uuid pk`
  - `sku_id text fk -> products.sku_id`
  - `position integer`
  - `image_url text`
  - Unique recomendada: `(sku_id, position, image_url)`
- Tabla `product_snapshots`:
  - `id uuid pk`
  - `run_id uuid fk -> scrape_runs.id`
  - `sku_id text fk -> products.sku_id`
  - `query text`
  - `page_number integer`
  - `position integer`
  - `source_url text`
  - `product_url text`
  - `current_price numeric(10,2) nullable`
  - `current_price_text text nullable`
  - `original_price numeric(10,2) nullable`
  - `original_price_text text nullable`
  - `discount_text text nullable`
  - `rating numeric(3,2) nullable`
  - `review_count integer nullable`
  - `seller text nullable`
  - `sponsored boolean not null`
  - `raw_text text`
  - `raw_prices jsonb`
  - `raw_payload jsonb`
  - `scraped_at timestamptz`
  - Unique recomendada: `(run_id, page_number, position, sku_id)`
- Variables de entorno nuevas:
  - `DATABASE_URL`
  - `SCRAPER_DEFAULT_MAX_PAGES`
  - `SCRAPER_MAX_ALLOWED_PAGES`
  - `SCRAPER_REQUEST_TIMEOUT`
  - `SCRAPER_REQUEST_DELAY_MS`
  - `SCRAPER_RETRY_ATTEMPTS`
  - `SCRAPER_USER_AGENT`

## Implementation Steps

1. Crear el esqueleto del proyecto Python desde cero con `uv`, `src/` layout, Flask app factory, SQLAlchemy, Alembic, pytest, Ruff y mypy.
2. Definir configuracion central y modelos de datos para `scrape_runs`, `products`, `product_images` y `product_snapshots`, incluyendo migracion inicial e indices.
3. Implementar `FalabellaClient` con `httpx`, headers tipo navegador, timeout, reintentos con backoff y constructor de URLs `search?Ntt=<query>&page=<n>`.
4. Implementar el parser de `#__NEXT_DATA__` y el normalizador que convierta cada item en un contrato interno con `product_id`, `sku_id`, `title`, `brand`, `seller`, `prices`, `image_urls`, `product_url`, `source_url`, `page_number`, `position`, `sponsored` y `raw_payload`.
5. Implementar `ScrapeRunService` para recorrer paginas `1..max_pages`, respetar el limite configurado, persistir progreso incremental y tolerar errores parciales pagina por pagina.
6. Implementar el fallback Selenium solo cuando el HTML no traiga `#__NEXT_DATA__` o el payload venga vacio, guardando bundles de debug con screenshot y HTML.
7. Exponer una CLI para ejecutar corridas manuales y una API Flask para registrar corridas y consultar estado/resultados sin duplicar logica de negocio.
8. Agregar fixtures HTML reales, pruebas unitarias del parser/normalizador, pruebas de servicio para 30 paginas y pruebas de contrato API.
9. Documentar setup, variables de entorno, comando de migracion, comando de scrape y decision de persistir URLs de imagen en README.

## Tests

- Unit: `tests/scraper/falabella/test_next_data_parser.py` cubrir extraccion de `pageProps.results`, `pagination.currentPage` y estructura de pagina 1 vs pagina 30.
- Unit: `tests/scraper/falabella/test_normalize.py` cubrir parseo de precios, discounts, `isSponsored`, rating, seller y multiple `mediaUrls`.
- Integration: `tests/services/test_scrape_runs.py` validar una corrida de 30 paginas simuladas, manejo de resultados patrocinados y upserts idempotentes.
- Integration: `tests/api/test_scrape_runs.py` validar `POST` de corrida, error por `query` vacia, enforcement del maximo de paginas y consulta de items persistidos.
- Regression: fijar fixtures SSR de pagina 1 y pagina 30 para detectar cambios del contrato `__NEXT_DATA__` sin depender del sitio en cada test.

## Validation

- Format: `uv run ruff format --check src tests`
- Lint: `uv run ruff check src tests`
- Types: `uv run mypy src`
- Tests: `uv run pytest`
- Migration smoke test: `uv run alembic upgrade head`
- End-to-end local smoke test: `uv run python -m pricing_prediction.cli scrape-falabella --query "ropa mujer" --max-pages 30`

## Risks and Mitigations

- Falabella puede cambiar el shape de `__NEXT_DATA__` -> Mitigar guardando `raw_payload`, fijando fixtures reales y manteniendo fallback Selenium.
- Cloudflare o protecciones anti-bot pueden bloquear corridas agresivas -> Mitigar con rate limiting suave, retries, headers realistas y ejecucion HTTP secuencial en la primera version.
- Una corrida de 30 paginas puede tardar demasiado para una request HTTP sincrona -> Mitigar devolviendo `202` y separando el flujo de ejecucion de la capa HTTP.
- Un mismo producto puede repetirse por patrocinio o paginacion -> Mitigar con upsert en `products` por `sku_id` y uniqueness por `run_id/page_number/position/sku_id` en snapshots.
- Imagenes en Postgres pueden inflar innecesariamente la base si se guardan como binario -> Mitigar guardando solo URLs o, si luego hace falta, usando Supabase Storage.

## Open Questions

- None

## Acceptance Criteria

- Dada una query, el sistema puede recorrer al menos las primeras 30 paginas de Falabella usando el parametro `page`.
- Cada snapshot persistido incluye nombre del producto, marca, seller, URLs de imagen, precios actuales/originales, descuento, pagina, posicion, `product_id`, `sku_id`, `product_url`, `source_url` y `scraped_at`.
- El backend expone un contrato estable para crear una corrida y consultar su estado y resultados.
- La corrida persiste progreso incremental y no pierde los resultados de paginas ya procesadas si una pagina falla.
- Ruff, mypy y pytest quedan configurados y ejecutables desde la raiz del repo.

## Definition of Done

- Proyecto Flask creado desde cero con estructura mantenible.
- Scraper Falabella implementado con extraccion HTTP de `__NEXT_DATA__` y fallback browser.
- Persistencia en Supabase Postgres operativa con migraciones y modelos.
- API, CLI y pruebas agregadas o actualizadas.
- `uv run ruff format --check src tests`, `uv run ruff check src tests`, `uv run mypy src` y `uv run pytest` en verde.
- Plan actualizado si durante la implementacion cambia el alcance o el contrato de extraccion.
