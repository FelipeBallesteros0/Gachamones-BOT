"""Los rechazos de compra dicen por qué, con una clave, además de su frase."""
from datetime import datetime, timedelta, timezone

import pytest

import casas as cas
import cosmeticos as cos
import db
import economia
import objetos as obj

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
U, G = "u1", "g1"
PEQUENA = cas.CATALOGO["pequena"]
MEDIANA = cas.CATALOGO["mediana"]
GRANDE = cas.CATALOGO["grande"]
SOMBRERO = next(c for c in cos.CATALOGO.values() if c.tipo == cos.SOMBRERO)
FELPUDO = cas.MUEBLES["felpudo"]
CHIMENEA = cas.MUEBLES["chimenea"]


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "motivos.db")
    db.inicializar()


def dar(monedas=0, gemas=0, usuario=U):
    with db.conectar() as con:
        economia._asegurar_monedero(con, usuario, G)
        con.execute(
            "UPDATE monederos SET asciicoins = ?, asciigems = ? "
            "WHERE usuario_id = ? AND guild_id = ?",
            (monedas, gemas, usuario, G),
        )


def id_de_la_casa(usuario=U):
    return db.hogar_de(usuario, G, T0).casas[0].id


def con_casa(casa=PEQUENA, monedas=5000):
    dar(monedas=monedas)
    assert economia.comprar_casa(U, G, casa, T0).ok
    return id_de_la_casa()


def rechazo(resultado, motivo):
    assert resultado.ok is False
    assert resultado.motivo == motivo
    assert isinstance(resultado.problema, str) and resultado.problema


# --- Lo que no se vende ----------------------------------------------------

def test_lo_que_no_se_vende_no_se_compra(base):
    poroto = obj.CATALOGO["poroto_rojo"]
    assert not poroto.se_vende
    with pytest.raises(ValueError):
        economia.comprar("evento-0001", U, G, poroto, T0)
    assert db.inventario(U, G) == {}


def test_a_la_venta_es_el_catalogo_sin_lo_que_se_cosecha_o_se_cocina():
    claves = [o.clave for o in obj.a_la_venta()]
    assert claves == [c for c, o in obj.CATALOGO.items() if o.se_vende]
    assert len(claves) == 17 and "semilla" in claves and "poroto_rojo" not in claves


# --- Cosméticos ------------------------------------------------------------

def test_el_cosmetico_que_ya_tienes_dice_ya_lo_tienes(base):
    dar(gemas=500)
    assert economia.comprar_cosmetico(U, G, SOMBRERO).ok
    rechazo(economia.comprar_cosmetico(U, G, SOMBRERO), "ya_lo_tienes")


def test_el_cosmetico_sin_gemas_suficientes_dice_faltan_gemas(base):
    dar(gemas=0)
    rechazo(economia.comprar_cosmetico(U, G, SOMBRERO), "faltan_gemas")


# --- Casas -----------------------------------------------------------------

def test_mejorar_una_casa_ajena_dice_no_es_tuya(base):
    dar(monedas=5000)
    rechazo(
        economia.comprar_casa(U, G, MEDIANA, T0, mejorar=9999), "no_es_tuya"
    )


def test_mejorar_hacia_abajo_dice_no_se_empeora(base):
    suya = con_casa(GRANDE)
    rechazo(
        economia.comprar_casa(U, G, PEQUENA, T0, mejorar=suya), "no_se_empeora"
    )


def test_comprar_la_cuarta_casa_dice_maximo_de_casas(base):
    dar(monedas=20000)
    for _ in range(cas.MAXIMO_CASAS):
        assert economia.comprar_casa(U, G, PEQUENA, T0).ok
    rechazo(economia.comprar_casa(U, G, PEQUENA, T0), "maximo_de_casas")


def test_comprar_casa_sin_monedas_dice_faltan_monedas(base):
    dar(monedas=0)
    rechazo(economia.comprar_casa(U, G, PEQUENA, T0), "faltan_monedas")


def test_vender_sin_tener_casa_dice_sin_casa(base):
    dar()
    rechazo(economia.vender_casa(U, G, 1, T0), "sin_casa")


def test_vender_la_casa_de_otro_dice_no_es_tuya(base):
    con_casa()
    rechazo(economia.vender_casa(U, G, 9999, T0), "no_es_tuya")


# --- Muebles ---------------------------------------------------------------

def test_amueblar_desde_el_refugio_dice_sin_casa(base):
    dar(monedas=500)
    db.hogar_de(U, G, T0)
    for operacion in (
        economia.comprar_mueble, economia.colocar_mueble,
        economia.retirar_mueble,
    ):
        rechazo(operacion(U, G, FELPUDO, T0), "sin_casa")


def test_amueblar_a_la_intemperie_dice_intemperie(base):
    dar(monedas=500)
    db.hogar_de(U, G, T0)
    despues = T0 + timedelta(days=cas.DIAS_DE_REFUGIO + 5)
    for operacion in (
        economia.comprar_mueble, economia.colocar_mueble,
        economia.retirar_mueble,
    ):
        rechazo(operacion(U, G, FELPUDO, despues), "intemperie")


def test_amueblar_una_casa_ajena_dice_no_es_tuya(base):
    con_casa()
    for operacion in (
        economia.comprar_mueble, economia.colocar_mueble,
        economia.retirar_mueble,
    ):
        rechazo(operacion(U, G, FELPUDO, T0, casa_id=9999), "no_es_tuya")


def test_el_mueble_que_ya_tienes_dice_ya_lo_tienes(base):
    con_casa()
    assert economia.comprar_mueble(U, G, FELPUDO, T0).ok
    rechazo(economia.comprar_mueble(U, G, FELPUDO, T0), "ya_lo_tienes")


def test_un_mueble_sin_monedas_dice_faltan_monedas(base):
    con_casa(monedas=PEQUENA.precio)
    rechazo(economia.comprar_mueble(U, G, CHIMENEA, T0), "faltan_monedas")


# --- colocado --------------------------------------------------------------

def test_el_mueble_comprado_con_sitio_queda_colocado(base):
    con_casa()
    resultado = economia.comprar_mueble(U, G, FELPUDO, T0)
    assert resultado.ok and resultado.colocado is True


def test_el_mueble_comprado_con_la_casa_llena_queda_guardado(base):
    suya = con_casa()
    llenos = [m for m in cas.MUEBLES.values() if m != CHIMENEA]
    for mueble in llenos:
        if not cas.caben_mas(PEQUENA, db.hogar_de(U, G, T0).casas[0].puestos):
            break
        assert economia.comprar_mueble(U, G, mueble, T0, casa_id=suya).ok
    dar(monedas=5000)
    resultado = economia.comprar_mueble(U, G, CHIMENEA, T0, casa_id=suya)
    assert resultado.ok is True and resultado.colocado is False


def test_colocar_bien_es_colocado_y_retirar_bien_no(base):
    con_casa()
    economia.comprar_mueble(U, G, FELPUDO, T0)
    retirado = economia.retirar_mueble(U, G, FELPUDO, T0)
    assert retirado.ok and retirado.colocado is False
    puesto = economia.colocar_mueble(U, G, FELPUDO, T0)
    assert puesto.ok and puesto.colocado is True


# --- Lo que sale bien no lleva motivo ---------------------------------------

def test_todo_lo_que_sale_bien_lleva_motivo_none(base):
    dar(monedas=5000, gemas=500)
    resultados = [
        economia.comprar_cosmetico(U, G, SOMBRERO),
        economia.comprar_casa(U, G, PEQUENA, T0),
    ]
    resultados.append(economia.comprar_casa(
        U, G, MEDIANA, T0, mejorar=id_de_la_casa()
    ))
    resultados += [
        economia.comprar_mueble(U, G, FELPUDO, T0),
        economia.retirar_mueble(U, G, FELPUDO, T0),
        economia.colocar_mueble(U, G, FELPUDO, T0),
        economia.vender_casa(U, G, id_de_la_casa(), T0),
    ]
    assert all(r.ok for r in resultados)
    assert all(r.motivo is None for r in resultados)
