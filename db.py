"""Persistencia en SQLite. Sigue el patrón de rowino_web/db.py.

Las consultas son síncronas dentro del bucle de eventos de discord.py. Con una
base de datos local de unas pocas decenas de filas cada operación tarda menos de
un milisegundo, así que meter una capa async sólo añadiría complejidad.

Detalle importante: en cada guardado se recalcula `muere_en`, el instante en que
el hambre llegará a cero. Como el hambre decae linealmente, ese momento se
despeja con una fórmula cerrada, y el bucle que mata criaturas se reduce a un
`WHERE muere_en <= ahora` en vez de recorrer y simular todas las filas.
"""
from __future__ import annotations

import random
import sqlite3
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config
import especies as esp
import personalidad as per
import simulacion as sim

RUTA: Path = config.RUTA_BD

# El esquema va en dos trozos porque el orden importa: primero las tablas,
# después las migraciones que añaden columnas nuevas, y sólo entonces los
# índices — que referencian esas columnas y fallarían si se crearan antes.
SCHEMA_TABLAS = """
CREATE TABLE IF NOT EXISTS criaturas (
    id INTEGER PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    especie TEXT NOT NULL,
    nombre TEXT NOT NULL,
    genero TEXT NOT NULL DEFAULT 'macho',
    caracter TEXT NOT NULL DEFAULT '',
    nacida_en TEXT NOT NULL,
    actualizada_en TEXT NOT NULL,
    muere_en TEXT,
    avisa_en TEXT,
    avisada INTEGER NOT NULL DEFAULT 0,
    muerta_en TEXT,
    causa_muerte TEXT,
    hambre REAL NOT NULL DEFAULT 100,
    animo REAL NOT NULL DEFAULT 100,
    limpieza REAL NOT NULL DEFAULT 100,
    base_fuerza INTEGER NOT NULL,
    base_velocidad INTEGER NOT NULL,
    base_salud INTEGER NOT NULL,
    ent_fuerza INTEGER NOT NULL DEFAULT 0,
    ent_velocidad INTEGER NOT NULL DEFAULT 0,
    ent_salud INTEGER NOT NULL DEFAULT 0,
    niv_fuerza INTEGER NOT NULL DEFAULT 0,
    niv_velocidad INTEGER NOT NULL DEFAULT 0,
    niv_salud INTEGER NOT NULL DEFAULT 0,
    xp INTEGER NOT NULL DEFAULT 0,
    nivel INTEGER NOT NULL DEFAULT 1,
    victorias INTEGER NOT NULL DEFAULT 0,
    derrotas INTEGER NOT NULL DEFAULT 0,
    pantalla_msg_id TEXT,
    canal_id TEXT
);

CREATE TABLE IF NOT EXISTS cooldowns (
    criatura_id INTEGER NOT NULL REFERENCES criaturas(id),
    accion TEXT NOT NULL,
    hasta TEXT NOT NULL,
    PRIMARY KEY (criatura_id, accion)
);

-- Lo que se ha hablado con cada criatura. Va atada a criatura_id, así que
-- cuando una muere y nace otra la relación empieza de cero sin código extra.
CREATE TABLE IF NOT EXISTS conversaciones (
    id INTEGER PRIMARY KEY,
    criatura_id INTEGER NOT NULL REFERENCES criaturas(id),
    rol TEXT NOT NULL,          -- 'user' | 'assistant'
    contenido TEXT NOT NULL,
    cuando TEXT NOT NULL
);

-- Un registro por mensaje enviado a la IA, para el límite por hora. Son
-- créditos de una cuenta de verdad: sin esto, uno se los funde en una tarde.
CREATE TABLE IF NOT EXISTS uso_ia (
    id INTEGER PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    cuando TEXT NOT NULL
);
"""

SCHEMA_INDICES = """
-- Una sola criatura viva por persona y servidor. Lo garantiza la base de
-- datos, no el código: así dos clics simultáneos en /huevo no pueden colar dos.
CREATE UNIQUE INDEX IF NOT EXISTS una_viva
    ON criaturas(usuario_id, guild_id) WHERE muerta_en IS NULL;

CREATE INDEX IF NOT EXISTS idx_muere
    ON criaturas(muere_en) WHERE muerta_en IS NULL;

CREATE INDEX IF NOT EXISTS idx_avisa
    ON criaturas(avisa_en) WHERE muerta_en IS NULL AND avisada = 0;

CREATE INDEX IF NOT EXISTS idx_conversacion
    ON conversaciones(criatura_id, id);

CREATE INDEX IF NOT EXISTS idx_uso_ia
    ON uso_ia(usuario_id, cuando);
"""

CAMPOS = (
    "usuario_id", "guild_id", "especie", "nombre", "genero", "caracter",
    "nacida_en", "actualizada_en",
    "muerta_en", "causa_muerte", "avisada", "hambre", "animo", "limpieza",
    "base_fuerza", "base_velocidad", "base_salud",
    "ent_fuerza", "ent_velocidad", "ent_salud",
    "niv_fuerza", "niv_velocidad", "niv_salud",
    "xp", "nivel", "victorias", "derrotas", "pantalla_msg_id", "canal_id",
)


def conectar() -> sqlite3.Connection:
    con = sqlite3.connect(RUTA)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


# Columnas añadidas después de la primera versión. Se aplican con ALTER TABLE
# sobre bases de datos que ya tienen criaturas dentro, para no perderlas.
MIGRACIONES = (
    ("avisa_en", "ALTER TABLE criaturas ADD COLUMN avisa_en TEXT"),
    ("avisada", "ALTER TABLE criaturas ADD COLUMN avisada INTEGER NOT NULL DEFAULT 0"),
    ("canal_id", "ALTER TABLE criaturas ADD COLUMN canal_id TEXT"),
    # Las criaturas anteriores al género se quedan macho, que es lo pedido, y
    # eso ya lo hace el DEFAULT. El carácter NO puede ir en el DEFAULT porque
    # saldrían todas iguales: se sortea fila a fila en `_migrar()`.
    ("genero",
     f"ALTER TABLE criaturas ADD COLUMN genero TEXT NOT NULL DEFAULT '{esp.MACHO}'"),
    ("caracter", "ALTER TABLE criaturas ADD COLUMN caracter TEXT NOT NULL DEFAULT ''"),
)


def inicializar() -> None:
    with conectar() as con:
        con.executescript(SCHEMA_TABLAS)
        _migrar(con)
        con.executescript(SCHEMA_INDICES)


def _migrar(con: sqlite3.Connection) -> None:
    existentes = {f["name"] for f in con.execute("PRAGMA table_info(criaturas)")}
    for columna, sentencia in MIGRACIONES:
        if columna not in existentes:
            con.execute(sentencia)

    # Las criaturas anteriores a esta versión no tienen calculado su avisa_en.
    for fila in con.execute(
        "SELECT * FROM criaturas WHERE muerta_en IS NULL AND avisa_en IS NULL"
    ).fetchall():
        criatura = _a_criatura(fila)
        con.execute(
            "UPDATE criaturas SET avisa_en = ? WHERE id = ?",
            (sim.momento_de_aviso(criatura).isoformat(), criatura.id),
        )

    # Una personalidad al azar para cada criatura anterior al carácter. Fila a
    # fila y no de una sola pasada: con un UPDATE global les tocaría la misma a
    # todas, que es justo lo que no se quiere.
    rng = random.Random()
    for (criatura_id,) in con.execute(
        "SELECT id FROM criaturas WHERE caracter = ''"
    ).fetchall():
        con.execute(
            "UPDATE criaturas SET caracter = ? WHERE id = ?",
            (per.tirar_caracter(rng), criatura_id),
        )


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


# --- Conversión entre filas y objetos --------------------------------------

def _fecha(valor: str | None) -> datetime | None:
    return datetime.fromisoformat(valor) if valor else None


def _a_criatura(fila: sqlite3.Row) -> sim.Criatura:
    datos = {c: fila[c] for c in CAMPOS}
    for campo in ("nacida_en", "actualizada_en", "muerta_en"):
        datos[campo] = _fecha(datos[campo])
    datos["avisada"] = bool(datos["avisada"])
    return sim.Criatura(id=fila["id"], **datos)


def _a_valores(criatura: sim.Criatura) -> dict:
    datos = {c: getattr(criatura, c) for c in CAMPOS}
    for campo in ("nacida_en", "actualizada_en", "muerta_en"):
        valor = datos[campo]
        datos[campo] = valor.isoformat() if valor else None
    datos["avisada"] = int(criatura.avisada)
    # Los dos instantes se recalculan en cada guardado: dependen de la comida
    # actual y de la salud, que cambian con cada acción.
    datos["muere_en"] = (
        sim.momento_de_muerte(criatura).isoformat() if criatura.viva else None
    )
    datos["avisa_en"] = (
        sim.momento_de_aviso(criatura).isoformat() if criatura.viva else None
    )
    return datos


# --- Criaturas -------------------------------------------------------------

def criatura_viva(usuario_id: str, guild_id: str) -> sim.Criatura | None:
    with conectar() as con:
        fila = con.execute(
            "SELECT * FROM criaturas "
            "WHERE usuario_id = ? AND guild_id = ? AND muerta_en IS NULL",
            (usuario_id, guild_id),
        ).fetchone()
    return _a_criatura(fila) if fila else None


def criatura_por_pantalla(mensaje_id: str) -> sim.Criatura | None:
    """De quién es la pantalla que se acaba de pulsar.

    Sirve para no dejar que alguien actúe sobre su propia criatura pulsando en
    la pantalla de otra persona: vería aparecer una mascota que no es la de ese
    mensaje y no entendería nada.
    """
    with conectar() as con:
        fila = con.execute(
            "SELECT * FROM criaturas WHERE pantalla_msg_id = ?", (mensaje_id,)
        ).fetchone()
    return _a_criatura(fila) if fila else None


def obtener(criatura_id: int) -> sim.Criatura | None:
    with conectar() as con:
        fila = con.execute(
            "SELECT * FROM criaturas WHERE id = ?", (criatura_id,)
        ).fetchone()
    return _a_criatura(fila) if fila else None


def crear(
    usuario_id: str,
    guild_id: str,
    especie: str,
    nombre: str,
    stats: tuple[int, int, int],
    ahora: datetime,
    genero: str = esp.MACHO,
    caracter: str = esp.CARACTER_POR_DEFECTO,
    canal_id: str | None = None,
) -> sim.Criatura:
    """Registra una criatura recién nacida.

    Si ya hay una viva, el índice único hace saltar `sqlite3.IntegrityError`:
    es la defensa contra dos `/huevo` a la vez.
    """
    fuerza, velocidad, salud = stats
    nueva = sim.Criatura(
        id=0, usuario_id=usuario_id, guild_id=guild_id, especie=especie,
        nombre=nombre, genero=genero, caracter=caracter,
        nacida_en=ahora, actualizada_en=ahora,
        base_fuerza=fuerza, base_velocidad=velocidad, base_salud=salud,
        canal_id=canal_id,
    )
    valores = _a_valores(nueva)
    columnas = list(valores)
    marcadores = ", ".join(f":{c}" for c in columnas)

    with conectar() as con:
        cursor = con.execute(
            f"INSERT INTO criaturas ({', '.join(columnas)}) VALUES ({marcadores})",
            valores,
        )
        nuevo_id = cursor.lastrowid

    return replace(nueva, id=nuevo_id)


def guardar(criatura: sim.Criatura) -> None:
    valores = _a_valores(criatura)
    valores["id"] = criatura.id
    asignaciones = ", ".join(f"{c} = :{c}" for c in valores if c != "id")
    with conectar() as con:
        con.execute(f"UPDATE criaturas SET {asignaciones} WHERE id = :id", valores)


def guardar_pantalla(
    criatura_id: int, mensaje_id: str | None, canal_id: str | None = None
) -> None:
    """Apunta dónde está la pantalla viva y en qué canal.

    El canal se actualiza en cada publicación, así que los avisos siguen a la
    persona si se cambia de canal a media partida.
    """
    with conectar() as con:
        if canal_id is None:
            con.execute(
                "UPDATE criaturas SET pantalla_msg_id = ? WHERE id = ?",
                (mensaje_id, criatura_id),
            )
        else:
            con.execute(
                "UPDATE criaturas SET pantalla_msg_id = ?, canal_id = ? WHERE id = ?",
                (mensaje_id, canal_id, criatura_id),
            )


def pendientes_de_morir(ahora: datetime) -> list[sim.Criatura]:
    """Criaturas vivas cuya hora de muerte ya pasó. Una sola consulta."""
    with conectar() as con:
        filas = con.execute(
            "SELECT * FROM criaturas "
            "WHERE muerta_en IS NULL AND muere_en IS NOT NULL AND muere_en <= ?",
            (ahora.isoformat(),),
        ).fetchall()
    return [_a_criatura(f) for f in filas]


def pendientes_de_aviso(ahora: datetime) -> list[sim.Criatura]:
    """Criaturas vivas que han bajado del umbral de comida y aún no lo saben."""
    with conectar() as con:
        filas = con.execute(
            "SELECT * FROM criaturas "
            "WHERE muerta_en IS NULL AND avisada = 0 "
            "AND avisa_en IS NOT NULL AND avisa_en <= ?",
            (ahora.isoformat(),),
        ).fetchall()
    return [_a_criatura(f) for f in filas]


# --- Cooldowns -------------------------------------------------------------

def espera_de(criatura_id: int, accion: str, ahora: datetime) -> timedelta:
    with conectar() as con:
        fila = con.execute(
            "SELECT hasta FROM cooldowns WHERE criatura_id = ? AND accion = ?",
            (criatura_id, accion),
        ).fetchone()
    if not fila:
        return timedelta(0)
    return max(timedelta(0), datetime.fromisoformat(fila["hasta"]) - ahora)


def esperas(criatura_id: int, ahora: datetime) -> dict[str, timedelta]:
    """Lo que falta para cada acción, para pintarlo en el subtexto."""
    with conectar() as con:
        filas = con.execute(
            "SELECT accion, hasta FROM cooldowns WHERE criatura_id = ?",
            (criatura_id,),
        ).fetchall()
    guardados = {f["accion"]: datetime.fromisoformat(f["hasta"]) for f in filas}
    return {
        accion: max(timedelta(0), guardados.get(accion, ahora) - ahora)
        for accion in sim.ACCIONES_DE_CUIDADO
    }


def poner_cooldown(criatura_id: int, accion: str, ahora: datetime) -> None:
    duracion = sim.COOLDOWNS.get(accion, timedelta(0))
    if not duracion:
        return
    with conectar() as con:
        con.execute(
            "INSERT INTO cooldowns (criatura_id, accion, hasta) VALUES (?, ?, ?) "
            "ON CONFLICT(criatura_id, accion) DO UPDATE SET hasta = excluded.hasta",
            (criatura_id, accion, (ahora + duracion).isoformat()),
        )


# --- Listados --------------------------------------------------------------

def vivas_del_servidor(guild_id: str) -> list[sim.Criatura]:
    """Todas las criaturas vivas de un servidor, para la escena del jardín."""
    with conectar() as con:
        filas = con.execute(
            "SELECT * FROM criaturas WHERE guild_id = ? AND muerta_en IS NULL "
            "ORDER BY nacida_en",
            (guild_id,),
        ).fetchall()
    return [_a_criatura(f) for f in filas]


def ranking(guild_id: str, limite: int = 10) -> list[sim.Criatura]:
    with conectar() as con:
        filas = con.execute(
            "SELECT * FROM criaturas WHERE guild_id = ? AND muerta_en IS NULL "
            "ORDER BY victorias DESC, nivel DESC, xp DESC LIMIT ?",
            (guild_id, limite),
        ).fetchall()
    return [_a_criatura(f) for f in filas]


# --- Conversación ----------------------------------------------------------

# 8 intercambios: bastante para seguir el hilo de una charla sin que el prompt
# (y con él el gasto) crezca sin control.
TURNOS_RECORDADOS = 16


def historial(criatura_id: int, limite: int = TURNOS_RECORDADOS) -> list[dict]:
    """Los últimos turnos, en orden cronológico y listos para el modelo."""
    with conectar() as con:
        filas = con.execute(
            "SELECT rol, contenido FROM conversaciones WHERE criatura_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (criatura_id, limite),
        ).fetchall()
    return [{"role": f["rol"], "content": f["contenido"]} for f in reversed(filas)]


def guardar_turnos(
    criatura_id: int, mensaje: str, respuesta: str, ahora: datetime
) -> None:
    """Guarda el intercambio y poda lo viejo, todo en una transacción."""
    with conectar() as con:
        con.executemany(
            "INSERT INTO conversaciones (criatura_id, rol, contenido, cuando) "
            "VALUES (?, ?, ?, ?)",
            [
                (criatura_id, "user", mensaje, ahora.isoformat()),
                (criatura_id, "assistant", respuesta, ahora.isoformat()),
            ],
        )
        con.execute(
            "DELETE FROM conversaciones WHERE criatura_id = ? AND id NOT IN "
            "(SELECT id FROM conversaciones WHERE criatura_id = ? "
            " ORDER BY id DESC LIMIT ?)",
            (criatura_id, criatura_id, TURNOS_RECORDADOS),
        )


def olvidar(criatura_id: int) -> None:
    with conectar() as con:
        con.execute("DELETE FROM conversaciones WHERE criatura_id = ?",
                    (criatura_id,))


# --- Límite de uso de la IA ------------------------------------------------

def registrar_uso_ia(usuario_id: str, ahora: datetime) -> None:
    with conectar() as con:
        con.execute("INSERT INTO uso_ia (usuario_id, cuando) VALUES (?, ?)",
                    (usuario_id, ahora.isoformat()))


def uso_ia_ultima_hora(usuario_id: str, ahora: datetime) -> int:
    desde = (ahora - timedelta(hours=1)).isoformat()
    with conectar() as con:
        fila = con.execute(
            "SELECT COUNT(*) AS n FROM uso_ia WHERE usuario_id = ? AND cuando > ?",
            (usuario_id, desde),
        ).fetchone()
    return fila["n"]


def ultimo_uso_ia(usuario_id: str) -> datetime | None:
    with conectar() as con:
        fila = con.execute(
            "SELECT MAX(cuando) AS ultimo FROM uso_ia WHERE usuario_id = ?",
            (usuario_id,),
        ).fetchone()
    return _fecha(fila["ultimo"]) if fila and fila["ultimo"] else None


def limpiar_uso_ia(ahora: datetime) -> int:
    """Borra los registros que ya no cuentan para el límite."""
    desde = (ahora - timedelta(hours=2)).isoformat()
    with conectar() as con:
        return con.execute("DELETE FROM uso_ia WHERE cuando <= ?", (desde,)).rowcount


# --- Listados --------------------------------------------------------------

def cementerio(guild_id: str, limite: int = 10) -> list[sim.Criatura]:
    with conectar() as con:
        filas = con.execute(
            "SELECT * FROM criaturas WHERE guild_id = ? AND muerta_en IS NOT NULL "
            "ORDER BY muerta_en DESC LIMIT ?",
            (guild_id, limite),
        ).fetchall()
    return [_a_criatura(f) for f in filas]
