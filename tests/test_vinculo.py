import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

import db
import vinculo

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (10, 10, 10, 10)
ANA, BETO = "111111111111111111", "222222222222222222"
G = "g"


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "vinculo.db")
    db.inicializar()


def test_el_codigo_mide_ocho_y_no_lleva_letras_que_se_confunden():
    codigo = vinculo.nuevo_codigo(random.Random(1))
    assert len(codigo) == vinculo.LARGO == 8
    assert set(codigo) <= set(vinculo.ALFABETO)
    assert not set("ILO01") & set(vinculo.ALFABETO)
    assert vinculo.nuevo_codigo(random.Random(1)) == codigo
    assert vinculo.nuevo_codigo() != vinculo.nuevo_codigo()


def test_normalizar_perdona_como_se_escribe_en_un_celular():
    assert vinculo.normalizar("  abcd-efgh ") == "ABCDEFGH"
    assert vinculo.normalizar("ab cd ef gh") == "ABCDEFGH"


def test_cada_resultado_de_un_canje_tiene_su_mensaje():
    assert set(vinculo.MENSAJES) == {
        vinculo.OK, vinculo.INVALIDO, vinculo.DEMASIADOS, vinculo.YA_VINCULADA,
    }
    assert all(len(texto) <= 2000 for texto in vinculo.MENSAJES.values())


def test_la_identidad_web_de_una_cuenta_es_su_numero_en_negativo():
    cuenta = db.crear_identidad_web(12, G, T0)
    assert cuenta == db.CuentaWeb(12, "-12", G, False)
    assert db.crear_identidad_web(12, G, T0 + timedelta(days=1)) == cuenta
    assert db.cuenta_web(12) == cuenta
    assert db.cuenta_web(99) is None


def test_canjear_un_codigo_vincula_la_cuenta_con_esa_persona_de_discord():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, T0) == vinculo.OK
    assert db.cuenta_web(12) == db.CuentaWeb(12, ANA, G, True)


def test_el_codigo_vale_escrito_con_minusculas_espacios_y_guiones():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    escrito = f" {codigo[:4].lower()}-{codigo[4:].lower()} "
    assert db.canjear_codigo_de_vinculo(escrito, ANA, G, T0) == vinculo.OK


def test_vale_hasta_un_segundo_antes_de_los_diez_minutos():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    justo_antes = T0 + timedelta(minutes=10) - timedelta(seconds=1)
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, justo_antes) == vinculo.OK


def test_a_los_diez_minutos_justos_ya_no_vale():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    a_los_diez = T0 + timedelta(minutes=10)
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, a_los_diez) == vinculo.INVALIDO
    assert db.cuenta_web(12) is None


def test_un_codigo_sirve_una_sola_vez():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, T0) == vinculo.OK
    assert db.canjear_codigo_de_vinculo(codigo, BETO, G, T0) == vinculo.INVALIDO


def test_pedir_otro_codigo_anula_el_anterior():
    viejo = db.pedir_codigo_de_vinculo(12, T0)
    nuevo = db.pedir_codigo_de_vinculo(12, T0 + timedelta(minutes=1))
    assert viejo != nuevo
    assert db.canjear_codigo_de_vinculo(viejo, ANA, G, T0 + timedelta(minutes=2)) == vinculo.INVALIDO
    assert db.canjear_codigo_de_vinculo(nuevo, ANA, G, T0 + timedelta(minutes=2)) == vinculo.OK


@pytest.mark.parametrize("basura", ["", "   ", "no-existe", "ñ" * 10_000, "'; DROP TABLE cuentas_web;--"])
def test_un_codigo_absurdo_es_invalido_y_no_rompe_nada(basura):
    db.pedir_codigo_de_vinculo(12, T0)
    assert db.canjear_codigo_de_vinculo(basura, ANA, G, T0) == vinculo.INVALIDO
    assert db.cuenta_web(12) is None


def test_una_persona_de_discord_no_puede_vincular_dos_cuentas():
    assert db.canjear_codigo_de_vinculo(db.pedir_codigo_de_vinculo(12, T0), ANA, G, T0) == vinculo.OK
    otro = db.pedir_codigo_de_vinculo(13, T0)
    assert db.canjear_codigo_de_vinculo(otro, ANA, G, T0) == vinculo.YA_VINCULADA
    assert db.cuenta_web(13) is None


def test_una_cuenta_ya_vinculada_no_puede_pedir_otro_codigo():
    db.canjear_codigo_de_vinculo(db.pedir_codigo_de_vinculo(12, T0), ANA, G, T0)
    with pytest.raises(vinculo.NoSePuede) as error:
        db.pedir_codigo_de_vinculo(12, T0)
    assert error.value.motivo == vinculo.YA_VINCULADA


def test_una_identidad_web_sin_gachamones_todavia_puede_vincularse():
    db.crear_identidad_web(12, G, T0)
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, T0) == vinculo.OK
    assert db.cuenta_web(12) == db.CuentaWeb(12, ANA, G, True)


def test_una_identidad_web_con_gachamones_ya_no_puede_pedir_codigo():
    cuenta = db.crear_identidad_web(12, G, T0)
    db.crear(cuenta.usuario_id, G, "pollito", "Pelusa", STATS, T0)
    with pytest.raises(vinculo.NoSePuede) as error:
        db.pedir_codigo_de_vinculo(12, T0)
    assert error.value.motivo == vinculo.CON_GACHAMONES


def test_si_el_gachamon_nace_entre_pedir_y_canjear_el_codigo_ya_no_sirve():
    cuenta = db.crear_identidad_web(12, G, T0)
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    db.crear(cuenta.usuario_id, G, "pollito", "Pelusa", STATS, T0)
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, T0) == vinculo.INVALIDO
    assert db.cuenta_web(12) == cuenta


def test_al_sexto_intento_en_diez_minutos_se_corta_aunque_el_codigo_sea_bueno():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    for _ in range(vinculo.INTENTOS_MAXIMOS):
        assert db.canjear_codigo_de_vinculo("MALMALMA", ANA, G, T0) == vinculo.INVALIDO
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, T0) == vinculo.DEMASIADOS
    assert db.canjear_codigo_de_vinculo(codigo, BETO, G, T0) == vinculo.OK


def test_pasada_la_ventana_se_puede_volver_a_intentar():
    for _ in range(vinculo.INTENTOS_MAXIMOS):
        db.canjear_codigo_de_vinculo("MALMALMA", ANA, G, T0)
    despues = T0 + vinculo.VENTANA_DE_INTENTOS + timedelta(seconds=1)
    codigo = db.pedir_codigo_de_vinculo(12, despues)
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, despues) == vinculo.OK


def test_dos_personas_canjeando_el_mismo_codigo_a_la_vez_solo_entra_una():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    with ThreadPoolExecutor(max_workers=2) as hilos:
        resultados = list(hilos.map(
            lambda quien: db.canjear_codigo_de_vinculo(codigo, quien, G, T0),
            (ANA, BETO),
        ))
    assert sorted(resultados) == sorted([vinculo.OK, vinculo.INVALIDO])
    assert db.cuenta_web(12).usuario_id in (ANA, BETO)
