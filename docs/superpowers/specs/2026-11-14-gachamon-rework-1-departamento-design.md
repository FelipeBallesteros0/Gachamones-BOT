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

- Que decorar tenga «modos» o pasos de más. Felipe probó un boceto con un modo
  «Decorar» y lo encontró complicado: se toca el mueble y ahí salen sus
  opciones **[Felipe]**.
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
  **0 monedas y 0 gemas** **[Felipe]**.
- **El primero se gana en la primera aventura** **[Felipe]**: es fija, vas tú
  solo con tu avatar, encuentras a un gachamon básico **sorteado entre los
  comunes** y se une siempre; hay diálogo, pero sin opciones. Se abre cuando ya
  pusiste la segunda cama: el juego lo pide como primer paso **[propuesta,
  aceptada]**. Después, las aventuras son las de siempre, con tu activo.
- **El nombre de un recluta se pone al reclutarlo. Si no se lo pones, se pone
  uno él solo** **[Felipe]**. El nombre sale de una lista del juego, nunca es
  el de su especie ni uno que ya tengas, y se le puede cambiar una vez desde su
  ficha **[propuesta]**. Los reclutas que hoy esperan nombre se lo ponen solos
  el día del cambio **[propuesta]**.
- **Mientras exista el bot, el plantel no pasa de 25** **[Felipe]**: sus menús
  no muestran más. Es la única excepción a «el límite son las casillas», y se
  quita cuando el bot se apague (proyecto 6).

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
- **Giran en 4 posiciones** **[Felipe]**. Cada mueble tiene **dos imágenes**,
  una de frente y una de espaldas, y cada una se usa también espejada: dos
  posiciones miran de frente y dos de espaldas. Vale igual para los de 1 × 1.
  Un mueble alargado cambia las casillas que ocupa al girar.
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

Cómo lo propongo **[propuesta]**:

| Mueble | Casillas | Precio | Con él puesto |
|---|---|---|---|
| Refrigerador | 1 | 300 | la comida de quienes viven ahí no baja de 30 |
| Consola | 1 | 300 | el ánimo no baja de 30 |
| Ducha | 1 | 300 | el aseo no baja de 30 |
| Pesas | 1 | 300 | cada gachamon gana 1 punto de entrenamiento de fuerza por día |

- No hay que llenarlos ni cuestan por uso. Tener dos no hace más.
- Si al ponerlo la barra ya está por debajo de 30, sube a 30.
- No dan experiencia ni monedas: eso sólo lo da cuidar uno mismo.
- Suman 3 de comodidad cada uno, como cualquier mueble.
- En pantalla se ve a los gachamones acercarse a usarlos de vez en cuando; es
  adorno, la regla la lleva el servidor.

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
  quieres.
- **«Guardados»** abre lo que tienes sin poner: tocas uno y después una
  casilla **[propuesta, aceptada]**.
- **Tocas a un gachamon** y su ficha queda abajo: sus barras, sus cuidados y
  «Salir con él». También tiene «Mover», para apartarlo **[Felipe]**.
- **Los gachamones caminan solos** por la pieza **[Felipe]**. Mientras mueves
  o colocas un mueble se quedan quietos, y si lo sueltas donde hay uno, se
  corre a la casilla libre más cercana **[propuesta]**. Dónde está parado cada
  uno no se guarda: sólo se guarda dónde están los muebles **[propuesta,
  aceptada]**.
- **«A todos»**: los cuatro botones, bajo la ficha.
- **«Ampliar»**: muestra cuánto cuesta sumar una fila y cuánto una columna.
- Bajo la pieza, una línea con el tamaño, las casillas ocupadas, las camas y
  los gachamones.
- Vale en el teléfono y en el computador, con el corte de 900 px de hoy.
- **Todo lo que se hace tocando el dibujo se puede hacer también sin él**
  (teclado y lector de pantalla): una lista de lo puesto y de lo guardado con
  los mismos botones **[propuesta]**.

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
  uno tenía no se tocan.
- **Las casas compradas se devuelven enteras en monedas** (lo que cuesta cada
  una en el catálogo). Es una devolución: no pasa por el tope diario, y se paga
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
- Cada persona ve **una vez** una carta del alcalde que cuenta qué le tocó: en
  la web al entrar, y en Discord como mensaje privado la primera vez que use un
  comando después del cambio. Verla en un lado la da por vista en el otro
  **[propuesta]**.
- El cambio corre una sola vez al arrancar, es seguro repetirlo y se hace con
  una copia de la base tomada antes.

## 7. Discord, mientras no se apague

Entre este proyecto y el 6 el bot sigue vivo. Lo acordado **[propuesta,
aceptada]**:

- **Deja de funcionar ahí todo lo de casas**: `/casa`, `/visitar`, comprar,
  mejorar y vender casa, los muebles de la tienda, Amueblar, Mudar y el huerto.
  Esos comandos contestan que tu departamento ahora está en la página, con el
  enlace.
- **Sigue igual**: cuidar al activo, competir, las aventuras, reclutar (con la
  regla de la cama libre y el nombre al reclutar), conversar, los logros.
- **`/huevo` deja de dar un huevo**: contesta que se empieza en la página, con
  el enlace **[propuesta, aceptada]**. Quien llega nuevo empieza ahí.
- **Elegir al activo sigue en Discord** (`/plantel`), sin hablar ya de la
  incubadora **[propuesta]**.
- Desaparecen el bucle de muertes, el aviso de hambre y la lápida de un
  gachamon recién muerto. `/cementerio` sigue enseñando a los de antes.
- **Regalar se pausa** hasta el intercambio del proyecto 5 **[Felipe]**: hoy
  sólo se regala desde `/visitar`, que desaparece. `/buzon` sigue funcionando,
  para que nadie pierda los regalos que tiene pendientes.
- **Cocinar sigue disponible en Discord**, fuera del menú del huerto: lo
  cosechado el día del cambio se puede seguir cocinando **[propuesta]**.
- El manual publicado se corrige en su sitio.
- **La web es de un solo servidor de Discord, Robot House** (decisión de
  Felipe en la parte A: un solo mundo). Si el bot está en otro servidor, ahí
  valen las mismas reglas nuevas pero no hay página adonde ir: el aviso dice
  que las casas ya no están disponibles, sin enlace **[propuesta]**.

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
- Esto no cabe en un plan. Corte sugerido **[propuesta]**: (1) el tiempo para
  todos y el fin de la muerte; (2) la vivienda por casillas en el servidor, el
  día del cambio y Discord; (3) el departamento en pantalla; (4) los muebles
  que se usan solos; (5) el pueblo sin Refugio ni Incubadora y los documentos.

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
- **El bot (6)** queda sin uso al terminar la migración.
