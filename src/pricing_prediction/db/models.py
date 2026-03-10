from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import UniqueConstraint

from pricing_prediction.extensions import db


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_uuid() -> str:
    return str(uuid4())


def decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


class ScrapeRun(db.Model):
    __tablename__ = "scrape_runs"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    source = db.Column(db.String(64), nullable=False)
    query = db.Column(db.String(255), nullable=False)
    requested_pages = db.Column(db.Integer, nullable=False)
    scraped_pages = db.Column(db.Integer, nullable=False, default=0)
    scraped_items = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(64), nullable=False, default="queued")
    error_message = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    snapshots = db.relationship("ProductSnapshot", back_populates="run", lazy="selectin")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "query": self.query,
            "requested_pages": self.requested_pages,
            "scraped_pages": self.scraped_pages,
            "scraped_items": self.scraped_items,
            "status": self.status,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Product(db.Model):
    __tablename__ = "products"

    sku_id = db.Column(db.String(64), primary_key=True)
    product_id = db.Column(db.String(64), nullable=False)
    canonical_url = db.Column(db.Text, nullable=False)
    source_domain = db.Column(db.String(255), nullable=False)
    brand = db.Column(db.String(255), nullable=True)
    title = db.Column(db.Text, nullable=False)
    seller = db.Column(db.String(255), nullable=True)
    first_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    raw_payload = db.Column(db.JSON, nullable=False)

    images = db.relationship(
        "ProductImage",
        back_populates="product",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="ProductImage.position.asc()",
    )
    snapshots = db.relationship("ProductSnapshot", back_populates="product", lazy="selectin")

    def to_dict(self) -> dict[str, Any]:
        return {
            "sku_id": self.sku_id,
            "product_id": self.product_id,
            "canonical_url": self.canonical_url,
            "source_domain": self.source_domain,
            "brand": self.brand,
            "title": self.title,
            "seller": self.seller,
            "image_urls": [image.image_url for image in self.images],
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }


class ProductImage(db.Model):
    __tablename__ = "product_images"
    __table_args__ = (UniqueConstraint("sku_id", "position", "image_url"),)

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    sku_id = db.Column(db.String(64), db.ForeignKey("products.sku_id"), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.Text, nullable=False)

    product = db.relationship("Product", back_populates="images")


class ProductSnapshot(db.Model):
    __tablename__ = "product_snapshots"
    __table_args__ = (UniqueConstraint("run_id", "page_number", "position", "sku_id"),)

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    run_id = db.Column(db.String(36), db.ForeignKey("scrape_runs.id"), nullable=False)
    sku_id = db.Column(db.String(64), db.ForeignKey("products.sku_id"), nullable=False)
    query = db.Column(db.String(255), nullable=False)
    page_number = db.Column(db.Integer, nullable=False)
    position = db.Column(db.Integer, nullable=False)
    source_url = db.Column(db.Text, nullable=False)
    product_url = db.Column(db.Text, nullable=False)
    current_price = db.Column(db.Numeric(10, 2), nullable=True)
    current_price_text = db.Column(db.String(255), nullable=True)
    original_price = db.Column(db.Numeric(10, 2), nullable=True)
    original_price_text = db.Column(db.String(255), nullable=True)
    discount_text = db.Column(db.String(64), nullable=True)
    rating = db.Column(db.Numeric(3, 2), nullable=True)
    review_count = db.Column(db.Integer, nullable=True)
    seller = db.Column(db.String(255), nullable=True)
    sponsored = db.Column(db.Boolean, nullable=False, default=False)
    raw_text = db.Column(db.Text, nullable=False)
    raw_prices = db.Column(db.JSON, nullable=False)
    raw_payload = db.Column(db.JSON, nullable=False)
    scraped_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    run = db.relationship("ScrapeRun", back_populates="snapshots")
    product = db.relationship("Product", back_populates="snapshots", lazy="selectin")

    def to_dict(self) -> dict[str, Any]:
        data = {
            "id": self.id,
            "run_id": self.run_id,
            "sku_id": self.sku_id,
            "product_id": self.product.product_id if self.product else None,
            "query": self.query,
            "page_number": self.page_number,
            "position": self.position,
            "source_url": self.source_url,
            "product_url": self.product_url,
            "brand": self.product.brand if self.product else None,
            "title": self.product.title if self.product else None,
            "source_domain": self.product.source_domain if self.product else None,
            "seller": self.seller,
            "image_urls": (
                [image.image_url for image in self.product.images] if self.product else []
            ),
            "current_price": decimal_to_float(self.current_price),
            "current_price_text": self.current_price_text,
            "original_price": decimal_to_float(self.original_price),
            "original_price_text": self.original_price_text,
            "discount_text": self.discount_text,
            "rating": decimal_to_float(self.rating),
            "review_count": self.review_count,
            "sponsored": self.sponsored,
            "raw_text": self.raw_text,
            "raw_prices": self.raw_prices,
            "scraped_at": self.scraped_at.isoformat(),
        }
        return data
