import copy
import json

import pytest

import casas
from web import pueblo

NUEVE = ("casa", "refugio", "incubadora", "tienda", "plaza", "barrio", "estadio", "cementerio", "aventura")


def test_el_archivo_es_el_del_boceto_y_no_tiene_problemas():
    datos = json.loads(pueblo.RUTA.read_text(encoding="utf-8"))
    assert datos == pueblo.DATOS
    assert (datos["ancho"], datos["alto"], datos["velocidad"], datos["hueco"]) == (690, 430, 115, 26)
    assert pueblo.problemas(datos) == []


def test_son_los_nueve_lugares_en_su_orden_con_su_parte():
    assert tuple(pueblo.LUGARES) == NUEVE
    assert [l.parte for l in pueblo.LUGARES.values()] == ["A"] * 4 + ["B"] * 5
    assert pueblo.LUGARES["casa"] == pueblo.Lugar("casa", "Tu casa", "A", pueblo.YA)
    assert pueblo.LUGARES["tienda"].abre == pueblo.PRONTO
    assert all(pueblo.LUGARES[c].abre == pueblo.DESPUES for c in NUEVE[4:])
    assert pueblo.DATOS["nodos"]["casa"] == [75, 330] and pueblo.DATOS["nodos"]["aventura"] == [640, 170]


@pytest.mark.parametrize("clave, vale", [
    ("plaza", True), ("portal", False), ("u1", False), ("", False), (None, False), (7, False), (["casa"], False),
])
def test_existe_solo_para_un_lugar_de_verdad(clave, vale):
    assert pueblo.existe(clave) is vale


def test_existe_consulta_lugares_en_el_momento(monkeypatch):
    monkeypatch.setattr(pueblo, "LUGARES", {"x": pueblo.Lugar("x", "X", "A", pueblo.YA)})
    assert pueblo.existe("x") is True
    assert pueblo.existe("casa") is False


def test_se_parte_del_hogar():
    assert pueblo.de_partida(casas.PROPIA) == "casa"
    assert pueblo.de_partida(casas.REFUGIO) == "refugio"
    assert pueblo.de_partida(casas.INTEMPERIE) == "refugio"


@pytest.mark.parametrize("clave, vinculada, hogar, frase", [
    ("estadio", True, casas.PROPIA, "Esto se abre más adelante. Por ahora se juega en Discord."),
    ("estadio", False, casas.PROPIA, "Esto se abre más adelante."),
    ("tienda", True, casas.REFUGIO, "Aquí todavía no hay nada que hacer. Abre pronto."),
    ("casa", False, casas.REFUGIO, "Todavía no tienes casa. Se compran en la tienda."),
    ("casa", False, casas.INTEMPERIE, "Todavía no tienes casa. Se compran en la tienda."),
    ("casa", True, casas.PROPIA, None),
    ("refugio", False, casas.REFUGIO, None),
])
def test_cada_lugar_avisa_lo_suyo(clave, vinculada, hogar, frase):
    assert pueblo.aviso(clave, vinculada, hogar) == frase


def _roto(cambio):
    datos = copy.deepcopy(pueblo.DATOS)
    cambio(datos)
    return pueblo.problemas(datos)


def test_los_datos_rotos_se_notan():
    assert _roto(lambda d: d["aristas"].append(["plaza", "fantasma"]))
    assert _roto(lambda d: d["nodos"].pop("tienda"))
    assert _roto(lambda d: d["nodos"].__setitem__("casa", [700, 330]))
    assert _roto(lambda d: d["nodos"].__setitem__("casa", [75, -1]))
    assert _roto(lambda d: d["lugares"]["plaza"].__setitem__("abre", "nunca"))
    assert _roto(lambda d: d["lugares"]["plaza"].__setitem__("parte", "C"))
    assert _roto(lambda d: d.__setitem__("velocidad", 0))
    assert _roto(lambda d: d.__setitem__("aristas", [a for a in d["aristas"] if "plaza" not in a]))


@pytest.mark.parametrize("clave", ["ancho", "alto", "velocidad", "hueco", "lugares", "nodos", "aristas"])
def test_una_clave_que_falta_es_un_problema_y_no_una_excepcion(clave):
    assert _roto(lambda d: d.pop(clave))


def test_cada_lugar_dice_como_se_va_hacia_el():
    assert {clave: lugar["hacia"] for clave, lugar in pueblo.DATOS["lugares"].items()} == {
        "casa": "a tu casa", "refugio": "al refugio", "incubadora": "a la incubadora",
        "tienda": "a la tienda", "plaza": "a la plaza", "barrio": "al barrio",
        "estadio": "al estadio", "cementerio": "al cementerio", "aventura": "a la aventura",
    }


@pytest.mark.parametrize("valor", [None, "", "   ", 7])
def test_un_lugar_sin_su_hacia_es_un_problema(valor):
    datos = json.loads(pueblo.RUTA.read_text(encoding="utf-8"))
    if valor is None:
        del datos["lugares"]["plaza"]["hacia"]
    else:
        datos["lugares"]["plaza"]["hacia"] = valor
    assert pueblo.problemas(datos)


@pytest.mark.parametrize("clave,hogar,vale", [
    ("casa", "refugio", True),
    ("casa", "intemperie", True),
    ("casa", "propia", False),
    ("refugio", "refugio", False),
    ("plaza", "intemperie", False),
    ("tienda", "refugio", False),
])
def test_sin_casa_es_estar_en_tu_casa_sin_tener_una(clave, hogar, vale):
    assert pueblo.sin_casa(clave, hogar) is vale
