"""Nacer: encontrar al primero, unirse un recluta y bautizar.

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
    """El de partida es sólo uno: el de la primera aventura.

    `solo_el_primero_sin_nombre` dice si lo único que tiene es ese primero,
    todavía sin nombre (un solo gachamon vivo, que espera el suyo): la ventana
    entre encontrarlo y ponerle nombre.
    """

    def __init__(self, solo_el_primero_sin_nombre: bool = False) -> None:
        super().__init__()
        self.solo_el_primero_sin_nombre = solo_el_primero_sin_nombre


class YaNoEsSuIdentidad(Exception):
    """La identidad web que iba a recibir al de partida ya no es la de esa
    cuenta: se vinculó."""


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


def nombre_sugerido(criatura: sim.Criatura) -> str:
    """El nombre que se le propone a su dueño al ponérselo: uno de la lista,
    como el de un recluta (`nombre_de_recluta`), y siempre el mismo para ese
    gachamon, porque el azar se siembra con su id y no con el reloj."""
    return nombre_de_recluta(
        criatura.usuario_id, criatura.guild_id, criatura.especie,
        random.Random(criatura.id),
    )


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


def encontrar_al_primero(
    usuario_id: str,
    guild_id: str,
    ahora: datetime,
    rng: random.Random | None = None,
) -> sim.Criatura:
    """El gachamon de partida, el que se gana en la primera aventura.

    Sale de las diez del huevo, con sus pesos (`esp.elegir_del_huevo`), nace
    activo y con el nombre de su especie, provisional hasta que su dueño le
    ponga uno (por eso lo espera). La hace cualquiera sin ningún gachamon vivo,
    también quien se quedó sin ninguno antes del día del cambio; con alguno vivo
    levanta `YaTieneGachamon`, que dice si ese alguno es sólo el primero, todavía
    sin nombre (lo mira en el plantel que ya leyó).

    Pide una cama libre, como todos: sin ella deja pasar `db.SinCamaLibre` y no
    crea nada. Si la cuenta se vinculó mientras tanto, `YaNoEsSuIdentidad`.
    Dos a la vez dejan uno solo: al segundo lo para la cama, que ya ocupó el
    primero, o el índice de la activa; en los dos casos, `YaTieneGachamon`.
    """
    rng = rng or random.Random()
    # El remiendo de siempre: si quedó un plantel sin activo, aquí pasa a serlo
    # uno de los vivos. Con plantel, vivo aunque no tenga activo, no hay primero.
    db.activa_al_dia(usuario_id, guild_id, ahora)
    plantel = db.plantel(usuario_id, guild_id)
    if plantel:
        raise YaTieneGachamon(
            solo_el_primero_sin_nombre=len(plantel) == 1 and espera_nombre(plantel[0])
        )
    especie = esp.elegir_del_huevo(rng)
    try:
        return db.crear(
            usuario_id=usuario_id,
            guild_id=guild_id,
            especie=especie.clave,
            nombre=especie.nombre,  # provisional hasta que le ponga uno
            stats=esp.tirar_stats_iniciales(especie, rng),
            genero=esp.tirar_genero(rng),
            caracter=per.tirar_caracter(rng),
            ahora=ahora,
            cuenta_vigente=True,
            pide_cama=True,
        )
    except db.IdentidadCaducada:
        raise YaNoEsSuIdentidad from None
    except db.SinCamaLibre:
        # Si mientras tanto llegó otro, la cama que faltó es la que ocupó él.
        if db.plantel(usuario_id, guild_id):
            raise YaTieneGachamon from None
        raise
    except sqlite3.IntegrityError:
        # Índice único de la activa: dos a la vez, con cama para los dos.
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
