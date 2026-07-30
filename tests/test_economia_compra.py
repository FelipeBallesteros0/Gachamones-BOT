import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

import db
import economia
import objetos as obj


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "economia.db")
    db.inicializar()


def test_compra_es_idempotente_y_valida_la_solicitud():
    objeto = obj.CATALOGO["fuerza_1d8"]
    primera = economia.comprar("evento", "u", "g", objeto)
    replay = economia.comprar("evento", "u", "g", objeto)

    assert primera.comprada and not primera.replay
    assert replay.comprada and replay.replay
    assert economia.saldos("u", "g").asciicoins == 50 - objeto.precio
    assert db.inventario("u", "g") == {objeto.clave: 1}
    with pytest.raises(RuntimeError):
        economia.comprar("evento", "u", "g", obj.CATALOGO["pocion_comida"])


def test_saldo_insuficiente_es_pegajoso_aunque_luego_haya_saldo():
    caro = obj.CATALOGO["fuerza_1d12"]
    assert economia.comprar("gasto", "u", "g", caro)
    fallida = economia.comprar("fallida", "u", "g", caro)
    with db.conectar() as con:
        con.execute("UPDATE monederos SET asciicoins = 100 WHERE usuario_id = 'u'")

    replay = economia.comprar("fallida", "u", "g", caro)
    assert not fallida and not replay and replay.replay
    assert db.inventario("u", "g") == {caro.clave: 1}


def test_fallo_al_insertar_operacion_revierte_debito_e_inventario():
    objeto = obj.CATALOGO["pocion_comida"]
    with db.conectar() as con:
        con.execute(
            "CREATE TRIGGER rompe_compra BEFORE INSERT ON operaciones_economia "
            "BEGIN SELECT RAISE(ABORT, 'fallo'); END"
        )
    with pytest.raises(sqlite3.IntegrityError):
        economia.comprar("evento", "u", "g", objeto)

    assert economia.saldos("u", "g") == economia.Saldos(50, 50)
    assert db.inventario("u", "g") == {}


def test_dos_compras_concurrentes_no_dejan_saldo_negativo():
    objeto = obj.CATALOGO["fuerza_1d12"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(
            lambda evento: economia.comprar(evento, "u", "g", objeto),
            ("uno", "dos"),
        ))

    assert sum(resultado.comprada for resultado in resultados) == 1
    assert economia.saldos("u", "g").asciicoins == 50 - objeto.precio
    assert db.inventario("u", "g") == {objeto.clave: 1}


def test_objeto_fuera_del_catalogo_se_rechaza_antes_de_escribir():
    falso = obj.Objeto("pocion_comida", "falso", "x", 1, "x")
    with pytest.raises(ValueError):
        economia.comprar("evento", "u", "g", falso)
    assert economia.saldos("u", "g") == economia.Saldos(50, 50)
