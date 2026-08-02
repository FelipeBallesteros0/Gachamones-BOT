"""Que un comando roto conteste siempre.

Discord deja el «pensando…» girando hasta que alguien responde la interacción.
Si un comando difiere y luego revienta, y el manejador se limita a relanzar el
error, quien juega se queda mirando un reloj para siempre — que es justo lo que
pasó con `/jardin`.
"""
import asyncio
from types import SimpleNamespace

import pytest
from discord import app_commands

import comun


class RespuestaFalsa:
    """Anota lo que se le habría contestado, sin hablar con Discord."""

    def __init__(self, ya_diferida=False):
        self.avisos = []
        self._diferida = ya_diferida

    def is_done(self):
        return self._diferida or bool(self.avisos)

    async def send_message(self, contenido="", **kw):
        self.avisos.append(str(contenido))


class SeguimientoFalso:
    def __init__(self, avisos):
        self.avisos = avisos

    async def send(self, contenido="", **kw):
        self.avisos.append(str(contenido))


def interaccion_falsa(ya_diferida=False):
    respuesta = RespuestaFalsa(ya_diferida)
    return SimpleNamespace(
        response=respuesta,
        followup=SeguimientoFalso(respuesta.avisos),
        channel_id=1,
    )


def manejar(error, ya_diferida=False):
    interaccion = interaccion_falsa(ya_diferida)
    return interaccion, asyncio.run(comun.manejar_error(interaccion, error))


# --- Lo que ya se contestaba -----------------------------------------------

def test_el_canal_equivocado_se_explica():
    interaccion, _ = manejar(comun.CanalEquivocado())
    assert interaccion.response.avisos
    assert "viven en" in interaccion.response.avisos[0]


def test_el_enfriamiento_dice_cuánto_falta():
    error = app_commands.CommandOnCooldown(cooldown=None, retry_after=42.0)
    interaccion, _ = manejar(error)
    assert "42" in interaccion.response.avisos[0]


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
