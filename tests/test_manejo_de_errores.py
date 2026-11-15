"""Que un comando roto conteste siempre.

Discord deja el «pensando…» girando hasta que alguien responde la interacción.
Si un comando difiere y luego revienta, y el manejador se limita a relanzar el
error, quien juega se queda mirando un reloj para siempre — que es justo lo que
pasó con `/jardin`.
"""
import asyncio
import logging
from types import SimpleNamespace

import pytest
from discord import app_commands

import comun
import config
from cogs import mudanza


class RespuestaFalsa:
    """Anota lo que se le habría contestado, sin hablar con Discord.

    `avisos` es todo lo contestado, salga por donde salga; `enviados`, sólo lo
    que salió por aquí, con si era privado.
    """

    def __init__(self, ya_diferida=False):
        self.avisos = []
        self.enviados = []
        self._diferida = ya_diferida

    def is_done(self):
        return self._diferida or bool(self.avisos)

    async def send_message(self, contenido="", **kw):
        self.avisos.append(str(contenido))
        self.enviados.append((str(contenido), kw.get("ephemeral", False)))


class SeguimientoFalso:
    def __init__(self, avisos):
        self.avisos = avisos
        self.enviados = []

    async def send(self, contenido="", **kw):
        self.avisos.append(str(contenido))
        self.enviados.append((str(contenido), kw.get("ephemeral", False)))


def interaccion_falsa(ya_diferida=False, guild_id=None, guild=None):
    respuesta = RespuestaFalsa(ya_diferida)
    return SimpleNamespace(
        response=respuesta,
        followup=SeguimientoFalso(respuesta.avisos),
        channel_id=1,
        guild_id=guild_id,
        guild=guild,
        user=SimpleNamespace(id=555),
    )


def servidor_que_ve(*canales):
    """Un servidor de Discord de mentira que sólo conoce esos canales."""
    return SimpleNamespace(
        get_channel=lambda cid: SimpleNamespace(id=cid) if cid in canales else None
    )


def manejar(error, ya_diferida=False, **donde):
    interaccion = interaccion_falsa(ya_diferida, **donde)
    return interaccion, asyncio.run(comun.manejar_error(interaccion, error))


# --- Lo que ya se contestaba -----------------------------------------------

def test_el_canal_equivocado_se_explica(monkeypatch):
    monkeypatch.setattr(config, "CANALES", (111, 222))
    interaccion, _ = manejar(comun.CanalEquivocado())
    assert interaccion.response.avisos == ["Escríbeme en <#111>, <#222>."]


def test_escribeme_en_nombra_solo_los_canales_de_ese_servidor(monkeypatch):
    """Con el bot en más de un servidor, el canal de otro es desde aquí un
    enlace a ninguna parte."""
    monkeypatch.setattr(config, "CANALES", (111, 222))
    interaccion, _ = manejar(comun.CanalEquivocado(), guild=servidor_que_ve(222))
    assert interaccion.response.avisos == ["Escríbeme en <#222>."]


def test_si_no_ve_ninguno_de_sus_canales_los_nombra_todos(monkeypatch):
    monkeypatch.setattr(config, "CANALES", (111, 222))
    interaccion, _ = manejar(comun.CanalEquivocado(), guild=servidor_que_ve())
    assert interaccion.response.avisos == ["Escríbeme en <#111>, <#222>."]


def test_el_enfriamiento_dice_cuánto_falta():
    error = app_commands.CommandOnCooldown(cooldown=None, retry_after=42.0)
    interaccion, _ = manejar(error)
    assert "42" in interaccion.response.avisos[0]


def test_si_ya_se_contesto_el_aviso_va_por_el_seguimiento(monkeypatch):
    """Una interacción ya contestada o diferida no admite otra respuesta: el
    aviso tiene que ir por `followup`, o Discord lo rechaza."""
    monkeypatch.setattr(config, "CANALES", (111,))
    interaccion, _ = manejar(comun.CanalEquivocado(), ya_diferida=True)
    assert interaccion.followup.enviados == [("Escríbeme en <#111>.", True)]
    assert interaccion.response.enviados == []


# --- Un comando que ya no existe --------------------------------------------
# Si la sincronización de un servidor falla al arrancar, allí siguen
# registrados los comandos del juego de antes, y discord.py los entrega como
# `CommandNotFound`.

def test_un_comando_que_ya_no_existe_contesta_el_aviso_de_la_mudanza(monkeypatch, caplog):
    monkeypatch.setattr(config, "GUILD_WEB", 4040)
    error = app_commands.CommandNotFound("tienda", [])
    with caplog.at_level(logging.WARNING):
        interaccion, _ = manejar(error, guild_id=4040)   # no lanza

    assert interaccion.response.enviados == [(mudanza.AVISO, True)]
    (aviso,) = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert aviso.name == "comun" and "tienda" in aviso.getMessage()
    assert "555" not in aviso.getMessage()   # el id de quien lo escribió


def test_en_otro_servidor_el_comando_que_ya_no_existe_avisa_de_la_pausa(monkeypatch):
    monkeypatch.setattr(config, "GUILD_WEB", 4040)
    error = app_commands.CommandNotFound("tienda", [])
    interaccion, _ = manejar(error, guild_id=4041)   # no lanza
    assert interaccion.response.enviados == [(mudanza.AVISO_SIN_PAGINA, True)]


# --- Lo que dejaba colgado -------------------------------------------------

def test_un_error_inesperado_contesta_igual():
    """**El fallo de `/jardin`.** El comando difirió, reventó al enviar y el
    manejador sólo relanzaba: nadie contestó y el «pensando…» se quedó girando.

    Ahora se contesta primero y se relanza después, así que el error sigue
    saliendo en el registro pero quien juega recibe algo.
    """
    interaccion = interaccion_falsa(ya_diferida=True)
    with pytest.raises(ValueError):
        asyncio.run(comun.manejar_error(interaccion, ValueError("reventón")))
    assert interaccion.response.avisos, "no se contestó la interacción"


def test_el_error_inesperado_se_sigue_relanzando():
    """Contestar no puede tragarse el error: si dejara de propagarse, el fallo
    desaparecería del registro y nos quedaríamos sin saber qué se rompió."""
    interaccion = interaccion_falsa()
    with pytest.raises(RuntimeError, match="el de verdad"):
        asyncio.run(comun.manejar_error(interaccion, RuntimeError("el de verdad")))


def test_el_aviso_no_delata_las_tripas():
    """Lo que ve quien juega no puede ser una traza ni un mensaje de librería."""
    interaccion = interaccion_falsa(ya_diferida=True)
    with pytest.raises(KeyError):
        asyncio.run(comun.manejar_error(interaccion, KeyError("tabla_secreta")))
    aviso = interaccion.response.avisos[0].lower()
    assert "tabla_secreta" not in aviso
    for fea in ("traceback", "keyerror", "exception", "none"):
        assert fea not in aviso
