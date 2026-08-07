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

import logging
import random
import sqlite3
from collections.abc import Collection
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import casas as cas
import config
import cosmeticos as cos
import especies as esp
import huerto as hue
import logros as lgr
import objetos as obj
import personalidad as per
import simulacion as sim

logger = logging.getLogger(__name__)

RUTA: Path = config.RUTA_BD

# Cuántos gachamones puede tener una persona por servidor. Uno activo y el resto
# en la incubadora. El primero sale de `/huevo`; los demás sólo reclutándolos.
#
# Subió de 3 a 10 y de 10 a 25 para que coleccionar sea un objetivo largo. Lo
# que de verdad cambia con este número es `/aventura`: con el plantel lleno los
# salvajes se convierten en objetos, así que el tope decide cuánto dura la fase
# de reclutar. Medido, se recluta en el 5,5 % de las aventuras y hay 37 minutos
# entre una y otra: llenar dos huecos son unas 22 horas de juego.
#
# **25 es el techo, y no lo pone el gusto sino Discord**: `equipo.MenuPlantel`
# pone una opción por gachamon y un desplegable admite 25 exactas. Con este
# número entra justo y sin un hueco de margen, así que subirlo obliga antes a
# paginar ese menú. Hay un test que lo vigila.
MAXIMO_PLANTEL = 25

# El esquema va en dos trozos porque el orden importa: primero las tablas,
# después las migraciones que añaden columnas nuevas, y sólo entonces los
# índices — que referencian esas columnas y fallarían si se crearan antes.
# Se escribe aparte del resto del esquema porque la migración lo necesita
# entero: SQLite no deja alterar un CHECK, así que añadir un tipo obliga a
# recrear la tabla y volver a copiar las filas.
DDL_OPERACIONES = """
CREATE TABLE operaciones_economia (
    evento_id        TEXT NOT NULL,
    usuario_id       TEXT NOT NULL,
    guild_id         TEXT NOT NULL,
    tipo             TEXT NOT NULL CHECK (tipo IN ('cuidado','evolucion','competencia','aventura','compra')),
    fecha_utc        TEXT NOT NULL,
    resultado        TEXT NOT NULL CHECK (resultado IN ('acreditada','topada','comprada','saldo_insuficiente')),
    delta_asciicoins INTEGER NOT NULL,
    solicitud        TEXT NOT NULL CHECK (length(solicitud) > 0),
    CHECK (
        (resultado = 'acreditada' AND tipo IN ('cuidado','evolucion','competencia','aventura') AND delta_asciicoins > 0) OR
        (resultado = 'topada' AND tipo IN ('cuidado','evolucion','competencia','aventura') AND delta_asciicoins = 0) OR
        (resultado = 'comprada' AND tipo = 'compra' AND delta_asciicoins < 0) OR
        (resultado = 'saldo_insuficiente' AND tipo = 'compra' AND delta_asciicoins = 0)
    ),
    PRIMARY KEY (evento_id, usuario_id, guild_id, tipo)
)
"""

COLUMNAS_OPERACIONES = (
    "evento_id", "usuario_id", "guild_id", "tipo", "fecha_utc", "resultado",
    "delta_asciicoins", "solicitud",
)

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
    base_ingenio INTEGER NOT NULL DEFAULT 0,
    ent_fuerza INTEGER NOT NULL DEFAULT 0,
    ent_velocidad INTEGER NOT NULL DEFAULT 0,
    ent_salud INTEGER NOT NULL DEFAULT 0,
    ent_ingenio INTEGER NOT NULL DEFAULT 0,
    niv_fuerza INTEGER NOT NULL DEFAULT 0,
    niv_velocidad INTEGER NOT NULL DEFAULT 0,
    niv_salud INTEGER NOT NULL DEFAULT 0,
    niv_ingenio INTEGER NOT NULL DEFAULT 0,
    ten_fuerza REAL NOT NULL DEFAULT 0,
    ten_velocidad REAL NOT NULL DEFAULT 0,
    ten_salud REAL NOT NULL DEFAULT 0,
    ten_ingenio REAL NOT NULL DEFAULT 0,
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

-- Las dos de arriba, pero de la persona. Tres medallas no son del gachamon
-- —convencer salvajes y que te salga una rara los haces tú— y ésas se quedan
-- aunque se te muera el plantel entero, que es justamente lo que las distingue.
-- La clave primaria vuelve a ser la garantía de que ninguna se cobra dos veces.
CREATE TABLE IF NOT EXISTS marcador_persona (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    clave TEXT NOT NULL,
    valor INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (usuario_id, guild_id, clave)
);

CREATE TABLE IF NOT EXISTS logros_persona (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    clave TEXT NOT NULL,
    cuando TEXT NOT NULL,
    PRIMARY KEY (usuario_id, guild_id, clave)
);

-- Lo que has comprado, que no es lo mismo que lo que lleva puesto. Las cuatro
-- columnas de `criaturas` siguen siendo lo puesto —uno de cada tipo, impuesto
-- por el esquema— y esto es el armario de donde sale. Sin `cantidad`: una
-- corona se tiene o no se tiene, y tener dos no significaría nada; la clave
-- primaria es lo que lo impone y de paso lo que impide cobrarla dos veces.
CREATE TABLE IF NOT EXISTS ropero (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    cosmetico TEXT NOT NULL,
    PRIMARY KEY (usuario_id, guild_id, cosmetico)
);

-- Cómo quiere cada persona que todo el servidor vea sus fichas. Sin fila se
-- usa Imagen; sólo se guarda una elección explícita desde Personalizar.
CREATE TABLE IF NOT EXISTS estilos_ficha (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    estilo TEXT NOT NULL CHECK (estilo IN ('imagen', 'ascii')),
    PRIMARY KEY (usuario_id, guild_id)
);

-- Qué mensaje del canal de info es cada página del manual. Se apunta para poder
-- **editarlas** en cada arranque en vez de publicarlas otra vez: sin esto, cada
-- despliegue dejaría ocho mensajes más y el canal sería un vertedero.
--
-- Se guarda el id en vez de rastrear el historial del canal porque rastrear
-- adivina: basta con que alguien escriba o borre algo para que el orden deje de
-- ser fiable y el bot reescriba la página equivocada. Si el mensaje apuntado ya
-- no está, se publica otro y se apunta el suyo, así que vaciar el canal a mano
-- lo arregla en el siguiente arranque en vez de romperlo.
CREATE TABLE IF NOT EXISTS publicaciones (
    canal_id TEXT NOT NULL,
    indice INTEGER NOT NULL,
    mensaje_id TEXT NOT NULL,
    PRIMARY KEY (canal_id, indice)
);

-- El reloj del refugio de cada persona, y si deja mirar lo suyo. Sus casas van
-- aparte, en `casas_propias`: aquí sólo queda lo que es de la persona y no de
-- una casa concreta. Sin ninguna casa manda `refugio_hasta` —en el futuro sigue
-- en el refugio, en el pasado se ha quedado a la intemperie—, y por eso ese
-- reloj sobrevive a comprarlas y venderlas.
CREATE TABLE IF NOT EXISTS hogar (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    refugio_hasta TEXT NOT NULL,
    publica INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (usuario_id, guild_id)
);

-- Los muebles que has comprado, y cuáles están puestos. Uno de cada, como el
-- ropero: tener dos chimeneas no significaría nada y llegar al techo repitiendo
-- el mueble más caro dejaría el catálogo sin sentido. `colocado` es lo que
-- distingue lo que está en la casa de lo que está guardado; los huecos los
-- cuenta quien mira, contra `casa.huecos`.
-- El buzón: regalos que alguien te ha dejado y todavía no has recogido. Se
-- guarda el **nombre** de quien lo manda y no su id, porque este texto va
-- directo a un mensaje. La nota es opcional y va con el regalo, no aparte: un
-- regalo con nota que se separase de su nota sería peor que no tenerla.
CREATE TABLE IF NOT EXISTS buzon (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    para_usuario TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    de_nombre TEXT NOT NULL,
    objeto TEXT NOT NULL,
    nota TEXT NOT NULL DEFAULT '',
    cuando TEXT NOT NULL,
    recogido INTEGER NOT NULL DEFAULT 0
);

-- Los bancales del huerto. Uno por número **dentro de cada casa**: cuántos tiene
-- lo decide su tamaño, así que mejorarla da sitio y las filas viejas siguen
-- valiendo. Sin fila es barbecho.
--
-- `casa_id` entra en la clave y no es un adorno: sin él, los bancales se
-- numerarían de corrido entre todas tus casas y vender una renumeraría los de
-- las demás, con lo plantado cambiando de sitio solo.
CREATE TABLE IF NOT EXISTS huerto (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    casa_id INTEGER NOT NULL,
    bancal INTEGER NOT NULL,
    plantado_en TEXT NOT NULL,
    regado INTEGER NOT NULL DEFAULT 0,
    -- Qué se sembró, por su clave de objeto. El color de la cosecha lo hereda de
    -- aquí, salvo la semilla y el arcoíris, que lo sortean.
    sembrado TEXT NOT NULL DEFAULT 'semilla',
    PRIMARY KEY (usuario_id, guild_id, casa_id, bancal)
);

-- Cada casa que alguien tiene, una por fila. Es lo que rompe el «una casa por
-- persona» que antes imponía la clave primaria de `hogar`, y el `id` hace falta
-- porque ahora se pueden tener dos del mismo tamaño y los gachamones, los
-- muebles y los bancales apuntan a una en concreto, no a «la mediana».
CREATE TABLE IF NOT EXISTS casas_propias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    casa TEXT NOT NULL,
    comprada_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mobiliario (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    mueble TEXT NOT NULL,
    colocado INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (usuario_id, guild_id, mueble)
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
    "base_fuerza", "base_velocidad", "base_salud", "base_ingenio",
    "ent_fuerza", "ent_velocidad", "ent_salud", "ent_ingenio",
    "niv_fuerza", "niv_velocidad", "niv_salud", "niv_ingenio",
    "ten_fuerza", "ten_velocidad", "ten_salud", "ten_ingenio",
    "historial_vetas",
    "xp", "nivel", "victorias", "derrotas", "pantalla_msg_id", "canal_id",
    "activa", "tinte", "sombrero", "marco", "titulo", "casa_id",
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
    ("base_ingenio", "ALTER TABLE criaturas ADD COLUMN base_ingenio INTEGER NOT NULL DEFAULT 0"),
    ("ent_ingenio", "ALTER TABLE criaturas ADD COLUMN ent_ingenio INTEGER NOT NULL DEFAULT 0"),
    ("niv_ingenio", "ALTER TABLE criaturas ADD COLUMN niv_ingenio INTEGER NOT NULL DEFAULT 0"),
    ("ten_ingenio", "ALTER TABLE criaturas ADD COLUMN ten_ingenio REAL NOT NULL DEFAULT 0"),
    ("ten_fuerza", "ALTER TABLE criaturas ADD COLUMN ten_fuerza REAL NOT NULL DEFAULT 0"),
    ("ten_velocidad", "ALTER TABLE criaturas ADD COLUMN ten_velocidad REAL NOT NULL DEFAULT 0"),
    ("ten_salud", "ALTER TABLE criaturas ADD COLUMN ten_salud REAL NOT NULL DEFAULT 0"),
    ("historial_vetas", "ALTER TABLE criaturas ADD COLUMN historial_vetas TEXT NOT NULL DEFAULT ''"),
    # Los cosméticos. Van en columnas y no en tabla justamente porque es uno de
    # cada tipo: una tabla permitiría llevar dos coronas y habría que prohibirlo
    # con código. `NULL` es «no lleva», que es con lo que se queda todo el mundo
    # hasta que compre algo.
    ("tinte", "ALTER TABLE criaturas ADD COLUMN tinte TEXT"),
    ("sombrero", "ALTER TABLE criaturas ADD COLUMN sombrero TEXT"),
    ("marco", "ALTER TABLE criaturas ADD COLUMN marco TEXT"),
    ("titulo", "ALTER TABLE criaturas ADD COLUMN titulo TEXT"),
    # En qué casa de su dueño vive. `NULL` es el refugio, que es adonde va quien
    # no cabe en ninguna. Lo rellena `_migrar_casas` para las que ya existían.
    ("casa_id", "ALTER TABLE criaturas ADD COLUMN casa_id INTEGER"),
)

# Lo mismo, para tablas que no son `criaturas`. Van aparte porque `MIGRACIONES`
# mira sólo el `PRAGMA` de aquélla, que es donde habían caído todas hasta ahora.
MIGRACIONES_DE_TABLAS = (
    # Las casas nacieron todas visibles y así se quedan las que ya existían: es
    # lo mismo que hace `/mascota @alguien`, que enseña el gachamon de quien sea
    # sin preguntar.
    ("hogar", "publica",
     "ALTER TABLE hogar ADD COLUMN publica INTEGER NOT NULL DEFAULT 1"),
    # Antes sólo se sembraban semillas, así que no había nada que guardar. El
    # `DEFAULT` deja a los bancales que ya estaban creciendo tal y como se
    # plantaron: semilla, y color al azar al cosechar. Ninguna fila que tocar.
    ("huerto", "sembrado",
     "ALTER TABLE huerto ADD COLUMN sembrado TEXT NOT NULL DEFAULT 'semilla'"),
    # En qué casa cuelga cada mueble. Se sigue teniendo uno de cada por persona
    # —eso lo impone la clave primaria y no cambia—; lo nuevo es elegir dónde.
    # `NULL` con `colocado = 1` es lo que deja `_migrar_casas` a quien no tenía
    # casa, y `_mobiliario_de` lo trata como guardado.
    ("mobiliario", "casa_id", "ALTER TABLE mobiliario ADD COLUMN casa_id INTEGER"),
)

# La tabla `hogar` tal como queda tras `_migrar_casas`, sin la columna `casa`.
DDL_HOGAR = """
CREATE TABLE hogar (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    refugio_hasta TEXT NOT NULL,
    publica INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (usuario_id, guild_id)
)
"""

DDL_HUERTO = """
CREATE TABLE huerto (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    casa_id INTEGER NOT NULL,
    bancal INTEGER NOT NULL,
    plantado_en TEXT NOT NULL,
    regado INTEGER NOT NULL DEFAULT 0,
    sembrado TEXT NOT NULL DEFAULT 'semilla',
    PRIMARY KEY (usuario_id, guild_id, casa_id, bancal)
)
"""


def inicializar() -> None:
    with conectar() as con:
        con.executescript(SCHEMA_TABLAS)
        _migrar(con)
        con.commit()
        _migrar_monederos(con)
        _migrar_operaciones(con)
        # Después de `_migrar`, que es quien añade `criaturas.casa_id` y
        # `mobiliario.casa_id`: esta migración los rellena, así que tienen que
        # existir antes.
        _migrar_casas(con)
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


def _migrar_operaciones(con: sqlite3.Connection) -> None:
    """Admite el tipo `aventura` en el ledger, una sola vez.

    SQLite no deja alterar un `CHECK`, así que la única salida es recrear la
    tabla y copiar las filas. **Es la primera migración de este proyecto que
    mueve un ledger con datos dentro**, así que va sola en su transacción y con
    su test sobre filas de verdad.

    Que ya haya corrido se detecta mirando el SQL guardado en `sqlite_master`:
    es la única señal fiable, porque el `CHECK` no aparece en `PRAGMA
    table_info`.
    """
    con.execute("BEGIN IMMEDIATE")
    fila = con.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        ("operaciones_economia",),
    ).fetchone()
    if fila is None:                       # base nueva: se crea y ya está
        con.execute(DDL_OPERACIONES)
        con.commit()
        return
    if "'aventura'" in fila["sql"]:        # ya migrada
        con.commit()
        return

    columnas = ", ".join(COLUMNAS_OPERACIONES)
    con.execute("ALTER TABLE operaciones_economia RENAME TO operaciones_legacy")
    con.execute(DDL_OPERACIONES)
    con.execute(
        f"INSERT INTO operaciones_economia ({columnas}) "
        f"SELECT {columnas} FROM operaciones_legacy"
    )
    con.execute("DROP TABLE operaciones_legacy")
    con.commit()


def _migrar_casas(con: sqlite3.Connection) -> None:
    """Pasa de «una casa por persona» a varias, una sola vez.

    Es la segunda migración del proyecto que mueve datos —tras la de
    `operaciones_economia`—, así que va sola en su transacción y con su test
    sobre filas de verdad. Dos tablas hay que recrearlas porque SQLite no deja
    quitar una columna de una clave primaria ni añadirla:

    * `hogar` pierde `casa`, que se lleva `casas_propias`.
    * `huerto` gana `casa_id` en la clave, para que los bancales se numeren
      dentro de cada casa y vender una no renumere los de las demás.

    **Nadie pierde su sitio.** Cada casa que hubiera pasa a ser una fila de
    `casas_propias`, y todo lo de esa persona —sus gachamones vivos, sus
    bancales y sus muebles colgados— queda apuntado a ella, aunque sean más
    gachamones de los que ahora caben: el aforo frena las mudanzas nuevas, no
    desaloja a quien ya estaba.

    Que ya haya corrido se detecta mirando si `hogar` conserva la columna
    `casa`, que es la señal que no se puede falsear.
    """
    con.execute("BEGIN IMMEDIATE")
    if "casa" not in _columnas(con, "hogar"):        # ya migrada
        con.commit()
        return

    # La tabla vieja no tiene dónde apuntar la casa. Se le añade suelta para
    # poder rellenarla, y al final se recrea entera con la clave nueva.
    if "casa_id" not in _columnas(con, "huerto"):
        con.execute("ALTER TABLE huerto ADD COLUMN casa_id INTEGER")

    for fila in con.execute(
        "SELECT usuario_id, guild_id, casa, refugio_hasta FROM hogar "
        "WHERE casa IS NOT NULL"
    ).fetchall():
        usuario_id, guild_id = fila["usuario_id"], fila["guild_id"]
        cursor = con.execute(
            "INSERT INTO casas_propias (usuario_id, guild_id, casa, comprada_en) "
            "VALUES (?, ?, ?, ?)",
            (usuario_id, guild_id, fila["casa"], fila["refugio_hasta"]),
        )
        casa_id = cursor.lastrowid
        con.execute(
            "UPDATE criaturas SET casa_id = ? "
            "WHERE usuario_id = ? AND guild_id = ? AND muerta_en IS NULL",
            (casa_id, usuario_id, guild_id),
        )
        con.execute(
            "UPDATE huerto SET casa_id = ? WHERE usuario_id = ? AND guild_id = ?",
            (casa_id, usuario_id, guild_id),
        )
        con.execute(
            "UPDATE mobiliario SET casa_id = ? "
            "WHERE usuario_id = ? AND guild_id = ? AND colocado = 1",
            (casa_id, usuario_id, guild_id),
        )

    # `hogar` sin `casa`. Se copia `publica` sólo si la tabla vieja la tenía:
    # una base anterior a esa migración no la lleva, y el DEFAULT la deja en 1,
    # que es lo mismo que hacía su propia migración.
    tenia_publica = "publica" in _columnas(con, "hogar")
    columnas = "usuario_id, guild_id, refugio_hasta"
    if tenia_publica:
        columnas += ", publica"
    con.execute("ALTER TABLE hogar RENAME TO hogar_legacy")
    con.execute(DDL_HOGAR)
    con.execute(
        f"INSERT INTO hogar ({columnas}) SELECT {columnas} FROM hogar_legacy"
    )
    con.execute("DROP TABLE hogar_legacy")

    # `huerto` con `casa_id` en la clave. Lo que quede sin casa —bancales de
    # quien no tenía— se tira: era tierra de una casa que no existe.
    con.execute("ALTER TABLE huerto RENAME TO huerto_legacy")
    con.execute(DDL_HUERTO)
    con.execute(
        "INSERT INTO huerto "
        "(usuario_id, guild_id, casa_id, bancal, plantado_en, regado, sembrado) "
        "SELECT usuario_id, guild_id, casa_id, bancal, plantado_en, regado, "
        "sembrado FROM huerto_legacy WHERE casa_id IS NOT NULL"
    )
    con.execute("DROP TABLE huerto_legacy")
    con.commit()


def _migrar(con: sqlite3.Connection) -> None:
    # El turno de escritura se toma ANTES de mirar qué columnas hay, igual que
    # en `_migrar_monederos`. Sin esto, dos arranques a la vez pueden leer los
    # dos que falta la misma columna y lanzar los dos el ALTER: el segundo
    # revienta con «duplicate column name». Pasaba una vez de cada trece, que es
    # la peor frecuencia posible — la justa para parecer casualidad.
    con.execute("BEGIN IMMEDIATE")
    existentes = {f["name"] for f in con.execute("PRAGMA table_info(criaturas)")}
    for columna, sentencia in MIGRACIONES:
        if columna not in existentes:
            con.execute(sentencia)

    for tabla, columna, sentencia in MIGRACIONES_DE_TABLAS:
        if columna not in _columnas(con, tabla):
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

    # Y por lo mismo, tres logros dejaron de ser del gachamon: a la aventura vas
    # tú, así que convencer salvajes lo haces tú, y que te salga una rara es tu
    # suerte. Se mudan en vez de tirarse — **no se paga ni se quita nada**: las
    # gemas ya cobradas se quedan donde están, y quien las cobró dos veces con
    # dos gachamones se las queda. Se conserva la fecha del primero, que es la de
    # verdad.
    #
    # Es idempotente porque borra su propia fuente, y las dos mitades caen en la
    # misma transacción que el resto de `_migrar`: o se muda todo o no se muda
    # nada.
    claves = tuple(logro.clave for logro in lgr.de_la_persona())
    huecos = ", ".join("?" * len(claves))
    con.execute(
        "INSERT INTO logros_persona (usuario_id, guild_id, clave, cuando) "
        "SELECT c.usuario_id, c.guild_id, l.clave, MIN(l.cuando) "
        "  FROM logros l JOIN criaturas c ON c.id = l.criatura_id "
        f" WHERE l.clave IN ({huecos}) "
        " GROUP BY c.usuario_id, c.guild_id, l.clave "
        "ON CONFLICT(usuario_id, guild_id, clave) DO UPDATE SET "
        "  cuando = MIN(cuando, excluded.cuando)",
        claves,
    )
    con.execute(f"DELETE FROM logros WHERE clave IN ({huecos})", claves)

    con.execute(
        "INSERT INTO marcador_persona (usuario_id, guild_id, clave, valor) "
        "SELECT c.usuario_id, c.guild_id, m.clave, SUM(m.valor) "
        "  FROM marcador m JOIN criaturas c ON c.id = m.criatura_id "
        " WHERE m.clave = ? "
        " GROUP BY c.usuario_id, c.guild_id, m.clave "
        "ON CONFLICT(usuario_id, guild_id, clave) DO UPDATE SET "
        "  valor = valor + excluded.valor",
        (lgr.RECLUTADOS,),
    )
    con.execute("DELETE FROM marcador WHERE clave = ?", (lgr.RECLUTADOS,))

    # Los cosméticos dejaron de comprarse puestos: ahora se compran al ropero de
    # la persona y desde ahí se equipan y se quitan. Lo que cada gachamon lleve
    # encima entra en el ropero de su dueño y **se queda puesto**, que es lo que
    # hace que nadie note el cambio salvo por poder quitárselo.
    #
    # Las columnas no se tocan: siguen siendo lo puesto. Idempotente por el
    # `OR IGNORE`, y al llegar aquí era cero filas.
    for columna in cos.TIPOS:
        con.execute(
            "INSERT OR IGNORE INTO ropero (usuario_id, guild_id, cosmetico) "
            f"SELECT usuario_id, guild_id, {columna} FROM criaturas "
            f"WHERE {columna} IS NOT NULL"
        )

    for clave, definicion in esp.ESPECIES.items():
        con.execute(
            "UPDATE criaturas SET base_ingenio = ? "
            "WHERE especie = ? AND base_ingenio = 0",
            (definicion.ingenio + 7, clave),
        )
    restantes = con.execute(
        "SELECT COUNT(*) c FROM criaturas WHERE base_ingenio = 0"
    ).fetchone()["c"]
    if restantes:
        logger.warning(
            "%d criaturas de especie desconocida reciben ingenio 15", restantes
        )
        con.execute("UPDATE criaturas SET base_ingenio = 15 WHERE base_ingenio = 0")


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

def _primera_casa_con_sitio(
    con: sqlite3.Connection, usuario_id: str, guild_id: str
) -> int | None:
    """La primera casa suya donde quepa uno más, o `None` si no cabe en ninguna.

    En orden de compra, que es el que quien juega reconoce. `None` significa el
    refugio, que es adonde va quien no cabe.
    """
    dentro = inquilinos_en(con, usuario_id, guild_id)
    for fila in con.execute(
        "SELECT id, casa FROM casas_propias "
        "WHERE usuario_id = ? AND guild_id = ? ORDER BY id",
        (usuario_id, guild_id),
    ):
        casa = cas.CATALOGO.get(fila["casa"])
        if casa and dentro.get(fila["id"], 0) < casa.aforo:
            return fila["id"]
    return None


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


def criatura_en(
    con: sqlite3.Connection, criatura_id: int
) -> sim.Criatura | None:
    fila = con.execute(
        "SELECT * FROM criaturas WHERE id = ?", (criatura_id,)
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
    stats: tuple[int, int, int, int],
    ahora: datetime,
    genero: str = esp.MACHO,
    caracter: str = esp.CARACTER_POR_DEFECTO,
    canal_id: str | None = None,
    activa: bool = True,
    reclutada: bool = False,
) -> sim.Criatura:
    """Registra una criatura recién nacida.

    `activa=False` la mete directa a la incubadora. Lo usa el reclutamiento: uno
    que se une en una aventura no puede desbancar sin avisar al que llevabas.

    `reclutada` dice que llega de una aventura, y le apunta el reclutamiento a
    **la persona** aquí dentro: si el alta se cae por el tope del plantel, no
    puede quedar apuntado un salvaje que no llegó a unirse. No hace falta decir
    qué gachamon lo convenció porque la medalla ya no es suya: a la aventura va
    la persona, que es la misma que sale en esta fila.

    Dos defensas distintas y las dos hacen falta:

    - **El tope de tres** se comprueba aquí dentro con `BEGIN IMMEDIATE`, porque
      no cabe en un índice. Levanta `ValueError`.
    - **Una sola activa** lo sigue imponiendo el índice único, que hace saltar
      `sqlite3.IntegrityError`: es la defensa contra dos `/huevo` a la vez.
    """
    fuerza, velocidad, salud, ingenio = stats
    nueva = sim.Criatura(
        id=0, usuario_id=usuario_id, guild_id=guild_id, especie=especie,
        nombre=nombre, genero=genero, caracter=caracter,
        nacida_en=ahora, actualizada_en=ahora,
        base_fuerza=fuerza, base_velocidad=velocidad, base_salud=salud,
        base_ingenio=ingenio, canal_id=canal_id, activa=activa,
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

        # Nace en la primera casa con sitio. Sin esto llegaría al refugio
        # aunque su dueño tenga tres casas medio vacías, y tendría que mudarlo a
        # mano cada vez: el reparto es para decidir dónde va, no para tener que
        # colocar a cada recién llegado.
        casa_id = _primera_casa_con_sitio(con, usuario_id, guild_id)
        valores["casa_id"] = casa_id
        # Y se refleja en lo que se devuelve: si sólo fuera a la fila, quien
        # llama tendría en la mano una criatura que dice vivir en el refugio
        # mientras la base dice otra cosa.
        nueva = replace(nueva, casa_id=casa_id)

        cursor = con.execute(
            f"INSERT INTO criaturas ({', '.join(columnas)}) VALUES ({marcadores})",
            valores,
        )
        nuevo_id = cursor.lastrowid
        if reclutada:
            apuntar_persona_en(con, usuario_id, guild_id, lgr.RECLUTADOS)

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


# --- El manual publicado en su canal ---------------------------------------

def publicacion_en(canal_id: str, indice: int) -> str | None:
    """El id del mensaje donde vive esa página, o `None` si aún no se publicó."""
    with conectar() as con:
        fila = con.execute(
            "SELECT mensaje_id FROM publicaciones "
            "WHERE canal_id = ? AND indice = ?",
            (canal_id, indice),
        ).fetchone()
    return fila["mensaje_id"] if fila else None


def guardar_publicacion(canal_id: str, indice: int, mensaje_id: str) -> None:
    """Apunta en qué mensaje quedó esa página. Sustituye lo que hubiera."""
    with conectar() as con:
        con.execute(
            "INSERT INTO publicaciones (canal_id, indice, mensaje_id) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(canal_id, indice) DO UPDATE SET "
            "mensaje_id = excluded.mensaje_id",
            (canal_id, indice, mensaje_id),
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
        return _inventario(con, usuario_id, guild_id)


def _inventario(
    con: sqlite3.Connection, usuario_id: str, guild_id: str
) -> dict[str, int]:
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


# --- El buzón --------------------------------------------------------------

LARGO_MAXIMO_NOTA = 140


@dataclass(frozen=True)
class Regalo:
    id: int
    de_nombre: str
    objeto: str
    nota: str
    cuando: datetime


def limpiar_nota(propuesta: str) -> str:
    """Deja la nota en una línea y del largo que cabe.

    Va aquí y no en el cog porque el recorte tiene que valer igual venga de donde
    venga: una nota con saltos de línea rompería el listado del buzón, que pinta
    un regalo por renglón.
    """
    return " ".join(propuesta.split())[:LARGO_MAXIMO_NOTA]


def mandar_regalo(
    de_usuario: str, de_nombre: str, para_usuario: str, guild_id: str,
    clave: str, nota: str, ahora: datetime,
) -> bool:
    """Saca el objeto de tu mochila y lo deja en el buzón del otro.

    Las dos mitades van en la misma transacción: un objeto que saliera de una
    mochila sin llegar a ningún buzón se habría perdido, y al revés se habría
    duplicado. Devuelve si había algo que mandar.
    """
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        gastado = con.execute(
            "UPDATE inventario SET cantidad = cantidad - 1 "
            "WHERE usuario_id = ? AND guild_id = ? AND objeto = ? AND cantidad > 0",
            (de_usuario, guild_id, clave),
        ).rowcount > 0
        if not gastado:
            return False
        con.execute(
            "INSERT INTO buzon "
            "(para_usuario, guild_id, de_nombre, objeto, nota, cuando) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (para_usuario, guild_id, de_nombre, clave,
             limpiar_nota(nota), ahora.isoformat()),
        )
        return True


def buzon_de(usuario_id: str, guild_id: str) -> list[Regalo]:
    """Lo que te espera sin recoger, lo más viejo primero."""
    with conectar() as con:
        filas = con.execute(
            "SELECT id, de_nombre, objeto, nota, cuando FROM buzon "
            "WHERE para_usuario = ? AND guild_id = ? AND recogido = 0 "
            "ORDER BY cuando, id",
            (usuario_id, guild_id),
        ).fetchall()
    return [
        Regalo(f["id"], f["de_nombre"], f["objeto"], f["nota"],
               datetime.fromisoformat(f["cuando"]))
        for f in filas
    ]


def recoger_del_buzon(
    usuario_id: str, guild_id: str, regalo_id: int
) -> Regalo | None:
    """Lo pasa a tu mochila y lo marca recogido. `None` si ya no estaba.

    Lo que impide entregarlo dos veces es el `BEGIN IMMEDIATE` con el `SELECT`
    dentro: el segundo clic no encuentra ya la fila sin recoger. Aquí no hace
    falta además meter la condición en el `UPDATE`, como sí hacen las compras —
    allí no hay un `SELECT` previo que la cubra.
    """
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        fila = con.execute(
            "SELECT id, de_nombre, objeto, nota, cuando FROM buzon "
            "WHERE id = ? AND para_usuario = ? AND guild_id = ? AND recogido = 0",
            (regalo_id, usuario_id, guild_id),
        ).fetchone()
        if fila is None:
            return None
        con.execute("UPDATE buzon SET recogido = 1 WHERE id = ?", (regalo_id,))
        con.execute(
            "INSERT INTO inventario (usuario_id, guild_id, objeto, cantidad) "
            "VALUES (?, ?, ?, 1) "
            "ON CONFLICT(usuario_id, guild_id, objeto) "
            "DO UPDATE SET cantidad = cantidad + 1",
            (usuario_id, guild_id, fila["objeto"]),
        )
        return Regalo(
            fila["id"], fila["de_nombre"], fila["objeto"], fila["nota"],
            datetime.fromisoformat(fila["cuando"]),
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


# --- Lo mismo, pero de la persona -------------------------------------------
#
# Cambia la clave y nada más: las mismas fronteras, la misma disciplina de
# apuntar dentro de la transacción que lo provoca, y la misma clave primaria
# haciendo de garantía de pago único.

def marcador_de_persona(usuario_id: str, guild_id: str) -> dict[str, int]:
    with conectar() as con:
        return _marcador_de_persona(con, usuario_id, guild_id)


def _marcador_de_persona(
    con: sqlite3.Connection, usuario_id: str, guild_id: str
) -> dict[str, int]:
    filas = con.execute(
        "SELECT clave, valor FROM marcador_persona "
        "WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    ).fetchall()
    return {f["clave"]: f["valor"] for f in filas}


def apuntar_persona_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str,
    clave: str, cuanto: int = 1,
) -> None:
    con.execute(
        "INSERT INTO marcador_persona (usuario_id, guild_id, clave, valor) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(usuario_id, guild_id, clave) "
        "DO UPDATE SET valor = valor + excluded.valor",
        (usuario_id, guild_id, clave, cuanto),
    )


def logros_de_persona(usuario_id: str, guild_id: str) -> dict[str, datetime]:
    with conectar() as con:
        filas = con.execute(
            "SELECT clave, cuando FROM logros_persona "
            "WHERE usuario_id = ? AND guild_id = ? ORDER BY cuando, clave",
            (usuario_id, guild_id),
        ).fetchall()
    return {f["clave"]: datetime.fromisoformat(f["cuando"]) for f in filas}


def anotar_logro_de_persona_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str,
    clave: str, cuando: datetime,
) -> bool:
    cursor = con.execute(
        "INSERT OR IGNORE INTO logros_persona "
        "(usuario_id, guild_id, clave, cuando) VALUES (?, ?, ?, ?)",
        (usuario_id, guild_id, clave, cuando.isoformat()),
    )
    return bool(cursor.rowcount)


# --- El estilo público de la ficha ----------------------------------------

def estilo_de_ficha(usuario_id: str, guild_id: str) -> str:
    """La elección pública de la persona; Imagen si nunca eligió."""
    with conectar() as con:
        fila = con.execute(
            "SELECT estilo FROM estilos_ficha "
            "WHERE usuario_id = ? AND guild_id = ?",
            (usuario_id, guild_id),
        ).fetchone()
    return fila["estilo"] if fila is not None else "imagen"


def guardar_estilo_de_ficha(usuario_id: str, guild_id: str, estilo: str) -> None:
    if estilo not in ("imagen", "ascii"):
        raise ValueError(f"Estilo de ficha inválido: {estilo}")
    with conectar() as con:
        con.execute(
            "INSERT INTO estilos_ficha (usuario_id, guild_id, estilo) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT (usuario_id, guild_id) DO UPDATE SET estilo = excluded.estilo",
            (usuario_id, guild_id, estilo),
        )


# --- El ropero -------------------------------------------------------------
#
# Lo que tienes, no lo que llevas puesto. Lo puesto sigue en las cuatro columnas
# de `criaturas`, que es lo que hace que sea uno de cada tipo sin comprobarlo.

def ropero(usuario_id: str, guild_id: str) -> frozenset[str]:
    with conectar() as con:
        return _ropero(con, usuario_id, guild_id)


def _ropero(
    con: sqlite3.Connection, usuario_id: str, guild_id: str
) -> frozenset[str]:
    filas = con.execute(
        "SELECT cosmetico FROM ropero WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    ).fetchall()
    return frozenset(f["cosmetico"] for f in filas)


def guardar_en_el_ropero_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, clave: str
) -> bool:
    """Lo mete y dice si era nuevo. Falso si ya lo tenía.

    Igual que `anotar_logro_en` y por lo mismo: lo que devuelve **es** la
    garantía de que no se cobre dos veces, y quien llama sólo cobra lo que entró
    de verdad.
    """
    cursor = con.execute(
        "INSERT OR IGNORE INTO ropero (usuario_id, guild_id, cosmetico) "
        "VALUES (?, ?, ?)",
        (usuario_id, guild_id, clave),
    )
    return bool(cursor.rowcount)


# --- El hogar --------------------------------------------------------------
#
# La fila se crea la primera vez que se mira, no al desplegar: así la semana de
# refugio empieza a contar cuando alguien aparece, y quien no juegue en un mes
# no llega y se la encuentra gastada. Por eso no hay migración que escribir.

def hogar_de(usuario_id: str, guild_id: str, ahora: datetime) -> cas.Hogar:
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        return _hogar_de(con, usuario_id, guild_id, ahora)


def _hogar_de(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, ahora: datetime
) -> cas.Hogar:
    """El hogar, **empezando la estancia** si es la primera vez que se mira."""
    hogar = _hogar_leido(con, usuario_id, guild_id, ahora)
    if not _hay_hogar(con, usuario_id, guild_id):
        con.execute(
            "INSERT INTO hogar (usuario_id, guild_id, refugio_hasta) "
            "VALUES (?, ?, ?)",
            (usuario_id, guild_id, hogar.refugio_hasta.isoformat()),
        )
    return hogar


def alargar_el_refugio(
    usuario_id: str, guild_id: str, dias: int, ahora: datetime
) -> datetime:
    """Le da otra estancia en el refugio y devuelve hasta cuándo llega.

    Cuenta **desde ahora** y no desde el final de la que hubiera: quien lo use
    con estancia de sobra estaría tirando el ticket, así que el aviso lo dice y
    el menú lo deja para cuando haga falta.
    """
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        _hogar_de(con, usuario_id, guild_id, ahora)     # la crea si no está
        hasta = ahora + timedelta(days=dias)
        con.execute(
            "UPDATE hogar SET refugio_hasta = ? WHERE usuario_id = ? "
            "AND guild_id = ?",
            (hasta.isoformat(), usuario_id, guild_id),
        )
        return hasta


def _hay_hogar(con: sqlite3.Connection, usuario_id: str, guild_id: str) -> bool:
    return con.execute(
        "SELECT 1 FROM hogar WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    ).fetchone() is not None


def _hogar_leido(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, ahora: datetime
) -> cas.Hogar:
    """El hogar **sin escribir nada**, para los caminos de sólo lectura.

    Quien no tiene fila todavía no ha empezado su estancia, y aquí se le trata
    como si acabara de entrar al refugio. Es lo correcto y además evita dos
    cosas feas: coger el cerrojo de escritura cada vez que alguien mira una
    ficha, y estrenarle el refugio a otra persona sólo por haber mirado su
    gachamon con `/mascota @alguien`.
    """
    fila = con.execute(
        "SELECT refugio_hasta, publica FROM hogar "
        "WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    ).fetchone()
    casas = _casas_de(con, usuario_id, guild_id)
    if fila is None:
        return cas.Hogar(
            casas=casas, refugio_hasta=cas.estancia_desde(ahora)
        )
    return cas.Hogar(
        casas=casas,
        refugio_hasta=datetime.fromisoformat(fila["refugio_hasta"]),
        publica=bool(fila["publica"]),
    )


def _casas_de(
    con: sqlite3.Connection, usuario_id: str, guild_id: str
) -> tuple[cas.CasaPropia, ...]:
    """Las casas de alguien con sus muebles dentro, en orden de compra.

    El orden es el de `id` y no el de tamaño: es el que quien juega reconoce
    —«la primera que compré»— y el que hace que los menús no le bailen debajo
    del dedo al comprar otra.

    Una casa cuya clave ya no esté en el catálogo se salta: si algún día se
    retira un tamaño, nadie se queda con una casa que el juego no sabe dibujar.
    """
    muebles: dict[int, list[str]] = {}
    for fila in con.execute(
        "SELECT mueble, casa_id FROM mobiliario "
        "WHERE usuario_id = ? AND guild_id = ? AND colocado = 1 "
        "AND casa_id IS NOT NULL",
        (usuario_id, guild_id),
    ):
        muebles.setdefault(fila["casa_id"], []).append(fila["mueble"])

    propias = []
    for fila in con.execute(
        "SELECT id, casa FROM casas_propias "
        "WHERE usuario_id = ? AND guild_id = ? ORDER BY id",
        (usuario_id, guild_id),
    ):
        casa = cas.CATALOGO.get(fila["casa"])
        if casa is None:
            continue
        propias.append(cas.CasaPropia(
            id=fila["id"], casa=casa,
            puestos=tuple(muebles.get(fila["id"], ())),
        ))
    return tuple(propias)


def huerto_de(
    usuario_id: str, guild_id: str, casa_id: int, cuantos: int
) -> list[hue.Bancal]:
    """Los bancales que da tu casa, plantados o en barbecho.

    Se devuelven **todos**, no sólo los que tienen fila: un bancal vacío es algo
    que enseñar y donde plantar, no una ausencia. Y si te mudas a una casa menor
    —que hoy no se puede— los de más se quedarían fuera sin borrar nada.
    """
    with conectar() as con:
        return _huerto_de(con, usuario_id, guild_id, casa_id, cuantos)


def _huerto_de(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, casa_id: int,
    cuantos: int,
) -> list[hue.Bancal]:
    filas = {
        f["bancal"]: f
        for f in con.execute(
            "SELECT bancal, plantado_en, regado, sembrado FROM huerto "
            "WHERE usuario_id = ? AND guild_id = ? AND casa_id = ?",
            (usuario_id, guild_id, casa_id),
        ).fetchall()
    }
    bancales = []
    for numero in range(1, cuantos + 1):
        fila = filas.get(numero)
        bancales.append(hue.Bancal(
            casa_id=casa_id,
            numero=numero,
            plantado_en=(
                datetime.fromisoformat(fila["plantado_en"]) if fila else None
            ),
            regado=bool(fila["regado"]) if fila else False,
            sembrado=fila["sembrado"] if fila else hue.SEMILLA,
        ))
    return bancales


def plantar_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str,
    casa_id: int, bancal: int, ahora: datetime, que: str = hue.SEMILLA,
) -> None:
    con.execute(
        "INSERT INTO huerto "
        "(usuario_id, guild_id, casa_id, bancal, plantado_en, regado, sembrado) "
        "VALUES (?, ?, ?, ?, ?, 0, ?) "
        "ON CONFLICT(usuario_id, guild_id, casa_id, bancal) DO UPDATE SET "
        "plantado_en = excluded.plantado_en, regado = 0, "
        "sembrado = excluded.sembrado",
        (usuario_id, guild_id, casa_id, bancal, ahora.isoformat(), que),
    )


def regar_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, casa_id: int,
    bancal: int,
) -> None:
    con.execute(
        "UPDATE huerto SET regado = 1 "
        "WHERE usuario_id = ? AND guild_id = ? AND casa_id = ? AND bancal = ?",
        (usuario_id, guild_id, casa_id, bancal),
    )


def arrancar_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, casa_id: int,
    bancal: int,
) -> None:
    """Deja el bancal en barbecho. Se llama al cosechar."""
    con.execute(
        "DELETE FROM huerto WHERE usuario_id = ? AND guild_id = ? "
        "AND casa_id = ? AND bancal = ?",
        (usuario_id, guild_id, casa_id, bancal),
    )


def guardar_en_la_mochila_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, clave: str,
    cuantos: int = 1,
) -> None:
    con.execute(
        "INSERT INTO inventario (usuario_id, guild_id, objeto, cantidad) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(usuario_id, guild_id, objeto) "
        "DO UPDATE SET cantidad = cantidad + excluded.cantidad",
        (usuario_id, guild_id, clave, cuantos),
    )


def gastar_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, clave: str,
    cuantos: int = 1,
) -> bool:
    """Descuenta varias unidades de golpe, o ninguna si no llegan."""
    gastado = con.execute(
        "UPDATE inventario SET cantidad = cantidad - ? "
        "WHERE usuario_id = ? AND guild_id = ? AND objeto = ? AND cantidad >= ?",
        (cuantos, usuario_id, guild_id, clave, cuantos),
    ).rowcount > 0
    con.execute(
        "DELETE FROM inventario WHERE usuario_id = ? AND guild_id = ? "
        "AND objeto = ? AND cantidad <= 0",
        (usuario_id, guild_id, clave),
    )
    return gastado


def hogar_leido(usuario_id: str, guild_id: str, ahora: datetime) -> cas.Hogar:
    """El hogar de alguien sin tocarle nada. Es lo que mira `/visitar`."""
    with conectar() as con:
        return _hogar_leido(con, usuario_id, guild_id, ahora)


def abrir_o_cerrar_la_casa(
    usuario_id: str, guild_id: str, publica: bool, ahora: datetime
) -> None:
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        _hogar_de(con, usuario_id, guild_id, ahora)      # la crea si no está
        con.execute(
            "UPDATE hogar SET publica = ? WHERE usuario_id = ? AND guild_id = ?",
            (int(publica), usuario_id, guild_id),
        )


def avanzar(criatura: sim.Criatura, ahora: datetime) -> sim.Criatura:
    """`sim.avanzar` con el ritmo que le toca por su hogar.

    Existe para que **no haya catorce sitios** teniendo que acordarse de mirar la
    casa antes de hacer pasar el tiempo. Quien llame a `sim.avanzar` a secas se
    queda con el ritmo de siempre, que es el de quien tiene techo: el fallo por
    olvido es el comportamiento anterior y nunca uno peor.
    """
    with conectar() as con:
        return _avanzar_en(con, criatura, ahora)


def _avanzar_en(
    con: sqlite3.Connection, criatura: sim.Criatura, ahora: datetime
) -> sim.Criatura:
    """La versión para quien ya tiene una transacción abierta.

    Hace falta la pareja porque abrir una segunda conexión dentro de un
    `BEGIN IMMEDIATE` ajeno se quedaría esperando a sí misma.
    """
    hogar = _hogar_leido(con, criatura.usuario_id, criatura.guild_id, ahora)
    # El ritmo sale de **su** casa y no de las de su dueño: con varias, dos
    # gachamones de la misma persona pueden vivir en sitios distintos, y quien
    # no cabe en ninguna está en el refugio aunque el dueño tenga tres.
    return sim.avanzar(
        criatura, ahora, cas.ritmo_de(hogar, ahora, criatura.casa_id)
    )


def vender_la_casa_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, casa_id: int,
    ahora: datetime,
) -> int:
    """Quita **esa** casa y recoloca lo que había dentro. Devuelve los muebles
    guardados.

    Tres cosas hay que recoger, y las tres en esta misma transacción:

    * **Sus inquilinos** se van al refugio —`casa_id` a `NULL`—. Sin esto
      apuntarían a una casa que ya no existe, y aunque `casa_por_id` lo trata
      como refugio, dejar punteros rotos en la base es pedir un fallo raro más
      adelante.
    * **Sus muebles** se descuelgan y se guardan: retirar uno nunca lo destruye,
      que es el invariante de siempre.
    * **Lo plantado en sus bancales se pierde**, porque la tierra era de esa
      casa. Los bancales de las otras no se tocan, y por eso el borrado va por
      `casa_id` y no por persona.

    El reloj del refugio **no se toca**: es de la persona, y quien vende una de
    tres casas no se ha quedado sin techo.
    """
    con.execute(
        "UPDATE criaturas SET casa_id = NULL "
        "WHERE usuario_id = ? AND guild_id = ? AND casa_id = ?",
        (usuario_id, guild_id, casa_id),
    )
    guardados = con.execute(
        "UPDATE mobiliario SET colocado = 0, casa_id = NULL "
        "WHERE usuario_id = ? AND guild_id = ? AND casa_id = ?",
        (usuario_id, guild_id, casa_id),
    ).rowcount
    con.execute(
        "DELETE FROM huerto WHERE usuario_id = ? AND guild_id = ? AND casa_id = ?",
        (usuario_id, guild_id, casa_id),
    )
    con.execute("DELETE FROM casas_propias WHERE id = ?", (casa_id,))

    # Vender la **última** devuelve la semana entera de refugio: quien se queda
    # sin nada no puede acabar en la calle de golpe. Vendiendo una de tres no
    # pasa nada de eso —sigue teniendo techo—, y así el reloj no se puede
    # refrescar comprando y vendiendo una casa barata en bucle.
    quedan = con.execute(
        "SELECT COUNT(*) AS n FROM casas_propias "
        "WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    ).fetchone()["n"]
    if not quedan:
        con.execute(
            "UPDATE hogar SET refugio_hasta = ? "
            "WHERE usuario_id = ? AND guild_id = ?",
            (cas.estancia_desde(ahora).isoformat(), usuario_id, guild_id),
        )
    return guardados


def anadir_casa_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, clave: str,
    ahora: datetime,
) -> int:
    """Le añade una casa y devuelve su id, que es con lo que se la referencia."""
    cursor = con.execute(
        "INSERT INTO casas_propias (usuario_id, guild_id, casa, comprada_en) "
        "VALUES (?, ?, ?, ?)",
        (usuario_id, guild_id, clave, ahora.isoformat()),
    )
    return int(cursor.lastrowid or 0)


def mejorar_casa_en(con: sqlite3.Connection, casa_id: int, clave: str) -> None:
    """Cambia el tamaño de una casa sin moverle nada de lo que hay dentro.

    Los inquilinos, los muebles y los bancales apuntan al `id`, que no cambia,
    así que mejorar es de verdad una obra y no una mudanza.
    """
    con.execute(
        "UPDATE casas_propias SET casa = ? WHERE id = ?", (clave, casa_id)
    )


def inquilinos_de(usuario_id: str, guild_id: str) -> dict[int | None, int]:
    """Cuántos gachamones vivos hay en cada casa, para las pantallas."""
    with conectar() as con:
        return inquilinos_en(con, usuario_id, guild_id)


def inquilinos_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str
) -> dict[int | None, int]:
    """Cuántos gachamones vivos hay en cada casa. `None` es el refugio."""
    return {
        fila["casa_id"]: fila["cuantos"]
        for fila in con.execute(
            "SELECT casa_id, COUNT(*) AS cuantos FROM criaturas "
            "WHERE usuario_id = ? AND guild_id = ? AND muerta_en IS NULL "
            "GROUP BY casa_id",
            (usuario_id, guild_id),
        )
    }


def acoger_a_los_sin_casa_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, casa_id: int,
    aforo: int,
) -> int:
    """Mete en esa casa a los que estén sin ninguna, hasta llenarla.

    Los más viejos primero, que es el orden en que se ven en todas partes.
    Devuelve cuántos entraron.
    """
    sitio = aforo - inquilinos_en(con, usuario_id, guild_id).get(casa_id, 0)
    if sitio <= 0:
        return 0
    sin_casa = [
        fila["id"] for fila in con.execute(
            "SELECT id FROM criaturas WHERE usuario_id = ? AND guild_id = ? "
            "AND muerta_en IS NULL AND casa_id IS NULL ORDER BY id LIMIT ?",
            (usuario_id, guild_id, sitio),
        )
    ]
    for criatura_id in sin_casa:
        con.execute(
            "UPDATE criaturas SET casa_id = ? WHERE id = ?", (casa_id, criatura_id)
        )
    return len(sin_casa)


def mudar_criatura_en(
    con: sqlite3.Connection, criatura_id: int, casa_id: int | None
) -> None:
    con.execute(
        "UPDATE criaturas SET casa_id = ? WHERE id = ?", (casa_id, criatura_id)
    )


# --- El mobiliario ---------------------------------------------------------

def mobiliario(usuario_id: str, guild_id: str) -> dict[str, bool]:
    """Los muebles que tienes y si están puestos. Los guardados salen a `False`."""
    with conectar() as con:
        return _mobiliario(con, usuario_id, guild_id)


def _mobiliario(
    con: sqlite3.Connection, usuario_id: str, guild_id: str
) -> dict[str, bool]:
    filas = con.execute(
        "SELECT mueble, colocado FROM mobiliario "
        "WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    ).fetchall()
    return {f["mueble"]: bool(f["colocado"]) for f in filas}


def puestos(usuario_id: str, guild_id: str) -> tuple[str, ...]:
    """Sólo los que están dentro de la casa, que son los que dan comodidad."""
    return tuple(c for c, dentro in mobiliario(usuario_id, guild_id).items() if dentro)


def comprar_mueble_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str,
    clave: str, colocado: bool, casa_id: int | None = None,
) -> None:
    con.execute(
        "INSERT INTO mobiliario (usuario_id, guild_id, mueble, colocado, casa_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (usuario_id, guild_id, clave, int(colocado),
         casa_id if colocado else None),
    )


def colocar_mueble_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str,
    clave: str, dentro: bool, casa_id: int | None = None,
) -> None:
    """Cuelga o descuelga un mueble, y en cuál de tus casas.

    Al retirarlo se borra también la casa: un mueble guardado no está en
    ninguna parte, y dejarle la casa vieja haría que reaparecer allí al volver a
    colocarlo pareciera magia.
    """
    con.execute(
        "UPDATE mobiliario SET colocado = ?, casa_id = ? "
        "WHERE usuario_id = ? AND guild_id = ? AND mueble = ?",
        (int(dentro), casa_id if dentro else None, usuario_id, guild_id, clave),
    )


def especies_de(usuario_id: str, guild_id: str) -> tuple[str, ...]:
    """Las especies que ha tenido, **vivas y muertas**.

    Es lo que alimenta «Uno entre veinticinco»: que te saliera una rara no deja
    de haber pasado porque se te muriera.
    """
    with conectar() as con:
        return _especies_de(con, usuario_id, guild_id)


def _especies_de(
    con: sqlite3.Connection, usuario_id: str, guild_id: str
) -> tuple[str, ...]:
    filas = con.execute(
        "SELECT DISTINCT especie FROM criaturas "
        "WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    ).fetchall()
    return tuple(f["especie"] for f in filas)


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
