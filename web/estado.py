"""El estado: todo lo que la pantalla necesita, en una sola lectura.

Aquí no se decide ninguna regla: se llama a quien la tiene y se traduce a
JSON. Leer no guarda el paso del tiempo del gachamon; sólo escribe quien se
entera de una muerte (`db.activa_al_dia`).
"""
from __future__ import annotations

import math
from dataclasses import asdict
from datetime import datetime

import db
import economia
import especies as esp
import globos
import nacer
import retrato
import simulacion as sim
from web import PREFIJO, pueblo
from web.cuenta import Jugador

_ACCIONES = (sim.ALIMENTAR, sim.JUGAR, sim.ENTRENAR, sim.LIMPIAR, sim.ACARICIAR)


def _barra(valor: float) -> int:
    return max(0, min(100, round(valor)))


def _esperas(criatura: sim.Criatura, ahora: datetime) -> dict[str, int]:
    pendientes = db.esperas(criatura.id, ahora, _ACCIONES)
    esperas = {
        accion: math.ceil(pendientes[accion].total_seconds()) for accion in _ACCIONES
    }
    if sim.puede_saltarse_espera(criatura, sim.ALIMENTAR):
        esperas[sim.ALIMENTAR] = 0
    return esperas


def ficha(criatura: sim.Criatura, ahora: datetime) -> dict:
    """El gachamon ya avanzado hasta `ahora`, tal como lo ve la pantalla."""
    especie = criatura.def_especie
    cara = criatura.animo_visual
    return {
        "id": criatura.id,
        "nombre": criatura.nombre,
        "espera_nombre": nacer.espera_nombre(criatura),
        "especie": criatura.especie,
        "nombre_especie": especie.nombre,
        "emoji": especie.emoji,
        "etapa": criatura.etapa,
        "nombre_etapa": esp.nombre_etapa(criatura.etapa, criatura.genero),
        "nivel": criatura.nivel,
        "genero": criatura.genero,
        "barras": {
            "comida": _barra(criatura.hambre),
            "animo": _barra(criatura.animo),
            "aseo": _barra(criatura.limpieza),
        },
        "cara": cara,
        "desfallecido": criatura.viva and _barra(criatura.hambre) == 0,
        "retrato": (
            f"{PREFIJO}/retrato/{criatura.especie}/{criatura.etapa}/{cara}/"
            f"{criatura.sombrero or 'sin'}.png?v={retrato.version()}"
        ),
        "esperas": _esperas(criatura, ahora),
    }


def _difunto(jugador: Jugador) -> dict | None:
    muerto = db.difunto_pendiente(jugador.persona.rowino_uid)
    if muerto is None:
        return None
    return {
        "nombre": muerto.nombre,
        "nombre_especie": muerto.def_especie.nombre,
        "dias": (muerto.muerta_en - muerto.nacida_en).days,
    }


def _lugar(
    jugador: Jugador, hogar_del_gachamon: str, hogar_de_la_persona: str, hay_gachamon: bool
) -> dict:
    clave = db.lugar_de_cuenta(jugador.persona.rowino_uid)
    if not pueblo.existe(clave):
        clave = pueblo.de_partida(hogar_del_gachamon)
    return {
        "clave": clave,
        "nombre": pueblo.LUGARES[clave].nombre,
        "abre": pueblo.LUGARES[clave].abre,
        "aviso": pueblo.aviso(
            clave, jugador.vinculada, hogar_de_la_persona, hogar_del_gachamon if hay_gachamon else None
        ),
    }


def armar(jugador: Jugador, ahora: datetime) -> dict:
    activa = db.activa_al_dia(jugador.usuario_id, jugador.guild_id, ahora)
    avatar = db.avatar_de(jugador.usuario_id, jugador.guild_id)
    saldos = economia.saldos(jugador.usuario_id, jugador.guild_id)
    hogar = db.hogar_leido(jugador.usuario_id, jugador.guild_id, ahora)
    estado_hogar = hogar.estado_de(None if activa is None else activa.casa_id, ahora)
    # Se parte de donde vive el gachamon; «Tu casa» mira si la persona tiene una.
    hogar_de_la_persona = hogar.estado(ahora)
    lugar = _lugar(jugador, estado_hogar, hogar_de_la_persona, activa is not None)
    # Sin casa propia, «Tu casa» avisa que no la hay, y a la intemperie el
    # Refugio avisa que ya no vive en él: el gachamon no habla de ese lugar.
    aqui = lugar["clave"]
    sin_frases = pueblo.sin_casa(aqui, hogar_de_la_persona) or pueblo.a_la_intemperie(aqui, estado_hogar)
    del_lugar = None if sin_frases else aqui
    return {
        "ahora": ahora.isoformat(),
        "persona": {
            "usuario": jugador.persona.usuario, "vinculada": jugador.vinculada,
        },
        "avatar": None if avatar is None else asdict(avatar),
        "saldos": {"monedas": saldos.asciicoins, "gemas": saldos.asciigems},
        "hogar": estado_hogar,
        "gachamon": None if activa is None else ficha(activa, ahora),
        "difunto": _difunto(jugador),
        "globos": [] if activa is None else [
            {"tipo": g.tipo, "texto": g.texto} for g in globos.de(activa, del_lugar)
        ],
        "lugar": lugar,
    }
