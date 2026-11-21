# Descargar los provisionales y lo subido — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el dibujante pueda bajar cada provisional a tamaño real, todos juntos en un zip, y la imagen subida de cada pieza.

**Architecture:** Dos rutas nuevas en `web/dibujante.py`, tras el mismo permiso que el resto, sirven los provisionales desde `web/static/arte/`; la página (`dibujante.js`) gana los botones. La imagen subida se baja con un enlace de descarga a la dirección que ya tiene.

**Tech Stack:** FastAPI, Pillow (ya está), JavaScript sin frameworks; pytest y `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-21-descargar-provisionales-design.md`.

## Global Constraints

- Es la **página congelada**, en producción con jugadores reales: sólo se toca la página del dibujante. Nada cambia para quien juega. Nada se sube ni se despliega sin la palabra del dueño.
- Todas las rutas del dibujante exigen su permiso; sin él, el mismo 404 de una ruta que no existe. Respuestas con `Cache-Control: no-store`.
- El provisional sale siempre de `web/static/arte/<ruta>` del repo, nunca de lo subido. Una ruta que no es del contrato se rechaza como ya lo hace `_la_pieza`.
- Familia `pieza`: el doble (`arte.REDUCCION`), ampliado con vecino más próximo.
- Frases (las ven sólo el dueño y el dibujante), tal cual: «Descargar el provisional», «Descargar la imagen subida», «Descargar los provisionales».
- El repo es público: ni direcciones, ni ids, ni rutas de la máquina, ni SHAs.

## Review Focus

- **Una pieza con imagen subida:** «Descargar el provisional» baja el provisional, no la subida.
- **Un mueble:** el provisional baja al doble y, subido tal cual, la página lo acepta y lo reduce al mismo provisional.
- **Una ruta inventada o con `..`:** se rechaza sin tocar el disco.
- **Sin permiso:** las dos rutas nuevas contestan el 404 de siempre.
- **Un provisional que falta en el repo:** la descarga suelta contesta 404; el zip sale sin él y lo avisa en el registro.

---

### Task 1: Las descargas del dibujante

**Files:**
- Modify: `web/dibujante.py`, `web/static/js/dibujante.js`, `web/static/estilo.css` (sólo si los botones lo piden)
- Test: `tests/test_web_dibujante.py`, `tests/js/dibujante.test.mjs`

**Interfaces:**
- Produces:
  - `GET /monsteropolis_dibujante/api/provisional?ruta=<ruta>` → `image/png`, `Content-Disposition: attachment; filename="provisional-<ruta con «/» cambiado por «-»>"`.
  - `GET /monsteropolis_dibujante/api/provisionales.zip` → `application/zip`, `attachment; filename="provisionales.zip"`; cada entrada es `<clave del grupo>/<último tramo de la ruta>` (si en un grupo se repite ese nombre, la ruta entera con guiones).

- [ ] **Step 1: Las pruebas que fallan** en `tests/test_web_dibujante.py`: `test_el_provisional_baja_en_la_medida_de_la_pieza` (el PNG devuelto mide `pieza.ancho × pieza.alto` para una pieza que no es de la familia `pieza`, y sus bytes son los del archivo del repo); `test_el_provisional_de_un_mueble_baja_al_doble` (mide el doble, y `arte_subido.preparar` lo acepta y lo reduce a los mismos píxeles que el archivo del repo); `test_el_provisional_no_es_lo_subido` (con una imagen subida para esa pieza, baja el provisional); `test_una_ruta_que_no_es_del_contrato_se_rechaza` (también con `..`); `test_un_provisional_que_falta_es_404`; `test_el_zip_trae_cada_provisional_en_la_carpeta_de_su_grupo` (tantas entradas como piezas con archivo, sin nombres repetidos, cada una bajo la clave de su grupo); `test_sin_permiso_las_descargas_no_existen` (404 en las dos, igual que una ruta inexistente); `test_las_descargas_no_se_guardan` (`no-store`). En `tests/js/dibujante.test.mjs`: `cada pieza ofrece descargar su provisional` (enlace con el atributo `download` a `provisional?ruta=…`), `sólo la pieza con imagen subida ofrece descargarla` (enlace `download` a la dirección de la subida), `arriba se ofrecen los provisionales` (enlace a `provisionales.zip`).
- [ ] **Step 2:** Correrlas y ver que fallan.
- [ ] **Step 3:** Implementar. El zip, como `la_copia`: en un temporal, a trozos, cerrado también si la descarga se corta.
- [ ] **Step 4:** La suite entera pasa (`python -m pytest -q` y `node --test tests/js/*.test.mjs`) y `git diff --check` sale limpio.
- [ ] **Step 5:** Commit: `feat: el dibujante descarga los provisionales y lo subido`.
