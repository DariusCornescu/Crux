"""DigitalOcean App Platform (and Heroku-style) DATABASE_URLs use postgres://
or postgresql:// — SQLAlchemy needs the psycopg3 driver spelled out."""
from app.config import Settings


def test_normalizes_postgres_scheme():
    s = Settings(database_url="postgres://u:p@host:25060/db?sslmode=require")
    assert s.database_url.startswith("postgresql+psycopg://")
    assert s.database_url.endswith("?sslmode=require")


def test_normalizes_postgresql_scheme():
    s = Settings(database_url="postgresql://u:p@host/db")
    assert s.database_url == "postgresql+psycopg://u:p@host/db"


def test_leaves_explicit_driver_and_sqlite_alone():
    assert Settings(database_url="postgresql+psycopg://u@h/db").database_url == "postgresql+psycopg://u@h/db"
    assert Settings(database_url="sqlite:////tmp/x.db").database_url == "sqlite:////tmp/x.db"
