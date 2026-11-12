import io
import logging

import pytest
from PIL import Image

import especies as esp
import retrato

PNG = b"\x89PNG\r\n\x1a\n"
SIN_DIBUJO = sorted(set(esp.ESPECIES) - set(retrato.CON_ETAPAS_COMPLETAS))


@pytest.fixture(autouse=True)
def sin_memoria():
    retrato.olvidar()
    yield
    retrato.olvidar()


def pedir(cliente, especie, etapa="bebe", animo="feliz", sombrero="sin"):
    return cliente.get(f"/gachamon/retrato/{especie}/{etapa}/{animo}/{sombrero}.png")


def test_una_especie_dibujada_trae_su_retrato(cliente):
    respuesta = pedir(cliente, "pollito", "adulto", "feliz", "corona")
    assert respuesta.status_code == 200 and respuesta.content.startswith(PNG)
    assert respuesta.headers["content-type"] == "image/png"
    assert respuesta.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert respuesta.content == retrato.armar("pollito", "adulto", "feliz", "corona")


def test_no_pide_sesion(cliente):
    cliente.cookies.clear()
    assert pedir(cliente, "pollito").status_code == 200


def test_hay_catorce_especies_sin_dibujo():
    assert len(SIN_DIBUJO) == 14


@pytest.mark.parametrize("especie", SIN_DIBUJO)
def test_una_especie_sin_dibujo_trae_un_relleno_que_se_ve(cliente, especie):
    respuesta = pedir(cliente, especie)
    assert respuesta.status_code == 200 and respuesta.content.startswith(PNG)
    imagen = Image.open(io.BytesIO(respuesta.content)).convert("RGBA")
    assert imagen.size == (256, 256)
    opacos = 256 * 256 - imagen.getchannel("A").histogram()[0]
    assert opacos > 256 * 256 * 0.1
    assert imagen.getpixel((0, 0))[3] == 0


def test_el_relleno_cambia_con_la_especie_la_etapa_y_el_animo():
    a, b = SIN_DIBUJO[0], SIN_DIBUJO[1]
    distintos = {
        retrato.relleno(a, "bebe", "feliz"), retrato.relleno(b, "bebe", "feliz"),
        retrato.relleno(a, "adulto", "feliz"), retrato.relleno(a, "bebe", "mal"),
    }
    assert len(distintos) == 4


def test_el_relleno_ignora_el_sombrero(cliente):
    assert pedir(cliente, SIN_DIBUJO[0], sombrero="corona").content == pedir(cliente, SIN_DIBUJO[0]).content


@pytest.mark.parametrize("partes", [
    ("dinosaurio", "bebe", "feliz", "sin"), ("pollito", "anciano", "feliz", "sin"),
    ("pollito", "bebe", "eufórico", "sin"), ("pollito", "bebe", "feliz", "casco"),
    ("pollito", "bebe", "feliz", "tinte_rojo"), ("..", "bebe", "feliz", "sin"),
])
def test_lo_que_no_existe_es_un_404(cliente, partes):
    respuesta = pedir(cliente, *partes)
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["clave"] == "no_existe"


def test_una_capa_que_falta_es_un_404_con_aviso_y_no_un_500(cliente, monkeypatch, caplog):
    cara = retrato.FUENTES / "caras" / retrato.CARAS["feliz"]
    ruta_cara = retrato._ruta_de_capa

    def sin_la_cara(carpeta, clave, archivo, forma):
        if carpeta == "caras" and archivo == retrato.CARAS["feliz"]:
            return retrato.FUENTES / "caras" / "no_esta.png"
        return ruta_cara(carpeta, clave, archivo, forma)

    assert cara.is_file()
    monkeypatch.setattr(retrato, "_ruta_de_capa", sin_la_cara)
    with caplog.at_level(logging.WARNING, logger="gachamones"):
        respuesta = pedir(cliente, "pollito", "bebe", "feliz", "sin")
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["clave"] == "no_existe"
    assert "pollito/bebe/feliz/sin" in caplog.text


def test_la_version_es_corta_estable_y_va_en_la_ficha(cliente, monkeypatch):
    from ayudas_web import con_gachamon, poner_reloj

    version = retrato.version()
    assert len(version) >= 8 and set(version) <= set("0123456789abcdef")
    assert retrato.version() == version
    poner_reloj(monkeypatch)
    gachamon = con_gachamon(cliente)["gachamon"]
    assert gachamon["retrato"] == (
        f"/gachamon/retrato/{gachamon['especie']}/bebe/{gachamon['cara']}/sin.png?v={version}"
    )
    assert cliente.get(gachamon["retrato"]).status_code == 200
