# El arte que falta · Lo que el dibujante adelanta para el ejecutable — diseño

Continúa el proyecto A (`2026-11-19-monsteropolis-a-herramientas-del-dibujante-design.md`)
y sus descargas (`2026-11-21-descargar-provisionales-design.md`), y retoma el
diseño A2 de las criaturas en cuatro orientaciones, aprobado el 2026-11-20 y
nunca construido. Sólo toca la página del dibujante y lo que hay detrás (el
contrato del arte, la subida y su tabla). La página del juego sigue congelada.

## Para qué

El juego se está convirtiendo en un ejecutable, en otra rama. Ese ejecutable va
a necesitar dibujos que la página de hoy no tiene: los objetos del documento de
diseño del dueño que el juego aún no trae, con sus íconos de tienda, el segundo
dibujo de los muebles que se encienden, las criaturas en cuatro orientaciones y
los muebles a más resolución. El dueño quiere que el dibujante pueda ir
adelantando todo eso desde su página, aunque todavía nadie lo pinte.

Aquí sólo se abren **los lugares de subida, sus descargas y su avance**. La
página congelada no pinta nada nuevo. Cada dibujo lo usará el ejecutable cuando
se construya su parte.

El diseño A2 sigue valiendo en lo que este diseño no cambia: la familia
`criaturas` con sus rutas propias, la búsqueda de caras y sombreros por forma,
luego por especie y luego la común, que de espaldas no hay cara, el avance por
casillas cubiertas y la categoría «Criaturas» del tablero.

## Lo que decidió el dueño (2026-11-21)

1. Abrir lugares de subida para **todos los objetos del documento de diseño que
   el juego todavía no tiene**: Consola Flappy, Consola Pong (hoy hay una sola
   «Consola», que se queda), Mesa de gato, Atril, Tocadiscos, Mayordomo robot
   (1 casilla, «altura de un jugador»), Puerta de cristal, bloque de cableados,
   Súper Dado, Mega TV (2 × 1 casillas), Lámpara Dragón, Silla y Mesa (1 casilla
   cada una, en seis colores: azul, roja, verde, amarilla, negra y blanca; cada
   color es un objeto distinto) y el **Balcón: una tira de 4 × 1 casillas por
   fuera de la pared**. Salvo lo dicho, todos son de 1 casilla y van en el suelo.
2. Los muebles que se encienden y se apagan llevan **dos dibujos, apagado y
   encendido**: Lámpara, Calefactor, Chimenea y Fuente (que ya están en el juego)
   y Tocadiscos, Puerta de cristal (sólida o atravesable), Mega TV y Lámpara
   Dragón. El dibujo de hoy pasa a ser el «apagado».
3. **Criaturas**: capas de **1024 × 1024** («para que no se vea pixelado»), por
   especie y etapa: el cuerpo en las cuatro orientaciones, las caras de los tres
   ánimos en las dos orientaciones de frente y los sombreros en las cuatro.
4. **Los muebles suben de medida: 1024 × 512 por casilla**, como única medida de
   subida (hoy el contrato pide 512 × 256 por casilla).
5. En el tablero, las criaturas van en una categoría nueva, «Criaturas», con
   una tarjeta por especie. Eso lo hace el sitio leyendo el avance. Aquí sólo
   importa que el avance traiga esos grupos con una `familia` que lo permita.

**Sus respuestas al borrador de este diseño (2026-11-21):**

6. El dibujante **no ha subido nada todavía** (el bloque `arte-subido` de la
   portada pública está vacío): no hay arte viejo que proteger.
7. **Cada objeto nuevo lleva también su ícono de tienda**, uno por objeto, con la
   medida de los íconos de hoy.
8. **El dibujo encendido va en la misma tarjeta del mueble**: su grupo cuenta los
   dos estados y está hecho cuando están todos. No hay grupos aparte para el
   encendido.
9. Acepta tres propuestas técnicas del borrador: **el suelo y las paredes también
   suben de medida**, **la ruta de las criaturas usa la clave de la especie**, y
   **los zips de arriba no traen las criaturas**, porque cada especie tiene los
   suyos. Acepta también **el tope de 24 MB**.

## Metas

1. El dibujante puede subir, a la medida que usará el ejecutable, todo lo que
   pidió el dueño: los objetos nuevos con sus íconos, los dibujos encendidos y
   las capas de las criaturas.
2. Lo que sube se guarda **entero, a la medida en que lo subió**, con el mismo
   historial, «Volver a la anterior», «Volver al provisional» y la misma poda que
   hoy, y se puede descargar.
3. Quien juega no nota nada: ni lo que ve, ni el peso o la velocidad de la
   portada.
4. El tablero lleva la cuenta de todo lo nuevo y no esconde trabajo pendiente.
5. La página del dibujante sigue siendo cómoda, también en el teléfono, con unos
   5 000 lugares más.

## Lo que no entra

- Que la página congelada pinte algo nuevo: ni criaturas orientadas, ni muebles
  encendidos, ni objetos nuevos, ni el balcón. Lo de A2 que es del juego (hacia
  dónde mira una criatura, el encuadre común al girar, la dirección del retrato
  con la orientación y el estado del juego con las orientaciones completas) queda
  para el ejecutable.
- Vender, poner, encender o apagar los objetos nuevos, o meterlos en el catálogo
  del juego (`departamento.MUEBLES`) o en la tienda. Sus íconos se suben, pero
  ninguna pantalla los enseña.
- Cambiar la medida de las familias de pixel art: pueblo, lugares, escenas,
  avatar, efectos e íconos siguen como están.
- Ver en la página del dibujante cómo quedan apiladas las capas de una criatura,
  que A2 proponía. El dibujante lo ve en su propio programa y el ejecutable lo
  pintará **[llamada mía]**.
- Pasar lo subido al repo (`fuentes/`) o meterlo en el ejecutable. El ejecutable
  lo leerá de la tabla.
- Animaciones y tintes.
- Tocar el tablero del sitio más allá de lo que dice «Lo que le toca al sitio».

## Lo que lo haría un fracaso aunque funcione

- Que quien juega note algo: otra imagen, otra medida, o una portada más pesada o
  más lenta.
- Que el ejecutable reciba la versión reducida de algo que el dibujante subió
  grande, porque se perdió el original, o que lo reciba con otros colores.
- Que el dibujante suba cientos de capas a rutas, claves o medidas que el
  ejecutable después no use.
- Que la página del dibujante se vuelva lenta, o que abrirla en el teléfono baje
  cientos de megas.
- Que el tablero esconda trabajo nuevo, por ejemplo con una tarjeta ya «hecha»
  que no se reabre aunque su grupo tenga dibujos pendientes.
- Que el disco o las copias se llenen sin aviso.
- Que el mundo en línea del ejecutable, que ya lee esta tabla, deje de leerla
  bien.

## Cómo es hoy

- **El contrato del juego** (`arte.piezas()`, en `web/arte.py`) tiene 270
  piezas en 35 grupos. La familia `pieza` (el suelo, las dos paredes y 72
  dibujos de 20 muebles) se sirve a la mitad de su original. El contrato las mide
  servidas (la casilla, 512 × 256), pero el documento del dibujante
  (`docs/arte/contrato.md`), `fuentes/pieza/` (sin originales todavía, sólo su
  `LEEME.md`) y `herramientas/pieza.py` ya hablan del original, de 1024 × 512
  por casilla. **La medida que pide el dueño es esa: el original de siempre.**
- **La subida** aceptó el original de la familia `pieza` y lo redujo, tirando el
  original, hasta hace unas horas. Desde entonces sólo acepta la medida servida,
  y el doble se rechaza.
- **La tabla `arte_subido`** guarda, por cada subida o vuelta atrás, la ruta, el
  archivo y su ancho y alto, que son los de lo servido. La portada lleva en un
  bloque `arte-subido` lo vigente de cada pieza del contrato cuya medida coincide
  (`db.arte_vigente(arte_subido.medidas())`). Se conservan las cinco últimas
  imágenes distintas de cada pieza.
- **Todavía no hay nada subido**: el bloque de la portada está vacío.
- **El mundo en línea del ejecutable** (otra rama) ya lee esta tabla y esta
  carpeta, en sólo lectura y con su propio código: pide `ruta, archivo, ancho,
  alto` y sirve lo que la tabla conserva.
- **La página del dibujante** arma de una vez las 270 tarjetas, plegadas por
  grupo. El avance sale de `arte.grupos()`.

## Enfoques considerados

Lo elegido en esta sección es **[llamada mía]**: son decisiones técnicas, no del
dueño. Las que él ya aceptó lo dicen.

### La medida nueva de los muebles, sin tocar lo que ve quien juega

- **Subir el original, guardarlo y derivar lo servido (elegido).** El dibujante
  sube a 1024 × 512 por casilla. El servidor guarda ese original y, con la misma
  reducción de siempre (`arte_subido.a_lo_servido`, a la mitad con `LANCZOS`, que
  es la de `herramientas/pieza.py`), saca la versión que sirve la página. La fila
  sigue diciendo qué se sirve (`archivo`, `ancho` y `alto`, como hoy) y gana el
  original al lado. `arte_vigente`, el bloque de la portada y lo que lee el
  ejecutable no cambian. Es la propuesta que traía el pedido, validada contra el
  código, con dos correcciones: la versión derivada no es sólo para la página,
  porque también sirve de miniatura (ver «La medida de subida y lo que se
  guarda»), y «tal cual» quiere decir los mismos píxeles, limpios, no los mismos
  bytes (ver «Riesgos»).
- **Guardar sólo el original y reducirlo al servirlo.** Rompe que el nombre de lo
  servido sea su contenido, gasta CPU en cada petición de quien juega y toca el
  camino de la página congelada. Descartado.
- **Que `archivo` pase a ser el original y añadir una columna para lo servido.**
  Cambia a cada lector de la tabla, también al mundo en línea del ejecutable, que
  dejaría de ver lo subido porque su contrato pide la medida servida. Descartado.
- **Cambiar el contrato del juego a la medida grande.** Quien juega bajaría
  cuatro veces más píxeles. Descartado.

### Los objetos que el juego no tiene

- **Una lista propia en el contrato del arte (elegido).** `web/arte.py` describe
  los objetos por venir (clave, nombre, forma, si van en el suelo o pegados a una
  pared y su segundo estado) sin pasar por `departamento.py`. Entran en los
  lugares de subida y no en `arte.piezas()`, así que no cambian ni el `arte.json`
  de la página, ni el bloque de la portada, ni ninguna regla del juego.
- **Meterlos en `departamento.MUEBLES` marcados «no a la venta».** Toda regla que
  recorre el catálogo (la comodidad, la tienda, los íconos, el ritmo) tendría que
  saltárselos, y choca con la rama del ejecutable, que los meterá ahí de verdad.
  Descartado.
- **Meterlos en `arte.piezas()` con sus provisionales en `web/static/arte/`.**
  Cambia el contrato y los estáticos de la página congelada. Descartado.

### El segundo estado

- **La ruta de hoy es la apagada y la encendida es otra ruta, con el estado antes
  de la orientación (elegido):** `pieza/muebles/lampara-encendido-se.png`. Lo que
  pide el juego no cambia.
- **Renombrar las dos (`-apagado-` y `-encendido-`).** Cambia la ruta que pide la
  página congelada. Descartado.
- **Una subcarpeta (`pieza/muebles/encendido/lampara-se.png`).** También sirve,
  pero aleja el estado del nombre del mueble y reparte en dos carpetas los
  dibujos de un mismo mueble. Descartado.

### Cómo cargan las criaturas en la página

- **Especies plegadas que se piden al abrirlas (elegido).** La lista general
  trae cada especie sin sus capas, con su cuenta. Al abrir una especie se pide
  esa especie sola, y cada sección se arma al abrirla.
- **Una lista paginada de todos los lugares.** No calza con la manera de
  trabajar por grupos de hoy. Descartado.
- **Todo de una vez, como hoy.** Son unas 5 000 tarjetas más. Descartado.

### El provisional de una capa de criatura

- **La capa de frente de hoy, ampliada ×4 sin suavizar (elegido).** Sale de
  `fuentes/`, con la misma búsqueda que usa `retrato.py`: el cuerpo de esa forma
  (o el dibujo provisional de `retrato.relleno` si la especie no tiene cuerpos) y
  la cara o el sombrero más concretos que haya. Le enseña al dibujante dónde va
  la criatura y de qué tamaño es en el lienzo, que es lo que hace falta para que
  las capas calcen y la criatura no salte al girar.
- **Un recuadro genérico rotulado, como el de los muebles.** No da posición ni
  escala. Descartado.
- **Nada (un lugar vacío).** Descartado por lo mismo.

### El tope de peso (aceptado por el dueño)

- **Un solo tope de 24 MB (elegido).** Es lo que pesa sin comprimir, a 8 bits,
  el lugar más grande: el balcón, de 2560 × 2304 (23,6 MB). Ningún PNG de una
  medida aceptada necesita más. Lo que se guarda lo limita la limpieza, que
  vuelve a escribir la imagen a 8 bits, y no el tope. Una capa de criatura de
  1024 × 1024 no puede guardar más de unos 4 MB, pase lo que pase.
- **Un tope por lugar, proporcional a su medida.** Protege poco más y añade
  código y una frase por lugar. Descartado.
- **Dejar 4 MB.** Alcanza para las criaturas (una capa pintada de cuerpo, medida
  con una aproximación, pesa algo más de 1 MB), pero no para los muebles grandes
  al doble. Descartado.

## Cómo es

### Dos listas: lo que pinta el juego y dónde se puede subir

- `arte.piezas()` **no cambia**: siguen las 270 piezas del juego, con su medida
  servida. De ella salen `arte.json`, el bloque de la portada y lo que lee el
  ejecutable.
- Aparece una segunda lista, **los lugares de subida**: las 270 de siempre, los
  dibujos encendidos, los objetos por venir con sus íconos y las capas de las
  criaturas. Cada lugar tiene su ruta, su familia, **la medida en que se sube**,
  su reducción y si lo pinta el juego. La página del dibujante, el avance y las
  descargas trabajan con esta lista. Como es fija mientras dura el proceso, se
  calcula una sola vez, y buscar un lugar por su ruta no recorre 5 000 cada vez
  **[llamada mía]**.

### La medida de subida y lo que se guarda

Cada subida guarda **dos archivos**, los dos con el nombre de su contenido: el
**original**, a la medida de subida, y la **versión chica**, reducida con
`LANCZOS`. Cuando no hay nada que reducir, los dos son el mismo archivo.

| Familia | Se sube a | Versión chica | Quién usa la chica |
|---|---|---|---|
| `pieza` (el suelo, las paredes, los muebles, los objetos por venir y los dibujos encendidos) | el doble de lo servido: **1024 × 512 por casilla** | la mitad: la medida de hoy | quien juega, si el juego la pinta; si no, sólo la miniatura de la página del dibujante |
| `criaturas` | **1024 × 1024** | 256 × 256 | sólo la miniatura de la página del dibujante |
| las demás (pixel art, también los íconos nuevos) | su medida de hoy | ninguna: es el mismo archivo | quien juega, como hoy (los íconos nuevos no los ve nadie) |

La familia `pieza` entera sube de medida, **también el suelo y las paredes**, y
no sólo los muebles (aceptado por el dueño): comparten la misma cuadrícula, y el
ejecutable no puede pintar un suelo a una escala y los muebles a otra. Es además
la medida de original que ya dice `docs/arte/contrato.md`.

Medidas de subida de la familia `pieza` (el doble de las de hoy, también lo que
sobresale):

| Forma | Medida de subida |
|---|---|
| El suelo, o un mueble plano de 1 × 1 | 1024 × 512 |
| Un tramo de pared, o lo de pared de 1 tramo (la puerta, el cuadro) | 512 × 1280 |
| Lo de pared de 2 tramos | 1024 × 1536 |
| Un mueble de bulto de 1 × 1 | 1024 × 1536 |
| Un mueble de bulto de 2 × 1 | 1536 × 1792 |
| Un mueble plano de 2 × 2 | 2048 × 1024 |
| Un mueble de bulto de 2 × 2 | 2048 × 2048 |
| El balcón | 2560 × 2304 |

La versión chica de una pieza que el juego pinta es exactamente lo que se le
sirve hoy, con la medida servida del contrato: la página congelada la recibe
igual que si se hubiera subido a esa medida, y **se ve al momento**, como desde
el proyecto A.

### La tabla

`arte_subido` gana tres columnas que pueden ir vacías: `original`,
`ancho_original` y `alto_original`. Entran por `MIGRACIONES_DE_TABLAS`, como las
columnas que se añadieron antes a otras tablas.

- `archivo`, `ancho` y `alto` **siguen siendo lo que se sirve** (la versión
  chica). Así `arte_vigente`, el bloque de la portada y el mundo en línea del
  ejecutable, que pide esas cuatro columnas por su nombre, no cambian.
- Cada fila nueva llena las tres columnas nuevas. Si no hubo nada que reducir,
  `original` es el mismo nombre que `archivo`.
- Las medidas del original se guardan y no se deducen de la reducción
  **[llamada mía]**. Es la regla del proyecto A («la tabla guarda la medida de lo
  subido»).
- **Una sola regla por si llegara una fila sin original** (una subida a la medida
  chica antes de publicar esto; hoy no hay ninguna): su archivo hace de
  original. Si mide lo que sirve el juego, se sigue viendo, como cualquier
  subida de hoy. Como no mide lo que pide subir, cuenta como pendiente. No hay
  nada más para ese caso.

### Subir, volver, podar y servir

- **Subir** sigue el orden de hoy, con los dos archivos: comprobar la cabecera a
  la medida de subida (antes de abrir nada, para que no entre una bomba de
  descompresión), limpiar, reducir, escribir los dos, anotar la fila, volver a
  escribir los dos (por si una poda que se cruzó se llevó alguno) y podar.
- **Limpiar convierte el color**: todo PNG que traiga un perfil de color se pasa
  a sRGB y se guarda sin perfil; el que no trae perfil se deja como está
  **[llamada mía]**. Hoy el perfil se descarta sin convertir, y un dibujo hecho
  en Display P3 (el de muchas tabletas) cambiaría de color. Se construye ya, sin
  esperar un archivo del dibujante.
- **La identidad de una imagen pasa a ser su original.** «Volver a la anterior»
  salta las subidas de la misma imagen que la puesta y las que no se conservan o
  no están enteras en disco: tienen que estar los dos archivos. La fila de la
  vuelta copia el original y sus medidas de la subida a la que vuelve.
- **«Volver al provisional»** no cambia.
- **La poda** conserva, de cada lugar, las cinco últimas imágenes distintas
  contadas por su original y, de cada una, **los dos archivos**. Los conocidos
  incluyen los originales. Corre igual que hoy, con la base tomada para escribir.
- **Servir:** la dirección de lo subido (`/monsteropolis/arte-subido/<nombre>`)
  sirve todo lo que la tabla conserva, así que sirve también los originales y
  las capas de las criaturas. De ahí salen «Descargar la imagen subida» y las
  miniaturas. El nombre es el hash del contenido, así que nadie lo adivina; lo
  que no tiene permiso es subir **[llamada mía]**.

### Lo que se dice de una imagen con otra medida

Un lugar está **provisional** (no hay nada subido), **al día** (el original mide
lo que hoy pide subir) o **con otra medida**. En ese último caso `medida_cambiada`
lleva `{ancho, alto}` del original, como hoy, y la tarjeta enseña el provisional
y un aviso que pide volver a subirlo. Pasa si el contrato le cambia la forma a
un lugar o con la fila sin original de arriba. Con estos estados se arman la
tarjeta, «Sólo lo que falta» y el avance. El historial enseña en cada fila la
medida del original.

### Los objetos que el juego no tiene

Van con la ruta que tendrán cuando entren al juego. **Este documento fija sus
claves, sus rutas y sus formas** **[llamada mía]**. La rama del ejecutable
todavía no las tiene y las adoptará tal cual al construir cada objeto: ése es el
contrato, y así lo subido ya estará en su sitio. La lista y las casillas son las
que decidió el dueño: el balcón, 4 × 1 por fuera de la pared; la Mega TV, 2 × 1;
y lo demás, 1 casilla.

- **Los dibujos de la pieza** (familia `pieza`):
  `pieza/muebles/<clave>-<orientación>.png`, y el encendido,
  `pieza/muebles/<clave>-<estado>-<orientación>.png`.
- **El ícono de tienda** (familia `iconos`): `iconos/muebles/<clave>.png`, de
  48 × 48 como los de hoy, uno por objeto, también el balcón.

| Clave | Nombre | Forma | Dibujos de la pieza | Segundo estado |
|---|---|---|---|---|
| `consola_flappy` | Consola Flappy | 1 × 1, de bulto | 4 | — |
| `consola_pong` | Consola Pong | 1 × 1, de bulto | 4 | — |
| `mesa_gato` | Mesa de gato | 1 × 1, de bulto | 4 | — |
| `atril` | Atril | 1 × 1, de bulto | 4 | — |
| `tocadiscos` | Tocadiscos | 1 × 1, de bulto | 4 + 4 | `encendido` |
| `mayordomo` | Mayordomo robot | 1 × 1, de bulto | 4 | — |
| `puerta_cristal` | Puerta de cristal | 1 × 1, de bulto | 4 + 4 | `atravesable` |
| `cableados` | Bloque de cableados | 1 × 1, de bulto | 4 | — |
| `super_dado` | Súper Dado | 1 × 1, de bulto | 4 | — |
| `mega_tv` | Mega TV | 2 × 1, de bulto | 4 + 4 | `encendido` |
| `lampara_dragon` | Lámpara Dragón | 1 × 1, de bulto | 4 + 4 | `encendido` |
| `silla_<color>` | Silla azul, roja, verde, amarilla, negra y blanca | 1 × 1, de bulto | 4 cada una | — |
| `mesa_<color>` | Mesa azul, roja, verde, amarilla, negra y blanca | 1 × 1, de bulto | 4 cada una | — |
| `balcon` | Balcón | 4 × 1, por fuera de la pared | 2 (`se`, `so`) | — |

`<color>` es `azul`, `roja`, `verde`, `amarilla`, `negra` o `blanca`.

- **«De suelo», en las palabras del dueño, es «de bulto» en el código**: ocupa su
  casilla y sobresale. Un lienzo de bulto contiene el de un mueble plano, así que
  el dibujante puede dibujar algo bajo (el bloque de cableados, si resulta plano)
  sin perder nada **[llamada mía]**.
- **El mayordomo** usa el lienzo de cualquier mueble de bulto de 1 × 1. La
  «altura de un jugador» es una guía para dibujar: en la pieza, tu avatar mide
  0,7 anchos de casilla (`ALTO_DEL_AVATAR` en `web/static/js/pieza.js`), unos
  717 px del original, de pie en el centro de la casilla. Cabe de sobra en el
  lienzo **[llamada mía]**.
- **El balcón** se pone como lo de pared, en una de las dos paredes: `se` va en la
  izquierda y `so` en la derecha, como dice el contrato para lo que cuelga. Su
  lienzo es el de una huella de 4 × 1 más el alto de la pared:
  (4 + 1) × 512 = 2560 de ancho y (4 + 1) × 256 + 1024 = 2304 de alto. Cubre la
  tira con su baranda y lo que se ponga encima **[llamada mía]**.
- La Puerta de cristal es de bulto, de 1 × 1, como dice la tabla. La sólida es
  el dibujo de siempre, y la atravesable, su segundo estado **[llamada mía]**.
- **Los íconos nuevos van en el grupo de hoy, «Iconos de los muebles»**, como los
  de los muebles que ya existen **[llamada mía]**.

Son **24 objetos, con 110 dibujos de la pieza** (23 de suelo × 4, más 4
encendidos × 4, más los 2 del balcón) **y 24 íconos**.

### El encendido de los cuatro que ya existen

La Lámpara, el Calefactor, la Chimenea y la Fuente ganan
`pieza/muebles/<clave>-encendido-<orientación>.png`, con las cuatro
orientaciones, a la misma medida que su dibujo de siempre. Son **16 dibujos**.
El dibujo y la ruta de hoy no cambian, y el juego sigue pidiendo sólo ésos.

**Los provisionales** de estos 150 lugares nuevos (126 dibujos de la pieza y 24
íconos) son rellenos como los de hoy, hechos por `herramientas/rellenos.py` a la
medida servida. Los encendidos llevan una marca que dice su estado. Viven en una
carpeta del repo **fuera de los estáticos** (`web/arte_por_venir/` propuesto, con
las mismas rutas), para que la página congelada no cambie ni los sirva. Una
prueba comprueba que estén todos y que no sobre ninguno, como `tests/test_arte.py`
hace con los de hoy **[llamada mía]**.

### Las criaturas

**Rutas** (familia `criaturas`, con las claves del juego para la especie, la
etapa, el ánimo y el sombrero):

| Lugar | Ruta | Cuántos |
|---|---|---|
| Cuerpo de una forma | `criaturas/<especie>/<etapa>/cuerpo-<o>.png`, con `o` en `se`, `so`, `no` y `ne` | 25 × 5 × 4 = 500 |
| Cara de una forma | `criaturas/<especie>/<etapa>/cara-<ánimo>-<o>.png`, con `o` en `se` y `so` | 25 × 5 × 3 × 2 = 750 |
| Sombrero de una forma | `criaturas/<especie>/<etapa>/sombrero-<sombrero>-<o>.png` | 25 × 5 × 6 × 4 = 3000 |
| Cara o sombrero de toda la especie | `criaturas/<especie>/cara-…` y `criaturas/<especie>/sombrero-…` | 25 × 30 = 750 |
| Cara o sombrero común | `criaturas/comun/cara-…` y `criaturas/comun/sombrero-…` | 30 |

Son **5 030 lugares**. Las etapas son `bebe`, `nino`, `adolescente`, `adulto` y
`adulto_grande`; los ánimos, `feliz`, `normal` y `mal`; los sombreros, los seis
de `cosmeticos.SOMBREROS`.

- **La especie va por su clave y no por su nombre** (`dragoncito`, no
  `tsushimon`; aceptado por el dueño). `fuentes/` usa los nombres para que el
  dibujante los reconozca, pero un nombre puede cambiar, y una ruta que cambia
  pierde lo subido. El dibujante no escribe rutas: toca una tarjeta que lleva el
  nombre.
- **El orden de los tramos sigue el resto del contrato**: carpetas por
  especie y etapa, y la orientación al final del nombre, separada por un guion.
  A2 sólo ponía su forma de ejemplo **[llamada mía]**.
- **De espaldas (`no` y `ne`) no hay cara**, como en A2.
- **Se suben a 1024 × 1024 exactos.** Se guardan con una versión chica de
  256 × 256, que sólo usa la página del dibujante.
- **Se guardan** en la misma tabla y la misma carpeta que todo lo subido, con el
  mismo historial y la misma poda.
- **Su provisional** es la capa de frente de hoy ampliada ×4, como en
  «Enfoques». Las especies que todavía no tienen dibujos en `fuentes/` usan como
  provisional del cuerpo el relleno de `retrato` (`retrato.relleno`), el mismo
  que hoy enseña su retrato. Se arma al pedirlo y se recuerda en memoria por su
  capa de origen.
  Para eso hace falta una función nueva en `retrato.py`, que es quien sabe buscar
  en `fuentes/`. Las cuatro orientaciones de un cuerpo tienen el mismo
  provisional, y su nombre dice cuál es cuál.
- **Una casilla de forma está cubierta** si tiene una capa al día para esa forma,
  para toda su especie o común, en ese orden, como en A2. **El cuerpo no se
  comparte**: cada etapa de cada especie lleva los suyos, como ya decía A2.

### Las descargas

- **«Descargar el provisional»** de cada lugar baja a la medida de subida. En la
  familia `pieza` es el relleno al doble, sin suavizar (cada píxel, un cuadrado
  de 2 × 2), o el original de `fuentes/pieza/` si el repo lo tiene. En las
  criaturas es la capa de frente ×4. En las demás familias, también los íconos
  nuevos, es el archivo de siempre.
- **«Descargar la imagen subida»** baja el **original**.
- **El zip de arriba con lo subido** baja el original de cada lugar con algo
  puesto, con su ruta como nombre, **sin las criaturas**. Su botón cambia de
  nombre (ver «Frases»).
- **«Descargar los provisionales»** de arriba trae todos, a la medida de subida,
  en carpetas por grupo, **sin las criaturas**.
- **Cada especie** tiene sus dos zips, el de lo subido y el de los provisionales.
  Son las mismas rutas con `?grupo=<clave>`. Las criaturas quedan fuera de los
  zips de arriba porque, subidas todas, serían varios GB que el servidor tendría
  que armar en un temporal (aceptado por el dueño).
- Todo sigue pidiendo el permiso y sin caché.

### La página del dibujante

- **Arriba, todo menos las criaturas**, como hoy: unas 420 tarjetas plegadas por
  grupo, que se arman al cargar.
- **Debajo, «Criaturas»**: 25 especies plegadas, cada una con su cuenta
  («12 de 170»), y aparte «Capas comunes a todas las especies». La lista general
  no trae sus capas. **Al abrir una especie se piden sólo las suyas**, y dentro
  cada parte se arma al abrirla: las cinco etapas (con el cuerpo, las caras y,
  plegados, los sombreros) y «Para todas las etapas de <especie>».
- **Cada lugar trae su miniatura.** Si tiene algo subido, la versión chica (que
  en las criaturas es de 256). Si no, su provisional sin ampliar. Las imágenes se
  piden al verse (`loading="lazy"`), y las secciones cerradas no piden nada.
  Abrir y recorrer una especie entera baja del orden de unos pocos MB.
- **Las tarjetas son las de hoy**, con «Subir», «Historial», «Volver a la
  anterior», «Volver al provisional» y las dos descargas. Cada tarjeta enseña la
  medida de subida, y las encendidas, una nota que lo dice. Una casilla de forma
  que no tiene capa propia pero está cubierta lo dice, con la miniatura de la que
  la cubre. Volver atrás una capa de toda la especie o común pide confirmación,
  porque afecta a otras.
- **«Sólo lo que falta»** enseña lo provisional y lo que tiene otra medida. Las
  casillas cubiertas no cuentan como faltantes, y los lugares compartidos (de
  especie y comunes) tampoco, porque son opcionales **[llamada mía]**. En las
  especies sin abrir, el filtro esconde las que están completas.
- **Lo que manda el servidor:** `GET …/api/piezas` sigue dando los grupos, ahora
  también con `total` y `hechas`. Los de `criaturas` llegan sin sus piezas.
  `GET …/api/piezas?grupo=<clave>` da un grupo entero. La vista de cada lugar
  gana la dirección de su original, su miniatura, su estado (apagado o encendido)
  y, en las criaturas, su etapa (o «especie» o «común»), su capa, su ánimo o su
  sombrero y su orientación, para armar las secciones sin leer la ruta.
- **Las capas de criatura no se pintan como cuadros** (sin `dib-cuadros`): a
  1024 no son pixel art.

### El avance

La forma del contrato del avance no cambia; sólo aparecen grupos y crecen
algunos.

| Grupos | `clave` | `familia` | `total` |
|---|---|---|---|
| 24 nuevos, uno por objeto por venir | `pieza/muebles/<clave>` | `pieza` | 4, u 8 con su encendido (el balcón, 2) |
| 25 nuevos, uno por especie | `criaturas/<especie>` | `criaturas` | 170 |
| Lámpara, Calefactor, Chimenea y Fuente (los de hoy) | la de siempre | `pieza` | pasa de 4 a 8, con su encendido |
| Iconos de los muebles (el de hoy) | la de siempre | `iconos` | pasa de 19 a 43, con los 24 nuevos |

- **El encendido va en el grupo del mueble**, como decidió el dueño: el grupo
  cuenta los dos estados y está hecho cuando están todos.
- **`hechas`** cuenta los lugares **al día**.
- **En una especie**, `hechas` son sus 170 casillas de forma (20 cuerpos, 30
  caras y 120 sombreros) cubiertas por una capa al día de cualquier nivel. Subir
  una capa común puede hacer avanzar varias especies a la vez, y `hechas` nunca
  pasa de `total`.
- **El grupo de las capas comunes no sale en el avance**: no lleva tarjeta,
  porque el dueño pidió una por especie, y lo que sube ya se cuenta en cada
  especie que cubre **[llamada mía]**.
- **Que crezcan grupos de hoy no esconde nada ahora**: como no hay nada subido,
  ninguna tarjeta de mueble ni de íconos está hecha. Lo que pasaría si un grupo
  creciera con su tarjeta ya hecha es cosa del sitio (ver «Lo que le toca al
  sitio»).
- Se calcula como hoy, con una lectura de la tabla y sin abrir imágenes.
  Recorrer 4 250 casillas es despreciable.
- El tablero tiene hoy 35 tarjetas y tendrá **84**.

### El tope de peso

Un solo tope de **24 MB** para todo, que se corta leyendo el cuerpo a trozos
como hoy, con su frase. El servidor tiene que poder leer y reducir uno así: unos
24 MB del cuerpo y unos 24 MB de píxeles, por subida.

### El espacio en disco

Es una estimación gruesa. La parte de las criaturas se midió con una capa de
frente de hoy ampliada y con grano; lo demás, por píxeles.

| Qué | Lugares | Una vuelta completa (original y versión chica) |
|---|---|---|
| La familia `pieza` a la medida nueva (75 del juego, 16 encendidos de los de hoy, 110 de los objetos nuevos) | 201 | 0,3 a 0,7 GB (unos 375 megapíxeles) |
| Las criaturas, todo por forma | 4 250 | 0,7 a 2,5 GB (un cuerpo pintado pesa algo más de 1 MB; una cara, menos de 0,2; un sombrero, unos 0,1 a 0,4) |
| Lo demás (pixel art, con los 24 íconos nuevos) | 219 | unos pocos MB |
| La tabla | — | unos pocos MB |

Con las versiones que se conservan (hasta cinco por lugar), **contar de 2 a 5 GB
en la práctica y hasta unos 15 GB en el peor caso**, más el temporal de un zip
mientras se arma (hasta lo que pesen los originales de los muebles). Compartir
sombreros por especie baja mucho la parte de las criaturas. Si hiciera falta,
la palanca es conservar menos versiones de las capas de criatura. Por ahora se
queda en cinco, como todo **[llamada mía]**.

### Lo que no cambia para quien juega, y cómo se comprueba

- `arte.piezas()` sigue con sus 270 piezas y su medida servida, y `arte.json`
  sale idéntico.
- El bloque `arte-subido` de la portada sigue vacío mientras no se suba nada. Con
  una subida nueva de una pieza del juego lleva su versión chica, de la medida de
  siempre. Nunca lleva un lugar que el juego no pinta.
- Las rutas que pide la página no cambian.
- Cambian `dibujante.js` y su hoja de estilos, y con ellos la versión de los
  estáticos: quien juega vuelve a bajar los archivos de la página una vez. No ve
  nada distinto. Ya pasó con cada cambio de la página del dibujante.

## Lo que queda al constructor

- Los nombres: de las columnas, de la lista de lugares, de la carpeta de los
  provisionales nuevos y de los parámetros de las rutas.
- Los dibujos de los rellenos nuevos (el balcón, la marca del encendido).
- Partir el trabajo en planes. Por ejemplo: (1) la medida nueva y el original,
  sin lugares nuevos, que se puede publicar solo; (2) los objetos por venir, sus
  íconos y los encendidos; (3) las criaturas y la página plegada.
- Las pruebas que fijan lo congelado: las 270 piezas y el `arte.json`; el bloque
  de la portada sin subidas y con una subida nueva; `arte_vigente`; y que una
  lectura de `ruta, archivo, ancho, alto`, como la del mundo en línea, sigue
  funcionando con las columnas nuevas.
- Medir la portada y la dirección de lo subido con unas 10 000 filas sintéticas
  en la tabla. Si se nota, un índice por ruta, o recordar lo que se conserva
  mientras no cambie la última fila.
- Poner al día `AGENTS.md` (la invariante de la familia `pieza`, que hoy dice
  «también el doble se rechaza», y la de lo subido), `docs/arte/contrato.md` (las
  secciones nuevas para el dibujante) y el README si lo nombra.

## Riesgos

- **«Tal cual» no son los mismos bytes.** La limpieza vuelve a escribir la imagen
  en RGBA de 8 bits, sin metadatos, y se queda (es la protección contra archivos
  raros). Un PNG de 16 bits se guarda a 8, y uno con perfil de color se convierte
  a sRGB (ver «Subir, volver, podar y servir»). La prueba con un archivo real del
  dibujante, en «Para publicar», sólo confirma la conversión.
- **El espacio y las copias.** El diseño de la mudanza del juego (en la rama del
  ejecutable) cuenta con «unos pocos» MB de arte subido y guarda 14 copias de
  cada noche. Con esto, el arte puede llegar a varios GB. Que la copia de cada
  noche lleve sólo lo nuevo de esa noche (un archivo subido nunca cambia, porque
  su nombre es su contenido) **es tarea del proyecto de la mudanza**, en sus
  guiones, y no de este trabajo **[llamada mía]**. Aquí no hay tarea para eso.
- **Mientras el juego siga en la Raspberry**, cuya tarjeta tiene pocos GB libres,
  conviene que **el dibujante no suba criaturas en masa hasta la mudanza**. Los
  lugares de las criaturas se publican igual, y quien publique se lo avisa al
  dueño **[llamada mía]**.
- **La rama del ejecutable.** Al juntarla con ésta **habrá conflictos en
  `arte_subido.py` y `web/dibujante.py`** (y en sus pruebas): esa rama todavía
  tiene la versión que acepta las dos medidas. **Su armado tiene que copiar sólo
  lo que usa su contrato**, no la carpeta entera, que con las criaturas pesará
  GB. Su mundo en línea ya lee esta tabla y esta carpeta: con este diseño sigue
  leyendo igual y recibe la versión chica. Para usar los originales, tiene que
  leer `original` y servir también esos archivos, porque su código de hoy sólo
  conserva `archivo`. Y adopta tal cual las claves, las rutas y las formas que
  fija este documento: si algún día cambiara una, lo subido a ella quedaría «con
  otra medida» o huérfano.
- **El balcón queda detrás de la pared.** Visto desde la pieza, una tira por
  fuera de las paredes del fondo la tapa la pared. Su lienzo lo fija este
  documento; cómo lo deja ver (por ejemplo, con un vano en la pared) es cosa del
  ejecutable.
- **El rendimiento con miles de filas.** La portada lee la tabla en cada visita,
  y la dirección de lo subido calcula lo que se conserva en cada imagen. Hoy no
  hay filas; con las criaturas pueden ser decenas de miles. Se mide antes de
  publicar (ver «Lo que queda al constructor»).
- **Una subida de 24 MB** por el túnel o desde un teléfono puede tardar o
  cortarse. Se prueba con un archivo de verdad.
- **El provisional de frente para una capa de espaldas** sólo da posición y
  tamaño. La página lo dice en una nota.
- **Una tarjeta hecha cuyo grupo crece.** Hoy no pasa, porque no hay nada
  subido. Si más adelante un grupo hecho gana lugares (otro estado, otro
  objeto), el sitio tendría que reabrir su tarjeta (ver «Lo que le toca al
  sitio»).

## Lo que le toca al sitio (otro repo)

- La categoría «Criaturas» para la familia `criaturas`, como pedía A2.
- **Requisito, si se quiere que el tablero no esconda trabajo**: cuando una
  tarjeta está «hecha» y su grupo pasa a tener `hechas` menor que `total` porque
  creció, volverla a «en curso». Hoy no hace falta para este diseño, pero es lo
  que lo cubriría si algún grupo crece con su tarjeta ya hecha.

## Para publicar

Cada paso que toca producción necesita el permiso expreso del dueño en ese
momento.

1. **El sitio primero**, con su categoría «Criaturas», como pedía A2. Sola es
   inofensiva. Si el juego saliera antes, las especies se sembrarían en
   «Avatar».
2. **Antes del juego**, confirmar con **un archivo real del dibujante** que sus
   colores llegan igual. La conversión a sRGB ya viene construida, y esto sólo la
   confirma.
3. **Probarlo en una página de prueba** (`herramientas/pagina_de_prueba.py
   --dibujante N`), no en producción, porque el historial no se borra: subir un
   mueble del juego a la medida nueva y verlo reducido en la página, subir un
   objeto por venir, su encendido y su ícono, abrir una especie, descargar.
4. **El juego**, con la copia de la base de siempre. Al arrancar, la tabla gana
   sus columnas. Se comprueba desde fuera que el bloque de la portada sigue
   vacío, que la página del dibujante carga y pliega las especies, que el avance
   trae los grupos nuevos y que el mundo en línea del ejecutable sigue leyendo la
   tabla.
5. **Quien publique le avisa al dueño** que, mientras el juego siga en la
   Raspberry, conviene que el dibujante no suba criaturas en masa hasta la
   mudanza. **El dueño le avisa al dibujante** eso y la medida nueva.
6. **Al juntar esta rama con la del ejecutable**, resolver los conflictos de
   `arte_subido.py` y `web/dibujante.py` a favor de este diseño, y que su armado
   copie sólo lo que usa su contrato.

## Frases para aprobar

Sólo las ven el dueño y el dibujante. Entre llaves va lo que pone la página.

**Nombres de los grupos** (en la página y en las tarjetas del tablero):

- Objetos: «Consola Flappy», «Consola Pong», «Mesa de gato», «Atril»,
  «Tocadiscos», «Mayordomo robot», «Puerta de cristal», «Bloque de cableados»,
  «Súper Dado», «Mega TV», «Lámpara Dragón», «Silla azul», «Silla roja», «Silla
  verde», «Silla amarilla», «Silla negra», «Silla blanca», «Mesa azul», «Mesa
  roja», «Mesa verde», «Mesa amarilla», «Mesa negra», «Mesa blanca» y «Balcón».
- Especies: su nombre del juego («Piollito», «Tsushimon»…).
- Sólo en la página, sin tarjeta: «Capas comunes a todas las especies».

**Botones y títulos:**

- «Descargar lo subido» (hoy dice «Descargar lo que se ve»; ahora baja los
  originales).
- «Descargar los provisionales» (se queda; ya no trae las criaturas).
- En cada especie: «Descargar lo subido de {especie}» y «Descargar los
  provisionales de {especie}».
- «Criaturas».
- En cada grupo: «{nombre} · {hechas} de {total}».
- Las etapas: «Cría», «Niño», «Adolescente», «Adulto» y «Adulto grande»; y
  «Para todas las etapas de {especie}».
- Las capas: «Cuerpo», «Caras» y «Sombreros».
- En cada tarjeta de criatura: «Cuerpo · {orientación}», «Cara
  {feliz/normal/mal} · {orientación}» y «{sombrero} · {orientación}».
- Las orientaciones: «se · de frente, hacia abajo a la derecha», «so · de frente,
  hacia abajo a la izquierda», «no · de espaldas, hacia arriba a la izquierda» y
  «ne · de espaldas, hacia arriba a la derecha».
- «Cargando las capas…».

**Avisos y notas:**

- Otra medida (reemplaza la de hoy): «Lo subido mide {a} × {b} px y este lugar
  pide {A} × {B} px: hay que volver a subirlo.»
- El tope (reemplaza la de 4 MB): «La imagen pesa más de 24 MB.»
- Un dibujo encendido: «El dibujo de siempre es el apagado; éste es el
  encendido.» En la Puerta de cristal: «La de siempre es la sólida; ésta es la
  que se puede atravesar.»
- El mayordomo: «Alto como tu avatar: unos 717 px del original, de pie en el
  centro de la casilla.»
- El balcón: «La tira de 4 × 1 casillas que queda por fuera de la pared, con su
  baranda. Como lo de pared: «se» va en la pared izquierda y «so», en la
  derecha.»
- En las criaturas: «Cada capa mide 1024 × 1024 y se apila con las demás de su
  etapa en el mismo lienzo. De espaldas no lleva cara.» y «El provisional es la
  capa de frente de hoy, ampliada: dice dónde va y de qué tamaño, no cómo se ve
  de lado ni de espaldas.»
- Una casilla cubierta: «Usa la de toda la especie.» / «Usa la común.»
- Antes de volver atrás una capa de toda la especie: «Esta capa la usan todas las
  etapas de {especie} que no tienen la suya. ¿Seguir?»
- Antes de volver atrás una capa común: «Esta capa la usan todas las especies que
  no tienen la suya. ¿Seguir?»
