"""Los cosméticos: el catálogo, y que ninguno descuadre una ficha.

El grueso de este fichero mide anchos. Es donde han salido todos los descuadres
de este proyecto, y siempre igual: algo se centra sobre otra cosa con la que no
comparte eje. Aquí se comprueban las 25 especies × 5 etapas × 6 sombreros de
una vez, porque a mano no se ve.
"""
import re
from datetime import datetime, timezone

import pytest

import cosmeticos as cos
import especies as esp
import pantalla
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
CODIGOS = re.compile(r"\x1b\[[0-9;]*m")


def sin_color(texto: str) -> str:
    """El ancho de verdad, que es el único que cuenta.

    Medir con los códigos ANSI dentro es lo que hace ver marcos rotos que están
    perfectos, y al revés."""
    return CODIGOS.sub("", texto)


def criatura(**cambios) -> sim.Criatura:
    base = dict(
        id=1, usuario_id="u1", guild_id="g1", especie="pulpo", nombre="Prueba",
        nacida_en=T0, actualizada_en=T0,
        base_fuerza=15, base_velocidad=15, base_salud=15,
    )
    base.update(cambios)
    return sim.Criatura(**base)


def caja_de(ficha: str) -> list[str]:
    """Las líneas de dentro del bloque ```ansi```, sin colores."""
    dentro = ficha.split("```ansi\n", 1)[1].split("\n```", 1)[0]
    return [sin_color(linea) for linea in dentro.split("\n")]


# --- El catálogo -----------------------------------------------------------

def test_ningun_cosmetico_esta_a_medias():
    for cosmetico in cos.CATALOGO.values():
        assert cosmetico.clave and cosmetico.nombre.strip(), cosmetico.clave
        assert cosmetico.tipo in cos.TIPOS, cosmetico.clave
        assert cosmetico.valor, cosmetico.clave
        assert cosmetico.precio > 0, cosmetico.clave


def test_ninguna_clave_se_repite_y_hay_de_los_cuatro_tipos():
    claves = [c.clave for c in cos.CATALOGO.values()]
    assert len(set(claves)) == len(claves)
    for tipo in cos.TIPOS:
        assert cos.del_tipo(tipo), tipo


def test_una_clave_que_ya_no_existe_no_rompe_la_ficha():
    """Un cosmético retirado del catálogo deja filas viejas apuntando a él. La
    ficha tiene que salir igual, sin corona pero sin reventar."""
    fantasma = criatura(
        tinte="tinte_que_se_retiro", sombrero="ni_idea",
        marco="tampoco", titulo="menos",
    )
    assert cos.buscar("lo_que_sea") is None
    assert cos.marco_de("lo_que_sea") == cos.REDONDO
    assert cos.texto_del_titulo("lo_que_sea", esp.MACHO) == ""
    assert pantalla.render(fantasma, T0) == pantalla.render(criatura(), T0)


# --- Tintes ----------------------------------------------------------------

def test_el_tinte_sustituye_al_color_de_la_especie():
    de_serie = pantalla.render(criatura(), T0)
    tenido = pantalla.render(criatura(tinte="tinte_rojo"), T0)

    assert f"\x1b[0;{esp.ESPECIES['pulpo'].color}m" in de_serie
    assert f"\x1b[0;{esp.ROJO}m" in tenido
    assert f"\x1b[0;{esp.ESPECIES['pulpo'].color}m" not in tenido
    # Y el dibujo es el mismo: sólo cambia de color.
    assert caja_de(de_serie) == caja_de(tenido)


@pytest.mark.parametrize("tinte", cos.del_tipo(cos.TINTE))
def test_ningun_tinte_descuadra_la_caja(tinte):
    for linea in caja_de(pantalla.render(criatura(tinte=tinte.clave), T0)):
        assert len(linea) == pantalla.ANCHO + 2, repr(linea)


# --- Sombreros -------------------------------------------------------------

def test_ningun_dibujo_llega_a_las_siete_filas():
    """**El invariante que hace posibles los sombreros.** El marco reserva
    siete filas; si algún día un dibujo usa las siete, el sombrero se comería la
    última sin que nadie se entere. Que salte aquí y no en Discord."""
    for clave, definicion in esp.ESPECIES.items():
        for etapa in esp.ETAPAS:
            arte = esp.arte_de(definicion, etapa, "normal")
            filas = len(arte.strip("\n").split("\n"))
            assert filas < pantalla.ALTO_ARTE, f"{clave} {etapa}: {filas} filas"


def test_el_sombrero_no_descuadra_ninguna_ficha():
    """Las 25 × 5 × 6 combinaciones, midiendo el ancho visible."""
    for clave in esp.ESPECIES:
        for nivel in range(1, len(esp.ETAPAS) + 1):
            for sombrero in cos.del_tipo(cos.SOMBRERO):
                vestida = criatura(
                    especie=clave, nivel=nivel, sombrero=sombrero.clave
                )
                for linea in caja_de(pantalla.render(vestida, T0)):
                    assert len(linea) == pantalla.ANCHO + 2, (
                        f"{clave} nivel {nivel} con {sombrero.clave}: {linea!r}"
                    )


def test_el_sombrero_no_come_dibujo():
    """El riesgo de verdad: la caja mide lo mismo con sombrero y sin él, así que
    la fila que ocupa tiene que salir del hueco libre y no del dibujo."""
    for clave in esp.ESPECIES:
        for nivel in range(1, len(esp.ETAPAS) + 1):
            pelada = caja_de(pantalla.render(
                criatura(especie=clave, nivel=nivel), T0))
            con_corona = caja_de(pantalla.render(
                criatura(especie=clave, nivel=nivel, sombrero="corona"), T0))

            assert len(pelada) == len(con_corona)
            # Ninguna fila con dibujo desaparece: todas las que tenían algo
            # siguen estando, en el mismo orden.
            dibujo = [ln for ln in pelada if ln.strip("│ ")]
            despues = [ln for ln in con_corona if ln.strip("│ ")]
            for fila in dibujo:
                assert fila in despues, f"{clave} nivel {nivel} perdió {fila!r}"


def _extremos(filas):
    """Primer y último carácter con tinta de un bloque de filas."""
    cuerpos = [fila.strip("│").rstrip() for fila in filas]
    cuerpos = [c for c in cuerpos if c.strip()]
    izquierda = min(len(c) - len(c.lstrip()) for c in cuerpos)
    derecha = max(len(c) for c in cuerpos) - 1
    return izquierda, derecha


def _eje(filas):
    izquierda, derecha = _extremos(filas)
    return (izquierda + derecha) / 2


def test_el_sombrero_va_sobre_el_eje_del_dibujo():
    """Lo que se ve mal aunque el ancho cuadre: la corona puesta de lado.

    El eje es el punto medio entre el primer y el último carácter con tinta del
    bloque, que es como se ha medido siempre la simetría de los dibujos. Medio
    carácter de margen porque los anchos pares y los impares no pueden caer los
    dos exactos, y no se distingue a ojo."""
    for clave in esp.ESPECIES:
        for nivel in range(1, len(esp.ETAPAS) + 1):
            caja = caja_de(pantalla.render(
                criatura(especie=clave, nivel=nivel, sombrero="corona"), T0))
            arte = [ln for ln in caja[1:pantalla.ALTO_ARTE + 1] if ln.strip("│ ")]
            sombrero, dibujo = arte[0], arte[1:]

            assert "\\_Y_/" in sombrero, f"{clave} nivel {nivel}: sin sombrero"
            assert abs(_eje([sombrero]) - _eje(dibujo)) <= 0.5, (
                f"{clave} nivel {nivel}: sombrero en {_eje([sombrero])}, "
                f"dibujo en {_eje(dibujo)}"
            )


def test_poner_sombrero_centra_el_dibujo_cuando_es_el_estrecho():
    """La lección de siempre: manda el eje del dibujo, y si el sombrero es más
    ancho es el dibujo el que se corre, no al revés."""
    assert cos.poner_sombrero(["ooooooo"], "-") == ["   -", "ooooooo"]
    assert cos.poner_sombrero(["o"], "-----") == ["-----", "  o"]


def test_sin_sombrero_no_se_toca_nada():
    lineas = [" oo ", "o  o"]
    assert cos.poner_sombrero(lineas, "") == lineas


# --- Marcos ----------------------------------------------------------------

@pytest.mark.parametrize("marco", cos.del_tipo(cos.MARCO))
def test_cada_marco_cierra_todas_sus_esquinas(marco):
    caja = caja_de(pantalla.render(criatura(marco=marco.clave), T0))
    piezas = dict(zip(cos.PIEZAS, marco.valor))

    assert caja[0] == piezas["sup_izq"] + piezas["horizontal"] * pantalla.ANCHO + piezas["sup_der"]
    assert caja[-1] == piezas["inf_izq"] + piezas["horizontal"] * pantalla.ANCHO + piezas["inf_der"]
    for linea in caja[1:-1]:
        if linea[0] == piezas["med_izq"]:
            assert linea[-1] == piezas["med_der"], repr(linea)
        else:
            assert linea[0] == linea[-1] == piezas["vertical"], repr(linea)


@pytest.mark.parametrize("marco", cos.del_tipo(cos.MARCO))
def test_ningun_marco_cambia_el_ancho_ni_el_alto(marco):
    pelada = caja_de(pantalla.render(criatura(), T0))
    enmarcada = caja_de(pantalla.render(criatura(marco=marco.clave), T0))

    assert len(pelada) == len(enmarcada)
    for linea in enmarcada:
        assert len(linea) == pantalla.ANCHO + 2, repr(linea)


def test_el_marco_no_toca_lo_de_dentro():
    """Cambiar el borde no puede alterar ni una barra ni un número."""
    def tripas(caja):
        return [ln[1:-1] for ln in caja if not ln[0] in "╭├╰╔╠╚┏┣┗┌└"]

    assert tripas(caja_de(pantalla.render(criatura(marco="marco_doble"), T0))) \
        == tripas(caja_de(pantalla.render(criatura(), T0)))


def test_todas_las_piezas_de_un_marco_son_distintas_del_relleno():
    """Un marco cuyo vertical fuera un espacio dejaría la caja abierta."""
    for marco in (cos.REDONDO, *(m.valor for m in cos.del_tipo(cos.MARCO))):
        assert len(marco) == len(cos.PIEZAS), marco
        assert " " not in marco, marco


# --- Títulos ---------------------------------------------------------------

@pytest.mark.parametrize("titulo", cos.del_tipo(cos.TITULO))
def test_todo_titulo_concuerda_en_los_dos_generos(titulo):
    for genero in (esp.MACHO, esp.HEMBRA):
        texto = cos.texto_del_titulo(titulo.clave, genero)
        assert texto, titulo.clave
        # Ninguna marca sin resolver: es el fallo que se cuela sin avisar.
        assert "{" not in texto and "}" not in texto, texto


def test_el_titulo_sale_entre_la_especie_y_el_caracter():
    ficha = pantalla.render(criatura(titulo="titulo_invicto"), T0)
    subtexto = next(ln for ln in ficha.split("\n") if ln.startswith("-# Octopul"))

    partes = subtexto.removeprefix("-# ").split(" · ")
    assert partes[0] == "Octopul"
    assert partes[1] == "el Invicto"


def test_el_titulo_de_una_hembra_va_en_femenino():
    ella = criatura(genero=esp.HEMBRA, titulo="titulo_invicto")
    assert "la Invicta" in pantalla.render(ella, T0)


def test_sin_titulo_el_subtexto_es_el_de_siempre():
    ficha = pantalla.render(criatura(), T0)
    assert "-# Octopul · " in ficha


# --- Todo junto ------------------------------------------------------------

def test_el_tinte_se_ve_tambien_en_el_jardin_y_en_el_ranking():
    """Un tinte que sólo se viera en la ficha se leería como un fallo: al
    gachamon lo dibujan tres sitios."""
    import jardin

    tenida = criatura(tinte="tinte_rojo")
    assert jardin.bloque_de(tenida).color == esp.ROJO
    assert jardin.bloque_de(criatura()).color == esp.ESPECIES["pulpo"].color


def test_los_cuatro_a_la_vez_no_descuadran_nada():
    """Como se van a ver de verdad: quien compre uno acabará comprando los
    cuatro."""
    completa = criatura(
        tinte="tinte_rojo", sombrero="corona",
        marco="marco_doble", titulo="titulo_invicto",
    )
    ficha = pantalla.render(completa, T0)

    for linea in caja_de(ficha):
        assert len(linea) == pantalla.ANCHO + 2, repr(linea)
    assert "el Invicto" in ficha
    assert f"\x1b[0;{esp.ROJO}m" in ficha
    assert "╔" in ficha and "╚" in ficha
    assert "\\_Y_/" in ficha


def test_un_gachamon_sin_cosmeticos_se_ve_exactamente_igual_que_antes():
    """La garantía de que esto no le toca nada a quien no lo use: sin cosméticos
    la ficha pasa por `_repintar_marco` y sale idéntica."""
    pelada = pantalla.render(criatura(), T0)
    caja = caja_de(pelada)

    assert caja[0].startswith("╭") and caja[0].endswith("╮")
    assert caja[-1].startswith("╰") and caja[-1].endswith("╯")
    assert pantalla._repintar_marco(caja, cos.REDONDO) is caja


def test_los_cosmeticos_se_ven_tambien_cuando_esta_hambriento():
    """El dibujo cambia con el ánimo, y el sombrero tiene que seguirlo: son
    tres caras distintas por etapa y el hueco libre podría no ser el mismo."""
    for animo in (100.0, 50.0, 5.0):
        hambrienta = criatura(
            animo=animo, hambre=animo, sombrero="corona", marco="marco_grueso"
        )
        for linea in caja_de(pantalla.render(hambrienta, T0)):
            assert len(linea) == pantalla.ANCHO + 2, f"ánimo {animo}: {linea!r}"
