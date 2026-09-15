"""API HTTP. Requiere el extra `server`:

    pip install -e ".[server]"
    python -m spacy download es_core_news_sm
    python -m spacy download en_core_web_sm

Para levantarla:

    uvicorn verbasizer.api.app:app --reload
"""

from __future__ import annotations

__all__ = ["app"]


def __getattr__(name: str):
    # Import perezoso: importar este paquete no debe exigir FastAPI instalado.
    if name == "app":
        from .app import app

        return app
    raise AttributeError(name)
