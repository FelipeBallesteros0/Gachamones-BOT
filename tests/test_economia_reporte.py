import json
from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

import db
import economia
import economia_reporte as reporte
import objetos as obj
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "economia.db")
    db.inicializar()


def test_reporte_agrega_sin_exponer_identidades():
    db.crear("usuario-secreto", "guild-secreta", "pulpo", "A", (15, 15, 15, 15), T0)
    economia.ejecutar_cuidado(
        "cuidado", "usuario-secreto", "guild-secreta", sim.JUGAR, T0
    )
    economia.comprar(
        "compra", "usuario-secreto", "guild-secreta",
        obj.CATALOGO["pocion_comida"], T0,
    )

    datos = reporte.datos_reporte(db.RUTA, date(2026, 1, 1), date(2026, 1, 1))
    serializado = json.dumps(datos)
    assert "usuario-secreto" not in serializado and "guild-secreta" not in serializado
    assert datos["por_dia"]["2026-01-01"] == {
        "emitido": 1, "gastado": 10, "neto": -9
    }
    assert datos["compras"]["pocion_comida"] == {"cantidad": 1, "gastado": 10}
    assert datos["reconciliacion"]["cuadra"]
    assert "Reconciliación histórica global: OK" in reporte.render_texto(datos)


def test_reclutar_en_aventura_no_toca_cupos_ni_conciliacion():
    activa = db.crear("u", "g", "pulpo", "A", (15, 15, 15, 15), T0)
    primero = economia.ejecutar_cuidado("antes", "u", "g", sim.JUGAR, T0)
    saldo = economia.saldos("u", "g")

    reclutada = db.crear(
        "u", "g", "brote", "Salvaje", (14, 14, 14, 15), T0, activa=False
    )
    db.regalar("u", "g", obj.CATALOGO["golosinas"])

    activa_actual = db.criatura_activa("u", "g")
    assert activa_actual is not None
    assert not reclutada.activa and activa_actual.id == activa.id
    assert economia.saldos("u", "g") == saldo
    con_siguiente_cupo = db.criatura_activa("u", "g")
    assert con_siguiente_cupo is not None
    db.guardar(replace(con_siguiente_cupo, limpieza=0.0))
    segundo = economia.ejecutar_cuidado(
        "despues", "u", "g", sim.LIMPIAR, T0
    )
    assert primero is not None and segundo is not None
    assert primero.usados == 1 and segundo.usados == 2

    datos = reporte.datos_reporte(db.RUTA, date(2026, 1, 1), date(2026, 1, 1))
    assert datos["reconciliacion"]["cuadra"]
    assert datos["actividad"]["monederos"] == 1
    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM operaciones_economia").fetchone()[0] == 2


def test_reconciliacion_detecta_manipulacion_y_intervalo_invalido():
    economia.saldos("u", "g")
    with db.conectar() as con:
        con.execute("UPDATE monederos SET asciicoins = 99")
    datos = reporte.datos_reporte(db.RUTA, date(2026, 1, 1), date(2026, 1, 1))
    assert not datos["reconciliacion"]["cuadra"]

    with pytest.raises(ValueError, match="intervalo UTC inválido"):
        reporte.datos_reporte(db.RUTA, date(2026, 1, 2), date(2026, 1, 1))
