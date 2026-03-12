from __future__ import annotations

from typing import Final

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

TRAINING_DATA_SQL: Final[str] = """
WITH image_agg AS (
    SELECT
        sku_id,
        COUNT(*) AS image_count,
        MAX(CASE WHEN position = 1 THEN image_url END) AS first_image_url
    FROM product_images
    GROUP BY sku_id
)
SELECT
    ps.id,
    ps.sku_id,
    ps.query,
    ps.page_number,
    ps.position,
    CAST(ps.current_price AS FLOAT) AS current_price,
    CAST(ps.rating AS FLOAT) AS rating,
    ps.review_count,
    COALESCE(NULLIF(ps.seller, ''), NULLIF(p.seller, ''), 'unknown') AS seller,
    CASE WHEN ps.sponsored THEN 1 ELSE 0 END AS sponsored,
    COALESCE(NULLIF(p.brand, ''), 'unknown') AS brand,
    p.title,
    p.source_domain,
    ps.raw_payload,
    COALESCE(img.image_count, 0) AS image_count,
    img.first_image_url
FROM product_snapshots ps
JOIN products p ON p.sku_id = ps.sku_id
LEFT JOIN image_agg img ON img.sku_id = ps.sku_id
WHERE ps.current_price IS NOT NULL
ORDER BY ps.scraped_at ASC, ps.page_number ASC, ps.position ASC
"""


def load_current_price_training_source_frame(
    engine: Engine,
    limit: int | None = None,
) -> pd.DataFrame:
    sql = TRAINING_DATA_SQL
    params: dict[str, int] = {}
    if limit is not None:
        sql = f"{sql}\nLIMIT :limit"
        params["limit"] = limit

    with engine.connect() as connection:
        return pd.read_sql_query(text(sql), connection, params=params)
