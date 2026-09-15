"""Tests del motor.

Lo que importa verificar: que sea determinístico, que los pesos realmente
sesguen el resultado, que la restricción gramatical filtre, y que la procedencia
sobreviva hasta el final.
"""

from __future__ import annotations

import pytest

from verbasizer.engine import (
    Column,
    Session,
    by_pos,
    generate,
    round_robin,
    to_fragments,
    tokenize,
)
from verbasizer.engine.tokens import Fragment, Token

TEXTO = """El cielo sobre el puerto tenía el color de una pantalla.
Nadie recordaba el nombre exacto de la calle.
Las luces se apagaron una por una, sin ruido.
"""


def columnas(count: int = 4, unit: int = 1) -> list[Column]:
    tokens = tokenize(TEXTO, source="prueba")
    return round_robin(to_fragments(tokens, unit=unit), count)


# ---------- tokenizador ----------


def test_tokenize_conserva_procedencia():
    tokens = tokenize(TEXTO, source="prueba")
    assert tokens
    assert all(t.source == "prueba" for t in tokens)
    assert tokens[0].text == "El"
    assert tokens[0].line == 0
    assert tokens[0].position == 0


def test_tokenize_conserva_puntuacion_por_defecto():
    tokens = tokenize("una por una, sin ruido.", source="x")
    assert "una," in [t.text for t in tokens]


def test_tokenize_puede_descartar_puntuacion():
    tokens = tokenize("una por una, sin ruido.", source="x", keep_punctuation=False)
    textos = [t.text for t in tokens]
    assert "una," not in textos
    assert "ruido" in textos


def test_split_de_frases_separa_por_punto_y_por_salto():
    tokens = tokenize(TEXTO, source="x")
    assert max(t.line for t in tokens) == 2


# ---------- fragmentos ----------


def test_fragmentos_de_una_palabra():
    tokens = tokenize(TEXTO, source="x")
    fragments = to_fragments(tokens, unit=1)
    assert len(fragments) == len(tokens)


def test_fragmentos_agrupan_palabras_consecutivas():
    tokens = tokenize("uno dos tres cuatro cinco seis", source="x")
    fragments = to_fragments(tokens, unit=3)
    assert [f.text for f in fragments] == ["uno dos tres", "cuatro cinco seis"]


def test_fragmentos_no_cruzan_frases():
    tokens = tokenize("uno dos. tres cuatro", source="x")
    fragments = to_fragments(tokens, unit=3)
    # El corte de frase fuerza un flush: nunca mezcla las dos oraciones.
    assert all(len({t.line for t in f.tokens}) == 1 for f in fragments)


def test_fragmento_vacio_es_error():
    with pytest.raises(ValueError):
        Fragment(())


# ---------- reparto ----------


def test_round_robin_reparte_exactamente_n_columnas():
    cols = columnas(5)
    assert len(cols) == 5
    assert all(c.fragments for c in cols)


def test_round_robin_no_pierde_fragmentos():
    tokens = tokenize(TEXTO, source="x")
    fragments = to_fragments(tokens)
    cols = round_robin(fragments, 4)
    assert sum(len(c.fragments) for c in cols) == len(fragments)


def test_by_pos_agrupa_por_categoria():
    tokens = [
        Token("cielo", "x", 0, 0, pos="NOUN"),
        Token("arder", "x", 0, 1, pos="VERB"),
        Token("puerto", "x", 0, 2, pos="NOUN"),
    ]
    cols = by_pos(to_fragments(tokens), ["NOUN", "VERB"])
    assert [c.name for c in cols] == ["NOUN", "VERB"]
    assert len(cols[0].fragments) == 2
    assert len(cols[1].fragments) == 1


# ---------- generación ----------


def test_misma_semilla_mismo_resultado():
    a = generate(columnas(), seed=1234, lines=6)
    b = generate(columnas(), seed=1234, lines=6)
    assert a.text == b.text


def test_semillas_distintas_dan_resultados_distintos():
    a = generate(columnas(), seed=1, lines=8)
    b = generate(columnas(), seed=2, lines=8)
    assert a.text != b.text


def test_la_semilla_queda_registrada_aunque_no_se_pase():
    resultado = generate(columnas(), lines=2)
    assert isinstance(resultado.seed, int)
    repetido = generate(columnas(), seed=resultado.seed, lines=2)
    assert repetido.text == resultado.text


def test_respeta_la_cantidad_de_lineas_y_el_largo():
    resultado = generate(columnas(), seed=7, lines=5, words_per_line=4)
    assert len(resultado.lines) == 5
    assert all(len(line.placements) == 4 for line in resultado.lines)


def test_la_regla_cicla_sobre_las_lineas():
    resultado = generate(columnas(), seed=7, lines=4, rule=[2, 5])
    largos = [len(line.placements) for line in resultado.lines]
    assert largos == [2, 5, 2, 5]


def test_el_peso_sesga_el_resultado():
    """Una columna con peso 20 contra tres de peso 1 tiene que dominar."""
    cols = columnas(4)
    for c in cols:
        c.weight = 1.0
    cols[0].weight = 20.0
    cols[0].name = "pesada"

    resultado = generate(cols, seed=99, lines=60, words_per_line=6)
    usos = [p.column for line in resultado.lines for p in line.placements]
    proporcion = usos.count("pesada") / len(usos)
    # Esperado teórico: 20/23 ≈ 0.87. Margen amplio para no atarse al RNG.
    assert proporcion > 0.7


def test_peso_cero_excluye_la_columna():
    cols = columnas(3)
    cols[1].weight = 0.0
    cols[1].name = "muda"
    resultado = generate(cols, seed=5, lines=20)
    usos = {p.column for line in resultado.lines for p in line.placements}
    assert "muda" not in usos


def test_peso_negativo_es_error():
    with pytest.raises(ValueError):
        Column(name="mala", weight=-1.0)


def test_restriccion_gramatical_filtra():
    tokens = [
        Token("cielo", "x", 0, 0, pos="NOUN"),
        Token("arder", "x", 0, 1, pos="VERB"),
        Token("puerto", "x", 0, 2, pos="NOUN"),
    ]
    fragments = to_fragments(tokens)
    solo_verbos = Column(name="V", fragments=fragments, pos_filter="VERB")
    assert [f.text for f in solo_verbos.eligible()] == ["arder"]

    resultado = generate([solo_verbos], seed=3, lines=2, words_per_line=3,
                         avoid_repeats=False)
    assert set(resultado.text.split()) == {"arder"}


def test_columna_sin_fragmentos_utilizables_falla_con_mensaje_claro():
    vacia = Column(name="V", fragments=[], pos_filter="VERB")
    with pytest.raises(ValueError, match="Ninguna columna"):
        generate([vacia], seed=1)


def test_sin_columnas_es_error():
    with pytest.raises(ValueError):
        generate([], seed=1)


def test_la_procedencia_sobrevive_hasta_el_resultado():
    resultado = generate(columnas(), seed=11, lines=3)
    for line in resultado.lines:
        for placement in line.placements:
            assert placement.column.startswith("col")
            assert placement.fragment.source == "prueba"
            assert placement.fragment.head.line >= 0


def test_no_repite_fragmento_dentro_de_la_linea():
    cols = columnas(4)
    resultado = generate(cols, seed=21, lines=10, words_per_line=5)
    for line in resultado.lines:
        textos = [p.text for p in line.placements]
        assert len(set(textos)) == len(textos)


# ---------- sesión ----------


def test_sesion_ida_y_vuelta_a_json(tmp_path):
    session = Session(name="prueba")
    session.columns = columnas(3)
    session.generations.append(generate(session.columns, seed=42, lines=3))
    session.keep("una línea que sirve")

    destino = tmp_path / "sesion.json"
    session.save(destino)
    recuperada = Session.load(destino)

    assert recuperada.name == "prueba"
    assert recuperada.saved == ["una línea que sirve"]
    assert len(recuperada.columns) == 3
    assert recuperada.generations[0].seed == 42
    assert recuperada.generations[0].text == session.generations[0].text


def test_la_bandeja_no_guarda_duplicados():
    session = Session()
    session.keep("misma línea")
    session.keep("misma línea")
    assert session.saved == ["misma línea"]
    session.discard("misma línea")
    assert session.saved == []


def test_formato_desconocido_es_error():
    with pytest.raises(ValueError, match="Formato de sesión desconocido"):
        Session.from_dict({"format": 999})
