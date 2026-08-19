"""credence_for(): evidencia duplicada o dependiente NO debe contar como
evidencia independiente.

La iteración 10 del meta-supervisor (2026-08-14) demostró con la función real que
2 lemas IDÉNTICOS + 4 experimentos IDÉNTICOS daban exactamente el mismo
credence 0.95 (el techo de la escala) que cuatro líneas de evidencia genuinamente
diversas. Ese es el punto ciego que estos tests fijan: la saturación
(`min(fuerte,2)`, `min(débil,4)`) actuaba sobre el CONTEO, no sobre la
INDEPENDENCIA.

Estos tests son la red que impide que vuelva a colarse -- y son prerrequisito
declarado del gate automático de disposición (ítem 2 de plan_mejoras.md): sin
ellos, el gate heredaría el mismo punto ciego que se supone que cierra."""
from __future__ import annotations

from acero.science.credence import credence_for, render_line


def _lemma(statement, rid=None, proved=True):
    return {"id": rid, "kind": "lemma", "payload": {"statement": statement,
                                                     "proved": proved}}


def _exp(claim, verdict="holds_empirically", rid=None, n_tested=None):
    payload = {"claim": claim, "result": {"verdict": verdict}}
    if n_tested:
        payload["result"]["n_tested"] = n_tested
    return {"id": rid, "kind": "experiment", "payload": payload}


def test_lemas_identicos_cuentan_una_sola_vez():
    uno = credence_for([_lemma("todo p≡1 mod 840 abre con k=23", rid=1)])
    dos = credence_for([_lemma("todo p≡1 mod 840 abre con k=23", rid=1),
                        _lemma("todo p≡1 mod 840 abre con k=23", rid=2)])
    assert dos["a_favor_fuerte"] == uno["a_favor_fuerte"] == 1
    assert dos["credence"] == uno["credence"]
    assert dos["duplicados_descartados"]["por_contenido"] == 1


def test_la_misma_fila_repetida_por_id_cuenta_una_vez():
    fila = _lemma("lema A", rid=99)
    r = credence_for([fila, fila, fila])
    assert r["a_favor_fuerte"] == 1
    assert r["duplicados_descartados"]["por_id"] == 2


def test_lemas_distintos_si_suman():
    r = credence_for([_lemma("lema A", rid=1), _lemma("lema B", rid=2)])
    assert r["a_favor_fuerte"] == 2
    assert r["duplicados_descartados"]["por_contenido"] == 0


def test_el_caso_exacto_de_la_iteracion_10_ya_no_empata():
    """Reproduce el escenario que destapó el bug: duplicado vs diverso.
    ANTES daban ambos 0.95; ahora el duplicado debe quedar por debajo."""
    duplicado = ([_lemma("mismo lema", rid=i) for i in (1, 2)]
                 + [_exp("mismo experimento", rid=i) for i in (3, 4, 5, 6)])
    diverso = ([_lemma("lema uno", rid=1), _lemma("lema dos", rid=2)]
               + [_exp(f"experimento {j}", rid=2 + j) for j in (1, 2, 3, 4)])

    c_dup = credence_for(duplicado)
    c_div = credence_for(diverso)

    assert c_dup["a_favor_fuerte"] == 1 and c_dup["a_favor_debil"] == 1
    assert c_div["a_favor_fuerte"] == 2 and c_div["a_favor_debil"] == 4
    assert c_dup["credence"] < c_div["credence"], (
        "evidencia duplicada NO puede dar el mismo credence que evidencia diversa")


def test_mismo_claim_con_veredicto_opuesto_son_evidencias_distintas():
    """Un claim SOSTENIDO y ese mismo claim REFUTADO no son la misma evidencia:
    son justamente el conflicto que hay que ver, no un duplicado."""
    r = credence_for([_exp("claim X", verdict="holds_empirically", rid=1),
                      _exp("claim X", verdict="refuted", rid=2)])
    assert r["a_favor_debil"] == 1
    assert r["en_contra"] == 1
    assert r["duplicados_descartados"]["por_contenido"] == 0


def test_experimentos_identicos_no_inflan():
    r = credence_for([_exp("mismo test", rid=i) for i in range(1, 6)])
    assert r["a_favor_debil"] == 1
    assert r["duplicados_descartados"]["por_contenido"] == 4


def test_normalizacion_de_espacios_y_mayusculas():
    r = credence_for([_lemma("El Lema  A", rid=1), _lemma("el lema a", rid=2)])
    assert r["a_favor_fuerte"] == 1, "difieren solo en espacios/mayúsculas"


def test_negativos_duplicados_tampoco_inflan_la_contraevidencia():
    r = credence_for([{"id": i, "kind": "negative",
                       "payload": {"statement": "falla en p=5003"}}
                      for i in (1, 2, 3)])
    assert r["en_contra"] == 1
    assert r["duplicados_descartados"]["por_contenido"] == 2


def test_patterns_duplicados_no_inflan():
    filas = [{"id": i, "kind": "pattern",
              "payload": {"expr": "k ~ log(p)", "independent_views": 2}}
             for i in (1, 2, 3)]
    r = credence_for(filas)
    assert r["a_favor_debil"] == 1


def test_objeciones_de_criticas_SI_se_acumulan_aunque_se_repitan():
    """Las críticas NO son evidencia: dos revisores señalando el mismo punto
    flojo es señal doble de que el punto existe, no un duplicado a descartar."""
    filas = [{"id": i, "kind": "critique",
              "payload": {"objections": ["el holdout ya fue visto"]}}
             for i in (1, 2)]
    r = credence_for(filas)
    assert r["objeciones"] == 2


def test_sin_evidencia_no_es_lo_mismo_que_evidencia_en_contra():
    vacio = credence_for([])
    contra = credence_for([{"id": 1, "kind": "negative",
                            "payload": {"statement": "contraejemplo"}}])
    assert "SIN evidencia" in vacio["estado"]
    assert "EN CONTRA" in contra["estado"]
    assert contra["credence"] < vacio["credence"]


def test_filas_sin_id_se_deduplican_igual_por_contenido():
    """El ledger real puede entregar filas sin `id`; el dedup por contenido debe
    seguir funcionando."""
    r = credence_for([_lemma("lema sin id"), _lemma("lema sin id")])
    assert r["a_favor_fuerte"] == 1
    assert r["duplicados_descartados"]["por_contenido"] == 1


def test_render_line_sigue_funcionando():
    linea = render_line(credence_for([_lemma("A", rid=1)]))
    assert "credence" in linea and "fuerte:1" in linea


def test_la_formula_declara_que_deduplica():
    r = credence_for([_lemma("A", rid=1)])
    assert "DEDUPLICADA" in r["formula"] or "deduplicada" in r["formula"].lower()


def test_filas_sin_statement_NO_colapsan_entre_si():
    """Auditoría ML0 (2026-08-19): kinds sin campo `statement` (decision,
    literature, build...) devolvían la huella vacía "kind|" y TODAS las filas
    de ese kind colapsaban en un grupo — 1685/2070 filas del proyecto real
    contadas como "duplicados" sin serlo."""
    filas = [{"id": i, "kind": "decision",
              "payload": {"persona": "bohr", "razon": f"jugada distinta {i}"}}
             for i in (1, 2, 3)]
    r = credence_for(filas)
    assert r["duplicados_descartados"]["por_contenido"] == 0


def test_filas_sin_statement_byte_iguales_SI_deduplican():
    pay = {"persona": "bohr", "razon": "la misma jugada re-registrada"}
    r = credence_for([{"id": 1, "kind": "decision", "payload": dict(pay)},
                      {"id": 2, "kind": "decision", "payload": dict(pay)}])
    assert r["duplicados_descartados"]["por_contenido"] == 1


def test_mismo_claim_en_dominios_distintos_son_evidencias_distintas():
    """El mismo claim sostenido en n=3000 y en n=15000 no es una re-corrida
    idéntica: el dominio es parte de la identidad de la evidencia."""
    r = credence_for([_exp("claim X", rid=1, n_tested=3000),
                      _exp("claim X", rid=2, n_tested=15000)])
    assert r["a_favor_debil"] == 2
    assert r["duplicados_descartados"]["por_contenido"] == 0
