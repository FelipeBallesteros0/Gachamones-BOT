"""Reglas locales de VETAS: física, persistencia y cableado mínimo."""
import random
import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone
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
    )
    datos.update(cambios)
    return sim.Criatura(**datos)


def test_impronta_es_determinista_y_no_se_persiste():
    c = criatura()
    primera = sim.impronta_de(c)
    segunda = sim.impronta_de(c)
    assert primera == segunda
    assert primera.giro in (-1, 1)
    assert len(primera.afinidades) == 3
    assert c.historial_vetas == ""


def test_receptividad_respeta_los_limites_y_el_anillo():
    c = criatura(niv_fuerza=4, niv_velocidad=1, niv_salud=2)
    assert all(0.35 <= sim.receptividad(c, stat) <= 3.0 for stat in sim.ESTADISTICAS)
    assert set(sim.impronta_de(c).anillo) == set(sim.ESTADISTICAS)


def test_impulso_refuerza_y_la_veta_anterior_proyecta_sombra():
    c = criatura()
    objetivo = "fuerza"
    anillo = sim.impronta_de(c).anillo
    anterior = anillo[(anillo.index(objetivo) - 1) % 3]
    siguiente = anillo[(anillo.index(objetivo) + 1) % 3]
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
    c = criatura(ten_fuerza=20, ten_velocidad=10, ten_salud=5)
    una = sim.avanzar(c, T0 + timedelta(hours=18))
    assert una.ten_fuerza == 10
    assert una.ten_velocidad == 5
    assert una.ten_salud == 2.5
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
    assert min(marcada.ten_fuerza, marcada.ten_velocidad, marcada.ten_salud) >= 0
    assert sim.umbral_veta(marcada) == 32


def test_cascada_marca_la_ruptura_arrastrada_y_no_la_que_alimenta():
    origen, siguiente, _ = sim.impronta_de(criatura()).anillo
    tensiones = {f"ten_{stat}": 0.0 for stat in sim.ESTADISTICAS}
    tensiones[f"ten_{origen}"] = 20.0
    tensiones[f"ten_{siguiente}"] = 14.0

    _, rupturas = sim.romper_vetas(criatura(**tensiones))

    assert [ruptura.stat for ruptura in rupturas] == [origen, siguiente]
    assert [ruptura.cascada for ruptura in rupturas] == [False, True]


def test_el_tope_no_anuncia_una_cascada_que_queda_pendiente():
    origen, siguiente, _ = sim.impronta_de(criatura()).anillo
    tensiones = {f"ten_{stat}": 0.0 for stat in sim.ESTADISTICAS}
    tensiones[f"ten_{origen}"] = 72.0

    marcada, rupturas = sim.romper_vetas(criatura(**tensiones))

    assert len(rupturas) == sim.MAX_RUPTURAS_POR_SUCESO
    assert not any(ruptura.cascada for ruptura in rupturas)
    assert getattr(marcada, f"ten_{siguiente}") >= sim.umbral_veta(marcada)


def test_cuidado_y_subida_comparten_el_mismo_tope_de_tres():
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
    assert all(ruptura.causa == sim.ENTRENAR for ruptura in resultado.rupturas)
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


def test_aventura_emite_cada_prueba_y_anade_salud_al_fallar():
    salida = av.Salida((
        av.Prueba("f", "fuerza", 20, 0, 20),
        av.Prueba("v", "velocidad", 10, 1, 30),
    ))
    esfuerzos = av.esfuerzos_de_viaje(salida)
    assert [e.stat for e in esfuerzos] == ["fuerza", "velocidad", "salud"]
    assert esfuerzos[-1].bruto == 1.0


def test_margen_de_competencia_usa_el_ultimo_combate():
    a = comp.Competidor("a", "pulpo", 10)
    b = comp.Competidor("b", "pulpo", 10)
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
        comp.Competidor(nombre, "pulpo", 10)
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


def test_persistencia_roundtrip_de_vetas(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "vetas.db")
    db.inicializar()
    c = db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15), T0)
    modificada = replace(
        c, ten_fuerza=2.5, ten_velocidad=1.25, ten_salud=0.5,
        historial_vetas="FVS",
    )
    db.guardar(modificada)
    assert db.criatura_activa("u1", "g1") == modificada
    recuperada = db.criatura_activa("u1", "g1")
    assert recuperada is not None and recuperada.historial_vetas == "FVS"
    reserva = db.crear("u1", "g1", "pulpo", "Reserva", (15, 15, 15), T0, activa=False)
    dormida = sim.avanzar(reserva, T0 + timedelta(days=3))
    assert dormida == reserva


def test_migracion_conserva_niveles_y_anade_defaults_vetas(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "legacy.db")
    db.inicializar()
    veterana = db.crear("u1", "g1", "pulpo", "Veterana", (15, 15, 15), T0)
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
    c = db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15), T0)
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
        criatura(ten_fuerza=4.5, ten_velocidad=1.0, historial_vetas="FVS"), T0
    )
    assert "tensión" in mensaje and "próxima veta" not in mensaje
    assert "impronta" in mensaje and "vetas: F·V·S" in mensaje
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
                    ten_salud=tension),
            T0,
        )
        linea = next(linea for linea in mensaje.splitlines() if "tensión" in linea)
        assert linea.count(banda) == 3
        assert not re.search(r"\d", linea)


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


def test_cuidado_descubre_identidad_por_el_camino_real():
    resultado = sim.aplicar_accion(
        _a_una_veta_de_identidad(), sim.ENTRENAR, T0
    )
    texto = pantalla.render_rupturas(resultado.criatura, resultado.rupturas)

    assert resultado.rupturas
    assert texto.count("El pasado toma forma") == 1


def test_competencia_descubre_identidad_por_el_camino_real():
    actualizada, rupturas = sim.aplicar_competencia(
        _a_una_veta_de_identidad(), True, "fuerza", margen=0
    )
    texto = pantalla.render_rupturas(actualizada, rupturas)

    assert rupturas
    assert texto.count("El pasado toma forma") == 1


def test_aventura_descubre_identidad_por_el_camino_real():
    salida = av.Salida((av.Prueba("f", "fuerza", 20, 0, 20),))
    actualizada, rupturas = av.aplicar_viaje(
        _a_una_veta_de_identidad(), salida, T0
    )
    texto = pantalla.render_rupturas(actualizada, rupturas)

    assert rupturas
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
    original = db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15), T0)
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
