import pytest

import db
from web import pueblo
from ayudas_web import CABECERA, con_gachamon, con_monedas_web, en_casa, entrar, ir

API = "/gachamon/api"


def ancho_y_fondo(uid, ancho, fondo):
    cuenta = db.cuenta_web(uid)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("UPDATE departamentos SET ancho = ?, fondo = ? WHERE usuario_id = ? AND guild_id = ?",
                    (ancho, fondo, cuenta.usuario_id, cuenta.guild_id))


def test_tu_departamento_de_partida(cliente):
    con_gachamon(cliente); en_casa(cliente)
    d = cliente.get(f"{API}/departamento").json()
    assert (d["ancho"], d["fondo"], d["casillas"], d["comodidad"], d["tope"]) == (3, 3, 9, 82, 100)
    assert (d["camas"], d["gachamones"], d["cabe_otro"], d["ampliar"]) == (1, 1, False, {"ancho": 45, "fondo": 45})
    assert [(p["clave"], p["x"], p["y"], p["casillas"]) for p in d["puestos"]] == [("cama_sencilla", 0, 0, [[0, 0], [1, 0]])]
    assert [(g["clave"], g["cama"], g["ancho"], g["fondo"]) for g in d["guardados"]] == [("cama_sencilla", True, 2, 1)]
    assert d["saldos"] == {"monedas": 50, "gemas": 50}
    cama = d["puestos"][0]
    assert (cama["nombre"], cama["icono"], cama["giro"], cama["capa"], cama["cama"]) == (
        "Cama sencilla", "iconos/muebles/cama_sencilla.png", 0, "bulto", True)


def test_fuera_de_tu_departamento_no_se_toca(cliente):
    con_gachamon(cliente); ir(cliente, "tienda")
    for metodo, ruta, cuerpo in ((cliente.get, "departamento", None), (cliente.post, "departamento/guardar", {"mueble_id": 1}),
                                 (cliente.post, "departamento/poner", {"mueble_id": 1, "x": 0, "y": 0, "giro": 0}),
                                 (cliente.post, "departamento/ampliar", {"eje": "ancho", "evento_id": "evento-a1"})):
        r = metodo(f"{API}/{ruta}", **({"json": cuerpo, "headers": CABECERA} if cuerpo else {}))
        assert r.status_code == 409 and "Para eso tienes que estar en tu departamento." in r.text
        assert r.json()["detail"]["clave"] == "no_estas_ahi"


def test_sin_haberte_movido_estas_en_tu_departamento(cliente):
    con_gachamon(cliente); con_monedas_web(cliente, 100)  # sin `ir`: nunca se movió
    assert cliente.get(f"{API}/estado").json()["lugar"]["ofrece"] == ["departamento"]
    assert cliente.get(f"{API}/departamento").status_code == 200
    r = cliente.post(f"{API}/departamento/ampliar", json={"eje": "ancho", "evento_id": "evento-sin-moverse"},
                     headers=CABECERA).json()
    assert (r["ok"], r["estado"]["saldos"]["monedas"]) == (True, 55)


def test_un_lugar_guardado_que_ya_no_existe_te_deja_en_tu_departamento(cliente, monkeypatch):
    con_gachamon(cliente); ir(cliente, "plaza")
    monkeypatch.setattr(pueblo, "LUGARES", {c: l for c, l in pueblo.LUGARES.items() if c != "plaza"})
    assert cliente.get(f"{API}/estado").json()["lugar"]["clave"] == "casa"
    assert cliente.get(f"{API}/departamento").status_code == 200


def test_poner_guardar_y_sus_noes(cliente):
    con_gachamon(cliente); en_casa(cliente)
    cama = cliente.get(f"{API}/departamento").json()["guardados"][0]["id"]
    poner = lambda **c: cliente.post(f"{API}/departamento/poner", json={"mueble_id": cama, **c}, headers=CABECERA).json()
    assert (poner(x=2, y=2, giro=0)["clave"], poner(x=2, y=2, giro=0)["mensaje"]) == ("no_cabe", "Ahí no cabe.")
    assert poner(x=0, y=0, giro=0)["mensaje"] == "Ahí ya hay algo."
    bien = poner(x=0, y=1, giro=0)
    assert (bien["ok"], bien["mensaje"], bien["departamento"]["camas"], bien["departamento"]["cabe_otro"]) == (True, None, 2, False)
    assert bien["estado"]["saldos"] == {"monedas": 50, "gemas": 50}
    no = cliente.post(f"{API}/departamento/guardar", json={"mueble_id": cama}, headers=CABECERA).json()
    assert (no["ok"], no["clave"], no["mensaje"]) == (False, "hace_falta", "Esa cama hace falta: sin ella alguien se queda sin dónde dormir.")
    ajeno = cliente.post(f"{API}/departamento/guardar", json={"mueble_id": 9999}, headers=CABECERA).json()
    assert ajeno["mensaje"] == "Ese mueble no es tuyo."
    assert (ajeno["ok"], ajeno["clave"]) == (False, "no_es_tuyo")


def test_guardar_lo_que_sobra_lo_deja_en_guardados_y_repetirlo_no_cambia_nada(cliente):
    con_gachamon(cliente); en_casa(cliente)
    d = cliente.get(f"{API}/departamento").json()
    cuenta = db.cuenta_web(1)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        maceta = db.anadir_mueble_en(con, cuenta.usuario_id, cuenta.guild_id, "maceta")
    poner = cliente.post(f"{API}/departamento/poner", json={"mueble_id": maceta, "x": 0, "y": 1, "giro": 0}, headers=CABECERA).json()
    assert poner["ok"] and [p["id"] for p in poner["departamento"]["puestos"]][-1] == maceta
    for _ in range(2):
        r = cliente.post(f"{API}/departamento/guardar", json={"mueble_id": maceta}, headers=CABECERA).json()
        assert (r["ok"], r["clave"], r["mensaje"]) == (True, None, None)
        assert [p["id"] for p in r["departamento"]["puestos"]] == [p["id"] for p in d["puestos"]]
        assert maceta in [g["id"] for g in r["departamento"]["guardados"]]


@pytest.mark.parametrize("cuerpo", [{"mueble_id": "1", "x": 0, "y": 0, "giro": 0}, {"mueble_id": 1, "x": 0.5, "y": 0, "giro": 0},
                                     {"mueble_id": 1, "x": 0, "y": 0, "giro": 4}, {"mueble_id": True, "x": 0, "y": 0, "giro": 0}, {},
                                     {"mueble_id": 1, "x": 0, "y": 0, "giro": -1}, {"mueble_id": 1, "x": True, "y": 0, "giro": 0},
                                     {"mueble_id": 2 ** 63, "x": 0, "y": 0, "giro": 0}])
def test_lo_que_la_pantalla_nunca_pide_es_un_422(cliente, cuerpo):
    con_gachamon(cliente); en_casa(cliente)
    assert cliente.post(f"{API}/departamento/poner", json=cuerpo, headers=CABECERA).status_code == 422


def test_guardar_sin_un_id_valido_es_un_422_y_sin_cabecera_un_403(cliente):
    con_gachamon(cliente); en_casa(cliente)
    assert cliente.post(f"{API}/departamento/guardar", json={"mueble_id": "1"}, headers=CABECERA).status_code == 422
    assert cliente.post(f"{API}/departamento/guardar", json={"mueble_id": 1}).status_code == 403
    assert cliente.post(f"{API}/departamento/poner", json={}).status_code == 403
    assert cliente.post(f"{API}/departamento/ampliar", json={"eje": "ancho", "evento_id": "evento-a1"}).status_code == 403


def test_ampliar_cobra_una_vez_por_evento(cliente):
    con_gachamon(cliente); en_casa(cliente); con_monedas_web(cliente, 100)
    ampliar = lambda eje, evento: cliente.post(f"{API}/departamento/ampliar", json={"eje": eje, "evento_id": evento}, headers=CABECERA)
    r = ampliar("ancho", "evento-a1").json()
    assert (r["ok"], r["mensaje"], r["estado"]["saldos"]["monedas"]) == (True, "Tu departamento ahora mide 4 × 3.", 55)
    assert ampliar("ancho", "evento-a1").json()["estado"]["saldos"]["monedas"] == 55
    assert ampliar("fondo", "evento-a1").status_code == 409                                  # el mismo evento para otra cosa
    assert ampliar("fondo", "evento-a2").json()["mensaje"] == "Te faltan 5 monedas."
    assert ampliar("arriba", "evento-a3").status_code == 422
    assert ampliar("ancho", "no vale!").status_code == 422


def test_en_8_ya_no_crece(cliente):
    con_gachamon(cliente); en_casa(cliente)
    cliente.get(f"{API}/departamento")
    ancho_y_fondo(1, 8, 3)
    con_monedas_web(cliente, 1000)
    r = cliente.post(f"{API}/departamento/ampliar", json={"eje": "ancho", "evento_id": "evento-a1"}, headers=CABECERA).json()
    assert (r["ok"], r["clave"], r["mensaje"]) == (False, "ya_es_el_maximo", "Por ese lado tu departamento ya no puede crecer.")
    assert r["departamento"]["ampliar"]["ancho"] is None and r["departamento"]["ampliar"]["fondo"] is not None
    assert r["estado"]["saldos"]["monedas"] == 1000


def test_cada_quien_ve_y_toca_solo_lo_suyo(cliente):
    con_gachamon(cliente, uid=1); en_casa(cliente)
    suya = cliente.get(f"{API}/departamento").json()["puestos"][0]["id"]
    con_gachamon(cliente, uid=2, nombre="Brisa"); en_casa(cliente)
    d2 = cliente.get(f"{API}/departamento").json()
    assert suya not in [p["id"] for p in d2["puestos"] + d2["guardados"]]
    for ruta, cuerpo in (("guardar", {"mueble_id": suya}), ("poner", {"mueble_id": suya, "x": 0, "y": 2, "giro": 0})):
        r = cliente.post(f"{API}/departamento/{ruta}", json=cuerpo, headers=CABECERA).json()
        assert (r["ok"], r["mensaje"]) == (False, "Ese mueble no es tuyo.")
    entrar(cliente, 1)
    d1 = cliente.get(f"{API}/departamento").json()
    assert [(p["id"], p["x"], p["y"]) for p in d1["puestos"]] == [(suya, 0, 0)]
