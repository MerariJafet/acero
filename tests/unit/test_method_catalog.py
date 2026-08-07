"""Tests for the program-owned MethodCatalog (LEGO pieces)."""

from __future__ import annotations

from acero.science.method_catalog import MethodCatalog, Technique


def _cat(tmp=None):
    return MethodCatalog(store=tmp)


def test_retrieval_is_deterministic_and_ranked():
    c = _cat()
    a = [t.id for t in c.retrieve("fórmula cerrada para la suma de cuadrados", 6)]
    b = [t.id for t in c.retrieve("fórmula cerrada para la suma de cuadrados", 6)]
    assert a == b                       # deterministic (program logic, not LLM)
    assert "sym_sum" in a               # a summation goal surfaces the summation piece


def test_retrieval_keeps_a_diverse_floor():
    c = _cat()
    got = c.retrieve("xyzzy nonsense goal", 6)   # no keyword overlap
    assert len(got) >= 6                 # still offers a toolbox, never empty


def test_toolbox_text_lists_idioms():
    c = _cat()
    txt = c.toolbox_text("valor de una integral definida", k=4)
    assert "idiom:" in txt and "sirve para:" in txt


def test_learn_persists_and_reloads(tmp_path):
    c = _cat(tmp_path / "cat")
    c.learn(Technique("my_new_trick", "Truco nuevo", ("algebra",),
                      "hacer algo", "así", "code()", "cuando aplique"))
    assert c.get("my_new_trick") is not None
    # a fresh catalog pointed at the same store reloads the learned piece
    c2 = MethodCatalog(store=tmp_path / "cat")
    assert c2.get("my_new_trick") is not None
    assert "my_new_trick" in c2.ids()


def test_seed_has_the_key_pieces():
    ids = set(_cat().ids())
    for must in ("sym_sum", "nsimplify_identify", "char_equation", "montecarlo_area"):
        assert must in ids
