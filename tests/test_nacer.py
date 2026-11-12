import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import especies as esp
import nacer

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "nacer.db")
    db.inicializar()


def test_del_huevo_sale_una_de_las_diez_con_nombre_provisional():
    nacida = nacer.romper_el_huevo("u", "g", T0, random.Random(3))
    especie = esp.ESPECIES[nacida.especie]
    assert especie.peso > 0
    assert nacida.nombre == especie.nombre and nacer.espera_nombre(nacida)
    assert nacida.activa and nacida.viva and nacida.nivel == 1
    assert db.criatura_activa("u", "g").id == nacida.id


def test_el_mismo_azar_da_el_mismo_gachamon():
    a = nacer.romper_el_huevo("a", "g", T0, random.Random(5))
    b = nacer.romper_el_huevo("b", "g", T0, random.Random(5))
    assert (a.especie, a.genero, a.caracter, a.base_fuerza, a.base_ingenio) == (
        b.especie, b.genero, b.caracter, b.base_fuerza, b.base_ingenio)


def test_el_huevo_es_solo_el_de_partida():
    nacer.romper_el_huevo("u", "g", T0)
    with pytest.raises(nacer.YaTieneGachamon):
        nacer.romper_el_huevo("u", "g", T0)
    assert len(db.plantel("u", "g")) == 1


def test_con_uno_en_la_incubadora_tampoco_hay_huevo():
    primero = nacer.romper_el_huevo("u", "g", T0)
    db.guardar(replace(primero, muerta_en=T0, causa_muerte="hambre"))
    db.crear("u", "g", "pulpo", "Tinta", (10, 10, 10, 10), T0, activa=False)
    with pytest.raises(nacer.YaTieneGachamon):
        nacer.romper_el_huevo("u", "g", T0)


def test_cuando_se_le_murio_el_unico_puede_sacar_otro():
    nacer.romper_el_huevo("d", "g", T0)
    otro = nacer.romper_el_huevo("d", "g", T0 + timedelta(days=5))
    assert otro.viva and len(db.plantel("d", "g")) == 1


def test_dos_huevos_a_la_vez_dejan_un_gachamon():
    def romper(_):
        try:
            return nacer.romper_el_huevo("u", "g", T0)
        except nacer.YaTieneGachamon:
            return None

    with ThreadPoolExecutor(max_workers=2) as hilos:
        nacidos = [n for n in hilos.map(romper, range(2)) if n]
    assert len(nacidos) == 1 and len(db.plantel("u", "g")) == 1


def test_bautizar_le_pone_nombre_una_vez():
    nacer.romper_el_huevo("u", "g", T0)
    assert nacer.bautizar("u", "g", "  Pelusa  ", T0).nombre == "Pelusa"
    assert db.criatura_activa("u", "g").nombre == "Pelusa"
    with pytest.raises(nacer.NoSePuedeBautizar):
        nacer.bautizar("u", "g", "Otra", T0)


@pytest.mark.parametrize("malo", ["", "   ", "<b>x</b>", "x" * 25, "Pelu🙂"])
def test_un_nombre_que_no_vale_no_bautiza(malo):
    nacida = nacer.romper_el_huevo("u", "g", T0)
    with pytest.raises(ValueError):
        nacer.bautizar("u", "g", malo, T0)
    assert db.criatura_activa("u", "g").nombre == nacida.nombre


def test_sin_gachamon_no_hay_a_quien_bautizar():
    with pytest.raises(nacer.NoSePuedeBautizar):
        nacer.bautizar("nadie", "g", "Pelusa", T0)


def test_no_nace_un_huerfano_si_la_cuenta_se_vinculo_mientras_tanto():
    import identidad

    web = db.crear_identidad_web(12, "g", T0).usuario_id
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    assert db.canjear_codigo_de_vinculo(codigo, "111111111111111111", "g", T0) == "ok"
    with pytest.raises(nacer.YaNoEsSuIdentidad):
        nacer.romper_el_huevo(web, "g", T0)
    assert not db.tiene_gachamones(web, "g")
    assert identidad.es_web(web)


def test_una_identidad_web_vigente_si_puede_nacer():
    web = db.crear_identidad_web(12, "g", T0).usuario_id
    assert nacer.romper_el_huevo(web, "g", T0).usuario_id == web


def test_el_bot_rompe_el_huevo_por_el_mismo_camino():
    from pathlib import Path

    fuente = (Path(__file__).resolve().parent.parent / "cogs" / "mascota.py").read_text(encoding="utf-8")
    assert "nacer.romper_el_huevo(" in fuente
    assert "esp.tirar_stats_iniciales" not in fuente


def test_cuenta_vigente_solo_va_por_nombre():
    with pytest.raises(TypeError):
        db.crear("u", "g", "pulpo", "Tinta", (10, 10, 10, 10), T0, esp.MACHO,
                 "sereno", None, True, False, True)


def test_bautizar_no_toca_al_recluta_de_la_incubadora():
    nacida = nacer.romper_el_huevo("u", "g", T0)
    nacer.bautizar("u", "g", "Pelusa", T0)
    recluta = db.crear("u", "g", "pulpo", "", (10, 10, 10, 10), T0, activa=False)
    with pytest.raises(nacer.NoSePuedeBautizar) as caido:
        nacer.bautizar("u", "g", "Otra", T0)
    assert caido.value.motivo == "ya_bautizado"
    assert db.por_id(recluta.id).nombre == ""
    assert db.por_id(nacida.id).nombre == "Pelusa"


def test_bautizar_no_toca_al_de_otra_persona():
    nacer.romper_el_huevo("a", "g", T0)
    ajena = nacer.romper_el_huevo("b", "g", T0)
    nacer.bautizar("a", "g", "Pelusa", T0)
    assert db.criatura_activa("b", "g").nombre == ajena.nombre
