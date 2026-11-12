# Gachamon web · Plan 1 de 3 — Reglas y bot

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dejar las reglas del juego y el bot de Discord listos para convivir con la web: la excepción de la muerte por hambre, el nombre nuevo de las monedas, el retiro de marcos y tintes con su devolución, y la vinculación de cuentas con `/vincular`.

**Architecture:** Todavía no hay servidor web. Todo cae en los módulos puros y en `db.py`/`economia.py`, y el bot sólo gana un comando. Dos módulos puros nuevos concentran lo que es propio de la web: `identidad.py` es el único sitio que sabe qué es una identidad web, y `vinculo.py` el único que sabe cómo es un código de vinculación.

**Tech Stack:** Python 3.12 y 3.14, SQLite síncrono, discord.py 2.7.1, pytest 9.1.1. Ninguna dependencia nueva.

**Spec:** `docs/superpowers/specs/2026-11-12-gachamon-web-parte-a-design.md` — sobre todo las secciones 5.2 y 5.8. Quien ejecute lee los dos documentos.

**Los tres planes de la parte A:**

1. **Reglas y bot** — este. Cambia cosas que se ven en Discord, y se puede desplegar solo.
2. **Servidor web y pantalla principal** — el servicio, la cuenta y el avatar, la pantalla de lugar, el pueblo, la caricia, los globos, los retratos y el arte de relleno, los cambios en Rowino y la puesta en marcha. Se escribe cuando este esté terminado.
3. **Lugares de la parte A** — incubadora, tienda, mochila, ropero, casa con huerto y muebles, refugio, y hablar.

## Global Constraints

- Los módulos puros del juego no importan `discord`. `identidad.py` y `vinculo.py` son puros.
- SQLite sigue síncrono. `db.py` posee el esquema, las conexiones y las transacciones, y **no importa `economia.py`**.
- Toda mutación de juego o de dinero va bajo `BEGIN IMMEDIATE`.
- Ninguna dependencia nueva.
- En las pruebas, el tiempo y el azar se inyectan; nada depende del reloj real.
- Todo texto que vea un jugador dice **«monedas»** y **«gemas»**. Nunca «asciicoins» ni «asciigems».
- Los nombres internos **no** se renombran: las columnas `asciicoins`, `asciigems` y `delta_asciicoins`, los atributos de `economia.Saldos` y las constantes como `ASCIICOINS_INICIALES` quedan como están.
- Devolución: **50 gemas por marco y 20 por tinte**, fuera de todo tope, y no puede pagarse dos veces.
- Ningún mensaje que publique el bot pasa de 2000 caracteres.
- `CLAUDE.md` del repositorio: antes de editar un símbolo que ya existe, `impact({target: "<símbolo>", direction: "upstream"})` con GitNexus; antes de cada commit, `detect_changes()`. Un riesgo HIGH o CRITICAL se le avisa a Felipe antes de seguir.
- Antes de cada commit: `./venv/bin/python -m pre_commit run --all-files` (compila y corre la suite entera), `git diff --check` y `git diff --cached --check`.
- Mensajes de commit convencionales y en castellano, como los del historial.
- **Nada de push, merge ni despliegue sin autorización explícita de Felipe.**
- Rama de trabajo: `web/1-reglas-y-bot`, que sale de `docs/gachamon-web-parte-a` para llevar el diseño consigo. Un commit por tarea.

## Review Focus

Lo que el diseño da por supuesto y más fácil es que falle con una persona de verdad. Cada línea tiene su prueba en la tarea que se indica.

1. **Cambiar de gachamon activo siendo identidad web.** El que sale de la incubadora no debe recibir un instante de muerte por el camino de `db.activar`. → Tarea 1.
2. **Alimentar a un gachamon web que lleva días en 0.** Tiene que comer con normalidad y seguir sin reloj de muerte. → Tarea 1.
3. **Arrancar dos procesos a la vez durante la devolución.** Pronto habrá dos servicios sobre la misma base; la devolución no puede pagar doble. → Tarea 4.
4. **Una pieza retirada que sigue puesta en un gachamon, vivo o muerto, o que reaparece en el ropero.** Se devuelve una vez y la columna queda limpia. → Tarea 4.
5. **Códigos escritos como los escribe la gente**, con minúsculas, espacios o guiones; el código que vence en ese mismo segundo; dos personas canjeando el mismo código a la vez. → Tarea 5.

---

### Task 1: Identidad web y la excepción de la muerte por hambre

El gachamon de una identidad web no muere de hambre mientras su dueño no tenga cómo enterarse (diseño, 5.8). Las barras bajan igual; lo único que cambia es que el hambre en 0 no mata y que no se guarda ni instante de muerte ni de aviso.

**Files:**
- Create: `identidad.py`
- Modify: `simulacion.py` — `avanzar()` (≈ líneas 952–1011)
- Modify: `db.py` — `_a_valores()` (≈ líneas 794–816)
- Modify: `AGENTS.md` — sección «Invariantes del dominio»
- Test: `tests/test_identidad.py`

**Interfaces:**
- Consumes: nada de otras tareas.
- Produces:
  - `identidad.es_web(usuario_id: str) -> bool` — cierto sólo para un entero positivo en negativo, sin ceros a la izquierda ni espacios (`"-12"`).
  - `identidad.de_cuenta_web(rowino_uid: int) -> str` — `12 → "-12"`; `ValueError` si `rowino_uid < 1`.
  - `identidad.sin_aviso_de_hambre(usuario_id: str) -> bool` — hoy devuelve lo mismo que `es_web`. Es **el único sitio** que el proyecto 2 tendrá que tocar para cerrar la excepción; las reglas preguntan por esta función y nunca por `es_web`.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_identidad.py`:

```python
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import economia
import identidad
import simulacion as sim

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (10, 10, 10, 10)
WEB = identidad.de_cuenta_web(12)
DISCORD = "123456789012345678"


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "identidad.db")
    db.inicializar()


def criatura(usuario_id: str, **cambios) -> sim.Criatura:
    base = sim.Criatura(
        id=1, usuario_id=usuario_id, guild_id="g", especie="pollito",
        nombre="Pelusa", nacida_en=T0, actualizada_en=T0, base_salud=10,
    )
    return replace(base, **cambios)


def relojes_de(usuario_id: str) -> list[tuple]:
    with db.conectar() as con:
        return [
            tuple(fila) for fila in con.execute(
                "SELECT muere_en, avisa_en, muerta_en FROM criaturas "
                "WHERE usuario_id = ?", (usuario_id,),
            )
        ]


@pytest.mark.parametrize("usuario_id, esperado", [
    ("-12", True), ("-1", True),
    (DISCORD, False), ("12", False), ("", False), ("-", False),
    ("-0", False), ("-012", False), ("--12", False), ("-1.5", False),
    ("-12 ", False), (" -12", False), ("abc", False),
])
def test_solo_un_entero_positivo_en_negativo_es_identidad_web(usuario_id, esperado):
    assert identidad.es_web(usuario_id) is esperado


def test_la_identidad_de_una_cuenta_es_su_numero_en_negativo():
    assert identidad.de_cuenta_web(12) == "-12"
    assert identidad.es_web(identidad.de_cuenta_web(1))
    with pytest.raises(ValueError):
        identidad.de_cuenta_web(0)


def test_hoy_quien_no_tiene_aviso_es_justo_la_identidad_web():
    assert identidad.sin_aviso_de_hambre(WEB)
    assert not identidad.sin_aviso_de_hambre(DISCORD)


def test_el_hambre_no_mata_al_gachamon_de_una_identidad_web():
    avanzada = sim.avanzar(criatura(WEB), T0 + timedelta(days=30))
    assert avanzada.viva and avanzada.muerta_en is None
    assert avanzada.hambre == 0.0


def test_el_hambre_sigue_matando_al_de_una_identidad_de_discord():
    avanzada = sim.avanzar(criatura(DISCORD), T0 + timedelta(days=30))
    assert not avanzada.viva
    assert avanzada.causa_muerte == "hambre"


def test_al_de_una_identidad_web_le_bajan_las_tres_barras_como_a_cualquiera():
    diez_horas = T0 + timedelta(hours=10)
    web = sim.avanzar(criatura(WEB), diez_horas)
    discord = sim.avanzar(criatura(DISCORD), diez_horas)
    assert (web.hambre, web.animo, web.limpieza) == (
        discord.hambre, discord.animo, discord.limpieza
    )
    assert web.hambre < 100


def test_a_una_identidad_web_no_se_le_guarda_reloj_de_muerte_ni_de_aviso():
    db.crear(WEB, "g", "pollito", "Pelusa", STATS, T0)
    db.crear(DISCORD, "g", "pollito", "Otra", STATS, T0)
    assert relojes_de(WEB) == [(None, None, None)]
    muere_en, avisa_en, _ = relojes_de(DISCORD)[0]
    assert muere_en is not None and avisa_en is not None


def test_los_bucles_del_bot_nunca_ven_a_una_identidad_web():
    db.crear(WEB, "g", "pollito", "Pelusa", STATS, T0)
    db.crear(DISCORD, "g", "pollito", "Otra", STATS, T0)
    lejos = T0 + timedelta(days=30)
    assert {c.usuario_id for c in db.pendientes_de_morir(lejos)} == {DISCORD}
    assert {c.usuario_id for c in db.pendientes_de_aviso(lejos)} == {DISCORD}


def test_cambiar_de_activo_no_le_devuelve_la_muerte():
    db.crear(WEB, "g", "pollito", "Uno", STATS, T0)
    reserva = db.crear(WEB, "g", "pulpo", "Dos", STATS, T0, activa=False)
    assert db.activar(reserva.id, WEB, "g", T0 + timedelta(hours=1))
    assert all(reloj == (None, None, None) for reloj in relojes_de(WEB))


def test_tras_dias_en_cero_come_con_normalidad_y_sigue_sin_reloj():
    # Cinco días y no treinta: tiene que caer dentro de los siete de refugio.
    # Pasados esos, quien no tiene casa está a la intemperie y ahí el hambre ya
    # tiene un suelo de 25 para todo el mundo, así que no se probaría nada.
    db.crear(WEB, "g", "pollito", "Pelusa", STATS, T0)
    resultado = economia.ejecutar_cuidado(
        "evento-1", WEB, "g", sim.ALIMENTAR, T0 + timedelta(days=5)
    )
    assert resultado is not None and resultado.ok
    assert resultado.criatura.viva
    assert resultado.criatura.hambre == sim.EFECTOS_CUIDADO[sim.ALIMENTAR]["hambre"]
    assert relojes_de(WEB) == [(None, None, None)]
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_identidad.py -q`
Expected: FAIL en la recolección, con `ModuleNotFoundError: No module named 'identidad'`.

- [ ] **Step 3: Crear `identidad.py` con las tres funciones de Interfaces**

Módulo puro, sin importar nada del proyecto. El docstring del módulo explica por qué existe `sin_aviso_de_hambre` aparte de `es_web`: es la pregunta que hacen las reglas, y el día que haya notificaciones su respuesta deja de coincidir con la otra.

- [ ] **Step 4: Aplicar la excepción en `simulacion.avanzar`**

Antes: `impact({target: "avanzar", direction: "upstream"})`.

En el tramo final de `avanzar`, el hambre en 0 sólo mata si `not identidad.sin_aviso_de_hambre(criatura.usuario_id)`. En el otro caso devuelve `avanzada` con `hambre=0.0`, viva. Se decide dentro de `sim.avanzar` y no en `db.avanzar` a propósito: hay sitios que llaman a `sim.avanzar` a secas, y ninguno puede matar a esta criatura por olvido. Ampliar el docstring de `avanzar` con esa razón.

- [ ] **Step 5: No guardar los dos relojes en `db._a_valores`**

Antes: `impact({target: "_a_valores", direction: "upstream"})`.

`muere_en` y `avisa_en` quedan a `None` también cuando `identidad.sin_aviso_de_hambre(criatura.usuario_id)`. Es la misma idea que ya protege a las de la incubadora: los dos bucles del bot piden `IS NOT NULL`, así que no hay que tocar ninguna consulta. Ampliar el comentario que ya está ahí.

Si `db.crear`, `db.activar` u otro camino escriben esos dos relojes sin pasar por `_a_valores`, las pruebas `test_a_una_identidad_web_no_se_le_guarda…` y `test_cambiar_de_activo…` lo delatan: se corrige también ahí.

- [ ] **Step 6: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_identidad.py -q`
Expected: PASS, 22 passed.

- [ ] **Step 7: Auditar dónde el bot nombra a un dueño**

Run: `grep -n '<@{' *.py cogs/*.py`
Expected: seis líneas — `cogs/mascota.py` en los dos avisos del bucle (muerte y hambre), y `vistas.py` en cuatro respuestas a quien pulsa un botón de una ficha ajena.

Ninguna puede alcanzar a una identidad web: los dos bucles ya no las ven (lo fija `test_los_bucles_del_bot_nunca_ven_a_una_identidad_web`), y las cuatro de `vistas.py` sólo se disparan desde una ficha publicada en Discord, que una identidad web no tiene. Si el `grep` enseña una línea más, es un sitio nuevo que hay que mirar antes de seguir. El jardín, el ranking y el cementerio muestran al gachamon y no a su dueño, así que no hay nada que cambiar en ellos.

- [ ] **Step 8: Anotar los invariantes en `AGENTS.md`**

En «Invariantes del dominio», añadir:

```markdown
- Una identidad web es una persona más: su `usuario_id` no puede ser un id de Discord, y sólo `identidad.py` sabe reconocerla.
- El gachamon de quien no tiene aviso de hambre no muere de hambre: la comida se queda en 0 y no se le guarda instante de muerte ni de aviso.
- Esa excepción se pregunta siempre con `identidad.sin_aviso_de_hambre`, nunca mirando el id.
```

- [ ] **Step 9: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files
git diff --check
git add identidad.py simulacion.py db.py AGENTS.md tests/test_identidad.py
git commit -m "feat(identidad): el gachamon de una identidad web no muere de hambre"
```

Expected: los dos hooks en `Passed`.

---

### Task 2: Monedas y gemas

Cambia sólo lo que lee un jugador. El concepto pasa de masculino a femenino, así que hay que rehacer la frase entera y no sustituir la palabra: «los asciicoins» → «las monedas», «para gastarlos» → «para gastarlas».

**Files:**
- Modify: `objetos.py:27` (`MONEDA_TIENDA`), `comun.py:104`, `pantalla.py:433`, `vistas.py:367,880`, `tienda.py:36,37,42,102,423`, `cogs/aventura.py:658,660`, `cogs/competencias.py:143`, `cogs/social.py:445-483`, y cualquier otro literal que señale la prueba del Step 1
- Modify: `README.md` (≈ líneas 396–416, «Consumibles» y «Economía»), `AGENTS.md` (líneas 81, 82, 85, 86 y 122)
- Test: `tests/test_textos.py`, más las pruebas que hoy esperan el nombre viejo

**Interfaces:**
- Consumes: nada.
- Produces: `objetos.MONEDA_TIENDA == "monedas"`. Ningún otro nombre público cambia.

- [ ] **Step 1: Escribir las pruebas que fallan**

Añadir al final de `tests/test_textos.py` (`re` y `Path` ya están importados; falta `import ast`):

```python
RAIZ = Path(__file__).resolve().parent.parent
# Estos tres guardan SQL y nombres de columna, que conservan el nombre viejo a
# propósito: renombrarlos no le da nada a quien juega.
SIN_TEXTO_DE_JUGADOR = {"db.py", "economia.py", "economia_reporte.py"}
NOMBRE_VIEJO = re.compile(r"ascii\s?(coin|gem)", re.IGNORECASE)


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
    ]
    assert not culpables, "\n".join(culpables)


def test_el_manual_publicado_habla_de_monedas_y_gemas():
    manual = "\n".join(social.paginas_de_ayuda("Gachamon"))
    assert not NOMBRE_VIEJO.search(manual)
    assert "monedas" in manual and "gemas" in manual


def test_la_ficha_nombra_las_monedas_en_femenino():
    assert objetos.MONEDA_TIENDA == "monedas"
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_textos.py -q -k "asciicoins or monedas"`
Expected: FAIL. La primera lista cada literal culpable con su archivo y su línea: esa lista es el trabajo del Step 3.

- [ ] **Step 3: Reescribir cada texto**

Antes: `impact({target: "MONEDA_TIENDA", direction: "upstream"})`.

Recorrer la lista del Step 2 y reescribir cada frase con «monedas» y «gemas», cuidando el género de artículos, pronombres y participios. No tocar identificadores, argumentos con nombre (`asciicoins=`), atributos (`saldos.asciicoins`) ni SQL.

- [ ] **Step 4: Poner al día las pruebas que esperaban el nombre viejo**

Run: `./venv/bin/python -m pytest tests/ -q`
Las que fallen por comparar contra un texto con «asciicoins» o «asciigems» se actualizan al texto nuevo. Una prueba que use `saldos.asciicoins` o una columna no se toca.

Expected al terminar: PASS, toda la suite.

- [ ] **Step 5: Poner al día `README.md` y `AGENTS.md`**

En los dos, los párrafos que nombran las monedas pasan a decir «monedas» y «gemas». En `AGENTS.md`, añadir tras la última línea que las nombra:

```markdown
- A quien juega se le dice siempre «monedas» y «gemas»; `asciicoins` y `asciigems` son sólo nombres internos de columnas y atributos.
```

- [ ] **Step 6: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files
git diff --check
git add -A
git commit -m "feat(economia): las asciicoins y asciigems pasan a llamarse monedas y gemas"
```

---

### Task 3: Los marcos y los tintes salen del catálogo

Dejan de venderse y de poder ponerse. El dinero se devuelve en la tarea 4; aquí sólo desaparecen de la tienda.

`cosmeticos.buscar` ya está pensado para esto: una fila vieja con una clave retirada pinta la ficha sin esa pieza. Por eso `color_del_tinte`, `marco_de` y `REDONDO` **no se tocan**: el dibujo ASCII del bot sigue funcionando y se va entero cuando se apague el bot.

**Files:**
- Modify: `cosmeticos.py`
- Modify: `cogs/social.py:486-488` (el manual deja de anunciar tintes y marcos)
- Modify: `AGENTS.md`
- Test: `tests/test_cosmeticos.py`, `tests/test_taller.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `cos.TIPOS == (cos.SOMBRERO, cos.TITULO)`
  - `cos.TIPOS_RETIRADOS == (cos.TINTE, cos.MARCO)` — son también los nombres de las dos columnas de `criaturas` que quedan huérfanas.
  - `cos.RETIRADOS: dict[str, int]` — clave → gemas a devolver. Once entradas: los ocho tintes a 20 y los tres marcos a 50, calculadas desde `TINTES`, `MARCOS` y `PRECIOS`, que siguen definidos.
  - `cos.CATALOGO` — doce entradas: seis sombreros y seis títulos.

- [ ] **Step 1: Escribir las pruebas que fallan**

Añadir a `tests/test_cosmeticos.py`:

```python
def test_los_marcos_y_los_tintes_ya_no_estan_en_el_catalogo():
    assert cos.TIPOS == (cos.SOMBRERO, cos.TITULO)
    assert {c.tipo for c in cos.CATALOGO.values()} == {cos.SOMBRERO, cos.TITULO}
    assert len(cos.CATALOGO) == 12
    assert cos.del_tipo(cos.TINTE) == () and cos.del_tipo(cos.MARCO) == ()


def test_lo_retirado_sabe_cuanto_hay_que_devolver():
    assert cos.TIPOS_RETIRADOS == (cos.TINTE, cos.MARCO)
    assert len(cos.RETIRADOS) == 11
    assert cos.RETIRADOS["tinte_rojo"] == 20
    assert cos.RETIRADOS["marco_doble"] == 50
    assert sorted(set(cos.RETIRADOS.values())) == [20, 50]
    assert not set(cos.RETIRADOS) & set(cos.CATALOGO)


def test_un_gachamon_con_piezas_retiradas_se_pinta_como_si_no_llevara_nada():
    con_retiradas = criatura(tinte="tinte_rojo", marco="marco_doble")
    assert pantalla.render(con_retiradas, T0) == pantalla.render(criatura(), T0)


def test_una_pieza_retirada_no_se_puede_comprar():
    retirada = cos.Cosmetico("tinte_rojo", cos.TINTE, "Rojo", esp.ROJO)
    with pytest.raises(ValueError):
        economia.comprar_cosmetico("u", "g", retirada)
```

`test_una_pieza_retirada_no_se_puede_comprar` necesita `import economia` e `import especies as esp`. No necesita base: `comprar_cosmetico` rechaza una pieza fuera del catálogo antes de abrir ninguna conexión.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_cosmeticos.py -q -k "retirad or ya_no_estan"`
Expected: FAIL — `AttributeError: module 'cosmeticos' has no attribute 'TIPOS_RETIRADOS'` y catálogo de 23.

- [ ] **Step 3: Cambiar `cosmeticos.py`**

Antes: `impact({target: "TIPOS", direction: "upstream"})` e `impact({target: "CATALOGO", direction: "upstream"})`.

`TIPOS` y `CATALOGO` quedan como dice Interfaces; se añaden `TIPOS_RETIRADOS` y `RETIRADOS`. `TINTES`, `MARCOS` y `PRECIOS` no se borran. Reescribir el docstring del módulo y los comentarios de las secciones de tintes y marcos: ya no describen algo que se vende, sino por qué se retiró y que su único uso es calcular la devolución.

Ojo con `db._migrar`: recorre `cos.TIPOS` para volcar al ropero lo que cada gachamon lleva puesto, **en cada arranque**. Al encoger `TIPOS` deja de volcar tintes y marcos, y eso es justo lo que hace falta: si los siguiera volcando, una pieza ya devuelta reaparecería en el ropero.

- [ ] **Step 4: Quitar del manual las dos líneas que los anuncian**

`cogs/social.py`, en la página de las gemas: fuera el renglón del tinte y el del marco. Quedan el sombrero y el título.

- [ ] **Step 5: Poner al día las pruebas que hablaban de marcos y tintes**

En `tests/test_cosmeticos.py`:

- Se borran, porque su objeto ya no existe: `test_el_tinte_sustituye_al_color_de_la_especie`, `test_ningun_tinte_descuadra_la_caja`, `test_cada_marco_cierra_todas_sus_esquinas`, `test_ningun_marco_cambia_el_ancho_ni_el_alto`, `test_el_marco_no_toca_lo_de_dentro`, `test_todas_las_piezas_de_un_marco_son_distintas_del_relleno` y `test_el_tinte_se_ve_tambien_en_el_jardin_y_en_el_ranking`.
- Se reescriben con sombrero y título solamente: `test_ninguna_clave_se_repite_y_hay_de_los_cuatro_tipos` (pasa a «de los dos tipos»), `test_los_cuatro_a_la_vez_no_descuadran_nada` (pasa a «los dos a la vez») y `test_los_cosmeticos_se_ven_tambien_cuando_esta_hambriento`.

En `tests/test_taller.py`: la constante `ROJO` pasa a ser un título, `INVICTO = cos.CATALOGO["titulo_invicto"]`, y cada aserción que miraba `.tinte` o `cos.TINTE` mira `.titulo` o `cos.TITULO` con `"titulo_invicto"`.

`tests/test_retrato.py:123` no se toca: `cos.TINTES` sigue existiendo y la regla que comprueba sigue siendo cierta para una fila vieja.

Run: `./venv/bin/python -m pytest tests/ -q`
Expected: PASS, toda la suite.

- [ ] **Step 6: Anotar el invariante en `AGENTS.md`**

```markdown
- Los marcos y los tintes están retirados: no se venden ni se ponen, y `cosmeticos.RETIRADOS` sólo existe para saber cuánto devolver.
```

- [ ] **Step 7: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files
git diff --check
git add -A
git commit -m "feat(cosmeticos): los marcos y los tintes salen del catálogo"
```

---

### Task 4: La devolución de marcos y tintes

Una sola pasada que devuelve las gemas, saca las piezas de los roperos y se las quita a quien las lleve. Corre en cada arranque y no hace nada la segunda vez.

**Files:**
- Modify: `db.py` — `SCHEMA_TABLAS` (tabla nueva)
- Modify: `economia.py` — función nueva y su dataclass
- Modify: `bot.py` — `setup_hook()`
- Modify: `AGENTS.md`
- Test: `tests/test_economia_devolucion.py`

**Interfaces:**
- Consumes: `cos.RETIRADOS` y `cos.TIPOS_RETIRADOS` (tarea 3).
- Produces:
  - Tabla `devoluciones`:

    ```sql
    CREATE TABLE IF NOT EXISTS devoluciones (
        usuario_id TEXT NOT NULL,
        guild_id TEXT NOT NULL,
        cosmetico TEXT NOT NULL,
        gemas INTEGER NOT NULL CHECK (gemas > 0),
        devuelta_en TEXT NOT NULL,
        PRIMARY KEY (usuario_id, guild_id, cosmetico)
    );
    ```
  - `economia.ResumenDevolucion` — dataclass congelada con `personas: int`, `piezas: int`, `gemas: int`.
  - `economia.devolver_cosmeticos_retirados(ahora: datetime) -> ResumenDevolucion`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_economia_devolucion.py`:

```python
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

import db
import economia

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (10, 10, 10, 10)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "devolucion.db")
    db.inicializar()


def con_piezas(usuario: str, *claves: str) -> None:
    with db.conectar() as con:
        for clave in claves:
            db.guardar_en_el_ropero_en(con, usuario, "g", clave)


def vestir(criatura_id: int, **piezas: str) -> None:
    asignaciones = ", ".join(f"{columna} = ?" for columna in piezas)
    with db.conectar() as con:
        con.execute(
            f"UPDATE criaturas SET {asignaciones} WHERE id = ?",
            (*piezas.values(), criatura_id),
        )


def gemas_de(usuario: str) -> int:
    return economia.saldos(usuario, "g").asciigems


def cuantas(tabla: str) -> int:
    with db.conectar() as con:
        return con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


def test_devuelve_veinte_por_tinte_y_cincuenta_por_marco():
    con_piezas("u", "tinte_rojo", "marco_doble", "corona")
    resumen = economia.devolver_cosmeticos_retirados(T0)
    assert (resumen.personas, resumen.piezas, resumen.gemas) == (1, 2, 70)
    assert gemas_de("u") == 50 + 70
    assert db.ropero("u", "g") == {"corona"}


def test_cada_persona_recibe_lo_suyo():
    con_piezas("a", "tinte_rojo", "tinte_azul")
    con_piezas("b", "marco_fino")
    resumen = economia.devolver_cosmeticos_retirados(T0)
    assert (resumen.personas, resumen.piezas, resumen.gemas) == (2, 3, 90)
    assert (gemas_de("a"), gemas_de("b")) == (90, 100)


def test_repetirla_no_paga_dos_veces():
    con_piezas("u", "tinte_rojo")
    economia.devolver_cosmeticos_retirados(T0)
    segunda = economia.devolver_cosmeticos_retirados(T0 + timedelta(days=1))
    assert (segunda.personas, segunda.piezas, segunda.gemas) == (0, 0, 0)
    assert gemas_de("u") == 70


def test_ni_aunque_la_pieza_reaparezca_en_el_ropero():
    con_piezas("u", "tinte_rojo")
    economia.devolver_cosmeticos_retirados(T0)
    con_piezas("u", "tinte_rojo")   # una base restaurada a medias, por ejemplo
    economia.devolver_cosmeticos_retirados(T0)
    assert gemas_de("u") == 70
    assert db.ropero("u", "g") == frozenset()


def test_se_la_quita_a_quien_la_lleva_y_le_deja_lo_demas():
    viva = db.crear("u", "g", "pollito", "Viva", STATS, T0)
    con_piezas("u", "tinte_rojo", "marco_doble", "corona")
    vestir(viva.id, tinte="tinte_rojo", marco="marco_doble", sombrero="corona")
    economia.devolver_cosmeticos_retirados(T0)
    despues = db.por_id(viva.id)
    assert (despues.tinte, despues.marco, despues.sombrero) == (None, None, "corona")


def test_tambien_se_la_quita_a_un_gachamon_muerto():
    muerta = db.crear("u", "g", "pollito", "Ida", STATS, T0)
    con_piezas("u", "tinte_rojo")
    vestir(muerta.id, tinte="tinte_rojo", muerta_en=T0.isoformat())
    economia.devolver_cosmeticos_retirados(T0)
    assert db.por_id(muerta.id).tinte is None
    assert gemas_de("u") == 70


def test_una_pieza_puesta_que_no_estaba_en_el_ropero_tambien_se_devuelve():
    viva = db.crear("u", "g", "pollito", "Viva", STATS, T0)
    vestir(viva.id, marco="marco_grueso")
    resumen = economia.devolver_cosmeticos_retirados(T0)
    assert resumen.piezas == 1 and gemas_de("u") == 100
    assert db.por_id(viva.id).marco is None


def test_queda_anotada_y_no_pasa_por_el_libro_de_las_monedas():
    con_piezas("u", "marco_doble")
    economia.devolver_cosmeticos_retirados(T0)
    with db.conectar() as con:
        fila = con.execute("SELECT * FROM devoluciones").fetchone()
    assert (fila["usuario_id"], fila["cosmetico"], fila["gemas"]) == (
        "u", "marco_doble", 50,
    )
    assert fila["devuelta_en"] == T0.isoformat()
    assert cuantas("operaciones_economia") == 0


def test_quien_no_tenia_nada_retirado_no_recibe_nada():
    con_piezas("u", "corona", "titulo_veloz")
    resumen = economia.devolver_cosmeticos_retirados(T0)
    assert (resumen.personas, resumen.piezas, resumen.gemas) == (0, 0, 0)
    assert gemas_de("u") == 50
    assert db.ropero("u", "g") == {"corona", "titulo_veloz"}
    assert cuantas("devoluciones") == 0


def test_dos_arranques_a_la_vez_pagan_una_sola_vez():
    con_piezas("u", "tinte_rojo", "marco_doble")
    with ThreadPoolExecutor(max_workers=2) as hilos:
        resumenes = list(hilos.map(
            lambda _: economia.devolver_cosmeticos_retirados(T0), range(2)
        ))
    assert sorted(r.piezas for r in resumenes) == [0, 2]
    assert gemas_de("u") == 50 + 70
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_economia_devolucion.py -q`
Expected: FAIL — `AttributeError: module 'economia' has no attribute 'devolver_cosmeticos_retirados'`.

- [ ] **Step 3: Añadir la tabla `devoluciones` a `db.SCHEMA_TABLAS`**

Con el DDL de Interfaces y un comentario que diga para qué es: el registro de lo devuelto y, a la vez, la garantía de que no se paga dos veces.

- [ ] **Step 4: Implementar `economia.devolver_cosmeticos_retirados`**

Todo dentro de un único `BEGIN IMMEDIATE`, en este orden:

1. Volcar al ropero lo retirado que aún esté puesto: por cada columna de `cos.TIPOS_RETIRADOS`, `INSERT OR IGNORE INTO ropero` desde `criaturas` donde esa columna no sea nula. Sin filtrar por vivas, igual que hace `db._migrar` con las demás piezas.
2. Por cada fila del ropero cuya pieza esté en `cos.RETIRADOS`: `INSERT OR IGNORE INTO devoluciones`. **Sólo si esa inserción entró** —`cursor.rowcount`, el mismo patrón que `db.guardar_en_el_ropero_en`— se asegura el monedero y se le suman las gemas.
3. Borrar del ropero todas las filas con una pieza retirada, hayan pagado o no.
4. Dejar a `NULL` las columnas de `cos.TIPOS_RETIRADOS` en todas las criaturas, vivas y muertas.

Devuelve el resumen de lo pagado **en esta pasada**. No escribe en `operaciones_economia`: su `CHECK` sólo admite monedas, y aquí la protección contra el doble pago es la clave primaria de `devoluciones`.

- [ ] **Step 5: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_economia_devolucion.py -q`
Expected: PASS, 10 passed.

- [ ] **Step 6: Llamarla al arrancar el bot**

Antes: `impact({target: "setup_hook", direction: "upstream"})`.

En `bot.py`, justo después de `db.inicializar()`: llamar a `economia.devolver_cosmeticos_retirados(db.ahora_utc())` y, si `piezas` no es cero, dejarlo en el registro con `log.info` — personas, piezas y gemas, sin ningún id. `bot.py` pasa a importar `economia`.

- [ ] **Step 7: Anotar los invariantes en `AGENTS.md`**

```markdown
- Lo retirado se devuelve una sola vez por persona y pieza: lo garantiza la clave primaria de `devoluciones`, y pagar ocurre en la misma transacción que anotarla.
- Una devolución no es una ganancia: no pasa por el tope diario ni por `operaciones_economia`.
```

- [ ] **Step 8: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files
git diff --check
git add -A
git commit -m "feat(economia): devuelve las gemas de los marcos y tintes retirados"
```

---

### Task 5: Cuentas web y códigos de vinculación

La base de la vinculación, sin Discord y sin web: quién es cada cuenta de Rowino en el juego y cómo se canjea un código. El plan 2 usará `cuenta_web`, `crear_identidad_web` y `pedir_codigo_de_vinculo`; la tarea 6 usa `canjear_codigo_de_vinculo`.

**Files:**
- Create: `vinculo.py`
- Modify: `db.py` — `SCHEMA_TABLAS` (tres tablas) y cuatro funciones
- Modify: `config.py`, `.env.ejemplo` — `GUILD_WEB`
- Modify: `AGENTS.md`
- Test: `tests/test_vinculo.py`

**Interfaces:**
- Consumes: `identidad.de_cuenta_web` (tarea 1).
- Produces, en `vinculo.py` (puro):
  - `ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"` — sin `I`, `L`, `O`, `0` ni `1`.
  - `LARGO = 8`, `MINUTOS_DE_VIDA = 10`, `INTENTOS_MAXIMOS = 5`, `VENTANA_DE_INTENTOS = timedelta(minutes=10)`.
  - `OK = "ok"`, `INVALIDO = "invalido"`, `DEMASIADOS = "demasiados"`, `YA_VINCULADA = "ya_vinculada"`, `CON_GACHAMONES = "con_gachamones"`.
  - `nuevo_codigo(rng: random.Random | None = None) -> str` — con `rng` es determinista; sin él usa `secrets`.
  - `normalizar(codigo: str) -> str` — mayúsculas, sin espacios ni guiones.
  - `class NoSePuede(Exception)` con el atributo `motivo: str`.
  - `MENSAJES: dict[str, str]` — lo que el bot contesta a cada resultado de un canje:

    | Resultado | Texto |
    |---|---|
    | `OK` | `✅ Listo. Tu cuenta de Rowino quedó vinculada: vuelve a la web y vas a encontrar a tus gachamones.` |
    | `INVALIDO` | `Ese código no sirve. Pide uno nuevo en la web y escríbelo antes de que caduque.` |
    | `DEMASIADOS` | `Demasiados intentos. Espera unos minutos y pide un código nuevo.` |
    | `YA_VINCULADA` | `Tu cuenta de Discord ya está vinculada a una cuenta de Rowino. Si es un error, avísale a quien administra el servidor.` |

- Produces, en `db.py`:
  - `class CuentaWeb` — dataclass congelada: `rowino_uid: int`, `usuario_id: str`, `guild_id: str`, `vinculada: bool`.
  - `cuenta_web(rowino_uid: int) -> CuentaWeb | None`
  - `crear_identidad_web(rowino_uid: int, guild_id: str, ahora: datetime) -> CuentaWeb` — idempotente: si la cuenta ya tiene fila, la devuelve como está.
  - `pedir_codigo_de_vinculo(rowino_uid: int, ahora: datetime, rng: random.Random | None = None) -> str` — lanza `vinculo.NoSePuede` con motivo `YA_VINCULADA` o `CON_GACHAMONES`.
  - `canjear_codigo_de_vinculo(codigo: str, usuario_id: str, guild_id: str, ahora: datetime) -> str` — devuelve `OK`, `INVALIDO`, `DEMASIADOS` o `YA_VINCULADA`. Nunca lanza por un código raro.
- Produces, en `config.py`: `GUILD_WEB: int` — la variable de entorno `GUILD_WEB`; si no está, el primero de `GUILDS`; si tampoco, `0`.

Tablas nuevas:

```sql
CREATE TABLE IF NOT EXISTS cuentas_web (
    rowino_uid INTEGER PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    vinculada INTEGER NOT NULL DEFAULT 0,
    creada_en TEXT NOT NULL,
    UNIQUE (usuario_id, guild_id)
);
CREATE TABLE IF NOT EXISTS vinculos_pendientes (
    codigo TEXT PRIMARY KEY,
    rowino_uid INTEGER NOT NULL UNIQUE,
    vence_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS intentos_de_vinculo (
    usuario_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    en TEXT NOT NULL
);
```

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_vinculo.py`:

```python
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

import db
import vinculo

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (10, 10, 10, 10)
ANA, BETO = "111111111111111111", "222222222222222222"
G = "g"


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "vinculo.db")
    db.inicializar()


def test_el_codigo_mide_ocho_y_no_lleva_letras_que_se_confunden():
    codigo = vinculo.nuevo_codigo(random.Random(1))
    assert len(codigo) == vinculo.LARGO == 8
    assert set(codigo) <= set(vinculo.ALFABETO)
    assert not set("ILO01") & set(vinculo.ALFABETO)
    assert vinculo.nuevo_codigo(random.Random(1)) == codigo
    assert vinculo.nuevo_codigo() != vinculo.nuevo_codigo()


def test_normalizar_perdona_como_se_escribe_en_un_celular():
    assert vinculo.normalizar("  abcd-efgh ") == "ABCDEFGH"
    assert vinculo.normalizar("ab cd ef gh") == "ABCDEFGH"


def test_cada_resultado_de_un_canje_tiene_su_mensaje():
    assert set(vinculo.MENSAJES) == {
        vinculo.OK, vinculo.INVALIDO, vinculo.DEMASIADOS, vinculo.YA_VINCULADA,
    }
    assert all(len(texto) <= 2000 for texto in vinculo.MENSAJES.values())


def test_la_identidad_web_de_una_cuenta_es_su_numero_en_negativo():
    cuenta = db.crear_identidad_web(12, G, T0)
    assert cuenta == db.CuentaWeb(12, "-12", G, False)
    assert db.crear_identidad_web(12, G, T0 + timedelta(days=1)) == cuenta
    assert db.cuenta_web(12) == cuenta
    assert db.cuenta_web(99) is None


def test_canjear_un_codigo_vincula_la_cuenta_con_esa_persona_de_discord():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, T0) == vinculo.OK
    assert db.cuenta_web(12) == db.CuentaWeb(12, ANA, G, True)


def test_el_codigo_vale_escrito_con_minusculas_espacios_y_guiones():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    escrito = f" {codigo[:4].lower()}-{codigo[4:].lower()} "
    assert db.canjear_codigo_de_vinculo(escrito, ANA, G, T0) == vinculo.OK


def test_vale_hasta_un_segundo_antes_de_los_diez_minutos():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    justo_antes = T0 + timedelta(minutes=10) - timedelta(seconds=1)
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, justo_antes) == vinculo.OK


def test_a_los_diez_minutos_justos_ya_no_vale():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    a_los_diez = T0 + timedelta(minutes=10)
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, a_los_diez) == vinculo.INVALIDO
    assert db.cuenta_web(12) is None


def test_un_codigo_sirve_una_sola_vez():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, T0) == vinculo.OK
    assert db.canjear_codigo_de_vinculo(codigo, BETO, G, T0) == vinculo.INVALIDO


def test_pedir_otro_codigo_anula_el_anterior():
    viejo = db.pedir_codigo_de_vinculo(12, T0)
    nuevo = db.pedir_codigo_de_vinculo(12, T0 + timedelta(minutes=1))
    assert viejo != nuevo
    assert db.canjear_codigo_de_vinculo(viejo, ANA, G, T0 + timedelta(minutes=2)) == vinculo.INVALIDO
    assert db.canjear_codigo_de_vinculo(nuevo, ANA, G, T0 + timedelta(minutes=2)) == vinculo.OK


@pytest.mark.parametrize("basura", ["", "   ", "no-existe", "ñ" * 10_000, "'; DROP TABLE cuentas_web;--"])
def test_un_codigo_absurdo_es_invalido_y_no_rompe_nada(basura):
    db.pedir_codigo_de_vinculo(12, T0)
    assert db.canjear_codigo_de_vinculo(basura, ANA, G, T0) == vinculo.INVALIDO
    assert db.cuenta_web(12) is None


def test_una_persona_de_discord_no_puede_vincular_dos_cuentas():
    assert db.canjear_codigo_de_vinculo(db.pedir_codigo_de_vinculo(12, T0), ANA, G, T0) == vinculo.OK
    otro = db.pedir_codigo_de_vinculo(13, T0)
    assert db.canjear_codigo_de_vinculo(otro, ANA, G, T0) == vinculo.YA_VINCULADA
    assert db.cuenta_web(13) is None


def test_una_cuenta_ya_vinculada_no_puede_pedir_otro_codigo():
    db.canjear_codigo_de_vinculo(db.pedir_codigo_de_vinculo(12, T0), ANA, G, T0)
    with pytest.raises(vinculo.NoSePuede) as error:
        db.pedir_codigo_de_vinculo(12, T0)
    assert error.value.motivo == vinculo.YA_VINCULADA


def test_una_identidad_web_sin_gachamones_todavia_puede_vincularse():
    db.crear_identidad_web(12, G, T0)
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, T0) == vinculo.OK
    assert db.cuenta_web(12) == db.CuentaWeb(12, ANA, G, True)


def test_una_identidad_web_con_gachamones_ya_no_puede_pedir_codigo():
    cuenta = db.crear_identidad_web(12, G, T0)
    db.crear(cuenta.usuario_id, G, "pollito", "Pelusa", STATS, T0)
    with pytest.raises(vinculo.NoSePuede) as error:
        db.pedir_codigo_de_vinculo(12, T0)
    assert error.value.motivo == vinculo.CON_GACHAMONES


def test_si_el_gachamon_nace_entre_pedir_y_canjear_el_codigo_ya_no_sirve():
    cuenta = db.crear_identidad_web(12, G, T0)
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    db.crear(cuenta.usuario_id, G, "pollito", "Pelusa", STATS, T0)
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, T0) == vinculo.INVALIDO
    assert db.cuenta_web(12) == cuenta


def test_al_sexto_intento_en_diez_minutos_se_corta_aunque_el_codigo_sea_bueno():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    for _ in range(vinculo.INTENTOS_MAXIMOS):
        assert db.canjear_codigo_de_vinculo("MALMALMA", ANA, G, T0) == vinculo.INVALIDO
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, T0) == vinculo.DEMASIADOS
    assert db.canjear_codigo_de_vinculo(codigo, BETO, G, T0) == vinculo.OK


def test_pasada_la_ventana_se_puede_volver_a_intentar():
    for _ in range(vinculo.INTENTOS_MAXIMOS):
        db.canjear_codigo_de_vinculo("MALMALMA", ANA, G, T0)
    despues = T0 + vinculo.VENTANA_DE_INTENTOS + timedelta(seconds=1)
    codigo = db.pedir_codigo_de_vinculo(12, despues)
    assert db.canjear_codigo_de_vinculo(codigo, ANA, G, despues) == vinculo.OK


def test_dos_personas_canjeando_el_mismo_codigo_a_la_vez_solo_entra_una():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    with ThreadPoolExecutor(max_workers=2) as hilos:
        resultados = list(hilos.map(
            lambda quien: db.canjear_codigo_de_vinculo(codigo, quien, G, T0),
            (ANA, BETO),
        ))
    assert sorted(resultados) == sorted([vinculo.OK, vinculo.INVALIDO])
    assert db.cuenta_web(12).usuario_id in (ANA, BETO)
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_vinculo.py -q`
Expected: FAIL en la recolección, `ModuleNotFoundError: No module named 'vinculo'`.

- [ ] **Step 3: Crear `vinculo.py`**

Con todo lo de Interfaces. Puro: sólo importa `random`, `secrets` y `datetime`.

- [ ] **Step 4: Añadir las tres tablas y `CuentaWeb` a `db.py`**

El DDL de Interfaces va en `SCHEMA_TABLAS`. `db.py` importa `identidad` y `vinculo`, que son puros.

- [ ] **Step 5: Implementar `cuenta_web`, `crear_identidad_web` y `pedir_codigo_de_vinculo`**

`pedir_codigo_de_vinculo`, bajo `BEGIN IMMEDIATE`:

1. Si la cuenta tiene fila con `vinculada = 1` → `NoSePuede(YA_VINCULADA)`.
2. Si tiene fila sin vincular y esa identidad tiene alguna criatura, viva o muerta → `NoSePuede(CON_GACHAMONES)`.
3. Borrar los códigos vencidos de todo el mundo y el código vivo de esta cuenta.
4. Guardar el nuevo, con `vence_en = ahora + MINUTOS_DE_VIDA`, y devolverlo.

- [ ] **Step 6: Implementar `canjear_codigo_de_vinculo`**

Bajo `BEGIN IMMEDIATE`, en este orden. El orden es parte del contrato: es lo que hace que un código bueno no sirva para saltarse el límite, y que la respuesta no revele si un código existe.

1. Borrar los intentos de esa persona anteriores a `ahora - VENTANA_DE_INTENTOS`. Si le quedan `INTENTOS_MAXIMOS` o más → `DEMASIADOS`, sin anotar otro.
2. Anotar este intento.
3. Si esa persona de Discord ya figura en `cuentas_web` para ese servidor → `YA_VINCULADA`.
4. Buscar el código normalizado con `vence_en > ahora`. Si no está → `INVALIDO`.
5. Mirar la cuenta dueña del código. Si ya está vinculada, o si es una identidad web con alguna criatura → borrar el código y `INVALIDO`.
6. Dejar la fila de la cuenta con el `usuario_id` de Discord, ese `guild_id` y `vinculada = 1` —creándola o reemplazando la identidad web vacía—, borrar el código y devolver `OK`.

- [ ] **Step 7: Añadir `GUILD_WEB` a `config.py` y a `.env.ejemplo`**

En `.env.ejemplo`, con su comentario: es el servidor de Discord que hace de pueblo en la web; sólo ahí funciona `/vincular`; si se deja vacío vale el primero de `GUILD_ID`.

- [ ] **Step 8: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_vinculo.py -q`
Expected: PASS, 23 passed.

- [ ] **Step 9: Anotar los invariantes en `AGENTS.md`**

```markdown
- Una cuenta de Rowino va con una sola identidad, y una identidad de Discord con una sola cuenta de Rowino.
- Sólo se vincula mientras la identidad web no tenga gachamones: dos planteles no se funden.
- Un código de vinculación sirve una vez, caduca, y canjearlo nunca revela si existía.
- Quién escribió `/vincular` es la única prueba de identidad: el código lo pide la cuenta de Rowino y lo canjea la persona de Discord.
```

- [ ] **Step 10: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files
git diff --check
git add -A
git commit -m "feat(vinculo): cuentas web y códigos para vincular una identidad de Discord"
```

---

### Task 6: El comando `/vincular`

**Files:**
- Modify: `cogs/social.py` — comando nuevo en `Social`, y una línea en el manual
- Modify: `tests/test_carga.py` — `COMANDOS_ESPERADOS`
- Modify: `README.md` — tabla de comandos
- Test: `tests/test_vincular.py`

**Interfaces:**
- Consumes: `db.canjear_codigo_de_vinculo`, `db.pedir_codigo_de_vinculo`, `db.cuenta_web`, `vinculo.MENSAJES`, `config.GUILD_WEB` (tarea 5).
- Produces: el comando `vincular` del cog `Social`, con un parámetro `codigo: str`; descripción `Une tu cuenta de Rowino con tus gachamones de aquí`; descripción del parámetro `El código que te dio la web`.
- Produces: `social.SERVIDOR_SIN_WEB = "Este servidor no está conectado con la web."`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_vincular.py`:

```python
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import config
import db
import vinculo
from cogs import social

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
PUEBLO = 777


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "vincular.db")
    monkeypatch.setattr(db, "ahora_utc", lambda: T0)
    monkeypatch.setattr(config, "GUILD_WEB", PUEBLO)
    db.inicializar()


def escribir(codigo: str, servidor: int = PUEBLO, quien: int = 555):
    interaccion = SimpleNamespace(
        guild_id=servidor,
        user=SimpleNamespace(id=quien),
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    cog = social.Social(SimpleNamespace())
    asyncio.run(social.Social.vincular.callback(cog, interaccion, codigo))
    return interaccion.response.send_message


def test_vincular_canjea_el_codigo_y_contesta_solo_a_quien_lo_escribio():
    respuesta = escribir(db.pedir_codigo_de_vinculo(12, T0))
    respuesta.assert_awaited_once_with(vinculo.MENSAJES[vinculo.OK], ephemeral=True)
    assert db.cuenta_web(12) == db.CuentaWeb(12, "555", str(PUEBLO), True)


def test_un_codigo_malo_tambien_se_contesta_en_privado():
    respuesta = escribir("MALMALMA")
    respuesta.assert_awaited_once_with(
        vinculo.MENSAJES[vinculo.INVALIDO], ephemeral=True
    )


def test_en_otro_servidor_no_canjea_nada():
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    respuesta = escribir(codigo, servidor=1)
    respuesta.assert_awaited_once_with(social.SERVIDOR_SIN_WEB, ephemeral=True)
    assert db.cuenta_web(12) is None
    assert escribir(codigo).await_args.args[0] == vinculo.MENSAJES[vinculo.OK]
```

Si `social.Social` no se deja construir con un `SimpleNamespace` por lo que haga su `__init__`, construirlo como lo hace `tests/test_carga.py`.

En `tests/test_carga.py`, añadir `"vincular"` a `COMANDOS_ESPERADOS`.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_vincular.py tests/test_carga.py -q`
Expected: FAIL — `AttributeError: type object 'Social' has no attribute 'vincular'`, y `test_todos_los_cogs_cargan_y_registran_sus_comandos` por el comando que falta.

- [ ] **Step 3: Implementar el comando**

Lleva `@comun.solo_en_el_canal()` como todos —lo exige `test_ningun_comando_se_sale_de_su_canal`—. Si `interaccion.guild_id != config.GUILD_WEB` contesta `SERVIDOR_SIN_WEB` y no llama a la base. Si coincide, contesta `vinculo.MENSAJES[...]` con lo que devuelva `db.canjear_codigo_de_vinculo(codigo, str(interaccion.user.id), str(interaccion.guild_id), db.ahora_utc())`. Las dos respuestas, siempre con `ephemeral=True`. El cog no decide nada más.

- [ ] **Step 4: Decirlo en el manual y en el README**

En `paginas_de_ayuda`, donde se listan los comandos, una línea: `` `/vincular <código>` · une esta cuenta con la tuya de rowino.online ``. En `README.md`, la misma fila en la tabla «Comandos».

- [ ] **Step 5: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_vincular.py tests/test_carga.py tests/test_manual.py -q`
Expected: PASS. `test_manual.py` confirma que ninguna página pasó de 2000 caracteres.

- [ ] **Step 6: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files
git diff --check
git add -A
git commit -m "feat(social): /vincular une la cuenta de Rowino con la identidad de Discord"
```

---

### Task 7: Comprobar en seco la regla por ruta del túnel

El diseño (5.1) pide saber esto **antes de ordenar el plan 2**: si el túnel puede mandar `rowino.online/gachamon/*` a otro servicio, Rowino casi no se toca; si no, Rowino tiene que reenviar esa ruta y el plan 2 crece. `cloudflared` sabe validar un archivo de reglas y decir qué regla atiende una dirección **sin reiniciar nada**, así que esta tarea no cambia nada en producción: lee la configuración real, escribe una copia en `/tmp` de la Pi y pregunta.

**Files:**
- Create: `docs/superpowers/specs/2026-11-12-tunel-regla-por-ruta.md`

**Interfaces:**
- Consumes: acceso por SSH a la Pi, el mismo `PI` que usa `actualizar-pi.sh` (`felipe@192.168.1.109`).
- Produces: el documento, con la regla exacta que funcionó o el motivo por el que no; el plan 2 parte de él.

- [ ] **Step 1: Armar la copia de prueba en la Pi**

```bash
PI="${PI:-felipe@192.168.1.109}"
ssh "$PI" 'cloudflared --version'
ssh "$PI" 'python3 - <<"EOF"
from pathlib import Path
original = Path("/etc/cloudflared/config.yml").read_text()
regla = (
    "  - hostname: rowino.online\n"
    "    path: ^/gachamon(/.*)?$\n"
    "    service: http://localhost:8010\n"
)
marca = "  - hostname: rowino.online\n"
assert original.count(marca) == 1, "se esperaba una sola regla para rowino.online"
Path("/tmp/tunel-prueba.yml").write_text(original.replace(marca, regla + marca))
EOF'
```

Expected: la versión de `cloudflared` y ningún error.

- [ ] **Step 2: Validar y preguntar qué regla atiende cada dirección**

```bash
ssh "$PI" 'cloudflared tunnel --config /tmp/tunel-prueba.yml ingress validate'
for url in https://rowino.online/gachamon https://rowino.online/gachamon/ \
           https://rowino.online/gachamon/api/estado https://rowino.online/generar \
           https://rowino.online/gachamones https://rowino.online/; do
  echo "== $url"; ssh "$PI" "cloudflared tunnel --config /tmp/tunel-prueba.yml ingress rule $url"
done
ssh "$PI" 'rm /tmp/tunel-prueba.yml'
```

Expected: `OK` en la validación; las tres primeras direcciones caen en `http://localhost:8010`; `/generar`, `/gachamones` y `/` caen en `http://localhost:8000`.

- [ ] **Step 3: Escribir lo encontrado**

En `docs/superpowers/specs/2026-11-12-tunel-regla-por-ruta.md`: la versión de `cloudflared`, la regla probada, la salida de cada pregunta y una conclusión de una línea — «la regla por ruta sirve» o «no sirve, por esto». Si no sirve, decir qué se vio y dejar anotado que el plan 2 tiene que usar el reenvío desde Rowino.

El repositorio es público: **no copiar** el identificador del túnel, la ruta de sus credenciales ni las reglas de otros sitios. Si esa versión de `cloudflared` no tiene el subcomando `ingress rule`, anotar la salida de `cloudflared tunnel ingress --help` y decirlo en la conclusión.

Recordar en el documento lo que **no** se probó: aplicar la regla de verdad pide `sudo` y reiniciar el túnel, corta unos segundos todos los sitios y necesita la autorización de Felipe en el momento. Eso es del plan 2.

- [ ] **Step 4: Commit**

```bash
git diff --check
git add docs/superpowers/specs/2026-11-12-tunel-regla-por-ruta.md
git commit -m "docs(web): la regla por ruta del túnel, comprobada en seco"
```

---

### Task 8: Cierre y entrega a Felipe

Nada de esto llega a producción sin que Felipe lo diga. La Pi baja el código de GitHub, así que desplegar es subir, fusionar a `main` y correr `./actualizar-pi.sh`: tres cosas que piden su autorización.

**Files:** ninguno nuevo.

**Interfaces:**
- Consumes: las tareas 1 a 7 confirmadas en `web/1-reglas-y-bot`.
- Produces: un resumen para Felipe y, con su sí, el despliegue.

- [ ] **Step 1: Verificación de toda la rama**

```bash
./venv/bin/python -m pre_commit run --all-files
git diff --check main...HEAD
git log --oneline main..HEAD
```

Y con GitNexus: `detect_changes({scope: "compare", base_ref: "main"})`.

Expected: los dos hooks en `Passed`; el historial con los dos commits del diseño y uno por tarea; ningún proceso afectado fuera de cuidado, economía, cosméticos y el arranque del bot.

- [ ] **Step 2: Comprobar a mano lo que ningún test mira**

```bash
./venv/bin/python - <<'EOF'
from cogs import social
for n, pagina in enumerate(social.paginas_de_ayuda("Gachamon"), 1):
    print(f"--- página {n} ({len(pagina)} caracteres)")
    print(pagina)
EOF
```

Leer el manual entero como lo leería un jugador: que hable de monedas y gemas con el género bien puesto, que no ofrezca tintes ni marcos y que mencione `/vincular`.

- [ ] **Step 3: Contarle a Felipe qué va a pasar al desplegar y pedirle el sí**

En lenguaje llano, lo que verán los jugadores de Discord en cuanto arranque el bot nuevo:

- Las monedas y las gemas cambian de nombre en todos los mensajes y en el manual.
- Los marcos y los tintes desaparecen de la tienda y de los gachamones que los llevaban, y cada dueño recibe 50 o 20 gemas por pieza. El registro del bot dice cuántas personas, piezas y gemas fueron.
- Aparece `/vincular`, que no sirve para nada hasta que exista la web.

Y lo que hay que hacer en la Pi además del código: añadir `GUILD_WEB` al `.env` con el id de Robot House.

Preguntarle si conviene avisar en el canal antes, porque a alguien se le va a ir el tinte sin haber hecho nada.

- [ ] **Step 4: Con su autorización, desplegar**

```bash
git push -u origin web/1-reglas-y-bot      # y el PR o la fusión que él prefiera
./actualizar-pi.sh                         # copia la base, corre la suite en la Pi y reinicia
ssh felipe@192.168.1.109 'journalctl -u tamagotchi -n 40 --no-pager'
```

Expected en el registro: el arranque sin errores, la línea de la devolución con sus tres números, y el manual editado en su canal. `actualizar-pi.sh` deja una copia de la base antes de tocar nada; si algo sale mal, esa copia es la vuelta atrás.
