# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
"""Las mutaciones externas apagan la ficha viva que acaba de quedar obsoleta."""
import asyncio
import random
import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock, call

import discord
import pytest

import competir as comp
import db
import economia
import equipo
import especies as esp
import nacer
import pantalla
import retrato
import simulacion as sim
import vistas

# Un bicho SIN retrato dibujado. Estos tests miran la ficha de TEXTO; si la
# especie tuviera imagen, la ficha sería un embed y dejarían de comprobar lo
# suyo. Se busca en vez de fijarse para que dibujar más especies no los rompa.
SIN_RETRATO = next(
    c for c in esp.ESPECIES if c not in retrato.CON_ETAPAS_COMPLETAS
)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)


@pytest.fixture(autouse=True)
def estilo_imagen(monkeypatch):
    monkeypatch.setattr(db, "estilo_de_ficha", lambda *_: "imagen")


def criatura(id_, nombre, activa, pantalla_msg_id) -> sim.Criatura:
    return sim.Criatura(
        id=id_, usuario_id="u1", guild_id="g1", especie=SIN_RETRATO,
        nombre=nombre,
        nacida_en=T0, actualizada_en=T0,
        base_fuerza=15, base_velocidad=15, base_salud=15,
        hambre=80.0, animo=80.0, activa=activa,
        pantalla_msg_id=pantalla_msg_id,
    )


@pytest.fixture
def bd_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "vistas.db")
    db.inicializar()


def interaccion_de(
    evento_id="evento", mensaje_id="ficha"
) -> tuple[Any, SimpleNamespace, SimpleNamespace]:
    respuesta = SimpleNamespace(
        edit_message=AsyncMock(),
        send_message=AsyncMock(),
    )
    canal = SimpleNamespace(id="canal", send=AsyncMock())
    interaccion = SimpleNamespace(
        id=evento_id,
        user=SimpleNamespace(id="u1"),
        guild_id="g1",
        message=SimpleNamespace(id=mensaje_id),
        response=respuesta,
        channel=canal,
    )
    return interaccion, respuesta, canal


def test_recibo_de_entrenamiento_detalla_efecto_costo_recompensa_y_tope():
    resultado = economia.ResultadoCuidado(
        criatura=criatura(1, "Mia", True, "ficha"),
        mensaje="Entrenamiento duro.",
        delta_asciicoins=1,
        usados=1,
    )

    assert vistas.texto_recibo_cuidado(resultado, sim.ENTRENAR) == (
        "-# 🏋️ Entrenar fuerza · fuerza +2 entrenamiento · +3 XP · "
        "coste base -15 comida · coste base -10 ánimo · "
        "🪙 +1 moneda · cuidado 1/12 UTC"
    )


def test_recibos_de_cuidado_redondean_los_stats_vivos():
    fraccionaria = replace(
        criatura(1, "Mia", True, "ficha"),
        hambre=89.5837,
        animo=99.9991,
        limpieza=42.4999,
    )
    resultado = economia.ResultadoCuidado(
        criatura=fraccionaria,
        mensaje="Ñam.",
        delta_asciicoins=1,
        usados=1,
        ent_salud_ganada=1,
    )

    recibos = {
        accion: vistas.texto_recibo_cuidado(resultado, accion)
        for accion in (sim.ALIMENTAR, sim.JUGAR, sim.ENTRENAR, sim.LIMPIAR)
    }
    assert recibos[sim.ALIMENTAR] == (
        "-# 🍖 Alimentar · comida 90 · ánimo 100 · salud +1 entrenamiento · "
        "+1 XP · 🪙 +1 moneda · cuidado 1/12 UTC"
    )
    assert recibos[sim.JUGAR] == (
        "-# 🪀 Jugar · ánimo 100 · velocidad +1 entrenamiento · +2 XP · "
        "coste base -5 comida · 🪙 +1 moneda · cuidado 1/12 UTC"
    )
    empacho = replace(resultado, ent_salud_ganada=0)
    assert "salud" not in vistas.texto_recibo_cuidado(empacho, sim.ALIMENTAR)

    decimal_vivo = re.compile(r"(?:comida|ánimo|aseo) -?\d+\.\d+")
    for recibo in recibos.values():
        assert not decimal_vivo.search(f"{recibo} · versión 1.2.3")


def test_recibo_de_cuidado_conserva_topes_y_recompensa_de_evolucion():
    base = criatura(1, "Mia", True, "ficha")
    evolucionada = replace(base, nivel=5)

    # Con cuidados de sobra (5 de 12), lo que frenó fue el bote del día.
    por_el_bote = economia.ResultadoCuidado(
        criatura=base,
        mensaje="Entrenamiento duro.",
        delta_asciicoins=0,
        usados=5,
        topada=True,
    )
    assert vistas.texto_recibo_cuidado(por_el_bote, sim.ENTRENAR).endswith(
        "🪙 +0 monedas (bote diario lleno) · cuidado 5/12 UTC"
    )

    # Y con los doce gastados, el freno es el de la actividad. Distinguirlos
    # importa porque se arreglan distinto: el de cuidados se esquiva compitiendo
    # o saliendo de aventura, y el bote no se esquiva.
    por_la_actividad = replace(por_el_bote, usados=economia.TOPE_CUIDADOS)
    assert vistas.texto_recibo_cuidado(por_la_actividad, sim.ENTRENAR).endswith(
        "🪙 +0 monedas (tope de cuidados) · cuidado 12/12 UTC"
    )

    evolucion = economia.ResultadoCuidado(
        criatura=evolucionada,
        mensaje="Entrenamiento duro.",
        etapa_anterior=base.etapa,
        delta_asciicoins=economia.PREMIO_EVOLUCION,
        delta_evolucion=economia.PREMIO_EVOLUCION,
        usados=economia.TOPE_CUIDADOS,
        evolucion_usadas=economia.TOPE_EVOLUCIONES,
        topada=True,
    )
    assert vistas.texto_recibo_cuidado(evolucion, sim.ENTRENAR).endswith(
        "🪙 +0 monedas (tope de cuidados) · cuidado 12/12 UTC · "
        "evolución +10 · 1/1 UTC"
    )


def test_abrir_entrenamiento_conjunto_ofrece_a_todos_los_vivos_que_no_son_el_activo(
    bd_temporal
):
    activa = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    otra = db.crear("u1", "g1", "michi", "Lúa", STATS, T0, activa=False)
    recluta = db.crear(
        "u1", "g1", "michi", "Brote", STATS, T0, activa=False, se_nombro_solo=True
    )
    db.guardar_pantalla(activa.id, "ficha", "canal")
    interaccion, respuesta, _ = interaccion_de()

    asyncio.run(vistas.abrir_entrenamiento_conjunto(interaccion))

    llamada = respuesta.send_message.await_args
    assert llamada.args == ("Elige con quién entrena tu gachamon activo.",)
    assert [opcion.label for opcion in llamada.kwargs["view"].children[0].options] == [
        "Lúa", "Brote"
    ]
    assert otra.id < recluta.id


def test_abrir_entrenamiento_conjunto_filtra_y_captura_reservas_elegibles(
    bd_temporal, monkeypatch
):
    activa = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    elegible = db.crear(
        "u1", "g1", "michi", "Lúa", STATS, T0, activa=False
    )
    muerta = db.crear(
        "u1", "g1", "michi", "Nube", STATS, T0, activa=False
    )
    db.guardar(replace(muerta, muerta_en=T0, causa_muerte="prueba"))
    db.guardar_pantalla(activa.id, "ficha", "canal")
    interaccion, respuesta, _ = interaccion_de()

    asyncio.run(vistas.abrir_entrenamiento_conjunto(interaccion))

    respuesta.send_message.assert_awaited_once()
    llamada = respuesta.send_message.await_args
    assert llamada is not None and llamada.kwargs["ephemeral"] is True
    vista = llamada.kwargs["view"]
    assert isinstance(vista, vistas.VistaEntrenamientoConjunto)
    menu = vista.children[0]
    assert isinstance(menu, vistas.MenuEntrenamientoConjunto)
    assert [(opcion.value, opcion.label) for opcion in menu.options] == [
        (str(elegible.id), "Lúa")
    ]
    assert menu.activo == (activa.id, "Mia")
    assert menu.reservas == {str(elegible.id): (elegible.id, "Lúa")}


def test_abrir_entrenamiento_conjunto_rechaza_ficha_caduca_o_sin_reservas(
    bd_temporal
):
    activa = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.guardar_pantalla(activa.id, "ficha", "canal")
    interaccion, respuesta, _ = interaccion_de(mensaje_id="otra")

    asyncio.run(vistas.abrir_entrenamiento_conjunto(interaccion))

    respuesta.send_message.assert_awaited_once_with(
        "Esta ficha ya no está vigente. Abre la actual con `/mascota`.",
        ephemeral=True,
    )

    interaccion, respuesta, _ = interaccion_de()
    asyncio.run(vistas.abrir_entrenamiento_conjunto(interaccion))
    respuesta.send_message.assert_awaited_once_with(
        "No tienes otro gachamon con quien entrenar.",
        ephemeral=True,
    )


def test_menu_entrenamiento_conjunto_acusa_antes_de_publicar_y_anuncia_ambos(
    monkeypatch
):
    activa = criatura(1, "Mia", True, "ficha")
    reserva = criatura(2, "Lúa", False, None)
    participantes = (
        sim.aplicar_entrenamiento_conjunto(activa),
        sim.aplicar_entrenamiento_conjunto(reserva),
    )
    resultado = economia.ResultadoEntrenamientoConjunto(
        participantes=participantes, delta_asciicoins=1, usados=1
    )
    eventos = []

    def ejecutar(*args):
        eventos.append(("economia", args))
        return resultado

    async def responder(**kwargs):
        eventos.append(("respuesta", kwargs))

    async def publicar(*args, **kwargs):
        eventos.append(("publicar", args, kwargs))

    async def anunciar(*args):
        eventos.append(("logro", args))

    monkeypatch.setattr(vistas.economia, "ejecutar_entrenamiento_conjunto", ejecutar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    monkeypatch.setattr(vistas.comun, "anunciar_logros", anunciar)
    monkeypatch.setattr(vistas.db, "ahora_utc", Mock(return_value=T0))
    menu = vistas.MenuEntrenamientoConjunto(activa, [reserva])
    menu._values = [str(reserva.id)]
    canal = SimpleNamespace()
    interaccion = SimpleNamespace(
        id="selector",
        user=SimpleNamespace(id="u1"),
        guild_id="g1",
        channel=canal,
        response=SimpleNamespace(edit_message=responder),
    )

    asyncio.run(menu.callback(interaccion))

    assert [evento[0] for evento in eventos] == [
        "economia",
        "respuesta",
        "publicar",
        "logro",
        "logro",
    ]
    llamada_economia = eventos[0][1]
    assert llamada_economia[:3] == ("selector", "u1", "g1")
    assert llamada_economia[3] == economia.SeleccionEntrenamientoConjunto(
        1, "Mia", 2, "Lúa"
    )
    assert llamada_economia[4] == T0
    respuesta = eventos[1][1]
    assert respuesta == {
        "content": "Entrenamiento conjunto completado.",
        "view": None,
    }
    publicacion = eventos[2]
    assert publicacion[1][:3] == (canal, participantes[0].criatura, T0)
    aviso = publicacion[2]["aviso"]
    assert "**Mia** + **Lúa**" in aviso
    assert "+2 XP · fuerza +1 entrenamiento · -10 comida · -5 ánimo" in aviso
    assert aviso.count("cuidado 1/12 UTC") == 1
    assert [evento[1][1].id for evento in eventos[3:]] == [1, 2]


def test_recibo_conjunto_separa_el_tope_monetario_del_contador_de_cuidado():
    activa = criatura(1, "Mia", True, "ficha")
    reserva = criatura(2, "Lúa", False, None)
    resultado = economia.ResultadoEntrenamientoConjunto(
        participantes=(
            sim.aplicar_entrenamiento_conjunto(activa),
            sim.aplicar_entrenamiento_conjunto(reserva),
        ),
        topada=True,
        usados=5,
    )

    recibo = vistas.texto_resultado_entrenamiento_conjunto(resultado)

    assert "🪙 +0 monedas (bote diario lleno) · cuidado 5/12 UTC" in recibo
    assert "cuidado 5/12 UTC (tope)" not in recibo


@pytest.mark.parametrize(
    "resultado,texto",
    [
        (
            economia.ResultadoEntrenamientoConjunto(replay=True),
            "Esta interacción ya estaba procesada.",
        ),
        (
            economia.ResultadoEntrenamientoConjunto(problema="activo_caduco"),
            "Esta ficha ya no está vigente. Abre la actual con `/mascota`.",
        ),
        (
            economia.ResultadoEntrenamientoConjunto(problema="reserva_caduca"),
            "Ese compañero ya no está disponible. "
            "Abre «Entrenar fuerza juntos» otra vez.",
        ),
    ],
)
def test_menu_entrenamiento_conjunto_cierra_errores_sin_publicar(
    monkeypatch, resultado, texto
):
    activa = criatura(1, "Mia", True, "ficha")
    reserva = criatura(2, "Lúa", False, None)
    monkeypatch.setattr(
        vistas.economia,
        "ejecutar_entrenamiento_conjunto",
        Mock(return_value=resultado),
    )
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    menu = vistas.MenuEntrenamientoConjunto(activa, [reserva])
    menu._values = [str(reserva.id)]
    interaccion, respuesta, _ = interaccion_de()

    asyncio.run(menu.callback(interaccion))

    respuesta.edit_message.assert_awaited_once_with(content=texto, view=None)
    publicar.assert_not_awaited()


def test_menu_entrenamiento_conjunto_nombra_quien_tiene_el_cooldown(monkeypatch):
    activa = criatura(1, "Mia", True, "ficha")
    reserva = criatura(2, "Lúa", False, None)
    resultado = economia.ResultadoEntrenamientoConjunto(
        problema="cooldown", bloqueada=reserva, espera=timedelta(minutes=7)
    )
    monkeypatch.setattr(
        vistas.economia,
        "ejecutar_entrenamiento_conjunto",
        Mock(return_value=resultado),
    )
    menu = vistas.MenuEntrenamientoConjunto(activa, [reserva])
    menu._values = [str(reserva.id)]
    interaccion, respuesta, _ = interaccion_de()

    asyncio.run(menu.callback(interaccion))

    respuesta.edit_message.assert_awaited_once_with(
        content="Todavía no. Lúa puede volver a entrenar en 7 min.", view=None
    )


def test_menu_entrenamiento_conjunto_falla_cerrado_si_el_valor_no_fue_capturado():
    activa = criatura(1, "Mia", True, "ficha")
    reserva = criatura(2, "Lúa", False, None)
    menu = vistas.MenuEntrenamientoConjunto(activa, [reserva])
    menu._values = ["999"]
    interaccion, respuesta, _ = interaccion_de()

    asyncio.run(menu.callback(interaccion))

    respuesta.edit_message.assert_awaited_once_with(
        content="Ese compañero ya no está disponible. "
        "Abre «Entrenar fuerza juntos» otra vez.",
        view=None,
    )


def interaccion_de_selector():
    mensaje = SimpleNamespace(id="ficha", edit=AsyncMock())
    return SimpleNamespace(
        user=SimpleNamespace(id="u1"),
        guild_id="g1",
        message=mensaje,
        response=SimpleNamespace(
            type=None, send_message=AsyncMock(), edit_message=AsyncMock()
        ),
        channel=SimpleNamespace(),
    )


@pytest.mark.parametrize(
    "valor,tipo",
    [
        (comp.CARRERA, comp.CARRERA),
        (comp.SUMO, comp.SUMO),
        (comp.TOTEM, comp.TOTEM),
    ],
)
def test_selector_social_abre_la_modalidad_elegida(monkeypatch, valor, tipo):
    abrir = AsyncMock()
    monkeypatch.setattr(vistas, "_es_de_otro", AsyncMock(return_value=False))
    monkeypatch.setattr(vistas, "abrir_seleccion_rivales", abrir)
    interaccion = interaccion_de_selector()
    selector = next(
        hijo
        for hijo in vistas.PantallaView().children
        if hijo.custom_id == "tama:desafiar"
    )
    selector._values = [valor]

    asyncio.run(selector.callback(interaccion))

    interaccion.message.edit.assert_awaited_once_with(view=selector.view)
    abrir.assert_awaited_once_with(interaccion, tipo)


@pytest.mark.parametrize(
    "custom_id,valor",
    [("tama:desafiar", comp.CARRERA), ("tama:mas_acciones", "tienda")],
)
def test_selectores_acusan_antes_de_restaurar_el_placeholder(
    monkeypatch, custom_id, valor
):
    acuse = asyncio.Event()
    edicion_empezo = asyncio.Event()
    liberar_edicion = asyncio.Event()

    async def responder(*args, **kwargs):
        interaccion.response.type = discord.InteractionResponseType.channel_message
        acuse.set()

    async def editar(**kwargs):
        edicion_empezo.set()
        await liberar_edicion.wait()

    helper = AsyncMock(side_effect=responder)
    monkeypatch.setattr(vistas, "_es_de_otro", AsyncMock(return_value=False))
    monkeypatch.setattr(vistas, "abrir_seleccion_rivales", helper)
    monkeypatch.setattr(vistas.tienda, "abrir_tienda", helper)
    interaccion = interaccion_de_selector()
    interaccion.message.edit.side_effect = editar
    selector = next(
        hijo
        for hijo in vistas.PantallaView().children
        if hijo.custom_id == custom_id
    )
    selector._values = [valor]

    async def comprobar():
        tarea = asyncio.create_task(selector.callback(interaccion))
        await edicion_empezo.wait()
        acusado_antes = acuse.is_set()
        liberar_edicion.set()
        await tarea
        assert acusado_antes

    asyncio.run(comprobar())
    helper.assert_awaited_once()


def test_selector_no_reedita_si_el_helper_ya_actualizo_el_mensaje(monkeypatch):
    async def actualizar(*args):
        interaccion.response.type = discord.InteractionResponseType.message_update

    monkeypatch.setattr(vistas, "_es_de_otro", AsyncMock(return_value=False))
    monkeypatch.setattr(vistas, "_ejecutar", AsyncMock(side_effect=actualizar))
    interaccion = interaccion_de_selector()
    selector = next(
        hijo
        for hijo in vistas.PantallaView().children
        if hijo.custom_id == "tama:mas_acciones"
    )
    selector._values = [sim.ACTUALIZAR]

    asyncio.run(selector.callback(interaccion))

    interaccion.message.edit.assert_not_awaited()


def test_selector_social_conserva_entrenar_juntos(monkeypatch):
    abrir = AsyncMock()
    monkeypatch.setattr(vistas, "_es_de_otro", AsyncMock(return_value=False))
    monkeypatch.setattr(vistas, "abrir_entrenamiento_conjunto", abrir)
    interaccion = interaccion_de_selector()
    selector = next(
        hijo
        for hijo in vistas.PantallaView().children
        if hijo.custom_id == "tama:desafiar"
    )
    selector._values = ["entrenar_juntos"]

    asyncio.run(selector.callback(interaccion))

    interaccion.message.edit.assert_awaited_once_with(view=selector.view)
    abrir.assert_awaited_once_with(interaccion)


@pytest.mark.parametrize(
    "valor,helper,args",
    [
        (sim.ACTUALIZAR, "ejecutar", (sim.ACTUALIZAR,)),
        ("inventario", "inventario", (vistas.congelar,)),
        ("tienda", "tienda", ()),
        (
            "plantel",
            "plantel",
            (vistas.congelar, vistas.publicar_pantalla),
        ),
        ("personalizar", "personalizar", (vistas.republicar_ficha,)),
    ],
)
def test_selector_de_gestion_delega_una_vez_al_helper_actual(
    monkeypatch, valor, helper, args
):
    helpers = {nombre: AsyncMock() for nombre in (
        "ejecutar", "inventario", "tienda", "plantel", "personalizar"
    )}
    monkeypatch.setattr(vistas, "_es_de_otro", AsyncMock(return_value=False))
    monkeypatch.setattr(vistas, "_ejecutar", helpers["ejecutar"])
    monkeypatch.setattr(vistas.tienda, "abrir_inventario", helpers["inventario"])
    monkeypatch.setattr(vistas.tienda, "abrir_tienda", helpers["tienda"])
    monkeypatch.setattr(vistas.equipo, "abrir_plantel", helpers["plantel"])
    monkeypatch.setattr(
        vistas.tienda, "abrir_personalizacion", helpers["personalizar"]
    )
    interaccion = interaccion_de_selector()
    selector = next(
        hijo
        for hijo in vistas.PantallaView().children
        if hijo.custom_id == "tama:mas_acciones"
    )
    selector._values = [valor]

    asyncio.run(selector.callback(interaccion))

    interaccion.message.edit.assert_awaited_once_with(view=selector.view)
    helpers[helper].assert_awaited_once_with(interaccion, *args)
    assert sum(mock.await_count for mock in helpers.values()) == 1


@pytest.mark.parametrize(
    "tipo,maximo,copy",
    [
        (comp.CARRERA, 4, "entre 1 y 4 rivales"),
        (comp.SUMO, 3, "1 o 3 rivales"),
        (comp.TOTEM, 4, "entre 1 y 4 rivales"),
        (comp.LABERINTO, 4, "entre 1 y 4 rivales"),
    ],
)
def test_cada_modalidad_abre_seleccion_privada_con_sus_cantidades(
    tipo, maximo, copy
):
    interaccion = interaccion_de_selector()
    interaccion.client = SimpleNamespace(
        get_cog=Mock(return_value=SimpleNamespace(_retar=AsyncMock()))
    )

    asyncio.run(vistas.abrir_seleccion_rivales(interaccion, tipo))

    llamada = interaccion.response.send_message.await_args
    assert llamada is not None and llamada.kwargs["ephemeral"] is True
    assert copy in llamada.args[0]
    vista = llamada.kwargs["view"]
    assert isinstance(vista, vistas.VistaSeleccionRivales)
    selector = vista.children[0]
    assert isinstance(selector, discord.ui.UserSelect)
    assert selector.min_values == 1
    assert selector.max_values == maximo


def test_el_menu_social_ofrece_el_laberinto():
    """La opción tiene que existir y despachar por el camino genérico."""
    menu = next(
        hijo for hijo in vistas.PantallaView().children
        if hijo.custom_id == "tama:desafiar"
    )
    opciones = {opcion.value: opcion.label for opcion in menu.options}

    assert opciones[comp.LABERINTO] == "Laberinto de Ecos"
    assert comp.LABERINTO in comp.CUANTOS_CABEN
    assert vistas.MenuSeleccionRivales(comp.LABERINTO).max_values == 4


@pytest.mark.parametrize(
    "tipo", [comp.CARRERA, comp.SUMO, comp.TOTEM, comp.LABERINTO]
)
def test_seleccion_de_rivales_termina_en_el_seam_canonico(tipo):
    rivales = [SimpleNamespace(id="u2"), SimpleNamespace(id="u3")]
    retar = AsyncMock()
    interaccion = interaccion_de_selector()
    interaccion.client = SimpleNamespace(
        get_cog=Mock(return_value=SimpleNamespace(_retar=retar))
    )
    selector = vistas.MenuSeleccionRivales(tipo)
    selector._values = rivales

    asyncio.run(selector.callback(interaccion))

    retar.assert_awaited_once_with(
        interaccion, tuple(rivales), tipo, canal_publico=interaccion.channel
    )


def test_selector_de_rivales_reserva_una_sola_delegacion_con_dos_callbacks():
    rivales = [SimpleNamespace(id="u2")]
    entro_en_retar = asyncio.Event()
    liberar_retar = asyncio.Event()

    async def retar(*args, **kwargs):
        if not entro_en_retar.is_set():
            entro_en_retar.set()
            await liberar_retar.wait()

    delegado = AsyncMock(side_effect=retar)
    selector = vistas.MenuSeleccionRivales(comp.CARRERA)
    selector._values = rivales
    primera = interaccion_de_selector()
    segunda = interaccion_de_selector()
    cog = SimpleNamespace(_retar=delegado)
    primera.client = SimpleNamespace(get_cog=Mock(return_value=cog))
    segunda.client = SimpleNamespace(get_cog=Mock(return_value=cog))

    async def competir_dos_veces():
        tarea_primera = asyncio.create_task(selector.callback(primera))
        await entro_en_retar.wait()
        await selector.callback(segunda)
        liberar_retar.set()
        await tarea_primera

    asyncio.run(competir_dos_veces())

    delegado.assert_awaited_once_with(
        primera, tuple(rivales), comp.CARRERA, canal_publico=primera.channel
    )
    segunda.response.send_message.assert_awaited_once_with(
        "Este selector ya se usó. Abre `/mascota` para elegir rivales de nuevo.",
        ephemeral=True,
    )


def test_seleccion_temporal_solo_responde_a_quien_la_abrio():
    vista = vistas.VistaSeleccionRivales("u1", comp.CARRERA)
    interaccion = interaccion_de_selector()
    interaccion.user.id = "u2"

    permitido = asyncio.run(vista.interaction_check(interaccion))

    assert not permitido
    interaccion.response.send_message.assert_awaited_once_with(
        "Este selector de rivales no es tuyo.", ephemeral=True
    )


def test_cog_de_competencias_ausente_falla_sin_crash():
    interaccion = interaccion_de_selector()
    interaccion.client = SimpleNamespace(get_cog=Mock(return_value=None))

    asyncio.run(vistas.abrir_seleccion_rivales(interaccion, comp.CARRERA))

    interaccion.response.send_message.assert_awaited_once_with(
        "Las competencias no están disponibles en este momento.", ephemeral=True
    )

    selector = vistas.MenuSeleccionRivales(comp.CARRERA)
    selector._values = [SimpleNamespace(id="u2")]
    asyncio.run(selector.callback(interaccion))
    interaccion.response.edit_message.assert_awaited_once_with(
        content="Las competencias no están disponibles en este momento.", view=None
    )


def test_entrenamiento_conjunto_reutiliza_el_rechazo_de_ficha_ajena(bd_temporal):
    ajena = db.crear("u2", "g1", SIN_RETRATO, "Ajena", STATS, T0)
    db.guardar_pantalla(ajena.id, "ficha", "canal")
    interaccion, respuesta, _ = interaccion_de()

    asyncio.run(vistas.abrir_entrenamiento_conjunto(interaccion))

    respuesta.send_message.assert_awaited_once_with(
        "Ese es el gachamon de <@u2>. "
        "Saca el tuyo con `/mascota` o `/huevo`.",
        ephemeral=True,
    )


def test_fallo_de_publicacion_deja_commit_y_el_replay_no_republica(
    bd_temporal, monkeypatch
):
    activa = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    reserva = db.crear(
        "u1", "g1", "michi", "Lúa", STATS, T0, activa=False
    )
    db.guardar_pantalla(activa.id, "ficha", "canal")
    monkeypatch.setattr(vistas.db, "ahora_utc", Mock(return_value=T0))
    publicar = AsyncMock(side_effect=RuntimeError("Discord cayó"))
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    monkeypatch.setattr(vistas.comun, "anunciar_logros", AsyncMock())
    menu = vistas.MenuEntrenamientoConjunto(activa, [reserva])
    menu._values = [str(reserva.id)]
    interaccion, respuesta, _ = interaccion_de(evento_id="selector")

    with pytest.raises(RuntimeError, match="Discord cayó"):
        asyncio.run(menu.callback(interaccion))

    activa_guardada = db.obtener(activa.id)
    reserva_guardada = db.obtener(reserva.id)
    assert activa_guardada is not None and reserva_guardada is not None
    assert activa_guardada.xp == reserva_guardada.xp == 2
    asyncio.run(menu.callback(interaccion))
    assert publicar.await_count == 1
    assert respuesta.edit_message.await_args_list == [
        call(content="Entrenamiento conjunto completado.", view=None),
        call(content="Esta interacción ya estaba procesada.", view=None),
    ]


def test_entrenar_juntos_con_el_activo_en_cero_se_completa(
    bd_temporal, monkeypatch
):
    """Días en 0 ya no matan al activo al ponerlo al día: se entrena y se
    publica su ficha viva, sin lápida."""
    activa = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.guardar(replace(activa, hambre=0.0))
    reserva = db.crear("u1", "g1", "michi", "Lúa", STATS, T0, activa=False)
    monkeypatch.setattr(
        vistas.db, "ahora_utc", Mock(return_value=T0 + timedelta(days=3))
    )
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    monkeypatch.setattr(vistas.comun, "anunciar_logros", AsyncMock())
    menu = vistas.MenuEntrenamientoConjunto(activa, [reserva])
    menu._values = [str(reserva.id)]
    interaccion, respuesta, canal = interaccion_de(evento_id="selector")

    asyncio.run(menu.callback(interaccion))

    respuesta.edit_message.assert_awaited_once_with(
        content="Entrenamiento conjunto completado.", view=None
    )
    publicada = publicar.await_args.args[1]
    assert publicada.id == activa.id and publicada.viva
    canal.send.assert_not_awaited()


def test_cambiar_activo_congela_responde_y_publica_en_ese_orden(monkeypatch):
    anterior = criatura(1, "Anterior", True, "ficha-anterior")
    nueva = criatura(2, "Nueva", True, "ficha-nueva")
    ahora = object()
    eventos = []

    def cambiar(*args):
        eventos.append(("cambiar", *args))
        return economia.ResultadoCambio(ok=True, criatura=nueva, saliente=anterior)

    monkeypatch.setattr(equipo.economia, "cambiar_de_activo", cambiar)
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock(return_value=ahora))

    async def responder(**_):
        eventos.append("respuesta")

    async def congelar(canal, mensaje_id):
        eventos.append(("congelar", canal, mensaje_id))

    async def publicar(canal, criatura_nueva, instante):
        eventos.append(("publicar", canal, criatura_nueva, instante))

    menu = equipo.MenuPlantel([anterior, nueva], congelar, publicar)
    menu._values = [str(nueva.id)]
    canal = SimpleNamespace()
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=canal,
        response=SimpleNamespace(edit_message=responder),
    )

    asyncio.run(menu.callback(interaccion))

    assert eventos == [
        ("cambiar", "u1", "g1", nueva.id, ahora),
        ("congelar", canal, "ficha-anterior"),
        "respuesta",
        ("publicar", canal, nueva, ahora),
    ]


def test_cambiar_al_mismo_activo_no_congela_ni_publica(monkeypatch):
    anterior = criatura(1, "Anterior", True, "ficha-anterior")
    cambiar = Mock(return_value=economia.ResultadoCambio(
        motivo="ya_es_el_activo", criatura=anterior
    ))
    monkeypatch.setattr(equipo.economia, "cambiar_de_activo", cambiar)
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    congelar = AsyncMock()
    publicar = AsyncMock()
    menu = equipo.MenuPlantel([anterior], congelar, publicar=publicar)
    menu._values = [str(anterior.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(interaccion))

    interaccion.response.edit_message.assert_awaited_once_with(
        content="**Anterior** ya era el activo.", view=None
    )
    congelar.assert_not_awaited()
    publicar.assert_not_awaited()


def test_cambio_de_activo_invalido_no_congela_ni_publica(monkeypatch):
    anterior = criatura(1, "Anterior", True, "ficha-anterior")
    ajena = criatura(2, "Ajena", False, "ficha-ajena")
    monkeypatch.setattr(equipo.economia, "cambiar_de_activo", Mock(
        return_value=economia.ResultadoCambio(motivo="no_esta", criatura=anterior)
    ))
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    congelar = AsyncMock()
    publicar = AsyncMock()
    menu = equipo.MenuPlantel([anterior, ajena], congelar, publicar=publicar)
    menu._values = [str(ajena.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(interaccion))

    interaccion.response.edit_message.assert_awaited_once_with(
        content="Ese gachamon no es tuyo o ya no está.", view=None
    )
    congelar.assert_not_awaited()
    publicar.assert_not_awaited()


def test_el_menu_cambia_de_activo_sin_tocarle_el_reloj_a_nadie(
    bd_temporal, monkeypatch
):
    """De verdad, sin dobles: el menú pasa por la regla y no por `db.activar`."""
    cinco = T0 + timedelta(hours=5)
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock(return_value=cinco))
    anterior = db.crear("u1", "g1", SIN_RETRATO, "Anterior", STATS, T0)
    reserva = db.crear("u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, activa=False)
    menu = equipo.MenuPlantel([anterior, reserva], AsyncMock(), publicar=AsyncMock())
    menu._values = [str(reserva.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(interaccion))

    interaccion.response.edit_message.assert_awaited_once_with(
        content="🧬 Ahora sales con **Reserva**. Míralo con `/mascota`.",
        view=None,
    )
    # Nadie se duerme ni se despierta: a los dos les sigue corriendo el tiempo
    # desde donde estaba.
    for antes in (anterior, reserva):
        guardada = db.por_id(antes.id)
        assert guardada is not None and guardada.actualizada_en == T0
        assert guardada.hambre == antes.hambre
    activa = db.criatura_activa("u1", "g1")
    assert activa is not None and activa.id == reserva.id


@pytest.mark.parametrize(
    ("genero", "mira"), [(esp.MACHO, "Míralo"), (esp.HEMBRA, "Mírala")]
)
def test_al_cambiar_dice_con_quien_sales(monkeypatch, genero, mira):
    anterior = criatura(1, "Ana", True, "ficha-ana")
    nueva = replace(criatura(2, "Bea", True, None), genero=genero)
    monkeypatch.setattr(equipo.economia, "cambiar_de_activo", Mock(
        return_value=economia.ResultadoCambio(
            ok=True, criatura=nueva, saliente=replace(anterior, activa=False)
        )
    ))
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    menu = equipo.MenuPlantel([anterior, nueva], AsyncMock(), publicar=AsyncMock())
    menu._values = [str(nueva.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(interaccion))

    interaccion.response.edit_message.assert_awaited_once_with(
        content=f"🧬 Ahora sales con **Bea**. {mira} con `/mascota`.",
        view=None,
    )


def test_el_plantel_dice_quien_se_quedo_en_casa():
    activa = criatura(1, "Ana", True, "ficha-ana")
    otra = criatura(2, "Bea", False, None)

    texto = equipo.texto_del_plantel([activa, otra])
    menu = equipo.MenuPlantel([activa, otra])

    assert "en casa" in texto and pantalla.EMOJI_EN_CASA in texto
    assert texto.endswith(
        "\n-# A todos les pasa el tiempo, salgan contigo o no. "
        "Elige abajo con cuál sales."
    )
    assert "incubadora" not in texto
    assert "**Ana**" in texto and "**Bea**" in texto
    assert menu.placeholder == "¿Con cuál sales?"
    assert [o.label for o in menu.options] == ["Ana", "Bea"]
    assert [o.description.endswith("· en casa") for o in menu.options] == [False, True]


def test_pulsar_la_ficha_de_uno_que_se_quedo_en_casa_lo_explica(
    bd_temporal, monkeypatch
):
    db.crear("u1", "g1", SIN_RETRATO, "Ana", STATS, T0)
    otra = db.crear("u1", "g1", SIN_RETRATO, "Bea", STATS, T0, activa=False)
    db.guardar_pantalla(otra.id, "ficha", "canal")
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=T0))
    ejecutar_cuidado = Mock()
    monkeypatch.setattr(vistas.economia, "ejecutar_cuidado", ejecutar_cuidado)
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ALIMENTAR))

    respuesta.send_message.assert_awaited_once_with(
        "Ese gachamon se quedó en casa. "
        "Elígelo con `/plantel` para cuidarlo desde aquí.",
        ephemeral=True,
    )
    ejecutar_cuidado.assert_not_called()
    canal.send.assert_not_awaited()


# --- La ficha vive en su canal, no en el que se escribe ----------------------

def canal_falso(id_, guild=None):
    mensaje = SimpleNamespace(edit=AsyncMock())
    return SimpleNamespace(
        id=id_, guild=guild, mensaje=mensaje,
        fetch_message=AsyncMock(return_value=mensaje),
        send=AsyncMock(return_value=SimpleNamespace(id=999)),
    )


def guild_falso(canales=(), hilos=()):
    """Un servidor como el de discord.py: `get_channel` no mira en los hilos."""
    por_id = {canal.id: canal for canal in canales}
    con_hilos = por_id | {hilo.id: hilo for hilo in hilos}
    return SimpleNamespace(
        get_channel=lambda cid: por_id.get(str(cid)),
        get_channel_or_thread=lambda cid: con_hilos.get(str(cid)),
    )


def dos_canales(guardado_id, actual_id, en_hilo=False):
    """El canal donde quedó la ficha y aquel donde se abre el menú."""
    guardado = canal_falso(guardado_id)
    if en_hilo:
        guild = guild_falso(hilos=(guardado,))
    else:
        guild = guild_falso(canales=(guardado,))
    return guardado, canal_falso(actual_id, guild=guild)


def menu_de_plantel(plantel, elegido, canal):
    """El `/plantel` de verdad: el menú abierto en un canal cualquiera."""
    menu = equipo.MenuPlantel(
        plantel, vistas.congelar, publicar=vistas.publicar_pantalla
    )
    menu._values = [str(elegido.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=canal,
        response=SimpleNamespace(edit_message=AsyncMock()),
    )
    return menu, interaccion


def test_congelar_va_al_canal_guardado_de_la_ficha_y_no_al_de_la_orden(bd_temporal):
    """Los menús sólo saben desde dónde se les abrió; la ficha sabe dónde está."""
    mia = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.guardar_pantalla(mia.id, "555", "111")
    guardado, actual = dos_canales("111", "222")

    asyncio.run(vistas.congelar(actual, "555"))

    guardado.fetch_message.assert_awaited_once_with(555)
    actual.fetch_message.assert_not_awaited()
    assert guardado.mensaje.edit.await_args.kwargs["view"].children[0].disabled


def test_cambiar_de_activo_publica_ficha_canonica_en_el_canal_actual(
    bd_temporal, monkeypatch
):
    """La ficha vieja se congela donde estaba y la nueva nace donde se eligió."""
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock(return_value=T0))
    anterior = db.crear("u1", "g1", SIN_RETRATO, "Anterior", STATS, T0, canal_id="111")
    db.guardar_pantalla(anterior.id, "555", "111")
    reserva = db.crear("u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, activa=False)
    guardado, actual = dos_canales("111", "222")

    menu, interaccion = menu_de_plantel([anterior, reserva], reserva, actual)
    asyncio.run(menu.callback(interaccion))

    activa = db.criatura_activa("u1", "g1")
    assert activa is not None and activa.id == reserva.id
    esperado = pantalla.render(
        activa,
        T0,
        esperas=db.esperas_de_ficha(activa, T0, pantalla.ACCIONES_EN_FICHA),
        efectos=db.efectos_activos(activa.id, T0),
        en_casa=1,
        asciicoins=economia.saldos("u1", "g1").asciicoins,
    )
    actual.send.assert_awaited_once()
    assert actual.send.await_args.kwargs["content"] == esperado
    vista = actual.send.await_args.kwargs["view"]
    assert isinstance(vista, vistas.PantallaView)
    assert all(not boton.disabled for boton in vista.children)
    guardado.fetch_message.assert_awaited_once_with(555)
    actual.fetch_message.assert_not_awaited()
    assert guardado.mensaje.edit.await_args.kwargs["view"].children[0].disabled
    recargada = db.por_id(reserva.id)
    assert recargada is not None
    assert (recargada.pantalla_msg_id, recargada.canal_id) == ("999", "222")


def test_cambiar_activo_congela_la_ficha_vieja_de_la_que_regresa(
    bd_temporal, monkeypatch
):
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock(return_value=T0))
    anterior = db.crear("u1", "g1", SIN_RETRATO, "Anterior", STATS, T0, canal_id="111")
    db.guardar_pantalla(anterior.id, "555", "111")
    reserva = db.crear(
        "u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, canal_id="111", activa=False
    )
    db.guardar_pantalla(reserva.id, "777", "111")
    guardado, actual = dos_canales("111", "222")

    menu, interaccion = menu_de_plantel([anterior, reserva], reserva, actual)
    asyncio.run(menu.callback(interaccion))

    assert guardado.fetch_message.await_args_list == [call(555), call(777)]
    assert guardado.mensaje.edit.await_count == 2
    assert all(
        llamada.kwargs["view"].children[0].disabled
        for llamada in guardado.mensaje.edit.await_args_list
    )
    actual.send.assert_awaited_once()
    assert all(
        not boton.disabled for boton in actual.send.await_args.kwargs["view"].children
    )


def test_cambiar_de_activo_congela_en_hilo_y_publica_en_canal_actual(
    bd_temporal, monkeypatch
):
    """Un hilo es un canal más donde jugar, y `get_channel` no lo encuentra."""
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock(return_value=T0))
    anterior = db.crear("u1", "g1", SIN_RETRATO, "Anterior", STATS, T0, canal_id="111")
    db.guardar_pantalla(anterior.id, "555", "111")
    reserva = db.crear("u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, activa=False)
    hilo, actual = dos_canales("111", "222", en_hilo=True)

    menu, interaccion = menu_de_plantel([anterior, reserva], reserva, actual)
    asyncio.run(menu.callback(interaccion))

    hilo.fetch_message.assert_awaited_once_with(555)
    actual.fetch_message.assert_not_awaited()
    assert hilo.mensaje.edit.await_args.kwargs["view"].children[0].disabled
    actual.send.assert_awaited_once()
    recargada = db.por_id(reserva.id)
    assert recargada is not None and recargada.canal_id == "222"


def test_cambiar_de_activo_con_un_canal_guardado_ilegible_responde_igual(
    bd_temporal, monkeypatch
):
    """Una ficha vieja con un canal que no es un número no rompe el menú."""
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock(return_value=T0))
    anterior = db.crear("u1", "g1", SIN_RETRATO, "Anterior", STATS, T0)
    db.guardar_pantalla(anterior.id, "555", "canal-viejo")
    reserva = db.crear("u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, activa=False)
    _, actual = dos_canales("111", "222")

    menu, interaccion = menu_de_plantel([anterior, reserva], reserva, actual)
    asyncio.run(menu.callback(interaccion))

    actual.fetch_message.assert_awaited_once_with(555)
    interaccion.response.edit_message.assert_awaited_once()
    activa = db.criatura_activa("u1", "g1")
    assert activa is not None and activa.id == reserva.id


def test_si_el_canal_no_deja_publicar_el_cambio_sigue_hecho_y_acusado(
    bd_temporal, monkeypatch
):
    """Sin permiso para escribir queda el `/mascota` de la respuesta efímera."""
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock(return_value=T0))
    anterior = db.crear("u1", "g1", SIN_RETRATO, "Anterior", STATS, T0, canal_id="111")
    db.guardar_pantalla(anterior.id, "555", "111")
    reserva = db.crear("u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, activa=False)
    guardado, actual = dos_canales("111", "222")
    actual.send = AsyncMock(side_effect=discord.HTTPException(
        SimpleNamespace(status=403, reason="Forbidden"), "Missing Permissions"
    ))

    menu, interaccion = menu_de_plantel([anterior, reserva], reserva, actual)
    with pytest.raises(discord.HTTPException):
        asyncio.run(menu.callback(interaccion))

    # Lo que se guardó y lo que se contestó pasó antes de intentar publicar: el
    # cambio está hecho, la ficha vieja congelada y la persona ya sabe volver.
    activa = db.criatura_activa("u1", "g1")
    assert activa is not None and activa.id == reserva.id
    guardado.fetch_message.assert_awaited_once_with(555)
    contenido = interaccion.response.edit_message.await_args.kwargs["content"]
    assert "/mascota" in contenido


# --- Todos salen igual: no hay nadie sin nombre ------------------------------

def test_el_plantel_se_abre_sin_gancho_de_bautizo(bd_temporal):
    """`abrir_plantel` ya no recibe `bautizar`: elegir a cualquiera cambia de activo."""
    db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.crear("u1", "g1", "michi", "Lúa", STATS, T0, activa=False)
    interaccion, respuesta, _ = interaccion_de()

    asyncio.run(equipo.abrir_plantel(interaccion, vistas.congelar, vistas.publicar_pantalla))

    respuesta.send_message.assert_awaited_once()
    menu = respuesta.send_message.await_args.kwargs["view"].children[0]
    assert isinstance(menu, equipo.MenuPlantel)
    assert not hasattr(menu, "bautizar")


def test_elegir_a_un_recluta_que_se_puso_nombre_solo_cambia_de_activo(bd_temporal, monkeypatch):
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock(return_value=T0))
    activa = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    recluta = db.crear(
        "u1", "g1", "michi", "Brote", STATS, T0, activa=False, se_nombro_solo=True
    )
    publicar = AsyncMock()
    menu = equipo.MenuPlantel(db.plantel("u1", "g1"), AsyncMock(), publicar)
    menu._values = [str(recluta.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(interaccion))

    assert db.criatura_activa("u1", "g1").id == recluta.id
    assert db.por_id(activa.id).activa is False
    publicar.assert_awaited_once()


def test_el_juego_ya_no_tiene_sin_nombre():
    assert not hasattr(sim, "NOMBRE_PENDIENTE")
    assert not hasattr(sim, "SIN_NOMBRE")
    assert not hasattr(sim, "esta_sin_nombrar")
    assert not hasattr(sim, "nombre_visible")
    assert not hasattr(equipo, "NO_SALE_SIN_NOMBRE")
    assert not hasattr(vistas, "bautizar")


# --- El recluta que se puso nombre él solo ----------------------------------

def recluta_de(usuario="u1", semilla=4):
    return nacer.unir_recluta(
        usuario, "g1", especie="michi", stats=STATS, genero=esp.HEMBRA,
        caracter=esp.CARACTER_POR_DEFECTO, ahora=T0, rng=random.Random(semilla),
    )


def pulsar_el_boton_de(custom_id, interaccion):
    """Lo que hace discord.py al pulsarlo: casar el `custom_id` con la
    plantilla, construir el botón desde él y llamar a su `callback`."""
    casa = vistas.BotonNombrarRecluta.__discord_ui_compiled_template__.fullmatch(custom_id)
    assert casa is not None, custom_id
    boton = asyncio.run(vistas.BotonNombrarRecluta.from_custom_id(interaccion, Mock(), casa))
    asyncio.run(boton.callback(interaccion))


def test_el_boton_de_cada_recluta_abre_el_formulario_de_ese_recluta(bd_temporal):
    """El fallo de antes: bajo el mensaje de B, el formulario salía con el
    nombre de A, el más antiguo, y lo que se escribía renombraba a A."""
    db.crear("u1", "g1", "pulpo", "Activa", STATS, T0)
    a, b = recluta_de(semilla=4), recluta_de(semilla=5)
    assert a.se_nombro_solo and b.se_nombro_solo and a.nombre != b.nombre

    abiertos = {}
    for recluta in (b, a):
        interaccion, respuesta, _ = interaccion_de()
        respuesta.send_modal = AsyncMock()
        pulsar_el_boton_de(f"tama:nombrar_recluta:{recluta.id}", interaccion)
        abiertos[recluta.id] = respuesta.send_modal.await_args.args[0]

    for recluta in (a, b):
        modal = abiertos[recluta.id]
        assert isinstance(modal, vistas.NombreModal)
        assert (modal.criatura_id, modal.nombre.default) == (recluta.id, recluta.nombre)

    interaccion, respuesta, _ = interaccion_de()
    interaccion.user = SimpleNamespace(id="u1", mention="<@u1>")
    asyncio.run(vistas.NombreModal.on_submit(
        cast(Any, SimpleNamespace(nombre="Rayo", criatura_id=abiertos[b.id].criatura_id)),
        cast(Any, interaccion),
    ))

    assert db.por_id(b.id).nombre == "Rayo" and not db.por_id(b.id).se_nombro_solo
    assert db.por_id(a.id) == a
    respuesta.edit_message.assert_awaited_once_with(view=None)


@pytest.mark.parametrize("cual", ["renombrado", "muerto", "no_existe"])
def test_el_boton_de_un_recluta_que_ya_no_puede_cambiar_de_nombre_lo_dice(
    bd_temporal, cual
):
    db.crear("u1", "g1", "pulpo", "Activa", STATS, T0)
    recluta = recluta_de()
    criatura_id = recluta.id
    if cual == "renombrado":
        nacer.bautizar_a("u1", "g1", recluta.id, "Rayo", T0)
    elif cual == "muerto":
        db.guardar(replace(recluta, muerta_en=T0, causa_muerte="hambre"))
    else:
        criatura_id = 9999
    antes = db.por_id(recluta.id)
    interaccion, respuesta, _ = interaccion_de()
    respuesta.send_modal = AsyncMock()

    pulsar_el_boton_de(f"tama:nombrar_recluta:{criatura_id}", interaccion)

    respuesta.send_message.assert_awaited_once_with(
        "Ese gachamon ya tiene nombre.", ephemeral=True
    )
    respuesta.send_modal.assert_not_awaited()
    assert db.por_id(recluta.id) == antes


def test_el_boton_del_recluta_de_otro_no_abre_nada(bd_temporal):
    db.crear("u2", "g1", "pulpo", "Ajena", STATS, T0)
    ajeno = recluta_de(usuario="u2")
    interaccion, respuesta, _ = interaccion_de()      # pulsa u1
    respuesta.send_modal = AsyncMock()

    pulsar_el_boton_de(f"tama:nombrar_recluta:{ajeno.id}", interaccion)

    respuesta.send_message.assert_awaited_once_with(
        "Ese gachamon es de <@u2>.", ephemeral=True
    )
    respuesta.send_modal.assert_not_awaited()
    assert db.por_id(ajeno.id) == ajeno


def test_el_boton_del_recluta_pulsado_en_otro_servidor_no_abre_nada(bd_temporal):
    """Tuyo, pero de otro servidor: lo de cada servidor no se mezcla."""
    db.crear("u1", "g1", "pulpo", "Activa", STATS, T0)
    recluta = recluta_de()
    interaccion, respuesta, _ = interaccion_de()
    interaccion.guild_id = "g2"
    respuesta.send_modal = AsyncMock()

    pulsar_el_boton_de(f"tama:nombrar_recluta:{recluta.id}", interaccion)

    respuesta.send_modal.assert_not_awaited()
    respuesta.send_message.assert_awaited_once()
    assert respuesta.send_message.await_args.kwargs == {"ephemeral": True}
    assert db.por_id(recluta.id) == recluta


def test_el_mensaje_del_recluta_lleva_un_boton_con_su_id():
    vista = vistas.vista_del_recluta(42)
    assert vista.timeout is None
    assert [
        (type(b), b.item.label, str(b.item.emoji), b.item.style, b.custom_id)
        for b in vista.children
    ] == [(
        vistas.BotonNombrarRecluta, "Ponerle otro nombre", "✏️",
        discord.ButtonStyle.success, "tama:nombrar_recluta:42",
    )]
    plantilla = vistas.BotonNombrarRecluta.__discord_ui_compiled_template__
    # Los botones ya publicados siguen yendo a la vista vieja, no a éste.
    assert plantilla.fullmatch("tama:nombrar_recluta") is None
    assert plantilla.fullmatch("tama:nombrar_recluta:") is None
    assert plantilla.fullmatch("tama:nombrar_recluta:42")


def test_el_boton_ya_publicado_abre_el_formulario_del_mas_antiguo(bd_temporal):
    """Los mensajes de antes de que el botón llevara el id siguen con la vista
    vieja, que busca al más antiguo que se nombró solo."""
    db.crear("u1", "g1", "pulpo", "Activa", STATS, T0)
    recluta = recluta_de()
    vista = vistas.NombrarReclutaView()
    boton = vista.children[0]
    assert (boton.label, boton.custom_id) == ("Ponerle otro nombre", "tama:nombrar_recluta")

    interaccion, respuesta, _ = interaccion_de()
    respuesta.send_modal = AsyncMock()
    asyncio.run(vista.nombrar.callback(cast(Any, interaccion)))

    modal = respuesta.send_modal.await_args.args[0]
    assert isinstance(modal, vistas.NombreModal)
    assert modal.criatura_id == recluta.id
    assert modal.nombre.default == recluta.nombre

    nacer.bautizar_a("u1", "g1", recluta.id, "Rayo", T0)
    interaccion, respuesta, _ = interaccion_de()
    asyncio.run(vista.nombrar.callback(cast(Any, interaccion)))

    respuesta.send_message.assert_awaited_once_with(
        "Ninguno de tus gachamones espera un nombre nuevo.", ephemeral=True
    )


def test_todas_las_rutas_de_ficha_viva_piden_las_seis_esperas(monkeypatch):
    viva = criatura(1, "Mia", True, None)
    esperas = Mock(return_value={})
    estilo = Mock(return_value="imagen")
    monkeypatch.setattr(db, "esperas_de_ficha", esperas)
    monkeypatch.setattr(db, "estilo_de_ficha", estilo)
    monkeypatch.setattr(db, "efectos_activos", Mock(return_value={}))
    monkeypatch.setattr(db, "plantel", Mock(return_value=[viva]))
    monkeypatch.setattr(db, "guardar_pantalla", Mock())
    monkeypatch.setattr(
        economia, "saldos", Mock(return_value=economia.Saldos(34, 0))
    )
    monkeypatch.setattr(pantalla, "render", Mock(return_value="ficha"))

    interaccion, _, _ = interaccion_de()
    interaccion.channel_id = "canal"
    interaccion.original_response = AsyncMock(
        return_value=SimpleNamespace(id="respuesta")
    )
    asyncio.run(vistas.responder_pantalla(interaccion, viva, T0))
    esperas.assert_called_once_with(viva, T0, pantalla.ACCIONES_EN_FICHA)
    estilo.assert_called_once_with(viva.usuario_id, viva.guild_id)

    esperas.reset_mock()
    estilo.reset_mock()
    canal = SimpleNamespace(
        id="canal",
        send=AsyncMock(return_value=SimpleNamespace(id="publicada")),
    )
    asyncio.run(vistas.publicar_pantalla(cast(Any, canal), viva, T0))
    esperas.assert_called_once_with(viva, T0, pantalla.ACCIONES_EN_FICHA)
    estilo.assert_called_once_with(viva.usuario_id, viva.guild_id)

    esperas.reset_mock()
    estilo.reset_mock()
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=T0))
    monkeypatch.setattr(db, "criatura_por_pantalla", Mock(return_value=viva))
    monkeypatch.setattr(
        vistas.economia,
        "ejecutar_cuidado",
        Mock(return_value=SimpleNamespace(criatura=viva, replay=False)),
    )
    interaccion, _, _ = interaccion_de()
    asyncio.run(vistas._ejecutar(interaccion, sim.ACTUALIZAR))
    esperas.assert_called_once_with(viva, T0, pantalla.ACCIONES_EN_FICHA)
    estilo.assert_called_once_with(viva.usuario_id, viva.guild_id)


def test_responder_y_publicar_pasan_el_saldo_de_la_persona_y_servidor(monkeypatch):
    viva = replace(
        criatura(1, "Mia", True, None),
        usuario_id="persona-correcta",
        guild_id="servidor-correcto",
    )
    saldos = Mock(return_value=economia.Saldos(asciicoins=34, asciigems=0))
    esperas = {sim.AVENTURA: timedelta(minutes=36)}
    render = Mock(return_value="ficha")
    monkeypatch.setattr(economia, "saldos", saldos)
    monkeypatch.setattr(db, "esperas_de_ficha", Mock(return_value=esperas))
    monkeypatch.setattr(db, "efectos_activos", Mock(return_value={}))
    monkeypatch.setattr(db, "plantel", Mock(return_value=[viva]))
    monkeypatch.setattr(db, "guardar_pantalla", Mock())
    monkeypatch.setattr(pantalla, "render", render)

    interaccion, _, _ = interaccion_de()
    interaccion.channel_id = "canal"
    interaccion.original_response = AsyncMock(
        return_value=SimpleNamespace(id="respuesta")
    )
    asyncio.run(vistas.responder_pantalla(interaccion, viva, T0))

    saldos.assert_called_once_with("persona-correcta", "servidor-correcto")
    assert render.call_args.kwargs["esperas"] == esperas
    assert render.call_args.kwargs["asciicoins"] == 34

    saldos.reset_mock()
    render.reset_mock()
    canal = SimpleNamespace(
        id="canal",
        send=AsyncMock(return_value=SimpleNamespace(id="publicada")),
    )
    asyncio.run(vistas.publicar_pantalla(cast(Any, canal), viva, T0))

    saldos.assert_called_once_with("persona-correcta", "servidor-correcto")
    assert render.call_args.kwargs["esperas"] == esperas
    assert render.call_args.kwargs["asciicoins"] == 34


def test_responder_y_publicar_no_consultan_saldo_para_una_lapida(monkeypatch):
    lapida = replace(
        criatura(1, "Mia", False, None),
        nacida_en=T0,
        actualizada_en=T0,
        muerta_en=T0,
    )
    saldos = Mock(side_effect=AssertionError("una lápida no consulta saldo"))
    render = Mock(return_value="lápida")
    monkeypatch.setattr(economia, "saldos", saldos)
    monkeypatch.setattr(db, "esperas_de_ficha", Mock(return_value={}))
    monkeypatch.setattr(db, "efectos_activos", Mock(return_value={}))
    monkeypatch.setattr(db, "plantel", Mock(return_value=[]))
    monkeypatch.setattr(db, "guardar_pantalla", Mock())
    monkeypatch.setattr(pantalla, "render", render)

    interaccion, respuesta, _ = interaccion_de()
    interaccion.channel_id = "canal"
    interaccion.original_response = AsyncMock(
        return_value=SimpleNamespace(id="respuesta")
    )
    asyncio.run(vistas.responder_pantalla(interaccion, lapida, T0))

    canal = SimpleNamespace(
        id="canal",
        send=AsyncMock(return_value=SimpleNamespace(id="publicada")),
    )
    asyncio.run(vistas.publicar_pantalla(cast(Any, canal), lapida, T0))

    saldos.assert_not_called()
    respuesta.send_message.assert_awaited_once_with(content="lápida")
    canal.send.assert_awaited_once_with(content="lápida")
    assert [llamada.kwargs["asciicoins"] for llamada in render.call_args_list] == [
        None,
        None,
    ]


def test_la_ficha_de_una_muerta_de_antes_es_su_lapida_sin_botones(bd_temporal):
    """Los que ya murieron siguen muertos: responder o publicar la ficha de una
    que murió antes arma su lápida, y va sola, sin ninguna vista de botones."""
    nacida = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.guardar(replace(
        nacida, hambre=0.0, muerta_en=T0 + timedelta(days=2),
        causa_muerte="hambre",
    ))
    muerta = db.por_id(nacida.id)
    assert muerta is not None and not muerta.viva
    ahora = T0 + timedelta(days=9)
    lapida = pantalla.render_lapida(muerta, ahora)
    assert "🪦" in lapida and "murió de hambre" in lapida

    interaccion, respuesta, _ = interaccion_de()
    interaccion.channel_id = "canal"
    interaccion.original_response = AsyncMock(
        return_value=SimpleNamespace(id="respuesta")
    )
    asyncio.run(vistas.responder_pantalla(interaccion, muerta, ahora))
    canal = SimpleNamespace(
        id="canal",
        send=AsyncMock(return_value=SimpleNamespace(id="publicada")),
    )
    asyncio.run(vistas.publicar_pantalla(cast(Any, canal), muerta, ahora))

    respuesta.send_message.assert_awaited_once_with(content=lapida)
    canal.send.assert_awaited_once_with(content=lapida)


# Pulsar el panel viejo de una que murió antes no enseña la lápida, ni lo hacía:
# hace lo de siempre —cuida a la activa viva si la hay— y no rompe nada.

MURIO = T0 + timedelta(days=2)
PULSA = T0 + timedelta(days=9)


def muerta_de_antes_con_panel(*, con_reserva=False):
    """Como la dejaba la muerte de antes: la comida en 0, la marca puesta,
    activa en 1 y su panel («ficha») todavía en el canal. Con `con_reserva`
    deja además a una viva y con nombre en casa, y la devuelve."""
    nacida = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    reserva = (
        db.crear("u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, activa=False)
        if con_reserva else None
    )
    db.guardar_pantalla(nacida.id, "ficha", "canal")
    db.guardar(replace(
        db.obtener(nacida.id), hambre=0.0, muerta_en=MURIO, causa_muerte="hambre",
    ))
    muerta = db.obtener(nacida.id)
    assert muerta is not None and not muerta.viva and muerta.activa
    assert muerta.pantalla_msg_id == "ficha"
    return muerta, reserva


def con_relevo():
    """La muerta de antes y su relevo: la reserva que ya ascendió y es la activa,
    con la comida en 50 a la hora de pulsar."""
    muerta, reserva = muerta_de_antes_con_panel(con_reserva=True)
    db.guardar(replace(reserva, hambre=50.0, actualizada_en=PULSA))
    relevo = db.ascender_un_relevo("u1", "g1")
    assert relevo is not None and relevo.id == reserva.id
    return muerta, relevo


def test_alimentar_en_el_panel_de_una_muerta_de_antes_alimenta_al_relevo(
    bd_temporal, monkeypatch
):
    muerta, relevo = con_relevo()
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=PULSA))
    congelar = AsyncMock()
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "_congelar_pulsada", congelar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ALIMENTAR))

    alimentado = db.obtener(relevo.id)
    assert alimentado is not None and alimentado.hambre == 80.0
    # Apaga el panel pulsado y publica la ficha del relevo.
    congelar.assert_awaited_once_with(interaccion)
    publicar.assert_awaited_once()
    llamada = publicar.await_args
    assert llamada is not None
    assert llamada.args[0] is canal
    assert llamada.args[1] == alimentado
    assert llamada.kwargs["ya_congelada"] == "ficha"
    respuesta.send_message.assert_not_awaited()
    assert not any("🪦" in str(c.args) for c in canal.send.await_args_list)
    # La muerta no cambia.
    assert db.obtener(muerta.id) == muerta


def test_actualizar_en_el_panel_de_una_muerta_de_antes_dice_que_ya_no_esta_vigente(
    bd_temporal, monkeypatch
):
    muerta, relevo = con_relevo()
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=PULSA + timedelta(hours=3)))
    congelar = AsyncMock()
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "_congelar_pulsada", congelar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ACTUALIZAR))

    respuesta.send_message.assert_awaited_once_with(
        "Esta ficha ya no está vigente. Abre la actual con `/mascota`.",
        ephemeral=True,
    )
    respuesta.edit_message.assert_not_awaited()
    congelar.assert_not_awaited()
    publicar.assert_not_awaited()
    canal.send.assert_not_awaited()
    # Ni el relevo ni la muerta se tocan.
    assert db.obtener(relevo.id) == relevo
    assert db.obtener(muerta.id) == muerta


@pytest.mark.parametrize(
    "con_reserva", [False, True], ids=["sola", "reserva-sin-ascender"]
)
def test_sin_activa_viva_el_panel_de_una_muerta_de_antes_dice_que_no_tienes_ninguno(
    bd_temporal, monkeypatch, con_reserva
):
    """Con una reserva con nombre que todavía no ha ascendido es lo mismo que
    sin nadie: pulsar un panel no corre el remiendo, que sale al entrar a la
    web, romper el huevo, bautizar o cambiar de activo."""
    muerta, reserva = muerta_de_antes_con_panel(con_reserva=con_reserva)
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=PULSA))
    congelar = AsyncMock()
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "_congelar_pulsada", congelar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ALIMENTAR))

    respuesta.send_message.assert_awaited_once_with(
        "No tienes ningún gachamon vivo. Empieza con `/huevo`.", ephemeral=True
    )
    respuesta.edit_message.assert_not_awaited()
    congelar.assert_not_awaited()
    publicar.assert_not_awaited()
    canal.send.assert_not_awaited()
    assert db.criatura_activa("u1", "g1") is None
    assert db.obtener(muerta.id) == muerta
    if reserva is not None:
        assert db.obtener(reserva.id) == reserva


def test_tras_arrancar_mascota_ensena_al_que_salio_y_no_dice_que_no_tienes_ninguno(
    bd_temporal, monkeypatch
):
    """Quien tenía el activo muerto de antes y sólo reclutas que no salían: al
    arrancar, el primero se pone nombre y sale contigo, y `/mascota` lo enseña
    sin que nada pase antes por la web."""
    from cogs import mascota as cog_mascota

    muerta, _ = muerta_de_antes_con_panel()
    recluta = db.crear("u1", "g1", SIN_RETRATO, "Provisional", STATS, T0, activa=False)
    otro = db.crear("u1", "g1", SIN_RETRATO, "Bea", STATS, T0, activa=False)
    with db.conectar() as con:                           # como lo dejó el bot de antes
        con.execute("UPDATE criaturas SET nombre = '' WHERE id = ?", (recluta.id,))
    db.inicializar()
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=PULSA))
    interaccion, respuesta, _ = interaccion_de()
    interaccion.channel_id = "canal"
    interaccion.original_response = AsyncMock(
        return_value=SimpleNamespace(id="respuesta")
    )
    cog = cog_mascota.Mascota.__new__(cog_mascota.Mascota)

    asyncio.run(cast(Any, cog_mascota.Mascota.mascota.callback)(cog, interaccion, None))

    respuesta.send_message.assert_awaited_once()
    enviado = respuesta.send_message.await_args
    assert "No tienes ningún gachamon vivo" not in str(enviado)
    salio = db.por_id(recluta.id)
    assert salio.activa and salio.se_nombro_solo and salio.nombre
    assert salio.nombre in enviado.kwargs["content"]
    assert salio.pantalla_msg_id == "respuesta"
    assert not db.por_id(otro.id).activa and db.obtener(muerta.id) == muerta


def test_cuidar_con_la_comida_en_cero_publica_la_ficha_viva(
    bd_temporal, monkeypatch
):
    """Días en 0 ya no la matan al ponerla al día: el cuidado se publica en
    una ficha viva, no en una lápida."""
    criatura = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.guardar(replace(criatura, hambre=0.0))
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    monkeypatch.setattr(
        db, "ahora_utc", Mock(return_value=T0 + timedelta(days=3))
    )
    congelar = AsyncMock()
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "_congelar_pulsada", congelar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ALIMENTAR))

    congelar.assert_awaited_once_with(interaccion)
    publicada = publicar.await_args.args[1]
    assert publicada.viva and publicada.hambre == 30.0
    respuesta.send_message.assert_not_awaited()
    assert not any(
        "🪦" in llamada.args[0] for llamada in canal.send.await_args_list
    )


def test_actualizar_con_la_comida_en_cero_edita_la_ficha_viva_con_botones(
    bd_temporal, monkeypatch
):
    criatura = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.guardar(replace(criatura, hambre=0.0))
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    monkeypatch.setattr(
        db, "ahora_utc", Mock(return_value=T0 + timedelta(days=3))
    )
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ACTUALIZAR))

    respuesta.edit_message.assert_awaited_once()
    contenido = respuesta.edit_message.await_args.kwargs["content"]
    vista = respuesta.edit_message.await_args.kwargs["view"]
    assert "🪦" not in contenido
    assert "🪙 50 monedas" in contenido
    assert isinstance(vista, vistas.PantallaView)
    canal.send.assert_not_awaited()


def test_actualizar_edita_la_ficha_viva_con_estado_y_controles_actuales(
    bd_temporal, monkeypatch
):
    criatura = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.crear("u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, activa=False)
    economia.saldos("u1", "g1")
    with db.conectar() as con:
        con.execute(
            "UPDATE monederos SET asciicoins = 73 "
            "WHERE usuario_id = 'u1' AND guild_id = 'g1'"
        )
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    ahora = T0 + timedelta(hours=6)
    db.poner_cooldown(criatura.id, sim.JUGAR, ahora - timedelta(minutes=1))
    db.poner_cooldown_persona(
        "u1", "g1", sim.AVENTURA, ahora - timedelta(minutes=1)
    )
    db.poner_efecto(criatura.id, "fuerza", 3, ahora - timedelta(minutes=1))
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=ahora))
    congelar = AsyncMock()
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "_congelar_pulsada", congelar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ACTUALIZAR))

    guardada = db.obtener(criatura.id)
    assert guardada is not None
    contenido = respuesta.edit_message.await_args.kwargs["content"]
    vista = respuesta.edit_message.await_args.kwargs["view"]
    esperado = pantalla.render(
        guardada,
        ahora,
        esperas=db.esperas_de_ficha(
            guardada, ahora, pantalla.ACCIONES_EN_FICHA
        ),
        efectos=db.efectos_activos(guardada.id, ahora),
        en_casa=1,
        asciicoins=73,
    )
    respuesta.edit_message.assert_awaited_once()
    assert contenido == esperado
    assert contenido.count(
        "-# 🪙 73 monedas · 🎒 Mochila para gastarlas"
    ) == 1
    assert contenido != pantalla.render(criatura, ahora)
    assert guardada.actualizada_en == ahora and guardada.hambre < criatura.hambre
    assert pantalla.ICONOS_ACCION[sim.JUGAR] in contenido
    assert pantalla.ICONOS_ACCION[sim.AVENTURA] in contenido
    assert pantalla.EMOJI_POCION in contenido
    assert pantalla.EMOJI_EN_CASA in contenido
    assert isinstance(vista, vistas.PantallaView)
    assert all(not getattr(boton, "disabled") for boton in vista.children)
    congelar.assert_not_awaited()
    publicar.assert_not_awaited()
    canal.send.assert_not_awaited()


@pytest.mark.parametrize("caso", ["muerta-tras-ascenso", "sin-mapeo"])
def test_actualizar_ficha_obsoleta_no_muta_ni_edita(
    bd_temporal, monkeypatch, caso
):
    ahora = T0 + timedelta(days=10)
    if caso == "muerta-tras-ascenso":
        antigua = db.crear("u1", "g1", SIN_RETRATO, "Antigua", STATS, T0)
        reserva = db.crear(
            "u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, activa=False
        )
        db.guardar_pantalla(antigua.id, "ficha", "canal")
        db.guardar(replace(
            db.obtener(antigua.id), hambre=0.0, muerta_en=ahora, causa_muerte="hambre",
        ))
        ascendida = db.ascender_un_relevo("u1", "g1")
        assert ascendida is not None and ascendida.id == reserva.id

    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=ahora))
    ejecutar_cuidado = Mock(return_value=None)
    congelar = AsyncMock()
    publicar = AsyncMock()
    monkeypatch.setattr(vistas.economia, "ejecutar_cuidado", ejecutar_cuidado)
    monkeypatch.setattr(vistas, "_congelar_pulsada", congelar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ACTUALIZAR))

    ejecutar_cuidado.assert_not_called()
    respuesta.send_message.assert_awaited_once_with(
        "Esta ficha ya no está vigente. Abre la actual con `/mascota`.",
        ephemeral=True,
    )
    respuesta.edit_message.assert_not_awaited()
    congelar.assert_not_awaited()
    publicar.assert_not_awaited()
    canal.send.assert_not_awaited()


@pytest.mark.parametrize(
    ("caso", "accion", "estado", "recibo"),
    [
        (
            "alimentar",
            sim.ALIMENTAR,
            {"hambre": 50.0, "animo": 70.0},
            "-# 🍖 Alimentar · comida 80 · ánimo 70 · salud +1 entrenamiento · "
            "+1 XP · 🪙 +1 moneda · cuidado 1/12 UTC",
        ),
        (
            "empacho",
            sim.ALIMENTAR,
            {"hambre": 100.0, "animo": 5.0},
            "-# 🍖 Alimentar · comida 100 · ánimo 0 · +1 XP · "
            "🪙 +1 moneda · cuidado 1/12 UTC",
        ),
        (
            "jugar",
            sim.JUGAR,
            {"hambre": 80.0, "animo": 70.0},
            "-# 🪀 Jugar · ánimo 95 · velocidad +1 entrenamiento · +2 XP · "
            "coste base -5 comida · 🪙 +1 moneda · cuidado 1/12 UTC",
        ),
        (
            "entrenar",
            sim.ENTRENAR,
            {"hambre": 80.0, "animo": 70.0},
            "-# 🏋️ Entrenar fuerza · fuerza +2 entrenamiento · +3 XP · "
            "coste base -15 comida · coste base -10 ánimo · "
            "🪙 +1 moneda · cuidado 1/12 UTC",
        ),
        (
            "limpiar",
            sim.LIMPIAR,
            {"limpieza": 25.0},
            "-# 🧼 Limpiar · aseo 100 · +0 XP · "
            "🪙 +1 moneda · cuidado 1/12 UTC",
        ),
    ],
)
def test_cuidado_publica_resultado_real_y_recibo_unificado(
    bd_temporal, monkeypatch, caso, accion, estado, recibo
):
    criatura = replace(
        db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0), **estado
    )
    db.guardar(criatura)
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=T0))
    monkeypatch.setattr(vistas, "_congelar_pulsada", AsyncMock())
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)

    if caso == "empacho":
        ejecutar_cuidado = economia.ejecutar_cuidado

        def ejecutar_con_otra_narrativa(*args):
            resultado = ejecutar_cuidado(*args)
            assert resultado is not None
            return replace(
                resultado, mensaje="Narrativa sustituida sin palabra clave."
            )

        monkeypatch.setattr(
            vistas.economia, "ejecutar_cuidado", ejecutar_con_otra_narrativa
        )

    interaccion, _, _ = interaccion_de()
    asyncio.run(vistas._ejecutar(interaccion, accion))

    llamada = publicar.await_args
    assert llamada is not None
    aviso = llamada.kwargs["aviso"]
    assert aviso.splitlines()[-1] == recibo
    if caso == "empacho":
        assert aviso.startswith("Narrativa sustituida sin palabra clave.\n")
        assert "salud +1" not in aviso


def test_cuidado_sin_efecto_responde_en_privado_sin_congelar_ni_publicar(
    bd_temporal, monkeypatch
):
    """Limpiar a quien ya está limpia no genera ficha: sólo el aviso privado."""
    criatura = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=T0))
    congelar = AsyncMock()
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "_congelar_pulsada", congelar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.LIMPIAR))

    # El texto esperado sale del dominio, no de una copia literal aquí: el
    # estado no cambió, así que repetir la acción devuelve el mismo resultado.
    dominio = economia.ejecutar_cuidado("otro", "u1", "g1", sim.LIMPIAR, T0)
    assert dominio is not None and dominio.sin_efecto
    respuesta.send_message.assert_awaited_once_with(
        dominio.mensaje + "\n-# Sus vetas permanecen quietas.", ephemeral=True
    )
    respuesta.edit_message.assert_not_awaited()
    congelar.assert_not_awaited()
    publicar.assert_not_awaited()
    canal.send.assert_not_awaited()


def test_cuidado_con_tension_no_dice_que_no_deja_marca(
    bd_temporal, monkeypatch
):
    criatura = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.guardar(replace(criatura, hambre=40.0))
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=T0))
    monkeypatch.setattr(vistas, "_congelar_pulsada", AsyncMock())
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, _, _ = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ENTRENAR))

    llamada = publicar.await_args
    assert llamada is not None
    aviso = llamada.kwargs["aviso"]
    assert "Algo se pone en movimiento bajo sus vetas." in aviso
    assert "permanecen quietas" not in aviso


def test_el_eco_de_vetas_no_declara_quietud_si_cambio_ingenio():
    """La marca sale de comparar las tensiones **enumeradas** del dominio.

    Un esfuerzo que sólo toca el ingenio —lo único que emite el laberinto—
    tiene que contar como movimiento. Con una enumeración de tres canales la
    criatura se movería y las dos superficies dirían que está quieta.
    """
    antes = criatura(1, "Mia", True, "ficha")
    despues, rupturas = sim.aplicar_evento(
        antes, (sim.Esfuerzo("ingenio", 3.0, causa=sim.COMPETIR),), 0
    )
    marca = bool(rupturas or sim._tensiones(despues) != sim._tensiones(antes))
    assert despues.ten_ingenio > antes.ten_ingenio
    assert marca, "mover sólo el ingenio ya es mover las vetas"

    eco = vistas._eco_vetas_cuidado(economia.ResultadoCuidado(
        criatura=despues, mensaje="", rupturas=rupturas, marca=marca,
    ))
    assert eco == "-# Algo se pone en movimiento bajo sus vetas."
    assert "permanecen quietas" not in eco

    resumen = vistas._resumen_participante(sim.ResultadoAccion(
        criatura=despues, mensaje="", rupturas=rupturas, marca=marca,
    ))
    assert "vetas quietas" not in resumen


def test_cuidado_con_ruptura_deja_el_eco_al_anuncio_existente(
    bd_temporal, monkeypatch
):
    criatura = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.guardar(replace(
        criatura, hambre=40.0,
        ten_fuerza=19.0, ten_velocidad=19.0, ten_salud=19.0,
    ))
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=T0))
    monkeypatch.setattr(vistas, "_congelar_pulsada", AsyncMock())
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, _, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ENTRENAR))

    # La ruptura primero y la medalla de la alfa después, cada una en su
    # mensaje: el eco de las vetas no se mezcla con el anuncio del logro.
    mandados = [llamada.args[0] for llamada in canal.send.await_args_list]
    assert len(mandados) == 2
    assert "🪵" in mandados[0]
    assert "De la alfa" in mandados[1]
    llamada = publicar.await_args
    assert llamada is not None
    aviso = llamada.kwargs["aviso"]
    assert "movimiento bajo sus vetas" not in aviso
    assert "permanecen quietas" not in aviso


def test_cuidado_normal_congela_publica_y_replay_responde_privado(
    bd_temporal, monkeypatch
):
    criatura = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    ahora = T0 + timedelta(hours=6)
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=ahora))
    congelar = AsyncMock()
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "_congelar_pulsada", congelar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ALIMENTAR))

    congelar.assert_awaited_once_with(interaccion)
    publicar.assert_awaited_once()
    llamada = publicar.await_args
    assert llamada is not None
    assert llamada.args[0] is canal
    assert llamada.args[1].id == criatura.id
    assert llamada.args[2] == ahora
    assert "Sus vetas permanecen quietas." in llamada.kwargs["aviso"]
    respuesta.edit_message.assert_not_awaited()
    respuesta.send_message.assert_not_awaited()
    # Lo único que se manda al canal aparte de la ficha es la medalla que se
    # lleva por haber nacido durante la alfa, y sale una sola vez.
    canal.send.assert_awaited_once()
    assert "De la alfa" in canal.send.await_args.args[0]

    asyncio.run(vistas._ejecutar(interaccion, sim.ALIMENTAR))

    congelar.assert_awaited_once()
    publicar.assert_awaited_once()
    respuesta.send_message.assert_awaited_once_with(
        "Esta interacción ya estaba procesada.", ephemeral=True
    )


def test_el_menu_del_plantel_aguanta_el_plantel_lleno():
    """Lo único que podía romperse al subir el tope es la cantidad: Discord no
    admite más de 25 opciones en un desplegable ni 2000 caracteres de mensaje,
    y la lista lleva una línea por gachamon."""
    lleno = [
        criatura(i, f"Gachamon {i}", i == 1, f"ficha-{i}")
        for i in range(1, db.MAXIMO_PLANTEL + 1)
    ]

    menu = equipo.MenuPlantel(lleno)
    texto = equipo.texto_del_plantel(lleno)

    # El 25 es el tope de opciones de un desplegable de Discord, y desde que
    # el plantel llegó a 25 este menú va **justo**, sin un hueco de margen:
    # subir `MAXIMO_PLANTEL` obliga antes a paginarlo. Va con literal para que
    # cambiar la constante no mueva también la portería.
    assert len(menu.options) == db.MAXIMO_PLANTEL
    assert db.MAXIMO_PLANTEL <= 25
    assert all(1 <= len(o.label) <= 100 for o in menu.options)
    assert all(len(o.description) <= 100 for o in menu.options)
    assert len(texto) < 2000, len(texto)
    # Y sale uno por gachamon, no uno de menos.
    assert texto.count("Gachamon ") == db.MAXIMO_PLANTEL
