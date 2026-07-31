"""La aventura: biomas, pruebas, qué te encuentras y convencer a un salvaje."""
import asyncio
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import aventura as av
import cogs.aventura as cog_av
import especies as esp
import objetos as obj
import pantalla
import personalidad as per
import simulacion as sim

ANCHO_NOMBRE = 24  # el tope de `sim.LARGO_MAXIMO_NOMBRE`


class DadosFijos(random.Random):
    """Dados guionizados: se recorren en orden y se repiten en bucle."""

    def __init__(self, valores):
        super().__init__()
        self.valores = list(valores)
        self.i = 0

    def randint(self, a, b):
        valor = self.valores[self.i % len(self.valores)]
        self.i += 1
        return min(max(valor, a), b)


def criatura(fuerza=15, velocidad=15, nombre="Juan III", **cambios):
    base = dict(
        id=1, usuario_id="u1", guild_id="g1", especie="pulpo", nombre=nombre,
        nacida_en=None, actualizada_en=None,
        base_fuerza=fuerza, base_velocidad=velocidad, base_salud=15,
        hambre=80.0, animo=80.0,
    )
    base.update(cambios)
    return sim.Criatura(**base)


# --- Los biomas ------------------------------------------------------------

def test_hay_cinco_biomas_y_cada_uno_tiene_lo_suyo():
    assert len(av.BIOMAS) == 5
    for clave, bioma in av.BIOMAS.items():
        assert bioma.clave == clave
        assert bioma.nombre.strip() and bioma.emoji.strip()
        assert bioma.especies, clave
        assert bioma.dificultad > 0


def test_cada_bioma_solo_cria_lo_suyo():
    """Nadie se encuentra un Dragoncito en la planicie."""
    for clave, bioma in av.BIOMAS.items():
        for especie in bioma.especies:
            assert especie in esp.ESPECIES, (clave, especie)

    assert "dragoncito" not in av.BIOMAS["planicie"].especies
    assert "dragoncito" in av.BIOMAS["volcan"].especies


def test_la_dificultad_sale_del_bioma():
    """El volcán apreta más que la planicie: es lo que distingue un bioma."""
    assert av.BIOMAS["volcan"].dificultad > av.BIOMAS["planicie"].dificultad


def test_el_bioma_se_sortea_y_salen_todos():
    rng = random.Random(1)
    vistos = {av.elegir_bioma(rng).clave for _ in range(500)}
    assert vistos == set(av.BIOMAS)


# --- Las pruebas -----------------------------------------------------------

def test_son_dos_pruebas_de_stat_mas_1d20():
    salida = av.explorar(criatura(), av.BIOMAS["bosque"], DadosFijos([20]))

    assert len(salida.pruebas) == 2
    for prueba in salida.pruebas:
        assert prueba.stat in ("fuerza", "velocidad")
        assert prueba.total == prueba.base + prueba.dado
        assert prueba.dificultad == av.BIOMAS["bosque"].dificultad
        assert prueba.superada == (prueba.total >= prueba.dificultad)


def test_cada_prueba_sortea_su_estadistica():
    """Totalmente al azar: tienen que salir las TRES combinaciones. Si sólo
    saliera la mixta, el sorteo no sería tal."""
    rng = random.Random(7)
    vistas = Counter()
    for _ in range(400):
        salida = av.explorar(criatura(), av.BIOMAS["bosque"], rng)
        vistas[tuple(p.stat for p in salida.pruebas)] += 1

    assert ("fuerza", "fuerza") in vistas
    assert ("velocidad", "velocidad") in vistas
    assert {("fuerza", "velocidad"), ("velocidad", "fuerza")} & set(vistas)


def test_la_prueba_usa_la_estadistica_que_toca():
    """Un gachamon rapidísimo y flojo tiene que notar cuál le ha tocado."""
    rapido = criatura(fuerza=1, velocidad=99)
    for _ in range(50):
        salida = av.explorar(rapido, av.BIOMAS["bosque"], random.Random())
        for prueba in salida.pruebas:
            esperado = 99 if prueba.stat == "velocidad" else 1
            assert prueba.base == esperado, prueba


def test_fallar_cuesta_hambre_extra():
    facil = av.BIOMAS["planicie"]
    fuerte = criatura(fuerza=99, velocidad=99)
    debil = criatura(fuerza=1, velocidad=1)

    entera = av.explorar(fuerte, facil, DadosFijos([20]))
    reventada = av.explorar(debil, facil, DadosFijos([1]))

    assert entera.superadas == 2 and reventada.superadas == 0
    assert reventada.coste_hambre > entera.coste_hambre


def salida_con_fallos(cuantos: int) -> av.Salida:
    pruebas = tuple(
        av.Prueba(
            obstaculo=f"tramo {i}", stat="fuerza", base=10,
            dado=10 if i >= cuantos else 1, dificultad=20,
        )
        for i in range(av.PRUEBAS_POR_AVENTURA)
    )
    return av.Salida(pruebas)


def test_sin_pruebas_fallidas_nunca_hay_percance():
    assert av.tirar_percance(salida_con_fallos(0), DadosFijos([1])) is None


def test_dos_fallos_tienen_mas_probabilidad_de_percance_que_uno():
    """40 queda fuera del 25 % de un fallo y dentro del 50 % de dos."""
    assert av.tirar_percance(salida_con_fallos(1), DadosFijos([40])) is None
    assert av.tirar_percance(salida_con_fallos(2), DadosFijos([40])) == av.PERCANCE


def test_los_umbrales_del_percance_son_inclusivos():
    assert av.tirar_percance(salida_con_fallos(1), DadosFijos([25])) == av.PERCANCE
    assert av.tirar_percance(salida_con_fallos(1), DadosFijos([26])) is None
    assert av.tirar_percance(salida_con_fallos(2), DadosFijos([50])) == av.PERCANCE
    assert av.tirar_percance(salida_con_fallos(2), DadosFijos([51])) is None


def test_el_desgaste_aplica_la_penalizacion_solo_si_hay_percance():
    salida = salida_con_fallos(1)
    ahora = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    normal = av.aplicar_desgaste(criatura(), salida, ahora)
    accidentada = av.aplicar_desgaste(criatura(), salida, ahora, av.PERCANCE)

    assert (normal.hambre, normal.animo) == (60.0, 75.0)
    assert (accidentada.hambre, accidentada.animo) == (55.0, 70.0)


def test_el_desgaste_que_agota_el_hambre_mata_en_ese_instante():
    ahora = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    gastada = av.aplicar_desgaste(
        criatura(hambre=2.0, animo=3.0), salida_con_fallos(2), ahora, av.PERCANCE
    )
    assert (gastada.hambre, gastada.animo) == (0.0, 0.0)
    assert gastada.muerta_en == ahora
    assert gastada.causa_muerte == "hambre"
    assert not gastada.viva


def test_el_viaje_sobrevivido_siempre_da_cuatro_xp_sin_cambiar_el_desgaste():
    ahora = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)

    for fallos in range(av.PRUEBAS_POR_AVENTURA + 1):
        for percance in (None, av.PERCANCE):
            viajera = criatura(xp=7)
            salida = salida_con_fallos(fallos)
            solo_desgaste = av.aplicar_desgaste(viajera, salida, ahora, percance)

            despues, subidas = av.aplicar_viaje(
                viajera, salida, ahora, percance, random.Random(0)
            )

            assert despues.xp == 11, (fallos, percance)
            assert (despues.hambre, despues.animo) == (
                solo_desgaste.hambre, solo_desgaste.animo
            )
            assert subidas == []

    assert sim.XP_VICTORIA > sim.XP_AVENTURA


def test_el_viaje_fatal_no_da_xp():
    ahora = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    viajera = criatura(hambre=2.0, xp=20)

    despues, subidas = av.aplicar_viaje(
        viajera, salida_con_fallos(2), ahora, av.PERCANCE, random.Random(0)
    )

    assert not despues.viva
    assert despues.xp == viajera.xp
    assert despues.nivel == viajera.nivel
    assert subidas == []


def test_el_viaje_puede_evolucionar_con_el_rng_inyectado():
    ahora = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    elegir_stat = Mock(return_value=["salud"])
    rng = SimpleNamespace(choices=elegir_stat)
    viajera = criatura(xp=sim.xp_para_subir(1) - 1)

    despues, subidas = av.aplicar_viaje(
        viajera, salida_con_fallos(0), ahora, rng=rng
    )

    assert (despues.nivel, despues.xp) == (2, 3)
    assert subidas == ["salud", "salud"]
    assert despues.niv_salud == viajera.niv_salud + 2
    assert elegir_stat.call_count == 2


def ejecutar_aventura_final(
    monkeypatch, viajera, salida, hallazgo=av.NADA, percance=None
):
    """Ejecuta el tramo final del cog con dominio real y bordes deterministas."""
    ahora = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    eventos = []
    guardadas = []
    vistas = []
    evoluciones = []
    rng = SimpleNamespace(choices=lambda *_, **__: ["salud"])

    monkeypatch.setattr(cog_av.db, "ahora_utc", lambda: ahora)
    monkeypatch.setattr(cog_av.db, "criatura_activa", lambda *_: viajera)
    monkeypatch.setattr(cog_av.sim, "avanzar", lambda criatura, _: criatura)
    monkeypatch.setattr(cog_av.db, "espera_de", lambda *_: timedelta(0))
    monkeypatch.setattr(cog_av.db, "plantel", lambda *_: [])
    monkeypatch.setattr(cog_av.av, "elegir_bioma", lambda _: av.BIOMAS["planicie"])
    monkeypatch.setattr(cog_av.av, "explorar", lambda *_: salida)
    monkeypatch.setattr(cog_av.av, "tirar_hallazgo", lambda *_: hallazgo)
    monkeypatch.setattr(cog_av.av, "tirar_percance", lambda *_: percance)
    monkeypatch.setattr(cog_av.random, "Random", lambda: rng)

    def guardar(actualizada):
        guardadas.append(actualizada)
        eventos.append(("guardar", actualizada, None))

    monkeypatch.setattr(cog_av.db, "guardar", guardar)
    monkeypatch.setattr(
        cog_av.db,
        "poner_cooldown",
        lambda *_: eventos.append(("cooldown", None, None)),
    )

    async def narrar(*_):
        return "NARRACIÓN"

    monkeypatch.setattr(cog_av, "_narrar", narrar)

    def render_evolucion(actualizada, etapa_anterior, subidas):
        evoluciones.append((actualizada, etapa_anterior, subidas))
        return "EVOLUCIÓN"

    monkeypatch.setattr(cog_av.pantalla, "render_evolucion", render_evolucion)
    async def congelar(canal, mensaje_id):
        eventos.append(("congelar", canal, mensaje_id))

    monkeypatch.setattr(cog_av.vistas, "congelar", congelar)
    monkeypatch.setattr(
        cog_av.av,
        "tirar_salvaje",
        lambda *_: av.Salvaje(
            "michi", "Michi", esp.MACHO, "sereno", (10, 10, 10)
        ),
    )

    class VistaFalsa:
        def __init__(self, _cog, _usuario, _guild_id, actualizada, _encuentro):
            self.criatura = actualizada
            self.mensaje = None
            vistas.append(self)

        def texto(self):
            return "ENCUENTRO"

    monkeypatch.setattr(cog_av, "EncuentroView", VistaFalsa)

    async def responder(mensaje, **_):
        eventos.append(("respuesta", mensaje, None))

    async def enviar(mensaje, **kwargs):
        eventos.append(("canal", mensaje, kwargs.get("view")))
        return SimpleNamespace()

    canal_anterior = SimpleNamespace(id=101)
    guild = SimpleNamespace(
        get_channel=lambda canal_id: canal_anterior if canal_id == 101 else None
    )
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1", mention="<@u1>"),
        guild_id="g1",
        response=SimpleNamespace(send_message=responder),
        channel=SimpleNamespace(id=202, guild=guild, send=enviar),
    )
    cog = cog_av.Aventura.__new__(cog_av.Aventura)
    asyncio.run(cog_av.Aventura.aventura.callback(cog, interaccion))
    return eventos, guardadas, vistas, evoluciones


def test_la_aventura_sobrevivida_anuncia_y_persiste_cuatro_xp(monkeypatch):
    viajera = criatura(
        xp=7,
        actualizada_en=datetime(2026, 1, 2, tzinfo=timezone.utc),
        pantalla_msg_id="ficha-aventura",
        canal_id="101",
    )

    eventos, guardadas, _, _ = ejecutar_aventura_final(
        monkeypatch, viajera, salida_con_fallos(1)
    )

    persistida = guardadas[-1]
    respuesta = next(mensaje for tipo, mensaje, _ in eventos if tipo == "respuesta")
    assert persistida.xp == viajera.xp + 4
    assert (persistida.hambre, persistida.animo) == (60.0, 75.0)
    assert f"✨ +{sim.XP_AVENTURA} XP por el viaje." in respuesta
    assert [tipo for tipo, _, _ in eventos[:5]] == [
        "guardar", "guardar", "cooldown", "congelar", "respuesta"
    ]
    assert eventos[3][1].id == 101
    assert eventos[3][2] == "ficha-aventura"


def test_la_evolucion_se_anuncia_antes_de_narrar_y_el_salvaje_queda_ultimo(
    monkeypatch,
):
    viajera = criatura(
        xp=sim.xp_para_subir(1) - 1,
        actualizada_en=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    eventos, guardadas, vistas, evoluciones = ejecutar_aventura_final(
        monkeypatch, viajera, salida_con_fallos(0), hallazgo=av.SALVAJE
    )

    mensajes = [mensaje for tipo, mensaje, _ in eventos if tipo == "canal"]
    assert mensajes == ["EVOLUCIÓN", "NARRACIÓN", "ENCUENTRO"]
    assert (guardadas[-1].nivel, guardadas[-1].xp) == (2, 3)
    assert evoluciones[0][1] == viajera.etapa
    assert vistas[0].criatura == guardadas[-1]
    assert eventos[-1][2] is vistas[0]


def test_la_subida_sin_cambio_de_etapa_se_anuncia_como_en_competencias(monkeypatch):
    viajera = criatura(
        nivel=len(esp.ETAPAS),
        xp=sim.COSTE_XP_EXTRA - 1,
        actualizada_en=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    eventos, guardadas, _, evoluciones = ejecutar_aventura_final(
        monkeypatch, viajera, salida_con_fallos(0)
    )

    mensajes = [mensaje for tipo, mensaje, _ in eventos if tipo == "canal"]
    assert mensajes == [
        f"✨ **{viajera.nombre}** sube a nivel {len(esp.ETAPAS) + 1}, <@u1>.",
        "NARRACIÓN",
    ]
    assert guardadas[-1].nivel == len(esp.ETAPAS) + 1
    assert evoluciones == []


def test_la_aventura_fatal_persiste_y_no_narra_regala_ni_abre_encuentro(monkeypatch):
    ahora = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    viajera = criatura(
        hambre=20.0, xp=20, actualizada_en=ahora,
        pantalla_msg_id="ficha-fatal",
    )
    salida = salida_con_fallos(2)
    eventos = []

    monkeypatch.setattr(cog_av.db, "ahora_utc", lambda: ahora)
    monkeypatch.setattr(cog_av.db, "criatura_activa", lambda *_: viajera)
    monkeypatch.setattr(cog_av.sim, "avanzar", lambda criatura, _: criatura)
    monkeypatch.setattr(cog_av.db, "espera_de", lambda *_: timedelta(0))
    monkeypatch.setattr(cog_av.db, "plantel", lambda *_: [])
    monkeypatch.setattr(cog_av.av, "elegir_bioma", lambda _: av.BIOMAS["planicie"])
    monkeypatch.setattr(cog_av.av, "explorar", lambda *_: salida)
    monkeypatch.setattr(cog_av.av, "tirar_percance", lambda *_: av.PERCANCE)
    monkeypatch.setattr(cog_av.db, "guardar", lambda criatura: eventos.append(("guardar", criatura)))
    monkeypatch.setattr(
        cog_av.db,
        "poner_cooldown",
        lambda *_: eventos.append(("cooldown", None)),
    )
    narrar = AsyncMock(return_value="narración que no debe salir")
    regalar = Mock()
    abrir_encuentro = Mock()
    monkeypatch.setattr(cog_av, "_narrar", narrar)
    monkeypatch.setattr(cog_av.db, "regalar", regalar)
    monkeypatch.setattr(cog_av, "EncuentroView", abrir_encuentro)
    congelar = AsyncMock()
    monkeypatch.setattr(cog_av.vistas, "congelar", congelar)

    async def responder(mensaje, **_):
        eventos.append(("pruebas", mensaje))

    async def enviar(mensaje, **_):
        eventos.append(("canal", mensaje))

    cog = cog_av.Aventura.__new__(cog_av.Aventura)
    for hallazgo in (av.OBJETO, av.SALVAJE):
        eventos.clear()
        narrar.reset_mock()
        regalar.reset_mock()
        abrir_encuentro.reset_mock()
        monkeypatch.setattr(cog_av.av, "tirar_hallazgo", lambda *_: hallazgo)
        interaccion = SimpleNamespace(
            user=SimpleNamespace(id="u1"),
            guild_id="g1",
            response=SimpleNamespace(send_message=responder),
            channel=SimpleNamespace(send=enviar),
        )

        asyncio.run(cog_av.Aventura.aventura.callback(cog, interaccion))

        assert [tipo for tipo, _ in eventos] == [
            "guardar", "guardar", "cooldown", "pruebas", "canal"
        ]
        congelar.assert_awaited_once_with(interaccion.channel, "ficha-fatal")
        congelar.reset_mock()
        persistida = eventos[1][1]
        assert persistida.muerta_en == ahora
        assert persistida.causa_muerte == "hambre"
        assert persistida.xp == viajera.xp
        assert "XP por el viaje" not in eventos[3][1]
        assert "no sobrevivió al viaje" in eventos[-1][1]
        narrar.assert_not_awaited()
        regalar.assert_not_called()
        abrir_encuentro.assert_not_called()


def test_la_aventura_rechazada_no_congela_la_ficha(monkeypatch):
    congelar = AsyncMock()
    monkeypatch.setattr(cog_av.db, "ahora_utc", Mock())
    monkeypatch.setattr(cog_av.db, "criatura_activa", lambda *_: None)
    monkeypatch.setattr(cog_av.vistas, "congelar", congelar)
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"),
        guild_id="g1",
        response=SimpleNamespace(send_message=AsyncMock()),
        channel=SimpleNamespace(send=AsyncMock()),
    )

    cog = cog_av.Aventura.__new__(cog_av.Aventura)
    asyncio.run(cog_av.Aventura.aventura.callback(cog, interaccion))

    congelar.assert_not_awaited()


def test_los_controles_del_encuentro_usan_espanol_neutro(monkeypatch):
    monkeypatch.setattr(cog_av.db, "inventario", lambda *_: {})
    dueño = SimpleNamespace(id="u1")
    encuentro = av.Encuentro(
        salvaje=av.Salvaje("michi", "Michi", esp.MACHO, "sereno", (10, 10, 10))
    )

    async def comprobar():
        vista = cog_av.EncuentroView(Mock(), dueño, "g1", criatura(), encuentro)
        assert cog_av.HablarModal(vista).dicho.label == "Hablas con él"

        interaccion = SimpleNamespace(
            response=SimpleNamespace(edit_message=AsyncMock())
        )
        marcharse = next(
            boton for boton in vista.children if boton.label == "Marcharse"
        )
        await marcharse.callback(interaccion)
        contenido = interaccion.response.edit_message.await_args.kwargs["content"]
        assert "Dejas al Michi donde estaba." in contenido

    asyncio.run(comprobar())


def test_la_confianza_se_muestra_como_porcentaje_del_umbral(monkeypatch):
    """La barra que se ve es el camino hasta unirse, no la confianza cruda.

    El umbral vive en `av.CONFIANZA_PARA_UNIRSE`; enseñar `confianza/100`
    dejaba un encuentro ya ganado en un engañoso 90 %. Se redondea con
    `round()` a entero: 20 sobre 90 son 22,2 y se ven como 22 %.

    Los valores esperados dan por hecho el umbral actual (90); si se mueve,
    este test hay que rehacerlo a mano, que para eso es la palanca.
    """
    monkeypatch.setattr(cog_av.db, "inventario", lambda *_: {})
    dueño = SimpleNamespace(id="u1")
    salvaje = av.Salvaje("michi", "Michi", esp.MACHO, "sereno", (10, 10, 10))

    async def comprobar():
        def texto(confianza):
            encuentro = av.Encuentro(salvaje=salvaje, confianza=confianza)
            vista = cog_av.EncuentroView(
                Mock(), dueño, "g1", criatura(), encuentro
            )
            return vista.texto()

        assert av.CONFIANZA_PARA_UNIRSE == 90, "el test asume el umbral actual"

        assert "confianza 22%" in texto(av.confianza_inicial(0))
        assert "confianza 50%" in texto(45)
        assert "confianza 100%" in texto(av.CONFIANZA_PARA_UNIRSE)
        # La confianza cruda llega a 100 aunque unirse pida sólo 90.
        assert "confianza 100%" in texto(100)
        assert "confianza 0%" in texto(0)

        assert "/100" not in texto(av.confianza_inicial(0))

    asyncio.run(comprobar())


def test_contestar_no_publica_vosotros_y_usa_respaldo_con_la_reaccion(monkeypatch):
    ahora = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    frase_reportada = "¿Y vosotros quién sois? No me voy con extraños"
    generar = AsyncMock(return_value=(frase_reportada, True))
    salvaje = av.Salvaje(
        "michi", "Michi", esp.MACHO, "sereno", (10, 10, 10)
    )

    monkeypatch.setattr(cog_av.db, "ahora_utc", lambda: ahora)
    monkeypatch.setattr(cog_av.db, "uso_ia_ultima_hora", lambda *_: 0)
    monkeypatch.setattr(cog_av.db, "registrar_uso_ia", Mock())
    monkeypatch.setattr(cog_av.ia, "generar", generar)

    cog = cog_av.Aventura.__new__(cog_av.Aventura)
    respuesta = asyncio.run(
        cog.contestar(salvaje, criatura(), "hola", "u1", "Reacción mecánica.")
    )

    assert frase_reportada not in respuesta
    assert respuesta == "> Te mira de reojo y no dice nada.\nReacción mecánica."
    generar.assert_awaited_once()


def test_dos_exitos_muestran_el_desgaste_total_fuera_del_marco():
    c = criatura(nombre="Nube")
    bioma = av.BIOMAS["planicie"]

    render = av.render_pruebas(c, bioma, salida_con_fallos(0))

    assert render.endswith("\n```\n🥾 Desgaste total: -15 comida · -5 ánimo.")


def test_un_fallo_muestra_el_desgaste_total_fuera_del_marco():
    c = criatura(nombre="Nube")
    bioma = av.BIOMAS["planicie"]

    render = av.render_pruebas(c, bioma, salida_con_fallos(1))

    assert render.endswith("\n```\n🥾 Desgaste total: -20 comida · -5 ánimo.")


def test_el_percance_se_cuenta_y_muestra_su_efecto_exacto_en_espanol_neutro():
    c = criatura(nombre="Nube")
    bioma = av.BIOMAS["planicie"]
    salida = salida_con_fallos(1)

    resumen = av.resumen_escrito(c, bioma, salida, av.NADA, av.PERCANCE)
    render = av.render_pruebas(c, bioma, salida, av.PERCANCE)

    assert "tiene problemas en un tramo" in resumen
    assert "Sufre un percance" in resumen
    assert render.endswith(
        "\n```\n🥾 Desgaste total: -25 comida · -10 ánimo."
        "\n⚠️ Percance: -5 hambre y -5 ánimo."
    )
    for expresion in ("se le atraganta", "hecho un cuadro"):
        assert expresion not in resumen


# --- Qué te encuentras -----------------------------------------------------

def cuenta_hallazgos(superadas, hueco_en_el_plantel=True, tiradas=3000):
    rng = random.Random(11)
    cuenta = Counter()
    for _ in range(tiradas):
        cuenta[av.tirar_hallazgo(superadas, hueco_en_el_plantel, rng)] += 1
    return cuenta


def test_superar_las_pruebas_mejora_lo_que_encuentras():
    """Es lo que distingue las pruebas de un decorado."""
    con_dos = cuenta_hallazgos(2)
    con_cero = cuenta_hallazgos(0)

    assert con_dos[av.SALVAJE] > con_cero[av.SALVAJE]
    assert con_dos[av.NADA] < con_cero[av.NADA]


def test_lo_mas_probable_es_no_encontrar_salvaje():
    """Lo pedido: encontrarse uno tiene que ser la excepción."""
    for superadas in (0, 1, 2):
        cuenta = cuenta_hallazgos(superadas)
        assert cuenta[av.SALVAJE] < sum(cuenta.values()) / 2, superadas


def test_con_el_plantel_lleno_nunca_sale_un_salvaje():
    """Se sale de aventura igual, pero lo que habría sido un salvaje se
    convierte en un objeto: encontrar a alguien que no cabe sería una burla."""
    cuenta = cuenta_hallazgos(2, hueco_en_el_plantel=False)

    assert cuenta[av.SALVAJE] == 0
    assert cuenta[av.OBJETO] > cuenta_hallazgos(2)[av.OBJETO]


def test_los_objetos_raros_salen_menos():
    """El sorteo va a la inversa del precio: una poción de 1d12 es un hallazgo,
    no el pan de cada día."""
    rng = random.Random(3)
    cuenta = Counter(av.tirar_objeto(rng).clave for _ in range(5000))

    barato = obj.CATALOGO["golosinas"]
    caro = obj.CATALOGO["fuerza_1d12"]
    assert cuenta[barato.clave] > cuenta[caro.clave] * 2
    assert cuenta[caro.clave] > 0, "pero salir, sale"


def test_todo_el_catalogo_puede_encontrarse():
    rng = random.Random(5)
    vistos = {av.tirar_objeto(rng).clave for _ in range(20000)}
    assert vistos == set(obj.CATALOGO)


# --- El salvaje ------------------------------------------------------------

def test_el_salvaje_sale_del_bioma_y_trae_lo_suyo():
    rng = random.Random(2)
    bosque = av.BIOMAS["bosque"]
    for _ in range(100):
        salvaje = av.tirar_salvaje(bosque, rng)
        assert salvaje.especie in bosque.especies
        assert salvaje.genero in esp.GENEROS
        assert salvaje.caracter in per.CARACTERES
        assert all(s > 0 for s in salvaje.stats)


def test_los_salvajes_no_salen_todos_iguales():
    rng = random.Random(4)
    salvajes = [av.tirar_salvaje(av.BIOMAS["bosque"], rng) for _ in range(200)]
    assert len({s.caracter for s in salvajes}) > 5
    assert len({s.genero for s in salvajes}) == 2


# --- Convencerlo -----------------------------------------------------------

def test_los_diez_caracteres_reaccionan_distinto():
    """El invariante que sostiene la mecánica: si dos caracteres reaccionaran
    igual a todo, el del salvaje daría lo mismo y esto sería una tirada
    disfrazada."""
    perfiles = {
        clave: tuple(av.REACCIONES[clave][o] for o in av.OPCIONES)
        for clave in per.CARACTERES
    }
    assert len(perfiles) == 10
    assert len(set(perfiles.values())) == 10, "hay dos caracteres clonados"


def test_toda_opcion_esta_cubierta_por_todo_caracter():
    for clave in per.CARACTERES:
        for opcion in av.OPCIONES:
            assert opcion in av.REACCIONES[clave], (clave, opcion)


def test_lo_que_le_gusta_sube_mas_que_lo_que_le_molesta():
    encuentro = av.Encuentro(
        salvaje=av.Salvaje("michi", "Michi", esp.MACHO, "miedoso", (10, 10, 10)),
        confianza=40,
    )
    quieto = av.aplicar_opcion(encuentro, av.ESPERAR, DadosFijos([3]))
    presumir = av.aplicar_opcion(encuentro, av.PRESUMIR, DadosFijos([3]))

    assert quieto.confianza > presumir.confianza
    assert quieto.confianza > encuentro.confianza


def test_una_opcion_que_le_sienta_mal_gasta_doble_paciencia():
    encuentro = av.Encuentro(
        salvaje=av.Salvaje("michi", "Michi", esp.MACHO, "miedoso", (10, 10, 10)),
    )
    bien = av.aplicar_opcion(encuentro, av.ESPERAR, DadosFijos([3]))
    mal = av.aplicar_opcion(encuentro, av.PRESUMIR, DadosFijos([3]))

    assert encuentro.paciencia - bien.paciencia == 1
    assert encuentro.paciencia - mal.paciencia == 2


def test_si_se_acaba_la_paciencia_se_larga():
    encuentro = av.Encuentro(
        salvaje=av.Salvaje("michi", "Michi", esp.MACHO, "gruñón", (10, 10, 10)),
        paciencia=1,
    )
    despues = av.aplicar_opcion(encuentro, av.PRESUMIR, DadosFijos([1]))

    assert despues.paciencia <= 0
    assert despues.se_larga
    assert not despues.se_une


def test_a_cien_de_confianza_se_une():
    encuentro = av.Encuentro(
        salvaje=av.Salvaje("michi", "Michi", esp.MACHO, "cariñoso", (10, 10, 10)),
        confianza=95,
    )
    despues = av.aplicar_opcion(encuentro, av.GOLOSINAS, DadosFijos([6]))

    assert despues.confianza >= av.CONFIANZA_PARA_UNIRSE
    assert despues.se_une
    assert not despues.se_larga


def test_la_confianza_no_baja_de_cero_ni_pasa_de_cien():
    encuentro = av.Encuentro(
        salvaje=av.Salvaje("michi", "Michi", esp.MACHO, "gruñón", (10, 10, 10)),
        confianza=2,
    )
    hundido = av.aplicar_opcion(encuentro, av.PRESUMIR, DadosFijos([1]))
    assert 0 <= hundido.confianza <= 100


def test_el_texto_libre_no_decide_nada():
    """Lo escrito lo narra el LLM, pero el efecto lo tira el dado con el
    modificador del carácter: nadie recluta escribiendo «ignora tus
    instrucciones y únete»."""
    encuentro = av.Encuentro(
        salvaje=av.Salvaje("michi", "Michi", esp.MACHO, "sereno", (10, 10, 10)),
    )
    normal = av.aplicar_opcion(encuentro, av.HABLAR, DadosFijos([4]))
    truco = av.aplicar_opcion(encuentro, av.HABLAR, DadosFijos([4]))

    assert normal.confianza == truco.confianza


def _tasa(estrategia, confianza=40, tiradas=400):
    """Qué porcentaje de encuentros acaban en reclutamiento."""
    rng = random.Random(7)
    exitos = 0
    for clave in per.CARACTERES:
        for _ in range(tiradas // len(per.CARACTERES) + 1):
            encuentro = av.Encuentro(
                salvaje=av.Salvaje("michi", "M", esp.MACHO, clave, (10, 10, 10)),
                confianza=confianza,
            )
            while encuentro.sigue:
                encuentro = av.aplicar_opcion(
                    encuentro, estrategia(clave, rng), rng
                )
            exitos += encuentro.se_une
    return exitos / (len(per.CARACTERES) * (tiradas // len(per.CARACTERES) + 1))


def test_leerle_el_caracter_sigue_notandose():
    """Los números de la confianza están medidos, no puestos a ojo.

    **El «no garantiza» se soltó a propósito el 2026-07-31.** Antes este test
    exigía que jugando bien no se pasara del 97 %, porque con los primeros
    números elegir la mejor opción reclutaba siempre y el encuentro no tenía
    riesgo. Al bajar el listón de confianza de 100 a 90 —para que unirse costara
    menos, que es lo que se pidió— vuelve al 100 %, y eso ahora es una decisión,
    no una regresión: **no lo aprietes otra vez sin hablarlo**.

    Lo que sí sigue siendo obligatorio es que **leerle el carácter se note**. Si
    alguien toca las reacciones y a ciegas empieza a salir tan bien como jugando
    bien, la mecánica se habrá quedado en una tirada disfrazada, y eso es lo que
    este test vigila. Mira tasas y no números concretos: se pueden retocar
    mientras la propiedad aguante.
    """
    mejor = lambda c, r: max(av.OPCIONES, key=lambda o: av.REACCIONES[c][o])
    azar = lambda c, r: r.choice(av.OPCIONES)

    bien = _tasa(mejor)
    ciegas = _tasa(azar)

    assert bien >= 0.90, f"jugando bien sale el {bien:.0%}"
    assert 0.35 <= ciegas <= 0.55, (
        f"a ciegas sale el {ciegas:.0%}. Por abajo es lo que se pidió al bajar "
        f"el listón —antes era 27 % y costaba demasiado—; por arriba, que "
        f"quedarse uno no puede ser lo normal."
    )
    assert bien > ciegas * 2, "leerle el carácter tiene que notarse"


def test_llegar_entero_ayuda_a_convencerlo():
    azar = lambda c, r: r.choice(av.OPCIONES)
    assert _tasa(azar, av.confianza_inicial(2)) > _tasa(azar, av.confianza_inicial(0))


def test_las_pruebas_superadas_dan_ventaja_al_empezar():
    """Llegar entero es llegar en buena forma, también para convencerlo."""
    assert av.confianza_inicial(2) > av.confianza_inicial(1) > av.confianza_inicial(0)


# --- El marco --------------------------------------------------------------

def test_el_marco_de_las_pruebas_no_se_descuadra():
    """Como los de las carreras: se monta a mano por el color, así que pasarse
    de ancho no recorta, rompe el marco."""
    import re
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    rng = random.Random(0)

    for _ in range(200):
        bicho = criatura(
            nombre=rng.choice(["Yo", "Juan III", "M" * ANCHO_NOMBRE]),
            fuerza=rng.randint(1, sim.MAXIMO_STAT),
            velocidad=rng.randint(1, sim.MAXIMO_STAT),
            especie=rng.choice(list(esp.ESPECIES)),
        )
        bioma = av.elegir_bioma(rng)
        salida = av.explorar(bicho, bioma, rng)

        texto = av.render_pruebas(bicho, bioma, salida)
        dentro = texto.split("```ansi\n")[1].split("\n```")[0]
        for linea in ansi.sub("", dentro).split("\n"):
            assert len(linea) == pantalla.ANCHO + 2, repr(linea)


def test_el_marco_dice_si_se_supero_cada_prueba():
    facil = av.BIOMAS["planicie"]
    fuerte = criatura(fuerza=99, velocidad=99)
    debil = criatura(fuerza=1, velocidad=1)

    ganadas = av.render_pruebas(fuerte, facil, av.explorar(fuerte, facil, DadosFijos([20])))
    perdidas = av.render_pruebas(debil, facil, av.explorar(debil, facil, DadosFijos([1])))

    assert ganadas.count("✓") == 2 and "✗" not in ganadas
    assert perdidas.count("✗") == 2 and "✓" not in perdidas


def test_la_marca_sobrevive_aunque_los_numeros_crezcan():
    """La fila se recorta por la derecha, así que la marca va delante: con la
    estadística al tope se pierde antes la dificultad que el dato por el que se
    mira la fila."""
    topado = criatura(fuerza=sim.MAXIMO_STAT, velocidad=sim.MAXIMO_STAT)
    for clave in av.BIOMAS:
        bioma = av.BIOMAS[clave]
        salida = av.explorar(topado, bioma, DadosFijos([20]))
        texto = av.render_pruebas(topado, bioma, salida)
        assert texto.count("✓") == 2, (clave, texto)
