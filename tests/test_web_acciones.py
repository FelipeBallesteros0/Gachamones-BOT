import pytest

import db
import economia
import identidad
import simulacion as sim
from ayudas_web import ESCRIBIR, PUEBLO, alta, con_gachamon, poner_reloj

CUIDAR, ACARICIAR = "/gachamon/api/cuidar", "/gachamon/api/acariciar"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)


def cuidar(cliente, accion, evento="evento-0001"):
    return cliente.post(CUIDAR, json={"accion": accion, "evento_id": evento}, headers=ESCRIBIR)


def test_jugar_sube_el_animo_paga_una_moneda_y_devuelve_el_estado(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    antes = cliente.get("/gachamon/api/estado").json()["gachamon"]["barras"]["animo"]
    respuesta = cuidar(cliente, "jugar")
    cuerpo = respuesta.json()
    assert respuesta.status_code == 200 and cuerpo["ok"] is True
    assert cuerpo["monedas"] == 1 and cuerpo["mensaje"]
    assert cuerpo["estado"]["gachamon"]["barras"]["animo"] > antes
    assert cuerpo["estado"]["saldos"]["monedas"] == 51
    assert cuerpo["estado"]["gachamon"]["esperas"]["jugar"] == 29 * 60


def test_el_mismo_evento_repetido_no_premia_ni_aplica_dos_veces(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    primera = cuidar(cliente, "jugar", "evento-doble").json()
    repetida = cuidar(cliente, "jugar", "evento-doble").json()
    assert repetida["ok"] is True and repetida["monedas"] == primera["monedas"] == 1
    assert repetida["estado"]["saldos"]["monedas"] == 51
    assert repetida["estado"]["gachamon"]["barras"] == primera["estado"]["gachamon"]["barras"]
    assert db.criatura_activa(YO, G).xp == sim.XP_POR_CUIDADO[sim.JUGAR]


def test_el_mismo_evento_para_otra_accion_se_rechaza(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    cuidar(cliente, "jugar", "evento-mezcla")
    respuesta = cuidar(cliente, "limpiar", "evento-mezcla")
    assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "evento"


def test_antes_de_tiempo_la_regla_dice_que_no_y_cuanto_falta(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    cuidar(cliente, "jugar", "evento-0001")
    reloj.pasar(minutes=9)
    cuerpo = cuidar(cliente, "jugar", "evento-0002").json()
    assert cuerpo["ok"] is False and cuerpo["monedas"] == 0
    assert cuerpo["espera"] == 20 * 60 and cuerpo["mensaje"]
    assert cuerpo["estado"]["saldos"]["monedas"] == 51


@pytest.mark.parametrize("cuerpo, clave", [
    ({"accion": "bailar", "evento_id": "evento-0001"}, "accion"),
    ({"accion": "competir", "evento_id": "evento-0001"}, "accion"),
    ({"accion": "acariciar", "evento_id": "evento-0001"}, "accion"),
    ({"evento_id": "evento-0001"}, "accion"),
    ({"accion": "jugar"}, "evento"),
    ({"accion": "jugar", "evento_id": "corto"}, "evento"),
    ({"accion": "jugar", "evento_id": "x" * 65}, "evento"),
    ({"accion": "jugar", "evento_id": "con espacios 1"}, "evento"),
    ({"accion": "jugar", "evento_id": "ñandú-00001"}, "evento"),
    ({"accion": "jugar", "evento_id": 12345678}, "evento"),
])
def test_un_pedido_mal_hecho_no_toca_nada(cliente, monkeypatch, cuerpo, clave):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    respuesta = cliente.post(CUIDAR, json=cuerpo, headers=ESCRIBIR)
    assert respuesta.status_code == 422 and respuesta.json()["detail"]["clave"] == clave
    assert economia.saldos(YO, G).asciicoins == 50


def test_sin_gachamon_no_hay_a_quien_cuidar_ni_acariciar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    for respuesta in (cuidar(cliente, "jugar"), cliente.post(ACARICIAR, headers=ESCRIBIR)):
        assert respuesta.status_code == 409
        assert respuesta.json()["detail"]["clave"] == "sin_gachamon"


def test_acariciar_cuenta_una_vez_y_despues_dice_cuanto_falta(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    antes = cliente.get("/gachamon/api/estado").json()["gachamon"]["barras"]["animo"]
    primera = cliente.post(ACARICIAR, headers=ESCRIBIR).json()
    assert primera["ok"] is True and primera["espera"] == 19 * 60
    assert primera["estado"]["gachamon"]["barras"]["animo"] == antes + 5
    reloj.pasar(minutes=4)
    segunda = cliente.post(ACARICIAR, headers=ESCRIBIR).json()
    assert segunda["ok"] is False and segunda["espera"] == 15 * 60
    assert segunda["estado"]["gachamon"]["barras"] == cliente.get("/gachamon/api/estado").json()["gachamon"]["barras"]
    assert segunda["estado"]["saldos"] == {"monedas": 50, "gemas": 50}


def test_nadie_cuida_ni_acaricia_al_gachamon_de_otro(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente, 1)
    mio = db.criatura_activa(YO, G)
    reloj.pasar(hours=6)
    alta(cliente, 2, nombre="Ana")
    assert cuidar(cliente, "jugar").status_code == 409
    assert cliente.post(ACARICIAR, headers=ESCRIBIR).status_code == 409
    intruso = cliente.post(
        CUIDAR, headers=ESCRIBIR,
        json={"accion": "jugar", "evento_id": "evento-0009", "usuario_id": YO,
              "guild_id": G, "criatura_id": mio.id},
    )
    assert intruso.status_code == 409
    assert db.por_id(mio.id).xp == 0 and economia.saldos(YO, G).asciicoins == 50


def test_las_dos_piden_la_cabecera(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    assert cliente.post(CUIDAR, json={"accion": "jugar", "evento_id": "evento-0001"}).status_code == 403
    assert cliente.post(ACARICIAR).status_code == 403
