"""Economía transaccional: saldos, límites diarios y operaciones idempotentes.

Este módulo concentra las reglas monetarias. ``db`` conserva el esquema, las
migraciones y los repositorios de dominio; la dependencia va sólo de aquí a db.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

import aventura as av
import casas as cas
import competir as comp
import cosmeticos as cos
import db
import huerto as hue
import logros as lgr
import objetos as obj
import simulacion as sim

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
class SeleccionEntrenamientoConjunto:
    activo_id: int
    activo_nombre: str
    reserva_id: int
    reserva_nombre: str


@dataclass(frozen=True)
class ResultadoEntrenamientoConjunto:
    participantes: tuple[sim.ResultadoAccion, ...] = ()
    delta_asciicoins: int = 0
    delta_evolucion: int = 0
    usados: int = 0
    limite: int = TOPE_CUIDADOS
    evolucion_usadas: int = 0
    topada: bool = False
    replay: bool = False
    problema: str | None = None
    bloqueada: sim.Criatura | None = None
    espera: timedelta | None = None


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
        nueva, rupturas = av.aplicar_viaje(
            avanzado, salida, ahora, percance
        )
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


def _asegurar_monedero(con, usuario_id: str, guild_id: str) -> None:
    con.execute(
        "INSERT OR IGNORE INTO monederos "
        "(usuario_id, guild_id, asciicoins, asciigems) VALUES (?, ?, 50, 50)",
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
    aunque se te haya muerto el plantel entero, que es de lo que van estas tres.
    """
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
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
    """Los asciicoins ya cobrados hoy, vengan de donde vengan.

    Sólo `acreditada`: las compras son `comprada` y llevan delta negativo, así
    que gastar no te devuelve sitio en el bote. El bote mide lo **ganado**, no
    lo que tienes.
    """
    return con.execute(
        "SELECT COALESCE(SUM(delta_asciicoins), 0) FROM operaciones_economia "
        "WHERE usuario_id = ? AND guild_id = ? AND fecha_utc = ? "
        "AND resultado = 'acreditada'",
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
    """Lo que te has encontrado por el camino y lo que de eso te llevas."""

    monedas: int = 0        # lo que entró de verdad, ya recortado por el bote
    monedas_vistas: int = 0  # lo que había en el suelo
    gemas: int = 0
    replay: bool = False

    @property
    def topado(self) -> bool:
        return self.monedas_vistas > self.monedas


def otorgar_hallazgo(
    evento_id: str, usuario_id: str, guild_id: str,
    monedas: int, gemas: int, ahora: datetime | None = None,
) -> ResultadoHallazgo:
    """Paga lo encontrado en una aventura, en una sola transacción.

    Las monedas pasan por el bote diario —un hallazgo puede salir topado y hay
    que decirlo— y las gemas no: son otra moneda y otra economía, y al 0,5 % no
    hacen falta frenos.

    La idempotencia sale de donde ya sale: la clave primaria del ledger sobre
    `(evento_id, usuario_id, guild_id, tipo)`. Con la fila puesta, reprocesar el
    mismo viaje no vuelve a pagar **ni monedas ni gemas**, aunque éstas no
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

        delta, _, _ = _registrar_recompensa(
            con, evento_id, usuario_id, guild_id, fecha, "aventura",
            monedas, None, json.dumps({"monedas": monedas, "gemas": gemas}),
        )
        if gemas:
            _asegurar_monedero(con, usuario_id, guild_id)
            con.execute(
                "UPDATE monederos SET asciigems = asciigems + ? "
                "WHERE usuario_id = ? AND guild_id = ?",
                (gemas, usuario_id, guild_id),
            )
        return ResultadoHallazgo(
            monedas=delta, monedas_vistas=monedas, gemas=gemas
        )


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
    accion: str, ahora: datetime,
) -> ResultadoCuidado | None:
    """Aplica cuidado, cooldown y premios bajo un único ``BEGIN IMMEDIATE``."""
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        operacion = con.execute(
            "SELECT * FROM operaciones_economia WHERE evento_id = ? "
            "AND usuario_id = ? AND guild_id = ? AND tipo = 'cuidado'",
            (evento_id, usuario_id, guild_id),
        ).fetchone()
        if operacion is not None:
            if operacion["solicitud"] != accion:
                raise RuntimeError("el evento de cuidado pertenece a otra acción")
            criatura = db.criatura_activa_en(con, usuario_id, guild_id)
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

        criatura = db.criatura_activa_en(con, usuario_id, guild_id)
        if criatura is None:
            return None
        criatura = db._avanzar_en(con, criatura, ahora)
        if not criatura.viva:
            db._guardar(con, criatura)
            return ResultadoCuidado(
                criatura, "Tu gachamon ya no está entre nosotros.", ok=False
            )

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
            "cuidado", PREMIO_CUIDADO, TOPE_CUIDADOS, accion,
        )
        delta_evolucion = 0
        evolucion_usadas = 0
        if resultado.evoluciono:
            delta_evolucion, evolucion_usadas, _ = _registrar_recompensa(
                con, evento_id, usuario_id, guild_id, fecha,
                "evolucion", PREMIO_EVOLUCION, TOPE_EVOLUCIONES, accion,
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


def ejecutar_entrenamiento_conjunto(
    evento_id: str,
    usuario_id: str,
    guild_id: str,
    seleccion: SeleccionEntrenamientoConjunto,
    ahora: datetime,
) -> ResultadoEntrenamientoConjunto:
    """Entrena activo y reserva bajo una sola transacción serializada."""
    solicitud = json.dumps(
        {
            "accion": "entrenar",
            "activo": {
                "id": seleccion.activo_id,
                "nombre": seleccion.activo_nombre,
            },
            "modo": "conjunto",
            "reserva": {
                "id": seleccion.reserva_id,
                "nombre": seleccion.reserva_nombre,
            },
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        filas = con.execute(
            "SELECT * FROM operaciones_economia WHERE evento_id = ? "
            "AND usuario_id = ? AND guild_id = ?",
            (evento_id, usuario_id, guild_id),
        ).fetchall()
        if filas:
            por_tipo = {fila["tipo"]: fila for fila in filas}
            if set(por_tipo) not in ({"cuidado"}, {"cuidado", "evolucion"}):
                raise RuntimeError("el evento de entrenamiento conjunto está incompleto")
            if any(fila["solicitud"] != solicitud for fila in filas):
                raise RuntimeError(
                    "el evento de entrenamiento conjunto pertenece a otra selección"
                )
            cuidado = por_tipo["cuidado"]
            evolucion = por_tipo.get("evolucion")
            delta_evolucion = (
                evolucion["delta_asciicoins"] if evolucion is not None else 0
            )
            return ResultadoEntrenamientoConjunto(
                delta_asciicoins=(
                    cuidado["delta_asciicoins"] + delta_evolucion
                ),
                delta_evolucion=delta_evolucion,
                usados=_contar_acreditadas(
                    con,
                    usuario_id,
                    guild_id,
                    cuidado["fecha_utc"],
                    "cuidado",
                ),
                evolucion_usadas=(
                    _contar_acreditadas(
                        con,
                        usuario_id,
                        guild_id,
                        evolucion["fecha_utc"],
                        "evolucion",
                    )
                    if evolucion is not None
                    else 0
                ),
                topada=cuidado["resultado"] == "topada",
                replay=True,
            )

        activo = db.criatura_activa_en(con, usuario_id, guild_id)
        if (
            activo is None
            or activo.id != seleccion.activo_id
            or activo.nombre != seleccion.activo_nombre
        ):
            return ResultadoEntrenamientoConjunto(problema="activo_caduco")

        reserva = db.criatura_en(con, seleccion.reserva_id)
        if (
            reserva is None
            or reserva.id == activo.id
            or reserva.usuario_id != usuario_id
            or reserva.guild_id != guild_id
            or not reserva.viva
            or reserva.activa
            or sim.esta_sin_nombrar(reserva)
            or reserva.nombre != seleccion.reserva_nombre
        ):
            return ResultadoEntrenamientoConjunto(problema="reserva_caduca")

        esperas = (
            (activo, db.espera_en(con, activo.id, sim.ENTRENAR, ahora)),
            (reserva, db.espera_en(con, reserva.id, sim.ENTRENAR, ahora)),
        )
        bloqueada, espera = max(esperas, key=lambda par: par[1])
        if espera > timedelta(0):
            return ResultadoEntrenamientoConjunto(
                problema="cooldown", bloqueada=bloqueada, espera=espera
            )

        # Por `db` y no por `sim` a secas: el hogar cambia el ritmo del activo,
        # y llamando directo se entrenaría con el de quien tiene techo aunque
        # esté a la intemperie. La reserva no avanza, que es su invariante.
        activo_avanzado = db._avanzar_en(con, activo, ahora)
        if not activo_avanzado.viva:
            db._guardar(con, activo_avanzado)
            return ResultadoEntrenamientoConjunto(
                problema="activo_muerto", bloqueada=activo_avanzado
            )

        participantes = (
            sim.aplicar_entrenamiento_conjunto(activo_avanzado),
            sim.aplicar_entrenamiento_conjunto(reserva),
        )
        for participante in participantes:
            db._guardar(con, participante.criatura)

        hasta = ahora + sim.COOLDOWNS[sim.ENTRENAR]
        for participante in participantes:
            db.poner_cooldown_en(
                con, participante.criatura.id, sim.ENTRENAR, hasta
            )
            db.apuntar_en(con, participante.criatura.id, lgr.CUIDADOS)

        fecha = _fecha_economica(ahora)
        delta, usados, topada = _registrar_recompensa(
            con,
            evento_id,
            usuario_id,
            guild_id,
            fecha,
            "cuidado",
            PREMIO_CUIDADO,
            TOPE_CUIDADOS,
            solicitud,
        )
        delta_evolucion = 0
        evolucion_usadas = 0
        if any(participante.evoluciono for participante in participantes):
            delta_evolucion, evolucion_usadas, _ = _registrar_recompensa(
                con,
                evento_id,
                usuario_id,
                guild_id,
                fecha,
                "evolucion",
                PREMIO_EVOLUCION,
                TOPE_EVOLUCIONES,
                solicitud,
            )
        return ResultadoEntrenamientoConjunto(
            participantes=participantes,
            delta_asciicoins=delta + delta_evolucion,
            delta_evolucion=delta_evolucion,
            usados=usados,
            evolucion_usadas=evolucion_usadas,
            topada=topada,
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
            if not criatura.viva:
                return ResultadoCompetencia(
                    None, antes=antes, despues=criaturas,
                    problema="Un gachamon ha muerto antes de competir.",
                    problema_usuario_id=usuario_id,
                    problema_criatura=criatura,
                )
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


def _vestir_en(
    con, criatura: sim.Criatura, tipo: str, clave: str | None
) -> tuple[sim.Criatura, cos.Cosmetico | None]:
    """Le cambia una pieza y devuelve cómo queda y qué llevaba antes."""
    llevaba = cos.buscar(getattr(criatura, tipo))
    vestido = replace(criatura, **{tipo: clave})
    db._guardar(con, vestido)
    return vestido, llevaba


def comprar_cosmetico(
    usuario_id: str, guild_id: str, cosmetico: cos.Cosmetico
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
    """
    if cos.CATALOGO.get(cosmetico.clave) != cosmetico:
        raise ValueError("el cosmético no coincide con el catálogo actual")

    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
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
            )

        pagado = con.execute(
            "UPDATE monederos SET asciigems = asciigems - ? "
            "WHERE usuario_id = ? AND guild_id = ? AND asciigems >= ?",
            (cosmetico.precio, usuario_id, guild_id, cosmetico.precio),
        ).rowcount > 0
        saldo = _saldos_en(con, usuario_id, guild_id).asciigems
        if not pagado:
            return ResultadoCosmetico(
                criatura=criatura, saldo=saldo,
                problema=(
                    f"Te faltan {cosmetico.precio - saldo} asciigems. "
                    "Se ganan con los logros: mira `/logros`."
                ),
            )

        db.guardar_en_el_ropero_en(con, usuario_id, guild_id, cosmetico.clave)
        if criatura is None:
            return ResultadoCosmetico(ok=True, saldo=saldo)
        vestido, sustituido = _vestir_en(
            con, criatura, cosmetico.tipo, cosmetico.clave
        )
        return ResultadoCosmetico(
            ok=True, criatura=vestido, saldo=saldo, sustituido=sustituido
        )


@dataclass(frozen=True)
class ResultadoMudanza:
    """Cómo salió comprar casa."""

    ok: bool = False
    casa: cas.Casa | None = None        # la nueva
    desde: cas.Casa | None = None       # de dónde viene; None es el refugio
    saldo: int = 0                      # asciicoins que quedan
    problema: str | None = None


@dataclass(frozen=True)
class ResultadoVenta:
    """Cómo salió vender la casa."""

    ok: bool = False
    casa: cas.Casa | None = None      # la que se ha vendido
    cobrado: int = 0
    saldo: int = 0
    guardados: int = 0                # muebles que vuelven al armario
    problema: str | None = None


def vender_casa(
    usuario_id: str, guild_id: str, ahora: datetime | None = None
) -> ResultadoVenta:
    """Vende la casa y te devuelve al refugio con la semana entera.

    **Lo cobrado no pasa por el bote diario, y es lo más importante de aquí.**
    El bote son veinte asciicoins al día y la casa grande devuelve novecientos
    sesenta: si esto contara como ganancia se cobrarían veinte y se perderían
    novecientos cuarenta. Una venta es una **devolución**, no una ganancia, y por
    eso entra directa al monedero y no lleva fila en `operaciones_economia` —que
    además envenenaría el bote del día, porque `_ganado_hoy` suma todo lo
    acreditado.

    Lo que impide cobrarla dos veces no es el ledger sino el propio estado: con
    la casa ya a `NULL` no hay nada que vender. Es el cerrojo de
    `comprar_cosmetico`.

    Los muebles se guardan sin colocar —retirar uno nunca lo destruye— y lo
    plantado se pierde: la tierra era de la casa.
    """
    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        hogar = db._hogar_de(con, usuario_id, guild_id, ahora)
        if hogar.casa is None:
            return ResultadoVenta(
                saldo=_saldos_en(con, usuario_id, guild_id).asciicoins,
                problema=(
                    "No tienes casa que vender: vives en el refugio."
                    if hogar.estado(ahora) == cas.REFUGIO
                    else "No tienes casa que vender."
                ),
            )

        casa = hogar.casa
        cobrado = cas.lo_que_dan_por(casa)
        _asegurar_monedero(con, usuario_id, guild_id)
        con.execute(
            "UPDATE monederos SET asciicoins = asciicoins + ? "
            "WHERE usuario_id = ? AND guild_id = ?",
            (cobrado, usuario_id, guild_id),
        )
        guardados = db.vaciar_la_casa_en(con, usuario_id, guild_id, ahora)
        return ResultadoVenta(
            ok=True, casa=casa, cobrado=cobrado, guardados=guardados,
            saldo=_saldos_en(con, usuario_id, guild_id).asciicoins,
        )


def comprar_casa(
    usuario_id: str, guild_id: str, casa: cas.Casa,
    ahora: datetime | None = None,
) -> ResultadoMudanza:
    """Cobra los asciicoins y te muda, en una transacción.

    **Sólo se sube de tamaño.** Comprar la que ya tienes, o una menor, no cobra
    ni cambia nada: es el mismo cerrojo que el del ropero contra el doble clic,
    y además es lo que quiere quien juega — nadie compra una casa pequeña
    teniendo la grande.

    Se paga con asciicoins y no con gemas a propósito: las gemas están enteras
    comprometidas con los cosméticos, y los asciicoins hasta ahora sólo compraban
    pociones. Esto les da adónde ir.

    No lleva fila en `operaciones_economia` aunque sean asciicoins: allí se
    congela lo que pagó un evento que puede reprocesarse, y aquí el cerrojo es el
    tamaño — el segundo intento ya encuentra la casa puesta y no cobra.
    """
    if cas.CATALOGO.get(casa.clave) != casa:
        raise ValueError("la casa no coincide con el catálogo actual")

    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        hogar = db._hogar_de(con, usuario_id, guild_id, ahora)
        _asegurar_monedero(con, usuario_id, guild_id)
        saldo = _saldos_en(con, usuario_id, guild_id).asciicoins

        if not cas.puede_mudarse_a(hogar, casa):
            return ResultadoMudanza(
                casa=hogar.casa, desde=hogar.casa, saldo=saldo,
                problema=(
                    f"Ya vives en {hogar.casa.nombre}, que no es peor."
                    if hogar.casa else "Esa casa no existe."
                ),
            )

        pagado = con.execute(
            "UPDATE monederos SET asciicoins = asciicoins - ? "
            "WHERE usuario_id = ? AND guild_id = ? AND asciicoins >= ?",
            (casa.precio, usuario_id, guild_id, casa.precio),
        ).rowcount > 0
        saldo = _saldos_en(con, usuario_id, guild_id).asciicoins
        if not pagado:
            return ResultadoMudanza(
                casa=casa, desde=hogar.casa, saldo=saldo,
                problema=(
                    f"Te faltan {casa.precio - saldo} asciicoins. "
                    "Se ganan cuidando, evolucionando y compitiendo."
                ),
            )

        db.mudar_en(con, usuario_id, guild_id, casa.clave)
        return ResultadoMudanza(
            ok=True, casa=casa, desde=hogar.casa, saldo=saldo
        )


@dataclass(frozen=True)
class ResultadoMueble:
    """Cómo salió comprar, colocar o retirar un mueble."""

    ok: bool = False
    mueble: cas.Mueble | None = None
    casa: cas.Casa | None = None
    comodidad: int = 0          # la de la casa después
    puestos: int = 0            # cuántos huecos van ocupados
    saldo: int = 0
    problema: str | None = None


def _estado_de_la_casa(
    con, usuario_id: str, guild_id: str, ahora: datetime
) -> tuple[cas.Casa | None, dict[str, bool], str | None]:
    """La casa, lo que hay dentro, y por qué no se puede amueblar si no se puede.

    El refugio no se decora —es común y no es tuyo— y a la intemperie no hay
    dónde poner nada. Las dos cosas se comprueban aquí, en un solo sitio, porque
    las tres operaciones necesitan lo mismo.
    """
    hogar = db._hogar_de(con, usuario_id, guild_id, ahora)
    if hogar.casa is None:
        estorbo = (
            "El refugio no se puede amueblar: es de todos. Cómprate una casa."
            if hogar.estado(ahora) == cas.REFUGIO
            else "Estás a la intemperie. Cómprate una casa para amueblarla."
        )
        return None, {}, estorbo
    return hogar.casa, db._mobiliario(con, usuario_id, guild_id), None


def _recibo_mueble(
    con, usuario_id: str, guild_id: str, casa, mobiliario, mueble=None, ok=False,
    problema=None,
) -> ResultadoMueble:
    dentro = [c for c, puesto in mobiliario.items() if puesto]
    return ResultadoMueble(
        ok=ok, mueble=mueble, casa=casa,
        comodidad=cas.comodidad_de(casa, dentro) if casa else 0,
        puestos=len(dentro),
        saldo=_saldos_en(con, usuario_id, guild_id).asciicoins,
        problema=problema,
    )


def comprar_mueble(
    usuario_id: str, guild_id: str, mueble: cas.Mueble,
    ahora: datetime | None = None,
) -> ResultadoMueble:
    """Cobra el mueble y lo coloca si queda hueco; si no, se guarda.

    Uno de cada, como el ropero, y por lo mismo: repetir la chimenea no
    significaría nada y llegar al techo comprando cuatro veces el mueble más caro
    dejaría el catálogo sin sentido. Comprar el que ya tienes no cobra.
    """
    if cas.MUEBLES.get(mueble.clave) != mueble:
        raise ValueError("el mueble no coincide con el catálogo actual")

    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        casa, mobiliario, estorbo = _estado_de_la_casa(
            con, usuario_id, guild_id, ahora
        )
        _asegurar_monedero(con, usuario_id, guild_id)
        if estorbo:
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=estorbo,
            )
        assert casa is not None
        if mueble.clave in mobiliario:
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=f"Ya tienes **{mueble.nombre}**.",
            )

        pagado = con.execute(
            "UPDATE monederos SET asciicoins = asciicoins - ? "
            "WHERE usuario_id = ? AND guild_id = ? AND asciicoins >= ?",
            (mueble.precio, usuario_id, guild_id, mueble.precio),
        ).rowcount > 0
        if not pagado:
            faltan = mueble.precio - _saldos_en(
                con, usuario_id, guild_id
            ).asciicoins
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=f"Te faltan {faltan} asciicoins.",
            )

        dentro = cas.caben_mas(
            casa, [c for c, puesto in mobiliario.items() if puesto]
        )
        db.comprar_mueble_en(con, usuario_id, guild_id, mueble.clave, dentro)
        mobiliario[mueble.clave] = dentro
        return _recibo_mueble(
            con, usuario_id, guild_id, casa, mobiliario, mueble, ok=True
        )


def colocar_mueble(
    usuario_id: str, guild_id: str, mueble: cas.Mueble,
    ahora: datetime | None = None,
) -> ResultadoMueble:
    """Lo mete en la casa. Falla si no queda hueco, y lo dice con el número."""
    if cas.MUEBLES.get(mueble.clave) != mueble:
        raise ValueError("el mueble no coincide con el catálogo actual")

    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        casa, mobiliario, estorbo = _estado_de_la_casa(
            con, usuario_id, guild_id, ahora
        )
        if estorbo:
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=estorbo,
            )
        assert casa is not None
        if mueble.clave not in mobiliario:
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=f"No tienes **{mueble.nombre}**.",
            )
        if mobiliario[mueble.clave]:
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=f"**{mueble.nombre}** ya está puesto.",
            )
        dentro = [c for c, puesto in mobiliario.items() if puesto]
        if not cas.caben_mas(casa, dentro):
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=(
                    f"No cabe: {casa.nombre} tiene {casa.huecos} huecos y están "
                    "todos ocupados. Retira algo primero."
                ),
            )

        db.colocar_mueble_en(con, usuario_id, guild_id, mueble.clave, True)
        mobiliario[mueble.clave] = True
        return _recibo_mueble(
            con, usuario_id, guild_id, casa, mobiliario, mueble, ok=True
        )


def retirar_mueble(
    usuario_id: str, guild_id: str, mueble: cas.Mueble,
    ahora: datetime | None = None,
) -> ResultadoMueble:
    """Lo saca de la casa. Se guarda: nunca se pierde, como el ropero."""
    if cas.MUEBLES.get(mueble.clave) != mueble:
        raise ValueError("el mueble no coincide con el catálogo actual")

    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        casa, mobiliario, estorbo = _estado_de_la_casa(
            con, usuario_id, guild_id, ahora
        )
        if estorbo:
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=estorbo,
            )
        if not mobiliario.get(mueble.clave):
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=f"**{mueble.nombre}** no está puesto.",
            )

        db.colocar_mueble_en(con, usuario_id, guild_id, mueble.clave, False)
        mobiliario[mueble.clave] = False
        return _recibo_mueble(
            con, usuario_id, guild_id, casa, mobiliario, mueble, ok=True
        )


@dataclass(frozen=True)
class ResultadoHuerto:
    """Cómo salió plantar, regar o cosechar."""

    ok: bool = False
    bancal: int = 0
    sembrado: str | None = None         # la clave de lo que se acaba de sembrar
    cosechado: str | None = None        # la clave del poroto que salió
    cuantos: int = 0                    # cuántos, todos de ese mismo color
    arcoiris: bool = False              # y si además salió uno arcoíris
    listo_en: datetime | None = None
    problema: str | None = None


def _huerto_abierto(
    con, usuario_id: str, guild_id: str, ahora: datetime
) -> tuple[list[hue.Bancal], str | None]:
    """Los bancales de tu casa, o por qué no tienes ninguno."""
    hogar = db._hogar_leido(con, usuario_id, guild_id, ahora)
    cuantos = hue.bancales_de(hogar.casa.clave if hogar.casa else None)
    if not cuantos:
        return [], (
            "El refugio no tiene huerto. Cómprate una casa en 🛒 **Tienda**."
        )
    return db._huerto_de(con, usuario_id, guild_id, cuantos), None


def plantar(
    usuario_id: str, guild_id: str, bancal: int, ahora: datetime | None = None,
    que: str = hue.SEMILLA,
) -> ResultadoHuerto:
    """Gasta lo que se siembre y lo siembra.

    `que` va **después de `ahora`** y con valor por defecto porque hay bastante
    código que llama a esto por posición; así seguir sembrando semillas se
    escribe igual que antes.
    """
    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        bancales, estorbo = _huerto_abierto(con, usuario_id, guild_id, ahora)
        if estorbo:
            return ResultadoHuerto(problema=estorbo)
        elegido = next((b for b in bancales if b.numero == bancal), None)
        if elegido is None:
            return ResultadoHuerto(problema="Ese bancal no es tuyo.")
        if elegido.plantado:
            return ResultadoHuerto(
                bancal=bancal, problema="En ese bancal ya hay algo creciendo."
            )
        objeto = obj.CATALOGO.get(que)
        if objeto is None:
            return ResultadoHuerto(bancal=bancal, problema="Eso no se siembra.")
        if not db.gastar_en(con, usuario_id, guild_id, que):
            # Con el nombre entero en vez de concordar en género: «ninguna
            # semilla» y «ningún poroto rojo» pedían dos frases para decir lo
            # mismo, y la lista de cosas sembrables sólo va a crecer.
            pista = " Cómpralas en 🛒 **Tienda**." if que == hue.SEMILLA else ""
            return ResultadoHuerto(
                bancal=bancal,
                problema=f"Ya no te queda {objeto.emoji} **{objeto.nombre}**.{pista}",
            )

        db.plantar_en(con, usuario_id, guild_id, bancal, ahora, que)
        return ResultadoHuerto(
            ok=True, bancal=bancal, sembrado=que,
            listo_en=hue.Bancal(bancal, ahora).listo_en(),
        )


def regar(
    usuario_id: str, guild_id: str, bancal: int, ahora: datetime | None = None
) -> ResultadoHuerto:
    """Adelanta la cosecha. Sólo mientras crece: regar lo listo no haría nada."""
    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        bancales, estorbo = _huerto_abierto(con, usuario_id, guild_id, ahora)
        if estorbo:
            return ResultadoHuerto(problema=estorbo)
        elegido = next((b for b in bancales if b.numero == bancal), None)
        if elegido is None or not elegido.plantado:
            return ResultadoHuerto(
                bancal=bancal, problema="Ahí no hay nada plantado."
            )
        if elegido.regado:
            return ResultadoHuerto(bancal=bancal, problema="Ya está regado.")
        if elegido.listo(ahora):
            return ResultadoHuerto(
                bancal=bancal, problema="Ya está listo: cosecha y vuelve a sembrar."
            )

        db.regar_en(con, usuario_id, guild_id, bancal)
        regado = replace(elegido, regado=True)
        return ResultadoHuerto(ok=True, bancal=bancal, listo_en=regado.listo_en())


def cosechar(
    usuario_id: str, guild_id: str, bancal: int,
    ahora: datetime | None = None, rng=None,
) -> ResultadoHuerto:
    """Recoge la cosecha y deja el bancal en barbecho.

    **El color lo hereda lo sembrado**, y sólo se sortea cuando lo sembrado no
    tiene ninguno: la semilla de la tienda y el arcoíris. Sembrar un poroto rojo
    y recoger azules sería no entender qué se plantó.

    Salen varios y **todos del mismo color**: se tira una vez y esa tirada vale
    para la mata entera, que es lo que se espera de una planta. Aparte va el
    arcoíris, que sale de cualquier cosecha, sustituye a uno del lote y no cambia
    cuántos recoges.
    """
    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        bancales, estorbo = _huerto_abierto(con, usuario_id, guild_id, ahora)
        if estorbo:
            return ResultadoHuerto(problema=estorbo)
        elegido = next((b for b in bancales if b.numero == bancal), None)
        if elegido is None or not elegido.plantado:
            return ResultadoHuerto(
                bancal=bancal, problema="Ahí no hay nada plantado."
            )
        if not elegido.listo(ahora):
            return ResultadoHuerto(
                bancal=bancal, listo_en=elegido.listo_en(),
                problema="Todavía no está listo.",
            )

        color = hue.color_sembrado(elegido.sembrado) or hue.tirar_color(rng)
        clave = hue.clave_de_poroto(color)
        lote = hue.tirar_cuantos(rng)
        arcoiris = hue.tirar_arcoiris(rng)

        # El arcoíris **sustituye** a uno del lote, no se suma: lo raro es que
        # salga, no que la cosecha rinda más de la cuenta.
        normales = lote - 1 if arcoiris else lote
        if normales:
            db.guardar_en_la_mochila_en(
                con, usuario_id, guild_id, clave, normales
            )
        if arcoiris:
            db.guardar_en_la_mochila_en(
                con, usuario_id, guild_id,
                hue.clave_de_poroto(hue.ARCOIRIS), 1,
            )
        db.arrancar_en(con, usuario_id, guild_id, bancal)
        return ResultadoHuerto(
            ok=True, bancal=bancal, cosechado=clave, cuantos=normales,
            arcoiris=arcoiris,
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
    usuario_id: str, guild_id: str, cosmetico: cos.Cosmetico
) -> ResultadoCosmetico:
    """Le pone al activo algo que ya tienes. No cobra nada.

    Exige tenerlo en el ropero, y eso se comprueba **dentro** de la transacción:
    un menú abierto hace dos minutos puede ofrecer algo que ya no está.
    """
    if cos.CATALOGO.get(cosmetico.clave) != cosmetico:
        raise ValueError("el cosmético no coincide con el catálogo actual")

    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        saldo = _saldos_en(con, usuario_id, guild_id).asciigems
        criatura = db.criatura_activa_en(con, usuario_id, guild_id)
        if criatura is None:
            return ResultadoCosmetico(
                saldo=saldo, problema="No tienes ningún gachamon activo."
            )
        if cosmetico.clave not in db._ropero(con, usuario_id, guild_id):
            return ResultadoCosmetico(
                criatura=criatura, saldo=saldo,
                problema=f"No tienes **{cosmetico.nombre}** en tu ropero.",
            )
        if getattr(criatura, cosmetico.tipo) == cosmetico.clave:
            return ResultadoCosmetico(
                criatura=criatura, saldo=saldo,
                problema=f"{sim.nombre_visible(criatura)} ya lo lleva puesto.",
            )

        vestido, sustituido = _vestir_en(
            con, criatura, cosmetico.tipo, cosmetico.clave
        )
        return ResultadoCosmetico(
            ok=True, criatura=vestido, saldo=saldo, sustituido=sustituido
        )


def quitar_cosmetico(
    usuario_id: str, guild_id: str, tipo: str
) -> ResultadoCosmetico:
    """Le quita una pieza al activo. Se queda en el ropero, no se pierde."""
    if tipo not in cos.TIPOS:
        raise ValueError(f"tipo de cosmético desconocido: {tipo!r}")

    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        saldo = _saldos_en(con, usuario_id, guild_id).asciigems
        criatura = db.criatura_activa_en(con, usuario_id, guild_id)
        if criatura is None:
            return ResultadoCosmetico(
                saldo=saldo, problema="No tienes ningún gachamon activo."
            )
        if getattr(criatura, tipo) is None:
            return ResultadoCosmetico(
                criatura=criatura, saldo=saldo,
                problema=f"{sim.nombre_visible(criatura)} no lleva nada de eso.",
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
