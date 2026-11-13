"""La Tienda del pueblo: lo que se vende, a quién, y lo que cada cuenta ya tiene.

Mirar el catálogo sólo lee (el hogar se mira con `db.hogar_leido`, nunca con
`db.hogar_de`). Comprar es otro adaptador fino: valida la petición, comprueba
que se está en la tienda y que eso se le vende a la cuenta, y llama a la regla
de `economia`, que cobra y entrega bajo `BEGIN IMMEDIATE` con el evento del
cliente; aquí sólo se traduce lo que pasó a una frase de la web. Las frases de
`economia` (`problema`) son de Discord y no salen por aquí. El servidor decide
qué se vende y a quién; el cliente pinta lo que le llega.

Ojo: este módulo es `web.tienda`, no el `tienda` de la raíz, que importa
`discord`. Dentro de `web/` se importa siempre como `from web import tienda`.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends

import casas as cas
import cosmeticos as cos
import db
import economia
import huerto as hue
import identidad
import objetos as obj
import simulacion as sim
from web import estado, pueblo
from web.cuenta import Jugador, jugador_actual, la_misma_activa
from web.juego import EVENTO_VALIDO
from web.sesion import con_cabecera, problema

log = logging.getLogger("gachamones")
router = APIRouter()

COMPETIR, HUERTO, REFUGIO = "competir", "huerto", "refugio"

_NOTA_DE_COMPETIR = "Sirve en las competencias, que por ahora se juegan en Discord."
_NOTA_DEL_HUERTO = "Se siembra en el huerto, que por ahora está en Discord."
_NOTA_MAS_ADELANTE = "Más adelante."
_NOTA_DEL_REFUGIO = "No lo necesitas: tu estancia en el refugio no tiene plazo."


def donde_sirve(objeto: obj.Objeto) -> str | None:
    """Dónde se usa lo que todavía no se usa en la web; `None` si ya sirve aquí."""
    if objeto.stat or objeto.reinicia == sim.COMPETIR:
        return COMPETIR
    if objeto.clave == hue.SEMILLA:
        return HUERTO
    if objeto.dias_de_refugio:
        return REFUGIO
    return None


def se_le_vende(objeto: obj.Objeto, jugador: Jugador) -> bool:
    """Todo lo que está a la venta; a quien no tiene Discord, sólo lo que ya sirve en la web.

    Lo del refugio, a quien tiene plazo en él: esa excepción se pregunta siempre
    con `identidad.sin_plazo_de_refugio`, nunca mirando la cuenta.
    """
    sirve = donde_sirve(objeto)
    if sirve == REFUGIO:
        return not identidad.sin_plazo_de_refugio(jugador.usuario_id)
    return sirve is None or jugador.vinculada


def _nota(objeto: obj.Objeto, jugador: Jugador) -> str | None:
    sirve = donde_sirve(objeto)
    if sirve is None:
        return None
    if sirve == REFUGIO:
        return _NOTA_DEL_REFUGIO if identidad.sin_plazo_de_refugio(jugador.usuario_id) else None
    if jugador.vinculada:
        return {COMPETIR: _NOTA_DE_COMPETIR, HUERTO: _NOTA_DEL_HUERTO}[sirve]
    return _NOTA_MAS_ADELANTE


def en_llano(texto: str) -> str:
    return texto.replace("**", "")


def _objetos(jugador: Jugador) -> list[dict]:
    mochila = db.inventario(jugador.usuario_id, jugador.guild_id)
    return [
        {
            "clave": o.clave, "nombre": o.nombre, "descripcion": en_llano(o.descripcion),
            "precio": o.precio, "icono": f"iconos/objetos/{o.clave}.png",
            "tienes": mochila.get(o.clave, 0),
            "se_vende": se_le_vende(o, jugador), "nota": _nota(o, jugador),
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


def _casa_tuya(
    jugador: Jugador, propia: cas.CasaPropia, viven: dict[int | None, int],
) -> dict:
    casa = propia.casa
    bancales = db.huerto_de(
        jugador.usuario_id, jugador.guild_id, propia.id, hue.bancales_de(casa.clave)
    )
    reventa = cas.lo_que_dan_por(casa)
    return {
        "id": propia.id, "clave": casa.clave, "nombre": casa.nombre,
        "icono": f"iconos/casas/{casa.clave}.png", "aforo": casa.aforo,
        "viven": viven.get(propia.id, 0), "muebles": len(propia.puestos),
        "plantados": sum(1 for b in bancales if b.plantado), "dan": reventa,
        "mejoras": [
            {"clave": c.clave, "nombre": c.nombre, "cuesta": c.precio - reventa}
            for c in cas.CATALOGO.values() if cas.puede_mejorarse_a(propia, c)
        ],
    }


def _casas(jugador: Jugador, hogar: cas.Hogar) -> dict:
    viven = db.inquilinos_de(jugador.usuario_id, jugador.guild_id)
    return {
        "maximo": cas.MAXIMO_CASAS,
        "puedes_otra": hogar.puede_comprar_otra(),
        "tuyas": [_casa_tuya(jugador, p, viven) for p in hogar.casas],
        "a_la_venta": [
            {
                "clave": c.clave, "nombre": c.nombre, "icono": f"iconos/casas/{c.clave}.png",
                "precio": c.precio, "aforo": c.aforo, "huecos": c.huecos,
                "bancales": hue.bancales_de(c.clave),
            }
            for c in cas.CATALOGO.values()
        ],
    }


def _muebles(jugador: Jugador, hogar: cas.Hogar) -> dict:
    suyos = db.mobiliario(jugador.usuario_id, jugador.guild_id)
    return {
        "tienes_casa": bool(hogar.casas),
        "lista": [
            {
                "clave": m.clave, "nombre": m.nombre, "precio": m.precio,
                "comodidad": m.comodidad, "icono": f"iconos/muebles/{m.clave}.png",
                "tuyo": m.clave in suyos,
            }
            for m in cas.MUEBLES.values()
        ],
    }


def catalogo(jugador: Jugador, ahora: datetime) -> dict:
    """Lo que pinta la pantalla de la tienda, tal como se le ve a esta cuenta."""
    saldos = economia.saldos(jugador.usuario_id, jugador.guild_id)
    hogar = db.hogar_leido(jugador.usuario_id, jugador.guild_id, ahora)
    return {
        "saldos": {"monedas": saldos.asciicoins, "gemas": saldos.asciigems},
        "objetos": _objetos(jugador),
        "cosmeticos": _cosmeticos(jugador),
        "casas": _casas(jugador, hogar),
        "muebles": _muebles(jugador, hogar),
    }


def en_la_tienda(jugador: Jugador) -> None:
    """Para entrar a la tienda hay que estar en ella: lo dice el lugar guardado de la cuenta.

    Un lugar guardado que ya no existe se resuelve como en el estado (se vuelve
    al hogar, que no ofrece nada); por eso basta con mirar el lugar si existe.
    """
    clave = db.lugar_de_cuenta(jugador.persona.rowino_uid)
    if not pueblo.existe(clave) or "tienda" not in pueblo.ofrece(clave):
        raise problema(409, "no_estas_ahi", "Para eso tienes que estar en la tienda.")


@router.get("/tienda")
def ver_la_tienda(jugador: Jugador = Depends(jugador_actual)) -> dict:
    en_la_tienda(jugador)
    return catalogo(jugador, db.ahora_utc())


# --- Comprar -------------------------------------------------------------------
#
# Un «no» del juego (no alcanza, ya lo tienes…) es un 200 con `ok: false`, la
# clave del motivo y su frase; los 4xx son para lo que la pantalla nunca pide.

OBJETO, COSMETICO, MUEBLE = "objeto", "cosmetico", "mueble"
COMPRAR, MEJORAR, VENDER = "comprar", "mejorar", "vender"

_SIN_GACHAMON = "Para comprar hace falta un gachamon."
_YA_LO_TIENES = "Ya lo tienes."
_NO_ES_TUYA = "Esa casa no es tuya."
_MUEBLES_SIN_CASA = "Los muebles van en una casa, y todavía no tienes."

# Lo que no depende de cuánto falta. Un motivo que no está aquí es un fallo
# nuestro y no se disfraza: sale como error.
_NO_DEL_COSMETICO = {"ya_lo_tienes": _YA_LO_TIENES}
_NO_DEL_MUEBLE = {
    "sin_casa": _MUEBLES_SIN_CASA, "intemperie": _MUEBLES_SIN_CASA,
    "no_es_tuya": _NO_ES_TUYA, "ya_lo_tienes": _YA_LO_TIENES,
}
_NO_DE_LA_CASA = {
    "no_es_tuya": _NO_ES_TUYA,
    "no_se_empeora": "Esa casa ya es de ese tamaño o más grande.",
    "maximo_de_casas": (
        f"Ya tienes {cas.MAXIMO_CASAS} casas, que es el máximo. "
        "Vende una o mejora las que tienes."
    ),
}
_NO_DE_LA_VENTA = {"sin_casa": "No tienes casa que vender.", "no_es_tuya": _NO_ES_TUYA}


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


def _pieza(que: str, clave: Any, jugador: Jugador):
    """Lo que se pide, si la tienda lo vende y se lo vende a esta cuenta."""
    if not isinstance(clave, str):
        raise no_se_entiende()
    if que == OBJETO:
        objeto = next((o for o in obj.a_la_venta() if o.clave == clave), None)
        if objeto is None:
            raise no_se_entiende()
        if not se_le_vende(objeto, jugador):
            raise problema(409, "mas_adelante", "Eso todavía no se vende aquí.")
        return objeto
    pieza = (cos.CATALOGO if que == COSMETICO else cas.MUEBLES).get(clave)
    if pieza is None:
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


def _del_mueble(mueble: cas.Mueble, hecho: economia.ResultadoMueble) -> dict:
    if hecho.ok:
        if hecho.colocado:
            return dicho_si(f"Compraste {mueble.nombre}. Ya está puesto en tu casa.")
        return dicho_si(f"Compraste {mueble.nombre}. No cabía en tu casa: quedó guardado.")
    if hecho.motivo == "faltan_monedas":
        return dicho_no(hecho.motivo, _faltan_monedas(mueble.precio - hecho.saldo))
    return dicho_no(hecho.motivo, _NO_DEL_MUEBLE[hecho.motivo])


def _de_la_casa(casa: cas.Casa, hecho: economia.ResultadoMudanza) -> dict:
    if hecho.ok:
        if hecho.desde is None:
            return dicho_si(f"Compraste una {casa.nombre.lower()}.")
        return dicho_si(f"Tu {hecho.desde.nombre.lower()} ahora es una {casa.nombre.lower()}.")
    if hecho.motivo == "faltan_monedas":
        # Mejorar cuesta la nueva menos lo que dan por la vieja.
        cuesta = casa.precio - (cas.lo_que_dan_por(hecho.desde) if hecho.desde else 0)
        return dicho_no(hecho.motivo, _faltan_monedas(cuesta - hecho.saldo))
    return dicho_no(hecho.motivo, _NO_DE_LA_CASA[hecho.motivo])


def _de_la_venta(hecho: economia.ResultadoVenta) -> dict:
    if hecho.ok:
        return dicho_si(
            f"Vendiste tu {hecho.casa.nombre.lower()} por {hecho.cobrado} "
            f"{obj.nombre_de_monedas(hecho.cobrado)}."
        )
    return dicho_no(hecho.motivo, _NO_DE_LA_VENTA[hecho.motivo])


def _respuesta(jugador: Jugador, ahora: datetime, dicho: dict) -> dict:
    return {**dicho, "tienda": catalogo(jugador, ahora), "estado": estado.armar(jugador, ahora)}


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
    pieza = _pieza(que, datos.get("clave"), jugador)
    usuario, guild = jugador.usuario_id, jugador.guild_id
    try:
        if que == OBJETO:
            dicho = _del_objeto(pieza, economia.comprar(evento, usuario, guild, pieza, ahora))
        elif que == COSMETICO:
            dicho = _del_cosmetico(
                pieza, economia.comprar_cosmetico(usuario, guild, pieza, evento_id=evento)
            )
        else:
            # Sin `casa_id`: va a la primera casa, como en Discord.
            dicho = _del_mueble(
                pieza, economia.comprar_mueble(usuario, guild, pieza, ahora, evento_id=evento)
            )
    except RuntimeError:
        raise evento_usado(evento) from None
    return _respuesta(jugador, ahora, dicho)


def _casa_id(datos: dict) -> int:
    casa_id = datos.get("casa_id")
    if type(casa_id) is not int:   # ni un texto, ni un decimal, ni `true`
        raise no_se_entiende()
    return casa_id


@router.post("/tienda/casa", dependencies=[Depends(con_cabecera)])
def comprar_mejorar_o_vender_una_casa(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    # El cuerpo se revisa a mano; la cuenta sale sólo de la cookie.
    datos, evento = datos_y_evento(cuerpo)
    accion = datos.get("accion")
    if not isinstance(accion, str) or accion not in (COMPRAR, MEJORAR, VENDER):
        raise no_se_entiende()
    ahora = db.ahora_utc()
    _de_la_tienda_y_el_mismo(jugador, ahora)
    usuario, guild = jugador.usuario_id, jugador.guild_id
    if accion == VENDER:
        casa_id = _casa_id(datos)
        try:
            hecho = economia.vender_casa(usuario, guild, casa_id, ahora, evento_id=evento)
        except RuntimeError:
            raise evento_usado(evento) from None
        return _respuesta(jugador, ahora, _de_la_venta(hecho))

    clave = datos.get("casa")
    nueva = cas.CATALOGO.get(clave) if isinstance(clave, str) else None
    if nueva is None:
        raise no_se_entiende()
    mejorar = _casa_id(datos) if accion == MEJORAR else None
    try:
        hecho = economia.comprar_casa(
            usuario, guild, nueva, ahora, mejorar=mejorar, evento_id=evento
        )
    except RuntimeError:
        raise evento_usado(evento) from None
    return _respuesta(jugador, ahora, _de_la_casa(nueva, hecho))
