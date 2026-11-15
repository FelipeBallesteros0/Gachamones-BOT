"""Nacer: romper el huevo, unirse un recluta y bautizar.

Aquí está lo que decide qué nace, con qué nombre llega un recluta y cuándo se
puede bautizar; quien llama (la ruta de la web) sólo traduce el resultado.
"""
from __future__ import annotations

import random
import sqlite3
from datetime import datetime

import db
import especies as esp
import nombres
import personalidad as per
import simulacion as sim


class YaTieneGachamon(Exception):
    """El huevo es sólo el de partida."""


class YaNoEsSuIdentidad(Exception):
    """La identidad web del huevo ya no es la de esa cuenta: se vinculó."""


SIN_GACHAMON = "sin_gachamon"
YA_BAUTIZADO = "ya_bautizado"
NO_ESTA = "no_esta"


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


def puede_recibir_nombre(criatura: sim.Criatura) -> bool:
    """Si su dueño le puede poner nombre: lo espera, o el que lleva se lo puso
    él solo. En cuanto se lo pone su dueño, ya no."""
    return espera_nombre(criatura) or criatura.se_nombro_solo


def nombre_de_recluta(
    usuario_id: str, guild_id: str, especie: str, rng: random.Random
) -> str:
    """El nombre que se pone un recluta de `especie` al unirse a ese plantel:
    ni el de otro de sus vivos ni el de su especie."""
    evitar = [criatura.nombre for criatura in db.plantel(usuario_id, guild_id)]
    evitar.append(esp.ESPECIES[especie].nombre)
    return nombres.elegir(rng, evitar)


def unir_recluta(
    usuario_id: str,
    guild_id: str,
    *,
    especie: str,
    stats: tuple[int, int, int, int],
    genero: str,
    caracter: str,
    ahora: datetime,
    rng: random.Random | None = None,
    canal_id: str | None = None,
) -> sim.Criatura:
    """El salvaje que se une en una aventura, ya con el nombre que se pone él
    solo (`nombre_de_recluta`) y que su dueño le puede cambiar una vez.

    No es el activo: uno que se une no desbanca sin avisar al que salía
    contigo. El reclutamiento se le apunta a la persona en la misma
    transacción que lo crea (`db.crear` con `reclutada`). Pide una cama puesta
    libre: sin ella deja pasar `db.SinCamaLibre`, y también el
    `sqlite3.IntegrityError`, como `db.crear`.
    """
    rng = rng or random.Random()
    return db.crear(
        usuario_id=usuario_id,
        guild_id=guild_id,
        especie=especie,
        nombre=nombre_de_recluta(usuario_id, guild_id, especie, rng),
        stats=stats,
        ahora=ahora,
        genero=genero,
        caracter=caracter,
        canal_id=canal_id,
        activa=False,
        reclutada=True,
        se_nombro_solo=True,
        pide_cama=True,
    )


def romper_el_huevo(
    usuario_id: str,
    guild_id: str,
    ahora: datetime,
    rng: random.Random | None = None,
    canal_id: str | None = None,
) -> sim.Criatura:
    """Hace nacer al gachamon de partida, con el nombre de su especie."""
    rng = rng or random.Random()
    # El remiendo de siempre: si quedó un plantel sin activo, aquí pasa a serlo
    # uno de los vivos. Con plantel, vivo aunque no tenga activo, no hay huevo.
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
    """Le pone nombre a la activa, sólo si todavía lo espera o el que lleva se
    lo puso ella sola (`puede_recibir_nombre`).

    El nombre de su especie no vale: `espera_nombre` lo lee como «sin nombre»,
    y el bautizo se repetiría.
    """
    try:
        nombre = sim.normalizar_nombre(nombre)
    except ValueError as error:
        raise NombreNoVale(str(error)) from None
    # El remiendo de siempre: si quedó un plantel sin activa, se pone a uno de
    # activo antes de mirar a quién se bautiza.
    db.activa_al_dia(usuario_id, guild_id, ahora)

    def puede(activa: sim.Criatura) -> bool:
        if not puede_recibir_nombre(activa):
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


def bautizar_a(
    usuario_id: str, guild_id: str, criatura_id: int, nombre: str,
    ahora: datetime,
) -> sim.Criatura:
    """Le pone nombre a ese gachamon tuyo, sólo si todavía lo espera o el que
    lleva se lo puso él solo (`puede_recibir_nombre`).

    Es como se le cambia una vez el nombre a un recluta, que llega con uno de
    la lista. Recibe `ahora` como `bautizar`, pero no pone al día a nadie:
    sólo se le escribe el nombre, y que ya no se lo puso él solo.
    """
    try:
        nombre = sim.normalizar_nombre(nombre)
    except ValueError as error:
        raise NombreNoVale(str(error)) from None

    def puede(criatura: sim.Criatura) -> bool:
        if not puede_recibir_nombre(criatura):
            return False
        # Se mira aquí, con la criatura releída en la transacción: es su especie.
        if nombre.casefold() == criatura.def_especie.nombre.casefold():
            raise NombreNoVale("Ese es el nombre de su especie. Ponle uno propio.")
        return True

    resultado, criatura = db.poner_nombre_a(
        usuario_id, guild_id, criatura_id, nombre, puede
    )
    if resultado == "no_esta":
        raise NoSePuedeBautizar(NO_ESTA, "Ese gachamon ya no está.")
    if resultado == "no_puede":
        raise NoSePuedeBautizar(YA_BAUTIZADO, "Ese gachamon ya tiene nombre.")
    return criatura
