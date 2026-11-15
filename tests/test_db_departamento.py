"""El departamento en la base: cómo nace, sus muebles, su tamaño y el ritmo que da."""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import db
import departamento as dep
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "departamento.db")
    db.inicializar()


def filas(tabla):
    with db.conectar() as con:
        return [tuple(f) for f in con.execute(f"SELECT * FROM {tabla}")]


def nacer(nombre, activa=True):
    return db.crear("u1", "g1", "pulpo", nombre, STATS, T0, activa=activa)


def con_muebles_puestos(usuario, *claves):
    """Crea el departamento de `usuario` y le pone cada mueble en el primer sitio libre."""
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db._departamento_en(con, usuario, "g1", T0)
        for clave in claves:
            pieza = db.anadir_mueble_en(con, usuario, "g1", clave)
            d = db._departamento_leido(con, usuario, "g1")
            x, y = next(
                (x, y)
                for y in range(-1, d.fondo)
                for x in range(-1, d.ancho)
                if dep.problema_al_poner(d, pieza, x, y, 0) is None
            )
            db.poner_mueble_en(con, pieza, x, y, 0)


def test_el_departamento_nace_al_mirarlo_con_tu_cama_puesta_y_otra_guardada():
    d = db.departamento_de("u1", "g1", T0)
    assert (d.ancho, d.fondo) == (3, 3)
    assert [(p.clave, p.x, p.y, p.giro) for p in d.piezas] == [("cama_sencilla", 0, 0, 0), ("cama_sencilla", None, None, 0)]
    assert all(p.id > 0 for p in d.piezas)
    assert db.departamento_de("u1", "g1", T0) == d                  # no nace dos veces


def test_leer_sin_crear_da_el_de_partida_y_no_escribe():
    assert db.departamento_leido("u9", "g1") == dep.DE_PARTIDA
    assert filas("departamentos") == [] and filas("muebles") == []


def test_un_mueble_llega_guardado_se_pone_y_se_vuelve_a_guardar():
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db._departamento_en(con, "u1", "g1", T0)
        uno = db.anadir_mueble_en(con, "u1", "g1", "felpudo")
        otro = db.anadir_mueble_en(con, "u1", "g1", "felpudo")      # puede haber varios iguales
        db.poner_mueble_en(con, uno, 2, 1, 3)
    d = db.departamento_leido("u1", "g1")
    assert uno != otro and d.pieza(uno) == dep.Pieza(uno, "felpudo", 2, 1, 3) and not d.pieza(otro).puesta
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db.guardar_mueble_en(con, uno)
    assert db.departamento_leido("u1", "g1").pieza(uno) == dep.Pieza(uno, "felpudo")


def test_ampliar_suma_una_columna_o_una_fila_y_no_mueve_nada():
    antes = db.departamento_de("u1", "g1", T0)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db.ampliar_en(con, "u1", "g1", dep.ANCHO)
        db.ampliar_en(con, "u1", "g1", dep.FONDO)
        db.ampliar_en(con, "u1", "g1", dep.FONDO)
    despues = db.departamento_leido("u1", "g1")
    assert (despues.ancho, despues.fondo, despues.piezas) == (4, 5, antes.piezas)


def test_el_esquema_no_admite_media_posicion_ni_un_tamano_imposible():
    for sql in ("INSERT INTO muebles (usuario_id, guild_id, mueble, x) VALUES ('u1', 'g1', 'felpudo', 1)",
                "INSERT INTO muebles (usuario_id, guild_id, mueble, giro) VALUES ('u1', 'g1', 'felpudo', 4)",
                "INSERT INTO departamentos (usuario_id, guild_id, ancho, creado_en) VALUES ('u1', 'g1', 9, 'x')"):
        with pytest.raises(sqlite3.IntegrityError), db.conectar() as con:
            con.execute(sql)


def test_el_departamento_es_de_cada_persona_y_de_cada_servidor():
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db._departamento_en(con, "u1", "g1", T0)
        db.anadir_mueble_en(con, "u1", "g1", "maceta")
    assert len(db.departamento_leido("u1", "g1").piezas) == 3
    assert db.departamento_leido("u1", "g2") == dep.DE_PARTIDA == db.departamento_leido("u2", "g1")


def test_el_ritmo_sale_del_departamento():
    c = nacer("Ana")
    con_muebles_puestos("u1", "chimenea", "biblioteca")              # 82 + 6 + 7
    tarde = T0 + timedelta(hours=10)
    d = db.departamento_leido("u1", "g1")
    assert d.comodidad == 95
    assert db.avanzar(c, tarde) == sim.avanzar(c, tarde, dep.ritmo_de(d))
    assert db.avanzar(c, tarde).animo > sim.avanzar(c, tarde).animo


def test_el_ritmo_ya_no_mira_casas_ni_refugio():
    c = nacer("Ana")
    with db.conectar() as con:      # lo que antes era «a la intemperie»: el refugio vencido y sin casa
        con.execute("INSERT INTO hogar (usuario_id, guild_id, refugio_hasta) VALUES ('u1', 'g1', ?)", ((T0 - timedelta(days=30)).isoformat(),))
    tarde = T0 + timedelta(days=30)
    assert db.avanzar(c, tarde) == sim.avanzar(c, tarde, dep.ritmo_de(dep.DE_PARTIDA))
    assert db.avanzar(c, tarde).hambre == 0                          # ya no hay suelo de 25


def test_asentar_guarda_a_todos_los_vivos_a_esa_hora():
    ana, bea = nacer("Ana"), nacer("Bea", activa=False)
    tarde = T0 + timedelta(hours=5)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        asentados = db.asentar_el_plantel_en(con, "u1", "g1", tarde)
    assert {c.id for c in asentados} == {ana.id, bea.id}
    for c in (ana, bea):
        assert db.por_id(c.id).actualizada_en == tarde and db.por_id(c.id).hambre < c.hambre
