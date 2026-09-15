"""Etiquetado gramatical con spaCy.

Esto vive **fuera** del motor a propósito: el motor es Python puro y no debe
depender de spaCy. Acá se produce lo que el motor consume, tokens con su
categoría gramatical (UPOS), y nada más.

Idioma explícito, no autodetectado. Detectar idioma necesita otra dependencia y
se equivoca con textos cortos, que es exactamente lo que se carga en una sesión
de cut-up.

Modelos `sm`: los `md` y `lg` solo agregan vectores de palabra, que este proyecto
no usa.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from .engine.tokenizer import split_lines, strip_punctuation
from .engine.tokens import Token

if TYPE_CHECKING:  # pragma: no cover
    from spacy.language import Language

MODELS = {
    "es": "es_core_news_sm",
    "en": "en_core_web_sm",
}

# Componentes que no usamos. Sacarlos baja la carga y el consumo de memoria.
_EXCLUDE = ["parser", "ner", "senter", "lemmatizer"]


class TaggerUnavailable(RuntimeError):
    """spaCy no está instalado, o falta el modelo del idioma pedido."""


@lru_cache(maxsize=4)
def load_model(lang: str) -> Language:
    """Carga el modelo de un idioma. Se cachea: cargarlo cuesta ~0,2 s."""
    if lang not in MODELS:
        raise TaggerUnavailable(
            f"Idioma no soportado: {lang!r}. Disponibles: {', '.join(sorted(MODELS))}"
        )

    try:
        import spacy
    except ImportError as exc:  # pragma: no cover
        raise TaggerUnavailable(
            "spaCy no está instalado. Instalá el extra: pip install -e \".[server]\""
        ) from exc

    name = MODELS[lang]
    try:
        return spacy.load(name, exclude=_EXCLUDE)
    except OSError as exc:
        raise TaggerUnavailable(
            f"Falta el modelo {name}. Instalalo con:\n"
            f"    python -m spacy download {name}"
        ) from exc


def tag(
    text: str,
    source: str,
    lang: str,
    *,
    keep_punctuation: bool = True,
) -> list[Token]:
    """Tokeniza y etiqueta un texto.

    Sustituye a `engine.tokenizer.tokenize` cuando hay etiquetador disponible.
    El corte en frases lo sigue haciendo el motor, para que los índices de línea
    coincidan con los de una sesión sin etiquetar.

    spaCy separa la puntuación en tokens propios; acá se vuelve a pegar al token
    anterior, para respetar la decisión de ADR-0002 de preservarla.
    """
    nlp = load_model(lang)
    lines = split_lines(text)

    tokens: list[Token] = []
    for line_index, doc in enumerate(nlp.pipe(lines)):
        position = 0
        pending: list[Token] = []

        for spacy_token in doc:
            if spacy_token.is_space:
                continue

            if spacy_token.is_punct:
                if keep_punctuation and pending:
                    # Se pega al token anterior en lugar de ocupar una posición.
                    previous = pending[-1]
                    pending[-1] = Token(
                        text=previous.text + spacy_token.text,
                        source=previous.source,
                        line=previous.line,
                        position=previous.position,
                        pos=previous.pos,
                    )
                continue

            word = spacy_token.text if keep_punctuation else strip_punctuation(
                spacy_token.text
            )
            if not word:
                continue

            pending.append(
                Token(
                    text=word,
                    source=source,
                    line=line_index,
                    position=position,
                    pos=spacy_token.pos_,
                )
            )
            position += 1

        tokens.extend(pending)

    return tokens


def available_languages() -> dict[str, bool]:
    """Qué idiomas tienen su modelo efectivamente instalado."""
    status: dict[str, bool] = {}
    for lang in MODELS:
        try:
            load_model(lang)
            status[lang] = True
        except TaggerUnavailable:
            status[lang] = False
    return status


# Categorías UPOS que tienen sentido como columna. El resto (DET, ADP, PUNCT,
# SYM…) sirve de relleno gramatical pero no aporta gran cosa como restricción.
USEFUL_POS = ["NOUN", "VERB", "ADJ", "ADV", "PROPN", "PRON", "NUM", "INTJ"]
