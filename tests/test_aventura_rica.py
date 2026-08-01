# pyright: reportArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false
"""Contrato del terreno honesto y del encuentro salvaje contextual."""
import asyncio
import inspect
import random
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import aventura as av
import cogs.aventura as cog_av
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
    return av.Escena(nombre, "Mover la roca", "Cruzar el hueco", "Dar un rodeo")


def terreno(bioma="bosque", favorecida=av.FUERZA):
    dificultad = av.BIOMAS[bioma].dificultad
    return av.Terreno(
        dificultad - 2 if favorecida == av.FUERZA else dificultad + 2,
        dificultad - 2 if favorecida == av.VELOCIDAD else dificultad + 2,
    )


def salvaje(
    especie="michi", genero=esp.MACHO, caracter="sereno",
):
    return av.Salvaje(
        especie, esp.ESPECIES[especie].nombre, genero, caracter, (10, 10, 10)
    )


# --- Terreno, riesgo y marca -----------------------------------------------


def test_terreno_se_sortea_ciego_y_aplica_menos_dos_mas_dos():
    bioma = av.BIOMAS["bosque"]
    fuerza = av.tirar_terreno(bioma, DadosFijos([0]))
    velocidad = av.tirar_terreno(bioma, DadosFijos([1]))

    assert fuerza == av.Terreno(bioma.dificultad - 2, bioma.dificultad + 2)
    assert velocidad == av.Terreno(bioma.dificultad + 2, bioma.dificultad - 2)
    assert fuerza.favorecida == av.FUERZA
    assert velocidad.favorecida == av.VELOCIDAD
    assert "criatura" not in inspect.signature(av.tirar_terreno).parameters


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
    assert av.pista_marcas(criatura(99, 99), av.Terreno(24, 24)).endswith(
        "ninguna"
    )
    assert av.pista_marcas(criatura(15, 99), av.Terreno(24, 24)).endswith(
        "sólo la 💪"
    )
    assert av.pista_marcas(criatura(15, 15), av.Terreno(24, 24)).endswith(
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


def test_catalogo_es_exactamente_dos_mas_dos_por_bioma_y_respeta_evitar():
    assert set(av.ESCENAS_ESCRITAS) == set(av.BIOMAS)
    for clave, por_lado in av.ESCENAS_ESCRITAS.items():
        assert set(por_lado) == {av.FUERZA, av.VELOCIDAD}
        assert len(por_lado[av.FUERZA]) == len(por_lado[av.VELOCIDAD]) == 2
        assert len(set(por_lado[av.FUERZA] + por_lado[av.VELOCIDAD])) == 4
        bioma = av.BIOMAS[clave]
        for lado in (av.FUERZA, av.VELOCIDAD):
            vista = por_lado[lado][0]
            for semilla in range(5):
                assert av.escena_escrita(
                    bioma, lado, vista, random.Random(semilla)
                ) != vista


def test_prompt_escena_dirige_solo_la_fisica_del_lado_sin_filtrar_mecanica():
    especies = av.BIOMAS["bosque"].nombres_especies
    fuerza, _ = per.prompt_escena(
        "al Bosque", 1, especies=especies, favorecida=av.FUERZA
    )
    velocidad, _ = per.prompt_escena(
        "al Bosque", 1, especies=especies, favorecida=av.VELOCIDAD
    )

    assert "se presta al cuerpo" in fuerza
    assert "se presta al impulso" not in fuerza
    assert "se presta al impulso" in velocidad
    assert "se presta al cuerpo" not in velocidad
    for prompt in (fuerza, velocidad):
        for fuga in ("favorable", "pareja", "cuesta arriba", "temeraria", "probabilidad"):
            assert fuga not in prompt.casefold()
        assert "estadísticas" in prompt


def test_prompt_escena_exige_favorecida_y_json_extra_no_mueve_mecanica():
    with pytest.raises(TypeError):
        per.prompt_escena("al Bosque", 1, especies=("Piollito",))
    salida = av.escena_desde_json(
        '{"situacion":"Un muro.","fuerza":"Empujar",'
        '"velocidad":"Trepar","volver":"Rodear","favorecida":"velocidad"}'
    )
    assert salida == av.Escena("Un muro.", "Empujar", "Trepar", "Rodear")


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
                t = av.Terreno(
                    dificultad - 2 if favorecida == av.FUERZA else dificultad + 2,
                    dificultad - 2 if favorecida == av.VELOCIDAD else dificultad + 2,
                )
                probabilidades = (
                    av.probabilidad_opcion(fuerza, t.fuerza),
                    av.probabilidad_opcion(velocidad, t.velocidad),
                )
                tensiones = (
                    tension_esperada(fuerza, t.fuerza),
                    tension_esperada(velocidad, t.velocidad),
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
    def __init__(self):
        self.eventos = []
        self.valores = iter((20, 0))

    def randint(self, minimo, maximo):
        self.eventos.append(("randint", minimo, maximo))
        return next(self.valores)

    def choice(self, opciones):
        self.eventos.append(("choice", len(opciones)))
        return opciones[0]


def test_primer_roll_y_siguiente_terreno_comparten_un_edit_y_orden_rng(monkeypatch):
    monkeypatch.setattr(cog_av.db, "uso_ia_ultima_hora", lambda *_: 999)
    rng = RNGTraza()
    monkeypatch.setattr(cog_av.random, "Random", lambda: rng)
    bioma = av.BIOMAS["bosque"]
    viaje = av.Viaje(bioma, escena(), terreno(),)
    vista = cog_av.ViajeView(
        Mock(), SimpleNamespace(id="u1", display_name="Felipe"), "g1",
        criatura(fuerza=99), viaje,
    )
    mensaje = SimpleNamespace(edit=AsyncMock())
    vista.mensaje = mensaje
    vista.cog.resolver = AsyncMock()
    interaccion = SimpleNamespace(
        response=SimpleNamespace(defer=AsyncMock()), channel=None,
    )

    asyncio.run(vista.children[0].callback(interaccion))

    mensaje.edit.assert_awaited_once()
    contenido = mensaje.edit.await_args.kwargs["content"]
    assert "✓ Mover la roca — 💪 99 + 20 = 119 / 22" in contenido
    assert vista.viaje.escena.situacion in contenido
    assert "pueden forjar marca" in contenido
    assert rng.eventos[:3] == [
        ("randint", 1, 20), ("randint", 0, 1), ("choice", 2)
    ]
    assert vista.viaje.escena in av.ESCENAS_ESCRITAS["bosque"][
        vista.viaje.terreno.favorecida
    ]


def test_botones_muestran_bandas_reales_y_siguen_bajo_el_tope(monkeypatch):
    monkeypatch.setattr(cog_av.db, "uso_ia_ultima_hora", lambda *_: 999)
    larga = escena()
    larga = replace(larga, fuerza="F" * av.LARGO_ETIQUETA,
                    velocidad="V" * av.LARGO_ETIQUETA)
    bioma = av.BIOMAS["bosque"]
    vista = cog_av.ViajeView(
        Mock(), SimpleNamespace(id="u1", display_name="Felipe"), "g1",
        criatura(), av.Viaje(bioma, larga, terreno()),
    )

    etiquetas = [boton.label for boton in vista.children]
    assert etiquetas[0].endswith(" · pareja")
    assert etiquetas[1].endswith(" · pareja")
    assert etiquetas[2] == "Dar un rodeo"
    assert all(len(etiqueta) <= cog_av.LARGO_BOTON for etiqueta in etiquetas)


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


@pytest.mark.parametrize("opcion", (av.GOLOSINAS, av.PRESUMIR, av.ESPERAR))
def test_gesto_no_terminal_es_determinista_y_no_llama_ia(monkeypatch, opcion):
    monkeypatch.setattr(cog_av.db, "inventario", lambda *_: {})
    bicho = salvaje()
    antes = av.Encuentro(bicho, confianza=40, paciencia=4)
    despues = replace(antes, confianza=48, paciencia=3, ultimo_cambio=8)
    monkeypatch.setattr(cog_av.av, "aplicar_opcion", lambda *_: despues)
    cog = SimpleNamespace(contestar=AsyncMock())
    vista = cog_av.EncuentroView(
        cog, SimpleNamespace(id="u1", display_name="Felipe"), "g1",
        criatura(), antes,
    )
    interaccion = SimpleNamespace(
        response=SimpleNamespace(is_done=lambda: True, defer=AsyncMock()),
        edit_original_response=AsyncMock(),
    )

    asyncio.run(vista._jugar(interaccion, opcion))

    cog.contestar.assert_not_awaited()
    assert len(vista.historial) == 1
    assert isinstance(vista.historial[0], av.TurnoGesto)


@pytest.mark.parametrize("opcion", av.OPCIONES)
@pytest.mark.parametrize("desenlace", ("se_une", "se_va"))
def test_turno_terminal_no_llama_ia_no_registra_y_usa_voz_cerrada(
    monkeypatch, opcion, desenlace
):
    monkeypatch.setattr(cog_av.db, "inventario", lambda *_: {})
    bicho = salvaje()
    antes = av.Encuentro(bicho, confianza=80, paciencia=2)
    despues = replace(
        antes,
        confianza=100 if desenlace == "se_une" else 50,
        paciencia=1 if desenlace == "se_une" else 0,
    )
    monkeypatch.setattr(cog_av.av, "aplicar_opcion", lambda *_: despues)
    cog = SimpleNamespace(contestar=AsyncMock(return_value="¡me marcho para siempre!"))
    vista = cog_av.EncuentroView(
        cog, SimpleNamespace(id="u1", display_name="Felipe"), "g1",
        criatura(), antes,
    )
    vista.historial = (av.TurnoHablar("antes", "respuesta"),)
    vista._unirse = AsyncMock()
    interaccion = SimpleNamespace(
        response=SimpleNamespace(is_done=lambda: True, defer=AsyncMock()),
        edit_original_response=AsyncMock(),
        channel_id="c1",
    )

    asyncio.run(vista._jugar(interaccion, opcion, "hola"))

    cog.contestar.assert_not_awaited()
    assert vista.historial == (av.TurnoHablar("antes", "respuesta"),)
    linea = per.linea_desenlace(
        bicho, desenlace, despues.confianza + despues.paciencia
    )
    if desenlace == "se_une":
        llamada = vista._unirse.await_args
        assert llamada is not None
        reaccion = llamada.args[1]
    else:
        reaccion = interaccion.edit_original_response.await_args.kwargs["content"]
    assert linea in reaccion
    assert "¡me marcho para siempre!" not in reaccion


def test_solo_hablar_no_terminal_llama_una_vez_y_guarda_lo_mostrado(monkeypatch):
    monkeypatch.setattr(cog_av.db, "inventario", lambda *_: {})
    bicho = salvaje()
    antes = av.Encuentro(bicho, confianza=40, paciencia=4)
    despues = replace(antes, confianza=48, paciencia=3, ultimo_cambio=8)
    monkeypatch.setattr(cog_av.av, "aplicar_opcion", lambda *_: despues)
    cog = SimpleNamespace(contestar=AsyncMock(return_value="Mrrf. Te escucho."))
    vista = cog_av.EncuentroView(
        cog, SimpleNamespace(id="u1", display_name="Felipe"), "g1",
        criatura(), antes,
    )
    interaccion = SimpleNamespace(
        response=SimpleNamespace(is_done=lambda: True, defer=AsyncMock()),
        edit_original_response=AsyncMock(),
    )

    asyncio.run(vista._jugar(interaccion, av.HABLAR, "hola"))

    cog.contestar.assert_awaited_once()
    assert vista.historial == (av.TurnoHablar("hola", "Mrrf. Te escucho."),)
    contenido = interaccion.edit_original_response.await_args.kwargs["content"]
    assert "> Mrrf. Te escucho." in contenido
