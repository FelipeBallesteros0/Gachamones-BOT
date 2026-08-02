"""El jardín: que quepan todas y que el marco no se descuadre nunca."""
import re
from datetime import datetime, timezone

import especies as esp
import ia
import jardin
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def criatura(especie="pollito", nombre="Prueba", nivel=1, **cambios) -> sim.Criatura:
    base = dict(
        id=1, usuario_id="u1", guild_id="g1", especie=especie, nombre=nombre,
        nacida_en=T0, actualizada_en=T0, nivel=nivel,
        base_fuerza=15, base_velocidad=15, base_salud=15,
    )
    base.update(cambios)
    return sim.Criatura(**base)


def lineas(escena: str) -> list[str]:
    dentro = escena.split("```ansi\n")[1].split("\n```")[0]
    return ANSI.sub("", dentro).split("\n")


def comprobar_marco(escena: str, ancho: int = jardin.ANCHO) -> None:
    for linea in lineas(escena):
        assert len(linea) == ancho + 2, (len(linea), repr(linea))
        assert linea[0] in "╭│╰"
        assert linea[-1] in "╮│╯"


# --- El marco aguanta cualquier cosa ---------------------------------------

def test_el_jardin_vacio_cuadra():
    """Regresión: se usaba pantalla.fila(), fijada al ancho de la pantalla
    individual (26), y el marco del jardín salía roto."""
    comprobar_marco(jardin.render([]))


def test_una_sola_criatura():
    comprobar_marco(jardin.render([criatura()]))


def test_muchas_criaturas_de_todas_las_etapas():
    bichos = [
        criatura(especie=clave, nombre=clave[:8], nivel=nivel)
        for clave in esp.ESPECIES
        for nivel in (1, 3, 5)
    ]
    comprobar_marco(jardin.render(bichos))


def test_todas_las_combinaciones_de_especie_y_etapa_caben():
    for clave in esp.ESPECIES:
        for nivel in range(1, 6):
            for hambre, animo in ((90, 90), (50, 50), (10, 10)):
                comprobar_marco(jardin.render([
                    criatura(especie=clave, nivel=nivel, hambre=hambre, animo=animo)
                ]))


def test_un_nombre_larguisimo_no_rompe_el_marco():
    comprobar_marco(jardin.render([
        criatura(nombre="Bartolomeo Maximiliano de la Vega y Mendoza III")
    ]))


def test_funciona_con_un_marco_estrecho():
    comprobar_marco(jardin.render([criatura(), criatura()], ancho=20), ancho=20)


# --- El reparto en filas ---------------------------------------------------

def bloque(ancho: int) -> jardin.Bloque:
    return jardin.Bloque(["#" * ancho], "x", esp.BLANCO)


def test_las_criaturas_que_caben_van_en_la_misma_fila():
    filas = jardin.repartir([bloque(10), bloque(10)], ancho=44)
    assert len(filas) == 1


def test_las_que_no_caben_pasan_a_la_siguiente_fila():
    filas = jardin.repartir([bloque(20), bloque(20), bloque(20)], ancho=44)
    assert [len(f) for f in filas] == [2, 1]


def test_se_tiene_en_cuenta_la_separacion_entre_criaturas():
    """Dos de 21 suman 42, pero con la separación de 3 se pasan de 44."""
    assert len(jardin.repartir([bloque(21), bloque(21)], ancho=44)) == 2


def test_una_criatura_mas_ancha_que_la_fila_va_sola():
    """No puede romper el marco por muy grande que sea."""
    filas = jardin.repartir([bloque(10), bloque(60), bloque(10)], ancho=44)
    assert [len(f) for f in filas] == [1, 1, 1]


def test_sin_bloques_no_hay_filas():
    assert jardin.repartir([]) == []


# --- La escena -------------------------------------------------------------

def test_los_nombres_salen_debajo_de_cada_criatura():
    escena = jardin.render([criatura(nombre="Kuro"), criatura(nombre="Nube")])
    assert "Kuro" in escena
    assert "Nube" in escena


def test_cada_criatura_sale_con_el_arte_de_su_etapa():
    bebe = jardin.render([criatura(nivel=1)])
    mayor = jardin.render([criatura(nivel=5)])
    assert bebe != mayor


def test_las_criaturas_pisan_el_mismo_suelo():
    """Se alinean por abajo: si no, las pequeñas flotarían a media altura."""
    escena = lineas(jardin.render([criatura(nivel=1), criatura(nivel=5)]))
    suelo = [l for l in escena if jardin.SUELO * 5 in l]
    assert suelo, "falta la línea de suelo"

    fila_nombres = escena[escena.index(suelo[0]) - 1]
    # Los dos nombres están en la misma línea, justo encima del suelo.
    assert fila_nombres.count("Prueba") == 2


def sangrias(lineas: list[str]) -> list[int]:
    return [len(l) - len(l.lstrip()) for l in lineas if l.strip()]


def test_el_dibujo_no_se_deforma_al_colocarlo():
    """Regresión: se centraba CADA LÍNEA por separado, y como la sangría propia
    de cada una cuenta para su longitud, las más indentadas se desplazaban más
    que el resto. Las criaturas salían corridas."""
    for clave in esp.ESPECIES:
        for nivel in range(1, 6):
            c = criatura(especie=clave, nivel=nivel, nombre="Un nombre largo")
            b = jardin.bloque_de(c)
            colocadas = [b.linea(i) for i in range(len(b.lineas))]

            # Las distancias entre líneas tienen que ser las mismas antes y
            # después de colocar el bloque.
            antes = sangrias(b.lineas)
            despues = sangrias(colocadas)
            desplazamiento = despues[0] - antes[0]
            assert [d - desplazamiento for d in despues] == antes, (clave, nivel)


def test_el_dibujo_sigue_centrado_bajo_su_nombre():
    c = criatura(especie="chispa", nombre="Mr. Pyro")
    b = jardin.bloque_de(c)
    colocadas = [b.linea(i) for i in range(len(b.lineas))]

    izquierda = min(len(l) - len(l.lstrip()) for l in colocadas if l.strip())
    derecha = min(len(l) - len(l.rstrip()) for l in colocadas if l.strip())
    assert abs(izquierda - derecha) <= 1, (izquierda, derecha)


def test_el_jardin_vacio_lo_dice():
    assert "vacío" in jardin.render([])


def test_hay_frases_de_respaldo_para_cuando_falle_la_ia():
    frases = {jardin.frase_de_respaldo(i) for i in range(len(jardin.RESPALDO))}
    assert len(frases) == len(jardin.RESPALDO)
    for f in frases:
        assert f.strip()
        for fea in ("error", "api", "fall"):
            assert fea not in f.lower()


# --- Que quepa en un mensaje de Discord ------------------------------------

def poblado(cuantas: int) -> list[sim.Criatura]:
    """Un servidor con criaturas de todas las especies, en su etapa mayor.

    Mezcla especies a propósito: el reparto empaqueta de a dos o de a tres según
    lo anchas que sean, así que un jardín de puros Nacar y uno de puros
    Magnetrón no miden ni de lejos lo mismo.
    """
    claves = list(esp.ESPECIES)
    return [
        criatura(especie=claves[i % len(claves)], nombre=f"Bicho{i}", nivel=5)
        for i in range(cuantas)
    ]


def test_el_jardin_de_un_servidor_lleno_cabe_en_un_mensaje():
    """**El fallo que llegó a producción.** El jardín es lo único del juego que
    crece con la gente que juega, y con 28 criaturas pedía 7500 caracteres: el
    comando reventaba con un 400 de Discord y, como ya había diferido, se
    quedaba en «pensando…» para siempre.

    Ninguna otra pantalla tiene este problema —la ficha, la casa y la tienda
    están acotadas—, y por eso no lo cazaba ningún test.
    """
    for cuantas in (1, 5, 28, 100):
        criaturas = poblado(cuantas)
        caben = jardin.cuantas_caben(criaturas)
        escena = jardin.render(criaturas[:caben])
        assert len(escena) <= jardin.TOPE_MENSAJE - jardin.MARGEN_DEL_TEXTO, (
            cuantas, caben, len(escena)
        )


def test_el_margen_es_una_estimacion_holgada_de_lo_que_va_fuera():
    """El margen sirve para que el reparto acierte a la primera, no para
    garantizar nada: quien garantiza es `_recortar`, que mide el mensaje ya
    montado. Aun así tiene que ser una estimación decente del caso normal.

    Un test que midiera un jardín de prueba no valdría: cada criatura son unos
    250 caracteres de golpe, así que el último escalón deja tanta holgura que
    pasaría con el margen en 20. Lo comprobé, y pasaba.
    """
    titulo = "## 🌳 El jardín · 999 gachamones\n"
    narracion_normal = jardin.LARGO_NARRACION + 2 * 4   # unas cuatro líneas
    resto = "\n-# Y 999 más, que hoy no han salido."

    assert len(titulo) + narracion_normal + len(resto) <= jardin.MARGEN_DEL_TEXTO


def test_la_narracion_del_jardin_es_mas_corta_que_la_de_la_charla():
    """Cada carácter de narración es un carácter menos de dibujo, y aquí lo que
    importa es el cuadro. Con el tope general —600— la narración sola se comería
    más de un tercio del mensaje."""
    assert jardin.LARGO_NARRACION < ia.LARGO_MAXIMO


def test_caben_todas_cuando_son_pocas():
    """El recorte sólo debe entrar cuando hace falta: con cuatro criaturas no
    puede desaparecer ninguna."""
    criaturas = poblado(4)
    assert jardin.cuantas_caben(criaturas) == 4


def test_cuantas_caben_no_se_pasa_ni_por_una():
    """La frontera: si dice que caben N, con N+1 tiene que pasarse. Si no,
    estaría recortando de más y quitando bichos sin motivo."""
    criaturas = poblado(60)
    caben = jardin.cuantas_caben(criaturas)
    assert 0 < caben < 60
    presupuesto = jardin.TOPE_MENSAJE - jardin.MARGEN_DEL_TEXTO
    assert len(jardin.render(criaturas[:caben])) <= presupuesto
    assert len(jardin.render(criaturas[:caben + 1])) > presupuesto


def test_nunca_se_esconden_todas():
    """Un jardín que dijera «está vacío» teniendo criaturas estaría mintiendo.
    Aunque el presupuesto sea absurdo, siempre se asoma al menos una."""
    assert jardin.cuantas_caben(poblado(10), presupuesto=1) == 1
    assert jardin.cuantas_caben([], presupuesto=1) == 0


def test_el_recorte_final_aguanta_una_narracion_desatada():
    """Lo que de verdad garantiza que el mensaje quepa.

    La narración la escribe la IA y su tamaño no se puede predecir: si devuelve
    muchas líneas cortas, el citado —«> » por línea— casi triplica. `_recortar`
    no lo estima, lo mide, y va quitando criaturas hasta que cabe.
    """
    from cogs.social import Social

    todas = poblado(28)
    titulo = "## 🌳 El jardín · 28 gachamones\n"
    # El peor citado imaginable: 280 caracteres, todos en líneas de uno.
    citado = "\n".join("> " + c for c in "x" * jardin.LARGO_NARRACION)
    asomadas = todas[:jardin.cuantas_caben(todas)]

    mensaje, quedan = Social._recortar(titulo, citado, asomadas, todas)
    assert len(mensaje) <= jardin.TOPE_MENSAJE, len(mensaje)
    assert quedan, "no puede quedarse sin ninguna"
    assert "Y " in mensaje and "más" in mensaje


def test_el_recorte_no_toca_nada_cuando_ya_cabe():
    """No puede quitar criaturas por si acaso: con pocas, salen todas y no hay
    coletilla que sobre."""
    from cogs.social import Social

    todas = poblado(3)
    mensaje, quedan = Social._recortar("## 🌳\n", "> Una frase.", todas, todas)
    assert len(quedan) == 3
    assert "más, que hoy no han salido" not in mensaje
