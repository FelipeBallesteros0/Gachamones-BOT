"""El ropero: poner y quitar el sombrero y el título del gachamon que se está viendo.

Ver el ropero sólo lee. Poner y quitar son adaptadores finos: validan la
petición, comprueban que el gachamon es el que enseñaba la pantalla y llaman a
la regla de `economia` (que decide todo y escribe bajo `BEGIN IMMEDIATE`); aquí
sólo se traduce lo que pasó a una frase de la web, en texto llano. Un «no» del
juego no es un error HTTP: es `ok: false` con su clave.

Ojo: este módulo es `web.ropero`; no importa `discord` ni nada que lo importe.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

import cosmeticos as cos
import db
import economia
import simulacion as sim
from web import estado
from web.cuenta import Jugador, jugador_actual, la_misma_activa
from web.sesion import con_cabecera, es_un_id, problema
from web.tienda import dicho_no, dicho_si, no_se_entiende

router = APIRouter()

_SIN_GACHAMON = "No tienes un gachamon que vestir."
_YA_NO_ES_EL_MISMO = "Tu gachamon ya no es el mismo. Mira otra vez."
_COMO_SE_DICE = {cos.SOMBRERO: "sombrero", cos.TITULO: "título"}


def lo_que_tienes(jugador: Jugador, ahora) -> dict:
    """Las piezas del ropero que siguen en el catálogo, y dónde está cada una."""
    activo = db.activa_al_dia(jugador.usuario_id, jugador.guild_id, ahora)
    if activo is None:
        raise problema(409, "sin_gachamon", _SIN_GACHAMON)
    tengo = db.ropero(jugador.usuario_id, jugador.guild_id)
    llevan = db.quien_lleva_cada(jugador.usuario_id, jugador.guild_id)
    piezas = []
    for pieza in cos.CATALOGO.values():
        if pieza.clave not in tengo:
            continue
        puesta = getattr(activo, pieza.tipo) == pieza.clave
        piezas.append({
            "clave": pieza.clave, "nombre": pieza.nombre, "tipo": pieza.tipo,
            "puesta": puesta,
            "lo_lleva": None if puesta else llevan.get(pieza.clave),
        })
    dinero = economia.saldos(jugador.usuario_id, jugador.guild_id)
    return {
        "gachamon": {"id": activo.id, "nombre": sim.nombre_visible(activo)},
        "piezas": piezas,
        "saldos": {"monedas": dinero.asciicoins, "gemas": dinero.asciigems},
    }


@router.get("/ropero")
def ver_el_ropero(jugador: Jugador = Depends(jugador_actual)) -> dict:
    return lo_que_tienes(jugador, db.ahora_utc())


def _gachamon_id(datos: dict) -> int:
    gachamon_id = datos.get("gachamon_id")
    if not es_un_id(gachamon_id):
        raise no_se_entiende()
    return gachamon_id


def _respuesta(dicho: dict, jugador: Jugador, ahora) -> dict:
    return {**dicho, "ropero": lo_que_tienes(jugador, ahora), "estado": estado.armar(jugador, ahora)}


def _quien(hecho: economia.ResultadoCosmetico) -> sim.Criatura:
    """La criatura a la que se aplicó; si la regla no trae a quién, no hay de quién hablar."""
    if hecho.criatura is None:
        raise problema(409, "sin_gachamon", _YA_NO_ES_EL_MISMO)
    return hecho.criatura


def _ya_puesta(pieza: cos.Cosmetico, criatura: sim.Criatura, sustituido=None) -> dict:
    nombre = sim.nombre_visible(criatura)
    if pieza.tipo == cos.TITULO:
        frase = f"Ahora es {nombre} {cos.texto_del_titulo(pieza.clave, criatura.genero)}."
    else:
        frase = f"{nombre} ya lleva {pieza.nombre}."
    if sustituido is not None:
        frase += f" {sustituido.nombre} vuelve a tu ropero."
    return dicho_si(frase)


@router.post("/ropero/poner", dependencies=[Depends(con_cabecera)])
def poner(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    datos = cuerpo if isinstance(cuerpo, dict) else {}
    clave, gachamon_id = datos.get("clave"), _gachamon_id(datos)
    pieza = cos.CATALOGO.get(clave) if isinstance(clave, str) else None
    if pieza is None:
        raise no_se_entiende()
    ahora = db.ahora_utc()
    la_misma_activa(jugador, ahora, _SIN_GACHAMON)
    hecho = economia.equipar_cosmetico(
        jugador.usuario_id, jugador.guild_id, pieza, criatura_id=gachamon_id
    )
    if hecho.motivo == "sin_gachamon":
        raise problema(409, "sin_gachamon", _YA_NO_ES_EL_MISMO)
    if hecho.ok:
        dicho = _ya_puesta(pieza, _quien(hecho), hecho.sustituido)
    elif hecho.motivo == "ya_lo_lleva":
        dicho = _ya_puesta(pieza, _quien(hecho))
    elif hecho.motivo == "lo_lleva_otro":
        dicho = dicho_no("lo_lleva_otro", f"{pieza.nombre}: lo lleva {hecho.lo_lleva}. Quítaselo primero.")
    elif hecho.motivo == "no_lo_tienes":
        dicho = dicho_no("no_lo_tienes", f"Ya no tienes {pieza.nombre}.")
    else:
        # Un motivo que no conocemos es un fallo nuestro y no se disfraza.
        raise RuntimeError(f"poner sin frase: {hecho.motivo!r}")
    return _respuesta(dicho, jugador, ahora)


@router.post("/ropero/quitar", dependencies=[Depends(con_cabecera)])
def quitar(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    datos = cuerpo if isinstance(cuerpo, dict) else {}
    tipo, gachamon_id = datos.get("tipo"), _gachamon_id(datos)
    if not isinstance(tipo, str) or tipo not in cos.TIPOS:
        raise no_se_entiende()
    ahora = db.ahora_utc()
    la_misma_activa(jugador, ahora, _SIN_GACHAMON)
    hecho = economia.quitar_cosmetico(
        jugador.usuario_id, jugador.guild_id, tipo, criatura_id=gachamon_id
    )
    if hecho.motivo == "sin_gachamon":
        raise problema(409, "sin_gachamon", _YA_NO_ES_EL_MISMO)
    nombre = sim.nombre_visible(_quien(hecho))
    if hecho.ok:
        dicho = dicho_si(f"{nombre} ya no lleva {hecho.sustituido.nombre}. Está en tu ropero.")
    elif hecho.motivo == "no_lleva_nada":
        dicho = dicho_si(f"{nombre} no lleva ningún {_COMO_SE_DICE[tipo]}.")
    else:
        raise RuntimeError(f"quitar sin frase: {hecho.motivo!r}")
    return _respuesta(dicho, jugador, ahora)
