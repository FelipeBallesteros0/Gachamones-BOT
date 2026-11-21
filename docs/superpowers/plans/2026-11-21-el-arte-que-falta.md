# El arte que falta — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el dibujante pueda subir, descargar y seguir en el tablero, a la medida del ejecutable, todo el arte que el juego todavía no tiene: la pieza a 1024 × 512 por casilla, los encendidos, los 24 objetos nuevos con sus íconos y las capas de las criaturas.

**Architecture:** `web/arte.py` gana una segunda lista, los lugares de subida (`arte.lugares()`), al lado del contrato del juego (`arte.piezas()`), que no cambia. Cada subida guarda el original y una versión chica derivada. La tabla `arte_subido` conserva `archivo, ancho, alto` como lo servido y gana el original en tres columnas nuevas, así que la portada y el mundo en línea del ejecutable leen igual que hoy. La página del dibujante pliega las criaturas por especie y las pide al abrirlas.

**Tech Stack:** Python 3.12, FastAPI, SQLite, Pillow 12.3.0 (con `ImageCms`), JavaScript sin frameworks; pytest y `node --test` (corre dentro de pytest por `tests/test_web_js.py`).

**Spec:** `docs/superpowers/specs/2026-11-21-el-arte-que-falta-design.md`.

## Global Constraints

- Es la **página congelada**, con jugadores reales. Sólo evoluciona la página del dibujante. **Nada cambia para quien juega**: `arte.piezas()` sigue con 270 piezas y su medida servida, y no cambian ni `web/static/datos/arte.json`, ni `arte_subido.medidas()`, ni `db.arte_vigente`, ni `urlDeArte`. El bloque `arte-subido` de la portada nunca lleva un lugar que el juego no pinta.
- Las columnas `ruta, archivo, ancho, alto` de `arte_subido` conservan su nombre y su significado (lo servido): el mundo en línea del ejecutable las lee por su nombre, en sólo lectura.
- Nada nuevo va bajo `web/static/` salvo `dibujante.js` y `dibujante.css`. Los provisionales nuevos viven en `web/arte_por_venir/<ruta>`.
- **Medidas de subida.** Familia `pieza`, el doble de lo servido (1024 × 512 por casilla), también el suelo y las paredes:

  | Forma | Medida de subida |
  |---|---|
  | Suelo; mueble plano 1 × 1 | 1024 × 512 |
  | Tramo de pared; lo de pared de 1 tramo | 512 × 1280 |
  | Lo de pared de 2 tramos | 1024 × 1536 |
  | Bulto 1 × 1 | 1024 × 1536 |
  | Bulto 2 × 1 | 1536 × 1792 |
  | Plano 2 × 2 | 2048 × 1024 |
  | Bulto 2 × 2 | 2048 × 2048 |
  | Balcón (4 × 1 por fuera de la pared) | 2560 × 2304 |

  Familia `criaturas`: 1024 × 1024. Las demás familias (también los íconos nuevos, de 48 × 48): su medida de hoy.
- **Versión chica:** en `pieza`, la mitad con `LANCZOS` (`arte_subido.a_lo_servido`, la misma reducción de `herramientas/pieza.py`); en `criaturas`, un cuarto con `LANCZOS` (256 × 256); en las demás, ninguna (es el mismo archivo).
- **Tope de peso:** `LIMITE_DE_BYTES = 24 * 1024 * 1024`, con la frase «La imagen pesa más de 24 MB.».
- **Color:** al limpiar, un PNG con un perfil de color RGB que se pueda leer pasa a sRGB, con el intento colorimétrico relativo y el alfa intacto, y se guarda sin perfil. Sin perfil, o con uno ilegible o que no es RGB, se deja como hoy: el perfil se descarta, y si no se pudo leer queda un aviso en el registro.
- **Rutas.** Lo de hoy no cambia. Lo nuevo, tal cual:
  - encendido: `pieza/muebles/<clave>-encendido-<o>.png` (la Puerta de cristal, `pieza/muebles/puerta_cristal-atravesable-<o>.png`);
  - objeto nuevo: `pieza/muebles/<clave>-<o>.png` y su ícono, `iconos/muebles/<clave>.png`;
  - criaturas: `criaturas/<especie>/<etapa>/cuerpo-<o>.png`, `criaturas/<especie>/<etapa>/cara-<ánimo>-<o>.png`, `criaturas/<especie>/<etapa>/sombrero-<sombrero>-<o>.png`, las mismas sin `<etapa>/` para toda la especie, y `criaturas/comun/cara-…` y `criaturas/comun/sombrero-…`.

  `<especie>` es la clave de `especies.ESPECIES` (`dragoncito`, no `tsushimon`). `<etapa>`, una de `bebe`, `nino`, `adolescente`, `adulto` y `adulto_grande`. `<ánimo>`, una de `feliz`, `normal` y `mal`. `<sombrero>`, una clave de `cosmeticos.SOMBREROS`. `<o>`, una de `se`, `so`, `no` y `ne`; la cara sólo lleva `se` y `so`, y lo que va en una pared (el balcón también) sólo `se` (pared izquierda) y `so` (pared derecha).
- **Los 24 objetos** (clave, nombre, forma, segundo estado), fijados por el diseño, que la rama del ejecutable adoptará tal cual:

  | Clave | Nombre | Forma | Segundo estado |
  |---|---|---|---|
  | `consola_flappy` | Consola Flappy | bulto 1 × 1 | — |
  | `consola_pong` | Consola Pong | bulto 1 × 1 | — |
  | `mesa_gato` | Mesa de gato | bulto 1 × 1 | — |
  | `atril` | Atril | bulto 1 × 1 | — |
  | `tocadiscos` | Tocadiscos | bulto 1 × 1 | `encendido` |
  | `mayordomo` | Mayordomo robot | bulto 1 × 1 | — |
  | `puerta_cristal` | Puerta de cristal | bulto 1 × 1 | `atravesable` |
  | `cableados` | Bloque de cableados | bulto 1 × 1 | — |
  | `super_dado` | Súper Dado | bulto 1 × 1 | — |
  | `mega_tv` | Mega TV | bulto 2 × 1 | `encendido` |
  | `lampara_dragon` | Lámpara Dragón | bulto 1 × 1 | `encendido` |
  | `silla_<color>` | Silla azul, roja, verde, amarilla, negra, blanca | bulto 1 × 1 | — |
  | `mesa_<color>` | Mesa azul, roja, verde, amarilla, negra, blanca | bulto 1 × 1 | — |
  | `balcon` | Balcón | 4 × 1 por fuera de la pared | — |

  Los colores son `azul`, `roja`, `verde`, `amarilla`, `negra` y `blanca`. Del juego, llevan encendido `lampara`, `calefactor`, `chimenea` y `fuente`.
- **Grupos:** cada objeto nuevo es un grupo `pieza/muebles/<clave>`, de familia `pieza`, con su encendido dentro. El encendido de los cuatro del juego entra en el grupo de hoy de su mueble. Los íconos nuevos entran en `iconos/muebles` («Iconos de los muebles»). Cada especie es un grupo `criaturas/<especie>`, de familia `criaturas`, con el nombre de la especie. `criaturas/comun` («Capas comunes a todas las especies») sale en la página pero **no en el avance**.
- **Cuentas:** 126 dibujos nuevos de la pieza (110 de los objetos y 16 encendidos), 24 íconos y 5 030 lugares de criaturas (4 250 de forma, 750 de especie y 30 comunes). Una especie tiene 170 casillas en el avance. El avance pasa de 35 a 84 grupos, y la página arriba tiene 420 lugares.
- **Lo que se conserva:** las cinco últimas imágenes distintas de cada lugar, contadas por su original, y de cada una los dos archivos.
- **Frases** (sólo las ven el dueño y el dibujante), tal cual, en la tabla «Frases».
- El repo es público: ni direcciones, ni ids, ni rutas de la máquina, ni SHAs. Nada se sube, se despliega ni se publica sin la palabra del dueño.
- Antes de cada commit, la verificación de `AGENTS.md`: `./venv/bin/python -m pre_commit run --all-files` (compila y corre la suite entera, también las pruebas de JavaScript) y `git diff --check`.

### Frases

| Dónde | Texto |
|---|---|
| Botón de arriba (antes «Descargar lo que se ve») | «Descargar lo subido» |
| Botón de arriba (se queda) | «Descargar los provisionales» |
| En cada especie | «Descargar lo subido de {especie}» · «Descargar los provisionales de {especie}» |
| Título de la sección | «Criaturas» |
| Resumen de cada grupo | «{nombre} · {hechas} de {total}» |
| Etapas | «Cría» · «Niño» · «Adolescente» · «Adulto» · «Adulto grande» · «Para todas las etapas de {especie}» |
| Capas | «Cuerpo» · «Caras» · «Sombreros» |
| Tarjeta de criatura | «Cuerpo · {orientación}» · «Cara {feliz/normal/mal} · {orientación}» · «{sombrero} · {orientación}» |
| Orientaciones | «se · de frente, hacia abajo a la derecha» · «so · de frente, hacia abajo a la izquierda» · «no · de espaldas, hacia arriba a la izquierda» · «ne · de espaldas, hacia arriba a la derecha» |
| Mientras pide una especie | «Cargando las capas…» |
| Otra medida (reemplaza la de hoy) | «Lo subido mide {a} × {b} px y este lugar pide {A} × {B} px: hay que volver a subirlo.» |
| Tope | «La imagen pesa más de 24 MB.» |
| Nota del encendido | «El dibujo de siempre es el apagado; éste es el encendido.» |
| Nota de la Puerta de cristal atravesable | «La de siempre es la sólida; ésta es la que se puede atravesar.» |
| Nota del mayordomo | «Alto como tu avatar: unos 717 px del original, de pie en el centro de la casilla.» |
| Nota del balcón | «La tira de 4 × 1 casillas que queda por fuera de la pared, con su baranda. Como lo de pared: «se» va en la pared izquierda y «so», en la derecha.» |
| Notas de las criaturas | «Cada capa mide 1024 × 1024 y se apila con las demás de su etapa en el mismo lienzo. De espaldas no lleva cara.» · «El provisional es la capa de frente de hoy, ampliada: dice dónde va y de qué tamaño, no cómo se ve de lado ni de espaldas.» |
| Casilla cubierta | «Usa la de toda la especie.» · «Usa la común.» |
| Confirmación al volver atrás una capa de especie | «Esta capa la usan todas las etapas de {especie} que no tienen la suya. ¿Seguir?» |
| Confirmación al volver atrás una capa común | «Esta capa la usan todas las especies que no tienen la suya. ¿Seguir?» |
| Nombres de los grupos nuevos | los de la tabla de los 24 objetos (cada silla y cada mesa con su color: «Silla azul», «Mesa roja»…), los de las especies y «Capas comunes a todas las especies» |

## Review Focus

- **Una subida de la medida chica.** Un PNG de 512 × 768 para `pieza/muebles/maceta-se.png` se rechaza con «La imagen mide 512 × 768 px y esta pieza pide 1024 × 1536 px.» y no deja renglón ni archivo. Una fila sin original de 512 × 768 (de antes de publicar) se sigue viendo en el juego (el bloque de la portada la trae) y cuenta como pendiente: `hechas` no la cuenta y la página enseña el aviso de otra medida. Lo fija la Task 2 (`test_una_fila_sin_original_se_sigue_viendo_y_cuenta_como_pendiente`).
- **Una capa compartida que se vuelve al provisional.** Con `criaturas/pulpo/cara-feliz-se.png` al día, las cinco casillas `cara-feliz-se` de Octopul que no tienen la suya cuentan como hechas. Al volverla al provisional vuelven a faltar, y las de otras especies no se mueven. La página pide confirmación antes de mandar nada, y si se cancela no manda nada. Lo fijan la Task 8 (`test_volver_una_capa_de_la_especie_al_provisional_descubre_sus_casillas`) y la Task 9 (`volver atrás una capa compartida pide confirmación y, si se cancela, no manda nada`).
- **Un PNG con perfil de color.** Uno con un perfil tipo Display P3 sale convertido a sRGB y sin el trozo `iCCP`. Uno sin perfil sale con los píxeles intactos. Uno con un perfil ilegible sale como hoy, con el perfil descartado y un aviso en el registro. Lo fija la Task 3 (`test_un_png_con_perfil_p3_sale_en_srgb_y_sin_perfil`).
- **Una especie con cientos de capas, abierta en un teléfono.** `GET …/api/piezas` no trae ninguna capa de criatura (sus grupos llegan sin `piezas`). La página no crea ni una tarjeta de criatura ni pide una imagen hasta abrir la especie, y dentro, hasta abrir cada sección. Las miniaturas son de 256 o el provisional sin ampliar. Lo fijan la Task 8 (`test_la_lista_general_no_trae_las_capas_de_las_criaturas`) y la Task 9 (`una especie no se pide ni se arma hasta abrirla`).
- **Un archivo de 24 MB a medio subir.** Un cuerpo que declara más de 24 MB recibe un 413 con «La imagen pesa más de 24 MB.» sin leerse. Uno que llega cortado se rechaza sin renglón ni archivo. Uno de 2560 × 2304 que pesa menos de 24 MB vale para el balcón. Lo fijan la Task 2 (`test_un_png_de_24_mb_vale_y_uno_de_un_byte_mas_no`) y la Task 4 (`test_una_subida_cortada_no_deja_renglon_ni_archivo`).

---

### Task 1: La tabla guarda el original

**Files:**
- Modify: `db.py`
- Test: `tests/test_db_arte_subido.py`

**Interfaces:**
- Consumes: nada nuevo.
- Produces:
  - Columnas nuevas de `arte_subido`: `original TEXT`, `ancho_original INTEGER`, `alto_original INTEGER`, que pueden ir vacías. Van en el `CREATE TABLE` y en `MIGRACIONES_DE_TABLAS` (la base de hoy las gana al arrancar). Sin `CHECK` nuevos: la regla la comprueba el código.
  - `db.subir_arte(ruta, archivo, ancho, alto, quien, ahora, *, original: str | None = None, ancho_original: int | None = None, alto_original: int | None = None) -> None`: las tres o ninguna (si no, `ValueError`), y `original` con la forma de `_ARCHIVO_DE_ARTE`.
  - `@dataclass(frozen=True) class ArtePuesto: archivo: str; ancho: int; alto: int; original: str; ancho_original: int; alto_original: int`.
  - `db.arte_puesto_entero() -> dict[str, ArtePuesto]`: lo puesto de cada ruta, en una consulta. Sin original, el original es el propio archivo con su medida (`COALESCE` en la consulta).
  - `RenglonDelArte` gana `original: str | None`, `ancho_original: int | None`, `alto_original: int | None`, resueltos igual (vacíos sólo en el provisional).
  - `volver_a_la_anterior(ruta, quien, ahora, en_disco)`: misma firma. La identidad de una imagen es `COALESCE(original, archivo)`. `en_disco` se llama con el archivo y con el original, y tienen que estar los dos. La fila de la vuelta copia el original y su medida de la subida a la que vuelve.
  - `archivos_que_se_conservan()` y `podar_arte(borrar)`: las cinco últimas imágenes por identidad, con sus dos archivos. Los conocidos incluyen los originales.
  - `arte_puesto()`, `arte_vigente()` y `quien_subio_lo_puesto()` no cambian.

- [ ] **Step 1: Las pruebas que fallan** en `tests/test_db_arte_subido.py`:
  - `test_subir_con_original_lo_deja_puesto_con_su_medida`: `arte_puesto_entero()` trae el original y 1024 × 1536 junto al archivo de 512 × 768.
  - `test_una_fila_sin_original_tiene_por_original_su_archivo`.
  - `test_el_original_va_con_su_medida_o_no_va` (con uno o dos de los tres, `ValueError` y ningún renglón).
  - `test_arte_vigente_y_arte_puesto_no_cambian_con_el_original`.
  - `test_volver_a_la_anterior_copia_el_original_y_su_medida`.
  - `test_volver_a_la_anterior_salta_la_subida_cuyo_original_no_esta_en_disco`.
  - `test_dos_originales_distintos_con_la_misma_version_chica_son_dos_imagenes`.
  - `test_se_conservan_el_archivo_y_el_original_de_las_cinco_ultimas`.
  - `test_la_poda_borra_el_original_que_ya_no_se_conserva`.
  - `test_el_historial_trae_el_original_y_su_medida`.
  - `test_una_base_de_antes_gana_las_tres_columnas_al_arrancar_sin_perder_filas`.
  - `test_una_lectura_de_ruta_archivo_ancho_alto_sigue_funcionando`: la consulta que hace el mundo en línea, copiada tal cual, sobre filas con y sin original.
- [ ] **Step 2:** Correrlas y ver que fallan.
- [ ] **Step 3:** Implementar. `_anotar_arte_en` gana las tres columnas.
- [ ] **Step 4: Medir.** Con 10 000 filas sintéticas (5 000 rutas × 2 subidas), medir `arte_vigente(medidas)` y `archivos_que_se_conservan()`. Si alguna pasa de 20 ms en la máquina de trabajo, añadir `CREATE INDEX IF NOT EXISTS arte_subido_por_ruta ON arte_subido(ruta, id)` en `SCHEMA_INDICES` y volver a medir. Las dos cifras van en el mensaje del commit.
- [ ] **Step 5:** La suite entera pasa y `git diff --check` sale limpio.
- [ ] **Step 6:** Commit: `feat: la tabla del arte guarda el original de cada subida`.

### Task 2: La subida a la medida nueva

**Files:**
- Modify: `web/arte.py`, `arte_subido.py`, `web/dibujante.py`, `herramientas/pieza.py` (sólo si deja de compilar)
- Test: `tests/test_arte.py`, `tests/test_arte_pieza.py`, `tests/test_arte_subido.py`, `tests/test_web_dibujante.py`, `tests/test_web_app.py`

**Interfaces:**
- Consumes: `db.subir_arte(..., original=, ancho_original=, alto_original=)`, `db.arte_puesto_entero()` (Task 1).
- Produces:
  - `web/arte.py`:
    - `@dataclass(frozen=True) class Lugar: ruta: str; ancho: int; alto: int; familia: str; reduccion: int; en_el_juego: bool; objeto: str | None = None; estado: str | None = None; criatura: "Capa | None" = None`. `ancho` y `alto` son la medida de subida. `objeto` es la clave del mueble en `pieza/muebles/*` y en `iconos/muebles/*`.
    - `lugares() -> tuple[Lugar, ...]`, con `functools.cache`. En esta tarea son sólo los 270 del juego: los de la familia `pieza` con `reduccion=2` y medida ×2, los demás con `reduccion=1`.
    - `lugar_de(ruta: str) -> Lugar | None`, con un índice que se arma una vez.
    - `olvidar() -> None`, que vacía las dos cachés (para las pruebas que cambian catálogos).
    - `grupos()` se arma desde `lugares()`, con el mismo resultado que hoy.
  - `arte_subido.py`:
    - `LIMITE_DE_BYTES = 24 * 1024 * 1024`; `PESA_DEMASIADO = "La imagen pesa más de 24 MB."`.
    - `@dataclass(frozen=True) class Imagen: datos: bytes; nombre: str; ancho: int; alto: int`.
    - `preparar(cuerpo: bytes, lugar: arte.Lugar) -> tuple[Imagen, Imagen]`: el original y la chica. La chica es el mismo objeto si `reduccion == 1`. La cabecera se mira contra `lugar.ancho × lugar.alto` antes de abrir nada. Desaparece `pieza_de`.
    - `subir(carpeta, lugar, cuerpo, quien, ahora) -> str` (el nombre de la chica): escribe los dos, anota con el original, vuelve a escribir los dos y poda. `volver` no cambia de firma, y su `en_disco` mira el nombre que le pasen.
  - `web/dibujante.py`:
    - `_el_lugar(ruta) -> arte.Lugar` (el 404 de siempre).
    - La vista lleva `ancho`, `alto` (la medida de subida), `subida` (sólo si está **al día**: el original mide `lugar.ancho × lugar.alto`), con `"original": direccion_de(original)` además de `direccion`, `quien` y `cuando`.
    - `medida_cambiada: {"ancho", "alto"}` (la del original puesto) si no está al día.
    - `GET …/api/avance`: `hechas` cuenta los lugares al día.
    - `_al_dia(puesto: dict[str, db.ArtePuesto]) -> set[str]`.

- [ ] **Step 1: Las pruebas que fallan:**
  - `test_el_contrato_tiene_sus_270_piezas` y `test_el_cliente_recibe_el_mismo_contrato` siguen igual.
  - `test_los_lugares_de_hoy_son_las_270_piezas_y_la_pieza_se_sube_al_doble`: suelo 1024 × 512, `pieza/pared-izquierda.png` 512 × 1280, `pieza/muebles/maceta-se.png` 1024 × 1536, `pieza/muebles/fuente-ne.png` 2048 × 2048; un ícono, 48 × 48 con `reduccion=1`.
  - `test_un_mueble_al_doble_sale_con_su_original_y_su_version_servida` (original 1024 × 1536 y chica 512 × 768 igual a `a_lo_servido` del original).
  - `test_la_medida_servida_de_un_mueble_se_rechaza_nombrando_la_de_subida`: «La imagen mide 512 × 768 px y esta pieza pide 1024 × 1536 px.».
  - `test_fuera_de_la_pieza_el_original_y_la_chica_son_el_mismo_archivo`.
  - `test_un_png_de_24_mb_vale_y_uno_de_un_byte_mas_no`: reemplaza la de 4 MB. Un PNG de la medida de su lugar, completado con un trozo auxiliar hasta los 24 MB justos, vale; con un byte más, `NoVale` con «La imagen pesa más de 24 MB.».
  - `test_la_bomba_de_descompresion_se_rechaza_sin_abrirla`, contra la medida de subida.
  - En `tests/test_web_dibujante.py`:
    - `test_subir_un_mueble_al_doble_lo_deja_al_dia_y_la_portada_sirve_la_chica`: el bloque `arte-subido` lleva la dirección de la de 512 × 768.
    - `test_una_fila_sin_original_se_sigue_viendo_y_cuenta_como_pendiente`.
    - `test_la_vista_pide_la_medida_de_subida`.
    - `test_el_413_dice_24_mb`.
  - En `tests/test_web_app.py`: `test_el_bloque_de_la_portada_sigue_vacio_sin_nada_subido`.
- [ ] **Step 2:** Correrlas y ver que fallan.
- [ ] **Step 3:** Implementar. La prueba de hoy `test_en_la_pieza_el_doble_se_rechaza…` se da vuelta: ahora lo que se rechaza es la medida servida.
- [ ] **Step 4:** La suite entera pasa y `git diff --check` sale limpio.
- [ ] **Step 5:** Commit: `feat: la pieza se sube a 1024 × 512 por casilla y se guarda el original`.

### Task 3: El color pasa a sRGB

**Files:**
- Modify: `arte_subido.py`
- Create: `tests/perfiles_de_color.py`, un ayudante de las pruebas
- Test: `tests/test_arte_subido.py`

**Interfaces:**
- Consumes: `preparar` (Task 2).
- Produces: `_a_srgb(rgba: Image.Image, perfil: bytes | None) -> Image.Image`, que `preparar` llama después de `_a_rgba`, con el `icc_profile` leído de la imagen abierta. Convierte con `ImageCms`: los tres canales de color, de ese perfil a `ImageCms.createProfile("sRGB")`, con el intento colorimétrico relativo; el alfa se separa antes y se vuelve a juntar intacto. Sin perfil, o con uno ilegible o que no es RGB, devuelve la imagen igual, y en el caso ilegible deja un `logger.warning`.
- El ayudante `perfil_rgb(primarios, blanco, gamma) -> bytes` escribe un perfil ICC v2 de matriz y curva (los colorantes adaptados a D50, `wtpt`, `rTRC`/`gTRC`/`bTRC` con una sola gamma). No se commitea ningún `.icc` de fuera.

- [ ] **Step 1: Las pruebas que fallan:**
  - `test_un_png_con_perfil_p3_sale_en_srgb_y_sin_perfil`: con primarios P3, D65 y gamma 2,2, un píxel (200, 100, 50) sale con el rojo ≥ 200, el verde ≤ 100 y el azul ≤ 50, al menos un canal se mueve 5 o más, no queda `iCCP` y el alfa no cambia.
  - `test_un_png_con_perfil_srgb_sale_casi_igual` (cada canal a ±1).
  - `test_un_png_sin_perfil_sale_con_los_pixeles_intactos`.
  - `test_un_perfil_ilegible_se_descarta_y_se_avisa`: la prueba de hoy con `icc_profile=b"un perfil de color"` sigue pasando, y además hay un aviso.
  - `test_un_gris_con_perfil_se_deja_como_hoy`.
- [ ] **Step 2:** Correrlas y ver que fallan.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** La suite entera pasa y `git diff --check` sale limpio.
- [ ] **Step 5:** Commit: `feat: lo que sube el dibujante con perfil de color se pasa a sRGB`.

### Task 4: Lo que se ve y se baja a la medida nueva

**Files:**
- Modify: `web/dibujante.py`, `web/static/js/dibujante.js`
- Test: `tests/test_web_dibujante.py`, `tests/test_web_app.py`, `tests/js/dibujante.test.mjs`

**Interfaces:**
- Consumes: `arte.lugar_de`, `Lugar`, `db.arte_puesto_entero`, `RenglonDelArte.original` (Tasks 1 y 2).
- Produces:
  - `GET …/api/historial?ruta=`: cada renglón `{"accion", "direccion", "original", "ancho", "alto", "quien", "cuando"}`, con `ancho` y `alto` del original y `original` = `direccion_de(original)` (`null` en el provisional).
  - `GET …/api/provisional?ruta=`, a la medida de subida:
    - familia `pieza`: `fuentes/<ruta>` si existe; si no, el provisional servido ampliado ×2 con `NEAREST`;
    - las demás familias: el archivo tal cual.
  - Con `&miniatura=1`, el provisional sin ampliar, como `image/png` sin `Content-Disposition`. El provisional servido sale de `arte.RAIZ` si el lugar está en el juego.
  - `GET …/api/copia.zip`: el **original** de cada lugar con algo puesto (al día o no), con su ruta como nombre.
  - `/monsteropolis/arte-subido/<original>` sirve el original (sale de `archivos_que_se_conservan`, Task 1).
  - En `dibujante.js`:
    - «Descargar la imagen subida» apunta a `subida.original`;
    - `avisoDeMedida(pieza)` dice «Lo subido mide {a} × {b} px y este lugar pide {A} × {B} px: hay que volver a subirlo.»;
    - el botón de arriba dice «Descargar lo subido».

- [ ] **Step 1: Las pruebas que fallan:**
  - `test_el_provisional_de_un_mueble_baja_al_doble_sin_suavizar`: 1024 × 1536, cada píxel del repo como un cuadrado de 2 × 2.
  - `test_si_fuentes_tiene_el_original_el_provisional_es_ese`.
  - `test_la_miniatura_del_provisional_es_la_del_repo_sin_ampliar`.
  - `test_el_provisional_de_un_icono_baja_tal_cual`.
  - `test_descargar_la_imagen_subida_baja_el_original`.
  - `test_la_copia_trae_los_originales_con_su_ruta`.
  - `test_el_historial_dice_la_medida_del_original`.
  - `test_una_subida_cortada_no_deja_renglon_ni_archivo`.
  - `test_el_original_se_sirve_por_su_nombre` (en `tests/test_web_app.py`).
  - En `tests/js/dibujante.test.mjs`: `descargar la imagen subida apunta al original`, `el aviso de otra medida nombra las dos medidas` y `arriba dice «Descargar lo subido»`.
- [ ] **Step 2:** Correrlas y ver que fallan.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** La suite entera pasa y `git diff --check` sale limpio.
- [ ] **Step 5:** Commit: `feat: el dibujante ve y descarga la medida nueva y el original`.

### Task 5: El encendido de los cuatro muebles del juego

**Files:**
- Modify: `web/arte.py`, `herramientas/rellenos.py`, `web/dibujante.py`
- Create: `web/arte_por_venir/pieza/muebles/<clave>-encendido-<o>.png` (16, generados por `herramientas/rellenos.py`)
- Test: `tests/test_arte.py`, `tests/test_web_dibujante.py`

**Interfaces:**
- Consumes: `Lugar`, `lugares()`, `grupos()` (Task 2); `/provisional` (Task 4).
- Produces:
  - `arte.RAIZ_POR_VENIR = Path(__file__).parent / "arte_por_venir"`.
  - `arte.ENCENDIDOS: dict[str, str] = {"lampara": "encendido", "calefactor": "encendido", "chimenea": "encendido", "fuente": "encendido"}`.
  - `lugares()` añade, detrás de los del juego, `pieza/muebles/<clave>-encendido-<o>.png` para cada uno, con las cuatro orientaciones, a la medida de subida de su mueble, `en_el_juego=False`, `objeto=<clave>` y `estado="encendido"`.
  - `_grupo_de` los mete en `pieza/muebles/<clave>`, que pasa de 4 a 8 rutas.
  - `rellenos.generar()` escribe también, en `RAIZ_POR_VENIR` y a la medida servida (`ancho // reduccion`), el relleno de cada lugar de la familia `pieza` o `iconos` que no está en el juego. El encendido es el relleno de su mueble con un renglón más: las tres primeras letras del estado en mayúsculas («ENC», «ATR»).
  - `/provisional` saca de `RAIZ_POR_VENIR` lo que no está en el juego.
  - La vista gana `"objeto"` y `"estado"`.

- [ ] **Step 1: Las pruebas que fallan:**
  - `test_los_cuatro_del_juego_tienen_su_encendido_en_su_grupo` (el grupo de `lampara` con 8 rutas, las de hoy primero y en su orden).
  - `test_el_encendido_mide_lo_mismo_que_su_mueble`.
  - `test_el_encendido_no_entra_al_contrato_del_juego` (`arte.piezas()` sigue con 270; `arte.json` igual).
  - `test_cada_lugar_por_venir_tiene_su_provisional_y_no_sobra_ninguno` (`web/arte_por_venir/` contra los lugares de `pieza` e `iconos` fuera del juego; cada uno a su medida servida).
  - `test_el_relleno_del_encendido_no_es_el_del_apagado`.
  - `test_subir_un_encendido_no_toca_la_portada` (el bloque no lo trae).
  - `test_el_provisional_del_encendido_baja_al_doble`.
- [ ] **Step 2:** Correrlas y ver que fallan.
- [ ] **Step 3:** Implementar y generar los rellenos con `./venv/bin/python -m herramientas.rellenos`. `web/static/` no cambia.
- [ ] **Step 4:** La suite entera pasa y `git diff --check` sale limpio.
- [ ] **Step 5:** Commit: `feat: el encendido de la lámpara, el calefactor, la chimenea y la fuente`.

### Task 6: Los 24 objetos nuevos y sus íconos

**Files:**
- Modify: `web/arte.py`, `herramientas/rellenos.py`
- Create: `web/arte_por_venir/pieza/muebles/…` (110) y `web/arte_por_venir/iconos/muebles/<clave>.png` (24), generados
- Test: `tests/test_arte.py`, `tests/test_arte_subido.py`, `tests/test_web_dibujante.py`

**Interfaces:**
- Consumes: `RAIZ_POR_VENIR`, los rellenos por venir y la vista con `objeto`/`estado` (Task 5).
- Produces:
  - `arte.FUERA = "fuera"`: la forma del balcón.
  - `@dataclass(frozen=True) class Objeto: clave: str; nombre: str; ancho: int = 1; fondo: int = 1; capa: str = departamento.BULTO; estado: str | None = None`.
  - `arte.POR_VENIR: tuple[Objeto, ...]`: los 24 de la tabla, en ese orden (cada silla y cada mesa en el orden de colores), y el balcón `Objeto("balcon", "Balcón", ancho=4, fondo=1, capa=FUERA)`.
  - `tamano_de_mueble` acepta un `Objeto`. Con `FUERA` mide como un bulto de su huella: 1280 × 1152 servido y 2560 × 2304 de subida.
  - `lugares()` añade, detrás de los encendidos: los dibujos (4 orientaciones, o `se` y `so` con `FUERA`; con su estado, otras 4 `<clave>-<estado>-<o>`) y después los íconos `iconos/muebles/<clave>.png` de 48 × 48.
  - `grupos()`: un grupo `pieza/muebles/<clave>` por objeto, con `nombre` de la tabla y familia `pieza`. Los íconos caen en `iconos/muebles`.
  - El relleno del balcón es una caja sobre su huella de 4 × 1: en `balcon-se` la tira corre a lo largo de la pared izquierda, de arriba a la derecha hacia abajo a la izquierda; en `balcon-so`, a lo largo de la derecha. Su baranda tiene la altura de la pared.

- [ ] **Step 1: Las pruebas que fallan:**
  - `test_los_24_objetos_y_sus_claves` (las claves de la tabla, ninguna en `departamento.MUEBLES`).
  - `test_los_objetos_nuevos_tienen_110_dibujos_y_24_iconos`.
  - `test_las_medidas_de_los_objetos_nuevos`: `consola_flappy-se` 1024 × 1536, `mega_tv-ne` 1536 × 1792, `balcon-se` 2560 × 2304, `iconos/muebles/balcon.png` 48 × 48.
  - `test_el_balcon_solo_tiene_se_y_so`.
  - `test_la_puerta_de_cristal_atraviesa_y_no_se_enciende`.
  - `test_los_objetos_nuevos_no_entran_al_juego` (`piezas()` 270, `arte.json` igual, `departamento.a_la_venta()` igual).
  - `test_cada_objeto_es_un_grupo_con_su_nombre_y_sus_dos_estados`.
  - `test_los_iconos_nuevos_van_con_los_de_los_muebles` (el grupo pasa de 19 a 43).
  - `test_las_rutas_nuevas_pasan_el_filtro_del_cliente_y_de_la_tabla` (`esRutaDeArte` y `_RUTA_DE_ARTE`).
  - `test_el_balcon_de_su_medida_vale` (que completa la del tope de la Task 2 con un PNG real de 2560 × 2304 de menos de 24 MB).
- [ ] **Step 2:** Correrlas y ver que fallan.
- [ ] **Step 3:** Implementar y generar los rellenos.
- [ ] **Step 4:** La suite entera pasa y `git diff --check` sale limpio.
- [ ] **Step 5:** Commit: `feat: los objetos que el juego todavía no tiene, con sus íconos`.

### Task 7: Las capas de las criaturas

**Files:**
- Modify: `web/arte.py`, `retrato.py`, `web/dibujante.py`
- Test: `tests/test_arte.py`, `tests/test_retrato.py`, `tests/test_arte_subido.py`, `tests/test_web_dibujante.py`

**Interfaces:**
- Consumes: `Lugar` (Task 2); `/provisional` (Task 4).
- Produces:
  - `@dataclass(frozen=True) class Capa: nivel: str; especie: str | None; etapa: str | None; capa: str; cual: str | None; orientacion: str`:
    - `nivel` es `"forma"`, `"especie"` o `"comun"`;
    - `capa` es `"cuerpo"`, `"cara"` o `"sombrero"`;
    - `cual` es el ánimo o la clave del sombrero, y `None` en el cuerpo.
  - `lugares()` añade al final las 5 030, en este orden: por especie (orden de `especies.ESPECIES`), por etapa (orden de `especies.ETAPAS`), el cuerpo (`se`, `so`, `no`, `ne`), las caras (por ánimo `feliz`, `normal`, `mal`; `se`, `so`) y los sombreros (orden de `cosmeticos.SOMBREROS`; 4 orientaciones); después las 30 de la especie y, al final de todas, las 30 comunes. Todas de 1024 × 1024, familia `criaturas`, `reduccion=4`, `en_el_juego=False` y su `criatura`.
  - `@dataclass(frozen=True) class Grupo` gana `casillas: tuple[tuple[str, ...], ...]` (lo que cuenta el avance, cada casilla con sus rutas candidatas en orden) y `con_tarjeta: bool = True`:
    - fuera de las criaturas, cada ruta es su propia casilla;
    - en `criaturas/<especie>`, sus 200 rutas y 170 casillas: el cuerpo con su ruta de forma, y cada cara o sombrero de forma con `(forma, especie, común)`;
    - `criaturas/comun`, con `con_tarjeta=False` y sus 30 rutas como casillas.
  - Nombres: el de la especie (`especies.ESPECIES[k].nombre`) y «Capas comunes a todas las especies».
  - `retrato.capa_de_frente(especie: str | None, etapa: str | None, capa: str, cual: str | None) -> bytes`: el PNG de 256 × 256 de la capa de frente de hoy, con `functools.lru_cache(maxsize=RECORDADOS)`.
    - El cuerpo sale de `_ruta_del_cuerpo` si la especie está en `CON_ETAPAS_COMPLETAS`; si no, de `relleno(especie, etapa, esp.NORMAL)`.
    - La cara y el sombrero salen de `_ruta_de_capa` (forma, especie y común); sin etapa, de la especie o la común; sin especie, la común.
    - `olvidar()` la vacía también.
  - `/provisional` de una capa: `capa_de_frente` ampliada ×4 con `NEAREST` (1024 × 1024); con `&miniatura=1`, la de 256.
  - La vista de una capa gana `"criatura": {"nivel", "etapa", "capa", "cual", "nombre_del_sombrero", "orientacion"}`.

- [ ] **Step 1: Las pruebas que fallan:**
  - `test_las_criaturas_tienen_5030_lugares` (4 250, 750 y 30).
  - `test_las_rutas_de_una_capa` (las tres formas, con la clave `dragoncito`).
  - `test_de_espaldas_no_hay_cara`.
  - `test_el_cuerpo_no_se_comparte` (no hay cuerpo de especie ni común).
  - `test_una_especie_tiene_200_lugares_y_170_casillas`.
  - `test_las_comunes_no_llevan_tarjeta`.
  - `test_una_capa_se_sube_a_1024_y_se_guarda_con_su_version_de_256`.
  - `test_el_provisional_de_un_cuerpo_dibujado_es_su_capa_de_frente_por_cuatro`.
  - `test_una_especie_sin_dibujos_usa_el_relleno_de_retrato`.
  - `test_el_provisional_de_una_cara_sigue_la_busqueda_forma_especie_comun`.
  - `test_las_capas_no_entran_al_juego_ni_a_la_portada`.
  - `test_las_rutas_de_las_capas_pasan_el_filtro_del_cliente_y_de_la_tabla`.
  - `test_buscar_un_lugar_entre_miles_no_recorre_la_lista` (`lugar_de` usa el índice: no llama a `lugares()` más de una vez en cien búsquedas).
- [ ] **Step 2:** Correrlas y ver que fallan.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** La suite entera pasa y `git diff --check` sale limpio.
- [ ] **Step 5:** Commit: `feat: las capas de las criaturas en cuatro orientaciones, para subir`.

### Task 8: El avance y la api por grupos

**Files:**
- Modify: `web/dibujante.py`
- Test: `tests/test_web_dibujante.py`

**Interfaces:**
- Consumes: `Grupo.casillas`, `Grupo.con_tarjeta`, `Capa` (Task 7); `_al_dia` (Task 2).
- Produces:
  - `total = len(grupo.casillas)`; `hechas` = casillas con alguna ruta candidata al día.
  - `GET …/api/avance`: `{"grupos": [{"clave", "nombre", "familia", "total", "hechas"}]}`, sólo los grupos `con_tarjeta` (84). Su forma no cambia.
  - `GET …/api/piezas`: `{"grupos": [{"clave", "nombre", "familia", "total", "hechas", "piezas"?}]}`. Los de familia `criaturas` llegan **sin** `piezas`.
  - `GET …/api/piezas?grupo=<clave>`: `{"grupos": [<ese grupo con "piezas">]}`; una clave que no existe da el 404 de siempre.
  - Una cara o un sombrero de forma sin capa propia al día, pero cubierto, lleva `"cubierta": {"por": "especie" | "comun", "direccion": <la chica de la que la cubre>}`; si no, `null`.
  - `GET …/api/copia.zip` y `GET …/api/provisionales.zip`, sin `grupo`, traen todos los grupos menos los de familia `criaturas`. Con `?grupo=<clave>`, sólo ese, en `copia-<clave con «/» → «-»>.zip` y `provisionales-<…>.zip`.

- [ ] **Step 1: Las pruebas que fallan:**
  - `test_el_avance_trae_84_grupos_y_no_el_de_las_comunes`.
  - `test_el_avance_sigue_siendo_el_contrato_del_diseno_campo_por_campo` (la prueba de hoy, con los grupos nuevos).
  - `test_una_capa_comun_hace_avanzar_a_todas_las_especies_que_cubre`.
  - `test_volver_una_capa_de_la_especie_al_provisional_descubre_sus_casillas`.
  - `test_hechas_nunca_pasa_de_total`.
  - `test_la_lista_general_no_trae_las_capas_de_las_criaturas` (y pesa menos de 200 KB).
  - `test_un_grupo_se_pide_entero`.
  - `test_un_grupo_que_no_existe_es_404`.
  - `test_una_casilla_cubierta_dice_por_quien`.
  - `test_los_zips_de_arriba_no_traen_criaturas`.
  - `test_cada_especie_tiene_sus_dos_zips`.
  - `test_el_avance_no_abre_ninguna_imagen` (la de hoy, con las criaturas dentro).
- [ ] **Step 2:** Correrlas y ver que fallan.
- [ ] **Step 3:** Implementar. El avance y la lista leen la tabla una sola vez por petición (`arte_puesto_entero`).
- [ ] **Step 4:** La suite entera pasa y `git diff --check` sale limpio.
- [ ] **Step 5:** Commit: `feat: el avance cuenta las casillas y la api del dibujante va por grupos`.

### Task 9: La página del dibujante

**Files:**
- Modify: `web/static/js/dibujante.js`, `web/static/dibujante.css`
- Test: `tests/js/dibujante.test.mjs`

**Interfaces:**
- Consumes: la forma de `/piezas`, `/piezas?grupo=`, la vista (con `objeto`, `estado`, `criatura`, `cubierta`, `miniatura`), `/provisional?…&miniatura=1` y los zips con `?grupo=` (Tasks 4 a 8).
- Produces:
  - Arriba, los grupos que no son criaturas, como hoy, cada `summary` con «{nombre} · {hechas} de {total}».
  - Debajo, «Criaturas»: un `details` por especie y otro para las comunes, sin tarjetas.
  - Al abrir uno por primera vez: «Cargando las capas…», `GET piezas?grupo=…` y sus secciones como `details` cerrados. Hay una por etapa, con «Cuerpo», «Caras» y «Sombreros» (éstos plegados), y «Para todas las etapas de {especie}». Las tarjetas de una sección se arman al abrirla.
  - La miniatura es `subida.direccion`; si no hay, `cubierta.direccion`; si no, `miniatura`; y si viene `null`, `urlDeArte(ruta)`.
  - `dib-cuadros` sólo fuera de `pieza` y `criaturas`.
  - Las notas, según `estado`, `objeto` (`mayordomo`, `balcon`) y la familia `criaturas`.
  - «Volver a la anterior» y «Volver al provisional» en una capa de nivel `especie` o `comun` piden `confirm(...)` con su frase, y si se cancela no mandan nada.
  - «Sólo lo que falta»: esconde lo cubierto y los lugares de nivel `especie` o `comun`, y esconde la especie sin abrir si `hechas === total`.
  - Cada especie tiene sus dos enlaces de descarga.
  - Todas las frases, tal cual, de la tabla «Frases».

- [ ] **Step 1: Las pruebas que fallan** en `tests/js/dibujante.test.mjs`:
  - `una especie no se pide ni se arma hasta abrirla` (ninguna petición `grupo=` ni ninguna `img` de criatura antes de abrir).
  - `al abrir una especie se pide una sola vez`.
  - `las secciones de una etapa se arman al abrirlas`.
  - `cada grupo dice cuántas tiene hechas`.
  - `una capa de espaldas no ofrece cara` (no hay tarjeta de cara `no`/`ne`).
  - `una casilla cubierta lo dice y enseña la que la cubre`.
  - `volver atrás una capa compartida pide confirmación y, si se cancela, no manda nada`.
  - `el encendido, el mayordomo y el balcón llevan su nota`.
  - `las capas no se pintan como cuadros`.
  - `sólo lo que falta esconde lo cubierto y lo compartido`.
  - `cada especie ofrece sus dos descargas`.
  - `si una especie no carga, lo dice en su sitio`.
  - `las frases son las aprobadas`.
- [ ] **Step 2:** Correrlas y ver que fallan.
- [ ] **Step 3:** Implementar. `confirm` se toma de `globalThis` para que la prueba lo cambie.
- [ ] **Step 4:** La suite entera pasa y `git diff --check` sale limpio.
- [ ] **Step 5:** Commit: `feat: la página del dibujante pliega las criaturas y las pide al abrirlas`.

### Task 10: La copia de lo subido al desplegar lleva sólo lo nuevo

Lo agrega el plan, no estaba en el diseño. `actualizar-pi.sh` comprime hoy la carpeta de lo subido entera en cada despliegue y guarda las cinco últimas. Con originales de varios cientos de MB, eso llena la tarjeta.

**Files:**
- Modify: `actualizar-pi.sh`, `deploy.sh`, `.gitignore`
- Test: `tests/test_despliegue.py`

**Interfaces:**
- Produces:
  - En `actualizar-pi.sh`, en lugar del `tar` y su rotación: `if [ -d arte_subido ]; then rsync -a --ignore-existing --exclude '.subiendo-*' arte_subido/ arte_subido.copia/; fi`. Un archivo subido nunca cambia, así que la copia gana sólo lo nuevo y nunca pisa nada. Las copias `arte_subido.*.tar.gz` que ya haya no se borran.
  - `deploy.sh` excluye también `arte_subido.copia` en su `rsync --delete`.
  - `.gitignore` gana `/arte_subido.copia/`.

- [ ] **Step 1: Las pruebas que fallan:**
  - `test_la_copia_de_lo_subido_lleva_solo_lo_nuevo` (reemplaza `test_la_copia_de_seguridad_incluye_lo_subido_y_conserva_las_cinco_ultimas`): está el `rsync -a --ignore-existing`, ya no hay `tar` de la carpeta y ningún `$` de la Pi queda sin escapar en el heredoc.
  - `test_rsync_no_borra_lo_subido_por_el_dibujante`: las exclusiones son exactamente `arte_subido`, `arte_subido.*.tar.gz` y `arte_subido.copia`.
  - `test_las_copias_de_lo_subido_no_entran_en_git` (las dos líneas).
  - `test_los_guiones_son_bash_valido` sigue pasando.
- [ ] **Step 2:** Correrlas y ver que fallan.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** La suite entera pasa y `git diff --check` sale limpio.
- [ ] **Step 5:** Commit: `fix: la copia de lo subido al desplegar lleva sólo lo nuevo`.

### Task 11: Los documentos

**Files:**
- Modify: `AGENTS.md`, `docs/arte/contrato.md`, `fuentes/pieza/LEEME.md`, `README.md`, `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces:
  - **`AGENTS.md`**, sección «La web», en tres renglones:
    - la invariante de la familia `pieza` dice que lo que sube el dibujante sólo vale al doble (1024 × 512 por casilla), que se guarda el original y que lo servido se deriva;
    - los lugares de subida (`arte.lugares()`) son más que el contrato del juego (`arte.piezas()`), y lo que el juego no pinta nunca entra en el bloque de la portada;
    - `archivo, ancho, alto` de `arte_subido` son lo servido y el original va aparte, y la poda conserva los dos.
  - **`docs/arte/contrato.md`**, para el dibujante:
    - la pieza se sube a la medida de original;
    - una sección por cada cosa nueva: los encendidos, los 24 objetos con su tabla, sus medidas y sus íconos, y las criaturas, con sus rutas, 1024 × 1024, los niveles y que de espaldas no hay cara;
    - la sección «Los gachamones no están en este contrato» se reemplaza.
  - **`README.md`**: la página del dibujante y la copia al desplegar (la línea que dice «guarda las 5 últimas de cada una»).
  - **Pendientes**, un apartado «Salió al planificar el arte que falta», con:
    - «Para publicar», con los pasos del diseño: el sitio primero; confirmar los colores con un archivo real del dibujante; la página de prueba; el juego, con lo que se comprueba desde fuera; avisarle al dueño que, mientras el juego siga en la Raspberry, el dibujante no suba criaturas en masa hasta la mudanza; y, al juntar con la rama del ejecutable, los conflictos en `arte_subido.py` y `web/dibujante.py` y su armado copiando sólo lo de su contrato;
    - «Lo que le toca al sitio»: la categoría «Criaturas» y, como requisito, reabrir una tarjeta hecha cuyo grupo crezca.
- [ ] **Step 1:** Escribir los cambios.
- [ ] **Step 2:** La suite entera pasa (hay pruebas que leen `AGENTS.md` y `README.md`) y `git diff --check` sale limpio.
- [ ] **Step 3:** Commit: `docs: el arte que falta en AGENTS, el contrato, el README y los pendientes`.

---

## Repaso

- **Cobertura del diseño:**
  - la medida nueva, la tabla y el original → Tasks 1 y 2; el tope → Task 2; el color → Task 3;
  - historial, descargas, provisional ×2 y copia → Task 4;
  - encendidos → Task 5; objetos e íconos → Task 6; criaturas, búsqueda, provisionales y versión de 256 → Task 7;
  - avance, casillas, comunes sin tarjeta, carga por grupo y zips por especie → Task 8;
  - página, notas, confirmaciones, filtro y frases → Task 9;
  - la copia al desplegar → Task 10 (lo añade el plan); documentos, «Para publicar» y «Lo que le toca al sitio» → Task 11;
  - el rendimiento con miles de filas → Task 1, Step 4; la conversión de color confirmada con un archivo real → pendientes, en la Task 11;
  - la copia de cada noche → fuera de este plan (es de la mudanza).
- **Nombres que cruzan tareas:**
  - `Lugar`, `lugares()`, `lugar_de()` y `olvidar()` nacen en la Task 2; `objeto` y `estado` se llenan en las 5 y 6, y `criatura` en la 7;
  - `ArtePuesto` y `arte_puesto_entero()` nacen en la Task 1 y los usan las 2, 4 y 8;
  - `Imagen` y `preparar() -> tuple[Imagen, Imagen]`, en la Task 2;
  - `RAIZ_POR_VENIR`, en la Task 5; `Objeto`, `POR_VENIR` y `FUERA`, en la 6; `Capa`, `Grupo.casillas`, `Grupo.con_tarjeta` y `retrato.capa_de_frente`, en la 7;
  - `_al_dia`, en la Task 2, y lo usa la 8;
  - la vista: `subida.original` (2), `objeto` y `estado` (5), `criatura` (7), `cubierta` y `total`/`hechas` (8).
- **Review Focus:** cada línea tiene su prueba nombrada en su tarea dueña (Tasks 2, 3, 4, 8 y 9).
