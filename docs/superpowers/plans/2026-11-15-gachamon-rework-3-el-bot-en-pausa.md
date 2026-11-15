# Rework 3 · El bot en pausa — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el juego de Discord quede en pausa: el bot sólo atiende `/vincular` y contesta a todo lo demás que el juego se mudó a la página, y el código del juego de Discord sale de la rama.

**Architecture:** Primero se construye el bot nuevo, pequeño, en un cog aparte (`cogs/mudanza.py`), y `bot.py` pasa a cargar sólo ése; con eso el juego de Discord deja de arrancar aunque su código siga en el árbol. Después se borra ese código (cogs, fichas, menús y sus pruebas), se quitan las pocas reglas que existían sólo para Discord y que el diseño no trae de vuelta, la web deja de mandar a Discord, y se corrigen los documentos. Las reglas que el proyecto 6 llevará a la página se quedan, con sus pruebas.

**Tech Stack:** Python 3.12, discord.py 2.7.1, FastAPI, SQLite síncrono, pytest y `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-14-gachamon-rework-1-departamento-design.md` (sección 7, «Discord, en pausa»; de la 1, la decisión del 2026-11-15).

**Dónde encaja.** Es el plan 3 de 7 del proyecto 1 del rework: (1) nadie muere — hecho; (2) el tiempo para todos — hecho; (3) el bot en pausa; (4) la vivienda por casillas en el servidor y el día del cambio; (5) el departamento en pantalla; (6) los muebles que se usan solos; (7) el pueblo sin Refugio ni Incubadora y los documentos. Los siete se juntan en la rama `rework/1-departamento` y **se publican juntos al final**: hasta ese día, en producción el bot sigue jugando como hoy.

**Lo que no entra, y dónde va.** Las casas, los muebles, el huerto y el buzón como reglas (`casas.py`, `huerto.py`, y en `economia.py` `comprar_casa`, `vender_casa`, `mudar_gachamon`, `comprar_mueble`, `colocar_mueble`, `retirar_mueble`, `plantar`, `regar`, `cosechar`, `cocinar`): plan 4, que los cambia por el departamento y entrega el buzón el día del cambio. El tope de 25 del plantel (`db.MAXIMO_PLANTEL`): plan 4, que lo cambia por las camas. El cliente web: no se toca en este plan.

## Global Constraints

- Nada se sube, se fusiona ni se despliega: todo queda en la rama local `rework/1-departamento`.
- Los módulos de juego no importan `discord`; `web/` no importa `discord` ni nada que lo importe; `db.py` no importa `economia.py`.
- Al terminar el plan, los únicos archivos de producción que importan `discord` son `bot.py`, `comun.py` y `cogs/mudanza.py`.
- Cada cambio de estado va en su transacción `BEGIN IMMEDIATE`, dentro de `db.py`, `economia.py` o `nacer.py`. **Ninguna regla del juego se ejecuta desde Discord**: el bot nuevo sólo escribe por `db.canjear_codigo_de_vinculo` y por las publicaciones del manual.
- Sin dependencias nuevas (`discord.py` se queda). Dominio determinista: el tiempo y el azar se inyectan en las pruebas.
- Nunca se abre `tamagotchi.db` ni `.env`; las pruebas usan bases temporales e ids sintéticos. El repo es público: sin IPs, ids de personas ni secretos.
- Antes de editar un símbolo, GitNexus `impact`; el índice se refresca sólo con `node .gitnexus/run.cjs analyze --index-only`.
- Cada commit: `./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "…"`, y termina con la línea de coautoría de la sesión que lo escribe.
- **No se pierde ningún dato**: no se borra ninguna tabla ni columna (`conversaciones`, `uso_ia`, `buzon`, `estilos_ficha`, `publicaciones`, `cooldowns_persona`, `pantalla_msg_id`, `canal_id` siguen en el esquema), y arrancar el bot nuevo sobre una base de hoy no cambia ninguna fila de juego.
- **Se quedan, con sus pruebas de dominio, las reglas que el proyecto 6 llevará a la página**: `aventura.py`, `competir.py`, `ia.py`, `personalidad.py`, `pantalla.py`, y en `economia.py` `ejecutar_viaje`, `otorgar_hallazgo`, `ejecutar_competencia`, `puede_aprender_hablando` y `aprender_hablando`, con lo de `db.py` que usan.
- A quien juega se le dice «monedas» y «gemas»; ningún mensaje del bot pasa de 2000 caracteres.
- **Regla de las pruebas de este plan.** Una prueba que ejercita un adaptador de Discord que se va (un comando, una ficha, un menú, un botón) se **borra** con él. Si además era la única que llegaba a una regla que se queda (por ejemplo, alcanzaba una función de `economia.py` sólo a través de un menú), se **reescribe** llamando a la regla directamente. Una prueba de una regla o de la web se conserva, quitándole lo que importara de Discord. Cada tarea dice en su informe, archivo por archivo, cuántas borró y cuántas reescribió, y qué regla quedó cubierta por dónde.
- **Frases nuevas** (se le enseñan a Felipe al confirmar el plan; van tal cual; `{URL}` es `config.URL_DE_LA_PAGINA`):
  - El aviso (botones y menús viejos, mencionar al bot, `/mascota`, `/huevo`): ``🏠 **Gachamon se mudó a la página.** Ahora se juega en {URL}. Tus gachamones, tus monedas y tus cosas te esperan ahí: entra, elige «Ya jugaba en Discord» y escribe aquí `/vincular` con el código que te dé.``
  - El aviso en un servidor que no es el de la página: `🏠 **Gachamon está en pausa en este servidor.** Tus gachamones y tus cosas siguen guardados.`
  - La descripción de `/mascota` y de `/huevo`: `Gachamon se mudó a la página`.
  - La página única del manual:

    ```
    ## 🏠 Gachamon se mudó a la página
    Desde ahora se juega en **{URL}**.

    **Cómo llevar tus gachamones**
    1. Entra a la página con tu cuenta de Rowino.
    2. Elige **«Ya jugaba en Discord»** y pide tu código.
    3. Escribe aquí `/vincular` y pega el código.

    -# Tus gachamones, monedas, gemas, objetos y medallas siguen guardados: los verás en la página en cuanto vincules.
    -# Competir, las aventuras, reclutar y conversar están en pausa. Volverán en la página.
    ```
  - Comando escrito fuera de su canal (antes «Los gachamones viven en {canales}. Escríbeme allí.»): `Escríbeme en {canales}.`
  - Web, Tienda, nota de lo que sirve para competir: `Sirve en las competencias, que todavía no están en la página.`
  - Web, Tienda, nota de la semilla: `Se siembra en el huerto, que todavía no está en la página.`
  - Web, aviso de un lugar que abre más adelante: `Esto se abre más adelante.` para todos (se va «Por ahora se juega en Discord.»).
  - Web, aviso de la intemperie con casa propia: `Se acabó tu estancia en el refugio y tu gachamon vive a la intemperie. Puedes comprar una casa más grande en la tienda.`
- **Lo que este plan decide en nombre de Felipe** (propuestas; se le enseñan con el plan):
  - El día del cambio el bot **borra sus otros siete mensajes del manual** y deja uno solo.
  - `/mascota` y `/huevo` se quedan como avisos; los otros quince comandos desaparecen de Discord.
  - «Entrenar juntos» y el jardín (`/jardin`) se van del código: en la página los reemplazan «entrenar con todos» y, más adelante, la plaza.
  - Lo que sólo servía en Discord (lo de competir, la semilla) deja de venderse en la página **a todos**, también a quien tiene Discord vinculado.

## Review Focus

1. **Un botón, un menú o un formulario de un mensaje viejo** (cualquier `custom_id`, también `tama:nombrar_recluta:<id>`): contesta el aviso en privado, sin «interacción fallida», sin error en el registro y sin cambiar nada en la base. → Task 1.
2. **`/vincular` después de mudarse de cog**: mismos mensajes, mismo límite de intentos, sólo en el servidor de la página y sólo en su canal. → Task 1.
3. **El manual, de ocho páginas a una**: no quedan mensajes huérfanos, un segundo arranque no toca el canal, y si alguien borró a mano una página vieja no revienta. → Task 1.
4. **La web sin el código de Discord**: `web.app` sigue sin cargar `discord`, ningún módulo de producción importa uno borrado, y la suite de la página (Python y JavaScript) pasa entera. → Task 2.
5. **Una regla que se queda y que sólo se probaba a través de Discord** (un viaje, una competencia, aprender hablando, comprar un cosmético): sigue cubierta por una prueba que la llama directamente. → Task 2.

**Sobre las pruebas de este plan.** Las ayudas (interacciones, canales y mensajes de mentira) son las de las pruebas vecinas (`tests/test_vincular.py`, `tests/test_manejo_de_errores.py`, y lo que haga falta copiar de `tests/test_carga.py` y `tests/test_manual.py` antes de que se vayan). Lo que manda son los nombres de las pruebas nuevas y sus aserciones.

---

### Task 1: El bot de la mudanza

**Files:**
- Create: `cogs/mudanza.py`, `tests/test_mudanza.py`
- Modify: `bot.py`, `config.py` (`URL_DE_LA_PAGINA`), `comun.py` (sólo la frase de `manejar_error`), `db.py` (nuevas `publicaciones_de`, `borrar_publicacion`), `tests/test_vincular.py`, `tests/test_manejo_de_errores.py`, y las pruebas de `tests/test_carga.py` que afirmaban el arranque viejo
- No se toca todavía: `cogs/social.py` y los demás cogs (siguen en el árbol, sin cargarse; se van en la Task 2)

**Interfaces:**
- Produces:
  - `config.URL_DE_LA_PAGINA: str`: la variable de entorno `URL_GACHAMON`, o `"https://rowino.online/gachamon"`.
  - En `cogs/mudanza.py`: las constantes `AVISO`, `AVISO_SIN_PAGINA` y `SERVIDOR_SIN_WEB` (ésta, la de hoy); `aviso_para(guild_id: int | None) -> str` (`AVISO` si es `config.GUILD_WEB`, si no `AVISO_SIN_PAGINA`); `pagina_del_manual() -> str`; `async publicar_la_pagina(canal, texto: str) -> None`; y el cog `Mudanza` con `async setup(bot)`.
  - `Mudanza` define **tres** comandos, los tres con `@comun.solo_en_el_canal()`: `/vincular` (el código de hoy, tal cual, con sus mismas descripciones), y `/mascota` y `/huevo`, que contestan `aviso_para(interaccion.guild_id)` en privado.
  - `Mudanza.on_interaction(interaccion)`: si la interacción es de un componente o de un formulario (`discord.InteractionType.component`, `modal_submit`) y nadie la ha contestado, contesta `aviso_para(...)` en privado. A los comandos de barra no los toca.
  - `Mudanza.on_message(mensaje)`: si mencionan al bot en uno de `config.CANALES` (y no es un bot ni un mensaje privado), contesta el aviso sin mencionar al autor. Nada más.
  - `Mudanza.on_ready()`: en cada canal de `config.CANALES_INFO`, una vez por arranque, `publicar_la_pagina(canal, pagina_del_manual())`, con el mismo trato de errores que hoy (`Forbidden`, `HTTPException`: aviso en el registro y el bot sigue).
  - `publicar_la_pagina`: la página 0 se publica si no está, se edita si su texto cambió y si no, no se toca; cada página de índice 1 en adelante que esté apuntada se **borra** del canal (si ya no existe, `discord.NotFound` se ignora) y su fila se quita.
  - `db.publicaciones_de(canal_id: str) -> dict[int, str]` (índice → id del mensaje) y `db.borrar_publicacion(canal_id: str, indice: int) -> None`.
  - `bot.EXTENSIONES == ("cogs.mudanza",)`. `setup_hook` conserva `economia.poner_al_dia(db.ahora_utc())`, `tree.on_error = comun.manejar_error` y la sincronización; **no registra ninguna vista ni elemento dinámico**. `bot.py` deja de importar `vistas`.

- [ ] **Step 1: Escribir las pruebas que fallan**, en `tests/test_mudanza.py`:

```python
def test_el_bot_solo_carga_la_mudanza():
    assert bot.EXTENSIONES == ("cogs.mudanza",)

def test_quedan_tres_comandos(cog):
    assert {c.name for c in cog.get_app_commands()} == {"vincular", "mascota", "huevo"}

def test_el_aviso_dice_donde_y_como():
    for texto in (mudanza.AVISO, mudanza.pagina_del_manual()):
        assert config.URL_DE_LA_PAGINA in texto and "`/vincular`" in texto
        assert "«Ya jugaba en Discord»" in texto and len(texto) < 2000
    assert config.URL_DE_LA_PAGINA not in mudanza.AVISO_SIN_PAGINA

@pytest.mark.parametrize("comando", ["mascota", "huevo"])
def test_los_comandos_de_memoria_avisan_y_no_tocan_nada(cog, comando):
    antes = volcado()
    interaccion = interaccion_falsa(guild_id=config.GUILD_WEB)
    asyncio.run(getattr(cog, comando).callback(cog, interaccion))
    interaccion.response.send_message.assert_awaited_once_with(mudanza.AVISO, ephemeral=True)
    assert volcado() == antes

@pytest.mark.parametrize("custom_id", [
    "tama:alimentar", "tama:plantel", "tama:nombrar", "tama:nombrar_recluta",
    "tama:nombrar_recluta:7", "tama:entrenar_juntos:reserva", "otra-cosa",
])
@pytest.mark.parametrize("tipo", [discord.InteractionType.component, discord.InteractionType.modal_submit])
def test_lo_viejo_contesta_el_aviso_y_no_toca_nada(cog, custom_id, tipo):
    antes = volcado()
    interaccion = interaccion_falsa(guild_id=config.GUILD_WEB, tipo=tipo, custom_id=custom_id)
    asyncio.run(cog.on_interaction(interaccion))
    interaccion.response.send_message.assert_awaited_once_with(mudanza.AVISO, ephemeral=True)
    assert volcado() == antes

def test_un_comando_de_barra_no_pasa_por_el_aviso(cog):
    interaccion = interaccion_falsa(tipo=discord.InteractionType.application_command)
    asyncio.run(cog.on_interaction(interaccion))
    interaccion.response.send_message.assert_not_awaited()

def test_lo_ya_contestado_no_se_contesta_otra_vez(cog):
    interaccion = interaccion_falsa(tipo=discord.InteractionType.component, contestada=True)
    asyncio.run(cog.on_interaction(interaccion))
    interaccion.response.send_message.assert_not_awaited()

def test_en_otro_servidor_el_aviso_no_promete_pagina(cog):
    interaccion = interaccion_falsa(guild_id=config.GUILD_WEB + 1, tipo=discord.InteractionType.component)
    asyncio.run(cog.on_interaction(interaccion))
    interaccion.response.send_message.assert_awaited_once_with(mudanza.AVISO_SIN_PAGINA, ephemeral=True)
```

Y, con canales y mensajes de mentira:

- `test_mencionar_al_bot_en_su_canal_contesta_el_aviso`: `mensaje.reply` se llama una vez con `mudanza.AVISO` y `mention_author=False`. `test_fuera_de_su_canal_o_sin_mencion_o_un_bot_no_contesta` (tres casos): `reply` no se llama.
- `test_el_manual_queda_en_una_sola_pagina`: un canal con ocho mensajes apuntados con `db.guardar_publicacion(canal, 0..7, …)`; tras `publicar_la_pagina(canal, pagina)`, el mensaje 0 se editó con `pagina`, los otros siete recibieron `delete()` una vez cada uno, y `db.publicaciones_de(canal) == {0: <su id>}`.
- `test_un_segundo_arranque_no_toca_el_canal`: tras la primera vez, una segunda llamada con el mismo texto no hace `send`, ni `edit`, ni `delete`.
- `test_una_pagina_vieja_borrada_a_mano_no_revienta`: `fetch_message` de la página 3 levanta `discord.NotFound`; no sale ninguna excepción, las otras seis se borran y la fila 3 se quita.
- `test_un_canal_sin_manual_publica_la_pagina`: sin filas, un solo `send` con la página y queda apuntada como 0.
- `test_el_arranque_no_registra_vistas_ni_botones_del_juego`: con el `setup_hook` de verdad sobre un bot de mentira (como lo hace hoy `tests/test_carga.py`): se llamó a `economia.poner_al_dia`, se cargó sólo `cogs.mudanza`, y `add_view` y `add_dynamic_items` no se llamaron.

En `tests/test_vincular.py`: las tres pruebas de hoy pasan a usar `cogs.mudanza.Mudanza`, con las mismas aserciones. En `tests/test_manejo_de_errores.py`: la del canal equivocado espera `Escríbeme en <#…>.`.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_mudanza.py tests/test_vincular.py tests/test_manejo_de_errores.py -q`
Expected: FAIL (no existe `cogs.mudanza`).

- [ ] **Step 3: Implementar.** El código de `/vincular`, `_mensaje_publicado` y el trato de errores de `on_ready` se **copian** de `cogs/social.py` (que se borra en la Task 2), sin cambiar su comportamiento. `Mudanza.on_interaction` es un `@commands.Cog.listener()`.

- [ ] **Step 4: Poner la suite en verde**

Run: `./venv/bin/python -m pytest -q`
Expected: fallan las pruebas de `tests/test_carga.py` (y las que haya en otros archivos) que afirmaban el arranque viejo: las extensiones, las vistas registradas, el botón dinámico, que cada comando tenga su canal. Bórralas o reescríbelas contra el bot nuevo según la regla de las pruebas; **el resto de esos archivos no se toca todavía**. Termina con la suite entera en verde.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "feat(bot): el bot de la mudanza: sólo /vincular, y a todo lo demás contesta que el juego está en la página"
```

---

### Task 2: Fuera el juego de Discord

**Files:**
- Delete: `vistas.py`, `tienda.py`, `equipo.py`, `jardin.py`, `cogs/mascota.py`, `cogs/competencias.py`, `cogs/aventura.py`, `cogs/social.py`, `cogs/charla.py`; `tests/test_vistas.py`, `tests/test_manual.py`, `tests/test_jardin.py`, y `tests/test_carga.py` salvo sus dos barridos genéricos de la fuente (los que no nombran ningún cog), que se mudan a `tests/test_textos.py`
- Modify: `comun.py` (queda en `CanalEquivocado`, `solo_en_el_canal` y `manejar_error`, con los `import` que eso pide), `db.py` (`vivas_del_servidor`, que sólo usaba el jardín), y las pruebas mezcladas: `tests/test_casas.py`, `tests/test_aventura.py`, `tests/test_aventura_rica.py`, `tests/test_economia_competencia.py`, `tests/test_taller.py`, `tests/test_tienda.py`, `tests/test_conversar.py`, `tests/test_objetos.py`, `tests/test_panel_logros.py`, `tests/test_textos.py`, `tests/test_estilo_ficha.py`, `tests/test_retrato.py`, `tests/test_economia_cuidado.py`, `tests/test_nombres.py`, `tests/test_nacer.py`, `tests/test_identidad.py`

**Interfaces:**
- Consumes: Task 1 (el bot ya no carga nada de esto; `/vincular` y el manual viven en `cogs/mudanza.py`).
- Produces: en el árbol no existe ninguno de los nueve archivos borrados ni nada que los importe. `comun.py` no importa `db`, `economia`, `objetos` ni `simulacion`. Ningún archivo de producción fuera de `bot.py`, `comun.py` y `cogs/mudanza.py` importa `discord`. Las reglas y la web no cambian de comportamiento.

- [ ] **Step 1: Escribir las pruebas que fallan**, en `tests/test_mudanza.py`:

```python
BORRADOS = ("vistas", "tienda", "equipo", "jardin", "cogs.mascota", "cogs.competencias",
            "cogs.aventura", "cogs.social", "cogs.charla")

@pytest.mark.parametrize("modulo", BORRADOS)
def test_el_juego_de_discord_ya_no_esta(modulo):
    assert importlib.util.find_spec(modulo) is None

def test_solo_el_bot_habla_con_discord():
    seguidos = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=RAIZ, capture_output=True, text=True, check=True
    ).stdout.split()
    con_discord = {
        ruta for ruta in seguidos
        if not ruta.startswith("tests/")
        and re.search(r"^\s*(import|from) discord\b", (RAIZ / ruta).read_text(), re.M)
    }
    assert con_discord == {"bot.py", "comun.py", "cogs/mudanza.py"}

def test_lo_comun_es_solo_el_canal_y_el_error():
    assert {n for n in vars(comun) if not n.startswith("_") and inspect.getmodule(getattr(comun, n)) is comun} \
        == {"CanalEquivocado", "solo_en_el_canal", "manejar_error"}
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_mudanza.py -q -k "ya_no_esta or solo_el_bot or lo_comun"`
Expected: FAIL (los módulos existen).

- [ ] **Step 3: Borrar y arreglar.** Antes de quitar cada prueba mezclada, mira qué regla tocaba: si la regla se queda y ninguna otra prueba la llama directamente (búscalo con `git grep -n "economia\.<función>\|db\.<función>" tests/`), reescríbela contra la regla. Atención especial a `economia.ejecutar_viaje`, `otorgar_hallazgo`, `ejecutar_competencia`, `aprender_hablando`, `comprar_cosmetico`, `equipar_cosmetico`, `quitar_cosmetico`, `comprar`, `usar_objeto`, `cocinar`, `cosechar`, `plantar`, `regar`, `mudar_gachamon`, `colocar_mueble` y `retirar_mueble`, y a los textos de `aventura.py`, `competir.py` y `pantalla.py`. `tests/test_nacer.py` tiene una prueba que lee la fuente de `cogs/mascota.py`: se va con él.

- [ ] **Step 4: Correr la suite**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS, sin avisos nuevos. Además:
- `./venv/bin/python -c "import bot, cogs.mudanza, web.app"` no falla.
- `git grep -n "import vistas\|import tienda\|import equipo\|import jardin\|from vistas\|from tienda\|cogs\.\(mascota\|competencias\|aventura\|social\|charla\)" -- '*.py'` sólo enseña la lista `BORRADOS` de la prueba.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "refactor(bot): fuera el juego de Discord: los comandos, las fichas, los menús y el jardín"
```

---

### Task 3: Lo que era sólo de Discord y no vuelve

**Files:**
- Modify: `economia.py` (`ejecutar_entrenamiento_conjunto`, `SeleccionEntrenamientoConjunto`, `ResultadoEntrenamientoConjunto`, `freno_de`, `FRENO_ACTIVIDAD`, `FRENO_BOTE`), `simulacion.py` (`aplicar_entrenamiento_conjunto`, `EFECTO_ENTRENAMIENTO_CONJUNTO`), `db.py` (`criatura_por_pantalla`, `guardar_pantalla`, `esperas_de_ficha`, `estilo_de_ficha`, `guardar_estilo_de_ficha`)
- Delete: `tests/test_economia_entrenamiento_conjunto.py`, y de `tests/test_estilo_ficha.py` lo que quede (el archivo entero si se queda vacío)
- Test: `tests/test_mudanza.py`, y las que nombren lo que se quita

**Interfaces:**
- Consumes: Task 2 (nadie en producción llama ya a nada de esto: compruébalo con `git grep` antes de borrar cada cosa).
- Produces: desaparecen esos símbolos. **Las tablas y columnas se quedan** (`estilos_ficha`, `criaturas.pantalla_msg_id`, `criaturas.canal_id`, y los campos `pantalla_msg_id` y `canal_id` de `sim.Criatura`). Se quedan también, aunque hoy nadie de producción las llame, las reglas que esperan su pantalla o su plan: las de la restricción global, y `db.ranking`, `db.cementerio`, el buzón (`db.mandar_regalo`, `buzon_de`, `recoger_del_buzon`), el huerto y las casas.

- [ ] **Step 1: Escribir la prueba que falla**, en `tests/test_mudanza.py`:

```python
@pytest.mark.parametrize("modulo, nombre", [
    (economia, "ejecutar_entrenamiento_conjunto"), (economia, "SeleccionEntrenamientoConjunto"),
    (economia, "ResultadoEntrenamientoConjunto"), (economia, "freno_de"),
    (sim, "aplicar_entrenamiento_conjunto"), (sim, "EFECTO_ENTRENAMIENTO_CONJUNTO"),
    (db, "criatura_por_pantalla"), (db, "guardar_pantalla"), (db, "esperas_de_ficha"),
    (db, "estilo_de_ficha"), (db, "guardar_estilo_de_ficha"), (db, "vivas_del_servidor"),
])
def test_lo_que_era_solo_de_discord_ya_no_esta(modulo, nombre):
    assert not hasattr(modulo, nombre)

@pytest.mark.parametrize("nombre", [
    "ejecutar_viaje", "otorgar_hallazgo", "ejecutar_competencia", "puede_aprender_hablando", "aprender_hablando",
])
def test_lo_que_vuelve_en_la_pagina_se_queda(nombre):
    assert callable(getattr(economia, nombre))

def test_no_se_fue_ninguna_tabla_ni_columna():
    with db.conectar() as con:
        tablas = {f[0] for f in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        columnas = {f["name"] for f in con.execute("PRAGMA table_info(criaturas)")}
    assert {"estilos_ficha", "conversaciones", "uso_ia", "buzon", "publicaciones", "cooldowns_persona"} <= tablas
    assert {"pantalla_msg_id", "canal_id"} <= columnas
```

- [ ] **Step 2: Correrla y ver que falla**

Run: `./venv/bin/python -m pytest tests/test_mudanza.py -q -k "solo_de_discord or se_queda or tabla"`
Expected: FAIL en la primera (los símbolos existen); las otras dos pasan ya y vigilan que no se borre de más.

- [ ] **Step 3: Implementar.** Quita también los `import` que queden sin uso y el comentario de `economia.py` que explicaba los dos frenos.

- [ ] **Step 4: Correr la suite**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "refactor(reglas): fuera «Entrenar juntos» y el seguimiento de los mensajes de Discord"
```

---

### Task 4: La web deja de mandar a Discord

**Files:**
- Modify: `web/tienda.py` (`se_le_vende`, `_nota`, las dos notas), `web/pueblo.py` (`aviso`), `web/estado.py` (quien llama a `pueblo.aviso`)
- Test: `tests/test_web_tienda.py`, `tests/test_pueblo.py`, `tests/test_web_lugar.py`, `tests/test_web_mochila.py`

**Interfaces:**
- Produces:
  - `web.tienda.se_le_vende(objeto, jugador) -> bool`: lo que todavía no se usa en la página (`donde_sirve` da `COMPETIR` o `HUERTO`) no se le vende **a nadie**, tenga o no Discord vinculado. Lo del refugio, como hoy.
  - `web.tienda._nota`: para `COMPETIR` y `HUERTO`, las dos notas nuevas, a todos. Desaparece `_NOTA_MAS_ADELANTE`.
  - `web.pueblo.aviso(clave: str, hogar: str, hogar_del_gachamon: str | None) -> str | None`: sin el parámetro `vinculada`. Un lugar que abre «después» avisa `Esto se abre más adelante.` a todos; la intemperie con casa propia, la frase nueva.
  - El cliente no se toca: la pantalla de vincular sigue diciendo que se escribe `/vincular` en Discord, que sigue siendo verdad.

- [ ] **Step 1: Escribir las pruebas que fallan**

- `tests/test_web_tienda.py`: `test_lo_que_no_se_usa_en_la_pagina_no_se_le_vende_ni_a_quien_tiene_discord` (cuenta vinculada: los artículos de competir y la semilla salen con `se_vende` falso y su nota nueva, y comprarlos por `POST` se rechaza sin cobrar, como hoy a quien no tiene Discord); `test_las_notas_ya_no_mandan_a_discord` (ninguna nota de ningún artículo contiene «Discord», con cuenta vinculada y sin ella).
- `tests/test_pueblo.py`: `test_un_lugar_que_abre_despues_avisa_lo_mismo_a_todos` (`pueblo.aviso("estadio", …) == "Esto se abre más adelante."`, con el lugar que hoy abra «después»); `test_el_aviso_de_la_intemperie_no_manda_a_discord` (la frase nueva, exacta).
- `tests/test_web_lugar.py`: el estado de una cuenta vinculada en un lugar que abre «después» trae ese mismo aviso.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_tienda.py tests/test_pueblo.py tests/test_web_lugar.py -q -k "discord or despues or intemperie or no_se_usa"`
Expected: FAIL.

- [ ] **Step 3: Implementar.** Reescribe o borra las pruebas vecinas que afirmaban lo de antes (que a quien tiene Discord se le vende todo, con las notas «por ahora… en Discord»).

- [ ] **Step 4: Correr la suite**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS. Además `git grep -n "Discord" -- 'web/*.py'` sólo enseña lo de vincular (`web/cuenta.py`, `web/app.py`) y comentarios que sigan siendo verdad.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "feat(web): la página deja de mandar a Discord: lo que todavía no se usa aquí no se vende"
```

---

### Task 5: Los documentos

**Files:**
- Modify: `AGENTS.md`, `README.md`, `.env.ejemplo` (sólo comentarios), `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`

- [ ] **Step 1: `AGENTS.md`**
  - «Propósito y alcance», las dos primeras líneas pasan a, tal cual: `Este repositorio contiene Gachamones, un tamagotchi que se juega en una página web.` y `Nació como bot de Discord; hoy su bot sólo sirve para vincular la cuenta de quien jugaba allí.` y `El producto combina cuidado, colección, competición y economía.`
  - «Para arrancar el bot…» se queda.
  - En «Invariantes del dominio», tal cual:
    - «El manual del juego lo publica el bot en su canal desde `paginas_de_ayuda()`, y no hay comando que lo enseñe.» pasa a ``- El bot publica en su canal una sola página, `cogs/mudanza.pagina_del_manual()`: el juego se mudó y cómo vincular.``
    - «El manual se edita en el sitio y nunca se republica: un arranque sin cambios no toca el canal.» pasa a `- Esa página se edita en el sitio y nunca se republica: un arranque sin cambios no toca el canal.`
    - Se añade después: ``- El juego de Discord está en pausa: el bot sólo atiende `/vincular` y contesta a todo lo demás que el juego se mudó a la página. Ninguna regla del juego se ejecuta desde Discord.``
    - Se quita la línea de `Entrenar juntos`.
    - «En la web se compra estando en la Tienda; lo que hoy sólo sirve en Discord se le vende sólo a quien tiene Discord vinculado.» pasa a `- En la web se compra estando en la Tienda; lo que todavía no se puede usar en la página no se le vende a nadie.`
    - «Usar un objeto que no haría nada … se rechaza sin gastarlo, en Discord y en la web.» pierde «, en Discord y en la web».
  - La sección «Arte ASCII» pasa a llamarse «Arte de texto» y dice sólo lo que siga siendo verdad: las fichas de texto eran de Discord y se fueron con su juego; lo que queda en `pantalla.py` es lo que usan `aventura.py` y `competir.py` (comprueba qué importan de él y dilo como es), a la espera de su pantalla en la página; no se amplía. Se va la línea de `/casa`.
  - En «Límites de arquitectura», las líneas de los cogs se quedan (valen para el cog que queda). «No respondas en Discord sobre una mutación hasta que la transacción confirme el commit.» se queda.
  - No toques el bloque final de GitNexus. Sin SHAs ni cantidades de pruebas.

- [ ] **Step 2: `README.md`**: léelo entero. Todo lo que cuente cómo se juega **en Discord** (los comandos, las fichas, competir, las aventuras, reclutar, conversar, la tienda y las casas por menús, el jardín) pasa a decir que el juego de Discord está en pausa y que se juega en la página; la tabla de comandos queda en `/vincular`, `/mascota` y `/huevo`. Las reglas que la página ya tiene se quedan contadas como reglas de la página. Las que esperan su pantalla (competir, las aventuras, reclutar, conversar) se cuentan en una sola sección corta, «En pausa». La puesta en marcha del bot (token, canal, servicio) se queda: sigue haciendo falta para vincular. No inventes reglas: si dudas, mira el código.

- [ ] **Step 3: `.env.ejemplo`**: los comentarios de las claves de IA y de `MODELO_IA` dicen que hoy no se usan (conversar está en pausa). No quites ninguna variable. Añade `URL_GACHAMON` comentada, con su valor por defecto.

- [ ] **Step 4: El documento de pendientes** gana, después de la sección del rework 2, **«Salió al ejecutar el rework 3 (el bot en pausa)»**, con la voz de las anteriores y sin SHAs ni números de tarea. El controlador le pasa a quien la escriba las notas de lo decidido y lo pendiente al terminar la Task 4; tiene que incluir la lista de reglas que se quedaron sin adaptador y a qué plan esperan, y lo que hay que saber el día de publicar (los comandos que desaparecen, los siete mensajes del manual que el bot borra, que la unidad `tamagotchi.service` sigue igual).

- [ ] **Step 5: Comprobar y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "docs: el bot en pausa, en la política, el README y los pendientes"
```

Después de la Task 5 el controlador lanza la revisión final de la rama (sólo los commits de este plan), arranca el bot nuevo contra una base temporal con un cliente de Discord de mentira si hace falta, recorre la página con el arnés (la Tienda con cuenta vinculada y sin ella, un lugar que abre «después») y le presenta el resultado a Felipe. No se fusiona, sube ni despliega: el plan 4 sigue en la misma rama.
