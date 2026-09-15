"""API HTTP sobre el motor.

Su única razón de existir es el etiquetado gramatical: spaCy es Python y el
navegador no puede correrlo. Todo lo demás —columnas, pesos, generación,
curaduría— puede vivir del lado del cliente una vez que los tokens están
etiquetados (ver ADR-0001).

Por eso la API es deliberadamente chica: etiquetar, repartir, generar.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..engine import generate, round_robin, to_fragments, tokenize
from ..engine.columns import by_pos
from ..engine.serialization import (
    column_from_dict,
    column_to_dict,
    generation_to_dict,
    token_from_dict,
    token_to_dict,
)
from ..tagging import MODELS, USEFUL_POS, TaggerUnavailable, available_languages, tag

WEB_DIR = Path(__file__).resolve().parents[3] / "web"

app = FastAPI(
    title="Verbasizer",
    description="Cut-up por columnas, con peso y restricción gramatical.",
    version="0.1.0",
)


# --------------------------------------------------------------------------
# Modelos de entrada
# --------------------------------------------------------------------------


class TagRequest(BaseModel):
    text: str = Field(min_length=1)
    source: str = "fuente"
    lang: str | None = Field(
        default=None,
        description="'es' o 'en'. Si es None, se tokeniza sin etiquetar.",
    )
    keep_punctuation: bool = True


class DistributeRequest(BaseModel):
    tokens: list[dict[str, Any]]
    unit: int = Field(default=1, ge=1)
    mode: Literal["round_robin", "by_pos"] = "round_robin"
    columns: int = Field(default=5, ge=1, le=50)
    categories: list[str] = Field(default_factory=lambda: ["NOUN", "VERB", "ADJ"])


class GenerateRequest(BaseModel):
    columns: list[dict[str, Any]]
    rule: list[int] | None = None
    lines: int = Field(default=8, ge=1, le=500)
    words_per_line: int = Field(default=6, ge=1, le=50)
    seed: int | None = None
    avoid_repeats: bool = True


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Estado del servicio y qué modelos de idioma están realmente instalados."""
    return {
        "status": "ok",
        "languages": available_languages(),
        "models": MODELS,
        "useful_pos": USEFUL_POS,
    }


@app.post("/api/tag")
def tag_text(request: TagRequest) -> dict[str, Any]:
    """Tokeniza un texto, con etiquetado gramatical si se pide un idioma.

    Es el único paso que necesita el servidor. Una vez hecho, la sesión puede
    trabajar sin backend.
    """
    if request.lang is None:
        tokens = tokenize(
            request.text,
            source=request.source,
            keep_punctuation=request.keep_punctuation,
        )
    else:
        try:
            tokens = tag(
                request.text,
                source=request.source,
                lang=request.lang,
                keep_punctuation=request.keep_punctuation,
            )
        except TaggerUnavailable as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not tokens:
        raise HTTPException(status_code=422, detail="El texto no tiene palabras utilizables.")

    return {
        "source": request.source,
        "lang": request.lang,
        "tokens": [token_to_dict(t) for t in tokens],
    }


@app.post("/api/distribute")
def distribute(request: DistributeRequest) -> dict[str, Any]:
    """Reparte tokens en columnas, uno a uno o por categoría gramatical."""
    try:
        tokens = [token_from_dict(t) for t in request.tokens]
    except (KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"Token mal formado: {exc}") from exc

    if not tokens:
        raise HTTPException(status_code=422, detail="No mandaste tokens.")

    fragments = to_fragments(tokens, unit=request.unit)

    if request.mode == "by_pos":
        if not any(t.pos for t in tokens):
            raise HTTPException(
                status_code=422,
                detail="Los tokens no están etiquetados: pedí /api/tag con un idioma primero.",
            )
        columns = by_pos(fragments, request.categories)
    else:
        if len(fragments) < request.columns:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Hay {len(fragments)} fragmentos para {request.columns} columnas. "
                    "Cargá más texto o pedí menos columnas."
                ),
            )
        columns = round_robin(fragments, request.columns)

    return {"columns": [column_to_dict(c) for c in columns]}


@app.post("/api/generate")
def generate_lines(request: GenerateRequest) -> dict[str, Any]:
    """Genera una tirada. Devuelve la procedencia de cada fragmento."""
    try:
        columns = [column_from_dict(c) for c in request.columns]
    except (KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"Columna mal formada: {exc}") from exc

    try:
        result = generate(
            columns,
            rule=request.rule,
            lines=request.lines,
            words_per_line=request.words_per_line,
            seed=request.seed,
            avoid_repeats=request.avoid_repeats,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return generation_to_dict(result)


# La interfaz se sirve desde acá cuando exista (fase 3).
if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
