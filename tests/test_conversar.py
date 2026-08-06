"""Hablarle bien al gachamon le entrena el ingenio.

Es la única vía que tiene la cuarta estadística fuera del laberinto, y la única
mecánica del juego cuyo árbitro es un modelo de fuera. Ni un solo test toca la
red: donde hace falta un veredicto se inyecta el transporte, como en
`test_ia.py`.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

import db
import economia
import ia
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "conversar.db")
    db.inicializar()


def nacer(animo=50.0):
    criatura = db.crear("u1", "g1", "pulpo", "Kuro", STATS, T0)
    from dataclasses import replace
    criatura = replace(criatura, animo=animo)
    db.guardar(criatura)
    return criatura


def correr(corrutina):
    return asyncio.run(corrutina)


CULTO = (
    "Me pregunto si mañana habrá suficiente claridad en el cielo para "
    "distinguir las estrellas desde el jardín."
)


# --- Cuándo merece la pena preguntarle al modelo ----------------------------

def test_un_mensaje_corto_no_se_manda_a_juzgar():
    """Preguntar cuesta una llamada, y en cuatro palabras no cabe nada que
    premiar. No mide el estilo: de eso ya se encarga el modelo."""
    assert not sim.merece_juicio("hola qué tal estás", [])
    assert sim.merece_juicio(CULTO, [])


def test_el_minimo_de_palabras_esta_clavado():
    """Con un literal y no leyendo la constante: deducirlo de ella movería la
    portería al cambiarla, que es el error circular de siempre."""
    assert sim.PALABRAS_MINIMAS_PARA_APRENDER == 8
    justas = " ".join(["palabra"] * 8)
    assert sim.merece_juicio(justas, [])
    assert not sim.merece_juicio(" ".join(["palabra"] * 7), [])


def test_repetir_lo_que_ya_dijo_no_se_juzga():
    """El agujero que deja juzgar por IA en vez de por reglas: pegar el mismo
    párrafo bonito cada vez que vence el enfriamiento."""
    historial = [
        {"role": "user", "content": CULTO},
        {"role": "assistant", "content": "Qué cosas dices."},
    ]

    assert not sim.merece_juicio(CULTO, historial)
    # Ni con otro espaciado o en mayúsculas: sigue siendo el mismo mensaje.
    assert not sim.merece_juicio(f"  {CULTO.upper()}  ", historial)
    assert sim.merece_juicio(CULTO + " Y también la luna.", historial)


def test_lo_que_contesto_la_criatura_no_cuenta_como_repetido():
    """Sólo se compara con lo que escribió la persona. Si contara lo del
    modelo, bastaría con que el bot te citara para dejarte sin premio."""
    historial = [{"role": "assistant", "content": CULTO}]
    assert sim.merece_juicio(CULTO, historial)


# --- El premio --------------------------------------------------------------

def test_una_buena_conversacion_entrena_el_ingenio_y_anima():
    antes = nacer(animo=50.0)

    premio = economia.aprender_hablando("u1", "g1", T0)

    assert premio.ok
    assert premio.entrenamiento_ganado == 1
    assert premio.animo_ganado == sim.EFECTO_CONVERSACION["animo"]
    despues = db.criatura_activa("u1", "g1")
    assert despues.ent_ingenio == antes.ent_ingenio + 1
    assert despues.animo == antes.animo + sim.EFECTO_CONVERSACION["animo"]
    # Conversar no es esfuerzo físico: no cuesta comida.
    assert despues.hambre == antes.hambre


def test_es_la_unica_via_del_ingenio_fuera_del_laberinto():
    """Lo que motivó el cambio: `ent_ingenio` existía en el esquema y nada lo
    tocaba nunca, así que quien no compitiera en laberintos no veía subir la
    cuarta estadística jamás."""
    for accion, campo in (
        (sim.ALIMENTAR, "ent_salud"),
        (sim.JUGAR, "ent_velocidad"),
        (sim.ENTRENAR, "ent_fuerza"),
    ):
        assert sim.EFECTOS_CUIDADO[accion].get(campo), accion
        assert "ent_ingenio" not in sim.EFECTOS_CUIDADO[accion], accion
    assert sim.EFECTO_CONVERSACION["ent_ingenio"] == 1


def test_no_se_aprende_dos_veces_seguidas():
    nacer()
    criatura = db.criatura_activa("u1", "g1")

    primera = economia.aprender_hablando("u1", "g1", T0)
    segunda = economia.aprender_hablando("u1", "g1", T0 + timedelta(minutes=5))

    assert primera.ok and not segunda.ok
    assert db.criatura_activa("u1", "g1").ent_ingenio == criatura.ent_ingenio + 1


def test_pasado_el_enfriamiento_se_vuelve_a_aprender():
    nacer()
    espera = sim.COOLDOWNS[sim.CONVERSAR]

    economia.aprender_hablando("u1", "g1", T0)
    justo_antes = economia.aprender_hablando("u1", "g1", T0 + espera - timedelta(minutes=1))
    justo_despues = economia.aprender_hablando("u1", "g1", T0 + espera)

    assert not justo_antes.ok and justo_despues.ok
    assert db.criatura_activa("u1", "g1").ent_ingenio == 2


def test_el_enfriamiento_esta_clavado_y_no_choca_con_ninguno():
    """97 minutos, con literal. Y primo, que es lo que hace que sus ciclos no
    coincidan para siempre con los de otra acción."""
    assert sim.COOLDOWNS[sim.CONVERSAR] == timedelta(minutes=97)
    minutos = {
        accion: int(espera.total_seconds() // 60)
        for accion, espera in sim.COOLDOWNS.items()
        if espera.total_seconds()
    }
    for accion, otros in minutos.items():
        if accion == sim.CONVERSAR:
            continue
        assert 97 % otros and otros % 97, accion


def test_conversar_no_es_una_accion_de_cuidado():
    """No tiene botón en la ficha ni da experiencia: se conversa hablando."""
    assert sim.CONVERSAR not in sim.ACCIONES_DE_CUIDADO
    assert sim.XP_POR_CUIDADO.get(sim.CONVERSAR, 0) == 0


def test_el_permiso_se_vuelve_a_comprobar_al_aplicar():
    """`puede_aprender_hablando` se consulta ANTES de hablar con la IA, así que
    entre esa consulta y el premio pasa una llamada de red entera: dos mensajes
    seguidos pueden llegar aquí con el mismo permiso en la mano."""
    criatura = nacer()

    assert economia.puede_aprender_hablando(criatura.id, T0)
    economia.aprender_hablando("u1", "g1", T0)
    # El permiso viejo sigue en la mano, pero ya no vale.
    assert not economia.puede_aprender_hablando(criatura.id, T0)
    assert not economia.aprender_hablando("u1", "g1", T0).ok


def test_sin_criatura_no_se_aprende():
    assert not economia.aprender_hablando("u1", "g1", T0).ok


def test_una_criatura_que_ha_muerto_de_hambre_no_cobra():
    """Se avanza en el tiempo ANTES de premiar, igual que en `cuidar`: la fila
    sólo se marca muerta al avanzarla, así que sin esto una criatura que lleva
    días sin comer cobraría la conversación en vez de morirse."""
    criatura = nacer()
    tarde = T0 + timedelta(hours=sim.horas_de_vida(criatura.salud) + 24)

    premio = economia.aprender_hablando("u1", "g1", tarde)

    assert not premio.ok
    assert premio.criatura is not None and not premio.criatura.viva
    # Y no se le ha puesto el enfriamiento a un cadáver.
    assert premio.entrenamiento_ganado == 0


def test_el_animo_no_se_pasa_de_cien():
    nacer(animo=98.0)

    premio = economia.aprender_hablando("u1", "g1", T0)

    assert premio.ok
    assert db.criatura_activa("u1", "g1").animo == 100.0
    # Y el ingenio se entrena igual aunque el ánimo ya estuviera lleno.
    assert premio.entrenamiento_ganado == 1


def test_la_estadistica_se_mueve_a_su_ritmo_y_el_mensaje_no_miente():
    """`stat_final` le saca la raíz al entrenamiento, así que la mayoría de las
    conversaciones suben el entrenamiento sin mover el ingenio. El resultado
    lleva los dos números para que el aviso pueda decir la verdad."""
    nacer()
    ahora = T0
    subidas = 0
    for vuelta in range(9):
        premio = economia.aprender_hablando("u1", "g1", ahora)
        assert premio.ok and premio.entrenamiento_ganado == 1
        subidas += premio.ingenio_ganado
        ahora += sim.COOLDOWNS[sim.CONVERSAR]

    # Nueve conversaciones son isqrt(9) = 3 puntos de ingenio, no nueve.
    assert subidas == 3
    assert db.criatura_activa("u1", "g1").ent_ingenio == 9


# --- El juez, visto desde el juego ------------------------------------------

def test_si_el_juez_dice_que_no_no_se_gasta_el_enfriamiento():
    """Rechazar no puede costarte la oportunidad: el enfriamiento sólo se pone
    cuando se ha aprendido algo."""
    from tests.test_ia import respuesta_de

    criatura = nacer()
    assert not correr(ia.juzgar_elocuencia("da igual", transporte=respuesta_de("NO")))
    # Quien llama no aplica nada, así que el permiso sigue en pie.
    assert economia.puede_aprender_hablando(criatura.id, T0)


def test_si_la_ia_se_cae_tampoco_se_gasta_el_enfriamiento():
    from tests.test_ia import transporte_roto

    criatura = nacer()
    assert not correr(ia.juzgar_elocuencia(CULTO, transporte=transporte_roto))
    assert economia.puede_aprender_hablando(criatura.id, T0)


# --- El orden en el cog: de lo barato a lo caro -----------------------------
#
# Es lo que hace viable juzgar con IA: la llamada extra ocurre como mucho una
# vez por enfriamiento, no una por mensaje. Si el orden se invirtiera, la charla
# pasaría de 20 llamadas por hora a 40 sin que nadie lo notara hasta la factura.

@pytest.fixture
def cog_con_juez(monkeypatch):
    """La charla, con un juez de mentira que apunta si le preguntan."""
    import cogs.charla as charla

    preguntas = []

    def juez(veredicto):
        async def juzgar(mensaje, transporte=None):
            preguntas.append(mensaje)
            return veredicto
        return juzgar

    def montar(veredicto=True):
        monkeypatch.setattr(charla.ia, "juzgar_elocuencia", juez(veredicto))
        return charla.Charla(bot=None), preguntas

    return montar


def test_no_se_le_pregunta_al_modelo_por_un_mensaje_corto(cog_con_juez):
    cog, preguntas = cog_con_juez()
    criatura = nacer()

    premio = correr(cog._premio_por_hablar_bien(criatura, "hola", [], T0))

    assert premio == "" and preguntas == []


def test_no_se_le_pregunta_al_modelo_si_el_enfriamiento_no_ha_vencido(cog_con_juez):
    """La razón de ser del diseño: se mira el enfriamiento —una lectura de
    SQLite— antes de gastar una llamada de red."""
    cog, preguntas = cog_con_juez()
    criatura = nacer()
    economia.aprender_hablando("u1", "g1", T0)      # deja el enfriamiento puesto

    premio = correr(cog._premio_por_hablar_bien(criatura, CULTO, [], T0))

    assert premio == "" and preguntas == []


def test_no_se_le_pregunta_al_modelo_por_algo_ya_dicho(cog_con_juez):
    cog, preguntas = cog_con_juez()
    criatura = nacer()
    historial = [{"role": "user", "content": CULTO}]

    premio = correr(cog._premio_por_hablar_bien(criatura, CULTO, historial, T0))

    assert premio == "" and preguntas == []


def test_si_el_juez_rechaza_no_hay_aviso_ni_premio(cog_con_juez):
    cog, preguntas = cog_con_juez(veredicto=False)
    criatura = nacer()

    premio = correr(cog._premio_por_hablar_bien(criatura, CULTO, [], T0))

    assert premio == ""
    assert preguntas == [CULTO]                      # sí se preguntó
    assert economia.puede_aprender_hablando(criatura.id, T0)   # y no costó nada


def test_una_conversacion_premiada_se_anuncia_al_pie(cog_con_juez):
    cog, preguntas = cog_con_juez(veredicto=True)
    criatura = nacer()

    premio = correr(cog._premio_por_hablar_bien(criatura, CULTO, [], T0))

    assert preguntas == [CULTO]
    assert premio.startswith("\n-# ")
    assert "ingenio" in premio.lower()
    assert f"+{sim.EFECTO_CONVERSACION['animo']}" in premio
    assert db.criatura_activa("u1", "g1").ent_ingenio == criatura.ent_ingenio + 1


def test_el_aviso_no_promete_ingenio_que_no_ha_subido(cog_con_juez):
    """La primera conversación sí mueve la estadística —isqrt(1) = 1—; la
    segunda no. El aviso tiene que cambiar de frase, no mentir."""
    cog, _ = cog_con_juez(veredicto=True)
    criatura = nacer()

    primero = correr(cog._premio_por_hablar_bien(criatura, CULTO, [], T0))
    luego = db.criatura_activa("u1", "g1")
    segundo = correr(cog._premio_por_hablar_bien(
        luego, CULTO + " Y la luna.", [], T0 + sim.COOLDOWNS[sim.CONVERSAR]
    ))

    assert "Ingenio **+1**" in primero
    assert "Ingenio **+" not in segundo
    assert "Entrenamiento de ingenio **+1**" in segundo
