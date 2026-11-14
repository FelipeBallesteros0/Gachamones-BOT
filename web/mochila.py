"""La mochila: lo que se lleva y usarlo.

Ver la mochila sólo lee y vale desde cualquier lugar. Usar es un adaptador fino:
valida la petición, comprueba que el gachamon es el que se estaba viendo y llama
a la regla de `economia` (una sola operación, con el evento del cliente); aquí
sólo se traduce lo que pasó a una frase de la web, en texto llano. Las frases de
`economia` (`problema`) son de Discord y sólo se enseña la del validador de
nombres, que no nombra comandos.

Ojo: este módulo es `web.mochila`; no importa `discord` ni nada que lo importe.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

import db
import economia
import huerto as hue
import identidad
import objetos as obj
import simulacion as sim
from web import estado
from web.cuenta import Jugador, jugador_actual, la_misma_activa
from web.sesion import con_cabecera, problema
from web.tienda import datos_y_evento, dicho_no, dicho_si, en_llano, evento_usado, no_se_entiende

router = APIRouter()

AL_MOMENTO, CON_NOMBRE = "al_momento", "con_nombre"

_SIN_GACHAMON = "Para usar eso hace falta un gachamon."
_YA_NO_ES_EL_MISMO = "Tu gachamon ya no es el mismo. Mira otra vez."
_NOTA_DEL_HUERTO = "Se usa en el huerto."
_NOTA_SIN_PLAZO = "No lo necesitas: tu estancia en el refugio no tiene plazo."
_NO_SE_USA = "Eso no se usa desde la mochila."
_YA_SE_LLAMA_ASI = "Ya se llama así."
_NO_QUEDA = "Ya no te queda ninguno."

# Lo que dice el juego cuando no hace falta nada más para contarlo.
_NO_DEL_USO = {
    "no_tienes": _NO_QUEDA, "no_se_usa": _NO_SE_USA,
    "sin_plazo": _NOTA_SIN_PLAZO, "mismo_nombre": _YA_SE_LLAMA_ASI,
}


def _uso(objeto: obj.Objeto, jugador: Jugador) -> tuple[str | None, str | None]:
    """Cómo se usa desde la mochila y, si no se usa, por qué."""
    if objeto.renombra:
        return CON_NOMBRE, None
    if objeto.clave == hue.SEMILLA or (objeto.color and not objeto.es_sopaipilla):
        return None, _NOTA_DEL_HUERTO
    if objeto.dias_de_refugio and identidad.sin_plazo_de_refugio(jugador.usuario_id):
        return None, _NOTA_SIN_PLAZO
    if objeto.se_aplica_al_momento:
        return AL_MOMENTO, None
    return None, _NO_SE_USA


def lo_que_llevas(jugador: Jugador) -> dict:
    """Lo que la persona lleva y sigue en el catálogo, en el orden del catálogo."""
    mochila = db.inventario(jugador.usuario_id, jugador.guild_id)
    lista = []
    for o in obj.CATALOGO.values():
        if mochila.get(o.clave, 0) <= 0:
            continue
        uso, nota = _uso(o, jugador)
        lista.append({
            "clave": o.clave, "nombre": o.nombre, "descripcion": en_llano(o.descripcion),
            "icono": f"iconos/objetos/{o.clave}.png", "cantidad": mochila[o.clave],
            "uso": uso, "nota": nota,
        })
    return {"objetos": lista}


@router.get("/mochila")
def ver_la_mochila(jugador: Jugador = Depends(jugador_actual)) -> dict:
    return lo_que_llevas(jugador)


# --- Usar --------------------------------------------------------------------------

def _quien(hecho: economia.ResultadoUso) -> str:
    """El nombre del gachamon; si la regla no trae a quién, no hay de quién hablar."""
    if hecho.criatura is None:
        raise problema(409, "sin_gachamon", _YA_NO_ES_EL_MISMO)
    return hecho.criatura.nombre


def frase(objeto: obj.Objeto, hecho: economia.ResultadoUso, propuesto: str = "") -> dict:
    """Lo que pasó, como respuesta de la web: `{ok, clave, mensaje}`."""
    if hecho.motivo == "sin_gachamon":
        raise problema(409, "sin_gachamon", _YA_NO_ES_EL_MISMO)
    if hecho.motivo == "nombre":
        return dicho_no("nombre", hecho.problema or "Ese nombre no vale.")
    if hecho.motivo == "no_hace_falta":
        return dicho_no("no_hace_falta", _no_hace_falta(hecho))
    if hecho.motivo is not None:
        return dicho_no(hecho.motivo, _NO_DEL_USO[hecho.motivo])
    minutos = obj.MINUTOS_DE_EFECTO
    if hecho.efecto == "reinicia":
        return dicho_si(f"{_quien(hecho)} ya puede {hecho.accion} otra vez.")
    if hecho.efecto == "estadistica":
        return dicho_si(
            f"{_quien(hecho)} gana +{hecho.bonus} de {hecho.stats[0]} durante {minutos} minutos."
        )
    if hecho.efecto == "sopaipilla":
        nombre, comida = _quien(hecho), objeto.nombre.lower()
        if len(hecho.stats) == 4:
            return dicho_si(
                f"{nombre} se come una {comida}. +{hecho.bonus} en las cuatro estadísticas "
                f"durante {minutos} minutos."
            )
        return dicho_si(
            f"{nombre} se come una {comida}: {hecho.gusto}. +{hecho.bonus} de fuerza y de "
            f"velocidad durante {minutos} minutos."
        )
    if hecho.efecto == "refugio":
        return dicho_si(f"Tienes otra estancia en el refugio, hasta el {hecho.refugio_hasta:%d/%m}.")
    if hecho.efecto == "comida":
        criatura = hecho.criatura
        if criatura is None:
            raise problema(409, "sin_gachamon", _YA_NO_ES_EL_MISMO)
        return dicho_si(
            f"{criatura.nombre} come. Comida +{hecho.comida} (ahora {round(criatura.hambre)})."
        )
    if hecho.efecto == "nombre":
        return dicho_si(f"{hecho.nombre_anterior} pasa a llamarse {sim.normalizar_nombre(propuesto)}.")
    # Un efecto que no conocemos es un fallo nuestro y no se disfraza.
    raise RuntimeError(f"efecto de uso sin frase: {hecho.efecto!r}")


def _no_hace_falta(hecho: economia.ResultadoUso) -> str:
    """Por qué no se usó lo que no habría hecho nada; `efecto` es el que habría tenido."""
    if hecho.efecto == "comida":
        return f"{_quien(hecho)} no tiene hambre: su comida ya está a 100. No se gastó nada."
    if hecho.efecto == "reinicia":
        return f"{_quien(hecho)} ya puede {hecho.accion}: no hace falta. No se gastó nada."
    if hecho.efecto == "refugio":
        return "El ticket no alargaría tu estancia en el refugio. No se gastó nada."
    raise RuntimeError(f"no_hace_falta sin frase: {hecho.efecto!r}")


@router.post("/mochila/usar", dependencies=[Depends(con_cabecera)])
def usar_de_la_mochila(
    cuerpo: Any = Body(default=None),
    jugador: Jugador = Depends(jugador_actual),
) -> dict:
    # El cuerpo se revisa a mano; la cuenta sale sólo de la cookie.
    datos, evento = datos_y_evento(cuerpo)
    clave, propuesto = datos.get("clave"), datos.get("nombre")
    if propuesto is None:
        propuesto = ""
    if not isinstance(clave, str) or not isinstance(propuesto, str):
        raise no_se_entiende()
    # El gachamon que enseñaba la pantalla. `la_misma_activa` sólo ve un cambio
    # que pasa en esta petición; uno ya registrado lo ve `economia` con esto.
    # Sin él (las páginas de antes, durante el despliegue), todo como siempre;
    # si viene, es un entero: ni un texto, ni un decimal, ni `true`.
    gachamon_id = datos.get("gachamon_id")
    if "gachamon_id" in datos and type(gachamon_id) is not int:
        raise no_se_entiende()
    ahora = db.ahora_utc()
    la_misma_activa(jugador, ahora, _SIN_GACHAMON)
    objeto = obj.CATALOGO.get(clave)
    if objeto is None:
        raise no_se_entiende()
    usuario, guild = jugador.usuario_id, jugador.guild_id
    try:
        if objeto.renombra:
            hecho = economia.renombrar_con_placa(
                evento, usuario, guild, objeto, propuesto, ahora, criatura_id=gachamon_id
            )
        else:
            hecho = economia.usar_objeto(evento, usuario, guild, objeto, ahora, criatura_id=gachamon_id)
    except RuntimeError:
        raise evento_usado(evento) from None
    return {
        **frase(objeto, hecho, propuesto),
        "mochila": lo_que_llevas(jugador), "estado": estado.armar(jugador, ahora),
    }
