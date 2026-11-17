# Rework 5c · El modo construcción — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la pantalla del departamento tenga dos modos: el normal, para vivir (cuidar, caminar, y tocar un mueble hace su acción: hoy, la puerta te saca), y el de construcción, para mover, girar y guardar muebles, puertas y ventanas, poner lo guardado y ampliar.

**Architecture:** El modo es estado de la pantalla, sólo del cliente: no se guarda ni se manda al servidor, y siempre se entra en el normal. Qué recibe un toque en modo normal lo decide una función pura nueva de `proyeccion.js` (`queSeUsa`), junto a la de hoy (`queSeToco`), que pasa a ser la del modo construcción. La pantalla (`departamento.js`) guarda en qué modo está, enseña u oculta lo de construir y le dice a la lista (`lista.js`) en qué modo pintarse. El servidor no cambia, salvo dos frases de la carta del alcalde.

**Tech Stack:** JavaScript sin framework ni compilación, `node --test`; Python 3.12 y pytest para la carta.

**Spec:** `docs/superpowers/specs/2026-11-14-gachamon-rework-1-departamento-design.md`, sección 5.1 («El modo construcción», añadida con este plan), la 5 y la 4.5.

**Dónde encaja.** Es un plan corto que Felipe pidió el 2026-11-16, con la puerta a medio construir: «añadir un modo construccion para mover muebles y puertas y ventanas, de esa forma en el modo normal solo podras usar la accion de ese mueble, y no habran choques como con la puerta que al hacerle click podria moverse o salir del departamento». Cambia una regla del diseño (la que decía que decorar no tiene modos) y resuelve lo que quedó aparcado en la puerta: con un mueble delante, la puerta no se podía tocar. Va después de «la puerta» (el 5b) y antes de «partir sin gachamon» (el 6). Se junta en la rama `rework/1-departamento` y **se publica con todo lo demás, al final**.

**Lo que no entra.** Acciones propias para más muebles (hoy la única es la de la puerta; las demás llegan con los muebles que se usan solos y con los objetos para jugar). Tocar un mueble por lo que se ve de su dibujo en vez de por la silueta de su caja (sigue pendiente, para cuando llegue el arte). Que el modo se recuerde entre visitas. Partir `departamento.js` (sigue siendo el primer paso del plan de los muebles que se usan solos).

## Global Constraints

- Nada se sube, se fusiona ni se despliega: todo queda en la rama local `rework/1-departamento`.
- `web/` no importa `discord` ni nada que lo importe; `departamento.py` es puro. Este plan no añade rutas, tablas ni cambios de estado.
- **El modo es del cliente**: no se guarda ni se manda al servidor. El servidor sigue aceptando poner, guardar y ampliar como hoy (no sabe de modos).
- El cliente: sin frameworks ni compilación, sin `innerHTML`, sin direcciones `http`, módulos con rutas relativas terminadas en `.js`. **Ninguna clave ni precio del catálogo escritos en el JavaScript**: la puerta se reconoce por la marca `puerta` que manda el servidor, nunca por su clave.
- `proyeccion.js` y `casillas.js` son **puros**: sin DOM, sin reloj, sin red.
- Accesibilidad, como en el resto de la página: lo que se hace tocando el dibujo se hace también con botones de verdad; lo que cambia se anuncia (`role="status"`); lo que no se puede usar lleva `aria-disabled`; con movimiento reducido nada camina: aparece; el foco no se pierde.
- El dinero no cambia: ampliar sigue preguntando antes de cobrar, con su evento creado una vez por lo que se ve y fuera de lo que se reintenta, y el clic de confirmar con `evento.detail > 1` se sigue ignorando.
- Sin dependencias nuevas. Nunca se abre `tamagotchi.db` ni `.env`; las pruebas usan bases temporales e ids sintéticos. El repo es público.
- Antes de editar un símbolo, GitNexus `impact` (lo corre el controlador). Cada commit: `./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "…"`, con la línea de coautoría.
- **Lo que decidió Felipe (2026-11-16):**
  1. Hay un **modo construcción** para mover muebles, puertas y ventanas; en el **modo normal** un toque sobre un mueble sólo hace **su acción**.
  2. El botón se llama **`🔨 Construir`** y, dentro del modo, **`✔ Listo`**.
  3. **«Guardados» y «Ampliar» están sólo dentro del modo.** Fuera, la pantalla queda para vivir: cuidar, caminar, salir.
  4. En modo normal, **tocar la puerta te saca directo**: caminas hasta ella y sales al pueblo, sin menú; si mientras caminas tocas otra cosa, no sales; si ya estás en la puerta, sales al momento.
  5. En modo normal, **tocar un mueble sin acción propia no hace nada**: no lo elige; si se pisa (una alfombra), caminas hasta ahí; y no le quita el toque a la puerta cuando está delante de ella.
  6. **En el modo construcción a los gachamones no se les toca**: el toque pasa al mueble que tengan detrás, así ninguno estorba. Siguen paseando, y si pones un mueble donde hay uno, se corre solo. En modo normal, su menú sigue como hoy («Mover» y «Acariciar»).
  7. **La carta del alcalde nombra el botón**: donde hablaba de los guardados, dice que se entra a «Construir».
  8. **Al mover la puerta sólo se ofrecen los tramos con la entrada libre**: los que dan a un mueble que no se pisa no se marcan ni salen en «¿Dónde?». Poner después un mueble delante de la puerta se sigue pudiendo. (El servidor no cambia: es el cliente el que no lo propone.)
- **Lo que este plan decidió en nombre de Felipe** (se le enseñó con el plan y lo aprobó el 2026-11-16):
  1. **Siempre se entra en modo normal.** El modo no se recuerda: al volver a «Tu casa» estás en el normal.
  2. **El botón va bajo la pieza**, no encima (encima taparía el menú de lo elegido y los globos). En el modo, ahí mismo se lee «Modo construcción» y debajo quedan, abiertos mientras dure, la bandeja de guardados y «Ampliar». La pieza se enmarca para que se note el modo.
  3. **Tocar el suelo es caminar en los dos modos.**
  4. En el modo, la puerta trae sólo **`✋ Mover`**. Las frases `🚪 Salir` (menú) y `Salir` (lista) dejan de usarse: tocando el dibujo se sale tocando la puerta, y sin el dibujo se sale con «Pueblo».
  5. **La lista para teclado y lector de pantalla sigue al modo**: en el normal trae «Tus gachamones»; en el de construcción, además, «Muebles puestos» y «Guardados» con sus botones de hoy.
  6. **«✔ Listo» deja todo recogido**: suelta lo que lleves en la mano, cierra el menú y cierra lo de ampliar, sin cobrar nada.
  7. Los cuidados, «A todos», «Mochila» y «Pueblo» siguen disponibles en los dos modos.
  8. Con una petición en camino no se cambia de modo.
- **Frases nuevas** (Felipe las aprobó el 2026-11-16; van tal cual):
  - El botón: `🔨 Construir` y `✔ Listo`.
  - Lo que se lee junto al botón mientras dura el modo: `Modo construcción`.
  - El aviso al entrar: `Toca un mueble para moverlo, girarlo o guardarlo.`
  - Para el lector de pantalla, al terminar: `Modo construcción terminado.`
  - En la carta del alcalde, en lugar de las dos de hoy: `Tu mueble está en guardados: entra a «Construir» y ponlo donde quieras.` y `Tus {n} muebles están en guardados: entra a «Construir» y ponlos donde quieras.`

## Review Focus

1. **Cambiar de modo a medias**: con un mueble en la mano, con el menú abierto, con la pregunta de ampliar abierta, con «¿Dónde?» abierto en la lista, caminando hacia la puerta para salir, con una petición en camino. Nada queda colgado ni se manda sin querer. → Tasks 2 y 3.
2. **Salir sin querer o no poder salir**: en modo normal la puerta saca; en el de construcción, jamás; con la entrada tapada se dice «No hay camino hasta la puerta.» y, entrando al modo, el mueble que estorba se puede mover. Con un mueble alto delante, la puerta recibe el toque igual. → Tasks 1 y 2.
3. **Lo que deja de alcanzarse**: todo lo que se hacía antes (poner, mover, girar, guardar, ampliar, elegir a un gachamon, cuidarlo, ir a la mochila y al pueblo) se sigue pudiendo hacer, tocando el dibujo y sin él; nada queda sin botón. → Tasks 2 y 3.
4. **El foco y el lector de pantalla al cambiar de modo**: el foco se queda en el botón; el cambio se anuncia; lo que se esconde (la bandeja, las listas de muebles, lo de ampliar) no se lleva el foco. → Tasks 2 y 3.
5. **Lo que llega mientras construyes**: la relectura de cada 30 segundos y un departamento nuevo no te sacan del modo, no cierran la bandeja ni sueltan lo elegido sin motivo; un estado que pide otra pantalla sí te saca, como hoy. → Tasks 2 y 3.

---

### Task 1: Qué se usa al tocar y dónde va la puerta, en cuentas

**Files:**
- Modify: `web/static/js/proyeccion.js`, `web/static/js/casillas.js`
- Test: `tests/js/proyeccion.test.mjs`, `tests/js/casillas.test.mjs`

**Interfaces:**
- Consumes: lo que ya hay en `proyeccion.js` (`queSeToco`, `tramoEn`, `casillaEn`, la silueta de un mueble, `cajaDelGachamon`, `ordenDePintado`).
- Produces: `queSeUsa(m, depto, gachamones, x, y, conAccion) -> {tipo: 'gachamon', id} | {tipo: 'accion', id} | {tipo: 'casilla', i, j} | null`. `conAccion` es `(puesto) => boolean`: dice si ese mueble puesto tiene acción propia. `queSeToco` **no cambia** (ni su firma ni lo que devuelve).
- Produces: en `casillas.js`, `conLaEntradaLibre(depto, sitios) -> sitios`: de unos sitios de pared (`{x, y, giro}`, como los da `dondeCabe`), los que tienen libre la casilla de dentro que queda enfrente (la misma que da `laPuerta`: `[max(x, 0), max(y, 0)]`), es decir, la que no está entre las de `noSePisan(depto)`. En el mismo orden. `dondeCabe` **no cambia**: la prueba que contrasta al cliente con el servidor (`tests/test_casillas_cliente.py`) tiene que seguir pasando sin tocarla, porque el servidor sí acepta la puerta en un tramo con la entrada tapada; es la pantalla la que no lo propone.

Lo que devuelve `queSeUsa`, en este orden:

1. Un gachamon bajo el punto: el de más adelante, como en `queSeToco`.
2. Un mueble de bulto **con acción** cuya silueta contiene el punto: el de más adelante de los que tienen acción → `{tipo: 'accion', id}`.
3. El mueble de pared **con acción** colgado en el tramo que hay bajo el punto → `{tipo: 'accion', id}`. Aunque el punto caiga también en la silueta de un mueble sin acción: lo que no tiene acción no le quita el toque a lo que la tiene.
4. Si el punto cae en la silueta de un mueble de bulto (sin acción), o en un tramo de pared (vacío o con algo colgado sin acción) → `null`. El toque **no pasa** al suelo de detrás.
5. Una casilla de la pieza → `{tipo: 'casilla', i, j}`, **sin** `mueble` aunque haya algo que se pisa.
6. Fuera de todo → `null`.

- [ ] **Step 1: Write the failing tests** (en `tests/js/proyeccion.test.mjs`, tras las de `queSeToco`; `M`, `GENTE`, `MACETA`, `FELPUDO`, `CUADRO` y `depto` son los del archivo)

```js
// Un 4 × 4 con la puerta en el tramo 2 de la pared izquierda, una maceta justo delante de ella, en (0, 2),
// un felpudo en (3, 0), un cuadro en el tramo 1 de la pared derecha y un gachamon parado en (1, 1).
const PUERTA = { clave: 'puerta', ancho: 1, fondo: 1, capa: 'pared', puerta: true };
const VIVIENDO = depto([{ id: 5, ...PUERTA, x: -1, y: 2, giro: 0, casillas: [[-1, 2]] },
                        { id: 7, ...MACETA, x: 0, y: 2, giro: 0, casillas: [[0, 2]] },
                        { id: 9, ...FELPUDO, x: 3, y: 0, giro: 0, casillas: [[3, 0]] },
                        { id: 11, ...CUADRO, x: 1, y: -1, giro: 0, casillas: [[1, -1]] }], 4, 4);
const conAccion = (puesto) => Boolean(puesto.puerta);
const uso = (i, j, h = 0) => p.queSeUsa(M, VIVIENDO, GENTE, ...p.proyectar(M, i, j, h), conAccion);

test('viviendo, sólo recibe el toque lo que tiene acción', () => {
  assert.deepEqual(uso(1.5, 1.5), { tipo: 'gachamon', id: 3 });
  assert.deepEqual(uso(0.5, 3.5), { tipo: 'casilla', i: 0, j: 3 });
  assert.deepEqual(uso(3.5, 0.5), { tipo: 'casilla', i: 3, j: 0 });        // lo que se pisa no se elige: se camina
  assert.equal(uso(0.5, 2.5), null);                                         // el pie de la maceta: nada
  assert.equal(uso(1.5, 0, M.pared / 2), null);                              // el cuadro: nada
  assert.equal(uso(3.5, 0, M.pared / 2), null);                              // un tramo vacío
  assert.equal(p.queSeUsa(M, VIVIENDO, GENTE, 2, 2, conAccion), null);       // una esquina del lienzo
});

test('un mueble delante no le quita el toque a la puerta', () => {
  const enLaPuerta = p.proyectar(M, 0, 2.5, M.pared / 2);                    // el centro de su tramo
  assert.deepEqual(p.queSeToco(M, VIVIENDO, [], ...enLaPuerta), { tipo: 'mueble', id: 7 });   // construyendo, la maceta
  assert.deepEqual(p.queSeUsa(M, VIVIENDO, [], ...enLaPuerta, conAccion), { tipo: 'accion', id: 5 });
  assert.equal(p.queSeUsa(M, VIVIENDO, [], ...enLaPuerta, () => false), null);                // sin acción, nada
});

test('la puerta se usa en las dos paredes, y un gachamon delante se toca antes', () => {
  const derecha = depto([{ id: 5, ...PUERTA, x: 2, y: -1, giro: 0, casillas: [[2, -1]] }], 4, 4);
  assert.deepEqual(p.queSeUsa(M, derecha, [], ...p.proyectar(M, 2.5, 0, M.pared / 2), conAccion), { tipo: 'accion', id: 5 });
  const delante = [{ id: 4, i: 0, j: 2 }];
  assert.deepEqual(p.queSeUsa(M, VIVIENDO, delante, ...p.proyectar(M, 0, 2.5, M.pared / 2), conAccion), { tipo: 'gachamon', id: 4 });
});

test('un mueble de bulto con acción también se usa', () => {
  const laMaceta = (puesto) => puesto.id === 7;
  assert.deepEqual(p.queSeUsa(M, VIVIENDO, [], ...p.proyectar(M, 0.5, 2.5), laMaceta), { tipo: 'accion', id: 7 });
});
```

Y en `tests/js/casillas.test.mjs` (con las formas y la ayuda `depto(...)` del archivo; si la cama o el felpudo de ejemplo no están, añádelos junto a las demás formas):

```js
test('la puerta sólo se ofrece donde la entrada queda libre', () => {
  // Un 3 × 3 con una cama de 2 × 1 en (0, 0) —tapa (0, 0) y (1, 0)— y un felpudo en (0, 1).
  const pieza = depto([{ id: 1, clave: 'cama_sencilla', capa: 'bulto', ancho: 2, fondo: 1, x: 0, y: 0, giro: 0, casillas: [[0, 0], [1, 0]] },
                       { id: 2, clave: 'felpudo', capa: 'suelo', ancho: 1, fondo: 1, x: 0, y: 1, giro: 0, casillas: [[0, 1]] }]);
  const sitios = [{ x: -1, y: 0, giro: 0 }, { x: -1, y: 1, giro: 0 }, { x: 0, y: -1, giro: 0 },
                  { x: 1, y: -1, giro: 0 }, { x: 2, y: -1, giro: 0 }];
  assert.deepEqual(c.conLaEntradaLibre(pieza, sitios), [{ x: -1, y: 1, giro: 0 }, { x: 2, y: -1, giro: 0 }]);
  assert.deepEqual(c.conLaEntradaLibre(depto([]), sitios), sitios);          // sin muebles, todos
  assert.deepEqual(c.conLaEntradaLibre(pieza, []), []);
});
```

(Si el archivo importa el módulo con otro nombre que `c`, usa el suyo.)

- [ ] **Step 2: Run them to make sure they fail**

Run: `node --test tests/js/proyeccion.test.mjs tests/js/casillas.test.mjs`
Expected: FAIL — `p.queSeUsa is not a function` en las cuatro pruebas nuevas de la proyección y `conLaEntradaLibre is not a function` en la de las casillas; las de antes pasan.

- [ ] **Step 3: Implement `queSeUsa(m, depto, gachamones, x, y, conAccion)` in `web/static/js/proyeccion.js` and `conLaEntradaLibre(depto, sitios)` in `web/static/js/casillas.js`**

`queSeUsa`, exportada junto a `queSeToco`, con el orden de la lista de arriba. Lo que las dos comparten (a quién se toca de los gachamones, qué muebles de bulto tienen el punto en su silueta, qué hay colgado en un tramo) se saca a funciones del módulo en vez de repetirse; `queSeToco` tiene que seguir devolviendo exactamente lo mismo que hoy. `conLaEntradaLibre`, con `noSePisan`. Actualiza los comentarios de cabecera de los dos módulos.

- [ ] **Step 4: Run the tests**

Run: `node --test tests/js/proyeccion.test.mjs tests/js/casillas.test.mjs` y `./venv/bin/python -m pytest -q tests/test_casillas_cliente.py`
Expected: PASS, todas (las de antes, sin tocarlas).

- [ ] **Step 5: Commit**

`feat(web): qué se usa al tocar la pieza viviendo y dónde se ofrece la puerta, en cuentas`

---

### Task 2: El modo en la pieza

**Files:**
- Modify: `web/static/js/departamento.js`, `web/static/estilo.css`
- Test: `tests/js/departamento.test.mjs`, `tests/test_web_cliente.py` (sólo si alguna guarda nombra lo que cambia)

**Interfaces:**
- Consumes: `queSeUsa` y `conLaEntradaLibre` (Task 1); `queSeToco`, `laPuerta` y lo demás de hoy.
- Produces: en la pantalla, el botón `.boton-construir` (dice `Construir` o `Listo`), la clase `construyendo` en el nodo `.pieza` mientras dura el modo, y el rótulo `.rotulo-de-obra` («Modo construcción», escondido fuera del modo). La Task 3 se apoya en ese estado y en esos nodos.

Lo que tiene que quedar:

- **El botón**, bajo la pieza (entre el dibujo y la línea del tamaño), siempre a la vista cuando la pieza ha llegado: `🔨 Construir`; dentro del modo, el mismo botón dice `✔ Listo` y a su lado se lee `Modo construcción`. El emoji va en su `span` con `aria-hidden`, como los demás botones con ícono. Con una petición en camino no se puede usar (`aria-disabled`) y no cambia el modo.
- **Siempre se entra en modo normal.** El modo no se guarda en ningún sitio.
- **Al entrar al modo**: deja de estar elegido el gachamon que lo estuviera (su menú se cierra; su ficha sigue a la derecha), se suelta lo que se llevara en la mano, se cancela una salida en curso, y el aviso dice `Toca un mueble para moverlo, girarlo o guardarlo.` El foco se queda en el botón.
- **Al terminar** (`✔ Listo`): se suelta lo que se lleve en la mano, deja de estar elegido el mueble que lo estuviera (su menú se cierra) y se le dice al lector de pantalla `Modo construcción terminado.` (por el anuncio que no se ve, el de la lista). El foco se queda en el botón.
- **Tocar el dibujo en modo normal** (con `queSeUsa`, donde tiene acción el puesto que trae `puerta`):
  - un gachamon: como hoy (lo elige, con su menú «Mover» y «Acariciar»; tocarlo otra vez deja de elegirlo);
  - la puerta: `salirPorLaPuerta()`, tal como está (camina y sale; si ya estás en ella, al momento; con menos movimiento, sin caminar; sin camino, `No hay camino hasta la puerta.`; con una petición en camino, no se sale);
  - una casilla: caminas hasta ella (contando con la puerta, como hoy) y deja de estar elegido el gachamon que lo estuviera;
  - nada (`null`): deja de estar elegido el gachamon; no se camina.
  - Ningún mueble queda elegido nunca en modo normal: no hay menú de mueble.
  - Mover a un gachamon (desde su menú) sigue igual: con él en la mano, el toque es el sitio adonde va.
- **Tocar el dibujo en el modo construcción** (con `queSeToco`, sin pasarle gachamones): como hoy para los muebles (elegir, su menú, lo que se pisa además se camina, el suelo es caminar, fuera deja de elegir), y a los gachamones no se les toca: el toque va a lo que tengan detrás.
- **El menú de un mueble** (sólo en el modo): `✋ Mover`, `🔄 Girar` (no lo de pared) y `📦 Guardar` (no la puerta). La puerta: sólo `✋ Mover`. `🚪 Salir` desaparece del menú.
- **Al mover la puerta sólo se ofrecen los tramos con la entrada libre** (`conLaEntradaLibre`), en el dibujo (lo que se marca) y en la lista («¿Dónde?»): los dos salen del mismo sitio (`manoAlDia`). Si no queda ninguno, `Ahí no cabe.`, como con cualquier mueble. Los demás muebles de pared no cambian.
- Tocar la pieza mientras caminas a la puerta sigue cancelando la salida, salvo que lo tocado sea otra vez la puerta. Elegir a un gachamon **desde la lista** también la cancela (hoy no lo hacía).
- **Se nota el modo**: mientras dura, `.pieza` lleva la clase `construyendo` y el dibujo se enmarca (con los colores del tema; que se vea en claro y en oscuro).
- En esta tarea «Guardados» y «Ampliar» **siguen donde están** (los mueve la Task 3) y la lista sigue como hoy, salvo que su fila de la puerta ya no trae «Salir» (trae sólo «Mover») y `salir` sale de lo que la pantalla le pasa a la lista.
- El comentario de cabecera de `departamento.js` (que hoy dice «sin modos») se pone al día.

- [ ] **Step 1: Write the failing tests** (en `tests/js/departamento.test.mjs`; con las ayudas del archivo: `abrir`, `boton`, `menu`, `rotulos`, `tocarTramo`, `tocarCasilla`, `tocarA`, `correrCuadros`, `dondeEstas`, `casillasMarcadas`, el servidor de mentira). Una ayuda nueva: `construir(pantalla)` toca `Construir` y `terminar(pantalla)` toca `Listo`.

  - `se entra en modo normal, con «Construir» bajo la pieza`: `boton(pantalla, 'Construir')` existe y `boton(pantalla, 'Listo')` no; `.pieza` no tiene la clase `construyendo`; `.rotulo-de-obra` está escondido.
  - `«Construir» entra al modo y «Listo» lo termina`: tras `construir`, el botón dice `Listo`, `.pieza` tiene `construyendo`, `.rotulo-de-obra` dice `Modo construcción` y se ve, y el aviso dice `Toca un mueble para moverlo, girarlo o guardarlo.`; el foco está en el botón; tras `terminar`, todo vuelve, el foco sigue en el botón y el anuncio (`.solo-lector[role=status]`) dice `Modo construcción terminado.`
  - `viviendo, tocar un mueble no lo elige`: con `CON_MACETA`, tocar la maceta: `menu(pantalla)` es `null`, no se marca nada y tu avatar no se mueve; tocar la cama, igual; tocar el cuadro de `CON_UN_CUADRO_COLGADO`, igual.
  - `viviendo, lo que se pisa se camina y no se elige`: con el felpudo puesto, tocarlo: sin menú, y tras `correrCuadros` estás en su casilla.
  - `viviendo, tocar la puerta te saca`: `tocarTramo(pantalla, -1, 2)` (la puerta de `DEPTO`) estando dentro: caminas y, al llegar, `seguir` recibe lo mismo que con «Pueblo»; ningún `POST` sale.
  - `viviendo, en la puerta y tocándola, sales al momento`: recién entrado (estás en la puerta), tocarla: `seguir` llamado sin correr cuadros.
  - `viviendo, la puerta se toca aunque tenga un mueble delante, y sin camino no se sale`: con una maceta en `(0, 2)`: tocar el tramo de la puerta dice `No hay camino hasta la puerta.` y no se sale (**es la prueba que la puerta dejó pendiente: ahora por el dibujo, no por la lista**).
  - `construyendo, tocar la puerta no saca: sale su menú, sólo con «Mover»`: `rotulos(menu(pantalla))` es `['Mover']`; `seguir` no se llamó.
  - `al mover la puerta sólo se ofrecen los tramos con la entrada libre`: en `DEPTO` (la cama tapa `(0, 0)` y `(1, 0)`), «Mover» la puerta marca sólo los tramos libres cuya casilla de enfrente no tapa la cama, y «¿Dónde?» de la puerta en la lista ofrece esos mismos; con un mueble de bulto delante de cada tramo libre, «Mover» dice `Ahí no cabe.` (pone al día la prueba de hoy «al mover la puerta se ofrecen los tramos libres de las dos paredes», sin perder lo que comprueba del cuadro colgado).
  - `construyendo, un mueble trae Mover, Girar y Guardar, y lo de pared no trae Girar`: `['Mover', 'Girar', 'Guardar']` para la cama; `['Mover', 'Guardar']` para el cuadro.
  - `construyendo, a un gachamon no se le toca: el toque va al mueble de detrás`: un gachamon parado delante de la cama; tocarlo abre el menú de la cama (o nada, si detrás sólo hay suelo: entonces caminas), nunca el del gachamon.
  - `entrar al modo deja de elegir al gachamon y suelta lo que llevas`: con el menú de un gachamon abierto, `construir`: sin menú; con un gachamon en la mano («Mover»), `construir`: nada marcado.
  - `«Listo» suelta lo que llevas y cierra el menú`: en el modo, «Mover» la cama (casillas marcadas) y `terminar`: nada marcado, sin menú, y ningún `POST` salió.
  - `entrar al modo cancela la salida`: tocar la puerta desde dentro y, a medio camino, `construir`: tras `correrCuadros`, `seguir` no se llamó.
  - `con una petición en camino no se cambia de modo`: con un cuidado sin contestar, el botón lleva `aria-disabled="true"` y tocarlo no cambia nada.
  - `la relectura no te saca del modo`: en el modo, con la cama elegida, `releer()`: sigue `construyendo`, y el menú de la cama sigue abierto.
  - `elegir a un gachamon desde la lista cancela la salida`: tocar la puerta desde dentro y, a medio camino, pulsar su botón en «Tus gachamones»: no se sale.
  - Las pruebas de hoy que eligen o mueven un mueble tocando el dibujo, o que esperan «Salir» en un menú o en la lista, se ponen al día (entrando antes al modo, o cambiando «Salir» por tocar la puerta) **sin perder lo que comprueban**; ninguna se borra. Lista en el informe cada una que cambiaste y por qué.

- [ ] **Step 2: Run them to make sure they fail**

Run: `node --test tests/js/departamento.test.mjs`
Expected: FAIL en las nuevas (no existe `Construir`).

- [ ] **Step 3: Implement**

En `departamento.js`: el estado `construyendo`; el botón y el rótulo en una fila propia dentro de `.pieza`, bajo el escenario; el oyente del lienzo partido en las dos formas de tocar; `hacerElMenu` sin «Salir» y sin «Guardar» para la puerta; el botón entre lo que no se puede usar con una petición en camino. En `estilo.css`: la fila del botón (en el teléfono y en el computador) y el marco del modo. Sin colores sueltos: con las variables del tema.

- [ ] **Step 4: Run the tests**

Run: `node --test tests/js/` y `./venv/bin/python -m pytest -q`
Expected: PASS, todo.

- [ ] **Step 5: Míralo** (obligatorio). Con el arnés (copia el más reciente a una carpeta tuya; bases temporales; puertos que no sean 8000, 8010, 8011 ni 8061; apaga por su pid lo que levantes), capturas en 390 y en 1280 de ancho, en claro y en oscuro: modo normal recién entrado; modo construcción con un mueble elegido y su menú; modo construcción con la puerta elegida; modo normal con una maceta delante de la puerta tras tocar la puerta (el aviso). Las rutas completas, al informe.

- [ ] **Step 6: Commit**

`feat(web): el modo construcción: viviendo, tocar un mueble hace su acción; construyendo, se mueve`

---

### Task 3: Guardados, ampliar y la lista, dentro del modo

**Files:**
- Modify: `web/static/js/departamento.js`, `web/static/js/lista.js`, `web/static/estilo.css`
- Test: `tests/js/departamento.test.mjs`

**Interfaces:**
- Consumes: el estado `construyendo`, el botón y la clase `construyendo` de la Task 2.
- Produces: `listaDelDepartamento(acciones).pintar(depto, visto, construyendo)` — el tercer parámetro dice en qué modo pintarse; sin él (o `false`), el normal.

Lo que tiene que quedar:

- **El botón «Guardados» desaparece.** La bandeja de guardados (con su rótulo `Guardados · toca uno y después una casilla` y su `No queda nada guardado.`) está **abierta bajo la pieza mientras dura el modo** y escondida fuera de él. El foco que estaba en un tipo de la bandeja que ya no queda va al botón del modo.
- **«Ampliar» pasa a estar bajo la pieza, junto a la bandeja, y sólo se ve en el modo.** Lo que abre (los lados, la pregunta, «Volver») no cambia. `✔ Listo` con lo de ampliar abierto lo cierra (y su pregunta) sin mandar nada.
- En modo normal, a la derecha quedan la ficha del elegido, «A todos», «Mochila» y «Pueblo».
- **La lista** (`lista.js`): en modo normal trae sólo «Tus gachamones»; en el de construcción, además, «Muebles puestos» y «Guardados», con sus botones de hoy (la puerta, sólo «Mover»). Al terminar el modo, «¿Dónde?» se cierra si estaba abierto. Lo que se esconde no se lleva el foco: el modo sólo cambia desde su botón, que es quien lo tiene. El comentario de cabecera de `lista.js` (que hoy dice «no es un modo») se pone al día.
- La relectura y un departamento nuevo no cierran la bandeja ni sacan del modo.

- [ ] **Step 1: Write the failing tests** (en `tests/js/departamento.test.mjs`)

  - `viviendo no se ven Guardados ni Ampliar`: `boton(pantalla, 'Guardados')` es `null` siempre; fuera del modo, `.bandeja` y el botón `Ampliar` están escondidos.
  - `construyendo, la bandeja está abierta y Ampliar a la vista`: tras `construir` con `SIN_MACETA`: se ve `.bandeja` con `Maceta × 1`; el botón `Ampliar` se ve; tras `terminar`, los dos escondidos.
  - `construyendo sin nada guardado, la bandeja lo dice`: `No queda nada guardado.`
  - `de la bandeja a la pieza, dentro del modo`: tomar la maceta de la bandeja, tocar una casilla libre: sale `POST departamento/poner` con ese sitio (lo de hoy, entrando antes al modo).
  - `«Listo» con algo de la bandeja en la mano lo suelta`: nada marcado y ningún `POST`.
  - `«Listo» cierra lo de ampliar y su pregunta sin cobrar`: con la pregunta `¿Ampliar por 45 monedas?` abierta, `terminar`: `.ampliar` escondido, lo de la derecha a la vista, ningún `POST departamento/ampliar`; al volver a entrar al modo y abrir «Ampliar», no hay pregunta abierta.
  - `la lista sigue al modo`: fuera del modo, `.lista-puestos` y `.lista-guardados` están escondidas y «Tus gachamones» a la vista; en el modo, las tres; la fila de la puerta trae sólo `Mover`.
  - `«Listo» cierra «¿Dónde?»`: con «¿Dónde?» abierto en la fila de la cama, terminar el modo (el foco pasa al botón al pulsarlo): `#lista-donde` ya no está.
  - `la relectura no cierra la bandeja`: en el modo, `releer()`: la bandeja sigue a la vista con lo suyo.
  - `el tipo que se acaba devuelve el foco al botón del modo`: con el foco en `Maceta × 1`, ponerla (ya no queda): el foco está en el botón que dice `Listo`.
  - Las pruebas de hoy de la bandeja, de ampliar y de la lista se ponen al día entrando antes al modo, **sin perder lo que comprueban**; ninguna se borra. Lista en el informe cada una que cambiaste y por qué.

- [ ] **Step 2: Run them to make sure they fail**

Run: `node --test tests/js/departamento.test.mjs`
Expected: FAIL en las nuevas.

- [ ] **Step 3: Implement**

- [ ] **Step 4: Run the tests**

Run: `node --test tests/js/` y `./venv/bin/python -m pytest -q`
Expected: PASS, todo.

- [ ] **Step 5: Míralo** (obligatorio). Con el arnés, capturas en 390 y en 1280, en claro y en oscuro: modo normal (lo de la derecha sin «Guardados» ni «Ampliar»); modo construcción con la bandeja y «Ampliar» bajo la pieza; con un mueble de la bandeja en la mano y sus casillas marcadas; con la pregunta de ampliar abierta; la lista en cada modo. Que en el teléfono el botón del modo, la bandeja y «Ampliar» queden juntos bajo el dibujo y nada se salga de la pantalla. Las rutas completas, al informe.

- [ ] **Step 6: Commit**

`feat(web): guardados, ampliar y la lista de muebles, dentro del modo construcción`

---

### Task 4: La carta y los documentos

**Files:**
- Modify: `web/carta.py`, `AGENTS.md`, `README.md`, `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`
- Test: `tests/test_web_carta.py`

**Interfaces:**
- Consumes: lo construido en las Tasks 1 a 3.
- Produces: nada que otra tarea use.

- [ ] **Step 1: Write the failing tests** (en `tests/test_web_carta.py`, poniendo al día las que hoy fijan esas dos frases): con un mueble, la carta trae `Tu mueble está en guardados: entra a «Construir» y ponlo donde quieras.`; con tres, `Tus 3 muebles están en guardados: entra a «Construir» y ponlos donde quieras.`

- [ ] **Step 2: Run them to make sure they fail**

Run: `./venv/bin/python -m pytest -q tests/test_web_carta.py`
Expected: FAIL (dice las frases de antes).

- [ ] **Step 3: Cambia las dos frases en `web/carta.py`** (`lineas_de`). Nada más de la carta.

- [ ] **Step 4: Los documentos**
  - `AGENTS.md`: una línea con el invariante nuevo, junto a las del departamento: el modo construcción es sólo del cliente (no se guarda ni se manda), viviendo sólo recibe el toque lo que tiene acción (`proyeccion.queSeUsa`) y el servidor no sabe de modos. Comprueba con `git grep` que cada nombre existe. Sin SHAs ni cantidades.
  - `README.md`: el párrafo de «Tu casa», en llano: para mover muebles se entra a «Construir»; tocando la puerta se sale.
  - Pendientes: una sección «Salió al ejecutar el rework 5c (el modo construcción)», con la misma forma que las anteriores: lo que decidió el dueño, lo que el plan propuso y él aprobó, lo que se decidió al construir (se puede cambiar) y lo que queda. Lo de la puerta que no se podía tocar con un mueble delante pasa de pendiente a resuelto (di cómo). Sigue pendiente: quien está en la puerta queda tapado por un mueble alto que tenga delante; el toque por la silueta de la caja y no por lo que se ve del dibujo.
  - Las notas del controlador para esta tarea estarán en la carpeta de trabajo del plan (`notas-para-la-tarea-4.md`).

- [ ] **Step 5: Run everything**

Run: `./venv/bin/python -m pytest -q` y `node --test tests/js/`
Expected: PASS.

- [ ] **Step 6: Commit**

`docs: el modo construcción, en la carta del alcalde, la política, el README y los pendientes`
