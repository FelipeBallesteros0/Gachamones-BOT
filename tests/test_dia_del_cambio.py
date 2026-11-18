"""El día del cambio: a cada quien su departamento, sus camas y lo que se le devuelve.

La base «de antes» se monta con filas escritas a mano en las tablas viejas, no
con las reglas de las casas, el refugio y el huerto, que se van.
"""
import logging
import random
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

import db
import economia
import huerto as hue
import logros as lgr

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(days=30)
STATS = (15, 15, 15, 15)
# Con lo que nace hoy un monedero.
MONEDAS_DE_ANTES = 50
GEMAS_DE_ANTES = 50
CAMBIO = economia.CAMBIO_DE_LA_VIVIENDA


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "dia_del_cambio.db")
    db.inicializar()


def borrar_la_marca(clave):
    with db.conectar() as con:
        con.execute("DELETE FROM cambios_hechos WHERE clave = ?", (clave,))


def marcas():
    with db.conectar() as con:
        return {f["clave"] for f in con.execute("SELECT clave FROM cambios_hechos")}


def el_cambio(ahora=T1, semilla=7):
    borrar_la_marca(CAMBIO)                 # por si acaso: db.inicializar() no la pone
    return economia.el_dia_del_cambio(ahora, random.Random(semilla))


def nacer(nombre, activa=True):
    return db.crear("u1", "g1", "pulpo", nombre, STATS, T0, activa=activa)


def escribir(sql, parametros=()):
    with db.conectar() as con:
        return con.execute(sql, parametros).lastrowid


def con_monedas(cuantas, usuario="u1", guild="g1"):
    with db.conectar() as con:
        economia._asegurar_monedero(con, usuario, guild)
        con.execute(
            "UPDATE monederos SET asciicoins = ? WHERE usuario_id = ? AND guild_id = ?",
            (cuantas, usuario, guild),
        )


def casa_de_antes(usuario, clave, guild="g1"):
    return escribir(
        "INSERT INTO casas_propias (usuario_id, guild_id, casa, comprada_en) VALUES (?, ?, ?, ?)",
        (usuario, guild, clave, T0.isoformat()),
    )


def vive_en(criatura, casa_id):
    escribir("UPDATE criaturas SET casa_id = ? WHERE id = ?", (casa_id, criatura.id))


def mueble_de_antes(usuario, clave, colocado):
    escribir(
        "INSERT INTO mobiliario (usuario_id, guild_id, mueble, colocado) VALUES (?, 'g1', ?, ?)",
        (usuario, clave, colocado),
    )


def plantado(usuario, casa_id, bancal, sembrado, cuando=T0):
    escribir(
        "INSERT INTO huerto (usuario_id, guild_id, casa_id, bancal, plantado_en, sembrado) "
        "VALUES (?, 'g1', ?, ?, ?, ?)",
        (usuario, casa_id, bancal, cuando.isoformat(), sembrado),
    )


def en_la_mochila(usuario, objeto, cuantos):
    escribir(
        "INSERT INTO inventario (usuario_id, guild_id, objeto, cantidad) VALUES (?, 'g1', ?, ?)",
        (usuario, objeto, cuantos),
    )


def regalo(para, objeto, de_nombre, recogido=0):
    escribir(
        "INSERT INTO buzon (para_usuario, guild_id, de_nombre, objeto, cuando, recogido) "
        "VALUES (?, 'g1', ?, ?, ?, ?)",
        (para, de_nombre, objeto, T0.isoformat(), recogido),
    )


def marcar_que_se_nombro_solo(criatura):
    escribir("UPDATE criaturas SET se_nombro_solo = 1 WHERE id = ?", (criatura.id,))


def dejar_con_hambre(criatura, cuanta):
    escribir("UPDATE criaturas SET hambre = ? WHERE id = ?", (cuanta, criatura.id))


def mochila(usuario, guild="g1"):
    return db.inventario(usuario, guild)


def filas(tabla):
    with db.conectar() as con:
        return [dict(f) for f in con.execute(f"SELECT * FROM {tabla}")]


def rompe(cuando):
    """Un disparador que aborta, como los de las pruebas del libro de cuentas."""
    with db.conectar() as con:
        con.execute(f"CREATE TRIGGER rompe {cuando} BEGIN SELECT RAISE(ABORT, 'falla a medias'); END")


def en_dos_hilos(funcion):
    """La corre dos veces a la vez; si alguna revienta, revienta aquí.

    La barrera suelta a los dos hilos juntos, para que las dos llamadas se
    solapen de verdad y no termine una antes de que empiece la otra.
    """
    barrera = threading.Barrier(2)

    def a_la_vez():
        barrera.wait(timeout=10)
        return funcion()

    with ThreadPoolExecutor(max_workers=2) as hilos:
        futuros = [hilos.submit(a_la_vez) for _ in range(2)]
        return [f.result() for f in futuros]


# --- El departamento y sus camas ----------------------------------------------

def test_a_cada_quien_su_departamento_con_una_cama_por_gachamon_mas_la_suya():
    for nombre in ("Ana", "Bea", "Cy"):
        nacer(nombre, activa=(nombre == "Ana"))
    assert el_cambio() == economia.ResumenDelCambio(personas=1, camas=4, monedas=0)
    d = db.departamento_leido("u1", "g1")
    assert (d.ancho, d.fondo, d.camas_puestas, d.guardadas) == (4, 4, 4, ())
    assert not db.hay_cama_libre("u1", "g1")


def test_a_quien_no_le_queda_ninguno_le_toca_lo_de_quien_empieza():
    con_monedas(5)                          # una persona con monedero y sin gachamones
    el_cambio()
    d = db.departamento_leido("u1", "g1")
    assert [(p.clave, p.puesta) for p in d.piezas] == [("cama_sencilla", True), ("cama_sencilla", False), ("puerta", True)]


def murio_antes():
    ana = nacer("Ana")
    escribir("UPDATE criaturas SET muerta_en = ?, causa_muerte = 'hambre' WHERE id = ?", (T0.isoformat(), ana.id))


LO_DE_CADA_QUIEN = {
    "criaturas": murio_antes,
    "monederos": lambda: con_monedas(5),
    "inventario": lambda: en_la_mochila("u1", "golosinas", 1),
    "casas_propias": lambda: casa_de_antes("u1", "pequena"),
    "mobiliario": lambda: mueble_de_antes("u1", "maceta", colocado=0),
    "huerto": lambda: plantado("u1", 1, 1, "semilla"),
    "hogar": lambda: escribir(
        "INSERT INTO hogar (usuario_id, guild_id, refugio_hasta) VALUES ('u1', 'g1', ?)", (T0.isoformat(),)),
    "avatares": lambda: escribir(
        "INSERT INTO avatares (usuario_id, guild_id, nombre, genero, piel, pelo, color_de_pelo, ropa, "
        "actualizado_en) VALUES ('u1', 'g1', 'Feli', 'macho', 'media', 'corto', 'castano', 'poleron', ?)",
        (T0.isoformat(),)),
    "cuentas_web": lambda: escribir(
        "INSERT INTO cuentas_web (rowino_uid, usuario_id, guild_id, creada_en) VALUES (1, 'u1', 'g1', ?)",
        (T0.isoformat(),)),
    "buzon": lambda: regalo("u1", "golosinas", "Ana"),
}


@pytest.mark.parametrize("tabla", LO_DE_CADA_QUIEN)
def test_basta_una_fila_de_lo_suyo_para_que_el_cambio_le_toque(tabla):
    LO_DE_CADA_QUIEN[tabla]()                # lo único que tiene; ningún gachamon vivo
    assert el_cambio().personas == 1
    d = db.departamento_leido("u1", "g1")
    assert [(p.clave, p.puesta) for p in d.piezas if p.clave == "cama_sencilla"] == [
        ("cama_sencilla", True), ("cama_sencilla", False)]
    assert db.carta_sin_ver("u1", "g1", CAMBIO)["vivos"] == 0
    assert [f["usuario_id"] for f in filas("monederos")] == ["u1"]


def test_veinticinco_gachamones_caben():
    for i in range(25):
        db.crear("u1", "g1", "pulpo", f"N{i}", STATS, T0, activa=(i == 0))
    el_cambio()
    d = db.departamento_leido("u1", "g1")
    assert (d.ancho, d.fondo, d.camas_puestas) == (8, 8, 26)


def test_si_no_cupieran_todas_las_camas_el_resto_queda_guardado():
    for i in range(40):
        db.crear("u1", "g1", "pulpo", f"N{i}", STATS, T0, activa=(i == 0))
    assert el_cambio().camas == 41
    d = db.departamento_leido("u1", "g1")
    assert (d.ancho, d.fondo, d.camas_puestas) == (8, 8, 32)
    assert [p.clave for p in d.guardadas] == ["cama_sencilla"] * 9


# --- Lo que se devuelve -------------------------------------------------------

def test_una_casa_mediana_o_grande_devuelve_140_mas():
    con_monedas(0)
    casa_de_antes("u1", "pequena"); casa_de_antes("u1", "mediana"); casa_de_antes("u1", "grande")
    el_cambio()
    assert economia.saldos("u1", "g1").asciicoins == 200 + 640 + 1340 == 2180
    assert db.carta_sin_ver("u1", "g1", CAMBIO)["monedas_por_casas"] == 2180


def test_las_casas_se_devuelven_enteras_y_fuera_del_tope():
    ana = nacer("Ana"); con_monedas(10)
    vive_en(ana, casa_de_antes("u1", "mediana")); casa_de_antes("u1", "grande")
    assert el_cambio().monedas == 640 + 1340
    assert economia.saldos("u1", "g1") == economia.Saldos(10 + 640 + 1340, GEMAS_DE_ANTES)
    assert filas("casas_propias") == [] == filas("operaciones_economia")
    assert db.por_id(ana.id).casa_id is None


def test_una_casa_de_clave_desconocida_no_paga_y_no_tumba_el_cambio():
    casa_de_antes("u1", "palacio"); con_monedas(0)
    el_cambio()
    assert economia.saldos("u1", "g1").asciicoins == 0 and filas("casas_propias") == []


def test_una_casa_de_clave_desconocida_deja_un_aviso_sin_ids(caplog):
    casa_de_antes("u1", "palacio"); con_monedas(0)
    with caplog.at_level(logging.WARNING, logger="economia"):
        el_cambio()
    avisos = [r.getMessage() for r in caplog.records if r.name == "economia"]
    assert len(avisos) == 1 and "palacio" in avisos[0] and "u1" not in avisos[0]
    assert db.carta_sin_ver("u1", "g1", CAMBIO)["casas"] == []


def de_una_especie_que_ya_no_existe(muerta):
    bicho = db.crear("u1", "g1", "pulpo", "Nube", STATS, T0, activa=not muerta)
    escribir("UPDATE criaturas SET especie = 'ya_no_existe' WHERE id = ?", (bicho.id,))
    if muerta:
        escribir("UPDATE criaturas SET muerta_en = ?, causa_muerte = 'hambre' WHERE id = ?", (T0.isoformat(), bicho.id))


@pytest.mark.parametrize("muerta", [True, False], ids=["muerta", "viva"])
def test_una_especie_desconocida_no_cuenta_como_rara_y_no_tumba_el_cambio(muerta):
    de_una_especie_que_ya_no_existe(muerta); reclutados(1)
    assert el_cambio().personas == 1
    assert CAMBIO in marcas() and [f["usuario_id"] for f in filas("departamentos")] == ["u1"]
    assert db.carta_sin_ver("u1", "g1", CAMBIO)["gemas_por_medallas"] == valen("domador")


def test_cada_ticket_del_refugio_vuelve_en_40_monedas():
    con_monedas(0); en_la_mochila("u1", "ticket_refugio", 2)
    el_cambio()
    assert economia.saldos("u1", "g1").asciicoins == 80 and "ticket_refugio" not in mochila("u1")


def test_quien_no_tenia_nada_que_devolver_conserva_su_monedero():
    nacer("Ana"); con_monedas(37)
    el_cambio()
    assert economia.saldos("u1", "g1") == economia.Saldos(37, GEMAS_DE_ANTES)


def test_a_quien_ya_jugaba_el_cambio_le_deja_su_monedero_creado():
    nacer("Ana")                                       # jugaba, y todavía no tenía fila de monedero
    assert filas("monederos") == []
    el_cambio()
    assert [(f["usuario_id"], f["asciicoins"], f["asciigems"]) for f in filas("monederos")] == [("u1", MONEDAS_DE_ANTES, GEMAS_DE_ANTES)]


def monedero(usuario, guild="g1"):
    """Sus monedas, sus gemas y con cuánto nació su monedero; None si no tiene."""
    with db.conectar() as con:
        fila = con.execute(
            "SELECT asciicoins, asciigems, partida FROM monederos WHERE usuario_id = ? AND guild_id = ?",
            (usuario, guild),
        ).fetchone()
    return None if fila is None else tuple(fila)


def test_el_dia_del_cambio_le_deja_cincuenta_a_quien_ya_estaba_sin_monedero():
    LO_DE_CADA_QUIEN["avatares"]()                     # sólo un avatar: ni gachamon ni monedero
    assert monedero("u1") is None
    el_cambio()
    assert monedero("u1") == (MONEDAS_DE_ANTES, GEMAS_DE_ANTES, 50)


def test_asegurar_a_quien_ya_estaba_da_cincuenta_aunque_el_cambio_ya_ocurriera():
    el_cambio()                                        # en una base vacía sólo deja su marca
    assert CAMBIO in marcas()
    with db.conectar() as con:
        economia._asegurar_monedero(con, "u1", "g1", ya_estaba=True)
        economia._asegurar_monedero(con, "u2", "g1")
    assert monedero("u1") == (50, 50, 50)
    assert monedero("u2") == (0, 0, 0)


def test_correr_el_cambio_otra_vez_no_le_da_nada_a_nadie():
    LO_DE_CADA_QUIEN["avatares"]()                     # u1 estaba, sin monedero
    con_monedas(37, usuario="u2")                      # u2 estaba, con el suyo
    el_cambio()
    economia.saldos("u3", "g1")                        # u3 empieza después: nace en cero
    antes = {f["usuario_id"]: (f["asciicoins"], f["asciigems"], f["partida"]) for f in filas("monederos")}
    assert antes == {"u1": (50, 50, 50), "u2": (37, 50, 50), "u3": (0, 0, 0)}
    assert economia.el_dia_del_cambio(T1 + timedelta(hours=1)) == economia.ResumenDelCambio()
    economia.poner_al_dia(T1 + timedelta(hours=2))     # y el arranque entero, migración incluida
    assert {f["usuario_id"]: (f["asciicoins"], f["asciigems"], f["partida"]) for f in filas("monederos")} == antes


def test_vale_para_cada_servidor_por_separado():
    casa_de_antes("u1", "pequena", guild="g1"); casa_de_antes("u1", "grande", guild="g2")
    el_cambio()
    assert (economia.saldos("u1", "g1").asciicoins, economia.saldos("u1", "g2").asciicoins) == (MONEDAS_DE_ANTES + 200, MONEDAS_DE_ANTES + 1340)


# --- Lo que se guarda, se cosecha y se entrega ----------------------------------

def test_los_muebles_de_antes_quedan_guardados():
    mueble_de_antes("u1", "chimenea", colocado=1); mueble_de_antes("u1", "cama", colocado=0)
    el_cambio()
    d = db.departamento_leido("u1", "g1")
    assert sorted(p.clave for p in d.guardadas) == ["cama", "cama_sencilla", "chimenea"]
    assert d.camas_puestas == 1 and filas("mobiliario") == []


def test_lo_plantado_se_cosecha_solo_aunque_no_estuviera_maduro():
    casa = casa_de_antes("u1", "pequena")
    plantado("u1", casa, 1, "poroto_rojo", cuando=T1 - timedelta(minutes=1))
    el_cambio()
    hay = mochila("u1")
    assert 2 <= hay.get("poroto_rojo", 0) + hay.get("poroto_arcoiris", 0) <= 4
    assert hay.get("poroto_arcoiris", 0) <= 1 and filas("huerto") == []


class SiempreArcoiris(random.Random):
    """Saca el arcoíris en cada cosecha; el color y el lote siguen con la semilla."""

    def random(self):
        return 0.0


def test_un_arcoiris_sustituye_a_uno_del_lote_y_la_carta_cuenta_lo_cosechado():
    casa = casa_de_antes("u1", "pequena"); plantado("u1", casa, 1, "poroto_rojo")
    lote = hue.tirar_cuantos(SiempreArcoiris(7))      # el color se hereda: lo primero que se tira es el lote
    borrar_la_marca(CAMBIO)
    economia.el_dia_del_cambio(T1, SiempreArcoiris(7))
    cosecha = db.carta_sin_ver("u1", "g1", CAMBIO)["cosecha"]
    assert cosecha == {"poroto_rojo": lote - 1, "poroto_arcoiris": 1} == mochila("u1")


def test_los_regalos_del_buzon_llegan_solos_y_un_ticket_regalado_tambien_se_devuelve():
    con_monedas(0)
    regalo("u1", "golosinas", "Ana"); regalo("u1", "ticket_refugio", "Ana"); regalo("u1", "golosinas", "Bea", recogido=1)
    el_cambio()
    assert mochila("u1") == {"golosinas": 1} and economia.saldos("u1", "g1").asciicoins == 40
    assert db.buzon_de("u1", "g1") == []


def test_el_reloj_de_todos_parte_del_dia_del_cambio():
    ana = nacer("Ana"); dejar_con_hambre(ana, 60.0)    # guardada por última vez en T0, hace 30 días
    el_cambio()
    ahora_es = db.por_id(ana.id)
    assert (ahora_es.actualizada_en, ahora_es.hambre) == (T1, 60.0)


# --- La carta del alcalde -----------------------------------------------------

def test_la_carta_cuenta_lo_que_le_toco_a_cada_quien():
    ana = nacer("Ana"); marcar_que_se_nombro_solo(ana)
    casa = casa_de_antes("u1", "mediana"); mueble_de_antes("u1", "maceta", colocado=1)
    en_la_mochila("u1", "ticket_refugio", 1); regalo("u1", "golosinas", "Bea")
    el_cambio()
    assert db.carta_sin_ver("u1", "g1", CAMBIO) == {
        "ancho": 3, "fondo": 3, "camas": 2, "vivos": 1, "casas": ["mediana"], "monedas_por_casas": 640,
        "muebles": 1, "cosecha": {}, "tickets": 1, "monedas_por_tickets": 40, "regalos": 1,
        "gemas_por_medallas": 0, "nombres": [{"especie": "pulpo", "nombre": "Ana"}],
    }
    db.marcar_carta_vista("u1", "g1", CAMBIO, T1)
    assert db.carta_sin_ver("u1", "g1", CAMBIO) is None


def test_la_carta_nombra_solo_a_los_vivos_que_se_pusieron_el_nombre_solos():
    nacer("Ana")                                       # el nombre se lo puso su dueño
    bea = nacer("Bea", activa=False); marcar_que_se_nombro_solo(bea)
    cy = nacer("Cy", activa=False); marcar_que_se_nombro_solo(cy)
    escribir("UPDATE criaturas SET muerta_en = ? WHERE id = ?", (T0.isoformat(), cy.id))
    el_cambio()
    carta = db.carta_sin_ver("u1", "g1", CAMBIO)
    assert carta["nombres"] == [{"especie": "pulpo", "nombre": "Bea"}] and carta["vivos"] == 2


def test_una_carta_vista_se_queda_con_la_primera_vez_que_se_vio():
    con_monedas(0)
    el_cambio()
    db.marcar_carta_vista("u1", "g1", CAMBIO, T1)
    db.marcar_carta_vista("u1", "g1", CAMBIO, T1 + timedelta(days=1))
    assert [(f["carta"], f["vista_en"]) for f in filas("cartas")] == [(CAMBIO, T1.isoformat())]


# --- Las medallas ganadas y sin cobrar ------------------------------------------

def con_gemas(cuantas, usuario="u1", guild="g1"):
    with db.conectar() as con:
        economia._asegurar_monedero(con, usuario, guild)
        con.execute(
            "UPDATE monederos SET asciigems = ? WHERE usuario_id = ? AND guild_id = ?",
            (cuantas, usuario, guild),
        )


def reclutados(cuantos, usuario="u1"):
    """Su marcador de salvajes convencidos, sin haber cobrado lo que vale."""
    with db.conectar() as con:
        db.apuntar_persona_en(con, usuario, "g1", lgr.RECLUTADOS, cuantos)


def una_rara(muerta, usuario="u1"):
    rara = db.crear(usuario, "g1", "dragoncito", "Rara", STATS, T0, activa=False)
    if muerta:
        escribir("UPDATE criaturas SET muerta_en = ?, causa_muerte = 'hambre' WHERE id = ?", (T0.isoformat(), rara.id))


def ya_cobrada(clave, usuario="u1"):
    with db.conectar() as con:
        db.anotar_logro_de_persona_en(con, usuario, "g1", clave, T0)


def valen(*claves):
    return sum(lgr.POR_CLAVE[clave].gemas for clave in claves)


def gemas(usuario="u1"):
    return economia.saldos(usuario, "g1").asciigems


LAS_TRES = ("domador", "flautista", "uno_entre_veinticinco")


@pytest.mark.parametrize("muerta", [False, True], ids=["viva", "muerta"])
def test_el_cambio_paga_las_medallas_de_persona_ganadas_y_sin_cobrar(muerta):
    nacer("Ana"); una_rara(muerta); reclutados(10); con_gemas(12)
    el_cambio()
    assert gemas() == 12 + valen(*LAS_TRES)
    assert db.logros_de_persona("u1", "g1") == {clave: T1 for clave in LAS_TRES}
    assert db.carta_sin_ver("u1", "g1", CAMBIO)["gemas_por_medallas"] == gemas() - 12 == valen(*LAS_TRES)


def test_quien_no_tenia_medallas_pendientes_queda_como_quedaba():
    nacer("Ana"); con_gemas(12)                                    # nunca ganó ninguna
    db.crear("u2", "g1", "pulpo", "Bea", STATS, T0); reclutados(1, usuario="u2")
    ya_cobrada("domador", usuario="u2"); con_gemas(30, usuario="u2")   # la ganó y ya la cobró
    el_cambio()
    assert (gemas("u1"), gemas("u2")) == (12, 30)
    assert db.logros_de_persona("u1", "g1") == {} and db.logros_de_persona("u2", "g1") == {"domador": T0}
    assert [db.carta_sin_ver(u, "g1", CAMBIO)["gemas_por_medallas"] for u in ("u1", "u2")] == [0, 0]


def test_las_ya_anotadas_no_se_vuelven_a_pagar():
    nacer("Ana"); reclutados(10); ya_cobrada("domador"); con_gemas(12)
    el_cambio()
    assert gemas() == 12 + valen("flautista")
    assert db.logros_de_persona("u1", "g1") == {"domador": T0, "flautista": T1}
    assert db.carta_sin_ver("u1", "g1", CAMBIO)["gemas_por_medallas"] == valen("flautista")


def test_tambien_cobra_quien_no_tiene_ningun_gachamon_vivo():
    una_rara(muerta=True); reclutados(1)                           # ni un vivo, y todavía sin monedero
    assert monedero("u1") is None
    el_cambio()
    assert monedero("u1") == (MONEDAS_DE_ANTES, GEMAS_DE_ANTES + valen("domador", "uno_entre_veinticinco"), 50)
    carta = db.carta_sin_ver("u1", "g1", CAMBIO)
    assert (carta["vivos"], carta["gemas_por_medallas"]) == (0, valen("domador", "uno_entre_veinticinco"))


def test_correr_el_cambio_otra_vez_no_paga_las_medallas_otra_vez():
    nacer("Ana"); una_rara(muerta=True); reclutados(10); con_gemas(12)
    el_cambio()
    antes = (monedero("u1"), db.logros_de_persona("u1", "g1"))
    assert antes == ((MONEDAS_DE_ANTES, 12 + valen(*LAS_TRES), 50), {clave: T1 for clave in LAS_TRES})
    assert economia.el_dia_del_cambio(T1 + timedelta(hours=1)) == economia.ResumenDelCambio()
    economia.poner_al_dia(T1 + timedelta(hours=2))                 # y el arranque entero
    assert (monedero("u1"), db.logros_de_persona("u1", "g1")) == antes


def test_despues_del_cambio_pedir_las_medallas_no_paga_nada_mas():
    nacer("Ana"); una_rara(muerta=False); reclutados(10); con_gemas(12)
    el_cambio()
    assert economia.pagar_logros_de_persona("u1", "g1", T1 + timedelta(days=1)) == economia.ReciboLogros()
    assert gemas() == 12 + valen(*LAS_TRES)


@pytest.mark.parametrize("donde", ["BEFORE INSERT ON logros_persona", "BEFORE INSERT ON cartas"])
def test_si_el_cambio_falla_a_medias_las_medallas_tampoco_quedan_pagadas(donde):
    nacer("Ana"); una_rara(muerta=True); reclutados(10); con_gemas(12)
    con_monedas(0); casa_de_antes("u1", "pequena")
    rompe(donde)
    borrar_la_marca(CAMBIO)
    with pytest.raises(sqlite3.DatabaseError):
        economia.el_dia_del_cambio(T1, random.Random(1))
    assert economia.saldos("u1", "g1") == economia.Saldos(0, 12) and db.logros_de_persona("u1", "g1") == {}
    assert len(filas("casas_propias")) == 1 and filas("departamentos") == [] and CAMBIO not in marcas()


# --- Una sola vez, y entero o nada ----------------------------------------------

def test_el_cambio_corre_una_sola_vez():
    casa_de_antes("u1", "pequena"); con_monedas(0)
    el_cambio()
    casa_de_antes("u1", "grande")                      # si corriera otra vez, la devolvería
    assert economia.el_dia_del_cambio(T1 + timedelta(hours=1)) == economia.ResumenDelCambio()
    assert economia.saldos("u1", "g1").asciicoins == 200 and len(filas("casas_propias")) == 1


def test_dos_arranques_a_la_vez_hacen_un_solo_cambio():      # dos hilos, como tests/test_db.py
    casa_de_antes("u1", "pequena"); con_monedas(0); borrar_la_marca(CAMBIO)
    hechos = en_dos_hilos(lambda: economia.el_dia_del_cambio(T1, random.Random(1)))
    assert economia.saldos("u1", "g1").asciicoins == 200 and len(db.departamento_leido("u1", "g1").piezas) == 3   # dos camas y su puerta
    assert sorted(h.personas for h in hechos) == [0, 1]


def test_si_algo_falla_a_medias_no_queda_nada_hecho_ni_la_marca():
    casa_de_antes("u1", "pequena"); con_monedas(0)
    rompe("BEFORE INSERT ON cartas")
    borrar_la_marca(CAMBIO)
    with pytest.raises(sqlite3.DatabaseError):
        economia.el_dia_del_cambio(T1, random.Random(1))
    assert economia.saldos("u1", "g1").asciicoins == 0 and len(filas("casas_propias")) == 1
    assert filas("departamentos") == [] and CAMBIO not in marcas()


def test_si_alguien_ya_tuviera_departamento_no_se_le_suman_camas_y_no_queda_nada_a_medias():
    casa_de_antes("u1", "pequena"); con_monedas(0)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db._departamento_en(con, "u1", "g1", T0)
    with pytest.raises(RuntimeError):
        el_cambio()
    assert economia.saldos("u1", "g1").asciicoins == 0 and len(filas("casas_propias")) == 1
    assert len(db.departamento_leido("u1", "g1").piezas) == 3 and CAMBIO not in marcas()   # dos camas y la puerta


def test_si_ya_habia_departamentos_sin_la_marca_no_se_hace_nada_y_se_dice():
    casa_de_antes("u1", "pequena"); con_monedas(0)
    db.departamento_de("u2", "g1", T0)                 # de otra persona, que no tiene nada más
    with pytest.raises(RuntimeError, match="no se hizo nada") as error:
        el_cambio()
    assert str(error.value) == (
        "El día del cambio encontró departamentos ya creados y sin su marca: no se hizo nada. "
        "La base no está como se esperaba; restaura la copia de antes o averigua de dónde "
        "salieron antes de arrancar.")
    assert len(filas("casas_propias")) == 1 and economia.saldos("u1", "g1").asciicoins == 0
    assert CAMBIO not in marcas() and db.carta_sin_ver("u1", "g1", CAMBIO) is None


def test_en_una_base_nueva_no_hay_a_quien_cambiar():
    assert el_cambio() == economia.ResumenDelCambio()


# --- El arranque ----------------------------------------------------------------

def test_el_arranque_hace_el_cambio():
    casa_de_antes("u1", "pequena"); con_monedas(0); borrar_la_marca(CAMBIO)
    economia.poner_al_dia(T1)
    assert economia.saldos("u1", "g1").asciicoins == 200


def test_el_arranque_apunta_las_tres_cifras_del_cambio_y_ningun_id(caplog):
    casa_de_antes("u1", "pequena"); con_monedas(0); borrar_la_marca(CAMBIO)
    with caplog.at_level(logging.INFO, logger="economia"):
        economia.poner_al_dia(T1)
        economia.poner_al_dia(T1 + timedelta(hours=1))    # el segundo no cambia a nadie: no apunta
    lineas = [r for r in caplog.records if r.name == "economia"]
    assert [r.args for r in lineas] == [(1, 2, 200)]
    assert "u1" not in lineas[0].getMessage()
    assert lineas[0].levelno >= logging.WARNING        # la web no configura el registro: un info se perdería


def test_el_dia_del_cambio_deja_a_cada_quien_su_puerta_con_la_entrada_libre():
    import departamento as dep
    for n in range(3):
        nacer(f"G{n}", activa=(n == 0))
    el_cambio()
    d = db.departamento_leido("u1", "g1")
    puertas = [p for p in d.piezas if p.clave == dep.PUERTA]
    assert len(puertas) == 1 and puertas[0].puesta
    tapadas = {c for p in d.puestas if dep.MUEBLES[p.clave].capa == dep.BULTO
               for c in dep.huella(dep.MUEBLES[p.clave], p.x, p.y, p.giro)}
    assert dep.frente_a(puertas[0].x, puertas[0].y) not in tapadas


def test_el_dia_del_cambio_mueve_la_puerta_al_otro_lado_si_las_camas_tapan_toda_la_pared_izquierda():
    import departamento as dep
    for n in range(6):
        nacer(f"G{n}", activa=(n == 0))
    el_cambio()
    d = db.departamento_leido("u1", "g1")
    assert (d.ancho, d.fondo, d.camas_puestas) == (5, 4, 7)
    assert any((p.x, p.y) == (0, 3) for p in d.puestas if p.clave == "cama_sencilla")   # tapa la entrada de (-1, 3)
    puertas = [p for p in d.piezas if p.clave == dep.PUERTA]
    assert [(p.x, p.y) for p in puertas] == [(4, -1)]


def test_con_21_o_24_vivos_el_alcalde_no_deja_la_entrada_tapada_por_una_de_sus_camas():
    import departamento as dep
    vivos = {"u1": 21, "u2": 24}             # con esos, las camas cubren la columna 0 y la fila 0
    for usuario, cuantos in vivos.items():
        for i in range(cuantos):
            db.crear(usuario, "g1", "pulpo", f"N{i}", STATS, T0, activa=(i == 0))
    el_cambio()
    for usuario, cuantos in vivos.items():
        d = db.departamento_leido(usuario, "g1")
        assert d.camas_puestas == cuantos + 1
        puertas = [p for p in d.piezas if p.clave == dep.PUERTA]
        assert len(puertas) == 1 and puertas[0].puesta
        bajo_las_camas = {c for p in d.puestas if dep.MUEBLES[p.clave].cama
                          for c in dep.huella(dep.MUEBLES[p.clave], p.x, p.y, p.giro)}
        assert dep.frente_a(puertas[0].x, puertas[0].y) not in bajo_las_camas
