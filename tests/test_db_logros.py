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


# --- Y los de la persona ---------------------------------------------------

def test_las_medallas_de_la_persona_sobreviven_a_todos_sus_gachamones():
    """Lo pedido: Domador, Flautista y Uno entre veinticinco son tuyos. Se te
    muere el plantel entero y los conservas, que es lo que los distingue de los
    otros quince."""
    bicho = nacer()
    with db.conectar() as con:
        db.apuntar_persona_en(con, "u1", "g1", logros.RECLUTADOS, 4)
        db.anotar_logro_de_persona_en(con, "u1", "g1", "domador", T0)
        con.execute(
            "UPDATE criaturas SET muerta_en = ?, causa_muerte = 'hambre' "
            "WHERE id = ?",
            (T0.isoformat(), bicho.id),
        )

    assert set(db.logros_de_persona("u1", "g1")) == {"domador"}
    assert db.marcador_de_persona("u1", "g1") == {logros.RECLUTADOS: 4}


def test_el_marcador_de_la_persona_es_por_servidor():
    """Como todo lo demás: lo que hagas en un servidor no cuenta en otro."""
    with db.conectar() as con:
        db.apuntar_persona_en(con, "u1", "g1", logros.RECLUTADOS, 3)

    assert db.marcador_de_persona("u1", "g1") == {logros.RECLUTADOS: 3}
    assert db.marcador_de_persona("u1", "g2") == {}
    assert db.marcador_de_persona("u2", "g1") == {}


def test_anotar_de_persona_dice_si_era_nuevo_y_no_mueve_la_fecha():
    with db.conectar() as con:
        assert db.anotar_logro_de_persona_en(con, "u1", "g1", "domador", T0)
        assert not db.anotar_logro_de_persona_en(
            con, "u1", "g1", "domador", T0 + timedelta(days=9)
        )

    assert db.logros_de_persona("u1", "g1")["domador"] == T0


def test_las_especies_de_una_persona_incluyen_las_muertas():
    """Es lo que alimenta «Uno entre veinticinco»: que te saliera una rara no
    deja de haber pasado porque se te muriera."""
    muerta = db.crear("u1", "g1", "dragoncito", "Rara", STATS, T0, activa=False)
    nacer(nombre="Viva")
    db.crear("u2", "g1", "michi", "DeOtro", STATS, T0)
    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET muerta_en = ?, causa_muerte = 'hambre' "
            "WHERE id = ?",
            (T0.isoformat(), muerta.id),
        )

    assert set(db.especies_de("u1", "g1")) == {"dragoncito", "pulpo"}
    assert set(db.especies_de("u2", "g1")) == {"michi"}


# --- La mudanza de los tres ------------------------------------------------

def _como_estaba_antes(criatura_id: int, reclutados: int = 2) -> None:
    """Deja la base con la forma vieja: los tres colgados del gachamon."""
    with db.conectar() as con:
        con.execute(
            "INSERT INTO logros (criatura_id, clave, cuando) VALUES (?, ?, ?)",
            (criatura_id, "domador", T0.isoformat()),
        )
        con.execute(
            "INSERT INTO marcador (criatura_id, clave, valor) VALUES (?, ?, ?)",
            (criatura_id, logros.RECLUTADOS, reclutados),
        )


def _gemas(usuario="u1", guild="g1") -> int:
    with db.conectar() as con:
        fila = con.execute(
            "SELECT asciigems FROM monederos WHERE usuario_id = ? AND guild_id = ?",
            (usuario, guild),
        ).fetchone()
    return fila["asciigems"]


def test_la_mudanza_traslada_lo_ganado_sin_pagar_ni_quitar_nada():
    """Lo que ya se cobró se queda cobrado, y la mudanza no toca el monedero:
    ni paga otra vez ni le quita a nadie lo que ganó con las reglas de antes."""
    bicho = nacer()
    db.inicializar()          # le publica el monedero, como en producción
    _como_estaba_antes(bicho.id)
    antes = _gemas()

    db.inicializar()          # y ahora sí, la mudanza

    assert set(db.logros_de_persona("u1", "g1")) == {"domador"}
    assert db.logros_de_persona("u1", "g1")["domador"] == T0
    assert db.marcador_de_persona("u1", "g1") == {logros.RECLUTADOS: 2}
    # Y no queda rastro en las viejas.
    assert db.logros_de(bicho.id) == {}
    assert db.marcador(bicho.id) == {}
    assert _gemas() == antes


def test_la_mudanza_suma_los_contadores_de_todos_tus_gachamones():
    """Cada uno llevaba su cuenta y «Flautista» pedía diez con el mismo. Al ser
    tuyo, se suman: si no, quien tuviera 6 y 5 se quedaría a las puertas."""
    uno = nacer(nombre="Uno")
    otro = nacer(nombre="Otro", activa=False)
    _como_estaba_antes(uno.id, reclutados=6)
    with db.conectar() as con:
        con.execute(
            "INSERT INTO marcador (criatura_id, clave, valor) VALUES (?, ?, ?)",
            (otro.id, logros.RECLUTADOS, 5),
        )
        con.execute(
            "INSERT INTO logros (criatura_id, clave, cuando) VALUES (?, ?, ?)",
            (otro.id, "domador", (T0 + timedelta(days=5)).isoformat()),
        )

    db.inicializar()

    assert db.marcador_de_persona("u1", "g1") == {logros.RECLUTADOS: 11}
    # La fecha es la del primero que lo consiguió, no la del último.
    assert db.logros_de_persona("u1", "g1")["domador"] == T0


def test_la_mudanza_dos_veces_deja_lo_mismo():
    """Corre en cada arranque, así que tiene que ser inocua a partir de la
    segunda: si sumara otra vez, cada reinicio regalaría reclutamientos."""
    bicho = nacer()
    _como_estaba_antes(bicho.id, reclutados=3)

    db.inicializar()
    primera = (db.marcador_de_persona("u1", "g1"), db.logros_de_persona("u1", "g1"))
    db.inicializar()
    db.inicializar()

    assert (
        db.marcador_de_persona("u1", "g1"), db.logros_de_persona("u1", "g1")
    ) == primera


def test_la_mudanza_no_mezcla_a_dos_personas():
    mio = nacer(nombre="Mio")
    tuyo = nacer(usuario="u2", nombre="Tuyo")
    _como_estaba_antes(mio.id, reclutados=2)
    _como_estaba_antes(tuyo.id, reclutados=7)

    db.inicializar()

    assert db.marcador_de_persona("u1", "g1") == {logros.RECLUTADOS: 2}
    assert db.marcador_de_persona("u2", "g1") == {logros.RECLUTADOS: 7}
