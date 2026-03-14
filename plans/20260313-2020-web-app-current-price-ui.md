# Web app con home y flujo de prediccion current_price

## Goal

- Convertir el backend Flask actual en una app web utilizable por usuarios finales, con un home publico y una vista para generar predicciones.
- Reusar el contrato y el servicio existentes de `POST /api/v1/predictions/current-price` sin rehacer el modelo ni introducir un frontend separado en la primera iteracion.
- Permitir que la vista de prediccion acepte URLs de imagen y archivos subidos por el usuario como input suplementario, dejando claro que el modelo actual no hace analisis visual del contenido.

## Request Snapshot

- User request: "revisa este repositorio, quiero hacer una aplicacion basada en este codigo, lo que tiene que tener es un home y una parte donde pueda generar predicciones a partir del api disponible en la aplicacion. Deberia ser capaz de cargar mis propias imagenes o de pasar imagenes en url, para la parte de prediccion. Haz un plan para implementar esto, que framework me sugieres?"
- Owner or issue: `pricing-prediction-dwj`
- Plan file: `plans/20260313-2020-web-app-current-price-ui.md`

## Current State

- El proyecto hoy es un backend Flask sin capa web de templates. `src/pricing_prediction/app.py` crea la app, registra `health_bp` y `api_v1`, y responde JSON en `/`.
- La API de prediccion ya existe en `src/pricing_prediction/api/predictions.py` como `POST /api/v1/predictions/current-price`.
- El request actual vive en `src/pricing_prediction/schemas/prediction.py::PredictCurrentPriceRequest` y exige `query`, `page_number`, `position` y `title`; el resto del payload es opcional.
- La inferencia actual vive en `src/pricing_prediction/services/current_price_predictions.py::CurrentPricePredictionService` y ya cachea el bundle del modelo por proceso.
- El feature engineering de inferencia se construye en `src/pricing_prediction/ml/current_price/features.py::build_inference_source_frame`.
- El modelo no procesa pixeles de imagen. Hoy `image_urls` solo alimenta features derivadas como `image_count`, `media_url_count` y `image_namespace` a partir de `first_image_url`.
- No existe `templates/`, `static/`, `render_template`, ni toolchain Node. `pyproject.toml` y `README.md` confirman un flujo 100% Python con `uv`, `ruff`, `mypy` y `pytest`.
- Las pruebas disponibles usan `create_app()` y `app.test_client()` en `tests/conftest.py`, lo que facilita agregar pruebas HTML y de formularios sin cambiar el harness.

## Findings

- El camino de menor riesgo para una v1 es mantener Flask como framework principal y agregar una capa server-rendered con Jinja + JS liviano. No hace falta introducir Next.js ni otra runtime para cumplir el pedido.
- El servicio de prediccion ya esta desacoplado del transporte HTTP. La vista web puede reutilizar `PredictCurrentPriceRequest` y `CurrentPricePredictionService` sin llamar por HTTP al endpoint interno.
- Soportar archivos subidos por el usuario no equivale a soporte de inferencia visual. Con el modelo actual, un archivo solo puede traducirse a metadata de conteo y a un placeholder URI; el peso fuerte de la prediccion sigue estando en `query`, `title` y metadata del listing.
- Aceptar URLs manuales si aporta una senal mas cercana al entrenamiento que aceptar archivos locales, porque `image_namespace` puede seguir viniendo de dominios reales.
- Cambiar `/` de JSON a HTML es razonable para una app web porque `GET /health` y `/api/v1/...` ya cubren los contratos machine-to-machine del servicio.
- No hay evidencia de necesidad para base de datos nueva, migraciones, storage persistente ni autenticacion en esta iteracion.

## Scope

### In scope

- Mantener Flask como framework de aplicacion para v1 y construir la UI dentro del mismo proceso.
- Agregar un blueprint web con home y formulario de prediccion.
- Agregar un adaptador de formulario que convierta `multipart/form-data` y entradas manuales al contrato `PredictCurrentPriceRequest`.
- Permitir dos fuentes de imagen en la UI: lista de URLs y archivos locales.
- Mostrar resultado, metadata del modelo y warnings devueltos por `CurrentPricePredictionService`.
- Mantener intacto `POST /api/v1/predictions/current-price` como contrato JSON para integraciones externas.
- Documentar de forma explicita que la prediccion no es image-only y que las imagenes son input suplementario en el estado actual del modelo.

### Out of scope

- Separar un frontend React/Next.js en esta primera entrega.
- Reentrenar el modelo para hacer inferencia visual real o prediccion solo a partir de imagenes.
- Persistir uploads, usuarios, historico de predicciones o sesiones.
- Agregar autenticacion, panel admin, pagos o despliegues multi-servicio.
- Batch prediction, colas async o cambios de infraestructura.

## File Plan

| Path | Action | Details |
| --- | --- | --- |
| `plans/20260313-2020-web-app-current-price-ui.md` | create | Registrar el plan implementable del feature y la decision de stack. |
| `README.md` | modify | Documentar el modo web, comandos para levantar la app y la limitacion actual del input de imagenes. |
| `src/pricing_prediction/app.py` | modify | Registrar el nuevo blueprint web y mover el home publico fuera del handler JSON actual de `/`. |
| `src/pricing_prediction/config.py` | modify | Agregar limites configurables para archivos del formulario web, por ejemplo `MAX_CONTENT_LENGTH`, cantidad maxima de imagenes y extensiones permitidas. |
| `src/pricing_prediction/web/__init__.py` | create | Declarar el namespace del modulo web y exportar `web_bp`. |
| `src/pricing_prediction/web/routes.py` | create | Implementar `GET /`, `GET /predict` y `POST /predict`, renderizado HTML, manejo de errores de validacion y uso directo de `CurrentPricePredictionService`. |
| `src/pricing_prediction/web/forms.py` | create | Parsear `request.form` y `request.files`, normalizar tipos, dividir URLs por linea, validar archivos y construir `PredictCurrentPriceRequest`. |
| `src/pricing_prediction/templates/base.html` | create | Layout comun, navegacion, slots para errores y metadata general de la app. |
| `src/pricing_prediction/templates/home.html` | create | Home con explicacion del producto, CTA a prediccion y resumen del alcance real del modelo. |
| `src/pricing_prediction/templates/predict.html` | create | Formulario principal con campos obligatorios, seccion avanzada, input de URLs y upload de archivos, mas render de resultados. |
| `src/pricing_prediction/templates/partials/prediction_result.html` | create | Parcial reutilizable para mostrar precio predicho, warnings, version de modelo y resumen del payload enviado. |
| `src/pricing_prediction/static/css/app.css` | create | Estilos de la experiencia web sin agregar toolchain frontend. |
| `src/pricing_prediction/static/js/predict-form.js` | create | Preview de archivos locales, contador de imagenes, UX de URLs y mejoras progresivas sin build step. |
| `tests/web/test_pages.py` | create | Cubrir `GET /`, `GET /predict`, submit valido, submit invalido y mensaje amigable cuando no hay bundle de modelo. |
| `tests/web/test_prediction_forms.py` | create | Cubrir parseo de booleans/numericos, mezcla de URLs + archivos, limites de archivos y conversion a `PredictCurrentPriceRequest`. |
| `tests/api/test_predictions_api.py` | keep | La suite existente ya cubre el endpoint JSON de prediccion y sirve como regresion mientras se agrega la capa web. |

## Data and Contract Changes

- Nuevas rutas HTML:
  - `GET /` -> home server-rendered.
  - `GET /predict` -> formulario de prediccion.
  - `POST /predict` -> submit `multipart/form-data` o `application/x-www-form-urlencoded` con render HTML del resultado.
- Contrato API existente:
  - `POST /api/v1/predictions/current-price` permanece sin cambios.
- Conversion de imagenes en la UI:
  - URLs ingresadas manualmente se pasan tal cual a `image_urls`.
  - Archivos locales se validan por extension/tamano y se traducen a placeholders `upload://<filename>` solo para conservar conteo y compatibilidad del contrato. No se persisten ni se analizan como pixeles.
- Cambios de configuracion:
  - `MAX_CONTENT_LENGTH` para evitar uploads demasiado grandes.
  - Limites del formulario web, por ejemplo `WEB_PREDICTION_MAX_IMAGE_FILES` y `WEB_PREDICTION_ALLOWED_EXTENSIONS`.
- Cambios de base de datos:
  - `None`

## Implementation Steps

1. Resolver la decision de framework para v1 dejando Flask como stack principal y usar templates Jinja + JS liviano en lugar de introducir un frontend separado.
2. Crear `src/pricing_prediction/web/` y registrar un `web_bp` en `src/pricing_prediction/app.py`, manteniendo `health_bp` y `api_v1` intactos.
3. Mover el home publico a una vista HTML en `GET /` y dejar la salud operativa en `GET /health`.
4. Implementar `src/pricing_prediction/web/forms.py` para:
   - leer campos obligatorios y opcionales del formulario,
   - normalizar `int`, `float` y `bool`,
   - dividir el textarea de URLs en `list[str]`,
   - validar cantidad, tipo y tamano de archivos,
   - convertir archivos seleccionados a placeholders `upload://...`,
   - construir `PredictCurrentPriceRequest` para reutilizar exactamente el contrato del backend.
5. Implementar `src/pricing_prediction/web/routes.py` con dos flujos:
   - render inicial del formulario,
   - submit sincronico que llama `CurrentPricePredictionService.from_app(current_app).predict(...)` y renderiza el parcial de resultado.
6. Manejar errores de forma HTML dentro del blueprint web:
   - errores de validacion del formulario como mensajes inline,
   - `ServiceUnavailableError` como estado vacio amigable si el bundle del modelo no existe,
   - mantener los handlers JSON existentes para `/api/v1/...`.
7. Crear `base.html`, `home.html`, `predict.html` y `partials/prediction_result.html`, con una nota visible que explique que las imagenes hoy son apoyo contextual y no entrada visual real del modelo.
8. Agregar `static/css/app.css` y `static/js/predict-form.js` para preview local de archivos, contador de imagenes y UX minima sin requerir bundler.
9. Actualizar `README.md` con:
   - framework recomendado para esta base: Flask server-rendered,
   - comando de arranque,
   - rutas nuevas,
   - limitaciones actuales del modelo respecto a imagenes.
10. Agregar pruebas web nuevas y reutilizar la suite API existente para asegurar que la capa HTML no rompe `POST /api/v1/predictions/current-price`.

## Tests

- Unit: `tests/web/test_prediction_forms.py` cubrir:
  - parseo de campos obligatorios y opcionales,
  - conversion de URLs multi-linea a `image_urls`,
  - conversion de archivos a placeholders `upload://...`,
  - rechazo por extension no permitida o exceso de archivos.
- Integration: `tests/web/test_pages.py` validar:
  - `GET /` devuelve HTML y el CTA a prediccion,
  - `GET /predict` expone el formulario con campos base,
  - `POST /predict` con datos minimos validos muestra `predicted_current_price`,
  - `POST /predict` con payload invalido vuelve a renderizar errores en HTML,
  - `POST /predict` sin bundle de modelo muestra mensaje amigable en lugar de JSON crudo.
- Regression: mantener `tests/api/test_predictions_api.py` dentro de la validacion para confirmar que el endpoint JSON de prediccion sigue respondiendo igual despues de agregar la capa web.

## Validation

- Format: `uv run ruff format --check src tests`
- Lint: `uv run ruff check src tests`
- Types: `uv run mypy src`
- Tests: `uv run pytest tests/web/test_pages.py tests/web/test_prediction_forms.py tests/api/test_predictions_api.py tests/services/test_current_price_predictions.py`
- Manual smoke test: `uv run flask --app pricing_prediction.app:create_app run --debug` y revisar `http://127.0.0.1:5000/` y `http://127.0.0.1:5000/predict`

## Risks and Mitigations

- El usuario puede interpretar "subir imagenes" como inferencia visual real -> Mitigar con copy visible en home y formulario, y dejar el reentrenamiento multimodal fuera de esta iteracion.
- Los archivos locales no traen un `image_namespace` comparable al de entrenamiento -> Mitigar tratando uploads como input suplementario, no obligatorio, y privilegiando URLs reales cuando existan.
- Cambiar `/` de JSON a HTML puede sorprender a algun consumidor informal -> Mitigar dejando `GET /health` y `/api/v1/...` como contratos oficiales para integraciones.
- El formulario puede duplicar reglas de validacion del schema JSON -> Mitigar construyendo siempre `PredictCurrentPriceRequest` desde el adaptador del formulario, en lugar de mantener dos contratos separados.
- Introducir un frontend separado ahora agregaria Node, package manager, lint, typecheck y despliegue dual sin necesidad inmediata -> Mitigar resolviendo la v1 dentro de Flask y revaluando una separacion solo si la UX o el roadmap lo justifican.

## Open Questions

- None

## Acceptance Criteria

- `GET /` muestra un home HTML utilizable y orientado al producto.
- `GET /predict` muestra un formulario para predecir precio usando el modelo actual.
- El formulario acepta tanto URLs de imagen como archivos locales del usuario.
- El submit del formulario reutiliza `PredictCurrentPriceRequest` y `CurrentPricePredictionService`, no una logica paralela.
- `POST /api/v1/predictions/current-price` sigue funcionando para clientes JSON externos.
- La documentacion deja claro que la prediccion actual no es image-only.

## Definition of Done

- Capa web implementada dentro del backend Flask.
- Home y flujo de prediccion disponibles y navegables desde el navegador.
- Upload de archivos y entrada de URLs soportados en la UI con validaciones basicas.
- Tests web y regresiones de API agregados o actualizados.
- `uv run ruff format --check src tests`, `uv run ruff check src tests`, `uv run mypy src` y `uv run pytest tests/web/test_pages.py tests/web/test_prediction_forms.py tests/api/test_predictions_api.py tests/services/test_current_price_predictions.py` definidos como gates del cambio.
- El plan se actualiza si cambia el contrato de UI, la estrategia de uploads o la recomendacion de framework.
