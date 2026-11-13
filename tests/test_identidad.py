from dataclasses import replace
from datetime import datetime, timedelta, timezone

import ast
from pathlib import Path

import pytest

import aventura
import casas
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


def test_volver_a_arrancar_no_le_devuelve_el_reloj_de_aviso():
    db.crear(WEB, "g", "pollito", "Pelusa", STATS, T0)
    db.crear(DISCORD, "g", "pollito", "Otra", STATS, T0)
    antes = relojes_de(DISCORD)
    db.inicializar()
    assert relojes_de(WEB) == [(None, None, None)]
    assert relojes_de(DISCORD) == antes
    lejos = T0 + timedelta(days=30)
    assert {c.usuario_id for c in db.pendientes_de_aviso(lejos)} == {DISCORD}


def test_volver_a_arrancar_no_le_pone_aviso_a_la_de_la_incubadora():
    db.crear(DISCORD, "g", "pollito", "Uno", STATS, T0)
    db.crear(DISCORD, "g", "pulpo", "Dos", STATS, T0, activa=False)
    db.inicializar()
    with db.conectar() as con:
        avisos = [f[0] for f in con.execute(
            "SELECT avisa_en FROM criaturas WHERE activa = 0")]
    assert avisos == [None]


def test_el_viaje_no_mata_de_hambre_a_quien_no_tiene_aviso():
    cansada = aventura.aplicar_desgaste(
        criatura(WEB, hambre=1.0), aventura.Salida(()), T0
    )
    assert cansada.viva
    assert cansada.hambre == 0.0
    assert cansada.muerta_en is None
    assert cansada.causa_muerte is None


def test_el_viaje_sigue_matando_de_hambre_a_una_identidad_de_discord():
    cansada = aventura.aplicar_desgaste(
        criatura(DISCORD, hambre=1.0), aventura.Salida(()), T0
    )
    assert not cansada.viva
    assert cansada.muerta_en == T0
    assert cansada.causa_muerte == "hambre"


def _asigna_hambre(arbol: ast.AST) -> bool:
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.keyword) and nodo.arg == "causa_muerte":
            valores = [nodo.value]
        elif isinstance(nodo, ast.Assign) and any(
            isinstance(t, ast.Attribute) and t.attr == "causa_muerte"
            for t in nodo.targets
        ):
            valores = [nodo.value]
        else:
            continue
        for valor in valores:
            if any(
                isinstance(n, ast.Constant) and n.value == "hambre"
                for n in ast.walk(valor)
            ):
                return True
    return False


def test_solo_la_simulacion_y_la_aventura_matan_de_hambre():
    """Impide que aparezca un tercer camino que mate de hambre sin respetar
    `identidad.sin_aviso_de_hambre`. Si esta prueba falla, hay un sitio nuevo
    que asigna `causa_muerte="hambre"`: mira si respeta la excepción y, sólo
    entonces, añádelo a la lista."""
    raiz = Path(__file__).resolve().parent.parent
    rutas = sorted(raiz.glob("*.py")) + sorted((raiz / "cogs").glob("*.py"))
    assert rutas
    con_hambre = {
        ruta.name for ruta in rutas
        if _asigna_hambre(ast.parse(ruta.read_text(encoding="utf-8")))
    }
    assert con_hambre == {"simulacion.py", "aventura.py"}


def test_quien_juega_solo_en_la_web_no_tiene_plazo_en_el_refugio():
    assert identidad.sin_plazo_de_refugio(identidad.de_cuenta_web(12)) is True
    assert identidad.sin_plazo_de_refugio("222222222222222222") is False


def test_una_identidad_web_nunca_queda_a_la_intemperie():
    web = identidad.de_cuenta_web(1)
    db.hogar_de(web, "g", T0)                       # empieza la estancia, como hará comprar una casa
    mucho_despues = T0 + timedelta(days=400)
    hogar = db.hogar_leido(web, "g", mucho_despues)
    assert hogar.estado(mucho_despues) == casas.REFUGIO
    assert hogar.estado_de(None, mucho_despues) == casas.REFUGIO


def test_a_quien_viene_de_discord_el_plazo_le_corre_como_siempre():
    db.hogar_de(DISCORD, "g", T0)
    despues = T0 + timedelta(days=casas.DIAS_DE_REFUGIO, seconds=1)
    assert db.hogar_leido(DISCORD, "g", despues).estado(despues) == casas.INTEMPERIE


def test_una_identidad_web_que_vende_su_casa_sigue_en_el_refugio():
    web = identidad.de_cuenta_web(1)
    db.crear(web, "g", "pulpo", "Kuro", STATS, T0)
    with db.conectar() as con:
        economia._asegurar_monedero(con, web, "g")
        con.execute("UPDATE monederos SET asciicoins = 5000 WHERE usuario_id = ?", (web,))
    comprada = economia.comprar_casa(web, "g", casas.CATALOGO["mediana"], T0)
    assert comprada.ok
    casa_id = db.hogar_leido(web, "g", T0).casas[0].id
    assert economia.vender_casa(web, "g", casa_id, T0).ok
    despues = T0 + timedelta(days=30)
    hogar = db.hogar_leido(web, "g", despues)
    assert hogar.casas == () and hogar.estado(despues) == casas.REFUGIO
