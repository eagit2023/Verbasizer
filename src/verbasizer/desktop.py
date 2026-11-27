"""Aplicación de escritorio.

Abre una ventana nativa —WebKit en macOS, WebView2 en Windows— con la interfaz
de `web/`, y expone las operaciones de `service` a JavaScript a través del puente
de pywebview. No hay HTTP entre la interfaz y el motor: el JS llama funciones
Python directamente y recibe Promises.

pywebview levanta un servidor interno solo para entregar los archivos estáticos
de la interfaz. Escucha en la máquina local, no se configura y no participa de
las llamadas al motor.

Uso:
    verbasizer-app              abre la aplicación
    verbasizer-app --debug      con herramientas de inspección
    verbasizer-app --selftest   verifica motor y modelos sin abrir ventana
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from . import __version__, service

log = logging.getLogger("verbasizer")

APP_TITLE = "Verbasizer"


# ---------------------------------------------------------------------------
# Recursos
# ---------------------------------------------------------------------------


def resource_dir() -> Path:
    """Dónde están los archivos que viajan con la aplicación.

    Empaquetado con PyInstaller, todo se extrae bajo `sys._MEIPASS`. Corriendo
    desde el repositorio, `web/` está junto a `src/`.
    """
    frozen = getattr(sys, "_MEIPASS", None)
    if frozen:
        return Path(frozen)
    return Path(__file__).resolve().parents[2]


def web_index() -> Path:
    index = resource_dir() / "web" / "index.html"
    if not index.is_file():
        raise FileNotFoundError(f"No encuentro la interfaz en {index}")
    return index


# ---------------------------------------------------------------------------
# Puente: lo que JavaScript puede llamar
# ---------------------------------------------------------------------------


class Bridge:
    """Métodos expuestos a JS como `window.pywebview.api.<nombre>`.

    Cada método recibe un único dict con los parámetros, para no depender del
    orden posicional. Un `ServiceError` llega al JS como una Promise rechazada
    cuyo `message` es el texto del error, listo para mostrar.

    pywebview corre cada llamada en su propio hilo: etiquetar un texto largo no
    congela la ventana.
    """

    def __init__(self) -> None:
        self._window = None

    def _attach(self, window: Any) -> None:
        self._window = window

    # ---- motor -----------------------------------------------------------

    def health(self) -> dict[str, Any]:
        data = service.health()
        data["version"] = __version__
        return data

    def tag(self, params: dict[str, Any]) -> dict[str, Any]:
        return service.tag_text(
            text=params.get("text", ""),
            source=params.get("source") or "fuente",
            lang=params.get("lang") or None,
            keep_punctuation=params.get("keep_punctuation", True),
        )

    def distribute(self, params: dict[str, Any]) -> dict[str, Any]:
        return service.distribute(
            tokens=params.get("tokens", []),
            unit=params.get("unit", 1),
            mode=params.get("mode", "round_robin"),
            columns=params.get("columns", 5),
            categories=params.get("categories"),
        )

    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        return service.generate_lines(
            columns=params.get("columns", []),
            rule=params.get("rule"),
            lines=params.get("lines", 8),
            words_per_line=params.get("words_per_line", 6),
            seed=params.get("seed"),
            avoid_repeats=params.get("avoid_repeats", True),
        )

    def regenerate(self, params: dict[str, Any]) -> dict[str, Any]:
        return service.regenerate_lines(
            columns=params.get("columns", []),
            previous=params.get("previous", {}),
            locked=params.get("locked", []),
            rule=params.get("rule"),
            lines=params.get("lines"),
            seed=params.get("seed"),
            avoid_repeats=params.get("avoid_repeats", True),
        )

    # ---- archivos --------------------------------------------------------
    #
    # En una ventana embebida las descargas del navegador están apagadas por
    # defecto (ALLOW_DOWNLOADS = False en pywebview), así que guardar y abrir
    # se hace con diálogos nativos del sistema.

    def _dialog(self, kind: str, **kwargs: Any) -> str | None:
        import webview

        dialog_type = {
            "open": webview.FileDialog.OPEN,
            "save": webview.FileDialog.SAVE,
        }[kind]
        result = self._window.create_file_dialog(dialog_type, **kwargs)
        if not result:
            return None
        # En macOS SAVE devuelve str; OPEN devuelve una secuencia.
        return result if isinstance(result, str) else result[0]

    def open_text_file(self) -> dict[str, str] | None:
        """Elegir un archivo de texto como fuente. None si se cancela."""
        path = self._dialog(
            "open",
            file_types=("Texto (*.txt;*.md)", "Todos los archivos (*.*)"),
        )
        if path is None:
            return None
        file = Path(path)
        try:
            text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = file.read_text(encoding="latin-1")
        return {"name": file.stem, "text": text}

    def open_session(self) -> dict[str, Any] | None:
        path = self._dialog(
            "open",
            file_types=("Sesión de Verbasizer (*.json)", "Todos los archivos (*.*)"),
        )
        if path is None:
            return None
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise service.ServiceError(f"No pude leer la sesión: {exc}") from exc

    def save_session(self, params: dict[str, Any]) -> str | None:
        """Guardar la sesión. Devuelve la ruta elegida, o None si se cancela."""
        path = self._dialog(
            "save",
            save_filename="sesion.verbasizer.json",
            file_types=("Sesión de Verbasizer (*.json)",),
        )
        if path is None:
            return None
        Path(path).write_text(
            json.dumps(params.get("session", {}), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def save_text(self, params: dict[str, Any]) -> str | None:
        """Exportar la bandeja como texto plano."""
        path = self._dialog(
            "save",
            save_filename=params.get("filename") or "bandeja.txt",
            file_types=("Texto (*.txt)",),
        )
        if path is None:
            return None
        Path(path).write_text(params.get("text", ""), encoding="utf-8")
        return path


# ---------------------------------------------------------------------------
# Autoverificación
# ---------------------------------------------------------------------------


def selftest(report_path: str | None = None) -> int:
    """Recorre el circuito completo sin abrir ventana.

    Sirve para verificar que un binario empaquetado trae el motor, spaCy y los
    modelos, y que todo responde. Lo usa la compilación automática después de
    cada build, en cada plataforma.

    En Windows una aplicación de ventana no tiene salida estándar
    (`sys.stdout` es None), así que el reporte también puede ir a un archivo.
    """
    report: dict[str, Any] = {"version": __version__, "frozen": bool(getattr(sys, "_MEIPASS", None))}
    try:
        report["web_index"] = str(web_index())
        status = service.health()
        report["languages"] = status["languages"]

        muestras = {
            "es": "El cielo sobre el puerto tenía el color de una pantalla apagada.",
            "en": "The sky above the port was the color of a dead channel.",
        }
        tokens: list[dict[str, Any]] = []
        for lang, text in muestras.items():
            if not status["languages"].get(lang):
                raise RuntimeError(f"falta el modelo de {lang}")
            tagged = service.tag_text(text, source=lang, lang=lang)["tokens"]
            if not any(t["pos"] == "NOUN" for t in tagged):
                raise RuntimeError(f"el etiquetado en {lang} no encontró sustantivos")
            tokens.extend(tagged)

        columns = service.distribute(tokens, mode="by_pos", categories=["NOUN", "VERB", "ADJ"])
        lines = service.generate_lines(columns["columns"], lines=2, words_per_line=3, seed=1)
        report["sample"] = [line["text"] for line in lines["lines"]]
        report["ok"] = True
    except Exception as exc:  # noqa: BLE001 — queremos el reporte, no el traceback
        report["ok"] = False
        report["error"] = f"{type(exc).__name__}: {exc}"

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if report_path:
        Path(report_path).write_text(text, encoding="utf-8")
    if sys.stdout is not None:
        print(text)
    return 0 if report["ok"] else 1


# ---------------------------------------------------------------------------
# Arranque
# ---------------------------------------------------------------------------


def run(debug: bool = False) -> int:
    import webview  # import tardío: --selftest no necesita interfaz gráfica

    bridge = Bridge()
    window = webview.create_window(
        APP_TITLE,
        url=str(web_index()),
        js_api=bridge,
        width=1180,
        height=900,
        min_size=(760, 560),
        text_select=True,
    )
    bridge._attach(window)
    # http_server=True: la documentación de pywebview indica activarlo para
    # rutas locales absolutas, que es como se pasa la interfaz.
    webview.start(debug=debug, http_server=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="verbasizer-app", description=__doc__.splitlines()[0])
    parser.add_argument("--debug", action="store_true", help="abrir con herramientas de inspección")
    parser.add_argument("--selftest", action="store_true", help="verificar sin abrir ventana")
    parser.add_argument("--report", metavar="ARCHIVO", help="con --selftest: escribir el reporte acá")
    parser.add_argument("--version", action="version", version=f"Verbasizer {__version__}")
    args = parser.parse_args(argv)

    # Sin consola (aplicación de ventana en Windows) no hay stderr donde loguear.
    if sys.stderr is not None:
        logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)

    if args.selftest:
        return selftest(args.report)
    return run(debug=args.debug)


if __name__ == "__main__":
    raise SystemExit(main())
