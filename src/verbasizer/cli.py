"""Línea de comandos del motor.

Fase 1: generar desde archivos de texto, sin etiquetado gramatical (eso llega
con el backend). Sirve para probar el motor de verdad antes de que haya interfaz.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import Session, Source, generate, round_robin, to_fragments, tokenize
from .engine.columns import by_pos


def _parse_weights(raw: str | None, count: int) -> list[float]:
    if raw is None:
        return [1.0] * count
    weights = [float(w) for w in raw.split(",")]
    if len(weights) != count:
        raise SystemExit(
            f"Pasaste {len(weights)} pesos para {count} columnas. Tienen que coincidir."
        )
    if all(w == 0 for w in weights):
        raise SystemExit("No pueden ser todos los pesos cero.")
    return weights


def _parse_rule(raw: str | None) -> list[int] | None:
    if raw is None:
        return None
    return [int(n) for n in raw.split(",")]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verbasizer",
        description="Cut-up por columnas, con peso por columna y procedencia.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generar una tirada")
    gen.add_argument(
        "sources",
        nargs="+",
        type=Path,
        help="Archivos de texto de entrada (uno o más)",
    )
    gen.add_argument("-c", "--columns", type=int, default=5, help="Cantidad de columnas")
    gen.add_argument(
        "--lang",
        choices=["es", "en"],
        help="Etiquetar gramaticalmente con spaCy. Sin esto no hay restricción por columna.",
    )
    gen.add_argument(
        "--by-pos",
        metavar="CATEGORIAS",
        help=(
            "Una columna por categoría gramatical, separadas por coma "
            "(ej: NOUN,VERB,ADJ). Requiere --lang. Ignora --columns."
        ),
    )
    gen.add_argument(
        "-w",
        "--weights",
        help="Pesos separados por coma, uno por columna (ej: 1,3,1,1,2)",
    )
    gen.add_argument(
        "-u",
        "--unit",
        type=int,
        default=1,
        help="Palabras por fragmento. 1 = palabra suelta; 4 o 5 = el método manual de Bowie",
    )
    gen.add_argument("-n", "--lines", type=int, default=8, help="Cantidad de líneas")
    gen.add_argument(
        "-l",
        "--length",
        type=int,
        default=6,
        help="Fragmentos por línea (se ignora si usás --rule)",
    )
    gen.add_argument(
        "-r",
        "--rule",
        help="Plantilla de estructura: fragmentos por línea, separados por coma (ej: 6,4,6,4)",
    )
    gen.add_argument("-s", "--seed", type=int, help="Semilla, para reproducir una tirada")
    gen.add_argument(
        "--strip-punctuation",
        action="store_true",
        help="Descartar la puntuación (por defecto se conserva)",
    )
    gen.add_argument(
        "--allow-repeats",
        action="store_true",
        help="Permitir que un fragmento se repita dentro de la misma línea",
    )
    gen.add_argument(
        "--show-origin",
        action="store_true",
        help="Mostrar de qué columna y fuente vino cada fragmento",
    )
    gen.add_argument("-o", "--save", type=Path, help="Guardar la sesión como JSON")

    serve = sub.add_parser("serve", help="Levantar la API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true", help="Recargar al editar código")

    return parser


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print(
            'Falta el extra del servidor. Instalalo con:\n    pip install -e ".[server]"',
            file=sys.stderr,
        )
        return 1

    uvicorn.run(
        "verbasizer.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    if args.by_pos and not args.lang:
        print("--by-pos necesita --lang: hay que etiquetar antes de agrupar.", file=sys.stderr)
        return 1

    session = Session(
        name=", ".join(p.stem for p in args.sources),
        unit=args.unit,
        keep_punctuation=not args.strip_punctuation,
    )

    all_tokens = []
    for path in args.sources:
        if not path.is_file():
            print(f"No encuentro el archivo: {path}", file=sys.stderr)
            return 1
        text = path.read_text(encoding="utf-8")

        if args.lang:
            from .tagging import TaggerUnavailable, tag

            try:
                tokens = tag(
                    text,
                    source=path.stem,
                    lang=args.lang,
                    keep_punctuation=session.keep_punctuation,
                )
            except TaggerUnavailable as exc:
                print(str(exc), file=sys.stderr)
                return 1
        else:
            tokens = tokenize(
                text, source=path.stem, keep_punctuation=session.keep_punctuation
            )

        if not tokens:
            print(f"El archivo {path} no tiene texto utilizable.", file=sys.stderr)
            return 1
        session.sources.append(
            Source(name=path.stem, text=text, lang=args.lang, tokens=tokens)
        )
        all_tokens.extend(tokens)

    fragments = to_fragments(all_tokens, unit=args.unit)

    if args.by_pos:
        categories = [c.strip().upper() for c in args.by_pos.split(",") if c.strip()]
        session.columns = by_pos(fragments, categories)
        vacias = [c.name for c in session.columns if not c.eligible()]
        if vacias:
            print(
                f"Sin material para: {', '.join(vacias)}. Esas columnas quedan mudas.",
                file=sys.stderr,
            )
        weights = _parse_weights(args.weights, len(session.columns))
    else:
        if len(fragments) < args.columns:
            print(
                f"Hay {len(fragments)} fragmentos para {args.columns} columnas. "
                "Cargá más texto o bajá la cantidad de columnas.",
                file=sys.stderr,
            )
            return 1
        session.columns = round_robin(fragments, args.columns)
        weights = _parse_weights(args.weights, args.columns)

    for column, weight in zip(session.columns, weights):
        column.weight = weight

    try:
        generation = generate(
            session.columns,
            rule=_parse_rule(args.rule),
            lines=args.lines,
            words_per_line=args.length,
            seed=args.seed,
            avoid_repeats=not args.allow_repeats,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    session.generations.append(generation)

    for line in generation.lines:
        if args.show_origin:
            detail = "  ".join(
                f"{p.text}[{p.column}/{p.fragment.source}]" for p in line.placements
            )
            print(detail)
        else:
            print(line.text)

    print(f"\n— semilla {generation.seed}", file=sys.stderr)

    if args.save:
        session.save(args.save)
        print(f"— sesión guardada en {args.save}", file=sys.stderr)

    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "generate":
        return cmd_generate(args)
    if args.command == "serve":
        return cmd_serve(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
