"""La ficha completa del gachamon activo: lo que la pantalla de la ficha pinta.

Sólo lee. Pone la activa al día (que es lo único que puede escribir una
lectura: la muerte que descubre) y arma el JSON con las funciones de siempre.
Las medallas se **miran** y no se pagan: pagarlas es cosa de Discord y de las
reglas de `economia`, y quien sólo mira no cobra ni anota nada.

Ojo: este módulo es `web.ficha`; no importa `discord` ni nada que lo importe.
"""
from __future__ import annotations

import math

from fastapi import APIRouter, Depends

import cosmeticos as cos
import db
import economia
import logros as lgr
import personalidad as per
import simulacion as sim
from web import estado
from web.cuenta import Jugador, jugador_actual
from web.sesion import problema

router = APIRouter()

_NOMBRES = {"fuerza": "Fuerza", "velocidad": "Velocidad", "salud": "Salud", "ingenio": "Ingenio"}


def _estadisticas(criatura: sim.Criatura, ahora) -> list[dict]:
    efectos = db.efectos_activos(criatura.id, ahora)
    lista = []
    for clave in sim.ESTADISTICAS:
        efecto = None
        if clave in efectos:
            bonus, resta = efectos[clave]
            efecto = {"bonus": bonus, "segundos": math.ceil(resta.total_seconds())}
        lista.append({
            "clave": clave, "nombre": _NOMBRES[clave],
            "valor": getattr(criatura, clave), "efecto": efecto,
        })
    return lista


def _medallas(catalogo, hechos: dict[str, int], conseguidas: dict) -> list[dict]:
    lista = []
    for logro in catalogo:
        tiene = logro.clave in conseguidas
        progreso = None
        if not tiene and logro.meta > 1:
            progreso = {"hecho": min(hechos.get(logro.hecho, 0), logro.meta), "meta": logro.meta}
        lista.append({
            "clave": logro.clave, "nombre": logro.nombre, "como": logro.como,
            "gemas": logro.gemas, "tiene": tiene, "progreso": progreso,
        })
    return lista


@router.get("/ficha")
def ver_la_ficha(jugador: Jugador = Depends(jugador_actual)) -> dict:
    ahora = db.ahora_utc()
    criatura = db.activa_al_dia(jugador.usuario_id, jugador.guild_id, ahora)
    if criatura is None:
        raise problema(409, "sin_gachamon", "No tienes un gachamon.")
    sombrero = cos.buscar(criatura.sombrero)
    hechos = lgr.hechos_de(criatura, db.marcador(criatura.id), ahora)
    hechos_persona = lgr.hechos_de_la_persona(
        db.marcador_de_persona(jugador.usuario_id, jugador.guild_id),
        db.especies_de(jugador.usuario_id, jugador.guild_id),
    )
    saldos = economia.saldos(jugador.usuario_id, jugador.guild_id)
    return {
        "gachamon": estado.ficha(criatura, ahora),
        "detalle": {
            "caracter": per.nombre_caracter(criatura),
            "sombrero": None if sombrero is None else sombrero.nombre,
            "experiencia": {
                "nivel": criatura.nivel, "xp": criatura.xp,
                "para_subir": sim.xp_para_subir(criatura.nivel),
            },
            "estadisticas": _estadisticas(criatura, ahora),
        },
        "medallas": {
            "del_gachamon": _medallas(lgr.del_gachamon(), hechos, db.logros_de(criatura.id)),
            "tuyas": _medallas(
                lgr.de_la_persona(), hechos_persona,
                db.logros_de_persona(jugador.usuario_id, jugador.guild_id),
            ),
        },
        "saldos": {"monedas": saldos.asciicoins, "gemas": saldos.asciigems},
    }
