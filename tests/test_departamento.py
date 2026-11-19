"""El departamento por casillas: catálogo, huellas, choques y cuentas."""
from dataclasses import replace

import pytest

import departamento as dep
import simulacion as sim

P = dep.Pieza

# (clave, ancho, fondo, capa); en lo de pared, `ancho` son los tramos.
FORMAS = [
    ("felpudo", 1, 1, dep.SUELO),
    ("maceta", 1, 1, dep.BULTO),
    ("cuadro", 1, 1, dep.PARED),
    ("estanteria", 2, 1, dep.BULTO),
    ("lampara", 1, 1, dep.BULTO),
    ("alfombra", 2, 2, dep.SUELO),
    ("cortinas", 2, 1, dep.PARED),
    ("cojines", 1, 1, dep.BULTO),
    ("fuente", 2, 2, dep.BULTO),
    ("chimenea", 2, 1, dep.BULTO),
    ("calefactor", 1, 1, dep.BULTO),
    ("cama", 2, 1, dep.BULTO),
    ("ventanal", 2, 1, dep.PARED),
    ("biblioteca", 2, 1, dep.BULTO),
    ("cama_sencilla", 2, 1, dep.BULTO),
    ("refrigerador", 1, 1, dep.BULTO),
    ("consola", 1, 1, dep.BULTO),
    ("ducha", 1, 1, dep.BULTO),
    ("pesas", 1, 1, dep.BULTO),
    ("puerta", 1, 1, dep.PARED),
]


def depto(*piezas, ancho=3, fondo=3):
    return dep.Departamento(ancho, fondo, tuple(piezas))


# Los catorce de las casas de antes, como eran: (clave, nombre, emoji, precio, comodidad).
LOS_CATORCE = [
    ("felpudo", "Felpudo", "🚪", 30, 2),
    ("maceta", "Maceta", "🪴", 50, 3),
    ("cuadro", "Cuadro", "🖼️", 50, 3),
    ("estanteria", "Estantería", "🗄️", 80, 4),
    ("lampara", "Lámpara", "💡", 80, 4),
    ("alfombra", "Alfombra", "🧶", 120, 5),
    ("cortinas", "Cortinas", "🪟", 120, 5),
    ("cojines", "Cojines", "🛋️", 180, 6),
    ("fuente", "Fuente", "⛲", 180, 6),
    ("chimenea", "Chimenea", "🔥", 180, 6),
    ("calefactor", "Calefactor", "🌡️", 280, 7),
    ("cama", "Cama grande", "🛏️", 280, 7),
    ("ventanal", "Ventanal", "🏞️", 280, 7),
    ("biblioteca", "Biblioteca", "📚", 280, 7),
]


# Los cuatro que cuidan solos a todos los gachamones del departamento: (clave, nombre, emoji, uso).
LOS_QUE_SE_USAN_SOLOS = [
    ("refrigerador", "Refrigerador", "🧊", dep.COMIDA),
    ("consola", "Consola", "🎮", dep.ANIMO),
    ("ducha", "Ducha", "🚿", dep.ASEO),
    ("pesas", "Pesas", "🏋️", dep.FUERZA),
]


def test_el_catalogo_son_los_catorce_de_siempre_la_cama_sencilla_los_cuatro_que_se_usan_solos_y_la_puerta():
    assert set(dep.MUEBLES) == (
        {fila[0] for fila in LOS_CATORCE} | {"cama_sencilla", "puerta"} | {fila[0] for fila in LOS_QUE_SE_USAN_SOLOS})
    for clave, nombre, emoji, precio, comodidad in LOS_CATORCE:
        nuevo = dep.MUEBLES[clave]
        assert (nuevo.nombre, nuevo.emoji, nuevo.precio, nuevo.comodidad) == (nombre, emoji, precio, comodidad), clave
    sencilla = dep.MUEBLES["cama_sencilla"]
    assert (sencilla.nombre, sencilla.precio, sencilla.comodidad) == ("Cama sencilla", 85, 2)
    assert {c for c, m in dep.MUEBLES.items() if m.cama} == {"cama", "cama_sencilla"}

def test_los_cuatro_que_se_usan_solos_cuestan_300_suman_3_y_dicen_su_uso():
    assert (dep.COMIDA, dep.ANIMO, dep.ASEO, dep.FUERZA) == ("comida", "animo", "aseo", "fuerza")
    for clave, nombre, emoji, uso in LOS_QUE_SE_USAN_SOLOS:
        m = dep.MUEBLES[clave]
        assert (m.nombre, m.emoji, m.precio, m.comodidad, m.uso) == (nombre, emoji, 300, 3, uso), clave
        assert not m.cama and not m.puerta, clave
    assert {c for c, m in dep.MUEBLES.items() if m.uso is not None} == {fila[0] for fila in LOS_QUE_SE_USAN_SOLOS}

def test_en_la_tienda_los_cuatro_van_tras_la_cama_sencilla():
    assert [m.clave for m in dep.a_la_venta()][-5:] == ["cama_sencilla", "refrigerador", "consola", "ducha", "pesas"]

@pytest.mark.parametrize("clave, ancho, fondo, capa", FORMAS)   # la tabla de arriba, las veinte filas
def test_cada_mueble_ocupa_lo_que_dice_el_diseno(clave, ancho, fondo, capa):
    m = dep.MUEBLES[clave]
    assert (m.ancho, m.fondo, m.capa) == (ancho, fondo, capa)

def test_un_mueble_alargado_cambia_de_casillas_al_girar():
    cama = dep.MUEBLES["cama_sencilla"]
    assert dep.huella(cama, 1, 1, 0) == {(1, 1), (2, 1)} == dep.huella(cama, 1, 1, 2)
    assert dep.huella(cama, 1, 1, 1) == {(1, 1), (1, 2)} == dep.huella(cama, 1, 1, 3)
    assert len(dep.huella(dep.MUEBLES["fuente"], 0, 0, 1)) == 4

def test_lo_de_pared_ocupa_tramos_de_una_de_las_dos_paredes():
    cortinas = dep.MUEBLES["cortinas"]
    assert dep.huella(cortinas, 1, -1, 0) == {(1, -1), (2, -1)}
    assert dep.huella(cortinas, -1, 0, 3) == {(-1, 0), (-1, 1)}

def test_cabe_dentro_y_no_se_sale():
    d = depto(P(1, "cama_sencilla"))
    assert dep.problema_al_poner(d, 1, 1, 0, 0) is None
    assert dep.problema_al_poner(d, 1, 2, 0, 0) == dep.NO_CABE      # se sale por una casilla
    assert dep.problema_al_poner(d, 1, 2, 0, 1) is None             # girada, sí
    assert dep.problema_al_poner(d, 1, 0, 2, 1) == dep.NO_CABE
    assert dep.problema_al_poner(d, 1, 0, -1, 0) == dep.NO_CABE     # un mueble de suelo no va en la pared

def test_dos_bultos_no_comparten_casilla_pero_uno_va_sobre_la_alfombra():
    d = depto(P(1, "alfombra", 0, 0), P(2, "maceta"), P(3, "felpudo"), P(4, "lampara", 2, 2))
    assert dep.problema_al_poner(d, 2, 1, 1, 0) is None             # encima de la alfombra
    assert dep.problema_al_poner(d, 3, 1, 1, 0) == dep.OCUPADO      # dos cosas que se pisan, no
    assert dep.problema_al_poner(d, 3, 2, 2, 0) is None             # el felpudo bajo la lámpara
    assert dep.problema_al_poner(d, 2, 2, 2, 0) == dep.OCUPADO      # donde está la lámpara

def test_moverse_o_girar_en_su_sitio_no_choca_consigo_mismo():
    d = depto(P(1, "cama_sencilla", 0, 0, 0))
    assert dep.problema_al_poner(d, 1, 0, 0, 1) is None
    assert dep.problema_al_poner(d, 1, 1, 0, 0) is None

def test_la_pared_tiene_sus_tramos():
    d = depto(P(1, "cortinas"), P(2, "cuadro", 0, -1), P(3, "ventanal"))
    assert dep.problema_al_poner(d, 1, 1, -1, 0) is None
    assert dep.problema_al_poner(d, 1, 0, -1, 0) == dep.OCUPADO     # el cuadro está en el tramo 0
    assert dep.problema_al_poner(d, 1, 2, -1, 0) == dep.NO_CABE     # se sale del muro
    assert dep.problema_al_poner(d, 3, -1, 1, 0) is None            # la otra pared
    assert dep.problema_al_poner(d, 1, 1, 1, 0) == dep.NO_CABE      # lo de pared no va en el suelo
    assert dep.problema_al_poner(d, 2, -1, -1, 0) == dep.NO_CABE    # la esquina no es de nadie

def test_dos_tramos_no_se_salen_por_el_fondo_ni_por_la_esquina():
    d = depto(P(1, "cortinas"))
    assert dep.problema_al_poner(d, 1, -1, d.fondo - 2, 0) is None  # los dos últimos tramos de la columna
    assert dep.problema_al_poner(d, 1, -1, d.fondo - 1, 0) == dep.NO_CABE
    assert dep.problema_al_poner(d, 1, -1, -1, 0) == dep.NO_CABE

@pytest.mark.parametrize("giro", [1, 2, 3])
def test_lo_de_pared_en_la_columna_ocupa_lo_mismo_con_cualquier_giro(giro):
    ventanal = dep.MUEBLES["ventanal"]
    assert dep.huella(ventanal, -1, 0, giro) == dep.huella(ventanal, -1, 0, 0) == {(-1, 0), (-1, 1)}
    d = depto(P(1, "ventanal"), P(2, "cuadro", -1, 1))
    assert dep.problema_al_poner(d, 1, -1, 0, giro) == dep.OCUPADO   # el cuadro está en su segundo tramo

def test_lo_que_no_es_tuyo_o_ya_no_existe_no_se_pone():
    assert dep.problema_al_poner(depto(), 9, 0, 0, 0) == dep.NO_ES_TUYO
    assert dep.problema_al_poner(depto(P(1, "ya_no_existe")), 1, 0, 0, 0) == dep.NO_ES_TUYO

def test_una_pieza_puesta_que_ya_no_esta_en_el_catalogo_no_estorba():
    d = depto(P(1, "ya_no_existe", 0, 0), P(2, "maceta"))
    assert dep.problema_al_poner(d, 2, 0, 0, 0) is None

def test_las_camas_puestas_son_las_que_cuentan():
    d = depto(P(1, "cama_sencilla", 0, 0), P(2, "cama", 0, 1), P(3, "cama_sencilla"))
    assert d.camas_puestas == 2
    assert dep.cama_libre(d, vivos=0) and not dep.cama_libre(d, vivos=1)

def test_no_se_guarda_la_cama_que_deja_a_alguien_sin_la_suya():
    d = depto(P(1, "cama_sencilla", 0, 0), P(2, "cama_sencilla", 0, 1), P(3, "cama_sencilla", 0, 2), P(4, "maceta", 2, 0))
    assert dep.puede_guardarse(d, 1, vivos=1)                       # sobra una
    assert not dep.puede_guardarse(d, 1, vivos=2)
    assert dep.puede_guardarse(d, 4, vivos=2)                       # una maceta, siempre
    assert not dep.puede_guardarse(depto(P(1, "cama_sencilla", 0, 0)), 1, vivos=0)   # la tuya no

def test_puede_guardarse_no_mira_de_quien_es_ni_lo_ya_guardado():
    d = depto(P(1, "cama_sencilla", 0, 0), P(2, "cama_sencilla"))
    assert dep.puede_guardarse(d, 9, vivos=0)                       # no existe: lo mira antes quien llama
    assert dep.puede_guardarse(d, 2, vivos=0)                       # una cama guardada no deja a nadie sin la suya

def test_la_comodidad_parte_de_80_y_cada_tipo_suma_una_vez():
    assert depto().comodidad == 80
    assert depto(P(1, "felpudo", 0, 0), P(2, "felpudo", 1, 0), P(3, "maceta", 2, 0), P(4, "cuadro"), P(5, "ya_no_existe", 2, 2)).comodidad == 85

def test_el_tope_depende_de_las_casillas():
    assert [dep.tope_de_comodidad(n) for n in (9, 12, 16, 64)] == [100, 102, 106, 150]
    todo = tuple(P(i, clave, 0, 0) for i, clave in enumerate(dep.MUEBLES, 1))   # la cuenta no mira choques
    assert dep.Departamento(3, 3, todo).comodidad == 100
    assert dep.Departamento(8, 8, todo).comodidad == 150

def test_la_comodidad_alivia_el_animo_como_siempre():
    assert dep.alivio_de_animo(75) == 1.0 and dep.alivio_de_animo(150) == 0.75 == dep.alivio_de_animo(200)
    for comodidad, alivio in ((75, 1.0), (80, 59 / 60), (100, 11 / 12), (125, 5 / 6), (150, 0.75)):
        assert dep.alivio_de_animo(comodidad) == pytest.approx(alivio)
    assert dep.ritmo_de(depto()) == sim.Ritmo(animo=dep.alivio_de_animo(80))

def _alivio(d):
    return dep.alivio_de_animo(d.comodidad)

def test_el_ritmo_lleva_el_minimo_de_cada_mueble_puesto():
    con_refrigerador = depto(P(1, "refrigerador", 0, 0))
    assert dep.ritmo_de(con_refrigerador) == sim.Ritmo(animo=_alivio(con_refrigerador), suelo_de_hambre=40.0)
    guardado = depto(P(1, "refrigerador"))
    assert dep.ritmo_de(guardado) == sim.Ritmo(animo=_alivio(guardado))           # guardado no cuenta
    dos = depto(P(1, "refrigerador", 0, 0), P(2, "refrigerador", 1, 0))
    assert dep.ritmo_de(dos) == dep.ritmo_de(con_refrigerador)                     # dos no hacen más
    cuatro = depto(P(1, "refrigerador", 0, 0), P(2, "consola", 1, 0), P(3, "ducha", 2, 0), P(4, "pesas", 0, 1))
    assert dep.ritmo_de(cuatro) == sim.Ritmo(
        animo=_alivio(cuatro), suelo_de_hambre=40.0, suelo_de_animo=40.0, suelo_de_limpieza=40.0, fuerza_por_dia=1)
    sin = depto(P(1, "maceta", 0, 0), P(2, "cama_sencilla", 1, 1), P(3, "ya_no_existe", 2, 2), P(4, "pesas"))
    assert dep.ritmo_de(sin) == sim.Ritmo(animo=_alivio(sin))                      # exactamente el de hoy

@pytest.mark.parametrize("clave, lo_que_pone", [
    ("refrigerador", {"suelo_de_hambre": 40.0}), ("consola", {"suelo_de_animo": 40.0}),
    ("ducha", {"suelo_de_limpieza": 40.0}), ("pesas", {"fuerza_por_dia": 1}),
])
def test_cada_uno_sostiene_lo_suyo_y_nada_mas(clave, lo_que_pone):
    d = depto(P(1, clave, 2, 2))
    assert dep.ritmo_de(d) == sim.Ritmo(animo=_alivio(d), **lo_que_pone)

def test_ampliar_cuesta_15_por_casilla_y_para_en_8():
    assert dep.coste_de_ampliar(depto(), dep.ANCHO) == 45 == dep.coste_de_ampliar(depto(), dep.FONDO)
    assert dep.coste_de_ampliar(dep.Departamento(4, 3), dep.FONDO) == 60
    assert dep.coste_de_ampliar(dep.Departamento(8, 3), dep.ANCHO) is None
    assert dep.coste_de_ampliar(dep.Departamento(3, 8), dep.FONDO) is None

@pytest.mark.parametrize("eje", ["alto", "", None, "ANCHO"])
def test_ampliar_por_un_lado_que_no_existe_es_un_error(eje):
    with pytest.raises(ValueError):
        dep.coste_de_ampliar(depto(), eje)

def test_de_3x3_a_8x8_son_825_monedas():
    d, total = dep.Departamento(), 0
    while (eje := dep.ANCHO if d.ancho <= d.fondo else dep.FONDO) and dep.coste_de_ampliar(d, eje):
        total += dep.coste_de_ampliar(d, eje)
        d = dep.Departamento(d.ancho + (eje == dep.ANCHO), d.fondo + (eje == dep.FONDO))
    assert (d.ancho, d.fondo, total) == (8, 8, 825)

def test_el_alcalde_da_el_primer_tamano_de_la_serie_en_que_caben():
    assert [dep.tamano_para(c) for c in (1, 2, 3, 4, 6, 26, 40)] == [(3, 3), (3, 3), (4, 3), (4, 4), (5, 4), (8, 8), (8, 8)]

@pytest.mark.parametrize("camas", range(0, 33))   # hasta las 32 que caben en 8 × 8
def test_las_camas_del_alcalde_caben_todas_y_no_se_pisan(camas):
    ancho, fondo = dep.tamano_para(camas)
    d = dep.Departamento(ancho, fondo, tuple(P(i, "cama_sencilla") for i in range(camas)))
    sitios = dep.acomodar_camas(ancho, fondo, camas)
    assert len(sitios) == camas
    for i, (x, y, giro) in enumerate(sitios):
        assert dep.problema_al_poner(d, i, x, y, giro) is None
        d = dep.Departamento(ancho, fondo, tuple(replace(p, x=x, y=y, giro=giro) if p.id == i else p for p in d.piezas))
    assert d.camas_puestas == camas

def test_en_8x8_no_caben_33_camas():
    with pytest.raises(ValueError):
        dep.acomodar_camas(8, 8, 33)

def test_el_departamento_de_partida_trae_tu_cama_puesta_y_otra_guardada():
    d = dep.DE_PARTIDA
    assert (d.ancho, d.fondo) == (3, 3)
    assert [(p.clave, p.puesta) for p in d.piezas] == [
        ("cama_sencilla", True), ("cama_sencilla", False), ("puerta", True)]   # y su puerta, puesta
    assert d.camas_puestas == 1 and d.comodidad == 82


# --- La puerta ------------------------------------------------------------------

def test_la_puerta_es_un_mueble_de_pared_de_un_tramo_que_no_suma():
    puerta = dep.MUEBLES[dep.PUERTA]
    assert (puerta.nombre, puerta.capa, puerta.ancho, puerta.comodidad, puerta.puerta) == ("Puerta", dep.PARED, 1, 0, True)
    assert [m.clave for m in dep.MUEBLES.values() if m.puerta] == ["puerta"]

def test_el_departamento_de_partida_trae_su_puerta_con_la_entrada_libre():
    puertas = [p for p in dep.DE_PARTIDA.puestas if p.clave == dep.PUERTA]
    assert [(p.x, p.y) for p in puertas] == [(-1, 2)]
    assert dep.frente_a(-1, 2) == (0, 2) and dep.frente_a(1, -1) == (1, 0)
    assert dep.DE_PARTIDA.comodidad == 82                       # como antes: la puerta no suma

def test_la_puerta_choca_con_lo_colgado_y_se_mueve_a_un_tramo_libre():
    d = depto(P(1, "puerta", -1, 2), P(2, "cuadro", -1, 0), P(3, "cortinas"))
    assert dep.problema_al_poner(d, 1, -1, 0, 0) == dep.OCUPADO  # ahí está el cuadro
    assert dep.problema_al_poner(d, 1, 2, -1, 0) is None         # a la pared derecha
    assert dep.problema_al_poner(d, 3, -1, 1, 0) == dep.OCUPADO  # las cortinas pisarían la puerta
    assert dep.problema_al_poner(d, 1, 1, 1, 0) == dep.NO_CABE   # la puerta no va en el suelo

def test_el_alcalde_busca_un_tramo_con_la_entrada_libre():
    assert dep.tramo_para_la_puerta(depto()) == (-1, 2)
    tapada = depto(P(1, "maceta", 0, 2))
    assert dep.tramo_para_la_puerta(tapada) == (-1, 1)
    con_cuadro = depto(P(1, "maceta", 0, 2), P(2, "cuadro", -1, 1))
    assert dep.tramo_para_la_puerta(con_cuadro) == (-1, 0)
    columna = depto(P(1, "maceta", 0, 0), P(2, "maceta", 0, 1), P(3, "maceta", 0, 2))
    assert dep.tramo_para_la_puerta(columna) == (2, -1)          # la pared derecha, de adelante hacia atrás
    todo = depto(*(P(n, "maceta", n % 3, n // 3) for n in range(9)))
    assert dep.tramo_para_la_puerta(todo) == (-1, 2)             # ninguna libre: el primero sin nada colgado
    assert dep.tramo_para_la_puerta(depto(P(1, "felpudo", 0, 2))) == (-1, 2)   # lo que se pisa no tapa


def test_sin_tramo_libre_para_la_puerta_el_alcalde_lo_dice_con_un_error_claro():
    colgado = depto(*(P(n + 1, "cuadro", x, y) for n, (x, y) in enumerate(
        [(-1, 0), (-1, 1), (-1, 2), (0, -1), (1, -1), (2, -1)])))
    with pytest.raises(ValueError, match="no hay tramo libre para la puerta"):
        dep.tramo_para_la_puerta(colgado)


def bajo_las_camas(sitios):
    """Las casillas que tapan esas camas sencillas, como las deja el alcalde: (x, y, giro)."""
    return [c for x, y, giro in sitios for c in dep.huella(dep.MUEBLES["cama_sencilla"], x, y, giro)]

def lo_de_hoy(ancho, fondo, camas):
    """Las camas donde dice `acomodar_camas` y la puerta donde dice `tramo_para_la_puerta` con ellas."""
    sitios = dep.acomodar_camas(ancho, fondo, camas)
    con_camas = depto(*(P(n, "cama_sencilla", x, y, giro) for n, (x, y, giro) in enumerate(sitios)), ancho=ancho, fondo=fondo)
    return sitios, dep.tramo_para_la_puerta(con_camas)

@pytest.mark.parametrize("vivos", range(0, 26))   # el tope de gachamones de antes era 25
def test_el_alcalde_deja_todas_las_camas_y_la_entrada_libre(vivos):
    camas = vivos + 1
    ancho, fondo = dep.tamano_para(camas)
    sitios, puerta = dep.acomodo_del_alcalde(ancho, fondo, camas)
    assert len(sitios) == camas
    tapadas = bajo_las_camas(sitios)
    assert all(0 <= x < ancho and 0 <= y < fondo for x, y in tapadas)          # dentro de la pieza
    assert len(tapadas) == len(set(tapadas))                                  # y sin pisarse
    assert dep.frente_a(*puerta) not in tapadas

@pytest.mark.parametrize("vivos", [v for v in range(0, 26) if v not in (21, 24)])
def test_donde_la_entrada_ya_quedaba_libre_el_alcalde_no_cambia_nada(vivos):
    camas = vivos + 1
    ancho, fondo = dep.tamano_para(camas)
    assert dep.acomodo_del_alcalde(ancho, fondo, camas) == lo_de_hoy(ancho, fondo, camas)

def test_con_21_vivos_la_cama_que_tapa_la_entrada_pasa_al_ultimo_sitio_que_sobra():
    assert dep.tamano_para(22) == (7, 7)
    sitios, puerta = lo_de_hoy(7, 7, 22)
    assert puerta == (-1, 6) and (0, 6, 0) in sitios                         # hoy, la cama de (0, 6) la tapa
    assert dep.acomodo_del_alcalde(7, 7, 22) == (
        tuple((6, 4, 1) if s == (0, 6, 0) else s for s in sitios), (-1, 6))

def test_con_24_vivos_la_cama_que_tapa_la_entrada_pasa_al_ultimo_sitio_que_sobra():
    assert dep.tamano_para(25) == (8, 7)
    sitios, puerta = lo_de_hoy(8, 7, 25)
    assert puerta == (-1, 6) and (0, 6, 0) in sitios
    assert dep.acomodo_del_alcalde(8, 7, 25) == (
        tuple((6, 6, 0) if s == (0, 6, 0) else s for s in sitios), (-1, 6))

@pytest.mark.parametrize("vivos", range(26, 32))   # por encima del tope de antes: no puede pasar, y no lanza
def test_por_encima_del_tope_de_antes_el_alcalde_tampoco_lanza(vivos):
    camas = vivos + 1
    ancho, fondo = dep.tamano_para(camas)
    sitios, _ = dep.acomodo_del_alcalde(ancho, fondo, camas)
    assert len(sitios) == camas

def test_en_un_8x8_lleno_de_camas_no_sobra_sitio_y_la_entrada_queda_tapada():
    assert dep.tamano_para(32) == (8, 8)
    sitios, puerta = dep.acomodo_del_alcalde(8, 8, 32)
    assert (sitios, puerta) == lo_de_hoy(8, 8, 32)
    assert dep.frente_a(*puerta) in bajo_las_camas(sitios)


def test_a_la_venta_son_los_muebles_del_catalogo_menos_la_puerta_en_su_orden():
    venta = dep.a_la_venta()
    assert isinstance(venta, tuple) and dep.MUEBLES[dep.PUERTA] not in venta
    assert [m.clave for m in venta] == [c for c in dep.MUEBLES if c != dep.PUERTA]
