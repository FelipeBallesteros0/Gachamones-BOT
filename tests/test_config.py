"""Lectura del .env, sobre todo la lista de canales."""
import pytest

import config


def lista(valor, monkeypatch):
    monkeypatch.setenv("CANALES_PRUEBA", valor)
    return config._lista_enteros("CANALES_PRUEBA")


def test_un_solo_canal(monkeypatch):
    assert lista("123456789012345678", monkeypatch) == (123456789012345678,)


def test_varios_canales_separados_por_comas(monkeypatch):
    assert lista("111,222,333", monkeypatch) == (111, 222, 333)


def test_tolera_espacios_saltos_y_punto_y_coma(monkeypatch):
    """Es lo que sale al pegar varios IDs copiados de Discord a mano."""
    assert lista(" 111 , 222;333 ,\n444 ", monkeypatch) == (111, 222, 333, 444)


def test_ignora_comas_sobrantes(monkeypatch):
    assert lista(",111,,222,", monkeypatch) == (111, 222)


def test_quita_repetidos_conservando_el_orden(monkeypatch):
    """El primero es el canal principal, así que el orden importa."""
    assert lista("333,111,333,222", monkeypatch) == (333, 111, 222)


def test_vacio_da_lista_vacia(monkeypatch):
    assert lista("", monkeypatch) == ()
    monkeypatch.delenv("CANALES_PRUEBA", raising=False)
    assert config._lista_enteros("CANALES_PRUEBA") == ()


def test_un_valor_que_no_es_id_avisa_con_claridad(monkeypatch):
    """El error típico: pegar el nombre del canal en vez de su ID."""
    with pytest.raises(ValueError) as fallo:
        lista("111,#general", monkeypatch)
    assert "#general" in str(fallo.value)
    assert "CANALES_PRUEBA" in str(fallo.value)


def test_el_canal_principal_es_el_primero(monkeypatch):
    canales = lista("777,888", monkeypatch)
    assert canales[0] == 777


def test_el_modelo_razonador_va_el_ultimo_de_la_cadena():
    """Con 300 tokens devolvía el contenido vacío 4 de cada 4 veces: se gasta
    más de mil caracteres razonando en inglés antes de contestar. Sigue en la
    lista como tercer recambio, pero no puede ser el primero al que se cae."""
    razonador = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
    assert razonador in config.MODELOS_IA
    assert config.MODELOS_IA[-1] == razonador
    assert len(config.MODELOS_IA) == 3
