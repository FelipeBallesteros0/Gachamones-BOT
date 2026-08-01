"""El catálogo de consumibles: precios, dados y qué hace cada uno."""
import random

import huerto as hue
import objetos as obj
import simulacion as sim


class DadoFijo(random.Random):
    """Un dado guionizado, para que el bonus de una poción sea predecible."""

    def __init__(self, valor):
        super().__init__()
        self.valor = valor

    def randint(self, a, b):
        assert a == 1, (a, b)
        return min(self.valor, b)


# --- El catálogo -----------------------------------------------------------

def test_estan_los_objetos_pedidos():
    """Una poción de comida, cinco tamaños por cada estadística, los dos
    reinicios de enfriamiento, la placa con nombre, las golosinas, el ticket del
    refugio y la semilla. Y aparte, lo que no se vende: un poroto y una
    sopaipilla por color."""
    a_la_venta = [o for o in obj.CATALOGO.values() if o.se_vende]
    assert len(a_la_venta) == 17
    assert len(obj.CATALOGO) == 17 + 2 * len(hue.COLORES)

    caras = sorted(o.caras for o in obj.CATALOGO.values() if o.stat == "fuerza")
    assert caras == [4, 6, 8, 10, 12]
    assert caras == sorted(
        o.caras for o in obj.CATALOGO.values() if o.stat == "velocidad"
    )


def test_todo_objeto_tiene_precio_nombre_y_clave_distinta():
    for clave, objeto in obj.CATALOGO.items():
        assert objeto.clave == clave, clave
        # Lo que no se vende no tiene por qué valer nada: los porotos se
        # cosechan y las sopaipillas se cocinan.
        assert (objeto.precio > 0) == objeto.se_vende, clave
        assert objeto.nombre.strip(), clave
        assert objeto.emoji.strip(), clave
        assert objeto.descripcion.strip(), clave

    nombres = [o.nombre for o in obj.CATALOGO.values()]
    assert len(set(nombres)) == len(nombres), "hay dos objetos con el mismo nombre"


def test_cuanto_mas_grande_el_dado_mas_caro():
    """Si una poción mayor costase menos, la pequeña no la compraría nadie."""
    for stat in ("fuerza", "velocidad"):
        pociones = sorted(
            (o for o in obj.CATALOGO.values() if o.stat == stat),
            key=lambda o: o.caras,
        )
        precios = [o.precio for o in pociones]
        assert precios == sorted(precios), (stat, precios)
        assert len(set(precios)) == len(precios), (stat, precios)


def test_lo_que_se_vende_cabe_en_un_desplegable_de_discord():
    """Discord no admite más de 25 opciones en un menú.

    Se mide sobre lo que sale a la venta y no sobre el catálogo entero: los
    porotos y las sopaipillas están en él para poder vivir en la mochila y
    regalarse, pero la tienda no los ofrece. El catálogo entero ya se pasa.
    """
    assert len([o for o in obj.CATALOGO.values() if o.se_vende]) <= 25


# --- Las pociones de estadística -------------------------------------------

def test_la_pocion_tira_su_dado_al_beberla():
    """Se tira al beber y no al competir: así el mensaje puede decir cuánto te
    ha tocado. Tirándolo en la pelea no habría forma de saber si sirvió."""
    pocion = obj.CATALOGO["fuerza_1d12"]
    assert obj.tirar_bonus(pocion, DadoFijo(7)) == 7
    assert obj.tirar_bonus(pocion, DadoFijo(99)) == 12  # topa en las caras


def test_el_bonus_siempre_suma_algo():
    rng = random.Random(3)
    for clave, objeto in obj.CATALOGO.items():
        if objeto.stat is None:
            continue
        for _ in range(200):
            bonus = obj.tirar_bonus(objeto, rng)
            assert 1 <= bonus <= objeto.caras, (clave, bonus)


def test_las_pociones_duran_cinco_minutos():
    """Cinco y no uno: quien acepta un reto tiene 120 segundos para pulsar, y la
    estadística se lee al resolver la pelea, no al retar. Con un minuto la
    poción habría caducado en la mayoría de las carreras."""
    assert obj.MINUTOS_DE_EFECTO * 60 > 120 + 30


def test_cada_pocion_dice_a_que_estadistica_va():
    for clave, objeto in obj.CATALOGO.items():
        if objeto.stat is not None:
            assert objeto.stat in ("fuerza", "velocidad"), clave
            assert str(objeto.caras) in objeto.nombre, clave


# --- Lo que hace cada objeto que no es poción de estadística ---------------

def test_la_pocion_de_comida_llena_del_todo_y_no_empacha():
    """Es una poción, no comida: se salta el empacho y el enfriamiento."""
    llena = sim.Criatura(
        id=1, usuario_id="u", guild_id="g", especie="pulpo", nombre="X",
        nacida_en=None, actualizada_en=None,
        base_fuerza=10, base_velocidad=10, base_salud=10,
        hambre=95.0, animo=50.0,
    )
    assert llena.hambre > sim.UMBRAL_EMPACHO  # si no, el test no prueba nada

    nueva = obj.aplicar_a_la_criatura(obj.CATALOGO["pocion_comida"], llena)
    assert nueva.hambre == 100.0
    assert nueva.animo == llena.animo, "la comida no toca el ánimo"


def test_los_reinicios_no_tocan_la_criatura():
    """Borran un enfriamiento, que vive en otra tabla: aquí no cambian nada."""
    criatura = sim.Criatura(
        id=1, usuario_id="u", guild_id="g", especie="pulpo", nombre="X",
        nacida_en=None, actualizada_en=None,
        base_fuerza=10, base_velocidad=10, base_salud=10,
        hambre=50.0, animo=50.0,
    )
    for clave in ("descanso_rapido", "silbato"):
        assert obj.aplicar_a_la_criatura(obj.CATALOGO[clave], criatura) is criatura


def test_los_reinicios_apuntan_a_acciones_de_verdad():
    reinicios = {o.reinicia for o in obj.CATALOGO.values() if o.reinicia}
    assert reinicios == {sim.COMPETIR, sim.ENTRENAR}
    for accion in reinicios:
        assert accion in sim.COOLDOWNS


def _efectos(objeto) -> list[bool]:
    return [objeto.stat is not None, objeto.reinicia is not None,
            bool(objeto.alimenta), objeto.renombra, objeto.ceba,
            bool(objeto.dias_de_refugio), objeto.es_sopaipilla]


def test_todo_objeto_hace_al_menos_una_cosa():
    """Lo que de verdad protegía el invariante viejo: que la tienda no venda
    algo que no hace nada.

    Antes exigía **exactamente** una cosa, y eso prohibía justo lo que ahora se
    quiere: las golosinas alimentan y además sirven de cebo. Lo que no puede
    haber es un objeto sin ningún efecto.

    Los ingredientes quedan fuera: un poroto no hace nada por sí solo —para eso
    es ingrediente— y la semilla se planta en el huerto, no se usa desde la
    mochila. Lo que se vende sin efecto y sin uso sí sería un timo.
    """
    ingredientes = {hue.clave_de_poroto(c) for c in hue.COLORES} | {"semilla"}
    for clave, objeto in obj.CATALOGO.items():
        if clave in ingredientes:
            continue
        assert any(_efectos(objeto)), clave


def test_los_ingredientes_dicen_para_qué_son():
    """No hacen nada al usarlos, así que su descripción es lo único que evita
    que parezcan un objeto roto."""
    for color in hue.COLORES:
        poroto = obj.CATALOGO[hue.clave_de_poroto(color)]
        assert "sopaipilla" in poroto.descripcion.lower(), color
        assert not poroto.se_usa_en_mochila, color
    assert "huerto" in obj.CATALOGO["semilla"].descripcion.lower()


def test_un_objeto_de_dos_usos_lo_dice_en_su_descripcion():
    """Si un objeto sirve en la mochila **y** en una aventura, la descripción
    tiene que decirlo.

    Es el fallo que hubo: las golosinas se gastaban desde la mochila sin hacer
    nada y su descripción sólo hablaba del cebo. Así no se puede volver a colar
    un objeto con un segundo uso escondido.
    """
    for clave, objeto in obj.CATALOGO.items():
        if objeto.ceba and objeto.se_usa_en_mochila:
            assert "aventura" in objeto.descripcion.lower(), (
                f"{clave} sirve para dos cosas y su descripción sólo cuenta una"
            )


def test_lo_que_no_se_usa_en_la_mochila_esta_declarado():
    """`se_usa_en_mochila` es lo que consulta el menú antes de gastar la unidad:
    tiene que coincidir con lo que el objeto hace de verdad."""
    for clave, objeto in obj.CATALOGO.items():
        esperado = bool(objeto.stat or objeto.reinicia or objeto.alimenta
                        or objeto.renombra or objeto.dias_de_refugio
                        or objeto.es_sopaipilla)
        assert objeto.se_usa_en_mochila == esperado, clave


def test_las_golosinas_alimentan_menos_que_la_pocion():
    """Si llenaran igual, la poción —que cuesta más y encima no sirve de cebo—
    no la compraría nadie."""
    golosinas = obj.CATALOGO["golosinas"]
    pocion = obj.CATALOGO["pocion_comida"]
    assert 0 < golosinas.alimenta < pocion.alimenta
    assert golosinas.precio < pocion.precio
