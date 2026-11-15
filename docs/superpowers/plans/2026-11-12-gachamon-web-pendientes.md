# Gachamon web — pendientes que dejó el plan 1

Lo que el plan 1 («reglas y bot») encontró y no le tocaba arreglar. Quien
escriba el plan 2 o el proyecto 2 parte de aquí.

## Para el plan 2 (servidor web y pantalla principal)

- ~~**Crear un gachamon y mirar la cuenta, en la misma transacción.** `db.crear` no consulta `cuentas_web`. Si la web resuelve `db.cuenta_web()` fuera de la transacción en la que crea la criatura, puede nacer un gachamon de la identidad web justo después de vincular, y queda huérfano.~~
  **Resuelto en el plan 2.**
- **«Sin gachamones» no es «sin estado».** Al vincular, una identidad web
  vacía de gachamones puede haber dejado un monedero, un reloj del refugio o
  una compra. Esas filas quedan huérfanas. Decidir si la web impide llegar a
  ese punto o si se limpian.
- ~~**El código de vinculación se puede pedir con engaños.** Quien convenza a otra persona de escribir su código en Discord se queda con los gachamones de esa persona en la web. Avisarlo donde la web muestra el código y en la descripción de `/vincular`.~~
  **Resuelto en el plan 2** (la web avisa «No se lo pases a nadie»); lo que falta del lado del bot está abajo.
- ~~**«Desfallecido».** Con la comida en 0, la ficha y los globos tienen que decir que el gachamon está desfallecido y pide comer (diseño, 5.8).~~
  **Resuelto en el plan 2.**
- ~~**La secuencia de arranque vive en `bot.py`.** `db.inicializar()` seguido de `economia.devolver_cosmeticos_retirados()` está escrito dentro de un módulo que importa `discord`. El servicio web necesita lo mismo: sacarlo a una función sin Discord y probarla.~~
  **Resuelto en el plan 2** (`economia.poner_al_dia`).
- **La prueba del reintento por colisión.** Ninguna prueba pasa `rng` a
  `db.pedir_codigo_de_vinculo`; añadirla cuando la web empiece a llamarla.
- **La regla por ruta del túnel sólo se comprobó en seco.** Aplicarla pide
  `sudo`, reiniciar el túnel y la autorización de Felipe. Ver
  `../specs/2026-11-12-tunel-regla-por-ruta.md`.

## Salió al ejecutar el plan 2

- Starlette avisa de que su cliente de pruebas con `httpx` está en desuso y
  pide `httpx2`; las pruebas filtran ese aviso. Recomendación: cambiar la
  dependencia de desarrollo cuando el dueño lo apruebe.
- La cookie de sesión de Rowino no lleva marca de tiempo: una copia robada sirve
  hasta que cambie la clave. Es de Rowino, no del juego.
- Cuando alguien canjea un código con `/vincular`, el bot contesta que quedó
  vinculada sin decir a qué cuenta de Rowino. Quien engañe a otro para que
  escriba un código ajeno se queda con sus gachamones. La web ya avisa «No se lo
  pases a nadie»; que el bot nombre la cuenta, o pida confirmar, queda por
  decidir.
- ~~La web deja apuntada cada muerte que registra (tabla `muertes_por_anunciar`) y el bucle del bot la anuncia en su siguiente vuelta, hasta quince minutos después.~~
  **Resuelto en el rework 1: ya nadie muere.**
- Si se repite un cuidado que hizo evolucionar (un reintento tras perderse la
  respuesta), la repetición no dice que evolucionó, aunque el estado ya muestra
  la etapa nueva.
- Las frases de los globos (`globos.py`) y los dibujos de relleno (el avatar, el
  huevo y las catorce especies sin arte) son provisionales.
- Un gachamon de Discord que nunca fue bautizado (se llama como su especie)
  pasa por el bautizo la primera vez que su dueño entra a la web.
- Cuando una cuenta vinculada no tiene activa pero sí uno con nombre en la
  incubadora, abrir la web lo saca y arranca su reloj de hambre sin anuncio en
  Discord.
- Las medallas que se ganan al nacer el gachamon se pagan pero la web aún no
  las enseña; las que se ganan en la web no se cantan en el canal de Discord.
- `users.id` de Rowino no es `AUTOINCREMENT`: si un día se borra a mano el
  usuario de id más alto, el siguiente registro heredaría su cuenta del juego y
  su vínculo. Hoy Rowino no borra usuarios.
- ~~`Mascota._avisar_hambrientas` lee la lista, espera envíos a Discord y guarda la fila entera: con la web escribiendo a la vez, un cuidado hecho en esos segundos se pisaría. Bastaría un `UPDATE` sólo de `avisada`.~~
  **Resuelto en el rework 1: ya nadie muere.**
- Cada lectura del estado toma el turno de escritura por el `INSERT OR IGNORE`
  del monedero; bastaría una lectura con los saldos iniciales por defecto.
- `globos.elegir` no lo usa nadie en el servidor: la regla vive otra vez en
  `tiempo.js`.

## Salió al ejecutar el plan 3

### Arte

- Todo el arte de la web es de relleno y se nota (lleva «RELLENO» escrito): 137
  archivos. Los nueve lugares del mapa son casitas de colores.
- El avatar se dibuja por capas desde archivos y el género ya no cambia el
  dibujo.
- El generador de rellenos (`herramientas/rellenos.py`) lleva sus propias tablas
  de colores y ramas por clave de ropa: una opción nueva del avatar extiende el
  contrato sola, pero `generar()` falla (color) o la dibuja en silencio como
  overol (ropa).
- En el relleno, la sombra del cuerpo se corta una fila por abajo y el pelo es
  idéntico en las tres poses.
- La escala del avatar y del mapa no es un número entero de píxeles: se prefirió
  conservar el tamaño. Algún píxel sale un poco más ancho que su vecino.
- En la escena de un lugar cuyo dibujo falta, el gachamon tapa parte del nombre
  del archivo en el recuadro. La falta se nota igual y queda en el registro del
  servidor y en `tests/test_arte.py`.
- Una ruta de arte sin forma de pieza no deja rastro ni en la consola.

### El mapa y la caminata

- `llegarYa` tras una vuelta corta (dar la vuelta antes de andar el hueco entero
  y volver al nodo de partida) deja al gachamon más cerca del avatar de lo
  debido, hasta encima; se ve sólo mientras se espera la respuesta del servidor.
- En los dos lugares sin camino hacia la izquierda, el gachamon arranca parado
  en el pasto, al lado del avatar.
- Pasar la ventana a otro monitor con distinta densidad no reencuadra el lienzo,
  que sale en bloques hasta el siguiente cambio de tamaño.
- Con la ventana del computador muy baja (menos de unos 490 px) aparecen la
  cámara y las flechas del teléfono.
- El comportamiento táctil real (arrastrar de lado mueve la cámara, de arriba
  abajo desplaza la página, un toque con temblor sigue entrando) sólo se probó
  con eventos sintéticos: hay que probarlo en un teléfono de verdad.
- «Volver» desde el mapa vuelve a leer la sesión, la cuenta y el estado, tres
  lecturas seguidas: tarda en vez de ser instantáneo, a cambio de que las
  esperas de los cuidados salgan bien. Bastaría la del estado.
- Tocar «Pueblo» con un cuidado todavía en camino pinta el mapa con los saldos
  de antes; se corrige al entrar a un lugar.
- Si `pueblo.json` faltara en la versión vigente (un despliegue roto),
  «Pueblo» devuelve al lugar sin decir por qué.

### La pantalla del lugar

- Si al llegar a un lugar hay una celebración en pantalla o la pestaña está
  oculta, el globo de llegada se pierde: la llegada queda muda y el siguiente
  globo ya es charla de siempre.
- El fondo de la escena no se guarda de un dibujo de ancho o alto cero.
- Al llegar a un lugar, el foco cae en el nombre del gachamon: un lector de
  pantalla no anuncia ni el lugar ni su aviso.

### El despliegue

- Los módulos mezclados quedaron resueltos en el plan 5. La web vieja servía
  los archivos nuevos bajo la dirección de su versión vieja mientras la suite
  corría en la Pi, y desde el plan 5 esos estáticos se guardan un año. Ahora
  `actualizar-pi.sh` para la web antes de tocar sus archivos y la vuelve a
  arrancar en el reinicio del final o, si la suite sale en rojo, en cuanto la
  Pi vuelve al commit de antes. A cambio, durante el despliegue la web no
  contesta: unos segundos con `SIN_TESTS=1`, unos minutos con la suite en la
  Pi. Una página abierta dice que el juego no está disponible y deja
  reintentar; quien la abre en ese rato no recibe la portada.
- Resuelto en los retoques del plan 5: un despliegue que se corta por otra
  cosa después de parar la web (falla `pip`, se cae la conexión, falla el
  reinicio del final) ya no la deja parada sin decir nada. Si el bloque remoto
  no llega al final (lo decide una marca, no el código de salida, para que
  también cuente una señal), hace lo mismo que la suite en rojo: vuelve al
  commit en el que estaba la Pi y reinstala sus requisitos, y reinicia la web.
  No la arranca con el código nuevo porque la web arranca por
  `economia.poner_al_dia`, que migraría la base mientras el bot sigue con el
  viejo. La orden de la suite ignora SIGPIPE, así que una conexión caída no le
  impide volver atrás y reiniciar la web en el camino en rojo. Los dos caminos
  usan `restart` y no `start`: si alguien la arrancó a mano siguiendo el aviso,
  un `start` no haría nada y la web serviría los archivos de antes bajo la
  versión nueva. Si el guion termina con error, su última línea es el comando
  exacto para arrancarla a mano. Una conexión caída durante la suite cuenta
  como suite en rojo aunque pasara (el `tail` no puede escribir): la Pi vuelve
  al commit de antes y reinicia la web. Lo que no cubre: si el corte llega
  cuando el bloque remoto y la suite ya terminaron bien (al conectar para el
  reinicio del final o durante él), o la Pi no se entera de él, la web queda
  parada y sólo queda ese aviso.
- `deploy.sh`, que copia esta carpeta con `rsync`, no para la web: entre la
  copia y el reinicio (lo que tarda `pip`, sin suite) la web vieja sigue
  sirviendo los archivos nuevos, y la caché puede guardar la mezcla.
- Mejora posible: correr la suite en un clon aparte antes de tocar el árbol
  vivo, y parar la web sólo para cambiar los archivos y reiniciar; así no
  estaría parada esos minutos.

### Pruebas

- Todo `mapa.js` y lo nuevo de `lugar.js` descansan en un arnés manual con
  capturas: sin dependencias nuevas no hay DOM en Node, y las pruebas de
  `tests/test_web_cliente.py` sobre el mapa y el lugar son de texto.
- La prueba de toques al azar de `pueblo.js` sólo vigila al avatar, no al
  gachamon.
- La prueba de palabras prohibidas en las frases de los lugares busca subcadenas
  y no vigila otras formas de implicar compañía («nadie», «vecinos»).
- Faltan pruebas de cosas que el código ya cumple: `POST /lugar` sin gachamon,
  repetir el mismo lugar, que el lugar sobrevive al vínculo; y cinco casos de
  datos rotos de `pueblo.problemas` (arista con un solo extremo, coordenada no
  numérica, `parte` ausente, `hueco` negativo, `aristas` que no es lista).
- A `tests/js/tiempo.test.mjs` le faltan tres casos de `elegirGlobo` que el
  código cumple: llegar con sólo charla, llegar cuando la única frase del lugar
  es la que se acaba de decir, y una lista de globos que no es lista.
- `pueblo.problemas` lanza si la raíz del JSON no es un diccionario, y
  `pueblo.aviso` lanza con una clave desconocida (quien llama pasa antes por
  `pueblo.existe`).

## Salió al ejecutar el plan 4

### El dinero y los eventos

- Repetir con el mismo evento una compra que no alcanzó, cuando entretanto ya
  alcanza, contesta «No se pudo comprar. Vuelve a intentarlo.» (clave
  `reintenta`): el «no» de una compra de objeto queda congelado con su evento.
- El mismo evento usado para dos tipos de compra distintos (una casa y luego un
  mueble) no da error: la clave de `acciones_unicas` lleva la acción. Nada se
  cobra dos veces.
- Un `casa_id` negativo o de otra persona no mueve nada y contesta «Esa casa no
  es tuya.»; al vender sin tener ninguna casa, «No tienes casa que vender.».
- La cuenta de lo que cuesta mejorar una casa está escrita dos veces (en
  `economia` y en la ruta de la tienda); lo limpio sería que el resultado de
  `comprar_casa` trajera lo que falta.
- En un reintento de «usar», la frase de la comida («ahora N») y el nombre del
  gachamon salen de cómo está ahora, no de la primera vez; para que fueran los
  de entonces habría que anotarlos con el evento.
- ~~Una muerte que descubra `usar_objeto` se guarda, pero no queda apuntada para que el bot la anuncie (igual que en los cuidados): en la web la ruta ya pasa antes por la comprobación que sí la apunta.~~
  **Resuelto en el rework 1: ya nadie muere.**
- El `except RuntimeError` de las rutas de la tienda y la mochila es más ancho
  que «evento ya usado»: cualquier `RuntimeError` de `economia` sale como el 409
  `evento`.
- La tabla `acciones_unicas` no se purga: cada evento queda guardado para
  siempre.

### Lo que el reconocimiento encontró en Discord y este plan no toca

- El botón «Amueblar» de `/casa` falla: `tienda.py` usa `hogar.casa`, que no
  existe.
- El texto de mejorar una casa anuncia el precio entero, no lo que falta.
- `db.activar` sobre el propio activo le borra el decaimiento pendiente.
- `economia.plantar` deja sembrar cualquier objeto.

### La web

- Sin ningún gachamon, comprar y usar contestan «Para comprar hace falta un
  gachamon.» y «Para usar eso hace falta un gachamon.»; la pantalla nunca llega
  ahí (sin gachamon se ve el huevo).
- La fecha hasta la que dura el refugio sale en hora UTC.
- La mochila enseña la descripción o la nota de cada objeto, no las dos.
- Cualquier error de la mochila que no sea de sesión ni de cuenta esconde la
  lista y la vuelve a pedir (es seguro, pero cierra el campo de la placa).
- Los cuidados (`POST /cuidar`) tienen el hueco que tenía la mochila: si el
  cambio de gachamon ya estaba registrado antes de la petición (otro activado
  desde Discord~~, una muerte que leyó otra pestaña~~), el cuidado le cae al
  relevo. La mochila lo cerró mandando el gachamon que enseña la pantalla.
  **Lo de la muerte, resuelto en el rework 1: ya nadie muere.** El cambio de
  activo desde Discord sigue.
- `web/mochila.py` importa sus ayudas de `web/tienda.py`, y `lugar.js` repite
  algunas de `articulos.js`.
- Las clases de CSS que comparten la tienda y la mochila se llaman `…-tienda`.
- En el estado de «no carga» de la tienda y de la mochila (cuando ni la compra
  ni la relectura recibieron respuesta), la cabecera sigue enseñando el saldo de
  antes; se arregla en el módulo común `articulos.js`.

### Pruebas

- Las pantallas de la tienda y la mochila sólo tienen pruebas de texto y el
  recorrido manual con capturas (como el mapa): no hay DOM en Node sin
  dependencias nuevas.
- Faltan pruebas de cosas que el código ya cumple: que comprar algo que no se
  vende no deje fila en el libro de la economía; que el menú de Discord usa la
  interacción como evento; el mismo evento de la misma persona en otro servidor;
  la frase exacta de las sopaipillas y de las pociones en la web; que el
  reinicio borra la espera; y, en la tienda, «nunca caminó», «lugar que ya no
  existe» y «tienda cerrada».

## Salió al ejecutar el plan 5

### Reglas y dinero

- Mirar la ficha no paga medallas: «Veterano» y «Bien criado» se cobran en el
  siguiente cuidado, y mientras tanto la ficha enseña su progreso lleno. En
  Discord, `/logros` las paga al abrirse.
- La regla del progreso de las medallas (sólo si no la tiene y la meta es mayor
  que 1, topado en la meta) está escrita dos veces: en la ficha de la web y en
  el panel de `/logros`, que vive en un módulo con Discord. Lo limpio sería una
  función pura en `logros.py` que usen los dos.
- `economia.saldos` crea el monedero si no existe, así que leer la ficha o el
  estado puede escribir esa fila (inocuo: quien tiene gachamon ya tiene
  monedero).
- La comprobación del bautizo (normalizar el nombre y rechazar el de su especie)
  está dos veces en `nacer.py`: en el bautizo de la activa y en el de un
  gachamon concreto.
- En Discord, bautizar a un recluta con el nombre de su especie contesta
  «Nombre no válido. Ese es el nombre de su especie. Ponle uno propio.»~~, y
  elegir en el menú del plantel a una activa que ya había muerto sin registrar
  registra su muerte y contesta «Ese gachamon no es tuyo o ya no está.»~~.
  **Lo del plantel, resuelto en el rework 1: ya nadie muere.**

### La web

- En el ropero, tocar «Poner» en un título que ya lleva repite «Ahora es Pelusa
  la Invicta.»: la frase de «ya lo lleva» es la de ponerlo.
- La ruta del ropero convierte una regla que no devuelve gachamon en el 409
  «Tu gachamon ya no es el mismo»; esa rama no debería darse, y un error interno
  sería más honesto. Además relee el activo antes de armar el estado: si muriera
  justo entre la regla y esa lectura, contestaría 409 con el cambio ya hecho
  (ventana mínima, como la mochila).
- `GET /incubadora` se puede pedir desde cualquier lugar; sólo sacar exige estar
  en la Incubadora. Un `gachamon_id: null` en `/bautizar` es un 422, porque la
  pantalla omite la clave para bautizar a la activa.
- `web/incubadora.py` escribe a mano la forma de sus respuestas en vez de usar
  las ayudas de `web/tienda.py` que usan el ropero y la mochila. La pantalla del
  ropero copia por tercera vez piezas de la mochila (el id del gachamon, devolver
  el foco a la fila, el fallo sin respuesta), y la frase «No hubo respuesta.
  Revisa tu conexión.» está repetida en tres pantallas. Todo eso podría vivir en
  `articulos.js`.
- En la Incubadora, un bautizo que sale bien no deja frase en la zona de aviso:
  la fila cambia a su nombre, con «Sacar». Y si el bautizo llegó pero la
  relectura del plantel falla, tampoco se dice nada.
- Dos reclutas sin nombre de la misma especie se leen igual para el lector de
  pantalla: «Ponerle nombre a Purreon» dos veces.
- Resuelto en los retoques del plan 5: a quien tiene Discord vinculado y nunca
  empezó su estancia (sin fila de hogar), el Refugio le decía cada día «Tu
  estancia en el refugio dura 7 días más.». Era cierto en el modelo, pero se
  leía igual todos los días. Ahora le dice «Tu semana en el refugio todavía no
  ha empezado.»; saber si hay fila es una lectura (`db.estancia_empezada`).

### Pruebas

- Las pruebas de texto de la incubadora vigilan la forma del código y no los
  flujos, como las de la tienda, la mochila y el ropero. Y una prueba de
  `articulos.js` comprueba detalles de `lienzoDePieza`.
- Ninguna prueba vigila el selector de los corazones (`.escena > .corazon`), ni
  que un 304 o un HEAD no lleven la cabecera inmutable.
- Faltan pruebas de: una medalla «tuya» con progreso en la ficha; y el ropero
  con títulos en «ya lo lleva», «lo lleva otro» y «ya no lo tienes». La de que
  mirar el Refugio no crea la fila del hogar quedó resuelta en los retoques del
  plan 5. También una ayuda de pruebas (`vinculada_sin_gachamon`) repite pasos
  de otras.

## Salió al ejecutar el rework 1 (nadie muere)

### Lo decidido

- Ningún gachamon muere: con la comida en 0 se queda en 0 y sigue vivo, sea de
  quien sea. Lo que antes sólo valía para quien juega sólo en la web vale ahora
  para todos, y la excepción (`identidad.sin_aviso_de_hambre`) desapareció.
- Quien antes moría ahora cobra lo de siempre: un viaje que deja la comida en 0
  paga su hallazgo y su experiencia, y cuidar a uno que lleva días en 0 paga su
  moneda. No abre ningún provecho nuevo: salir de aventura y competir siguen
  pidiendo comida.
- Los que murieron antes siguen muertos, en el cementerio, con las medallas que
  tenían. Un gachamon al que ya le tocaba morir cuando llega el cambio y el bot
  no había procesado sigue vivo, con la comida en 0.
- Se fueron: el bucle de muertes del bot (queda un mantenimiento que sólo limpia
  el uso de la IA), el aviso de hambre, el anuncio de una muerte, la pantalla
  del difunto de la web y su ruta, el instante de muerte y de aviso que guardaba
  cada fila, y la tabla de las muertes por anunciar (las filas que hubiera
  pendientes se van sin anunciarse).
- «Superviviente» son 100 aventuras, sin más condición.
- Queda «el remiendo»: si una persona se quedó sin activa viva por un muerto de
  antes, sale sola de la incubadora la primera que tenga nombre, al entrar a la
  web, al romper el huevo, al poner nombre o al cambiar de activo; en Discord,
  al elegir otro en `/plantel`. Sin nombre no sale ninguna.
- Pulsar el panel viejo de Discord de un gachamon que murió antes hace lo de
  siempre: actúa sobre el relevo si lo hay y apaga ese panel, o dice que no
  tienes gachamon vivo.
- En el manual de Discord, el bloque «Quién le ha tocado ser» pasó de la página
  1 a la 4: la frase nueva de «Cuidarlo» es más larga y la página 1 se salía
  del margen.

### Al publicar

- Los dos guiones de despliegue reinician primero el bot y después la web. Con
  `actualizar-pi.sh` la web está parada mientras tanto, así que no hay ventana.
  Con `deploy.sh` la web vieja sigue viva unos segundos sobre la base que el bot
  nuevo ya migró y, si en ese rato descubre una muerte, esa petición da un error
  500 sin guardar nada.
- Mientras exista la intemperie (se va con el plan de la vivienda), su suelo de
  25 protege la comida mejor que estar bajo techo, donde llega a 0. No llega a
  ningún jugador: todo el rediseño se publica junto.

### Si hubiera que volver atrás

- El código de antes arranca sobre la base ya limpia (recrea la tabla y los
  índices), pero los gachamones de Discord que lleven tiempo con la comida en 0
  mueren en la primera lectura de cualquiera (basta el `/jardin` de otra
  persona), sin aviso, sin anuncio y sin relevo.
- Antes de publicar el rediseño, guardar aparte, fuera de la rotación de cinco
  copias, la copia de la base de antes del cambio.
- Si algún día se vuelve al código de antes, con los dos servicios parados y
  antes de arrancarlo, correr:

  ```sql
  UPDATE criaturas SET hambre = MAX(hambre, 50), actualizada_en = <ahora en UTC, formato ISO> WHERE muerta_en IS NULL AND activa = 1
  ```

  Probado: nadie muere al volver y el juego de antes retoma solo.
- Desde el rework 2 esta receta va sin `AND activa = 1`, para todos los vivos:
  lo cuenta «Si hubiera que volver atrás» en la sección del rework 2.
- Hoy hay muy poca gente jugando, así que el riesgo real es pequeño, pero la
  receta queda escrita.

### Pendiente

- Las columnas `muere_en`, `avisa_en` y `avisada` de `criaturas` y
  `difuntos_vistos_hasta` de `cuentas_web` siguen en el esquema, sin que nadie
  las lea; `Criatura.avisada` sigue como campo, siempre en falso.
- `.claude/skills/generated/` (lo genera GitNexus) todavía nombra el bucle de
  muertes: se corrige solo cuando se regeneren.

### De producto, para decidir más adelante

Son observaciones de la revisión final, no decisiones.

- Descuidar ahora rinde: el esfuerzo de entrenar vale más con las barras
  bajas, y sin muerte dejar la comida en 0 es gratis para todos.
- «Veterano» (30 días de vida) ya no pide cuidar a nadie.
- Los gachamones abandonados ya no salen nunca de `/jardin` ni de `/ranking`.
- Algunas muertes no se contarán nunca: las pendientes de anunciar al llegar
  el cambio y las que una cuenta web no había visto.
- Discord se queda sin señal de hambre: su ficha enseña la barra en 0 y la
  cara de siempre, sin un equivalente a «Desfallecido».
- En el manual, la página «Tu casa» todavía dice que la intemperie «no puede
  matarlo», y el bloque «Quién le ha tocado ser», que pasó a la página 4,
  empieza con un «también» que se refería a la página 1. Las dos cosas se
  arreglan cuando el plan de la vivienda reescriba el manual.

### Pruebas

- La prueba del mantenimiento del bot no fija el argumento de la limpieza ni el
  intervalo del bucle.
- La frase del `/cementerio` vacío («Aquí no descansa nadie.») no la fija
  ninguna prueba: ninguna llega a ese comando.
- No hay prueba del adaptador web de romper un huevo después de una muerta de
  antes (lo cubren el dominio y el recorrido).

## Salió al ejecutar el rework 2 (el tiempo para todos)

### Lo decidido

- A todos los gachamones vivos les pasa el tiempo, sean o no el activo: la
  comida, el ánimo y el aseo les bajan al mismo ritmo, con el ritmo de su casa.
  Antes sólo le pasaba a la activa y las demás «dormían en la incubadora».
- El día del cambio, a los que no eran el activo el reloj les parte de ese
  momento: no se les viene encima lo que durmieron. Pasa una sola vez, aunque
  el bot y la web arranquen a la vez, y queda apuntado en una tabla nueva,
  `cambios_hechos`, en la misma transacción que el cambio. Lo que haya que
  hacer una sola vez en los planes que siguen usa esa misma marca.
- El activo es sólo «el que sale contigo»: el que compite, va de aventura y
  conversa. Cambiar de activo ya no toca el reloj de nadie ni guarda nada: ir y
  volver muchas veces no ahorra ni duplica el paso del tiempo.
- Un cuidado o una caricia le cae al gachamon que se elija (en la web,
  mandando su `gachamon_id`), o al activo si no se elige ninguno. Las esperas
  son de cada gachamon; el tope diario de monedas sigue siendo uno solo por
  persona. Uno ajeno, de otro servidor, muerto de antes o que no existe no
  cambia nada, no cobra y contesta lo mismo en todos los casos.
- «A todos» le hace un cuidado a cada gachamon que puede recibirlo y dice a
  cuántos les tocó. Paga una moneda por cada uno, igual que cuidarlos de a uno
  y dentro del tope de siempre. No se alimenta al que se empacharía ni se baña
  al que ya está limpio; jugar y entrenar les sirven siempre, porque entrenan.
  Todo va en una sola transacción: o a todos los que tocaba, o a ninguno.
- En Discord se sigue cuidando sólo al activo: para cuidar a otro se sale con
  él, que no cuesta nada. Cuidar a cualquiera sin cambiar y «a todos» son de la
  página.
- Un recluta llega con un nombre que se pone él solo, de una lista de cuarenta
  (`nombres.py`), nunca el de su especie ni uno que ya tenga su dueño, y se le
  puede cambiar una vez. En Discord, el botón que sale al unirse lleva dentro a
  qué recluta pertenece y le cambia el nombre a ése. Los que estaban sin nombre
  se lo pusieron solos al arrancar, y ya no existe un gachamon sin nombre.
- Quien tenía el activo muerto de antes y sólo reclutas sin nombre no podía
  jugar: ahora, al arrancar el bot o la web, los reclutas reciben nombre y el
  primero que siga vivo pasa a ser el activo, así que la persona recupera su
  partida en Discord y en la web. El remiendo de siempre sigue ahí por si acaso.
- Las frases de Discord y de la web ya no hablan de la incubadora como un sitio
  donde el tiempo se para: los que no salen contigo están «en casa».

### Si hubiera que volver atrás

Probado yendo del código nuevo al de producción de hoy y otra vez al nuevo,
sobre la misma base.

- El código de producción de hoy arranca y funciona sobre la base ya cambiada:
  no conoce la columna `se_nombro_solo` ni la tabla `cambios_hechos`, y no las
  toca.
- Los que no son el activo vuelven a «dormir» con lo último que se les guardó.
  Nadie pierde nada por eso.
- Los que se nombraron solos conservan su nombre. Con el código viejo no se les
  puede cambiar; al volver el nuevo recuperan su cambio.
- Lo que el código viejo reclute llega otra vez sin nombre, y el siguiente
  arranque del código nuevo se lo pone: por eso ese paso va sin marca.
- **Primera trampa:** uno que no era el activo y quedó guardado con la comida
  en 0 muere en cuanto el código viejo lo saca. La receta del rework 1 sólo
  subía la comida a los activos; desde este plan tiene que ser para todos los
  vivos. Con los dos servicios parados y antes de arrancar el código viejo:

  ```sql
  UPDATE criaturas SET hambre = MAX(hambre, 50), actualizada_en = <ahora en UTC, formato ISO> WHERE muerta_en IS NULL
  ```

- **Segunda trampa:** si después se vuelve a subir el código nuevo, la marca ya
  está puesta y el reloj no se mueve: a todos los que durmieron mientras mandaba
  el código viejo se les cobra de golpe (en la prueba, tras ocho días, las tres
  barras a 0). Antes de arrancar el código nuevo otra vez, con los dos servicios
  parados:

  ```sql
  DELETE FROM cambios_hechos WHERE clave = 'el_tiempo_para_todos'
  ```

  Con eso el arranque vuelve a poner los relojes.
- Restaurar la copia de la base de antes del cambio no tiene ninguna de las dos
  trampas, pero pierde lo jugado desde entonces.

### Pendiente

- Las reglas de cuidar a otro gachamon y de «a todos» están en el servidor,
  pero la página todavía no tiene botones para ellas: llegan con el
  departamento en pantalla. Ahí también se decide si hay que estar en el
  departamento para cuidar a los que no salen contigo.
- Cambiarle el nombre a un recluta desde su ficha de la web no existe todavía:
  el servidor ya lo permite (`POST bautizar` con su `gachamon_id`) y la ficha
  ya dice si se nombró solo.
- El cliente de la web todavía sabe qué hacer con un recluta sin nombre
  (`pantallas.js`, `entrada.js`, `incubadora.js`), aunque el servidor ya no
  manda ninguno. Se va cuando se rehaga la entrada.
- El lugar «Incubadora» de la web sigue existiendo, con su nombre: ahí se
  elige con quién sales. Se va con el pueblo sin Refugio ni Incubadora.
- La mochila y el ropero siguen siendo sólo para el activo.
- El monedero de quien empieza sigue siendo de 50 monedas y 50 gemas, y el
  huevo sigue existiendo: partir sin gachamon y con el monedero en 0 es del
  plan de la vivienda.
- En Discord, el botón «Ponerle nombre» que sale bajo el huevo deja renombrar
  al activo las veces que se quiera, sin gastar una placa. Es anterior al
  rediseño y no se tocó aquí (sólo deja anotado que el nombre lo eligió su
  dueño). Se decide cuando se rehaga `/huevo`.
- Los botones «Ponerle nombre» publicados en Discord antes del cambio (los de
  reclutas que estaban sin nombre) no saben a quién pertenecen: buscan al
  recluta más antiguo de esa persona que todavía conserve el nombre que se puso
  solo.
- Si un reintento de «a todos» llega después de que el pago de una medalla
  fallara, la respuesta no vuelve a mirar las medallas: esas gemas se cobran en
  el siguiente cuidado de ese gachamon. No se pierden.
- `.claude/skills/generated/` (lo genera GitNexus) y los documentos históricos
  de `docs/` todavía nombran `ascender_de_la_incubadora`, que ahora es
  `ascender_un_relevo`.
- El manual publicado, en «Tu casa», todavía dice que la comodidad le frena el
  ánimo «a tu activo»: ahora es a todos los que viven ahí. Se corrige cuando el
  plan de la vivienda reescriba esa página, junto con las otras dos frases
  del manual que quedaron apuntadas en el rework 1.
- Los mensajes de reclutas ya publicados en Discord siguen diciendo que no
  tienen nombre, y nadie le cuenta a su dueño que su recluta se puso uno: la
  carta del alcalde del día del cambio podría decirlo.
- **Para el plan de la vivienda y el de los muebles que se usan solos:** el
  ritmo del hogar se aplica hacia atrás a todo el tiempo que un gachamon lleva
  sin guardarse. Antes de cambiar lo que fija el ritmo de alguien (ampliar,
  poner o guardar un mueble que suma comodidad, el refrigerador, la consola o
  la ducha), hay que poner al día y guardar a todos los que viven ahí, en esa
  misma transacción. Hoy mudar, comprar o vender una casa y el ticket del
  refugio no lo hacen; no le llega a nadie porque las casas y el refugio se van
  antes de publicar.
- **Para el plan de la vivienda:** el día del cambio grande tiene que salir con
  su propia sección de vuelta atrás desde el principio: cada paso de una sola
  vez con marca tiene la misma segunda trampa. Y cuando una regla diga que «la
  persona recupera su partida», se prueba por cada adaptador (un comando de
  Discord y una ruta de la web), no sólo por la función de dominio.

### De producto, para decidir más adelante

Son observaciones, no decisiones.

- Quien juega sólo en Discord y tiene varios gachamones: les baja a todos sin
  que en Discord se vea (`/plantel` no enseña barras), y sólo puede cuidarlos
  de a uno, saliendo con cada uno.
- Con muchos gachamones el tope de 12 cuidados pagados al día se alcanza en uno
  o dos toques de «a todos».
- «Entrenar juntos» paga una moneda por dos entrenados y «a todos», una por
  cada uno.
- La medalla «De la alfa» es de cada gachamon, y con «a todos» se cobran todas
  en un toque: no da más gemas que antes, sólo antes.
- Desde el día del cambio, a quien no tiene casa y se le venció el refugio le
  bajan más rápido todos sus gachamones, no sólo el activo. Se va con la
  vivienda.

### Pruebas

- `POST acariciar` con un cuerpo que no es un objeto se trata como si no
  hubiera cuerpo y acaricia al activo.
- La regla del nombre de un recluta está escrita dos veces: al reclutar
  (`nacer.nombre_de_recluta`) y en el paso de arranque que nombra a los que
  estaban sin nombre.

## Salió al ejecutar el rework 3 (el bot en pausa)

### Lo decidido

- El juego de Discord queda en pausa: el bot sólo atiende `/vincular`, que es
  la forma de que quien jugaba en Discord lleve sus gachamones a la página. Lo
  decidió el dueño para facilitar la migración: en Discord jugaban dos personas,
  y mantener dos juegos con reglas distintas era buena parte del trabajo que
  venía y el mayor riesgo del día del cambio.
- Todo lo demás contesta que el juego se mudó a la página, con el enlace y cómo
  vincular. Los botones, menús y formularios de los mensajes viejos, y
  `/mascota` y `/huevo` —que se quedan como avisos porque son los que la gente
  escribe de memoria—, contestan **en privado**. A quien **menciona** al bot en
  su canal se le contesta **en el canal, a la vista de todos, cada vez y sin
  espera**: una respuesta a un mensaje no puede ser privada. Los otros quince
  comandos desaparecen de Discord.
- Un comando que ya no existe —uno de esos quince, si en un servidor falló la
  sincronización y siguen registrados— también contesta el aviso, en privado, y
  deja una línea en el registro.
- En un servidor que no es el de la página, el aviso dice que el juego está en
  pausa en ese servidor y que lo de cada quien sigue guardado.
- «Escríbeme en …», lo que contesta un comando escrito fuera de su canal, nombra
  sólo los canales del juego de ese servidor: los de otro serían enlaces a
  ninguna parte. Si no ve ninguno, los nombra todos.
- El manual del canal queda en una sola página: el juego se mudó, dónde está y
  cómo vincular, nombrando el canal del juego de ese servidor (que es donde se
  acepta `/vincular`). En un canal de información de un servidor sin página, la
  página única es el aviso de la pausa.
- El código del juego de Discord salió de la rama: los comandos, las fichas de
  texto, los menús de la tienda, del taller, de las casas y del huerto, el
  cambio de plantel por menú, y el jardín. Sigue en producción hasta el día de
  publicar, y en el historial después.
- Se fueron también «Entrenar juntos» (en la página lo reemplaza «entrenar con
  todos»), el seguimiento de los mensajes del bot (la ficha publicada de cada
  gachamon y el estilo de ficha) y el jardín (`/jardin`), que era un dibujo de
  texto en un mensaje.
- No se perdió ningún dato: no se borró ninguna tabla ni columna. Las que
  quedaron sin uso (el estilo de ficha, el mensaje de la ficha y su canal, la
  conversación, el uso de la IA, el buzón) siguen ahí.
- La página ya no manda a Discord: lo que todavía no se puede usar en ella (lo
  de competir, la semilla) no se le vende a nadie, tenga o no Discord
  vinculado, y los avisos de los lugares que abren más adelante dicen sólo eso.
- Ninguna regla del juego se ejecuta ya desde Discord: el bot sólo escribe al
  canjear un código de vinculación y al mantener su página del manual.

### Al publicar

- El bot nuevo, al arrancar, sincroniza sus comandos: en Discord desaparecen
  quince y quedan tres (`/vincular`, `/mascota`, `/huevo`).
- En cada canal de información edita la primera página del manual y **borra
  las otras siete**. Si le falta permiso o el canal no está, deja un aviso en el
  registro y sigue; lo reintenta al reconectar. Un segundo arranque no toca el
  canal.
- Qué mirar en el registro tras arrancar: una línea de comandos sincronizados
  por cada servidor y una de «Manual al día» por cada canal de información. Si
  la sincronización de un servidor falla, allí siguen registrados los comandos
  viejos, que contestan el aviso hasta que un arranque sincronice bien. Si falta
  permiso o el bot no ve el canal, ese canal conserva el manual viejo hasta que
  se arregle y el bot reconecte.
- El bot sólo borra las páginas que tiene apuntadas en los canales de
  información configurados: si el manual estuvo en un canal que ya no está en
  esa lista, esas páginas se borran a mano.
- Si se corta a medias de los borrados, el reintento sigue donde quedó.
- Los botones de todos los mensajes viejos siguen en Discord; al pulsarlos
  contestan el aviso.
- La unidad `tamagotchi.service` y los guiones de despliegue no cambian: el bot
  sigue siendo el mismo servicio, y sigue haciendo falta su token y su canal.
- La variable nueva `URL_GACHAMON` es opcional: sin ella, el aviso apunta a la
  dirección pública de la página.

### Si hubiera que volver atrás

- Al arrancar, el bot de antes vuelve a registrar sus comandos y a publicar su
  manual: la primera página la edita en su sitio y las otras siete las publica
  de nuevo, debajo de lo que haya en el canal, porque sus mensajes ya no
  existen. Si alguien escribió entre medias, esas siete quedan después de lo
  suyo; se arregla borrando las ocho a mano y reiniciando.
- Los botones de las fichas viejas vuelven a funcionar.
- Los avisos que se contestaron a las menciones se quedan en el canal: hay que
  borrarlos a mano.
- Quien vinculó sigue vinculado. Este plan no necesita restaurar la base.

### Pendiente

- **Reglas que se quedaron sin pantalla**, esperando la suya en la página:
  las aventuras y reclutar (`aventura.py`, `economia.ejecutar_viaje`,
  `otorgar_hallazgo`), competir (`competir.py`, `economia.ejecutar_competencia`),
  conversar (`ia.py`, `economia.aprender_hablando`, la conversación y el uso de
  la IA en `db.py`), el ranking y el cementerio (`db.ranking`, `db.cementerio`).
  Hasta entonces no se puede hacer nada de eso en ningún sitio. Si conviene
  adelantar las aventuras y reclutar en la página está por decidir.
- **Reglas que cambia o cierra el plan de la vivienda:** las casas, mudar,
  amueblar, el huerto y cocinar (ya sin menú que las alcance), y el buzón, cuyos
  regalos pendientes ese plan entrega solos el día del cambio.
  - A la intemperie con casa propia, el aviso manda a comprar una casa más
    grande, pero **mejorar** una casa no mete dentro al que está fuera (sólo
    comprar otra lo recoge) y mudar no tiene pantalla en la página. Ese plan no
    debe heredar la trampa.
- `pantalla.py` sigue en el repo porque `aventura.py` y `competir.py` arman con
  él sus textos; las fichas de texto que también dibujaba ya no las usa nadie.
- Los campos `pantalla_msg_id` y `canal_id` de cada gachamon, y el parámetro
  `canal_id` al nacer y al reclutar, quedaron sin uso: quitarlos toca la
  función que escribe cada fila, y se dejó para más adelante.
- El tope de 25 gachamones existía por los menús de Discord; se va con el plan
  de la vivienda, que lo cambia por las camas.
- Las claves de la IA siguen en la configuración, sin uso mientras conversar
  esté en pausa.
- Los mensajes de reclutas ya publicados en Discord siguen diciendo que no
  tienen nombre, y sus botones ahora contestan el aviso: que la carta del
  alcalde le cuente a cada quien cómo se llama su recluta pesa más que antes.
- **Por decidir (de producto, lo decide el dueño):**
  - La mochila de la página deja gastar pociones de fuerza y de velocidad y
    sopaipillas, que hoy no sirven en ningún sitio.
  - Quien ya tiene plantel propio en la página no puede vincular, y su plantel
    de Discord queda guardado sin dónde jugarlo.
  - El aviso le explica cómo vincular también a quien ya vinculó.
  - La descripción de las golosinas anuncia la aventura.
  - Frases y textos en código en pausa que nombran comandos que ya no existen.

### Pruebas

- Con los adaptadores de Discord se fueron sus pruebas; las reglas a las que
  sólo se llegaba por un menú se probaron de nuevo llamándolas directamente.
- La prueba que vigila que no se fue ninguna tabla ni columna
  (`tests/test_mudanza.py::test_no_se_fue_ninguna_tabla_ni_columna`) hay que
  cambiarla a propósito si el plan de la vivienda quita la tabla del buzón.
- Sigue sin haber prueba de que cuidar, viajar y competir se revierten enteras
  cuando falla el libro. Es de antes; conviene cerrarla en el plan de la
  vivienda, que toca dinero.
- Al borrar, medir la cobertura **por ramas y en las dos puntas del plan
  entero**, no por líneas ni sólo en la tarea que más borra. Así se escaparon el
  modo sin dibujo de las fichas y la subida de nivel que hace crecer algo,
  repuestas las dos.

## Para el plan 6 (tu casa)

> El rediseño del 2026-11-14 cambió el rumbo: lo que sigue se replantea en docs/superpowers/specs/2026-11-14-gachamon-rework-1-departamento-design.md.

- Elegir casa al comprar un mueble, colocar y retirar. Un mueble comprado en la
  web va a la primera casa. Los rechazos propios de `colocar_mueble` («No
  tienes», «ya está puesto», «No cabe») y de `retirar_mueble` («no está puesto»)
  todavía no dan `motivo`.
- El huerto; con él, la semilla deja de ser «más adelante».
- Los muebles dibujados dentro de la casa: el contrato de arte (`web/arte.py`,
  `docs/arte/contrato.md`) gana ese arte.
- En «Tu casa» sin casa propia el gachamon no dice frases del lugar (sólo su
  charla de siempre). Si se quieren frases propias para ese caso, son texto
  nuevo por decidir.

## Para el plan 7 (hablar y la apertura)

> El rediseño del 2026-11-14 cambió el rumbo: lo que sigue se replantea en docs/superpowers/specs/2026-11-14-gachamon-rework-1-departamento-design.md.

- Hablar: la navegación del lugar lo gana (hoy sólo están «Pueblo», la tienda y
  la mochila).
- Hay frases que caducan al abrir un lugar (`globos.py`), y hay que cambiarlas
  en la misma tarea que lo abra:
  - Las que presuponen lugares vacíos: el eco de la plaza y del estadio, y «Qué
    tranquilo está el barrio.».
  - De la tienda, que ya abrió, quedan dudosas las de «madera y pintura
    fresca».
- «Me gustan estos faroles.» (barrio) presupone un dibujo con faroles: depende
  del arte definitivo del barrio. «Aquí da el sol a todas horas.» sería falsa si
  un día hay noche.

## Para el proyecto 2 (notificaciones)

- ~~**Cerrar la excepción de la muerte por hambre pide dos cosas.** Cambiar `identidad.sin_aviso_de_hambre` y, además, poner al día el reloj de quien sale de ella: un gachamon que lleve días en 0 no puede morir en el siguiente `avanzar` con una fecha de muerte en el pasado (diseño, 5.8, «Termina»).~~
  **Resuelto en el rework 1: ya nadie muere.**

## Detalles que se dejaron como están

- `/vincular` sale en el manual de todos los servidores, aunque sólo funciona
  en el que hace de pueblo. Hoy hay un solo servidor activo.
- `db.canjear_codigo_de_vinculo` lanza si el código trae un carácter suelto de
  un par sustituto de Unicode. Discord no entrega esa entrada; endurecerlo
  cuando la web empiece a llamar a esa función o a otra parecida.
- `intentos_de_vinculo` sólo se limpia para quien vuelve a intentar.
