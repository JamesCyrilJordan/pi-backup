import logging
import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import api_router
from .views import view_router, templates
from .backup.config import get_config_dir, ensure_default_config
from .backup.engine import LOG_DIR, configure_logging


configure_logging()
ensure_default_config()

app = FastAPI(title="Pi Backup Manager", version="1.0.0")

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(view_router)
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
async def startup_event() -> None:
    logging.getLogger(__name__).info("Pi Backup Manager started. Config dir: %s", get_config_dir())
    LOG_DIR.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("PI_BACKUP_HOST", "0.0.0.0")
    port = int(os.environ.get("PI_BACKUP_PORT", "8080"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
