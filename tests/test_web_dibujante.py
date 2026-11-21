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
SUELO = "pieza/suelo.png"          # 512 × 256, familia `pieza`: vale también su original, 1024 × 512
LIMITE = 4 * 1024 * 1024

# (id, usuario, bloqueada, arte_access, is_admin)
CUENTAS = ((1, "dibuja", 0, 1, 0), (2, "admin", 0, 0, 1), (3, "nadie", 0, 0, 0), (4, "bloqueado", 1, 1, 1))
DIBUJA, ADMIN, NADIE, BLOQUEADO, NO_EXISTE = 1, 2, 3, 4, 99

NO_SE_ENTIENDE = {"detail": {"clave": "peticion", "mensaje": "La petición no se entiende."}}
IMAGEN_DEMASIADO_GRANDE = {"detail": {"clave": "demasiado", "mensaje": "La imagen pesa más de 4 MB."}}
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


def png(ancho: int, alto: int, semilla: int = 0) -> bytes:
    """Un PNG RGBA de ruido, siempre el mismo para la misma semilla."""
    imagen = Image.frombytes("RGBA", (ancho, alto), random.Random(semilla).randbytes(ancho * alto * 4))
    salida = io.BytesIO()
    imagen.save(salida, "PNG")
    return salida.getvalue()


def nombre_limpio(cuerpo: bytes, ruta: str) -> str:
    """El nombre con que queda guardado lo que se sube: el de su PNG limpio."""
    return arte_subido.preparar(cuerpo, arte_subido.pieza_de(ruta))[1]


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
}
DEMAS = ["sin_sesion", "cookie_falsa", "sin_permiso", "bloqueada", "no_existe", "sin_la_columna"]


@pytest.mark.parametrize("ruta", RUTAS)
def test_el_dibujante_y_el_admin_entran_en_cada_ruta(cliente, sin_ampliar, ruta):
    for uid in (DIBUJA, ADMIN):
        entrar(cliente, uid)
        assert RUTAS[ruta](cliente).status_code == 200


@pytest.mark.parametrize("ruta", RUTAS)
@pytest.mark.parametrize("quien", DEMAS)
def test_a_los_demas_cada_ruta_les_contesta_como_una_que_no_existe(
        cliente, sin_ampliar, tmp_path, monkeypatch, carpeta, ruta, quien):
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
FAMILIAS = {"avatar", "pieza", "iconos", "pueblo", "lugares", "escenas", "efectos"}


def test_el_avance_es_el_contrato_del_diseno_campo_por_campo(cliente):
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
        {"clave": g.clave, "nombre": g.nombre, "familia": g.familia, "total": len(g.rutas), "hechas": 0}
        for g in arte.grupos()
    ]


def test_el_avance_cuenta_lo_vigente_desde_la_tabla_sin_abrir_ninguna_imagen(cliente, carpeta, monkeypatch):
    for ruta, cuerpo in ((CORAZON, png(32, 32, 1)), (ESTRELLA, png(32, 32, 2)), (SUELO, png(512, 256))):
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
    assert sum(hechas for hechas, _ in avance.values()) == 2


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
        "ruta": CORAZON, "ancho": 32, "alto": 32, "original": None,
        "subida": {"direccion": d1, "quien": "dibuja", "cuando": T0.isoformat()}, "medida_cambiada": None,
    }
    assert (carpeta / nombre_limpio(v1, CORAZON)).is_file()
    piezas = {p["ruta"]: p for g in cliente.get(f"{API}/piezas").json()["grupos"] for p in g["piezas"]}
    assert piezas[CORAZON] == hecho.json()

    reloj.pasar(minutes=5)
    segunda = reloj.ahora
    entrar(cliente, ADMIN)
    hecho = subir(cliente, CORAZON, v2)
    assert hecho.status_code == 200
    assert hecho.json()["subida"] == {"direccion": d2, "quien": "admin", "cuando": segunda.isoformat()}

    reloj.pasar(minutes=5)
    entrar(cliente, DIBUJA)
    hecho = volver(cliente, CORAZON, "anterior")
    assert hecho.status_code == 200
    # Se ve otra vez la primera: quién la subió y cuándo.
    assert hecho.json()["subida"] == {"direccion": d1, "quien": "dibuja", "cuando": T0.isoformat()}
    vuelta = reloj.ahora

    reloj.pasar(minutes=5)
    entrar(cliente, ADMIN)
    hecho = volver(cliente, CORAZON, "provisional")
    assert hecho.status_code == 200
    assert hecho.json() == {
        "ruta": CORAZON, "ancho": 32, "alto": 32, "original": None, "subida": None, "medida_cambiada": None}

    al_provisional = reloj.ahora

    # Desde el provisional, «anterior» lo deshace: vuelve a la última subida.
    reloj.pasar(minutes=5)
    deshecho = reloj.ahora
    hecho = volver(cliente, CORAZON, "anterior")
    assert hecho.status_code == 200
    assert hecho.json()["subida"] == {"direccion": d2, "quien": "admin", "cuando": segunda.isoformat()}

    # Una pieza sin nada subido no tiene anterior: se dice por qué y no cambia nada.
    no = volver(cliente, ESTRELLA, "anterior")
    assert no.status_code == 400
    assert no.json() == {"detail": {"clave": "no_vale", "mensaje": "No hay una imagen anterior."}}
    assert historial(cliente, ESTRELLA).json() == {"ruta": ESTRELLA, "historial": []}

    def renglon(accion, dire, quien, cuando):
        medida = (32, 32) if dire else (None, None)
        return {"accion": accion, "direccion": dire, "ancho": medida[0], "alto": medida[1],
                "quien": quien, "cuando": cuando.isoformat()}

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


def test_en_la_familia_de_la_pieza_vale_tambien_el_original_al_doble(cliente, carpeta):
    original = png(1024, 512)
    # Más de lo que deja pasar el tope de la api del juego: aquí no se aplica.
    assert len(original) > 16 * 1024
    respuesta = subir(cliente, SUELO, original)
    assert respuesta.status_code == 200
    vista = respuesta.json()
    assert (vista["ancho"], vista["alto"], vista["original"]) == (512, 256, {"ancho": 1024, "alto": 512})
    assert vista["subida"]["direccion"] == direccion(original, SUELO)
    with Image.open(carpeta / nombre_limpio(original, SUELO)) as guardada:
        assert guardada.size == (512, 256)


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

def test_una_imagen_de_mas_de_4_mb_da_413_y_no_cambia_nada(cliente, carpeta):
    respuesta = subir(cliente, CORAZON, b"\0" * (LIMITE + 1))
    assert respuesta.status_code == 413 and respuesta.json() == IMAGEN_DEMASIADO_GRANDE
    assert nada_guardado(carpeta)


def test_justo_4_mb_llega_a_mirarse(cliente, carpeta):
    respuesta = subir(cliente, CORAZON, b"\0" * LIMITE)
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"]["mensaje"] == "El archivo no es un PNG."


def test_un_cuerpo_troceado_se_corta_en_cuanto_pasa_de_4_mb(cliente, carpeta):
    estado, cuerpo, leidos = _subir_a_trozos(cliente.app, [b"\0" * (1536 * 1024)] * 5)
    assert (estado, cuerpo) == (413, IMAGEN_DEMASIADO_GRANDE)
    # Uno y medio, tres, cuatro y medio: al tercero ya se pasa, y los otros dos no se leen.
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


# --- Las piezas, el historial y la copia ----------------------------------------

def test_las_piezas_van_por_grupos_con_su_medida_y_lo_que_se_ve_hoy(cliente):
    subido = subir(cliente, SUELO, png(512, 256)).json()
    # Lo subido con una medida que el contrato ya no pide no se sirve (se ve el
    # recuadro), y la pieza lo dice con la medida de lo subido.
    db.subir_arte(CORAZON, "0" * 64 + ".png", 31, 31, "dibuja", T0)
    respuesta = cliente.get(f"{API}/piezas")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert list(cuerpo) == ["grupos"]
    assert [(g["clave"], g["nombre"], g["familia"]) for g in cuerpo["grupos"]] == [
        (g.clave, g.nombre, g.familia) for g in arte.grupos()]
    assert [p["ruta"] for g in cuerpo["grupos"] for p in g["piezas"]] == [
        r for g in arte.grupos() for r in g.rutas]
    piezas = {p["ruta"]: p for g in cuerpo["grupos"] for p in g["piezas"]}
    for pieza in arte.piezas():
        vista = piezas[pieza.ruta]
        assert set(vista) == {"ruta", "ancho", "alto", "original", "subida", "medida_cambiada"}
        assert (vista["ancho"], vista["alto"]) == (pieza.ancho, pieza.alto)
        doble = {"ancho": pieza.ancho * arte.REDUCCION, "alto": pieza.alto * arte.REDUCCION}
        assert vista["original"] == (doble if pieza.familia == "pieza" else None)
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
    vistas = [p for g in cliente.get(f"{API}/piezas").json()["grupos"] for p in g["piezas"]]
    assert sum(p["subida"] is not None for p in vistas) == 150


def test_si_una_subida_se_cruza_entre_las_lecturas_no_se_mezclan_dos_imagenes(cliente, monkeypatch):
    assert subir(cliente, CORAZON, png(32, 32, 1)).status_code == 200
    # Como si otra subida hubiera cambiado la imagen entre leer lo vigente y leer quién
    # la subió: no se enseña la dirección de una con el nombre de quien subió la otra.
    otra = ("f" * 64 + ".png", "otra persona", T0)
    monkeypatch.setattr(db, "quien_subio_lo_puesto", lambda: {CORAZON: otra})
    piezas = {p["ruta"]: p for g in cliente.get(f"{API}/piezas").json()["grupos"] for p in g["piezas"]}
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
        assert copia.read(SUELO) == (carpeta / nombre_limpio(suelo, SUELO)).read_bytes()
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
    return (arte.RAIZ / ruta).read_bytes()


@pytest.fixture
def sin_ampliar(monkeypatch):
    """El zip de provisionales sin ampliar de verdad los de la familia `pieza` (lo caro: ~2,5 s).

    Para las pruebas que no miran esas imágenes; la ampliación se prueba aparte, con las de verdad.
    """
    verdadero = dibujante._el_provisional
    monkeypatch.setattr(dibujante, "_el_provisional",
                        lambda pieza: b"png" if pieza.familia == "pieza" else verdadero(pieza))


def test_el_provisional_baja_en_la_medida_de_la_pieza(cliente):
    respuesta = cliente.get(f"{API}/provisional", params={"ruta": CORAZON})
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "image/png"
    assert respuesta.headers["content-disposition"] == 'attachment; filename="provisional-efectos-corazon.png"'
    pieza = arte_subido.pieza_de(CORAZON)
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
def test_el_provisional_de_un_mueble_baja_al_doble_y_subido_la_pagina_lo_acepta_y_lo_reduce(cliente, carpeta, ruta):
    pieza = arte_subido.pieza_de(ruta)
    respuesta = cliente.get(f"{API}/provisional", params={"ruta": ruta})
    assert respuesta.status_code == 200
    medida_doble = (pieza.ancho * arte.REDUCCION, pieza.alto * arte.REDUCCION)
    with Image.open(io.BytesIO(respuesta.content)) as imagen:
        assert imagen.size == medida_doble
    # Subido tal cual, la página lo acepta y lo reduce a la medida de la pieza.
    limpio, _ = arte_subido.preparar(respuesta.content, pieza)
    with Image.open(io.BytesIO(limpio)) as reducido:
        assert reducido.size == (pieza.ancho, pieza.alto)
    assert subir(cliente, ruta, respuesta.content).status_code == 200


def test_el_provisional_no_es_lo_subido(cliente, carpeta):
    assert subir(cliente, CORAZON, png(32, 32, 5)).status_code == 200
    assert subir(cliente, SUELO, png(1024, 512, 6)).status_code == 200
    assert cliente.get(f"{API}/provisional", params={"ruta": CORAZON}).content == _del_repo(CORAZON)
    suelo = cliente.get(f"{API}/provisional", params={"ruta": SUELO})
    with Image.open(io.BytesIO(suelo.content)) as imagen:
        # El doble del archivo del repo, ampliado al vecino más próximo, no el ruido que se subió.
        esperado = Image.open(arte.RAIZ / SUELO).convert("RGBA").resize((1024, 512), Image.NEAREST)
        assert imagen.convert("RGBA").tobytes() == esperado.tobytes()


@pytest.mark.parametrize("ruta", [
    "../config.py", "efectos/../../config.py", "/etc/passwd", "efectos/inventada.png",
    "efectos/corazon.png/", "efectos\\corazon.png", "", "efectos/corazon.png\x00.png",
])
def test_una_ruta_que_no_es_del_contrato_se_rechaza_sin_tocar_el_disco(cliente, monkeypatch, ruta):
    abiertos = []
    abrir = builtins.open
    monkeypatch.setattr(builtins, "open", lambda *a, **k: (abiertos.append(a[0]), abrir(*a, **k))[1])
    respuesta = cliente.get(f"{API}/provisional", params={"ruta": ruta})
    como_una_ruta_que_no_existe(cliente, respuesta)
    assert not [a for a in abiertos if str(arte.RAIZ) in str(a)]


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
    esperado = {}
    for grupo in arte.grupos():
        for ruta in grupo.rutas:
            esperado[f"{grupo.clave}/{ruta.rsplit('/', 1)[1]}"] = ruta
    assert len(esperado) == len(arte.piezas())
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        assert copia.testzip() is None
        nombres = copia.namelist()
        assert len(nombres) == len(set(nombres)) == len(arte.piezas())
        assert set(nombres) == set(esperado)
        # Una de cada familia: la medida de la pieza, y el doble en los muebles.
        for ruta in (CORAZON, SUELO):
            pieza = arte_subido.pieza_de(ruta)
            clave = next(g.clave for g in arte.grupos() if ruta in g.rutas)
            veces = arte.REDUCCION if pieza.familia == "pieza" else 1
            with Image.open(io.BytesIO(copia.read(f"{clave}/{ruta.rsplit('/', 1)[1]}"))) as imagen:
                assert imagen.size == (pieza.ancho * veces, pieza.alto * veces)
        assert copia.read("efectos/corazon.png") == _del_repo(CORAZON)
    assert [archivo.closed for archivo in temporales] == [True]


def test_el_zip_de_provisionales_no_es_lo_subido(cliente, sin_ampliar, carpeta):
    assert subir(cliente, CORAZON, png(32, 32, 7)).status_code == 200
    respuesta = cliente.get(f"{API}/provisionales.zip")
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        assert copia.read("efectos/corazon.png") == _del_repo(CORAZON)


def test_en_el_zip_un_nombre_repetido_dentro_de_un_grupo_lleva_su_ruta_entera(cliente, monkeypatch):
    repetido = arte.Grupo("junto", "Junto", "lugares", ("pueblo/lugares/tienda.png", "escenas/tienda.png"))
    monkeypatch.setattr(arte, "grupos", lambda: (repetido,))
    respuesta = cliente.get(f"{API}/provisionales.zip")
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        assert sorted(copia.namelist()) == ["junto/escenas-tienda.png", "junto/pueblo-lugares-tienda.png"]


def test_si_falta_un_provisional_en_el_repo_el_zip_sale_sin_el_y_lo_avisa(cliente, sin_ampliar, monkeypatch, tmp_path, caplog):
    copia_del_arte = tmp_path / "arte-incompleta"
    shutil.copytree(arte.RAIZ, copia_del_arte)
    (copia_del_arte / CORAZON).unlink()
    monkeypatch.setattr(arte, "RAIZ", copia_del_arte)
    with caplog.at_level("WARNING", logger="gachamones"):
        respuesta = cliente.get(f"{API}/provisionales.zip")
    assert respuesta.status_code == 200
    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as copia:
        assert "efectos/corazon.png" not in copia.namelist()
        assert len(copia.namelist()) == len(arte.piezas()) - 1
    assert CORAZON in caplog.text


def test_las_descargas_de_provisionales_no_se_guardan(cliente, sin_ampliar):
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
