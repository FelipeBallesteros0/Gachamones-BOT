"""Lo subido por el dibujante en la base: el historial que sólo crece, la vigente de cada pieza y la poda.

Las pruebas de punta a punta siguen el camino de una subida tal como lo arma
quien la recibe: la pieza del contrato, `preparar`, `guardar`, `db.subir_arte` y
la poda. Los PNG se fabrican aquí.
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

T0 = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
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


A, B, C, D, E, F = (falso(n) for n in range(6))


def filas():
    with db.conectar() as con:
        return [tuple(f) for f in con.execute("SELECT ruta, archivo, ancho, alto, quien, cuando FROM arte_subido ORDER BY id")]


def subir(ruta, archivo, quien="ana", ahora=T0, medida=(32, 32)):
    db.subir_arte(ruta, archivo, *medida, quien, ahora)


def png(color, ancho=32, alto=32) -> bytes:
    salida = io.BytesIO()
    Image.new("RGBA", (ancho, alto), color).save(salida, "PNG")
    return salida.getvalue()


def subida_entera(carpeta, ruta, cuerpo, quien="ana", ahora=T0) -> str:
    """Lo que hace quien recibe una subida, en su orden."""
    pieza = arte_subido.pieza_de(ruta)
    if pieza is None:
        raise LookupError(ruta)
    datos, nombre = arte_subido.preparar(cuerpo, pieza)
    arte_subido.guardar(carpeta, nombre, datos)
    db.subir_arte(ruta, nombre, pieza.ancho, pieza.alto, quien, ahora)
    del_historial = [r.archivo for r in db.historial_del_arte(ruta) if r.archivo]
    arte_subido.podar(carpeta, del_historial, db.archivos_que_se_conservan())
    return nombre


# --- El historial ---------------------------------------------------------------

def test_sin_nada_subido_todo_es_provisional():
    assert db.arte_vigente(arte_subido.medidas()) == {}
    assert db.historial_del_arte(CORAZON) == []
    assert db.archivos_que_se_conservan() == set()


def test_subir_deja_su_renglon_con_el_nombre_de_quien_sube_y_pasa_a_ser_la_vigente():
    subir(CORAZON, A, "ana", T0)
    subir(CORAZON, B, "felipe", T0 + timedelta(minutes=1))
    assert filas() == [
        (CORAZON, A, 32, 32, "ana", T0.isoformat()),
        (CORAZON, B, 32, 32, "felipe", (T0 + timedelta(minutes=1)).isoformat()),
    ]
    assert db.arte_vigente(arte_subido.medidas()) == {CORAZON: (B, 32, 32)}
    historial = db.historial_del_arte(CORAZON)
    assert [(r.archivo, r.ancho, r.alto, r.quien, r.cuando) for r in historial] == [
        (B, 32, 32, "felipe", T0 + timedelta(minutes=1)),
        (A, 32, 32, "ana", T0),
    ]


def test_el_historial_es_de_cada_pieza():
    subir(CORAZON, A)
    subir(ESTRELLA, B)
    assert [r.archivo for r in db.historial_del_arte(CORAZON)] == [A]
    assert db.arte_vigente(arte_subido.medidas()) == {CORAZON: (A, 32, 32), ESTRELLA: (B, 32, 32)}


def test_volver_a_la_anterior_deja_un_renglon_nuevo_a_nombre_de_quien_vuelve_y_apunta_a_la_anterior_distinta():
    subir(CORAZON, A, "ana", T0)
    subir(CORAZON, B, "ana", T0 + timedelta(minutes=1))
    subir(CORAZON, B, "ana", T0 + timedelta(minutes=2))  # la misma otra vez: no es «la anterior»
    despues = T0 + timedelta(minutes=3)
    assert db.volver_a_la_anterior(CORAZON, "felipe", despues) == A
    assert filas()[-1] == (CORAZON, A, 32, 32, "felipe", despues.isoformat())
    assert len(filas()) == 4
    assert db.arte_vigente(arte_subido.medidas()) == {CORAZON: (A, 32, 32)}
    # Y volver otra vez lleva a la que estaba antes de ésta, que es B.
    assert db.volver_a_la_anterior(CORAZON, "felipe", despues) == B
    assert db.arte_vigente(arte_subido.medidas()) == {CORAZON: (B, 32, 32)}


def test_volver_sin_anterior_vuelve_al_provisional():
    subir(CORAZON, A, "ana")
    assert db.volver_a_la_anterior(CORAZON, "felipe", T0 + timedelta(hours=1)) is None
    assert filas()[-1] == (CORAZON, None, None, None, "felipe", (T0 + timedelta(hours=1)).isoformat())
    assert db.arte_vigente(arte_subido.medidas()) == {}


def test_volver_en_una_pieza_sin_historial_deja_igual_su_renglon_provisional():
    assert db.volver_a_la_anterior(CORAZON, "felipe", T0) is None
    assert filas() == [(CORAZON, None, None, None, "felipe", T0.isoformat())]


def test_desde_el_provisional_volver_a_la_anterior_recupera_la_ultima_imagen():
    subir(CORAZON, A)
    subir(CORAZON, B)
    db.volver_al_provisional(CORAZON, "felipe", T0)
    assert db.arte_vigente(arte_subido.medidas()) == {}
    assert db.volver_a_la_anterior(CORAZON, "felipe", T0) == B
    assert db.arte_vigente(arte_subido.medidas()) == {CORAZON: (B, 32, 32)}


def test_volver_al_provisional_deja_su_renglon_y_la_pieza_sin_imagen():
    subir(CORAZON, A, "ana")
    db.volver_al_provisional(CORAZON, "felipe", T0 + timedelta(hours=2))
    assert filas()[-1] == (CORAZON, None, None, None, "felipe", (T0 + timedelta(hours=2)).isoformat())
    assert db.arte_vigente(arte_subido.medidas()) == {}
    assert [r.archivo for r in db.historial_del_arte(CORAZON)] == [None, A]


def test_el_historial_solo_crece():
    subir(CORAZON, A)
    db.volver_al_provisional(CORAZON, "felipe", T0)
    db.volver_a_la_anterior(CORAZON, "felipe", T0)
    subir(CORAZON, B)
    assert [f[1] for f in filas()] == [A, None, A, B]


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
            db.volver_a_la_anterior(ruta, "ana", T0)
        with pytest.raises(ValueError):
            db.volver_al_provisional(ruta, "ana", T0)
    assert filas() == []


def test_la_tabla_no_admite_una_imagen_sin_medida_ni_una_medida_sin_imagen():
    with db.conectar() as con:
        for archivo, ancho, alto in ((A, None, None), (None, 32, 32), (A, 32, None)):
            with pytest.raises(sqlite3.IntegrityError):
                con.execute("INSERT INTO arte_subido (ruta, archivo, ancho, alto, quien, cuando) "
                            "VALUES (?, ?, ?, ?, 'ana', ?)", (CORAZON, archivo, ancho, alto, T0.isoformat()))


def test_inicializar_dos_veces_no_pierde_el_historial():
    subir(CORAZON, A)
    db.inicializar(T0)
    assert [r.archivo for r in db.historial_del_arte(CORAZON)] == [A]


# --- Lo que se conserva y la poda ---------------------------------------------------

def test_se_conservan_las_cinco_ultimas_imagenes_distintas_de_cada_pieza():
    for archivo in (A, B, A, B, C, D, E, F):
        subir(CORAZON, archivo)
    db.volver_al_provisional(CORAZON, "felipe", T0)  # el provisional no es una de las cinco
    # Del corazón, las cinco últimas distintas son F, E, D, C y B: A se subió dos veces,
    # pero la última vez fue antes que todas ellas.
    assert db.archivos_que_se_conservan() == {B, C, D, E, F}
    # A vuelve a conservarse en cuanto es de las cinco de otra pieza.
    subir(ESTRELLA, A)
    assert db.archivos_que_se_conservan() == {A, B, C, D, E, F}


def test_la_poda_no_borra_la_vigente_ni_una_de_las_cinco(carpeta):
    colores = [(n * 30, 0, 0, 255) for n in range(7)]
    nombres = [subida_entera(carpeta, CORAZON, png(color)) for color in colores]
    # Las dos primeras ya no son de las cinco últimas del corazón: se borraron.
    assert not (carpeta / nombres[0]).exists()
    assert not (carpeta / nombres[1]).exists()
    assert all((carpeta / nombre).exists() for nombre in nombres[2:])
    # Dos piezas pueden compartir archivo: la vigente de la estrella no se borra aunque
    # el corazón ya no la cuente entre sus cinco.
    compartida = subida_entera(carpeta, ESTRELLA, png(colores[2]))
    assert compartida == nombres[2]
    for color in [(0, n * 30, 0, 255) for n in range(3)]:
        subida_entera(carpeta, CORAZON, png(color))
    assert (carpeta / compartida).exists()
    assert sorted(p.name for p in carpeta.iterdir()) == sorted(db.archivos_que_se_conservan())


def test_volver_no_borra_nada_y_la_anterior_sigue_en_disco(carpeta):
    primera = subida_entera(carpeta, CORAZON, png((1, 2, 3, 255)))
    segunda = subida_entera(carpeta, CORAZON, png((4, 5, 6, 255)))
    assert db.volver_a_la_anterior(CORAZON, "felipe", T0) == primera
    assert (carpeta / primera).exists() and (carpeta / segunda).exists()


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
    subida_entera(carpeta, CORAZON, png((9, 9, 9, 255)))
    antes_en_disco = sorted(p.name for p in carpeta.iterdir())
    antes_en_la_base = filas()
    with pytest.raises(rechazo):
        subida_entera(carpeta, ruta, cuerpo)
    assert sorted(p.name for p in carpeta.iterdir()) == antes_en_disco
    assert filas() == antes_en_la_base


def test_dos_subidas_a_la_vez_a_la_misma_pieza_quedan_las_dos_en_orden(carpeta):
    cuerpos = [png((200, 0, 0, 255)), png((0, 200, 0, 255))]
    salida = threading.Barrier(len(cuerpos))
    nombres, errores = {}, []

    def subir_a_la_vez(indice, cuerpo):
        salida.wait()
        try:
            nombres[indice] = subida_entera(carpeta, CORAZON, cuerpo, quien=f"dibujante {indice}")
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
    assert sorted(p.name for p in carpeta.iterdir()) == sorted(nombres.values())
    for nombre in nombres.values():
        assert hashlib.sha256((carpeta / nombre).read_bytes()).hexdigest() + ".png" == nombre
