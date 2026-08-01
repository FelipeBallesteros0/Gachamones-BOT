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
# Las especies
#
# Comunes y poco comunes reparten 24 puntos entre las tres estadísticas:
# ninguna es mejor, sólo distinta. Las raras llevan 30 y por eso salen poco.
#
# Los pesos se reparten por rareza y suman 100 entre todas:
#   17 comunes × 4,5  +  5 poco comunes × 3,5  +  3 raras × 2,0  =  100
# Al triplicar el catálogo, encontrar una rara CONCRETA bajó del 4 % al 2 %,
# pero las tres juntas siguen saliendo el 6 % de las veces.
# --------------------------------------------------------------------------

_registrar(Especie(
    clave="pollito", nombre="Piollito", emoji="🐥", color=AMARILLO,
    fuerza=4, velocidad=14, salud=6, rareza=COMUN, peso=4.5,
    descripcion="Corre como si le persiguieran. Porque suele ser el caso.",
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
    clave="brote", articulo="una", nombre="Magora", emoji="🌱", color=VERDE,
    fuerza=7, velocidad=3, salud=14, rareza=COMUN, peso=4.5,
    descripcion="Aguanta lo que le echen. Moverse ya es otro tema.",
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
    clave="michi", nombre="Purreon", emoji="🐱", color=AMARILLO,
    fuerza=7, velocidad=12, salud=5, rareza=COMUN, peso=4.5,
    descripcion="Rápido y elegante. Te obedece cuando quiere.",
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
    clave="slime", nombre="Gelatín", emoji="🟢", color=CIAN,
    fuerza=7, velocidad=6, salud=11, rareza=COMUN, peso=4.5,
    descripcion="Blando, resistente y sorprendentemente alegre.",
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
    clave="pedrusco", nombre="Geo", emoji="🪨", color=BLANCO,
    fuerza=13, velocidad=2, salud=9, rareza=COMUN, peso=4.5,
    descripcion="Inamovible en el sumo. Inamovible en general, la verdad.",
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
    clave="pulpo", nombre="Octopul", emoji="🐙", color=ROSA,
    fuerza=8, velocidad=8, salud=8, rareza=COMUN, peso=4.5,
    descripcion="Ni el más fuerte ni el más rápido, pero nunca el peor.",
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
    clave="chispa", nombre="Pyro", emoji="🔥", color=ROJO, articulo="un",
    fuerza=13, velocidad=8, salud=3, rareza=COMUN, peso=4.5,
    descripcion="Pega fortísimo y se apaga igual de rápido. Dale de comer.",
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
    clave="fantasma", nombre="Duskhause", emoji="👻", color=ROSA,
    fuerza=4, velocidad=13, salud=7, rareza=POCO_COMUN, peso=3.5,
    descripcion="Ya estaba muerto antes de nacer. No preguntes.",
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
    clave="chatarra", nombre="Re-bot", emoji="🤖", color=CIAN, articulo="un",
    fuerza=7, velocidad=4, salud=13, rareza=POCO_COMUN, peso=3.5,
    descripcion="No se cansa, no se queja, no se muere. Casi.",
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
    clave="dragoncito", nombre="Tsushimon", emoji="🐉", color=ROJO,
    fuerza=12, velocidad=9, salud=9, rareza=RARA, peso=2.0,
    descripcion="Sale una vez de cada cincuenta huevos. Cuídalo bien.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
  ^^^
 ({cara})~
  \_/
""",
        NINO: r"""
   ^^^^
  ({cara})~~
   |   |
   ^   ^
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

# --------------------------------------------------------------------------
# Las quince nuevas
#
# Mismo reparto que las de arriba: 24 puntos las comunes y poco comunes, 30 las
# raras. Los pesos se recalcularon para las veinticinco a la vez, así que aquí
# no hay ningún número suelto: sale de la rareza.
# --------------------------------------------------------------------------

_registrar(Especie(
    clave="swampdon", nombre="Swampdón", emoji="🐸", color=VERDE,
    fuerza=9, velocidad=4, salud=11, rareza=COMUN, peso=4.5,
    descripcion="Un pegote de barro con ojos. Se hunde a propósito.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
  ___
 ({cara})
  ---
""",
        NINO: r"""
   ___
  ({cara})
  (   )
   ---
""",
        ADOLESCENTE: r"""
    ___
   ({cara})
  (     )
   -----
""",
        ADULTO: r"""
    _____
    ({cara})
  (       )
 (         )
   -------
""",
        ADULTO_GRANDE: r"""
   _______
    ({cara})
  (       )
 (         )
(           )
  ---------
""",
    },
))

_registrar(Especie(
    clave="canizo", nombre="Cañizo", emoji="🎋", color=VERDE,
    fuerza=5, velocidad=10, salud=9, rareza=COMUN, peso=4.5,
    descripcion="Tan flaco que el viento lo dobla y no lo parte.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "-_-"},
    arte={
        BEBE: r"""
   |
 ({cara})
   |
""",
        NINO: r"""
   \|/
  ({cara})
    |
    |
""",
        ADOLESCENTE: r"""
  \\|//
  ({cara})
   |||
   |||
""",
        ADULTO: r"""
  \\\|///
   ({cara})
   |||||
   |||||
   |||||
""",
        ADULTO_GRANDE: r"""
 \\\\|////
   ({cara})
  |||||||
  |||||||
  |||||||
  |||||||
""",
    },
))

_registrar(Especie(
    clave="lucierno", nombre="Lucierno", emoji="✨", color=AMARILLO,
    fuerza=3, velocidad=13, salud=8, rareza=POCO_COMUN, peso=3.5,
    descripcion="Se enciende cuando está contento. Delata al equipo entero.",
    caras={FELIZ: "^o^", NORMAL: "o.o", MAL: "u.u"},
    arte={
        BEBE: r"""
   .
 ({cara})
   '
""",
        NINO: r"""
  .'.
 ({cara})
  '.'
""",
        ADOLESCENTE: r"""
 .'.'.
 ({cara})
 '.'.'
""",
        ADULTO: r"""
 .'.'.'.
  ({cara})
 '.'.'.'
""",
        ADULTO_GRANDE: r"""
.'.'.'.'.
 .'.'.'.
  ({cara})
 '.'.'.'
'.'.'.'.'
""",
    },
))

_registrar(Especie(
    clave="coralito", nombre="Coralito", emoji="🪸", color=ROSA,
    fuerza=7, velocidad=6, salud=11, rareza=COMUN, peso=4.5,
    descripcion="Duro por fuera y quisquilloso por dentro. No lo toques.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
  Y
({cara})
  A
""",
        NINO: r"""
 YvY
({cara})
 AAA
""",
        ADOLESCENTE: r"""
 YvYvY
 ({cara})
 AAAAA
""",
        ADULTO: r"""
 YvYvYvY
  ({cara})
  AAAAA
 AAAAAAA
""",
        ADULTO_GRANDE: r"""
YvYvYvYvY
 YvYvYvY
  ({cara})
  AAAAA
 AAAAAAA
AAAAAAAAA
""",
    },
))

_registrar(Especie(
    clave="escorpgon", nombre="Escorpgon", emoji="🦂", color=ROJO,
    fuerza=12, velocidad=8, salud=4, rareza=COMUN, peso=4.5,
    descripcion="Toda la fuerza está en la cola. El resto es decorado.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 ({cara})j
 /   \
""",
        NINO: r"""
  ({cara})jj
  /   \
 //   \\
""",
        ADOLESCENTE: r"""
   ({cara})jjj
   /   \
  //   \\
 ///   \\\
""",
        ADULTO: r"""
 v ({cara})jjjj
   /   \
  //   \\
 ///   \\\
////   \\\\
""",
        ADULTO_GRANDE: r"""
 vv ({cara})jjjjj
    /   \
   //   \\
  ///   \\\
 ////   \\\\
/////   \\\\\
""",
    },
))

_registrar(Especie(
    clave="nacar", nombre="Nacar", emoji="🐚", color=ROSA,
    fuerza=5, velocidad=7, salud=12, rareza=COMUN, peso=4.5,
    descripcion="Se mete en su concha al primer susto. Aguanta ahí semanas.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 (({cara}))
""",
        NINO: r"""
  ((({cara})))
""",
        ADOLESCENTE: r"""
   (((({cara}))))
    \      /
""",
        ADULTO: r"""
  ((((({cara})))))
    \\      //
     \\    //
""",
        ADULTO_GRANDE: r"""
  (((((({cara}))))))
    \\\      ///
     \\\    ///
      \\\  ///
""",
    },
))

_registrar(Especie(
    clave="remolin", nombre="Remolín", emoji="🌀", color=CIAN,
    fuerza=6, velocidad=14, salud=4, rareza=POCO_COMUN, peso=3.5,
    descripcion="Nunca está donde lo dejaste. Marea sólo de mirarlo.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "@_@"},
    arte={
        BEBE: r"""
 ({cara})
  ~~~
""",
        NINO: r"""
 ({cara})
 ~~~~~
  ~~~
""",
        ADOLESCENTE: r"""
  ({cara})
 ~~~~~~~
  ~~~~~
   ~~~
""",
        ADULTO: r"""
   ({cara})
 ~~~~~~~~~
  ~~~~~~~
   ~~~~~
    ~~~
""",
        ADULTO_GRANDE: r"""
    ({cara})
 ~~~~~~~~~~~
  ~~~~~~~~~
   ~~~~~~~
    ~~~~~
     ~~~
""",
    },
))

_registrar(Especie(
    clave="prinel", nombre="Prinel", emoji="🔩", color=GRIS,
    fuerza=11, velocidad=5, salud=8, rareza=COMUN, peso=4.5,
    descripcion="Cabezón y roscado. Cuesta lo mismo apretarlo que convencerlo.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 [{cara}]
  ===
""",
        NINO: r"""
 [{cara}]
 =====
 =====
""",
        ADOLESCENTE: r"""
  [{cara}]
 =======
 =======
 =======
""",
        ADULTO: r"""
   [{cara}]
 =========
 =========
 =========
 =========
""",
        ADULTO_GRANDE: r"""
    [{cara}]
 ===========
 ===========
 ===========
 ===========
 ===========
""",
    },
))

_registrar(Especie(
    clave="bulb", nombre="Bulb", emoji="💡", color=AMARILLO,
    fuerza=4, velocidad=9, salud=11, rareza=COMUN, peso=4.5,
    descripcion="Parpadea cuando piensa. Piensa poco, así que alumbra bien.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 ({cara})
  |=|
""",
        NINO: r"""
  ({cara})
  (   )
   |=|
""",
        ADOLESCENTE: r"""
  -({cara})-
   (   )
    |=|
    |=|
""",
        ADULTO: r"""
   \     /
   -({cara})-
   (     )
     |=|
     |=|
""",
        ADULTO_GRANDE: r"""
  \   |   /
   -({cara})-
   (     )
  /  |=|  \
     |=|
     |=|
""",
    },
))

_registrar(Especie(
    clave="magnetron", nombre="Magnetrón", emoji="🧲", color=ROJO,
    fuerza=13, velocidad=4, salud=7, rareza=COMUN, peso=4.5,
    descripcion="Se le pega todo. A veces lo que no debería.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 ({cara})
 U   U
""",
        NINO: r"""
  ({cara})
  |   |
  U   U
""",
        ADOLESCENTE: r"""
  ({cara})
  |   |
  |   |
  U   U
""",
        ADULTO: r"""
   ({cara})
  /|   |\
   |   |
   |   |
   U   U
""",
        ADULTO_GRANDE: r"""
 -  ({cara})  -
   /|   |\
    |   |
    |   |
    |   |
    U   U
""",
    },
))

_registrar(Especie(
    clave="criold", nombre="Criold", emoji="❄️", color=CIAN,
    fuerza=6, velocidad=11, salud=7, rareza=COMUN, peso=4.5,
    descripcion="Cae despacio y siempre de pie. No se derrite: se ofende.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 *({cara})*
""",
        NINO: r"""
    *
 *({cara})*
    *
""",
        ADOLESCENTE: r"""
   \*/
 *({cara})*
   /*\
""",
        ADULTO: r"""
   \ * /
 --({cara})--
   / * \
""",
        ADULTO_GRANDE: r"""
    \ * /
   * \|/ *
 ---({cara})---
   * /|\ *
    / * \
""",
    },
))

_registrar(Especie(
    clave="goot", nombre="Goot", emoji="🐐", color=BLANCO,
    fuerza=12, velocidad=7, salud=5, rareza=COMUN, peso=4.5,
    descripcion="Sube por donde no hay camino. Baja igual de mal.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 ({cara})
  n n
""",
        NINO: r"""
 (({cara}))
  /   \
  n   n
""",
        ADOLESCENTE: r"""
 \({cara})/
  /   \
  n   n
""",
        ADULTO: r"""
 \\({cara})//
   /   \
  //   \\
  n     n
""",
        ADULTO_GRANDE: r"""
 \\\({cara})///
    /   \
   //   \\
  ///   \\\
  n       n
""",
    },
))

_registrar(Especie(
    clave="cefiro", nombre="Céfiro", emoji="🦅", color=AMARILLO,
    fuerza=9, velocidad=14, salud=7, rareza=RARA, peso=2.0,
    descripcion="Vive donde no llega nadie. Baja sólo si le conviene.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 ({cara})
  v v
""",
        NINO: r"""
 <({cara})>
   v v
""",
        ADOLESCENTE: r"""
 <<({cara})>>
    v v
    ' '
""",
        ADULTO: r"""
 <<<({cara})>>>
     v v
     ' '
    /   \
""",
        ADULTO_GRANDE: r"""
   \\   //
 <<<({cara})>>>
     v v
     ' '
    /   \
   //   \\
""",
    },
))

_registrar(Especie(
    clave="noctule", nombre="Noctule", emoji="🦇", color=ROSA,
    fuerza=6, velocidad=13, salud=5, rareza=POCO_COMUN, peso=3.5,
    descripcion="Duerme de día y se queja de noche. Ve mejor que tú.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "u.u"},
    arte={
        BEBE: r"""
 v({cara})v
""",
        NINO: r"""
  v v
 v({cara})v
""",
        ADOLESCENTE: r"""
 vv   vv
 v({cara})v
   / \
""",
        ADULTO: r"""
 vvv   vvv
  v({cara})v
    / \
    ' '
""",
        ADULTO_GRANDE: r"""
 vvvv   vvvv
  vvv   vvv
   v({cara})v
     / \
     ' '
""",
    },
))

_registrar(Especie(
    clave="prismlon", nombre="Prismlon", emoji="💎", color=AZUL,
    fuerza=12, velocidad=5, salud=13, rareza=RARA, peso=2.0,
    descripcion="Tardó mil años en formarse. Tiene la paciencia que eso implica.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 /{cara}\
 \___/
""",
        NINO: r"""
  /{cara}\
 /     \
 \_____/
""",
        ADOLESCENTE: r"""
   /\
  /{cara}\
 /     \
 \_____/
""",
        ADULTO: r"""
   /\
  /  \
 /{cara}\
/       \
\_______/
""",
        ADULTO_GRANDE: r"""
    /   \
   /     \
  /       \
  /  {cara}  \
 /         \
 \_________/
""",
    },
))
