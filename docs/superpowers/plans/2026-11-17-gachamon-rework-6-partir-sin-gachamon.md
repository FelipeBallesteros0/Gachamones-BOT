# Rework 6 · Partir sin gachamon — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que quien empieza llegue a su departamento sin gachamon, sin huevo y con el monedero en cero, ponga su segunda cama, gane a su primer gachamon en la primera aventura y le ponga nombre; y que toda la página funcione sin ningún gachamon.

**Architecture:** El huevo deja de existir en la web. El primer gachamon lo crea una función nueva de `nacer.py` (la misma especie que daba el huevo, pero pidiendo cama como todos) detrás de una ruta nueva (`web/aventura.py`); el diálogo de la aventura lo manda el servidor. El estado gana lo que el cliente necesita para guiarse sin gachamon (el paso que toca y el nombre sugerido), y `pantallas.siguiente` deja de mandar al huevo. Con cuánto nace un monedero lo decide `economia` mirando si el día del cambio ya ocurrió, y queda anotado en el propio monedero para que la conciliación cuadre.

**Tech Stack:** Python 3.12, FastAPI, SQLite síncrono, JavaScript sin framework ni compilación, pytest y `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-14-gachamon-rework-1-departamento-design.md`, secciones 3 («Se parte sin gachamon y sin huevo», «El primero se gana en la primera aventura», «El nombre de un recluta…»), 6, 8 («La entrada cambia», «Todo tiene que funcionar sin ningún gachamon») y la 8.1 («La primera aventura», añadida con este plan).

**Dónde encaja.** Es el sexto plan del rediseño. Lo anterior ya está en la rama: nadie muere, el tiempo corre para todos, el bot en pausa, la vivienda por casillas con su día del cambio, el departamento en pantalla con su puerta y su modo construcción. Hasta este plan, el huevo seguía existiendo y el que nacía de él no pedía cama. Reconocimiento del código: `.superpowers/sdd/2026-11-17-rework-6-reconocimiento/inventario.md` (**léelo: trae archivo y línea de todo lo que este plan toca**). Se junta en la rama `rework/1-departamento` y **se publica con todo lo demás, al final**.

**Lo que no entra.** Las aventuras de siempre (con tu activo, con opciones y hallazgos): siguen siendo de un proyecto posterior. Reclutar en la web. Retirar el Refugio y la Incubadora del pueblo (es el plan 8; aquí sólo se tocan donde rozan con el huevo). Los muebles que se usan solos (el 7). Quitar del bot de Discord lo que dibuja el huevo (`pantalla.render_huevo`, `esp.HUEVO*`): el bot no se toca.

## Global Constraints

- Nada se sube, se fusiona ni se despliega: todo queda en la rama local `rework/1-departamento`.
- Los módulos de juego no importan `discord`; `web/` no importa `discord` ni nada que lo importe; `db.py` no importa `economia.py`; `departamento.py` es puro. Cada cambio de estado va en su transacción `BEGIN IMMEDIATE`. El servicio web no guarda estado del juego en memoria. El reloj es `db.ahora_utc()`; en las pruebas, el tiempo y el azar se inyectan.
- **Quién eres sale sólo de la cookie de Rowino.** Toda ruta que cambia algo es `POST` o `PUT` y exige la cabecera `X-Gachamon: 1`; las rutas se declaran con `def`. Un error se contesta `{"detail": {"clave": …, "mensaje": …}}`.
- **El dinero**: quien ya tiene monedero no pierde ni gana nada con este plan. El primer gachamon no cuesta nada. Las medallas de la persona que tocaba pagar al nacer el primero se siguen pagando, una sola vez.
- **El día del cambio no cambia lo que deja** (corre una sola vez sobre producción): este plan sólo cambia una frase de su carta. La única excepción la decidió Felipe el 2026-11-18 y es la Task 7: ese día se pagan las medallas de persona que cada quien ya tenía ganadas.
- El cliente: sin frameworks ni compilación, sin `innerHTML`, sin direcciones `http`, módulos con rutas relativas terminadas en `.js`. Ninguna clave ni precio del catálogo escritos en el JavaScript. **El pueblo vive en datos** (`web/static/datos/pueblo.json`).
- Accesibilidad, como en el resto de la página: todo se puede hacer con botones de verdad; lo que cambia se anuncia; lo que no se puede usar lleva `aria-disabled`; con movimiento reducido nada se mueve solo; el foco no se pierde.
- A quien juega se le dice «monedas» y «gemas». Las frases nuevas son **sólo** las de este plan, letra por letra.
- Sin dependencias nuevas. Nunca se abre `tamagotchi.db` ni `.env`; las pruebas usan bases temporales e ids sintéticos. El repo es público.
- Antes de editar un símbolo, GitNexus `impact` (lo corre el controlador). Cada commit: `./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "…"`, con la línea de coautoría. Las pruebas de JavaScript se corren con `node --test tests/js/*.test.mjs`.
- **Lo que decidió Felipe:**
  1. Se parte **sin gachamon y sin huevo**; quien empieza después del día del cambio tiene **0 monedas y 0 gemas**; quien ya jugaba, también quien viene de Discord, conserva lo suyo (diseño, 2026-11-14 y 2026-11-15).
  2. **El primero se gana en la primera aventura**: fija, vas tú solo con tu avatar, se une siempre, con diálogo sin opciones; se abre cuando ya pusiste la segunda cama (diseño).
  3. La entrada es: avatar → tu departamento (poner la segunda cama) → la primera aventura → el nombre. El lugar «Aventura» del mapa abre sólo esa primera aventura. Todo tiene que funcionar sin ningún gachamon (diseño).
  4. **El primero se sortea entre las diez del huevo, con sus pesos**: como el huevo de hoy (2026-11-17).
  5. **La guía es el paso que toca, bajo la pieza**: mientras no tengas gachamon, en tu departamento se lee siempre el paso siguiente (2026-11-17).
  6. **El nombre: un campo con un nombre sugerido**, que cambias o dejas (2026-11-17).
  7. **Los muebles se pueden comprar sin gachamon**; objetos y cosméticos siguen pidiendo uno (2026-11-17).
  8. Después de aprobar el plan (2026-11-17 y 2026-11-18): vincular con Discord una cuenta web de antes del cambio se queda como está (sus 50 monedas y 50 gemas de partida se quedan atrás, como su departamento); y **las medallas de persona ganadas y sin pagar se pagan el día del cambio**, una sola vez, y la carta lo dice (Task 7).
- **Lo que este plan decidió en nombre de Felipe** (se le enseñó con el plan y lo aprobó el 2026-11-17: «Apruebo, ejecútalo»):
  1. **Quién hace la primera aventura**: cualquiera que no tenga ningún gachamon vivo. Quien empieza; quien tenía una cuenta con avatar y el huevo sin romper; y quien se quedó sin ninguno antes del día del cambio. Estos dos últimos conservan sus monedas y sus gemas.
  2. **Quién «empieza»**: aquel cuyo monedero nace después del día del cambio. El día del cambio le deja monedero a todo el que ya estaba, así que desde entonces monedero nuevo es persona nueva: nace en 0 y 0.
  3. **La aventura no guarda nada hasta el encuentro.** Si cierras la página antes, empieza de nuevo. Si la cierras después, el gachamon ya es tuyo y vuelves al paso del nombre.
  4. **Al terminar vuelves a tu departamento con él**, y es el que sale contigo.
  5. **Sin gachamon**: el pueblo y los lugares se ven con tu avatar solo y sin cuidados; la mochila se ve; la ficha y el ropero no se abren; la Tienda vende muebles.
  6. El lugar «Aventura», cuando ya tienes gachamon, sigue diciendo `Esto se abre más adelante.`
  7. **El huevo desaparece de la página**: la bienvenida cambia su ícono y su nota. El dibujo del huevo de la pantalla de inicio de sesión se queda, como adorno, hasta que haya otro. En Discord, `/huevo` sigue siendo el aviso de hoy.
  8. **El primero necesita cama, como todos.** Ya no hay ningún gachamon que no la pida.
  9. **Vincular Discord sigue como hoy** (sólo sin gachamones). Si alguien amuebló sin gachamon y después vincula, ese departamento se queda atrás: queda anotado.
  10. Con cuánto nació cada monedero queda anotado en él (una columna nueva), para que el reporte de conciliación siga cuadrando.
- **Frases nuevas** (Felipe las aprobó el 2026-11-17: «Apruebo todas»; van tal cual):
  - La guía, en el departamento. Sin cama libre: `Pon tu segunda cama: entra a «Construir», tócala en los guardados y después toca una casilla.` Con cama libre: `Ya hay cama para un gachamon. Sal al pueblo y ve a «Aventura».`
  - En «Aventura», sin cama libre: `Antes pon tu segunda cama en tu departamento: sin cama, nadie se queda contigo.`
  - El título de la pantalla: `La primera aventura`.
  - El diálogo, antes del encuentro: `Sales del pueblo por el sendero. Hoy vas tú solo.` · `Entre los matorrales, algo se mueve.` · `No huye. Se queda mirándote.` Para avanzar: `Seguir`. Para el encuentro: `Acercarte`.
  - El diálogo, después: `Sale de su escondite: es {especie}.` · `Le tiendes la mano. La huele… y se queda a tu lado.` · `Desde hoy vive contigo.` Para terminar: `Volver a casa`.
  - Si ya tienes uno: `Ya tienes un gachamon. La primera aventura es sólo la de partida.` (en lugar de la del huevo).
  - El nombre: el título `¡Se vino contigo!` (en lugar de «¡Nació tu gachamon!») y, bajo el campo, `Le puedes dejar este nombre o escribir otro.` La etiqueta `¿Cómo se va a llamar?` y el botón `Ponerle este nombre` son los de hoy.
  - La bienvenida: `🏠 Empezar de cero` (cambia el ícono) y la nota `Si empiezas de cero y un gachamon se va contigo, ya no podrás traer los de Discord.`
  - La carta del alcalde, a quien no le queda ninguno: `Te dejé tu cama puesta y otra guardada: ponla y ve a «Aventura», que ahí te espera un gachamon.`
  - Aprobadas después, el 2026-11-17 y el 2026-11-18: lo que contesta la ruta de la primera aventura si no estás en el lugar, `Para eso tienes que estar en la aventura.`; en la pantalla del avatar, `Así te verán en el pueblo.`; y en la carta del alcalde, sólo a quien cobre algo, `Tenías medallas ganadas y sin cobrar: te pagué {gemas}.`

## Review Focus

1. **A medias**: cerrar la página o perder la red en cada paso de la entrada (tras el avatar, con la cama a medio poner, a mitad del diálogo, justo después del encuentro, en el paso del nombre) y volver a entrar: siempre se retoma en el paso que toca, nunca hay dos primeros ni ninguno a medias. Dos pestañas o un doble clic en `Acercarte`: un solo gachamon.
2. **La cama**: llegar a «Aventura» sin haber puesto la segunda cama; ponerla y guardarla otra vez antes de ir; tapar la entrada del departamento. Sin cama libre no hay encuentro y se dice por qué.
3. **Sin gachamon por toda la página**: el pueblo, cada lugar (también los cerrados), la Tienda, la mochila, la ficha y el ropero pedidos a mano, el departamento con su guía, «A todos», los cuidados: nada revienta ni se queda en blanco, y nada manda al huevo.
4. **Quién parte con cuánto**: cuenta nueva después del cambio (0 y 0), cuenta que ya existía (lo suyo), quien se quedó sin gachamones antes del cambio (lo suyo, y hace la aventura), una persona de Discord que nunca jugó y vincula después (0 y 0). El día del cambio corrido dos veces. La conciliación cuadra.
5. **Los que ya juegan no notan nada**: quien tiene gachamones entra como siempre, no ve guía, no puede hacer la primera aventura (ni pidiéndola a mano), y «Aventura» le dice lo de hoy.

---

### Task 1: Con cuánto se empieza

**Files:**
- Modify: `db.py` (la tabla `monederos`, `_migrar_monederos`), `economia.py` (`_asegurar_monedero`), `economia_reporte.py`
- Test: `tests/test_db.py`, `tests/test_economia_migracion.py`, `tests/test_economia_reporte.py`, `tests/test_dia_del_cambio.py`, `tests/test_web_estado.py`

**Interfaces:**
- Consumes: la marca del día del cambio (`cambios_hechos`, clave `economia.CAMBIO_DE_LA_VIVIENDA`).
- Produces: la columna `monederos.partida` (`INTEGER NOT NULL DEFAULT 50`: con cuántas monedas y gemas nació ese monedero). `economia._asegurar_monedero` crea el monedero con 50, 50 y `partida` 50 si el día del cambio **no** ha ocurrido en esa base, y con 0, 0 y `partida` 0 si ya ocurrió.

Lo que tiene que quedar:

- `monederos` gana `partida`. Una base de antes (la de producción) la recibe al arrancar, con 50 para todos los que ya están (es verdad: todos nacieron con 50). `_migrar_monederos` acepta la forma nueva y la vieja; lo que rellena al arrancar para quien tiene criaturas u objetos y no tiene monedero respeta la misma regla (50 antes del cambio, 0 después).
- `_asegurar_monedero`, en una sola sentencia (no una lectura y después una escritura): 0/0 si la marca del cambio existe; 50/50 si no.
- **Dentro del día del cambio la marca todavía no existe** cuando se asegura el monedero de cada quien: quien ya estaba y no tenía monedero recibe 50/50, como hasta ahora. Compruébalo: es lo que hace verdad «quien ya jugaba conserva lo suyo».
- `economia_reporte`: lo esperado es la suma de las `partida` más los movimientos, no `50 ×` monederos.

- [ ] **Step 1: Write the failing tests**
  - `test_un_monedero_nace_con_cincuenta_antes_del_cambio_y_con_cero_despues` (`tests/test_db.py` o el archivo de economía que ya prueba el monedero): en una base sin la marca, `economia.saldos` de alguien nuevo es 50 y 50 y su `partida` 50; tras `economia.el_dia_del_cambio`, el de **otra** persona nueva es 0 y 0 y su `partida` 0; el de la primera sigue en 50 y 50.
  - `test_el_dia_del_cambio_le_deja_cincuenta_a_quien_ya_estaba_sin_monedero` (`tests/test_dia_del_cambio.py`): una persona con sólo un avatar (sin monedero) antes del cambio: después tiene 50 y 50 con `partida` 50.
  - `test_correr_el_cambio_otra_vez_no_le_da_nada_a_nadie`: los saldos y las `partida` no cambian en la segunda corrida.
  - `test_una_base_de_antes_recibe_la_columna_con_cincuenta` (`tests/test_economia_migracion.py`): con la tabla en la forma de hoy y dos filas, tras `db.inicializar` existe `partida` y vale 50 en las dos; sus saldos no cambian.
  - `test_la_conciliacion_cuadra_con_monederos_que_nacieron_en_cero` (`tests/test_economia_reporte.py`): con un monedero de 50 y otro de 0 y sus movimientos, lo esperado es la suma de las partidas más los movimientos.
  - `tests/test_web_estado.py`: la prueba del recién llegado sigue fijando 50/50 en una base sin el cambio; una nueva, `test_quien_llega_despues_del_cambio_parte_en_cero`: tras el cambio, el estado de una cuenta nueva trae `saldos == {"monedas": 0, "gemas": 0}`.

- [ ] **Step 2: Run them to make sure they fail**

Run: `./venv/bin/python -m pytest -q tests/test_db.py tests/test_economia_migracion.py tests/test_economia_reporte.py tests/test_dia_del_cambio.py tests/test_web_estado.py`
Expected: FAIL en las nuevas (no existe `partida`; el monedero nace con 50 tras el cambio).

- [ ] **Step 3: Implement**

- [ ] **Step 4: Run everything**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS. Las pruebas de hoy que confían en 50 siguen valiendo: sus bases no han pasado por el día del cambio.

- [ ] **Step 5: Commit**

`feat(economia): quien empieza después del día del cambio parte con el monedero en cero`

---

### Task 2: El primero se gana

**Files:**
- Create: `web/aventura.py`
- Modify: `nacer.py`, `web/app.py` (o donde se montan las rutas), `web/estado.py`, `web/pueblo.py`
- Test: `tests/test_nacer.py`, `tests/test_web_aventura.py` (nuevo), `tests/test_web_estado.py`, `tests/test_pueblo.py`

**Interfaces:**
- Consumes: `esp.elegir_del_huevo(rng)`, `db.crear(..., pide_cama=True, cuenta_vigente=True)`, `db.hay_cama_libre`, `nombres.elegir`, `economia.pagar_logros_de_persona`, lo que usa `POST /lugar` para cambiar de lugar.
- Produces:
  - `nacer.encontrar_al_primero(usuario_id, guild_id, ahora, rng=None) -> Criatura`: lanza `nacer.YaTieneGachamon` si esa persona tiene algún gachamon vivo, `db.SinCamaLibre` si no tiene cama libre y `nacer.YaNoEsSuIdentidad` si la cuenta ya no es la suya. La especie, `esp.elegir_del_huevo(rng)`. Nace **activa**, pidiendo cama, con el nombre de su especie (provisional: es lo que hace que `espera_nombre` sea verdad).
  - `GET /gachamon/aventura` → `{"primera": {"puede": bool, "motivo": "ya_tienes" | "sin_cama" | null, "antes": [str, …]}}`. Exige estar en el lugar `aventura` (como la Tienda exige estar en la tienda).
  - `POST /gachamon/aventura/primera` → `{"estado": <el estado de siempre>, "despues": [str, …]}`. Errores, todos 409: `sin_avatar`, `ya_tienes`, `sin_cama`, `cuenta_cambio`, y el de no estar en el lugar, como en la Tienda.
  - En el estado: `guia` (`null`, o `{"clave": "cama" | "aventura", "texto": str}`: sólo cuando no hay ningún gachamon vivo); `gachamon.sugerido` (un nombre de la lista, cuando `espera_nombre`; el mismo en cada lectura para ese gachamon); y `lugar.ofrece` trae `"aventura"` en el lugar `aventura` sólo para quien no tiene ningún gachamon vivo.

Lo que tiene que quedar:

- `encontrar_al_primero` hace lo que hacía `romper_el_huevo` (míralo: el remiendo de la activa, la protección `cuenta_vigente`, que dos a la vez dejan uno solo por el índice único de la activa), con dos diferencias: **pide cama** y no le hace falta nada del huevo. `romper_el_huevo` y `POST /huevo` **siguen existiendo en esta tarea** (los retira la siguiente).
- `POST aventura/primera`: en este orden, avatar, estar en el lugar, crear al primero, pagar las medallas de la persona (como hace hoy el huevo), **llevarte a tu casa** (el lugar pasa a ser `casa`), y contestar el estado con las tres frases de después, con el nombre de la especie puesto.
- `GET aventura`: `puede` es verdad sólo sin gachamon vivo y con cama libre; las frases de antes van siempre que no tengas gachamon.
- El lugar `aventura`, en el estado: con gachamon, como hoy (`Esto se abre más adelante.`, sin ofrecer nada); sin gachamon, ofrece `aventura` y su aviso es, sin cama libre, `Antes pon tu segunda cama en tu departamento: sin cama, nadie se queda contigo.`, y con cama libre, ninguno. `pueblo.json` no cambia el `abre` de ese lugar: lo que cambia es lo que se le ofrece a esa persona; decide dónde vive esa regla (`web/pueblo.py`) y dilo en el informe.
- `guia`: sin gachamon vivo y sin cama libre, `cama`; sin gachamon vivo y con cama libre, `aventura`; con alguno, `null`. Con sus dos frases.
- `gachamon.sugerido`: de `nombres`, sin repetir los del plantel ni el de su especie, y estable para ese gachamon (el azar, sembrado con su id).

- [ ] **Step 1: Write the failing tests**
  - `tests/test_nacer.py`: `test_el_primero_sale_de_las_diez_del_huevo_y_pide_cama` (con el azar fijado: la misma especie que daría `elegir_del_huevo`; nace activo; su nombre es el de su especie; sin cama libre lanza `SinCamaLibre` y no crea nada); `test_con_un_gachamon_vivo_no_hay_primero`; `test_dos_primeros_a_la_vez_dejan_uno` (con la forma de la prueba de hoy de los dos huevos); `test_el_primero_no_nace_si_la_cuenta_se_vinculo_mientras_tanto`; `test_quien_se_quedo_sin_ninguno_puede_encontrar_al_primero` (con un gachamon muerto de antes).
  - `tests/test_web_aventura.py`: `test_sin_la_segunda_cama_no_hay_encuentro` (409 `sin_cama` con su frase; ningún gachamon creado); `test_el_encuentro_deja_un_gachamon_y_te_lleva_a_casa` (tras poner la cama e ir a `aventura`: 200; `estado.gachamon.espera_nombre` es verdad; `estado.lugar.clave == "casa"`; `despues` son las tres frases con el nombre de la especie; `estado.guia is None`); `test_el_segundo_encuentro_se_rechaza` (409 `ya_tienes`, con su frase); `test_fuera_del_lugar_no_hay_aventura`; `test_sin_avatar_no_hay_aventura`; `test_al_encontrarlo_se_pagan_las_medallas_de_la_persona` (como la de hoy del huevo); `test_lo_que_dice_el_lugar` (las tres frases de antes y `puede` según la cama).
  - `tests/test_web_estado.py`: `test_la_guia_dice_el_paso_que_toca` (sin cama libre, `cama` y su frase; con ella, `aventura` y la suya; con gachamon, `None`); `test_el_que_espera_nombre_trae_uno_sugerido_y_es_siempre_el_mismo`; `test_aventura_se_ofrece_solo_a_quien_no_tiene_gachamon`.
  - `tests/test_pueblo.py`: las de hoy siguen pasando (el dato del lugar no cambia).

- [ ] **Step 2: Run them to make sure they fail**

Run: `./venv/bin/python -m pytest -q tests/test_nacer.py tests/test_web_aventura.py tests/test_web_estado.py tests/test_pueblo.py`
Expected: FAIL en las nuevas (no existe `encontrar_al_primero` ni la ruta).

- [ ] **Step 3: Implement**

- [ ] **Step 4: Run everything**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS (el barrido de textos incluido).

- [ ] **Step 5: Commit**

`feat(web): el primer gachamon se gana en la primera aventura`

---

### Task 3: Sin huevo

**Files:**
- Modify: `nacer.py`, `web/juego.py`, `web/tienda.py`, `web/carta.py`, `web/incubadora.py` (sólo donde roza con el huevo), `tests/ayudas_web.py` y las pruebas que dependan de ella
- Test: `tests/test_web_nacer.py`, `tests/test_nacer.py`, `tests/test_camas.py`, `tests/test_web_tienda.py`, `tests/test_web_carta.py`, y las que usan `con_gachamon`

**Interfaces:**
- Consumes: `nacer.encontrar_al_primero` y `POST aventura/primera` (Task 2).
- Produces: ya no existen `POST /gachamon/huevo` ni `nacer.romper_el_huevo`. `tests/ayudas_web.con_gachamon(cliente, …)` deja a esa cuenta con su segunda cama puesta, su primer gachamon (de la especie fijada, como hoy) y su nombre, **por las rutas** (poner la cama, ir a `aventura`, el encuentro, el nombre), y de vuelta en su casa.

Lo que tiene que quedar:

- `POST /huevo` desaparece (un `POST` a esa dirección contesta 404, como cualquier ruta que no existe) y `nacer.romper_el_huevo` también. `esp.elegir_del_huevo`, `DEL_HUEVO` y los pesos **se quedan**: son de donde sale el primero. Lo del bot de Discord no se toca.
- Ya no hay ningún gachamon que no pida cama: se quita de `db.crear`, de `web/incubadora.py` y de sus pruebas la excepción del que nacía del huevo (el «nunca menos que los que ya tiene» de la Incubadora incluido, si con esto ya no puede darse; si sigue pudiendo darse para alguien —mira `tests/test_camas.py`—, se queda y lo dices).
- **La Tienda**: comprar un mueble no pide gachamon. Comprar un objeto o un cosmético sigue contestando `Para comprar hace falta un gachamon.`
- **La carta**, a quien no le queda ninguno: `Te dejé tu cama puesta y otra guardada: ponla y ve a «Aventura», que ahí te espera un gachamon.`
- **Las pruebas.** `con_gachamon` tiene cerca de ciento cincuenta usos: tras este cambio, quien tiene un gachamon tiene dos camas puestas y ninguna guardada, y está en su casa. Las pruebas que daban por hecho otra cosa (una cama puesta y otra guardada con un gachamon; el gachamon sin cama) se ponen al día **sin perder lo que comprueban**. Las del huevo como tal (`tests/test_web_nacer.py`, `tests/test_nacer.py`) pasan a ser las de la primera aventura donde comprueban algo que sigue existiendo (las de la Task 2 ya cubren varias: no dupliques, y di cuál cubre a cuál); las que comprueban algo que desaparece con el huevo se sustituyen por una que fija que ya no existe. **Lista en el informe cada prueba que cambiaste, quitaste o sustituiste, y por qué**, en una tabla. Es la única tarea del plan en la que se puede quitar una prueba, y sólo si lo que comprobaba ya no existe.

- [ ] **Step 1: Write the failing tests**
  - `test_el_huevo_ya_no_existe` (`tests/test_web_nacer.py`): `POST /gachamon/huevo` → 404; y `nacer` no tiene `romper_el_huevo`.
  - `test_un_mueble_se_compra_sin_gachamon` y `test_un_objeto_sigue_pidiendo_gachamon` (`tests/test_web_tienda.py`): con monedas y sin gachamon, el felpudo se compra (200, y queda en guardados); el objeto contesta 409 con la frase de hoy.
  - `tests/test_web_carta.py`: la frase nueva, entera, para quien no tiene vivos.
  - `test_todo_gachamon_pide_cama` (`tests/test_camas.py`): no queda forma de crear uno por las rutas sin cama libre.
  - `test_la_ayuda_con_gachamon_deja_dos_camas_puestas_y_esta_en_casa` (junto a la de hoy de la ayuda).

- [ ] **Step 2: Run them to make sure they fail**

Run: `./venv/bin/python -m pytest -q tests/test_web_nacer.py tests/test_web_tienda.py tests/test_web_carta.py tests/test_camas.py`
Expected: FAIL en las nuevas.

- [ ] **Step 3: Implement**, empezando por `tests/ayudas_web.py`.

- [ ] **Step 4: Run everything**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS, toda la suite.

- [ ] **Step 5: Commit**

`feat(web): el huevo se va: todo gachamon pide cama y los muebles se compran sin gachamon`

---

### Task 4: La página, sin gachamon

**Files:**
- Modify: `web/static/js/pantallas.js`, `web/static/js/principal.js`, `web/static/js/entrada.js`, `web/static/js/lugar.js`, `web/static/js/mapa.js`, `web/static/estilo.css` (lo que deje huérfano el huevo)
- Test: `tests/js/pantallas.test.mjs`, `tests/js/entrada.test.mjs`, `tests/js/api.test.mjs`, y las de `lugar` y `mapa` que hagan falta (hoy `lugar.js` no tiene pruebas de JavaScript: se le escribe lo mínimo que fije lo de esta tarea)

**Interfaces:**
- Consumes: el estado sin gachamon (`gachamon: null`, `globos: []`, `guia`) y `lugar.ofrece` con `"aventura"` (Task 2).
- Produces: `pantallas.siguiente` ya no devuelve `'huevo'`; devuelve `'aventura'` cuando el lugar la ofrece y se pide esa vista, igual que hace con `'tienda'`. La Task 5 pone la pantalla; en esta tarea `PANTALLAS.aventura` todavía no existe, así que **`siguiente` sólo la devuelve cuando se pide esa vista**, y nadie la pide aún.

Lo que tiene que quedar:

- `siguiente`: sin gachamon ya no se va al huevo: se sigue como cualquiera (el pueblo, el departamento o el lugar, la tienda, la mochila). Sin gachamon, pedir la ficha o el ropero deja donde estás. El paso del nombre (`espera_nombre`) sigue yendo antes que todo lo demás. La rama muerta de `sin_nombre` se quita. Sus pruebas de hoy se ponen al día.
- `principal.js`: sale `huevo` de la tabla de pantallas.
- `entrada.js`: sale la pantalla del huevo y lo que sólo ella usaba (también las ramas muertas del recluta sin nombre). La bienvenida cambia a `🏠 Empezar de cero` y su nota a `Si empiezas de cero y un gachamon se va contigo, ya no podrás traer los de Discord.` `dibujarHuevo` se queda (lo usa la pantalla de inicio de sesión).
- `lugar.js` **no revienta sin gachamon**: se ve el lugar con tu avatar solo, su aviso si lo tiene, y sus salidas; sin ficha, sin cuidados, sin globo. Con gachamon, exactamente igual que hoy.
- `mapa.js` **no revienta sin gachamon**: caminas tú solo. Con gachamon, igual que hoy.
- En la mochila sin gachamon, «Usar» sigue contestando lo que conteste el servidor; nada revienta.

- [ ] **Step 1: Write the failing tests**
  - `tests/js/pantallas.test.mjs`: `sin gachamon ya no se va al huevo: se sigue al departamento` (en casa → `'departamento'`; en la tienda → `'lugar'` o `'tienda'` según la vista; con `vista: 'pueblo'` → `'pueblo'`); `sin gachamon, la ficha y el ropero dejan donde estás`; `la aventura se abre sólo donde se ofrece` (con `lugar.ofrece` que la trae y `vista: 'aventura'` → `'aventura'`; sin ofrecerla → el lugar); `el que espera nombre va al nombre antes que a nada`; y que `'huevo'` no sale nunca (recorre los casos de las pruebas de hoy).
  - `tests/js/entrada.test.mjs`: la bienvenida dice `Empezar de cero` con su nota nueva; no existe la pantalla del huevo.
  - Para `lugar.js` y `mapa.js`: una prueba por pantalla que la abra con un estado sin gachamon y compruebe que no lanza y qué se ve (el aviso del lugar, sin botones de cuidar); y otra con gachamon que fije lo de hoy que más importa (la ficha y sus cuidados están).

- [ ] **Step 2: Run them to make sure they fail**

Run: `node --test tests/js/*.test.mjs`
Expected: FAIL en las nuevas.

- [ ] **Step 3: Implement**

- [ ] **Step 4: Run the tests**

Run: `node --test tests/js/*.test.mjs` y `./venv/bin/python -m pytest -q`
Expected: PASS, todo.

- [ ] **Step 5: Míralo** (obligatorio). Con el arnés (copia el más reciente a una carpeta tuya; bases temporales armadas con el código de ahora; puertos que no sean 8000, 8010, 8011 ni 8061; apaga por su pid lo que levantes), con una cuenta nueva sin gachamon, capturas en 390 × 664 y en 1280: la bienvenida; tu departamento vacío de gachamones; el pueblo caminando tú solo; un lugar cerrado; la Tienda; la mochila. Y una con gachamon, para ver que el lugar sigue igual. Las rutas completas, al informe.

- [ ] **Step 6: Commit**

`feat(web): la página funciona sin ningún gachamon y ya no hay huevo`

---

### Task 5: La primera aventura y la guía, en pantalla

**Files:**
- Create: `web/static/js/aventura.js`
- Modify: `web/static/js/principal.js`, `web/static/js/pantallas.js` (si hace falta), `web/static/js/lugar.js` (el botón que lleva a la aventura donde se ofrece), `web/static/js/entrada.js` (el paso del nombre), `web/static/js/departamento.js` (la guía), `web/static/estilo.css`
- Test: `tests/js/aventura.test.mjs` (nuevo), `tests/js/entrada.test.mjs`, `tests/js/departamento.test.mjs`, `tests/js/pantallas.test.mjs`

**Interfaces:**
- Consumes: `GET aventura` y `POST aventura/primera`, `estado.guia`, `estado.gachamon.sugerido` (Task 2); `siguiente` con `'aventura'` (Task 4).
- Produces: la pantalla `aventura` en la tabla de `principal.js`.

Lo que tiene que quedar:

- **En el lugar «Aventura»**, a quien se le ofrece: se llega a la pantalla de la primera aventura como se llega a la Tienda desde su lugar (mira cómo lo hace hoy la Tienda y hazlo igual). Sin cama libre, el lugar dice su aviso y no hay encuentro.
- **La pantalla** (`La primera aventura`): la escena del lugar, tu avatar, y el diálogo de a una frase, con `Seguir`. Tras la tercera, el botón es `Acercarte`: manda `POST aventura/primera` **una sola vez** (un doble toque o un reintento no crean dos: el servidor rechaza el segundo, y el cliente no lo manda dos veces a la vez). Con la respuesta, se ve a tu gachamon (su retrato) y las tres frases de después, con `Seguir`; tras la última, `Volver a casa`, que sigue con el estado recibido: toca el paso del nombre.
  - Si el servidor dice `sin_cama` o `ya_tienes`, se ve su frase y un botón para volver al lugar.
  - Si no hay respuesta, se dice lo de siempre y `Acercarte` se puede volver a pulsar.
  - Lo que se dice va en un `role="status"`; el foco queda en el botón que avanza; con movimiento reducido nada entra animado.
- **El paso del nombre**, para el que espera nombre: el título `¡Se vino contigo!`, el campo con `estado.gachamon.sugerido` ya escrito y, debajo, `Le puedes dejar este nombre o escribir otro.` Lo demás, como hoy (`¿Cómo se va a llamar?`, `Ponerle este nombre`, los errores del servidor). Al ponerlo se sigue: estás en tu casa, con él.
- **La guía**, en tu departamento: mientras `estado.guia` no sea `null`, su texto se lee bajo la pieza, en los dos modos, y se pone al día cuando llega un estado nuevo (al poner la cama pasa del primer paso al segundo sin recargar). No es un aviso que se borra solo. Para el lector de pantalla, se anuncia cuando cambia.

- [ ] **Step 1: Write the failing tests**
  - `tests/js/aventura.test.mjs` (con el arnés de DOM y de `fetch` de mentira de las demás pantallas): `el diálogo va de a una frase y termina en «Acercarte»`; `acercarte manda el encuentro una sola vez` (doble toque: un `POST`); `tras el encuentro se ve al gachamon, sus tres frases y «Volver a casa», que sigue con el estado recibido`; `sin cama se dice y no se manda nada más`; `sin respuesta se puede volver a intentar`; `el foco queda en el botón que avanza`.
  - `tests/js/entrada.test.mjs`: `el paso del nombre trae el sugerido escrito y dice que se puede dejar`; `con el sugerido tal cual, «Ponerle este nombre» lo manda`.
  - `tests/js/departamento.test.mjs`: `sin gachamon se lee el paso que toca, y cambia al poner la cama` (con `guia` de `cama` y, tras la respuesta de poner, de `aventura`); `con gachamon no hay guía`; `la guía se lee también construyendo`.
  - `tests/js/pantallas.test.mjs`: lo que haga falta para la entrada a la pantalla desde el lugar.

- [ ] **Step 2: Run them to make sure they fail**

Run: `node --test tests/js/*.test.mjs`
Expected: FAIL en las nuevas.

- [ ] **Step 3: Implement**

- [ ] **Step 4: Run the tests**

Run: `node --test tests/js/*.test.mjs` y `./venv/bin/python -m pytest -q`
Expected: PASS, todo.

- [ ] **Step 5: Míralo** (obligatorio). Con el arnés y una cuenta nueva, **el recorrido entero**, en 390 × 664 y en 1280: la bienvenida; el avatar; tu departamento con el primer paso de la guía; la cama puesta y el segundo paso; el pueblo; «Aventura»; cada momento del diálogo; el encuentro; el paso del nombre con el sugerido; de vuelta en casa con tu gachamon y sin guía. Y «Aventura» sin la cama puesta. Las rutas completas, al informe.

- [ ] **Step 6: Commit**

`feat(web): la primera aventura, el nombre sugerido y el paso que toca en tu departamento`

---

### Task 6: Los documentos

**Files:**
- Modify: `AGENTS.md`, `README.md`, `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`

- [ ] **Step 1: `AGENTS.md`**: donde dice que mientras exista el huevo el que nace de él no pide cama, ahora todo gachamon la pide, también el primero; una línea con lo nuevo que es duradero (el primero lo crea `nacer.encontrar_al_primero` detrás de la ruta de la primera aventura; un monedero nace con 50 antes del día del cambio y con 0 después, y lo anota en `partida`). Cada nombre, comprobado con `git grep`. Sin SHAs ni cantidades.
- [ ] **Step 2: `README.md`**: todo lo que habla del huevo en la web (la entrada, cómo se empieza) se pone al día, en llano.
- [ ] **Step 3: Pendientes**: una sección «Salió al ejecutar el rework 6 (partir sin gachamon)», con la forma de las anteriores: lo que decidió el dueño, lo que el plan propuso y él aprobó, lo que se decidió al construir (se puede cambiar) y lo que queda. Las notas del controlador estarán en la carpeta de trabajo del plan (`notas-para-la-tarea-6.md`). En las secciones anteriores, una nota breve en cada punto que este plan resuelve o cambia (el estado intermedio del huevo, el «nunca menos» de la Incubadora, lo de amueblar sin gachamon y vincular).
- [ ] **Step 4: Run everything**

Run: `./venv/bin/python -m pytest -q` y `node --test tests/js/*.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

`docs: partir sin gachamon, en la política, el README y los pendientes`

---

### Task 7: Las medallas ganadas se pagan el día del cambio

Añadida el 2026-11-18. Al revisar el pago de las medallas del primero salió algo anterior a este plan: hay personas con medallas **de persona** ganadas y sin pagar (la de un recluta, la de diez y la de haber tenido una rara). En Discord se cobraban al usar `/logros`, al reclutar o al nacer un gachamon; con el bot en pausa, ninguna ruta de la web se las paga a quien ya tiene gachamones. **Felipe decidió (2026-11-18) que se paguen el día del cambio**, una sola vez, y que la carta lo diga. Es la única excepción a «el día del cambio no cambia lo que deja».

**Files:**
- Modify: `economia.py` (`pagar_logros_de_persona`, `_mudar_a`), `web/carta.py`
- Test: `tests/test_dia_del_cambio.py`, `tests/test_web_carta.py`, y el archivo que ya prueba `pagar_logros_de_persona`

**Interfaces:**
- Consumes: `lgr.hechos_de_la_persona`, `lgr.cumplidos(…, lgr.PERSONA)`, `db.anotar_logro_de_persona_en`, `_cobrar_logros` (lo que usa hoy `pagar_logros_de_persona`).
- Produces: en lo que guarda la carta de cada persona (`db.guardar_carta_en`), la clave `gemas_por_medallas` (un entero; 0 si no cobró nada). `economia.pagar_logros_de_persona(usuario_id, guild_id, ahora)` conserva su firma y lo que devuelve.

Lo que tiene que quedar:

- El pago de las medallas de la persona se puede hacer **dentro de una transacción que ya está abierta** (la del día del cambio): lo que hoy hace `pagar_logros_de_persona` con su propia conexión pasa a una función que recibe la conexión, y `pagar_logros_de_persona` la llama con la suya. No se copia la lógica: queda en un solo sitio.
- `_mudar_a` (el cambio de cada persona) paga con ella las medallas de persona que esa persona tenga cumplidas y sin anotar, **dentro de la misma transacción del cambio**, y guarda en su carta cuántas gemas fueron. Tenga o no gachamones vivos. Las medallas quedan anotadas como cualquier otra (no se pagan dos veces, ni ese día ni después).
- La carta, sólo a quien cobró algo, junto a las devoluciones y antes de lo de los nombres: `Tenías medallas ganadas y sin cobrar: te pagué {gemas}.` (con las gemas dichas como siempre: `70 gemas`, `1 gema`).
- **Nada más del día del cambio cambia**: ni su orden, ni la marca, ni lo que devuelve por casas y tickets, ni las camas, ni la puerta. Quien no tenía ninguna medalla pendiente queda exactamente como quedaba, carta incluida.
- Las medallas **de un gachamon** (las que necesitan una criatura viva delante) no entran: sólo las tres de la persona.

- [ ] **Step 1: Write the failing tests**
  - `test_el_cambio_paga_las_medallas_de_persona_ganadas_y_sin_cobrar` (`tests/test_dia_del_cambio.py`): una persona con el marcador de reclutados en 10 y una rara en su historial (viva o muerta), sin ninguna medalla de persona anotada, con 12 gemas: tras el cambio tiene 12 más lo que valen `domador`, `flautista` y `uno_entre_veinticinco` (los valores, de `logros`, no escritos a mano), las tres quedan anotadas, y su carta guarda ese total en `gemas_por_medallas`.
  - `test_quien_no_tenia_medallas_pendientes_queda_como_quedaba`: su saldo de gemas no cambia y su carta trae `gemas_por_medallas == 0`.
  - `test_las_ya_anotadas_no_se_vuelven_a_pagar`: con `domador` ya anotada y cumplida también `flautista`, cobra sólo `flautista`.
  - `test_tambien_cobra_quien_no_tiene_ningun_gachamon_vivo`.
  - `test_correr_el_cambio_otra_vez_no_paga_las_medallas_otra_vez` (o, si la prueba de hoy de la segunda corrida ya lo cubre al comparar saldos, se le añaden las gemas y las medallas anotadas).
  - `test_despues_del_cambio_pedir_las_medallas_no_paga_nada_mas`: tras el cambio, `economia.pagar_logros_de_persona` de esa persona devuelve un recibo vacío.
  - `tests/test_web_carta.py`: con `gemas_por_medallas` de 70, la carta trae `Tenías medallas ganadas y sin cobrar: te pagué 70 gemas.` en su sitio; con 1, `…te pagué 1 gema.`; con 0 o sin la clave (una carta guardada antes de este cambio), no la trae. La prueba que fija la carta entera se pone al día.
  - Las pruebas de hoy de `pagar_logros_de_persona` pasan sin tocarlas.

- [ ] **Step 2: Run them to make sure they fail**

Run: `./venv/bin/python -m pytest -q tests/test_dia_del_cambio.py tests/test_web_carta.py`
Expected: FAIL en las nuevas.

- [ ] **Step 3: Implement**

- [ ] **Step 4: Run everything**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

`feat(economia): el día del cambio paga las medallas de persona ganadas y sin cobrar`
