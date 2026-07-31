"""Cliente de NVIDIA cloud para que las criaturas hablen.

NVIDIA expone una API compatible con la de OpenAI, así que basta un POST con
`aiohttp` — que ya viene instalado porque discord.py lo usa. Cero dependencias
nuevas y nada de meter el cliente síncrono de `openai`, que bloquearía el bucle
de eventos del bot.

No importa `discord`. El transporte HTTP se inyecta, así que los tests cubren
respuestas buenas, errores y caídas sin tocar la red.

Regla de oro: `responder()` **nunca lanza**. Si la API falla, se acabaron los
créditos o no hay key, la criatura contesta con una de sus frases escritas a
mano. Quien habla con su mascota no debería ver nunca un mensaje de error.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime

import aiohttp

import config
import personalidad as per
import simulacion as sim

log = logging.getLogger(__name__)

# Medido contra el endpoint: la misma petición tarda 0,6 s, 13 s o se cuelga.
# Con 20 s se perdían respuestas buenas que sólo tardaban un poco más.
SEGUNDOS_TIMEOUT = 30

# Tope de TODO el proceso: reintentos y salto de modelo incluidos. Es lo que
# como mucho dura el «escribiendo...» antes de la frase de respaldo.
SEGUNDOS_PRESUPUESTO = 90

# El endpoint compartido de NVIDIA devuelve 503 «ResourceExhausted» a menudo
# cuando está congestionado, y se recupera en cuestión de segundos. Tres
# intentos con espera creciente convierten casi todos esos fallos en una
# respuesta buena; lo que quede se cubre con las frases de respaldo.
INTENTOS = 3
SEGUNDOS_ENTRE_INTENTOS = 1
# Generoso a propósito. Los modelos normales paran solos entre 20 y 70 tokens y
# ni se enteran del tope; el que lo necesita es el razonador, que se gasta más
# de mil caracteres pensando en inglés antes de abrir la boca. Con 300 devolvía
# el contenido vacío o un muñón cortado a media frase.
MAX_TOKENS = 1200
LARGO_MAXIMO = 600

# Cuánto se aparta un modelo después de fallar. Nunca se le echa de la lista:
# se manda al final, así que si fallan todos se siguen probando todos.
#
# Los dos números salen de dos fallos distintos medidos en producción:
#
# * Los cuelgues van a rachas. El 28/07 mistral-nemotron se cayó de 16:34 a
#   16:37 —tres conversaciones seguidas se comieron el plazo entero— y al rato
#   volvía a contestar en 0,6 s. Cinco minutos bastan para saltarse la racha
#   sin castigar a un modelo que está sano.
# * Un DEGRADED de NVIDIA es otra cosa: a deepseek-v4-flash le duró horas.
#
# Medido el 28/07, ninguno de los tres es fiablemente mejor que los otros
# (6/6, 4/6 y 5/6 en la misma tanda), así que no vale ordenarlos de antemano:
# lo único que se sabe es cuál acaba de fallar.
MINUTOS_PENALIZACION = 5
MINUTOS_PENALIZACION_PERMANENTE = 30

_sesion: aiohttp.ClientSession | None = None

# Hasta cuándo está apartado cada modelo que ha fallado, en reloj monotónico.
_penalizado_hasta: dict[str, float] = {}


class ErrorIA(Exception):
    """Algo salió mal hablando con NVIDIA. Siempre se acaba capturando."""


class ErrorTransitorio(ErrorIA):
    """Congestión, timeout o caída pasajera: reintentar el mismo modelo."""


class ErrorPermanente(ErrorIA):
    """El modelo no va a funcionar por mucho que insistamos.

    El caso real que motivó separarlos: NVIDIA marcó deepseek-v4-flash como
    DEGRADED y devolvía 400 al instante. Reintentarlo tres veces con espera
    creciente convertía un fallo inmediato en 65 segundos de espera antes de
    la frase de respaldo, y el bot parecía muerto.
    """


# --- Transporte ------------------------------------------------------------

async def _sesion_compartida() -> aiohttp.ClientSession:
    global _sesion
    if _sesion is None or _sesion.closed:
        _sesion = aiohttp.ClientSession()
    return _sesion


async def cerrar() -> None:
    """La llama el cog al descargarse, para no dejar la sesión abierta."""
    global _sesion
    if _sesion is not None and not _sesion.closed:
        await _sesion.close()
    _sesion = None


async def _transporte_http(cuerpo: dict) -> dict:
    sesion = await _sesion_compartida()
    try:
        async with sesion.post(
            config.NVIDIA_URL,
            headers={
                "Authorization": f"Bearer {config.NVIDIA_API_KEY}",
                "Content-Type": "application/json",
            },
            json=cuerpo,
            timeout=aiohttp.ClientTimeout(total=SEGUNDOS_TIMEOUT),
        ) as respuesta:
            if respuesta.status != 200:
                detalle = (await respuesta.text())[:200]
                mensaje = f"HTTP {respuesta.status}: {detalle}"
                # 429 y 5xx se pasan; el resto de 4xx (modelo degradado, 404,
                # payload inválido) no mejoran por reintentar.
                if respuesta.status == 429 or respuesta.status >= 500:
                    raise ErrorTransitorio(mensaje)
                raise ErrorPermanente(mensaje)
            return await respuesta.json()
    except asyncio.TimeoutError as error:
        raise ErrorTransitorio(f"sin respuesta en {SEGUNDOS_TIMEOUT}s") from error
    except aiohttp.ClientError as error:
        raise ErrorTransitorio(f"fallo de red: {error}") from error


# --- Limpieza de la respuesta ----------------------------------------------

_CERCA_CODIGO = re.compile(r"```.*?```", re.S)
_MARCAS = re.compile(r"[*_`#>]+")
_LINEAS_VACIAS = re.compile(r"\n{2,}")

# Una línea que es sólo un paréntesis: el modelo comentando su propio trabajo.
# El caso que lo motivó salió publicado en un /jardin: terminaba la escena y
# añadía «(Palabras: 40).» aparte, haciéndole caso al límite del prompt como si
# fuera un formulario. Se exige que ocupe la línea entera para no tocar los
# paréntesis que sí son narración, como «Rimuru rebota (plop) y se queda».
_NOTA_AL_FINAL = re.compile(r"\n\s*\([^()\n]*\)\s*\.?\s*$")


_FINALES = ".!?…"


def _cortar_en_frase(texto: str, minimo: int = 0) -> str:
    """Deja el texto en la última frase completa.

    La usan los dos sitios donde una respuesta puede quedar a medias: cuando el
    modelo se queda sin tokens (`finish_reason: length`) y cuando se pasa de
    `LARGO_MAXIMO`. Si no hay ningún final aprovechable se cierra con puntos
    suspensivos, que es mejor que dejarlo a media palabra y mucho mejor que
    dejarlo vacío.

    `minimo` es cuánto texto hay que conservar para que compense cortar: sin él,
    una respuesta con un punto muy al principio se quedaría en nada.
    """
    corte = max((texto.rfind(c) for c in _FINALES), default=-1)
    corte = max(corte, texto.rfind("\n"))
    if corte > minimo:
        return texto[:corte + 1].strip()
    return texto.rstrip() + "…"


def limpiar(texto: str, nombre: str) -> str:
    """Deja la respuesta lista para publicar.

    El modelo a veces se pone creativo con el formato pese a las instrucciones:
    mete markdown, se antepone el nombre como si fuera un guion de teatro, o se
    enrolla. Aquí se corrige en vez de confiar en que obedezca siempre.
    """
    texto = _CERCA_CODIGO.sub("", texto).strip()

    # «Pelusa: ¡pío!» -> «¡pío!». Sin nombre no hay prefijo que quitar, y el
    # patrón vacío se comería cualquier guion inicial.
    if nombre:
        prefijo = re.compile(rf"^\s*{re.escape(nombre)}\s*[:\-–]\s*", re.I)
        texto = prefijo.sub("", texto)

    # Los asteriscos sueltos de *chisp* son parte del personaje y se quedan;
    # las negritas `**así**` no, que el modelo las mete pese a las
    # instrucciones y en Discord se ven como tales.
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto, flags=re.S)
    texto = re.sub(r"^#{1,6}\s*", "", texto, flags=re.M)
    texto = re.sub(r"^\s*[>\-\*]\s+", "", texto, flags=re.M)

    texto = _LINEAS_VACIAS.sub("\n", texto).strip()

    # Puede haber más de una nota seguida, y la primera línea también puede
    # serlo entera: se quitan hasta que no quede ninguna.
    while True:
        sin_nota = _NOTA_AL_FINAL.sub("", texto)
        if sin_nota == texto:
            break
        texto = sin_nota
    if re.fullmatch(r"\s*\([^()\n]*\)\s*\.?\s*", texto):
        texto = ""

    if len(texto) > LARGO_MAXIMO:
        texto = _cortar_en_frase(texto[:LARGO_MAXIMO], minimo=LARGO_MAXIMO // 3)

    return texto.strip()


# --- Llamada ---------------------------------------------------------------

def _modelos_a_probar() -> list[str]:
    """Los modelos en el orden en que conviene intentarlos.

    Primero los que no han fallado hace poco, en el orden de la configuración;
    los apartados, al final. **Nunca se quita ninguno**: si están todos
    castigados se prueban todos igual, sólo que en ese orden.

    Los castigos caducan solos, así que no hace falta ningún temporizador que
    devuelva el orden bueno: se restaura cuando pasa el rato.
    """
    ahora = time.monotonic()
    libres = [m for m in config.MODELOS_IA if _penalizado_hasta.get(m, 0) <= ahora]
    castigados = [m for m in config.MODELOS_IA if _penalizado_hasta.get(m, 0) > ahora]
    return libres + castigados


def _penalizar(modelo: str, minutos: float) -> None:
    """Aparta un modelo que acaba de fallar, para que el siguiente mensaje no
    vuelva a estrellarse contra él."""
    if modelo not in config.MODELOS_IA:
        return
    _penalizado_hasta[modelo] = time.monotonic() + minutos * 60


def _perdonar(modelo: str) -> None:
    """Ha contestado: se le quita el castigo aunque hubiera fallado antes."""
    _penalizado_hasta.pop(modelo, None)


def reiniciar_modelos() -> None:
    """Borra todos los castigos. Para los tests y para el arranque."""
    _penalizado_hasta.clear()


async def pedir(mensajes: list[dict], transporte=None, modelo: str | None = None) -> str:
    """Manda la conversación al modelo y devuelve su texto. Puede lanzar ErrorIA."""
    transporte = transporte or _transporte_http
    cuerpo = {
        "model": modelo or config.MODELOS_IA[0],
        "messages": mensajes,
        "temperature": 1,
        "top_p": 0.95,
        "max_tokens": MAX_TOKENS,
        # El modo de razonamiento aquí sólo añadiría segundos de espera: las
        # respuestas son de tres líneas en boca de un pollito.
        "chat_template_kwargs": {"thinking": False},
        "stream": False,
    }

    datos = await transporte(cuerpo)
    try:
        eleccion = datos["choices"][0]
        texto = eleccion["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise ErrorTransitorio(
            f"respuesta con forma inesperada: {str(datos)[:200]}") from error

    if not texto or not texto.strip():
        # Transitorio, no un fallo del modelo: el endpoint compartido devuelve
        # respuestas vacías de vez en cuando y a la siguiente contesta bien.
        razonamiento = (eleccion.get("message", {}) or {}).get("reasoning_content")
        if razonamiento:
            # El caso real: llama-3.3-nemotron-super razona en inglés durante
            # más de mil caracteres y se queda sin presupuesto antes de decir
            # nada. Merece un mensaje propio: el genérico costó una tarde.
            raise ErrorTransitorio(
                f"{cuerpo['model']} gastó los {MAX_TOKENS} tokens razonando "
                f"({len(razonamiento)} caracteres) y no llegó a contestar"
            )
        raise ErrorTransitorio("el modelo devolvió una respuesta vacía")

    # Si se quedó sin tokens, la última frase está a medias. Vale más decir una
    # frase menos que publicar «Pío pío... ¡hasta cuándo».
    if eleccion.get("finish_reason") == "length":
        log.info("Respuesta cortada por el tope de tokens; la dejo en la última "
                 "frase entera")
        texto = _cortar_en_frase(texto.strip())

    return texto


async def _intentar(mensajes: list[dict], transporte=None) -> str | None:
    """Prueba los modelos en orden hasta que uno conteste.

    Devuelve el texto crudo, o None si no hubo forma. Nunca lanza: es quien
    llama el que decide con qué frase de respaldo cubrir el hueco.

    Se reintenta **todo lo que no sea permanente**. El caso que motivó la regla:
    una respuesta vacía llegaba como `ErrorIA` de la clase base, no encajaba en
    ninguna rama y caía en el cajón de sastre, que abandonaba la cadena entera
    sin reintentar ni probar los otros modelos. Quien escribía se comía la frase
    de respaldo por un fallo que se arreglaba solo al segundo intento.

    El tope es de tiempo y no de intentos, porque el modo de fallo real de este
    endpoint es tardar, no negarse: con la nube lenta, nueve intentos de 30 s se
    iban a más de cuatro minutos de «escribiendo...».

    Se va **por rondas: primero una vez cada modelo**, y sólo después se repite.
    Insistir con el primero antes de haber probado los demás cuesta el
    presupuesto entero cuando el que falla es justo ése. Pasó en producción: tres
    intentos de 30 s con el preferido colgado agotaban los 90 s exactos, la
    cadena de recambio no se alcanzaba nunca y la criatura soltaba la frase
    enlatada mientras otro modelo contestaba en 1,3 s sin que nadie se lo
    pidiera.
    """
    limite = time.monotonic() + SEGUNDOS_PRESUPUESTO
    modelos = _modelos_a_probar()
    descartados: set[str] = set()

    for ronda in range(1, INTENTOS + 1):
        for modelo in modelos:
            if modelo in descartados:
                continue
            restante = limite - time.monotonic()
            if restante <= 0:
                log.warning("Agotado el presupuesto de %ds hablando con la IA",
                            SEGUNDOS_PRESUPUESTO)
                return None
            try:
                texto = await asyncio.wait_for(
                    pedir(mensajes, transporte, modelo),
                    timeout=min(SEGUNDOS_TIMEOUT, restante),
                )
                _perdonar(modelo)
                return texto
            except ErrorPermanente as error:
                # Insistir no sirve de nada y hace esperar a quien escribió.
                log.warning("Modelo %s no utilizable: %s", modelo, error)
                _penalizar(modelo, MINUTOS_PENALIZACION_PERMANENTE)
                descartados.add(modelo)
            except (ErrorIA, asyncio.TimeoutError) as error:
                _penalizar(modelo, MINUTOS_PENALIZACION)
                # `str()` y no el objeto: un TimeoutError va sin mensaje, y como
                # las excepciones siempre son «truthy», `error or ...` dejaba la
                # línea del log acabada en dos puntos y nada detrás.
                log.warning("IA falló con %s (ronda %d/%d): %s", modelo, ronda,
                            INTENTOS, str(error) or "sin respuesta a tiempo")
            except Exception:
                # Aquí sólo deberían llegar errores de programación.
                log.exception("IA falló de forma inesperada")
                return None

        if len(descartados) == len(modelos):
            return None
        if ronda < INTENTOS:
            await asyncio.sleep(SEGUNDOS_ENTRE_INTENTOS * ronda)
    return None


async def responder(
    criatura: sim.Criatura,
    ahora: datetime,
    dueño: str,
    historial: list[dict],
    mensaje: str,
    transporte=None,
    semilla: int = 0,
) -> tuple[str, bool]:
    """Lo que contesta la criatura.

    Devuelve `(texto, salió_de_la_ia)`. El segundo valor le sirve a quien llama
    para no guardar en la memoria las frases de respaldo: si se guardaran, el
    modelo aprendería a repetirlas.

    Nunca lanza.
    """
    respaldo = per.frase_de_respaldo(criatura, semilla)
    if not config.IA_ACTIVA and transporte is None:
        return respaldo, False

    mensajes = [{"role": "system",
                 "content": per.construir_prompt(criatura, ahora, dueño)}]
    mensajes += historial
    mensajes.append({"role": "user", "content": mensaje})

    crudo = await _intentar(mensajes, transporte)
    if crudo:
        limpio = limpiar(crudo, criatura.nombre)
        if limpio:
            return limpio, True
        log.warning("La respuesta quedó vacía después de limpiarla")
    return respaldo, False


async def generar_crudo(sistema: str, peticion: str, transporte=None) -> str | None:
    """Una generación **sin limpiar**, para cuando se pide JSON y no prosa.

    `limpiar` está hecho para frases: quita bloques de código, marcas y notas
    finales, y con un objeto JSON haría destrozos. Devuelve `None` si no hay IA
    o si falla, que es la señal de tirar del respaldo escrito.

    Como el resto del módulo, nunca lanza.
    """
    if not config.IA_ACTIVA and transporte is None:
        return None
    return await _intentar(
        [{"role": "system", "content": sistema},
         {"role": "user", "content": peticion}],
        transporte,
    )


async def generar(
    sistema: str,
    peticion: str,
    respaldo: str,
    transporte=None,
) -> tuple[str, bool]:
    """Una generación suelta, sin historial ni criatura concreta.

    La usa el jardín. Como `responder`, nunca lanza y siempre devuelve texto.
    """
    if not config.IA_ACTIVA and transporte is None:
        return respaldo, False

    crudo = await _intentar(
        [{"role": "system", "content": sistema},
         {"role": "user", "content": peticion}],
        transporte,
    )
    if crudo:
        limpio = limpiar(crudo, "")
        if limpio:
            return limpio, True
    return respaldo, False
