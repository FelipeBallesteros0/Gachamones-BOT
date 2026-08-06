"""Reglas locales de VETAS: física, persistencia y cableado mínimo."""
import random
import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import aventura as av
import competir as comp
import db
import economia
import pantalla
import simulacion as sim

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def criatura(**cambios) -> sim.Criatura:
    datos: dict[str, Any] = dict(
        id=7,
        usuario_id="u1",
        guild_id="g1",
        especie="pulpo",
        nombre="Prueba",
        nacida_en=T0,
        actualizada_en=T0,
        base_fuerza=15,
        base_velocidad=15,
        base_salud=15,
        base_ingenio=15,
    )
    datos.update(cambios)
    return sim.Criatura(**datos)


def test_impronta_es_determinista_y_no_se_persiste():
    c = criatura()
    primera = sim.impronta_de(c)
    segunda = sim.impronta_de(c)
    assert primera == segunda
    assert primera.giro in (-1, 1)
    assert len(primera.afinidades) == 4
    assert c.historial_vetas == ""


def test_receptividad_respeta_los_limites_y_el_anillo():
    c = criatura(niv_fuerza=4, niv_velocidad=1, niv_salud=2)
    assert all(0.35 <= sim.receptividad(c, stat) <= 3.0 for stat in sim.ESTADISTICAS)
    assert set(sim.impronta_de(c).anillo) == set(sim.ESTADISTICAS)


def test_impulso_refuerza_y_la_veta_anterior_proyecta_sombra():
    c = criatura()
    objetivo = "fuerza"
    anillo = sim.impronta_de(c).anillo
    anterior = anillo[(anillo.index(objetivo) - 1) % len(anillo)]
    siguiente = anillo[(anillo.index(objetivo) + 1) % len(anillo)]
    propia = replace(c, niv_fuerza=1)
    con_anterior = replace(c, **{f"niv_{anterior}": 1})
    con_siguiente = replace(c, **{f"niv_{siguiente}": 1})

    assert sim.receptividad(propia, objetivo) > sim.receptividad(c, objetivo)
    assert sim.receptividad(con_anterior, objetivo) < sim.receptividad(
        con_siguiente, objetivo
    )


def test_esfuerzos_aplican_formula_y_filtro_notable():
    esfuerzo = sim.esfuerzo_de_cuidado(criatura(hambre=100), sim.ALIMENTAR)
    assert esfuerzo is not None and esfuerzo.bruto == 0
    entrenamiento = sim.esfuerzo_de_cuidado(
        criatura(hambre=40, animo=100), sim.ENTRENAR
    )
    assert entrenamiento is not None
    assert entrenamiento.bruto == 1.5
    suave = sim.aplicar_accion(criatura(), sim.JUGAR, T0)
    assert suave.criatura.ten_velocidad == 0
    assert not suave.rupturas


def test_entrenamiento_conjunto_usa_barras_previas_y_causa_entrenar():
    c = criatura(hambre=20.0, animo=100.0)

    resultado = sim.aplicar_entrenamiento_conjunto(c)

    esperado = 2.0 * sim.ESCALA * sim.receptividad(c, "fuerza")
    assert abs(resultado.criatura.ten_fuerza - esperado) < 1e-12
    assert resultado.criatura.hambre == 10.0


def test_cada_participante_resuelve_nivel_evolucion_y_tope_de_vetas_por_separado():
    base = dict(
        xp=sim.xp_para_subir(1) - 1,
        hambre=40.0,
        ten_fuerza=100.0,
        ten_velocidad=100.0,
        ten_salud=100.0,
    )

    activo = sim.aplicar_entrenamiento_conjunto(criatura(id=7, **base))
    reserva = sim.aplicar_entrenamiento_conjunto(
        criatura(id=8, activa=False, **base)
    )

    assert activo.evoluciono and reserva.evoluciono
    assert activo.criatura.nivel == reserva.criatura.nivel == 2
    assert len(activo.rupturas) == len(reserva.rupturas) == 3
    assert all(r.causa == "nivel" for r in activo.rupturas + reserva.rupturas)


def test_emision_profunda_multiplica_y_no_deja_tension_negativa():
    c = criatura(hambre=10)
    esfuerzo = sim.esfuerzo_de_cuidado(c, sim.ALIMENTAR)
    assert esfuerzo is not None and esfuerzo.profunda
    marcada, _ = sim.emitir_tension(c, esfuerzo)
    assert marcada.ten_salud >= 0
    assert marcada.ten_salud > 0
    normal, _ = sim.emitir_tension(
        c, sim.Esfuerzo("fuerza", 1.0, forzar=True)
    )
    subumbral_profunda, _ = sim.emitir_tension(
        c, sim.Esfuerzo("fuerza", 1.0, profunda=True)
    )
    assert abs(
        subumbral_profunda.ten_fuerza - normal.ten_fuerza * sim.PROFUNDA
    ) < 1e-12


def test_decaimiento_de_tension_es_lazy_y_no_toca_reservas_ni_muertas():
    c = criatura(ten_fuerza=20, ten_velocidad=10, ten_salud=5, ten_ingenio=8)
    una = sim.avanzar(c, T0 + timedelta(hours=18))
    assert una.ten_fuerza == 10
    assert una.ten_velocidad == 5
    assert una.ten_salud == 2.5
    assert una.ten_ingenio == 4
    assert sim.avanzar(una, T0 + timedelta(hours=18)) == una
    reserva = replace(c, activa=False)
    muerta = replace(c, muerta_en=T0, causa_muerte="hambre")
    assert sim.avanzar(reserva, T0 + timedelta(days=2)) == reserva
    assert sim.avanzar(muerta, T0 + timedelta(days=2)) == muerta


def test_umbral_global_y_rupturas_deterministas_con_maximo_tres():
    c = criatura(ten_fuerza=100, ten_velocidad=100, ten_salud=100)
    assert sim.umbral_veta(c) == 20
    marcada, rupturas = sim.romper_vetas(c)
    assert len(rupturas) == sim.MAX_RUPTURAS_POR_SUCESO
    assert rupturas[0].stat == "fuerza"
    assert len(marcada.historial_vetas) == 3
    assert min(getattr(marcada, f"ten_{stat}") for stat in sim.ESTADISTICAS) >= 0
    assert sim.umbral_veta(marcada) == 32


def test_cascada_marca_la_ruptura_arrastrada_y_no_la_que_alimenta():
    origen, siguiente = sim.impronta_de(criatura()).anillo[:2]
    tensiones = {f"ten_{stat}": 0.0 for stat in sim.ESTADISTICAS}
    tensiones[f"ten_{origen}"] = 20.0
    tensiones[f"ten_{siguiente}"] = 14.0

    _, rupturas = sim.romper_vetas(criatura(**tensiones))

    assert [ruptura.stat for ruptura in rupturas] == [origen, siguiente]
    assert [ruptura.cascada for ruptura in rupturas] == [False, True]


def test_el_tope_no_anuncia_una_cascada_que_queda_pendiente():
    origen, siguiente = sim.impronta_de(criatura()).anillo[:2]
    tensiones = {f"ten_{stat}": 0.0 for stat in sim.ESTADISTICAS}
    tensiones[f"ten_{origen}"] = 72.0

    marcada, rupturas = sim.romper_vetas(criatura(**tensiones))

    assert len(rupturas) == sim.MAX_RUPTURAS_POR_SUCESO
    assert not any(ruptura.cascada for ruptura in rupturas)
    assert getattr(marcada, f"ten_{siguiente}") >= sim.umbral_veta(marcada)


def test_cuidado_y_subida_comparten_el_mismo_tope_de_tres():
    """Tres en total, y la última es de la subida.

    El cuidado se queda con dos porque el suceso aparta una para el nivel: es
    la que garantiza que evolucionar se note en alguna estadística visible.
    """
    c = criatura(
        xp=sim.xp_para_subir(1) - 1,
        hambre=40.0,
        ten_fuerza=100.0,
        ten_velocidad=100.0,
        ten_salud=100.0,
    )

    resultado = sim.aplicar_accion(c, sim.ENTRENAR, T0)

    assert resultado.criatura.nivel == 2
    assert len(resultado.rupturas) == sim.MAX_RUPTURAS_POR_SUCESO
    assert [ruptura.causa for ruptura in resultado.rupturas] == [
        sim.ENTRENAR, sim.ENTRENAR, "nivel",
    ]
    assert all(ruptura.despues == ruptura.antes + 1 for ruptura in resultado.rupturas)


def test_mismo_estado_y_evento_dan_el_mismo_resultado_sin_rng():
    c = criatura(hambre=35, animo=40)
    a = sim.aplicar_accion(c, sim.ENTRENAR, T0, random.Random(1))
    b = sim.aplicar_accion(c, sim.ENTRENAR, T0, random.Random(999))
    assert a == b
    uno, _ = sim.aplicar_xp(c, 900, random.Random(1))
    dos, _ = sim.aplicar_xp(c, 900, random.Random(999))
    assert uno == dos


def test_subida_de_nivel_conserva_xp_y_usa_surge_determinista():
    c = criatura(xp=sim.xp_para_subir(1) - 1)
    subida, rupturas = sim.aplicar_xp(c, 1)
    assert subida.nivel == 2 and subida.xp == 0
    assert all(r.stat in sim.ESTADISTICAS for r in rupturas)
    assert subida.ten_fuerza + subida.ten_velocidad + subida.ten_salud > 0


def test_competencia_usa_margen_derrota_y_veta_profunda():
    amplia = sim.esfuerzo_de_competencia("velocidad", margen=30, gano=True)
    derrota = sim.esfuerzo_de_competencia("velocidad", margen=30, gano=False)
    cerrada = sim.esfuerzo_de_competencia("velocidad", margen=2, gano=True)
    assert amplia.bruto == 1.5
    assert abs(derrota.bruto - 1.95) < 1e-12
    assert cerrada.profunda


def test_las_tres_marcas_del_totem_comparten_el_tope_de_tres_rupturas():
    c = criatura(ten_fuerza=100.0, ten_velocidad=100.0, ten_salud=100.0)

    _, rupturas = sim.aplicar_competencia(
        c, True, comp.STATS[comp.TOTEM], margen=0
    )

    assert len(rupturas) == sim.MAX_RUPTURAS_POR_SUCESO


def test_aventura_emite_cada_prueba_y_anade_salud_al_fallar():
    salida = av.Salida((
        av.Prueba("f", "fuerza", 20, 0, 20),
        av.Prueba("v", "velocidad", 10, 1, 30),
    ))
    esfuerzos = av.esfuerzos_de_viaje(salida)
    assert [e.stat for e in esfuerzos] == ["fuerza", "velocidad", "salud"]
    assert esfuerzos[-1].bruto == 1.0


def test_margen_de_competencia_usa_el_ultimo_combate():
    a = comp.Competidor("a", "pulpo", 10, 10, 10)
    b = comp.Competidor("b", "pulpo", 10, 10, 10)
    resultado = comp.Resultado(
        comp.CARRERA, (a, b),
        [comp.Ronda((1, 1), (11, 11)), comp.Ronda((3, 1), (13, 11))],
        (0, 1),
    )
    encuentro = comp.Encuentro(comp.CARRERA, (a, b), (resultado,), (0, 1), resultado.totales)
    assert comp.margen_de(encuentro, 0) == 2
    assert comp.margen_de(encuentro, 1) == 2


def test_margen_multijugador_compara_con_quien_gana():
    competidores = tuple(
        comp.Competidor(nombre, "pulpo", 10, 10, 10)
        for nombre in ("a", "b", "c")
    )
    resultado = comp.Resultado(
        comp.CARRERA,
        competidores,
        [comp.Ronda((1, 1, 1), (90, 60, 59))],
        (0, 1, 2),
    )
    encuentro = comp.Encuentro(
        comp.CARRERA, competidores, (resultado,), (0, 1, 2), resultado.totales
    )
    assert [comp.margen_de(encuentro, dorsal) for dorsal in range(3)] == [30, 30, 31]


def test_margen_de_sumo_usa_el_intercambio_que_da_la_segunda_victoria():
    a = comp.Competidor("a", "pulpo", 10, 10, 10)
    b = comp.Competidor("b", "pulpo", 10, 10, 10)
    resultado = comp.Resultado(
        comp.SUMO,
        (a, b),
        [
            comp.Ronda((2, 1), (12, 11), comp.POSICION, 0),
            comp.Ronda((1, 20), (11, 30), comp.EMPUJE, 1),
            comp.Ronda((5, 2), (15, 12), comp.AGUANTE, 0),
        ],
        (0, 1),
    )
    encuentro = comp.Encuentro(
        comp.SUMO, (a, b), (resultado,), (0, 1), resultado.marcadores
    )

    assert comp.margen_de(encuentro, 0) == 3
    assert comp.margen_de(encuentro, 1) == 3


def test_margen_de_sumo_puede_ser_cero_tras_el_fallback_acotado():
    a = comp.Competidor("a", "pulpo", 10, 10, 10)
    b = comp.Competidor("b", "pulpo", 10, 10, 10)
    resultado = comp.Resultado(
        comp.SUMO,
        (a, b),
        [
            comp.Ronda((7, 7), (17, 17), comp.POSICION, 0, comp.MAX_DESEMPATES),
            comp.Ronda((7, 7), (17, 17), comp.EMPUJE, 0, comp.MAX_DESEMPATES),
        ],
        (0, 1),
    )
    encuentro = comp.Encuentro(
        comp.SUMO, (a, b), (resultado,), (0, 1), resultado.marcadores
    )
    assert comp.margen_de(encuentro, 0) == 0
    assert comp.margen_de(encuentro, 1) == 0


def test_margen_de_sumo_respeta_el_ultimo_combate_del_torneo():
    class Dados(random.Random):
        def __init__(self):
            super().__init__()
            self.valores = iter([
                2, 1, 1, 2, 2, 1,
                20, 19, 20, 19,
                20, 1, 20, 1,
            ])

        def randint(self, a, b):
            return next(self.valores)

        def shuffle(self, x):
            return None

    cuatro = [
        comp.Competidor(f"c{i}", "pulpo", 10, 10, 10)
        for i in range(4)
    ]
    encuentro = comp.enfrentar(cuatro, comp.SUMO, Dados())

    assert [comp.margen_de(encuentro, dorsal) for dorsal in range(4)] == [
        19, 1, 19, 1,
    ]


def test_persistencia_roundtrip_de_vetas(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "vetas.db")
    db.inicializar()
    c = db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15, 15), T0)
    modificada = replace(
        c, ten_fuerza=2.5, ten_velocidad=1.25, ten_salud=0.5,
        historial_vetas="FVS",
    )
    db.guardar(modificada)
    assert db.criatura_activa("u1", "g1") == modificada
    recuperada = db.criatura_activa("u1", "g1")
    assert recuperada is not None and recuperada.historial_vetas == "FVS"
    reserva = db.crear("u1", "g1", "pulpo", "Reserva", (15, 15, 15, 15), T0, activa=False)
    dormida = sim.avanzar(reserva, T0 + timedelta(days=3))
    assert dormida == reserva


def test_migracion_conserva_niveles_y_anade_defaults_vetas(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "legacy.db")
    db.inicializar()
    veterana = db.crear("u1", "g1", "pulpo", "Veterana", (15, 15, 15, 15), T0)
    db.guardar(replace(
        veterana, niv_fuerza=4, niv_velocidad=2, niv_salud=1
    ))
    with db.conectar() as con:
        for columna in (
            "ten_fuerza", "ten_velocidad", "ten_salud", "historial_vetas"
        ):
            con.execute(f"ALTER TABLE criaturas DROP COLUMN {columna}")

    db.inicializar()

    recuperada = db.criatura_activa("u1", "g1")
    assert recuperada is not None
    assert (recuperada.niv_fuerza, recuperada.niv_velocidad, recuperada.niv_salud) == (4, 2, 1)
    assert (
        recuperada.ten_fuerza,
        recuperada.ten_velocidad,
        recuperada.ten_salud,
        recuperada.historial_vetas,
    ) == (0.0, 0.0, 0.0, "")


def test_transaccion_de_aventura_recarga_el_activo_y_confirma_antes_de_publicar(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(db, "RUTA", tmp_path / "aventura.db")
    db.inicializar()
    c = db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15, 15), T0)
    db.guardar(replace(c, hambre=50.0))
    salida = av.Salida((av.Prueba("f", "fuerza", 15, 10, 20),))
    resultado = economia.ejecutar_viaje("u1", "g1", c.id, salida, T0)
    assert resultado.problema is None
    guardada = db.criatura_activa("u1", "g1")
    assert guardada is not None and guardada == resultado.criatura
    assert resultado.antes is not None and resultado.antes.hambre == 50.0
    assert guardada.hambre == 35.0


def test_ficha_muestra_vetas_impronta_y_conserva_ancho_ascii():
    mensaje = pantalla.render(
        criatura(ten_fuerza=4.5, ten_velocidad=1.0, historial_vetas="FVSI"), T0
    )
    assert "tensión" in mensaje and "próxima veta" not in mensaje
    assert "impronta" in mensaje and "vetas: F·V·S·I" in mensaje
    linea_impronta = next(
        linea for linea in mensaje.splitlines() if "impronta" in linea
    )
    assert "giro" not in linea_impronta
    assert not re.search(r"[+-]\d", linea_impronta)
    bloque = mensaje.split("```ansi\n", 1)[1].split("\n```", 1)[0]
    limpio = re.sub(r"\x1b\[[0-9;]*m", "", bloque)
    assert {len(linea) for linea in limpio.splitlines()} == {pantalla.ANCHO + 2}


def test_ficha_traduce_la_tension_a_cuatro_bandas_relativas():
    base = criatura()
    umbral = sim.umbral_veta(base)
    casos = (
        (0, "en reposo"),
        (umbral / 4, "despierta"),
        (umbral / 2, "cargada"),
        (umbral * 3 / 4, "al borde"),
    )

    for tension, banda in casos:
        mensaje = pantalla.render(
            replace(base, ten_fuerza=tension, ten_velocidad=tension,
                    ten_salud=tension, ten_ingenio=tension),
            T0,
        )
        linea = next(linea for linea in mensaje.splitlines() if "tensión" in linea)
        assert linea.count(banda) == 4
        assert not re.search(r"\d", linea)


def test_el_anillo_tiene_cuatro_pasos_en_ambos_giros():
    improntas = {
        sim.impronta_de(criatura(id=criatura_id)).giro:
        sim.impronta_de(criatura(id=criatura_id))
        for criatura_id in range(1, 100)
    }

    assert set(improntas) == {-1, 1}
    for impronta in improntas.values():
        assert set(impronta.anillo) == set(sim.ESTADISTICAS)
        assert len(impronta.anillo) == len(impronta.afinidades) == 4
    assert improntas[1].anillo == sim.ESTADISTICAS
    assert improntas[-1].anillo == ("fuerza", "ingenio", "salud", "velocidad")


def test_la_impronta_conserva_el_orden_de_tiradas_con_ingenio_al_final():
    for especie, criatura_id in (("pulpo", 1), ("dragoncito", 7), ("pollito", 19)):
        semilla = f"{especie}:{criatura_id}"
        rng = random.Random(semilla)
        giro = rng.choice((1, -1))
        crudas = tuple(rng.choice((-1, 0, 1)) for _ in range(4))
        media = sum(crudas) / 4

        vieja = random.Random(semilla)
        assert vieja.choice((1, -1)) == giro
        assert tuple(vieja.choice((-1, 0, 1)) for _ in range(3)) == crudas[:3]

        impronta = sim.impronta_de(criatura(especie=especie, id=criatura_id))
        assert impronta.giro == giro
        assert impronta.afinidades == tuple(
            sim.AFIN * (valor - media) for valor in crudas
        )


def test_ninguna_flecha_se_invierte_por_la_recalibracion():
    muestras = 0
    for especie in sorted(sim.esp.ESPECIES):
        for criatura_id in range(1, 11):
            rng = random.Random(f"{especie}:{criatura_id}")
            rng.choice((1, -1))
            crudas = tuple(rng.choice((-1, 0, 1)) for _ in range(4))
            media_vieja = sum(crudas[:3]) / 3
            media_nueva = sum(crudas) / 4
            for valor in crudas[:3]:
                vieja = sim.AFIN * (valor - media_vieja)
                nueva = sim.AFIN * (valor - media_nueva)
                assert vieja * nueva >= 0
                assert abs(vieja - nueva) <= 0.175 + 1e-9
            muestras += 1
    assert muestras >= 200


def test_la_cascada_de_salud_alimenta_al_ingenio():
    c = next(
        criatura(id=criatura_id)
        for criatura_id in range(1, 100)
        if sim.impronta_de(criatura(id=criatura_id)).giro == 1
    )

    marcada, rupturas = sim.romper_vetas(replace(c, ten_salud=20), 1)

    assert [ruptura.stat for ruptura in rupturas] == ["salud"]
    assert marcada.ten_ingenio == sim.CASCADA * 20
    assert marcada.ten_fuerza == 0


def test_la_sombra_de_fuerza_lee_las_vetas_de_ingenio():
    c = next(
        criatura(id=criatura_id)
        for criatura_id in range(1, 100)
        if sim.impronta_de(criatura(id=criatura_id)).giro == 1
    )
    assert sim.receptividad(replace(c, niv_ingenio=1), "fuerza") < sim.receptividad(
        c, "fuerza"
    )


def test_el_surge_de_nivel_reparte_un_cuarto_al_ingenio():
    for especie in ("pulpo", "dragoncito"):
        emisiones = sim._emisiones_de_nivel(criatura(especie=especie), 2)
        ingenio = next(emision for emision in emisiones if emision.stat == "ingenio")
        assert ingenio.bruto == sim._surge(2) * 0.25
        assert ingenio.forzar


def test_las_identidades_legadas_no_cambian():
    casos = {
        "": None,
        "FFFFF": None,
        "FFFFVS": "Corazón de roble",
        "VVVVSV": "Fibra de fresno",
        "SSSSFS": "Savia de olivo",
        "FVSFVS": "Veta en espiral",
        "VSFVSF": "Veta en espiral",
        "SFVSFV": "Veta en espiral",
        "FSVFSV": "Veta en espiral",
        "SVFSVF": "Veta en espiral",
        "VFSVFS": "Veta en espiral",
        "FVFVFV": "Veta trenzada",
        "VSVSVS": "Veta trenzada",
        "FFVVSS": None,
        "FFFVVVSSS": None,
        "FFVVSSV": None,
        "FVSFVSFFFFFF": "Veta en espiral",
    }
    assert {historial: sim.identidad_de(historial) for historial in casos} == casos


def test_nudo_de_nogal_se_reconoce_una_sola_vez():
    assert sim.identidad_de("IIIIII") == "Nudo de nogal"
    texto = pantalla.render_rupturas(
        criatura(historial_vetas="IIIIII", niv_ingenio=6),
        (sim.Ruptura("ingenio", 40, 5, 6, causa=sim.ENTRENAR),),
    )
    assert texto.count("El pasado toma forma") == 1
    assert "Nudo de nogal" in texto


def test_la_tension_de_ingenio_decae_con_la_misma_semivida():
    c = criatura(ten_ingenio=18)
    assert sim.avanzar(c, T0 + timedelta(hours=18)).ten_ingenio == 9
    reserva = replace(c, activa=False)
    assert sim.avanzar(reserva, T0 + timedelta(days=2)) == reserva


def test_la_reserva_de_crecimiento_cuenta_al_ingenio_como_visible():
    antes = criatura(
        xp=sim.xp_para_subir(1) - 1,
        base_fuerza=sim.MAXIMO_STAT,
        base_velocidad=sim.MAXIMO_STAT,
        base_salud=sim.MAXIMO_STAT,
        base_ingenio=50,
    )

    despues, rupturas = sim.aplicar_xp(antes, 1)

    assert despues.ingenio == antes.ingenio + 1
    assert any(
        ruptura.stat == "ingenio" and ruptura.causa == "nivel"
        for ruptura in rupturas
    )


def _impronta_de_cuatro(_criatura=None) -> SimpleNamespace:
    """La impronta de cuatro canales que traerá A3, sin tocar el dominio.

    Las afinidades van en el orden canónico —fuerza, velocidad, salud,
    ingenio— y el anillo en el suyo propio, distinto a propósito: así una
    ficha que confunda ambos órdenes no puede pasar la prueba.
    """
    return SimpleNamespace(
        giro=1,
        anillo=("fuerza", "salud", "ingenio", "velocidad"),
        afinidades=(0.35, 0.0, -0.35, 0.35),
    )


def test_la_ficha_dibuja_el_cuarto_canal_de_la_impronta(monkeypatch):
    monkeypatch.setattr(sim, "impronta_de", _impronta_de_cuatro)
    c = criatura(ten_ingenio=16.0)
    assert sim.umbral_veta(c) == 20.0

    mensaje = pantalla.render(c, T0)

    assert "anillo FUE→SAL→ING→VEL" in mensaje
    assert "afinidad FUE ↑ · SAL ↓ · ING ↑" in mensaje
    linea = next(linea for linea in mensaje.splitlines() if "tensión" in linea)
    assert linea.endswith("· ING al borde")
    bloque = mensaje.split("```ansi\n", 1)[1].split("\n```", 1)[0]
    limpio = re.sub(r"\x1b\[[0-9;]*m", "", bloque)
    assert {len(linea) for linea in limpio.splitlines()} == {pantalla.ANCHO + 2}


def test_las_vetas_anteriores_cuentan_tambien_las_de_ingenio(monkeypatch):
    monkeypatch.setattr(sim, "impronta_de", _impronta_de_cuatro)
    mensaje = pantalla.render(
        criatura(niv_fuerza=1, niv_ingenio=2, historial_vetas="F"), T0
    )
    assert "vetas: 2 anteriores sin trayectoria · F" in mensaje


def test_render_rupturas_etiqueta_la_veta_de_ingenio():
    texto = pantalla.render_rupturas(
        criatura(historial_vetas="I", niv_ingenio=1),
        (sim.Ruptura("ingenio", 20, 8, 9, causa=sim.ENTRENAR),),
    )
    assert "le ha salido una veta de ING" in texto
    assert "ING 8 → 9" in texto and "ahora ING en reposo" in texto


def test_la_ficha_dibuja_el_anillo_real_de_cuatro_y_sus_cuatro_bandas():
    """Sin monkeypatch: el anillo que sale en la ficha es el del dominio.

    Los dos giros son los únicos posibles, así que basta con exigir que la
    línea de impronta sea uno de ellos y que la de tensión nombre las cuatro
    bandas en el orden canónico.
    """
    for criatura_id in range(1, 40):
        mensaje = pantalla.render(criatura(id=criatura_id), T0)
        impronta = next(
            linea for linea in mensaje.splitlines() if "impronta" in linea
        )
        assert (
            "anillo FUE→VEL→SAL→ING" in impronta
            or "anillo FUE→ING→SAL→VEL" in impronta
        ), impronta
        tension = next(
            linea for linea in mensaje.splitlines() if "tensión" in linea
        )
        assert [
            trozo.split()[0] for trozo in tension.split("· ")[1:]
        ] == ["FUE", "VEL", "SAL", "ING"], tension


def test_las_descripciones_de_identidad_nombran_el_nudo_de_nogal():
    assert (
        pantalla.DESCRIPCIONES_IDENTIDAD["Nudo de nogal"]
        == "el ingenio domina su historia"
    )
    assert (
        pantalla.DESCRIPCIONES_IDENTIDAD["Veta en espiral"]
        == "sus últimas vetas giran por tres caminos"
    )


def test_render_rupturas_anuncia_cascada_fuera_del_arte():
    c = criatura(historial_vetas="FV")
    texto = pantalla.render_rupturas(
        c,
        (
            sim.Ruptura("fuerza", 20, 15, 16, causa=sim.ENTRENAR),
            sim.Ruptura(
                "velocidad", 24, 18, 19, cascada=True, causa=sim.ENTRENAR
            ),
        ),
    )
    assert "Cascada" in texto and "cascada" in texto
    assert "FUE 15 → 16" in texto and "por entrenar" in texto
    assert "próxima veta" not in texto
    assert "ahora FUE en reposo · VEL en reposo" in texto
    assert "```ansi" not in texto


def test_identidad_reconoce_patrones_deterministas_y_respeta_el_umbral():
    assert sim.UMBRAL_IDENTIDAD == sim.VENTANA_SECUENCIA == 6
    casos = {
        "": None,
        "FFFFF": None,
        "FFFFVS": "Corazón de roble",
        "VVVVSV": "Fibra de fresno",
        "SSSSFS": "Savia de olivo",
        "FVSFVS": "Veta en espiral",
        "VSFVSF": "Veta en espiral",
        "SFVSFV": "Veta en espiral",
        "FSVFSV": "Veta en espiral",
        "SVFSVF": "Veta en espiral",
        "VFSVFS": "Veta en espiral",
        "FVFVFV": "Veta trenzada",
        "VSVSVS": "Veta trenzada",
        "FFVVSS": None,
        "FFFVVVSSS": None,
        "FFVVSSV": None,
    }

    for historial, esperada in casos.items():
        assert sim.identidad_de(historial) == esperada
        assert sim.identidad_de(historial) == esperada


def test_identidad_prioriza_dominancia_y_conserva_la_primera_reconocida():
    assert sim.identidad_de("FFFFVFVFVF") == "Corazón de roble"
    assert sim.identidad_de("FVSFVSF") == "Veta en espiral"
    assert sim.identidad_de("FVSFVSFFFFFF") == "Veta en espiral"


def test_identidad_depende_solo_del_historial_persistido():
    veterana = criatura(niv_fuerza=20, niv_velocidad=20, niv_salud=20)
    assert sim.identidad_de(veterana.historial_vetas) is None


def test_primera_identidad_se_anuncia_exactamente_una_vez():
    texto = pantalla.render_rupturas(
        criatura(historial_vetas="FFFFFF", niv_fuerza=6),
        (sim.Ruptura("fuerza", 40, 5, 6, causa=sim.ENTRENAR),),
    )

    assert texto.count("El pasado toma forma") == 1
    assert "Corazón de roble" in texto


def test_cruce_en_segunda_ruptura_de_lote_anuncia_una_sola_vez():
    texto = pantalla.render_rupturas(
        criatura(historial_vetas="FFFFFFF", niv_fuerza=7),
        (
            sim.Ruptura("fuerza", 36, 4, 5, causa=sim.ENTRENAR),
            sim.Ruptura("fuerza", 40, 5, 6, causa=sim.ENTRENAR),
            sim.Ruptura("fuerza", 44, 6, 7, causa=sim.ENTRENAR),
        ),
    )

    assert texto.count("El pasado toma forma") == 1


def test_cascada_no_duplica_el_descubrimiento():
    texto = pantalla.render_rupturas(
        criatura(historial_vetas="FFFFFFF", niv_fuerza=7),
        (
            sim.Ruptura("fuerza", 36, 4, 5, causa=sim.ENTRENAR),
            sim.Ruptura(
                "fuerza", 40, 5, 6, cascada=True, causa=sim.ENTRENAR
            ),
            sim.Ruptura("fuerza", 44, 6, 7, causa=sim.ENTRENAR),
        ),
    )

    assert texto.count("El pasado toma forma") == 1


def test_identidad_reconocida_aparece_sin_nuevo_descubrimiento():
    texto = pantalla.render_rupturas(
        criatura(historial_vetas="FFFFFFF", niv_fuerza=7),
        (sim.Ruptura("fuerza", 44, 6, 7, causa=sim.ENTRENAR),),
    )

    assert "El pasado toma forma" not in texto
    assert "Corazón de roble" in texto


def test_cada_identidad_se_anuncia_con_su_descripcion():
    """`pantalla` describe las seis identidades que `simulacion` reconoce.

    El anuncio busca la descripción por el nombre de la identidad, así que un
    nombre sin pareja no fallaría en `simulacion`: reventaría al anunciarlo.
    """
    casos = {
        "FFFFVF": ("Corazón de roble", "fuerza"),
        "VVVVFV": ("Fibra de fresno", "velocidad"),
        "SSSSFS": ("Savia de olivo", "salud"),
        "IIIIFI": ("Nudo de nogal", "ingenio"),
        "FVSFVS": ("Veta en espiral", "salud"),
        "FVFVFV": ("Veta trenzada", "velocidad"),
    }

    for historial, (identidad, stat) in casos.items():
        assert sim.identidad_de(historial) == identidad
        texto = pantalla.render_rupturas(
            criatura(historial_vetas=historial),
            (sim.Ruptura(stat, 20, 0, 1, causa=sim.ENTRENAR),),
        )
        assert texto.count("El pasado toma forma") == 1
        assert identidad in texto
        assert pantalla.DESCRIPCIONES_IDENTIDAD[identidad] in texto


def test_ruptura_sin_identidad_conserva_el_mensaje():
    texto = pantalla.render_rupturas(
        criatura(historial_vetas="FV", niv_fuerza=1, niv_velocidad=1),
        (
            sim.Ruptura("fuerza", 20, 0, 1, causa=sim.ENTRENAR),
            sim.Ruptura(
                "velocidad", 24, 0, 1, cascada=True, causa=sim.ENTRENAR
            ),
        ),
    )

    assert texto == (
        "## 🪵🪵 ¡Cascada en Prueba!\n"
        "-# FUE 0 → 1 · VEL 0 → 1 · por entrenar · "
        "ahora FUE en reposo · VEL en reposo · 1 por cascada"
    )


def _a_una_veta_de_identidad() -> sim.Criatura:
    base = criatura(
        historial_vetas="FFFFF",
        niv_fuerza=5,
        hambre=40.0,
        animo=100.0,
    )
    return replace(base, ten_fuerza=sim.umbral_veta(base) - 0.01)


def _sufijo_del_lote(antes: sim.Criatura, despues: sim.Criatura) -> str:
    """Letras que el suceso añadió al historial, conservando el prefijo.

    `render_rupturas` compara el historial final con el prefijo anterior al
    lote restando su longitud. Si un camino real dejara de anunciar todas sus
    rupturas —o tocara el historial por otro sitio— esa resta señalaría al
    prefijo equivocado y el descubrimiento se anunciaría de más o de menos.
    """
    assert despues.historial_vetas.startswith(antes.historial_vetas)
    return despues.historial_vetas[len(antes.historial_vetas):]


def test_cuidado_descubre_identidad_por_el_camino_real():
    antes = _a_una_veta_de_identidad()
    resultado = sim.aplicar_accion(antes, sim.ENTRENAR, T0)
    texto = pantalla.render_rupturas(resultado.criatura, resultado.rupturas)

    assert resultado.rupturas
    assert len(_sufijo_del_lote(antes, resultado.criatura)) == len(
        resultado.rupturas
    )
    assert texto.count("El pasado toma forma") == 1


def test_competencia_descubre_identidad_por_el_camino_real():
    antes = _a_una_veta_de_identidad()
    actualizada, rupturas = sim.aplicar_competencia(
        antes, True, ("fuerza",), margen=0
    )
    texto = pantalla.render_rupturas(actualizada, rupturas)

    assert rupturas
    assert len(_sufijo_del_lote(antes, actualizada)) == len(rupturas)
    assert texto.count("El pasado toma forma") == 1


def test_aventura_descubre_identidad_por_el_camino_real():
    antes = _a_una_veta_de_identidad()
    salida = av.Salida((av.Prueba("f", "fuerza", 20, 0, 20),))
    actualizada, rupturas = av.aplicar_viaje(antes, salida, T0)
    texto = pantalla.render_rupturas(actualizada, rupturas)

    assert rupturas
    assert len(_sufijo_del_lote(antes, actualizada)) == len(rupturas)
    assert texto.count("El pasado toma forma") == 1


def test_evolucion_muestra_identidad_sin_prometer_descubrimiento():
    con_identidad = pantalla.render_evolucion(
        criatura(historial_vetas="FFFFFF", niv_fuerza=6, nivel=2), "bebe"
    )
    sin_identidad = pantalla.render_evolucion(criatura(nivel=2), "bebe")

    assert "Corazón de roble" in con_identidad
    assert "El pasado toma forma" not in con_identidad
    assert "Corazón de roble" not in sin_identidad


def test_ficha_acota_historial_y_explica_vetas_anteriores():
    larga = criatura(
        niv_fuerza=500, historial_vetas="F" * 500
    )
    mensaje = pantalla.render(larga, T0)
    assert len(mensaje) < 2000
    assert "…·" in mensaje

    veterana = pantalla.render(criatura(niv_fuerza=4, niv_salud=3), T0)
    assert "7 anteriores sin trayectoria" in veterana


def test_cuidado_distingue_tension_de_ausencia_de_marca():
    notable = sim.aplicar_accion(
        criatura(hambre=40.0, animo=100.0), sim.ENTRENAR, T0
    )
    suave = sim.aplicar_accion(criatura(), sim.JUGAR, T0)
    assert notable.marca and notable.criatura.ten_fuerza > 0
    assert not suave.marca


def test_fallo_al_guardar_viaje_revierte_tension_y_desgaste(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(db, "RUTA", tmp_path / "rollback.db")
    db.inicializar()
    original = db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15, 15), T0)
    salida = av.Salida((av.Prueba("f", "fuerza", 15, 10, 20),))

    def fallar(*_):
        raise RuntimeError("fallo al guardar")

    monkeypatch.setattr(db, "_guardar", fallar)
    try:
        economia.ejecutar_viaje("u1", "g1", original.id, salida, T0)
    except RuntimeError as error:
        assert str(error) == "fallo al guardar"
    else:
        raise AssertionError("el viaje debía fallar")

    assert db.criatura_activa("u1", "g1") == original


def test_el_totem_deja_una_sola_marca_de_entrenamiento_y_veta_en_las_tres():
    antes = criatura()
    assert comp.STATS[comp.TOTEM] == ("velocidad", "fuerza", "salud")

    despues, _ = sim.aplicar_competencia(
        antes, True, comp.STATS[comp.TOTEM], margen=10
    )

    subidas = {
        stat: getattr(despues, f"ent_{stat}") - getattr(antes, f"ent_{stat}")
        for stat in sim.ESTADISTICAS
    }
    assert sum(subidas.values()) == sim.ENTRENAMIENTO_POR_COMPETIR
    assert sorted(subidas.values()) == [0, 0, 0, 1]
    for stat in comp.STATS[comp.TOTEM]:
        assert getattr(despues, f"ten_{stat}") > getattr(antes, f"ten_{stat}")


def test_el_totem_entrena_la_mas_atrasada_y_asi_va_rotando():
    """Seis asaltos son seis puntos repartidos, no dieciocho amontonados."""
    c = criatura()
    conteos = []
    for _ in range(6):
        c, _ = sim.aplicar_competencia(
            c, True, comp.STATS[comp.TOTEM], margen=10
        )
        conteos.append((c.ent_velocidad, c.ent_fuerza, c.ent_salud))

    assert conteos == [
        (1, 0, 0), (1, 1, 0), (1, 1, 1),
        (2, 1, 1), (2, 2, 1), (2, 2, 2),
    ]
    assert sum(conteos[-1]) == 6 * sim.ENTRENAMIENTO_POR_COMPETIR


def test_el_totem_respeta_los_contadores_que_ya_traia():
    c = criatura(ent_velocidad=5, ent_fuerza=2, ent_salud=9)

    despues, _ = sim.aplicar_competencia(
        c, True, comp.STATS[comp.TOTEM], margen=10
    )

    assert sim.stat_a_entrenar(c, comp.STATS[comp.TOTEM]) == "fuerza"
    assert (
        despues.ent_velocidad, despues.ent_fuerza, despues.ent_salud
    ) == (5, 3, 9)


def test_competir_rechaza_estadisticas_vacias_repetidas_o_desconocidas():
    for stats in ((), ("fuerza", "fuerza"), ("magia",), "fuerza"):
        try:
            sim.aplicar_competencia(criatura(), True, stats, margen=0)
        except ValueError:
            continue
        raise AssertionError(f"{stats!r} debería levantar ValueError")


# --- Crecimiento visible al evolucionar (PR #37) ---------------------------

def _visibles(c: sim.Criatura) -> tuple[int, ...]:
    return tuple(getattr(c, stat) for stat in sim.ESTADISTICAS)


def _al_borde_de_evolucionar_con_dos_topes() -> sim.Criatura:
    """Nivel 1 a un paso de subir, con fuerza y salud ya en el tope visible.

    Sólo la velocidad puede crecer a la vista, así que la subida de nivel tiene
    que gastarse ahí su veta: es la garantía que trajo `fix: garantiza
    crecimiento visible al evolucionar`.
    """
    return criatura(
        xp=sim.xp_para_subir(1) - sim.XP_VICTORIA,
        base_fuerza=sim.MAXIMO_STAT,
        base_velocidad=50,
        base_salud=sim.MAXIMO_STAT,
        base_ingenio=sim.MAXIMO_STAT,
        ent_fuerza=1,
        ent_velocidad=1,
        ent_salud=1,
        ten_salud=35,
    )


def test_el_totem_no_se_come_la_veta_que_hace_crecer_al_evolucionar():
    """Tres esfuerzos no pueden dejar sin sitio a la veta de la subida."""
    antes = _al_borde_de_evolucionar_con_dos_topes()
    assert _visibles(antes) == (
        sim.MAXIMO_STAT, 51, sim.MAXIMO_STAT, sim.MAXIMO_STAT,
    )

    despues, rupturas = sim.aplicar_competencia(
        antes, True, comp.STATS[comp.TOTEM], margen=0
    )

    assert despues.nivel == antes.nivel + 1
    assert despues.etapa != antes.etapa
    assert _visibles(despues) == (
        sim.MAXIMO_STAT, 52, sim.MAXIMO_STAT, sim.MAXIMO_STAT,
    )

    assert len(rupturas) <= sim.MAX_RUPTURAS_POR_SUCESO
    assert any(ruptura.causa == "nivel" for ruptura in rupturas)
    # Las vetas topadas siguen valiendo: no se filtran por no verse.
    assert any(
        ruptura.antes == ruptura.despues == sim.MAXIMO_STAT
        for ruptura in rupturas
    )
    subidas = sum(
        getattr(despues, f"ent_{stat}") - getattr(antes, f"ent_{stat}")
        for stat in sim.ESTADISTICAS
    )
    assert subidas == sim.ENTRENAMIENTO_POR_COMPETIR


def test_la_carrera_y_el_sumo_siguen_creciendo_igual_al_evolucionar():
    antes = _al_borde_de_evolucionar_con_dos_topes()

    for tipo in (comp.CARRERA, comp.SUMO):
        despues, _ = sim.aplicar_competencia(
            antes, True, comp.STATS[tipo], margen=0
        )
        assert despues.etapa != antes.etapa, tipo
        assert _visibles(despues) == (
            sim.MAXIMO_STAT, 52, sim.MAXIMO_STAT, sim.MAXIMO_STAT,
        ), tipo


def test_una_subida_con_todo_al_tope_no_aparta_ninguna_veta():
    """Si no hay nada visible que crecer no se reserva nada: los tres esfuerzos
    se gastan las tres rupturas, como en cualquier suceso sin subida."""
    antes = criatura(
        xp=sim.xp_para_subir(1) - sim.XP_VICTORIA,
        base_fuerza=sim.MAXIMO_STAT,
        base_velocidad=sim.MAXIMO_STAT,
        base_salud=sim.MAXIMO_STAT,
        base_ingenio=sim.MAXIMO_STAT,
        ten_fuerza=100.0,
        ten_velocidad=100.0,
        ten_salud=100.0,
        ten_ingenio=100.0,
    )

    despues, rupturas = sim.aplicar_competencia(
        antes, True, comp.STATS[comp.TOTEM], margen=0
    )

    assert despues.nivel == antes.nivel + 1
    assert _visibles(despues) == _visibles(antes) == (sim.MAXIMO_STAT,) * 4
    assert len(rupturas) == sim.MAX_RUPTURAS_POR_SUCESO
    assert all(ruptura.causa == sim.COMPETIR for ruptura in rupturas)


def test_la_veta_que_hace_crecer_suelta_el_hueco_para_su_propia_cascada():
    """La reserva se suelta **dentro** de la emisión que hace crecer.

    Una identidad concreta —`P1`, con anillo fuerza → ingenio → salud →
    velocidad— y las dos tensiones justo por debajo del umbral: la subida rompe primero
    velocidad, después salud —que es la que crece a la vista, justo por debajo
    del tope y hasta él— y esa
    ruptura arrastra a velocidad otra vez. Si el hueco apartado se soltara sólo
    entre emisiones, esa tercera ruptura se quedaría fuera y el suceso acabaría
    con una tensión elegible pendiente y un hueco muerto.
    """
    antes = criatura(
        id=1,
        nombre="P1",
        xp=sim.xp_para_subir(1) - 1,
        base_fuerza=sim.MAXIMO_STAT,
        base_velocidad=sim.MAXIMO_STAT,
        base_salud=sim.MAXIMO_STAT - 1,
        base_ingenio=sim.MAXIMO_STAT,
        ten_fuerza=0.0,
        ten_velocidad=36.0,
        ten_salud=33.0,
    )
    assert sim.impronta_de(antes).anillo == (
        "fuerza", "ingenio", "salud", "velocidad",
    )
    assert _visibles(antes) == (
        sim.MAXIMO_STAT, sim.MAXIMO_STAT, sim.MAXIMO_STAT - 1, sim.MAXIMO_STAT,
    )

    despues, rupturas = sim.aplicar_xp(antes, 1)

    assert despues.nivel == 2
    assert _visibles(despues) == (sim.MAXIMO_STAT,) * 4
    assert len(rupturas) == sim.MAX_RUPTURAS_POR_SUCESO
    assert [ruptura.stat for ruptura in rupturas] == [
        "velocidad", "salud", "velocidad",
    ]
    assert [ruptura.cascada for ruptura in rupturas] == [False, False, True]
    assert all(ruptura.causa == "nivel" for ruptura in rupturas)
    # La segunda es la que crece a la vista y suelta el hueco de la tercera.
    assert (rupturas[1].antes, rupturas[1].despues) == (sim.MAXIMO_STAT - 1, sim.MAXIMO_STAT)
    # Y no queda tensión elegible por culpa de la reserva.
    umbral = sim.umbral_veta(despues)
    assert max(
        despues.ten_fuerza,
        despues.ten_velocidad,
        despues.ten_salud,
        despues.ten_ingenio,
    ) < umbral
