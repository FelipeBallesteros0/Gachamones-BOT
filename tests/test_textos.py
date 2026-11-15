"""El vocabulario visible usa los términos canónicos del producto."""
import ast
import re
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

import aventura
from cogs import mudanza
import competir as comp
import objetos
import pantalla
import personalidad as per
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def gachamon(**cambios) -> sim.Criatura:
    datos: dict[str, Any] = dict(
        id=1,
        usuario_id="u1",
        guild_id="g1",
        especie="pulpo",
        nombre="Prueba",
        nacida_en=T0,
        actualizada_en=T0,
        base_fuerza=15,
        base_velocidad=15,
        base_salud=15,
    )
    datos.update(cambios)
    return sim.Criatura(**datos)


def contexto_salvaje(salvaje, acompañante):
    antes = aventura.Encuentro(salvaje, confianza=40, paciencia=4)
    despues = aventura.Encuentro(
        salvaje, confianza=45, paciencia=3, ultimo_cambio=5
    )
    return aventura.ContextoSalvaje(
        salvaje=salvaje,
        acompañante=acompañante,
        fase=aventura.fase_de(antes.confianza),
        fase_ahora=aventura.fase_de(despues.confianza),
        tendencia=aventura.tendencia_de(antes, despues),
        paciencia=despues.paciencia,
        dicho="hola",
    )


def test_prompts_usan_gachamon_y_aventura_nombra_comida():
    c = gachamon()
    salvaje = aventura.Salvaje("chispa", "Salvaje", c.genero, "gruñón", (10, 10, 10, 15))
    charla = per.construir_prompt(c, T0, "Alan")
    viaje = per.prompt_aventura(
        c, "al bosque", [], aventura.NADA, aventura.PERCANCE
    )[0]
    escena = per.prompt_escena(
        "al bosque", 1, especies=aventura.BIOMAS["bosque"].nombres_especies,
        pareja=(aventura.FUERZA, aventura.VELOCIDAD),
        favorecida=aventura.FUERZA,
    )[0]
    voz_salvaje = per.prompt_salvaje(contexto_salvaje(salvaje, c))[0]

    for sistema in (charla, viaje, escena, voz_salvaje):
        restante = sistema.replace(per.REGLA_NOMBRE_GACHAMON, "").casefold()
        assert "gachamon" in sistema.casefold()
        assert not re.search(r"\b(?:criaturas?|mascotas?)\b", restante)
    for sistema in (charla, viaje, voz_salvaje):
        assert per.REGLA_NOMBRE_GACHAMON in sistema
    assert "-5 comida y -5 ánimo" in viaje


def test_ficha_usa_barras_canonicas_sin_cambiar_el_marco():
    mensaje = ANSI.sub("", pantalla.render(gachamon(), T0))
    marco = mensaje.split("```ansi\n")[1].split("\n```")[0].splitlines()
    separadores = [i for i, linea in enumerate(marco) if linea.startswith("├")]
    barras = marco[separadores[0] + 1 : separadores[1]]

    assert [linea[2:9].strip() for linea in barras] == ["COMIDA", "ÁNIMO", "ASEO"]
    assert {len(linea) for linea in marco} == {pantalla.ANCHO + 2}
    assert all(linea[0] in "╭├╰│" and linea[-1] in "╮┤╯│" for linea in marco)


def test_el_percance_nombra_la_comida_y_el_animo():
    assert aventura.render_percance(aventura.PERCANCE) == (
        "⚠️ Percance: -5 comida y -5 ánimo."
    )


def test_catalogo_visible_nombra_la_barra_comida():
    assert objetos.CATALOGO["pocion_comida"].descripcion.startswith(
        "Deja la comida a 100."
    )
    assert "+25 de comida" in objetos.CATALOGO["golosinas"].descripcion


# «Coger» es de España y aquí se dice tomar. Va con frontera de palabra para no
# pisar «recoger» ni «escoger», que sí son neutras.
COGER = re.compile(r"\bcog[ei]\w*", re.IGNORECASE)


def test_el_texto_visible_de_competir_usa_espanol_neutro():
    visible = "\n".join((
        *comp.REGLAS.values(),
        *comp.ARTICULOS.values(),
        (Path(__file__).resolve().parent.parent / "README.md").read_text(
            encoding="utf-8"
        ),
    ))

    encontrado = COGER.search(visible)
    assert encontrado is None, encontrado.group(0)


# --- Los nombres de las especies -------------------------------------------
#
# Jugando salió «un grupo de chispas», y Chispa dejó de existir el 31 de julio:
# hoy se llama Pyro. Lo que lo permitía es que a la escena se le pedía inventar
# —incluso «otro gachamon que no deja pasar»— sin decirle qué especies hay.

def test_la_escena_solo_puede_nombrar_a_los_del_bioma():
    """El censo va en el prompt y sale del catálogo, no escrito aquí: así un
    rebautizo futuro llega solo y este test no se puede quedar viejo."""
    import especies as esp

    for clave, bioma in aventura.BIOMAS.items():
        sistema, _ = per.prompt_escena(
            bioma.adonde, 1, especies=bioma.nombres_especies,
            pareja=(aventura.FUERZA, aventura.VELOCIDAD),
            favorecida=aventura.FUERZA,
        )
        for nombre in bioma.nombres_especies:
            assert nombre in sistema, (clave, nombre)
        for otra in esp.ESPECIES.values():
            if otra.clave not in bioma.especies:
                assert otra.nombre not in sistema, (clave, otra.nombre)
        assert "Nunca te inventes nombres de especie." in sistema


def test_el_censo_enumera_en_castellano():
    """La «o» pasa a «u» ante palabra que empieza por o-, y en el catálogo hay
    justo un caso: el Arrecife acaba en «Remolín u Octopul». No rompe nada y
    canta al leerlo, que es exactamente lo que no cazaría ningún otro test."""
    assert per.enumerar(("Pyro",)) == "Pyro"
    assert per.enumerar(("Pyro", "Tsushimon")) == "Pyro o Tsushimon"
    assert per.enumerar(("Geo", "Ostra")) == "Geo u Ostra"
    assert per.enumerar(("Geo", "Hongo")) == "Geo u Hongo"
    assert per.enumerar(aventura.BIOMAS["arrecife"].nombres_especies) == (
        "Coralito, Nacar, Remolín u Octopul"
    )


def test_ninguna_pantalla_ensena_la_clave_de_la_especie():
    """El invariante de fondo: lo que se guarda es la clave y lo que se ve es el
    nombre. Diez especies tienen los dos distintos desde el rebautizo, y son las
    únicas donde confundirlos se nota."""
    import especies as esp

    for especie in esp.ESPECIES.values():
        if especie.clave.casefold() == especie.nombre.casefold():
            continue
        ficha = ANSI.sub("", pantalla.render(gachamon(especie=especie.clave), T0))
        assert especie.nombre in ficha, especie.clave
        assert especie.clave not in ficha.casefold(), especie.clave


RAIZ = Path(__file__).resolve().parent.parent
# Herramienta de consola para el dueño del proyecto, no texto de jugador.
SIN_TEXTO_DE_JUGADOR = {"economia_reporte.py"}
# db.py y economia.py guardan SQL y nombres de columna, que conservan el nombre
# viejo a propósito, pero también avisos que lee quien juega: sólo se salta el SQL.
CON_SQL = {"db.py", "economia.py"}
NOMBRE_VIEJO = re.compile(r"ascii\s?(coin|gem)", re.IGNORECASE)
# Un identificador suelto es un nombre de columna o de atributo.
IDENTIFICADOR = re.compile(r"^[a-z_]+$")
# Una palabra clave de SQL en mayúsculas, entera, delata una sentencia.
PALABRA_SQL = re.compile(
    r"\b(SELECT|UPDATE|INSERT|DELETE|CREATE TABLE|ALTER TABLE|VALUES|WHERE|FROM)\b"
)


def _es_sql(texto: str) -> bool:
    return bool(IDENTIFICADOR.match(texto) or PALABRA_SQL.search(texto))


def _literales_de(ruta: Path):
    """Las cadenas de un módulo, sin sus docstrings ni sus comentarios."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    docstrings = {
        id(nodo.body[0].value)
        for nodo in ast.walk(arbol)
        if isinstance(
            nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        )
        and nodo.body
        and isinstance(nodo.body[0], ast.Expr)
        and isinstance(nodo.body[0].value, ast.Constant)
    }
    for nodo in ast.walk(arbol):
        if (
            isinstance(nodo, ast.Constant)
            and isinstance(nodo.value, str)
            and id(nodo) not in docstrings
        ):
            yield nodo.lineno, nodo.value


def test_ningun_texto_de_jugador_dice_asciicoins_ni_asciigems():
    fuentes = [*RAIZ.glob("*.py"), *(RAIZ / "cogs").glob("*.py")]
    culpables = [
        f"{ruta.name}:{linea}: {texto!r}"
        for ruta in fuentes
        if ruta.name not in SIN_TEXTO_DE_JUGADOR
        for linea, texto in _literales_de(ruta)
        if NOMBRE_VIEJO.search(texto)
        and not (ruta.name in CON_SQL and _es_sql(texto))
    ]
    assert not culpables, "\n".join(culpables)


def test_el_manual_publicado_habla_de_monedas_y_gemas():
    manual = mudanza.pagina_del_manual()
    assert not NOMBRE_VIEJO.search(manual)
    assert "monedas" in manual and "gemas" in manual


def test_la_ficha_nombra_las_monedas_en_femenino():
    assert objetos.MONEDA_TIENDA == "monedas"


# --- Barridos de la fuente ---------------------------------------------------

def test_ningun_texto_lleva_ya_el_femenino_fijo():
    """Barrido del fuente. El constructor de `ResultadoAccion` cubre los avisos
    de las acciones, pero hay texto escrito a mano y ahí no hay nada que lo
    cubra: esto vigila que no reaparezca un adjetivo clavado en femenino
    hablando de una criatura concreta."""
    # Sólo frases sin sustantivo al lado. «una criatura hambrienta» no entra en
    # la lista: ahí el femenino concuerda con «criatura» y es correcto.
    sospechosas = ("encantada", "molida", "Como nueva", "mírala")
    for ruta in RAIZ.glob("**/*.py"):
        if "tests" in ruta.parts or "venv" in ruta.parts:
            continue
        for _, literal in _literales_de(ruta):
            for palabra in sospechosas:
                assert palabra not in literal, (ruta.name, palabra, literal)


def test_ningun_modulo_define_dos_veces_la_misma_clase():
    """Regresión: un cambio dejó `EncuentroView` definida DOS veces en el mismo
    fichero. Python se queda con la última, así que la versión nueva quedó
    muerta y el bot siguió enseñando la vieja — desplegado y con los 1542 tests
    en verde, porque ninguno miraba el fichero como texto.

    Se revisa el árbol de sintaxis y no el texto: así no se cuela una definición
    dentro de un `if` ni se confunde con una mención en un comentario.
    """
    ficheros = [
        f for f in RAIZ.rglob("*.py")
        if "venv" not in f.parts and ".git" not in f.parts
    ]
    assert ficheros, "sin ficheros que revisar esto no prueba nada"

    for fichero in ficheros:
        arbol = ast.parse(fichero.read_text(), filename=str(fichero))
        cuenta = Counter(
            nodo.name for nodo in arbol.body
            if isinstance(nodo, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        )
        repetidos = [n for n, veces in cuenta.items() if veces > 1]
        assert not repetidos, f"{fichero.name} define dos veces: {repetidos}"
