"""Lo que el gachamon dice por su cuenta en el globo de la pantalla principal.

Frases escritas, nunca una llamada a la IA, y un globo no anuncia nada que no
esté pasando. Módulo puro: no importa `discord`, `db` ni `economia`.

Las frases se guardan con sus marcas de género («Estoy suci{o/a}.») y se
concuerdan al salir de `de`. Quién arma la pantalla y elige el globo llega
después: aquí sólo está lo que se puede decir y cómo escoger una.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

import especies as esp
import simulacion as sim

# Por debajo de esta barra, el gachamon lo dice.
UMBRAL_NECESIDAD = 40.0

NECESIDAD = "necesidad"
SUELTA = "suelta"


@dataclass(frozen=True)
class Globo:
    tipo: str
    texto: str


COMUNES: dict[str, tuple[str, ...]] = {
    "desfallecido": (
        "Ya no puedo más… Comida, por favor.",
        "Estoy desfallecid{o/a} de hambre.",
        "Todo me da vueltas. Necesito comer.",
    ),
    "hambre": (
        "Tengo hambre.",
        "Mi barriga hace ruiditos.",
        "¿Hay algo rico por ahí?",
        "Estoy hambrient{o/a}.",
    ),
    "sucio": (
        "Estoy suci{o/a}.",
        "Necesito un baño.",
        "Me siento pegajos{o/a}.",
    ),
    "aburrido": (
        "Estoy aburrid{o/a}.",
        "¿Jugamos a algo?",
        "Me vendría bien un poco de compañía.",
    ),
    "suelta": (
        "¿Cómo estás?",
        "Qué bien se está aquí.",
        "Me gusta que vengas.",
        "Hoy me siento con ganas de todo.",
        "¿Te cuento un secreto? Me gusta mirar el cielo.",
        "Estoy muy content{o/a}.",
    ),
}

# Lo que una especie tenga aquí manda sobre lo común, clave por clave.
PROPIAS: dict[str, dict[str, tuple[str, ...]]] = {
    "pollito": {
        "desfallecido": (
            "Pío… pío… no me quedan fuerzas.",
            "Pío, pío… necesito comer ya.",
        ),
        "hambre": (
            "¡Pío, pío! Tengo hambre.",
            "Pío… ¿hay semillitas?",
            "Pío, mi barriguita está vacía.",
        ),
        "sucio": (
            "¡Pío! Tengo las plumas sucias.",
            "Pío, quiero un baño.",
            "Pío… estoy hech{o/a} un desastre.",
        ),
        "aburrido": (
            "Pío, pío… ¿jugamos?",
            "Pío… me aburro.",
            "¡Pío! Hazme compañía.",
        ),
        "suelta": (
            "¡Pío! ¿Cómo estás?",
            "Pío, pío. Qué bien estamos.",
            "Pío… me gusta que vengas.",
            "¡Pío, pío! Estoy content{o/a}.",
        ),
    },
}


def _frases(criatura: sim.Criatura, clave: str) -> tuple[str, ...]:
    propias = PROPIAS.get(criatura.especie, {})
    return propias.get(clave, COMUNES[clave])


def de(criatura: sim.Criatura) -> tuple[Globo, ...]:
    """Todo lo que puede decir ahora, concordado con su género.

    Primero lo que necesita y después la charla. Con la comida en 0 se dice
    «desfallecido» en vez de «hambre». Una criatura muerta no dice nada.
    """
    if not criatura.viva:
        return ()
    necesidades: list[str] = []
    if criatura.hambre <= 0:
        necesidades.append("desfallecido")
    elif criatura.hambre < UMBRAL_NECESIDAD:
        necesidades.append("hambre")
    if criatura.limpieza < UMBRAL_NECESIDAD:
        necesidades.append("sucio")
    if criatura.animo < UMBRAL_NECESIDAD:
        necesidades.append("aburrido")
    salida = [
        Globo(NECESIDAD, esp.concordar(frase, criatura.genero))
        for clave in necesidades
        for frase in _frases(criatura, clave)
    ]
    salida += [Globo(SUELTA, esp.concordar(frase, criatura.genero)) for frase in _frases(criatura, "suelta")]
    return tuple(salida)


def elegir(globos: Sequence[Globo], anterior: str | None, rng: random.Random) -> Globo | None:
    """Escoge uno: de necesidad si hay alguno, y si no, de la charla.

    No repite `anterior` mientras su grupo tenga otra frase; nunca salta de
    grupo para evitar una repetición.
    """
    candidatas = [g for g in globos if g.tipo == NECESIDAD] or [g for g in globos if g.tipo == SUELTA]
    if not candidatas:
        return None
    otras = [g for g in candidatas if g.texto != anterior]
    return rng.choice(otras or candidatas)
