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
from random import Random as _RandomImpronta
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

# --- VETAS -----------------------------------------------------------------

# El crecimiento de las estadísticas no usa dados propios. Los sucesos reales
# emiten tensión, que decae y rompe por el punto más cargado.
UMBRAL_ESFUERZO = 1.3
PROFUNDA = 2.5
BETA = 0.70
GAMMA = 0.25
AFIN = 0.35
ESCALA = 1.4
SEMIVIDA_TENSION = 18.0
U0 = 20.0
PASO = 4.0
CASCADA = 0.5
MAX_RUPTURAS_POR_SUCESO = 3
ESTADISTICAS = ("fuerza", "velocidad", "salud")
LETRAS_VETA = {"fuerza": "F", "velocidad": "V", "salud": "S"}
UMBRAL_IDENTIDAD = 6
VENTANA_SECUENCIA = 6
IDENTIDADES_DOMINANTES = {
    "F": "Corazón de roble",
    "V": "Fibra de fresno",
    "S": "Savia de olivo",
}


def _identidad_en(historial: str) -> str | None:
    """Reconoce una identidad en un único prefijo del historial."""
    longitud = len(historial)
    for letra, identidad in IDENTIDADES_DOMINANTES.items():
        if 3 * historial.count(letra) >= 2 * longitud:
            return identidad

    cola = historial[-VENTANA_SECUENCIA:]
    if len(set(cola[:3])) == 3 and cola[:3] == cola[3:]:
        return "Veta en espiral"
    if len(set(cola)) == 2 and cola[:2] * 3 == cola:
        return "Veta trenzada"
    return None


def identidad_de(historial: str) -> str | None:
    """Devuelve la primera identidad reconocida, que no cambia ni desaparece."""
    for longitud in range(UMBRAL_IDENTIDAD, len(historial) + 1):
        identidad = _identidad_en(historial[:longitud])
        if identidad is not None:
            return identidad
    return None


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

# Las cuatro acciones de cuidado; son la consulta por defecto de db.esperas.
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


# Un recluta se guarda sin nombre y no puede salir de la incubadora hasta que se
# lo pongan. El nombre vacío es la marca: no hace falta una columna nueva porque
# `normalizar_nombre` ya impide que nadie llegue aquí por las buenas, y así la
# regla se lee en el propio dato en vez de en una bandera aparte.
NOMBRE_PENDIENTE = ""
SIN_NOMBRE = "sin nombrar"


def esta_sin_nombrar(criatura: Criatura) -> bool:
    return not criatura.nombre


def nombre_visible(criatura: Criatura) -> str:
    """Cómo se le llama mientras no tenga nombre propio.

    Existe porque Discord rechaza una etiqueta vacía en un desplegable: sin
    esto, el menú del plantel reventaría al listar a un recién reclutado.
    """
    return criatura.nombre or SIN_NOMBRE

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

# Efectos numéricos de cada cuidado. La simulación los aplica y las capas de
# presentación los describen sin repetir reglas ni interpretar la narrativa.
EFECTOS_CUIDADO = {
    ALIMENTAR: {"hambre": 30, "ent_salud": 1},
    JUGAR: {"animo": 25, "hambre": -5, "ent_velocidad": 1},
    ENTRENAR: {"hambre": -15, "animo": -10, "ent_fuerza": 2},
    LIMPIAR: {"limpieza": 100.0},
}
EFECTO_EMPACHO = {"hambre": 10, "animo": -15}

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
XP_AVENTURA = 4
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
    ten_fuerza: float = 0.0
    ten_velocidad: float = 0.0
    ten_salud: float = 0.0
    historial_vetas: str = ""
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


@dataclass(frozen=True)
class Impronta:
    """Fisiología derivada de especie e id, nunca persistida."""

    giro: int
    afinidades: tuple[float, float, float]

    @property
    def anillo(self) -> tuple[str, str, str]:
        return (
            ESTADISTICAS if self.giro == 1
            else ("fuerza", "salud", "velocidad")
        )


@dataclass(frozen=True)
class Esfuerzo:
    """Un resultado real que puede dejar tensión en una estadística."""

    stat: str
    bruto: float
    profunda: bool = False
    forzar: bool = False
    causa: str = ""


@dataclass(frozen=True)
class Ruptura:
    """Una veta ganada dentro de un suceso."""

    stat: str
    umbral: float
    antes: int = 0
    despues: int = 0
    cascada: bool = False
    causa: str = ""


def impronta_de(criatura: Criatura) -> Impronta:
    """Deriva siempre la misma impronta sin añadir una columna a SQLite."""
    rng = _RandomImpronta(f"{criatura.especie}:{criatura.id}")
    giro = rng.choice((1, -1))
    crudas = tuple(rng.choice((-1, 0, 1)) for _ in ESTADISTICAS)
    media = sum(crudas) / len(crudas)
    afinidades = tuple(AFIN * (valor - media) for valor in crudas)
    return Impronta(giro, (afinidades[0], afinidades[1], afinidades[2]))


def _vetas(criatura: Criatura) -> tuple[int, int, int]:
    return criatura.niv_fuerza, criatura.niv_velocidad, criatura.niv_salud


def _tensiones(criatura: Criatura) -> tuple[float, float, float]:
    return criatura.ten_fuerza, criatura.ten_velocidad, criatura.ten_salud


def umbral_veta(criatura: Criatura) -> float:
    """Umbral global de la siguiente veta."""
    return U0 + PASO * sum(_vetas(criatura))


def _indice_stat(stat: str) -> int:
    try:
        return ESTADISTICAS.index(stat)
    except ValueError as exc:
        raise ValueError(f"estadística desconocida: {stat}") from exc


def _real(valor: float, nombre: str) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{nombre} inválido: {valor!r}") from exc


def receptividad(criatura: Criatura, stat: str) -> float:
    """Multiplicador acoplado al historial de vetas e impronta."""
    indice = _indice_stat(stat)
    vetas = _vetas(criatura)
    media = sum(vetas) / 3.0
    impronta = impronta_de(criatura)
    anillo = impronta.anillo
    anterior = anillo[(anillo.index(stat) - 1) % 3]
    valor = BETA * (vetas[indice] - media)
    valor += impronta.afinidades[indice]
    valor -= GAMMA * vetas[_indice_stat(anterior)]
    # Limitar el exponente evita overflow con criaturas antiguas sin cambiar
    # el resultado dentro del rango mecánico observable.
    exponente = max(math.log(0.35), min(math.log(3.0), valor))
    return max(0.35, min(3.0, math.exp(exponente)))


def esfuerzos_de_cuidado(criatura: Criatura, accion: str) -> tuple[Esfuerzo, ...]:
    """Calcula la marca de una acción usando sus barras antes del efecto."""
    if accion == ALIMENTAR:
        return (Esfuerzo(
            "salud", 4.0 * (100.0 - criatura.hambre) / 100.0,
            criatura.hambre < 15.0, causa=accion,
        ),)
    if accion == JUGAR:
        return (Esfuerzo(
            "velocidad", 3.5 * (100.0 - criatura.animo) / 100.0,
            causa=accion,
        ),)
    if accion == ENTRENAR:
        bruto = 4.0 * max(
            15.0 / max(15.0, criatura.hambre),
            10.0 / max(10.0, criatura.animo),
        )
        return (Esfuerzo("fuerza", bruto, causa=accion),)
    if accion == LIMPIAR:
        return (Esfuerzo(
            "salud", 1.5 * (100.0 - criatura.limpieza) / 100.0,
            causa=accion,
        ),)
    return ()


def esfuerzo_de_cuidado(criatura: Criatura, accion: str) -> Esfuerzo | None:
    """Devuelve el esfuerzo de una acción de cuidado concreta."""
    emisiones = esfuerzos_de_cuidado(criatura, accion)
    return emisiones[0] if emisiones else None


def esfuerzo_de_competencia(
    stat: str, margen: float, gano: bool,
) -> Esfuerzo:
    margen = max(0.0, _real(margen, "margen"))
    bruto = 3.0 * (
        0.5 + 0.5 * (1.0 - min(1.0, margen / 30.0))
    ) * (1.0 if gano else 1.3)
    return Esfuerzo(stat, bruto, margen <= 2.0, causa=COMPETIR)


def esfuerzo_de_aventura(stat: str, holgura: float) -> Esfuerzo:
    holgura = _real(holgura, "holgura")
    return Esfuerzo(
        stat, 3.0 * (1.0 - min(1.0, abs(holgura) / 10.0)),
        holgura in (0.0, 1.0), causa=AVENTURA,
    )


def _aplicar_rupturas(
    criatura: Criatura,
    limite: int = MAX_RUPTURAS_POR_SUCESO,
    causa: str = "",
) -> tuple[Criatura, tuple[Ruptura, ...]]:
    """Rompe tensiones ya acumuladas, con selección y cascada deterministas."""
    rupturas: list[Ruptura] = []
    arrastradas: set[str] = set()
    estado = criatura
    while len(rupturas) < limite:
        umbral = umbral_veta(estado)
        tensiones = _tensiones(estado)
        elegibles = [
            stat for stat, tension in zip(ESTADISTICAS, tensiones)
            if tension >= umbral
        ]
        if not elegibles:
            break
        # max estable con este orden: primero tensión, luego FUE, VEL, SAL.
        stat = max(
            elegibles,
            key=lambda candidato: (tensiones[_indice_stat(candidato)],
                                   -_indice_stat(candidato)),
        )
        cascada = stat in arrastradas
        stat_antes = getattr(estado, stat)
        indice = _indice_stat(stat)
        antes = list(tensiones)
        anillo = impronta_de(estado).anillo
        posicion = anillo.index(stat)
        siguiente = anillo[(posicion + 1) % 3]
        anterior = anillo[(posicion - 1) % 3]
        siguiente_i = _indice_stat(siguiente)
        anterior_i = _indice_stat(anterior)
        acoplamiento = CASCADA * umbral
        siguiente_era_elegible = antes[siguiente_i] >= umbral
        tensiones_nuevas = list(antes)
        tensiones_nuevas[indice] = max(0.0, antes[indice] - umbral)
        tensiones_nuevas[siguiente_i] += acoplamiento
        tensiones_nuevas[anterior_i] = max(
            0.0, antes[anterior_i] - acoplamiento
        )
        vetas = list(_vetas(estado))
        vetas[indice] += 1
        umbral_nuevo = U0 + PASO * sum(vetas)
        arrastradas = {
            candidata for candidata in arrastradas
            if candidata != stat
            and tensiones_nuevas[_indice_stat(candidata)] >= umbral_nuevo
        }
        if (
            not siguiente_era_elegible
            and tensiones_nuevas[siguiente_i] >= umbral_nuevo
        ):
            arrastradas.add(siguiente)
        estado = replace(
            estado,
            niv_fuerza=vetas[0],
            niv_velocidad=vetas[1],
            niv_salud=vetas[2],
            ten_fuerza=tensiones_nuevas[0],
            ten_velocidad=tensiones_nuevas[1],
            ten_salud=tensiones_nuevas[2],
            historial_vetas=estado.historial_vetas + LETRAS_VETA[stat],
        )
        rupturas.append(Ruptura(
            stat=stat,
            umbral=umbral,
            antes=stat_antes,
            despues=getattr(estado, stat),
            cascada=cascada,
            causa=causa,
        ))
    return estado, tuple(rupturas)


def romper_vetas(
    criatura: Criatura, max_rupturas: int = MAX_RUPTURAS_POR_SUCESO,
) -> tuple[Criatura, tuple[Ruptura, ...]]:
    return _aplicar_rupturas(criatura, max(0, max_rupturas))


def emitir_tension(
    criatura: Criatura, esfuerzo: Esfuerzo | str, bruto: float | None = None,
    *, profunda: bool = False, forzar: bool = False, causa: str = "",
    max_rupturas: int = MAX_RUPTURAS_POR_SUCESO,
) -> tuple[Criatura, tuple[Ruptura, ...]]:
    """Añade una emisión, filtra el esfuerzo y rompe como máximo tres veces."""
    if isinstance(esfuerzo, str):
        esfuerzo = Esfuerzo(esfuerzo, bruto or 0.0, profunda, forzar, causa)
    if esfuerzo.stat not in ESTADISTICAS:
        raise ValueError(f"estadística desconocida: {esfuerzo.stat}")
    valor = max(0.0, _real(esfuerzo.bruto, "esfuerzo"))
    if (
        not (esfuerzo.forzar or forzar or esfuerzo.profunda or profunda)
        and valor < UMBRAL_ESFUERZO
    ):
        return criatura, ()
    if esfuerzo.profunda or profunda:
        valor *= PROFUNDA
    if valor <= 0.0:
        return criatura, ()
    indice = _indice_stat(esfuerzo.stat)
    tensiones = list(_tensiones(criatura))
    tensiones[indice] = max(
        0.0, tensiones[indice] + valor * ESCALA * receptividad(criatura, esfuerzo.stat)
    )
    con_tension = replace(
        criatura,
        ten_fuerza=tensiones[0],
        ten_velocidad=tensiones[1],
        ten_salud=tensiones[2],
    )
    return _aplicar_rupturas(
        con_tension,
        max(0, max_rupturas),
        esfuerzo.causa or causa,
    )


def _surge(nivel: int) -> float:
    return (3.0, 4.0, 5.0, 6.0)[nivel - 2] if 2 <= nivel <= 5 else 2.5


def _emisiones_de_nivel(criatura: Criatura, nivel: int) -> tuple[Esfuerzo, ...]:
    definicion = criatura.def_especie
    pesos = (definicion.fuerza, definicion.velocidad, definicion.salud)
    total = sum(pesos)
    surge = _surge(nivel)
    return tuple(
        Esfuerzo(stat, surge * peso / total, forzar=True, causa="nivel")
        for stat, peso in zip(ESTADISTICAS, pesos)
    )


def aplicar_evento(
    criatura: Criatura, esfuerzos: tuple[Esfuerzo, ...] = (),
    ganada: int = 0, rng: random.Random | None = None,
) -> tuple[Criatura, tuple[Ruptura, ...]]:
    """Aplica emisiones reales y después las subidas de nivel del mismo evento."""
    del rng  # La firma conserva compatibilidad; VETAS no tira dados de crecimiento.
    estado = criatura
    rupturas: list[Ruptura] = []
    for esfuerzo in esfuerzos:
        estado, nuevas = emitir_tension(
            estado, esfuerzo, max_rupturas=MAX_RUPTURAS_POR_SUCESO - len(rupturas)
        )
        rupturas.extend(nuevas)
    xp = estado.xp + ganada
    nivel = estado.nivel
    while xp >= xp_para_subir(nivel):
        xp -= xp_para_subir(nivel)
        nivel += 1
        for esfuerzo in _emisiones_de_nivel(estado, nivel):
            estado, nuevas = emitir_tension(
                estado, esfuerzo,
                max_rupturas=MAX_RUPTURAS_POR_SUCESO - len(rupturas),
            )
            rupturas.extend(nuevas)
    estado = replace(estado, xp=xp, nivel=nivel)
    return estado, tuple(rupturas)


def aplicar_xp(
    criatura: Criatura, ganada: int, rng: random.Random | None = None
) -> tuple[Criatura, list[Ruptura]]:
    """Suma XP y emite el surge determinista de cada nivel alcanzado."""
    estado, rupturas = aplicar_evento(criatura, ganada=ganada, rng=rng)
    return estado, list(rupturas)


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
    factor_tension = 0.5 ** (horas / SEMIVIDA_TENSION)

    avanzada = replace(
        criatura,
        hambre=hambre,
        animo=animo,
        limpieza=limpieza,
        ten_fuerza=max(0.0, criatura.ten_fuerza * factor_tension),
        ten_velocidad=max(0.0, criatura.ten_velocidad * factor_tension),
        ten_salud=max(0.0, criatura.ten_salud * factor_tension),
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
    rupturas: tuple[Ruptura, ...] = ()
    marca: bool = False
    # Alias de lectura para integraciones antiguas; las nuevas deben usar
    # `rupturas`, que conserva la causa y la cascada de cada veta.
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
        if self.rupturas and not self.subidas:
            object.__setattr__(
                self, "subidas", tuple(ruptura.stat for ruptura in self.rupturas)
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
    crecida, rupturas = aplicar_evento(
        bruto.criatura, esfuerzos_de_cuidado(criatura, accion), ganada, rng
    )
    return ResultadoAccion(
        criatura=crecida,
        mensaje=bruto.mensaje,
        rupturas=rupturas,
        marca=bool(rupturas or _tensiones(crecida) != _tensiones(bruto.criatura)),
        etapa_anterior=criatura.etapa if ganada else None,
    )


def _efecto_de(criatura: Criatura, accion: str) -> ResultadoAccion:
    """El efecto de la acción sobre las barras, sin tocar la experiencia."""
    if not criatura.viva:
        return ResultadoAccion(criatura, "Tu gachamon ya no está entre nosotros.", ok=False)

    if accion == ACTUALIZAR:
        return ResultadoAccion(criatura, "")

    if accion == ALIMENTAR:
        if criatura.hambre >= UMBRAL_EMPACHO:
            nueva = replace(
                criatura,
                hambre=_limitar(criatura.hambre + EFECTO_EMPACHO["hambre"]),
                animo=_limitar(criatura.animo + EFECTO_EMPACHO["animo"]),
            )
            return ResultadoAccion(nueva, "Se ha empachado. No tenía nada de hambre.")
        efecto = EFECTOS_CUIDADO[ALIMENTAR]
        nueva = replace(
            criatura,
            hambre=_limitar(criatura.hambre + efecto["hambre"]),
            ent_salud=criatura.ent_salud + efecto["ent_salud"],
            # Alimentarla rearma el aviso: si vuelve a pasar hambre, se avisa
            # otra vez. Es la única acción que sube la comida, así que es el
            # único sitio donde hace falta reiniciarlo.
            avisada=False,
        )
        return ResultadoAccion(nueva, "Ñam. Se lo ha comido todo.")

    if accion == JUGAR:
        efecto = EFECTOS_CUIDADO[JUGAR]
        nueva = replace(
            criatura,
            animo=_limitar(criatura.animo + efecto["animo"]),
            hambre=_limitar(criatura.hambre + efecto["hambre"]),
            ent_velocidad=criatura.ent_velocidad + efecto["ent_velocidad"],
        )
        return ResultadoAccion(nueva, "Juegan un rato. Está encantad{o/a}.")

    if accion == ENTRENAR:
        efecto = EFECTOS_CUIDADO[ENTRENAR]
        nueva = replace(
            criatura,
            hambre=_limitar(criatura.hambre + efecto["hambre"]),
            animo=_limitar(criatura.animo + efecto["animo"]),
            ent_fuerza=criatura.ent_fuerza + efecto["ent_fuerza"],
        )
        return ResultadoAccion(nueva, "Entrenamiento duro. Ha quedado molid{o/a}.")

    if accion == LIMPIAR:
        nueva = replace(
            criatura, limpieza=EFECTOS_CUIDADO[LIMPIAR]["limpieza"]
        )
        return ResultadoAccion(nueva, "Como nuev{o/a}.")

    raise ValueError(f"acción desconocida: {accion}")


def aplicar_competencia(
    criatura: Criatura,
    gano: bool,
    stat: str,
    rng: random.Random | None = None,
    margen: float | None = None,
) -> tuple[Criatura, list[Ruptura]]:
    """Aplica desgaste, marca real, XP y entrenamiento de haber competido."""
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
    esfuerzo = esfuerzo_de_competencia(
        stat, 30.0 if margen is None else margen, gano
    )
    estado, rupturas = aplicar_evento(
        desgastada,
        (esfuerzo,),
        XP_VICTORIA if gano else XP_DERROTA,
        rng,
    )
    return estado, list(rupturas)
