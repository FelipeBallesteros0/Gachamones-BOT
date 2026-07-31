"""Las mutaciones externas apagan la ficha viva que acaba de quedar obsoleta."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import equipo
import simulacion as sim
import vistas


def criatura(id_, nombre, activa, pantalla_msg_id):
    return sim.Criatura(
        id=id_, usuario_id="u1", guild_id="g1", especie="pulpo", nombre=nombre,
        nacida_en=None, actualizada_en=None,
        base_fuerza=15, base_velocidad=15, base_salud=15,
        hambre=80.0, animo=80.0, activa=activa,
        pantalla_msg_id=pantalla_msg_id,
    )


def test_pantalla_inyecta_el_congelador_en_mochila_y_plantel(monkeypatch):
    monkeypatch.setattr(vistas, "_es_de_otro", AsyncMock(return_value=False))
    abrir_inventario = AsyncMock()
    abrir_plantel = AsyncMock()
    monkeypatch.setattr(vistas.tienda, "abrir_inventario", abrir_inventario)
    monkeypatch.setattr(vistas.equipo, "abrir_plantel", abrir_plantel)
    interaccion = SimpleNamespace()
    botones = {boton.custom_id: boton for boton in vistas.PantallaView().children}

    asyncio.run(botones["tama:inventario"].callback(interaccion))
    asyncio.run(botones["tama:plantel"].callback(interaccion))

    abrir_inventario.assert_awaited_once_with(interaccion, vistas.congelar)
    abrir_plantel.assert_awaited_once_with(interaccion, vistas.congelar)


def test_cambiar_activo_congela_la_ficha_anterior_antes_de_responder(monkeypatch):
    anterior = criatura(1, "Anterior", True, "ficha-anterior")
    nueva = criatura(2, "Nueva", False, "ficha-nueva")
    monkeypatch.setattr(
        equipo.db, "criatura_activa", Mock(side_effect=[anterior, nueva])
    )
    monkeypatch.setattr(equipo.db, "activar", Mock(return_value=True))
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    eventos = []

    async def responder(**_):
        eventos.append("respuesta")

    async def congelar(canal, mensaje_id):
        eventos.append(("congelar", canal, mensaje_id))

    menu = equipo.MenuPlantel([anterior, nueva], congelar)
    menu._values = [str(nueva.id)]
    canal = SimpleNamespace()
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=canal,
        response=SimpleNamespace(edit_message=responder),
    )

    asyncio.run(menu.callback(interaccion))

    assert eventos == [("congelar", canal, "ficha-anterior"), "respuesta"]


def test_cambiar_al_mismo_activo_no_congela(monkeypatch):
    anterior = criatura(1, "Anterior", True, "ficha-anterior")
    monkeypatch.setattr(equipo.db, "criatura_activa", Mock(return_value=anterior))
    monkeypatch.setattr(equipo.db, "activar", Mock())
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    congelar = AsyncMock()
    menu = equipo.MenuPlantel([anterior], congelar)
    menu._values = [str(anterior.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(interaccion))

    congelar.assert_not_awaited()
    equipo.db.activar.assert_not_called()


def test_cambio_de_activo_invalido_no_congela(monkeypatch):
    anterior = criatura(1, "Anterior", True, "ficha-anterior")
    ajena = criatura(2, "Ajena", False, "ficha-ajena")
    monkeypatch.setattr(equipo.db, "criatura_activa", Mock(return_value=anterior))
    monkeypatch.setattr(equipo.db, "activar", Mock(return_value=False))
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    congelar = AsyncMock()
    menu = equipo.MenuPlantel([anterior, ajena], congelar)
    menu._values = [str(ajena.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(interaccion))

    congelar.assert_not_awaited()
