# El contrato de arte del pueblo

Esto es para ti, que dibujas. No hace falta tocar código.

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

## Los dibujos de ahora (255)

### Pueblo (`pueblo/`)

| Archivo | Tamaño | Qué es |
|---|---|---|
| `pueblo/fondo.png` | 1380 × 860 | El suelo del pueblo: pasto y caminos. **Sin lugares encima**: cada lugar va en su archivo. Es el doble del tamaño del mapa (690 × 430), así que un píxel del mapa son dos del dibujo. |
| `pueblo/lugares/<lugar>.png` | 160 × 160 | La casa o figura de cada lugar. Fondo transparente. Se **apoya en el borde de abajo**: el punto donde el personaje llega es el centro del borde inferior. Sin texto: el nombre lo escribe el mapa. |

Los nueve lugares: `casa`, `refugio`, `incubadora`, `tienda`, `plaza`, `barrio`, `estadio`, `cementerio`, `aventura`.
Por ejemplo: `pueblo/lugares/plaza.png`.

### Escenas (`escenas/`)

| Archivo | Tamaño | Qué es |
|---|---|---|
| `escenas/<lugar>.png` | 720 × 480 | El fondo de la pantalla de cada lugar, uno por cada uno de los nueve de arriba. Por ejemplo `escenas/cementerio.png`. Ocupa todo el cuadro, sin transparencia. |

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
| `iconos/muebles/<clave>.png` | 15 | Cada mueble del departamento que se vende, la cama sencilla incluida. La puerta no lleva ícono: no se vende ni se guarda. |

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

Dejas tus originales en **`fuentes/pieza/`**, con **el mismo nombre y la misma
subcarpeta** que tiene el relleno en `web/static/arte/pieza/` (por ejemplo,
`fuentes/pieza/muebles/cama-se.png`). Después se corre
`./venv/bin/python -m herramientas.pieza`: comprueba que cada original mide
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
`calefactor`, `cama`, `ventanal`, `biblioteca` y `cama_sencilla`. La puerta
(`puerta`) tiene sus dibujos de pieza, pero ningún ícono.

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

## Los gachamones

Los gachamones **no están en este contrato**: siguen con su formato de capas de
`fuentes/` (cuerpos, caras y cosméticos), tal como hasta ahora.

Eso sí: el mapa voltea el retrato cuando el gachamon camina hacia la derecha.
Por eso, **si un gachamon se dibuja de perfil, mira a la izquierda**; si está
de frente, da igual.

## Dónde mirar si algo no calza

La lista completa y exacta de archivos, con sus tamaños, está en
`web/static/datos/arte.json`. Una prueba (`tests/test_arte.py`) comprueba que
cada archivo exista, sea PNG y mida lo que dice, y que no sobre ninguno.
