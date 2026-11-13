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
LUGAR = "lugar"


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
        "¿Qué me cuentas?",
        "Me gusta que vengas.",
        "¿Qué hiciste hoy?",
        "¿Te cuento un secreto? Me gusta mirar el cielo.",
        "Te estaba esperando.",
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
            "Pío, pío. ¿Qué me cuentas?",
            "Pío… me gusta que vengas.",
            "¡Pío, pío! Te estaba esperando.",
        ),
    },
}

# Lo que dice de cada lugar del pueblo: cómo es, a qué huele, qué se oye. Nada de
# lo que se hace ahí ni de quién hay. Las claves son las de `web/pueblo.py`
# (una prueba vigila que coincidan); este módulo no lo importa.
DEL_LUGAR: dict[str, tuple[str, ...]] = {
    "casa": (
        "Qué calentito se está aquí.",
        "Este rincón me da sueño.",
        "Aquí se oye el silencio de las casas.",
    ),
    "refugio": (
        "Huele a mantas viejas.",
        "Aquí siempre hay un poco de corriente.",
        "Es un lugar sencillo, pero abriga.",
    ),
    "incubadora": (
        "Aquí hace un calorcito muy suave.",
        "Huele a cáscara tibia.",
        "Todo está quietito, como si durmiera.",
    ),
    "tienda": (
        "Cuántas cosas hay en los estantes.",
        "Huele a madera y a pintura fresca.",
        "¿Me compras algo?",
    ),
    "plaza": (
        "Qué amplia es la plaza.",
        "Se oye el eco de mis pasitos.",
        "Aquí da el sol a todas horas.",
    ),
    "barrio": (
        "Las calles huelen a pan recién hecho.",
        "Qué tranquilo está el barrio.",
        "Me gustan estos faroles.",
    ),
    "estadio": (
        "Las gradas son enormes.",
        "Se me eriza todo con este eco.",
        "Qué grande se ve el campo desde aquí.",
    ),
    "cementerio": (
        "Qué silencio hay aquí.",
        "Huele a tierra húmeda.",
        "Las piedras están frías y quietas.",
    ),
    "aventura": (
        "Desde aquí se ve el camino largo.",
        "Sopla un viento que huele a lejos.",
        "El horizonte se ve enorme.",
    ),
}

# Como PROPIAS: lo que una especie diga en un lugar manda sobre lo común, para ese lugar.
PROPIAS_DEL_LUGAR: dict[str, dict[str, tuple[str, ...]]] = {
    "pollito": {
        "casa": ("Pío, qué calentito se está.", "Pío… este rincón me da sueño."),
        "refugio": ("Pío, huele a mantas viejas.", "Pío… aquí hay corriente."),
        "incubadora": ("Pío, huele a cáscara tibia.", "Pío… qué calorcito."),
        "tienda": ("Pío, cuántas cosas.", "Pío… huele a madera nueva."),
        "plaza": ("¡Pío! Qué amplia es la plaza.", "Pío, pío… aquí hay mucho sol."),
        "barrio": ("Pío, huele a pan recién hecho.", "Pío… qué tranquilo está."),
        "estadio": ("¡Pío! Las gradas son enormes.", "Pío… el eco me eriza las plumas."),
        "cementerio": ("Pío… qué silencio.", "Pío, huele a tierra húmeda."),
        "aventura": ("¡Pío! El camino se ve larguísimo.", "Pío, pío… sopla un viento de lejos."),
    },
}


def _frases(criatura: sim.Criatura, clave: str) -> tuple[str, ...]:
    propias = PROPIAS.get(criatura.especie, {})
    return propias.get(clave, COMUNES[clave])


def de(criatura: sim.Criatura, lugar: str | None = None) -> tuple[Globo, ...]:
    """Todo lo que puede decir ahora, concordado con su género.

    Primero lo que necesita, luego lo del lugar donde está (si `lugar` es uno
    de `DEL_LUGAR`) y al final la charla. Con la comida en 0 se dice
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
    if lugar in DEL_LUGAR:
        frases = PROPIAS_DEL_LUGAR.get(criatura.especie, {}).get(lugar, DEL_LUGAR[lugar])
        salida += [Globo(LUGAR, esp.concordar(frase, criatura.genero)) for frase in frases]
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
