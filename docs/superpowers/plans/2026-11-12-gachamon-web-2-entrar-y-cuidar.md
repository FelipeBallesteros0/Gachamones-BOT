# Gachamon web · Plan 2 de 4 — Entrar y cuidar

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que una cuenta de Rowino pueda abrir `rowino.online/gachamon`, vincular su Discord o empezar de cero, crear su avatar, sacar su primer gachamon y cuidarlo, acariciarlo y verlo hablar — todo desplegado en la Pi, todavía sin enlace público.

**Architecture:** Un paquete nuevo, `web/`, con un servicio FastAPI que cuelga entero de `/gachamon` y usa los mismos `db.py` y `economia.py` que el bot, contra la misma base. No guarda estado del juego en memoria: cada petición lee, actúa y contesta el estado completo. El cliente es HTML, CSS y módulos de JavaScript sin compilar; pregunta por el estado y dibuja la pantalla que toca.

**Tech Stack:** Python 3.12 y 3.14, FastAPI 0.162.5, Uvicorn 0.54.0, itsdangerous 2.2.0, SQLite síncrono, Pillow 12.3.0, pytest 9.1.1 con httpx 0.28.1 para el cliente de pruebas. JavaScript del navegador, sin dependencias.

**Spec:** `docs/superpowers/specs/2026-11-12-gachamon-web-parte-a-design.md` — secciones 5.1, 5.2, 5.3, 5.6, 5.7 y 5.9. También `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md` y `docs/superpowers/specs/2026-11-12-tunel-regla-por-ruta.md`. Quien ejecute lee los tres.

**Los cuatro planes de la parte A** (eran tres; este se partió para que al terminarlo ya se pueda jugar algo de verdad):

1. **Reglas y bot** — hecho y desplegado.
2. **Entrar y cuidar** — este.
3. **El pueblo** — los nueve lugares, los caminos, la cámara en el celular y el mapa completo en el computador, las escenas por lugar y el contrato de arte entero.
4. **Los lugares y la apertura** — incubadora, tienda, mochila, ropero, casa con huerto y muebles, refugio, hablar; el enlace en Rowino, que su inicio de sesión vuelva a Gachamon, y el aviso en el canal.

## Global Constraints

- Todo lo de `AGENTS.md` sigue mandando: módulos puros sin `discord`, SQLite síncrono, `db.py` no importa `economia.py`, mutaciones bajo `BEGIN IMMEDIATE`, tiempo y azar inyectados en las pruebas.
- **`web/` no importa `discord`, ni directa ni indirectamente.** No puede importar `vistas`, `tienda`, `equipo`, `comun` ni nada de `cogs/`.
- **El servicio no guarda estado del juego en memoria.** Lo único que se recuerda entre peticiones son cachés de cosas que no cambian mientras el proceso vive (dibujos ya armados, la versión de los archivos estáticos).
- **Quién eres sale sólo de la cookie de Rowino.** Ninguna ruta acepta un `usuario_id`, un `guild_id` ni un id de cuenta en la dirección o en el cuerpo.
- Toda ruta que cambia algo es `POST` o `PUT` y exige la cabecera `X-Gachamon: 1`. Sin ella, 403.
- Todo cuelga de `/gachamon`. Fuera de ese prefijo el servicio contesta 404, y no publica `/docs` ni `/openapi.json`.
- Las rutas se declaran con `def`, no con `async def`: SQLite es síncrono y FastAPI las corre en su grupo de hilos.
- El reloj es siempre `db.ahora_utc()`, llamado en el momento; las pruebas lo sustituyen.
- Un error se contesta siempre con esta forma: `{"detail": {"clave": "<clave>", "mensaje": "<frase para el jugador>"}}`.
- Dependencias nuevas, con versión exacta: `fastapi==0.162.5`, `uvicorn==0.54.0`, `itsdangerous==2.2.0` en `requirements.txt`; `httpx==0.28.1` en `requirements-dev.txt`. Ninguna otra.
- Texto de jugador: «monedas» y «gemas», en singular cuando es una; nunca ASCII. Las frases que hablan del gachamon llevan las marcas de concordancia de `especies.concordar`.
- **El cliente no usa frameworks ni paso de compilación**, y **nunca mete texto en la página con `innerHTML`**: todo lo que venga del servidor o del jugador entra con `textContent`.
- Toda prueba que toque `db`, `economia` o el servicio usa una base temporal. La guardia de `tests/conftest.py` hace fallar a la que se olvide.
- El arte es de relleno y **se tiene que notar** que lo es. Si falta un dibujo se enseña el relleno de esa pieza, nunca el de otra.
- Caricia: **+5 de ánimo cada 19 minutos**. El diseño decía 20; son 19 porque ningún enfriamiento puede ser múltiplo de otro (competir dura 10) y hay una prueba que lo vigila.
- Antes de cada commit: `./venv/bin/python -m pre_commit run --all-files && git diff --check`, encadenados con `&&`.
- **Nada de push, merge ni despliegue sin autorización explícita de Felipe.** La tarea 13 toca la Pi y el túnel: cada paso de esa tarea se le pide.
- Rama de trabajo: `web/2-entrar-y-cuidar`, desde `main`. Un commit por tarea.

## Review Focus

1. **Una cookie bien firmada de una cuenta bloqueada o borrada, y un servicio sin clave configurada.** En los tres casos no entra nadie y nada revienta. → Tarea 2.
2. **El doble toque y el reintento de red al cuidar.** El mismo evento no premia dos veces ni gasta dos enfriamientos. → Tarea 9.
3. **Dos pestañas, o el bot y la web, sobre el mismo gachamon a la vez.** Dos caricias simultáneas cuentan una; una muerte que detectan los dos procesos deja un solo relevo. → Tareas 5 y 7.
4. **El gachamon de una cuenta vinculada que murió por el bucle del bot mientras nadie miraba la web.** Al entrar se cuenta una vez, y no vuelve a salir. → Tarea 7.
5. **Nombres con HTML, emoji o espacios raros.** El servidor los valida y el cliente no los interpreta como marcado. → Tareas 4, 8 y 11.

---

### Task 1: Arranque compartido y esqueleto del servicio

Lo primero es que el bot y la web arranquen por el mismo camino, y que exista un servicio vacío al que colgarle rutas.

**Files:**
- Modify: `requirements.txt`, `requirements-dev.txt`
- Modify: `economia.py` — `poner_al_dia`
- Modify: `bot.py` — `setup_hook`
- Modify: `config.py`, `.env.ejemplo` — `ROWINO_SECRET_KEY`, `RUTA_ROWINO_BD`
- Create: `web/__init__.py`, `web/app.py`, `web/static/index.html`
- Create: `tests/ayudas_web.py`
- Modify: `tests/conftest.py` — fixture `cliente`
- Test: `tests/test_web_app.py`

**Interfaces:**
- Consumes: `economia.devolver_cosmeticos_retirados`, `db.inicializar` (plan 1).
- Produces:
  - `economia.poner_al_dia(ahora: datetime) -> ResumenDevolucion` — `db.inicializar()` y después la devolución. Es **el** arranque: lo llaman `bot.py` y `web/app.py`, y nadie más llama a `db.inicializar()` fuera de las pruebas.
  - `config.ROWINO_SECRET_KEY: str` — variable de entorno `ROWINO_SECRET_KEY`, vacía si falta.
  - `config.RUTA_ROWINO_BD: Path` — variable `RUTA_ROWINO_BD`; si falta, `RAIZ.parent / "rowino_web" / "rowino.db"`.
  - `web.app.PREFIJO = "/gachamon"`
  - `web.app.crear_app() -> FastAPI` — fábrica sin efectos al importar. Al arrancar llama a `economia.poner_al_dia(db.ahora_utc())` y anota el resumen igual que el bot. `web.app.app = crear_app()` al final del módulo, para `uvicorn web.app:app`.
  - `app.state.version: str` — huella corta (8 hexadecimales o más) del contenido de `web/static/`, calculada al crear la app.
  - Rutas: `GET /gachamon/api/salud` → `{"ok": true}`; `GET /gachamon` y `GET /gachamon/` → `web/static/index.html` con `Cache-Control: no-cache` y con cada `__V__` del archivo sustituido por la versión; los estáticos en `/gachamon/static/<versión>/…`.
  - `tests/ayudas_web.py`: `CLAVE = "clave-de-prueba"`, `PUEBLO = 777`, `ESCRIBIR = {"X-Gachamon": "1"}`, `T0`, `galleta(uid, clave=CLAVE) -> str`, `crear_rowino(ruta, usuarios)`, `servicio(tmp_path, monkeypatch)` (gestor de contexto que da un `TestClient`), `entrar(cliente, uid)`, `poner_reloj(monkeypatch, ahora=T0) -> Reloj` con `.pasar(**kwargs)`.
  - Fixture `cliente` en `tests/conftest.py`, construida sobre `ayudas_web.servicio`.

Los estáticos van bajo una ruta con versión porque Cloudflare los guarda cuatro horas: así un despliegue nuevo se ve al momento sin tocar la caché de nadie.

- [ ] **Step 1: Instalar las dependencias y comprobar que entran en las dos versiones de Python**

Añadir las cuatro líneas con sus versiones exactas y correr `./venv/bin/python -m pip install -r requirements-dev.txt`.
Expected: instala sin compilar nada. Si alguna no tiene paquete para Python 3.14, parar e informar: no se cambia de versión por cuenta propia.

- [ ] **Step 2: Escribir las ayudas de prueba**

`tests/ayudas_web.py`:

```python
"""Lo que comparten las pruebas del servicio web."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from itsdangerous import URLSafeSerializer

import config
import db

CLAVE = "clave-de-prueba"
PUEBLO = 777
ESCRIBIR = {"X-Gachamon": "1"}
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
USUARIOS = ((1, "felipe", 0), (2, "ana", 0), (3, "bloqueada", 1))


def galleta(uid, clave: str = CLAVE) -> str:
    """La cookie de sesión tal como la firma Rowino."""
    return URLSafeSerializer(clave, salt="session").dumps({"uid": uid})


def crear_rowino(ruta, usuarios=USUARIOS) -> None:
    con = sqlite3.connect(ruta)
    con.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, "
        "blocked INTEGER NOT NULL DEFAULT 0)"
    )
    con.executemany("INSERT INTO users VALUES (?, ?, ?)", usuarios)
    con.commit()
    con.close()


class Reloj:
    def __init__(self, ahora: datetime) -> None:
        self.ahora = ahora

    def __call__(self) -> datetime:
        return self.ahora

    def pasar(self, **cuanto) -> None:
        self.ahora += timedelta(**cuanto)


def poner_reloj(monkeypatch, ahora: datetime = T0) -> Reloj:
    reloj = Reloj(ahora)
    monkeypatch.setattr(db, "ahora_utc", reloj)
    return reloj


@contextmanager
def servicio(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "juego.db")
    monkeypatch.setattr(config, "ROWINO_SECRET_KEY", CLAVE)
    monkeypatch.setattr(config, "RUTA_ROWINO_BD", tmp_path / "rowino.db")
    monkeypatch.setattr(config, "GUILD_WEB", PUEBLO)
    crear_rowino(tmp_path / "rowino.db")
    from web.app import crear_app

    with TestClient(crear_app()) as cliente:
        yield cliente


def entrar(cliente, uid: int) -> None:
    cliente.cookies.set("session", galleta(uid))
```

Y en `tests/conftest.py`:

```python
@pytest.fixture
def cliente(tmp_path, monkeypatch):
    import ayudas_web

    with ayudas_web.servicio(tmp_path, monkeypatch) as cliente:
        yield cliente
```

- [ ] **Step 3: Escribir las pruebas que fallan**

`tests/test_web_app.py`:

```python
import os
import subprocess
import sys
from pathlib import Path

import pytest

import db
import economia
from ayudas_web import T0

RAIZ = Path(__file__).resolve().parent.parent


def test_la_salud_contesta(cliente):
    respuesta = cliente.get("/gachamon/api/salud")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True}


@pytest.mark.parametrize("ruta", ["/gachamon", "/gachamon/"])
def test_la_portada_se_sirve_sin_cache_y_con_la_version_puesta(cliente, ruta):
    respuesta = cliente.get(ruta)
    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]
    assert respuesta.headers["cache-control"] == "no-cache"
    assert "__V__" not in respuesta.text
    assert cliente.app.state.version in respuesta.text


def test_los_estaticos_cuelgan_de_una_ruta_con_version(cliente):
    version = cliente.app.state.version
    assert len(version) >= 8 and set(version) <= set("0123456789abcdef")
    assert cliente.get(f"/gachamon/static/{version}/index.html").status_code == 200
    assert cliente.get("/gachamon/static/otra/index.html").status_code == 404


@pytest.mark.parametrize("ruta", [
    "/", "/api/salud", "/docs", "/openapi.json", "/gachamon/docs",
    "/gachamon/openapi.json", "/gachamones",
])
def test_fuera_de_lo_suyo_no_hay_nada(cliente, ruta):
    assert cliente.get(ruta).status_code == 404


def test_poner_al_dia_crea_la_base_y_se_puede_repetir(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "nueva.db")
    economia.poner_al_dia(T0)
    segunda = economia.poner_al_dia(T0)
    assert (segunda.personas, segunda.piezas, segunda.gemas) == (0, 0, 0)
    assert economia.saldos("u", "g").asciigems == 50


def test_arrancar_el_servicio_hace_la_devolucion(tmp_path, monkeypatch):
    import ayudas_web

    monkeypatch.setattr(db, "RUTA", tmp_path / "juego.db")
    db.inicializar()
    with db.conectar() as con:
        db.guardar_en_el_ropero_en(con, "u", "g", "tinte_rojo")
    with ayudas_web.servicio(tmp_path, monkeypatch):
        pass
    assert economia.saldos("u", "g").asciigems == 70
    assert db.ropero("u", "g") == frozenset()


def test_el_bot_arranca_por_el_mismo_camino():
    fuente = (RAIZ / "bot.py").read_text(encoding="utf-8")
    assert "economia.poner_al_dia(" in fuente
    assert "db.inicializar()" not in fuente
    assert "devolver_cosmeticos_retirados" not in fuente


def test_la_web_no_arrastra_discord(tmp_path):
    entorno = {**os.environ, "RUTA_BD": str(tmp_path / "no-existe" / "x.db")}
    orden = "import sys, web.app; sys.exit(1 if 'discord' in sys.modules else 0)"
    hecho = subprocess.run(
        [sys.executable, "-c", orden], cwd=RAIZ, env=entorno,
        capture_output=True, text=True,
    )
    assert hecho.returncode == 0, hecho.stderr
```

- [ ] **Step 4: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_app.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'web'` o `AttributeError` de `config.ROWINO_SECRET_KEY`.

- [ ] **Step 5: Implementar**

`economia.poner_al_dia`, las dos variables de `config.py` (con su comentario en `.env.ejemplo`: la clave es la misma `SECRET_KEY` de Rowino y nunca se escribe en el repositorio), `web/app.py` como dice Interfaces y un `web/static/index.html` mínimo que ya lleve `__V__` en la ruta de su hoja de estilo o de su guion, aunque todavía no existan.

`web/app.py` no puede hacer nada al importarse salvo crear la app: la prueba `test_la_web_no_arrastra_discord` lo importa con una base que no existe, así que el arranque de verdad vive en el ciclo de vida de FastAPI y no en el cuerpo del módulo.

`bot.py`: `setup_hook` pasa a llamar a `economia.poner_al_dia(db.ahora_utc())` en lugar de sus dos llamadas, con las mismas dos líneas de registro.

- [ ] **Step 6: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_app.py tests/test_carga.py -q`
Expected: PASS.

- [ ] **Step 7: Anotar los invariantes en `AGENTS.md`**

Sección nueva «La web», tras «Límites de arquitectura»:

```markdown
## La web

- `web/` es otro adaptador fino, como los cogs: traduce peticiones y presenta resultados. No importa `discord` ni nada que lo importe.
- El servicio web no guarda estado del juego en memoria: lo que cambie el bot tiene que verse en la siguiente petición.
- Quién eres sale sólo de la cookie de sesión de Rowino. Ninguna ruta acepta un identificador de persona.
- El bot y la web arrancan por `economia.poner_al_dia`, y nadie más prepara la base.
```

- [ ] **Step 8: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): el esqueleto del servicio y un arranque común con el bot"
```

---

### Task 2: La sesión de Rowino

**Files:**
- Create: `web/sesion.py`
- Modify: `web/app.py` — ruta `GET /gachamon/api/sesion`
- Test: `tests/test_web_sesion.py`

**Interfaces:**
- Consumes: `config.ROWINO_SECRET_KEY`, `config.RUTA_ROWINO_BD`, `tests/ayudas_web.py` (tarea 1).
- Produces, en `web/sesion.py`:
  - `class Persona` — dataclass congelada: `rowino_uid: int`, `usuario: str`.
  - `problema(estado: int, clave: str, mensaje: str) -> HTTPException` — la única forma de contestar un error en todo el servicio.
  - `leer_cookie(valor: str | None) -> int | None` — el `uid` de una cookie firmada por Rowino (`URLSafeSerializer(clave, salt="session")`, cuerpo `{"uid": <entero>}`). `None` si falta, está manipulada, no trae un entero positivo, o no hay clave configurada.
  - `buscar_persona(rowino_uid: int) -> Persona | None` — lee la tabla `users` de `rowino.db` **abierta en modo de sólo lectura**. `None` si no existe, si `blocked` no es 0, o si la base no se puede abrir.
  - `persona_actual(request: Request) -> Persona` — dependencia de FastAPI. Sin persona: 401, clave `sin_sesion`.
  - `con_cabecera(request: Request) -> None` — dependencia para toda ruta que cambie algo. Sin `X-Gachamon: 1`: 403, clave `sin_cabecera`.
  - `GET /gachamon/api/sesion` → `{"usuario": "<nombre>"}`.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_web_sesion.py`:

```python
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from itsdangerous import URLSafeSerializer

import config
from ayudas_web import CLAVE, ESCRIBIR, entrar, galleta
from web import sesion

RUTA = "/gachamon/api/sesion"


def firmar(cuerpo) -> str:
    return URLSafeSerializer(CLAVE, salt="session").dumps(cuerpo)


def test_sin_cookie_no_hay_sesion(cliente):
    respuesta = cliente.get(RUTA)
    assert respuesta.status_code == 401
    assert respuesta.json()["detail"]["clave"] == "sin_sesion"
    assert respuesta.json()["detail"]["mensaje"]


def test_con_la_cookie_de_rowino_se_entra(cliente):
    entrar(cliente, 1)
    assert cliente.get(RUTA).json() == {"usuario": "felipe"}


@pytest.mark.parametrize("valor", [
    "", "basura", galleta(1, clave="otra-clave"), galleta(1)[:-2] + "xx",
    URLSafeSerializer(CLAVE, salt="otra-sal").dumps({"uid": 1}),
])
def test_una_cookie_que_no_firmo_rowino_no_vale(cliente, valor):
    cliente.cookies.set("session", valor)
    assert cliente.get(RUTA).status_code == 401


@pytest.mark.parametrize("cuerpo", [
    {"otro": 1}, {"uid": "1"}, {"uid": None}, {"uid": -1}, {"uid": 0},
    {"uid": True}, {"uid": 1.5}, [1], "1", 1,
])
def test_bien_firmada_pero_sin_un_uid_entero_tampoco(cliente, cuerpo):
    cliente.cookies.set("session", firmar(cuerpo))
    assert cliente.get(RUTA).status_code == 401


def test_una_cuenta_bloqueada_no_entra(cliente):
    entrar(cliente, 3)
    assert cliente.get(RUTA).status_code == 401


def test_una_cuenta_que_ya_no_existe_no_entra(cliente):
    entrar(cliente, 99)
    assert cliente.get(RUTA).status_code == 401


def test_sin_clave_configurada_no_entra_nadie(cliente, monkeypatch):
    monkeypatch.setattr(config, "ROWINO_SECRET_KEY", "")
    entrar(cliente, 1)
    assert cliente.get(RUTA).status_code == 401
    assert sesion.leer_cookie(galleta(1)) is None
    assert sesion.leer_cookie("lo-que-sea") is None


def test_si_falta_la_base_de_rowino_no_entra_nadie_y_no_se_crea(cliente, monkeypatch, tmp_path):
    fantasma = tmp_path / "no-existe" / "rowino.db"
    monkeypatch.setattr(config, "RUTA_ROWINO_BD", fantasma)
    entrar(cliente, 1)
    assert cliente.get(RUTA).status_code == 401
    assert not fantasma.exists() and not fantasma.parent.exists()


def test_la_base_de_rowino_solo_se_lee(cliente, tmp_path):
    antes = (tmp_path / "rowino.db").read_bytes()
    entrar(cliente, 1)
    for _ in range(3):
        cliente.get(RUTA)
    assert (tmp_path / "rowino.db").read_bytes() == antes
    assert sorted(p.name for p in tmp_path.glob("rowino.db*")) == ["rowino.db"]


def test_una_cuenta_bloqueada_despues_deja_de_entrar_en_la_siguiente_peticion(cliente, tmp_path):
    import sqlite3

    entrar(cliente, 1)
    assert cliente.get(RUTA).status_code == 200
    con = sqlite3.connect(tmp_path / "rowino.db")
    con.execute("UPDATE users SET blocked = 1 WHERE id = 1")
    con.commit()
    con.close()
    assert cliente.get(RUTA).status_code == 401


def test_escribir_pide_la_cabecera():
    app = FastAPI()

    @app.post("/x", dependencies=[Depends(sesion.con_cabecera)])
    def x():
        return {"ok": True}

    with TestClient(app) as c:
        sin = c.post("/x")
        assert sin.status_code == 403
        assert sin.json()["detail"]["clave"] == "sin_cabecera"
        assert c.post("/x", headers={"X-Gachamon": "0"}).status_code == 403
        assert c.post("/x", headers=ESCRIBIR).json() == {"ok": True}
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_sesion.py -q`
Expected: FAIL — `ImportError: cannot import name 'sesion' from 'web'`.

- [ ] **Step 3: Implementar `web/sesion.py` y la ruta**

La base de Rowino se abre con una dirección `file:…?mode=ro` y `uri=True`, una conexión por consulta, que se cierra antes de volver. No se guarda nada entre peticiones: así una cuenta bloqueada deja de entrar en la siguiente. `True` no cuenta como entero aunque Python diga que lo es. Sin clave configurada, `leer_cookie` devuelve `None` **antes de intentar verificar nada**: una clave vacía es una clave que cualquiera conoce.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_sesion.py -q`
Expected: PASS, 24 passed.

- [ ] **Step 5: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): se entra con la sesión de Rowino"
```

---

### Task 3: La cuenta: empezar o vincular

**Files:**
- Create: `web/cuenta.py`
- Modify: `web/app.py` — incluir el router
- Modify: `db.py` — `tiene_gachamones`
- Test: `tests/test_web_cuenta.py`

**Interfaces:**
- Consumes: `sesion.persona_actual`, `sesion.con_cabecera`, `sesion.problema` (tarea 2); `db.cuenta_web`, `db.crear_identidad_web`, `db.pedir_codigo_de_vinculo`, `db.canjear_codigo_de_vinculo`, `vinculo.NoSePuede`, `vinculo.MINUTOS_DE_VIDA`, `config.GUILD_WEB` (plan 1).
- Produces:
  - `db.tiene_gachamones(usuario_id: str, guild_id: str) -> bool` — cualquier fila en `criaturas`, viva o muerta. Versión pública de la privada que ya usa la vinculación.
  - `class Jugador` en `web/cuenta.py` — dataclass congelada: `persona: Persona`, `usuario_id: str`, `guild_id: str`, `vinculada: bool`.
  - `jugador_actual(persona = Depends(persona_actual)) -> Jugador` — dependencia. Sin fila en `cuentas_web`: 409, clave `sin_cuenta`.
  - `GET /gachamon/api/cuenta` → `{"usuario": str, "estado": "nueva" | "web" | "vinculada", "tiene_gachamones": bool}`.
  - `POST /gachamon/api/cuenta/empezar` → el mismo cuerpo. Crea la identidad web si la cuenta es nueva; si ya tiene identidad, no cambia nada.
  - `POST /gachamon/api/cuenta/codigo` → `{"codigo": str, "minutos": 10}`. 409 con clave `ya_vinculada` o `con_gachamones`.
  - Las dos de `POST` contestan 503, clave `sin_pueblo`, si `config.GUILD_WEB` es 0.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_web_cuenta.py`:

```python
import config
import db
import identidad
from ayudas_web import ESCRIBIR, PUEBLO, T0, entrar, poner_reloj

CUENTA = "/gachamon/api/cuenta"
STATS = (10, 10, 10, 10)
ANA_DISCORD = "222222222222222222"


def test_sin_sesion_no_hay_cuenta(cliente):
    assert cliente.get(CUENTA).status_code == 401
    assert cliente.post(f"{CUENTA}/empezar", headers=ESCRIBIR).status_code == 401


def test_una_cuenta_que_nunca_entro_es_nueva(cliente):
    entrar(cliente, 1)
    assert cliente.get(CUENTA).json() == {
        "usuario": "felipe", "estado": "nueva", "tiene_gachamones": False,
    }


def test_empezar_le_da_una_identidad_web(cliente):
    entrar(cliente, 1)
    respuesta = cliente.post(f"{CUENTA}/empezar", headers=ESCRIBIR)
    assert respuesta.json()["estado"] == "web"
    assert db.cuenta_web(1) == db.CuentaWeb(1, identidad.de_cuenta_web(1), str(PUEBLO), False)
    assert cliente.post(f"{CUENTA}/empezar", headers=ESCRIBIR).json()["estado"] == "web"


def test_empezar_y_pedir_codigo_piden_la_cabecera(cliente):
    entrar(cliente, 1)
    assert cliente.post(f"{CUENTA}/empezar").status_code == 403
    assert cliente.post(f"{CUENTA}/codigo").status_code == 403
    assert db.cuenta_web(1) is None


def test_vincular_de_punta_a_punta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    entrar(cliente, 2)
    pedido = cliente.post(f"{CUENTA}/codigo", headers=ESCRIBIR).json()
    assert pedido["minutos"] == 10 and len(pedido["codigo"]) == 8
    db.crear(ANA_DISCORD, str(PUEBLO), "pollito", "Pelusa", STATS, T0)

    assert db.canjear_codigo_de_vinculo(pedido["codigo"], ANA_DISCORD, str(PUEBLO), T0) == "ok"

    assert cliente.get(CUENTA).json() == {
        "usuario": "ana", "estado": "vinculada", "tiene_gachamones": True,
    }


def test_empezar_no_deshace_un_vinculo(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    entrar(cliente, 2)
    codigo = cliente.post(f"{CUENTA}/codigo", headers=ESCRIBIR).json()["codigo"]
    db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, str(PUEBLO), T0)
    assert cliente.post(f"{CUENTA}/empezar", headers=ESCRIBIR).json()["estado"] == "vinculada"
    assert db.cuenta_web(2).usuario_id == ANA_DISCORD


def test_una_cuenta_vinculada_no_puede_pedir_otro_codigo(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    entrar(cliente, 2)
    codigo = cliente.post(f"{CUENTA}/codigo", headers=ESCRIBIR).json()["codigo"]
    db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, str(PUEBLO), T0)
    respuesta = cliente.post(f"{CUENTA}/codigo", headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["clave"] == "ya_vinculada"


def test_con_gachamones_en_la_web_ya_no_se_puede_vincular(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    entrar(cliente, 1)
    cliente.post(f"{CUENTA}/empezar", headers=ESCRIBIR)
    db.crear(identidad.de_cuenta_web(1), str(PUEBLO), "pollito", "Pelusa", STATS, T0)
    assert cliente.get(CUENTA).json()["tiene_gachamones"] is True
    respuesta = cliente.post(f"{CUENTA}/codigo", headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["clave"] == "con_gachamones"
    assert respuesta.json()["detail"]["mensaje"]


def test_sin_pueblo_configurado_no_se_puede_empezar(cliente, monkeypatch):
    monkeypatch.setattr(config, "GUILD_WEB", 0)
    entrar(cliente, 1)
    for ruta in ("empezar", "codigo"):
        respuesta = cliente.post(f"{CUENTA}/{ruta}", headers=ESCRIBIR)
        assert respuesta.status_code == 503
        assert respuesta.json()["detail"]["clave"] == "sin_pueblo"
    assert db.cuenta_web(1) is None


def test_cada_cuenta_ve_solo_lo_suyo(cliente):
    entrar(cliente, 1)
    cliente.post(f"{CUENTA}/empezar", headers=ESCRIBIR)
    entrar(cliente, 2)
    assert cliente.get(CUENTA).json()["estado"] == "nueva"


def test_si_el_codigo_nuevo_ya_existe_se_saca_otro_y_no_se_pisa_el_ajeno(cliente, monkeypatch):
    import vinculo

    poner_reloj(monkeypatch)
    salen = iter(["AAAAAAAA", "AAAAAAAA", "BBBBBBBB"])
    monkeypatch.setattr(vinculo, "nuevo_codigo", lambda rng=None: next(salen))
    entrar(cliente, 1)
    primero = cliente.post(f"{CUENTA}/codigo", headers=ESCRIBIR).json()["codigo"]
    entrar(cliente, 2)
    segundo = cliente.post(f"{CUENTA}/codigo", headers=ESCRIBIR).json()["codigo"]
    assert (primero, segundo) == ("AAAAAAAA", "BBBBBBBB")
    assert db.canjear_codigo_de_vinculo(primero, "111111111111111111", str(PUEBLO), T0) == "ok"
    assert db.cuenta_web(1).usuario_id == "111111111111111111" and db.cuenta_web(2) is None
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_cuenta.py -q`
Expected: FAIL — 404 en `/gachamon/api/cuenta`.

- [ ] **Step 3: Implementar `db.tiene_gachamones`, `web/cuenta.py` y colgar el router**

Los mensajes de `ya_vinculada` y `con_gachamones` los lee un jugador: el segundo tiene que explicar que ya empezó a jugar aquí y que dos planteles no se juntan.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_cuenta.py tests/test_vinculo.py -q`
Expected: PASS.

- [ ] **Step 5: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): empezar de cero o pedir el código para vincular Discord"
```

---

### Task 4: El avatar

**Files:**
- Create: `avatar.py`
- Modify: `db.py` — tabla `avatares`, `guardar_avatar`, `avatar_de`
- Modify: `web/cuenta.py` — rutas del avatar
- Modify: `tests/ayudas_web.py` — `alta`
- Modify: `AGENTS.md`
- Test: `tests/test_avatar.py`, `tests/test_web_avatar.py`

**Interfaces:**
- Consumes: `sim.normalizar_nombre`, `esp.MACHO`, `esp.HEMBRA`; `jugador_actual`, `con_cabecera` (tareas 2 y 3).
- Produces, en `avatar.py` (puro):
  - `class Opcion` — dataclass congelada: `clave: str`, `nombre: str`.
  - Los catálogos, como tuplas de `Opcion`, con estas claves y en este orden:
    - `GENEROS`: `esp.MACHO` («Masculino»), `esp.HEMBRA` («Femenino»).
    - `PIELES`: `clara`, `media`, `tostada`, `oscura`.
    - `PELOS`: `corto`, `largo`, `rizado`, `coleta`, `rapado`.
    - `COLORES_DE_PELO`: `negro`, `castano` («Castaño»), `rubio`, `rojo` («Pelirrojo»), `cano`, `azul`.
    - `ROPAS`: `poleron` («Polerón»), `camisa`, `vestido`, `overol`.
  - `class Avatar` — dataclass congelada: `nombre`, `genero`, `piel`, `pelo`, `color_de_pelo`, `ropa`, todos `str`.
  - `crear(nombre, genero, piel, pelo, color_de_pelo, ropa) -> Avatar` — normaliza el nombre con `sim.normalizar_nombre` y exige que cada opción esté en su catálogo. `ValueError` con una frase para el jugador.
  - `opciones() -> dict[str, tuple[Opcion, ...]]` — claves `generos`, `pieles`, `pelos`, `colores_de_pelo`, `ropas`.
- Produces, en `db.py`:
  - Tabla `avatares`: `usuario_id TEXT NOT NULL`, `guild_id TEXT NOT NULL`, `nombre`, `genero`, `piel`, `pelo`, `color_de_pelo`, `ropa` (todos `TEXT NOT NULL`), `actualizado_en TEXT NOT NULL`, clave primaria `(usuario_id, guild_id)`.
  - `guardar_avatar(usuario_id, guild_id, avatar: avatar.Avatar, ahora) -> None` — crea o reemplaza.
  - `avatar_de(usuario_id, guild_id) -> avatar.Avatar | None`
- Produces, en la web:
  - `GET /gachamon/api/avatar/opciones` → `{"generos": [{"clave": …, "nombre": …}, …], "pieles": […], "pelos": […], "colores_de_pelo": […], "ropas": […]}`. Pide sesión, no pide cuenta.
  - `PUT /gachamon/api/avatar` — cuerpo con los seis campos. 200 con el avatar guardado; 422, clave `avatar`, con la frase del `ValueError`; 409 `sin_cuenta` si aún no eligió empezar o vincular.
  - `ayudas_web.alta(cliente, uid=1, nombre="Feli") -> None` — entra, empieza y guarda un avatar válido.

El avatar es de la identidad, no de la cuenta: quien vincula su Discord tiene un avatar para esa identidad.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_avatar.py`:

```python
import pytest

import avatar
import db
import especies as esp
from ayudas_web import T0

BUENO = dict(nombre="Feli", genero=esp.MACHO, piel="media", pelo="corto",
             color_de_pelo="castano", ropa="poleron")


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "avatar.db")
    db.inicializar()


def test_los_catalogos_son_los_acordados():
    claves = {nombre: tuple(o.clave for o in lista) for nombre, lista in avatar.opciones().items()}
    assert claves == {
        "generos": (esp.MACHO, esp.HEMBRA),
        "pieles": ("clara", "media", "tostada", "oscura"),
        "pelos": ("corto", "largo", "rizado", "coleta", "rapado"),
        "colores_de_pelo": ("negro", "castano", "rubio", "rojo", "cano", "azul"),
        "ropas": ("poleron", "camisa", "vestido", "overol"),
    }
    assert all(o.nombre and o.nombre[0].isupper() for lista in avatar.opciones().values() for o in lista)


def test_un_avatar_bien_hecho_se_crea_y_normaliza_el_nombre():
    hecho = avatar.crear(**{**BUENO, "nombre": "  Feli   Pe  "})
    assert hecho == avatar.Avatar("Feli Pe", esp.MACHO, "media", "corto", "castano", "poleron")


@pytest.mark.parametrize("campo, valor", [
    ("nombre", ""), ("nombre", "   "), ("nombre", "<b>Feli</b>"), ("nombre", "Feli🙂"),
    ("nombre", "x" * 25), ("genero", "otro"), ("piel", "verde"), ("pelo", "cresta"),
    ("color_de_pelo", "castaño"), ("ropa", "armadura"), ("piel", ""),
])
def test_lo_que_no_vale_se_rechaza_con_una_frase(campo, valor):
    with pytest.raises(ValueError) as error:
        avatar.crear(**{**BUENO, campo: valor})
    assert str(error.value).strip()


def test_se_guarda_se_lee_y_se_puede_cambiar():
    assert db.avatar_de("u", "g") is None
    db.guardar_avatar("u", "g", avatar.crear(**BUENO), T0)
    assert db.avatar_de("u", "g") == avatar.crear(**BUENO)
    db.guardar_avatar("u", "g", avatar.crear(**{**BUENO, "ropa": "overol"}), T0)
    assert db.avatar_de("u", "g").ropa == "overol"
    assert db.avatar_de("otro", "g") is None and db.avatar_de("u", "otro") is None
```

`tests/test_web_avatar.py`:

```python
import db
import identidad
from ayudas_web import ESCRIBIR, PUEBLO, entrar

AVATAR = "/gachamon/api/avatar"
BUENO = {"nombre": "Feli", "genero": "macho", "piel": "media", "pelo": "corto",
         "color_de_pelo": "castano", "ropa": "poleron"}


def empezar(cliente, uid=1):
    entrar(cliente, uid)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)


def test_las_opciones_se_piden_con_sesion(cliente):
    assert cliente.get(f"{AVATAR}/opciones").status_code == 401
    entrar(cliente, 1)
    opciones = cliente.get(f"{AVATAR}/opciones").json()
    assert [o["clave"] for o in opciones["pieles"]] == ["clara", "media", "tostada", "oscura"]
    assert opciones["generos"][0] == {"clave": "macho", "nombre": "Masculino"}


def test_guardar_el_avatar(cliente):
    empezar(cliente)
    respuesta = cliente.put(AVATAR, json=BUENO, headers=ESCRIBIR)
    assert respuesta.status_code == 200 and respuesta.json() == BUENO
    assert db.avatar_de(identidad.de_cuenta_web(1), str(PUEBLO)).nombre == "Feli"


def test_sin_haber_empezado_no_hay_donde_guardarlo(cliente):
    entrar(cliente, 1)
    respuesta = cliente.put(AVATAR, json=BUENO, headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["clave"] == "sin_cuenta"


def test_un_avatar_que_no_vale_vuelve_con_su_frase(cliente):
    empezar(cliente)
    respuesta = cliente.put(AVATAR, json={**BUENO, "nombre": "<script>"}, headers=ESCRIBIR)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["clave"] == "avatar"
    assert "letras" in respuesta.json()["detail"]["mensaje"]


def test_un_cuerpo_incompleto_tambien_vuelve_con_nuestra_forma_de_error(cliente):
    empezar(cliente)
    respuesta = cliente.put(AVATAR, json={"nombre": "Feli"}, headers=ESCRIBIR)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["clave"] == "avatar"


def test_guardar_pide_la_cabecera(cliente):
    empezar(cliente)
    assert cliente.put(AVATAR, json=BUENO).status_code == 403


def test_el_avatar_es_de_cada_cual(cliente):
    empezar(cliente, 1)
    cliente.put(AVATAR, json=BUENO, headers=ESCRIBIR)
    empezar(cliente, 2)
    cliente.put(AVATAR, json={**BUENO, "nombre": "Ana"}, headers=ESCRIBIR)
    assert db.avatar_de(identidad.de_cuenta_web(1), str(PUEBLO)).nombre == "Feli"
    assert db.avatar_de(identidad.de_cuenta_web(2), str(PUEBLO)).nombre == "Ana"
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_avatar.py tests/test_web_avatar.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'avatar'`.

- [ ] **Step 3: Implementar `avatar.py`, la tabla y las dos funciones de `db.py`, y las rutas**

El cuerpo incompleto o con tipos raros no puede salir con el error por defecto de FastAPI: todo error del servicio lleva `clave` y `mensaje`. Lo más simple es recibir el cuerpo como un diccionario y validar a mano.

- [ ] **Step 4: Añadir `alta` a `tests/ayudas_web.py`**

```python
AVATAR = {"nombre": "Feli", "genero": "macho", "piel": "media", "pelo": "corto",
          "color_de_pelo": "castano", "ropa": "poleron"}


def alta(cliente, uid: int = 1, nombre: str = "Feli") -> None:
    """Deja una cuenta con identidad web y avatar, lista para sacar su huevo."""
    entrar(cliente, uid)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    hecho = cliente.put("/gachamon/api/avatar", json={**AVATAR, "nombre": nombre}, headers=ESCRIBIR)
    assert hecho.status_code == 200, hecho.text
```

- [ ] **Step 5: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_avatar.py tests/test_web_avatar.py tests/test_textos.py -q`
Expected: PASS.

- [ ] **Step 6: Anotar el invariante en `AGENTS.md`**

```markdown
- El avatar es de la persona, no de un gachamon: sobrevive a todo su plantel.
```

- [ ] **Step 7: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(avatar): pelo, piel, ropa, nombre y género de quien juega"
```

---

### Task 5: La caricia, como regla del juego

**Files:**
- Modify: `simulacion.py` — `ACARICIAR`, `COOLDOWNS`, `EFECTO_CARICIA`, `aplicar_caricia`
- Modify: `db.py` — `ResultadoCaricia`, `acariciar`
- Modify: `AGENTS.md`
- Test: `tests/test_caricia.py`

**Interfaces:**
- Consumes: `db.criatura_activa_en`, `db._avanzar_en`, `db.espera_en`, `db.poner_cooldown_en`, `db._guardar`.
- Produces:
  - `sim.ACARICIAR = "acariciar"`; `sim.COOLDOWNS[sim.ACARICIAR] == timedelta(minutes=19)`; `sim.EFECTO_CARICIA = {"animo": 5}`. **No** entra en `sim.ACCIONES_DE_CUIDADO`.
  - `sim.aplicar_caricia(criatura) -> sim.ResultadoAccion` — sube el ánimo, con tope en 100. No da experiencia ni toca nada más. A una muerta, `ok=False`.
  - `db.ResultadoCaricia` — dataclass congelada: `ok: bool`, `criatura: sim.Criatura | None`, `espera: timedelta`.
  - `db.acariciar(usuario_id, guild_id, ahora) -> db.ResultadoCaricia` — todo bajo un `BEGIN IMMEDIATE`. Sin gachamon activo: `(False, None, 0)`. Antes de tiempo: `ok=False`, la criatura sin cambios y lo que falta. A tiempo: `ok=True`, la criatura ya acariciada y guardada, el enfriamiento puesto, y `espera` igual a los 19 minutos.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_caricia.py`:

```python
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import economia
import identidad
import simulacion as sim

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (10, 10, 10, 10)
ESPERA = timedelta(minutes=19)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "caricia.db")
    db.inicializar()


def nacer(usuario="u", animo=50.0, **mas):
    creada = db.crear(usuario, "g", "pollito", "Pelusa", STATS, T0, **mas)
    db.guardar(replace(creada, animo=animo))
    return creada


def test_son_cinco_de_animo_cada_diecinueve_minutos_y_no_es_un_cuidado():
    assert sim.EFECTO_CARICIA == {"animo": 5}
    assert sim.COOLDOWNS[sim.ACARICIAR] == ESPERA
    assert sim.ACARICIAR not in sim.ACCIONES_DE_CUIDADO


def test_acariciar_sube_el_animo_y_nada_mas():
    antes = replace(nacer(), animo=50.0)
    despues = sim.aplicar_caricia(antes).criatura
    assert despues.animo == 55.0
    assert replace(despues, animo=50.0) == antes


def test_el_animo_no_pasa_de_cien():
    assert sim.aplicar_caricia(replace(nacer(), animo=98.0)).criatura.animo == 100.0


def test_a_una_muerta_no_se_la_acaricia():
    muerta = replace(nacer(), muerta_en=T0, causa_muerte="hambre")
    resultado = sim.aplicar_caricia(muerta)
    assert not resultado.ok and resultado.criatura == muerta


def test_la_primera_caricia_cuenta_y_queda_guardada():
    nacer()
    resultado = db.acariciar("u", "g", T0)
    assert resultado.ok and resultado.espera == ESPERA
    assert resultado.criatura.animo == 55.0
    assert db.criatura_activa("u", "g").animo == 55.0


def test_la_segunda_antes_de_tiempo_no_hace_nada_y_dice_cuanto_falta():
    nacer()
    db.acariciar("u", "g", T0)
    poco_despues = T0 + timedelta(minutes=5)
    segunda = db.acariciar("u", "g", poco_despues)
    assert not segunda.ok
    assert segunda.espera == timedelta(minutes=14)
    assert db.criatura_activa("u", "g").animo == 55.0


def test_a_los_diecinueve_minutos_vuelve_a_contar():
    nacer()
    db.acariciar("u", "g", T0)
    assert not db.acariciar("u", "g", T0 + ESPERA - timedelta(seconds=1)).ok
    assert db.acariciar("u", "g", T0 + ESPERA).ok


def test_no_da_experiencia_ni_monedas_ni_toca_el_tope():
    creada = nacer()
    db.acariciar("u", "g", T0)
    despues = db.criatura_activa("u", "g")
    assert (despues.xp, despues.nivel) == (creada.xp, creada.nivel)
    assert economia.saldos("u", "g") == economia.Saldos(50, 50)
    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM operaciones_economia").fetchone()[0] == 0


def test_el_enfriamiento_es_de_cada_gachamon():
    nacer()
    otro = db.crear("u", "g", "pulpo", "Tinta", STATS, T0, activa=False)
    db.acariciar("u", "g", T0)
    assert db.activar(otro.id, "u", "g", T0)
    assert db.acariciar("u", "g", T0).ok


def test_sin_gachamon_no_hay_a_quien():
    assert db.acariciar("nadie", "g", T0) == db.ResultadoCaricia(False, None, timedelta(0))


def test_no_revive_ni_acaricia_a_quien_ya_murio_de_hambre():
    nacer()
    mucho_despues = T0 + timedelta(days=5)
    resultado = db.acariciar("u", "g", mucho_despues)
    assert not resultado.ok
    assert db.criatura_activa("u", "g") is None


def test_la_de_una_identidad_web_se_acaricia_igual():
    web = identidad.de_cuenta_web(12)
    nacer(usuario=web)
    assert db.acariciar(web, "g", T0).ok


def test_dos_caricias_a_la_vez_cuentan_una():
    nacer()
    with ThreadPoolExecutor(max_workers=2) as hilos:
        resultados = list(hilos.map(lambda _: db.acariciar("u", "g", T0), range(2)))
    assert sorted(r.ok for r in resultados) == [False, True]
    assert db.criatura_activa("u", "g").animo == 55.0
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_caricia.py -q`
Expected: FAIL — `AttributeError: module 'simulacion' has no attribute 'EFECTO_CARICIA'`.

- [ ] **Step 3: Implementar en `simulacion.py` y en `db.py`**

En `db.acariciar` la criatura se avanza hasta `ahora` antes de nada, con `_avanzar_en`, igual que hace `economia.ejecutar_cuidado`. Si al avanzar resulta que murió, se guarda muerta y se contesta `ok=False`: la caricia no es el sitio para sacar al relevo de la incubadora, eso lo hace quien lee el estado (tarea 7).

El comentario de `COOLDOWNS` ya explica la regla de los primos; añadirle por qué la caricia son 19 y no 20.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_caricia.py tests/test_simulacion.py -q`
Expected: PASS. La prueba que vigila que ningún enfriamiento sea múltiplo de otro sigue en verde.

- [ ] **Step 5: Anotar el invariante en `AGENTS.md`**

```markdown
- Acariciar no es un cuidado: no da experiencia ni monedas, no cuenta para ningún tope y tiene su propio enfriamiento, que es de cada gachamon.
```

- [ ] **Step 6: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(caricia): acariciar sube el ánimo y tiene su propio enfriamiento"
```

---

### Task 6: Los globos

Lo que el gachamon dice por su cuenta. Frases escritas, no inteligencia artificial (diseño, 5.7).

**Files:**
- Create: `globos.py`
- Modify: `AGENTS.md`
- Test: `tests/test_globos.py`

**Interfaces:**
- Consumes: `esp.concordar`, `esp.ESPECIES`, `esp.MACHO`, `esp.HEMBRA`.
- Produces, en `globos.py` (puro):
  - `UMBRAL_NECESIDAD = 40.0`
  - `NECESIDAD = "necesidad"`, `SUELTA = "suelta"`
  - `class Globo` — dataclass congelada: `tipo: str`, `texto: str`.
  - `COMUNES: dict[str, tuple[str, ...]]` — claves `desfallecido`, `hambre`, `sucio`, `aburrido` y `suelta`. Al menos dos frases en cada una; en `suelta`, al menos cuatro, entre ellas «¿Cómo estás?».
  - `PROPIAS: dict[str, dict[str, tuple[str, ...]]]` — por clave de especie, las mismas claves. Lo que una especie tenga ahí **manda** sobre lo común para esa clave. Viene con las cinco claves completas para `pollito`, cuyas frases llevan todas «pío».
  - `de(criatura: sim.Criatura) -> tuple[Globo, ...]` — todo lo que puede decir ahora, ya concordado con su género. Primero las de necesidad y después las sueltas. Con la comida en 0, las de `desfallecido` van en lugar de las de `hambre`. A una muerta, tupla vacía.
  - `elegir(globos: Sequence[Globo], anterior: str | None, rng: random.Random) -> Globo | None` — si hay alguna de necesidad, elige entre ellas; si no, entre las sueltas. No repite `anterior` mientras haya otra candidata.

Necesidades y su barra: comida por debajo de 40 → `hambre` (o `desfallecido` si está en 0); aseo por debajo de 40 → `sucio`; ánimo por debajo de 40 → `aburrido`.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_globos.py`:

```python
import random
from dataclasses import replace
from datetime import datetime, timezone

import pytest

import especies as esp
import globos
import simulacion as sim

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
CLAVES = ("desfallecido", "hambre", "sucio", "aburrido", "suelta")


def criatura(especie="pulpo", genero=esp.HEMBRA, **barras) -> sim.Criatura:
    base = sim.Criatura(id=1, usuario_id="u", guild_id="g", especie=especie,
                        nombre="Tinta", nacida_en=T0, actualizada_en=T0, genero=genero)
    return replace(base, **barras)


def textos(c, tipo=None):
    return [g.texto for g in globos.de(c) if tipo in (None, g.tipo)]


def test_lo_comun_trae_frases_para_todo():
    assert set(globos.COMUNES) == set(CLAVES)
    assert all(len(globos.COMUNES[c]) >= 2 for c in CLAVES)
    assert len(globos.COMUNES["suelta"]) >= 4
    assert "¿Cómo estás?" in globos.COMUNES["suelta"]


def test_contenta_y_cuidada_solo_charla():
    c = criatura(hambre=90, animo=90, limpieza=90)
    assert textos(c, globos.NECESIDAD) == []
    assert set(textos(c)) == set(esp.concordar(f, esp.HEMBRA) for f in globos.COMUNES["suelta"])


@pytest.mark.parametrize("barras, clave", [
    (dict(hambre=39.9), "hambre"), (dict(limpieza=39.9), "sucio"), (dict(animo=39.9), "aburrido"),
])
def test_por_debajo_de_cuarenta_pide_lo_que_le_falta(barras, clave):
    pedidas = textos(criatura(**barras), globos.NECESIDAD)
    assert set(pedidas) == set(esp.concordar(f, esp.HEMBRA) for f in globos.COMUNES[clave])


def test_justo_en_cuarenta_todavia_no_pide():
    assert textos(criatura(hambre=40.0, limpieza=40.0, animo=40.0), globos.NECESIDAD) == []


def test_con_la_comida_en_cero_esta_desfallecida_y_no_solo_con_hambre():
    pedidas = set(textos(criatura(hambre=0.0), globos.NECESIDAD))
    assert pedidas == set(esp.concordar(f, esp.HEMBRA) for f in globos.COMUNES["desfallecido"])


def test_las_necesidades_van_antes_que_la_charla():
    tipos = [g.tipo for g in globos.de(criatura(hambre=10, limpieza=10))]
    assert tipos == sorted(tipos, key=[globos.NECESIDAD, globos.SUELTA].index)
    assert globos.SUELTA in tipos


def test_una_muerta_no_dice_nada():
    assert globos.de(criatura(muerta_en=T0, causa_muerte="hambre")) == ()


def test_el_piollito_habla_a_su_manera_en_todo():
    assert set(globos.PROPIAS["pollito"]) == set(CLAVES)
    for barras in (dict(), dict(hambre=10), dict(hambre=0), dict(limpieza=10), dict(animo=10)):
        for texto in textos(criatura(especie="pollito", **barras)):
            assert "pío" in texto.lower(), texto


def test_lo_propio_manda_solo_en_la_clave_que_trae(monkeypatch):
    monkeypatch.setitem(globos.PROPIAS, "pulpo", {"sucio": ("Glub. Mis ocho brazos, pegajosos.",)})
    assert textos(criatura(limpieza=10), globos.NECESIDAD) == ["Glub. Mis ocho brazos, pegajosos."]
    assert set(textos(criatura(hambre=10), globos.NECESIDAD)) == set(
        esp.concordar(f, esp.HEMBRA) for f in globos.COMUNES["hambre"]
    )


@pytest.mark.parametrize("especie", sorted(esp.ESPECIES))
@pytest.mark.parametrize("genero", [esp.MACHO, esp.HEMBRA])
def test_ninguna_frase_llega_con_una_marca_sin_resolver(especie, genero):
    for barras in (dict(), dict(hambre=10, limpieza=10, animo=10), dict(hambre=0)):
        for globo in globos.de(criatura(especie=especie, genero=genero, **barras)):
            assert "{" not in globo.texto and "}" not in globo.texto, globo.texto
            assert 0 < len(globo.texto) <= 80


def test_macho_y_hembra_no_dicen_exactamente_lo_mismo():
    hembra = set(textos(criatura(genero=esp.HEMBRA, hambre=10, limpieza=10, animo=10)))
    macho = set(textos(criatura(genero=esp.MACHO, hambre=10, limpieza=10, animo=10)))
    assert hembra != macho


def test_elegir_prefiere_la_necesidad_y_no_se_repite():
    disponibles = globos.de(criatura(hambre=10))
    rng = random.Random(7)
    anterior = None
    for _ in range(30):
        elegido = globos.elegir(disponibles, anterior, rng)
        assert elegido.tipo == globos.NECESIDAD
        assert elegido.texto != anterior
        anterior = elegido.texto


def test_elegir_sin_nada_que_decir_o_con_una_sola_frase():
    assert globos.elegir((), None, random.Random(1)) is None
    unico = (globos.Globo(globos.SUELTA, "Hola."),)
    assert globos.elegir(unico, "Hola.", random.Random(1)) == unico[0]
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_globos.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'globos'`.

- [ ] **Step 3: Escribir `globos.py`**

Las frases son cortas —caben en un globo— y hablan en primera persona. Donde un adjetivo dependa del género va con su marca: «Estoy suci{o/a}.». La prueba de macho y hembra exige que al menos una frase de necesidad lleve marca. Ninguna frase anuncia algo que no esté pasando: nada de visitantes ni de ventanas, que son del proyecto de eventos.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_globos.py tests/test_textos.py -q`
Expected: PASS.

- [ ] **Step 5: Anotar el invariante en `AGENTS.md`**

```markdown
- Lo que el gachamon dice por su cuenta son frases escritas en `globos.py`, nunca una llamada a la IA, y un globo no anuncia nada que no esté pasando.
```

- [ ] **Step 6: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(globos): lo que el gachamon dice por su cuenta"
```

---

### Task 7: El estado

Una sola lectura que trae todo lo que la pantalla necesita. Es también quien se entera de las muertes.

**Files:**
- Modify: `db.py` — columna `difuntos_vistos_hasta` en `cuentas_web`, `activa_al_dia`, `difunto_pendiente`, `marcar_difuntos_vistos`
- Create: `web/estado.py`, `web/juego.py`
- Modify: `web/app.py` — incluir el router
- Test: `tests/test_web_estado.py`

**Interfaces:**
- Consumes: `Jugador`, `jugador_actual`, `con_cabecera`; `db.avatar_de`; `globos.de`; `sim.ACARICIAR`; `economia.saldos`; `db.hogar_leido`; `db.esperas`, `sim.puede_saltarse_espera`; `db.avanzar`, `db.guardar`, `db.ascender_de_la_incubadora`; `identidad.sin_aviso_de_hambre`.
- Produces, en `db.py`:
  - `activa_al_dia(usuario_id, guild_id, ahora) -> sim.Criatura | None` — la activa, viva y avanzada hasta `ahora`, **sin guardarla**. Si al avanzar resulta que murió, la guarda muerta, saca al relevo de la incubadora y devuelve a ese relevo, o `None` si no queda nadie. Llamarla dos veces, o desde dos procesos, deja un solo relevo.
  - Columna `cuentas_web.difuntos_vistos_hasta TEXT`, añadida por `MIGRACIONES_DE_TABLAS`.
  - `difunto_pendiente(rowino_uid: int) -> sim.Criatura | None` — el gachamon de esa cuenta muerto más recientemente, si murió después de `difuntos_vistos_hasta` (o, si esa columna está vacía, después de `creada_en`). `None` si no hay.
  - `marcar_difuntos_vistos(rowino_uid: int, ahora) -> None`
- Produces, en `web/estado.py`:
  - `ficha(criatura: sim.Criatura, ahora) -> dict` y `armar(jugador: Jugador, ahora) -> dict`.
- Produces, en la web:
  - `GET /gachamon/api/estado` → el estado, con esta forma exacta:

    ```json
    {
      "ahora": "2026-01-01T00:00:00+00:00",
      "persona": {"usuario": "felipe", "vinculada": false},
      "avatar": {"nombre": "Feli", "genero": "macho", "piel": "media", "pelo": "corto", "color_de_pelo": "castano", "ropa": "poleron"},
      "saldos": {"monedas": 50, "gemas": 50},
      "hogar": "refugio",
      "gachamon": {
        "id": 1, "nombre": "Pelusa", "espera_nombre": false,
        "especie": "pollito", "nombre_especie": "Piollito", "emoji": "🐥",
        "etapa": "bebe", "nombre_etapa": "cría", "nivel": 1, "genero": "hembra",
        "barras": {"comida": 100, "animo": 100, "aseo": 100},
        "cara": "feliz", "desfallecido": false,
        "retrato": "/gachamon/retrato/pollito/bebe/feliz/sin.png",
        "esperas": {"alimentar": 0, "jugar": 0, "entrenar": 0, "limpiar": 0, "acariciar": 0}
      },
      "difunto": null,
      "globos": [{"tipo": "suelta", "texto": "¿Cómo estás?"}]
    }
    ```
  - `POST /gachamon/api/difunto/visto` → 200 con el estado nuevo.

Reglas del estado:

- `avatar` y `gachamon` son `null` cuando no hay; `globos` es `[]` sin gachamon.
- Las barras son enteros de 0 a 100, redondeados; `comida` es `hambre` y `aseo` es `limpieza`.
- Las esperas son segundos enteros, redondeados hacia arriba. La de `alimentar` es 0 cuando `sim.puede_saltarse_espera` dice que puede.
- `espera_nombre` es cierto si el nombre está vacío o es igual al de su especie (tarea 8 lo usa).
- `desfallecido` es cierto con la comida en 0 y el gachamon vivo.
- `hogar` es `casas.PROPIA`, `casas.REFUGIO` o `casas.INTEMPERIE`: la situación **del gachamon activo** (`Hogar.estado_de(casa_id, ahora)`), o la de la persona si no tiene gachamon.
- `retrato` lleva `sin` cuando no tiene sombrero.
- `difunto` es `{"nombre", "nombre_especie", "dias"}` del que `db.difunto_pendiente` devuelva, con `dias` los días enteros que vivió: de `nacida_en` a `muerta_en`, que es cuando el hambre llegó a 0 y no cuando alguien miró.
- Leer el estado **no guarda el paso del tiempo** del gachamon: lo calcula y lo contesta. Sólo escribe cuando se entera de una muerte. (El monedero nace la primera vez que alguien mira su saldo, como ya pasa en el bot.)

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_web_estado.py`:

```python
from dataclasses import replace
from datetime import timedelta

import db
import especies as esp
import identidad
from ayudas_web import ESCRIBIR, PUEBLO, T0, alta, entrar, poner_reloj

ESTADO = "/gachamon/api/estado"
STATS = (10, 10, 10, 10)
G = str(PUEBLO)
YO = identidad.de_cuenta_web(1)
ANA_DISCORD = "222222222222222222"


def nace(usuario=YO, especie="pollito", nombre="Pelusa", ahora=T0, **mas):
    return db.crear(usuario, G, especie, nombre, STATS, ahora, **mas)


def test_sin_cuenta_no_hay_estado(cliente):
    assert cliente.get(ESTADO).status_code == 401
    entrar(cliente, 1)
    respuesta = cliente.get(ESTADO)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["clave"] == "sin_cuenta"


def test_recien_llegado_no_tiene_ni_avatar_ni_gachamon(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    entrar(cliente, 1)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    estado = cliente.get(ESTADO).json()
    assert estado["avatar"] is None and estado["gachamon"] is None
    assert estado["globos"] == [] and estado["difunto"] is None
    assert estado["saldos"] == {"monedas": 50, "gemas": 50}
    assert estado["persona"] == {"usuario": "felipe", "vinculada": False}
    assert estado["ahora"] == T0.isoformat()
    assert estado["hogar"] == "refugio"


def test_el_estado_completo_de_un_gachamon_recien_nacido(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    creado = nace(genero="hembra")
    estado = cliente.get(ESTADO).json()
    assert estado["avatar"]["nombre"] == "Feli"
    assert estado["gachamon"] == {
        "id": creado.id, "nombre": "Pelusa", "espera_nombre": False,
        "especie": "pollito", "nombre_especie": esp.ESPECIES["pollito"].nombre,
        "emoji": esp.ESPECIES["pollito"].emoji,
        "etapa": "bebe", "nombre_etapa": esp.nombre_etapa("bebe", "hembra"),
        "nivel": 1, "genero": "hembra",
        "barras": {"comida": 100, "animo": 100, "aseo": 100},
        "cara": "feliz", "desfallecido": False,
        "retrato": "/gachamon/retrato/pollito/bebe/feliz/sin.png",
        "esperas": {"alimentar": 0, "jugar": 0, "entrenar": 0, "limpiar": 0, "acariciar": 0},
    }
    assert estado["globos"] and all(g["tipo"] == "suelta" for g in estado["globos"])
    assert set(estado) == {"ahora", "persona", "avatar", "saldos", "hogar", "gachamon", "difunto", "globos"}


def test_las_barras_bajan_con_el_reloj_y_leer_no_guarda(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    creado = nace()
    reloj.pasar(hours=10)
    barras = cliente.get(ESTADO).json()["gachamon"]["barras"]
    assert barras["comida"] < 100 and barras["animo"] < 100 and barras["aseo"] < 100
    assert all(isinstance(v, int) for v in barras.values())
    assert db.por_id(creado.id).actualizada_en == T0


def test_el_que_espera_nombre_lo_dice(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    nace(nombre="Piollito")
    assert cliente.get(ESTADO).json()["gachamon"]["espera_nombre"] is True


def test_las_esperas_salen_en_segundos_y_la_de_alimentar_cede_con_hambre(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    creado = nace()
    for accion in ("alimentar", "jugar", "acariciar"):
        db.poner_cooldown(creado.id, accion, T0)
    reloj.pasar(minutes=4, seconds=30)
    esperas = cliente.get(ESTADO).json()["gachamon"]["esperas"]
    assert esperas == {"alimentar": 18 * 60 + 30, "jugar": 24 * 60 + 30,
                       "entrenar": 0, "limpiar": 0, "acariciar": 14 * 60 + 30}
    db.guardar(replace(db.por_id(creado.id), hambre=30.0, actualizada_en=reloj.ahora))
    assert cliente.get(ESTADO).json()["gachamon"]["esperas"]["alimentar"] == 0


def test_con_necesidades_los_globos_piden_primero(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    creado = nace()
    db.guardar(replace(creado, limpieza=10.0))
    tipos = [g["tipo"] for g in cliente.get(ESTADO).json()["globos"]]
    assert tipos[0] == "necesidad" and "suelta" in tipos


def test_el_de_una_cuenta_web_se_queda_desfallecido_y_vivo(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    nace()
    reloj.pasar(days=5)
    gachamon = cliente.get(ESTADO).json()["gachamon"]
    assert gachamon["barras"]["comida"] == 0 and gachamon["desfallecido"] is True
    assert gachamon["cara"] == "mal"


def test_el_de_una_cuenta_vinculada_muere_y_la_web_lo_cuenta_una_vez(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    entrar(cliente, 2)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, G, T0)
    muerto = nace(usuario=ANA_DISCORD, nombre="Viejo")
    relevo = nace(usuario=ANA_DISCORD, especie="pulpo", nombre="Tinta", activa=False)
    reloj.pasar(days=5)

    estado = cliente.get(ESTADO).json()
    # Vivió lo que aguanta sin comer con salud 10: 62 horas, o sea dos días enteros.
    assert estado["difunto"] == {
        "nombre": "Viejo", "nombre_especie": esp.ESPECIES["pollito"].nombre, "dias": 2,
    }
    assert estado["gachamon"]["id"] == relevo.id
    assert db.por_id(muerto.id).causa_muerte == "hambre"
    assert cliente.get(ESTADO).json()["difunto"]["nombre"] == "Viejo"

    visto = cliente.post("/gachamon/api/difunto/visto", headers=ESCRIBIR)
    assert visto.status_code == 200 and visto.json()["difunto"] is None
    assert cliente.get(ESTADO).json()["difunto"] is None


def test_una_muerte_que_proceso_el_bot_tambien_se_cuenta(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    entrar(cliente, 2)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, G, T0)
    muerto = nace(usuario=ANA_DISCORD, nombre="Viejo")
    reloj.pasar(days=5)
    db.guardar(db.avanzar(db.por_id(muerto.id), reloj.ahora))   # lo que hace el bucle del bot

    estado = cliente.get(ESTADO).json()
    assert estado["difunto"]["nombre"] == "Viejo" and estado["gachamon"] is None


def test_los_muertos_de_antes_de_tener_cuenta_no_se_cuentan(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    antiguo = nace(usuario=ANA_DISCORD, nombre="Antiguo")
    db.guardar(replace(antiguo, muerta_en=T0, causa_muerte="hambre"))
    reloj.pasar(days=30)
    entrar(cliente, 2)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, G, reloj.ahora)
    assert cliente.get(ESTADO).json()["difunto"] is None


def test_activa_al_dia_es_repetible(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "relevo.db")
    db.inicializar()
    nace(usuario=ANA_DISCORD, nombre="Viejo")
    primero = nace(usuario=ANA_DISCORD, especie="pulpo", nombre="Uno", activa=False)
    nace(usuario=ANA_DISCORD, especie="pulpo", nombre="Dos", activa=False)
    tarde = T0 + timedelta(days=5)
    assert db.activa_al_dia(ANA_DISCORD, G, tarde).id == primero.id
    assert db.activa_al_dia(ANA_DISCORD, G, tarde).id == primero.id
    activas = [c for c in db.plantel(ANA_DISCORD, G) if c.activa]
    assert [c.id for c in activas] == [primero.id]


def test_cada_cual_ve_su_estado(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente, 1)
    nace(usuario=YO, nombre="Mío")
    alta(cliente, 2, nombre="Ana")
    estado = cliente.get(ESTADO).json()
    assert estado["gachamon"] is None and estado["avatar"]["nombre"] == "Ana"
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_estado.py -q`
Expected: FAIL — 404 en `/gachamon/api/estado`.

- [ ] **Step 3: Implementar lo de `db.py`**

`activa_al_dia` hace lo mismo que ya hace el comando `/huevo` del bot cuando se encuentra una muerte: `avanzar`, y si no vive, `guardar` y `ascender_de_la_incubadora`. La diferencia es que ahora vive en un solo sitio.

- [ ] **Step 4: Implementar `web/estado.py`, `web/juego.py` y colgar el router**

`web/estado.py` no decide reglas: llama y traduce. Quien arma el estado resuelve la identidad a partir del `Jugador` y de nada más.

- [ ] **Step 5: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_estado.py tests/test_db.py tests/test_identidad.py -q`
Expected: PASS.

- [ ] **Step 6: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): el estado completo en una lectura, muertes incluidas"
```

---

### Task 8: Nacer: el huevo y el bautizo

**Files:**
- Create: `nacer.py`
- Modify: `cogs/mascota.py` — `HuevoView.romper` usa `nacer.romper_el_huevo`
- Modify: `web/juego.py` — rutas del huevo y del bautizo
- Modify: `tests/ayudas_web.py` — `con_gachamon`
- Test: `tests/test_nacer.py`, `tests/test_web_nacer.py`

**Interfaces:**
- Consumes: `esp.elegir_del_huevo`, `esp.tirar_stats_iniciales`, `esp.tirar_genero`, `per.tirar_caracter`, `db.crear`, `db.activa_al_dia`, `db.plantel`, `sim.normalizar_nombre`, `estado.armar`.
- Produces, en `nacer.py` (sin `discord`):
  - `class YaTieneGachamon(Exception)`
  - `class YaNoEsSuIdentidad(Exception)` — la identidad web con la que se pidió el huevo dejó de ser la de esa cuenta, porque se vinculó mientras tanto.
  - `class NoSePuedeBautizar(Exception)` — su texto es una frase para el jugador.
  - `espera_nombre(criatura: sim.Criatura) -> bool` — sin nombre, o con el de su especie. `web/estado.py` pasa a usar esta.
  - `romper_el_huevo(usuario_id, guild_id, ahora, rng: random.Random | None = None, canal_id: str | None = None) -> sim.Criatura` — sólo si no le queda ningún gachamon vivo. Nace con el nombre de su especie, provisional. `YaTieneGachamon` en cualquier otro caso, también si dos huevos llegan a la vez. Y `YaNoEsSuIdentidad` si `usuario_id` es una identidad web que ya no figura en `cuentas_web`: esa comprobación ocurre **dentro de la misma transacción que crea la criatura**, en `db.crear`, para que no pueda nacer un gachamon huérfano justo después de vincular.
  - `bautizar(usuario_id, guild_id, nombre: str, ahora) -> sim.Criatura` — le pone nombre a la activa de esa persona, sólo si `espera_nombre`. `ValueError` de `sim.normalizar_nombre` si el nombre no vale; `NoSePuedeBautizar` si no tiene gachamon o si ya tiene nombre.
- Produces, en la web:
  - `POST /gachamon/api/huevo` → 201 con el estado. 409 `sin_avatar` si aún no creó el avatar; 409 `ya_tienes`; 409 `cuenta_cambio` si la cuenta se vinculó mientras tanto (el cliente vuelve a preguntar quién es).
  - `POST /gachamon/api/bautizar` — cuerpo `{"nombre": str}`. 200 con el estado; 422 `nombre` con la frase; 409 `ya_bautizado` o `sin_gachamon`.
  - `ayudas_web.con_gachamon(cliente, uid=1, nombre="Pelusa") -> dict` — `alta`, huevo y bautizo; devuelve el estado.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_nacer.py`:

```python
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import especies as esp
import nacer

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "nacer.db")
    db.inicializar()


def test_del_huevo_sale_una_de_las_diez_con_nombre_provisional():
    nacida = nacer.romper_el_huevo("u", "g", T0, random.Random(3))
    especie = esp.ESPECIES[nacida.especie]
    assert especie.peso > 0
    assert nacida.nombre == especie.nombre and nacer.espera_nombre(nacida)
    assert nacida.activa and nacida.viva and nacida.nivel == 1
    assert db.criatura_activa("u", "g").id == nacida.id


def test_el_mismo_azar_da_el_mismo_gachamon():
    a = nacer.romper_el_huevo("a", "g", T0, random.Random(5))
    b = nacer.romper_el_huevo("b", "g", T0, random.Random(5))
    assert (a.especie, a.genero, a.caracter, a.base_fuerza, a.base_ingenio) == (
        b.especie, b.genero, b.caracter, b.base_fuerza, b.base_ingenio)


def test_el_huevo_es_solo_el_de_partida():
    nacer.romper_el_huevo("u", "g", T0)
    with pytest.raises(nacer.YaTieneGachamon):
        nacer.romper_el_huevo("u", "g", T0)
    assert len(db.plantel("u", "g")) == 1


def test_con_uno_en_la_incubadora_tampoco_hay_huevo():
    primero = nacer.romper_el_huevo("u", "g", T0)
    db.guardar(replace(primero, muerta_en=T0, causa_muerte="hambre"))
    db.crear("u", "g", "pulpo", "Tinta", (10, 10, 10, 10), T0, activa=False)
    with pytest.raises(nacer.YaTieneGachamon):
        nacer.romper_el_huevo("u", "g", T0)


def test_cuando_se_le_murio_el_unico_puede_sacar_otro():
    nacer.romper_el_huevo("d", "g", T0)
    otro = nacer.romper_el_huevo("d", "g", T0 + timedelta(days=5))
    assert otro.viva and len(db.plantel("d", "g")) == 1


def test_dos_huevos_a_la_vez_dejan_un_gachamon():
    def romper(_):
        try:
            return nacer.romper_el_huevo("u", "g", T0)
        except nacer.YaTieneGachamon:
            return None

    with ThreadPoolExecutor(max_workers=2) as hilos:
        nacidos = [n for n in hilos.map(romper, range(2)) if n]
    assert len(nacidos) == 1 and len(db.plantel("u", "g")) == 1


def test_bautizar_le_pone_nombre_una_vez():
    nacer.romper_el_huevo("u", "g", T0)
    assert nacer.bautizar("u", "g", "  Pelusa  ", T0).nombre == "Pelusa"
    assert db.criatura_activa("u", "g").nombre == "Pelusa"
    with pytest.raises(nacer.NoSePuedeBautizar):
        nacer.bautizar("u", "g", "Otra", T0)


@pytest.mark.parametrize("malo", ["", "   ", "<b>x</b>", "x" * 25, "Pelu🙂"])
def test_un_nombre_que_no_vale_no_bautiza(malo):
    nacida = nacer.romper_el_huevo("u", "g", T0)
    with pytest.raises(ValueError):
        nacer.bautizar("u", "g", malo, T0)
    assert db.criatura_activa("u", "g").nombre == nacida.nombre


def test_sin_gachamon_no_hay_a_quien_bautizar():
    with pytest.raises(nacer.NoSePuedeBautizar):
        nacer.bautizar("nadie", "g", "Pelusa", T0)


def test_no_nace_un_huerfano_si_la_cuenta_se_vinculo_mientras_tanto():
    import identidad

    web = db.crear_identidad_web(12, "g", T0).usuario_id
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    assert db.canjear_codigo_de_vinculo(codigo, "111111111111111111", "g", T0) == "ok"
    with pytest.raises(nacer.YaNoEsSuIdentidad):
        nacer.romper_el_huevo(web, "g", T0)
    assert not db.tiene_gachamones(web, "g")
    assert identidad.es_web(web)


def test_una_identidad_web_vigente_si_puede_nacer():
    web = db.crear_identidad_web(12, "g", T0).usuario_id
    assert nacer.romper_el_huevo(web, "g", T0).usuario_id == web


def test_el_bot_rompe_el_huevo_por_el_mismo_camino():
    from pathlib import Path

    fuente = (Path(__file__).resolve().parent.parent / "cogs" / "mascota.py").read_text(encoding="utf-8")
    assert "nacer.romper_el_huevo(" in fuente
    assert "esp.tirar_stats_iniciales" not in fuente
```

`tests/test_web_nacer.py`:

```python
import db
import identidad
from ayudas_web import ESCRIBIR, PUEBLO, alta, entrar, poner_reloj

HUEVO, BAUTIZAR = "/gachamon/api/huevo", "/gachamon/api/bautizar"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)


def test_sin_avatar_no_hay_huevo(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    entrar(cliente, 1)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    respuesta = cliente.post(HUEVO, headers=ESCRIBIR)
    assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "sin_avatar"
    assert db.plantel(YO, G) == []


def test_romper_el_huevo_devuelve_el_estado_con_el_recien_nacido(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    respuesta = cliente.post(HUEVO, headers=ESCRIBIR)
    assert respuesta.status_code == 201
    gachamon = respuesta.json()["gachamon"]
    assert gachamon["espera_nombre"] is True and gachamon["nombre"] == gachamon["nombre_especie"]
    assert gachamon["etapa"] == "bebe"


def test_el_segundo_huevo_se_rechaza(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    cliente.post(HUEVO, headers=ESCRIBIR)
    respuesta = cliente.post(HUEVO, headers=ESCRIBIR)
    assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "ya_tienes"


def test_bautizar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    cliente.post(HUEVO, headers=ESCRIBIR)
    respuesta = cliente.post(BAUTIZAR, json={"nombre": " Pelusa "}, headers=ESCRIBIR)
    assert respuesta.status_code == 200
    assert respuesta.json()["gachamon"]["nombre"] == "Pelusa"
    assert respuesta.json()["gachamon"]["espera_nombre"] is False
    otra = cliente.post(BAUTIZAR, json={"nombre": "Otra"}, headers=ESCRIBIR)
    assert otra.status_code == 409 and otra.json()["detail"]["clave"] == "ya_bautizado"


def test_un_nombre_malo_vuelve_con_su_frase(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    cliente.post(HUEVO, headers=ESCRIBIR)
    for cuerpo in ({"nombre": "<img src=x>"}, {"nombre": ""}, {}, {"nombre": 7}):
        respuesta = cliente.post(BAUTIZAR, json=cuerpo, headers=ESCRIBIR)
        assert respuesta.status_code == 422, cuerpo
        assert respuesta.json()["detail"]["clave"] == "nombre"
        assert respuesta.json()["detail"]["mensaje"]


def test_bautizar_sin_gachamon(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    respuesta = cliente.post(BAUTIZAR, json={"nombre": "Pelusa"}, headers=ESCRIBIR)
    assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "sin_gachamon"


def test_las_dos_piden_la_cabecera(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    assert cliente.post(HUEVO).status_code == 403
    assert cliente.post(BAUTIZAR, json={"nombre": "Pelusa"}).status_code == 403
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_nacer.py tests/test_web_nacer.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'nacer'`.

- [ ] **Step 3: Escribir `nacer.py` y pasar el bot a usarlo**

Antes: `impact({target: "romper", direction: "upstream"})` sobre `cogs/mascota.py`.

`romper_el_huevo` empieza por `db.activa_al_dia`, que es lo que hace que quien perdió a su único gachamon pueda sacar otro. La comprobación de que una identidad web sigue vigente va en `db.crear`, bajo su mismo `BEGIN IMMEDIATE`: es el único sitio donde no puede colarse un vínculo entre mirar y crear. Para una identidad de Discord, `db.crear` no cambia en nada. Las dos excepciones con que `db.crear` avisa de que ya había uno —`sqlite3.IntegrityError` y `ValueError`— salen de aquí convertidas en `YaTieneGachamon`.

En `cogs/mascota.py`, `HuevoView.romper` llama a `nacer.romper_el_huevo(…, canal_id=str(interaccion.channel_id))` y atrapa `nacer.YaTieneGachamon` donde atrapaba las otras dos. El mensaje que ve el jugador de Discord no cambia.

- [ ] **Step 4: Las rutas, y `con_gachamon` en las ayudas**

```python
def con_gachamon(cliente, uid: int = 1, nombre: str = "Pelusa") -> dict:
    """Una cuenta con avatar y un gachamon ya bautizado. Devuelve el estado."""
    alta(cliente, uid)
    assert cliente.post("/gachamon/api/huevo", headers=ESCRIBIR).status_code == 201
    hecho = cliente.post("/gachamon/api/bautizar", json={"nombre": nombre}, headers=ESCRIBIR)
    assert hecho.status_code == 200, hecho.text
    return hecho.json()
```

- [ ] **Step 5: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_nacer.py tests/test_web_nacer.py tests/test_web_estado.py tests/test_carga.py tests/test_vistas.py -q`
Expected: PASS.

- [ ] **Step 6: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(nacer): el huevo y el bautizo, iguales en Discord y en la web"
```

---

### Task 9: Cuidar y acariciar desde la web

**Files:**
- Modify: `web/juego.py`
- Test: `tests/test_web_acciones.py`

**Interfaces:**
- Consumes: `economia.ejecutar_cuidado`, `sim.ACCIONES_DE_CUIDADO`, `db.acariciar`, `estado.armar`, `ayudas_web.con_gachamon`.
- Produces:
  - `POST /gachamon/api/cuidar` — cuerpo `{"accion": str, "evento_id": str}`. `accion` es una de `sim.ACCIONES_DE_CUIDADO`; `evento_id` son de 8 a 64 caracteres entre letras sin tilde, números y guiones. Contesta 200:

    ```json
    {"ok": true, "mensaje": "…", "espera": 0, "monedas": 1, "evoluciono": false, "estado": {…}}
    ```
    `ok` es falso cuando la regla no dejó (enfriamiento, empacho…), con su `mensaje` y, si aplica, `espera` en segundos. El `mensaje` es el del dominio; si la regla dijo que no y no trajo frase, la ruta pone «Todavía no.». `monedas` es lo ganado con este evento. Un evento repetido contesta `ok: true` con las mismas `monedas` y no vuelve a aplicar nada. 422 con clave `accion` o `evento`; 409 `sin_gachamon`; 409 `evento` si ese `evento_id` ya se usó para otra acción.
  - `POST /gachamon/api/acariciar` → 200 `{"ok": bool, "espera": <segundos>, "estado": {…}}`; 409 `sin_gachamon`.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_web_acciones.py`:

```python
import pytest

import db
import economia
import identidad
import simulacion as sim
from ayudas_web import ESCRIBIR, PUEBLO, alta, con_gachamon, poner_reloj

CUIDAR, ACARICIAR = "/gachamon/api/cuidar", "/gachamon/api/acariciar"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)


def cuidar(cliente, accion, evento="evento-0001"):
    return cliente.post(CUIDAR, json={"accion": accion, "evento_id": evento}, headers=ESCRIBIR)


def test_jugar_sube_el_animo_paga_una_moneda_y_devuelve_el_estado(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    antes = cliente.get("/gachamon/api/estado").json()["gachamon"]["barras"]["animo"]
    respuesta = cuidar(cliente, "jugar")
    cuerpo = respuesta.json()
    assert respuesta.status_code == 200 and cuerpo["ok"] is True
    assert cuerpo["monedas"] == 1 and cuerpo["mensaje"]
    assert cuerpo["estado"]["gachamon"]["barras"]["animo"] > antes
    assert cuerpo["estado"]["saldos"]["monedas"] == 51
    assert cuerpo["estado"]["gachamon"]["esperas"]["jugar"] == 29 * 60


def test_el_mismo_evento_repetido_no_premia_ni_aplica_dos_veces(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    primera = cuidar(cliente, "jugar", "evento-doble").json()
    repetida = cuidar(cliente, "jugar", "evento-doble").json()
    assert repetida["ok"] is True and repetida["monedas"] == primera["monedas"] == 1
    assert repetida["estado"]["saldos"]["monedas"] == 51
    assert repetida["estado"]["gachamon"]["barras"] == primera["estado"]["gachamon"]["barras"]
    assert db.criatura_activa(YO, G).xp == sim.XP_POR_CUIDADO[sim.JUGAR]


def test_el_mismo_evento_para_otra_accion_se_rechaza(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    cuidar(cliente, "jugar", "evento-mezcla")
    respuesta = cuidar(cliente, "limpiar", "evento-mezcla")
    assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "evento"


def test_antes_de_tiempo_la_regla_dice_que_no_y_cuanto_falta(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    cuidar(cliente, "jugar", "evento-0001")
    reloj.pasar(minutes=9)
    cuerpo = cuidar(cliente, "jugar", "evento-0002").json()
    assert cuerpo["ok"] is False and cuerpo["monedas"] == 0
    assert cuerpo["espera"] == 20 * 60 and cuerpo["mensaje"]
    assert cuerpo["estado"]["saldos"]["monedas"] == 51


@pytest.mark.parametrize("cuerpo, clave", [
    ({"accion": "bailar", "evento_id": "evento-0001"}, "accion"),
    ({"accion": "competir", "evento_id": "evento-0001"}, "accion"),
    ({"accion": "acariciar", "evento_id": "evento-0001"}, "accion"),
    ({"evento_id": "evento-0001"}, "accion"),
    ({"accion": "jugar"}, "evento"),
    ({"accion": "jugar", "evento_id": "corto"}, "evento"),
    ({"accion": "jugar", "evento_id": "x" * 65}, "evento"),
    ({"accion": "jugar", "evento_id": "con espacios 1"}, "evento"),
    ({"accion": "jugar", "evento_id": "ñandú-00001"}, "evento"),
    ({"accion": "jugar", "evento_id": 12345678}, "evento"),
])
def test_un_pedido_mal_hecho_no_toca_nada(cliente, monkeypatch, cuerpo, clave):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    respuesta = cliente.post(CUIDAR, json=cuerpo, headers=ESCRIBIR)
    assert respuesta.status_code == 422 and respuesta.json()["detail"]["clave"] == clave
    assert economia.saldos(YO, G).asciicoins == 50


def test_sin_gachamon_no_hay_a_quien_cuidar_ni_acariciar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    for respuesta in (cuidar(cliente, "jugar"), cliente.post(ACARICIAR, headers=ESCRIBIR)):
        assert respuesta.status_code == 409
        assert respuesta.json()["detail"]["clave"] == "sin_gachamon"


def test_acariciar_cuenta_una_vez_y_despues_dice_cuanto_falta(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    antes = cliente.get("/gachamon/api/estado").json()["gachamon"]["barras"]["animo"]
    primera = cliente.post(ACARICIAR, headers=ESCRIBIR).json()
    assert primera["ok"] is True and primera["espera"] == 19 * 60
    assert primera["estado"]["gachamon"]["barras"]["animo"] == antes + 5
    reloj.pasar(minutes=4)
    segunda = cliente.post(ACARICIAR, headers=ESCRIBIR).json()
    assert segunda["ok"] is False and segunda["espera"] == 15 * 60
    assert segunda["estado"]["gachamon"]["barras"] == cliente.get("/gachamon/api/estado").json()["gachamon"]["barras"]
    assert segunda["estado"]["saldos"] == {"monedas": 50, "gemas": 50}


def test_nadie_cuida_ni_acaricia_al_gachamon_de_otro(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente, 1)
    mio = db.criatura_activa(YO, G)
    reloj.pasar(hours=6)
    alta(cliente, 2, nombre="Ana")
    assert cuidar(cliente, "jugar").status_code == 409
    assert cliente.post(ACARICIAR, headers=ESCRIBIR).status_code == 409
    intruso = cliente.post(
        CUIDAR, headers=ESCRIBIR,
        json={"accion": "jugar", "evento_id": "evento-0009", "usuario_id": YO,
              "guild_id": G, "criatura_id": mio.id},
    )
    assert intruso.status_code == 409
    assert db.por_id(mio.id).xp == 0 and economia.saldos(YO, G).asciicoins == 50


def test_las_dos_piden_la_cabecera(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    assert cliente.post(CUIDAR, json={"accion": "jugar", "evento_id": "evento-0001"}).status_code == 403
    assert cliente.post(ACARICIAR).status_code == 403
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_acciones.py -q`
Expected: FAIL — 404 o 405 en `/gachamon/api/cuidar`.

- [ ] **Step 3: Implementar las dos rutas**

`economia.ejecutar_cuidado` devuelve `None` cuando no hay gachamon activo, lanza `RuntimeError` cuando el evento pertenece a otra acción, y su resultado trae `ok`, `mensaje`, `espera`, `delta_asciicoins`, `etapa_anterior` y `replay`. La ruta sólo traduce. El `evento_id` del cuerpo se usa tal cual: el dominio ya lo guarda por persona y servidor, así que el de una cuenta no choca con el de otra.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_acciones.py tests/test_economia_cuidado.py -q`
Expected: PASS.

- [ ] **Step 5: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): cuidar y acariciar, con el mismo evento sin premio doble"
```

---

### Task 10: Los retratos

**Files:**
- Modify: `retrato.py` — `armar`, `relleno`, `version`
- Create: `web/retratos.py`
- Modify: `web/app.py`, `web/estado.py` — el `retrato` de la ficha lleva `?v=`
- Modify: `tests/test_web_estado.py` — la aserción del `retrato`
- Test: `tests/test_web_retratos.py`

**Interfaces:**
- Consumes: `retrato._armar`, `retrato.CON_RETRATO`, `retrato.COLORES`, `retrato.FUENTES`, `retrato.SIN_SOMBRERO`, `cos.SOMBREROS`, `esp.ESPECIES`, `esp.ETAPAS`.
- Produces, en `retrato.py`:
  - `armar(clave, etapa, animo, sombrero) -> bytes` — el nombre público de `_armar`.
  - `relleno(clave: str, etapa: str, animo: str) -> bytes` — un PNG de 256×256 con fondo transparente para una especie sin dibujo: una silueta redonda del color de la especie, que crece con la etapa, una cara simple que cambia con el ánimo, y una franja con el nombre de la especie y la palabra `RELLENO`. Recordado con `lru_cache`.
  - `version() -> str` — huella corta del contenido de `fuentes/`. Calculada una vez.
- Produces, en la web:
  - `GET /gachamon/retrato/{especie}/{etapa}/{animo}/{sombrero}.png` — sin sesión: es un dibujo, no un dato de nadie. `image/png` con `Cache-Control: public, max-age=31536000, immutable`. 404 si la especie, la etapa, el ánimo o el sombrero no existen. Con dibujo, el de `armar`; sin él, el de `relleno`, que ignora el sombrero.
  - En la ficha: `"retrato": "/gachamon/retrato/<especie>/<etapa>/<cara>/<sombrero o sin>.png?v=<versión>"`.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_web_retratos.py`:

```python
import io

import pytest
from PIL import Image

import especies as esp
import retrato

PNG = b"\x89PNG\r\n\x1a\n"
SIN_DIBUJO = sorted(set(esp.ESPECIES) - set(retrato.CON_ETAPAS_COMPLETAS))


def pedir(cliente, especie, etapa="bebe", animo="feliz", sombrero="sin"):
    return cliente.get(f"/gachamon/retrato/{especie}/{etapa}/{animo}/{sombrero}.png")


def test_una_especie_dibujada_trae_su_retrato(cliente):
    respuesta = pedir(cliente, "pollito", "adulto", "feliz", "corona")
    assert respuesta.status_code == 200 and respuesta.content.startswith(PNG)
    assert respuesta.headers["content-type"] == "image/png"
    assert respuesta.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert respuesta.content == retrato.armar("pollito", "adulto", "feliz", "corona")


def test_no_pide_sesion(cliente):
    cliente.cookies.clear()
    assert pedir(cliente, "pollito").status_code == 200


def test_hay_catorce_especies_sin_dibujo():
    assert len(SIN_DIBUJO) == 14


@pytest.mark.parametrize("especie", SIN_DIBUJO)
def test_una_especie_sin_dibujo_trae_un_relleno_que_se_ve(cliente, especie):
    respuesta = pedir(cliente, especie)
    assert respuesta.status_code == 200 and respuesta.content.startswith(PNG)
    imagen = Image.open(io.BytesIO(respuesta.content)).convert("RGBA")
    assert imagen.size == (256, 256)
    opacos = sum(1 for alfa in imagen.getchannel("A").getdata() if alfa > 0)
    assert opacos > 256 * 256 * 0.1
    assert imagen.getpixel((0, 0))[3] == 0


def test_el_relleno_cambia_con_la_especie_la_etapa_y_el_animo():
    a, b = SIN_DIBUJO[0], SIN_DIBUJO[1]
    distintos = {
        retrato.relleno(a, "bebe", "feliz"), retrato.relleno(b, "bebe", "feliz"),
        retrato.relleno(a, "adulto", "feliz"), retrato.relleno(a, "bebe", "mal"),
    }
    assert len(distintos) == 4


def test_el_relleno_ignora_el_sombrero(cliente):
    assert pedir(cliente, SIN_DIBUJO[0], sombrero="corona").content == pedir(cliente, SIN_DIBUJO[0]).content


@pytest.mark.parametrize("partes", [
    ("dinosaurio", "bebe", "feliz", "sin"), ("pollito", "anciano", "feliz", "sin"),
    ("pollito", "bebe", "eufórico", "sin"), ("pollito", "bebe", "feliz", "casco"),
    ("pollito", "bebe", "feliz", "tinte_rojo"), ("..", "bebe", "feliz", "sin"),
])
def test_lo_que_no_existe_es_un_404(cliente, partes):
    assert pedir(cliente, *partes).status_code == 404


def test_la_version_es_corta_estable_y_va_en_la_ficha(cliente, monkeypatch):
    from ayudas_web import con_gachamon, poner_reloj

    version = retrato.version()
    assert len(version) >= 8 and set(version) <= set("0123456789abcdef")
    assert retrato.version() == version
    poner_reloj(monkeypatch)
    gachamon = con_gachamon(cliente)["gachamon"]
    assert gachamon["retrato"] == (
        f"/gachamon/retrato/{gachamon['especie']}/bebe/{gachamon['cara']}/sin.png?v={version}"
    )
    assert cliente.get(gachamon["retrato"]).status_code == 200
```

Y en `tests/test_web_estado.py`, la aserción del estado completo pasa a esperar el `retrato` con `?v=` y `retrato.version()`.

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_retratos.py -q`
Expected: FAIL — `AttributeError: module 'retrato' has no attribute 'armar'`.

- [ ] **Step 3: Implementar**

El relleno se dibuja con Pillow, que ya es dependencia. Usa la fuente por defecto de Pillow para la franja: no se añade ningún archivo de tipografía. Lo que importa es que nadie lo confunda con un dibujo terminado y que dos especies no se vean iguales.

La ruta valida las cuatro partes contra los catálogos antes de tocar el disco: nada de lo que venga en la dirección llega a formar una ruta de archivo sin haber pasado por ahí.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_retratos.py tests/test_web_estado.py tests/test_retrato.py -q`
Expected: PASS.

- [ ] **Step 5: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(retratos): la web sirve los dibujos, y un relleno para las especies que no tienen"
```

---

### Task 11: El cliente: entrar

HTML, CSS y módulos de JavaScript, sin compilar. Esta tarea deja a alguien desde que abre la página hasta que tiene un gachamon con nombre.

**Files:**
- Modify: `web/static/index.html`
- Create: `web/static/estilo.css`
- Create: `web/static/js/api.js`, `pantallas.js`, `dom.js`, `dibujo.js`, `entrada.js`, `principal.js`
- Create: `web/static/js/package.json` — sólo `{"type": "module"}`, para que Node, en cualquier versión, lea esos archivos como módulos al correr las pruebas
- Create: `tests/js/pantallas.test.mjs`, `tests/js/dibujo.test.mjs`
- Test: `tests/test_web_js.py`, `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: todas las rutas de las tareas 1 a 10.
- Produces, en `web/static/js/` (módulos ES; se importan entre sí con rutas relativas):
  - `api.js`: `pedir(metodo, ruta, cuerpo)` — llama a `/gachamon/api/<ruta>`, añade `X-Gachamon: 1` a lo que no sea `GET`, devuelve el JSON, y si la respuesta no es 2xx lanza `{estado, clave, mensaje}`. `nuevoEvento()` — un id de evento válido para `/api/cuidar`.
  - `pantallas.js` (puro, sin tocar `document`): `siguiente(sesion, cuenta, estado) -> string`. Decide qué pantalla toca:

    | Situación | Pantalla |
    |---|---|
    | sin sesión | `"sesion"` |
    | cuenta `nueva` | `"bienvenida"` |
    | con cuenta y sin avatar | `"avatar"` |
    | con `difunto` pendiente | `"difunto"` |
    | sin gachamon | `"huevo"` |
    | gachamon que espera nombre | `"bautizo"` |
    | lo demás | `"lugar"` |
  - `dom.js`: `el(etiqueta, atributos, ...hijos)` — crea un elemento; los hijos de texto entran como nodos de texto. Es la única forma en que el cliente crea elementos.
  - `dibujo.js`: `COLORES_DE_PIEL`, `COLORES_DE_PELO`, `COLORES_DE_ROPA` (un color por clave del catálogo del servidor) y `dibujarAvatar(ctx, avatar, escala)` — el monigote de relleno, que cambia con las cinco elecciones. Dibuja sólo con `fillStyle`, `fillRect`, `beginPath`, `ellipse`, `fill`, `save`, `restore`, `translate` y `scale`, y con una clave que no conoce usa un color por defecto en vez de fallar.
  - `entrada.js`: una función por pantalla — `sesion`, `bienvenida`, `avatar`, `huevo`, `bautizo`, `difunto` — que recibe el contenedor y una función `seguir()` para pedir que se vuelva a decidir la pantalla.
  - `principal.js`: arranca, pregunta por la sesión, la cuenta y el estado, y pinta la pantalla que diga `siguiente`. La pantalla `"lugar"` la pone la tarea 12; aquí deja un aviso provisional.

Lo que tiene que pasar en cada pantalla:

- **sesion:** dice que hay que entrar a Rowino y enlaza a `/login`.
- **bienvenida:** pregunta si ya jugaba en Discord. «Empezar de cero» llama a `cuenta/empezar`. «Ya jugaba» pide el código, lo muestra grande con la instrucción `/vincular <código>` y cuántos minutos dura, **avisa de que ese código da acceso a sus gachamones, con la frase «No se lo pases a nadie»**, y pregunta cada 3 segundos si la cuenta ya está vinculada. Si pedir el código falla con `con_gachamones` o `ya_vinculada`, enseña el mensaje del servidor.
- **avatar:** pide las opciones al servidor, deja elegir las cinco cosas y escribir el nombre, y enseña el monigote cambiando en vivo. Si el servidor rechaza el avatar, enseña su mensaje junto al formulario.
- **huevo:** un huevo y un botón para romperlo.
- **bautizo:** enseña al recién nacido —retrato, especie— y pide el nombre. Un nombre rechazado enseña el mensaje del servidor.
- **difunto:** quién era y cuántos días vivió, y un botón para seguir, que llama a `difunto/visto`.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/js/pantallas.test.mjs`:

```javascript
import test from 'node:test';
import assert from 'node:assert/strict';
import { siguiente } from '../../web/static/js/pantallas.js';

const sesion = { usuario: 'felipe' };
const gachamon = { nombre: 'Pelusa', espera_nombre: false };
const avatar = { nombre: 'Feli' };
const estado = (cambios = {}) => ({ avatar, gachamon, difunto: null, ...cambios });

test('sin sesión, a entrar', () => {
  assert.equal(siguiente(null, null, null), 'sesion');
});

test('una cuenta nueva ve la bienvenida', () => {
  assert.equal(siguiente(sesion, { estado: 'nueva' }, null), 'bienvenida');
});

test('con cuenta y sin avatar, al avatar', () => {
  for (const cuenta of [{ estado: 'web' }, { estado: 'vinculada' }]) {
    assert.equal(siguiente(sesion, cuenta, estado({ avatar: null })), 'avatar');
  }
});

test('el avatar va antes que cualquier otra cosa del juego', () => {
  const todo = estado({ avatar: null, difunto: { nombre: 'Viejo' }, gachamon: null });
  assert.equal(siguiente(sesion, { estado: 'vinculada' }, todo), 'avatar');
});

test('un difunto pendiente se cuenta antes de seguir', () => {
  assert.equal(siguiente(sesion, { estado: 'web' }, estado({ difunto: { nombre: 'Viejo' } })), 'difunto');
  assert.equal(
    siguiente(sesion, { estado: 'web' }, estado({ difunto: { nombre: 'Viejo' }, gachamon: null })),
    'difunto',
  );
});

test('sin gachamon, al huevo', () => {
  assert.equal(siguiente(sesion, { estado: 'web' }, estado({ gachamon: null })), 'huevo');
});

test('el que espera nombre va al bautizo', () => {
  const sinNombre = estado({ gachamon: { nombre: 'Piollito', espera_nombre: true } });
  assert.equal(siguiente(sesion, { estado: 'web' }, sinNombre), 'bautizo');
});

test('con todo en su sitio, al lugar', () => {
  assert.equal(siguiente(sesion, { estado: 'web' }, estado()), 'lugar');
  assert.equal(siguiente(sesion, { estado: 'vinculada' }, estado()), 'lugar');
});
```

`tests/js/dibujo.test.mjs`:

```javascript
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  COLORES_DE_PIEL, COLORES_DE_PELO, COLORES_DE_ROPA, dibujarAvatar,
} from '../../web/static/js/dibujo.js';

const lienzo = () => {
  const trazos = [];
  let color = null;
  return {
    trazos,
    set fillStyle(valor) { color = valor; },
    get fillStyle() { return color; },
    fillRect: (...caja) => trazos.push([color, ...caja]),
    save() {}, restore() {}, translate() {}, scale() {}, beginPath() {}, ellipse() {}, fill() {},
  };
};
const base = { piel: 'media', pelo: 'corto', color_de_pelo: 'castano', ropa: 'poleron', genero: 'macho' };
const pintar = (cambios = {}) => {
  const ctx = lienzo();
  dibujarAvatar(ctx, { ...base, ...cambios }, 4);
  return JSON.stringify(ctx.trazos);
};

test('hay un color para cada clave del catálogo', () => {
  assert.deepEqual(Object.keys(COLORES_DE_PIEL), ['clara', 'media', 'tostada', 'oscura']);
  assert.deepEqual(Object.keys(COLORES_DE_PELO), ['negro', 'castano', 'rubio', 'rojo', 'cano', 'azul']);
  assert.deepEqual(Object.keys(COLORES_DE_ROPA), ['poleron', 'camisa', 'vestido', 'overol']);
});

test('cada elección cambia el dibujo', () => {
  const normal = pintar();
  for (const cambio of [
    { piel: 'oscura' }, { pelo: 'largo' }, { pelo: 'rapado' }, { pelo: 'rizado' },
    { pelo: 'coleta' }, { color_de_pelo: 'azul' }, { ropa: 'vestido' }, { ropa: 'overol' },
  ]) {
    assert.notEqual(pintar(cambio), normal, JSON.stringify(cambio));
  }
});

test('una clave desconocida no revienta el dibujo', () => {
  assert.doesNotThrow(() => pintar({ piel: 'verde', pelo: 'cresta', ropa: 'armadura' }));
});
```

`tests/test_web_js.py`:

```python
"""Corre con Node las pruebas de la lógica del cliente que no necesita pantalla."""
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def test_la_logica_del_cliente():
    node = shutil.which("node")
    if node is None:
        pytest.skip("no hay Node en esta máquina")
    pruebas = sorted(str(p) for p in (RAIZ / "tests" / "js").glob("*.test.mjs"))
    assert pruebas, "no hay pruebas de JavaScript que correr"
    hecho = subprocess.run([node, "--test", *pruebas], cwd=RAIZ, capture_output=True, text=True)
    assert hecho.returncode == 0, hecho.stdout + hecho.stderr
```

`tests/test_web_cliente.py`:

```python
"""Lo que se puede vigilar del cliente leyendo sus archivos."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ESTATICOS = RAIZ / "web" / "static"
GUIONES = sorted((ESTATICOS / "js").glob("*.js"))


def test_hay_guiones_que_mirar():
    assert {g.name for g in GUIONES} >= {
        "api.js", "pantallas.js", "dom.js", "dibujo.js", "entrada.js", "principal.js",
    }


def test_nada_entra_en_la_pagina_como_marcado():
    prohibido = re.compile(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write")
    culpables = [
        f"{g.name}:{n}" for g in GUIONES
        for n, linea in enumerate(g.read_text(encoding="utf-8").splitlines(), 1)
        if prohibido.search(linea)
    ]
    assert not culpables, culpables


def test_el_cliente_no_depende_de_nada_de_fuera():
    for archivo in [ESTATICOS / "index.html", ESTATICOS / "estilo.css", *GUIONES]:
        texto = archivo.read_text(encoding="utf-8")
        assert "http://" not in texto and "https://" not in texto, archivo.name


def test_la_portada_carga_sus_archivos_por_la_ruta_con_version():
    portada = (ESTATICOS / "index.html").read_text(encoding="utf-8")
    assert "static/__V__/estilo.css" in portada
    assert "static/__V__/js/principal.js" in portada
    assert 'type="module"' in portada and 'lang="es"' in portada
    assert 'name="viewport"' in portada


def test_los_modulos_se_importan_con_rutas_relativas():
    importa = re.compile(r"""from\s+['"]([^'"]+)['"]""")
    for guion in GUIONES:
        for ruta in importa.findall(guion.read_text(encoding="utf-8")):
            assert ruta.startswith("./") and ruta.endswith(".js"), f"{guion.name}: {ruta}"


def test_el_aviso_del_codigo_esta_escrito():
    entrada = (ESTATICOS / "js" / "entrada.js").read_text(encoding="utf-8")
    assert "/vincular" in entrada
    assert "no se lo pases a nadie" in entrada.lower()


def test_ningun_texto_del_cliente_usa_los_nombres_viejos():
    for archivo in [ESTATICOS / "index.html", *GUIONES]:
        assert not re.search(r"ascii\s?(coin|gem)", archivo.read_text(encoding="utf-8"), re.I)
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py -q`
Expected: FAIL — faltan los archivos.

- [ ] **Step 3: Escribir el cliente**

- Primero el celular en vertical: una columna de 360 a 480 píxeles de ancho, centrada en pantallas más grandes. Ningún tamaño depende de que el teléfono sea de un ancho concreto.
- Los colores, los bordes y la tipografía se definen una vez como variables de CSS en `:root`. La tipografía es la del sistema.
- Cada botón dice lo que hace. Un botón que espera al servidor se desactiva mientras espera, para que un segundo toque no mande otra petición.
- Si una petición falla sin `clave` —la red se cayó—, la pantalla lo dice con una frase y ofrece reintentar. No se queda en blanco.
- El texto del jugador y el del servidor entran por `dom.el` o por `textContent`.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py tests/test_web_app.py -q`
Expected: PASS. Con Node instalado, `test_la_logica_del_cliente` corre y pasa; sin él, se salta.

- [ ] **Step 5: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): el cliente lleva de la puerta al bautizo"
```

---

### Task 12: El cliente: la pantalla principal

La pantalla que Felipe aprobó en el boceto (diseño, 5.3), todavía sin pueblo: el lugar es el hogar del gachamon.

**Files:**
- Create: `web/static/js/lugar.js`, `web/static/js/tiempo.js`
- Modify: `web/static/js/principal.js`, `web/static/estilo.css`
- Create: `tests/js/tiempo.test.mjs`
- Modify: `tests/test_web_cliente.py`

**Interfaces:**
- Consumes: `api.pedir`, `api.nuevoEvento`, `dom.el`, `dibujo.dibujarAvatar` (tarea 11); el estado (tarea 7); `/api/cuidar`, `/api/acariciar` (tarea 9).
- Produces:
  - `tiempo.js` (puro): `formatoEspera(segundos) -> string` — `""` para 0 o menos, `"45 s"` por debajo del minuto, `"5 min"` redondeando hacia arriba, `"1 h 5 min"` desde la hora. `elegirGlobo(globos, anterior, azar) -> objeto | null` — la misma regla que `globos.elegir` del servidor: necesidad antes que suelta, sin repetir la anterior si hay otra. `nombreDelHogar(hogar) -> string` — `"Tu casa"`, `"Refugio"` o `"A la intemperie"`.
  - `lugar.js`: `lugar(contenedor, estado, seguir)` — pinta la pantalla y la mantiene al día.

Lo que tiene la pantalla, de arriba hacia abajo: la cabecera con el nombre del hogar, las monedas y las gemas; la escena con el avatar, el gachamon en grande y su globo; la ficha con nombre, especie, etapa y nivel y las tres barras; los cuatro cuidados.

Cómo se comporta:

- **El globo** aparece a los pocos segundos de entrar y cambia cada 20 a 40 segundos, eligiendo con `elegirGlobo` entre los del estado. No habla sin parar: entre uno y otro, la escena queda sin globo un rato.
- **Tocar al gachamon** llama a `acariciar`. Si cuenta, salen corazones y el gachamon salta. Si no cuenta, **no sale ningún corazón**: apenas se mueve y bajo la ficha se lee cuánto falta. Nunca aparece un mensaje de error por acariciar antes de tiempo.
- **Cada cuidado** manda su acción con un evento nuevo. Mientras espera, el botón está desactivado. Si la regla dice que no, se enseña su mensaje. Un botón con espera la muestra con `formatoEspera` y está desactivado; la cuenta baja sola, segundo a segundo, sin preguntar al servidor.
- **Las monedas ganadas** se ven un momento junto al saldo («+1 moneda»).
- **El estado se vuelve a pedir** cada 30 segundos, y al volver a la pestaña después de tenerla oculta. Si lo que llega pide otra pantalla —un difunto, un gachamon sin nombre—, llama a `seguir()`.
- **Desfallecido:** con la comida en 0 la ficha lo dice con esa palabra, y el gachamon se ve decaído.
- **En un computador** (900 píxeles de ancho o más) la escena va a un lado y la ficha con los cuidados al otro.
- Todo lo que temporiza se detiene cuando la pantalla deja de ser la del lugar.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/js/tiempo.test.mjs`:

```javascript
import test from 'node:test';
import assert from 'node:assert/strict';
import { formatoEspera, elegirGlobo, nombreDelHogar } from '../../web/static/js/tiempo.js';

test('la espera se lee como la diría una persona', () => {
  assert.equal(formatoEspera(0), '');
  assert.equal(formatoEspera(-5), '');
  assert.equal(formatoEspera(1), '1 s');
  assert.equal(formatoEspera(59), '59 s');
  assert.equal(formatoEspera(60), '1 min');
  assert.equal(formatoEspera(61), '2 min');
  assert.equal(formatoEspera(19 * 60), '19 min');
  assert.equal(formatoEspera(3600), '1 h');
  assert.equal(formatoEspera(3900), '1 h 5 min');
  assert.equal(formatoEspera(113 * 60), '1 h 53 min');
});

const pide = { tipo: 'necesidad', texto: 'Tengo hambre.' };
const pideOtra = { tipo: 'necesidad', texto: 'Estoy sucia.' };
const charla = { tipo: 'suelta', texto: '¿Cómo estás?' };
const charlaOtra = { tipo: 'suelta', texto: 'Qué lindo día.' };
const primero = () => 0;
const ultimo = () => 0.999;

test('una necesidad va antes que la charla', () => {
  for (const azar of [primero, ultimo]) {
    assert.equal(elegirGlobo([charla, pide, charlaOtra], null, azar), pide);
  }
});

test('no repite el anterior si hay otro del mismo tipo', () => {
  assert.equal(elegirGlobo([pide, pideOtra], pide.texto, primero), pideOtra);
  assert.equal(elegirGlobo([charla, charlaOtra], charlaOtra.texto, ultimo), charla);
});

test('con una sola frase la repite, y sin frases no dice nada', () => {
  assert.equal(elegirGlobo([charla], charla.texto, primero), charla);
  assert.equal(elegirGlobo([], null, primero), null);
});

test('el azar elige entre las candidatas', () => {
  assert.equal(elegirGlobo([charla, charlaOtra], null, primero), charla);
  assert.equal(elegirGlobo([charla, charlaOtra], null, ultimo), charlaOtra);
});

test('el hogar tiene un nombre que se entiende', () => {
  assert.equal(nombreDelHogar('propia'), 'Tu casa');
  assert.equal(nombreDelHogar('refugio'), 'Refugio');
  assert.equal(nombreDelHogar('intemperie'), 'A la intemperie');
});
```

Y en `tests/test_web_cliente.py`:

```python
def test_la_pantalla_principal_esta_y_se_usa():
    nombres = {g.name for g in GUIONES}
    assert {"lugar.js", "tiempo.js"} <= nombres
    principal = (ESTATICOS / "js" / "principal.js").read_text(encoding="utf-8")
    assert "./lugar.js" in principal


def test_la_pantalla_principal_dice_desfallecido_y_no_inventa_errores_al_acariciar():
    lugar = (ESTATICOS / "js" / "lugar.js").read_text(encoding="utf-8")
    assert "esfallecid" in lugar
    assert "acariciar" in lugar and "cuidar" in lugar
    assert "visibilitychange" in lugar


def test_el_estilo_piensa_en_el_celular_y_en_el_computador():
    estilo = (ESTATICOS / "estilo.css").read_text(encoding="utf-8")
    assert "min-width: 900px" in estilo
    assert "prefers-reduced-motion" in estilo
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py -q`
Expected: FAIL — falta `tiempo.js`.

- [ ] **Step 3: Escribir `tiempo.js`, `lugar.js` y enchufarlos**

El fondo de la escena es de relleno: un color de pared y uno de piso, distintos para casa, refugio e intemperie, hechos con CSS. Los corazones y el salto son animaciones de CSS, y quien pidió menos movimiento en su sistema (`prefers-reduced-motion`) no las ve: el ánimo sube igual.

El gachamon es un `<img>` con el `retrato` del estado y un texto alternativo con su nombre. Se tiene que poder acariciar y cuidar con teclado: lo que se toca son botones de verdad.

- [ ] **Step 4: Correr las pruebas**

Run: `./venv/bin/python -m pytest tests/test_web_js.py tests/test_web_cliente.py -q`
Expected: PASS.

- [ ] **Step 5: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(web): la pantalla principal — el gachamon en grande, sus cuidados y la caricia"
```

- [ ] **Step 6: (Controlador) Verlo funcionar de verdad, antes de dar la tarea por buena**

Las pruebas de esta tarea miran la lógica y los archivos, no la pantalla. Antes de cerrarla, el controlador la ve funcionar: levanta el servicio en local contra una base temporal y una base de Rowino de prueba, le pone delante un pequeño intermediario que añade a cada petición una cookie firmada con la clave de prueba, y saca capturas con el Chrome de Windows sin ventana, en ancho de celular y en ancho de computador, de cada pantalla del camino: bienvenida, avatar, huevo, bautizo y pantalla principal. Lo que no se haya podido ver se le dice a Felipe tal cual.

---

### Task 13: En la Pi, sin enlace público

La parte de archivos la hace quien implementa. La parte de la Pi la hace el controlador, **pidiéndole a Felipe cada paso**.

**Files:**
- Create: `gachamon-web.service`
- Modify: `actualizar-pi.sh`, `deploy.sh`
- Modify: `README.md`, `.env.ejemplo`
- Modify: `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`
- Test: `tests/test_despliegue.py`

**Interfaces:**
- Consumes: `web.app:app` (tarea 1); la regla del túnel ya comprobada en seco (`docs/superpowers/specs/2026-11-12-tunel-regla-por-ruta.md`).
- Produces:
  - `gachamon-web.service` — unidad de systemd: mismo usuario y directorio que `tamagotchi.service`, `ExecStart` con `venv/bin/python -m uvicorn web.app:app --host 127.0.0.1 --port 8010`, `Restart=always`.
  - Los dos guiones instalan y reinician las dos unidades, y la suite en la Pi corre con su temporal en memoria.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_despliegue.py`:

```python
"""Lo que los guiones de despliegue no pueden dejar de hacer."""
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
GUIONES = ("actualizar-pi.sh", "deploy.sh")


def leer(nombre: str) -> str:
    return (RAIZ / nombre).read_text(encoding="utf-8")


def test_el_servicio_web_escucha_solo_en_la_propia_maquina():
    unidad = leer("gachamon-web.service")
    assert "uvicorn web.app:app" in unidad
    assert "--host 127.0.0.1" in unidad and "--port 8010" in unidad
    assert "0.0.0.0" not in unidad
    assert "Restart=always" in unidad
    assert "WorkingDirectory=/home/felipe/tamagotchi-bot" in unidad


@pytest.mark.parametrize("guion", GUIONES)
def test_cada_guion_reinicia_los_dos_servicios(guion):
    texto = leer(guion)
    assert "gachamon-web.service" in texto
    assert "restart tamagotchi" in texto and "gachamon-web" in texto.split("restart tamagotchi", 1)[1]


@pytest.mark.parametrize("guion", GUIONES)
def test_cada_guion_copia_la_base_antes_de_reiniciar(guion):
    texto = leer(guion)
    assert texto.index(".bak") < texto.index("systemctl restart")


def test_una_suite_en_rojo_frena_el_despliegue_y_corre_en_memoria():
    texto = leer("actualizar-pi.sh")
    linea = next(l for l in texto.splitlines() if "pytest" in l and "ssh" in l)
    assert "set -o pipefail" in linea
    assert "--basetemp=/dev/shm/" in linea


@pytest.mark.parametrize("guion", GUIONES)
def test_los_guiones_son_bash_valido(guion):
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("no hay bash")
    hecho = subprocess.run([bash, "-n", str(RAIZ / guion)], capture_output=True, text=True)
    assert hecho.returncode == 0, hecho.stderr
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `./venv/bin/python -m pytest tests/test_despliegue.py -q`
Expected: FAIL — falta `gachamon-web.service`.

- [ ] **Step 3: Escribir la unidad y poner al día los dos guiones**

No ejecutar ninguno de los dos guiones. Los dos servicios se reinician uno detrás del otro, el bot primero. El temporal en memoria baja la suite en la Pi de diez minutos a algo razonable: cada prueba con base crea su SQLite, y hoy lo hace en la tarjeta SD.

- [ ] **Step 4: Documentar**

`README.md`: una sección «La web» que diga qué es el servicio, cómo se levanta en local (`./venv/bin/python -m uvicorn web.app:app --port 8010`), las dos variables nuevas del `.env`, y que en producción cuelga de `rowino.online/gachamon` detrás del túnel. Corregir el «~50 s» de la suite en la Pi.

En el documento de pendientes, tachar lo que este plan resolvió (la secuencia de arranque, «desfallecido», crear un gachamon mirando la cuenta, el aviso del código) y dejar lo que sigue abierto.

- [ ] **Step 5: Verificación completa y commit**

```bash
./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git commit -m "feat(despliegue): el servicio web como unidad, y la suite de la Pi en memoria"
```

- [ ] **Step 6: (Controlador, con Felipe) Revisión final, fusión y subida**

Lo de siempre: revisión de toda la rama, y la decisión de fusionar y subir es de Felipe. La CI tiene que pasar en 3.12 y 3.14 antes de tocar la Pi.

- [ ] **Step 7: (Controlador, con Felipe) Dejar la clave en la Pi sin enseñarla**

Con su sí: copiar el valor de `SECRET_KEY` del `.env` de Rowino a `ROWINO_SECRET_KEY` en el `.env` del juego, en la propia Pi, con una orden que no lo imprima, y dejar antes una copia del `.env` del juego en `~/respaldos/`. Comprobar sólo que la línea existe y que su valor mide lo mismo que el original.

- [ ] **Step 8: (Controlador, con Felipe) Desplegar y comprobar por dentro**

`./actualizar-pi.sh`. Después, desde la Pi: `systemctl is-active tamagotchi gachamon-web`, y `curl -s http://127.0.0.1:8010/gachamon/api/salud` tiene que contestar `{"ok":true}`. El registro del servicio web, sin errores.

- [ ] **Step 9: (Controlador, con Felipe) Aplicar la regla del túnel**

Esto corta unos segundos todos los sitios que salen por el túnel, así que se le pregunta el momento. Antes, comprobar que Rowino no tiene ninguna generación en curso.

Copia de `/etc/cloudflared/config.yml` a `~/respaldos/`; insertar la regla probada en seco, justo antes de la de `rowino.online`; `cloudflared tunnel --config /etc/cloudflared/config.yml ingress validate`; y sólo si valida, reiniciar `cloudflared`. Si algo sale mal, se restaura la copia y se reinicia otra vez.

Comprobar desde fuera: `https://rowino.online/gachamon/api/salud` contesta `{"ok":true}`, y `https://rowino.online/` y `https://rowino.online/generar` siguen siendo Rowino.

- [ ] **Step 10: (Felipe) Probarlo**

Felipe entra a `rowino.online/gachamon` con su cuenta, vincula su Discord con `/vincular` y encuentra a sus gachamones. No hay enlace en Rowino todavía: sólo entra quien conoce la dirección.
