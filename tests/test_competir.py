"""Carreras, sumo y torneos: dados fijos y marcos que no se descuadran."""
import random
import re

import competir as comp
import especies as esp
import pantalla
import simulacion as sim

ANSI = re.compile(r"\x1b\[[0-9;]*m")


class DadosFijos(random.Random):
    """Dados guionizados: se recorren en orden y se repiten en bucle."""

    def __init__(self, valores):
        super().__init__()
        self.valores = list(valores)
        self.i = 0

    def randint(self, a, b):
        valor = self.valores[self.i % len(self.valores)]
        self.i += 1
        return valor

    def shuffle(self, x, *args, **kwargs):
        """El sorteo del torneo, también guionizado: no mezcla.

        Hace falta porque `random.Random.shuffle` no pasa por `randint` sino por
        `getrandbits`, que sigue siendo el del sistema: sin esto las parejas del
        torneo saldrían distintas en cada ejecución y ningún test del cuadro
        sería reproducible. Dejando el orden de invitación, la pareja de un test
        es la que se escribe.
        """
        return None


def competidor(nombre="A", especie="pulpo", stat=10, modificador=0,
               animo=esp.NORMAL):
    return comp.Competidor(nombre, especie, stat, modificador, animo)


def combate(competidores, tipo, rng):
    """Un encuentro de un solo combate: `(encuentro, su único Resultado)`."""
    encuentro = comp.enfrentar(competidores, tipo, rng)
    return encuentro, encuentro.combates[0]


def espera_error(competidores, tipo, motivo):
    try:
        comp.enfrentar(competidores, tipo, DadosFijos([10]))
    except ValueError:
        return
    raise AssertionError(motivo)


# --- Resolución ------------------------------------------------------------

def test_son_tres_tramos_y_cada_uno_es_stat_mas_1d20():
    a = competidor("A", stat=10)
    b = competidor("B", stat=5)
    # Los dados se reparten en orden: A, B, A, B...
    _, r = combate([a, b], comp.CARRERA, DadosFijos([20, 1]))

    assert len(r.rondas) == 3
    for ronda in r.rondas:
        assert ronda.totales == (10 + 20, 5 + 1)
    assert r.totales == (90, 18)
    assert r.orden == (0, 1)


def test_gana_quien_suma_mas_no_quien_gana_mas_tramos():
    """Con acumulado, una remontada en el último tramo puede darle la vuelta:
    es justo lo que hace que la animación tenga gracia."""
    a = competidor("A", stat=0)
    b = competidor("B", stat=0)
    # A: 20, 1, 1 = 22+3(base mínima) ... B: 1, 20, 20 = 41+3
    _, r = combate([a, b], comp.CARRERA, DadosFijos([20, 1, 1, 20, 1, 20]))
    assert r.orden[0] == 1
    assert r.competidor_ganador.nombre == "B"


def test_un_empate_se_desempata_con_tramos_extra():
    a = competidor("A", stat=10)
    b = competidor("B", stat=10)
    # Tres tramos idénticos -> empate; en el cuarto A saca más.
    dados = [5, 5, 5, 5, 5, 5, 20, 1]
    _, r = combate([a, b], comp.CARRERA, DadosFijos(dados))

    assert r.desempates == 1
    assert len(r.rondas) == 4
    assert r.orden[0] == 0


def test_los_desempates_tienen_tope():
    """Con dados siempre iguales el empate sería eterno: no puede colgarse."""
    a = competidor("A", stat=10)
    b = competidor("B", stat=10)
    _, r = combate([a, b], comp.SUMO, DadosFijos([7]))

    assert r.desempates == comp.MAX_DESEMPATES
    assert set(r.orden) == {0, 1}


def test_al_agotar_los_desempates_manda_el_orden_de_llegada():
    """Con todo empatado el orden lo decide el índice, que es el equivalente al
    «gana `a` los empates» de cuando la carrera era de dos."""
    cinco = [competidor(f"C{i}", stat=10) for i in range(5)]
    _, r = combate(cinco, comp.CARRERA, DadosFijos([7]))

    assert len(set(r.totales)) == 1, r.totales
    assert r.orden == (0, 1, 2, 3, 4)


def test_la_carrera_usa_velocidad_y_el_sumo_fuerza():
    criatura = sim.Criatura(
        id=1, usuario_id="u", guild_id="g", especie="pulpo", nombre="X",
        nacida_en=None, actualizada_en=None,
        base_fuerza=30, base_velocidad=5, base_salud=10,
        hambre=50.0, animo=50.0,
    )
    assert comp.competidor_de(criatura, comp.CARRERA).stat == 5
    assert comp.competidor_de(criatura, comp.SUMO).stat == 30


def test_el_bonus_de_una_pocion_llega_al_competidor():
    """La poción no cambia la estadística de la criatura: entra por el mismo
    sitio que el modificador de estado, que es lo que hace que siga topada por
    el dado y no por lo que uno gaste en la tienda."""
    criatura = sim.Criatura(
        id=1, usuario_id="u", guild_id="g", especie="pulpo", nombre="X",
        nacida_en=None, actualizada_en=None,
        base_fuerza=10, base_velocidad=10, base_salud=10,
        hambre=50.0, animo=50.0,
    )
    sin = comp.competidor_de(criatura, comp.CARRERA)
    con = comp.competidor_de(criatura, comp.CARRERA, bonus_objetos=7)

    assert con.modificador == sin.modificador + 7
    assert con.base == sin.base + 7
    assert con.stat == sin.stat, "la estadística de la criatura no se toca"


def test_sin_pocion_el_competidor_sale_igual_que_siempre():
    criatura = sim.Criatura(
        id=1, usuario_id="u", guild_id="g", especie="pulpo", nombre="X",
        nacida_en=None, actualizada_en=None,
        base_fuerza=10, base_velocidad=10, base_salud=10,
        hambre=50.0, animo=50.0,
    )
    assert comp.competidor_de(criatura, comp.SUMO) == \
        comp.competidor_de(criatura, comp.SUMO, bonus_objetos=0)


def test_el_competidor_se_lleva_la_cara_que_tiene_puesta():
    """La necesita el podio: sin ella habría que volver a la criatura, y este
    módulo es puro a propósito."""
    def criatura(hambre, animo):
        return sim.Criatura(
            id=1, usuario_id="u", guild_id="g", especie="pulpo", nombre="X",
            nacida_en=None, actualizada_en=None,
            base_fuerza=10, base_velocidad=10, base_salud=10,
            hambre=hambre, animo=animo,
        )

    contento = comp.competidor_de(criatura(90.0, 90.0), comp.CARRERA)
    hecho_polvo = comp.competidor_de(criatura(10.0, 10.0), comp.CARRERA)

    assert contento.cara == esp.ESPECIES["pulpo"].caras[esp.FELIZ]
    assert hecho_polvo.cara == esp.ESPECIES["pulpo"].caras[esp.MAL]


# --- Cuántos caben ---------------------------------------------------------

def test_una_carrera_admite_hasta_cinco():
    cinco = [competidor(f"C{i}", stat=10 + i) for i in range(comp.MAX_CORREDORES)]
    e, r = combate(cinco, comp.CARRERA, DadosFijos([10, 11, 12, 13, 14]))

    assert len(r.competidores) == 5
    assert len(e.orden) == 5
    for ronda in r.rondas:
        assert len(ronda.dados) == 5 and len(ronda.totales) == 5

    # Cinco pistas y cinco filas de dado en cada fotograma.
    for fotograma in comp.fotogramas_de(e)[0]:
        ls = lineas(fotograma)
        assert sum(1 for ln in ls if ">" in ln) == 5, ls
        assert sum(1 for ln in ls if "+d20" in ln) == 5, ls


def test_no_caben_mas_de_cinco():
    espera_error([competidor(f"C{i}") for i in range(6)], comp.CARRERA,
                 "una carrera de seis debería estar prohibida")


def test_hacen_falta_dos_para_competir():
    espera_error([competidor("Solo")], comp.CARRERA,
                 "una carrera de uno debería estar prohibida")


def test_solo_caben_dos_o_cuatro_en_el_sumo():
    """El sumo es un forcejeo: de dos, o de cuatro en torneo. Con tres no hay
    forma de emparejar sin que alguien pelee solo o dos veces."""
    espera_error([competidor(f"C{i}") for i in range(3)], comp.SUMO,
                 "un sumo de tres debería estar prohibido")
    espera_error([competidor(f"C{i}") for i in range(5)], comp.SUMO,
                 "un sumo de cinco debería estar prohibido")

    # Y los dos que sí valen no levantan nada.
    for cuantos in (2, 4):
        comp.enfrentar([competidor(f"C{i}", stat=10 + i) for i in range(cuantos)],
                       comp.SUMO, DadosFijos([20, 1]))


def test_la_clasificacion_va_del_primero_al_ultimo():
    cinco = [competidor(f"C{i}", stat=0) for i in range(5)]
    # Un dado fijo por competidor y por tramo: C4 saca 20 siempre, C0 saca 1.
    e, _ = combate(cinco, comp.CARRERA, DadosFijos([1, 5, 10, 15, 20]))

    nombres = [c.nombre for c, _ in e.clasificacion]
    assert nombres == ["C4", "C3", "C2", "C1", "C0"]

    marcadores = [marcador for _, marcador in e.clasificacion]
    assert marcadores == sorted(marcadores, reverse=True)
    assert e.campeon.nombre == "C4"


def test_un_empate_entre_cinco_se_desempata():
    cinco = [competidor(f"C{i}", stat=10) for i in range(5)]
    # Cinco iguales tres tramos; en el cuarto se rompe el empate del todo.
    dados = [7] * 15 + [1, 2, 3, 4, 5]
    _, r = combate(cinco, comp.CARRERA, DadosFijos(dados))

    assert r.desempates == 1
    assert len(set(r.totales)) == 5, r.totales


# --- El torneo -------------------------------------------------------------

def torneo_guionizado():
    """Cuatro al sumo con dados fijos, sin sorteo: parejas (C0,C1) y (C2,C3).

    C0 y C2 saca 20 siempre y sus rivales 1, así que C0 gana su semifinal, C2 la
    suya y C0 la final. Los eliminados quedan por lo que sumaron: C3 (42) sobre
    C1 (36).
    """
    cuatro = [competidor(f"C{i}", stat=10 + i) for i in range(4)]
    return comp.enfrentar(cuatro, comp.SUMO, DadosFijos([20, 1]))


def test_el_sumo_de_cuatro_es_un_torneo_de_tres_combates():
    e = torneo_guionizado()
    assert len(e.combates) == 3

    semi1, semi2, final = e.combates
    assert [c.nombre for c in semi1.competidores] == ["C0", "C1"]
    assert [c.nombre for c in semi2.competidores] == ["C2", "C3"]
    assert [c.nombre for c in final.competidores] == ["C0", "C2"]


def test_el_sumo_de_dos_sigue_siendo_un_solo_combate():
    e = comp.enfrentar([competidor("A", stat=10), competidor("B", stat=5)],
                       comp.SUMO, DadosFijos([20, 1]))
    assert len(e.combates) == 1


def test_la_carrera_sigue_siendo_un_solo_combate():
    """Aunque corran cinco: en una carrera se enfrentan todos a la vez."""
    for cuantos in range(2, comp.MAX_CORREDORES + 1):
        e = comp.enfrentar(
            [competidor(f"C{i}", stat=10 + i) for i in range(cuantos)],
            comp.CARRERA, DadosFijos([10, 11, 12, 13, 14]),
        )
        assert len(e.combates) == 1, cuantos


def test_quien_pierde_la_semifinal_no_llega_a_la_final():
    e = torneo_guionizado()
    final = e.combates[-1]
    perdedores = {e.combates[0].competidor_perdedor.nombre,
                  e.combates[1].competidor_perdedor.nombre}

    assert perdedores == {"C1", "C3"}
    for c in final.competidores:
        assert c.nombre not in perdedores, c.nombre


def test_el_campeon_es_quien_gana_la_final():
    e = torneo_guionizado()
    assert e.campeon.nombre == "C0"
    assert e.campeon is e.combates[-1].competidor_ganador


def test_el_orden_del_torneo_es_campeon_finalista_y_los_de_semis():
    """Los dos que caen en semifinales no pelean por el bronce, así que se
    ordenan entre sí por lo que sumaron: mejor marcador, mejor puesto."""
    e = torneo_guionizado()
    assert [c.nombre for c, _ in e.clasificacion] == ["C0", "C2", "C3", "C1"]

    marcadores = dict(e.clasificacion)
    # A cada uno se le apunta el marcador de su última pelea.
    assert marcadores[e.competidores[1]] == 36   # C1, su semifinal
    assert marcadores[e.competidores[3]] == 42   # C3, su semifinal


def test_el_sorteo_mezcla_las_parejas():
    """Lo que distingue un sorteo de haber dejado el orden de invitación: a la
    larga cada uno se cruza con todos, así que en la primera semifinal tienen que
    llegar a salir las seis parejas posibles."""
    from itertools import combinations

    cuatro = [competidor(f"C{i}", stat=10 + i) for i in range(4)]
    rng = random.Random(1)

    vistas = set()
    for _ in range(200):
        e = comp.enfrentar(cuatro, comp.SUMO, rng)
        vistas.add(frozenset(c.nombre for c in e.combates[0].competidores))

    posibles = {frozenset(p) for p in combinations([c.nombre for c in cuatro], 2)}
    assert len(posibles) == 6
    assert vistas == posibles, sorted(map(sorted, posibles - vistas))


def test_el_reto_se_anuncia_segun_lo_que_sea():
    assert comp.como_se_llama(comp.CARRERA, 2) == "una CARRERA"
    assert comp.como_se_llama(comp.CARRERA, 5) == "una CARRERA"
    assert comp.como_se_llama(comp.SUMO, 2) == "un SUMO"
    assert comp.como_se_llama(comp.SUMO, 4) == "un TORNEO DE SUMO"


def test_el_torneo_solo_cuenta_una_vez_para_cada_uno():
    """Los finalistas pelean dos veces pero el encuentro es uno: el cog reparte
    coste y XP con `orden`, y ahí cada dorsal aparece exactamente una vez."""
    e = torneo_guionizado()
    assert sorted(e.orden) == [0, 1, 2, 3]


# --- Modificadores ---------------------------------------------------------

def test_el_estado_modifica_poco_comparado_con_el_d20():
    assert comp.modificador_por_estado(hambre=80, animo=80) == 2
    assert comp.modificador_por_estado(hambre=80, animo=50) == 0
    assert comp.modificador_por_estado(hambre=80, animo=10) == -2
    assert comp.modificador_por_estado(hambre=10, animo=10) == -5
    # El rango total (7 puntos) es menor que el del dado (19): el azar manda.
    assert 7 < comp.CARA_DADO - 1


def test_una_criatura_hecha_polvo_sigue_aportando_algo():
    debil = competidor(stat=1, modificador=-5)
    assert debil.base == 1


# --- Narración -------------------------------------------------------------

def lineas(texto: str) -> list[str]:
    dentro = texto.split("```ansi\n")[1].split("\n```")[0]
    return ANSI.sub("", dentro).split("\n")


def test_hay_un_fotograma_por_tramo():
    e, r = combate([competidor("A"), competidor("B")], comp.CARRERA,
                   DadosFijos([20, 1]))
    assert len(comp.fotogramas_de(e)[0]) == len(r.rondas)


def test_el_torneo_se_anima_combate_por_combate_y_con_su_ronda():
    e = torneo_guionizado()
    tandas = comp.fotogramas_de(e)

    assert len(tandas) == 3
    titulos = [lineas(tanda[0])[1] for tanda in tandas]
    assert "SEMIFINAL 1" in titulos[0]
    assert "SEMIFINAL 2" in titulos[1]
    assert "FINAL" in titulos[2]


def test_un_combate_suelto_se_titula_con_su_modalidad():
    for tipo in (comp.CARRERA, comp.SUMO):
        e, _ = combate([competidor("A"), competidor("B")], tipo,
                       DadosFijos([20, 1]))
        assert comp.NOMBRES[tipo] in lineas(comp.fotogramas_de(e)[0][0])[1]


def test_los_marcos_de_competencia_nunca_se_descuadran():
    """Con campos de dos a cinco y con torneos: las filas del corredor y del dado
    se montan a mano por el color, así que pasarse de ancho no recorta, rompe el
    marco."""
    rng = random.Random(0)
    for cuantos in range(2, comp.MAX_CORREDORES + 1):
        tipos = [comp.CARRERA]
        if cuantos in comp.CUANTOS_CABEN[comp.SUMO]:
            tipos.append(comp.SUMO)
        for tipo in tipos:
            for _ in range(40):
                corredores = [
                    competidor(
                        nombre=rng.choice(["Bartolomeo", "Yo", "X" * 24]),
                        especie=rng.choice(list(esp.ESPECIES)),
                        stat=rng.randint(1, sim.MAXIMO_STAT),
                        modificador=rng.randint(-5, 2),
                        animo=rng.choice(esp.ANIMOS),
                    )
                    for _ in range(cuantos)
                ]
                e = comp.enfrentar(corredores, tipo, rng)
                for tanda in comp.fotogramas_de(e):
                    for fotograma in tanda:
                        for linea in lineas(fotograma):
                            assert len(linea) == pantalla.ANCHO + 2, repr(linea)


def test_la_fila_del_corredor_aguanta_marcadores_de_cuatro_cifras():
    """Regresión: esta fila se monta a mano por el color de la pista, así que
    pasarse de ancho no recorta, rompe el marco. Con la estadística al tope los
    marcadores llegan a cuatro cifras (3 tramos de ~1000).

    El modificador va a +2 a propósito: `base` puede pasar del tope aunque la
    estadística esté topada, así que los anchos no pueden darlo por hecho."""
    a = competidor("Bartolomeo", stat=sim.MAXIMO_STAT, modificador=2)
    b = competidor("Yo", stat=sim.MAXIMO_STAT, modificador=2)
    for tipo in (comp.CARRERA, comp.SUMO):
        e, r = combate([a, b], tipo, DadosFijos([20, 19]))
        assert r.totales[0] > 999, r.totales  # si no, el test no prueba nada
        for fotograma in comp.fotogramas_de(e)[0]:
            for linea in lineas(fotograma):
                assert len(linea) == pantalla.ANCHO + 2, repr(linea)


def test_las_columnas_del_dado_no_bailan_entre_las_filas():
    """Los anchos se miden sobre el combate entero, no fila a fila: si cada una
    midiera lo suyo, con un competidor a 9 y otro a 240 el `+d20` de arriba no
    caería en la misma columna que el de abajo."""
    for tipo in (comp.CARRERA, comp.SUMO):
        e, _ = combate([competidor("Aaa", stat=9), competidor("Bbb", stat=240)],
                       tipo, DadosFijos([20, 19]))
        for fotograma in comp.fotogramas_de(e)[0]:
            filas = [ln for ln in lineas(fotograma) if "+d20" in ln]
            assert len(filas) == 2
            assert filas[0].index("+d20") == filas[1].index("+d20"), filas
            assert filas[0].index(" = ") == filas[1].index(" = "), filas


def test_las_columnas_del_dado_cuadran_tambien_con_cinco():
    corredores = [competidor(f"C{i}", stat=9 * 10 ** (i % 3)) for i in range(5)]
    e, _ = combate(corredores, comp.CARRERA, DadosFijos([20, 19, 18, 17, 16]))
    for fotograma in comp.fotogramas_de(e)[0]:
        filas = [ln for ln in lineas(fotograma) if "+d20" in ln]
        assert len(filas) == 5
        assert len({f.index("+d20") for f in filas}) == 1, filas
        assert len({f.index(" = ") for f in filas}) == 1, filas


def test_un_combate_normal_se_dibuja_igual_que_siempre():
    """El ancho se calcula, pero el caso corriente no puede cambiar: los
    mínimos (2 para la base, 3 para el total) son los de toda la vida."""
    e, _ = combate([competidor("Bartolomeo", stat=22, modificador=2),
                    competidor("Yo", stat=19)], comp.CARRERA,
                   DadosFijos([20, 19]))
    filas = [ln for ln in lineas(comp.fotogramas_de(e)[0][0]) if "+d20" in ln]
    assert filas[0] == "│ Bartolo 24+d20 20 =  44  │"
    assert filas[1] == "│ Yo      19+d20 19 =  38  │"


def test_el_total_del_tramo_se_ve_entero():
    """Regresión: la fila del dado se pasaba de ancho y se recortaba justo el
    total, que es el número que importa."""
    for stat in (99, sim.MAXIMO_STAT):
        a = competidor("Bartolomeo", stat=stat, modificador=2)
        e, r = combate([a, competidor("B", stat=stat)], comp.SUMO,
                       DadosFijos([20, 19]))
        primera = lineas(comp.fotogramas_de(e)[0][0])
        fila_dado = next(ln for ln in primera if "+d20" in ln)
        assert str(r.rondas[0].totales[0]) in fila_dado, (stat, fila_dado)
        assert f"{a.base}+d20" in fila_dado, (stat, fila_dado)


def test_el_ganador_llega_a_la_meta_en_la_carrera():
    a = competidor("A", stat=30)
    e, _ = combate([a, competidor("B", stat=1)], comp.CARRERA,
                   DadosFijos([20, 1]))
    ultimo = lineas(comp.fotogramas_de(e)[0][-1])
    fila_ganador = ultimo[3]  # cabecera(3 líneas) -> primer corredor
    assert fila_ganador.count("=") == comp.ANCHO_PISTA


def test_en_el_sumo_la_marca_se_mueve_progresivamente():
    """Regresión: normalizando contra la diferencia final, la marca saltaba al
    extremo en cuanto alguien se adelantaba y se quedaba clavada."""
    a = competidor("A", stat=10)
    b = competidor("B", stat=10)
    e, _ = combate([a, b], comp.SUMO, DadosFijos([12, 8]))  # A gana 4 por tramo

    posiciones = []
    for fotograma in comp.fotogramas_de(e)[0]:
        fila = next(ln for ln in lineas(fotograma) if ln.count("(") and "O" in ln)
        posiciones.append(fila.index("O"))

    assert posiciones == sorted(posiciones)
    assert len(set(posiciones)) > 1, posiciones


# --- El podio --------------------------------------------------------------

def carrera_de(cuantos, **kwargs):
    corredores = [
        competidor(f"C{i}", stat=cuantos - i, **kwargs) for i in range(cuantos)
    ]
    return comp.enfrentar(corredores, comp.CARRERA, DadosFijos([10]))


def test_con_dos_no_hay_podio_sino_la_linea_de_siempre():
    """El 1 contra 1 tiene que quedar igual que antes: no hay tres mejores."""
    texto = comp.resumen(carrera_de(2))
    assert "```" not in texto
    assert "🥇" not in texto
    assert "gana a" in texto


def test_el_resumen_nombra_al_ganador():
    e = comp.enfrentar([competidor("Pelusa", stat=30), competidor("Slimy", stat=1)],
                       comp.CARRERA, DadosFijos([20, 1]))
    texto = comp.resumen(e)
    assert "Pelusa" in texto and "Slimy" in texto
    assert str(e.combates[0].totales[0]) in texto


def test_con_tres_o_mas_el_resumen_es_el_podio():
    for cuantos in (3, 4, 5):
        assert comp.resumen(carrera_de(cuantos)) == comp.podio(carrera_de(cuantos))


def test_el_podio_dibuja_a_los_tres_de_arriba():
    e = carrera_de(5)
    texto = comp.podio(e)

    # Las medallas van FUERA del bloque: dentro Discord las convierte en
    # imágenes de ancho variable y descuadra el marco.
    cabecera = texto.split("```ansi")[0]
    assert "🥇" in cabecera and "🥈" in cabecera and "🥉" in cabecera
    dentro = "\n".join(lineas(texto))
    assert "🥇" not in dentro

    for puesto, (c, _) in enumerate(e.clasificacion[:3], start=1):
        assert c.nombre in cabecera, c.nombre
        assert f"│ {puesto} │" in dentro, (puesto, dentro)

    # Los cinco salen en la lista de abajo, no sólo los del podio.
    for c, marcador in e.clasificacion:
        assert c.nombre in dentro and str(marcador) in dentro


def _donde_esta_el_cajon(ls: list[str], puesto: int) -> tuple[int, int]:
    """Fila y columna del `│ n │` de un puesto dentro del dibujo."""
    marca = f"│ {puesto} │"
    fila = next(i for i, ln in enumerate(ls) if marca in ln)
    return fila, ls[fila].index(marca)


def test_cada_gachamon_va_encima_de_su_cajon():
    """Lo que se pidió: el gachamón subido a SU cajón. Un descuadre de una sola
    columna se ve a simple vista en Discord, así que se comprueba por posición:
    encima del número va el techo del cajón, y encima del techo la cara, las tres
    piezas empezando en la misma columna.

    Se prueban las veinticinco porque la cara la pone la especie, y con caras
    de distinto ancho el dibujo se torcería. (Hoy las 25 miden 3, y hay un test
    en `test_especies.py` que lo vigila; esto cuida el otro lado.)
    """
    for clave in esp.ESPECIES:
        e = carrera_de(3, especie=clave)
        ls = lineas(comp.podio(e))
        for puesto, (c, _) in enumerate(e.clasificacion[:3], start=1):
            y, x = _donde_esta_el_cajon(ls, puesto)
            ancho = comp.ANCHO_CAJON
            assert ls[y - 1][x:x + ancho] == "┌───┐", (
                f"{clave} puesto {puesto}: encima del número hay "
                f"«{ls[y - 1][x:x + ancho]}» y no el techo del cajón"
            )
            assert ls[y - 2][x:x + ancho] == f"({c.cara})", (
                f"{clave} puesto {puesto}: encima del cajón hay "
                f"«{ls[y - 2][x:x + ancho]}» y no «({c.cara})»"
            )


def test_el_podio_esta_en_el_orden_clasico_dos_uno_tres():
    """El 1.º en medio y más alto, el 2.º a su izquierda, el 3.º a su derecha."""
    ls = lineas(comp.podio(carrera_de(3)))
    sitios = {p: _donde_esta_el_cajon(ls, p) for p in (1, 2, 3)}

    _, x1 = sitios[1]
    _, x2 = sitios[2]
    _, x3 = sitios[3]
    assert x2 < x1 < x3

    # Cuanto más arriba empieza el cajón, más alto es.
    alturas = [sitios[p][0] for p in (1, 2, 3)]
    assert alturas == sorted(alturas) and len(set(alturas)) == 3, alturas


def test_el_podio_no_se_descuadra():
    """Las filas del podio llevan color, así que se montan a mano y pasarse de
    ancho rompe el marco en vez de recortar. Se aprieta con lo peor de todo:
    nombres del largo máximo, estadísticas al tope y desempates encadenados,
    que es lo que hace crecer los marcadores hasta cinco cifras."""
    rng = random.Random(7)
    largo = "M" * 24  # vistas.LARGO_MAXIMO_NOMBRE
    for cuantos in (3, 4, 5):
        for _ in range(40):
            corredores = [
                competidor(
                    nombre=rng.choice([largo, "Yo", "Juan III"]),
                    especie=rng.choice(list(esp.ESPECIES)),
                    stat=rng.randint(1, sim.MAXIMO_STAT),
                    modificador=2,
                    animo=rng.choice(esp.ANIMOS),
                )
                for _ in range(cuantos)
            ]
            e = comp.enfrentar(corredores, comp.CARRERA, rng)
            for linea in lineas(comp.podio(e)):
                assert len(linea) == pantalla.ANCHO + 2, repr(linea)

    # Y el caso extremo de verdad: todos empatados hasta agotar los desempates.
    iguales = [competidor(largo, stat=sim.MAXIMO_STAT, modificador=2)
               for _ in range(5)]
    e = comp.enfrentar(iguales, comp.CARRERA, DadosFijos([7]))
    assert e.combates[0].totales[0] > 9999  # cinco cifras: el marcador aprieta
    for linea in lineas(comp.podio(e)):
        assert len(linea) == pantalla.ANCHO + 2, repr(linea)


# --- El cuadro del torneo --------------------------------------------------

def test_el_resumen_de_un_torneo_es_el_cuadro():
    e = torneo_guionizado()
    assert comp.resumen(e) == comp.cuadro(e)


def test_el_cuadro_nombra_al_campeon_fuera_del_bloque():
    e = torneo_guionizado()
    texto = comp.cuadro(e)

    cabecera = texto.split("```ansi")[0]
    assert "🥇" in cabecera and "C0" in cabecera
    assert "🥇" not in "\n".join(lineas(texto))


def test_el_cuadro_une_a_cada_pareja_con_su_ganador():
    """El invariante del dibujo: las tres esquinas de un cruce (`┐`, `├`, `┘`) en
    la misma columna, y el nombre pegado al `├` es el del que ganó esa pelea.
    Un descuadre de una columna deja el cuadro sin sentido."""
    e = torneo_guionizado()
    ls = lineas(comp.cuadro(e))

    # Con el espacio: el separador del marco, `├────┤`, también empieza por `├─`.
    cruces = [i for i, ln in enumerate(ls) if "├─ " in ln]
    assert len(cruces) == len(e.combates) == 3

    for fila, resultado in zip(cruces, e.combates):
        columna = ls[fila].index("├─ ")
        assert ls[fila - 1][columna] == "┐", (fila, ls[fila - 1])
        assert ls[fila + 1][columna] == "┘", (fila, ls[fila + 1])

        ancho = comp.ANCHO_NOMBRE_CUADRO
        ganador = resultado.competidor_ganador.nombre[:ancho]
        hueco = ls[fila][columna + 3:columna + 3 + ancho]
        assert hueco == f"{ganador:<{ancho}}", (
            f"junto al cruce hay «{hueco}» y ganó «{ganador}»"
        )


def test_el_cuadro_ensena_a_los_cuatro_y_las_tres_peleas():
    e = torneo_guionizado()
    dentro = "\n".join(lineas(comp.cuadro(e)))
    for c in e.competidores:
        assert c.nombre in dentro, c.nombre
    assert dentro.count("├─ ") == 3


def test_el_que_cae_sale_en_gris():
    """El color es lo que hace legible el cuadro de un golpe: quien pasa va del
    color de su especie y quien cae, en gris, como en `/cementerio`."""
    e = torneo_guionizado()
    con_color = comp.cuadro(e)
    gris = f"\x1b[0;{esp.GRIS}m"

    for combate_ in e.combates:
        perdedor = combate_.competidor_perdedor
        recorte = perdedor.nombre[:comp.ANCHO_NOMBRE_CUADRO]
        assert f"{gris}{recorte:<{comp.ANCHO_NOMBRE_CUADRO}}" in con_color, recorte

    campeon = e.campeon
    suyo = f"\x1b[0;{campeon.color}m"
    assert suyo in con_color
    # Y el campeón no aparece nunca en gris: no ha caído en ninguna ronda.
    assert f"{gris}{campeon.nombre[:comp.ANCHO_NOMBRE_CUADRO]}" not in con_color


def test_los_marcadores_del_torneo_van_fuera_del_marco():
    """En el cuadro no caben, y meterlos a la fuerza lo rompería."""
    e = torneo_guionizado()
    texto = comp.cuadro(e)
    cola = texto.split("```")[-1]

    for combate_ in e.combates:
        for total in combate_.totales:
            assert str(total) in cola, (total, cola)


def test_el_cuadro_no_se_descuadra():
    """Las filas del cuadro llevan color, así que se montan a mano. Se aprieta
    con nombres del largo máximo y desempates encadenados."""
    rng = random.Random(5)
    largo = "M" * 24  # vistas.LARGO_MAXIMO_NOMBRE
    for _ in range(60):
        cuatro = [
            competidor(
                nombre=rng.choice([largo, "Yo", "Bartolomeo"]),
                especie=rng.choice(list(esp.ESPECIES)),
                stat=rng.randint(1, sim.MAXIMO_STAT),
                modificador=2,
                animo=rng.choice(esp.ANIMOS),
            )
            for _ in range(4)
        ]
        e = comp.enfrentar(cuatro, comp.SUMO, rng)
        for linea in lineas(comp.cuadro(e)):
            assert len(linea) == pantalla.ANCHO + 2, repr(linea)

    # Todos iguales: desempates hasta el tope y marcadores de cinco cifras.
    iguales = [competidor(largo, stat=sim.MAXIMO_STAT, modificador=2)
               for _ in range(4)]
    e = comp.enfrentar(iguales, comp.SUMO, DadosFijos([7]))
    for linea in lineas(comp.cuadro(e)):
        assert len(linea) == pantalla.ANCHO + 2, repr(linea)
