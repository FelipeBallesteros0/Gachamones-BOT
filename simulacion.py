"""Reglas del juego: decaimiento, acciones de cuidado, stats y niveles.

Módulo puro: sin discord, sin SQLite, sin reloj global. Todo recibe `ahora`
explícitamente, así que los tests pueden viajar en el tiempo sin esperar.

Decaimiento perezoso
--------------------
No hay ningún bucle tocando cada mascota cada minuto. Se guarda cuándo se
actualizó por última vez y el valor real se calcula al leer, en función de las
horas transcurridas. Es barato, exacto y sobrevive a los reinicios del bot.

El hambre decae de forma estrictamente lineal (su ritmo depende sólo de la
salud, que no cambia entre acciones), así que la hora de la muerte se despeja
con una fórmula cerrada en vez de simulando. Por eso la suciedad castiga al
ánimo y no al hambre: si acelerase el hambre, dos barras que caen a la vez se
acoplarían y la muerte dejaría de ser predecible.
"""
from __future__ import annotations

import math
import random
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

import especies as esp

# --- Ritmo -----------------------------------------------------------------

# El hambre baja 100 puntos en (40 + salud * 2.2) horas.
# Salud típica al nacer (~15) -> ~73 h. Un Brote sano (~21) -> ~86 h.
# Una Chispa frágil (~10) -> ~62 h. Todas entre 2,5 y 3,5 días.
HORAS_BASE_HAMBRE = 40.0
HORAS_POR_SALUD = 2.2

HORAS_VACIAR_ANIMO = 60.0
HORAS_VACIAR_LIMPIEZA = 48.0

# Estar sucio amarga a la criatura: el ánimo cae más rápido.
LIMPIEZA_SUCIA = 30.0
MULTIPLICADOR_ANIMO_SUCIO = 1.5

# --- Evolución --------------------------------------------------------------

# La etapa sale del nivel: nivel 1 = bebé, nivel 5 o más = adulto grande.
# Cuánto cuesta cada subida, calibrado sobre ~30 XP diarios (lo que saca quien
# atiende a su criatura un par de veces al día): el primer nivel cae en un día
# y llegar a adulto grande cuesta alrededor de un mes.
COSTE_XP_NIVEL = (25, 100, 250, 525)
COSTE_XP_EXTRA = 525  # niveles a partir del quinto: ya no hay etapa nueva

# Puntos de estadística que reparte cada evolución, repartidos según el perfil
# de la especie. +14 en total sobre unos 45 de partida, y como parte va a
# salud, la criatura evolucionada aguanta bastante más sin comer.
PUNTOS_POR_EVOLUCION = (2, 3, 4, 5)
PUNTOS_POR_NIVEL_EXTRA = 2

# --- Acciones --------------------------------------------------------------

ALIMENTAR = "alimentar"
JUGAR = "jugar"
ENTRENAR = "entrenar"
LIMPIAR = "limpiar"
ACTUALIZAR = "actualizar"
COMPETIR = "competir"
AVENTURA = "aventura"

# La regla es que **ninguno sea múltiplo de otro**, y hay un test que la vigila.
# No es un capricho: antes eran 30, 30, 60, 120 y 10 —todos múltiplos de 10, dos
# de ellos iguales— y si un enfriamiento es múltiplo de otro sus ciclos coinciden
# para siempre. Medido sobre 24 h de juego atento, con aquellos números las
# acciones se liberaban juntas **las 48 veces**, en bloque, y entre bloque y
# bloque no había nada que hacer durante media hora. Con éstos se turnan: 3
# coincidencias de 147 momentos, y la espera más larga baja de 30 a 23 minutos.
#
# Los cuatro de cuidado son primos, que es la forma barata de garantizar la
# propiedad sin pensarla. El de competir no lo es, pero la cumple igual.
COOLDOWNS = {
    ALIMENTAR: timedelta(minutes=23),
    JUGAR: timedelta(minutes=29),
    ENTRENAR: timedelta(minutes=113),
    LIMPIAR: timedelta(minutes=53),
    ACTUALIZAR: timedelta(0),
    # Competir lo comparten carrera y sumo. Diez minutos son 6 peleas por hora,
    # y el hambre da para 7,8 —10 por pelea, mínimo 20 para entrar, +30 por
    # comida cada 23 min—, así que **es este número el que ata**, no la comida.
    # Es a propósito: con los 3 minutos de antes ataba el hambre y el objeto que
    # reinicia esta espera no servía para nada.
    COMPETIR: timedelta(minutes=10),
    # Salir al campo es más lento que una pelea. 37 es primo, así que cumple la
    # regla de arriba sin tener que comprobar nada a mano.
    AVENTURA: timedelta(minutes=37),
}

# Sólo estas cuatro salen en el subtexto de la pantalla.
ACCIONES_DE_CUIDADO = (ALIMENTAR, JUGAR, ENTRENAR, LIMPIAR)

LARGO_MAXIMO_NOMBRE = 24


def normalizar_nombre(nombre: str) -> str:
    """Valida y normaliza un nombre antes de mostrarlo en Discord.

    Los nombres son Unicode y no se restringen a un alfabeto concreto, pero su
    puntuación se limita para que no controle o suplante la salida del bot.
    """
    normalizado = " ".join(parte for parte in nombre.split(" ") if parte)
    if not normalizado:
        raise ValueError("El nombre está vacío.")
    permitidos = {" ", "'", "’", "-"}
    if any(
        caracter not in permitidos
        and unicodedata.category(caracter)[0] not in {"L", "M", "N"}
        for caracter in normalizado
    ):
        raise ValueError(
            "El nombre sólo puede contener letras, números, espacios, "
            "apóstrofes y guiones."
        )
    if len(normalizado) > LARGO_MAXIMO_NOMBRE:
        raise ValueError(
            f"El nombre no puede tener más de {LARGO_MAXIMO_NOMBRE} caracteres."
        )
    return normalizado

# Cuidar también hace crecer, para que quien no quiera competir pueda ver
# evolucionar a su criatura igualmente. Los enfriamientos de arriba topan la
# ganancia en unos 8 XP/hora sin necesidad de ninguna regla nueva. Ese tope sólo
# lo alcanza quien esté pegado a la pantalla: el ritmo real está calibrado sobre
# una rutina humana de 27 XP diarios, que la limitan las veces que uno entra a
# Discord y no los enfriamientos.
XP_POR_CUIDADO = {
    ALIMENTAR: 1,
    JUGAR: 2,
    ENTRENAR: 3,
    LIMPIAR: 0,
    ACTUALIZAR: 0,
}

# Dónde cambia de color una barra. Viven aquí, en las reglas, y no en
# `pantalla.py`, porque además de pintar deciden cuándo se puede alimentar de
# urgencia. Con el umbral duplicado en los dos sitios, el día que alguien
# tocase uno volvería el error de ver la barra en naranja y el botón bloqueado.
UMBRAL_BARRA_BIEN = 60.0   # a partir de aquí, verde
UMBRAL_BARRA_MAL = 30.0    # por debajo de aquí, rojo

# Comer estando ya lleno sienta mal.
UMBRAL_EMPACHO = 90.0

# Cuando la comida baja de aquí, el bot avisa al dueño. Al 10% quedan todavía
# un 10% de las horas de vida (unas 7 h en una criatura típica): margen de sobra
# para reaccionar sin que el aviso llegue tan pronto que se ignore.
UMBRAL_AVISO_HAMBRE = 10.0

# --- Competencias ----------------------------------------------------------

# Competir sigue siendo lo más rentable por acción, para que las carreras no
# pierdan sentido ahora que también se sube de nivel cuidando a la criatura.
XP_VICTORIA = 10
XP_DERROTA = 4
HAMBRE_MINIMA_COMPETIR = 20.0
COSTE_HAMBRE_COMPETIR = 10.0
COSTE_ANIMO_COMPETIR = 5.0

# Salir de aventura cansa más que una pelea: es un viaje, no un asalto. El
# mínimo es el mismo que para competir, para no tener dos umbrales que explicar.
HAMBRE_MINIMA_AVENTURA = HAMBRE_MINIMA_COMPETIR
COSTE_HAMBRE_AVENTURA = 15.0
COSTE_ANIMO_AVENTURA = 5.0

# Competir también entrena, aunque menos que una sesión dedicada.
ENTRENAMIENTO_POR_COMPETIR = 1

@dataclass(frozen=True)
class Criatura:
    """Una criatura con el decaimiento YA aplicado hasta cierto instante."""

    id: int
    usuario_id: str
    guild_id: str
    especie: str
    nombre: str
    nacida_en: datetime
    actualizada_en: datetime
    # Los dos se sortean al nacer y no cambian. El carácter se guarda por clave;
    # quién es cada uno vive en `personalidad.CARACTERES`, que no se puede
    # importar aquí (ese módulo ya importa éste), de ahí el literal.
    genero: str = esp.MACHO
    caracter: str = esp.CARACTER_POR_DEFECTO
    hambre: float = 100.0
    animo: float = 100.0
    limpieza: float = 100.0
    base_fuerza: int = 0
    base_velocidad: int = 0
    base_salud: int = 0
    ent_fuerza: int = 0
    ent_velocidad: int = 0
    ent_salud: int = 0
    niv_fuerza: int = 0
    niv_velocidad: int = 0
    niv_salud: int = 0
    xp: int = 0
    nivel: int = 1
    victorias: int = 0
    derrotas: int = 0
    muerta_en: datetime | None = None
    causa_muerte: str | None = None
    pantalla_msg_id: str | None = None
    # Canal donde se atendió por última vez. Con el bot en varios canales, es
    # ahí donde llegan los avisos de hambre y muerte: donde estabas jugando.
    canal_id: str | None = None
    # Si ya se avisó de que está en las últimas. Se reinicia al alimentarla,
    # para que el aviso no se repita cada cuarto de hora ni se pierda si la
    # criatura vuelve a caer al mismo punto días después.
    avisada: bool = False
    # La que recibe los comandos y los botones. Sólo puede haber una por persona
    # y servidor —lo impone un índice único—; las demás esperan en la incubadora,
    # donde no les pasa el tiempo. Ver `avanzar`.
    activa: bool = True

    # -- accesos derivados --------------------------------------------------

    @property
    def def_especie(self) -> esp.Especie:
        return esp.ESPECIES[self.especie]

    @property
    def viva(self) -> bool:
        return self.muerta_en is None

    @property
    def fuerza(self) -> int:
        return stat_final(self.base_fuerza, self.ent_fuerza, self.niv_fuerza)

    @property
    def velocidad(self) -> int:
        return stat_final(self.base_velocidad, self.ent_velocidad, self.niv_velocidad)

    @property
    def salud(self) -> int:
        return stat_final(self.base_salud, self.ent_salud, self.niv_salud)

    def edad_horas(self, ahora: datetime) -> float:
        return (ahora - self.nacida_en).total_seconds() / 3600.0

    @property
    def etapa(self) -> str:
        """En qué etapa está, deducida del nivel.

        No se guarda en la base de datos: el nivel ya está ahí y la etapa es
        una consecuencia suya, así que no puede desincronizarse.
        """
        return esp.ETAPAS[min(self.nivel, len(esp.ETAPAS)) - 1]

    @property
    def animo_visual(self) -> str:
        """Qué cara pone: decide qué dibujo se enseña."""
        if self.hambre > 60 and self.animo > 60:
            return esp.FELIZ
        if self.hambre < 30 or self.animo < 30:
            return esp.MAL
        return esp.NORMAL


# --- Stats y niveles -------------------------------------------------------

# Techo de FUE / VEL / SAL. Tres cifras es lo que cabe en el marco, y jugando
# no se alcanza ni de lejos (una criatura veterana anda por 20), así que esto
# es una red: sin tope, las estadísticas crecerían hasta desbordar el dibujo.
MAXIMO_STAT = 999


def stat_final(base: int, entrenamiento: int, bonus_nivel: int) -> int:
    """base + raíz del entrenamiento + bonus de nivel, topado en `MAXIMO_STAT`.

    La raíz cuadrada da rendimientos decrecientes: hacen falta 4 sesiones para
    el segundo punto, 9 para el tercero, 100 para el décimo. Machacar el botón
    no dispara a nadie, y el 1d20 de las competencias sigue pesando más que la
    diferencia entre dos criaturas cuidadas.

    El tope se aplica aquí porque esta función es el embudo por el que pasan
    `fuerza`, `velocidad` y `salud`: topando una vez queda topado todo lo que
    las consume. Los contadores `ent_` y `niv_` siguen subiendo por dentro,
    simplemente dejan de notarse.
    """
    return min(MAXIMO_STAT, base + math.isqrt(max(0, entrenamiento)) + bonus_nivel)


def xp_para_subir(nivel: int) -> int:
    """Lo que cuesta pasar de `nivel` al siguiente."""
    if nivel <= len(COSTE_XP_NIVEL):
        return COSTE_XP_NIVEL[nivel - 1]
    return COSTE_XP_EXTRA


def xp_acumulada_para(nivel: int) -> int:
    """XP total desde el nacimiento hasta alcanzar `nivel`."""
    return sum(xp_para_subir(n) for n in range(1, nivel))


def puntos_al_subir(nivel_alcanzado: int) -> int:
    indice = nivel_alcanzado - 2
    if 0 <= indice < len(PUNTOS_POR_EVOLUCION):
        return PUNTOS_POR_EVOLUCION[indice]
    return PUNTOS_POR_NIVEL_EXTRA


def aplicar_xp(
    criatura: Criatura, ganada: int, rng: random.Random | None = None
) -> tuple[Criatura, list[str]]:
    """Suma XP y sube de nivel las veces que haga falta.

    Cada subida reparte varios puntos entre las stats, sorteados con el perfil
    de la especie como peso: un Pollito tiende a mejorar en velocidad, un
    Pedrusco en fuerza. Las evoluciones tardías dan más puntos que las
    primeras, así que llegar arriba se nota.
    """
    rng = rng or random.Random()
    definicion = criatura.def_especie
    xp = criatura.xp + ganada
    nivel = criatura.nivel
    bonus = {
        "fuerza": criatura.niv_fuerza,
        "velocidad": criatura.niv_velocidad,
        "salud": criatura.niv_salud,
    }
    subidas: list[str] = []

    while xp >= xp_para_subir(nivel):
        xp -= xp_para_subir(nivel)
        nivel += 1
        for _ in range(puntos_al_subir(nivel)):
            stat = rng.choices(
                ["fuerza", "velocidad", "salud"],
                weights=[definicion.fuerza, definicion.velocidad, definicion.salud],
                k=1,
            )[0]
            bonus[stat] += 1
            subidas.append(stat)

    actualizada = replace(
        criatura,
        xp=xp,
        nivel=nivel,
        niv_fuerza=bonus["fuerza"],
        niv_velocidad=bonus["velocidad"],
        niv_salud=bonus["salud"],
    )
    return actualizada, subidas


# --- Decaimiento -----------------------------------------------------------

def tasa_hambre_por_hora(salud: int) -> float:
    return 100.0 / (HORAS_BASE_HAMBRE + salud * HORAS_POR_SALUD)


def horas_de_vida(salud: int) -> float:
    """Cuánto aguanta desde el hambre a tope hasta morir."""
    return HORAS_BASE_HAMBRE + salud * HORAS_POR_SALUD


def momento_de_aviso(criatura: Criatura) -> datetime:
    """Instante en que la comida bajará del umbral de aviso.

    Se guarda en la base de datos por el mismo motivo que `muere_en`: el bucle
    de vigilancia es entonces un `WHERE avisa_en <= ahora` y no hace falta
    simular todas las criaturas cada cuarto de hora.
    """
    restante = criatura.hambre - UMBRAL_AVISO_HAMBRE
    if restante <= 0:
        return criatura.actualizada_en
    horas = restante / tasa_hambre_por_hora(criatura.salud)
    return criatura.actualizada_en + timedelta(hours=horas)


def momento_de_muerte(criatura: Criatura) -> datetime:
    """Instante exacto en que el hambre llegará a 0 si nadie la alimenta.

    Se guarda en la base de datos para que el bucle de muerte sea una única
    consulta (`WHERE muere_en <= ahora`) en vez de recorrer y simular cada fila.
    """
    horas = criatura.hambre / tasa_hambre_por_hora(criatura.salud)
    return criatura.actualizada_en + timedelta(hours=horas)


def avanzar(criatura: Criatura, ahora: datetime) -> Criatura:
    """Aplica el paso del tiempo hasta `ahora`. Idempotente y sin efectos.

    A las de la incubadora no les pasa el tiempo. Es lo que hace viable tener
    tres: los cuidados sólo llegan a la activa, así que si las otras decayeran se
    morirían de hambre hiciera lo que hiciera su dueño. Al sacarlas, `db.activar`
    les pone `actualizada_en` al día para que las horas dormidas no se les caigan
    encima de golpe.
    """
    if not criatura.viva or not criatura.activa:
        return criatura

    horas = (ahora - criatura.actualizada_en).total_seconds() / 3600.0
    if horas <= 0:
        return criatura

    hambre = max(0.0, criatura.hambre - tasa_hambre_por_hora(criatura.salud) * horas)
    limpieza = max(0.0, criatura.limpieza - (100.0 / HORAS_VACIAR_LIMPIEZA) * horas)

    # El ánimo cae más rápido si está sucia. Se decide con la limpieza al
    # principio del intervalo: es una aproximación, pero el ánimo no mata, así
    # que un error de unos puntos no tiene consecuencias.
    ritmo_animo = 100.0 / HORAS_VACIAR_ANIMO
    if criatura.limpieza < LIMPIEZA_SUCIA:
        ritmo_animo *= MULTIPLICADOR_ANIMO_SUCIO
    animo = max(0.0, criatura.animo - ritmo_animo * horas)

    avanzada = replace(
        criatura,
        hambre=hambre,
        animo=animo,
        limpieza=limpieza,
        actualizada_en=ahora,
    )

    if hambre <= 0.0:
        momento = momento_de_muerte(criatura)
        return replace(
            avanzada,
            hambre=0.0,
            muerta_en=min(momento, ahora),
            causa_muerte="hambre",
        )
    return avanzada


# --- Acciones de cuidado ---------------------------------------------------

@dataclass(frozen=True)
class ResultadoAccion:
    criatura: Criatura
    mensaje: str
    ok: bool = True
    espera: timedelta | None = None
    subidas: tuple[str, ...] = ()
    etapa_anterior: str | None = None

    def __post_init__(self) -> None:
        """Concuerda el aviso con el género de la criatura.

        Se hace aquí y no en cada `return` de `_efecto_de()` porque el fallo que
        esto arregla fue exactamente ése: el mensaje se escribe en un sitio y se
        concordaba —o no— en otro, así que «Está encantada» le salía también a
        los machos. En el constructor no hay nada que recordar y los avisos que
        se añadan mañana quedan cubiertos solos.

        `concordar` es idempotente: un texto ya resuelto no tiene marcas, así
        que volver a pasar por aquí (un `replace()`, por ejemplo) no rompe nada.
        """
        object.__setattr__(
            self, "mensaje", esp.concordar(self.mensaje, self.criatura.genero)
        )

    @property
    def evoluciono(self) -> bool:
        return (
            self.etapa_anterior is not None
            and self.etapa_anterior != self.criatura.etapa
        )


def _limitar(valor: float) -> float:
    return max(0.0, min(100.0, valor))


def puede_saltarse_espera(criatura: Criatura, accion: str) -> bool:
    """Si esta acción se puede hacer aunque el enfriamiento siga corriendo.

    Alimentar no espera cuando la criatura tiene hambre de verdad: el
    enfriamiento marca el ritmo del juego, y eso sólo tiene sentido mientras
    está bien. Ver a tu criatura en rojo y que el bot te diga que esperes es
    absurdo.

    No se puede abusar: alimentar da +30 y esto sólo aplica por debajo de 60,
    así que desde 0 son dos veces seguidas (0 → 30 → 60) y ahí se acaba. Volver
    a bajar de 60 cuesta unas 29 horas de decaimiento.
    """
    return accion == ALIMENTAR and criatura.hambre < UMBRAL_BARRA_BIEN


def aplicar_accion(
    criatura: Criatura, accion: str, ahora: datetime,
    rng: random.Random | None = None,
) -> ResultadoAccion:
    """Ejecuta una acción de cuidado sobre una criatura ya avanzada en el tiempo.

    Además del efecto en las barras, otorga la experiencia de la acción y sube
    de nivel si toca. El resultado lleva la etapa anterior para que quien llame
    pueda anunciar la evolución.

    No comprueba cooldowns: de eso se encarga la capa de base de datos, que es
    quien sabe cuándo se usó por última vez.
    """
    bruto = _efecto_de(criatura, accion)
    if not bruto.ok or accion == ACTUALIZAR:
        return bruto

    ganada = XP_POR_CUIDADO.get(accion, 0)
    if not ganada:
        return bruto

    crecida, subidas = aplicar_xp(bruto.criatura, ganada, rng)
    return ResultadoAccion(
        criatura=crecida,
        mensaje=bruto.mensaje,
        subidas=tuple(subidas),
        etapa_anterior=criatura.etapa,
    )


def _efecto_de(criatura: Criatura, accion: str) -> ResultadoAccion:
    """El efecto de la acción sobre las barras, sin tocar la experiencia."""
    if not criatura.viva:
        return ResultadoAccion(criatura, "Tu criatura ya no está entre nosotros.", ok=False)

    if accion == ACTUALIZAR:
        return ResultadoAccion(criatura, "")

    if accion == ALIMENTAR:
        if criatura.hambre >= UMBRAL_EMPACHO:
            nueva = replace(
                criatura,
                hambre=_limitar(criatura.hambre + 10),
                animo=_limitar(criatura.animo - 15),
            )
            return ResultadoAccion(nueva, "Se ha empachado. No tenía nada de hambre.")
        nueva = replace(
            criatura,
            hambre=_limitar(criatura.hambre + 30),
            ent_salud=criatura.ent_salud + 1,
            # Alimentarla rearma el aviso: si vuelve a pasar hambre, se avisa
            # otra vez. Es la única acción que sube la comida, así que es el
            # único sitio donde hace falta reiniciarlo.
            avisada=False,
        )
        return ResultadoAccion(nueva, "Ñam. Se lo ha comido todo.")

    if accion == JUGAR:
        nueva = replace(
            criatura,
            animo=_limitar(criatura.animo + 25),
            hambre=_limitar(criatura.hambre - 5),
            ent_velocidad=criatura.ent_velocidad + 1,
        )
        return ResultadoAccion(nueva, "Habéis jugado un rato. Está encantad{o/a}.")

    if accion == ENTRENAR:
        nueva = replace(
            criatura,
            hambre=_limitar(criatura.hambre - 15),
            animo=_limitar(criatura.animo - 10),
            ent_fuerza=criatura.ent_fuerza + 2,
        )
        return ResultadoAccion(nueva, "Entrenamiento duro. Ha quedado molid{o/a}.")

    if accion == LIMPIAR:
        nueva = replace(criatura, limpieza=100.0)
        return ResultadoAccion(nueva, "Como nuev{o/a}.")

    raise ValueError(f"acción desconocida: {accion}")


def aplicar_competencia(
    criatura: Criatura,
    gano: bool,
    stat: str,
    rng: random.Random | None = None,
) -> tuple[Criatura, list[str]]:
    """Aplica el desgaste, la XP y el entrenamiento de haber competido.

    `stat` es "velocidad" en las carreras y "fuerza" en el sumo. Se recibe como
    texto para no tener que importar `competir`, que ya importa este módulo.
    """
    if stat not in ("velocidad", "fuerza"):
        raise ValueError(f"estadística de competencia desconocida: {stat}")

    entrenados = {
        "ent_velocidad": criatura.ent_velocidad,
        "ent_fuerza": criatura.ent_fuerza,
    }
    entrenados[f"ent_{stat}"] += ENTRENAMIENTO_POR_COMPETIR

    desgastada = replace(
        criatura,
        hambre=_limitar(criatura.hambre - COSTE_HAMBRE_COMPETIR),
        animo=_limitar(criatura.animo - COSTE_ANIMO_COMPETIR),
        victorias=criatura.victorias + (1 if gano else 0),
        derrotas=criatura.derrotas + (0 if gano else 1),
        **entrenados,
    )
    return aplicar_xp(desgastada, XP_VICTORIA if gano else XP_DERROTA, rng)
