"""La primera aventura: quien no tiene ningún gachamon gana al primero en «Aventura»."""
from dataclasses import replace

import db
import economia
import especies as esp
import identidad
import nacer
from ayudas_web import AVATAR, ESCRIBIR, PUEBLO, alta, entrar, ir, poner_la_segunda_cama, poner_reloj

AVENTURA, PRIMERA = "/gachamon/api/aventura", "/gachamon/api/aventura/primera"
ESTADO = "/gachamon/api/estado"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)

ANTES = [
    "Sales del pueblo por el sendero. Hoy vas tú solo.",
    "Entre los matorrales, algo se mueve.",
    "No huye. Se queda mirándote.",
]
SIN_CAMA = "Antes pon tu segunda cama en tu departamento: sin cama, nadie se queda contigo."
YA_TIENES = "Ya tienes un gachamon. La primera aventura es sólo la de partida."


def despues(especie):
    return [
        f"Sale de su escondite: es {especie}.",
        "Le tiendes la mano. La huele… y se queda a tu lado.",
        "Desde hoy vive contigo.",
    ]


def lista_para_la_aventura(cliente):
    """Con avatar, la segunda cama puesta y en «Aventura»."""
    alta(cliente)
    poner_la_segunda_cama(cliente)
    assert ir(cliente, "aventura").status_code == 200


def test_sin_la_segunda_cama_no_hay_encuentro(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    ir(cliente, "aventura")
    respuesta = cliente.post(PRIMERA, headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {"clave": "sin_cama", "mensaje": SIN_CAMA}
    assert db.plantel(YO, G) == [] and not db.tiene_gachamones(YO, G)
    assert cliente.get(ESTADO).json()["lugar"]["clave"] == "aventura"


def test_el_encuentro_deja_un_gachamon_y_te_lleva_a_casa(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    lista_para_la_aventura(cliente)
    respuesta = cliente.post(PRIMERA, headers=ESCRIBIR)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"estado", "despues"}
    estado = cuerpo["estado"]
    gachamon = estado["gachamon"]
    assert gachamon["espera_nombre"] is True and gachamon["nombre"] == gachamon["nombre_especie"]
    assert gachamon["especie"] in esp.DEL_HUEVO and gachamon["etapa"] == "bebe"
    assert estado["lugar"]["clave"] == "casa" and estado["guia"] is None
    assert cuerpo["despues"] == despues(gachamon["nombre_especie"])
    # Es el que sale contigo, y la vuelta a casa quedó guardada.
    assert [c.id for c in db.plantel(YO, G)] == [gachamon["id"]]
    assert db.criatura_activa(YO, G).id == gachamon["id"]
    assert cliente.get(ESTADO).json()["lugar"]["clave"] == "casa"


def test_el_segundo_encuentro_se_rechaza(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    lista_para_la_aventura(cliente)
    assert cliente.post(PRIMERA, headers=ESCRIBIR).status_code == 200
    ir(cliente, "aventura")
    respuesta = cliente.post(PRIMERA, headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {"clave": "ya_tienes", "mensaje": YA_TIENES}
    assert len(db.plantel(YO, G)) == 1


ANA_DISCORD = "222222222222222222"


def test_con_la_activa_muerta_y_un_recluta_la_aventura_dice_que_ya_tienes(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    entrar(cliente, 2)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    assert db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, G, reloj.ahora) == "ok"
    assert cliente.put("/gachamon/api/avatar", json=AVATAR, headers=ESCRIBIR).status_code == 200
    viejo = db.crear(ANA_DISCORD, G, "pollito", "Viejo", (10, 10, 10, 10), reloj.ahora)
    recluta = db.crear(ANA_DISCORD, G, "pulpo", "Bruma", (10, 10, 10, 10), reloj.ahora, activa=False)
    reloj.pasar(days=5)
    db.guardar(replace(viejo, hambre=0.0, muerta_en=reloj.ahora, causa_muerte="hambre"))

    # El remiendo de la lectura lo pone de activo: con plantel vivo siempre hay uno.
    assert cliente.get(ESTADO).json()["gachamon"]["nombre"] == "Bruma"
    ir(cliente, "aventura")
    respuesta = cliente.post(PRIMERA, headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {"clave": "ya_tienes", "mensaje": YA_TIENES}
    assert db.por_id(recluta.id).activa and [c.id for c in db.plantel(ANA_DISCORD, G)] == [recluta.id]


def test_fuera_del_lugar_no_hay_aventura(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    poner_la_segunda_cama(cliente)
    for lugar in ("casa", "tienda", "plaza"):
        ir(cliente, lugar)
        for respuesta in (cliente.get(AVENTURA), cliente.post(PRIMERA, headers=ESCRIBIR)):
            assert respuesta.status_code == 409, lugar
            assert respuesta.json()["detail"] == {
                "clave": "no_estas_ahi", "mensaje": "Para eso tienes que estar en la aventura.",
            }
    assert db.plantel(YO, G) == []


def test_sin_avatar_no_hay_aventura(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    entrar(cliente, 1)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    ir(cliente, "aventura")
    respuesta = cliente.post(PRIMERA, headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {"clave": "sin_avatar", "mensaje": "Primero crea tu avatar."}
    assert db.plantel(YO, G) == []


def test_el_encuentro_pide_la_cabecera(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    lista_para_la_aventura(cliente)
    assert cliente.post(PRIMERA).status_code == 403
    assert db.plantel(YO, G) == []


def test_si_la_cuenta_cambio_no_hay_encuentro(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    lista_para_la_aventura(cliente)

    def vinculada(*_, **__):
        raise nacer.YaNoEsSuIdentidad

    monkeypatch.setattr(nacer, "encontrar_al_primero", vinculada)
    respuesta = cliente.post(PRIMERA, headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {
        "clave": "cuenta_cambio", "mensaje": "Tu cuenta cambió mientras tanto. Vuelve a entrar.",
    }


def test_al_encontrarlo_se_pagan_las_medallas_de_la_persona(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    lista_para_la_aventura(cliente)
    rara = esp.ESPECIES["dragoncito"]
    assert rara.rareza == esp.RARA
    monkeypatch.setattr(nacer.esp, "elegir_del_huevo", lambda rng: rara)
    respuesta = cliente.post(PRIMERA, headers=ESCRIBIR)
    assert respuesta.status_code == 200
    # «Uno entre veinticinco»: veinte gemas, ya en el saldo del estado (se parte de cero).
    assert respuesta.json()["estado"]["saldos"] == {"monedas": 0, "gemas": 20}
    assert economia.saldos(YO, G).asciigems == 20
    assert respuesta.json()["despues"][0] == f"Sale de su escondite: es {rara.nombre}."


def test_un_segundo_encuentro_no_vuelve_a_pagar_las_medallas(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    lista_para_la_aventura(cliente)
    monkeypatch.setattr(nacer.esp, "elegir_del_huevo", lambda rng: esp.ESPECIES["dragoncito"])
    assert cliente.post(PRIMERA, headers=ESCRIBIR).status_code == 200
    ir(cliente, "aventura")
    respuesta = cliente.post(PRIMERA, headers=ESCRIBIR)
    assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "ya_tienes"
    assert economia.saldos(YO, G).asciigems == 20
    assert set(db.logros_de_persona(YO, G)) == {"uno_entre_veinticinco"}


def test_si_el_pago_de_las_medallas_fallo_el_reintento_lo_paga(cliente, monkeypatch):
    from fastapi.testclient import TestClient

    poner_reloj(monkeypatch)
    lista_para_la_aventura(cliente)
    monkeypatch.setattr(nacer.esp, "elegir_del_huevo", lambda rng: esp.ESPECIES["dragoncito"])
    pagar = economia.pagar_logros_de_persona

    def falla(*_):
        raise RuntimeError("se cortó")

    monkeypatch.setattr(economia, "pagar_logros_de_persona", falla)
    sin_trampa = TestClient(cliente.app, raise_server_exceptions=False, cookies=cliente.cookies)
    assert sin_trampa.post(PRIMERA, headers=ESCRIBIR).status_code == 500
    assert economia.saldos(YO, G).asciigems == 0 and len(db.plantel(YO, G)) == 1
    # El reintento ya no encuentra a nadie (el gachamon es tuyo), pero las medallas sí se pagan.
    monkeypatch.setattr(economia, "pagar_logros_de_persona", pagar)
    respuesta = cliente.post(PRIMERA, headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {"clave": "ya_tienes", "mensaje": YA_TIENES}
    assert economia.saldos(YO, G).asciigems == 20 and len(db.plantel(YO, G)) == 1
    assert set(db.logros_de_persona(YO, G)) == {"uno_entre_veinticinco"}


def test_si_algo_falla_despues_del_encuentro_el_gachamon_ya_es_tuyo(cliente, monkeypatch):
    from fastapi.testclient import TestClient

    poner_reloj(monkeypatch)
    lista_para_la_aventura(cliente)

    def falla(*_):
        raise RuntimeError("se cortó")

    monkeypatch.setattr(economia, "pagar_logros_de_persona", falla)
    sin_trampa = TestClient(cliente.app, raise_server_exceptions=False, cookies=cliente.cookies)
    assert sin_trampa.post(PRIMERA, headers=ESCRIBIR).status_code == 500
    # Al volver a entrar, su gachamon lo espera para que le ponga nombre.
    gachamon = cliente.get(ESTADO).json()["gachamon"]
    assert gachamon["espera_nombre"] is True and len(db.plantel(YO, G)) == 1


def test_lo_que_dice_el_lugar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    ir(cliente, "aventura")
    assert cliente.get(AVENTURA).json() == {
        "primera": {"puede": False, "motivo": "sin_cama", "antes": ANTES},
    }
    poner_la_segunda_cama(cliente)
    ir(cliente, "aventura")
    assert cliente.get(AVENTURA).json() == {
        "primera": {"puede": True, "motivo": None, "antes": ANTES},
    }
    assert db.plantel(YO, G) == []          # mirar no guarda nada
    cliente.post(PRIMERA, headers=ESCRIBIR)
    ir(cliente, "aventura")
    assert cliente.get(AVENTURA).json() == {
        "primera": {"puede": False, "motivo": "ya_tienes", "antes": []},
    }
