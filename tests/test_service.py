"""Tests del módulo de servicio: el contrato entre la interfaz y el motor.

Reemplazan a los de la API HTTP, que ya no existe. Prueban lo mismo —entradas
JSON, errores con mensaje para el usuario, procedencia en la salida— sin
transporte de por medio.
"""

from __future__ import annotations

import pytest

from verbasizer import service
from verbasizer.service import ServiceError

TEXTO = "El cielo sobre el puerto tenía el color de una pantalla apagada. Nadie recordaba la calle."


def _tiene_modelo(lang: str) -> bool:
    try:
        from verbasizer.tagging import TaggerUnavailable, load_model
    except ImportError:
        return False
    try:
        load_model(lang)
        return True
    except (TaggerUnavailable, ImportError):
        return False


necesita_es = pytest.mark.skipif(not _tiene_modelo("es"), reason="falta el modelo es")


def _tokens(texto: str = TEXTO, lang: str | None = None) -> list[dict]:
    return service.tag_text(texto, source="x", lang=lang)["tokens"]


def _columnas(n: int = 4) -> list[dict]:
    return service.distribute(_tokens(), columns=n)["columns"]


# ---------- health ----------


def test_health_informa_idiomas_y_limite():
    data = service.health()
    assert data["status"] == "ok"
    assert set(data["languages"]) == {"es", "en"}
    assert "NOUN" in data["useful_pos"]
    assert data["max_text_bytes"] == 2 * 1024 * 1024


# ---------- tag ----------


def test_tag_sin_idioma_tokeniza_sin_etiquetar():
    tokens = _tokens()
    assert tokens
    assert all(t["pos"] is None for t in tokens)
    assert all(t["source"] == "x" for t in tokens)


def test_tag_texto_vacio_es_error():
    with pytest.raises(ServiceError, match="No hay texto"):
        service.tag_text("   ", source="x")


def test_tag_texto_sin_palabras_es_error():
    with pytest.raises(ServiceError, match="utilizables"):
        service.tag_text("...", source="x")


def test_tag_por_encima_del_limite_es_error(monkeypatch):
    monkeypatch.setattr(service, "MAX_TEXT_BYTES", 500)
    with pytest.raises(ServiceError, match="máximo"):
        service.tag_text("palabra " * 200, source="x")


def test_el_limite_cuenta_bytes_no_caracteres(monkeypatch):
    # 40 caracteres con tilde pesan 80 bytes en UTF-8.
    monkeypatch.setattr(service, "MAX_TEXT_BYTES", 45)
    with pytest.raises(ServiceError):
        service.tag_text("á" * 40, source="x")


def test_idioma_desconocido_es_error_legible():
    pytest.importorskip("spacy")
    with pytest.raises(ServiceError, match="Idioma no soportado"):
        service.tag_text(TEXTO, source="x", lang="fr")


@necesita_es
def test_tag_con_idioma_etiqueta():
    assert any(t["pos"] == "NOUN" for t in _tokens(lang="es"))


# ---------- distribute ----------


def test_distribute_uno_a_uno():
    tokens = _tokens()
    columnas = service.distribute(tokens, columns=4)["columns"]
    assert len(columnas) == 4
    assert sum(len(c["fragments"]) for c in columnas) == len(tokens)


def test_distribute_respeta_la_unidad():
    columnas = service.distribute(_tokens(), columns=2, unit=3)["columns"]
    fragmentos = [f for c in columnas for f in c["fragments"]]
    assert any(len(f) == 3 for f in fragmentos)


def test_distribute_sin_tokens_es_error():
    with pytest.raises(ServiceError, match="cargá una fuente"):
        service.distribute([])


def test_distribute_por_categoria_sin_etiquetar_avisa():
    with pytest.raises(ServiceError, match="no están etiquetadas"):
        service.distribute(_tokens(), mode="by_pos")


def test_distribute_con_mas_columnas_que_fragmentos_avisa():
    with pytest.raises(ServiceError, match="fragmentos"):
        service.distribute(_tokens("dos palabras"), columns=30)


def test_distribute_fuera_de_rango_es_error():
    with pytest.raises(ServiceError, match="Columnas"):
        service.distribute(_tokens(), columns=0)
    with pytest.raises(ServiceError, match="Unidad"):
        service.distribute(_tokens(), unit=0)


def test_distribute_modo_desconocido_es_error():
    with pytest.raises(ServiceError, match="Modo"):
        service.distribute(_tokens(), mode="al_reves")


def test_distribute_token_mal_formado_es_error():
    with pytest.raises(ServiceError, match="mal formado"):
        service.distribute([{"sin": "texto"}])


@necesita_es
def test_distribute_por_categoria():
    columnas = service.distribute(
        _tokens(lang="es"), mode="by_pos", categories=["NOUN", "VERB"]
    )["columns"]
    assert [c["name"] for c in columnas] == ["NOUN", "VERB"]
    assert columnas[0]["pos_filter"] == "NOUN"


# ---------- generate ----------


def test_generate_devuelve_procedencia():
    data = service.generate_lines(_columnas(), lines=3, words_per_line=4, seed=9)
    assert data["seed"] == 9
    assert len(data["lines"]) == 3
    for line in data["lines"]:
        assert line["text"]
        assert len(line["placements"]) == 4
        for placement in line["placements"]:
            assert placement["column"].startswith("col")
            assert placement["source"] == "x"


def test_generate_es_reproducible():
    columnas = _columnas()
    a = service.generate_lines(columnas, seed=55)
    b = service.generate_lines(columnas, seed=55)
    assert [l["text"] for l in a["lines"]] == [l["text"] for l in b["lines"]]


def test_generate_respeta_la_regla():
    data = service.generate_lines(_columnas(), rule=[2, 5], lines=4, seed=1)
    assert [len(l["placements"]) for l in data["lines"]] == [2, 5, 2, 5]


def test_generate_regla_invalida_es_error():
    with pytest.raises(ServiceError, match="regla"):
        service.generate_lines(_columnas(), rule=[2, 0])


def test_generate_fuera_de_rango_es_error():
    with pytest.raises(ServiceError, match="Líneas"):
        service.generate_lines(_columnas(), lines=0)


def test_generate_sin_columnas_utilizables_es_error():
    columnas = _columnas(2)
    for c in columnas:
        c["weight"] = 0
    with pytest.raises(ServiceError, match="Ninguna columna"):
        service.generate_lines(columnas, seed=1)


def test_generate_columna_mal_formada_es_error():
    with pytest.raises(ServiceError, match="mal formada"):
        service.generate_lines([{"sin": "nombre"}])


# ---------- regenerate ----------


def test_regenerate_preserva_lo_bloqueado():
    columnas = _columnas(4)
    previa = service.generate_lines(columnas, lines=3, words_per_line=4, seed=10)
    nueva = service.regenerate_lines(columnas, previa, locked=[[0, 0], [1, 2]], seed=20)
    assert nueva["lines"][0]["placements"][0]["text"] == previa["lines"][0]["placements"][0]["text"]
    assert nueva["lines"][1]["placements"][2]["text"] == previa["lines"][1]["placements"][2]["text"]


def test_regenerate_cambia_el_resto():
    columnas = _columnas(4)
    previa = service.generate_lines(columnas, lines=3, words_per_line=5, seed=10)
    nueva = service.regenerate_lines(columnas, previa, locked=[[0, 0]], seed=33)
    assert [l["text"] for l in previa["lines"]] != [l["text"] for l in nueva["lines"]]


def test_regenerate_entrada_mal_formada_es_error():
    with pytest.raises(ServiceError, match="mal formada"):
        service.regenerate_lines(_columnas(2), {"sin": "seed"}, locked=[])
