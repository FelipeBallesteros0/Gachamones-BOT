import copy
import json
from dataclasses import replace

import pytest

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
    assert pueblo.LUGARES["tienda"].abre == pueblo.YA
    assert pueblo.LUGARES["incubadora"].abre == pueblo.YA
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


def test_el_aviso_de_un_lugar_ya_no_mira_el_hogar():
    assert pueblo.aviso("plaza") == "Esto se abre más adelante."
    assert pueblo.aviso("tienda") is None and pueblo.aviso("casa") is None and pueblo.de_partida() == "casa"


@pytest.mark.parametrize("clave, frase", [
    ("casa", None),
    ("refugio", "El refugio cerró. Ahora cada quien vive en su departamento."),
    ("incubadora", None),
    ("tienda", None),
    ("estadio", "Esto se abre más adelante."),
    ("aventura", "Esto se abre más adelante."),
])
def test_cada_lugar_avisa_lo_suyo(clave, frase):
    assert pueblo.aviso(clave) == frase


def test_un_lugar_que_abre_pronto_lo_avisa(monkeypatch):
    # Ya no queda ninguno así en el archivo, pero la regla sigue: se prueba con uno de mentira.
    monkeypatch.setitem(pueblo.LUGARES, "tienda", replace(pueblo.LUGARES["tienda"], abre=pueblo.PRONTO))
    assert pueblo.aviso("tienda") == "Aquí todavía no hay nada que hacer. Abre pronto."


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


def test_lo_que_ofrece_cada_lugar_son_lugares_del_archivo_y_solo_si_ya_abrieron(monkeypatch):
    assert set(pueblo.OFRECE) <= set(pueblo.LUGARES)
    assert pueblo.ofrece("tienda") == ("tienda",)
    assert pueblo.ofrece("casa") == ("departamento",)
    assert pueblo.ofrece("refugio") == () and pueblo.ofrece("estadio") == ()
    monkeypatch.setitem(pueblo.LUGARES, "tienda", replace(pueblo.LUGARES["tienda"], abre=pueblo.PRONTO))
    assert pueblo.ofrece("tienda") == ()


def test_ningun_lugar_ofrece_la_incubadora():
    # Con quién sales se elige en tu departamento: la Incubadora ya no se ofrece en ningún sitio.
    assert "incubadora" not in pueblo.OFRECE
    for clave in (*pueblo.LUGARES, "incubadora"):
        for sin_gachamon in (False, True):
            assert "incubadora" not in pueblo.ofrece(clave, sin_gachamon=sin_gachamon), clave
    assert pueblo.ofrece("incubadora") == ()


def test_quien_no_tiene_lugar_guardado_o_ya_no_existe_esta_en_su_casa():
    assert pueblo.donde_esta("tienda") == "tienda"
    for clave in (None, "", "no_existe", 7):
        assert pueblo.donde_esta(clave) == pueblo.de_partida() == "casa"


def test_aventura_ofrece_la_primera_solo_a_quien_no_tiene_gachamon():
    sin_cama = "Antes pon tu segunda cama en tu departamento: sin cama, nadie se queda contigo."
    # Llamadas como siempre, «Aventura» sigue cerrada: el dato no cambia.
    assert pueblo.LUGARES["aventura"].abre == pueblo.DESPUES
    assert pueblo.ofrece("aventura") == () and pueblo.aviso("aventura") == "Esto se abre más adelante."
    assert pueblo.ofrece("aventura", sin_gachamon=True) == ("aventura",)
    assert pueblo.aviso("aventura", sin_gachamon=True, cama_libre=False) == sin_cama
    assert pueblo.aviso("aventura", sin_gachamon=True, cama_libre=True) is None
    # A los demás lugares no les cambia nada.
    for clave in pueblo.LUGARES:
        if clave != "aventura":
            assert pueblo.ofrece(clave, sin_gachamon=True) == pueblo.ofrece(clave), clave
            for cama_libre in (False, True):
                assert pueblo.aviso(clave, sin_gachamon=True, cama_libre=cama_libre) == pueblo.aviso(clave)
