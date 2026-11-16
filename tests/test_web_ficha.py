from dataclasses import replace
from datetime import timedelta

import db
import economia
import identidad
import logros
import personalidad as per
import simulacion as sim
from ayudas_web import PUEBLO, T0, con_gachamon, entrar, poner_reloj

FICHA = "/gachamon/api/ficha"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)
STATS = (10, 10, 10, 10)


def activa():
    return db.criatura_activa(YO, G)


def con_efecto(stat, bonus, hasta):
    with db.conectar() as con:
        con.execute(
            "INSERT INTO efectos (criatura_id, stat, bonus, hasta) VALUES (?, ?, ?, ?)",
            (activa().id, stat, bonus, hasta.isoformat()),
        )


def test_las_cuatro_estadisticas_en_orden(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    estadisticas = cliente.get(FICHA).json()["detalle"]["estadisticas"]
    assert [e["clave"] for e in estadisticas] == ["fuerza", "velocidad", "salud", "ingenio"]
    assert [e["nombre"] for e in estadisticas] == ["Fuerza", "Velocidad", "Salud", "Ingenio"]
    criatura = activa()
    assert [e["valor"] for e in estadisticas] == [getattr(criatura, s) for s in sim.ESTADISTICAS]


def test_un_efecto_en_curso_sale_con_lo_que_le_queda(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    con_efecto("fuerza", 3, reloj.ahora + timedelta(minutes=4))
    con_efecto("salud", 2, reloj.ahora - timedelta(seconds=1))
    por_clave = {e["clave"]: e for e in cliente.get(FICHA).json()["detalle"]["estadisticas"]}
    assert por_clave["fuerza"]["efecto"] == {"bonus": 3, "segundos": 240}
    assert por_clave["salud"]["efecto"] is None
    assert por_clave["velocidad"]["efecto"] is None and por_clave["ingenio"]["efecto"] is None


def test_los_segundos_del_efecto_se_redondean_hacia_arriba(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    con_efecto("fuerza", 3, reloj.ahora + timedelta(seconds=10, milliseconds=1))
    por_clave = {e["clave"]: e for e in cliente.get(FICHA).json()["detalle"]["estadisticas"]}
    assert por_clave["fuerza"]["efecto"]["segundos"] == 11


def test_la_experiencia_y_el_caracter(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    with db.conectar() as con:
        con.execute("UPDATE criaturas SET xp = 40, nivel = 2 WHERE usuario_id = ?", (YO,))
    detalle = cliente.get(FICHA).json()["detalle"]
    assert detalle["experiencia"] == {"nivel": 2, "xp": 40, "para_subir": sim.xp_para_subir(2)}
    assert detalle["caracter"] == per.nombre_caracter(activa())


def test_el_sombrero_puesto(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    assert cliente.get(FICHA).json()["detalle"]["sombrero"] is None
    with db.conectar() as con:
        con.execute("UPDATE criaturas SET sombrero = 'corona' WHERE usuario_id = ?", (YO,))
    assert cliente.get(FICHA).json()["detalle"]["sombrero"] == "Corona"


def test_la_ficha_lleva_al_gachamon_y_los_saldos(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    estado = con_gachamon(cliente)
    cuerpo = cliente.get(FICHA).json()
    assert cuerpo["gachamon"] == estado["gachamon"]
    assert cuerpo["saldos"] == estado["saldos"]


def test_las_medallas_con_su_progreso(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    db.apuntar(activa().id, logros.CUIDADOS, 100)
    economia.pagar_logros(activa(), reloj.ahora)
    medallas = cliente.get(FICHA).json()["medallas"]
    assert len(medallas["del_gachamon"]) == len(logros.del_gachamon())
    assert len(medallas["tuyas"]) == len(logros.de_la_persona())
    por_clave = {m["clave"]: m for m in medallas["del_gachamon"]}
    assert por_clave["consentido"]["tiene"] is True and por_clave["consentido"]["progreso"] is None
    assert por_clave["malcriado"]["tiene"] is False
    assert por_clave["malcriado"]["progreso"] == {"hecho": 100, "meta": 500}
    assert por_clave["malcriado"]["nombre"] == "Malcriado"
    assert por_clave["malcriado"]["como"] == "recibe 500 cuidados"
    assert por_clave["malcriado"]["gemas"] == 30
    assert por_clave["primera_sangre"]["progreso"] is None
    assert [m["clave"] for m in medallas["del_gachamon"]] == [l.clave for l in logros.del_gachamon()]
    assert [m["clave"] for m in medallas["tuyas"]] == [l.clave for l in logros.de_la_persona()]


def test_el_progreso_no_pasa_de_la_meta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    db.apuntar(activa().id, logros.CUIDADOS, 900)
    por_clave = {m["clave"]: m for m in cliente.get(FICHA).json()["medallas"]["del_gachamon"]}
    assert por_clave["malcriado"]["progreso"] == {"hecho": 500, "meta": 500}


def test_mirar_la_ficha_no_escribe(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET nacida_en = ? WHERE usuario_id = ?",
            ((T0 - timedelta(days=31)).isoformat(), YO),
        )
    gemas = economia.saldos(YO, G).asciigems
    cuerpo = cliente.get(FICHA).json()
    veterano = {m["clave"]: m for m in cuerpo["medallas"]["del_gachamon"]}["veterano"]
    assert veterano["tiene"] is False and veterano["progreso"] == {"hecho": 30, "meta": 30}
    assert economia.saldos(YO, G).asciigems == gemas == cuerpo["saldos"]["gemas"]
    assert db.logros_de(activa().id) == {}


def test_sin_gachamon_es_un_409(cliente):
    entrar(cliente, 1)
    cliente.post("/gachamon/api/cuenta/empezar", headers={"X-Gachamon": "1"})
    respuesta = cliente.get(FICHA)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {"clave": "sin_gachamon", "mensaje": "No tienes un gachamon."}


def test_sin_sesion_es_un_401(cliente):
    assert cliente.get(FICHA).status_code == 401


def con_otro(cliente):
    """La cuenta con su huevo bautizado y un segundo gachamon, Rulo, que no sale."""
    con_gachamon(cliente)
    return db.crear(YO, G, "pollito", "Rulo", STATS, db.ahora_utc(), activa=False)


def test_la_ficha_de_uno_que_no_sale_contigo(cliente, monkeypatch):
    poner_reloj(monkeypatch); otro = con_otro(cliente)
    suya = cliente.get(FICHA, params={"gachamon_id": otro.id}).json()
    assert (suya["gachamon"]["nombre"], suya["es_el_activo"]) == ("Rulo", False) and "estadisticas" in suya["detalle"]
    assert cliente.get(FICHA).json()["es_el_activo"] is True
    sin = cliente.get(FICHA, params={"gachamon_id": 999999})
    assert sin.status_code == 409 and sin.json()["detail"]["clave"] == "no_esta"
    assert sin.json()["detail"]["mensaje"] == "Ese gachamon ya no está."
    for malo in ("x", "1.5", "true", "0", "-1", str(2**70), "9" * 5000):
        assert cliente.get(FICHA, params={"gachamon_id": malo}).status_code == 422


def test_la_ficha_de_uno_es_la_de_ese_gachamon_y_no_la_del_activo(cliente, monkeypatch):
    poner_reloj(monkeypatch); otro = con_otro(cliente)
    db.guardar(replace(db.por_id(otro.id), nivel=3, xp=7))
    suya = cliente.get(FICHA, params={"gachamon_id": otro.id}).json()
    assert suya["detalle"]["experiencia"]["nivel"] == 3 and suya["detalle"]["experiencia"]["xp"] == 7
    assert suya["detalle"]["estadisticas"][0]["valor"] == otro.fuerza
    assert cliente.get(FICHA).json()["detalle"]["experiencia"]["nivel"] != 3


def test_la_ficha_del_gachamon_de_otra_persona_no_se_ve(cliente, monkeypatch):
    poner_reloj(monkeypatch); con_gachamon(cliente)
    ajeno = db.crear(identidad.de_cuenta_web(2), G, "pollito", "Ajeno", STATS, db.ahora_utc())
    r = cliente.get(FICHA, params={"gachamon_id": ajeno.id})
    assert r.status_code == 409 and r.json()["detail"]["clave"] == "no_esta"
