from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pricing_prediction.db.models import Product, ProductImage, ProductSnapshot, ScrapeRun, utcnow
from pricing_prediction.errors import NotFoundError
from pricing_prediction.extensions import db
from pricing_prediction.scraper.falabella.normalize import NormalizedProductRecord


class ScrapeRunRepository:
    def create_run(self, *, source: str, query: str, requested_pages: int) -> ScrapeRun:
        run = ScrapeRun(
            source=source,
            query=query,
            requested_pages=requested_pages,
            status="queued",
        )
        db.session.add(run)
        db.session.commit()
        return run

    def get_run(self, run_id: str) -> ScrapeRun:
        run = db.session.get(ScrapeRun, run_id)
        if run is None:
            raise NotFoundError(f"Scrape run '{run_id}' was not found.")
        return run

    def list_snapshots(
        self, run_id: str, limit: int, offset: int
    ) -> tuple[int, Sequence[ProductSnapshot]]:
        self.get_run(run_id)
        total = db.session.scalar(
            select(func.count())
            .select_from(ProductSnapshot)
            .where(ProductSnapshot.run_id == run_id)
        )
        snapshots = db.session.scalars(
            select(ProductSnapshot)
            .options(
                selectinload(ProductSnapshot.product).selectinload(Product.images),
            )
            .where(ProductSnapshot.run_id == run_id)
            .order_by(ProductSnapshot.page_number.asc(), ProductSnapshot.position.asc())
            .limit(limit)
            .offset(offset)
        ).all()
        return int(total or 0), snapshots

    def persist_page(
        self, *, run_id: str, query: str, items: Sequence[NormalizedProductRecord]
    ) -> int:
        inserted_count = 0
        for item in items:
            product = self._upsert_product(item)
            existing = db.session.scalar(
                select(ProductSnapshot).where(
                    ProductSnapshot.run_id == run_id,
                    ProductSnapshot.page_number == item.page_number,
                    ProductSnapshot.position == item.position,
                    ProductSnapshot.sku_id == item.sku_id,
                )
            )
            if existing is not None:
                continue

            db.session.add(
                ProductSnapshot(
                    run_id=run_id,
                    sku_id=item.sku_id,
                    query=query,
                    page_number=item.page_number,
                    position=item.position,
                    source_url=item.source_url,
                    product_url=item.product_url,
                    current_price=item.current_price,
                    current_price_text=item.current_price_text,
                    original_price=item.original_price,
                    original_price_text=item.original_price_text,
                    discount_text=item.discount_text,
                    rating=item.rating,
                    review_count=item.review_count,
                    seller=item.seller,
                    sponsored=item.sponsored,
                    raw_text=item.raw_text,
                    raw_prices=item.raw_prices,
                    raw_payload=item.raw_payload,
                    scraped_at=item.scraped_at,
                    product=product,
                )
            )
            inserted_count += 1

        db.session.commit()
        return inserted_count

    def commit(self) -> None:
        db.session.commit()

    def rollback(self) -> None:
        db.session.rollback()

    def _upsert_product(self, item: NormalizedProductRecord) -> Product:
        product = db.session.get(Product, item.sku_id)
        desired_images = list(enumerate(item.image_urls, start=1))
        if product is None:
            product = Product(
                sku_id=item.sku_id,
                product_id=item.product_id,
                canonical_url=item.product_url,
                source_domain=item.source_domain,
                brand=item.brand,
                title=item.title,
                seller=item.seller,
                first_seen_at=item.scraped_at,
                last_seen_at=item.scraped_at,
                raw_payload=item.raw_payload,
            )
            db.session.add(product)
        else:
            product.product_id = item.product_id
            product.canonical_url = item.product_url
            product.source_domain = item.source_domain
            product.brand = item.brand
            product.title = item.title
            product.seller = item.seller
            product.last_seen_at = utcnow()
            product.raw_payload = item.raw_payload

        current_images = [(image.position, image.image_url) for image in product.images]
        if current_images != desired_images:
            for image in list(product.images):
                db.session.delete(image)
            db.session.flush()
            for position, image_url in desired_images:
                product.images.append(ProductImage(position=position, image_url=image_url))

        return product
