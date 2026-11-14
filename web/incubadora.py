"""La Incubadora del pueblo: tu plantel entero y sacar a otro gachamon.

Ver el plantel sólo lee: pone la activa al día (lo único que escribe una
lectura es la muerte que descubre) y lista a los vivos. Sacar es un adaptador
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
from web.sesion import con_cabecera, problema

router = APIRouter()

_NO_ESTA = "Ese gachamon ya no está."


def en_la_incubadora(jugador: Jugador) -> None:
    """Para sacar a otro hay que estar en la incubadora: lo dice el lugar guardado de la cuenta.

    Un lugar guardado que ya no existe se resuelve como en el estado (se vuelve
    al hogar, que no ofrece nada); por eso basta con mirar el lugar si existe.
    """
    clave = db.lugar_de_cuenta(jugador.persona.rowino_uid)
    if not pueblo.existe(clave) or "incubadora" not in pueblo.ofrece(clave):
        raise problema(409, "no_estas_ahi", "Para eso tienes que estar en la incubadora.")


def _del_plantel(criatura: sim.Criatura) -> dict:
    return {
        "id": criatura.id,
        "nombre": criatura.nombre,
        "sin_nombre": sim.esta_sin_nombrar(criatura),
        "nombre_especie": criatura.def_especie.nombre,
        "nombre_etapa": esp.nombre_etapa(criatura.etapa, criatura.genero),
        "nivel": criatura.nivel,
        "retrato": estado.retrato_de(criatura),
        "activo": criatura.activa,
    }


def el_plantel(jugador: Jugador, ahora: datetime) -> dict:
    """Los vivos de la cuenta, la activa primero y luego por id, y cuántos caben."""
    activa = db.activa_al_dia(jugador.usuario_id, jugador.guild_id, ahora)
    vivos = db.plantel(jugador.usuario_id, jugador.guild_id)
    # La activa, tal como está ahora: con la cara que se le ve en el estado.
    if activa is not None:
        vivos = [activa if c.id == activa.id else c for c in vivos]
    dinero = economia.saldos(jugador.usuario_id, jugador.guild_id)
    return {
        "plantel": [_del_plantel(c) for c in vivos],
        "maximo": db.MAXIMO_PLANTEL,
        "saldos": {"monedas": dinero.asciicoins, "gemas": dinero.asciigems},
    }


@router.get("/incubadora")
def ver_la_incubadora(jugador: Jugador = Depends(jugador_actual)) -> dict:
    return el_plantel(jugador, db.ahora_utc())


def _dicho(hecho: economia.ResultadoCambio) -> dict:
    if hecho.ok:
        return {"ok": True, "clave": None, "mensaje": f"{sim.nombre_visible(hecho.criatura)} sale de la incubadora."}
    if hecho.motivo == "ya_es_el_activo":
        # Lo que ya está como se pidió es un sí: un toque doble no enseña un error.
        return {
            "ok": True, "clave": None,
            "mensaje": f"{sim.nombre_visible(hecho.criatura)} ya es tu gachamon activo.",
        }
    if hecho.motivo == "sin_nombre":
        return {"ok": False, "clave": "sin_nombre", "mensaje": "Antes de sacarlo, ponle nombre."}
    if hecho.motivo == "no_esta":
        return {"ok": False, "clave": "no_esta", "mensaje": _NO_ESTA}
    # Un motivo que no conocemos es un fallo nuestro y no se disfraza.
    raise RuntimeError(f"sacar sin frase: {hecho.motivo!r}")


@router.post("/incubadora/sacar", dependencies=[Depends(con_cabecera)])
def sacar(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    # El cuerpo se revisa a mano; la cuenta sale sólo de la cookie, y el
    # `gachamon_id` es el que enseña la pantalla: la regla mira que sea tuyo.
    datos = cuerpo if isinstance(cuerpo, dict) else {}
    gachamon_id = datos.get("gachamon_id")
    if type(gachamon_id) is not int:   # ni un texto, ni un decimal, ni `true`
        raise problema(422, "peticion", "La petición no se entiende.")
    en_la_incubadora(jugador)
    ahora = db.ahora_utc()
    # Si al ponerlo al día murió el activo, el cambio sigue: el `estado` trae
    # al difunto y la pantalla decide.
    hecho = economia.cambiar_de_activo(jugador.usuario_id, jugador.guild_id, gachamon_id, ahora)
    return {
        **_dicho(hecho),
        "incubadora": el_plantel(jugador, ahora),
        "estado": estado.armar(jugador, ahora),
    }
