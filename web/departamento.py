"""Tu departamento: lo que hay en él y poner, guardar y ampliar.

Es un adaptador fino, como `web/tienda.py`: valida la petición, comprueba que se
está en el departamento y llama a la regla de `economia`, que cambia todo bajo
`BEGIN IMMEDIATE`; aquí sólo se traduce lo que pasó a una frase de la web. Qué
mueble hay en qué casilla lo valida y lo guarda el servidor. Mirar el
departamento lo crea si es la primera vez (`db.departamento_de`); las
respuestas de las rutas que escriben lo leen sin escribir.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends

import db
import departamento as dep
import economia
from web import estado, pueblo
from web.cuenta import Jugador, jugador_actual
from web.sesion import con_cabecera, es_un_id, problema
from web.tienda import datos_y_evento, dicho_no, evento_usado, no_se_entiende, _faltan_monedas

router = APIRouter()

_NO_DEL_DEPARTAMENTO = {
    dep.NO_ES_TUYO: "Ese mueble no es tuyo.",
    dep.NO_CABE: "Ahí no cabe.",
    dep.OCUPADO: "Ahí ya hay algo.",
    "hace_falta": "Esa cama hace falta: sin ella alguien se queda sin dónde dormir.",
    "ya_es_el_maximo": "Por ese lado tu departamento ya no puede crecer.",
}


def en_el_departamento(jugador: Jugador) -> None:
    """Para tocar el departamento hay que estar en él: lo dice el lugar guardado de la cuenta.

    El lugar que falta o que ya no existe se resuelve como en el estado: tu casa.
    """
    clave = pueblo.donde_esta(db.lugar_de_cuenta(jugador.persona.rowino_uid))
    if "departamento" not in pueblo.ofrece(clave):
        raise problema(409, "no_estas_ahi", "Para eso tienes que estar en tu departamento.")


def _icono(clave: str) -> str:
    return f"iconos/muebles/{clave}.png"


def vista(jugador: Jugador, depto: dep.Departamento) -> dict:
    """El departamento como lo pinta la pantalla. Una pieza que ya no está en el catálogo no se lista."""
    usuario, guild = jugador.usuario_id, jugador.guild_id
    saldos = economia.saldos(usuario, guild)
    puestos, guardados = [], []
    for pieza in depto.puestas:
        mueble = dep.MUEBLES.get(pieza.clave)
        if mueble is None:
            continue
        puestos.append({
            "id": pieza.id, "clave": mueble.clave, "nombre": mueble.nombre,
            "icono": _icono(mueble.clave), "x": pieza.x, "y": pieza.y, "giro": pieza.giro,
            "capa": mueble.capa, "cama": mueble.cama,
            "casillas": [list(c) for c in sorted(dep.huella(mueble, pieza.x, pieza.y, pieza.giro))],
        })
    for pieza in depto.guardadas:
        mueble = dep.MUEBLES.get(pieza.clave)
        if mueble is None:
            continue
        guardados.append({
            "id": pieza.id, "clave": mueble.clave, "nombre": mueble.nombre,
            "icono": _icono(mueble.clave), "capa": mueble.capa, "cama": mueble.cama,
            "ancho": mueble.ancho, "fondo": mueble.fondo,
        })
    return {
        "ancho": depto.ancho, "fondo": depto.fondo, "casillas": depto.casillas,
        "comodidad": depto.comodidad, "tope": dep.tope_de_comodidad(depto.casillas),
        "camas": depto.camas_puestas, "gachamones": len(db.plantel(usuario, guild)),
        "cabe_otro": db.hay_cama_libre(usuario, guild),
        "ampliar": {
            dep.ANCHO: dep.coste_de_ampliar(depto, dep.ANCHO),
            dep.FONDO: dep.coste_de_ampliar(depto, dep.FONDO),
        },
        "puestos": puestos, "guardados": guardados,
        "saldos": {"monedas": saldos.asciicoins, "gemas": saldos.asciigems},
    }


@router.get("/departamento")
def ver_el_departamento(jugador: Jugador = Depends(jugador_actual)) -> dict:
    en_el_departamento(jugador)
    return vista(jugador, db.departamento_de(jugador.usuario_id, jugador.guild_id, db.ahora_utc()))


# --- Poner, guardar y ampliar -----------------------------------------------------
#
# Un «no» del juego es un 200 con `ok: false`, la clave del motivo y su frase; los
# 4xx son para lo que la pantalla nunca pide.

def _respuesta(jugador: Jugador, ahora: datetime, dicho: dict, depto: dep.Departamento) -> dict:
    return {**dicho, "departamento": vista(jugador, depto), "estado": estado.armar(jugador, ahora)}


def _del_cambio(hecho: economia.ResultadoDepartamento, bien: str | None) -> dict:
    if hecho.ok:
        return {"ok": True, "clave": None, "mensaje": bien}
    if hecho.motivo == "faltan_monedas":
        return dicho_no(hecho.motivo, _faltan_monedas(hecho.coste - hecho.saldo))
    return dicho_no(hecho.motivo, _NO_DEL_DEPARTAMENTO[hecho.motivo])


def _un_entero(datos: dict, campo: str) -> int:
    valor = datos.get(campo)
    if type(valor) is not int:   # ni un texto, ni un decimal, ni `true`
        raise no_se_entiende()
    return valor


def _el_mueble(datos: dict) -> int:
    mueble_id = datos.get("mueble_id")
    if not es_un_id(mueble_id):
        raise no_se_entiende()
    return mueble_id


def _cuerpo(cuerpo: Any) -> dict:
    return cuerpo if isinstance(cuerpo, dict) else {}


@router.post("/departamento/poner", dependencies=[Depends(con_cabecera)])
def poner_un_mueble(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    # El cuerpo se revisa a mano; la cuenta sale sólo de la cookie.
    datos = _cuerpo(cuerpo)
    mueble_id = _el_mueble(datos)
    x, y, giro = _un_entero(datos, "x"), _un_entero(datos, "y"), _un_entero(datos, "giro")
    if not 0 <= giro <= 3:
        raise no_se_entiende()
    en_el_departamento(jugador)
    ahora = db.ahora_utc()
    hecho = economia.poner_mueble(jugador.usuario_id, jugador.guild_id, mueble_id, x, y, giro, ahora)
    return _respuesta(jugador, ahora, _del_cambio(hecho, None), hecho.departamento)


@router.post("/departamento/guardar", dependencies=[Depends(con_cabecera)])
def guardar_un_mueble(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    mueble_id = _el_mueble(_cuerpo(cuerpo))
    en_el_departamento(jugador)
    ahora = db.ahora_utc()
    hecho = economia.guardar_mueble(jugador.usuario_id, jugador.guild_id, mueble_id, ahora)
    return _respuesta(jugador, ahora, _del_cambio(hecho, None), hecho.departamento)


@router.post("/departamento/ampliar", dependencies=[Depends(con_cabecera)])
def ampliar_el_departamento(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    datos, evento = datos_y_evento(cuerpo)
    eje = datos.get("eje")
    if not isinstance(eje, str) or eje not in (dep.ANCHO, dep.FONDO):
        raise no_se_entiende()
    en_el_departamento(jugador)
    ahora = db.ahora_utc()
    try:
        hecho = economia.ampliar_departamento(
            jugador.usuario_id, jugador.guild_id, eje, ahora, evento_id=evento
        )
    except RuntimeError:
        raise evento_usado(evento) from None
    nuevo = hecho.departamento
    bien = f"Tu departamento ahora mide {nuevo.ancho} × {nuevo.fondo}."
    return _respuesta(jugador, ahora, _del_cambio(hecho, bien), nuevo)
