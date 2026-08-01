"""El marcador y la tabla de logros: contar, y que nada se apunte dos veces."""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import db
import logros

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15)


@pytest.fixture(autouse=True)
def bd_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "prueba.db")
    db.inicializar()


def nacer(usuario="u1", guild="g1", nombre="Prueba", activa=True):
    return db.crear(usuario, guild, "pulpo", nombre, STATS, T0, activa=activa)


# --- El marcador -----------------------------------------------------------

def test_un_gachamon_nuevo_no_lleva_nada_hecho():
    assert db.marcador(nacer().id) == {}


def test_apuntar_suma_sobre_lo_que_ya_habia():
    bicho = nacer()
    for _ in range(3):
        db.apuntar(bicho.id, logros.CARRERAS)
    db.apuntar(bicho.id, logros.NODOS, 5)

    assert db.marcador(bicho.id) == {logros.CARRERAS: 3, logros.NODOS: 5}


def test_el_marcador_es_de_cada_gachamon_por_separado():
    uno, otro = nacer(nombre="Uno"), nacer(nombre="Otro", activa=False)
    db.apuntar(uno.id, logros.CARRERAS, 7)

    assert db.marcador(uno.id) == {logros.CARRERAS: 7}
    assert db.marcador(otro.id) == {}


def test_lo_apuntado_a_medias_no_queda():
    """`apuntar_en` recibe la conexión justo para esto: si la transacción que
    resuelve la carrera se cae, la carrera no se cuenta. Lo contrario —contar
    fuera— dejaría victorias que no existieron."""
    bicho = nacer()
    with pytest.raises(sqlite3.IntegrityError):
        with db.conectar() as con:
            con.execute("BEGIN IMMEDIATE")
            db.apuntar_en(con, bicho.id, logros.CARRERAS)
            # Lo que revienta la transacción: apuntarle algo a un gachamon que
            # no existe. Da igual el motivo del fallo; lo que se comprueba es
            # que la carrera de arriba se va con él.
            db.apuntar_en(con, bicho.id + 999, logros.CARRERAS)

    assert db.marcador(bicho.id) == {}


# --- Anotar ----------------------------------------------------------------
#
# Quién decide que un logro está cumplido y quién lo paga es de `economia`; lo
# de aquí es sólo la fila y su fecha.

def test_anotar_dice_si_era_nuevo():
    """Lo que devuelve **es** la garantía de que no se pague dos veces: quien
    llama sólo cobra lo que entró de verdad."""
    bicho = nacer()
    with db.conectar() as con:
        assert db.anotar_logro_en(con, bicho.id, "velocista", T0) is True
        assert db.anotar_logro_en(con, bicho.id, "velocista", T0) is False


def test_la_fecha_es_la_de_cuando_se_consiguio():
    bicho = nacer()
    despues = T0 + timedelta(days=3)
    with db.conectar() as con:
        db.anotar_logro_en(con, bicho.id, "explorador", despues)

    assert db.logros_de(bicho.id)["explorador"] == despues


def test_reintentar_no_mueve_la_fecha():
    """El segundo intento no entra, así que tampoco puede reescribir el día en
    que se consiguió por el de hoy."""
    bicho = nacer()
    with db.conectar() as con:
        db.anotar_logro_en(con, bicho.id, "explorador", T0)
        db.anotar_logro_en(con, bicho.id, "explorador", T0 + timedelta(days=9))

    assert db.logros_de(bicho.id)["explorador"] == T0


def test_los_logros_son_de_cada_gachamon_por_separado():
    uno, otro = nacer(nombre="Uno"), nacer(nombre="Otro", activa=False)
    with db.conectar() as con:
        db.anotar_logro_en(con, uno.id, "velocista", T0)

    assert set(db.logros_de(uno.id)) == {"velocista"}
    assert db.logros_de(otro.id) == {}
