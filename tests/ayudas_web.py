"""Lo que comparten las pruebas del servicio web."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from itsdangerous import URLSafeSerializer

import config
import db

CLAVE = "clave-de-prueba"
PUEBLO = 777
ESCRIBIR = {"X-Gachamon": "1"}
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
USUARIOS = ((1, "felipe", 0), (2, "ana", 0), (3, "bloqueada", 1))


def galleta(uid, clave: str = CLAVE) -> str:
    """La cookie de sesión tal como la firma Rowino."""
    return URLSafeSerializer(clave, salt="session").dumps({"uid": uid})


def crear_rowino(ruta, usuarios=USUARIOS) -> None:
    con = sqlite3.connect(ruta)
    con.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, "
        "blocked INTEGER NOT NULL DEFAULT 0)"
    )
    con.executemany("INSERT INTO users VALUES (?, ?, ?)", usuarios)
    con.commit()
    con.close()


class Reloj:
    def __init__(self, ahora: datetime) -> None:
        self.ahora = ahora

    def __call__(self) -> datetime:
        return self.ahora

    def pasar(self, **cuanto) -> None:
        self.ahora += timedelta(**cuanto)


def poner_reloj(monkeypatch, ahora: datetime = T0) -> Reloj:
    reloj = Reloj(ahora)
    monkeypatch.setattr(db, "ahora_utc", reloj)
    return reloj


@contextmanager
def servicio(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "juego.db")
    monkeypatch.setattr(config, "ROWINO_SECRET_KEY", CLAVE)
    monkeypatch.setattr(config, "RUTA_ROWINO_BD", tmp_path / "rowino.db")
    monkeypatch.setattr(config, "GUILD_WEB", PUEBLO)
    crear_rowino(tmp_path / "rowino.db")
    from web.app import crear_app

    with TestClient(crear_app()) as cliente:
        yield cliente


def entrar(cliente, uid: int) -> None:
    cliente.cookies.set("session", galleta(uid))


AVATAR = {"nombre": "Feli", "genero": "macho", "piel": "media", "pelo": "corto",
          "color_de_pelo": "castano", "ropa": "poleron"}


def alta(cliente, uid: int = 1, nombre: str = "Feli") -> None:
    """Deja una cuenta con identidad web y avatar, lista para sacar su huevo."""
    entrar(cliente, uid)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    hecho = cliente.put("/gachamon/api/avatar", json={**AVATAR, "nombre": nombre}, headers=ESCRIBIR)
    assert hecho.status_code == 200, hecho.text
