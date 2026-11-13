"""Lo que se lee y se hace jugando: el estado, el huevo, el bautizo, los
cuidados y la caricia."""
from __future__ import annotations

import logging
import math
import re
from typing import Any

from fastapi import APIRouter, Body, Depends

import db
import economia
import nacer
import simulacion as sim
from web import estado, pueblo
from web.cuenta import Jugador, jugador_actual, la_misma_activa
from web.sesion import con_cabecera, problema

log = logging.getLogger("gachamones")
router = APIRouter()

EVENTO_VALIDO = re.compile(r"[A-Za-z0-9-]{8,64}")


def _segundos(espera) -> int:
    """Una espera en segundos enteros, hacia arriba; 0 si no hay."""
    return math.ceil(espera.total_seconds()) if espera else 0


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
        if db.criatura_activa(jugador.usuario_id, jugador.guild_id) is None:
            # Ninguna activa, pero hay alguien: un recluta sin nombre, que sólo
            # se bautiza en Discord. Sin esto el huevo se repetiría para siempre.
            raise problema(
                409, "ya_tienes",
                "Tienes un gachamon esperando nombre en la incubadora. "
                "Ponle nombre en Discord y vuelve.",
            ) from None
        raise problema(
            409, "ya_tienes",
            "Ya tienes un gachamon. El huevo es sólo el de partida.",
        ) from None
    except nacer.YaNoEsSuIdentidad:
        raise problema(
            409, "cuenta_cambio",
            "Tu cuenta cambió mientras tanto. Vuelve a entrar.",
        ) from None
    # Como en Discord: al nacer se miran las medallas de la persona (una rara).
    economia.pagar_logros_de_persona(jugador.usuario_id, jugador.guild_id, ahora)
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


@router.post("/lugar", dependencies=[Depends(con_cabecera)])
def ir_a_un_lugar(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    # El cuerpo se revisa a mano; la cuenta sale sólo de la cookie.
    lugar = cuerpo.get("lugar") if isinstance(cuerpo, dict) else None
    if not pueblo.existe(lugar):
        raise problema(422, "lugar", "Ese lugar no existe.")
    db.poner_lugar(jugador.persona.rowino_uid, lugar)
    return estado.armar(jugador, db.ahora_utc())


@router.post("/cuidar", dependencies=[Depends(con_cabecera)])
def cuidar(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    # El cuerpo se revisa a mano; la identidad sale sólo de la cookie.
    datos = cuerpo if isinstance(cuerpo, dict) else {}
    accion = datos.get("accion")
    if not isinstance(accion, str) or accion not in sim.ACCIONES_DE_CUIDADO:
        raise problema(422, "accion", "Esa acción no existe.")
    evento = datos.get("evento_id")
    if not isinstance(evento, str) or not EVENTO_VALIDO.fullmatch(evento):
        raise problema(422, "evento", "Ese identificador de evento no vale.")
    ahora = db.ahora_utc()
    sin_gachamon = "No tienes un gachamon que cuidar."
    la_misma_activa(jugador, ahora, sin_gachamon)
    try:
        resultado = economia.ejecutar_cuidado(
            evento, jugador.usuario_id, jugador.guild_id, accion, ahora
        )
    except RuntimeError:
        log.warning("evento de cuidado reutilizado: %s", evento, exc_info=True)
        raise problema(
            409, "evento", "Ese cuidado ya se usó para otra acción."
        ) from None
    if resultado is None:
        raise problema(409, "sin_gachamon", sin_gachamon)
    # Como en Discord: un cuidado que sale bien termina pagando las medallas
    # nuevas, antes de armar el estado para que sus gemas ya vayan en el saldo.
    logros = []
    if resultado.ok:
        recibo = economia.pagar_logros(resultado.criatura, ahora)
        logros = [{"nombre": logro.nombre, "gemas": logro.gemas} for logro in recibo.nuevos]
    return {
        "ok": resultado.ok,
        "mensaje": resultado.mensaje or ("" if resultado.ok else "Todavía no."),
        "espera": _segundos(resultado.espera),
        "monedas": resultado.delta_asciicoins,
        "evoluciono": resultado.evoluciono,
        "logros": logros,
        "estado": estado.armar(jugador, ahora),
    }


@router.post("/acariciar", dependencies=[Depends(con_cabecera)])
def acariciar(jugador: Jugador = Depends(jugador_actual)) -> dict:
    ahora = db.ahora_utc()
    sin_gachamon = "No tienes un gachamon que acariciar."
    la_misma_activa(jugador, ahora, sin_gachamon)
    caricia = db.acariciar(jugador.usuario_id, jugador.guild_id, ahora)
    if caricia.criatura is None:
        raise problema(409, "sin_gachamon", sin_gachamon)
    return {
        "ok": caricia.ok,
        "espera": _segundos(caricia.espera),
        "estado": estado.armar(jugador, ahora),
    }
