"""El marco no se descuadra jamás: ni con dibujos raros ni con nombres largos."""
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import especies as esp
import pantalla
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def test_recibo_une_solo_las_partes_no_vacias():
    assert pantalla.recibo("efecto", "", "costo", "tope") == (
        "-# efecto · costo · tope"
    )


def sin_color(texto: str) -> str:
    return ANSI.sub("", texto)


def lineas_del_marco(mensaje: str) -> list[str]:
    """Saca las líneas que hay dentro del bloque ```ansi, ya sin códigos."""
    dentro = mensaje.split("```ansi\n")[1].split("\n```")[0]
    return sin_color(dentro).split("\n")


def criatura(**cambios) -> sim.Criatura:
    base: dict[str, Any] = dict(
        id=1, usuario_id="u1", guild_id="g1", especie="pulpo", nombre="Prueba",
        nacida_en=T0, actualizada_en=T0,
        base_fuerza=15, base_velocidad=15, base_salud=15,
    )
    base.update(cambios)
    return sim.Criatura(**base)


def comprobar_marco(mensaje: str) -> None:
    lineas = lineas_del_marco(mensaje)
    anchos = {len(ln) for ln in lineas}
    assert anchos == {pantalla.ANCHO + 2}, anchos
    for linea in lineas:
        assert linea[0] in "╭├╰│", linea
        assert linea[-1] in "╮┤╯│", linea


def test_todas_las_especies_en_todos_los_estados_cuadran():
    """10 especies x 3 ánimos x 2 etapas: 60 pantallas, ninguna descuadrada."""
    for clave in esp.ESPECIES:
        for hambre, animo in ((90, 90), (50, 50), (10, 50)):
            for horas in (2, 48):  # cría y adulta
                c = criatura(especie=clave, hambre=hambre, animo=animo)
                comprobar_marco(pantalla.render(c, T0 + timedelta(hours=horas)))


def test_el_huevo_y_la_lapida_tambien_cuadran():
    comprobar_marco(pantalla.render_huevo())
    comprobar_marco(pantalla.render_huevo(rajado=True))
    muerta = criatura(muerta_en=T0 + timedelta(days=3), causa_muerte="hambre")
    comprobar_marco(pantalla.render(muerta, T0 + timedelta(days=3)))


def test_la_revelacion_cuadra_en_todas_las_especies():
    for clave in esp.ESPECIES:
        comprobar_marco(pantalla.render_revelacion(criatura(especie=clave), T0))


def test_la_revelacion_enseña_especie_y_estadisticas_pero_no_el_nombre():
    """Es lo que se ve ANTES de bautizarla: el nombre provisional no pinta
    nada ahí, pero la tirada de estadísticas sí, que es lo emocionante."""
    c = criatura(especie="dragoncito", nombre="Dragoncito",
                 base_fuerza=18, base_velocidad=14, base_salud=12)
    mensaje = pantalla.render_revelacion(c, T0)
    cabecera = mensaje.split("```ansi")[0]

    assert "Dragoncito" in cabecera
    assert "rara" in cabecera  # avisa de que ha tenido suerte
    for stat in ("18", "14", "12"):
        assert stat in mensaje


def test_un_nombre_larguisimo_no_rompe_la_lapida():
    muerta = criatura(
        nombre="Bartolomeo Maximiliano de la Vega y Mendoza III",
        muerta_en=T0 + timedelta(days=3), causa_muerte="hambre",
    )
    comprobar_marco(pantalla.render(muerta, T0 + timedelta(days=3)))


# --- La fila de estadísticas ------------------------------------------------

def fila_stats(criatura_) -> str:
    return next(l for l in lineas_del_marco(pantalla.render(criatura_, T0))
                if "FUE" in l)


def test_stats_de_tres_cifras_no_rompen_el_marco():
    c = criatura(base_fuerza=120, base_velocidad=999, base_salud=100)
    comprobar_marco(pantalla.render(c, T0 + timedelta(hours=48)))


def test_el_marco_cuadra_con_cualquier_estadistica_hasta_el_tope():
    """Las tres pantallas que enseñan estadísticas, no sólo la principal."""
    for valor in (0, 9, 10, 99, 100, 500, sim.MAXIMO_STAT):
        c = criatura(base_fuerza=valor, base_velocidad=valor, base_salud=valor)
        comprobar_marco(pantalla.render(c, T0 + timedelta(hours=48)))
        comprobar_marco(pantalla.render_revelacion(c, T0))
        comprobar_marco(pantalla.render_evolucion(c, esp.NINO, ("fuerza",)))


def test_las_estadisticas_grandes_se_ven_enteras():
    """Regresión: el marco cuadraba *recortando*. Con tres cifras la fila medía
    29 y `_fila()` cortaba en 26, así que se veía «SAL 1» en vez de «SAL 100»."""
    c = criatura(base_fuerza=sim.MAXIMO_STAT, base_velocidad=100, base_salud=123)
    fila = fila_stats(c)
    assert f"FUE {sim.MAXIMO_STAT}" in fila
    assert "VEL 100" in fila
    assert "SAL 123" in fila


def test_con_dos_cifras_la_fila_es_la_de_siempre():
    """El ancho se calcula, pero el caso normal no puede cambiar de aspecto:
    ninguna criatura real pasa de 99 y no queremos que se les mueva nada."""
    c = criatura(base_fuerza=18, base_velocidad=22, base_salud=19)
    assert fila_stats(c) == "│ FUE 18   VEL 22   SAL 19 │"


def test_el_dibujo_sale_centrado():
    """Regresión: el arte arrastra la sangría del código fuente. Si no se quita
    con dedent antes de centrar, se suma al margen y todo sale escorado."""
    for clave in esp.ESPECIES:
        c = criatura(especie=clave)
        lineas = lineas_del_marco(pantalla.render(c, T0 + timedelta(hours=48)))
        # Las filas del dibujo son las que hay antes del primer separador.
        arte = [ln[1:-1] for ln in lineas[1:] if ln[0] == "│"]
        arte = [ln for ln in arte[:pantalla.ALTO_ARTE] if ln.strip()]

        izquierda = min(len(ln) - len(ln.lstrip()) for ln in arte)
        derecha = min(len(ln) - len(ln.rstrip()) for ln in arte)
        assert abs(izquierda - derecha) <= 1, (clave, izquierda, derecha)


def test_las_barras_reflejan_el_valor():
    lleno = lineas_del_marco(pantalla.render(criatura(hambre=100.0), T0))
    fila = next(ln for ln in lleno if "COMIDA" in ln)
    assert "░" not in fila
    assert fila.count("█") == pantalla.ANCHO_BARRA
    assert "100" in fila

    vacio = lineas_del_marco(pantalla.render(criatura(hambre=0.5), T0))
    fila = next(ln for ln in vacio if "COMIDA" in ln)
    assert fila.count("░") == pantalla.ANCHO_BARRA


# --- La barra de experiencia -----------------------------------------------

def fila_exp(criatura_) -> str:
    return next(l for l in lineas_del_marco(pantalla.render(criatura_, T0))
                if "EXP" in l)


def test_la_barra_de_experiencia_dice_cuanto_falta():
    """«12/25» en vez de un porcentaje: con un objetivo que cambia en cada
    etapa, un 48% no dice si faltan 13 puntos o 270."""
    fila = fila_exp(criatura(nivel=1, xp=12))
    assert f"12/{sim.xp_para_subir(1)}" in fila


def test_la_barra_de_experiencia_se_llena_en_proporcion():
    vacia = fila_exp(criatura(nivel=1, xp=0))
    assert vacia.count("░") == pantalla.ANCHO_BARRA_XP
    assert "█" not in vacia

    casi = fila_exp(criatura(nivel=1, xp=sim.xp_para_subir(1) - 1))
    assert casi.count("█") == pantalla.ANCHO_BARRA_XP

    media = fila_exp(criatura(nivel=1, xp=sim.xp_para_subir(1) // 2))
    assert 0 < media.count("█") < pantalla.ANCHO_BARRA_XP


def test_el_numero_mas_largo_no_descuadra_el_marco():
    """524/525 son siete caracteres, el caso peor de toda la curva."""
    comprobar_marco(pantalla.render(
        criatura(nivel=4, xp=sim.xp_para_subir(4) - 1), T0
    ))


def test_en_el_nivel_maximo_la_barra_sigue_teniendo_sentido():
    """Ya no hay etapa nueva, pero se sigue subiendo de nivel y repartiendo
    estadísticas, así que la barra sigue midiendo algo real."""
    fila = fila_exp(criatura(nivel=7, xp=100))
    assert f"100/{sim.xp_para_subir(7)}" in fila
    comprobar_marco(pantalla.render(criatura(nivel=7, xp=100), T0))


def test_la_experiencia_no_usa_los_colores_del_bienestar():
    """Regresión: con la escala verde/amarillo/rojo, una criatura recién
    evolucionada (0 XP) saldría en rojo justo en su mejor momento."""
    mensaje = pantalla.render(criatura(nivel=2, xp=0), T0)
    bloque = mensaje.split("```ansi\n")[1]
    fila_cruda = next(l for l in bloque.split("\n") if "EXP" in l)
    assert f"\x1b[0;{esp.ROJO}m" not in fila_cruda
    assert f"\x1b[0;{esp.CIAN}m" in fila_cruda


def test_la_barra_de_experiencia_va_debajo_de_las_estadisticas():
    filas = lineas_del_marco(pantalla.render(criatura(), T0))
    posicion_stats = next(i for i, l in enumerate(filas) if "FUE" in l)
    posicion_exp = next(i for i, l in enumerate(filas) if "EXP" in l)
    assert posicion_exp > posicion_stats


def test_las_barras_cambian_de_color_segun_el_nivel():
    assert pantalla._color_barra(80) == esp.VERDE
    assert pantalla._color_barra(45) == esp.AMARILLO
    assert pantalla._color_barra(10) == esp.ROJO


def test_el_arte_se_pinta_del_color_de_la_especie():
    mensaje = pantalla.render(criatura(especie="brote"), T0 + timedelta(hours=48))
    assert f"\x1b[0;{esp.VERDE}m" in mensaje


def test_el_mensaje_lleva_encabezado_y_subtexto_fuera_del_bloque():
    mensaje = pantalla.render(criatura(nombre="Pelusa"), T0)
    cabecera = mensaje.split("```ansi")[0]
    assert "## " in cabecera
    assert "Pelusa" in cabecera
    assert "-# " in cabecera


def test_los_cooldowns_salen_como_subtexto():
    mensaje = pantalla.render(
        criatura(), T0,
        esperas={sim.ALIMENTAR: timedelta(0), sim.ENTRENAR: timedelta(minutes=80)},
    )
    assert "🍖 listo" in mensaje
    assert "🏋️ 1 h 20 min" in mensaje


def test_las_seis_esperas_salen_en_orden_con_iconos_exactos():
    esperas: dict[str, timedelta] = dict(zip(
        pantalla.ACCIONES_EN_FICHA,
        (
            timedelta(0), timedelta(minutes=2), timedelta(minutes=80),
            timedelta(0), timedelta(minutes=10), timedelta(minutes=37),
        ),
    ))

    linea = pantalla.render(criatura(), T0, esperas=esperas).splitlines()[-1]

    assert linea == (
        "-# 🍖 listo · 🎮 2 min · 🏋️ 1 h 20 min · 🧼 listo"
        " · 🏁 10 min · 🧭 37 min"
    )


def test_el_color_de_la_barra_y_la_regla_de_urgencia_no_pueden_separarse():
    """Regresión del error original: el 60 vivía en el código de dibujo y la
    regla de juego no lo consultaba, así que la barra salía naranja y el botón
    seguía bloqueado. Si alguien vuelve a duplicar el umbral, esto falla."""
    for valor in range(0, 101):
        no_esta_verde = pantalla._color_barra(valor) != esp.VERDE
        puede_comer = sim.puede_saltarse_espera(criatura(hambre=float(valor)),
                                                sim.ALIMENTAR)
        assert no_esta_verde == puede_comer, valor


def test_el_subtexto_avisa_del_hambre_en_vez_de_mentir():
    """Si el botón funciona, poner «en 12 min» sería mentira."""
    mensaje = pantalla.render(
        criatura(hambre=25.0), T0,
        esperas={sim.ALIMENTAR: timedelta(minutes=12)},
    )
    assert "🍖 ¡tiene hambre!" in mensaje
    assert "🍖 12 min" not in mensaje


def test_con_la_barra_verde_el_subtexto_dice_el_tiempo_normal():
    mensaje = pantalla.render(
        criatura(hambre=80.0), T0,
        esperas={sim.ALIMENTAR: timedelta(minutes=12)},
    )
    assert "🍖 12 min" in mensaje
    assert "tiene hambre" not in mensaje


def test_el_aviso_de_hambre_no_afecta_a_las_demas_acciones():
    mensaje = pantalla.render(
        criatura(hambre=10.0), T0,
        esperas={sim.JUGAR: timedelta(minutes=12),
                 sim.ENTRENAR: timedelta(minutes=80),
                 sim.COMPETIR: timedelta(minutes=10),
                 sim.AVENTURA: timedelta(minutes=37)},
    )
    assert "🎮 12 min" in mensaje
    assert "🏋️ 1 h 20 min" in mensaje
    assert "🏁 10 min" in mensaje
    assert "🧭 37 min" in mensaje
    assert "tiene hambre" not in mensaje


def test_formato_de_espera():
    assert pantalla.formato_espera(timedelta(0)) == "listo"
    assert pantalla.formato_espera(timedelta(seconds=-5)) == "listo"
    assert pantalla.formato_espera(timedelta(minutes=12)) == "12 min"
    assert pantalla.formato_espera(timedelta(seconds=30)) == "1 min"
    assert pantalla.formato_espera(timedelta(hours=2)) == "2 h"
    assert pantalla.formato_espera(timedelta(minutes=80)) == "1 h 20 min"


def test_el_aviso_de_la_accion_sale_como_cita():
    mensaje = pantalla.render(criatura(), T0, aviso="Ñam.")
    assert "> Ñam." in mensaje


# --- Género y carácter en la ficha -----------------------------------------

def test_la_ficha_lleva_el_emoji_del_genero_y_la_palabra_del_caracter():
    el = pantalla.render(criatura(genero=esp.MACHO, caracter="gruñón"), T0)
    assert "♂️" in el.split("```ansi")[0]
    assert "gruñón" in el

    ella = pantalla.render(criatura(genero=esp.HEMBRA, caracter="gruñón"), T0)
    assert "♀️" in ella.split("```ansi")[0]
    assert "gruñona" in ella


def test_el_emoji_de_genero_nunca_entra_en_el_marco():
    """Regresión estructural: dentro del bloque ```ansi Discord sustituye el
    emoji por una imagen de ancho variable y descuadra el dibujo entero."""
    for genero in esp.GENEROS:
        for render in (pantalla.render, pantalla.render_revelacion):
            mensaje = render(criatura(genero=genero), T0)
            comprobar_marco(mensaje)
            dentro = mensaje.split("```ansi\n")[1].split("\n```")[0]
            for emoji in pantalla.EMOJI_GENERO.values():
                assert emoji not in dentro


def test_la_etapa_concuerda_con_el_genero():
    el = pantalla.render(criatura(nivel=2), T0)
    ella = pantalla.render(criatura(nivel=2, genero=esp.HEMBRA), T0)
    assert "niño" in el and "niña" not in el
    assert "niña" in ella


def test_la_revelacion_enseña_el_genero_y_el_caracter():
    """Es lo que se descubre al romper el huevo, junto con las estadísticas."""
    mensaje = pantalla.render_revelacion(
        criatura(genero=esp.HEMBRA, caracter="travieso"), T0)
    assert "♀️" in mensaje
    assert "traviesa" in mensaje


def test_la_lapida_conserva_quien_era():
    muerta = criatura(genero=esp.HEMBRA, caracter="perezoso",
                      muerta_en=T0 + timedelta(days=3), causa_muerte="hambre")
    mensaje = pantalla.render(muerta, T0 + timedelta(days=3))
    assert "♀️" in mensaje
    assert "perezosa" in mensaje
    comprobar_marco(mensaje)


def test_una_criatura_muerta_siempre_enseña_la_lapida():
    muerta = criatura(muerta_en=T0, causa_muerte="hambre")
    assert "🪦" in pantalla.render(muerta, T0)
    assert "/huevo" in pantalla.render(muerta, T0)


def test_la_lapida_no_muestra_esperas():
    muerta = criatura(muerta_en=T0, causa_muerte="hambre")
    esperas = {accion: timedelta(minutes=1) for accion in (
        *sim.ACCIONES_DE_CUIDADO, sim.COMPETIR, sim.AVENTURA
    )}

    mensaje = pantalla.render(muerta, T0, esperas=esperas)

    assert all(icono not in mensaje for icono in ("🍖", "🎮", "🏋️", "🧼", "🏁", "🧭"))


def test_la_revelacion_usa_el_articulo_de_la_especie():
    chispa = pantalla.render_revelacion(criatura(especie="chispa"), T0)
    assert "una Chispa" in chispa
    pulpo = pantalla.render_revelacion(criatura(especie="pulpo"), T0)
    assert "un Pulpo" in pulpo


# --- Las pociones activas --------------------------------------------------

def test_el_efecto_de_una_pocion_sale_en_el_subtexto():
    """Si no se viera, no habría forma de saber que la poción está haciendo
    algo, ni cuánto le queda."""
    from datetime import timedelta

    texto = pantalla.render(
        criatura(), T0,
        efectos={"fuerza": (7, timedelta(minutes=4))},
    )
    subtexto = [ln for ln in texto.split("\n") if ln.startswith("-#")]
    assert any("+7" in ln and "fuerza" in ln for ln in subtexto), subtexto


def test_el_efecto_va_fuera_del_marco():
    """Lleva emoji, y dentro de un bloque ```ansi Discord lo sustituye por una
    imagen de ancho variable y descuadra el marco. Cuatro descuadres han salido
    ya de meter cosas dentro que no debían."""
    from datetime import timedelta

    texto = pantalla.render(
        criatura(), T0,
        efectos={"fuerza": (12, timedelta(minutes=5)),
                 "velocidad": (9, timedelta(minutes=1))},
    )
    dentro = texto.split("```ansi\n")[1].split("\n```")[0]
    assert "⚗" not in dentro and "+12" not in dentro

    for linea in ANSI.sub("", dentro).split("\n"):
        assert len(linea) == pantalla.ANCHO + 2, repr(linea)


def test_sin_pociones_no_se_aniade_ninguna_linea():
    """La ficha de siempre no puede cambiar por esto."""
    assert pantalla.render(criatura(), T0) == \
        pantalla.render(criatura(), T0, efectos={})


def test_se_ven_las_dos_pociones_a_la_vez():
    from datetime import timedelta

    texto = pantalla.render(
        criatura(), T0,
        efectos={"fuerza": (3, timedelta(minutes=2)),
                 "velocidad": (5, timedelta(minutes=1))},
    )
    assert "+3" in texto and "+5" in texto
    assert "fuerza" in texto and "velocidad" in texto


# --- La incubadora ---------------------------------------------------------

def test_la_incubadora_sale_en_el_subtexto_y_fuera_del_marco():
    texto = pantalla.render(criatura(), T0, en_la_incubadora=2)

    assert "2 esperan" in texto
    dentro = texto.split("```ansi\n")[1].split("\n```")[0]
    assert "🥚" not in dentro
    for linea in ANSI.sub("", dentro).split("\n"):
        assert len(linea) == pantalla.ANCHO + 2, repr(linea)


def test_con_uno_solo_la_incubadora_no_se_menciona():
    """La ficha de quien tiene un único gachamon no puede cambiar por esto."""
    assert pantalla.render(criatura(), T0) == \
        pantalla.render(criatura(), T0, en_la_incubadora=0)


def test_el_singular_de_la_incubadora_esta_bien():
    texto = pantalla.render(criatura(), T0, en_la_incubadora=1)
    assert "1 espera" in texto and "esperan" not in texto


def test_la_ficha_adversarial_cabe_en_discord():
    mensaje = pantalla.render(
        criatura(nombre="N" * sim.LARGO_MAXIMO_NOMBRE),
        T0,
        esperas={
            accion: timedelta(hours=1, minutes=59)
            for accion in (*sim.ACCIONES_DE_CUIDADO, sim.COMPETIR, sim.AVENTURA)
        },
        aviso=(
            "La aventura terminó sin botín porque la mochila estaba llena; "
            "se conservaron las recompensas congeladas del evento y el plantel "
            "activo no cambió. Libera espacio antes de volver a intentarlo."
        ),
        efectos={
            "fuerza": (99, timedelta(hours=23, minutes=59)),
            "velocidad": (99, timedelta(hours=23, minutes=59)),
        },
        en_la_incubadora=2,
    )

    assert len(mensaje) < 2000
