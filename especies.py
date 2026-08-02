"""Las 25 especies: arte ASCII por etapa, estadísticas base y rarezas.

Módulo puro: no importa discord ni toca la base de datos, así que se puede
testear entero sin conexión.

Cómo se guarda el arte
----------------------
Cinco etapas por veinticinco especies, y cada una con tres estados de ánimo,
serían 375 dibujos. Insostenible.

Pero mirando los dibujos, casi todos se diferencian **sólo en la cara**: el
mismo cuerpo de Piollito con `^v^`, `o.o` o `T_T`. Así que cada etapa se guarda
como una plantilla con un hueco `{cara}`, y cada especie declara sus tres
caras. Resultado: **125 dibujos y los ánimos salen gratis**.

Donde el ánimo cambia más que la cara —a Magora se le caen las hojas, la llama
de Pyro mengua— se declara el dibujo completo en `excepciones`, que gana a la
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

# Lo que pesa cada rareza al cruzarte con un salvaje en `/aventura`.
#
# Es el MISMO reparto que usa el huevo (12/6/4), a propósito: así «raro»
# significa lo mismo en los dos sitios y no hay un segundo juego de números que
# mantener al lado del primero.
#
# **No puede salir de `Especie.peso`**, que es la probabilidad en el huevo y
# vale 0 en las quince que no salen de él: leerlo aquí las dejaría sin aparecer
# nunca en ningún sitio. Sale de la rareza, que está declarada en cada especie.
#
# Sólo muerde donde el bioma mezcla rarezas. En las Ruinas las tres son «poco
# común» y allí reparte igual que antes; hay un test que lo deja escrito para
# que nadie lo lea como un fallo.
PESO_EN_EL_CAMPO = {COMUN: 12, POCO_COMUN: 6, RARA: 4}

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
    # «una Magora macho» es lo correcto, igual que «una jirafa macho». Son dos
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
# **El peso es la probabilidad en el huevo, y sólo eso.** `aventura.tirar_salvaje`
# elige uniforme dentro del bioma y no lo mira, así que las especies que no
# salen del huevo llevan peso 0 en vez de arrastrar un número que no significa
# nada. Las diez que sí salen suman 100 entre ellas y cada peso se lee como un
# porcentaje.
# --------------------------------------------------------------------------

_registrar(Especie(
    clave="pollito", nombre="Piollito", emoji="🐥", color=AMARILLO,
    fuerza=4, velocidad=14, salud=6, rareza=COMUN, peso=12.0,
    descripcion="Corre como si le persiguieran. Porque suele ser el caso.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "T_T"},
    arte={
        BEBE: r"""
  ｰ
 .-.
({cara})
 '-'
 ﾞ ﾞ
""",
        NINO: r"""
  ｰﾉ
 .-~-.
<({cara})>
 '-.-'
 ﾞ  ﾞ
""",
        ADOLESCENTE: r"""
    ｼｰﾉ
   .-~-.
   ({cara})
<(|  ▿  |)>
   '-.-'
   ﾞﾞ ﾞﾞ
""",
        ADULTO: r"""
     ｼｰﾉ
   .-~~~-.
  / ({cara}) \
<(|   ▿   |)>
   \  ,  /
   ﾞﾞ   ﾞﾞ
""",
        ADULTO_GRANDE: r"""
      ｼｰﾉ｡
    .-~~~~~-.
   /  ({cara})  \
<(|     ▿     |)>
   \   ,,,   /
    ﾞﾞ     ﾞﾞ
""",
    },
))

_registrar(Especie(
    clave="brote", articulo="una", nombre="Magora", emoji="🌱", color=VERDE,
    fuerza=7, velocidad=3, salud=14, rareza=COMUN, peso=12.0,
    descripcion="Aguanta lo que le echen. Moverse ya es otro tema.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 \|/
({cara})
  |
 ===
""",
        NINO: r"""
\\|//
({cara})
  |
=====
""",
        ADOLESCENTE: r"""
\\\|///
~~~~~~~
 ({cara})
 \ | /
=======
""",
        ADULTO: r"""
\\\\|////
~~~~~~~~~
~~({cara})~~
 \\ | //
   |||
=========
""",
        ADULTO_GRANDE: r"""
 \\\\\|/////
~~~~~~~~~~~~~
~~~~({cara})~~~~
  \\\ | ///
    |||||
 ===░░░░░===
""",
    },
    # La cara va escrita y no como hueco: `arte_de` devuelve la excepción tal
    # cual, y hay un test que prohíbe dejar un «{cara}» sin rellenar.
    excepciones={
        (NINO, MAL): r"""
., .,
(T_T)
  |
=====
""",
        (ADULTO_GRANDE, MAL): r"""
., . | . .,
 .,.,.,.,
., (T_T) .,
  \\ | //
   |||||
===░░░░░===
""",
    },
))

_registrar(Especie(
    clave="michi", nombre="Purreon", emoji="🐱", color=AMARILLO,
    fuerza=7, velocidad=12, salud=5, rareza=COMUN, peso=12.0,
    descripcion="Rápido y elegante. Te obedece cuando quiere.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "T_T"},
    arte={
        BEBE: r"""
/\_/\
({cara})
'^ ^'
""",
        NINO: r"""
/\_/\
({cara})
( w )
'^ ^'
""",
        ADOLESCENTE: r"""
 /\___/\
 / {cara} \
=(  w  )=
|  ,,  |~
 ^^   ^^
""",
        ADULTO: r"""
  /\____/\
  /  {cara}  \
=(    w    )=
|   ,,,   |~~
  \       /
  ^^^   ^^^
""",
        ADULTO_GRANDE: r"""
   /\_____/\
  /  ({cara})  \
=(     w     )=
|    ,,,    |~~~
  \         /
  ^^^     ^^^
""",
    },
))

_registrar(Especie(
    clave="slime", nombre="Gelatín", emoji="🟢", color=CIAN,
    fuerza=7, velocidad=6, salud=11, rareza=COMUN, peso=12.0,
    descripcion="Blando, resistente y sorprendentemente alegre.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
  '
({cara})
~~~~~
""",
        NINO: r"""
  ' '
 ({cara})
 ( w )
~~~~~~~
""",
        ADOLESCENTE: r"""
  '  '
 ,-~~-.
 ( {cara} )
 (  w  )
~~~~~~~~~
""",
        ADULTO: r"""
   '   '
 ,-~~~~-.
 (  {cara}  )
 (   w   )
 (       )
~~~~~~~~~~~
""",
        ADULTO_GRANDE: r"""
   '   '   '
  ,-~~~~~~~-.
 (   ({cara})   )
(      w      )
(             )
~~~~~~~~~~~~~~~
""",
    },
))

_registrar(Especie(
    clave="pedrusco", nombre="Geo", emoji="🪨", color=BLANCO,
    fuerza=13, velocidad=2, salud=9, rareza=COMUN, peso=12.0,
    descripcion="Inamovible en el sumo. Inamovible en general, la verdad.",
    caras={FELIZ: "^ ^", NORMAL: "o o", MAL: "x x"},
    arte={
        BEBE: r"""
,---.
({cara})
`---'
""",
        NINO: r"""
,-----.
( {cara} )
`-----'
""",
        ADOLESCENTE: r"""
,-------.
(  {cara}  )
|  ░░░  |
`-------'
""",
        ADULTO: r"""
,---------.
/   {cara}   \
|    w    |
|  ░░░░░  |
`---------'
""",
        ADULTO_GRANDE: r"""
 _,-----------,_
/      {cara}      \
|       w       |
|   ░░░░░░░░░   |
`---------------'
 |__|       |__|
""",
    },
))

_registrar(Especie(
    clave="pulpo", nombre="Octopul", emoji="🐙", color=ROSA,
    fuerza=8, velocidad=8, salud=8, rareza=COMUN, peso=12.0,
    descripcion="Ni el más fuerte ni el más rápido, pero nunca el peor.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 .-.
({cara})
\|||/
""",
        NINO: r"""
 ,-~-.
( {cara} )
\|/ \|/
 '  '
""",
        ADOLESCENTE: r"""
,-~~~-.
( {cara} )
`--w--'
\|/ \|/
'  '  '
""",
        ADULTO: r"""
 ,-~~~~~~-.
 /   {cara}   \
|     w     |
`-----------'
 \|/ \|/ \|/
 '  '  '  '
""",
        ADULTO_GRANDE: r"""
   ,-~~~~~~~~~-.
  /     {cara}     \
 |       w       |
 `---------------'
//|\ \|/ |/ \|/ /|\\
' '  ' ' '  ' '  ' '
""",
    },
))

_registrar(Especie(
    clave="chispa", nombre="Pyro", emoji="🔥", color=ROJO, articulo="un",
    fuerza=13, velocidad=8, salud=3, rareza=COMUN, peso=12.0,
    descripcion="Pega fortísimo y se apaga igual de rápido. Dale de comer.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
  (
 )(
({cara})
 \_/
""",
        NINO: r"""
 )(
( )(
({cara})
\_w_/
""",
        ADOLESCENTE: r"""
 )( )(
( )( )(
( {cara} )
 \_w_/
 `---'
""",
        ADULTO: r"""
 )( )( )(
( )( )( )(
\ ({cara}) /
\ \_w_/ /
`-------'
""",
        ADULTO_GRANDE: r"""
    )( )( )(
   )( )( )( )(
  ( )( )( )( )(
\  )  ({cara})  (  /
 \(   \_w_/   )/
  `-----------'
""",
    },
    # La cara va escrita y no como hueco: `arte_de` devuelve la excepción tal
    # cual, y hay un test que prohíbe dejar un «{cara}» sin rellenar.
    excepciones={
        (ADOLESCENTE, MAL): r"""
 '  '
 . . .
( T_T )
\_~~_/
 `---'
""",
        (ADULTO_GRANDE, MAL): r"""
      '   '
   .  .  .  .
\  .  (T_T)  .  /
\(   \_~~_/   )/
  `-----------'
""",
    },
))

_registrar(Especie(
    clave="fantasma", nombre="Duskhouse", emoji="👻", color=ROSA,
    fuerza=4, velocidad=13, salud=7, rareza=POCO_COMUN, peso=6.0,
    descripcion="Ya estaba muerto antes de nacer. No preguntes.",
    caras={FELIZ: "^ ^", NORMAL: "o o", MAL: "x x"},
    arte={
        BEBE: r"""
.---.
|{cara}|
 ~~~
""",
        NINO: r"""
.-----.
| {cara} |
\     /
 ~~~~~
""",
        ADOLESCENTE: r"""
' .-----. '
 |  {cara}  |
 |   w   |
 \       /
  ~~~~~~~
""",
        ADULTO: r"""
'  .-------.  '
 /    {cara}    \
 |     w     |
 \           /
  ~~~~~~~~~~~
""",
        ADULTO_GRANDE: r"""
'   .-----------.   '
 /       {cara}       \
 |        w        |
 |                 |
  \               /
   ~~~~~~~~~~~~~~~
""",
    },
))

_registrar(Especie(
    clave="chatarra", nombre="Re-bot", emoji="🤖", color=CIAN, articulo="un",
    fuerza=7, velocidad=4, salud=13, rareza=POCO_COMUN, peso=6.0,
    descripcion="No se cansa, no se queja, no se muere. Casi.",
    # El único que se dibuja con líneas de caja, y a propósito: en un elenco de
    # bichos redondos, ser el que cierra en ángulo recto es su identidad. El
    # marco tiene que cuadrar en las cinco etapas, no sólo en la última.
    caras={FELIZ: "^ ^", NORMAL: "o o", MAL: "x x"},
    arte={
        BEBE: r"""
  |
[{cara}]
 |_|
""",
        NINO: r"""
  \|/
╭─────╮
│ {cara} │
╰╷───╷╯
""",
        ADOLESCENTE: r"""
\|/   \|/
╭───────╮
│  {cara}  │
│ ░░░░░ │
╰╷─╷─╷─╷╯
""",
        ADULTO: r"""
\|/      \|/
╭───────────╮
│    {cara}    │
│  ░░░░░░░  │
╰─╷─╷───╷─╷─╯
 /| || || |\
""",
        ADULTO_GRANDE: r"""
 \|/         \|/
╭───────────────╮
│      {cara}      │
│  ░░░░░░░░░░░  │
╰──╷─╷─────╷─╷──╯
/|| || ||| || ||\
""",
    },
))

_registrar(Especie(
    clave="dragoncito", nombre="Tsushimon", emoji="🐉", color=ROJO,
    fuerza=12, velocidad=9, salud=9, rareza=RARA, peso=4.0,
    descripcion="Sale una vez de cada veinticinco huevos. Cuídalo bien.",
    # Dragón chino: serpentino y SIN ALAS. Astas de ciervo «⌐ ¬», bigotes «~»
    # saliendo del hocico, melena, escamas y garras. Lo de antes le ponía
    # membranas a los lados, que es un dragón occidental.
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 ⌐\/¬
({cara})
 ~~~
""",
        NINO: r"""
⌐\ /¬
({cara})
(~~~)
 ᐩ ᐩ
""",
        ADOLESCENTE: r"""
⌐\  /¬
-({cara})-
(~~~~~)
~(░░░)~
 ᐩ   ᐩ
""",
        ADULTO: r"""
  ⌐\   /¬
 --({cara})--
  ~)___(~
~(  ░░░  )~
~~(     )~~
 ᐩ   ᐩ   ᐩ
""",
        ADULTO_GRANDE: r"""
   ⌐\     /¬
 --( ({cara}) )--
   ~)_____(~
 ~~(  ░░░  )~~
~~~(       )~~~
  ᐩ    ᐩ    ᐩ
""",
    },
))


# --------------------------------------------------------------------------
# Selección al nacer
# --------------------------------------------------------------------------

# Las que puede dar el huevo de partida: las diez de siempre. Las demás sólo se
# consiguen reclutándolas en `/aventura`, para que el comienzo sea conocido y el
# catálogo grande sea lo que se descubre jugando.
DEL_HUEVO: tuple[str, ...] = tuple(
    clave for clave, especie in ESPECIES.items() if especie.peso > 0
)


def elegir_del_huevo(rng: random.Random | None = None) -> Especie:
    """Qué sale al romper el huevo, respetando los pesos de rareza.

    Se llama así y no `elegir_especie` porque no elige entre todas: las quince
    que no salen del huevo se quedan fuera por llevar peso 0.
    """
    rng = rng or random.Random()
    pesos = [ESPECIES[c].peso for c in DEL_HUEVO]
    return ESPECIES[rng.choices(list(DEL_HUEVO), weights=pesos, k=1)[0]]


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
    fuerza=9, velocidad=4, salud=11, rareza=COMUN, peso=0.0,
    descripcion="Un pegote de barro con ojos. Se hunde a propósito.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 ___
({cara})
 ~~~
""",
        NINO: r"""
 _____
( {cara} )
 ~~~~~
""",
        ADOLESCENTE: r"""
 _______
(  {cara}  )
(       )
 ~~~~~~~
""",
        ADULTO: r"""
 _________
(   {cara}   )
(         )
 \       /
  ~~~~~~~
""",
        ADULTO_GRANDE: r"""
  ___________
 (    {cara}    )
(     ,,,     )
(             )
 \           /
  ~~~~~~~~~~~
""",
    },
))

_registrar(Especie(
    clave="canizo", nombre="Cañizo", emoji="🎋", color=VERDE,
    fuerza=5, velocidad=10, salud=9, rareza=COMUN, peso=0.0,
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
 =|=
""",
        ADOLESCENTE: r"""
\\|//
({cara})
=|=|=
|| ||
""",
        ADULTO: r"""
\\\|///
 ({cara})
=|=|=|=
|| || ||
=|=|=|=
""",
        ADULTO_GRANDE: r"""
 \\\\|////
   ({cara})
 =|=|=|=|=
|| || || ||
 =|=|=|=|=
|| || || ||
""",
    },
))

_registrar(Especie(
    clave="lucierno", nombre="Lucierno", emoji="✨", color=AMARILLO,
    fuerza=3, velocidad=13, salud=8, rareza=POCO_COMUN, peso=0.0,
    descripcion="Se enciende cuando está contento. Delata al equipo entero.",
    caras={FELIZ: "^o^", NORMAL: "o.o", MAL: "u.u"},
    arte={
        BEBE: r"""
  '
({cara})
  '
""",
        NINO: r"""
 ' '
({cara})
 ' '
""",
        ADOLESCENTE: r"""
' . '
.'.'.
({cara})
'.'.'
""",
        ADULTO: r"""
' . ' . '
 .'.'.'.
  ({cara})
 '.'.'.'
' ' ' ' '
""",
        ADULTO_GRANDE: r"""
'  .  '  .  '
 .'.'.'.'.'.
 \.'.'.'.'./
   =({cara})=
 /'.'.'.'.'\
'  '  '  '  '
""",
    },
))

_registrar(Especie(
    clave="coralito", nombre="Coralito", emoji="🪸", color=ROSA,
    fuerza=7, velocidad=6, salud=11, rareza=COMUN, peso=0.0,
    descripcion="Duro por fuera y quisquilloso por dentro. No lo toques.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
  Y
({cara})
  A
""",
        NINO: r"""
 Y Y
({cara})
 AAA
""",
        ADOLESCENTE: r"""
Y Y Y
YvYvY
({cara})
AAAAA
""",
        ADULTO: r"""
 Y Y Y Y
 YvYvYvY
 ⌐({cara})¬
 AAAAAAA
AAAAAAAAA
""",
        ADULTO_GRANDE: r"""
  Y Y Y Y Y Y
  YvYvYvYvYvY
  ⌐(  {cara}  )¬
  AAAAAAAAAAA
 AAAAAAAAAAAAA
AAAAAAAAAAAAAAA
""",
    },
))

_registrar(Especie(
    clave="escorpgon", nombre="Escorpgon", emoji="🦂", color=ROJO,
    fuerza=12, velocidad=8, salud=4, rareza=COMUN, peso=0.0,
    descripcion="Toda la fuerza está en la cola. El resto es decorado.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
({cara})j
 '  '
""",
        NINO: r"""
 ,j
({cara})
'  '
""",
        ADOLESCENTE: r"""
  _,-,
  /  j
⊐-({cara})-⊏
//  ,  \\
'  ' '  '
""",
        ADULTO: r"""
    _,-,
    /   j
⊐---({cara})---⊏
 //  ,,,  \\
 /   | |   \
 '   ' '   '
""",
        ADULTO_GRANDE: r"""
      _,-,
     /    j
⊐----(({cara}))----⊏
 ///   ,,,   \\\
 //    |||    \\
 '     ' '     '
""",
    },
))

_registrar(Especie(
    clave="nacar", nombre="Nacar", emoji="🐚", color=ROSA,
    fuerza=5, velocidad=7, salud=12, rareza=COMUN, peso=0.0,
    descripcion="Se mete en su concha al primer susto. Aguanta ahí semanas.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
(({cara}))
""",
        NINO: r"""
((({cara})))
  \ | /
""",
        ADOLESCENTE: r"""
  _,-~-,_
(((({cara}))))
  \\ | //
""",
        ADULTO: r"""
 _,-~~~~-,_
((((({cara})))))
\(((( w ))))/
  \\\ | ///
""",
        ADULTO_GRANDE: r"""
 _,-~~~~~~~-,_
(((((({cara}))))))
\((((( w )))))/
 \\\\\ | /////
  \\\\ | ////
  '    '    '
""",
    },
))

_registrar(Especie(
    clave="remolin", nombre="Remolín", emoji="🌀", color=CIAN,
    fuerza=6, velocidad=14, salud=4, rareza=POCO_COMUN, peso=0.0,
    descripcion="Nunca está donde lo dejaste. Marea sólo de mirarlo.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "@_@"},
    arte={
        BEBE: r"""
({cara})
 ~~~
""",
        NINO: r"""
~ ~ ~
({cara})
~~~~~
""",
        ADOLESCENTE: r"""
~ ~ ~ ~
 ({cara})
~~~~~~~
 ~~~~~
""",
        ADULTO: r"""
~  ~  ~  ~
   ({cara})
~~~~~~~~~~~
 ~~~~~~~~~
  ~~~~~~~
""",
        ADULTO_GRANDE: r"""
~  ~  ~  ~  ~
   ~({cara})~
~~~~~~~~~~~~~
 ~~~~~~~~~~~
   ~~~~~~~
    ~~~~~
""",
    },
))

_registrar(Especie(
    clave="prinel", nombre="Prinel", emoji="🔩", color=GRIS,
    fuerza=11, velocidad=5, salud=8, rareza=COMUN, peso=0.0,
    descripcion="Cabezón y roscado. Cuesta lo mismo apretarlo que convencerlo.",
    # Cabeza hexagonal con ranura, que es lo que tiene un tornillo. Con la
    # cúpula redonda de antes le robaba la cabeza a Geo en tres etapas.
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
[{cara}]
 ===
""",
        NINO: r"""
_,-,_
({cara})
=====
""",
        ADOLESCENTE: r"""
 _,-,_
/ {cara} \
\_____/
 =====
 \_=_/
""",
        ADULTO: r"""
 __,-,__
/  {cara}  \
\_______/
 =======
  =====
 \__=__/
""",
        ADULTO_GRANDE: r"""
  _,-,-,-,_
/    {cara}    \
\___________/
=============
 ===========
\_____=_____/
""",
    },
))

_registrar(Especie(
    clave="bulb", nombre="Bulb", emoji="💡", color=AMARILLO,
    fuerza=4, velocidad=9, salud=11, rareza=COMUN, peso=0.0,
    descripcion="Parpadea cuando piensa. Piensa poco, así que alumbra bien.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
({cara})
 |=|
""",
        NINO: r"""
 \ /
({cara})
 |=|
""",
        ADOLESCENTE: r"""
\ | /
,-'-.
({cara})
|===|
""",
        ADULTO: r"""
 \  |  /
- ,-~~-. -
 ( {cara} )
  `-w-'
 |=====|
""",
        ADULTO_GRANDE: r"""
  \   |   /
-- ,-~~~~-. --
  (  {cara}  )
   `--w--'
  |=======|
  |=======|
""",
    },
))

_registrar(Especie(
    clave="magnetron", nombre="Magnetrón", emoji="🧲", color=ROJO,
    fuerza=13, velocidad=4, salud=7, rareza=COMUN, peso=0.0,
    descripcion="Se le pega todo. A veces lo que no debería.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
({cara})
 U U
""",
        NINO: r"""
.   .
({cara})
U   U
""",
        ADOLESCENTE: r"""
. ⌐({cara})¬ .
  /|   |\
   |   |
   U   U
""",
        ADULTO: r"""
.  ⌐( {cara} )¬  .
   /|     |\
    |     |
    |     |
    U     U
""",
        ADULTO_GRANDE: r"""
∙  .  ⌐(  {cara}  )¬  .  ∙
      /|       |\
       |       |
       |       |
      ░|       |░
       U       U
""",
    },
))

_registrar(Especie(
    clave="criold", nombre="Criold", emoji="❄️", color=CIAN,
    fuerza=6, velocidad=11, salud=7, rareza=COMUN, peso=0.0,
    descripcion="Cae despacio y siempre de pie. No se derrite: se ofende.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
*({cara})*
""",
        NINO: r"""
  \|/
*({cara})*
  /|\
""",
        ADOLESCENTE: r"""
 \ * /
=({cara})=
 / * \
""",
        ADULTO: r"""
 \  *  /
 * \|/ *
==({cara})==
 * /|\ *
 /  *  \
""",
        ADULTO_GRANDE: r"""
  \    *    /
' * \  |  / * '
 ====({cara})====
' * /  |  \ * '
  /    *    \
  '    '    '
""",
    },
))

_registrar(Especie(
    clave="goot", nombre="Goot", emoji="🐐", color=BLANCO,
    fuerza=12, velocidad=7, salud=5, rareza=COMUN, peso=0.0,
    descripcion="Sube por donde no hay camino. Baja igual de mal.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
 \ /
({cara})
 'v'
 n n
""",
        NINO: r"""
 \\ //
¬({cara})¬
  'v'
  n n
""",
        ADOLESCENTE: r"""
\\\___///
¬( {cara} )¬
  \ w /
  '-v-'
  n   n
""",
        ADULTO: r"""
\\\_____///
¬(  {cara}  )¬
  \  w  /
  '-vv-'
  //   \\
  n     n
""",
        ADULTO_GRANDE: r"""
\\\_______///
¬(   {cara}   )¬
  \   w   /
   '-vvv-'
  //     \\
  n       n
""",
    },
))

_registrar(Especie(
    clave="cefiro", nombre="Céfiro", emoji="🦅", color=AMARILLO,
    fuerza=9, velocidad=14, salud=7, rareza=RARA, peso=0.0,
    descripcion="Vive donde no llega nadie. Baja sólo si le conviene.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
({cara})
 ᐩ ᐩ
""",
        NINO: r"""
 \ /
({cara})
 ᐩ ᐩ
""",
        ADOLESCENTE: r"""
\\\  ///
\({cara})/
 \ ⌐ /
 ᐩ   ᐩ
""",
        ADULTO: r"""
\\\\\   /////
 \\\({cara})///
    \ ⌐ /
    /   \
    ᐩ   ᐩ
""",
        ADULTO_GRANDE: r"""
\\\\\\\     ///////
  \\\\\({cara})/////
      \\ ⌐ //
       |   |
       /   \
       ᐩ   ᐩ
""",
    },
))

_registrar(Especie(
    clave="noctule", nombre="Noctule", emoji="🦇", color=ROSA,
    fuerza=6, velocidad=13, salud=5, rareza=POCO_COMUN, peso=0.0,
    descripcion="Duerme de día y se queja de noche. Ve mejor que tú.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "u.u"},
    arte={
        BEBE: r"""
v({cara})v
""",
        NINO: r"""
vv({cara})vv
   ' '
""",
        ADOLESCENTE: r"""
vvv({cara})vvv
   \ ᵕ /
    ' '
""",
        ADULTO: r"""
vvvv      vvvv
 vvv({cara})vvv
   \  ᵕ  /
   |     |
   ''   ''
""",
        ADULTO_GRANDE: r"""
vvvvv       vvvvv
  vvvv({cara})vvvv
    \   ᵕ   /
    |  ,,,  |
    \       /
    ''     ''
""",
    },
))

_registrar(Especie(
    clave="prismlon", nombre="Prismlon", emoji="💎", color=AZUL,
    fuerza=12, velocidad=5, salud=13, rareza=RARA, peso=0.0,
    descripcion="Tardó mil años en formarse. Tiene la paciencia que eso implica.",
    caras={FELIZ: "^v^", NORMAL: "o.o", MAL: "x_x"},
    arte={
        BEBE: r"""
/{cara}\
 \_/
""",
        NINO: r"""
 /\
/{cara}\
\__/
""",
        ADOLESCENTE: r"""
 /\  /\
/  \/  \
| {cara} |
 \____/
""",
        ADULTO: r"""
 /\  /\
/  \/  \
/  {cara}  \
|   w   |
\_______/
""",
        ADULTO_GRANDE: r"""
   /\   /\
  /  \ /  \
 /    v    \
/   ({cara})   \
 |  ░░░░░  |
 \_________/
""",
    },
))
