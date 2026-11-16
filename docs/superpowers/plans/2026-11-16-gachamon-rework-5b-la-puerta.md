# Rework 5b · La puerta — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que cada departamento tenga su puerta de entrada: va en la pared como un cuadro, se mueve pero no se guarda, es una casilla más fuera de la pieza, ahí apareces al entrar y por ella se sale al pueblo.

**Architecture:** La puerta es un mueble más del catálogo (`departamento.py`), de pared y de un tramo, con una marca propia (`puerta`): por eso valen para ella, sin tocarlas, las reglas de poner, de chocar con lo demás de la pared y de dibujarse. Lo que la hace distinta se decide en el servidor: cada departamento nace con la suya ya puesta, no se vende y no se guarda. El cliente la reconoce por la marca que manda el servidor (nunca por su clave) y le añade lo suyo: la casilla de la puerta como un sitio más por el que camina sólo tu avatar, que apareces en ella al entrar, y «Salir» en su menú.

**Tech Stack:** Python 3.12, FastAPI, SQLite síncrono, Pillow (rellenos), JavaScript sin framework ni compilación, pytest y `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-14-gachamon-rework-1-departamento-design.md`, sección 4.5 («La puerta», añadida con este plan) y la 5.

**Dónde encaja.** Es un plan corto que Felipe pidió el 2026-11-16 al probar «el departamento en pantalla» (el 5): «falta la puerta de entrada, que va adjunta a la pared al igual que las ventanas y los cuadros, y debe ser movible pero no guardable en el inventario, y la puerta es una casilla más fuera del departamento que es donde apareces al entrar en el departamento, al igual que en Habbo». Va antes de «partir sin gachamon» (el 6). Se junta en la rama `rework/1-departamento` y **se publica con todo lo demás, al final**.

**Lo que no entra.** Que los gachamones usen la puerta (no la pisan). Visitar el departamento de otra persona y entrar por su puerta: es del proyecto de la gente en vivo. Más de una puerta, o puertas que se compran. El arte definitivo: aquí va un dibujo de relleno.

## Global Constraints

- Nada se sube, se fusiona ni se despliega: todo queda en la rama local `rework/1-departamento`.
- Los módulos de juego no importan `discord`; `web/` no importa `discord` ni nada que lo importe; `db.py` no importa `economia.py`; `departamento.py` es puro. Cada cambio de estado va en su transacción `BEGIN IMMEDIATE`.
- **El servidor manda**: que haya una puerta, dónde está y que no se guarde lo decide y lo guarda el servidor. **Dónde está parado tu avatar no se guarda ni se manda al servidor.**
- El cliente: sin frameworks ni compilación, sin `innerHTML`, sin direcciones `http`, módulos con rutas relativas terminadas en `.js`. **Ninguna clave ni precio del catálogo escritos en el JavaScript**: la puerta se reconoce por la marca `puerta` que manda el servidor, nunca por su clave.
- **Decorar no tiene modos**: se toca la puerta y ahí salen sus opciones.
- Accesibilidad, como en el resto de la página: lo que se hace tocando el dibujo se hace también desde la lista; lo que cambia se anuncia; lo que no se puede usar lleva `aria-disabled`; con movimiento reducido nada camina: aparece.
- El arte son archivos descritos en el contrato (`web/arte.py`); el relleno se tiene que notar.
- Sin dependencias nuevas. Dominio determinista. Nunca se abre `tamagotchi.db` ni `.env`; las pruebas usan bases temporales e ids sintéticos. El repo es público.
- Antes de editar un símbolo, GitNexus `impact` (lo corre el controlador). Cada commit: `./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "…"`, con la línea de coautoría.
- **Lo que decidió Felipe (2026-11-16):**
  1. La puerta va en la pared, como las ventanas y los cuadros; se puede mover; **no se guarda**.
  2. Es **una casilla más, fuera del departamento**, y es donde apareces al entrar, como en Habbo.
  3. La casilla de dentro que queda frente a la puerta **se puede tapar con un mueble** («como en Habbo»): entonces apareces en la puerta y no pasas hasta mover el mueble.
  4. La casilla de la puerta **sólo la pisas tú**: los gachamones no.
  5. La puerta **también sirve para salir** al pueblo, además del botón «Pueblo».
  6. Sin camino, tu avatar **no va** (decisión del mismo día sobre el plan 5): vale también desde y hacia la puerta.
- **Lo que este plan decide en nombre de Felipe** (propuestas; se le enseñan con el plan):
  1. **Se sale desde el menú de la puerta.** Tocar la puerta la elige, como a cualquier mueble, y su menú trae `✋ Mover` y `🚪 Salir`. «Salir» te lleva caminando hasta ella y, al llegar, al pueblo. No hay otra forma de pisar su casilla, así que no hay salidas por accidente.
  2. **Dónde nace**: en la pared izquierda, en el tramo de más adelante; si la casilla de enfrente está tapada por lo que el alcalde dejó puesto, en el primer tramo que la tenga libre.
  3. **No suma comodidad**, no se vende en la Tienda y no aparece en «Guardados».
  4. Si al tocar «Salir» no hay camino hasta la puerta, no se sale y se dice por qué.
- **Frases nuevas** (se le enseñan a Felipe con el plan; van tal cual):
  - El nombre del mueble: `Puerta`.
  - En su menú: `🚪 Salir`; en la lista: `Salir`.
  - Si se pide guardarla: `La puerta no se guarda.`
  - Si no hay camino al salir: `No hay camino hasta la puerta.`
  - En la lista se nombra como los demás: `Puerta, en la pared izquierda, tramo 3`.

## Review Focus

1. **La puerta que falta o que sobra**: un departamento hecho antes de este plan no tiene puerta (la pantalla tiene que seguir funcionando: se entra como hasta ahora y no hay «Salir»); nadie puede acabar con dos, ni comprando ni por una petición repetida. → Tasks 1 y 4.
2. **Entrar con la entrada tapada**: apareces en la puerta, no puedes caminar hacia adentro, y aun así puedes tocar el mueble que estorba, moverlo y entonces pasar. → Task 4.
3. **Mover la puerta contigo en ella**: si estás en su casilla y la mueves, sigues en la puerta, en su sitio nuevo; si estabas dentro, no te mueves. → Task 4.
4. **La puerta en la esquina y en el borde**: en el último tramo de cada pared, tras ampliar, junto a un cuadro o unas cortinas (no comparten tramo), en la pared derecha y en la izquierda. → Tasks 1 y 3.
5. **Salir a medias**: tocar «Salir» y, mientras caminas, tocar otra cosa (se cancela la salida); salir con una petición en camino; salir con movimiento reducido. → Task 4.

---

### Task 1: La puerta en las reglas

**Files:**
- Modify: `departamento.py`, `db.py` (sólo si la puerta de partida no entra sola por `DE_PARTIDA`), `economia.py`, `web/departamento.py`, `web/tienda.py`, `tests/test_departamento.py`, `tests/test_camas.py` o donde se prueben guardar y comprar, `tests/test_dia_del_cambio.py`, `tests/test_web_departamento.py`, `tests/test_web_tienda.py`

**Interfaces:**
- Produces (`departamento.py`):
  - `Mueble` gana `puerta: bool = False`. El catálogo gana `Mueble("puerta", "Puerta", "🚪", 0, 0, capa=PARED, puerta=True)`; `PUERTA = "puerta"`.
  - `DE_PARTIDA` gana la puerta puesta en `(-1, 2)`: la pared izquierda, el tramo de más adelante (su casilla de enfrente, `(0, 2)`, está libre).
  - `frente_a(x, y) -> tuple[int, int]`: la casilla de dentro que queda frente a un tramo: `(0, y)` para `(-1, y)` y `(x, 0)` para `(x, -1)`.
  - `tramo_para_la_puerta(depto) -> tuple[int, int]`: el primer tramo sin nada colgado cuya casilla de enfrente no tiene un mueble que no se pise, buscando por la pared izquierda de adelante hacia atrás (`(-1, fondo - 1)` … `(-1, 0)`) y después por la derecha, igual (`(ancho - 1, -1)` … `(0, -1)`); si ninguno la tiene libre, el primero sin nada colgado en ese mismo orden.
  - `puede_guardarse` no cambia. Quien pregunta antes es `economia`.
- Produces (`economia.py`):
  - `_departamento_del_alcalde` (el día del cambio) deja además la puerta puesta en `dep.tramo_para_la_puerta` del departamento ya con sus camas.
  - `guardar_mueble` de la puerta: `ok=False`, `motivo="no_se_guarda"`, sin cambiar nada.
  - `comprar_mueble` de la puerta: `ValueError` (no es algo que se compre; la ruta la rechaza antes).
- Produces (`web/`):
  - `GET /departamento` y lo que devuelven poner, guardar, ampliar y salir: cada uno de los `puestos` gana **`puerta: bool`**.
  - `POST /departamento/guardar` de la puerta: `ok: False`, `clave: "no_se_guarda"`, `mensaje: "La puerta no se guarda."`.
  - La Tienda no lista la puerta, y comprarla (`POST /tienda/comprar` con su clave) se contesta como una clave que no existe.
  - La comodidad no cambia por tenerla (suma 0).

- [ ] **Step 1: Escribir las pruebas que fallan.**

```python
# tests/test_departamento.py
def test_la_puerta_es_un_mueble_de_pared_de_un_tramo_que_no_suma():
    puerta = dep.MUEBLES[dep.PUERTA]
    assert (puerta.nombre, puerta.capa, puerta.ancho, puerta.comodidad, puerta.puerta) == ("Puerta", dep.PARED, 1, 0, True)
    assert [m.clave for m in dep.MUEBLES.values() if m.puerta] == ["puerta"]

def test_el_departamento_de_partida_trae_su_puerta_con_la_entrada_libre():
    puertas = [p for p in dep.DE_PARTIDA.puestas if p.clave == dep.PUERTA]
    assert [(p.x, p.y) for p in puertas] == [(-1, 2)]
    assert dep.frente_a(-1, 2) == (0, 2) and dep.frente_a(1, -1) == (1, 0)
    assert dep.DE_PARTIDA.comodidad == 82                       # como antes: la puerta no suma

def test_la_puerta_choca_con_lo_colgado_y_se_mueve_a_un_tramo_libre():
    d = depto(P(1, "puerta", -1, 2), P(2, "cuadro", -1, 0), P(3, "cortinas"))
    assert dep.problema_al_poner(d, 1, -1, 0, 0) == dep.OCUPADO  # ahí está el cuadro
    assert dep.problema_al_poner(d, 1, 2, -1, 0) is None         # a la pared derecha
    assert dep.problema_al_poner(d, 3, -1, 1, 0) == dep.OCUPADO  # las cortinas pisarían la puerta
    assert dep.problema_al_poner(d, 1, 1, 1, 0) == dep.NO_CABE   # la puerta no va en el suelo

def test_el_alcalde_busca_un_tramo_con_la_entrada_libre():
    assert dep.tramo_para_la_puerta(depto()) == (-1, 2)
    tapada = depto(P(1, "maceta", 0, 2))
    assert dep.tramo_para_la_puerta(tapada) == (-1, 1)
    con_cuadro = depto(P(1, "maceta", 0, 2), P(2, "cuadro", -1, 1))
    assert dep.tramo_para_la_puerta(con_cuadro) == (-1, 0)
    columna = depto(P(1, "maceta", 0, 0), P(2, "maceta", 0, 1), P(3, "maceta", 0, 2))
    assert dep.tramo_para_la_puerta(columna) == (2, -1)          # la pared derecha, de adelante hacia atrás
    todo = depto(*(P(n, "maceta", n % 3, n // 3) for n in range(9)))
    assert dep.tramo_para_la_puerta(todo) == (-1, 2)             # ninguna libre: el primero sin nada colgado
    assert dep.tramo_para_la_puerta(depto(P(1, "felpudo", 0, 2))) == (-1, 2)   # lo que se pisa no tapa

# tests/test_camas.py (o el archivo donde se prueban guardar y comprar)
def test_la_puerta_no_se_guarda_ni_se_compra():
    nacer("Ana"); depto_ = db.departamento_de("u1", "g1", T0)
    puerta = next(p for p in depto_.puestas if p.clave == dep.PUERTA)
    hecho = economia.guardar_mueble("u1", "g1", puerta.id, T0)
    assert (hecho.ok, hecho.motivo) == (False, "no_se_guarda")
    assert db.departamento_leido("u1", "g1").pieza(puerta.id).puesta
    with pytest.raises(ValueError):
        economia.comprar_mueble("u1", "g1", dep.MUEBLES[dep.PUERTA], T0, "evento-puerta-1")

def test_la_puerta_se_mueve_como_cualquier_cosa_de_pared():
    nacer("Ana"); puerta = next(p for p in db.departamento_de("u1", "g1", T0).puestas if p.clave == dep.PUERTA)
    hecho = economia.poner_mueble("u1", "g1", puerta.id, 1, -1, 0, T0)
    assert hecho.ok and (hecho.departamento.pieza(puerta.id).x, hecho.departamento.pieza(puerta.id).y) == (1, -1)

# tests/test_dia_del_cambio.py
def test_el_dia_del_cambio_deja_a_cada_quien_su_puerta_con_la_entrada_libre():
    for n in range(3):
        nacer(f"G{n}", activa=(n == 0))
    el_cambio()
    d = db.departamento_leido("u1", "g1")
    puertas = [p for p in d.piezas if p.clave == dep.PUERTA]
    assert len(puertas) == 1 and puertas[0].puesta
    tapadas = {c for p in d.puestas if dep.MUEBLES[p.clave].capa == dep.BULTO
               for c in dep.huella(dep.MUEBLES[p.clave], p.x, p.y, p.giro)}
    assert dep.frente_a(puertas[0].x, puertas[0].y) not in tapadas

# tests/test_web_departamento.py
def test_el_departamento_dice_cual_es_la_puerta(cliente):
    con_gachamon(cliente); en_casa(cliente)
    d = cliente.get(f"{API}/departamento").json()
    assert [(p["clave"], p["x"], p["y"], p["puerta"]) for p in d["puestos"]] == [
        ("cama_sencilla", 0, 0, False), ("puerta", -1, 2, True)]
    assert (d["comodidad"], d["camas"]) == (82, 1)
    assert all(not g.get("puerta") for g in d["guardados"])

def test_la_puerta_no_se_guarda_desde_la_pagina(cliente):
    con_gachamon(cliente); en_casa(cliente)
    puerta = next(p for p in cliente.get(f"{API}/departamento").json()["puestos"] if p["puerta"])
    r = cliente.post(f"{API}/departamento/guardar", json={"mueble_id": puerta["id"]}, headers=CABECERA).json()
    assert (r["ok"], r["clave"], r["mensaje"]) == (False, "no_se_guarda", "La puerta no se guarda.")
    assert any(p["puerta"] for p in r["departamento"]["puestos"])

# tests/test_web_tienda.py
def test_la_tienda_no_vende_la_puerta(cliente):
    con_gachamon(cliente); ir(cliente, "tienda")
    assert "puerta" not in [m["clave"] for m in cliente.get(f"{API}/tienda").json()["muebles"]["lista"]]
    r = cliente.post(f"{API}/tienda/comprar", json={"que": "mueble", "clave": "puerta", "evento_id": "evento-puerta-web"}, headers=CABECERA)
    assert r.status_code == 422
```

  (La forma exacta de la lista de muebles de la Tienda y el código con que hoy rechaza una clave que no existe se toman de las pruebas vecinas de `tests/test_web_tienda.py`.)

- [ ] **Step 2: Verlas fallar.** Run: `./venv/bin/python -m pytest tests/test_departamento.py tests/test_camas.py tests/test_dia_del_cambio.py tests/test_web_departamento.py tests/test_web_tienda.py -q` — Expected: FAIL (no hay `dep.PUERTA`).
- [ ] **Step 3: Implementar** lo de Interfaces. Las pruebas de hoy que fijan el catálogo («los catorce y la cama sencilla»), lo que trae el departamento de partida (una cama puesta y nada más) o cuántos muebles tiene alguien tras el día del cambio se ponen al día; el informe las lista. Ninguna prueba se borra.
- [ ] **Step 4: La suite entera.** Run: `./venv/bin/python -m pytest tests/ -q -p no:cacheprovider` — Expected: PASS (las de arte fallarán hasta la Task 2 si el contrato ya cuenta la puerta: si es así, las dos tareas se confirman juntas y el informe lo dice).
- [ ] **Step 5: Commit** — `feat(reglas): cada departamento tiene su puerta: va en la pared, se mueve y no se guarda`.

---

### Task 2: El dibujo de la puerta

**Files:**
- Modify: `web/arte.py`, `herramientas/rellenos.py`, `web/static/datos/arte.json`, `web/static/arte/pieza/muebles/puerta-se.png` y `puerta-so.png` (nuevos, de relleno), `docs/arte/contrato.md`, `tests/test_arte.py`, `tests/test_arte_pieza.py`, `tests/js/arte.test.mjs`

**Interfaces:**
- Produces: la familia `pieza` del contrato gana `pieza/muebles/puerta-se.png` (la que va en la pared izquierda) y `pieza/muebles/puerta-so.png` (la de la derecha), del tamaño de cualquier cosa de pared de un tramo (256 × 640 servido; el original, el doble). El contrato pasa de 253 a 255 piezas. **La puerta no tiene ícono** de 48 × 48 (`iconos/muebles/…`): no se vende ni se guarda, así que ninguna pantalla lo pide.
- El relleno de la puerta se distingue de un cuadro: el marco y un hueco oscuro de arriba abajo, con sus letras. No deja transparente más de la mitad de su caja (la prueba que ya vigila eso tiene que seguir pasando).
- `docs/arte/contrato.md`, en la sección de la pieza: la puerta, sus dos archivos y cómo se dibuja: es el vano de la puerta visto desde dentro, ocupa su tramo de pared de arriba abajo, y tu avatar se pinta de pie en su umbral, así que el dibujo no debe traer a nadie ni tapar el umbral.

- [ ] **Step 1: Escribir las pruebas que fallan.**

```python
# tests/test_arte_pieza.py
def test_la_puerta_tiene_sus_dos_dibujos_y_ningun_icono():
    rutas = {p.ruta: p for p in arte.piezas()}
    assert (rutas["pieza/muebles/puerta-se.png"].ancho, rutas["pieza/muebles/puerta-se.png"].alto) == (256, 640)
    assert "pieza/muebles/puerta-so.png" in rutas and "pieza/muebles/puerta-no.png" not in rutas
    assert "iconos/muebles/puerta.png" not in rutas
    assert len(arte.piezas()) == 255

def test_el_relleno_de_la_puerta_no_es_el_de_un_cuadro():
    puerta = rellenos._dibujar(next(p for p in arte.piezas() if p.ruta == "pieza/muebles/puerta-se.png"))
    cuadro = rellenos._dibujar(next(p for p in arte.piezas() if p.ruta == "pieza/muebles/cuadro-se.png"))
    assert puerta.size == cuadro.size and puerta.tobytes() != cuadro.tobytes()
```

- [ ] **Step 2: Verlas fallar.** Run: `./venv/bin/python -m pytest tests/test_arte_pieza.py -q` — Expected: FAIL.
- [ ] **Step 3: Implementar**, generar los dos rellenos y `arte.json`, y poner al día los totales (253 → 255) en `tests/test_arte.py` y `tests/js/arte.test.mjs`.
- [ ] **Step 4: El contrato escrito.**
- [ ] **Step 5: La suite entera.** Expected: PASS.
- [ ] **Step 6: Commit** — `feat(arte): la puerta del departamento entra al contrato, con su dibujo de relleno`.

---

### Task 3: La puerta, en cuentas

**Files:**
- Modify: `web/static/js/casillas.js`, `web/static/js/proyeccion.js`, `tests/js/casillas.test.mjs`, `tests/js/proyeccion.test.mjs`

**Interfaces:**
- Produces (`casillas.js`, puro):
  - `laPuerta(depto) -> {id, celda: [x, y], dentro: [i, j]} | null`: la puerta del departamento (el puesto con `puerta` verdadero), su casilla (la del tramo: `[-1, y]` o `[x, -1]`) y la casilla de dentro que queda enfrente (`[0, y]` o `[x, 0]`); `null` si el departamento no trae puerta.
  - `camino(ancho, fondo, noSePisan, desde, hasta, puerta = null)`: con `puerta` (lo que da `laPuerta`), su `celda` es un sitio más, vecino **sólo** de `dentro`. `desde` o `hasta` pueden ser esa casilla. Sin `puerta`, todo como hoy (las pruebas de hoy no cambian).
  - Nada más cambia: `noSePisan`, `sitiosDeEntrada`, `libreMasCercana` y `pasoSuelto` siguen hablando sólo de la pieza, así que ningún gachamon llega a la puerta.
- Produces (`proyeccion.js`, puro):
  - `umbralDe(celda) -> [i, j]`: dónde se pinta quien está en la casilla de la puerta, para que se le vea de pie en el vano y no detrás de la pared: `[-0.6, y]` para `[-1, y]` y `[x, -0.6]` para `[x, -1]`.

- [ ] **Step 1: Escribir las pruebas que fallan.**

```js
// tests/js/casillas.test.mjs  (PUERTA = { clave: 'puerta', ancho: 1, fondo: 1, capa: 'pared', puerta: true })
test('la puerta tiene su casilla fuera de la pieza y otra enfrente', () => {
  const izquierda = depto([{ id: 9, ...PUERTA, x: -1, y: 2, giro: 0, casillas: [[-1, 2]] }]);
  assert.deepEqual(c.laPuerta(izquierda), { id: 9, celda: [-1, 2], dentro: [0, 2] });
  const derecha = depto([{ id: 9, ...PUERTA, x: 1, y: -1, giro: 0, casillas: [[1, -1]] }]);
  assert.deepEqual(c.laPuerta(derecha), { id: 9, celda: [1, -1], dentro: [1, 0] });
  assert.equal(c.laPuerta(depto([{ id: 1, ...CUADRO, x: -1, y: 0, giro: 0, casillas: [[-1, 0]] }])), null);
});

test('desde la puerta se entra por la casilla de enfrente, y por ella se sale', () => {
  const puerta = { id: 9, celda: [-1, 2], dentro: [0, 2] };
  assert.deepEqual(c.camino(3, 3, new Set(), [-1, 2], [2, 2], puerta), [[0, 2], [1, 2], [2, 2]]);
  assert.deepEqual(c.camino(3, 3, new Set(), [2, 0], [-1, 2], puerta).at(-1), [-1, 2]);
  assert.deepEqual(c.camino(3, 3, new Set(), [0, 1], [-1, 2], puerta), [[0, 2], [-1, 2]]);   // no se cuela desde (0, 1)
  assert.deepEqual(c.camino(3, 3, new Set(), [-1, 2], [-1, 2], puerta), []);
});

test('con la entrada tapada no se entra ni se sale', () => {
  const puerta = { id: 9, celda: [-1, 2], dentro: [0, 2] };
  const tapada = new Set(['0,2']);
  assert.deepEqual(c.camino(3, 3, tapada, [-1, 2], [2, 2], puerta), []);
  assert.deepEqual(c.camino(3, 3, tapada, [2, 2], [-1, 2], puerta), []);
});

test('sin puerta, su casilla no existe y nadie pasea hasta ella', () => {
  assert.deepEqual(c.camino(3, 3, new Set(), [0, 2], [-1, 2]), []);
  for (let n = 0; n < 20; n += 1) {
    const [i, j] = c.pasoSuelto(3, 3, new Set(), [0, 2], () => n / 20);
    assert.ok(i >= 0 && j >= 0);
  }
  assert.ok(c.sitiosDeEntrada(3, 3, new Set(), 9).every(([i, j]) => i >= 0 && j >= 0));
});

// tests/js/proyeccion.test.mjs
test('quien está en la puerta se pinta en su umbral', () => {
  assert.deepEqual(p.umbralDe([-1, 2]), [-0.6, 2]);
  assert.deepEqual(p.umbralDe([1, -1]), [1, -0.6]);
  const m = p.medir(380, 310, 3, 3);
  const [x, y] = p.proyectar(m, -0.6 + 0.5, 2 + 0.5);                  // sus pies
  const caja = p.cajaDelMueble(m, { ancho: 1, fondo: 1, capa: 'pared' }, -1, 2, 0);   // el tramo de la puerta
  assert.ok(x >= caja.x && x <= caja.x + caja.ancho);                   // dentro del ancho del vano
  assert.ok(y <= caja.y + caja.alto && y >= caja.y + caja.alto - m.th); // junto a su base
});

test('en la puerta se pinta antes que lo que tiene delante', () => {
  const tu = { tipo: 'tu', i: -0.6, j: 2 };
  const maceta = { tipo: 'mueble', i: 0, j: 2, a: 1, f: 1 };
  assert.deepEqual(p.ordenDePintado([maceta, tu]), [tu, maceta]);
});
```

- [ ] **Step 2: Verlas fallar.** Run: `node --test tests/js/casillas.test.mjs tests/js/proyeccion.test.mjs` — Expected: FAIL en las nuevas.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Verlas pasar**, y con ellas `tests/test_casillas_cliente.py` (el contraste con el servidor recorre ahora también la puerta). Run: `node --test tests/js/casillas.test.mjs tests/js/proyeccion.test.mjs && ./venv/bin/python -m pytest tests/test_casillas_cliente.py -q` — Expected: PASS.
- [ ] **Step 5: Commit** — `feat(web): la puerta en cuentas: su casilla, el paso por ella y dónde se pinta quien está ahí`.

---

### Task 4: La puerta en pantalla

**Files:**
- Modify: `web/static/js/departamento.js`, `web/static/js/pieza.js`, `web/static/js/lista.js`, `web/static/estilo.css` (si hace falta), `tests/js/departamento.test.mjs`, `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: Task 1 (`puerta` en cada puesto; el rechazo `no_se_guarda`), Task 2 (su dibujo, que `rutaDelMueble` ya arma), Task 3 (`laPuerta`, `camino` con puerta, `umbralDe`).
- Produces (en la pantalla):
  - **Al entrar apareces en la puerta**: tu avatar parte en la casilla de la puerta, pintado en su umbral. Los gachamones se reparten por la pieza como hoy. Si el departamento no trae puerta, todo como hoy.
  - **Caminar** cuenta con la puerta: desde ella se entra por la casilla de enfrente; si está tapada, no hay camino y no vas (te quedas en la puerta), pero puedes tocar cualquier mueble y moverlo.
  - **Tocar la puerta la elige**: su menú trae su nombre y `✋ Mover` y `🚪 Salir`. No trae «Girar» ni «Guardar».
  - **Mover** la puerta es como mover un cuadro (se marcan los tramos libres de las dos paredes). Si estabas en su casilla, sigues en ella, en el sitio nuevo; si estabas dentro, no te mueves.
  - **Salir**: caminas hasta la puerta y, al llegar, vas al pueblo (lo mismo que el botón «Pueblo»). Si ya estás en ella, sales al momento. Tocar otra cosa mientras caminas cancela la salida. Con movimiento reducido, sales sin caminar. Si no hay camino: `No hay camino hasta la puerta.` y no se sale. Mientras va una petición, no se sale.
  - **En la lista**: la puerta va en «Muebles puestos» con su nombre y su sitio, y sus botones `Mover` y `Salir`.
  - Nunca aparece en la bandeja de guardados.

- [ ] **Step 1: Escribir las pruebas que fallan**, en `tests/js/departamento.test.mjs`. Los departamentos de ejemplo ganan su puerta (`PUERTA_ID`, en `(-1, 2)`, con `puerta: true`); `SIN_PUERTA` es el de antes. `dondeEstas(pantalla)` dice en qué casilla se pintó tu avatar (como ya lo mira la prueba del toque contado desde la esquina); las pruebas de caminar usan `correrCuadros`.

```js
test('al entrar apareces en la puerta', async () => {
  const { pantalla } = await abrir(DEPTO);
  assert.deepEqual(dondeEstas(pantalla), [-0.6, 2]);                   // su umbral
});

test('sin puerta se entra como antes', async () => {
  const { pantalla } = await abrir(SIN_PUERTA);
  assert.deepEqual(dondeEstas(pantalla), [2, 2]);
  assert.equal(todos(pantalla, '.lista-puestos li').some((f) => /Salir/.test(f.textContent)), false);
});

test('desde la puerta se camina hacia adentro por la casilla de enfrente', async () => {
  const { pantalla } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 2, 2);
  await correrCuadros(5000);
  assert.deepEqual(dondeEstas(pantalla), [2, 2]);
});

test('con la entrada tapada te quedas en la puerta, y puedes mover lo que estorba', async () => {
  const tapada = conPuesto(DEPTO, { id: MACETA_ID, ...MACETA, nombre: 'Maceta', x: 0, y: 2, giro: 0, casillas: [[0, 2]] });
  const { pantalla, pedidos, servidor } = await abrir(tapada);
  await tocarCasilla(pantalla, 2, 2);
  await correrCuadros(5000);
  assert.deepEqual(dondeEstas(pantalla), [-0.6, 2]);                   // no va
  servidor.responde('POST departamento/poner', BIEN(conPuesto(DEPTO, { id: MACETA_ID, ...MACETA, nombre: 'Maceta', x: 2, y: 0, giro: 0, casillas: [[2, 0]] })));
  await tocarCasilla(pantalla, 0, 2); await tocar(boton(menu(pantalla), 'Mover')); await tocarCasilla(pantalla, 2, 0);
  assert.equal(pedidos.at(-1)[0], 'POST departamento/poner');
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  assert.deepEqual(dondeEstas(pantalla), [2, 2]);                      // ahora sí
});

test('el menú de la puerta trae mover y salir, y nada más', async () => {
  const { pantalla } = await abrir(DEPTO);
  await tocarTramo(pantalla, -1, 2);
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Puerta');
  assert.deepEqual(rotulos(menu(pantalla)), ['Mover', 'Salir']);
});

test('salir desde la puerta lleva al pueblo al momento', async () => {
  const { pantalla, seguido, pedidos } = await abrir(DEPTO);
  await tocarTramo(pantalla, -1, 2);
  await tocar(boton(menu(pantalla), 'Salir'));
  assert.deepEqual(seguido.at(-1)[1], { vista: 'pueblo' });
  assert.equal(pedidos.filter(([ruta]) => ruta.startsWith('POST')).length, 0);
});

test('salir desde dentro camina hasta la puerta y entonces va al pueblo', async () => {
  const { pantalla, seguido } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  await tocarTramo(pantalla, -1, 2); await tocar(boton(menu(pantalla), 'Salir'));
  assert.equal(seguido.length, 0);                                     // todavía va caminando
  await correrCuadros(5000);
  assert.deepEqual(seguido.at(-1)[1], { vista: 'pueblo' });
});

test('tocar otra cosa mientras caminas a la puerta cancela la salida', async () => {
  const { pantalla, seguido } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  await tocarTramo(pantalla, -1, 2); await tocar(boton(menu(pantalla), 'Salir'));
  await correrCuadros(100);
  await tocarCasilla(pantalla, 2, 1);
  await correrCuadros(5000);
  assert.equal(seguido.length, 0);
  assert.deepEqual(dondeEstas(pantalla), [2, 1]);
});

test('sin camino hasta la puerta no se sale y se dice', async () => {
  const { pantalla, seguido, servidor } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  servidor.responde('GET departamento', conPuesto(DEPTO, { id: MACETA_ID, ...MACETA, nombre: 'Maceta', x: 0, y: 2, giro: 0, casillas: [[0, 2]] }));
  await releer(pantalla);
  await tocarTramo(pantalla, -1, 2); await tocar(boton(menu(pantalla), 'Salir'));
  await correrCuadros(5000);
  assert.equal(seguido.length, 0);
  assert.equal(texto(pantalla, '[role=status].aviso'), 'No hay camino hasta la puerta.');
});

test('con menos movimiento se sale sin caminar', async () => {
  const { pantalla, seguido } = await abrir(DEPTO, ESTADO, { movimientoReducido: true });
  await tocarCasilla(pantalla, 2, 2);
  await tocarTramo(pantalla, -1, 2); await tocar(boton(menu(pantalla), 'Salir'));
  assert.deepEqual(seguido.at(-1)[1], { vista: 'pueblo' });
});

test('mover la puerta estando en ella te lleva con ella; estando dentro, no', async () => {
  const movida = moverPuesto(DEPTO, PUERTA_ID, { x: 1, y: -1, casillas: [[1, -1]] });
  let { pantalla, pedidos, servidor } = await abrir(DEPTO);
  servidor.responde('POST departamento/poner', BIEN(movida));
  await tocarTramo(pantalla, -1, 2); await tocar(boton(menu(pantalla), 'Mover')); await tocarTramo(pantalla, 1, -1);
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: PUERTA_ID, x: 1, y: -1, giro: 0 }]);
  assert.deepEqual(dondeEstas(pantalla), [1, -0.6]);
  ({ pantalla, servidor } = await abrir(DEPTO));
  servidor.responde('POST departamento/poner', BIEN(movida));
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  await tocarTramo(pantalla, -1, 2); await tocar(boton(menu(pantalla), 'Mover')); await tocarTramo(pantalla, 1, -1);
  assert.deepEqual(dondeEstas(pantalla), [2, 2]);
});

test('en la lista, la puerta se mueve y por ella se sale, pero no se gira ni se guarda', async () => {
  const { pantalla, seguido } = await abrir(DEPTO);
  const fila_ = fila(pantalla, PUERTA_ID);
  assert.equal(texto(fila_, '.mueble-nombre'), 'Puerta, en la pared izquierda, tramo 3');
  assert.deepEqual(rotulos(fila_), ['Mover', 'Salir']);
  await tocar(boton(fila_, 'Salir'));
  assert.deepEqual(seguido.at(-1)[1], { vista: 'pueblo' });
});

test('los gachamones no llegan a la puerta', async () => {
  const { pantalla } = await abrir(CON_DOS, ESTADO, { azar: () => 0 });
  for (let n = 0; n < 40; n += 1) await correrReloj(9000);
  assert.ok(dondeEstanLosGachamones(pantalla).every(([i, j]) => i >= 0 && j >= 0));
});
```

```python
# tests/test_web_cliente.py
def test_el_cliente_reconoce_la_puerta_por_su_marca_y_no_por_su_clave():
    for nombre in ("departamento.js", "pieza.js", "lista.js", "casillas.js", "proyeccion.js", "plantel.js", "flotantes.js"):
        codigo = _sin_comentarios(_guion(nombre))
        assert "'puerta'" not in codigo and '"puerta"' not in codigo, nombre
    assert ".puerta" in _guion("casillas.js")
```

- [ ] **Step 2: Verlas fallar.** Run: `node --test tests/js/departamento.test.mjs` — Expected: FAIL en las nuevas. Las pruebas de hoy que miran dónde está tu avatar al entrar pasan a usar `SIN_PUERTA` o a esperar la puerta, sin perder lo que comprueban; el informe las lista.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Mirarlo** con el arnés, en 390 y en 1280: recién entrado (en la puerta), caminando hacia adentro, el menú de la puerta, la puerta movida a la otra pared, la entrada tapada por un mueble, y la salida al pueblo. Las capturas van al informe.
- [ ] **Step 5: La suite entera** (Python y JavaScript). Expected: PASS.
- [ ] **Step 6: Commit** — `feat(web): la puerta del departamento: apareces en ella al entrar y por ella sales`.

---

### Task 5: Los documentos

**Files:**
- Modify: `AGENTS.md`, `README.md`, `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md` (el diseño ya trae su sección 4.5 desde que se confirmó este plan)

**Interfaces:**
- **`AGENTS.md`**, una o dos líneas, concisas y sin SHAs: cada departamento tiene exactamente una puerta, siempre puesta: nace con él, no se vende ni se guarda y se mueve como lo de pared; su casilla queda fuera de la pieza y sólo la pisa tu avatar; el cliente la reconoce por la marca que manda el servidor.
- **`README.md`**: en «Tu casa», una frase: apareces en la puerta, que se puede mover de pared, y por ella también se sale al pueblo.
- **Pendientes**: lo decidido (las seis decisiones de Felipe y las cuatro propuestas del plan) y lo que queda: un departamento hecho antes de este plan no tiene puerta (no hay ninguno en producción: nacen todos el día del cambio, ya con ella); el dibujo es de relleno; los gachamones no usan la puerta; visitar a otros es de otro proyecto.

- [ ] **Step 1: Escribir** los tres documentos.
- [ ] **Step 2: Comprobar** que cada invariante nuevo de `AGENTS.md` es verdad en el código (`git grep`).
- [ ] **Step 3: La verificación completa.** Run: `./venv/bin/python -m pre_commit run --all-files` — Expected: PASS.
- [ ] **Step 4: Commit** — `docs: la puerta del departamento, en la política, el README y los pendientes`.
