"""El huerto de la casa: porotos de colores y sopaipillas.

Módulo puro, como `casas.py`: catálogo y reglas, sin base de datos ni Discord.

El bucle es corto y tiene una gracia: se planta una semilla, sale un poroto **de
color al azar**, y con tres del mismo color se cocina una sopaipilla que le da a
tu gachamon un bonus temporal de fuerza y velocidad. Lo que hace que el color
importe es que **a cada carácter le gustan en distinto orden**: la misma
sopaipilla es un 1d12 para un gruñón y un 1d4 para un miedoso.

Que el color salga al azar es a propósito. Con semillas de color elegido, cada
cual se cocinaría lo suyo y no hablaría con nadie; así acabas con porotos que no
te sirven y con vecinos a los que sí, que es justo para lo que está el buzón.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta

# Los cinco colores y los cinco tamaños de dado, que se corresponden uno a uno:
# el sitio que ocupe el color en la lista de tu carácter decide con qué dado se
# tira. El primero es 1d12 y el último 1d4.
COLORES = ("rojo", "azul", "verde", "rosa", "amarillo")
CARAS_POR_PUESTO = (12, 10, 8, 6, 4)

EMOJI_COLOR = {
    "rojo": "🔴", "azul": "🔵", "verde": "🟢", "rosa": "🩷", "amarillo": "🟡",
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

# Cuánto tarda un bancal y cuánto ahorra regarlo a mitad de camino. Regar no es
# obligatorio: es lo que premia pasarse a media tarde.
HORAS_DE_CULTIVO = 8
HORAS_QUE_AHORRA_REGAR = 3

POROTOS_POR_SOPAIPILLA = 3

# Cuántos bancales da cada casa, por su clave. El refugio no tiene huerto: no es
# tuyo. Se guarda por clave y no por `casas.Casa` a propósito: así este módulo no
# importa `casas`, y `objetos` —que sí importa éste— no acaba arrastrando la pila
# entera de dibujo por la cadena `casas → jardin → pantalla`.
BANCALES = {"pequena": 1, "mediana": 2, "grande": 3}


def bancales_de(clave_de_casa: str | None) -> int:
    return BANCALES.get(clave_de_casa or "", 0)


def caras_de(caracter: str, color: str) -> int:
    """Con qué dado se tira una sopaipilla de ese color para ese carácter."""
    orden = AFINIDAD[caracter]
    return CARAS_POR_PUESTO[orden.index(color)]


def le_gusta(caracter: str, color: str) -> str:
    """Cómo describirlo sin soltar el número, para el mensaje."""
    puesto = AFINIDAD[caracter].index(color)
    return ("es su favorito", "le gusta mucho", "le gusta",
            "no le entusiasma", "lo detesta")[puesto]


def clave_de_poroto(color: str) -> str:
    return f"poroto_{color}"


def clave_de_sopaipilla(color: str) -> str:
    return f"sopaipilla_{color}"


def tirar_color(rng: random.Random | None = None) -> str:
    return (rng or random.Random()).choice(COLORES)


@dataclass(frozen=True)
class Bancal:
    """Un trozo de huerto. Sin `plantado_en` está en barbecho."""

    numero: int
    plantado_en: datetime | None = None
    regado: bool = False

    @property
    def plantado(self) -> bool:
        return self.plantado_en is not None

    def listo_en(self) -> datetime | None:
        if self.plantado_en is None:
            return None
        horas = HORAS_DE_CULTIVO - (HORAS_QUE_AHORRA_REGAR if self.regado else 0)
        return self.plantado_en + timedelta(hours=horas)

    def listo(self, ahora: datetime) -> bool:
        momento = self.listo_en()
        return momento is not None and ahora >= momento

    def puede_regarse(self, ahora: datetime) -> bool:
        """Sólo mientras crece: regar lo ya listo no adelantaría nada."""
        return self.plantado and not self.regado and not self.listo(ahora)
