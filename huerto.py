"""Los porotos de colores y las sopaipillas.

Módulo puro: catálogo y reglas, sin base de datos ni Discord.

El huerto por casa se fue, y vuelve más adelante. Lo que se queda es lo que dio:
con tres porotos del mismo color se cocina una sopaipilla que le da a tu
gachamon un bonus temporal. Lo que hace que el color importe es que **a cada
carácter le gustan en distinto orden**: la misma sopaipilla es un 1d12 para un
gruñón y un 1d4 para un miedoso.

Las cuentas de la cosecha se quedan también, porque con ellas cosechó el día del
cambio lo que cada quien tenía plantado (`economia.el_dia_del_cambio`). **El
color lo hereda lo sembrado**: de un poroto rojo salen rojos. Sólo sortean color
la semilla y el poroto arcoíris.

Y de cualquier cosecha puede salir un **poroto arcoíris**, uno solo y con poca
probabilidad. No tiene color, así que sembrarlo no hereda nada; lo que sí hace es
una sopaipilla que no mira el carácter y sube las cuatro estadísticas a la vez.
"""
from __future__ import annotations

import random

# Los cinco colores y los cinco tamaños de dado, que se corresponden uno a uno:
# el sitio que ocupe el color en la lista de tu carácter decide con qué dado se
# tira. El primero es 1d12 y el último 1d4.
COLORES = ("rojo", "azul", "verde", "rosa", "amarillo")
CARAS_POR_PUESTO = (12, 10, 8, 6, 4)

EMOJI_COLOR = {
    "rojo": "🔴", "azul": "🔵", "verde": "🟢", "rosa": "🩷", "amarillo": "🟡",
}

# El plural de cada color, escrito entero. Cuatro hacen «-s» y «azul» hace
# «azules», así que una regla tendría una excepción de cinco: sale más barato
# la tabla, y además es la única forma de que el mensaje concuerde bien.
PLURAL_COLOR = {
    "rojo": "rojos", "azul": "azules", "verde": "verdes",
    "rosa": "rosas", "amarillo": "amarillos",
}

# A qué sabe cada color según el carácter, del que más le gusta al que menos.
# Se escribe entero y no se deduce de una rueda de colores: es una tabla de
# gustos, y lo que la hace divertida es que no siga ninguna regla adivinable.
AFINIDAD: dict[str, tuple[str, ...]] = {
    "alegre":    ("amarillo", "rosa", "verde", "rojo", "azul"),
    "sereno":    ("azul", "verde", "amarillo", "rosa", "rojo"),
    "miedoso":   ("verde", "azul", "rosa", "amarillo", "rojo"),
    "valiente":  ("rojo", "amarillo", "azul", "verde", "rosa"),
    "gruñón":    ("rojo", "verde", "azul", "amarillo", "rosa"),
    "curioso":   ("rosa", "amarillo", "azul", "rojo", "verde"),
    "cariñoso":  ("rosa", "rojo", "amarillo", "verde", "azul"),
    "orgulloso": ("azul", "rojo", "rosa", "verde", "amarillo"),
    "perezoso":  ("verde", "rosa", "azul", "rojo", "amarillo"),
    "travieso":  ("amarillo", "rojo", "verde", "azul", "rosa"),
}

# Lo que se podía sembrar y no es un poroto: la semilla. Su clave es la misma
# que la del objeto, y también el `DEFAULT` de la columna `sembrado`, así que los
# bancales plantados antes de que el poroto fuera sembrable se comportan solos
# como siempre: color al azar al cosechar.
SEMILLA = "semilla"

# El poroto arcoíris. **No entra en `COLORES` a propósito**: esa tupla alimenta
# `tirar_color`, la tabla de afinidad y el bucle que registra el catálogo, así
# que meterlo dentro lo volvería un color más —sorteable y con gustos— y es justo
# lo contrario de lo que es. No tiene color: por eso sembrarlo no hereda nada y
# su sopaipilla no mira el carácter.
ARCOIRIS = "arcoiris"
EMOJI_ARCOIRIS = "🌈"
# La clave va sin tilde, porque es clave de objeto y de columna; el texto la
# lleva. Y no tiene plural: «tres porotos arcoíris».
NOMBRE_ARCOIRIS = "arcoíris"

# El dado de la sopaipilla arcoíris **se sortea al cocinarla**, entre los mismos
# cinco tamaños que dan las de color. No puede salir del carácter porque no tiene
# color con el que consultar la tabla de gustos, y dejarlo siempre en 1d12 la
# volvía la mejor sopaipilla posible sin nada que jugarse: así cocinarla también
# se disfruta. Por eso hay cinco sopaipillas arcoíris en el catálogo y no una —el
# dado tiene que recordarse desde que se cuece hasta que alguien se la come—,
# igual que las pociones de la tienda son cinco por estadística.
CARAS_DE_ARCOIRIS = CARAS_POR_PUESTO

# Cada cuánto sale un arcoíris en una cosecha. Sale **uno** del lote, no el lote
# entero: lo que se busca es el hallazgo suelto que guardas, no una cosecha que
# valga por diez.
PROBABILIDAD_ARCOIRIS = 0.05

POROTOS_POR_SOPAIPILLA = 3

# Cuántos porotos da una cosecha, extremos incluidos. Con uno solo, y siendo el
# color al azar entre cinco, una sopaipilla pedía del orden de quince cosechas:
# demasiado poco para ocho horas de espera por bancal.
POROTOS_POR_COSECHA = (2, 4)


def caras_de(caracter: str, color: str) -> int:
    """Con qué dado se tira una sopaipilla de ese color para ese carácter."""
    orden = AFINIDAD[caracter]
    return CARAS_POR_PUESTO[orden.index(color)]


def le_gusta(caracter: str, color: str) -> str:
    """Cómo describirlo sin soltar el número, para el mensaje."""
    puesto = AFINIDAD[caracter].index(color)
    return ("es su favorito", "le gusta mucho", "le gusta",
            "no le entusiasma", "lo detesta")[puesto]


# De qué hay poroto y sopaipilla. Es `COLORES` más el arcoíris, y existe porque
# casi todo lo que recorre los colores tiene que recorrer también el arcoíris:
# cocinarlo, enseñarlo en la mochila y ofrecerlo en los menús. Lo que **no** lo
# incluye es el sorteo del color ni la tabla de gustos, que es justo el motivo de
# que el arcoíris no esté en `COLORES`.
COCINABLES = (*COLORES, ARCOIRIS)


def emoji_de(color: str) -> str:
    return EMOJI_ARCOIRIS if color == ARCOIRIS else EMOJI_COLOR[color]


def nombre_de(color: str) -> str:
    return NOMBRE_ARCOIRIS if color == ARCOIRIS else color


def plural_de(color: str) -> str:
    return NOMBRE_ARCOIRIS if color == ARCOIRIS else PLURAL_COLOR[color]


def clave_de_poroto(color: str) -> str:
    return f"poroto_{color}"


def clave_de_sopaipilla(color: str, caras: int = 0) -> str:
    """La sopaipilla de ese color, y con qué dado si lo lleva escrito.

    Sólo el arcoíris lo lleva: las de color sacan el dado del carácter de quien
    se la come, así que no hay nada que guardar. El arcoíris lo sortea al
    cocinarse, y si no fuera en la clave se perdería en cuanto entrara en la
    mochila.
    """
    return f"sopaipilla_{color}_1d{caras}" if caras else f"sopaipilla_{color}"


def tirar_color(rng: random.Random | None = None) -> str:
    return (rng or random.Random()).choice(COLORES)


def tirar_cuantos(rng: random.Random | None = None) -> int:
    """Cuántos porotos da esta cosecha. Todos serán del mismo color.

    El RNG se inyecta como en `tirar_color`: en las pruebas se fija y el
    resultado deja de depender del azar.
    """
    return (rng or random.Random()).randint(*POROTOS_POR_COSECHA)


def tirar_arcoiris(rng: random.Random | None = None) -> bool:
    """Si esta cosecha trae un arcoíris. Uno, sea cual sea el tamaño del lote."""
    return (rng or random.Random()).random() < PROBABILIDAD_ARCOIRIS


def tirar_caras_de_arcoiris(rng: random.Random | None = None) -> int:
    """Con qué dado sale esta sopaipilla arcoíris. Los cinco, por igual.

    Sin cargar los dados hacia el 12: el arcoíris ya es mejor que cualquier
    sopaipilla de color con el mismo dado, porque sube las cuatro estadísticas
    en vez de dos. Que además saliera casi siempre el dado mayor lo dejaría sin
    nada que jugarse al cocinarlo.
    """
    return (rng or random.Random()).choice(CARAS_DE_ARCOIRIS)


def color_sembrado(sembrado: str) -> str | None:
    """El color que hereda la cosecha, o `None` si toca sortearlo.

    Devuelven `None` la semilla —que es la puerta a un color que no tienes— y el
    arcoíris, que no tiene color que heredar. Cualquier otra cosa que no se
    reconozca cae también en el sorteo: es lo que hacía el huerto entero antes de
    que el poroto fuera sembrable, así que es el peor caso que sabemos tratar.
    """
    color = sembrado.removeprefix("poroto_")
    return color if color in COLORES else None
