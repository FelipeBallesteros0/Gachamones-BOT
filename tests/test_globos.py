import random
from dataclasses import replace
from datetime import datetime, timezone

import pytest

import especies as esp
import globos
import simulacion as sim
from web import pueblo

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
CLAVES = ("desfallecido", "hambre", "sucio", "aburrido", "suelta")


def criatura(especie="pulpo", genero=esp.HEMBRA, **barras) -> sim.Criatura:
    base = sim.Criatura(id=1, usuario_id="u", guild_id="g", especie=especie,
                        nombre="Tinta", nacida_en=T0, actualizada_en=T0, genero=genero)
    return replace(base, **barras)


def textos(c, tipo=None):
    return [g.texto for g in globos.de(c) if tipo in (None, g.tipo)]


def test_lo_comun_trae_frases_para_todo():
    assert set(globos.COMUNES) == set(CLAVES)
    assert all(len(globos.COMUNES[c]) >= 2 for c in CLAVES)
    assert len(globos.COMUNES["suelta"]) >= 4
    assert "¿Cómo estás?" in globos.COMUNES["suelta"]


def _sueltas():
    return [*globos.COMUNES["suelta"],
            *(f for propias in globos.PROPIAS.values() for f in propias.get("suelta", ()))]


@pytest.mark.parametrize("afirma", ["content", "qué bien", "aquí", "estamos", "me siento"])
def test_la_charla_no_afirma_un_estado_ni_un_lugar(afirma):
    # Las sueltas salen siempre, también con el ánimo en 41 o a la intemperie:
    # un globo no anuncia nada que no esté pasando.
    for frase in _sueltas():
        assert afirma not in frase.lower(), frase


def test_la_charla_del_pollito_sigue_siendo_suya():
    sueltas = globos.PROPIAS["pollito"]["suelta"]
    assert len(sueltas) >= 4 and all("pío" in f.lower() for f in sueltas)
    assert "¡Pío! ¿Cómo estás?" in sueltas


def test_contenta_y_cuidada_solo_charla():
    c = criatura(hambre=90, animo=90, limpieza=90)
    assert textos(c, globos.NECESIDAD) == []
    assert set(textos(c)) == set(esp.concordar(f, esp.HEMBRA) for f in globos.COMUNES["suelta"])


@pytest.mark.parametrize("barras, clave", [
    (dict(hambre=39.9), "hambre"), (dict(limpieza=39.9), "sucio"), (dict(animo=39.9), "aburrido"),
])
def test_por_debajo_de_cuarenta_pide_lo_que_le_falta(barras, clave):
    pedidas = textos(criatura(**barras), globos.NECESIDAD)
    assert set(pedidas) == set(esp.concordar(f, esp.HEMBRA) for f in globos.COMUNES[clave])


def test_justo_en_cuarenta_todavia_no_pide():
    assert textos(criatura(hambre=40.0, limpieza=40.0, animo=40.0), globos.NECESIDAD) == []


def test_con_la_comida_en_cero_esta_desfallecida_y_no_solo_con_hambre():
    pedidas = set(textos(criatura(hambre=0.0), globos.NECESIDAD))
    assert pedidas == set(esp.concordar(f, esp.HEMBRA) for f in globos.COMUNES["desfallecido"])


def test_las_necesidades_van_antes_que_la_charla():
    tipos = [g.tipo for g in globos.de(criatura(hambre=10, limpieza=10))]
    assert tipos == sorted(tipos, key=[globos.NECESIDAD, globos.SUELTA].index)
    assert globos.SUELTA in tipos


def test_una_muerta_no_dice_nada():
    assert globos.de(criatura(muerta_en=T0, causa_muerte="hambre")) == ()


def test_el_pollito_habla_a_su_manera_en_todo():
    assert set(globos.PROPIAS["pollito"]) == set(CLAVES)
    for barras in (dict(), dict(hambre=10), dict(hambre=0), dict(limpieza=10), dict(animo=10)):
        for texto in textos(criatura(especie="pollito", **barras)):
            assert "pío" in texto.lower(), texto


def test_lo_propio_manda_solo_en_la_clave_que_trae(monkeypatch):
    monkeypatch.setitem(globos.PROPIAS, "pulpo", {"sucio": ("Glub. Mis ocho brazos, pegajosos.",)})
    assert textos(criatura(limpieza=10), globos.NECESIDAD) == ["Glub. Mis ocho brazos, pegajosos."]
    assert set(textos(criatura(hambre=10), globos.NECESIDAD)) == set(
        esp.concordar(f, esp.HEMBRA) for f in globos.COMUNES["hambre"]
    )


@pytest.mark.parametrize("especie", sorted(esp.ESPECIES))
@pytest.mark.parametrize("genero", [esp.MACHO, esp.HEMBRA])
def test_ninguna_frase_llega_con_una_marca_sin_resolver(especie, genero):
    for barras in (dict(), dict(hambre=10, limpieza=10, animo=10), dict(hambre=0)):
        for globo in globos.de(criatura(especie=especie, genero=genero, **barras)):
            assert "{" not in globo.texto and "}" not in globo.texto, globo.texto
            assert 0 < len(globo.texto) <= 80


def test_macho_y_hembra_no_dicen_exactamente_lo_mismo():
    hembra = set(textos(criatura(genero=esp.HEMBRA, hambre=10, limpieza=10, animo=10)))
    macho = set(textos(criatura(genero=esp.MACHO, hambre=10, limpieza=10, animo=10)))
    assert hembra != macho


def test_elegir_prefiere_la_necesidad_y_no_se_repite():
    disponibles = globos.de(criatura(hambre=10))
    rng = random.Random(7)
    anterior = None
    for _ in range(30):
        elegido = globos.elegir(disponibles, anterior, rng)
        assert elegido.tipo == globos.NECESIDAD
        assert elegido.texto != anterior
        anterior = elegido.texto


def test_elegir_sin_nada_que_decir_o_con_una_sola_frase():
    assert globos.elegir((), None, random.Random(1)) is None
    unico = (globos.Globo(globos.SUELTA, "Hola."),)
    assert globos.elegir(unico, "Hola.", random.Random(1)) == unico[0]


def test_elegir_no_cae_a_la_charla_por_evitar_una_repeticion():
    una_necesidad = globos.Globo(globos.NECESIDAD, "Tengo hambre.")
    charla = (globos.Globo(globos.SUELTA, "Hola."), globos.Globo(globos.SUELTA, "Buenas."))
    assert globos.elegir((una_necesidad, *charla), "Tengo hambre.", random.Random(1)) == una_necesidad


def test_ningun_modulo_de_globos_importa_lo_prohibido():
    fuente = open(globos.__file__, encoding="utf-8").read()
    for prohibido in ("import discord", "import db", "import economia"):
        assert prohibido not in fuente


def test_hay_frases_para_los_nueve_lugares_y_solo_para_ellos():
    assert set(globos.DEL_LUGAR) == set(pueblo.LUGARES)
    assert all(len(frases) >= 2 for frases in globos.DEL_LUGAR.values())
    assert set(globos.PROPIAS_DEL_LUGAR["pollito"]) == set(pueblo.LUGARES)


def test_al_estar_en_un_lugar_dice_algo_de_ese_lugar():
    c = criatura(hambre=90, animo=90, limpieza=90)
    del_lugar = [g.texto for g in globos.de(c, "tienda") if g.tipo == globos.LUGAR]
    assert set(del_lugar) == set(esp.concordar(f, esp.HEMBRA) for f in globos.DEL_LUGAR["tienda"])
    assert [g for g in globos.de(c) if g.tipo == globos.LUGAR] == []
    assert [g for g in globos.de(c, "portal") if g.tipo == globos.LUGAR] == []


def test_el_orden_es_necesidad_lugar_y_charla():
    tipos = [g.tipo for g in globos.de(criatura(hambre=10), "plaza")]
    orden = [globos.NECESIDAD, globos.LUGAR, globos.SUELTA]
    assert tipos == sorted(tipos, key=orden.index) and set(tipos) == set(orden)


def test_el_pollito_habla_a_su_manera_en_cada_lugar():
    for lugar in pueblo.LUGARES:
        for g in globos.de(criatura(especie="pollito", hambre=90, animo=90, limpieza=90), lugar):
            if g.tipo == globos.LUGAR:
                assert "pío" in g.texto.lower(), g.texto


def test_una_muerta_tampoco_habla_del_lugar():
    assert globos.de(criatura(muerta_en=T0, causa_muerte="hambre"), "plaza") == ()


@pytest.mark.parametrize("lugar", sorted(globos.DEL_LUGAR))
@pytest.mark.parametrize("genero", [esp.MACHO, esp.HEMBRA])
def test_las_frases_de_lugar_llegan_resueltas_y_cortas(lugar, genero):
    for especie in ("pulpo", "pollito"):
        for g in globos.de(criatura(especie=especie, genero=genero), lugar):
            assert "{" not in g.texto and "}" not in g.texto and 0 < len(g.texto) <= 80


@pytest.mark.parametrize("prohibida", ["amigos", "todos", "alguien", "gente", "moneda", "gema", "ventana"])
def test_ninguna_frase_de_lugar_anuncia_lo_que_no_pasa(prohibida):
    todas = [f for frases in globos.DEL_LUGAR.values() for f in frases]
    todas += [f for por_lugar in globos.PROPIAS_DEL_LUGAR.values() for frases in por_lugar.values() for f in frases]
    assert not [f for f in todas if prohibida in f.lower()]


def test_las_frases_de_la_tienda_son_las_de_una_tienda_abierta():
    assert globos.DEL_LUGAR["tienda"] == (
        "Cuántas cosas hay en los estantes.", "Huele a madera y a pintura fresca.", "¿Me compras algo?",
    )
    assert globos.PROPIAS_DEL_LUGAR["pollito"]["tienda"] == ("Pío, cuántas cosas.", "Pío… huele a madera nueva.")
    frases = [f for fs in globos.DEL_LUGAR.values() for f in fs]
    frases += [f for lugares in globos.PROPIAS_DEL_LUGAR.values() for fs in lugares.values() for f in fs]
    assert not [f for f in frases if "vacíos" in f or "abrirá" in f]
