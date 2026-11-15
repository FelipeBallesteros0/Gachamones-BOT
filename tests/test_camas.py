"""Las camas puestas mandan: reclutar pide una cama libre y no hay tope de 25."""
import random
from datetime import datetime, timezone

import pytest

import db
import departamento as dep
import especies as esp
import identidad
import nacer as nacer_
from ayudas_web import PUEBLO, con_gachamon
from test_web_incubadora import ir

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)
USUARIO_WEB = identidad.de_cuenta_web(1)
# Con tu cama en (0, 0), en un 3 x 3 caben tres más.
SITIOS = ((0, 1, 0), (0, 2, 0), (2, 0, 1))


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "camas.db")
    db.inicializar()


def nacer(nombre, activa=True):
    return db.crear("u1", "g1", "pulpo", nombre, STATS, T0, activa=activa)


def poner_camas(usuario, cuantas, guild="g1"):
    """Le añade `cuantas` camas sencillas puestas, creando su departamento si falta."""
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db._departamento_en(con, usuario, guild, T0)
        for x, y, giro in SITIOS[:cuantas]:
            db.anadir_mueble_en(con, usuario, guild, "cama_sencilla", x, y, giro)


def guardado(usuario, clave, guild="g1"):
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db._departamento_en(con, usuario, guild, T0)
        return db.anadir_mueble_en(con, usuario, guild, clave)


def filas(tabla):
    with db.conectar() as con:
        return [tuple(f) for f in con.execute(f"SELECT * FROM {tabla}")]


def recluta(rng=1):
    return nacer_.unir_recluta(
        "u1", "g1", especie="pulpo", stats=STATS, genero=esp.MACHO,
        caracter=esp.CARACTER_POR_DEFECTO, ahora=T0, rng=random.Random(rng),
    )


def test_un_recluta_pide_una_cama_libre():
    nacer("Ana")                                   # del huevo: tú y Ana, con una sola cama puesta
    with pytest.raises(db.SinCamaLibre):
        recluta()
    poner_camas("u1", 2)                           # ya son tres: la tuya, la de Ana y una libre
    assert recluta().nombre
    with pytest.raises(db.SinCamaLibre):
        recluta(2)


def test_sin_cama_libre_no_nace_nadie_ni_cuenta_como_reclutado():
    nacer("Ana")
    antes = (filas("criaturas"), filas("marcador_persona"))
    with pytest.raises(db.SinCamaLibre):
        recluta()
    assert (filas("criaturas"), filas("marcador_persona")) == antes


def test_sin_cama_libre_es_un_value_error_para_quien_ya_trata_ese_caso():
    assert issubclass(db.SinCamaLibre, ValueError)


def test_las_camas_guardadas_no_cuentan():
    nacer("Ana")
    for _ in range(3):
        guardado("u1", "cama_sencilla")
    assert not db.hay_cama_libre("u1", "g1")


def test_la_cama_libre_es_por_persona_y_por_servidor():
    nacer("Ana")
    poner_camas("u1", 2)
    assert db.hay_cama_libre("u1", "g1")
    assert not db.hay_cama_libre("u1", "g2")       # sin departamento: sólo la tuya
    assert not db.hay_cama_libre("u2", "g1")
    nacer_.unir_recluta(
        "u1", "g1", especie="pulpo", stats=STATS, genero=esp.MACHO,
        caracter=esp.CARACTER_POR_DEFECTO, ahora=T0, rng=random.Random(1),
    )
    assert not db.hay_cama_libre("u1", "g1")


def test_el_que_nace_del_huevo_todavia_no_pide_cama():
    assert nacer_.romper_el_huevo("u1", "g1", T0, random.Random(1)).id


def test_ya_no_hay_tope_de_25():
    for i in range(27):
        db.crear("u1", "g1", "pulpo", f"N{i}", STATS, T0, activa=(i == 0))
    assert len(db.plantel("u1", "g1")) == 27 and not hasattr(db, "MAXIMO_PLANTEL")


def test_hay_mas_nombres_que_gachamones_caben():
    assert dep.MAXIMO_DE_GACHAMONES == 31       # y en tests/test_nombres.py, la cuenta de nombres se compara con esto


def test_la_incubadora_dice_cuantos_caben_por_las_camas(cliente):
    con_gachamon(cliente); ir(cliente, "incubadora")
    assert cliente.get("/gachamon/api/incubadora").json()["maximo"] == 1     # el del huevo, que aún no tiene cama
    poner_camas(USUARIO_WEB, 3, guild=str(PUEBLO))                           # ya son cuatro puestas
    assert cliente.get("/gachamon/api/incubadora").json()["maximo"] == 3
