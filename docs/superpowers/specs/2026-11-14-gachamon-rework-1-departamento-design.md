# Gachamon, el rework — Proyecto 1: las reglas nuevas y tu departamento por casillas

Diseño acordado con Felipe el 2026-11-14. Describe **qué** se construye y **por
qué**; los planes de tareas se escriben después, a partir de este documento.

Lo que decidió Felipe va marcado **[Felipe]**. Lo que elegí yo para cerrar un
hueco va marcado **[propuesta]**: lo primero no se cambia sin preguntarle; lo
segundo se puede discutir.

## 1. Qué es esto y por qué

Felipe encuentra el sistema de casas de hoy «muy aburrido y simplista»: una
casa es un número de huecos y una lista, y no hay nada que hacer con ella. Lo
que quiere hacer en su casa es **redecorarla, ver a sus gachamones y jugar con
los objetos, al estilo de Habbo Hotel** **[Felipe]**.

Eso cambia el juego entero, y es más de un proyecto. El orden acordado
**[Felipe]**:

1. **Las reglas nuevas y tu departamento por casillas, jugando solo** — este
   documento.
2. **El balcón y el huerto.**
3. **El pueblo y los lugares en vista isométrica**, con el edificio de
   viviendas en vez de «Tu casa» y «Barrio».
4. **Gente en vivo**: ver a otros caminar, hablar con globos de texto, visitar
   departamentos.
5. **Los objetos para jugar y el intercambio**: la mesa de gato, el atril, los
   teletransportadores, intercambiar objetos y dinero.
6. **Lo que hoy sólo está en Discord** (competir, las aventuras, reclutar,
   conversar) y, con eso, **apagar el bot**: al final se juega sólo en la
   página **[Felipe]**.

El 2026-11-15 Felipe decidió además **pausar el juego en Discord desde el día
del cambio de este proyecto** **[Felipe]**: el bot queda sólo para vincular
(sección 7). Así que entre este proyecto y el 6 no hay competir, aventuras
(salvo la primera), reclutar ni conversar en ningún sitio. Por eso el
2026-11-16 Felipe decidió **adelantar las aventuras y reclutar**: van a la
página justo después de este proyecto, antes del balcón **[Felipe]**. Competir
y conversar siguen en el proyecto 6.

Cada proyecto tendrá su propio diseño. La sección 12 guarda lo que Felipe ya
dijo de los proyectos 2 a 6, para que no se pierda.

El plan anterior de «tu casa» (la casa por dentro con varias casas, huecos y
mudanza al refugio) quedó terminado en la rama local `web/6-tu-casa` y **no se
publica** **[Felipe]**: sirve de cantera (sección 10). El plan del huerto y el
buzón que le seguía no se hace.

## 2. Metas, lo que no entra y lo que sería un fracaso

**Metas de este proyecto**

- Una sola vivienda por persona: un departamento por casillas que se amplía.
- Decorarlo tocando: poner, mover, girar y guardar muebles.
- Ver ahí a todos tus gachamones, cuidarlos de a uno o a todos de una vez.
- Las reglas nuevas: todos decaen, ninguno muere, no hay refugio ni
  incubadora, y el límite de gachamones son las camas.
- Los muebles que los gachamones usan solos (refrigerador, consola, ducha,
  pesas).
- Que el día del cambio nadie pierda nada.
- Partir sin gachamon: el primero se gana en una primera aventura.

**No entra** (es de otro proyecto): el balcón y el huerto; el pueblo y los
demás lugares en isométrico; el edificio de viviendas y visitar; ver a otras
personas; el chat; la mesa de gato, el atril y los teletransportadores; el
intercambio; pasar a la web lo que hoy sólo está en Discord. Tampoco el arte
definitivo: todo lo nuevo sale con dibujos de relleno.

**Sería un fracaso, aunque funcione**

- Que decorar tenga pasos de más: se toca el mueble y ahí salen sus opciones
  **[Felipe]**. Al principio esta línea decía también «modos»: Felipe probó un
  boceto con un modo «Decorar» y lo encontró complicado **[Felipe]**.
  **[Felipe, 2026-11-16]** Después decidió añadir un **modo construcción** para
  mover muebles, puertas y ventanas: así, fuera de él, un toque sobre un mueble
  hace su acción y no hay choques como el de la puerta, que al tocarla se podía
  mover o salir. Está en la sección 5.1. Dentro del modo sigue valiendo lo de
  siempre: tocar el mueble y elegir **[propuesta, aceptada]**.
- Que haya un tope de camas o de gachamones que no salga de las casillas: «la
  limitación va por las casillas solamente» **[Felipe]**.
- Que alguien pierda gachamones, muebles o monedas con el cambio.
- Que descuidar a un gachamon tenga castigo: en cero se queda en cero, y sólo
  hay que volver a subirlo **[Felipe]**.

## 3. Las reglas nuevas de los gachamones

- **Todos viven en tu departamento y a todos les pasa el tiempo**: les bajan
  la comida, el ánimo y el aseo, al ritmo de hoy **[Felipe]**. Desaparece la
  regla de que sólo la activa avanza.
- **No mueren** **[Felipe]**. La comida llega a 0 y ahí se queda. No hay
  instante de muerte, ni aviso de hambre, ni anuncio. Un gachamon en 0 de
  comida se sigue viendo «desfallecido», como hoy el de quien juega sólo en la
  web **[propuesta]**. Lo que hoy pide un mínimo de comida (salir de aventura)
  lo sigue pidiendo **[propuesta]**: no es un castigo nuevo.
- **Los que ya murieron se quedan en el cementerio**; nadie revive
  **[propuesta, aceptada]**.
- **El activo es el que sale contigo** **[Felipe]**: el que camina por el
  pueblo, compite, va de aventura y conversa. Se elige en tu departamento,
  tocándolo («Salir con él») **[propuesta, aceptada]**. Cambiar de activo ya no
  duerme ni despierta a nadie.
- **Cuidar**: cada cuidado le cae al gachamon que elijas. Cada uno conserva
  sus tiempos de espera, y el tope diario de monedas sigue siendo uno solo por
  persona **[propuesta, aceptada]**.
- **«A todos»** **[Felipe]**: alimentar a todos, jugar con todos, entrenar con
  todos, bañar a todos. Un toque le hace ese cuidado a cada gachamon que pueda
  recibirlo (al que le serviría y no está esperando) y dice a cuántos les tocó
  **[propuesta]**.
- **El límite de gachamones son las camas** **[Felipe]**: cada gachamon
  necesita una cama puesta, y **la primera cama es la tuya** **[Felipe]**: hacen
  falta siempre tantas camas puestas como gachamones más una. Al reclutar, el
  salvaje sólo acepta si tienes una cama libre **[Felipe]**. Una cama no se
  puede guardar si deja a alguien, o a ti, sin la suya **[propuesta]**.
- **Se parte sin gachamon y sin huevo** **[Felipe]**. El departamento nace con
  tu cama puesta y **una segunda cama sencilla guardada**, y quien empieza tiene
  **0 monedas y 0 gemas** **[Felipe]**. Eso vale sólo para quien empieza después
  del día del cambio: **quien ya jugaba, también quien viene de Discord,
  conserva sus monedas y sus gemas** **[Felipe, 2026-11-15]**.
- **El primero se gana en la primera aventura** **[Felipe]**: es fija, vas tú
  solo con tu avatar, encuentras a un gachamon básico **sorteado entre los
  comunes** y se une siempre; hay diálogo, pero sin opciones. Se abre cuando ya
  pusiste la segunda cama: el juego lo pide como primer paso **[propuesta,
  aceptada]**. Después, las aventuras son las de siempre, con tu activo.
  **[Felipe, 2026-11-17]** El primero se sortea entre **las diez que salían del
  huevo, con sus pesos**: casi siempre una común, y rara vez una poco común o
  una rara. El detalle, en la sección 8.1.
- **El nombre de un recluta se pone al reclutarlo. Si no se lo pones, se pone
  uno él solo** **[Felipe]**. El nombre sale de una lista del juego, nunca es
  el de su especie ni uno que ya tengas, y se le puede cambiar una vez desde su
  ficha **[propuesta]**. Los reclutas que hoy esperan nombre se lo ponen solos
  el día del cambio **[propuesta]**.
- **El plantel ya no tiene un tope propio** **[propuesta]**: el de 25 existía
  sólo porque los menús de Discord no muestran más, y el juego de Discord se
  pausa el día del cambio (sección 7). Desde ese día el único límite son las
  camas, es decir, las casillas **[Felipe]**.

## 4. El departamento

### 4.1 Tamaño y ampliación

- Todos viven en el mismo edificio y cada persona tiene **un solo
  departamento** **[Felipe]**. Ya no se compran casas.
- Parte en **3 × 3 casillas** **[Felipe]**.
- Se amplía comprando **una fila o una columna** de casillas, y cuesta según
  las casillas que suma **[Felipe]**: **15 monedas por casilla** **[propuesta,
  aceptada]**. La fila o la columna nueva se añade por los bordes de delante,
  así que nada de lo ya puesto cambia de sitio **[propuesta]**.
- Tamaño máximo: **8 × 8** **[propuesta, aceptada]**. De 3 × 3 a 8 × 8 son 825
  monedas.

### 4.2 Los muebles

- **Ocupan casillas enteras**: una cama usa 2, una silla 1 **[Felipe]**. No
  hay límite de objetos: el límite es lo que cabe **[Felipe]**.
- **Los cuadros, las ventanas y las cortinas van en la pared** y no ocupan
  suelo **[propuesta, aceptada]**.
- **Se puede tener más de uno de cada mueble** **[propuesta, aceptada]** (hoy
  sólo uno).
- **Giran en 4 posiciones** **[Felipe]**. Cada mueble tiene **cuatro
  imágenes**, una por posición, mirando al NE, al NO, al SE y al SO; **nada se
  espeja**, porque un objeto como una planta no tiene por qué ser simétrico
  **[Felipe, 2026-11-16]** (antes este documento decía dos imágenes, cada una
  usada también espejada). Vale igual para los de 1 × 1. Un mueble alargado
  cambia las casillas que ocupa al girar. Lo que va en la pared lleva dos
  imágenes, una por pared **[Felipe, 2026-11-16]**.
- **El arte de la pieza no es pixel art**, y la casilla mide **1024 × 512
  píxeles**: así lo acordó Felipe con el dibujante **[Felipe, 2026-11-16]**.
  Los originales van en el repo, en `fuentes/`, y la página sirve copias
  reducidas que saca una herramienta del repo **[Felipe, 2026-11-16]**.
- **Tener un mueble no es tenerlo puesto**: los que no están puestos están
  «guardados». Guardar nunca destruye.
- **Lo que se puede pisar (el felpudo, la alfombra) es una capa del suelo**
  **[propuesta]**, como en Habbo: se camina encima y admite un mueble encima,
  pero no otro objeto que se pise. Los gachamones y tu avatar se paran en
  cualquier casilla sin mueble, también sobre una alfombra; el servidor no
  reserva suelo libre para ellos.
- Lo que se compra en la Tienda llega a guardados **[propuesta]**.

Casillas de cada mueble **[propuesta]**. Los catorce de hoy conservan su precio
y su comodidad **[propuesta, aceptada]**:

| Mueble | Dónde va | Precio | Comodidad |
|---|---|---|---|
| Felpudo | 1 casilla (se puede pisar) | 30 | 2 |
| Maceta | 1 casilla | 50 | 3 |
| Cuadro | pared, 1 tramo | 50 | 3 |
| Estantería | 2 casillas | 80 | 4 |
| Lámpara | 1 casilla | 80 | 4 |
| Alfombra | 2 × 2 casillas (se puede pisar) | 120 | 5 |
| Cortinas | pared, 2 tramos | 120 | 5 |
| Cojines | 1 casilla | 180 | 6 |
| Fuente | 2 × 2 casillas | 180 | 6 |
| Chimenea | 2 casillas | 180 | 6 |
| Calefactor | 1 casilla | 280 | 7 |
| Cama grande | 2 casillas; cuenta como cama | 280 | 7 |
| Ventanal | pared, 2 tramos | 280 | 7 |
| Biblioteca | 2 casillas | 280 | 7 |
| **Cama sencilla** (nueva) | 2 casillas; cuenta como cama | **85** **[Felipe]** | 2 |

Felipe pidió que el segundo gachamon tarde **una semana jugando todos los
días** **[Felipe]**. Hoy se ganan hasta 12 monedas por día cuidando y 20 con
todo. El primero no cuesta nada (su cama viene de regalo); el segundo pide una
tercera cama, que cabe en el 3 × 3, así que lo que tarda una semana es esa
cama: de ahí los 85.

### 4.3 La comodidad

- Sigue frenando la caída del ánimo, ahora de **todos** los que viven ahí
  **[propuesta, aceptada]**.
- **Cada tipo de mueble puesto suma su comodidad una vez** **[Felipe]**: diez
  felpudos suman lo que uno.
- **El tope depende de las casillas del departamento** **[Felipe]**. La cuenta
  **[propuesta]**: se parte de 80; el tope es 100 con 9 casillas y sube parejo
  hasta 150 con 64 (`100 + (casillas − 9) × 50 // 55`).
- Nunca se enseña con `%`.

### 4.4 Los muebles que los gachamones usan solos

Idea de Felipe: «si compras un refrigerador o similar los gachamones podrán
tomar comida de ahí y recuperarán cierta cantidad de hambre, lo mismo para el
ánimo con una consola de videojuegos, y una ducha para la higiene, podrán
entrenar solos si les compras pesas» **[Felipe]**.

Cómo queda **[propuesta, aceptada, salvo lo que se marca]**:

| Mueble | Casillas | Precio | Con él puesto |
|---|---|---|---|
| Refrigerador | 1 | 300 | la comida de quienes viven ahí no baja de 40 |
| Consola | 1 | 300 | el ánimo no baja de 40 |
| Ducha | 1 | 300 | el aseo no baja de 40 |
| Pesas | 1 | 300 | cada gachamon gana 1 punto de entrenamiento de fuerza por día |

- **El mínimo es 40** **[Felipe, 2026-11-18]** (este documento decía 30): por
  debajo de 40 el gachamon pide lo que le falta, y con 30 pediría siempre lo
  que el mueble le sostiene.
- **«No baja de 40» vale siempre**, también contra lo que gastan los cuidados:
  con el mueble puesto, un cuidado que dejaría la barra por debajo la deja en
  40 **[Felipe, 2026-11-18]**. Y si al ponerlo la barra ya está por debajo,
  sube a 40.
- **Las pesas dan 1 punto por día** y gachamon **[Felipe, 2026-11-18]**. Llega
  al pasar la medianoche UTC, el mismo día de los topes diarios; guardarlas y
  volver a ponerlas no da puntos de más **[propuesta, aceptada]**.
- No hay que llenarlos ni cuestan por uso. Tener dos no hace más.
- No dan experiencia ni monedas: eso sólo lo da cuidar uno mismo.
- **Quitan crecimiento, y se acepta** **[Felipe, 2026-11-18]**: cuidar a un
  gachamon que está muy mal lo hace crecer más, y con la ducha y el
  refrigerador ya no llega a estarlo. Es el precio de la comodidad; no hay
  regla que lo compense. Simulando un mes, a quien entra unas tres veces al día
  el refrigerador le deja cerca de la mitad de los saltos de estadística por
  cuidar; con ese dato delante, Felipe eligió dejarlo como está y no avisarlo
  en la Tienda **[Felipe, 2026-11-19]**.
- Suman 3 de comodidad cada uno, como cualquier mueble.
- **Lo que hacen se dice en una línea de la Tienda**, bajo el nombre de cada
  uno, y en ningún otro sitio por ahora **[Felipe, 2026-11-18]**.
- En pantalla se ve a los gachamones acercarse a ellos de vez en cuando: uno
  que está quieto camina hasta su lado y se queda unos segundos
  **[propuesta, aceptada]**. Es adorno; la regla la lleva el servidor.

### 4.5 La puerta

Felipe la pidió el 2026-11-16, al probar la pantalla: «falta la puerta de
entrada, que va adjunta a la pared al igual que las ventanas y los cuadros, y
debe ser movible pero no guardable en el inventario, y la puerta es una casilla
más fuera del departamento que es donde apareces al entrar en el departamento,
al igual que en Habbo».

- **Cada departamento tiene una puerta, y sólo una** **[Felipe, 2026-11-16]**.
  Va en la pared, en un tramo, como un cuadro; se puede **mover** a otro tramo
  libre de cualquiera de las dos paredes, y **no se guarda**.
- **Es una casilla más, fuera de la pieza** **[Felipe, 2026-11-16]**: la del
  tramo donde está. Ahí apareces al entrar al departamento, y desde ahí caminas
  hacia adentro por la casilla que queda enfrente.
- **La casilla de enfrente se puede tapar con un mueble**, como en Habbo
  **[Felipe, 2026-11-16]**: entonces apareces en la puerta y no pasas hasta
  mover el mueble, cosa que puedes hacer desde ahí, entrando al modo
  construcción. (Sin camino, tu avatar no va: sección 5.) Lo que no se ofrece
  es llevar la propia puerta a un tramo con la entrada tapada: al moverla sólo
  se marcan los que la tienen libre **[Felipe, 2026-11-16]**.
- **La casilla de la puerta sólo la pisas tú** **[Felipe, 2026-11-16]**: los
  gachamones no pasean hasta ella ni se les puede llevar.
- **Por la puerta también se sale al pueblo** **[Felipe, 2026-11-16]**, además
  del botón «Pueblo». **Tocarla, en modo normal, te saca directo**: caminas
  hasta ella y, al llegar, sales; si mientras caminas tocas otra cosa, no
  sales; si ya estás en ella, sales al momento **[Felipe, 2026-11-16]**. (Al
  principio se salía desde su menú, que traía «Mover» y «Salir»; con el modo
  construcción —sección 5.1— el menú es sólo de ese modo y trae «Mover».) Si
  no hay camino hasta la puerta, no se sale y se dice **[propuesta, aceptada]**.
- **Nace con el departamento** **[propuesta, aceptada]**: en la pared izquierda, en el
  tramo de más adelante; el día del cambio, el alcalde la deja en el primer
  tramo cuya casilla de enfrente esté libre de lo que él mismo puso. Si con sus
  camas puestas no queda ninguno, corre la cama que tapa la entrada a un sitio
  de cama que le sobre **[propuesta]**. No se vende
  en la Tienda, no aparece en «Guardados» y no suma comodidad.
- **Su dibujo** sigue las reglas de lo de pared (dos imágenes, una por pared):
  es el vano visto desde dentro, y tu avatar se pinta de pie en su umbral.

## 5. La pantalla de tu departamento

Felipe aprobó dos bocetos, guardados junto a este documento en
`2026-11-14-bocetos/`: `departamento-casillas.html` (cómo se ve la pieza) y
`departamento-pantalla.html` (la pantalla entera, para tocar). Los dos son
cajas de colores: valen por lo que muestran, no por cómo están hechos.

- **La pieza arriba, en vista isométrica**, como Habbo **[Felipe]**: el suelo
  por casillas, las dos paredes del fondo, los muebles, tus gachamones y tu
  avatar.
- **Te mueves casilla a casilla tocando el suelo** **[propuesta, aceptada]**:
  el avatar camina hasta ahí rodeando los muebles.
- **Tocas un mueble y encima salen sus opciones: Mover, Girar, Guardar**
  **[Felipe]**. Con «Mover» se marcan las casillas libres y tocas dónde lo
  quieres. Desde el 2026-11-16, **dentro del modo construcción** (sección 5.1).
- **«Guardados»** abre lo que tienes sin poner: tocas uno y después una
  casilla **[propuesta, aceptada]**. Desde el 2026-11-16 no es un botón: la
  bandeja está abierta mientras dura el modo construcción (sección 5.1).
- **Tocas a un gachamon** y su ficha queda abajo: sus barras, sus cuidados y
  «Salir con él». También tiene «Mover», para apartarlo **[Felipe]**.
- **Los gachamones caminan solos** por la pieza **[Felipe]**. Mientras mueves
  o colocas un mueble se quedan quietos, y si lo sueltas donde hay uno, se
  corre a la casilla libre más cercana **[propuesta]**. Dónde está parado cada
  uno no se guarda: sólo se guarda dónde están los muebles **[propuesta,
  aceptada]**.
- **«A todos»**: los cuatro botones, bajo la ficha.
- **«Ampliar»**: muestra cuánto cuesta sumar una fila y cuánto una columna.
  **Antes de cobrar pregunta, como la Tienda** («¿Ampliar por 45 monedas?»,
  con «Ampliar» y «No») **[Felipe, 2026-11-16]**. Está dentro del modo
  construcción (sección 5.1).
- Bajo la pieza, una línea con el tamaño, las casillas ocupadas, las camas y
  los gachamones, y **también la comodidad** **[Felipe, 2026-11-16]**.
- **En el computador, la pieza a la izquierda** y, a la derecha, la ficha, «A
  todos» y los botones; los guardados quedan bajo la pieza **[Felipe,
  2026-11-16]**.
- **Al poner, mover o guardar bien no sale texto**; sólo cuando algo no se
  puede **[Felipe, 2026-11-16]**. Al elegir algo para poner o mover, la
  indicación «Toca la casilla donde lo quieres.» se queda mientras lo lleves en
  la mano **[propuesta]**. Tocar fuera de lo marcado lo suelta y cierra el
  menú; lo que no cabe en ningún sitio no entra en la mano («Ahí no cabe.») y
  todo queda como estaba **[propuesta]**.
- **Se toca lo que se ve, con los gachamones primero** **[propuesta]**: a un
  gachamon siempre se le puede tocar, también con un mueble delante; después,
  los muebles por la silueta de su caja; después la pared; después el suelo.
  Con los modos (sección 5.1): en el normal sólo recibe el toque lo que tiene
  acción, y en el de construcción a los gachamones no se les toca.
  **Quién tapa a quién** se calcula de verdad, por las cajas que cada cosa
  ocupa en el suelo, y no con la cuenta rápida del boceto, que dibujaba a un
  gachamon debajo de la cama que tiene al lado **[propuesta]**.
- **El tope de 12 cuidados pagados al día se queda** **[Felipe,
  2026-11-16]**.
- **Si no hay camino hasta la casilla tocada, no se va**: tu avatar se queda
  donde está, y al mover a un gachamon sólo se marcan las casillas a las que
  tiene camino **[Felipe, 2026-11-16]**. Al llegar un departamento nuevo, quien
  quedó sobre un mueble o fuera de la pieza aparece en la casilla libre más
  cercana; si no queda ninguna casilla que se pueda pisar, no se dibuja a nadie
  y se les sigue eligiendo desde la lista **[propuesta]**.
- Del que eliges queda abajo su ficha completa **[Felipe, 2026-11-16]**, y el
  globo de lo que dice sale sólo sobre el que sale contigo **[propuesta]**.
- Vale en el teléfono y en el computador, con el corte de 900 px de hoy.
- **Todo lo que se hace tocando el dibujo se puede hacer también sin él**
  (teclado y lector de pantalla): una lista de lo puesto y de lo guardado con
  los mismos botones **[propuesta]**. La lista de muebles sigue al modo
  (sección 5.1).

### 5.1 El modo construcción

Felipe lo pidió el 2026-11-16, con la puerta recién puesta en pantalla: «se me
acaba de ocurrir, añadir un modo construccion para mover muebles y puertas y
ventanas, de esa forma en el modo normal solo podras usar la accion de ese
mueble, y no habran choques como con la puerta que al hacerle click podria
moverse o salir del departamento».

- **Dos modos: el normal y el de construcción** **[Felipe, 2026-11-16]**.
  Siempre se entra en el normal, y el modo no se recuerda: es cosa de la
  pantalla, no se guarda ni se manda al servidor **[propuesta, aceptada]**.
- **El botón se llama «🔨 Construir» y, dentro del modo, «✔ Listo»**
  **[Felipe, 2026-11-16]**. Va bajo la pieza; mientras dura el modo, a su lado
  se lee «Modo construcción» y la pieza se enmarca **[propuesta, aceptada]**.
- **En modo normal, un toque sobre un mueble hace su acción**
  **[Felipe, 2026-11-16]**. Hoy la única es la de la puerta: te saca (sección
  4.5). **Un mueble sin acción propia no hace nada**: no se elige; si se pisa
  (una alfombra), caminas hasta ahí; y no le quita el toque a lo que tiene
  acción aunque esté delante **[Felipe, 2026-11-16]**. A los gachamones se les
  toca como siempre, con su menú («Mover» y «Acariciar»).
- **En el modo construcción se tocan los muebles, la puerta y lo de pared**: de
  cada uno salen «Mover», «Girar» (no lo de pared) y «Guardar» (no la puerta)
  **[Felipe, 2026-11-16]**. **A los gachamones no se les toca**: el toque pasa
  al mueble que tengan detrás; siguen paseando, y si pones un mueble donde hay
  uno, se corre solo **[Felipe, 2026-11-16]**.
- **Tocar el suelo es caminar en los dos modos** **[propuesta, aceptada]**.
- **«Guardados» y «Ampliar» están sólo dentro del modo**
  **[Felipe, 2026-11-16]**: la bandeja, abierta bajo la pieza mientras dura; y
  «Ampliar», a su lado **[propuesta, aceptada]**. Fuera del modo la pantalla
  queda para vivir: cuidar, caminar, salir.
- **«Listo» deja todo recogido**: suelta lo que lleves en la mano y cierra el
  menú y lo de ampliar, sin cobrar nada. Con una petición en camino no se
  cambia de modo **[propuesta, aceptada]**.
- **Sin el dibujo** (teclado y lector de pantalla): en modo normal la lista
  trae tus gachamones; en el de construcción, además, los muebles puestos y los
  guardados con sus botones. Para salir sin el dibujo está «Pueblo»
  **[propuesta, aceptada]**.
- Los cuidados, «A todos», «Mochila» y «Pueblo» siguen en los dos modos
  **[propuesta, aceptada]**.
- **Lo que se lee**: al entrar al modo, «Toca un mueble para moverlo, girarlo o
  guardarlo.»; y al terminar, sólo para el lector de pantalla, «Modo
  construcción terminado.» **[propuesta, aceptada]**.
- **La carta del alcalde nombra el botón** **[Felipe, 2026-11-16]**: donde
  habla de los muebles guardados, dice «entra a «Construir» y ponlos donde
  quieras» (sección 6).

## 6. El día del cambio

Felipe: los que juegan hoy «conservan sus gachamones y el alcalde les regala
camas» **[Felipe]**. Lo acordado **[propuesta, aceptada]**, y cómo lo completo
**[propuesta]**:

- A cada persona se le crea su departamento de 3 × 3.
- **El alcalde regala camas sencillas hasta que tengas una por cada gachamon
  vivo más la tuya, y las deja puestas**, y **agranda gratis** el departamento
  de quien no le quepan: el primer tamaño de la serie 3 × 3, 4 × 3, 4 × 4,
  5 × 4… con al menos `2 × camas + 5` casillas, hasta 8 × 8. A quien no le
  quede ningún gachamon le deja lo que a quien empieza: su cama puesta, otra
  guardada y la primera aventura por hacer. Las monedas y las gemas que cada
  uno tenía no se tocan; las medallas ganadas y sin cobrar se pagan ese día
  (sección 8.1).
- **Las casas compradas se devuelven enteras en monedas** (lo que cuesta cada
  una en el catálogo), y **cada casa mediana o grande devuelve 140 monedas más**
  (pequeña 200, mediana 640, grande 1340) **[Felipe, 2026-11-16]**. Es una
  devolución: no pasa por el tope diario, y se paga
  una sola vez por persona.
- **Los muebles quedan guardados.**
- **Lo plantado en el huerto se cosecha solo**, como si estuviera maduro, y va
  a la mochila. El huerto queda cerrado hasta el proyecto 2. Las semillas dejan
  de venderse y de salir como botín hasta entonces; las que ya tienes se quedan
  **[propuesta]**.
- Un gachamon al que ya le había llegado la hora de morir y el bot todavía no
  lo había registrado sigue vivo, con la comida en 0.
- **Cada ticket del refugio se devuelve en sus 40 monedas** y deja de venderse
  y de salir como botín.
- A los gachamones que estaban en la incubadora el tiempo les empieza a correr
  ese día: no se les viene encima lo que durmieron.
- El logro «Superviviente» pasa a ser sólo «100 aventuras».
- Cada persona ve **una vez** una carta del alcalde que cuenta qué le tocó, en
  la página, la primera vez que entra después del cambio, antes que nada, y se
  cierra con «Entendido» **[propuesta]**. La carta le dice también cómo se
  llama ahora cada recluta suyo que estaba sin nombre, con la especie con su
  mayúscula, y dice «por tu ticket» cuando era uno **[Felipe, 2026-11-16]**.
- **Los regalos que esperaban en el buzón se entregan solos** a la mochila de
  cada quien **[propuesta]**: el buzón era de Discord, y el juego de Discord se
  pausa ese día.
- El cambio corre una sola vez al arrancar, es seguro repetirlo y se hace con
  una copia de la base tomada antes.

## 7. Discord, en pausa

Lo acordado el 2026-11-14 era mantener el bot jugable entre este proyecto y el
6, con las reglas nuevas. El 2026-11-15 Felipe lo cambió: **pausar el bot para
facilitar la migración** **[Felipe]**. Hoy juegan dos personas en Discord, y
mantener dos juegos con reglas distintas era buena parte del trabajo y el mayor
riesgo del día del cambio.

- **Desde el día del cambio el juego en Discord se apaga** **[Felipe]**:
  cuidar, competir, las aventuras, reclutar, conversar, la tienda, la mochila,
  las casas, el huerto, los logros, el jardín, el ranking y el cementerio.
- **El bot sigue encendido sólo para `/vincular`** **[Felipe]**: es la única
  forma de que quien jugaba en Discord lleve sus gachamones a la página, y casi
  nadie la ha usado todavía.
- **Todo lo demás contesta que el juego se mudó**, con el enlace y cómo vincular
  **[propuesta]**: los botones y menús de los mensajes viejos, mencionar al bot,
  y los comandos que la gente escribe de memoria (`/mascota` y `/huevo`). Los
  demás comandos desaparecen.
- **El manual del canal queda en una sola página** **[propuesta]**: el juego se
  mudó, dónde está y cómo vincular.
- **Nadie pierde nada**: gachamones, monedas, gemas, objetos y logros siguen en
  la base y aparecen en la página al vincular. Lo que sólo se podía hacer en
  Discord (competir, las aventuras salvo la primera, reclutar, conversar) no se
  puede hacer en ningún sitio hasta el proyecto 6.
- **La Tienda de la página deja de vender lo que sólo servía en Discord**
  hasta que su uso exista en la página; lo que ya tengas se queda en tu mochila
  **[propuesta]**.
- **«Entrenar juntos» desaparece** con el juego de Discord: en la página lo
  reemplaza «entrenar con todos» **[propuesta]**.
- **En el código**, el juego de Discord (los comandos, las fichas, los menús,
  el arte de texto) se retira de la rama del rediseño **[propuesta]**: sigue en
  producción hasta el día del cambio y en el historial después. Las reglas que
  el proyecto 6 llevará a la página (las aventuras, competir, conversar) se
  quedan, con sus pruebas.
- **La web es de un solo servidor de Discord, Robot House** (decisión de
  Felipe en la parte A: un solo mundo). Si el bot está en otro servidor, ahí el
  juego también se pausa y no hay página adonde ir: lo de esas personas queda
  guardado **[propuesta]**.

## 8. El pueblo y las demás pantallas de la web

- El mapa sigue como hoy hasta el proyecto 3, pero **pierde el Refugio y la
  Incubadora**, y «Tu casa» pasa a llamarse **«Tu departamento»**
  **[propuesta, aceptada]**. Quien entra por primera vez parte ahí.
- La pantalla de la Incubadora y lo del Refugio desaparecen. Lo que hacían se
  hace en el departamento.
- **La entrada cambia**: ya no es avatar → huevo → nombre, sino avatar → tu
  departamento (poner la segunda cama) → la primera aventura → el nombre. El
  lugar «Aventura» del mapa abre sólo esa primera aventura; las demás siguen
  siendo del proyecto 6.
- **Todo tiene que funcionar sin ningún gachamon**: el estado, el pueblo, cada
  lugar y el departamento se ven y se usan sin activo.
- **La Tienda** deja de vender casas; los muebles se venden de a varios. Las
  ampliaciones se compran en el departamento **[propuesta]**.
- **La ficha, el ropero y la mochila** se abren para el gachamon que tengas
  elegido en el departamento; fuera de él, para el activo **[propuesta]**.
  Lo que se decidió después, al construir la pantalla **[Felipe, 2026-11-16]**:
  del gachamon que tocas en el departamento se abre sólo su **ficha completa**
  y sus cuidados; **el ropero y la mochila siguen siendo del que sale contigo**
  (para vestir a otro o darle un objeto, primero «Salir con él»).
- **Lo que la mochila ya no deja usar**: las pociones de fuerza y de velocidad
  y las sopaipillas, que sólo sirven en las competencias, no se usan ni se
  gastan desde ella y dicen lo mismo que la Tienda; la poción de descanso
  rápido, que sólo sirve para volver a competir, también **[propuesta,
  aceptada]**. La semilla, su nota en la mochila y los porotos dicen que el
  huerto vuelve más adelante **[Felipe, 2026-11-16]**.
- El cuidado de aseo se llama **«Bañar»** en todas partes **[Felipe,
  2026-11-16]**.

### 8.1 Partir sin gachamon y la primera aventura

Lo que faltaba decidir de la sección 3 y de «La entrada cambia», cerrado con
Felipe el 2026-11-17 al escribir su plan.

- **Quién hace la primera aventura**: cualquiera que no tenga ningún gachamon
  vivo. Quien empieza; quien tenía una cuenta con avatar y el huevo sin romper;
  y quien se quedó sin ninguno antes del día del cambio. Estos dos últimos
  conservan sus monedas y sus gemas **[propuesta, aceptada]**.
- **Quién «empieza»**: aquel cuyo monedero nace después del día del cambio (el
  cambio le deja monedero a todo el que ya estaba). Nace en 0 monedas y 0 gemas
  **[propuesta, aceptada]**; lo de partir en cero es de la sección 3
  **[Felipe]**.
- **El primero se sortea entre las diez del huevo, con sus pesos**
  **[Felipe, 2026-11-17]**. Necesita cama, como todos: ya no hay ningún
  gachamon que no la pida **[propuesta, aceptada]**.
- **La guía es el paso que toca, bajo la pieza** **[Felipe, 2026-11-17]**:
  mientras no tengas gachamon, en tu departamento se lee siempre el paso
  siguiente: «Pon tu segunda cama: entra a «Construir», tócala en los guardados
  y después toca una casilla.» y, con la cama puesta, «Ya hay cama para un
  gachamon. Sal al pueblo y ve a «Aventura».» **[propuesta, aceptada]**.
- **La aventura ocurre en el lugar «Aventura»**, con un diálogo fijo de a una
  frase («Sales del pueblo por el sendero. Hoy vas tú solo.» · «Entre los
  matorrales, algo se mueve.» · «No huye. Se queda mirándote.» · «Sale de su
  escondite: es {especie}.» · «Le tiendes la mano. La huele… y se queda a tu
  lado.» · «Desde hoy vive contigo.») **[propuesta, aceptada]**. No guarda nada
  hasta el encuentro: si cierras la página antes, empieza de nuevo; si la
  cierras después, el gachamon ya es tuyo y vuelves al paso del nombre. Al
  terminar vuelves a tu departamento con él, y es el que sale contigo
  **[propuesta, aceptada]**. Sin la segunda cama puesta no hay encuentro, y se
  dice. Con gachamon, el lugar sigue diciendo «Esto se abre más adelante.»
  **[propuesta, aceptada]**.
- **El nombre: un campo con un nombre sugerido**, que cambias o dejas
  **[Felipe, 2026-11-17]**.
- **Sin gachamon**, el pueblo y los lugares se ven con tu avatar solo y sin
  cuidados; la mochila se ve; la ficha y el ropero no se abren **[propuesta,
  aceptada]**. **Los muebles se pueden comprar sin gachamon**; los objetos y
  los cosméticos siguen pidiendo uno **[Felipe, 2026-11-17]**.
- **El huevo desaparece de la página**: la bienvenida cambia su ícono y su
  nota; el dibujo del huevo de la pantalla de inicio de sesión se queda, como
  adorno, hasta que haya otro; en Discord, `/huevo` sigue siendo el aviso de
  hoy **[propuesta, aceptada]**.
- **La carta del alcalde**, a quien no le queda ninguno, dice dónde está el
  suyo: «Te dejé tu cama puesta y otra guardada: ponla y ve a «Aventura», que
  ahí te espera un gachamon.» **[propuesta, aceptada]**.
- Vincular Discord sigue como hoy (sólo sin gachamones): quien amuebló sin
  gachamon y después vincula deja ese departamento atrás **[propuesta,
  aceptada]**. El enlace para traer los de Discord se ofrece en tu
  departamento mientras no tengas gachamon **[Felipe, 2026-11-18]**.
- **[Felipe, 2026-11-18]** El día del cambio paga las medallas de persona que
  cada quien ya tenía ganadas y sin cobrar, una sola vez, y la carta lo dice:
  «Tenías medallas ganadas y sin cobrar: te pagué {gemas}.» **[propuesta,
  aceptada]**.

## 9. Restricciones

- Vale todo lo de `AGENTS.md` que este diseño no contradice: los módulos de
  juego no importan `discord`; `web/` es un adaptador fino; `db.py` posee el
  esquema y no importa `economia.py`; cada cambio de estado va en su
  transacción `BEGIN IMMEDIATE`; ninguna ruta acepta un identificador de
  persona; el servicio web no guarda estado del juego en memoria.
- **El servidor manda**: qué mueble hay en qué casilla lo valida y lo guarda
  el servidor. El cliente dibuja y propone.
- **Lo que mueve monedas lleva un evento** (ampliar, comprar): repetirlo
  devuelve lo de la primera vez. Poner, mover, girar y guardar se pueden
  repetir tal cual.
- Sin dependencias nuevas, sin biblioteca de dibujo: lienzo y módulos de
  JavaScript como hoy. La lógica (proyección, qué casilla se tocó, camino del
  avatar, si un mueble cabe) va en módulos puros con sus pruebas.
- El arte sigue siendo archivos descritos en el contrato; si falta uno se ve
  su recuadro y nunca otro dibujo.
- El repo es público: sin IPs, ids de personas ni secretos.
- `AGENTS.md` se reescribe con este proyecto: unas cuarenta de sus líneas
  hablan de la muerte, el refugio, la incubadora o las casas.

## 10. De dónde se parte

- **Cuánto código toca**: el inventario está en
  `.superpowers/sdd/2026-11-14-rework-reconocimiento/inventario.md` (no va en
  el repo). Lo esencial: la muerte, el refugio, la incubadora y las casas tocan
  cerca de un tercio de las pruebas; el ritmo de **todo** paso del tiempo se
  calcula hoy según la casa (`db._avanzar_en` → `casas.ritmo_de`); cada bancal
  del huerto pertenece a una casa; la tabla `mobiliario` sólo deja un mueble de
  cada por persona; `simulacion.avanzar` no avanza a quien no es la activa.
- **La cantera**: la rama local `web/6-tu-casa` (no publicada) tiene piezas
  que sirven: el recorte de una escena en un lienzo (`escena.js`), las piezas
  comunes de las pantallas de lista (`articulos.js`: `mandarDesdeLaFila`,
  `trasElToque`, `volverALaFila`) y la idea de guardar posiciones en datos.
- **Se publica todo junto, una sola vez** **[Felipe]**: los planes se juntan
  en la rama del rework, Felipe revisa cada uno en local con su recorrido, y
  hay un solo día del cambio. Publicado a medias el juego queda roto (los
  gachamones tendrían hambre mientras la Incubadora dice que ahí no pasa el
  tiempo; Discord perdería las casas antes de que exista el departamento).
- Esto no cabe en un plan. Corte sugerido **[propuesta]**: (1) nadie muere;
  (2) el tiempo para todos; (3) el bot en pausa; (4) la vivienda por casillas
  en el servidor y el día del cambio; (5) el departamento en pantalla; (6)
  partir sin gachamon (sin huevo, el monedero en 0 para quien empieza, la
  primera aventura, y que todo funcione sin ninguno); (7) los muebles que se
  usan solos; (8) el pueblo sin Refugio ni Incubadora y los documentos. Partir
  sin gachamon se separó del (4) al escribir su plan, y el 2026-11-16 Felipe
  puso la pantalla antes **[Felipe]**: hasta el (6), el huevo sigue existiendo
  y el que nace de él no pide cama.
  Entre el (5) y el (6) va un plan corto, la puerta (sección 4.5), que Felipe
  pidió al probar la pantalla **[Felipe, 2026-11-16]**.

## 11. Lo que queda al constructor

Los nombres de tablas, módulos y rutas; cómo se guarda cada mueble (cada uno
necesita su identidad, porque puede haber varios iguales); el tamaño en píxeles
de una casilla y de las imágenes; cómo camina solo un gachamon; la lista de
nombres para los reclutas; el texto exacto de cada frase nueva, entre ellas el
diálogo de la primera aventura (se le presentan a Felipe antes de publicarlas,
como siempre); el orden y el tamaño de las tareas.

## 12. Lo que Felipe ya dijo de los proyectos que siguen

- **Balcón y huerto (2).** El 3 × 3 no puede tener balcón; con la primera
  ampliación llega el objeto balcón, que se coloca como las ventanas. Son 4
  casillas y va pegado a una pared. Sin balcón no hay huerto.
- **Pueblo y edificio (3).** El mapa y el interior de cada lugar, en
  isométrico. «Tu casa» y «Barrio» se funden en un edificio de viviendas: al
  entrar sale una ventana «Departamento / Visitar».
- **Gente en vivo (4).** Ves a la otra persona entrar por la puerta y caminar.
  Se hablan con globos de texto sobre la cabeza; lo ven sólo los de esa pieza y
  no se guarda. Cada departamento tiene tres estados: libre (el de partida),
  con contraseña o con timbre (el dueño tiene que estar para abrir). La plaza,
  la tienda y los demás lugares son públicos: se habla y se intercambia, sin
  mover ni llevarse nada. Quien te visita ve tus cosas y no las toca.
- **Objetos e intercambio (5).** Una mesa de 1 × 1 con «gato», contra un
  gachamon o contra otra persona. Un atril para dibujar a mano alzada; el
  dibujo queda como cuadro si tienes marcos comprados. Teletransportadores en
  pareja: de un punto a otro de la pieza, o entre dos departamentos si le das
  uno a otra persona. Intercambiar objetos y dinero con quien está en el mismo
  lugar.
- **El cementerio** queda como un lugar para explorar, con algún evento
  secreto opcional.
- **El bot (6)** queda sin uso al terminar la migración. Desde el día del
  cambio de este proyecto ya sólo sirve para vincular (sección 7).
