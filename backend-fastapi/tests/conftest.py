"""Test env is configured BEFORE app modules import (engine binds at import).

The SQLite file lives in the system temp dir (mounted/synced folders can fail
SQLite locking).

Mirrors ListManagerApp's suite layout: file-based SQLite, fresh schema per
test, TestClient fixture.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:////tmp/splitrail_test.db"
os.environ["RUN_MIGRATIONS"] = "false"
os.environ["ANTHROPIC_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("error", request=None, response=None)
