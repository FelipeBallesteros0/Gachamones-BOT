from dataclasses import replace

import pytest

import casas
import cosmeticos
import db
import economia
import especies as esp
import huerto
import identidad
import nacer
import objetos
from ayudas_web import AVATAR, ESCRIBIR, PUEBLO, alta, con_gachamon, entrar, poner_reloj
from web import tienda

TIENDA, LUGAR = "/gachamon/api/tienda", "/gachamon/api/lugar"
COMPRAR, CASA = f"{TIENDA}/comprar", f"{TIENDA}/casa"
LA_DE_DISCORD = "222222222222222222"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)


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


# Hoy coinciden quien no tiene Discord y quien no tiene plazo en el refugio; el
# día que no, lo del refugio lo decide `identidad.sin_plazo_de_refugio`.

def test_el_ticket_se_le_vende_a_quien_tiene_plazo_aunque_no_tenga_discord(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    ir(cliente, "tienda")
    monkeypatch.setattr(identidad, "sin_plazo_de_refugio", lambda usuario_id: False)
    objetos_ = {o["clave"]: o for o in cliente.get(TIENDA).json()["objetos"]}
    assert objetos_["ticket_refugio"]["se_vende"] is True and objetos_["ticket_refugio"]["nota"] is None
    assert objetos_["semilla"]["se_vende"] is False and objetos_["semilla"]["nota"] == "Más adelante."


def test_el_ticket_no_se_le_vende_a_quien_no_tiene_plazo_aunque_tenga_discord(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_vinculo(cliente)
    ir(cliente, "tienda")
    monkeypatch.setattr(identidad, "sin_plazo_de_refugio", lambda usuario_id: True)
    objetos_ = {o["clave"]: o for o in cliente.get(TIENDA).json()["objetos"]}
    assert objetos_["ticket_refugio"]["se_vende"] is False
    assert objetos_["ticket_refugio"]["nota"] == "No lo necesitas: tu estancia en el refugio no tiene plazo."
    assert objetos_["semilla"]["se_vende"] is True


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
    # El huevo da una especie común: con una rara (una de cada veinticinco)
    # nacer pagaría «Uno entre veinticinco» y habría 20 gemas más.
    comun = esp.ESPECIES["pollito"]
    assert comun.rareza == esp.COMUN
    monkeypatch.setattr(nacer.esp, "elegir_del_huevo", lambda rng: comun)
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


# --- Comprar -------------------------------------------------------------------

def dar(monedas=0, gemas=0, usuario=YO):
    """Deja el monedero con esos saldos, escribiendo en la base como lo haría la otra cara."""
    with db.conectar() as con:
        economia._asegurar_monedero(con, usuario, G)
        con.execute(
            "UPDATE monederos SET asciicoins = ?, asciigems = ? WHERE usuario_id = ? AND guild_id = ?",
            (monedas, gemas, usuario, G),
        )


def en_la_tienda_con(cliente, monkeypatch, monedas=0, gemas=0):
    """La cuenta 1, sólo de la web, con su gachamon, parada en la tienda y con esos saldos."""
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    ir(cliente, "tienda")
    dar(monedas, gemas)
    return reloj


def una_casa(reloj, clave="pequena", usuario=YO):
    """Una casa propia puesta directamente en la base; devuelve su id."""
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        return db.anadir_casa_en(con, usuario, G, clave, reloj())


def casa(cliente, accion, evento, **resto):
    return cliente.post(CASA, json={"evento_id": evento, "accion": accion, **resto}, headers=ESCRIBIR)


def comprar(cliente, que, clave, evento):
    return cliente.post(COMPRAR, json={"evento_id": evento, "que": que, "clave": clave}, headers=ESCRIBIR)


def test_comprar_un_objeto_lo_cobra_una_vez_aunque_se_repita(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=50)
    cuerpo = {"evento_id": "evento-compra-01", "que": "objeto", "clave": "pocion_comida"}
    primera = cliente.post(COMPRAR, json=cuerpo, headers=ESCRIBIR).json()
    segunda = cliente.post(COMPRAR, json=cuerpo, headers=ESCRIBIR).json()
    for respuesta in (primera, segunda):
        assert respuesta["ok"] is True and respuesta["clave"] is None
        assert respuesta["mensaje"] == "Compraste Poción de comida. Está en tu mochila."
        assert respuesta["estado"]["saldos"]["monedas"] == 40
        assert respuesta["tienda"]["saldos"]["monedas"] == 40
    assert db.inventario(YO, G) == {"pocion_comida": 1}


def test_si_no_alcanza_es_un_no_con_su_frase_y_no_un_error(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=4)
    respuesta = cliente.post(COMPRAR, json={
        "evento_id": "evento-compra-02", "que": "objeto", "clave": "pocion_comida"}, headers=ESCRIBIR)
    assert respuesta.status_code == 200
    assert respuesta.json()["ok"] is False and respuesta.json()["clave"] == "faltan_monedas"
    assert respuesta.json()["mensaje"] == "Te faltan 6 monedas."


def test_el_reintento_de_un_no_alcanza_cuando_ya_alcanza_no_ensena_una_cifra_imposible(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=4)
    primera = comprar(cliente, "objeto", "pocion_comida", "evento-reintento").json()
    assert (primera["ok"], primera["clave"], primera["mensaje"]) == (False, "faltan_monedas", "Te faltan 6 monedas.")
    dar(monedas=50)   # entran monedas por la otra cara antes del reintento
    reintento = comprar(cliente, "objeto", "pocion_comida", "evento-reintento").json()
    assert (reintento["ok"], reintento["clave"], reintento["mensaje"]) == (
        False, "reintenta", "No se pudo comprar. Vuelve a intentarlo.")
    assert economia.saldos(YO, G).asciicoins == 50 and db.inventario(YO, G) == {}
    otra = comprar(cliente, "objeto", "pocion_comida", "evento-reintento-2").json()
    assert otra["ok"] is True and otra["estado"]["saldos"]["monedas"] == 40
    assert db.inventario(YO, G) == {"pocion_comida": 1}


@pytest.mark.parametrize("cuerpo,estado,clave", [
    ({"evento_id": "evento-compra-03", "que": "objeto", "clave": "poroto_rojo"}, 422, "peticion"),
    ({"evento_id": "evento-compra-04", "que": "objeto", "clave": "semilla"}, 409, "mas_adelante"),
    ({"evento_id": "evento-compra-05", "que": "sombrilla", "clave": "corona"}, 422, "peticion"),
    ({"evento_id": "corto", "que": "objeto", "clave": "pocion_comida"}, 422, "evento"),
    ({"que": "objeto", "clave": "pocion_comida"}, 422, "evento"),
    ([], 422, "evento"),
])
def test_lo_que_la_pantalla_nunca_pide_no_cobra_y_no_revienta(cliente, monkeypatch, cuerpo, estado, clave):
    en_la_tienda_con(cliente, monkeypatch, monedas=500)
    respuesta = cliente.post(COMPRAR, json=cuerpo, headers=ESCRIBIR)
    assert respuesta.status_code == estado and respuesta.json()["detail"]["clave"] == clave
    assert economia.saldos(YO, G).asciicoins == 500 and db.inventario(YO, G) == {}


@pytest.mark.parametrize("cuerpo", [
    {"que": "objeto", "clave": ["pocion_comida"]},
    {"que": "objeto", "clave": None},
    {"que": "objeto"},
    {"que": "cosmetico", "clave": "tinte_rojo"},
    {"que": "cosmetico", "clave": "pocion_comida"},
    {"que": "mueble", "clave": "trono"},
    {"que": ["objeto"], "clave": "pocion_comida"},
    {"que": None, "clave": "pocion_comida"},
])
def test_una_pieza_que_la_tienda_no_vende_es_422_peticion(cliente, monkeypatch, cuerpo):
    en_la_tienda_con(cliente, monkeypatch, monedas=500, gemas=500)
    respuesta = cliente.post(COMPRAR, json={"evento_id": "evento-pieza-01", **cuerpo}, headers=ESCRIBIR)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == {"clave": "peticion", "mensaje": "La petición no se entiende."}
    assert economia.saldos(YO, G) == economia.Saldos(500, 500)
    assert db.inventario(YO, G) == {} and db.ropero(YO, G) == frozenset() and db.mobiliario(YO, G) == {}


def test_las_frases_de_lo_que_no_se_compra(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=500)
    assert comprar(cliente, "objeto", "semilla", "evento-frase-01").json()["detail"] == {
        "clave": "mas_adelante", "mensaje": "Eso todavía no se vende aquí."}
    assert comprar(cliente, "objeto", "pocion_comida", "corto").json()["detail"] == {
        "clave": "evento", "mensaje": "Ese identificador de evento no vale."}


def test_el_saldo_que_cambio_por_la_otra_cara_ya_cuenta(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=50)
    assert cliente.get(TIENDA).json()["saldos"]["monedas"] == 50
    dar(monedas=4)
    respuesta = comprar(cliente, "objeto", "pocion_comida", "evento-otra-cara").json()
    assert respuesta["ok"] is False and respuesta["mensaje"] == "Te faltan 6 monedas."
    assert respuesta["tienda"]["saldos"]["monedas"] == 4 and respuesta["estado"]["saldos"]["monedas"] == 4
    assert db.inventario(YO, G) == {}


def test_te_falta_una_moneda_en_singular(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=9)
    assert comprar(cliente, "objeto", "pocion_comida", "evento-singular").json()["mensaje"] == "Te faltan 1 moneda."


def test_fuera_de_la_tienda_no_se_compra_nada(cliente, monkeypatch):
    reloj = en_la_tienda_con(cliente, monkeypatch, monedas=5000)
    una_casa(reloj)
    ir(cliente, "plaza")
    for respuesta in (
        comprar(cliente, "objeto", "pocion_comida", "evento-fuera-01"),
        comprar(cliente, "mueble", "felpudo", "evento-fuera-02"),
        casa(cliente, "comprar", "evento-fuera-03", casa="pequena"),
        casa(cliente, "vender", "evento-fuera-04", casa_id=1),
    ):
        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == {
            "clave": "no_estas_ahi", "mensaje": "Para eso tienes que estar en la tienda."}
    assert economia.saldos(YO, G).asciicoins == 5000 and db.inventario(YO, G) == {}
    assert len(db.hogar_leido(YO, G, reloj()).casas) == 1 and db.mobiliario(YO, G) == {}


def test_sin_la_cabecera_no_pasa(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=5000)
    sin = cliente.post(COMPRAR, json={"evento_id": "evento-cabecera", "que": "objeto", "clave": "pocion_comida"})
    assert sin.status_code == 403 and sin.json()["detail"]["clave"] == "sin_cabecera"
    sin = cliente.post(CASA, json={"evento_id": "evento-cabecera", "accion": "comprar", "casa": "pequena"})
    assert sin.status_code == 403 and sin.json()["detail"]["clave"] == "sin_cabecera"
    assert economia.saldos(YO, G).asciicoins == 5000 and db.inventario(YO, G) == {}


def test_sin_sesion_no_hay_compra(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    assert comprar(cliente, "objeto", "pocion_comida", "evento-sesion").status_code == 401
    assert casa(cliente, "comprar", "evento-sesion", casa="pequena").status_code == 401


def test_el_orden_de_las_comprobaciones(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)   # con avatar y sin gachamon
    dar(monedas=500)
    # Fuera de la tienda: el evento y el qué se miran antes que el lugar; la pieza, después.
    assert comprar(cliente, "objeto", "pocion_comida", "corto").json()["detail"]["clave"] == "evento"
    assert comprar(cliente, "sombrilla", "pocion_comida", "evento-orden-1").json()["detail"]["clave"] == "peticion"
    assert casa(cliente, "tirar", "evento-orden-2", casa="pequena").json()["detail"]["clave"] == "peticion"
    assert comprar(cliente, "objeto", "poroto_rojo", "evento-orden-3").json()["detail"]["clave"] == "no_estas_ahi"
    # En la tienda, sin gachamon: eso se mira antes que la pieza.
    ir(cliente, "tienda")
    for respuesta in (
        comprar(cliente, "objeto", "poroto_rojo", "evento-orden-4"),
        comprar(cliente, "objeto", "pocion_comida", "evento-orden-5"),
        casa(cliente, "vender", "evento-orden-6", casa_id="uno"),
    ):
        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == {
            "clave": "sin_gachamon", "mensaje": "Para comprar hace falta un gachamon."}
    assert economia.saldos(YO, G).asciicoins == 500 and db.inventario(YO, G) == {}


def test_un_evento_usado_para_una_cosa_no_sirve_para_otra(cliente, monkeypatch):
    reloj = en_la_tienda_con(cliente, monkeypatch, monedas=5000)
    assert comprar(cliente, "objeto", "pocion_comida", "evento-doble-1").json()["ok"] is True
    otra = comprar(cliente, "objeto", "silbato", "evento-doble-1")
    assert otra.status_code == 409
    assert otra.json()["detail"] == {"clave": "evento", "mensaje": "Ese evento ya se usó para otra cosa."}
    assert db.inventario(YO, G) == {"pocion_comida": 1} and economia.saldos(YO, G).asciicoins == 4990

    assert casa(cliente, "comprar", "evento-doble-2", casa="pequena").json()["ok"] is True
    otra = casa(cliente, "comprar", "evento-doble-2", casa="mediana")
    assert otra.status_code == 409 and otra.json()["detail"]["clave"] == "evento"
    assert [c.casa.clave for c in db.hogar_leido(YO, G, reloj()).casas] == ["pequena"]
    assert economia.saldos(YO, G).asciicoins == 4990 - 200


def test_si_el_gachamon_murio_entre_medias_no_se_cobra(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_vinculo(cliente)
    ir(cliente, "tienda")
    dar(monedas=5000, gemas=500, usuario=LA_DE_DISCORD)
    reloj.pasar(days=5)
    respuesta = comprar(cliente, "objeto", "pocion_comida", "evento-muerto")
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {
        "clave": "sin_gachamon", "mensaje": "Tu gachamon ya no es el mismo. Mira otra vez."}
    assert economia.saldos(LA_DE_DISCORD, G) == economia.Saldos(5000, 500)
    assert db.inventario(LA_DE_DISCORD, G) == {}


# --- El cosmético ----------------------------------------------------------------

def test_el_cosmetico_cobra_gemas_y_el_gachamon_ya_lo_lleva(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=50, gemas=100)
    antes = cliente.get("/gachamon/api/estado").json()["gachamon"]["retrato"]
    assert "/sin.png" in antes
    primera = comprar(cliente, "cosmetico", "corona", "evento-corona-1").json()
    segunda = comprar(cliente, "cosmetico", "corona", "evento-corona-1").json()
    for respuesta in (primera, segunda):
        assert respuesta["ok"] is True and respuesta["clave"] is None
        assert respuesta["mensaje"] == "Compraste Corona. Pelusa ya lo lleva."
        assert respuesta["estado"]["saldos"] == {"monedas": 50, "gemas": 40}
        assert respuesta["estado"]["gachamon"]["retrato"] == antes.replace("/sin.png", "/corona.png")
        assert next(c for c in respuesta["tienda"]["cosmeticos"] if c["clave"] == "corona")["tuyo"] is True
    assert economia.saldos(YO, G).asciigems == 40 and db.ropero(YO, G) == frozenset({"corona"})


@pytest.mark.parametrize("ahora_lleva", [None, "chistera"], ids=["se_la_quitaron", "lleva_otra"])
def test_el_replay_de_un_cosmetico_que_ya_no_lleva_dice_que_esta_en_el_ropero(cliente, monkeypatch, ahora_lleva):
    en_la_tienda_con(cliente, monkeypatch, gemas=100)
    primera = comprar(cliente, "cosmetico", "corona", "evento-corona-1").json()
    assert primera["mensaje"] == "Compraste Corona. Pelusa ya lo lleva."
    # Entre el intento y el reintento, por la otra cara, al activo le cambian el sombrero.
    with db.conectar() as con:
        if ahora_lleva:
            db.guardar_en_el_ropero_en(con, YO, G, ahora_lleva)
        con.execute("UPDATE criaturas SET sombrero = ? WHERE usuario_id = ? AND guild_id = ? AND muerta_en IS NULL",
                    (ahora_lleva, YO, G))
    replay = comprar(cliente, "cosmetico", "corona", "evento-corona-1").json()
    assert (replay["ok"], replay["clave"], replay["mensaje"]) == (True, None, "Compraste Corona. Está en tu ropero.")
    assert economia.saldos(YO, G).asciigems == 40


def test_la_frase_del_cosmetico_sin_gachamon_no_revienta():
    corona = cosmeticos.CATALOGO["corona"]
    hecho = economia.ResultadoCosmetico(ok=True, criatura=None, saldo=40, replay=True)
    assert tienda._del_cosmetico(corona, hecho) == {
        "ok": True, "clave": None, "mensaje": "Compraste Corona. Está en tu ropero."}


def test_el_titulo_comprado_aparece_en_el_estado(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, gemas=30)
    respuesta = comprar(cliente, "cosmetico", "titulo_veloz", "evento-titulo").json()
    assert respuesta["ok"] is True and respuesta["mensaje"] == "Compraste El Veloz. Pelusa ya lo lleva."
    genero = respuesta["estado"]["gachamon"]["genero"]
    assert respuesta["estado"]["gachamon"]["titulo"] == cosmeticos.texto_del_titulo("titulo_veloz", genero)
    assert respuesta["estado"]["saldos"]["gemas"] == 0


@pytest.mark.parametrize("gemas,mensaje", [
    (10, "Te faltan 50 gemas. Se ganan con las medallas."),
    (59, "Te faltan 1 gema. Se ganan con las medallas."),
])
def test_un_cosmetico_sin_gemas_bastantes(cliente, monkeypatch, gemas, mensaje):
    en_la_tienda_con(cliente, monkeypatch, gemas=gemas)
    respuesta = comprar(cliente, "cosmetico", "corona", "evento-sin-gemas")
    assert respuesta.status_code == 200
    assert {k: respuesta.json()[k] for k in ("ok", "clave", "mensaje")} == {
        "ok": False, "clave": "faltan_gemas", "mensaje": mensaje}
    assert economia.saldos(YO, G).asciigems == gemas and db.ropero(YO, G) == frozenset()


def test_un_cosmetico_que_ya_es_tuyo(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, gemas=500)
    assert comprar(cliente, "cosmetico", "corona", "evento-corona-1").json()["ok"] is True
    otra = comprar(cliente, "cosmetico", "corona", "evento-corona-2").json()
    assert {k: otra[k] for k in ("ok", "clave", "mensaje")} == {
        "ok": False, "clave": "ya_lo_tienes", "mensaje": "Ya lo tienes."}
    assert economia.saldos(YO, G).asciigems == 440


# --- El mueble -------------------------------------------------------------------

def test_un_mueble_sin_casa_no_se_compra(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=500)
    respuesta = comprar(cliente, "mueble", "felpudo", "evento-mueble-0").json()
    assert {k: respuesta[k] for k in ("ok", "clave", "mensaje")} == {
        "ok": False, "clave": "sin_casa", "mensaje": "Los muebles van en una casa, y todavía no tienes."}
    assert economia.saldos(YO, G).asciicoins == 500 and db.mobiliario(YO, G) == {}


def test_un_mueble_a_la_intemperie_dice_lo_mismo(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_vinculo(cliente)
    db.hogar_de(LA_DE_DISCORD, G, reloj())   # empieza la estancia en el refugio…
    reloj.pasar(days=casas.DIAS_DE_REFUGIO, seconds=1)   # …y se acaba
    ir(cliente, "tienda")
    dar(monedas=500, usuario=LA_DE_DISCORD)
    respuesta = comprar(cliente, "mueble", "felpudo", "evento-intemperie").json()
    assert respuesta["estado"]["hogar"] == "intemperie"
    assert {k: respuesta[k] for k in ("ok", "clave", "mensaje")} == {
        "ok": False, "clave": "intemperie", "mensaje": "Los muebles van en una casa, y todavía no tienes."}
    assert economia.saldos(LA_DE_DISCORD, G).asciicoins == 500


def test_un_mueble_con_casa_queda_puesto(cliente, monkeypatch):
    reloj = en_la_tienda_con(cliente, monkeypatch, monedas=500)
    casa_id = una_casa(reloj)
    primera = comprar(cliente, "mueble", "felpudo", "evento-mueble-1").json()
    segunda = comprar(cliente, "mueble", "felpudo", "evento-mueble-1").json()
    for respuesta in (primera, segunda):
        assert respuesta["ok"] is True and respuesta["clave"] is None
        assert respuesta["mensaje"] == "Compraste Felpudo. Ya está puesto en tu casa."
        assert respuesta["estado"]["saldos"]["monedas"] == 470
        assert respuesta["tienda"]["casas"]["tuyas"][0]["muebles"] == 1
        assert next(m for m in respuesta["tienda"]["muebles"]["lista"] if m["clave"] == "felpudo")["tuyo"] is True
    assert db.mobiliario(YO, G) == {"felpudo": True}
    assert db.hogar_leido(YO, G, reloj()).casa_por_id(casa_id).puestos == ("felpudo",)


def test_un_mueble_que_no_cabe_queda_guardado(cliente, monkeypatch):
    reloj = en_la_tienda_con(cliente, monkeypatch, monedas=500)
    casa_id = una_casa(reloj)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        for clave in ("felpudo", "maceta", "cuadro"):
            db.comprar_mueble_en(con, YO, G, clave, True, casa_id)
    respuesta = comprar(cliente, "mueble", "lampara", "evento-mueble-2").json()
    assert respuesta["ok"] is True
    assert respuesta["mensaje"] == "Compraste Lámpara. No cabía en tu casa: quedó guardado."
    assert respuesta["estado"]["saldos"]["monedas"] == 420
    assert db.mobiliario(YO, G)["lampara"] is False


def test_un_mueble_que_ya_tienes_o_que_no_alcanzas(cliente, monkeypatch):
    reloj = en_la_tienda_con(cliente, monkeypatch, monedas=100)
    una_casa(reloj)
    assert comprar(cliente, "mueble", "felpudo", "evento-mueble-3").json()["ok"] is True
    otra = comprar(cliente, "mueble", "felpudo", "evento-mueble-4").json()
    assert (otra["ok"], otra["clave"], otra["mensaje"]) == (False, "ya_lo_tienes", "Ya lo tienes.")
    cara = comprar(cliente, "mueble", "alfombra", "evento-mueble-5").json()
    assert (cara["ok"], cara["clave"], cara["mensaje"]) == (False, "faltan_monedas", "Te faltan 50 monedas.")
    assert economia.saldos(YO, G).asciicoins == 70


# --- Las casas -------------------------------------------------------------------

def test_una_casa_nueva_con_el_mismo_evento_es_una_sola(cliente, monkeypatch):
    reloj = en_la_tienda_con(cliente, monkeypatch, monedas=1000)
    assert cliente.get("/gachamon/api/estado").json()["hogar"] == "refugio"
    primera = casa(cliente, "comprar", "evento-casa-01", casa="pequena").json()
    segunda = casa(cliente, "comprar", "evento-casa-01", casa="pequena").json()
    for respuesta in (primera, segunda):
        assert respuesta["ok"] is True and respuesta["clave"] is None
        assert respuesta["mensaje"] == "Compraste una casa pequeña."
        assert respuesta["estado"]["hogar"] == "propia"
        assert respuesta["estado"]["saldos"]["monedas"] == 800
        assert [c["clave"] for c in respuesta["tienda"]["casas"]["tuyas"]] == ["pequena"]
    assert len(db.hogar_leido(YO, G, reloj()).casas) == 1


def test_mejorar_una_casa_cobra_la_diferencia(cliente, monkeypatch):
    reloj = en_la_tienda_con(cliente, monkeypatch, monedas=500)
    casa_id = una_casa(reloj)
    respuesta = casa(cliente, "mejorar", "evento-mejora-1", casa="mediana", casa_id=casa_id).json()
    assert respuesta["ok"] is True and respuesta["clave"] is None
    assert respuesta["mensaje"] == "Tu casa pequeña ahora es una casa mediana."
    assert respuesta["estado"]["saldos"]["monedas"] == 500 - 340
    assert [(c["id"], c["clave"]) for c in respuesta["tienda"]["casas"]["tuyas"]] == [(casa_id, "mediana")]
    repetida = casa(cliente, "mejorar", "evento-mejora-1", casa="mediana", casa_id=casa_id).json()
    assert repetida["ok"] is True and repetida["mensaje"] == respuesta["mensaje"]
    assert economia.saldos(YO, G).asciicoins == 160


def test_vender_una_casa_devuelve_el_ochenta_por_ciento(cliente, monkeypatch):
    reloj = en_la_tienda_con(cliente, monkeypatch, monedas=7)
    casa_id = una_casa(reloj)
    primera = casa(cliente, "vender", "evento-venta-1", casa_id=casa_id).json()
    segunda = casa(cliente, "vender", "evento-venta-1", casa_id=casa_id).json()
    for respuesta in (primera, segunda):
        assert respuesta["ok"] is True and respuesta["clave"] is None
        assert respuesta["mensaje"] == "Vendiste tu casa pequeña por 160 monedas."
        assert respuesta["estado"]["saldos"]["monedas"] == 7 + 160
        assert respuesta["tienda"]["casas"]["tuyas"] == []
    assert economia.saldos(YO, G).asciicoins == 167


def test_la_cuarta_casa_no_se_compra(cliente, monkeypatch):
    reloj = en_la_tienda_con(cliente, monkeypatch, monedas=5000)
    for _ in range(casas.MAXIMO_CASAS):
        una_casa(reloj)
    respuesta = casa(cliente, "comprar", "evento-cuarta", casa="pequena")
    assert respuesta.status_code == 200
    assert {k: respuesta.json()[k] for k in ("ok", "clave", "mensaje")} == {
        "ok": False, "clave": "maximo_de_casas",
        "mensaje": "Ya tienes 3 casas, que es el máximo. Vende una o mejora las que tienes."}
    assert economia.saldos(YO, G).asciicoins == 5000 and len(db.hogar_leido(YO, G, reloj()).casas) == 3


@pytest.mark.parametrize("pedido,clave,mensaje", [
    (lambda ids: ("comprar", {"casa": "grande"}), "faltan_monedas", "Te faltan 900 monedas."),
    (lambda ids: ("mejorar", {"casa": "grande", "casa_id": ids[0]}), "faltan_monedas", "Te faltan 740 monedas."),
    (lambda ids: ("mejorar", {"casa": "pequena", "casa_id": ids[1]}), "no_se_empeora",
     "Esa casa ya es de ese tamaño o más grande."),
    (lambda ids: ("mejorar", {"casa": "mediana", "casa_id": ids[1]}), "no_se_empeora",
     "Esa casa ya es de ese tamaño o más grande."),
], ids=["comprar_sin_alcanzar", "mejorar_sin_alcanzar", "a_mas_pequena", "al_mismo_tamano"])
def test_lo_que_no_se_puede_hacer_con_una_casa_dice_por_que(cliente, monkeypatch, pedido, clave, mensaje):
    reloj = en_la_tienda_con(cliente, monkeypatch, monedas=300)
    ids = [una_casa(reloj, "pequena"), una_casa(reloj, "mediana")]
    accion, resto = pedido(ids)
    respuesta = casa(cliente, accion, "evento-casa-no", **resto)
    assert respuesta.status_code == 200
    assert {k: respuesta.json()[k] for k in ("ok", "clave", "mensaje")} == {
        "ok": False, "clave": clave, "mensaje": mensaje}
    assert economia.saldos(YO, G).asciicoins == 300
    assert [c.casa.clave for c in db.hogar_leido(YO, G, reloj()).casas] == ["pequena", "mediana"]


OTRA = "333333333333333333"   # otra persona: una identidad de Discord sintética, con su casa en la base temporal


@pytest.mark.parametrize("pedido", [
    lambda ajena: ("mejorar", {"casa": "mediana", "casa_id": ajena}),
    lambda ajena: ("vender", {"casa_id": ajena}),
    lambda ajena: ("mejorar", {"casa": "mediana", "casa_id": -1}),
    lambda ajena: ("vender", {"casa_id": -1}),
], ids=["mejorar_la_de_otro", "vender_la_de_otro", "mejorar_un_id_negativo", "vender_un_id_negativo"])
def test_la_casa_de_otro_no_se_mejora_ni_se_vende(cliente, monkeypatch, pedido):
    reloj = en_la_tienda_con(cliente, monkeypatch, monedas=5000)
    dar(monedas=70, usuario=OTRA)
    mia_ = una_casa(reloj)
    ajena = una_casa(reloj, usuario=OTRA)
    accion, resto = pedido(ajena)
    respuesta = casa(cliente, accion, "evento-ajena", **resto)
    assert respuesta.status_code == 200
    assert {k: respuesta.json()[k] for k in ("ok", "clave", "mensaje")} == {
        "ok": False, "clave": "no_es_tuya", "mensaje": "Esa casa no es tuya."}
    assert [(c.id, c.casa.clave) for c in db.hogar_leido(OTRA, G, reloj()).casas] == [(ajena, "pequena")]
    assert [(c.id, c.casa.clave) for c in db.hogar_leido(YO, G, reloj()).casas] == [(mia_, "pequena")]
    assert economia.saldos(YO, G).asciicoins == 5000 and economia.saldos(OTRA, G).asciicoins == 70


def test_sin_casa_no_hay_nada_que_vender(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=10)
    respuesta = casa(cliente, "vender", "evento-sin-casa", casa_id=1).json()
    assert {k: respuesta[k] for k in ("ok", "clave", "mensaje")} == {
        "ok": False, "clave": "sin_casa", "mensaje": "No tienes casa que vender."}
    assert economia.saldos(YO, G).asciicoins == 10


@pytest.mark.parametrize("cuerpo,clave", [
    ({"accion": "comprar", "casa": "pequena"}, "evento"),
    ({"evento_id": "corto", "accion": "comprar", "casa": "pequena"}, "evento"),
    ({"evento_id": "evento-casa-mal", "accion": "derribar", "casa": "pequena"}, "peticion"),
    ({"evento_id": "evento-casa-mal", "accion": ["comprar"], "casa": "pequena"}, "peticion"),
    ({"evento_id": "evento-casa-mal", "casa": "pequena"}, "peticion"),
    ({"evento_id": "evento-casa-mal", "accion": "comprar", "casa": "refugio"}, "peticion"),
    ({"evento_id": "evento-casa-mal", "accion": "comprar", "casa": "castillo"}, "peticion"),
    ({"evento_id": "evento-casa-mal", "accion": "comprar"}, "peticion"),
    ({"evento_id": "evento-casa-mal", "accion": "mejorar", "casa": "mediana"}, "peticion"),
    ({"evento_id": "evento-casa-mal", "accion": "mejorar", "casa_id": 1}, "peticion"),
    ({"evento_id": "evento-casa-mal", "accion": "mejorar", "casa": "mediana", "casa_id": "1"}, "peticion"),
    ({"evento_id": "evento-casa-mal", "accion": "vender"}, "peticion"),
    ({"evento_id": "evento-casa-mal", "accion": "vender", "casa_id": True}, "peticion"),
    ({"evento_id": "evento-casa-mal", "accion": "vender", "casa_id": 1.0}, "peticion"),
    ("comprar", "evento"),
])
def test_una_peticion_de_casa_mal_hecha_no_toca_nada(cliente, monkeypatch, cuerpo, clave):
    reloj = en_la_tienda_con(cliente, monkeypatch, monedas=5000)
    una_casa(reloj)
    respuesta = cliente.post(CASA, json=cuerpo, headers=ESCRIBIR)
    assert respuesta.status_code == 422 and respuesta.json()["detail"]["clave"] == clave
    assert economia.saldos(YO, G).asciicoins == 5000
    assert [c.casa.clave for c in db.hogar_leido(YO, G, reloj()).casas] == ["pequena"]
