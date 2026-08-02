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

import huerto as hue
import simulacion as sim

# Cuánto dura una poción de estadística. Cinco minutos y no uno: quien acepta un
# reto tiene 120 segundos para pulsar, y la estadística se lee al **resolver** la
# pelea, no al retar. Con un minuto la poción habría caducado en la mayoría de
# las carreras y no habría forma de saber por qué no hizo nada.
MINUTOS_DE_EFECTO = 5

ASCIICOINS_INICIALES = 50
ASCIIGEMS_INICIALES = 50
MONEDA_TIENDA = "asciicoins"
EMOJI_MONEDA_TIENDA = "🪙"
EMOJI_GEMA = "💎"


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
    # Cuánta hambre devuelve al usarlo desde la mochila. Es un número y no una
    # bandera para que quepan el tentempié y la comida entera con la misma
    # regla: sumar 100 y recortar a 100 **es** «déjalo lleno».
    alimenta: int = 0
    # Abre un formulario para cambiarle el nombre al gachamon activo.
    renombra: bool = False
    # Sirve además en una aventura, para ganarse a un salvaje. Se gasta al
    # ofrecérselo, sin pasar por la mochila.
    ceba: bool = False
    # Devuelve una estancia entera en el refugio. Es la salida de la intemperie
    # para quien todavía no llega a una casa.
    dias_de_refugio: int = 0
    # De qué color es, si es un poroto o una sopaipilla. Los porotos no hacen
    # nada por sí solos —son ingrediente— y las sopaipillas dan el bonus.
    color: str | None = None
    es_sopaipilla: bool = False
    # Si sale a la venta. Lo que se cosecha o se cocina no se compra, y además
    # no cabría: la tienda ya roza las 25 opciones que admite un desplegable.
    se_vende: bool = True

    @property
    def se_usa_en_mochila(self) -> bool:
        """Si elegirlo en la mochila hace algo, con formulario o sin él.

        Lo consulta el menú **antes de gastar la unidad**: sin esto, elegir algo
        que sólo sirve de cebo te costaría el objeto a cambio de nada.
        """
        return bool(
            self.reinicia or self.stat or self.alimenta or self.renombra
            or self.dias_de_refugio or self.es_sopaipilla
        )

    @property
    def se_aplica_al_momento(self) -> bool:
        """Si `tienda.usar` lo resuelve por sí solo al elegirlo.

        La placa no: necesita que escribas el nombre, así que abre un formulario
        y se gasta al confirmarlo. Por eso son dos propiedades y no una.
        """
        return bool(
            self.reinicia or self.stat or self.alimenta or self.dias_de_refugio
            or self.es_sopaipilla
        )


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
    descripcion="Deja la comida a 100. Ni empacha ni gasta el enfriamiento.",
    alimenta=100,  # sumar 100 y recortar a 100: llena desde donde esté
))

# Reinicia la espera de diez minutos entre peleas, que es la que de verdad topa
# cuánto se puede competir. A 5 —lo que costaba cuando esa espera era de tres
# minutos— se compraban veinte con el saldo de partida y la espera dejaba de
# existir, que es lo contrario de lo que se busca.
_registrar(Objeto(
    clave="descanso_rapido",
    nombre="Poción de descanso rápido",
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

# El único de dos usos, y por eso su descripción los dice los dos. Alimenta menos
# que la poción de comida a propósito: si llenara igual, la poción —que cuesta
# más y encima no sirve de cebo— no la compraría nadie.
_registrar(Objeto(
    clave="golosinas",
    nombre="Golosinas de campo",
    emoji="🍬",
    precio=8,
    descripcion=(
        "Un tentempié: +25 de comida. Y en una aventura, para ganarte a un "
        "gachamon salvaje."
    ),
    alimenta=25,
    ceba=True,
))

_registrar(Objeto(
    clave="placa",
    nombre="Placa con nombre",
    emoji="🏷️",
    precio=15,
    descripcion="Le cambia el nombre a tu gachamon activo.",
    renombra=True,
))

# La salida de la intemperie para quien todavía no llega a una casa. Cuesta
# poco a propósito: es una red de seguridad, no una alternativa a comprar. Quien
# lo use cada semana gasta más que la casa pequeña en dos meses y sigue sin
# tener dónde poner un mueble.
_registrar(Objeto(
    clave="ticket_refugio",
    nombre="Ticket del refugio",
    emoji="🎟️",
    precio=40,
    descripcion="Otra semana en el refugio, desde que lo uses.",
    dias_de_refugio=7,
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
    if objeto.alimenta:
        return replace(
            criatura, hambre=min(100.0, criatura.hambre + objeto.alimenta)
        )
    return criatura


# --- Lo del huerto ---------------------------------------------------------
#
# Nada de esto sale a la venta salvo la semilla: los porotos se cosechan y las
# sopaipillas se cocinan. Van en el catálogo igual porque viven en la mochila y
# se pueden regalar por el buzón, que es media gracia de tener colores.

_registrar(Objeto(
    clave="semilla",
    nombre="Semilla de poroto",
    emoji="🌱",
    precio=15,
    descripcion="Se planta en el huerto de tu casa. Sale un poroto de color al azar.",
))

for _color in hue.COLORES:
    _registrar(Objeto(
        clave=hue.clave_de_poroto(_color),
        nombre=f"Poroto {_color}",
        emoji=hue.EMOJI_COLOR[_color],
        precio=0,
        descripcion=(
            f"Ingrediente. Con {hue.POROTOS_POR_SOPAIPILLA} se cocina una "
            f"sopaipilla {_color}."
        ),
        color=_color,
        se_vende=False,
    ))
    _registrar(Objeto(
        clave=hue.clave_de_sopaipilla(_color),
        nombre=f"Sopaipilla {_color}",
        emoji="🥟",
        precio=0,
        descripcion=(
            "Bonus de fuerza y velocidad a la vez, por unos minutos. Cuánto "
            "depende de si a tu gachamon le gusta el color."
        ),
        color=_color,
        es_sopaipilla=True,
        se_vende=False,
    ))
