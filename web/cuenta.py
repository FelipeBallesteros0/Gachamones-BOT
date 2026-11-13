"""La cuenta de juego: empezar de cero o vincular con Discord.

Quién eres sale de la sesión y de `db.cuenta_web`, nunca de la petición.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends

import avatar as av
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


def la_misma_activa(jugador: Jugador, ahora: datetime, sin_ninguno: str) -> None:
    """Que la acción le caiga al gachamon que el jugador estaba viendo.

    Se mira quién es la activa antes de ponerla al día y quién después: si se
    murió en esta misma petición, `activa_al_dia` saca al relevo, que el
    jugador todavía no ha visto, y no se le aplica nada. Una muerte la
    registra igual quien la deja apuntada para el bot.
    """
    antes = db.criatura_activa(jugador.usuario_id, jugador.guild_id)
    despues = db.activa_al_dia(jugador.usuario_id, jugador.guild_id, ahora)
    if antes is None and despues is None:
        raise problema(409, "sin_gachamon", sin_ninguno)
    if antes is None or despues is None or antes.id != despues.id:
        raise problema(
            409, "sin_gachamon", "Tu gachamon ya no es el mismo. Mira otra vez.",
        )


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
        if error.motivo == vinculo.CON_GACHAMONES:
            raise problema(
                409, "con_gachamones",
                "Ya empezaste a jugar aquí, y dos grupos de gachamones no se "
                "pueden juntar.",
            ) from None
        # Un motivo que esto no conoce es un fallo nuestro: no se disfraza.
        raise
    return {"codigo": codigo, "minutos": vinculo.MINUTOS_DE_VIDA}


_CAMPOS_DEL_AVATAR = (
    "nombre", "genero", "piel", "pelo", "color_de_pelo", "ropa",
)


@router.get("/avatar/opciones")
def opciones_del_avatar(persona: Persona = Depends(persona_actual)) -> dict:
    return {
        grupo: [{"clave": o.clave, "nombre": o.nombre} for o in lista]
        for grupo, lista in av.opciones().items()
    }


@router.put("/avatar", dependencies=[Depends(con_cabecera)])
def guardar_avatar(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    # El cuerpo se revisa a mano: así todo fallo sale con nuestra forma.
    if not isinstance(cuerpo, dict):
        raise problema(422, "avatar", "Faltan los datos del avatar.")
    faltan = [
        c for c in _CAMPOS_DEL_AVATAR if not isinstance(cuerpo.get(c), str)
    ]
    if faltan:
        raise problema(
            422, "avatar",
            "Faltan datos del avatar o no son texto: " + ", ".join(faltan) + ".",
        )
    try:
        hecho = av.crear(**{c: cuerpo[c] for c in _CAMPOS_DEL_AVATAR})
    except ValueError as error:
        raise problema(422, "avatar", str(error)) from None
    db.guardar_avatar(jugador.usuario_id, jugador.guild_id, hecho, db.ahora_utc())
    return asdict(hecho)
