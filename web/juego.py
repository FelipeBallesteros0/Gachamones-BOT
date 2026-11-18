"""Lo que se lee y se hace jugando: el estado, el bautizo, los cuidados y la
caricia. El primer gachamon se gana en la primera aventura (`web.aventura`)."""
from __future__ import annotations

import logging
import math
import re
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

import db
import economia
import nacer
import simulacion as sim
from web import estado, pueblo
from web.cuenta import Jugador, jugador_actual, la_misma_activa
from web.sesion import con_cabecera, es_un_id, problema

log = logging.getLogger("gachamones")
router = APIRouter()

EVENTO_VALIDO = re.compile(r"[A-Za-z0-9-]{8,64}")


def _segundos(espera) -> int:
    """Una espera en segundos enteros, hacia arriba; 0 si no hay."""
    return math.ceil(espera.total_seconds()) if espera else 0


def _elegido(datos: dict) -> int | None:
    """El `gachamon_id` del cuerpo, que dice a quién le cae la acción.

    Sin él, al activo, como siempre. Si viene y no es un id, la petición no se
    entiende.
    """
    if "gachamon_id" not in datos:
        return None
    gachamon_id = datos["gachamon_id"]
    if not es_un_id(gachamon_id):
        raise problema(422, "peticion", "La petición no se entiende.")
    return gachamon_id


def _nadie(gachamon_id: int | None, sin_gachamon: str) -> HTTPException:
    """El 409 de cuando el juego no encontró a quién aplicarle la acción."""
    if gachamon_id is None:
        return problema(409, "sin_gachamon", sin_gachamon)
    return problema(409, "no_esta", "Ese gachamon ya no está.")


@router.get("/estado")
def ver_estado(jugador: Jugador = Depends(jugador_actual)) -> dict:
    return estado.armar(jugador, db.ahora_utc())


def _pagar_las_medallas_del_primero(jugador: Jugador, ahora) -> None:
    """Las medallas de la persona, si lo que tiene es el primero de la primera
    aventura y todavía espera nombre (`nacer.es_el_primero_sin_nombre`, sobre el
    plantel vivo de ahora: la misma guarda que el reintento del encuentro).

    Las paga el encuentro; esto cubre a quien, con ese pago cortado, recargó en
    vez de reintentar: por el paso del nombre pasa todo el mundo, y lo ya pagado
    no se paga dos veces. A cualquier otro —quien ya jugaba, también con un único
    gachamon sin bautizar, o con dos— no se le paga nada por aquí. Va antes del
    nombre, porque después ya no lo espera y, si algo cortara entre las dos
    cosas, la vuelta siguiente lo pagaría igual; y si el pago falla se dice en
    el registro y el nombre se pone igual.
    """
    if not nacer.es_el_primero_sin_nombre(db.plantel(jugador.usuario_id, jugador.guild_id)):
        return
    try:
        economia.pagar_logros_de_persona(jugador.usuario_id, jugador.guild_id, ahora)
    except Exception:
        log.warning("no se pudieron pagar las medallas al ponerle nombre al primero", exc_info=True)


@router.post("/bautizar", dependencies=[Depends(con_cabecera)])
def bautizar(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    # El cuerpo se revisa a mano: así todo fallo sale con nuestra forma.
    datos = cuerpo if isinstance(cuerpo, dict) else {}
    nombre = datos.get("nombre")
    if not isinstance(nombre, str):
        raise problema(422, "nombre", "Falta el nombre.")
    # Con `gachamon_id`, el de la pantalla (un recluta que se puso el nombre él
    # solo), que se comprueba que sea tuyo; sin él, la activa, como siempre.
    gachamon_id = datos.get("gachamon_id")
    if "gachamon_id" in datos and not es_un_id(gachamon_id):
        raise problema(422, "peticion", "La petición no se entiende.")
    ahora = db.ahora_utc()
    _pagar_las_medallas_del_primero(jugador, ahora)
    try:
        if gachamon_id is None:
            nacer.bautizar(jugador.usuario_id, jugador.guild_id, nombre, ahora)
        else:
            nacer.bautizar_a(jugador.usuario_id, jugador.guild_id, gachamon_id, nombre, ahora)
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
    # Con `gachamon_id`, a ese gachamon tuyo; sin él, al activo, que tiene que
    # ser el que el jugador estaba viendo.
    gachamon_id = _elegido(datos)
    ahora = db.ahora_utc()
    sin_gachamon = "No tienes un gachamon que cuidar."
    if gachamon_id is None:
        la_misma_activa(jugador, ahora, sin_gachamon)
    try:
        resultado = economia.ejecutar_cuidado(
            evento, jugador.usuario_id, jugador.guild_id, accion, ahora,
            criatura_id=gachamon_id,
        )
    except RuntimeError:
        log.warning("evento de cuidado reutilizado: %s", evento, exc_info=True)
        raise problema(
            409, "evento", "Ese cuidado ya se usó para otra acción."
        ) from None
    if resultado is None:
        raise _nadie(gachamon_id, sin_gachamon)
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
        # El que recibió el cuidado, que con `gachamon_id` no es el activo.
        "gachamon": estado.ficha(db.avanzar(resultado.criatura, ahora), ahora),
        "estado": estado.armar(jugador, ahora),
    }


# Lo que dice «a todos», con `{n}` a cuántos les tocó y `{total}` cuántos tenía.
A_TODOS = {
    sim.ALIMENTAR: "Les diste de comer a {n} de {total}.",
    sim.JUGAR: "Jugaste con {n} de {total}.",
    sim.ENTRENAR: "Entrenaste con {n} de {total}.",
    sim.LIMPIAR: "Bañaste a {n} de {total}.",
}


@router.post("/cuidar/todos", dependencies=[Depends(con_cabecera)])
def cuidar_a_todos(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    # Se valida como en `cuidar`. No hay activo que comprobar: le cae a todos.
    datos = cuerpo if isinstance(cuerpo, dict) else {}
    accion = datos.get("accion")
    if not isinstance(accion, str) or accion not in sim.ACCIONES_DE_CUIDADO:
        raise problema(422, "accion", "Esa acción no existe.")
    evento = datos.get("evento_id")
    if not isinstance(evento, str) or not EVENTO_VALIDO.fullmatch(evento):
        raise problema(422, "evento", "Ese identificador de evento no vale.")
    ahora = db.ahora_utc()
    try:
        hecho = economia.cuidar_a_todos(
            evento, jugador.usuario_id, jugador.guild_id, accion, ahora
        )
    except RuntimeError:
        log.warning("evento de «a todos» reutilizado: %s", evento, exc_info=True)
        raise problema(
            409, "evento", "Ese cuidado ya se usó para otra acción."
        ) from None
    if hecho.de_cuantos == 0:
        raise problema(409, "sin_gachamon", "No tienes gachamones que cuidar.")
    # Como en `cuidar`, las medallas de cada uno que recibió el cuidado. En un
    # replay no hay cuidados: ya se pagaron la primera vez.
    logros = [
        {"nombre": logro.nombre, "gemas": logro.gemas, "de": cuidado.criatura.nombre}
        for cuidado in hecho.cuidados
        for logro in economia.pagar_logros(cuidado.criatura, ahora).nuevos
    ]
    a_cuantos = len(hecho.tocados)
    return {
        "ok": a_cuantos > 0,
        "a_cuantos": a_cuantos,
        "de_cuantos": hecho.de_cuantos,
        "tocados": list(hecho.tocados),
        "mensaje": (
            A_TODOS[accion].format(n=a_cuantos, total=hecho.de_cuantos)
            if a_cuantos else "Ahora mismo no le toca a ninguno."
        ),
        "monedas": hecho.delta_asciicoins,
        "logros": logros,
        "estado": estado.armar(jugador, ahora),
    }


@router.post("/acariciar", dependencies=[Depends(con_cabecera)])
def acariciar(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    # El cuerpo es opcional: sin él, o sin `gachamon_id`, al activo.
    gachamon_id = _elegido(cuerpo if isinstance(cuerpo, dict) else {})
    ahora = db.ahora_utc()
    sin_gachamon = "No tienes un gachamon que acariciar."
    if gachamon_id is None:
        la_misma_activa(jugador, ahora, sin_gachamon)
    caricia = db.acariciar(
        jugador.usuario_id, jugador.guild_id, ahora, criatura_id=gachamon_id
    )
    if caricia.criatura is None:
        raise _nadie(gachamon_id, sin_gachamon)
    return {
        "ok": caricia.ok,
        "espera": _segundos(caricia.espera),
        "gachamon": estado.ficha(db.avanzar(caricia.criatura, ahora), ahora),
        "estado": estado.armar(jugador, ahora),
    }
