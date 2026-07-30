"""Los consumibles: qué se vende, cuánto cuesta y qué hace cada cosa.

Módulo puro, como `especies.py`: aquí sólo está el catálogo y las reglas. Ni
base de datos ni Discord. El generador de dados se pasa como argumento, así que
los tests fijan la tirada y comprueban el resultado exacto.

Un objeto hace **una sola cosa**, y hay un test que lo vigila: o da un bonus a
una estadística, o llena el hambre, o borra un enfriamiento. Mezclar efectos
haría imposible contar en un renglón qué compraste.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace

import simulacion as sim

# Cuánto dura una poción de estadística. Cinco minutos y no uno: quien acepta un
# reto tiene 120 segundos para pulsar, y la estadística se lee al **resolver** la
# pelea, no al retar. Con un minuto la poción habría caducado en la mayoría de
# las carreras y no habría forma de saber por qué no hizo nada.
MINUTOS_DE_EFECTO = 5

# Lo que se le regala a cada persona la primera vez que abre el monedero.
# Provisional: la idea es que más adelante salgan de eventos o de comprarlas.
GEMAS_DE_BIENVENIDA = 100

MONEDA = "asciigemas"
EMOJI_MONEDA = "💎"


@dataclass(frozen=True)
class Objeto:
    clave: str
    nombre: str
    emoji: str
    precio: int
    descripcion: str
    # Poción de estadística: a cuál va y con cuántas caras se tira.
    stat: str | None = None
    caras: int = 0
    # Objeto que borra el enfriamiento de una acción.
    reinicia: str | None = None
    # Poción de comida.
    llena_el_hambre: bool = False


CATALOGO: dict[str, Objeto] = {}


def _registrar(objeto: Objeto) -> Objeto:
    CATALOGO[objeto.clave] = objeto
    return objeto


# Cuánto cuesta cada tamaño de dado. Van de menos a más porque una poción mayor
# que costara menos dejaría a la pequeña sin comprador.
PRECIOS_POR_CARAS = {4: 8, 6: 12, 8: 18, 10: 26, 12: 36}

_ESTADISTICAS = {
    "fuerza": ("💪", "Fuerza", "el sumo"),
    "velocidad": ("💨", "Velocidad", "las carreras"),
}

for _stat, (_emoji, _titulo, _donde) in _ESTADISTICAS.items():
    for _caras, _precio in PRECIOS_POR_CARAS.items():
        _registrar(Objeto(
            clave=f"{_stat}_1d{_caras}",
            nombre=f"Poción de {_titulo.lower()} 1d{_caras}",
            emoji=_emoji,
            precio=_precio,
            descripcion=(
                f"+1d{_caras} de {_stat} durante {MINUTOS_DE_EFECTO} min. "
                f"Se nota en {_donde}."
            ),
            stat=_stat,
            caras=_caras,
        ))

_registrar(Objeto(
    clave="pocion_comida",
    nombre="Poción de comida",
    emoji="🧃",
    precio=10,
    descripcion="Deja el hambre a 100. Ni empacha ni gasta el enfriamiento.",
    llena_el_hambre=True,
))

# Reinicia la espera de diez minutos entre peleas, que es la que de verdad topa
# cuánto se puede competir. A cinco gemas —lo que costaba cuando esa espera era
# de tres minutos— se compraban veinte y la espera dejaba de existir, que es lo
# contrario de lo que se busca.
_registrar(Objeto(
    clave="descanso_rapido",
    nombre="Descanso rápido",
    emoji="😮‍💨",
    precio=12,
    descripcion="Deja competir otra vez ya, sin esperar el enfriamiento.",
    reinicia=sim.COMPETIR,
))

_registrar(Objeto(
    clave="silbato",
    nombre="Silbato del entrenador",
    emoji="📣",
    precio=20,
    descripcion="Deja entrenar otra vez ya. La espera normal es de casi dos horas.",
    reinicia=sim.ENTRENAR,
))


def tirar_bonus(objeto: Objeto, rng: random.Random | None = None) -> int:
    """Lo que suma una poción de estadística.

    Se tira **al beberla**, no al competir, para que el mensaje pueda decir
    cuánto te ha tocado. Tirándolo en la pelea el número quedaría escondido y no
    habría forma de saber si la poción sirvió de algo.
    """
    if objeto.stat is None:
        return 0
    return (rng or random.Random()).randint(1, objeto.caras)


def aplicar_a_la_criatura(objeto: Objeto, criatura: sim.Criatura) -> sim.Criatura:
    """La parte del efecto que cambia a la criatura, si la hay.

    Las pociones de estadística y los reinicios no tocan la criatura: viven en
    sus propias tablas. Devuelven la misma que entró.
    """
    if objeto.llena_el_hambre:
        return replace(criatura, hambre=100.0)
    return criatura
