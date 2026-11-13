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


# --- Las medallas de la persona al nacer ----------------------------------------

def test_al_nacer_se_pagan_las_medallas_de_la_persona(cliente, monkeypatch):
    import economia
    import especies as esp
    import nacer

    poner_reloj(monkeypatch)
    alta(cliente)
    rara = esp.ESPECIES["dragoncito"]
    assert rara.rareza == esp.RARA
    monkeypatch.setattr(nacer.esp, "elegir_del_huevo", lambda rng: rara)
    respuesta = cliente.post(HUEVO, headers=ESCRIBIR)
    assert respuesta.status_code == 201
    # «Uno entre veinticinco»: veinte gemas, ya en el saldo del estado.
    assert respuesta.json()["saldos"]["gemas"] == 70
    assert economia.saldos(YO, G).asciigems == 70
    assert set(respuesta.json()) == {
        "ahora", "persona", "avatar", "saldos", "hogar", "gachamon", "difunto", "globos", "lugar",
    }


# --- El huevo cuando hay un recluta sin nombre ---------------------------------

ANA_DISCORD = "222222222222222222"


def test_con_la_activa_muerta_y_un_recluta_sin_nombre_el_huevo_dice_que_hacer(cliente, monkeypatch):
    from ayudas_web import AVATAR

    reloj = poner_reloj(monkeypatch)
    entrar(cliente, 2)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    assert db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, G, reloj.ahora) == "ok"
    assert cliente.put("/gachamon/api/avatar", json=AVATAR, headers=ESCRIBIR).status_code == 200
    db.crear(ANA_DISCORD, G, "pollito", "Viejo", (10, 10, 10, 10), reloj.ahora)
    recluta = db.crear(ANA_DISCORD, G, "pulpo", "", (10, 10, 10, 10), reloj.ahora, activa=False)
    reloj.pasar(days=5)

    assert cliente.get("/gachamon/api/estado").json()["gachamon"] is None
    respuesta = cliente.post(HUEVO, headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {
        "clave": "ya_tienes",
        "mensaje": "Tienes un gachamon esperando nombre en la incubadora. "
                   "Ponle nombre en Discord y vuelve.",
    }
    assert db.por_id(recluta.id).nombre == "" and not db.por_id(recluta.id).activa


def test_con_una_activa_el_segundo_huevo_dice_lo_de_siempre(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    cliente.post(HUEVO, headers=ESCRIBIR)
    respuesta = cliente.post(HUEVO, headers=ESCRIBIR)
    assert respuesta.json()["detail"] == {
        "clave": "ya_tienes",
        "mensaje": "Ya tienes un gachamon. El huevo es sólo el de partida.",
    }


# --- El nombre de la especie no es un nombre ----------------------------------

def test_bautizar_con_el_nombre_de_su_especie_no_vale(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    especie = cliente.post(HUEVO, headers=ESCRIBIR).json()["gachamon"]["nombre_especie"]
    respuesta = cliente.post(BAUTIZAR, json={"nombre": especie.upper()}, headers=ESCRIBIR)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == {
        "clave": "nombre", "mensaje": "Ese es el nombre de su especie. Ponle uno propio.",
    }
    assert cliente.get("/gachamon/api/estado").json()["gachamon"]["espera_nombre"] is True
