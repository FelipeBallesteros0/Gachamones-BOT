from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import economia
import identidad
import simulacion as sim

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (10, 10, 10, 10)
WEB = identidad.de_cuenta_web(12)
DISCORD = "123456789012345678"


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "identidad.db")
    db.inicializar()


def criatura(usuario_id: str, **cambios) -> sim.Criatura:
    base = sim.Criatura(
        id=1, usuario_id=usuario_id, guild_id="g", especie="pollito",
        nombre="Pelusa", nacida_en=T0, actualizada_en=T0, base_salud=10,
    )
    return replace(base, **cambios)


def relojes_de(usuario_id: str) -> list[tuple]:
    with db.conectar() as con:
        return [
            tuple(fila) for fila in con.execute(
                "SELECT muere_en, avisa_en, muerta_en FROM criaturas "
                "WHERE usuario_id = ?", (usuario_id,),
            )
        ]


@pytest.mark.parametrize("usuario_id, esperado", [
    ("-12", True), ("-1", True),
    (DISCORD, False), ("12", False), ("", False), ("-", False),
    ("-0", False), ("-012", False), ("--12", False), ("-1.5", False),
    ("-12 ", False), (" -12", False), ("abc", False),
])
def test_solo_un_entero_positivo_en_negativo_es_identidad_web(usuario_id, esperado):
    assert identidad.es_web(usuario_id) is esperado


def test_la_identidad_de_una_cuenta_es_su_numero_en_negativo():
    assert identidad.de_cuenta_web(12) == "-12"
    assert identidad.es_web(identidad.de_cuenta_web(1))
    with pytest.raises(ValueError):
        identidad.de_cuenta_web(0)


def test_hoy_quien_no_tiene_aviso_es_justo_la_identidad_web():
    assert identidad.sin_aviso_de_hambre(WEB)
    assert not identidad.sin_aviso_de_hambre(DISCORD)


def test_el_hambre_no_mata_al_gachamon_de_una_identidad_web():
    avanzada = sim.avanzar(criatura(WEB), T0 + timedelta(days=30))
    assert avanzada.viva and avanzada.muerta_en is None
    assert avanzada.hambre == 0.0


def test_el_hambre_sigue_matando_al_de_una_identidad_de_discord():
    avanzada = sim.avanzar(criatura(DISCORD), T0 + timedelta(days=30))
    assert not avanzada.viva
    assert avanzada.causa_muerte == "hambre"


def test_al_de_una_identidad_web_le_bajan_las_tres_barras_como_a_cualquiera():
    diez_horas = T0 + timedelta(hours=10)
    web = sim.avanzar(criatura(WEB), diez_horas)
    discord = sim.avanzar(criatura(DISCORD), diez_horas)
    assert (web.hambre, web.animo, web.limpieza) == (
        discord.hambre, discord.animo, discord.limpieza
    )
    assert web.hambre < 100


def test_a_una_identidad_web_no_se_le_guarda_reloj_de_muerte_ni_de_aviso():
    db.crear(WEB, "g", "pollito", "Pelusa", STATS, T0)
    db.crear(DISCORD, "g", "pollito", "Otra", STATS, T0)
    assert relojes_de(WEB) == [(None, None, None)]
    muere_en, avisa_en, _ = relojes_de(DISCORD)[0]
    assert muere_en is not None and avisa_en is not None


def test_los_bucles_del_bot_nunca_ven_a_una_identidad_web():
    db.crear(WEB, "g", "pollito", "Pelusa", STATS, T0)
    db.crear(DISCORD, "g", "pollito", "Otra", STATS, T0)
    lejos = T0 + timedelta(days=30)
    assert {c.usuario_id for c in db.pendientes_de_morir(lejos)} == {DISCORD}
    assert {c.usuario_id for c in db.pendientes_de_aviso(lejos)} == {DISCORD}


def test_cambiar_de_activo_no_le_devuelve_la_muerte():
    db.crear(WEB, "g", "pollito", "Uno", STATS, T0)
    reserva = db.crear(WEB, "g", "pulpo", "Dos", STATS, T0, activa=False)
    assert db.activar(reserva.id, WEB, "g", T0 + timedelta(hours=1))
    assert all(reloj == (None, None, None) for reloj in relojes_de(WEB))


def test_tras_dias_en_cero_come_con_normalidad_y_sigue_sin_reloj():
    # Cinco días y no treinta: tiene que caer dentro de los siete de refugio.
    # Pasados esos, quien no tiene casa está a la intemperie y ahí el hambre ya
    # tiene un suelo de 25 para todo el mundo, así que no se probaría nada.
    db.crear(WEB, "g", "pollito", "Pelusa", STATS, T0)
    resultado = economia.ejecutar_cuidado(
        "evento-1", WEB, "g", sim.ALIMENTAR, T0 + timedelta(days=5)
    )
    assert resultado is not None and resultado.ok
    assert resultado.criatura.viva
    assert resultado.criatura.hambre == sim.EFECTOS_CUIDADO[sim.ALIMENTAR]["hambre"]
    assert relojes_de(WEB) == [(None, None, None)]
