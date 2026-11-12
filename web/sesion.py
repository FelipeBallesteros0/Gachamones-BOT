"""Quién está al otro lado: la sesión de Rowino, y nada más.

Rowino firma una cookie con `{"uid": <entero>}`; aquí se verifica y se
comprueba en su base (sólo lectura) que la cuenta existe y no está bloqueada.
Nada se recuerda entre peticiones. Ante cualquier duda, no entra nadie.
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


def problema(estado: int, clave: str, mensaje: str) -> HTTPException:
    """La única forma de contestar un error en todo el servicio."""
    return HTTPException(
        status_code=estado, detail={"clave": clave, "mensaje": mensaje},
    )


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
    """La persona de Rowino con ese id, si existe y no está bloqueada."""
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
        return None
    if fila is None:
        return None
    ident, usuario, bloqueada = fila
    if bloqueada != 0 or type(ident) is not int or not isinstance(usuario, str):
        return None
    return Persona(rowino_uid=ident, usuario=usuario)


def persona_actual(request: Request) -> Persona:
    uid = leer_cookie(request.cookies.get(COOKIE))
    persona = buscar_persona(uid) if uid is not None else None
    if persona is None:
        raise problema(401, "sin_sesion", "Entra a Rowino para jugar.")
    return persona


def con_cabecera(request: Request) -> None:
    if request.headers.get("X-Gachamon") != "1":
        raise problema(
            403, "sin_cabecera", "Esta petición no viene del juego.",
        )
