"""Las especies: equilibrio, rarezas, tirada de nacimiento y las cinco etapas."""
import random
import statistics
import textwrap
from collections import Counter

import especies as esp
import pantalla


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

def test_hay_diez_especies():
    assert len(esp.ESPECIES) == 10


def test_las_no_raras_estan_equilibradas():
    """Comunes y poco comunes reparten los mismos 24 puntos: ninguna es mejor,
    sólo distinta. Si alguien retoca la tabla, esto lo caza."""
    for especie in esp.ESPECIES.values():
        if especie.rareza != esp.RARA:
            assert especie.total_base == 24, especie.clave


def test_la_rara_es_mejor():
    dragon = esp.ESPECIES["dragoncito"]
    assert dragon.rareza == esp.RARA
    assert dragon.total_base == 30


def test_los_pesos_suman_cien():
    assert round(sum(e.peso for e in esp.ESPECIES.values()), 6) == 100.0


def test_distribucion_de_rarezas():
    rng = random.Random(1234)
    cuenta = Counter(esp.elegir_especie(rng).clave for _ in range(20_000))
    for clave, especie in esp.ESPECIES.items():
        observado = cuenta[clave] / 20_000 * 100
        assert abs(observado - especie.peso) < 1.5, (clave, observado, especie.peso)


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


def test_toda_especie_tiene_sus_tres_caras_y_un_nombre_de_evolucion():
    for especie in esp.ESPECIES.values():
        assert set(especie.caras) == set(esp.ANIMOS), especie.clave
        assert especie.evolucion.strip(), especie.clave


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


def test_el_arte_no_lleva_emoji():
    """Discord dibuja los emoji como imágenes de ancho variable incluso dentro
    de un bloque de código: descuadrarían el marco."""
    for nombre, arte in todos_los_dibujos().items():
        for caracter in arte:
            assert ord(caracter) < 0x2500, (nombre, repr(caracter))


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
    """«un Chispa» y «un Chatarra» se leían mal: el artículo concuerda con el
    NOMBRE de la especie, no con el género de la criatura."""
    femeninas = {"chispa", "chatarra"}
    for clave, especie in esp.ESPECIES.items():
        esperado = "una" if clave in femeninas else "un"
        assert especie.articulo == esperado, (clave, especie.articulo)


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
    """Regresión: el Michi cría salía con la cara una columna a la izquierda de
    las orejas y los bigotes, y se le veía torcido en Discord. Había cinco casos
    así repartidos entre Michi, Slime, Dragoncito y Chispa.

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
