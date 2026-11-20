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
la tabla, sin abrir imágenes, y su forma no cambia sin cambiar el tablero.
"""
from __future__ import annotations

import json
import logging
import tempfile
import zipfile
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.requests import ClientDisconnect

import arte_subido
import config
import db
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


def _la_pieza(ruta: str) -> arte.Pieza:
    """La pieza del contrato con esa ruta, tal cual; si no la hay, el 404 de una ruta que no existe.

    Como dependencia, es la de `?ruta=`, y se mira antes de leer ningún cuerpo.
    """
    pieza = arte_subido.pieza_de(ruta)
    if pieza is None:
        raise HTTPException(status_code=404)
    return pieza


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
    return await _leer_hasta(request, arte_subido.LIMITE_DE_BYTES, "La imagen pesa más de 4 MB.")


async def _cuerpo_de_volver(request: Request) -> bytes:
    return await _leer_hasta(request, TOPE_DE_VOLVER, "Eso es demasiado grande.")


def _lo_vigente() -> dict[str, tuple[str, int, int]]:
    """Ruta → (archivo, ancho, alto) de lo que se sirve hoy: una sola lectura de la tabla."""
    return db.arte_vigente(arte_subido.medidas())


def _subida(pieza: arte.Pieza, vigente: dict[str, tuple[str, int, int]]) -> dict | None:
    """Lo subido que se ve hoy de esa pieza, o `None` si se ve su recuadro provisional.

    Quién y cuándo son los de la última subida de esa misma imagen: tras volver a
    la anterior se ve quién la subió, no quién volvió (eso lo cuenta el historial).
    """
    if pieza.ruta not in vigente:
        return None
    archivo = vigente[pieza.ruta][0]
    subida = next((r for r in db.historial_del_arte(pieza.ruta)
                   if r.accion == "subir" and r.archivo == archivo), None)
    if subida is None:
        return None
    return {"direccion": direccion_de(archivo), "quien": subida.quien, "cuando": subida.cuando.isoformat()}


def _medida_cambiada(pieza: arte.Pieza, puesto: dict[str, tuple[str, int, int]]) -> dict | None:
    """La medida de lo que tiene puesto la pieza, si no es la que hoy pide el contrato.

    Eso no se sirve (se ve el recuadro) y la página del dibujante lo dice; si no, `None`.
    """
    if pieza.ruta not in puesto:
        return None
    _, ancho, alto = puesto[pieza.ruta]
    if (ancho, alto) == (pieza.ancho, pieza.alto):
        return None
    return {"ancho": ancho, "alto": alto}


def _vista(pieza: arte.Pieza, vigente: dict[str, tuple[str, int, int]],
           puesto: dict[str, tuple[str, int, int]]) -> dict:
    """Una pieza como la enseña la página del dibujante.

    `ancho` y `alto` son la medida que pide el contrato; en la familia `pieza` vale
    también el original, al doble, que `arte_subido` reduce.
    """
    original = None
    if pieza.familia == "pieza":
        original = {"ancho": pieza.ancho * arte.REDUCCION, "alto": pieza.alto * arte.REDUCCION}
    return {"ruta": pieza.ruta, "ancho": pieza.ancho, "alto": pieza.alto, "original": original,
            "subida": _subida(pieza, vigente), "medida_cambiada": _medida_cambiada(pieza, puesto)}


def _al_dia(pieza: arte.Pieza) -> dict:
    return _vista(pieza, _lo_vigente(), db.arte_puesto())


@router.get("/piezas")
def las_piezas() -> dict:
    """Las piezas del contrato por grupos, con su medida y lo subido que se ve hoy."""
    vigente, puesto = _lo_vigente(), db.arte_puesto()
    por_ruta = {p.ruta: p for p in arte.piezas()}
    return {"grupos": [
        {"clave": g.clave, "nombre": g.nombre, "familia": g.familia,
         "piezas": [_vista(por_ruta[ruta], vigente, puesto) for ruta in g.rutas]}
        for g in arte.grupos()
    ]}


@router.post("/subir", dependencies=[Depends(con_cabecera)])
def subir_una_imagen(
    pieza: arte.Pieza = Depends(_la_pieza),
    persona: Persona = Depends(dibujante_actual),
    cuerpo: bytes = Depends(_png_subido),
) -> dict:
    """El PNG crudo del cuerpo, para la pieza de `?ruta=`; devuelve la pieza al día."""
    try:
        arte_subido.subir(config.RUTA_ARTE_SUBIDO, pieza, cuerpo, persona.usuario, db.ahora_utc())
    except arte_subido.NoVale as no_vale:
        raise problema(400, "no_vale", no_vale.mensaje) from None
    return _al_dia(pieza)


@router.post("/volver", dependencies=[Depends(con_cabecera)])
def volver_atras(
    persona: Persona = Depends(dibujante_actual),
    cuerpo: bytes = Depends(_cuerpo_de_volver),
) -> dict:
    """`{"ruta", "a": "anterior" | "provisional"}`; devuelve la pieza al día."""
    try:
        datos = json.loads(cuerpo)
    except (ValueError, RecursionError):
        raise no_se_entiende() from None
    if not isinstance(datos, dict) or not isinstance(datos.get("ruta"), str):
        raise no_se_entiende()
    if datos.get("a") not in ("anterior", "provisional"):
        raise no_se_entiende()
    pieza = _la_pieza(datos["ruta"])
    try:
        arte_subido.volver(config.RUTA_ARTE_SUBIDO, pieza, datos["a"], persona.usuario, db.ahora_utc())
    except arte_subido.NoVale as no_vale:
        raise problema(400, "no_vale", no_vale.mensaje) from None
    return _al_dia(pieza)


@router.get("/historial")
def el_historial(pieza: arte.Pieza = Depends(_la_pieza)) -> dict:
    """Todo lo que le ha pasado a la pieza de `?ruta=`, lo último primero."""
    return {"ruta": pieza.ruta, "historial": [
        {"accion": r.accion, "direccion": direccion_de(r.archivo) if r.archivo else None,
         "ancho": r.ancho, "alto": r.alto, "quien": r.quien, "cuando": r.cuando.isoformat()}
        for r in db.historial_del_arte(pieza.ruta)
    ]}


@router.get("/avance")
def el_avance() -> dict:
    """El contrato con el tablero del arte: por grupo, cuántas piezas tiene y cuántas
    tienen hoy una imagen subida con la medida del contrato."""
    vigente = _lo_vigente()
    return {"grupos": [
        {"clave": g.clave, "nombre": g.nombre, "familia": g.familia,
         "total": len(g.rutas), "hechas": sum(1 for ruta in g.rutas if ruta in vigente)}
        for g in arte.grupos()
    ]}


def _a_trozos(archivo) -> Iterator[bytes]:
    try:
        while trozo := archivo.read(_TROZO_DE_LA_COPIA):
            yield trozo
    finally:
        archivo.close()


@router.get("/copia.zip")
def la_copia() -> StreamingResponse:
    """Todo lo vigente en un zip, cada imagen con su ruta del contrato como nombre.

    Se arma en un temporal sin nombre en disco (se va solo al cerrarse, también si
    la descarga se corta) y se manda a trozos: nada se carga entero en memoria.
    Una imagen que falta en disco se deja fuera y se avisa en el registro.
    """
    vigente = _lo_vigente()
    archivo = tempfile.TemporaryFile()
    try:
        with zipfile.ZipFile(archivo, "w") as copia:
            for ruta, (nombre, _, _) in sorted(vigente.items()):
                try:
                    copia.write(config.RUTA_ARTE_SUBIDO / nombre, arcname=ruta)
                except FileNotFoundError:
                    log.warning("Falta en disco la imagen subida de %s; la copia sale sin ella.", ruta)
        largo = archivo.tell()
        archivo.seek(0)
    except BaseException:
        archivo.close()
        raise
    return StreamingResponse(
        _a_trozos(archivo), media_type="application/zip",
        headers={"Content-Length": str(largo), "Content-Disposition": 'attachment; filename="copia.zip"'},
    )
