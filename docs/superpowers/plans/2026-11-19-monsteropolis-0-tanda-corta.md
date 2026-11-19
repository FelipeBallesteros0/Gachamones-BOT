# Monsteropolis 0 · La tanda corta — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dejar hechas las tres cosas chicas que el dueño pidió el 2026-11-19 antes de los proyectos grandes: el logro de la alfa a 5 gemas, la página a pantalla completa en un computador y la limpieza técnica anotada.

**Architecture:** Nada nuevo. Un número del catálogo de logros, la hoja de estilos del cliente (y, sólo si hace falta, cómo mide su escenario cada pantalla), y cuatro limpiezas que no ve quien juega.

**Tech Stack:** Python 3.12, FastAPI, SQLite; cliente en módulos de JavaScript sin frameworks ni compilación; pytest y `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-19-monsteropolis-hoja-de-ruta.md` (el proyecto 0).

## Global Constraints

- La página está **en producción, con jugadores reales**. Nada de esta rama se sube ni se despliega sin la palabra del dueño.
- Nadie gana ni pierde monedas ni gemas con este plan, salvo lo que dice la tarea 1.
- **Ninguna frase que lea quien juega cambia, se añade ni se quita.** Las tareas 2 a 5 no tocan textos.
- El bot de Discord no se toca (`bot.py`, `comun.py`, `cogs/`, `pantalla.py`).
- El cliente no usa frameworks ni compilación, no mete texto con `innerHTML` y no lleva claves ni precios del catálogo ni claves de lugar.
- Los colores, con las variables del tema de `estilo.css`. La página sólo tiene tema claro.
- **Por debajo de 900 px de ancho la página no cambia en nada**: el teléfono se ve exactamente como hoy.
- Accesibilidad como en el resto de la página: nada pierde el foco ni su nombre accesible, y con `prefers-reduced-motion` nada se mueve solo.
- El repo es público: ni direcciones, ni ids, ni rutas del dueño, ni SHAs, ni cantidades de pruebas en documentos ni comentarios.
- Las copias del repo para sondas se sacan sólo con `git archive`; nunca se abre `.env` ni `tamagotchi.db`.

## Review Focus

- **El teléfono, intacto**: a 390 × 664 y a 360 × 640 cada pantalla se ve igual que antes de la tarea 2, pixel por pixel salvo lo que el azar mueva.
- **Ventanas raras de computador**: 900 × 600 (el borde justo), 1366 × 768 (portátil bajo), 1920 × 1080 y 2560 × 1440; con la letra del navegador al 125 %; ninguna con barra de desplazamiento horizontal, ni con el panel de botones cortado o fuera de la vista.
- **El escenario que crece**: al agrandar y achicar la ventana con la pantalla abierta, la pieza, el mapa y la escena se recolocan sin deformarse, sin quedar borrosos donde hoy no lo están, y los toques siguen cayendo en la casilla que se ve.
- **Lo que se abre encima** (la carta, la ficha, la mochila, el aviso de lo que contesta el juego, el menú de la pieza, la bandeja de guardados): siguen legibles y dentro de la ventana en un computador.
- **La limpieza no cambia comportamiento**: lo que se mueve de archivo hace lo mismo, con sus mismas pruebas, y las guardas de toda la página (`tests/test_web_cliente.py`, `tests/test_web_minimos.py`, la de lecturas crudas de `tests/test_web_app.py`) siguen mordiendo.

---

### Task 1: El logro de la alfa paga 5 gemas

**Hecha por el controlador** (cambio de un número, con su prueba primero): `logros.py` paga 5 gemas por «De la alfa» en vez de 25; `tests/test_web_acciones.py` fija el 5. Lo ya pagado no se toca: un logro se paga una sola vez.

### Task 2: La página a pantalla completa en un computador

**Files:**
- Modify: `web/static/estilo.css`
- Modify, sólo si el escenario no puede crecer sin ello: el módulo de la pantalla que mida su escenario (`web/static/js/departamento.js`, `pueblo.js`, `lugar.js`, `aventura.js`, `ropero.js`) y su prueba en `tests/js/`
- Test: `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: las variables del tema de `estilo.css` (`--fondo`, `--fondo-fuera`, `--margen`…) y el atributo `data-pantalla` de `#juego`.
- Produces: nada que otra tarea use.

**Lo que pidió el dueño, textual:** «aprovechar toda la pantalla en pc, que no queden líneas blancas en los laterales».

**Cómo está hoy** (medido a 1920 × 1080): `#juego` es una columna centrada de 480 px (la carta) o de 1120 px (el departamento, un lugar, el pueblo, la aventura, el ropero), y a cada lado queda una franja de 400 px del color `--fondo-fuera`.

**Cómo tiene que quedar, desde 900 px de ancho:**

1. `#juego` ocupa **todo el ancho y todo el alto de la ventana**: ningún `max-width` suyo, ninguna franja de otro color a los lados, y la barra de arriba de lado a lado. El fondo de la página es el del juego.
2. **Las pantallas con escenario** (el departamento, un lugar, el pueblo, la aventura y el ropero): el escenario —la pieza, la escena, el mapa— se queda con todo el ancho que sobra y con el alto de la ventana, y lo que dibuja crece hasta donde quepa sin deformarse; el panel de botones conserva un ancho cómodo y fijo a su lado. En una ventana baja (1366 × 768) lo principal de la pantalla —el escenario y los botones de cuidar— se ve sin desplazar la página.
3. **Las pantallas de listas** (la tienda, la mochila, lo que el ropero lista): la lista usa el ancho en más columnas, en vez de una columna angosta en el centro.
4. **Las pantallas de leer** (la carta, la bienvenida, el avatar, poner nombre, la ficha): el texto conserva un ancho de lectura cómodo y va centrado, pero sobre el mismo fondo continuo y bajo la barra de lado a lado: no vuelve a verse una columna recortada con franjas.
5. Sin barra de desplazamiento horizontal en ningún ancho.
6. **Por debajo de 900 px no cambia nada.**

- [ ] **Step 1: Las capturas de antes.** Con el arnés (ver las reglas del implementador), cada pantalla a 390 × 664, 360 × 640, 900 × 600, 1366 × 768, 1920 × 1080 y 2560 × 1440, guardadas en tu carpeta: son la referencia del «teléfono intacto» y del «antes».

- [ ] **Step 2: La prueba que falla.** En `tests/test_web_cliente.py`, una prueba `test_en_un_computador_el_juego_ocupa_toda_la_ventana` que lee `estilo.css` y comprueba: que dentro de los bloques `@media (min-width: 900px)` ningún selector `#juego…` lleva un `max-width` distinto de `none`; que existe en uno de esos bloques una regla `#juego { … max-width: none … }`; y que `--fondo-fuera` ya no se usa en ninguna regla que valga desde 900 px. Y un guion de medida tuyo, fuera del repo, que para cada pantalla y cada tamaño de computador compruebe en el navegador que el ancho de `#juego` es el de la ventana y que `document.documentElement.scrollWidth` no pasa del ancho de la ventana.

Run: `./venv/bin/python -m pytest tests/test_web_cliente.py -q -k computador`
Expected: FAIL (hoy hay cinco `max-width: 1120px`).

- [ ] **Step 3: La hoja de estilos**, hasta cumplir los seis puntos de arriba. Si el escenario de una pantalla no crece sólo con la hoja porque su tamaño se calcula en JavaScript, se toca ese cálculo y nada más de ese módulo, con su prueba en `tests/js/` primero.

- [ ] **Step 4: Medir y mirar.** El guion de medida en verde en los cuatro tamaños de computador y en todas las pantallas; las capturas de después junto a las de antes; y las del teléfono comparadas con las de antes (las mismas, salvo lo que mueva el azar: se dice cuál y por qué).

Run: `./venv/bin/python -m pytest tests/test_web_cliente.py -q -k computador`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "feat: en un computador la página ocupa toda la ventana"
```

### Task 3: Tres limpiezas de un renglón

**Files:**
- Delete: todo lo que `git ls-files .claude/skills/generated` lista
- Modify: `web/estado.py`, `web/departamento.py`, `web/ficha.py`
- Modify: `tests/test_web_nacer.py` (un comentario)

**Interfaces:**
- Produces: `web.estado.NO_ESTA`, la misma excepción que hoy es `web.departamento.NO_ESTA`.

- [ ] **Step 1:** Borrar del repo los documentos generados de `.claude/skills/generated/` (nombran funciones que ya no existen; nada del repo los cita: comprobarlo con `git grep -n "skills/generated"` antes de borrar, y si algo los cita, parar y decirlo). `.claude/skills/gitnexus/` no se toca.
- [ ] **Step 2:** `NO_ESTA` pasa a definirse en `web/estado.py`; `web/departamento.py` y `web/ficha.py` la importan de ahí, y ningún router importa de otro router. Primero una prueba en `tests/test_web_cliente.py` o donde vivan las guardas de imports de `web/`, que falle mientras `web/ficha.py` importe de `web/departamento.py`.
- [ ] **Step 3:** El comentario de `tests/test_web_nacer.py` que dice «su casa» dice «su departamento».
- [ ] **Step 4: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "refactor: fuera los documentos generados viejos y un router que importaba de otro"
```

### Task 4: El transporte sale de la pantalla del departamento

**Files:**
- Create: `web/static/js/transporte.js`
- Modify: `web/static/js/departamento.js`
- Test: `tests/js/transporte.test.mjs`, `tests/js/departamento.test.mjs`, y las listas de archivos vigilados de `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: lo que hoy hacen dentro de `departamento.js` `mandar`, `enviar`, `releer` y sus reintentos (`conReintentos`), tal como los describe el renglón «Sacar el transporte de `departamento.js`» de la sección del rework 7 en `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`.
- Produces: un módulo `transporte.js` sin estado de pantalla, que recibe lo que necesita (la función de pedir, la señal de la pantalla, cómo avisar) y devuelve esas mismas operaciones; `departamento.js` las usa y no cambia nada de lo que hace.

- [ ] **Step 1:** Leer en `departamento.js` y en sus pruebas qué hace hoy cada una de esas funciones, y escribir en `tests/js/transporte.test.mjs` las pruebas del módulo nuevo que fijan ese comportamiento (reintentos, lo que se hace al salir de la pantalla, lo que se relee tras un rechazo). Tienen que fallar porque el módulo no existe.
- [ ] **Step 2:** Mover el código al módulo, sin cambiar comportamiento; `departamento.js` lo importa. Ninguna prueba existente de `tests/js/departamento.test.mjs` se cambia salvo donde importaba algo que se mudó.
- [ ] **Step 3:** `node --test tests/js/*.test.mjs` y la suite entera en verde; mirar el departamento con el arnés (poner, mover, guardar, ampliar, salir a media petición) y dejar las capturas.
- [ ] **Step 4: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "refactor: el transporte del departamento, a su módulo"
```

### Task 5: La herramienta para levantar una página de prueba

**Files:**
- Create: `herramientas/pagina_de_prueba.py`
- Test: `tests/test_pagina_de_prueba.py`
- Modify: `README.md` (cómo se usa, en la sección de desarrollo)

**Interfaces:**
- Produces: `python -m herramientas.pagina_de_prueba --carpeta <carpeta nueva> [--puerto N] [--cuentas N]`, que deja corriendo en `127.0.0.1` la web de **una copia del repo sacada con `git archive HEAD`** sobre una base nueva y una base de Rowino de mentira, y un intermediario local que le pone a cada puerto la cookie firmada de una cuenta de mentira; imprime las direcciones y cómo apagarla.

Reglas de la herramienta, que sus pruebas fijan:

- Nunca corre sobre el directorio de trabajo ni lee `.env`: la web arranca desde la copia de `git archive`, con `RUTA_BD`, `RUTA_ROWINO_BD`, `ROWINO_SECRET_KEY` y `GUILD_WEB` puestos por ella.
- La clave de sesión la inventa en cada arranque (`secrets.token_urlsafe`); nunca acepta una por parámetro ni por el entorno.
- La carpeta tiene que no existir o estar vacía, y no puede estar dentro del repo; la base que crea vive ahí. Se niega si `RUTA_BD` o `RUTA_ROWINO_BD` ya vienen puestas en el entorno.
- Sólo escucha en `127.0.0.1`.
- Las cuentas de mentira son ids chicos y sintéticos.

- [ ] **Step 1:** Las pruebas de esas cinco reglas sobre las funciones puras de la herramienta (armar el entorno, validar la carpeta, crear la base de Rowino de mentira, firmar la cookie), sin levantar ningún servidor. Tienen que fallar porque el módulo no existe.
- [ ] **Step 2:** La herramienta, tomando como molde el arnés del scratchpad que se ha usado en cada plan (ver las reglas del implementador).
- [ ] **Step 3:** Levantarla de verdad en una carpeta del scratchpad, entrar con dos cuentas, y apagarla; la salida, al informe.
- [ ] **Step 4: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "feat: una herramienta para levantar una página de prueba con bases de mentira"
```
