"""Tests del puente de escritorio, sin abrir ventana.

Lo que se puede verificar fuera de una ventana real: que cada método del puente
llega al servicio con los parámetros correctos, que los errores conservan su
mensaje, que los archivos se leen y escriben bien cuando el diálogo devuelve una
ruta, y que la cancelación se respeta.
"""

from __future__ import annotations

import json

import pytest

from verbasizer import desktop, service
from verbasizer.desktop import Bridge


class _FakeWindow:
    """Simula los diálogos nativos: devuelve la ruta que se le indique."""

    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def create_file_dialog(self, dialog_type, **kwargs):
        self.calls.append((dialog_type, kwargs))
        return self.answer


@pytest.fixture
def bridge():
    return Bridge()


def _with_dialog(bridge, answer):
    pytest.importorskip("webview")
    window = _FakeWindow(answer)
    bridge._attach(window)
    return window


# ---------- recursos ----------


def test_encuentra_la_interfaz():
    index = desktop.web_index()
    assert index.name == "index.html"
    assert index.is_file()


def test_resource_dir_respeta_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert desktop.resource_dir() == tmp_path


# ---------- motor ----------


def test_health_incluye_version(bridge):
    data = bridge.health()
    assert data["status"] == "ok"
    assert data["version"]


def test_circuito_completo_por_el_puente(bridge):
    tagged = bridge.tag({"text": "uno dos tres cuatro cinco seis siete ocho", "source": "a"})
    columnas = bridge.distribute({"tokens": tagged["tokens"], "columns": 3})["columns"]
    tirada = bridge.generate({"columns": columnas, "lines": 2, "words_per_line": 3, "seed": 4})
    assert len(tirada["lines"]) == 2

    otra = bridge.regenerate(
        {"columns": columnas, "previous": tirada, "locked": [[0, 0]], "seed": 5}
    )
    assert otra["lines"][0]["placements"][0]["text"] == tirada["lines"][0]["placements"][0]["text"]


def test_los_errores_conservan_el_mensaje(bridge):
    # pywebview pasa str(excepción) al JS como Error.message
    with pytest.raises(service.ServiceError) as exc:
        bridge.tag({"text": "", "source": "a"})
    assert str(exc.value) == "No hay texto para procesar."


def test_parametros_faltantes_usan_valores_por_defecto(bridge):
    tagged = bridge.tag({"text": "una frase con varias palabras dentro"})
    assert tagged["source"] == "fuente"
    assert tagged["lang"] is None


# ---------- archivos ----------


def test_abrir_texto(bridge, tmp_path):
    archivo = tmp_path / "diario.txt"
    archivo.write_text("Había una vez un puerto.", encoding="utf-8")
    _with_dialog(bridge, (str(archivo),))
    assert bridge.open_text_file() == {"name": "diario", "text": "Había una vez un puerto."}


def test_abrir_texto_en_latin1(bridge, tmp_path):
    archivo = tmp_path / "viejo.txt"
    archivo.write_bytes("canción".encode("latin-1"))
    _with_dialog(bridge, (str(archivo),))
    assert bridge.open_text_file()["text"] == "canción"


def test_cancelar_el_dialogo_devuelve_none(bridge):
    _with_dialog(bridge, None)
    assert bridge.open_text_file() is None
    assert bridge.open_session() is None
    assert bridge.save_session({"session": {}}) is None
    assert bridge.save_text({"text": "x"}) is None


def test_guardar_y_abrir_sesion(bridge, tmp_path):
    destino = tmp_path / "s.json"
    sesion = {"format": 1, "saved": ["una línea"], "sources": []}

    _with_dialog(bridge, str(destino))  # SAVE devuelve str en macOS
    assert bridge.save_session({"session": sesion}) == str(destino)
    assert json.loads(destino.read_text(encoding="utf-8")) == sesion

    _with_dialog(bridge, (str(destino),))  # OPEN devuelve una secuencia
    assert bridge.open_session() == sesion


def test_sesion_corrupta_da_error_legible(bridge, tmp_path):
    roto = tmp_path / "roto.json"
    roto.write_text("{esto no es json", encoding="utf-8")
    _with_dialog(bridge, (str(roto),))
    with pytest.raises(service.ServiceError, match="No pude leer la sesión"):
        bridge.open_session()


def test_guardar_bandeja(bridge, tmp_path):
    destino = tmp_path / "bandeja.txt"
    ventana = _with_dialog(bridge, (str(destino),))
    bridge.save_text({"text": "línea uno\nlínea dos\n", "filename": "bandeja.txt"})
    assert destino.read_text(encoding="utf-8") == "línea uno\nlínea dos\n"
    assert ventana.calls[0][1]["save_filename"] == "bandeja.txt"


# ---------- autoverificación ----------


def test_selftest_pasa(capsys):
    pytest.importorskip("spacy")
    from verbasizer.tagging import TaggerUnavailable, load_model

    try:
        load_model("es")
        load_model("en")
    except TaggerUnavailable:
        pytest.skip("faltan modelos")

    assert desktop.selftest() == 0
    reporte = json.loads(capsys.readouterr().out)
    assert reporte["ok"] is True
    assert len(reporte["sample"]) == 2
