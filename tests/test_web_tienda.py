from dataclasses import replace

import pytest

import cosmeticos
import db
import departamento as dep
import economia
import especies as esp
import identidad
import nacer
import objetos
from ayudas_web import AVATAR, CABECERA, ESCRIBIR, PUEBLO, alta, con_gachamon, entrar, poner_reloj
from web import tienda

API = "/gachamon/api"
TIENDA, LUGAR = f"{API}/tienda", f"{API}/lugar"
COMPRAR = f"{TIENDA}/comprar"
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


NOTA_DE_COMPETIR = "Sirve en las competencias, que todavía no están en la página."
PARA_COMPETIR = ("fuerza_1d4", "velocidad_1d12", "descanso_rapido")


def _con_sus_notas(objetos_):
    for clave in PARA_COMPETIR:
        assert objetos_[clave]["se_vende"] is False and objetos_[clave]["nota"] == NOTA_DE_COMPETIR


def test_a_quien_no_tiene_discord_no_se_le_vende_lo_que_todavia_no_se_usa_en_la_pagina(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    ir(cliente, "tienda")
    objetos_ = {o["clave"]: o for o in cliente.get(TIENDA).json()["objetos"]}
    assert len(objetos_) == 15
    _con_sus_notas(objetos_)
    for clave in ("pocion_comida", "silbato", "golosinas", "placa"):
        assert objetos_[clave]["se_vende"] is True and objetos_[clave]["nota"] is None


def test_lo_que_no_se_usa_en_la_pagina_no_se_le_vende_ni_a_quien_tiene_discord(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_vinculo(cliente)
    ir(cliente, "tienda")
    dar(monedas=5000, usuario=LA_DE_DISCORD)
    objetos_ = {o["clave"]: o for o in cliente.get(TIENDA).json()["objetos"]}
    assert len(objetos_) == 15
    _con_sus_notas(objetos_)
    assert objetos_["pocion_comida"]["se_vende"] is True and objetos_["pocion_comida"]["nota"] is None
    for i, clave in enumerate(PARA_COMPETIR):
        respuesta = comprar(cliente, "objeto", clave, f"evento-sin-uso-{i}")
        assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "mas_adelante"
    assert economia.saldos(LA_DE_DISCORD, G).asciicoins == 5000 and db.inventario(LA_DE_DISCORD, G) == {}


@pytest.mark.parametrize("vinculada", [False, True])
def test_las_notas_ya_no_mandan_a_discord(cliente, monkeypatch, vinculada):
    poner_reloj(monkeypatch)
    (con_vinculo if vinculada else con_gachamon)(cliente)
    ir(cliente, "tienda")
    lista = cliente.get(TIENDA).json()["objetos"]
    assert not [o["clave"] for o in lista if o["nota"] and "Discord" in o["nota"]]
    assert all(o["nota"] != "Más adelante." for o in lista)


def test_la_tienda_ya_no_vende_casas(cliente):
    con_gachamon(cliente); ir(cliente, "tienda")
    assert "casas" not in cliente.get(f"{API}/tienda").json()
    assert cliente.post(f"{API}/tienda/casa", json={"accion": "comprar", "casa": "pequena", "evento_id": "c1"}, headers=CABECERA).status_code in (404, 405)


def test_la_tienda_no_vende_ni_el_ticket_del_refugio_ni_la_semilla(cliente):
    con_gachamon(cliente); ir(cliente, "tienda")
    claves = {o["clave"] for o in cliente.get(f"{API}/tienda").json()["objetos"]}
    assert "ticket_refugio" not in claves and "semilla" not in claves


@pytest.mark.parametrize("clave", ["ticket_refugio", "semilla"])
@pytest.mark.parametrize("vinculada", [False, True])
def test_ni_el_ticket_ni_la_semilla_se_compran_ni_teniendo_discord(cliente, monkeypatch, vinculada, clave):
    # El ticket ya no existe y la semilla ya no se vende: pedirlos no se entiende.
    poner_reloj(monkeypatch)
    (con_vinculo if vinculada else con_gachamon)(cliente)
    ir(cliente, "tienda")
    usuario = LA_DE_DISCORD if vinculada else YO
    dar(monedas=500, usuario=usuario)
    respuesta = comprar(cliente, "objeto", clave, "evento-de-antes-01")
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == {"clave": "peticion", "mensaje": "La petición no se entiende."}
    assert economia.saldos(usuario, G).asciicoins == 500 and db.inventario(usuario, G) == {}


def test_cada_objeto_trae_lo_suyo_en_el_orden_del_catalogo(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    usuario, guild = mia()
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(con, usuario, guild, "pocion_comida", 3)
    ir(cliente, "tienda")
    lista = cliente.get(TIENDA).json()["objetos"]
    # Todo lo que está a la venta.
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


def test_cada_mueble_trae_lo_suyo_y_cuantos_tienes_puestos_o_guardados(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    usuario, guild = mia()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db._departamento_en(con, usuario, guild, reloj())     # tu cama puesta y otra guardada
        db.anadir_mueble_en(con, usuario, guild, "felpudo", 1, 1)
        db.anadir_mueble_en(con, usuario, guild, "felpudo")
    ir(cliente, "tienda")
    lista = cliente.get(TIENDA).json()["muebles"]["lista"]
    assert [m["clave"] for m in lista] == list(dep.MUEBLES)
    assert lista[0] == {"clave": "felpudo", "nombre": "Felpudo", "precio": 30, "comodidad": 2,
                        "icono": "iconos/muebles/felpudo.png", "tienes": 2}
    assert {m["clave"]: m["tienes"] for m in lista if m["tienes"]} == {"felpudo": 2, "cama_sencilla": 2}


def test_mirar_el_catalogo_no_crea_el_departamento(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    ir(cliente, "tienda")
    assert cliente.get(TIENDA).status_code == 200
    with db.conectar() as con:
        departamentos = con.execute("SELECT COUNT(*) FROM departamentos").fetchone()[0]
    assert departamentos == 0


def test_donde_sirve_cada_objeto():
    sirve = {o.clave: tienda.donde_sirve(o) for o in objetos.a_la_venta()}
    assert {c for c, d in sirve.items() if d == "competir"} == {"fuerza_1d4", "velocidad_1d12", "descanso_rapido"} | {
        o.clave for o in objetos.a_la_venta() if o.stat}
    assert set(sirve.values()) == {"competir", None}
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
    ({"evento_id": "evento-compra-04", "que": "objeto", "clave": "fuerza_1d4"}, 409, "mas_adelante"),
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
    assert db.inventario(YO, G) == {} and db.ropero(YO, G) == frozenset()
    assert db.departamento_leido(YO, G) == dep.DE_PARTIDA


def test_las_frases_de_lo_que_no_se_compra(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=500)
    assert comprar(cliente, "objeto", "descanso_rapido", "evento-frase-01").json()["detail"] == {
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
    en_la_tienda_con(cliente, monkeypatch, monedas=5000, gemas=500)
    ir(cliente, "plaza")
    for respuesta in (
        comprar(cliente, "objeto", "pocion_comida", "evento-fuera-01"),
        comprar(cliente, "mueble", "felpudo", "evento-fuera-02"),
        comprar(cliente, "cosmetico", "corona", "evento-fuera-03"),
    ):
        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == {
            "clave": "no_estas_ahi", "mensaje": "Para eso tienes que estar en la tienda."}
    assert economia.saldos(YO, G) == economia.Saldos(5000, 500) and db.inventario(YO, G) == {}
    assert db.ropero(YO, G) == frozenset() and db.departamento_leido(YO, G) == dep.DE_PARTIDA


def test_sin_la_cabecera_no_pasa(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=5000)
    sin = cliente.post(COMPRAR, json={"evento_id": "evento-cabecera", "que": "objeto", "clave": "pocion_comida"})
    assert sin.status_code == 403 and sin.json()["detail"]["clave"] == "sin_cabecera"
    assert economia.saldos(YO, G).asciicoins == 5000 and db.inventario(YO, G) == {}


def test_sin_sesion_no_hay_compra(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    assert comprar(cliente, "objeto", "pocion_comida", "evento-sesion").status_code == 401


def test_el_orden_de_las_comprobaciones(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)   # con avatar y sin gachamon
    dar(monedas=500)
    # Fuera de la tienda: el evento y el qué se miran antes que el lugar; la pieza, después.
    assert comprar(cliente, "objeto", "pocion_comida", "corto").json()["detail"]["clave"] == "evento"
    assert comprar(cliente, "sombrilla", "pocion_comida", "evento-orden-1").json()["detail"]["clave"] == "peticion"
    assert comprar(cliente, "objeto", "poroto_rojo", "evento-orden-3").json()["detail"]["clave"] == "no_estas_ahi"
    # En la tienda, sin gachamon: eso se mira antes que la pieza.
    ir(cliente, "tienda")
    for respuesta in (
        comprar(cliente, "objeto", "poroto_rojo", "evento-orden-4"),
        comprar(cliente, "objeto", "pocion_comida", "evento-orden-5"),
        comprar(cliente, "mueble", "trono", "evento-orden-6"),
    ):
        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == {
            "clave": "sin_gachamon", "mensaje": "Para comprar hace falta un gachamon."}
    assert economia.saldos(YO, G).asciicoins == 500 and db.inventario(YO, G) == {}


def test_un_evento_usado_para_una_cosa_no_sirve_para_otra(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=5000)
    assert comprar(cliente, "objeto", "pocion_comida", "evento-doble-1").json()["ok"] is True
    otra = comprar(cliente, "objeto", "silbato", "evento-doble-1")
    assert otra.status_code == 409
    assert otra.json()["detail"] == {"clave": "evento", "mensaje": "Ese evento ya se usó para otra cosa."}
    assert db.inventario(YO, G) == {"pocion_comida": 1} and economia.saldos(YO, G).asciicoins == 4990

    assert comprar(cliente, "mueble", "felpudo", "evento-doble-2").json()["ok"] is True
    otra = comprar(cliente, "mueble", "maceta", "evento-doble-2")
    assert otra.status_code == 409 and otra.json()["detail"]["clave"] == "evento"
    assert [p.clave for p in db.departamento_leido(YO, G).guardadas] == ["cama_sencilla", "felpudo"]
    assert economia.saldos(YO, G).asciicoins == 4990 - dep.MUEBLES["felpudo"].precio


def test_si_el_relevo_sale_en_la_peticion_no_se_cobra(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_vinculo(cliente)
    ir(cliente, "tienda")
    dar(monedas=5000, gemas=500, usuario=LA_DE_DISCORD)
    nube = db.crear(LA_DE_DISCORD, G, "pulpo", "Nube", (15, 15, 15, 15), reloj.ahora, activa=False)
    # Pelusa murió cuando todavía se moría de hambre, y nadie sacó todavía al relevo.
    pelusa = db.criatura_activa(LA_DE_DISCORD, G)
    db.guardar(replace(pelusa, hambre=0.0, muerta_en=reloj.ahora, causa_muerte="hambre"))

    respuesta = comprar(cliente, "objeto", "pocion_comida", "evento-relevo")
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {
        "clave": "sin_gachamon", "mensaje": "Tu gachamon ya no es el mismo. Mira otra vez."}
    assert economia.saldos(LA_DE_DISCORD, G) == economia.Saldos(5000, 500)
    assert db.inventario(LA_DE_DISCORD, G) == {}
    assert db.criatura_activa(LA_DE_DISCORD, G).id == nube.id   # el relevo sí salió


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

def test_la_tienda_vende_muebles_de_a_varios(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=200)
    for evento in ("evento-mueble-1", "evento-mueble-2"):
        r = comprar(cliente, "mueble", "felpudo", evento).json()
        assert (r["ok"], r["mensaje"]) == (True, "Compraste Felpudo. Quedó en tus guardados.")
    felpudo = next(m for m in r["tienda"]["muebles"]["lista"] if m["clave"] == "felpudo")
    assert felpudo["tienes"] == 2 and "tuyo" not in felpudo and "tienes_casa" not in r["tienda"]["muebles"]
    assert r["estado"]["saldos"]["monedas"] == 140


def test_la_cama_sencilla_esta_a_la_venta_por_85(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch)
    lista = cliente.get(TIENDA).json()["muebles"]["lista"]
    assert next(m for m in lista if m["clave"] == "cama_sencilla")["precio"] == 85


def test_un_mueble_no_pide_tener_casa(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=30)
    for _ in range(2):   # el reintento con el mismo evento no cobra ni entrega otro
        r = comprar(cliente, "mueble", "felpudo", "evento-sin-casa").json()
        assert (r["ok"], r["clave"], r["mensaje"]) == (True, None, "Compraste Felpudo. Quedó en tus guardados.")
        assert r["estado"]["saldos"]["monedas"] == 0
    guardados = db.departamento_leido(YO, G).guardadas
    assert [p.clave for p in guardados] == ["cama_sencilla", "felpudo"]


def test_sin_monedas_el_mueble_dice_cuantas_faltan(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=10)
    r = comprar(cliente, "mueble", "felpudo", "evento-sin-monedas")
    assert r.status_code == 200
    assert {k: r.json()[k] for k in ("ok", "clave", "mensaje")} == {
        "ok": False, "clave": "faltan_monedas", "mensaje": "Te faltan 20 monedas."}
    assert economia.saldos(YO, G).asciicoins == 10
    assert [p.clave for p in db.departamento_leido(YO, G).piezas] == ["cama_sencilla", "cama_sencilla"]
