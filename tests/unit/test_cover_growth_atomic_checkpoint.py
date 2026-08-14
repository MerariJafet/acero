"""cover_growth.py corre días seguidos y ya sobrevivió un apagón real (2026-08-11,
ver su propio docstring de WORKERS). `open(path, "w"/"wb")` trunca el archivo antes de
escribir: si el proceso muere a mitad del checkpoint (OOM-kill, corte de luz, kill -9)
la corrida completa se pierde, no solo el último hito. Estos tests fijan que
`_atomic_write` nunca deja un estado a medias -- ADVERTENCIA: nunca deben tocar el
CKPT/OUT_JSON reales del proceso que puede estar corriendo en vivo; solo llaman a la
función con rutas propias bajo tmp_path.

`research/reto50/` está en .gitignore (el repo publica solo el motor; datos e
investigaciones viven fuera, ver memoria "espacio de trabajo") -- este archivo NO
está versionado. En un clon limpio del repo no existe, así que estos tests se
saltan solos en vez de fallar; solo corren de verdad en un workspace que ya tiene
la investigación activa (como este)."""
from __future__ import annotations

import importlib.util
import json
import pickle
from pathlib import Path

import pytest

_MODULE_PATH = (Path(__file__).resolve().parents[2] / "research" / "reto50"
                / "cover_growth.py")

pytestmark = pytest.mark.skipif(
    not _MODULE_PATH.exists(),
    reason="research/reto50/cover_growth.py no está versionado (dato de workspace, "
          "no del motor) -- ausente en un clon limpio del repo")


@pytest.fixture(scope="module")
def cover_growth_module():
    """Importa el script SIN ejecutar main() (guardado tras `if __name__ == '__main__'`)
    y sin depender de que el paquete `research` sea importable normalmente."""
    spec = importlib.util.spec_from_file_location("_cover_growth_under_test", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_atomic_write_deja_el_archivo_completo(cover_growth_module, tmp_path) -> None:
    path = str(tmp_path / "prueba.json")
    cover_growth_module._atomic_write(
        path, lambda fh: json.dump({"rows": [1, 2, 3]}, fh))
    assert json.loads(Path(path).read_text()) == {"rows": [1, 2, 3]}
    # no debe quedar ningun temporal suelto
    assert list(tmp_path.glob("*.tmp*")) == []


def test_atomic_write_modo_binario_para_ckpt(cover_growth_module, tmp_path) -> None:
    path = str(tmp_path / "prueba.ckpt")
    payload = {"sig": {1: 2}, "n": 3, "p": 5, "rows": []}
    cover_growth_module._atomic_write(path, lambda fh: pickle.dump(payload, fh))
    with open(path, "rb") as fh:
        assert pickle.load(fh) == payload


def test_una_escritura_fallida_no_toca_el_archivo_previo(cover_growth_module, tmp_path
                                                          ) -> None:
    """Simula el caso real: el checkpoint viejo YA existe con datos buenos, y la
    escritura del nuevo falla a mitad de camino. El archivo real debe seguir
    siendo el viejo, completo -- nunca un .ckpt truncado."""
    path = str(tmp_path / "prueba.ckpt")
    with open(path, "wb") as fh:
        pickle.dump({"version": "buena"}, fh)

    def _escritura_que_falla(fh):
        fh.write(b"datos parciales, nunca deberian quedar como el archivo final")
        raise RuntimeError("simulacion de OOM-kill a mitad de escritura")

    with pytest.raises(RuntimeError):
        cover_growth_module._atomic_write(path, _escritura_que_falla)

    with open(path, "rb") as fh:
        assert pickle.load(fh) == {"version": "buena"}, (
            "el checkpoint previo se corrompio pese a que la escritura nueva fallo")
    assert list(tmp_path.glob("*.tmp*")) == [], "quedo un temporal huerfano"
