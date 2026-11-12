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
    # Sólo se da por visto lo que ya estaba a la vista: una muerte que se
    # descubra al armar el estado de esta misma petición se enseña antes.
    pendiente = db.difunto_pendiente(jugador.persona.rowino_uid)
    if pendiente is not None:
        db.marcar_difuntos_vistos(jugador.persona.rowino_uid, pendiente.muerta_en)
    return estado.armar(jugador, db.ahora_utc())
