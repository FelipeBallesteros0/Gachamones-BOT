"""El camino completo de un consumible: comprarlo, usarlo y notarlo peleando."""
import random
from datetime import datetime, timedelta, timezone

import pytest

import competir as comp
import db
import objetos as obj
import simulacion as sim
import tienda

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15)


@pytest.fixture(autouse=True)
def bd_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "prueba.db")
    db.inicializar()


def nacer(usuario="u1"):
    return db.crear(usuario, "g1", "pulpo", "Prueba", STATS, T0)


class DadoFijo(random.Random):
    def __init__(self, valor):
        super().__init__()
        self.valor = valor

    def randint(self, a, b):
        return min(self.valor, b)


# --- De la tienda a la pelea ------------------------------------------------

def test_comprar_beber_y_que_se_note_en_la_carrera():
    """El recorrido entero: es lo que no se puede probar por partes."""
    criatura = nacer()
    pocion = obj.CATALOGO["velocidad_1d10"]

    assert db.comprar("u1", "g1", pocion)
    assert db.gastar("u1", "g1", pocion.clave)
    aviso = tienda.usar(criatura, pocion, T0, DadoFijo(6))
    assert "+6" in aviso and "velocidad" in aviso

    bonus = db.efecto_activo(criatura.id, "velocidad", T0)
    competidor = comp.competidor_de(criatura, comp.CARRERA, bonus)
    normal = comp.competidor_de(criatura, comp.CARRERA)

    assert competidor.base == normal.base + 6


def test_la_pocion_de_fuerza_no_ayuda_en_la_carrera():
    """Cada poción sirve donde dice: la de fuerza, en el sumo."""
    criatura = nacer()
    tienda.usar(criatura, obj.CATALOGO["fuerza_1d12"], T0, DadoFijo(12))

    assert db.efecto_activo(criatura.id, comp.STATS[comp.SUMO], T0) == 12
    assert db.efecto_activo(criatura.id, comp.STATS[comp.CARRERA], T0) == 0


def test_al_caducar_deja_de_ayudar():
    criatura = nacer()
    tienda.usar(criatura, obj.CATALOGO["fuerza_1d8"], T0, DadoFijo(8))
    tarde = T0 + timedelta(minutes=obj.MINUTOS_DE_EFECTO + 1)

    assert db.efecto_activo(criatura.id, "fuerza", tarde) == 0
    assert comp.competidor_de(criatura, comp.SUMO, 0).base == \
        comp.competidor_de(criatura, comp.SUMO).base


# --- Los otros objetos -----------------------------------------------------

def test_la_pocion_de_comida_llena_y_se_guarda():
    criatura = db.guardar(sim.avanzar(nacer(), T0))
    from dataclasses import replace
    db.guardar(replace(db.criatura_viva("u1", "g1"), hambre=12.0))
    hambrienta = db.criatura_viva("u1", "g1")
    assert hambrienta.hambre == 12.0

    tienda.usar(hambrienta, obj.CATALOGO["pocion_comida"], T0)

    assert db.criatura_viva("u1", "g1").hambre == 100.0


def test_el_silbato_deja_entrenar_otra_vez():
    criatura = nacer()
    db.poner_cooldown(criatura.id, sim.ENTRENAR, T0)
    assert db.espera_de(criatura.id, sim.ENTRENAR, T0).total_seconds() > 0

    tienda.usar(criatura, obj.CATALOGO["silbato"], T0)

    assert db.espera_de(criatura.id, sim.ENTRENAR, T0) == timedelta(0)


def test_el_descanso_solo_toca_el_de_competir():
    criatura = nacer()
    db.poner_cooldown(criatura.id, sim.COMPETIR, T0)
    db.poner_cooldown(criatura.id, sim.ENTRENAR, T0)

    tienda.usar(criatura, obj.CATALOGO["descanso_rapido"], T0)

    assert db.espera_de(criatura.id, sim.COMPETIR, T0) == timedelta(0)
    assert db.espera_de(criatura.id, sim.ENTRENAR, T0).total_seconds() > 0


# --- Los textos de los menús -----------------------------------------------

def test_la_mochila_vacia_manda_a_la_tienda():
    texto = tienda.texto_del_inventario("u1", "g1")
    assert "Tienda" in texto and str(obj.GEMAS_DE_BIENVENIDA) in texto


def test_la_mochila_cuenta_lo_que_hay():
    db.comprar("u1", "g1", obj.CATALOGO["silbato"])
    db.comprar("u1", "g1", obj.CATALOGO["silbato"])
    db.comprar("u1", "g1", obj.CATALOGO["pocion_comida"])

    texto = tienda.texto_del_inventario("u1", "g1")
    assert "×2" in texto and "Silbato del entrenador" in texto
    assert "Poción de comida" in texto


def test_la_tienda_dice_el_saldo():
    db.cobrar("u1", "g1", 40)
    assert str(obj.GEMAS_DE_BIENVENIDA - 40) in tienda.texto_de_la_tienda("u1", "g1")


def test_un_objeto_que_ya_no_existiera_no_rompe_la_mochila():
    """Si algún día se retira un objeto del catálogo, quien lo tuviera guardado
    no puede quedarse con la mochila rota."""
    with db.conectar() as con:
        con.execute(
            "INSERT INTO inventario (usuario_id, guild_id, objeto, cantidad) "
            "VALUES ('u1', 'g1', 'objeto_retirado', 3)"
        )
    texto = tienda.texto_del_inventario("u1", "g1")
    assert "objeto_retirado" not in texto
