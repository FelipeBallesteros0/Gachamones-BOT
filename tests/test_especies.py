"""Las especies: equilibrio, rarezas, tirada de nacimiento y las cinco etapas."""
import random
import re
import statistics
import textwrap
import unicodedata
from collections import Counter
from pathlib import Path

import especies as esp
import pantalla

# Lo que puede aparecer en un dibujo de especie.
#
# Va como lista explícita y no como rangos, y eso es la corrección de un fallo
# que llegó a producción. Con rangos se abrían bloques enteros —miles de puntos
# de código que nadie había visto pintados nunca— y por ahí se colaron once
# caracteres de ancho **ambiguo**: los que valen una celda en fuente occidental
# y dos en fuente asiática. Cuál se aplica depende de a qué fuente caiga el
# cliente cuando su monoespaciada no tiene el glifo, así que las fichas salían
# corridas en Discord y ningún test se enteraba.
#
# El ASCII entra entero porque es lo único probado de verdad: las 25 especies
# estuvieron meses dibujadas sólo con él.
ASCII_IMPRIMIBLE = frozenset(chr(cp) for cp in range(0x20, 0x7F))

PERMITIDOS = ASCII_IMPRIMIBLE | frozenset(
    "¬"      # signo de negación: las orejas caídas de Goot
    "ᐩ"      # silábico canadiense: las garras de Céfiro
    "ᵕ"      # media o baja: bocas dormidas
    "‿"      # undertie: la boca contenta
    "∙⊏⊐⊗"   # operadores: limaduras, pinzas y ojos mareados
    "⌐"      # negación al revés: el pico de Céfiro
    "╷"      # trazo hacia abajo: patas
    "░"      # sombra ligera: escamas y texturas
    "▿◠"     # picos y ojos contentos
    "｡ｰｼﾉﾞ"  # katakana de medio ancho: crestas, alas y patas
)

# Y aparte, los de ancho ambiguo que sí valen. Son los seis del marco de la
# ficha y de los arcos de las casas: llevan meses pintándose bien en Discord, y
# ésa —haberlos visto— es la única garantía que cuenta. Cualquier otro ambiguo
# está prohibido; lo comprueba el test de más abajo.
AMBIGUOS_PROBADOS = frozenset("─│╭╮╯╰")


def lineas(arte: str) -> list[str]:
    return [ln.rstrip() for ln in textwrap.dedent(arte.strip("\n")).split("\n")]


def todos_los_dibujos() -> dict[str, str]:
    dibujos = {
        f"{clave}/{etapa}/{animo}": esp.arte_de(e, etapa, animo)
        for clave, e in esp.ESPECIES.items()
        for etapa in esp.ETAPAS
        for animo in esp.ANIMOS
    }
    dibujos["huevo"] = esp.HUEVO
    dibujos["huevo_rajado"] = esp.HUEVO_RAJADO
    dibujos["lapida"] = esp.LAPIDA
    return dibujos


# --- Equilibrio y rarezas --------------------------------------------------

def test_el_catalogo_esta_completo():
    """Sin el número escrito dentro: al pasar de 10 a 25 este test habría
    obligado a venir a cambiarlo, que es cuando un test deja de comprobar algo
    y pasa a estorbar. Lo que importa es que no haya claves repetidas ni fichas
    a medias."""
    assert len(esp.ESPECIES) >= 10
    for clave, especie in esp.ESPECIES.items():
        assert especie.clave == clave
        assert especie.nombre.strip() and especie.emoji.strip()
        assert especie.descripcion.strip(), clave
        assert especie.rareza in (esp.COMUN, esp.POCO_COMUN, esp.RARA), clave


def test_ninguna_especie_repite_emoji():
    """Con diez se veía a simple vista; con veinticinco, no. Y dos especies con
    el mismo emoji se confunden en la cabecera de la ficha, que es donde más se
    mira."""
    from collections import Counter
    repetidos = [e for e, n in Counter(
        especie.emoji for especie in esp.ESPECIES.values()).items() if n > 1]
    assert not repetidos, repetidos


def test_ninguna_especie_repite_nombre():
    from collections import Counter
    repetidos = [n for n, veces in Counter(
        especie.nombre for especie in esp.ESPECIES.values()).items() if veces > 1]
    assert not repetidos, repetidos


def test_las_no_raras_estan_equilibradas():
    """Comunes y poco comunes reparten los mismos 24 puntos: ninguna es mejor,
    sólo distinta. Si alguien retoca la tabla, esto lo caza."""
    for especie in esp.ESPECIES.values():
        if especie.rareza != esp.RARA:
            assert especie.total_base == 24, especie.clave


def test_las_raras_son_mejores():
    raras = [e for e in esp.ESPECIES.values() if e.rareza == esp.RARA]
    assert raras
    for rara in raras:
        assert rara.total_base == 30, rara.clave


# --- Tirada de nacimiento --------------------------------------------------

def test_2d6_rango_y_media():
    rng = random.Random(7)
    tiradas = [esp.tirar_2d6(rng) for _ in range(20_000)]
    assert min(tiradas) == 2
    assert max(tiradas) == 12
    assert abs(sum(tiradas) / len(tiradas) - 7.0) < 0.1


def test_stats_iniciales_son_base_mas_2d6():
    rng = random.Random(99)
    pollito = esp.ESPECIES["pollito"]
    for _ in range(2_000):
        fue, vel, sal = esp.tirar_stats_iniciales(pollito, rng)
        assert pollito.fuerza + 2 <= fue <= pollito.fuerza + 12
        assert pollito.velocidad + 2 <= vel <= pollito.velocidad + 12
        assert pollito.salud + 2 <= sal <= pollito.salud + 12


def test_cada_stat_se_tira_por_separado():
    """Si las tres compartieran tirada saldrían siempre con el mismo bonus."""
    rng = random.Random(3)
    pulpo = esp.ESPECIES["pulpo"]  # base 8/8/8, así que el bonus se ve directo
    distintas = sum(
        1 for _ in range(500)
        if len(set(esp.tirar_stats_iniciales(pulpo, rng))) > 1
    )
    assert distintas > 400


# --- Las cinco etapas ------------------------------------------------------

def test_toda_especie_tiene_las_cinco_etapas():
    assert len(esp.ETAPAS) == 5
    for especie in esp.ESPECIES.values():
        assert set(especie.arte) == set(esp.ETAPAS), especie.clave


def test_toda_especie_tiene_sus_tres_caras():
    for especie in esp.ESPECIES.values():
        assert set(especie.caras) == set(esp.ANIMOS), especie.clave


def test_las_tres_caras_de_una_especie_miden_lo_mismo():
    """Si midieran distinto, cambiar de ánimo movería el resto de la línea y
    descuadraría el dibujo entero."""
    for especie in esp.ESPECIES.values():
        anchos = {len(c) for c in especie.caras.values()}
        assert len(anchos) == 1, (especie.clave, especie.caras)


def test_no_queda_ningun_hueco_sin_rellenar():
    for nombre, arte in todos_los_dibujos().items():
        assert "{cara}" not in arte, nombre


def test_las_plantillas_llevan_hueco_de_cara():
    """Salvo las excepciones, que son dibujos completos a propósito."""
    for especie in esp.ESPECIES.values():
        for etapa, plantilla in especie.arte.items():
            assert "{cara}" in plantilla, (especie.clave, etapa)


def test_las_excepciones_apuntan_a_etapas_y_animos_reales():
    for especie in esp.ESPECIES.values():
        for (etapa, animo) in especie.excepciones:
            assert etapa in esp.ETAPAS, (especie.clave, etapa)
            assert animo in esp.ANIMOS, (especie.clave, animo)


def test_la_excepcion_gana_a_la_plantilla():
    brote = esp.ESPECIES["brote"]
    assert (esp.NINO, esp.MAL) in brote.excepciones
    assert esp.arte_de(brote, esp.NINO, esp.MAL) == \
        brote.excepciones[(esp.NINO, esp.MAL)]


def test_la_criatura_crece_al_evolucionar():
    """Cada etapa debe verse mayor que la anterior: si no, la evolución no se
    nota y toda la mecánica pierde la gracia."""
    for especie in esp.ESPECIES.values():
        tamanos = []
        for etapa in esp.ETAPAS:
            ls = lineas(esp.arte_de(especie, etapa))
            tamanos.append(max(len(l) for l in ls) * len(ls))
        assert tamanos == sorted(tamanos), (especie.clave, tamanos)
        assert tamanos[-1] > tamanos[0] * 2, (especie.clave, tamanos)


# --- Que quepan y no se rompan ---------------------------------------------

def test_el_arte_cabe_en_el_marco():
    for nombre, arte in todos_los_dibujos().items():
        for linea in lineas(arte):
            assert len(linea) <= pantalla.ANCHO, (nombre, linea)


def test_el_arte_esta_centrado_de_forma_consistente():
    """Regresión: al dibujar las cinco etapas, varias líneas de la cara
    quedaron con distinto ancho que sus vecinas y el bicho salía torcido."""
    for nombre, arte in todos_los_dibujos().items():
        centros = [
            ((len(l) - len(l.lstrip())) + (len(l) - 1)) / 2
            for l in lineas(arte) if l.strip()
        ]
        if len(centros) < 2:
            continue
        medio = statistics.median(centros)
        assert max(abs(c - medio) for c in centros) <= 1.5, (nombre, centros)


def test_el_arte_no_rompe_el_bloque_de_codigo():
    for nombre, arte in todos_los_dibujos().items():
        assert "```" not in arte, nombre


def test_el_arte_solo_usa_caracteres_de_una_columna():
    """La regla de verdad: en el marco cabe lo que mide **una columna**.

    `pantalla` rellena el marco contando caracteres, así que un glifo que se
    pinte más ancho descuadra la ficha y `len()` no se entera.

    Añadir un carácter a `PERMITIDOS` no es gratis: hay que **verlo pintado en
    Discord**, en escritorio y en móvil. Ninguna tabla de Unicode responde a esa
    pregunta, y creer que sí es lo que rompió las fichas.
    """
    permitido = PERMITIDOS | AMBIGUOS_PROBADOS
    for nombre, arte in todos_los_dibujos().items():
        for caracter in arte:
            if caracter == "\n":
                continue
            assert caracter in permitido, (nombre, repr(caracter))


def test_ningun_permitido_es_de_ancho_incierto():
    """Ni ancho ni **ambiguo**, que es la lección que costó un despliegue.

    Un carácter «ambiguo» —`east_asian_width == "A"`— mide una celda en fuente
    occidental y dos en asiática. Cuál se aplica lo decide el cliente al elegir
    la fuente, no nosotros, así que en el arte no puede haber ninguno: la ficha
    saldría bien en un sitio y corrida en otro.

    El guardián de antes sólo prohibía `W` y `F` y dejaba pasar la `A`. Con eso
    se colaron once —`● ω ╥ ˚ ≡ ˘ ≈ ˍ ┬ ▁ ·`— repartidos por las 25 especies.

    Los seis de `AMBIGUOS_PROBADOS` quedan fuera de esta comprobación a
    propósito: son el marco y los arcos de las casas, y su garantía no es una
    tabla sino que llevan meses viéndose bien.
    """
    for caracter in PERMITIDOS:
        assert unicodedata.east_asian_width(caracter) in ("Na", "N", "H"), (
            repr(caracter), unicodedata.name(caracter, "?")
        )


def test_los_ambiguos_probados_salen_ya_en_cada_ficha():
    """La puerta de atrás tiene que seguir siendo pequeña.

    `AMBIGUOS_PROBADOS` es la única lista que se salta la regla, así que lo que
    la protege es que todo lo que hay dentro **ya se pinta** en el marco de cada
    ficha. Eso es lo que quiere decir «probado»: no que una tabla lo diga, sino
    que lleva meses delante de los ojos de quien juega.

    Si alguien mete aquí un carácter que no dibuja `pantalla`, por definición no
    está probado y esto salta.
    """
    fuente = Path(pantalla.__file__).read_text(encoding="utf-8")
    for caracter in AMBIGUOS_PROBADOS:
        assert caracter in fuente, repr(caracter)


def test_cada_etapa_se_ve_distinta():
    for especie in esp.ESPECIES.values():
        dibujos = {esp.arte_de(especie, etapa) for etapa in esp.ETAPAS}
        assert len(dibujos) == len(esp.ETAPAS), especie.clave


def test_cada_animo_se_ve_distinto():
    for especie in esp.ESPECIES.values():
        for etapa in esp.ETAPAS:
            caras = {esp.arte_de(especie, etapa, a) for a in esp.ANIMOS}
            assert len(caras) == len(esp.ANIMOS), (especie.clave, etapa)


def test_toda_etapa_tiene_nombre_en_castellano():
    for etapa in esp.ETAPAS:
        for genero in esp.GENEROS:
            nombre = esp.nombre_etapa(etapa, genero)
            assert nombre.strip()
            assert "{" not in nombre, nombre


def test_toda_especie_lleva_su_articulo():
    """El artículo concuerda con el NOMBRE de la especie, no con el género de la
    criatura: «una Magora macho» es correcto igual que «una jirafa macho».

    Se comprueba la regla y no una lista escrita a mano, para que rebautizar una
    especie no obligue a venir aquí: si el nombre acaba en -a, el artículo es
    «una»; si no, «un». Los nombres inventados que no siguen la regla llevan su
    artículo puesto a mano y se listan como excepción."""
    excepciones = {}  # clave -> artículo, para nombres que engañan al oído
    for clave, especie in esp.ESPECIES.items():
        esperado = excepciones.get(
            clave, "una" if especie.nombre.lower().endswith("a") else "un"
        )
        assert especie.articulo == esperado, (clave, especie.nombre, especie.articulo)


# --- Nada torcido ----------------------------------------------------------

ESPEJO = str.maketrans("/\\()<>[]{}", "\\/)(><][}{")


def es_simetrica(linea: str) -> bool:
    """Si la línea es su propio reflejo, tratando `/` y `\\` como pareja.

    `(o.o)` y `\\\\   //` lo son; una cola como `(  u  )~~` no, porque sobresale
    a un lado a propósito.
    """
    nucleo = linea.strip()
    return bool(nucleo) and nucleo == nucleo.translate(ESPEJO)[::-1]


def test_lo_que_es_simetrico_va_centrado():
    """Regresión: el Purreon cría salía con la cara una columna a la izquierda de
    las orejas y los bigotes, y se le veía torcido en Discord. Había cinco casos
    así repartidos entre Purreon, Gelatín, Tsushimon y Pyro.

    El test de centrado general no los cazaba porque tolera hasta 1,5 de
    desviación, que es justo lo que necesitan las colas y los picos. La
    distinción buena no es cuánto se desvía una línea, sino **si tenía motivo**:
    una línea que es su propio reflejo no lo tiene.
    """
    for clave, especie in esp.ESPECIES.items():
        for etapa in esp.ETAPAS:
            for animo in esp.ANIMOS:
                ls = [l for l in lineas(esp.arte_de(especie, etapa, animo))
                      if l.strip()]
                centros = [((len(l) - len(l.lstrip())) + (len(l) - 1)) / 2
                           for l in ls]
                eje = statistics.median(centros)
                for linea, centro in zip(ls, centros):
                    if es_simetrica(linea):
                        assert abs(centro - eje) < 1.0, (
                            f"{clave}/{etapa}/{animo}: «{linea.strip()}» es "
                            f"simétrica pero está a {centro} y el eje es {eje}"
                        )


def test_el_reflejo_distingue_una_cola_de_un_descuadre():
    """Lo que hace útil al test de arriba: que no señale a las colas."""
    assert es_simetrica("(o.o)")
    assert es_simetrica(r"\\     //")
    assert es_simetrica("<( )>")
    assert not es_simetrica("(  u  )~~")      # cola de gato
    assert not es_simetrica("<(    )>>>")     # cola de pollo


# Adornos que varias especies pueden compartir sin que se confundan: son
# texturas, no rasgos. Una línea de un solo carácter repetido (`_____`, `~~~~~`),
# un adorno radial (`\|/`, `\\\|///`) o una tapa de caja (`.---.`) no dicen qué
# bicho eres; una cabeza sí.
_RAYOS = re.compile(r"^[\\/|]+$")
_CAJA = re.compile(r"^\.-+\.$")


def _es_textura(linea: str) -> bool:
    nucleo = linea.replace(" ", "")
    return (
        len(set(nucleo)) == 1
        or bool(_RAYOS.match(nucleo))
        or bool(_CAJA.match(nucleo))
    )


def _corona(plantilla: str) -> str:
    """La línea justo encima de la cara: la cabeza, lo que identifica al bicho."""
    ls = [l.strip() for l in lineas(plantilla) if l.strip()]
    for i, linea in enumerate(ls):
        if "{cara}" in linea:
            return ls[i - 1] if i else ""
    return ""


def test_ninguna_especie_copia_la_cabeza_de_otra():
    r"""Reportado jugando: el Tsushimon bebé llevaba `/\_/\` encima de la cara
    —la cabeza de gato de ASCII— igual que el Purreon, así que el bicho más raro
    del juego parecía el gato común al salir del huevo.

    No lo cazaba nada: `test_cada_etapa_se_ve_distinta` compara las etapas
    DENTRO de una especie, no entre especies.

    **La regla es un apaño y conviene saberlo.** Se probaron cuatro: la primera
    línea, las dos primeras, cualquier línea compartida y ésta. Las tres
    primeras o dejaban pasar el fallo —la boca ya difería— o señalaban texturas
    legítimas como `~~~~~`. La distinción de verdad es semántica, no de texto,
    así que esto mira **la línea de encima de la cara** y perdona lo que es
    adorno repetido. Si algún día señala algo que no debe, mira `_es_textura`
    antes de tocar el dibujo.
    """
    coronas: dict[str, set[str]] = {}
    for clave, especie in esp.ESPECIES.items():
        for etapa in esp.ETAPAS:
            corona = _corona(especie.arte[etapa])
            if corona and not _es_textura(corona):
                coronas.setdefault(corona, set()).add(clave)

    repetidas = {c: sorted(quienes) for c, quienes in coronas.items()
                 if len(quienes) > 1}
    assert not repetidas, repetidas


# --- Del huevo salen sólo las diez de siempre -------------------------------

def test_del_huevo_solo_salen_las_originales():
    """Lo pedido: el huevo de partida da una de las diez de siempre, y las
    quince nuevas hay que encontrárselas por ahí. Así el huevo sigue siendo el
    comienzo conocido y el catálogo grande es lo que se descubre jugando."""
    rng = random.Random(20260801)
    salidas = {esp.elegir_del_huevo(rng).clave for _ in range(20_000)}

    assert salidas == set(esp.DEL_HUEVO)
    assert len(salidas) == 10


def test_las_nuevas_no_salen_del_huevo_pero_viven_en_algun_bioma():
    """La otra mitad de la regla: si no salieran del huevo NI de un bioma, no
    habría forma de conseguirlas."""
    import aventura as av

    en_biomas = {e for bioma in av.BIOMAS.values() for e in bioma.especies}
    for clave, especie in esp.ESPECIES.items():
        if clave in esp.DEL_HUEVO:
            continue
        assert especie.peso == 0, (clave, "no sale del huevo: su peso sobra")
        assert clave in en_biomas, (clave, "no se consigue de ninguna forma")


def test_el_peso_es_la_probabilidad_en_el_huevo():
    """El peso sólo lo usa el huevo: `tirar_salvaje` elige uniforme dentro del
    bioma y no lo mira. Por eso las que no salen del huevo lo llevan a 0, en vez
    de arrastrar un número que no significa nada."""
    del_huevo = [esp.ESPECIES[c] for c in esp.DEL_HUEVO]
    assert round(sum(e.peso for e in del_huevo), 6) == 100.0

    rng = random.Random(1234)
    cuenta = Counter(esp.elegir_del_huevo(rng).clave for _ in range(20_000))
    for clave in esp.DEL_HUEVO:
        observado = cuenta[clave] / 20_000 * 100
        assert abs(observado - esp.ESPECIES[clave].peso) < 1.5, (clave, observado)
