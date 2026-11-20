# Monsteropolis A · Las herramientas del dibujante, en el juego — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el juego viva en `/monsteropolis` (con `/gachamon` redirigiendo), que el dibujante suba desde `/monsteropolis_dibujante` las imágenes que reemplazan los recuadros provisionales y se vean al momento, con historial y vuelta atrás, y que el tablero del arte del sitio reciba su avance.

**Architecture:** El servicio del juego gana un segundo prefijo, el del dibujante, con su página y su API. El permiso es una marca de la tabla de cuentas del sitio, que el juego sólo lee y en una consulta aparte. Lo subido vive en una carpeta junto a la base, fuera de git, y una tabla nueva del juego guarda el historial. La página del juego lleva, en cada petición, un bloque de datos con las piezas subidas y su dirección; `urlDeArte` lo mira primero.

**Tech Stack:** Python 3.12, FastAPI, SQLite síncrono (`db.py`), Pillow (ya está); JavaScript sin frameworks; pytest y `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-19-monsteropolis-a-herramientas-del-dibujante-design.md` (copiado del repo del sitio, donde se aprobó; la pieza 2 entera, el contrato del avance y «Para publicar»). El plan del sitio ya está hecho en su repo y consume lo que produce la tarea 5.

## Global Constraints

- La página está **en producción, con jugadores reales**. Nada de esta rama se sube ni se despliega sin la palabra del dueño, y **el juego se publica antes que el sitio** (ver «Para publicar» del diseño).
- Direcciones que fijó el dueño: el juego en `/monsteropolis`, la página del dibujante en `/monsteropolis_dibujante`. `/gachamon` y todo lo que cuelga de ella redirigen a la misma ruta bajo `/monsteropolis`, con su consulta, conservando el método (308).
- La única frase nueva para quien juega, aprobada por el dueño: `Para jugar, entra con tu cuenta de Rowino. Después, vuelve a rowino.online/monsteropolis.` (sustituye a la de `/gachamon` en `web/static/js/entrada.js`). El título y la marca «Gachamon» de la página **no cambian** (es el proyecto B).
- Las frases de la página del dibujante las ven sólo el dueño y el dibujante: las fija este plan (tarea 6).
- Una imagen subida **se ve en el juego al momento** (decisión del dueño); la red es el historial con «volver a la anterior» y «volver al provisional».
- El permiso: `users.arte_access = 1` o `users.is_admin = 1` en la base del sitio, leída en sólo lectura **en una consulta aparte**; si la columna no existe, sólo el administrador del sitio tiene el permiso (por `is_admin`) y el resto del juego sigue igual. `sesion.buscar_persona` no se toca. A quien no lo tiene, todo lo del dibujante le contesta como una ruta que no existe (404).
- Sólo PNG, hasta 4 MB, de la medida exacta del contrato (`web/arte.py`); para la familia `pieza` también el doble, que se reduce como `herramientas/pieza.py` (`LANCZOS`, a la mitad). La imagen se abre de verdad y se vuelve a escribir limpia. Lo que no cumple se rechaza diciendo la medida esperada y la que llegó, sin cambiar nada.
- Lo subido vive en `config.RUTA_ARTE_SUBIDO` (por defecto, la carpeta `arte_subido` junto a la base de `RUTA_BD`), fuera de git; cada archivo, con el nombre de su contenido, escrito entero antes de darlo por bueno. Se guardan en disco las cinco últimas imágenes distintas de cada pieza.
- `db.py` posee la tabla nueva y sus transacciones; las mutaciones van bajo `BEGIN IMMEDIATE`. El historial sólo crece y guarda el **nombre** de quien sube, nunca su número de cuenta.
- El contrato del avance es exactamente el de la sección «El contrato del avance» del diseño (claves `^[a-z0-9/_-]{1,64}$`, sin extensión, únicas; `total` y `hechas` enteros ≥ 0; 404 sin permiso).
- La subida va como cuerpo crudo (`Content-Type: image/png`), sin `multipart`: **ninguna dependencia nueva**.
- Toda ruta que cambia algo es `POST` y exige `X-Gachamon: 1`; las rutas se declaran con `def`. El servicio no guarda estado en memoria.
- `web/` no importa `discord`; el bot no se toca (su manual sigue enlazando `/gachamon`, que redirige).
- El repo es público: ni direcciones, ni ids, ni rutas del dueño, ni SHAs en documentos ni comentarios.

## Review Focus

- **Quien tiene la página vieja abierta** el día de publicar: sus peticiones a `/gachamon/api/…` (también los `POST` con cuerpo) llegan por la redirección, la página se entera de la versión nueva y se recarga; nadie queda atrapado ni cobra dos veces.
- **Una subida rara**: un archivo que dice ser PNG y no lo es, uno truncado, uno de 4 MB + 1 byte, uno con la medida de otra pieza, uno con perfil de color o modo indexado, dos subidas a la vez a la misma pieza, y una ruta de pieza con `..` o que no está en el contrato: se rechazan sin dejar archivos a medias ni filas en el historial.
- **El juego sin el sitio desplegado**: la columna del permiso no existe todavía; nadie entra a lo del dibujante, y el juego (sesión, estado, departamento) responde igual que antes.
- **Lo subido que ya no vale**: el contrato le cambia la medida a una pieza (un mueble cambia de forma) o la quita; esa imagen deja de servirse y se ve el recuadro, y la página del dibujante lo dice.
- **Caché**: una imagen nueva es otra dirección y se ve al recargar, en el navegador y tras la red de entrega; la página del juego no se guarda en caché; una imagen subida que falta en disco da el recuadro de esa pieza, nunca otra.

---

### Task 1: El juego en `/monsteropolis`

**Files:**
- Modify: `web/__init__.py` (`PREFIJO`), `web/app.py`, `web/static/index.html`, `web/static/js/api.js`, `web/static/js/entrada.js`, `web/static/js/arte.js` (sólo el comentario de la dirección)
- Test: `tests/test_web_app.py`, `tests/test_web_cliente.py`, `tests/js/entrada.test.mjs` (o donde viva la frase)

**Interfaces:**
- Produces: `web.PREFIJO == "/monsteropolis"` y `web.PREFIJO_ANTIGUO == "/gachamon"`; ninguna otra ruta del servidor ni del cliente escribe `/gachamon` (una guarda lo vigila).

- [ ] **Step 1: Las pruebas que fallan**
  - `test_el_juego_vive_en_monsteropolis`: `GET /monsteropolis/` da la portada; `GET /monsteropolis/api/salud` da 200; los estáticos versionados cuelgan de `/monsteropolis/static/<versión>/`.
  - `test_gachamon_redirige_conservando_la_ruta`: `GET /gachamon`, `GET /gachamon/`, `GET /gachamon/api/estado?x=1` y `POST /gachamon/api/cuidar` contestan 308 con `Location` en `/monsteropolis…` con la misma ruta y consulta; nada fuera de `/gachamon` y `/monsteropolis` cambia de respuesta (`/gachamonx` sigue en 404).
  - `test_el_cliente_no_nombra_gachamon_como_direccion`: ningún archivo de `web/static/` lleva `/gachamon/` (salvo, si la hubiera, la marca visible «Gachamon», que no es una dirección).
  - La prueba de la frase de `entrada.js` con el texto aprobado, tal cual.

- [ ] **Step 2: Implementar.** `index.html` y `api.js` toman la dirección de `PREFIJO` (el servidor ya reescribe `__V__` en la portada: reescribe también el prefijo, o el cliente lo deduce de su propia dirección, `import.meta.url`; lo que deje un solo sitio que lo diga). La redirección es una ruta propia de `web/app.py` para `PREFIJO_ANTIGUO` y `PREFIJO_ANTIGUO/{resto:path}`.

- [ ] **Step 3: Mirarlo** con la herramienta de páginas de prueba (`python -m herramientas.pagina_de_prueba`, que hoy imprime direcciones `/gachamon/`: pásala a `/monsteropolis/` en esta tarea): entrar, cuidar, ir a la Tienda; y una página cargada desde `/gachamon/` antes de reiniciar el servicio con el código nuevo sigue funcionando tras el reinicio.

- [ ] **Step 4: Commit** — `feat: el juego vive en /monsteropolis y /gachamon redirige`

### Task 2: Los grupos del arte

**Files:**
- Modify: `web/arte.py`
- Test: `tests/test_web_arte.py` (o donde vivan las del contrato)

**Interfaces:**
- Produces: `arte.Grupo(clave: str, nombre: str, familia: str, rutas: tuple[str, ...])` (inmutable) y `arte.grupos() -> tuple[Grupo, ...]`.

- [ ] **Step 1: Las pruebas que fallan**: toda pieza de `arte.piezas()` está en exactamente un grupo; cada `clave` cumple `^[a-z0-9/_-]{1,64}$` y no termina en `.png`; las claves son únicas; `familia` es la de sus piezas (un grupo no mezcla familias); `nombre` no está vacío y no pasa de 120 letras; un mueble con sus cuatro orientaciones es un solo grupo; un peinado con sus colores y poses, uno solo.
- [ ] **Step 2: Implementar** el corte: la pieza de cada mueble por mueble; paredes y suelo, uno; cada peinado, uno; los cuerpos, uno; la ropa, uno; los iconos por su carpeta; los lugares, uno; las escenas, uno; los efectos, uno; el fondo del pueblo, uno. Los nombres, en castellano, con el nombre del catálogo cuando lo hay (`departamento.MUEBLES[clave].nombre`, `avatar` para peinados).
- [ ] **Step 3: Commit** — `feat: los grupos del arte`

### Task 3: El permiso del dibujante

**Files:**
- Modify: `web/sesion.py`
- Test: `tests/test_web_sesion.py` (o donde vivan las de la sesión)

**Interfaces:**
- Produces: `sesion.puede_dibujar(rowino_uid: int) -> bool` y la dependencia `sesion.dibujante_actual(request) -> Persona`, que lanza el 404 de una ruta que no existe (`{"detail": "Not Found"}`) a quien no tiene el permiso, sin sesión o con la base del sitio sin leer.

- [ ] **Step 1: Las pruebas que fallan**, sobre bases de Rowino de mentira: con `arte_access = 1`, con `is_admin = 1`, con ninguna, con la cuenta bloqueada, **sin la columna `arte_access`** (una base como la de hoy) y sin la columna `is_admin`; y que `buscar_persona` y `persona_actual` contestan exactamente igual en todos esos casos.
- [ ] **Step 2: Implementar** con una consulta aparte, en sólo lectura, que mira qué columnas tiene `users` antes de leerlas.
- [ ] **Step 3: Commit** — `feat: el permiso del dibujante, leído de la base del sitio`

### Task 4: Lo subido, en el servidor

**Files:**
- Create: `arte_subido.py` (las reglas de una subida: validar, reducir, nombrar; puro salvo escribir el archivo en la carpeta que se le pasa)
- Modify: `db.py` (la tabla y sus funciones), `config.py` (`RUTA_ARTE_SUBIDO`)
- Test: `tests/test_arte_subido.py`, `tests/test_db_arte_subido.py`

**Interfaces:**
- Consumes: `arte.piezas()`, `arte.REDUCCION`.
- Produces:
  - tabla `arte_subido (id INTEGER PRIMARY KEY, ruta TEXT NOT NULL, archivo TEXT, ancho INTEGER, alto INTEGER, quien TEXT NOT NULL, cuando TEXT NOT NULL)`: un renglón por subida o vuelta atrás; `archivo` NULL es «el recuadro provisional»;
  - `arte_subido.preparar(cuerpo: bytes, pieza: arte.Pieza) -> tuple[bytes, str]`: el PNG limpio y su nombre (`<sha256 de los bytes limpios>.png`), o `arte_subido.NoVale(mensaje)` con la medida esperada y la recibida;
  - `db.subir_arte(ruta, archivo, ancho, alto, quien, ahora) -> None`, `db.volver_a_la_anterior(ruta, quien, ahora) -> str | None`, `db.volver_al_provisional(ruta, quien, ahora) -> None`, `db.arte_vigente() -> dict[str, tuple[str, int, int]]` (ruta → archivo, ancho, alto, sólo las que tienen imagen), `db.historial_del_arte(ruta) -> list`;
  - `arte_subido.guardar(carpeta: Path, nombre: str, datos: bytes)`: escribe a un temporal en la misma carpeta y lo renombra; `arte_subido.podar(carpeta, ruta, conservar)`: borra del disco lo que ya no está entre las cinco últimas distintas de esa pieza ni es la vigente de ninguna.
- [ ] **Step 1: Las pruebas que fallan** (con PNG fabricados en la prueba, nunca arte del repo modificado): cada caso de «Una subida rara» del Review Focus; el doble de una pieza de la familia `pieza` se reduce a su medida; un PNG con metadatos sale sin ellos; dos subidas iguales dan el mismo nombre; «volver a la anterior» deja un renglón nuevo a nombre de quien vuelve y apunta a la imagen anterior distinta; volver sin anterior vuelve al provisional; la poda no borra la vigente ni una de las cinco; una pieza cuyo contrato cambió de medida no sale en `arte_vigente()`.
- [ ] **Step 2: Implementar.**
- [ ] **Step 3: Commit** — `feat: lo subido por el dibujante, con su historial`

### Task 5: La API del dibujante y el avance

**Files:**
- Create: `web/dibujante.py` (router bajo `/monsteropolis_dibujante/api`)
- Modify: `web/app.py`
- Test: `tests/test_web_dibujante.py`

**Interfaces:**
- Consumes: tareas 2, 3 y 4.
- Produces (todo con `dibujante_actual`; sin permiso, 404):
  - `GET /monsteropolis_dibujante/api/piezas` → los grupos con sus piezas: ruta, medida esperada, si tiene imagen subida, su dirección, quién y cuándo;
  - `POST /monsteropolis_dibujante/api/subir?ruta=<ruta>` con el cuerpo PNG crudo (`X-Gachamon: 1`; hasta 4 MB: lo que pase se corta al leer y se rechaza con 413) → la pieza al día;
  - `POST /monsteropolis_dibujante/api/volver` con `{"ruta", "a": "anterior" | "provisional"}`;
  - `GET /monsteropolis_dibujante/api/historial?ruta=<ruta>`;
  - `GET /monsteropolis_dibujante/api/avance` → **exactamente** el contrato del diseño, calculado desde la tabla, sin abrir imágenes;
  - `GET /monsteropolis_dibujante/api/copia.zip` → todo lo vigente, con su ruta del contrato como nombre dentro del zip.
- [ ] **Step 1: Las pruebas que fallan**: 404 sin permiso en cada ruta (también sin sesión y sin la columna); el contrato del avance campo por campo, con `{"grupos": []}` imposible porque siempre hay grupos; una ruta que no está en el contrato o con `..` da 404; la subida y la vuelta atrás de punta a punta; el zip abre y trae lo vigente.
- [ ] **Step 2: Implementar.**
- [ ] **Step 3: Commit** — `feat: la api del dibujante y el avance del arte`

### Task 6: Lo subido llega a quien juega, y la página del dibujante

**Files:**
- Modify: `web/app.py` (la portada con el bloque de datos; la ruta que sirve lo subido), `web/static/index.html`, `web/static/js/arte.js` (`urlDeArte`)
- Create: `web/static/dibujante.html`, `web/static/js/dibujante.js`, sus estilos (en `estilo.css` o en un archivo propio)
- Test: `tests/test_web_app.py`, `tests/js/arte.test.mjs`, `tests/js/dibujante.test.mjs`, `tests/test_web_cliente.py` (listas de archivos vigilados)

**Interfaces:**
- Produces:
  - `GET /monsteropolis/arte-subido/<sha256>.png`: sólo nombres que la tabla tiene vigentes o en el historial; `Cache-Control: public, max-age=31536000, immutable`; 404 para todo lo demás;
  - la portada del juego lleva `<script type="application/json" id="arte-subido">{"<ruta>": "<dirección>", …}</script>`, armado en cada petición, escapado para que nada cierre la etiqueta;
  - `urlDeArte(ruta)` devuelve la dirección del bloque si la pieza está, y si no, la de siempre; sigue siendo síncrona y nada de lo que la llama cambia;
  - `GET /monsteropolis_dibujante/` sirve la página del dibujante (sin caché), sólo con permiso.
- **Las frases de la página del dibujante** (sólo las ven el dueño y el dibujante): título `Arte de Monsteropolis`; filtro `Sólo lo que falta`; por pieza, `Provisional` o `Subida por {nombre} el {fecha}`, la medida `{ancho} × {alto} px` (y `o {ancho2} × {alto2} px` en la familia de la pieza), botones `Subir`, `Historial`, `Volver a la anterior`, `Volver al provisional`; arriba, `Descargar todo lo subido`; al subir bien, `Listo: ya se ve en el juego.`; los rechazos, con el mensaje del servidor.
- [ ] **Step 1: Las pruebas que fallan**, incluida una que fija que la portada sin nada subido sale con `{}` y otra que fija que una imagen subida que falta en disco da 404 y el cliente pinta el recuadro de esa pieza.
- [ ] **Step 2: Implementar.**
- [ ] **Step 3: Mirarlo** con la herramienta de páginas de prueba y una base de Rowino de mentira que tenga la columna `arte_access` (la herramienta crea la tabla `users` sin ella: añádele una opción `--dibujante N` que la cree y le dé el permiso a la cuenta N): subir una pieza de mueble y verla en el departamento, volver a la anterior, volver al provisional; a 390 × 664 y a 1280.
- [ ] **Step 4: Commit** — `feat: lo subido se ve en el juego, y la página del dibujante`

### Task 7: Documentos y lo de publicar

**Files:**
- Modify: `README.md`, `AGENTS.md` (los invariantes: el permiso se lee aparte, lo subido vive fuera de git, el historial sólo crece y guarda nombres), `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md` (sección de este plan y «Para publicar» del proyecto A del lado del juego), `actualizar-pi.sh` (su copia de seguridad incluye también la carpeta de lo subido, si existe)
- Test: el pre-commit entero

- [ ] **Step 1:** «Para publicar», del lado del juego, con el orden del diseño (nota posterior: el orden bueno es el del diseño corregido, el túnel, el juego y el sitio, y así quedó en los pendientes; lo que sigue es como se escribió): (1) el juego, con permiso expreso; (2) la regla del túnel para `^/(gachamon|monsteropolis|monsteropolis_dibujante)(/.*)?$`, con permiso expreso, comprobada con `curl` desde fuera (y que `/plan/monsteropolis` siga yendo al sitio); (3) el sitio, con su propio permiso y la copia de su base. Cada paso dice qué se hace, cómo se comprueba y qué hacer si falla.
- [ ] **Step 2: Commit** — `docs: las herramientas del dibujante, del lado del juego`
