"""Quién está al otro lado: la sesión de Rowino, y nada más.

Rowino firma una cookie con `{"uid": <entero>}`; aquí se verifica y se
comprueba en su base (sólo lectura) que la cuenta existe y no está bloqueada.
Nada se recuerda entre peticiones. Ante cualquier duda, no entra nadie; y si
lo que falla es el propio servicio (sin clave, o sin poder leer la base de
Rowino), se dice que no está disponible en vez de pedir que se entre.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, Request
from itsdangerous import URLSafeSerializer

import config

log = logging.getLogger("gachamones")

COOKIE = "session"


@dataclass(frozen=True)
class Persona:
    rowino_uid: int
    usuario: str


class RowinoNoSeLee(Exception):
    """No se pudo mirar la base de Rowino: no es lo mismo que «no existe»."""


def problema(estado: int, clave: str, mensaje: str) -> HTTPException:
    """La única forma de contestar un error en todo el servicio."""
    return HTTPException(
        status_code=estado, detail={"clave": clave, "mensaje": mensaje},
    )


def es_un_id(valor: object) -> bool:
    """Si `valor` puede ser el id de un gachamon: un entero positivo que cabe en SQLite.

    Ni un texto, ni un decimal, ni `true`; y uno de 2**63 o más no se puede ni
    buscar (SQLite lanzaría `OverflowError`, que saldría como un 500).
    """
    return type(valor) is int and 0 < valor < 2**63


def leer_cookie(valor: str | None) -> int | None:
    """El `uid` de una cookie firmada por Rowino; `None` ante cualquier duda."""
    try:
        clave = config.ROWINO_SECRET_KEY
        if not valor or not clave or not isinstance(clave, str):
            return None
        cuerpo = URLSafeSerializer(clave, salt="session").loads(valor)
        if not isinstance(cuerpo, dict):
            return None
        uid = cuerpo.get("uid")
        if type(uid) is not int or uid <= 0:
            return None
        return uid
    except Exception:
        return None


def _direccion_de_solo_lectura(ruta) -> str:
    return Path(ruta).absolute().as_uri() + "?mode=ro"


def buscar_persona(rowino_uid: int) -> Persona | None:
    """La persona de Rowino con ese id, si existe y no está bloqueada.

    Lanza `RowinoNoSeLee` si su base no se pudo leer (no está, está rota o le
    falta la tabla): eso es un fallo del servicio, no una cuenta que no existe.
    """
    try:
        con = sqlite3.connect(
            _direccion_de_solo_lectura(config.RUTA_ROWINO_BD), uri=True,
        )
        try:
            fila = con.execute(
                "SELECT id, username, blocked FROM users WHERE id = ?",
                (rowino_uid,),
            ).fetchone()
        finally:
            con.close()
    except Exception as error:
        log.warning(
            "No se pudo leer la base de Rowino: %s", type(error).__name__,
        )
        raise RowinoNoSeLee from None
    if fila is None:
        return None
    ident, usuario, bloqueada = fila
    if bloqueada != 0 or type(ident) is not int or not isinstance(usuario, str):
        return None
    return Persona(rowino_uid=ident, usuario=usuario)


def puede_dibujar(rowino_uid: int) -> bool:
    """Si la cuenta tiene el permiso del dibujante: `arte_access` o `is_admin`, y no está bloqueada.

    Es una consulta aparte de `buscar_persona`: primero mira qué columnas tiene
    `users` y lee sólo las que existen, así que una base sin `arte_access` (o sin
    `is_admin`) no da el permiso a nadie por esa vía. Si la base no se puede leer
    no hay permiso, y no falla nada.
    """
    try:
        con = sqlite3.connect(
            _direccion_de_solo_lectura(config.RUTA_ROWINO_BD), uri=True,
        )
        try:
            existentes = {fila[1] for fila in con.execute("PRAGMA table_info(users)")}
            permisos = [c for c in ("arte_access", "is_admin") if c in existentes]
            if not permisos or "blocked" not in existentes:
                return False
            fila = con.execute(
                f"SELECT blocked, {', '.join(permisos)} FROM users WHERE id = ?",
                (rowino_uid,),
            ).fetchone()
        finally:
            con.close()
    except Exception as error:
        log.warning(
            "No se pudo leer el permiso del dibujante: %s", type(error).__name__,
        )
        return False
    if fila is None or fila[0] != 0:
        return False
    return any(valor == 1 for valor in fila[1:])


def _sin_servicio() -> HTTPException:
    return problema(503, "servicio", "El juego no está disponible ahora mismo.")


def persona_actual(request: Request) -> Persona:
    clave = config.ROWINO_SECRET_KEY
    if not clave or not isinstance(clave, str):
        # Sin clave no se puede verificar ninguna cookie: no entra nadie, y
        # no es porque falte la sesión.
        raise _sin_servicio()
    uid = leer_cookie(request.cookies.get(COOKIE))
    try:
        persona = buscar_persona(uid) if uid is not None else None
    except RowinoNoSeLee:
        raise _sin_servicio() from None
    if persona is None:
        raise problema(401, "sin_sesion", "Entra a Rowino para jugar.")
    return persona


def dibujante_actual(request: Request) -> Persona:
    """Quien tiene el permiso del dibujante; a cualquier otro, el 404 de una ruta que no existe.

    Sin clave, sin sesión, con la base sin leer o sin el permiso: la respuesta es
    la misma, para que nadie distinga si la ruta existe.
    """
    clave = config.ROWINO_SECRET_KEY
    if not clave or not isinstance(clave, str):
        raise HTTPException(status_code=404)
    uid = leer_cookie(request.cookies.get(COOKIE))
    try:
        persona = buscar_persona(uid) if uid is not None else None
    except RowinoNoSeLee:
        raise HTTPException(status_code=404) from None
    if persona is None or not puede_dibujar(persona.rowino_uid):
        raise HTTPException(status_code=404)
    return persona


def con_cabecera(request: Request) -> None:
    if request.headers.get("X-Gachamon") != "1":
        raise problema(
            403, "sin_cabecera", "Esta petición no viene del juego.",
        )
