"""El servicio web de Gachamon: todo cuelga de `/gachamon`.

Importar este módulo no hace nada más que definir la fábrica y crear la app: la
base se prepara en el ciclo de vida de FastAPI, al arrancar el servidor.
"""
from __future__ import annotations

import hashlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import db
import economia
from web.sesion import Persona, persona_actual

PREFIJO = "/gachamon"
ESTATICOS = Path(__file__).resolve().parent / "static"

log = logging.getLogger("gachamones")


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


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI):
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
    app = FastAPI(
        lifespan=_ciclo_de_vida,
        docs_url=None, redoc_url=None, openapi_url=None,
    )
    version = calcular_version()
    app.state.version = version
    portada = (ESTATICOS / "index.html").read_text(encoding="utf-8")
    portada = portada.replace("__V__", version)

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
