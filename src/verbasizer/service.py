"""Operaciones de la aplicación, independientes de cómo se las llame.

Antes vivían dentro de los endpoints de FastAPI. Ahora la aplicación de
escritorio las llama directo desde la interfaz a través del puente de
pywebview, sin HTTP. Este módulo es ese contrato: recibe y devuelve estructuras
JSON simples (dict, list, str, int), que es lo único que el puente sabe pasar.

Los errores pensados para el usuario salen como `ServiceError`, con un mensaje
en castellano listo para mostrar. El puente los convierte en una Promise
rechazada del lado de JavaScript.
"""

from __future__ import annotations

from typing import Any

from .engine import generate, regenerate, round_robin, to_fragments, tokenize
from .engine.columns import by_pos
from .engine.serialization import (
    column_from_dict,
    column_to_dict,
    generation_from_dict,
    generation_to_dict,
    token_from_dict,
    token_to_dict,
)
from .tagging import MODELS, USEFUL_POS, TaggerUnavailable, available_languages, tag

# Medido: un texto de 2 MB tarda ~12 s en etiquetarse y produce ~28 MB de datos
# que la interfaz tiene que dibujar. Aunque ya no hay servidor que proteger, el
# límite evita que alguien congele la aplicación pegando un libro entero. Un
# texto de trabajo típico ronda los 20 KB.
MAX_TEXT_BYTES = 2 * 1024 * 1024

LIMITS = {
    "columns": (1, 50),
    "lines": (1, 500),
    "words_per_line": (1, 50),
    "unit": (1, 50),
}


class ServiceError(ValueError):
    """Error con un mensaje apto para mostrarle al usuario tal cual."""


def _check_range(name: str, value: int | None, label: str) -> None:
    if value is None:
        return
    low, high = LIMITS[name]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ServiceError(f"{label}: tiene que ser un número entero.")
    if not low <= value <= high:
        raise ServiceError(f"{label}: tiene que estar entre {low} y {high}.")


def _check_rule(rule: list[int] | None) -> None:
    if rule is None:
        return
    if not rule or not all(isinstance(n, int) and n >= 1 for n in rule):
        raise ServiceError("La regla tiene que ser una lista de enteros mayores a cero.")


# ---------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------


def health() -> dict[str, Any]:
    """Qué modelos de idioma están realmente disponibles."""
    return {
        "status": "ok",
        "languages": available_languages(),
        "models": MODELS,
        "useful_pos": USEFUL_POS,
        "max_text_bytes": MAX_TEXT_BYTES,
    }


# ---------------------------------------------------------------------------
# Operaciones
# ---------------------------------------------------------------------------


def tag_text(
    text: str,
    source: str = "fuente",
    lang: str | None = None,
    keep_punctuation: bool = True,
) -> dict[str, Any]:
    """Tokeniza un texto, con etiquetado gramatical si se pide un idioma."""
    if not isinstance(text, str) or not text.strip():
        raise ServiceError("No hay texto para procesar.")

    size = len(text.encode("utf-8"))
    if size > MAX_TEXT_BYTES:
        raise ServiceError(
            f"El texto pesa {size / 1_048_576:.1f} MB y el máximo es "
            f"{MAX_TEXT_BYTES / 1_048_576:.0f} MB. Cargalo por partes."
        )

    if lang:
        try:
            tokens = tag(text, source=source, lang=lang, keep_punctuation=keep_punctuation)
        except TaggerUnavailable as exc:
            raise ServiceError(str(exc)) from exc
    else:
        tokens = tokenize(text, source=source, keep_punctuation=keep_punctuation)

    if not tokens:
        raise ServiceError("El texto no tiene palabras utilizables.")

    return {
        "source": source,
        "lang": lang or None,
        "tokens": [token_to_dict(t) for t in tokens],
    }


def distribute(
    tokens: list[dict[str, Any]],
    unit: int = 1,
    mode: str = "round_robin",
    columns: int = 5,
    categories: list[str] | None = None,
) -> dict[str, Any]:
    """Reparte tokens en columnas, uno a uno o por categoría gramatical."""
    _check_range("unit", unit, "Unidad")
    _check_range("columns", columns, "Columnas")
    if mode not in ("round_robin", "by_pos"):
        raise ServiceError(f"Modo de reparto desconocido: {mode!r}.")

    try:
        parsed = [token_from_dict(t) for t in tokens or []]
    except (KeyError, TypeError) as exc:
        raise ServiceError(f"Token mal formado: {exc}") from exc

    if not parsed:
        raise ServiceError("No hay palabras para repartir: cargá una fuente primero.")

    fragments = to_fragments(parsed, unit=unit)

    if mode == "by_pos":
        if not any(t.pos for t in parsed):
            raise ServiceError(
                "Las fuentes no están etiquetadas: cargalas eligiendo un idioma."
            )
        cats = [c.strip().upper() for c in (categories or ["NOUN", "VERB", "ADJ"]) if c.strip()]
        if not cats:
            raise ServiceError("Indicá al menos una categoría gramatical.")
        result = by_pos(fragments, cats)
    else:
        if len(fragments) < columns:
            raise ServiceError(
                f"Hay {len(fragments)} fragmentos para {columns} columnas. "
                "Cargá más texto o pedí menos columnas."
            )
        result = round_robin(fragments, columns)

    return {"columns": [column_to_dict(c) for c in result]}


def generate_lines(
    columns: list[dict[str, Any]],
    rule: list[int] | None = None,
    lines: int = 8,
    words_per_line: int = 6,
    seed: int | None = None,
    avoid_repeats: bool = True,
) -> dict[str, Any]:
    """Genera una tirada, con la procedencia de cada fragmento."""
    _check_range("lines", lines, "Líneas")
    _check_range("words_per_line", words_per_line, "Largo")
    _check_rule(rule)

    try:
        parsed = [column_from_dict(c) for c in columns or []]
    except (KeyError, TypeError, ValueError) as exc:
        raise ServiceError(f"Columna mal formada: {exc}") from exc

    try:
        result = generate(
            parsed,
            rule=rule,
            lines=lines,
            words_per_line=words_per_line,
            seed=seed,
            avoid_repeats=avoid_repeats,
        )
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc

    return generation_to_dict(result)


def regenerate_lines(
    columns: list[dict[str, Any]],
    previous: dict[str, Any],
    locked: list[list[int]] | None = None,
    rule: list[int] | None = None,
    lines: int | None = None,
    seed: int | None = None,
    avoid_repeats: bool = True,
) -> dict[str, Any]:
    """Vuelve a tirar preservando las posiciones bloqueadas."""
    _check_range("lines", lines, "Líneas")
    _check_rule(rule)

    try:
        parsed = [column_from_dict(c) for c in columns or []]
        prev = generation_from_dict(previous)
        keep = {(int(line), int(pos)) for line, pos in (locked or [])}
    except (KeyError, TypeError, ValueError) as exc:
        raise ServiceError(f"Entrada mal formada: {exc}") from exc

    try:
        result = regenerate(
            parsed,
            prev,
            keep,
            rule=rule,
            lines=lines,
            seed=seed,
            avoid_repeats=avoid_repeats,
        )
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc

    return generation_to_dict(result)
