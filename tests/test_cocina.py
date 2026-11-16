"""Los porotos, la cocina y las sopaipillas.

El huerto por casa se fue, pero lo que se cosechó se queda: con tres porotos de
un color se cocina una sopaipilla, y comérsela da un bonus que depende del
carácter. Vienen de las pruebas de las casas, que se fueron con ellas.
"""
import random
from dataclasses import replace
from datetime import datetime, timezone

import pytest

import db
import economia
import huerto as hue
import objetos as objs
import personalidad as per
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)
_usos = 0


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "cocina.db")
    db.inicializar()


def nacer(nombre="Kuro", especie="pulpo"):
    return db.crear("u1", "g1", especie, nombre, STATS, T0)


def dar(objeto, cuantos=1):
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(con, "u1", "g1", objeto.clave, cuantos)


def usar(objeto, ahora=T0, rng=None):
    """Usar una unidad de la mochila, con un evento nuevo cada vez."""
    global _usos
    _usos += 1
    return economia.usar_objeto(f"uso-{_usos}", "u1", "g1", objeto, ahora, rng)


class DadosDelHuerto:
    """Un RNG de mentira que sólo dice si sale arcoíris.

    Con `random.Random` haría falta buscar una semilla que diera cada caso, y
    eso ata el test a la implementación del generador.
    """

    def __init__(self, arcoiris: bool):
        self.arcoiris = arcoiris

    def random(self) -> float:
        # `tirar_arcoiris` compara con `<`, así que 0.0 siempre sale y 1.0 nunca.
        return 0.0 if self.arcoiris else 1.0


# --- La tabla de gustos ---

def test_cada_caracter_ordena_los_cinco_colores():
    """Es lo que hace que el color importe: sin una lista completa por carácter,
    `caras_de` reventaría con el que faltara."""
    assert set(hue.AFINIDAD) == set(per.CARACTERES)
    for caracter, orden in hue.AFINIDAD.items():
        assert set(orden) == set(hue.COLORES), caracter
        assert len(orden) == len(set(orden)) == len(hue.COLORES), caracter


def test_los_cinco_dados_se_reparten_uno_por_puesto():
    assert len(hue.CARAS_POR_PUESTO) == len(hue.COLORES)
    assert list(hue.CARAS_POR_PUESTO) == sorted(hue.CARAS_POR_PUESTO, reverse=True)

    for caracter, orden in hue.AFINIDAD.items():
        caras = [hue.caras_de(caracter, color) for color in orden]
        assert caras == list(hue.CARAS_POR_PUESTO), caracter


def test_el_favorito_es_el_dado_mayor_y_el_peor_el_menor():
    for caracter, orden in hue.AFINIDAD.items():
        assert hue.caras_de(caracter, orden[0]) == 12, caracter
        assert hue.caras_de(caracter, orden[-1]) == 4, caracter
        assert "favorito" in hue.le_gusta(caracter, orden[0])
        assert "detesta" in hue.le_gusta(caracter, orden[-1])


def test_a_dos_caracteres_no_les_gusta_lo_mismo_en_el_mismo_orden():
    """Si dos coincidieran, el carácter daría igual para media tabla."""
    ordenes = [tuple(o) for o in hue.AFINIDAD.values()]
    assert len(set(ordenes)) == len(ordenes)


# --- Lo que da una cosecha, y el arcoíris ---

def test_la_cosecha_da_de_dos_a_cuatro():
    """Los números van clavados y no leídos de la constante.

    Deducirlos de `POROTOS_POR_COSECHA` haría el test circular: cambiar la
    constante movería a la vez lo que se comprueba, y nadie se enteraría de que
    el huerto pasó a dar uno o siete.
    """
    assert hue.POROTOS_POR_COSECHA == (2, 4)


def test_la_cosecha_siempre_cae_dentro_del_rango():
    """Y con varias semillas distintas, no con una sola tirada afortunada; y no
    siempre el mismo número, o el rango sería de adorno."""
    minimo, maximo = hue.POROTOS_POR_COSECHA
    vistos = {hue.tirar_cuantos(random.Random(semilla)) for semilla in range(40)}
    assert vistos == set(range(minimo, maximo + 1))


def test_sin_dado_inyectado_cada_tirada_saca_uno_propio():
    """El día del cambio trae su RNG, pero las tiradas no lo exigen: sin él
    sacan uno propio y siguen cayendo dentro de lo suyo."""
    minimo, maximo = hue.POROTOS_POR_COSECHA
    for _ in range(50):
        assert minimo <= hue.tirar_cuantos() <= maximo
        assert hue.tirar_arcoiris() in (True, False)
        assert hue.tirar_color() in hue.COLORES
        assert hue.tirar_caras_de_arcoiris() in hue.CARAS_DE_ARCOIRIS


def test_la_probabilidad_del_arcoiris_esta_clavada():
    """Con literales y no leyendo la constante: deducir de ella lo que se espera
    haría que cambiarla moviera también la portería, y el test no protegería
    nada. Si esto falla es que alguien tocó el equilibrio a propósito.
    """
    assert hue.PROBABILIDAD_ARCOIRIS == 0.05
    assert sorted(hue.CARAS_DE_ARCOIRIS) == [4, 6, 8, 10, 12]
    assert hue.tirar_arcoiris(DadosDelHuerto(arcoiris=True))
    assert not hue.tirar_arcoiris(DadosDelHuerto(arcoiris=False))


def test_el_arcoiris_no_es_un_color():
    """Está fuera de `COLORES` a propósito: si entrara, se sortearía como uno
    más y habría que darle sitio en la tabla de gustos de cada carácter."""
    assert hue.ARCOIRIS not in hue.COLORES
    assert hue.ARCOIRIS in hue.COCINABLES
    assert hue.color_sembrado(hue.clave_de_poroto(hue.ARCOIRIS)) is None
    assert hue.color_sembrado(hue.SEMILLA) is None
    assert hue.color_sembrado(hue.clave_de_poroto("rojo")) == "rojo"
    for _ in range(50):
        assert hue.tirar_color() != hue.ARCOIRIS


# --- Cocinar ---

def test_cocinar_gasta_los_porotos_y_da_la_sopaipilla():
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(
            con, "u1", "g1", hue.clave_de_poroto("rojo"),
            hue.POROTOS_POR_SOPAIPILLA + 1,
        )

    resultado = economia.cocinar("u1", "g1", "rojo")

    assert resultado.ok
    mochila = db.inventario("u1", "g1")
    assert mochila[hue.clave_de_poroto("rojo")] == 1
    assert mochila[hue.clave_de_sopaipilla("rojo")] == 1


def test_sin_porotos_suficientes_no_se_cocina_ni_se_gasta_nada():
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(con, "u1", "g1", hue.clave_de_poroto("rojo"), 2)

    resultado = economia.cocinar("u1", "g1", "rojo")

    assert not resultado.ok and "y tienes 2" in resultado.problema
    assert db.inventario("u1", "g1")[hue.clave_de_poroto("rojo")] == 2


def test_no_se_cocina_un_color_que_no_existe():
    with pytest.raises(ValueError):
        economia.cocinar("u1", "g1", "morado")


def test_la_cocina_hace_el_arcoiris_cuando_te_llegan():
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(
            con, "u1", "g1", hue.clave_de_poroto(hue.ARCOIRIS),
            hue.POROTOS_POR_SOPAIPILLA,
        )

    assert hue.ARCOIRIS in hue.COCINABLES
    assert hue.nombre_de(hue.ARCOIRIS) == hue.NOMBRE_ARCOIRIS
    assert hue.emoji_de(hue.ARCOIRIS) == hue.EMOJI_ARCOIRIS
    resultado = economia.cocinar("u1", "g1", hue.ARCOIRIS, T0, random.Random(1))
    assert resultado.ok
    mochila = db.inventario("u1", "g1")
    assert mochila[resultado.sopaipilla.clave] == 1
    assert resultado.sopaipilla.caras in hue.CARAS_DE_ARCOIRIS
    assert mochila.get(hue.clave_de_poroto(hue.ARCOIRIS), 0) == 0


def test_la_cocina_solo_hace_los_colores_que_te_llegan():
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(
            con, "u1", "g1", hue.clave_de_poroto("rojo"),
            hue.POROTOS_POR_SOPAIPILLA,
        )
        db.guardar_en_la_mochila_en(con, "u1", "g1", hue.clave_de_poroto("azul"), 1)

    assert not economia.cocinar("u1", "g1", "azul").ok
    assert economia.cocinar("u1", "g1", "rojo").ok
    assert (hue.nombre_de("rojo"), hue.emoji_de("rojo")) == ("rojo", hue.EMOJI_COLOR["rojo"])


def test_el_dado_del_arcoiris_se_sortea_al_cocinarlo():
    """Es lo que se pidió: cocinarlo también se juega. Salen los cinco tamaños,
    y con el mismo reparto que las de color —ninguno cargado hacia el 12—.
    """
    salidos = []
    for vuelta in range(60):
        with db.conectar() as con:
            db.guardar_en_la_mochila_en(
                con, "u1", "g1", hue.clave_de_poroto(hue.ARCOIRIS),
                hue.POROTOS_POR_SOPAIPILLA,
            )
        cocinada = economia.cocinar(
            "u1", "g1", hue.ARCOIRIS, T0, random.Random(vuelta)
        )
        assert cocinada.ok
        salidos.append(cocinada.sopaipilla.caras)

    assert set(salidos) == set(hue.CARAS_DE_ARCOIRIS)
    # Cada sopaipilla guarda su dado: si la clave no lo llevara, todas las de la
    # mochila serían la misma y el sorteo no habría servido de nada.
    mochila = db.inventario("u1", "g1")
    for caras in hue.CARAS_DE_ARCOIRIS:
        clave = hue.clave_de_sopaipilla(hue.ARCOIRIS, caras)
        assert mochila[clave] == salidos.count(caras), caras


def test_una_cocina_que_falla_no_gasta_una_tirada_de_dado():
    """El dado se tira con los porotos ya gastados. Si se tirara antes, quien no
    llegara a tres porotos iría corriendo el sorteo sin cocinar nada."""
    class DadoQueChilla:
        def choice(self, opciones):
            raise AssertionError("no debería tirarse el dado sin cocinar")

    with db.conectar() as con:
        db.guardar_en_la_mochila_en(
            con, "u1", "g1", hue.clave_de_poroto(hue.ARCOIRIS), 2
        )

    fallida = economia.cocinar("u1", "g1", hue.ARCOIRIS, T0, DadoQueChilla())

    assert not fallida.ok and "y tienes 2" in fallida.problema


# --- Comerse la sopaipilla ---

def test_la_sopaipilla_sube_fuerza_y_velocidad_a_la_vez():
    """Un plato, no dos pociones: el mismo número en las dos."""
    bicho = nacer(especie="chispa")
    dar(objs.CATALOGO[hue.clave_de_sopaipilla("rojo")])

    resultado = usar(
        objs.CATALOGO[hue.clave_de_sopaipilla("rojo")], T0, random.Random(3)
    )

    # `efectos_activos` devuelve (bonus, lo que queda), no sólo el número.
    efectos = {
        stat: bonus for stat, (bonus, _) in
        db.efectos_activos(bicho.id, T0).items()
    }
    assert set(efectos) == {"fuerza", "velocidad"}
    assert efectos["fuerza"] == efectos["velocidad"]
    assert resultado.bonus == efectos["fuerza"]


@pytest.mark.parametrize("caras", hue.CARAS_DE_ARCOIRIS)
def test_la_sopaipilla_arcoiris_sube_las_cuatro_con_su_dado(caras):
    """Lo mismo que la de color —un plato, un solo dado— pero en las cuatro, y
    con el dado que le tocó al cocinarla en vez de con el del carácter."""
    bicho = nacer(especie="chispa")
    sopaipilla = objs.CATALOGO[hue.clave_de_sopaipilla(hue.ARCOIRIS, caras)]
    dar(sopaipilla)

    resultado = usar(sopaipilla, T0, random.Random(3))

    efectos = {
        stat: bonus for stat, (bonus, _) in
        db.efectos_activos(bicho.id, T0).items()
    }
    assert set(efectos) == set(sim.ESTADISTICAS)
    assert len(set(efectos.values())) == 1      # el mismo número en las cuatro
    assert 1 <= efectos["salud"] <= caras
    assert resultado.bonus == efectos["salud"] and resultado.caras == caras


def test_el_dado_del_arcoiris_es_el_suyo_y_no_el_del_caracter():
    """No tiene color, así que no hay tabla de gustos que consultar: se come con
    el dado que traiga escrito, le toque el carácter que le toque."""
    class DadoEspia:
        def __init__(self):
            self.caras = None

        def randint(self, a, b):
            self.caras = b
            return b

    # Una criatura sola, cambiándole el carácter: sólo hay una activa por
    # persona y servidor, y lo que se mira aquí es el dado, no la criatura.
    bicho = nacer()
    for caracter in per.CARACTERES:
        db.guardar(replace(bicho, caracter=caracter))
        for caras in hue.CARAS_DE_ARCOIRIS:
            espia = DadoEspia()
            sopaipilla = objs.CATALOGO[hue.clave_de_sopaipilla(hue.ARCOIRIS, caras)]
            dar(sopaipilla)
            usar(sopaipilla, T0, espia)
            assert espia.caras == caras, (caracter, caras)


def test_el_dado_de_la_sopaipilla_sale_del_caracter():
    bicho = nacer()
    favorito = hue.AFINIDAD[bicho.caracter][0]
    peor = hue.AFINIDAD[bicho.caracter][-1]

    dar(objs.CATALOGO[hue.clave_de_sopaipilla(favorito)])
    dar(objs.CATALOGO[hue.clave_de_sopaipilla(peor)])

    bueno = usar(objs.CATALOGO[hue.clave_de_sopaipilla(favorito)], T0)
    malo = usar(objs.CATALOGO[hue.clave_de_sopaipilla(peor)], T0)

    assert bueno.caras == 12 and bueno.gusto == "es su favorito"
    assert malo.caras == 4 and malo.gusto == "lo detesta"


def test_la_sopaipilla_no_se_acumula():
    """Como las pociones: la nueva sustituye a la anterior."""
    bicho = nacer()
    dar(objs.CATALOGO[hue.clave_de_sopaipilla("rojo")], 3)
    for _ in range(3):
        usar(objs.CATALOGO[hue.clave_de_sopaipilla("rojo")], T0)

    efectos = db.efectos_activos(bicho.id, T0)
    assert len(efectos) == 2                 # fuerza y velocidad, una de cada


# --- Lo que no se vende ---

def test_los_porotos_y_las_sopaipillas_no_se_compran():
    """Y desde que se fue el huerto por casa, tampoco la semilla."""
    for color in hue.COLORES:
        for clave in (hue.clave_de_poroto(color), hue.clave_de_sopaipilla(color)):
            assert not objs.CATALOGO[clave].se_vende, clave
    assert not objs.CATALOGO["semilla"].se_vende
