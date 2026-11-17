"""La primera aventura: donde gana su primer gachamon quien no tiene ninguno.

Es la única aventura de la página por ahora y no guarda nada hasta el
encuentro: mirarla sólo lee, y el encuentro es una sola petición que crea al
primero (`nacer.encontrar_al_primero`). El diálogo es fijo y lo pinta el
cliente; aquí se dice si se puede y con qué frases. Lo que se le ofrece en el
lugar «Aventura» a quien no tiene ninguno lo decide `pueblo`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

import db
import economia
import nacer
from web import estado, pueblo
from web.cuenta import Jugador, jugador_actual
from web.sesion import con_cabecera, problema

router = APIRouter()

# El diálogo, de a una frase: antes del encuentro, y después, con su especie.
ANTES = (
    "Sales del pueblo por el sendero. Hoy vas tú solo.",
    "Entre los matorrales, algo se mueve.",
    "No huye. Se queda mirándote.",
)
DESPUES = (
    "Sale de su escondite: es {especie}.",
    "Le tiendes la mano. La huele… y se queda a tu lado.",
    "Desde hoy vive contigo.",
)

YA_TIENES, SIN_CAMA = "ya_tienes", "sin_cama"
_YA_TIENES = "Ya tienes un gachamon. La primera aventura es sólo la de partida."


def en_la_aventura(jugador: Jugador) -> None:
    """Para la aventura hay que estar en «Aventura»: lo dice el lugar guardado de la cuenta.

    El lugar que falta o que ya no existe se resuelve como en el estado: tu casa.
    """
    clave = pueblo.donde_esta(db.lugar_de_cuenta(jugador.persona.rowino_uid))
    if clave != pueblo.AVENTURA:
        raise problema(409, "no_estas_ahi", "Para eso tienes que estar en la aventura.")


@router.get("/aventura")
def ver_la_aventura(jugador: Jugador = Depends(jugador_actual)) -> dict:
    en_la_aventura(jugador)
    if db.plantel(jugador.usuario_id, jugador.guild_id):
        motivo = YA_TIENES
    elif not db.hay_cama_libre(jugador.usuario_id, jugador.guild_id):
        motivo = SIN_CAMA
    else:
        motivo = None
    return {"primera": {
        "puede": motivo is None,
        "motivo": motivo,
        # Las frases de antes, a quien no tiene ninguno: con o sin cama, la aventura es la misma.
        "antes": [] if motivo == YA_TIENES else list(ANTES),
    }}


@router.post("/aventura/primera", dependencies=[Depends(con_cabecera)])
def la_primera_aventura(jugador: Jugador = Depends(jugador_actual)) -> dict:
    if db.avatar_de(jugador.usuario_id, jugador.guild_id) is None:
        raise problema(409, "sin_avatar", "Primero crea tu avatar.")
    en_la_aventura(jugador)
    ahora = db.ahora_utc()
    try:
        primero = nacer.encontrar_al_primero(jugador.usuario_id, jugador.guild_id, ahora)
    except nacer.YaTieneGachamon:
        raise problema(409, YA_TIENES, _YA_TIENES) from None
    except db.SinCamaLibre:
        raise problema(409, SIN_CAMA, pueblo.SIN_CAMA) from None
    except nacer.YaNoEsSuIdentidad:
        raise problema(
            409, "cuenta_cambio", "Tu cuenta cambió mientras tanto. Vuelve a entrar.",
        ) from None
    # Desde aquí el gachamon ya es tuyo, en su propia transacción: si lo que
    # sigue fallara, al volver a entrar te esperaría para que le pongas nombre.
    # Como al romper el huevo: al llegar el primero se miran las medallas de la
    # persona (una rara).
    economia.pagar_logros_de_persona(jugador.usuario_id, jugador.guild_id, ahora)
    # Vuelves a tu casa con él.
    db.poner_lugar(jugador.persona.rowino_uid, "casa")
    especie = primero.def_especie.nombre
    return {
        "estado": estado.armar(jugador, ahora),
        "despues": [frase.format(especie=especie) for frase in DESPUES],
    }
