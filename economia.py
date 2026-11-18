"""Economía transaccional: saldos, límites diarios y operaciones idempotentes.

Este módulo concentra las reglas monetarias. ``db`` conserva el esquema, las
migraciones y los repositorios de dominio; la dependencia va sólo de aquí a db.
"""
from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

import aventura as av
import competir as comp
import cosmeticos as cos
import db
import departamento as dep
import huerto as hue
import logros as lgr
import objetos as obj
import simulacion as sim

logger = logging.getLogger(__name__)

# El bote diario. Es **uno solo para todo** lo que se gana: cuidar, evolucionar,
# competir y lo que te encuentres en una aventura salen de aquí. Antes no había
# tope en monedas —sólo por número de eventos— y el techo de 40 era un número
# derivado; ahora el techo es esto y se puede decir en una frase.
TOPE_DIARIO_ASCIICOINS = 20

TOPE_CUIDADOS = 12
TOPE_EVOLUCIONES = 1
TOPE_COMPETENCIAS = 3
PREMIO_CUIDADO = 1
PREMIO_EVOLUCION = 10
PREMIO_COMPETENCIA = 4
PREMIO_GANADOR = 6


@dataclass(frozen=True)
class Saldos:
    asciicoins: int
    asciigems: int


@dataclass(frozen=True)
class ResultadoCompra:
    comprada: bool
    replay: bool
    saldos: Saldos
    objeto: str

    def __bool__(self) -> bool:
        return self.comprada


@dataclass(frozen=True)
class ResultadoCuidado:
    criatura: sim.Criatura
    mensaje: str
    ok: bool = True
    espera: timedelta | None = None
    rupturas: tuple[sim.Ruptura, ...] = ()
    marca: bool = False
    subidas: tuple[str, ...] = ()
    etapa_anterior: str | None = None
    delta_asciicoins: int = 0
    delta_evolucion: int = 0
    ent_salud_ganada: int = 0
    usados: int = 0
    limite: int = TOPE_CUIDADOS
    evolucion_usadas: int = 0
    replay: bool = False
    topada: bool = False
    # La acción era válida pero el dominio devolvió la misma criatura: no hay
    # nada nuevo que enseñar. Sin esto, Discord no distingue este caso de un
    # cuidado normal y publica otra ficha idéntica.
    sin_efecto: bool = False

    @property
    def evoluciono(self) -> bool:
        return (
            self.etapa_anterior is not None
            and self.etapa_anterior != self.criatura.etapa
        )


@dataclass(frozen=True)
class ResultadoATodos:
    """Cómo salió un cuidado «a todos»: a quiénes les tocó y de cuántos."""

    accion: str
    tocados: tuple[int, ...] = ()       # sus ids, en el orden del plantel
    de_cuantos: int = 0                 # los vivos que tenía
    delta_asciicoins: int = 0           # lo de sus cuidados, evoluciones incluidas
    cuidados: tuple[ResultadoCuidado, ...] = ()   # uno por tocado; vacío en un replay
    replay: bool = False


@dataclass(frozen=True)
class ReciboCompetencia:
    usuario_id: str
    delta_asciicoins: int
    delta_competencia: int
    delta_evolucion: int
    usados: int
    evolucion_usadas: int = 0
    limite: int = TOPE_COMPETENCIAS
    topada: bool = False
    evoluciono: bool = False
    evolucion_topada: bool = False


@dataclass(frozen=True)
class ResultadoCompetencia:
    encuentro: comp.Encuentro | None
    antes: tuple[sim.Criatura, ...] = ()
    despues: tuple[sim.Criatura, ...] = ()
    rupturas: tuple[tuple[sim.Ruptura, ...], ...] = ()
    subidas: tuple[tuple[str, ...], ...] = ()
    recibos: tuple[ReciboCompetencia, ...] = ()
    replay: bool = False
    problema: str | None = None
    problema_usuario_id: str | None = None
    problema_criatura: sim.Criatura | None = None
    espera: timedelta | None = None


@dataclass(frozen=True)
class ResultadoViaje:
    criatura: sim.Criatura | None
    antes: sim.Criatura | None = None
    rupturas: tuple[sim.Ruptura, ...] = ()
    problema: str | None = None


def ejecutar_viaje(
    usuario_id: str,
    guild_id: str,
    criatura_id: int,
    salida: av.Salida,
    ahora: datetime,
    percance: av.Percance | None = None,
    viaje: av.Viaje | None = None,
) -> ResultadoViaje:
    """Confirma el viaje sobre la criatura activa actual, antes de publicarlo.

    Las aventuras no tienen ledger histórico; esta frontera sólo evita aplicar
    una vista vieja sobre otra criatura o sobre un estado concurrente.

    `viaje` es de dónde sale el marcador —dónde estuvo y cuántos nodos pasó—,
    que se apunta aquí para que vaya en la misma transacción que el desgaste.
    Es opcional porque lo que confirma el viaje es la `salida`; sin él, todo
    ocurre igual pero no se apunta nada.
    """
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        actual = db.criatura_activa_en(con, usuario_id, guild_id)
        if actual is None:
            return ResultadoViaje(None, problema="No hay un gachamon activo.")
        if actual.id != criatura_id:
            return ResultadoViaje(
                actual,
                problema="La aventura ya no pertenece al gachamon activo.",
            )
        avanzado = db._avanzar_en(con, actual, ahora)
        nueva, rupturas = av.aplicar_viaje(avanzado, salida, percance)
        db._guardar(con, nueva)
        if viaje is not None:
            db.apuntar_en(con, nueva.id, lgr.AVENTURAS)
            db.apuntar_en(con, nueva.id, lgr.clave_de_bioma(viaje.bioma.clave))
            if viaje.nodos_superados:
                db.apuntar_en(
                    con, nueva.id, lgr.NODOS, viaje.nodos_superados
                )
        return ResultadoViaje(
            nueva, antes=avanzado, rupturas=tuple(rupturas)
        )


def _fecha_economica(ahora: datetime) -> str:
    return ahora.astimezone(timezone.utc).date().isoformat()


def _asegurar_monedero(
    con, usuario_id: str, guild_id: str, *, ya_estaba: bool = False
) -> None:
    """Le crea el monedero a quien no lo tiene; uno que ya existe no se toca.

    Nace con 50 monedas y 50 gemas mientras el día del cambio no haya ocurrido
    en esta base, y con 0 y 0 desde entonces (`db.PARTIDA_DE_UN_MONEDERO_NUEVO`);
    `partida` anota con cuánto nació. Con `ya_estaba` nace con 50 y 50 haya
    ocurrido o no: lo pide el día del cambio para quien ya jugaba, porque su
    marca se escribe al empezar, antes de asegurar los monederos.

    Una sola sentencia y sin leer antes: un `INSERT OR IGNORE` que decide la
    partida dentro de la misma sentencia.
    """
    partida = db.PARTIDA_DE_ANTES if ya_estaba else db.PARTIDA_DE_UN_MONEDERO_NUEVO
    con.execute(
        "INSERT OR IGNORE INTO monederos "
        "(usuario_id, guild_id, asciicoins, asciigems, partida) "
        f"SELECT ?, ?, partida, partida, partida FROM (SELECT {partida} AS partida)",
        (usuario_id, guild_id),
    )


def _saldos_en(con, usuario_id: str, guild_id: str) -> Saldos:
    _asegurar_monedero(con, usuario_id, guild_id)
    fila = con.execute(
        "SELECT asciicoins, asciigems FROM monederos "
        "WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    ).fetchone()
    return Saldos(fila["asciicoins"], fila["asciigems"])


def saldos(usuario_id: str, guild_id: str) -> Saldos:
    with db.conectar() as con:
        return _saldos_en(con, usuario_id, guild_id)


# --- La devolución de lo retirado ---------------------------------------------

@dataclass(frozen=True)
class ResumenDevolucion:
    personas: int
    piezas: int
    gemas: int


def devolver_cosmeticos_retirados(ahora: datetime) -> ResumenDevolucion:
    """Devuelve las gemas de lo retirado, lo saca de los roperos y de los gachamones.

    Corre en cada arranque y la segunda vez no hace nada. Todo va bajo un único
    `BEGIN IMMEDIATE`: pagar y anotar en `devoluciones` son lo mismo, y sólo
    cobra quien consigue que la fila entre (`rowcount`), así que ni dos
    arranques a la vez ni una pieza que reaparezca pagan dos veces. No pasa por
    `operaciones_economia`: una devolución no es una ganancia.
    """
    claves = tuple(cos.RETIRADOS)
    marcas = ", ".join("?" for _ in claves)
    personas: set[tuple[str, str]] = set()
    piezas = total = 0
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        # 1. Lo retirado que aún lleva puesto algún gachamon pasa al ropero.
        for columna in cos.TIPOS_RETIRADOS:
            con.execute(
                f"INSERT OR IGNORE INTO ropero (usuario_id, guild_id, cosmetico) "
                f"SELECT usuario_id, guild_id, {columna} FROM criaturas "
                f"WHERE {columna} IN ({marcas})",
                claves,
            )
        # 2. Se paga una vez por persona y pieza.
        filas = con.execute(
            "SELECT usuario_id, guild_id, cosmetico FROM ropero "
            f"WHERE cosmetico IN ({marcas})",
            claves,
        ).fetchall()
        for fila in filas:
            gemas = cos.RETIRADOS[fila["cosmetico"]]
            entro = con.execute(
                "INSERT OR IGNORE INTO devoluciones "
                "(usuario_id, guild_id, cosmetico, gemas, devuelta_en) "
                "VALUES (?, ?, ?, ?, ?)",
                (fila["usuario_id"], fila["guild_id"], fila["cosmetico"],
                 gemas, ahora.isoformat()),
            ).rowcount
            if not entro:
                continue
            _asegurar_monedero(con, fila["usuario_id"], fila["guild_id"])
            con.execute(
                "UPDATE monederos SET asciigems = asciigems + ? "
                "WHERE usuario_id = ? AND guild_id = ?",
                (gemas, fila["usuario_id"], fila["guild_id"]),
            )
            personas.add((fila["usuario_id"], fila["guild_id"]))
            piezas += 1
            total += gemas
        # 3. Fuera del ropero, hayan pagado o no.
        con.execute(f"DELETE FROM ropero WHERE cosmetico IN ({marcas})", claves)
        # 4. Y de todas las criaturas, vivas y muertas.
        for columna in cos.TIPOS_RETIRADOS:
            con.execute(
                f"UPDATE criaturas SET {columna} = NULL WHERE {columna} IS NOT NULL"
            )
    return ResumenDevolucion(len(personas), piezas, total)


# --- El día del cambio -------------------------------------------------------
#
# Las casas, el refugio y el huerto de cada casa se cambian por un solo
# departamento por casillas. Ese día se convierte, una sola vez, lo de cada
# quien, y nadie pierde nada: lo que no tiene sitio en lo nuevo se le devuelve.

# Su clave vive en `db`, que también la lee para saber con cuánto nace un
# monedero.
CAMBIO_DE_LA_VIVIENDA = db.CAMBIO_DE_LA_VIVIENDA
# Lo que costaban el día del cambio. Van escritos aquí y no se leen de
# `casas.py` ni de `objetos.py`, que dejan de tenerlos: se devuelve lo que valían
# entonces. Cada casa vuelve al precio de la que es (una pequeña que se mejoró a
# grande vuelve como grande).
PRECIO_DE_LAS_CASAS_DE_ANTES = {"pequena": 200, "mediana": 500, "grande": 1200}
# Lo que se suma, ese día, al precio de una casa mediana o grande: la mejora que
# el dueño decidió para quien ya la había comprado.
MEJORA_DE_LAS_CASAS_DE_ANTES = 140
_CASAS_QUE_SE_MEJORAN = ("mediana", "grande")
PRECIO_DEL_TICKET_DE_ANTES = 40
_TICKET_DE_ANTES = "ticket_refugio"
_CAMA_SENCILLA = "cama_sencilla"
# Las que caben en el departamento más grande, el de 8 × 8.
_CAMAS_QUE_CABEN = dep.MAXIMO_DE_GACHAMONES + 1
# Dónde puede tener filas cada quien, y con qué columna: tener alguna en
# cualquiera de ellas es ser alguien a quien el cambio le toca.
_LO_DE_CADA_QUIEN = (
    ("criaturas", "usuario_id"), ("monederos", "usuario_id"),
    ("inventario", "usuario_id"), ("casas_propias", "usuario_id"),
    ("mobiliario", "usuario_id"), ("huerto", "usuario_id"),
    ("hogar", "usuario_id"), ("avatares", "usuario_id"),
    ("cuentas_web", "usuario_id"), ("buzon", "para_usuario"),
)


@dataclass(frozen=True)
class ResumenDelCambio:
    """A cuántas personas tocó, cuántas camas regaló entre puestas y guardadas,
    y cuántas monedas devolvió."""

    personas: int = 0
    camas: int = 0
    monedas: int = 0


def el_dia_del_cambio(
    ahora: datetime, rng: random.Random | None = None
) -> ResumenDelCambio:
    """Pasa a cada quien a la vivienda por casillas, una sola vez.

    Todo va bajo un único `BEGIN IMMEDIATE` con la marca de `cambios_hechos`
    dentro: o se hace entero, marca incluida, o no queda nada hecho, y de dos
    arranques a la vez sólo el primero encuentra algo que hacer. Como en
    `devolver_cosmeticos_retirados`, lo devuelto no pasa por
    `operaciones_economia`: una devolución no es una ganancia.

    A cada persona le entrega el buzón, le cosecha lo plantado, le devuelve los
    tickets y las casas, le paga las medallas suyas que tenía ganadas y sin
    cobrar, le crea el departamento con sus camas, le guarda los muebles y le
    escribe la carta del alcalde (`_mudar_a`). Y a todos los
    gachamones vivos el reloj les parte de `ahora`: a nadie se le cobra el
    tiempo que pasó desde la última vez que se guardó.

    Si ya hay departamentos y la marca no estaba, la base no es la que se
    espera: no hace nada, marca incluida, y lo dice con un `RuntimeError` para
    quien publica, que detiene el arranque.
    """
    rng = rng or random.Random()
    personas = camas = monedas = 0
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        if not db._una_sola_vez(con, CAMBIO_DE_LA_VIVIENDA, ahora):
            return ResumenDelCambio()
        if con.execute("SELECT 1 FROM departamentos LIMIT 1").fetchone():
            raise RuntimeError(
                "El día del cambio encontró departamentos ya creados y sin su "
                "marca: no se hizo nada. La base no está como se esperaba; "
                "restaura la copia de antes o averigua de dónde salieron antes "
                "de arrancar."
            )
        for usuario_id, guild_id in _quienes_ya_estaban(con):
            regaladas, devueltas = _mudar_a(con, usuario_id, guild_id, ahora, rng)
            personas += 1
            camas += regaladas
            monedas += devueltas
        con.execute(
            "UPDATE criaturas SET actualizada_en = ? WHERE muerta_en IS NULL",
            (ahora.isoformat(),),
        )
    return ResumenDelCambio(personas, camas, monedas)


def _quienes_ya_estaban(con) -> list[tuple[str, str]]:
    """Cada pareja persona + servidor con alguna fila de lo suyo, en orden."""
    union = " UNION ".join(
        f"SELECT {quien}, guild_id FROM {tabla}" for tabla, quien in _LO_DE_CADA_QUIEN
    )
    return [(f[0], f[1]) for f in con.execute(f"{union} ORDER BY 1, 2")]


def _mudar_a(
    con, usuario_id: str, guild_id: str, ahora: datetime, rng: random.Random
) -> tuple[int, int]:
    """El cambio de una persona. Devuelve cuántas camas le regaló y cuántas
    monedas le devolvió.

    El monedero se le asegura le toque o no una devolución: quien ya jugaba lo
    conserva tal cual, y si todavía no tenía fila lo recibe con 50 y 50, como
    le habría nacido antes del cambio. Va con `ya_estaba` porque la marca del
    cambio ya está escrita a estas alturas, y sin él nacería en cero, como el
    de quien empieza. El buzón va antes que los tickets, para que un ticket
    regalado también se devuelva.

    Las medallas de la persona que tenía ganadas y nadie le pagó se le pagan
    aquí, una sola vez y como cualquier otra (`_pagar_logros_de_persona_en`),
    tenga o no gachamones vivos. Van después de asegurarle el monedero: si no lo
    tuviera, el pago le crearía el de quien empieza, en cero.
    """
    _asegurar_monedero(con, usuario_id, guild_id, ya_estaba=True)
    regalos = _entregar_el_buzon(con, usuario_id, guild_id)
    cosecha = _cosechar_lo_plantado(con, usuario_id, guild_id, rng)
    tickets = _sacar_los_tickets(con, usuario_id, guild_id)
    casas, monedas_por_casas = _cerrar_las_casas(con, usuario_id, guild_id)
    monedas_por_tickets = tickets * PRECIO_DEL_TICKET_DE_ANTES
    devueltas = monedas_por_casas + monedas_por_tickets
    if devueltas:
        con.execute(
            "UPDATE monederos SET asciicoins = asciicoins + ? "
            "WHERE usuario_id = ? AND guild_id = ?",
            (devueltas, usuario_id, guild_id),
        )
    medallas = _pagar_logros_de_persona_en(con, usuario_id, guild_id, ahora)
    vivos = db.plantel_en(con, usuario_id, guild_id)
    ancho, fondo, puestas, regaladas = _departamento_del_alcalde(
        con, usuario_id, guild_id, len(vivos), ahora
    )
    muebles = _guardar_los_muebles_de_antes(con, usuario_id, guild_id)
    db.guardar_carta_en(con, usuario_id, guild_id, CAMBIO_DE_LA_VIVIENDA, {
        "ancho": ancho, "fondo": fondo, "camas": puestas, "vivos": len(vivos),
        "casas": casas, "monedas_por_casas": monedas_por_casas,
        "muebles": muebles, "cosecha": cosecha,
        "tickets": tickets, "monedas_por_tickets": monedas_por_tickets,
        "regalos": regalos, "gemas_por_medallas": medallas.asciigems,
        # Como todo se publica junto, ese día los que se pusieron el nombre
        # solos son justo los reclutas que lo esperaban.
        "nombres": [
            {"especie": c.especie, "nombre": c.nombre}
            for c in vivos if c.se_nombro_solo
        ],
    }, ahora)
    return regaladas, devueltas


def _entregar_el_buzon(con, usuario_id: str, guild_id: str) -> int:
    """Cada regalo sin recoger pasa a la mochila y queda recogido. Dice cuántos."""
    regalos = con.execute(
        "SELECT id, objeto FROM buzon "
        "WHERE para_usuario = ? AND guild_id = ? AND recogido = 0 ORDER BY id",
        (usuario_id, guild_id),
    ).fetchall()
    for regalo in regalos:
        db.guardar_en_la_mochila_en(con, usuario_id, guild_id, regalo["objeto"])
        con.execute("UPDATE buzon SET recogido = 1 WHERE id = ?", (regalo["id"],))
    return len(regalos)


def _cosechar_lo_plantado(
    con, usuario_id: str, guild_id: str, rng: random.Random
) -> dict[str, int]:
    """Cosecha cada bancal plantado como si estuviera maduro y lo deja en barbecho.

    El color lo hereda lo sembrado o se sortea, salen de 2 a 4 porotos y un
    arcoíris sustituye a uno. Dice qué salió y cuánto de cada cosa.
    """
    cosecha: dict[str, int] = {}
    for bancal in con.execute(
        "SELECT sembrado FROM huerto WHERE usuario_id = ? AND guild_id = ? "
        "ORDER BY casa_id, bancal",
        (usuario_id, guild_id),
    ).fetchall():
        color = hue.color_sembrado(bancal["sembrado"]) or hue.tirar_color(rng)
        lote = hue.tirar_cuantos(rng)
        arcoiris = hue.tirar_arcoiris(rng)
        normales = lote - 1 if arcoiris else lote
        for clave, cuantos in (
            (hue.clave_de_poroto(color), normales),
            (hue.clave_de_poroto(hue.ARCOIRIS), int(arcoiris)),
        ):
            if cuantos:
                db.guardar_en_la_mochila_en(con, usuario_id, guild_id, clave, cuantos)
                cosecha[clave] = cosecha.get(clave, 0) + cuantos
    con.execute(
        "DELETE FROM huerto WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    )
    return cosecha


def _sacar_los_tickets(con, usuario_id: str, guild_id: str) -> int:
    """Saca de la mochila los tickets del refugio y dice cuántos eran."""
    fila = con.execute(
        "SELECT cantidad FROM inventario "
        "WHERE usuario_id = ? AND guild_id = ? AND objeto = ?",
        (usuario_id, guild_id, _TICKET_DE_ANTES),
    ).fetchone()
    con.execute(
        "DELETE FROM inventario WHERE usuario_id = ? AND guild_id = ? AND objeto = ?",
        (usuario_id, guild_id, _TICKET_DE_ANTES),
    )
    return max(fila["cantidad"], 0) if fila else 0


def _cerrar_las_casas(
    con, usuario_id: str, guild_id: str
) -> tuple[list[str], int]:
    """Borra sus casas y les vacía `casa_id` a sus gachamones. Dice cuáles se
    devuelven, en orden de compra, y cuánto suman.

    Una clave que no está en la tabla de precios no paga: deja un aviso, sin
    decir de quién era, y no tumba el cambio.
    """
    claves: list[str] = []
    monedas = 0
    for casa in con.execute(
        "SELECT id, casa FROM casas_propias "
        "WHERE usuario_id = ? AND guild_id = ? ORDER BY id",
        (usuario_id, guild_id),
    ).fetchall():
        precio = PRECIO_DE_LAS_CASAS_DE_ANTES.get(casa["casa"])
        if precio is None:
            logger.warning(
                "El día del cambio, una casa de clave desconocida (%r) no se devolvió",
                casa["casa"],
            )
        else:
            claves.append(casa["casa"])
            monedas += precio
            if casa["casa"] in _CASAS_QUE_SE_MEJORAN:
                monedas += MEJORA_DE_LAS_CASAS_DE_ANTES
        con.execute(
            "UPDATE criaturas SET casa_id = NULL "
            "WHERE usuario_id = ? AND guild_id = ? AND casa_id = ?",
            (usuario_id, guild_id, casa["id"]),
        )
    con.execute(
        "DELETE FROM casas_propias WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    )
    return claves, monedas


def _departamento_del_alcalde(
    con, usuario_id: str, guild_id: str, vivos: int, ahora: datetime
) -> tuple[int, int, int, int]:
    """Le crea el departamento con una cama puesta por gachamon vivo más la suya
    y su puerta.

    Del primer tamaño donde caben (`dep.tamano_para`), con las camas y la
    puerta donde dice `dep.acomodo_del_alcalde`: la puerta, en un tramo con la
    entrada libre; si con las camas puestas no queda ninguno, la cama que la
    tapa se corre a un sitio de cama que sobre. Sólo en un 8 × 8 lleno de camas
    queda tapada, y con el tope de 25 de antes no puede pasar. A quien no le
    queda ningún vivo, además, otra guardada: lo mismo que a quien empieza. Si
    no cupieran todas —más de 32 en 8 × 8; tampoco puede pasar—, las que sobran
    quedan guardadas.

    Nadie tiene departamento todavía, así que nace con un `INSERT` a secas: si
    alguien ya tuviera uno, el cambio entero se deshace en vez de sumarle camas.

    Dice el ancho, el fondo, cuántas camas dejó puestas y cuántas regaló en
    total.
    """
    camas = vivos + 1
    ancho, fondo = dep.tamano_para(camas)
    sitios, (puerta_x, puerta_y) = dep.acomodo_del_alcalde(
        ancho, fondo, min(camas, _CAMAS_QUE_CABEN))
    con.execute(
        "INSERT INTO departamentos (usuario_id, guild_id, ancho, fondo, creado_en) "
        "VALUES (?, ?, ?, ?, ?)",
        (usuario_id, guild_id, ancho, fondo, ahora.isoformat()),
    )
    for x, y, giro in sitios:
        db.anadir_mueble_en(con, usuario_id, guild_id, _CAMA_SENCILLA, x, y, giro)
    guardadas = camas - len(sitios) + (0 if vivos else 1)
    for _ in range(guardadas):
        db.anadir_mueble_en(con, usuario_id, guild_id, _CAMA_SENCILLA)
    # La puerta, la última, en el tramo que buscó el alcalde con las camas ya puestas.
    db.anadir_mueble_en(con, usuario_id, guild_id, dep.PUERTA, puerta_x, puerta_y)
    return ancho, fondo, len(sitios), len(sitios) + guardadas


def _guardar_los_muebles_de_antes(con, usuario_id: str, guild_id: str) -> int:
    """Cada mueble de antes pasa a guardados con su misma clave, y su fila vieja
    se borra. Dice cuántos eran."""
    viejos = con.execute(
        "SELECT mueble FROM mobiliario WHERE usuario_id = ? AND guild_id = ? "
        "ORDER BY mueble",
        (usuario_id, guild_id),
    ).fetchall()
    for viejo in viejos:
        db.anadir_mueble_en(con, usuario_id, guild_id, viejo["mueble"])
    con.execute(
        "DELETE FROM mobiliario WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    )
    return len(viejos)


def poner_al_dia(ahora: datetime) -> ResumenDevolucion:
    """El arranque: prepara la base, hace el día del cambio y la devolución de
    lo retirado.

    Lo llaman el bot y la web, y nadie más prepara la base fuera de las pruebas.
    El día del cambio sólo hace algo la primera vez; si toca a alguien, lo deja
    en el registro con sus tres cifras y sin decir a quién.
    """
    db.inicializar(ahora)
    cambio = el_dia_del_cambio(ahora)
    if cambio.personas:
        # Aviso y no info: la web no configura el registro, y ahí un info se pierde.
        logger.warning(
            "El día del cambio: %d personas, %d camas regaladas, %d monedas devueltas",
            cambio.personas, cambio.camas, cambio.monedas,
        )
    return devolver_cosmeticos_retirados(ahora)


# --- Los logros y lo que pagan ----------------------------------------------

@dataclass(frozen=True)
class ReciboLogros:
    """Lo que acaba de desbloquear un gachamon y lo que le ha valido."""

    nuevos: tuple[lgr.Logro, ...] = ()
    asciigems: int = 0
    saldo: int = 0          # lo que queda en reserva después de cobrar


def pagar_logros(criatura: sim.Criatura, ahora: datetime) -> ReciboLogros:
    """Desbloquea las quince del gachamon y le paga las gemas a su dueño.

    Las tres de la persona no pasan por aquí: van en `pagar_logros_de_persona`.

    Vive aquí y no en `db` porque toca el monedero, y la orquestación monetaria
    es de este módulo. Desbloquear y pagar van bajo un mismo `BEGIN IMMEDIATE`,
    y no por costumbre: un logro apuntado sin pagar **no se puede reintentar**,
    porque el segundo intento ya lo encuentra puesto y no devuelve nada.

    No lleva ledger propio en `operaciones_economia` como los asciicoins. Allí
    hace falta porque el mismo clic puede reprocesarse y hay que congelar lo que
    pagó; aquí la clave primaria de `logros` ya dice, por sí sola, que cada uno
    se cobró una vez. Tampoco hay tope diario: todos son de una sola vez por
    construcción, así que no hay nada que machacar.

    Las gemas van al monedero de **la persona**, que es de quien son los
    monederos, aunque la medalla sea del gachamon: es lo que cierra el círculo
    con los cosméticos, que se compran para el que tengas activo.
    """
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        hechos = lgr.hechos_de(criatura, db._marcador(con, criatura.id), ahora)
        nuevos = tuple(
            logro for logro in lgr.cumplidos(hechos, lgr.GACHAMON)
            if db.anotar_logro_en(con, criatura.id, logro.clave, ahora)
        )
        return _cobrar_logros(
            con, criatura.usuario_id, criatura.guild_id, nuevos
        )


def pagar_logros_de_persona(
    usuario_id: str, guild_id: str, ahora: datetime
) -> ReciboLogros:
    """Lo mismo, con las tres medallas que son tuyas y no de ningún gachamon.

    Se separa de `pagar_logros` en vez de meterle un modo porque las dos miran
    cosas distintas: aquella necesita una criatura viva delante y ésta funciona
    aunque no tengas ninguna: estas tres son tuyas, no de un gachamon.
    """
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        return _pagar_logros_de_persona_en(con, usuario_id, guild_id, ahora)


def _pagar_logros_de_persona_en(
    con, usuario_id: str, guild_id: str, ahora: datetime
) -> ReciboLogros:
    """Lo mismo, dentro de la transacción que ya abrió quien llama.

    La abre `pagar_logros_de_persona` o el día del cambio, que paga con ella lo
    que cada quien tenía ganado y sin cobrar: si el cambio se deshace, el pago
    también. A quien no tiene monedero, `_cobrar_logros` le crea el de quien
    empieza; por eso el día del cambio le asegura el suyo antes de pagarle.
    """
    hechos = lgr.hechos_de_la_persona(
        db._marcador_de_persona(con, usuario_id, guild_id),
        db._especies_de(con, usuario_id, guild_id),
    )
    nuevos = tuple(
        logro for logro in lgr.cumplidos(hechos, lgr.PERSONA)
        if db.anotar_logro_de_persona_en(
            con, usuario_id, guild_id, logro.clave, ahora
        )
    )
    return _cobrar_logros(con, usuario_id, guild_id, nuevos)


def _cobrar_logros(
    con, usuario_id: str, guild_id: str, nuevos: tuple[lgr.Logro, ...]
) -> ReciboLogros:
    """Le paga a la persona lo que acaba de desbloquear, sea de quien sea.

    Compartido a propósito: las gemas van al mismo monedero se gane la medalla
    con un gachamon o por tu cuenta, y así el pago se escribe una vez.
    """
    if not nuevos:
        return ReciboLogros()

    gemas = sum(logro.gemas for logro in nuevos)
    _asegurar_monedero(con, usuario_id, guild_id)
    con.execute(
        "UPDATE monederos SET asciigems = asciigems + ? "
        "WHERE usuario_id = ? AND guild_id = ?",
        (gemas, usuario_id, guild_id),
    )
    return ReciboLogros(nuevos, gemas, _saldos_en(con, usuario_id, guild_id).asciigems)


def _contar_acreditadas(
    con, usuario_id: str, guild_id: str, fecha: str, tipo: str,
    hasta: int | None = None,
) -> int:
    if hasta is not None:
        return con.execute(
            "SELECT COUNT(*) FROM operaciones_economia "
            "WHERE usuario_id = ? AND guild_id = ? AND fecha_utc = ? "
            "AND tipo = ? AND resultado = 'acreditada' AND rowid <= ?",
            (usuario_id, guild_id, fecha, tipo, hasta),
        ).fetchone()[0]
    return con.execute(
        "SELECT COUNT(*) FROM operaciones_economia "
        "WHERE usuario_id = ? AND guild_id = ? AND fecha_utc = ? "
        "AND tipo = ? AND resultado = 'acreditada'",
        (usuario_id, guild_id, fecha, tipo),
    ).fetchone()[0]


def _ganado_hoy(con, usuario_id: str, guild_id: str, fecha: str) -> int:
    """Los asciicoins ya cobrados hoy **jugando**.

    Sólo `acreditada`: las compras son `comprada` y llevan delta negativo, así
    que gastar no te devuelve sitio en el bote. El bote mide lo **ganado**, no
    lo que tienes.

    Y **fuera los hallazgos de aventura**, que se cobran enteros y por su
    cuenta. Sin esta cláusula, encontrarse diez monedas por el camino le
    restaría diez a lo que se gane cuidando después — que es justo lo que se
    quería quitar. Su fila sigue en el ledger porque es lo que impide pagar dos
    veces el mismo viaje; lo que no hace es contar aquí.
    """
    return con.execute(
        "SELECT COALESCE(SUM(delta_asciicoins), 0) FROM operaciones_economia "
        "WHERE usuario_id = ? AND guild_id = ? AND fecha_utc = ? "
        "AND resultado = 'acreditada' AND tipo <> 'aventura'",
        (usuario_id, guild_id, fecha),
    ).fetchone()[0]


def _resolver_recompensa(
    con, usuario_id: str, guild_id: str, fecha: str,
    tipo: str, monto: int, limite: int | None,
) -> tuple[int, int, bool]:
    """Cuánto se cobra de verdad, contra el tope de la actividad y el bote.

    Son dos frenos y el que manda es el bote: 20 al día para todo. Los topes por
    actividad siguen ahí porque limitan otra cosa —cuántas veces cobras por lo
    mismo— y quitarlos cambiaría el comportamiento de quien hace trece cuidados.
    `limite=None` es para lo que no tiene tope propio, como los hallazgos.

    **Se cobra lo que quepa, no todo o nada**: con 3 libres y un premio de 6
    entran 3. Es lo que espera quien lee «hasta 20 al día», y la fila del ledger
    lo admite tal cual; sólo cuando no cabe nada se apunta `topada`.
    """
    usados = _contar_acreditadas(con, usuario_id, guild_id, fecha, tipo)
    libre = max(0, TOPE_DIARIO_ASCIICOINS - _ganado_hoy(con, usuario_id, guild_id, fecha))
    cabe = limite is None or usados < limite
    delta = min(monto, libre) if cabe else 0
    acreditada = delta > 0
    if delta:
        _asegurar_monedero(con, usuario_id, guild_id)
        con.execute(
            "UPDATE monederos SET asciicoins = asciicoins + ? "
            "WHERE usuario_id = ? AND guild_id = ?",
            (delta, usuario_id, guild_id),
        )
    return delta, usados + (1 if acreditada else 0), not acreditada


def _registrar_recompensa(
    con, evento_id: str, usuario_id: str, guild_id: str, fecha: str,
    tipo: str, monto: int, limite: int | None, solicitud: str,
) -> tuple[int, int, bool]:
    delta, usados, topada = _resolver_recompensa(
        con, usuario_id, guild_id, fecha, tipo, monto, limite
    )
    con.execute(
        "INSERT INTO operaciones_economia "
        "(evento_id, usuario_id, guild_id, tipo, fecha_utc, resultado, "
        "delta_asciicoins, solicitud) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            evento_id, usuario_id, guild_id, tipo, fecha,
            "topada" if topada else "acreditada", delta, solicitud,
        ),
    )
    return delta, usados, topada


@dataclass(frozen=True)
class ResultadoHallazgo:
    """Lo que te has encontrado por el camino.

    Sin `monedas_vistas` ni `topado`: desde que los hallazgos salieron del bote
    no hay diferencia entre lo que había en el suelo y lo que te llevas, así que
    tener dos números invitaba a preguntarse cuál era cuál.
    """

    monedas: int = 0
    gemas: int = 0
    replay: bool = False


def otorgar_hallazgo(
    evento_id: str, usuario_id: str, guild_id: str,
    monedas: int, gemas: int, ahora: datetime | None = None,
) -> ResultadoHallazgo:
    """Paga lo encontrado en una aventura, en una sola transacción.

    **Ni las monedas ni las gemas pasan por el bote diario**, y se cobran
    enteras. Un hallazgo no es un sueldo: es un golpe de suerte, y antes se
    cobraba dos veces mal — si habías llegado al tope no te daba nada, y si no,
    te comía sitio de lo que ibas a ganar cuidando. Es el mismo trato que las
    devoluciones, por el mismo motivo: no se gana jugando.

    Que no rompa la economía no es una impresión: sale al 4 % con 1–10 monedas,
    o sea 0,22 por aventura, y con la espera de 37 minutos entre viajes ni
    aventurando un día entero se llega a la mitad del bote.

    La fila del ledger **se queda**, y no por el bote: es la clave primaria
    sobre `(evento_id, usuario_id, guild_id, tipo)` lo que impide que reprocesar
    el mismo viaje vuelva a pagar **ni monedas ni gemas**, aunque éstas no
    tengan ledger propio — van dentro de la misma transacción.
    """
    if not monedas and not gemas:
        return ResultadoHallazgo()

    ahora = ahora or db.ahora_utc()
    fecha = _fecha_economica(ahora)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        ya_estaba = con.execute(
            "SELECT 1 FROM operaciones_economia WHERE evento_id = ? "
            "AND usuario_id = ? AND guild_id = ? AND tipo = 'aventura'",
            (evento_id, usuario_id, guild_id),
        ).fetchone()
        if ya_estaba is not None:
            return ResultadoHallazgo(replay=True)

        _asegurar_monedero(con, usuario_id, guild_id)
        if monedas:
            con.execute(
                "UPDATE monederos SET asciicoins = asciicoins + ? "
                "WHERE usuario_id = ? AND guild_id = ?",
                (monedas, usuario_id, guild_id),
            )
        if gemas:
            con.execute(
                "UPDATE monederos SET asciigems = asciigems + ? "
                "WHERE usuario_id = ? AND guild_id = ?",
                (gemas, usuario_id, guild_id),
            )
        # La fila se apunta igual, y siempre como acreditada: es el cerrojo
        # contra el doble pago, no una cuenta del bote. `_ganado_hoy` la ignora.
        con.execute(
            "INSERT INTO operaciones_economia "
            "(evento_id, usuario_id, guild_id, tipo, fecha_utc, resultado, "
            "delta_asciicoins, solicitud) "
            "VALUES (?, ?, ?, 'aventura', ?, 'acreditada', ?, ?)",
            (
                evento_id, usuario_id, guild_id, fecha, monedas,
                json.dumps({"monedas": monedas, "gemas": gemas}),
            ),
        )
        return ResultadoHallazgo(monedas=monedas, gemas=gemas)


def _envolver_cuidado(
    resultado: sim.ResultadoAccion, *, delta: int = 0,
    delta_evolucion: int = 0, ent_salud_ganada: int = 0,
    usados: int = 0, evolucion_usadas: int = 0,
    topada: bool = False, sin_efecto: bool = False,
) -> ResultadoCuidado:
    return ResultadoCuidado(
        criatura=resultado.criatura,
        mensaje=resultado.mensaje,
        ok=resultado.ok,
        espera=resultado.espera,
        rupturas=tuple(resultado.rupturas),
        marca=resultado.marca,
        subidas=tuple(resultado.subidas),
        etapa_anterior=resultado.etapa_anterior,
        delta_asciicoins=delta + delta_evolucion,
        delta_evolucion=delta_evolucion,
        ent_salud_ganada=ent_salud_ganada,
        usados=usados,
        evolucion_usadas=evolucion_usadas,
        topada=topada,
        sin_efecto=sin_efecto,
    )


def ejecutar_cuidado(
    evento_id: str, usuario_id: str, guild_id: str,
    accion: str, ahora: datetime, criatura_id: int | None = None,
) -> ResultadoCuidado | None:
    """Aplica cuidado, cooldown y premios bajo un único ``BEGIN IMMEDIATE``.

    Sin `criatura_id`, al activo. Con él, a ese gachamon si es de esa persona,
    de ese servidor y está vivo; si no, `None` sin escribir nada. El id va en
    la `solicitud` del ledger, así que el mismo evento no sirve para cuidar a
    otro gachamon.
    """
    solicitud = accion if criatura_id is None else f"{accion}:{criatura_id}"
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        operacion = con.execute(
            "SELECT * FROM operaciones_economia WHERE evento_id = ? "
            "AND usuario_id = ? AND guild_id = ? AND tipo = 'cuidado'",
            (evento_id, usuario_id, guild_id),
        ).fetchone()
        if operacion is not None:
            if operacion["solicitud"] != solicitud:
                raise RuntimeError("el evento de cuidado pertenece a otra acción")
            criatura = db.criatura_elegida_en(con, usuario_id, guild_id, criatura_id)
            if criatura is None:
                return None
            evolucion = con.execute(
                "SELECT resultado, delta_asciicoins FROM operaciones_economia "
                "WHERE evento_id = ? AND usuario_id = ? AND guild_id = ? "
                "AND tipo = 'evolucion'",
                (evento_id, usuario_id, guild_id),
            ).fetchone()
            delta_evolucion = evolucion["delta_asciicoins"] if evolucion else 0
            evolucion_usadas = (
                _contar_acreditadas(
                    con, usuario_id, guild_id, operacion["fecha_utc"], "evolucion"
                ) if evolucion else 0
            )
            return ResultadoCuidado(
                criatura=criatura,
                mensaje="",
                delta_asciicoins=operacion["delta_asciicoins"] + delta_evolucion,
                delta_evolucion=delta_evolucion,
                usados=_contar_acreditadas(
                    con, usuario_id, guild_id, operacion["fecha_utc"], "cuidado"
                ),
                evolucion_usadas=evolucion_usadas,
                replay=True,
                topada=operacion["resultado"] == "topada",
            )

        criatura = db.criatura_elegida_en(con, usuario_id, guild_id, criatura_id)
        if criatura is None:
            return None
        criatura = db._avanzar_en(con, criatura, ahora)
        return _cuidar_en(
            con, evento_id, usuario_id, guild_id, criatura, accion, ahora, solicitud
        )


def _cuidar_en(
    con, evento_id: str, usuario_id: str, guild_id: str,
    criatura: sim.Criatura, accion: str, ahora: datetime, solicitud: str,
) -> ResultadoCuidado:
    """El cuidado en sí, de la espera al recibo, dentro de la transacción de quien llama.

    `criatura` llega **ya puesta al día** hasta `ahora`. Mira la espera, aplica
    el cuidado, lo guarda, le pone su enfriamiento, lo apunta en su marcador y
    paga el cuidado y, si evolucionó, la evolución, con `solicitud` en las filas
    del ledger.
    """
    espera = db.espera_en(con, criatura.id, accion, ahora)
    if espera and not sim.puede_saltarse_espera(criatura, accion):
        db._guardar(con, criatura)
        return ResultadoCuidado(criatura, "", ok=False, espera=espera)

    resultado = sim.aplicar_accion(criatura, accion, ahora)
    db._guardar(con, resultado.criatura)
    sin_efecto = (
        resultado.ok
        and accion != sim.ACTUALIZAR
        and resultado.criatura == criatura
    )
    if not resultado.ok or accion == sim.ACTUALIZAR or sin_efecto:
        return _envolver_cuidado(resultado, sin_efecto=sin_efecto)

    duracion = sim.COOLDOWNS.get(accion, timedelta(0))
    if duracion:
        db.poner_cooldown_en(con, criatura.id, accion, ahora + duracion)
    # Un cuidado de los que cuentan: los tres returns de arriba ya han
    # descartado el fallo, el `/actualizar` y el que no cambió nada.
    db.apuntar_en(con, criatura.id, lgr.CUIDADOS)
    fecha = _fecha_economica(ahora)
    delta, usados, topada = _registrar_recompensa(
        con, evento_id, usuario_id, guild_id, fecha,
        "cuidado", PREMIO_CUIDADO, TOPE_CUIDADOS, solicitud,
    )
    delta_evolucion = 0
    evolucion_usadas = 0
    if resultado.evoluciono:
        delta_evolucion, evolucion_usadas, _ = _registrar_recompensa(
            con, evento_id, usuario_id, guild_id, fecha,
            "evolucion", PREMIO_EVOLUCION, TOPE_EVOLUCIONES, solicitud,
        )
    return _envolver_cuidado(
        resultado,
        delta=delta,
        delta_evolucion=delta_evolucion,
        ent_salud_ganada=resultado.criatura.ent_salud - criatura.ent_salud,
        usados=usados,
        evolucion_usadas=evolucion_usadas,
        topada=topada,
    )


def cuidar_a_todos(
    evento_id: str, usuario_id: str, guild_id: str, accion: str, ahora: datetime,
) -> ResultadoATodos:
    """Le hace el mismo cuidado a cada gachamon vivo que puede recibirlo.

    Todo bajo un solo ``BEGIN IMMEDIATE``: o les toca a todos los que tocaba,
    o a ninguno. A cada vivo, en el orden del plantel, se le pone al día; se
    salta, **sin escribirle nada**, al que no le serviría y al que le corre la
    espera sin poder saltársela. A los demás, el cuidado de siempre
    (`_cuidar_en`) con su propio evento, así que cada uno paga como cuidarlo de
    a uno, dentro del mismo tope diario.

    Si le tocó a alguien queda anotado y repetir el evento devuelve lo de la
    primera vez sin cuidar ni pagar; si no le tocó a nadie no se anota, y
    repetirlo vuelve a decidir.
    """
    if accion not in sim.ACCIONES_DE_CUIDADO:
        raise ValueError(f"«a todos» sólo con un cuidado, no con {accion!r}")
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        hecha = _ya_hecha(con, evento_id, usuario_id, guild_id, "a_todos", accion)
        if hecha is not None:
            return ResultadoATodos(
                accion,
                tocados=tuple(hecha["tocados"]),
                de_cuantos=hecha["de_cuantos"],
                delta_asciicoins=hecha["monedas"],
                replay=True,
            )

        vivos = db.plantel_en(con, usuario_id, guild_id)
        cuidados = []
        for criatura in vivos:
            criatura = db._avanzar_en(con, criatura, ahora)
            if not sim.le_serviria(criatura, accion):
                continue
            espera = db.espera_en(con, criatura.id, accion, ahora)
            if espera and not sim.puede_saltarse_espera(criatura, accion):
                continue
            cuidado = _cuidar_en(
                con, f"{evento_id}:{criatura.id}", usuario_id, guild_id,
                criatura, accion, ahora, accion,
            )
            # Tocado es quien recibió el cuidado de verdad. Los dos filtros de
            # arriba ya descartan lo que `_cuidar_en` rechazaría.
            if cuidado.ok and not cuidado.sin_efecto:
                cuidados.append(cuidado)

        tocados = tuple(cuidado.criatura.id for cuidado in cuidados)
        monedas = sum(cuidado.delta_asciicoins for cuidado in cuidados)
        if tocados:
            _anotar(
                con, evento_id, usuario_id, guild_id, "a_todos", accion,
                {"tocados": list(tocados), "de_cuantos": len(vivos),
                 "monedas": monedas},
                ahora,
            )
        return ResultadoATodos(
            accion,
            tocados=tocados,
            de_cuantos=len(vivos),
            delta_asciicoins=monedas,
            cuidados=tuple(cuidados),
        )


@dataclass(frozen=True)
class ResultadoConversacion:
    """Qué sacó la criatura de una conversación, si es que sacó algo."""

    ok: bool = False
    criatura: sim.Criatura | None = None
    # Los dos, y no uno: el entrenamiento sube siempre de uno en uno, pero
    # `stat_final` le saca la raíz, así que la estadística **casi nunca se mueve
    # en el mismo momento**. Decir «+1 de ingenio» cada vez sería mentir en tres
    # de cada cuatro conversaciones.
    entrenamiento_ganado: int = 0
    ingenio_ganado: int = 0
    animo_ganado: int = 0


def puede_aprender_hablando(criatura_id: int, ahora: datetime) -> bool:
    """Si a esta criatura le toca ya poder aprender algo de una conversación.

    Es una lectura suelta y barata, y existe para **no gastar una llamada a la
    IA cuando no hay nada que ganar**: juzgar cada mensaje serían veinte
    llamadas extra por hora y persona; juzgar sólo cuando el enfriamiento está
    listo es una cada 97 minutos como mucho.

    Que aquí diga que sí no basta: entre esta consulta y el premio pasa una
    llamada de red entera, así que `aprender_hablando` lo vuelve a comprobar
    dentro de su transacción.
    """
    with db.conectar() as con:
        return not db.espera_en(con, criatura_id, sim.CONVERSAR, ahora)


def aprender_hablando(
    usuario_id: str, guild_id: str, ahora: datetime | None = None
) -> ResultadoConversacion:
    """Le da a la activa lo que deja una buena conversación, si le toca.

    Quien llama ya ha decidido que la conversación valía la pena; aquí sólo se
    comprueba que el enfriamiento siga libre y se aplica. La comprobación se
    repite **dentro** de la transacción porque la de `puede_aprender_hablando`
    se hizo antes de hablar con la IA, y dos mensajes seguidos pueden llegar a
    este punto con el mismo permiso en la mano.
    """
    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        criatura = db.criatura_activa_en(con, usuario_id, guild_id)
        if criatura is None:
            return ResultadoConversacion()
        # Se avanza antes de premiar, igual que en `cuidar`: el ánimo que gana
        # se suma al que tiene ahora, no al de la última vez que se guardó.
        criatura = db._avanzar_en(con, criatura, ahora)
        if db.espera_en(con, criatura.id, sim.CONVERSAR, ahora):
            db._guardar(con, criatura)
            return ResultadoConversacion(criatura=criatura)

        resultado = sim.aplicar_conversacion(criatura)
        db._guardar(con, resultado.criatura)
        db.poner_cooldown_en(
            con, criatura.id, sim.CONVERSAR,
            ahora + sim.COOLDOWNS[sim.CONVERSAR],
        )
        return ResultadoConversacion(
            ok=True,
            criatura=resultado.criatura,
            entrenamiento_ganado=(
                resultado.criatura.ent_ingenio - criatura.ent_ingenio
            ),
            ingenio_ganado=resultado.criatura.ingenio - criatura.ingenio,
            animo_ganado=round(resultado.criatura.animo - criatura.animo),
        )


# Qué cuenta cada victoria. Vive aquí y no en `competir.py` ni en `logros.py`
# porque es el único sitio que habla los dos vocabularios: la modalidad y la
# clave del marcador.
MARCADOR_DE_MODALIDAD = {
    comp.CARRERA: lgr.CARRERAS,
    comp.SUMO: lgr.SUMOS,
    comp.TOTEM: lgr.TOTEMS,
    comp.LABERINTO: lgr.LABERINTOS,
}


def _replay_competencia(
    con, evento_id: str, usuarios: tuple[str, ...],
    guild_id: str, solicitud: str,
) -> ResultadoCompetencia | None:
    filas = con.execute(
        "SELECT rowid AS orden_ledger, * FROM operaciones_economia "
        "WHERE evento_id = ? AND guild_id = ? AND tipo = 'competencia'",
        (evento_id, guild_id),
    ).fetchall()
    if not filas:
        return None
    por_usuario = {fila["usuario_id"]: fila for fila in filas}
    if set(por_usuario) != set(usuarios):
        raise RuntimeError("el evento de competencia está incompleto")
    recibos = []
    for usuario_id in usuarios:
        fila = por_usuario[usuario_id]
        if fila["solicitud"] != solicitud:
            raise RuntimeError("el evento de competencia pertenece a otro encuentro")
        evolucion = con.execute(
            "SELECT rowid AS orden_ledger, fecha_utc, resultado, "
            "delta_asciicoins FROM operaciones_economia "
            "WHERE evento_id = ? AND usuario_id = ? AND guild_id = ? "
            "AND tipo = 'evolucion'",
            (evento_id, usuario_id, guild_id),
        ).fetchone()
        delta_evolucion = evolucion["delta_asciicoins"] if evolucion else 0
        recibos.append(ReciboCompetencia(
            usuario_id=usuario_id,
            delta_asciicoins=fila["delta_asciicoins"] + delta_evolucion,
            delta_competencia=fila["delta_asciicoins"],
            delta_evolucion=delta_evolucion,
            usados=_contar_acreditadas(
                con, usuario_id, guild_id, fila["fecha_utc"], "competencia",
                fila["orden_ledger"],
            ),
            evolucion_usadas=(
                _contar_acreditadas(
                    con, usuario_id, guild_id, evolucion["fecha_utc"], "evolucion",
                    evolucion["orden_ledger"],
                ) if evolucion else 0
            ),
            topada=fila["resultado"] == "topada",
            evoluciono=evolucion is not None,
            evolucion_topada=(
                evolucion is not None and evolucion["resultado"] == "topada"
            ),
        ))
    return ResultadoCompetencia(None, recibos=tuple(recibos), replay=True)


def ejecutar_competencia(
    evento_id: str,
    usuario_ids: list[str] | tuple[str, ...],
    guild_id: str,
    tipo: str,
    ahora: datetime,
    rng: random.Random | None = None,
) -> ResultadoCompetencia:
    """Resuelve y confirma el encuentro completo antes de cualquier publicación."""
    usuarios = tuple(usuario_ids)
    if len(set(usuarios)) != len(usuarios):
        raise ValueError("una persona no puede competir dos veces en el mismo encuentro")
    solicitud = json.dumps(
        {"participantes": usuarios, "tipo": tipo},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    rng = rng or random.Random()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        replay = _replay_competencia(
            con, evento_id, usuarios, guild_id, solicitud
        )
        if replay is not None:
            return replay

        antes_lista = []
        for usuario_id in usuarios:
            criatura = db.criatura_activa_en(con, usuario_id, guild_id)
            if criatura is None:
                return ResultadoCompetencia(
                    None,
                    problema="Falta un gachamon activo para competir.",
                    problema_usuario_id=usuario_id,
                )
            antes_lista.append(criatura)
        antes = tuple(antes_lista)
        criaturas = tuple(
            db._avanzar_en(con, criatura, ahora) for criatura in antes
        )
        for criatura in criaturas:
            db._guardar(con, criatura)
        for usuario_id, criatura in zip(usuarios, criaturas):
            if criatura.hambre < sim.HAMBRE_MINIMA_COMPETIR:
                return ResultadoCompetencia(
                    None, antes=antes, despues=criaturas,
                    problema="Un gachamon tiene demasiada hambre para competir.",
                    problema_usuario_id=usuario_id,
                    problema_criatura=criatura,
                )
            espera = db.espera_en(con, criatura.id, sim.COMPETIR, ahora)
            if espera:
                return ResultadoCompetencia(
                    None, antes=antes, despues=criaturas,
                    problema="Un gachamon todavía se está recuperando.",
                    problema_usuario_id=usuario_id,
                    problema_criatura=criatura,
                    espera=espera,
                )

        stats = comp.STATS[tipo]
        encuentro = comp.enfrentar(
            [
                comp.competidor_de(
                    criatura,
                    **{
                        f"bonus_{stat}": db.efecto_activo_en(
                            con, criatura.id, stat, ahora
                        )
                        for stat in sim.ESTADISTICAS
                    },
                )
                for criatura in criaturas
            ],
            tipo,
            rng,
        )
        ganador = encuentro.orden[0]
        aplicadas = tuple(
            sim.aplicar_competencia(
                criatura,
                dorsal == ganador,
                stats,
                rng,
                comp.margen_de(encuentro, dorsal),
            )
            for dorsal, criatura in enumerate(criaturas)
        )
        despues = tuple(criatura for criatura, _ in aplicadas)
        rupturas = tuple(tuple(lista) for _, lista in aplicadas)
        subidas = tuple(
            tuple(ruptura.stat for ruptura in lista) for lista in rupturas
        )
        for criatura in despues:
            db._guardar(con, criatura)
            db.poner_cooldown_en(
                con, criatura.id, sim.COMPETIR,
                ahora + sim.COOLDOWNS[sim.COMPETIR],
            )

        # El marcador del ganador, aquí dentro y no después: si se cayera la
        # conexión entre ganar y apuntarlo quedaría una victoria que no cuenta
        # para nada, y nadie tendría forma de saberlo. El replay de más arriba
        # ya ha vuelto antes de llegar aquí, así que reprocesar el mismo evento
        # no cuenta dos veces.
        campeon = despues[ganador]
        db.apuntar_en(con, campeon.id, MARCADOR_DE_MODALIDAD[tipo])
        if encuentro.es_torneo:
            db.apuntar_en(con, campeon.id, lgr.TORNEOS)

        fecha = _fecha_economica(ahora)
        recibos = []
        for dorsal, (anterior, nueva) in enumerate(zip(criaturas, despues)):
            delta_comp, usados, topada = _registrar_recompensa(
                con, evento_id, nueva.usuario_id, guild_id, fecha,
                "competencia",
                PREMIO_GANADOR if dorsal == ganador else PREMIO_COMPETENCIA,
                TOPE_COMPETENCIAS,
                solicitud,
            )
            evoluciono = anterior.etapa != nueva.etapa
            delta_evolucion = 0
            evolucion_usadas = 0
            evolucion_topada = False
            if evoluciono:
                delta_evolucion, evolucion_usadas, evolucion_topada = (
                    _registrar_recompensa(
                        con, evento_id, nueva.usuario_id, guild_id, fecha,
                        "evolucion", PREMIO_EVOLUCION,
                        TOPE_EVOLUCIONES, solicitud,
                    )
                )
            recibos.append(ReciboCompetencia(
                usuario_id=nueva.usuario_id,
                delta_asciicoins=delta_comp + delta_evolucion,
                delta_competencia=delta_comp,
                delta_evolucion=delta_evolucion,
                usados=usados,
                evolucion_usadas=evolucion_usadas,
                topada=topada,
                evoluciono=evoluciono,
                evolucion_topada=evolucion_topada,
            ))
        return ResultadoCompetencia(
            encuentro=encuentro,
            antes=antes,
            despues=despues,
            rupturas=rupturas,
            subidas=subidas,
            recibos=tuple(recibos),
        )


# --- Las compras que no se cobran dos veces -----------------------------------
#
# La web manda un evento con cada compra y, si no le llega la respuesta, repite
# la petición con ese mismo evento. Discord no manda ninguno, y sin evento estas
# dos no hacen nada: todo sigue como antes.

def _ya_hecha(
    con, evento_id: str | None, usuario_id: str, guild_id: str, accion: str,
    solicitud: str,
) -> dict | None:
    """Lo que salió la primera vez si ese evento ya se hizo; `None` si no.

    Va justo detrás del `BEGIN IMMEDIATE` y antes de cualquier otra lectura que
    pueda rechazar: un replay contesta que salió bien aunque el estado de ahora
    ya no lo permita —la corona ya en el ropero, el departamento ya ampliado, el
    objeto ya gastado—. Un evento usado para pedir otra cosa es un error de
    quien llama, como en `comprar`.
    """
    if evento_id is None:
        return None
    hecha = db.accion_hecha_en(con, evento_id, usuario_id, guild_id, accion)
    if hecha is None:
        return None
    pedida, resultado = hecha
    if pedida != solicitud:
        raise RuntimeError(f"el evento de {accion} pertenece a otra solicitud")
    return resultado


def _anotar(
    con, evento_id: str | None, usuario_id: str, guild_id: str, accion: str,
    solicitud: str, resultado: dict, ahora: datetime,
) -> None:
    """Apunta lo que salió bien, en la misma transacción que lo hizo.

    Sólo se llama al acabar bien: un rechazo no se anota y repetirlo vuelve a
    decidir, porque entretanto pueden haber llegado las monedas.
    """
    if evento_id is not None:
        db.anotar_accion_en(
            con, evento_id, usuario_id, guild_id, accion, solicitud, resultado,
            ahora,
        )


@dataclass(frozen=True)
class ResultadoCosmetico:
    """Cómo salió comprar, poner o quitar un cosmético."""

    ok: bool = False
    criatura: sim.Criatura | None = None
    saldo: int = 0                  # asciigems que quedan
    problema: str | None = None
    # El que llevaba de ese tipo y se ha quitado para dejar sitio. **No se
    # pierde**: sigue en el ropero, que es de la persona.
    sustituido: cos.Cosmetico | None = None
    # Por qué no se pudo, como clave; None si salió bien o si el rechazo aún no
    # tiene una (equipar y quitar).
    motivo: str | None = None
    # En `lo_lleva_otro`: el nombre visible del gachamon que lleva la pieza.
    lo_lleva: str | None = None
    replay: bool = False            # la compra ya estaba hecha con ese evento


def _vestir_en(
    con, criatura: sim.Criatura, tipo: str, clave: str | None
) -> tuple[sim.Criatura, cos.Cosmetico | None]:
    """Le cambia una pieza y devuelve cómo queda y qué llevaba antes."""
    llevaba = cos.buscar(getattr(criatura, tipo))
    vestido = replace(criatura, **{tipo: clave})
    db._guardar(con, vestido)
    return vestido, llevaba


def comprar_cosmetico(
    usuario_id: str, guild_id: str, cosmetico: cos.Cosmetico,
    evento_id: str | None = None,
) -> ResultadoCosmetico:
    """Cobra las gemas, lo mete en tu ropero y se lo pone al activo.

    Como las compras de la tienda, la condición del cobro viaja **dentro** del
    UPDATE: así dos clics a la vez no pueden dejar el saldo en negativo pagando
    dos veces la última gema.

    No lleva fila en `operaciones_economia` porque allí sólo caben asciicoins
    —lo dice su CHECK—, pero el doble clic sí hace falta pararlo: dos compras del
    mismo sombrero cobrarían 120 gemas y dejarían una corona. Lo para el ropero:
    si ya lo tienes, ni se cobra ni se toca nada. Mirar antes de cobrar es seguro
    porque el `BEGIN IMMEDIATE` pone en fila a los que escriben, así que el
    segundo clic ya lo encuentra dentro.

    Que además se lo ponga es a propósito, y no un efecto secundario: es lo que
    espera quien acaba de gastarse sesenta gemas en una corona. Lo que llevara de
    ese tipo se le quita pero **no se pierde**, que es la diferencia con antes.

    Sin gachamon activo se puede comprar igual: va al ropero y se equipa cuando
    haya a quién.

    Con `evento_id` (la web), repetir la petición con el mismo evento contesta
    que salió bien sin cobrar otra vez, en vez de «ya lo tienes».
    """
    if cos.CATALOGO.get(cosmetico.clave) != cosmetico:
        raise ValueError("el cosmético no coincide con el catálogo actual")

    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        hecha = _ya_hecha(
            con, evento_id, usuario_id, guild_id, "cosmetico", cosmetico.clave
        )
        if hecha is not None:
            return ResultadoCosmetico(
                ok=True, replay=True,
                criatura=db.criatura_activa_en(con, usuario_id, guild_id),
                saldo=_saldos_en(con, usuario_id, guild_id).asciigems,
                sustituido=cos.buscar(hecha["sustituido"]),
            )

        criatura = db.criatura_activa_en(con, usuario_id, guild_id)
        _asegurar_monedero(con, usuario_id, guild_id)

        if cosmetico.clave in db._ropero(con, usuario_id, guild_id):
            return ResultadoCosmetico(
                criatura=criatura,
                saldo=_saldos_en(con, usuario_id, guild_id).asciigems,
                problema=(
                    f"Ya tienes **{cosmetico.nombre}** en tu ropero. "
                    "Póntelo desde 🎨 Personalizar."
                ),
                motivo="ya_lo_tienes",
            )

        pagado = con.execute(
            "UPDATE monederos SET asciigems = asciigems - ? "
            "WHERE usuario_id = ? AND guild_id = ? AND asciigems >= ?",
            (cosmetico.precio, usuario_id, guild_id, cosmetico.precio),
        ).rowcount > 0
        saldo = _saldos_en(con, usuario_id, guild_id).asciigems
        if not pagado:
            falta = cosmetico.precio - saldo
            return ResultadoCosmetico(
                criatura=criatura, saldo=saldo,
                problema=(
                    f"Te faltan {falta} {obj.nombre_de_gemas(falta)}. "
                    "Se ganan con los logros: mira `/logros`."
                ),
                motivo="faltan_gemas",
            )

        db.guardar_en_el_ropero_en(con, usuario_id, guild_id, cosmetico.clave)
        vestido, sustituido = criatura, None
        if criatura is not None:
            vestido, sustituido = _vestir_en(
                con, criatura, cosmetico.tipo, cosmetico.clave
            )
        _anotar(
            con, evento_id, usuario_id, guild_id, "cosmetico", cosmetico.clave,
            {"sustituido": sustituido.clave if sustituido else None},
            db.ahora_utc(),
        )
        return ResultadoCosmetico(
            ok=True, criatura=vestido, saldo=saldo, sustituido=sustituido
        )


@dataclass(frozen=True)
class ResultadoCambio:
    """Cómo salió cambiar de gachamon activo."""

    ok: bool = False
    motivo: str | None = None          # ya_es_el_activo o no_esta
    criatura: sim.Criatura | None = None   # el activo después: con el que sales
    saliente: sim.Criatura | None = None   # el que lo era y se queda en casa


def cambiar_de_activo(
    usuario_id: str, guild_id: str, criatura_id: int, ahora: datetime
) -> ResultadoCambio:
    """Sales con ese gachamon tuyo; el que era el activo se queda en casa.

    Sólo cambia quién es el activo. A todos les pasa el tiempo, salgan contigo
    o no, así que no se le guarda ni se le borra el paso del tiempo a ninguno.
    Con `ok`, `criatura` y `saliente` vuelven releídas tras el cambio y
    avanzadas hasta `ahora`, para enseñarlas como están; en la base se quedan
    como estaban.
    """
    # Por si no le queda ninguna activa viva (la tenía muerta de antes): sale
    # el relevo, como en `nacer.bautizar`. Entonces el relevo es «la que
    # estaba».
    db.activa_al_dia(usuario_id, guild_id, ahora)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        elegida = db.criatura_en(con, criatura_id)
        activa = db.criatura_activa_en(con, usuario_id, guild_id)
        if activa is not None and activa.id == criatura_id:
            return ResultadoCambio(motivo="ya_es_el_activo", criatura=activa)
        if (
            elegida is None
            or elegida.usuario_id != usuario_id
            or elegida.guild_id != guild_id
            or not elegida.viva
        ):
            return ResultadoCambio(motivo="no_esta", criatura=activa)

        db._activar_en(con, criatura_id)
        # Releídas tras el cambio, con la marca nueva, y al día sin guardarlo.
        nueva = db.criatura_en(con, criatura_id)
        assert nueva is not None
        saliente = None if activa is None else db.criatura_en(con, activa.id)
        return ResultadoCambio(
            ok=True,
            criatura=db._avanzar_en(con, nueva, ahora),
            saliente=(
                None if saliente is None else db._avanzar_en(con, saliente, ahora)
            ),
        )


@dataclass(frozen=True)
class ResultadoDepartamento:
    """Cómo salió comprar, poner o guardar un mueble, o ampliar el departamento.

    `departamento` es como queda; en un replay, el de ahora, igual que `saldo`.
    `saldo` y `coste` son monedas, y sólo los llenan comprar y ampliar.
    """

    ok: bool = False
    departamento: dep.Departamento | None = None
    motivo: str | None = None       # por qué no, como clave
    saldo: int = 0                  # las monedas que quedan
    coste: int = 0                  # lo que cuesta el mueble o ese lado
    mueble_id: int | None = None
    replay: bool = False            # ya estaba hecha con ese evento


def _cobrar_monedas_en(con, usuario_id: str, guild_id: str, cuanto: int) -> bool:
    """Cobra si alcanza. La condición va **dentro** del UPDATE: dos clics a la
    vez no pueden dejar el saldo en negativo."""
    _asegurar_monedero(con, usuario_id, guild_id)
    return con.execute(
        "UPDATE monederos SET asciicoins = asciicoins - ? "
        "WHERE usuario_id = ? AND guild_id = ? AND asciicoins >= ?",
        (cuanto, usuario_id, guild_id, cuanto),
    ).rowcount > 0


def comprar_mueble(
    usuario_id: str, guild_id: str, mueble: dep.Mueble,
    ahora: datetime | None = None, evento_id: str | None = None,
) -> ResultadoDepartamento:
    """Cobra el mueble y lo deja **guardado**: dónde ponerlo se decide después.

    Se puede comprar el mismo las veces que se quiera; cada uno es una pieza
    con su id. No lleva fila en `operaciones_economia`.

    Con `evento_id` (la web), repetir la petición devuelve el mismo mueble y lo
    que costó la primera vez, sin cobrar ni entregar otro.
    """
    if dep.MUEBLES.get(mueble.clave) != mueble:
        raise ValueError("el mueble no coincide con el catálogo actual")
    if mueble.puerta:
        raise ValueError("la puerta no se compra")

    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        hecha = _ya_hecha(con, evento_id, usuario_id, guild_id, "mueble", mueble.clave)
        if hecha is not None:
            # Un evento anotado antes de guardar lo cobrado lleva sólo el
            # mueble: ése vuelve con el precio de ahora.
            return ResultadoDepartamento(
                ok=True, replay=True, coste=hecha.get("coste", mueble.precio),
                mueble_id=hecha["mueble_id"],
                departamento=db._departamento_en(con, usuario_id, guild_id, ahora),
                saldo=_saldos_en(con, usuario_id, guild_id).asciicoins,
            )

        depto = db._departamento_en(con, usuario_id, guild_id, ahora)
        if not _cobrar_monedas_en(con, usuario_id, guild_id, mueble.precio):
            return ResultadoDepartamento(
                departamento=depto, motivo="faltan_monedas", coste=mueble.precio,
                saldo=_saldos_en(con, usuario_id, guild_id).asciicoins,
            )

        mueble_id = db.anadir_mueble_en(con, usuario_id, guild_id, mueble.clave)
        _anotar(
            con, evento_id, usuario_id, guild_id, "mueble", mueble.clave,
            {"mueble_id": mueble_id, "coste": mueble.precio}, ahora,
        )
        return ResultadoDepartamento(
            ok=True, coste=mueble.precio, mueble_id=mueble_id,
            departamento=db._departamento_leido(con, usuario_id, guild_id),
            saldo=_saldos_en(con, usuario_id, guild_id).asciicoins,
        )


def poner_mueble(
    usuario_id: str, guild_id: str, mueble_id: int, x: int, y: int, giro: int,
    ahora: datetime | None = None,
) -> ResultadoDepartamento:
    """Pone un mueble tuyo en (x, y) con ese giro. Mover y girar son esto mismo.

    Si no se puede, dice por qué con el motivo de `dep.problema_al_poner`.
    Ponerlo donde ya está no cambia nada. `x`, `y` y `giro` tienen que ser
    enteros, y `giro` de 0 a 3: otra cosa es un fallo de quien llama.
    """
    if not all(type(v) is int for v in (x, y, giro)) or not 0 <= giro <= 3:
        raise ValueError("el sitio o el giro no existen")

    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        depto = db._departamento_en(con, usuario_id, guild_id, ahora)
        motivo = dep.problema_al_poner(depto, mueble_id, x, y, giro)
        if motivo is not None:
            return ResultadoDepartamento(departamento=depto, motivo=motivo, mueble_id=mueble_id)

        pieza = depto.pieza(mueble_id)
        if (pieza.x, pieza.y, pieza.giro) != (x, y, giro):
            # Lo puesto fija el ritmo: el tiempo que ya pasó corre con el de antes.
            db.asentar_el_plantel_en(con, usuario_id, guild_id, ahora)
            db.poner_mueble_en(con, mueble_id, x, y, giro)
            depto = db._departamento_leido(con, usuario_id, guild_id)
        return ResultadoDepartamento(ok=True, departamento=depto, mueble_id=mueble_id)


def guardar_mueble(
    usuario_id: str, guild_id: str, mueble_id: int, ahora: datetime | None = None,
) -> ResultadoDepartamento:
    """Guarda un mueble tuyo. Guardar nunca lo destruye, y guardar lo ya
    guardado sale bien sin cambiar nada.

    La cama que hace falta —la tuya y una por cada gachamon vivo— no se guarda,
    ni la puerta (`motivo="no_se_guarda"`).
    """
    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        depto = db._departamento_en(con, usuario_id, guild_id, ahora)
        # `dep.puede_guardarse` deja pasar una pieza que no existe: hay que
        # mirar antes que sea de esta persona.
        pieza = depto.pieza(mueble_id)
        if pieza is None:
            return ResultadoDepartamento(
                departamento=depto, motivo=dep.NO_ES_TUYO, mueble_id=mueble_id,
            )
        if pieza.clave in dep.MUEBLES and dep.MUEBLES[pieza.clave].puerta:
            return ResultadoDepartamento(
                departamento=depto, motivo="no_se_guarda", mueble_id=mueble_id,
            )
        if not pieza.puesta:
            return ResultadoDepartamento(ok=True, departamento=depto, mueble_id=mueble_id)

        vivos = len(db.plantel_en(con, usuario_id, guild_id))
        if not dep.puede_guardarse(depto, mueble_id, vivos):
            return ResultadoDepartamento(
                departamento=depto, motivo="hace_falta", mueble_id=mueble_id,
            )

        db.asentar_el_plantel_en(con, usuario_id, guild_id, ahora)
        db.guardar_mueble_en(con, mueble_id)
        return ResultadoDepartamento(
            ok=True, mueble_id=mueble_id,
            departamento=db._departamento_leido(con, usuario_id, guild_id),
        )


def ampliar_departamento(
    usuario_id: str, guild_id: str, eje: str,
    ahora: datetime | None = None, evento_id: str | None = None,
) -> ResultadoDepartamento:
    """Le suma una columna (`dep.ANCHO`) o una fila (`dep.FONDO`), a 15 monedas
    por casilla nueva. Lo puesto no se mueve.

    Con `evento_id` (la web), repetir la petición no cobra ni amplía otra vez:
    devuelve lo que costó la primera, con el departamento y el saldo de ahora.
    """
    if eje not in (dep.ANCHO, dep.FONDO):
        raise ValueError(f"un departamento no tiene el lado «{eje}»")

    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        hecha = _ya_hecha(con, evento_id, usuario_id, guild_id, "ampliar", eje)
        if hecha is not None:
            return ResultadoDepartamento(
                ok=True, replay=True, coste=hecha["coste"],
                departamento=db._departamento_en(con, usuario_id, guild_id, ahora),
                saldo=_saldos_en(con, usuario_id, guild_id).asciicoins,
            )

        depto = db._departamento_en(con, usuario_id, guild_id, ahora)
        coste = dep.coste_de_ampliar(depto, eje)
        if coste is None:
            return ResultadoDepartamento(
                departamento=depto, motivo="ya_es_el_maximo",
                saldo=_saldos_en(con, usuario_id, guild_id).asciicoins,
            )
        if not _cobrar_monedas_en(con, usuario_id, guild_id, coste):
            return ResultadoDepartamento(
                departamento=depto, motivo="faltan_monedas", coste=coste,
                saldo=_saldos_en(con, usuario_id, guild_id).asciicoins,
            )

        # Más casillas suben el tope de la comodidad: es parte del ritmo.
        db.asentar_el_plantel_en(con, usuario_id, guild_id, ahora)
        db.ampliar_en(con, usuario_id, guild_id, eje)
        ampliado = db._departamento_leido(con, usuario_id, guild_id)
        _anotar(
            con, evento_id, usuario_id, guild_id, "ampliar", eje,
            {"ancho": ampliado.ancho, "fondo": ampliado.fondo, "coste": coste}, ahora,
        )
        return ResultadoDepartamento(
            ok=True, departamento=ampliado, coste=coste,
            saldo=_saldos_en(con, usuario_id, guild_id).asciicoins,
        )


@dataclass(frozen=True)
class ResultadoCocina:
    ok: bool = False
    sopaipilla: obj.Objeto | None = None
    problema: str | None = None


def cocinar(
    usuario_id: str, guild_id: str, color: str, ahora: datetime | None = None,
    rng=None,
) -> ResultadoCocina:
    """Cambia porotos de un color por una sopaipilla de ese color.

    El arcoíris se cuece igual y cuesta lo mismo que los demás: lo que lo hace
    raro es encontrarlo, no cocinarlo. Lo que sí cambia es que **su dado se tira
    aquí**, porque no tiene color del que sacarlo; las de color lo consultan al
    comerse, en la tabla de gustos de quien se la come.
    """
    if color not in hue.COCINABLES:
        raise ValueError(f"color de poroto desconocido: {color!r}")

    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        if not db.gastar_en(
            con, usuario_id, guild_id, hue.clave_de_poroto(color),
            hue.POROTOS_POR_SOPAIPILLA,
        ):
            tengo = db._inventario(con, usuario_id, guild_id).get(
                hue.clave_de_poroto(color), 0
            )
            return ResultadoCocina(
                problema=(
                    f"Hacen falta {hue.POROTOS_POR_SOPAIPILLA} porotos "
                    f"{hue.plural_de(color)} y tienes {tengo}."
                ),
            )
        # El dado se tira con los porotos ya gastados: así una cocina que falla
        # por falta de ingredientes no consume una tirada.
        caras = hue.tirar_caras_de_arcoiris(rng) if color == hue.ARCOIRIS else 0
        sopaipilla = obj.CATALOGO[hue.clave_de_sopaipilla(color, caras)]
        db.guardar_en_la_mochila_en(
            con, usuario_id, guild_id, sopaipilla.clave
        )
        return ResultadoCocina(ok=True, sopaipilla=sopaipilla)


def equipar_cosmetico(
    usuario_id: str, guild_id: str, cosmetico: cos.Cosmetico,
    criatura_id: int | None = None,
) -> ResultadoCosmetico:
    """Le pone al activo algo que tengas **libre**. No cobra nada.

    `criatura_id`, si viene, es el gachamon que enseña la pantalla: si ya no es
    el activo no se viste a nadie y el motivo es `sin_gachamon`.

    Libre y no sólo «tuyo»: una pieza la lleva un gachamon vivo o ninguno, así
    que la que ya está puesta en otro no se puede duplicar. Se comprueba
    **dentro** de la transacción porque un menú abierto hace dos minutos puede
    ofrecer algo que entretanto se ha puesto otro.

    El orden de las comprobaciones importa: primero si el activo ya la lleva.
    Al revés, ponerle lo que ya tiene puesto respondería «no lo tienes» —porque
    lo puesto no está entre lo libre—, que es falso y desconcertante.
    """
    if cos.CATALOGO.get(cosmetico.clave) != cosmetico:
        raise ValueError("el cosmético no coincide con el catálogo actual")

    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        saldo = _saldos_en(con, usuario_id, guild_id).asciigems
        criatura = db.criatura_activa_en(con, usuario_id, guild_id)
        if criatura is None or (
            criatura_id is not None and criatura.id != criatura_id
        ):
            return ResultadoCosmetico(
                saldo=saldo, problema="No tienes ningún gachamon activo.",
                motivo="sin_gachamon",
            )
        if getattr(criatura, cosmetico.tipo) == cosmetico.clave:
            return ResultadoCosmetico(
                criatura=criatura, saldo=saldo, motivo="ya_lo_lleva",
                problema=f"{criatura.nombre} ya lo lleva puesto.",
            )
        if cosmetico.clave not in db._ropero_disponible(con, usuario_id, guild_id):
            # Se distingue no tenerlo de tenerlo puesto en otro: son problemas
            # distintos y se arreglan distinto —uno se compra, el otro se quita—.
            lleva = db.quien_lleva(
                con, usuario_id, guild_id, cosmetico.clave, cosmetico.tipo
            )
            # La frase y el motivo salen de lo mismo: si lo lleva alguien.
            return ResultadoCosmetico(
                criatura=criatura, saldo=saldo,
                problema=(
                    f"**{cosmetico.nombre}** lo lleva **{lleva.nombre}**. "
                    "Quítaselo primero."
                    if lleva
                    else f"No tienes **{cosmetico.nombre}** en tu ropero."
                ),
                motivo="lo_lleva_otro" if lleva else "no_lo_tienes",
                lo_lleva=lleva.nombre if lleva else None,
            )

        vestido, sustituido = _vestir_en(
            con, criatura, cosmetico.tipo, cosmetico.clave
        )
        return ResultadoCosmetico(
            ok=True, criatura=vestido, saldo=saldo, sustituido=sustituido
        )


def quitar_cosmetico(
    usuario_id: str, guild_id: str, tipo: str,
    criatura_id: int | None = None,
) -> ResultadoCosmetico:
    """Le quita una pieza al activo. Se queda en el ropero, no se pierde.

    `criatura_id` funciona como en `equipar_cosmetico`.
    """
    if tipo not in cos.TIPOS:
        raise ValueError(f"tipo de cosmético desconocido: {tipo!r}")

    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        saldo = _saldos_en(con, usuario_id, guild_id).asciigems
        criatura = db.criatura_activa_en(con, usuario_id, guild_id)
        if criatura is None or (
            criatura_id is not None and criatura.id != criatura_id
        ):
            return ResultadoCosmetico(
                saldo=saldo, problema="No tienes ningún gachamon activo.",
                motivo="sin_gachamon",
            )
        if getattr(criatura, tipo) is None:
            return ResultadoCosmetico(
                criatura=criatura, saldo=saldo, motivo="no_lleva_nada",
                problema=f"{criatura.nombre} no lleva nada de eso.",
            )

        desnudo, quitado = _vestir_en(con, criatura, tipo, None)
        return ResultadoCosmetico(
            ok=True, criatura=desnudo, saldo=saldo, sustituido=quitado
        )


def comprar(
    evento_id: str,
    usuario_id: str,
    guild_id: str,
    objeto: obj.Objeto,
    ahora: datetime | None = None,
) -> ResultadoCompra:
    """Decide, debita, entrega y registra una compra en una transacción."""
    if obj.CATALOGO.get(objeto.clave) != objeto:
        raise ValueError("el objeto no coincide exactamente con el catálogo actual")
    if not objeto.se_vende:
        raise ValueError("ese objeto no está a la venta")
    fecha = _fecha_economica(ahora or db.ahora_utc())
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        previa = con.execute(
            "SELECT resultado, solicitud FROM operaciones_economia "
            "WHERE evento_id = ? AND usuario_id = ? AND guild_id = ? "
            "AND tipo = 'compra'",
            (evento_id, usuario_id, guild_id),
        ).fetchone()
        if previa is not None:
            if previa["solicitud"] != objeto.clave:
                raise RuntimeError("el evento de compra pertenece a otro objeto")
            return ResultadoCompra(
                previa["resultado"] == "comprada",
                True,
                _saldos_en(con, usuario_id, guild_id),
                objeto.clave,
            )

        _asegurar_monedero(con, usuario_id, guild_id)
        debitada = con.execute(
            "UPDATE monederos SET asciicoins = asciicoins - ? "
            "WHERE usuario_id = ? AND guild_id = ? AND asciicoins >= ?",
            (objeto.precio, usuario_id, guild_id, objeto.precio),
        ).rowcount > 0
        resultado = "comprada" if debitada else "saldo_insuficiente"
        delta = -objeto.precio if debitada else 0
        if debitada:
            con.execute(
                "INSERT INTO inventario (usuario_id, guild_id, objeto, cantidad) "
                "VALUES (?, ?, ?, 1) ON CONFLICT(usuario_id, guild_id, objeto) "
                "DO UPDATE SET cantidad = cantidad + 1",
                (usuario_id, guild_id, objeto.clave),
            )
        con.execute(
            "INSERT INTO operaciones_economia "
            "(evento_id, usuario_id, guild_id, tipo, fecha_utc, resultado, "
            "delta_asciicoins, solicitud) VALUES (?, ?, ?, 'compra', ?, ?, ?, ?)",
            (evento_id, usuario_id, guild_id, fecha, resultado, delta, objeto.clave),
        )
        return ResultadoCompra(
            debitada, False, _saldos_en(con, usuario_id, guild_id), objeto.clave
        )


# --- Usar lo que llevas en la mochila ----------------------------------------
#
# Una sola operación con evento: gastar la unidad, avanzar al gachamon y aplicar
# el efecto van juntos, y un reintento no gasta otra. Las frases no van aquí: las
# pone la web.

@dataclass(frozen=True)
class ResultadoUso:
    """Cómo salió usar algo de la mochila, con los datos para contarlo.

    En el rechazo `no_hace_falta` (no habría hecho nada), `efecto` y `accion`
    son los que habría tenido, y `criatura` cómo está: lo que piden las frases.
    """

    ok: bool = False
    motivo: str | None = None            # sin_gachamon | no_tienes | no_se_usa | nombre | mismo_nombre | no_hace_falta
    problema: str | None = None          # la frase de quien valida el nombre, cuando motivo == "nombre"
    objeto: str = ""
    criatura: sim.Criatura | None = None  # cómo queda
    efecto: str | None = None            # reinicia | estadistica | sopaipilla | comida | nombre
    accion: str | None = None            # la que queda libre, si efecto == "reinicia"
    stats: tuple[str, ...] = ()
    bonus: int = 0
    caras: int = 0
    gusto: str | None = None             # `huerto.le_gusta`, en la sopaipilla de color
    comida: int = 0                      # cuánta ganó
    nombre_anterior: str = ""
    replay: bool = False


def usar_objeto(
    evento_id: str, usuario_id: str, guild_id: str, objeto: obj.Objeto,
    ahora: datetime | None = None, rng: random.Random | None = None,
    criatura_id: int | None = None,
) -> ResultadoUso:
    """Gasta una unidad y aplica lo que hace, en una sola transacción.

    Ningún rechazo cuesta el objeto: todo lo que puede decir que no va antes de
    gastar, también que no haría nada (`no_hace_falta`). Repetirlo con el mismo
    evento contesta lo que salió la primera vez, sin gastar ni volver a tirar el
    dado. La placa no se usa aquí: necesita un nombre, y va por
    `renombrar_con_placa`.

    `criatura_id` es el gachamon a quien se le da (la web manda el que enseñaba
    su pantalla): si el activo ya es otro, o no hay, no se le da a nadie y no se
    gasta. Sin él, se le da al activo.
    """
    return _usar(
        evento_id, usuario_id, guild_id, objeto, ahora or db.ahora_utc(),
        rng=rng, criatura_id=criatura_id,
    )


def renombrar_con_placa(
    evento_id: str, usuario_id: str, guild_id: str, objeto: obj.Objeto,
    propuesto: str, ahora: datetime | None = None,
    criatura_id: int | None = None,
) -> ResultadoUso:
    """Valida el nombre, gasta la placa y se lo pone al activo, todo de una vez.

    Se valida antes que nada: un nombre que no vale no puede costar la placa.
    `criatura_id`, como en `usar_objeto`.
    """
    return _usar(
        evento_id, usuario_id, guild_id, objeto, ahora or db.ahora_utc(),
        propuesto=propuesto, criatura_id=criatura_id,
    )


def _usar(
    evento_id: str, usuario_id: str, guild_id: str, objeto: obj.Objeto,
    ahora: datetime, *, rng: random.Random | None = None,
    propuesto: str | None = None, criatura_id: int | None = None,
) -> ResultadoUso:
    """Lo común a usar un objeto y a la placa; `propuesto` es lo de la placa."""
    placa = propuesto is not None
    solicitud = f"{objeto.clave}:{propuesto}" if placa else objeto.clave
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        hecha = _ya_hecha(con, evento_id, usuario_id, guild_id, "uso", solicitud)
        if hecha is not None:
            return _resultado_del_uso(
                objeto, db.criatura_activa_en(con, usuario_id, guild_id), hecha,
                replay=True,
            )

        # Va detrás del replay, que contesta lo de la primera vez aunque el
        # activo ya sea otro, y delante de todo lo demás: si el cambio de
        # gachamon ya estaba registrado (otro activado desde otra pestaña, por
        # ejemplo), sólo se nota aquí.
        if criatura_id is not None:
            activa = db.criatura_activa_en(con, usuario_id, guild_id)
            if activa is None or activa.id != criatura_id:
                return ResultadoUso(motivo="sin_gachamon", objeto=objeto.clave)

        nombre = None
        if placa:
            try:
                nombre = sim.normalizar_nombre(propuesto)
            except ValueError as error:
                return ResultadoUso(
                    motivo="nombre", problema=str(error), objeto=objeto.clave
                )

        criatura = db.criatura_activa_en(con, usuario_id, guild_id)
        if criatura is None:
            return ResultadoUso(motivo="sin_gachamon", objeto=objeto.clave)
        if not (objeto.renombra if placa else objeto.se_aplica_al_momento):
            return ResultadoUso(
                motivo="no_se_usa", objeto=objeto.clave, criatura=criatura
            )

        # Como en `ejecutar_cuidado`: se pone al día antes de mirar si haría
        # falta y de aplicarle nada.
        criatura = db._avanzar_en(con, criatura, ahora)
        if placa and nombre == criatura.nombre:
            return ResultadoUso(
                motivo="mismo_nombre", objeto=objeto.clave, criatura=criatura
            )
        sin_efecto = None if placa else _no_haria_nada(con, criatura, objeto, ahora)
        if sin_efecto is not None:
            return ResultadoUso(
                motivo="no_hace_falta", objeto=objeto.clave, criatura=criatura,
                efecto=sin_efecto, accion=objeto.reinicia,
            )
        if not db.gastar_en(con, usuario_id, guild_id, objeto.clave):
            return ResultadoUso(
                motivo="no_tienes", objeto=objeto.clave, criatura=criatura
            )

        if placa:
            # El nombre de la placa lo eliges tú: deja de ser el que se puso solo.
            queda = replace(criatura, nombre=nombre, se_nombro_solo=False)
            datos = {"efecto": "nombre", "nombre_anterior": criatura.nombre}
        else:
            queda, datos = _aplicar_objeto(con, criatura, objeto, ahora, rng)
        db._guardar(con, queda)
        _anotar(
            con, evento_id, usuario_id, guild_id, "uso", solicitud, datos, ahora
        )
        return _resultado_del_uso(objeto, queda, datos)


def _aplicar_objeto(
    con, criatura: sim.Criatura, objeto: obj.Objeto, ahora: datetime,
    rng: random.Random | None,
) -> tuple[sim.Criatura, dict]:
    """El efecto del objeto: cómo queda el gachamon y qué anotar de lo que salió.

    Lo anotado es JSON y es todo lo que hace falta para contarlo otra vez igual:
    un replay no vuelve a tirar el dado ni a mirar el reloj.
    """
    if objeto.reinicia:
        db.quitar_cooldown_en(con, criatura.id, objeto.reinicia)
        return criatura, {"efecto": "reinicia", "accion": objeto.reinicia}

    if objeto.stat:
        bonus = obj.tirar_bonus(objeto, rng)
        db.poner_efecto_en(con, criatura.id, objeto.stat, bonus, ahora)
        return criatura, {
            "efecto": "estadistica", "stats": [objeto.stat], "bonus": bonus,
            "caras": objeto.caras,
        }

    if objeto.es_sopaipilla:
        # El arcoíris no tiene color, así que no hay gusto que consultar: su
        # dado se decidió al cocinarla y lo trae escrito. Lo que comparte con las
        # de color es lo de siempre: **un solo dado** para todas las
        # estadísticas que toque, porque es un plato y no varias pociones.
        arcoiris = objeto.color == hue.ARCOIRIS
        caras = (
            objeto.caras if arcoiris
            else hue.caras_de(criatura.caracter, objeto.color)
        )
        stats = sim.ESTADISTICAS if arcoiris else ("fuerza", "velocidad")
        bonus = (rng or random.Random()).randint(1, caras)
        for stat in stats:
            db.poner_efecto_en(con, criatura.id, stat, bonus, ahora)
        return criatura, {
            "efecto": "sopaipilla", "stats": list(stats), "bonus": bonus,
            "caras": caras,
            "gusto": None if arcoiris
            else hue.le_gusta(criatura.caracter, objeto.color),
        }

    # Lo único que queda de `se_aplica_al_momento`, y `_usar` ya lo ha mirado:
    # no hay caso por descarte que gaste la unidad sin hacer nada. No es un
    # `assert`, que con `python -O` desaparece; al lanzar, la transacción
    # devuelve la unidad.
    if not objeto.alimenta:
        raise ValueError(f"objeto sin efecto conocido: {objeto.clave}")
    alimentada, comida = _alimentar(criatura, objeto)
    return alimentada, {"efecto": "comida", "comida": comida}


def _alimentar(
    criatura: sim.Criatura, objeto: obj.Objeto
) -> tuple[sim.Criatura, int]:
    """Cómo queda al comérselo y cuánta comida gana, redondeada como se cuenta."""
    alimentada = obj.aplicar_a_la_criatura(objeto, criatura)
    return alimentada, round(alimentada.hambre - criatura.hambre)


def _no_haria_nada(
    con, criatura: sim.Criatura, objeto: obj.Objeto, ahora: datetime
) -> str | None:
    """Si usarlo ahora no haría nada, el efecto que habría tenido; si no, `None`.

    Dos casos, ni uno más, mirados como los aplicaría `_aplicar_objeto` y con
    sus mismas cuentas: un reinicio sin espera que borrar y comida que sumaría 0
    redondeado. Las pociones y las sopaipillas siempre ponen o renuevan su
    efecto.
    """
    if objeto.reinicia:
        if db.espera_en(con, criatura.id, objeto.reinicia, ahora):
            return None
        return "reinicia"
    if objeto.stat or objeto.es_sopaipilla:
        return None
    if objeto.alimenta and _alimentar(criatura, objeto)[1] == 0:
        return "comida"
    return None


def _resultado_del_uso(
    objeto: obj.Objeto, criatura: sim.Criatura | None, datos: dict,
    replay: bool = False,
) -> ResultadoUso:
    """El mismo resultado la primera vez y en un replay: sale de lo anotado."""
    return ResultadoUso(
        ok=True, objeto=objeto.clave, criatura=criatura, replay=replay,
        efecto=datos["efecto"], accion=datos.get("accion"),
        stats=tuple(datos.get("stats", ())), bonus=datos.get("bonus", 0),
        caras=datos.get("caras", 0), gusto=datos.get("gusto"),
        comida=datos.get("comida", 0),
        nombre_anterior=datos.get("nombre_anterior", ""),
    )
