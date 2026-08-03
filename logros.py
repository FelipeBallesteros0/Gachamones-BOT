"""Las medallas, las del gachamon y las tuyas.

Módulo puro, como `competir.py`: no toca la base ni Discord. Se le pasa un
diccionario de **hechos** y dice qué logros cumple. Así todos se pueden
probar sin partida y sin red.

Hay dos dueños y conviene no confundirlos:

* **Casi todas son del gachamon**: dos gachamones de la misma persona llevan
  medallas distintas, y si uno se muere se va con las suyas. Es lo que hace que
  signifiquen algo.
* **Las tres de la persona** —Domador, Flautista y Uno entre veinticinco— son
  tuyos y se quedan aunque se te muera el plantel entero. A la aventura vas tú,
  así que convencer a un salvaje lo haces tú; y que te salga una rara es tu
  suerte, no un mérito suyo.

Los hechos del gachamon vienen de dos sitios y `hechos_de()` los junta: el
**marcador**, que cuenta lo que va pasando y vive en la base, y la **criatura
misma**, de donde salen el nivel, la edad y si sigue viva. Los de la persona los
junta `hechos_de_la_persona()`, con su propio marcador y con las especies que ha
tenido alguna vez.
"""
from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime

import especies as esp
import simulacion as sim

# De quién es cada medalla. Va en el propio logro y no en dos listas sueltas
# para que el catálogo siga siendo uno solo: la del panel, la de los totales y
# la de quién cobra qué salen todas de aquí.
GACHAMON = "gachamon"
PERSONA = "persona"

# --- Claves del marcador ----------------------------------------------------
#
# Van aquí y no en `db.py` porque son parte del juego: quien añada un logro
# nuevo mira esta lista para saber qué puede contar. Hay dos marcadores, uno por
# dueño, y una clave pertenece a uno o al otro pero nunca a los dos.

# Del gachamon.
CARRERAS = "carreras_ganadas"
SUMOS = "sumos_ganados"
# Aparte de `SUMOS` aunque las dos sean peleas: apuntarlos juntos cobraría
# «Yokozuna» con tótems, y no habría forma de separarlos después.
TOTEMS = "totems_ganados"
LABERINTOS = "laberintos_ganados"
TORNEOS = "torneos_ganados"
AVENTURAS = "aventuras"
NODOS = "nodos_superados"
CUIDADOS = "cuidados"

# Los biomas pisados se guardan uno por clave —`bioma:volcan`— en vez de como
# un número: así «pisar los diez» se puede comprobar de verdad, y no se cuenta
# diez veces el mismo sitio.
PREFIJO_BIOMA = "bioma:"

# De la persona.
RECLUTADOS = "salvajes_reclutados"

# Hechos que no salen del marcador sino de la criatura.
NIVEL = "nivel"
VICTORIAS = "victorias"
DIAS_DE_VIDA = "dias_de_vida"
BIOMAS_PISADOS = "biomas_pisados"
NACIO_EN_LA_ALFA = "nacio_en_la_alfa"
SIGUE_VIVA = "sigue_viva"

# Hecho que no sale del marcador sino del historial de la persona: si alguna de
# sus criaturas fue rara, valgan vivas o muertas.
TUVO_RARA = "tuvo_rara"

# Hasta cuándo cuenta haber estado en la alfa. Con `None` la alfa **sigue
# abierta** y cualquiera que nazca ahora se lleva la medalla; el día que se
# quiera cerrar, se pone la fecha aquí y los que nazcan después ya no.
FIN_DE_LA_ALFA: datetime | None = None


@dataclass(frozen=True)
class Logro:
    clave: str
    nombre: str
    como: str        # cómo se gana, tal como se le cuenta a quien juega
    hecho: str       # qué hecho se mira
    meta: int        # cuánto hace falta
    gemas: int
    de_quien: str = GACHAMON


LOGROS: tuple[Logro, ...] = (
    # --- Competir ---------------------------------------------------------
    Logro("primera_sangre", "Primera sangre", "gana tu primera competencia",
          VICTORIAS, 1, 5),
    Logro("velocista", "Velocista", "gana 10 carreras", CARRERAS, 10, 10),
    Logro("bolido", "Bólido", "gana 100 carreras", CARRERAS, 100, 50),
    Logro("luchador", "Luchador", "gana 10 sumos", SUMOS, 10, 10),
    Logro("yokozuna", "Yokozuna", "gana 100 sumos", SUMOS, 100, 50),
    Logro("asaltante", "Asaltante", "gana 10 asaltos al tótem", TOTEMS, 10, 10),
    Logro("dinastia", "Dinastía", "gana 10 torneos", TORNEOS, 10, 40),
    # --- Salir al campo ---------------------------------------------------
    Logro("explorador", "Explorador", "sal de aventura 10 veces",
          AVENTURAS, 10, 10),
    Logro("cartografo", "Cartógrafo", "pisa los diez biomas",
          BIOMAS_PISADOS, 10, 30),
    Logro("domador", "Domador", "convence a tu primer salvaje",
          RECLUTADOS, 1, 10, PERSONA),
    Logro("flautista", "Flautista", "convence a diez",
          RECLUTADOS, 10, 40, PERSONA),
    Logro("paso_firme", "Paso firme", "supera 50 nodos del árbol",
          NODOS, 50, 20),
    # --- Vivir y crecer ---------------------------------------------------
    Logro("bien_criado", "Bien criado", "llega a adulto grande", NIVEL, 5, 15),
    Logro("veterano", "Veterano", "cumple 30 días de vida", DIAS_DE_VIDA, 30, 25),
    Logro("consentido", "Consentido", "recibe 100 cuidados", CUIDADOS, 100, 15),
    Logro("malcriado", "Malcriado", "recibe 500 cuidados", CUIDADOS, 500, 30),
    # --- De los que no se repiten -----------------------------------------
    Logro("de_la_alfa", "De la alfa", "haber estado aquí desde el principio",
          NACIO_EN_LA_ALFA, 1, 25),
    Logro("uno_entre_veinticinco", "Uno entre veinticinco",
          "que te salga una especie rara", TUVO_RARA, 1, 20, PERSONA),
    Logro("superviviente", "Superviviente", "100 aventuras y seguir vivo",
          AVENTURAS, 100, 30),
)

POR_CLAVE = {logro.clave: logro for logro in LOGROS}


def del_gachamon() -> tuple[Logro, ...]:
    return tuple(logro for logro in LOGROS if logro.de_quien == GACHAMON)


def de_la_persona() -> tuple[Logro, ...]:
    return tuple(logro for logro in LOGROS if logro.de_quien == PERSONA)


def hechos_de(
    criatura: sim.Criatura, marcador: dict[str, int], ahora: datetime
) -> dict[str, int]:
    """Todo lo que puede desbloquear algo, en un solo diccionario.

    Junta el marcador con lo que ya se sabía de la criatura. Los booleanos van
    como 0/1 para que la condición sea siempre la misma comparación y no haya
    dos formas de escribir un logro.
    """
    nacio_en_la_alfa = (
        FIN_DE_LA_ALFA is None or criatura.nacida_en < FIN_DE_LA_ALFA
    )
    hechos = dict(marcador)
    hechos.update({
        NIVEL: criatura.nivel,
        VICTORIAS: criatura.victorias,
        DIAS_DE_VIDA: (ahora - criatura.nacida_en).days,
        BIOMAS_PISADOS: sum(
            1 for clave in marcador if clave.startswith(PREFIJO_BIOMA)
        ),
        NACIO_EN_LA_ALFA: 1 if nacio_en_la_alfa else 0,
        SIGUE_VIVA: 1 if criatura.viva else 0,
    })
    return hechos


def hechos_de_la_persona(
    marcador: dict[str, int], especies: Collection[str]
) -> dict[str, int]:
    """Lo que puede desbloquear algo tuyo, en un solo diccionario.

    `especies` son las de **todas** tus criaturas, vivas y muertas: que te haya
    salido una rara no deja de haber pasado porque se te muera.
    """
    hechos = dict(marcador)
    hechos[TUVO_RARA] = 1 if any(
        esp.ESPECIES[clave].rareza == esp.RARA for clave in especies
    ) else 0
    return hechos


def cumplidos(hechos: dict[str, int], de_quien: str) -> tuple[Logro, ...]:
    """Los logros de ese dueño que se cumplen ahora mismo.

    Dice cuáles **cumple**, no cuáles son nuevos: quién los tenía ya y a quién
    hay que pagarle lo decide `db`, que es quien recuerda. Separarlo así es lo
    que permite probarlos todos sin base de datos.

    `de_quien` no lleva valor por defecto a propósito: quien lo olvidara
    evaluaría el juego de medallas equivocado contra hechos que no le tocan, y
    sin enterarse.
    """
    conseguidos = [
        logro for logro in LOGROS
        if logro.de_quien == de_quien and hechos.get(logro.hecho, 0) >= logro.meta
    ]
    # Superviviente pide además seguir en pie, y es el único con dos
    # condiciones: se trata aparte en vez de complicar la forma de `Logro` por
    # un caso.
    if not hechos.get(SIGUE_VIVA, 1):
        conseguidos = [l for l in conseguidos if l.clave != "superviviente"]
    return tuple(conseguidos)


def clave_de_bioma(bioma: str) -> str:
    return f"{PREFIJO_BIOMA}{bioma}"
