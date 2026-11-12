"""Los retratos como imagen: el dibujo de cada gachamon, sin sesión.

Es un dibujo y no un dato de nadie, así que no pide cookie y se guarda para
siempre: la dirección lleva `?v=` con la huella de `fuentes/`, y si se redibuja
una capa la dirección cambia.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import RedirectResponse, Response

import cosmeticos as cos
import especies as esp
import retrato
from web import PREFIJO
from web.sesion import problema

log = logging.getLogger("gachamones")

router = APIRouter()

CACHE = "public, max-age=31536000, immutable"


@router.get("/retrato/{especie}/{etapa}/{animo}/{sombrero}.png")
def un_retrato(especie: str, etapa: str, animo: str, sombrero: str,
               v: str | None = None) -> Response:
    # Las cuatro partes se comprueban contra los catálogos antes de tocar el
    # disco: nada de lo que venga en la dirección forma una ruta sin pasar por aquí.
    if (
        especie not in esp.ESPECIES or etapa not in esp.ETAPAS
        or animo not in esp.ANIMOS
        or (sombrero != retrato.SIN_SOMBRERO
            and sombrero not in {s.clave for s in cos.SOMBREROS})
    ):
        raise problema(404, "no_existe", "Eso no existe.")
    vigente = retrato.version()
    if v != vigente:
        # Sin la versión vigente no se compone ni se guarda nada: así no se
        # esquiva la caché con una `v` inventada. El destino sale sólo de las
        # claves ya validadas.
        return RedirectResponse(
            f"{PREFIJO}/retrato/{especie}/{etapa}/{animo}/{sombrero}.png?v={vigente}",
            status_code=307,
        )
    if (especie, etapa) in retrato.CON_RETRATO:
        try:
            png = retrato.armar(especie, etapa, animo, sombrero)
        except FileNotFoundError as error:
            # Falta una capa de una especie que se declaró dibujada: ni un 500
            # ni la capa de otra forma. Se avisa para que alguien la dibuje.
            log.warning("Falta una capa del retrato %s/%s/%s/%s: %s",
                        especie, etapa, animo, sombrero, error.filename)
            raise problema(404, "no_existe", "Eso no existe.") from None
    else:
        png = retrato.relleno(especie, etapa, animo)
    return Response(png, media_type="image/png", headers={"Cache-Control": CACHE})
