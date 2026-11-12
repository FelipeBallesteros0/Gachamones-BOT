"""La cuenta de juego: empezar de cero o vincular con Discord.

Quién eres sale de la sesión y de `db.cuenta_web`, nunca de la petición.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends

import config
import db
import vinculo
from web.sesion import Persona, con_cabecera, persona_actual, problema

router = APIRouter()


@dataclass(frozen=True)
class Jugador:
    persona: Persona
    usuario_id: str
    guild_id: str
    vinculada: bool


def jugador_actual(persona: Persona = Depends(persona_actual)) -> Jugador:
    cuenta = db.cuenta_web(persona.rowino_uid)
    if cuenta is None:
        raise problema(
            409, "sin_cuenta", "Primero tienes que elegir cómo empezar a jugar.",
        )
    return Jugador(persona, cuenta.usuario_id, cuenta.guild_id, cuenta.vinculada)


def _estado(persona: Persona) -> dict:
    cuenta = db.cuenta_web(persona.rowino_uid)
    if cuenta is None:
        return {"usuario": persona.usuario, "estado": "nueva",
                "tiene_gachamones": False}
    return {
        "usuario": persona.usuario,
        "estado": "vinculada" if cuenta.vinculada else "web",
        "tiene_gachamones": db.tiene_gachamones(cuenta.usuario_id, cuenta.guild_id),
    }


def _pueblo() -> str:
    if not config.GUILD_WEB:
        raise problema(
            503, "sin_pueblo", "El juego no está disponible en este momento.",
        )
    return str(config.GUILD_WEB)


@router.get("/cuenta")
def ver_cuenta(persona: Persona = Depends(persona_actual)) -> dict:
    return _estado(persona)


@router.post("/cuenta/empezar", dependencies=[Depends(con_cabecera)])
def empezar(persona: Persona = Depends(persona_actual)) -> dict:
    pueblo = _pueblo()
    # Idempotente: si ya hay identidad, de cualquier tipo, no cambia nada.
    db.crear_identidad_web(persona.rowino_uid, pueblo, db.ahora_utc())
    return _estado(persona)


@router.post("/cuenta/codigo", dependencies=[Depends(con_cabecera)])
def pedir_codigo(persona: Persona = Depends(persona_actual)) -> dict:
    _pueblo()
    try:
        codigo = db.pedir_codigo_de_vinculo(persona.rowino_uid, db.ahora_utc())
    except vinculo.NoSePuede as error:
        if error.motivo == vinculo.YA_VINCULADA:
            raise problema(
                409, "ya_vinculada",
                "Esta cuenta ya está unida a tu Discord.",
            ) from None
        raise problema(
            409, "con_gachamones",
            "Ya empezaste a jugar aquí, y dos grupos de gachamones no se "
            "pueden juntar.",
        ) from None
    return {"codigo": codigo, "minutos": vinculo.MINUTOS_DE_VIDA}
