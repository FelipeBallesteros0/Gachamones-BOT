from dataclasses import replace

import pytest

import db
import identidad
import retrato
from web import pueblo
from ayudas_web import (
    FUERA_DE_RANGO, OTRA_PERSONA, PUEBLO, CABECERA, STATS, T0, alta, con_gachamon, con_monedas_web, con_plantel,
    en_casa, entrar, ir, poner_reloj,
)

API = "/gachamon/api"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)


def ancho_y_fondo(uid, ancho, fondo):
    cuenta = db.cuenta_web(uid)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("UPDATE departamentos SET ancho = ?, fondo = ? WHERE usuario_id = ? AND guild_id = ?",
                    (ancho, fondo, cuenta.usuario_id, cuenta.guild_id))


def test_tu_departamento_de_partida(cliente):
    alta(cliente); en_casa(cliente)   # quien empieza, antes de ganar a su primero
    d = cliente.get(f"{API}/departamento").json()
    assert (d["ancho"], d["fondo"], d["casillas"], d["comodidad"], d["tope"]) == (3, 3, 9, 82, 100)
    assert (d["camas"], d["gachamones"], d["cabe_otro"], d["ampliar"]) == (1, 0, False, {"ancho": 45, "fondo": 45})
    assert [(p["clave"], p["x"], p["y"], p["casillas"]) for p in d["puestos"]] == [
        ("cama_sencilla", 0, 0, [[0, 0], [1, 0]]), ("puerta", -1, 2, [[-1, 2]])]
    assert [(g["clave"], g["cama"], g["ancho"], g["fondo"]) for g in d["guardados"]] == [("cama_sencilla", True, 2, 1)]
    assert d["saldos"] == {"monedas": 0, "gemas": 0}
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
    alta(cliente); en_casa(cliente)   # con la segunda cama guardada: ganar al primero la pone
    cama = cliente.get(f"{API}/departamento").json()["guardados"][0]["id"]
    poner = lambda **c: cliente.post(f"{API}/departamento/poner", json={"mueble_id": cama, **c}, headers=CABECERA).json()
    assert (poner(x=2, y=2, giro=0)["clave"], poner(x=2, y=2, giro=0)["mensaje"]) == ("no_cabe", "Ahí no cabe.")
    assert poner(x=0, y=0, giro=0)["mensaje"] == "Ahí ya hay algo."
    bien = poner(x=0, y=1, giro=0)
    assert (bien["ok"], bien["mensaje"], bien["departamento"]["camas"], bien["departamento"]["cabe_otro"]) == (True, None, 2, True)
    assert bien["estado"]["saldos"] == {"monedas": 0, "gemas": 0}
    # Llega el primero, a esa cama: ya no cabe otro, y la cama hace falta.
    ir(cliente, "aventura")
    assert cliente.post(f"{API}/aventura/primera", headers=CABECERA).status_code == 200
    d = cliente.get(f"{API}/departamento").json()
    assert (d["camas"], d["gachamones"], d["cabe_otro"]) == (2, 1, False)
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
    poner = cliente.post(f"{API}/departamento/poner", json={"mueble_id": maceta, "x": 2, "y": 0, "giro": 0}, headers=CABECERA).json()
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


@pytest.mark.parametrize("ruta", ["poner", "guardar", "ampliar"])
@pytest.mark.parametrize("cuerpo", [b"null", b"[1, 2]", b"5", b"{roto"], ids=["null", "lista", "numero", "json_roto"])
def test_un_cuerpo_que_no_es_un_objeto_es_un_422_y_no_toca_nada(cliente, ruta, cuerpo):
    con_gachamon(cliente); en_casa(cliente); con_monedas_web(cliente, 100)
    antes = cliente.get(f"{API}/departamento").json()
    r = cliente.post(f"{API}/departamento/{ruta}", content=cuerpo, headers={**CABECERA, "Content-Type": "application/json"})
    assert r.status_code == 422 and r.json()["detail"]["mensaje"].strip()
    assert cliente.get(f"{API}/departamento").json() == antes


def test_una_pieza_que_ya_no_esta_en_el_catalogo_no_se_lista(cliente):
    alta(cliente); en_casa(cliente)   # con su cama guardada: guardados no queda vacío
    cuenta = db.cuenta_web(1)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db._departamento_en(con, cuenta.usuario_id, cuenta.guild_id, db.ahora_utc())
        puesta = db.anadir_mueble_en(con, cuenta.usuario_id, cuenta.guild_id, "ya_no_existe", 2, 2, 0)
        guardada = db.anadir_mueble_en(con, cuenta.usuario_id, cuenta.guild_id, "ya_no_existe")
    d = cliente.get(f"{API}/departamento").json()
    ids = [p["id"] for p in d["puestos"] + d["guardados"]]
    assert puesta not in ids and guardada not in ids
    assert [p["clave"] for p in d["puestos"] + d["guardados"]] == ["cama_sencilla", "puerta", "cama_sencilla"]


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
    alta(cliente, uid=1); en_casa(cliente)
    suya = cliente.get(f"{API}/departamento").json()["puestos"][0]["id"]
    alta(cliente, uid=2, nombre="Brisa"); en_casa(cliente)
    d2 = cliente.get(f"{API}/departamento").json()
    assert suya not in [p["id"] for p in d2["puestos"] + d2["guardados"]]
    for ruta, cuerpo in (("guardar", {"mueble_id": suya}), ("poner", {"mueble_id": suya, "x": 0, "y": 2, "giro": 0})):
        r = cliente.post(f"{API}/departamento/{ruta}", json=cuerpo, headers=CABECERA).json()
        assert (r["ok"], r["mensaje"]) == (False, "Ese mueble no es tuyo.")
    entrar(cliente, 1)
    d1 = cliente.get(f"{API}/departamento").json()
    assert [(p["id"], p["x"], p["y"]) for p in d1["puestos"]] == [(suya, 0, 0), (d1["puestos"][1]["id"], -1, 2)]   # tu cama y tu puerta


def con_otro(cliente):
    """La cuenta con su primer gachamon ya con nombre (Pelusa) y un segundo gachamon, Rulo, que no sale."""
    con_gachamon(cliente)
    return db.crear(YO, G, "pollito", "Rulo", STATS, db.ahora_utc(), activa=False)


def salir(cliente, gachamon_id):
    return cliente.post(f"{API}/departamento/salir", json={"gachamon_id": gachamon_id}, headers=CABECERA)


def test_el_departamento_trae_a_todos_con_sus_barras(cliente):
    otro = con_otro(cliente); en_casa(cliente)                 # Pelusa sale contigo; Rulo, no
    d = cliente.get(f"{API}/departamento").json()
    assert d["gachamones"] == 2
    assert [(g["nombre"], g["activo"]) for g in d["plantel"]] == [("Pelusa", True), ("Rulo", False)]
    assert d["plantel"][1]["id"] == otro.id
    for g in d["plantel"]:
        assert set(g["barras"]) == {"comida", "animo", "aseo"}
        assert set(g["esperas"]) >= {"alimentar", "jugar", "entrenar", "limpiar", "acariciar"}
        assert g["retrato"] and g["nombre_especie"] and g["nombre_etapa"]


def test_el_plantel_del_departamento_ensena_a_cada_uno_con_la_cara_de_ahora_y_mirar_no_guarda(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    otro = con_otro(cliente); en_casa(cliente)                 # Rulo no sale contigo
    pelusa = db.criatura_activa(YO, G)
    reloj.pasar(days=3)
    plantel = cliente.get(f"{API}/departamento").json()["plantel"]
    rulo = next(g for g in plantel if g["id"] == otro.id)
    assert rulo["activo"] is False
    # Su cara es la de ahora (al día con el ritmo de su departamento), no la de su fila.
    cara = db.avanzar(db.por_id(otro.id), reloj.ahora).animo_visual
    assert cara != "feliz"
    assert rulo["retrato"] == f"/gachamon/retrato/pollito/bebe/{cara}/sin.png?v={retrato.version()}"
    # Y mirar no le guarda a nadie el paso del tiempo.
    assert db.por_id(otro.id).actualizada_en == db.por_id(pelusa.id).actualizada_en == T0


def test_cada_mueble_puesto_dice_su_forma(cliente):
    con_gachamon(cliente); en_casa(cliente)
    cama = cliente.get(f"{API}/departamento").json()["puestos"][0]
    assert (cama["ancho"], cama["fondo"], cama["capa"]) == (2, 1, "bulto")


def test_salir_con_otro_desde_el_departamento(cliente):
    otro = con_otro(cliente); en_casa(cliente)
    r = salir(cliente, otro.id).json()
    assert (r["ok"], r["clave"], r["mensaje"]) == (True, None, "Ahora sales con Rulo.")
    assert r["estado"]["gachamon"]["nombre"] == "Rulo"
    assert [(g["nombre"], g["activo"]) for g in r["departamento"]["plantel"]] == [("Rulo", True), ("Pelusa", False)]
    otra_vez = salir(cliente, otro.id).json()                  # con el que ya sale: un sí, como en la Incubadora
    assert (otra_vez["ok"], otra_vez["mensaje"]) == (True, "Rulo ya es tu gachamon activo.")


def test_salir_pide_estar_en_el_departamento_y_un_id_de_verdad(cliente):
    con_gachamon(cliente); ir(cliente, "tienda")
    assert salir(cliente, 1).status_code == 409
    en_casa(cliente)
    for malo in ("1", 1.5, True, None):
        assert salir(cliente, malo).status_code == 422
    ajeno = salir(cliente, 999999).json()
    assert (ajeno["ok"], ajeno["clave"], ajeno["mensaje"]) == (False, "no_esta", "Ese gachamon ya no está.")


def test_salir_con_uno_ajeno_es_no_esta_y_no_cambia_nada(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pelusa, _, _ = con_plantel(cliente)
    ajeno = db.crear(OTRA_PERSONA, G, "pulpo", "Ajeno", STATS, db.ahora_utc())
    en_casa(cliente)
    for gachamon_id in (ajeno.id, 999_999):
        hecho = salir(cliente, gachamon_id)
        assert hecho.status_code == 200
        cuerpo = hecho.json()
        assert (cuerpo["ok"], cuerpo["clave"], cuerpo["mensaje"]) == (False, "no_esta", "Ese gachamon ya no está.")
    assert db.criatura_activa(YO, G).id == pelusa.id
    assert db.criatura_activa(OTRA_PERSONA, G).id == ajeno.id


def test_si_el_activo_ya_estaba_muerto_salir_con_otro_sigue_funcionando(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    viejo = db.crear(YO, G, "pollito", "Viejo", STATS, reloj.ahora)
    db.crear(YO, G, "pulpo", "Nube", STATS, reloj.ahora, activa=False)
    bruma = db.crear(YO, G, "pulpo", "Bruma", STATS, reloj.ahora, activa=False)
    en_casa(cliente)
    reloj.pasar(days=5)
    # Viejo murió cuando todavía se moría de hambre, y nadie sacó todavía al relevo.
    db.guardar(replace(db.por_id(viejo.id), hambre=0.0, muerta_en=reloj.ahora, causa_muerte="hambre"))
    cuerpo = salir(cliente, bruma.id).json()
    assert (cuerpo["ok"], cuerpo["mensaje"]) == (True, "Ahora sales con Bruma.")
    assert cuerpo["estado"]["gachamon"]["id"] == bruma.id
    assert not db.por_id(viejo.id).viva


def test_salir_con_un_id_que_no_es_entero_es_un_422(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pelusa, nube, _ = con_plantel(cliente)
    en_casa(cliente)
    for cuerpo in ({}, {"gachamon_id": str(nube.id)}, {"gachamon_id": None}, {"gachamon_id": True},
                   {"gachamon_id": float(nube.id)}, [nube.id], nube.id):
        hecho = cliente.post(f"{API}/departamento/salir", json=cuerpo, headers=CABECERA)
        assert hecho.status_code == 422, cuerpo
        assert hecho.json()["detail"] == {"clave": "peticion", "mensaje": "La petición no se entiende."}
    assert cliente.post(f"{API}/departamento/salir", json={"gachamon_id": nube.id}).status_code == 403
    assert db.criatura_activa(YO, G).id == pelusa.id


def test_salir_con_un_id_fuera_de_rango_es_un_422_y_no_cambia_nada(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pelusa, nube, recluta = con_plantel(cliente)
    en_casa(cliente)
    antes = [db.por_id(c.id) for c in (pelusa, nube, recluta)]
    for gachamon_id in FUERA_DE_RANGO:
        hecho = salir(cliente, gachamon_id)
        assert hecho.status_code == 422, gachamon_id
        assert hecho.json()["detail"] == {"clave": "peticion", "mensaje": "La petición no se entiende."}
    assert db.criatura_activa(YO, G).id == pelusa.id
    assert [db.por_id(c.id) for c in (pelusa, nube, recluta)] == antes


def test_el_departamento_dice_cual_es_la_puerta(cliente):
    alta(cliente); en_casa(cliente)   # con su cama guardada: guardados no queda vacío
    d = cliente.get(f"{API}/departamento").json()
    assert [(p["clave"], p["x"], p["y"], p["puerta"]) for p in d["puestos"]] == [
        ("cama_sencilla", 0, 0, False), ("puerta", -1, 2, True)]
    assert (d["comodidad"], d["camas"]) == (82, 1)
    assert all(not g.get("puerta") for g in d["guardados"])


def test_el_puesto_de_la_puerta_no_lleva_icono_y_los_demas_si(cliente):
    alta(cliente); en_casa(cliente)   # con su cama guardada: guardados no queda vacío
    d = cliente.get(f"{API}/departamento").json()
    assert [(p["clave"], p["icono"]) for p in d["puestos"]] == [
        ("cama_sencilla", "iconos/muebles/cama_sencilla.png"), ("puerta", None)]
    assert all(g["icono"] for g in d["guardados"])


def test_la_puerta_no_se_guarda_desde_la_pagina(cliente):
    con_gachamon(cliente); en_casa(cliente)
    puerta = next(p for p in cliente.get(f"{API}/departamento").json()["puestos"] if p["puerta"])
    r = cliente.post(f"{API}/departamento/guardar", json={"mueble_id": puerta["id"]}, headers=CABECERA).json()
    assert (r["ok"], r["clave"], r["mensaje"]) == (False, "no_se_guarda", "La puerta no se guarda.")
    assert any(p["puerta"] for p in r["departamento"]["puestos"])


# --- Los muebles que se usan solos -------------------------------------------------

def un_mueble(clave, x=None, y=None, giro=0, uid=1):
    """Le da a esa cuenta un mueble, puesto en (x, y) o guardado, sin pasar por la Tienda."""
    cuenta = db.cuenta_web(uid)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        return db.anadir_mueble_en(con, cuenta.usuario_id, cuenta.guild_id, clave, x, y, giro)


def con_comida(comida, ahora):
    """Le deja esa comida al gachamon que sale contigo, puesta al día en `ahora`."""
    db.guardar(replace(db.criatura_activa(YO, G), hambre=comida, actualizada_en=ahora))


def con_animo(animo, ahora):
    """Le deja ese ánimo al gachamon que sale contigo, puesto al día en `ahora`."""
    db.guardar(replace(db.criatura_activa(YO, G), animo=animo, actualizada_en=ahora))


def test_cada_puesto_dice_si_se_usa_solo_y_para_que(cliente):
    con_gachamon(cliente); en_casa(cliente)                   # sus dos camas, en (0, 0) y en (0, 1)
    ids = {clave: un_mueble(clave, x, y) for clave, x, y in (
        ("refrigerador", 2, 0), ("consola", 2, 1), ("ducha", 2, 2), ("pesas", 1, 2), ("maceta", 0, 2))}
    usos = {p["id"]: p["uso"] for p in cliente.get(f"{API}/departamento").json()["puestos"]}
    assert {clave: usos[i] for clave, i in ids.items()} == {
        "refrigerador": "comida", "consola": "animo", "ducha": "aseo", "pesas": "fuerza", "maceta": None}
    assert [uso for i, uso in usos.items() if i not in ids.values()] == [None, None, None]   # las camas y la puerta


def test_al_poner_el_refrigerador_la_comida_es_40_en_esa_misma_respuesta(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente); en_casa(cliente)
    refrigerador = un_mueble("refrigerador")
    con_comida(10.0, reloj.ahora)
    reloj.pasar(hours=1)
    assert cliente.get(f"{API}/estado").json()["gachamon"]["barras"]["comida"] < 40
    r = cliente.post(f"{API}/departamento/poner", json={"mueble_id": refrigerador, "x": 2, "y": 2, "giro": 0},
                     headers=CABECERA).json()
    assert r["ok"]
    assert [g["barras"]["comida"] for g in r["departamento"]["plantel"]] == [40]
    assert r["estado"]["gachamon"]["barras"]["comida"] == 40


def test_con_el_refrigerador_puesto_entrenar_no_baja_la_comida_de_40(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente); en_casa(cliente)
    un_mueble("refrigerador", 2, 2)
    con_comida(40.0, reloj.ahora)
    r = cliente.post(f"{API}/cuidar", json={"accion": "entrenar", "evento_id": "evento-entrenar"}, headers=CABECERA).json()
    assert r["ok"]
    assert (r["gachamon"]["barras"]["comida"], r["estado"]["gachamon"]["barras"]["comida"]) == (40, 40)


def test_con_la_consola_puesta_entrenar_no_baja_el_animo_de_40(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente); en_casa(cliente)
    un_mueble("consola", 2, 2)
    con_animo(40.0, reloj.ahora)
    r = cliente.post(f"{API}/cuidar", json={"accion": "entrenar", "evento_id": "evento-entrenar"}, headers=CABECERA).json()
    assert r["ok"]
    assert (r["gachamon"]["barras"]["animo"], r["estado"]["gachamon"]["barras"]["animo"]) == (40, 40)
