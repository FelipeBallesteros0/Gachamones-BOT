"""Validación pura de nombres visibles en Discord y su adaptador modal."""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

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
    db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15, 15), ahora,)
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


# --- Bautizar al recluta ----------------------------------------------------

def montar_plantel(tmp_path, monkeypatch):
    """Una activa con nombre y un recluta sin bautizar, como al volver de una
    aventura en la que alguien se unió."""
    ahora = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(db, "RUTA", tmp_path / "prueba.db")
    monkeypatch.setattr(db, "ahora_utc", lambda: ahora)
    db.inicializar()
    activa = db.crear("u1", "g1", "pulpo", "Vieja", (15, 15, 15, 15), ahora)
    recluta = db.crear("u1", "g1", "michi", sim.NOMBRE_PENDIENTE, (15, 15, 15, 15), ahora,
    activa=False,)
    return activa, recluta


class Bandeja:
    """Recoge lo que se responde, sin Discord de por medio."""

    def __init__(self):
        self.enviados = []
        self.editado = None
        self.publicadas = []

    def interaccion(self, usuario="u1", guild="g1"):
        bandeja = self

        class Respuesta:
            async def send_message(self, contenido, **opciones):
                bandeja.enviados.append((contenido, opciones))

            async def edit_message(self, **opciones):
                bandeja.editado = opciones

        class Canal:
            id = 1

            async def send(self, contenido, **opciones):
                bandeja.enviados.append((contenido, opciones))

        return SimpleNamespace(
            user=SimpleNamespace(id=usuario, mention=f"<@{usuario}>"),
            guild_id=guild,
            response=Respuesta(),
            channel=Canal(),
        )


def test_bautizar_al_recluta_no_le_toca_el_nombre_al_activo(tmp_path, monkeypatch):
    """De aquí saldría el fallo: el modal buscaba «la activa», y el recluta
    duerme en la incubadora."""
    activa, recluta = montar_plantel(tmp_path, monkeypatch)
    bandeja = Bandeja()

    async def publicar(canal, criatura, ahora):
        bandeja.publicadas.append(criatura)

    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    modal = SimpleNamespace(nombre="Pelusa", criatura_id=recluta.id)

    asyncio.run(vistas.NombreModal.on_submit(modal, bandeja.interaccion()))

    assert db.por_id(recluta.id).nombre == "Pelusa"
    assert db.criatura_activa("u1", "g1").nombre == activa.nombre
    # Y no se publica su ficha: sigue en la incubadora, no es la que se cuida.
    assert bandeja.publicadas == []


def test_bautizado_el_recluta_ya_sale_de_la_incubadora(tmp_path, monkeypatch):
    _, recluta = montar_plantel(tmp_path, monkeypatch)
    bandeja = Bandeja()
    monkeypatch.setattr(vistas, "publicar_pantalla", AsyncMock())
    modal = SimpleNamespace(nombre="Pelusa", criatura_id=recluta.id)

    assert not db.activar(recluta.id, "u1", "g1", db.ahora_utc())
    asyncio.run(vistas.NombreModal.on_submit(modal, bandeja.interaccion()))

    assert db.activar(recluta.id, "u1", "g1", db.ahora_utc())
    assert db.criatura_activa("u1", "g1").nombre == "Pelusa"


def test_no_se_puede_bautizar_al_recluta_de_otra_persona(tmp_path, monkeypatch):
    """El identificador viaja dentro del formulario: si no se comprobara, uno
    copiado de otro mensaje renombraría la mascota de otro."""
    _, recluta = montar_plantel(tmp_path, monkeypatch)
    bandeja = Bandeja()
    modal = SimpleNamespace(nombre="Robada", criatura_id=recluta.id)

    asyncio.run(
        vistas.NombreModal.on_submit(modal, bandeja.interaccion(usuario="u2"))
    )

    assert db.por_id(recluta.id).nombre == sim.NOMBRE_PENDIENTE
    assert bandeja.enviados[0][1].get("ephemeral") is True


def test_el_boton_del_recluta_busca_al_que_espera_nombre(tmp_path, monkeypatch):
    _, recluta = montar_plantel(tmp_path, monkeypatch)

    encontrado = vistas.sin_nombrar_de("u1", "g1")

    assert encontrado is not None and encontrado.id == recluta.id
    assert vistas.sin_nombrar_de("u2", "g1") is None
