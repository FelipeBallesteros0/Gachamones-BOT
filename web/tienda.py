"""La Tienda del pueblo: lo que se vende, a quién, y lo que cada cuenta ya tiene.

Mirar el catálogo sólo lee (el departamento se mira con `db.departamento_leido`,
que no lo crea). Comprar es otro adaptador fino: valida la petición, comprueba
que se está en la tienda y que eso se le vende a la cuenta, y llama a la regla
de `economia`, que cobra y entrega bajo `BEGIN IMMEDIATE` con el evento del
cliente; aquí sólo se traduce lo que pasó a una frase de la web. Las frases de
`economia` (`problema`) son de Discord y no salen por aquí. El servidor decide
qué se vende y a quién; el cliente pinta lo que le llega.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends

import cosmeticos as cos
import db
import departamento as dep
import economia
import objetos as obj
import simulacion as sim
from web import estado, pueblo
from web.cuenta import Jugador, jugador_actual, la_misma_activa
from web.juego import EVENTO_VALIDO
from web.sesion import con_cabecera, problema

log = logging.getLogger("gachamones")
router = APIRouter()

COMPETIR = "competir"

_NOTA_DE_COMPETIR = "Sirve en las competencias, que todavía no están en la página."


def donde_sirve(objeto: obj.Objeto) -> str | None:
    """Dónde se usa lo que todavía no se usa en la web; `None` si ya sirve aquí."""
    if objeto.stat or objeto.reinicia == sim.COMPETIR or objeto.es_sopaipilla:
        return COMPETIR
    return None


def se_le_vende(objeto: obj.Objeto) -> bool:
    """Todo lo que está a la venta y ya sirve en la página; lo demás no se le vende a nadie."""
    return donde_sirve(objeto) is None


def nota_de(objeto: obj.Objeto) -> str | None:
    """Por qué no se usa en la web lo que todavía no sirve aquí; `None` si ya sirve."""
    return None if donde_sirve(objeto) is None else _NOTA_DE_COMPETIR


def en_llano(texto: str) -> str:
    return texto.replace("**", "")


def _objetos(jugador: Jugador) -> list[dict]:
    mochila = db.inventario(jugador.usuario_id, jugador.guild_id)
    return [
        {
            "clave": o.clave, "nombre": o.nombre, "descripcion": en_llano(o.descripcion),
            "precio": o.precio, "icono": f"iconos/objetos/{o.clave}.png",
            "tienes": mochila.get(o.clave, 0),
            "se_vende": se_le_vende(o), "nota": nota_de(o),
        }
        for o in obj.a_la_venta()
    ]


def _cosmeticos(jugador: Jugador) -> list[dict]:
    suyos = db.ropero(jugador.usuario_id, jugador.guild_id)
    return [
        {
            "clave": c.clave, "tipo": c.tipo, "nombre": c.nombre, "precio": c.precio,
            "icono": f"iconos/cosmeticos/{c.clave}.png", "tuyo": c.clave in suyos,
        }
        for c in cos.CATALOGO.values()
    ]


def _muebles(jugador: Jugador) -> dict:
    """Cada mueble del catálogo y cuántos tienes, puestos o guardados: se compran de a varios."""
    depto = db.departamento_leido(jugador.usuario_id, jugador.guild_id)
    tienes = Counter(p.clave for p in depto.piezas)
    return {
        "lista": [
            {
                "clave": m.clave, "nombre": m.nombre, "precio": m.precio,
                "comodidad": m.comodidad, "icono": f"iconos/muebles/{m.clave}.png",
                "tienes": tienes[m.clave],
            }
            for m in dep.MUEBLES.values()
            if not m.puerta
        ],
    }


def catalogo(jugador: Jugador) -> dict:
    """Lo que pinta la pantalla de la tienda, tal como se le ve a esta cuenta."""
    saldos = economia.saldos(jugador.usuario_id, jugador.guild_id)
    return {
        "saldos": {"monedas": saldos.asciicoins, "gemas": saldos.asciigems},
        "objetos": _objetos(jugador),
        "cosmeticos": _cosmeticos(jugador),
        "muebles": _muebles(jugador),
    }


def en_la_tienda(jugador: Jugador) -> None:
    """Para entrar a la tienda hay que estar en ella: lo dice el lugar guardado de la cuenta.

    El lugar que falta o que ya no existe se resuelve como en el estado: tu casa.
    """
    clave = pueblo.donde_esta(db.lugar_de_cuenta(jugador.persona.rowino_uid))
    if "tienda" not in pueblo.ofrece(clave):
        raise problema(409, "no_estas_ahi", "Para eso tienes que estar en la tienda.")


@router.get("/tienda")
def ver_la_tienda(jugador: Jugador = Depends(jugador_actual)) -> dict:
    en_la_tienda(jugador)
    return catalogo(jugador)


# --- Comprar -------------------------------------------------------------------
#
# Un «no» del juego (no alcanza, ya lo tienes…) es un 200 con `ok: false`, la
# clave del motivo y su frase; los 4xx son para lo que la pantalla nunca pide.

OBJETO, COSMETICO, MUEBLE = "objeto", "cosmetico", "mueble"

_SIN_GACHAMON = "Para comprar hace falta un gachamon."
_YA_LO_TIENES = "Ya lo tienes."

# Lo que no depende de cuánto falta. Un motivo que no está aquí es un fallo
# nuestro y no se disfraza: sale como error.
_NO_DEL_COSMETICO = {"ya_lo_tienes": _YA_LO_TIENES}


def no_se_entiende():
    return problema(422, "peticion", "La petición no se entiende.")


def _faltan_monedas(n: int) -> str:
    return f"Te faltan {n} {obj.nombre_de_monedas(n)}."


def _faltan_gemas(n: int) -> str:
    return f"Te faltan {n} {obj.nombre_de_gemas(n)}. Se ganan con las medallas."


def dicho_si(mensaje: str) -> dict:
    return {"ok": True, "clave": None, "mensaje": mensaje}


def dicho_no(motivo: str, mensaje: str) -> dict:
    return {"ok": False, "clave": motivo, "mensaje": mensaje}


def datos_y_evento(cuerpo: Any) -> tuple[dict, str]:
    """El cuerpo como diccionario (si no es un objeto, vacío) y su evento, que tiene que valer."""
    datos = cuerpo if isinstance(cuerpo, dict) else {}
    evento = datos.get("evento_id")
    if not isinstance(evento, str) or not EVENTO_VALIDO.fullmatch(evento):
        raise problema(422, "evento", "Ese identificador de evento no vale.")
    return datos, evento


def _de_la_tienda_y_el_mismo(jugador: Jugador, ahora: datetime) -> None:
    en_la_tienda(jugador)
    la_misma_activa(jugador, ahora, _SIN_GACHAMON)


def evento_usado(evento: str):
    log.warning("evento reutilizado: %s", evento, exc_info=True)
    return problema(409, "evento", "Ese evento ya se usó para otra cosa.")


def _pieza(que: str, clave: Any):
    """Lo que se pide, si la tienda lo vende y ya sirve en la página."""
    if not isinstance(clave, str):
        raise no_se_entiende()
    if que == OBJETO:
        objeto = next((o for o in obj.a_la_venta() if o.clave == clave), None)
        if objeto is None:
            raise no_se_entiende()
        if not se_le_vende(objeto):
            raise problema(409, "mas_adelante", "Eso todavía no se vende aquí.")
        return objeto
    pieza = (cos.CATALOGO if que == COSMETICO else dep.MUEBLES).get(clave)
    if pieza is None or getattr(pieza, "puerta", False):   # la puerta no está a la venta
        raise no_se_entiende()
    return pieza


def _del_objeto(objeto: obj.Objeto, hecho: economia.ResultadoCompra) -> dict:
    # Comprar un objeto sólo dice que no cuando no alcanza.
    if hecho.comprada:
        return dicho_si(f"Compraste {objeto.nombre}. Está en tu mochila.")
    faltan = objeto.precio - hecho.saldos.asciicoins
    if faltan <= 0:
        # `economia.comprar` congela también el «no alcanza»: el reintento con el
        # mismo evento vuelve a decir que no aunque entretanto hayan entrado monedas.
        return dicho_no("reintenta", "No se pudo comprar. Vuelve a intentarlo.")
    return dicho_no("faltan_monedas", _faltan_monedas(faltan))


def _del_cosmetico(cosmetico: cos.Cosmetico, hecho: economia.ResultadoCosmetico) -> dict:
    if hecho.ok:
        # En un replay, `criatura` es el activo de ahora: puede ser otro, no
        # llevarla ya, o no haber nadie. Sólo se le nombra si la lleva puesta.
        criatura = hecho.criatura
        if criatura is not None and getattr(criatura, cosmetico.tipo) == cosmetico.clave:
            return dicho_si(f"Compraste {cosmetico.nombre}. {criatura.nombre} ya lo lleva.")
        return dicho_si(f"Compraste {cosmetico.nombre}. Está en tu ropero.")
    if hecho.motivo == "faltan_gemas":
        return dicho_no(hecho.motivo, _faltan_gemas(cosmetico.precio - hecho.saldo))
    return dicho_no(hecho.motivo, _NO_DEL_COSMETICO[hecho.motivo])


def _del_mueble(mueble: dep.Mueble, hecho: economia.ResultadoDepartamento) -> dict:
    # Comprar un mueble sólo dice que no cuando no alcanza: se tienen de a varios.
    # Otro motivo sería un fallo nuestro y sale como error, como en el cosmético.
    if hecho.ok:
        return dicho_si(f"Compraste {mueble.nombre}. Quedó en tus guardados.")
    if hecho.motivo != "faltan_monedas":
        raise KeyError(hecho.motivo)
    return dicho_no(hecho.motivo, _faltan_monedas(hecho.coste - hecho.saldo))


def _respuesta(jugador: Jugador, ahora: datetime, dicho: dict) -> dict:
    return {**dicho, "tienda": catalogo(jugador), "estado": estado.armar(jugador, ahora)}


@router.post("/tienda/comprar", dependencies=[Depends(con_cabecera)])
def comprar_en_la_tienda(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    # El cuerpo se revisa a mano; la cuenta sale sólo de la cookie.
    datos, evento = datos_y_evento(cuerpo)
    que = datos.get("que")
    if not isinstance(que, str) or que not in (OBJETO, COSMETICO, MUEBLE):
        raise no_se_entiende()
    ahora = db.ahora_utc()
    _de_la_tienda_y_el_mismo(jugador, ahora)
    pieza = _pieza(que, datos.get("clave"))
    usuario, guild = jugador.usuario_id, jugador.guild_id
    try:
        if que == OBJETO:
            dicho = _del_objeto(pieza, economia.comprar(evento, usuario, guild, pieza, ahora))
        elif que == COSMETICO:
            dicho = _del_cosmetico(
                pieza, economia.comprar_cosmetico(usuario, guild, pieza, evento_id=evento)
            )
        else:
            dicho = _del_mueble(
                pieza, economia.comprar_mueble(usuario, guild, pieza, ahora, evento_id=evento)
            )
    except RuntimeError:
        raise evento_usado(evento) from None
    return _respuesta(jugador, ahora, dicho)
