"""El bote diario de asciicoins y lo que se encuentra en las aventuras.

Antes de esto no había tope en monedas: había topes por **número de eventos**
—12 cuidados, 1 evolución, 3 competencias— y los 40 al día eran un número
derivado. Ahora el techo es uno solo y se puede decir en una frase, y por eso lo
que te encuentras por el camino puede caber dentro o no caber.
"""
import random
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import aventura as av
import db
import economia
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "bote.db")
    db.inicializar()


def nacer(nombre="Kuro"):
    return db.crear("u1", "g1", "pulpo", nombre, STATS, T0)


def monedas(usuario="u1"):
    return economia.saldos(usuario, "g1").asciicoins


def gemas(usuario="u1"):
    return economia.saldos(usuario, "g1").asciigems


def ganado_hoy(usuario="u1", fecha="2026-01-01"):
    with db.conectar() as con:
        return economia._ganado_hoy(con, usuario, "g1", fecha)


def cuidar(evento, accion=sim.ALIMENTAR, cuando=T0):
    return economia.ejecutar_cuidado(evento, "u1", "g1", accion, cuando)


def llenar_el_bote(deja_libre=0, fecha="2026-01-01"):
    """Deja el bote a tope, o con ese hueco libre.

    Se apunta una fila de competencia a mano en vez de jugar de verdad: ninguna
    actividad sola llega a 20 —el tope de cuidados corta en 12— y encadenarlas
    llenaría el test de ruido. Y **ya no se puede llenar con hallazgos**, que es
    como se hacía antes: desde que salieron del bote no cuentan.
    """
    cuanto = economia.TOPE_DIARIO_ASCIICOINS - deja_libre
    with db.conectar() as con:
        con.execute(
            "INSERT INTO operaciones_economia "
            "(evento_id, usuario_id, guild_id, tipo, fecha_utc, resultado, "
            "delta_asciicoins, solicitud) "
            "VALUES ('lleno', 'u1', 'g1', 'competencia', ?, 'acreditada', ?, '{}')",
            (fecha, cuanto),
        )
        con.execute(
            "UPDATE monederos SET asciicoins = asciicoins + ? "
            "WHERE usuario_id = 'u1' AND guild_id = 'g1'", (cuanto,),
        )
        con.commit()
    return cuanto


def filas_del_ledger(tipo=None):
    with db.conectar() as con:
        sql = "SELECT * FROM operaciones_economia"
        if tipo:
            sql += f" WHERE tipo = '{tipo}'"
        return [dict(f) for f in con.execute(sql).fetchall()]


# --- El bote --------------------------------------------------------------

def test_el_bote_es_uno_solo_para_lo_que_se_gana_jugando():
    """Cuidar, evolucionar y competir salen del mismo sitio: la primera que
    llegue a 20 deja secas a las demás. Los hallazgos ya no, y por eso este
    test se mide con cuidados y no con ellos, como se medía antes."""
    nacer()
    for i in range(economia.TOPE_CUIDADOS):
        cuidar(f"c{i}", cuando=T0 + timedelta(hours=i))

    assert ganado_hoy() == economia.TOPE_CUIDADOS      # 12 de los 20


def test_lo_que_te_encuentras_no_toca_el_bote():
    """**Lo pedido.** Un hallazgo no es un sueldo: es un golpe de suerte, y
    antes se cobraba dos veces mal —si habías llegado al tope no daba nada, y si
    no, te comía sitio de lo que ibas a ganar después—."""
    nacer()
    for i in range(economia.TOPE_CUIDADOS):
        cuidar(f"c{i}", cuando=T0 + timedelta(hours=i))
    antes_bote, antes_saldo = ganado_hoy(), monedas()

    recibo = economia.otorgar_hallazgo("v1", "u1", "g1", 10, 0, T0)

    assert recibo.monedas == 10, "se cobra entero, no lo que quepa"
    assert monedas() == antes_saldo + 10
    assert ganado_hoy() == antes_bote, "y no le quita sitio a lo que se gane después"


def test_se_cobra_lo_que_quepa_y_no_todo_o_nada():
    """Con sitio para 3 y un premio de 10, entran 3. Es lo que espera quien lee
    «hasta 20 al día», y la fila queda `acreditada`, no `topada`.

    Se mide con la evolución, que premia 10 de golpe: los hallazgos ya no valen
    para esto porque no pasan por el bote.
    """
    nacer()
    llenar_el_bote(deja_libre=3)

    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        delta, _, topada = economia._registrar_recompensa(
            con, "evo1", "u1", "g1", "2026-01-01", "evolucion",
            economia.PREMIO_EVOLUCION, economia.TOPE_EVOLUCIONES, "{}",
        )
        con.commit()

    assert delta == 3 and not topada, "entra lo que cabe, y la fila es acreditada"
    assert ganado_hoy() == economia.TOPE_DIARIO_ASCIICOINS


def test_el_bote_se_renueva_cada_dia_utc():
    nacer()
    llenar_el_bote()
    lleno = monedas()

    manana = T0 + timedelta(days=1)
    recibo = economia.otorgar_hallazgo("v1", "u1", "g1", 7, 0, manana)

    assert recibo.monedas == 7
    assert monedas() == lleno + 7


def test_gastar_no_devuelve_sitio_en_el_bote():
    """El bote mide lo **ganado**, no lo que tienes: si comprar liberara hueco,
    bastaría con comprar y vender para saltárselo."""
    nacer()
    llenar_el_bote()

    import objetos as obj
    economia.comprar("compra1", "u1", "g1", obj.CATALOGO["golosinas"], T0)

    assert ganado_hoy() == economia.TOPE_DIARIO_ASCIICOINS


def test_el_bote_es_de_cada_persona_y_servidor():
    nacer()
    llenar_el_bote()

    assert ganado_hoy("u2") == 0 and ganado_hoy("u1", "2026-01-02") == 0


# --- Los hallazgos ---------------------------------------------------------

def test_ni_las_monedas_ni_las_gemas_del_hallazgo_miran_el_bote():
    """Las gemas nunca lo miraron —otra moneda, otra economía— y desde este
    cambio las monedas del hallazgo tampoco: con el bote lleno caen las dos."""
    nacer()
    llenar_el_bote()
    antes_gemas, antes_monedas = gemas(), monedas()

    recibo = economia.otorgar_hallazgo("v1", "u1", "g1", 10, 4, T0)

    assert (recibo.monedas, recibo.gemas) == (10, 4)
    assert gemas() == antes_gemas + 4
    assert monedas() == antes_monedas + 10
    assert ganado_hoy() == economia.TOPE_DIARIO_ASCIICOINS, "el bote no se mueve"


def test_el_mismo_viaje_no_paga_dos_veces():
    """Ni monedas ni gemas, aunque éstas no tengan ledger propio: van dentro de
    la misma transacción y las tapa la clave primaria del ledger."""
    nacer()
    primero = economia.otorgar_hallazgo("v1", "u1", "g1", 6, 3, T0)
    saldo, reserva = monedas(), gemas()

    segundo = economia.otorgar_hallazgo("v1", "u1", "g1", 6, 3, T0)

    assert primero.monedas == 6 and primero.gemas == 3
    assert segundo.replay
    assert (monedas(), gemas()) == (saldo, reserva)
    assert len(filas_del_ledger("aventura")) == 1


def test_un_viaje_sin_nada_no_toca_el_ledger():
    """Lo normal es no encontrarse nada: 96 de cada 100 veces. Escribir una fila
    por cada aventura llenaría el ledger de ruido."""
    nacer()
    recibo = economia.otorgar_hallazgo("v1", "u1", "g1", 0, 0, T0)

    assert not recibo.monedas and not recibo.gemas and not recibo.replay
    assert filas_del_ledger("aventura") == []


# --- Las tiradas -----------------------------------------------------------

def test_las_tasas_salen_a_lo_pedido():
    """Medido y no calculado: 4 % para las monedas y 0,5 % para las gemas, con
    un margen que aguanta la aleatoriedad de 200 000 tiradas."""
    rng = random.Random(20260802)
    n = 200_000
    con_monedas = sum(1 for _ in range(n) if av.tirar_monedas(rng))
    con_gemas = sum(1 for _ in range(n) if av.tirar_gemas(rng))

    assert 3.7 <= con_monedas / n * 100 <= 4.3
    assert 0.4 <= con_gemas / n * 100 <= 0.6


def test_lo_encontrado_cae_dentro_de_su_rango():
    rng = random.Random(7)
    monedas_vistas = {av.tirar_monedas(rng) for _ in range(20_000)} - {0}
    gemas_vistas = {av.tirar_gemas(rng) for _ in range(200_000)} - {0}

    assert monedas_vistas == set(range(1, 11))
    assert gemas_vistas == set(range(1, 6))


def test_los_hallazgos_no_pueden_llenar_el_bote_ellos_solos():
    """La aventura tiene 37 min de espera, así que caben 38 al día. Al 4 % con
    1-10 eso son ~9 asciicoins: queda sitio de sobra para cuidar y competir, que
    es justo por lo que la probabilidad bajó del 10 % al 4 %.
    """
    rng = random.Random(20260802)
    n = 200_000
    por_aventura = sum(av.tirar_monedas(rng) for _ in range(n)) / n
    al_dia = timedelta(days=1) / sim.COOLDOWNS[sim.AVENTURA]

    assert por_aventura * al_dia < economia.TOPE_DIARIO_ASCIICOINS / 2


# --- La migración del ledger ----------------------------------------------

LEDGER_VIEJO = """
CREATE TABLE operaciones_economia (
    evento_id        TEXT NOT NULL,
    usuario_id       TEXT NOT NULL,
    guild_id         TEXT NOT NULL,
    tipo             TEXT NOT NULL CHECK (tipo IN ('cuidado','evolucion','competencia','compra')),
    fecha_utc        TEXT NOT NULL,
    resultado        TEXT NOT NULL CHECK (resultado IN ('acreditada','topada','comprada','saldo_insuficiente')),
    delta_asciicoins INTEGER NOT NULL,
    solicitud        TEXT NOT NULL CHECK (length(solicitud) > 0),
    CHECK (
        (resultado = 'acreditada' AND tipo IN ('cuidado','evolucion','competencia') AND delta_asciicoins > 0) OR
        (resultado = 'topada' AND tipo IN ('cuidado','evolucion','competencia') AND delta_asciicoins = 0) OR
        (resultado = 'comprada' AND tipo = 'compra' AND delta_asciicoins < 0) OR
        (resultado = 'saldo_insuficiente' AND tipo = 'compra' AND delta_asciicoins = 0)
    ),
    PRIMARY KEY (evento_id, usuario_id, guild_id, tipo)
)
"""

VIEJAS = [
    ("e1", "u1", "g1", "cuidado", "2026-01-01", "acreditada", 1, "alimentar"),
    ("e2", "u1", "g1", "competencia", "2026-01-01", "acreditada", 6, "{}"),
    ("e3", "u1", "g1", "cuidado", "2026-01-01", "topada", 0, "jugar"),
    ("e4", "u2", "g1", "compra", "2026-01-02", "comprada", -8, "golosinas"),
]


def _con_ledger_viejo():
    """Deja la base con la forma de antes y filas dentro."""
    with db.conectar() as con:
        con.execute("DROP TABLE operaciones_economia")
        con.execute(LEDGER_VIEJO)
        con.executemany(
            "INSERT INTO operaciones_economia VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            VIEJAS,
        )
        con.commit()


def test_la_migracion_conserva_todas_las_filas():
    """Es la primera migración del proyecto que copia un ledger con datos
    dentro, así que lo que importa es que no se pierda ni cambie ninguna."""
    _con_ledger_viejo()

    db.inicializar()

    assert sorted(
        tuple(f.values()) for f in filas_del_ledger()
    ) == sorted(VIEJAS)


def test_la_migracion_admite_el_tipo_nuevo():
    _con_ledger_viejo()
    with pytest.raises(sqlite3.IntegrityError):
        with db.conectar() as con:
            con.execute(
                "INSERT INTO operaciones_economia VALUES "
                "('v1','u1','g1','aventura','2026-01-01','acreditada',5,'{}')"
            )

    db.inicializar()

    assert economia.otorgar_hallazgo("v1", "u1", "g1", 5, 0, T0).monedas == 5


def test_la_migracion_dos_veces_deja_lo_mismo():
    """Corre en cada arranque: a partir de la segunda tiene que ser inocua, o
    cada reinicio copiaría el ledger otra vez."""
    _con_ledger_viejo()

    db.inicializar()
    primera = sorted(tuple(f.values()) for f in filas_del_ledger())
    db.inicializar()
    db.inicializar()

    assert sorted(tuple(f.values()) for f in filas_del_ledger()) == primera


def test_una_base_nueva_ya_nace_con_el_tipo_nuevo():
    assert economia.otorgar_hallazgo("v1", "u1", "g1", 5, 0, T0).monedas == 5


def test_cuidando_solo_no_se_llega_al_bote():
    """Los topes por actividad siguen ahí y siguen mandando dentro de lo suyo:
    doce cuidados son doce monedas, y para los otros ocho hay que competir,
    evolucionar o salir al campo. Es lo que reparte el día."""
    nacer()
    for i in range(economia.TOPE_CUIDADOS + 5):
        cuidar(f"c{i}", cuando=T0 + timedelta(hours=i))

    assert ganado_hoy() == economia.TOPE_CUIDADOS
    assert economia.TOPE_CUIDADOS < economia.TOPE_DIARIO_ASCIICOINS
