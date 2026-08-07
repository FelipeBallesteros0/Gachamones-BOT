"""La migración de «una casa por persona» a varias, sobre filas de verdad.

Es la segunda del proyecto que mueve datos, y la que puede romper la partida que
hay ahora mismo en producción: allí hay una persona con una casa pequeña y
cuatro gachamones, o sea **por encima del aforo nuevo**. Que se le respeten los
cuatro es el caso que más se prueba aquí.

La base vieja se fabrica deshaciendo el esquema nuevo —`hogar` con su columna
`casa`, `huerto` sin `casa_id`— en vez de copiar la de producción, que no se
toca. Datos sintéticos, como manda la política.
"""
from datetime import datetime, timedelta, timezone

import pytest

import casas as cas
import db
import economia
import huerto as hue

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

    assert dentro == 4
    assert cas.CATALOGO["pequena"].aforo == 3, "si no, este test no prueba nada"


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


def test_los_bancales_del_huerto_salen_de_la_suma_de_las_casas():
    """Lo que cambia el equilibrio: con varias casas, los bancales se suman."""
    assert hue.BANCALES == {"pequena": 1, "mediana": 3, "grande": 7}
    assert cas.MAXIMO_CASAS == 3


@pytest.mark.parametrize("baratas, cara", [
    (("pequena", "pequena"), "mediana"),
    (("mediana", "mediana"), "grande"),
])
def test_apilar_casas_baratas_nunca_gana_a_mejorar(baratas, cara):
    """El motivo de que los bancales pasaran de 1/2/3 a 1/3/7: con los viejos,
    dos pequeñas costaban 400 y daban los mismos 2 bancales que la mediana de
    500, y no había precio que lo arreglara porque igualaban también su aforo.
    """
    precio_apilado = sum(cas.CATALOGO[c].precio for c in baratas)
    bancales_apilado = sum(hue.BANCALES[c] for c in baratas)

    assert precio_apilado < cas.CATALOGO[cara].precio, "si no, no hay dilema"
    assert bancales_apilado < hue.BANCALES[cara]


def test_el_huerto_de_tres_casas_cabe_en_un_desplegable():
    """El menú del huerto lleva una fila por bancal y Discord admite 25. Es lo
    que fija el tope de tres casas, y por eso se comprueba aquí."""
    maximo = cas.MAXIMO_CASAS * max(hue.BANCALES.values())

    assert maximo <= 25, maximo
    assert (cas.MAXIMO_CASAS + 1) * max(hue.BANCALES.values()) > 25, (
        "con una casa más ya no cabría, que es de donde sale el tope"
    )


# --- El aforo y el reparto --------------------------------------------------

def con_casa(clave="pequena", usuario="u1"):
    with db.conectar() as con:
        economia._asegurar_monedero(con, usuario, "g1")
        con.execute(
            "UPDATE monederos SET asciicoins = 9000 WHERE usuario_id = ? "
            "AND guild_id = 'g1'", (usuario,),
        )
        con.commit()
    return economia.comprar_casa(usuario, "g1", cas.CATALOGO[clave], T0).casa_id


def test_un_gachamon_nace_en_la_primera_casa_con_sitio():
    """Si naciera siempre en el refugio habría que colocar a mano a cada recién
    llegado, y el reparto es para decidir, no para hacer trabajo obligatorio."""
    casa = con_casa("pequena")

    nacidos = [
        db.crear("u1", "g1", "pulpo", f"K{i}", STATS, T0, activa=(i == 0))
        for i in range(4)
    ]

    dentro = db.inquilinos_de("u1", "g1")
    assert dentro[casa] == cas.CATALOGO["pequena"].aforo == 3
    assert dentro[None] == 1, "el cuarto no cabe y se queda en el refugio"
    assert nacidos[3].casa_id is None


def test_comprar_una_casa_acoge_a_los_que_estaban_en_el_refugio():
    for i in range(4):
        db.crear("u1", "g1", "pulpo", f"K{i}", STATS, T0, activa=(i == 0))
    assert db.inquilinos_de("u1", "g1") == {None: 4}

    casa = con_casa("mediana")

    dentro = db.inquilinos_de("u1", "g1")
    assert dentro[casa] == 4 and None not in dentro


def test_no_cabe_uno_mas_del_aforo():
    casa = con_casa("pequena")
    for i in range(4):
        db.crear("u1", "g1", "pulpo", f"K{i}", STATS, T0, activa=(i == 0))
    fuera = [c for c in db.plantel("u1", "g1") if c.casa_id is None][0]

    resultado = economia.mudar_gachamon("u1", "g1", fuera.id, casa, T0)

    assert not resultado.ok and "3/3" in resultado.problema
    assert db.inquilinos_de("u1", "g1")[casa] == 3


def test_mudar_al_refugio_hace_sitio_para_otro():
    """El refugio siempre acepta: es lo que permite vaciar una casa antes de
    venderla, y sin él quien llene las tres no podría mover a nadie."""
    casa = con_casa("pequena")
    for i in range(4):
        db.crear("u1", "g1", "pulpo", f"K{i}", STATS, T0, activa=(i == 0))
    dentro = [c for c in db.plantel("u1", "g1") if c.casa_id == casa][0]
    fuera = [c for c in db.plantel("u1", "g1") if c.casa_id is None][0]

    assert economia.mudar_gachamon("u1", "g1", dentro.id, None, T0).ok
    assert economia.mudar_gachamon("u1", "g1", fuera.id, casa, T0).ok

    reparto = db.inquilinos_de("u1", "g1")
    assert reparto[casa] == 3 and reparto[None] == 1


def test_quien_ya_se_pasaba_del_aforo_no_es_desalojado():
    """Lo que dejó la migración: el aforo frena que **entre** uno más, no echa
    a quien ya estaba. Así esas casas se vacían solas y nunca vuelven a
    llenarse por encima del tope."""
    partida_vieja(casa="pequena", cuantos=4)
    casa = casas_de()[0]["id"]
    assert db.inquilinos_de("u1", "g1")[casa] == 4

    dentro = db.plantel("u1", "g1")[0]
    assert economia.mudar_gachamon("u1", "g1", dentro.id, None, T0).ok
    assert db.inquilinos_de("u1", "g1")[casa] == 3

    # Y ya no puede volver: al bajar a tres la casa está llena de verdad. Es lo
    # que hace que el exceso se vaya para no volver en vez de quedarse fijo.
    vuelta = economia.mudar_gachamon("u1", "g1", dentro.id, casa, T0)
    assert not vuelta.ok and "3/3" in vuelta.problema


def test_cada_gachamon_vive_su_propia_comodidad():
    """Lo que hace que repartir importe: dos de la misma persona pueden estar
    en sitios distintos, y a quien no cabe le pasa el tiempo como en el
    refugio aunque su dueño tenga una casa grande."""
    casa = con_casa("grande")
    hogar = db.hogar_de("u1", "g1", T0)

    dentro = cas.ritmo_de(hogar, T0, casa)
    fuera = cas.ritmo_de(hogar, T0, None)

    assert dentro.animo < fuera.animo, "en casa el ánimo baja más despacio"
    assert hogar.comodidad_de(casa, T0) > hogar.comodidad_de(None, T0)


def test_vender_una_casa_desaloja_solo_la_suya():
    """Sus inquilinos al refugio, sus muebles al armario y sus bancales fuera;
    las otras casas, intactas."""
    primera = con_casa("pequena")
    segunda = con_casa("mediana")
    for i in range(5):
        db.crear("u1", "g1", "pulpo", f"K{i}", STATS, T0, activa=(i == 0))
    antes = db.inquilinos_de("u1", "g1")
    assert antes[primera] == 3 and antes[segunda] == 2

    resultado = economia.vender_casa("u1", "g1", primera, T0)

    assert resultado.ok and resultado.desalojados == 3
    despues = db.inquilinos_de("u1", "g1")
    assert primera not in despues
    assert despues[segunda] == 2, "la otra casa no se toca"
    assert despues[None] == 3


def test_vender_una_casa_no_arranca_lo_plantado_en_las_otras():
    """Los bancales se borran por casa. Por persona, vender la pequeña dejaría
    en barbecho el huerto entero de la grande sin que nadie lo pidiera."""
    primera = con_casa("pequena")
    segunda = con_casa("grande")
    ahora = T0
    with db.conectar() as con:
        for casa, bancal in ((primera, 1), (segunda, 1), (segunda, 2)):
            db.plantar_en(con, "u1", "g1", casa, bancal, ahora)
        con.commit()

    economia.vender_casa("u1", "g1", primera, ahora)

    with db.conectar() as con:
        quedan = con.execute("SELECT casa_id, bancal FROM huerto").fetchall()
    assert {(f["casa_id"], f["bancal"]) for f in quedan} == {
        (segunda, 1), (segunda, 2)
    }


def test_al_avanzar_el_tiempo_manda_la_casa_del_gachamon():
    """La tubería entera, no sólo `ritmo_de`: **la misma criatura** pierde menos
    ánimo en un día viviendo en la casa grande que en el refugio.

    Se compara consigo misma y no con otra porque sólo hay una activa por
    persona, y las reservas no decaen: medir contra una reserva compararía el
    paso del tiempo con el hecho de estar congelada.
    """
    casa = con_casa("grande")
    bicho = db.crear("u1", "g1", "pulpo", "Kuro", STATS, T0)
    assert bicho.casa_id == casa, "nace dentro, que es lo que hace `crear`"

    un_dia = T0 + timedelta(days=1)
    en_casa = db.avanzar(bicho, un_dia).animo

    economia.mudar_gachamon("u1", "g1", bicho.id, None, T0)
    with db.conectar() as con:
        al_refugio = db.criatura_en(con, bicho.id)
    en_refugio = db.avanzar(al_refugio, un_dia).animo

    assert en_casa > en_refugio, (
        "la comodidad de su casa tiene que frenarle el ánimo"
    )
