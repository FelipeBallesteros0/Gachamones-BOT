# Rework 7 · Los muebles que se usan solos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que se puedan comprar y poner cuatro muebles nuevos —refrigerador, consola, ducha y pesas— que cuidan solos a todos los gachamones del departamento: los tres primeros no dejan que la comida, el ánimo o el aseo bajen de 40, y las pesas les dan un punto de entrenamiento de fuerza por día; y que en la pieza se vea a los gachamones acercarse a ellos de vez en cuando.

**Architecture:** El efecto no es una regla nueva sino el ritmo de siempre: `departamento.ritmo_de` ya es lo único que le dice a `sim.avanzar` cómo corre el tiempo en un departamento, así que el catálogo marca cada mueble con su uso, `ritmo_de` lo traduce en mínimos y en puntos por día dentro de `sim.Ritmo`, y `sim.avanzar` los aplica. `db.py` y `economia.py` no cambian: asentar antes de poner o guardar ya parte el tiempo donde toca. En el cliente, la pantalla del departamento se parte antes en módulos (sin cambiar nada de lo que se ve) y el paseo de los gachamones gana un destino: el lado de un mueble marcado por el servidor.

**Tech Stack:** Python 3.12, FastAPI, SQLite síncrono, JavaScript sin framework ni compilación, pytest y `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-14-gachamon-rework-1-departamento-design.md`, secciones 4.2, 4.3, **4.4** (reescrita con este plan) y 5.1. Inventario del código afectado: `.superpowers/sdd/2026-11-18-rework-7-reconocimiento/inventario.md` (con archivo y línea; léelo antes de cada tarea).

**Dónde encaja.** Es el séptimo plan del rediseño. Lo anterior ya está en la rama: nadie muere, el tiempo corre para todos, la vivienda por casillas con su día del cambio, el departamento en pantalla con su puerta y su modo construcción, y la partida sin gachamon. Queda después el plan 8 (el pueblo sin Refugio ni Incubadora y los documentos).

**Lo que no entra.** Decir junto a una barra que un mueble la sostiene, o bajo la pieza (Felipe: sólo una línea en la Tienda). Cambiar los globos, los colores de las barras o cualquier umbral que no sea el mínimo nuevo. Una acción propia al tocar estos muebles. Dibujos nuevos de un gachamon usando un mueble, o que se dé vuelta. El arte de verdad de los cuatro (llega del dibujante; aquí, relleno). Sacar el «transporte» (`mandar`, `enviar`, `releer`) de `departamento.js`: queda anotado. El día del cambio. Discord.

## Global Constraints

- Nada se sube, se fusiona ni se despliega: todo queda en la rama local `rework/1-departamento`.
- Los módulos de juego no importan `discord`; `web/` no importa `discord` ni nada que lo importe; `db.py` no importa `economia.py`; `departamento.py` y `simulacion.py` son puros; `casillas.js`, `proyeccion.js` y el nuevo `caminantes.js` son puros (ni DOM, ni red, ni reloj: el azar y el tiempo entran por parámetro).
- **Este plan no cambia `db.py` ni `economia.py`** (sí sus pruebas). Si una tarea cree que hace falta, se detiene y lo dice.
- **El dinero**: este plan no da ni quita monedas ni gemas a nadie. Los cuatro muebles se compran por el camino de siempre. Ni los mínimos ni las pesas dan experiencia, monedas, medallas, marcador ni crecimiento: no pasan por `aplicar_accion`, `ejecutar_cuidado` ni `_registrar_recompensa`.
- **El día del cambio no se toca**, ni `globos.py`, ni `cuidados.js` (`nivelDeBarra`), ni `proyeccion.queSeUsa` / `tocarViviendo`: ningún mueble nuevo tiene acción propia.
- El cliente: sin frameworks ni compilación, sin `innerHTML`, sin direcciones `http`, módulos con rutas relativas terminadas en `.js`. **Ninguna clave ni precio del catálogo escritos en el JavaScript**: el cliente reconoce estos muebles por la marca `uso` que manda el servidor. `tests/test_web_cliente.py` vigila listas de archivos escritas a mano (claves, `'puerta'`, los números 15 y 85, `aria-disabled`, «❤»): **cada módulo nuevo de la pieza se añade a esas listas**, y ninguna aserción existente se quita ni se afloja.
- Accesibilidad, como en el resto de la página: con movimiento reducido nada se mueve solo; lo que no se puede usar lleva `aria-disabled`; el foco no se pierde.
- A quien juega se le dice «comida», «ánimo», «aseo», «monedas» y «gemas». Las frases nuevas son **sólo** las de este plan, letra por letra.
- Sin dependencias nuevas. Nunca se abre `tamagotchi.db` ni `.env`; las pruebas usan bases temporales, ids sintéticos y reloj y azar inyectados. El repo es público: ni SHAs, ni ids, ni cantidades de pruebas en los documentos.
- Antes de editar un símbolo, GitNexus `impact` (lo corre el controlador; `simulacion.avanzar` y `departamento.ritmo_de` salen **CRITICAL** porque todo el paso del tiempo pasa por ellos: se amplían sólo con campos que por defecto dejan todo como hoy). Cada commit: `./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "…"`, con la línea de coautoría. Las pruebas de JavaScript: `node --test tests/js/*.test.mjs`.
- **Lo que decidió Felipe** (2026-11-14 en el diseño, y el 2026-11-18 eligiendo entre opciones que se le propusieron):
  1. Los cuatro muebles y su idea: refrigerador para la comida, consola para el ánimo, ducha para el aseo y pesas para entrenar solos (diseño).
  2. **El mínimo es 40**, no 30: por debajo de 40 el gachamon pide, y con 30 pediría siempre lo que el mueble le sostiene («Subir el suelo a 40», 2026-11-18).
  3. **Se acepta que quiten crecimiento**: con la ducha y el refrigerador dejan de salir los crecimientos de cuidar a un gachamon que está muy mal («Sí, es el precio de la comodidad», 2026-11-18). Sin regla nueva.
  4. **Lo que hacen se dice en una línea de la Tienda**, bajo el nombre de cada uno; nada más en este plan (2026-11-18).
  5. **Las pesas dan 1 punto por día** y gachamon, como decía el diseño (2026-11-18).
  6. **«No baja de 40» vale siempre**, también contra lo que gastan los cuidados: con el mueble puesto, un cuidado que dejaría la barra por debajo (entrenar o jugar gastan comida y ánimo) la deja en 40 («Sí, vale siempre», 2026-11-18).
- **Lo que este plan decide en nombre de Felipe** (se le enseñó con el plan y lo aprobó el 2026-11-18: «Apruebo, ejecútalo»):
  1. Si al poner el mueble la barra estaba por debajo de 40, **sube a 40 en ese momento** (como decía el diseño con su 30).
  2. **El punto de las pesas llega al pasar la medianoche UTC** (el mismo día de los topes diarios). Guardarlas y volver a ponerlas no da puntos de más; la medianoche que pasan guardadas no cuenta.
  3. Cuestan 300 monedas y suman 3 de comodidad cada uno; tener dos no hace más; no hay que llenarlos ni cuestan por uso (diseño). En la Tienda van tras la cama sencilla, en este orden: Refrigerador, Consola, Ducha, Pesas.
  4. **El adorno**: uno de cada tres paseos, un gachamon que está quieto camina hasta el lado de uno de esos muebles y se queda ahí unos segundos. Cualquiera, al azar; sin ícono ni dibujo nuevo. Es sólo de la pantalla: no se guarda ni cambia ninguna regla.
  5. El arte de los cuatro es de relleno (el cajón con sus tres letras), como el de todos los muebles hoy.
  6. `departamento.js` se parte en módulos sin cambiar nada de lo que se ve ni de lo que se manda.
- **Frases nuevas** (Felipe las aprobó el 2026-11-18: «Apruebo todas»; van tal cual):
  - Los nombres: `Refrigerador`, `Consola`, `Ducha`, `Pesas`.
  - La línea de la Tienda, bajo el nombre: `Con él puesto, la comida de tus gachamones no baja de 40.` · `Con ella puesta, el ánimo de tus gachamones no baja de 40.` · `Con ella puesta, el aseo de tus gachamones no baja de 40.` · `Con ellas puestas, tus gachamones entrenan la fuerza solos, un poco cada día.`

## Review Focus

1. **Poner, guardar y mover a medias del tiempo**: un gachamon con la comida en 10 al poner el refrigerador (40 en toda pantalla, en esa misma respuesta); el tramo de antes de ponerlo corre sin mínimo y el de después de guardarlo también; con dos puestos, guardar uno no quita nada; mover o girar el mueble no cambia nada; un mueble guardado no hace nada.
2. **Cuidar en el mínimo**: entrenar o jugar con la barra en 40 y el mueble puesto: la respuesta de ese cuidado, el estado y la lectura siguiente dicen 40, nunca un valor por debajo que luego «rebota». Y ninguna lectura de barras se salta `db.avanzar`.
3. **Las pesas y el calendario**: ponerlas un minuto antes de la medianoche UTC; diez días sin abrir la página (diez puntos, se lea las veces que se lea); guardar y poner el mismo día; guardadas durante una medianoche; un gachamon que nace con las pesas ya puestas; la estadística visible en su techo (`sim.MAXIMO_STAT`). Nunca más de un punto por medianoche, y nada de experiencia, monedas, medallas ni marcador.
4. **Quien no tiene ninguno de los cuatro no nota nada**: sus barras bajan igual, sus paseos llaman al azar las mismas veces, su Tienda sólo gana cuatro filas y sus pruebas de hoy pasan sin tocarlas.
5. **El adorno en una pieza apretada**: el mueble arrinconado o rodeado (sin casilla libre al lado), todos los gachamones ocupados, uno elegido con su menú abierto, algo en la mano, el modo construcción, movimiento reducido, la pestaña oculta, salir de la pantalla a mitad del camino, y que el mueble se guarde mientras alguien camina hacia él.

---

### Task 1: Los caminantes, a su módulo

Primer paso de partir `web/static/js/departamento.js` (más de 1800 líneas): las cuentas de quién está en qué casilla y hacia dónde camina salen a un módulo puro. **No cambia ningún comportamiento.**

**Files:**
- Create: `web/static/js/caminantes.js`, `tests/js/caminantes.test.mjs`
- Modify: `web/static/js/departamento.js`, `tests/test_web_cliente.py` (sólo **añadir** `caminantes.js` a las listas de archivos vigilados)

**Interfaces:**
- Produces (exportadas por `caminantes.js`, todo por parámetro; el inventario, sección F, dice de qué líneas sale cada una):
  - `caminanteEn(casilla)`, `reubicar(depto, quien, ocupado, puerta)`, `reubicarte(depto, tu, ocupado, puerta, entrada)`, `repartir(depto, tu, enPiezaAntes)` → `{ tu, enPieza }`
  - `avanzar(quien, dt)`, `rutaHasta(depto, quien, destino, puerta)` → ruta o `null`
  - `noSePisanConGente(depto, tu, enPieza, salvo)`, `casillasDelGachamon(depto, quien)`
  - `unPaseo(depto, plantel, enPieza, tu, elegidoG, azar)` → `{ id, ruta } | null`, con **las mismas dos llamadas a `azar`** que hoy hace `darUnPaseo` (quién y hacia dónde), en el mismo orden.
- Si al extraer hace falta otro parámetro, se añade y se dice en el informe: la Task 6 consume `unPaseo` y `noSePisanConGente`.

- [ ] **Step 1: la línea base.** `node --test tests/js/*.test.mjs` y `./venv/bin/python -m pytest tests/test_web_cliente.py tests/test_web_js.py -q`: anota los totales.
- [ ] **Step 2: las pruebas del módulo, primero.** En `tests/js/caminantes.test.mjs`, una prueba por función exportada con departamentos pequeños escritos a mano (3 × 3 con una cama y la puerta): `repartir` deja a cada gachamon en una casilla libre distinta y a `tu` en la entrada; `rutaHasta` rodea un mueble y da `null` sin camino; `noSePisanConGente` cuenta a `tu` y a los demás y deja fuera a `salvo`; `avanzar` no pasa del final de la ruta; `unPaseo` devuelve un paso a una vecina libre, nunca al elegido, y llama a `azar` exactamente dos veces; sin nadie quieto, `null`. Córrelas: fallan porque el módulo no existe.
- [ ] **Step 3: extraer.** Mueve las funciones a `caminantes.js` y haz que `departamento.js` las llame. Se quedan en `departamento.js` el estado (`tu`, `enPieza`, `saltos`, `andado`, `saliendo`), el bucle de cuadros (`pedirCuadro`, `cuadro`), `programarUnPaseo` (la llamada de «cuándo»), `salirPorLaPuerta`, `salirSiLlegaste` y `saltar`. La parte del comentario de cabecera que habla de caminar se va con el módulo.
- [ ] **Step 4: verde sin tocar aserciones.** `node --test tests/js/*.test.mjs` (los de hoy más los nuevos) y las dos pruebas de Python: todo pasa; en `tests/test_web_cliente.py` el único cambio es `caminantes.js` añadido a las listas de la sección «ni claves, ni la puerta, ni 15 ni 85».
- [ ] **Step 5: commit** — `refactor(web): los caminantes de la pieza, a su módulo`.

### Task 2: El menú, la bandeja y el panel de ampliar, a sus módulos

Segundo paso de la partición: tres fábricas con DOM, al estilo de `plantel.js` y `lista.js` (arman sus nodos, reciben callbacks, no hablan con el servidor ni deciden qué está elegido). **No cambia ningún comportamiento.**

**Files:**
- Create: `web/static/js/menu.js`, `web/static/js/bandeja.js`, `web/static/js/ampliar.js`
- Modify: `web/static/js/departamento.js`, `tests/test_web_cliente.py` (sólo **añadir** los tres a las listas vigiladas, también a la de `aria-disabled` y a la de «❤»)

**Interfaces:**
- Produces:
  - `menu.js`: `menuDeLaPieza({ lienzo, mover, girar, guardar, moverGachamon, acariciar, soltarElegido })` → `{ nodo, pintar({ puesto | gachamon, caja }), cerrar(), contiene(nodo) }`. Conserva la clase `.menu-de-la-pieza`.
  - `bandeja.js`: `bandejaDeGuardados({ tomar, focoDeReserva })` → `{ nodo, pintar(guardados, { enCamino }), marcar(tipoEnLaMano) }`, con `porTipo` dentro.
  - `ampliar.js`: `panelDeAmpliar({ alConfirmar(eje, boton), alVolver })` → el panel con su pregunta y su foco.
- **Se quedan en `departamento.js`** (las pruebas de `tests/test_web_cliente.py` leen su texto): `eventosDeAmpliar`, `eventoDeAmpliar` y `ampliar`; cada llamada a `conReintentos` con su `evento_id`; el `import` de `./cuidados.js`; `requestAnimationFrame`, `cancelAnimationFrame`, `prefers-reduced-motion`, `visibilitychange` y `aria-hidden`; qué está elegido, el modo y `tomarDeLaBandeja`.

- [ ] **Step 1: `menu.js`.** Extrae, corre `node --test tests/js/departamento.test.mjs` y las pruebas de Python del cliente: verde sin tocar aserciones. Commit — `refactor(web): el menú de la pieza, a su módulo`.
- [ ] **Step 2: `bandeja.js`.** Igual. Commit — `refactor(web): la bandeja de guardados, a su módulo`.
- [ ] **Step 3: `ampliar.js`.** Igual; comprueba que `test_web_cliente` sigue encontrando el evento de ampliar creado en `departamento.js`. Commit — `refactor(web): el panel de ampliar, a su módulo`.
- [ ] **Step 4: mirarlo.** Con el arnés (la carpeta del scratchpad que dé el controlador), una captura en 390 × 664 y otra en 1280 del departamento con el menú de un mueble abierto, la bandeja en «Construir» y la pregunta de ampliar: iguales a como se veían antes.

### Task 3: Los mínimos y las pesas en el paso del tiempo

**Files:**
- Modify: `simulacion.py` (`Ritmo`, `avanzar`)
- Test: `tests/test_simulacion.py`

**Interfaces:**
- Produces: `sim.Ritmo` gana `suelo_de_animo: float = 0.0`, `suelo_de_limpieza: float = 0.0` y `fuerza_por_dia: int = 0` (al final, tras `suelo_de_hambre`, que ya existe). `sim.Ritmo()` sigue siendo el de hoy.
- `sim.avanzar(criatura, ahora, ritmo)`, para una criatura viva:
  1. Una barra por debajo de su suelo **sube al suelo aunque no haya pasado tiempo** (`ahora <= actualizada_en`), sin tocar `actualizada_en`. Si nada cambia devuelve **el mismo objeto**, como hoy.
  2. Con tiempo: cada barra baja como hoy y no pasa de su suelo (`max(suelo, …)`); el castigo del ánimo por estar sucia se decide con el aseo **ya subido a su suelo**.
  3. `ent_fuerza` sube `ritmo.fuerza_por_dia` por cada medianoche UTC entre `actualizada_en` y `ahora` (`(ahora_utc.date() - antes_utc.date()).days`). Nada más cambia por las pesas: ni experiencia, ni nivel, ni tensiones.
  4. Una muerta no cambia.

- [ ] **Step 1: las pruebas.** En `tests/test_simulacion.py`:
  - `test_cada_suelo_frena_su_barra_y_no_las_otras`: tras un mes con `Ritmo(suelo_de_animo=40.0)`, el ánimo es `40.0` y la comida y el aseo `0.0`; lo mismo con cada uno de los tres.
  - `test_una_barra_bajo_su_suelo_sube_aunque_no_pase_el_tiempo`: con comida 10, ánimo 5 y aseo 0 y los tres suelos en 40, `avanzar(c, c.actualizada_en, ritmo)` da `(40.0, 40.0, 40.0)` con el mismo `actualizada_en`; repetirlo devuelve lo mismo; y `avanzar(c, c.actualizada_en)` sin suelos `is c`.
  - `test_con_el_suelo_del_aseo_el_animo_no_cae_como_sucio`: aseo guardado en 10, diez horas con `Ritmo(suelo_de_limpieza=40.0)`: el ánimo queda igual (`pytest.approx`) que el de una con el aseo en 100 y sin suelo.
  - `test_las_pesas_dan_un_punto_por_medianoche_utc`: con `Ritmo(fuerza_por_dia=1)` y `actualizada_en` a las 23:59 UTC, a las 00:01 del día siguiente `ent_fuerza` sube 1; de las 00:01 a las 23:59 del mismo día, 0; diez días después, 10; en dos tramos da lo mismo que en uno; sin pesas, 0.
  - `test_las_pesas_solo_tocan_el_entrenamiento_de_fuerza`: tras tres días, la criatura con `fuerza_por_dia=1` es igual a la de sin pesas salvo `ent_fuerza` (`replace(con, ent_fuerza=sin.ent_fuerza) == sin`).
  - `test_una_muerta_no_sube_ni_entrena`.
- [ ] **Step 2:** córrelas: fallan (los campos no existen).
- [ ] **Step 3:** amplía `Ritmo` y `avanzar`. Pon al día el docstring de `Ritmo` (ya no «era de la intemperie»: lo ponen los muebles del departamento).
- [ ] **Step 4:** `./venv/bin/python -m pytest tests/test_simulacion.py -q` y después la suite entera: todo pasa sin tocar ninguna prueba existente.
- [ ] **Step 5: commit** — `feat(sim): mínimos para el ánimo y el aseo y un punto de fuerza por día en el ritmo`.

### Task 4: Los cuatro muebles: el catálogo, su ritmo y su arte

**Files:**
- Modify: `departamento.py` (`Mueble`, `MUEBLES`, `ritmo_de`), `web/departamento.py` (`vista`), `web/static/arte/…` y `web/static/datos/arte.json` (generados), `docs/arte/contrato.md`
- Test: `tests/test_departamento.py`, `tests/test_economia_departamento.py`, `tests/test_web_departamento.py`, `tests/test_arte.py`, `tests/test_arte_pieza.py`

**Interfaces:**
- Consumes: de la Task 3, `sim.Ritmo(suelo_de_hambre, suelo_de_animo, suelo_de_limpieza, fuerza_por_dia)`.
- Produces, en `departamento.py`:
  - `COMIDA = "comida"`, `ANIMO = "animo"`, `ASEO = "aseo"`, `FUERZA = "fuerza"`; `MINIMO_SOSTENIDO = 40.0`; `FUERZA_POR_DIA = 1`.
  - `Mueble.uso: str | None = None` (el último campo).
  - Cuatro muebles **tras `cama_sencilla` y antes de la puerta**, en este orden: `Mueble("refrigerador", "Refrigerador", "🧊", 300, 3, uso=COMIDA)`, `Mueble("consola", "Consola", "🎮", 300, 3, uso=ANIMO)`, `Mueble("ducha", "Ducha", "🚿", 300, 3, uso=ASEO)`, `Mueble("pesas", "Pesas", "🏋️", 300, 3, uso=FUERZA)`.
  - `ritmo_de(depto)`: el alivio del ánimo de hoy, más `MINIMO_SOSTENIDO` en el suelo de cada barra cuyo mueble esté **puesto** (por tipo: dos no hacen más; uno guardado no cuenta; una clave fuera del catálogo se ignora) y `fuerza_por_dia=FUERZA_POR_DIA` con unas pesas puestas.
- Produces, en `web/departamento.vista`: cada elemento de `puestos` gana `"uso": mueble.uso` (`None` en los demás). La Task 6 lo consume.

- [ ] **Step 1: las pruebas del catálogo y del ritmo** (`tests/test_departamento.py`): la lista de claves gana las cuatro (la prueba del catálogo y la tabla `FORMAS`, las cuatro de 1 × 1 y `dep.BULTO`); cada una con su nombre, 300 y 3 y su `uso`; ningún otro mueble tiene `uso`; `a_la_venta()` termina en `cama_sencilla, refrigerador, consola, ducha, pesas`. Y `test_el_ritmo_lleva_el_minimo_de_cada_mueble_puesto`: con el refrigerador puesto, `ritmo_de` es `sim.Ritmo(animo=<el alivio>, suelo_de_hambre=40.0)`; guardado, el ritmo de hoy; con dos, igual que con uno; con los cuatro, los tres suelos en 40.0 y `fuerza_por_dia == 1`; sin ninguno, exactamente el de hoy.
- [ ] **Step 2: las pruebas de las reglas** (`tests/test_economia_departamento.py`, con la base temporal y el reloj por parámetro, como las que ya hay):
  - `test_al_poner_el_refrigerador_la_comida_sube_al_minimo`: un gachamon guardado con la comida en 10; se pone el refrigerador una hora después; leído **con ese mismo instante** (`db.plantel_al_dia`), su comida es `40.0`, y su ánimo y su aseo bajaron esa hora como sin mueble.
  - `test_al_guardarlo_la_barra_vuelve_a_bajar_desde_el_minimo`: cien horas con él puesto → 40.0; se guarda; diez horas después la comida es menor que 40 y es la de diez horas de caída desde 40.
  - `test_con_dos_refrigeradores_guardar_uno_no_quita_el_minimo`.
  - `test_las_pesas_entrenan_a_todos_un_punto_por_dia`: dos gachamones, pesas puestas a las 12:00 UTC; tres días después cada uno tiene 3 puntos más de `ent_fuerza`.
  - `test_guardar_y_volver_a_poner_las_pesas_el_mismo_dia_no_da_puntos` y `test_la_medianoche_con_las_pesas_guardadas_no_cuenta`.
  - `test_los_muebles_que_se_usan_solos_no_mueven_el_dinero`: con los cuatro puestos y treinta días por delante, los saldos, las filas de `operaciones_economia`, la experiencia, el nivel y el marcador de cuidados son los de antes.
- [ ] **Step 3: las pruebas de la web** (`tests/test_web_departamento.py`): los `puestos` llevan `uso` (el del refrigerador, `"comida"`; el de una maceta, `None`); tras `POST /departamento/poner` del refrigerador con el gachamon hambriento, la comida es 40 en `departamento.plantel` **y** en `estado` de esa misma respuesta; y con el refrigerador puesto y la comida en 40, `POST` de entrenar contesta 40 en `gachamon.barras.comida` y en `estado`.
- [ ] **Step 4:** córrelas: fallan.
- [ ] **Step 5: el catálogo y el ritmo.** Añade las constantes, el campo, los cuatro muebles y `ritmo_de`; `"uso"` en `vista`.
- [ ] **Step 6: el arte.** `./venv/bin/python -m herramientas.rellenos` (escribe sólo lo que falta: un ícono y cuatro dibujos por mueble, y rehace `web/static/datos/arte.json`). Pon al día las cuentas fijas de `tests/test_arte.py` y `tests/test_arte_pieza.py` (el inventario, sección D, dice dónde están y cuánto pasan a valer) y `docs/arte/contrato.md` (el total, los íconos de muebles y la lista de claves). Comprueba que ningún archivo de arte existente cambió (`git status` sólo enseña archivos nuevos en `web/static/arte/`).
- [ ] **Step 7:** la suite entera de Python y `node --test tests/js/*.test.mjs`: todo pasa.
- [ ] **Step 8: commits** — `feat(departamento): refrigerador, consola, ducha y pesas, con su mínimo y su punto de fuerza` y `feat(arte): los rellenos de los cuatro muebles que se usan solos`.

### Task 5: La línea de la Tienda

**Files:**
- Modify: `web/tienda.py` (`_muebles`), `web/static/js/tienda.js` (`filaDeMueble`)
- Test: `tests/test_web_tienda.py`, `tests/js/tienda.test.mjs`

**Interfaces:**
- Consumes: de la Task 4, `Mueble.uso` y `dep.MINIMO_SOSTENIDO`.
- Produces: cada mueble de `GET /tienda` gana `"detalle"`: la frase de su uso o `None`. Las frases viven en `web/tienda.py`, una por uso, y el 40 sale de `dep.MINIMO_SOSTENIDO` (una prueba fija el texto entero).

- [ ] **Step 1: las pruebas.** En `tests/test_web_tienda.py`: los cuatro traen su frase, letra por letra (las de «Frases nuevas»), y los demás `None`. En `tests/js/tienda.test.mjs`: un mueble con `detalle` enseña esa línea **justo bajo el nombre y antes de** «Comodidad +3»; uno sin `detalle` se ve como hoy.
- [ ] **Step 2:** córrelas: fallan.
- [ ] **Step 3:** `"detalle"` en `_muebles`, y en `filaDeMueble` la línea (con la clase de las demás líneas de detalle) cuando viene.
- [ ] **Step 4:** las pruebas de la Tienda (Python y JavaScript) y la suite entera: todo pasa.
- [ ] **Step 5: mirarlo.** Con el arnés, la Tienda en 390 × 664 y en 1280, la pestaña de muebles con los cuatro: la línea no desborda ni empuja el botón del precio.
- [ ] **Step 6: commit** — `feat(web): la Tienda dice lo que hacen el refrigerador, la consola, la ducha y las pesas`.

### Task 6: Los gachamones se acercan a sus muebles

**Files:**
- Modify: `web/static/js/caminantes.js`, `web/static/js/departamento.js`
- Test: `tests/js/caminantes.test.mjs`, `tests/js/departamento.test.mjs`

**Interfaces:**
- Consumes: de la Task 1, `caminantes.js` (`unPaseo`, `noSePisanConGente`, `rutaHasta`); de la Task 4, `puesto.uso`.
- Produces: `caminantes.unPaseoAUnMueble(depto, plantel, enPieza, tu, elegidoG, azar)` → `{ id, ruta } | null`: elige al azar uno de los muebles puestos con `uso` y un gachamon quieto (los mismos que valen para `unPaseo`), y devuelve el camino hasta una casilla libre pegada al mueble (vecina por un lado, no en diagonal), que nadie pise y con camino. `null` si no hay mueble marcado, casilla o gachamon.
- En `departamento.js`, `darUnPaseo`: **sólo si hay algún mueble puesto con `uso`**, una llamada más a `azar` decide (menos de un tercio) si este paseo va a un mueble; si va y hay camino, el gachamon camina hasta ahí y al llegar **se queda** `SE_QUEDA_MS` (6000) sin que le toque otro paseo; si no, el paso suelto de siempre. Sin ningún mueble marcado, un paseo llama a `azar` las mismas tres veces que hoy. Las guardas son las de hoy (pieza lista, sin movimiento reducido, nada en la mano, pestaña visible), y la espera se cancela con todo lo demás al salir de la pantalla.

- [ ] **Step 1: las pruebas del módulo** (`tests/js/caminantes.test.mjs`): el camino termina en una casilla pegada al mueble marcado y nunca sobre un mueble, sobre `tu`, sobre otro gachamon ni en la casilla de la puerta; con el mueble rodeado, `null`; sin muebles con `uso`, `null` **sin llamar a `azar`**; no elige al que tiene su menú abierto.
- [ ] **Step 2: las pruebas de la pantalla** (`tests/js/departamento.test.mjs`): con un mueble con `uso` y un azar que fuerza la rama, un gachamon llega al lado del mueble y durante `SE_QUEDA_MS` los paseos siguientes no lo mueven; pasado ese tiempo vuelve a pasear; con un azar que no la fuerza, da el paso suelto de siempre; con movimiento reducido no se mueve nadie; si llega un estado sin ese mueble mientras camina, nada revienta y el gachamon acaba en una casilla libre. Las pruebas de paseos que ya existen pasan **sin tocarlas**.
- [ ] **Step 3:** córrelas: fallan.
- [ ] **Step 4:** `unPaseoAUnMueble` en `caminantes.js` y la rama en `darUnPaseo`. Ninguna clave del catálogo, ni el número 15, en el JavaScript.
- [ ] **Step 5:** `node --test tests/js/*.test.mjs` y `./venv/bin/python -m pytest tests/test_web_cliente.py tests/test_web_js.py -q`: todo pasa.
- [ ] **Step 6: mirarlo.** Con el arnés, una cuenta con los cuatro muebles puestos y tres gachamones: deja la página abierta un minuto y captura a uno junto a un mueble (390 × 664 y 1280). Con «reducir movimiento» activado, nadie se mueve.
- [ ] **Step 7: commit** — `feat(web): de vez en cuando un gachamon se acerca a un mueble de los que usa solo`.

### Task 7: Los documentos

**Files:**
- Modify: `AGENTS.md`, `README.md`, `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`

- [ ] **Step 1: `AGENTS.md`**, en «Invariantes del dominio»: donde dice que el ritmo y la comodidad «no tocan el hambre», lo que es ahora (el departamento fija el ritmo: la comodidad frena el ánimo y los muebles que se usan solos ponen un mínimo a su barra); donde dice que cada estadística se entrena por su vía, que las pesas son la otra vía de la fuerza; y lo nuevo, en pocas líneas: el mínimo y las pesas viven en `departamento.ritmo_de` y los aplica `sim.avanzar` (también sin tiempo transcurrido), no dan experiencia ni dinero, asentar antes de poner o guardar los cubre, el cliente reconoce esos muebles por la marca `uso` y el paseo hasta ellos es sólo de la pantalla.
- [ ] **Step 2: `README.md`**: en las reglas del departamento, los cuatro muebles (qué hacen, que no se llenan, que dos no hacen más, que no dan experiencia ni monedas, y lo que cuestan en crecimiento); en la pantalla de tu casa, que se acercan a usarlos; y de paso la línea desfasada que dice que «a todos» todavía no tiene botón.
- [ ] **Step 3: los pendientes**: una sección «Salió al ejecutar el rework 7» con lo que decidió Felipe, lo que decidió el plan, lo que se decidió al construir y lo que queda (sacar el transporte de `departamento.js`; decir junto a la barra que un mueble la sostiene; el arte de verdad de los cuatro; que el gachamon se dé vuelta o tenga dibujo usando el mueble); y quita de las secciones anteriores lo que este plan resuelve (la partición de `departamento.js` y su orden).
- [ ] **Step 4:** sin SHAs, números de tarea, cantidades de pruebas ni ids; «aprobó» no es «decidió». La suite entera pasa. **Commit** — `docs: los muebles que se usan solos, en la política, el README y los pendientes`.
