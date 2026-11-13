# Gachamon web · Plan 4 — La tienda y la mochila

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que quien juega en `rowino.online/gachamon` entre a la Tienda del pueblo y compre objetos, cosméticos, casas y muebles, y que desde cualquier lugar abra su mochila y use lo que lleva — con las mismas reglas y el mismo dinero que en Discord, sin que un toque doble o una red que falla cobre dos veces.

**Architecture:** Las reglas de comprar ya viven en `economia.py`; este plan les añade lo que la web necesita y Discord no pedía: un **motivo** en cada rechazo (la web escribe sus propias frases), un **evento** en las compras que no llevan libro contable (para que repetir no cobre dos veces) y **usar un objeto** como regla del juego, que hoy vive pegada al menú de Discord. La web gana dos routers finos (`web/tienda.py`, `web/mochila.py`) que traducen peticiones y arman frases, y el cliente dos pantallas (`tienda.js`, `mochila.js`) que se abren desde el lugar donde estás, igual que el pueblo. El servidor dice qué ofrece cada lugar; comprar exige estar en la Tienda.

**Tech Stack:** Lo de los planes 2 y 3, sin dependencias nuevas: Python 3.12 y 3.14, FastAPI 0.162.5, SQLite síncrono, Pillow 12.3.0 (rellenos), pytest 9.1.1; JavaScript del navegador en módulos, probado con `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-12-gachamon-web-parte-a-design.md` — secciones 5.1 (la forma de la API y el evento por acción), 5.3 (la navegación del lugar), 5.5 (Tienda y Mochila), 5.8 (cosméticos que quedan) y 5.9 (íconos en el contrato de arte). Lo que el reconocimiento encontró en el código está en `.superpowers/sdd/2026-11-13-gachamon-web-4-reconocimiento/` (no versionado): son afirmaciones de exploradores, y cada tarea comprueba contra el código las que usa.

**Lo que queda de la parte A, en cuatro planes** (decidido con Felipe el 2026-11-13):

4. **La tienda y la mochila** — este.
5. **La ficha, el ropero, la incubadora y el refugio.**
6. **Tu casa** — el interior, mudar, el huerto y la cocina, el buzón.
7. **Hablar y la apertura** — la conversación con IA, cambiar el avatar, el enlace en Rowino con retorno del inicio de sesión, y el aviso en el canal.

## Lo que decidió Felipe para este plan

- **Lo que hoy sólo sirve en Discord** —las pociones de fuerza y de velocidad y el descanso rápido (competencias), y las semillas mientras la web no tenga huerto—: a quien **no** tiene Discord vinculado, la tienda **lo enseña sin venderlo**, marcado «Más adelante.»; a quien sí lo tiene, se lo vende diciendo dónde sirve.
- **El reloj del refugio sigue sin arrancar** para quien juega sólo en la web: gana como mucho 12 monedas al día cuidando y la casa pequeña cuesta 200, así que con el plazo de 7 días quedaría a la intemperie antes de poder comprarla. Es una excepción temporal, como la del hambre, hasta que la parte B le dé más formas de ganar monedas.

## Lo que este plan decide y Felipe tiene que mirar

Son propuestas mías donde el diseño deja la decisión a quien construye. Si alguna no te gusta, se cambia antes de ejecutar.

- **«Sin plazo» se cumple siempre, no sólo mientras no compres nada.** Comprar una casa crea el reloj del refugio; si después la vendes, en Discord ese reloj corre. Para que la decisión de arriba no tenga agujeros, quien juega sólo en la web **nunca** queda a la intemperie, tenga o haya tenido casa. Consecuencia: el **ticket del refugio** no le sirve y la tienda no se lo vende («No lo necesitas: tu estancia en el refugio no tiene plazo.»).
- **Comprar exige estar en la Tienda.** La mochila se abre desde cualquier lugar. Lo hace cumplir el servidor, no sólo la pantalla.
- **Toda compra se confirma con un segundo toque** en la misma fila («¿Comprar por 10 monedas?» · Comprar · No). Con 12 monedas al día, un toque sin querer duele. Vender una casa dice antes lo que pasa: «¿Vender tu casa pequeña por 160 monedas? Sus 2 muebles quedan guardados, sus 3 gachamones se van al refugio y lo plantado se pierde.»
- **Un cosmético recién comprado se lo pone tu gachamon**, como en Discord. Quitárselo o cambiarlo llega con el ropero (plan 5); lo que llevaba no se pierde. Para que un **título** comprado se vea desde ya, la ficha lo enseña junto al nombre.
- **Los muebles se compran aquí y se cuelgan solos si caben** en tu primera casa; elegir casa, colocar y retirar llega con «Tu casa» (plan 6).
- **Usar un objeto también se confirma** («¿Usar?»). La placa pide el nombre nuevo ahí mismo.
- **Los íconos** de objetos, cosméticos, muebles y casas son archivos del contrato de arte: 62 piezas de 48 × 48, con relleno que se nota.
- **Las frases nuevas** (las escribí yo; cámbialas si no suenan a tu juego):
  - En la Tienda, el gachamon pasa a decir «Cuántas cosas hay en los estantes.», «Huele a madera y a pintura fresca.» y «¿Me compras algo?»; el pollito, «Pío, cuántas cosas.» y «Pío… huele a madera nueva.». Se van las de los estantes vacíos y la de que abrirá pronto.
  - Al comprar: «Compraste Poción de comida. Está en tu mochila.» · «Compraste Corona. Pelusa ya lo lleva.» · «Compraste Felpudo. Ya está puesto en tu casa.» / «…No cabía en tu casa: quedó guardado.» · «Compraste una casa pequeña.» · «Tu casa pequeña ahora es una casa mediana.» · «Vendiste tu casa pequeña por 160 monedas.»
  - Al no poder: «Te faltan 12 monedas.» · «Te faltan 10 gemas. Se ganan con las medallas.» · «Ya lo tienes.» · «Ya tienes 3 casas, que es el máximo. Vende una o mejora las que tienes.» · «Los muebles van en una casa, y todavía no tienes.» · «Para eso tienes que estar en la tienda.»
  - En la mochila: «Pelusa ya puede entrenar otra vez.» · «Pelusa gana +3 de fuerza durante 5 minutos.» · «Pelusa come. Comida +25 (ahora 80).» · «Pelusa pasa a llamarse Nube.» · «Ya no te queda ninguno.» · «Eso no se usa desde la mochila.» · «Se usa en el huerto.» · «Tu mochila está vacía. Lo que compres en la tienda aparece aquí.»
  - A quien tiene Discord, bajo lo que sólo sirve allá: «Sirve en las competencias, que por ahora se juegan en Discord.» y «Se siembra en el huerto, que por ahora está en Discord.»
- **En Discord cambia una cosa, y es un arreglo:** usar un objeto de la mochila pasa a ser una sola operación. Hoy, si tu gachamon ya había muerto sin que nadie lo registrara, el objeto se gastaba igual; ahora no se gasta. Los textos de Discord no cambian.

## Global Constraints

- Todo lo de `AGENTS.md` y las restricciones globales de los planes 2 y 3 siguen mandando. Las que más pesan aquí:
  - `web/` no importa `discord`, ni directa ni indirectamente (`tienda.py`, `vistas.py`, `equipo.py`, `comun.py` y `cogs/` lo importan).
  - El servicio no guarda estado del juego en memoria.
  - Quién eres sale sólo de la cookie de Rowino; ninguna ruta acepta un id de persona.
  - Toda ruta que cambia algo es `POST` o `PUT` y exige `X-Gachamon: 1`. Las rutas se declaran con `def`.
  - Un error se contesta siempre como `{"detail": {"clave": "<clave>", "mensaje": "<frase>"}}`.
  - Toda mutación va bajo `BEGIN IMMEDIATE` y dentro de `db.py` o `economia.py`. `db.py` no importa `economia.py` ni nada de `web/`.
  - El reloj es `db.ahora_utc()`; en las pruebas, el tiempo y el azar se inyectan y la base es temporal.
- **El dinero no se duplica.** Toda petición que compra, vende o gasta lleva un `evento_id` del cliente (`[A-Za-z0-9-]{8,64}`, el mismo patrón de `web/juego.py`); repetirla con el mismo evento devuelve lo que pasó la primera vez y no cobra, no entrega ni gasta otra vez. Un evento reutilizado para otra cosa es un error (409 `evento`).
- **Un «no» del juego no es un error HTTP.** Como en `POST /cuidar`: si la regla dice que no (no alcanza, ya lo tienes…), la respuesta es 200 con `ok: false`, la `clave` del motivo y una frase. Los 4xx son para peticiones que la pantalla nunca hace (cuerpo mal hecho, no estás en la tienda, eso no se te vende).
- **Las frases de la web las escribe la web**, en texto llano: sin `**`, sin `-#`, sin nombrar comandos ni botones de Discord. Las de `economia` (`problema`) son de Discord y no se enseñan en la web. A quien juega se le dice «monedas» y «gemas», en singular cuando es una (`objetos.nombre_de_monedas`, `objetos.nombre_de_gemas`).
- **Lo que Discord hace hoy no cambia** salvo donde este plan lo dice: los parámetros nuevos de `economia` son opcionales y, sin ellos, cada función se comporta como antes.
- **Mirar no escribe.** Las lecturas de la web usan `db.hogar_leido`, nunca `db.hogar_de` (que empieza la estancia en el refugio).
- **El cliente no usa frameworks ni compilación, nunca mete texto con `innerHTML`, y no contiene `http://` ni `https://`.** Los módulos se importan con rutas relativas terminadas en `.js`. Ninguna dependencia nueva, ni de Python ni de JavaScript.
- **Las reglas son del servidor.** El servidor decide qué se vende, a quién, a cuánto y si se puede usar; el cliente pinta lo que le dicen y no calcula precios ni permisos.
- **El pueblo vive en datos.** El código sólo nombra un lugar por su clave donde le da un significado, y una prueba vigila que esas claves existan en `pueblo.json`.
- **Arte:** cada dibujo nuevo es un archivo bajo `web/static/arte/` descrito en `web/arte.py`. El relleno se nota. Si un archivo falta, se ve el recuadro de esa pieza y nunca el dibujo de otra.
- El análisis de impacto de GitNexus lo corre el controlador antes de cada tarea que toque un símbolo existente; el índice se refresca sólo con `node .gitnexus/run.cjs analyze --index-only`.
- Antes de cada commit: `./venv/bin/python -m pre_commit run --all-files && git diff --check`, encadenados con `&&` al commit y **sin tuberías**.
- **Nada de push, merge ni despliegue sin autorización explícita de Felipe.**
- Rama de trabajo: `web/4-la-tienda-y-la-mochila`, desde `main`. Un commit por tarea.

## Review Focus

1. **Doble toque o reintento al comprar** (la respuesta no llegó y el cliente repite): no se cobra dos veces, no se compran dos casas, no se gastan dos objetos; la segunda respuesta cuenta lo mismo que la primera. → Tareas 3, 4, 6 y 7.
2. **El gachamon murió o cambió mientras mirabas la tienda o la mochila** (otra pestaña, Discord, el tiempo): nada se le aplica al relevo, no se gasta el objeto, y la pantalla vuelve a decidir. → Tareas 4, 6 y 7.
3. **El saldo o la mochila cambiaron por la otra cara** entre ver y comprar: decide el servidor con lo que hay en ese instante y la pantalla se pone al día con la respuesta. → Tareas 6, 7 y 9.
4. **Una petición hecha a mano**: comprar sin estar en la tienda, comprar lo que no se vende (un poroto), lo que no se le vende a esa cuenta, o usar lo que no se usa desde la mochila. Ninguna cobra ni gasta, y ninguna contesta 500. → Tareas 1, 6 y 7.
5. **Falta el ícono de una pieza**: se ve su recuadro, y se puede comprar y usar igual. → Tareas 8, 9 y 10.

**Sobre las pruebas de este plan.** Los nombres de ayuda que aparecen en ellas (`base`, `U`, `G`, `YO`, `T0`, `nace`, `dar`, `dar_monedas`, `hambrear`, `en_la_tienda_con`, `TIENDA`, `COMPRAR`, `MOCHILA`, `USAR`…) son los de las pruebas vecinas o ayudas pequeñas que cada archivo escribe al principio; `dar_monedas(quien, n)` **deja** el saldo en `n`. Lo que manda son los nombres de las pruebas y sus aserciones, con sus valores.

---

### Task 1: Los rechazos dicen por qué

Las funciones de compra de `economia` devuelven, cuando algo no se puede, una frase escrita para Discord. La web necesita saber **por qué** para escribir la suya.

**Files:**
- Modify: `economia.py`, `objetos.py`
- Test: `tests/test_motivos.py` (nuevo)

**Interfaces:**
- Produces:
  - `ResultadoCosmetico`, `ResultadoMudanza`, `ResultadoVenta` y `ResultadoMueble` ganan `motivo: str | None = None`. `ResultadoMueble` gana además `colocado: bool = False` (si **ese** mueble quedó puesto tras la operación).
  - Motivos, uno por cada rechazo que hoy existe:
    - `comprar_cosmetico`: `"ya_lo_tienes"`, `"faltan_gemas"`.
    - `comprar_casa`: `"no_es_tuya"`, `"no_se_empeora"`, `"maximo_de_casas"`, `"faltan_monedas"`.
    - `vender_casa`: `"sin_casa"` (no tiene ninguna), `"no_es_tuya"`.
    - `comprar_mueble`, `colocar_mueble` y `retirar_mueble`, lo común: `"sin_casa"` (vive en el refugio), `"intemperie"`, `"no_es_tuya"`. Además, en `comprar_mueble`: `"ya_lo_tienes"`, `"faltan_monedas"`.
  - Los `problema` (las frases) no cambian ni una letra, y un resultado con `ok=True` lleva `motivo=None`.
  - `objetos.a_la_venta() -> tuple[Objeto, ...]` — lo del catálogo con `se_vende`, en el orden del catálogo.
  - `economia.comprar(...)` lanza `ValueError` si `not objeto.se_vende`, antes de abrir la base.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_motivos.py`, sobre la base temporal (mira cómo dan monedas, gemas y casas `tests/test_casas.py` y `tests/test_cosmeticos.py`):

```python
def test_lo_que_no_se_vende_no_se_compra(base):
    poroto = obj.CATALOGO["poroto_rojo"]
    assert not poroto.se_vende
    with pytest.raises(ValueError):
        economia.comprar("evento-0001", U, G, poroto, T0)
    assert db.inventario(U, G) == {}


def test_a_la_venta_es_el_catalogo_sin_lo_que_se_cosecha_o_se_cocina():
    claves = [o.clave for o in obj.a_la_venta()]
    assert claves == [c for c, o in obj.CATALOGO.items() if o.se_vende]
    assert len(claves) == 17 and "semilla" in claves and "poroto_rojo" not in claves
```

Y una prueba por motivo, con nombre que lo diga (`test_el_cosmetico_que_ya_tienes_dice_ya_lo_tienes`, etc.): provoca el rechazo y afirma `resultado.ok is False`, `resultado.motivo == "<clave>"` y que `resultado.problema` sigue siendo una frase no vacía. Para el mueble: comprado con sitio → `colocado is True`; comprado con la casa llena → `ok is True and colocado is False`. Una más: todas las compras que salen bien llevan `motivo is None`.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_motivos.py -q`
Expected: FAIL — los resultados no tienen `motivo`, no existe `a_la_venta`, y comprar un poroto lanza `IntegrityError`.

- [ ] **Step 3: Implementar**

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_motivos.py tests/test_casas.py tests/test_cosmeticos.py tests/test_tienda.py -q`
Expected: PASS, sin tocar ninguna prueba que ya existía.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(economia): cada rechazo de compra dice su motivo, y lo que no se vende no se compra"
```

---

### Task 2: El refugio no tiene plazo para quien juega sólo en la web

**Files:**
- Modify: `identidad.py`, `db.py` (`_hogar_leido`), `AGENTS.md`
- Test: `tests/test_identidad.py`, `tests/test_web_lugar.py`

**Interfaces:**
- Produces:
  - `identidad.sin_plazo_de_refugio(usuario_id: str) -> bool` — cierto para una identidad web.
  - `db._hogar_leido` (y con él `hogar_de`, `hogar_leido` y `_avanzar_en`): para esas identidades el `Hogar` sale con `refugio_hasta = casas.estancia_desde(ahora)` diga lo que diga la fila. Así `Hogar.estado` y `Hogar.estado_de` nunca dan `INTEMPERIE` para ellas, tengan o hayan tenido casa. La fila de `hogar` no se toca.
  - Una cuenta **vinculada** actúa con su id de Discord: para ella nada cambia.
- En `AGENTS.md`, al final de «Invariantes del dominio», tal cual:

```markdown
- Quien juega sólo en la web no tiene plazo en el refugio: su estancia no vence y nunca queda a la intemperie, tenga o haya tenido casa. Esa excepción se pregunta siempre con `identidad.sin_plazo_de_refugio`, nunca mirando el id.
```

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_identidad.py`:

```python
def test_quien_juega_solo_en_la_web_no_tiene_plazo_en_el_refugio():
    assert identidad.sin_plazo_de_refugio(identidad.de_cuenta_web(12)) is True
    assert identidad.sin_plazo_de_refugio("222222222222222222") is False


def test_una_identidad_web_nunca_queda_a_la_intemperie(base):
    web = identidad.de_cuenta_web(1)
    db.hogar_de(web, G, T0)                         # empieza la estancia, como hará comprar una casa
    mucho_despues = T0 + timedelta(days=400)
    hogar = db.hogar_leido(web, G, mucho_despues)
    assert hogar.estado(mucho_despues) == casas.REFUGIO
    assert hogar.estado_de(None, mucho_despues) == casas.REFUGIO


def test_a_quien_viene_de_discord_el_plazo_le_corre_como_siempre(base):
    db.hogar_de("222222222222222222", G, T0)
    despues = T0 + timedelta(days=casas.DIAS_DE_REFUGIO, seconds=1)
    assert db.hogar_leido("222222222222222222", G, despues).estado(despues) == casas.INTEMPERIE
```

Y otra: una identidad web que compra una casa, la vende y deja pasar 30 días sigue en `REFUGIO`.

En `tests/test_web_lugar.py`, las tres pruebas de la intemperie usan hoy una cuenta que sólo juega en la web, y eso deja de poder pasar: cámbialas para que la cuenta esté **vinculada** a una identidad de Discord sintética (mira cómo lo hacen las pruebas que ya usan una cuenta vinculada), y añade `test_quien_juega_solo_en_la_web_no_ve_el_aviso_de_la_intemperie`: la cuenta web con la estancia «vencida» sigue con `estado["hogar"] == "refugio"` y `lugar["aviso"] is None`.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_identidad.py tests/test_web_lugar.py -q`
Expected: FAIL — no existe `sin_plazo_de_refugio` y la identidad web queda a la intemperie.

- [ ] **Step 3: Implementar**

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_identidad.py tests/test_web_lugar.py tests/test_casas.py tests/test_web_estado.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(reglas): quien juega sólo en la web no tiene plazo en el refugio"
```

---

### Task 3: Una compra no se cobra dos veces

Comprar un objeto ya es idempotente por evento (lleva fila en `operaciones_economia`). Las demás compras no llevan libro: un cosmético o un mueble repetido se frena solo («ya lo tienes»), pero **una casa nueva repetida compra dos**. Este plan les da a todas el mismo trato.

**Files:**
- Modify: `db.py` (tabla y dos funciones), `economia.py`
- Test: `tests/test_acciones_unicas.py` (nuevo)

**Interfaces:**
- Produces, en `db.py`:
  - Tabla nueva, creada con el esquema (`CREATE TABLE IF NOT EXISTS`):

```sql
CREATE TABLE IF NOT EXISTS acciones_unicas (
    evento_id  TEXT NOT NULL,
    usuario_id TEXT NOT NULL,
    guild_id   TEXT NOT NULL,
    accion     TEXT NOT NULL,
    solicitud  TEXT NOT NULL,
    resultado  TEXT NOT NULL,
    cuando     TEXT NOT NULL,
    PRIMARY KEY (evento_id, usuario_id, guild_id, accion)
)
```

  - `accion_hecha_en(con, evento_id: str, usuario_id: str, guild_id: str, accion: str) -> tuple[str, dict] | None` — la `solicitud` y el `resultado` (JSON ya leído) de ese evento, o `None`.
  - `anotar_accion_en(con, evento_id: str, usuario_id: str, guild_id: str, accion: str, solicitud: str, resultado: dict, ahora: datetime) -> None`.
- Produces, en `economia.py` — un parámetro opcional al final de cada firma, y `replay: bool = False` en los cuatro resultados:
  - `comprar_cosmetico(usuario_id, guild_id, cosmetico, evento_id: str | None = None)`
  - `comprar_casa(usuario_id, guild_id, casa, ahora=None, mejorar=None, evento_id: str | None = None)`
  - `vender_casa(usuario_id, guild_id, casa_id, ahora=None, evento_id: str | None = None)`
  - `comprar_mueble(usuario_id, guild_id, mueble, ahora=None, casa_id=None, evento_id: str | None = None)`
- La regla, igual en las cuatro, dentro del mismo `BEGIN IMMEDIATE` de la operación:
  - **Sin `evento_id`**, todo como hoy (es lo que usa Discord).
  - **Con `evento_id` ya anotado** para esa persona y esa acción: si la `solicitud` es otra, `RuntimeError`; si es la misma, devuelve `ok=True, replay=True` sin cobrar ni cambiar nada, con el saldo de ahora y las piezas del catálogo que nombra lo anotado.
  - **Con `evento_id` nuevo**: hace lo de siempre y, **sólo si salió bien**, lo anota. Un rechazo no se anota: repetirlo vuelve a decidir.

| Función | `accion` | `solicitud` | `resultado` anotado |
|---|---|---|---|
| `comprar_cosmetico` | `cosmetico` | la clave | `{"sustituido": clave o null}` |
| `comprar_casa` | `casa` | `"<clave>"` o `"<clave>:<mejorar>"` | `{"casa_id": int, "desde": clave o null}` |
| `vender_casa` | `venta` | `str(casa_id)` | `{"casa": clave, "cobrado": int, "guardados": int, "desalojados": int}` |
| `comprar_mueble` | `mueble` | `"<clave>:<casa_id o vacío>"` | `{"colocado": bool, "casa_id": int}` |

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_acciones_unicas.py`:

```python
def test_repetir_la_compra_de_una_casa_con_el_mismo_evento_no_compra_otra(base):
    dar_monedas(U, 1000)
    pequena = casas.CATALOGO["pequena"]
    primera = economia.comprar_casa(U, G, pequena, T0, evento_id="evento-casa-1")
    segunda = economia.comprar_casa(U, G, pequena, T0, evento_id="evento-casa-1")
    assert primera.ok and not primera.replay
    assert segunda.ok and segunda.replay and segunda.casa_id == primera.casa_id
    assert len(db.hogar_leido(U, G, T0).casas) == 1
    assert economia.saldos(U, G).asciicoins == 1000 - pequena.precio == segunda.saldo


def test_sin_evento_cada_compra_de_casa_es_otra_casa(base):
    dar_monedas(U, 1000)
    pequena = casas.CATALOGO["pequena"]
    assert economia.comprar_casa(U, G, pequena, T0).ok and economia.comprar_casa(U, G, pequena, T0).ok
    assert len(db.hogar_leido(U, G, T0).casas) == 2


def test_un_evento_no_sirve_para_otra_cosa(base):
    dar_monedas(U, 2000)
    economia.comprar_casa(U, G, casas.CATALOGO["pequena"], T0, evento_id="evento-casa-1")
    with pytest.raises(RuntimeError):
        economia.comprar_casa(U, G, casas.CATALOGO["mediana"], T0, evento_id="evento-casa-1")


def test_un_rechazo_no_gasta_el_evento(base):
    pequena = casas.CATALOGO["pequena"]
    assert economia.comprar_casa(U, G, pequena, T0, evento_id="evento-casa-1").motivo == "faltan_monedas"
    dar_monedas(U, 1000)
    hecha = economia.comprar_casa(U, G, pequena, T0, evento_id="evento-casa-1")
    assert hecha.ok and not hecha.replay
```

Y, con el mismo molde: el cosmético (segunda vez `ok and replay`, las gemas se cobran una vez, `sustituido` es el mismo); la venta (segunda vez `ok and replay` con el mismo `cobrado`, las monedas entran una vez); la mejora (segunda vez `ok and replay`, no «no se puede empeorar»); el mueble (segunda vez `ok and replay` con el mismo `colocado`). Una de persona: el mismo `evento_id` usado por **otra** persona no es un replay.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_acciones_unicas.py -q`
Expected: FAIL — `comprar_casa` no acepta `evento_id`.

- [ ] **Step 3: Implementar**

Una sola ayuda privada en `economia.py` para «¿ya se hizo?» y otra para «anótalo»; las cuatro funciones la usan, sin repetir el bloque.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_acciones_unicas.py tests/test_motivos.py tests/test_casas.py tests/test_cosmeticos.py tests/test_db.py -q`
Expected: PASS, sin tocar ninguna prueba que ya existía.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(economia): repetir una compra con el mismo evento no cobra dos veces"
```

---

### Task 4: Usar un objeto es una regla del juego

Hoy «usar» vive en `tienda.py`, que importa `discord`: el menú gasta la unidad, avanza y guarda al gachamon, y aplica el efecto, cada paso en su propia transacción y sin evento. La web no puede importarlo, y un reintento gastaría dos unidades.

**Files:**
- Modify: `economia.py`, `db.py`, `tienda.py`
- Test: `tests/test_usar_objeto.py` (nuevo); las pruebas que hoy llaman a `tienda.usar` o `tienda.renombrar` (`tests/test_tienda.py`, `tests/test_casas.py`, `tests/test_textos.py`)

**Interfaces:**
- Consumes: `acciones_unicas` (tarea 3, acción `"uso"`); `identidad.sin_plazo_de_refugio` (tarea 2).
- Produces, en `economia.py`:

```python
@dataclass(frozen=True)
class ResultadoUso:
    ok: bool = False
    motivo: str | None = None            # sin_gachamon | no_tienes | no_se_usa | sin_plazo | nombre | mismo_nombre
    problema: str | None = None          # la frase de quien valida el nombre, cuando motivo == "nombre"
    objeto: str = ""
    criatura: sim.Criatura | None = None  # cómo queda
    efecto: str | None = None            # reinicia | estadistica | sopaipilla | refugio | comida | nombre
    accion: str | None = None            # la que queda libre, si efecto == "reinicia"
    stats: tuple[str, ...] = ()
    bonus: int = 0
    caras: int = 0
    gusto: str | None = None             # `huerto.le_gusta`, en la sopaipilla de color
    comida: int = 0                      # cuánta ganó
    refugio_hasta: datetime | None = None
    nombre_anterior: str = ""
    replay: bool = False
```

  - `usar_objeto(evento_id: str, usuario_id: str, guild_id: str, objeto: obj.Objeto, ahora: datetime | None = None, rng: random.Random | None = None) -> ResultadoUso`
  - `renombrar_con_placa(evento_id: str, usuario_id: str, guild_id: str, objeto: obj.Objeto, propuesto: str, ahora: datetime | None = None) -> ResultadoUso`
- Las dos, bajo **un solo** `BEGIN IMMEDIATE`, en este orden:
  1. Si el evento ya está anotado (acción `"uso"`; solicitud: la clave, o `"<clave>:<nombre>"` en la placa): otra solicitud → `RuntimeError`; la misma → lo anotado, con `replay=True` y el gachamon de ahora.
  2. `renombrar_con_placa` valida el nombre antes que nada (`sim.normalizar_nombre`): si no vale, `motivo="nombre"` con la frase del validador en `problema`.
  3. Sin gachamon activo → `sin_gachamon`.
  4. `usar_objeto` con algo que no `se_aplica_al_momento` → `no_se_usa`. `renombrar_con_placa` con algo que no `renombra` → `no_se_usa`.
  5. Un objeto con `dias_de_refugio` para quien `sin_plazo_de_refugio` → `sin_plazo`.
  6. El gachamon se avanza a `ahora` con su ritmo (`db._avanzar_en`). Si ya no vive, se guarda y es `sin_gachamon`.
  7. En la placa, el mismo nombre que ya tiene → `mismo_nombre`.
  8. Se gasta una unidad (`db.gastar_en`); si no había → `no_tienes`.
  9. Se aplica el efecto, se guarda el gachamon y se anota el evento.
  - **Hasta el paso 8 nada se gasta**: ningún rechazo cuesta el objeto.
- Los efectos son los de hoy, sin cambiar ningún número: el reinicio borra la espera de `objeto.reinicia`; la poción tira `obj.tirar_bonus` y dura `obj.MINUTOS_DE_EFECTO`; la sopaipilla de color tira un dado de `hue.caras_de(carácter, color)` para fuerza y velocidad, y la arcoíris uno de `objeto.caras` para las cuatro; el ticket deja la estancia en `ahora + dias`; la comida suma `objeto.alimenta` con tope en 100.
- En `db.py`, las versiones «con la conexión ya abierta» que falten (`poner_efecto_en`, `quitar_cooldown_en`, `alargar_el_refugio_en`); las públicas pasan a llamarlas.
- En `tienda.py` (Discord): desaparecen `usar` y `renombrar`; el menú de la mochila y el formulario de la placa llaman a las dos funciones nuevas con `str(interaccion.id)` como evento, y una función nueva `texto_del_uso(objeto: obj.Objeto, resultado: economia.ResultadoUso) -> str` arma **las mismas frases de hoy, letra por letra**. Los rechazos conservan también sus frases de hoy («Ya no te queda ninguno.», «…no se usa desde aquí…», «Ya no te queda ninguna placa.», «Ya se llama **X**.»).

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_usar_objeto.py`, con el azar inyectado (`random.Random(7)`) y la base temporal:

```python
def test_usar_dos_veces_con_el_mismo_evento_gasta_una_sola_unidad(base):
    criatura = nace()
    dar(U, "pocion_comida", 2)
    hambrear(criatura, 40)
    primera = economia.usar_objeto("evento-uso-01", U, G, obj.CATALOGO["pocion_comida"], T0)
    segunda = economia.usar_objeto("evento-uso-01", U, G, obj.CATALOGO["pocion_comida"], T0)
    assert primera.ok and primera.efecto == "comida" and primera.comida == 60
    assert segunda.ok and segunda.replay and segunda.comida == 60
    assert db.inventario(U, G) == {"pocion_comida": 1}


def test_ningun_rechazo_gasta_el_objeto(base):
    dar(U, "pocion_comida", 1)
    dar(U, "semilla", 1)
    assert economia.usar_objeto("evento-uso-02", U, G, obj.CATALOGO["pocion_comida"], T0).motivo == "sin_gachamon"
    nace()
    assert economia.usar_objeto("evento-uso-03", U, G, obj.CATALOGO["semilla"], T0).motivo == "no_se_usa"
    assert economia.usar_objeto("evento-uso-04", U, G, obj.CATALOGO["silbato"], T0).motivo == "no_tienes"
    assert db.inventario(U, G) == {"pocion_comida": 1, "semilla": 1}


def test_a_un_gachamon_que_ya_murio_no_se_le_gasta_nada(base):
    nace()
    dar(U, "pocion_comida", 1)
    despues = cuando_ya_murio_de_hambre(T0)   # una identidad de Discord, sin casa
    assert economia.usar_objeto("evento-uso-05", U, G, obj.CATALOGO["pocion_comida"], despues).motivo == "sin_gachamon"
    assert db.inventario(U, G) == {"pocion_comida": 1}
```

(Para `cuando_ya_murio_de_hambre`, mira las pruebas de muerte que ya existen: a la intemperie el hambre tiene un suelo y no mata, así que el plazo tiene que caer donde una identidad de Discord sí muere.)

Y una por efecto, afirmando los datos del resultado y lo que quedó en la base: el silbato (`efecto == "reinicia"`, `accion == sim.ENTRENAR`, la espera de entrenar a cero); una poción (`stats == ("fuerza",)`, `1 <= bonus <= caras`, `db.efectos_activos` lo trae); la sopaipilla de color (dos estadísticas, un solo `bonus`, `gusto` no vacío); la arcoíris (las cuatro, `caras` las de su clave); el ticket (para una identidad de Discord: `refugio_hasta == ahora + 7 días`; para una identidad web: `motivo == "sin_plazo"` y el ticket sigue en la mochila); la placa (`efecto == "nombre"`, `nombre_anterior`, el gachamon se llama distinto; con un nombre que no vale: `motivo == "nombre"`, `problema` la frase del validador y la placa intacta; con el mismo nombre: `mismo_nombre`).

Para Discord: las pruebas que llamaban a `tienda.usar` o a `tienda.renombrar` pasan a llamar a la función de `economia` y a `tienda.texto_del_uso`, **conservando cada frase que afirmaban**. Di en el informe cuáles moviste.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_usar_objeto.py -q`
Expected: FAIL — `economia` no tiene `usar_objeto`.

- [ ] **Step 3: Implementar**

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_usar_objeto.py tests/test_tienda.py tests/test_casas.py tests/test_textos.py tests/test_acciones_unicas.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(economia): usar un objeto es una sola operación, con evento, y la usan Discord y la web"
```

---

### Task 5: La Tienda abre — lo que ofrece el lugar y su catálogo

**Files:**
- Modify: `web/static/datos/pueblo.json` (la tienda pasa a `"abre": "ya"`), `globos.py`, `web/pueblo.py`, `web/estado.py`, `web/cuenta.py`, `web/juego.py`, `web/app.py`
- Create: `web/tienda.py`
- Test: `tests/test_pueblo.py`, `tests/test_globos.py`, `tests/test_web_estado.py`, `tests/test_web_tienda.py` (nuevo)

**Interfaces:**
- Consumes: `objetos.a_la_venta` (tarea 1).
- Produces:
  - `pueblo.OFRECE: dict[str, tuple[str, ...]] = {"tienda": ("tienda",)}` y `pueblo.ofrece(clave: str) -> tuple[str, ...]` — lo que se puede hacer en ese lugar; vacío si el lugar no abre `ya`. Una prueba vigila que las claves de `OFRECE` existan en `pueblo.json`.
  - `estado["lugar"]` gana `"ofrece": list[str]`. `estado["gachamon"]` gana `"titulo": str | None` (el texto del título ya concordado, `cosmeticos.texto_del_titulo`).
  - `web/cuenta.py`: `la_misma_activa(jugador, ahora, sin_ninguno)` — la ayuda que hoy es `_la_misma_activa` en `web/juego.py` se muda aquí, pública, sin cambiar lo que hace; `juego.py` la importa.
  - `web/tienda.py`:
    - `donde_sirve(objeto: obj.Objeto) -> str | None` — `"competir"` para una poción de estadística o lo que reinicia `sim.COMPETIR`; `"huerto"` para la semilla; `"refugio"` para lo que da días de refugio; `None` para lo que ya sirve en la web.
    - `se_le_vende(objeto: obj.Objeto, jugador: Jugador) -> bool` — todo lo que está a la venta, salvo, para una cuenta **sin** vincular, lo que `donde_sirve` en `"competir"`, `"huerto"` o `"refugio"`.
    - `catalogo(jugador: Jugador, ahora: datetime) -> dict` — lo que pinta la pantalla (abajo).
    - `en_la_tienda(jugador: Jugador) -> None` — lanza 409 `no_estas_ahi`, «Para eso tienes que estar en la tienda.», si el lugar guardado de la cuenta no ofrece `"tienda"`.
    - `GET /gachamon/api/tienda` → `catalogo(...)`, tras `en_la_tienda`.

La forma del catálogo:

```json
{
  "saldos": {"monedas": 50, "gemas": 50},
  "objetos": [
    {"clave": "pocion_comida", "nombre": "Poción de comida", "descripcion": "…", "precio": 10,
     "icono": "iconos/objetos/pocion_comida.png", "tienes": 0, "se_vende": true, "nota": null}
  ],
  "cosmeticos": [
    {"clave": "corona", "tipo": "sombrero", "nombre": "Corona", "precio": 60,
     "icono": "iconos/cosmeticos/corona.png", "tuyo": false}
  ],
  "casas": {
    "maximo": 3, "puedes_otra": true,
    "tuyas": [
      {"id": 4, "clave": "pequena", "nombre": "Casa pequeña", "icono": "iconos/casas/pequena.png",
       "aforo": 3, "viven": 1, "muebles": 2, "plantados": 0, "dan": 160,
       "mejoras": [{"clave": "mediana", "nombre": "Casa mediana", "cuesta": 340}]}
    ],
    "a_la_venta": [
      {"clave": "pequena", "nombre": "Casa pequeña", "icono": "iconos/casas/pequena.png",
       "precio": 200, "aforo": 3, "huecos": 3, "bancales": 1}
    ]
  },
  "muebles": {
    "tienes_casa": true,
    "lista": [
      {"clave": "felpudo", "nombre": "Felpudo", "precio": 30, "comodidad": 2,
       "icono": "iconos/muebles/felpudo.png", "tuyo": false}
    ]
  }
}
```

  - `objetos`: sólo lo de `a_la_venta()`, en su orden. `tienes` es lo que hay en la mochila. `descripcion` sin las marcas `**` de Discord.
  - `se_vende` y `nota`, por cuenta: a una cuenta vinculada se le vende todo, y lo que `donde_sirve` en `"competir"` lleva la nota «Sirve en las competencias, que por ahora se juegan en Discord.» y en `"huerto"`, «Se siembra en el huerto, que por ahora está en Discord.». A una cuenta sin vincular, lo de `"competir"` y `"huerto"` va con `se_vende: false` y la nota «Más adelante.», y lo de `"refugio"` con `se_vende: false` y «No lo necesitas: tu estancia en el refugio no tiene plazo.».
  - `cosmeticos`: todo `cosmeticos.CATALOGO`; `tuyo` si está en el ropero (puesto o no).
  - `casas.tuyas`: en orden de compra; `viven` cuenta los gachamones vivos de esa casa, `muebles` los puestos en ella, `plantados` sus bancales con algo sembrado, `dan` es `casas.lo_que_dan_por`, y `mejoras` las casas a las que `casas.puede_mejorarse_a`, cada una con lo que cuesta de verdad (su precio menos lo que dan por la actual). `a_la_venta` es el catálogo entero; `puedes_otra` es `Hogar.puede_comprar_otra()`.
  - Todo se lee sin escribir (`db.hogar_leido`).
- **Las frases del gachamon en la Tienda** (`globos.py`), tal cual: comunes `("Cuántas cosas hay en los estantes.", "Huele a madera y a pintura fresca.", "¿Me compras algo?")`; las del pollito `("Pío, cuántas cosas.", "Pío… huele a madera nueva.")`.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_pueblo.py`:

```python
def test_lo_que_ofrece_cada_lugar_son_lugares_del_archivo_y_solo_si_ya_abrieron(monkeypatch):
    assert set(pueblo.OFRECE) <= set(pueblo.LUGARES)
    assert pueblo.ofrece("tienda") == ("tienda",)
    assert pueblo.ofrece("refugio") == () and pueblo.ofrece("estadio") == ()
    monkeypatch.setitem(pueblo.LUGARES, "tienda", replace(pueblo.LUGARES["tienda"], abre=pueblo.PRONTO))
    assert pueblo.ofrece("tienda") == ()
```

y la prueba del archivo que hoy fija `abre` de cada lugar pasa a esperar `"ya"` para la tienda.

En `tests/test_globos.py`: las frases de la tienda son exactamente las de arriba, y ninguna frase de ningún lugar contiene «vacíos» ni «abrirá».

En `tests/test_web_estado.py`: `estado["lugar"]["ofrece"] == []` en el refugio; `estado["gachamon"]["titulo"] is None` sin título y, con `titulo_invicto` puesto a una hembra, `"la Invicta"`.

En `tests/test_web_tienda.py`:

```python
def test_el_catalogo_solo_se_ve_en_la_tienda(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    fuera = cliente.get(TIENDA)
    assert fuera.status_code == 409 and fuera.json()["detail"]["clave"] == "no_estas_ahi"
    ir(cliente, "tienda")
    assert cliente.get(TIENDA).status_code == 200


def test_a_quien_no_tiene_discord_no_se_le_vende_lo_que_solo_sirve_alla(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    ir(cliente, "tienda")
    objetos = {o["clave"]: o for o in cliente.get(TIENDA).json()["objetos"]}
    assert len(objetos) == 17
    for clave in ("fuerza_1d4", "velocidad_1d12", "descanso_rapido", "semilla"):
        assert objetos[clave]["se_vende"] is False and objetos[clave]["nota"] == "Más adelante."
    assert objetos["ticket_refugio"]["se_vende"] is False
    assert objetos["ticket_refugio"]["nota"] == "No lo necesitas: tu estancia en el refugio no tiene plazo."
    for clave in ("pocion_comida", "silbato", "golosinas", "placa"):
        assert objetos[clave]["se_vende"] is True and objetos[clave]["nota"] is None
```

Y: con una cuenta vinculada, los 17 llevan `se_vende: true` y las notas de Discord donde tocan; el catálogo de alguien con una casa pequeña, un mueble puesto y un cosmético trae `tuyas` con sus números, `mejoras` con 340 y 1040, `tuyo: true` donde toca y `tienes_casa: true`; ninguna `descripcion` contiene `**`; mirar el catálogo no crea la fila de `hogar` (la tabla sigue vacía para esa persona); y `tests/test_web_app.py` sigue probando que la web no carga `discord`.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_pueblo.py tests/test_globos.py tests/test_web_estado.py tests/test_web_tienda.py -q`
Expected: FAIL — la tienda abre «pronto», no existen `ofrece` ni la ruta.

- [ ] **Step 3: Implementar**

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_pueblo.py tests/test_globos.py tests/test_web_estado.py tests/test_web_tienda.py tests/test_web_lugar.py tests/test_web_acciones.py tests/test_web_app.py -q`
Expected: PASS. Las pruebas que afirmaban el estado completo del lugar ganan `"ofrece"`; las que esperaban el aviso «Abre pronto» en la tienda pasan a esperarlo en la incubadora, que sigue cerrada.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): la Tienda abre — lo que ofrece cada lugar y el catálogo de lo que se vende"
```

---

### Task 6: Comprar

**Files:**
- Modify: `web/tienda.py`
- Test: `tests/test_web_tienda.py`

**Interfaces:**
- Consumes: los motivos (tarea 1), los eventos (tarea 3), `catalogo`, `se_le_vende`, `en_la_tienda` y `la_misma_activa` (tarea 5).
- Produces:
  - `POST /gachamon/api/tienda/comprar` — cuerpo `{"evento_id": str, "que": "objeto" | "cosmetico" | "mueble", "clave": str}`.
  - `POST /gachamon/api/tienda/casa` — cuerpo `{"evento_id": str, "accion": "comprar" | "mejorar" | "vender", "casa": str, "casa_id": int}`; `casa` (la clave del catálogo) va en comprar y en mejorar, `casa_id` en mejorar y en vender.
  - Las dos contestan 200 con `{"ok": bool, "clave": str | None, "mensaje": str, "tienda": <catalogo>, "estado": <estado.armar>}`. `clave` es el motivo cuando `ok` es falso.
- El orden de cada petición: el evento vale (si no, 422 `evento`, «Ese identificador de evento no vale.», como en `POST /cuidar`; un cuerpo que no es un objeto se trata como vacío) → `que` o `accion` es de los que hay (si no, 422 `peticion`, «La petición no se entiende.») → `en_la_tienda` → `la_misma_activa` → la pieza es de las que la tienda vende (para un objeto, las de `objetos.a_la_venta()`: un poroto no lo es; si no, 422 `peticion`) → para un objeto, `se_le_vende` a esa cuenta (si no, 409 `mas_adelante`, «Eso todavía no se vende aquí.») → la función de `economia` con el `evento_id` → un `RuntimeError` es 409 `evento`, «Ese evento ya se usó para otra cosa.».
- Qué función: objeto → `economia.comprar`; cosmético → `comprar_cosmetico`; mueble → `comprar_mueble` (sin `casa_id`: la primera casa); casa → `comprar_casa` (con `mejorar=casa_id` al mejorar) o `vender_casa`.
- **Las frases** (texto llano; `{monedas}` y `{gemas}` con `objetos.nombre_de_…`; los nombres de casa en minúscula dentro de la frase):

| Qué pasó | Frase |
|---|---|
| objeto comprado | «Compraste {nombre}. Está en tu mochila.» |
| cosmético comprado, con gachamon | «Compraste {nombre}. {gachamon} ya lo lleva.» |
| mueble comprado y colgado | «Compraste {nombre}. Ya está puesto en tu casa.» |
| mueble comprado y guardado | «Compraste {nombre}. No cabía en tu casa: quedó guardado.» |
| casa nueva | «Compraste una {casa}.» |
| casa mejorada | «Tu {desde} ahora es una {casa}.» |
| casa vendida | «Vendiste tu {casa} por {n} {monedas}.» |
| `faltan_monedas` | «Te faltan {n} {monedas}.» |
| `faltan_gemas` | «Te faltan {n} {gemas}. Se ganan con las medallas.» |
| `ya_lo_tienes` | «Ya lo tienes.» |
| `maximo_de_casas` | «Ya tienes {casas.MAXIMO_CASAS} casas, que es el máximo. Vende una o mejora las que tienes.» |
| `no_es_tuya` | «Esa casa no es tuya.» |
| `no_se_empeora` | «Esa casa ya es de ese tamaño o más grande.» |
| `sin_casa` o `intemperie`, comprando un mueble | «Los muebles van en una casa, y todavía no tienes.» |
| `sin_casa`, vendiendo | «No tienes casa que vender.» |

  Un replay cuenta lo mismo que la primera vez. «Te faltan {n}» es el precio (o lo que cuesta la mejora) menos el saldo.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_web_tienda.py`:

```python
def test_comprar_un_objeto_lo_cobra_una_vez_aunque_se_repita(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=50)
    cuerpo = {"evento_id": "evento-compra-01", "que": "objeto", "clave": "pocion_comida"}
    primera = cliente.post(COMPRAR, json=cuerpo, headers=ESCRIBIR).json()
    segunda = cliente.post(COMPRAR, json=cuerpo, headers=ESCRIBIR).json()
    for respuesta in (primera, segunda):
        assert respuesta["ok"] is True and respuesta["clave"] is None
        assert respuesta["mensaje"] == "Compraste Poción de comida. Está en tu mochila."
        assert respuesta["estado"]["saldos"]["monedas"] == 40
        assert respuesta["tienda"]["saldos"]["monedas"] == 40
    assert db.inventario(YO, G) == {"pocion_comida": 1}


def test_si_no_alcanza_es_un_no_con_su_frase_y_no_un_error(cliente, monkeypatch):
    en_la_tienda_con(cliente, monkeypatch, monedas=4)
    respuesta = cliente.post(COMPRAR, json={
        "evento_id": "evento-compra-02", "que": "objeto", "clave": "pocion_comida"}, headers=ESCRIBIR)
    assert respuesta.status_code == 200
    assert respuesta.json()["ok"] is False and respuesta.json()["clave"] == "faltan_monedas"
    assert respuesta.json()["mensaje"] == "Te faltan 6 monedas."


@pytest.mark.parametrize("cuerpo,estado,clave", [
    ({"evento_id": "evento-compra-03", "que": "objeto", "clave": "poroto_rojo"}, 422, "peticion"),
    ({"evento_id": "evento-compra-04", "que": "objeto", "clave": "semilla"}, 409, "mas_adelante"),
    ({"evento_id": "evento-compra-05", "que": "sombrilla", "clave": "corona"}, 422, "peticion"),
    ({"evento_id": "corto", "que": "objeto", "clave": "pocion_comida"}, 422, "evento"),
    ({"que": "objeto", "clave": "pocion_comida"}, 422, "evento"),
    ([], 422, "evento"),
])
def test_lo_que_la_pantalla_nunca_pide_no_cobra_y_no_revienta(cliente, monkeypatch, cuerpo, estado, clave):
    en_la_tienda_con(cliente, monkeypatch, monedas=500)
    respuesta = cliente.post(COMPRAR, json=cuerpo, headers=ESCRIBIR)
    assert respuesta.status_code == estado and respuesta.json()["detail"]["clave"] == clave
    assert economia.saldos(YO, G).asciicoins == 500 and db.inventario(YO, G) == {}
```

Y, una por caso: el saldo que cambió por la otra cara (se pide el catálogo con 50 monedas, se dejan 4 escribiendo en la base temporal, y comprar contesta «Te faltan 6 monedas.» con el catálogo y el estado ya al día); comprar fuera de la tienda es 409 `no_estas_ahi` y no cobra; sin la cabecera `X-Gachamon` no pasa; el cosmético (cobra gemas, la frase con el nombre del gachamon, `estado.gachamon.retrato` cambia de sombrero; el título aparece en `estado.gachamon.titulo`; repetirlo con el mismo evento no cobra otra vez); el mueble sin casa (`sin_casa` con su frase), con casa (colgado) y con la casa llena (guardado); la casa nueva (dos peticiones con el mismo evento dejan **una** casa; `estado.hogar` pasa a `propia`), la mejora (cobra 340 y dice «Tu casa pequeña ahora es una casa mediana.»), la venta (entra el 80 %, la frase dice cuánto) y la cuarta casa (`maximo_de_casas`); un evento usado para comprar una cosa y reutilizado para otra es 409 `evento`; y si el gachamon murió entre medias (identidad vinculada, reloj adelantado), 409 `sin_gachamon` y nada se cobra.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_tienda.py -q`
Expected: FAIL — las rutas no existen (404 o 405).

- [ ] **Step 3: Implementar**

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_tienda.py tests/test_web_app.py tests/test_textos.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): comprar objetos, cosméticos, muebles y casas en la Tienda"
```

---

### Task 7: La mochila

**Files:**
- Create: `web/mochila.py`
- Modify: `web/app.py`
- Test: `tests/test_web_mochila.py` (nuevo)

**Interfaces:**
- Consumes: `economia.usar_objeto`, `economia.renombrar_con_placa`, `ResultadoUso` (tarea 4); `la_misma_activa` (tarea 5).
- Produces:
  - `GET /gachamon/api/mochila` → `{"objetos": [{"clave", "nombre", "descripcion", "icono", "cantidad", "uso", "nota"}]}` — lo que la persona lleva y **sigue en el catálogo**, en el orden del catálogo. `uso` es `"al_momento"`, `"con_nombre"` (la placa) o `null`; cuando es `null`, `nota` dice por qué: «Se usa en el huerto.» para la semilla y los porotos, «No lo necesitas: tu estancia en el refugio no tiene plazo.» para el ticket de quien no tiene plazo, y «Eso no se usa desde la mochila.» para lo demás. Desde cualquier lugar.
  - `POST /gachamon/api/mochila/usar` — cuerpo `{"evento_id": str, "clave": str, "nombre": str}` (`nombre` sólo con la placa). Contesta 200 con `{"ok", "clave", "mensaje", "mochila": <lo de GET>, "estado": <estado.armar>}`.
- El orden: cuerpo y evento válidos (422) → `la_misma_activa` → el objeto existe en el catálogo (422 `peticion`) → `renombrar_con_placa` si `objeto.renombra`, `usar_objeto` si no → `RuntimeError` es 409 `evento`. Un `motivo == "sin_gachamon"` del resultado se contesta como el 409 `sin_gachamon` de siempre.
- **Las frases**, según `ResultadoUso` (`{nombre}` es el del gachamon; `{minutos}` es `objetos.MINUTOS_DE_EFECTO`):

| `efecto` o `motivo` | Frase |
|---|---|
| `reinicia` | «{nombre} ya puede {accion} otra vez.» |
| `estadistica` | «{nombre} gana +{bonus} de {stat} durante {minutos} minutos.» |
| `sopaipilla` de color | «{nombre} se come una {objeto en minúscula}: {gusto}. +{bonus} de fuerza y de velocidad durante {minutos} minutos.» |
| `sopaipilla` arcoíris | «{nombre} se come una {objeto en minúscula}. +{bonus} en las cuatro estadísticas durante {minutos} minutos.» |
| `refugio` | «Tienes otra estancia en el refugio, hasta el {día}/{mes}.» |
| `comida` | «{nombre} come. Comida +{comida} (ahora {total}).» |
| `nombre` (efecto) | «{nombre_anterior} pasa a llamarse {nombre}.» |
| `no_tienes` | «Ya no te queda ninguno.» |
| `no_se_usa` | «Eso no se usa desde la mochila.» |
| `sin_plazo` | «No lo necesitas: tu estancia en el refugio no tiene plazo.» |
| `mismo_nombre` | «Ya se llama así.» |
| `nombre` (motivo) | la frase de `ResultadoUso.problema` |

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_web_mochila.py`:

```python
def test_la_mochila_ensena_lo_que_llevas_y_como_se_usa(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "pocion_comida", 2); dar(YO, "placa", 1); dar(YO, "semilla", 3)
    objetos = cliente.get(MOCHILA).json()["objetos"]
    assert [(o["clave"], o["cantidad"], o["uso"]) for o in objetos] == [
        ("pocion_comida", 2, "al_momento"), ("placa", 1, "con_nombre"), ("semilla", 3, None),
    ]
    assert objetos[2]["nota"] == "Se usa en el huerto." and objetos[0]["nota"] is None
    assert objetos[0]["icono"] == "iconos/objetos/pocion_comida.png"


def test_usar_dos_veces_con_el_mismo_evento_gasta_una(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "golosinas", 2)
    reloj.pasar(hours=20)          # lo que haga falta para que la comida baje de 75
    cuerpo = {"evento_id": "evento-mochila-01", "clave": "golosinas"}
    primera = cliente.post(USAR, json=cuerpo, headers=ESCRIBIR).json()
    segunda = cliente.post(USAR, json=cuerpo, headers=ESCRIBIR).json()
    assert primera["ok"] and segunda["ok"] and primera["mensaje"] == segunda["mensaje"]
    assert primera["mensaje"].startswith("Pelusa come. Comida +25 (ahora ")
    assert [o["cantidad"] for o in segunda["mochila"]["objetos"]] == [1]
    assert segunda["estado"]["gachamon"]["barras"]["comida"] == primera["estado"]["gachamon"]["barras"]["comida"]
```

Y: la placa con un nombre que vale (`"Pelusa pasa a llamarse Nube."`, y `estado.gachamon.nombre == "Nube"`), con uno que no vale (200, `ok: false`, `clave == "nombre"`, la frase del validador, la placa sigue), sin `nombre` (igual que vacío) y con el mismo (`mismo_nombre`); usar lo que no llevas (`no_tienes`, 200); usar la semilla (`no_se_usa`, sigue en la mochila); una clave que no existe (422 `peticion`); un objeto que alguien guarda y ya no está en el catálogo no aparece ni rompe la lista (mételo a mano en la base temporal); sin gachamon, `GET` devuelve la lista y `POST` es 409 `sin_gachamon`; si el gachamon murió entre medias (cuenta vinculada, reloj adelantado), 409 `sin_gachamon` y el objeto sigue en la mochila; sin la cabecera no pasa; y nadie usa la mochila de otra cuenta (dos cuentas, cada una ve la suya).

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_mochila.py -q`
Expected: FAIL — las rutas no existen.

- [ ] **Step 3: Implementar**

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_mochila.py tests/test_web_tienda.py tests/test_web_app.py tests/test_textos.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): la mochila — ver lo que llevas y usarlo"
```

---

### Task 8: Los íconos

**Files:**
- Modify: `web/arte.py`, `herramientas/rellenos.py`, `docs/arte/contrato.md`
- Create (generados): `web/static/arte/iconos/**` y `web/static/datos/arte.json` regenerado
- Test: `tests/test_arte.py`, `tests/js/arte.test.mjs`

**Interfaces:**
- Produces: la familia `iconos`, de **48 × 48**, una pieza por cada entrada de cuatro catálogos, en su orden:
  - `iconos/objetos/<clave>.png` — todo `objetos.CATALOGO` (33: también lo que no se vende, porque se ve en la mochila).
  - `iconos/cosmeticos/<clave>.png` — `cosmeticos.CATALOGO` (12).
  - `iconos/muebles/<clave>.png` — `casas.MUEBLES` (14).
  - `iconos/casas/<clave>.png` — `casas.CATALOGO` (3).
  - El contrato pasa de 137 a **199** piezas. Añadir un objeto al catálogo añade su ícono solo.
- El relleno: un cuadro de color liso por familia, con las primeras letras del nombre de la pieza; se tiene que notar que es relleno y distinguirse un ícono de otro. Determinista, y **los 137 archivos que ya existen no cambian ni un byte** (se corre `./venv/bin/python -m herramientas.rellenos`, sin `--todo`).
- `docs/arte/contrato.md`: la familia nueva en su tabla, con el tamaño, de qué catálogo sale cada grupo y dónde se ve (la tienda y la mochila). Fondo transparente.

- [ ] **Step 1: Escribir las pruebas que fallan**

Las tres aserciones que hoy cuentan 137 pasan a 199, y en `tests/test_arte.py`:

```python
def test_cada_cosa_que_se_compra_o_se_lleva_tiene_su_icono():
    rutas = {p.ruta: p for p in arte.piezas()}
    esperadas = (
        [f"iconos/objetos/{c}.png" for c in objetos.CATALOGO]
        + [f"iconos/cosmeticos/{c}.png" for c in cosmeticos.CATALOGO]
        + [f"iconos/muebles/{c}.png" for c in casas.MUEBLES]
        + [f"iconos/casas/{c}.png" for c in casas.CATALOGO]
    )
    assert len(esperadas) == 62
    for ruta in esperadas:
        assert (rutas[ruta].ancho, rutas[ruta].alto, rutas[ruta].familia) == (48, 48, "iconos")
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_arte.py tests/test_web_js.py -q`
Expected: FAIL — el contrato tiene 137 piezas.

- [ ] **Step 3: Implementar y generar**

- [ ] **Step 4: Correr las pruebas y mirar una hoja**

Run: `./venv/bin/python -m pytest tests/test_arte.py tests/test_web_js.py -q` → PASS. Arma una hoja con los 62 íconos (fuera del repo) y mírala: se distinguen, se nota que son relleno. `git status` enseña 62 PNG nuevos y ninguno cambiado.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(arte): los íconos de objetos, cosméticos, muebles y casas entran al contrato"
```

---

### Task 9: La pantalla de la Tienda

**Files:**
- Create: `web/static/js/tienda.js`, `web/static/js/compras.js`
- Modify: `web/static/js/api.js`, `web/static/js/arte.js`, `web/static/js/pantallas.js`, `web/static/js/principal.js`, `web/static/js/lugar.js`, `web/static/estilo.css`
- Test: `tests/js/compras.test.mjs` (nuevo), `tests/js/api.test.mjs`, `tests/js/pantallas.test.mjs`, `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: `GET tienda`, `POST tienda/comprar`, `POST tienda/casa` (tareas 5 y 6); `estado.lugar.ofrece` y `estado.gachamon.titulo` (tarea 5); los íconos (tarea 8).
- Produces:
  - `api.conReintentos(hacer, sigue = () => true)` — el bucle de reintentos que hoy vive dentro de `lugar.js`, mudado a `api.js` y exportado, **sin cambiar lo que hace**: repite sólo lo que no llegó a ser una respuesta del juego, con las mismas pausas, y deja de insistir si `sigue()` da falso. `lugar.js` pasa a usarlo.
  - `arte.lienzoDePieza(ruta, ancho, alto) -> HTMLCanvasElement` — un lienzo `aria-hidden`, nítido, que carga esa pieza y la pinta (o su recuadro si falta).
  - `pantallas.siguiente(sesion, cuenta, estado, vista)` — además de `'pueblo'`: con `vista === 'tienda'` devuelve `'tienda'` sólo si `estado.lugar.ofrece` incluye `'tienda'`; con `vista === 'mochila'`, `'mochila'`. Cualquier otra cosa, `'lugar'`, como hoy.
  - `compras.js`, puro:
    - `preguntaDeCompra(precio, moneda) -> string` — `moneda` es `'monedas'` o `'gemas'`: «¿Comprar por 10 monedas?», «¿Comprar por 1 gema?».
    - `preguntaDeVenta(casa) -> string` — con una de `casas.tuyas`: «¿Vender tu casa pequeña por 160 monedas? Sus 2 muebles quedan guardados, sus 3 gachamones se van al refugio y lo plantado se pierde.» Sólo nombra lo que hay: sin muebles, sin inquilinos o sin nada plantado, esa parte no sale; con uno, en singular («Su mueble queda guardado», «su gachamon se va al refugio»).
    - `preguntaDeMejora(casa, mejora) -> string` — «¿Mejorar tu casa pequeña a casa mediana por 340 monedas?»
  - `tienda(contenedor, estado, seguir)` — la pantalla, registrada en `principal.js` como `tienda`.
- **La pantalla.** Cabecera de siempre con «🛒 Tienda» en un `h1` y los dos saldos. Cuatro pestañas —**Objetos**, **Cosméticos**, **Casas**, **Muebles**— que son botones con `aria-pressed`; se ve una sección a la vez y se recuerda la última mientras dure la página. Abajo, «Volver», que hace `seguir()` a secas.
  - Cada fila: el ícono (`lienzoDePieza`, 48 px), el nombre, la descripción o la nota, y a la derecha el botón con el precio («🪙 10», «💎 60») y su texto para lector («Comprar por 10 monedas»).
  - Lo que no se vende a esa cuenta (`se_vende: false`) sale sin botón, con su nota. Lo que ya es tuyo (`tuyo: true`) dice «Ya lo tienes» en vez del botón. Un objeto dice cuántos llevas («Tienes 2») cuando llevas alguno.
  - **Comprar son dos toques**: el primero cambia el botón por la pregunta (`preguntaDeCompra`) con «Comprar» y «No»; el segundo manda la petición. Abrir otra pregunta cierra la anterior.
  - En **Casas**: primero las tuyas, cada una con cuántos viven, sus mejoras posibles (cada una su botón y su pregunta) y «Vender» (con `preguntaDeVenta`); después las que se venden, con su aforo, sus huecos para muebles y sus bancales. Si `puedes_otra` es falso, en vez de los botones de comprar: «Ya tienes 3 casas, que es el máximo.»
  - En **Muebles**, sin casa: «Los muebles van en una casa, y todavía no tienes.» sobre la lista, y ninguna fila lleva botón.
  - Mientras una compra está en camino, esa fila espera y ninguna otra compra sale. La petición va con `nuevoEvento()` y `conReintentos`. La respuesta trae `tienda` y `estado`: la pantalla se repinta con esos datos (saldos incluidos) y enseña `mensaje` en una zona `role="status"` (en rojo si `ok` es falso).
  - Si la respuesta es 401, o un 409 (`sin_gachamon`, `no_estas_ahi`…), la pantalla hace `seguir()` a secas: se decide de nuevo. Si no llegó respuesta tras los reintentos: «No se pudo comprar. Revisa tu conexión.», y la pantalla vuelve a pedir el catálogo para enseñar la verdad.
  - Si el catálogo no carga: la frase y «Volver a intentarlo», más «Volver».
  - Todo lo que temporiza o escucha se detiene al salir, y una respuesta tardía no pinta ni llama a `seguir`.
- **En `lugar.js`:** donde `estado.lugar.ofrece` incluye `'tienda'`, un botón «🛒 Comprar» sobre «Pueblo», que hace `seguir(actual, { vista: 'tienda' })`. Y la ficha enseña `estado.gachamon.titulo`, cuando lo hay, junto al nombre. Nada más cambia en esa pantalla.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/js/pantallas.test.mjs`:

```javascript
test('la tienda sólo se abre donde el lugar la ofrece', () => {
  const en = (ofrece) => ({ ...jugando, lugar: { clave: 'x', nombre: 'X', ofrece } });
  assert.equal(siguiente(sesion, cuenta, en(['tienda']), 'tienda'), 'tienda');
  assert.equal(siguiente(sesion, cuenta, en([]), 'tienda'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, { ...jugando, lugar: { clave: 'x', nombre: 'X' } }, 'tienda'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, en([]), 'mochila'), 'mochila');
  assert.equal(siguiente(sesion, cuenta, en(['tienda']), 'otra cosa'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, { ...jugando, difunto: { nombre: 'Pelusa' } }, 'tienda'), 'difunto');
});
```

(`sesion`, `cuenta` y `jugando` son los que ese archivo ya usa para un jugador con gachamon.)

En `tests/js/compras.test.mjs`:

```javascript
test('la pregunta dice el precio con su moneda, en singular cuando es una', () => {
  assert.equal(preguntaDeCompra(10, 'monedas'), '¿Comprar por 10 monedas?');
  assert.equal(preguntaDeCompra(1, 'monedas'), '¿Comprar por 1 moneda?');
  assert.equal(preguntaDeCompra(60, 'gemas'), '¿Comprar por 60 gemas?');
  assert.equal(preguntaDeCompra(1, 'gemas'), '¿Comprar por 1 gema?');
});

test('vender dice lo que pasa con lo que hay dentro, y sólo con lo que hay', () => {
  const casa = { nombre: 'Casa pequeña', dan: 160, muebles: 2, viven: 3, plantados: 1 };
  assert.equal(preguntaDeVenta(casa),
    '¿Vender tu casa pequeña por 160 monedas? Sus 2 muebles quedan guardados, sus 3 gachamones se van al refugio y lo plantado se pierde.');
  assert.equal(preguntaDeVenta({ ...casa, muebles: 1, viven: 1, plantados: 0 }),
    '¿Vender tu casa pequeña por 160 monedas? Su mueble queda guardado y su gachamon se va al refugio.');
  assert.equal(preguntaDeVenta({ ...casa, muebles: 0, viven: 0, plantados: 0 }),
    '¿Vender tu casa pequeña por 160 monedas?');
});

test('mejorar dice de qué a qué y por cuánto', () => {
  assert.equal(preguntaDeMejora({ nombre: 'Casa pequeña' }, { nombre: 'Casa mediana', cuesta: 340 }),
    '¿Mejorar tu casa pequeña a casa mediana por 340 monedas?');
});
```

En `tests/js/api.test.mjs`, con relojes de mentira: `conReintentos` devuelve a la primera si sale bien; repite hasta dos veces lo que no llegó (`{estado: 0, clave: null}`) y a la tercera lanza; no repite un error del juego (`clave` no nula) ni un 401; y deja de insistir si `sigue()` da falso.

En `tests/test_web_cliente.py` (de texto, como las del mapa): `tienda.js` existe, `principal.js` la registra, pide con `conReintentos` y `nuevoEvento`, no contiene `innerHTML` ni `http`; `lugar.js` ya no define su propio `conReintentos` y nombra `vista: 'tienda'`; y ninguna pantalla nueva escribe un precio ni una clave del catálogo en el código.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py -q`
Expected: FAIL — no existen `compras.js`, `tienda.js` ni `conReintentos` en `api.js`.

- [ ] **Step 3: Implementar**

- [ ] **Step 4: Correr las pruebas y mirar la página**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py tests/test_web_app.py -q` → PASS.

Con el servicio levantado sobre bases temporales, a 390 y a 1280 px: la Tienda con el botón «Comprar»; cada pestaña; una compra con sus dos toques y su frase; un «te faltan»; lo de «Más adelante.» de una cuenta sin vincular y las notas de una vinculada; un sombrero recién comprado puesto en la escena y un título junto al nombre; comprar, mejorar y vender una casa con sus preguntas; los muebles sin casa; un ícono que falta; la red caída a mitad de una compra; y que cuidar en el lugar sigue funcionando igual tras mudar `conReintentos`.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): la pantalla de la Tienda, con sus cuatro secciones y la compra en dos toques"
```

---

### Task 10: La pantalla de la mochila

**Files:**
- Create: `web/static/js/mochila.js`
- Modify: `web/static/js/principal.js`, `web/static/js/lugar.js`, `web/static/estilo.css`
- Test: `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: `GET mochila`, `POST mochila/usar` (tarea 7); `conReintentos`, `lienzoDePieza`, la vista `'mochila'` (tarea 9).
- Produces: `mochila(contenedor, estado, seguir)`, registrada en `principal.js` como `mochila`.
- **La pantalla.** Cabecera con «🎒 Mochila» en un `h1` y los saldos; la lista; «Volver» (`seguir()` a secas). Cada fila: el ícono, el nombre con la cantidad («Poción de comida × 2»), la descripción o la nota, y «Usar» si `uso` no es `null`.
  - **Usar son dos toques**: «Usar» → «¿Usar?» con «Usar» y «No». En la placa (`uso: 'con_nombre'`), el primer toque abre ahí mismo un campo «Nuevo nombre» con su etiqueta y «Cambiar nombre» / «No»; el nombre se manda tal cual y lo valida el servidor.
  - La respuesta trae `mochila` y `estado`: la lista se repinta y `mensaje` se enseña en una zona `role="status"` (en rojo si `ok` es falso). Mientras una petición está en camino no sale otra.
  - Vacía: «Tu mochila está vacía. Lo que compres en la tienda aparece aquí.»
  - Los mismos tratos que la tienda para el 401 y los 409 (`seguir()` a secas), para la red caída («No se pudo usar. Revisa tu conexión.», y se vuelve a pedir la lista) y para la lista que no carga.
- **En `lugar.js`:** un botón «🎒 Mochila» junto a «Pueblo», en todos los lugares: `seguir(actual, { vista: 'mochila' })`. En el teléfono los dos caben en una fila.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_web_cliente.py`, de texto: `mochila.js` existe y `principal.js` la registra; pide con `conReintentos` y `nuevoEvento`; no contiene `innerHTML` ni `http`; `lugar.js` nombra `vista: 'mochila'`; y ningún archivo del cliente escribe una clave del catálogo de objetos.

- [ ] **Step 2: Correrlas y ver que fallan** — Run: `./venv/bin/python -m pytest tests/test_web_cliente.py -q`

- [ ] **Step 3: Implementar**

- [ ] **Step 4: Correr las pruebas y mirar la página**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py tests/test_web_app.py -q` → PASS.

A 390 y a 1280 px: el lugar con «Pueblo» y «Mochila»; la mochila vacía; con varias cosas; usar unas golosinas con sus dos toques (la frase, la cantidad baja, y al volver la barra de comida subió); la placa con un nombre bueno y con uno malo; la semilla con su nota y sin botón; y el recorrido entero: comprar en la tienda, volver, abrir la mochila, usar.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): la pantalla de la mochila, desde cualquier lugar"
```

---

### Task 11: Documentos y puesta en marcha

**Files:**
- Modify: `README.md`, `AGENTS.md`, `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`

- [ ] **Step 1: `AGENTS.md`**

En los invariantes, además de la línea de la tarea 2:

```markdown
- Usar un objeto es una regla del juego (`economia.usar_objeto`), no del menú: se gasta, se aplica y se anota en una sola transacción, y ningún rechazo cuesta el objeto.
- Toda compra, venta o uso que llega de la web lleva un evento: repetirlo devuelve lo que pasó la primera vez y no cobra, entrega ni gasta otra vez.
- En la web se compra estando en la Tienda; lo que hoy sólo sirve en Discord se le vende sólo a quien tiene Discord vinculado.
```

- [ ] **Step 2: `README.md`**

En «La web»: una frase sobre la tienda y la mochila; y en «Arte», que los íconos salen de los catálogos (un objeto nuevo añade el suyo).

- [ ] **Step 3: El documento de pendientes**

Una sección «Salió al ejecutar el plan 4» con lo que se haya dejado. En «Para el plan 4», lo que este plan resuelve se quita (los avisos de la tienda, sus frases, la mochila en la navegación, los íconos) y la sección pasa a llamarse por los planes que quedan, con lo de cada uno: plan 5 (el ropero: quitar y cambiar; la ficha completa con los efectos activos; la incubadora y sus frases; hablar sale de la navegación del plan 7), plan 6 (elegir casa al comprar un mueble, colocar y retirar; el huerto, y con él la semilla deja de ser «más adelante»; los muebles dibujados dentro de la casa), plan 7 (hablar). Y lo que el reconocimiento encontró en Discord y este plan no toca: el botón «Amueblar» de `/casa` falla (`tienda.py` usa `hogar.casa`, que no existe); el texto de mejorar una casa anuncia el precio entero; `db.activar` sobre el propio activo le borra el decaimiento pendiente; `economia.plantar` deja sembrar cualquier objeto; y `acciones_unicas` no se purga.

- [ ] **Step 4: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "docs(web): la tienda y la mochila, en el README, la política y los pendientes"
```

- [ ] **Step 5: (Controlador) Mirar el juego entero**

Con el servicio en local sobre bases temporales: el recorrido de las tareas 9 y 10 otra vez, sobre la rama terminada, a 390 y a 1280 px, con una cuenta sin vincular y una vinculada. Las capturas se le enseñan a Felipe antes de pedirle nada.

- [ ] **Step 6: (Controlador, con Felipe) Revisión final, fusión y subida**

Revisión de toda la rama; fusionar y subir son decisión de Felipe. La CI tiene que pasar en 3.12 y 3.14.

- [ ] **Step 7: (Controlador, con Felipe) Desplegar**

`./actualizar-pi.sh`. La tabla `acciones_unicas` se crea sola al arrancar. Este despliegue **sí** cambia Discord (usar un objeto): tras reiniciar, comprobar en el registro que el bot arrancó sin errores. Después, desde la Pi y desde fuera: los servicios activos, `/gachamon/api/salud`, y que un ícono de `arte/iconos/` contesta 200.

- [ ] **Step 8: (Felipe) Probarlo**

En la web: comprar algo barato, usarlo desde la mochila, comprar un sombrero. En Discord: usar un objeto de la mochila y ver que dice lo de siempre.
