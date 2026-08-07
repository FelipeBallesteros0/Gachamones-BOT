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

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jardin
import simulacion as sim

# Cuánto dura la estancia en el refugio. Empieza a contar la primera vez que se
# mira el hogar, no al desplegar: quien no juegue en un mes no llega y se lo
# encuentra gastado.
DIAS_DE_REFUGIO = 7

SUELO = "═"          # tablas, en vez de la tierra del jardín

# Lo máximo que puede sumar un mueble. Es lo que hace que los techos de abajo
# sean alcanzables: con muebles de +6, la casa pequeña se quedaría a dos puntos
# de su techo para siempre y el número estaría mintiendo. Hay un test que ata las
# tres cosas —techos, huecos y catálogo— para que no puedan separarse.
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
    # Cuántos gachamones viven dentro. Coincide con `huecos` a propósito: un
    # número menos que recordar, y la lectura sale sola —una casa pequeña tiene
    # sitio para tres cosas, sean muebles o inquilinos—. El refugio se queda en
    # 0, que aquí significa **sin límite**: es adonde va quien no cabe en
    # ninguna parte, así que no puede llenarse.
    aforo: int = 0


EL_REFUGIO = Casa(
    clave=REFUGIO, nombre="Refugio", precio=0,
    comodidad=75, huecos=0, techo=75, alto_tejado=2, tamano=0,
    cobertizo=True,
)

CATALOGO: dict[str, Casa] = {
    casa.clave: casa
    for casa in (
        Casa("pequena", "Casa pequeña", 200, 80, 3, 100, 3, 1, aforo=3),
        Casa("mediana", "Casa mediana", 500, 85, 6, 125, 4, 2, aforo=6),
        Casa("grande", "Casa grande", 1200, 90, 10, 150, 5, 3, aforo=10),
    )
}

# Cuántas casas puede tener alguien a la vez. Tres, y el número sale de una
# restricción de Discord y no del gusto: los bancales del huerto se listan uno
# por fila en un desplegable, que admite 25 opciones. Tres casas grandes son 21
# bancales y caben; con una cuarta se pasaría y el menú del huerto reventaría
# justo para quien más ha invertido en él.
MAXIMO_CASAS = 3


def buscar(clave: str | None) -> Casa | None:
    """La casa de esa clave, o `None` si no hay ninguna o no se reconoce."""
    if clave is None:
        return None
    if clave == REFUGIO:
        return EL_REFUGIO
    return CATALOGO.get(clave)


@dataclass(frozen=True)
class CasaPropia:
    """Una casa concreta de alguien: cuál es, y qué tiene puesto dentro.

    Lleva `id` porque ahora se pueden tener varias del mismo tamaño y hay que
    poder distinguirlas: los gachamones y los muebles apuntan a una en concreto,
    no a «la mediana».
    """

    id: int
    casa: Casa
    # Los muebles que hay dentro. Se sigue teniendo **uno de cada por persona**;
    # lo que se elige es en cuál de tus casas cuelga.
    puestos: tuple[str, ...] = ()

    @property
    def comodidad(self) -> int:
        return comodidad_de(self.casa, self.puestos)

    def caben_mas_inquilinos(self, cuantos_dentro: int) -> bool:
        return cuantos_dentro < self.casa.aforo


@dataclass(frozen=True)
class Hogar:
    """Todo lo que alguien tiene donde vivir.

    Sin ninguna casa manda `refugio_hasta`: en el futuro es que sigue en el
    refugio, y en el pasado que se ha quedado a la intemperie. Ese reloj es **de
    la persona** y no de una casa, y por eso sobrevive a comprarlas y venderlas.
    """

    casas: tuple[CasaPropia, ...] = ()
    refugio_hasta: datetime = datetime.min.replace(tzinfo=timezone.utc)
    # Si otros pueden verlo con `/visitar`. Nace abierto, como todo lo demás del
    # bot: `/mascota @alguien` y `/jardin` ya enseñan lo de cualquiera.
    publica: bool = True

    def estado(self, ahora: datetime) -> str:
        """En qué situación está la **persona**, no un gachamon suyo."""
        if self.casas:
            return PROPIA
        return REFUGIO if ahora < self.refugio_hasta else INTEMPERIE

    def casa_por_id(self, casa_id: int | None) -> CasaPropia | None:
        """La casa de ese id, si sigue siendo suya.

        Devuelve `None` para un id desconocido y no revienta: una criatura puede
        apuntar a una casa que se acaba de vender, y eso significa que vive en el
        refugio, no que haya un error.
        """
        if casa_id is None:
            return None
        return next((c for c in self.casas if c.id == casa_id), None)

    def donde_vive(self, casa_id: int | None) -> Casa:
        """En qué casa vive de hecho ese gachamon. Sin casa, el refugio."""
        propia = self.casa_por_id(casa_id)
        return propia.casa if propia else EL_REFUGIO

    def estado_de(self, casa_id: int | None, ahora: datetime) -> str:
        """La situación de un gachamon concreto.

        No es la de la persona: quien tiene casa pero no le cabe este gachamon
        lo tiene en el refugio, y si además se le acabó la estancia, a la
        intemperie. Es lo que hace que repartirlos importe.
        """
        if self.casa_por_id(casa_id) is not None:
            return PROPIA
        return REFUGIO if ahora < self.refugio_hasta else INTEMPERIE

    def comodidad_de(self, casa_id: int | None, ahora: datetime) -> int:
        """Lo cómodo que vive ese gachamon, muebles incluidos."""
        if self.estado_de(casa_id, ahora) == INTEMPERIE:
            return 0
        propia = self.casa_por_id(casa_id)
        return propia.comodidad if propia else EL_REFUGIO.comodidad

    def puede_comprar_otra(self) -> bool:
        return len(self.casas) < MAXIMO_CASAS


def estancia_desde(ahora: datetime) -> datetime:
    return ahora + timedelta(days=DIAS_DE_REFUGIO)


def puede_mejorarse_a(propia: CasaPropia, casa: Casa) -> bool:
    """Mejorar **esa** casa. Sólo se sube de tamaño.

    Bajar se hace vendiéndola primero, y así el 20 % que se pierde es explícito
    en vez de una sorpresa dentro de una compra. La regla es la de siempre; lo
    único que cambia es que ahora se aplica a una casa concreta y no a «la
    casa», porque se pueden tener varias y cada una se mejora por su cuenta.
    """
    return casa.tamano > propia.casa.tamano


# Lo que dan por una casa usada. El 20 % que se pierde es lo que evita comprar y
# vender por deporte, y con los precios de hoy sale exacto: 160, 400 y 960.
#
# Coincide con el ticket del refugio, y no por casualidad: vender la pequeña
# cuesta 40 netos, que es lo que vale el ticket por la misma semana. Comprar y
# vender para tener techo no es un atajo, es la misma tarifa por otro camino.
PORCENTAJE_DE_REVENTA = 80


def lo_que_dan_por(casa: Casa) -> int:
    """Con enteros y no con flotantes: el dinero no admite un 159,99999."""
    return casa.precio * PORCENTAJE_DE_REVENTA // 100


# --- El mobiliario ---------------------------------------------------------
#
# **Todos los muebles suman comodidad**, y ninguno es sólo decorativo. Con los
# huecos contados —tres en la casa pequeña—, un mueble que no hiciera nada sería
# una trampa: ocuparía sitio a cambio de nada y quien lo comprara habría perdido
# el hueco. Lo que cambia entre ellos es cuánto suman y lo que cuestan.
#
# Se pagan con asciicoins, como la casa: los asciigems son del aspecto del
# gachamon y ésta es la otra economía. Una moneda por categoría, que es lo que
# hace legible la tienda.


@dataclass(frozen=True)
class Mueble:
    clave: str
    nombre: str
    emoji: str
    precio: int
    comodidad: int


MUEBLES: dict[str, Mueble] = {
    mueble.clave: mueble
    for mueble in (
        Mueble("felpudo", "Felpudo", "🚪", 30, 2),
        Mueble("maceta", "Maceta", "🪴", 50, 3),
        Mueble("cuadro", "Cuadro", "🖼️", 50, 3),
        Mueble("estanteria", "Estantería", "🗄️", 80, 4),
        Mueble("lampara", "Lámpara", "💡", 80, 4),
        Mueble("alfombra", "Alfombra", "🧶", 120, 5),
        Mueble("cortinas", "Cortinas", "🪟", 120, 5),
        Mueble("cojines", "Cojines", "🛋️", 180, 6),
        Mueble("fuente", "Fuente", "⛲", 180, 6),
        Mueble("chimenea", "Chimenea", "🔥", 180, 6),
        Mueble("calefactor", "Calefactor", "🌡️", 280, 7),
        Mueble("cama", "Cama grande", "🛏️", 280, 7),
        Mueble("ventanal", "Ventanal", "🏞️", 280, 7),
        Mueble("biblioteca", "Biblioteca", "📚", 280, 7),
    )
}


def comodidad_de(casa: Casa, puestos: Collection[str]) -> int:
    """La comodidad de una casa con esos muebles dentro, sin pasar del techo.

    Los que no estén en el catálogo no suman: si algún día se retira un mueble,
    quien lo tuviera puesto no puede quedarse con una comodidad que no se puede
    volver a conseguir.
    """
    suma = sum(MUEBLES[c].comodidad for c in puestos if c in MUEBLES)
    return min(casa.techo, casa.comodidad + suma)


def caben_mas(casa: Casa, puestos: Collection[str]) -> bool:
    return len(puestos) < casa.huecos


# --- Lo que el hogar le hace al gachamon ------------------------------------
#
# Sólo a la **activa**: las de la incubadora siguen congeladas, como manda el
# invariante. Un hogar no puede despertarlas sin romper lo que hace viable tener
# diez.
#
# Dos efectos, simétricos a propósito para que se puedan explicar en una frase:
#
# * **A la intemperie todo cae un 25 % más rápido**, y el hambre no baja del
#   suelo: se pasa mal, pero no se pierde el gachamon por no tener casa.
# * **La comodidad por encima del refugio frena el ánimo**, hasta ese mismo 25 %
#   en la casa mejor amueblada.
#
# El hambre no la toca la comodidad, y es a propósito: `muere_en` va precalculado
# en la base para que el bucle de la muerte sea una consulta y no una simulación
# de todas las filas. Si la casa cambiara el ritmo del hambre, ese instante
# guardado dejaría de ser cierto en cuanto alguien se mudara.

PENALIZACION_INTEMPERIE = 1.25
ALIVIO_MAXIMO_DE_ANIMO = 0.25

# Por debajo de esto el hambre no baja mientras se esté a la intemperie. Deja
# margen de sobra por encima del aviso: quien por fin compre casa no puede
# encontrarse con que su gachamon se muere a los dos minutos de mudarse.
SUELO_DE_HAMBRE_A_LA_INTEMPERIE = 25.0


def ritmo_de(
    hogar: Hogar, ahora: datetime, casa_id: int | None = None
) -> sim.Ritmo:
    """Cómo le pasa el tiempo al gachamon que vive en esa casa.

    El ritmo es **suyo y no de su dueño**: con varias casas, dos gachamones de
    la misma persona pueden vivir en sitios distintos, y quien no cabe en
    ninguna está en el refugio aunque su dueño tenga tres.
    """
    if hogar.estado_de(casa_id, ahora) == INTEMPERIE:
        return sim.Ritmo(
            hambre=PENALIZACION_INTEMPERIE,
            animo=PENALIZACION_INTEMPERIE,
            limpieza=PENALIZACION_INTEMPERIE,
            suelo_de_hambre=SUELO_DE_HAMBRE_A_LA_INTEMPERIE,
        )
    return sim.Ritmo(animo=alivio_de_animo(hogar.comodidad_de(casa_id, ahora)))


def alivio_de_animo(comodidad: int) -> float:
    """El multiplicador del ánimo: 1.0 en el refugio y 0.75 en la mejor casa.

    Se calcula del catálogo —del techo más alto que existe— y no de un número
    escrito, para que añadir una casa mejor no deje esto desfasado.
    """
    mejor = max(casa.techo for casa in CATALOGO.values())
    de_mas = max(0, comodidad - EL_REFUGIO.comodidad)
    margen = mejor - EL_REFUGIO.comodidad
    return 1.0 - ALIVIO_MAXIMO_DE_ANIMO * min(1.0, de_mas / margen)


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
