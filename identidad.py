"""Quién es quién en `usuario_id`: ids de Discord e identidades web.

Un id de Discord es un entero positivo. Una identidad web es el número de su
cuenta en negativo (`"-12"`), así que nunca puede chocar con uno de Discord.
Módulo puro: no importa nada del proyecto.

`sin_aviso_de_hambre` existe aparte de `es_web` a propósito. Es la pregunta que
hacen las reglas ("¿tiene esta persona cómo enterarse de que su gachamon se
muere de hambre?"). Hoy la respuesta coincide con `es_web`, pero el día que haya
notificaciones dejará de coincidir. Es el único sitio donde se **pregunta** por
la excepción, y las reglas preguntan por ella y nunca por `es_web`; pero cerrarla
pide además poner al día el reloj de quien sale de ella, como hace `db.activar`
con quien sale de la incubadora: su gachamon puede llevar días en 0 y, sin eso,
moriría en el siguiente `avanzar` con una fecha de muerte en el pasado.
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


def sin_aviso_de_hambre(usuario_id: str) -> bool:
    """¿Su dueño no tiene cómo enterarse de que el hambre llega a 0?"""
    return es_web(usuario_id)
