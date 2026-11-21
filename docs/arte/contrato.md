# El contrato de arte del pueblo

Esto es para ti, que dibujas. No hace falta tocar código.

Tu camino es **la página del dibujante**: ahí subes cada dibujo con el nombre y la medida que dice esta lista. Guardar archivos en carpetas del repositorio es sólo para quien trabaja con él.

## La regla de oro

**Reemplazar un dibujo es guardar el archivo nuevo con el mismo nombre y el mismo tamaño.**

Todos los dibujos viven en `web/static/arte/`. Hoy cada archivo es un *relleno*:
un dibujo provisional, simple y a propósito feo, para que se note qué falta.
Cuando guardas el tuyo encima, el juego lo usa solo. Si un archivo falta o no
mide lo que dice esta lista, una prueba automática lo avisa.

- Formato: **PNG con transparencia** (RGBA). En Aseprite: *Archivo > Exportar* y deja el modo RGB.
- Tamaño: **exacto**, en píxeles. Ni uno más ni uno menos.
- Las partes que no se dibujan se dejan **transparentes**, nunca de un color.
- Si quieres ver cómo quedaría el relleno de nuevo, borra el archivo y pide que se regenere.

## Los dibujos de ahora (270)

### Pueblo (`pueblo/`)

| Archivo | Tamaño | Qué es |
|---|---|---|
| `pueblo/fondo.png` | 1380 × 860 | El suelo del pueblo: pasto y caminos. **Sin lugares encima**: cada lugar va en su archivo. Es el doble del tamaño del mapa (690 × 430), así que un píxel del mapa son dos del dibujo. |
| `pueblo/lugares/<lugar>.png` | 160 × 160 | La casa o figura de cada lugar. Fondo transparente. Se **apoya en el borde de abajo**: el punto donde el personaje llega es el centro del borde inferior. Sin texto: el nombre lo escribe el mapa. |

Los siete lugares: `casa` (tu departamento), `tienda`, `plaza`, `barrio`, `estadio`, `cementerio`, `aventura`.
Por ejemplo: `pueblo/lugares/plaza.png`.

### Escenas (`escenas/`)

| Archivo | Tamaño | Qué es |
|---|---|---|
| `escenas/<lugar>.png` | 720 × 480 | El fondo de la pantalla de cada lugar: seis, uno por cada lugar de arriba menos `casa`, que no lleva escena porque ahí se ve la pieza de tu departamento (más abajo). Por ejemplo `escenas/cementerio.png`. Ocupa todo el cuadro, sin transparencia. |

- **La escena no se ve entera.** En pantalla el cuadro es más cuadrado que el dibujo: se ve todo el alto y se recorta por los dos lados, por igual. En un teléfono se pierde de un décimo a un quinto del ancho; en el computador, de un quinto a un cuarto, y hasta cerca de la mitad si la ventana es angosta. Lo importante va en la mitad central, que se ve siempre. (En algunos teléfonos acostados es al revés: se ve todo el ancho y se pierde un décimo por arriba y otro por abajo.)
- **Dónde pisan.** Cuando se ve todo el alto, y contando desde abajo:
  - **El avatar**, a la izquierda: el borde de abajo de su dibujo queda al 14 % del alto, y sus pies, cuatro píxeles de su dibujo más arriba (de los 84 que mide), así que caen cerca del 16 %: entre el 15 % y el 17 % según la pantalla, unos 73 a 80 px de los 480 del dibujo.
  - **El gachamon**, algo a la derecha del centro: el borde de abajo de su retrato queda al 6 % (unos 29 px), y sus pies, apenas más arriba por el margen que deja el retrato: con los retratos que ya están dibujados, entre el 6,4 % y el 6,7 % (unos 31 px). La sombra que el juego le pone en la escena baja hasta cerca del 4 % (unos 19 px).
  - Así que el suelo tiene que llegar, desde abajo, por lo menos hasta el 17 % del alto (unos 80 px).

### El avatar (`avatar/`)

El avatar es la persona que camina por el pueblo. Se arma apilando **tres capas**
de abajo hacia arriba: **cuerpo, ropa, pelo**. Las tres capas de una misma pose
tienen que **calzar exactas** al ponerlas una sobre otra, así que usa el mismo
lienzo y no muevas nada de lugar entre capas.

- Todos los archivos de avatar miden **48 × 84** y tienen fondo transparente.
- El personaje **mira a la derecha**. La nuca queda a la izquierda.
- Los **pies se apoyan cerca del borde de abajo** (a unos 4 píxeles) y el cuerpo va **centrado a lo ancho**.
- El juego lo dibuja con la sombra que ya trae la capa del cuerpo.

Hay tres **poses**, que se escriben siempre igual al final del nombre:

| Pose | Qué es |
|---|---|
| `quieto` | De pie, parado. |
| `paso1` | Un paso: una pierna adelante. |
| `paso2` | El otro paso: la otra pierna adelante. Se alterna con `paso1` al caminar. |

`paso1` y `paso2` tienen que **verse distintos** de `quieto` y entre sí. Cambian
sobre todo las piernas (y el borde de la ropa si hace falta). El torso y la
cabeza se quedan donde están.

| Archivo | Cuántos | Qué lleva |
|---|---|---|
| `avatar/cuerpo/<piel>-<pose>.png` | 12 | Sombra, piernas, brazos, cabeza y cara, en el color de la piel. |
| `avatar/ropa/<ropa>-<pose>.png` | 12 | Pantalón o falda, tronco y mangas. Va encima del cuerpo. |
| `avatar/pelo/<peinado>-<color>-<pose>.png` | 90 | Sólo el pelo (cinco peinados, seis colores). Va encima de todo. Puede ser igual en las tres poses. |

Los nombres que van en lugar de las palabras entre `< >`:

- `<piel>`: `clara`, `media`, `tostada`, `oscura`.
- `<ropa>`: `poleron`, `camisa`, `vestido`, `overol`.
- `<peinado>`: `corto`, `largo`, `rizado`, `coleta`, `rapado`.
- `<color>`: `negro`, `castano` (sin eñe), `rubio`, `rojo`, `cano`, `azul`.
- `<pose>`: `quieto`, `paso1`, `paso2`.

Ejemplos: `avatar/cuerpo/oscura-paso2.png`, `avatar/ropa/overol-paso1.png`,
`avatar/pelo/coleta-azul-quieto.png`.

Un truco: puedes dibujar un solo color de pelo y los demás sacarlos cambiando el
tono, pero cada color es un archivo aparte.

### Efectos (`efectos/`)

| Archivo | Tamaño | Qué es |
|---|---|---|
| `efectos/corazon.png` | 32 × 32 | Un corazón (cariño). |
| `efectos/estrella.png` | 32 × 32 | Una estrella (logros). |
| `efectos/marca.png` | 32 × 32 | La marca de destino: donde vas a caminar al tocar el mapa. |
| `efectos/sombra.png` | 32 × 32 | La sombra del gachamon en el mapa. Va en el suelo, bajo sus pies (el centro del dibujo cae justo donde pisa), y **no salta con él**: cuando da sus saltitos al caminar, se queda abajo. Oscura y translúcida, para que se vea el suelo a través. (El avatar no la usa: su sombra viene en su capa del cuerpo.) |

Fondo transparente y la figura centrada.

El juego dibuja `efectos/corazon.png` en los corazones que suben al acariciar
al gachamon (se ve entre 24 y 32 píxeles) y `efectos/estrella.png`, a 20
píxeles, delante de cada medalla conseguida de la ficha y en el aviso de una
medalla nueva. Si falta un archivo, se ve el recuadro de esa pieza.

### Íconos (`iconos/`)

Son los dibujitos de lo que se compra y se lleva. Se ven **en la tienda y en la
mochila, a 48 píxeles**, así que hay que dibujarlos legibles y simples. Todos
miden **48 × 48**, con **fondo transparente**. Hay uno por cada cosa del juego,
y su nombre es la clave de esa cosa: si el juego suma un objeto nuevo, pedirá
su ícono con el mismo nombre.

| Archivo | Cuántos | Qué es |
|---|---|---|
| `iconos/objetos/<clave>.png` | 32 | Cada objeto: pociones, golosinas, porotos, sopaipillas, placa, silbato, semilla. También los que no se venden, porque se ven en la mochila. |
| `iconos/cosmeticos/<clave>.png` | 12 | Cada cosmético del gachamon: sombreros y títulos. |
| `iconos/muebles/<clave>.png` | 19 | Cada mueble del departamento que se vende, la cama sencilla incluida. La puerta no lleva ícono: no se vende ni se guarda. Hay además 24 íconos de muebles por venir, que el juego todavía no pide: están en «Los objetos que el juego todavía no tiene». |

Cada ícono ya tiene su relleno en `web/static/arte/iconos/`, con el nombre
exacto de su archivo: dibuja el tuyo y guárdalo encima. Por ejemplo:
`iconos/objetos/fuerza_1d4.png`, `iconos/cosmeticos/corona.png`,
`iconos/muebles/lampara.png`.

El relleno de un ícono es un cuadro de color liso (un color por grupo) con las
primeras letras del nombre, porque a este tamaño no cabe la palabra «RELLENO».

## La pieza de tu departamento

Es lo único de este contrato que **no es pixel art**: se dibuja con suavizado,
a lo grande, y la página lo sirve reducido a la mitad. Todo se dibuja en vista
isométrica, y la medida de partida es **la casilla: un rombo de 1024 × 512** que
llena su lienzo. Los tamaños de abajo son los **originales** (los que tú
dibujas); la página sirve cada uno a la mitad.

**Si dibujas y no tienes el repositorio, nada de esto es tuyo: tu camino es subir cada archivo desde la página del dibujante** (ver «Lo que subes en la página del dibujante», más abajo). Lo que sigue es la vía de quien trabaja con el repositorio, y sólo cubre las piezas que el juego ya pinta, no lo nuevo de las secciones del final.

Quien tiene el repositorio deja los originales en **`fuentes/pieza/`**, con **el mismo nombre y la misma
subcarpeta** que tiene el relleno en `web/static/arte/pieza/` (por ejemplo,
`fuentes/pieza/muebles/cama-se.png`). Después corre
`./venv/bin/python -m herramientas.pieza`, que comprueba que cada original mide
exactamente lo que dice esta lista (si no, lo dice y no escribe nada) y
guarda la copia reducida en `web/static/arte/pieza/`.

| Archivo | Cuántos | Tamaño original | Qué es |
|---|---|---|---|
| `pieza/suelo.png` | 1 | 1024 × 512 | Una casilla de suelo: un rombo que llena el lienzo. Se repite en cada casilla de la pieza. |
| `pieza/pared-izquierda.png`, `pieza/pared-derecha.png` | 2 | 512 × 1280 | Un tramo de pared: media casilla de ancho, con su pendiente (256 de subida) y 1024 de alto. La izquierda sube hacia la derecha; la derecha, hacia la izquierda. |
| `pieza/muebles/<clave>-<orientación>.png` | 4 por cada mueble de suelo | `(a + f) × 512` de ancho y `(a + f) × 256` de alto, más 1024 de alto si el mueble es de bulto | Un mueble de suelo, con cuatro imágenes: una por cada orientación. |
| `pieza/muebles/<clave>-se.png` y `-so.png` | 2 por cada mueble de pared | `tramos × 512` de ancho y `tramos × 256 + 1024` de alto | Un mueble de pared. |

En la fila de los muebles, `a` y `f` son el **ancho** y el **fondo** del mueble
en casillas, y `tramos` es el ancho de uno de pared. Los de suelo son **de
bulto** (sobresalen del suelo: una lámpara, una cama) o **planos** (se pisan:
el felpudo y la alfombra, que miden sólo `(a + f) × 256` de alto). Por ejemplo:

| Mueble | Archivo | Tamaño original |
|---|---|---|
| Maceta, de 1 × 1 | `pieza/muebles/maceta-se.png` | 1024 × 1536 |
| Felpudo, plano de 1 × 1 | `pieza/muebles/felpudo-no.png` | 1024 × 512 |
| Cama sencilla, de 2 × 1 | `pieza/muebles/cama_sencilla-so.png` | 1536 × 1792 |
| Fuente, de 2 × 2 | `pieza/muebles/fuente-ne.png` | 2048 × 2048 |
| Alfombra, plana de 2 × 2 | `pieza/muebles/alfombra-se.png` | 2048 × 1024 |
| Cuadro, de pared (1 tramo) | `pieza/muebles/cuadro-se.png` | 512 × 1280 |
| Cortinas, de pared (2 tramos) | `pieza/muebles/cortinas-so.png` | 1024 × 1536 |

`<clave>` es el nombre del mueble en el juego, el mismo del ícono
(`iconos/muebles/<clave>.png`): `felpudo`, `maceta`, `cuadro`, `estanteria`,
`lampara`, `alfombra`, `cortinas`, `cojines`, `fuente`, `chimenea`,
`calefactor`, `cama`, `ventanal`, `biblioteca`, `cama_sencilla`,
`refrigerador`, `consola`, `ducha` y `pesas`. La puerta (`puerta`) tiene sus
dibujos de pieza, pero ningún ícono.

### Las cuatro orientaciones

`<orientación>` dice **hacia dónde mira el frente del mueble** en el dibujo:

| Orientación | El frente mira |
|---|---|
| `se` | abajo a la derecha |
| `so` | abajo a la izquierda |
| `no` | arriba a la izquierda |
| `ne` | arriba a la derecha |

Cada mueble de suelo tiene **las cuatro, dibujadas una por una: nada se espeja**.
Un mueble de 2 × 1, girado un cuarto de vuelta, ocupa 1 × 2, pero **su lienzo
mide lo mismo**: las cuatro orientaciones de un mismo mueble tienen el mismo
tamaño de archivo, y en `so` y `ne` lo que dibujas es la caja con su huella girada.
El lado largo del mueble (su ancho, `a`) corre, en `se` y en `no`, **de arriba a
la izquierda hacia abajo a la derecha**; en `so` y en `ne`, girado, de arriba a
la derecha hacia abajo a la izquierda. El relleno de la cama sencilla
(`pieza/muebles/cama_sencilla-se.png` y sus otras tres) sirve de ejemplo.

Lo de pared lleva **sólo dos**: `se` es el que cuelga en la **pared izquierda**
(mira abajo a la derecha) y `so` el que cuelga en la **pared derecha** (mira
abajo a la izquierda). No hay `no` ni `ne` de lo que va en la pared.

### La puerta

La puerta de cada departamento es un mueble de pared de un tramo, así que lleva
**dos archivos**: `pieza/muebles/puerta-se.png` (la que va en la pared
izquierda) y `pieza/muebles/puerta-so.png` (la de la derecha). Miden lo que
cualquier cosa de pared de un tramo: **512 × 1280** de original (256 × 640
servido). **No tiene ícono**: no se vende ni se guarda, y ninguna pantalla lo
pide.

Se dibuja como **el vano de una puerta visto desde dentro**: ocupa su tramo de
pared **de arriba abajo**, con su marco y el hueco por el que se sale. Tu avatar
se pinta **de pie en su umbral**, delante del dibujo, así que **el dibujo no debe
traer a nadie dentro ni tapar el umbral** (la casilla de la puerta es la que
queda fuera del departamento, junto a su pared).

Para que tu avatar quepa en el hueco, esto es **dónde cae dentro del dibujo**,
contando desde la esquina de arriba a la izquierda del original de 512 × 1280:
ocupa una caja de unos 410 × 717, pegada al borde de delante del dibujo. En
`puerta-se.png` va **de x 0 a 410**; en `puerta-so.png`, **de x 102 a 512**; y
en los dos, **de y 444 a 1161**. Servido, la mitad: de x 0 a 205 o de 51 a 256,
y de y 222 a 580. Es la misma caja con cualquier tamaño de pieza y en cualquier
tramo; la página redondea el avatar al píxel de pantalla, así que en pantalla
puede correrse un poco. Se pinta siempre delante del dibujo: lo del marco que
caiga dentro de esa caja queda detrás de él.

Su relleno es un marco claro con un hueco oscuro de arriba abajo, el rótulo
«PUERTA» y un pomo amarillo, para que no se confunda con un cuadro.

### Cómo se coloca cada dibujo

- **Un mueble de suelo** cubre **a lo ancho exactamente su huella**: de la esquina
  izquierda a la esquina derecha del rombo que ocupa. Su **borde de abajo
  coincide con la esquina de delante** de ese rombo. Si no se pisa, sobresale
  hacia arriba (1024 en el original). Lo que no es el mueble queda transparente.
- **Un tramo de pared**, o un mueble de pared, cubre **a lo ancho sus tramos** y
  **a lo alto toda la pared**: su borde de abajo sigue la línea de la pared, y
  por eso un mueble de pared de 2 tramos tiene el doble de ancho y la pendiente
  de los dos tramos.
- Si falta un archivo, la página muestra el recuadro de esa pieza, nunca el
  dibujo de otra.

El relleno de la pieza es una caja de color liso sobre la huella, con las
primeras letras de la clave y, en su cara hacia la que mira, una marca amarilla
(y una flecha en la tapa) para que girar se note.

## Lo que subes en la página del dibujante

**Tú, que dibujas, subes todo desde la página del dibujante**: no necesitas el repositorio ni correr nada. Lo de más arriba sobre guardar originales en `fuentes/pieza/` y correr una herramienta es sólo para quien trabaja con el repositorio: tú subes tu original en la página, y ella hace lo demás.

Todo lo de la pieza del departamento (suelo, paredes y muebles) lo subes **a la medida de original**, la de la columna «Tamaño original» de arriba: el doble de lo que se ve en pantalla (la casilla, de 1024 × 512). Si subes uno de la mitad, la página lo rechaza y te dice qué medida pide ese dibujo.

- La página guarda **tu original**, con su medida y su transparencia, y, aparte, una versión reducida a la mitad, que es la que usa el juego. Tú no reduces nada. Tu original se guarda a 8 bits por canal (si lo exportas a 16, queda a 8) y, si traía un perfil de color, ya pasado a sRGB (lo explica el punto siguiente).
- Cada imagen puede pesar **hasta 24 MB**. Es PNG con transparencia, como siempre.
- Si tu PNG trae un perfil de color (por ejemplo Display P3), la página lo pasa a sRGB, que es el color de las pantallas corrientes, y guarda la imagen sin el perfil. Si no trae perfil, queda como la dibujaste.
- De cada dibujo se conservan **las cinco últimas imágenes distintas** que subas, cada una con su original y su versión reducida. «Volver a la anterior» las recorre.
- Lo que no es de la pieza (pueblo, escenas, avatar, efectos e íconos) se sube a su medida de siempre.

Los dibujos de las secciones que siguen **todavía no los pinta el juego**: se van adelantando para cuando el juego los use. Aparecen en la página, con su provisional y su avance, pero nadie los ve jugando. El **avance** es la cuenta de lo que ya está dibujado de cada grupo (por ejemplo, 4 de 8); se ve en el tablero de tareas del proyecto.

## Los muebles que se encienden

Cuatro muebles de hoy tienen **un segundo dibujo, el encendido**: la lámpara, el calefactor, la chimenea y la fuente. El dibujo de siempre es el apagado; el encendido es el mismo mueble prendido (con luz, fuego o agua corriendo).

| Mueble | Archivos del encendido | Tamaño original |
|---|---|---|
| Lámpara | `pieza/muebles/lampara-encendido-<orientación>.png` | 1024 × 1536 |
| Calefactor | `pieza/muebles/calefactor-encendido-<orientación>.png` | 1024 × 1536 |
| Chimenea | `pieza/muebles/chimenea-encendido-<orientación>.png` | 1536 × 1792 |
| Fuente | `pieza/muebles/fuente-encendido-<orientación>.png` | 2048 × 2048 |

Cada uno lleva **las cuatro orientaciones** (`se`, `so`, `no`, `ne`) y mide **lo mismo que su dibujo apagado**, en el mismo lienzo y con el mueble en el mismo lugar: así, al encender, solo cambia lo que se enciende. En la página, el encendido aparece dentro del grupo del mueble, junto a las cuatro orientaciones del dibujo apagado.

## Los objetos que el juego todavía no tiene

Son 24 objetos nuevos. Cada uno lleva **su dibujo de pieza** y **su ícono**.

- Dibujo de pieza: `pieza/muebles/<clave>-<orientación>.png`, con las cuatro orientaciones (el balcón, sólo dos, más abajo).
- Ícono: `iconos/muebles/<clave>.png`, de **48 × 48** como los demás (pixel art, fondo transparente).
- Si tiene un segundo estado, su dibujo va aparte, con las mismas orientaciones y la misma medida: `pieza/muebles/<clave>-encendido-<orientación>.png`. La excepción es la Puerta de cristal, cuyo segundo estado se llama `atravesable`: `pieza/muebles/puerta_cristal-atravesable-<orientación>.png`.

Todos son de bulto, como una lámpara: sobresalen del suelo (el balcón es un caso aparte, más abajo). La medida de la tabla es la de cada orientación.

| Clave | Nombre | Forma | Tamaño original (cada orientación) | Segundo estado |
|---|---|---|---|---|
| `consola_flappy` | Consola Flappy | bulto de 1 × 1 | 1024 × 1536 | no tiene |
| `consola_pong` | Consola Pong | bulto de 1 × 1 | 1024 × 1536 | no tiene |
| `mesa_gato` | Mesa de gato | bulto de 1 × 1 | 1024 × 1536 | no tiene |
| `atril` | Atril | bulto de 1 × 1 | 1024 × 1536 | no tiene |
| `tocadiscos` | Tocadiscos | bulto de 1 × 1 | 1024 × 1536 | `encendido` |
| `mayordomo` | Mayordomo robot | bulto de 1 × 1 | 1024 × 1536 | no tiene |
| `puerta_cristal` | Puerta de cristal | bulto de 1 × 1 | 1024 × 1536 | `atravesable` |
| `cableados` | Bloque de cableados | bulto de 1 × 1 | 1024 × 1536 | no tiene |
| `super_dado` | Súper Dado | bulto de 1 × 1 | 1024 × 1536 | no tiene |
| `mega_tv` | Mega TV | bulto de 2 × 1 | 1536 × 1792 | `encendido` |
| `lampara_dragon` | Lámpara Dragón | bulto de 1 × 1 | 1024 × 1536 | `encendido` |
| `silla_azul`, `silla_roja`, `silla_verde`, `silla_amarilla`, `silla_negra`, `silla_blanca` | Silla azul, roja, verde, amarilla, negra y blanca | bulto de 1 × 1 | 1024 × 1536 | no tiene |
| `mesa_azul`, `mesa_roja`, `mesa_verde`, `mesa_amarilla`, `mesa_negra`, `mesa_blanca` | Mesa azul, roja, verde, amarilla, negra y blanca | bulto de 1 × 1 | 1024 × 1536 | no tiene |
| `balcon` | Balcón | tira de 4 × 1 por fuera de la pared | 2560 × 2304 (sólo `se` y `so`) | no tiene |

Son 24 claves y 24 íconos (cada silla y cada mesa lleva el suyo, con su color). Cosas que conviene saber:

- **Mayordomo robot.** Es **tan alto como tu avatar**: unos 717 px del original, de pie en el centro de la casilla.
- **Puerta de cristal.** La de siempre es la sólida (`puerta_cristal-<orientación>.png`); la otra es la que se puede atravesar (`puerta_cristal-atravesable-<orientación>.png`).
- **Balcón.** Es la tira de 4 × 1 casillas que queda por fuera de la pared, con su baranda. Se comporta como lo de pared: lleva **sólo dos dibujos**, `se` en la pared izquierda y `so` en la derecha (`pieza/muebles/balcon-se.png` y `pieza/muebles/balcon-so.png`).
- Los que se encienden (Tocadiscos, Mega TV y Lámpara Dragón) llevan, además de sus cuatro dibujos de siempre, los cuatro del encendido, igual que los cuatro muebles de la sección anterior.

Cuentas: los 24 objetos suman 110 dibujos de pieza (23 objetos de cuatro orientaciones y el balcón de dos, más cuatro encendidos o atravesables de cuatro orientaciones cada uno: Tocadiscos, Puerta de cristal, Mega TV y Lámpara Dragón) y 24 íconos.

## Las criaturas

Cada criatura se arma **apilando capas**: el cuerpo, la cara y, si lleva, el sombrero. Cada capa es un PNG con transparencia de **1024 × 1024**, y **todas las capas de una misma etapa y orientación se dibujan en el mismo lienzo**, una encima de la otra, sin mover nada de lugar: así calzan al apilarlas.

Hay cuatro **orientaciones**, las mismas de los muebles:

| Orientación | Hacia dónde mira |
|---|---|
| `se` | de frente, hacia abajo a la derecha |
| `so` | de frente, hacia abajo a la izquierda |
| `no` | de espaldas, hacia arriba a la izquierda |
| `ne` | de espaldas, hacia arriba a la derecha |

**De espaldas no hay cara.** La cara sólo lleva `se` y `so`; el cuerpo y los sombreros llevan las cuatro.

### Los nombres de los archivos

Todo vive bajo `criaturas/`. `<especie>` es el nombre interno de la especie, que no siempre se parece al nombre que ve quien juega (`dragoncito` es Tsushimon). Son 25:

| `<especie>` | Nombre en el juego |
|---|---|
| `pollito` | Piollito |
| `brote` | Magora |
| `michi` | Purreon |
| `slime` | Gelatín |
| `pedrusco` | Geo |
| `pulpo` | Octopul |
| `chispa` | Pyro |
| `fantasma` | Duskhouse |
| `chatarra` | Re-bot |
| `dragoncito` | Tsushimon |
| `swampdon` | Swampdón |
| `canizo` | Cañizo |
| `lucierno` | Lucierno |
| `coralito` | Coralito |
| `escorpgon` | Escorpgon |
| `nacar` | Nacar |
| `remolin` | Remolín |
| `prinel` | Prinel |
| `bulb` | Bulb |
| `magnetron` | Magnetrón |
| `criold` | Criold |
| `goot` | Goot |
| `cefiro` | Céfiro |
| `noctule` | Noctule |
| `prismlon` | Prismlon |

| Qué | Archivo | Orientaciones |
|---|---|---|
| El cuerpo | `criaturas/<especie>/<etapa>/cuerpo-<orientación>.png` | `se`, `so`, `no`, `ne` |
| Una cara | `criaturas/<especie>/<etapa>/cara-<ánimo>-<orientación>.png` | `se`, `so` |
| Un sombrero | `criaturas/<especie>/<etapa>/sombrero-<sombrero>-<orientación>.png` | `se`, `so`, `no`, `ne` |

Los nombres que van en lugar de las palabras entre `< >`:

- `<etapa>`: `bebe` (la cría), `nino`, `adolescente`, `adulto` y `adulto_grande`.
- `<ánimo>`: `feliz`, `normal` y `mal`.
- `<sombrero>`: `corona`, `chistera`, `laurel`, `cuernos`, `aureola` y `cinta`.
- `<orientación>`: `se`, `so`, `no` y `ne`.

Ejemplos: `criaturas/pollito/bebe/cuerpo-se.png`, `criaturas/pollito/bebe/cara-feliz-so.png`, `criaturas/pollito/adulto/sombrero-corona-ne.png`.

**Todo se dibuja por especie y por etapa**: cada capa es de una especie en una etapa, y sólo esa etapa la usa. Cada etapa lleva sus **4 cuerpos** (uno por orientación), sus **6 caras** (tres ánimos, de frente: `se` y `so`) y sus **24 sombreros** (seis sombreros, en las cuatro orientaciones): 34 dibujos por etapa y **170 por especie**, que es lo que cuenta su avance.

### El provisional

El provisional de una capa de criatura es **la capa de frente de hoy, ampliada**. Dice **dónde va** la capa en el lienzo y **de qué tamaño**, no cómo se ve de lado ni de espaldas. Sirve de guía de posición, no de modelo del dibujo.

### Qué ves en la página

Las criaturas salen **plegadas por especie**, en una sección «Criaturas»; cada especie se abre aparte y por dentro se divide en sus cinco etapas («Cría», «Niño», «Adolescente», «Adulto» y «Adulto grande»), y cada etapa en las capas «Cuerpo», «Caras» y «Sombreros». Cada especie tiene sus dos botones de descarga, «Descargar lo subido de» la especie y «Descargar los provisionales de» la especie.

El juego de hoy sigue con sus retratos de siempre; nada de esta sección se ve todavía al jugar. Eso sí: el mapa voltea el retrato cuando el gachamon camina hacia la derecha, así que **si un retrato de hoy se dibuja de perfil, mira a la izquierda**.

## Dónde mirar si algo no calza

La lista de los 270 archivos que el juego pinta hoy, con sus tamaños, está en
`web/static/datos/arte.json`. Una prueba (`tests/test_arte.py`) comprueba que
cada uno exista, sea PNG y mida lo que dice, y que no sobre ninguno. Esa lista
**no trae** lo que el juego todavía no pinta (los encendidos, los 24 objetos con
sus íconos y las criaturas): eso sale en la página del dibujante, con sus medidas.
