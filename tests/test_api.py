"""Tests de la API.

Se saltean si FastAPI no está instalado. Los que necesitan modelos de idioma se
saltean aparte.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="FastAPI no instalado")
pytest.importorskip("httpx", reason="httpx no instalado (hace falta para TestClient)")

from fastapi.testclient import TestClient  # noqa: E402

from verbasizer.api.app import app  # noqa: E402

client = TestClient(app)

TEXTO = "El cielo sobre el puerto tenía el color de una pantalla apagada. Nadie recordaba la calle."


def _tiene_modelo(lang: str) -> bool:
    from verbasizer.tagging import TaggerUnavailable, load_model

    try:
        load_model(lang)
        return True
    except TaggerUnavailable:
        return False


necesita_es = pytest.mark.skipif(not _tiene_modelo("es"), reason="falta el modelo es")


# ---------- health ----------


def test_health():
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert set(data["languages"]) == {"es", "en"}
    assert "NOUN" in data["useful_pos"]


# ---------- tag ----------


def test_tag_sin_idioma_no_etiqueta_pero_tokeniza():
    data = client.post("/api/tag", json={"text": TEXTO, "source": "x"}).json()
    assert data["tokens"]
    assert all(t["pos"] is None for t in data["tokens"])
    assert all(t["source"] == "x" for t in data["tokens"])


def test_tag_texto_vacio_es_422():
    assert client.post("/api/tag", json={"text": "", "source": "x"}).status_code == 422


def test_tag_texto_sin_palabras_es_422():
    r = client.post("/api/tag", json={"text": "...", "source": "x"})
    assert r.status_code == 422
    assert "utilizables" in r.json()["detail"]


@necesita_es
def test_tag_con_idioma_etiqueta():
    data = client.post(
        "/api/tag", json={"text": TEXTO, "source": "x", "lang": "es"}
    ).json()
    assert any(t["pos"] == "NOUN" for t in data["tokens"])


# ---------- distribute ----------


def test_distribute_round_robin():
    tokens = client.post("/api/tag", json={"text": TEXTO, "source": "x"}).json()["tokens"]
    data = client.post(
        "/api/distribute", json={"tokens": tokens, "columns": 4}
    ).json()
    assert len(data["columns"]) == 4
    total = sum(len(c["fragments"]) for c in data["columns"])
    assert total == len(tokens)


def test_distribute_respeta_la_unidad():
    tokens = client.post("/api/tag", json={"text": TEXTO, "source": "x"}).json()["tokens"]
    data = client.post(
        "/api/distribute", json={"tokens": tokens, "columns": 2, "unit": 3}
    ).json()
    fragmentos = [f for c in data["columns"] for f in c["fragments"]]
    assert any(len(f) == 3 for f in fragmentos)


def test_distribute_sin_tokens_es_422():
    assert client.post("/api/distribute", json={"tokens": []}).status_code == 422


def test_distribute_por_pos_sin_etiquetar_avisa():
    tokens = client.post("/api/tag", json={"text": TEXTO, "source": "x"}).json()["tokens"]
    r = client.post("/api/distribute", json={"tokens": tokens, "mode": "by_pos"})
    assert r.status_code == 422
    assert "no están etiquetados" in r.json()["detail"]


def test_distribute_con_mas_columnas_que_fragmentos_avisa():
    tokens = client.post("/api/tag", json={"text": "dos palabras", "source": "x"}).json()[
        "tokens"
    ]
    r = client.post("/api/distribute", json={"tokens": tokens, "columns": 30})
    assert r.status_code == 422
    assert "fragmentos" in r.json()["detail"]


@necesita_es
def test_distribute_por_pos():
    tokens = client.post(
        "/api/tag", json={"text": TEXTO, "source": "x", "lang": "es"}
    ).json()["tokens"]
    data = client.post(
        "/api/distribute",
        json={"tokens": tokens, "mode": "by_pos", "categories": ["NOUN", "VERB"]},
    ).json()
    assert [c["name"] for c in data["columns"]] == ["NOUN", "VERB"]
    assert data["columns"][0]["pos_filter"] == "NOUN"


# ---------- generate ----------


def _columnas(n: int = 4) -> list[dict]:
    tokens = client.post("/api/tag", json={"text": TEXTO, "source": "x"}).json()["tokens"]
    return client.post("/api/distribute", json={"tokens": tokens, "columns": n}).json()[
        "columns"
    ]


def test_generate_devuelve_lineas_con_procedencia():
    data = client.post(
        "/api/generate",
        json={"columns": _columnas(), "lines": 3, "words_per_line": 4, "seed": 9},
    ).json()
    assert data["seed"] == 9
    assert len(data["lines"]) == 3
    for line in data["lines"]:
        assert line["text"]
        assert len(line["placements"]) == 4
        for placement in line["placements"]:
            assert placement["column"].startswith("col")
            assert placement["source"] == "x"


def test_generate_es_reproducible_por_semilla():
    columnas = _columnas()
    a = client.post("/api/generate", json={"columns": columnas, "seed": 55}).json()
    b = client.post("/api/generate", json={"columns": columnas, "seed": 55}).json()
    assert [l["text"] for l in a["lines"]] == [l["text"] for l in b["lines"]]


def test_generate_respeta_la_regla():
    data = client.post(
        "/api/generate", json={"columns": _columnas(), "rule": [2, 5], "lines": 4, "seed": 1}
    ).json()
    assert [len(l["placements"]) for l in data["lines"]] == [2, 5, 2, 5]


def test_generate_sin_columnas_utilizables_es_422():
    columnas = _columnas(2)
    for c in columnas:
        c["weight"] = 0
    r = client.post("/api/generate", json={"columns": columnas, "seed": 1})
    assert r.status_code == 422
    assert "Ninguna columna" in r.json()["detail"]


def test_generate_con_columna_mal_formada_es_422():
    r = client.post("/api/generate", json={"columns": [{"sin": "nombre"}]})
    assert r.status_code == 422
