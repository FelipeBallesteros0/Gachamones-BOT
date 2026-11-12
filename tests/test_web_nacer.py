import db
import identidad
from ayudas_web import ESCRIBIR, PUEBLO, alta, entrar, poner_reloj

HUEVO, BAUTIZAR = "/gachamon/api/huevo", "/gachamon/api/bautizar"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)


def test_sin_avatar_no_hay_huevo(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    entrar(cliente, 1)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    respuesta = cliente.post(HUEVO, headers=ESCRIBIR)
    assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "sin_avatar"
    assert db.plantel(YO, G) == []


def test_romper_el_huevo_devuelve_el_estado_con_el_recien_nacido(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    respuesta = cliente.post(HUEVO, headers=ESCRIBIR)
    assert respuesta.status_code == 201
    gachamon = respuesta.json()["gachamon"]
    assert gachamon["espera_nombre"] is True and gachamon["nombre"] == gachamon["nombre_especie"]
    assert gachamon["etapa"] == "bebe"


def test_el_segundo_huevo_se_rechaza(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    cliente.post(HUEVO, headers=ESCRIBIR)
    respuesta = cliente.post(HUEVO, headers=ESCRIBIR)
    assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "ya_tienes"


def test_bautizar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    cliente.post(HUEVO, headers=ESCRIBIR)
    respuesta = cliente.post(BAUTIZAR, json={"nombre": " Pelusa "}, headers=ESCRIBIR)
    assert respuesta.status_code == 200
    assert respuesta.json()["gachamon"]["nombre"] == "Pelusa"
    assert respuesta.json()["gachamon"]["espera_nombre"] is False
    otra = cliente.post(BAUTIZAR, json={"nombre": "Otra"}, headers=ESCRIBIR)
    assert otra.status_code == 409 and otra.json()["detail"]["clave"] == "ya_bautizado"


def test_un_nombre_malo_vuelve_con_su_frase(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    cliente.post(HUEVO, headers=ESCRIBIR)
    for cuerpo in ({"nombre": "<img src=x>"}, {"nombre": ""}, {}, {"nombre": 7}):
        respuesta = cliente.post(BAUTIZAR, json=cuerpo, headers=ESCRIBIR)
        assert respuesta.status_code == 422, cuerpo
        assert respuesta.json()["detail"]["clave"] == "nombre"
        assert respuesta.json()["detail"]["mensaje"]


def test_bautizar_sin_gachamon(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    respuesta = cliente.post(BAUTIZAR, json={"nombre": "Pelusa"}, headers=ESCRIBIR)
    assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "sin_gachamon"


def test_las_dos_piden_la_cabecera(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    assert cliente.post(HUEVO).status_code == 403
    assert cliente.post(BAUTIZAR, json={"nombre": "Pelusa"}).status_code == 403


def test_un_valueerror_ajeno_no_sale_como_nombre_malo(cliente, monkeypatch):
    import nacer
    from fastapi.testclient import TestClient

    poner_reloj(monkeypatch)
    alta(cliente)
    cliente.post(HUEVO, headers=ESCRIBIR)

    def falla(*_):
        raise ValueError("texto interno")

    monkeypatch.setattr(nacer, "bautizar", falla)
    sin_trampa = TestClient(cliente.app, raise_server_exceptions=False, cookies=cliente.cookies)
    respuesta = sin_trampa.post(BAUTIZAR, json={"nombre": "Pelusa"}, headers=ESCRIBIR)
    assert respuesta.status_code == 500
    assert "texto interno" not in respuesta.text


def test_cuenta_cambio_por_la_ruta(cliente, monkeypatch):
    import nacer

    poner_reloj(monkeypatch)
    alta(cliente)

    def vinculada(*_, **__):
        raise nacer.YaNoEsSuIdentidad

    monkeypatch.setattr(nacer, "romper_el_huevo", vinculada)
    respuesta = cliente.post(HUEVO, headers=ESCRIBIR)
    assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "cuenta_cambio"
