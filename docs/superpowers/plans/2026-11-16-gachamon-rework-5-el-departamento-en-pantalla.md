# Rework 5 · El departamento en pantalla — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que «Tu casa» sea la pieza de tu departamento en vista isométrica por casillas: verla, caminar por ella, poner, mover, girar y guardar muebles, ver ahí a todos tus gachamones y cuidarlos, de a uno o a todos, y ampliarla.

**Architecture:** El servidor ya tiene las reglas (plan 4); aquí gana lo poco que la pantalla necesita (el plantel entero en `GET /departamento`, «salir con él» desde el departamento, la ficha de cualquiera) y las decisiones de Felipe del 2026-11-16. El arte de la pieza entra al contrato con su familia propia: originales grandes en `fuentes/pieza/` y copias reducidas, que son las que sirve la página. En el cliente, toda la cuenta vive en dos módulos puros con sus pruebas: `casillas.js` (la rejilla: qué cabe dónde, por dónde se camina) y `proyeccion.js` (dónde se pinta cada cosa, quién tapa a quién y qué se tocó); `pieza.js` sólo dibuja, y `departamento.js` es la pantalla. Lo que el cliente cree que cabe se contrasta en una prueba con lo que dice `departamento.py`. Todo lo que se hace tocando el dibujo se hace también desde una lista con los mismos botones, y por esa lista se prueba la pantalla.

**Tech Stack:** Python 3.12, FastAPI, SQLite síncrono, Pillow (ya en uso para el arte), JavaScript sin framework ni compilación, lienzo 2D, pytest y `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-14-gachamon-rework-1-departamento-design.md` (secciones 4.2, 5, 8 y 9; la 2, «sería un fracaso»). Los dos bocetos aprobados: `docs/superpowers/specs/2026-11-14-bocetos/departamento-pantalla.html` y `departamento-casillas.html`. Inventario del cliente de hoy y de los bocetos, con archivo y línea: `.superpowers/sdd/2026-11-16-gachamon-rework-5-reconocimiento/inventario.md`; las decisiones de Felipe, con sus palabras: `decisiones-de-felipe.md`, en esa misma carpeta (ninguno de los dos va en el repo).

**Dónde encaja.** Es el plan 5 de 8 del proyecto 1 del rework. El orden cambió el 2026-11-16 (Felipe: «de acuerdo, primero la pantalla»): (1) nadie muere — hecho; (2) el tiempo para todos — hecho; (3) el bot en pausa — hecho; (4) la vivienda por casillas — hecho; **(5) el departamento en pantalla**; (6) partir sin gachamon; (7) los muebles que se usan solos; (8) el pueblo sin Refugio ni Incubadora y los documentos. Todos se juntan en la rama `rework/1-departamento` y **se publican juntos al final**.

**Lo que no entra, y dónde va.** Partir sin gachamon, sin huevo y con la primera aventura: plan 6 (aquí la pantalla ya tiene que **verse bien sin ningún gachamon**, pero a ella se sigue llegando con uno). El ropero y la mochila del gachamon que no sale contigo: no se hacen (decisión de Felipe: para vestirlo o darle un objeto, primero «Salir con él»). El refrigerador, la consola, la ducha y las pesas: plan 7. Quitar del mapa el Refugio y la Incubadora y llamar «Tu departamento» a «Tu casa»: plan 8. Reclutar (el botón del boceto era de mentira), el balcón, la mesa de gato y los teletransportadores: otros proyectos. El arte definitivo: lo dibuja el dibujante después; aquí todo sale con dibujos de relleno.

## Global Constraints

- Nada se sube, se fusiona ni se despliega: todo queda en la rama local `rework/1-departamento`.
- Los módulos de juego no importan `discord`; `web/` no importa `discord` ni nada que lo importe; `db.py` no importa `economia.py`; `departamento.py` es puro. Ninguna ruta acepta un identificador de persona; el servicio no guarda estado del juego en memoria.
- **El servidor manda**: el cliente dibuja y propone; qué mueble hay en qué casilla lo decide y lo guarda el servidor. Lo que el cliente calcula (qué cabe, qué casillas se marcan) es para dibujar y para no proponer lo imposible, nunca para decidir.
- **Dónde está parado cada gachamon y el avatar no se guarda ni se manda al servidor.** Sólo se guardan los muebles.
- Lo que mueve monedas lleva un evento (`nuevoEvento()` fuera del reintento, una vez por toque): ampliar y cada cuidado. Poner y guardar se pueden repetir tal cual.
- **Decorar no tiene modos**: se toca el mueble y ahí salen sus opciones (Mover, Girar, Guardar). Es lo que Felipe pidió y lo que sería un fracaso romper.
- El cliente: sin frameworks ni compilación, sin `innerHTML`, sin direcciones `http`, módulos con rutas relativas terminadas en `.js`, nodos sólo con `el(...)` de `dom.js`. **Ninguna clave ni precio del catálogo escritos en el JavaScript**: los nombres, las formas y los costes llegan del servidor.
- **El arte son archivos descritos en el contrato** (`web/arte.py`); si falta uno se ve su recuadro con su nombre y nunca otro dibujo. La pieza **no es pixel art**: sus dibujos se pintan con suavizado; el avatar y los retratos de hoy, que sí lo son, se siguen pintando sin él.
- Accesibilidad, como en el resto de la página: el lienzo es `aria-hidden` y todo lo que se hace en él se hace también desde la lista; lo que cambia se anuncia con `role="status"`; botones que no se pueden usar con `aria-disabled`, no `disabled`; con `prefers-reduced-motion`, nada camina: aparece.
- Vale en el teléfono y en el computador, con el corte de 900 px de hoy.
- Sin dependencias nuevas. Dominio determinista: el tiempo y el azar se inyectan en las pruebas (en el cliente, las funciones puras reciben el azar como argumento).
- Nunca se abre `tamagotchi.db` ni `.env`; las pruebas usan bases temporales e ids sintéticos. El repo es público: sin IPs, ids de personas ni secretos.
- Antes de editar un símbolo, GitNexus `impact` (lo corre el controlador; si devuelve CRITICAL con una lista de símbolos que no tiene que ver, se contrasta con `git grep`). El índice se refresca sólo con `node .gitnexus/run.cjs analyze --index-only`.
- Cada commit: `./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "…"`, y termina con la línea de coautoría de la sesión que lo escribe.
- A quien juega se le dice «monedas» y «gemas»; la comodidad nunca se enseña con `%`.
- **Decisiones de Felipe del 2026-11-16** (contestadas una por una; van tal cual):
  1. El día del cambio, cada casa **mediana o grande** devuelve **140 monedas más** que su precio de catálogo (pequeña 200, mediana 640, grande 1340).
  2. La carta dice «por tu ticket» cuando era uno: `El refugio cerró. Te devolví 40 monedas por tu ticket.`
  3. En la carta, la especie va con su mayúscula: `Tu Octopul ahora se llama Brisa. Se puso el nombre solo, y se lo puedes cambiar una vez.`
  4. Las pociones de fuerza y de velocidad y las sopaipillas **no se pueden usar y no se gastan** desde la mochila; dicen lo mismo que la Tienda: `Sirve en las competencias, que todavía no están en la página.`
  5. El cuidado de aseo se llama **«Bañar»** en todas partes (hoy el botón dice «Limpiar»).
  6. Frases del huerto cerrado. Semilla: `Se planta en el huerto, que vuelve más adelante. Salen de 2 a 4 porotos, todos del mismo color al azar. Es la única forma de conseguir un color que no tengas.` Su nota en la mochila: `Se usa en el huerto, que vuelve más adelante.` Porotos: su texto de hoy más `El huerto y la cocina vuelven más adelante.`
  7. Del gachamon que toques en el departamento: sus cuidados y su **ficha completa**. El ropero y la mochila siguen siendo del que sale contigo.
  8. **El arte de la pieza** (cambia el diseño §4.2): la casilla mide **1024 × 512 píxeles**, **no es pixel art**, y **cada mueble tiene cuatro imágenes, mirando al NE, al NO, al SE y al SO**; nada se espeja. Los originales van **en el repo, en `fuentes/`**; la página sirve copias reducidas.
  9. En el computador, la pieza a la izquierda y, a la derecha, la ficha, «A todos» y los botones; los guardados, bajo la pieza.
  10. Bajo la pieza se muestra también la comodidad.
  11. El tope de 12 cuidados pagados al día se queda.
  12. Al poner, mover o guardar **bien no sale texto**; sólo cuando algo no se puede.
- **Frases nuevas de este plan** (Felipe las aprobó el 2026-11-16, al aprobar el plan; van tal cual). Las de los bocetos que aprobó van marcadas «boceto»:
  - La línea bajo la pieza: `{ancho} × {fondo} · {ocupadas} de {casillas} casillas · camas {camas} · gachamones {n} · comodidad {comodidad} de {tope}`
  - El menú de un mueble (boceto): `✋ Mover` · `🔄 Girar` · `📦 Guardar`. El de un gachamon: `✋ Mover` (boceto) y `Acariciar`; `Acariciar` está también en su ficha.
  - Con algo elegido para poner o mover (boceto): `Toca la casilla donde lo quieres.` Para lo de pared: `Toca la pared donde lo quieres.`
  - Guardados (boceto): el botón `📦 Guardados`; el rótulo `Guardados · toca uno y después una casilla`; vacío, `No queda nada guardado.`; bajo cada uno, `1 casilla`, `{n} casillas` o `en la pared`.
  - «A todos» (boceto): `🍖 Alimentar a todos` · `🎮 Jugar con todos` · `🏋️ Entrenar con todos` · `🧼 Bañar a todos`.
  - La ficha del elegido (boceto): la chapa `Sale contigo` y el botón `Salir con {nombre}`.
  - Ampliar (boceto, con los costes que manda el servidor): el botón `📐 Ampliar`; el rótulo `Ampliar el departamento`; `+ columna ({n} casillas) · {coste} 🪙` y `+ fila ({n} casillas) · {coste} 🪙`; `Volver`. Cuando ya mide 8 × 8: `Tu departamento ya no puede crecer más.`
  - Sin ningún gachamon: `Todavía no vive ningún gachamon contigo.`
  - Mientras carga y si no carga, lo que ya dicen la tienda y la mochila (el mensaje de siempre y «Volver a intentarlo»). Si al girar no cabe de ninguna otra forma, la frase que ya da el juego: `Ahí no cabe.`
  - La lista para quien no usa el dibujo: los rótulos `Tus gachamones`, `Muebles puestos`, `Guardados` y `¿Dónde?`; los botones `Mover`, `Girar`, `Guardar`, `Poner` y `Ponerlo ahí`; cada sitio, `fila {f}, columna {c}`, `pared izquierda, tramo {n}` o `pared derecha, tramo {n}`; cada mueble puesto, `{nombre}, en fila {f}, columna {c}` (o `{nombre}, en la pared izquierda, tramo {n}`).
  - La carta: el botón `Entendido`.
- **Lo que este plan decidió en nombre de Felipe** (se le enseñaron con el plan y lo aprobó el 2026-11-16):
  1. **En «Tu casa» la pantalla es el departamento**, no la del lugar de antes: ahí están los cuidados, la mochila y el pueblo. Los demás lugares siguen como hoy.
  2. Al poner algo desde guardados, **si no cabe como viene se prueba girado** (como en el boceto); «Girar» recorre las cuatro posiciones.
  3. **Acariciar sigue existiendo en casa**: tocar a un gachamon lo elige (su ficha queda abajo) y en su menú, junto a «Mover», está «Acariciar».
  4. **Lo de pared tiene dos imágenes, no cuatro**: una por cada pared del fondo, que es donde puede ir. Los muebles de suelo, las cuatro. Felipe lo eligió expresamente («Dos, una por pared»).
  5. **La página sirve la pieza reducida a la mitad** (casilla de 512 × 256), en un solo tamaño: con la pieza en 3 × 3, una pantalla de alta densidad pinta la casilla con unos 450 píxeles, y a la cuarta parte el dibujo se vería borroso. Los originales de 1024 × 512 quedan en `fuentes/pieza/`. Si el arte definitivo pesa demasiado para el teléfono, las copias servidas pueden pasar a otro formato sin tocar los originales.
  6. **El globo de lo que dice el gachamon** sale sólo sobre el que sale contigo (es lo que manda el servidor hoy).
  7. La carta del alcalde se ve **al entrar, antes que nada**, y se cierra con «Entendido».
  8. «Salir con él» contesta con **la misma frase que da hoy la Incubadora**, y la Incubadora sigue sirviendo para lo mismo hasta el plan 8.
  9. La ficha de un gachamon que no sale contigo **no ofrece el ropero**.
  10. **La poción de descanso rápido**, que sólo sirve para volver a competir, queda como las de fuerza y velocidad: no se usa ni se gasta desde la mochila (la Tienda ya no la vende por lo mismo).
  11. **Quién tapa a quién** se calcula de verdad (qué queda detrás de qué, mueble por mueble), no con la cuenta rápida del boceto, que dibujaba a un gachamon debajo de la cama que tiene al lado.

## Review Focus

1. **Tocar donde no hay nada que tocar**: fuera de la pieza, en el borde entre dos casillas, en la esquina de las dos paredes, con el departamento en 3 × 3 y en 8 × 8, en teléfono y en computador, con la densidad de píxeles en 1 y en 3. Se toca lo que se ve bajo el dedo: la cabeza de un gachamon es el gachamon, no la casilla de atrás. → Tasks 5 y 6.
2. **Un mueble donde no cabe o donde hay otro**: el cliente no marca como libre lo que el servidor rechazaría (capas, pared, bordes, girado), y si aun así el servidor dice que no, se ve su frase y la pieza queda como estaba. → Tasks 4 y 7.
3. **El gachamon que queda bajo un mueble**: si un mueble cae donde hay uno, se corre a la casilla libre más cercana; el avatar también; nadie queda encerrado dentro de un mueble ni fuera de la pieza, tampoco al ampliar o al llegar un estado nuevo. → Tasks 4 y 8.
4. **La respuesta que llega tarde o no llega**: tocar dos veces seguidas, cambiar de pestaña a mitad, quedarse sin red al ampliar (un solo cobro), una lectura vieja que llega después de una acción, salir de la pantalla con una petición en vuelo. → Tasks 6, 7 y 8.
5. **Sin el dibujo**: con teclado y lector de pantalla se puede hacer todo lo que se hace tocando (poner, mover, girar, guardar, elegir a un gachamon, cuidarlo, ampliar), y lo que cambia se anuncia. → Task 9.

**Sobre las pruebas de este plan.** Las de Python usan las ayudas vecinas: de `tests/ayudas_web.py`, `con_gachamon`, `ir`, `en_casa`, `con_monedas_web`, `poner_reloj`, `CABECERA` y `PUEBLO`; cada archivo web define, como ya hacen sus vecinos, `API = "/gachamon/api"`, `YO, G = identidad.de_cuenta_web(1), str(PUEBLO)` y `STATS = (15, 15, 15, 15)`; un segundo gachamon se crea como en `tests/test_web_acciones.py::_con_otro` (`db.crear(YO, G, "pollito", "Rulo", STATS, ahora, activa=False)`), aquí con la ayuda `con_otro(cliente) -> Criatura`. Las del cliente son de dos clases: las de `casillas.js`, puro, se importan directo; las de la pantalla montan un DOM y un `fetch` de mentira como `tests/js/tienda.test.mjs` y **manejan la pantalla por su lista** (la alternativa al dibujo), que tiene los mismos botones. Lo que manda son los nombres de las pruebas y sus aserciones.

Los departamentos de ejemplo de `tests/js/departamento.test.mjs`, escritos al principio del archivo con la forma exacta de `GET /departamento`:

- `DEPTO`: el de partida. 3 × 3 (`casillas: 9`), `comodidad: 82`, `tope: 100`, `camas: 1`, `gachamones: 1`, `ampliar: {ancho: 45, fondo: 45}`; puesta, una cama sencilla (`CAMA_ID`) en (0, 0) con giro 0, casillas `[[0, 0], [1, 0]]`; guardada, otra cama sencilla (`GUARDADA_ID`); `plantel: [PELUSA]`, que sale contigo.
- `CON_MACETA`: `DEPTO` más una maceta (`MACETA_ID`) puesta en (2, 2). `SIN_MACETA`: `DEPTO` con esa maceta en guardados.
- `CON_UN_CUADRO_GUARDADO`: `DEPTO` con un cuadro (`CUADRO_ID`, de pared, 1 tramo) en guardados.
- `CON_DOS`: `DEPTO` con `gachamones: 2` y `plantel: [PELUSA, RULO]` (Pelusa sale contigo). `CON_RULO_ACTIVO`: lo mismo con `plantel: [RULO, PELUSA]` y Rulo como el que sale.
- `PELUSA` y `RULO` tienen la forma de `estado.ficha` más `activo`; `ESTADO`, la de `GET /estado` en casa, con `gachamon: PELUSA`.

---

### Task 1: Lo que Felipe decidió tras el plan 4

**Files:**
- Modify: `economia.py` (el día del cambio), `web/carta.py`, `web/mochila.py`, `web/tienda.py`, `objetos.py`, `web/static/js/lugar.js` (una palabra), `README.md` y `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md` (lo que ya no está «por decidir»), y sus pruebas: `tests/test_dia_del_cambio.py`, `tests/test_web_carta.py`, `tests/test_web_mochila.py`, `tests/test_textos.py` o donde se fijen esas frases, `tests/test_web_cliente.py`

**Interfaces:**
- Produces:
  - `economia.MEJORA_DE_LAS_CASAS_DE_ANTES = 140`: el día del cambio, una casa de clave `mediana` o `grande` devuelve su precio de `PRECIO_DE_LAS_CASAS_DE_ANTES` **más** 140. La pequeña, su precio. `monedas_por_casas` de la carta lleva la suma ya con eso.
  - `web/carta.lineas_de`: con `tickets == 1`, la frase en singular; la línea de cada recluta usa el nombre de la especie tal cual (sin pasarlo a minúsculas).
  - `web/tienda.py`: `donde_sirve(objeto)` da `COMPETIR` también por las sopaipillas (`objeto.es_sopaipilla`), que no están a la venta, así que la Tienda no cambia; `_nota` pasa a ser pública, `nota_de(objeto) -> str | None` (con el `rename` de GitNexus, no a mano).
  - `web/mochila._uso`: lo que `tienda.donde_sirve` da por `COMPETIR` no se usa desde la mochila (`uso: None`) y lleva de nota `tienda.nota_de(objeto)`: la frase de la Tienda, no una copia. `POST /mochila/usar` de uno de ésos se rechaza en `web/mochila.py`, igual que hoy la semilla, sin gastarlo: `ok: False`, `clave: "no_se_usa"` y de `mensaje` esa misma nota.
  - `objetos.py` y `web/mochila.py`: las tres frases del huerto de las restricciones.
  - `lugar.js`: el cuidado `limpiar` se llama `Bañar`.

- [ ] **Step 1: Escribir las pruebas que fallan.**

```python
# tests/test_dia_del_cambio.py
def test_una_casa_mediana_o_grande_devuelve_140_mas():
    con_monedas(0)
    casa_de_antes("u1", "pequena"); casa_de_antes("u1", "mediana"); casa_de_antes("u1", "grande")
    el_cambio()
    assert economia.saldos("u1", "g1").asciicoins == 200 + 640 + 1340 == 2180
    assert db.carta_sin_ver("u1", "g1", CAMBIO)["monedas_por_casas"] == 2180

# tests/test_web_carta.py
def test_con_un_solo_ticket_la_carta_lo_dice_en_singular():
    lineas = carta.lineas_de({**TODO, "tickets": 1, "monedas_por_tickets": 40})
    assert "El refugio cerró. Te devolví 40 monedas por tu ticket." in lineas
    assert "El refugio cerró. Te devolví 80 monedas por tus tickets." in carta.lineas_de({**TODO, "tickets": 2, "monedas_por_tickets": 80})

def test_la_especie_del_recluta_va_con_su_mayuscula():
    nombre = esp.ESPECIES["pulpo"].nombre
    assert nombre[0].isupper()
    assert f"Tu {nombre} ahora se llama Brisa. Se puso el nombre solo, y se lo puedes cambiar una vez." in carta.lineas_de(TODO)

# tests/test_web_mochila.py
NO_SIRVE_AUN = "Sirve en las competencias, que todavía no están en la página."

@pytest.mark.parametrize("clave", ["fuerza_1d4", "velocidad_1d12", "descanso_rapido", "sopaipilla_rojo", "sopaipilla_arcoiris_1d6"])
def test_lo_que_solo_sirve_para_competir_no_se_usa_ni_se_gasta(cliente, monkeypatch, clave):
    poner_reloj(monkeypatch); con_gachamon(cliente); dar(YO, clave)
    fila = next(o for o in cliente.get(MOCHILA).json()["objetos"] if o["clave"] == clave)
    assert (fila["uso"], fila["nota"]) == (None, NO_SIRVE_AUN)
    r = usar(cliente, clave).json()
    assert (r["ok"], r["clave"], r["mensaje"]) == (False, "no_se_usa", NO_SIRVE_AUN)
    assert db.inventario(YO, G) == {clave: 1}                  # no se gastó

def test_los_textos_del_huerto_dicen_que_vuelve(cliente, monkeypatch):
    assert objetos.CATALOGO["semilla"].descripcion == (
        "Se planta en el huerto, que vuelve más adelante. Salen de 2 a 4 porotos, "
        "todos del mismo color al azar. Es la única forma de conseguir un color que no tengas.")
    for clave in ("poroto_rojo", "poroto_arcoiris"):
        assert objetos.CATALOGO[clave].descripcion.endswith(" El huerto y la cocina vuelven más adelante.")
    poner_reloj(monkeypatch); con_gachamon(cliente); dar(YO, "semilla")
    fila = next(o for o in cliente.get(MOCHILA).json()["objetos"] if o["clave"] == "semilla")
    assert fila["nota"] == "Se usa en el huerto, que vuelve más adelante."

# tests/test_web_cliente.py
def test_el_cuidado_de_aseo_se_llama_banar():
    lugar = _guion("lugar.js")
    assert "nombre: 'Bañar'" in lugar and "'Limpiar'" not in lugar and "accion: 'limpiar'" in lugar
```

  (`MOCHILA` es la ruta de `GET /mochila`, con el nombre que ya tenga en ese archivo. Las claves del arcoíris salen de `huerto.clave_de_poroto` y `huerto.clave_de_sopaipilla`: si no son exactamente `poroto_arcoiris` y `sopaipilla_arcoiris_1d6`, se usan las que den.)

- [ ] **Step 2: Verlas fallar.** Run: `./venv/bin/python -m pytest tests/test_dia_del_cambio.py tests/test_web_carta.py tests/test_web_mochila.py tests/test_web_cliente.py -q` — Expected: FAIL en las nuevas.
- [ ] **Step 3: Implementar** lo de Interfaces. Las pruebas de hoy que fijan 500 por una mediana, 1200 por una grande, «tu octopul» en minúsculas o las frases viejas del huerto se cambian por los valores nuevos; el informe las lista. El poroto arcoíris lleva la misma frase añadida que los de color.
- [ ] **Step 4: Los documentos.** En el README y en los pendientes, lo que estaba «por decidir» y ya se decidió (la casa mejorada, «por tus tickets», la especie en minúsculas, los textos del huerto, la mochila con lo que no sirve) pasa a contarse como decidido, con lo que se decidió.
- [ ] **Step 5: La suite entera.** Run: `./venv/bin/python -m pytest tests/ -q -p no:cacheprovider` — Expected: PASS, sin avisos nuevos.
- [ ] **Step 6: Commit** — `feat(reglas): lo que el dueño decidió tras la vivienda: 140 por casa mejorable, la mochila sin lo de competir, «Bañar» y las frases`.

---

### Task 2: Lo que la pantalla le pide al servidor

**Files:**
- Modify: `web/departamento.py`, `web/ficha.py`, `web/incubadora.py` (sólo para compartir su frase), `tests/test_web_departamento.py`, `tests/test_web_ficha.py`

**Interfaces:**
- Consumes: `db.plantel_al_dia(usuario_id, guild_id, ahora)`, `web.estado.ficha(criatura, ahora)`, `economia.cambiar_de_activo(usuario_id, guild_id, criatura_id, ahora)`, y lo que hoy contesta `POST /incubadora/sacar` (`web/incubadora._dicho`).
- Produces:
  - `GET /departamento` (y el `departamento` que devuelven poner, guardar, ampliar y salir) gana **`plantel`**: la lista de todos los gachamones vivos, el que sale contigo primero y después por id, cada uno con lo de `estado.ficha` (`id, nombre, especie, nombre_especie, emoji, etapa, nombre_etapa, nivel, genero, barras, cara, desfallecido, retrato, esperas, titulo…`) más **`activo: bool`**. `gachamones` sigue siendo el número.
  - Cada uno de los `puestos` gana **`ancho`** y **`fondo`**, los del catálogo (sin girar), como ya los traen los `guardados`: sin ellos el cliente no sabe qué ocuparía el mueble en otro sitio o con otro giro.
  - `POST /departamento/salir {gachamon_id}` → `{ok, clave, mensaje, departamento, estado}`. Pide estar en el departamento (`en_el_departamento`). Llama a `economia.cambiar_de_activo` y contesta **con las mismas frases y claves que `POST /incubadora/sacar`** (`web/incubadora._dicho`, que se mueve a donde las dos rutas lo usen; no se copia): «Ahora sales con {nombre}.», «{nombre} ya es tu gachamon activo.» (que es un sí) y `no_esta`. Un `gachamon_id` que no es un id, 422.
  - `GET /ficha?gachamon_id=<id>`: la ficha completa de ese gachamon, si es tuyo y está vivo; sin el parámetro, la del que sale contigo, como hoy. Gana **`es_el_activo: bool`**. De otro o inexistente: 409 `no_esta` «Ese gachamon ya no está.». Uno que no es un entero: 422.

- [ ] **Step 1: Escribir las pruebas que fallan.**

```python
# tests/test_web_departamento.py
def salir(cliente, gachamon_id):
    return cliente.post(f"{API}/departamento/salir", json={"gachamon_id": gachamon_id}, headers=CABECERA)

def test_el_departamento_trae_a_todos_con_sus_barras(cliente):
    otro = con_otro(cliente); en_casa(cliente)                 # Pelusa sale contigo; Rulo, no
    d = cliente.get(f"{API}/departamento").json()
    assert d["gachamones"] == 2
    assert [(g["nombre"], g["activo"]) for g in d["plantel"]] == [("Pelusa", True), ("Rulo", False)]
    assert d["plantel"][1]["id"] == otro.id
    for g in d["plantel"]:
        assert set(g["barras"]) == {"comida", "animo", "aseo"}
        assert set(g["esperas"]) >= {"alimentar", "jugar", "entrenar", "limpiar", "acariciar"}
        assert g["retrato"] and g["nombre_especie"] and g["nombre_etapa"]

def test_cada_mueble_puesto_dice_su_forma(cliente):
    con_gachamon(cliente); en_casa(cliente)
    cama = cliente.get(f"{API}/departamento").json()["puestos"][0]
    assert (cama["ancho"], cama["fondo"], cama["capa"]) == (2, 1, "bulto")

def test_salir_con_otro_desde_el_departamento(cliente):
    otro = con_otro(cliente); en_casa(cliente)
    r = salir(cliente, otro.id).json()
    assert (r["ok"], r["clave"], r["mensaje"]) == (True, None, "Ahora sales con Rulo.")
    assert r["estado"]["gachamon"]["nombre"] == "Rulo"
    assert [(g["nombre"], g["activo"]) for g in r["departamento"]["plantel"]] == [("Rulo", True), ("Pelusa", False)]
    otra_vez = salir(cliente, otro.id).json()                  # con el que ya sale: un sí, como en la Incubadora
    assert (otra_vez["ok"], otra_vez["mensaje"]) == (True, "Rulo ya es tu gachamon activo.")

def test_salir_pide_estar_en_el_departamento_y_un_id_de_verdad(cliente):
    con_gachamon(cliente); ir(cliente, "tienda")
    assert salir(cliente, 1).status_code == 409
    en_casa(cliente)
    for malo in ("1", 1.5, True, None):
        assert salir(cliente, malo).status_code == 422
    ajeno = salir(cliente, 999999).json()
    assert (ajeno["ok"], ajeno["clave"]) == (False, "no_esta")

# tests/test_web_ficha.py
def test_la_ficha_de_uno_que_no_sale_contigo(cliente, monkeypatch):
    poner_reloj(monkeypatch); otro = con_otro(cliente)
    suya = cliente.get(FICHA, params={"gachamon_id": otro.id}).json()
    assert (suya["gachamon"]["nombre"], suya["es_el_activo"]) == ("Rulo", False) and "estadisticas" in suya["detalle"]
    assert cliente.get(FICHA).json()["es_el_activo"] is True
    sin = cliente.get(FICHA, params={"gachamon_id": 999999})
    assert sin.status_code == 409 and sin.json()["detail"]["clave"] == "no_esta"
    assert cliente.get(FICHA, params={"gachamon_id": "x"}).status_code == 422

def test_la_ficha_del_gachamon_de_otra_persona_no_se_ve(cliente, monkeypatch):
    poner_reloj(monkeypatch); con_gachamon(cliente)
    ajeno = db.crear(identidad.de_cuenta_web(2), G, "pollito", "Ajeno", STATS, db.ahora_utc())
    r = cliente.get(FICHA, params={"gachamon_id": ajeno.id})
    assert r.status_code == 409 and r.json()["detail"]["clave"] == "no_esta"
```

  (`con_otro(cliente) -> Criatura` hace `con_gachamon(cliente)` y crea a Rulo con `db.crear(YO, G, "pollito", "Rulo", STATS, db.ahora_utc(), activa=False)`.)

- [ ] **Step 2: Verlas fallar.** Run: `./venv/bin/python -m pytest tests/test_web_departamento.py tests/test_web_ficha.py -q` — Expected: FAIL (`plantel` no existe; 404 en `/departamento/salir`).
- [ ] **Step 3: Implementar** lo de Interfaces. La frase de «salir» sale de la misma función que la de la Incubadora, movida a donde las dos puedan usarla.
- [ ] **Step 4: La suite entera.** Run: `./venv/bin/python -m pytest tests/ -q -p no:cacheprovider` — Expected: PASS.
- [ ] **Step 5: Commit** — `feat(web): el plantel en el departamento, «salir con él» desde ahí y la ficha de cualquiera`.

---

### Task 3: El arte de la pieza

**Files:**
- Create: `herramientas/pieza.py`, `fuentes/pieza/LEEME.md`, `tests/test_arte_pieza.py`
- Modify: `web/arte.py`, `herramientas/rellenos.py`, `web/static/datos/arte.json`, `web/static/arte/pieza/…` (los rellenos), `docs/arte/contrato.md`, `tests/test_arte.py`, `tests/js/arte.test.mjs`

**Interfaces:**
- Produces (en `web/arte.py`; todo lo que sirve la página es **la mitad** del original):
  - `CASILLA = (512, 256)`, `ALTURA = 512` (lo que sobresale un mueble o mide la pared), `REDUCCION = 2`, `ORIENTACIONES = ("se", "so", "no", "ne")` (por giro 0, 1, 2 y 3: cada giro es un cuarto de vuelta).
  - Una familia nueva, `pieza`, con estas piezas:

    | Ruta | Cuántas | Tamaño servido |
    |---|---|---|
    | `pieza/suelo.png` | 1 | 512 × 256 (una casilla) |
    | `pieza/pared-izquierda.png`, `pieza/pared-derecha.png` | 2 | 256 × 640 (un tramo: media casilla de ancho, 128 de pendiente y 512 de alto) |
    | `pieza/muebles/<clave>-<orientación>.png`, de cada mueble de suelo (`capa` `bulto` o `suelo`) | 4 por mueble | ancho `(a + f) × 256`; alto `(a + f) × 128`, más 512 si es `bulto` (`a` y `f` son su ancho y su fondo en casillas: 1 × 1 → 512 × 768 o 512 × 256; 2 × 1 → 768 × 896; 2 × 2 → 1024 × 1024, o 1024 × 512 la alfombra) |
    | `pieza/muebles/<clave>-se.png` y `-so.png`, de cada mueble de `pared` | 2 por mueble | ancho `tramos × 256`; alto `tramos × 128 + 512` |

    Con el catálogo de hoy (doce de suelo y tres de pared) son 57 piezas; el contrato pasa de 196 a 253.
  - `originales_de_la_pieza() -> tuple[Pieza, ...]`: las mismas rutas bajo `fuentes/`, a tamaño de original (por `REDUCCION`).
- Produces (`herramientas/pieza.py`, que se corre con `./venv/bin/python -m herramientas.pieza`): `reducir() -> list[str]`: por cada original que **exista** en `fuentes/pieza/…`, comprueba que mide exactamente lo que dice el contrato (si no, lo dice y no escribe nada) y escribe su copia reducida en `web/static/arte/pieza/…` (Pillow, `LANCZOS`). Devuelve las rutas escritas.
- `herramientas/rellenos.py` gana la rama de la familia `pieza`: dibuja el relleno **al tamaño servido** (una casilla lisa; un tramo de pared; para cada mueble, una caja de color sobre su huella con las primeras letras de su clave y **una marca en la cara hacia la que mira**, para que girar se note). Determinista. No se generan originales de relleno: en `fuentes/pieza/` sólo va lo que entregue el dibujante.
- **Cómo se coloca cada dibujo** (lo dice el contrato y lo usa el cliente): el de un mueble de suelo cubre a lo ancho exactamente su huella —de la esquina izquierda a la derecha del rombo que ocupa— y su borde de abajo coincide con la esquina de delante; el de un tramo de pared, o de un mueble de pared, cubre a lo ancho sus tramos y a lo alto toda la pared.
- `docs/arte/contrato.md` gana la sección «La pieza de tu departamento»: la casilla original de 1024 × 512; que no es pixel art; los nombres de archivo y los tamaños originales (los de la tabla por dos); las cuatro orientaciones y qué significa cada una (hacia dónde mira el frente del mueble: `se` abajo a la derecha, `so` abajo a la izquierda, `no` arriba a la izquierda, `ne` arriba a la derecha); que lo de pared lleva sólo `se` (colgado en la pared izquierda) y `so` (en la derecha); cómo se coloca; que los originales se dejan en `fuentes/pieza/` con el mismo nombre y después se corre la herramienta. Y se corrige lo que quede hablando de «el interior de cada casa».

- [ ] **Step 1: Escribir las pruebas que fallan**, en `tests/test_arte_pieza.py`:

```python
def test_la_pieza_tiene_su_familia_en_el_contrato():
    pieza = [p for p in arte.piezas() if p.familia == "pieza"]
    rutas = {p.ruta for p in pieza}
    assert {"pieza/suelo.png", "pieza/pared-izquierda.png", "pieza/pared-derecha.png"} <= rutas
    de_suelo = [m for m in dep.MUEBLES.values() if m.capa != dep.PARED]
    de_pared = [m for m in dep.MUEBLES.values() if m.capa == dep.PARED]
    assert len(pieza) == 3 + 4 * len(de_suelo) + 2 * len(de_pared)
    for m in de_suelo:
        assert {f"pieza/muebles/{m.clave}-{o}.png" for o in arte.ORIENTACIONES} <= rutas
    for m in de_pared:
        assert {f"pieza/muebles/{m.clave}-se.png", f"pieza/muebles/{m.clave}-so.png"} <= rutas
        assert f"pieza/muebles/{m.clave}-no.png" not in rutas

@pytest.mark.parametrize("ruta, tamano", [
    ("pieza/suelo.png", (512, 256)), ("pieza/pared-izquierda.png", (256, 640)),
    ("pieza/muebles/maceta-se.png", (512, 768)), ("pieza/muebles/felpudo-no.png", (512, 256)),
    ("pieza/muebles/cama_sencilla-so.png", (768, 896)), ("pieza/muebles/fuente-ne.png", (1024, 1024)),
    ("pieza/muebles/alfombra-se.png", (1024, 512)), ("pieza/muebles/cuadro-se.png", (256, 640)),
    ("pieza/muebles/cortinas-so.png", (512, 768)),
])
def test_cada_dibujo_mide_lo_que_ocupa(ruta, tamano):
    p = next(p for p in arte.piezas() if p.ruta == ruta)
    assert (p.ancho, p.alto) == tamano

def test_los_originales_miden_el_doble_de_lo_servido():
    servidas = {p.ruta: p for p in arte.piezas() if p.familia == "pieza"}
    for o in arte.originales_de_la_pieza():
        assert (o.ancho, o.alto) == (servidas[o.ruta].ancho * 2, servidas[o.ruta].alto * 2)
    assert next(o for o in arte.originales_de_la_pieza() if o.ruta == "pieza/suelo.png").ancho == 1024

def test_cada_dibujo_de_la_pieza_tiene_su_archivo_del_tamano_justo():
    for p in (p for p in arte.piezas() if p.familia == "pieza"):
        with Image.open(arte.RAIZ / p.ruta) as imagen:
            assert imagen.size == (p.ancho, p.alto), p.ruta

def test_las_cuatro_orientaciones_de_relleno_no_son_el_mismo_dibujo():
    datos = {o: (arte.RAIZ / f"pieza/muebles/maceta-{o}.png").read_bytes() for o in arte.ORIENTACIONES}
    assert len(set(datos.values())) == 4

def test_reducir_escribe_la_copia_de_un_original_y_rechaza_el_de_otro_tamano(tmp_path, monkeypatch):
    fuentes, servido = tmp_path / "fuentes", tmp_path / "arte"
    monkeypatch.setattr(pieza, "FUENTES", fuentes); monkeypatch.setattr(pieza, "SERVIDO", servido)
    (fuentes / "pieza").mkdir(parents=True)
    Image.new("RGBA", (1024, 512), (10, 200, 30, 255)).save(fuentes / "pieza/suelo.png")
    assert pieza.reducir() == ["pieza/suelo.png"]
    with Image.open(servido / "pieza/suelo.png") as chica:
        assert chica.size == (512, 256) and chica.getpixel((256, 128))[:3] == (10, 200, 30)
    Image.new("RGBA", (1000, 500)).save(fuentes / "pieza/suelo.png")
    with pytest.raises(ValueError, match="1024"):
        pieza.reducir()

def test_lo_servido_es_la_reduccion_de_su_original_si_lo_hay():
    # Nadie entrega un original y se olvida de correr la herramienta: los píxeles coinciden.
    for o in arte.originales_de_la_pieza():
        original = pieza.FUENTES / o.ruta
        if original.exists():
            assert pieza.reducida(original).tobytes() == Image.open(arte.RAIZ / o.ruta).convert("RGBA").tobytes(), o.ruta
```

- [ ] **Step 2: Verlas fallar.** Run: `./venv/bin/python -m pytest tests/test_arte_pieza.py -q` — Expected: FAIL (no hay familia `pieza`).
- [ ] **Step 3: Implementar** el contrato, la herramienta y la rama de los rellenos; generar los 57 rellenos y `arte.json` como se generan hoy (`herramientas.rellenos.generar`). `tests/test_arte.py` (tres sitios) y `tests/js/arte.test.mjs` pasan de 196 a 253 y cuentan la familia nueva.
- [ ] **Step 4: El contrato escrito** (`docs/arte/contrato.md`) y `fuentes/pieza/LEEME.md` (tres líneas: qué va ahí, con qué nombre y qué correr después).
- [ ] **Step 5: La suite entera.** Run: `./venv/bin/python -m pytest tests/ -q -p no:cacheprovider` — Expected: PASS.
- [ ] **Step 6: Commit** — `feat(arte): la pieza del departamento entra al contrato, con cuatro orientaciones por mueble y originales en fuentes/`.

---

### Task 4: La rejilla, en cuentas

**Files:**
- Create: `web/static/js/casillas.js`, `tests/js/casillas.test.mjs`

**Interfaces:**
- Produces (`casillas.js`, puro: sin DOM, sin reloj, sin red; el azar entra como función). `depto` es siempre lo que devuelve `GET /departamento`; `pieza`, uno de sus `puestos` o de sus `guardados` (los dos traen `id`, `ancho`, `fondo` y `capa`):
  - `huellaDe(forma, x, y, giro) -> [[i, j], …]`: la del servidor (`departamento.huella`), ordenada por `i` y después por `j`, que es como llegan las `casillas` de un mueble puesto. `forma` es `{ancho, fondo, capa}`. Lo de pared ocupa `ancho` tramos seguidos a lo largo de su pared (`y = -1`, la derecha; `x = -1`, la izquierda) y el giro no le cambia nada; lo demás, `ancho × fondo`, o `fondo × ancho` con giro 1 o 3.
  - `problemaAlPoner(depto, pieza, x, y, giro) -> 'no_cabe' | 'ocupado' | null`: la regla del servidor (`departamento.problema_al_poner`): fuera de la pieza —o lo de pared fuera de su pared, o en la esquina, o un mueble en la pared—, `'no_cabe'`; pisar a otro puesto **de su misma capa**, `'ocupado'`; no choca consigo mismo.
  - `giroParaPoner(depto, pieza, x, y, giro) -> number | null`: ese giro si cabe; si no, el siguiente que quepa, de cuarto en cuarto; `null` si ninguno.
  - `dondeCabe(depto, pieza, giro) -> [{x, y, giro}, …]`: cada sitio donde se puede poner, con el giro de `giroParaPoner` para ese sitio. En el suelo, en orden de lectura (fila a fila); en la pared, primero los tramos de la derecha y después los de la izquierda.
  - `ocupadas(depto) -> number`: cuántas casillas del suelo tienen algo puesto (un mueble sobre la alfombra no cuenta dos veces; lo de pared no cuenta).
  - `noSePisan(depto) -> Set<string>` (`"i,j"`): las casillas con un mueble que no se pisa. Sobre la alfombra y el felpudo se camina.
  - `camino(ancho, fondo, noSePisan, desde, hasta) -> [[i, j], …]`: el más corto de casilla en casilla (sin diagonales), sin contar `desde` y terminando en `hasta`; `[]` si no hay, si `hasta` no se pisa o si ya se está ahí. Las vecinas se prueban en este orden: `[i, j+1]`, `[i+1, j]`, `[i, j-1]`, `[i-1, j]`.
  - `libreMasCercana(ancho, fondo, noSePisan, desde) -> [i, j] | null`: `desde` si se pisa; si no, la más cercana que se pise (a igual distancia, la primera en orden de lectura); `null` si no queda ninguna.
  - `pasoSuelto(ancho, fondo, noSePisan, desde, azar) -> [i, j]`: adónde da un paso un gachamon que camina solo: una vecina que se pise, elegida con `azar()` (de 0 a 1), o `desde` si no tiene.
  - `sitiosDeEntrada(ancho, fondo, noSePisan, cuantos) -> [[i, j], …]`: dónde se para cada uno al entrar: las casillas que se pisan, desde el frente (por `i + j` de mayor a menor y, a igualdad, por `i` de menor a mayor). Devuelve `cuantos`; si hay menos casillas que gente, se repiten en ronda; si no queda ninguna, `[]`.
  - `lineaDeEstado(depto) -> string`: la frase de las restricciones.
  - `nombreDelSitio(x, y) -> string`: `fila {y + 1}, columna {x + 1}`; `pared izquierda, tramo {y + 1}`; `pared derecha, tramo {x + 1}`.

- [ ] **Step 1: Escribir las pruebas que fallan**, en `tests/js/casillas.test.mjs`. `depto(puestos, ancho = 3, fondo = 3)` arma el objeto con la forma de `GET /departamento`; las formas de ejemplo: `CAMA = {clave: 'cama_sencilla', ancho: 2, fondo: 1, capa: 'bulto'}`, `ALFOMBRA` 2 × 2 `suelo`, `MACETA` 1 × 1 `bulto`, `FELPUDO` 1 × 1 `suelo`, `CUADRO` 1 tramo `pared`, `CORTINAS` 2 tramos `pared`.

```js
test('la huella es la del servidor', () => {
  assert.deepEqual(c.huellaDe(CAMA, 1, 1, 0), [[1, 1], [2, 1]]);
  assert.deepEqual(c.huellaDe(CAMA, 1, 1, 1), [[1, 1], [1, 2]]);
  assert.deepEqual(c.huellaDe(CAMA, 1, 1, 2), c.huellaDe(CAMA, 1, 1, 0));
  assert.deepEqual(c.huellaDe(ALFOMBRA, 0, 0, 3), [[0, 0], [0, 1], [1, 0], [1, 1]]);
  assert.deepEqual(c.huellaDe(CORTINAS, 1, -1, 3), [[1, -1], [2, -1]]);
  assert.deepEqual(c.huellaDe(CORTINAS, -1, 0, 0), [[-1, 0], [-1, 1]]);
});

test('lo que el servidor rechazaría no cabe', () => {
  const d = depto([{ id: 1, ...ALFOMBRA, x: 0, y: 0, giro: 0, casillas: [[0, 0], [0, 1], [1, 0], [1, 1]] },
                   { id: 4, ...MACETA, x: 2, y: 2, giro: 0, casillas: [[2, 2]] },
                   { id: 5, ...CORTINAS, x: 0, y: -1, giro: 0, casillas: [[0, -1], [1, -1]] }]);
  const maceta = { id: 2, ...MACETA }, felpudo = { id: 3, ...FELPUDO }, cama = { id: 6, ...CAMA }, cuadro = { id: 7, ...CUADRO };
  assert.equal(c.problemaAlPoner(d, maceta, 1, 1, 0), null);            // encima de la alfombra
  assert.equal(c.problemaAlPoner(d, felpudo, 1, 1, 0), 'ocupado');      // dos cosas que se pisan
  assert.equal(c.problemaAlPoner(d, felpudo, 2, 2, 0), null);           // el felpudo bajo la maceta
  assert.equal(c.problemaAlPoner(d, maceta, 2, 2, 0), 'ocupado');
  assert.equal(c.problemaAlPoner(d, cama, 2, 0, 0), 'no_cabe');         // se sale por una casilla
  assert.equal(c.problemaAlPoner(d, cama, 2, 0, 1), null);              // girada, sí
  assert.equal(c.problemaAlPoner(d, cama, 0, -1, 0), 'no_cabe');        // un mueble no va en la pared
  assert.equal(c.problemaAlPoner(d, cuadro, 1, -1, 0), 'ocupado');      // ahí están las cortinas
  assert.equal(c.problemaAlPoner(d, cuadro, 2, -1, 0), null);
  assert.equal(c.problemaAlPoner(d, cuadro, -1, 3, 0), 'no_cabe');      // más allá del largo de la pared
  assert.equal(c.problemaAlPoner(d, cuadro, -1, -1, 0), 'no_cabe');     // la esquina
  assert.equal(c.problemaAlPoner(d, cuadro, 1, 1, 0), 'no_cabe');       // lo de pared no va en el suelo
  assert.equal(c.problemaAlPoner(d, d.puestos[1], 2, 2, 1), null);      // girar en su sitio no choca consigo mismo
});

test('dónde cabe y con qué giro', () => {
  const d = depto([{ id: 1, ...CAMA, x: 0, y: 0, giro: 0, casillas: [[0, 0], [1, 0]] }]);
  const otra = { id: 2, ...CAMA };
  assert.equal(c.giroParaPoner(d, otra, 0, 1, 0), 0);
  assert.equal(c.giroParaPoner(d, otra, 2, 0, 0), 1);                   // no cabe a lo ancho: se prueba girada
  assert.equal(c.giroParaPoner(d, otra, 0, 0, 0), null);
  assert.deepEqual(c.dondeCabe(d, otra, 0), [
    { x: 2, y: 0, giro: 1 }, { x: 0, y: 1, giro: 0 }, { x: 1, y: 1, giro: 0 },
    { x: 2, y: 1, giro: 1 }, { x: 0, y: 2, giro: 0 }, { x: 1, y: 2, giro: 0 },
  ]);
  assert.deepEqual(c.dondeCabe(d, { id: 3, ...CORTINAS }, 0), [
    { x: 0, y: -1, giro: 0 }, { x: 1, y: -1, giro: 0 }, { x: -1, y: 0, giro: 0 }, { x: -1, y: 1, giro: 0 },
  ]);
});

test('las casillas ocupadas no cuentan dos veces la de la alfombra', () => {
  const d = depto([{ id: 1, ...ALFOMBRA, x: 0, y: 0, giro: 0, casillas: [[0, 0], [0, 1], [1, 0], [1, 1]] },
                   { id: 2, ...MACETA, x: 1, y: 1, giro: 0, casillas: [[1, 1]] },
                   { id: 3, ...CORTINAS, x: 0, y: -1, giro: 0, casillas: [[0, -1], [1, -1]] }]);
  assert.equal(c.ocupadas(d), 4);
  assert.deepEqual([...c.noSePisan(d)], ['1,1']);
});

test('el camino rodea los muebles', () => {
  const muro = new Set(['1,0', '1,1']);
  assert.deepEqual(c.camino(3, 3, muro, [0, 0], [2, 0]), [[0, 1], [0, 2], [1, 2], [2, 2], [2, 1], [2, 0]]);
  assert.deepEqual(c.camino(3, 3, new Set(), [0, 0], [0, 0]), []);
  assert.deepEqual(c.camino(3, 3, muro, [0, 0], [1, 1]), []);            // sobre un mueble no se para nadie
  assert.deepEqual(c.camino(3, 3, new Set(['1,0', '1,1', '1,2']), [0, 0], [2, 0]), []);   // encerrado
});

test('quien queda bajo un mueble se corre a la libre más cercana', () => {
  const muro = new Set(['1,1']);
  assert.deepEqual(c.libreMasCercana(3, 3, muro, [0, 0]), [0, 0]);
  assert.deepEqual(c.libreMasCercana(3, 3, muro, [1, 1]), [1, 0]);
  const todo = new Set(); for (let i = 0; i < 3; i += 1) for (let j = 0; j < 3; j += 1) todo.add(`${i},${j}`);
  assert.equal(c.libreMasCercana(3, 3, todo, [1, 1]), null);
  assert.deepEqual(c.libreMasCercana(3, 3, new Set(), [7, 7]), [2, 2]);   // la pieza cambió de tamaño
});

test('un gachamon suelto da un paso a una vecina que se pise', () => {
  assert.deepEqual(c.pasoSuelto(3, 3, new Set(['1,0']), [0, 0], () => 0), [0, 1]);
  assert.deepEqual(c.pasoSuelto(3, 3, new Set(['1,0', '0,1']), [0, 0], () => 0.99), [0, 0]);
});

test('al entrar se reparten desde el frente', () => {
  const cama = new Set(['0,0', '1,0']);
  assert.deepEqual(c.sitiosDeEntrada(3, 3, cama, 3), [[2, 2], [1, 2], [2, 1]]);
  const casiTodo = new Set(['0,0', '1,0', '2,0', '0,1', '1,1', '2,1', '0,2', '1,2']);
  assert.deepEqual(c.sitiosDeEntrada(3, 3, casiTodo, 3), [[2, 2], [2, 2], [2, 2]]);   // no hay más: comparten
  assert.deepEqual(c.sitiosDeEntrada(3, 3, new Set([...casiTodo, '2,2']), 3), []);     // ni una casilla libre
});

test('la línea bajo la pieza', () => {
  const d = { ancho: 4, fondo: 4, casillas: 16, comodidad: 88, tope: 106, camas: 4, gachamones: 3,
              puestos: [{ id: 1, ...CAMA, x: 0, y: 0, giro: 0, casillas: [[0, 0], [1, 0]] }] };
  assert.equal(c.lineaDeEstado(d), '4 × 4 · 2 de 16 casillas · camas 4 · gachamones 3 · comodidad 88 de 106');
});

test('cada sitio tiene su nombre', () => {
  assert.equal(c.nombreDelSitio(1, 0), 'fila 1, columna 2');
  assert.equal(c.nombreDelSitio(-1, 2), 'pared izquierda, tramo 3');
  assert.equal(c.nombreDelSitio(0, -1), 'pared derecha, tramo 1');
});
```

- [ ] **Step 2: Verlas fallar.** Run: `node --test tests/js/casillas.test.mjs` — Expected: FAIL (no existe el módulo).
- [ ] **Step 3: Implementar `casillas.js`** con las firmas de arriba. `camino` es una búsqueda a lo ancho.
- [ ] **Step 4: Contrastar con el servidor.** Una prueba de Python nueva, `tests/test_casillas_cliente.py`, que se salta sin Node: para un departamento de 4 × 3 con una alfombra, una cama y unas cortinas puestas, recorre cada mueble del catálogo en cada sitio (de `-1` a `ancho`, de `-1` a `fondo`) y cada giro, y comprueba que `problemaAlPoner` del cliente (corrido con `node --input-type=module`, que recibe el caso por la entrada y contesta JSON) dice lo mismo que `departamento.problema_al_poner`, y que `huellaDe` da las mismas casillas que `departamento.huella`. Es lo que impide que el cliente marque como libre lo que el servidor rechaza.
- [ ] **Step 5: Verlas pasar.** Run: `node --test tests/js/casillas.test.mjs && ./venv/bin/python -m pytest tests/test_casillas_cliente.py -q` — Expected: PASS.
- [ ] **Step 6: Commit** — `feat(web): la rejilla del departamento en cuentas: qué cabe, dónde y por dónde se camina`.

---

### Task 5: La pieza proyectada y el toque

**Files:**
- Create: `web/static/js/proyeccion.js`, `tests/js/proyeccion.test.mjs`

**Interfaces:**
- Consumes: de `casillas.js`, `huellaDe`.
- Produces (`proyeccion.js`, puro). `m` es siempre lo que devuelve `medir`; las medidas, en píxeles de pantalla (CSS):
  - `ORIENTACIONES = ['se', 'so', 'no', 'ne']`.
  - `medir(anchoPx, altoPx, ancho, fondo) -> {tw, th, ox, oy, pared}`: la casilla más grande que deja ver la pieza entera con sus paredes. Con `suma = ancho + fondo`: `tw = min(2 * (anchoPx - 28) / suma, (altoPx - 34) / (1 + suma / 4))`, `th = tw / 2`, `pared = tw`, `ox = anchoPx / 2 - (ancho - fondo) * tw / 4`, `oy = 16 + pared`.
  - `proyectar(m, i, j, h = 0) -> [x, y]`: `[m.ox + (i - j) * m.tw / 2, m.oy + (i + j) * m.th / 2 - h]`.
  - `casillaEn(m, x, y, ancho, fondo) -> [i, j] | null`: la casilla del suelo que contiene ese punto; `null` fuera de la pieza.
  - `tramoEn(m, x, y, ancho, fondo) -> [i, j] | null`: el tramo de pared que contiene ese punto, con las coordenadas del servidor: en la pared izquierda (a lo largo del fondo) `[-1, j]`; en la derecha (a lo largo del ancho) `[i, -1]`.
  - `cajaDelMueble(m, forma, x, y, giro) -> {x, y, ancho, alto}`: dónde se pinta su dibujo (la regla del contrato). En el suelo: a lo ancho, de la esquina izquierda a la derecha de su huella; el borde de abajo, en la esquina de delante; lo que no se pisa sobresale `m.pared` hacia arriba. En la pared: a lo ancho sus tramos, y a lo alto la pared entera más su pendiente.
  - `cajaDelGachamon(m, i, j) -> {x, y, ancho, alto}`: un cuadrado de lado `0.8 * m.tw`, centrado a lo ancho en el centro de la casilla y con el borde de abajo `m.th / 4` por debajo de ese centro.
  - `rutaDelMueble(clave, capa, x, y, giro) -> string`: `pieza/muebles/<clave>-<orientación>.png`; en el suelo, `ORIENTACIONES[giro]`; en la pared, `so` si `y === -1` y `se` si `x === -1`.
  - `ordenDePintado(cosas) -> cosas`: una copia (con los mismos objetos) ordenada de atrás hacia adelante. Cada cosa es `{tipo: 'suelo' | 'mueble' | 'gachamon' | 'tu', i, j, a, f}`: la caja que ocupa en el suelo, `[i, i + a) × [j, j + f)`; `a` y `f` valen 1 si faltan, e `i` y `j` pueden ser fraccionarios. Lo de `suelo` (lo que se pisa) va primero, en el orden en que llegó. Lo demás **no** se ordena con una clave —la cuenta del boceto falla junto a un mueble de más de una casilla—, sino por quién tapa a quién: **A va antes que B** si A acaba donde B empieza, o antes, en alguno de los dos ejes (`A.i + A.a <= B.i` o `A.j + A.f <= B.j`) y B no cumple lo mismo respecto de A. Se va sacando, de entre lo que ya no tiene nada pendiente detrás, lo de menor `i + j + (a + f) / 2`; a igualdad, tú vas después de un gachamon, y si no, se respeta el orden de llegada. Si alguna vez no queda nada sin pendientes (dos que se cruzan a medio paso), se saca igual lo de menor cuenta: nunca se queda sin terminar.
  - `queSeToco(m, depto, gachamones, x, y) -> objeto | null`: **lo que se ve bajo el dedo**, de delante hacia atrás. `gachamones` es `[{id, i, j}]`, dónde está parado cada uno.
    1. **Primero los gachamones**: si el punto cae en la `cajaDelGachamon` de alguno, `{tipo: 'gachamon', id}`; si cae en la de varios, el que esté más adelante según `ordenDePintado`. Ganan también a un mueble que tengan delante: a un gachamon siempre se le puede tocar.
    2. Si no, un mueble que no se pisa, si el punto cae en su silueta —la de la caja que se levanta `m.pared` sobre su huella, no el rectángulo que la envuelve—: el que esté más adelante. `{tipo: 'mueble', id}`.
    3. Si no, la pared: `{tipo: 'mueble', id}` si ese tramo tiene algo colgado; si no, `{tipo: 'tramo', i, j}`.
    4. Si no, el suelo: `{tipo: 'casilla', i, j}`, con `mueble: id` si en esa casilla hay algo que se pisa.
    5. Fuera de todo, `null`.
    Tu avatar no se toca: el toque lo atraviesa.

- [ ] **Step 1: Escribir las pruebas que fallan**, en `tests/js/proyeccion.test.mjs` (las formas de ejemplo, las de la Task 4):

```js
const cerca = (a, b) => Math.abs(a - b) < 1e-9;

test('la casilla se ajusta al tamaño de la pieza', () => {
  assert.ok(Math.abs(p.medir(380, 310, 3, 3).tw - 110.4) < 1e-6);
  assert.equal(p.medir(380, 310, 8, 8).tw, 44);
  const m = p.medir(380, 310, 4, 2);
  assert.deepEqual([m.th, m.pared], [m.tw / 2, m.tw]);
  assert.ok(cerca(m.ox, 190 - 2 * m.tw / 4));
});

test('toda la pieza cabe en el lienzo, del 3 × 3 al 8 × 8', () => {
  for (let ancho = 3; ancho <= 8; ancho += 1) for (let fondo = 3; fondo <= 8; fondo += 1) {
    const m = p.medir(380, 310, ancho, fondo);
    const esquinas = [p.proyectar(m, 0, 0, m.pared), p.proyectar(m, ancho, 0, m.pared), p.proyectar(m, 0, fondo, m.pared),
                      p.proyectar(m, ancho, 0), p.proyectar(m, 0, fondo), p.proyectar(m, ancho, fondo)];
    for (const [x, y] of esquinas) assert.ok(x >= 0 && x <= 380 && y >= 0 && y <= 310, `${ancho}×${fondo}`);
  }
});

test('el centro de cada casilla cae en su casilla', () => {
  for (const [ancho, fondo] of [[3, 3], [8, 8], [8, 3], [4, 7]]) {
    const m = p.medir(1040, 520, ancho, fondo);
    for (let i = 0; i < ancho; i += 1) for (let j = 0; j < fondo; j += 1) {
      const [x, y] = p.proyectar(m, i + 0.5, j + 0.5);
      assert.deepEqual(p.casillaEn(m, x, y, ancho, fondo), [i, j]);
    }
  }
});

test('fuera de la pieza no hay casilla', () => {
  const m = p.medir(380, 310, 3, 3);
  for (const [i, j] of [[-0.2, 1], [1, -0.2], [3.1, 1], [1, 3.1], [-5, -5]]) {
    const [x, y] = p.proyectar(m, i, j);
    assert.equal(p.casillaEn(m, x, y, 3, 3), null);
  }
});

test('las paredes tienen sus tramos', () => {
  const m = p.medir(380, 310, 4, 3);
  let [x, y] = p.proyectar(m, 0, 1.5, m.pared / 2);          // pared izquierda, a media altura, tramo 1
  assert.deepEqual(p.tramoEn(m, x, y, 4, 3), [-1, 1]);
  [x, y] = p.proyectar(m, 2.5, 0, m.pared / 2);              // pared derecha, tramo 2
  assert.deepEqual(p.tramoEn(m, x, y, 4, 3), [2, -1]);
  [x, y] = p.proyectar(m, 1.5, 1.5);                         // el suelo no es pared
  assert.equal(p.tramoEn(m, x, y, 4, 3), null);
  [x, y] = p.proyectar(m, 0, 3.5, m.pared / 2);              // más allá del largo de la pared
  assert.equal(p.tramoEn(m, x, y, 4, 3), null);
  [x, y] = p.proyectar(m, 2.5, 0, m.pared * 1.2);            // por encima de la pared
  assert.equal(p.tramoEn(m, x, y, 4, 3), null);
});

test('el dibujo de un mueble cubre su huella y sobresale hacia arriba', () => {
  const m = p.medir(1040, 520, 4, 4);
  const caja = p.cajaDelMueble(m, CAMA, 1, 2, 0);                      // ocupa (1, 2) y (2, 2)
  assert.ok(cerca(caja.x, p.proyectar(m, 1, 3)[0]));                    // la esquina izquierda de la huella
  assert.ok(cerca(caja.ancho, 3 * m.tw / 2));                           // (ancho + fondo) medias casillas
  assert.ok(cerca(caja.y + caja.alto, p.proyectar(m, 3, 3)[1]));        // el borde de abajo, en la esquina de delante
  assert.ok(cerca(caja.alto, 3 * m.th / 2 + m.pared));
  const girada = p.cajaDelMueble(m, CAMA, 1, 2, 1);                     // ocupa (1, 2) y (1, 3)
  assert.ok(cerca(girada.ancho, caja.ancho) && cerca(girada.alto, caja.alto));
  assert.ok(cerca(p.cajaDelMueble(m, ALFOMBRA, 0, 0, 0).alto, 4 * m.th / 2));   // lo que se pisa no sobresale
});

test('lo de pared se pinta sobre sus tramos', () => {
  const m = p.medir(1040, 520, 4, 4);
  const derecha = p.cajaDelMueble(m, CUADRO, 2, -1, 0);
  assert.ok(cerca(derecha.x, m.ox + m.tw) && cerca(derecha.ancho, m.tw / 2));
  assert.ok(cerca(derecha.y, m.oy + m.th - m.pared) && cerca(derecha.alto, m.pared + m.th / 2));
  const izquierda = p.cajaDelMueble(m, CORTINAS, -1, 1, 0);             // tramos 1 y 2 de la izquierda
  assert.ok(cerca(izquierda.x, m.ox - 3 * m.tw / 2) && cerca(izquierda.ancho, m.tw));
  assert.ok(cerca(izquierda.y, m.oy + m.th / 2 - m.pared) && cerca(izquierda.alto, m.pared + m.th));
});

test('cada mueble pide el dibujo de hacia dónde mira', () => {
  assert.equal(p.rutaDelMueble('maceta', 'bulto', 1, 1, 0), 'pieza/muebles/maceta-se.png');
  assert.equal(p.rutaDelMueble('maceta', 'bulto', 1, 1, 3), 'pieza/muebles/maceta-ne.png');
  assert.equal(p.rutaDelMueble('cuadro', 'pared', 2, -1, 0), 'pieza/muebles/cuadro-so.png');
  assert.equal(p.rutaDelMueble('cuadro', 'pared', -1, 2, 2), 'pieza/muebles/cuadro-se.png');
});

const antes = (orden, x, y) => orden.indexOf(x) < orden.indexOf(y);

test('lo de atrás se pinta antes', () => {
  const alfombra = { tipo: 'suelo', i: 2, j: 2, a: 2, f: 2 };
  const maceta = { tipo: 'mueble', i: 1, j: 0, a: 1, f: 1 };
  const detras = { tipo: 'gachamon', i: 0, j: 0 }, delante = { tipo: 'gachamon', i: 1, j: 1 };
  const tu = { tipo: 'tu', i: 3, j: 3 };
  const orden = p.ordenDePintado([tu, delante, maceta, detras, alfombra]);
  assert.equal(orden.length, 5);
  assert.equal(orden[0], alfombra);                                  // lo que se pisa, primero, aunque esté delante
  assert.ok(antes(orden, detras, maceta) && antes(orden, maceta, delante) && antes(orden, delante, tu));
});

test('junto a un mueble largo, quien está delante de su cara se pinta después', () => {
  const cama = { tipo: 'mueble', i: 0, j: 0, a: 1, f: 2 };           // girada: a lo largo del fondo
  const alLado = { tipo: 'gachamon', i: 1, j: 0 };                   // la cuenta del boceto lo pintaba debajo
  const alPie = { tipo: 'gachamon', i: 0, j: 2 };
  const fuente = { tipo: 'mueble', i: 2, j: 2, a: 2, f: 2 };
  const juntoALaFuente = { tipo: 'tu', i: 4, j: 2 };
  const orden = p.ordenDePintado([juntoALaFuente, alPie, fuente, alLado, cama]);
  assert.ok(antes(orden, cama, alLado) && antes(orden, cama, alPie));
  assert.ok(antes(orden, fuente, juntoALaFuente) && antes(orden, alLado, fuente));
});

test('dos en la misma casilla o a medio paso no lo dejan sin terminar', () => {
  const g = { tipo: 'gachamon', i: 1, j: 1 }, tu = { tipo: 'tu', i: 1, j: 1 };
  assert.deepEqual(p.ordenDePintado([tu, g]), [g, tu]);
  const cruzando = [{ tipo: 'gachamon', i: 1.5, j: 1 }, { tipo: 'gachamon', i: 1, j: 1.5 }, { tipo: 'mueble', i: 2, j: 2 }];
  assert.equal(p.ordenDePintado(cruzando).length, 3);
});

// Un 4 × 4 con una maceta en (2, 2), un felpudo en (3, 0), un cuadro en el tramo 1 de la pared derecha
// y un gachamon parado en (1, 1), justo detrás de la maceta.
const PIEZA = depto([{ id: 7, ...MACETA, x: 2, y: 2, giro: 0, casillas: [[2, 2]] },
                     { id: 9, ...FELPUDO, x: 3, y: 0, giro: 0, casillas: [[3, 0]] },
                     { id: 11, ...CUADRO, x: 1, y: -1, giro: 0, casillas: [[1, -1]] }], 4, 4);
const GENTE = [{ id: 3, i: 1, j: 1 }];
const M = p.medir(1040, 520, 4, 4);
const toco = (i, j, h = 0) => p.queSeToco(M, PIEZA, GENTE, ...p.proyectar(M, i, j, h));

test('se toca lo que se ve', () => {
  assert.deepEqual(toco(0.5, 3.5), { tipo: 'casilla', i: 0, j: 3 });
  assert.deepEqual(toco(1.5, 1.5), { tipo: 'gachamon', id: 3 });                    // sus pies
  assert.deepEqual(toco(1.5, 1.5, 0.5 * M.tw), { tipo: 'gachamon', id: 3 });        // su cabeza, sobre la casilla de atrás
  assert.deepEqual(toco(2.5, 2.5), { tipo: 'mueble', id: 7 });                      // el pie de la maceta
  assert.deepEqual(toco(2.95, 2.05, 0.5 * M.tw), { tipo: 'mueble', id: 7 });        // su costado, a media altura
  assert.deepEqual(toco(2.5, 2.5, 0.75 * M.tw), { tipo: 'gachamon', id: 3 });       // donde se cruzan, el gachamon
  assert.deepEqual(toco(3.5, 0.5), { tipo: 'casilla', i: 3, j: 0, mueble: 9 });     // lo que se pisa
  assert.deepEqual(toco(1.5, 0, M.pared / 2), { tipo: 'mueble', id: 11 });          // el cuadro
  assert.deepEqual(toco(3.5, 0, M.pared / 2), { tipo: 'tramo', i: 3, j: -1 });
  assert.equal(p.queSeToco(M, PIEZA, GENTE, 2, 2), null);                           // una esquina del lienzo
});

test('de dos gachamones que se tapan, el de delante', () => {
  const dos = [{ id: 1, i: 1, j: 1 }, { id: 2, i: 2, j: 2 }];
  const punto = p.proyectar(M, 2.5, 2.5, 0.6 * M.tw);                               // la cabeza del de delante, sobre el de atrás
  assert.deepEqual(p.queSeToco(M, depto([], 4, 4), dos, ...punto), { tipo: 'gachamon', id: 2 });
  assert.deepEqual(p.queSeToco(M, depto([], 4, 4), dos.slice().reverse(), ...punto), { tipo: 'gachamon', id: 2 });
});

test('la esquina vacía del recuadro de un mueble no es el mueble', () => {
  const caja = p.cajaDelMueble(M, MACETA, 2, 2, 0);
  const ahi = p.queSeToco(M, PIEZA, [], caja.x + 2, caja.y + 2);
  assert.ok(ahi === null || ahi.tipo !== 'mueble' || ahi.id !== 7);
});
```

- [ ] **Step 2: Verlas fallar.** Run: `node --test tests/js/proyeccion.test.mjs` — Expected: FAIL (no existe el módulo).
- [ ] **Step 3: Implementar `proyeccion.js`.** `casillaEn` es la inversa de `proyectar`: con `u = (x - ox) / (tw / 2)` y `v = (y - oy) / (th / 2)`, `i = floor((v + u) / 2)` y `j = floor((v - u) / 2)`. La silueta de un mueble que no se pisa: bajar por la pantalla desde el punto es avanzar por la diagonal del suelo, así que el punto está en ella si, partiendo de su `(i, j)` del suelo sin redondear y sumándole a los dos lo mismo, de 0 a `pared / th`, se entra en su huella.
- [ ] **Step 4: Verlas pasar.** Run: `node --test tests/js/proyeccion.test.mjs` — Expected: PASS.
- [ ] **Step 5: Commit** — `feat(web): la pieza proyectada: dónde se pinta cada cosa, quién tapa a quién y qué se tocó`.

---

### Task 6: La pieza en pantalla

**Files:**
- Create: `web/static/js/pieza.js`, `web/static/js/departamento.js`, `tests/js/departamento.test.mjs`
- Modify: `web/static/js/pantallas.js`, `web/static/js/principal.js`, `web/static/estilo.css`, `tests/js/pantallas.test.mjs`, `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: `casillas.js` (Task 4) y `proyeccion.js` (Task 5); `GET /departamento` con `plantel` y la forma de cada puesto (Task 2); el arte `pieza/…` (Task 3); de hoy, `api.js` (`pedir`, `conReintentos`, `nuevoEvento`), `arte.js` (`cargar`, `faltante`, `olvidarLasQueFaltan`), `avatar.js` (`cargarAvatar`, `dibujarAvatar`, `poseAlCaminar`), `articulos.js` (`cabeceraConSaldos`, `zonaDeAviso`, `mensajeDe`), `dom.js`.
- Produces:
  - `pantallas.siguiente(...)`: donde hoy contesta `'lugar'`, si el lugar ofrece `departamento` contesta **`'departamento'`**; `ofreceElDepartamento(lugar)` se exporta. `principal.js` la monta: `departamento(destino, estado, seguir)`.
  - `pieza.js`: `dibujarPieza(ctx, m, escena)`: pinta de atrás hacia adelante las paredes (un tramo por casilla, con `cajaDelMueble` de un tramo), el suelo (una casilla por casilla), lo colgado en la pared y, en el orden de `ordenDePintado`, lo que se pisa, los muebles, los gachamones (su retrato en su `cajaDelGachamon`, con su sombra) y tu avatar; encima de todo y translúcidas, las marcas: `escena.libres` (las casillas o tramos donde se puede poner lo que se lleva en la mano) y `escena.elegido` (la huella de lo elegido). `escena` es `{depto, cargadas, gachamones: [{id, i, j, retrato, activo}], tu: {i, j, pose, espejo} | null, libres, elegido}`; las posiciones pueden ser fraccionarias. Lo de la pieza se pinta con suavizado (`imageSmoothingEnabled = true`); el avatar y los retratos, sin él. Un dibujo que falta se pinta con `faltante`, nunca con otro.
  - `departamento(contenedor, estado, seguir)`: la pantalla. En este paso:
    - la barra con «📍» y el nombre del lugar y los saldos; el lienzo de la pieza (`aria-hidden`); **la línea bajo la pieza** (`p.pieza-linea`, con `lineaDeEstado`); la zona de aviso (`role="status"`, clase `aviso`); y las salidas `🎒 Mochila` y `🗺️ Pueblo`, como en el lugar;
    - el lienzo se mide con `medir` según su tamaño en pantalla (`getBoundingClientRect()`), se pinta a la densidad de píxeles del aparato (de 1 a 3) y se vuelve a medir cuando cambia de tamaño;
    - pide `GET departamento` al entrar, cada 30 segundos y al volver a la pestaña; **una lectura que salió antes que una acción no pisa lo que la acción dejó**; un 401 o un 409 se va de la pantalla con `seguir()`; la primera carga usa la pieza común de `articulos.js` que ya usan la tienda y la mochila: lo que enseña mientras carga y, si falla, el mensaje de `mensajeDe` en un `role="alert"` y «Volver a intentarlo»; una relectura que falla no borra la pieza ni dice nada;
    - el lienzo escucha `click`; el punto, relativo a `getBoundingClientRect()`, pasa por `queSeToco`. En este paso sólo se camina: tocar una casilla que se pisa lleva al avatar hasta ahí por `camino(...)`, de casilla en casilla, con `requestAnimationFrame` sólo mientras algo se mueve; tocar otra a mitad cambia el destino; con movimiento reducido, aparece. El avatar parte en `sitiosDeEntrada(...)[0]`; si no hay ninguna casilla que se pise, no se dibuja.
  - En el computador (`#juego[data-pantalla="departamento"]`, desde 900 px): la pieza a la izquierda, grande, con la línea debajo; a la derecha, lo demás.

- [ ] **Step 1: Escribir las pruebas que fallan.** El DOM y el `fetch` de mentira de `tests/js/departamento.test.mjs` se copian de `tests/js/tienda.test.mjs` y se amplían con lo que falta: un lienzo que mide 380 × 310 (`getBoundingClientRect`), `requestAnimationFrame`, `setTimeout` y `setInterval` que no corren solos, `matchMedia` (sin movimiento reducido), `ResizeObserver`, y un servidor al que se le dice qué contestar (`servidor.responde(ruta, cuerpo)`, `servidor.falla(ruta)`, `servidor.retiene(ruta)`, que devuelve la función que suelta esa respuesta). `abrir(depto, estado = ESTADO, { movimientoReducido = false } = {})` monta la pantalla con ese `GET departamento` y devuelve `{pantalla, pedidos, servidor, seguido, documento}`; `pedidos` es la lista de `[ruta, cuerpo]`. `tocar(boton)` hace `click` y espera a que se asiente lo que desencadena. `tocarCasilla(pantalla, i, j)` hace `click` en el lienzo en el centro de esa casilla (con `medir(380, 310, …)` y `proyectar`), y `tocarTramo(pantalla, i, j)`, a media altura de ese tramo.

```js
// tests/js/pantallas.test.mjs (sustituye a la que hoy fija que «departamento» da «lugar»; `sesion`, `cuenta`, `jugando` y `en` son los del archivo)
test('en «Tu casa» la pantalla es el departamento', () => {
  const enCasa = { ...jugando, lugar: { clave: 'casa', nombre: 'Tu casa', ofrece: ['departamento'] } };
  for (const vista of [undefined, 'lugar', 'tienda', 'incubadora', 'departamento', 'otra cosa']) {
    assert.equal(siguiente(sesion, cuenta, enCasa, vista), 'departamento');
  }
  for (const vista of ['pueblo', 'mochila', 'ficha', 'ropero']) assert.equal(siguiente(sesion, cuenta, enCasa, vista), vista);
  assert.equal(siguiente(sesion, cuenta, en([]), undefined), 'lugar');
  assert.equal(siguiente(sesion, cuenta, en(['tienda']), 'departamento'), 'lugar');
});

// tests/js/departamento.test.mjs
test('al entrar pide el departamento y dice cómo está', async () => {
  const { pantalla, pedidos } = await abrir(DEPTO);
  assert.deepEqual(pedidos.map(([ruta]) => ruta), ['GET departamento']);
  assert.equal(texto(pantalla, '.pieza-linea'), '3 × 3 · 2 de 9 casillas · camas 1 · gachamones 1 · comodidad 82 de 100');
  assert.equal(uno(pantalla, 'canvas').getAttribute('aria-hidden'), 'true');
  assert.equal(texto(pantalla, 'h1'), 'Tu casa');
});

test('si no carga lo dice y deja volver a intentarlo', async () => {
  const { pantalla, pedidos, servidor } = await abrir(new Error('sin red'));
  assert.equal(texto(pantalla, '[role=alert]'), 'No hubo respuesta. Revisa tu conexión.');
  servidor.responde('GET departamento', DEPTO);
  await tocar(boton(pantalla, 'Volver a intentarlo'));
  assert.equal(pedidos.length, 2);
  assert.equal(texto(pantalla, '.pieza-linea').startsWith('3 × 3'), true);
});

test('un 409 al leer se va de la pantalla', async () => {
  const { seguido } = await abrir({ estado: 409, clave: 'no_estas_ahi', mensaje: 'Para eso tienes que estar en tu departamento.' });
  assert.equal(seguido.length, 1);
});

test('al volver a la pestaña se vuelve a leer', async () => {
  const { pantalla, pedidos, servidor, documento } = await abrir(DEPTO);
  servidor.responde('GET departamento', CON_MACETA);
  await documento.dispara('visibilitychange');
  assert.equal(pedidos.length, 2);
  assert.equal(texto(pantalla, '.pieza-linea').startsWith('3 × 3 · 3 de 9'), true);
});

test('tocar fuera de la pieza no hace nada', async () => {
  const { pantalla, pedidos } = await abrir(DEPTO);
  await tocarEn(pantalla, 2, 2);                                        // una esquina del lienzo
  assert.equal(pedidos.length, 1);
  assert.equal(texto(pantalla, '[role=status].aviso'), '');
});
```

```python
# tests/test_web_cliente.py
def test_el_departamento_esta_montado_y_tiene_su_ancho_en_el_computador():
    principal = _guion("principal.js")
    assert "from './departamento.js'" in principal and "departamento:" in principal
    assert '#juego[data-pantalla="departamento"]' in (ESTATICOS / "estilo.css").read_text(encoding="utf-8")

def test_la_pieza_no_es_pixel_art_pero_el_avatar_si():
    pieza = _guion("pieza.js")
    assert "imageSmoothingEnabled = true" in pieza and "imageSmoothingEnabled = false" in pieza

def test_el_departamento_no_escribe_claves_ni_precios_del_catalogo():
    for nombre in ("departamento.js", "pieza.js", "casillas.js", "proyeccion.js"):
        codigo = _sin_comentarios(_guion(nombre))
        for clave in departamento.MUEBLES:
            assert f"'{clave}'" not in codigo and f'"{clave}"' not in codigo, (nombre, clave)
        assert not re.search(r"\b(15|85)\b", codigo), nombre      # lo que cuesta una casilla y una cama

def test_el_departamento_camina_solo_mientras_algo_se_mueve_y_respeta_el_movimiento_reducido():
    codigo = _guion("departamento.js")
    for trozo in ("requestAnimationFrame", "cancelAnimationFrame", "prefers-reduced-motion", "visibilitychange", "aria-hidden"):
        assert trozo in codigo, trozo
```

- [ ] **Step 2: Verlas fallar.** Run: `node --test tests/js/pantallas.test.mjs tests/js/departamento.test.mjs` y `./venv/bin/python -m pytest tests/test_web_cliente.py -q` — Expected: FAIL.
- [ ] **Step 3: Implementar** `pieza.js`, la pantalla y su estilo.
- [ ] **Step 4: Mirarla.** Con el arnés del recorrido (bases temporales, nunca `tamagotchi.db`): la pieza en 3 × 3 y en 8 × 8, en 390 y en 1280 de ancho; caminar; la consola, limpia. Las capturas van al informe.
- [ ] **Step 5: La suite entera** (Python y JavaScript). Run: `./venv/bin/python -m pytest tests/ -q -p no:cacheprovider` — Expected: PASS.
- [ ] **Step 6: Commit** — `feat(web): tu casa es la pieza de tu departamento, y se camina por ella`.

---

### Task 7: Los muebles

**Files:**
- Modify: `web/static/js/departamento.js`, `web/static/js/pieza.js`, `web/static/estilo.css`, `tests/js/departamento.test.mjs`, `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: Tasks 4, 5 y 6; `POST departamento/poner {mueble_id, x, y, giro}`, `POST departamento/guardar {mueble_id}`, `POST departamento/ampliar {eje, evento_id}` (plan 4): `{ok, clave, mensaje, departamento, estado}`.
- Produces (en la pantalla):
  - **Tocar un mueble lo elige**: su huella se marca y sobre él sale su menú (`.menu-de-la-pieza`, botones de verdad puestos encima del lienzo) con su nombre y `✋ Mover`, `🔄 Girar`, `📦 Guardar`. Tocarlo otra vez, tocar el suelo o elegir otra cosa lo cierra. No hay modo que encender. Tocar una casilla con algo que se pisa (la alfombra, el felpudo) lo elige **y** camina hasta ahí.
  - **Mover**: lo llevas en la mano: se marcan los sitios de `dondeCabe` (menos donde ya está) y sale `Toca la casilla donde lo quieres.` (o la de la pared). Con algo en la mano, el toque se lee sólo como casilla o tramo (`casillaEn`, `tramoEn`), sin mirar lo que haya dibujado encima. Tocar un sitio marcado manda `poner` con el giro que `dondeCabe` dio para ese sitio; tocar cualquier otra cosa lo suelta sin mandar nada.
  - **Girar**: manda `poner` en su sitio con el giro siguiente que quepa (`giroParaPoner` desde `giro + 1`); si no cabe en ningún otro, no manda nada y dice `Ahí no cabe.` Lo de pared no ofrece girar.
  - **Guardar**: manda `guardar`.
  - **Guardados**: el botón abre o cierra la bandeja (`.bandeja`, bajo la pieza) con un botón por **tipo** de mueble guardado (`aria-pressed`): su ícono de la Tienda (`icono`), su nombre, `× {cuántos}` y cuánto ocupa. Elegir uno lo pone en la mano, como «Mover», empezando por el giro 0; al tocar un sitio se manda `poner` del primero de ese tipo. Queda puesto y elegido.
  - **Ampliar**: el botón cambia lo de la derecha por el panel `.ampliar`, con un botón por lado que pueda crecer (el coste sale de `departamento.ampliar`; las casillas que suma, de `ancho` y `fondo`) y `Volver`. Cada toque lleva su evento (`const … = nuevoEvento();` fuera de `conReintentos`).
  - **Lo que sale bien no dice nada**: se ve en la pieza. Ampliar sí enseña la frase del servidor. **Lo que no**, la frase del servidor (`mensaje`) en la zona de aviso, y la pieza queda como estaba. Sin respuesta: `No hubo respuesta. Revisa tu conexión.` y se vuelve a leer.
  - Mientras una petición va, lo que la mandó queda en espera (`aria-busy`) y no se manda otra.
  - Al llegar un departamento nuevo, tu avatar y cada gachamon que haya quedado sobre un mueble o fuera de la pieza aparece en `libreMasCercana` (no camina hasta ahí).

- [ ] **Step 1: Escribir las pruebas que fallan**, en `tests/js/departamento.test.mjs` (`menu(pantalla)` es el menú abierto o `null`; `rotulos(raiz)`, el texto de cada botón sin su emoji; `boton(raiz, texto)`, el botón cuyo texto lo contiene; `BIEN(depto)` es `{ ok: true, clave: null, mensaje: null, departamento: depto, estado: ESTADO }`):

```js
test('tocar un mueble abre su menú, y tocarlo otra vez lo cierra', async () => {
  const { pantalla, pedidos } = await abrir(CON_MACETA);
  assert.equal(menu(pantalla), null);
  await tocarCasilla(pantalla, 2, 2);
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Maceta');
  assert.deepEqual(rotulos(menu(pantalla)), ['Mover', 'Girar', 'Guardar']);
  await tocarCasilla(pantalla, 2, 2);
  assert.equal(menu(pantalla), null);
  await tocarCasilla(pantalla, 0, 0); await tocarCasilla(pantalla, 2, 0);           // elegir la cama y tocar el suelo
  assert.equal(menu(pantalla), null);
  assert.equal(pedidos.length, 1);                                                  // nada de esto habla con el servidor
});

test('guardar un mueble lo manda y no dice nada si sale bien', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_MACETA);
  servidor.responde('POST departamento/guardar', BIEN(SIN_MACETA));
  await tocarCasilla(pantalla, 2, 2);
  await tocar(boton(menu(pantalla), 'Guardar'));
  assert.deepEqual(pedidos.at(-1), ['POST departamento/guardar', { mueble_id: MACETA_ID }]);
  assert.equal(texto(pantalla, '[role=status].aviso'), '');
  assert.equal(texto(pantalla, '.pieza-linea').startsWith('3 × 3 · 2 de 9'), true);
  assert.equal(menu(pantalla), null);
});

test('lo que el servidor rechaza se dice con su frase y nada cambia', async () => {
  const { pantalla, servidor } = await abrir(DEPTO);
  servidor.responde('POST departamento/guardar', { ok: false, clave: 'hace_falta', mensaje: 'Esa cama hace falta: sin ella alguien se queda sin dónde dormir.', departamento: DEPTO, estado: ESTADO });
  await tocarCasilla(pantalla, 0, 0);
  await tocar(boton(menu(pantalla), 'Guardar'));
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Esa cama hace falta: sin ella alguien se queda sin dónde dormir.');
  assert.equal(texto(pantalla, '.pieza-linea'), '3 × 3 · 2 de 9 casillas · camas 1 · gachamones 1 · comodidad 82 de 100');
});

test('girar manda el giro siguiente que cabe, en su mismo sitio', async () => {
  const { pantalla, pedidos, servidor } = await abrir(DEPTO);            // la cama en (0, 0) con giro 0
  servidor.responde('POST departamento/poner', BIEN(DEPTO));
  await tocarCasilla(pantalla, 1, 0);                                    // la otra casilla de la cama también es la cama
  await tocar(boton(menu(pantalla), 'Girar'));
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: CAMA_ID, x: 0, y: 0, giro: 1 }]);
});

test('mover: se toca dónde, y tocar donde no cabe lo suelta', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_MACETA);
  servidor.responde('POST departamento/poner', BIEN(CON_MACETA));
  await tocarCasilla(pantalla, 2, 2); await tocar(boton(menu(pantalla), 'Mover'));
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Toca la casilla donde lo quieres.');
  await tocarCasilla(pantalla, 0, 0);                                    // ahí está la cama: se suelta
  assert.equal(pedidos.length, 1);
  await tocarCasilla(pantalla, 2, 0);                                    // ya no hay nada en la mano: es caminar
  assert.equal(pedidos.length, 1);
  await tocarCasilla(pantalla, 2, 2); await tocar(boton(menu(pantalla), 'Mover'));
  await tocarCasilla(pantalla, 2, 0);
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: MACETA_ID, x: 2, y: 0, giro: 0 }]);
});

test('poner uno guardado donde no cabe como viene lo prueba girado', async () => {
  const { pantalla, pedidos, servidor } = await abrir(DEPTO);            // una cama guardada
  servidor.responde('POST departamento/poner', BIEN(DEPTO));
  await tocar(boton(pantalla, 'Guardados'));
  assert.match(texto(uno(pantalla, '.bandeja'), 'button'), /Cama sencilla.*× 1.*2 casillas/s);
  await tocar(boton(uno(pantalla, '.bandeja'), 'Cama sencilla'));
  await tocarCasilla(pantalla, 2, 1);                                    // a lo ancho se sale: va girada
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: GUARDADA_ID, x: 2, y: 1, giro: 1 }]);
});

test('lo de pared se pone tocando la pared', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_UN_CUADRO_GUARDADO);
  servidor.responde('POST departamento/poner', BIEN(CON_UN_CUADRO_GUARDADO));
  await tocar(boton(pantalla, 'Guardados'));
  assert.match(texto(uno(pantalla, '.bandeja'), 'button'), /Cuadro.*en la pared/s);
  await tocar(boton(uno(pantalla, '.bandeja'), 'Cuadro'));
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Toca la pared donde lo quieres.');
  await tocarTramo(pantalla, 1, -1);
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: CUADRO_ID, x: 1, y: -1, giro: 0 }]);
});

test('sin guardados, la bandeja lo dice', async () => {
  const { pantalla } = await abrir({ ...DEPTO, guardados: [] });
  await tocar(boton(pantalla, 'Guardados'));
  assert.match(texto(pantalla, '.bandeja'), /No queda nada guardado\./);
});

test('ampliar lleva un evento por toque y enseña lo que cuesta', async () => {
  const { pantalla, pedidos, servidor } = await abrir(DEPTO);
  await tocar(boton(pantalla, 'Ampliar'));
  assert.match(texto(pantalla, '.ampliar'), /\+ columna \(3 casillas\) · 45/);
  const mas = { ...DEPTO, ancho: 4, casillas: 12, ampliar: { ancho: 45, fondo: 60 } };
  servidor.responde('POST departamento/ampliar', { ok: true, clave: null, mensaje: 'Tu departamento ahora mide 4 × 3.', departamento: mas, estado: ESTADO });
  await tocar(boton(pantalla, '+ columna'));
  const [ruta, cuerpo] = pedidos.at(-1);
  assert.equal(ruta, 'POST departamento/ampliar');
  assert.equal(cuerpo.eje, 'ancho'); assert.match(cuerpo.evento_id, /^[\w-]{8,64}$/);
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Tu departamento ahora mide 4 × 3.');
  assert.match(texto(pantalla, '.ampliar'), /\+ fila \(4 casillas\) · 60/);
  await tocar(boton(pantalla, '+ columna'));
  assert.notEqual(pedidos.at(-1)[1].evento_id, cuerpo.evento_id);        // otro toque, otro evento
});

test('en 8 × 8 ya no se ofrece crecer', async () => {
  const { pantalla } = await abrir({ ...DEPTO, ancho: 8, fondo: 8, casillas: 64, ampliar: { ancho: null, fondo: null } });
  await tocar(boton(pantalla, 'Ampliar'));
  assert.equal(texto(pantalla, '.ampliar p'), 'Tu departamento ya no puede crecer más.');
});

test('sin respuesta lo dice y vuelve a leer', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_MACETA);
  servidor.falla('POST departamento/guardar');
  await tocarCasilla(pantalla, 2, 2);
  await tocar(boton(menu(pantalla), 'Guardar'));
  assert.equal(texto(pantalla, '[role=status].aviso'), 'No hubo respuesta. Revisa tu conexión.');
  assert.equal(pedidos.at(-1)[0], 'GET departamento');
});

test('una lectura que salió antes que una acción no pisa lo que la acción dejó', async () => {
  const { pantalla, servidor, documento } = await abrir(CON_MACETA);
  const soltar = servidor.retiene('GET departamento');
  await documento.dispara('visibilitychange');                           // sale una lectura, y se queda en camino
  servidor.responde('POST departamento/guardar', BIEN(SIN_MACETA));
  await tocarCasilla(pantalla, 2, 2);
  await tocar(boton(menu(pantalla), 'Guardar'));
  await soltar(CON_MACETA);                                              // llega tarde, con la maceta todavía puesta
  assert.equal(texto(pantalla, '.pieza-linea').startsWith('3 × 3 · 2 de 9'), true);
});

test('mientras una petición va, no sale otra', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_MACETA);
  const soltar = servidor.retiene('POST departamento/guardar');
  await tocarCasilla(pantalla, 2, 2);
  const guardar = boton(menu(pantalla), 'Guardar');
  await tocar(guardar); await tocar(guardar);
  assert.equal(pedidos.filter(([ruta]) => ruta === 'POST departamento/guardar').length, 1);
  assert.equal(guardar.getAttribute('aria-busy'), 'true');
  await soltar(BIEN(SIN_MACETA));
});
```

  En `tests/test_web_cliente.py`, la guarda `test_el_evento_se_crea_una_vez_fuera_de_lo_que_se_reintenta` recorre hoy `("tienda.js", "mochila.js", "lugar.js")`: se le añade `"departamento.js"`.

- [ ] **Step 2: Verlas fallar.** Run: `node --test tests/js/departamento.test.mjs` — Expected: FAIL en las nuevas.
- [ ] **Step 3: Implementar** el menú sobre el mueble, mover, girar, guardar, los guardados y ampliar.
- [ ] **Step 4: Mirarlo** con el arnés: tocar un mueble, moverlo, girarlo junto a la pared, guardarlo, sacar uno de guardados, colgar un cuadro, ampliar; en 390 y en 1280. Las capturas van al informe.
- [ ] **Step 5: La suite entera** (Python y JavaScript). Expected: PASS.
- [ ] **Step 6: Commit** — `feat(web): poner, mover, girar y guardar muebles tocándolos, y ampliar el departamento`.

---

### Task 8: Los gachamones

**Files:**
- Create: `web/static/js/cuidados.js`
- Modify: `web/static/js/departamento.js`, `web/static/js/pieza.js`, `web/static/js/lugar.js` (deja de tener su copia de lo que pasa a `cuidados.js`), `web/static/js/ficha.js`, `web/static/js/principal.js`, `web/static/estilo.css`, `tests/js/departamento.test.mjs`, `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: Tasks 2, 6 y 7; `POST cuidar {accion, evento_id, gachamon_id}` (devuelve la ficha del cuidado en `gachamon`), `POST cuidar/todos {accion, evento_id}`, `POST acariciar {gachamon_id}`, `POST departamento/salir {gachamon_id}`, `GET ficha?gachamon_id=`.
- Produces:
  - `cuidados.js`: lo que el lugar y el departamento hacen igual, sacado de `lugar.js` **sin cambiar lo que hace**: `CUIDADOS` (las cuatro acciones con su ícono y su nombre, con «Bañar»), lo que calcula cuánto le falta a cada espera y cómo se rotula, y lo que decide qué se celebra y qué se avisa tras un cuidado (las monedas ganadas, la evolución, las medallas, la frase del juego). Los nombres, los que ya tengan esas funciones en `lugar.js`. `lugar.js` pasa a importarlo y se sigue portando igual.
  - En la pantalla:
    - **Cada gachamon vivo está en la pieza**: al entrar, tú y ellos os repartís con `sitiosDeEntrada` (tú, el primero; después ellos, en el orden de `plantel`). El que sale contigo lleva su marca (`efectos/marca.png`).
    - **Caminan solos**: cada cierto rato (entre 4 y 9 segundos, con el azar inyectado) uno da un paso (`pasoSuelto`). Se quedan quietos mientras llevas algo en la mano y con movimiento reducido.
    - **Tocar a uno lo elige**: su ficha queda a la derecha (`.ficha-elegido`): nombre, la chapa `Sale contigo` si lo es, «Especie etapa · nivel N», las tres barras, los cuatro cuidados con sus esperas, `Acariciar`, `Ver ficha` y, si no es el que sale contigo, `Salir con {nombre}`. Sobre él sale su menú, con `✋ Mover` y `Acariciar`. Al entrar está elegido el que sale contigo, sin menú.
    - **Mover a un gachamon** es sólo del dibujo: se toca dónde y camina hasta ahí (si no hay camino, aparece). No se manda nada al servidor.
    - **Cuidarlo** manda `cuidar` con su `gachamon_id` y un evento por toque; con la respuesta cambian sus barras y sus esperas, y se avisa como en el lugar.
    - **Acariciarlo**, desde su menú o desde su ficha, manda `acariciar` con su `gachamon_id`; como en el lugar: corazones si se pudo, la frase de la espera si no.
    - **«A todos»** (un grupo con `aria-label="A todos"`): cuatro botones; cada uno manda `cuidar/todos` con su evento, enseña la frase del servidor («Jugaste con 2 de 3.») y vuelve a leer el departamento.
    - **Salir con él** manda `departamento/salir` y enseña la frase del servidor.
    - **Ver ficha** abre la ficha completa de ese gachamon: `seguir(estado, { vista: 'ficha', gachamonId })`. `principal.js` deja pasar `opciones.gachamonId` hasta la pantalla (`ficha(destino, estado, seguir, gachamonId)`); `ficha.js` la pide con `ficha?gachamon_id=…` cuando lo recibe (sin él, como hoy), no ofrece el ropero si `es_el_activo` es falso, y su «volver» sigue siendo `seguir(estado)`, que en casa ya lleva al departamento.
    - El globo de lo que dice el gachamon sale sobre el que sale contigo (`estado.globos`), como en el lugar, y se anuncia igual (`aria-live="polite"`).
    - **Sin ningún gachamon**: donde iría la ficha, `Todavía no vive ningún gachamon contigo.`; «A todos» no se enseña; la pieza, los muebles y ampliar funcionan igual.
    - Si no queda ninguna casilla que se pise, no se dibuja a nadie en la pieza; la ficha del que sale contigo sigue a la derecha.

- [ ] **Step 1: Escribir las pruebas que fallan**, en `tests/js/departamento.test.mjs` (`dondeEsta(depto, n)` es el sitio de entrada del gachamon `n` de su plantel: `sitiosDeEntrada(depto.ancho, depto.fondo, noSePisan(depto), depto.plantel.length + 1)[n + 1]`; `tocarA(pantalla, depto, n)` toca esa casilla):

```js
test('la ficha de la derecha es la del que sale contigo, y se cambia tocando a otro', async () => {
  const { pantalla } = await abrir(CON_DOS);                             // Pelusa (sale contigo) y Rulo
  assert.match(texto(pantalla, '.ficha-elegido'), /Pelusa.*Sale contigo/s);
  assert.equal(boton(pantalla, 'Salir con'), null);
  assert.equal(menu(pantalla), null);
  await tocarA(pantalla, CON_DOS, 1);
  assert.match(texto(pantalla, '.ficha-elegido'), /Rulo/);
  assert.doesNotMatch(texto(pantalla, '.ficha-elegido'), /Sale contigo/);
  assert.notEqual(boton(pantalla, 'Salir con Rulo'), null);
  assert.deepEqual(rotulos(menu(pantalla)), ['Mover', 'Acariciar']);
});

test('cuidar al elegido manda su id y un evento, y cambia sus barras', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_DOS);
  await tocarA(pantalla, CON_DOS, 1);
  servidor.responde('POST cuidar', { ok: true, mensaje: 'Rulo quedó reluciente.', espera: 600, monedas: 1, evoluciono: false, logros: [],
    gachamon: { ...RULO, barras: { ...RULO.barras, aseo: 100 }, esperas: { ...RULO.esperas, limpiar: 600 } }, estado: ESTADO });
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Bañar'));
  const [ruta, cuerpo] = pedidos.at(-1);
  assert.equal(ruta, 'POST cuidar');
  assert.deepEqual([cuerpo.accion, cuerpo.gachamon_id], ['limpiar', RULO.id]); assert.match(cuerpo.evento_id, /^[\w-]{8,64}$/);
  assert.equal(boton(uno(pantalla, '.ficha-elegido'), 'Bañar').getAttribute('aria-disabled'), 'true');
  assert.match(texto(pantalla, '[role=status].aviso'), /Rulo quedó reluciente\./);
});

test('acariciar al elegido manda su id', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_DOS);
  servidor.responde('POST acariciar', { ok: true, mensaje: null, espera: 60, estado: ESTADO });
  await tocarA(pantalla, CON_DOS, 1);
  await tocar(boton(menu(pantalla), 'Acariciar'));
  assert.deepEqual(pedidos.at(-1), ['POST acariciar', { gachamon_id: RULO.id }]);
});

test('mover a un gachamon no habla con el servidor', async () => {
  const { pantalla, pedidos } = await abrir(CON_DOS, ESTADO, { movimientoReducido: true });   // no camina: aparece
  await tocarA(pantalla, CON_DOS, 1);
  await tocar(boton(menu(pantalla), 'Mover'));
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Toca la casilla donde lo quieres.');
  await tocarCasilla(pantalla, 0, 2);
  assert.equal(pedidos.length, 1);
  await tocarA(pantalla, CON_DOS, 0);                                    // se elige a Pelusa…
  assert.match(texto(pantalla, '.ficha-elegido'), /Pelusa/);
  await tocarCasilla(pantalla, 0, 2);                                    // …y Rulo está donde se le dejó: tocarlo lo elige
  assert.match(texto(pantalla, '.ficha-elegido'), /Rulo/);
});

test('a todos manda su evento, dice lo que contesta el juego y vuelve a leer', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_DOS);
  servidor.responde('POST cuidar/todos', { ok: true, a_cuantos: 2, de_cuantos: 2, tocados: [PELUSA.id, RULO.id], mensaje: 'Jugaste con 2 de 2.', monedas: 2, logros: [], estado: ESTADO });
  await tocar(boton(pantalla, 'Jugar con todos'));
  const [ruta, cuerpo] = pedidos.at(-2);
  assert.equal(ruta, 'POST cuidar/todos'); assert.equal(cuerpo.accion, 'jugar'); assert.match(cuerpo.evento_id, /^[\w-]{8,64}$/);
  assert.equal(pedidos.at(-1)[0], 'GET departamento');
  assert.match(texto(pantalla, '[role=status].aviso'), /Jugaste con 2 de 2\./);
});

test('salir con otro lo manda y lo deja como el que sale contigo', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_DOS);
  await tocarA(pantalla, CON_DOS, 1);
  servidor.responde('POST departamento/salir', { ok: true, clave: null, mensaje: 'Ahora sales con Rulo.', departamento: CON_RULO_ACTIVO, estado: { ...ESTADO, gachamon: RULO } });
  await tocar(boton(pantalla, 'Salir con Rulo'));
  assert.deepEqual(pedidos.at(-1), ['POST departamento/salir', { gachamon_id: RULO.id }]);
  assert.match(texto(pantalla, '.ficha-elegido'), /Rulo.*Sale contigo/s);
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Ahora sales con Rulo.');
});

test('ver ficha abre la de ese gachamon', async () => {
  const { pantalla, seguido } = await abrir(CON_DOS);
  await tocarA(pantalla, CON_DOS, 1);
  await tocar(boton(pantalla, 'Ver ficha'));
  assert.deepEqual(seguido.at(-1)[1], { vista: 'ficha', gachamonId: RULO.id });
});

test('poner un mueble donde está parado uno lo corre a un lado', async () => {
  const { pantalla, servidor, documento } = await abrir(CON_DOS);
  const [i, j] = dondeEsta(CON_DOS, 1);                                  // donde está Rulo
  const conMaceta = { ...CON_DOS, puestos: [...CON_DOS.puestos, { id: MACETA_ID, ...MACETA, nombre: 'Maceta', x: i, y: j, giro: 0, casillas: [[i, j]] }] };
  servidor.responde('GET departamento', conMaceta);
  await documento.dispara('visibilitychange');
  await tocarCasilla(pantalla, i, j);
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Maceta');         // ahí ya no está Rulo: está la maceta
});

test('sin ningún gachamon la pieza se ve igual y lo dice', async () => {
  const { pantalla } = await abrir({ ...DEPTO, gachamones: 0, plantel: [] }, { ...ESTADO, gachamon: null, globos: [] });
  assert.equal(texto(pantalla, '.ficha-elegido'), 'Todavía no vive ningún gachamon contigo.');
  assert.equal(boton(pantalla, 'Alimentar a todos'), null);
  assert.notEqual(boton(pantalla, 'Ampliar'), null);
});
```

```python
# tests/test_web_cliente.py
def test_lo_comun_de_los_cuidados_vive_en_un_solo_sitio():
    cuidados, lugar, depto = (_guion(n) for n in ("cuidados.js", "lugar.js", "departamento.js"))
    assert "export const CUIDADOS" in cuidados and "nombre: 'Bañar'" in cuidados
    assert "from './cuidados.js'" in lugar and "from './cuidados.js'" in depto
    assert "nombre: 'Bañar'" not in lugar and "nombre: 'Bañar'" not in depto

def test_la_ficha_de_uno_que_no_sale_contigo_no_ofrece_el_ropero():
    ficha = _guion("ficha.js")
    assert "gachamon_id" in ficha and "es_el_activo" in ficha
    assert "gachamonId" in _guion("principal.js")
```

  Las guardas de hoy que miran `lugar.js` (la del evento, la de `nombre: 'Bañar'` de la Task 1, las de `acariciar`, `cuidar` y `visibilitychange`) se ajustan a dónde vive ahora cada cosa, sin aflojar lo que vigilan; el informe dice cuál cambió y por qué.

- [ ] **Step 2: Verlas fallar.** Run: `node --test tests/js/departamento.test.mjs` — Expected: FAIL en las nuevas.
- [ ] **Step 3: Sacar `cuidados.js` de `lugar.js`** sin cambiar el comportamiento del lugar, y comprobarlo: las pruebas y las guardas del lugar siguen pasando, y en el arnés un cuidado y una caricia en otro lugar (la plaza) se ven igual que antes.
- [ ] **Step 4: Implementar** los gachamones en la pieza, la ficha del elegido, «A todos», salir, y la ficha de cualquiera.
- [ ] **Step 5: Mirarlo** con el arnés, con tres gachamones: elegir a otro, cuidarlo, «a todos», salir con él, ver su ficha y volver, moverlo, poner un mueble donde está uno (se corre). Capturas al informe.
- [ ] **Step 6: La suite entera** (Python y JavaScript). Expected: PASS.
- [ ] **Step 7: Commit** — `feat(web): tus gachamones en la pieza: elegir, cuidar, a todos, salir con él y su ficha`.

---

### Task 9: Sin el dibujo

**Files:**
- Modify: `web/static/js/departamento.js`, `web/static/estilo.css`, `tests/js/departamento.test.mjs`, `tests/test_web_cliente.py`

**Interfaces:**
- Produces: bajo la pieza y sus paneles, y siempre presente (no es un modo ni está oculta a quien ve), **la lista**, con todo lo que se puede hacer en el dibujo:
  - Los gachamones (`.lista-gachamones`, un grupo con `aria-label="Tus gachamones"`): un botón por cada uno, con su nombre (`aria-pressed` en el elegido); elegirlo es lo mismo que tocarlo, sin el menú.
  - `Muebles puestos` (`.lista-puestos`): cada uno en un `li[data-fila=<id>]` con su nombre y su sitio (`{nombre}, en fila {f}, columna {c}`, o su pared y su tramo) y sus botones `Mover`, `Girar` (no en lo de pared) y `Guardar`.
  - `Guardados` (`.lista-guardados`): cada **mueble** guardado, de a uno, en un `li[data-fila=<id>]` con su nombre, cuánto ocupa y el botón `Poner`.
  - Al pulsar `Mover` o `Poner` aparece `¿Dónde?` (`.donde`): un desplegable con los sitios de `dondeCabe` (cada opción, `nombreDelSitio`; al mover, sin el sitio donde ya está) y el botón `Ponerlo ahí`, que manda `poner` con el giro de ese sitio. Si no cabe en ninguno: `Ahí no cabe.`, y no aparece.
  - Lo que sale bien y no se dice con texto (poner, mover, guardar) **se anuncia a quien no ve el dibujo**: la línea de estado se vuelve a decir en un `role="status"` aparte, de clase `solo-lector`.
  - El foco no se pierde: tras una acción vuelve a ese mismo mueble, en la lista donde haya quedado (puestos o guardados).
  - Lo que no se puede usar lleva `aria-disabled="true"`, no `disabled`.

- [ ] **Step 1: Escribir las pruebas que fallan**, en `tests/js/departamento.test.mjs` (`fila(pantalla, id)` es el `li[data-fila]` de ese mueble; `elegir(select, texto)` deja elegida la opción con ese texto):

```js
test('cada mueble puesto está en la lista con su sitio y sus botones', async () => {
  const { pantalla } = await abrir(CON_MACETA);
  const filas = todos(pantalla, '.lista-puestos li');
  assert.deepEqual(filas.map((f) => texto(f, '.mueble-nombre')), ['Cama sencilla, en fila 1, columna 1', 'Maceta, en fila 3, columna 3']);
  for (const f of filas) assert.deepEqual(rotulos(f), ['Mover', 'Girar', 'Guardar']);
  assert.deepEqual(rotulos(uno(pantalla, '.lista-guardados li')), ['Poner']);
});

test('mover desde la lista: se elige el sitio en un desplegable', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_MACETA);
  servidor.responde('POST departamento/poner', BIEN(CON_MACETA));
  await tocar(boton(fila(pantalla, MACETA_ID), 'Mover'));
  const sitios = todos(pantalla, '.donde option').map((o) => o.textContent);
  assert.ok(sitios.includes('fila 1, columna 3'));
  assert.ok(!sitios.includes('fila 1, columna 1') && !sitios.includes('fila 3, columna 3'));   // la cama, y donde ya está
  elegir(uno(pantalla, '.donde select'), 'fila 2, columna 3');
  await tocar(boton(pantalla, 'Ponerlo ahí'));
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: MACETA_ID, x: 2, y: 1, giro: 0 }]);
});

test('poner desde la lista uno que sólo cabe girado', async () => {
  const { pantalla, pedidos, servidor } = await abrir(DEPTO);
  servidor.responde('POST departamento/poner', BIEN(DEPTO));
  await tocar(boton(fila(pantalla, GUARDADA_ID), 'Poner'));
  elegir(uno(pantalla, '.donde select'), 'fila 1, columna 3');
  await tocar(boton(pantalla, 'Ponerlo ahí'));
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: GUARDADA_ID, x: 2, y: 0, giro: 1 }]);
});

test('lo de pared se ofrece en sus tramos y no se gira', async () => {
  const { pantalla } = await abrir(CON_UN_CUADRO_GUARDADO);
  await tocar(boton(fila(pantalla, CUADRO_ID), 'Poner'));
  const sitios = todos(pantalla, '.donde option').map((o) => o.textContent);
  assert.deepEqual(sitios, ['pared derecha, tramo 1', 'pared derecha, tramo 2', 'pared derecha, tramo 3',
                            'pared izquierda, tramo 1', 'pared izquierda, tramo 2', 'pared izquierda, tramo 3']);
});

test('tras guardar, el foco sigue en ese mueble y se vuelve a decir cómo quedó la pieza', async () => {
  const { pantalla, servidor, documento } = await abrir(CON_MACETA);
  servidor.responde('POST departamento/guardar', BIEN(SIN_MACETA));
  await tocar(boton(fila(pantalla, MACETA_ID), 'Guardar'));
  assert.equal(fila(pantalla, MACETA_ID).closest('.lista-guardados') !== null, true);
  assert.equal(fila(pantalla, MACETA_ID).contains(documento.activeElement), true);
  assert.equal(texto(pantalla, '.solo-lector[role=status]'), '3 × 3 · 2 de 9 casillas · camas 1 · gachamones 1 · comodidad 82 de 100');
});

test('los gachamones se eligen también desde la lista, y se les acaricia desde su ficha', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_DOS);
  const botones = todos(pantalla, '.lista-gachamones button');
  assert.deepEqual(botones.map((b) => [b.textContent.trim(), b.getAttribute('aria-pressed')]), [['Pelusa', 'true'], ['Rulo', 'false']]);
  await tocar(botones[1]);
  assert.match(texto(pantalla, '.ficha-elegido'), /Rulo/);
  servidor.responde('POST acariciar', { ok: true, mensaje: null, espera: 60, estado: ESTADO });
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Acariciar'));
  assert.deepEqual(pedidos.at(-1), ['POST acariciar', { gachamon_id: RULO.id }]);
});
```

```python
# tests/test_web_cliente.py
def test_lo_que_no_se_puede_usar_no_se_apaga_con_disabled():
    codigo = _sin_comentarios(_guion("departamento.js"))
    assert "aria-disabled" in codigo and not re.search(r"\bdisabled\s*[:=]", codigo)
```

- [ ] **Step 2: Verlas fallar.** Run: `node --test tests/js/departamento.test.mjs` — Expected: FAIL en las nuevas.
- [ ] **Step 3: Implementar** la lista entera, el «¿Dónde?», el foco y el anuncio.
- [ ] **Step 4: Recorrerlo sólo con el teclado** en el arnés: llegar a cada mueble con Tab, moverlo, girarlo, guardarlo y volver a ponerlo; elegir a un gachamon, cuidarlo y acariciarlo; ampliar. Lo que no se pueda, se arregla. El recorrido va al informe.
- [ ] **Step 5: La suite entera** (Python y JavaScript). Expected: PASS.
- [ ] **Step 6: Commit** — `feat(web): el departamento, entero, también sin el dibujo`.

---

### Task 10: La carta del alcalde, al entrar

**Files:**
- Create: `web/static/js/carta.js`, `tests/js/carta.test.mjs`
- Modify: `web/static/js/pantallas.js`, `web/static/js/principal.js`, `web/static/estilo.css`, `tests/js/pantallas.test.mjs`, `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: `estado.carta` (bool), `GET carta` → `{carta: {titulo, lineas, firma} | null}`, `POST carta/vista` → `{carta: null}` (plan 4).
- Produces:
  - `pantallas.siguiente(...)`: con sesión, cuenta y avatar, **si `estado.carta` es verdadero la pantalla es `'carta'`**, antes que el huevo, el nombre o cualquier lugar, y se pida la vista que se pida.
  - `carta(contenedor, estado, seguir)`, montada en `principal.js`: pide `GET carta`; enseña el título en un `h1`, cada línea en su párrafo (`.carta-linea`), la firma (`.carta-firma`) y el botón `Entendido`, que manda `POST carta/vista` y sigue (`seguir()`, que vuelve a leer el estado). Si la carta ya no está (`null`), sigue sin enseñar nada. Si no hay respuesta al marcarla, lo dice en un `role="status"` con la frase de siempre (`No hubo respuesta. Revisa tu conexión.`) y deja volver a intentarlo: la carta no se pierde.
  - En el computador, una columna de lectura, no los 1120 px.

- [ ] **Step 1: Escribir las pruebas que fallan.**

```js
// tests/js/pantallas.test.mjs (`sesion`, `cuenta` y `jugando` son los del archivo)
test('la carta se ve antes que nada', () => {
  for (const vista of [undefined, 'tienda', 'mochila', 'pueblo']) {
    assert.equal(siguiente(sesion, cuenta, { ...jugando, carta: true }, vista), 'carta');
  }
  assert.equal(siguiente(sesion, cuenta, { ...jugando, carta: true, gachamon: null }, undefined), 'carta');   // antes que el huevo
  assert.equal(siguiente(sesion, cuenta, { ...jugando, carta: false }, undefined), 'lugar');
  assert.equal(siguiente(sesion, cuenta, { ...jugando, carta: true, avatar: null }, undefined), 'avatar');   // primero, tener avatar
});

// tests/js/carta.test.mjs
test('la carta se lee entera y se cierra con Entendido', async () => {
  const { pantalla, pedidos, servidor, seguido } = await abrir({ carta: { titulo: 'Carta del alcalde', lineas: ['Una.', 'Dos.'], firma: 'El alcalde' } });
  assert.equal(texto(pantalla, 'h1'), 'Carta del alcalde');
  assert.deepEqual(todos(pantalla, '.carta-linea').map((p) => p.textContent), ['Una.', 'Dos.']);
  assert.equal(texto(pantalla, '.carta-firma'), 'El alcalde');
  servidor.responde('POST carta/vista', { carta: null });
  await tocar(boton(pantalla, 'Entendido'));
  assert.deepEqual(pedidos.map(([ruta]) => ruta), ['GET carta', 'POST carta/vista']); assert.equal(seguido.length, 1);
});

test('si ya no hay carta, se sigue de largo', async () => {
  const { seguido } = await abrir({ carta: null });
  assert.equal(seguido.length, 1);
});

test('si no se pudo marcar, la carta sigue ahí y se puede volver a intentar', async () => {
  const { pantalla, servidor, seguido } = await abrir({ carta: { titulo: 'Carta del alcalde', lineas: ['Una.'], firma: 'El alcalde' } });
  servidor.falla('POST carta/vista');
  await tocar(boton(pantalla, 'Entendido'));
  assert.equal(seguido.length, 0); assert.equal(texto(pantalla, '[role=status]'), 'No hubo respuesta. Revisa tu conexión.');
  assert.notEqual(boton(pantalla, 'Entendido'), null);
  assert.deepEqual(todos(pantalla, '.carta-linea').map((p) => p.textContent), ['Una.']);
});
```

```python
# tests/test_web_cliente.py
def test_la_carta_esta_montada():
    principal = _guion("principal.js")
    assert "from './carta.js'" in principal and "carta:" in principal
    assert "carta/vista" in _guion("carta.js")
```

- [ ] **Step 2: Verlas fallar.** Run: `node --test tests/js/carta.test.mjs tests/js/pantallas.test.mjs` — Expected: FAIL.
- [ ] **Step 3: Implementar** la pantalla, montarla en `principal.js` y su estilo (una tarjeta, legible en teléfono y en computador).
- [ ] **Step 4: Mirarla** en el arnés, sobre la base hecha con las reglas de producción (la del recorrido del plan 4): la persona que vincula ve su carta al entrar, la cierra y llega a su departamento, con sus camas puestas y sus muebles en guardados. Capturas al informe.
- [ ] **Step 5: La suite entera** (Python y JavaScript). Expected: PASS.
- [ ] **Step 6: Commit** — `feat(web): la carta del alcalde se ve al entrar, una vez`.

---

### Task 11: Los documentos

**Files:**
- Modify: `docs/superpowers/specs/2026-11-14-gachamon-rework-1-departamento-design.md`, `AGENTS.md`, `README.md`, `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`

**Interfaces:**
- **El diseño.** Lo que Felipe decidió el 2026-11-16 sobre el orden y el arte ya está en él desde que se confirmó este plan (§1, las aventuras y reclutar adelantados; §4.2, el arte de la pieza; §10, el corte con el orden nuevo). Aquí se le añade lo que salió de construir, cada cambio marcado **[Felipe, 2026-11-16]** o **[propuesta]** según de quién sea: §5, lo que cambió respecto del boceto (bajo la pieza se ve también la comodidad; al poner, mover o guardar bien no sale texto; en el computador, la pieza a la izquierda; se toca lo que se ve, con los gachamones primero, y quién tapa a quién se calcula de verdad); §6, cada casa mediana o grande devuelve 140 monedas más, «por tu ticket» y la especie con su mayúscula; §8, del gachamon elegido sólo la ficha (el ropero y la mochila siguen siendo del que sale contigo) y lo que la mochila ya no deja usar.
- **`AGENTS.md`**, concisos y sin SHAs: se cambia de activo estando en la Incubadora **o en tu departamento**; dónde está parado cada gachamon y tu avatar no se guarda; el arte de la pieza (su familia en el contrato, los originales en `fuentes/pieza/` al doble de lo servido, la herramienta que los reduce, cuatro orientaciones por mueble de suelo y dos por mueble de pared); el cliente no decide qué cabe: lo que calcula es para dibujar, y una prueba lo contrasta con `departamento.py`.
- **`README.md`**: «Tu casa» es la pieza del departamento y qué se puede hacer en ella; cómo entregar un dibujo de la pieza (apuntando al contrato).
- **Pendientes**, sección «Salió al ejecutar el rework 5 (el departamento en pantalla)», con la voz de las anteriores y sin SHAs, números de tarea ni ids. El controlador le pasa al implementador un archivo de notas con lo decidido durante la ejecución; como mínimo: lo decidido; lo que queda para «partir sin gachamon» (la pantalla ya se ve sin gachamon, pero a ella se llega con uno; quitar la Incubadora de «cuántos caben»); lo que queda para el pueblo (la Incubadora sigue sirviendo para cambiar de activo; «Tu casa» todavía no se llama «Tu departamento»); el ropero y la mochila siguen siendo del que sale contigo; el arte es de relleno hasta que el dibujante entregue; la silueta que se toca de un mueble es su caja entera, y con el arte definitivo puede convenir la del dibujo; y cuánto pesa el arte en el repo, para avisar si se acerca a lo que aguanta la tarjeta de la Pi.

- [ ] **Step 1: Escribir** los cuatro documentos con lo de arriba y las notas del controlador.
- [ ] **Step 2: Comprobar** que cada invariante nuevo de `AGENTS.md` es verdad en el código (`git grep` de cada símbolo que nombra) y que el diseño ya no dice en ningún sitio «dos imágenes» ni «espejada» sin su corrección.
- [ ] **Step 3: La verificación completa.** Run: `./venv/bin/python -m pre_commit run --all-files` — Expected: PASS.
- [ ] **Step 4: Commit** — `docs: el departamento en pantalla, en el diseño, la política, el README y los pendientes`.
