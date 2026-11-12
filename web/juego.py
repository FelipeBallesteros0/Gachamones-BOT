"""Lo que se lee y se hace jugando: el estado y, más adelante, el cuidado."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

import db
import nacer
from web import estado
from web.cuenta import Jugador, jugador_actual
from web.sesion import con_cabecera, problema

router = APIRouter()


@router.get("/estado")
def ver_estado(jugador: Jugador = Depends(jugador_actual)) -> dict:
    return estado.armar(jugador, db.ahora_utc())


@router.post("/difunto/visto", dependencies=[Depends(con_cabecera)])
def difunto_visto(jugador: Jugador = Depends(jugador_actual)) -> dict:
    # Sólo se da por visto lo que ya estaba a la vista: una muerte que se
    # descubra al armar el estado de esta misma petición se enseña antes.
    pendiente = db.difunto_pendiente(jugador.persona.rowino_uid)
    if pendiente is not None:
        db.marcar_difuntos_vistos(jugador.persona.rowino_uid, pendiente.muerta_en)
    return estado.armar(jugador, db.ahora_utc())


@router.post("/huevo", status_code=201, dependencies=[Depends(con_cabecera)])
def romper_el_huevo(jugador: Jugador = Depends(jugador_actual)) -> dict:
    if db.avatar_de(jugador.usuario_id, jugador.guild_id) is None:
        raise problema(409, "sin_avatar", "Primero crea tu avatar.")
    ahora = db.ahora_utc()
    try:
        nacer.romper_el_huevo(jugador.usuario_id, jugador.guild_id, ahora)
    except nacer.YaTieneGachamon:
        raise problema(
            409, "ya_tienes",
            "Ya tienes un gachamon. El huevo es sólo el de partida.",
        ) from None
    except nacer.YaNoEsSuIdentidad:
        raise problema(
            409, "cuenta_cambio",
            "Tu cuenta cambió mientras tanto. Vuelve a entrar.",
        ) from None
    return estado.armar(jugador, ahora)


@router.post("/bautizar", dependencies=[Depends(con_cabecera)])
def bautizar(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    # El cuerpo se revisa a mano: así todo fallo sale con nuestra forma.
    nombre = cuerpo.get("nombre") if isinstance(cuerpo, dict) else None
    if not isinstance(nombre, str):
        raise problema(422, "nombre", "Falta el nombre.")
    ahora = db.ahora_utc()
    try:
        nacer.bautizar(jugador.usuario_id, jugador.guild_id, nombre, ahora)
    except nacer.NombreNoVale as error:
        raise problema(422, "nombre", str(error)) from None
    except nacer.NoSePuedeBautizar as error:
        raise problema(409, error.motivo, str(error)) from None
    return estado.armar(jugador, ahora)
