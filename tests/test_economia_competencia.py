# pyright: reportArgumentType=false
import asyncio
import random
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import competir as comp
import cogs.competencias as cog_comp
import db
import economia
import logros as lgr
import simulacion as sim
from cogs.competencias import Competencias

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "economia.db")
    db.inicializar()


def nacer(usuario, activa=True):
    return db.crear(usuario, "g1", "pulpo", usuario, STATS, T0, activa=activa)


def competir(evento, cuando=T0, usuarios=("u1", "u2"), semilla=1):
    return economia.ejecutar_competencia(
        evento, usuarios, "g1", comp.CARRERA, cuando, random.Random(semilla)
    )


def laberinto(evento, cuando=T0, usuarios=("u1", "u2"), rng=None):
    return economia.ejecutar_competencia(
        evento, usuarios, "g1", comp.LABERINTO,
        cuando, rng or random.Random(1),
    )


def test_recibo_de_competencia_detalla_efecto_costo_recompensa_y_tope():
    recibo = economia.ReciboCompetencia(
        usuario_id="u1",
        delta_asciicoins=economia.PREMIO_GANADOR,
        delta_competencia=economia.PREMIO_GANADOR,
        delta_evolucion=0,
        usados=1,
    )

    assert cog_comp.texto_recibo_competencia(
        recibo, "<@u1>", gano=True,
        stats=comp.STATS[comp.CARRERA], entrenada="velocidad",
    ) == (
        "-# <@u1> · velocidad +1 entrenamiento · +10 XP · "
        "coste base -10 comida · coste base -5 ánimo · "
        "🪙 +6 asciicoins · competencia 1/3 UTC"
    )


def test_el_recibo_del_totem_separa_las_tres_vetas_de_la_unica_entrenada():
    recibo = economia.ReciboCompetencia(
        usuario_id="u1",
        delta_asciicoins=economia.PREMIO_GANADOR,
        delta_competencia=economia.PREMIO_GANADOR,
        delta_evolucion=0,
        usados=1,
    )

    assert cog_comp.texto_recibo_competencia(
        recibo, "<@u1>", gano=True,
        stats=comp.STATS[comp.TOTEM], entrenada="fuerza",
    ).startswith(
        "-# <@u1> · velocidad, fuerza y salud dejan veta · "
        "fuerza +1 entrenamiento · "
    )


def test_testigo_elige_la_primera_reserva_nombrada_y_distingue_resultado():
    activa = db.crear("u1", "g1", "pulpo", "Sol", STATS, T0)
    sin_nombre = db.crear(
        "u1", "g1", "michi", sim.NOMBRE_PENDIENTE, STATS, T0, activa=False
    )
    primera = db.crear(
        "u1", "g1", "michi", "Luna", STATS, T0, activa=False
    )
    segunda = db.crear(
        "u1", "g1", "michi", "Bruma", STATS, T0, activa=False
    )
    # Va delante de Luna y aun así no reacciona: quien ya no está no presencia.
    muerta = replace(primera, nombre="Nube", muerta_en=T0)
    plantel = [activa, sin_nombre, muerta, primera, segunda]

    assert cog_comp.texto_testigo_competencia(plantel, activa, gano=True) == (
        "-# 👀 Desde la incubadora, **Luna** celebra a **Sol**."
    )
    assert cog_comp.texto_testigo_competencia(plantel, activa, gano=False) == (
        "-# 👀 Desde la incubadora, **Luna** espera a **Sol**."
    )


def test_testigo_no_sale_sin_reserva_nombrada():
    activa = nacer("u1")
    assert cog_comp.texto_testigo_competencia([activa], activa, gano=True) is None

    sin_nombre = db.crear(
        "u1", "g1", "michi", sim.NOMBRE_PENDIENTE, STATS, T0, activa=False
    )
    assert cog_comp.texto_testigo_competencia(
        [activa, sin_nombre], activa, gano=True
    ) is None


def test_testigo_con_cambio_de_activa_conserva_la_protagonista_del_evento():
    protagonista = db.crear("u1", "g1", "pulpo", "Sol", STATS, T0)
    nueva_activa = db.crear(
        "u1", "g1", "michi", "Luna", STATS, T0, activa=False
    )
    tercera = db.crear(
        "u1", "g1", "michi", "Bruma", STATS, T0, activa=False
    )
    plantel_tardio = [
        replace(protagonista, activa=False),
        replace(nueva_activa, activa=True),
        tercera,
    ]

    assert cog_comp.texto_testigo_competencia(
        plantel_tardio, protagonista, gano=True
    ) == "-# 👀 Desde la incubadora, **Bruma** celebra a **Sol**."
    assert cog_comp.texto_testigo_competencia(
        plantel_tardio[:2], protagonista, gano=True
    ) is None


def test_disputar_con_cambio_tardio_usa_protagonista_del_evento(monkeypatch):
    protagonista = db.crear("1", "g1", "pulpo", "Sol", STATS, T0)
    luna = db.crear(
        "1", "g1", "michi", "Luna", STATS, T0, activa=False
    )
    bruma = db.crear(
        "1", "g1", "michi", "Bruma", STATS, T0, activa=False
    )
    db.crear("2", "g1", "pulpo", "Rival", STATS, T0)
    resultado = competir(
        "evento-testigo-integrado", usuarios=("1", "2"), semilla=6
    )
    assert resultado.encuentro is not None
    assert resultado.encuentro.orden[0] == 0
    assert resultado.despues[0].id == protagonista.id

    planteles_tardios = {
        "1": [
            replace(resultado.despues[0], activa=False),
            replace(luna, activa=True),
            bruma,
        ],
        "2": [resultado.despues[1]],
    }
    monkeypatch.setattr(
        cog_comp.economia, "ejecutar_competencia", lambda *_: resultado
    )
    monkeypatch.setattr(cog_comp.db, "ahora_utc", lambda: T0)
    monkeypatch.setattr(
        cog_comp.db,
        "plantel",
        lambda usuario_id, guild_id: planteles_tardios[usuario_id],
    )
    monkeypatch.setattr(cog_comp.vistas, "congelar", AsyncMock())
    monkeypatch.setattr(cog_comp.vistas, "publicar_pantalla", AsyncMock())
    cog = Competencias.__new__(Competencias)
    cog._animar = AsyncMock()
    canal = SimpleNamespace(id="canal", send=AsyncMock())
    participantes = [
        SimpleNamespace(id=1, mention="<@1>", display_name="Dueña de Sol"),
        SimpleNamespace(id=2, mention="<@2>", display_name="Dueña de Rival"),
    ]

    asyncio.run(
        cog.disputar(canal, participantes, comp.CARRERA, "g1", "publicacion")
    )

    mensajes_testigo = [
        llamada.args[0]
        for llamada in canal.send.await_args_list
        if "👀" in llamada.args[0]
    ]
    assert mensajes_testigo == [
        "-# 👀 Desde la incubadora, **Bruma** celebra a **Sol**."
    ]


def test_recibo_de_competencia_conserva_topes_de_moneda_y_evolucion():
    recibo = economia.ReciboCompetencia(
        usuario_id="u1",
        delta_asciicoins=0,
        delta_competencia=0,
        delta_evolucion=0,
        usados=economia.TOPE_COMPETENCIAS,
        evolucion_usadas=economia.TOPE_EVOLUCIONES,
        topada=True,
        evoluciono=True,
        evolucion_topada=True,
    )

    assert cog_comp.texto_recibo_competencia(
        recibo, "<@u1>", gano=False,
        stats=comp.STATS[comp.SUMO], entrenada="fuerza",
    ).endswith(
        "🪙 +0 asciicoins · competencia 3/3 UTC (tope) · "
        "evolución +0 · evolución 1/1 UTC (tope)"
    )


def test_disputar_cinco_participantes_publica_recibos_emparejados_y_cabe(
    monkeypatch,
):
    usuarios = tuple(str(1_000_000_000_000_000_001 + n) for n in range(5))
    nombres = tuple(f"CriaturaLimite{n:010d}" for n in range(1, 6))
    assert all(len(nombre) == sim.LARGO_MAXIMO_NOMBRE for nombre in nombres)
    # Los testigos también van al largo máximo: es el caso que aprieta los
    # 2000 caracteres, y con nombres cortos el tope no se estaría midiendo.
    testigos = tuple(f"Testigo{n:017d}" for n in range(1, 6))
    assert all(len(testigo) == sim.LARGO_MAXIMO_NOMBRE for testigo in testigos)
    reservas = []
    for usuario, nombre, testigo in zip(usuarios, nombres, testigos):
        db.crear(usuario, "g1", "pulpo", nombre, STATS, T0)
        reservas.append(
            db.crear(
                usuario, "g1", "michi", testigo, STATS, T0, activa=False
            )
        )

    resultado = competir("evento-cinco", usuarios=usuarios, semilla=1)
    assert resultado.encuentro is not None
    assert tuple(criatura.nombre for criatura in resultado.antes) == nombres
    monkeypatch.setattr(
        cog_comp.economia, "ejecutar_competencia", lambda *_: resultado
    )
    monkeypatch.setattr(cog_comp.db, "ahora_utc", lambda: T0)
    monkeypatch.setattr(cog_comp.vistas, "congelar", AsyncMock())
    monkeypatch.setattr(cog_comp.vistas, "publicar_pantalla", AsyncMock())
    cog = Competencias.__new__(Competencias)
    cog._animar = AsyncMock()
    canal = SimpleNamespace(id="canal", send=AsyncMock())
    leer_plantel_db = db.plantel

    def leer_plantel(*args):
        assert len(canal.send.await_args_list) == 6
        return leer_plantel_db(*args)

    monkeypatch.setattr(cog_comp.db, "plantel", leer_plantel)
    participantes = [
        SimpleNamespace(
            id=int(usuario), mention=f"<@{usuario}>", display_name=nombre
        )
        for usuario, nombre in zip(usuarios, nombres)
    ]

    asyncio.run(
        cog.disputar(canal, participantes, comp.CARRERA, "g1", "publicacion")
    )

    # Primero el resumen con los cinco recibos, después una medalla por cabeza
    # y al final un único mensaje con todos los testigos.
    mandados = [llamada.args[0] for llamada in canal.send.await_args_list]
    resumen, *medallas, testigos_mensaje = mandados
    assert len(medallas) == 5
    assert all("De la alfa" in medalla for medalla in medallas)
    lineas = [linea for linea in resumen.splitlines() if linea.startswith("-# <@")]
    reacciones = testigos_mensaje.splitlines()
    assert len(resumen) < 2000
    assert "👀" not in resumen
    assert len(lineas) == 5
    assert len(testigos_mensaje) < 2000
    assert len(reacciones) == 5
    assert sum("👀" in mensaje for mensaje in mandados) == 1
    assert all(
        f"**{testigo}**" in linea and f"**{nombre}**" in linea
        for testigo, nombre, linea in zip(testigos, nombres, reacciones)
    )
    assert all("Desde la incubadora" in linea for linea in reacciones)
    assert sum(" celebra a " in linea for linea in reacciones) == 1
    assert sum(" espera a " in linea for linea in reacciones) == 4
    assert [linea.split(" · ", 1)[0] for linea in lineas] == [
        f"-# <@{usuario}>" for usuario in usuarios
    ]
    ganador = resultado.encuentro.orden[0]
    assert " celebra a " in reacciones[ganador]
    assert sum("+10 XP" in linea for linea in lineas) == 1
    assert sum("+4 XP" in linea for linea in lineas) == 4
    for dorsal, linea in enumerate(lineas):
        assert f"+{10 if dorsal == ganador else 4} XP" in linea
        assert "velocidad +1 entrenamiento" in linea
        assert "coste base -10 comida" in linea
        assert "coste base -5 ánimo" in linea

    assert [db.obtener(reserva.id) for reserva in reservas] == reservas
    for reserva in reservas:
        assert db.esperas(reserva.id, T0, (sim.COMPETIR,)) == {
            sim.COMPETIR: timedelta(0)
        }
        assert db.efectos_activos(reserva.id, T0) == {}
        assert db.marcador(reserva.id) == {}
        assert db.logros_de(reserva.id) == {}
    with db.conectar() as con:
        assert con.execute(
            "SELECT COUNT(*) FROM operaciones_economia WHERE tipo = 'competencia'"
        ).fetchone()[0] == 5


def test_competencia_acredita_6_al_ganador_y_4_al_resto_y_replay_no_muta():
    nacer("u1")
    nacer("u2")
    resultado = competir("evento")
    despues = (db.criatura_activa("u1", "g1"), db.criatura_activa("u2", "g1"))
    replay = competir("evento")

    assert sorted(r.delta_competencia for r in resultado.recibos) == [4, 6]
    assert all(r.usados == 1 for r in resultado.recibos)
    assert replay.replay
    assert sorted(r.delta_competencia for r in replay.recibos) == [4, 6]
    assert despues == (db.criatura_activa("u1", "g1"), db.criatura_activa("u2", "g1"))
    assert sum(economia.saldos(u, "g1").asciicoins for u in ("u1", "u2")) == 110


def test_los_bonus_de_fuerza_y_velocidad_llegan_a_las_fases_en_transaccion():
    uno = nacer("u1")
    nacer("u2")
    db.poner_efecto(uno.id, "fuerza", 10, T0)
    db.poner_efecto(uno.id, "velocidad", 20, T0)

    resultado = economia.ejecutar_competencia(
        "bonus", ("u1", "u2"), "g1", comp.CARRERA, T0, random.Random(1)
    )
    assert resultado.encuentro is not None
    combate = resultado.encuentro.combates[0]
    bases = [ronda.totales[0] - ronda.dados[0] for ronda in combate.rondas]
    assert bases == [37, 34, 31]  # +2 de ánimo, una vez tras cada mezcla


def test_cada_modalidad_entrena_solo_su_stat_primario():
    for usuario in ("u1", "u2", "u3", "u4"):
        nacer(usuario)

    economia.ejecutar_competencia(
        "carrera", ("u1", "u2"), "g1", comp.CARRERA, T0, random.Random(1)
    )
    economia.ejecutar_competencia(
        "sumo", ("u3", "u4"), "g1", comp.SUMO, T0, random.Random(2)
    )

    corredor = db.criatura_activa("u1", "g1")
    luchador = db.criatura_activa("u3", "g1")
    assert corredor is not None and luchador is not None
    assert corredor.ent_velocidad == sim.ENTRENAMIENTO_POR_COMPETIR
    assert corredor.ent_fuerza == 0
    assert luchador.ent_fuerza == sim.ENTRENAMIENTO_POR_COMPETIR
    assert luchador.ent_velocidad == 0


def test_el_totem_deja_un_solo_punto_de_entrenamiento_por_asalto():
    nacer("u1")
    nacer("u2")

    economia.ejecutar_competencia(
        "totem", ("u1", "u2"), "g1", comp.TOTEM, T0, random.Random(1)
    )

    asaltante = db.criatura_activa("u1", "g1")
    assert asaltante is not None
    assert (
        asaltante.ent_velocidad + asaltante.ent_fuerza + asaltante.ent_salud
    ) == sim.ENTRENAMIENTO_POR_COMPETIR


def test_el_recibo_nombra_la_estadistica_que_de_verdad_ha_subido():
    """El recibo y la ficha no pueden decir cosas distintas."""
    nacer("u1")
    nacer("u2")

    resultado = economia.ejecutar_competencia(
        "totem", ("u1", "u2"), "g1", comp.TOTEM, T0, random.Random(1)
    )

    for antes, despues in zip(resultado.antes, resultado.despues):
        subidas = [
            stat for stat in sim.ESTADISTICAS
            if getattr(despues, f"ent_{stat}") > getattr(antes, f"ent_{stat}")
        ]
        assert subidas == [sim.stat_a_entrenar(antes, comp.STATS[comp.TOTEM])]


def test_el_totem_apunta_su_marcador_y_no_el_de_la_carrera_ni_el_del_sumo():
    """Un tótem ganado no es un sumo ganado: `Yokozuna` no se cobra por aquí."""
    nacer("u1")
    nacer("u2")

    resultado = economia.ejecutar_competencia(
        "totem", ("u1", "u2"), "g1", comp.TOTEM, T0, random.Random(1)
    )

    assert resultado.encuentro is not None
    campeon = resultado.despues[resultado.encuentro.orden[0]]
    marcador = db.marcador(campeon.id)
    assert marcador.get(lgr.TOTEMS) == 1
    assert lgr.CARRERAS not in marcador
    assert lgr.SUMOS not in marcador
    assert lgr.TORNEOS not in marcador


def test_el_replay_de_un_totem_conserva_premios_y_marcador_sin_tirar_dados():
    class RngProhibido(random.Random):
        def randint(self, a, b):
            raise AssertionError("un replay no vuelve a tirar")

    nacer("u1")
    nacer("u2")
    primero = economia.ejecutar_competencia(
        "totem", ("u1", "u2"), "g1", comp.TOTEM, T0, random.Random(3)
    )
    marcadores = tuple(db.marcador(c.id) for c in primero.despues)

    replay = economia.ejecutar_competencia(
        "totem", ("u1", "u2"), "g1", comp.TOTEM, T0, RngProhibido()
    )

    assert replay.replay
    assert [r.delta_competencia for r in replay.recibos] == [
        r.delta_competencia for r in primero.recibos
    ]
    assert tuple(db.marcador(c.id) for c in primero.despues) == marcadores
    assert (
        db.criatura_activa("u1", "g1"), db.criatura_activa("u2", "g1")
    ) == primero.despues


def test_el_laberinto_apunta_su_marcador_y_no_los_otros():
    nacer("u1")
    nacer("u2")

    resultado = laberinto("laberinto-marcador")

    assert resultado.encuentro is not None
    campeon = resultado.despues[resultado.encuentro.orden[0]]
    marcador = db.marcador(campeon.id)
    assert marcador.get(lgr.LABERINTOS) == 1
    assert all(
        marcador.get(clave, 0) == 0
        for clave in (lgr.CARRERAS, lgr.SUMOS, lgr.TOTEMS, lgr.TORNEOS)
    )


def test_el_replay_del_laberinto_conserva_premios_sin_tirar_dados():
    class RngProhibido(random.Random):
        def randint(self, a, b):
            raise AssertionError("un replay no vuelve a tirar")

    nacer("u1")
    nacer("u2")
    primero = laberinto("laberinto-replay", rng=random.Random(3))
    laberinto("laberinto-posterior", T0 + timedelta(minutes=11))
    saldos = tuple(economia.saldos(usuario, "g1") for usuario in ("u1", "u2"))
    criaturas = tuple(
        db.criatura_activa(usuario, "g1") for usuario in ("u1", "u2")
    )

    replay = laberinto("laberinto-replay", rng=RngProhibido())

    assert replay.replay
    assert replay.recibos == primero.recibos
    assert tuple(
        economia.saldos(usuario, "g1") for usuario in ("u1", "u2")
    ) == saldos
    assert tuple(
        db.criatura_activa(usuario, "g1") for usuario in ("u1", "u2")
    ) == criaturas


def test_el_laberinto_entrena_solo_ingenio():
    nacidas = (nacer("u1"), nacer("u2"))

    resultado = laberinto("laberinto-entrena")

    for dorsal, (antes, despues, recibo) in enumerate(zip(
        nacidas, resultado.despues, resultado.recibos,
    )):
        assert despues.ent_ingenio == antes.ent_ingenio + 1
        assert (
            despues.ent_fuerza, despues.ent_velocidad, despues.ent_salud,
        ) == (antes.ent_fuerza, antes.ent_velocidad, antes.ent_salud)
        texto = cog_comp.texto_recibo_competencia(
            recibo,
            f"<@u{dorsal + 1}>",
            gano=resultado.encuentro is not None
            and dorsal == resultado.encuentro.orden[0],
            stats=comp.STATS[comp.LABERINTO],
            entrenada="ingenio",
        )
        assert "ingenio +1 entrenamiento" in texto


def test_el_laberinto_deja_veta_de_ingenio():
    uno = nacer("u1")
    nacer("u2")
    db.guardar(replace(uno, ten_ingenio=20.0))

    resultado = laberinto("laberinto-veta")

    sufijo = resultado.despues[0].historial_vetas.removeprefix(
        resultado.antes[0].historial_vetas
    )
    assert sufijo
    assert set(sufijo) == {"I"}


def test_la_ficha_se_republica_si_solo_se_movio_la_tension_de_ingenio():
    """El laberinto sólo tensa el ingenio: si la comparación se quedara en los
    tres canales de siempre, la ficha nueva no llegaría a publicarse nunca."""
    antes = nacer("u1")
    despues = replace(antes, ten_ingenio=antes.ten_ingenio + 3.0)

    assert cog_comp._ha_cambiado_la_ficha(antes, despues)
    assert not cog_comp._ha_cambiado_la_ficha(antes, replace(antes))


def test_disputar_un_laberinto_narra_beats_cierre_y_recibos(monkeypatch):
    """El seam donde se juntan las tres capas: motor, economía y Discord.

    Cada pieza tiene sus propias pruebas; ésta comprueba que el cog las une
    para una modalidad que no existía cuando se escribió `disputar`.
    """
    nacer("u1")
    nacer("u2")
    resultado = laberinto("laberinto-disputa")
    assert resultado.encuentro is not None

    monkeypatch.setattr(
        cog_comp.economia, "ejecutar_competencia", lambda *_: resultado
    )
    monkeypatch.setattr(cog_comp.db, "ahora_utc", lambda: T0)
    monkeypatch.setattr(cog_comp.vistas, "congelar", AsyncMock())
    monkeypatch.setattr(cog_comp.vistas, "publicar_pantalla", AsyncMock())
    animados = []

    async def animar(canal, fotogramas, tipo):
        del canal
        animados.append((fotogramas, tipo))

    cog = Competencias.__new__(Competencias)
    cog._animar = animar
    canal = SimpleNamespace(id="canal", send=AsyncMock())
    participantes = [
        SimpleNamespace(id=1000 + n, mention=f"<@{u}>", display_name=u)
        for n, u in enumerate(("u1", "u2"))
    ]

    asyncio.run(
        cog.disputar(canal, participantes, comp.LABERINTO, "g1", "laberinto-disputa")
    )

    (fotogramas, tipo), = animados
    assert tipo == comp.LABERINTO
    assert len(fotogramas) >= len(comp.FASES_LABERINTO)
    assert all("eco del pasillo" in fotograma for fotograma in fotogramas[:3])

    mandados = [llamada.args[0] for llamada in canal.send.await_args_list]
    resumen = mandados[0]
    assert "puertas abiertas." in resumen
    assert resumen.count("ingenio +1 entrenamiento") == 2
    assert all(len(mandado) < 2000 for mandado in mandados)


def test_el_laberinto_pone_cooldown_competir_a_todos():
    nacidas = (nacer("u1"), nacer("u2"))

    laberinto("laberinto-cooldown")

    assert all(
        db.espera_de(criatura.id, sim.COMPETIR, T0) > timedelta(0)
        for criatura in nacidas
    )


def test_el_laberinto_respeta_el_tope_diario_de_competencias():
    nacer("u1")
    nacer("u2")
    resultados = [
        laberinto(f"laberinto-tope-{i}", T0 + timedelta(minutes=11 * i))
        for i in range(4)
    ]

    ultimo = resultados[-1]
    assert all(recibo.topada for recibo in ultimo.recibos)
    assert all(
        "(tope)" in cog_comp.texto_recibo_competencia(
            recibo,
            f"<@u{dorsal + 1}>",
            gano=ultimo.encuentro is not None
            and dorsal == ultimo.encuentro.orden[0],
            stats=comp.STATS[comp.LABERINTO],
            entrenada="ingenio",
        )
        for dorsal, recibo in enumerate(ultimo.recibos)
    )


def test_sumo_paga_al_ganador_de_intercambios_y_el_replay_no_tira_dados():
    class Dados(random.Random):
        def __init__(self):
            super().__init__()
            self.valores = iter([2, 1, 1, 20, 2, 1])

        def randint(self, a, b):
            return next(self.valores, a)

    class RngProhibido(random.Random):
        def randint(self, a, b):
            raise AssertionError("un replay no vuelve a tirar")

        def shuffle(self, x):
            raise AssertionError("un replay no vuelve a sortear")

    nacer("u1")
    nacer("u2")
    resultado = economia.ejecutar_competencia(
        "sumo", ("u1", "u2"), "g1", comp.SUMO, T0, Dados()
    )

    assert resultado.encuentro is not None
    combate = resultado.encuentro.combates[0]
    assert combate.marcadores == (2, 1)
    assert combate.totales[0] < combate.totales[1]
    assert [r.delta_competencia for r in resultado.recibos] == [6, 4]
    uno = db.criatura_activa("u1", "g1")
    dos = db.criatura_activa("u2", "g1")
    assert uno is not None and uno.victorias == 1
    assert dos is not None and dos.derrotas == 1

    replay = economia.ejecutar_competencia(
        "sumo", ("u1", "u2"), "g1", comp.SUMO, T0, RngProhibido()
    )
    assert replay.replay
    assert [r.delta_competencia for r in replay.recibos] == [6, 4]


def test_cuarta_competencia_aplica_desgaste_pero_no_premia():
    nacer("u1")
    nacer("u2")
    resultados = [
        competir(f"evento-{i}", T0 + timedelta(minutes=11 * i), semilla=i)
        for i in range(4)
    ]
    assert all(r.delta_competencia == 0 and r.topada for r in resultados[-1].recibos)
    assert all(r.usados == 3 for r in resultados[-1].recibos)


def test_fallo_al_insertar_ledger_revierte_encuentro_completo():
    originales = (nacer("u1"), nacer("u2"))
    with db.conectar() as con:
        con.execute(
            "CREATE TRIGGER rompe_premio BEFORE INSERT ON operaciones_economia "
            "BEGIN SELECT RAISE(ABORT, 'fallo premio'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="fallo premio"):
        competir("evento")

    assert originales == (
        db.criatura_activa("u1", "g1"), db.criatura_activa("u2", "g1")
    )
    assert economia.saldos("u1", "g1") == economia.Saldos(50, 50)
    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM cooldowns").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM operaciones_economia").fetchone()[0] == 0


def test_competencia_rechaza_invitado_sin_activa_sin_filas_ni_deltas():
    uno = nacer("u1")
    dos = nacer("u2", activa=False)
    resultado = competir("evento")

    assert resultado.problema and resultado.problema_usuario_id == "u2"
    assert db.obtener(uno.id) == uno and db.obtener(dos.id) == dos
    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM operaciones_economia").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM monederos").fetchone()[0] == 0


def test_dos_resoluciones_concurrentes_del_mismo_evento_aplican_una_vez():
    nacer("u1")
    nacer("u2")
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(lambda _: competir("mismo"), range(2)))

    assert sum(resultado.replay for resultado in resultados) == 1
    with db.conectar() as con:
        assert con.execute(
            "SELECT COUNT(*) FROM operaciones_economia WHERE tipo = 'competencia'"
        ).fetchone()[0] == 2


def test_torneo_escribe_una_fila_por_persona_no_por_combate():
    for usuario in ("u1", "u2", "u3", "u4"):
        nacer(usuario)
    resultado = competir("torneo", usuarios=("u1", "u2", "u3", "u4"))
    assert len(resultado.recibos) == 4
    with db.conectar() as con:
        assert con.execute(
            "SELECT COUNT(*) FROM operaciones_economia WHERE tipo = 'competencia'"
        ).fetchone()[0] == 4


def test_evolucion_de_competencia_comparte_el_tope_diario():
    primero = nacer("u1")
    nacer("u2")
    db.guardar(replace(primero, xp=24))
    resultado = competir("evento")
    evolucionados = [r for r in resultado.recibos if r.evoluciono]
    assert evolucionados
    assert sum(r.delta_evolucion for r in evolucionados) == 10


def test_fallo_de_discord_ocurre_despues_del_commit_y_retry_no_reenvia(monkeypatch):
    nacer("u1")
    nacer("u2")
    monkeypatch.setattr(db, "ahora_utc", lambda: T0)
    cog = Competencias.__new__(Competencias)
    cog._animar = AsyncMock(side_effect=RuntimeError("discord caído"))
    monkeypatch.setattr(cog_comp.vistas, "congelar", AsyncMock())
    canal = SimpleNamespace(send=AsyncMock())
    usuarios = [
        SimpleNamespace(id="u1", mention="<@u1>", display_name="u1"),
        SimpleNamespace(id="u2", mention="<@u2>", display_name="u2"),
    ]

    with pytest.raises(RuntimeError, match="discord caído"):
        asyncio.run(cog.disputar(canal, usuarios, comp.CARRERA, "g1", "mensaje-1"))
    saldos = tuple(economia.saldos(u, "g1") for u in ("u1", "u2"))
    asyncio.run(cog.disputar(canal, usuarios, comp.CARRERA, "g1", "mensaje-1"))

    assert cog._animar.await_count == 1
    assert tuple(economia.saldos(u, "g1") for u in ("u1", "u2")) == saldos
    with db.conectar() as con:
        assert con.execute(
            "SELECT COUNT(*) FROM operaciones_economia WHERE tipo = 'competencia'"
        ).fetchone()[0] == 2


def test_competencia_congela_todas_las_fichas_antes_de_animar_y_no_repite(
    monkeypatch,
):
    antes = (
        replace(nacer("u1"), pantalla_msg_id="ficha-1", canal_id="101"),
        replace(nacer("u2"), pantalla_msg_id="ficha-2", canal_id="102"),
    )
    despues = (replace(antes[0], nivel=2), antes[1])
    resultado = SimpleNamespace(
        replay=False,
        problema=None,
        encuentro=SimpleNamespace(orden=(0, 1)),
        antes=antes,
        despues=despues,
        rupturas=((), ()),
        subidas=(("fuerza",), ()),
        recibos=(object(), object()),
    )
    eventos = []

    monkeypatch.setattr(cog_comp.db, "ahora_utc", lambda: T0)
    monkeypatch.setattr(
        cog_comp.economia, "ejecutar_competencia", lambda *_: resultado
    )
    monkeypatch.setattr(cog_comp.comp, "fotogramas_de", lambda _: [["tramo"]])
    monkeypatch.setattr(cog_comp.comp, "resumen", lambda _: "resumen")
    monkeypatch.setattr(
        cog_comp, "texto_recibo_competencia", lambda *_, **__: "recibo"
    )

    async def congelar(canal, mensaje_id):
        eventos.append(("congelar", canal, mensaje_id))

    async def animar(canal, fotogramas, tipo):
        eventos.append(("animar", canal, fotogramas, tipo))

    async def publicar(canal, criatura, ahora, **kwargs):
        eventos.append(("publicar", criatura, kwargs))

    monkeypatch.setattr(cog_comp.vistas, "congelar", congelar)
    monkeypatch.setattr(cog_comp.vistas, "publicar_pantalla", publicar)
    cog = Competencias.__new__(Competencias)
    cog._animar = animar
    canales_anteriores = {
        101: SimpleNamespace(id=101),
        102: SimpleNamespace(id=102),
    }
    canal = SimpleNamespace(
        id=999,
        guild=SimpleNamespace(get_channel_or_thread=canales_anteriores.get),
        send=AsyncMock(),
    )
    participantes = [
        SimpleNamespace(id="u1", mention="<@u1>", display_name="u1"),
        SimpleNamespace(id="u2", mention="<@u2>", display_name="u2"),
    ]

    asyncio.run(cog.disputar(canal, participantes, comp.CARRERA, "g1", "evento"))

    assert eventos[:3] == [
        ("congelar", canales_anteriores[101], "ficha-1"),
        ("congelar", canales_anteriores[102], "ficha-2"),
        ("animar", canal, ["tramo"], comp.CARRERA),
    ]
    assert eventos[-1][0] == "publicar"
    assert eventos[-1][2] == {"ya_congelada": "ficha-1"}
    assert not any(
        "👀" in (
            llamada.args[0] if llamada.args else llamada.kwargs.get("content") or ""
        )
        for llamada in canal.send.await_args_list
    )


def test_una_veta_sin_nivel_no_anuncia_una_subida(monkeypatch):
    primera = replace(nacer("u1"), ten_velocidad=20.0)
    db.guardar(primera)
    nacer("u2")
    resultado = competir("veta-sin-nivel")
    assert resultado.rupturas[0]
    assert resultado.antes[0].nivel == resultado.despues[0].nivel

    monkeypatch.setattr(cog_comp.db, "ahora_utc", lambda: T0)
    monkeypatch.setattr(
        cog_comp.economia, "ejecutar_competencia", lambda *_: resultado
    )
    monkeypatch.setattr(cog_comp.comp, "fotogramas_de", lambda _: [])
    monkeypatch.setattr(cog_comp.comp, "resumen", lambda _: "resumen")
    monkeypatch.setattr(
        cog_comp, "texto_recibo_competencia", lambda *_, **__: "recibo"
    )
    monkeypatch.setattr(cog_comp.vistas, "congelar", AsyncMock())
    monkeypatch.setattr(cog_comp.vistas, "publicar_pantalla", AsyncMock())
    canal = SimpleNamespace(id="canal", send=AsyncMock())
    participantes = [
        SimpleNamespace(id=usuario, mention=f"<@{usuario}>", display_name=usuario)
        for usuario in ("u1", "u2")
    ]

    cog = Competencias.__new__(Competencias)
    cog._animar = AsyncMock()
    asyncio.run(cog.disputar(
        canal, participantes, comp.CARRERA, "g1", "veta-sin-nivel"
    ))

    mensajes = [llamada.args[0] for llamada in canal.send.await_args_list]
    assert not any("sube a nivel" in mensaje for mensaje in mensajes)
    assert any("veta" in mensaje.lower() for mensaje in mensajes)


@pytest.mark.parametrize(
    "resultado",
    [
        SimpleNamespace(replay=True, problema=None),
        SimpleNamespace(
            replay=False,
            problema="no puede competir",
            problema_usuario_id=None,
        ),
    ],
)
def test_competencia_repetida_o_rechazada_no_congela(monkeypatch, resultado):
    congelar = AsyncMock()
    monkeypatch.setattr(cog_comp.db, "ahora_utc", lambda: T0)
    monkeypatch.setattr(
        cog_comp.economia, "ejecutar_competencia", lambda *_: resultado
    )
    monkeypatch.setattr(cog_comp.vistas, "congelar", congelar)
    leer_plantel = Mock(
        side_effect=AssertionError("replay o problema no debe leer el plantel")
    )
    monkeypatch.setattr(cog_comp.db, "plantel", leer_plantel)
    cog = Competencias.__new__(Competencias)
    canal = SimpleNamespace(send=AsyncMock())

    asyncio.run(cog.disputar(canal, [], comp.CARRERA, "g1", "evento"))

    congelar.assert_not_awaited()
    leer_plantel.assert_not_called()
    assert not any(
        "👀" in llamada.args[0] for llamada in canal.send.await_args_list
    )


def test_el_totem_deja_victoria_derrota_premio_y_enfriamiento_como_las_demas():
    nacer("u1")
    nacer("u2")

    resultado = economia.ejecutar_competencia(
        "totem", ("u1", "u2"), "g1", comp.TOTEM, T0, random.Random(1)
    )

    assert resultado.encuentro is not None
    ganador = resultado.encuentro.orden[0]
    for dorsal, criatura in enumerate(resultado.despues):
        assert criatura.victorias == (1 if dorsal == ganador else 0)
        assert criatura.derrotas == (0 if dorsal == ganador else 1)
        assert db.espera_de(criatura.id, sim.COMPETIR, T0) == (
            sim.COOLDOWNS[sim.COMPETIR]
        )
    assert sorted(r.delta_competencia for r in resultado.recibos) == [4, 6]


def test_el_mensaje_final_de_un_totem_de_cinco_cabe_en_un_mensaje_de_discord():
    """Cinco recibos con las tres estadísticas es el caso que más aprieta."""
    usuarios = tuple(str(1_000_000_000_000_000_001 + n) for n in range(5))
    nombres = tuple(f"CriaturaLimite{n:010d}" for n in range(1, 6))
    assert all(len(nombre) == sim.LARGO_MAXIMO_NOMBRE for nombre in nombres)
    for usuario, nombre in zip(usuarios, nombres):
        db.crear(usuario, "g1", "pulpo", nombre, STATS, T0)

    resultado = economia.ejecutar_competencia(
        "totem-cinco", usuarios, "g1", comp.TOTEM, T0, random.Random(1)
    )

    assert resultado.encuentro is not None
    ganador = resultado.encuentro.orden[0]
    recibos = "\n".join(
        cog_comp.texto_recibo_competencia(
            recibo, f"<@{usuario}>",
            gano=dorsal == ganador,
            stats=comp.STATS[comp.TOTEM],
            entrenada=sim.stat_a_entrenar(antes, comp.STATS[comp.TOTEM]),
        )
        for dorsal, (recibo, usuario, antes) in enumerate(
            zip(resultado.recibos, usuarios, resultado.antes)
        )
    )
    mensaje = f"{comp.resumen(resultado.encuentro)}\n{recibos}"

    assert len(mensaje) < 2000, len(mensaje)
    assert mensaje.count("velocidad, fuerza y salud dejan veta") == 5
    assert mensaje.count("+1 entrenamiento") == 5


def test_un_totem_que_evoluciona_publica_veta_de_nivel_y_crecimiento_visible():
    """Integración: la evolución que confirma la transacción es la que crece.

    Con fuerza, salud e ingenio ya en el tope visible, la única que puede
    crecer es la velocidad, y el tótem no puede dejarla sin veta.
    """
    for usuario in ("u1", "u2"):
        nacida = db.crear(
            usuario, "g1", "pulpo", usuario,
            (sim.MAXIMO_STAT, 50, sim.MAXIMO_STAT, sim.MAXIMO_STAT), T0,
        )
        db.guardar(replace(
            nacida,
            xp=sim.xp_para_subir(1) - sim.XP_VICTORIA,
            ent_fuerza=1, ent_velocidad=1, ent_salud=1, ten_salud=35.0,
        ))

    resultado = economia.ejecutar_competencia(
        "totem-evo", ("u1", "u2"), "g1", comp.TOTEM, T0, random.Random(1)
    )

    assert resultado.encuentro is not None
    ganador = resultado.encuentro.orden[0]
    antes = resultado.antes[ganador]
    despues = resultado.despues[ganador]

    assert antes.etapa != despues.etapa
    assert (antes.fuerza, antes.velocidad, antes.salud, antes.ingenio) == (
        sim.MAXIMO_STAT, 51, sim.MAXIMO_STAT, sim.MAXIMO_STAT,
    )
    assert (despues.fuerza, despues.velocidad, despues.salud, despues.ingenio) == (
        sim.MAXIMO_STAT, 52, sim.MAXIMO_STAT, sim.MAXIMO_STAT,
    )

    rupturas = resultado.rupturas[ganador]
    assert len(rupturas) <= sim.MAX_RUPTURAS_POR_SUCESO
    assert any(ruptura.causa == "nivel" for ruptura in rupturas)
    assert resultado.recibos[ganador].evoluciono
    # Lo publicado es lo confirmado: la ficha guardada es la misma que se narra.
    assert db.criatura_activa(
        resultado.recibos[ganador].usuario_id, "g1"
    ) == despues


# --- Que el bonus de una poción llegue a las cuatro estadísticas -------------
#
# Hasta que existió la sopaipilla arcoíris, ningún objeto tocaba salud ni
# ingenio, así que `ejecutar_competencia` sólo leía fuerza y velocidad. Un
# efecto en las otras dos se habría guardado, se habría pintado en la ficha y no
# habría hecho **nada** en el tótem ni en el laberinto: la peor clase de fallo,
# el que se ve y miente.

def test_el_competidor_acepta_un_bonus_por_cada_estadistica():
    """`ejecutar_competencia` los pasa por nombre recorriendo
    `sim.ESTADISTICAS`. Si aquí faltara uno, la competencia entera reventaría
    con un `TypeError` la primera vez que alguien compitiera."""
    import inspect

    firma = inspect.signature(comp.competidor_de).parameters
    for stat in sim.ESTADISTICAS:
        assert f"bonus_{stat}" in firma, stat


def test_la_competencia_recoge_el_efecto_de_las_cuatro_estadisticas():
    """La mitad de arriba de la tubería: lo que hay guardado llega a la pista.

    Se mira el competidor que se armó y no el resultado de la carrera porque
    competir **cambia a la criatura** —experiencia y vetas—, así que correr dos
    veces para comparar no aísla el efecto: la segunda tirada ya no es la misma
    criatura.
    """
    bicho = nacer("u1")
    nacer("u2")
    puestos = {"fuerza": 11, "velocidad": 22, "salud": 33, "ingenio": 44}
    for stat, cuanto in puestos.items():
        db.poner_efecto(bicho.id, stat, cuanto, T0)

    encuentro = economia.ejecutar_competencia(
        "evento", ("u1", "u2"), "g1", comp.TOTEM, T0, random.Random(7)
    ).encuentro

    corredor = encuentro.competidores[0]
    for stat, cuanto in puestos.items():
        assert getattr(corredor, f"bonus_{stat}") == cuanto, stat


@pytest.mark.parametrize(
    "stat, fase",
    [
        ("fuerza", comp.EMPUJE),
        ("velocidad", comp.SALIDA),
        ("salud", comp.HUIDA),
        ("ingenio", comp.SENALES),
    ],
)
def test_el_bonus_de_cada_estadistica_cuenta_en_su_fase(stat, fase):
    """La mitad de abajo: una vez en la pista, el bonus suma.

    Cada fase de las elegidas se juega con **una sola estadística entera y sin
    mezclar**, así que el aporte tiene que subir exactamente lo que se puso.
    """
    bicho = nacer("u1")
    ventaja = 40

    sin_efecto = comp.competidor_de(bicho).base_en(fase)
    con_efecto = comp.competidor_de(bicho, **{f"bonus_{stat}": ventaja})

    assert con_efecto.base_en(fase) == sin_efecto + ventaja
