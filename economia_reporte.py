"""Informe local agregado de la economía, sin IDs de usuarios ni servidores."""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from statistics import median

import config
import economia

TIPOS_RECOMPENSA = ("cuidado", "evolucion", "competencia")
LIMITES_RECOMPENSA = {
    "cuidado": economia.TOPE_CUIDADOS,
    "evolucion": economia.TOPE_EVOLUCIONES,
    "competencia": economia.TOPE_COMPETENCIAS,
}


def _conectar(ruta: str | Path) -> sqlite3.Connection:
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    return con


def datos_reporte(ruta: str | Path, desde: date, hasta: date) -> dict:
    if desde > hasta:
        raise ValueError("intervalo UTC inválido: desde es posterior a hasta")
    with closing(_conectar(ruta)) as con:
        # Una sola vista de lectura: una operación concurrente no puede quedar
        # partida entre el saldo leído y el delta usado para reconciliarlo.
        con.execute("BEGIN")
        operaciones = con.execute(
            "SELECT * FROM operaciones_economia "
            "WHERE fecha_utc BETWEEN ? AND ? ORDER BY fecha_utc, tipo, solicitud",
            (desde.isoformat(), hasta.isoformat()),
        ).fetchall()
        monederos = con.execute(
            "SELECT asciicoins, asciigems FROM monederos"
        ).fetchall()
        delta_total = con.execute(
            "SELECT COALESCE(SUM(delta_asciicoins), 0) FROM operaciones_economia"
        ).fetchone()[0]

    activos = {(f["usuario_id"], f["guild_id"]) for f in operaciones}
    dias_activos = {
        (f["fecha_utc"], f["usuario_id"], f["guild_id"]) for f in operaciones
    }
    por_dia: dict[str, dict[str, int]] = {}
    for fila in operaciones:
        resumen = por_dia.setdefault(
            fila["fecha_utc"], {"emitido": 0, "gastado": 0, "neto": 0}
        )
        delta = fila["delta_asciicoins"]
        resumen["emitido"] += max(0, delta)
        resumen["gastado"] += max(0, -delta)
        resumen["neto"] += delta

    recompensas = [f for f in operaciones if f["tipo"] in TIPOS_RECOMPENSA]
    grupos: dict[tuple[str, str, str, str], int] = {}
    for fila in recompensas:
        if fila["resultado"] == "acreditada":
            clave = (
                fila["fecha_utc"], fila["usuario_id"],
                fila["guild_id"], fila["tipo"],
            )
            grupos[clave] = grupos.get(clave, 0) + 1
    por_tipo = {}
    alcanzaron_global = set()
    for tipo in TIPOS_RECOMPENSA:
        filas_tipo = [f for f in recompensas if f["tipo"] == tipo]
        jornadas = {
            clave for clave, creditos in grupos.items()
            if clave[3] == tipo and creditos >= LIMITES_RECOMPENSA[tipo]
        }
        monederos_tipo = {(u, g) for _fecha, u, g, _tipo in jornadas}
        alcanzaron_global.update(monederos_tipo)
        por_tipo[tipo] = {
            "acreditadas": sum(f["resultado"] == "acreditada" for f in filas_tipo),
            "topadas": sum(f["resultado"] == "topada" for f in filas_tipo),
            "monederos_que_alcanzaron_tope": len(monederos_tipo),
            "jornadas_monedero_que_alcanzaron_tope": len(jornadas),
        }

    compras: dict[str, dict[str, int]] = {}
    for fila in operaciones:
        if fila["tipo"] == "compra" and fila["resultado"] == "comprada":
            item = compras.setdefault(fila["solicitud"], {"cantidad": 0, "gastado": 0})
            item["cantidad"] += 1
            item["gastado"] += -fila["delta_asciicoins"]

    saldos = sorted(f["asciicoins"] for f in monederos)
    estadisticas = (
        {
            "mediana": float(median(saldos)),
            "p90": saldos[math.ceil(len(saldos) * 0.9) - 1],
            "maximo": saldos[-1],
        }
        if saldos else {"mediana": 0.0, "p90": 0, "maximo": 0}
    )
    esperado = 50 * len(monederos) + delta_total
    suma_saldos = sum(saldos)
    return {
        "intervalo_utc": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "actividad": {
            "monederos": len(monederos),
            "monederos_activos": len(activos),
            "dias_monedero_activos": len(dias_activos),
        },
        "por_dia": dict(sorted(por_dia.items())),
        "recompensas": {
            "acreditadas": sum(f["resultado"] == "acreditada" for f in recompensas),
            "topadas": sum(f["resultado"] == "topada" for f in recompensas),
            "monederos_que_alcanzaron_tope": len(alcanzaron_global),
            "por_tipo": por_tipo,
        },
        "compras": dict(sorted(compras.items())),
        "intentos_saldo_insuficiente": sum(
            f["tipo"] == "compra" and f["resultado"] == "saldo_insuficiente"
            for f in operaciones
        ),
        "saldos_asciicoins": estadisticas,
        "reconciliacion": {
            "alcance": "historico_global",
            "esperado": esperado,
            "saldos": suma_saldos,
            "cuadra": esperado == suma_saldos,
        },
        "asciigems_fuera_de_50": sum(f["asciigems"] != 50 for f in monederos),
    }


def render_texto(datos: dict) -> str:
    actividad = datos["actividad"]
    recompensas = datos["recompensas"]
    reconciliacion = datos["reconciliacion"]
    lineas = [
        "REPORTE DE ECONOMÍA (UTC)",
        f"Intervalo: {datos['intervalo_utc']['desde']}..{datos['intervalo_utc']['hasta']}",
        (
            f"Actividad: {actividad['monederos_activos']} monederos activos; "
            f"{actividad['dias_monedero_activos']} días-monedero; "
            f"{actividad['monederos']} monederos totales"
        ),
        "Por día:",
    ]
    for dia, valores in datos["por_dia"].items():
        lineas.append(
            f"  {dia}: emitido={valores['emitido']} gastado={valores['gastado']} "
            f"neto={valores['neto']}"
        )
    lineas.append(
        f"Recompensas: acreditadas={recompensas['acreditadas']} "
        f"topadas={recompensas['topadas']}"
    )
    for tipo in TIPOS_RECOMPENSA:
        valores = recompensas["por_tipo"][tipo]
        lineas.append(
            f"  {tipo}: acreditadas={valores['acreditadas']} "
            f"topadas={valores['topadas']}"
        )
    lineas.append("Compras:")
    for objeto, valores in datos["compras"].items():
        lineas.append(
            f"  {objeto}: cantidad={valores['cantidad']} gastado={valores['gastado']}"
        )
    saldos = datos["saldos_asciicoins"]
    lineas += [
        f"Intentos con saldo insuficiente: {datos['intentos_saldo_insuficiente']}",
        (
            f"Saldos asciicoins: mediana={saldos['mediana']} "
            f"p90={saldos['p90']} máximo={saldos['maximo']}"
        ),
        (
            "Reconciliación histórica global: "
            f"{'OK' if reconciliacion['cuadra'] else 'ERROR'} "
            f"({reconciliacion['esperado']} = {reconciliacion['saldos']})"
        ),
        f"Asciigems fuera de 50: {datos['asciigems_fuera_de_50']}",
    ]
    return "\n".join(lineas)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=config.RUTA_BD)
    parser.add_argument("--desde", type=date.fromisoformat, required=True)
    parser.add_argument("--hasta", type=date.fromisoformat, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    datos = datos_reporte(args.db, args.desde, args.hasta)
    print(
        json.dumps(datos, ensure_ascii=False, sort_keys=True, indent=2)
        if args.json else render_texto(datos)
    )


if __name__ == "__main__":
    main()
