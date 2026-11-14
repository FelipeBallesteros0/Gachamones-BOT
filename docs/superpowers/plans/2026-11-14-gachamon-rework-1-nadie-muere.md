# Rework 1 · Nadie muere — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que ningún gachamon muera: con la comida en 0 se queda en 0 y sigue vivo, y desaparece todo lo que existía sólo para matar, avisar o anunciar una muerte.

**Architecture:** De dentro hacia fuera. Primero cambia la regla en los módulos puros (`simulacion.avanzar`, `aventura.aplicar_desgaste`); después se quita, capa por capa, lo que queda sin poder ocurrir: el bucle y los anuncios del bot, las ramas «se murió al ponerla al día» de `economia.py` y de los cogs, la pantalla del difunto en la web, y por último los relojes de muerte y sus tablas en `db.py`. Los que ya murieron siguen muertos y en el cementerio.

**Tech Stack:** Python 3.12, discord.py, FastAPI, SQLite síncrono, JavaScript de módulos sin empaquetar, pytest y `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-14-gachamon-rework-1-departamento-design.md` (secciones 3, 6, 7 y 9).

**Dónde encaja.** Es el plan 1 de 6 del proyecto 1 del rework: (1) nadie muere; (2) el tiempo para todos; (3) la vivienda por casillas en el servidor, el día del cambio y Discord; (4) el departamento en pantalla; (5) los muebles que se usan solos; (6) el pueblo sin Refugio ni Incubadora y los documentos. Los seis se juntan en la rama `rework/1-departamento` y **se publican juntos al final**: este plan no se sube ni se despliega solo. En este plan la incubadora, el refugio y las casas siguen como están.

## Global Constraints

- Nada se sube, se fusiona ni se despliega: todo queda en la rama local `rework/1-departamento`.
- Los módulos de juego no importan `discord`; `web/` no importa `discord` ni nada que lo importe; `db.py` no importa `economia.py`.
- Cada cambio de estado va en su transacción `BEGIN IMMEDIATE`, dentro de `db.py`, `economia.py` o `nacer.py`.
- Sin dependencias nuevas. Dominio determinista: el tiempo y el azar se inyectan en las pruebas.
- Nunca se abre `tamagotchi.db` ni `.env`; las pruebas usan bases temporales e ids sintéticos. El repo es público: sin IPs, ids de personas ni secretos.
- Antes de editar un símbolo, GitNexus `impact`; el índice se refresca sólo con `node .gitnexus/run.cjs analyze --index-only`.
- Cada commit: `./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "…"`.
- A quien juega se le dice «monedas» y «gemas»; el arte de texto de Discord no se reformatea.
- **Los que ya murieron no reviven**: una fila con `muerta_en` sigue muerta, sale en `/cementerio` y no vuelve al plantel.
- **Regla de las pruebas de este plan.** Una prueba que existía para comprobar que el tiempo o un viaje **mata** (o lo que pasa justo después: el relevo, el anuncio, el aviso, la pantalla del difunto) se **borra** con el código que cubría. Una prueba que usaba una muerte sólo como preparación de otra cosa (el cementerio, el ropero que devuelve la pieza, un panel viejo) **se conserva**, fabricando la muerta directamente con `muerta_en` puesto. Cada tarea dice en su informe cuántas borró y cuántas reescribió, y por qué.
- **Frases nuevas** (se le enseñan a Felipe al confirmar el plan; van tal cual):
  - Manual, «Cuidarlo»: `-# Si la comida llega a 0, **no se muere**: se queda en 0 hasta que le des de comer. Tarda unas {horas} h en vaciarse; la estadística de salud alarga ese margen.`
  - Manual, aventura: `Al volver gana **+{sim.XP_AVENTURA} XP**.` (en vez de «Si vuelve con vida gana … ; si muere por el desgaste, no.»)
  - Manual, «El plantel»: `…donde no les pasa el tiempo: ni comida, ni ánimo, ni aseo.` (se quita «así que no se te mueren mientras juegas con otro»)
  - Manual, gemas: `**{n}** son de cada gachamon ({g} 💎); los otros **{m}** son tuyos ({h} 💎).` (se quita «y se van con él» y «y se quedan»)
  - Panel de `/logros`: `-# Las de arriba son de tu gachamon y las otras son tuyas. Las gemas van a tu monedero en los dos casos.`
  - Logro «Superviviente»: `100 aventuras`.
  - `/cementerio` vacío: `-# Aquí no descansa nadie.`

## Review Focus

1. **Un gachamon al que ya le tocaba morir cuando llega el cambio** (su `muere_en` guardado está en el pasado y el bot no lo había procesado): sigue vivo, con la comida en 0, y su fila queda sin `muere_en`. → Task 6.
2. **Días en 0 y después come**: la barra sube desde 0 como siempre (+30), sin deuda acumulada ni fecha rara. → Task 1.
3. **Un panel viejo de Discord de un gachamon que murió antes del cambio**: pulsar sus botones sigue enseñando la lápida y no rompe nada. → Task 3.
4. **Una cuenta web con una muerte de antes del cambio que nunca vio**: el estado ya no trae `difunto`; entra a su relevo o al huevo sin pantalla rota, y nadie llama a `difunto/visto`. → Task 4.
5. **Filas pendientes en `muertes_por_anunciar` al arrancar con el código nuevo**: la tabla se va sin anunciar nada y arrancar dos veces no falla. → Task 6.

**Sobre las pruebas de este plan.** Los nombres de ayuda (`criatura(...)`, `base`, `U`, `G`, `T0`, `cliente`, `con_gachamon`…) son los de las pruebas vecinas de cada archivo. Lo que manda son los nombres de las pruebas nuevas y sus aserciones, con sus valores.

---

### Task 1: El tiempo y los viajes ya no matan

**Files:**
- Modify: `simulacion.py` (`avanzar`, su docstring), `aventura.py` (`aplicar_desgaste`, `aplicar_viaje`)
- Test: `tests/test_simulacion.py`, `tests/test_identidad.py`, las de aventura que prueben el desgaste, y **toda prueba de la suite que falle porque esperaba una muerte por tiempo o por viaje** (regla de las pruebas)

**Interfaces:**
- Produces:
  - `sim.avanzar(criatura, ahora, ritmo=RITMO_BAJO_TECHO) -> Criatura`: nunca pone `muerta_en` ni `causa_muerte`. Si la comida llega a 0, devuelve `hambre == 0.0` y `viva`. Ya no pregunta a `identidad`. Sigue sin avanzar a quien no es la activa (eso es del plan 2) y a quien ya está muerta.
  - `av.aplicar_desgaste(...) -> Criatura`: nunca mata. `av.aplicar_viaje(...)`: siempre emite las pruebas y da la XP.
  - `sim.momento_de_muerte`, `sim.momento_de_aviso`, `sim.UMBRAL_AVISO_HAMBRE` e `identidad.sin_aviso_de_hambre` **siguen existiendo** en esta tarea: los quita la Task 6, cuando ya nadie los use.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_simulacion.py`:

```python
def test_con_la_comida_en_cero_sigue_viva():
    c = sim.avanzar(criatura(hambre=5.0), T0 + timedelta(hours=200))
    assert (c.hambre, c.viva, c.muerta_en, c.causa_muerte) == (0.0, True, None, None)

def test_tras_dias_en_cero_come_y_sube_desde_cero():
    despues = T0 + timedelta(days=5)
    c = sim.avanzar(criatura(hambre=5.0), despues)
    comida = sim.aplicar_accion(c, sim.ALIMENTAR, despues).criatura
    assert comida.hambre == 30.0 and comida.viva

def test_no_muere_sea_de_quien_sea():
    for usuario in ("123456789012345678", "-12"):
        c = sim.avanzar(criatura(usuario_id=usuario, hambre=1.0), T0 + timedelta(days=30))
        assert c.viva and c.hambre == 0.0
```

En las pruebas de aventura: `test_un_viaje_no_mata` (con `hambre=3.0`, `aplicar_desgaste` deja `hambre == 0.0` y `viva`) y `test_un_viaje_que_deja_en_cero_da_igual_su_xp` (`aplicar_viaje` devuelve una criatura viva con la XP del viaje sumada).

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_simulacion.py -q -k "cero or sea_de_quien"`
Expected: FAIL (hoy `viva` es `False` para el id de Discord).

- [ ] **Step 3: Implementar**

`avanzar`: el final queda en una sola salida (`hambre` ya viene acotada a 0 o al suelo del ritmo). Reescribe el docstring: ya no hay excepción de nadie. `aplicar_desgaste`: sin `muere`. `aplicar_viaje`: sin la rama de «no vuelve con vida».

- [ ] **Step 4: Poner la suite en verde**

Run: `./venv/bin/python -m pytest -q`
Expected: fallan las pruebas que esperaban una muerte. Aplícales la regla de las pruebas, **sin tocar todavía el código que cubrían** (el bucle del bot, `economia`, la web y `db` son de las tareas 2 a 6: si una prueba de esas capas sólo puede pasar con una muerte por tiempo, se borra ahora y su código se quita en su tarea). Termina con la suite entera en verde.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "feat(reglas): el tiempo y los viajes ya no matan: con la comida en 0 se sigue vivo"
```

---

### Task 2: El bot deja de matar, avisar y anunciar

**Files:**
- Modify: `cogs/mascota.py` (el bucle, `/huevo`, `/mascota`), `config.py` sólo si el nombre de la constante deja de tener sentido
- Test: las pruebas de `cogs/mascota.py` que haya (búscalas con `git grep -n "revisar_muertes\|_avisar_hambrientas\|_anunciar_muerte" tests/`)

**Interfaces:**
- Consumes: la Task 1 (nadie muere al avanzar).
- Produces: en `cogs/mascota.py` el bucle pasa a llamarse `mantenimiento` y hace **sólo** `db.limpiar_uso_ia(ahora)`, con el mismo intervalo. Desaparecen `_anunciar_muerte`, `_avisar_hambrientas` y `_canal_de`. `/huevo` y `/mascota` ya no guardan una muerte ni ascienden a nadie: `/huevo` mira el plantel y contesta como hoy.

- [ ] **Step 1: Escribir la prueba que falla**

`test_el_mantenimiento_solo_limpia_el_uso_de_la_ia`: con una criatura cuya comida está en 0 hace días y un `canal` de mentira, correr el cuerpo del bucle no envía ningún mensaje, no cambia la fila de la criatura y sí llama a `db.limpiar_uso_ia`. Y `test_el_cog_ya_no_tiene_bucle_de_muertes`: `Mascota` no tiene los atributos `revisar_muertes`, `_anunciar_muerte` ni `_avisar_hambrientas`.

- [ ] **Step 2: Correrla y ver que falla**

Run: `./venv/bin/python -m pytest tests -q -k "mantenimiento or bucle_de_muertes"`
Expected: FAIL.

- [ ] **Step 3: Implementar.** Quita también los `import` que queden sin uso.

- [ ] **Step 4: Correr la suite**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "feat(bot): sin bucle de muertes ni aviso de hambre; el mantenimiento sólo limpia el uso de la IA"
```

---

### Task 3: Las reglas y los cogs dejan de preguntar si se murió

**Files:**
- Modify: `economia.py` (`ejecutar_viaje`, `ejecutar_cuidado`, `aprender_hablando`, `ejecutar_entrenamiento_conjunto`, la competencia, `cambiar_de_activo`, `_usar`), `nacer.py`, `cogs/charla.py`, `cogs/competencias.py`, `cogs/aventura.py`, `vistas.py`
- Test: `tests/test_economia_*.py`, `tests/test_cambiar_de_activo.py`, `tests/test_usar_objeto.py`, `tests/test_vistas.py`

**Interfaces:**
- Consumes: Task 1.
- Produces: en esas funciones desaparece la rama «al ponerla al día resultó muerta» (y con ella: el `ok=False` «Tu gachamon ya no está entre nosotros.» del cuidado, el `problema="activo_muerto"` del entrenamiento conjunto, «Un gachamon ha muerto antes de competir.», el `motivo="sin_gachamon"` del uso por muerte, y la llamada a `db._apuntar_muerte` de `cambiar_de_activo`). En los cogs se van los mensajes que sólo salían por esas ramas: «ya no puede contestarte. 🪦», «El gachamon de {quien} ha muerto.», «💀 … no sobrevivió al viaje.». Las firmas y los demás resultados no cambian.
- **Se queda** todo lo que responde a una criatura que **ya estaba** muerta en la base: `economia.mudar_gachamon` («Ya no está entre nosotros.» para un id de un muerto), `sim` rechazando cuidar a una muerta, y en `vistas.py` el panel de un muerto, que sigue pintando la lápida y sin botones.

- [ ] **Step 1: Escribir las pruebas que fallan**

- `tests/test_economia_cuidado.py`, `test_con_la_comida_en_cero_el_cuidado_se_aplica`: una activa con `hambre=0.0` desde hace 3 días; `ejecutar_cuidado(..., sim.ALIMENTAR, ...)` devuelve `ok` verdadero y la deja con `hambre == 30.0`.
- `tests/test_vistas.py`, `test_el_panel_de_un_muerto_de_antes_sigue_ensenando_la_lapida`: una criatura con `muerta_en` puesto a mano; lo que arma la ficha no trae botones y trae la lápida (como comprueban hoy las pruebas vecinas de la ficha muerta).
- `tests/test_cambiar_de_activo.py`, `test_cambiar_con_la_saliente_en_cero_no_apunta_nada`: la saliente con `hambre=0.0` hace días; el cambio es `ok`, la saliente sigue viva.

- [ ] **Step 2: Correrlas y ver que fallan o pasan por el motivo equivocado.** Las dos primeras pueden pasar ya tras la Task 1: entonces son pruebas de regresión y vale; la que debe fallar antes de implementar es una nueva por cada rama que quitas, que afirme que el resultado ya no tiene ese problema (por ejemplo, que `ResultadoEntrenamientoConjunto` no devuelve nunca `problema == "activo_muerto"` con el activo en 0).

- [ ] **Step 3: Implementar.** Borra las ramas y los textos; no dejes campos de resultado que ya nadie rellena si eran sólo de la muerte (mira quién los lee antes de quitarlos).

- [ ] **Step 4: Correr la suite**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "refactor(reglas): fuera las ramas de «se murió al ponerla al día» en cuidar, hablar, entrenar, competir, usar y cambiar de activo"
```

---

### Task 4: La web sin la pantalla del difunto

**Files:**
- Modify: `web/estado.py`, `web/juego.py`, `web/cuenta.py` (docstring de `la_misma_activa`), `web/static/js/pantallas.js`, `web/static/js/principal.js`, `web/static/js/entrada.js`, `web/static/estilo.css`, `db.py` (`difunto_pendiente`, `marcar_difuntos_vistos`, lo que `canjear_codigo_de_vinculo` escribe en `difuntos_vistos_hasta`)
- Test: `tests/test_web_estado.py`, `tests/test_web_cliente.py`, `tests/js/pantallas.test.mjs`, `tests/js/entrada.test.mjs`, `tests/test_db.py`

**Interfaces:**
- Produces:
  - El estado (`web.estado.armar`) ya no trae la clave `difunto`. No existe `POST /gachamon/api/difunto/visto`.
  - `pantallas.siguiente` ya no devuelve `'difunto'`; `PANTALLAS` no tiene esa fila; `entrada.js` no exporta la pantalla del difunto; se van las reglas `.lapida` de `estilo.css` si nadie más las usa.
  - `db.difunto_pendiente` y `db.marcar_difuntos_vistos` desaparecen. La columna `cuentas_web.difuntos_vistos_hasta` se queda en el esquema sin que nadie la lea ni la escriba.
  - `desfallecido` sigue igual: verdadero para cualquier gachamon vivo con la comida en 0.

- [ ] **Step 1: Escribir las pruebas que fallan**

- `tests/test_web_estado.py`: `test_el_estado_ya_no_habla_de_difuntos` (una cuenta con un gachamon muerto de antes —`muerta_en` puesto a mano— y otro vivo: `"difunto" not in estado` y `estado["gachamon"]` es el vivo); `test_una_muerte_de_antes_sin_ver_no_rompe_nada` (sólo el muerto: `estado["gachamon"] is None`, sin `difunto`); `test_difunto_visto_ya_no_existe` (`POST difunto/visto` → 404); `test_cualquiera_con_la_comida_en_cero_esta_desfallecido` (una vinculada, id de Discord, con `hambre=0.0`: `estado["gachamon"]["desfallecido"] is True`).
- `tests/js/pantallas.test.mjs`: con `estado.difunto` presente (un servidor viejo), `siguiente(...)` **no** devuelve `'difunto'`: sigue con el huevo, el bautizo o el lugar.
- `tests/test_web_cliente.py`: `test_el_cliente_ya_no_tiene_difunto`: ni `pantallas.js`, ni `principal.js`, ni `entrada.js` contienen `difunto`.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_estado.py tests/test_web_cliente.py tests/test_web_js.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar.** En `pantallas.js`, actualiza el comentario de cabecera (ya no hay «muerte pendiente»).

- [ ] **Step 4: Correr la suite**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "feat(web): sin pantalla del difunto: el estado ya no la trae y el cliente no la conoce"
```

---

### Task 5: Los logros, el manual y las frases

**Files:**
- Modify: `logros.py` (`SIGUE_VIVA`, «Superviviente», `cumplidos`, docstrings), `cogs/social.py` (panel de `/logros`, `paginas_de_ayuda`, `/cementerio` vacío), `simulacion.py` (docstring de `horas_de_vida`: es lo que tarda en vaciarse la comida)
- Test: `tests/test_logros.py` (o donde estén), `tests/test_economia_logros.py`, `tests/test_carga.py`

**Interfaces:**
- Produces: `logros.SIGUE_VIVA` desaparece; `logros.hechos_de` no lo incluye; `logros.cumplidos` no tiene caso especial; «Superviviente» es `Logro("superviviente", "Superviviente", "100 aventuras", AVENTURAS, 100, 30)`. Las frases de Discord quedan como dice «Frases nuevas» en las restricciones, letra por letra.

- [ ] **Step 1: Escribir las pruebas que fallan**

- `test_superviviente_son_cien_aventuras`: con `{AVENTURAS: 100}` y nada más, `cumplidos(hechos, GACHAMON)` incluye `superviviente`; y `lgr.POR_CLAVE["superviviente"].descripcion == "100 aventuras"` (usa el nombre real del campo).
- `tests/test_carga.py`: el manual contiene `no se muere` y `Al volver gana`, y **no** contiene `se muere**`, `si muere por el desgaste` ni `se te mueren`; ninguna página pasa de 2000 caracteres (la prueba que ya lo vigila sigue pasando).
- `test_el_panel_de_logros_no_habla_de_morir`: el texto de `/logros` contiene «Las de arriba son de tu gachamon y las otras son tuyas.» y no contiene «si se muere».

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_carga.py tests -q -k "superviviente or manual or logros"`
Expected: FAIL.

- [ ] **Step 3: Implementar.**

- [ ] **Step 4: Correr la suite**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "feat(logros): Superviviente son 100 aventuras, y el manual y el panel dejan de hablar de morir"
```

---

### Task 6: La base sin relojes de muerte

**Files:**
- Modify: `db.py` (`_lleva_relojes`, `_a_valores`, el esquema y `inicializar`/las migraciones, `_activar_en`, `activa_al_dia`, `acariciar`, `_apuntar_muerte`, `muertes_por_anunciar`, `muerte_anunciada`, `pendientes_de_morir`, `pendientes_de_aviso`, el docstring del módulo), `simulacion.py` (`momento_de_muerte`, `momento_de_aviso`, `UMBRAL_AVISO_HAMBRE`, el campo `avisada` sólo si no arrastra una migración), `identidad.py` (`sin_aviso_de_hambre` y el docstring), `nacer.py` (comentarios de «por si se murió»)
- Test: `tests/test_db.py`, `tests/test_identidad.py`, `tests/test_muertes_por_anunciar.py` (se borra entero), `tests/test_caricia.py`

**Interfaces:**
- Consumes: las tareas 1 a 5 (ya nadie llama a lo que aquí se quita: compruébalo con `git grep` antes de borrar cada cosa).
- Produces:
  - Ninguna fila guarda `muere_en` ni `avisa_en`: `_a_valores` los escribe siempre a `None`, y `avisada` a 0. `inicializar` deja a `NULL`/0 los que hubiera (`UPDATE criaturas SET muere_en = NULL, avisa_en = NULL, avisada = 0 WHERE muere_en IS NOT NULL OR avisa_en IS NOT NULL OR avisada != 0`), quita los índices `idx_muere` e `idx_avisa` y hace `DROP TABLE IF EXISTS muertes_por_anunciar`. Las columnas se quedan en el esquema.
  - Desaparecen `db.pendientes_de_morir`, `db.pendientes_de_aviso`, `db._apuntar_muerte`, `db.muertes_por_anunciar`, `db.muerte_anunciada`, `db._lleva_relojes`, `sim.momento_de_muerte`, `sim.momento_de_aviso`, `sim.UMBRAL_AVISO_HAMBRE` e `identidad.sin_aviso_de_hambre`.
  - `db.activa_al_dia(usuario_id, guild_id, ahora) -> Criatura | None`: la activa avanzada hasta `ahora`, sin guardar. **No escribe nunca**, salvo el remiendo de siempre: si no hay activa y sí plantel, asciende a una (`ascender_de_la_incubadora`) y la devuelve.
  - `db.acariciar` sin rama de muerte.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_db.py`:

```python
def test_a_quien_le_tocaba_morir_sigue_vivo_y_sin_reloj(base):
    c = crear_activa(hambre=2.0)                       # ayuda del archivo
    poner_en_la_fila(c.id, muere_en=(T0 - timedelta(days=1)).isoformat())
    db.inicializar()
    fila = leer_fila(c.id)
    assert fila["muere_en"] is None and fila["avisa_en"] is None and fila["muerta_en"] is None
    al_dia = db.activa_al_dia(U, G, T0 + timedelta(days=3))
    assert al_dia.viva and al_dia.hambre == 0.0

def test_guardar_no_escribe_relojes(base):
    c = crear_activa(hambre=80.0)
    db.guardar(c)
    fila = leer_fila(c.id)
    assert (fila["muere_en"], fila["avisa_en"], fila["avisada"]) == (None, None, 0)

def test_la_tabla_de_muertes_por_anunciar_se_va_y_arrancar_dos_veces_no_falla(base):
    crear_la_tabla_vieja_con_una_fila()               # CREATE TABLE muertes_por_anunciar ... + INSERT
    db.inicializar(); db.inicializar()
    assert "muertes_por_anunciar" not in tablas()

def test_activa_al_dia_no_escribe(base):
    c = crear_activa(hambre=0.0)
    antes = volcado()                                  # todas las filas de criaturas
    db.activa_al_dia(U, G, T0 + timedelta(days=10))
    assert volcado() == antes
```

En `tests/test_identidad.py`: `test_ya_no_hay_excepcion_del_hambre` (`not hasattr(identidad, "sin_aviso_de_hambre")`); las pruebas de `sin_plazo_de_refugio` se quedan.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_db.py tests/test_identidad.py -q -k "reloj or relojes or anunciar or no_escribe or excepcion"`
Expected: FAIL.

- [ ] **Step 3: Implementar.** Reescribe el docstring de `db.py` y el de `identidad.py`: ya no hay instante de muerte ni excepción.

- [ ] **Step 4: Correr la suite**

Run: `./venv/bin/python -m pytest -q`
Expected: PASS. Además: `git grep -n "muere_en\|avisa_en\|sin_aviso_de_hambre\|momento_de_muerte\|pendientes_de" -- '*.py' ':!tests'` sólo enseña el esquema, la limpieza de `inicializar` y `CAMPOS`.

- [ ] **Step 5: Commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "refactor(db): sin relojes de muerte ni tabla de muertes por anunciar; la activa al día no escribe"
```

---

### Task 7: Los documentos

**Files:**
- Modify: `AGENTS.md`, `README.md`, `docs/superpowers/specs/2026-11-14-gachamon-rework-1-departamento-design.md` (sólo el corte de la sección 10)

- [ ] **Step 1: `AGENTS.md`**, en «Invariantes del dominio»:
  - La línea «El gachamon de quien no tiene aviso de hambre no muere de hambre: …» pasa a, tal cual: `- Ningún gachamon muere: con la comida en 0 se queda en 0 y sigue vivo, y no se guarda instante de muerte ni de aviso. Los que murieron antes siguen en el cementerio.`
  - Se quitan «Esa excepción se pregunta siempre con `identidad.sin_aviso_de_hambre`, nunca mirando el id.» y «La web nunca habla en Discord: la muerte que registra queda apuntada en `muertes_por_anunciar` y la anuncia el bucle del bot en su siguiente vuelta.».
  - «La comodidad frena el ánimo y no toca el hambre, que lleva su instante de muerte precalculado.» pasa a `- La comodidad frena el ánimo y no toca el hambre.`
  - «Casi todos los logros son de la criatura y se pierden con ella.» pasa a `- Casi todos los logros son de la criatura.`
  - Nada más: lo del refugio, la incubadora y las casas es de los planes que siguen.

- [ ] **Step 2: `README.md`**: donde diga que un gachamon se muere de hambre o que el bot avisa o anuncia, que diga lo de ahora (léelo entero buscando «muer», «hambre», «aviso»); la mención al cementerio se queda como el lugar de los de antes.

- [ ] **Step 3: El diseño**, sección 10: el corte sugerido pasa a seis planes, con «(1) nadie muere; (2) el tiempo para todos» en vez de «(1) el tiempo para todos y el fin de la muerte», y los demás corridos un número.

- [ ] **Step 4: Comprobar y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "docs: nadie muere, en la política, el README y el corte del diseño"
```

Después de la Task 7 el controlador lanza la revisión final de la rama (sólo los commits de este plan), recorre con el arnés una cuenta con la comida en 0 (web a 390 y 1280 px) y le presenta el resultado a Felipe. No se fusiona, sube ni despliega: el plan 2 sigue en la misma rama.
