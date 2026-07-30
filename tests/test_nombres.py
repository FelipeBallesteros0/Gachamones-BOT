"""Validación pura de nombres visibles en Discord y su adaptador modal."""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import db
import simulacion as sim
import vistas


def test_normaliza_nombres_unicode_y_espacios_internos():
    assert sim.normalizar_nombre("  Éowyn   del  Río  ") == "Éowyn del Río"
    assert sim.normalizar_nombre("O'Connor-Luz") == "O'Connor-Luz"
    assert sim.normalizar_nombre("星 の 子") == "星 の 子"
    assert sim.normalizar_nombre("A\u0301ngel D’Artagnan 2") == "A\u0301ngel D’Artagnan 2"


@pytest.mark.parametrize(
    ("nombre", "motivo"),
    [
        ("   ", "vacío"),
        ("a" * 25, "24"),
        ("Luna\nFalsa", "letras, números"),
        ("<@123456789012345678>", "letras, números"),
        ("<@!123456789012345678>", "letras, números"),
        ("<@&123456789012345678>", "letras, números"),
        ("<#123456789012345678>", "letras, números"),
        ("@everyone", "letras, números"),
        ("**Luna**", "letras, números"),
        ("```Luna```", "letras, números"),
        ("[Luna](https://x.co)", "letras, números"),
        ("||Luna||", "letras, números"),
        ("__Luna__", "letras, números"),
        ("~~Luna~~", "letras, números"),
    ],
)
def test_rechaza_nombres_que_rompen_o_suplantan_la_salida(nombre, motivo):
    with pytest.raises(ValueError, match=motivo):
        sim.normalizar_nombre(nombre)


def test_el_modal_invalido_responde_en_privado_y_no_muta_la_bd(
    tmp_path, monkeypatch
):
    ahora = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(db, "RUTA", tmp_path / "prueba.db")
    monkeypatch.setattr(db, "ahora_utc", lambda: ahora)
    db.inicializar()
    db.crear(
        "u1", "g1", "pulpo", "Prueba", (15, 15, 15), ahora,
    )
    enviados = []

    class Respuesta:
        async def send_message(self, contenido, **opciones):
            enviados.append((contenido, opciones))

        async def edit_message(self, **opciones):
            enviados.append(("editado", opciones))

    class Canal:
        id = 1

        async def send(self, contenido, **opciones):
            enviados.append((contenido, opciones))

    async def no_publicar(*args, **kwargs):
        return None

    monkeypatch.setattr(vistas, "publicar_pantalla", no_publicar)
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1", mention="<@u1>"),
        guild_id="g1",
        response=Respuesta(),
        channel=Canal(),
    )
    modal = SimpleNamespace(nombre="**Luna**")

    asyncio.run(vistas.NombreModal.on_submit(modal, interaccion))

    assert db.criatura_activa("u1", "g1").nombre == "Prueba"
    assert len(enviados) == 1
    assert "letras, números" in enviados[0][0]
    assert enviados[0][1].get("ephemeral") is True
