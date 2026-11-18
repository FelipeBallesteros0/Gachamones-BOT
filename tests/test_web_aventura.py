"""La primera aventura: quien no tiene ningún gachamon gana al primero en «Aventura»."""
from dataclasses import replace
from datetime import datetime, timedelta

import db
import economia
import especies as esp
import identidad
import logros as lgr
import nacer
from ayudas_web import (
    AVATAR, ESCRIBIR, PUEBLO, alta, con_gachamon, entrar, ganar_el_primero, ir, poner_la_segunda_cama, poner_reloj,
)

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


def diez_reclutados_sin_cobrar(usuario=YO):
    """Dos medallas de la persona cumplidas y sin anotar (la del primer salvaje y la
    de los diez): diez reclutados en su marcador y ninguna medalla apuntada."""
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db.apuntar_persona_en(con, usuario, G, lgr.RECLUTADOS, 10)


def test_quien_ya_tenia_gachamones_no_cobra_nada_al_pedir_la_primera_aventura(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)                       # su gachamon, ya con nombre
    diez_reclutados_sin_cobrar()
    antes = economia.saldos(YO, G)
    ir(cliente, "aventura")
    respuesta = cliente.post(PRIMERA, headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {"clave": "ya_tienes", "mensaje": YA_TIENES}
    assert economia.saldos(YO, G) == antes and db.logros_de_persona(YO, G) == {}


def test_con_dos_gachamones_aunque_uno_espere_nombre_la_primera_aventura_no_cobra(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    monkeypatch.setattr(nacer.esp, "elegir_del_huevo", lambda rng: esp.ESPECIES["pollito"])
    alta(cliente)
    ganar_el_primero(cliente)                   # el primero, todavía sin nombre
    db.crear(YO, G, "pulpo", "Nube", (10, 10, 10, 10), reloj.ahora, activa=False)
    diez_reclutados_sin_cobrar()
    antes = economia.saldos(YO, G)
    ir(cliente, "aventura")
    respuesta = cliente.post(PRIMERA, headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {"clave": "ya_tienes", "mensaje": YA_TIENES}
    assert economia.saldos(YO, G) == antes and db.logros_de_persona(YO, G) == {}


def de_antes_del_cambio_sin_bautizar(cliente, reloj):
    """Alguien de Discord de antes del cambio que vincula su cuenta web (uid 2): una
    rara que se le murió (su medalla, cumplida y sin cobrar), diez reclutados sin
    cobrar y un único gachamon vivo que nunca bautizó. Se parece al primero de la
    primera aventura (uno solo, sin nombre), pero nació antes del día del cambio."""
    entrar(cliente, 2)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    assert db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, G, reloj.ahora) == "ok"
    assert cliente.put("/gachamon/api/avatar", json=AVATAR, headers=ESCRIBIR).status_code == 200
    with db.conectar() as con:
        marca = datetime.fromisoformat(con.execute(
            "SELECT hecho_en FROM cambios_hechos WHERE clave = ?", (db.CAMBIO_DE_LA_VIVIENDA,)
        ).fetchone()[0])
    antes_del_cambio = marca - timedelta(days=30)
    rara = db.crear(ANA_DISCORD, G, "dragoncito", "Brasa", (10, 10, 10, 10), antes_del_cambio, activa=False)
    db.guardar(replace(rara, muerta_en=antes_del_cambio, causa_muerte="hambre"))
    unico = db.crear(ANA_DISCORD, G, "pollito", esp.ESPECIES["pollito"].nombre, (10, 10, 10, 10), antes_del_cambio)
    diez_reclutados_sin_cobrar(ANA_DISCORD)
    assert [c.id for c in db.plantel(ANA_DISCORD, G)] == [unico.id] and nacer.espera_nombre(unico)


def test_uno_de_antes_del_cambio_sin_bautizar_no_cobra_nada_al_pedir_la_primera_aventura(cliente, monkeypatch):
    """Alguien de Discord de antes del cambio, con un único gachamon vivo que nunca
    bautizó, se parece al reintento (uno solo, sin nombre), pero nació antes del día
    del cambio: no es un primero de la primera aventura y no cobra nada."""
    reloj = poner_reloj(monkeypatch)
    de_antes_del_cambio_sin_bautizar(cliente, reloj)
    antes = economia.saldos(ANA_DISCORD, G)
    ir(cliente, "aventura")
    respuesta = cliente.post(PRIMERA, headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {"clave": "ya_tienes", "mensaje": YA_TIENES}
    assert economia.saldos(ANA_DISCORD, G) == antes and db.logros_de_persona(ANA_DISCORD, G) == {}


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


# --- La medalla del primero, también en el paso del nombre ---------------------------

NOMBRAR = "/gachamon/api/bautizar"


def se_corta_el_pago_tras_el_encuentro(cliente, monkeypatch):
    """La primera aventura con una rara, con el pago de las medallas cortado justo
    después del encuentro: el gachamon ya es tuyo y su medalla está sin pagar. Deja
    `pagar_logros_de_persona` fallando; devuelve el de verdad."""
    from fastapi.testclient import TestClient

    lista_para_la_aventura(cliente)
    monkeypatch.setattr(nacer.esp, "elegir_del_huevo", lambda rng: esp.ESPECIES["dragoncito"])
    pagar = economia.pagar_logros_de_persona

    def falla(*_):
        raise RuntimeError("se cortó")

    monkeypatch.setattr(economia, "pagar_logros_de_persona", falla)
    sin_trampa = TestClient(cliente.app, raise_server_exceptions=False, cookies=cliente.cookies)
    assert sin_trampa.post(PRIMERA, headers=ESCRIBIR).status_code == 500
    assert economia.saldos(YO, G).asciigems == 0 and db.logros_de_persona(YO, G) == {}
    return pagar


def test_si_el_pago_fallo_y_recargas_ponerle_nombre_paga_la_medalla_una_sola_vez(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pagar = se_corta_el_pago_tras_el_encuentro(cliente, monkeypatch)
    monkeypatch.setattr(economia, "pagar_logros_de_persona", pagar)
    # En vez de reintentar, recarga: le toca el paso del nombre, y al ponérselo se paga.
    assert cliente.get(ESTADO).json()["gachamon"]["espera_nombre"] is True
    respuesta = cliente.post(NOMBRAR, json={"nombre": "Brasa"}, headers=ESCRIBIR)
    assert respuesta.status_code == 200
    assert respuesta.json()["gachamon"]["nombre"] == "Brasa"
    assert respuesta.json()["saldos"] == {"monedas": 0, "gemas": 20}       # ya en el estado que contesta
    assert set(db.logros_de_persona(YO, G)) == {"uno_entre_veinticinco"}
    # Una sola vez: ni otro nombre ni otro encuentro la vuelven a pagar.
    assert cliente.post(NOMBRAR, json={"nombre": "Ceniza"}, headers=ESCRIBIR).status_code == 409
    ir(cliente, "aventura")
    assert cliente.post(PRIMERA, headers=ESCRIBIR).status_code == 409
    assert economia.saldos(YO, G) == economia.Saldos(0, 20)


def test_si_el_pago_vuelve_a_fallar_el_nombre_se_pone_igual(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    se_corta_el_pago_tras_el_encuentro(cliente, monkeypatch)       # y sigue fallando
    respuesta = cliente.post(NOMBRAR, json={"nombre": "Brasa"}, headers=ESCRIBIR)
    assert respuesta.status_code == 200
    assert respuesta.json()["gachamon"]["nombre"] == "Brasa" and db.criatura_activa(YO, G).nombre == "Brasa"
    assert economia.saldos(YO, G).asciigems == 0


def test_en_el_recorrido_de_siempre_ponerle_nombre_no_paga_nada_mas(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    lista_para_la_aventura(cliente)
    monkeypatch.setattr(nacer.esp, "elegir_del_huevo", lambda rng: esp.ESPECIES["dragoncito"])
    assert cliente.post(PRIMERA, headers=ESCRIBIR).status_code == 200      # el encuentro ya pagó
    assert economia.saldos(YO, G) == economia.Saldos(0, 20)
    assert cliente.post(NOMBRAR, json={"nombre": "Brasa"}, headers=ESCRIBIR).status_code == 200
    assert economia.saldos(YO, G) == economia.Saldos(0, 20)
    assert set(db.logros_de_persona(YO, G)) == {"uno_entre_veinticinco"}


def test_a_quien_ya_jugaba_ponerle_nombre_a_su_unico_sin_bautizar_no_le_cambia_el_saldo(cliente, monkeypatch):
    """Sus medallas están cumplidas y sin anotar (la rara, la del primer salvaje y la
    de los diez), pero su único gachamon nació antes del día del cambio: no es el
    primero de la primera aventura, y ponerle nombre no le paga nada."""
    reloj = poner_reloj(monkeypatch)
    de_antes_del_cambio_sin_bautizar(cliente, reloj)
    antes = economia.saldos(ANA_DISCORD, G)
    respuesta = cliente.post(NOMBRAR, json={"nombre": "Pipo"}, headers=ESCRIBIR)
    assert respuesta.status_code == 200 and respuesta.json()["gachamon"]["nombre"] == "Pipo"
    assert economia.saldos(ANA_DISCORD, G) == antes and db.logros_de_persona(ANA_DISCORD, G) == {}


def test_con_dos_gachamones_ponerle_nombre_al_que_lo_espera_no_cobra(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    monkeypatch.setattr(nacer.esp, "elegir_del_huevo", lambda rng: esp.ESPECIES["pollito"])
    alta(cliente)
    ganar_el_primero(cliente)                   # el primero, todavía sin nombre
    db.crear(YO, G, "pulpo", "Nube", (10, 10, 10, 10), reloj.ahora, activa=False)
    diez_reclutados_sin_cobrar()
    antes = economia.saldos(YO, G)
    respuesta = cliente.post(NOMBRAR, json={"nombre": "Pipo"}, headers=ESCRIBIR)
    assert respuesta.status_code == 200 and respuesta.json()["gachamon"]["nombre"] == "Pipo"
    assert economia.saldos(YO, G) == antes and db.logros_de_persona(YO, G) == {}


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
