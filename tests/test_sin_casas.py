"""Las reglas de antes se fueron: ni casas, ni refugio, ni intemperie, ni huerto
por casa, ni el ticket.

Lo que sí se queda son sus tablas y `db._migrar_casas`: una base vieja tiene que
poder llegar hasta el día del cambio, que es quien convierte lo de cada quien.
"""
import random
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import aventura as av
import db
import economia
import huerto
import identidad
import objetos as obj
from web import tienda

RAIZ = Path(__file__).resolve().parent.parent
T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(days=30)
STATS = (15, 15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "sin_casas.db")
    db.inicializar()


def archivos_de_produccion() -> list[Path]:
    """Los `.py` que sigue git, sin `tests/`."""
    seguidos = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=RAIZ, capture_output=True, text=True, check=True
    ).stdout.split()
    return [RAIZ / ruta for ruta in seguidos if not ruta.startswith("tests/")]


def tablas() -> set[str]:
    with db.conectar() as con:
        return {f["name"] for f in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def columnas(tabla: str) -> set[str]:
    with db.conectar() as con:
        return {f["name"] for f in con.execute(f"PRAGMA table_info({tabla})")}


def nacer(nombre: str, usuario: str = "u1"):
    return db.crear(usuario, "g1", "pulpo", nombre, STATS, T0)


def test_ya_no_hay_modulo_de_casas_ni_quien_lo_importe():
    assert not (RAIZ / "casas.py").exists()
    archivos = archivos_de_produccion()
    assert archivos
    for archivo in archivos:
        assert not re.search(r"^\s*(import casas|from casas )", archivo.read_text(), re.M), archivo


@pytest.mark.parametrize("modulo, nombre", [
    (economia, "comprar_casa"), (economia, "vender_casa"), (economia, "mudar_gachamon"), (economia, "plantar"),
    (economia, "regar"), (economia, "cosechar"), (db, "hogar_leido"), (db, "_hogar_leido"), (db, "_casas_de"),
    (db, "alargar_el_refugio_en"), (identidad, "sin_plazo_de_refugio"), (huerto, "BANCALES"), (huerto, "Bancal"),
    # Y lo demás que se fue con ellas.
    (economia, "ResultadoMudanza"), (economia, "ResultadoVenta"), (economia, "ResultadoMudanzaDeGachamon"),
    (economia, "ResultadoHuerto"), (economia, "_huerto_abierto"), (economia, "_bancal_de"),
    (db, "_primera_casa_con_sitio"), (db, "hogar_de"), (db, "_hogar_de"), (db, "_hay_hogar"),
    (db, "estancia_empezada"), (db, "abrir_o_cerrar_la_casa"), (db, "vender_la_casa_en"), (db, "anadir_casa_en"),
    (db, "mejorar_casa_en"), (db, "inquilinos_de"), (db, "inquilinos_en"), (db, "acoger_a_los_sin_casa_en"),
    (db, "mudar_criatura_en"), (db, "huerto_de"), (db, "_huerto_de"), (db, "plantar_en"), (db, "regar_en"),
    (db, "arrancar_en"), (huerto, "bancales_de"), (huerto, "plantables"), (huerto, "HORAS_DE_CULTIVO"),
    (huerto, "HORAS_QUE_AHORRA_REGAR"), (tienda, "HUERTO"), (tienda, "fuera_de_la_pagina"),
])
def test_las_reglas_de_antes_se_fueron(modulo, nombre):
    assert not hasattr(modulo, nombre)


def test_ningun_objeto_alarga_ya_el_refugio():
    assert "dias_de_refugio" not in obj.Objeto.__dataclass_fields__


def test_no_se_fue_ninguna_tabla_ni_columna_de_antes():
    for tabla in ("casas_propias", "mobiliario", "huerto", "hogar", "buzon"):
        assert tabla in tablas()
    assert "casa_id" in columnas("criaturas")
    assert {"refugio_hasta", "publica"} <= columnas("hogar")
    assert "casa_id" in columnas("huerto") and "casa_id" in columnas("mobiliario")


def test_el_ticket_ya_no_existe_y_la_semilla_ni_se_vende_ni_sale_de_botin():
    assert "ticket_refugio" not in obj.CATALOGO and not obj.CATALOGO["semilla"].se_vende
    rng = random.Random(1)
    assert all(av.tirar_objeto(rng).clave not in ("semilla", "ticket_refugio") for _ in range(2000))


def test_una_base_de_antes_todavia_llega_hasta_el_cambio():
    """Una casa de cuando había «una por persona», en la tabla `hogar` de
    entonces: `_migrar_casas` la pasa a `casas_propias` y el día del cambio la
    devuelve en monedas y le da a su dueña el departamento."""
    from tests.test_migracion_casas import volver_al_esquema_viejo

    nacer("Ana")
    with db.conectar() as con:
        volver_al_esquema_viejo(con)
        con.execute(
            "INSERT INTO hogar (usuario_id, guild_id, casa, refugio_hasta) VALUES ('u1', 'g1', 'pequena', ?)",
            (T0.isoformat(),),
        )
    antes = economia.saldos("u1", "g1").asciicoins

    economia.poner_al_dia(T1)

    assert economia.saldos("u1", "g1").asciicoins == antes + 200
    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM casas_propias").fetchone()[0] == 0
        assert "casa" not in {f["name"] for f in con.execute("PRAGMA table_info(hogar)")}
        assert con.execute(
            "SELECT ancho, fondo FROM departamentos WHERE usuario_id = 'u1' AND guild_id = 'g1'"
        ).fetchone() is not None
    depto = db.departamento_leido("u1", "g1")
    assert depto.camas_puestas == 2             # la suya y la de Ana
    [ana] = db.plantel("u1", "g1")
    assert ana.casa_id is None


def test_un_gachamon_nace_sin_casa():
    """Aunque su dueña tenga todavía una fila en `casas_propias`, como una base de
    antes del cambio: ya nadie vive en una casa."""
    with db.conectar() as con:
        con.execute(
            "INSERT INTO casas_propias (usuario_id, guild_id, casa, comprada_en) VALUES ('u1', 'g1', 'grande', ?)",
            (T0.isoformat(),),
        )
    assert nacer("Ana").casa_id is None
    with db.conectar() as con:
        assert con.execute("SELECT casa_id FROM criaturas").fetchone()["casa_id"] is None


def test_todo_lo_que_hace_pasar_el_tiempo_mira_el_departamento():
    """Ningún sitio puede llamar a `sim.avanzar` a secas.

    El valor por defecto es el ritmo de siempre, así que olvidarlo no rompe nada
    visible: simplemente la comodidad del departamento deja de contar, en
    silencio. Lo vigila un barrido del fuente en vez de la buena voluntad.
    (Viene de las pruebas de las casas, que miraban lo mismo con el hogar.)
    """
    permitidos = {"simulacion.py", "db.py"}
    sueltos = []
    for archivo in RAIZ.glob("**/*.py"):
        if "tests" in archivo.parts or "venv" in archivo.parts:
            continue
        if archivo.name not in permitidos and "sim.avanzar(" in archivo.read_text():
            sueltos.append(archivo.name)
    assert not sueltos, (
        f"llaman a sim.avanzar sin mirar el departamento: {sueltos}. Usa db.avanzar "
        "o db._avanzar_en si ya hay una transacción abierta."
    )
