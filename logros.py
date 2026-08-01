"""Las medallas de cada gachamon.

Módulo puro, como `competir.py`: no toca la base ni Discord. Se le pasa un
diccionario de **hechos** —lo que ese gachamon lleva hecho— y dice qué logros
cumple. Así los dieciocho se pueden probar sin partida y sin red.

Son **del gachamon y no de quien lo cuida**, que es lo que se pidió: dos
gachamones de la misma persona llevan medallas distintas, y si uno se muere se
va con las suyas. Es lo que hace que signifiquen algo.

Los hechos vienen de dos sitios y `hechos_de()` los junta:

* el **marcador**, que cuenta lo que va pasando (carreras ganadas, aventuras,
  biomas pisados) y vive en la base;
* la **criatura misma**, de donde salen el nivel, la edad, la especie y si sigue
  viva — datos que ya se guardaban y no necesitan contador nuevo.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import especies as esp
import simulacion as sim

# --- Claves del marcador ----------------------------------------------------
#
# Van aquí y no en `db.py` porque son parte del juego: quien añada un logro
# nuevo mira esta lista para saber qué puede contar.
CARRERAS = "carreras_ganadas"
SUMOS = "sumos_ganados"
TORNEOS = "torneos_ganados"
AVENTURAS = "aventuras"
NODOS = "nodos_superados"
RECLUTADOS = "salvajes_reclutados"
CUIDADOS = "cuidados"

# Los biomas pisados se guardan uno por clave —`bioma:volcan`— en vez de como
# un número: así «pisar los diez» se puede comprobar de verdad, y no se cuenta
# diez veces el mismo sitio.
PREFIJO_BIOMA = "bioma:"

# Hechos que no salen del marcador sino de la criatura.
NIVEL = "nivel"
VICTORIAS = "victorias"
DIAS_DE_VIDA = "dias_de_vida"
BIOMAS_PISADOS = "biomas_pisados"
ES_RARA = "es_rara"
NACIO_EN_LA_ALFA = "nacio_en_la_alfa"
SIGUE_VIVA = "sigue_viva"

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


LOGROS: tuple[Logro, ...] = (
    # --- Competir ---------------------------------------------------------
    Logro("primera_sangre", "Primera sangre", "gana tu primera competencia",
          VICTORIAS, 1, 5),
    Logro("velocista", "Velocista", "gana 10 carreras", CARRERAS, 10, 10),
    Logro("bolido", "Bólido", "gana 100 carreras", CARRERAS, 100, 50),
    Logro("luchador", "Luchador", "gana 10 sumos", SUMOS, 10, 10),
    Logro("yokozuna", "Yokozuna", "gana 100 sumos", SUMOS, 100, 50),
    Logro("dinastia", "Dinastía", "gana 10 torneos", TORNEOS, 10, 40),
    # --- Salir al campo ---------------------------------------------------
    Logro("explorador", "Explorador", "sal de aventura 10 veces",
          AVENTURAS, 10, 10),
    Logro("cartografo", "Cartógrafo", "pisa los diez biomas",
          BIOMAS_PISADOS, 10, 30),
    Logro("domador", "Domador", "convence a tu primer salvaje",
          RECLUTADOS, 1, 10),
    Logro("flautista", "Flautista", "convence a diez", RECLUTADOS, 10, 40),
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
          "ser de una especie rara", ES_RARA, 1, 20),
    Logro("superviviente", "Superviviente", "100 aventuras y seguir vivo",
          AVENTURAS, 100, 30),
)

POR_CLAVE = {logro.clave: logro for logro in LOGROS}


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
        DIAS_DE_VIDA: int(criatura.edad_horas(ahora) // 24),
        BIOMAS_PISADOS: sum(
            1 for clave in marcador if clave.startswith(PREFIJO_BIOMA)
        ),
        ES_RARA: int(criatura.def_especie.rareza == esp.RARA),
        NACIO_EN_LA_ALFA: int(nacio_en_la_alfa),
        SIGUE_VIVA: int(criatura.viva),
    })
    return hechos


def cumplidos(hechos: dict[str, int]) -> tuple[Logro, ...]:
    """Los logros que ese gachamon cumple ahora mismo.

    Dice cuáles **cumple**, no cuáles son nuevos: quién los tenía ya y a quién
    hay que pagarle lo decide `db`, que es quien recuerda. Separarlo así es lo
    que permite probar los dieciocho sin base de datos.
    """
    conseguidos = [
        logro for logro in LOGROS if hechos.get(logro.hecho, 0) >= logro.meta
    ]
    # Superviviente pide además seguir en pie, y es el único con dos
    # condiciones: se trata aparte en vez de complicar la forma de `Logro` por
    # un caso.
    if not hechos.get(SIGUE_VIVA, 1):
        conseguidos = [l for l in conseguidos if l.clave != "superviviente"]
    return tuple(conseguidos)


def clave_de_bioma(bioma: str) -> str:
    return f"{PREFIJO_BIOMA}{bioma}"
