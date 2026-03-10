from __future__ import annotations

from pathlib import Path

import pytest

from pricing_prediction.app import create_app
from pricing_prediction.extensions import db


@pytest.fixture()
def app(tmp_path: Path):
    import pricing_prediction.db.models  # noqa: F401

    database_path = tmp_path / "test.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "SCRAPER_INLINE_EXECUTION": True,
            "SCRAPER_ENABLE_BROWSER_FALLBACK": False,
            "SCRAPER_DEFAULT_MAX_PAGES": 30,
            "SCRAPER_MAX_ALLOWED_PAGES": 30,
            "SCRAPER_REQUEST_DELAY_MS": 0,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def search_page_1_html() -> str:
    return (Path(__file__).parent / "fixtures" / "falabella" / "search_page_1.html").read_text()


@pytest.fixture()
def search_page_30_html() -> str:
    return (Path(__file__).parent / "fixtures" / "falabella" / "search_page_30.html").read_text()
