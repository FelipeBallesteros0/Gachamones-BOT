"""El servicio web de Gachamon: todo cuelga de `/gachamon`.

Importar este módulo no hace nada más que definir la fábrica y crear la app: la
base se prepara en el ciclo de vida de FastAPI, al arrancar el servidor.
"""
from __future__ import annotations

import hashlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import MutableHeaders
from starlette.exceptions import HTTPException as ErrorHTTP
from starlette.types import ASGIApp, Message, Receive, Scope, Send

import config
import db
import economia
import retrato
from web import PREFIJO, cuenta, ficha, juego, mochila, retratos, tienda
from web.sesion import Persona, persona_actual, problema

ESTATICOS = Path(__file__).resolve().parent / "static"

log = logging.getLogger("gachamones")

_ERRORES_CONOCIDOS = {
    404: ("no_existe", "Eso no existe."),
    405: ("metodo", "Eso no se puede hacer así."),
}

API = f"{PREFIJO}/api/"
TOPE_DEL_CUERPO = 16 * 1024
DEMASIADO = ("demasiado", "Eso es demasiado grande.")


def _se_pasa(declarado: bytes, tope: int) -> bool:
    """Si un `Content-Length` no es un número o pasa del tope.

    Se cuentan las cifras antes de convertir: `int` no acepta más de 4300, y
    una cabecera así no tiene que acabar en un 500.
    """
    if not declarado.isdigit():
        return True
    cifras = declarado.lstrip(b"0") or b"0"
    return len(cifras) > len(str(tope)) or int(cifras) > tope


class _TopeDelCuerpo:
    """Un cuerpo grande no llega a cargarse en memoria, se haya entrado o no.

    FastAPI lee el cuerpo entero antes de mirar la cookie, así que la sesión no
    frena a un anónimo. Esto va delante, en ASGI puro, para lo que cuelga de la
    api: un `Content-Length` que no es un número o que pasa del tope se contesta
    413 sin leer nada; y como un cuerpo troceado no lo declara (o miente), se
    cuenta además lo que va llegando y se corta en cuanto se pasa.
    """

    def __init__(self, app: ASGIApp, tope: int = TOPE_DEL_CUERPO) -> None:
        self.app = app
        self.tope = tope

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(API):
            await self.app(scope, receive, send)
            return
        declarados = [v for k, v in scope["headers"] if k.lower() == b"content-length"]
        if any(_se_pasa(v, self.tope) for v in declarados):
            clave, mensaje = DEMASIADO
            respuesta = JSONResponse(
                status_code=413,
                content={"detail": {"clave": clave, "mensaje": mensaje}},
            )
            await respuesta(scope, receive, send)
            return

        llegado = 0

        async def contando() -> Message:
            nonlocal llegado
            mensaje = await receive()
            if mensaje["type"] == "http.request":
                llegado += len(mensaje.get("body", b""))
                if llegado > self.tope:
                    # FastAPI deja pasar el HTTPException que salga de aquí
                    # mientras lee el cuerpo, y lo contesta `_error_http`.
                    raise problema(413, *DEMASIADO)
            return mensaje

        await self.app(scope, contando, send)


class _Cabeceras:
    """Lo que lleva toda respuesta del servicio, sea cual sea.

    Nadie la mete en un marco ni adivina su tipo; y lo de la api no se guarda
    en ninguna caché, tampoco los errores. Los retratos no son de la api y
    conservan su caché de un año. Lo de la api dice además de qué versión es
    el servidor, también un error: así una página de una versión anterior se
    entera y se recarga.
    """

    def __init__(self, app: ASGIApp, version: str) -> None:
        self.app = app
        self.version = version

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        de_la_api = scope["path"].startswith(API)

        async def con_cabeceras(mensaje: Message) -> None:
            if mensaje["type"] == "http.response.start":
                mensaje.setdefault("headers", [])
                cabeceras = MutableHeaders(scope=mensaje)
                cabeceras["X-Content-Type-Options"] = "nosniff"
                cabeceras["Content-Security-Policy"] = "frame-ancestors 'none'"
                if de_la_api:
                    cabeceras["Cache-Control"] = "no-store"
                    cabeceras["X-Gachamon-Version"] = self.version
            await send(mensaje)

        await self.app(scope, receive, con_cabeceras)


class _Servicio(FastAPI):
    def build_middleware_stack(self) -> ASGIApp:
        # Las cabeceras van por fuera de todo, también del que contesta un 500,
        # que manda su respuesta saltándose los middlewares de dentro. Starlette
        # lo arma en su primera llamada, cuando `crear_app` ya puso la versión.
        return _Cabeceras(super().build_middleware_stack(), self.state.version)


def calcular_version(carpeta: Path = ESTATICOS) -> str:
    """Huella corta del contenido de `carpeta`: nombres y bytes, nunca fechas.

    Para el mismo commit da lo mismo en cualquier máquina.
    """
    huella = hashlib.sha256()
    for archivo in sorted(p for p in carpeta.rglob("*") if p.is_file()):
        huella.update(archivo.relative_to(carpeta).as_posix().encode("utf-8"))
        huella.update(b"\0")
        huella.update(archivo.read_bytes())
        huella.update(b"\0")
    return huella.hexdigest()[:12]


def _avisar_de_lo_que_falta() -> None:
    """Un aviso por cada cosa del `.env` sin la cual el juego no funciona.

    Son `warning` y no `info` porque uvicorn no configura el registrador raíz y
    los `info` no saldrían. El valor de la clave no se escribe nunca.
    """
    if not config.ROWINO_SECRET_KEY:
        log.warning(
            "Falta ROWINO_SECRET_KEY en el .env: nadie podrá entrar al juego."
        )
    if not Path(config.RUTA_ROWINO_BD).is_file():
        log.warning(
            "No existe la base de Rowino en %s (RUTA_ROWINO_BD en el .env): "
            "nadie podrá entrar al juego.", config.RUTA_ROWINO_BD,
        )
    if not config.GUILD_WEB:
        log.warning(
            "GUILD_WEB vale 0 (sin GUILD_WEB ni GUILD_ID en el .env): nadie "
            "podrá empezar a jugar ni pedir un código para vincular."
        )


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI):
    _avisar_de_lo_que_falta()
    retrato.version()  # se calcula al arrancar, no en la primera petición
    devolucion = economia.poner_al_dia(db.ahora_utc())
    if devolucion.piezas:
        log.info(
            "Devueltos marcos y tintes retirados: %d personas, %d piezas, %d gemas",
            devolucion.personas, devolucion.piezas, devolucion.gemas,
        )
    else:
        log.debug("Devolución de marcos y tintes retirados: nada que devolver")
    yield


def crear_app() -> FastAPI:
    app = _Servicio(
        lifespan=_ciclo_de_vida,
        docs_url=None, redoc_url=None, openapi_url=None,
    )
    app.add_middleware(_TopeDelCuerpo)
    version = calcular_version()
    app.state.version = version
    portada = (ESTATICOS / "index.html").read_text(encoding="utf-8")
    portada = portada.replace("__V__", version)

    @app.exception_handler(RequestValidationError)
    def _peticion_mal_hecha(
        peticion: Request, error: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": {
                "clave": "peticion",
                "mensaje": "La petición no se entiende.",
            }},
        )

    @app.exception_handler(ErrorHTTP)
    def _error_http(peticion: Request, error: ErrorHTTP) -> JSONResponse:
        # Todo error lleva `clave` y `mensaje`, también el 404 de una dirección
        # que no existe y el 405 de un verbo que no toca.
        detalle = error.detail
        if not (isinstance(detalle, dict) and "clave" in detalle and "mensaje" in detalle):
            clave, mensaje = _ERRORES_CONOCIDOS.get(
                error.status_code, ("error", "Algo salió mal."),
            )
            detalle = {"clave": clave, "mensaje": mensaje}
        return JSONResponse(
            status_code=error.status_code, content={"detail": detalle},
            headers=error.headers,
        )

    app.include_router(cuenta.router, prefix=f"{PREFIJO}/api")
    app.include_router(juego.router, prefix=f"{PREFIJO}/api")
    app.include_router(tienda.router, prefix=f"{PREFIJO}/api")
    app.include_router(mochila.router, prefix=f"{PREFIJO}/api")
    app.include_router(ficha.router, prefix=f"{PREFIJO}/api")
    app.include_router(retratos.router, prefix=PREFIJO)

    @app.get(f"{PREFIJO}/api/salud")
    def salud() -> dict:
        return {"ok": True}

    @app.get(f"{PREFIJO}/api/sesion")
    def sesion(persona: Persona = Depends(persona_actual)) -> dict:
        return {"usuario": persona.usuario}

    @app.get(PREFIJO, include_in_schema=False)
    def sin_barra() -> RedirectResponse:
        return RedirectResponse(f"{PREFIJO}/")

    @app.get(f"{PREFIJO}/", include_in_schema=False)
    def inicio() -> HTMLResponse:
        return HTMLResponse(portada, headers={"Cache-Control": "no-cache"})

    # Los estáticos sólo existen bajo la versión vigente: Cloudflare los guarda
    # horas, y así un despliegue nuevo se ve al momento sin tocar su caché.
    app.mount(
        f"{PREFIJO}/static/{version}", StaticFiles(directory=ESTATICOS),
        name="estaticos",
    )
    return app


app = crear_app()
