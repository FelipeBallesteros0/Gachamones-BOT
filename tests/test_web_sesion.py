import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from itsdangerous import URLSafeSerializer

import config
from ayudas_web import CLAVE, ESCRIBIR, entrar, galleta
from web import sesion

RUTA = "/gachamon/api/sesion"


def firmar(cuerpo) -> str:
    return URLSafeSerializer(CLAVE, salt="session").dumps(cuerpo)


def test_sin_cookie_no_hay_sesion(cliente):
    respuesta = cliente.get(RUTA)
    assert respuesta.status_code == 401
    assert respuesta.json()["detail"]["clave"] == "sin_sesion"
    assert respuesta.json()["detail"]["mensaje"]


def test_con_la_cookie_de_rowino_se_entra(cliente):
    entrar(cliente, 1)
    assert cliente.get(RUTA).json() == {"usuario": "felipe"}


@pytest.mark.parametrize("valor", [
    "", "basura", galleta(1, clave="otra-clave"), galleta(1)[:-2] + "xx",
    URLSafeSerializer(CLAVE, salt="otra-sal").dumps({"uid": 1}),
])
def test_una_cookie_que_no_firmo_rowino_no_vale(cliente, valor):
    cliente.cookies.set("session", valor)
    assert cliente.get(RUTA).status_code == 401


@pytest.mark.parametrize("cuerpo", [
    {"otro": 1}, {"uid": "1"}, {"uid": None}, {"uid": -1}, {"uid": 0},
    {"uid": True}, {"uid": 1.5}, [1], "1", 1,
])
def test_bien_firmada_pero_sin_un_uid_entero_tampoco(cliente, cuerpo):
    cliente.cookies.set("session", firmar(cuerpo))
    assert cliente.get(RUTA).status_code == 401


def test_una_cuenta_bloqueada_no_entra(cliente):
    entrar(cliente, 3)
    assert cliente.get(RUTA).status_code == 401


def test_una_cuenta_que_ya_no_existe_no_entra(cliente):
    entrar(cliente, 99)
    assert cliente.get(RUTA).status_code == 401


def test_sin_clave_configurada_no_entra_nadie(cliente, monkeypatch):
    monkeypatch.setattr(config, "ROWINO_SECRET_KEY", "")
    entrar(cliente, 1)
    assert cliente.get(RUTA).status_code == 401
    assert sesion.leer_cookie(galleta(1)) is None
    assert sesion.leer_cookie("lo-que-sea") is None
    # Firmada con la clave vacía se verificaría sola: sólo la guarda la frena.
    assert sesion.leer_cookie(galleta(1, clave="")) is None
    cliente.cookies.set("session", galleta(1, clave=""))
    assert cliente.get(RUTA).status_code == 401


def test_si_falta_la_base_de_rowino_no_entra_nadie_y_no_se_crea(cliente, monkeypatch, tmp_path):
    fantasma = tmp_path / "no-existe" / "rowino.db"
    monkeypatch.setattr(config, "RUTA_ROWINO_BD", fantasma)
    entrar(cliente, 1)
    assert cliente.get(RUTA).status_code == 401
    assert not fantasma.exists() and not fantasma.parent.exists()


def test_una_ruta_mal_puesta_en_una_carpeta_que_existe_no_crea_la_base(cliente, monkeypatch, tmp_path):
    fantasma = tmp_path / "no-existe.db"
    monkeypatch.setattr(config, "RUTA_ROWINO_BD", fantasma)
    entrar(cliente, 1)
    assert cliente.get(RUTA).status_code == 401
    assert not fantasma.exists()


def test_la_base_de_rowino_solo_se_lee(cliente, tmp_path):
    antes = (tmp_path / "rowino.db").read_bytes()
    entrar(cliente, 1)
    for _ in range(3):
        cliente.get(RUTA)
    assert (tmp_path / "rowino.db").read_bytes() == antes
    assert sorted(p.name for p in tmp_path.glob("rowino.db*")) == ["rowino.db"]


def test_una_cuenta_bloqueada_despues_deja_de_entrar_en_la_siguiente_peticion(cliente, tmp_path):
    import sqlite3

    entrar(cliente, 1)
    assert cliente.get(RUTA).status_code == 200
    con = sqlite3.connect(tmp_path / "rowino.db")
    con.execute("UPDATE users SET blocked = 1 WHERE id = 1")
    con.commit()
    con.close()
    assert cliente.get(RUTA).status_code == 401


def test_escribir_pide_la_cabecera():
    app = FastAPI()

    @app.post("/x", dependencies=[Depends(sesion.con_cabecera)])
    def x():
        return {"ok": True}

    with TestClient(app) as c:
        sin = c.post("/x")
        assert sin.status_code == 403
        assert sin.json()["detail"]["clave"] == "sin_cabecera"
        assert c.post("/x", headers={"X-Gachamon": "0"}).status_code == 403
        assert c.post("/x", headers=ESCRIBIR).json() == {"ok": True}


def test_una_ruta_con_espacios_y_signos_raros_se_lee(cliente, monkeypatch, tmp_path):
    from ayudas_web import crear_rowino

    carpeta = tmp_path / "mi carpeta ?#%&"
    carpeta.mkdir()
    crear_rowino(carpeta / "rowino 1.db")
    monkeypatch.setattr(config, "RUTA_ROWINO_BD", carpeta / "rowino 1.db")
    entrar(cliente, 2)
    assert cliente.get(RUTA).json() == {"usuario": "ana"}
