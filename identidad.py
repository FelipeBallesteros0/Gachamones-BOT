"""Quién es quién en `usuario_id`: ids de Discord e identidades web.

Un id de Discord es un entero positivo. Una identidad web es el número de su
cuenta en negativo (`"-12"`), así que nunca puede chocar con uno de Discord.
Módulo puro: no importa nada del proyecto.

`sin_plazo_de_refugio` existe aparte de `es_web` a propósito: es la pregunta
que hacen las reglas, y las reglas preguntan por ella y nunca por `es_web`. Hoy
la respuesta coincide con `es_web`, pero el día que cambie la excepción se
cambia sólo aquí. Del hambre ya no hay excepción que preguntar: no se muere
nadie, juegue donde juegue.
"""

from __future__ import annotations


def es_web(usuario_id: str) -> bool:
    """Cierto sólo para un entero positivo en negativo, sin ceros a la izquierda ni espacios."""
    cifras = usuario_id[1:]
    return (
        usuario_id.startswith("-")
        and cifras.isascii()
        and cifras.isdigit()
        and not cifras.startswith("0")
    )


def de_cuenta_web(rowino_uid: int) -> str:
    """El `usuario_id` de la identidad web de una cuenta: `12` -> `"-12"`."""
    if rowino_uid < 1:
        raise ValueError("el número de cuenta web empieza en 1")
    return str(-rowino_uid)


def sin_plazo_de_refugio(usuario_id: str) -> bool:
    """¿Su estancia en el refugio no vence? Quien juega sólo en la web no gana
    lo bastante para comprarse una casa antes de que corra el plazo de siempre."""
    return es_web(usuario_id)
