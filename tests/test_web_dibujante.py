"""La api del dibujante: el permiso en cada ruta, las piezas, subir, volver atrás, el
historial, el avance que lee el tablero del arte del sitio y la copia de lo subido.

Los PNG se fabrican aquí; nunca se toca el arte del repo ni la carpeta de lo subido de
verdad (cada prueba tiene la suya).
"""
import asyncio
import builtins
import gc
import io
import json
import random
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import pytest
from PIL import Image

import arte_subido
import config
import db
from ayudas_web import ESCRIBIR, T0, crear_rowino_con_permisos, entrar, galleta, poner_reloj, servicio
from web import arte, dibujante

API = "/monsteropolis_dibujante/api"
INVENTADA = f"{API}/ruta-inventada"
CORAZON = "efectos/corazon.png"    # 32 × 32
ESTRELLA = "efectos/estrella.png"  # 32 × 32
SOMBRA = "efectos/sombra.png"      # 32 × 32
SUELO = "pieza/suelo.png"          # se sube a 1024 × 512 y el juego sirve 512 × 256
MACETA = "pieza/muebles/maceta-se.png"  # se sube a 1024 × 1536 y el juego sirve 512 × 768
LIMITE = 24 * 1024 * 1024
# Las cuentas del contrato: de dónde salen, en un solo sitio.
CAPAS_DE_CRIATURAS = 5030   # 4 250 de forma, 750 de especie y 30 comunes
GRUPOS = 85                 # 59 de siempre, 25 especies y lo común
GRUPOS_CON_TARJETA = 84     # lo común se sube pero no está en el avance
CASILLAS_POR_ESPECIE = 170
PULPO = "criaturas/pulpo"

# (id, usuario, bloqueada, arte_access, is_admin)
CUENTAS = ((1, "dibuja", 0, 1, 0), (2, "admin", 0, 0, 1), (3, "nadie", 0, 0, 0), (4, "bloqueado", 1, 1, 1))
DIBUJA, ADMIN, NADIE, BLOQUEADO, NO_EXISTE = 1, 2, 3, 4, 99

NO_SE_ENTIENDE = {"detail": {"clave": "peticion", "mensaje": "La petición no se entiende."}}
IMAGEN_DEMASIADO_GRANDE = {"detail": {"clave": "demasiado", "mensaje": "La imagen pesa más de 24 MB."}}
CUERPO_DEMASIADO_GRANDE = {"detail": {"clave": "demasiado", "mensaje": "Eso es demasiado grande."}}


def _permisos(tmp_path, monkeypatch, con_arte_access: bool = True) -> None:
    """La base de Rowino con las columnas del permiso (o, como las de antes, sin `arte_access`)."""
    ruta = tmp_path / ("permisos.db" if con_arte_access else "permisos-sin-arte-access.db")
    if not ruta.exists():
        crear_rowino_con_permisos(ruta, CUENTAS, con_arte_access=con_arte_access)
    monkeypatch.setattr(config, "RUTA_ROWINO_BD", ruta)


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    lugar = tmp_path / "arte_subido"
    monkeypatch.setattr(config, "RUTA_ARTE_SUBIDO", lugar)
    return lugar


@pytest.fixture
def cliente(tmp_path, monkeypatch, carpeta):
    """El servicio, con la cuenta que tiene `arte_access` dentro y el reloj en `T0`."""
    with servicio(tmp_path, monkeypatch) as cliente:
        _permisos(tmp_path, monkeypatch)
        poner_reloj(monkeypatch)
        entrar(cliente, DIBUJA)
        yield cliente


@pytest.fixture
def provisional_barato(monkeypatch):
    """Para lo que sólo mira la estructura o el permiso: el provisional sale tal como está en el
    repo, sin ampliarlo (ampliar los 270 de `provisionales.zip` tarda unos segundos)."""
    monkeypatch.setattr(dibujante, "_el_provisional", lambda lugar: dibujante._el_provisional_servido(lugar).read_bytes())


def png(ancho: int, alto: int, semilla: int = 0) -> bytes:
    """Un PNG RGBA de ruido, siempre el mismo para la misma semilla."""
    imagen = Image.frombytes("RGBA", (ancho, alto), random.Random(semilla).randbytes(ancho * alto * 4))
    salida = io.BytesIO()
    imagen.save(salida, "PNG")
    return salida.getvalue()


def nombre_limpio(cuerpo: bytes, ruta: str) -> str:
    """El nombre con que queda guardado lo que se sube: el de su PNG limpio."""
    return arte_subido.preparar(cuerpo, arte.lugar_de(ruta))[1].nombre


def nombre_original(cuerpo: bytes, ruta: str) -> str:
    """El nombre con que queda guardado el original (el que sube el dibujante, ya limpio)."""
    return arte_subido.preparar(cuerpo, arte.lugar_de(ruta))[0].nombre


def direccion(cuerpo: bytes, ruta: str) -> str:
    return f"/monsteropolis/arte-subido/{nombre_limpio(cuerpo, ruta)}"


def subir(cliente, ruta, cuerpo, cabeceras=ESCRIBIR):
    return cliente.post(f"{API}/subir", params={"ruta": ruta}, content=cuerpo,
                        headers={**cabeceras, "Content-Type": "image/png"})


def volver(cliente, ruta, a):
    return cliente.post(f"{API}/volver", json={"ruta": ruta, "a": a}, headers=ESCRIBIR)


def historial(cliente, ruta):
    return cliente.get(f"{API}/historial", params={"ruta": ruta})


def renglones() -> int:
    with db.conectar() as con:
        return con.execute("SELECT COUNT(*) FROM arte_subido").fetchone()[0]


def nada_guardado(carpeta) -> bool:
    return renglones() == 0 and (not carpeta.exists() or not any(carpeta.iterdir()))


def como_una_ruta_que_no_existe(cliente, respuesta) -> None:
    inventada = cliente.get(INVENTADA)
    assert inventada.status_code == 404
    assert (respuesta.status_code, respuesta.content) == (404, inventada.content)
    assert respuesta.headers == inventada.headers


# --- El permiso, en cada ruta ---------------------------------------------------

RUTAS = {
    "piezas": lambda c: c.get(f"{API}/piezas"),
    "subir": lambda c: subir(c, CORAZON, png(32, 32)),
    "volver": lambda c: volver(c, CORAZON, "provisional"),
    "historial": lambda c: historial(c, CORAZON),
    "avance": lambda c: c.get(f"{API}/avance"),
    "copia": lambda c: c.get(f"{API}/copia.zip"),
    "provisional": lambda c: c.get(f"{API}/provisional", params={"ruta": CORAZON}),
    "provisionales": lambda c: c.get(f"{API}/provisionales.zip"),
    "piezas_de_un_grupo": lambda c: c.get(f"{API}/piezas", params={"grupo": "efectos"}),
    "copia_de_un_grupo": lambda c: c.get(f"{API}/copia.zip", params={"grupo": "efectos"}),
    "provisionales_de_un_grupo": lambda c: c.get(f"{API}/provisionales.zip", params={"grupo": "efectos"}),
}
DEMAS = ["sin_sesion", "cookie_falsa", "sin_permiso", "bloqueada", "no_existe", "sin_la_columna"]


@pytest.mark.usefixtures("provisional_barato")
@pytest.mark.parametrize("ruta", RUTAS)
def test_el_dibujante_y_el_admin_entran_en_cada_ruta(cliente, ruta):
    for uid in (DIBUJA, ADMIN):
        entrar(cliente, uid)
        assert RUTAS[ruta](cliente).status_code == 200


@pytest.mark.usefixtures("provisional_barato")
@pytest.mark.parametrize("ruta", RUTAS)
@pytest.mark.parametrize("quien", DEMAS)
def test_a_los_demas_cada_ruta_les_contesta_como_una_que_no_existe(
        cliente, tmp_path, monkeypatch, carpeta, ruta, quien):
    if quien == "sin_sesion":
        cliente.cookies.clear()
    elif quien == "cookie_falsa":
        cliente.cookies.set("session", galleta(DIBUJA, clave="otra-clave"))
    elif quien == "sin_la_columna":
        # Una base de Rowino de antes del permiso: sin `arte_access`, nadie lo tiene por esa vía.
        _permisos(tmp_path, monkeypatch, con_arte_access=False)
    else:
        entrar(cliente, {"sin_permiso": NADIE, "bloqueada": BLOQUEADO, "no_existe": NO_EXISTE}[quien])
    como_una_ruta_que_no_existe(cliente, RUTAS[ruta](cliente))
    assert nada_guardado(carpeta)
    # La misma petición, con el permiso, sí llega.
    _permisos(tmp_path, monkeypatch)
    entrar(cliente, DIBUJA)
    assert RUTAS[ruta](cliente).status_code == 200


# Un cuerpo de `volver` de más de 16 KiB y uno que no se entiende.
VOLVER_RAROS = (b" " * (16 * 1024 + 1), b"{")


def volver_con(cliente, cuerpo):
    return cliente.post(f"{API}/volver", content=cuerpo,
                        headers={**ESCRIBIR, "Content-Type": "application/json"})


def test_a_los_demas_se_les_contesta_sin_mirar_la_cabecera_ni_el_cuerpo(cliente, carpeta):
    entrar(cliente, NADIE)
    sin_cabecera = cliente.post(f"{API}/subir", params={"ruta": CORAZON}, content=png(32, 32))
    como_una_ruta_que_no_existe(cliente, sin_cabecera)
    sin_cabecera = cliente.post(f"{API}/volver", json={"ruta": CORAZON, "a": "provisional"})
    como_una_ruta_que_no_existe(cliente, sin_cabecera)
    grande = subir(cliente, CORAZON, b"\0" * (LIMITE + 1))
    como_una_ruta_que_no_existe(cliente, grande)
    for cuerpo in VOLVER_RAROS:
        como_una_ruta_que_no_existe(cliente, volver_con(cliente, cuerpo))
    assert nada_guardado(carpeta)
    # Al dibujante, en cambio, sí se le mira la cabecera y se le cuenta lo que manda.
    entrar(cliente, DIBUJA)
    assert cliente.post(f"{API}/subir", params={"ruta": CORAZON}, content=png(32, 32)).status_code == 403
    assert subir(cliente, CORAZON, b"\0" * (LIMITE + 1)).status_code == 413
    assert [volver_con(cliente, cuerpo).status_code for cuerpo in VOLVER_RAROS] == [413, 422]


def _subir_a_trozos(app, trozos, uid=DIBUJA, declarado=None, se_corta=False, ruta=CORAZON):
    """Una subida hablando ASGI a pelo, troceada o con un `Content-Length` dicho a mano.
    Con `se_corta`, quien sube se va antes del último trozo.

    Devuelve el estado, el cuerpo de la respuesta y cuántos trozos se leyeron.
    """
    pendientes = [{"type": "http.request", "body": t, "more_body": True} for t in trozos]
    pendientes[-1]["more_body"] = se_corta
    leidos, enviados = [], []

    async def recibir():
        if pendientes:
            leidos.append(pendientes.pop(0))
            return leidos[-1]
        return {"type": "http.disconnect"}

    async def enviar(mensaje):
        enviados.append(mensaje)

    cabeceras = [(b"host", b"prueba"), (b"content-type", b"image/png"), (b"x-gachamon", b"1"),
                 (b"cookie", f"session={galleta(uid)}".encode())]
    if declarado is None:
        cabeceras.append((b"transfer-encoding", b"chunked"))
    else:
        cabeceras.append((b"content-length", str(declarado).encode()))
    camino = f"{API}/subir"
    alcance = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "POST", "scheme": "http", "path": camino, "raw_path": camino.encode(),
        "root_path": "", "query_string": f"ruta={ruta}".encode(), "client": ("prueba", 1),
        "server": ("prueba", 80), "headers": cabeceras,
    }
    asyncio.run(app(alcance, recibir, enviar))
    inicio = next(m for m in enviados if m["type"] == "http.response.start")
    cuerpo = b"".join(m.get("body", b"") for m in enviados if m["type"] == "http.response.body")
    return inicio["status"], json.loads(cuerpo), len(leidos)


def test_a_los_demas_no_se_les_lee_ni_un_trozo_del_cuerpo(cliente, carpeta):
    estado, cuerpo, leidos = _subir_a_trozos(cliente.app, [b"\0" * 1024] * 3, uid=NADIE)
    assert (estado, cuerpo["detail"]["clave"], leidos) == (404, "no_existe", 0)
    assert nada_guardado(carpeta)
    # Lo mismo, del dibujante, se lee entero y se mira.
    estado, cuerpo, leidos = _subir_a_trozos(cliente.app, [b"\0" * 1024] * 3)
    assert (estado, cuerpo["detail"]["mensaje"], leidos) == (400, "El archivo no es un PNG.", 3)


# --- El avance: el contrato con el tablero del arte ------------------------------

CLAVE_DEL_CONTRATO = re.compile(r"[a-z0-9/_-]{1,64}")
FAMILIAS = {"avatar", "pieza", "iconos", "pueblo", "lugares", "escenas", "efectos", "criaturas"}


def test_el_avance_sigue_siendo_el_contrato_del_diseno_campo_por_campo(cliente):
    respuesta = cliente.get(f"{API}/avance")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/json"
    cuerpo = respuesta.json()
    assert list(cuerpo) == ["grupos"]
    grupos = cuerpo["grupos"]
    # `{"grupos": []}` valdría para el tablero, pero aquí no puede salir: siempre hay grupos.
    assert isinstance(grupos, list) and grupos
    for grupo in grupos:
        assert set(grupo) == {"clave", "nombre", "familia", "total", "hechas"}
        assert isinstance(grupo["clave"], str) and CLAVE_DEL_CONTRATO.fullmatch(grupo["clave"])
        assert not grupo["clave"].endswith(".png")
        assert isinstance(grupo["nombre"], str) and grupo["nombre"].strip()
        assert grupo["familia"] in FAMILIAS
        assert type(grupo["total"]) is int and type(grupo["hechas"]) is int
        assert 0 <= grupo["hechas"] <= grupo["total"]
    claves = [g["clave"] for g in grupos]
    assert len(set(claves)) == len(claves)
    assert grupos == [
        {"clave": g.clave, "nombre": g.nombre, "familia": g.familia, "total": len(g.casillas), "hechas": 0}
        for g in arte.grupos() if g.con_tarjeta
    ]


def test_el_avance_no_abre_ninguna_imagen(cliente, carpeta, monkeypatch):
    for ruta, cuerpo in ((CORAZON, png(32, 32, 1)), (ESTRELLA, png(32, 32, 2)), (SUELO, png(1024, 512)),
                         (f"{PULPO}/cara-feliz-se.png", png(1024, 1024, 3)),
                         ("criaturas/comun/sombrero-laurel-so.png", png(1024, 1024, 4))):
        assert subir(cliente, ruta, cuerpo).status_code == 200
    assert volver(cliente, ESTRELLA, "provisional").status_code == 200
    # Lo que la tabla tiene y ya no se sirve no cuenta: una medida que el contrato
    # ya no pide y una pieza que ya no está en él.
    db.subir_arte(SOMBRA, "0" * 64 + ".png", 31, 31, "dibuja", T0)
    db.subir_arte("efectos/ya-no-esta.png", "1" * 64 + ".png", 32, 32, "dibuja", T0)
    # Sin las imágenes en disco y sin poder abrir ninguna: el avance no las necesita.
    shutil.rmtree(carpeta)

    def prohibido(*_, **__):
        raise AssertionError("el avance abrió una imagen")

    abrir = builtins.open

    def abrir_sin_imagenes(archivo, *argumentos, **opciones):
        if str(archivo).endswith(".png"):
            prohibido()
        return abrir(archivo, *argumentos, **opciones)

    monkeypatch.setattr(Image, "open", prohibido)
    monkeypatch.setattr(builtins, "open", abrir_sin_imagenes)
    monkeypatch.setattr(io, "open", abrir_sin_imagenes)
    respuesta = cliente.get(f"{API}/avance")
    assert respuesta.status_code == 200
    avance = {g["clave"]: (g["hechas"], g["total"]) for g in respuesta.json()["grupos"]}
    assert avance["efectos"] == (1, 4)
    assert avance["pieza/paredes-y-suelo"] == (1, 3)
    # La de la especie cubre las cinco etapas de Octopul; la común, las de las 25 especies.
    assert avance[PULPO] == (5 + 5, CASILLAS_POR_ESPECIE)
    assert avance["criaturas/dragoncito"] == (5, CASILLAS_POR_ESPECIE)
    assert sum(hechas for hechas, _ in avance.values()) == 2 + 10 + 24 * 5


# --- Las rutas de pieza que no son del contrato ---------------------------------

RARAS = [
    "efectos/no-hay.png", "../efectos/corazon.png", "efectos/../efectos/corazon.png",
    "/efectos/corazon.png", "efectos/corazon", "efectos\\corazon.png", "", "efectos/corazon.png/..",
    "EFECTOS/CORAZON.PNG", "efectos/corazon.png\x00", "pieza/muebles/cama", "../../tamagotchi.db",
]


@pytest.mark.parametrize("ruta", RARAS)
def test_una_ruta_que_no_es_una_pieza_del_contrato_da_404(cliente, carpeta, ruta):
    for respuesta in (subir(cliente, ruta, png(32, 32)), volver(cliente, ruta, "provisional"),
                      volver(cliente, ruta, "anterior"), historial(cliente, ruta)):
        como_una_ruta_que_no_existe(cliente, respuesta)
    assert nada_guardado(carpeta)
    assert historial(cliente, CORAZON).status_code == 200


def test_la_ruta_de_la_pieza_se_mira_antes_de_leer_el_cuerpo(cliente, carpeta):
    estado, cuerpo, leidos = _subir_a_trozos(cliente.app, [b"\0" * 1024] * 3, ruta="efectos/no-hay.png")
    assert (estado, cuerpo["detail"]["clave"], leidos) == (404, "no_existe", 0)
    assert nada_guardado(carpeta)


# --- Subir y volver atrás, de punta a punta --------------------------------------

def test_subir_y_volver_atras_de_punta_a_punta(cliente, carpeta, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    v1, v2 = png(32, 32, 1), png(32, 32, 2)
    d1, d2 = direccion(v1, CORAZON), direccion(v2, CORAZON)

    hecho = subir(cliente, CORAZON, v1)
    assert hecho.status_code == 200
    assert hecho.json() == {
        "ruta": CORAZON, "ancho": 32, "alto": 32,
        "subida": {"direccion": d1, "original": d1, "quien": "dibuja", "cuando": T0.isoformat()},
        "medida_cambiada": None, "objeto": None, "estado": None, "miniatura": None, "criatura": None,
        "cubierta": None,
    }
    assert (carpeta / nombre_limpio(v1, CORAZON)).is_file()
    piezas = {p["ruta"]: p for g in cliente.get(f"{API}/piezas").json()["grupos"] for p in g.get("piezas", ())}
    assert piezas[CORAZON] == hecho.json()

    reloj.pasar(minutes=5)
    segunda = reloj.ahora
    entrar(cliente, ADMIN)
    hecho = subir(cliente, CORAZON, v2)
    assert hecho.status_code == 200
    assert hecho.json()["subida"] == {"direccion": d2, "original": d2, "quien": "admin", "cuando": segunda.isoformat()}

    reloj.pasar(minutes=5)
    entrar(cliente, DIBUJA)
    hecho = volver(cliente, CORAZON, "anterior")
    assert hecho.status_code == 200
    # Se ve otra vez la primera: quién la subió y cuándo.
    assert hecho.json()["subida"] == {"direccion": d1, "original": d1, "quien": "dibuja", "cuando": T0.isoformat()}
    vuelta = reloj.ahora

    reloj.pasar(minutes=5)
    entrar(cliente, ADMIN)
    hecho = volver(cliente, CORAZON, "provisional")
    assert hecho.status_code == 200
    assert hecho.json() == {
        "ruta": CORAZON, "ancho": 32, "alto": 32, "subida": None, "medida_cambiada": None,
        "objeto": None, "estado": None, "miniatura": None, "criatura": None, "cubierta": None}

    al_provisional = reloj.ahora

    # Desde el provisional, «anterior» lo deshace: vuelve a la última subida.
    reloj.pasar(minutes=5)
    deshecho = reloj.ahora
    hecho = volver(cliente, CORAZON, "anterior")
    assert hecho.status_code == 200
    assert hecho.json()["subida"] == {"direccion": d2, "original": d2, "quien": "admin", "cuando": segunda.isoformat()}

    # Una pieza sin nada subido no tiene anterior: se dice por qué y no cambia nada.
    no = volver(cliente, ESTRELLA, "anterior")
    assert no.status_code == 400
    assert no.json() == {"detail": {"clave": "no_vale", "mensaje": "No hay una imagen anterior."}}
    assert historial(cliente, ESTRELLA).json() == {"ruta": ESTRELLA, "historial": []}

    def renglon(accion, dire, quien, cuando):
        medida = (32, 32) if dire else (None, None)
        return {"accion": accion, "direccion": dire, "original": dire, "ancho": medida[0],
                "alto": medida[1], "quien": quien, "cuando": cuando.isoformat()}

    respuesta = historial(cliente, CORAZON)
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ruta": CORAZON, "historial": [
        renglon("anterior", d2, "admin", deshecho),
        renglon("provisional", None, "admin", al_provisional),
        renglon("anterior", d1, "dibuja", vuelta),
        renglon("subir", d2, "admin", segunda),
        renglon("subir", d1, "dibuja", T0),
    ]}
    # Lo que se guarda de quien sube o vuelve es su nombre, nunca su número de cuenta.
    with db.conectar() as con:
        assert {f["quien"] for f in con.execute("SELECT quien FROM arte_subido")} == {"dibuja", "admin"}


def test_en_la_familia_de_la_pieza_la_medida_servida_se_rechaza_y_la_de_subida_se_guarda_con_su_chica(
        cliente, carpeta):
    servida = png(512, 256)
    respuesta = subir(cliente, SUELO, servida)
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detail": {
        "clave": "no_vale", "mensaje": "La imagen mide 512 × 256 px y esta pieza pide 1024 × 512 px."}}
    assert nada_guardado(carpeta)
    exacta = png(1024, 512)
    vista = subir(cliente, SUELO, exacta).json()
    assert (vista["ancho"], vista["alto"]) == (1024, 512)
    original, chica = arte_subido.preparar(exacta, arte.lugar_de(SUELO))
    assert vista["subida"]["direccion"] == f"/monsteropolis/arte-subido/{chica.nombre}"
    assert vista["subida"]["original"] == f"/monsteropolis/arte-subido/{original.nombre}"
    # Lo vigente con la medida de subida se ve y se guarda sin cambiar un píxel, con su chica.
    with Image.open(carpeta / original.nombre) as guardada:
        assert guardada.size == (1024, 512)
        assert guardada.convert("RGBA").tobytes() == Image.open(io.BytesIO(exacta)).convert("RGBA").tobytes()
    with Image.open(carpeta / chica.nombre) as guardada:
        assert guardada.size == (512, 256)
    en_la_lista = {x["ruta"]: x for g in cliente.get(f"{API}/piezas").json()["grupos"] for x in g.get("piezas", ())}
    assert en_la_lista[SUELO] == vista


@pytest.mark.parametrize("cuerpo, mensaje", [
    (b"esto no es un png", "El archivo no es un PNG."),
    (png(31, 32), "La imagen mide 31 × 32 px y esta pieza pide 32 × 32 px."),
    (png(32, 32)[:-12], "El PNG está dañado o incompleto."),
], ids=["no_es_png", "otra_medida", "cortado"])
def test_lo_que_no_vale_se_rechaza_diciendo_por_que_y_no_cambia_nada(cliente, carpeta, cuerpo, mensaje):
    respuesta = subir(cliente, CORAZON, cuerpo)
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detail": {"clave": "no_vale", "mensaje": mensaje}}
    assert nada_guardado(carpeta)


def test_subir_y_volver_piden_la_cabecera_del_juego(cliente, carpeta):
    for respuesta in (cliente.post(f"{API}/subir", params={"ruta": CORAZON}, content=png(32, 32)),
                      cliente.post(f"{API}/volver", json={"ruta": CORAZON, "a": "provisional"})):
        assert respuesta.status_code == 403
        assert respuesta.json()["detail"]["clave"] == "sin_cabecera"
    assert nada_guardado(carpeta)


@pytest.mark.parametrize("cuerpo", [
    b"", b"no es json", b"\xff", b"[]", b'"provisional"', pytest.param(b"[" * 16000, id="anidado"),
    b'{"ruta": "efectos/corazon.png"}', b'{"a": "provisional"}',
    b'{"ruta": "efectos/corazon.png", "a": "siguiente"}', b'{"ruta": 3, "a": "provisional"}',
    b'{"ruta": "efectos/corazon.png", "a": ["provisional"]}',
])
def test_volver_con_un_cuerpo_que_no_se_entiende_da_422(cliente, carpeta, cuerpo):
    respuesta = cliente.post(f"{API}/volver", content=cuerpo,
                             headers={**ESCRIBIR, "Content-Type": "application/json"})
    assert respuesta.status_code == 422 and respuesta.json() == NO_SE_ENTIENDE
    assert nada_guardado(carpeta)


# --- Lo que pesa demasiado se corta al leer --------------------------------------

def test_una_imagen_de_mas_de_24_mb_da_413_y_no_cambia_nada(cliente, carpeta):
    respuesta = subir(cliente, CORAZON, b"\0" * (LIMITE + 1))
    assert respuesta.status_code == 413 and respuesta.json() == IMAGEN_DEMASIADO_GRANDE
    assert nada_guardado(carpeta)


def test_justo_24_mb_llega_a_mirarse(cliente, carpeta):
    respuesta = subir(cliente, CORAZON, b"\0" * LIMITE)
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"]["mensaje"] == "El archivo no es un PNG."


def test_un_cuerpo_troceado_se_corta_en_cuanto_pasa_de_24_mb(cliente, carpeta):
    estado, cuerpo, leidos = _subir_a_trozos(cliente.app, [b"\0" * (10 * 1024 * 1024)] * 5)
    assert (estado, cuerpo) == (413, IMAGEN_DEMASIADO_GRANDE)
    # Diez, veinte, treinta: al tercero ya se pasa, y los otros dos no se leen.
    assert leidos == 3
    assert nada_guardado(carpeta)


@pytest.mark.parametrize("declarado", [LIMITE + 1, "9" * 5000, "abc"], ids=["uno_mas", "cinco_mil_cifras", "letras"])
def test_un_content_length_de_mas_se_contesta_sin_leer_nada(cliente, carpeta, declarado):
    estado, cuerpo, leidos = _subir_a_trozos(cliente.app, [b"\0" * 1024], declarado=declarado)
    assert (estado, cuerpo, leidos) == (413, IMAGEN_DEMASIADO_GRANDE, 0)
    assert nada_guardado(carpeta)


def test_si_quien_sube_se_va_a_medias_no_se_guarda_nada_ni_es_un_fallo_del_servicio(cliente, carpeta):
    estado, cuerpo, leidos = _subir_a_trozos(cliente.app, [png(32, 32)[:100]] * 2, se_corta=True)
    # Los dos trozos que llegaron, y después la desconexión.
    assert (estado, cuerpo["detail"]["clave"], leidos) == (400, "error", 2)
    assert nada_guardado(carpeta)


def test_volver_con_un_cuerpo_de_mas_de_16_kib_da_413(cliente, carpeta):
    respuesta = cliente.post(f"{API}/volver", content=b" " * (16 * 1024 + 1),
                             headers={**ESCRIBIR, "Content-Type": "application/json"})
    assert respuesta.status_code == 413 and respuesta.json() == CUERPO_DEMASIADO_GRANDE
    assert nada_guardado(carpeta)


# --- Los lugares de la pieza, subidos al doble --------------------------------------

def _vista_de(cliente, ruta) -> dict:
    return {p["ruta"]: p for g in cliente.get(f"{API}/piezas").json()["grupos"] for p in g.get("piezas", ())}[ruta]


def _bloque_de_la_portada(cliente) -> dict:
    texto = cliente.get("/monsteropolis/").text
    return json.loads(re.search(r'<script type="application/json" id="arte-subido">(.*?)</script>', texto, re.S).group(1))


def test_subir_un_mueble_al_doble_lo_deja_al_dia_y_la_portada_sirve_la_chica(cliente, carpeta):
    cuerpo = png(1024, 1536)
    vista = subir(cliente, MACETA, cuerpo).json()
    original, chica = arte_subido.preparar(cuerpo, arte.lugar_de(MACETA))
    assert (original.ancho, original.alto, chica.ancho, chica.alto) == (1024, 1536, 512, 768)
    assert (vista["ancho"], vista["alto"], vista["medida_cambiada"]) == (1024, 1536, None)
    assert vista["subida"]["direccion"] == f"/monsteropolis/arte-subido/{chica.nombre}"
    assert vista["subida"]["original"] == f"/monsteropolis/arte-subido/{original.nombre}"
    assert sorted(p.name for p in carpeta.iterdir()) == sorted([original.nombre, chica.nombre])
    avance = {g["clave"]: g["hechas"] for g in cliente.get(f"{API}/avance").json()["grupos"]}
    assert avance["pieza/muebles/maceta"] == 1
    # El juego sirve la de 512 × 768.
    assert _bloque_de_la_portada(cliente) == {MACETA: f"/monsteropolis/arte-subido/{chica.nombre}"}


def test_una_fila_sin_original_se_sigue_viendo_y_cuenta_como_pendiente(cliente, carpeta):
    # Una subida de antes de publicar el doble: sólo el archivo servido, de 512 × 768.
    db.subir_arte(MACETA, "a" * 64 + ".png", 512, 768, "dibuja", T0)
    assert _bloque_de_la_portada(cliente) == {MACETA: f"/monsteropolis/arte-subido/{'a' * 64}.png"}
    vista = _vista_de(cliente, MACETA)
    assert vista["subida"] is None
    assert vista["medida_cambiada"] == {"ancho": 512, "alto": 768}
    avance = {g["clave"]: g["hechas"] for g in cliente.get(f"{API}/avance").json()["grupos"]}
    assert avance["pieza/muebles/maceta"] == 0


def test_la_vista_pide_la_medida_de_subida(cliente):
    medidas = {SUELO: (1024, 512), "pieza/pared-izquierda.png": (512, 1280), MACETA: (1024, 1536),
               "pieza/muebles/fuente-ne.png": (2048, 2048), CORAZON: (32, 32)}
    for ruta, medida in medidas.items():
        vista = _vista_de(cliente, ruta)
        assert (vista["ancho"], vista["alto"]) == medida


def test_el_413_dice_24_mb(cliente, carpeta):
    respuesta = subir(cliente, MACETA, b"\0" * (LIMITE + 1))
    assert respuesta.status_code == 413
    assert respuesta.json()["detail"]["mensaje"] == "La imagen pesa más de 24 MB."
    assert nada_guardado(carpeta)


def test_una_subida_de_la_medida_chica_se_rechaza_y_no_deja_renglon_ni_archivo(cliente, carpeta):
    respuesta = subir(cliente, MACETA, png(512, 768))
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"]["mensaje"] == \
        "La imagen mide 512 × 768 px y esta pieza pide 1024 × 1536 px."
    assert nada_guardado(carpeta)


# --- Las piezas, el historial y la copia ----------------------------------------

def test_las_piezas_van_por_grupos_con_su_medida_y_lo_que_se_ve_hoy(cliente):
    subido = subir(cliente, SUELO, png(1024, 512)).json()
    # Lo subido con una medida que el contrato ya no pide no se sirve (se ve el
    # recuadro), y la pieza lo dice con la medida de lo subido.
    db.subir_arte(CORAZON, "0" * 64 + ".png", 31, 31, "dibuja", T0)
    respuesta = cliente.get(f"{API}/piezas")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert list(cuerpo) == ["grupos"]
    assert [(g["clave"], g["nombre"], g["familia"], g["total"], g["hechas"]) for g in cuerpo["grupos"]] == [
        (g.clave, g.nombre, g.familia, len(g.casillas), 1 if g.clave in ("pieza/paredes-y-suelo",) else 0)
        for g in arte.grupos()]
    # Las criaturas llegan sin sus capas: se piden por grupo.
    assert all(("piezas" in g) == (g["familia"] != "criaturas") for g in cuerpo["grupos"])
    assert [p["ruta"] for g in cuerpo["grupos"] for p in g.get("piezas", ())] == [
        r for g in arte.grupos() if g.familia != "criaturas" for r in g.rutas]
    piezas = {p["ruta"]: p for g in cuerpo["grupos"] for p in g.get("piezas", ())}
    for lugar in arte.lugares():
        if lugar.familia == "criaturas":
            continue
        vista = piezas[lugar.ruta]
        assert set(vista) == {"ruta", "ancho", "alto", "subida", "medida_cambiada", "objeto", "estado",
                              "miniatura", "criatura", "cubierta"}
        assert (vista["ancho"], vista["alto"]) == (lugar.ancho, lugar.alto)
    assert piezas[SUELO] == subido
    assert [ruta for ruta, vista in piezas.items() if vista["subida"] is not None] == [SUELO]
    assert piezas[CORAZON]["subida"] is None
    assert piezas[CORAZON]["medida_cambiada"] == {"ancho": 31, "alto": 31}
    assert [ruta for ruta, vista in piezas.items() if vista["medida_cambiada"] is not None] == [CORAZON]


def test_la_medida_cambiada_se_va_al_subir_una_de_la_medida_de_hoy_o_al_volver_al_provisional(cliente):
    db.subir_arte(CORAZON, "0" * 64 + ".png", 31, 31, "dibuja", T0)
    db.subir_arte(ESTRELLA, "1" * 64 + ".png", 31, 31, "dibuja", T0)
    hecho = subir(cliente, CORAZON, png(32, 32))
    assert hecho.status_code == 200 and hecho.json()["medida_cambiada"] is None
    assert hecho.json()["subida"] is not None
    hecho = volver(cliente, ESTRELLA, "provisional")
    assert hecho.status_code == 200
    assert (hecho.json()["subida"], hecho.json()["medida_cambiada"]) == (None, None)


def test_la_lista_de_piezas_abre_las_mismas_conexiones_con_pocas_o_muchas_piezas_subidas(cliente, monkeypatch):
    # Cada conexión de `db.conectar` vive hasta que pasa el recolector: una por pieza
    # subida llegó a agotar los descriptores del servicio.
    conectar, abiertas = db.conectar, []

    def contando():
        abiertas.append(1)
        return conectar()

    monkeypatch.setattr(db, "conectar", contando)

    def conexiones_de_una_lista():
        abiertas.clear()
        assert cliente.get(f"{API}/piezas").status_code == 200
        return len(abiertas)

    piezas = arte.piezas()
    for indice, pieza in enumerate(piezas[:3]):
        db.subir_arte(pieza.ruta, f"{indice:064x}.png", pieza.ancho, pieza.alto, "dibuja", T0)
    pocas = conexiones_de_una_lista()
    for indice, pieza in enumerate(piezas[3:150], start=3):
        db.subir_arte(pieza.ruta, f"{indice:064x}.png", pieza.ancho, pieza.alto, "dibuja", T0)
    muchas = conexiones_de_una_lista()
    assert muchas == pocas <= 3
    vistas = [p for g in cliente.get(f"{API}/piezas").json()["grupos"] for p in g.get("piezas", ())]
    assert sum(p["subida"] is not None for p in vistas) == 150


def test_si_una_subida_se_cruza_entre_las_lecturas_no_se_mezclan_dos_imagenes(cliente, monkeypatch):
    assert subir(cliente, CORAZON, png(32, 32, 1)).status_code == 200
    # Como si otra subida hubiera cambiado la imagen entre leer lo vigente y leer quién
    # la subió: no se enseña la dirección de una con el nombre de quien subió la otra.
    otra = ("f" * 64 + ".png", "otra persona", T0)
    monkeypatch.setattr(db, "quien_subio_lo_puesto", lambda: {CORAZON: otra})
    piezas = {p["ruta"]: p for g in cliente.get(f"{API}/piezas").json()["grupos"] for p in g.get("piezas", ())}
    assert piezas[CORAZON]["subida"] is None


def test_el_historial_de_una_pieza_sin_nada_esta_vacio(cliente):
    respuesta = historial(cliente, CORAZON)
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ruta": CORAZON, "historial": []}


@pytest.fixture
def temporales(monkeypatch):
    """Los archivos que abre `tempfile.TemporaryFile` en la prueba: la copia se arma en
    uno (sin nombre en disco: nunca en memoria) y se cierra al acabar la respuesta."""
    crear, abiertos = tempfile.TemporaryFile, []

    def anotando(*argumentos, **opciones):
        abiertos.append(crear(*argumentos, **opciones))
        return abiertos[-1]

    monkeypatch.setattr(tempfile, "TemporaryFile", anotando)
    return abiertos


def test_la_copia_trae_lo_vigente_con_su_ruta_del_contrato(cliente, carpeta, temporales):
    vacia = cliente.get(f"{API}/copia.zip")
    assert vacia.status_code == 200
    with zipfile.ZipFile(io.BytesIO(vacia.content)) as copia:
        assert copia.namelist() == []

    corazon, suelo = png(32, 32, 1), png(1024, 512)
    assert subir(cliente, CORAZON, png(32, 32, 9)).status_code == 200
    assert subir(cliente, CORAZON, corazon).status_code == 200
    assert subir(cliente, SUELO, suelo).status_code == 200
    assert subir(cliente, ESTRELLA, png(32, 32, 3)).status_code == 200
    assert volver(cliente, ESTRELLA, "provisional").status_code == 200

    respuesta = cliente.get(f"{API}/copia.zip")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/zip"
    assert respuesta.headers["content-disposition"].startswith("attachment")
    assert int(respuesta.headers["content-length"]) == len(respuesta.content)
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        assert copia.testzip() is None
        assert sorted(copia.namelist()) == [CORAZON, SUELO]
        assert copia.read(CORAZON) == (carpeta / nombre_limpio(corazon, CORAZON)).read_bytes()
        assert copia.read(SUELO) == (carpeta / nombre_original(suelo, SUELO)).read_bytes()
    # Cada copia se armó en su temporal, y los dos quedaron cerrados.
    assert [archivo.closed for archivo in temporales] == [True, True]


def _bajar_la_copia_y_cortar(app, abiertos):
    """Pide la copia hablando ASGI y se va en cuanto llega el primer trozo.

    Devuelve cuántos trozos llegaron y si los temporales estaban cerrados al acabar la
    respuesta, antes de que el bucle se apague y recoja lo que quedó colgando.
    """
    enviados = []

    async def pedir():
        empezo = asyncio.Event()

        async def recibir():
            await empezo.wait()
            return {"type": "http.disconnect"}

        async def enviar(mensaje):
            enviados.append(mensaje)
            if mensaje["type"] == "http.response.body":
                empezo.set()

        camino = f"{API}/copia.zip"
        alcance = {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": "GET", "scheme": "http", "path": camino, "raw_path": camino.encode(),
            "root_path": "", "query_string": b"", "client": ("prueba", 1), "server": ("prueba", 80),
            "headers": [(b"host", b"prueba"), (b"cookie", f"session={galleta(DIBUJA)}".encode())],
        }
        await app(alcance, recibir, enviar)
        return [archivo.closed for archivo in abiertos]

    cerrados = asyncio.run(pedir())
    return sum(m["type"] == "http.response.body" for m in enviados), cerrados


def test_si_la_descarga_se_corta_el_temporal_se_cierra_igual(cliente, carpeta, temporales):
    assert subir(cliente, SUELO, png(1024, 512)).status_code == 200
    # Sin el recolector: lo que se cierra tiene que cerrarse solo.
    gc.disable()
    try:
        trozos, cerrados = _bajar_la_copia_y_cortar(cliente.app, temporales)
    finally:
        gc.enable()
    assert 1 <= trozos < 5
    assert cerrados == [True]


def test_si_falta_una_imagen_en_disco_la_copia_sale_igual_sin_ella(cliente, carpeta, temporales):
    estrella = png(32, 32, 4)
    assert subir(cliente, CORAZON, png(32, 32, 1)).status_code == 200
    assert subir(cliente, ESTRELLA, estrella).status_code == 200
    (carpeta / nombre_limpio(estrella, ESTRELLA)).unlink()
    respuesta = cliente.get(f"{API}/copia.zip")
    assert respuesta.status_code == 200
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        assert copia.namelist() == [CORAZON]
    assert [archivo.closed for archivo in temporales] == [True]


# --- Descargar los provisionales -------------------------------------------------

def _del_repo(ruta: str) -> bytes:
    raiz = arte.RAIZ if arte.lugar_de(ruta).en_el_juego else arte.RAIZ_POR_VENIR
    return (raiz / ruta).read_bytes()


def test_el_provisional_baja_en_la_medida_de_la_pieza(cliente):
    respuesta = cliente.get(f"{API}/provisional", params={"ruta": CORAZON})
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "image/png"
    assert respuesta.headers["content-disposition"] == 'attachment; filename="provisional-efectos-corazon.png"'
    pieza = arte.lugar_de(CORAZON)
    with Image.open(io.BytesIO(respuesta.content)) as imagen:
        assert imagen.format == "PNG" and imagen.size == (pieza.ancho, pieza.alto)
    assert respuesta.content == _del_repo(CORAZON)


def test_cada_pieza_que_no_es_de_la_pieza_baja_en_su_medida(cliente):
    for pieza in arte.piezas():
        if pieza.familia == "pieza":
            continue
        respuesta = cliente.get(f"{API}/provisional", params={"ruta": pieza.ruta})
        assert respuesta.status_code == 200, pieza.ruta
        with Image.open(io.BytesIO(respuesta.content)) as imagen:
            assert imagen.size == (pieza.ancho, pieza.alto), pieza.ruta


@pytest.mark.parametrize("ruta", [SUELO, "pieza/pared-izquierda.png", "pieza/muebles/cama-se.png"])
def test_el_provisional_de_un_mueble_baja_en_su_medida_de_subida(cliente, carpeta, ruta):
    lugar = arte.lugar_de(ruta)
    respuesta = cliente.get(f"{API}/provisional", params={"ruta": ruta})
    assert respuesta.status_code == 200
    with Image.open(io.BytesIO(respuesta.content)) as imagen:
        assert imagen.size == (lugar.ancho, lugar.alto)
    # Lo que baja se puede subir tal cual (es la medida de subida).
    assert subir(cliente, ruta, respuesta.content).status_code == 200


def test_el_provisional_no_es_lo_subido(cliente, carpeta):
    assert subir(cliente, CORAZON, png(32, 32, 5)).status_code == 200
    assert subir(cliente, SUELO, png(1024, 512, 6)).status_code == 200
    assert cliente.get(f"{API}/provisional", params={"ruta": CORAZON}).content == _del_repo(CORAZON)
    with Image.open(io.BytesIO(cliente.get(f"{API}/provisional", params={"ruta": SUELO}).content)) as imagen:
        assert imagen.size == (1024, 512)


@pytest.mark.parametrize("ruta", [
    "../config.py", "efectos/../../config.py", "/etc/passwd", "efectos/inventada.png",
    "efectos/corazon.png/", "efectos\\corazon.png", "", "efectos/corazon.png\x00.png",
])
def test_una_ruta_que_no_es_del_contrato_se_rechaza_sin_tocar_el_disco(cliente, monkeypatch, ruta):
    def leer(*_):
        pytest.fail("se leyó un archivo para una ruta que no es del contrato")

    respuesta = cliente.get(f"{API}/provisional", params={"ruta": ruta})
    como_una_ruta_que_no_existe(cliente, respuesta)
    monkeypatch.setattr(dibujante, "_el_provisional", leer)
    monkeypatch.setattr(Path, "read_bytes", leer)
    como_una_ruta_que_no_existe(cliente, cliente.get(f"{API}/provisional", params={"ruta": ruta}))


def test_un_provisional_que_falta_en_el_repo_es_404(cliente, monkeypatch, tmp_path):
    vacia = tmp_path / "arte-vacia"
    vacia.mkdir()
    monkeypatch.setattr(arte, "RAIZ", vacia)
    respuesta = cliente.get(f"{API}/provisional", params={"ruta": CORAZON})
    assert respuesta.status_code == 404
    assert respuesta.headers["cache-control"] == "no-store"


def test_el_zip_de_provisionales_trae_cada_uno_en_la_carpeta_de_su_grupo(cliente, temporales):
    respuesta = cliente.get(f"{API}/provisionales.zip")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/zip"
    assert respuesta.headers["content-disposition"] == 'attachment; filename="provisionales.zip"'
    assert int(respuesta.headers["content-length"]) == len(respuesta.content)
    # Sin las criaturas: son 5 030 y se bajan por especie.
    grupos = [g for g in arte.grupos() if g.familia != "criaturas"]
    esperado = {}
    for grupo in grupos:
        for ruta in grupo.rutas:
            esperado[f"{grupo.clave}/{ruta.rsplit('/', 1)[1]}"] = ruta
    assert len(esperado) == len(arte.lugares()) - CAPAS_DE_CRIATURAS
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        assert copia.testzip() is None
        nombres = copia.namelist()
        assert len(nombres) == len(set(nombres)) == len(arte.lugares()) - CAPAS_DE_CRIATURAS
        assert set(nombres) == set(esperado)
        # Cada uno, en su medida de subida; lo que no es de la pieza, con los bytes del repo.
        for grupo in grupos:
            for ruta in grupo.rutas:
                lugar, dentro = arte.lugar_de(ruta), copia.read(f"{grupo.clave}/{ruta.rsplit('/', 1)[1]}")
                with Image.open(io.BytesIO(dentro)) as imagen:
                    assert imagen.size == (lugar.ancho, lugar.alto), ruta
                if lugar.reduccion == 1:
                    assert dentro == _del_repo(ruta), ruta
    assert [archivo.closed for archivo in temporales] == [True]


@pytest.mark.usefixtures("provisional_barato")
def test_el_zip_de_provisionales_no_es_lo_subido(cliente, carpeta):
    assert subir(cliente, CORAZON, png(32, 32, 7)).status_code == 200
    respuesta = cliente.get(f"{API}/provisionales.zip")
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        assert copia.read("efectos/corazon.png") == _del_repo(CORAZON)


def test_en_el_zip_un_nombre_repetido_dentro_de_un_grupo_lleva_su_ruta_entera(cliente, monkeypatch):
    rutas = ("pueblo/lugares/tienda.png", "escenas/tienda.png")
    repetido = arte.Grupo("junto", "Junto", "lugares", rutas, tuple((r,) for r in rutas))

    def solo_el_repetido():
        return (repetido,)
    solo_el_repetido.cache_clear = arte.grupos.cache_clear   # `arte.olvidar()` la vacía al acabar la prueba
    monkeypatch.setattr(arte, "grupos", solo_el_repetido)
    respuesta = cliente.get(f"{API}/provisionales.zip")
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        assert sorted(copia.namelist()) == ["junto/escenas-tienda.png", "junto/pueblo-lugares-tienda.png"]


@pytest.mark.usefixtures("provisional_barato")
def test_si_falta_un_provisional_en_el_repo_el_zip_sale_sin_el_y_lo_avisa(cliente, monkeypatch, tmp_path, caplog):
    copia_del_arte = tmp_path / "arte-incompleta"
    shutil.copytree(arte.RAIZ, copia_del_arte)
    (copia_del_arte / CORAZON).unlink()
    monkeypatch.setattr(arte, "RAIZ", copia_del_arte)
    with caplog.at_level("WARNING", logger="gachamones"):
        respuesta = cliente.get(f"{API}/provisionales.zip")
    assert respuesta.status_code == 200
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        assert "efectos/corazon.png" not in copia.namelist()
        assert len(copia.namelist()) == len(arte.lugares()) - CAPAS_DE_CRIATURAS - 1
    assert CORAZON in caplog.text


@pytest.mark.usefixtures("provisional_barato")
def test_las_descargas_de_provisionales_no_se_guardan(cliente):
    for respuesta in (cliente.get(f"{API}/provisional", params={"ruta": CORAZON}),
                      cliente.get(f"{API}/provisionales.zip")):
        assert respuesta.status_code == 200 and respuesta.headers["cache-control"] == "no-store"


# --- Nada de esto se guarda en una caché -----------------------------------------

def test_el_zip_y_el_404_de_quien_no_tiene_permiso_salen_sin_cache(cliente):
    copia = cliente.get(f"{API}/copia.zip")
    assert copia.status_code == 200 and copia.headers["cache-control"] == "no-store"
    cliente.cookies.clear()
    for pedir in (lambda c: c.get(f"{API}/copia.zip"), lambda c: c.get(f"{API}/avance")):
        respuesta = pedir(cliente)
        assert respuesta.status_code == 404 and respuesta.headers["cache-control"] == "no-store"


SIEMPRE = {"x-content-type-options": "nosniff", "content-security-policy": "frame-ancestors 'none'"}


def test_lo_del_juego_sigue_con_sus_cabeceras_de_siempre(cliente):
    version = cliente.app.state.version
    api = cliente.get("/monsteropolis/api/salud")
    assert api.status_code == 200
    assert {k: api.headers.get(k) for k in (*SIEMPRE, "cache-control", "x-gachamon-version")} == {
        **SIEMPRE, "cache-control": "no-store", "x-gachamon-version": version}
    estatico = cliente.get(f"/monsteropolis/static/{version}/js/principal.js")
    assert estatico.status_code == 200
    assert {k: estatico.headers.get(k) for k in (*SIEMPRE, "cache-control", "x-gachamon-version")} == {
        **SIEMPRE, "cache-control": "public, max-age=31536000, immutable", "x-gachamon-version": None}
    portada = cliente.get("/monsteropolis/")
    assert (portada.headers["cache-control"], portada.headers.get("x-gachamon-version")) == ("no-cache", None)


def test_nada_de_la_api_del_dibujante_se_guarda_en_una_cache(cliente):
    version = cliente.app.state.version
    for respuesta in (cliente.get(f"{API}/avance"), cliente.get(f"{API}/copia.zip"),
                      subir(cliente, CORAZON, b"no"), subir(cliente, CORAZON, b"\0" * (LIMITE + 1)),
                      cliente.get(INVENTADA)):
        assert respuesta.headers["cache-control"] == "no-store"
        assert respuesta.headers["x-gachamon-version"] == version
    entrar(cliente, NADIE)
    for pedir in RUTAS.values():
        respuesta = pedir(cliente)
        assert respuesta.status_code == 404 and respuesta.headers["cache-control"] == "no-store"


# --- La página del dibujante --------------------------------------------------------

PAGINA = "/monsteropolis_dibujante/"


def test_la_pagina_del_dibujante_se_sirve_sin_cache_y_con_los_estaticos_de_la_version(cliente):
    version = cliente.app.state.version
    for uid in (DIBUJA, ADMIN):
        entrar(cliente, uid)
        respuesta = cliente.get(PAGINA)
        assert respuesta.status_code == 200
        assert "text/html" in respuesta.headers["content-type"]
        assert respuesta.headers["cache-control"] == "no-store"
        assert {k: respuesta.headers.get(k) for k in SIEMPRE} == SIEMPRE
        assert "__V__" not in respuesta.text
        assert f'"/monsteropolis/static/{version}/js/dibujante.js"' in respuesta.text
        assert f'"/monsteropolis/static/{version}/estilo.css"' in respuesta.text
        assert "<title>Arte de Criópolis</title>" in respuesta.text


def test_sin_la_barra_del_final_se_llega_igual_a_la_pagina(cliente):
    respuesta = cliente.get(PAGINA.rstrip("/"))
    assert respuesta.status_code == 200 and respuesta.url.path == PAGINA
    # Con una dirección relativa, como la del juego: detrás del túnel no cambia ni el
    # esquema ni el puerto, ni se pierde la cookie.
    redirige = cliente.get(PAGINA.rstrip("/"), follow_redirects=False)
    assert redirige.status_code in (301, 302, 307, 308)
    assert redirige.headers["location"] == PAGINA


def test_sin_la_barra_a_los_demas_les_contesta_como_una_que_no_existe(cliente):
    entrar(cliente, NADIE)
    respuesta = cliente.get(PAGINA.rstrip("/"), follow_redirects=False)
    inventada = cliente.get(f"{PAGINA}no-existe")
    assert (respuesta.status_code, respuesta.content) == (404, inventada.content)
    assert respuesta.headers == inventada.headers


def test_la_pagina_del_dibujante_no_se_sirve_como_estatico(cliente):
    version = cliente.app.state.version
    entrar(cliente, NADIE)
    assert cliente.get(f"/monsteropolis/static/{version}/dibujante.html").status_code == 404
    # Su hoja y su guion sí son estáticos: no dicen nada que no diga el repo.
    assert cliente.get(f"/monsteropolis/static/{version}/js/dibujante.js").status_code == 200
    assert cliente.get(f"/monsteropolis/static/{version}/dibujante.css").status_code == 200


@pytest.mark.parametrize("quien", DEMAS)
def test_a_los_demas_la_pagina_les_contesta_como_una_que_no_existe(cliente, tmp_path, monkeypatch, quien):
    if quien == "sin_sesion":
        cliente.cookies.clear()
    elif quien == "cookie_falsa":
        cliente.cookies.set("session", galleta(DIBUJA, clave="otra-clave"))
    elif quien == "sin_la_columna":
        _permisos(tmp_path, monkeypatch, con_arte_access=False)
    else:
        entrar(cliente, {"sin_permiso": NADIE, "bloqueada": BLOQUEADO, "no_existe": NO_EXISTE}[quien])
    respuesta = cliente.get(PAGINA)
    inventada = cliente.get(f"{PAGINA}no-existe")
    assert inventada.status_code == 404
    assert (respuesta.status_code, respuesta.content) == (404, inventada.content)
    assert respuesta.headers == inventada.headers
    assert "Arte de Criópolis" not in respuesta.text
    # Con el permiso, sí.
    _permisos(tmp_path, monkeypatch)
    entrar(cliente, DIBUJA)
    assert cliente.get(PAGINA).status_code == 200


# --- Lo que se ve y se baja a la medida nueva -----------------------------------

def _con_fuentes(monkeypatch, tmp_path) -> Path:
    fuentes = tmp_path / "fuentes"
    monkeypatch.setattr(arte, "FUENTES", fuentes)
    return fuentes


def test_el_provisional_de_un_mueble_baja_al_doble_sin_suavizar(cliente, monkeypatch, tmp_path):
    _con_fuentes(monkeypatch, tmp_path)   # sin original en `fuentes/`
    respuesta = cliente.get(f"{API}/provisional", params={"ruta": MACETA})
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "image/png"
    assert respuesta.headers["content-disposition"] == 'attachment; filename="provisional-pieza-muebles-maceta-se.png"'
    with Image.open(io.BytesIO(respuesta.content)) as doble, Image.open(arte.RAIZ / MACETA) as chico:
        assert doble.size == (1024, 1536) == (arte.lugar_de(MACETA).ancho, arte.lugar_de(MACETA).alto)
        doble, chico = doble.convert("RGBA"), chico.convert("RGBA")
        assert doble.tobytes() == chico.resize(doble.size, Image.NEAREST).tobytes()
        for x, y in ((0, 0), (255, 400), (511, 767)):
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                assert doble.getpixel((2 * x + dx, 2 * y + dy)) == chico.getpixel((x, y))


def test_si_fuentes_tiene_el_original_el_provisional_es_ese(cliente, monkeypatch, tmp_path):
    fuentes = _con_fuentes(monkeypatch, tmp_path)
    (fuentes / "pieza/muebles").mkdir(parents=True)
    original = png(1024, 1536, 7)
    (fuentes / MACETA).write_bytes(original)
    respuesta = cliente.get(f"{API}/provisional", params={"ruta": MACETA})
    assert respuesta.status_code == 200
    assert respuesta.content == original


def test_la_miniatura_del_provisional_es_la_del_repo_sin_ampliar(cliente, monkeypatch, tmp_path):
    fuentes = _con_fuentes(monkeypatch, tmp_path)   # aunque `fuentes/` tenga el original
    (fuentes / "pieza/muebles").mkdir(parents=True)
    (fuentes / MACETA).write_bytes(png(1024, 1536, 7))
    respuesta = cliente.get(f"{API}/provisional", params={"ruta": MACETA, "miniatura": 1})
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "image/png"
    assert "content-disposition" not in respuesta.headers
    assert respuesta.content == _del_repo(MACETA)


def test_el_provisional_de_un_icono_baja_tal_cual(cliente):
    respuesta = cliente.get(f"{API}/provisional", params={"ruta": CORAZON})
    assert respuesta.content == _del_repo(CORAZON)
    con_miniatura = cliente.get(f"{API}/provisional", params={"ruta": CORAZON, "miniatura": 1})
    assert con_miniatura.content == _del_repo(CORAZON)


def test_descargar_la_imagen_subida_baja_el_original(cliente, carpeta):
    cuerpo = png(1024, 1536, 3)
    vista = subir(cliente, MACETA, cuerpo).json()
    original, chica = arte_subido.preparar(cuerpo, arte.lugar_de(MACETA))
    baja = cliente.get(vista["subida"]["original"])
    assert baja.status_code == 200
    assert baja.content == original.datos
    assert vista["subida"]["direccion"].endswith(chica.nombre)
    assert baja.content != cliente.get(vista["subida"]["direccion"]).content


def test_la_copia_trae_los_originales_con_su_ruta(cliente, carpeta):
    cuerpo = png(1024, 1536, 4)
    assert subir(cliente, MACETA, cuerpo).status_code == 200
    # Una fila de antes de publicar, sin original: la copia lleva su propio archivo.
    db.subir_arte(SUELO, "b" * 64 + ".png", 512, 256, "dibuja", T0)
    (carpeta / ("b" * 64 + ".png")).write_bytes(b"viejo")
    respuesta = cliente.get(f"{API}/copia.zip")
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        assert sorted(copia.namelist()) == [MACETA, SUELO]
        original = arte_subido.preparar(cuerpo, arte.lugar_de(MACETA))[0]
        assert copia.read(MACETA) == original.datos
        assert Image.open(io.BytesIO(copia.read(MACETA))).size == (1024, 1536)
        assert copia.read(SUELO) == b"viejo"


def test_el_historial_dice_la_medida_del_original(cliente, carpeta):
    cuerpo = png(1024, 1536, 5)
    assert subir(cliente, MACETA, cuerpo).status_code == 200
    assert volver(cliente, MACETA, "provisional").status_code == 200
    original, chica = arte_subido.preparar(cuerpo, arte.lugar_de(MACETA))
    renglones_ = historial(cliente, MACETA).json()["historial"]
    assert [r["accion"] for r in renglones_] == ["provisional", "subir"]
    assert renglones_[0]["direccion"] is None and renglones_[0]["original"] is None
    subida = renglones_[1]
    assert subida["direccion"] == f"/monsteropolis/arte-subido/{chica.nombre}"
    assert subida["original"] == f"/monsteropolis/arte-subido/{original.nombre}"
    assert (subida["ancho"], subida["alto"]) == (1024, 1536)


def test_una_subida_cortada_no_deja_renglon_ni_archivo(cliente, carpeta):
    entero = png(1024, 1536, 6)
    respuesta = subir(cliente, MACETA, entero[: len(entero) // 2])
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detail": {"clave": "no_vale", "mensaje": "El PNG está dañado o incompleto."}}
    assert nada_guardado(carpeta)
    assert not list(carpeta.glob(".subiendo-*"))


# --- El encendido de los cuatro muebles del juego -----------------------------------

LAMPARA_ENCENDIDA = "pieza/muebles/lampara-encendido-se.png"


def test_subir_un_encendido_no_toca_la_portada(cliente, carpeta):
    lugar = arte.lugar_de(LAMPARA_ENCENDIDA)
    vista = subir(cliente, LAMPARA_ENCENDIDA, png(lugar.ancho, lugar.alto)).json()
    assert vista["subida"] is not None and vista["medida_cambiada"] is None
    assert (vista["objeto"], vista["estado"]) == ("lampara", "encendido")
    assert _bloque_de_la_portada(cliente) == {}
    avance = {g["clave"]: (g["hechas"], g["total"]) for g in cliente.get(f"{API}/avance").json()["grupos"]}
    assert avance["pieza/muebles/lampara"] == (1, 8)


def test_la_vista_dice_el_objeto_el_estado_y_donde_esta_la_miniatura(cliente):
    de_juego = _vista_de(cliente, "pieza/muebles/lampara-se.png")
    assert (de_juego["objeto"], de_juego["estado"], de_juego["miniatura"]) == (None, None, None)
    nueva = _vista_de(cliente, "pieza/muebles/fuente-encendido-ne.png")
    assert (nueva["objeto"], nueva["estado"]) == ("fuente", "encendido")
    assert nueva["miniatura"] == ("/monsteropolis_dibujante/api/provisional"
                                  "?ruta=pieza/muebles/fuente-encendido-ne.png&miniatura=1")
    assert cliente.get(nueva["miniatura"]).status_code == 200


def test_el_provisional_del_encendido_baja_al_doble(cliente):
    lugar = arte.lugar_de(LAMPARA_ENCENDIDA)
    respuesta = cliente.get(f"{API}/provisional", params={"ruta": LAMPARA_ENCENDIDA})
    assert respuesta.status_code == 200
    with Image.open(io.BytesIO(respuesta.content)) as imagen:
        assert imagen.size == (lugar.ancho, lugar.alto)
    chica = cliente.get(f"{API}/provisional", params={"ruta": LAMPARA_ENCENDIDA, "miniatura": 1})
    assert chica.status_code == 200 and "content-disposition" not in chica.headers
    with Image.open(io.BytesIO(chica.content)) as imagen:
        assert imagen.size == (lugar.ancho // 2, lugar.alto // 2)
    assert chica.content == (arte.RAIZ_POR_VENIR / LAMPARA_ENCENDIDA).read_bytes()


def test_un_objeto_nuevo_se_ve_y_se_baja_pero_no_toca_la_portada(cliente, carpeta):
    vista = _vista_de(cliente, "pieza/muebles/balcon-se.png")
    assert (vista["objeto"], vista["estado"]) == ("balcon", None)
    assert (vista["ancho"], vista["alto"]) == (2560, 2304)
    assert cliente.get(vista["miniatura"]).status_code == 200
    icono = _vista_de(cliente, "iconos/muebles/silla_azul.png")
    assert (icono["ancho"], icono["alto"]) == (48, 48)
    assert cliente.get(f"{API}/provisional", params={"ruta": "pieza/muebles/mega_tv-ne.png"}).status_code == 200
    assert _bloque_de_la_portada(cliente) == {}


# --- Las capas de las criaturas ---------------------------------------------------

CUERPO = "criaturas/dragoncito/adulto/cuerpo-no.png"
CARA = "criaturas/dragoncito/adulto/cara-mal-so.png"


def _de_frente(*capa) -> bytes:
    from retrato import capa_de_frente

    return capa_de_frente(*capa)


def test_el_provisional_de_un_cuerpo_dibujado_es_su_capa_de_frente_por_cuatro(cliente):
    chico = _de_frente("dragoncito", "adulto", "cuerpo", None)
    respuesta = cliente.get(f"{API}/provisional", params={"ruta": CUERPO})
    assert respuesta.status_code == 200 and respuesta.headers["content-type"] == "image/png"
    assert respuesta.headers["content-disposition"] == \
        'attachment; filename="provisional-criaturas-dragoncito-adulto-cuerpo-no.png"'
    with Image.open(io.BytesIO(respuesta.content)) as grande, Image.open(io.BytesIO(chico)) as base:
        assert grande.size == (1024, 1024) == (arte.lugar_de(CUERPO).ancho, arte.lugar_de(CUERPO).alto)
        assert grande.convert("RGBA").tobytes() == base.convert("RGBA").resize((1024, 1024), Image.NEAREST).tobytes()
    # La miniatura es la de 256, tal cual y sin descarga.
    mini = cliente.get(f"{API}/provisional", params={"ruta": CUERPO, "miniatura": 1})
    assert mini.content == chico and "content-disposition" not in mini.headers
    # Las cuatro orientaciones tienen el mismo provisional.
    otra = cliente.get(f"{API}/provisional", params={"ruta": CUERPO.replace("-no", "-se"), "miniatura": 1})
    assert otra.content == chico


def test_una_especie_sin_dibujos_usa_el_relleno_de_retrato(cliente):
    import especies
    import retrato

    sin_dibujo = next(c for c in especies.ESPECIES if c not in retrato.CON_ETAPAS_COMPLETAS)
    ruta = f"criaturas/{sin_dibujo}/bebe/cuerpo-se.png"
    respuesta = cliente.get(f"{API}/provisional", params={"ruta": ruta, "miniatura": 1})
    assert respuesta.status_code == 200
    assert respuesta.content == retrato.relleno(sin_dibujo, "bebe", "normal")


def test_el_provisional_de_una_cara_sigue_la_busqueda_forma_especie_comun(cliente):
    for ruta, esperado in ((CARA, ("dragoncito", "adulto", "cara", "mal")),
                           ("criaturas/dragoncito/cara-feliz-se.png", ("dragoncito", None, "cara", "feliz")),
                           ("criaturas/comun/cara-normal-so.png", (None, None, "cara", "normal")),
                           ("criaturas/dragoncito/sombrero-laurel-ne.png", ("dragoncito", None, "sombrero", "laurel")),
                           ("criaturas/comun/sombrero-cinta-se.png", (None, None, "sombrero", "cinta"))):
        respuesta = cliente.get(f"{API}/provisional", params={"ruta": ruta, "miniatura": 1})
        assert respuesta.status_code == 200, ruta
        assert respuesta.content == _de_frente(*esperado), ruta


def test_la_vista_de_una_capa_dice_que_es(cliente):
    vistas = {}
    for clave in ("criaturas/dragoncito", "criaturas/comun", "efectos"):
        grupos = cliente.get(f"{API}/piezas", params={"grupo": clave}).json()["grupos"]
        vistas |= {p["ruta"]: p for g in grupos for p in g["piezas"]}
    assert vistas[CUERPO]["criatura"] == {"nivel": "forma", "etapa": "adulto", "capa": "cuerpo", "cual": None,
                                          "nombre_del_sombrero": None, "orientacion": "no"}
    sombrero = vistas["criaturas/comun/sombrero-laurel-se.png"]
    assert sombrero["criatura"] == {"nivel": "comun", "etapa": None, "capa": "sombrero", "cual": "laurel",
                                    "nombre_del_sombrero": "Laurel", "orientacion": "se"}
    assert sombrero["miniatura"] == f"{API}/provisional?ruta=criaturas/comun/sombrero-laurel-se.png&miniatura=1"
    assert vistas[CORAZON]["criatura"] is None


def test_una_capa_se_sube_y_se_ve(cliente, carpeta):
    cuerpo = png(1024, 1024, 5)
    vista = subir(cliente, CARA, cuerpo).json()
    assert vista["subida"]["direccion"] == direccion(cuerpo, CARA)
    assert vista["criatura"]["capa"] == "cara"
    with Image.open(carpeta / nombre_limpio(cuerpo, CARA)) as chica:
        assert chica.size == (256, 256)
    # Y no es del juego: no entra en lo que lee la portada.
    assert CARA not in db.arte_vigente(arte_subido.medidas())


@pytest.mark.usefixtures("provisional_barato")
def test_el_zip_de_provisionales_no_trae_las_criaturas(cliente):
    respuesta = cliente.get(f"{API}/provisionales.zip")
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        nombres = copia.namelist()
    assert not any(n.startswith("criaturas") for n in nombres)
    assert len(nombres) == len(arte.lugares()) - CAPAS_DE_CRIATURAS


# --- El avance cuenta casillas, y la api va por grupos --------------------------------

CARA_PULPO = f"{PULPO}/bebe/cara-feliz-se.png"
CARA_DE_LA_ESPECIE = f"{PULPO}/cara-feliz-se.png"
CARA_COMUN = "criaturas/comun/cara-feliz-se.png"


def liso(color: int, lado: int = 1024) -> bytes:
    """Un PNG de un solo color (pesa casi nada), distinto para cada `color`."""
    salida = io.BytesIO()
    Image.new("RGBA", (lado, lado), (color, 0, 0, 255)).save(salida, "PNG")
    return salida.getvalue()


def _avance(cliente) -> dict[str, tuple[int, int]]:
    return {g["clave"]: (g["hechas"], g["total"]) for g in cliente.get(f"{API}/avance").json()["grupos"]}


def test_el_avance_trae_84_grupos_y_no_el_de_las_comunes(cliente):
    assert len(arte.grupos()) == GRUPOS
    claves = [g["clave"] for g in cliente.get(f"{API}/avance").json()["grupos"]]
    assert len(claves) == GRUPOS_CON_TARJETA
    assert "criaturas/comun" not in claves
    assert _avance(cliente)[PULPO] == (0, CASILLAS_POR_ESPECIE)


def test_cien_avances_arman_los_grupos_una_sola_vez(cliente, monkeypatch):
    """El tablero pide el avance cada pocos segundos por pestaña, en el proceso que atiende a
    quien juega: los grupos (miles de lugares) se arman una vez, y `olvidar()` los vuelve a armar."""
    arte.olvidar()
    armados, original = [], arte._casillas_de
    monkeypatch.setattr(arte, "_casillas_de", lambda rutas: armados.append(rutas) or original(rutas))
    for _ in range(100):
        assert cliente.get(f"{API}/avance").status_code == 200
    assert len(armados) == GRUPOS          # `_casillas_de` corre una vez por grupo: un solo armado
    assert cliente.get(f"{API}/piezas").status_code == 200
    assert cliente.get(f"{API}/piezas", params={"grupo": PULPO}).status_code == 200
    assert len(armados) == GRUPOS
    arte.olvidar()
    assert cliente.get(f"{API}/avance").status_code == 200
    assert len(armados) == 2 * GRUPOS


def test_una_capa_comun_hace_avanzar_a_todas_las_especies_que_cubre(cliente):
    assert subir(cliente, CARA_COMUN, liso(1)).status_code == 200
    avance = _avance(cliente)
    especies_ = [clave for clave in avance if clave.startswith("criaturas/")]
    assert len(especies_) == 25
    # Una cara por etapa y por especie: la común cubre las cinco casillas `cara-feliz-se` de cada una.
    assert {avance[clave] for clave in especies_} == {(5, CASILLAS_POR_ESPECIE)}
    assert sum(hechas for hechas, _ in avance.values()) == 25 * 5
    # Ya de una especie con su propia capa en una etapa: esa casilla no se cuenta dos veces.
    assert subir(cliente, CARA_PULPO, liso(2)).status_code == 200
    assert _avance(cliente)[PULPO] == (5, CASILLAS_POR_ESPECIE)


def test_volver_una_capa_de_la_especie_al_provisional_descubre_sus_casillas(cliente):
    assert subir(cliente, CARA_DE_LA_ESPECIE, liso(3)).status_code == 200
    avance = _avance(cliente)
    assert avance[PULPO] == (5, CASILLAS_POR_ESPECIE)
    assert avance["criaturas/dragoncito"] == (0, CASILLAS_POR_ESPECIE)
    assert volver(cliente, CARA_DE_LA_ESPECIE, "provisional").status_code == 200
    # Vuelven a faltar las cinco, y las de las otras especies no se movieron.
    assert set(_avance(cliente).values()) == {(0, CASILLAS_POR_ESPECIE), *(
        (0, total) for _, total in avance.values())}
    assert sum(hechas for hechas, _ in _avance(cliente).values()) == 0


def test_hechas_nunca_pasa_de_total(cliente):
    # La misma casilla por sus tres rutas, y todo lo de la especie y lo común.
    for color, ruta in enumerate((CARA_PULPO, CARA_DE_LA_ESPECIE, CARA_COMUN,
                                  f"{PULPO}/bebe/cuerpo-se.png", "criaturas/comun/sombrero-laurel-so.png",
                                  f"{PULPO}/sombrero-laurel-so.png"), start=10):
        assert subir(cliente, ruta, liso(color)).status_code == 200
    for clave, (hechas, total) in _avance(cliente).items():
        assert 0 <= hechas <= total, clave
    # Por casilla: la cara de Octopul bebé (3 rutas) cuenta una vez; las otras 4 de la especie, una cada una.
    assert _avance(cliente)[PULPO][0] == 5 + 1 + 5


def test_la_lista_general_no_trae_las_capas_de_las_criaturas(cliente):
    respuesta = cliente.get(f"{API}/piezas")
    assert respuesta.status_code == 200
    assert len(respuesta.content) < 200 * 1024
    grupos = respuesta.json()["grupos"]
    assert len(grupos) == GRUPOS
    for grupo in grupos:
        assert set(grupo) - {"piezas"} == {"clave", "nombre", "familia", "total", "hechas"}
        assert ("piezas" in grupo) == (grupo["familia"] != "criaturas"), grupo["clave"]
    assert all(len(g["piezas"]) == g["total"] for g in grupos if "piezas" in g)
    pulpo = next(g for g in grupos if g["clave"] == PULPO)
    assert (pulpo["total"], pulpo["hechas"]) == (CASILLAS_POR_ESPECIE, 0)
    assert subir(cliente, CARA_COMUN, liso(1)).status_code == 200
    de_nuevo = {g["clave"]: g for g in cliente.get(f"{API}/piezas").json()["grupos"]}
    assert de_nuevo[PULPO]["hechas"] == 5 and de_nuevo["criaturas/comun"]["hechas"] == 1


def test_un_grupo_se_pide_entero(cliente):
    respuesta = cliente.get(f"{API}/piezas", params={"grupo": PULPO})
    assert respuesta.status_code == 200
    grupos = respuesta.json()["grupos"]
    assert [g["clave"] for g in grupos] == [PULPO]
    grupo = {g.clave: g for g in arte.grupos()}[PULPO]
    assert [p["ruta"] for p in grupos[0]["piezas"]] == list(grupo.rutas)
    assert (grupos[0]["nombre"], grupos[0]["familia"], grupos[0]["total"]) == ("Octopul", "criaturas", 170)
    # También uno de los de siempre, y lo común (que no sale en el avance).
    for clave in ("efectos", "criaturas/comun"):
        uno = cliente.get(f"{API}/piezas", params={"grupo": clave}).json()["grupos"]
        assert [g["clave"] for g in uno] == [clave] and uno[0]["piezas"]


@pytest.mark.parametrize("clave", ["criaturas/no-hay", "", "../efectos", "efectos/../efectos", "efectos.png",
                                   "EFECTOS", "efectos\x00", "criaturas", "/efectos", "efectos\\x"])
def test_un_grupo_que_no_existe_es_404(cliente, clave):
    for ruta in ("piezas", "copia.zip", "provisionales.zip"):
        como_una_ruta_que_no_existe(cliente, cliente.get(f"{API}/{ruta}", params={"grupo": clave}))


def test_una_casilla_cubierta_dice_por_quien(cliente, carpeta):
    sin_nada = _vista_de_grupo(cliente, PULPO, CARA_PULPO)
    assert sin_nada["cubierta"] is None
    comun = liso(20)
    assert subir(cliente, CARA_COMUN, comun).status_code == 200
    vista = _vista_de_grupo(cliente, PULPO, CARA_PULPO)
    assert vista["cubierta"] == {"por": "comun", "direccion": direccion(comun, CARA_COMUN)}
    assert vista["subida"] is None
    # La de la especie va antes que la común.
    de_la_especie = liso(21)
    assert subir(cliente, CARA_DE_LA_ESPECIE, de_la_especie).status_code == 200
    assert _vista_de_grupo(cliente, PULPO, CARA_PULPO)["cubierta"] == {
        "por": "especie", "direccion": direccion(de_la_especie, CARA_DE_LA_ESPECIE)}
    # Con la suya al día, ya no está cubierta.
    propia = liso(22)
    hecha = subir(cliente, CARA_PULPO, propia).json()
    assert hecha["cubierta"] is None and hecha["subida"]["direccion"] == direccion(propia, CARA_PULPO)
    # Lo que no es una cara o un sombrero de forma, nunca; y otra especie sólo ve la común.
    assert _vista_de_grupo(cliente, PULPO, f"{PULPO}/bebe/cuerpo-se.png")["cubierta"] is None
    assert _vista_de_grupo(cliente, PULPO, CARA_DE_LA_ESPECIE)["cubierta"] is None
    assert _vista_de_grupo(cliente, "criaturas/dragoncito", "criaturas/dragoncito/bebe/cara-feliz-se.png")[
        "cubierta"]["por"] == "comun"
    # Volver la suya al provisional la deja cubierta de nuevo, y lo dice la respuesta de volver.
    vuelta = volver(cliente, CARA_PULPO, "provisional").json()
    assert vuelta["cubierta"]["por"] == "especie" and vuelta["subida"] is None
    assert _vista_de(cliente, "efectos/corazon.png")["cubierta"] is None


def _vista_de_grupo(cliente, clave, ruta) -> dict:
    grupos = cliente.get(f"{API}/piezas", params={"grupo": clave}).json()["grupos"]
    return {p["ruta"]: p for p in grupos[0]["piezas"]}[ruta]


@pytest.mark.usefixtures("provisional_barato")
def test_los_zips_de_arriba_no_traen_criaturas(cliente, carpeta):
    for ruta, color in ((CARA_PULPO, 30), (CARA_COMUN, 31)):
        assert subir(cliente, ruta, liso(color)).status_code == 200
    assert subir(cliente, CORAZON, png(32, 32)).status_code == 200
    with zipfile.ZipFile(io.BytesIO(cliente.get(f"{API}/copia.zip").content)) as copia:
        assert copia.namelist() == [CORAZON]
    respuesta = cliente.get(f"{API}/provisionales.zip")
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        nombres = copia.namelist()
    assert not any(n.startswith("criaturas") for n in nombres)
    assert len(nombres) == len(arte.lugares()) - CAPAS_DE_CRIATURAS


def test_cada_especie_tiene_sus_dos_zips(cliente, carpeta):
    suya, otra = liso(40), liso(41)
    for ruta, cuerpo in ((CARA_PULPO, suya), (CARA_DE_LA_ESPECIE, liso(42)),
                         ("criaturas/dragoncito/bebe/cara-feliz-se.png", otra), (CORAZON, png(32, 32))):
        assert subir(cliente, ruta, cuerpo).status_code == 200
    respuesta = cliente.get(f"{API}/copia.zip", params={"grupo": PULPO})
    assert respuesta.status_code == 200 and respuesta.headers["content-type"] == "application/zip"
    assert respuesta.headers["content-disposition"] == 'attachment; filename="copia-criaturas-pulpo.zip"'
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        assert sorted(copia.namelist()) == sorted([CARA_PULPO, CARA_DE_LA_ESPECIE])
        assert copia.read(CARA_PULPO) == (carpeta / nombre_original(suya, CARA_PULPO)).read_bytes()
    respuesta = cliente.get(f"{API}/provisionales.zip", params={"grupo": PULPO})
    assert respuesta.status_code == 200
    assert respuesta.headers["content-disposition"] == 'attachment; filename="provisionales-criaturas-pulpo.zip"'
    assert int(respuesta.headers["content-length"]) == len(respuesta.content)
    grupo = {g.clave: g for g in arte.grupos()}[PULPO]
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        nombres = copia.namelist()
        assert len(nombres) == len(set(nombres)) == len(grupo.rutas) == 200
        assert all(n.startswith(f"{PULPO}/") for n in nombres)
        with Image.open(io.BytesIO(copia.read(nombres[0]))) as imagen:
            assert imagen.size == (1024, 1024)
    # Uno de los de siempre también tiene los suyos, con su nombre.
    respuesta = cliente.get(f"{API}/copia.zip", params={"grupo": "efectos"})
    assert respuesta.headers["content-disposition"] == 'attachment; filename="copia-efectos.zip"'
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        assert copia.namelist() == [CORAZON]
    respuesta = cliente.get(f"{API}/provisionales.zip", params={"grupo": "pieza/muebles/cama"})
    assert respuesta.headers["content-disposition"] == 'attachment; filename="provisionales-pieza-muebles-cama.zip"'


def test_los_zips_se_arman_junto_a_lo_subido_y_no_en_el_tmp_del_sistema(cliente, carpeta, monkeypatch, tmp_path):
    """Con los originales, un zip son cientos de MB, y el `/tmp` del sistema puede ser memoria: el
    temporal va en la carpeta de lo subido (creándola si falta) y no deja nombre en ella."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / "no-hay-tmp"))
    assert not carpeta.exists()
    vacia = cliente.get(f"{API}/copia.zip")
    assert vacia.status_code == 200
    with zipfile.ZipFile(io.BytesIO(vacia.content)) as copia:
        assert copia.namelist() == []
    assert carpeta.is_dir() and not any(carpeta.iterdir())

    corazon = png(32, 32, 5)
    assert subir(cliente, CORAZON, corazon).status_code == 200
    guardado = sorted(carpeta.iterdir())
    with zipfile.ZipFile(io.BytesIO(cliente.get(f"{API}/copia.zip").content)) as copia:
        assert copia.namelist() == [CORAZON]
    respuesta = cliente.get(f"{API}/provisionales.zip", params={"grupo": "efectos"})
    assert respuesta.status_code == 200
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        assert len(copia.namelist()) == 4
    assert sorted(carpeta.iterdir()) == guardado
    assert not (tmp_path / "no-hay-tmp").exists()


def test_el_zip_de_una_especie_conserva_sus_carpetas(cliente, carpeta, monkeypatch):
    """Dentro del zip de una especie, cada capa va con su ruta relativa a la especie
    (`bebe/cuerpo-se.png`), igual en los dos zips; los nombres se repiten entre etapas."""
    monkeypatch.setattr(dibujante, "_el_provisional", lambda lugar: b"provisional")
    for color, ruta in enumerate((CARA_PULPO, CARA_DE_LA_ESPECIE, CARA_COMUN), start=50):
        assert subir(cliente, ruta, liso(color)).status_code == 200
    grupos = {g.clave: g for g in arte.grupos()}

    def nombres(zip_, clave):
        respuesta = cliente.get(f"{API}/{zip_}", params={"grupo": clave})
        assert respuesta.status_code == 200
        with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
            return copia.namelist()

    provisionales = nombres("provisionales.zip", PULPO)
    assert sorted(provisionales) == sorted(grupos[PULPO].rutas)
    assert f"{PULPO}/bebe/cuerpo-se.png" in provisionales and f"{PULPO}/adulto/cuerpo-se.png" in provisionales
    assert CARA_DE_LA_ESPECIE in provisionales
    # Lo subido de la especie va con el mismo nombre que su provisional.
    assert sorted(nombres("copia.zip", PULPO)) == sorted([CARA_PULPO, CARA_DE_LA_ESPECIE])
    assert set(nombres("copia.zip", PULPO)) <= set(provisionales)
    # Lo común, en su carpeta, igual en los dos.
    comunes = nombres("provisionales.zip", "criaturas/comun")
    assert sorted(comunes) == sorted(grupos["criaturas/comun"].rutas)
    assert nombres("copia.zip", "criaturas/comun") == [CARA_COMUN]
