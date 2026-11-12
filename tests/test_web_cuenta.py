import config
import db
import identidad
from ayudas_web import ESCRIBIR, PUEBLO, T0, entrar, poner_reloj

CUENTA = "/gachamon/api/cuenta"
STATS = (10, 10, 10, 10)
ANA_DISCORD = "222222222222222222"


def test_sin_sesion_no_hay_cuenta(cliente):
    assert cliente.get(CUENTA).status_code == 401
    assert cliente.post(f"{CUENTA}/empezar", headers=ESCRIBIR).status_code == 401


def test_una_cuenta_que_nunca_entro_es_nueva(cliente):
    entrar(cliente, 1)
    assert cliente.get(CUENTA).json() == {
        "usuario": "felipe", "estado": "nueva", "tiene_gachamones": False,
    }


def test_empezar_le_da_una_identidad_web(cliente):
    entrar(cliente, 1)
    respuesta = cliente.post(f"{CUENTA}/empezar", headers=ESCRIBIR)
    assert respuesta.json()["estado"] == "web"
    assert db.cuenta_web(1) == db.CuentaWeb(1, identidad.de_cuenta_web(1), str(PUEBLO), False)
    assert cliente.post(f"{CUENTA}/empezar", headers=ESCRIBIR).json()["estado"] == "web"


def test_empezar_y_pedir_codigo_piden_la_cabecera(cliente):
    entrar(cliente, 1)
    assert cliente.post(f"{CUENTA}/empezar").status_code == 403
    assert cliente.post(f"{CUENTA}/codigo").status_code == 403
    assert db.cuenta_web(1) is None


def test_vincular_de_punta_a_punta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    entrar(cliente, 2)
    pedido = cliente.post(f"{CUENTA}/codigo", headers=ESCRIBIR).json()
    assert pedido["minutos"] == 10 and len(pedido["codigo"]) == 8
    db.crear(ANA_DISCORD, str(PUEBLO), "pollito", "Pelusa", STATS, T0)

    assert db.canjear_codigo_de_vinculo(pedido["codigo"], ANA_DISCORD, str(PUEBLO), T0) == "ok"

    assert cliente.get(CUENTA).json() == {
        "usuario": "ana", "estado": "vinculada", "tiene_gachamones": True,
    }


def test_empezar_no_deshace_un_vinculo(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    entrar(cliente, 2)
    codigo = cliente.post(f"{CUENTA}/codigo", headers=ESCRIBIR).json()["codigo"]
    db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, str(PUEBLO), T0)
    assert cliente.post(f"{CUENTA}/empezar", headers=ESCRIBIR).json()["estado"] == "vinculada"
    assert db.cuenta_web(2).usuario_id == ANA_DISCORD


def test_una_cuenta_vinculada_no_puede_pedir_otro_codigo(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    entrar(cliente, 2)
    codigo = cliente.post(f"{CUENTA}/codigo", headers=ESCRIBIR).json()["codigo"]
    db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, str(PUEBLO), T0)
    respuesta = cliente.post(f"{CUENTA}/codigo", headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["clave"] == "ya_vinculada"


def test_con_gachamones_en_la_web_ya_no_se_puede_vincular(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    entrar(cliente, 1)
    cliente.post(f"{CUENTA}/empezar", headers=ESCRIBIR)
    db.crear(identidad.de_cuenta_web(1), str(PUEBLO), "pollito", "Pelusa", STATS, T0)
    assert cliente.get(CUENTA).json()["tiene_gachamones"] is True
    respuesta = cliente.post(f"{CUENTA}/codigo", headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["clave"] == "con_gachamones"
    assert respuesta.json()["detail"]["mensaje"]


def test_sin_pueblo_configurado_no_se_puede_empezar(cliente, monkeypatch):
    monkeypatch.setattr(config, "GUILD_WEB", 0)
    entrar(cliente, 1)
    for ruta in ("empezar", "codigo"):
        respuesta = cliente.post(f"{CUENTA}/{ruta}", headers=ESCRIBIR)
        assert respuesta.status_code == 503
        assert respuesta.json()["detail"]["clave"] == "sin_pueblo"
    assert db.cuenta_web(1) is None


def test_cada_cuenta_ve_solo_lo_suyo(cliente):
    entrar(cliente, 1)
    cliente.post(f"{CUENTA}/empezar", headers=ESCRIBIR)
    entrar(cliente, 2)
    assert cliente.get(CUENTA).json()["estado"] == "nueva"


def test_si_el_codigo_nuevo_ya_existe_se_saca_otro_y_no_se_pisa_el_ajeno(cliente, monkeypatch):
    import vinculo

    poner_reloj(monkeypatch)
    salen = iter(["AAAAAAAA", "AAAAAAAA", "BBBBBBBB"])
    monkeypatch.setattr(vinculo, "nuevo_codigo", lambda rng=None: next(salen))
    entrar(cliente, 1)
    primero = cliente.post(f"{CUENTA}/codigo", headers=ESCRIBIR).json()["codigo"]
    entrar(cliente, 2)
    segundo = cliente.post(f"{CUENTA}/codigo", headers=ESCRIBIR).json()["codigo"]
    assert (primero, segundo) == ("AAAAAAAA", "BBBBBBBB")
    assert db.canjear_codigo_de_vinculo(primero, "111111111111111111", str(PUEBLO), T0) == "ok"
    assert db.cuenta_web(1).usuario_id == "111111111111111111" and db.cuenta_web(2) is None
