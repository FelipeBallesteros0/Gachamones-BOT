"""La carta del alcalde: lo que le tocó a cada quien el día del cambio de la vivienda.

La escribe `economia` ese día y queda guardada en la base, sin ver. Aquí sólo se
cuenta con las frases de la web (`lineas_de`) y se marca vista; `estado.armar`
avisa si queda una por ver.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

import db
import economia
import especies as esp
import objetos as obj
from web.cuenta import Jugador, jugador_actual
from web.sesion import con_cabecera

router = APIRouter()

TITULO, FIRMA = "Carta del alcalde", "El alcalde"


def _monedas(n: int) -> str:
    return f"{n} {obj.nombre_de_monedas(n)}"


def _gemas(n: int) -> str:
    return f"{n} {obj.nombre_de_gemas(n)}"


def lineas_de(contenido: dict) -> list[str]:
    """Las frases de la carta, en su orden y sólo las que le tocan a esa persona."""
    lineas = [
        "El pueblo cambió, y vengo a contarte qué te toca.",
        f"Desde hoy todos vivimos en el mismo edificio. Tu departamento mide "
        f"{contenido['ancho']} × {contenido['fondo']} casillas, y lo puedes ampliar.",
    ]
    if contenido.get("vivos", 0) > 0:
        lineas.append(
            f"Te dejé puestas {contenido['camas']} camas: una para ti y una para cada gachamon."
        )
    else:
        lineas.append(
            "Te dejé tu cama puesta y otra guardada: ponla y ve a «Aventura», que ahí te espera un gachamon."
        )

    casas = contenido.get("casas") or []
    if len(casas) == 1:
        lineas.append(f"Te devolví lo que costó tu casa: {_monedas(contenido['monedas_por_casas'])}.")
    elif casas:
        lineas.append(f"Te devolví lo que costaron tus casas: {_monedas(contenido['monedas_por_casas'])}.")

    muebles = contenido.get("muebles", 0)
    if muebles == 1:
        lineas.append("Tu mueble está en guardados: entra a «Construir» y ponlo donde quieras.")
    elif muebles > 1:
        lineas.append(f"Tus {muebles} muebles están en guardados: entra a «Construir» y ponlos donde quieras.")

    if contenido.get("cosecha"):
        lineas.append(
            "Coseché lo que tenías plantado y lo dejé en tu mochila. El huerto vuelve más adelante."
        )
    if contenido.get("tickets", 0) > 0:
        suyo = "tu ticket" if contenido["tickets"] == 1 else "tus tickets"
        lineas.append(
            f"El refugio cerró. Te devolví {_monedas(contenido['monedas_por_tickets'])} por {suyo}."
        )
    if contenido.get("regalos", 0) > 0:
        lineas.append("Lo que te esperaba en el buzón ya está en tu mochila.")
    # Una carta guardada antes de que el cambio pagara las medallas no trae la clave.
    if contenido.get("gemas_por_medallas", 0) > 0:
        lineas.append(
            f"Tenías medallas ganadas y sin cobrar: te pagué {_gemas(contenido['gemas_por_medallas'])}."
        )

    for recluta in contenido.get("nombres") or []:
        especie = esp.ESPECIES.get(recluta["especie"])
        if especie is None:   # la especie ya no está en el catálogo
            continue
        lineas.append(
            f"Tu {especie.nombre} ahora se llama {recluta['nombre']}. "
            "Se puso el nombre solo, y se lo puedes cambiar una vez."
        )

    lineas.append(
        "Y dos cosas más: ya ningún gachamon muere, y a todos les pasa el tiempo, "
        "no sólo al que sale contigo."
    )
    return lineas


def _la_carta(jugador: Jugador) -> dict:
    contenido = db.carta_sin_ver(jugador.usuario_id, jugador.guild_id, economia.CAMBIO_DE_LA_VIVIENDA)
    if contenido is None:
        return {"carta": None}
    return {"carta": {"titulo": TITULO, "lineas": lineas_de(contenido), "firma": FIRMA}}


@router.get("/carta")
def ver_la_carta(jugador: Jugador = Depends(jugador_actual)) -> dict:
    return _la_carta(jugador)


@router.post("/carta/vista", dependencies=[Depends(con_cabecera)])
def marcar_vista_la_carta(jugador: Jugador = Depends(jugador_actual)) -> dict:
    db.marcar_carta_vista(
        jugador.usuario_id, jugador.guild_id, economia.CAMBIO_DE_LA_VIVIENDA, db.ahora_utc()
    )
    return {"carta": None}
