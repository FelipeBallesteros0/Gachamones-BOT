"""Validación pura de nombres visibles en Discord y su adaptador modal."""
import asyncio
import random
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import db
import especies as esp
import nacer
import nombres
import simulacion as sim
import vistas


# --- Los nombres que se pone un recluta -------------------------------------

def test_la_lista_de_nombres_de_recluta_vale():
    assert len(nombres.NOMBRES) == 40 > db.MAXIMO_PLANTEL + 1
    assert all(sim.normalizar_nombre(n) == n for n in nombres.NOMBRES)
    assert len({n.casefold() for n in nombres.NOMBRES}) == 40
    assert not {n.casefold() for n in nombres.NOMBRES} & {e.nombre.casefold() for e in esp.ESPECIES.values()}


def test_elegir_evita_los_que_ya_hay_sin_mirar_mayusculas():
    todos_menos_uno = [n.upper() for n in nombres.NOMBRES if n != "Trufa"]
    assert nombres.elegir(random.Random(7), todos_menos_uno) == "Trufa"
    assert nombres.elegir(random.Random(7), nombres.NOMBRES) in nombres.NOMBRES


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
    """Una activa con nombre y un recluta que se puso el suyo solo, como al
    volver de una aventura en la que alguien se unió."""
    ahora = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(db, "RUTA", tmp_path / "prueba.db")
    monkeypatch.setattr(db, "ahora_utc", lambda: ahora)
    db.inicializar()
    activa = db.crear("u1", "g1", "pulpo", "Vieja", (15, 15, 15, 15), ahora)
    recluta = db.crear(
        "u1", "g1", "michi", "Brote", (15, 15, 15, 15), ahora,
        activa=False, se_nombro_solo=True,
    )
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


def test_el_modal_del_huevo_deja_el_nombre_como_tuyo(tmp_path, monkeypatch):
    """El formulario sin `criatura_id` (el del botón del huevo) renombra al
    activo; si ése se había puesto el nombre solo, ya no lo tiene."""
    ahora = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(db, "RUTA", tmp_path / "prueba.db")
    monkeypatch.setattr(db, "ahora_utc", lambda: ahora)
    db.inicializar()
    activa = db.crear(
        "u1", "g1", "pulpo", "Miga", (15, 15, 15, 15), ahora, se_nombro_solo=True
    )
    monkeypatch.setattr(vistas, "publicar_pantalla", AsyncMock())
    modal = SimpleNamespace(nombre="Rayo", criatura_id=None)

    asyncio.run(vistas.NombreModal.on_submit(modal, Bandeja().interaccion()))

    guardada = db.por_id(activa.id)
    assert guardada.nombre == "Rayo" and guardada.se_nombro_solo is False


def test_bautizar_al_recluta_no_le_toca_el_nombre_al_activo(tmp_path, monkeypatch):
    """De aquí saldría el fallo: el modal buscaba «la activa», y el recluta
    no lo es."""
    activa, recluta = montar_plantel(tmp_path, monkeypatch)
    bandeja = Bandeja()

    async def publicar(canal, criatura, ahora):
        bandeja.publicadas.append(criatura)

    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    modal = SimpleNamespace(nombre="Pelusa", criatura_id=recluta.id)

    asyncio.run(vistas.NombreModal.on_submit(modal, bandeja.interaccion()))

    assert db.por_id(recluta.id).nombre == "Pelusa"
    assert db.criatura_activa("u1", "g1").nombre == activa.nombre
    # Y no se publica su ficha: no es el activo, no es la que se cuida.
    assert bandeja.publicadas == []


def test_bautizado_el_recluta_se_puede_sacar(tmp_path, monkeypatch):
    _, recluta = montar_plantel(tmp_path, monkeypatch)
    bandeja = Bandeja()
    monkeypatch.setattr(vistas, "publicar_pantalla", AsyncMock())
    modal = SimpleNamespace(nombre="Pelusa", criatura_id=recluta.id)

    asyncio.run(vistas.NombreModal.on_submit(modal, bandeja.interaccion()))

    assert db.activar(recluta.id, "u1", "g1")
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

    assert db.por_id(recluta.id).nombre == "Brote"
    assert bandeja.enviados == [
        ("Ya no tienes ningún gachamon vivo.", {"ephemeral": True})
    ]


def test_el_modal_del_recluta_bautiza_con_la_regla_del_juego(tmp_path, monkeypatch):
    _, recluta = montar_plantel(tmp_path, monkeypatch)
    bandeja = Bandeja()
    monkeypatch.setattr(vistas, "publicar_pantalla", AsyncMock())
    regla = Mock(wraps=nacer.bautizar_a)
    monkeypatch.setattr(vistas.nacer, "bautizar_a", regla)
    modal = SimpleNamespace(nombre="Pelusa", criatura_id=recluta.id)

    asyncio.run(vistas.NombreModal.on_submit(modal, bandeja.interaccion()))

    regla.assert_called_once_with("u1", "g1", recluta.id, "Pelusa", db.ahora_utc())
    assert db.por_id(recluta.id).nombre == "Pelusa"
    assert bandeja.editado == {"view": None}
    assert bandeja.enviados == [("✨ <@u1> la ha llamado **Pelusa**.", {})]


def test_el_modal_del_recluta_enviado_dos_veces_dice_que_ya_tiene_nombre(
    tmp_path, monkeypatch
):
    """Un formulario abierto dos veces no le pisa el nombre al primero."""
    _, recluta = montar_plantel(tmp_path, monkeypatch)
    bandeja = Bandeja()
    monkeypatch.setattr(vistas, "publicar_pantalla", AsyncMock())

    for nombre in ("Pelusa", "Otro"):
        modal = SimpleNamespace(nombre=nombre, criatura_id=recluta.id)
        asyncio.run(vistas.NombreModal.on_submit(modal, bandeja.interaccion()))

    assert db.por_id(recluta.id).nombre == "Pelusa"
    assert bandeja.enviados[-1] == (
        "Ese gachamon ya tiene nombre.", {"ephemeral": True}
    )


def test_el_modal_del_recluta_no_acepta_el_nombre_de_su_especie(
    tmp_path, monkeypatch
):
    _, recluta = montar_plantel(tmp_path, monkeypatch)
    bandeja = Bandeja()
    modal = SimpleNamespace(
        nombre=recluta.def_especie.nombre, criatura_id=recluta.id
    )

    asyncio.run(vistas.NombreModal.on_submit(modal, bandeja.interaccion()))

    assert db.por_id(recluta.id).nombre == "Brote"
    assert bandeja.enviados == [(
        "Nombre no válido. Ese es el nombre de su especie. Ponle uno propio.",
        {"ephemeral": True},
    )]


def test_el_boton_ya_publicado_busca_al_mas_antiguo_que_se_nombro_solo(
    tmp_path, monkeypatch
):
    """Es lo que hace la vista vieja, la de los botones publicados antes de
    que cada uno llevara el id de su recluta. El que tiene el nombre que le
    puso su dueño no cuenta; de los que se lo pusieron solos, el más antiguo,
    aunque el otro sea el activo."""
    ahora = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(db, "RUTA", tmp_path / "prueba.db")
    db.inicializar()
    db.crear("u1", "g1", "pulpo", "Vieja", (15, 15, 15, 15), ahora)
    primero, segundo = (
        nacer.unir_recluta(
            "u1", "g1", especie="michi", stats=(15, 15, 15, 15),
            genero=esp.MACHO, caracter=esp.CARACTER_POR_DEFECTO, ahora=ahora,
            rng=random.Random(semilla),
        )
        for semilla in (1, 2)
    )
    assert db.activar(segundo.id, "u1", "g1")

    encontrado = vistas.el_que_se_nombro_solo("u1", "g1")

    assert encontrado is not None and encontrado.id == primero.id
    assert vistas.el_que_se_nombro_solo("u2", "g1") is None
