"""La api de las herramientas del dibujante, bajo `/monsteropolis_dibujante/api`.

Es un adaptador fino, como el resto de `web/`: qué vale y cómo se guarda una
subida o una vuelta atrás es de `arte_subido` (`subir` y `volver` son lo único
que se llama para cambiar algo), lo vigente y el historial los lee `db`, y las
piezas y sus grupos son el contrato del arte (`web/arte.py`).

Toda ruta pide el permiso del dibujante (`dibujante_actual`), antes que nada: a
quien no lo tiene se le contesta lo mismo que a una ruta que no existe, sin
mirar su cabecera ni leer su cuerpo. Una ruta de pieza que no está en el
contrato también es un 404, y nunca se arma una ruta de archivo con ella.

Los cuerpos se leen a mano y a trozos, después del permiso, y se cortan en
cuanto pasan de su tope: el tope de la api del juego no cuelga de este prefijo,
y FastAPI leería un cuerpo declarado entero antes de mirar la sesión.

El avance (`/avance`) es el contrato con el tablero del arte del sitio, que lo
pide cada pocos segundos por cada pestaña abierta: sale de una sola lectura de
la tabla, sin abrir imágenes, y su forma no cambia sin cambiar el tablero. Cuenta
casillas, no rutas, y sólo de los grupos con tarjeta.

Las criaturas son miles de capas: la lista general y los zips de arriba no las
traen, y cada grupo se pide entero con `?grupo=<clave>`. La clave sólo se compara
con las de `arte.grupos()`: nunca arma una ruta de archivo.
"""
from __future__ import annotations

import io
import json
import logging
import tempfile
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from PIL import Image
from starlette.background import BackgroundTask
from starlette.requests import ClientDisconnect

import arte_subido
import config
import cosmeticos
import db
import retrato
from web import PREFIJO, arte
from web.sesion import Persona, con_cabecera, dibujante_actual, problema
from web.tienda import no_se_entiende

PREFIJO_DIBUJANTE = "/monsteropolis_dibujante"
# Lo único que pide volver es un objeto de dos campos.
TOPE_DE_VOLVER = 16 * 1024
_TROZO_DE_LA_COPIA = 64 * 1024

log = logging.getLogger("gachamones")

router = APIRouter(dependencies=[Depends(dibujante_actual)])


def direccion_de(archivo: str) -> str:
    """Dónde se le sirve a quien juega una imagen subida: su nombre es su contenido."""
    return f"{PREFIJO}/arte-subido/{archivo}"


def _el_lugar(ruta: str) -> arte.Lugar:
    """El lugar de subida con esa ruta, tal cual; si no lo hay, el 404 de una ruta que no existe.

    Como dependencia, es la de `?ruta=`, y se mira antes de leer ningún cuerpo.
    """
    lugar = arte.lugar_de(ruta)
    if lugar is None:
        raise HTTPException(status_code=404)
    return lugar


def _se_declara_mas_de(request: Request, tope: int) -> bool:
    """Si el `Content-Length` no es un número o pasa de `tope` (sin convertir uno de miles de cifras)."""
    declarado = request.headers.get("content-length")
    if declarado is None:
        return False
    if not (declarado.isascii() and declarado.isdigit()):
        return True
    cifras = declarado.lstrip("0") or "0"
    return len(cifras) > len(str(tope)) or int(cifras) > tope


async def _leer_hasta(request: Request, tope: int, demasiado: str) -> bytes:
    """El cuerpo, leído a trozos; en cuanto pasa de `tope`, un 413 sin leer el resto."""
    if _se_declara_mas_de(request, tope):
        raise problema(413, "demasiado", demasiado)
    trozos, llegado = [], 0
    try:
        async for trozo in request.stream():
            llegado += len(trozo)
            if llegado > tope:
                raise problema(413, "demasiado", demasiado)
            trozos.append(trozo)
    except ClientDisconnect:
        # Quien mandaba se fue: no hay a quién contestar, y no es un fallo nuestro.
        raise HTTPException(status_code=400) from None
    return b"".join(trozos)


# Son `async` sólo para leer el cuerpo a trozos; las rutas siguen siendo `def`.
async def _png_subido(request: Request) -> bytes:
    return await _leer_hasta(request, arte_subido.LIMITE_DE_BYTES, arte_subido.PESA_DEMASIADO)


async def _cuerpo_de_volver(request: Request) -> bytes:
    return await _leer_hasta(request, TOPE_DE_VOLVER, "Eso es demasiado grande.")


def _lo_vigente() -> dict[str, tuple[str, int, int]]:
    """Ruta → (archivo, ancho, alto) de lo que se sirve hoy: una sola lectura de la tabla."""
    return db.arte_vigente(arte_subido.medidas())


@dataclass(frozen=True)
class _LoSubido:
    """Lo que piden las vistas de los lugares, leído de la tabla una vez por petición.

    Son tres consultas, haya pocos lugares subidos o muchos: cada conexión de `db`
    vive hasta que pasa el recolector, y una por lugar llegó a agotar los
    descriptores del servicio.
    """
    vigente: dict[str, tuple[str, int, int]]
    puesto: dict[str, db.ArtePuesto]
    quien_subio: dict[str, tuple[str, str, datetime]]
    al_dia: set[str]


def _lo_subido() -> _LoSubido:
    puesto = db.arte_puesto_entero()
    return _LoSubido(_lo_vigente(), puesto, db.quien_subio_lo_puesto(), _al_dia(puesto))


def _al_dia(puesto: dict[str, db.ArtePuesto]) -> set[str]:
    """Las rutas cuyo original puesto mide lo que hoy pide su lugar.

    Una fila de antes de guardar originales tiene por original su propio archivo, que
    mide lo servido: en la pieza no está al día hasta que se vuelva a subir.
    """
    return {ruta for ruta, p in puesto.items()
            if (lugar := arte.lugar_de(ruta)) is not None
            and (p.ancho_original, p.alto_original) == (lugar.ancho, lugar.alto)}


def _subida(lugar: arte.Lugar, lo: _LoSubido) -> dict | None:
    """Lo subido que se ve hoy de ese lugar, o `None` si se ve su recuadro provisional
    o lo puesto no tiene la medida de subida.

    Quién y cuándo son los de la última subida de esa misma imagen: tras volver a
    la anterior se ve quién la subió, no quién volvió (eso lo cuenta el historial).
    Si una subida se cruzó entre las lecturas y no coinciden, sale como provisional
    y la próxima lista ya la trae.
    """
    # Lo que el juego no pinta nunca está entre lo vigente (el bloque de la portada): se ve lo puesto.
    if (lugar.en_el_juego and lugar.ruta not in lo.vigente) or lugar.ruta not in lo.al_dia:
        return None
    puesto = lo.puesto[lugar.ruta]
    archivo = lo.vigente[lugar.ruta][0] if lugar.en_el_juego else puesto.archivo
    de_quien = lo.quien_subio.get(lugar.ruta)
    if de_quien is None or de_quien[0] != archivo or puesto.archivo != archivo:
        return None
    _, quien, cuando = de_quien
    return {"direccion": direccion_de(archivo), "original": direccion_de(puesto.original),
            "quien": quien, "cuando": cuando.isoformat()}


def _medida_cambiada(lugar: arte.Lugar, lo: _LoSubido) -> dict | None:
    """La medida del original que tiene puesto el lugar, si no es la que hoy pide.

    Eso no cuenta como hecho (se ve el recuadro) y la página del dibujante lo dice; si no, `None`.
    """
    if lugar.ruta not in lo.puesto or lugar.ruta in lo.al_dia:
        return None
    p = lo.puesto[lugar.ruta]
    return {"ancho": p.ancho_original, "alto": p.alto_original}


def _miniatura(lugar: arte.Lugar) -> str | None:
    """Dónde pedir el provisional chico de un lugar que el juego no pinta; los del juego ya
    tienen su imagen servida, y la página la pide por su ruta."""
    if lugar.en_el_juego:
        return None
    return f"{PREFIJO_DIBUJANTE}/api/provisional?ruta={quote(lugar.ruta, safe='/')}&miniatura=1"


def _criatura(capa: arte.Capa | None) -> dict | None:
    """Qué capa de criatura es un lugar, para el título de su tarjeta; `None` si no lo es."""
    if capa is None:
        return None
    sombrero = next((s.nombre for s in cosmeticos.SOMBREROS if s.clave == capa.cual), None) \
        if capa.capa == "sombrero" else None
    return {"nivel": capa.nivel, "etapa": capa.etapa, "capa": capa.capa, "cual": capa.cual,
            "nombre_del_sombrero": sombrero, "orientacion": capa.orientacion}


def _cubierta(lugar: arte.Lugar, lo: _LoSubido) -> dict | None:
    """Quién cubre una cara o un sombrero de forma que no tiene su capa propia al día.

    Si la de su especie está al día, `{"por": "especie", ...}`; si no, la común. La
    `direccion` es la imagen chica de la que la cubre. Si no, `None`."""
    capa = lugar.criatura
    if capa is None or capa.nivel != "forma" or capa.capa == "cuerpo" or lugar.ruta in lo.al_dia:
        return None
    candidatas = (("especie", replace(capa, nivel="especie", etapa=None)),
                  ("comun", replace(capa, nivel="comun", especie=None, etapa=None)))
    for por, candidata in candidatas:
        de_quien = arte.lugar_de(arte.ruta_de_capa(candidata))
        if de_quien is not None and (subida := _subida(de_quien, lo)) is not None:
            return {"por": por, "direccion": subida["direccion"]}
    return None


def _vista(lugar: arte.Lugar, lo: _LoSubido) -> dict:
    """Un lugar como lo enseña la página del dibujante.

    `ancho` y `alto` son la única medida de subida que vale para ese lugar.
    """
    return {"ruta": lugar.ruta, "ancho": lugar.ancho, "alto": lugar.alto,
            "subida": _subida(lugar, lo), "medida_cambiada": _medida_cambiada(lugar, lo),
            "objeto": lugar.objeto, "estado": lugar.estado, "miniatura": _miniatura(lugar),
            "criatura": _criatura(lugar.criatura), "cubierta": _cubierta(lugar, lo)}


def _la_vista(lugar: arte.Lugar) -> dict:
    return _vista(lugar, _lo_subido())


def _el_grupo(grupo: str | None = None) -> arte.Grupo | None:
    """El grupo de `?grupo=`, o `None` si no se pidió ninguno; una clave que no es de ningún
    grupo es el 404 de una ruta que no existe. Sólo se compara con las claves conocidas."""
    if grupo is None:
        return None
    pedido = next((g for g in arte.grupos() if g.clave == grupo), None)
    if pedido is None:
        raise HTTPException(status_code=404)
    return pedido


def _resumen(g: arte.Grupo, al_dia: set[str]) -> dict:
    """Lo que dice un grupo de sí mismo: sus casillas, y las hechas (alguna ruta candidata al día)."""
    return {"clave": g.clave, "nombre": g.nombre, "familia": g.familia, "total": len(g.casillas),
            "hechas": sum(1 for casilla in g.casillas if any(ruta in al_dia for ruta in casilla))}


@router.get("/piezas")
def las_piezas(pedido: arte.Grupo | None = Depends(_el_grupo)) -> dict:
    """Los grupos del contrato, cada uno con sus piezas, su medida y lo subido que se ve hoy.

    Los de las criaturas salen sin `piezas` (son miles); `?grupo=<clave>` da ese grupo entero."""
    lo = _lo_subido()
    grupos = (pedido,) if pedido else arte.grupos()
    return {"grupos": [
        {**_resumen(g, lo.al_dia),
         **({"piezas": [_vista(arte.lugar_de(ruta), lo) for ruta in g.rutas]}
            if pedido or g.familia != "criaturas" else {})}
        for g in grupos
    ]}


@router.post("/subir", dependencies=[Depends(con_cabecera)])
def subir_una_imagen(
    lugar: arte.Lugar = Depends(_el_lugar),
    persona: Persona = Depends(dibujante_actual),
    cuerpo: bytes = Depends(_png_subido),
) -> dict:
    """El PNG crudo del cuerpo, para el lugar de `?ruta=`; devuelve su vista al día."""
    try:
        arte_subido.subir(config.RUTA_ARTE_SUBIDO, lugar, cuerpo, persona.usuario, db.ahora_utc())
    except arte_subido.NoVale as no_vale:
        raise problema(400, "no_vale", no_vale.mensaje) from None
    return _la_vista(lugar)


@router.post("/volver", dependencies=[Depends(con_cabecera)])
def volver_atras(
    persona: Persona = Depends(dibujante_actual),
    cuerpo: bytes = Depends(_cuerpo_de_volver),
) -> dict:
    """`{"ruta", "a": "anterior" | "provisional"}`; devuelve su vista al día."""
    try:
        datos = json.loads(cuerpo)
    except (ValueError, RecursionError):
        raise no_se_entiende() from None
    if not isinstance(datos, dict) or not isinstance(datos.get("ruta"), str):
        raise no_se_entiende()
    if datos.get("a") not in ("anterior", "provisional"):
        raise no_se_entiende()
    lugar = _el_lugar(datos["ruta"])
    try:
        arte_subido.volver(config.RUTA_ARTE_SUBIDO, lugar, datos["a"], persona.usuario, db.ahora_utc())
    except arte_subido.NoVale as no_vale:
        raise problema(400, "no_vale", no_vale.mensaje) from None
    return _la_vista(lugar)


@router.get("/historial")
def el_historial(lugar: arte.Lugar = Depends(_el_lugar)) -> dict:
    """Todo lo que le ha pasado al lugar de `?ruta=`, lo último primero."""
    return {"ruta": lugar.ruta, "historial": [
        {"accion": r.accion, "direccion": direccion_de(r.archivo) if r.archivo else None,
         "original": direccion_de(r.original) if r.original else None,
         "ancho": r.ancho_original, "alto": r.alto_original,
         "quien": r.quien, "cuando": r.cuando.isoformat()}
        for r in db.historial_del_arte(lugar.ruta)
    ]}


@router.get("/avance")
def el_avance() -> dict:
    """El contrato con el tablero del arte: por grupo con tarjeta, cuántas casillas tiene y
    cuántas tienen hoy una imagen subida con la medida de subida (en las criaturas, la de la
    forma, la de la especie o la común)."""
    al_dia = _al_dia(db.arte_puesto_entero())
    return {"grupos": [_resumen(g, al_dia) for g in arte.grupos() if g.con_tarjeta]}


def _a_trozos(archivo) -> Iterator[bytes]:
    try:
        while trozo := archivo.read(_TROZO_DE_LA_COPIA):
            yield trozo
    finally:
        archivo.close()


def _temporal_del_zip():
    """Donde se arma un zip: un temporal sin nombre en disco (se va solo al cerrarse), en la
    carpeta de lo subido y no en el `/tmp` del sistema, que puede ser memoria; con los
    originales, un zip son cientos de MB. Crea la carpeta, pero no lo que hay encima."""
    config.RUTA_ARTE_SUBIDO.mkdir(exist_ok=True)
    return tempfile.TemporaryFile(dir=config.RUTA_ARTE_SUBIDO)


def _nombre_del_zip(antes: str, pedido: arte.Grupo | None) -> str:
    return f'attachment; filename="{antes}{"-" + pedido.clave.replace("/", "-") if pedido else ""}.zip"'


@router.get("/copia.zip")
def la_copia(pedido: arte.Grupo | None = Depends(_el_grupo)) -> StreamingResponse:
    """El original de todo lo que tiene algo puesto (esté al día o no), en un zip, cada
    imagen con su ruta del contrato como nombre.

    Sin `?grupo=`, sin las criaturas (se bajan por especie); con él, sólo las de ese grupo.

    Se arma en un temporal sin nombre en disco, junto a lo subido (`_temporal_del_zip`), y se
    manda a trozos: nada se carga entero en memoria. El temporal se cierra al acabar la
    respuesta, también si la descarga se corta: entonces el generador se queda
    a medias, y sin la tarea del final seguiría abierto hasta que pasara el recolector.
    Una imagen que falta en disco se deja fuera y se avisa en el registro.
    """
    puesto = db.arte_puesto_entero()
    archivo = _temporal_del_zip()
    try:
        with zipfile.ZipFile(archivo, "w") as copia:
            for ruta, lo_puesto in sorted(puesto.items()):
                if pedido is not None:
                    if ruta not in pedido.rutas:
                        continue
                elif (lugar := arte.lugar_de(ruta)) is not None and lugar.familia == "criaturas":
                    continue
                try:
                    copia.write(config.RUTA_ARTE_SUBIDO / lo_puesto.original, arcname=ruta)
                except FileNotFoundError:
                    log.warning("Falta en disco la imagen subida de %s; la copia sale sin ella.", ruta)
        largo = archivo.tell()
        archivo.seek(0)
    except BaseException:
        archivo.close()
        raise
    return StreamingResponse(
        _a_trozos(archivo), media_type="application/zip",
        headers={"Content-Length": str(largo), "Content-Disposition": _nombre_del_zip("copia", pedido)},
        background=BackgroundTask(archivo.close),
    )


def _el_provisional(lugar: arte.Lugar) -> bytes:
    """El PNG del provisional del lugar, tal como baja el dibujante, a su medida de subida.

    En la familia `pieza`, el original de `fuentes/<ruta>` si existe; si no, el
    provisional servido ampliado al doble sin suavizar (`NEAREST`). En las demás, el
    archivo tal cual. En las criaturas, la capa de frente de hoy (`retrato.capa_de_frente`)
    ampliada ×4. Nunca sale de lo subido. Si el archivo no está, lanza `FileNotFoundError`.
    """
    if lugar.reduccion == 1:
        return _el_provisional_servido(lugar).read_bytes()
    if lugar.criatura is None:
        try:
            return (arte.FUENTES / lugar.ruta).read_bytes()
        except FileNotFoundError:
            pass
    with Image.open(_el_provisional_chico(lugar)) as chico:
        grande = chico.convert("RGBA").resize(
            (chico.width * lugar.reduccion, chico.height * lugar.reduccion), Image.NEAREST)
    salida = io.BytesIO()
    # Compresión rápida: se arma en cada petición, y el tamaño no importa para quien baja.
    grande.save(salida, "PNG", compress_level=1)
    return salida.getvalue()


def _el_provisional_servido(lugar: arte.Lugar):
    """El archivo del provisional que sirve el juego (a su medida servida)."""
    return (arte.RAIZ if lugar.en_el_juego else arte.RAIZ_POR_VENIR) / lugar.ruta


def _el_provisional_chico(lugar: arte.Lugar):
    """El provisional a su medida servida, para abrirlo: un archivo, o (en las criaturas, que
    no tienen archivos, serían miles) la capa de frente armada al vuelo."""
    capa = lugar.criatura
    if capa is None:
        return _el_provisional_servido(lugar)
    return io.BytesIO(retrato.capa_de_frente(capa.especie, capa.etapa, capa.capa, capa.cual))


@router.get("/provisional")
def el_provisional(lugar: arte.Lugar = Depends(_el_lugar), miniatura: bool = False) -> Response:
    """El provisional del lugar de `?ruta=`, como descarga.

    Con `miniatura`, el provisional servido sin ampliar y sin `Content-Disposition`: es
    lo que enseña la página en vez de bajarlo.
    """
    try:
        if miniatura:
            if lugar.criatura is not None:
                return Response(_el_provisional_chico(lugar).getvalue(), media_type="image/png")
            return Response(_el_provisional_servido(lugar).read_bytes(), media_type="image/png")
        cuerpo = _el_provisional(lugar)
    except FileNotFoundError:
        raise HTTPException(status_code=404) from None
    nombre = f"provisional-{lugar.ruta.replace('/', '-')}"
    return Response(cuerpo, media_type="image/png",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


def _nombres_en_el_zip(grupo: arte.Grupo) -> dict[str, str]:
    """Ruta → nombre dentro del zip, en la carpeta del grupo (`<clave del grupo>/`).

    La ruta que ya cae dentro de esa carpeta va con su ruta relativa a ella: en una especie,
    `bebe/cuerpo-se.png`, como en `la_copia` (los nombres se repiten entre etapas). Las demás,
    con su último tramo; si en el grupo se repite, las que lo repiten llevan la ruta entera
    con guiones.
    """
    carpeta = f"{grupo.clave}/"
    ultimos = [ruta.rsplit("/", 1)[1] for ruta in grupo.rutas]
    return {ruta: ruta if ruta.startswith(carpeta)
            else f"{carpeta}{ruta.replace('/', '-') if ultimos.count(ultimo) > 1 else ultimo}"
            for ruta, ultimo in zip(grupo.rutas, ultimos)}


@router.get("/provisionales.zip")
def los_provisionales(pedido: arte.Grupo | None = Depends(_el_grupo)) -> StreamingResponse:
    """Los provisionales en un zip, cada uno en la carpeta de su grupo.

    Sin `?grupo=`, todos menos las criaturas: son miles, y se bajan por especie. Se arma y se
    manda como `la_copia`. Un provisional que falta en el repo se deja fuera y se avisa en el registro.
    """
    grupos = (pedido,) if pedido else [g for g in arte.grupos() if g.familia != "criaturas"]
    archivo = _temporal_del_zip()
    try:
        with zipfile.ZipFile(archivo, "w") as copia:
            for grupo in grupos:
                for ruta, nombre in _nombres_en_el_zip(grupo).items():
                    try:
                        copia.writestr(nombre, _el_provisional(arte.lugar_de(ruta)))
                    except FileNotFoundError:
                        log.warning("Falta en el repo el provisional de %s; el zip sale sin él.", ruta)
        largo = archivo.tell()
        archivo.seek(0)
    except BaseException:
        archivo.close()
        raise
    return StreamingResponse(
        _a_trozos(archivo), media_type="application/zip",
        headers={"Content-Length": str(largo),
                 "Content-Disposition": _nombre_del_zip("provisionales", pedido)},
        background=BackgroundTask(archivo.close),
    )
