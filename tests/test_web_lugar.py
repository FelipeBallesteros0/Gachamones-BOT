import pytest

import db
import especies as esp
import globos
import identidad
from ayudas_web import ESCRIBIR, PUEBLO, alta, con_gachamon, entrar, poner_reloj
from web import pueblo

API = "/monsteropolis/api"
ESTADO, LUGAR = f"{API}/estado", f"{API}/lugar"


def ir(cliente, lugar):
    return cliente.post(LUGAR, json={"lugar": lugar}, headers=ESCRIBIR)


def test_quien_llega_esta_en_su_casa(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)   # recién llegada: ganar al primero ya la habría llevado a «Aventura» y de vuelta
    lugar = cliente.get(ESTADO).json()["lugar"]
    assert lugar == {
        "clave": "casa", "nombre": "Tu departamento", "abre": "ya", "aviso": None, "ofrece": ["departamento"],
    }
    assert db.lugar_de_cuenta(1) is None


def test_el_estado_no_habla_de_hogar_ni_de_refugio(cliente):
    con_gachamon(cliente)
    estado = cliente.get(f"{API}/estado").json()
    assert "hogar" not in estado and "refugio" not in estado["lugar"]
    assert (estado["lugar"]["clave"], estado["lugar"]["aviso"]) == ("casa", None)


def test_llegar_a_un_lugar_lo_guarda_y_devuelve_el_estado(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    respuesta = ir(cliente, "estadio")
    assert respuesta.status_code == 200
    assert respuesta.json()["lugar"] == {
        "clave": "estadio", "nombre": "Estadio", "abre": "despues", "aviso": "Esto se abre más adelante.",
        "ofrece": [],
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
    ir(cliente, "plaza")                      # un lugar que no es ninguno de los cuerpos
    respuesta = cliente.post(LUGAR, json=cuerpo, headers=ESCRIBIR)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == {"clave": "lugar", "mensaje": "Ese lugar no existe."}
    assert db.lugar_de_cuenta(1) == "plaza"


def test_si_el_lugar_guardado_ya_no_esta_en_el_pueblo_vuelves_a_tu_casa(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    ir(cliente, "plaza")
    sin_plaza = {c: l for c, l in pueblo.LUGARES.items() if c != "plaza"}
    monkeypatch.setattr(pueblo, "LUGARES", sin_plaza)
    assert cliente.get(ESTADO).json()["lugar"]["clave"] == "casa"


@pytest.mark.parametrize("se_fue", ["refugio", "incubadora"])
def test_quien_se_quedo_en_el_refugio_o_la_incubadora_aparece_en_su_departamento(cliente, monkeypatch, se_fue):
    # Como quien estaba parado ahí el día de publicar: la fila sigue diciendo ese lugar, y no hay migración.
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    db.poner_lugar(1, se_fue)
    assert db.lugar_de_cuenta(1) == se_fue
    lugar = cliente.get(ESTADO).json()["lugar"]
    assert (lugar["clave"], lugar["nombre"], lugar["ofrece"]) == ("casa", "Tu departamento", ["departamento"])
    depto = cliente.get(f"{API}/departamento")
    assert depto.status_code == 200, depto.text
    assert [g["nombre"] for g in depto.json()["plantel"]] == ["Pelusa"]


def test_el_lugar_es_de_cada_cuenta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente, 1)
    ir(cliente, "tienda")
    alta(cliente, 2, nombre="Ana")
    assert cliente.get(ESTADO).json()["lugar"]["clave"] == "casa"
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
    assert db.lugar_de_cuenta(1) == "casa" and db.lugar_de_cuenta(2) == "plaza"


def test_el_estado_trae_las_frases_del_lugar_donde_estas(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    antes = [g for g in cliente.get(ESTADO).json()["globos"] if g["tipo"] == "lugar"]
    en_la_plaza = [g for g in ir(cliente, "plaza").json()["globos"] if g["tipo"] == "lugar"]
    assert antes and en_la_plaza and {g["texto"] for g in antes} != {g["texto"] for g in en_la_plaza}


def frases_de_la_casa(gachamon: dict) -> set[str]:
    propias = globos.PROPIAS_DEL_LUGAR.get(gachamon["especie"], {}).get("casa", ())
    return {esp.concordar(f, gachamon["genero"]) for f in (*globos.DEL_LUGAR["casa"], *propias)}


def test_en_tu_casa_el_gachamon_habla_de_ella(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    estado = ir(cliente, "casa").json()
    assert estado["lugar"]["clave"] == "casa"
    assert estado["lugar"]["aviso"] is None
    del_lugar = {g["texto"] for g in estado["globos"] if g["tipo"] == "lugar"}
    assert del_lugar and del_lugar <= frases_de_la_casa(estado["gachamon"])


# --- La Incubadora se fue: con quién sales se elige en tu departamento ----------------

def test_ningun_lugar_lleva_a_la_incubadora_y_sus_rutas_ya_no_existen(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    yo, guild = identidad.de_cuenta_web(1), str(PUEBLO)
    rulo = db.crear(yo, guild, "pulpo", "Rulo", (10, 10, 10, 10), db.ahora_utc(), activa=False)
    for clave in pueblo.LUGARES:
        assert "incubadora" not in ir(cliente, clave).json()["lugar"]["ofrece"], clave
    # Quien la tenía abierta el día de publicar oye lo de siempre, y nada cambia.
    no_existe = {"detail": {"clave": "no_existe", "mensaje": "Eso no existe."}}
    ver = cliente.get(f"{API}/incubadora")
    sacar = cliente.post(f"{API}/incubadora/sacar", json={"gachamon_id": rulo.id}, headers=ESCRIBIR)
    for respuesta in (ver, sacar):
        assert (respuesta.status_code, respuesta.json()) == (404, no_existe)
    assert db.criatura_activa(yo, guild).nombre == "Pelusa"
