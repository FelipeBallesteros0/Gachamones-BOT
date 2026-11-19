# Rework 8 · El pueblo sin Refugio ni Incubadora, y los documentos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar el rediseño: el mapa pierde el Refugio y la Incubadora, «Tu casa» pasa a llamarse «Tu departamento» en todas partes, la pantalla de la Incubadora desaparece (lo que hacía ya se hace en el departamento), se resuelven las tres cosas que quedaban sin decidir para quien juega (la Tienda sin gachamon, la frase del encuentro y el cambio de nombre de los reclutas, que pasa a ser una placa de regalo), y los documentos quedan diciendo lo que el juego es hoy, con una lista única para el día de publicar.

**Architecture:** El pueblo vive en datos (`web/static/datos/pueblo.json`): quitar un lugar es quitarlo de ahí con su nodo y su arista, y el contrato del arte, los globos y el mapa lo siguen solos. La Incubadora es un router, un módulo de JavaScript y un botón: se borran enteros, después de mudar las pruebas que vivían en su archivo sin ser suyas. La clave interna del lugar sigue siendo `casa`; sólo cambian su nombre y su «hacia». La placa de regalo es un objeto más que el día del cambio deja en la mochila, dentro de su misma transacción.

**Tech Stack:** Python 3.12, FastAPI, SQLite síncrono, JavaScript sin framework ni compilación, pytest y `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-14-gachamon-rework-1-departamento-design.md`, secciones 3, 6 y **8** (puestas al día con este plan). Inventario del código afectado: `.superpowers/sdd/2026-11-19-rework-8-reconocimiento/inventario.md` (con archivo y línea; léelo antes de cada tarea).

**Dónde encaja.** Es el octavo y último plan del rediseño. Todo lo anterior ya está en la rama y el dueño lo probó en una página viva. Después de éste sólo quedan el ensayo sobre una copia de la base (que pide permiso expreso del dueño) y publicar.

**Lo que no entra.** Publicar, fusionar o ensayar sobre la base: este plan sólo deja escrita la lista. Renombrar la clave interna `casa`. Una pantalla para cambiarle el nombre a un recluta (el dueño eligió regalar una placa en su lugar). Abrir lugares nuevos, el cementerio para explorar, reclutar en la web o las aventuras de siempre. El arte de verdad. Arreglar la conciliación tras el día del cambio (queda dicho en la lista de publicar cómo cuadrarla).

## Global Constraints

- Nada se sube, se fusiona ni se despliega: todo queda en la rama local `rework/1-departamento`. **Nunca** se abre `tamagotchi.db` ni `.env`; las pruebas usan bases temporales, ids sintéticos y reloj y azar inyectados. El repo es público: ni SHAs, ni ids, ni cantidades de pruebas, ni direcciones en los documentos.
- Los módulos de juego no importan `discord`; `web/` no importa `discord` ni nada que lo importe; `db.py` no importa `economia.py`; cada cambio de estado va en su transacción `BEGIN IMMEDIATE`. El bot de Discord no se toca (`bot.py`, `comun.py`, `cogs/`, `pantalla.py`).
- **El pueblo vive en datos**: ninguna lista de lugares ni coordenada en el código; el JavaScript no lleva claves de lugar ni del catálogo. **La clave `casa` no se renombra.**
- **No se le pone aviso al lugar «Aventura»**: el botón de la primera aventura deduce que hay cama libre de que ese lugar no traiga aviso.
- **El día del cambio** (`economia.el_dia_del_cambio`) corre una sola vez sobre producción y todavía no ha corrido. Este plan le añade **una sola cosa** (Task 5: las placas) y cambia dos frases de su carta; nada más de lo que deja puede cambiar. **El dinero**: nadie gana ni pierde monedas ni gemas con este plan.
- **Toda lectura de barras pasa por `db.avanzar`** (lo vigilan `tests/test_web_minimos.py` y la guarda de lecturas crudas de `tests/test_web_app.py`): al quitar rutas, esas dos pruebas se ponen al día sin aflojarlas.
- El cliente: sin frameworks ni compilación, sin `innerHTML`, sin direcciones `http`, módulos con rutas relativas terminadas en `.js`. Las listas de archivos vigilados de `tests/test_web_cliente.py` se ponen al día cuando un archivo se borra, sin quitar ninguna vigilancia de los que quedan.
- Accesibilidad, como en el resto de la página. A quien juega se le dice «monedas» y «gemas». **Las frases nuevas o cambiadas son sólo las de este plan, letra por letra**; ninguna otra letra de un texto de la página cambia.
- Antes de editar un símbolo, GitNexus `impact` (lo corre el controlador; `pueblo.ofrece` sale de riesgo **alto** porque lo llaman la Tienda, el departamento, la Incubadora y el estado: la función no cambia, sólo pierde una entrada la tabla que consulta; `economia._mudar_a` y `web/carta.lineas_de`, bajo). Cada commit: `./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "…"`, con la línea de coautoría. Las pruebas de JavaScript: `node --test tests/js/*.test.mjs`.
- **Lo que decidió Felipe** (el diseño, 2026-11-14; y el 2026-11-19, eligiendo entre opciones que se le propusieron salvo donde se dice):
  1. El mapa pierde el Refugio y la Incubadora, y «Tu casa» pasa a llamarse «Tu departamento» (diseño; propuesta suya aceptada).
  2. Las tres frases que nombraban la casa pasan a decir «tu departamento» («Apruebo las tres», 2026-11-19).
  3. El globo del departamento dice «el silencio del edificio» (2026-11-19).
  4. **El cambio de nombre de los reclutas que se nombraron solos no se construye: se regala una placa con nombre en su lugar** (lo escribió él: «les regalas una placa con nombre en su lugar, es mas sencillo»), **una por cada recluta** (2026-11-19).
  5. **La Tienda sin gachamon lo enseña todo, con una nota** («Enseñarlo todo con una nota», y aprobó la frase; 2026-11-19).
  6. **La frase del encuentro concuerda con el género**: «es un…» / «es una…» (2026-11-19).
- **Lo que este plan decide en nombre de Felipe** (se le enseñó con el plan y lo aprobó el 2026-11-19: «Apruebo, ejecútalo»):
  1. La pantalla de la Incubadora se borra entera, con su botón «Tu plantel»: ver a todos y elegir con quién sales ya se hace en tu departamento. Quien tenga la página abierta ahí el día de publicar verá «Eso no existe.» hasta recargar.
  2. Quien se quedó parado en el Refugio o en la Incubadora aparece en su departamento (ya pasaba con cualquier lugar que deja de existir).
  3. La regla del servidor que deja cambiarle el nombre una vez a un recluta **se queda como está, sin pantalla**: la placa es la forma de hacerlo en la página. Se decidirá de nuevo cuando vuelva reclutar.
  4. Las placas se regalan **el día del cambio**, a cada recluta **vivo** que se puso el nombre solo, y la carta lo dice.
  5. La nota de la Tienda sale arriba de las pestañas de objetos y de cosméticos mientras no tengas ningún gachamon; la de muebles no la lleva.
  6. El dibujo de relleno de la escena de la casa, que ninguna pantalla pinta, sale del contrato del arte junto con los del Refugio y la Incubadora.
- **Frases nuevas o cambiadas** (Felipe las aprobó todas el 2026-11-19, las de la carta con «Apruebo las tres»; van tal cual):
  - El lugar: nombre `Tu departamento`, «hacia» `a tu departamento` (el botón del mapa lee «Volver a tu departamento» y la cabecera de la pieza «Tu departamento»).
  - La Tienda, al comprar un mueble: `Compraste {nombre}. Quedó en tus guardados: en tu departamento, entra a «Construir».`
  - El último botón de la primera aventura: `Volver a tu departamento`.
  - El globo del lugar: `Aquí se oye el silencio del edificio.`
  - La nota de la Tienda sin gachamon: `Para comprar objetos y cosméticos hace falta un gachamon. Los muebles sí los puedes comprar.`
  - El encuentro: `Sale de su escondite: es un {especie}.` para un macho y `Sale de su escondite: es una {especie}.` para una hembra.
  - La carta del alcalde, por cada recluta que se nombró solo: `Tu {especie} ahora se llama {nombre}. Se puso el nombre solo.` (pierde «, y se lo puedes cambiar una vez»). Y después de esas líneas, una más: con una placa, `Te dejé una placa con nombre en tu mochila, por si le quieres cambiar el nombre.`; con varias, `Te dejé {n} placas con nombre en tu mochila, por si les quieres cambiar el nombre.`
  - Se van con sus pantallas: todas las frases de la Incubadora (`🥚 Tu plantel`, `🥚 Incubadora`, «Sacar», «Aquí esperan…», «Caben {n} gachamones.», «Para eso tienes que estar en la incubadora.») y el aviso del Refugio (`El refugio cerró. Ahora cada quien vive en su departamento.`). La línea de la carta sobre los tickets del refugio **se queda**: habla del pasado y es cierta.

## Review Focus

1. **Quien estaba donde ya no hay nada**: una cuenta con `refugio` o `incubadora` guardado como lugar, y otra con la página abierta en la Incubadora: el estado, el mapa, el departamento, la Tienda y la primera aventura funcionan y nadie queda atrapado; pedir a mano las rutas de la Incubadora contesta «Eso no existe.» sin reventar.
2. **Lo que la Incubadora cubría sin que se notara**: cambiar de activo con un id que no existe, de otra persona o fuera de rango; el activo muerto de antes; ponerle nombre por `gachamon_id`: siguen probados en otro sitio, y «Salir con…» desde el departamento hace todo lo que hacía «Sacar».
3. **El mapa con siete lugares**: caminar entre todos (también desde y hacia donde colgaban los dos que se van), el botón de volver, el lector de pantalla, y «Tu departamento» en la etiqueta del mapa y en la cabecera de la pieza a 390 px (que no se corte ni empuje los saldos).
4. **Las placas del día del cambio**: nadie con reclutas, uno, varios; un recluta muerto que se nombró solo (no cuenta); una especie fuera del catálogo; correr el arranque dos veces; quien empieza después del cambio (ninguna placa); que la placa de regalo funcione como una comprada; y que monedas y gemas de todos queden como sin este plan.
5. **Sin gachamon por la Tienda**: la nota en objetos y cosméticos y no en muebles; comprar un mueble sigue funcionando; al ganar al primero la nota desaparece; con gachamon nunca se ve.

---

### Task 1: Las pruebas que vivían con la Incubadora sin ser suyas

Antes de borrar nada, lo que `tests/test_web_incubadora.py` prueba y **no** es de la Incubadora se muda. Sólo pruebas: ningún código de producción cambia.

**Files:**
- Modify: `tests/test_web_departamento.py`, `tests/test_web_nacer.py`, `tests/test_camas.py`
- (No se borra todavía `tests/test_web_incubadora.py`: lo hace la Task 2.)

**Interfaces:**
- Produces: `tests/test_camas.py` deja de importar nada de `test_web_incubadora` (su propio `ir`, o el de `tests/ayudas_web.py`) y cuenta las camas por lo que dice `GET /departamento` (`camas`, `gachamones`, `cabe_otro`) en vez de por `maximo` de `GET /incubadora`.

- [ ] **Step 1: cambiar de activo, por el departamento.** En `tests/test_web_departamento.py`, gemelas de las pruebas de `POST /incubadora/sacar` que no tienen pareja en `POST /departamento/salir`: un `gachamon_id` que no existe, de otra persona, fuera del rango de un entero de SQLite, y el caso del activo muerto de antes (el inventario, sección B, dice cuáles son y sus líneas). Mismas aserciones que las originales, sobre la ruta del departamento.
- [ ] **Step 2: ponerle nombre por `gachamon_id`.** A `tests/test_web_nacer.py`, las pruebas de `POST /bautizar` con `gachamon_id` y la del remiendo, tal cual.
- [ ] **Step 3: `tests/test_camas.py`** con su propio `ir` y la cuenta por el departamento.
- [ ] **Step 4:** corre las pruebas tocadas y la suite entera: todo pasa. Comprueba con una mutación en una copia fuera del repo que las gemelas del Step 1 muerden (por ejemplo, que `departamento/salir` acepte el id de otra persona). **Commit** — `test(web): lo que la incubadora probaba de paso, en el departamento y en el nombre`.

### Task 2: La Incubadora se va

**Files:**
- Delete: `web/incubadora.py`, `web/salir.py`, `web/static/js/incubadora.js`, `tests/test_web_incubadora.py`
- Modify: `web/app.py` (su router), `web/departamento.py` (recibe `dicho_de_salir`), `web/pueblo.py` (`OFRECE`), `web/static/js/pantallas.js`, `principal.js`, `lugar.js`, `web/static/estilo.css`, y sus comentarios en `articulos.js`
- Test: `tests/test_pueblo.py`, `tests/test_web_cliente.py`, `tests/test_web_minimos.py`, `tests/test_web_app.py`, `tests/test_web_lugar.py`, `tests/js/pantallas.test.mjs`, `tests/js/lugar.test.mjs`

**Interfaces:**
- Consumes: de la Task 1, que nada dependa ya de `tests/test_web_incubadora.py`.
- Produces: no existe la vista `'incubadora'`, ni `ofreceLaIncubadora`, ni las rutas `GET /incubadora` y `POST /incubadora/sacar` (contestan el 404 de siempre, «Eso no existe.»). `web/departamento.py` tiene dentro lo que decía `web/salir.py`, con la misma frase. El lugar `incubadora` sigue en el mapa hasta la Task 3, sin ofrecer nada.

- [ ] **Step 1: las pruebas, primero.** `GET /gachamon/api/incubadora` y `POST …/incubadora/sacar` contestan 404; ningún lugar ofrece `incubadora` (`tests/test_pueblo.py`); en el cliente, `siguiente` nunca devuelve `'incubadora'` y la pantalla de un lugar no tiene el botón «Tu plantel» (`tests/js/pantallas.test.mjs`, `tests/js/lugar.test.mjs`). Córrelas: fallan.
- [ ] **Step 2: el servidor.** Borra el módulo y su router; `dicho_de_salir` pasa a `web/departamento.py` y `web/salir.py` desaparece; `OFRECE` pierde `incubadora`. `nacer.bautizar_a`, `POST /bautizar` con `gachamon_id`, `economia.cambiar_de_activo`, `db.activa_al_dia` y `db.plantel_al_dia` **se quedan**.
- [ ] **Step 3: el cliente.** Borra `incubadora.js` y su entrada en `principal.js`; de `pantallas.js`, `ofreceLaIncubadora` y su rama en `siguiente`; de `lugar.js`, el botón «Tu plantel»; de `estilo.css`, las reglas que sólo usaba esa pantalla (el inventario, sección B, las lista: comprueba con `git grep` que ninguna otra pantalla usa cada clase antes de borrarla).
- [ ] **Step 4: las pruebas que la nombraban.** Borra `tests/test_web_incubadora.py`; en `tests/test_web_cliente.py`, las pruebas que eran sólo de `incubadora.js` se van y las listas de archivos pierden ese nombre (sin quitar vigilancia a ningún otro); en `tests/test_web_minimos.py` salen del recorrido las tres peticiones de la Incubadora (el resto del recorrido, intacto); la guarda de lecturas crudas de `tests/test_web_app.py` se pone al día si nombraba ese módulo. El informe lista cada prueba borrada con su porqué.
- [ ] **Step 5:** la suite entera de Python y `node --test tests/js/*.test.mjs`: todo pasa.
- [ ] **Step 6: mirarlo.** Con el arnés: la pantalla de un lugar (la Tienda) con gachamon, en 390 × 664 y en 1280, sin el botón «Tu plantel» y sin hueco raro donde estaba; y tu departamento, donde «Salir con…» cambia quién sale contigo.
- [ ] **Step 7: commit** — `feat(web): la incubadora se va: con quién sales se elige en tu departamento`.

### Task 3: El pueblo con siete lugares, y «Tu departamento»

**Files:**
- Modify: `web/static/datos/pueblo.json`, `web/pueblo.py` (`aviso`), `globos.py`, `web/arte.py`, `web/tienda.py` (la frase de comprar un mueble), `web/static/js/aventura.js` (el último botón), comentarios caducados (`mapa.js`, `lugar.js`), `docs/arte/contrato.md`, `web/static/arte/…` y `web/static/datos/arte.json` (generados)
- Delete: `web/static/arte/pueblo/lugares/refugio.png`, `…/incubadora.png`, `web/static/arte/escenas/refugio.png`, `…/incubadora.png`, `…/casa.png`; `tests/test_web_refugio.py`
- Test: `tests/test_pueblo.py`, `tests/test_web_lugar.py`, `tests/test_globos.py`, `tests/test_arte.py`, `tests/test_arte_pieza.py`, `tests/test_web_tienda.py`, `tests/js/pueblo.test.mjs`, `tests/js/mapa.test.mjs`, `tests/js/aventura.test.mjs`, `tests/js/tienda.test.mjs`, `tests/js/arte.test.mjs`, `tests/js/departamento.test.mjs`

**Interfaces:**
- Produces: `pueblo.json` con siete lugares (`casa` el primero), sin los nodos `refugio` e `incubadora` ni sus dos aristas; el lugar `casa` con `nombre` `Tu departamento` y `hacia` `a tu departamento`. `pueblo.aviso` sin la rama del refugio. `globos.DEL_LUGAR` y `PROPIAS_DEL_LUGAR` con las mismas claves que el pueblo. El contrato del arte: escenas sólo de los lugares cuya pantalla es la del lugar (la de `casa` sale), 270 piezas.

- [ ] **Step 1: las pruebas del pueblo.** `tests/test_pueblo.py`: son siete, cuatro abiertos hoy menos dos (la tabla de partes y nombres al día), `casa` se llama `Tu departamento` y va `a tu departamento`, el grafo sigue conectado, y `aviso` ya no dice nada del refugio. `tests/test_web_lugar.py`: el estado de quien tiene guardado `refugio` o `incubadora` como lugar dice `casa`, y `GET /departamento` le contesta (prueba nueva, con esas dos claves escritas en la fila). `tests/js/pueblo.test.mjs`: los casos que usaban `refugio` como partida o destino, con lugares que existan (el inventario, sección A, propone cuáles) y la caminata más larga sin cambiar. Córrelas: fallan.
- [ ] **Step 2: los datos y el aviso.** `pueblo.json` y `web/pueblo.py`.
- [ ] **Step 3: los globos.** Fuera las claves `refugio` e `incubadora` de los dos diccionarios; `Aquí se oye el silencio del edificio.` en lugar de la de las casas; el comentario caducado. Sus pruebas al día (`tests/test_globos.py`).
- [ ] **Step 4: las tres frases.** La Tienda (`web/tienda.py`), el botón de la aventura (`aventura.js`) y el «hacia» (ya en el JSON), con sus pruebas, letra por letra. Los datos de prueba del cliente que decían «Tu casa» como nombre del lugar (`tests/js/departamento.test.mjs`, `mapa.test.mjs`, `aventura.test.mjs`, `pantallas.test.mjs`) pasan a «Tu departamento».
- [ ] **Step 5: el arte.** La regla de las escenas en `web/arte.py`; borra los cinco archivos que sobran y `pueblo/fondo.png`, y corre `./venv/bin/python -m herramientas.rellenos` **sin** `--todo` (rehace el fondo y `arte.json`; ningún otro dibujo cambia: compruébalo con `git status`). Las cuentas fijas de las pruebas del arte y `docs/arte/contrato.md` (el total, los siete lugares, las seis escenas), al día.
- [ ] **Step 6:** borra `tests/test_web_refugio.py` (lo que probaba ya no existe; dilo en el informe). La suite entera y las de JavaScript: todo pasa.
- [ ] **Step 7: mirarlo.** Con el arnés, en 390 × 664 y en 1280: el mapa con sus siete lugares y sin caminos a ninguna parte, la etiqueta «Tu departamento» entera, el botón «Volver a tu departamento», y la cabecera «📍 Tu departamento» de la pieza junto a los saldos sin cortarse. Si algo no cabe, para y dilo con la captura: no cambies tamaños por tu cuenta.
- [ ] **Step 8: commits** — `feat(web): el pueblo pierde el refugio y la incubadora, y tu casa es tu departamento` y `feat(arte): el contrato sin los dos lugares ni la escena de la casa`.

### Task 4: La nota de la Tienda y la frase del encuentro

**Files:**
- Modify: `web/tienda.py`, `web/static/js/tienda.js`, `web/aventura.py`
- Test: `tests/test_web_tienda.py`, `tests/js/tienda.test.mjs`, `tests/test_web_aventura.py`, `tests/js/aventura.test.mjs`

**Interfaces:**
- Produces: `GET /tienda` gana `"aviso"`: la nota si la persona no tiene ningún gachamon vivo, `None` si tiene. La frase vive en `web/tienda.py`. El encuentro (`POST /aventura/primera`) dice `es un {especie}` o `es una {especie}` según el género del que nació, con `especies.concordar`.

- [ ] **Step 1: las pruebas.** Tienda: sin gachamon, `aviso` es la frase, letra por letra; con gachamon, `None`; en el cliente, la nota se ve arriba de la lista en las pestañas de objetos y de cosméticos y **no** en la de muebles, se anuncia como las demás notas, y desaparece cuando llega un catálogo sin ella. Aventura: con un macho, `Sale de su escondite: es un Octopul.`; con una hembra, `…es una Octopul.`; ninguna marca de género sin resolver en lo que sale. Córrelas: fallan.
- [ ] **Step 2:** la nota en `web/tienda.py` y en `tienda.js`; la frase del encuentro en `web/aventura.py`.
- [ ] **Step 3:** las pruebas tocadas, la suite entera y las de JavaScript: todo pasa (hay un barrido de textos en `tests/test_textos.py`: si salta, para y dilo).
- [ ] **Step 4: mirarlo.** Con el arnés, una cuenta sin gachamon en la Tienda, en 390 × 664 y en 1280: la nota en objetos y en cosméticos, no en muebles, sin empujar las pestañas fuera de la vista; y el encuentro de la primera aventura con su frase.
- [ ] **Step 5: commit** — `feat(web): la tienda avisa de que sin gachamon sólo se compran muebles, y el encuentro dice un o una`.

### Task 5: Las placas del día del cambio

**Files:**
- Modify: `economia.py` (`_mudar_a`, `ResumenDelCambio`, el aviso del arranque), `web/carta.py` (`lineas_de`)
- Test: `tests/test_dia_del_cambio.py`, `tests/test_web_carta.py` (o donde estén las de la carta)

**Interfaces:**
- Produces: dentro de la transacción del cambio de cada persona, **una placa con nombre** (`objetos`, clave `placa`) en su mochila por cada gachamon **vivo** con `se_nombro_solo`, puesta con la misma función que usa el cambio para lo demás que deja en la mochila. La carta guarda `"placas": <cuántas>`. `ResumenDelCambio` gana `placas: int = 0` (al final) y el aviso del arranque lo dice. `lineas_de` escribe las frases de «Frases nuevas»: la línea de cada recluta sin «, y se lo puedes cambiar una vez», y después de ellas la de las placas, en singular o en plural, **según `placas` de la carta** (no según cuántas líneas de recluta salieron); una carta sin esa clave no dice nada de placas.

- [ ] **Step 1: las pruebas del cambio** (`tests/test_dia_del_cambio.py`, con sus ayudas): una persona con tres reclutas vivos que se nombraron solos recibe tres placas y su carta guarda `placas == 3`; con uno, una; sin ninguno, ninguna y la mochila no cambia; un recluta **muerto** que se nombró solo no cuenta; una especie fuera del catálogo cuenta para la placa aunque su línea no salga; correr el arranque otra vez no deja más placas; quien llega después del cambio no recibe ninguna; el resumen suma las de todos; y **monedas y gemas de cada quien son las mismas que sin esta tarea** (compara con lo que dejaba el cambio antes: las pruebas que ya fijan saldos no se tocan).
- [ ] **Step 2: las pruebas de la carta**: las frases, letra por letra: un recluta, `Tu Octopul ahora se llama Rulo. Se puso el nombre solo.` y `Te dejé una placa con nombre en tu mochila, por si le quieres cambiar el nombre.`; tres, las tres líneas y `Te dejé 3 placas con nombre en tu mochila, por si les quieres cambiar el nombre.`; sin reclutas, ninguna de las dos; el orden (después de las de los reclutas y antes de «Y dos cosas más…»). Las pruebas de hoy que fijan «, y se lo puedes cambiar una vez» se ponen al día (lístalas).
- [ ] **Step 3:** córrelas: fallan.
- [ ] **Step 4:** las placas en `_mudar_a`, el campo del resumen y su aviso, y `lineas_de`.
- [ ] **Step 5: de punta a punta** (prueba nueva por las rutas): tras el cambio, quien recibió una placa la ve en su mochila y al usarla le cambia el nombre a su recluta (el que sale con él) como una comprada.
- [ ] **Step 6:** la suite entera: todo pasa. Mutaciones en una copia fuera del repo: que cuente a los muertos; que la deje dos veces al repetir el arranque; que la carta cuente líneas en vez de `placas`.
- [ ] **Step 7: commit** — `feat(economia): el día del cambio regala una placa por cada recluta que se puso el nombre solo`.

### Task 6: Los documentos y la lista de publicar

**Files:**
- Modify: `README.md`, `AGENTS.md`, `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`, `docs/superpowers/specs/2026-11-12-gachamon-web-parte-a-design.md` (sólo una nota arriba)

- [ ] **Step 1: `README.md`.** «La web»: siete lugares, sin Incubadora ni Refugio, «Tu departamento» (y donde otras secciones decían «tu casa» como nombre de la pantalla); la tabla de «Cómo está montado» con los módulos que faltan y con `web/` y su cliente contados como son (un router y un módulo de JavaScript por pantalla); «Tests» con las pruebas de JavaScript y sin la cuenta de combinaciones de las fichas de texto. El inventario, sección G, lo lista sección por sección: compruébalo contra el código antes de escribir.
- [ ] **Step 2: `AGENTS.md`.** El invariante que nombra la Incubadora (se cambia de activo en tu departamento); el del nombre de los reclutas (la regla de cambiarlo una vez sigue en el servidor y ninguna pantalla la ofrece; en la página se cambia con la placa); lo nuevo del día del cambio (regala las placas). Sin alargar.
- [ ] **Step 3: los pendientes.** Título al día (es el registro de todos los planes). Sección nueva «Salió al ejecutar el rework 8» (lo que decidió el dueño, las frases que aprobó, lo que el plan propuso y él aprobó, lo que se decidió al construir, lo que queda). En las secciones anteriores, marcar como hecho lo que este plan cierra y como cerradas las decisiones que ya se tomaron (el inventario, secciones G, H1 e I, da las líneas), y los dos menores que el rework 7 dejó para aquí. **Y una sección propia, «Para publicar»: la lista única, en orden** (antes, el día, y si hay que volver atrás), juntando lo de todos los planes sin repetir: el inventario, sección H2, la trae armada; contrasta cada punto con el código y con la sección de donde sale, y añade lo de este plan (quien tenga la página abierta en la Incubadora; las placas en la carta y en el aviso del arranque; siete lugares).
- [ ] **Step 4:** una nota arriba del diseño de la parte A que remita al diseño del rework (describe nueve lugares, casas, Refugio e Incubadora, y ya no es así). Nada más de ese documento.
- [ ] **Step 5:** sin SHAs, números de tarea, cantidades de pruebas ni ids; «aprobó» no es «decidió»; las fechas, las reales. La suite entera pasa. **Commit** — `docs: el pueblo de siete lugares, tu departamento y la lista para publicar`.
