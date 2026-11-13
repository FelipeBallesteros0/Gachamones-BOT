# Gachamon web · Plan 3 de 4 — El pueblo

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que quien juega en `rowino.online/gachamon` deje de estar en una sola pantalla y recorra un pueblo: toca un lugar, su avatar camina hasta ahí con el gachamon detrás a saltitos, entra, y el gachamon dice algo de ese lugar — con todo el arte nuevo en archivos que el dibujante puede reemplazar sin tocar código.

**Architecture:** El pueblo es un archivo de datos (`pueblo.json`: lugares, nodos y caminos) que leen el servidor y el cliente. El servidor sólo guarda **en qué lugar estás** y arma el estado con ese lugar y sus frases; la caminata es del cliente y no se guarda a medias. El cliente gana un módulo puro con la lógica del pueblo (ruta, caminata, seguidor, cámara), una pantalla de mapa sobre un `<canvas>`, y un cargador de arte que saca cada dibujo de un archivo descrito en el contrato de arte.

**Tech Stack:** Lo del plan 2, sin dependencias nuevas: Python 3.12 y 3.14, FastAPI 0.162.5, SQLite síncrono, Pillow 12.3.0 (para generar los rellenos), pytest 9.1.1; JavaScript del navegador en módulos, probado con `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-12-gachamon-web-parte-a-design.md` — secciones 5.3, 5.4, 5.7 (globos «algo del lugar») y 5.9. El boceto que Felipe eligió es el **B** de `docs/superpowers/specs/2026-11-12-bocetos/mapa.js`: de ahí salen las coordenadas, la velocidad y la forma de caminar. También `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`. Quien ejecute lee los tres.

**Los cuatro planes de la parte A:**

1. **Reglas y bot** — hecho y desplegado.
2. **Entrar y cuidar** — hecho y desplegado (2026-11-13).
3. **El pueblo** — este.
4. **Los lugares y la apertura** — incubadora, tienda, mochila, ropero, casa con huerto y muebles, refugio, hablar, la ficha desplegable; el enlace en Rowino, que su inicio de sesión vuelva a Gachamon, y el aviso en el canal.

## Lo que este plan decide y Felipe tiene que mirar

Son propuestas mías donde el diseño deja la decisión a quien construye. Si alguna no te gusta, se cambia antes de ejecutar.

- **Qué hay dentro de cada lugar al terminar este plan.** En los nueve se entra y se ve la escena con tu avatar y tu gachamon, y los cuatro cuidados y la caricia funcionan en todos. **Tu casa** y **Refugio** quedan abiertos (son tu hogar). **Incubadora** y **Tienda** avisan «Aquí todavía no hay nada que hacer. Abre pronto.» (sus acciones son del plan 4). Los cinco de la parte B avisan «Esto se abre más adelante.», y a quien tiene Discord vinculado, además, «Por ahora se juega en Discord.». En **Tu casa** sin casa propia: «Todavía no tienes casa. Se compran en la tienda.»
- **El avatar pasa a dibujarse con archivos, por capas** (cuerpo según la piel, ropa, pelo según peinado y color; quieto y dos cuadros caminando). Hoy lo dibuja el código. Consecuencia visible: **el género deja de cambiar el dibujo** (el diseño dice que el género es para que los textos concuerden); el monigote de relleno se verá parecido al de hoy.
- **El contrato de arte** lista todas las familias de piezas, pero en este plan sólo se entregan los rellenos de las que este plan usa: el fondo del pueblo, los nueve lugares, las nueve escenas, el avatar y tres efectos (136 archivos). Los íconos de objetos, cosméticos y muebles llegan con las pantallas del plan 4.
- **El computador** deja de mover la cámara a partir de **900 píxeles** de ancho, el mismo corte que ya usa la pantalla de un lugar.
- **La caminata no se guarda a medias.** Si recargas la página en mitad del camino, apareces en el último lugar al que llegaste.
- **No se ven gachamones ni personas de adorno en el pueblo.** El boceto los tenía; se quitan porque todavía no hay nadie más ahí (eso es el proyecto 3) y nada debe sugerir que sí.
- **Con «reducir movimiento» activado en el teléfono**, tocar un lugar te lleva de inmediato, sin caminata.

## Global Constraints

- Todo lo de `AGENTS.md` y todas las restricciones globales del plan 2 siguen mandando. Las que más pesan aquí:
  - `web/` no importa `discord`, ni directa ni indirectamente.
  - El servicio no guarda estado del juego en memoria.
  - Quién eres sale sólo de la cookie de Rowino; ninguna ruta acepta un id de persona.
  - Toda ruta que cambia algo es `POST` o `PUT` y exige `X-Gachamon: 1`. Las rutas se declaran con `def`.
  - Un error se contesta siempre como `{"detail": {"clave": "<clave>", "mensaje": "<frase>"}}`.
  - Toda mutación va bajo `BEGIN IMMEDIATE` y dentro de `db.py` o `economia.py`. `db.py` no importa nada de `web/`.
  - El reloj es `db.ahora_utc()`; en las pruebas, el tiempo y el azar se inyectan y la base es temporal.
- **El cliente no usa frameworks ni compilación, nunca mete texto con `innerHTML`, y no contiene `http://` ni `https://`.** Los módulos se importan con rutas relativas terminadas en `.js`.
- **Ninguna dependencia nueva**, ni de Python ni de JavaScript.
- **El pueblo vive en datos.** Qué lugares hay, sus nombres, sus coordenadas y sus caminos están en `web/static/datos/pueblo.json` y en ningún otro sitio. El código no lleva coordenadas ni recorre una lista propia de lugares. Sólo nombra un lugar por su clave donde le da un significado —el hogar del que se parte, las frases de cada lugar—, y una prueba vigila que esas claves existan en el archivo. La lógica del mapa en el cliente (`pueblo.js`, `mapa.js`) no nombra ninguno.
- **Las reglas son del servidor.** El cliente decide por dónde se camina; el servidor decide en qué lugar estás, qué se puede hacer ahí y qué dice el gachamon.
- **Arte:** cada dibujo nuevo es un archivo bajo `web/static/arte/` descrito en el contrato (`web/arte.py`). El relleno **se nota**. Si un archivo falta al cargar, se ve un recuadro genérico con el nombre de esa pieza, **nunca** el dibujo de otra; la falta queda en el registro del servidor como el 404 de ese archivo, y `tests/test_arte.py` la hace fallar antes de desplegar. Las direcciones del arte se arman a partir de la del propio módulo (`import.meta.url`), para que lleven la versión de los estáticos.
- **Un globo no anuncia nada que no esté pasando.** Las frases de un lugar no dicen que haya otras personas ni otros gachamones, ni prometen lo que ese lugar todavía no hace.
- Texto de jugador: castellano, de tú; «monedas» y «gemas»; las frases que hablan del gachamon llevan las marcas de `especies.concordar`.
- El análisis de impacto de GitNexus lo corre el controlador antes de cada tarea que toque un símbolo existente; el índice se refresca sólo con `node .gitnexus/run.cjs analyze --index-only`.
- Antes de cada commit: `./venv/bin/python -m pre_commit run --all-files && git diff --check`, encadenados con `&&` al commit y **sin tuberías**.
- **Nada de push, merge ni despliegue sin autorización explícita de Felipe.**
- Rama de trabajo: `web/3-el-pueblo`, desde `main`. Un commit por tarea.

## Review Focus

1. **Tocar mientras se camina:** otro lugar a mitad de camino, el mismo lugar dos veces, el lugar donde ya estás, y muchos toques seguidos. Nunca queda el avatar fuera de un camino ni la pantalla esperando para siempre. → Tareas 6 y 7.
2. **La pantalla cambia de tamaño en plena caminata** (se gira el teléfono, se cruza el corte de 900 px). El mapa se reencuadra y la caminata sigue. → Tareas 6 y 7.
3. **El lugar guardado ya no existe** porque el pueblo se redibujó. Apareces en tu hogar y nada falla. → Tarea 2.
4. **Falta un archivo de arte al cargar.** Se ve el recuadro de esa pieza, el mapa sigue funcionando y se puede llegar a todos los lugares. → Tareas 5 y 7.
5. **La red falla justo al llegar.** No quedas atrapado en el mapa: se dice con una frase y se puede volver a intentar o volver al lugar anterior. → Tarea 7.

---

### Task 1: Los datos del pueblo

**Files:**
- Create: `web/static/datos/pueblo.json`
- Create: `web/pueblo.py`
- Test: `tests/test_pueblo.py`

**Interfaces:**
- Produces, en `web/static/datos/pueblo.json`, exactamente esto (son las coordenadas del boceto B; `portal` pasa a llamarse `aventura`):

  ```json
  {
    "ancho": 690,
    "alto": 430,
    "velocidad": 115,
    "hueco": 26,
    "lugares": {
      "casa": {"nombre": "Tu casa", "parte": "A", "abre": "ya"},
      "refugio": {"nombre": "Refugio", "parte": "A", "abre": "ya"},
      "incubadora": {"nombre": "Incubadora", "parte": "A", "abre": "pronto"},
      "tienda": {"nombre": "Tienda", "parte": "A", "abre": "pronto"},
      "plaza": {"nombre": "Plaza", "parte": "B", "abre": "despues"},
      "barrio": {"nombre": "Barrio", "parte": "B", "abre": "despues"},
      "estadio": {"nombre": "Estadio", "parte": "B", "abre": "despues"},
      "cementerio": {"nombre": "Cementerio", "parte": "B", "abre": "despues"},
      "aventura": {"nombre": "Aventura", "parte": "B", "abre": "despues"}
    },
    "nodos": {
      "incubadora": [75, 170], "u1": [165, 170], "tienda": [220, 170], "ptop": [300, 170],
      "estadio": [390, 170], "u3": [485, 170], "cementerio": [545, 170], "aventura": [640, 170],
      "afuera": [640, 62],
      "borde": [30, 330], "casa": [75, 330], "l1": [165, 330], "l2": [300, 330],
      "barrio": [395, 330], "l3": [485, 330], "refugio": [575, 330],
      "plaza": [300, 250]
    },
    "aristas": [
      ["incubadora", "u1"], ["u1", "tienda"], ["tienda", "ptop"], ["ptop", "estadio"],
      ["estadio", "u3"], ["u3", "cementerio"], ["cementerio", "aventura"], ["aventura", "afuera"],
      ["borde", "casa"], ["casa", "l1"], ["l1", "l2"], ["l2", "barrio"], ["barrio", "l3"], ["l3", "refugio"],
      ["u1", "l1"], ["ptop", "plaza"], ["plaza", "l2"], ["u3", "l3"]
    ]
  }
  ```
  Cada lugar se para en el nodo que lleva su misma clave. `velocidad` va en unidades del pueblo por segundo; `hueco` es lo que el gachamon va detrás.
- Produces, en `web/pueblo.py` (sin `discord`, sin `db`):
  - `RUTA: Path` — el archivo de datos. `DATOS: dict` — su contenido, leído una vez al importar.
  - `class Lugar` — dataclass congelada: `clave: str`, `nombre: str`, `parte: str`, `abre: str`.
  - `LUGARES: dict[str, Lugar]` — en el orden del archivo.
  - `YA = "ya"`, `PRONTO = "pronto"`, `DESPUES = "despues"`.
  - `existe(clave: object) -> bool` — cierto sólo para una cadena que es clave de `LUGARES`.
  - `de_partida(hogar: str) -> str` — `"casa"` si `hogar == casas.PROPIA`; si no, `"refugio"`.
  - `aviso(clave: str, vinculada: bool, hogar: str) -> str | None` — lo que la pantalla del lugar tiene que avisar, o `None`:

    | Caso | Frase |
    |---|---|
    | `abre == "despues"` y vinculada | «Esto se abre más adelante. Por ahora se juega en Discord.» |
    | `abre == "despues"` y no vinculada | «Esto se abre más adelante.» |
    | `abre == "pronto"` | «Aquí todavía no hay nada que hacer. Abre pronto.» |
    | `clave == "casa"` y `hogar != casas.PROPIA` | «Todavía no tienes casa. Se compran en la tienda.» |
    | lo demás | `None` |
  - `problemas(datos: dict) -> list[str]` — lo que está mal en unos datos de pueblo, en frases; lista vacía si todo está bien. Detecta: una arista que nombra un nodo que no existe; un lugar sin nodo de su clave; una coordenada fuera de `0..ancho` × `0..alto`; un lugar al que no se puede llegar desde otro por los caminos; un `abre` o una `parte` que no es de los valores de arriba; `velocidad` o `hueco` que no son números positivos.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_pueblo.py`:

```python
import copy
import json

import pytest

import casas
from web import pueblo

NUEVE = ("casa", "refugio", "incubadora", "tienda", "plaza", "barrio", "estadio", "cementerio", "aventura")


def test_el_archivo_es_el_del_boceto_y_no_tiene_problemas():
    datos = json.loads(pueblo.RUTA.read_text(encoding="utf-8"))
    assert datos == pueblo.DATOS
    assert (datos["ancho"], datos["alto"], datos["velocidad"], datos["hueco"]) == (690, 430, 115, 26)
    assert pueblo.problemas(datos) == []


def test_son_los_nueve_lugares_en_su_orden_con_su_parte():
    assert tuple(pueblo.LUGARES) == NUEVE
    assert [l.parte for l in pueblo.LUGARES.values()] == ["A"] * 4 + ["B"] * 5
    assert pueblo.LUGARES["casa"] == pueblo.Lugar("casa", "Tu casa", "A", pueblo.YA)
    assert pueblo.LUGARES["tienda"].abre == pueblo.PRONTO
    assert all(pueblo.LUGARES[c].abre == pueblo.DESPUES for c in NUEVE[4:])
    assert pueblo.DATOS["nodos"]["casa"] == [75, 330] and pueblo.DATOS["nodos"]["aventura"] == [640, 170]


@pytest.mark.parametrize("clave, vale", [
    ("plaza", True), ("portal", False), ("u1", False), ("", False), (None, False), (7, False), (["casa"], False),
])
def test_existe_solo_para_un_lugar_de_verdad(clave, vale):
    assert pueblo.existe(clave) is vale


def test_se_parte_del_hogar():
    assert pueblo.de_partida(casas.PROPIA) == "casa"
    assert pueblo.de_partida(casas.REFUGIO) == "refugio"
    assert pueblo.de_partida(casas.INTEMPERIE) == "refugio"


@pytest.mark.parametrize("clave, vinculada, hogar, frase", [
    ("estadio", True, casas.PROPIA, "Esto se abre más adelante. Por ahora se juega en Discord."),
    ("estadio", False, casas.PROPIA, "Esto se abre más adelante."),
    ("tienda", True, casas.REFUGIO, "Aquí todavía no hay nada que hacer. Abre pronto."),
    ("casa", False, casas.REFUGIO, "Todavía no tienes casa. Se compran en la tienda."),
    ("casa", False, casas.INTEMPERIE, "Todavía no tienes casa. Se compran en la tienda."),
    ("casa", True, casas.PROPIA, None),
    ("refugio", False, casas.REFUGIO, None),
])
def test_cada_lugar_avisa_lo_suyo(clave, vinculada, hogar, frase):
    assert pueblo.aviso(clave, vinculada, hogar) == frase


def _roto(cambio):
    datos = copy.deepcopy(pueblo.DATOS)
    cambio(datos)
    return pueblo.problemas(datos)


def test_los_datos_rotos_se_notan():
    assert _roto(lambda d: d["aristas"].append(["plaza", "fantasma"]))
    assert _roto(lambda d: d["nodos"].pop("tienda"))
    assert _roto(lambda d: d["nodos"].__setitem__("casa", [700, 330]))
    assert _roto(lambda d: d["nodos"].__setitem__("casa", [75, -1]))
    assert _roto(lambda d: d["lugares"]["plaza"].__setitem__("abre", "nunca"))
    assert _roto(lambda d: d["lugares"]["plaza"].__setitem__("parte", "C"))
    assert _roto(lambda d: d.__setitem__("velocidad", 0))
    assert _roto(lambda d: d.__setitem__("aristas", [a for a in d["aristas"] if "plaza" not in a]))
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_pueblo.py -q`
Expected: FAIL — `ImportError: cannot import name 'pueblo' from 'web'`.

- [ ] **Step 3: Escribir el archivo de datos y `web/pueblo.py`**

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_pueblo.py tests/test_web_app.py -q`
Expected: PASS. (El archivo nuevo entra en la huella de los estáticos; ninguna prueba de `test_web_app.py` depende de su valor.)

- [ ] **Step 5: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(pueblo): los nueve lugares y sus caminos, en datos"
```

---

### Task 2: Dónde estás

El servidor recuerda el último lugar al que llegaste y lo pone en el estado.

**Files:**
- Modify: `db.py` — columna `lugar` en `cuentas_web`, `lugar_de_cuenta`, `poner_lugar`
- Modify: `web/estado.py`, `web/juego.py`
- Modify: `tests/test_web_estado.py` — el conjunto de claves del estado gana `lugar`
- Test: `tests/test_web_lugar.py`, y una prueba de migración en `tests/test_db.py`

**Interfaces:**
- Consumes: `pueblo.existe`, `pueblo.de_partida`, `pueblo.aviso`, `pueblo.LUGARES` (tarea 1); `Jugador`, `jugador_actual`, `con_cabecera`, `problema`; `estado.armar`.
- Produces, en `db.py`:
  - Columna `cuentas_web.lugar TEXT` (puede ser `NULL`), en el `CREATE TABLE` y en `MIGRACIONES_DE_TABLAS`, como se hizo con `difuntos_vistos_hasta`.
  - `lugar_de_cuenta(rowino_uid: int) -> str | None` — lo guardado, o `None` si no hay cuenta o no hay lugar.
  - `poner_lugar(rowino_uid: int, lugar: str) -> None` — bajo `BEGIN IMMEDIATE`. No valida contra el pueblo: `db.py` no sabe de lugares. Sin cuenta, no hace nada.
- Produces, en la web:
  - El estado gana la clave `lugar`:

    ```json
    "lugar": {"clave": "refugio", "nombre": "Refugio", "abre": "ya", "aviso": null}
    ```
    Es el lugar guardado si todavía existe en el pueblo; si no hay ninguno guardado, o ya no existe, el de `pueblo.de_partida(hogar)`. El `aviso` sale de `pueblo.aviso` con el `vinculada` del jugador y el `hogar` del estado. Leer el estado no escribe el lugar.
  - `POST /gachamon/api/lugar` — cuerpo `{"lugar": str}`, revisado a mano como los demás. 200 con el estado nuevo. 422 con clave `lugar` y «Ese lugar no existe.» si falta, no es una cadena o no es un lugar del pueblo.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_web_lugar.py`:

```python
import pytest

import db
from ayudas_web import ESCRIBIR, alta, con_gachamon, entrar, poner_reloj
from web import pueblo

ESTADO, LUGAR = "/gachamon/api/estado", "/gachamon/api/lugar"


def ir(cliente, lugar):
    return cliente.post(LUGAR, json={"lugar": lugar}, headers=ESCRIBIR)


def test_quien_llega_esta_en_su_hogar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    assert cliente.get(ESTADO).json()["lugar"] == {
        "clave": "refugio", "nombre": "Refugio", "abre": "ya", "aviso": None,
    }
    assert db.lugar_de_cuenta(1) is None


def test_llegar_a_un_lugar_lo_guarda_y_devuelve_el_estado(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    respuesta = ir(cliente, "estadio")
    assert respuesta.status_code == 200
    assert respuesta.json()["lugar"] == {
        "clave": "estadio", "nombre": "Estadio", "abre": "despues", "aviso": "Esto se abre más adelante.",
    }
    assert respuesta.json()["gachamon"]["nombre"] == "Pelusa"
    assert cliente.get(ESTADO).json()["lugar"]["clave"] == "estadio"
    assert db.lugar_de_cuenta(1) == "estadio"


@pytest.mark.parametrize("cuerpo", [
    {"lugar": "portal"}, {"lugar": "u1"}, {"lugar": ""}, {"lugar": 7}, {"lugar": ["casa"]}, {}, [], "casa",
])
def test_un_lugar_que_no_existe_no_se_guarda(cliente, monkeypatch, cuerpo):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    respuesta = cliente.post(LUGAR, json=cuerpo, headers=ESCRIBIR)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == {"clave": "lugar", "mensaje": "Ese lugar no existe."}
    assert db.lugar_de_cuenta(1) is None


def test_si_el_lugar_guardado_ya_no_esta_en_el_pueblo_vuelves_a_tu_hogar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    ir(cliente, "plaza")
    sin_plaza = {c: l for c, l in pueblo.LUGARES.items() if c != "plaza"}
    monkeypatch.setattr(pueblo, "LUGARES", sin_plaza)
    assert cliente.get(ESTADO).json()["lugar"]["clave"] == "refugio"


def test_el_lugar_es_de_cada_cuenta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente, 1)
    ir(cliente, "tienda")
    alta(cliente, 2, nombre="Ana")
    assert cliente.get(ESTADO).json()["lugar"]["clave"] == "refugio"
    assert db.lugar_de_cuenta(1) == "tienda" and db.lugar_de_cuenta(2) is None


def test_pide_la_cabecera_la_sesion_y_la_cuenta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    assert ir(cliente, "plaza").status_code == 401
    entrar(cliente, 1)
    respuesta = ir(cliente, "plaza")
    assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "sin_cuenta"
    alta(cliente)
    assert cliente.post(LUGAR, json={"lugar": "plaza"}).status_code == 403


def test_el_cuerpo_no_puede_decir_de_quien_es_el_lugar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente, 1)
    alta(cliente, 2, nombre="Ana")
    cliente.post(LUGAR, headers=ESCRIBIR, json={"lugar": "plaza", "rowino_uid": 1, "usuario_id": "-1"})
    assert db.lugar_de_cuenta(1) is None and db.lugar_de_cuenta(2) == "plaza"
```

En `tests/test_web_estado.py`, la aserción del conjunto de claves del estado pasa a incluir `"lugar"`.

En `tests/test_db.py`, una prueba de que una base creada sin la columna `lugar` la gana al inicializar, con el mismo modelo que la de `difuntos_vistos_hasta`.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_lugar.py -q`
Expected: FAIL — `KeyError: 'lugar'` y 404 en `/gachamon/api/lugar`.

- [ ] **Step 3: Implementar**

Antes: `impact` sobre `MIGRACIONES_DE_TABLAS` y sobre `armar` (lo corre el controlador).

El aviso de un lugar con Discord vinculado usa el `vinculada` del `Jugador`; el `hogar` es el mismo valor que ya va en el estado.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_lugar.py tests/test_web_estado.py tests/test_db.py -q`
Expected: PASS.

- [ ] **Step 5: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): el juego recuerda en qué lugar estás"
```

---

### Task 3: Lo que el gachamon dice de cada lugar

**Files:**
- Modify: `globos.py`
- Modify: `web/estado.py` — pasa el lugar a `globos.de`
- Modify: `AGENTS.md`
- Test: `tests/test_globos.py`, `tests/test_web_lugar.py`

**Interfaces:**
- Consumes: `pueblo.LUGARES` sólo en las pruebas (`globos.py` es puro y no importa `web`).
- Produces, en `globos.py`:
  - `LUGAR = "lugar"` — el tercer tipo de globo.
  - `DEL_LUGAR: dict[str, tuple[str, ...]]` — por clave de lugar, al menos dos frases comunes. Trae los nueve.
  - `PROPIAS_DEL_LUGAR: dict[str, dict[str, tuple[str, ...]]]` — por especie y lugar; lo que una especie tenga ahí manda sobre lo común **para ese lugar**. Trae los nueve del `pollito`, todos con «pío».
  - `de(criatura, lugar: str | None = None) -> tuple[Globo, ...]` — como hoy, y además, si `lugar` es una clave de `DEL_LUGAR`, las frases de ese lugar con tipo `LUGAR`. Orden: necesidad, lugar, suelta. Con un lugar desconocido o `None`, ninguna de tipo `LUGAR`.
- Produces, en la web: `estado["globos"]` incluye las del lugar donde estás.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_globos.py`:

```python
from web import pueblo


def test_hay_frases_para_los_nueve_lugares_y_solo_para_ellos():
    assert set(globos.DEL_LUGAR) == set(pueblo.LUGARES)
    assert all(len(frases) >= 2 for frases in globos.DEL_LUGAR.values())
    assert set(globos.PROPIAS_DEL_LUGAR["pollito"]) == set(pueblo.LUGARES)


def test_al_estar_en_un_lugar_dice_algo_de_ese_lugar():
    c = criatura(hambre=90, animo=90, limpieza=90)
    del_lugar = [g.texto for g in globos.de(c, "tienda") if g.tipo == globos.LUGAR]
    assert set(del_lugar) == set(esp.concordar(f, esp.HEMBRA) for f in globos.DEL_LUGAR["tienda"])
    assert [g for g in globos.de(c) if g.tipo == globos.LUGAR] == []
    assert [g for g in globos.de(c, "portal") if g.tipo == globos.LUGAR] == []


def test_el_orden_es_necesidad_lugar_y_charla():
    tipos = [g.tipo for g in globos.de(criatura(hambre=10), "plaza")]
    orden = [globos.NECESIDAD, globos.LUGAR, globos.SUELTA]
    assert tipos == sorted(tipos, key=orden.index) and set(tipos) == set(orden)


def test_el_piollito_habla_a_su_manera_en_cada_lugar():
    for lugar in pueblo.LUGARES:
        for g in globos.de(criatura(especie="pollito", hambre=90, animo=90, limpieza=90), lugar):
            if g.tipo == globos.LUGAR:
                assert "pío" in g.texto.lower(), g.texto


def test_una_muerta_tampoco_habla_del_lugar():
    assert globos.de(criatura(muerta_en=T0, causa_muerte="hambre"), "plaza") == ()


@pytest.mark.parametrize("lugar", sorted(globos.DEL_LUGAR))
@pytest.mark.parametrize("genero", [esp.MACHO, esp.HEMBRA])
def test_las_frases_de_lugar_llegan_resueltas_y_cortas(lugar, genero):
    for especie in ("pulpo", "pollito"):
        for g in globos.de(criatura(especie=especie, genero=genero), lugar):
            assert "{" not in g.texto and "}" not in g.texto and 0 < len(g.texto) <= 80


@pytest.mark.parametrize("prohibida", ["amigos", "todos", "alguien", "gente", "moneda", "gema", "ventana"])
def test_ninguna_frase_de_lugar_anuncia_lo_que_no_pasa(prohibida):
    todas = [f for frases in globos.DEL_LUGAR.values() for f in frases]
    todas += [f for por_lugar in globos.PROPIAS_DEL_LUGAR.values() for frases in por_lugar.values() for f in frases]
    assert not [f for f in todas if prohibida in f.lower()]
```

En `tests/test_web_lugar.py`:

```python
def test_el_estado_trae_las_frases_del_lugar_donde_estas(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    antes = [g for g in cliente.get(ESTADO).json()["globos"] if g["tipo"] == "lugar"]
    en_la_plaza = [g for g in ir(cliente, "plaza").json()["globos"] if g["tipo"] == "lugar"]
    assert antes and en_la_plaza and {g["texto"] for g in antes} != {g["texto"] for g in en_la_plaza}
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_globos.py -q`
Expected: FAIL — `AttributeError: module 'globos' has no attribute 'DEL_LUGAR'`.

- [ ] **Step 3: Escribir las frases y el cambio de `de`**

Cada frase habla de **ese** lugar tal como es hoy: lo que se ve, a qué huele, qué se guarda ahí. Frases cortas, en primera persona, sin emojis. No dicen que haya otras personas u otros gachamones (todavía no se ven), ni prometen lo que el lugar aún no hace («¡hoy gano yo!» en un estadio cerrado no vale). La palabra «casa» en la frase de `casa` no afirma que el jugador tenga una.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_globos.py tests/test_web_lugar.py tests/test_textos.py -q`
Expected: PASS.

- [ ] **Step 5: Anotar el invariante en `AGENTS.md`**

```markdown
- Las frases de un lugar hablan de ese lugar tal como es hoy: no dicen que haya otras personas ni prometen lo que el lugar todavía no hace.
```

- [ ] **Step 6: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(globos): el gachamon dice algo del lugar donde está"
```

---

### Task 4: El contrato de arte y los rellenos

El documento para el dibujante, la lista que lo vigila, y un relleno para cada pieza.

**Files:**
- Create: `web/arte.py` — el contrato, como datos
- Create: `herramientas/__init__.py` (vacío) y `herramientas/rellenos.py` — genera los rellenos que falten
- Create: `web/static/arte/…` — 136 archivos PNG generados
- Create: `web/static/datos/arte.json` — el contrato, para el cliente
- Create: `docs/arte/contrato.md` — el contrato, para el dibujante
- Test: `tests/test_arte.py`

**Interfaces:**
- Consumes: `pueblo.LUGARES`, `pueblo.DATOS`; `avatar.PIELES`, `avatar.PELOS`, `avatar.COLORES_DE_PELO`, `avatar.ROPAS`.
- Produces, en `web/arte.py` (sin `discord`, sin `db`):
  - `RAIZ: Path` — `web/static/arte`.
  - `POSES = ("quieto", "paso1", "paso2")`.
  - `class Pieza` — dataclass congelada: `ruta: str` (relativa a `RAIZ`, con `/`), `ancho: int`, `alto: int`, `familia: str`.
  - `piezas() -> tuple[Pieza, ...]` — todas, construidas a partir de los catálogos, en este orden y con estos tamaños en píxeles:

    | Familia | Ruta | Tamaño | Cuántas |
    |---|---|---|---|
    | `pueblo` | `pueblo/fondo.png` | 1380 × 860 | 1 |
    | `lugares` | `pueblo/lugares/<lugar>.png` | 160 × 160 | 9 |
    | `escenas` | `escenas/<lugar>.png` | 720 × 480 | 9 |
    | `avatar` | `avatar/cuerpo/<piel>-<pose>.png` | 48 × 84 | 12 |
    | `avatar` | `avatar/ropa/<ropa>-<pose>.png` | 48 × 84 | 12 |
    | `avatar` | `avatar/pelo/<pelo>-<color>-<pose>.png` | 48 × 84 | 90 |
    | `efectos` | `efectos/corazon.png`, `efectos/estrella.png`, `efectos/marca.png` | 32 × 32 | 3 |
  - `como_json() -> dict` — `{"piezas": [{"ruta", "ancho", "alto", "familia"}, …]}`.
- Produces, en `herramientas/rellenos.py`: `generar(todo: bool = False) -> list[str]` — escribe el relleno de cada pieza del contrato cuyo archivo **no exista** (con `todo=True`, de todas) y devuelve las rutas escritas; además deja `web/static/datos/arte.json` igual a `arte.como_json()`. Se corre con `./venv/bin/python -m herramientas.rellenos` (`--todo` para regenerar).
- Produces: los 136 PNG, todos RGBA, del tamaño exacto del contrato.

Cómo es cada relleno (lo que importa es que **se note** que es relleno y que dos piezas no se confundan):
- **Fondo del pueblo:** pasto liso con los caminos de `pueblo.json` pintados (al doble de escala, porque el fondo mide el doble que el pueblo) y la palabra `RELLENO` repetida en gris tenue.
- **Lugares:** una casita o figura simple de un color distinto por lugar, con fondo transparente; se dibuja apoyada en el borde inferior, que es donde va el nodo.
- **Escenas:** pared y piso lisos, de un tono distinto por lugar, con el nombre del lugar y `RELLENO` en una franja. Sin tildes ni «ñ» en el texto dibujado (la fuente por defecto de Pillow no las trae): pásalo por `retrato._sin_tildes`.
- **Avatar:** el monigote de cuadros de hoy, repartido en capas que se apilan cuerpo → ropa → pelo. Todas miran a la derecha. `paso1` y `paso2` cambian las piernas del cuerpo y, si hace falta, el borde de la ropa; el pelo puede ser igual en las tres poses. Fondo transparente.
- **Efectos:** un corazón, una estrella y una marca de destino, simples.

`docs/arte/contrato.md`, para alguien que dibuja y no programa: qué es cada familia, el nombre exacto de cada archivo, su tamaño, hacia dónde mira, dónde se apoya, qué partes son transparentes, y la regla de oro: **reemplazar un dibujo es guardar el archivo nuevo con el mismo nombre y el mismo tamaño**. Incluye las familias que todavía no tienen archivos (íconos de objetos y cosméticos, muebles, las escenas de cada casa), marcadas como «llegan con el plan 4», y recuerda que los gachamones siguen con su formato de capas de `fuentes/`.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_arte.py`:

```python
import json
from collections import Counter

from PIL import Image

import avatar
from web import arte, pueblo


def test_el_contrato_tiene_las_136_piezas_de_este_plan():
    piezas = arte.piezas()
    assert Counter(p.familia for p in piezas) == {
        "pueblo": 1, "lugares": 9, "escenas": 9, "avatar": 114, "efectos": 3,
    }
    assert len({p.ruta for p in piezas}) == len(piezas)
    rutas = {p.ruta: (p.ancho, p.alto) for p in piezas}
    assert rutas["pueblo/fondo.png"] == (2 * pueblo.DATOS["ancho"], 2 * pueblo.DATOS["alto"])
    assert rutas["pueblo/lugares/plaza.png"] == (160, 160)
    assert rutas["escenas/cementerio.png"] == (720, 480)
    assert rutas["avatar/cuerpo/oscura-paso2.png"] == (48, 84)
    assert rutas["avatar/pelo/coleta-azul-quieto.png"] == (48, 84)
    assert rutas["avatar/ropa/overol-paso1.png"] == (48, 84)
    assert rutas["efectos/marca.png"] == (32, 32)


def test_el_contrato_sale_de_los_catalogos():
    rutas = {p.ruta for p in arte.piezas()}
    for lugar in pueblo.LUGARES:
        assert f"pueblo/lugares/{lugar}.png" in rutas and f"escenas/{lugar}.png" in rutas
    for pose in arte.POSES:
        for piel in avatar.PIELES:
            assert f"avatar/cuerpo/{piel.clave}-{pose}.png" in rutas
        for ropa in avatar.ROPAS:
            assert f"avatar/ropa/{ropa.clave}-{pose}.png" in rutas
        for pelo in avatar.PELOS:
            for color in avatar.COLORES_DE_PELO:
                assert f"avatar/pelo/{pelo.clave}-{color.clave}-{pose}.png" in rutas


def test_cada_pieza_esta_y_mide_lo_que_debe():
    faltan, mal = [], []
    for pieza in arte.piezas():
        ruta = arte.RAIZ / pieza.ruta
        if not ruta.is_file():
            faltan.append(pieza.ruta)
            continue
        with Image.open(ruta) as imagen:
            if imagen.format != "PNG" or imagen.size != (pieza.ancho, pieza.alto):
                mal.append((pieza.ruta, imagen.format, imagen.size))
    assert not faltan, f"faltan dibujos: {faltan}"
    assert not mal, f"no miden lo que dice el contrato: {mal}"


def test_no_hay_dibujos_que_el_contrato_no_conozca():
    en_disco = {p.relative_to(arte.RAIZ).as_posix() for p in arte.RAIZ.rglob("*") if p.is_file()}
    assert en_disco == {p.ruta for p in arte.piezas()}


def test_el_cliente_recibe_el_mismo_contrato():
    escrito = json.loads((arte.RAIZ.parent / "datos" / "arte.json").read_text(encoding="utf-8"))
    assert escrito == arte.como_json()


def test_generar_no_pisa_un_dibujo_que_ya_esta(tmp_path, monkeypatch):
    from herramientas import rellenos

    monkeypatch.setattr(arte, "RAIZ", tmp_path / "arte")
    (tmp_path / "datos").mkdir()
    escritas = rellenos.generar()
    assert len(escritas) == 136
    corazon = arte.RAIZ / "efectos" / "corazon.png"
    propio = Image.new("RGBA", (32, 32), (1, 2, 3, 255))
    propio.save(corazon)
    assert rellenos.generar() == []
    with Image.open(corazon) as imagen:
        assert imagen.getpixel((0, 0)) == (1, 2, 3, 255)
    assert len(rellenos.generar(todo=True)) == 136


def test_dos_lugares_no_tienen_el_mismo_relleno():
    def bytes_de(ruta):
        return (arte.RAIZ / ruta).read_bytes()

    lugares = [bytes_de(f"pueblo/lugares/{l}.png") for l in pueblo.LUGARES]
    escenas = [bytes_de(f"escenas/{l}.png") for l in pueblo.LUGARES]
    assert len(set(lugares)) == 9 and len(set(escenas)) == 9


def test_el_fondo_de_un_lugar_y_de_una_capa_es_transparente():
    for ruta in ("pueblo/lugares/casa.png", "avatar/pelo/corto-negro-quieto.png", "efectos/corazon.png"):
        with Image.open(arte.RAIZ / ruta) as imagen:
            assert imagen.convert("RGBA").getpixel((0, 0))[3] == 0, ruta
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_arte.py -q`
Expected: FAIL — `ImportError: cannot import name 'arte' from 'web'`.

- [ ] **Step 3: Escribir `web/arte.py` y `herramientas/rellenos.py`, y generar**

Run: `./venv/bin/python -m herramientas.rellenos`
Expected: imprime 136 rutas escritas y deja `web/static/datos/arte.json`.

Mira lo que salió antes de seguir: arma una hoja con el fondo, los nueve lugares, tres escenas y seis avatares distintos en sus tres poses, guárdala fuera del repo y ábrela. Nada de recuadros por letras que la fuente no tiene; el monigote se tiene que reconocer.

- [ ] **Step 4: Escribir `docs/arte/contrato.md`**

- [ ] **Step 5: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_arte.py tests/test_web_app.py tests/test_web_cliente.py -q`
Expected: PASS.

- [ ] **Step 6: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(arte): el contrato de arte y un relleno para cada pieza"
```

---

### Task 5: El cargador de arte y el avatar por capas

El cliente deja de dibujar el monigote con código y pasa a apilar archivos.

**Files:**
- Create: `web/static/js/arte.js`, `web/static/js/avatar.js`
- Modify: `web/static/js/dibujo.js` — se va `dibujarAvatar` y sus tres tablas de colores; se queda `dibujarHuevo`
- Modify: `web/static/js/entrada.js`, `web/static/js/lugar.js` — usan el avatar por capas
- Modify: `web/static/estilo.css` — si hace falta
- Test: `tests/js/arte.test.mjs`, `tests/js/avatar.test.mjs`; se ajusta `tests/js/dibujo.test.mjs`; `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: `web/static/datos/arte.json` y los archivos de `web/static/arte/` (tarea 4).
- Produces, en `arte.js`:
  - `urlDeArte(ruta: string) -> string` — la dirección de una pieza, armada con `new URL('../arte/' + ruta, import.meta.url)`: así lleva la versión de los estáticos.
  - `cargar(ruta: string) -> Promise<{ruta, imagen}>` — `imagen` es la imagen ya cargada, o `null` si no se pudo. Nunca rechaza. Recuerda lo ya pedido: dos llamadas con la misma ruta devuelven la misma promesa.
  - `faltante(ctx, x, y, ancho, alto, ruta) -> void` — el recuadro genérico de una pieza que no cargó: un rectángulo rayado con el nombre del archivo. Es lo único que se dibuja en lugar de una pieza ausente.
  - `pintarPieza(ctx, cargada, x, y, ancho, alto) -> void` — dibuja `cargada.imagen`, o `faltante` si es `null`.
- Produces, en `avatar.js`:
  - `POSES` — `['quieto', 'paso1', 'paso2']`.
  - `capasDelAvatar(avatar, pose) -> string[]` — las tres rutas, en el orden en que se apilan: cuerpo, ropa, pelo. Puro.
  - `poseAlCaminar(t: number, moviendose: boolean) -> string` — `'quieto'` si no se mueve; si se mueve, alterna `paso1` y `paso2` cada 0,18 s.
  - `cargarAvatar(avatar) -> Promise<Map<string, {ruta, imagen}>>` — las nueve capas (tres por pose), ya cargadas.
  - `dibujarAvatar(ctx, capas, avatar, pose, x, y, alto, espejo) -> void` — apila las tres capas de esa pose con los pies en `(x, y)`, a `alto` píxeles de alto y el ancho que corresponda a 48 × 84; con `espejo`, mirando a la izquierda. Una capa que no cargó se dibuja con `faltante`, las demás igual.
  - `lienzoDelAvatar(lienzo, avatar, alto) -> Promise<void>` — pinta el avatar quieto en un `<canvas>` suelto, con la densidad de la pantalla y sin suavizar los píxeles. Es lo que usan la pantalla del avatar (vista previa en vivo) y la escena de un lugar.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/js/avatar.test.mjs`:

```javascript
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { POSES, capasDelAvatar, poseAlCaminar, dibujarAvatar } from '../../web/static/js/avatar.js';

const contrato = JSON.parse(readFileSync(new URL('../../web/static/datos/arte.json', import.meta.url), 'utf8'));
const rutas = new Set(contrato.piezas.map((p) => p.ruta));
const feli = { nombre: 'Feli', genero: 'macho', piel: 'media', pelo: 'corto', color_de_pelo: 'castano', ropa: 'poleron' };

test('las capas se apilan cuerpo, ropa y pelo', () => {
  assert.deepEqual(capasDelAvatar(feli, 'quieto'), [
    'avatar/cuerpo/media-quieto.png', 'avatar/ropa/poleron-quieto.png', 'avatar/pelo/corto-castano-quieto.png',
  ]);
  assert.deepEqual(capasDelAvatar({ ...feli, piel: 'oscura', pelo: 'coleta', color_de_pelo: 'azul', ropa: 'vestido' }, 'paso2'), [
    'avatar/cuerpo/oscura-paso2.png', 'avatar/ropa/vestido-paso2.png', 'avatar/pelo/coleta-azul-paso2.png',
  ]);
});

test('toda combinación del catálogo cae en una pieza del contrato', () => {
  const partes = (prefijo) => [...rutas].filter((r) => r.startsWith(prefijo)).map((r) => r.slice(prefijo.length, -4));
  const pieles = new Set(partes('avatar/cuerpo/').map((p) => p.split('-')[0]));
  const ropas = new Set(partes('avatar/ropa/').map((p) => p.split('-')[0]));
  const pelos = new Set(partes('avatar/pelo/').map((p) => p.split('-').slice(0, 2).join('-')));
  assert.equal(pieles.size * ropas.size * pelos.size, 4 * 4 * 30);
  for (const piel of pieles) for (const ropa of ropas) for (const pelo of pelos) for (const pose of POSES) {
    const [forma, color] = pelo.split('-');
    for (const ruta of capasDelAvatar({ ...feli, piel, ropa, pelo: forma, color_de_pelo: color }, pose)) {
      assert.ok(rutas.has(ruta), ruta);
    }
  }
});

test('el género no cambia el dibujo', () => {
  assert.deepEqual(capasDelAvatar({ ...feli, genero: 'hembra' }, 'quieto'), capasDelAvatar(feli, 'quieto'));
});

test('quieto no da pasos, y caminando alterna', () => {
  assert.equal(poseAlCaminar(5, false), 'quieto');
  assert.equal(poseAlCaminar(0, true), 'paso1');
  assert.equal(poseAlCaminar(0.19, true), 'paso2');
  assert.equal(poseAlCaminar(0.37, true), 'paso1');
});

function lienzoDeMentira() {
  const hecho = [];
  const ctx = new Proxy({}, {
    get: (_, nombre) => (...args) => { hecho.push([nombre, ...args]); },
    set: (_, nombre, valor) => { hecho.push(['=' + String(nombre), valor]); return true; },
  });
  return { ctx, hecho };
}

test('se dibujan las tres capas en orden, y la que falta se ve como faltante', () => {
  const capas = new Map(capasDelAvatar(feli, 'quieto').map((ruta, i) => [ruta, { ruta, imagen: i === 1 ? null : { ruta } }]));
  const { ctx, hecho } = lienzoDeMentira();
  dibujarAvatar(ctx, capas, feli, 'quieto', 100, 200, 84, false);
  const imagenes = hecho.filter(([n]) => n === 'drawImage').map(([, imagen]) => imagen.ruta);
  assert.deepEqual(imagenes, ['avatar/cuerpo/media-quieto.png', 'avatar/pelo/corto-castano-quieto.png']);
  assert.ok(hecho.some(([n, texto]) => n === 'fillText' && String(texto).includes('poleron-quieto.png')));
});

test('con espejo se da vuelta', () => {
  const capas = new Map(capasDelAvatar(feli, 'quieto').map((ruta) => [ruta, { ruta, imagen: { ruta } }]));
  const { ctx, hecho } = lienzoDeMentira();
  dibujarAvatar(ctx, capas, feli, 'quieto', 100, 200, 84, true);
  assert.ok(hecho.some(([n, sx]) => n === 'scale' && sx === -1));
});
```

`tests/js/arte.test.mjs`: `cargar` no rechaza cuando la imagen falla y devuelve `imagen: null`; dos llamadas con la misma ruta devuelven la misma promesa; `urlDeArte('efectos/corazon.png')` termina en `/arte/efectos/corazon.png` y no contiene `..`; `pintarPieza` con `imagen: null` escribe el nombre del archivo. (El módulo usa `Image` del navegador: en la prueba se sustituye `globalThis.Image` por una clase de mentira que dispara `onload` u `onerror`.)

En `tests/js/dibujo.test.mjs` se quitan las pruebas del monigote dibujado con código; se queda la del huevo.

En `tests/test_web_cliente.py`:

```python
def test_el_avatar_ya_no_se_dibuja_con_codigo():
    dibujo = (ESTATICOS / "js" / "dibujo.js").read_text(encoding="utf-8")
    assert "dibujarAvatar" not in dibujo and "COLORES_DE_PIEL" not in dibujo
    for nombre in ("entrada.js", "lugar.js"):
        assert "./avatar.js" in (ESTATICOS / "js" / nombre).read_text(encoding="utf-8")


def test_el_arte_se_pide_por_la_ruta_con_version():
    arte = (ESTATICOS / "js" / "arte.js").read_text(encoding="utf-8")
    assert "import.meta.url" in arte
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py -q`
Expected: FAIL — no existe `avatar.js`.

- [ ] **Step 3: Implementar**

En la pantalla de crear el avatar, la vista previa sigue cambiando en vivo con cada elección; mientras cargan las capas de una elección nueva se queda la anterior, sin parpadeo. Las opciones de piel, pelo y ropa siguen enseñando su muestra de color: esos colores de muestra pasan a `entrada.js`, que es el único que los usa.

- [ ] **Step 4: Correr las pruebas y mirar la página**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py tests/test_web_app.py -q`
Expected: PASS.

Levanta el servicio con bases temporales y captura a 390 px la pantalla del avatar con dos combinaciones distintas y la escena de un lugar: el monigote se ve nítido, apoyado en el piso y del tamaño de antes.

- [ ] **Step 5: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): el avatar se arma con capas de archivo y el arte tiene un solo cargador"
```

---

### Task 6: La lógica del pueblo, sin pantalla

Todo lo que se puede probar sin dibujar: el camino más corto, la caminata, el gachamon que sigue, la cámara.

**Files:**
- Create: `web/static/js/pueblo.js`
- Test: `tests/js/pueblo.test.mjs`

**Interfaces:**
- Consumes: la forma de `pueblo.json` (tarea 1).
- Produces, en `pueblo.js` (puro: no toca `document` ni `window`):
  - `armarGrafo(datos) -> grafo` — vecinos de cada nodo con su distancia.
  - `ruta(grafo, desde, hasta) -> {camino: string[], largo: number}` — el camino más corto, con los dos extremos. De un nodo a sí mismo: `{camino: [nodo], largo: 0}`.
  - `crearPaseo(datos, grafo, lugar) -> paseo` — el avatar parado en ese lugar, mirando a la derecha, y el gachamon `hueco` más a la izquierda. `paseo` es un objeto con, al menos: `x`, `y`, `mira` (1 o −1), `caminando`, `destino` (clave de lugar o `null`), `en` (el último lugar o nodo alcanzado), `gx`, `gy`, `gmira`, `gcaminando`, `t` (segundos caminados).
  - `ir(paseo, lugar) -> 'camina' | 'llego' | 'nada'` — fija el destino. Parado en ese mismo lugar: `'llego'` sin moverse. Caminando hacia otro lugar: cambia de rumbo **desde donde está**, siguiendo hasta el nodo al que iba o volviendo al que dejó, lo que dé el camino total más corto. Un lugar que no existe: `'nada'`.
  - `avanzar(paseo, dt) -> boolean` — mueve al avatar `velocidad × dt` por su camino y al gachamon por el rastro del avatar, `hueco` detrás. Devuelve `true` en el paso en que llega al destino (una sola vez).
  - `llegarYa(paseo) -> boolean` — lo deja en el destino de inmediato, con el gachamon `hueco` detrás sobre el último tramo del camino por el que habría llegado. `false` si no tenía destino.
  - `salto(t, caminando) -> number` — cuánto sube el gachamon en este instante: 0 parado; caminando, `5 × |sen(π × t / 0,18)|` (un saltito de 5 unidades cada 0,18 s).
  - `encuadre(anchoPx, altoPx, datos) -> {escala, completo, anchoVista}` — con `anchoPx >= 900`, el pueblo entero: `escala = min(anchoPx / ancho, altoPx / alto)`, `completo: true`. Si no, `escala = altoPx / alto`, `completo: false`. `anchoVista` es cuánto pueblo cabe a lo ancho, en unidades del pueblo.
  - `camaraHacia(x, anchoVista, datos) -> number` — dónde quiere estar la cámara para centrar `x`, sin salirse del pueblo. Con `anchoVista >= ancho`, 0.
  - `acercarCamara(camara, objetivo, dt) -> number` — se acerca al objetivo con suavidad (`camara + (objetivo − camara) × min(1, 5·dt)`).
  - `arrastrarCamara(camaraAlTocar, dxPx, escala, anchoVista, datos) -> number` — la cámara tras arrastrar `dxPx` píxeles, sin salirse.
  - `flechas(camara, anchoVista, datos) -> {izquierda: boolean, derecha: boolean}` — si queda pueblo por ver a cada lado (con 2 unidades de margen).
  - `lugarEn(datos, x, y) -> string | null` — el lugar tocado en ese punto del pueblo: el más cercano entre los que tienen su nodo a menos de 40 unidades a lo ancho y cuyo dibujo (de 70 unidades por encima del nodo a 12 por debajo) contiene `y`.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/js/pueblo.test.mjs`:

```javascript
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as p from '../../web/static/js/pueblo.js';

const datos = JSON.parse(readFileSync(new URL('../../web/static/datos/pueblo.json', import.meta.url), 'utf8'));
const grafo = p.armarGrafo(datos);
const lugares = Object.keys(datos.lugares);
const cerca = (a, b, margen = 0.01) => assert.ok(Math.abs(a - b) <= margen, `${a} no es ${b}`);

function caminar(paseo, segundos, paso = 0.05) {
  let llegadas = 0;
  for (let t = 0; t < segundos - 1e-9; t += paso) if (p.avanzar(paseo, paso)) llegadas += 1;
  return llegadas;
}

test('el camino más corto', () => {
  assert.deepEqual(p.ruta(grafo, 'casa', 'tienda'), { camino: ['casa', 'l1', 'u1', 'tienda'], largo: 305 });
  assert.deepEqual(p.ruta(grafo, 'casa', 'plaza'), { camino: ['casa', 'l1', 'l2', 'plaza'], largo: 305 });
  assert.deepEqual(p.ruta(grafo, 'plaza', 'plaza'), { camino: ['plaza'], largo: 0 });
});

test('la caminata más larga dura unos seis segundos', () => {
  let maximo = 0;
  for (const a of lugares) for (const b of lugares) maximo = Math.max(maximo, p.ruta(grafo, a, b).largo);
  assert.equal(maximo, 725);
  cerca(maximo / datos.velocidad, 6.3, 0.05);
});

test('se llega una vez, al lugar, y el gachamon queda detrás', () => {
  const paseo = p.crearPaseo(datos, grafo, 'casa');
  assert.deepEqual([paseo.x, paseo.y, paseo.gx, paseo.gy, paseo.caminando], [75, 330, 75 - 26, 330, false]);
  assert.equal(p.ir(paseo, 'tienda'), 'camina');
  assert.equal(paseo.destino, 'tienda');
  assert.equal(caminar(paseo, 305 / 115 + 0.2), 1);
  assert.deepEqual([paseo.x, paseo.y, paseo.caminando, paseo.destino, paseo.en], [220, 170, false, null, 'tienda']);
  cerca(Math.hypot(paseo.x - paseo.gx, paseo.y - paseo.gy), 26, 0.5);
});

test('a medio camino va por el camino, a su velocidad, y el gachamon por el mismo rastro', () => {
  const paseo = p.crearPaseo(datos, grafo, 'casa');
  p.ir(paseo, 'tienda');
  caminar(paseo, 1);
  cerca(paseo.x, 75 + 90, 0.01);
  cerca(paseo.y, 330 - 25, 0.01);
  assert.equal(paseo.caminando, true);
  cerca(paseo.gx, 165 - 1, 0.6);
  cerca(paseo.gy, 330, 0.6);
  assert.equal(paseo.gcaminando, true);
});

test('mira hacia donde camina', () => {
  const paseo = p.crearPaseo(datos, grafo, 'refugio');
  p.ir(paseo, 'barrio');
  caminar(paseo, 0.5);
  assert.equal(paseo.mira, -1);
  assert.equal(paseo.gmira, -1);
});

test('cambiar de rumbo a mitad de camino: seguir o volver, lo más corto', () => {
  const sigue = p.crearPaseo(datos, grafo, 'casa');
  p.ir(sigue, 'tienda');
  caminar(sigue, 0.5);
  assert.equal(p.ir(sigue, 'refugio'), 'camina');
  caminar(sigue, 0.1);
  assert.ok(sigue.x > 132.5 && sigue.y === 330);
  assert.equal(caminar(sigue, 10), 1);
  assert.deepEqual([sigue.x, sigue.y, sigue.en], [575, 330, 'refugio']);

  const vuelve = p.crearPaseo(datos, grafo, 'casa');
  p.ir(vuelve, 'tienda');
  caminar(vuelve, 0.2);
  assert.equal(p.ir(vuelve, 'casa'), 'camina');
  assert.equal(caminar(vuelve, 1), 1);
  assert.deepEqual([vuelve.x, vuelve.y, vuelve.en], [75, 330, 'casa']);
});

test('tocar donde ya estás es llegar, y un lugar que no existe no hace nada', () => {
  const paseo = p.crearPaseo(datos, grafo, 'plaza');
  assert.equal(p.ir(paseo, 'plaza'), 'llego');
  assert.equal(paseo.caminando, false);
  assert.equal(p.ir(paseo, 'portal'), 'nada');
  assert.equal(p.ir(paseo, 'u1'), 'nada');
  assert.equal(p.avanzar(paseo, 1), false);
});

test('el segundo toque te lleva de inmediato', () => {
  const paseo = p.crearPaseo(datos, grafo, 'casa');
  assert.equal(p.llegarYa(paseo), false);
  p.ir(paseo, 'aventura');
  caminar(paseo, 1);
  assert.equal(p.llegarYa(paseo), true);
  assert.deepEqual([paseo.x, paseo.y, paseo.caminando, paseo.destino, paseo.en], [640, 170, false, null, 'aventura']);
  cerca(Math.hypot(paseo.x - paseo.gx, paseo.y - paseo.gy), 26, 0.5);
  assert.equal(p.avanzar(paseo, 1), false);
});

test('muchos toques seguidos nunca lo sacan de un camino', () => {
  const paseo = p.crearPaseo(datos, grafo, 'casa');
  const enUnCamino = () => datos.aristas.some(([a, b]) => {
    const [ax, ay] = datos.nodos[a], [bx, by] = datos.nodos[b];
    const largo = Math.hypot(bx - ax, by - ay);
    return Math.abs(Math.hypot(paseo.x - ax, paseo.y - ay) + Math.hypot(paseo.x - bx, paseo.y - by) - largo) < 0.01;
  });
  let semilla = 7;
  const azar = () => { semilla = (semilla * 1664525 + 1013904223) % 4294967296; return semilla / 4294967296; };
  for (let i = 0; i < 400; i += 1) {
    p.ir(paseo, lugares[Math.floor(azar() * lugares.length)]);
    caminar(paseo, azar() * 1.5, 0.03);
    assert.ok(enUnCamino(), `fuera del camino en ${paseo.x}, ${paseo.y}`);
  }
});

test('el gachamon salta sólo cuando camina', () => {
  assert.equal(p.salto(1.23, false), 0);
  assert.equal(p.salto(0, true), 0);
  cerca(p.salto(0.09, true), 5, 0.01);
  cerca(p.salto(0.18, true), 0, 0.01);
  assert.ok(p.salto(0.27, true) > 0);
});

test('en el teléfono se ve un trozo y en el computador el pueblo entero', () => {
  const telefono = p.encuadre(390, 559, datos);
  cerca(telefono.escala, 1.3, 0.001);
  assert.equal(telefono.completo, false);
  cerca(telefono.anchoVista, 300, 0.01);
  const compu = p.encuadre(1000, 645, datos);
  cerca(compu.escala, 1000 / 690, 0.001);
  assert.equal(compu.completo, true);
  assert.ok(compu.anchoVista >= 690 - 1e-6);
  assert.equal(p.encuadre(900, 2000, datos).completo, true);
  assert.equal(p.encuadre(899, 559, datos).completo, false);
});

test('la cámara sigue al avatar sin salirse del pueblo', () => {
  assert.equal(p.camaraHacia(75, 300, datos), 0);
  assert.equal(p.camaraHacia(300, 300, datos), 150);
  assert.equal(p.camaraHacia(640, 300, datos), 390);
  assert.equal(p.camaraHacia(300, 800, datos), 0);
  cerca(p.acercarCamara(0, 100, 0.1), 50);
  assert.equal(p.acercarCamara(0, 100, 1), 100);
});

test('arrastrar mueve la cámara, y las flechas dicen si queda pueblo', () => {
  assert.equal(p.arrastrarCamara(100, -130, 1.3, 300, datos), 200);
  assert.equal(p.arrastrarCamara(100, 1300, 1.3, 300, datos), 0);
  assert.equal(p.arrastrarCamara(100, -1300, 1.3, 300, datos), 390);
  assert.deepEqual(p.flechas(0, 300, datos), { izquierda: false, derecha: true });
  assert.deepEqual(p.flechas(200, 300, datos), { izquierda: true, derecha: true });
  assert.deepEqual(p.flechas(390, 300, datos), { izquierda: true, derecha: false });
  assert.deepEqual(p.flechas(0, 800, datos), { izquierda: false, derecha: false });
});

test('qué lugar se tocó', () => {
  assert.equal(p.lugarEn(datos, 75, 300), 'casa');
  assert.equal(p.lugarEn(datos, 75, 338), 'casa');
  assert.equal(p.lugarEn(datos, 300, 215), 'plaza');
  assert.equal(p.lugarEn(datos, 232, 250), null);
  assert.equal(p.lugarEn(datos, 75, 240), null);
  assert.equal(p.lugarEn(datos, 165, 150), null);
});
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `node --test tests/js/pueblo.test.mjs`
Expected: FAIL — no existe `pueblo.js`.

- [ ] **Step 3: Escribir `web/static/js/pueblo.js`**

El rastro del avatar se guarda como una lista de puntos acotada (no crece sin fin en un paseo largo). El gachamon se coloca recorriendo ese rastro hacia atrás hasta acumular `hueco`. El cambio de rumbo compara, igual que el boceto, «seguir hasta el nodo al que iba y de ahí al destino» contra «volver al nodo que dejó y de ahí al destino».

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py -q`
Expected: PASS.

- [ ] **Step 5: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): la lógica del pueblo — ruta, caminata, seguidor y cámara"
```

---

### Task 7: El mapa

La pantalla del pueblo: se ve, se toca y se camina.

**Files:**
- Create: `web/static/js/mapa.js`
- Modify: `web/static/js/pantallas.js`, `web/static/js/principal.js`
- Modify: `web/static/js/lugar.js` — sólo el botón «Pueblo»
- Modify: `web/static/estilo.css`
- Test: `tests/js/pantallas.test.mjs`, `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: `pueblo.js` entero (tarea 6); `arte.cargar`, `arte.pintarPieza`, `avatar.cargarAvatar`, `avatar.dibujarAvatar`, `avatar.poseAlCaminar` (tarea 5); `api.pedir`; `POST /gachamon/api/lugar` y `estado.lugar` (tarea 2); `web/static/datos/pueblo.json`.
- Produces:
  - `pantallas.siguiente(sesion, cuenta, estado, vista)` — gana un cuarto argumento. Devuelve `'pueblo'` sólo cuando todo lo demás daría `'lugar'` y `vista === 'pueblo'`. Sin el argumento, se comporta como hoy.
  - `principal.js`: `seguir(estado, opciones)` acepta `opciones.vista` (`'pueblo'` o nada) y `opciones.llegando` (cierto cuando se acaba de llegar caminando), y se los pasa a la pantalla en sus datos: `{sesion, cuenta, estado, llegando}`. La vista no se recuerda entre llamadas: `seguir()` a secas vuelve al lugar.
  - `pantallas.trasFallarLaLlegada(error) -> 'decidir' | 'reintentar'` — qué se hace si falla el `POST lugar` de la llegada: con un 401 o un 409, `'decidir'` (se llama a `seguir()` a secas); con cualquier otra cosa, `'reintentar'` (te quedas en el mapa con una frase).
  - `mapa.js`: `pueblo(contenedor, estado, seguir)` — pinta el mapa y lo mantiene vivo hasta que se sale.
  - `lugar.js`: bajo los cuidados, un botón «Pueblo» que llama a `seguir(estadoActual, {vista: 'pueblo'})`. Es lo único que esta tarea toca de esa pantalla.

Lo que tiene la pantalla: la cabecera de siempre (con «Pueblo» en vez del nombre de un lugar, y los saldos); el lienzo del mapa; debajo, un botón «Volver a <lugar donde estás>» y una lista con un botón por lugar.

Cómo se comporta:

- **Se dibuja**, de atrás hacia adelante: el fondo, los nueve lugares apoyados en su nodo (80 × 80 unidades, centrados a lo ancho) con su nombre debajo, la marca sobre el destino mientras se camina, el gachamon y el avatar ordenados por su `y` (el de más abajo tapa al otro). El gachamon es su retrato de siempre (`estado.gachamon.retrato`), de 30 unidades de alto, levantado lo que diga `salto` y dado vuelta según `gmira`. El avatar mide 42 unidades de alto.
- **Empiezas** parado en `estado.lugar.clave`.
- **Tocar un lugar** (en el lienzo o en la lista) llama a `ir`. Si ya estabas ahí, entras de inmediato. Tocar **el mismo destino** mientras caminas te lleva ya (`llegarYa`). Tocar fuera de todo lugar no hace nada.
- **Al llegar** se manda `POST lugar` y, con el estado que vuelve, `seguir(estado, {llegando: true})`: la pantalla pasa a la del lugar. Mientras se espera esa respuesta, los toques no hacen nada.
- **Si esa petición falla**, decide `trasFallarLaLlegada`: `'reintentar'` es una frase («No se pudo entrar. Revisa tu conexión.») y dos salidas — tocar el lugar otra vez, o «Volver a …»; `'decidir'` es `seguir()` a secas.
- **En el teléfono** (menos de 900 px) la cámara sigue al avatar; arrastrar con el dedo la mueve y deja de seguir hasta el próximo toque en un lugar; unas flechas en los bordes avisan cuando queda pueblo hacia ese lado. Un arrastre de más de 8 px no cuenta como toque.
- **En el computador** (900 px o más) se ve el pueblo entero, centrado, sin cámara ni flechas.
- **Al cambiar el tamaño** de la ventana o girar el teléfono, se reencuadra con `encuadre` sin perder la caminata.
- **Con `prefers-reduced-motion`**, tocar un lugar es llegar de inmediato.
- **La lista de botones** («Ir a la Plaza», …) es la forma de usar el pueblo con teclado o lector de pantalla: hace lo mismo que tocar el lienzo. El lienzo lleva `aria-hidden`.
- **Si un dibujo no carga**, en su sitio va el recuadro de `arte.faltante` y todo lo demás sigue: se puede tocar y llegar igual.
- Todo lo que corre (el cuadro de animación, los oyentes) se detiene al salir de la pantalla, y una respuesta que llega tarde no pinta ni llama a `seguir`.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/js/pantallas.test.mjs`:

```javascript
test('el pueblo sólo se ve cuando todo lo demás está en orden', () => {
  assert.equal(siguiente(sesion, { estado: 'web' }, estado(), 'pueblo'), 'pueblo');
  assert.equal(siguiente(sesion, { estado: 'web' }, estado()), 'lugar');
  assert.equal(siguiente(sesion, { estado: 'web' }, estado({ difunto: { nombre: 'Viejo' } }), 'pueblo'), 'difunto');
  assert.equal(siguiente(sesion, { estado: 'web' }, estado({ gachamon: null }), 'pueblo'), 'huevo');
  assert.equal(siguiente(null, null, null, 'pueblo'), 'sesion');
});

test('si falla la llegada: sin sesión o sin gachamon se decide de nuevo; lo demás se reintenta', () => {
  assert.equal(trasFallarLaLlegada({ estado: 401, clave: 'sin_sesion' }), 'decidir');
  assert.equal(trasFallarLaLlegada({ estado: 409, clave: 'sin_cuenta' }), 'decidir');
  assert.equal(trasFallarLaLlegada({ estado: 0, clave: null }), 'reintentar');
  assert.equal(trasFallarLaLlegada({ estado: 503, clave: 'servicio' }), 'reintentar');
  assert.equal(trasFallarLaLlegada(undefined), 'reintentar');
});
```

En `tests/test_web_cliente.py`:

```python
def test_el_mapa_esta_y_se_usa():
    nombres = {g.name for g in GUIONES}
    assert {"mapa.js", "pueblo.js", "arte.js", "avatar.js"} <= nombres
    principal = (ESTATICOS / "js" / "principal.js").read_text(encoding="utf-8")
    assert "./mapa.js" in principal


def test_el_mapa_no_lleva_el_pueblo_escrito_en_el_codigo():
    mapa = (ESTATICOS / "js" / "mapa.js").read_text(encoding="utf-8")
    logica = (ESTATICOS / "js" / "pueblo.js").read_text(encoding="utf-8")
    assert "pueblo.json" in mapa
    for clave in ("incubadora", "cementerio", "estadio", "barrio"):
        assert clave not in mapa and clave not in logica


def test_el_mapa_se_puede_usar_sin_el_lienzo_y_respeta_a_quien_no_quiere_movimiento():
    mapa = (ESTATICOS / "js" / "mapa.js").read_text(encoding="utf-8")
    assert "aria-hidden" in mapa and "prefers-reduced-motion" in mapa
    assert "requestAnimationFrame" in mapa and "cancelAnimationFrame" in mapa


def test_desde_un_lugar_se_va_al_pueblo():
    lugar = (ESTATICOS / "js" / "lugar.js").read_text(encoding="utf-8")
    assert "vista: 'pueblo'" in lugar or 'vista: "pueblo"' in lugar
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py -q`
Expected: FAIL — no existe `mapa.js`.

- [ ] **Step 3: Implementar**

`mapa.js` no decide nada del pueblo: lee `pueblo.json`, le pasa los toques a `pueblo.js` y dibuja lo que éste le diga. El lienzo se dimensiona con la densidad de la pantalla y con el suavizado apagado, para que los dibujos de cuadros no se emborronen.

- [ ] **Step 4: Correr las pruebas y mirar la página**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py tests/test_web_app.py -q`
Expected: PASS.

Levanta el servicio con bases temporales, entra y pulsa «Pueblo». Captura a 390 px y a 1280 px: parado, a mitad de camino (avanzando la simulación a mano, porque el tiempo virtual de Chrome sin ventana no mueve la animación), con la cámara al fondo del pueblo y con un dibujo quitado a propósito.

- [ ] **Step 5: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): el mapa del pueblo — tocas un lugar y caminas hasta ahí"
```

---

### Task 8: Cada lugar por dentro

La pantalla principal deja de ser siempre «tu hogar»: es el lugar donde estás.

**Files:**
- Modify: `web/static/js/lugar.js`, `web/static/js/tiempo.js`, `web/static/js/principal.js`
- Modify: `web/static/estilo.css`
- Test: `tests/js/tiempo.test.mjs`, `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: `estado.lugar` y los globos de tipo `lugar` (tareas 2 y 3); `arte.cargar`, `avatar.lienzoDelAvatar` (tarea 5); el dato `llegando` y el botón «Pueblo» (tarea 7).
- Produces:
  - `tiempo.elegirGlobo(globos, anterior, azar, llegando = false)` — gana un cuarto argumento. Regla: si hay alguna necesidad, entre ellas; si no, y `llegando` es cierto y hay alguna de tipo `lugar`, entre ellas; si no, entre las sueltas. Las de tipo `lugar` no salen nunca si no se está llegando. No repite `anterior` mientras haya otra candidata.
  - `lugar(contenedor, estado, seguir, llegando = false)` — la pantalla del lugar donde estás.

Lo que cambia en la pantalla:

- **La cabecera** dice el nombre del lugar (`estado.lugar.nombre`), no el del hogar.
- **La escena** lleva de fondo el dibujo `escenas/<clave>.png`. Si no carga, se queda la pared y el piso de hoy con el recuadro de la pieza que falta. El avatar se pinta por capas.
- **El aviso del lugar** (`estado.lugar.aviso`), cuando lo hay, va en una franja propia entre la ficha y los cuidados. No es un error ni desaparece solo.
- **Al llegar** (`llegando`), el primer globo sale enseguida y es del lugar, salvo que haya una necesidad. Después el gachamon sigue con su charla de siempre.
- **El botón «Pueblo»** de la tarea 7 se queda donde está, como única navegación. (La mochila y hablar llegan con el plan 4; no se pone nada que no funcione.)
- **Dónde vive** el gachamon ya no sale en la cabecera: va en la línea de detalle de la ficha, después del nivel — «vive en tu casa», «vive en el refugio» o «vive a la intemperie».
- Los cuidados, la caricia, las barras, las medallas y la relectura cada 30 segundos siguen igual en los nueve lugares.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/js/tiempo.test.mjs`:

```javascript
const delLugar = { tipo: 'lugar', texto: 'Aquí huele a pan.' };

test('al llegar habla del lugar, salvo que necesite algo', () => {
  for (const azar of [primero, ultimo]) {
    assert.equal(elegirGlobo([charla, delLugar, charlaOtra], null, azar, true), delLugar);
    assert.equal(elegirGlobo([charla, delLugar, pide], null, azar, true), pide);
  }
});

test('si no está llegando, del lugar no dice nada', () => {
  for (const azar of [primero, ultimo]) {
    assert.notEqual(elegirGlobo([charla, delLugar, charlaOtra], null, azar), delLugar);
    assert.notEqual(elegirGlobo([charla, delLugar, charlaOtra], null, azar, false), delLugar);
  }
  assert.equal(elegirGlobo([delLugar], null, primero), null);
});

test('dónde vive se dice en minúscula y con su preposición', () => {
  assert.equal(dondeVive('propia'), 'vive en tu casa');
  assert.equal(dondeVive('refugio'), 'vive en el refugio');
  assert.equal(dondeVive('intemperie'), 'vive a la intemperie');
  assert.equal(dondeVive('otra cosa'), '');
});
```

(`dondeVive(hogar) -> string` es nueva en `tiempo.js`; `nombreDelHogar` se va si ya nadie la usa.)

En `tests/test_web_cliente.py`:

```python
def test_la_pantalla_del_lugar_dice_donde_estas_y_avisa_lo_del_lugar():
    lugar = (ESTATICOS / "js" / "lugar.js").read_text(encoding="utf-8")
    assert "lugar.nombre" in lugar and "lugar.aviso" in lugar
    assert "escenas/" in lugar
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py -q`
Expected: FAIL — `elegirGlobo` devuelve la frase del lugar sin estar llegando, y falta `dondeVive`.

- [ ] **Step 3: Implementar**

- [ ] **Step 4: Correr las pruebas y mirar la página**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py tests/test_web_app.py -q`
Expected: PASS.

Con el servicio levantado sobre bases temporales, recorre el juego entero y captura a 390 px y a 1280 px: tu hogar al entrar; el pueblo; la llegada a la tienda (aviso de «abre pronto» y globo del lugar); la llegada al estadio con una cuenta vinculada y con una que no lo está; tu casa sin casa propia; y un cuidado y una caricia hechos en la plaza.

- [ ] **Step 5: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): cada lugar por dentro, con su escena, su aviso y la vuelta al pueblo"
```

---

### Task 9: Documentos y puesta en marcha

**Files:**
- Modify: `README.md`, `AGENTS.md`
- Modify: `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`

- [ ] **Step 1: `AGENTS.md`**

En los invariantes:

```markdown
- El pueblo vive en `web/static/datos/pueblo.json`: qué lugares hay, sus nombres, sus coordenadas y sus caminos. El código no lleva coordenadas ni una lista propia de lugares; sólo nombra uno por su clave donde le da un significado. El servidor recuerda en qué lugar estás; la caminata es del cliente y no se guarda a medias.
- Cada dibujo de la web es un archivo de `web/static/arte/` descrito en `web/arte.py`. Reemplazar un dibujo es cambiar el archivo; si falta, se ve un recuadro con su nombre y nunca el dibujo de otra pieza.
```

- [ ] **Step 2: `README.md`**

En la sección «La web»: una frase sobre el pueblo, y un apartado «Arte» que diga dónde está el contrato (`docs/arte/contrato.md`), cómo se regeneran los rellenos que falten (`./venv/bin/python -m herramientas.rellenos`) y que `tests/test_arte.py` avisa de lo que falta o no mide lo que debe.

- [ ] **Step 3: El documento de pendientes**

Una sección «Salió al ejecutar el plan 3» con lo que se haya dejado, y, para el plan 4: los avisos de «abre pronto» de la incubadora y la tienda se quitan cambiando `abre` a `ya` en `pueblo.json`; la navegación del lugar gana la mochila y hablar; el contrato de arte gana los íconos y los muebles.

- [ ] **Step 4: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "docs(web): el pueblo y el contrato de arte, en el README y en la política"
```

- [ ] **Step 5: (Controlador) Mirar el juego entero**

Con el servicio en local sobre bases temporales: el recorrido de la tarea 8 otra vez, sobre la rama terminada, en 390 px y 1280 px. Las capturas se le enseñan a Felipe antes de pedirle nada.

- [ ] **Step 6: (Controlador, con Felipe) Revisión final, fusión y subida**

Revisión de toda la rama; fusionar y subir son decisión de Felipe. La CI tiene que pasar en 3.12 y 3.14.

- [ ] **Step 7: (Controlador, con Felipe) Desplegar**

`./actualizar-pi.sh`. No hay nada que tocar en el túnel ni en el `.env`. Después, desde la Pi y desde fuera: los dos servicios activos, `/gachamon/api/salud`, y que `https://rowino.online/gachamon/static/<versión>/datos/pueblo.json` y un dibujo de `arte/` contestan 200.

- [ ] **Step 8: (Felipe) Probarlo**

En el teléfono y en el computador: caminar por el pueblo, entrar a cada lugar, cuidar y acariciar fuera de casa.
