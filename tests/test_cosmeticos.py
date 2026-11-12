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
import db
import economia
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


# --- Lo retirado -----------------------------------------------------------

def test_los_marcos_y_los_tintes_ya_no_estan_en_el_catalogo():
    assert cos.TIPOS == (cos.SOMBRERO, cos.TITULO)
    assert {c.tipo for c in cos.CATALOGO.values()} == {cos.SOMBRERO, cos.TITULO}
    assert len(cos.CATALOGO) == 12
    assert cos.del_tipo(cos.TINTE) == () and cos.del_tipo(cos.MARCO) == ()


def test_lo_retirado_sabe_cuanto_hay_que_devolver():
    assert cos.TIPOS_RETIRADOS == (cos.TINTE, cos.MARCO)
    assert len(cos.RETIRADOS) == 11
    assert cos.RETIRADOS["tinte_rojo"] == 20
    assert cos.RETIRADOS["marco_doble"] == 50
    assert sorted(set(cos.RETIRADOS.values())) == [20, 50]
    assert not set(cos.RETIRADOS) & set(cos.CATALOGO)


def test_un_gachamon_con_piezas_retiradas_se_pinta_como_si_no_llevara_nada():
    con_retiradas = criatura(tinte="tinte_rojo", marco="marco_doble")
    assert pantalla.render(con_retiradas, T0) == pantalla.render(criatura(), T0)


@pytest.fixture
def bd_temporal(tmp_path, monkeypatch):
    """Una base propia, sólo para la prueba que toca `economia`: el resto de
    este fichero es dibujo puro y no debe crear bases."""
    monkeypatch.setattr(db, "RUTA", tmp_path / "cosmeticos.db")
    db.inicializar()


def test_una_pieza_retirada_no_se_puede_comprar(bd_temporal):
    with db.conectar() as con:
        economia._asegurar_monedero(con, "u", "g")
        con.execute(
            "UPDATE monederos SET asciigems = 50 "
            "WHERE usuario_id = 'u' AND guild_id = 'g'"
        )
    retirada = cos.Cosmetico("tinte_rojo", cos.TINTE, "Rojo", esp.ROJO)

    with pytest.raises(ValueError):
        economia.comprar_cosmetico("u", "g", retirada)

    assert economia.saldos("u", "g").asciigems == 50
    assert db.ropero("u", "g") == frozenset()


# --- El catálogo -----------------------------------------------------------

def test_ningun_cosmetico_esta_a_medias():
    for cosmetico in cos.CATALOGO.values():
        assert cosmetico.clave and cosmetico.nombre.strip(), cosmetico.clave
        assert cosmetico.tipo in cos.TIPOS, cosmetico.clave
        assert cosmetico.valor, cosmetico.clave
        assert cosmetico.precio > 0, cosmetico.clave


def test_ninguna_clave_se_repite_y_hay_de_los_dos_tipos():
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

def test_los_dos_a_la_vez_no_descuadran_nada():
    """Como se van a ver de verdad: quien compre uno acabará comprando los
    dos."""
    completa = criatura(sombrero="corona", titulo="titulo_invicto")
    ficha = pantalla.render(completa, T0)

    for linea in caja_de(ficha):
        assert len(linea) == pantalla.ANCHO + 2, repr(linea)
    assert "el Invicto" in ficha
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
            animo=animo, hambre=animo, sombrero="corona", titulo="titulo_veloz"
        )
        for linea in caja_de(pantalla.render(hambrienta, T0)):
            assert len(linea) == pantalla.ANCHO + 2, f"ánimo {animo}: {linea!r}"
