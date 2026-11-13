"""Nacer: romper el huevo y bautizar. Lo comparten el bot y la web.

Aquí está lo que decide qué nace y cuándo se puede bautizar; quien llama
(el botón del bot, la ruta de la web) sólo traduce el resultado.
"""
from __future__ import annotations

import random
import sqlite3
from datetime import datetime

import db
import especies as esp
import personalidad as per
import simulacion as sim


class YaTieneGachamon(Exception):
    """El huevo es sólo el de partida."""


class YaNoEsSuIdentidad(Exception):
    """La identidad web del huevo ya no es la de esa cuenta: se vinculó."""


SIN_GACHAMON = "sin_gachamon"
YA_BAUTIZADO = "ya_bautizado"


class NombreNoVale(ValueError):
    """El nombre no pasa `sim.normalizar_nombre`; el texto es para el jugador."""


class NoSePuedeBautizar(Exception):
    """No hay a quién bautizar. `motivo` es la clave; el texto, la frase."""

    def __init__(self, motivo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.motivo = motivo


def espera_nombre(criatura: sim.Criatura) -> bool:
    """Si todavía no se le ha puesto nombre propio."""
    return not criatura.nombre or criatura.nombre == criatura.def_especie.nombre


def romper_el_huevo(
    usuario_id: str,
    guild_id: str,
    ahora: datetime,
    rng: random.Random | None = None,
    canal_id: str | None = None,
) -> sim.Criatura:
    """Hace nacer al gachamon de partida, con el nombre de su especie."""
    rng = rng or random.Random()
    # Primero se pone al día: si el único se murió, aquí se registra y sale el
    # relevo de la incubadora, y entonces sí cuenta como que le queda uno.
    db.activa_al_dia(usuario_id, guild_id, ahora)
    if db.plantel(usuario_id, guild_id):
        raise YaTieneGachamon
    especie = esp.elegir_del_huevo(rng)
    try:
        return db.crear(
            usuario_id=usuario_id,
            guild_id=guild_id,
            especie=especie.clave,
            nombre=especie.nombre,  # provisional hasta que la bautice
            stats=esp.tirar_stats_iniciales(especie, rng),
            genero=esp.tirar_genero(rng),
            caracter=per.tirar_caracter(rng),
            ahora=ahora,
            canal_id=canal_id,
            cuenta_vigente=True,
        )
    except db.IdentidadCaducada:
        raise YaNoEsSuIdentidad from None
    except (sqlite3.IntegrityError, ValueError):
        # Índice único: dos huevos a la vez. ValueError: plantel lleno.
        raise YaTieneGachamon from None


def bautizar(
    usuario_id: str, guild_id: str, nombre: str, ahora: datetime
) -> sim.Criatura:
    """Le pone nombre a la activa, sólo si todavía lo espera.

    El nombre de su especie no vale: `espera_nombre` lo lee como «sin nombre»,
    y el bautizo se repetiría.
    """
    try:
        nombre = sim.normalizar_nombre(nombre)
    except ValueError as error:
        raise NombreNoVale(str(error)) from None
    # Por si la activa se murió: se registra y, si hay relevo, es a él.
    db.activa_al_dia(usuario_id, guild_id, ahora)

    def puede(activa: sim.Criatura) -> bool:
        if not espera_nombre(activa):
            return False
        # Se mira aquí, con la activa releída en la transacción: es su especie.
        if nombre.casefold() == activa.def_especie.nombre.casefold():
            raise NombreNoVale("Ese es el nombre de su especie. Ponle uno propio.")
        return True

    resultado, criatura = db.poner_nombre_a_la_activa(
        usuario_id, guild_id, nombre, puede
    )
    if resultado == "sin_gachamon":
        raise NoSePuedeBautizar(SIN_GACHAMON, "No tienes ningún gachamon vivo.")
    if resultado == "no_puede":
        raise NoSePuedeBautizar(YA_BAUTIZADO, "Tu gachamon ya tiene nombre.")
    return criatura
