"""El jardín: que quepan todas y que el marco no se descuadre nunca."""
import re
from datetime import datetime, timezone

import especies as esp
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
    c = criatura(especie="chispa", nombre="Mr. Chispa")
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
