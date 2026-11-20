# Monsteropolis A · Las herramientas del dibujante — diseño

Proyecto A de la hoja de ruta (`2026-11-19-monsteropolis-hoja-de-ruta.md`).
Toca **dos repos**: éste (el juego) y el de la aplicación del sitio donde vive
el juego, que tiene su propia portada, sus cuentas y un tablero de otro
proyecto. Aquí se les dice «el juego» y «el sitio».

## Para qué

El arte del juego son 270 recuadros provisionales descritos en un contrato
(`web/arte.py`: la ruta, el ancho, el alto y la familia de cada pieza). Un
dibujante los va a reemplazar. Hoy reemplazar un dibujo es cambiar un archivo
del repo y desplegar, y eso lo tiene que hacer alguien con acceso al servidor.
El dueño quiere que el dibujante suba sus imágenes él mismo, tener a la vista
qué falta, y que quien visita el sitio encuentre el juego.

## Lo que pidió y decidió el dueño (2026-11-19)

- El pedido, con sus palabras: «añadir monsteropolis como boton en la portada
  […] y un nuevo boton que solo lo vea el dibujante y yo donde pueda subir las
  diferentes imagenes para sustituir los placeholders, y otro tablero como el de
  pokemon cuarzo con kanban gantt y roadmap e historial, pero para las imagenes
  agregadas que tiene que hacer el dibujante».
- Una imagen subida **se ve en el juego al momento**. No hay aprobación previa.
- El botón de Monsteropolis lo ven **todos, también sin cuenta**.
- El tablero lleva **una tarjeta por grupo de piezas**, y la tarjeta avanza
  sola cuando se suben sus imágenes.

- Al aprobar este diseño (2026-11-19) fijó las direcciones: **el juego pasa a
  `/monsteropolis`** y **la página del dibujante va en
  `/monsteropolis_dibujante`**.
- El botón destacado de la portada dice: título «Monsteropolis», renglón «Una
  ciudad virtual donde crías criaturas que viven en tu departamento.» y botón
  «Jugar». En la barra, el enlace dice «Monsteropolis».

Resuelto aquí y dicho al dueño: el permiso es propio y lo da él desde la página
de administración del sitio, como hoy da el del otro tablero; y entran las 270
piezas del contrato, no los retratos de las criaturas.

## Metas

1. El dibujante reemplaza cualquier pieza del contrato desde una página, sin
   que nadie despliegue.
2. El dueño ve qué se reemplazó, quién y cuándo, y puede volver a la imagen
   anterior o al recuadro provisional. Como lo subido se ve al momento, esto no
   es un adorno: es la única red.
3. El tablero dice qué falta, y su avance se pone al día solo.
4. Quien entra al sitio encuentra el juego.

## Lo que no entra

- Los retratos de las criaturas, que tienen su propio generador.
- Aprobar, comentar o devolver una imagen: el dueño eligió que se vea al
  momento.
- Añadir o quitar piezas del contrato desde la página, o cambiarles la medida.
- Editar imágenes en la página.
- Cambiar el nombre dentro del juego (es el proyecto B). Aquí sólo aparece
  «Monsteropolis» en el botón del sitio.

## Lo que no puede pasar

- Que una imagen subida rompa el juego para quien juega: una medida que no es
  la de su pieza, un archivo que no es una imagen, una imagen a medio escribir.
- Que un despliegue borre lo subido.
- Que alguien sin el permiso suba, vea la página o el tablero.
- Que lo subido se pierda sin copia.
- Que el juego escriba en la base del sitio, o que un servicio importe código
  del otro.

## Las tres piezas

### 1 · El botón de Monsteropolis (en el sitio)

Un enlace en la barra de arriba de todas las páginas del sitio, para todos, con
o sin cuenta, y un botón destacado al principio de la portada. Los dos llevan a
la página del juego, que ya sabe pedirle a quien no ha entrado que entre o cree
su cuenta. El texto del botón y de su renglón los aprueba el dueño.

### 2 · La página para subir imágenes (en el juego)

**Dónde.** En el servicio del juego, que es el dueño del contrato del arte, en
la dirección que fijó el dueño: `/monsteropolis_dibujante`, un segundo prefijo
del mismo servicio, con su página y sus rutas. Lo subido se le sirve a quien
juega bajo el prefijo del juego. Se llega por un enlace de la barra del sitio,
que sólo ve quien tiene el permiso.

**La dirección del juego.** El juego pasa de `/gachamon` a `/monsteropolis`.
La dirección vieja sigue contestando y redirige a la nueva conservando el resto
de la ruta, para que no se rompa ningún enlace guardado ni los que el bot dejó
escritos en Discord. El reparto por ruta que manda al servicio del juego lo que
llega bajo su prefijo necesita las dos direcciones nuevas: se cambia al
publicar, con el permiso del dueño.

**Quién.** El permiso es una marca nueva en la tabla de cuentas del sitio, que
el sitio crea y que el dueño pone y quita desde su página de administración.
El juego la **lee**, en una consulta propia que sólo hacen las rutas del arte, y
deja pasar a quien la tiene o es administrador del sitio. A los demás, la
página y sus rutas les contestan lo mismo que a una ruta que no existe. Quién
eres sale sólo de la sesión, como en todo el juego. La lectura de la sesión que
usa el resto del juego **no se toca**: si el juego se despliega antes que el
sitio y la marca todavía no existe, nadie tiene el permiso y el juego sigue
andando igual. Así el orden de los dos despliegues no importa.

**Qué enseña.** Las piezas, por grupos (los mismos del tablero). De cada una: su
imagen de ahora, su nombre, la medida exacta que tiene que tener, si es el
recuadro provisional o una imagen subida, y quién y cuándo la subió. Se puede
filtrar por grupo y por «lo que falta». Cada pieza tiene su botón para subir,
su historial, «volver a la anterior» y «volver al provisional».

**Qué acepta.** Sólo PNG, hasta 4 MB, y de la **medida exacta** del contrato.
Para la familia de la pieza del departamento, cuyos originales van al doble de
lo que sirve la página, se acepta también ese doble y se reduce como lo reduce
hoy `herramientas/pieza.py`. La imagen se abre de verdad para comprobarla y se
vuelve a escribir limpia (sin datos añadidos) antes de guardarla. Lo que no
cumple se rechaza diciendo por qué, con la medida que se esperaba y la que
llegó, y no cambia nada.

**Dónde se guarda.** Fuera de lo que sigue git: en una carpeta propia junto a la
base, que sólo vive en el servidor, como la base. Así un despliegue no la toca.
Cada imagen se guarda bajo un nombre que sale de su contenido, se escribe
entera antes de darla por buena, y una tabla nueva del juego apunta, por pieza,
cuál es la de ahora, quién la subió (su nombre, no su número de cuenta) y
cuándo, y las anteriores. Se conservan las cinco últimas de cada pieza.

**Cómo llega a quien juega.** Hoy el cliente arma él solo la dirección de cada
imagen (`urlDeArte`, en `web/static/js/arte.js`), bajo la versión de los
archivos estáticos, que el navegador y la red de entrega guardan como
inmutables: servir lo subido por esa misma dirección dejaría a la gente viendo
el recuadro viejo. Por eso lo subido tiene dirección propia, con el nombre de su
contenido dentro (se puede guardar para siempre, y una imagen nueva es otra
dirección), y la página del juego, que ya se entrega sin guardar en caché, lleva
dentro un bloque de datos con las piezas que tienen imagen subida y su
dirección. El servidor arma ese bloque en cada petición, leyendo la tabla: no
recuerda nada entre peticiones. `urlDeArte` mira primero ese bloque y, si la
pieza no está, hace lo de siempre; sigue siendo inmediata, y nada de lo que la
llama cambia. Quien tiene la página abierta ve la imagen nueva al recargar.

**La copia.** El dueño puede bajarse todo lo subido en un archivo comprimido
desde la misma página. Pasar lo subido al repo (para que el recuadro
provisional deje de existir) es trabajo aparte y no entra aquí.

**Lo que cambia en el cliente del juego**: ese único punto de `arte.js`. Si una
imagen subida faltara del disco, se ve el recuadro con su nombre, nunca el
dibujo de otra pieza.

**El historial.** Es un registro que sólo crece: cada subida y cada «volver»
deja su renglón con la pieza, qué imagen quedó puesta (o ninguna: el recuadro
provisional), quién lo hizo y cuándo. El provisional es un estado aparte, no
una de las cinco: siempre se puede volver a él. «Volver a la anterior» deja un
renglón nuevo a nombre de quien vuelve. Se guardan en disco las cinco últimas
imágenes distintas de cada pieza; a una más vieja ya no se puede volver.

**Si el contrato cambia después.** La medida se comprueba contra el contrato en
cada subida, y la tabla guarda la medida de lo subido. Si más adelante el
contrato le cambia la medida a una pieza (por ejemplo, porque cambió la forma
de un mueble), lo subido con la medida vieja deja de servirse —vuelve a verse
el recuadro— y la página de subida lo dice. Lo subido para una pieza que ya no
está en el contrato se ignora.

### 3 · El tablero del arte (en el sitio)

El sitio tiene un tablero de un solo proyecto. Se generaliza a **varios
tableros** con el mismo código y la misma página —tarjetas, calendario, hoja de
ruta e historial—: el de antes sigue igual, en su dirección y con sus datos, y
aparece el del arte, con su propia dirección (`/plan/monsteropolis`, elegida
aquí), su propio título, sus propios datos e historial, y el permiso nuevo.

**El modelo.** Los datos de cada tablero van en su propia fila, y su historial
se distingue por tablero. Las listas cerradas que hoy valida el tablero (sus
categorías y sus fases) pasan a ser de cada tablero: el de antes conserva las
suyas tal cual, y el del arte tiene por categorías las familias del arte y
parte con una sola fase, que el dueño divide cuando quiera. La tarea gana un
campo opcional, la clave de su grupo, que es lo que une una tarjeta con su
grupo: no su nombre ni su identificador, que el tablero pone como siempre.

**Las tarjetas.** Una por grupo de piezas. Los grupos los define el juego, a
partir de las rutas del contrato (por ejemplo: cada mueble con sus
orientaciones, cada peinado con sus colores y poses, los iconos de la tienda,
las escenas de los lugares); salen unas treinta. El juego los entrega por una
ruta que sólo contesta a quien tiene el permiso: de cada grupo, su clave, su
nombre, cuántas piezas tiene y cuántas están ya subidas.

**Sembrar.** En el tablero del arte, el dueño tiene una acción que crea las
tarjetas de los grupos que todavía no la tienen (ninguna tarjeta lleva su
clave). Se puede repetir sin duplicar; una tarjeta nace ya en el estado que le
toca por su avance. Renombrar una tarjeta no la desliga; si el dueño la borra,
sembrar la vuelve a crear. La clave de un grupo sale de las rutas del contrato,
no de su nombre, así que ponerle otro nombre a un grupo no cambia nada; si
algún día el juego cambia el corte, las tarjetas del corte viejo quedan sin
avance y se borran a mano.

**El avance.** La página del tablero le pide ese avance al juego desde el
navegador (están en el mismo sitio) y lo enseña en cada tarjeta. Cuando un
grupo pasa de cero, su tarjeta pasa a «en curso»; cuando está completo, a
«hecho». Ese movimiento lo hace la página con una operación corriente del
tablero, a nombre de quien lo está mirando, y queda en el historial. Sólo
avanza: si el dueño vuelve una pieza al provisional, la tarjeta no retrocede
sola. Con dos personas mirando a la vez no se duplica: la operación se hace
sobre la versión que cada página conoce, la que llega tarde se rechaza, y esa
página relee y ve que la tarjeta ya está donde tenía que estar. Una tarjeta
nunca se lleva sola a «pendiente»: con su grupo en cero, el dueño la puede
dejar en «ideas».

**Lo que el dueño decidió de la vuelta atrás (2026-11-20).** La tarjeta sigue a
las piezas: si su grupo está completo y alguien la mueve a mano hacia atrás,
vuelve sola a «hecho». Para reabrir un grupo se devuelve una de sus piezas al
recuadro provisional en la página del dibujante; desde ahí la tarjeta se queda
donde la pongan.

**El contrato del avance.** Lo escribe el juego y lo lee la página del tablero;
lo que no esté aquí no se puede dar por hecho en ninguno de los dos lados.
`GET /monsteropolis_dibujante/api/avance`:

- a quien tiene el permiso: `200` con `{"grupos": [...]}`, un objeto por grupo:
  - `clave`: cumple `^[a-z0-9/_-]{1,64}$`, **sin extensión** (no es la ruta de
    un archivo: `escenas/plaza`, no `escenas/plaza.png`), y **única** en la
    lista. Un grupo con otra forma no recibe tarjeta;
  - `nombre`: texto para quien lo lee; la página lo recorta a 120 letras y, si
    viene vacío, usa la clave;
  - `familia`: una de `avatar`, `pieza`, `iconos`, `pueblo`, `lugares`,
    `escenas` y `efectos`; otra cae en la categoría «Avatar»;
  - `total` y `hechas`: enteros mayores o iguales que cero, con `hechas` como
    mucho `total`;
- a los demás, `404`, como una ruta que no existe;
- `{"grupos": []}` es una respuesta válida; cualquier otra cosa (otro código, una
  página HTML, un JSON sin `grupos`) cuenta como «sin avance»;
- mientras contesta, cada pestaña abierta del tablero lo pide cada pocos
  segundos: se calcula desde la tabla, sin abrir imágenes.

**Lo único que une a los dos servicios**: el enlace de la barra, la marca del
permiso (el sitio la escribe, el juego la lee) y el navegador pidiendo el
avance. Ninguno importa código del otro ni llama al otro desde el servidor. El
juego y el sitio se ven en la misma dirección —lo que llega bajo el prefijo del
juego va a su servicio y lo demás al sitio; ese reparto ya existe y no se
toca—, así que el navegador manda la misma sesión a los dos.

## Decisiones técnicas tomadas aquí

No son del dueño; salieron de revisar el diseño contra el código de los dos
repos: la consulta aparte para el permiso, que hace que el orden de los
despliegues no importe; la dirección propia de lo subido y el bloque de datos
en la página; el historial que sólo crece y el provisional como estado aparte;
qué pasa si el contrato cambia; y el modelo del tablero (una fila por tablero,
listas por tablero, la clave del grupo en la tarea).

## Lo que queda a quien lo construya

Los nombres de las rutas, de la tabla, de la carpeta y de la marca; el corte
exacto de los grupos y sus nombres; cómo se ve la página de subida (es una
herramienta para dos personas: clara antes que bonita); si la reducción de
`herramientas/pieza.py` se reutiliza tal cual o se mueve a un sitio común; y
cómo se parte el trabajo en planes (por lo menos uno por repo).

## Lo que el dueño todavía tiene que ver

- El texto del botón de Monsteropolis y de su renglón en la portada.
- Los grupos y sus nombres, en una página de prueba.
- Publicar: son dos despliegues, el del sitio y el del juego, y cada uno
  necesita su permiso expreso.

## Para publicar

El orden importa: el sitio enseña «Jugar» y «Monsteropolis» a todos los
visitantes, y si sale antes que el juego esos enlaces llevan a una página de
error; y el juego necesita que el túnel ya le mande sus direcciones nuevas.
Cada paso que toca producción necesita el permiso expreso del dueño en ese
momento.

1. **La regla del túnel, antes que nada.** Hoy el túnel sólo manda `/gachamon`
   al servicio del juego. Si el juego nuevo saliera con el túnel viejo,
   `/gachamon` redirigiría a `/monsteropolis` y eso caería en el sitio con un
   error para todos. La regla nueva manda al juego las tres direcciones (por
   ejemplo `^/(gachamon|monsteropolis|monsteropolis_dibujante)(/.*)?$`; con el
   `^` delante no alcanza `/plan/monsteropolis` ni `/api/plan/monsteropolis`, que
   son del sitio). Con el juego de antes todavía en marcha, `/gachamon` sigue
   igual y `/monsteropolis` contesta el «no existe» del juego, que nadie enlaza
   todavía. Se comprueba desde fuera que `/gachamon` sigue andando y que
   `/plan/monsteropolis` sigue siendo del sitio.
2. **Después el juego**, ya contestando en `/monsteropolis/` y en
   `/monsteropolis_dibujante/`. Se comprueba desde fuera que las dos direcciones
   contestan y que `/gachamon` redirige.
3. **Al final el sitio.** Antes de reiniciarlo, una copia de su base en la
   Raspberry, fuera de la carpeta del sitio (su guion de despliegue no la
   respalda, y esta rama le añade una columna y dos tablas al arrancar). Se
   comprueba la copia con la comprobación de integridad de SQLite.
4. **Mirarlo**: el tablero de siempre como estaba, la portada con su botón, y el
   tablero del arte sembrado por el dueño con el avance del juego.
