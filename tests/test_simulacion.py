"""Reglas del juego: decaimiento, muerte, acciones, stats y niveles."""
import random
from datetime import datetime, timedelta, timezone

import especies as esp
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def criatura(**cambios) -> sim.Criatura:
    base = dict(
        id=1, usuario_id="u1", guild_id="g1", especie="pulpo", nombre="Prueba",
        nacida_en=T0, actualizada_en=T0,
        base_fuerza=15, base_velocidad=15, base_salud=15,
    )
    base.update(cambios)
    return sim.Criatura(**base)


# --- Decaimiento y muerte --------------------------------------------------

def test_una_criatura_tipica_aguanta_unas_73_horas():
    assert 72 <= sim.horas_de_vida(15) <= 74


def test_el_rango_de_vida_entre_especies_es_el_previsto():
    """De 2,5 a 3,5 días: el ritmo indulgente que se pidió."""
    frágil = sim.horas_de_vida(10)   # Chispa recién nacida
    sana = sim.horas_de_vida(21)     # Brote sano
    assert 60 <= frágil <= 64
    assert 84 <= sana <= 88


def test_el_hambre_baja_de_forma_lineal():
    c = criatura()
    mitad = sim.avanzar(c, T0 + timedelta(hours=sim.horas_de_vida(15) / 2))
    assert abs(mitad.hambre - 50.0) < 0.5


def test_muere_justo_al_agotarse_el_hambre():
    c = criatura()
    horas = sim.horas_de_vida(c.salud)

    antes = sim.avanzar(c, T0 + timedelta(hours=horas - 0.5))
    assert antes.viva
    assert antes.hambre > 0

    despues = sim.avanzar(c, T0 + timedelta(hours=horas + 0.5))
    assert not despues.viva
    assert despues.causa_muerte == "hambre"
    assert despues.hambre == 0.0


def test_momento_de_muerte_coincide_con_la_simulacion():
    """La fecha guardada en la BD tiene que cuadrar con lo que hace `avanzar`,
    porque el bucle de muerte se fía de ella."""
    c = criatura(hambre=42.0)
    momento = sim.momento_de_muerte(c)

    assert sim.avanzar(c, momento - timedelta(minutes=1)).viva
    assert not sim.avanzar(c, momento + timedelta(minutes=1)).viva


def test_avanzar_en_dos_tramos_da_lo_mismo_que_en_uno():
    c = criatura()
    de_una = sim.avanzar(c, T0 + timedelta(hours=10))
    en_dos = sim.avanzar(sim.avanzar(c, T0 + timedelta(hours=4)), T0 + timedelta(hours=10))
    assert abs(de_una.hambre - en_dos.hambre) < 0.01
    assert abs(de_una.limpieza - en_dos.limpieza) < 0.01


def test_una_criatura_muerta_ya_no_cambia():
    muerta = criatura(muerta_en=T0, causa_muerte="hambre", hambre=0.0)
    assert sim.avanzar(muerta, T0 + timedelta(days=30)) == muerta


def test_la_suciedad_amarga_el_animo_pero_no_mata():
    limpia = criatura(limpieza=100.0)
    sucia = criatura(limpieza=10.0)
    horas = timedelta(hours=10)

    a = sim.avanzar(limpia, T0 + horas)
    b = sim.avanzar(sucia, T0 + horas)

    assert b.animo < a.animo
    # Lo que no puede hacer la suciedad es tocar el hambre: si lo hiciera, la
    # hora de la muerte dejaría de ser predecible.
    assert abs(a.hambre - b.hambre) < 0.001


# --- Aviso de hambre -------------------------------------------------------

def test_el_aviso_salta_al_llegar_al_umbral():
    c = criatura()
    momento = sim.momento_de_aviso(c)

    antes = sim.avanzar(c, momento - timedelta(minutes=5))
    assert antes.hambre > sim.UMBRAL_AVISO_HAMBRE

    despues = sim.avanzar(c, momento + timedelta(minutes=5))
    assert despues.hambre <= sim.UMBRAL_AVISO_HAMBRE
    assert despues.viva


def test_el_aviso_deja_margen_de_reaccion():
    """Al 10% de comida queda el 10% de la vida: horas, no minutos."""
    c = criatura()
    margen = sim.momento_de_muerte(c) - sim.momento_de_aviso(c)
    assert margen > timedelta(hours=5)


def test_si_ya_esta_por_debajo_el_aviso_es_inmediato():
    c = criatura(hambre=3.0)
    assert sim.momento_de_aviso(c) == c.actualizada_en


def test_alimentarla_rearma_el_aviso():
    hambrienta = criatura(hambre=5.0, avisada=True)
    llena = sim.aplicar_accion(hambrienta, sim.ALIMENTAR, T0).criatura
    assert not llena.avisada
    assert llena.hambre > sim.UMBRAL_AVISO_HAMBRE


def test_las_demas_acciones_no_rearman_el_aviso():
    """Sólo alimentar sube la comida; jugar o entrenar la bajan todavía más."""
    for accion in (sim.JUGAR, sim.ENTRENAR, sim.LIMPIAR):
        c = criatura(hambre=8.0, avisada=True)
        assert sim.aplicar_accion(c, accion, T0).criatura.avisada, accion


# --- Etapas y cara ---------------------------------------------------------

def test_la_etapa_sale_del_nivel():
    """La etapa no se guarda: es una consecuencia del nivel, así que no puede
    desincronizarse con él."""
    for nivel, etapa in enumerate(esp.ETAPAS, start=1):
        assert criatura(nivel=nivel).etapa == etapa


def test_a_partir_del_ultimo_nivel_la_etapa_ya_no_cambia():
    assert criatura(nivel=5).etapa == esp.ADULTO_GRANDE
    assert criatura(nivel=12).etapa == esp.ADULTO_GRANDE


def test_la_edad_ya_no_decide_la_etapa():
    """Antes bastaba con esperar 24 h. Ahora hay que cuidarla."""
    vieja_sin_cuidar = criatura(nivel=1, nacida_en=T0 - timedelta(days=30))
    assert vieja_sin_cuidar.etapa == esp.BEBE


def test_la_cara_refleja_como_esta():
    assert criatura(hambre=90, animo=90).animo_visual == esp.FELIZ
    assert criatura(hambre=50, animo=50).animo_visual == esp.NORMAL
    assert criatura(hambre=10, animo=90).animo_visual == esp.MAL
    assert criatura(hambre=90, animo=10).animo_visual == esp.MAL


# --- Stats -----------------------------------------------------------------

def test_el_entrenamiento_tiene_rendimientos_decrecientes():
    assert sim.stat_final(10, 0, 0) == 10
    assert sim.stat_final(10, 1, 0) == 11
    assert sim.stat_final(10, 3, 0) == 11    # aún no llega al segundo punto
    assert sim.stat_final(10, 4, 0) == 12
    assert sim.stat_final(10, 9, 0) == 13
    assert sim.stat_final(10, 100, 0) == 20  # 100 sesiones para +10


def test_el_bonus_de_nivel_suma_entero():
    assert sim.stat_final(10, 0, 3) == 13


def test_las_estadisticas_tienen_techo():
    """Sin tope crecerían hasta desbordar el marco, que es de tres cifras."""
    assert sim.stat_final(30, 1_000_000, 5000) == sim.MAXIMO_STAT
    assert sim.stat_final(sim.MAXIMO_STAT, 0, 1) == sim.MAXIMO_STAT
    assert sim.MAXIMO_STAT == 999


def test_el_techo_no_toca_nada_por_debajo_de_el():
    """Lo que se ve jugando no cambia: una criatura veterana anda por 20."""
    assert sim.stat_final(sim.MAXIMO_STAT - 1, 0, 0) == sim.MAXIMO_STAT - 1
    assert sim.stat_final(15, 100, 4) == 29


def test_el_techo_lo_respetan_las_tres_estadisticas():
    """Se topa en `stat_final()`, el embudo por el que pasan las tres, para no
    tener que acordarse del tope en cada propiedad."""
    bestia = criatura(
        base_fuerza=900, base_velocidad=900, base_salud=900,
        ent_fuerza=10_000, ent_velocidad=10_000, ent_salud=10_000,
        niv_fuerza=500, niv_velocidad=500, niv_salud=500,
    )
    assert (bestia.fuerza, bestia.velocidad, bestia.salud) == (
        sim.MAXIMO_STAT, sim.MAXIMO_STAT, sim.MAXIMO_STAT
    )


# --- XP y niveles ----------------------------------------------------------

def test_la_curva_cumple_lo_prometido():
    """Un día para la primera evolución, un mes para la última, sobre unos
    30 XP diarios de juego atento."""
    # Una rutina diaria normal (5 comidas, 5 juegos, 4 entrenamientos) da 27 XP,
    # así que el primer escalón tiene que caer por debajo de eso.
    assert sim.xp_para_subir(1) <= 27
    assert sim.xp_acumulada_para(5) == 900                 # ~30 días
    # Y va costando más cada vez, nunca menos.
    costes = [sim.xp_para_subir(n) for n in range(1, 5)]
    assert costes == sorted(costes)


def test_pasado_el_ultimo_nivel_se_sigue_subiendo():
    assert sim.xp_para_subir(9) == sim.COSTE_XP_EXTRA


def test_sube_de_nivel_al_acumular_xp():
    c = criatura()
    subida, cambios = sim.aplicar_xp(c, sim.xp_para_subir(1), random.Random(1))
    assert subida.nivel == 2
    assert subida.xp == 0
    assert len(cambios) == sim.puntos_al_subir(2)


def test_las_evoluciones_tardias_dan_mas_puntos():
    """Llegar arriba tiene que notarse más que el primer escalón."""
    puntos = [sim.puntos_al_subir(n) for n in range(2, 6)]
    assert puntos == sorted(puntos)
    assert sum(puntos) == 14


def test_un_golpe_grande_de_xp_puede_subir_varios_niveles():
    c = criatura()
    subida, cambios = sim.aplicar_xp(c, 900, random.Random(1))
    assert subida.nivel == 5
    assert len(cambios) == sum(sim.puntos_al_subir(n) for n in range(2, 6))


def test_los_puntos_repartidos_cuadran_con_las_subidas():
    c = criatura()
    subida, cambios = sim.aplicar_xp(c, 900, random.Random(5))
    total = subida.niv_fuerza + subida.niv_velocidad + subida.niv_salud
    assert total == len(cambios)


def test_evolucionar_alarga_la_vida():
    """Parte de los puntos van a salud, así que aguanta más sin comer: era el
    otro efecto que se pedía de la evolución."""
    bebe = criatura(especie="brote")
    mayor, _ = sim.aplicar_xp(bebe, 900, random.Random(2))
    assert sim.horas_de_vida(mayor.salud) > sim.horas_de_vida(bebe.salud)


def test_las_subidas_siguen_el_perfil_de_la_especie():
    """Un Pollito (vel 14 / fue 4) debe mejorar mucho más en velocidad."""
    rng = random.Random(11)
    c = criatura(especie="pollito")
    subida, _ = sim.aplicar_xp(c, 5_000, rng)
    assert subida.niv_velocidad > subida.niv_fuerza


# --- Acciones de cuidado ---------------------------------------------------

def test_alimentar_llena_y_entrena_salud():
    c = criatura(hambre=40.0)
    r = sim.aplicar_accion(c, sim.ALIMENTAR, T0)
    assert r.ok
    assert r.criatura.hambre == 70.0
    assert r.criatura.ent_salud == 1


def test_alimentar_estando_lleno_provoca_empacho():
    c = criatura(hambre=95.0, animo=80.0)
    r = sim.aplicar_accion(c, sim.ALIMENTAR, T0)
    assert r.criatura.animo == 65.0
    assert r.criatura.ent_salud == 0  # el empacho no entrena nada
    assert "empach" in r.mensaje.lower()


def test_ninguna_barra_se_pasa_de_cien_ni_baja_de_cero():
    llena = sim.aplicar_accion(criatura(hambre=100.0, animo=50.0), sim.JUGAR, T0)
    assert llena.criatura.animo == 75.0

    vacia = sim.aplicar_accion(criatura(hambre=5.0, animo=5.0), sim.ENTRENAR, T0)
    assert vacia.criatura.hambre == 0.0
    assert vacia.criatura.animo == 0.0


def test_cuidar_da_experiencia():
    """Quien no quiera competir tiene que poder ver crecer a su criatura."""
    for accion, esperado in ((sim.ALIMENTAR, 1), (sim.JUGAR, 2), (sim.ENTRENAR, 3)):
        r = sim.aplicar_accion(criatura(hambre=50.0, animo=50.0), accion, T0)
        assert r.criatura.xp == esperado, accion


def test_limpiar_y_actualizar_no_dan_experiencia():
    for accion in (sim.LIMPIAR, sim.ACTUALIZAR):
        r = sim.aplicar_accion(criatura(limpieza=10.0), accion, T0)
        assert r.criatura.xp == 0, accion


def test_competir_sigue_siendo_lo_mas_rentable():
    """Si cuidar rindiera más que competir, las carreras se quedarían
    decorativas ahora que también se sube de nivel cuidando."""
    assert sim.XP_VICTORIA > max(sim.XP_POR_CUIDADO.values())


def test_cuidar_puede_disparar_una_evolucion():
    apunto = criatura(xp=sim.xp_para_subir(1) - 1, hambre=50.0)
    r = sim.aplicar_accion(apunto, sim.JUGAR, T0, random.Random(1))
    assert r.evoluciono
    assert r.etapa_anterior == esp.BEBE
    assert r.criatura.etapa == esp.NINO
    assert r.subidas


def test_una_accion_normal_no_dice_que_hubo_evolucion():
    r = sim.aplicar_accion(criatura(hambre=50.0), sim.JUGAR, T0, random.Random(1))
    assert not r.evoluciono


def test_jugar_y_entrenar_entrenan_lo_suyo():
    jugado = sim.aplicar_accion(criatura(), sim.JUGAR, T0).criatura
    assert jugado.ent_velocidad == 1

    entrenado = sim.aplicar_accion(criatura(), sim.ENTRENAR, T0).criatura
    assert entrenado.ent_fuerza == 2


def test_entrenar_cuesta_hambre_y_animo():
    c = criatura(hambre=80.0, animo=80.0)
    r = sim.aplicar_accion(c, sim.ENTRENAR, T0)
    assert r.criatura.hambre == 65.0
    assert r.criatura.animo == 70.0


# --- Alimentar de urgencia -------------------------------------------------

def test_con_hambre_se_puede_alimentar_sin_esperar():
    """Ver a tu criatura en rojo y que el bot te diga que esperes es absurdo."""
    assert sim.puede_saltarse_espera(criatura(hambre=59.0), sim.ALIMENTAR)
    assert sim.puede_saltarse_espera(criatura(hambre=25.0), sim.ALIMENTAR)
    assert sim.puede_saltarse_espera(criatura(hambre=0.0), sim.ALIMENTAR)


def test_estando_bien_el_enfriamiento_manda():
    assert not sim.puede_saltarse_espera(criatura(hambre=60.0), sim.ALIMENTAR)
    assert not sim.puede_saltarse_espera(criatura(hambre=90.0), sim.ALIMENTAR)


def test_el_salto_es_solo_para_alimentar():
    """Jugar o entrenar con la criatura famélica no es ninguna urgencia."""
    famelica = criatura(hambre=5.0)
    for accion in (sim.JUGAR, sim.ENTRENAR, sim.LIMPIAR, sim.ACTUALIZAR):
        assert not sim.puede_saltarse_espera(famelica, accion), accion


def test_la_cadena_de_urgencia_esta_acotada():
    """Desde 0 son dos alimentadas y se acaba: 0 -> 30 -> 60. Sin bucle."""
    c = criatura(hambre=0.0)
    saltos = 0
    while sim.puede_saltarse_espera(c, sim.ALIMENTAR) and saltos < 10:
        c = sim.aplicar_accion(c, sim.ALIMENTAR, T0).criatura
        saltos += 1
    assert saltos == 2
    assert c.hambre >= sim.UMBRAL_BARRA_BIEN


def test_limpiar_deja_el_aseo_a_tope():
    r = sim.aplicar_accion(criatura(limpieza=3.0), sim.LIMPIAR, T0)
    assert r.criatura.limpieza == 100.0


def test_actualizar_no_cambia_nada():
    c = criatura(hambre=55.0)
    r = sim.aplicar_accion(c, sim.ACTUALIZAR, T0)
    assert r.criatura == c


def test_no_se_puede_cuidar_a_una_criatura_muerta():
    muerta = criatura(muerta_en=T0, causa_muerte="hambre")
    r = sim.aplicar_accion(muerta, sim.ALIMENTAR, T0)
    assert not r.ok
    assert r.criatura == muerta


# --- Concordancia de los avisos --------------------------------------------

def test_ningun_aviso_sale_con_marcas_sin_resolver():
    """El equivalente al test que ya cubre los prompts. Una marca «{o/a}» que
    se escape sale tal cual en la pantalla de Discord."""
    for genero in esp.GENEROS:
        for accion in (*sim.ACCIONES_DE_CUIDADO, sim.ACTUALIZAR):
            for hambre in (95.0, 50.0):  # 95 dispara el empacho al alimentar
                r = sim.aplicar_accion(
                    criatura(genero=genero, hambre=hambre), accion, T0)
                assert "{" not in r.mensaje, (accion, genero, r.mensaje)
                assert "}" not in r.mensaje, (accion, genero, r.mensaje)

    # También el de la criatura muerta, que va por otra rama.
    muerta = criatura(muerta_en=T0, causa_muerte="hambre")
    assert "{" not in sim.aplicar_accion(muerta, sim.ALIMENTAR, T0).mensaje


def test_los_avisos_concuerdan_con_el_genero():
    """Regresión de lo que se vio en Discord: a Juan III, que es macho, jugar
    con él le contestaba «Está encantada»."""
    casos = (
        (sim.JUGAR, "encantado", "encantada"),
        (sim.ENTRENAR, "molido", "molida"),
        (sim.LIMPIAR, "nuevo", "nueva"),
    )
    for accion, en_macho, en_hembra in casos:
        el = sim.aplicar_accion(criatura(genero=esp.MACHO), accion, T0)
        ella = sim.aplicar_accion(criatura(genero=esp.HEMBRA), accion, T0)
        assert en_macho in el.mensaje, (accion, el.mensaje)
        assert en_hembra in ella.mensaje, (accion, ella.mensaje)


def test_el_aviso_se_concuerda_lo_construya_quien_lo_construya():
    """La concordancia vive en el constructor, no en cada `return`: es lo que
    evita que el próximo aviso que se añada vuelva a salir en femenino fijo."""
    suelto = sim.ResultadoAccion(criatura(genero=esp.HEMBRA), "Está cansad{o/a}.")
    assert suelto.mensaje == "Está cansada."

    # Y pasar dos veces por el constructor no rompe el texto ya resuelto.
    from dataclasses import replace
    assert replace(suelto, ok=True).mensaje == "Está cansada."


# --- Los enfriamientos no pueden sincronizarse -----------------------------

def enfriamientos_reales() -> dict:
    """Los que hacen esperar. `ACTUALIZAR` es gratis y queda fuera."""
    return {a: c for a, c in sim.COOLDOWNS.items() if c > timedelta(0)}


def test_no_hay_dos_enfriamientos_iguales():
    valores = list(enfriamientos_reales().values())
    assert len(set(valores)) == len(valores), sim.COOLDOWNS


def test_ningun_enfriamiento_es_multiplo_de_otro():
    """Si uno es múltiplo de otro, sus ciclos coinciden para siempre y las
    acciones se liberan siempre en bloque. Con los 30/30/60/120 de antes,
    las 48 veces del día se juntaban dos o más y luego había media hora
    muerta. Elegirlos primos es la forma barata de garantizarlo."""
    minutos = {a: int(c.total_seconds() // 60)
               for a, c in enfriamientos_reales().items()}
    for a, ca in minutos.items():
        for b, cb in minutos.items():
            if a == b:
                continue
            assert ca % cb != 0, (
                f"{a} ({ca} min) es múltiplo de {b} ({cb} min): "
                "van a caer siempre juntos"
            )


def test_el_enfriamiento_de_competir_ata_mas_que_el_hambre():
    """Lo que le da sentido al objeto que reinicia esta espera.

    Hay dos cosas que topan cuánto se puede competir: este enfriamiento y el
    hambre. Con los 3 minutos de antes ataba el hambre —7,8 peleas por hora
    frente a 20—, así que saltarse la espera no servía de nada. A 10 minutos son
    6 por hora y manda el enfriamiento, que es lo que se buscaba.

    Si alguien vuelve a bajarlo, este test avisa de que además está dejando el
    «Descanso rápido» sin utilidad.
    """
    minutos = sim.COOLDOWNS[sim.COMPETIR].total_seconds() / 60
    peleas_por_enfriamiento = 60 / minutos

    comidas_por_hora = 60 / (sim.COOLDOWNS[sim.ALIMENTAR].total_seconds() / 60)
    peleas_por_comida = 30 / sim.COSTE_HAMBRE_COMPETIR  # alimentar da +30
    peleas_por_hambre = comidas_por_hora * peleas_por_comida

    assert peleas_por_enfriamiento < peleas_por_hambre, (
        f"{peleas_por_enfriamiento:.1f} peleas/hora por enfriamiento contra "
        f"{peleas_por_hambre:.1f} por hambre: ata la comida, no la espera"
    )


def test_solo_actualizar_es_gratis():
    gratis = [a for a, c in sim.COOLDOWNS.items() if c == timedelta(0)]
    assert gratis == [sim.ACTUALIZAR]


def test_las_acciones_se_turnan_en_vez_de_amontonarse():
    """La medida de lo que se buscaba: un día de juego atento, contando
    cuántos momentos liberan dos acciones a la vez y cuál es el hueco más
    largo sin nada que hacer."""
    dia = 24 * 60
    momentos: dict[int, int] = {}
    for accion in sim.ACCIONES_DE_CUIDADO:
        paso = int(sim.COOLDOWNS[accion].total_seconds() // 60)
        for t in range(paso, dia + 1, paso):
            momentos[t] = momentos.get(t, 0) + 1

    puntos = sorted(momentos)
    amontonados = sum(1 for t in puntos if momentos[t] > 1)
    mayor_hueco = max(b - a for a, b in zip([0] + puntos, puntos))

    assert amontonados < 5, f"{amontonados} momentos con acciones a la vez"
    assert mayor_hueco <= 25, f"{mayor_hueco} min sin nada que hacer"
