from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

os.environ["APP_DATABASE_URL"] = f"sqlite:///./test_livestock_monitor_{uuid.uuid4().hex}.db"

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.services.seed import seed_database


@pytest.fixture()
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()
