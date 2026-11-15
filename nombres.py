"""Los nombres que se pone un recluta él solo al unirse.

Módulo puro: sin discord, sin SQLite y sin azar propio. Lo usan el
reclutamiento (`nacer.unir_recluta`) y la migración que les pone nombre a los
que se unieron antes y lo esperaban (`db._migrar`).

Son cuarenta, más que los gachamones que caben (`departamento.MAXIMO_DE_GACHAMONES`), así que a quien
se une siempre le queda alguno que no lleva otro de su dueño.
"""
from __future__ import annotations

import random
from collections.abc import Collection

NOMBRES: tuple[str, ...] = (
    "Nube", "Miga", "Trufa", "Copo", "Brote", "Chispa", "Pompón", "Motita",
    "Lenteja", "Garbanzo", "Pistacho", "Canela", "Mochi", "Churro", "Fideo",
    "Ñoqui", "Maní", "Kiwi", "Coco", "Menta", "Mote", "Piñón", "Maqui",
    "Lúcuma", "Murta", "Calafate", "Boldo", "Nalca", "Luche", "Merkén",
    "Charqui", "Totora", "Burbuja", "Cochayuyo", "Rulo", "Tambor", "Pepita",
    "Galleta", "Bolita", "Pixel",
)


def elegir(rng: random.Random, evitar: Collection[str] = ()) -> str:
    """Uno de `NOMBRES` al azar que no esté en `evitar`, sin mirar mayúsculas.

    Si estuvieran todos, uno cualquiera de la lista: un nombre repetido es
    mejor que ninguno, y ningún gachamon se queda sin nombre.
    """
    tomados = {nombre.casefold() for nombre in evitar}
    libres = [nombre for nombre in NOMBRES if nombre.casefold() not in tomados]
    return rng.choice(libres or NOMBRES)
