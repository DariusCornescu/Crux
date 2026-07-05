"""Drift guard (same idea as ListManagerApp): models and migrations must agree.
Fails whenever someone edits app/models.py without generating a migration."""


def test_models_match_migrations(tmp_path):
    from alembic import command
    from alembic.config import Config
    from alembic.autogenerate import compare_metadata
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine

    from app.database import Base

    url = f"sqlite:///{tmp_path}/migration_check.db"
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")

    engine = create_engine(url)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"render_as_batch": True})
        diff = compare_metadata(ctx, Base.metadata)

    assert diff == [], f"models diverge from migrations: {diff}"
