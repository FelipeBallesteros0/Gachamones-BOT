from dataclasses import replace
from datetime import timedelta

import db
import especies as esp
import identidad
import retrato
from ayudas_web import ESCRIBIR, PUEBLO, T0, alta, entrar, poner_reloj

ESTADO = "/gachamon/api/estado"
STATS = (10, 10, 10, 10)
G = str(PUEBLO)
YO = identidad.de_cuenta_web(1)
ANA_DISCORD = "222222222222222222"


def nace(usuario=YO, especie="pollito", nombre="Pelusa", ahora=T0, **mas):
    return db.crear(usuario, G, especie, nombre, STATS, ahora, **mas)


def test_sin_cuenta_no_hay_estado(cliente):
    assert cliente.get(ESTADO).status_code == 401
    entrar(cliente, 1)
    respuesta = cliente.get(ESTADO)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["clave"] == "sin_cuenta"


def test_recien_llegado_no_tiene_ni_avatar_ni_gachamon(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    entrar(cliente, 1)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    estado = cliente.get(ESTADO).json()
    assert estado["avatar"] is None and estado["gachamon"] is None
    assert estado["globos"] == [] and estado["difunto"] is None
    assert estado["saldos"] == {"monedas": 50, "gemas": 50}
    assert estado["persona"] == {"usuario": "felipe", "vinculada": False}
    assert estado["ahora"] == T0.isoformat()
    assert estado["hogar"] == "refugio"


def test_el_estado_completo_de_un_gachamon_recien_nacido(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    creado = nace(genero="hembra")
    estado = cliente.get(ESTADO).json()
    assert estado["avatar"]["nombre"] == "Feli"
    assert estado["gachamon"] == {
        "id": creado.id, "nombre": "Pelusa", "espera_nombre": False,
        "especie": "pollito", "nombre_especie": esp.ESPECIES["pollito"].nombre,
        "emoji": esp.ESPECIES["pollito"].emoji,
        "etapa": "bebe", "nombre_etapa": esp.nombre_etapa("bebe", "hembra"),
        "nivel": 1, "genero": "hembra",
        "barras": {"comida": 100, "animo": 100, "aseo": 100},
        "cara": "feliz", "desfallecido": False,
        "retrato": f"/gachamon/retrato/pollito/bebe/feliz/sin.png?v={retrato.version()}",
        "esperas": {"alimentar": 0, "jugar": 0, "entrenar": 0, "limpiar": 0, "acariciar": 0},
    }
    assert estado["globos"] and all(g["tipo"] == "suelta" for g in estado["globos"])
    assert set(estado) == {"ahora", "persona", "avatar", "saldos", "hogar", "gachamon", "difunto", "globos"}


def test_las_barras_bajan_con_el_reloj_y_leer_no_guarda(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    creado = nace()
    reloj.pasar(hours=10)
    barras = cliente.get(ESTADO).json()["gachamon"]["barras"]
    assert barras["comida"] < 100 and barras["animo"] < 100 and barras["aseo"] < 100
    assert all(isinstance(v, int) for v in barras.values())
    assert db.por_id(creado.id).actualizada_en == T0


def test_el_que_espera_nombre_lo_dice(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    nace(nombre="Piollito")
    assert cliente.get(ESTADO).json()["gachamon"]["espera_nombre"] is True


def test_las_esperas_salen_en_segundos_y_la_de_alimentar_cede_con_hambre(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    creado = nace()
    for accion in ("alimentar", "jugar", "acariciar"):
        db.poner_cooldown(creado.id, accion, T0)
    reloj.pasar(minutes=4, seconds=30)
    esperas = cliente.get(ESTADO).json()["gachamon"]["esperas"]
    assert esperas == {"alimentar": 18 * 60 + 30, "jugar": 24 * 60 + 30,
                       "entrenar": 0, "limpiar": 0, "acariciar": 14 * 60 + 30}
    db.guardar(replace(db.por_id(creado.id), hambre=30.0, actualizada_en=reloj.ahora))
    assert cliente.get(ESTADO).json()["gachamon"]["esperas"]["alimentar"] == 0


def test_con_necesidades_los_globos_piden_primero(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    creado = nace()
    db.guardar(replace(creado, limpieza=10.0))
    tipos = [g["tipo"] for g in cliente.get(ESTADO).json()["globos"]]
    assert tipos[0] == "necesidad" and "suelta" in tipos


def test_el_de_una_cuenta_web_se_queda_desfallecido_y_vivo(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    nace()
    reloj.pasar(days=5)
    gachamon = cliente.get(ESTADO).json()["gachamon"]
    assert gachamon["barras"]["comida"] == 0 and gachamon["desfallecido"] is True
    assert gachamon["cara"] == "mal"


def test_el_de_una_cuenta_vinculada_muere_y_la_web_lo_cuenta_una_vez(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    entrar(cliente, 2)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, G, T0)
    muerto = nace(usuario=ANA_DISCORD, nombre="Viejo")
    relevo = nace(usuario=ANA_DISCORD, especie="pulpo", nombre="Tinta", activa=False)
    reloj.pasar(days=5)

    estado = cliente.get(ESTADO).json()
    # Vivió lo que aguanta sin comer con salud 10: 62 horas, o sea dos días enteros.
    assert estado["difunto"] == {
        "nombre": "Viejo", "nombre_especie": esp.ESPECIES["pollito"].nombre, "dias": 2,
    }
    assert estado["gachamon"]["id"] == relevo.id
    assert db.por_id(muerto.id).causa_muerte == "hambre"
    assert cliente.get(ESTADO).json()["difunto"]["nombre"] == "Viejo"

    visto = cliente.post("/gachamon/api/difunto/visto", headers=ESCRIBIR)
    assert visto.status_code == 200 and visto.json()["difunto"] is None
    assert cliente.get(ESTADO).json()["difunto"] is None


def test_una_muerte_que_proceso_el_bot_tambien_se_cuenta(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    entrar(cliente, 2)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, G, T0)
    muerto = nace(usuario=ANA_DISCORD, nombre="Viejo")
    reloj.pasar(days=5)
    db.guardar(db.avanzar(db.por_id(muerto.id), reloj.ahora))   # lo que hace el bucle del bot

    estado = cliente.get(ESTADO).json()
    assert estado["difunto"]["nombre"] == "Viejo" and estado["gachamon"] is None


def test_los_muertos_de_antes_de_tener_cuenta_no_se_cuentan(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    antiguo = nace(usuario=ANA_DISCORD, nombre="Antiguo")
    db.guardar(replace(antiguo, muerta_en=T0, causa_muerte="hambre"))
    reloj.pasar(days=30)
    entrar(cliente, 2)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, G, reloj.ahora)
    assert cliente.get(ESTADO).json()["difunto"] is None


def test_activa_al_dia_es_repetible(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "relevo.db")
    db.inicializar()
    nace(usuario=ANA_DISCORD, nombre="Viejo")
    primero = nace(usuario=ANA_DISCORD, especie="pulpo", nombre="Uno", activa=False)
    nace(usuario=ANA_DISCORD, especie="pulpo", nombre="Dos", activa=False)
    tarde = T0 + timedelta(days=5)
    assert db.activa_al_dia(ANA_DISCORD, G, tarde).id == primero.id
    assert db.activa_al_dia(ANA_DISCORD, G, tarde).id == primero.id
    activas = [c for c in db.plantel(ANA_DISCORD, G) if c.activa]
    assert [c.id for c in activas] == [primero.id]


def test_cada_cual_ve_su_estado(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente, 1)
    nace(usuario=YO, nombre="Mío")
    alta(cliente, 2, nombre="Ana")
    estado = cliente.get(ESTADO).json()
    assert estado["gachamon"] is None and estado["avatar"]["nombre"] == "Ana"


def test_una_muerte_anterior_al_vinculo_no_es_noticia(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    entrar(cliente, 2)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    muerto = nace(usuario=ANA_DISCORD, nombre="Viejo")
    reloj.pasar(days=5)
    db.guardar(db.avanzar(db.por_id(muerto.id), reloj.ahora))
    reloj.pasar(days=5)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, G, reloj.ahora)
    assert cliente.get(ESTADO).json()["difunto"] is None


def test_marcar_visto_hasta_una_muerte_deja_pendiente_la_siguiente(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "dos.db")
    db.inicializar()
    db.crear_identidad_web(5, G, T0)
    yo = identidad.de_cuenta_web(5)
    primero = nace(usuario=yo, nombre="Uno")
    segundo = nace(usuario=yo, nombre="Dos", activa=False)
    m1, m2 = T0 + timedelta(days=1), T0 + timedelta(days=2)
    db.guardar(replace(primero, muerta_en=m1, causa_muerte="hambre"))
    db.guardar(replace(segundo, muerta_en=m2, causa_muerte="hambre"))
    assert db.difunto_pendiente(5).nombre == "Dos"
    db.marcar_difuntos_vistos(5, m1)
    assert db.difunto_pendiente(5).nombre == "Dos"
    db.marcar_difuntos_vistos(5, m2)
    assert db.difunto_pendiente(5) is None


def test_visto_sin_nada_pendiente_no_escribe(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    cliente.post("/gachamon/api/difunto/visto", headers=ESCRIBIR)
    with db.conectar() as con:
        fila = con.execute("SELECT difuntos_vistos_hasta FROM cuentas_web").fetchone()
    assert fila[0] is None


def test_visto_no_da_por_vista_una_muerte_que_se_descubre_en_la_misma_peticion(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    entrar(cliente, 2)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, G, T0)
    nace(usuario=ANA_DISCORD, nombre="Viejo")
    reloj.pasar(days=5)
    respuesta = cliente.post("/gachamon/api/difunto/visto", headers=ESCRIBIR).json()
    assert respuesta["difunto"]["nombre"] == "Viejo"


def test_difunto_visto_exige_cabecera_sesion_y_cuenta(cliente):
    url = "/gachamon/api/difunto/visto"
    assert cliente.post(url, headers=ESCRIBIR).status_code == 401
    entrar(cliente, 1)
    assert cliente.post(url).status_code == 403
    respuesta = cliente.post(url, headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["clave"] == "sin_cuenta"
