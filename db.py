"""Persistencia en SQLite. Sigue el patrón de rowino_web/db.py.

Las consultas son síncronas dentro del bucle de eventos de discord.py. Con una
base de datos local de unas pocas decenas de filas cada operación tarda menos de
un milisegundo, así que meter una capa async sólo añadiría complejidad.

El paso del tiempo no se guarda en ningún reloj: cada criatura lleva cuándo se
actualizó por última vez, y sus barras se calculan al leerla (`avanzar`).
Ningún gachamon muere, así que tampoco hay instante de muerte ni de aviso que
guardar: `muere_en`, `avisa_en` y `avisada` siguen en el esquema, las dos
primeras siempre vacías y `avisada` siempre en 0.
"""
from __future__ import annotations

import json
import logging
import random
import sqlite3
from collections.abc import Callable, Collection
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import avatar as av
import config
import cosmeticos as cos
import departamento as dep
import especies as esp
import identidad
import logros as lgr
import nombres
import objetos as obj
import personalidad as per
import simulacion as sim
import vinculo

logger = logging.getLogger(__name__)

RUTA: Path = config.RUTA_BD

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
-- cada una tiene la suya y la de una recién llegada empieza de cero sin código
-- extra.
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

-- El monedero y los objetos son de la PERSONA, no de la criatura: lo comprado
-- sirve para cualquiera de sus gachamones. Por servidor, como todo lo demás.
CREATE TABLE IF NOT EXISTS inventario (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    objeto TEXT NOT NULL,
    cantidad INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (usuario_id, guild_id, objeto)
);

-- Los efectos sí van atados a la criatura: es ella la que se envalentona, y
-- no se los pasa a nadie. La clave primaria (criatura_id, stat) **es** la
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
-- suyo y no de su dueño.
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
-- —convencer salvajes y que te salga una rara los haces tú— y ésas son tuyas
-- tengas el gachamon que tengas, que es justamente lo que las distingue.
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

-- Lo que se devolvió por cada cosmético retirado. Es el registro y, a la vez, la
-- garantía de que no se paga dos veces: la clave primaria deja entrar una sola
-- vez a cada persona + pieza, y sólo quien consigue la fila cobra.
CREATE TABLE IF NOT EXISTS devoluciones (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    cosmetico TEXT NOT NULL,
    gemas INTEGER NOT NULL CHECK (gemas > 0),
    devuelta_en TEXT NOT NULL,
    PRIMARY KEY (usuario_id, guild_id, cosmetico)
);

-- Las compras que no deben hacerse dos veces aunque la petición se repita: la
-- web reenvía el mismo evento cuando no le llega la respuesta. Se anota sólo lo
-- que salió bien, en la transacción que lo hizo; la clave primaria es la que
-- impide que el mismo evento de la misma persona cobre otra vez.
CREATE TABLE IF NOT EXISTS acciones_unicas (
    evento_id  TEXT NOT NULL,
    usuario_id TEXT NOT NULL,
    guild_id   TEXT NOT NULL,
    accion     TEXT NOT NULL,
    solicitud  TEXT NOT NULL,
    resultado  TEXT NOT NULL,
    cuando     TEXT NOT NULL,
    PRIMARY KEY (evento_id, usuario_id, guild_id, accion)
);

-- Quién es en el juego cada cuenta de Rowino (la web). Antes de vincular es una
-- identidad web (`usuario_id` negativo); al canjear un código pasa a ser la
-- persona de Discord, con `vinculada = 1`. Una persona de Discord sólo puede
-- tener una cuenta por servidor, de ahí el UNIQUE.
CREATE TABLE IF NOT EXISTS cuentas_web (
    rowino_uid INTEGER PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    vinculada INTEGER NOT NULL DEFAULT 0,
    creada_en TEXT NOT NULL,
    difuntos_vistos_hasta TEXT,
    lugar TEXT,
    UNIQUE (usuario_id, guild_id)
);

-- Códigos de un solo uso para vincular una cuenta de Rowino con Discord. Cada
-- cuenta tiene como mucho uno vivo (UNIQUE sobre `rowino_uid`).
CREATE TABLE IF NOT EXISTS vinculos_pendientes (
    codigo TEXT PRIMARY KEY,
    rowino_uid INTEGER NOT NULL UNIQUE,
    vence_en TEXT NOT NULL
);

-- Cada vez que alguien escribe un código cuenta un intento, sea bueno o no:
-- es lo que impide adivinarlos probando.
CREATE TABLE IF NOT EXISTS intentos_de_vinculo (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    en TEXT NOT NULL
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

-- La vivienda de antes: `hogar`, `casas_propias`, `mobiliario` y `huerto`. Ya no
-- las usa ninguna regla; el día del cambio (`economia.el_dia_del_cambio`)
-- convierte una sola vez lo que tenga cada quien. Se quedan para que una base
-- vieja pueda llegar hasta ese día, y `_migrar_casas` sigue corriendo.
--
-- El reloj del refugio de cada persona, y si dejaba mirar lo suyo. Sus casas
-- iban aparte, en `casas_propias`: aquí sólo quedaba lo que era de la persona y
-- no de una casa concreta.
CREATE TABLE IF NOT EXISTS hogar (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    refugio_hasta TEXT NOT NULL,
    publica INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (usuario_id, guild_id)
);

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

-- Los bancales del huerto de cada casa, numerados dentro de ella. Sin fila era
-- barbecho.
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

-- Cada casa que alguien tenía, una por fila; los gachamones, los muebles y los
-- bancales apuntaban a una en concreto por su `id`.
CREATE TABLE IF NOT EXISTS casas_propias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    casa TEXT NOT NULL,
    comprada_en TEXT NOT NULL
);

-- Los muebles de antes, uno de cada por persona: `colocado` decía si estaba
-- puesto, y `casa_id` en cuál de sus casas.
CREATE TABLE IF NOT EXISTS mobiliario (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    mueble TEXT NOT NULL,
    colocado INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (usuario_id, guild_id, mueble)
);

-- El departamento de cada persona: una cuadrícula de `ancho × fondo` casillas
-- (`departamento.py`). Uno por persona y servidor, y lo impone la clave
-- primaria; los `CHECK` son los lados que admite, de 3 a 8. Nace la primera vez
-- que se mira, como `dep.DE_PARTIDA`.
CREATE TABLE IF NOT EXISTS departamentos (
    usuario_id TEXT NOT NULL, guild_id TEXT NOT NULL,
    ancho INTEGER NOT NULL DEFAULT 3 CHECK (ancho BETWEEN 3 AND 8),
    fondo INTEGER NOT NULL DEFAULT 3 CHECK (fondo BETWEEN 3 AND 8),
    creado_en TEXT NOT NULL,
    PRIMARY KEY (usuario_id, guild_id));

-- Sus muebles, uno por fila. A diferencia de `mobiliario` se pueden tener
-- varios iguales, y por eso cada uno tiene su `id`: es lo que se pone o se
-- guarda. Dónde está lo dicen `x` e `y`, y el esquema no admite media posición.
CREATE TABLE IF NOT EXISTS muebles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id TEXT NOT NULL, guild_id TEXT NOT NULL, mueble TEXT NOT NULL,
    x INTEGER, y INTEGER,                         -- las dos vacías: guardado
    giro INTEGER NOT NULL DEFAULT 0 CHECK (giro BETWEEN 0 AND 3),
    CHECK ((x IS NULL) = (y IS NULL)));

-- El avatar de quien juega en la web: nombre, género, piel, pelo y ropa. Es de
-- la persona (identidad + servidor), no de un gachamon.
CREATE TABLE IF NOT EXISTS avatares (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    nombre TEXT NOT NULL,
    genero TEXT NOT NULL,
    piel TEXT NOT NULL,
    pelo TEXT NOT NULL,
    color_de_pelo TEXT NOT NULL,
    ropa TEXT NOT NULL,
    actualizado_en TEXT NOT NULL,
    PRIMARY KEY (usuario_id, guild_id)
);

-- Los cambios de reglas que tocan filas y se hacen una sola vez, con su
-- instante. La clave primaria es lo que impide hacerlos dos veces: la apunta
-- `_una_sola_vez` en la misma transacción que el cambio.
CREATE TABLE IF NOT EXISTS cambios_hechos (
    clave TEXT PRIMARY KEY,
    hecho_en TEXT NOT NULL
);

-- Las cartas que le llegan a cada quien, una de cada clave: la primera es la
-- del alcalde el día del cambio. `contenido` es JSON con lo que cuenta, en
-- datos y no en frases (las frases las pone la web), y `vista_en` vacía es que
-- todavía no la ha visto.
CREATE TABLE IF NOT EXISTS cartas (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    carta TEXT NOT NULL,
    contenido TEXT NOT NULL,
    escrita_en TEXT NOT NULL,
    vista_en TEXT,
    PRIMARY KEY (usuario_id, guild_id, carta)
);

"""

SCHEMA_INDICES = """
-- Una sola criatura ACTIVA por persona y servidor. Antes era «una sola viva»;
-- desde que se puede tener un plantel, lo que hay que garantizar es que no haya
-- dos recibiendo los comandos a la vez. Lo sigue garantizando la base de datos y
-- no el código, que era el motivo original: dos clics simultáneos no pueden
-- dejar dos activas. La cama libre no cabe en un índice y se comprueba en
-- `crear()`.
CREATE UNIQUE INDEX IF NOT EXISTS una_activa
    ON criaturas(usuario_id, guild_id) WHERE muerta_en IS NULL AND activa = 1;

CREATE INDEX IF NOT EXISTS idx_conversacion
    ON conversaciones(criatura_id, id);

CREATE INDEX IF NOT EXISTS idx_uso_ia
    ON uso_ia(usuario_id, cuando);

CREATE INDEX IF NOT EXISTS idx_cupo
    ON operaciones_economia(usuario_id, guild_id, fecha_utc, tipo);

CREATE INDEX IF NOT EXISTS idx_muebles
    ON muebles(usuario_id, guild_id);
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
    "se_nombro_solo",
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
    # En qué casa de su dueño vivía. `NULL` era el refugio. Lo rellena
    # `_migrar_casas` para las que ya existían, y lo vacía el día del cambio.
    ("casa_id", "ALTER TABLE criaturas ADD COLUMN casa_id INTEGER"),
    # Si el nombre se lo puso él solo, como un recluta al unirse. Los que ya
    # tenían nombre se lo puso su dueño, y el DEFAULT los deja en 0; a los que
    # lo esperaban se lo pone `_migrar` y los marca.
    ("se_nombro_solo",
     "ALTER TABLE criaturas ADD COLUMN se_nombro_solo INTEGER NOT NULL DEFAULT 0"),
)

# Lo mismo, para tablas que no son `criaturas`. Van aparte porque `MIGRACIONES`
# mira sólo el `PRAGMA` de aquélla, que es donde habían caído todas hasta ahora.
MIGRACIONES_DE_TABLAS = (
    # Las casas nacieron todas visibles y así se quedan las que ya existían.
    ("hogar", "publica",
     "ALTER TABLE hogar ADD COLUMN publica INTEGER NOT NULL DEFAULT 1"),
    # Antes sólo se sembraban semillas, así que no había nada que guardar. El
    # `DEFAULT` deja a los bancales que ya estaban creciendo tal y como se
    # plantaron: semilla, y color al azar al cosechar. Ninguna fila que tocar.
    ("huerto", "sembrado",
     "ALTER TABLE huerto ADD COLUMN sembrado TEXT NOT NULL DEFAULT 'semilla'"),
    # En qué casa colgaba cada mueble. `NULL` con `colocado = 1` es lo que deja
    # `_migrar_casas` a quien no tenía casa; el día del cambio lo guarda como a
    # todos.
    ("mobiliario", "casa_id", "ALTER TABLE mobiliario ADD COLUMN casa_id INTEGER"),
    # Hasta cuándo la web había contado las muertes de esa cuenta. Ya no se
    # cuentan, y nadie la lee ni la escribe: se queda para no rehacer la tabla.
    ("cuentas_web", "difuntos_vistos_hasta",
     "ALTER TABLE cuentas_web ADD COLUMN difuntos_vistos_hasta TEXT"),
    # El último lugar del pueblo al que llegó la cuenta. Vacía, vale el de partida.
    ("cuentas_web", "lugar", "ALTER TABLE cuentas_web ADD COLUMN lugar TEXT"),
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


def inicializar(ahora: datetime | None = None) -> None:
    """Prepara la base. `ahora` es el instante de los cambios que se hacen una
    sola vez; sin él, el de `ahora_utc()`."""
    if ahora is None:
        ahora = ahora_utc()
    with conectar() as con:
        con.executescript(SCHEMA_TABLAS)
        _migrar(con, ahora)
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

    Las casas ya no tienen reglas (las convierte el día del cambio); esta
    migración se queda para que una base vieja pueda llegar hasta ese día.

    Es la segunda migración del proyecto que mueve datos —tras la de
    `operaciones_economia`—, así que va sola en su transacción y con su test
    sobre filas de verdad. Dos tablas hay que recrearlas porque SQLite no deja
    quitar una columna de una clave primaria ni añadirla:

    * `hogar` pierde `casa`, que se lleva `casas_propias`.
    * `huerto` gana `casa_id` en la clave, para que los bancales se numeren
      dentro de cada casa y vender una no renumerara los de las demás.

    **Nadie pierde su sitio.** Cada casa que hubiera pasa a ser una fila de
    `casas_propias`, y todo lo de esa persona —sus gachamones vivos, sus
    bancales y sus muebles colgados— queda apuntado a ella, aunque sean más
    gachamones de los que cabían: el aforo frenaba las mudanzas nuevas, no
    desalojaba a quien ya estaba.

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


def _una_sola_vez(con: sqlite3.Connection, clave: str, ahora: datetime) -> bool:
    """Apunta el cambio `clave` hecho en `ahora` y dice si es la primera vez.

    Va dentro de la transacción de quien hace el cambio, que es la que lo
    serializa: la marca y el cambio se confirman juntos o ninguno. No abre
    conexión ni transacción propias.
    """
    return con.execute(
        "INSERT OR IGNORE INTO cambios_hechos (clave, hecho_en) VALUES (?, ?)",
        (clave, ahora.isoformat()),
    ).rowcount == 1


def _nombrar_a_los_que_lo_esperaban(
    con: sqlite3.Connection, rng: random.Random
) -> None:
    """Le pone nombre a cada fila que no lo tiene, y lo marca como suyo.

    Un recluta llega ya con un nombre que se pone él solo; los que se unieron
    antes se quedaron esperando a que se lo pusieran, y se lo ponen aquí: uno
    de `nombres.NOMBRES` que no sea el de su especie ni el de otro vivo de su
    dueño. Fila a fila y no de una pasada, como el carácter, y releyendo los
    vivos de cada dueño: así cuentan también los que se acaban de poner.

    Va sin marca de una sola vez: cuando no queda ninguna fila sin nombre no
    encuentra nada que hacer, y repetirlo no cambia nada. El azar lo pone
    quien llama, para que una prueba pueda fijarlo.
    """
    for fila in con.execute(
        "SELECT id, usuario_id, guild_id, especie FROM criaturas "
        "WHERE nombre = '' ORDER BY id"
    ).fetchall():
        evitar = [
            otra["nombre"] for otra in con.execute(
                "SELECT nombre FROM criaturas WHERE usuario_id = ? "
                "AND guild_id = ? AND muerta_en IS NULL",
                (fila["usuario_id"], fila["guild_id"]),
            )
        ]
        # Si su especie ya no existe no hay nombre de especie que evitar, y
        # buscarla con `[]` tiraría el arranque (ver el ingenio, más abajo).
        especie = esp.ESPECIES.get(fila["especie"])
        if especie is not None:
            evitar.append(especie.nombre)
        con.execute(
            "UPDATE criaturas SET nombre = ?, se_nombro_solo = 1 WHERE id = ?",
            (nombres.elegir(rng, evitar), fila["id"]),
        )


def _ascender_un_relevo_donde_falte(con: sqlite3.Connection) -> None:
    """Hace activo al vivo de menor id de cada plantel vivo que no tiene activo.

    Hay quien se quedó así: el activo se le murió cuando todavía se moría y
    sólo le quedaban reclutas que no podían salir. Por la web lo arreglaba el
    remiendo de `activa_al_dia`, pero en Discord nadie lo corría. Elige al mismo
    que `ascender_un_relevo`, y el remiendo se queda por si acaso.

    Tiene que ir **después** del paso del reloj, que sólo mira a los que no
    son el activo: si fuera antes, al ascendido no se le movería el reloj y se
    le cobraría de golpe todo lo que durmió. Y después del de los nombres, así
    que el que sale ya lleva el suyo.

    Va sin marca de una sola vez: cuando todo plantel vivo tiene su activo no
    encuentra nada que hacer, y repetirlo no cambia nada. Sólo asciende a uno
    por persona y servidor donde no había ninguno, así que el índice
    `una_activa` no puede saltar.
    """
    con.execute(
        "UPDATE criaturas SET activa = 1 WHERE id IN ("
        "    SELECT MIN(id) FROM criaturas WHERE muerta_en IS NULL"
        "     GROUP BY usuario_id, guild_id HAVING MAX(activa) = 0)"
    )


def _migrar(con: sqlite3.Connection, ahora: datetime) -> None:
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

    # A todos los vivos les pasa el tiempo, no sólo a la activa. Las demás
    # tenían el reloj parado desde la última vez que se guardaron, y el primer
    # `avanzar` les cobraría de golpe todo ese tiempo: su día empieza el del
    # cambio. Una sola vez, y la marca va en esta misma transacción.
    if _una_sola_vez(con, "el_tiempo_para_todos", ahora):
        con.execute(
            "UPDATE criaturas SET actualizada_en = ? "
            "WHERE muerta_en IS NULL AND activa = 0",
            (ahora.isoformat(),),
        )

    # El índice viejo prohibía una segunda criatura viva; el nuevo sólo prohíbe
    # una segunda ACTIVA. Se tira aquí y no en el script de índices porque
    # `executescript` no borra: hay que quitarlo antes de crear el que lo
    # sustituye, y este paso corre justo entre las tablas y los índices.
    con.execute("DROP INDEX IF EXISTS una_viva")

    # Nadie se muere de hambre ya, así que no queda instante de muerte ni de
    # aviso que guardar. Las columnas se quedan —quitarlas obligaría a rehacer
    # la tabla—, pero vacías: a quien ya le tocaba morir sigue vivo con la
    # comida en 0. Se van los dos índices que las recorrían y la tabla de las
    # muertes que la web dejaba para que el bot las anunciara; lo que quedara
    # pendiente en ella no se anuncia. Como con `una_viva`, se tiran aquí
    # porque los scripts del esquema sólo crean. Repetirlo no hace nada: los
    # `DROP` llevan `IF EXISTS` y el `UPDATE` ya no encuentra filas.
    con.execute("DROP INDEX IF EXISTS idx_muere")
    con.execute("DROP INDEX IF EXISTS idx_avisa")
    con.execute("DROP TABLE IF EXISTS muertes_por_anunciar")
    con.execute(
        "UPDATE criaturas SET muere_en = NULL, avisa_en = NULL, avisada = 0 "
        "WHERE muere_en IS NOT NULL OR avisa_en IS NOT NULL OR avisada != 0"
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

    _nombrar_a_los_que_lo_esperaban(con, rng)
    _ascender_un_relevo_donde_falte(con)

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
    datos["se_nombro_solo"] = bool(datos["se_nombro_solo"])
    return sim.Criatura(id=fila["id"], **datos)


def _a_valores(criatura: sim.Criatura) -> dict:
    datos = {c: getattr(criatura, c) for c in CAMPOS}
    for campo in ("nacida_en", "actualizada_en", "muerta_en"):
        valor = datos[campo]
        datos[campo] = valor.isoformat() if valor else None
    datos["activa"] = int(criatura.activa)
    datos["se_nombro_solo"] = int(criatura.se_nombro_solo)
    # Ni instante de muerte ni aviso de hambre: nadie se muere. Las columnas
    # siguen en el esquema y se escriben vacías en cada guardado.
    datos["avisada"] = 0
    datos["muere_en"] = None
    datos["avisa_en"] = None
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


def criatura_en(
    con: sqlite3.Connection, criatura_id: int
) -> sim.Criatura | None:
    fila = con.execute(
        "SELECT * FROM criaturas WHERE id = ?", (criatura_id,)
    ).fetchone()
    return _a_criatura(fila) if fila else None


def criatura_elegida_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, criatura_id: int | None
) -> sim.Criatura | None:
    """A quién le cae un cuidado o una caricia.

    Sin `criatura_id`, al activo. Con él, a ese gachamon si es de esa persona,
    de ese servidor y está vivo. `None` si no hay a quién.
    """
    if criatura_id is None:
        return criatura_activa_en(con, usuario_id, guild_id)
    criatura = criatura_en(con, criatura_id)
    if (
        criatura is None
        or criatura.usuario_id != usuario_id
        or criatura.guild_id != guild_id
        or not criatura.viva
    ):
        return None
    return criatura


def por_id(criatura_id: int) -> sim.Criatura | None:
    with conectar() as con:
        fila = con.execute(
            "SELECT * FROM criaturas WHERE id = ?", (criatura_id,)
        ).fetchone()
    return _a_criatura(fila) if fila else None


def ascender_un_relevo(
    usuario_id: str, guild_id: str
) -> sim.Criatura | None:
    """Hace activo al primero vivo si no queda ningún activo.

    Es el remiendo de `activa_al_dia`. Sin esto, quien se quedó sin activo
    —porque se le murió cuando todavía se moría, por ejemplo— tendría
    gachamones vivos y el juego le diría que no tiene ninguno. Sólo cambia la
    marca, como `activar`: el reloj del relevo sigue donde estaba.
    """
    if criatura_activa(usuario_id, guild_id) is not None:
        return None
    vivas = plantel(usuario_id, guild_id)
    if not vivas:
        return None
    activar(vivas[0].id, usuario_id, guild_id)
    return criatura_activa(usuario_id, guild_id)


def activa_al_dia(
    usuario_id: str, guild_id: str, ahora: datetime
) -> sim.Criatura | None:
    """La activa, avanzada hasta `ahora`, sin guardarle el paso del tiempo.

    No escribe nunca, salvo el remiendo: si no hay activa y sí alguien vivo,
    lo hace el activo (`ascender_un_relevo`) y lo devuelve
    avanzado. Repetirla, o correrla desde dos procesos, deja una sola activa.
    Sin nadie que pueda serlo devuelve `None`.
    """
    activa = criatura_activa(usuario_id, guild_id)
    if activa is None:
        ascender_un_relevo(usuario_id, guild_id)
        activa = criatura_activa(usuario_id, guild_id)
        if activa is None:
            return None
    return avanzar(activa, ahora)


def plantel(usuario_id: str, guild_id: str) -> list[sim.Criatura]:
    """Las criaturas vivas de una persona, la activa primero."""
    with conectar() as con:
        return plantel_en(con, usuario_id, guild_id)


def plantel_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str
) -> list[sim.Criatura]:
    """Lo de `plantel`, para quien ya tiene la conexión."""
    filas = con.execute(
        "SELECT * FROM criaturas WHERE usuario_id = ? AND guild_id = ? "
        "AND muerta_en IS NULL ORDER BY activa DESC, id",
        (usuario_id, guild_id),
    ).fetchall()
    return [_a_criatura(f) for f in filas]


def plantel_al_dia(
    usuario_id: str, guild_id: str, ahora: datetime
) -> list[sim.Criatura]:
    """Los vivos, la activa primero, cada uno avanzado hasta `ahora` con el
    ritmo de su departamento. Sólo lee: no les guarda el paso del tiempo."""
    with conectar() as con:
        return [
            _avanzar_en(con, criatura, ahora)
            for criatura in plantel_en(con, usuario_id, guild_id)
        ]


def activar(criatura_id: int, usuario_id: str, guild_id: str) -> bool:
    """La hace el activo, el que sale contigo, en lugar del que lo era.

    Devuelve si se pudo: pide que la criatura sea de quien la reclama, para que
    un identificador copiado de otro mensaje no active la mascota de otro.

    Sólo cambia la marca `activa`: a todos les pasa el tiempo, salgan contigo o
    no, así que nadie se duerme ni se despierta y `actualizada_en` no se toca.
    """
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        fila = con.execute(
            "SELECT id FROM criaturas WHERE id = ? AND usuario_id = ? "
            "AND guild_id = ? AND muerta_en IS NULL",
            (criatura_id, usuario_id, guild_id),
        ).fetchone()
        if fila is None:
            return False
        _activar_en(con, criatura_id)
    return True


def _activar_en(con: sqlite3.Connection, criatura_id: int) -> None:
    """Lo de `activar` para quien ya tiene la transacción abierta y ya ha
    comprobado que esa criatura puede ser el activo.

    Primero todas a 0 y después ésa a 1: el índice `una_activa` no admite el
    orden contrario. Sólo se toca la marca, nunca `actualizada_en`.
    """
    dueño = con.execute(
        "SELECT usuario_id, guild_id FROM criaturas WHERE id = ?", (criatura_id,)
    ).fetchone()
    con.execute(
        "UPDATE criaturas SET activa = 0 "
        "WHERE usuario_id = ? AND guild_id = ? AND muerta_en IS NULL",
        (dueño["usuario_id"], dueño["guild_id"]),
    )
    con.execute("UPDATE criaturas SET activa = 1 WHERE id = ?", (criatura_id,))


def obtener(criatura_id: int) -> sim.Criatura | None:
    with conectar() as con:
        fila = con.execute(
            "SELECT * FROM criaturas WHERE id = ?", (criatura_id,)
        ).fetchone()
    return _a_criatura(fila) if fila else None


class IdentidadCaducada(Exception):
    """La identidad web ya no figura en `cuentas_web` (se vinculó)."""


class SinCamaLibre(ValueError):
    """No hay una cama puesta libre para quien llega.

    Hereda de `ValueError` porque quien recluta ya trata ese error como «no
    cabe».
    """


def hay_cama_libre(usuario_id: str, guild_id: str) -> bool:
    """Si a esa persona le cabe un gachamon más: sólo cuentan las camas puestas."""
    with conectar() as con:
        return dep.cama_libre(
            _departamento_leido(con, usuario_id, guild_id),
            len(plantel_en(con, usuario_id, guild_id)),
        )


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
    *,
    cuenta_vigente: bool = False,
    se_nombro_solo: bool = False,
    pide_cama: bool = False,
) -> sim.Criatura:
    """Registra una criatura recién nacida.

    Nadie nace sin nombre: con `nombre` vacío levanta `ValueError` y no crea
    nada.

    `activa=False` la crea sin hacerla la activa: no sale contigo, pero el
    tiempo le pasa igual. Lo usa el reclutamiento: uno que se une en una
    aventura no puede desbancar sin avisar al que llevabas.

    `reclutada` dice que llega de una aventura, y le apunta el reclutamiento a
    **la persona** aquí dentro: si el alta se cae por falta de cama, no
    puede quedar apuntado un salvaje que no llegó a unirse. No hace falta decir
    qué gachamon lo convenció porque la medalla ya no es suya: a la aventura va
    la persona, que es la misma que sale en esta fila.

    Dos defensas distintas y las dos hacen falta:

    - **La cama libre** se comprueba aquí dentro con `BEGIN IMMEDIATE`, porque
      no cabe en un índice, y sólo si `pide_cama`: levanta `SinCamaLibre` antes
      de insertar y de apuntar nada. Quien nace del huevo no la pide.
    - **Una sola activa** lo sigue imponiendo el índice único, que hace saltar
      `sqlite3.IntegrityError`: es la defensa contra romper dos huevos a la vez.

    `cuenta_vigente` sólo cuenta para una identidad web: comprueba, en esta
    misma transacción, que `cuentas_web` sigue teniéndola. Si no, levanta
    `IdentidadCaducada` y no crea nada: así no nace un huérfano justo después
    de vincular. Para una identidad de Discord no cambia nada.

    `se_nombro_solo` dice que `nombre` no lo eligió su dueño: es el del
    recluta, que se lo pone él solo (`nacer.unir_recluta`).
    """
    if not nombre:
        raise ValueError("una criatura nace con nombre")
    fuerza, velocidad, salud, ingenio = stats
    nueva = sim.Criatura(
        id=0, usuario_id=usuario_id, guild_id=guild_id, especie=especie,
        nombre=nombre, genero=genero, caracter=caracter,
        nacida_en=ahora, actualizada_en=ahora,
        base_fuerza=fuerza, base_velocidad=velocidad, base_salud=salud,
        base_ingenio=ingenio, canal_id=canal_id, activa=activa,
        se_nombro_solo=se_nombro_solo,
    )
    valores = _a_valores(nueva)
    columnas = list(valores)
    marcadores = ", ".join(f":{c}" for c in columnas)

    with conectar() as con:
        # El turno de escritura se toma antes de mirar las camas: si no, dos
        # peticiones a la vez podrían ver la misma cama libre y llenarla las dos.
        con.execute("BEGIN IMMEDIATE")
        if cuenta_vigente and identidad.es_web(usuario_id) and con.execute(
            "SELECT 1 FROM cuentas_web WHERE usuario_id = ? AND guild_id = ?",
            (usuario_id, guild_id),
        ).fetchone() is None:
            raise IdentidadCaducada(usuario_id)
        if pide_cama and not dep.cama_libre(
            _departamento_leido(con, usuario_id, guild_id),
            len(plantel_en(con, usuario_id, guild_id)),
        ):
            raise SinCamaLibre(
                f"{usuario_id} no tiene una cama libre en {guild_id}"
            )

        cursor = con.execute(
            f"INSERT INTO criaturas ({', '.join(columnas)}) VALUES ({marcadores})",
            valores,
        )
        nuevo_id = cursor.lastrowid
        if reclutada:
            apuntar_persona_en(con, usuario_id, guild_id, lgr.RECLUTADOS)

    return replace(nueva, id=nuevo_id)


def poner_nombre_a_la_activa(
    usuario_id: str,
    guild_id: str,
    nombre: str,
    puede: Callable[[sim.Criatura], bool],
) -> tuple[str, sim.Criatura | None]:
    """Le cambia sólo el nombre a la activa de esa persona, si `puede(activa)`.

    Relee la activa bajo `BEGIN IMMEDIATE` y no guarda nada más de ella que el
    nombre y que ya no se lo puso sola (`se_nombro_solo = 0`): se lo ha puesto
    su dueño. Devuelve `("sin_gachamon", None)`, `("no_puede", activa)` o
    `("hecho", activa_con_su_nombre)`.
    """
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        activa = criatura_activa_en(con, usuario_id, guild_id)
        if activa is None:
            return "sin_gachamon", None
        if not puede(activa):
            return "no_puede", activa
        con.execute(
            "UPDATE criaturas SET nombre = ?, se_nombro_solo = 0 WHERE id = ?",
            (nombre, activa.id),
        )
    return "hecho", replace(activa, nombre=nombre, se_nombro_solo=False)


def poner_nombre_a(
    usuario_id: str,
    guild_id: str,
    criatura_id: int,
    nombre: str,
    puede: Callable[[sim.Criatura], bool],
) -> tuple[str, sim.Criatura | None]:
    """Como `poner_nombre_a_la_activa`, pero a esa criatura, si es tuya y vive.

    Devuelve `("no_esta", None)`, `("no_puede", criatura)` o
    `("hecho", criatura_con_su_nombre)`. Sólo escribe `nombre`, y
    `se_nombro_solo = 0`.
    """
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        criatura = criatura_en(con, criatura_id)
        if (
            criatura is None
            or criatura.usuario_id != usuario_id
            or criatura.guild_id != guild_id
            or not criatura.viva
        ):
            return "no_esta", None
        if not puede(criatura):
            return "no_puede", criatura
        con.execute(
            "UPDATE criaturas SET nombre = ?, se_nombro_solo = 0 WHERE id = ?",
            (nombre, criatura.id),
        )
    return "hecho", replace(criatura, nombre=nombre, se_nombro_solo=False)


def guardar(criatura: sim.Criatura) -> None:
    with conectar() as con:
        _guardar(con, criatura)


def _guardar(con: sqlite3.Connection, criatura: sim.Criatura) -> None:
    valores = _a_valores(criatura)
    valores["id"] = criatura.id
    asignaciones = ", ".join(f"{c} = :{c}" for c in valores if c != "id")
    con.execute(f"UPDATE criaturas SET {asignaciones} WHERE id = :id", valores)


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


def publicaciones_de(canal_id: str) -> dict[int, str]:
    """Las páginas apuntadas en ese canal: índice → id del mensaje."""
    with conectar() as con:
        filas = con.execute(
            "SELECT indice, mensaje_id FROM publicaciones "
            "WHERE canal_id = ? ORDER BY indice",
            (canal_id,),
        ).fetchall()
    return {fila["indice"]: fila["mensaje_id"] for fila in filas}


def borrar_publicacion(canal_id: str, indice: int) -> None:
    """Olvida dónde estaba esa página, una vez quitado su mensaje del canal."""
    with conectar() as con:
        con.execute(
            "DELETE FROM publicaciones WHERE canal_id = ? AND indice = ?",
            (canal_id, indice),
        )


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
        quitar_cooldown_en(con, criatura_id, accion)


def quitar_cooldown_en(
    con: sqlite3.Connection, criatura_id: int, accion: str
) -> None:
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


@dataclass(frozen=True)
class ResultadoCaricia:
    ok: bool
    criatura: sim.Criatura | None
    espera: timedelta


def acariciar(
    usuario_id: str, guild_id: str, ahora: datetime, criatura_id: int | None = None
) -> ResultadoCaricia:
    """Acaricia a un gachamon, con su enfriamiento, en una sola transacción.

    Sin `criatura_id`, al activo; con él, a ese gachamon si es de esa persona,
    de ese servidor y está vivo. Si no hay a quién, no se escribe nada y el
    resultado va sin criatura.

    La criatura se avanza hasta `ahora` antes de nada. Antes de tiempo no se
    guarda nada: la criatura que se devuelve va avanzada hasta `ahora`, pero en
    la base sigue como estaba (el avance se recalcula igual la próxima vez).
    """
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        criatura = criatura_elegida_en(con, usuario_id, guild_id, criatura_id)
        if criatura is None:
            return ResultadoCaricia(False, None, timedelta(0))
        criatura = _avanzar_en(con, criatura, ahora)

        espera = espera_en(con, criatura.id, sim.ACARICIAR, ahora)
        if espera:
            return ResultadoCaricia(False, criatura, espera)

        acariciada = sim.aplicar_caricia(criatura).criatura
        _guardar(con, acariciada)
        duracion = sim.COOLDOWNS[sim.ACARICIAR]
        poner_cooldown_en(con, criatura.id, sim.ACARICIAR, ahora + duracion)
        return ResultadoCaricia(True, acariciada, duracion)


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

    Va aquí y no en quien llama porque el recorte tiene que valer igual venga de
    donde venga: una nota con saltos de línea rompería el listado del buzón, que pinta
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
    with conectar() as con:
        poner_efecto_en(con, criatura_id, stat, bonus, ahora)


def poner_efecto_en(
    con: sqlite3.Connection, criatura_id: int, stat: str, bonus: int,
    ahora: datetime,
) -> None:
    hasta = ahora + timedelta(minutes=obj.MINUTOS_DE_EFECTO)
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


# --- Las acciones que no se repiten ------------------------------------------
#
# Las dos reciben la conexión porque van dentro de la transacción de la compra:
# mirar, cobrar y anotar tienen que ser una sola cosa.

def accion_hecha_en(
    con: sqlite3.Connection, evento_id: str, usuario_id: str, guild_id: str,
    accion: str,
) -> tuple[str, dict] | None:
    """Lo que se pidió y lo que salió con ese evento, o `None` si es nuevo."""
    fila = con.execute(
        "SELECT solicitud, resultado FROM acciones_unicas "
        "WHERE evento_id = ? AND usuario_id = ? AND guild_id = ? AND accion = ?",
        (evento_id, usuario_id, guild_id, accion),
    ).fetchone()
    if fila is None:
        return None
    return fila["solicitud"], json.loads(fila["resultado"])


def anotar_accion_en(
    con: sqlite3.Connection, evento_id: str, usuario_id: str, guild_id: str,
    accion: str, solicitud: str, resultado: dict, ahora: datetime,
) -> None:
    """Apunta que ese evento ya se hizo y qué salió.

    Un `INSERT` a secas y no `OR IGNORE`: quien llama ya miró dentro de la misma
    transacción, así que un choque sería un error y debe deshacer la compra
    entera en vez de dejarla cobrada sin anotar.
    """
    con.execute(
        "INSERT INTO acciones_unicas (evento_id, usuario_id, guild_id, accion, "
        "solicitud, resultado, cuando) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (evento_id, usuario_id, guild_id, accion, solicitud,
         json.dumps(resultado), ahora.isoformat()),
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
    """Todo lo que tiene, lleve puesto lo que lleve.

    Es el cerrojo contra el doble cobro: `comprar_cosmetico` mira aquí para no
    volver a cobrar algo que ya es tuyo. Para saber qué se puede poner **ahora**
    está `_ropero_disponible`, que es otra pregunta.
    """
    filas = con.execute(
        "SELECT cosmetico FROM ropero WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    ).fetchall()
    return frozenset(f["cosmetico"] for f in filas)


def ropero_disponible(usuario_id: str, guild_id: str) -> frozenset[str]:
    with conectar() as con:
        return _ropero_disponible(con, usuario_id, guild_id)


def _ropero_disponible(
    con: sqlite3.Connection, usuario_id: str, guild_id: str
) -> frozenset[str]:
    """Lo que tiene **menos lo que ya llevan puesto sus gachamones vivos**.

    Se calcula en vez de guardarse: así la pieza de un gachamon que murió antes
    volvió sola al ropero, sin que nadie tuviera que acordarse de devolverla,
    porque un muerto deja de contar aquí.

    El muerto **conserva su columna**, así que en el cementerio se le sigue
    viendo vestido: vuelve la pieza, se queda el recuerdo.
    """
    puestos = {
        fila[tipo]
        for tipo in cos.TIPOS
        for fila in con.execute(
            f"SELECT {tipo} FROM criaturas WHERE usuario_id = ? "
            f"AND guild_id = ? AND muerta_en IS NULL AND {tipo} IS NOT NULL",
            (usuario_id, guild_id),
        )
    }
    return _ropero(con, usuario_id, guild_id) - puestos


def quien_lleva(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, clave: str,
    tipo: str,
) -> sim.Criatura | None:
    """El gachamon vivo que lleva esa pieza, o None si no la lleva ninguno.

    Para poder decir «lo lleva Kuro» en vez del genérico «no lo tienes», que
    ahora sería mentira: sí lo tiene, lo que pasa es que está puesto.
    """
    fila = con.execute(
        f"SELECT * FROM criaturas WHERE usuario_id = ? AND guild_id = ? "
        f"AND muerta_en IS NULL AND {tipo} = ?",
        (usuario_id, guild_id, clave),
    ).fetchone()
    return _a_criatura(fila) if fila else None


def quien_lleva_cada(usuario_id: str, guild_id: str) -> dict[str, str]:
    """Cada pieza puesta en un gachamon **vivo** de esa persona, y quién la lleva.

    Clave de la pieza → nombre de quien la lleva. Es lo que el
    ropero necesita para decir «la lleva Nube» sin una consulta por pieza.
    """
    llevan: dict[str, str] = {}
    with conectar() as con:
        filas = con.execute(
            "SELECT * FROM criaturas WHERE usuario_id = ? AND guild_id = ? "
            "AND muerta_en IS NULL",
            (usuario_id, guild_id),
        ).fetchall()
    for fila in filas:
        criatura = _a_criatura(fila)
        for tipo in cos.TIPOS:
            clave = getattr(criatura, tipo)
            if clave:
                llevan[clave] = criatura.nombre
    return llevan


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


# --- La mochila, dentro de una transacción ----------------------------------

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


# --- El paso del tiempo ------------------------------------------------------

def avanzar(criatura: sim.Criatura, ahora: datetime) -> sim.Criatura:
    """`sim.avanzar` con el ritmo que le toca por su departamento.

    Existe para que **no haya catorce sitios** teniendo que acordarse de mirar
    el departamento antes de hacer pasar el tiempo. Quien llame a `sim.avanzar`
    a secas se queda con el ritmo de siempre, que es el de quien tiene techo: el
    fallo por olvido es el comportamiento anterior y nunca uno peor.
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
    # El ritmo sale del departamento de su dueño, el mismo para todos sus
    # gachamones. Se lee sin escribir: hacer pasar el tiempo no lo estrena.
    depto = _departamento_leido(con, criatura.usuario_id, criatura.guild_id)
    return sim.avanzar(criatura, ahora, dep.ritmo_de(depto))


# --- El departamento -------------------------------------------------------
#
# Nace la primera vez que se mira. Mirarlo sin escribir da el de partida, que es
# justo el que nacería.

# La columna de cada eje. Va escrita aquí y no sale del argumento: es un nombre
# de columna dentro del SQL.
_LADOS = {dep.ANCHO: "ancho", dep.FONDO: "fondo"}


def departamento_de(
    usuario_id: str, guild_id: str, ahora: datetime
) -> dep.Departamento:
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        return _departamento_en(con, usuario_id, guild_id, ahora)


def _departamento_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, ahora: datetime
) -> dep.Departamento:
    """El departamento, **creándolo** como `dep.DE_PARTIDA` si es la primera
    vez que se mira: la fila, sus dos camas, una puesta y otra guardada, y su
    puerta, puesta.

    El `INSERT OR IGNORE` es lo que decide si nace: si dos peticiones llegan a
    la vez, sólo la que consigue la fila pone sus piezas.
    """
    nace = con.execute(
        "INSERT OR IGNORE INTO departamentos "
        "(usuario_id, guild_id, ancho, fondo, creado_en) VALUES (?, ?, ?, ?, ?)",
        (usuario_id, guild_id, dep.DE_PARTIDA.ancho, dep.DE_PARTIDA.fondo,
         ahora.isoformat()),
    ).rowcount
    if nace:
        for pieza in dep.DE_PARTIDA.piezas:
            anadir_mueble_en(
                con, usuario_id, guild_id, pieza.clave, pieza.x, pieza.y,
                pieza.giro,
            )
    return _departamento_leido(con, usuario_id, guild_id)


def departamento_leido(usuario_id: str, guild_id: str) -> dep.Departamento:
    """El departamento de alguien sin tocarle nada."""
    with conectar() as con:
        return _departamento_leido(con, usuario_id, guild_id)


def _departamento_leido(
    con: sqlite3.Connection, usuario_id: str, guild_id: str
) -> dep.Departamento:
    """El departamento **sin escribir nada**, con las piezas por orden de id.

    Sin fila todavía, el de partida. Así hacer pasar el tiempo o mirar una
    ficha no coge el cerrojo de escritura ni le estrena el departamento a nadie.
    """
    fila = con.execute(
        "SELECT ancho, fondo FROM departamentos "
        "WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    ).fetchone()
    if fila is None:
        return dep.DE_PARTIDA
    piezas = tuple(
        dep.Pieza(f["id"], f["mueble"], f["x"], f["y"], f["giro"])
        for f in con.execute(
            "SELECT id, mueble, x, y, giro FROM muebles "
            "WHERE usuario_id = ? AND guild_id = ? ORDER BY id",
            (usuario_id, guild_id),
        )
    )
    return dep.Departamento(fila["ancho"], fila["fondo"], piezas)


def anadir_mueble_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, clave: str,
    x: int | None = None, y: int | None = None, giro: int = 0,
) -> int:
    """Le da un mueble más, guardado si no se dice dónde, y devuelve su id."""
    cursor = con.execute(
        "INSERT INTO muebles (usuario_id, guild_id, mueble, x, y, giro) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (usuario_id, guild_id, clave, x, y, giro),
    )
    return int(cursor.lastrowid or 0)


def poner_mueble_en(
    con: sqlite3.Connection, mueble_id: int, x: int, y: int, giro: int
) -> None:
    """Lo pone en (x, y) con ese giro. Si cabe ahí lo decide quien llama."""
    con.execute(
        "UPDATE muebles SET x = ?, y = ?, giro = ? WHERE id = ?",
        (x, y, giro, mueble_id),
    )


def guardar_mueble_en(con: sqlite3.Connection, mueble_id: int) -> None:
    """Lo guarda: sin sitio y sin giro, como llega uno recién comprado."""
    con.execute(
        "UPDATE muebles SET x = NULL, y = NULL, giro = 0 WHERE id = ?",
        (mueble_id,),
    )


def ampliar_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, eje: str
) -> None:
    """Le suma una columna (`dep.ANCHO`) o una fila (`dep.FONDO`).

    Lo puesto no se mueve: la casilla nueva queda al final de ese eje. Pasar de
    8 lo impide el `CHECK` del esquema; cuándo se puede lo decide quien llama.
    """
    lado = _LADOS[eje]
    con.execute(
        f"UPDATE departamentos SET {lado} = {lado} + 1 "
        "WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    )


def asentar_el_plantel_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, ahora: datetime
) -> list[sim.Criatura]:
    """Pone al día **y guarda** hasta `ahora` a cada gachamon vivo de esa persona.

    Va antes de cambiar lo que fija su ritmo —poner o guardar un mueble,
    ampliar—, en la misma transacción: `sim.avanzar` aplica el ritmo a todo el
    tiempo sin guardar, y sin esto el ritmo nuevo valdría también hacia atrás.
    """
    asentados = [
        _avanzar_en(con, criatura, ahora)
        for criatura in plantel_en(con, usuario_id, guild_id)
    ]
    for criatura in asentados:
        _guardar(con, criatura)
    return asentados


# --- Las cartas --------------------------------------------------------------

def guardar_carta_en(
    con: sqlite3.Connection, usuario_id: str, guild_id: str, carta: str,
    contenido: dict, ahora: datetime,
) -> None:
    """Le deja esa carta, sin ver, dentro de la transacción de quien la escribe.

    Un `INSERT` a secas y no `OR IGNORE`: cada carta se escribe una vez, así que
    un choque sería un error y debe deshacer a quien la escribe entero.
    """
    con.execute(
        "INSERT INTO cartas (usuario_id, guild_id, carta, contenido, escrita_en) "
        "VALUES (?, ?, ?, ?, ?)",
        (usuario_id, guild_id, carta, json.dumps(contenido), ahora.isoformat()),
    )


def carta_sin_ver(usuario_id: str, guild_id: str, carta: str) -> dict | None:
    """Lo que cuenta esa carta si todavía no la ha visto; `None` si ya la vio o
    no tiene ninguna."""
    with conectar() as con:
        fila = con.execute(
            "SELECT contenido FROM cartas WHERE usuario_id = ? AND guild_id = ? "
            "AND carta = ? AND vista_en IS NULL",
            (usuario_id, guild_id, carta),
        ).fetchone()
    return None if fila is None else json.loads(fila["contenido"])


def marcar_carta_vista(
    usuario_id: str, guild_id: str, carta: str, ahora: datetime
) -> None:
    """Apunta que ya la vio. Repetirlo no cambia la primera vez; sin carta, nada."""
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "UPDATE cartas SET vista_en = ? WHERE usuario_id = ? AND guild_id = ? "
            "AND carta = ? AND vista_en IS NULL",
            (ahora.isoformat(), usuario_id, guild_id, carta),
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


# --- Cuentas web y vinculación ----------------------------------------------

@dataclass(frozen=True)
class CuentaWeb:
    rowino_uid: int
    usuario_id: str
    guild_id: str
    vinculada: bool


def _cuenta_de(fila: sqlite3.Row | None) -> CuentaWeb | None:
    if fila is None:
        return None
    return CuentaWeb(
        fila["rowino_uid"], fila["usuario_id"], fila["guild_id"],
        bool(fila["vinculada"]),
    )


def _cuenta_en(con: sqlite3.Connection, rowino_uid: int) -> CuentaWeb | None:
    return _cuenta_de(con.execute(
        "SELECT * FROM cuentas_web WHERE rowino_uid = ?", (rowino_uid,)
    ).fetchone())


def _tiene_gachamones(con: sqlite3.Connection, usuario_id: str, guild_id: str) -> bool:
    """Cualquier criatura de esa identidad en ese servidor, viva o muerta."""
    return con.execute(
        "SELECT 1 FROM criaturas WHERE usuario_id = ? AND guild_id = ? LIMIT 1",
        (usuario_id, guild_id),
    ).fetchone() is not None


def tiene_gachamones(usuario_id: str, guild_id: str) -> bool:
    """Si esa identidad tiene alguna criatura en ese servidor, viva o muerta."""
    with conectar() as con:
        return _tiene_gachamones(con, usuario_id, guild_id)


def cuenta_web(rowino_uid: int) -> CuentaWeb | None:
    with conectar() as con:
        return _cuenta_en(con, rowino_uid)


def lugar_de_cuenta(rowino_uid: int) -> str | None:
    """El último lugar al que llegó esa cuenta; None si no hay cuenta o lugar."""
    with conectar() as con:
        fila = con.execute(
            "SELECT lugar FROM cuentas_web WHERE rowino_uid = ?", (rowino_uid,)
        ).fetchone()
    return None if fila is None else fila["lugar"]


def poner_lugar(rowino_uid: int, lugar: str) -> None:
    """Guarda el lugar de esa cuenta. No valida contra el pueblo; sin cuenta, nada."""
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "UPDATE cuentas_web SET lugar = ? WHERE rowino_uid = ?", (lugar, rowino_uid)
        )


def crear_identidad_web(rowino_uid: int, guild_id: str, ahora: datetime) -> CuentaWeb:
    """La identidad de una cuenta de Rowino. Idempotente: si ya tiene fila, la
    devuelve tal cual."""
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        existente = _cuenta_en(con, rowino_uid)
        if existente is not None:
            return existente
        usuario_id = identidad.de_cuenta_web(rowino_uid)
        con.execute(
            "INSERT INTO cuentas_web (rowino_uid, usuario_id, guild_id, vinculada, "
            "creada_en) VALUES (?, ?, ?, 0, ?)",
            (rowino_uid, usuario_id, guild_id, ahora.isoformat()),
        )
        return CuentaWeb(rowino_uid, usuario_id, guild_id, False)


def guardar_avatar(
    usuario_id: str, guild_id: str, avatar: av.Avatar, ahora: datetime,
) -> None:
    """Crea o reemplaza el avatar de esa persona en ese servidor."""
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "INSERT OR REPLACE INTO avatares (usuario_id, guild_id, nombre, genero, "
            "piel, pelo, color_de_pelo, ropa, actualizado_en) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (usuario_id, guild_id, avatar.nombre, avatar.genero, avatar.piel,
             avatar.pelo, avatar.color_de_pelo, avatar.ropa, ahora.isoformat()),
        )


def avatar_de(usuario_id: str, guild_id: str) -> av.Avatar | None:
    with conectar() as con:
        fila = con.execute(
            "SELECT nombre, genero, piel, pelo, color_de_pelo, ropa FROM avatares "
            "WHERE usuario_id = ? AND guild_id = ?",
            (usuario_id, guild_id),
        ).fetchone()
    return None if fila is None else av.Avatar(*fila)


_REINTENTOS_DE_CODIGO = 10


def pedir_codigo_de_vinculo(
    rowino_uid: int, ahora: datetime, rng: random.Random | None = None
) -> str:
    """Un código nuevo para esa cuenta, que anula el que tuviera.

    Lanza `vinculo.NoSePuede` si la cuenta ya está vinculada o si su identidad
    web ya tiene gachamones: dos planteles no se funden.
    """
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        cuenta = _cuenta_en(con, rowino_uid)
        if cuenta is not None:
            if cuenta.vinculada:
                raise vinculo.NoSePuede(vinculo.YA_VINCULADA)
            if _tiene_gachamones(con, cuenta.usuario_id, cuenta.guild_id):
                raise vinculo.NoSePuede(vinculo.CON_GACHAMONES)
        con.execute(
            "DELETE FROM vinculos_pendientes WHERE vence_en <= ? OR rowino_uid = ?",
            (ahora.isoformat(), rowino_uid),
        )
        for _ in range(_REINTENTOS_DE_CODIGO):
            codigo = vinculo.nuevo_codigo(rng)
            if con.execute(
                "SELECT 1 FROM vinculos_pendientes WHERE codigo = ?", (codigo,)
            ).fetchone() is None:
                break
        else:
            raise RuntimeError("no se pudo generar un código de vinculación libre")
        vence = ahora + timedelta(minutes=vinculo.MINUTOS_DE_VIDA)
        con.execute(
            "INSERT INTO vinculos_pendientes (codigo, rowino_uid, vence_en) "
            "VALUES (?, ?, ?)",
            (codigo, rowino_uid, vence.isoformat()),
        )
        return codigo


def canjear_codigo_de_vinculo(
    codigo: str, usuario_id: str, guild_id: str, ahora: datetime
) -> str:
    """Canjea un código escrito en Discord. Devuelve un resultado de `vinculo`.

    El orden de los pasos es el contrato: el intento se anota **antes** de mirar
    el código, así que uno bueno no sirve para saltarse el límite, y todo lo que
    no sea «sirve» contesta lo mismo, así que la respuesta no revela si un
    código existe, caducó o era de una cuenta que ya no puede vincularse.
    """
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        # 1. El límite de intentos.
        con.execute(
            "DELETE FROM intentos_de_vinculo WHERE usuario_id = ? AND guild_id = ? "
            "AND en <= ?",
            (usuario_id, guild_id,
             (ahora - vinculo.VENTANA_DE_INTENTOS).isoformat()),
        )
        intentos = con.execute(
            "SELECT COUNT(*) n FROM intentos_de_vinculo "
            "WHERE usuario_id = ? AND guild_id = ?",
            (usuario_id, guild_id),
        ).fetchone()["n"]
        if intentos >= vinculo.INTENTOS_MAXIMOS:
            return vinculo.DEMASIADOS
        # 2. Este intento cuenta, salga como salga.
        con.execute(
            "INSERT INTO intentos_de_vinculo (usuario_id, guild_id, en) "
            "VALUES (?, ?, ?)",
            (usuario_id, guild_id, ahora.isoformat()),
        )
        # 3. Una persona de Discord, una cuenta de Rowino.
        if con.execute(
            "SELECT 1 FROM cuentas_web WHERE usuario_id = ? AND guild_id = ?",
            (usuario_id, guild_id),
        ).fetchone() is not None:
            return vinculo.YA_VINCULADA
        # 4. El código, vivo.
        pendiente = con.execute(
            "SELECT rowino_uid FROM vinculos_pendientes "
            "WHERE codigo = ? AND vence_en > ?",
            (vinculo.normalizar(codigo), ahora.isoformat()),
        ).fetchone()
        if pendiente is None:
            return vinculo.INVALIDO
        rowino_uid = pendiente["rowino_uid"]
        # 5. Su cuenta todavía tiene que poder vincularse.
        cuenta = _cuenta_en(con, rowino_uid)
        if cuenta is not None and (
            cuenta.vinculada
            or _tiene_gachamones(con, cuenta.usuario_id, cuenta.guild_id)
        ):
            con.execute(
                "DELETE FROM vinculos_pendientes WHERE rowino_uid = ?", (rowino_uid,)
            )
            return vinculo.INVALIDO
        # 6. Esa cuenta pasa a ser esta persona.
        if cuenta is None:
            con.execute(
                "INSERT INTO cuentas_web (rowino_uid, usuario_id, guild_id, "
                "vinculada, creada_en) VALUES (?, ?, ?, 1, ?)",
                (rowino_uid, usuario_id, guild_id, ahora.isoformat()),
            )
        else:
            con.execute(
                "UPDATE cuentas_web SET usuario_id = ?, guild_id = ?, vinculada = 1 "
                "WHERE rowino_uid = ?",
                (usuario_id, guild_id, rowino_uid),
            )
        con.execute(
            "DELETE FROM vinculos_pendientes WHERE rowino_uid = ?", (rowino_uid,)
        )
        return vinculo.OK
