"""Que cada cosa se cuente donde se resuelve, y sólo una vez.

Estos tests miran los contadores desde fuera —después de competir, cuidar o
viajar de verdad—, que es la única forma de cazar el fallo que importa: uno que
se cuente en el sitio equivocado sigue pasando todos los tests de `logros.py`.
"""
import random
from datetime import datetime, timedelta, timezone

import pytest

import aventura as av
import competir as comp
import db
import economia
import logros
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "marcador.db")
    db.inicializar()


def nacer(usuario="u1", activa=True, nombre=None):
    return db.crear(
        usuario, "g1", "pulpo", nombre or usuario, STATS, T0, activa=activa
    )


def competir_de(evento, tipo=comp.CARRERA, usuarios=("u1", "u2"), semilla=1):
    return economia.ejecutar_competencia(
        evento, usuarios, "g1", tipo, T0, random.Random(semilla)
    )


def ganador_de(resultado):
    return resultado.despues[resultado.encuentro.orden[0]]


# --- Competir --------------------------------------------------------------

def test_la_carrera_se_le_apunta_al_que_gana_y_a_nadie_mas():
    nacer("u1")
    nacer("u2")
    resultado = competir_de("e1")

    ganador = ganador_de(resultado)
    perdedor = next(c for c in resultado.despues if c.id != ganador.id)
    assert db.marcador(ganador.id) == {logros.CARRERAS: 1}
    assert db.marcador(perdedor.id) == {}


def test_el_sumo_cuenta_como_sumo_y_no_como_carrera():
    nacer("u1")
    nacer("u2")
    resultado = competir_de("e1", tipo=comp.SUMO)

    assert db.marcador(ganador_de(resultado).id) == {logros.SUMOS: 1}


def test_el_torneo_cuenta_como_torneo_y_tambien_como_sumo():
    """Ganar el torneo es haber ganado sumos: se lleva las dos cosas."""
    for usuario in ("u1", "u2", "u3", "u4"):
        nacer(usuario)
    resultado = competir_de("e1", tipo=comp.SUMO, usuarios=("u1", "u2", "u3", "u4"))

    assert resultado.encuentro is not None and resultado.encuentro.es_torneo
    assert db.marcador(ganador_de(resultado).id) == {
        logros.SUMOS: 1, logros.TORNEOS: 1,
    }


def test_reprocesar_el_mismo_encuentro_no_cuenta_dos_veces():
    """Mismo motivo que el dinero congelado: el replay devuelve lo de antes, no
    vuelve a resolver nada."""
    nacer("u1")
    nacer("u2")
    primero = competir_de("e1")
    ganador = ganador_de(primero)

    repetido = competir_de("e1")
    assert repetido.replay
    assert db.marcador(ganador.id) == {logros.CARRERAS: 1}


# --- Cuidar ----------------------------------------------------------------

def test_cada_cuidado_se_apunta():
    bicho = nacer()
    economia.ejecutar_cuidado("c1", "u1", "g1", sim.ALIMENTAR, T0)
    economia.ejecutar_cuidado("c2", "u1", "g1", sim.JUGAR, T0)

    assert db.marcador(bicho.id) == {logros.CUIDADOS: 2}


def test_actualizar_no_es_un_cuidado():
    """`/actualizar` sólo mira; no debería acercar a «Consentido»."""
    bicho = nacer()
    economia.ejecutar_cuidado("c1", "u1", "g1", sim.ACTUALIZAR, T0)

    assert db.marcador(bicho.id) == {}


def test_el_cuidado_que_rebota_por_la_espera_no_cuenta():
    bicho = nacer()
    economia.ejecutar_cuidado("c1", "u1", "g1", sim.ALIMENTAR, T0)
    economia.ejecutar_cuidado("c2", "u1", "g1", sim.ALIMENTAR, T0)

    assert db.marcador(bicho.id) == {logros.CUIDADOS: 1}


def test_repetir_el_mismo_evento_de_cuidado_no_cuenta_dos_veces():
    bicho = nacer()
    economia.ejecutar_cuidado("c1", "u1", "g1", sim.ALIMENTAR, T0)
    economia.ejecutar_cuidado("c1", "u1", "g1", sim.ALIMENTAR, T0)

    assert db.marcador(bicho.id) == {logros.CUIDADOS: 1}


# --- Salir al campo --------------------------------------------------------

def viaje_de(bioma="planicie", nodos=2):
    """Un viaje ya cerrado, como el que llega a `resolver`."""
    destino = av.BIOMAS[bioma]
    terreno = av.Terreno(
        (av.FUERZA, av.VELOCIDAD),
        (
            destino.dificultad - av.SESGO_TERRENO,
            destino.dificultad + av.SESGO_TERRENO,
        ),
    )
    escena = av.ESCENAS_ESCRITAS[bioma][av.FUERZA][0]
    pruebas = tuple(
        av.Prueba(obstaculo=f"tramo {i}", stat=av.FUERZA, base=10, dado=20,
                  dificultad=1)
        for i in range(nodos)
    )
    return av.Viaje(
        bioma=destino, escena=escena, terreno=terreno,
        pruebas=pruebas, nivel=nodos,
    )


def test_el_viaje_apunta_la_aventura_el_bioma_y_los_nodos():
    bicho = nacer()
    viaje = viaje_de("planicie", nodos=2)
    economia.ejecutar_viaje(
        "u1", "g1", bicho.id, viaje.salida, T0, viaje=viaje
    )

    assert db.marcador(bicho.id) == {
        logros.AVENTURAS: 1,
        logros.NODOS: 2,
        logros.clave_de_bioma("planicie"): 1,
    }


def test_salud_e_ingenio_cruzan_la_economia_y_el_marcador_sin_caso_especial():
    bicho = nacer()
    bioma = av.BIOMAS["planicie"]
    pareja = (av.SALUD, av.INGENIO)
    escena = av.Escena(
        "Un tramo exigente.", pareja,
        ("Resistir el cansancio", "Observar las señales"), "Volver",
    )
    terreno = av.Terreno(pareja, (1, 1))
    pruebas = (
        av.Prueba("Resistir", av.SALUD, 10, 20, 1),
        av.Prueba("Observar", av.INGENIO, 10, 20, 1),
    )
    viaje = av.Viaje(bioma, escena, terreno, pruebas=pruebas, nivel=2)

    resultado = economia.ejecutar_viaje(
        "u1", "g1", bicho.id, viaje.salida, T0, viaje=viaje
    )

    assert not resultado.problema
    assert db.marcador(bicho.id)[logros.NODOS] == 2


def test_volver_al_mismo_bioma_no_abre_uno_nuevo():
    bicho = nacer()
    for cuando in (T0, T0 + timedelta(hours=1)):
        viaje = viaje_de("planicie", nodos=0)
        economia.ejecutar_viaje(
            "u1", "g1", bicho.id, viaje.salida, cuando, viaje=viaje
        )

    marcador = db.marcador(bicho.id)
    assert marcador[logros.clave_de_bioma("planicie")] == 2
    assert sum(1 for c in marcador if c.startswith(logros.PREFIJO_BIOMA)) == 1


def test_el_viaje_que_no_se_confirma_no_cuenta():
    """Si el activo ya no es el que salió, no hay viaje y no hay marcador."""
    bicho = nacer()
    viaje = viaje_de()
    resultado = economia.ejecutar_viaje(
        "u1", "g1", bicho.id + 999, viaje.salida, T0, viaje=viaje
    )

    assert resultado.problema
    assert db.marcador(bicho.id) == {}


def test_reclutar_se_le_apunta_a_la_persona_y_no_a_ningun_gachamon():
    """A la aventura vas tú, así que el reclutamiento es tuyo. Ni el que salió
    ni el que se une llevan nada en su marcador."""
    aventurero = nacer(nombre="Aventurero")
    recluta = db.crear(
        "u1", "g1", "michi", sim.NOMBRE_PENDIENTE, STATS, T0,
        activa=False, reclutada=True,
    )

    assert db.marcador_de_persona("u1", "g1") == {logros.RECLUTADOS: 1}
    assert db.marcador(aventurero.id) == {}
    assert db.marcador(recluta.id) == {}


def test_los_reclutas_de_tus_gachamones_suman_en_el_mismo_sitio():
    """Antes cada gachamon llevaba su cuenta y «Flautista» pedía diez con el
    mismo: ahora se suman todos porque el que recluta eres tú."""
    nacer(nombre="Primero")
    for i in range(3):
        db.crear(
            "u1", "g1", "michi", f"Recluta{i}", STATS, T0,
            activa=False, reclutada=True,
        )
    db.crear("u2", "g1", "michi", "DeOtro", STATS, T0, reclutada=True)

    assert db.marcador_de_persona("u1", "g1") == {logros.RECLUTADOS: 3}
    assert db.marcador_de_persona("u2", "g1") == {logros.RECLUTADOS: 1}


def test_el_recluta_que_no_cabe_no_se_apunta():
    """El alta y el marcador van en la misma transacción justamente para esto:
    con el plantel lleno no puede quedar apuntado un salvaje que no se unió."""
    for i in range(db.MAXIMO_PLANTEL):
        nacer(nombre=f"Relleno{i}", activa=i == 0)

    with pytest.raises(ValueError):
        db.crear(
            "u1", "g1", "michi", sim.NOMBRE_PENDIENTE, STATS, T0,
            activa=False, reclutada=True,
        )

    assert db.marcador_de_persona("u1", "g1") == {}
