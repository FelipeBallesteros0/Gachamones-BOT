from dataclasses import replace

import casas
import cosmeticos
import db
import huerto
import objetos
from ayudas_web import AVATAR, ESCRIBIR, PUEBLO, con_gachamon, entrar, poner_reloj
from web import tienda

TIENDA, LUGAR = "/gachamon/api/tienda", "/gachamon/api/lugar"
LA_DE_DISCORD = "222222222222222222"


def ir(cliente, lugar):
    return cliente.post(LUGAR, json={"lugar": lugar}, headers=ESCRIBIR)


def mia():
    cuenta = db.cuenta_web(1)
    return cuenta.usuario_id, cuenta.guild_id


def con_vinculo(cliente):
    """La cuenta 1 vinculada a un id de Discord sintético, con su gachamon ya nacido."""
    entrar(cliente, 1)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    assert db.canjear_codigo_de_vinculo(codigo, LA_DE_DISCORD, str(PUEBLO), db.ahora_utc()) == "ok"
    assert cliente.put("/gachamon/api/avatar", json=AVATAR, headers=ESCRIBIR).status_code == 200
    assert cliente.post("/gachamon/api/huevo", headers=ESCRIBIR).status_code == 201
    hecho = cliente.post("/gachamon/api/bautizar", json={"nombre": "Pelusa"}, headers=ESCRIBIR)
    assert hecho.status_code == 200


def test_el_catalogo_solo_se_ve_en_la_tienda(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    fuera = cliente.get(TIENDA)
    assert fuera.status_code == 409 and fuera.json()["detail"]["clave"] == "no_estas_ahi"
    assert fuera.json()["detail"]["mensaje"] == "Para eso tienes que estar en la tienda."
    ir(cliente, "tienda")
    assert cliente.get(TIENDA).status_code == 200
    ir(cliente, "plaza")
    assert cliente.get(TIENDA).status_code == 409


def test_el_catalogo_pide_sesion_y_cuenta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    assert cliente.get(TIENDA).status_code == 401


def test_a_quien_no_tiene_discord_no_se_le_vende_lo_que_solo_sirve_alla(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    ir(cliente, "tienda")
    objetos_ = {o["clave"]: o for o in cliente.get(TIENDA).json()["objetos"]}
    assert len(objetos_) == 17
    for clave in ("fuerza_1d4", "velocidad_1d12", "descanso_rapido", "semilla"):
        assert objetos_[clave]["se_vende"] is False and objetos_[clave]["nota"] == "Más adelante."
    assert objetos_["ticket_refugio"]["se_vende"] is False
    assert objetos_["ticket_refugio"]["nota"] == "No lo necesitas: tu estancia en el refugio no tiene plazo."
    for clave in ("pocion_comida", "silbato", "golosinas", "placa"):
        assert objetos_[clave]["se_vende"] is True and objetos_[clave]["nota"] is None


def test_a_quien_tiene_discord_se_le_vende_todo_con_las_notas_donde_tocan(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_vinculo(cliente)
    ir(cliente, "tienda")
    objetos_ = {o["clave"]: o for o in cliente.get(TIENDA).json()["objetos"]}
    assert len(objetos_) == 17 and all(o["se_vende"] for o in objetos_.values())
    for clave in ("fuerza_1d4", "velocidad_1d12", "descanso_rapido"):
        assert objetos_[clave]["nota"] == "Sirve en las competencias, que por ahora se juegan en Discord."
    assert objetos_["semilla"]["nota"] == "Se siembra en el huerto, que por ahora está en Discord."
    assert objetos_["ticket_refugio"]["nota"] is None
    assert objetos_["pocion_comida"]["nota"] is None


def test_cada_objeto_trae_lo_suyo_en_el_orden_del_catalogo(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    usuario, guild = mia()
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(con, usuario, guild, "pocion_comida", 3)
    ir(cliente, "tienda")
    lista = cliente.get(TIENDA).json()["objetos"]
    assert [o["clave"] for o in lista] == [o.clave for o in objetos.a_la_venta()]
    comida = lista[[o["clave"] for o in lista].index("pocion_comida")]
    esperado = objetos.CATALOGO["pocion_comida"]
    assert comida["nombre"] == esperado.nombre and comida["precio"] == esperado.precio
    assert comida["tienes"] == 3 and comida["icono"] == "iconos/objetos/pocion_comida.png"
    assert all(o["tienes"] == 0 for o in lista if o["clave"] != "pocion_comida")


def test_ninguna_descripcion_lleva_marcas_de_discord(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    # Hoy ninguna lleva marcas; se le pone una para que la prueba tenga dientes.
    marcada = replace(objetos.CATALOGO["pocion_comida"], descripcion="Deja la comida a **100**.")
    monkeypatch.setitem(objetos.CATALOGO, "pocion_comida", marcada)
    con_vinculo(cliente)
    ir(cliente, "tienda")
    lista = cliente.get(TIENDA).json()["objetos"]
    assert all(o["descripcion"] and "**" not in o["descripcion"] for o in lista)
    assert next(o for o in lista if o["clave"] == "pocion_comida")["descripcion"] == "Deja la comida a 100."


def test_los_saldos_son_los_de_la_cuenta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    ir(cliente, "tienda")
    assert cliente.get(TIENDA).json()["saldos"] == {"monedas": 50, "gemas": 50}


def test_los_cosmeticos_marcan_lo_que_ya_es_tuyo_puesto_o_no(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    usuario, guild = mia()
    with db.conectar() as con:
        db.guardar_en_el_ropero_en(con, usuario, guild, "corona")
    ir(cliente, "tienda")
    lista = cliente.get(TIENDA).json()["cosmeticos"]
    assert [c["clave"] for c in lista] == list(cosmeticos.CATALOGO) and len(lista) == 12
    corona = next(c for c in lista if c["clave"] == "corona")
    assert corona == {"clave": "corona", "tipo": "sombrero", "nombre": "Corona",
                      "precio": cosmeticos.CATALOGO["corona"].precio,
                      "icono": "iconos/cosmeticos/corona.png", "tuyo": True}
    assert [c["clave"] for c in lista if c["tuyo"]] == ["corona"]


def test_sin_casa_el_catalogo_de_casas_y_muebles_lo_dice(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    ir(cliente, "tienda")
    datos = cliente.get(TIENDA).json()
    assert datos["casas"]["tuyas"] == [] and datos["casas"]["maximo"] == casas.MAXIMO_CASAS
    assert datos["casas"]["puedes_otra"] is True
    assert datos["casas"]["a_la_venta"] == [
        {"clave": c.clave, "nombre": c.nombre, "icono": f"iconos/casas/{c.clave}.png",
         "precio": c.precio, "aforo": c.aforo, "huecos": c.huecos, "bancales": huerto.bancales_de(c.clave)}
        for c in casas.CATALOGO.values()
    ]
    assert datos["muebles"]["tienes_casa"] is False
    assert [m["clave"] for m in datos["muebles"]["lista"]] == list(casas.MUEBLES)
    assert not any(m["tuyo"] for m in datos["muebles"]["lista"])


def test_con_casa_mueble_y_cosmetico_el_catalogo_trae_los_numeros_de_cada_una(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    usuario, guild = mia()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        casa_id = db.anadir_casa_en(con, usuario, guild, "pequena", reloj())
        db.comprar_mueble_en(con, usuario, guild, "felpudo", True, casa_id)
        db.guardar_en_el_ropero_en(con, usuario, guild, "titulo_veloz")
    ir(cliente, "tienda")
    datos = cliente.get(TIENDA).json()
    assert datos["casas"]["tuyas"] == [{
        "id": casa_id, "clave": "pequena", "nombre": "Casa pequeña", "icono": "iconos/casas/pequena.png",
        "aforo": 3, "viven": 0, "muebles": 1, "plantados": 0, "dan": 160,
        "mejoras": [{"clave": "mediana", "nombre": "Casa mediana", "cuesta": 340},
                    {"clave": "grande", "nombre": "Casa grande", "cuesta": 1040}],
    }]
    assert datos["muebles"]["tienes_casa"] is True
    assert [m["clave"] for m in datos["muebles"]["lista"] if m["tuyo"]] == ["felpudo"]
    felpudo = datos["muebles"]["lista"][0]
    assert felpudo == {"clave": "felpudo", "nombre": "Felpudo", "precio": 30, "comodidad": 2,
                       "icono": "iconos/muebles/felpudo.png", "tuyo": True}
    assert [c["clave"] for c in datos["cosmeticos"] if c["tuyo"]] == ["titulo_veloz"]


def test_los_inquilinos_y_los_bancales_plantados_se_cuentan(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    usuario, guild = mia()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        casa_id = db.anadir_casa_en(con, usuario, guild, "mediana", reloj())
        con.execute("UPDATE criaturas SET casa_id = ? WHERE usuario_id = ? AND muerta_en IS NULL",
                    (casa_id, usuario))
        db.plantar_en(con, usuario, guild, casa_id, 2, reloj())
    ir(cliente, "tienda")
    casa = cliente.get(TIENDA).json()["casas"]["tuyas"][0]
    assert casa["viven"] == 1 and casa["plantados"] == 1
    assert casa["mejoras"] == [{"clave": "grande", "nombre": "Casa grande", "cuesta": 1200 - 400}]
    assert casa["dan"] == 400


def test_con_las_tres_casas_ya_no_puedes_otra(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    usuario, guild = mia()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        for _ in range(casas.MAXIMO_CASAS):
            db.anadir_casa_en(con, usuario, guild, "grande", reloj())
    ir(cliente, "tienda")
    datos = cliente.get(TIENDA).json()["casas"]
    assert datos["puedes_otra"] is False and len(datos["tuyas"]) == 3
    assert all(c["mejoras"] == [] for c in datos["tuyas"])


def test_mirar_el_catalogo_no_crea_la_fila_del_hogar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    usuario, guild = mia()
    ir(cliente, "tienda")
    assert cliente.get(TIENDA).status_code == 200
    with db.conectar() as con:
        filas = con.execute(
            "SELECT COUNT(*) FROM hogar WHERE usuario_id = ? AND guild_id = ?", (usuario, guild)
        ).fetchone()[0]
    assert filas == 0


def test_donde_sirve_cada_objeto():
    sirve = {o.clave: tienda.donde_sirve(o) for o in objetos.a_la_venta()}
    assert {c for c, d in sirve.items() if d == "competir"} == {"fuerza_1d4", "velocidad_1d12", "descanso_rapido"} | {
        o.clave for o in objetos.a_la_venta() if o.stat}
    assert {c for c, d in sirve.items() if d == "huerto"} == {"semilla"}
    assert {c for c, d in sirve.items() if d == "refugio"} == {"ticket_refugio"}
    assert sirve["pocion_comida"] is None and sirve["placa"] is None
