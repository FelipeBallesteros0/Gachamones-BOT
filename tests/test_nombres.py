"""Validación pura de los nombres visibles y los que se pone un recluta."""
import random

import pytest

import db
import especies as esp
import nombres
import simulacion as sim


# --- Los nombres que se pone un recluta -------------------------------------

def test_la_lista_de_nombres_de_recluta_vale():
    assert len(nombres.NOMBRES) == 40 > db.MAXIMO_PLANTEL + 1
    assert all(sim.normalizar_nombre(n) == n for n in nombres.NOMBRES)
    assert len({n.casefold() for n in nombres.NOMBRES}) == 40
    assert not {n.casefold() for n in nombres.NOMBRES} & {e.nombre.casefold() for e in esp.ESPECIES.values()}


def test_elegir_evita_los_que_ya_hay_sin_mirar_mayusculas():
    todos_menos_uno = [n.upper() for n in nombres.NOMBRES if n != "Trufa"]
    assert nombres.elegir(random.Random(7), todos_menos_uno) == "Trufa"
    assert nombres.elegir(random.Random(7), nombres.NOMBRES) in nombres.NOMBRES


def test_normaliza_nombres_unicode_y_espacios_internos():
    assert sim.normalizar_nombre("  Éowyn   del  Río  ") == "Éowyn del Río"
    assert sim.normalizar_nombre("O'Connor-Luz") == "O'Connor-Luz"
    assert sim.normalizar_nombre("星 の 子") == "星 の 子"
    assert sim.normalizar_nombre("A\u0301ngel D’Artagnan 2") == "A\u0301ngel D’Artagnan 2"


@pytest.mark.parametrize(
    ("nombre", "motivo"),
    [
        ("   ", "vacío"),
        ("a" * 25, "24"),
        ("Luna\nFalsa", "letras, números"),
        ("<@123456789012345678>", "letras, números"),
        ("<@!123456789012345678>", "letras, números"),
        ("<@&123456789012345678>", "letras, números"),
        ("<#123456789012345678>", "letras, números"),
        ("@everyone", "letras, números"),
        ("**Luna**", "letras, números"),
        ("```Luna```", "letras, números"),
        ("[Luna](https://x.co)", "letras, números"),
        ("||Luna||", "letras, números"),
        ("__Luna__", "letras, números"),
        ("~~Luna~~", "letras, números"),
    ],
)
def test_rechaza_nombres_que_rompen_o_suplantan_la_salida(nombre, motivo):
    with pytest.raises(ValueError, match=motivo):
        sim.normalizar_nombre(nombre)


def test_el_juego_ya_no_tiene_sin_nombre():
    """Todo gachamon tiene nombre: el que se lo pone su dueño o el que se pone
    él solo al unirse. Lo de «sin nombre» no puede volver."""
    assert not hasattr(sim, "NOMBRE_PENDIENTE")
    assert not hasattr(sim, "SIN_NOMBRE")
    assert not hasattr(sim, "esta_sin_nombrar")
    assert not hasattr(sim, "nombre_visible")
