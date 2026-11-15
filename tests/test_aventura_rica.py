# pyright: reportArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false
"""Contrato del terreno honesto y del encuentro salvaje contextual."""
import inspect
import random
from dataclasses import replace

import pytest

import aventura as av
import especies as esp
import personalidad as per
import simulacion as sim


class DadosFijos(random.Random):
    def __init__(self, valores):
        super().__init__()
        self.valores = list(valores)
        self.i = 0

    def randint(self, a, b):
        valor = self.valores[self.i]
        self.i += 1
        return min(max(valor, a), b)


def criatura(fuerza=15, velocidad=15, **cambios):
    datos = dict(
        id=1, usuario_id="u1", guild_id="g1", especie="pulpo", nombre="Nube",
        nacida_en=None, actualizada_en=None,
        base_fuerza=fuerza, base_velocidad=velocidad, base_salud=15,
        hambre=80.0, animo=80.0,
    )
    datos.update(cambios)
    return sim.Criatura(**datos)


def escena(nombre="Un paso estrecho."):
    return av.Escena(
        nombre, (av.FUERZA, av.VELOCIDAD),
        ("Mover la roca", "Cruzar el hueco"), "Dar un rodeo",
    )


def terreno(bioma="bosque", favorecida=av.FUERZA):
    dificultad = av.BIOMAS[bioma].dificultad
    return av.Terreno(
        (av.FUERZA, av.VELOCIDAD),
        (
            dificultad - 2 if favorecida == av.FUERZA else dificultad + 2,
            dificultad - 2 if favorecida == av.VELOCIDAD else dificultad + 2,
        ),
    )


def salvaje(
    especie="michi", genero=esp.MACHO, caracter="sereno",
):
    return av.Salvaje(especie, esp.ESPECIES[especie].nombre, genero, caracter, (10, 10, 10, 15))


# --- Terreno, riesgo y marca -----------------------------------------------


def test_las_seis_parejas_cubren_las_cuatro_stats_con_complementos_disjuntos():
    assert (av.FUERZA, av.VELOCIDAD, av.SALUD, av.INGENIO) == sim.ESTADISTICAS
    assert av.PAREJAS == (
        (av.FUERZA, av.VELOCIDAD),
        (av.FUERZA, av.SALUD),
        (av.FUERZA, av.INGENIO),
        (av.VELOCIDAD, av.SALUD),
        (av.VELOCIDAD, av.INGENIO),
        (av.SALUD, av.INGENIO),
    )
    for pareja in av.PAREJAS:
        complemento = av.complementaria(pareja)
        assert set(pareja).isdisjoint(complemento)
        assert set(pareja + complemento) == set(sim.ESTADISTICAS)


def test_cada_indice_fijo_alcanza_una_pareja_sin_recibir_criatura():
    assert tuple(av.tirar_pareja(DadosFijos([i])) for i in range(6)) == av.PAREJAS
    assert "criatura" not in inspect.signature(av.tirar_pareja).parameters


@pytest.mark.parametrize("pareja", av.PAREJAS)
@pytest.mark.parametrize("bit", (0, 1))
def test_terreno_alinea_exigencias_y_favor_con_cada_pareja(pareja, bit):
    bioma = av.BIOMAS["bosque"]
    terreno = av.tirar_terreno(bioma, pareja, DadosFijos([bit]))
    baja, alta = bioma.dificultad - 2, bioma.dificultad + 2
    esperadas = (baja, alta) if bit == 0 else (alta, baja)

    assert terreno == av.Terreno(pareja, esperadas)
    assert terreno.favorecida == pareja[bit]
    assert tuple(terreno.exigencia(stat) for stat in pareja) == esperadas
    inactiva = next(stat for stat in sim.ESTADISTICAS if stat not in pareja)
    with pytest.raises(ValueError):
        terreno.exigencia(inactiva)


def test_terreno_rechaza_pareja_invalida_y_en_empate_favorece_la_segunda():
    with pytest.raises(ValueError):
        av.Terreno((av.FUERZA, av.FUERZA), (20, 24))
    terreno = av.Terreno((av.SALUD, av.INGENIO), (24, 24))
    assert terreno.favorecida == av.INGENIO


def test_escena_ofrece_su_pareja_y_volver_y_rechaza_etiquetas_inactivas():
    escena = av.Escena(
        "La corriente aprieta.",
        (av.SALUD, av.INGENIO),
        ("Resistir la corriente", "Leer el ritmo del agua"),
        "Buscar otro paso",
    )

    assert escena.opciones == (av.SALUD, av.INGENIO, av.VOLVER)
    assert tuple(escena.etiqueta(opcion) for opcion in escena.opciones) == (
        "Resistir la corriente", "Leer el ritmo del agua", "Buscar otro paso"
    )
    with pytest.raises(ValueError):
        escena.etiqueta(av.FUERZA)


def test_viaje_rechaza_escena_y_terreno_de_parejas_distintas():
    bioma = av.BIOMAS["bosque"]
    escena = av.Escena(
        "Un paso.", (av.SALUD, av.INGENIO),
        ("Resistir", "Observar"), "Volver",
    )
    terreno = av.Terreno((av.FUERZA, av.VELOCIDAD), (20, 24))

    with pytest.raises(ValueError):
        av.Viaje(bioma, escena, terreno)


def test_terreno_se_sortea_ciego_y_aplica_menos_dos_mas_dos():
    bioma = av.BIOMAS["bosque"]
    pareja = (av.FUERZA, av.VELOCIDAD)
    fuerza = av.tirar_terreno(bioma, pareja, DadosFijos([0]))
    velocidad = av.tirar_terreno(bioma, pareja, DadosFijos([1]))

    assert fuerza == av.Terreno(
        pareja, (bioma.dificultad - 2, bioma.dificultad + 2)
    )
    assert velocidad == av.Terreno(
        pareja, (bioma.dificultad + 2, bioma.dificultad - 2)
    )
    assert fuerza.favorecida == av.FUERZA
    assert velocidad.favorecida == av.VELOCIDAD
    assert "criatura" not in inspect.signature(av.tirar_terreno).parameters


@pytest.mark.parametrize(
    "stat,pareja",
    (
        (av.FUERZA, (av.FUERZA, av.VELOCIDAD)),
        (av.VELOCIDAD, (av.FUERZA, av.VELOCIDAD)),
        (av.SALUD, (av.SALUD, av.INGENIO)),
        (av.INGENIO, (av.SALUD, av.INGENIO)),
    ),
)
def test_resolver_usa_cada_una_de_las_cuatro_stats(stat, pareja):
    bicho = criatura(fuerza=11, velocidad=22, base_salud=33, base_ingenio=44)
    prueba = av.resolver_opcion(
        bicho, av.Terreno(pareja, (20, 20)), stat, DadosFijos([7])
    )

    assert prueba is not None
    assert prueba.stat == stat
    assert prueba.base == getattr(bicho, stat)
    assert prueba.dado == 7


def test_probabilidad_y_bandas_salen_del_d20_real_clampado():
    casos = (
        (15, 20, 0.80, "favorable"),
        (15, 21, 0.75, "favorable"),
        (15, 22, 0.70, "pareja"),
        (15, 26, 0.50, "pareja"),
        (15, 27, 0.45, "cuesta arriba"),
        (15, 31, 0.25, "cuesta arriba"),
        (15, 32, 0.20, "temeraria"),
        (99, 1, 1.00, "favorable"),
        (1, 99, 0.00, "temeraria"),
    )
    for stat, exigencia, probabilidad, banda in casos:
        assert av.probabilidad_opcion(stat, exigencia) == probabilidad
        assert av.banda_opcion(stat, exigencia) == banda


def test_marca_real_y_potencial_nacen_del_esfuerzo_canonico():
    for holgura in range(-25, 26):
        esfuerzo = sim.esfuerzo_de_aventura(av.FUERZA, holgura)
        esperada = esfuerzo.profunda or esfuerzo.bruto >= sim.UMBRAL_ESFUERZO
        assert av.deja_marca(holgura) is esperada

    assert av.puede_dejar_marca(15, 24)
    assert not av.puede_dejar_marca(99, 24)
    assert not av.puede_dejar_marca(1, 40)


def test_beat_muestra_ecuacion_margen_y_marca_reales():
    profunda = av.Prueba("Sujetar la torre", av.FUERZA, 20, 5, 24)
    fallo_justo = av.Prueba("Cruzar el hueco", av.VELOCIDAD, 15, 5, 24)
    sobrada = av.Prueba("Mover la roca", av.FUERZA, 30, 20, 24)

    assert av.render_beat(profunda) == (
        "✓ Sujetar la torre — 💪 20 + 5 = 25 / 24 · al límite, marca profunda"
    )
    assert av.render_beat(fallo_justo) == (
        "✗ Cruzar el hueco — 💨 15 + 5 = 20 / 24 · por un pelo, deja marca"
    )
    assert av.render_beat(sobrada).endswith("sobrada, sin marca")
    assert av.render_beat(None) == "🚶 Prefirieron no meterse"


def test_salud_e_ingenio_conservan_identidad_en_pista_beat_y_marco():
    bicho = criatura(base_salud=15, base_ingenio=99)
    terreno = av.Terreno((av.SALUD, av.INGENIO), (24, 24))
    salud = av.Prueba("Resistir el humo", av.SALUD, 15, 5, 24)
    ingenio = av.Prueba("Leer el patrón", av.INGENIO, 99, 5, 24)

    assert av.pista_marcas(bicho, terreno).endswith("sólo la 🛡️")
    assert "— 🛡️ 15 + 5" in av.render_beat(salud)
    assert "— 🧠 99 + 5" in av.render_beat(ingenio)
    marco = av.render_pruebas(
        bicho, av.BIOMAS["bosque"], av.Salida((salud, ingenio)), dueño="Felipe"
    )
    assert "SAL" in marco and "ING" in marco


def test_salud_e_ingenio_fluyen_por_pruebas_y_vetas_genericas():
    salida = av.Salida((
        av.Prueba("Resistir", av.SALUD, 20, 10, 24),
        av.Prueba("Observar", av.INGENIO, 20, 10, 24),
    ))

    assert tuple(esfuerzo.stat for esfuerzo in av.esfuerzos_de_viaje(salida)) == (
        av.SALUD, av.INGENIO
    )


def test_volver_en_salud_ingenio_no_tira_ni_deja_esfuerzo():
    bioma = av.BIOMAS["bosque"]
    pareja = (av.SALUD, av.INGENIO)
    escena = av.Escena("Un paso.", pareja, ("Resistir", "Observar"), "Volver")
    terreno = av.Terreno(pareja, (22, 26))
    viaje = av.Viaje(bioma, escena, terreno)

    despues = av.avanzar(viaje, criatura(), av.VOLVER, escena, terreno, DadosFijos([]))

    assert despues.pruebas == ()
    assert av.esfuerzos_de_viaje(despues.salida) == ()


def test_volver_no_tira_y_escena_terreno_cambian_juntos():
    bioma = av.BIOMAS["bosque"]
    inicial = av.Viaje(bioma, escena(), terreno())
    otra_escena = escena("Un claro abierto.")
    otro_terreno = terreno(favorecida=av.VELOCIDAD)
    rng = DadosFijos([])

    despues = av.avanzar(
        inicial, criatura(), av.VOLVER, otra_escena, otro_terreno, rng
    )

    assert despues.escena is otra_escena
    assert despues.terreno is otro_terreno
    assert despues.pruebas == ()
    assert av.esfuerzos_de_viaje(despues.salida) == ()
    with pytest.raises(ValueError):
        av.avanzar(inicial, criatura(), av.VOLVER, otra_escena, None, rng)
    with pytest.raises(ValueError):
        av.avanzar(inicial, criatura(), av.VOLVER, None, otro_terreno, rng)


def test_pista_previa_enumera_ninguna_una_o_ambas_sin_prometarlas():
    assert av.pista_marcas(
        criatura(99, 99), av.Terreno((av.FUERZA, av.VELOCIDAD), (24, 24))
    ).endswith(
        "ninguna"
    )
    assert av.pista_marcas(
        criatura(15, 99), av.Terreno((av.FUERZA, av.VELOCIDAD), (24, 24))
    ).endswith(
        "sólo la 💪"
    )
    assert av.pista_marcas(
        criatura(15, 15), av.Terreno((av.FUERZA, av.VELOCIDAD), (24, 24))
    ).endswith(
        "cualquiera de las dos"
    )


def test_resolver_usa_la_exigencia_del_terreno_real():
    bioma = av.BIOMAS["bosque"]
    t = terreno()
    viaje = av.Viaje(bioma, escena(), t)

    fuerza = av.avanzar(viaje, criatura(), av.FUERZA, None, None, DadosFijos([9]))
    velocidad = av.avanzar(viaje, criatura(), av.VELOCIDAD, None, None, DadosFijos([9]))

    assert fuerza.pruebas[-1].dificultad == bioma.dificultad - 2
    assert velocidad.pruebas[-1].dificultad == bioma.dificultad + 2


# --- Catálogo y prompt de escena ------------------------------------------


def test_json_solo_llena_las_etiquetas_de_la_pareja_decidida():
    escena = av.escena_desde_json(
        '{"situacion":"Una corriente helada.","salud":"Resistir el frío",'
        '"ingenio":"Leer los remolinos","volver":"Buscar un vado",'
        '"favorecida":"fuerza"}',
        (av.SALUD, av.INGENIO),
    )
    assert escena == av.Escena(
        "Una corriente helada.",
        (av.SALUD, av.INGENIO),
        ("Resistir el frío", "Leer los remolinos"),
        "Buscar un vado",
    )
    assert av.escena_desde_json(
        '{"situacion":"Un muro.","fuerza":"Empujar",'
        '"velocidad":"Trepar","volver":"Rodear"}',
        (av.SALUD, av.INGENIO),
    ) is None


def test_catalogo_cubre_las_cuatro_sendas_y_se_proyecta_en_las_seis_parejas():
    assert set(av.ESCENAS_ESCRITAS) == set(av.BIOMAS)
    for clave, por_favorecida in av.ESCENAS_ESCRITAS.items():
        assert set(por_favorecida) == set(sim.ESTADISTICAS), clave
        bioma = av.BIOMAS[clave]
        for pareja in av.PAREJAS:
            for favorecida in pareja:
                escena = av.escena_escrita(bioma, pareja, favorecida)
                assert escena.pareja == pareja
                assert escena.situacion == por_favorecida[favorecida].situacion
                for opcion in escena.opciones:
                    assert escena.etiqueta(opcion).strip()


def test_prompt_escena_dirige_solo_la_fisica_del_lado_sin_filtrar_mecanica():
    especies = av.BIOMAS["bosque"].nombres_especies
    fuerza, _ = per.prompt_escena(
        "al Bosque", 1, especies=especies,
        pareja=(av.FUERZA, av.VELOCIDAD), favorecida=av.FUERZA,
    )
    velocidad, _ = per.prompt_escena(
        "al Bosque", 1, especies=especies,
        pareja=(av.FUERZA, av.VELOCIDAD), favorecida=av.VELOCIDAD,
    )
    salud, _ = per.prompt_escena(
        "al Bosque", 1, especies=especies,
        pareja=(av.SALUD, av.INGENIO), favorecida=av.SALUD,
    )
    ingenio, _ = per.prompt_escena(
        "al Bosque", 1, especies=especies,
        pareja=(av.SALUD, av.INGENIO), favorecida=av.INGENIO,
    )

    assert "se presta al cuerpo" in fuerza
    assert "se presta al impulso" not in fuerza
    assert "se presta al impulso" in velocidad
    assert "se presta al cuerpo" not in velocidad
    assert "se presta al aguante" in salud
    assert "se presta a la observación" not in salud
    assert "se presta a la observación" in ingenio
    assert "se presta al aguante" not in ingenio
    # Salud es aguante y nunca curación; ingenio es leer y nunca magia. Las dos
    # reglas viajan sólo cuando su senda está activa.
    for prompt in (salud, ingenio):
        assert "nunca curar, sanar ni atender a nadie" in prompt
        assert "nunca magia" in prompt
    for prompt in (fuerza, velocidad):
        assert "nunca curar, sanar ni atender a nadie" not in prompt
        assert "nunca magia" not in prompt
    for prompt in (fuerza, velocidad, salud, ingenio):
        for fuga in ("favorable", "pareja", "cuesta arriba", "temeraria", "probabilidad"):
            assert fuga not in prompt.casefold()
        assert "estadísticas" in prompt


def test_prompt_escena_solo_nombra_la_pareja_activa_y_ninguna_cifra():
    """El modelo pone texto en huecos ya decididos: ni elige pareja ni mecánica."""
    bicho = criatura(fuerza=11, velocidad=22, base_salud=33, base_ingenio=44)
    for pareja in av.PAREJAS:
        for favorecida in pareja:
            sistema, peticion = per.prompt_escena(
                "al Bosque", 1, especies=av.BIOMAS["bosque"].nombres_especies,
                pareja=pareja, favorecida=favorecida,
            )
            for activa in pareja:
                assert f'"{activa}"' in sistema
            for inactiva in av.complementaria(pareja):
                assert f'"{inactiva}"' not in sistema
            entero = sistema + peticion
            assert bicho.nombre not in entero
            # Ni las stats de nadie, ni el dado, ni la exigencia del terreno.
            for fuga in ("11", "22", "33", "44", "1d20", "d20", "dificultad"):
                assert fuga not in entero.casefold(), fuga
    assert "criatura" not in inspect.signature(per.prompt_escena).parameters


def test_prompt_escena_exige_pareja_y_favorecida_de_esa_pareja():
    with pytest.raises(TypeError):
        per.prompt_escena("al Bosque", 1, especies=("Piollito",))
    with pytest.raises(TypeError):
        per.prompt_escena(
            "al Bosque", 1, especies=("Piollito",),
            pareja=(av.SALUD, av.INGENIO),
        )
    with pytest.raises(ValueError):
        per.prompt_escena(
            "al Bosque", 1, especies=("Piollito",),
            pareja=(av.SALUD, av.INGENIO), favorecida=av.FUERZA,
        )


@pytest.mark.parametrize("pareja", av.PAREJAS)
def test_el_json_dinamico_llena_cada_pareja_y_lo_extra_no_mueve_nada(pareja):
    crudo = (
        '{"situacion":"Un paso.",'
        f'"{pareja[0]}":"Primera salida","{pareja[1]}":"Segunda salida",'
        '"volver":"Rodear","favorecida":"fuerza","dificultad":9,'
        '"exito":true,"premio":"gemas"}'
    )

    escena = av.escena_desde_json(crudo, pareja)

    assert escena == av.Escena(
        "Un paso.", pareja, ("Primera salida", "Segunda salida"), "Rodear",
    )
    # Con las claves de la otra pareja no cuadra nada y se cae al respaldo.
    assert av.escena_desde_json(crudo, av.complementaria(pareja)) is None


# --- Balance exacto, sin Monte Carlo --------------------------------------


def test_balance_exacto_conserva_acceso_y_no_crea_una_receta_unica():
    builds = ((11, 21), (20, 9), (15, 15), (14, 19), (14, 10),
              (14, 13), (16, 21), (24, 16), (9, 8))
    dificultades = sorted({b.dificultad for b in av.BIOMAS.values()})
    acceso = []
    cambia_caza = cambia_marca = estados = 0

    def tension_esperada(stat, exigencia):
        return sum(
            sim.esfuerzo_de_aventura(av.FUERZA, stat + dado - exigencia).bruto
            * (sim.PROFUNDA if stat + dado - exigencia in (0, 1) else 1)
            if av.deja_marca(stat + dado - exigencia) else 0
            for dado in range(1, 21)
        ) / 20

    for fuerza, velocidad in builds:
        for dificultad in dificultades:
            probabilidades_por_lado = []
            for favorecida in (av.FUERZA, av.VELOCIDAD):
                exigencias = (
                    dificultad - 2 if favorecida == av.FUERZA else dificultad + 2,
                    dificultad - 2 if favorecida == av.VELOCIDAD else dificultad + 2,
                )
                t = av.Terreno((av.FUERZA, av.VELOCIDAD), exigencias)
                probabilidades = (
                    av.probabilidad_opcion(fuerza, t.exigencia(av.FUERZA)),
                    av.probabilidad_opcion(velocidad, t.exigencia(av.VELOCIDAD)),
                )
                tensiones = (
                    tension_esperada(fuerza, t.exigencia(av.FUERZA)),
                    tension_esperada(velocidad, t.exigencia(av.VELOCIDAD)),
                )
                ingenua = 0 if fuerza >= velocidad else 1
                caza = max(range(2), key=lambda i: (probabilidades[i], i == ingenua))
                marca = max(range(2), key=lambda i: (tensiones[i], probabilidades[i]))
                cambia_caza += caza != ingenua
                cambia_marca += marca != caza
                estados += 1
                probabilidades_por_lado.append(probabilidades[caza])
            p_nodo = sum(probabilidades_por_lado) / 2
            acceso.append(p_nodo * p_nodo * av.HALLAZGOS[2][av.SALVAJE] / 100)

    assert 0.23 <= sum(acceso) / len(acceso) <= 0.28
    assert cambia_caza / estados >= 0.10
    assert cambia_marca / estados >= 0.20


# --- Integración compacta del árbol ---------------------------------------


class RNGTraza:
    def __init__(self, valores=(20, 0)):
        self.eventos = []
        self.valores = iter(valores)

    def randint(self, minimo, maximo):
        self.eventos.append(("randint", minimo, maximo))
        return next(self.valores)

    def choice(self, opciones):
        self.eventos.append(("choice", len(opciones)))
        return opciones[0]


def test_fallar_cierra_el_viaje_con_un_solo_dado():
    """Fallar cierra el viaje ahí: ni dado del terreno siguiente ni otra escena,
    y la senda se cuenta como perdida de largo."""
    rng = RNGTraza(valores=(1,))
    viaje = av.Viaje(av.BIOMAS["bosque"], escena(), terreno())

    despues = av.avanzar(viaje, criatura(fuerza=1), av.FUERZA, None, None, rng)

    assert rng.eventos == [("randint", 1, 20)]
    assert not despues.sigue and despues.fallo
    assert despues.terreno.pareja == (av.FUERZA, av.VELOCIDAD)
    assert av.render_beat(despues.pruebas[-1]) == (
        "✗ Mover la roca — 💪 1 + 1 = 2 / 22 · de largo, sin marca"
    )


# --- Historial y prompt salvaje -------------------------------------------


def contexto(*, antes=39, despues=42, historial=(), dicho="hola"):
    bicho = salvaje()
    previo = av.Encuentro(bicho, confianza=antes, paciencia=4)
    actual = av.Encuentro(bicho, confianza=despues, paciencia=3, ultimo_cambio=3)
    return av.ContextoSalvaje(
        salvaje=bicho,
        acompañante=criatura(),
        fase=av.fase_de(previo.confianza),
        fase_ahora=av.fase_de(actual.confianza),
        tendencia=av.tendencia_de(previo, actual),
        paciencia=actual.paciencia,
        dicho=dicho,
        historial=historial,
    )


def test_fases_y_tendencia_salen_del_estado_antes_y_despues():
    assert [av.fase_de(n) for n in (0, 39, 40, 69, 70, 100)] == [
        "arisco", "arisco", "receloso", "receloso", "cercano", "cercano"
    ]
    bicho = salvaje()
    antes = av.Encuentro(bicho, confianza=40, paciencia=4)
    assert av.tendencia_de(antes, replace(antes, confianza=45, paciencia=3)) == "mejora"
    assert av.tendencia_de(antes, replace(antes, confianza=45, paciencia=2)) == "recela"
    assert av.tendencia_de(antes, replace(antes, paciencia=3)) == "estancada"


def test_historial_unico_intercala_fifo_y_trunca_respuestas():
    eventos = (
        av.TurnoHablar("uno", "a" * 300),
        av.TurnoGesto(av.GOLOSINAS, av.frase_gesto(av.GOLOSINAS, True)),
        av.TurnoHablar("dos", "respuesta dos"),
        av.TurnoGesto(av.ESPERAR, av.frase_gesto(av.ESPERAR, False)),
        av.TurnoHablar("tres", "respuesta tres"),
    )
    historial = ()
    for evento in eventos:
        historial = av.recordar(historial, evento)

    assert historial == eventos[-4:]
    assert len(historial) == av.MAX_HISTORIAL_ENCUENTRO == 4
    truncado = av.recordar((), eventos[0])[0]
    assert isinstance(truncado, av.TurnoHablar)
    assert len(truncado.contesto) == av.LARGO_CONTESTO_HISTORIAL == 160


def test_prompt_salvaje_renderiza_historial_real_en_orden_y_oculta_caracter():
    historial = (
        av.TurnoHablar("Tranquilo", "Mrrf. Eso dicen todos."),
        av.TurnoGesto(av.GOLOSINAS, av.frase_gesto(av.GOLOSINAS, True)),
        av.TurnoHablar("Somos amigos", "No te emociones."),
    )
    ctx = contexto(antes=65, despues=72, historial=historial, dicho="¿Vienes?")

    sistema, peticion = per.prompt_salvaje(ctx)

    bloque_estado = sistema.split("CÓMO ESTÁS AHORA\n", 1)[1].split(
        "\n\nCÓMO RESPONDER", 1
    )[0]
    assert [linea.partition(":")[0] for linea in bloque_estado.splitlines()] == [
        "- Antes", "- Ahora", "- Tendencia"
    ]
    assert sistema.index("empiezas a escuchar") < sistema.index("casi convencido")
    assert "lo último que hicieron te gustó" in sistema
    assert "sereno" not in sistema.casefold() and "serena" not in sistema.casefold()
    prompt = sistema + peticion
    assert "Nube" in prompt and esp.ESPECIES["pulpo"].nombre in prompt
    peticion_neutra = peticion.casefold()
    posiciones = [peticion_neutra.index(texto.casefold()) for texto in (
        "Tranquilo", "te ofrecieron golosinas", "Somos amigos", "¿Vienes?"
    )]
    assert posiciones == sorted(posiciones)
    assert "Nunca digas que te unes ni que te vas" in sistema


def test_respaldo_salvaje_es_coherente_con_fase_y_tendencia():
    arisco = per.respaldo_salvaje(contexto(antes=20, despues=22), 0)
    cercano = per.respaldo_salvaje(contexto(antes=70, despues=75), 0)
    recela = per.respaldo_salvaje(
        replace(contexto(antes=70, despues=75), tendencia="recela"), 0
    )

    assert arisco != cercano
    assert "distancia" in arisco.casefold()
    assert any(palabra in cercano.casefold() for palabra in ("cerca", "confianza", "acepta"))
    assert "desconfía" not in cercano.casefold()
    assert "sin irse" in recela.casefold()


# --- Voz terminal y garantía estructural ----------------------------------


def test_catalogo_terminal_cubre_todas_las_voces_y_concuerda():
    assert set(per.VOCES) == set(esp.ESPECIES)
    for especie, voz in per.VOCES.items():
        for desenlace, lineas in (("se_une", voz.al_unirse), ("se_va", voz.al_irse)):
            assert len(lineas) >= 2, (especie, desenlace)
            assert all(0 < len(linea) <= 120 for linea in lineas)
            for genero in esp.GENEROS:
                bicho = salvaje(especie, genero)
                for semilla in range(len(lineas)):
                    linea = per.linea_desenlace(bicho, desenlace, semilla)
                    assert linea == esp.concordar(lineas[semilla], genero)
                    assert "{" not in linea and "}" not in linea
    goot_hembra = salvaje("goot", esp.HEMBRA)
    prinel_hembra = salvaje("prinel", esp.HEMBRA)
    assert "sola" in per.linea_desenlace(goot_hembra, "se_va", 0)
    assert "Decidida" in per.linea_desenlace(prinel_hembra, "se_une", 0)


@pytest.mark.parametrize(
    ("opcion", "le_gusta"),
    ((av.GOLOSINAS, True), (av.PRESUMIR, False), (av.ESPERAR, True)),
)
def test_el_gesto_se_recuerda_por_lo_que_le_parece_a_su_caracter(opcion, le_gusta):
    """Un gesto no pasa por la IA: lo que se recuerda es una frase escrita, la
    de si a un salvaje sereno le gusta o no."""
    bicho = salvaje()

    assert av.le_gusta(bicho, opcion) is le_gusta
    turno = av.TurnoGesto(opcion, av.frase_gesto(opcion, le_gusta))
    assert av.recordar((), turno) == (turno,)


@pytest.mark.parametrize("opcion", av.OPCIONES)
@pytest.mark.parametrize("desenlace", ("se_une", "se_va"))
def test_el_turno_terminal_cuenta_lo_que_movio_la_jugada(opcion, desenlace):
    """El turno que cierra el encuentro: unirse llena la confianza, y quedarse
    sin turnos se cuenta como que se cansa y se va."""
    bicho = salvaje()
    antes = av.Encuentro(bicho, confianza=80, paciencia=2)
    despues = replace(
        antes,
        confianza=100 if desenlace == "se_une" else 50,
        paciencia=1 if desenlace == "se_une" else 0,
    )
    emoji, etiqueta = av.ETIQUETAS[opcion]

    assert not despues.sigue
    assert despues.se_une is (desenlace == "se_une")
    assert av.narrar_opcion(antes, opcion, despues) == (
        f"-# {emoji} {etiqueta} · confianza +20" if desenlace == "se_une"
        else f"-# {emoji} {etiqueta} · **Se cansa de esperar y se va.**"
    )
