"""Economía transaccional: saldos, límites diarios y operaciones idempotentes.

Este módulo concentra las reglas monetarias. ``db`` conserva el esquema, las
migraciones y los repositorios de dominio; la dependencia va sólo de aquí a db.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

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
    subidas: tuple[str, ...] = ()
    etapa_anterior: str | None = None
    delta_asciicoins: int = 0
    delta_evolucion: int = 0
    usados: int = 0
    limite: int = TOPE_CUIDADOS
    evolucion_usadas: int = 0
    replay: bool = False
    topada: bool = False

    @property
    def evoluciono(self) -> bool:
        return (
            self.etapa_anterior is not None
            and self.etapa_anterior != self.criatura.etapa
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
    return delta, usados + int(acreditada), not acreditada


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
) -> ResultadoCuidado:
    return ResultadoCuidado(
        criatura=resultado.criatura,
        mensaje=resultado.mensaje,
        ok=resultado.ok,
        espera=resultado.espera,
        subidas=tuple(resultado.subidas),
        etapa_anterior=resultado.etapa_anterior,
        delta_asciicoins=delta + delta_evolucion,
        delta_evolucion=delta_evolucion,
        usados=usados,
        evolucion_usadas=evolucion_usadas,
        topada=topada,
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
                criatura, "Tu criatura ya no está entre nosotros.", ok=False
            )

        espera = db.espera_en(con, criatura.id, accion, ahora)
        if espera and not sim.puede_saltarse_espera(criatura, accion):
            db._guardar(con, criatura)
            return ResultadoCuidado(criatura, "", ok=False, espera=espera)

        resultado = sim.aplicar_accion(criatura, accion, ahora)
        db._guardar(con, resultado.criatura)
        if not resultado.ok or accion == sim.ACTUALIZAR or resultado.criatura == criatura:
            return _envolver_cuidado(resultado)

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
