"""La Incubadora del pueblo: tu plantel entero y sacar a otro gachamon.

Ver el plantel sólo lee: lista a los vivos, cada uno al día (lo único que
puede escribir una lectura es el remiendo: poner a uno de activo si no hay
ninguno). Sacar es un adaptador
fino: valida la petición, comprueba que se está en la incubadora y llama a la
regla de `economia`, que decide y escribe bajo `BEGIN IMMEDIATE`; aquí sólo se
traduce lo que pasó a una frase de la web, en texto llano. Un «no» del juego no
es un error HTTP: es `ok: false` con su clave. Ponerle nombre a un recluta va
por `POST /bautizar` con su `gachamon_id`.

Ojo: este módulo es `web.incubadora`; no importa `discord` ni nada que lo importe.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends

import db
import economia
import especies as esp
import simulacion as sim
from web import estado, pueblo
from web.cuenta import Jugador, jugador_actual
from web.salir import dicho_de_salir
from web.sesion import con_cabecera, es_un_id, problema

router = APIRouter()

def en_la_incubadora(jugador: Jugador) -> None:
    """Para sacar a otro hay que estar en la incubadora: lo dice el lugar guardado de la cuenta.

    El lugar que falta o que ya no existe se resuelve como en el estado: tu casa.
    """
    clave = pueblo.donde_esta(db.lugar_de_cuenta(jugador.persona.rowino_uid))
    if "incubadora" not in pueblo.ofrece(clave):
        raise problema(409, "no_estas_ahi", "Para eso tienes que estar en la incubadora.")


def _del_plantel(criatura: sim.Criatura) -> dict:
    return {
        "id": criatura.id,
        "nombre": criatura.nombre,
        "nombre_especie": criatura.def_especie.nombre,
        "nombre_etapa": esp.nombre_etapa(criatura.etapa, criatura.genero),
        "nivel": criatura.nivel,
        "retrato": estado.retrato_de(criatura),
        "activo": criatura.activa,
    }


def el_plantel(jugador: Jugador, ahora: datetime) -> dict:
    """Los vivos de la cuenta, la activa primero y luego por id, y cuántos caben.

    Caben las camas puestas menos la tuya, y nunca menos de los que ya tiene:
    el que nació del huevo todavía no tiene su cama. Cada uno tal como está
    ahora, con la cara que tiene a esta hora.
    """
    # El remiendo, si no hay activa; lo que devuelve ya viene en el plantel.
    db.activa_al_dia(jugador.usuario_id, jugador.guild_id, ahora)
    vivos = db.plantel_al_dia(jugador.usuario_id, jugador.guild_id, ahora)
    camas = db.departamento_leido(
        jugador.usuario_id, jugador.guild_id
    ).camas_puestas
    dinero = economia.saldos(jugador.usuario_id, jugador.guild_id)
    return {
        "plantel": [_del_plantel(c) for c in vivos],
        "maximo": max(len(vivos), camas - 1),
        "saldos": {"monedas": dinero.asciicoins, "gemas": dinero.asciigems},
    }


@router.get("/incubadora")
def ver_la_incubadora(jugador: Jugador = Depends(jugador_actual)) -> dict:
    return el_plantel(jugador, db.ahora_utc())


@router.post("/incubadora/sacar", dependencies=[Depends(con_cabecera)])
def sacar(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    # El cuerpo se revisa a mano; la cuenta sale sólo de la cookie, y el
    # `gachamon_id` es el que enseña la pantalla: la regla mira que sea tuyo.
    datos = cuerpo if isinstance(cuerpo, dict) else {}
    gachamon_id = datos.get("gachamon_id")
    if not es_un_id(gachamon_id):
        raise problema(422, "peticion", "La petición no se entiende.")
    en_la_incubadora(jugador)
    ahora = db.ahora_utc()
    hecho = economia.cambiar_de_activo(jugador.usuario_id, jugador.guild_id, gachamon_id, ahora)
    return {
        **dicho_de_salir(hecho),
        "incubadora": el_plantel(jugador, ahora),
        "estado": estado.armar(jugador, ahora),
    }
