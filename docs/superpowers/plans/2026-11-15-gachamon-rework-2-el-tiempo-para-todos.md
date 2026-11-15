# Rework 2 · El tiempo para todos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que a todos los gachamones vivos les pase el tiempo, que el activo sea sólo el que sale contigo, que cada cuidado le caiga al que elijas o a todos de una vez, y que un recluta llegue ya con nombre.

**Architecture:** De dentro hacia fuera, como el plan 1. Primero la regla (`simulacion.avanzar` deja de mirar quién es la activa) con su cambio de una sola vez en la base; después lo que colgaba de «la incubadora congela»: cambiar de activo, los cuidados y el nombre de los reclutas, cada uno en su regla de `economia.py` o `nacer.py`, con Discord y la web como adaptadores finos. Al final se quita el estado «sin nombre», que ya no puede darse, y se corrigen los documentos.

**Tech Stack:** Python 3.12, discord.py, FastAPI, SQLite síncrono, pytest y `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-14-gachamon-rework-1-departamento-design.md` (sección 3; de la 6, la línea de los que estaban en la incubadora; de la 7, «sigue igual: cuidar al activo» y «elegir al activo sigue en Discord»).

**Dónde encaja.** Es el plan 2 de 6 del proyecto 1 del rework: (1) nadie muere — hecho; (2) el tiempo para todos; (3) la vivienda por casillas en el servidor, el día del cambio y Discord; (4) el departamento en pantalla; (5) los muebles que se usan solos; (6) el pueblo sin Refugio ni Incubadora y los documentos. Los seis se juntan en la rama `rework/1-departamento` y **se publican juntos al final**.

**Lo que no entra, y dónde va.** Las camas, partir sin gachamon ni huevo, la primera aventura, el monedero que empieza en 0 y `/huevo` mandando a la página: plan 3. Los botones de «a todos», «Salir con él», cambiarle el nombre desde la ficha de la web, y exigir estar en el departamento para cuidar a los que no salen contigo: plan 4. La mochila y el ropero para el gachamon elegido: planes 4 y 6. El lugar «Incubadora» de la web y el código del cliente que todavía sabe qué hacer con un recluta sin nombre (`pantallas.js`, `entrada.js`, `incubadora.js`): plan 6, que rehace la entrada. En este plan **las casas, el refugio y el huevo siguen como están**, y el cliente web no se toca.

## Global Constraints

- Nada se sube, se fusiona ni se despliega: todo queda en la rama local `rework/1-departamento`.
- Los módulos de juego no importan `discord`; `web/` no importa `discord` ni nada que lo importe; `db.py` no importa `economia.py`.
- Cada cambio de estado va en su transacción `BEGIN IMMEDIATE`, dentro de `db.py`, `economia.py` o `nacer.py`.
- Sin dependencias nuevas. Dominio determinista: el tiempo y el azar se inyectan en las pruebas.
- Nunca se abre `tamagotchi.db` ni `.env`; las pruebas usan bases temporales e ids sintéticos. El repo es público: sin IPs, ids de personas ni secretos.
- Antes de editar un símbolo, GitNexus `impact`; el índice se refresca sólo con `node .gitnexus/run.cjs analyze --index-only`.
- Cada commit: `./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "…"`, y termina con la línea de coautoría de la sesión que lo escribe.
- A quien juega se le dice «monedas» y «gemas»; el arte de texto de Discord no se reformatea; ningún mensaje del bot pasa de 2000 caracteres.
- Si el plantel no está vacío hay exactamente una activa; el plantel no pasa de `db.MAXIMO_PLANTEL` (25). **Todo lo de este plan tiene que funcionar con el plantel vacío**: el rediseño parte sin gachamon.
- El tope diario de monedas sigue siendo uno solo por persona + servidor + día UTC; ninguna regla de este plan lo sube ni lo reparte por gachamon.
- **Regla de las pruebas de este plan.** Una prueba que existía para comprobar que a una reserva **no** le pasa el tiempo, que cambiar de activo duerme o despierta a alguien, o que un recluta sin nombre no puede salir, se **reescribe** para afirmar la regla nueva o se **borra** si ya no afirma nada. Una prueba que usaba una reserva sólo como preparación de otra cosa se conserva. Cada tarea dice en su informe cuántas borró y cuántas reescribió, y por qué.
- **Frases nuevas** (se le enseñan a Felipe al confirmar el plan; van tal cual):
  - `/plantel`, cómo está cada uno: `activo ahora` (igual) y `en casa` (antes «en la incubadora»); el emoji de los que no son el activo pasa de 🥚 a 🏠.
  - `/plantel`, pie con más de uno: `-# A todos les pasa el tiempo, salgan contigo o no. Elige abajo con cuál sales.`
  - `/plantel`, desplegable: `¿Con cuál sales?`
  - Al cambiar de activo en Discord: ``🧬 Ahora sales con **{nombre}**. Mír{alo/ala} con `/mascota`.``
  - Botón de una ficha que no es la del activo: ``Ese gachamon se quedó en casa. Elígelo con `/plantel` para cuidarlo desde aquí.``
  - Pie de la ficha: `-# 🏠 Tienes {n} más en casa · «Cambiar» para salir con otro` (con 1 y con varios, la misma).
  - Testigo de una competencia: `-# 👀 Desde casa, **{testigo}** celebra a **{nombre}**.` y `…espera a **{nombre}**.`
  - Manual, «El plantel»: `Puedes tener hasta **{db.MAXIMO_PLANTEL}** gachamones. **Uno es el activo**: el que sale contigo y recibe los botones y los comandos. A los demás también les pasa el tiempo: para cuidar a otro, sal con él.` (el renglón `-# Se cambia con…` no cambia).
  - Manual, aventura: `Al unirse **se pone un nombre él solo**; puedes cambiárselo una vez.`
  - Al unirse un salvaje: `🧬 **¡Se une a tu equipo!** Dice que se llama **{nombre}**. Si prefieres otro nombre, pónselo ahora.` El botón pasa a `Ponerle otro nombre`.
  - Ese botón cuando ya no hay a quién: `Ninguno de tus gachamones espera un nombre nuevo.`
  - «Entrenar fuerza juntos»: `No tienes otro gachamon con quien entrenar.` y `Elige con quién entrena tu gachamon activo.`
  - Web, al cambiar de activo: `Ahora sales con {nombre}.`
  - Web, «a todos»: `Les diste de comer a {n} de {total}.` · `Jugaste con {n} de {total}.` · `Entrenaste con {n} de {total}.` · `Bañaste a {n} de {total}.` · si no le tocó a ninguno, `Ahora mismo no le toca a ninguno.` · sin gachamones, `No tienes gachamones que cuidar.`
  - Los nombres que se pone un recluta (40): Nube, Miga, Trufa, Copo, Brote, Chispa, Pompón, Motita, Lenteja, Garbanzo, Pistacho, Canela, Mochi, Churro, Fideo, Ñoqui, Maní, Kiwi, Coco, Menta, Mote, Piñón, Maqui, Lúcuma, Murta, Calafate, Boldo, Nalca, Luche, Merkén, Charqui, Totora, Burbuja, Cochayuyo, Rulo, Tambor, Pepita, Galleta, Bolita, Pixel.
- **Lo que este plan decide en nombre de Felipe** (propuestas; se le enseñan con el plan):
  - «A todos» paga una moneda por cada gachamon al que le tocó, igual que cuidarlos de a uno, dentro del tope diario de siempre.
  - «Le serviría»: no se alimenta al que se empacharía (comida en 90 o más) ni se hace un cuidado que lo dejaría igual (bañar al que está limpio). Jugar y entrenar le sirven siempre, porque entrenan.
  - En Discord se sigue cuidando sólo al activo: para cuidar a otro se sale con él, que no cuesta nada. Cuidar a cualquiera sin cambiar y «a todos» son de la página.
  - El recluta se pone el nombre **al unirse**, y el botón de siempre deja cambiárselo una vez. Así ya no existe un gachamon sin nombre.

## Review Focus

1. **El día del cambio, con el bot y la web arrancando a la vez**: a los que estaban en la incubadora el reloj les parte de ese momento, una sola vez; un arranque posterior no les regala tiempo. → Task 1.
2. **Ir y volver de activo muchas veces**: no ahorra ni duplica el paso del tiempo de ninguno de los dos. → Task 2.
3. **Un `gachamon_id` ajeno, de un muerto de antes o que no existe**, al cuidar o acariciar: no cambia nada, no cobra y contesta lo mismo en los tres casos. → Task 3.
4. **«A todos» con más gachamones que cuidados pagados quedan hoy**: cuida a todos los que pueden, paga sólo lo que cabe en el tope, y repetir el evento no cuida ni paga otra vez. → Task 4.
5. **Quien tiene el activo muerto de antes y un único recluta sin nombre** (hoy no puede jugar): al arrancar el recluta se pone nombre, pasa a ser el activo y la persona recupera su partida. → Task 5.

**Sobre las pruebas de este plan.** Los nombres de ayuda (`criatura(...)`, `nacer(...)`, `nace(...)`, `U`, `G`, `T0`, `STATS`, `cliente`, `con_gachamon`, `poner_reloj`…) son los de las pruebas vecinas de cada archivo. Lo que manda son los nombres de las pruebas nuevas y sus aserciones, con sus valores.

---

### Task 1: A todos les pasa el tiempo

**Files:**
- Modify: `simulacion.py` (`avanzar`), `db.py` (`SCHEMA_TABLAS`, `inicializar`, `_migrar`; nuevas `_una_sola_vez`, `plantel_en`, `plantel_al_dia`; docstrings de `crear` y `vivas_del_servidor`), `economia.py` (`poner_al_dia`, `ejecutar_entrenamiento_conjunto`), `vistas.py` (`NombreModal.on_submit`), `nacer.py` (docstring de `bautizar_a`), `casas.py` (el comentario «Sólo a la **activa**…»), `web/incubadora.py` (`el_plantel`), `web/estado.py` (`_refugio`)
- Test: `tests/test_simulacion.py`, `tests/test_db.py`, `tests/test_economia_entrenamiento_conjunto.py`, `tests/test_web_incubadora.py`, `tests/test_web_refugio.py`, y **toda prueba de la suite que falle porque esperaba que una reserva no decayera** (regla de las pruebas)

**Interfaces:**
- Produces:
  - `sim.avanzar(criatura, ahora, ritmo=RITMO_BAJO_TECHO) -> Criatura`: avanza a cualquier criatura viva, sea o no la activa. Sólo una muerta de antes queda igual.
  - Tabla `cambios_hechos (clave TEXT PRIMARY KEY, hecho_en TEXT NOT NULL)` y `db._una_sola_vez(con, clave: str, ahora: datetime) -> bool`: apunta el cambio y devuelve verdadero sólo la primera vez. La clave de esta tarea es `"el_tiempo_para_todos"`.
  - `db.inicializar(ahora: datetime | None = None) -> None` (sin `ahora`, `ahora_utc()`); `economia.poner_al_dia(ahora)` se lo pasa.
  - `db.plantel_en(con, usuario_id, guild_id) -> list[sim.Criatura]` (lo de `plantel`, para quien ya tiene la conexión) y `db.plantel_al_dia(usuario_id, guild_id, ahora) -> list[sim.Criatura]`: los vivos, la activa primero, cada uno avanzado con el ritmo de su hogar. Sólo lee.
  - `db._activar_en` **sigue** poniendo `actualizada_en` en esta tarea: lo quita la Task 2.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_simulacion.py`:

```python
def test_el_tiempo_le_pasa_igual_a_la_que_no_es_la_activa():
    despues = T0 + timedelta(hours=10)
    activa = sim.avanzar(criatura(activa=True), despues)
    otra = sim.avanzar(criatura(activa=False), despues)
    assert (otra.hambre, otra.animo, otra.limpieza) == (activa.hambre, activa.animo, activa.limpieza)
    assert otra.hambre < 100.0 and otra.actualizada_en == despues
```

En `tests/test_db.py` (la marca se borra para fabricar «una base de antes»):

```python
def borrar_la_marca(clave):
    with db.conectar() as con:
        con.execute("DELETE FROM cambios_hechos WHERE clave = ?", (clave,))

def test_el_dia_del_cambio_el_reloj_de_las_que_dormian_parte_de_ahi():
    activa = nacer(nombre="Ana")
    dormida = db.crear(U, G, "pulpo", "Bea", STATS, T0, activa=False)
    borrar_la_marca("el_tiempo_para_todos")
    cambio = T0 + timedelta(days=40)
    db.inicializar(cambio)
    assert db.por_id(dormida.id).actualizada_en == cambio
    assert db.por_id(activa.id).actualizada_en == T0
    assert db.avanzar(db.por_id(dormida.id), cambio + timedelta(hours=1)).hambre > 95.0

def test_el_reloj_de_las_que_dormian_se_pone_una_sola_vez():
    nacer(nombre="Ana")
    dormida = db.crear(U, G, "pulpo", "Bea", STATS, T0, activa=False)
    borrar_la_marca("el_tiempo_para_todos")
    cambio = T0 + timedelta(days=40)
    db.inicializar(cambio)
    db.inicializar(cambio + timedelta(days=3))
    assert db.por_id(dormida.id).actualizada_en == cambio

def test_dos_arranques_a_la_vez_ponen_el_reloj_una_vez():
    nacer(nombre="Ana")
    dormida = db.crear(U, G, "pulpo", "Bea", STATS, T0, activa=False)
    borrar_la_marca("el_tiempo_para_todos")
    momentos = [T0 + timedelta(days=40), T0 + timedelta(days=41)]
    with ThreadPoolExecutor(max_workers=2) as hilos:
        list(hilos.map(db.inicializar, momentos))
    with db.conectar() as con:
        marca = con.execute("SELECT hecho_en FROM cambios_hechos WHERE clave = 'el_tiempo_para_todos'").fetchone()[0]
    assert db.por_id(dormida.id).actualizada_en.isoformat() == marca

def test_el_plantel_al_dia_avanza_a_cada_uno_y_no_escribe():
    nacer(nombre="Ana")
    otra = db.crear(U, G, "pulpo", "Bea", STATS, T0, activa=False)
    antes = volcado()
    al_dia = db.plantel_al_dia(U, G, T0 + timedelta(hours=10))
    assert [c.nombre for c in al_dia] == ["Ana", "Bea"]
    assert all(c.hambre < 100.0 for c in al_dia) and volcado() == antes
```

Además: en `tests/test_db.py`, una muerta de antes no cambia el día del cambio (`muerta_de_antes(...)`, su `actualizada_en` queda igual). En `tests/test_economia_entrenamiento_conjunto.py`, la que hoy se llama `test_solo_la_activa_avanza_el_tiempo_y_la_reserva_conserva_su_reloj` pasa a `test_el_entrenamiento_conjunto_pone_al_dia_a_los_dos`: tras entrenar 10 horas después, las dos filas tienen `actualizada_en == ahora` y la comida de la reserva es la de `sim.avanzar(reserva, ahora)` menos 10. En `tests/test_web_incubadora.py`, `test_el_plantel_ensena_a_cada_uno_como_esta_ahora`: con un segundo gachamon creado con `db.crear(..., activa=False)` y el reloj tres días después, su `retrato` en `GET incubadora` lleva la cara de `sim.avanzar(ese, ahora).animo_visual`. En `tests/test_web_refugio.py`, lo mismo para la lista `viven` del refugio.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_simulacion.py tests/test_db.py tests/test_economia_entrenamiento_conjunto.py tests/test_web_incubadora.py tests/test_web_refugio.py -q -k "no_es_la_activa or dormian or a_la_vez or al_dia or como_esta_ahora or pone_al_dia"`
Expected: FAIL (la reserva no avanza; no existen `cambios_hechos`, `plantel_al_dia` ni el parámetro de `inicializar`).

- [ ] **Step 3: Implementar**

`avanzar`: la salida temprana queda en `if not criatura.viva`; reescribe el docstring (ya no hay incubadora que congele). En `_migrar(con, ahora)`, después de las columnas: `if _una_sola_vez(con, "el_tiempo_para_todos", ahora):` un solo `UPDATE criaturas SET actualizada_en = ? WHERE muerta_en IS NULL AND activa = 0`. La marca y el `UPDATE` van en la misma transacción de `_migrar`. `ejecutar_entrenamiento_conjunto` avanza también a la reserva con `db._avanzar_en`. `NombreModal.on_submit` avanza siempre (se van los dos `if criatura.activa:` que protegían a «la que duerme» y sus comentarios; publicar la ficha sigue siendo sólo para la activa). `el_plantel` y `_refugio` leen con `db.plantel_al_dia`.

- [ ] **Step 4: Poner la suite en verde**

Run: `./venv/bin/python -m pytest -q`
Expected: fallan las pruebas que esperaban una reserva congelada. Aplícales la regla de las pruebas, sin tocar todavía `db._activar_en` ni `economia.cambiar_de_activo` (son de la Task 2). Termina con la suite entera en verde.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "feat(reglas): a todos los gachamones les pasa el tiempo, y a los que dormían les empieza el día del cambio"
```

---

### Task 2: El activo es el que sale contigo

**Files:**
- Modify: `db.py` (`_activar_en`, `activar`, `ascender_de_la_incubadora`, `activa_al_dia`, el comentario de `MAXIMO_PLANTEL`), `economia.py` (`cambiar_de_activo`, `ResultadoCambio`), `simulacion.py` (el comentario del campo `activa`), `equipo.py`, `pantalla.py` (`render`, `EMOJI_INCUBADORA`), `vistas.py` (`_ejecutar`, los tres `en_la_incubadora=`), `cogs/competencias.py` (`texto_testigo_competencia`), `cogs/social.py` (manual, «El plantel»), `web/incubadora.py` (`_dicho`)
- Test: `tests/test_cambiar_de_activo.py`, `tests/test_db.py`, `tests/test_pantalla.py`, `tests/test_vistas.py`, `tests/test_economia_competencia.py`, `tests/test_carga.py`, `tests/test_web_incubadora.py`

**Interfaces:**
- Consumes: Task 1 (`sim.avanzar` para todos).
- Produces:
  - `db._activar_en(con, criatura_id: int) -> None` y `db.activar(criatura_id, usuario_id, guild_id) -> bool`: sólo cambian la marca `activa` (primero todas a 0, después ésa a 1: el índice `una_activa` no admite el orden contrario). **No tocan `actualizada_en`** y ya no reciben `ahora`.
  - `db.ascender_un_relevo(usuario_id, guild_id) -> sim.Criatura | None`: el nombre nuevo de `ascender_de_la_incubadora` (con GitNexus `rename`), sin `ahora`.
  - `economia.cambiar_de_activo(usuario_id, guild_id, criatura_id, ahora) -> ResultadoCambio`: misma firma y mismos motivos. Con `ok`, `criatura` (con la que sales) y `saliente` (la que se queda) van avanzadas hasta `ahora`; **no se guarda** el paso del tiempo de ninguna.
  - `pantalla.render(..., en_casa: int = 0)` (antes `en_la_incubadora`) y `pantalla.EMOJI_EN_CASA = "🏠"` (antes `EMOJI_INCUBADORA`); `equipo.py` usa el de `pantalla` y deja de definir el suyo.
  - Las frases de «Frases nuevas» que hablan de cambiar, del pie de la ficha, del testigo y del manual «El plantel».

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_cambiar_de_activo.py` (sustituyen a `test_cambiar_pone_al_dia_a_la_que_sale` y a `test_la_que_entra_sale_al_dia_y_sin_reloj`):

```python
def test_cambiar_no_le_borra_el_tiempo_a_la_que_entra():
    nace("Ana")
    b = nace("Bea", activa=False)
    cinco = T0 + timedelta(hours=5)
    resultado = economia.cambiar_de_activo(U, G, b.id, cinco)
    assert resultado.ok and resultado.criatura.id == b.id
    assert resultado.criatura.hambre == pytest.approx(sim.avanzar(b, cinco).hambre)
    assert resultado.criatura.hambre < 100.0
    assert db.por_id(b.id).actualizada_en == T0

def test_a_la_que_se_queda_le_sigue_pasando_el_tiempo():
    a = nace("Ana")
    b = nace("Bea", activa=False)
    resultado = economia.cambiar_de_activo(U, G, b.id, T0 + timedelta(hours=1))
    assert resultado.saliente.id == a.id and resultado.saliente.activa is False
    veinte = T0 + timedelta(hours=20)
    assert db.avanzar(db.por_id(a.id), veinte).hambre == pytest.approx(sim.avanzar(a, veinte).hambre)

def test_ir_y_volver_no_ahorra_ni_duplica_el_tiempo():
    a = nace("Ana")
    b = nace("Bea", activa=False)
    for hora, quien in enumerate((b, a, b, a, b), start=1):
        assert economia.cambiar_de_activo(U, G, quien.id, T0 + timedelta(hours=hora)).ok
    final = T0 + timedelta(hours=10)
    for c in (a, b):
        assert db.avanzar(db.por_id(c.id), final).hambre == pytest.approx(sim.avanzar(c, final).hambre)
```

En `tests/test_pantalla.py`: `pantalla.render(criatura(), T0, en_casa=1)` y `en_casa=3` contienen `🏠 Tienes 1 más en casa · «Cambiar» para salir con otro` y `🏠 Tienes 3 más en casa · «Cambiar» para salir con otro`; con `en_casa=0` no sale la línea; ninguna contiene `incubadora`. En `tests/test_vistas.py`: el texto de `equipo.texto_del_plantel` con dos gachamones contiene `en casa`, `🏠` y el pie nuevo, y no contiene `incubadora`; el mensaje tras cambiar es `🧬 Ahora sales con **Bea**.` seguido de ``Mírala con `/mascota`.`` (o `Míralo`); y pulsar un botón de la ficha de uno que no es el activo contesta la frase nueva. En `tests/test_economia_competencia.py`: el testigo dice `Desde casa,`. En `tests/test_carga.py`, junto a las que ya leen el manual: «El plantel» contiene `el que sale contigo` y `A los demás también les pasa el tiempo`, y no contiene `no les pasa el tiempo`. En `tests/test_web_incubadora.py`: sacar a otro contesta `Ahora sales con Bea.`.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_cambiar_de_activo.py tests/test_pantalla.py tests/test_vistas.py tests/test_economia_competencia.py tests/test_carga.py tests/test_web_incubadora.py -q`
Expected: FAIL en las nuevas (hoy la que entra sale con `actualizada_en == ahora` y los textos dicen «incubadora»).

- [ ] **Step 3: Implementar.** En `cambiar_de_activo` se quedan el remiendo del principio (`db.activa_al_dia`) y las comprobaciones; se van el guardado de la saliente y el reloj de la que entra. Reescribe los docstrings de `cambiar_de_activo`, `ResultadoCambio`, `activar`, `activa_al_dia` y `ascender_un_relevo`, y los comentarios de `MAXIMO_PLANTEL` y del campo `activa`: nadie duerme ni despierta. Comprueba que la página del manual sigue por debajo de 2000 caracteres (la prueba que lo vigila tiene que seguir pasando) **sin mover bloques entre páginas**.

- [ ] **Step 4: Correr la suite**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS. Además `git grep -n -i "incubadora" -- equipo.py pantalla.py cogs/competencias.py` sólo enseña `equipo.NO_SALE_SIN_NOMBRE`, que se va en la Task 6.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "feat(reglas): el activo es el que sale contigo; cambiar de activo ya no duerme ni despierta a nadie"
```

---

### Task 3: Cuidar al que elijas

**Files:**
- Modify: `economia.py` (`ejecutar_cuidado`; nueva `_cuidar_en`), `db.py` (`acariciar`), `web/juego.py` (`cuidar`, `acariciar`)
- Test: `tests/test_economia_cuidado.py`, `tests/test_caricia.py`, `tests/test_web_acciones.py`

**Interfaces:**
- Consumes: Task 1.
- Produces:
  - `economia.ejecutar_cuidado(evento_id, usuario_id, guild_id, accion, ahora, criatura_id: int | None = None) -> ResultadoCuidado | None`. Sin `criatura_id`, al activo, como hoy (Discord no cambia). Con él, a ese gachamon si es de esa persona, de ese servidor y está vivo; si no, `None` sin escribir nada. La `solicitud` del ledger es `accion` sin id y `f"{accion}:{criatura_id}"` con él, así que el mismo evento pedido para otro gachamon levanta el `RuntimeError` de siempre (el texto no cambia: «el evento de cuidado pertenece a otra acción»). En un replay con id, `criatura` es ese gachamon.
  - `economia._cuidar_en(con, evento_id, usuario_id, guild_id, criatura, accion, ahora, solicitud) -> ResultadoCuidado`: lo que hoy hace `ejecutar_cuidado` desde mirar la espera hasta el recibo, sobre una criatura **ya avanzada** y dentro de la transacción de quien llama. Es mover código, no cambiarlo: la Task 4 lo reutiliza.
  - `db.acariciar(usuario_id, guild_id, ahora, criatura_id: int | None = None) -> ResultadoCaricia`, con la misma regla; uno ajeno, muerto o inexistente da `ResultadoCaricia(False, None, timedelta(0))`.
  - `POST /gachamon/api/cuidar` y `POST /gachamon/api/acariciar` aceptan `gachamon_id` opcional en el cuerpo. Si viene y no pasa `es_un_id`: 422 `peticion`. Con él no se llama a `la_misma_activa`; si el juego no encuentra a quién: 409 `no_esta`, `Ese gachamon ya no está.`. Las dos respuestas ganan la clave `gachamon`: `estado.ficha(db.avanzar(criatura, ahora), ahora)` del que recibió el cuidado. Sin `gachamon_id` todo sigue como hoy.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_economia_cuidado.py`:

```python
def test_se_cuida_al_que_se_elige_y_al_activo_no_le_cae_nada():
    activa = nacer("Ana")
    otra = replace(nacer("Bea", activa=False), animo=40.0)
    db.guardar(otra)
    hecho = economia.ejecutar_cuidado("ev-otra", "u1", "g1", sim.JUGAR, T0, criatura_id=otra.id)
    assert hecho.ok and hecho.criatura.id == otra.id and hecho.criatura.animo == 65.0
    assert hecho.delta_asciicoins == 1 and hecho.usados == 1
    assert db.por_id(activa.id) == activa
    assert db.espera_de(otra.id, sim.JUGAR, T0) == sim.COOLDOWNS[sim.JUGAR]
    assert db.espera_de(activa.id, sim.JUGAR, T0) == timedelta(0)

def test_el_tope_de_cuidados_es_de_la_persona_no_de_cada_gachamon():
    ids = [nacer("Ana").id] + [nacer(f"G{n}", activa=False).id for n in range(12)]
    for criatura_id in ids:
        db.guardar(replace(db.por_id(criatura_id), limpieza=0.0))
    pagos = [
        economia.ejecutar_cuidado(f"ev-{n}", "u1", "g1", sim.LIMPIAR, T0, criatura_id=criatura_id)
        for n, criatura_id in enumerate(ids)
    ]
    assert [p.delta_asciicoins for p in pagos] == [1] * 12 + [0]
    assert pagos[-1].ok and pagos[-1].topada
    assert economia.saldos("u1", "g1").asciicoins == 50 + economia.TOPE_CUIDADOS

@pytest.mark.parametrize("caso", ["ajeno", "muerto", "no_existe"])
def test_cuidar_a_quien_no_es_tuyo_o_no_esta_no_hace_nada(caso):
    nacer("Ana")
    ajeno = db.crear("u2", "g1", "pulpo", "Otro", STATS, T0)
    muerta = replace(nacer("Bea", activa=False), muerta_en=T0, causa_muerte="hambre")
    db.guardar(muerta)
    criatura_id = {"ajeno": ajeno.id, "muerto": muerta.id, "no_existe": 999_999}[caso]
    assert economia.ejecutar_cuidado("ev-x", "u1", "g1", sim.JUGAR, T0, criatura_id=criatura_id) is None
    assert db.por_id(ajeno.id) == ajeno and db.por_id(muerta.id) == muerta
    assert economia.saldos("u1", "g1").asciicoins == 50

def test_el_replay_devuelve_al_mismo_y_el_evento_no_sirve_para_otro():
    nacer("Ana")
    otra = nacer("Bea", activa=False)
    tercera = nacer("Cía", activa=False)
    economia.ejecutar_cuidado("ev-r", "u1", "g1", sim.JUGAR, T0, criatura_id=otra.id)
    otra_vez = economia.ejecutar_cuidado("ev-r", "u1", "g1", sim.JUGAR, T0, criatura_id=otra.id)
    assert otra_vez.replay and otra_vez.criatura.id == otra.id
    assert economia.saldos("u1", "g1").asciicoins == 51
    with pytest.raises(RuntimeError, match="otra acción"):
        economia.ejecutar_cuidado("ev-r", "u1", "g1", sim.JUGAR, T0, criatura_id=tercera.id)
```

En `tests/test_caricia.py`: `test_se_acaricia_al_que_se_elige` (a uno no activo le sube el ánimo en 5 y queda con su espera de 19 minutos; el activo sigue igual y sin espera) y `test_acariciar_a_uno_ajeno_no_hace_nada` (resultado sin criatura, nada escrito). En `tests/test_web_acciones.py`: `test_cuidar_a_otro_por_su_id` (cuenta con huevo y un segundo gachamon creado con `db.crear(YO, G, "pollito", "Bea", STATS, ahora, activa=False)`; `POST cuidar` con `{"accion": "jugar", "evento_id": …, "gachamon_id": ese}` → 200, `cuerpo["gachamon"]["id"] == ese`, `cuerpo["monedas"] == 1`, y `cuerpo["estado"]["gachamon"]["esperas"]["jugar"] == 0`: al activo no le corre la espera); `test_cuidar_a_uno_ajeno_es_no_esta` (id de un gachamon de otra identidad → 409 `no_esta` y ninguno cambia); `test_un_gachamon_id_que_no_es_un_id_es_un_422` (`"7"`, `-1`, `True` → 422 `peticion`); `test_acariciar_a_otro_por_su_id`.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_economia_cuidado.py tests/test_caricia.py tests/test_web_acciones.py -q -k "elige or de_la_persona or no_es_tuyo or replay_devuelve or por_su_id or no_esta or no_es_un_id or ajeno"`
Expected: FAIL (`ejecutar_cuidado` y `acariciar` no aceptan `criatura_id`).

- [ ] **Step 3: Implementar.** Extrae primero `_cuidar_en` sin cambiar comportamiento (la suite de cuidado tiene que seguir en verde tal cual) y después añade `criatura_id`.

- [ ] **Step 4: Correr la suite**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "feat(cuidar): cada cuidado le cae al gachamon que elijas; el tope diario sigue siendo uno por persona"
```

---

### Task 4: «A todos»

**Files:**
- Modify: `simulacion.py` (nueva `le_serviria`), `economia.py` (nuevas `ResultadoATodos` y `cuidar_a_todos`), `web/juego.py` (ruta nueva)
- Create: `tests/test_a_todos.py`
- Test: `tests/test_simulacion.py`, `tests/test_a_todos.py`, `tests/test_web_acciones.py`

**Interfaces:**
- Consumes: `economia._cuidar_en` (Task 3), `db.plantel_en` (Task 1), `economia._ya_hecha` y `economia._anotar` (ya existen).
- Produces:
  - `sim.le_serviria(criatura: Criatura, accion: str) -> bool`: falso si está muerta, si `accion` es `ALIMENTAR` y `hambre >= UMBRAL_EMPACHO`, o si el cuidado la dejaría igual (`_efecto_de(criatura, accion).criatura == criatura`). Verdadero en lo demás.
  - `economia.ResultadoATodos` (congelado): `accion: str`, `tocados: tuple[int, ...] = ()` (ids, en el orden del plantel), `de_cuantos: int = 0` (los vivos que tenía), `delta_asciicoins: int = 0`, `cuidados: tuple[ResultadoCuidado, ...] = ()` (uno por tocado; vacío en un replay), `replay: bool = False`.
  - `economia.cuidar_a_todos(evento_id, usuario_id, guild_id, accion, ahora) -> ResultadoATodos`. `accion` fuera de `sim.ACCIONES_DE_CUIDADO` levanta `ValueError`. Todo bajo un solo `BEGIN IMMEDIATE`: a cada vivo, en el orden de `db.plantel_en`, se le pone al día; se salta al que no `le_serviria` o al que le corre la espera y no `puede_saltarse_espera`; a los demás, `_cuidar_en` con el evento `f"{evento_id}:{criatura.id}"` y `solicitud=accion`. Si le tocó a alguien se anota con `_anotar(..., "a_todos", accion, {"tocados": [...], "de_cuantos": n, "monedas": m}, ahora)`; si no le tocó a nadie no se anota y repetirlo vuelve a decidir. El replay sale de `_ya_hecha(..., "a_todos", accion)`.
  - `POST /gachamon/api/cuidar/todos` con `{"accion", "evento_id"}` (validados como en `cuidar`). `RuntimeError` → 409 `evento`, con la frase de `cuidar`. `de_cuantos == 0` → 409 `sin_gachamon`, `No tienes gachamones que cuidar.`. Si no, 200 con `ok` (si le tocó a alguno), `a_cuantos`, `de_cuantos`, `tocados`, `mensaje` (las frases de «Frases nuevas»), `monedas`, `logros` (los de `economia.pagar_logros` de cada cuidado, cada uno con `nombre`, `gemas` y `de`, el nombre del gachamon) y `estado`.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_simulacion.py`:

```python
def test_a_quien_le_serviria_cada_cuidado():
    assert sim.le_serviria(criatura(hambre=89.0), sim.ALIMENTAR)
    assert not sim.le_serviria(criatura(hambre=90.0), sim.ALIMENTAR)
    assert sim.le_serviria(criatura(limpieza=99.0), sim.LIMPIAR)
    assert not sim.le_serviria(criatura(limpieza=100.0), sim.LIMPIAR)
    assert sim.le_serviria(criatura(animo=100.0), sim.JUGAR)
    assert sim.le_serviria(criatura(hambre=0.0), sim.ENTRENAR)
    assert not sim.le_serviria(criatura(muerta_en=T0), sim.JUGAR)
```

En `tests/test_a_todos.py` (ayudas como las de `tests/test_economia_cuidado.py`: `bd`, `T0`, `STATS`, y `con(nombre, activa=False, **barras)` que crea y guarda con esas barras):

```python
def test_le_toca_a_cada_uno_que_puede_y_dice_a_cuantos():
    hambrienta = con("Ana", activa=True, hambre=50.0)
    llena = con("Bea", hambre=95.0)
    esperando = con("Cía", hambre=70.0)
    db.poner_cooldown(esperando.id, sim.ALIMENTAR, T0)
    hecho = economia.cuidar_a_todos("ev-todos", "u1", "g1", sim.ALIMENTAR, T0)
    assert hecho.tocados == (hambrienta.id,) and hecho.de_cuantos == 3
    assert hecho.delta_asciicoins == 1 and len(hecho.cuidados) == 1
    assert db.por_id(hambrienta.id).hambre == 80.0
    assert db.por_id(llena.id).hambre == 95.0          # no se empacha
    assert db.por_id(esperando.id).hambre == 70.0

def test_paga_como_cuidarlos_de_a_uno_y_solo_lo_que_cabe_en_el_tope():
    ids = [con("Ana", activa=True, limpieza=0.0).id] + [con(f"G{n}", limpieza=0.0).id for n in range(12)]
    hecho = economia.cuidar_a_todos("ev-13", "u1", "g1", sim.LIMPIAR, T0)
    assert hecho.tocados == tuple(ids) and hecho.de_cuantos == 13
    assert hecho.delta_asciicoins == economia.TOPE_CUIDADOS
    assert all(db.por_id(i).limpieza == 100.0 for i in ids)
    assert all(db.espera_de(i, sim.LIMPIAR, T0) == sim.COOLDOWNS[sim.LIMPIAR] for i in ids)
    assert all(db.marcador(i)[lgr.CUIDADOS] == 1 for i in ids)
    assert economia.saldos("u1", "g1").asciicoins == 50 + economia.TOPE_CUIDADOS

def test_repetir_el_evento_no_cuida_ni_paga_otra_vez():
    a = con("Ana", activa=True, animo=40.0)
    b = con("Bea", animo=40.0)
    primero = economia.cuidar_a_todos("ev-r", "u1", "g1", sim.JUGAR, T0)
    segundo = economia.cuidar_a_todos("ev-r", "u1", "g1", sim.JUGAR, T0 + timedelta(hours=3))
    assert segundo.replay and segundo.tocados == primero.tocados == (a.id, b.id)
    assert segundo.de_cuantos == 2 and segundo.delta_asciicoins == 2 and segundo.cuidados == ()
    assert db.por_id(a.id).animo == 65.0 and economia.saldos("u1", "g1").asciicoins == 52
    with pytest.raises(RuntimeError):
        economia.cuidar_a_todos("ev-r", "u1", "g1", sim.LIMPIAR, T0)

def test_antes_de_cuidar_les_pasa_el_tiempo():
    b = con("Bea", hambre=100.0)
    con("Ana", activa=True, hambre=100.0)
    tarde = T0 + timedelta(hours=30)
    economia.cuidar_a_todos("ev-t", "u1", "g1", sim.ALIMENTAR, tarde)
    assert db.por_id(b.id).hambre == pytest.approx(sim.avanzar(b, tarde).hambre + 30.0)

def test_si_no_le_toca_a_nadie_no_se_anota_y_se_puede_repetir():
    a = con("Ana", activa=True)                          # limpia
    nada = economia.cuidar_a_todos("ev-n", "u1", "g1", sim.LIMPIAR, T0)
    assert nada.tocados == () and nada.de_cuantos == 1 and not nada.replay
    db.guardar(replace(db.por_id(a.id), limpieza=10.0))
    ahora_si = economia.cuidar_a_todos("ev-n", "u1", "g1", sim.LIMPIAR, T0)
    assert ahora_si.tocados == (a.id,) and not ahora_si.replay

def test_sin_gachamones_no_hay_a_quien():
    muerta = con("Ana", activa=True, muerta_en=T0, causa_muerte="hambre")
    hecho = economia.cuidar_a_todos("ev-0", "u1", "g1", sim.JUGAR, T0)
    assert hecho.tocados == () and hecho.de_cuantos == 0
    assert db.por_id(muerta.id) == muerta

def test_un_fallo_a_medias_no_deja_a_nadie_cuidado(monkeypatch):
    a = con("Ana", activa=True, animo=40.0)
    b = con("Bea", animo=40.0)
    de_verdad, llamadas = db.poner_cooldown_en, []
    def falla_a_la_segunda(*args):
        llamadas.append(args)
        if len(llamadas) == 2:
            raise sqlite3.OperationalError("disco lleno")
        return de_verdad(*args)
    monkeypatch.setattr(db, "poner_cooldown_en", falla_a_la_segunda)
    with pytest.raises(sqlite3.OperationalError):
        economia.cuidar_a_todos("ev-f", "u1", "g1", sim.JUGAR, T0)
    assert db.por_id(a.id).animo == 40.0 and db.por_id(b.id).animo == 40.0
    assert economia.saldos("u1", "g1").asciicoins == 50
```

En `tests/test_web_acciones.py`: `test_a_todos_por_la_web_dice_a_cuantos` (huevo más dos `db.crear(..., activa=False)`, reloj 6 horas después; `POST cuidar/todos` con `jugar` → 200, `ok`, `a_cuantos == 3`, `de_cuantos == 3`, `mensaje == "Jugaste con 3 de 3."`, `monedas == 3`, saldo 53; repetido con el mismo evento, los mismos números y saldo 53); `test_a_todos_cuando_a_nadie_le_toca` (recién nacido, `limpiar` → 200, `ok` falso, `a_cuantos == 0`, `mensaje == "Ahora mismo no le toca a ninguno."`); `test_a_todos_sin_gachamones_es_un_409` (cuenta con avatar y sin huevo → 409 `sin_gachamon`); `test_a_todos_con_una_accion_que_no_existe_es_un_422`.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_a_todos.py tests/test_simulacion.py tests/test_web_acciones.py -q -k "todos or serviria or le_toca or paga_como or repetir or antes_de_cuidar or no_le_toca or sin_gachamones or fallo_a_medias"`
Expected: FAIL (`le_serviria`, `cuidar_a_todos` y la ruta no existen).

- [ ] **Step 3: Implementar.**

- [ ] **Step 4: Correr la suite**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "feat(cuidar): «a todos» le hace un cuidado a cada gachamon que puede recibirlo y dice a cuántos"
```

---

### Task 5: El recluta llega con nombre

**Files:**
- Create: `nombres.py`
- Modify: `simulacion.py` (campo `Criatura.se_nombro_solo`), `db.py` (`MIGRACIONES`, `CAMPOS`, `_a_criatura`, `_a_valores`, `crear`, `poner_nombre_a`, `poner_nombre_a_la_activa`, `_migrar`), `nacer.py` (`bautizar`, `bautizar_a`; nuevas `puede_recibir_nombre`, `nombre_de_recluta`, `unir_recluta`), `economia.py` (`_usar`, la placa), `cogs/aventura.py` (`_unirse`), `vistas.py` (`NombrarReclutaView`, `sin_nombrar_de`), `cogs/social.py` (manual, aventura), `web/estado.py` (`ficha`)
- Test: `tests/test_nombres.py`, `tests/test_nacer.py`, `tests/test_bautizar_a.py`, `tests/test_db.py`, `tests/test_usar_objeto.py`, `tests/test_vistas.py`, `tests/test_carga.py`, `tests/test_web_estado.py`, y la prueba de `_unirse` (búscala con `git grep -n "Se une a tu equipo\|NOMBRE_PENDIENTE" tests/`)

**Interfaces:**
- Produces:
  - `nombres.NOMBRES: tuple[str, ...]`: los 40 de «Frases nuevas», en ese orden. `nombres.elegir(rng: random.Random, evitar: Collection[str] = ()) -> str`: uno al azar que no esté en `evitar`, comparando con `casefold()`; si estuvieran todos, uno cualquiera de la lista. Módulo puro: no importa `db`.
  - `sim.Criatura.se_nombro_solo: bool = False`, columna `criaturas.se_nombro_solo INTEGER NOT NULL DEFAULT 0` (por `MIGRACIONES`, como `casa_id`), y `db.crear(..., se_nombro_solo: bool = False)`.
  - `nacer.puede_recibir_nombre(criatura) -> bool`: `espera_nombre(criatura) or criatura.se_nombro_solo`. `nacer.bautizar` y `nacer.bautizar_a` la usan donde hoy usan `espera_nombre`; `db.poner_nombre_a` y `db.poner_nombre_a_la_activa` escriben `nombre` y dejan `se_nombro_solo = 0`. El segundo intento sigue siendo `YA_BAUTIZADO`.
  - `nacer.nombre_de_recluta(usuario_id, guild_id, especie: str, rng: random.Random) -> str`: `nombres.elegir` evitando los nombres de sus vivos y el de esa especie. Con el plantel vacío también funciona.
  - `nacer.unir_recluta(usuario_id, guild_id, *, especie: str, stats, genero: str, caracter: str, ahora, rng: random.Random | None = None, canal_id: str | None = None) -> sim.Criatura`: crea al recluta con su nombre, `activa=False`, `reclutada=True` y `se_nombro_solo=True`. Deja pasar el `ValueError` del tope y el `sqlite3.IntegrityError`, como `db.crear`.
  - Al arrancar, `_migrar` le pone nombre a cada fila con `nombre = ''`: uno de `nombres.NOMBRES` que no sea el de su especie ni el de otro vivo de su dueño, con `se_nombro_solo = 1`. Fila a fila, como el carácter; repetirlo no cambia nada.
  - La placa (`economia._usar` con `propuesto`) deja `se_nombro_solo` en falso.
  - `vistas.el_que_se_nombro_solo(usuario_id, guild_id) -> sim.Criatura | None` (antes `sin_nombrar_de`): el más antiguo de sus vivos con `se_nombro_solo`. `NombrarReclutaView` conserva su `custom_id` (`tama:nombrar_recluta`), abre `NombreModal(recluta.nombre, recluta.id)` y su botón dice `Ponerle otro nombre`.
  - `web.estado.ficha(...)` gana la clave `se_nombro_solo` (booleano).

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_nombres.py`:

```python
def test_la_lista_de_nombres_de_recluta_vale():
    assert len(nombres.NOMBRES) == 40 > db.MAXIMO_PLANTEL + 1
    assert all(sim.normalizar_nombre(n) == n for n in nombres.NOMBRES)
    assert len({n.casefold() for n in nombres.NOMBRES}) == 40
    assert not {n.casefold() for n in nombres.NOMBRES} & {e.nombre.casefold() for e in esp.ESPECIES.values()}

def test_elegir_evita_los_que_ya_hay_sin_mirar_mayusculas():
    todos_menos_uno = [n.upper() for n in nombres.NOMBRES if n != "Trufa"]
    assert nombres.elegir(random.Random(7), todos_menos_uno) == "Trufa"
    assert nombres.elegir(random.Random(7), nombres.NOMBRES) in nombres.NOMBRES
```

En `tests/test_nacer.py`:

```python
def test_el_recluta_llega_con_el_nombre_que_se_puso_solo():
    activa = nace("Nube")                                  # ya hay una Nube
    recluta = nacer.unir_recluta(
        U, G, especie="pollito", stats=STATS, genero=esp.HEMBRA, caracter=esp.CARACTER_POR_DEFECTO,
        ahora=T0, rng=random.Random(3),
    )
    assert recluta.nombre in nombres.NOMBRES and recluta.nombre != "Nube"
    assert recluta.se_nombro_solo and recluta.activa is False
    assert db.por_id(recluta.id) == recluta
    assert db.criatura_activa(U, G).id == activa.id
    assert db.marcador_de_persona(U, G)[lgr.RECLUTADOS] == 1

def test_el_nombre_de_un_recluta_se_elige_tambien_sin_ningun_gachamon():
    assert nacer.nombre_de_recluta(U, G, "pollito", random.Random(1)) in nombres.NOMBRES
```

En `tests/test_db.py`:

```python
def test_el_unico_vivo_sin_nombre_recibe_nombre_y_pasa_a_ser_el_activo():
    muerta_de_antes(nacer(nombre="Ana"))
    recluta = db.crear(U, G, "pulpo", "Provisional", STATS, T0, activa=False)
    with db.conectar() as con:                           # como lo dejó el bot de antes
        con.execute("UPDATE criaturas SET nombre = '' WHERE id = ?", (recluta.id,))
    assert db.criatura_activa(U, G) is None
    db.inicializar()
    activa = db.activa_al_dia(U, G, T0 + timedelta(hours=1))
    assert activa.id == recluta.id and activa.activa and activa.nombre in nombres.NOMBRES
```

En `tests/test_bautizar_a.py`: `test_al_que_se_nombro_solo_se_le_cambia_el_nombre_una_vez` (tras `nacer.unir_recluta`, `bautizar_a(..., "Rayo", T0)` deja `nombre == "Rayo"` y `se_nombro_solo` falso en la base; un segundo `bautizar_a` levanta `NoSePuedeBautizar` con `motivo == nacer.YA_BAUTIZADO`; con el nombre de su especie, `NombreNoVale` y sigue pudiendo). En `tests/test_db.py`: `test_los_reclutas_sin_nombre_se_lo_ponen_solos_al_arrancar` (dos filas del mismo dueño a las que se les vacía el nombre con un `UPDATE`, y una tercera llamada «Nube»; tras `db.inicializar()` las dos tienen nombres de la lista, distintos entre sí y de «Nube», con `se_nombro_solo` puesto; tras un segundo `db.inicializar()` conservan los mismos; «Nube» no cambió y sigue con `se_nombro_solo` en falso). En `tests/test_usar_objeto.py`: `test_la_placa_deja_el_nombre_como_tuyo`. En `tests/test_vistas.py`: `test_el_boton_del_recluta_abre_el_formulario_con_su_nombre` (con un recluta de `unir_recluta`, pulsar `NombrarReclutaView.nombrar` manda un `NombreModal` con `criatura_id == recluta.id` y `nombre.default == recluta.nombre`; sin ninguno con `se_nombro_solo`, contesta `Ninguno de tus gachamones espera un nombre nuevo.`). La prueba de `_unirse`: el mensaje contiene `Dice que se llama **` con el nombre del recién creado y no contiene `incubadora`. En `tests/test_carga.py`: la página de la aventura contiene `se pone un nombre él solo`, ninguna página contiene `incubadora`, y la prueba que exigía esa palabra en el manual deja de exigirla. En `tests/test_web_estado.py`: `estado["gachamon"]["se_nombro_solo"]` es falso para el del huevo.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_nombres.py tests/test_nacer.py tests/test_bautizar_a.py tests/test_db.py tests/test_usar_objeto.py tests/test_vistas.py tests/test_carga.py tests/test_web_estado.py -q -k "recluta or nombre or placa or manual or se_nombro or unico_vivo"`
Expected: FAIL (no existen `nombres`, `unir_recluta` ni `se_nombro_solo`).

- [ ] **Step 3: Implementar.** `cogs/aventura.py::_unirse` llama a `nacer.unir_recluta` en vez de a `db.crear` y enseña la frase nueva con el nombre. `sim.NOMBRE_PENDIENTE`, `sim.esta_sin_nombrar` y `sim.nombre_visible` **siguen existiendo** en esta tarea: los quita la Task 6.

- [ ] **Step 4: Correr la suite**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "feat(reclutar): el recluta llega con un nombre que se pone él solo, y se le puede cambiar una vez"
```

---

### Task 6: Fuera el «sin nombre»

**Files:**
- Modify: `simulacion.py` (`NOMBRE_PENDIENTE`, `SIN_NOMBRE`, `esta_sin_nombrar`, `nombre_visible`), `db.py` (`crear`, `activar`, `ascender_un_relevo`, `quien_lleva_cada`), `economia.py` (`cambiar_de_activo`, `ResultadoCambio`, `ejecutar_entrenamiento_conjunto`, los tres usos de `nombre_visible`), `equipo.py`, `vistas.py` (`bautizar`, `abrir_entrenamiento_conjunto`, quien pasa `bautizar` a `equipo.abrir_plantel`), `cogs/social.py` (`plantel` y los usos de `nombre_visible`), `cogs/competencias.py`, `comun.py`, `tienda.py`, `web/estado.py` (`_sin_nombre`, `_refugio`, la clave `sin_nombre` de `armar`), `web/incubadora.py` (`_del_plantel`, `_dicho`), `web/juego.py` (`romper_el_huevo`), `web/ropero.py`
- Test: `tests/test_db.py`, `tests/test_cambiar_de_activo.py`, `tests/test_vistas.py`, `tests/test_web_estado.py`, `tests/test_web_incubadora.py`, `tests/test_web_nacer.py`, `tests/test_web_refugio.py`, y las que nombren lo que se quita (`git grep -n "sin_nombre\|sin_nombrar\|NOMBRE_PENDIENTE\|nombre_visible\|SIN_NOMBRE" tests/`)

**Interfaces:**
- Consumes: Task 5 (nadie nace sin nombre y los que quedaban se lo pusieron al arrancar).
- Produces:
  - `db.crear` levanta `ValueError("una criatura nace con nombre")` si `nombre` está vacío.
  - Desaparecen `sim.NOMBRE_PENDIENTE`, `sim.SIN_NOMBRE`, `sim.esta_sin_nombrar` y `sim.nombre_visible` (cada `sim.nombre_visible(x)` pasa a `x.nombre`); el motivo `sin_nombre` de `ResultadoCambio`; el `AND nombre != ''` de `db.activar` y el filtro por nombre de `db.ascender_un_relevo`; `equipo.NO_SALE_SIN_NOMBRE`, el estado «esperando nombre», la rama del recluta pendiente de `MenuPlantel` y el parámetro `bautizar` de `MenuPlantel`, `VistaPlantel` y `equipo.abrir_plantel`; `vistas.bautizar`; `web.estado._sin_nombre`.
  - El estado de la web **deja de traer** la clave `sin_nombre`, y cada fila de `GET incubadora` deja de traer `sin_nombre`. El cliente no se toca: lee una clave que ya no llega y sigue de largo.
  - En `web/juego.py`, `POST huevo` con plantel contesta siempre `Ya tienes un gachamon. El huevo es sólo el de partida.`.
  - `/plantel` con un solo gachamon y con varios, «Entrenar fuerza juntos» y el testigo de las competencias cuentan a todos los vivos que no son el activo. Las dos frases de «Entrenar fuerza juntos» de «Frases nuevas».

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_db.py`:

```python
def test_nadie_nace_sin_nombre():
    with pytest.raises(ValueError, match="nace con nombre"):
        db.crear(U, G, "pulpo", "", STATS, T0)
```

En `tests/test_web_estado.py`: `test_el_estado_ya_no_habla_de_reclutas_sin_nombre` (`"sin_nombre" not in estado`, con y sin gachamon). En `tests/test_web_incubadora.py`: ninguna fila del plantel trae `sin_nombre`; sacar a cualquiera de los tuyos es un sí. En `tests/test_web_nacer.py`: con plantel, `POST huevo` es 409 `ya_tienes` con la frase única. En `tests/test_vistas.py`: `equipo.abrir_plantel(interaccion, congelar, publicar)` se llama sin `bautizar`; elegir a cualquiera en `MenuPlantel` cambia de activo; `abrir_entrenamiento_conjunto` sin otro vivo contesta `No tienes otro gachamon con quien entrenar.`. Y `test_el_juego_ya_no_tiene_sin_nombre`: `sim` no tiene `NOMBRE_PENDIENTE`, `esta_sin_nombrar` ni `nombre_visible`.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_db.py tests/test_web_estado.py tests/test_web_incubadora.py tests/test_web_nacer.py tests/test_vistas.py -q -k "sin_nombre or nace_sin or huevo or plantel or entrenar"`
Expected: FAIL.

- [ ] **Step 3: Implementar.** Antes de borrar cada cosa, `git grep` de quién la usa. Las pruebas que fabricaban un recluta con `nombre=""` para comprobar que no podía salir, que pedía bautizo o que se llamaba «sin nombrar» se borran (regla de las pruebas); las que lo usaban de relleno pasan a darle un nombre.

- [ ] **Step 4: Correr la suite**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS. Además `git grep -n "esta_sin_nombrar\|nombre_visible\|NOMBRE_PENDIENTE\|NO_SALE_SIN_NOMBRE" -- '*.py'` no enseña nada, y `git grep -n "sin_nombre" -- '*.py' ':!tests'` tampoco.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "refactor(reglas): fuera el gachamon sin nombre: ya no puede darse, ni en las reglas ni en Discord ni en lo que manda la web"
```

---

### Task 7: Los documentos

**Files:**
- Modify: `AGENTS.md`, `README.md`, `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`

- [ ] **Step 1: `AGENTS.md`**, en «Invariantes del dominio», tal cual:
  - «Sólo la criatura activa avanza por tiempo y recibe efectos o recompensas ordinarios del activo.» pasa a `- A todos los gachamones vivos les pasa el tiempo, sean o no el activo: la comida, el ánimo y el aseo les bajan al mismo ritmo.`
  - «Una reserva viva y con nombre elegida explícitamente para `Entrenar juntos` puede recibir sólo…» pasa a ``- En `Entrenar juntos` los dos se ponen al día y reciben lo mismo: barras, XP, VETAS/evolución, cooldown `ENTRENAR` y marcador de criatura; el compañero no se vuelve activo.``
  - «Las reservas no decaen, reciben progreso pasivo ni heredan efectos del activo en ningún otro caso.» pasa a `- El activo es el que sale contigo: el que compite, va de aventura y conversa. Cambiar de activo no duerme ni despierta a nadie, ni le borra el tiempo a ninguno.`
  - «Reclutar, evolucionar o promover desde la incubadora tampoco reinicia los topes.» pasa a `- Reclutar o evolucionar tampoco reinicia los topes.`
  - «El hogar sólo afecta a la criatura activa; las de reserva siguen congeladas.» pasa a `- El hogar afecta a todos los que viven en él.`
  - «Cambiar de gachamon activo es una regla del juego (`economia.cambiar_de_activo`): la que sale queda al día antes de dormirse, y elegir…» pasa a ``- Cambiar de gachamon activo es una regla del juego (`economia.cambiar_de_activo`): sólo cambia quién sale contigo, y elegir a la que ya es la activa no cambia nada.``
  - «Ponerle nombre a un gachamon concreto es una regla (`nacer.bautizar_a`): sólo a uno tuyo, vivo y sin nombre, …» pasa a ``- Ponerle nombre a un gachamon concreto es una regla (`nacer.bautizar_a`): sólo a uno tuyo y vivo que todavía lo espere o que se lo haya puesto él solo, nunca con el nombre de su especie.``
  - Se añaden, después de la línea del activo: ``- Cada cuidado le cae a un gachamon concreto: al que se elige o, si no se elige, al activo. Las esperas son de cada gachamon; el tope diario de monedas es uno solo por persona.`` · ``- «A todos» le hace un cuidado a cada gachamon que puede recibirlo —le serviría y no está esperando— y paga como esos mismos cuidados hechos de a uno.`` · ``- Un recluta llega con un nombre que se pone él solo, de `nombres.py`, y su dueño se lo puede cambiar una vez. Ningún gachamon está sin nombre.`` · ``- Lo que se hace una sola vez al arrancar deja su marca en `cambios_hechos`, en la misma transacción que el cambio.``
  - Nada más: lo del refugio, las casas, el huevo y la Incubadora de la web es de los planes que siguen.

- [ ] **Step 2: `README.md`**: léelo entero buscando «incubadora», «no les pasa el tiempo», «dormid», «no trae nombre» y «reserva». Donde cuente la regla vieja (los que no son el activo no decaen; cambiar los duerme; el recluta llega sin nombre y no sale hasta tenerlo), que cuente la de ahora. La Incubadora como lugar de la web se queda como está.

- [ ] **Step 3: El documento de pendientes** gana, después de «Salió al ejecutar el rework 1 (nadie muere)», la sección **«Salió al ejecutar el rework 2 (el tiempo para todos)»**, con la voz de ese documento y sin SHAs ni números de tarea. El controlador le pasa a quien la escriba las notas de lo decidido y lo pendiente al terminar la Task 6.

- [ ] **Step 4: Comprobar y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "docs: el tiempo para todos, en la política, el README y los pendientes"
```

Después de la Task 7 el controlador lanza la revisión final de la rama (sólo los commits de este plan), recorre con el arnés una cuenta con tres gachamones (el paso del tiempo de los tres, cambiar de activo ida y vuelta, cuidar a otro y «a todos» por la API, y un recluta con su nombre) y le presenta el resultado a Felipe. No se fusiona, sube ni despliega: el plan 3 sigue en la misma rama.
