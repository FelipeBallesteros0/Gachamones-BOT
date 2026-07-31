"""Economía transaccional: saldos, límites diarios y operaciones idempotentes.

Este módulo concentra las reglas monetarias. ``db`` conserva el esquema, las
migraciones y los repositorios de dominio; la dependencia va sólo de aquí a db.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import aventura as av
import competir as comp
import db
import objetos as obj
import simulacion as sim

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
) -> ResultadoViaje:
    """Confirma el viaje sobre la criatura activa actual, antes de publicarlo.

    Las aventuras no tienen ledger histórico; esta frontera sólo evita aplicar
    una vista vieja sobre otra criatura o sobre un estado concurrente.
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
        avanzado = sim.avanzar(actual, ahora)
        nueva, rupturas = av.aplicar_viaje(
            avanzado, salida, ahora, percance
        )
        db._guardar(con, nueva)
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


def _contar_acreditadas(
    con, usuario_id: str, guild_id: str, fecha: str, tipo: str
) -> int:
    return con.execute(
        "SELECT COUNT(*) FROM operaciones_economia "
        "WHERE usuario_id = ? AND guild_id = ? AND fecha_utc = ? "
        "AND tipo = ? AND resultado = 'acreditada'",
        (usuario_id, guild_id, fecha, tipo),
    ).fetchone()[0]


def _resolver_recompensa(
    con, usuario_id: str, guild_id: str, fecha: str,
    tipo: str, monto: int, limite: int,
) -> tuple[int, int, bool]:
    usados = _contar_acreditadas(con, usuario_id, guild_id, fecha, tipo)
    acreditada = usados < limite
    delta = monto if acreditada else 0
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
    tipo: str, monto: int, limite: int, solicitud: str,
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


def _envolver_cuidado(
    resultado: sim.ResultadoAccion, *, delta: int = 0,
    delta_evolucion: int = 0, usados: int = 0,
    evolucion_usadas: int = 0, topada: bool = False,
    sin_efecto: bool = False,
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
        criatura = sim.avanzar(criatura, ahora)
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
            usados=usados,
            evolucion_usadas=evolucion_usadas,
            topada=topada,
        )


def _replay_competencia(
    con, evento_id: str, usuarios: tuple[str, ...],
    guild_id: str, solicitud: str,
) -> ResultadoCompetencia | None:
    filas = con.execute(
        "SELECT * FROM operaciones_economia WHERE evento_id = ? "
        "AND guild_id = ? AND tipo = 'competencia'",
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
            "SELECT resultado, delta_asciicoins FROM operaciones_economia "
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
                con, usuario_id, guild_id, fila["fecha_utc"], "competencia"
            ),
            evolucion_usadas=(
                _contar_acreditadas(
                    con, usuario_id, guild_id, fila["fecha_utc"], "evolucion"
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
        criaturas = tuple(sim.avanzar(criatura, ahora) for criatura in antes)
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

        stat = comp.STATS[tipo]
        encuentro = comp.enfrentar(
            [
                comp.competidor_de(
                    criatura, tipo,
                    db.efecto_activo_en(con, criatura.id, stat, ahora),
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
                stat,
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
