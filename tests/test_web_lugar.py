import pytest

import casas
import db
import economia
import especies as esp
import globos
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


def test_el_estado_trae_las_frases_del_lugar_donde_estas(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    antes = [g for g in cliente.get(ESTADO).json()["globos"] if g["tipo"] == "lugar"]
    en_la_plaza = [g for g in ir(cliente, "plaza").json()["globos"] if g["tipo"] == "lugar"]
    assert antes and en_la_plaza and {g["texto"] for g in antes} != {g["texto"] for g in en_la_plaza}


def test_en_tu_casa_sin_casa_propia_el_gachamon_no_habla_de_la_casa(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    estado = ir(cliente, "casa").json()
    assert estado["lugar"]["aviso"] == "Todavía no tienes casa. Se compran en la tienda."
    assert [g for g in estado["globos"] if g["tipo"] == "lugar"] == []
    assert any(g["tipo"] == "suelta" for g in estado["globos"])
    assert [g for g in cliente.get(ESTADO).json()["globos"] if g["tipo"] == "lugar"] == []


def comprar_una_casa(reloj) -> db.CuentaWeb:
    """La cuenta 1 se compra una casa grande; su gachamon se muda a ella solo."""
    cuenta = db.cuenta_web(1)
    with db.conectar() as con:
        economia._asegurar_monedero(con, cuenta.usuario_id, cuenta.guild_id)
        con.execute(
            "UPDATE monederos SET asciicoins = 9000 WHERE usuario_id = ? AND guild_id = ?",
            (cuenta.usuario_id, cuenta.guild_id),
        )
    assert economia.comprar_casa(cuenta.usuario_id, cuenta.guild_id, casas.CATALOGO["grande"], reloj()).ok
    return cuenta


def con_casa_y_el_gachamon_en_el_refugio(cliente, monkeypatch) -> None:
    """Una cuenta con casa propia cuyo gachamon activo vive en el refugio."""
    reloj = poner_reloj(monkeypatch)
    activo = con_gachamon(cliente)["gachamon"]["id"]
    cuenta = comprar_una_casa(reloj)
    assert economia.mudar_gachamon(cuenta.usuario_id, cuenta.guild_id, activo, None, reloj()).ok


def frases_de_la_casa(gachamon: dict) -> set[str]:
    propias = globos.PROPIAS_DEL_LUGAR.get(gachamon["especie"], {}).get("casa", ())
    return {esp.concordar(f, gachamon["genero"]) for f in (*globos.DEL_LUGAR["casa"], *propias)}


def test_en_tu_casa_con_casa_propia_si_habla_de_ella(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    comprar_una_casa(reloj)
    estado = ir(cliente, "casa").json()
    assert estado["lugar"]["clave"] == "casa"
    assert estado["lugar"]["aviso"] is None
    del_lugar = {g["texto"] for g in estado["globos"] if g["tipo"] == "lugar"}
    assert del_lugar and del_lugar <= frases_de_la_casa(estado["gachamon"])


def test_quien_tiene_casa_esta_en_su_casa_aunque_su_gachamon_viva_en_el_refugio(cliente, monkeypatch):
    con_casa_y_el_gachamon_en_el_refugio(cliente, monkeypatch)
    estado = ir(cliente, "casa").json()
    assert estado["hogar"] == "refugio"
    assert estado["lugar"]["clave"] == "casa"
    assert estado["lugar"]["aviso"] is None
    del_lugar = {g["texto"] for g in estado["globos"] if g["tipo"] == "lugar"}
    assert del_lugar and del_lugar <= frases_de_la_casa(estado["gachamon"])


def test_se_parte_de_donde_vive_el_gachamon(cliente, monkeypatch):
    con_casa_y_el_gachamon_en_el_refugio(cliente, monkeypatch)
    estado = cliente.get(ESTADO).json()
    assert db.lugar_de_cuenta(1) is None
    assert estado["hogar"] == "refugio"
    assert estado["lugar"]["clave"] == "refugio"
    assert estado["lugar"]["aviso"] is None
