from acero.core.hashing import hash_json, hash_text
from acero.core.ids import is_valid, new_id


def test_new_id_shape_and_prefix():
    i = new_id("hyp")
    assert i.startswith("hyp_")
    assert is_valid(i, "hyp")
    assert not is_valid(i, "q")


def test_ids_are_time_sortable():
    a = new_id("x", now_ms=1000, entropy=b"\x00" * 10)
    b = new_id("x", now_ms=2000, entropy=b"\x00" * 10)
    assert a < b


def test_ids_unique_with_entropy():
    a = new_id("x", now_ms=1000, entropy=b"\x01" * 10)
    b = new_id("x", now_ms=1000, entropy=b"\x02" * 10)
    assert a != b


def test_invalid_ids():
    assert not is_valid("noprefix")
    assert not is_valid("x_short")
    assert not is_valid("x_" + "I" * 26)  # I not in Crockford alphabet


def test_hashing_deterministic_and_canonical():
    assert hash_text("abc") == hash_text("abc")
    assert hash_text("abc").startswith("sha256:")
    # key order does not matter
    assert hash_json({"a": 1, "b": 2}) == hash_json({"b": 2, "a": 1})
    assert hash_json({"a": 1}) != hash_json({"a": 2})
