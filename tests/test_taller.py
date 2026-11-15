"""El ropero: comprar al armario, ponérselo y quitárselo sin perder nada."""
from datetime import datetime, timezone

import pytest

import cosmeticos as cos
import db
import economia
import logros

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)
CORONA = cos.CATALOGO["corona"]
CHISTERA = cos.CATALOGO["chistera"]
INVICTO = cos.CATALOGO["titulo_invicto"]


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "ropero.db")
    db.inicializar()


def nacer(usuario="u1", nombre="Mia", activa=True):
    return db.crear(usuario, "g1", "pulpo", nombre, STATS, T0, activa=activa)


def con_gemas(cuantas, usuario="u1"):
    """Deja el monedero en esa cifra exacta, sin pasar por los logros."""
    with db.conectar() as con:
        economia._asegurar_monedero(con, usuario, "g1")
        con.execute(
            "UPDATE monederos SET asciigems = ? WHERE usuario_id = ? AND guild_id = 'g1'",
            (cuantas, usuario),
        )


def gemas(usuario="u1"):
    return economia.saldos(usuario, "g1").asciigems


def comprar(cosmetico=CORONA, usuario="u1"):
    return economia.comprar_cosmetico(usuario, "g1", cosmetico)


def poner(cosmetico=CORONA, usuario="u1"):
    return economia.equipar_cosmetico(usuario, "g1", cosmetico)


def quitar(tipo=cos.SOMBRERO, usuario="u1"):
    return economia.quitar_cosmetico(usuario, "g1", tipo)


def activa(usuario="u1"):
    return db.criatura_activa(usuario, "g1")


# --- Comprar ---------------------------------------------------------------

def test_comprar_cobra_lo_mete_en_el_ropero_y_se_lo_pone():
    """Que además se lo ponga es a propósito: es lo que espera quien acaba de
    gastarse sesenta gemas en una corona."""
    nacer()
    con_gemas(100)

    resultado = comprar()

    assert resultado.ok
    assert resultado.criatura.sombrero == "corona"
    assert db.ropero("u1", "g1") == {"corona"}
    assert gemas() == 100 - CORONA.precio
    assert resultado.saldo == gemas()
    # Y queda guardado, no sólo en el objeto devuelto.
    assert activa().sombrero == "corona"


def test_sin_gemas_suficientes_no_se_cobra_ni_entra_en_el_ropero():
    nacer()
    con_gemas(CORONA.precio - 1)

    resultado = comprar()

    assert not resultado.ok
    assert "faltan 1 gema." in resultado.problema
    assert gemas() == CORONA.precio - 1
    assert db.ropero("u1", "g1") == frozenset()
    assert activa().sombrero is None


def test_el_saldo_nunca_se_queda_en_negativo():
    """La condición viaja dentro del UPDATE justamente para esto."""
    nacer()
    con_gemas(0)

    for _ in range(3):
        assert not comprar().ok
    assert gemas() == 0


def test_comprar_lo_que_ya_tienes_no_cuesta_nada():
    """El doble clic: dos compras del mismo sombrero cobrarían 120 gemas y
    dejarían una corona. Y sigue valiendo aunque se lo hayas quitado, que es
    justo cuando el catálogo lo vuelve a ofrecer."""
    nacer()
    con_gemas(200)
    comprar()
    quitar()
    saldo = gemas()

    repetida = comprar()

    assert not repetida.ok
    assert "Ya tienes" in repetida.problema
    assert gemas() == saldo
    assert db.ropero("u1", "g1") == {"corona"}


def test_sin_gachamon_activo_se_compra_igual_y_va_al_ropero():
    """Antes hacía falta uno activo porque comprar era ponérselo. Ahora el
    ropero es tuyo, así que puedes comprar y equipar cuando tengas a quién."""
    con_gemas(200)
    resultado = comprar()

    assert resultado.ok
    assert resultado.criatura is None
    assert db.ropero("u1", "g1") == {"corona"}
    assert gemas() == 200 - CORONA.precio


def test_un_cosmetico_que_no_es_del_catalogo_no_se_cuela():
    nacer()
    con_gemas(200)
    falso = cos.Cosmetico("corona", cos.SOMBRERO, "Corona de mentira", "xx")

    with pytest.raises(ValueError):
        economia.comprar_cosmetico("u1", "g1", falso)
    with pytest.raises(ValueError):
        economia.equipar_cosmetico("u1", "g1", falso)
    with pytest.raises(ValueError):
        economia.quitar_cosmetico("u1", "g1", "peluca")
    assert gemas() == 200


# --- Poner y quitar --------------------------------------------------------

def test_desequipar_no_pierde_el_cosmetico():
    """Lo pedido: te lo quitas, sigue siendo tuyo y te lo puedes volver a poner
    sin pagar otra vez."""
    nacer()
    con_gemas(200)
    comprar(CORONA)
    saldo = gemas()

    quitada = quitar(cos.SOMBRERO)

    assert quitada.ok
    assert quitada.sustituido == CORONA
    assert activa().sombrero is None
    assert db.ropero("u1", "g1") == {"corona"}

    devuelta = poner(CORONA)

    assert devuelta.ok
    assert activa().sombrero == "corona"
    assert gemas() == saldo          # ponérsela otra vez es gratis


def test_otro_del_mismo_tipo_no_destruye_al_anterior():
    """Lo que cambia respecto de antes: la corona que se quita para dejar sitio
    a la chistera sigue en el ropero."""
    nacer()
    con_gemas(200)
    comprar(CORONA)

    resultado = comprar(CHISTERA)

    assert resultado.ok
    assert resultado.sustituido == CORONA
    assert activa().sombrero == "chistera"
    assert db.ropero("u1", "g1") == {"corona", "chistera"}
    assert poner(CORONA).ok
    assert activa().sombrero == "corona"


def test_la_corona_se_puede_pasar_de_un_gachamon_a_otro():
    """El sentido de que el ropero sea tuyo: antes hacían falta dos coronas."""
    primero = nacer(nombre="Primero")
    segundo = db.crear("u1", "g1", "michi", "Segundo", STATS, T0, activa=False)
    con_gemas(200)
    comprar(CORONA)
    quitar(cos.SOMBRERO)

    db.activar(segundo.id, "u1", "g1")
    assert poner(CORONA).ok

    assert db.por_id(segundo.id).sombrero == "corona"
    assert db.por_id(primero.id).sombrero is None
    assert gemas() == 200 - CORONA.precio   # una sola corona pagada


def test_no_se_puede_poner_lo_que_no_tienes():
    """El menú de personalizar caduca en dos minutos, pero se comprueba dentro
    de la transacción: no puede vestirse con lo que no ha comprado."""
    nacer()
    con_gemas(0)

    resultado = poner(CORONA)

    assert not resultado.ok
    assert "No tienes" in resultado.problema
    assert activa().sombrero is None


def test_quitar_lo_que_no_lleva_no_hace_nada():
    nacer()
    resultado = quitar(cos.SOMBRERO)

    assert not resultado.ok
    assert "no lleva nada" in resultado.problema


def test_poner_lo_que_ya_lleva_lo_dice_y_no_lo_repite():
    nacer()
    con_gemas(200)
    comprar(CORONA)

    resultado = poner(CORONA)

    assert not resultado.ok
    assert "ya lo lleva puesto" in resultado.problema


def test_los_de_tipos_distintos_conviven():
    nacer()
    con_gemas(300)
    comprar(CORONA)
    resultado = comprar(INVICTO)

    assert resultado.sustituido is None
    puesta = activa()
    assert (puesta.sombrero, puesta.titulo) == ("corona", "titulo_invicto")


def test_el_ropero_sobrevive_a_la_muerte_de_todo_el_plantel():
    """Es tuyo, no suyo: se te mueren todos y sigues teniendo la corona."""
    nacer()
    con_gemas(200)
    comprar(CORONA)

    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET muerta_en = ?, causa_muerte = 'hambre'",
            (T0.isoformat(),),
        )

    assert db.ropero("u1", "g1") == {"corona"}


def test_el_ropero_es_de_cada_persona_y_de_cada_servidor():
    nacer()
    nacer(usuario="u2", nombre="Ajeno")
    con_gemas(200)
    comprar(CORONA)

    assert db.ropero("u1", "g1") == {"corona"}
    assert db.ropero("u2", "g1") == frozenset()
    assert db.ropero("u1", "g2") == frozenset()


def test_lo_puesto_sobrevive_a_guardar_y_recargar():
    """Las columnas tienen que ir en `CAMPOS`, o se perderían en el
    primer cuidado."""
    bicho = nacer()
    con_gemas(300)
    comprar(CORONA)
    comprar(INVICTO)

    db.guardar(db.por_id(bicho.id))

    otra_vez = db.por_id(bicho.id)
    assert (otra_vez.sombrero, otra_vez.titulo) == ("corona", "titulo_invicto")


# --- La mudanza de lo que ya estaba puesto ---------------------------------

def test_lo_puesto_se_muda_al_ropero_de_su_dueño():
    """Antes de esto, comprar era ponérselo y no había ropero. Lo que cada
    gachamon llevara encima pasa a ser de su dueño y **se queda puesto**."""
    bicho = nacer()
    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET sombrero = 'corona', titulo = 'titulo_invicto' "
            "WHERE id = ?", (bicho.id,),
        )
        con.execute("DELETE FROM ropero")

    db.inicializar()

    assert db.ropero("u1", "g1") == {"corona", "titulo_invicto"}
    puesto = db.por_id(bicho.id)
    assert (puesto.sombrero, puesto.titulo) == ("corona", "titulo_invicto")


def test_la_mudanza_dos_veces_deja_lo_mismo():
    """Corre en cada arranque; a partir de la segunda tiene que ser inocua."""
    bicho = nacer()
    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET sombrero = 'corona' WHERE id = ?", (bicho.id,)
        )
        con.execute("DELETE FROM ropero")

    db.inicializar()
    primera = db.ropero("u1", "g1")
    db.inicializar()
    db.inicializar()

    assert db.ropero("u1", "g1") == primera == {"corona"}


# --- Con los logros, de punta a punta ---------------------------------------

def test_las_gemas_de_los_logros_pagan_un_cosmetico():
    """El círculo entero: ganar medallas, cobrarlas y gastárselas."""
    bicho = nacer()
    db.apuntar(bicho.id, logros.CARRERAS, 100)
    recibo = economia.pagar_logros(bicho, T0)
    assert recibo.asciigems >= CORONA.precio

    resultado = comprar(CORONA)

    assert resultado.ok
    assert resultado.saldo == recibo.saldo - CORONA.precio


# --- Una pieza, un gachamon ------------------------------------------------
#
# El fallo que motivó esto: comprar un sombrero y ponérselo NO lo sacaba del
# ropero, así que se le podía poner también al siguiente. Una Corona de 60 gemas
# acababa puesta en tres gachamones a la vez.

def test_lo_puesto_no_se_le_puede_poner_a_otro():
    """**El fallo del informe.** Es el test que lo encarna."""
    primero = nacer(nombre="Uno")
    segundo = nacer(nombre="Dos", activa=False)
    con_gemas(200)
    comprar(CORONA)                       # se la pone a Uno al comprarla

    db.activar(segundo.id, "u1", "g1")
    resultado = poner(CORONA)

    assert not resultado.ok
    assert "Uno" in resultado.problema, "y se dice quién la lleva, no «no la tienes»"
    assert db.criatura_activa("u1", "g1").sombrero is None
    assert primero.id != segundo.id


@pytest.mark.parametrize("cosmetico", [
    next(c for c in cos.CATALOGO.values() if c.tipo == tipo) for tipo in cos.TIPOS
])
def test_pasa_con_los_dos_tipos_no_solo_con_el_sombrero(cosmetico):
    """`_vestir_en` es genérica, así que el fallo lo tenían los dos tipos."""
    nacer(nombre="Uno")
    otro = nacer(nombre="Dos", activa=False)
    con_gemas(500)
    comprar(cosmetico)

    db.activar(otro.id, "u1", "g1")

    assert cosmetico.clave not in db.ropero_disponible("u1", "g1")
    assert not economia.equipar_cosmetico("u1", "g1", cosmetico).ok


def test_quitarsela_la_deja_libre_otra_vez():
    """No se pierde: sale del ropero mientras la lleva puesta y vuelve al
    quitársela. Es lo que ya prometía el recibo."""
    nacer(nombre="Uno")
    otro = nacer(nombre="Dos", activa=False)
    con_gemas(200)
    comprar(CORONA)
    assert CORONA.clave not in db.ropero_disponible("u1", "g1")

    economia.quitar_cosmetico("u1", "g1", CORONA.tipo)

    assert CORONA.clave in db.ropero_disponible("u1", "g1")
    db.activar(otro.id, "u1", "g1")
    assert poner(CORONA).ok, "y ahora sí se le puede poner al otro"


def test_al_morir_la_pieza_vuelve_al_ropero_y_el_muerto_sigue_vestido():
    """Se calcula en vez de guardarse, y por eso morirse la devuelve solo: si
    hubiera que devolverla a mano, la muerte se consuma en media docena de
    sitios y olvidar uno perdería sesenta gemas sin dejar rastro."""
    muerto = nacer(nombre="Uno")
    con_gemas(200)
    comprar(CORONA)
    assert CORONA.clave not in db.ropero_disponible("u1", "g1")

    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET muerta_en = ?, causa_muerte = 'hambre' "
            "WHERE id = ?", (T0.isoformat(), muerto.id),
        )
        con.commit()

    assert CORONA.clave in db.ropero_disponible("u1", "g1")
    with db.conectar() as con:
        fila = con.execute(
            "SELECT sombrero FROM criaturas WHERE id = ?", (muerto.id,)
        ).fetchone()
    assert fila["sombrero"] == CORONA.clave, (
        "el muerto se sigue viendo vestido en el cementerio"
    )


def test_comprar_dos_veces_sigue_sin_cobrar_dos_veces_aunque_la_lleve_puesta():
    """El caso que este cambio puede romper sin que se note: el cerrojo del
    doble cobro mira **lo que tienes**, no lo que está libre. Con lo libre,
    comprar otra corona llevando puesta la primera volvería a cobrar 60 gemas.
    """
    nacer()
    con_gemas(200)
    comprar(CORONA)
    saldo = gemas()

    repetida = comprar(CORONA)

    assert not repetida.ok
    assert gemas() == saldo, "no se cobra de nuevo lo que ya es tuyo"
