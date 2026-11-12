"""Códigos para vincular una cuenta de Rowino con una persona de Discord.

La cuenta de la web pide un código de un solo uso y la persona lo escribe en
Discord: quién lo escribe es la única prueba de identidad. Módulo puro: no
importa nada del proyecto. La base de datos y las transacciones viven en `db.py`.
"""

from __future__ import annotations

import random
import secrets
from datetime import timedelta

# Sin I, L, O, 0 ni 1: son las que se confunden al copiar a mano.
ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LARGO = 8
MINUTOS_DE_VIDA = 10
INTENTOS_MAXIMOS = 5
VENTANA_DE_INTENTOS = timedelta(minutes=10)

OK = "ok"
INVALIDO = "invalido"
DEMASIADOS = "demasiados"
YA_VINCULADA = "ya_vinculada"
# Sólo sale por `NoSePuede` al pedir un código, nunca como resultado de un canje.
CON_GACHAMONES = "con_gachamones"

# Lo que el bot contesta a cada resultado de un canje. Hay un solo texto para
# «no existe», «caducó» y «su cuenta ya no puede vincularse»: distinguirlos le
# diría a un adivino qué códigos existen.
MENSAJES: dict[str, str] = {
    OK: (
        "✅ Listo. Tu cuenta de Rowino quedó vinculada: vuelve a la web y vas a "
        "encontrar a tus gachamones."
    ),
    INVALIDO: (
        "Ese código no sirve. Pide uno nuevo en la web y escríbelo antes de que "
        "caduque."
    ),
    DEMASIADOS: "Demasiados intentos. Espera unos minutos y pide un código nuevo.",
    YA_VINCULADA: (
        "Tu cuenta de Discord ya está vinculada a una cuenta de Rowino. Si es un "
        "error, avísale a quien administra el servidor."
    ),
}


class NoSePuede(Exception):
    """Pedir un código no procede; `motivo` es `YA_VINCULADA` o `CON_GACHAMONES`."""

    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo


def nuevo_codigo(rng: random.Random | None = None) -> str:
    """Un código al azar. Con `rng` es determinista; sin él usa `secrets`."""
    elegir = rng.choice if rng is not None else secrets.choice
    return "".join(elegir(ALFABETO) for _ in range(LARGO))


def normalizar(codigo: str) -> str:
    """Mayúsculas y sin espacios ni guiones: como se escribe en un celular."""
    return "".join(
        c for c in codigo.upper() if not c.isspace() and c != "-"
    )
