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

## Los dibujos de ahora (136)

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

Fondo transparente y la figura centrada.

## Lo que llega con el plan 4

Estas familias todavía **no tienen archivos ni medidas**: se fijan cuando llegue
el plan 4 y se sumarán a esta lista. No dibujes nada de esto todavía.

- Íconos de objetos y de cosméticos.
- Muebles.
- Las escenas del interior de cada casa.

## Los gachamones

Los gachamones **no están en este contrato**: siguen con su formato de capas de
`fuentes/` (cuerpos, caras y cosméticos), tal como hasta ahora.

## Dónde mirar si algo no calza

La lista completa y exacta de archivos, con sus tamaños, está en
`web/static/datos/arte.json`. Una prueba (`tests/test_arte.py`) comprueba que
cada archivo exista, sea PNG y mida lo que dice, y que no sobre ninguno.
