"""Ponerle nombre al primero y a los demás; y que el huevo ya no existe.

El primero se gana en la primera aventura: sus pruebas están en
`test_web_aventura.py`.
"""
from dataclasses import replace

import db
import especies as esp
import identidad
from ayudas_web import (
    ESCRIBIR, FUERA_DE_RANGO, OTRA_PERSONA, PUEBLO, STATS, alta, con_gachamon, con_plantel, ganar_el_primero,
    poner_la_segunda_cama, poner_reloj,
)

ESTADO = "/gachamon/api/estado"
HUEVO, BAUTIZAR = "/gachamon/api/huevo", "/gachamon/api/bautizar"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)


def test_bautizar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    ganar_el_primero(cliente)
    respuesta = cliente.post(BAUTIZAR, json={"nombre": " Pelusa "}, headers=ESCRIBIR)
    assert respuesta.status_code == 200
    assert respuesta.json()["gachamon"]["nombre"] == "Pelusa"
    assert respuesta.json()["gachamon"]["espera_nombre"] is False
    otra = cliente.post(BAUTIZAR, json={"nombre": "Otra"}, headers=ESCRIBIR)
    assert otra.status_code == 409 and otra.json()["detail"]["clave"] == "ya_bautizado"


def test_un_nombre_malo_vuelve_con_su_frase(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    ganar_el_primero(cliente)
    for cuerpo in ({"nombre": "<img src=x>"}, {"nombre": ""}, {}, {"nombre": 7}):
        respuesta = cliente.post(BAUTIZAR, json=cuerpo, headers=ESCRIBIR)
        assert respuesta.status_code == 422, cuerpo
        assert respuesta.json()["detail"]["clave"] == "nombre"
        assert respuesta.json()["detail"]["mensaje"]


def test_un_gachamon_id_que_no_es_entero_es_un_422(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    ganar_el_primero(cliente)
    yo = db.criatura_activa(YO, G).id
    for gachamon_id in (str(yo), None, True, float(yo), [yo]):
        respuesta = cliente.post(BAUTIZAR, json={"nombre": "Pelusa", "gachamon_id": gachamon_id}, headers=ESCRIBIR)
        assert respuesta.status_code == 422, gachamon_id
        assert respuesta.json()["detail"] == {"clave": "peticion", "mensaje": "La petición no se entiende."}
    assert cliente.get("/gachamon/api/estado").json()["gachamon"]["espera_nombre"] is True


def test_sin_gachamon_id_se_bautiza_a_la_activa_como_siempre(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    ganar_el_primero(cliente)
    recluta = db.crear(YO, G, "pulpo", "Brote", (10, 10, 10, 10), db.ahora_utc(), activa=False)
    respuesta = cliente.post(BAUTIZAR, json={"nombre": "Pelusa"}, headers=ESCRIBIR)
    assert respuesta.status_code == 200 and respuesta.json()["gachamon"]["nombre"] == "Pelusa"
    assert db.por_id(recluta.id).nombre == "Brote"


def test_bautizar_sin_gachamon(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    respuesta = cliente.post(BAUTIZAR, json={"nombre": "Pelusa"}, headers=ESCRIBIR)
    assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "sin_gachamon"


def test_bautizar_pide_la_cabecera(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    assert cliente.post(BAUTIZAR, json={"nombre": "Pelusa"}).status_code == 403


def test_un_valueerror_ajeno_no_sale_como_nombre_malo(cliente, monkeypatch):
    import nacer
    from fastapi.testclient import TestClient

    poner_reloj(monkeypatch)
    alta(cliente)
    ganar_el_primero(cliente)

    def falla(*_):
        raise ValueError("texto interno")

    monkeypatch.setattr(nacer, "bautizar", falla)
    sin_trampa = TestClient(cliente.app, raise_server_exceptions=False, cookies=cliente.cookies)
    respuesta = sin_trampa.post(BAUTIZAR, json={"nombre": "Pelusa"}, headers=ESCRIBIR)
    assert respuesta.status_code == 500
    assert "texto interno" not in respuesta.text


# --- La ayuda de las pruebas ----------------------------------------------------

def test_la_ayuda_con_gachamon_nace_siempre_de_una_especie_comun(cliente, monkeypatch):
    import economia
    import especies as esp
    import nacer
    from ayudas_web import con_gachamon

    poner_reloj(monkeypatch)
    # Aunque al sorteo del primero le tocara una rara, la ayuda gana una común:
    # no paga «Uno entre veinticinco» y las gemas no dependen de la suerte.
    rara = esp.ESPECIES["dragoncito"]
    monkeypatch.setattr(nacer.esp, "elegir_del_huevo", lambda rng: rara)
    estado = con_gachamon(cliente)
    assert esp.ESPECIES[estado["gachamon"]["especie"]].rareza == esp.COMUN
    assert estado["gachamon"]["nombre"] == "Pelusa"
    assert estado["saldos"]["gemas"] == economia.saldos(YO, G).asciigems == 0
    # Y al salir de la ayuda, el sorteo vuelve a ser el que era.
    assert nacer.esp.elegir_del_huevo(None) is rara


def test_la_ayuda_con_gachamon_deja_dos_camas_puestas_y_esta_en_casa(cliente, monkeypatch):
    from ayudas_web import con_gachamon

    poner_reloj(monkeypatch)
    estado = con_gachamon(cliente)
    # Lo ganó como quien juega: puso su segunda cama, y el primero duerme en ella.
    depto = db.departamento_leido(YO, G)
    assert depto.camas_puestas == 2
    assert [p.clave for p in depto.guardadas] == []
    assert [(c.id, c.nombre, c.activa) for c in db.plantel(YO, G)] == [(estado["gachamon"]["id"], "Pelusa", True)]
    # De vuelta en su departamento, sin guía (ya tiene gachamon) y con el monedero en cero.
    assert estado["lugar"]["clave"] == "casa" and estado["guia"] is None
    assert cliente.get("/gachamon/api/estado").json()["lugar"]["clave"] == "casa"
    assert estado["saldos"] == {"monedas": 0, "gemas": 0}


# --- El huevo ya no existe -----------------------------------------------------

def test_el_huevo_ya_no_existe(cliente, monkeypatch):
    import nacer

    poner_reloj(monkeypatch)
    alta(cliente)
    poner_la_segunda_cama(cliente)          # aun con cama para uno, el huevo no está
    respuesta = cliente.post(HUEVO, headers=ESCRIBIR)
    nunca_existio = cliente.post("/gachamon/api/nunca-existio", headers=ESCRIBIR)
    assert respuesta.status_code == 404
    assert respuesta.json() == nunca_existio.json() == {
        "detail": {"clave": "no_existe", "mensaje": "Eso no existe."}}
    assert db.plantel(YO, G) == [] and not db.tiene_gachamones(YO, G)
    assert not hasattr(nacer, "romper_el_huevo")


# --- El nombre de la especie no es un nombre ----------------------------------

def test_bautizar_con_el_nombre_de_su_especie_no_vale(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    especie = ganar_el_primero(cliente)["estado"]["gachamon"]["nombre_especie"]
    respuesta = cliente.post(BAUTIZAR, json={"nombre": especie.upper()}, headers=ESCRIBIR)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == {
        "clave": "nombre", "mensaje": "Ese es el nombre de su especie. Ponle uno propio.",
    }
    assert cliente.get("/gachamon/api/estado").json()["gachamon"]["espera_nombre"] is True


# --- Ponerle nombre a un recluta por su id (la regla se queda en el servidor, sin pantalla) ---

def bautizar_a(cliente, gachamon_id, nombre):
    return cliente.post(BAUTIZAR, json={"nombre": nombre, "gachamon_id": gachamon_id}, headers=ESCRIBIR)


def test_bautizar_a_un_recluta_por_su_id(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pelusa, _, recluta = con_plantel(cliente)
    especie = esp.ESPECIES["pollito"].nombre
    hecho = bautizar_a(cliente, recluta.id, especie.upper())
    assert hecho.status_code == 422
    assert hecho.json()["detail"] == {"clave": "nombre", "mensaje": "Ese es el nombre de su especie. Ponle uno propio."}
    assert db.por_id(recluta.id).nombre == "Brote"

    hecho = bautizar_a(cliente, recluta.id, " Bruma ")
    assert hecho.status_code == 200
    assert db.por_id(recluta.id).nombre == "Bruma" and not db.por_id(recluta.id).activa
    assert hecho.json()["gachamon"]["id"] == pelusa.id and db.criatura_activa(YO, G).id == pelusa.id

    hecho = bautizar_a(cliente, recluta.id, "Otra")
    assert hecho.status_code == 409
    assert hecho.json()["detail"] == {"clave": "ya_bautizado", "mensaje": "Ese gachamon ya tiene nombre."}

    ajeno = db.crear(OTRA_PERSONA, G, "pulpo", "Mote", STATS, db.ahora_utc(), activa=False, se_nombro_solo=True)
    hecho = bautizar_a(cliente, ajeno.id, "Mío")
    assert hecho.status_code == 409
    assert hecho.json()["detail"] == {"clave": "no_esta", "mensaje": "Ese gachamon ya no está."}
    assert db.por_id(ajeno.id).nombre == "Mote" and db.por_id(recluta.id).nombre == "Bruma"


def test_bautizar_con_un_id_fuera_de_rango_es_un_422_y_no_cambia_nada(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pelusa, nube, recluta = con_plantel(cliente)
    antes = [db.por_id(c.id) for c in (pelusa, nube, recluta)]
    for gachamon_id in FUERA_DE_RANGO:
        hecho = bautizar_a(cliente, gachamon_id, "Bruma")
        assert hecho.status_code == 422, gachamon_id
        assert hecho.json()["detail"] == {"clave": "peticion", "mensaje": "La petición no se entiende."}
    assert db.criatura_activa(YO, G).id == pelusa.id and db.por_id(recluta.id).nombre == "Brote"
    assert [db.por_id(c.id) for c in (pelusa, nube, recluta)] == antes


def test_si_solo_queda_un_recluta_el_remiendo_lo_pone_de_activo(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    viejo = db.crear(YO, G, "pollito", "Viejo", STATS, reloj.ahora)
    recluta = db.crear(YO, G, "pulpo", "Brote", STATS, reloj.ahora, activa=False, se_nombro_solo=True)
    reloj.pasar(days=5)
    # Viejo murió cuando todavía se moría de hambre, y nadie lo relevó.
    db.guardar(replace(db.por_id(viejo.id), hambre=0.0, muerta_en=reloj.ahora, causa_muerte="hambre"))

    estado = cliente.get(ESTADO).json()
    assert estado["gachamon"]["id"] == recluta.id and estado["gachamon"]["nombre"] == "Brote"
    assert "sin_nombre" not in estado
    assert db.criatura_activa(YO, G).id == recluta.id
