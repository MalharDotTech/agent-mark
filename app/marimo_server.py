"""Marimo dashboard server integration."""
import marimo
from pathlib import Path
from typing import Any
from .core.logging import get_logger

logger = get_logger(__name__)


def create_marimo_server() -> Any:
    """Create marimo ASGI server with all dashboard notebooks."""
    notebooks_dir = Path(__file__).parent.parent / "notebooks"
    
    # Create base ASGI app
    server = marimo.create_asgi_app()
    
    # Mount index as root
    index_path = notebooks_dir / "index.py"
    server = server.with_app(path="/", root=str(index_path))
    logger.info(f"Mounted index notebook at root: {index_path}")
    
    # Auto-discover and mount all other dashboard notebooks
    dashboard_count = 0
    for notebook_file in sorted(notebooks_dir.glob("*_dashboard.py")):
        # Remove .py extension for URL path
        app_path = notebook_file.stem
        server = server.with_app(path=f"/{app_path}", root=str(notebook_file))
        logger.info(f"Mounted dashboard: /{app_path} -> {notebook_file.name}")
        dashboard_count += 1
    
    logger.info(f"Marimo server configured with index + {dashboard_count} dashboards")
    return server.build()
