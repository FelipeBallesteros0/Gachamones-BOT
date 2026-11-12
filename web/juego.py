"""Lo que se lee y se hace jugando: el estado y, más adelante, el cuidado."""
from __future__ import annotations

from fastapi import APIRouter, Depends

import db
from web import estado
from web.cuenta import Jugador, jugador_actual
from web.sesion import con_cabecera

router = APIRouter()


@router.get("/estado")
def ver_estado(jugador: Jugador = Depends(jugador_actual)) -> dict:
    return estado.armar(jugador, db.ahora_utc())


@router.post("/difunto/visto", dependencies=[Depends(con_cabecera)])
def difunto_visto(jugador: Jugador = Depends(jugador_actual)) -> dict:
    ahora = db.ahora_utc()
    db.marcar_difuntos_vistos(jugador.persona.rowino_uid, ahora)
    return estado.armar(jugador, ahora)
