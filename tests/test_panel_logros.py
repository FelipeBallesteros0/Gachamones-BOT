"""Cómo se cuentan las medallas: el anuncio del canal y el panel de `/logros`."""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import cogs.social as social
import comun
import db
import economia
import logros
import objetos as obj
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "panel.db")
    db.inicializar()


def nacer(nombre="Mia"):
    return db.crear("u1", "g1", "pulpo", nombre, STATS, T0)


# --- El anuncio ------------------------------------------------------------

def recibo_de(*claves, saldo=0):
    nuevos = tuple(logros.POR_CLAVE[c] for c in claves)
    return economia.ReciboLogros(
        nuevos, sum(l.gemas for l in nuevos), saldo
    )


def test_una_sola_medalla_se_canta_en_una_linea():
    bicho = nacer()
    texto = comun.texto_del_anuncio("Mia", recibo_de("velocista"))

    assert texto == (
        "🏅 **Mia** consigue **Velocista** — gana 10 carreras. 💎 +10"
    )


def test_varias_medallas_van_juntas_y_no_en_mensajes_sueltos():
    """Diez carreras seguidas pueden desbloquear dos a la vez; dos mensajes
    seguidos con el mismo formato se leen como si el bot se hubiera repetido."""
    bicho = nacer()
    texto = comun.texto_del_anuncio(
        "Mia", recibo_de("velocista", "primera_sangre")
    )

    assert texto.startswith("**Mia** consigue 2 logros. 💎 +15")
    assert texto.count("🏅") == 2
    # Y cada una dice lo suyo, que es lo que se mira cuando se cobran de golpe.
    assert "💎 +10" in texto and "💎 +5" in texto


def test_el_anuncio_sale_una_vez_por_mucho_que_se_llame():
    """Es lo que permite ponerlo en todos los sitios sin pensar: el segundo
    intento no encuentra nada nuevo y no manda nada."""
    bicho = nacer()
    canal = SimpleNamespace(send=AsyncMock())

    asyncio.run(comun.anunciar_logros(canal, bicho, T0))
    asyncio.run(comun.anunciar_logros(canal, bicho, T0))

    canal.send.assert_awaited_once()
    assert "De la alfa" in canal.send.await_args.args[0]


def test_sin_nada_nuevo_no_se_manda_mensaje():
    bicho = nacer()
    canal = SimpleNamespace(send=AsyncMock())
    economia.pagar_logros(bicho, T0)

    asyncio.run(comun.anunciar_logros(canal, bicho, T0))

    canal.send.assert_not_awaited()


def test_el_recluta_sin_nombre_no_sale_como_cadena_vacia():
    """Un salvaje recién unido no tiene nombre todavía, y `**** consigue` sería
    lo que saldría si quien anuncia no pasara por `nombre_visible`."""
    recluta = db.crear(
        "u2", "g1", "michi", sim.NOMBRE_PENDIENTE, STATS, T0, activa=False
    )
    canal = SimpleNamespace(send=AsyncMock())

    asyncio.run(comun.anunciar_logros(canal, recluta, T0))

    assert sim.SIN_NOMBRE in canal.send.await_args.args[0]


# --- El panel --------------------------------------------------------------

def panel_de(bicho, ahora=T0, persona="Felipe"):
    usuario, guild = bicho.usuario_id, bicho.guild_id
    hechos = logros.hechos_de(bicho, db.marcador(bicho.id), ahora)
    hechos_persona = logros.hechos_de_la_persona(
        db.marcador_de_persona(usuario, guild), db.especies_de(usuario, guild)
    )
    reserva = economia.saldos(usuario, guild).asciigems
    return social.panel_de_logros(
        bicho, hechos, db.logros_de(bicho.id),
        persona, hechos_persona, db.logros_de_persona(usuario, guild),
        reserva,
    )


def test_el_panel_las_lista_todas_tenga_las_que_tenga():
    """Las que faltan también salen: son la lista de lo que hay por hacer."""
    panel = panel_de(nacer())

    for logro in logros.LOGROS:
        assert logro.nombre in panel
    assert panel.count("⬜") + panel.count("✅") == len(logros.LOGROS)


def test_el_panel_marca_lo_conseguido_y_cuenta_cuánto_falta():
    bicho = nacer()
    db.apuntar(bicho.id, logros.CARRERAS, 10)
    economia.pagar_logros(bicho, T0)

    panel = panel_de(bicho)
    assert "✅ **Velocista**" in panel
    # Las mismas diez carreras son 10 de las 100 que pide Bólido.
    assert "⬜ **Bólido** · gana 100 carreras · 💎 50 · `10/100`" in panel


def test_el_progreso_no_se_pasa_de_la_meta():
    """Con «Velocista» ya conseguido el contador sigue subiendo, y `137/100`
    en «Bólido» estaría bien pero en uno a medias se lee como un fallo."""
    bicho = nacer()
    db.apuntar(bicho.id, logros.CARRERAS, 137)

    assert "`100/100`" in panel_de(bicho)


def test_los_de_una_sola_vez_no_enseñan_progreso():
    """Un «0/1» en «De la alfa» no le dice nada a nadie."""
    panel = panel_de(nacer())
    assert "/1`" not in panel


def test_el_panel_cabe_en_un_mensaje_de_discord():
    """Dieciocho líneas con nombre y descripción; el tope son 2000 caracteres."""
    bicho = nacer(nombre="Nombre bastante largo pa")
    assert len(panel_de(bicho)) < 2000


def test_el_panel_dice_cuantas_lleva():
    bicho = nacer()
    economia.pagar_logros(bicho, T0)

    assert f"-# 1 de {len(logros.LOGROS)}" in panel_de(bicho)


def test_el_panel_enseña_la_reserva_y_lo_que_queda_por_ganar():
    """Las dos cifras que hacen falta para decidir si ya te alcanza para algo,
    y lo que se dejaría de ganar quien abandone a este gachamon."""
    todas = sum(logro.gemas for logro in logros.LOGROS)
    bicho = nacer()
    recibo = economia.pagar_logros(bicho, T0)  # «De la alfa» y sus gemas

    panel = panel_de(bicho)
    assert f"💎 **{obj.ASCIIGEMS_INICIALES + recibo.asciigems}** en reserva" in panel
    assert f"le quedan {todas - recibo.asciigems} por ganar" in panel


def test_cada_logro_dice_lo_que_paga():
    """Es lo que convierte el panel en una lista de objetivos: sin el número,
    no hay forma de saber cuál compensa perseguir."""
    panel = panel_de(nacer())

    for logro in logros.LOGROS:
        assert f"**{logro.nombre}** · {logro.como} · 💎 {logro.gemas}" in panel


def test_veterano_se_apunta_al_mirar_el_panel_aunque_nadie_haya_jugado():
    """El único que se cumple solo con esperar. Si `/logros`
    no lo pagara, el panel lo daría por conseguido, la tabla no se habría
    enterado y las gemas no se cobrarían nunca."""
    bicho = nacer()
    un_mes = T0 + timedelta(days=31)

    assert "veterano" not in db.logros_de(bicho.id)
    recibo = economia.pagar_logros(bicho, un_mes)

    assert "veterano" in {logro.clave for logro in recibo.nuevos}
    assert "veterano" in db.logros_de(bicho.id)
    assert recibo.asciigems >= logros.POR_CLAVE["veterano"].gemas


# --- Que el anuncio esté enchufado donde se gana ----------------------------
#
# Las tres de la persona sólo pueden cambiar al nacer un gachamon y al reclutar,
# y ahí es donde se cantan. Se prueban contra los cogs de verdad porque el fallo
# que importa es el cable suelto: la medalla se gana igual, pero nadie se entera
# hasta que escriba `/logros`.

def _interaccion(canal, usuario_id="1", nombre="Felipe"):
    return SimpleNamespace(
        user=SimpleNamespace(id=usuario_id, display_name=nombre),
        guild_id="g1",
        channel_id="c1",
        channel=canal,
        response=SimpleNamespace(edit_message=AsyncMock()),
        original_response=AsyncMock(return_value=SimpleNamespace(id="m1")),
        edit_original_response=AsyncMock(),
    )


def test_al_romper_el_huevo_una_rara_se_canta_como_tuya(monkeypatch):
    import cogs.mascota as cog_mascota
    import especies as esp

    canal = SimpleNamespace(send=AsyncMock())
    monkeypatch.setattr(
        cog_mascota.esp, "elegir_del_huevo", lambda _: esp.ESPECIES["dragoncito"]
    )
    vista = cog_mascota.HuevoView("1")

    asyncio.run(vista.romper.callback(_interaccion(canal)))

    anuncio = canal.send.await_args.args[0]
    assert "Uno entre veinticinco" in anuncio
    assert "Felipe" in anuncio          # tuya, no del bicho
    assert set(db.logros_de_persona("1", "g1")) == {"uno_entre_veinticinco"}


def test_al_reclutar_domador_se_canta_como_tuyo(monkeypatch):
    import aventura as av
    import cogs.aventura as cog_av

    bicho = db.crear("1", "g1", "pulpo", "Aventurero", STATS, T0)
    canal = SimpleNamespace(send=AsyncMock())
    salvaje = av.Salvaje("michi", "Michi", "macho", "sereno", (10, 10, 10, 15))
    vista = cog_av.EncuentroView(
        None, SimpleNamespace(id="1", display_name="Felipe"), "g1", bicho,
        av.Encuentro(salvaje=salvaje, confianza=100),
    )

    asyncio.run(vista._unirse(_interaccion(canal), "se acerca"))

    anuncios = " ".join(c.args[0] for c in canal.send.await_args_list)
    assert "Domador" in anuncios and "Felipe" in anuncios
    assert set(db.logros_de_persona("1", "g1")) == {"domador"}
    # Y el gachamon que salió no se lleva ninguna de las tres.
    assert "domador" not in db.logros_de(bicho.id)


@pytest.mark.parametrize("clave", ["dragoncito", "cefiro", "prismlon"])
def test_reclutar_un_raro_tambien_da_uno_entre_veinticinco(clave):
    """Pedido tras jugarlo: la medalla no es sólo del huevo de partida.

    Se prueban las tres raras y no una: **dos de ellas no salen del huevo**, así
    que reclutarlas es la única forma de conseguirlas, y si esto sólo mirase a
    la del huevo no habría manera de ganarla con ellas.
    """
    import aventura as av
    import cogs.aventura as cog_av
    import especies as esp

    assert esp.ESPECIES[clave].rareza == esp.RARA
    bicho = db.crear("1", "g1", "pulpo", "Aventurero", STATS, T0)
    canal = SimpleNamespace(send=AsyncMock())
    salvaje = av.Salvaje(clave, esp.ESPECIES[clave].nombre, esp.MACHO, "sereno", (10, 10, 10, 15))
    vista = cog_av.EncuentroView(
        None, SimpleNamespace(id="1", display_name="Felipe"), "g1", bicho,
        av.Encuentro(salvaje=salvaje, confianza=100),
    )

    asyncio.run(vista._unirse(_interaccion(canal), "se acerca"))

    anuncios = " ".join(c.args[0] for c in canal.send.await_args_list)
    assert "Uno entre veinticinco" in anuncios
    assert set(db.logros_de_persona("1", "g1")) == {
        "domador", "uno_entre_veinticinco"
    }


def test_dos_de_las_tres_raras_no_salen_del_huevo():
    """Lo que hace imprescindible al test de arriba: si «Uno entre veinticinco»
    dependiera del cascarón, Céfiro y Prismlon no la darían nunca."""
    import especies as esp

    raras = {c for c, e in esp.ESPECIES.items() if e.rareza == esp.RARA}
    assert raras - set(esp.DEL_HUEVO) == {"cefiro", "prismlon"}
