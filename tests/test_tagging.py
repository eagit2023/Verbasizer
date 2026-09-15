"""Tests del etiquetado gramatical.

Se saltean solos si spaCy o los modelos no están instalados: el motor tiene que
poder testearse sin nada de eso.
"""

from __future__ import annotations

import pytest

spacy = pytest.importorskip("spacy", reason="spaCy no instalado")

from verbasizer.tagging import (  # noqa: E402
    MODELS,
    TaggerUnavailable,
    load_model,
    tag,
)


def _tiene_modelo(lang: str) -> bool:
    try:
        load_model(lang)
        return True
    except TaggerUnavailable:
        return False


necesita_es = pytest.mark.skipif(
    not _tiene_modelo("es"), reason=f"falta {MODELS['es']}"
)
necesita_en = pytest.mark.skipif(
    not _tiene_modelo("en"), reason=f"falta {MODELS['en']}"
)


def test_idioma_desconocido_es_error():
    with pytest.raises(TaggerUnavailable, match="Idioma no soportado"):
        load_model("fr")


@necesita_es
def test_etiqueta_castellano():
    tokens = tag("El cielo sobre el puerto tenía un color extraño.", "x", "es")
    por_texto = {t.text: t.pos for t in tokens}
    assert por_texto["cielo"] == "NOUN"
    assert por_texto["tenía"] == "VERB"
    assert por_texto["extraño."] == "ADJ"


@necesita_en
def test_etiqueta_ingles():
    tokens = tag("The sky above the port was grey.", "x", "en")
    por_texto = {t.text: t.pos for t in tokens}
    assert por_texto["sky"] == "NOUN"
    assert por_texto["grey."] == "ADJ"


@necesita_es
def test_la_puntuacion_se_pega_al_token_anterior():
    tokens = tag("una por una, sin ruido.", "x", "es")
    textos = [t.text for t in tokens]
    assert "una," in textos
    assert "ruido." in textos
    # La puntuación no ocupa posición propia.
    assert all(t.text not in {",", "."} for t in tokens)


@necesita_es
def test_puede_descartar_la_puntuacion():
    tokens = tag("una por una, sin ruido.", "x", "es", keep_punctuation=False)
    textos = [t.text for t in tokens]
    assert "una" in textos
    assert "una," not in textos


@necesita_es
def test_los_indices_de_linea_coinciden_con_el_tokenizador_del_motor():
    from verbasizer.engine.tokenizer import tokenize

    texto = "Primera frase corta. Segunda frase.\nTercera en otra línea."
    etiquetados = tag(texto, "x", "es")
    planos = tokenize(texto, "x")
    assert max(t.line for t in etiquetados) == max(t.line for t in planos)


@necesita_es
def test_la_procedencia_se_conserva():
    tokens = tag("El cielo estaba gris.", "diario", "es")
    assert all(t.source == "diario" for t in tokens)
    assert [t.position for t in tokens] == list(range(len(tokens)))
