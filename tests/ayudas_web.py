"""Lo que comparten las pruebas del servicio web."""
import sqlite3
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from itsdangerous import URLSafeSerializer

import config
import db
import economia
import especies as esp
import identidad
import nacer

CLAVE = "clave-de-prueba"
PUEBLO = 777
ESCRIBIR = {"X-Gachamon": "1"}
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
# Cuándo arranca el servicio de las pruebas, y con él el día del cambio: antes de
# todo reloj de las pruebas (`T0` y lo que sigue), como en producción, donde el
# cambio es anterior a todo primero que se encuentre en la primera aventura.
ARRANQUE = T0 - timedelta(days=1)
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

    with ExitStack() as pila:
        # Sólo el arranque va con `ARRANQUE`; después, el reloj vuelve a ser el que era.
        with pytest.MonkeyPatch.context() as parche:
            parche.setattr(db, "ahora_utc", lambda: ARRANQUE)
            cliente = pila.enter_context(TestClient(crear_app()))
        yield cliente


def entrar(cliente, uid: int) -> None:
    cliente.cookies.set("session", galleta(uid))


AVATAR = {"nombre": "Feli", "genero": "macho", "piel": "media", "pelo": "corto",
          "color_de_pelo": "castano", "ropa": "poleron"}


def alta(cliente, uid: int = 1, nombre: str = "Feli") -> None:
    """Deja una cuenta con identidad web y avatar, todavía sin ningún gachamon."""
    entrar(cliente, uid)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    hecho = cliente.put("/gachamon/api/avatar", json={**AVATAR, "nombre": nombre}, headers=ESCRIBIR)
    assert hecho.status_code == 200, hecho.text


def ganar_el_primero(cliente) -> dict:
    """La primera aventura de la cuenta de la cookie, por las rutas, como la juega
    quien empieza: pone la segunda cama, va a «Aventura» y se encuentra al primero,
    que todavía espera nombre. El encuentro la deja en su casa.

    Devuelve lo que contesta el encuentro (`estado` y `despues`).
    """
    poner_la_segunda_cama(cliente)
    assert ir(cliente, "aventura").status_code == 200
    hecho = cliente.post("/gachamon/api/aventura/primera", headers=ESCRIBIR)
    assert hecho.status_code == 200, hecho.text
    return hecho.json()


def con_gachamon(cliente, uid: int = 1, nombre: str = "Pelusa") -> dict:
    """Una cuenta con avatar y su primer gachamon, ya con nombre. Devuelve el estado.

    Lo gana por las rutas (`ganar_el_primero`) y le pone nombre, así que queda
    en su casa, con sus dos camas puestas y ninguna guardada.

    El primero sale siempre de una especie común: con una rara (una de cada
    veinticinco) pagaría «Uno entre veinticinco» y habría 20 gemas más según la
    suerte.
    """
    alta(cliente, uid)
    comun = esp.ESPECIES["pollito"]
    with pytest.MonkeyPatch.context() as parche:
        parche.setattr(nacer.esp, "elegir_del_huevo", lambda rng: comun)
        ganar_el_primero(cliente)
    hecho = cliente.post("/gachamon/api/bautizar", json={"nombre": nombre}, headers=ESCRIBIR)
    assert hecho.status_code == 200, hecho.text
    return hecho.json()


# Para las rutas que eligen a un gachamon por su id: el dueño de uno ajeno y los
# ids que ni siquiera se pueden buscar (más allá de lo que cabe en SQLite sería un 500).
OTRA_PERSONA = "333333333333333333"
STATS = (10, 10, 10, 10)
FUERA_DE_RANGO = (2**70, 2**63, 0, -1)


def con_plantel(cliente):
    """La cuenta 1 con Pelusa activa, Nube y un recluta que se puso nombre solo, en ese orden."""
    con_gachamon(cliente)
    yo, guild = identidad.de_cuenta_web(1), str(PUEBLO)
    pelusa = db.criatura_activa(yo, guild)
    nube = db.crear(yo, guild, "pulpo", "Nube", STATS, db.ahora_utc(), activa=False)
    recluta = db.crear(yo, guild, "pollito", "Brote", STATS, db.ahora_utc(), activa=False, se_nombro_solo=True)
    return pelusa, nube, recluta


CABECERA = ESCRIBIR
LUGAR = "/gachamon/api/lugar"


def ir(cliente, lugar):
    """Lleva a la cuenta de la cookie a ese lugar y devuelve la respuesta."""
    return cliente.post(LUGAR, json={"lugar": lugar}, headers=ESCRIBIR)


def en_casa(cliente):
    return ir(cliente, "casa")


def poner_la_segunda_cama(cliente) -> None:
    """Pone la cama que el departamento de partida trae guardada, como en «Construir».

    Deja a la cuenta en su casa, que es donde se pone.
    """
    en_casa(cliente)
    depto = cliente.get("/gachamon/api/departamento").json()
    cama = next(g["id"] for g in depto["guardados"] if g["cama"])
    hecho = cliente.post(
        "/gachamon/api/departamento/poner",
        json={"mueble_id": cama, "x": 0, "y": 1, "giro": 0}, headers=ESCRIBIR,
    )
    assert hecho.status_code == 200 and hecho.json()["ok"], hecho.text


def con_monedas_web(cliente, cuantas, uid: int = 1) -> None:
    """Deja el monedero de esa cuenta web con esas monedas (y las gemas como estaban)."""
    cuenta = db.cuenta_web(uid)
    with db.conectar() as con:
        economia._asegurar_monedero(con, cuenta.usuario_id, cuenta.guild_id)
        con.execute(
            "UPDATE monederos SET asciicoins = ? WHERE usuario_id = ? AND guild_id = ?",
            (cuantas, cuenta.usuario_id, cuenta.guild_id),
        )


def con_carta(cliente, contenido: dict, uid: int = 1) -> None:
    """Le escribe en la base la carta del cambio de la vivienda a esa cuenta web."""
    cuenta = db.cuenta_web(uid)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db.guardar_carta_en(
            con, cuenta.usuario_id, cuenta.guild_id, economia.CAMBIO_DE_LA_VIVIENDA,
            contenido, db.ahora_utc(),
        )
