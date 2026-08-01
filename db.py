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
from collections.abc import Collection
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config
import especies as esp
import logros as lgr
import objetos as obj
import personalidad as per
import simulacion as sim

RUTA: Path = config.RUTA_BD

# Cuántos gachamones puede tener una persona por servidor. Uno activo y el resto
# en la incubadora. El primero sale de `/huevo`; los demás sólo reclutándolos.
#
# Subió de 3 a 10 para que coleccionar sea un objetivo largo. Lo que de verdad
# cambia con este número es `/aventura`: con el plantel lleno los salvajes se
# convierten en objetos, así que el tope decide cuánto dura la fase de reclutar.
# Medido, se recluta en el 5,5 % de las aventuras y hay 37 minutos entre una y
# otra: llenar dos huecos son unas 22 horas de juego y llenar nueve, unas 100.
MAXIMO_PLANTEL = 10

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
    ten_fuerza REAL NOT NULL DEFAULT 0,
    ten_velocidad REAL NOT NULL DEFAULT 0,
    ten_salud REAL NOT NULL DEFAULT 0,
    historial_vetas TEXT NOT NULL DEFAULT '',
    xp INTEGER NOT NULL DEFAULT 0,
    nivel INTEGER NOT NULL DEFAULT 1,
    victorias INTEGER NOT NULL DEFAULT 0,
    derrotas INTEGER NOT NULL DEFAULT 0,
    pantalla_msg_id TEXT,
    canal_id TEXT,
    activa INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS cooldowns (
    criatura_id INTEGER NOT NULL REFERENCES criaturas(id),
    accion TEXT NOT NULL,
    hasta TEXT NOT NULL,
    PRIMARY KEY (criatura_id, accion)
);

-- Las esperas que son de quien juega y no de su gachamon. Hoy sólo la aventura:
-- ahí vas TÚ con él, así que cambiar de activo no puede saltarse el descanso;
-- con la tabla de arriba se salía tres veces seguidas teniendo tres gachamones.
-- Cuidar y competir sí son suyos —es él quien come y quien pelea— y siguen allí.
CREATE TABLE IF NOT EXISTS cooldowns_persona (
    usuario_id TEXT NOT NULL,
    guild_id   TEXT NOT NULL,
    accion     TEXT NOT NULL,
    hasta      TEXT NOT NULL,
    PRIMARY KEY (usuario_id, guild_id, accion)
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

-- El monedero y los objetos son de la PERSONA, no de la criatura: así lo
-- comprado sobrevive a la muerte de una mascota y al nacimiento de la
-- siguiente. Por servidor, como todo lo demás.
CREATE TABLE IF NOT EXISTS inventario (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    objeto TEXT NOT NULL,
    cantidad INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (usuario_id, guild_id, objeto)
);

-- Los efectos sí van atados a la criatura: es ella la que se envalentona, y
-- cuando muere se los lleva. La clave primaria (criatura_id, stat) **es** la
-- regla de «una poción activa por estadística»: al beber otra, el ON CONFLICT
-- sustituye a la anterior sin que haya que vigilarlo desde el código.
CREATE TABLE IF NOT EXISTS efectos (
    criatura_id INTEGER NOT NULL REFERENCES criaturas(id),
    stat TEXT NOT NULL,          -- 'fuerza' | 'velocidad'
    bonus INTEGER NOT NULL,
    hasta TEXT NOT NULL,
    PRIMARY KEY (criatura_id, stat)
);

-- Lo que lleva hecho cada gachamon: carreras ganadas, aventuras, biomas
-- pisados. Es una tabla de clave y valor y no una columna por contador porque
-- los logros se añaden a menudo: así uno nuevo se escribe en `logros.py` y no
-- toca el esquema. Va atada a `criatura_id`, como los efectos: el marcador es
-- suyo y se lo lleva al morirse.
CREATE TABLE IF NOT EXISTS marcador (
    criatura_id INTEGER NOT NULL REFERENCES criaturas(id),
    clave TEXT NOT NULL,
    valor INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (criatura_id, clave)
);

-- Los logros conseguidos, con la fecha de verdad. La clave primaria **es** la
-- garantía de que ninguno se cobra dos veces: los contadores siguen subiendo
-- después de desbloquear «Velocista», así que sin esto se pagaría en cada
-- carrera. El INSERT que no entra es exactamente el que ya estaba.
CREATE TABLE IF NOT EXISTS logros (
    criatura_id INTEGER NOT NULL REFERENCES criaturas(id),
    clave TEXT NOT NULL,
    cuando TEXT NOT NULL,
    PRIMARY KEY (criatura_id, clave)
);

CREATE TABLE IF NOT EXISTS operaciones_economia (
    evento_id        TEXT NOT NULL,
    usuario_id       TEXT NOT NULL,
    guild_id         TEXT NOT NULL,
    tipo             TEXT NOT NULL CHECK (tipo IN ('cuidado','evolucion','competencia','compra')),
    fecha_utc        TEXT NOT NULL,
    resultado        TEXT NOT NULL CHECK (resultado IN ('acreditada','topada','comprada','saldo_insuficiente')),
    delta_asciicoins INTEGER NOT NULL,
    solicitud        TEXT NOT NULL CHECK (length(solicitud) > 0),
    CHECK (
        (resultado = 'acreditada' AND tipo IN ('cuidado','evolucion','competencia') AND delta_asciicoins > 0) OR
        (resultado = 'topada' AND tipo IN ('cuidado','evolucion','competencia') AND delta_asciicoins = 0) OR
        (resultado = 'comprada' AND tipo = 'compra' AND delta_asciicoins < 0) OR
        (resultado = 'saldo_insuficiente' AND tipo = 'compra' AND delta_asciicoins = 0)
    ),
    PRIMARY KEY (evento_id, usuario_id, guild_id, tipo)
);
"""

SCHEMA_INDICES = """
-- Una sola criatura ACTIVA por persona y servidor. Antes era «una sola viva»;
-- desde que se puede tener un plantel de tres, lo que hay que garantizar es que
-- no haya dos recibiendo los comandos a la vez. Lo sigue garantizando la base de
-- datos y no el código, que era el motivo original: dos clics simultáneos no
-- pueden dejar dos activas. El tope de tres no cabe en un índice y se comprueba
-- en `crear()`.
CREATE UNIQUE INDEX IF NOT EXISTS una_activa
    ON criaturas(usuario_id, guild_id) WHERE muerta_en IS NULL AND activa = 1;

CREATE INDEX IF NOT EXISTS idx_muere
    ON criaturas(muere_en) WHERE muerta_en IS NULL;

CREATE INDEX IF NOT EXISTS idx_avisa
    ON criaturas(avisa_en) WHERE muerta_en IS NULL AND avisada = 0;

CREATE INDEX IF NOT EXISTS idx_conversacion
    ON conversaciones(criatura_id, id);

CREATE INDEX IF NOT EXISTS idx_uso_ia
    ON uso_ia(usuario_id, cuando);

CREATE INDEX IF NOT EXISTS idx_cupo
    ON operaciones_economia(usuario_id, guild_id, fecha_utc, tipo);
"""

DDL_MONEDEROS = """
CREATE TABLE monederos (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    asciicoins INTEGER NOT NULL DEFAULT 50 CHECK (asciicoins >= 0),
    asciigems INTEGER NOT NULL DEFAULT 50 CHECK (asciigems >= 0),
    PRIMARY KEY (usuario_id, guild_id)
)
"""

COLUMNAS_MONEDERO = ("usuario_id", "guild_id", "asciicoins", "asciigems")
COLUMNAS_MONEDERO_LEGACY = ("usuario_id", "guild_id", "gemas")

CAMPOS = (
    "usuario_id", "guild_id", "especie", "nombre", "genero", "caracter",
    "nacida_en", "actualizada_en",
    "muerta_en", "causa_muerte", "avisada", "hambre", "animo", "limpieza",
    "base_fuerza", "base_velocidad", "base_salud",
    "ent_fuerza", "ent_velocidad", "ent_salud",
    "niv_fuerza", "niv_velocidad", "niv_salud",
    "ten_fuerza", "ten_velocidad", "ten_salud", "historial_vetas",
    "xp", "nivel", "victorias", "derrotas", "pantalla_msg_id", "canal_id",
    "activa",
)


def conectar() -> sqlite3.Connection:
    con = sqlite3.connect(RUTA, timeout=30)
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
    # Las que ya existían son la única de su dueño, así que el DEFAULT 1 las deja
    # activas y no hace falta rellenar nada fila a fila.
    ("activa", "ALTER TABLE criaturas ADD COLUMN activa INTEGER NOT NULL DEFAULT 1"),
    ("ten_fuerza", "ALTER TABLE criaturas ADD COLUMN ten_fuerza REAL NOT NULL DEFAULT 0"),
    ("ten_velocidad", "ALTER TABLE criaturas ADD COLUMN ten_velocidad REAL NOT NULL DEFAULT 0"),
    ("ten_salud", "ALTER TABLE criaturas ADD COLUMN ten_salud REAL NOT NULL DEFAULT 0"),
    ("historial_vetas", "ALTER TABLE criaturas ADD COLUMN historial_vetas TEXT NOT NULL DEFAULT ''"),
)


def inicializar() -> None:
    with conectar() as con:
        con.executescript(SCHEMA_TABLAS)
        _migrar(con)
        con.commit()
        _migrar_monederos(con)
        con.executescript(SCHEMA_INDICES)


def _columnas(con: sqlite3.Connection, tabla: str) -> tuple[str, ...]:
    return tuple(f["name"] for f in con.execute(f"PRAGMA table_info({tabla})"))


def _migrar_monederos(con: sqlite3.Connection) -> None:
    """Publica el monedero dual y reinicia saldos legacy a 50/50, una sola vez."""
    con.execute("BEGIN IMMEDIATE")
    columnas = _columnas(con, "monederos")
    if not columnas:
        con.execute(DDL_MONEDEROS)
    elif columnas == COLUMNAS_MONEDERO_LEGACY:
        con.execute("ALTER TABLE monederos RENAME TO monederos_legacy")
        con.execute(DDL_MONEDEROS)
        con.execute(
            "INSERT INTO monederos "
            "(usuario_id, guild_id, asciicoins, asciigems) "
            "SELECT usuario_id, guild_id, 50, 50 FROM monederos_legacy"
        )
        con.execute("DROP TABLE monederos_legacy")
    elif columnas != COLUMNAS_MONEDERO:
        raise RuntimeError(f"forma de monederos desconocida: {columnas!r}")

    for tabla in ("criaturas", "inventario"):
        con.execute(
            "INSERT OR IGNORE INTO monederos "
            "(usuario_id, guild_id, asciicoins, asciigems) "
            f"SELECT DISTINCT usuario_id, guild_id, 50, 50 FROM {tabla}"
        )
    con.commit()


def _migrar(con: sqlite3.Connection) -> None:
    existentes = {f["name"] for f in con.execute("PRAGMA table_info(criaturas)")}
    for columna, sentencia in MIGRACIONES:
        if columna not in existentes:
            con.execute(sentencia)

    # El índice viejo prohibía una segunda criatura viva; el nuevo sólo prohíbe
    # una segunda ACTIVA. Se tira aquí y no en el script de índices porque
    # `executescript` no borra: hay que quitarlo antes de crear el que lo
    # sustituye, y este paso corre justo entre las tablas y los índices.
    con.execute("DROP INDEX IF EXISTS una_viva")

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

    # La espera de aventura dejó de ser del gachamon y pasó a ser de quien juega.
    # Las que estén corriendo se mudan en vez de tirarse: si no, todo el que
    # estuviera esperando al desplegar se llevaría una aventura gratis. Se coge
    # la más lejana de cada persona, que es la que de verdad le queda.
    con.execute(
        "INSERT INTO cooldowns_persona (usuario_id, guild_id, accion, hasta) "
        "SELECT c.usuario_id, c.guild_id, cd.accion, MAX(cd.hasta) "
        "  FROM cooldowns cd JOIN criaturas c ON c.id = cd.criatura_id "
        " WHERE cd.accion = ? "
        " GROUP BY c.usuario_id, c.guild_id, cd.accion "
        "ON CONFLICT(usuario_id, guild_id, accion) DO UPDATE SET "
        "  hasta = MAX(hasta, excluded.hasta)",
        (sim.AVENTURA,),
    )
    con.execute("DELETE FROM cooldowns WHERE accion = ?", (sim.AVENTURA,))


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
    datos["activa"] = bool(datos["activa"])
    return sim.Criatura(id=fila["id"], **datos)


def _a_valores(criatura: sim.Criatura) -> dict:
    datos = {c: getattr(criatura, c) for c in CAMPOS}
    for campo in ("nacida_en", "actualizada_en", "muerta_en"):
        valor = datos[campo]
        datos[campo] = valor.isoformat() if valor else None
    datos["avisada"] = int(criatura.avisada)
    datos["activa"] = int(criatura.activa)
    # Los dos instantes se recalculan en cada guardado: dependen de la comida
    # actual y de la salud, que cambian con cada acción.
    #
    # A las de la incubadora se les dejan a NULL, y eso es lo único que hace
    # falta para que los bucles de muerte y de aviso las ignoren: los dos piden
    # `IS NOT NULL`, así que no hay que tocar ninguna de las dos consultas.
    corre_el_tiempo = criatura.viva and criatura.activa
    datos["muere_en"] = (
        sim.momento_de_muerte(criatura).isoformat() if corre_el_tiempo else None
    )
    datos["avisa_en"] = (
        sim.momento_de_aviso(criatura).isoformat() if corre_el_tiempo else None
    )
    return datos


# --- Criaturas -------------------------------------------------------------

def criatura_activa(usuario_id: str, guild_id: str) -> sim.Criatura | None:
    """La que recibe los comandos y los botones. Puede haber otras esperando."""
    with conectar() as con:
        return criatura_activa_en(con, usuario_id, guild_id)


def criatura_activa_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str
) -> sim.Criatura | None:
    fila = con.execute(
        "SELECT * FROM criaturas WHERE usuario_id = ? AND guild_id = ? "
        "AND muerta_en IS NULL AND activa = 1",
        (usuario_id, guild_id),
    ).fetchone()
    return _a_criatura(fila) if fila else None


def por_id(criatura_id: int) -> sim.Criatura | None:
    with conectar() as con:
        fila = con.execute(
            "SELECT * FROM criaturas WHERE id = ?", (criatura_id,)
        ).fetchone()
    return _a_criatura(fila) if fila else None


def ascender_de_la_incubadora(
    usuario_id: str, guild_id: str, ahora: datetime
) -> sim.Criatura | None:
    """Saca a la primera de la incubadora si no queda ninguna activa.

    Se llama al morir la activa. Sin esto te quedarías con dos gachamones
    esperando y el bot diciéndote que no tienes ninguno.
    """
    if criatura_activa(usuario_id, guild_id) is not None:
        return None
    # Sólo las que tienen nombre: `activar` no deja salir a un recluta sin
    # bautizar, así que ascender a uno dejaría el plantel sin activa ninguna.
    vivas = [c for c in plantel(usuario_id, guild_id) if c.nombre]
    if not vivas:
        return None
    activar(vivas[0].id, usuario_id, guild_id, ahora)
    return criatura_activa(usuario_id, guild_id)


def plantel(usuario_id: str, guild_id: str) -> list[sim.Criatura]:
    """Las criaturas vivas de una persona, la activa primero."""
    with conectar() as con:
        filas = con.execute(
            "SELECT * FROM criaturas WHERE usuario_id = ? AND guild_id = ? "
            "AND muerta_en IS NULL ORDER BY activa DESC, id",
            (usuario_id, guild_id),
        ).fetchall()
    return [_a_criatura(f) for f in filas]


def activar(
    criatura_id: int, usuario_id: str, guild_id: str, ahora: datetime
) -> bool:
    """Saca una criatura de la incubadora y mete dentro a la que estaba.

    Devuelve si se pudo: pide que la criatura sea de quien la reclama, para que
    un identificador copiado de otro mensaje no active la mascota de otro, y que
    **tenga nombre**. Un recluta se guarda sin nombre y no sale de la incubadora
    hasta que se lo pongan; la comprobación vive aquí y no en la vista porque es
    un invariante del plantel, no una regla de un menú.

    **`actualizada_en` se pone al día aquí**, y este es el único sitio por el que
    se sale de la incubadora. Sin eso, las horas que pasó dormida se le
    aplicarían de golpe en el primer `avanzar` y saldría muerta de hambre.
    """
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        fila = con.execute(
            "SELECT id FROM criaturas WHERE id = ? AND usuario_id = ? "
            "AND guild_id = ? AND muerta_en IS NULL AND nombre != ''",
            (criatura_id, usuario_id, guild_id),
        ).fetchone()
        if fila is None:
            return False

        con.execute(
            "UPDATE criaturas SET activa = 0, muere_en = NULL, avisa_en = NULL "
            "WHERE usuario_id = ? AND guild_id = ? AND muerta_en IS NULL",
            (usuario_id, guild_id),
        )
        con.execute(
            "UPDATE criaturas SET activa = 1, actualizada_en = ? WHERE id = ?",
            (ahora.isoformat(), criatura_id),
        )

    # Un guardado normal recalcula `muere_en` y `avisa_en` de la que acaba de
    # despertar, que el UPDATE de arriba dejó en blanco junto a las demás.
    despierta = por_id(criatura_id)
    if despierta is not None:
        guardar(despierta)
    return True


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
    activa: bool = True,
    reclutado_por: int | None = None,
) -> sim.Criatura:
    """Registra una criatura recién nacida.

    `activa=False` la mete directa a la incubadora. Lo usa el reclutamiento: uno
    que se une en una aventura no puede desbancar sin avisar al que llevabas.

    `reclutado_por` es el id de quien lo convenció, y le apunta el reclutamiento
    en su marcador aquí dentro: si el alta se cae por el tope del plantel, no
    puede quedar apuntado un salvaje que no llegó a unirse.

    Dos defensas distintas y las dos hacen falta:

    - **El tope de tres** se comprueba aquí dentro con `BEGIN IMMEDIATE`, porque
      no cabe en un índice. Levanta `ValueError`.
    - **Una sola activa** lo sigue imponiendo el índice único, que hace saltar
      `sqlite3.IntegrityError`: es la defensa contra dos `/huevo` a la vez.
    """
    fuerza, velocidad, salud = stats
    nueva = sim.Criatura(
        id=0, usuario_id=usuario_id, guild_id=guild_id, especie=especie,
        nombre=nombre, genero=genero, caracter=caracter,
        nacida_en=ahora, actualizada_en=ahora,
        base_fuerza=fuerza, base_velocidad=velocidad, base_salud=salud,
        canal_id=canal_id, activa=activa,
    )
    valores = _a_valores(nueva)
    columnas = list(valores)
    marcadores = ", ".join(f":{c}" for c in columnas)

    with conectar() as con:
        # El turno de escritura se toma antes de contar: si no, dos peticiones a
        # la vez podrían contar dos y colar una cuarta criatura entre las dos.
        con.execute("BEGIN IMMEDIATE")
        cuantas = con.execute(
            "SELECT COUNT(*) c FROM criaturas "
            "WHERE usuario_id = ? AND guild_id = ? AND muerta_en IS NULL",
            (usuario_id, guild_id),
        ).fetchone()["c"]
        if cuantas >= MAXIMO_PLANTEL:
            raise ValueError(
                f"{usuario_id} ya tiene {cuantas} gachamones vivos en {guild_id}"
            )

        cursor = con.execute(
            f"INSERT INTO criaturas ({', '.join(columnas)}) VALUES ({marcadores})",
            valores,
        )
        nuevo_id = cursor.lastrowid
        if reclutado_por is not None:
            apuntar_en(con, reclutado_por, lgr.RECLUTADOS)

    return replace(nueva, id=nuevo_id)


def guardar(criatura: sim.Criatura) -> None:
    with conectar() as con:
        _guardar(con, criatura)


def _guardar(con: sqlite3.Connection, criatura: sim.Criatura) -> None:
    valores = _a_valores(criatura)
    valores["id"] = criatura.id
    asignaciones = ", ".join(f"{c} = :{c}" for c in valores if c != "id")
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

def espera_en(
    con: sqlite3.Connection, criatura_id: int, accion: str, ahora: datetime
) -> timedelta:
    fila = con.execute(
        "SELECT hasta FROM cooldowns WHERE criatura_id = ? AND accion = ?",
        (criatura_id, accion),
    ).fetchone()
    if not fila:
        return timedelta(0)
    return max(timedelta(0), datetime.fromisoformat(fila["hasta"]) - ahora)


def poner_cooldown_en(
    con: sqlite3.Connection, criatura_id: int, accion: str, hasta: datetime
) -> None:
    con.execute(
        "INSERT INTO cooldowns (criatura_id, accion, hasta) VALUES (?, ?, ?) "
        "ON CONFLICT(criatura_id, accion) DO UPDATE SET hasta = excluded.hasta",
        (criatura_id, accion, hasta.isoformat()),
    )

def espera_de(criatura_id: int, accion: str, ahora: datetime) -> timedelta:
    with conectar() as con:
        return espera_en(con, criatura_id, accion, ahora)


def esperas(
    criatura_id: int,
    ahora: datetime,
    acciones: Collection[str] = sim.ACCIONES_DE_CUIDADO,
) -> dict[str, timedelta]:
    """Lo que falta para las acciones pedidas, para pintarlo en el subtexto."""
    with conectar() as con:
        filas = con.execute(
            "SELECT accion, hasta FROM cooldowns WHERE criatura_id = ?",
            (criatura_id,),
        ).fetchall()
    guardados = {f["accion"]: datetime.fromisoformat(f["hasta"]) for f in filas}
    return {
        accion: max(timedelta(0), guardados.get(accion, ahora) - ahora)
        for accion in acciones
    }


def poner_cooldown(criatura_id: int, accion: str, ahora: datetime) -> None:
    duracion = sim.COOLDOWNS.get(accion, timedelta(0))
    if not duracion:
        return
    with conectar() as con:
        poner_cooldown_en(con, criatura_id, accion, ahora + duracion)


def quitar_cooldown(criatura_id: int, accion: str) -> None:
    """Borra la espera de una acción. Lo que hacen los objetos de reinicio."""
    with conectar() as con:
        con.execute(
            "DELETE FROM cooldowns WHERE criatura_id = ? AND accion = ?",
            (criatura_id, accion),
        )


# --- Cooldowns de la persona ------------------------------------------------
#
# Van aparte en vez de con un `criatura_id` inventado porque la clave es otra:
# persona + servidor, como el inventario. No hay `quitar_cooldown_persona`
# porque ningún objeto reinicia la aventura; el día que lo haya, se escribe.

def espera_de_persona(
    usuario_id: str, guild_id: str, accion: str, ahora: datetime
) -> timedelta:
    with conectar() as con:
        fila = con.execute(
            "SELECT hasta FROM cooldowns_persona "
            "WHERE usuario_id = ? AND guild_id = ? AND accion = ?",
            (usuario_id, guild_id, accion),
        ).fetchone()
    if not fila:
        return timedelta(0)
    return max(timedelta(0), datetime.fromisoformat(fila["hasta"]) - ahora)


def poner_cooldown_persona(
    usuario_id: str, guild_id: str, accion: str, ahora: datetime
) -> None:
    duracion = sim.COOLDOWNS.get(accion, timedelta(0))
    if not duracion:
        return
    with conectar() as con:
        con.execute(
            "INSERT INTO cooldowns_persona (usuario_id, guild_id, accion, hasta) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(usuario_id, guild_id, accion) "
            "DO UPDATE SET hasta = excluded.hasta",
            (usuario_id, guild_id, accion, (ahora + duracion).isoformat()),
        )


def esperas_de_ficha(
    criatura: sim.Criatura,
    ahora: datetime,
    acciones: Collection[str] = sim.ACCIONES_DE_CUIDADO,
) -> dict[str, timedelta]:
    """Todas las esperas que salen en la ficha, cada una de su tabla.

    Se junta aquí y no en cada vista porque son cuatro los sitios que pintan la
    ficha: si cada uno tuviera que acordarse de mirar en los dos lados, el día
    que se añada un quinto se le olvidaría y el 🧭 saldría siempre a cero.

    `acciones` la pone quien llama —`pantalla.ACCIONES_EN_FICHA`— porque la lista
    de lo que se enseña es cosa de la presentación, y este módulo no la importa.
    """
    todas = esperas(criatura.id, ahora, acciones)
    if sim.AVENTURA in todas:
        todas[sim.AVENTURA] = espera_de_persona(
            criatura.usuario_id, criatura.guild_id, sim.AVENTURA, ahora
        )
    return todas


# --- Inventario ------------------------------------------------------------

def inventario(usuario_id: str, guild_id: str) -> dict[str, int]:
    """Qué tiene y cuánto. Lo que se ha gastado del todo no sale."""
    with conectar() as con:
        filas = con.execute(
            "SELECT objeto, cantidad FROM inventario "
            "WHERE usuario_id = ? AND guild_id = ? AND cantidad > 0",
            (usuario_id, guild_id),
        ).fetchall()
    return {f["objeto"]: f["cantidad"] for f in filas}


def regalar(usuario_id: str, guild_id: str, objeto: obj.Objeto) -> None:
    """Mete un objeto en la mochila sin cobrar. Lo que se encuentra por ahí."""
    with conectar() as con:
        con.execute(
            "INSERT INTO inventario (usuario_id, guild_id, objeto, cantidad) "
            "VALUES (?, ?, ?, 1) "
            "ON CONFLICT(usuario_id, guild_id, objeto) "
            "DO UPDATE SET cantidad = cantidad + 1",
            (usuario_id, guild_id, objeto.clave),
        )


def gastar(usuario_id: str, guild_id: str, clave: str) -> bool:
    """Descuenta una unidad. Devuelve si la había.

    Igual que `cobrar`: la condición viaja dentro del UPDATE para que dos clics
    seguidos no puedan gastar dos veces la última unidad.
    """
    with conectar() as con:
        cursor = con.execute(
            "UPDATE inventario SET cantidad = cantidad - 1 "
            "WHERE usuario_id = ? AND guild_id = ? AND objeto = ? AND cantidad > 0",
            (usuario_id, guild_id, clave),
        )
        con.execute(
            "DELETE FROM inventario WHERE usuario_id = ? AND guild_id = ? "
            "AND objeto = ? AND cantidad <= 0",
            (usuario_id, guild_id, clave),
        )
    return cursor.rowcount > 0


# --- Efectos de las pociones -----------------------------------------------

def poner_efecto(criatura_id: int, stat: str, bonus: int, ahora: datetime) -> None:
    """Activa una poción. Si ya había otra en esa estadística, la sustituye."""
    hasta = ahora + timedelta(minutes=obj.MINUTOS_DE_EFECTO)
    with conectar() as con:
        con.execute(
            "INSERT INTO efectos (criatura_id, stat, bonus, hasta) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(criatura_id, stat) DO UPDATE SET "
            "bonus = excluded.bonus, hasta = excluded.hasta",
            (criatura_id, stat, bonus, hasta.isoformat()),
        )


def efecto_activo_en(
    con: sqlite3.Connection, criatura_id: int, stat: str, ahora: datetime
) -> int:
    fila = con.execute(
        "SELECT bonus, hasta FROM efectos WHERE criatura_id = ? AND stat = ?",
        (criatura_id, stat),
    ).fetchone()
    if not fila or datetime.fromisoformat(fila["hasta"]) <= ahora:
        return 0
    return fila["bonus"]


def efecto_activo(criatura_id: int, stat: str, ahora: datetime) -> int:
    """Lo que suma la poción en curso, o 0 si no hay o ya caducó."""
    with conectar() as con:
        return efecto_activo_en(con, criatura_id, stat, ahora)


def efectos_activos(criatura_id: int, ahora: datetime) -> dict[str, tuple[int, timedelta]]:
    """Las pociones en curso: `{stat: (bonus, lo que le queda)}`, para pintarlas."""
    with conectar() as con:
        filas = con.execute(
            "SELECT stat, bonus, hasta FROM efectos WHERE criatura_id = ?",
            (criatura_id,),
        ).fetchall()
    activos = {}
    for fila in filas:
        restante = datetime.fromisoformat(fila["hasta"]) - ahora
        if restante.total_seconds() > 0:
            activos[fila["stat"]] = (fila["bonus"], restante)
    return activos


# --- Marcador y logros ------------------------------------------------------
#
# Aquí sólo se guarda y se recuerda; qué hace falta para cada medalla lo decide
# `logros.py`, que es puro. La frontera está donde siempre: este módulo sabe de
# filas y aquel sabe de juego.

def marcador(criatura_id: int) -> dict[str, int]:
    """Lo que lleva hecho. Lo que no ha hecho nunca no sale, y vale cero."""
    with conectar() as con:
        return _marcador(con, criatura_id)


def _marcador(con: sqlite3.Connection, criatura_id: int) -> dict[str, int]:
    filas = con.execute(
        "SELECT clave, valor FROM marcador WHERE criatura_id = ?", (criatura_id,)
    ).fetchall()
    return {f["clave"]: f["valor"] for f in filas}


def apuntar_en(
    con: sqlite3.Connection, criatura_id: int, clave: str, cuanto: int = 1
) -> None:
    """Sube un contador dentro de una transacción que ya está abierta.

    Recibe la conexión a propósito: contar tiene que ocurrir **con** el
    resultado que lo provoca, no después. Si se cayera la conexión entre ganar
    la carrera y apuntarla, quedaría una victoria que no cuenta para nada y no
    habría forma de saberlo.
    """
    con.execute(
        "INSERT INTO marcador (criatura_id, clave, valor) VALUES (?, ?, ?) "
        "ON CONFLICT(criatura_id, clave) DO UPDATE SET valor = valor + excluded.valor",
        (criatura_id, clave, cuanto),
    )


def apuntar(criatura_id: int, clave: str, cuanto: int = 1) -> None:
    """La versión suelta, para quien no tiene ya una transacción entre manos."""
    with conectar() as con:
        apuntar_en(con, criatura_id, clave, cuanto)


def logros_de(criatura_id: int) -> dict[str, datetime]:
    """Los que ya tiene y cuándo los consiguió."""
    with conectar() as con:
        filas = con.execute(
            "SELECT clave, cuando FROM logros WHERE criatura_id = ? "
            "ORDER BY cuando, clave",
            (criatura_id,),
        ).fetchall()
    return {f["clave"]: datetime.fromisoformat(f["cuando"]) for f in filas}


def anotar_logro_en(
    con: sqlite3.Connection, criatura_id: int, clave: str, cuando: datetime
) -> bool:
    """Apunta un logro y dice si era nuevo. Falso si ya lo tenía.

    Recibe la conexión porque quien desbloquea también paga —`economia`— y las
    dos cosas tienen que ir juntas: un logro apuntado sin pagar no se puede
    reintentar, porque el segundo intento ya lo encuentra puesto.

    Que no se pague dos veces no lo vigila el código sino la clave primaria de
    la tabla: se intenta insertar y se mira si entró. Es la misma disciplina de
    `operaciones_economia`, y por el mismo motivo — el contador de carreras
    sigue subiendo para siempre después de desbloquear «Velocista».
    """
    cursor = con.execute(
        "INSERT OR IGNORE INTO logros (criatura_id, clave, cuando) "
        "VALUES (?, ?, ?)",
        (criatura_id, clave, cuando.isoformat()),
    )
    return bool(cursor.rowcount)


# --- Listados --------------------------------------------------------------

def vivas_del_servidor(guild_id: str) -> list[sim.Criatura]:
    """Las criaturas **activas** de un servidor, para la escena del jardín.

    Sólo las activas: las de la incubadora están dormidas y con el tiempo
    parado, así que dibujarlas paseando por el jardín no se sostiene. En
    `/ranking` y `/cementerio` sí salen todas, porque eso es historial.
    """
    with conectar() as con:
        filas = con.execute(
            "SELECT * FROM criaturas WHERE guild_id = ? AND muerta_en IS NULL "
            "AND activa = 1 ORDER BY nacida_en",
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
