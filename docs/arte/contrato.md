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

## Los dibujos de ahora (199)

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

El juego todavía no dibuja `efectos/corazon.png` ni `efectos/estrella.png`: los
corazones de la caricia son un carácter de texto y la estrella no se usa.
Reemplazarlos hoy no cambia nada en pantalla.

### Íconos (`iconos/`)

Son los dibujitos de lo que se compra y se lleva. Se ven **en la tienda y en la
mochila, a 48 píxeles**, así que hay que dibujarlos legibles y simples. Todos
miden **48 × 48**, con **fondo transparente**. Hay uno por cada cosa del juego,
y su nombre es la clave de esa cosa: si el juego suma un objeto nuevo, pedirá
su ícono con el mismo nombre.

| Archivo | Cuántos | Qué es |
|---|---|---|
| `iconos/objetos/<clave>.png` | 33 | Cada objeto: pociones, golosinas, porotos, sopaipillas, placa, silbato, ticket de refugio, semilla. También los que no se venden, porque se ven en la mochila. |
| `iconos/cosmeticos/<clave>.png` | 12 | Cada cosmético del gachamon: sombreros y títulos. |
| `iconos/muebles/<clave>.png` | 14 | Cada mueble de las casas. |
| `iconos/casas/<clave>.png` | 3 | Cada casa que se compra: `pequena`, `mediana`, `grande`. |

Cada ícono ya tiene su relleno en `web/static/arte/iconos/`, con el nombre
exacto de su archivo: dibuja el tuyo y guárdalo encima. Por ejemplo:
`iconos/objetos/fuerza_1d4.png`, `iconos/cosmeticos/corona.png`,
`iconos/muebles/lampara.png`, `iconos/casas/mediana.png`.

El relleno de un ícono es un cuadro de color liso (un color por grupo) con las
primeras letras del nombre, porque a este tamaño no cabe la palabra «RELLENO».

## Lo que llega después

Todavía **no tienen archivos ni medidas** y no hay que dibujarlas: las escenas
del interior de cada casa.

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
