import db
import economia
import especies as esp
import globos
import identidad
import retrato
from ayudas_web import AVATAR, ESCRIBIR, PUEBLO, T0, alta, con_gachamon, entrar, poner_reloj
from test_web_tienda import LA_DE_DISCORD, con_vinculo
from web import pueblo

INCUBADORA, SACAR = "/gachamon/api/incubadora", "/gachamon/api/incubadora/sacar"
ESTADO, LUGAR = "/gachamon/api/estado", "/gachamon/api/lugar"
HUEVO, BAUTIZAR = "/gachamon/api/huevo", "/gachamon/api/bautizar"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)
OTRA_PERSONA = "333333333333333333"
STATS = (10, 10, 10, 10)


def ir(cliente, lugar="incubadora"):
    hecho = cliente.post(LUGAR, json={"lugar": lugar}, headers=ESCRIBIR)
    assert hecho.status_code == 200, hecho.text
    return hecho.json()


def sacar(cliente, gachamon_id):
    return cliente.post(SACAR, json={"gachamon_id": gachamon_id}, headers=ESCRIBIR)


def bautizar(cliente, gachamon_id, nombre):
    return cliente.post(BAUTIZAR, json={"nombre": nombre, "gachamon_id": gachamon_id}, headers=ESCRIBIR)


def activa():
    return db.criatura_activa(LA_DE_DISCORD, G)


def con_plantel(cliente):
    """La cuenta 1, vinculada: Pelusa activa, Nube con nombre y un recluta sin él, en ese orden."""
    con_vinculo(cliente)
    pelusa = activa()
    nube = db.crear(LA_DE_DISCORD, G, "pulpo", "Nube", STATS, db.ahora_utc(), activa=False)
    recluta = db.crear(LA_DE_DISCORD, G, "pollito", "", STATS, db.ahora_utc(), activa=False)
    return pelusa, nube, recluta


def vinculada_sin_gachamon(cliente):
    """La cuenta 1 vinculada a Discord, con avatar y sin haber roto el huevo."""
    entrar(cliente, 1)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    assert db.canjear_codigo_de_vinculo(codigo, LA_DE_DISCORD, G, db.ahora_utc()) == "ok"
    assert cliente.put("/gachamon/api/avatar", json=AVATAR, headers=ESCRIBIR).status_code == 200


def el_retrato(especie, cara="feliz"):
    return f"/gachamon/retrato/{especie}/bebe/{cara}/sin.png?v={retrato.version()}"


# --- El lugar ------------------------------------------------------------------

def test_la_incubadora_abre_y_ofrece_su_plantel(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    assert pueblo.LUGARES["incubadora"].abre == "ya"
    assert pueblo.OFRECE["incubadora"] == ("incubadora",)
    assert pueblo.ofrece("incubadora") == ("incubadora",)
    con_gachamon(cliente)
    estado = ir(cliente)
    assert estado["lugar"] == {
        "clave": "incubadora", "nombre": "Incubadora", "abre": "ya", "aviso": None, "ofrece": ["incubadora"],
    }


def test_la_incubadora_ya_no_dice_que_todo_duerme():
    assert "Todo está quietito, como si durmiera." not in globos.DEL_LUGAR["incubadora"]
    assert "Se oye un zumbido tibio, muy bajito." in globos.DEL_LUGAR["incubadora"]


# --- El plantel ----------------------------------------------------------------

def test_el_plantel_en_orden(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pelusa, nube, recluta = con_plantel(cliente)
    # La activa va primero aunque no sea la de menor id; las demás, por id.
    assert db.activar(nube.id, LA_DE_DISCORD, G, db.ahora_utc())
    cuerpo = cliente.get(INCUBADORA).json()
    assert [g["id"] for g in cuerpo["plantel"]] == [nube.id, pelusa.id, recluta.id]
    assert [g["activo"] for g in cuerpo["plantel"]] == [True, False, False]
    assert cuerpo["plantel"][0] == {
        "id": nube.id, "nombre": "Nube", "sin_nombre": False,
        "nombre_especie": esp.ESPECIES["pulpo"].nombre, "nombre_etapa": esp.nombre_etapa("bebe", "macho"),
        "nivel": 1, "retrato": el_retrato("pulpo"), "activo": True,
    }
    assert cuerpo["plantel"][2] == {
        "id": recluta.id, "nombre": "", "sin_nombre": True,
        "nombre_especie": esp.ESPECIES["pollito"].nombre, "nombre_etapa": esp.nombre_etapa("bebe", "macho"),
        "nivel": 1, "retrato": el_retrato("pollito"), "activo": False,
    }
    assert cuerpo["plantel"][1]["nombre"] == "Pelusa" and cuerpo["plantel"][1]["sin_nombre"] is False
    assert cuerpo["maximo"] == db.MAXIMO_PLANTEL == 25
    saldos = economia.saldos(LA_DE_DISCORD, G)
    assert cuerpo["saldos"] == {"monedas": saldos.asciicoins, "gemas": saldos.asciigems}
    # Con una activa no hay nadie esperando que lo bauticen para seguir jugando.
    assert cliente.get(ESTADO).json()["sin_nombre"] is None


def test_quien_juega_solo_en_la_web_ve_a_su_unico_gachamon(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    pelusa = con_gachamon(cliente)["gachamon"]
    reloj.pasar(days=5)
    plantel = cliente.get(INCUBADORA).json()["plantel"]
    assert [(g["id"], g["nombre"], g["activo"], g["sin_nombre"]) for g in plantel] == [
        (pelusa["id"], "Pelusa", True, False),
    ]
    # El activo se ve con la cara de ahora, la misma que en el estado.
    gachamon = cliente.get(ESTADO).json()["gachamon"]
    assert gachamon["cara"] == "mal"
    assert plantel[0]["retrato"] == gachamon["retrato"]
    # Y mirar no le guarda el paso del tiempo.
    assert db.por_id(pelusa["id"]).actualizada_en == T0


def test_el_plantel_pide_sesion_y_cuenta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    assert cliente.get(INCUBADORA).status_code == 401
    entrar(cliente, 1)
    assert cliente.get(INCUBADORA).json()["detail"]["clave"] == "sin_cuenta"
    alta(cliente)
    cuerpo = cliente.get(INCUBADORA).json()
    assert cuerpo["plantel"] == [] and cuerpo["maximo"] == db.MAXIMO_PLANTEL


# --- Sacar a otro --------------------------------------------------------------

def test_sacar_a_otro(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pelusa, nube, recluta = con_plantel(cliente)
    ir(cliente)
    hecho = sacar(cliente, nube.id)
    assert hecho.status_code == 200
    cuerpo = hecho.json()
    assert (cuerpo["ok"], cuerpo["clave"], cuerpo["mensaje"]) == (True, None, "Nube sale de la incubadora.")
    assert cuerpo["estado"]["gachamon"]["id"] == nube.id
    assert [(g["id"], g["activo"]) for g in cuerpo["incubadora"]["plantel"]] == [
        (nube.id, True), (pelusa.id, False), (recluta.id, False),
    ]
    assert activa().id == nube.id


def test_sacar_fuera_de_la_incubadora_es_un_409(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pelusa, nube, _ = con_plantel(cliente)
    for donde in (None, "tienda", "estadio"):
        if donde is not None:
            ir(cliente, donde)
        hecho = sacar(cliente, nube.id)
        assert hecho.status_code == 409, donde
        assert hecho.json()["detail"] == {
            "clave": "no_estas_ahi", "mensaje": "Para eso tienes que estar en la incubadora.",
        }
    assert activa().id == pelusa.id


def test_sacar_al_que_ya_es_el_activo_es_un_si(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pelusa, _, _ = con_plantel(cliente)
    ir(cliente)
    antes = db.por_id(pelusa.id)
    hecho = sacar(cliente, pelusa.id)
    assert hecho.status_code == 200
    cuerpo = hecho.json()
    assert (cuerpo["ok"], cuerpo["clave"], cuerpo["mensaje"]) == (True, None, "Pelusa ya es tu gachamon activo.")
    assert cuerpo["estado"]["gachamon"]["id"] == pelusa.id
    assert db.por_id(pelusa.id) == antes


def test_sacar_a_un_recluta_sin_nombre(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pelusa, _, recluta = con_plantel(cliente)
    ir(cliente)
    hecho = sacar(cliente, recluta.id)
    assert hecho.status_code == 200
    cuerpo = hecho.json()
    assert (cuerpo["ok"], cuerpo["clave"], cuerpo["mensaje"]) == (
        False, "sin_nombre", "Antes de sacarlo, ponle nombre.",
    )
    assert cuerpo["estado"]["gachamon"]["id"] == pelusa.id
    assert activa().id == pelusa.id and not db.por_id(recluta.id).activa


def test_sacar_a_uno_ajeno_es_no_esta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pelusa, _, _ = con_plantel(cliente)
    ajeno = db.crear(OTRA_PERSONA, G, "pulpo", "Ajeno", STATS, db.ahora_utc())
    ir(cliente)
    for gachamon_id in (ajeno.id, 999_999):
        hecho = sacar(cliente, gachamon_id)
        assert hecho.status_code == 200
        cuerpo = hecho.json()
        assert (cuerpo["ok"], cuerpo["clave"], cuerpo["mensaje"]) == (False, "no_esta", "Ese gachamon ya no está.")
    assert activa().id == pelusa.id
    assert db.criatura_activa(OTRA_PERSONA, G).id == ajeno.id


def test_si_el_activo_murio_al_sacar_el_cambio_sigue_y_el_estado_trae_al_difunto(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    vinculada_sin_gachamon(cliente)
    viejo = db.crear(LA_DE_DISCORD, G, "pollito", "Viejo", STATS, reloj.ahora)
    db.crear(LA_DE_DISCORD, G, "pulpo", "Nube", STATS, reloj.ahora, activa=False)
    bruma = db.crear(LA_DE_DISCORD, G, "pulpo", "Bruma", STATS, reloj.ahora, activa=False)
    ir(cliente)
    reloj.pasar(days=5)   # Viejo se muere de hambre, y nadie lo ha visto todavía
    cuerpo = sacar(cliente, bruma.id).json()
    assert (cuerpo["ok"], cuerpo["mensaje"]) == (True, "Bruma sale de la incubadora.")
    assert cuerpo["estado"]["difunto"]["nombre"] == "Viejo"
    assert cuerpo["estado"]["gachamon"]["id"] == bruma.id
    assert not db.por_id(viejo.id).viva


def test_sacar_con_un_id_que_no_es_entero_es_un_422(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pelusa, nube, _ = con_plantel(cliente)
    ir(cliente)
    for cuerpo in ({}, {"gachamon_id": str(nube.id)}, {"gachamon_id": None}, {"gachamon_id": True},
                   {"gachamon_id": float(nube.id)}, [nube.id], nube.id):
        hecho = cliente.post(SACAR, json=cuerpo, headers=ESCRIBIR)
        assert hecho.status_code == 422, cuerpo
        assert hecho.json()["detail"] == {"clave": "peticion", "mensaje": "La petición no se entiende."}
    assert cliente.post(SACAR, json={"gachamon_id": nube.id}).status_code == 403
    assert activa().id == pelusa.id


# --- Ponerle nombre a un recluta ---------------------------------------------------

def test_bautizar_a_un_recluta_desde_la_incubadora(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pelusa, _, recluta = con_plantel(cliente)
    ir(cliente)
    especie = esp.ESPECIES["pollito"].nombre
    hecho = bautizar(cliente, recluta.id, especie.upper())
    assert hecho.status_code == 422
    assert hecho.json()["detail"] == {"clave": "nombre", "mensaje": "Ese es el nombre de su especie. Ponle uno propio."}
    assert db.por_id(recluta.id).nombre == ""

    hecho = bautizar(cliente, recluta.id, " Bruma ")
    assert hecho.status_code == 200
    assert db.por_id(recluta.id).nombre == "Bruma" and not db.por_id(recluta.id).activa
    assert hecho.json()["gachamon"]["id"] == pelusa.id and activa().id == pelusa.id

    hecho = bautizar(cliente, recluta.id, "Otra")
    assert hecho.status_code == 409
    assert hecho.json()["detail"] == {"clave": "ya_bautizado", "mensaje": "Ese gachamon ya tiene nombre."}

    ajeno = db.crear(OTRA_PERSONA, G, "pulpo", "", STATS, db.ahora_utc(), activa=False)
    hecho = bautizar(cliente, ajeno.id, "Mío")
    assert hecho.status_code == 409
    assert hecho.json()["detail"] == {"clave": "no_esta", "mensaje": "Ese gachamon ya no está."}
    assert db.por_id(ajeno.id).nombre == "" and db.por_id(recluta.id).nombre == "Bruma"


def test_si_solo_queda_un_recluta_sin_nombre_se_puede_seguir(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    vinculada_sin_gachamon(cliente)
    db.crear(LA_DE_DISCORD, G, "pollito", "Viejo", STATS, reloj.ahora)
    recluta = db.crear(LA_DE_DISCORD, G, "pulpo", "", STATS, reloj.ahora, activa=False)
    otro = db.crear(LA_DE_DISCORD, G, "pollito", "", STATS, reloj.ahora, activa=False)
    reloj.pasar(days=5)   # Viejo se muere de hambre y nadie con nombre lo releva

    estado = cliente.get(ESTADO).json()
    assert estado["gachamon"] is None and estado["difunto"]["nombre"] == "Viejo"
    # El de menor id, con la cara con que se durmió.
    assert estado["sin_nombre"] == {
        "id": recluta.id, "nombre_especie": esp.ESPECIES["pulpo"].nombre, "retrato": el_retrato("pulpo"),
    }

    hecho = bautizar(cliente, recluta.id, "Bruma")
    assert hecho.status_code == 200
    estado = hecho.json()
    assert estado["gachamon"]["id"] == recluta.id and estado["gachamon"]["nombre"] == "Bruma"
    assert estado["sin_nombre"] is None
    assert activa().id == recluta.id and db.por_id(otro.id).nombre == ""


# --- El huevo ------------------------------------------------------------------

def test_el_huevo_con_un_recluta_lo_dice(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    recluta = db.crear(YO, G, "pulpo", "", STATS, db.ahora_utc(), activa=False)
    hecho = cliente.post(HUEVO, headers=ESCRIBIR)
    assert hecho.status_code == 409
    assert hecho.json()["detail"] == {
        "clave": "ya_tienes", "mensaje": "Antes, ponle nombre al gachamon que espera en la incubadora.",
    }
    assert [c.id for c in db.plantel(YO, G)] == [recluta.id]
