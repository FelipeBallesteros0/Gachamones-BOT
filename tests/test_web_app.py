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


def test_un_error_http_sin_forma_propia_no_filtra_su_texto(tmp_path, monkeypatch):
    import ayudas_web
    from fastapi import HTTPException

    with ayudas_web.servicio(tmp_path, monkeypatch) as cliente:
        @cliente.app.get("/gachamon/api/prueba-418")
        def _rara():
            raise HTTPException(status_code=418, detail="texto interno")

        respuesta = cliente.get("/gachamon/api/prueba-418")
    assert respuesta.status_code == 418
    assert respuesta.json() == {
        "detail": {"clave": "error", "mensaje": "Algo salió mal."},
    }
    assert "texto interno" not in respuesta.text


# --- Al arrancar se avisa de lo que falta en el .env --------------------------

def _avisos_al_arrancar(tmp_path, monkeypatch, caplog, *, clave, rowino, pueblo):
    import logging

    from fastapi.testclient import TestClient

    import ayudas_web
    import config
    from web.app import crear_app

    monkeypatch.setattr(db, "RUTA", tmp_path / "juego.db")
    monkeypatch.setattr(config, "ROWINO_SECRET_KEY", clave)
    monkeypatch.setattr(config, "RUTA_ROWINO_BD", tmp_path / "rowino.db")
    monkeypatch.setattr(config, "GUILD_WEB", pueblo)
    if rowino:
        ayudas_web.crear_rowino(tmp_path / "rowino.db")
    with caplog.at_level(logging.WARNING, logger="gachamones"):
        with TestClient(crear_app()):
            pass
    return [r for r in caplog.records if r.name == "gachamones" and r.levelno == logging.WARNING]


def test_bien_configurado_arranca_sin_avisos(tmp_path, monkeypatch, caplog):
    from ayudas_web import CLAVE, PUEBLO

    assert _avisos_al_arrancar(
        tmp_path, monkeypatch, caplog, clave=CLAVE, rowino=True, pueblo=PUEBLO,
    ) == []


@pytest.mark.parametrize("falta, variable", [
    ({"clave": ""}, "ROWINO_SECRET_KEY"),
    ({"rowino": False}, "RUTA_ROWINO_BD"),
    ({"pueblo": 0}, "GUILD_WEB"),
])
def test_al_arrancar_avisa_de_cada_cosa_que_falta(tmp_path, monkeypatch, caplog, falta, variable):
    from ayudas_web import CLAVE, PUEBLO

    bien = {"clave": CLAVE, "rowino": True, "pueblo": PUEBLO}
    avisos = _avisos_al_arrancar(tmp_path, monkeypatch, caplog, **{**bien, **falta})
    # Uno solo, de nivel `warning` (los `info` no salen con uvicorn), que dice
    # qué variable del .env es.
    assert len(avisos) == 1
    assert variable in avisos[0].getMessage()


def test_con_todo_mal_avisa_de_las_tres(tmp_path, monkeypatch, caplog):
    avisos = _avisos_al_arrancar(tmp_path, monkeypatch, caplog, clave="", rowino=False, pueblo=0)
    assert len(avisos) == 3
    for variable in ("ROWINO_SECRET_KEY", "RUTA_ROWINO_BD", "GUILD_WEB"):
        assert any(variable in r.getMessage() for r in avisos), variable


def test_el_aviso_nunca_escribe_la_clave(tmp_path, monkeypatch, caplog):
    secreta = "la-clave-que-no-se-escribe"
    avisos = _avisos_al_arrancar(tmp_path, monkeypatch, caplog, clave=secreta, rowino=False, pueblo=0)
    assert len(avisos) == 2
    assert secreta not in caplog.text


# --- Un tope para el cuerpo, antes de mirar la cookie -------------------------

DEMASIADO = {"detail": {"clave": "demasiado", "mensaje": "Eso es demasiado grande."}}
CON_CUERPO = [("PUT", "/gachamon/api/avatar"), ("POST", "/gachamon/api/bautizar"),
              ("POST", "/gachamon/api/cuidar")]


@pytest.mark.parametrize("metodo, ruta", CON_CUERPO)
@pytest.mark.parametrize("con_cookie", [False, True], ids=["anonimo", "con_cookie"])
def test_un_cuerpo_de_17_kib_da_413(cliente, metodo, ruta, con_cookie):
    from ayudas_web import ESCRIBIR, entrar

    if con_cookie:
        entrar(cliente, 1)
    respuesta = cliente.request(metodo, ruta, content=b"x" * (17 * 1024),
                                headers={**ESCRIBIR, "Content-Type": "application/json"})
    assert respuesta.status_code == 413
    assert respuesta.json() == DEMASIADO


@pytest.mark.parametrize("declarado", [
    "abc", "", "-1", "1e3", str(16 * 1024 + 1), "9" * 5000, "0" * 5000 + "16385",
], ids=["letras", "vacio", "negativo", "exponente", "uno_mas", "cinco_mil_cifras", "ceros_delante"])
def test_un_content_length_que_no_es_un_numero_o_se_pasa_da_413(cliente, declarado):
    from ayudas_web import ESCRIBIR

    respuesta = cliente.post("/gachamon/api/cuidar", content=b"{}",
                             headers={**ESCRIBIR, "Content-Length": declarado,
                                      "Content-Type": "application/json"})
    assert respuesta.status_code == 413 and respuesta.json() == DEMASIADO


def test_un_content_length_que_miente_por_lo_bajo_tambien_se_corta(cliente):
    from ayudas_web import ESCRIBIR

    respuesta = cliente.post("/gachamon/api/bautizar", content=b"x" * (17 * 1024),
                             headers={**ESCRIBIR, "Content-Length": "10",
                                      "Content-Type": "application/json"})
    assert respuesta.status_code == 413 and respuesta.json() == DEMASIADO


def test_un_cuerpo_normal_pasa_y_el_tope_justo_tambien(cliente, monkeypatch):
    from ayudas_web import ESCRIBIR, con_gachamon, poner_reloj

    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    normal = cliente.post("/gachamon/api/cuidar", headers=ESCRIBIR,
                          json={"accion": "limpiar", "evento_id": "evento-normal"})
    assert normal.status_code == 200
    # Justo 16 KiB no se pasa: llega a la ruta, que dice lo suyo del nombre.
    relleno = b'{"nombre": "' + b"a" * (16 * 1024 - 14) + b'"}'
    assert len(relleno) == 16 * 1024
    justo = cliente.post("/gachamon/api/bautizar", content=relleno,
                         headers={**ESCRIBIR, "Content-Type": "application/json"})
    assert justo.status_code != 413


def _pedir_a_trozos(app, ruta, trozos):
    """Una petición troceada y sin `Content-Length`, hablando ASGI a pelo.

    Devuelve el estado, el cuerpo de la respuesta y cuántos trozos se leyeron.
    """
    import asyncio
    import json

    pendientes = [{"type": "http.request", "body": t, "more_body": True} for t in trozos]
    pendientes[-1]["more_body"] = False
    leidos = []
    enviados = []

    async def recibir():
        if pendientes:
            leidos.append(pendientes.pop(0))
            return leidos[-1]
        return {"type": "http.disconnect"}

    async def enviar(mensaje):
        enviados.append(mensaje)

    alcance = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "POST", "scheme": "http", "path": ruta, "raw_path": ruta.encode(),
        "root_path": "", "query_string": b"", "client": ("prueba", 1),
        "server": ("prueba", 80),
        "headers": [(b"host", b"prueba"), (b"content-type", b"application/json"),
                    (b"x-gachamon", b"1"), (b"transfer-encoding", b"chunked")],
    }
    asyncio.run(app(alcance, recibir, enviar))
    inicio = next(m for m in enviados if m["type"] == "http.response.start")
    cuerpo = b"".join(m.get("body", b"") for m in enviados if m["type"] == "http.response.body")
    return inicio["status"], json.loads(cuerpo), len(leidos)


def test_un_cuerpo_troceado_se_corta_en_cuanto_se_pasa(tmp_path, monkeypatch):
    import ayudas_web

    with ayudas_web.servicio(tmp_path, monkeypatch) as cliente:
        estado, cuerpo, leidos = _pedir_a_trozos(
            cliente.app, "/gachamon/api/cuidar", [b"x" * (6 * 1024)] * 5)
    assert estado == 413 and cuerpo == DEMASIADO
    # Seis, doce, dieciocho: al tercero ya se pasa, y los otros dos no se leen.
    assert leidos == 3


# --- Las cabeceras de toda respuesta ----------------------------------------------

SIEMPRE = {"x-content-type-options": "nosniff",
           "content-security-policy": "frame-ancestors 'none'"}


def _lleva_siempre(respuesta):
    return all(respuesta.headers.get(k) == v for k, v in SIEMPRE.items())


@pytest.mark.parametrize("ruta, estado", [
    ("/gachamon/api/salud", 200),
    ("/gachamon/api/sesion", 401),
    ("/gachamon/api/no-hay-nada", 404),
])
def test_lo_de_la_api_no_se_guarda_en_ninguna_cache(cliente, ruta, estado):
    respuesta = cliente.get(ruta)
    assert respuesta.status_code == estado
    assert respuesta.headers["cache-control"] == "no-store"
    assert _lleva_siempre(respuesta)


def test_el_413_tambien_lleva_sus_cabeceras(cliente):
    respuesta = cliente.post("/gachamon/api/cuidar", content=b"x" * (17 * 1024))
    assert respuesta.status_code == 413
    assert respuesta.headers["cache-control"] == "no-store" and _lleva_siempre(respuesta)


def test_un_500_tambien_lleva_sus_cabeceras(tmp_path, monkeypatch):
    import ayudas_web
    from fastapi.testclient import TestClient

    with ayudas_web.servicio(tmp_path, monkeypatch) as cliente:
        @cliente.app.get("/gachamon/api/prueba-500")
        def _rota():
            raise RuntimeError("se rompió")

        sin_trampa = TestClient(cliente.app, raise_server_exceptions=False)
        respuesta = sin_trampa.get("/gachamon/api/prueba-500")
        version = cliente.app.state.version
    assert respuesta.status_code == 500
    assert respuesta.headers["cache-control"] == "no-store" and _lleva_siempre(respuesta)
    assert respuesta.headers["x-gachamon-version"] == version


@pytest.mark.parametrize("ruta, estado", [
    ("/gachamon/api/salud", 200),
    ("/gachamon/api/sesion", 401),
    ("/gachamon/api/no-hay-nada", 404),
])
def test_lo_de_la_api_dice_de_que_version_es_el_servidor(cliente, ruta, estado):
    respuesta = cliente.get(ruta)
    assert respuesta.status_code == estado
    assert respuesta.headers["x-gachamon-version"] == cliente.app.state.version


def test_el_413_tambien_dice_la_version(cliente):
    respuesta = cliente.post("/gachamon/api/cuidar", content=b"x" * (17 * 1024))
    assert respuesta.status_code == 413
    assert respuesta.headers["x-gachamon-version"] == cliente.app.state.version


@pytest.mark.parametrize("ruta", ["/gachamon/", "/", "/gachamon/static/otra/index.html"])
def test_fuera_de_la_api_tambien_van_las_de_siempre(cliente, ruta):
    respuesta = cliente.get(ruta)
    assert _lleva_siempre(respuesta)
    assert respuesta.headers.get("cache-control") != "no-store"


def test_los_estaticos_llevan_las_de_siempre(cliente):
    version = cliente.app.state.version
    respuesta = cliente.get(f"/gachamon/static/{version}/js/principal.js")
    assert respuesta.status_code == 200 and _lleva_siempre(respuesta)


def test_un_retrato_conserva_su_cache_de_un_año(cliente):
    import retrato

    respuesta = cliente.get(f"/gachamon/retrato/pollito/bebe/feliz/sin.png?v={retrato.version()}")
    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert _lleva_siempre(respuesta)


def test_otro_sitio_no_recibe_permiso_para_escribir(cliente):
    # Fija la defensa contra otros sitios: no hay CORS, así que una pregunta
    # previa del navegador no recibe ninguna cabecera que le abra la puerta.
    respuesta = cliente.options("/gachamon/api/cuidar", headers={
        "Origin": "https://otro-sitio.example", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "x-gachamon, content-type",
    })
    assert not [k for k in respuesta.headers if k.lower().startswith("access-control-")]
