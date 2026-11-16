"""La migración de «una casa por persona» a varias, sobre filas de verdad.

Es la segunda del proyecto que mueve datos, y la que puede romper la partida que
hay ahora mismo en producción: allí hay una persona con una casa pequeña y
cuatro gachamones, o sea **por encima del aforo nuevo**. Que se le respeten los
cuatro es el caso que más se prueba aquí.

La base vieja se fabrica deshaciendo el esquema nuevo —`hogar` con su columna
`casa`, `huerto` sin `casa_id`— en vez de copiar la de producción, que no se
toca. Datos sintéticos, como manda la política.

Las casas ya no tienen reglas: las convierte el día del cambio. La migración se
queda porque una base vieja tiene que poder llegar hasta ese día, y por eso
estas pruebas miran las filas que deja y no lo que las casas hacían con ellas.
"""
from datetime import datetime, timedelta, timezone

import pytest

import db

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)

DDL_HOGAR_VIEJO = """
CREATE TABLE hogar (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    casa TEXT,
    refugio_hasta TEXT NOT NULL,
    publica INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (usuario_id, guild_id)
)
"""

DDL_HUERTO_VIEJO = """
CREATE TABLE huerto (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    bancal INTEGER NOT NULL,
    plantado_en TEXT NOT NULL,
    regado INTEGER NOT NULL DEFAULT 0,
    sembrado TEXT NOT NULL DEFAULT 'semilla',
    PRIMARY KEY (usuario_id, guild_id, bancal)
)
"""


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "migracion.db")
    db.inicializar()


def volver_al_esquema_viejo(con):
    """Deshace la migración: `hogar` con `casa` y `huerto` sin `casa_id`.

    Se reconstruye hacia atrás en vez de escribir el esquema antiguo entero
    porque así el resto de las tablas —criaturas, mobiliario, monederos— son las
    de verdad, y la migración se prueba contra lo que se va a encontrar.
    """
    con.execute("DROP TABLE hogar")
    con.execute(DDL_HOGAR_VIEJO)
    con.execute("DROP TABLE huerto")
    con.execute(DDL_HUERTO_VIEJO)
    con.execute("DELETE FROM casas_propias")
    con.execute("UPDATE criaturas SET casa_id = NULL")
    con.execute("UPDATE mobiliario SET casa_id = NULL")


def partida_vieja(casa="pequena", cuantos=4, con_huerto=(1,), muebles=("felpudo",)):
    """Una partida tal como estaría antes del cambio, y la deja migrada."""
    criaturas = [
        db.crear("u1", "g1", "pulpo", f"K{i}", STATS, T0, activa=(i == 0))
        for i in range(cuantos)
    ]
    with db.conectar() as con:
        volver_al_esquema_viejo(con)
        con.execute(
            "INSERT INTO hogar (usuario_id, guild_id, casa, refugio_hasta, publica) "
            "VALUES ('u1', 'g1', ?, ?, 0)",
            (casa, (T0 + timedelta(days=7)).isoformat()),
        )
        # Alguien sin casa, para comprobar que no se le inventa ninguna.
        con.execute(
            "INSERT INTO hogar (usuario_id, guild_id, casa, refugio_hasta) "
            "VALUES ('u2', 'g1', NULL, ?)",
            ((T0 + timedelta(days=3)).isoformat(),),
        )
        for bancal in con_huerto:
            con.execute(
                "INSERT INTO huerto "
                "(usuario_id, guild_id, bancal, plantado_en, regado, sembrado) "
                "VALUES ('u1', 'g1', ?, ?, 1, 'poroto_rojo')",
                (bancal, T0.isoformat()),
            )
        for mueble in muebles:
            con.execute(
                "INSERT INTO mobiliario (usuario_id, guild_id, mueble, colocado) "
                "VALUES ('u1', 'g1', ?, 1)",
                (mueble,),
            )
        con.commit()
        db._migrar_casas(con)
    return criaturas


def casas_de(usuario="u1"):
    with db.conectar() as con:
        return con.execute(
            "SELECT * FROM casas_propias WHERE usuario_id = ? AND guild_id = 'g1'",
            (usuario,),
        ).fetchall()


def test_la_casa_que_habia_pasa_a_ser_una_fila_propia():
    partida_vieja(casa="pequena")

    filas = casas_de()

    assert len(filas) == 1
    assert filas[0]["casa"] == "pequena"
    assert not casas_de("u2"), "a quien no tenía casa no se le inventa ninguna"


def test_nadie_pierde_su_sitio_aunque_se_pase_del_aforo():
    """El caso que existe en producción: una pequeña —aforo 3— con cuatro
    gachamones. El aforo frena las mudanzas nuevas, no desaloja a quien ya
    estaba, así que los cuatro se quedan dentro."""
    partida_vieja(casa="pequena", cuantos=4)
    casa_id = casas_de()[0]["id"]

    with db.conectar() as con:
        dentro = con.execute(
            "SELECT COUNT(*) AS n FROM criaturas WHERE casa_id = ? "
            "AND muerta_en IS NULL",
            (casa_id,),
        ).fetchone()["n"]

    assert dentro == 4, "la pequeña tenía aforo 3: si no, este test no prueba nada"


def test_lo_plantado_sigue_creciendo_en_la_casa_que_era():
    partida_vieja(con_huerto=(1,))
    casa_id = casas_de()[0]["id"]

    with db.conectar() as con:
        filas = con.execute("SELECT * FROM huerto").fetchall()

    assert len(filas) == 1
    assert filas[0]["casa_id"] == casa_id
    # Y sin perder lo que ya llevaba: regado y con un poroto rojo sembrado.
    assert filas[0]["regado"] == 1
    assert filas[0]["sembrado"] == "poroto_rojo"


def test_los_muebles_colgados_se_quedan_en_esa_casa():
    partida_vieja(muebles=("felpudo", "maceta"))
    casa_id = casas_de()[0]["id"]

    with db.conectar() as con:
        filas = con.execute(
            "SELECT mueble, casa_id, colocado FROM mobiliario"
        ).fetchall()

    assert {f["mueble"] for f in filas} == {"felpudo", "maceta"}
    assert all(f["casa_id"] == casa_id and f["colocado"] for f in filas)


def test_el_reloj_del_refugio_sobrevive_intacto():
    """Es de la persona y no de la casa, así que la migración no puede tocarlo:
    quien tenía tres días de estancia sigue teniendo tres."""
    partida_vieja()

    with db.conectar() as con:
        filas = {
            f["usuario_id"]: f
            for f in con.execute("SELECT * FROM hogar").fetchall()
        }

    assert set(filas) == {"u1", "u2"}
    assert filas["u1"]["refugio_hasta"] == (T0 + timedelta(days=7)).isoformat()
    assert filas["u2"]["refugio_hasta"] == (T0 + timedelta(days=3)).isoformat()
    assert not filas["u1"]["publica"], "y si tenía la casa cerrada, sigue cerrada"
    assert "casa" not in filas["u1"].keys(), "la columna vieja ya no está"


def test_correrla_dos_veces_no_duplica_nada():
    """`inicializar()` corre en cada arranque: si no fuera idempotente, cada
    reinicio le regalaría una casa a todo el mundo."""
    partida_vieja()

    with db.conectar() as con:
        db._migrar_casas(con)
        db._migrar_casas(con)

    assert len(casas_de()) == 1


def test_una_base_nueva_no_necesita_migracion():
    """Sin partida vieja no hay nada que mover, y la migración lo detecta por la
    columna que ya no está en vez de por una bandera aparte."""
    with db.conectar() as con:
        db._migrar_casas(con)

    assert not casas_de()
