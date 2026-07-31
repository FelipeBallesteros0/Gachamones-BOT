"""Personalidades: que estén completas y que el prompt diga lo que debe."""
import inspect
import random
import re
from datetime import datetime, timedelta, timezone

import especies as esp
import personalidad as per
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def criatura(**cambios) -> sim.Criatura:
    base = dict(
        id=1, usuario_id="u1", guild_id="g1", especie="chispa", nombre="Prueba",
        nacida_en=T0, actualizada_en=T0,
        base_fuerza=15, base_velocidad=15, base_salud=15,
    )
    base.update(cambios)
    return sim.Criatura(**base)


# --- Cobertura -------------------------------------------------------------

def test_todas_las_especies_tienen_personalidad():
    assert set(per.VOCES) == set(esp.ESPECIES)


def test_ninguna_personalidad_esta_a_medias():
    for clave, yo in per.VOCES.items():
        assert yo.tono.strip(), clave
        assert yo.tic.strip(), clave
        assert yo.contacto.strip(), clave
        assert len(yo.respaldo) >= 3, clave
        assert all(f.strip() for f in yo.respaldo), clave


def test_las_personalidades_son_distintas_entre_si():
    tonos = [yo.tono for yo in per.VOCES.values()]
    assert len(set(tonos)) == len(tonos)


# --- El prompt -------------------------------------------------------------

def test_el_prompt_lleva_nombre_especie_y_dueño():
    p = per.construir_prompt(criatura(nombre="Pelusa"), T0, "felipe")
    assert "Pelusa" in p
    assert "Chispa" in p
    assert "felipe" in p


def test_el_prompt_incluye_la_muletilla_y_el_contacto():
    p = per.construir_prompt(criatura(especie="pollito"), T0, "felipe")
    assert "pío" in p
    assert "acarici" in p  # su reacción al contacto


def test_cada_especie_genera_un_prompt_distinto():
    prompts = {
        clave: per.construir_prompt(criatura(especie=clave), T0, "felipe")
        for clave in esp.ESPECIES
    }
    assert len(set(prompts.values())) == len(esp.ESPECIES)


def test_el_prompt_nunca_lleva_numeros_del_estado():
    """Regresión de la primera prueba real: pasándole «ánimo 85%», el modelo
    contestaba «estoy bien, con 85% de ánimo». Suena a ficha técnica."""
    c = criatura(hambre=85.0, animo=42.0, limpieza=13.0, nivel=7, victorias=3)
    estado = per.describir_estado(c, T0)
    for prohibido in ("85", "42", "13", "%"):
        assert prohibido not in estado, estado


def test_las_reglas_prohiben_decir_numeros_y_romper_el_personaje():
    p = per.construir_prompt(criatura(), T0, "felipe")
    assert "números" in p
    assert "IA" in p


# --- El estado se nota en el tono ------------------------------------------

def test_el_hambre_cambia_la_descripcion():
    llena = per.describir_estado(criatura(hambre=95.0), T0)
    vacia = per.describir_estado(criatura(hambre=5.0), T0)
    assert llena != vacia
    assert "hambre" in vacia.lower()


def test_las_tres_barras_influyen():
    bien = per.describir_estado(
        criatura(hambre=90.0, animo=90.0, limpieza=90.0), T0)
    mal = per.describir_estado(
        criatura(hambre=10.0, animo=10.0, limpieza=10.0), T0)
    assert bien != mal
    for palabra in ("hambre", "deprimido", "asqueroso"):
        assert palabra in mal.lower()

    ella = per.describir_estado(
        criatura(hambre=10.0, animo=10.0, limpieza=10.0, genero=esp.HEMBRA), T0)
    for palabra in ("deprimida", "asquerosa"):
        assert palabra in ella.lower()


def test_la_etapa_cambia_como_habla():
    """Un bebé no habla como un adulto grande: es lo que más cambia el tono por
    debajo de la personalidad de la especie."""
    bebe = per.construir_prompt(criatura(nivel=1), T0, "felipe")
    mayor = per.construir_prompt(criatura(nivel=5), T0, "felipe")
    assert "nacer" in bebe
    assert "nacer" not in mayor
    assert "forma final" in mayor


def test_el_estado_no_va_en_segunda_persona():
    """Regresión: escrito como «estás bien comida», la narración del jardín se
    contagiaba y acababa tuteando a las criaturas en vez de narrarlas."""
    tuteo = re.compile(r"\b(estás|tienes|te|eres|acabas|tu|tus)\b", re.I)
    for hambre in (95.0, 50.0, 20.0, 3.0):
        for animo in (95.0, 50.0, 20.0, 3.0):
            estado = per.describir_estado(
                criatura(hambre=hambre, animo=animo, victorias=3, derrotas=1), T0)
            encontrado = tuteo.search(estado)
            assert not encontrado, (estado, encontrado.group())


def test_toda_etapa_tiene_su_descripcion():
    for etapa in esp.ETAPAS:
        assert per.POR_ETAPA[etapa].strip(), etapa


def test_el_historial_de_competencias_se_refleja():
    ganadora = per.describir_estado(criatura(victorias=5, derrotas=1), T0)
    perdedora = per.describir_estado(criatura(victorias=1, derrotas=5), T0)
    novata = per.describir_estado(criatura(), T0)

    assert "orgulloso" in ganadora
    assert "molesta" in perdedora
    assert "orgullos" not in novata and "molesta" not in novata

    ella = per.describir_estado(criatura(victorias=5, derrotas=1,
                                         genero=esp.HEMBRA), T0)
    assert "orgullosa" in ella


# --- El jardín -------------------------------------------------------------

def test_el_prompt_del_jardin_describe_a_las_dos():
    a = criatura(especie="pollito", nombre="Kuro")
    b = criatura(especie="michi", nombre="Nube")
    sistema, peticion = per.prompt_jardin([a, b], T0)

    assert "Kuro" in sistema and "Nube" in sistema
    assert "pío" in sistema      # la muletilla del pollito
    assert "zarpazo" in sistema  # cómo reacciona el michi al contacto
    assert "Kuro" in peticion and "Nube" in peticion


def test_el_prompt_del_jardin_admite_una_sola_criatura():
    _, peticion = per.prompt_jardin([criatura(nombre="Solitario")], T0)
    assert "solo" in peticion
    _, peticion = per.prompt_jardin(
        [criatura(nombre="Solitaria", genero=esp.HEMBRA)], T0)
    assert "sola" in peticion


def test_el_jardin_tambien_prohibe_el_markdown_y_los_emoji():
    sistema, _ = per.prompt_jardin([criatura(), criatura()], T0)
    assert "markdown" in sistema
    assert "emoji" in sistema


def test_el_estado_de_cada_una_entra_en_la_escena():
    """Una criatura hambrienta tiene que comportarse como tal en el jardín."""
    llena, _ = per.prompt_jardin([criatura(hambre=95.0)], T0)
    vacia, _ = per.prompt_jardin([criatura(hambre=5.0)], T0)
    assert llena != vacia
    assert "hambre" in vacia.lower()


def test_todos_los_prompts_relevantes_exigen_espanol_neutro():
    import aventura as av

    c = criatura()
    salvaje = av.Salvaje("chispa", "Salvaje", c.genero, "gruñón", (10, 10, 10))
    prompts = (
        per.construir_prompt(c, T0, "Felipe"),
        per.prompt_jardin([c], T0)[0],
        per.prompt_aventura(c, "al bosque", [], av.NADA)[0],
        per.prompt_salvaje(salvaje, c, "hola")[0],
        per.prompt_escena("al bosque", 1)[0],
    )

    for prompt in prompts:
        assert per.REGLA_ESPANOL_NEUTRO in prompt
        assert "tuteo o ustedes" in prompt
        assert "nunca uses vosotros" in prompt


def test_el_prompt_salvaje_contrasta_ustedes_con_vosotros():
    import aventura as av

    c = criatura()
    salvaje = av.Salvaje("chispa", "Salvaje", c.genero, "gruñón", (10, 10, 10))
    sistema, _ = per.prompt_salvaje(salvaje, c, "hola")

    assert "ustedes son" in sistema
    assert "vosotros sois" in sistema


def test_el_guard_rechaza_la_frase_reportada_y_admite_su_equivalente_neutro():
    assert per.usa_formas_de_vosotros(
        "¿Y vosotros quién sois? No me voy con extraños"
    )
    assert not per.usa_formas_de_vosotros(
        "¿Y ustedes quiénes son? No me voy con extraños"
    )


def test_el_guard_detecta_formas_de_vosotros_solo_como_palabras_completas():
    formas = (
        "vosotros", "vosotras", "vuestro", "vuestra", "vuestros", "vuestras",
        "os", "sois", "estáis", "tenéis", "podéis", "queréis", "habéis",
        "hacéis", "vais", "venís", "decís", "dais", "sabéis", "veis",
    )
    for forma in formas:
        assert per.usa_formas_de_vosotros(f"Aquí {forma} ahora"), forma

    assert not per.usa_formas_de_vosotros("La famosa postal muestra dos cosas")


def test_las_fichas_no_alimentan_regionalismos_peninsulares_al_prompt():
    c = criatura(limpieza=20.0, victorias=1, derrotas=2)
    fichas = " ".join(
        [voz.tono for voz in per.VOCES.values()]
        + [caracter.rasgo for caracter in per.CARACTERES.values()]
        + [per.describir_estado(c, T0)]
    )

    for regionalismo in (
        "no pillas", "todo el rato", "echas de menos", "le fastidia", "picores",
    ):
        assert regionalismo not in fichas


def test_el_prompt_de_aventura_recibe_el_percance_ya_decidido():
    import aventura as av

    sistema, _ = per.prompt_aventura(
        criatura(), "al bosque", [], av.NADA, av.PERCANCE
    )

    assert "Sufre un percance" in sistema
    assert "-5 hambre y -5 ánimo" in sistema
    assert "ya está decidido" in sistema
    assert "No decidas" in sistema


# --- Respaldo --------------------------------------------------------------

def test_hay_respaldo_para_toda_especie():
    for clave in esp.ESPECIES:
        frase = per.frase_de_respaldo(criatura(especie=clave))
        assert frase.strip()


def test_el_respaldo_no_repite_la_misma_frase_seguida():
    c = criatura(especie="pollito")
    frases = [per.frase_de_respaldo(c, i) for i in range(3)]
    assert len(set(frases)) == 3


def test_el_respaldo_suena_al_personaje():
    """Si la API falla, la criatura tiene que seguir sonando a ella misma."""
    assert "ío" in per.frase_de_respaldo(criatura(especie="pollito"), 0)
    assert "chisp" in " ".join(per.VOCES["chispa"].respaldo)
    assert "ip" in " ".join(per.VOCES["chatarra"].respaldo)


def test_el_respaldo_nunca_parece_un_mensaje_de_error():
    for clave in esp.ESPECIES:
        for frase in per.VOCES[clave].respaldo:
            bajo = frase.lower()
            for fea in ("error", "api", "fall", "disponible", "intent"):
                assert fea not in bajo, (clave, frase)


# --- Género y carácter -----------------------------------------------------

def todos_los_textos(genero: str) -> list[str]:
    """Todo lo que puede acabar delante del modelo, para un género."""
    textos = []
    for clave in esp.ESPECIES:
        for nivel in (1, 3, 5):
            for barras in ((95.0, 95.0, 95.0), (10.0, 10.0, 10.0)):
                c = criatura(especie=clave, genero=genero, nivel=nivel,
                             hambre=barras[0], animo=barras[1], limpieza=barras[2],
                             victorias=3, derrotas=1)
                textos.append(per.construir_prompt(c, T0, "felipe"))
                textos.append(per.describir_estado(c, T0))
                textos.extend(per.prompt_jardin([c], T0))
                textos.extend(per.frase_de_respaldo(c, i) for i in range(3))
                textos.extend(_textos_de_aventura(c, genero))
    return textos


def _textos_de_aventura(c, genero: str) -> list[str]:
    """Los prompts de la aventura, con todos los finales y los dos géneros.

    Entran en el barrido por lo mismo que los demás: una marca «{o/a}» olvidada
    llega tal cual al modelo y nadie se entera hasta que la lee alguien.
    """
    import aventura as av

    textos = []
    for bioma in av.BIOMAS.values():
        viaje = av.Viaje(
            bioma=bioma,
            escena=av.escena_escrita(bioma, rng=random.Random(1)),
        )
        for opcion in (av.FUERZA, av.VELOCIDAD):
            viaje = av.avanzar(viaje, c, opcion,
                               av.escena_escrita(bioma, rng=random.Random(2)),
                               random.Random(1))
        salida = viaje.salida
        for final in (av.SALVAJE, av.OBJETO, av.NADA):
            textos.extend(
                per.prompt_aventura(c, bioma.adonde, list(salida.pruebas), final)
            )
        salvaje = av.Salvaje(
            bioma.especies[0], "Salvaje", genero, "gruñón", (10, 10, 10)
        )
        textos.extend(per.prompt_salvaje(salvaje, c, "hola"))
        textos.extend(per.respaldo_salvaje(i) for i in range(3))
    return textos


def test_no_queda_ninguna_marca_de_genero_sin_resolver():
    """El fallo que se colaría sin avisar: una marca «{o/a}» olvidada llega
    tal cual al modelo y la criatura escribe «bien comid{o/a}»."""
    for genero in esp.GENEROS:
        for texto in todos_los_textos(genero):
            assert "{" not in texto and "}" not in texto, texto


def test_todas_las_criaturas_tienen_carne_de_los_dos_generos():
    """Cada especie suena distinta según el género, que es lo que justifica
    haber marcado los textos en vez de dejarlos en femenino."""
    distintos = 0
    for clave in esp.ESPECIES:
        el = per.construir_prompt(criatura(especie=clave), T0, "felipe")
        ella = per.construir_prompt(
            criatura(especie=clave, genero=esp.HEMBRA), T0, "felipe")
        if el != ella:
            distintos += 1
    assert distintos == len(esp.ESPECIES)


def test_el_prompt_dice_el_genero_y_manda_concordar():
    el = per.construir_prompt(criatura(), T0, "felipe")
    assert "macho" in el and "masculino" in el
    ella = per.construir_prompt(criatura(genero=esp.HEMBRA), T0, "felipe")
    assert "hembra" in ella and "femenino" in ella


def test_hay_diez_caracteres_completos_y_distintos():
    assert len(per.CARACTERES) == 10
    for clave, c in per.CARACTERES.items():
        assert c.masculino.strip() and c.femenino.strip(), clave
        assert c.rasgo.strip(), clave
    rasgos = [c.rasgo for c in per.CARACTERES.values()]
    assert len(set(rasgos)) == len(rasgos)


def test_el_caracter_por_defecto_existe():
    """`Criatura` lo trae como literal porque `simulacion` no puede importar
    `personalidad`. Si alguien renombra el carácter, esto avisa."""
    assert esp.CARACTER_POR_DEFECTO in per.CARACTERES


def test_la_palabra_del_caracter_concuerda_con_el_genero():
    assert per.nombre_caracter(criatura(caracter="gruñón")) == "gruñón"
    assert per.nombre_caracter(
        criatura(caracter="gruñón", genero=esp.HEMBRA)) == "gruñona"
    # Los invariantes no cambian.
    assert per.nombre_caracter(
        criatura(caracter="valiente", genero=esp.HEMBRA)) == "valiente"


def test_el_caracter_entra_en_el_prompt_y_en_el_jardin():
    c = criatura(caracter="perezoso")
    assert per.CARACTERES["perezoso"].rasgo in per.construir_prompt(c, T0, "felipe")
    sistema, _ = per.prompt_jardin([c], T0)
    assert "perezoso" in sistema


def test_el_caracter_no_sustituye_a_la_voz_de_la_especie():
    """Un Pedrusco travieso sigue siendo lento y de pocas palabras."""
    p = per.construir_prompt(
        criatura(especie="pedrusco", caracter="travieso"), T0, "felipe")
    assert "pocas palabras" in p      # la especie
    assert "trastadas" in p           # el carácter


def test_el_sorteo_reparte_los_diez_caracteres_y_los_dos_generos():
    rng = random.Random(0)
    caracteres = {per.tirar_caracter(rng) for _ in range(500)}
    assert caracteres == set(per.CARACTERES)

    generos = [esp.tirar_genero(rng) for _ in range(1000)]
    assert set(generos) == set(esp.GENEROS)
    machos = generos.count(esp.MACHO)
    assert 400 < machos < 600, machos  # 50/50 con holgura de sobra


def test_el_prompt_usa_el_articulo_de_la_especie():
    """A Juan III, que es una Chispa, el prompt le decía «un Chispa»."""
    p = per.construir_prompt(criatura(especie="chispa", nombre="Juan III"), T0, "f")
    assert "una Chispa macho" in p
    p = per.construir_prompt(criatura(especie="pulpo", genero=esp.HEMBRA), T0, "f")
    assert "un Pulpo hembra" in p


def test_dos_respaldos_seguidos_nunca_son_la_misma_frase():
    """Regresión de lo que vio John Bazooka en Discord: dos mensajes distintos
    le devolvieron literalmente la misma frase enlatada, y por eso parecía que
    el bot lo ignoraba. La semilla tiene que avanzar, no depender del texto."""
    c = criatura(especie="pollito")
    frases = [per.frase_de_respaldo(c, n) for n in range(1, 7)]
    for anterior, siguiente in zip(frases, frases[1:]):
        assert anterior != siguiente, frases


def test_la_semilla_vieja_es_justo_la_que_fallaba():
    """Deja constancia del cálculo exacto: con 0V-0D la semilla era la longitud
    del mensaje, y estos dos textos caen en el mismo índice."""
    c = criatura(especie="pollito", victorias=0, derrotas=0)
    vieja = lambda t: c.victorias + c.derrotas + len(t)
    assert vieja("hola") % 3 == vieja("qué te gustaría comer?") % 3
    assert per.frase_de_respaldo(c, vieja("hola")) == \
        per.frase_de_respaldo(c, vieja("qué te gustaría comer?"))


def test_el_prompt_de_escena_pide_las_cuatro_claves_y_sitúa_el_bioma():
    sistema, peticion = per.prompt_escena("al Volcán", 1)

    for clave in ("situacion", "fuerza", "velocidad", "volver"):
        assert f'"{clave}"' in sistema
    assert "al Volcán" in sistema
    assert "JSON" in sistema
    assert "Es lo primero" in peticion


def test_el_prompt_de_escena_no_le_cuenta_al_modelo_quién_va():
    """Los dados deciden y el modelo narra.

    A la escena no se le pasa la criatura: si el modelo supiera si es fuerte o
    rápida, escribiría la opción que le conviene, y quien decide es quien juega.
    Además se le prohíbe expresamente adelantar el resultado."""
    sistema, _ = per.prompt_escena("al Bosque", 2)

    assert "no digas cuál es la buena" in sistema.lower()
    assert "no menciones a la criatura" in sistema.lower()
    # El nombre y las cifras de nadie caben aquí: la función no recibe criatura.
    assert "criatura" not in inspect.signature(per.prompt_escena).parameters


def test_en_el_segundo_nodo_es_donde_puede_aparecer_algo():
    """Es donde va el hallazgo. Lo que NO se le dice es de qué forma: un cofre
    era un ejemplo, y si se le nombra sólo eso, todas las escenas acaban siendo
    cofres."""
    _, primera = per.prompt_escena("al Bosque", 1)
    _, segunda = per.prompt_escena("al Bosque", 2, "Forzó la puerta.")

    assert "algo que se lleve" in segunda and "algo que se lleve" not in primera
    assert "cofre" not in segunda
    assert "Forzó la puerta." in segunda


def test_el_prompt_de_escena_abre_la_mano_mas_alla_del_obstaculo():
    """Pedido tras jugarlo: cruzarse con alguien que te da algo, o que esté
    pasando una cosa, no sólo puertas trancadas."""
    sistema, _ = per.prompt_escena("al Bosque", 1)

    assert "No sólo un obstáculo cerrado" in sistema
    for forma in ("viajero", "pastor", "tormenta", "criatura"):
        assert forma in sistema, forma
    assert "dos puertas cerradas" in sistema  # la instrucción de variar


def test_el_guard_pilla_tambien_los_verbos_que_no_estan_en_la_lista():
    """La lista es cerrada y el modelo conjuga lo que le da la gana. Desde que
    la aventura se narra en plural esto pasa de verdad: la primera narración que
    salió fue «Cruzáis el río y llegáis al claro», y colaba entera."""
    for frase in ("Cruzáis el río", "Llegaréis tarde", "Si queréis, subís",
                  "Ya lo veréis", "Cuando lleguéis"):
        assert per.usa_formas_de_vosotros(frase), frase

    # Y no se lleva por delante palabras normales que acaban parecido.
    for frase in ("Vuelven al país de origen", "La raíz del árbol",
                  "Cruzan el río y llegan al claro", "Tenía seis piedras"):
        assert not per.usa_formas_de_vosotros(frase), frase


def test_el_prompt_del_viaje_prohibe_recitar_la_ficha():
    """Reportado jugando: «Juan III, ese chispa macho y perezoso, se burla de
    los que cavan tesoros». El modelo copiaba tal cual la línea de QUIÉN VA.

    Es el mismo fallo que el jardín ya tenía resuelto con «empieza por lo que
    hacen, no por describir cómo son», y la aventura se lo había saltado."""
    import aventura as av

    c = criatura(nombre="Juan III", caracter="perezoso")
    sistema, _ = per.prompt_aventura(c, "al desierto", [], av.NADA, dueño="Felipe")

    assert "no para escribirlo" in sistema
    assert "Empieza por lo que hacen, no por describir cómo son" in sistema
    # Y el dato deja de estar servido como una frase copiable.
    assert "chispa macho y perezoso" not in sistema.lower()


def test_el_prompt_del_viaje_sigue_diciendole_quien_es():
    """Prohibir recitarlo no puede ser quitárselo: sin la especie ni el carácter
    no puede comportarse como quien es."""
    import aventura as av

    c = criatura(nombre="Juan III", caracter="perezoso", genero=esp.HEMBRA)
    sistema, _ = per.prompt_aventura(c, "al desierto", [], av.NADA, dueño="Felipe")

    assert "Juan III" in sistema
    assert "Chispa" in sistema
    assert "perezosa" in sistema           # concordado con su género
    assert per.CARACTERES["perezoso"].rasgo in sistema
    assert "{" not in sistema and "}" not in sistema  # sin marcas sin resolver


def test_el_limite_de_la_narracion_cabe_en_lo_que_publica_el_bot():
    """El fallo que esto vigila ya pasó: se subió el límite de palabras sin
    subir el recorte y se cortaron 7 de cada 10 narraciones, perdiéndose el
    final —que es donde se cuenta si encontraste algo—.

    Y no basta con que quepa el límite: **el modelo se pasa un 25 %**, medido
    subiendo de 45 a 90. El recorte tiene que dar para el límite más ese 25 %.
    """
    import ia
    import aventura as av

    sistema, _ = per.prompt_aventura(criatura(), "al bosque", [], av.NADA)

    assert f"{per.PALABRAS_NARRACION} palabras como máximo" in sistema
    # 6,5 caracteres por palabra en castellano, espacios incluidos.
    con_lo_que_se_pasa = per.PALABRAS_NARRACION * 1.25 * 6.5
    assert con_lo_que_se_pasa < ia.LARGO_MAXIMO_NARRACION, (
        f"con {per.PALABRAS_NARRACION} palabras el modelo escribirá unos "
        f"{con_lo_que_se_pasa:.0f} caracteres y el recorte está en "
        f"{ia.LARGO_MAXIMO_NARRACION}: se cortarían por el final"
    )
    # Y lo que se publica sigue cabiendo en un mensaje de Discord.
    assert ia.LARGO_MAXIMO_NARRACION < 2000
