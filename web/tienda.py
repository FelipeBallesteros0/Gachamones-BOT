"""La Tienda del pueblo: lo que se vende, a quién, y lo que cada cuenta ya tiene.

Aquí sólo se lee: ni se cobra ni se entrega nada, y nada se escribe (el hogar
se mira con `db.hogar_leido`, nunca con `db.hogar_de`). El servidor decide qué
se vende y a quién; el cliente pinta lo que le llega.

Ojo: este módulo es `web.tienda`, no el `tienda` de la raíz, que importa
`discord`. Dentro de `web/` se importa siempre como `from web import tienda`.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

import casas as cas
import cosmeticos as cos
import db
import economia
import huerto as hue
import objetos as obj
import simulacion as sim
from web import pueblo
from web.cuenta import Jugador, jugador_actual
from web.sesion import problema

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
    """Todo lo que está a la venta; a quien no tiene Discord, sólo lo que ya sirve en la web."""
    if jugador.vinculada:
        return True
    return donde_sirve(objeto) not in (COMPETIR, HUERTO, REFUGIO)


def _nota(objeto: obj.Objeto, jugador: Jugador) -> str | None:
    sirve = donde_sirve(objeto)
    if sirve is None:
        return None
    if jugador.vinculada:
        return {COMPETIR: _NOTA_DE_COMPETIR, HUERTO: _NOTA_DEL_HUERTO}.get(sirve)
    return _NOTA_DEL_REFUGIO if sirve == REFUGIO else _NOTA_MAS_ADELANTE


def _en_llano(texto: str) -> str:
    return texto.replace("**", "")


def _objetos(jugador: Jugador) -> list[dict]:
    mochila = db.inventario(jugador.usuario_id, jugador.guild_id)
    return [
        {
            "clave": o.clave, "nombre": o.nombre, "descripcion": _en_llano(o.descripcion),
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
