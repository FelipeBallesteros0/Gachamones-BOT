import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import config
import db
import vinculo
from cogs import social

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
PUEBLO = 777


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "vincular.db")
    monkeypatch.setattr(db, "ahora_utc", lambda: T0)
    monkeypatch.setattr(config, "GUILD_WEB", PUEBLO)
    db.inicializar()


def escribir(codigo: str, servidor: int = PUEBLO, quien: int = 555):
    interaccion = SimpleNamespace(
        guild_id=servidor,
        user=SimpleNamespace(id=quien),
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    cog = social.Social(SimpleNamespace())
    asyncio.run(social.Social.vincular.callback(cog, interaccion, codigo))
    return interaccion.response.send_message


def test_vincular_canjea_el_codigo_y_contesta_solo_a_quien_lo_escribio():
    respuesta = escribir(db.pedir_codigo_de_vinculo(12, T0))
    respuesta.assert_awaited_once_with(vinculo.MENSAJES[vinculo.OK], ephemeral=True)
    assert db.cuenta_web(12) == db.CuentaWeb(12, "555", str(PUEBLO), True)


def test_un_codigo_malo_tambien_se_contesta_en_privado():
    respuesta = escribir("MALMALMA")
    respuesta.assert_awaited_once_with(
        vinculo.MENSAJES[vinculo.INVALIDO], ephemeral=True
    )


def test_en_otro_servidor_no_canjea_nada():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    respuesta = escribir(codigo, servidor=1)
    respuesta.assert_awaited_once_with(social.SERVIDOR_SIN_WEB, ephemeral=True)
    assert db.cuenta_web(12) is None
    assert escribir(codigo).await_args.args[0] == vinculo.MENSAJES[vinculo.OK]
