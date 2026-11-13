import pytest

import db
from ayudas_web import ESCRIBIR, alta, con_gachamon, entrar, poner_reloj
from web import pueblo

ESTADO, LUGAR = "/gachamon/api/estado", "/gachamon/api/lugar"


def ir(cliente, lugar):
    return cliente.post(LUGAR, json={"lugar": lugar}, headers=ESCRIBIR)


def test_quien_llega_esta_en_su_hogar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    assert cliente.get(ESTADO).json()["lugar"] == {
        "clave": "refugio", "nombre": "Refugio", "abre": "ya", "aviso": None,
    }
    assert db.lugar_de_cuenta(1) is None


def test_llegar_a_un_lugar_lo_guarda_y_devuelve_el_estado(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    respuesta = ir(cliente, "estadio")
    assert respuesta.status_code == 200
    assert respuesta.json()["lugar"] == {
        "clave": "estadio", "nombre": "Estadio", "abre": "despues", "aviso": "Esto se abre más adelante.",
    }
    assert respuesta.json()["gachamon"]["nombre"] == "Pelusa"
    assert cliente.get(ESTADO).json()["lugar"]["clave"] == "estadio"
    assert db.lugar_de_cuenta(1) == "estadio"


@pytest.mark.parametrize("cuerpo", [
    {"lugar": "portal"}, {"lugar": "u1"}, {"lugar": ""}, {"lugar": 7}, {"lugar": ["casa"]}, {}, [], "casa",
])
def test_un_lugar_que_no_existe_no_se_guarda(cliente, monkeypatch, cuerpo):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    respuesta = cliente.post(LUGAR, json=cuerpo, headers=ESCRIBIR)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == {"clave": "lugar", "mensaje": "Ese lugar no existe."}
    assert db.lugar_de_cuenta(1) is None


def test_si_el_lugar_guardado_ya_no_esta_en_el_pueblo_vuelves_a_tu_hogar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    ir(cliente, "plaza")
    sin_plaza = {c: l for c, l in pueblo.LUGARES.items() if c != "plaza"}
    monkeypatch.setattr(pueblo, "LUGARES", sin_plaza)
    assert cliente.get(ESTADO).json()["lugar"]["clave"] == "refugio"


def test_el_lugar_es_de_cada_cuenta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente, 1)
    ir(cliente, "tienda")
    alta(cliente, 2, nombre="Ana")
    assert cliente.get(ESTADO).json()["lugar"]["clave"] == "refugio"
    assert db.lugar_de_cuenta(1) == "tienda" and db.lugar_de_cuenta(2) is None


def test_pide_la_cabecera_la_sesion_y_la_cuenta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    assert ir(cliente, "plaza").status_code == 401
    entrar(cliente, 1)
    respuesta = ir(cliente, "plaza")
    assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "sin_cuenta"
    alta(cliente)
    assert cliente.post(LUGAR, json={"lugar": "plaza"}).status_code == 403


def test_el_cuerpo_no_puede_decir_de_quien_es_el_lugar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente, 1)
    alta(cliente, 2, nombre="Ana")
    cliente.post(LUGAR, headers=ESCRIBIR, json={"lugar": "plaza", "rowino_uid": 1, "usuario_id": "-1"})
    assert db.lugar_de_cuenta(1) is None and db.lugar_de_cuenta(2) == "plaza"
