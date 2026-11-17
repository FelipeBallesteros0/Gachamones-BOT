"""El estado: todo lo que la pantalla necesita, en una sola lectura.

Aquí no se decide ninguna regla: se llama a quien la tiene y se traduce a
JSON. Leer no guarda el paso del tiempo del gachamon; lo único del gachamon
que puede escribir es el remiendo de `db.activa_al_dia`, que pone a uno de
activo si no hay ninguno. Leer el estado también asegura el monedero.
"""
from __future__ import annotations

import math
from dataclasses import asdict
from datetime import datetime

import cosmeticos as cos
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


def retrato_de(criatura: sim.Criatura) -> str:
    """La dirección de su retrato: su especie, su etapa, la cara que pone y su sombrero."""
    return (
        f"{PREFIJO}/retrato/{criatura.especie}/{criatura.etapa}/{criatura.animo_visual}/"
        f"{criatura.sombrero or 'sin'}.png?v={retrato.version()}"
    )


def ficha(criatura: sim.Criatura, ahora: datetime) -> dict:
    """El gachamon ya avanzado hasta `ahora`, tal como lo ve la pantalla."""
    especie = criatura.def_especie
    cara = criatura.animo_visual
    return {
        "id": criatura.id,
        "nombre": criatura.nombre,
        "espera_nombre": nacer.espera_nombre(criatura),
        "se_nombro_solo": criatura.se_nombro_solo,
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
        "retrato": retrato_de(criatura),
        "esperas": _esperas(criatura, ahora),
        "titulo": cos.texto_del_titulo(criatura.titulo, criatura.genero) or None,
    }


def _lugar(jugador: Jugador, sin_gachamon: bool, cama_libre: bool) -> dict:
    clave = pueblo.donde_esta(db.lugar_de_cuenta(jugador.persona.rowino_uid))
    return {
        "clave": clave,
        "nombre": pueblo.LUGARES[clave].nombre,
        "abre": pueblo.LUGARES[clave].abre,
        "aviso": pueblo.aviso(clave, sin_gachamon=sin_gachamon, cama_libre=cama_libre),
        "ofrece": list(pueblo.ofrece(clave, sin_gachamon=sin_gachamon)),
    }


# La guía de quien no tiene ningún gachamon vivo: el paso que le toca.
_GUIA_CAMA = {
    "clave": "cama",
    "texto": "Pon tu segunda cama: entra a «Construir», tócala en los guardados y después toca una casilla.",
}
_GUIA_AVENTURA = {
    "clave": "aventura",
    "texto": "Ya hay cama para un gachamon. Sal al pueblo y ve a «Aventura».",
}


def _guia(sin_gachamon: bool, cama_libre: bool) -> dict | None:
    """El paso que le toca a quien no tiene ningún gachamon vivo; con alguno, ninguno."""
    if not sin_gachamon:
        return None
    return dict(_GUIA_AVENTURA if cama_libre else _GUIA_CAMA)


def _el_gachamon(activa: sim.Criatura, ahora: datetime) -> dict:
    """La ficha de la activa y, si espera nombre, el que se le sugiere."""
    sugerido = nacer.nombre_sugerido(activa) if nacer.espera_nombre(activa) else None
    return {**ficha(activa, ahora), "sugerido": sugerido}


def armar(jugador: Jugador, ahora: datetime) -> dict:
    activa = db.activa_al_dia(jugador.usuario_id, jugador.guild_id, ahora)
    avatar = db.avatar_de(jugador.usuario_id, jugador.guild_id)
    saldos = economia.saldos(jugador.usuario_id, jugador.guild_id)
    # Sin ninguno vivo, la cama libre dice qué paso le toca: ponerla, o la aventura.
    sin_gachamon = activa is None
    cama_libre = sin_gachamon and db.hay_cama_libre(jugador.usuario_id, jugador.guild_id)
    lugar = _lugar(jugador, sin_gachamon, cama_libre)
    return {
        "ahora": ahora.isoformat(),
        "persona": {
            "usuario": jugador.persona.usuario, "vinculada": jugador.vinculada,
        },
        "avatar": None if avatar is None else asdict(avatar),
        "saldos": {"monedas": saldos.asciicoins, "gemas": saldos.asciigems},
        "gachamon": None if activa is None else _el_gachamon(activa, ahora),
        "globos": [] if activa is None else [
            {"tipo": g.tipo, "texto": g.texto} for g in globos.de(activa, lugar["clave"])
        ],
        "lugar": lugar,
        "carta": db.carta_sin_ver(
            jugador.usuario_id, jugador.guild_id, economia.CAMBIO_DE_LA_VIVIENDA
        ) is not None,
        "guia": _guia(sin_gachamon, cama_libre),
    }
