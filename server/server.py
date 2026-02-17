#!/usr/bin/env python3
"""
Serafis Evaluation Framework Server — entrypoint for uvicorn server.server:app.

For uvicorn server:app use server/__init__.py (exposes app from server.app).
"""

try:
    from .app import app
except ImportError:
    from app import app

if __name__ == "__main__":
    import uvicorn
    try:
        from .config import get_config
    except ImportError:
        from config import get_config
    config = get_config()
    uvicorn.run(app, host=config.host, port=config.port)
