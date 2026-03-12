# Runbook: Current Price Prediction API

## Objetivo

Este runbook documenta como invocar `POST /api/v1/predictions/current-price` con payloads reales derivados de snapshots existentes en `instance/pricing_prediction.db`.

Los ejemplos de abajo se validaron localmente el 12 de marzo de 2026 contra el bundle activo:

- `CURRENT_PRICE_MODEL_DIR=instance/models/current_price/dev`
- `model_name=cb_leakfree_title_tfidf_deeper`
- `model_version=20260312-014817`

## Prerrequisitos

1. Tener el bundle del modelo entrenado en `instance/models/current_price/dev`.
2. Levantar la API:

```bash
uv run flask --app pricing_prediction.app:create_app run --debug
```

3. Verificar salud del servicio:

```bash
curl http://127.0.0.1:5000/health
```

## Contrato minimo

Campos obligatorios del request:

- `query`
- `page_number`
- `position`
- `title`

Campos opcionales recomendados:

- `brand`
- `seller`
- `seller_id`
- `source_domain`
- `rating`
- `review_count`
- `sponsored`
- `gsc_category_id`
- `provider_name`
- `availability`
- `image_urls`
- `is_best_seller`
- `is_frequent_product`
- `multipurpose_badges_count`

## Respuesta esperada

```json
{
  "data": {
    "predicted_current_price": 141.23,
    "currency": "PEN",
    "model_name": "cb_leakfree_title_tfidf_deeper",
    "model_version": "20260312-014817",
    "target": "current_price",
    "features_version": "v1",
    "warnings": []
  }
}
```

## Payloads reales

### Ejemplo 1: `zapatos hombre`

Origen real:

- `sku_id=126034143`
- `query=zapatos hombre`
- `observed_current_price=174.90`

```bash
curl -X POST http://127.0.0.1:5000/api/v1/predictions/current-price \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "zapatos hombre",
    "page_number": 50,
    "position": 23,
    "title": "Pack 5 Pares Horma Zapatos Formador Ensanchador Hombre/mujer",
    "brand": "GENERICO",
    "seller": "GOLIANK TECH",
    "seller_id": "SCD0BF3",
    "source_domain": "www.falabella.com.pe",
    "rating": null,
    "review_count": null,
    "sponsored": false,
    "gsc_category_id": "G180102",
    "provider_name": null,
    "availability": {
      "homeDeliveryShipping": "",
      "pickUpFromStoreShipping": "",
      "internationalShipping": "",
      "primeShipping": "",
      "expressShipping": ""
    },
    "image_urls": [
      "https://media.falabella.com.pe/falabellaPE/126034143_01/public",
      "https://media.falabella.com.pe/falabellaPE/126034143_02/public",
      "https://media.falabella.com.pe/falabellaPE/126034143_03/public"
    ],
    "is_best_seller": false,
    "is_frequent_product": false,
    "multipurpose_badges_count": 0
  }'
```

Respuesta real observada:

```json
{
  "data": {
    "predicted_current_price": 132.25,
    "currency": "PEN",
    "model_name": "cb_leakfree_title_tfidf_deeper",
    "model_version": "20260312-014817",
    "target": "current_price",
    "features_version": "v1",
    "warnings": []
  }
}
```

### Ejemplo 2: `zapatos niños`

Origen real:

- `sku_id=143420092`
- `query=zapatos niños`
- `observed_current_price=47.00`

```bash
curl -X POST http://127.0.0.1:5000/api/v1/predictions/current-price \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "zapatos niños",
    "page_number": 50,
    "position": 48,
    "title": "Zapatos Medias De Carrito Para Niño Talla 22-23",
    "brand": "GENERICO",
    "seller": "Importaciones Nokol",
    "seller_id": "SC06727",
    "source_domain": "www.falabella.com.pe",
    "rating": null,
    "review_count": null,
    "sponsored": false,
    "gsc_category_id": "G220204",
    "provider_name": null,
    "availability": {
      "homeDeliveryShipping": "",
      "pickUpFromStoreShipping": "",
      "internationalShipping": "",
      "primeShipping": "",
      "expressShipping": ""
    },
    "image_urls": [
      "https://media.falabella.com.pe/falabellaPE/143420092_01/public"
    ],
    "is_best_seller": false,
    "is_frequent_product": false,
    "multipurpose_badges_count": 0
  }'
```

Respuesta real observada:

```json
{
  "data": {
    "predicted_current_price": 37.16,
    "currency": "PEN",
    "model_name": "cb_leakfree_title_tfidf_deeper",
    "model_version": "20260312-014817",
    "target": "current_price",
    "features_version": "v1",
    "warnings": []
  }
}
```

### Ejemplo 3: `ropa mujeres`

Origen real:

- `sku_id=151378846`
- `query=ropa mujeres`
- `observed_current_price=139.90`

```bash
curl -X POST http://127.0.0.1:5000/api/v1/predictions/current-price \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "ropa mujeres",
    "page_number": 50,
    "position": 48,
    "title": "Vestido con Lazo Catania Guinda",
    "brand": "GENERICO",
    "seller": "Bhuki",
    "seller_id": "SC36181",
    "source_domain": "www.falabella.com.pe",
    "rating": null,
    "review_count": null,
    "sponsored": false,
    "gsc_category_id": "G08020602",
    "provider_name": null,
    "availability": {
      "homeDeliveryShipping": "",
      "pickUpFromStoreShipping": "",
      "internationalShipping": "",
      "primeShipping": "",
      "expressShipping": ""
    },
    "image_urls": [
      "https://media.falabella.com.pe/falabellaPE/151378846_01/public",
      "https://media.falabella.com.pe/falabellaPE/151378846_02/public",
      "https://media.falabella.com.pe/falabellaPE/151378846_03/public"
    ],
    "is_best_seller": false,
    "is_frequent_product": false,
    "multipurpose_badges_count": 0
  }'
```

Respuesta real observada:

```json
{
  "data": {
    "predicted_current_price": 141.23,
    "currency": "PEN",
    "model_name": "cb_leakfree_title_tfidf_deeper",
    "model_version": "20260312-014817",
    "target": "current_price",
    "features_version": "v1",
    "warnings": []
  }
}
```

## Ejemplo desde Python

```python
import requests

payload = {
    "query": "ropa mujeres",
    "page_number": 50,
    "position": 48,
    "title": "Vestido con Lazo Catania Guinda",
    "brand": "GENERICO",
    "seller": "Bhuki",
    "seller_id": "SC36181",
    "source_domain": "www.falabella.com.pe",
    "rating": None,
    "review_count": None,
    "sponsored": False,
    "gsc_category_id": "G08020602",
    "provider_name": None,
    "availability": {
        "homeDeliveryShipping": "",
        "pickUpFromStoreShipping": "",
        "internationalShipping": "",
        "primeShipping": "",
        "expressShipping": "",
    },
    "image_urls": [
        "https://media.falabella.com.pe/falabellaPE/151378846_01/public",
        "https://media.falabella.com.pe/falabellaPE/151378846_02/public",
        "https://media.falabella.com.pe/falabellaPE/151378846_03/public",
    ],
    "is_best_seller": False,
    "is_frequent_product": False,
    "multipurpose_badges_count": 0,
}

response = requests.post(
    "http://127.0.0.1:5000/api/v1/predictions/current-price",
    json=payload,
    timeout=30,
)
response.raise_for_status()
print(response.json())
```

## Errores comunes

### `503 Service Unavailable`

Causa habitual:

- `CURRENT_PRICE_MODEL_DIR` no apunta a un bundle valido.
- Faltan archivos como `model.cbm`, `title_vectorizer.pkl`, `title_svd.pkl`, `metadata.json` o `feature_contract.json`.

Check rapido:

```bash
ls instance/models/current_price/dev
```

### `422 Validation failed`

Causa habitual:

- Falta alguno de los campos obligatorios.
- `page_number` o `position` no son enteros positivos.
- `query` o `title` llegan vacios.

### Predicciones con menor calidad

Señales que degradan la calidad:

- omitir `brand`
- omitir `seller`
- no enviar `gsc_category_id`
- no enviar `image_urls`

La API responde esos casos, pero puede agregar `warnings` y perder precision.
