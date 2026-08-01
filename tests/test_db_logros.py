"""El marcador y los logros en la base: que cuenten, y que no paguen dos veces."""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import db
import logros
import simulacion as sim

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


# --- Desbloquear -----------------------------------------------------------

def test_revisar_devuelve_lo_recien_ganado_y_lo_guarda():
    bicho = nacer()
    db.apuntar(bicho.id, logros.CARRERAS, 10)

    nuevos = {logro.clave for logro in db.revisar_logros(bicho, T0)}
    assert "velocista" in nuevos
    assert set(db.logros_de(bicho.id)) >= {"velocista", "de_la_alfa"}


def test_un_logro_no_se_cobra_dos_veces():
    """El fallo caro: el contador de carreras sigue subiendo después de
    desbloquear «Velocista», así que si `revisar_logros` lo devolviera cada vez,
    en la entrega de las gemas se pagaría en cada carrera."""
    bicho = nacer()
    db.apuntar(bicho.id, logros.CARRERAS, 10)
    db.revisar_logros(bicho, T0)

    for _ in range(5):
        db.apuntar(bicho.id, logros.CARRERAS)
        assert db.revisar_logros(bicho, T0 + timedelta(hours=1)) == ()

    assert len(db.logros_de(bicho.id)) == 2  # velocista y de_la_alfa, una vez


def test_la_fecha_es_la_de_cuando_se_consiguio():
    bicho = nacer()
    despues = T0 + timedelta(days=3)
    db.apuntar(bicho.id, logros.AVENTURAS, 10)
    db.revisar_logros(bicho, despues)

    assert db.logros_de(bicho.id)["explorador"] == despues


def test_los_logros_son_del_gachamon_y_no_del_jugador():
    """Lo que se pidió: dos gachamones de la misma persona llevan medallas
    distintas, y morirse se las lleva."""
    corredor = nacer(nombre="Corredor")
    novato = nacer(nombre="Novato", activa=False)

    db.apuntar(corredor.id, logros.CARRERAS, 10)
    db.revisar_logros(corredor, T0)
    db.revisar_logros(novato, T0)

    assert "velocista" in db.logros_de(corredor.id)
    assert "velocista" not in db.logros_de(novato.id)
    # Al novato le queda lo que se lleva por existir, y nada más.
    assert set(db.logros_de(novato.id)) == {"de_la_alfa"}


def test_al_morir_conserva_lo_que_hizo_pero_no_superviviente():
    bicho = nacer()
    db.apuntar(bicho.id, logros.AVENTURAS, 100)
    db.revisar_logros(bicho, T0)
    assert "superviviente" in db.logros_de(bicho.id)

    otro = nacer(usuario="u2", nombre="Muerto")
    db.apuntar(otro.id, logros.AVENTURAS, 100)
    muerto = sim.Criatura(**{
        **otro.__dict__, "muerta_en": T0, "causa_muerte": "hambre",
    })
    db.guardar(muerto)
    db.revisar_logros(muerto, T0)
    conseguidos = db.logros_de(otro.id)

    assert "explorador" in conseguidos
    assert "superviviente" not in conseguidos


def test_cartografo_pide_los_diez_biomas_de_verdad():
    """El marcador guarda una clave por bioma, así que volver al mismo sitio no
    acerca la medalla. Es la razón de que no sea un simple contador."""
    import aventura as av

    bicho = nacer()
    for _ in range(20):
        db.apuntar(bicho.id, logros.clave_de_bioma("volcan"))
    assert "cartografo" not in {l.clave for l in db.revisar_logros(bicho, T0)}

    for bioma in av.BIOMAS:
        db.apuntar(bicho.id, logros.clave_de_bioma(bioma))
    assert "cartografo" in {l.clave for l in db.revisar_logros(bicho, T0)}
