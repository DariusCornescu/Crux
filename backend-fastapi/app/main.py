import os

from fastapi import FastAPI

from app.routers import activities, chat, dashboard, devices, health, integrations, reports, voice_logs


# Schema is managed by Alembic (see backend-fastapi/alembic/). On startup we
# bring the configured database up to the latest revision — fresh database
# applies all migrations, current database is a no-op. Same pattern as
# ListManagerApp. Disable with RUN_MIGRATIONS=false (tests manage their own DB).
def _run_migrations_to_head() -> None:
    from alembic import command
    from alembic.config import Config

    from app.database import DATABASE_URL

    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_cfg = Config(os.path.join(backend_root, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(backend_root, "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(alembic_cfg, "head")


if os.getenv("RUN_MIGRATIONS", "true").lower() != "false":
    _run_migrations_to_head()

app = FastAPI(title="Splitrail API", version="0.2.0")

app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(activities.router)
app.include_router(reports.router)
app.include_router(chat.router)
app.include_router(integrations.router)
app.include_router(devices.router)
app.include_router(voice_logs.router)
