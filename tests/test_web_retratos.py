import io
import logging
import urllib.parse

import pytest
from PIL import Image, ImageDraw

import especies as esp
import retrato

PNG = b"\x89PNG\r\n\x1a\n"
SIN_DIBUJO = sorted(set(esp.ESPECIES) - set(retrato.CON_ETAPAS_COMPLETAS))


@pytest.fixture(autouse=True)
def sin_memoria():
    retrato.olvidar()
    yield
    retrato.olvidar()


def pedir(cliente, especie, etapa="bebe", animo="feliz", sombrero="sin", v=None, **extra):
    v = retrato.version() if v is None else v
    return cliente.get(
        f"/gachamon/retrato/{especie}/{etapa}/{animo}/{sombrero}.png?v={v}", **extra)


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
    ("pollito", "bebe", "feliz", "tinte_rojo"), ("..", "bebe", "feliz", "sin"), ("%2E%2E", "bebe", "feliz", "sin"),
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
    assert "no_esta.png" in caplog.text


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


# --- La versión cubre fuentes y código --------------------------------------

def _versiones(tmp_path, monkeypatch, cambio):
    (tmp_path / "caras").mkdir(exist_ok=True)
    (tmp_path / "caras" / "a.png").write_bytes(b"a")
    codigo = tmp_path / "codigo.py"
    codigo.write_text("uno")
    monkeypatch.setattr(retrato, "FUENTES", tmp_path / ".")
    monkeypatch.setattr(retrato, "ARCHIVOS_DE_CODIGO", (codigo,))
    retrato.olvidar()
    antes = retrato.version()
    cambio(tmp_path, codigo)
    retrato.olvidar()
    return antes, retrato.version()


@pytest.mark.parametrize("cambio", [
    lambda d, c: (d / "caras" / "a.png").write_bytes(b"b"),
    lambda d, c: (d / "caras" / "nueva.png").write_bytes(b"a"),
    lambda d, c: (d / "caras" / "a.png").rename(d / "caras" / "z.png"),
    lambda d, c: c.write_text("dos"),
], ids=["cambia", "se_añade", "se_renombra", "cambia_el_codigo"])
def test_la_version_cambia_con_las_fuentes_y_con_el_codigo(tmp_path, monkeypatch, cambio):
    antes, despues = _versiones(tmp_path, monkeypatch, cambio)
    assert antes != despues


def test_el_codigo_que_decide_la_imagen_entra_en_la_huella():
    nombres = {p.name for p in retrato.ARCHIVOS_DE_CODIGO}
    assert nombres == {"retrato.py", "especies.py", "cosmeticos.py"}


# --- La ruta exige la versión vigente ---------------------------------------

@pytest.mark.parametrize("v", [None, "inventada", ""])
def test_sin_la_version_vigente_redirige_sin_componer(cliente, v):
    def no_debe_componer(*a):
        raise AssertionError("compuso con una versión que no es la vigente")

    ruta = "/gachamon/retrato/pollito/bebe/feliz/sin.png"
    url = ruta if v is None else f"{ruta}?v={v}"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(retrato, "armar", no_debe_componer)
        mp.setattr(retrato, "relleno", no_debe_componer)
        respuesta = cliente.get(url, follow_redirects=False)
    assert respuesta.status_code == 307
    assert respuesta.headers["location"] == f"{ruta}?v={retrato.version()}"
    assert "cache-control" not in respuesta.headers


@pytest.mark.parametrize("consulta", ["v={v}&x=1", "x=1&v={v}", "v={v}&v={v}", "v={v}&"])
def test_con_algo_mas_en_la_consulta_redirige_sin_componer(cliente, consulta):
    # Si no, cada `x` distinto se saltaría la caché del borde y obligaría a
    # componer el retrato otra vez.
    def no_debe_componer(*a):
        raise AssertionError("compuso con una consulta que no es la canónica")

    ruta = "/gachamon/retrato/pollito/bebe/feliz/sin.png"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(retrato, "armar", no_debe_componer)
        mp.setattr(retrato, "relleno", no_debe_componer)
        respuesta = cliente.get(
            f"{ruta}?{consulta.format(v=retrato.version())}", follow_redirects=False)
    assert respuesta.status_code == 307
    assert respuesta.headers["location"] == f"{ruta}?v={retrato.version()}"
    assert "cache-control" not in respuesta.headers


def test_la_redireccion_de_un_relleno_tambien_va_a_la_vigente(cliente):
    ruta = f"/gachamon/retrato/{SIN_DIBUJO[0]}/adulto/mal/sin.png"
    respuesta = cliente.get(f"{ruta}?v=x", follow_redirects=False)
    assert respuesta.status_code == 307
    assert respuesta.headers["location"] == f"{ruta}?v={retrato.version()}"


def test_lo_que_no_existe_es_404_aunque_la_version_sea_cualquiera(cliente):
    for v in ("inventada", retrato.version()):
        respuesta = cliente.get(
            f"/gachamon/retrato/dinosaurio/bebe/feliz/sin.png?v={v}", follow_redirects=False)
        assert respuesta.status_code == 404


def test_con_la_version_vigente_va_la_cabecera_de_un_año(cliente):
    respuesta = pedir(cliente, "pollito", follow_redirects=False)
    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_la_version_se_calcula_al_arrancar(tmp_path, monkeypatch):
    from ayudas_web import servicio

    retrato.olvidar()
    with servicio(tmp_path, monkeypatch):
        assert retrato.version.cache_info().currsize == 1


# --- olvidar ----------------------------------------------------------------

def test_olvidar_vacia_tambien_el_relleno_y_la_version():
    retrato.relleno(SIN_DIBUJO[0], "bebe", "feliz")
    retrato.version()
    assert retrato.relleno.cache_info().currsize and retrato.version.cache_info().currsize
    retrato.olvidar()
    assert retrato.relleno.cache_info().currsize == 0
    assert retrato.version.cache_info().currsize == 0


# --- La franja se lee -------------------------------------------------------

def _textos_dibujados(monkeypatch, especie):
    dibujados = []
    original = ImageDraw.ImageDraw.text

    def espia(self, xy, texto, *a, **k):
        dibujados.append((xy, texto, k.get("font")))
        return original(self, xy, texto, *a, **k)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", espia)
    retrato.olvidar()
    retrato.relleno(especie, "bebe", "feliz")
    return dibujados


@pytest.mark.parametrize("especie", SIN_DIBUJO)
def test_la_franja_es_ascii_y_cabe_en_el_lienzo(monkeypatch, especie):
    dibujados = _textos_dibujados(monkeypatch, especie)
    assert len(dibujados) == 2 and dibujados[1][1] == "RELLENO"
    medidor = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    for (x, _y), texto, letra in dibujados:
        assert texto.isascii(), texto
        assert x >= 0 and x + medidor.textlength(texto, font=letra) <= retrato.LADO_RELLENO
        assert letra.size >= 16
    assert dibujados[0][1] == urllib.parse.unquote(
        retrato._sin_tildes(esp.ESPECIES[especie].nombre).upper())
