"""Backend agéntico: disponibilidad honesta del agente de codegen.

Todo offline — se falsifica el HOME de credenciales y el archivo del
cortacircuitos; nunca se levanta docker ni se llama a un agente real.
"""

from __future__ import annotations

# --- cortacircuitos de sesión muerta -----------------------------------------

def test_breaker_se_abre_y_se_cierra_solo_al_reloguear(tmp_path, monkeypatch):
    """Que las credenciales EXISTAN no significa que el token valga. 2026-08-21:
    un OAuth expirado dejó los archivos en su sitio y ACERO reintentó 173 veces."""
    from acero.sandbox import agentic_runner as ar
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    creds = home / ".claude" / ".credentials.json"
    creds.write_text('{"token": "viejo"}', encoding="utf-8")
    (home / ".claude.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("ACERO_CLAUDE_HOME", str(home))
    monkeypatch.setenv("ACERO_AGENT_BREAKER", str(tmp_path / "breaker.json"))

    assert ar.agent_breaker_open() is False          # arranca cerrado
    ar.mark_agent_unauthenticated("Not logged in · Please run /login")
    assert ar.agent_breaker_open() is True           # sesión muerta conocida
    # el agente deja de ofrecerse aunque docker y las credenciales estén ahí
    assert ar.agent_available() is False

    # el humano se re-loguea: cambia la huella → el breaker se cierra SOLO
    import os
    creds.write_text('{"token": "nuevo-y-mas-largo"}', encoding="utf-8")
    os.utime(creds, (9_999_999, 9_999_999))
    assert ar.agent_breaker_open() is False


def test_breaker_sin_archivo_no_bloquea(tmp_path, monkeypatch):
    from acero.sandbox import agentic_runner as ar
    monkeypatch.setenv("ACERO_AGENT_BREAKER", str(tmp_path / "no-existe.json"))
    assert ar.agent_breaker_open() is False
