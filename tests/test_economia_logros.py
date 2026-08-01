"""Los logros y lo que pagan: desbloquear, cobrar, y no cobrar dos veces."""
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

import aventura as av
import competir as comp
import db
import economia
import logros
import objetos as obj
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "logros.db")
    db.inicializar()


def nacer(usuario="u1", activa=True, nombre=None):
    return db.crear(
        usuario, "g1", "pulpo", nombre or usuario, STATS, T0, activa=activa
    )


def gemas_de(usuario="u1"):
    return economia.saldos(usuario, "g1").asciigems


def claves(recibo):
    return {logro.clave for logro in recibo.nuevos}


# --- Desbloquear -----------------------------------------------------------

def test_devuelve_lo_recien_ganado_y_lo_guarda():
    bicho = nacer()
    db.apuntar(bicho.id, logros.CARRERAS, 10)

    recibo = economia.pagar_logros(bicho, T0)
    assert "velocista" in claves(recibo)
    assert set(db.logros_de(bicho.id)) >= {"velocista", "de_la_alfa"}


def test_los_logros_son_del_gachamon_y_no_del_jugador():
    """Lo que se pidió: dos gachamones de la misma persona llevan medallas
    distintas."""
    corredor = nacer(nombre="Corredor")
    novato = nacer(nombre="Novato", activa=False)

    db.apuntar(corredor.id, logros.CARRERAS, 10)
    economia.pagar_logros(corredor, T0)
    economia.pagar_logros(novato, T0)

    assert "velocista" in db.logros_de(corredor.id)
    assert "velocista" not in db.logros_de(novato.id)
    # Al novato le queda lo que se lleva por existir, y nada más.
    assert set(db.logros_de(novato.id)) == {"de_la_alfa"}


def test_al_morir_conserva_lo_que_hizo_pero_no_superviviente():
    bicho = nacer()
    db.apuntar(bicho.id, logros.AVENTURAS, 100)
    economia.pagar_logros(bicho, T0)
    assert "superviviente" in db.logros_de(bicho.id)

    otro = nacer(usuario="u2", nombre="Muerto")
    db.apuntar(otro.id, logros.AVENTURAS, 100)
    muerto = sim.Criatura(**{
        **otro.__dict__, "muerta_en": T0, "causa_muerte": "hambre",
    })
    db.guardar(muerto)
    economia.pagar_logros(muerto, T0)
    conseguidos = db.logros_de(otro.id)

    assert "explorador" in conseguidos
    assert "superviviente" not in conseguidos


def test_cartografo_pide_los_diez_biomas_de_verdad():
    """El marcador guarda una clave por bioma, así que volver al mismo sitio no
    acerca la medalla. Es la razón de que no sea un simple contador."""
    bicho = nacer()
    for _ in range(20):
        db.apuntar(bicho.id, logros.clave_de_bioma("volcan"))
    assert "cartografo" not in claves(economia.pagar_logros(bicho, T0))

    for bioma in av.BIOMAS:
        db.apuntar(bicho.id, logros.clave_de_bioma(bioma))
    assert "cartografo" in claves(economia.pagar_logros(bicho, T0))


# --- Cobrar ----------------------------------------------------------------

def test_el_logro_paga_sus_gemas_al_monedero_de_la_persona():
    bicho = nacer()
    antes = gemas_de()
    db.apuntar(bicho.id, logros.CARRERAS, 10)

    recibo = economia.pagar_logros(bicho, T0)

    velocista = logros.POR_CLAVE["velocista"].gemas
    alfa = logros.POR_CLAVE["de_la_alfa"].gemas
    assert recibo.asciigems == velocista + alfa
    assert gemas_de() == antes + velocista + alfa
    assert recibo.saldo == gemas_de()


def test_el_saldo_de_partida_no_se_toca_hasta_que_se_gana_algo():
    nacer()
    assert gemas_de() == obj.ASCIIGEMS_INICIALES


def test_un_logro_no_se_cobra_dos_veces():
    """El fallo caro de toda la entrega: el contador de carreras sigue subiendo
    después de desbloquear «Velocista», así que sin la clave primaria de
    `logros` se pagarían gemas en cada carrera para siempre."""
    bicho = nacer()
    db.apuntar(bicho.id, logros.CARRERAS, 10)
    economia.pagar_logros(bicho, T0)
    saldo = gemas_de()

    for _ in range(5):
        db.apuntar(bicho.id, logros.CARRERAS)
        recibo = economia.pagar_logros(bicho, T0 + timedelta(hours=1))
        assert recibo.nuevos == ()
        assert recibo.asciigems == 0

    assert gemas_de() == saldo
    assert len(db.logros_de(bicho.id)) == 2  # velocista y de_la_alfa, una vez


def test_dos_gachamones_de_la_misma_persona_llenan_el_mismo_monedero():
    """Las medallas son de cada uno; el monedero es de la persona. Es lo que
    hace que coleccionar sirva para comprarle algo a cualquiera de ellos."""
    uno = nacer(nombre="Uno")
    otro = nacer(nombre="Otro", activa=False)
    antes = gemas_de()

    db.apuntar(uno.id, logros.CARRERAS, 10)
    db.apuntar(otro.id, logros.SUMOS, 10)
    primero = economia.pagar_logros(uno, T0)
    segundo = economia.pagar_logros(otro, T0)

    assert gemas_de() == antes + primero.asciigems + segundo.asciigems
    assert segundo.saldo == gemas_de()


def test_las_gemas_de_uno_no_se_le_pagan_al_vecino():
    mio = nacer("u1")
    del_otro = nacer("u2")
    db.apuntar(mio.id, logros.CARRERAS, 10)
    antes = gemas_de("u2")

    economia.pagar_logros(mio, T0)

    assert gemas_de("u2") == antes
    assert db.logros_de(del_otro.id) == {}


def test_el_pago_y_el_apunte_van_juntos_o_no_van(monkeypatch):
    """Si el UPDATE del monedero se cayera después de anotar el logro, quedaría
    un logro conseguido que nunca se pagó y que ya no se puede reintentar: el
    segundo intento lo encuentra puesto y devuelve vacío."""
    bicho = nacer()
    db.apuntar(bicho.id, logros.CARRERAS, 10)
    antes = gemas_de()

    def reventar(*_args, **_kwargs):
        raise RuntimeError("se cayó al pagar")

    original = economia._asegurar_monedero
    monkeypatch.setattr(economia, "_asegurar_monedero", reventar)
    with pytest.raises(RuntimeError):
        economia.pagar_logros(bicho, T0)
    # Sólo esta pieza: `monkeypatch.undo()` se llevaría por delante la base
    # temporal del fixture, que usa el mismo monkeypatch.
    monkeypatch.setattr(economia, "_asegurar_monedero", original)

    assert db.logros_de(bicho.id) == {}
    assert gemas_de() == antes
    # Y al reintentarlo, cobra: nada se ha quedado a medias.
    assert economia.pagar_logros(bicho, T0).asciigems > 0


def test_dos_hilos_a_la_vez_pagan_una_sola_vez():
    """El caso real: dos botones pulsados a la vez sobre el mismo gachamon.
    Lo serializa `BEGIN IMMEDIATE`, igual que las compras."""
    bicho = nacer()
    db.apuntar(bicho.id, logros.CARRERAS, 10)
    antes = gemas_de()

    with ThreadPoolExecutor(max_workers=2) as pool:
        recibos = list(pool.map(
            lambda _: economia.pagar_logros(bicho, T0), range(2)
        ))

    pagado = sum(recibo.asciigems for recibo in recibos)
    assert sorted(len(r.nuevos) for r in recibos) == [0, 2]
    assert gemas_de() == antes + pagado


# --- Jugando de verdad ------------------------------------------------------

def test_la_primera_victoria_se_paga_al_terminar_la_carrera():
    """De punta a punta: nadie llama a `pagar_logros` a mano, se llega ahí
    corriendo una carrera."""
    nacer("u1")
    nacer("u2")
    resultado = economia.ejecutar_competencia(
        "e1", ("u1", "u2"), "g1", comp.CARRERA, T0, random.Random(1)
    )
    campeon = resultado.despues[resultado.encuentro.orden[0]]
    antes = gemas_de(campeon.usuario_id)

    recibo = economia.pagar_logros(campeon, T0)

    assert "primera_sangre" in claves(recibo)
    assert gemas_de(campeon.usuario_id) == antes + recibo.asciigems
