"""Lo subido por el dibujante en la base: el historial que sólo crece, la vigente de cada pieza,
cómo se vuelve hacia atrás y la poda.

Las pruebas de punta a punta pasan por `arte_subido.subir` y `arte_subido.volver`, que es por
donde pasa quien recibe una subida. Los PNG se fabrican aquí.

`T0` va en el pasado a propósito: la poda compara la hora de los archivos (la del reloj de
verdad) con la que se le pasa, y así nada de lo escrito en estas pruebas parece un huérfano
viejo.
"""
import hashlib
import io
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image

import arte_subido
import db

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
CORAZON = "efectos/corazon.png"
ESTRELLA = "efectos/estrella.png"
SUELO = "pieza/suelo.png"


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "arte.db")
    db.inicializar(T0)


@pytest.fixture
def carpeta(tmp_path):
    return tmp_path / "arte_subido"


def falso(n: int) -> str:
    """Un nombre de archivo con la forma de los de verdad, para lo que no toca el disco."""
    return hashlib.sha256(f"imagen {n}".encode()).hexdigest() + ".png"


A, B, C, D, E, F, G = (falso(n) for n in range(7))
V1, V2, V3, V4 = A, B, C, D


def todo_en_disco(_archivo):
    return True


def filas():
    with db.conectar() as con:
        return [tuple(f) for f in con.execute(
            "SELECT ruta, accion, archivo, ancho, alto, quien, cuando FROM arte_subido ORDER BY id")]


def subir(ruta, archivo, quien="ana", ahora=T0, medida=(32, 32)):
    db.subir_arte(ruta, archivo, *medida, quien, ahora)


def anterior(ruta=CORAZON, quien="felipe", ahora=T0, en_disco=todo_en_disco):
    return db.volver_a_la_anterior(ruta, quien, ahora, en_disco)


def vigente(ruta=CORAZON):
    return db.arte_vigente(arte_subido.medidas()).get(ruta, (None,))[0]


def png(color, ancho=32, alto=32) -> bytes:
    salida = io.BytesIO()
    Image.new("RGBA", (ancho, alto), color).save(salida, "PNG")
    return salida.getvalue()


def subir_por_ruta(carpeta, ruta, cuerpo, quien="ana", ahora=T0) -> str:
    """Lo que hace quien recibe una subida: buscar la pieza y subir."""
    pieza = arte_subido.pieza_de(ruta)
    if pieza is None:
        raise LookupError(ruta)
    return arte_subido.subir(carpeta, pieza, cuerpo, quien, ahora)


def en_carpeta(carpeta):
    return sorted(p.name for p in carpeta.iterdir()) if carpeta.exists() else []


# --- El historial ---------------------------------------------------------------

def test_sin_nada_subido_todo_es_provisional():
    assert db.arte_vigente(arte_subido.medidas()) == {}
    assert db.historial_del_arte(CORAZON) == []
    assert db.archivos_que_se_conservan() == set()


def test_subir_deja_su_renglon_con_el_nombre_de_quien_sube_y_pasa_a_ser_la_vigente():
    subir(CORAZON, A, "ana", T0)
    subir(CORAZON, B, "felipe", T0 + timedelta(minutes=1))
    assert filas() == [
        (CORAZON, "subir", A, 32, 32, "ana", T0.isoformat()),
        (CORAZON, "subir", B, 32, 32, "felipe", (T0 + timedelta(minutes=1)).isoformat()),
    ]
    assert db.arte_vigente(arte_subido.medidas()) == {CORAZON: (B, 32, 32)}
    historial = db.historial_del_arte(CORAZON)
    assert [(r.accion, r.archivo, r.ancho, r.alto, r.quien, r.cuando) for r in historial] == [
        ("subir", B, 32, 32, "felipe", T0 + timedelta(minutes=1)),
        ("subir", A, 32, 32, "ana", T0),
    ]


def test_el_historial_es_de_cada_pieza():
    subir(CORAZON, A)
    subir(ESTRELLA, B)
    assert [r.archivo for r in db.historial_del_arte(CORAZON)] == [A]
    assert db.arte_vigente(arte_subido.medidas()) == {CORAZON: (A, 32, 32), ESTRELLA: (B, 32, 32)}


# --- Volver hacia atrás -------------------------------------------------------------

def test_volver_a_la_anterior_retrocede_por_las_subidas_hasta_el_provisional():
    for archivo in (V1, V2, V3):
        subir(CORAZON, archivo, "ana")
    despues = T0 + timedelta(hours=1)
    assert anterior(quien="felipe", ahora=despues) == V2
    assert filas()[-1] == (CORAZON, "anterior", V2, 32, 32, "felipe", despues.isoformat())
    assert vigente() == V2
    assert anterior() == V1
    assert vigente() == V1
    assert anterior() is None
    assert filas()[-1] == (CORAZON, "provisional", None, None, None, "felipe", T0.isoformat())
    assert vigente() is None
    assert [f[1] for f in filas()] == ["subir"] * 3 + ["anterior", "anterior", "provisional"]


def test_una_subida_nueva_va_al_final_de_la_secuencia():
    for archivo in (V1, V2, V3):
        subir(CORAZON, archivo)
    assert anterior() == V2
    assert anterior() == V1
    subir(CORAZON, V4)
    assert vigente() == V4
    assert anterior() == V3
    assert anterior() == V2


def test_desde_el_provisional_volver_a_la_anterior_vuelve_a_la_ultima_subida():
    """Un toque de más en «Volver al provisional» se deshace con otro (el dueño, 2026-11-20)."""
    subir(CORAZON, V1)
    subir(CORAZON, V2)
    db.volver_al_provisional(CORAZON, "felipe", T0)
    assert anterior(quien="ana") == V2
    assert filas()[-1] == (CORAZON, "anterior", V2, 32, 32, "ana", T0.isoformat())
    assert vigente() == V2
    # Y desde ahí sigue retrocediendo por las subidas, como siempre.
    assert anterior() == V1
    assert anterior() is None
    assert anterior() == V2


def test_desde_el_provisional_se_salta_la_ultima_si_ya_no_esta_en_disco():
    subir(CORAZON, V1)
    subir(CORAZON, V2)
    db.volver_al_provisional(CORAZON, "felipe", T0)
    assert anterior(en_disco=lambda archivo: archivo != V2) == V1


def test_desde_el_provisional_sin_nada_en_disco_no_hay_anterior():
    subir(CORAZON, V1)
    db.volver_al_provisional(CORAZON, "felipe", T0)
    antes = filas()
    with pytest.raises(db.NoHayAnterior):
        anterior(en_disco=lambda _archivo: False)
    assert filas() == antes and vigente() is None


def test_sin_historial_tampoco_hay_anterior():
    with pytest.raises(db.NoHayAnterior):
        anterior()
    assert filas() == []


def test_volver_a_la_anterior_salta_lo_que_ya_no_esta_guardado_ni_en_disco():
    subidas = [falso(10 + n) for n in range(7)]
    for archivo in subidas:
        subir(CORAZON, archivo)
    # Se guardan las cinco últimas: de la séptima a la tercera. La quinta falta en disco.
    falta = subidas[4]
    en_disco = lambda archivo: archivo != falta  # noqa: E731
    recorridas = [anterior(en_disco=en_disco) for _ in range(4)]
    assert recorridas == [subidas[5], subidas[3], subidas[2], None]


def test_volver_a_la_anterior_salta_la_misma_imagen_subida_dos_veces_seguidas():
    subir(CORAZON, V1)
    subir(CORAZON, V2)
    subir(CORAZON, V2)
    assert anterior() == V1
    assert anterior() is None


def test_volver_al_provisional_deja_su_renglon_y_la_pieza_sin_imagen():
    subir(CORAZON, A, "ana")
    db.volver_al_provisional(CORAZON, "felipe", T0 + timedelta(hours=2))
    assert filas()[-1] == (CORAZON, "provisional", None, None, None, "felipe", (T0 + timedelta(hours=2)).isoformat())
    assert db.arte_vigente(arte_subido.medidas()) == {}
    assert [r.archivo for r in db.historial_del_arte(CORAZON)] == [None, A]


def test_el_historial_solo_crece():
    subir(CORAZON, A)
    subir(CORAZON, B)
    anterior()
    db.volver_al_provisional(CORAZON, "felipe", T0)
    subir(CORAZON, C)
    assert [(f[1], f[2]) for f in filas()] == [
        ("subir", A), ("subir", B), ("anterior", A), ("provisional", None), ("subir", C)]


def test_una_pieza_cuyo_contrato_cambio_de_medida_no_sale_en_arte_vigente():
    subir(CORAZON, A, medida=(32, 32))
    subir(SUELO, B, medida=(512, 256))
    hoy = arte_subido.medidas()
    assert db.arte_vigente(hoy) == {CORAZON: (A, 32, 32), SUELO: (B, 512, 256)}
    # El suelo cambió de medida en el contrato: lo subido con la vieja deja de servirse.
    assert db.arte_vigente({**hoy, SUELO: (512, 300)}) == {CORAZON: (A, 32, 32)}
    # Y lo de una pieza que ya no está en el contrato se ignora.
    sin_corazon = {ruta: medida for ruta, medida in hoy.items() if ruta != CORAZON}
    assert db.arte_vigente(sin_corazon) == {SUELO: (B, 512, 256)}


def test_arte_puesto_es_la_imagen_de_cada_pieza_mida_lo_que_mida():
    assert db.arte_puesto() == {}
    subir(CORAZON, A, medida=(31, 31))
    subir(SUELO, B, medida=(512, 256))
    subir(SUELO, C, medida=(512, 256))
    subir(ESTRELLA, D)
    subir("efectos/ya-no-esta.png", E)
    db.volver_a_la_anterior(SUELO, "ana", T0, todo_en_disco)
    db.volver_al_provisional(ESTRELLA, "ana", T0)
    # Lo que tiene puesto cada pieza, aunque su medida ya no sea la del contrato o la
    # pieza ya no esté en él; la que está en su recuadro provisional no sale.
    assert db.arte_puesto() == {
        CORAZON: (A, 31, 31), SUELO: (B, 512, 256), "efectos/ya-no-esta.png": (E, 32, 32)}
    assert db.arte_vigente(arte_subido.medidas()) == {SUELO: (B, 512, 256)}


def test_quien_subio_lo_puesto_es_la_ultima_subida_de_esa_misma_imagen():
    assert db.quien_subio_lo_puesto() == {}
    minuto = timedelta(minutes=1)
    subir(CORAZON, A, "ana", T0)
    subir(CORAZON, B, "felipe", T0 + minuto)
    subir(CORAZON, A, "jona", T0 + 2 * minuto)
    subir(CORAZON, C, "felipe", T0 + 3 * minuto)
    # Vuelve a A: la subió por última vez jona, no quien vuelve.
    assert db.volver_a_la_anterior(CORAZON, "pepe", T0 + 4 * minuto, todo_en_disco) == A
    subir(SUELO, B, "ana", T0 + 5 * minuto, medida=(512, 256))
    subir(ESTRELLA, D, "ana", T0)
    db.volver_al_provisional(ESTRELLA, "ana", T0 + 6 * minuto)
    assert db.quien_subio_lo_puesto() == {
        CORAZON: (A, "jona", T0 + 2 * minuto), SUELO: (B, "ana", T0 + 5 * minuto)}


@pytest.mark.parametrize("ruta, archivo", [
    ("../efectos/corazon.png", A), ("efectos/../corazon.png", A), ("/efectos/corazon.png", A),
    ("efectos\\corazon.png", A), ("efectos/corazon", A), (CORAZON, "nota.txt"), (CORAZON, "../" + A),
    (CORAZON, A.upper()), (CORAZON, ""),
])
def test_una_ruta_o_un_archivo_con_forma_rara_no_deja_renglon(ruta, archivo):
    with pytest.raises(ValueError):
        db.subir_arte(ruta, archivo, 32, 32, "ana", T0)
    if archivo == A:
        with pytest.raises(ValueError):
            anterior(ruta)
        with pytest.raises(ValueError):
            db.volver_al_provisional(ruta, "ana", T0)
    assert filas() == []


@pytest.mark.parametrize("accion, subida, archivo, ancho, alto", [
    ("subir", None, A, None, None), ("provisional", None, None, 32, 32), ("subir", None, A, 32, None),
    ("subir", None, None, None, None), ("provisional", None, A, 32, 32), ("anterior", None, A, 32, 32),
    ("subir", 1, A, 32, 32), ("otra", None, A, 32, 32),
])
def test_la_tabla_no_admite_renglones_que_no_cuadran(accion, subida, archivo, ancho, alto):
    subir(CORAZON, A)
    with db.conectar() as con, pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO arte_subido (ruta, accion, subida, archivo, ancho, alto, quien, cuando) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'ana', ?)", (CORAZON, accion, subida, archivo, ancho, alto, T0.isoformat()))


def test_inicializar_dos_veces_no_pierde_el_historial():
    subir(CORAZON, A)
    db.inicializar(T0)
    assert [r.archivo for r in db.historial_del_arte(CORAZON)] == [A]


@pytest.mark.parametrize("accion", ["subir", "anterior", "provisional", "podar"])
def test_lo_que_escribe_toma_la_base_para_escribir_antes_de_leer_nada(accion, monkeypatch):
    """Sobre todo `volver_a_la_anterior`, que lee y luego escribe: dos vueltas a la vez no
    pueden leer lo mismo y caer las dos en la misma imagen."""
    subir(CORAZON, A)
    subir(CORAZON, B)
    sentencias = []
    conectar = db.conectar

    def conectar_espiando():
        con = conectar()
        con.set_trace_callback(sentencias.append)
        return con

    monkeypatch.setattr(db, "conectar", conectar_espiando)
    {
        "subir": lambda: subir(CORAZON, C),
        "anterior": lambda: anterior(),
        "provisional": lambda: db.volver_al_provisional(CORAZON, "felipe", T0),
        "podar": lambda: db.podar_arte(lambda conservar, conocidos: None),
    }[accion]()
    assert sentencias[0] == "BEGIN IMMEDIATE", sentencias


# --- Lo que se conserva y la poda ---------------------------------------------------

def test_se_conservan_las_cinco_ultimas_imagenes_distintas_subidas_de_cada_pieza():
    for archivo in (A, B, A, B, C, D, E, F):
        subir(CORAZON, archivo)
    db.volver_al_provisional(CORAZON, "felipe", T0)  # el provisional no es una de las cinco
    # Del corazón, las cinco últimas distintas son F, E, D, C y B: A se subió dos veces,
    # pero la última vez fue antes que todas ellas.
    assert db.archivos_que_se_conservan() == {B, C, D, E, F}
    # A vuelve a conservarse en cuanto es de las cinco de otra pieza.
    subir(ESTRELLA, A)
    assert db.archivos_que_se_conservan() == {A, B, C, D, E, F}


def test_volver_hacia_atras_no_cambia_lo_que_se_guarda():
    for archivo in (A, B, C, D, E):
        subir(CORAZON, archivo)
    for _ in range(4):
        anterior()
    assert vigente() == A
    # Las vueltas no cuentan como subidas: al llegar F, la que sale de las cinco es A, la
    # subida más vieja, aunque se acabe de volver a ella; y la anterior a F es E.
    subir(CORAZON, F)
    assert db.archivos_que_se_conservan() == {B, C, D, E, F}
    assert anterior() == E


def test_la_poda_decide_y_borra_con_la_base_tomada_para_escribir():
    subir(CORAZON, A)
    vistos = []

    def borrar(conservar, conocidos):
        vistos.append((conservar, conocidos))
        otra = sqlite3.connect(db.RUTA, timeout=0)
        try:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                otra.execute("BEGIN IMMEDIATE")
        finally:
            otra.close()

    db.podar_arte(borrar)
    assert vistos == [({A}, {A})]


def test_la_poda_no_borra_la_vigente_ni_una_de_las_cinco(carpeta):
    colores = [(n * 30, 0, 0, 255) for n in range(7)]
    nombres = [subir_por_ruta(carpeta, CORAZON, png(color)) for color in colores]
    # Las dos primeras ya no son de las cinco últimas del corazón: se borraron.
    assert not (carpeta / nombres[0]).exists()
    assert not (carpeta / nombres[1]).exists()
    assert all((carpeta / nombre).exists() for nombre in nombres[2:])
    # Dos piezas pueden compartir archivo: la vigente de la estrella no se borra aunque
    # el corazón ya no la cuente entre sus cinco.
    compartida = subir_por_ruta(carpeta, ESTRELLA, png(colores[2]))
    assert compartida == nombres[2]
    for color in [(0, n * 30, 0, 255) for n in range(3)]:
        subir_por_ruta(carpeta, CORAZON, png(color))
    assert (carpeta / compartida).exists()
    assert en_carpeta(carpeta) == sorted(db.archivos_que_se_conservan())


def test_una_imagen_vieja_que_vuelve_a_subirse_se_conserva(carpeta):
    vieja = png((7, 7, 7, 255))
    primera = subir_por_ruta(carpeta, CORAZON, vieja)
    for n in range(5):
        subir_por_ruta(carpeta, CORAZON, png((n + 100, 0, 0, 255)))
    assert not (carpeta / primera).exists()
    # Vuelve a subirse: es la vigente, está en disco y se conserva.
    assert subir_por_ruta(carpeta, CORAZON, vieja) == primera
    assert vigente() == primera and (carpeta / primera).exists()
    assert primera in db.archivos_que_se_conservan()
    # Y sigue siendo de las cinco cuando llega otra encima: se la cuenta por su última subida.
    subir_por_ruta(carpeta, CORAZON, png((1, 2, 3, 255)))
    assert (carpeta / primera).exists() and primera in db.archivos_que_se_conservan()
    assert arte_subido.volver(carpeta, arte_subido.pieza_de(CORAZON), "anterior", "felipe", T0) == primera


def test_una_imagen_vieja_a_la_que_se_vuelve_sigue_en_disco(carpeta):
    nombres = [subir_por_ruta(carpeta, CORAZON, png((n, 50, 50, 255))) for n in range(5)]
    corazon = arte_subido.pieza_de(CORAZON)
    for _ in range(4):
        arte_subido.volver(carpeta, corazon, "anterior", "felipe", T0)
    assert vigente() == nombres[0]
    # Otra pieza sube y poda: la vieja del corazón, que es su vigente, no se toca.
    subir_por_ruta(carpeta, ESTRELLA, png((1, 1, 1, 255)))
    assert (carpeta / nombres[0]).exists()
    assert en_carpeta(carpeta) == sorted(db.archivos_que_se_conservan())


def test_volver_no_borra_nada_y_la_anterior_sigue_en_disco(carpeta):
    primera = subir_por_ruta(carpeta, CORAZON, png((1, 2, 3, 255)))
    segunda = subir_por_ruta(carpeta, CORAZON, png((4, 5, 6, 255)))
    corazon = arte_subido.pieza_de(CORAZON)
    assert arte_subido.volver(carpeta, corazon, "anterior", "felipe", T0) == primera
    assert (carpeta / primera).exists() and (carpeta / segunda).exists()
    assert arte_subido.volver(carpeta, corazon, "provisional", "felipe", T0) is None
    assert vigente() is None


def test_volver_a_la_anterior_salta_lo_que_falta_en_la_carpeta(carpeta):
    nombres = [subir_por_ruta(carpeta, CORAZON, png((n, 9, 9, 255))) for n in range(3)]
    (carpeta / nombres[1]).unlink()
    corazon = arte_subido.pieza_de(CORAZON)
    assert arte_subido.volver(carpeta, corazon, "anterior", "felipe", T0) == nombres[0]


def test_desde_el_provisional_volver_a_la_anterior_deshace_el_provisional(carpeta):
    primera = subir_por_ruta(carpeta, CORAZON, png((1, 2, 3, 255)))
    segunda = subir_por_ruta(carpeta, CORAZON, png((4, 5, 6, 255)))
    corazon = arte_subido.pieza_de(CORAZON)
    arte_subido.volver(carpeta, corazon, "provisional", "felipe", T0)
    assert arte_subido.volver(carpeta, corazon, "anterior", "felipe", T0) == segunda
    assert arte_subido.volver(carpeta, corazon, "anterior", "felipe", T0) == primera


def test_sin_nada_subido_en_disco_volver_a_la_anterior_lo_dice(carpeta):
    corazon = arte_subido.pieza_de(CORAZON)
    with pytest.raises(arte_subido.NoVale) as rechazo:
        arte_subido.volver(carpeta, corazon, "anterior", "felipe", T0)
    assert rechazo.value.mensaje == "No hay una imagen anterior."
    assert filas() == []
    # Con lo subido ya fuera de la carpeta, tampoco hay a qué volver.
    nombre = subir_por_ruta(carpeta, CORAZON, png((1, 2, 3, 255)))
    arte_subido.volver(carpeta, corazon, "provisional", "felipe", T0)
    (carpeta / nombre).unlink()
    antes = filas()
    with pytest.raises(arte_subido.NoVale) as rechazo:
        arte_subido.volver(carpeta, corazon, "anterior", "felipe", T0)
    assert rechazo.value.mensaje == "No hay una imagen anterior."
    assert filas() == antes


def test_volver_a_otra_cosa_no_vale(carpeta):
    with pytest.raises(ValueError):
        arte_subido.volver(carpeta, arte_subido.pieza_de(CORAZON), "siguiente", "felipe", T0)
    assert filas() == []


# --- Una subida y una poda a la vez -------------------------------------------------

def test_subir_repone_la_imagen_si_una_poda_se_la_llevo_antes_del_renglon(carpeta, monkeypatch):
    subir_arte = db.subir_arte

    def poda_que_se_cruza(ruta, archivo, *resto):
        (carpeta / archivo).unlink()  # otra poda, con la imagen todavía sin renglón
        subir_arte(ruta, archivo, *resto)

    monkeypatch.setattr(db, "subir_arte", poda_que_se_cruza)
    nombre = subir_por_ruta(carpeta, CORAZON, png((1, 2, 3, 255)))
    assert vigente() == nombre and (carpeta / nombre).exists()


def test_una_poda_no_se_cruza_con_la_subida_de_una_imagen_ya_podada(carpeta, monkeypatch):
    """El intercalado que encontró la revisión.

    R1 vuelve a subir X, que ya se había podado, y escribe su archivo. Antes de que anote su
    renglón, R2 sube otra imagen a la misma pieza y poda: X todavía no se conserva, así que
    la borra. Si R1 pudiera anotar X y terminar mientras R2 poda, X quedaría vigente y sin
    archivo. R1 tiene que esperar a que R2 termine de podar, y luego reponer X.
    """
    vieja = png((10, 10, 10, 255))
    x = subir_por_ruta(carpeta, CORAZON, vieja)
    for n in range(5):
        subir_por_ruta(carpeta, CORAZON, png((n + 100, 0, 0, 255)))
    assert not (carpeta / x).exists()

    r1_antes_del_renglon, r2_podando, r1_termino = threading.Event(), threading.Event(), threading.Event()
    subir_arte, podar = db.subir_arte, arte_subido.podar

    def subir_arte_espiando(*args):
        if threading.current_thread().name == "R1":
            r1_antes_del_renglon.set()
            r2_podando.wait(5)
        subir_arte(*args)

    def podar_espiando(*args):
        if threading.current_thread().name == "R2":
            r2_podando.set()
            r1_termino.wait(0.5)  # si R1 puede terminar mientras R2 poda, termina aquí
        return podar(*args)

    monkeypatch.setattr(db, "subir_arte", subir_arte_espiando)
    monkeypatch.setattr(arte_subido, "podar", podar_espiando)
    errores = []

    def r1():
        try:
            subir_por_ruta(carpeta, CORAZON, vieja, quien="uno")
        except Exception as error:  # se mira después, fuera del hilo
            errores.append(error)
        finally:
            r1_termino.set()

    def r2():
        r1_antes_del_renglon.wait(5)
        try:
            subir_por_ruta(carpeta, CORAZON, png((0, 0, 200, 255)), quien="dos")
        except Exception as error:  # se mira después, fuera del hilo
            errores.append(error)

    hilos = [threading.Thread(target=r1, name="R1"), threading.Thread(target=r2, name="R2")]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(30)
    assert errores == []
    assert [r.quien for r in db.historial_del_arte(CORAZON)][:2] == ["uno", "dos"]
    assert vigente() == x
    assert (carpeta / x).exists()
    assert en_carpeta(carpeta) == sorted(db.archivos_que_se_conservan())


# --- Una subida rara ---------------------------------------------------------------

def pesado(tamano: int) -> bytes:
    return png((1, 2, 3, 255))[:8] + b"\x00" * (tamano - 8)


@pytest.mark.parametrize("ruta, cuerpo, rechazo", [
    pytest.param(CORAZON, b"esto dice ser un png", arte_subido.NoVale, id="no-es-png"),
    pytest.param(CORAZON, png((1, 2, 3, 255))[:-20], arte_subido.NoVale, id="truncado"),
    pytest.param(CORAZON, pesado(arte_subido.LIMITE_DE_BYTES + 1), arte_subido.NoVale, id="4-mb-y-un-byte"),
    pytest.param(CORAZON, png((1, 2, 3, 255), 48, 48), arte_subido.NoVale, id="medida-de-otra-pieza"),
    pytest.param("efectos/../efectos/corazon.png", png((1, 2, 3, 255)), LookupError, id="ruta-con-puntos"),
    pytest.param("efectos/inventado.png", png((1, 2, 3, 255)), LookupError, id="ruta-fuera-del-contrato"),
])
def test_una_subida_rara_no_deja_archivos_ni_renglones(carpeta, ruta, cuerpo, rechazo):
    subir_por_ruta(carpeta, CORAZON, png((9, 9, 9, 255)))
    antes_en_disco = en_carpeta(carpeta)
    antes_en_la_base = filas()
    with pytest.raises(rechazo):
        subir_por_ruta(carpeta, ruta, cuerpo)
    assert en_carpeta(carpeta) == antes_en_disco
    assert filas() == antes_en_la_base


def test_dos_subidas_a_la_vez_a_la_misma_pieza_quedan_las_dos_en_orden(carpeta):
    cuerpos = [png((200, 0, 0, 255)), png((0, 200, 0, 255))]
    salida = threading.Barrier(len(cuerpos))
    nombres, errores = {}, []

    def subir_a_la_vez(indice, cuerpo):
        salida.wait()
        try:
            nombres[indice] = subir_por_ruta(carpeta, CORAZON, cuerpo, quien=f"dibujante {indice}")
        except Exception as error:  # se mira después, fuera del hilo
            errores.append(error)

    hilos = [threading.Thread(target=subir_a_la_vez, args=(i, c)) for i, c in enumerate(cuerpos)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert errores == []
    historial = db.historial_del_arte(CORAZON)
    assert sorted(r.archivo for r in historial) == sorted(nombres.values())
    assert len({r.quien for r in historial}) == 2
    # La vigente es la del último renglón, y las dos están enteras en disco, sin temporales.
    assert db.arte_vigente(arte_subido.medidas()) == {CORAZON: (historial[0].archivo, 32, 32)}
    assert en_carpeta(carpeta) == sorted(nombres.values())
    for nombre in nombres.values():
        assert hashlib.sha256((carpeta / nombre).read_bytes()).hexdigest() + ".png" == nombre
