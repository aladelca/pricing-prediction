"""create scrape tables

Revision ID: 20260310_01
Revises:
Create Date: 2026-03-10 01:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260310_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("query", sa.String(length=255), nullable=False),
        sa.Column("requested_pages", sa.Integer(), nullable=False),
        sa.Column("scraped_pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scraped_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "products",
        sa.Column("sku_id", sa.String(length=64), primary_key=True),
        sa.Column("product_id", sa.String(length=64), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("source_domain", sa.String(length=255), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("seller", sa.String(length=255), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
    )

    op.create_table(
        "product_images",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("sku_id", sa.String(length=64), sa.ForeignKey("products.sku_id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.UniqueConstraint("sku_id", "position", "image_url"),
    )

    op.create_table(
        "product_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("scrape_runs.id"), nullable=False),
        sa.Column("sku_id", sa.String(length=64), sa.ForeignKey("products.sku_id"), nullable=False),
        sa.Column("query", sa.String(length=255), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("product_url", sa.Text(), nullable=False),
        sa.Column("current_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("current_price_text", sa.String(length=255), nullable=True),
        sa.Column("original_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("original_price_text", sa.String(length=255), nullable=True),
        sa.Column("discount_text", sa.String(length=64), nullable=True),
        sa.Column("rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=True),
        sa.Column("seller", sa.String(length=255), nullable=True),
        sa.Column("sponsored", sa.Boolean(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("raw_prices", sa.JSON(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "page_number", "position", "sku_id"),
    )


def downgrade() -> None:
    op.drop_table("product_snapshots")
    op.drop_table("product_images")
    op.drop_table("products")
    op.drop_table("scrape_runs")
