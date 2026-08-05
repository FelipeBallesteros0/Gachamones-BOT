"""El retrato dibujado: que exista, que esté acotado y que llegue entero.

Los fallos de un adjunto en Discord son silenciosos —una miniatura rota no se ve
y no escribe nada en ningún registro—, así que aquí se comprueba antes.
"""
import struct
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

import pytest

import cosmeticos as cos
import db
import especies as esp
import retrato
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
SOMBREROS = [c.clave for c in cos.SOMBREROS]


NIVEL_DE_ETAPA = {etapa: nivel for nivel, etapa in enumerate(esp.ETAPAS, start=1)}


@pytest.fixture(autouse=True)
def estilo_imagen(monkeypatch):
    monkeypatch.setattr(db, "estilo_de_ficha", lambda *_: "imagen")


def criatura(especie="chispa", etapa="adulto_grande", **cambios) -> sim.Criatura:
    base: dict[str, Any] = dict(
        id=1, usuario_id="u1", guild_id="g1", especie=especie,
        nombre="Pyro", nacida_en=T0, actualizada_en=T0,
        nivel=NIVEL_DE_ETAPA[etapa],
        base_fuerza=15, base_velocidad=15, base_salud=15,
        hambre=90.0, animo=90.0, limpieza=90.0,
    )
    base.update(cambios)
    return sim.Criatura(**base)


# --- Que estén los 21 ------------------------------------------------------

def test_hay_retrato_para_cada_animo_y_cada_sombrero():
    """Tres ánimos por siete estados de sombrero. Que falte uno significa que a
    alguien se le rompe la ficha justo cuando se pone triste o estrena gorro,
    que son los dos momentos en que se mira."""
    faltan = []
    for especie, etapa in retrato.CON_RETRATO:
        for animo in esp.ANIMOS:
            for sombrero in [None, *SOMBREROS]:
                ruta = (retrato.ARTE / especie / etapa
                        / f"{animo}_{sombrero or retrato.SIN_SOMBRERO}.png")
                if not ruta.is_file():
                    faltan.append(str(ruta.relative_to(retrato.ARTE)))
    assert not faltan, faltan


def test_son_png_de_verdad_y_todos_del_mismo_tamaño():
    """Un PNG mal escrito no se ve en Discord y no avisa. Se comprueba la firma
    y la cabecera, que es donde vive el tamaño.

    Que midan **todos lo mismo** importa tanto como que existan: si cada uno se
    hubiera recortado a su propia silueta, el bicho cambiaría de tamaño al
    cambiar de ánimo o al ponerse un sombrero, y se vería pegar saltos.
    """
    for especie, etapa in retrato.CON_RETRATO:
        imagenes = sorted((retrato.ARTE / especie / etapa).glob("*.png"))
        assert len(imagenes) == len(esp.ANIMOS) * (len(SOMBREROS) + 1) == 21

        tamanos = set()
        for ruta in imagenes:
            crudo = ruta.read_bytes()
            assert crudo[:8] == b"\x89PNG\r\n\x1a\n", ruta.name
            tamanos.add(struct.unpack(">II", crudo[16:24]))
            assert (crudo[24], crudo[25]) == (8, 6), f"{ruta}: hace falta RGBA"
        assert len(tamanos) == 1, (especie, etapa, tamanos)

        # Y que sea grande de verdad: Discord no amplía la imagen de un embed
        # más allá de su tamaño real, así que el del fichero ES el que se ve.
        ancho, alto = tamanos.pop()
        assert max(ancho, alto) >= 250, (especie, etapa, ancho, alto)


# --- Que la prueba esté acotada --------------------------------------------

def test_pyro_adulto_grande_tiene_retrato():
    assert retrato.ruta_de(criatura()) is not None


def test_el_animo_y_el_sombrero_eligen_la_imagen():
    hambriento = criatura(hambre=5.0, animo=5.0)
    assert retrato.ruta_de(hambriento) != retrato.ruta_de(criatura())

    for clave in SOMBREROS:
        con = retrato.ruta_de(criatura(sombrero=clave))
        assert con is not None and con.name.endswith(f"_{clave}.png"), clave


def test_ninguna_otra_especie_ni_etapa_entra_en_la_prueba():
    """El cerrojo. Sin él, la ficha pediría una imagen que no existe.

    Se recorren TODAS las combinaciones —25 especies por 5 etapas— y se exige
    que sólo las declaradas devuelvan algo. Es lo que impide que la prueba se
    escape sola cuando alguien deje una carpeta a medias.
    """
    for clave in esp.ESPECIES:
        for etapa in esp.ETAPAS:
            tiene = retrato.ruta_de(criatura(especie=clave, etapa=etapa))
            esperado = (clave, etapa) in retrato.CON_RETRATO
            assert (tiene is not None) == esperado, (clave, etapa)


def test_una_criatura_teñida_vuelve_al_arte_ascii():
    """Enseñar el retrato sin teñir sería peor que no enseñar ninguno: alguien
    pagó por tener su Pyro azul y lo vería rojo. El tinte se resolverá con una
    imagen por color, y hasta entonces estos vuelven a ASCII."""
    for tinte in (c.clave for c in cos.TINTES):
        assert retrato.ruta_de(criatura(tinte=tinte)) is None, tinte


def test_un_sombrero_sin_dibujo_no_deja_la_ficha_a_medias():
    """Si mañana se añade un sombrero y falta su imagen, la ficha cae al arte
    ASCII en vez de quedarse sin nada."""
    assert retrato.ruta_de(criatura(sombrero="sombrero_que_no_existe")) is None


# --- Que llegue entero a Discord -------------------------------------------

def test_el_nombre_del_adjunto_sale_del_mismo_sitio_que_la_ruta():
    """Es el fallo clásico de los embeds: si `attachment://x.png` no cuadra con
    el nombre del fichero enviado, la miniatura sale vacía y no falla nada."""
    ruta = retrato.ruta_de(criatura())
    assert ruta is not None
    assert retrato.nombre_del_adjunto(ruta) == ruta.name


def test_el_borde_lleva_el_color_de_la_especie():
    assert retrato.color_de(criatura()) == retrato.COLORES[esp.ROJO]


def test_todas_las_especies_tienen_color_de_borde():
    """Aunque hoy sólo Pyro tenga retrato: el día que entre otra, el borde no
    puede salir gris por un color sin traducir."""
    for clave, definicion in esp.ESPECIES.items():
        assert definicion.color in retrato.COLORES, clave


# --- La ficha ya montada ---------------------------------------------------

def test_la_ficha_con_retrato_ata_la_miniatura_a_su_adjunto():
    """Lo que de verdad se envía a Discord.

    El embed pide la miniatura por `attachment://<nombre>` y el adjunto viaja
    aparte; si los dos nombres no coinciden, Discord muestra el embed sin
    imagen y **no da ningún error**. Por eso se comprueba aquí y no mirando.
    """
    import vistas

    ficha = vistas._ficha(criatura(), T0)
    assert ficha["content"] is None, "con retrato el texto va dentro del embed"

    adjunto = ficha["file"]
    assert ficha["embed"].image.url == f"attachment://{adjunto.filename}"
    assert adjunto.filename.endswith(".png")


def test_la_ficha_con_retrato_no_repite_el_bicho_en_ascii():
    """Si además del retrato se pintara el arte, saldría dos veces."""
    import pantalla
    import vistas

    ficha = vistas._ficha(criatura(), T0)
    descripcion = ficha["embed"].description
    assert "COMIDA" in descripcion and "EXP" in descripcion
    arte = esp.arte_de(esp.ESPECIES["chispa"], "adulto_grande", "normal")
    primera = [l for l in arte.strip("\n").split("\n") if l.strip()][0]
    assert primera.strip() not in descripcion
    assert len(descripcion) < len(pantalla.render(criatura(), T0))


SIN_RETRATO = next(
    c for c in esp.ESPECIES if c not in retrato.CON_ETAPAS_COMPLETAS
)


def test_la_ficha_sin_retrato_sigue_siendo_texto_pelado():
    """Las especies sin dibujar no pueden notar nada de esto."""
    import vistas

    ficha = vistas._ficha(criatura(especie=SIN_RETRATO), T0)
    assert set(ficha) == {"content"} and ficha["content"]


def test_al_editar_se_limpian_siempre_adjunto_y_embed():
    """Discord conserva lo que no mencionas. Una ficha que vuelve a ASCII
    —porque el bicho evolucionó, se murió o se tiñó— tiene que decir
    explícitamente que ya no lleva imagen, o se queda el retrato viejo pegado.
    """
    import vistas

    texto = vistas._como_edicion(vistas._ficha(criatura(especie=SIN_RETRATO), T0))
    assert texto["attachments"] == [] and texto["embed"] is None

    con_foto = vistas._como_edicion(vistas._ficha(criatura(), T0))
    assert len(con_foto["attachments"]) == 1 and con_foto["content"] is None
