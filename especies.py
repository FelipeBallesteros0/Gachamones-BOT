"""Las 10 especies: arte ASCII por etapa, estadísticas base y rarezas.

Módulo puro: no importa discord ni toca la base de datos, así que se puede
testear entero sin conexión.

Cómo se guarda el arte
----------------------
Cinco etapas por diez especies, y cada una con tres estados de ánimo, serían
150 dibujos. Insostenible.

Pero mirando los dibujos, casi todos se diferencian **sólo en la cara**: el
mismo cuerpo de Pollito con `^v^`, `o.o` o `T_T`. Así que cada etapa se guarda
como una plantilla con un hueco `{cara}`, y cada especie declara sus tres
caras. Resultado: **50 dibujos y los ánimos salen gratis**.

Donde el ánimo cambia más que la cara —al Brote se le caen las hojas, la llama
de Chispa mengua— se declara el dibujo completo en `excepciones`, que gana a la
plantilla.

Las tres caras de una especie tienen que medir lo mismo: si no, sustituir una
por otra movería el resto de la línea y descuadraría el dibujo. Hay un test que
lo comprueba.

El arte se guarda con su tamaño natural; es `pantalla.py` quien lo centra y lo
rellena dentro del marco. Nada de emoji: Discord los dibuja como imágenes de
ancho variable incluso dentro de un bloque de código.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

# Códigos ANSI que Discord acepta dentro de un bloque ```ansi
GRIS = "30"
ROJO = "31"
VERDE = "32"
AMARILLO = "33"
AZUL = "34"
ROSA = "35"
CIAN = "36"
BLANCO = "37"

COMUN = "común"
POCO_COMUN = "poco común"
RARA = "rara"

# Estados de ánimo.
FELIZ = "feliz"
NORMAL = "normal"
MAL = "mal"
ANIMOS = (FELIZ, NORMAL, MAL)

# Género. Se sortea al nacer y no cambia nunca. No toca ninguna estadística:
# sólo decide los pronombres y la concordancia de todo lo que se dice de la
# criatura. Vive aquí, y no en `simulacion`, porque `concordar()` la necesitan
# hasta los nombres de etapa de más abajo y este módulo no importa a nadie.
MACHO = "macho"
HEMBRA = "hembra"
GENEROS = (MACHO, HEMBRA)

# El carácter que llevan las criaturas construidas sin decir cuál. Un test
# comprueba que sigue siendo una clave válida de `personalidad.CARACTERES`.
CARACTER_POR_DEFECTO = "alegre"

# Las cinco etapas, en orden. El nivel de la criatura decide en cuál está:
# nivel 1 = bebé, nivel 5 o más = adulto grande.
BEBE = "bebe"
NINO = "nino"
ADOLESCENTE = "adolescente"
ADULTO = "adulto"
ADULTO_GRANDE = "adulto_grande"
ETAPAS = (BEBE, NINO, ADOLESCENTE, ADULTO, ADULTO_GRANDE)

# Con la marca «{masculino/femenino}» que resuelve `personalidad.concordar()`.
NOMBRES_ETAPA = {
    BEBE: "cría",
    NINO: "niñ{o/a}",
    ADOLESCENTE: "adolescente",
    ADULTO: "adult{o/a}",
    ADULTO_GRANDE: "adult{o/a} grande",
}


@dataclass(frozen=True)
class Especie:
    clave: str
    nombre: str
    emoji: str
    color: str
    fuerza: int
    velocidad: int
    salud: int
    rareza: str
    peso: float
    descripcion: str
    evolucion: str          # cómo se llama de mayor, para el anuncio
    caras: dict[str, str]   # ánimo -> los caracteres que van en {cara}
    arte: dict[str, str]    # etapa -> plantilla
    # Concuerda con el NOMBRE de la especie, no con el género de la criatura:
    # «una Chispa macho» es lo correcto, igual que «una jirafa macho». Son dos
    # ejes distintos y no hay que mezclarlos.
    articulo: str = "un"
    excepciones: dict[tuple[str, str], str] = field(default_factory=dict)

    @property
    def total_base(self) -> int:
        return self.fuerza + self.velocidad + self.salud


# --------------------------------------------------------------------------
# Arte compartido
# --------------------------------------------------------------------------

HUEVO = r"""
   _____
  /  .  \
 | .   . |
 |   .   |
  \_____/
"""

HUEVO_RAJADO = r"""
   __/\_
  /  .  \
 |../\.  |
 |_/  \._|
  \_____/
"""

LAPIDA = r"""
   _______
  /       \
 |   R.I.P |
 |         |
 |_________|
"""


ESPECIES: dict[str, Especie] = {}


def _registrar(especie: Especie) -> None:
    ESPECIES[especie.clave] = especie


# --------------------------------------------------------------------------
# Las 10 especies
#
# Comunes y poco comunes reparten 24 puntos entre las tres estadísticas:
# ninguna es mejor, sólo distinta. El dragón lleva 30 y por eso sólo sale el
# 4% de las veces.
# --------------------------------------------------------------------------

_registrar(Especie(
    clave="pollito", nombre="Pollito", emoji="🐥", color=AMARILLO,
    fuerza=4, velocidad=14, salud=6, rareza=COMUN, peso=12.0,
    descripcion="Corre como si le persiguieran. Porque suele ser el caso.",
    evolucion="Gallo de Bronce",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "T_T"},
    arte={
        BEBE: r"""
   _
  (,)
 ({cara})
  ^ ^
""",
        NINO: r"""
    _
   (,)
  ({cara})
 <(   )>
   ^ ^
""",
        ADOLESCENTE: r"""
   \|/
   (,)
  ({cara})
 <(   )>>
   ^ ^
""",
        ADULTO: r"""
   \|/,
   (,,)
  ({cara})
 <(    )>>>
   ^^ ^^
""",
        ADULTO_GRANDE: r"""
   \\|//
   (,,,)
   ({cara})
 <(     )>>>>
  ^^^ ^^^
""",
    },
))

_registrar(Especie(
    clave="brote", nombre="Brote", emoji="🌱", color=VERDE,
    fuerza=7, velocidad=3, salud=14, rareza=COMUN, peso=12.0,
    descripcion="Aguanta lo que le echen. Moverse ya es otro tema.",
    evolucion="Árbol Anciano",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
  \|/
 ({cara})
   |
  _|_
""",
        NINO: r"""
   \ | /
    \|/
  ( {cara} )
    |||
   \___/
""",
        ADOLESCENTE: r"""
  \  |  /
 ---{cara}---
    |||
    |||
   \___/
""",
        ADULTO: r"""
  \\\|///
 ~~~{cara}~~~
   \ | /
    |||
   /___\
""",
        ADULTO_GRANDE: r"""
 \\\\|////
~~~~~~~~~~~
 ~~~{cara}~~~
   \\ | //
     |||
    /___\
""",
    },
    excepciones={
        (NINO, MAL): r"""
   ._|_.
    \|/
  ( x_x )
    |||
   \___/
""",
        (ADULTO_GRANDE, MAL): r"""
 .,.,|.,.,
.,.,.,.,.,.
 .,.x_x.,.
   \\ | //
     |||
    /___\
""",
    },
))

_registrar(Especie(
    clave="michi", nombre="Michi", emoji="🐱", color=AMARILLO,
    fuerza=7, velocidad=12, salud=5, rareza=COMUN, peso=12.0,
    descripcion="Rápido y elegante. Te obedece cuando quiere.",
    evolucion="Pantera de Salón",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "T_T"},
    arte={
        BEBE: r"""
 /\_/\
 ({cara})
 > ^ <
""",
        NINO: r"""
  /\_/\
 ( {cara} )
 (  u  )
  ^^ ^^
""",
        ADOLESCENTE: r"""
  /\_/\
 ( {cara} )
 (  u  )~
  |   |
  ^^ ^^
""",
        ADULTO: r"""
   /\_/\
  ( {cara} )
 (   u   )~~
  |     |
  ^^   ^^
""",
        ADULTO_GRANDE: r"""
   /\___/\
  (  {cara}  )
 (    u    )~~~
 |         |
 ^^^     ^^^
""",
    },
))

_registrar(Especie(
    clave="slime", nombre="Slime", emoji="🟢", color=CIAN,
    fuerza=7, velocidad=6, salud=11, rareza=COMUN, peso=12.0,
    descripcion="Blando, resistente y sorprendentemente alegre.",
    evolucion="Slime Rey",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
  ___
 ({cara})
 ~~~~~
""",
        NINO: r"""
   ___
  /{cara}\
 (_____)
  ~~~~~
""",
        ADOLESCENTE: r"""
    ___
   /{cara}\
  (  v  )
 (_______)
  ~~~~~~~
""",
        ADULTO: r"""
    _____
    /{cara}\
  (   v   )
 (_________)
  ~~~~~~~~~
""",
        ADULTO_GRANDE: r"""
    \\|//
    _____
    /{cara}\
  (   v   )
 (_________)
 ~~~~~~~~~~~
""",
    },
))

_registrar(Especie(
    clave="pedrusco", nombre="Pedrusco", emoji="🪨", color=BLANCO,
    fuerza=13, velocidad=2, salud=9, rareza=COMUN, peso=12.0,
    descripcion="Inamovible en el sumo. Inamovible en general, la verdad.",
    evolucion="Golem de Cantera",
    caras={FELIZ: "^ ^", NORMAL: "o o", MAL: "x x"},
    arte={
        BEBE: r"""
 ,-----.
 ( {cara} )
 `-----'
""",
        NINO: r"""
  ,-------.
  |  {cara}  |
  '-------'
""",
        ADOLESCENTE: r"""
   _______
  /       \
 |   {cara}   |
 '---------'
""",
        ADULTO: r"""
    _________
   /         \
  |    {cara}    |
  |     u     |
  '-----------'
""",
        ADULTO_GRANDE: r"""
     _________
    /         \
   |    {cara}    |
   |     u     |
   |___________|
    |_|     |_|
""",
    },
))

_registrar(Especie(
    clave="pulpo", nombre="Pulpo", emoji="🐙", color=ROSA,
    fuerza=8, velocidad=8, salud=8, rareza=COMUN, peso=12.0,
    descripcion="Ni el más fuerte ni el más rápido, pero nunca el peor.",
    evolucion="Kraken de Bolsillo",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
  .-.
 ({cara})
 \|||/
""",
        NINO: r"""
   ___
  /{cara}\
  \___/
  /| |\
  ' ' '
""",
        ADOLESCENTE: r"""
   _____
  / {cara} \
  \_____/
  /|\ /|\
  ' ' ' '
""",
        ADULTO: r"""
   _______
  /  {cara}  \
 |    u    |
  \_______/
  /|\ | /|\
  ' ' ' ' '
""",
        ADULTO_GRANDE: r"""
    _________
   /   {cara}   \
  |     u     |
   \_________/
  //|\  |  /|\\
  ' ' ' ' ' ' '
""",
    },
))

_registrar(Especie(
    clave="chispa", nombre="Chispa", emoji="🔥", color=ROJO, articulo="una",
    fuerza=13, velocidad=8, salud=3, rareza=COMUN, peso=12.0,
    descripcion="Pega fortísimo y se apaga igual de rápido. Dale de comer.",
    evolucion="Fénix de Ceniza",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
   (
  (^)
 ({cara})
  \_/
""",
        NINO: r"""
     )
    ( (
   ){cara}(
  ( \_/ )
   `---'
""",
        ADOLESCENTE: r"""
    ) (
   ( ) )
  ) {cara} (
 (  \_/  )
  `-----'
""",
        ADULTO: r"""
   ) ( ) (
  ( ) ( ) )
 )   {cara}   (
(   \___/   )
 `---------'
""",
        ADULTO_GRANDE: r"""
  )( )( )( )
 ( )( )( )( )
\  )  {cara}  (  /
 \(  \___/  )/
  `---------'
""",
    },
    excepciones={
        (ADOLESCENTE, MAL): r"""
     .
    ( )
  . x_x .
 (  ~~~  )
  `-----'
""",
        (ADULTO_GRANDE, MAL): r"""
    .  .  .
   .  ( )  .
\  .  x_x  .  /
 \(  ~~~~~  )/
  `---------'
""",
    },
))

_registrar(Especie(
    clave="fantasma", nombre="Fantasma", emoji="👻", color=ROSA,
    fuerza=4, velocidad=13, salud=7, rareza=POCO_COMUN, peso=6.0,
    descripcion="Ya estaba muerto antes de nacer. No preguntes.",
    evolucion="Espectro Mayor",
    caras={FELIZ: "^ ^", NORMAL: "o o", MAL: "x x"},
    arte={
        BEBE: r"""
 .---.
 |{cara}|
  ~~~
""",
        NINO: r"""
  .---.
 / {cara} \
 |     |
  ~~~~~
""",
        ADOLESCENTE: r"""
   .-----.
  /  {cara}  \
  |   v   |
  |       |
   ~~~~~~~
""",
        ADULTO: r"""
    .-------.
   /   {cara}   \
   |    v    |
   |         |
    ~~~~~~~~~
""",
        ADULTO_GRANDE: r"""
   .-----------.
  /             \
 |      {cara}      |
 |       v       |
  \             /
   ~~~~~~~~~~~~~
""",
    },
))

_registrar(Especie(
    clave="chatarra", nombre="Chatarra", emoji="🤖", color=CIAN, articulo="una",
    fuerza=7, velocidad=4, salud=13, rareza=POCO_COMUN, peso=6.0,
    descripcion="No se cansa, no se queja, no se muere. Casi.",
    evolucion="Titán de Desguace",
    caras={FELIZ: "^ ^", NORMAL: "o o", MAL: "x x"},
    arte={
        BEBE: r"""
  [{cara}]
   |_|
""",
        NINO: r"""
    |
  .---.
  |{cara}|
  '---'
  /| |\
""",
        ADOLESCENTE: r"""
     |
  .-----.
  | {cara} |
  | --- |
  '-----'
  /|   |\
""",
        ADULTO: r"""
    |   |
  .-------.
  |  {cara}  |
  | ----- |
  '-------'
  /|     |\
""",
        ADULTO_GRANDE: r"""
  \|/   \|/
 .---------.
 |   {cara}   |
 | ------- |
 '---------'
 /| || || |\
""",
    },
))

_registrar(Especie(
    clave="dragoncito", nombre="Dragoncito", emoji="🐉", color=ROJO,
    fuerza=12, velocidad=9, salud=9, rareza=RARA, peso=4.0,
    descripcion="Sale una vez de cada veinticinco huevos. Cuídalo bien.",
    evolucion="Dragón Ancestral",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 /\_/\
({cara})>
 \___/
""",
        NINO: r"""
  /\_/\
 ( {cara} )>
  \___/
   ^ ^
""",
        ADOLESCENTE: r"""
 \       /
  \/\_/\/
  ( {cara} )>
   |   |
   ^   ^
""",
        ADULTO: r"""
  \\     //
  \\/\_/\//
  ( {cara} )>>
  /|     |\
  ^ ^   ^ ^
""",
        ADULTO_GRANDE: r"""
 \\\\  /\  ////
 \\\\/\_/\////
   (  {cara}  )>>>
  //|      |\\
  ^^ ^    ^ ^^
""",
    },
))


# --------------------------------------------------------------------------
# Selección al nacer
# --------------------------------------------------------------------------

def elegir_especie(rng: random.Random | None = None) -> Especie:
    """Elige una especie al azar respetando los pesos de rareza."""
    rng = rng or random.Random()
    claves = list(ESPECIES)
    pesos = [ESPECIES[c].peso for c in claves]
    return ESPECIES[rng.choices(claves, weights=pesos, k=1)[0]]


def tirar_2d6(rng: random.Random) -> int:
    return rng.randint(1, 6) + rng.randint(1, 6)


def tirar_stats_iniciales(
    especie: Especie, rng: random.Random | None = None
) -> tuple[int, int, int]:
    """Stats al nacer: base de la especie + 2d6 tirado por separado en cada una.

    El 2d6 es una campana (media 7, casi siempre 6-8), así que dos criaturas de
    la misma especie se diferencian en ±2-3 puntos: abrir el huevo emociona sin
    romper el equilibrio entre especies.
    """
    rng = rng or random.Random()
    return (
        especie.fuerza + tirar_2d6(rng),
        especie.velocidad + tirar_2d6(rng),
        especie.salud + tirar_2d6(rng),
    )


def arte_de(especie: Especie, etapa: str, animo: str = NORMAL) -> str:
    """El dibujo de una criatura en una etapa y un ánimo concretos."""
    especial = especie.excepciones.get((etapa, animo))
    if especial is not None:
        return especial
    return especie.arte[etapa].replace("{cara}", especie.caras[animo])


def tirar_genero(rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    return rng.choice(GENEROS)


# Marca de concordancia: «{masculino/femenino}».
MARCA_GENERO = re.compile(r"\{([^{}/]*)/([^{}/]*)\}")


def concordar(texto: str, genero: str) -> str:
    """Resuelve las marcas «{o/a}» del texto según el género.

    Una sola mecánica para toda la concordancia, porque en castellano casi todo
    lo que una criatura dice de sí misma la lleva: «bien comid{o/a}»,
    «{Contento/Contenta}», «{gruñón/gruñona}». Escrito así el fuente se sigue
    leyendo, y vale igual para lo regular y para lo irregular.

    Un test comprueba que no queda ninguna marca sin resolver en ningún prompt:
    es el fallo que se colaría sin avisar.
    """
    indice = 1 if genero == MACHO else 2
    return MARCA_GENERO.sub(lambda m: m.group(indice), texto)


def nombre_etapa(etapa: str, genero: str = MACHO) -> str:
    return concordar(NOMBRES_ETAPA[etapa], genero)
