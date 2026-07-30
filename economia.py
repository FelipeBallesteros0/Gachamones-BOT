"""Economía transaccional: saldos, límites diarios y operaciones idempotentes.

Este módulo concentra las reglas monetarias. ``db`` conserva el esquema, las
migraciones y los repositorios de dominio; la dependencia va sólo de aquí a db.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import db
import objetos as obj

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
