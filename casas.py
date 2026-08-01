"""El hogar: dónde vive el plantel de cada persona.

Módulo puro, como `jardin.py`: catálogo y dibujo, sin base de datos ni Discord.

Nadie se queda en la calle de entrada. Se empieza en el **refugio**, que es común
a todo el mundo y no se decora, y desde ahí se compra casa. El refugio caduca:
es una red de seguridad, no un sitio donde quedarse.

El techo de comodidad **sube con el tamaño** y no se queda en 100 para las tres.
Con un tope común, una casa grande desperdiciaría siete de sus diez huecos, y
comprarla sólo valdría para mirarla. Por eso la comodidad deja de ser un
porcentaje y pasa a ser una puntuación: se enseña como número y nunca con `%`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import jardin
import simulacion as sim

# Cuánto dura la estancia en el refugio. Empieza a contar la primera vez que se
# mira el hogar, no al desplegar: quien no juegue en un mes no llega y se lo
# encuentra gastado.
DIAS_DE_REFUGIO = 7

SUELO = "═"          # tablas, en vez de la tierra del jardín

# Lo máximo que podrá sumar un mueble cuando lleguen, en la entrega 2. Vive aquí
# y no allí porque es lo que hace que los techos de abajo sean alcanzables: con
# muebles de +6, la casa pequeña se quedaría a dos puntos de su techo para
# siempre y el número estaría mintiendo. Hay un test que ata las dos cosas.
MAX_COMODIDAD_POR_MUEBLE = 7

# Los tres estados posibles. Salen de los datos y no de una columna aparte, que
# es lo que evita que puedan contradecirse.
PROPIA = "propia"
REFUGIO = "refugio"
INTEMPERIE = "intemperie"


@dataclass(frozen=True)
class Casa:
    clave: str
    nombre: str
    precio: int         # asciicoins; el refugio no se compra y vale 0
    comodidad: int      # la de partida, antes de amueblar
    huecos: int         # cuántos muebles caben
    techo: int          # hasta dónde puede llegar la comodidad amueblada
    alto_tejado: int
    # Cuánto manda a la hora de mudarse: sólo se puede subir. El refugio es 0,
    # así que salir de él siempre es subir.
    tamano: int
    # El refugio es un cobertizo largo y no una casa a dos aguas. Se dibuja
    # distinto a propósito: `/casa` es lo que se mira, y tener casa propia se
    # tiene que notar de un vistazo sin leer el pie.
    cobertizo: bool = False


EL_REFUGIO = Casa(
    clave=REFUGIO, nombre="Refugio", precio=0,
    comodidad=75, huecos=0, techo=75, alto_tejado=2, tamano=0,
    cobertizo=True,
)

CATALOGO: dict[str, Casa] = {
    casa.clave: casa
    for casa in (
        Casa("pequena", "Casa pequeña", 200, 80, 3, 100, 3, 1),
        Casa("mediana", "Casa mediana", 500, 85, 6, 125, 4, 2),
        Casa("grande", "Casa grande", 1200, 90, 10, 150, 5, 3),
    )
}


def buscar(clave: str | None) -> Casa | None:
    """La casa de esa clave, o `None` si no hay ninguna o no se reconoce."""
    if clave is None:
        return None
    if clave == REFUGIO:
        return EL_REFUGIO
    return CATALOGO.get(clave)


@dataclass(frozen=True)
class Hogar:
    """Dónde vive alguien ahora mismo.

    `casa` a `None` significa sin casa propia, y entonces manda `refugio_hasta`:
    en el futuro es que sigue en el refugio, y en el pasado que se ha quedado a
    la intemperie.
    """

    casa: Casa | None
    refugio_hasta: datetime

    def estado(self, ahora: datetime) -> str:
        if self.casa is not None:
            return PROPIA
        return REFUGIO if ahora < self.refugio_hasta else INTEMPERIE

    def donde(self, ahora: datetime) -> Casa:
        """Dónde vive de hecho. A la intemperie no hay comodidad que valga."""
        return self.casa or EL_REFUGIO

    def comodidad(self, ahora: datetime) -> int:
        return 0 if self.estado(ahora) == INTEMPERIE else self.donde(ahora).comodidad


def estancia_desde(ahora: datetime) -> datetime:
    return ahora + timedelta(days=DIAS_DE_REFUGIO)


def puede_mudarse_a(hogar: Hogar, casa: Casa) -> bool:
    """Sólo se sube de tamaño. Comprar lo que ya tienes no es una mudanza."""
    return casa.tamano > (hogar.casa.tamano if hogar.casa else 0)


# --- El dibujo -------------------------------------------------------------

def _centrado(pieza: str, ancho: int) -> str:
    """La pieza puesta sobre el eje del marco **con sus bordes**.

    Sobre `ancho + 2` y no sobre `ancho`: el `╭` de la izquierda corre el
    interior una columna, así que centrando sobre el hueco el adorno queda una
    columna a la izquierda de la casa. Es medio carácter, y se ve.
    """
    return " " * max(0, (ancho + 2 - len(pieza)) // 2) + pieza


def tejado(casa: Casa, ancho: int = jardin.ANCHO) -> list[str]:
    """El tejado de una casa, centrado sobre el eje del marco.

    El refugio lleva un cobertizo largo y plano; las casas, dos aguas que crecen
    con el tamaño.
    """
    if casa.cobertizo:
        ala = (ancho * 2 // 3) // 2 * 2      # par, para que el centrado sea exacto
        # La cumbrera se centra con el mismo ancho que el alero —los espacios
        # cuentan— y se le quita el sobrante al final: un espacio en blanco no se
        # ve, pero se copia y se pega con el dibujo.
        return [
            _centrado(" " + "_" * ala + " ", ancho).rstrip(),
            _centrado("/" + "_" * ala + "\\", ancho),
        ]
    return _dos_aguas(casa.alto_tejado, ancho)


def _dos_aguas(alto: int, ancho: int) -> list[str]:
    """Un tejado a dos aguas, centrado sobre el eje del marco.

    Se dibuja y no se escribe a mano justamente por eso: el eje sale del ancho
    que se le pase, así que no puede quedar descuadrado respecto del marco que
    lleva debajo. Es la clase de descuadre que ha salido una y otra vez en este
    proyecto, y siempre por centrar el adorno sobre su propio eje y no sobre el
    del dibujo.

    Cada agua se abre **de cuatro en cuatro** para que la pieza mida siempre un
    número par de columnas. Con un ancho impar, el `//2` del centrado la tira
    media columna a la izquierda y el tejado sale torcido fila a fila. Es lo que
    salió al probarlo, y hay un test que lo vigila sobre los tres tamaños.
    """
    lineas = []
    for fila in range(alto):
        hueco = 4 * fila
        relleno = ("_" if fila == alto - 1 else " ") * hueco
        agua = f"/{relleno}\\"          # ancho = 2 + hueco, siempre par
        lineas.append(_centrado(agua, ancho))
    return lineas


def render(
    criaturas: list[sim.Criatura], casa: Casa, ancho: int = jardin.ANCHO
) -> str:
    """El hogar con todos los que viven dentro."""
    cuerpo = tejado(casa, ancho)
    cuerpo.append("╭" + "─" * ancho + "╮")
    cuerpo += jardin.cuerpo_de(criaturas, ancho, SUELO, "No vive nadie aquí.")
    cuerpo.append("╰" + "─" * ancho + "╯")
    return "```ansi\n" + "\n".join(cuerpo) + "\n```"
