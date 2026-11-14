# Gachamon web · Plan 5 — La ficha, el ropero, la incubadora y el refugio

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que quien juega en `rowino.online/gachamon` vea la ficha entera de su gachamon (estadísticas, experiencia, carácter, efectos y medallas), le ponga y le quite el sombrero y el título, entre a la Incubadora a ver su plantel, cambiar de activo y ponerle nombre a quien no lo tiene, y que el Refugio diga quién vive ahí y cuánto le queda — con las mismas reglas que Discord.

**Architecture:** Dos reglas que hoy viven pegadas a los menús de Discord pasan a ser del juego: **cambiar de activo** (`economia.cambiar_de_activo`) y **ponerle nombre a un gachamon concreto** (`nacer.bautizar_a`); Discord las usa también. Poner y quitar cosméticos ganan un **motivo** en cada rechazo y el id del gachamon que enseña la pantalla, como la mochila. La web gana tres routers finos (`web/ficha.py`, `web/ropero.py`, `web/incubadora.py`), el estado dice quién vive en el Refugio, y el cliente gana tres pantallas (`ficha.js`, `ropero.js`, `incubadora.js`). La Incubadora abre: su lugar ofrece «incubadora», como la Tienda ofrece «tienda».

**Tech Stack:** Lo de los planes 2 a 4, sin dependencias nuevas: Python 3.12 y 3.14, FastAPI 0.162.5, SQLite síncrono, pytest 9.1.1; JavaScript del navegador en módulos, probado con `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-12-gachamon-web-parte-a-design.md` — secciones 5.3 (la ficha se abre para ver el resto), 5.5 (Refugio, Incubadora y Ropero) y 5.9 (el arte de los efectos). Lo que el reconocimiento encontró en el código está en `.superpowers/sdd/2026-11-13-gachamon-web-4-reconocimiento/` (no versionado); son afirmaciones de exploradores, y cada tarea comprueba contra el código las que usa. Los pendientes que este plan recoge están en `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`, sección «Para el plan 5».

## Lo que decidió Felipe y sigue valiendo

- **El reloj del refugio no arranca para quien juega sólo en la web** (`identidad.sin_plazo_de_refugio`): su estancia no vence. El Refugio se lo dice en vez de enseñarle una cuenta atrás.
- **Usar algo que no haría nada se rechaza sin gastarlo** (plan 4): no cambia aquí.

## Lo que este plan decide y Felipe tiene que mirar

Son propuestas mías donde el diseño deja la decisión a quien construye. Si alguna no te gusta, se cambia antes de ejecutar.

- **La ficha completa se abre con un botón «Ver ficha»** en la ficha del lugar, y el **ropero desde la ficha completa** (el diseño lo proponía así). Enseña: las cuatro estadísticas con el efecto que tengan encima («+3 · 4 min»), la experiencia («40 de 100 para el nivel 3»), el género, el carácter, el sombrero, el título y las medallas (las de tu gachamon y las tuyas, con su progreso, como `/logros`).
- **Mirar la ficha no paga medallas.** En Discord, `/logros` paga las que dependen del tiempo («Veterano») al abrirse. En la web, una lectura no escribe: esas medallas se pagan en el siguiente cuidado (que ya paga las medallas nuevas), y mientras tanto la ficha enseña su progreso lleno («30/30»).
- **El ropero viste al gachamon que enseña la pantalla.** Si entretanto cambió (otra pestaña, Discord), no se viste a otro: la pantalla vuelve a mirar. Poner y quitar **no se confirman** (no cuestan nada y se deshacen con otro toque). Una pieza que lleva otro de tus gachamones sale con «Lo lleva Nube.» y sin botón.
- **«Sacar» de la incubadora sólo estando en la Incubadora** (como comprar en la Tienda), sin confirmar: no cuesta nada y se deshace sacando al otro. **Ponerle nombre** a un recluta, en cambio, se puede donde la pantalla lo ofrezca: en la Incubadora, y en la pantalla del bautizo cuando tu único gachamon vivo es un recluta sin nombre (hoy la web se queda atascada en el huevo con «Ponle nombre en Discord y vuelve.»).
- **El Refugio enseña «Viven aquí»** (retrato pequeño y nombre de cada uno de los tuyos que vive en él) y una línea sobre tu estancia. Quien juega sólo en la web lee que su estancia no tiene plazo.
- **Los efectos del contrato de arte se usan por fin:** los corazones de la caricia son `efectos/corazon.png` (hoy son un carácter de texto) y la estrella `efectos/estrella.png` marca las medallas conseguidas y el aviso de medalla nueva.
- **Los estáticos versionados se guardan en el navegador** (`Cache-Control: public, max-age=31536000, immutable`): la dirección cambia con cada despliegue, así que nunca se sirve uno viejo, y el mapa deja de repetir sus peticiones en cada visita.
- **En Discord cambian tres cosas, y son arreglos:**
  1. **Cambiar de activo pone al día a la que sale** antes de dormirla. Hoy se salta el decaimiento desde su último guardado: cambiar de activo servía para que no bajara la comida. Si la que sale ya debería estar muerta, se registra su muerte (y el bot la anuncia) y el cambio se hace igual.
  2. **Elegir en el menú al que ya es el activo no le borra el decaimiento** (lo impedía el menú; ahora lo impide la regla).
  3. **Bautizar a un recluta** rechaza el nombre de su especie (como el bautizo del huevo), no nombra a uno muerto ni ajeno y sólo escribe el nombre (hoy guarda la fila entera y podía pisar lo que el bot acababa de guardar). Frase nueva en Discord: «Ese gachamon ya tiene nombre.» si se envía dos veces. Las demás frases de Discord no cambian.
- **Las frases nuevas** (las escribí yo; cámbialas si no suenan a tu juego):
  - **Ficha:** «Ver ficha» · «Estadísticas» · «Experiencia: 40 de 100 para el nivel 3» · «+3 · 4 min» · «Lleva Corona» · «Medallas de Pelusa» · «Tuyas» · «Las de Pelusa se van con él si se muere; las tuyas se quedan.» (con ella / él según el género).
  - **Ropero:** «Ropero» · «Sombreros» · «Títulos» · «Poner» · «Quitar» · «Lo lleva Pelusa.» · «Lo lleva Nube.» · «Tu ropero está vacío. Los sombreros y los títulos se compran en la tienda, con gemas.» · Al poner: «Pelusa ya lleva Corona.» / «Ahora es Pelusa la Invicta.», y si llevaba otro, «… Chistera vuelve a tu ropero.» · Al quitar: «Pelusa ya no lleva Corona. Está en tu ropero.» · «Pelusa no lleva ningún sombrero.» / «… ningún título.» · «Corona: lo lleva Nube. Quítaselo primero.» · «Ya no tienes Corona.»
  - **Incubadora:** el botón del lugar, «Tu plantel» · «Activo» · «Sacar» · «Sin nombre» · «Ponerle nombre» · «Nube sale de la incubadora.» · «Pelusa ya es tu gachamon activo.» · «Antes de sacarlo, ponle nombre.» · «Ese gachamon ya no está.» · «Aquí esperan los gachamones que no son el activo. Ahora sólo tienes a Pelusa.» · «Caben 25 gachamones.» · «Para eso tienes que estar en la incubadora.» · En el huevo, si hay un recluta: «Antes, ponle nombre al gachamon que espera en la incubadora.»; en el bautizo de un recluta: «Este Purreon espera en la incubadora y todavía no tiene nombre.»
  - **En la Incubadora el gachamon deja de decir** «Todo está quietito, como si durmiera.» y dice «Se oye un zumbido tibio, muy bajito.»
  - **Refugio:** «Viven aquí» · «Ninguno de tus gachamones vive aquí.» · «Tu estancia aquí no tiene plazo.» · «Tu estancia en el refugio dura 6 días más.» (1 día) · «Tu estancia en el refugio se acaba en 5 horas.» (1 hora; «en menos de una hora») · Para quien **tiene casa** y su gachamon se quedó a la intemperie: «Se acabó tu estancia en el refugio y tu gachamon vive a la intemperie. Puedes mudarlo a tu casa, por ahora desde Discord, o comprar una más grande en la tienda.»

## Global Constraints

- Todo lo de `AGENTS.md` y las restricciones globales de los planes 2 a 4 siguen mandando. Las que más pesan aquí:
  - `web/` no importa `discord`, ni directa ni indirectamente (`tienda.py`, `vistas.py`, `equipo.py`, `comun.py` y `cogs/` lo importan).
  - El servicio no guarda estado del juego en memoria.
  - Quién eres sale sólo de la cookie de Rowino; ninguna ruta acepta un id de persona. Un `gachamon_id` en el cuerpo es el gachamon que enseña la pantalla, nunca una identidad, y se comprueba que sea tuyo.
  - Toda ruta que cambia algo es `POST` o `PUT` y exige `X-Gachamon: 1`. Las rutas se declaran con `def`.
  - Un error se contesta siempre como `{"detail": {"clave": "<clave>", "mensaje": "<frase>"}}`. El cuerpo se revisa a mano (`Body(default=None)`), como en las rutas de la tienda y la mochila; un número que no es entero (`type(x) is int`) es 422 `peticion`.
  - Toda mutación va bajo `BEGIN IMMEDIATE` y dentro de `db.py`, `economia.py` o `nacer.py` (que llama a `db`). `db.py` no importa `economia.py` ni nada de `web/`.
  - El reloj es `db.ahora_utc()`; en las pruebas, el tiempo y el azar se inyectan y la base es temporal.
- **Un «no» del juego no es un error HTTP.** Como en la mochila: si la regla dice que no, la respuesta es 200 con `ok: false`, la `clave` del motivo y una frase. Los 4xx son para peticiones que la pantalla nunca hace (cuerpo mal hecho, no estás en la incubadora, el gachamon de la pantalla ya no es el activo).
- **Lo que ya está como se pidió es un sí.** Poner lo que ya lleva, quitar lo que no lleva o sacar al que ya es el activo contestan `ok: true` con la frase de cómo está; así un toque doble no enseña un error.
- **Las frases de la web las escribe la web**, en texto llano: sin `**`, sin `-#`, sin nombrar comandos ni botones de Discord. Las de `economia` (`problema`) son de Discord y no se enseñan en la web.
- **Lo que Discord hace hoy no cambia** salvo los tres arreglos de arriba: los parámetros nuevos son opcionales y, sin ellos, cada función se comporta como antes; las frases de Discord siguen letra por letra salvo «Ese gachamon ya tiene nombre.».
- **Mirar no escribe.** Las lecturas usan `db.hogar_leido` y no pagan medallas; lo único que escribe una lectura es la muerte que descubre `db.activa_al_dia`.
- **El cliente no usa frameworks ni compilación, nunca mete texto con `innerHTML`, y no contiene `http://` ni `https://`.** Los módulos se importan con rutas relativas terminadas en `.js`. Ninguna dependencia nueva.
- **Las reglas son del servidor**: quién se puede sacar, qué se puede poner y qué dice la ficha lo decide el servidor; el cliente pinta lo que le dicen.
- **El pueblo vive en datos.** El código sólo nombra un lugar por su clave donde le da un significado, y una prueba vigila que esas claves existan en `pueblo.json`.
- **Arte:** cada dibujo es un archivo bajo `web/static/arte/` descrito en `web/arte.py`. Si un archivo falta, se ve el recuadro de esa pieza y nunca el dibujo de otra.
- El análisis de impacto de GitNexus lo corre el controlador antes de cada tarea que toque un símbolo existente; el índice se refresca sólo con `node .gitnexus/run.cjs analyze --index-only`.
- Antes de cada commit: `./venv/bin/python -m pre_commit run --all-files && git diff --check`, encadenados con `&&` al commit y **sin tuberías**.
- **Nada de push, merge ni despliegue sin autorización explícita de Felipe.**
- Rama de trabajo: `web/5-ficha-ropero-incubadora-refugio`, desde `main`. Un commit por tarea.

## Review Focus

1. **La pantalla enseña un gachamon que ya no es el activo** (otra pestaña lo cambió, Discord, una muerte) y se pone o se quita un cosmético: no se le aplica a otro; 409 `sin_gachamon` y la pantalla vuelve a decidir. → Tareas 1 y 4.
2. **Sacar a otro cuando el activo ya debería estar muerto o lleva horas sin guardarse**: la muerte se registra y se cuenta primero, y el decaimiento de la que sale no se pierde. → Tareas 2 y 5.
3. **Una petición hecha a mano**: sacar o bautizar a un gachamon ajeno, muerto o que no existe, o con un id que no es un entero. Nada cambia y nada contesta 500. → Tareas 2, 4 y 5.
4. **El único vivo es un recluta sin nombre**: se le pone nombre en la web y el juego sigue (sale de la incubadora solo). → Tareas 5 y 8.
5. **Quien juega sólo en la web, con un solo gachamon y sin casa**, en la Incubadora y en el Refugio: frases ciertas («Ahora sólo tienes a Pelusa.», «Tu estancia aquí no tiene plazo.») y nada roto. → Tareas 5, 6 y 8.

**Sobre las pruebas de este plan.** Los nombres de ayuda que aparecen en ellas (`base`, `U`, `G`, `YO`, `T0`, `nace`, `dar_gemas`, `con_gachamon`, `con_vinculo`, `poner_reloj`, `ESCRIBIR`…) son los de las pruebas vecinas o ayudas pequeñas que cada archivo escribe al principio. Lo que manda son los nombres de las pruebas y sus aserciones, con sus valores.

---

### Task 1: Poner y quitar cosméticos dicen por qué no, y a quién

**Files:**
- Modify: `economia.py` (`ResultadoCosmetico`, `equipar_cosmetico`, `quitar_cosmetico`), `db.py` (nueva lectura)
- Test: `tests/test_ropero.py` (nuevo)

**Interfaces:**
- Produces:
  - `ResultadoCosmetico` gana `lo_lleva: str | None = None`: en el rechazo `lo_lleva_otro`, el `sim.nombre_visible` de quien la lleva.
  - `economia.equipar_cosmetico(usuario_id: str, guild_id: str, cosmetico: cos.Cosmetico, criatura_id: int | None = None) -> ResultadoCosmetico` y `economia.quitar_cosmetico(usuario_id: str, guild_id: str, tipo: str, criatura_id: int | None = None) -> ResultadoCosmetico`. Motivos de rechazo: `sin_gachamon` (no hay activo, o `criatura_id` no es el activo), `ya_lo_lleva`, `lo_lleva_otro`, `no_lo_tienes` (poner) y `no_lleva_nada` (quitar). `problema` sigue siendo la frase de Discord de hoy, letra por letra; con un `criatura_id` que no es el activo, `problema` es «No tienes ningún gachamon activo.».
  - `db.quien_lleva_cada(usuario_id: str, guild_id: str) -> dict[str, str]`: clave de cada pieza puesta en un gachamon **vivo** de esa persona → su `sim.nombre_visible`.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_ropero.py`, sobre la base temporal, con dos gachamones de la misma persona (Pelusa activa, Nube en la incubadora) y piezas dadas en el ropero:

- `test_cada_rechazo_de_poner_dice_su_motivo`: poner a Pelusa lo que ya lleva → `motivo == "ya_lo_lleva"`; lo que lleva Nube → `motivo == "lo_lleva_otro"` y `lo_lleva == "Nube"`; lo que no está en el ropero → `"no_lo_tienes"`; sin activa → `"sin_gachamon"`. En ningún caso cambia lo que llevan.
- `test_quitar_sin_nada_puesto_dice_no_lleva_nada`.
- `test_con_otro_criatura_id_no_se_viste_ni_se_desviste`: `equipar_cosmetico(…, criatura_id=nube.id)` y `quitar_cosmetico(…, criatura_id=nube.id)` con Pelusa activa → `motivo == "sin_gachamon"`, y Pelusa y Nube llevan lo mismo que antes.
- `test_con_el_criatura_id_del_activo_se_viste_como_siempre`.
- `test_las_frases_de_discord_no_cambian`: el `problema` de cada rechazo es el de hoy, escrito literal en la prueba («Pelusa ya lo lleva puesto.», «**Corona** lo lleva **Nube**. Quítaselo primero.», «No tienes **Corona** en tu ropero.», «No tienes ningún gachamon activo.», «Pelusa no lleva nada de eso.»).
- `test_quien_lleva_cada`: con Pelusa con una corona y Nube con un título → `{"corona": "Pelusa", <título>: "Nube"}`; si Nube muere, su título ya no sale.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_ropero.py -q`
Expected: FAIL (`motivo` es `None`, `quien_lleva_cada` no existe).

- [ ] **Step 3: Implementar**

El `criatura_id` se mira justo después de leer la activa, dentro de la transacción. `quien_lleva_cada` es una consulta sobre `criaturas` (vivas, de esa persona y servidor, con `sombrero` o `titulo`).

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_ropero.py tests/test_cosmeticos.py tests/test_tienda.py tests/test_motivos.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(economia): poner y quitar cosméticos dicen por qué no, y a qué gachamon se aplican"
```

---

### Task 2: Cambiar de activo y bautizar a uno concreto son reglas del juego

**Files:**
- Modify: `economia.py`, `db.py`, `nacer.py`, `equipo.py` (sólo `MenuPlantel.callback`), `vistas.py` (sólo `NombreModal.on_submit`, el camino con `criatura_id`)
- Test: `tests/test_cambiar_de_activo.py` (nuevo), `tests/test_bautizar_a.py` (nuevo), y las de Discord que ya cubren el menú y el modal (`tests/test_vistas.py`, `tests/test_taller.py`, `tests/test_nombres.py`)

**Interfaces:**
- Produces:
  - `economia.ResultadoCambio` (dataclass congelada): `ok: bool = False`, `motivo: str | None = None`, `criatura: sim.Criatura | None = None` (la activa después), `saliente: sim.Criatura | None = None` (la que estaba, ya al día).
  - `economia.cambiar_de_activo(usuario_id: str, guild_id: str, criatura_id: int, ahora: datetime) -> ResultadoCambio`. Motivos: `ya_es_el_activo` (no escribe nada), `no_esta` (no es tuyo, está muerto o no existe), `sin_nombre` (`sim.esta_sin_nombrar`). Empieza llamando a `db.activa_al_dia` (como `nacer.bautizar`), y después, en **una** transacción `BEGIN IMMEDIATE`: relee la elegida y la activa; pone al día a la activa con `db._avanzar_en` y la guarda; si al ponerla al día sale muerta, la guarda muerta y la apunta con `db._apuntar_muerte`, y el cambio sigue; activa a la elegida con `actualizada_en = ahora` y sus relojes recalculados.
  - `db._activar_en(con: sqlite3.Connection, criatura_id: int, ahora: datetime) -> sim.Criatura`: las dos `UPDATE` de hoy y el guardado de la que despierta, dentro de la transacción que le pasan. `db.activar` conserva su firma y su comportamiento, ahora a través de `_activar_en`.
  - `nacer.NO_ESTA = "no_esta"` y `nacer.bautizar_a(usuario_id: str, guild_id: str, criatura_id: int, nombre: str, ahora: datetime) -> sim.Criatura`. Lanza `NombreNoVale` (nombre que no pasa `sim.normalizar_nombre`, o el de su especie: «Ese es el nombre de su especie. Ponle uno propio.»), `NoSePuedeBautizar(NO_ESTA, "Ese gachamon ya no está.")` (ajeno, muerto o inexistente) y `NoSePuedeBautizar(YA_BAUTIZADO, "Ese gachamon ya tiene nombre.")` (si no `espera_nombre`). No pone al día a nadie.
  - `db.poner_nombre_a(usuario_id: str, guild_id: str, criatura_id: int, nombre: str, puede: Callable[[sim.Criatura], bool]) -> tuple[str, sim.Criatura | None]`: como `poner_nombre_a_la_activa`, pero de esa criatura viva y tuya; devuelve `("no_esta", None)`, `("no_puede", criatura)` o `("hecho", criatura_con_su_nombre)`; sólo escribe la columna `nombre`.
  - Discord: `MenuPlantel.callback` usa `economia.cambiar_de_activo` en lugar de `db.activar` (frases: `ya_es_el_activo` → la de hoy «**{nombre}** ya era el activo.»; `no_esta` → «Ese gachamon no es tuyo o ya no está.»; `sin_nombre`, si llega, → «Ese gachamon no sale de la incubadora hasta que le pongas nombre.»). `NombreModal.on_submit` con `criatura_id` usa `nacer.bautizar_a` (`NombreNoVale` → «Nombre no válido. {error}» como hoy; `NO_ESTA` → «Ya no tienes ningún gachamon vivo.» como hoy; `YA_BAUTIZADO` → «Ese gachamon ya tiene nombre.», nueva). Sin `criatura_id`, el modal no cambia.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_cambiar_de_activo.py` (identidad de Discord sintética, reloj inyectado):

- `test_cambiar_pone_al_dia_a_la_que_sale`: A activa con la comida a 100 en `T0`, B en la incubadora; `cambiar_de_activo(…, b.id, T0 + 5h)` → `ok`, B es la activa, y A guardada tiene `actualizada_en == T0 + 5h` y la comida que da `sim.avanzar` hasta `T0 + 5h` (menor que 100).
- `test_la_que_entra_sale_con_su_reloj_al_dia`: B queda con `actualizada_en == ahora` y `muere_en` calculado (no `None`).
- `test_cambiar_al_que_ya_es_el_activo_no_toca_nada`: `motivo == "ya_es_el_activo"`, `ok is False`, y su `actualizada_en` y su comida guardadas no cambian.
- `test_no_se_saca_a_un_recluta_sin_nombre`: `motivo == "sin_nombre"`; la activa sigue siendo la misma.
- `test_no_se_saca_a_uno_ajeno_muerto_ni_inexistente`: los tres → `motivo == "no_esta"`, nada cambia.
- `test_si_la_que_sale_ya_estaba_muerta_se_registra_y_se_cambia_igual`: A activa con `muere_en` en el pasado, y B y C en la incubadora (B es el relevo que `db.activa_al_dia` saca primero); `cambiar_de_activo(…, c.id, …)` → A queda muerta (`muerta_en` puesto) y apuntada en `muertes_por_anunciar`, y C es la activa.
- `test_si_la_elegida_es_el_relevo_que_acaba_de_salir_ya_es_el_activo`: lo mismo, eligiendo a B → `motivo == "ya_es_el_activo"` y B es la activa.

En `tests/test_bautizar_a.py`:

- `test_bautizar_a_un_recluta`: un recluta con `nombre == ""` en la incubadora → queda con el nombre; la activa no cambia; y las demás columnas del recluta siguen como estaban en la base (escribe sólo el nombre: cambia su comida en la base antes de llamar y comprueba que sigue así).
- `test_bautizar_a_rechaza_el_nombre_de_su_especie`, `test_bautizar_a_uno_con_nombre_es_ya_bautizado`, `test_bautizar_a_uno_ajeno_o_muerto_es_no_esta` (con sus motivos y frases exactas).

En las pruebas de Discord que ya cubren el menú del plantel y el modal del nombre (o con el doble de interacción que usen): el menú llama a `economia.cambiar_de_activo` y sus frases siguen letra por letra; el modal con `criatura_id` llama a `nacer.bautizar_a` y, enviado dos veces, contesta «Ese gachamon ya tiene nombre.».

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_cambiar_de_activo.py tests/test_bautizar_a.py -q`
Expected: FAIL (no existen).

- [ ] **Step 3: Implementar**

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_cambiar_de_activo.py tests/test_bautizar_a.py tests/test_vistas.py tests/test_taller.py tests/test_nombres.py tests/test_economia_cuidado.py tests/test_estilo_ficha.py tests/test_usar_objeto.py -q` y después la suite entera.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(economia): cambiar de activo y bautizar a uno concreto son reglas del juego, también en Discord"
```

---

### Task 3: La ficha completa, en el servidor

**Files:**
- Create: `web/ficha.py`
- Modify: `web/app.py` (registrar el router)
- Test: `tests/test_web_ficha.py` (nuevo)

**Interfaces:**
- Consumes: `estado.ficha(criatura, ahora)` (la ficha de siempre), `db.efectos_activos`, `logros`, `db.logros_de`, `db.logros_de_persona`, `db.marcador`, `db.marcador_de_persona`, `db.especies_de`, `per.nombre_caracter`, `cos.buscar`.
- Produces: `GET /gachamon/api/ficha` →

```json
{
  "gachamon": "<estado.ficha(activa, ahora)>",
  "detalle": {
    "caracter": "Tímido",
    "sombrero": "Corona",
    "experiencia": {"nivel": 2, "xp": 40, "para_subir": 100},
    "estadisticas": [
      {"clave": "fuerza", "nombre": "Fuerza", "valor": 12, "efecto": {"bonus": 3, "segundos": 240}}
    ]
  },
  "medallas": {
    "del_gachamon": [{"clave": "malcriado", "nombre": "Malcriado", "como": "recibe 500 cuidados",
                      "gemas": 30, "tiene": false, "progreso": {"hecho": 100, "meta": 500}}],
    "tuyas": []
  },
  "saldos": {"monedas": 0, "gemas": 0}
}
```

  `estadisticas` va en el orden de `sim.ESTADISTICAS`, con nombres «Fuerza», «Velocidad», «Salud» e «Ingenio»; `valor` es la propiedad de la criatura (ya topada); `efecto` es `None` sin efecto en curso, y `segundos` se redondea hacia arriba. `sombrero` es el nombre del sombrero o `None`. `para_subir` es `sim.xp_para_subir(nivel)`. Las medallas, en el orden de `logros.del_gachamon()` y `logros.de_la_persona()`; `progreso` sólo si no la tiene y `meta > 1`, con `hecho` topado en la meta. Sin activa tras `db.activa_al_dia` → 409 `sin_gachamon`, «No tienes un gachamon.».

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_web_ficha.py`, con el cliente de pruebas y reloj quieto:

- `test_las_cuatro_estadisticas_en_orden`: claves `["fuerza", "velocidad", "salud", "ingenio"]` y cada `valor` igual a la propiedad del gachamon en la base.
- `test_un_efecto_en_curso_sale_con_lo_que_le_queda`: un efecto de fuerza +3 que acaba en `ahora + 4 min` → `{"bonus": 3, "segundos": 240}`; las demás, `None`; uno que ya acabó, `None`.
- `test_la_experiencia_y_el_caracter`: `nivel`, `xp`, `para_subir == sim.xp_para_subir(nivel)` y `caracter == per.nombre_caracter(criatura)`.
- `test_el_sombrero_puesto`: `None` sin sombrero; «Corona» con la corona puesta.
- `test_las_medallas_con_su_progreso`: con el marcador de cuidados en 100 y las medallas pagadas con `economia.pagar_logros` → `consentido` sale `tiene: True` y `progreso: None`; `malcriado`, `{"hecho": 100, "meta": 500}`; `primera_sangre` (meta 1), `progreso: None`; las listas tienen tantas como `logros.del_gachamon()` y `logros.de_la_persona()`.
- `test_mirar_la_ficha_no_escribe`: con «Veterano» cumplido y sin pagar, pedir la ficha no cambia el saldo de gemas ni anota la medalla; `veterano` sale `tiene: False` y `progreso == {"hecho": 30, "meta": 30}`.
- `test_sin_gachamon_es_un_409` y `test_sin_sesion_es_un_401`.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_ficha.py -q`
Expected: FAIL (404).

- [ ] **Step 3: Implementar `web/ficha.py`**

Router fino: arma el JSON con las funciones de arriba; no paga medallas.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_ficha.py tests/test_web_app.py -q`
Expected: PASS (incluida la prueba que vigila que la web no carga `discord`).

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): la ficha completa, con estadísticas, efectos, experiencia y medallas"
```

---

### Task 4: El ropero, en el servidor

**Files:**
- Create: `web/ropero.py`
- Modify: `web/app.py`
- Test: `tests/test_web_ropero.py` (nuevo)

**Interfaces:**
- Consumes: Task 1 (`equipar_cosmetico`/`quitar_cosmetico` con `criatura_id` y motivos, `db.quien_lleva_cada`), `la_misma_activa` (`web/cuenta.py`), `estado.armar`, `cos.texto_del_titulo`.
- Produces:
  - `GET /gachamon/api/ropero` → `{"gachamon": {"id": int, "nombre": str}, "piezas": [{"clave": str, "nombre": str, "tipo": "sombrero" | "titulo", "puesta": bool, "lo_lleva": str | None}], "saldos": {...}}`. Sólo las piezas de `db.ropero` que están en `cos.CATALOGO` (lo retirado nunca), en el orden del catálogo. `puesta` si la lleva el activo; `lo_lleva`, el nombre de **otro** gachamon vivo que la lleve. Sin activo → 409 `sin_gachamon`.
  - `POST /gachamon/api/ropero/poner`, cuerpo `{"clave": str, "gachamon_id": int}`, y `POST /gachamon/api/ropero/quitar`, cuerpo `{"tipo": "sombrero" | "titulo", "gachamon_id": int}`. `gachamon_id` obligatorio y entero; `clave` del catálogo; `tipo` de `cos.TIPOS`: si no, 422 `peticion`. Primero `la_misma_activa(jugador, ahora, "No tienes un gachamon que vestir.")`; después la regla con `criatura_id=gachamon_id`; `sin_gachamon` de la regla → 409 `sin_gachamon`, «Tu gachamon ya no es el mismo. Mira otra vez.».
  - Respuesta: `{"ok": bool, "clave": str | None, "mensaje": str, "ropero": <lo de GET>, "estado": estado.armar(...)}`. `ya_lo_lleva` y `no_lleva_nada` son `ok: true`. Frases (con `{nombre}` el del gachamon y `{pieza}` el nombre del catálogo):
    - poner un sombrero: «{nombre} ya lleva {pieza}.»; poner un título: «Ahora es {nombre} {cos.texto_del_titulo(clave, genero)}.»; si sustituyó a otro, se añade « {sustituido} vuelve a tu ropero.» (`ya_lo_lleva` dice lo mismo, sin la segunda frase);
    - quitar: «{nombre} ya no lleva {pieza}. Está en tu ropero.»; `no_lleva_nada`: «{nombre} no lleva ningún sombrero.» / «{nombre} no lleva ningún título.»;
    - `lo_lleva_otro`: «{pieza}: lo lleva {otro}. Quítaselo primero.»; `no_lo_tienes`: «Ya no tienes {pieza}.».

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_web_ropero.py`:

- `test_el_ropero_ensena_lo_que_tienes_y_quien_lo_lleva`: con una corona puesta en el activo, una chistera libre y un título que lleva otro gachamon (cuenta vinculada con dos) → `puesta`, libre y `lo_lleva == "Nube"`, en el orden del catálogo; una pieza retirada en el ropero no sale.
- `test_poner_un_sombrero` (frase exacta, `ok: true`, y el `retrato` del estado lleva la clave del sombrero), `test_poner_un_titulo` (frase con el título concordado), `test_poner_en_lugar_de_otro` (frase con «Chistera vuelve a tu ropero.»).
- `test_poner_lo_que_ya_lleva_es_un_si` y `test_quitar_sin_nada_es_un_si`.
- `test_quitar`, `test_lo_que_lleva_otro` (200, `ok: false`, `lo_lleva_otro`, frase exacta), `test_lo_que_ya_no_tienes`.
- `test_si_la_pantalla_ensena_otro_gachamon_es_un_409_y_no_cambia_nada`.
- `test_peticiones_mal_hechas`: sin `gachamon_id`, con `gachamon_id` `"3"` o `null`, con una `clave` que no es del catálogo y con un `tipo` desconocido → 422 `peticion`; sin cabecera → 403.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_ropero.py -q`
Expected: FAIL (404).

- [ ] **Step 3: Implementar `web/ropero.py`**

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_ropero.py tests/test_web_app.py tests/test_ropero.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): el ropero, para poner y quitar el sombrero y el título"
```

---

### Task 5: La incubadora abre

**Files:**
- Create: `web/incubadora.py`
- Modify: `web/static/datos/pueblo.json` (incubadora: `"abre": "ya"`), `web/pueblo.py` (`OFRECE`), `globos.py` (una frase), `web/juego.py` (`POST /bautizar` y la frase de `POST /huevo`), `web/estado.py` (`sin_nombre`), `web/app.py`
- Test: `tests/test_web_incubadora.py` (nuevo), `tests/test_web_nacer.py` (huevo y bautizo); ajustar las pruebas que fijan que la incubadora «abre pronto» y la frase que se va

**Interfaces:**
- Consumes: Task 2 (`economia.cambiar_de_activo`, `nacer.bautizar_a`).
- Produces:
  - `pueblo.OFRECE["incubadora"] == ("incubadora",)`.
  - `GET /gachamon/api/incubadora` → `{"plantel": [{"id": int, "nombre": str, "sin_nombre": bool, "nombre_especie": str, "nombre_etapa": str, "nivel": int, "retrato": str, "activo": bool}], "maximo": db.MAXIMO_PLANTEL, "saldos": {...}}`, con `db.plantel` tras `db.activa_al_dia` (la activa primero y luego por id); `nombre` es `""` para un recluta; `retrato` con la misma forma de dirección que `estado.ficha`.
  - `POST /gachamon/api/incubadora/sacar`, cuerpo `{"gachamon_id": int}` (entero obligatorio; si no, 422 `peticion`). Si el lugar donde estás no ofrece `"incubadora"` → 409 `no_estas_ahi`, «Para eso tienes que estar en la incubadora.» (la misma clave que la tienda). Después, `economia.cambiar_de_activo`. Respuesta `{"ok", "clave", "mensaje", "incubadora": <lo de GET>, "estado": estado.armar(...)}`: `ok` → «{nombre} sale de la incubadora.»; `ya_es_el_activo` → `ok: true`, «{nombre} ya es tu gachamon activo.»; `sin_nombre` → «Antes de sacarlo, ponle nombre.»; `no_esta` → «Ese gachamon ya no está.». Si al ponerlo al día murió el activo, el `estado` trae el `difunto` y la pantalla decide.
  - `POST /gachamon/api/bautizar` gana `gachamon_id` opcional (entero; si viene y no lo es, 422 `peticion`): con él, `nacer.bautizar_a`; `NoSePuedeBautizar` → 409 con su motivo y su frase; `NombreNoVale` → 422 `nombre`, como hoy. Sin él, como hoy. Contesta `estado.armar`, como hoy.
  - `estado.armar` gana `"sin_nombre": {"id": int, "nombre_especie": str, "retrato": str} | None`: sólo cuando no hay activa y queda vivo un recluta sin nombre (el de menor id).
  - `POST /huevo` con un recluta sin nombre contesta, con la misma clave de hoy, «Antes, ponle nombre al gachamon que espera en la incubadora.».
  - `globos.DEL_LUGAR["incubadora"]`: «Todo está quietito, como si durmiera.» pasa a «Se oye un zumbido tibio, muy bajito.».

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_web_incubadora.py`:

- `test_la_incubadora_abre_y_ofrece_su_plantel`: `pueblo.LUGARES["incubadora"].abre == "ya"`, `pueblo.ofrece("incubadora") == ("incubadora",)`, y estando en ella, el estado no trae aviso.
- `test_el_plantel_en_orden`: cuenta vinculada con la activa, uno con nombre y un recluta → tres entradas, la activa primero con `activo: True`, el recluta con `sin_nombre: True` y `nombre == ""`; `maximo == 25`.
- `test_quien_juega_solo_en_la_web_ve_a_su_unico_gachamon`.
- `test_sacar_a_otro`: en la incubadora → `ok: true`, frase exacta, y `estado.gachamon.id` es el elegido.
- `test_sacar_fuera_de_la_incubadora_es_un_409` (y no cambia la activa).
- `test_sacar_al_que_ya_es_el_activo_es_un_si`, `test_sacar_a_un_recluta_sin_nombre` (`ok: false`, `sin_nombre`), `test_sacar_a_uno_ajeno_es_no_esta`.
- `test_sacar_con_un_id_que_no_es_entero_es_un_422`.
- `test_bautizar_a_un_recluta_desde_la_incubadora`: `POST /bautizar` con `gachamon_id` → el recluta tiene nombre; con el nombre de su especie → 422 `nombre`; otra vez → 409 `ya_bautizado`; con el id de otra persona → 409 `no_esta`.
- `test_si_solo_queda_un_recluta_sin_nombre_se_puede_seguir`: sin activa y con un recluta → el estado trae `sin_nombre` con su id y `gachamon: None`; tras `POST /bautizar` con ese id, el estado trae a ese gachamon como activo y `sin_nombre: None`.
- `test_el_huevo_con_un_recluta_lo_dice`: la frase nueva.
- `test_la_incubadora_ya_no_dice_que_todo_duerme`: la frase vieja no está en `globos.DEL_LUGAR["incubadora"]` y la nueva sí.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_incubadora.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar**

`en_la_incubadora` se escribe como `en_la_tienda` en `web/tienda.py` (el lugar guardado de la cuenta y `pueblo.ofrece`), sin importar ayudas de `web/tienda.py`.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_incubadora.py tests/test_web_nacer.py tests/test_web_lugar.py tests/test_web_estado.py tests/test_globos.py tests/test_web_app.py -q` y la suite entera.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): la incubadora abre: tu plantel, sacar a otro y ponerle nombre a un recluta"
```

---

### Task 6: El Refugio dice quién vive ahí y cuánto le queda

**Files:**
- Modify: `casas.py` (nueva función pura), `cogs/social.py` (`texto_de_la_casa` la usa; su texto no cambia), `web/estado.py`, `web/pueblo.py` (`aviso`)
- Test: `tests/test_casas.py`, `tests/test_carga.py` (las que fijan el texto de `/casa`), `tests/test_web_refugio.py` (nuevo)

**Interfaces:**
- Produces:
  - `casas.reparto(plantel: Iterable[sim.Criatura], hogar: Hogar) -> dict[int | None, list[sim.Criatura]]`: los vivos agrupados por el id de su casa; los de `casa_id` `None` o de una casa que no está en `hogar.casas`, bajo `None` (el refugio). Conserva el orden de entrada.
  - `estado.armar(...)["lugar"]["refugio"]`, **sólo** cuando el lugar es `"refugio"`: `{"viven": [{"id": int, "nombre": str, "nombre_especie": str, "retrato": str}], "estancia": str | None}`. `viven` sale de `casas.reparto(db.plantel(...), hogar)[None]` (con `sim.nombre_visible`). `estancia`:
    - `identidad.sin_plazo_de_refugio` → «Tu estancia aquí no tiene plazo.»;
    - le queda un día o más (`(refugio_hasta - ahora).days`) → «Tu estancia en el refugio dura {n} días más.» («1 día más» con uno);
    - le quedan menos de 24 horas → «Tu estancia en el refugio se acaba en {h} horas.», con las horas redondeadas hacia arriba («1 hora»; «en menos de una hora» si quedan menos de 60 minutos);
    - ya venció → `None` (el aviso del lugar ya lo dice).
  - `pueblo.aviso`: en el Refugio, con el gachamon a la intemperie y **casa propia** (`hogar == casas.PROPIA`) → «Se acabó tu estancia en el refugio y tu gachamon vive a la intemperie. Puedes mudarlo a tu casa, por ahora desde Discord, o comprar una más grande en la tienda.». Sin casa, la frase de hoy.

- [ ] **Step 1: Escribir las pruebas que fallan**

- En `tests/test_casas.py`: `test_el_reparto_manda_al_refugio_a_quien_no_tiene_casa_conocida` (uno en una casa, uno con `casa_id` `None` y uno con un id de una casa vendida; un muerto no sale) y que el texto de `/casa` de las pruebas que ya existen no cambia.
- En `tests/test_web_refugio.py`:
  - `test_en_el_refugio_se_ve_quien_vive_ahi`: quien juega sólo en la web, sin casa → `viven` con su gachamon y `estancia == "Tu estancia aquí no tiene plazo."`.
  - `test_con_casa_y_el_gachamon_dentro_no_vive_nadie_aqui`: `viven == []`.
  - `test_las_frases_de_la_estancia`: cuenta vinculada con la estancia a 6 días y 2 horas → «… dura 6 días más.»; a 1 día → «… dura 1 día más.»; a 5 horas y 10 minutos → «… se acaba en 6 horas.»; a 40 minutos → «… se acaba en menos de una hora.»; vencida → `None`.
  - `test_fuera_del_refugio_no_viene`: en la Tienda, `lugar` no tiene `refugio`.
  - `test_a_la_intemperie_con_casa_lo_dice`: la frase nueva exacta; y sin casa, la de hoy.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_casas.py tests/test_web_refugio.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar**

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_casas.py tests/test_carga.py tests/test_web_refugio.py tests/test_web_lugar.py tests/test_web_estado.py -q` y la suite entera.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): el refugio dice quién vive ahí y cuánto dura tu estancia"
```

---

### Task 7: Las pantallas de la ficha y el ropero

**Files:**
- Create: `web/static/js/ficha.js`, `web/static/js/ropero.js`
- Modify: `web/static/js/lugar.js` (botón «Ver ficha»), `web/static/js/pantallas.js` (`siguiente`), `web/static/js/principal.js` (`PANTALLAS`), `web/static/estilo.css`
- Test: `tests/js/pantallas.test.mjs`, `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: `GET ficha` (Task 3), `GET ropero` y `POST ropero/poner|quitar` (Task 4); de `articulos.js`: `cabeceraConSaldos`, `filaDeArticulo`, `zonaDeAviso`, `listaQueSePide`, `mensajeDe`, `hayQueDecidirDeNuevo`, `pideOtraPantalla`; `conReintentos` de `api.js`.
- Produces:
  - `siguiente(sesion, cuenta, estado, vista)` acepta `'ficha'` y `'ropero'` (cuando todo está en orden, como `'mochila'`).
  - `ficha(contenedor, estado, seguir)` y `ropero(contenedor, estado, seguir)`.

- [ ] **Step 1: Escribir las pruebas que fallan**

- `tests/js/pantallas.test.mjs`: `siguiente(..., 'ficha') === 'ficha'` y `siguiente(..., 'ropero') === 'ropero'` con todo en orden; con un difunto pendiente sigue siendo `'difunto'`.
- `tests/test_web_cliente.py`: `ficha.js` y `ropero.js` existen, no usan `innerHTML` ni contienen `http://` o `https://`; `ropero.js` manda `gachamon_id` en el cuerpo de poner y quitar.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar**

- **Lugar:** en la cabeza de la ficha, un botón «Ver ficha» que lleva a la vista `'ficha'`.
- **Ficha** (cabecera «📋 Ficha» con los saldos): el retrato, el nombre con su título, «Especie etapa · nivel N», «♂ Macho · Tímido» (o «♀ Hembra»), «Lleva Corona» si lleva sombrero; «Experiencia: 40 de 100 para el nivel 3» con su barra; «Estadísticas»: una fila por estadística con su valor y, si tiene efecto, «+3 · 4 min» (minutos redondeados hacia arriba); «Medallas de {nombre}» y «Tuyas»: cada medalla con su nombre, cómo se gana, sus gemas, y el progreso («100/500») si lo trae; las conseguidas, marcadas (la estrella llega en la Task 9; aquí, un ✓ de texto con su nombre para lector). Al pie, «Las de {nombre} se van con {él|ella} si se muere; las tuyas se quedan.». Botones «👒 Ropero» (vista `'ropero'`) y «Volver» (el lugar). Un 409 `sin_gachamon` o un fallo de sesión hace volver a decidir la pantalla, como la mochila.
- **Ropero** (cabecera «👒 Ropero»): secciones «Sombreros» y «Títulos» con las filas de `filaDeArticulo` (ícono `iconos/cosmeticos/<clave>.png`): la puesta, con «Lo lleva {nombre}.» y el botón «Quitar»; la que lleva otro, apagada, con «Lo lleva Nube.» y sin botón; las libres, con «Poner». Sin piezas: «Tu ropero está vacío. Los sombreros y los títulos se compran en la tienda, con gemas.». Cada toque manda `gachamon_id` (el `id` del gachamon del último estado), con `conReintentos`; la respuesta repinta la lista y deja el `mensaje` en la zona de aviso. Los nombres accesibles de los botones dicen la pieza («Poner Corona», «Quitar El Invicto»), como en la tienda. «Volver» lleva a la ficha.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): las pantallas de la ficha completa y del ropero"
```

---

### Task 8: Las pantallas de la incubadora y del refugio

**Files:**
- Create: `web/static/js/incubadora.js`
- Modify: `web/static/js/lugar.js` (botón «Tu plantel» y el bloque «Viven aquí»), `web/static/js/pantallas.js` (`siguiente`, `ofreceLaIncubadora`), `web/static/js/principal.js`, `web/static/js/entrada.js` (el bautizo de un recluta), `web/static/js/articulos.js` (`filaDeArticulo` acepta un nodo como ícono), `web/static/estilo.css`
- Test: `tests/js/pantallas.test.mjs`, `tests/js/entrada.test.mjs` si toca, `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: Tasks 5 y 6.
- Produces:
  - `ofreceLaIncubadora(lugar) -> boolean` en `pantallas.js`, como `ofreceLaTienda`.
  - `siguiente`: con `vista === 'incubadora'` → `'incubadora'` si el lugar la ofrece (si no, `'lugar'`); sin `estado.gachamon` y con `estado.sin_nombre` → `'bautizo'` (antes que `'huevo'`; después de `'difunto'`).
  - `filaDeArticulo({ icono, ... })`: `icono` puede ser una ruta de arte (como hoy) o un nodo ya hecho, que se usa tal cual.
  - `incubadora(contenedor, estado, seguir)`.

- [ ] **Step 1: Escribir las pruebas que fallan**

- `tests/js/pantallas.test.mjs`: `ofreceLaIncubadora({ ofrece: ['incubadora'] }) === true` y `false` con `[]` o sin lugar; `siguiente(..., 'incubadora')` según lo ofrezca o no el lugar; sin gachamon y con `sin_nombre` → `'bautizo'`; con difunto pendiente y `sin_nombre` → `'difunto'`.
- `tests/test_web_cliente.py`: `incubadora.js` existe, sin `innerHTML` ni `http`; `incubadora.js` manda `gachamon_id` al sacar y al bautizar.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar**

- **Lugar:** donde se ofrece `"incubadora"`, un botón «🥚 Tu plantel» (vista `'incubadora'`), en el mismo sitio que «Comprar». En el Refugio (`estado.lugar.refugio`), bajo la franja del lugar, el bloque «Viven aquí»: cada uno con su retrato pequeño y su nombre (o «Ninguno de tus gachamones vive aquí.»), y debajo la `estancia` si la trae.
- **Incubadora** (cabecera «🥚 Incubadora»): una fila por gachamon con su retrato (un `<img>` con su `retrato` y `alt` vacío, pasado como nodo a `filaDeArticulo`), su nombre o «Sin nombre», «Especie etapa · nivel N», y: el activo con «Activo» y sin botón; los demás con «Sacar»; los sin nombre con «Ponerle nombre», que abre en la fila el campo «¿Cómo se va a llamar?» (24 caracteres) con «Ponerle este nombre» y «No» (como la placa de la mochila). Sacar manda `POST incubadora/sacar` y bautizar `POST bautizar`, los dos con `gachamon_id` y `conReintentos`; después se vuelve a pedir la lista y el `mensaje` queda en la zona de aviso. Con un solo gachamon, bajo la lista: «Aquí esperan los gachamones que no son el activo. Ahora sólo tienes a {nombre}.»; siempre, «Caben {maximo} gachamones.». Si la respuesta trae un `estado` que pide otra pantalla (un difunto), se va a esa.
- **Bautizo de un recluta** (`entrada.js`): si el estado no trae `gachamon` y sí `sin_nombre`, la pantalla del bautizo dice «Este {nombre_especie} espera en la incubadora y todavía no tiene nombre.», enseña su retrato y manda `gachamon_id` con el nombre.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): las pantallas de la incubadora y del refugio, y el bautizo de un recluta"
```

---

### Task 9: Los efectos dibujados y la caché de los estáticos

**Files:**
- Modify: `web/static/js/lugar.js` (corazones y aviso de medalla), `web/static/js/ficha.js` (estrella en las conseguidas), `web/app.py` (cabecera de caché), `docs/arte/contrato.md` (la nota de los efectos sin usar)
- Test: `tests/test_web_app.py`, `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: `lienzoDePieza(ruta, ancho, alto)` de `arte.js`.
- Produces: las respuestas **200** bajo `{PREFIJO}/static/{version}/` llevan `Cache-Control: public, max-age=31536000, immutable`; los 404 no la llevan; la portada sigue con `no-cache`.

- [ ] **Step 1: Escribir las pruebas que fallan**

- `tests/test_web_app.py`: `test_los_estaticos_versionados_se_guardan_para_siempre` (un `.js` → la cabecera exacta), `test_un_estatico_que_falta_no_se_guarda` (404 sin `immutable`), y la portada con `no-cache`.
- `tests/test_web_cliente.py`: `lugar.js` nombra `efectos/corazon.png` y `efectos/estrella.png` y ya no contiene el carácter `❤`; `ficha.js` nombra `efectos/estrella.png`.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_app.py tests/test_web_cliente.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar**

Cada corazón de la caricia es un `lienzoDePieza('efectos/corazon.png', 32, 32)` con la misma animación de hoy (el tamaño varía por CSS entre 24 y 32 px). El aviso de medalla nueva y cada medalla conseguida de la ficha llevan delante `lienzoDePieza('efectos/estrella.png', 32, 32)` (a 20 px por CSS), con `aria-hidden`. En `docs/arte/contrato.md`, la nota «El juego todavía no dibuja…» pasa a decir dónde se usan.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_app.py tests/test_web_cliente.py tests/test_arte.py tests/test_web_js.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): los corazones y la estrella salen del arte, y los estáticos versionados se guardan"
```

---

### Task 10: Los documentos

**Files:**
- Modify: `AGENTS.md`, `README.md`, `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`

- [ ] **Step 1: `AGENTS.md`**, al final de «Invariantes del dominio», tal cual:

```markdown
- Cambiar de gachamon activo es una regla del juego (`economia.cambiar_de_activo`): la que sale queda al día antes de dormirse, y elegir a la que ya es la activa no cambia nada.
- Ponerle nombre a un gachamon concreto es una regla (`nacer.bautizar_a`): sólo a uno tuyo, vivo y sin nombre, nunca con el nombre de su especie, y sólo se escribe el nombre.
- En la web se cambia de activo estando en la Incubadora; vestir, desvestir y usar le caen sólo al gachamon que enseña la pantalla.
```

- [ ] **Step 2: `README.md`**: en la sección de la web, lo que se puede hacer ahora (la ficha completa y el ropero desde cualquier lugar; la Incubadora; quién vive en el Refugio).

- [ ] **Step 3: El documento de pendientes**: se quita lo que este plan resuelve de «Para el plan 5», y se añade una sección «Salió al ejecutar el plan 5» con lo que el controlador haya apuntado durante las tareas (te lo pasa en un archivo aparte; con la voz del documento, sin SHAs ni números de tarea).

- [ ] **Step 4: Comprobar**

Run: `./venv/bin/python -m pre_commit run --all-files && git diff --check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "docs: la ficha, el ropero, la incubadora y el refugio en la política, el README y los pendientes"
```

Después de la Task 10, el controlador recorre el juego entero con el arnés y capturas a 390 y 1280 px, lanza la revisión final de la rama y, con el sí de Felipe en cada paso, fusiona, sube y despliega.
