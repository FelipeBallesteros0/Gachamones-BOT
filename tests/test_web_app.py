import os
import subprocess
import sys
from pathlib import Path

import pytest

import db
import economia
from ayudas_web import T0

RAIZ = Path(__file__).resolve().parent.parent


def test_la_salud_contesta(cliente):
    respuesta = cliente.get("/gachamon/api/salud")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True}


@pytest.mark.parametrize("ruta", ["/gachamon", "/gachamon/"])
def test_la_portada_se_sirve_sin_cache_y_con_la_version_puesta(cliente, ruta):
    respuesta = cliente.get(ruta)
    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]
    assert respuesta.headers["cache-control"] == "no-cache"
    assert "__V__" not in respuesta.text
    assert cliente.app.state.version in respuesta.text


def test_la_portada_pide_sus_archivos_con_rutas_absolutas(cliente):
    version = cliente.app.state.version
    texto = cliente.get("/gachamon/").text
    assert f'"/gachamon/static/{version}/estilo.css"' in texto
    assert f'"/gachamon/static/{version}/js/principal.js"' in texto


def test_sin_barra_redirige_a_la_portada(cliente):
    respuesta = cliente.get("/gachamon", follow_redirects=False)
    assert respuesta.status_code in (301, 302, 307, 308)
    assert respuesta.headers["location"].endswith("/gachamon/")


def test_los_estaticos_cuelgan_de_una_ruta_con_version(cliente):
    version = cliente.app.state.version
    assert len(version) >= 8 and set(version) <= set("0123456789abcdef")
    assert cliente.get(f"/gachamon/static/{version}/index.html").status_code == 200
    assert cliente.get("/gachamon/static/otra/index.html").status_code == 404


def test_la_version_sale_del_contenido_y_no_de_las_fechas(tmp_path):
    from web.app import calcular_version

    (tmp_path / "js").mkdir()
    (tmp_path / "a.css").write_text("a")
    (tmp_path / "js" / "b.js").write_text("b")
    antes = calcular_version(tmp_path)
    for archivo in tmp_path.rglob("*"):
        os.utime(archivo, (1, 1))
    assert calcular_version(tmp_path) == antes
    (tmp_path / "js" / "b.js").write_text("otro")
    assert calcular_version(tmp_path) != antes


@pytest.mark.parametrize("ruta", [
    "/", "/api/salud", "/docs", "/openapi.json", "/gachamon/docs",
    "/gachamon/openapi.json", "/gachamones",
])
def test_fuera_de_lo_suyo_no_hay_nada(cliente, ruta):
    assert cliente.get(ruta).status_code == 404


def test_poner_al_dia_crea_la_base_y_se_puede_repetir(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "nueva.db")
    economia.poner_al_dia(T0)
    segunda = economia.poner_al_dia(T0)
    assert (segunda.personas, segunda.piezas, segunda.gemas) == (0, 0, 0)
    assert economia.saldos("u", "g").asciigems == 50


def test_arrancar_el_servicio_hace_la_devolucion(tmp_path, monkeypatch):
    import ayudas_web

    monkeypatch.setattr(db, "RUTA", tmp_path / "juego.db")
    db.inicializar()
    with db.conectar() as con:
        db.guardar_en_el_ropero_en(con, "u", "g", "tinte_rojo")
    with ayudas_web.servicio(tmp_path, monkeypatch):
        pass
    assert economia.saldos("u", "g").asciigems == 70
    assert db.ropero("u", "g") == frozenset()


def test_el_bot_arranca_por_el_mismo_camino():
    fuente = (RAIZ / "bot.py").read_text(encoding="utf-8")
    assert "economia.poner_al_dia(" in fuente
    assert "db.inicializar()" not in fuente
    assert "devolver_cosmeticos_retirados" not in fuente


def test_la_web_no_arrastra_discord(tmp_path):
    entorno = {**os.environ, "RUTA_BD": str(tmp_path / "no-existe" / "x.db")}
    orden = "import sys, web.app; sys.exit(1 if 'discord' in sys.modules else 0)"
    hecho = subprocess.run(
        [sys.executable, "-c", orden], cwd=RAIZ, env=entorno,
        capture_output=True, text=True,
    )
    assert hecho.returncode == 0, hecho.stderr


def test_una_direccion_que_no_existe_contesta_con_clave(cliente):
    respuesta = cliente.get("/gachamon/api/no-hay-nada")
    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "detail": {"clave": "no_existe", "mensaje": "Eso no existe."},
    }


def test_un_verbo_que_no_toca_contesta_405_con_clave_y_allow(cliente):
    respuesta = cliente.post("/gachamon/api/salud")
    assert respuesta.status_code == 405
    assert respuesta.json()["detail"]["clave"] == "metodo"
    assert "GET" in respuesta.headers["allow"]


def test_un_error_con_su_propia_clave_la_conserva(cliente):
    respuesta = cliente.get("/gachamon/api/sesion")
    assert respuesta.status_code == 401
    assert respuesta.json()["detail"]["clave"] == "sin_sesion"


def test_el_prefijo_vive_en_el_paquete_y_la_app_lo_sigue_exponiendo():
    import web
    import web.app

    assert web.PREFIJO == "/gachamon" == web.app.PREFIJO
