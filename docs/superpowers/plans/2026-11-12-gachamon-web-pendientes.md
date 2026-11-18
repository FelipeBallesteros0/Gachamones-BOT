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
  (Cambiado por el rework 6: el huevo ya no existe y sin gachamon la página
  funciona; comprar un mueble ya no pide gachamon, y para un objeto o un
  cosmético la pantalla lee la frase del servidor y se queda donde está.)
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
  (Rework 6: ya no hay huevo; el remiendo corre ahora también al ganar al
  primero en la primera aventura.)
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
  (Resuelto en el rework 6: sin huevo, y quien empieza después del día del
  cambio parte con 0 y 0.)
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
- **Decidido por el dueño tras el rework 4:** la mochila de la página ya no
  deja usar ni gasta las pociones de fuerza, de velocidad y de descanso rápido
  ni las sopaipillas, y dice lo mismo que la Tienda («Sirve en las
  competencias, que todavía no están en la página.»); el cuidado de aseo se
  llama «Bañar»; los textos de la semilla, los porotos y la nota de la mochila
  dicen que el huerto vuelve más adelante.
- **Por decidir (de producto, lo decide el dueño):**
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

## Salió al ejecutar el rework 4 (la vivienda por casillas)

### Lo decidido

- Cada persona tiene un solo departamento por servidor: parte en 3 × 3 y se
  amplía por una fila o una columna, a 15 monedas por casilla, hasta 8 × 8.
  Ampliar se compra estando en tu departamento; lo demás, en la Tienda.
- Los muebles ocupan casillas, giran en cuatro posiciones, puede haber varios
  iguales, y están puestos o guardados; guardar nunca destruye. Lo que se
  compra llega a guardados. El felpudo y la alfombra se pisan y admiten un
  mueble encima; los cuadros, las cortinas y el ventanal van en una de las dos
  paredes del fondo. El catálogo y sus formas viven en `departamento.py`, que
  es puro, y el servidor manda sobre qué mueble hay en qué casilla.
- Hacen falta tantas camas puestas como gachamones vivos más una, la tuya:
  reclutar pide una cama libre y la cama que hace falta no se guarda. Ya no hay
  tope de 25: el límite son las camas, es decir, las casillas. Hay una cama
  nueva, la sencilla, a 85 monedas.
- La comodidad parte de 80, cada tipo de mueble puesto suma una vez y el tope
  depende de las casillas (100 en 3 × 3, 150 en 8 × 8). Frena el ánimo de todos
  los que viven ahí, como antes, y no toca el hambre.
- El ritmo del tiempo sale del departamento. Antes de cambiar lo que lo fija
  (poner o guardar un mueble, ampliar) se pone al día y se guarda a todos los
  gachamones vivos de esa persona, en la misma transacción.
- Se fueron las casas compradas, el refugio y su plazo, la intemperie, mudar, el
  huerto por casa (plantar, regar, cosechar), el ticket del refugio y abrir o
  cerrar la casa a las visitas. La semilla ya no se vende ni sale de botín; las
  que alguien tenga se quedan. Cocinar y el buzón siguen en el código, en pausa.
- No se borró ninguna tabla ni columna: `casas_propias`, `mobiliario`,
  `huerto`, `hogar`, `buzon` y `criaturas.casa_id` siguen en el esquema, sin
  uso, y la migración vieja de las casas sigue corriendo para que una base
  antigua pueda llegar hasta el día del cambio.
- El plan se partió en dos: «partir sin gachamon» (sin huevo, el monedero en 0,
  la primera aventura, y que todo funcione sin ningún gachamon) es el plan que
  sigue. Aclaración del dueño: sólo parte con 0 monedas y 0 gemas quien empiece
  después del día del cambio; quien ya jugaba, también quien viene de Discord,
  conserva las suyas.
- «Dónde estás» se resuelve en un solo sitio (`web/pueblo.donde_esta`): el
  lugar guardado o, si falta o ya no existe, tu casa. Lo usan el estado y los
  tres «para eso tienes que estar ahí» (la Tienda, sacar de la Incubadora y el
  departamento). Ver el plantel de la Incubadora no pide estar en ella; sacar a
  uno, sí.

### El día del cambio

- Corre una sola vez, al arrancar (lo hace quien arranque primero, el bot o la
  web), con su marca en `cambios_hechos` y todo dentro de una sola transacción:
  o se hace entero o no se hace nada.
- A cada persona que ya existía: se le entregan los regalos que esperaban en el
  buzón; se le cosecha lo plantado como si estuviera maduro; cada ticket del
  refugio le vuelve en 40 monedas (también el que acaba de llegar del buzón);
  cada casa le vuelve al precio de catálogo de la casa que es ese día (una
  mejorada vuelve como lo que es ahora), y a la mediana y a la grande se les
  suman 140 monedas más (lo decidió el dueño: ver «Lo decidido» del rework 5, más
  abajo en este documento); se le crea su departamento del primer
  tamaño de la serie en que quepan sus camas, con una cama puesta por cada
  gachamon vivo más la suya; a quien no tiene ninguno vivo, su cama puesta y
  otra guardada; sus muebles de antes pasan a guardados; y se le deja su
  monedero creado, con lo que tenía.
- El reloj de todos los gachamones vivos parte de ese momento: a ninguno se le
  cobra el tiempo desde la última vez que se guardó.
- Las devoluciones no pasan por el tope diario ni por el libro de operaciones.
- Decidido por el dueño: el día del cambio cada casa mediana o grande devuelve
  140 monedas más que su precio de catálogo (pequeña 200, mediana 640, grande
  1340). La carta dice «por tu ticket» cuando era uno, y la especie de cada
  recluta va con su mayúscula.
- Las filas ya convertidas (las casas, los muebles de antes, lo plantado) se
  borran, para que nada valga dos veces.
- A cada persona le queda escrita una carta del alcalde, que la página enseña
  una vez (`GET /carta`, `POST /carta/vista`, y el campo `carta` del estado).
  Quien empieza después del cambio no tiene carta.

### Al publicar

- **Antes de publicar**: tomar la copia de la base y guardarla aparte, fuera de
  la rotación. Y ensayar el cambio sobre una copia de la base de producción
  (con permiso expreso del dueño): si alguna tabla muy vieja guardara los
  identificadores con otro tipo, una misma persona saldría dos veces y el
  cambio entero se desharía.
- **Parar los dos servicios antes de sacar la copia.** El guion de
  actualización saca su copia al principio, con el bot de antes todavía en
  marcha, y copiar una base en uso no garantiza una copia sana. Para este
  despliegue: parar el bot y la web, copiar, guardar la copia fuera de la
  rotación, y recién entonces actualizar.
- Qué mirar al ensayarlo sobre una copia: las monedas devueltas son la suma de
  los precios de catálogo de las casas, más 140 por cada casa mediana o grande,
  más 40 por ticket (los de las mochilas y
  los del buzón sin recoger); las tablas de casas, muebles de antes y huerto
  quedan vacías; hay tantos departamentos y cartas como personas; nadie tiene
  menos monedas ni gemas que antes.
- Qué mirar en el registro tras arrancar: una línea del día del cambio con tres
  cifras (a cuántas personas tocó, cuántas camas regaló, cuántas monedas
  devolvió). Sale una sola vez, y queda en el registro la escriba el bot o la
  web: va como aviso, para que salga también en la web. La otra prueba de que
  el cambio corrió es la marca `la_vivienda_por_casillas` en `cambios_hechos` y
  que haya tantas cartas como personas.
- En ese mismo arranque corren antes, y en otra transacción, los cambios de los
  planes anteriores (nadie muere, el tiempo para todos, los nombres de los
  reclutas): si el día del cambio se detuviera, ésos ya quedaron hechos, y la
  vuelta atrás sigue siendo la copia.
- Si al arrancar ya hubiera departamentos sin la marca del cambio (no debería:
  sólo pasa en una base de desarrollo de esta rama, si alguien borra la marca
  para repetirlo, o con una base restaurada a medias), el cambio no hace nada y
  el arranque se detiene. Es a propósito: ahí lo seguro es no tocar nada y que
  se note, con la copia intacta. No se convirtió nada y no hay marca que
  borrar; el mensaje del error lo dice. Los servicios lo reintentan solos cada
  pocos segundos: es inofensivo, pero llena el registro.
- Quien jugaba sólo en Discord ve su carta cuando vincula, no antes. Quien ya
  había abierto la página sin vincular ve dos: la de su identidad web y, al
  vincular, la suya.

### Si hubiera que volver atrás

- **La única vuelta limpia es restaurar la copia de antes.** El cambio borra las
  casas, los muebles de antes y lo plantado, y paga las devoluciones: arrancar
  el código de antes sobre la base ya cambiada dejaría a la gente sin casas y
  con las monedas.
- La vuelta atrás es **la copia y el código de antes, las dos cosas juntas**.
  Si el guion de actualización falla *después* del reinicio (la base ya está
  convertida), no hay que volver al commit anterior a mano sin restaurar la
  copia.
- La segunda trampa de toda marca: si se restaura la base a medias, o se borra
  la marca a mano sobre una base ya convertida, el cambio se detiene sin hacer
  nada (ver arriba) en vez de repetirse.
- Lo que la gente haya hecho después del cambio (comprar muebles, ampliar,
  colocar) se pierde al restaurar.
- Siguen valiendo las recetas de vuelta atrás de los planes anteriores (la de la
  comida, la de la marca del tiempo para todos).

### Pendiente

- **Partir sin gachamon** (el plan siguiente): el huevo sigue existiendo y el
  que nace de él no pide cama; el monedero de quien empieza sigue naciendo con
  lo de hoy; comprar en la Tienda, usar la mochila y abrir el ropero siguen
  pidiendo un gachamon. (Hecho en el rework 6; mira abajo cómo quedó: sin
  huevo, el primero pide cama, el monedero de quien empieza nace en 0, y comprar
  muebles ya no pide gachamon.) Quien sólo tenía un regalo en el buzón y nunca jugó
  recibió también su monedero el día del cambio: cuenta como alguien que ya
  estaba.
  - Cuando el huevo se vaya, quitar el «nunca menos que los que ya tiene» de lo
    que caben en la Incubadora. (Hecho en el rework 6: se quitó.)
  - Vincular después de haber amueblado deja atrás el departamento de la
    identidad web. Hoy apenas pesa; cuando se empiece amueblando, pesará.
    (Rework 6: el dueño decidió dejarlo como está; ver abajo.)
- ~~**El departamento en pantalla**: no hay pantalla todavía; las rutas están
  (`/departamento`, poner, guardar, ampliar) y la carta también.~~ Hecho en el
  rework 5 (ver «Salió al ejecutar el rework 5», más abajo): la pantalla existe
  y todo lo que vende la Tienda ya se puede poner. Cambiar de activo se hace
  ahora también desde el departamento; la Incubadora sigue sirviendo para lo
  mismo hasta el plan del pueblo, y dice cuántos caben por las camas.
- **El pueblo**: el lugar «Refugio» sigue en el mapa, cerrado y con su aviso, y
  «Tu casa» todavía no se llama «Tu departamento».
  - La Incubadora dice «Caben 1 gachamones.» cuando cabe uno (antes siempre
    eran 25); se va con esa pantalla.
- **Las aventuras y reclutar** siguen sin pantalla. Cuando vuelvan, el «hay
  sitio para un recluta» tiene que salir de las camas (`db.hay_cama_libre`).
- **El huerto** está cerrado hasta el balcón. Los textos de la semilla y de los
  porotos todavía hablan de sembrar («Se planta en el huerto de tu casa», «Se
  usa en el huerto.», «Y se puede sembrar»): son frases de jugador y las decide
  el dueño.
- Las tablas viejas sin uso, `criaturas.casa_id`, `sim.Criatura.casa_id` y el
  suelo de hambre de `sim.Ritmo` siguen ahí.
- En la carta, el nombre de la especie de un recluta sale en minúsculas («Tu
  octopul ahora se llama…»): si se prefiere con mayúscula es una palabra.
- **Por decidir (de producto, lo decide el dueño):**
  - Una casa **mejorada** costó más de lo que vuelve: se devuelve el precio de
    catálogo de la casa de hoy, y mejorar cobraba el precio nuevo menos el 80 %
    de la vieja; hasta 140 monedas de diferencia por casa.
  - La comodidad de todos queda en 82 hasta que cada quien ponga sus muebles, y
    el tope ahora depende de las casillas.
  - El reloj de todos parte del día del cambio, que es más generoso que «con la
    comida en 0».
  - La carta dice «por tus tickets» también cuando era uno.

### Pruebas

- Con las reglas de antes se fueron sus pruebas; las de cocinar y las del buzón
  se mudaron a archivos propios.
- Al borrar se midió la cobertura por ramas en las dos puntas; la medición tuvo
  que contar por separado las dos salidas de una rama escrita en una sola línea
  (`a or b`), que una medición más gruesa no ve.
- La medición por ramas no ve **datos** (una entrada de una tabla de
  migraciones, una clave de un diccionario): para eso hace falta mutar. Así se
  encontró la migración de «lo sembrado», que se había quedado sin prueba.
- Tres huecos anteriores a este plan, para cuando toque: nada nota que la
  mochila deje de comprobar que el gachamon es el mismo, ni que nacer deje de
  poner al día al activo, y la migración de la columna `activa` no tiene prueba
  sobre una base sin ella.

## Salió al ejecutar el rework 5 (el departamento en pantalla)

### Lo decidido

- **Lo que decidió el dueño:**
  - El día del cambio, cada casa mediana o grande devuelve 140 monedas más que
    su precio de catálogo (640 y 1340); la pequeña, 200. La carta dice «por tu
    ticket» cuando era uno, y la especie del recluta va con su mayúscula.
  - Las pociones de fuerza y de velocidad y las sopaipillas no se usan ni se
    gastan desde la mochila: dicen lo mismo que la Tienda. La poción de
    descanso rápido, igual. El cuidado de aseo se llama «Bañar» en todas
    partes. El huerto cerrado tiene sus frases (la semilla, su nota en la
    mochila y los porotos).
  - Del gachamon que se toca en el departamento se abren sus cuidados y su
    ficha completa; el ropero y la mochila siguen siendo del que sale contigo.
  - El arte de la pieza: la casilla original mide 1024 × 512 y no es pixel art;
    cuatro imágenes por mueble de suelo (NE, NO, SE, SO) y nada se espeja; lo
    de pared, dos, una por pared. Los originales van en `fuentes/pieza/` y la
    página sirve copias a la mitad.
  - En el computador, la pieza a la izquierda; bajo la pieza se ve también la
    comodidad; al poner, mover o guardar bien no sale texto; el tope de 12
    cuidados pagados al día se queda.
  - El orden de los planes cambió: primero la pantalla, después partir sin
    gachamon; y las aventuras y reclutar se adelantan, justo después de este
    proyecto y antes del balcón.
  - Al ver el plan terminado: **ampliar pregunta antes de cobrar**, como la
    Tienda («¿Ampliar por 45 monedas?», con «Ampliar» y «No», y el coste que
    manda el servidor). Salga como salga, tras «Ampliar» la pregunta se cierra;
    «No», Escape y «Volver» también la cierran, y sólo hay una abierta.
  - **Sin camino no se va**: si los muebles cierran el paso hasta la casilla
    tocada, tu avatar se queda donde está, sin decir nada; al mover a un
    gachamon sólo se marcan las casillas a las que tiene camino, y tocar una
    sin camino lo suelta sin moverlo. Con menos movimiento, quien tiene camino
    sigue apareciendo en su destino.
  - Las frases de espera: «Cargando tu departamento…» y «Cargando la carta…».
    La carta tiene su título, «Carta del alcalde», desde el principio; cuando
    llega se pone el que manda el servidor, y si la carga falla se queda.
- **Lo que se decidió al construir** (se puede cambiar):
  - Se toca lo que se ve, con los gachamones primero: a un gachamon siempre se
    le puede tocar, también con un mueble delante; después los muebles, por la
    silueta de su caja; después la pared; después el suelo. Quién tapa a quién
    se calcula por las cajas que ocupan en el suelo.
  - Al llegar un departamento nuevo, quien quedó sobre un mueble o fuera de la
    pieza aparece en la casilla libre más cercana; si no queda ninguna que se
    pise, no se dibuja a nadie en la pieza y se les sigue eligiendo desde la
    lista.
  - Tocar fuera de lo marcado suelta lo que llevas y cierra el menú. Lo que no
    cabe en ningún sitio no entra en la mano («Ahí no cabe.») y todo queda como
    estaba. «Toca la casilla donde lo quieres.» se queda mientras haya algo en
    la mano.
  - La pregunta de ampliar sale debajo del botón de su lado, que sigue a la
    vista con lo que se compra y lo que cuesta (en un 3 × 3 los dos lados
    cuestan lo mismo) y dice si está abierta; tocarlo otra vez la cierra, así
    que un doble clic sobre un lado abre y cierra y no confirma. Si llega una
    pieza que mide o cuesta otra cosa, la pregunta se cierra sola, para no
    cobrar algo distinto de lo que se ve; mientras mida y cueste lo mismo, una
    relectura no la toca ni le vuelve a dar el foco.
  - Los rótulos («Guardados · toca uno y después una casilla», «Ampliar el
    departamento», «A todos») se ven en mayúsculas por estilo, como los demás
    subtítulos. «A todos» enseña una línea por medalla ganada; si varios ganan
    la misma, las líneas salen iguales porque la frase no dice de quién.
  - Sin gachamon, la pantalla del departamento no se va sola al huevo mientras
    estás en casa. (Rework 6: el huevo ya no existe; sin gachamon la guía bajo
    la pieza dice el paso que toca.) Hay una sola petición a la vez en toda la pantalla.
  - Cómo quedó armado el cliente: `casillas.js` (la rejilla) y `proyeccion.js`
    (dónde se pinta cada cosa, quién tapa a quién, qué se tocó) son puros;
    `pieza.js` dibuja; `departamento.js` es la pantalla y habla con el
    servidor; `plantel.js`, `lista.js` y `flotantes.js` arman la ficha, la
    lista para teclado y lector de pantalla y lo que flota sobre la pieza;
    `cuidados.js` es lo que el lugar y el departamento hacen igual con un
    gachamon; `carta.js` es la carta del alcalde.
  - La carta del alcalde se ve al entrar, antes que nada (con avatar), una vez, y
    se cierra con «Entendido».

### Pendiente

- **Partir sin gachamon** (el plan que sigue): la pantalla ya se ve y funciona
  sin ninguno, pero a ella todavía se llega con uno (`siguiente` manda al
  huevo). Quitar la Incubadora de «cuántos caben». (Hecho en el rework 6: a la
  pantalla se llega sin gachamon y sin huevo, y el «nunca menos» de lo que
  caben en la Incubadora se quitó.)
- **El pueblo** (el último plan): la Incubadora sigue sirviendo para cambiar de
  activo, además del departamento, y «Tu casa» todavía no se llama «Tu
  departamento». `escenas/casa.png` sigue en el contrato del arte aunque ya no
  la pinta ninguna pantalla (en tu casa se ve la pieza): se saca con las del
  Refugio y la Incubadora.
- **El arte es de relleno**: cajas de color tan altas como la pared, que tapan
  mucho de la pieza. Con el arte del dibujante no pasará.
  - Lo primero al llegar arte más bajo que su caja: el toque sobre un mueble va
    hoy por la silueta de su caja entera. Con el relleno coincide con lo que se
    ve, pero con un mueble bajo, tocar el aire de encima lo elegiría a él en
    vez de la casilla de atrás. Hay que pasar a mirar lo que se ve del dibujo.
  - Si el arte definitivo pesa demasiado para el teléfono, las copias servidas
    pueden pasar a otro formato sin tocar los originales. Los 57 rellenos de hoy
    pesan menos de 1 MB en total; avisar al dueño si el arte del repo se acerca
    a lo que aguanta la tarjeta de la Pi.
- Si la primera carga de la pantalla falla, dice lo que ya dicen la Tienda y la
  mochila (el mensaje de siempre y «Volver a intentarlo»).
- **Caminar** (el avatar y los gachamones) sólo se ha visto en el arnés, con el
  reloj de cuadros sustituido: falta mirarlo en un navegador de verdad.
- En la pieza, el gachamon no se da vuelta ni titubea al caminar. Cuando la
  pieza queda limitada por el ancho (8 × 8 en el teléfono) se dibuja pegada
  arriba y sobra una franja vacía debajo.
- Mover a mano a un gachamon puede dejarlo en la casilla donde estás tú o donde
  está otro (los paseos sí esquivan a la gente).
- El pegamento de lo que flota sobre la escena (globo, corazones, ganancia,
  celebración, medallas) está en dos sitios: la pantalla del lugar y el
  departamento. Lo que decide qué se dice sí es común (`cuidados.js`).
- `departamento.js` sigue siendo un archivo grande (cerca de 1400 líneas en una
  sola función, con una docena de variables que toca todo). Partirlo es el
  primer paso del plan de los muebles que se usan solos, que va a poner a los
  gachamones a caminar hacia los muebles, y en este orden: primero los que
  caminan (casi puros, se pueden probar sin pantalla), después el transporte
  (mandar, esperar y releer, con sus contadores), la bandeja con lo de
  ampliar, y el menú de lo elegido; la pantalla queda como coordinadora.
- Un retrato que no cargó (un corte de un segundo) no se vuelve a pedir
  mientras se está en la pantalla: ese gachamon queda como su recuadro hasta
  salir y volver. El arte de la pieza sí se vuelve a pedir.
- La bandeja de «Guardados» se alcanza con el teclado, pero su indicación
  («Toca la casilla donde lo quieres.») sólo sirve para el dibujo: con el
  teclado, lo suyo es «Poner» en la lista.
- Tras «Ver ficha» y «Volver», la ficha de la derecha vuelve a ser la del que
  sale contigo, no la del que se estaba mirando (la pantalla se monta de
  nuevo).
- La lista para teclado y lector de pantalla está siempre a la vista, bajo la
  pieza; con «Guardados» vacío dice lo mismo que la bandeja («No queda nada
  guardado.»). Tras un «Guardar» hecho desde el menú del dibujo, el foco va al
  título; lo de volver al mueble vale para lo que se hace desde la lista.
- En la mochila quedan sin camino desde la página las frases de las pociones de
  estadística y las sopaipillas, hasta que vuelvan las competencias.
- Pequeñeces de las revisiones: la ficha con `gachamon_id` pone al día dos
  veces, y `web/mochila.py` importa la Tienda de dos formas.
- Un gachamon al que los muebles dejan sin ninguna casilla con camino: su
  «Mover» dice «Ahí no cabe.», la frase de los muebles (ya pasaba antes, pero
  sólo si no quedaba ninguna otra casilla que se pisara). Si se quiere otra
  frase, o que no se ofrezca «Mover», es del dueño.

### Pruebas

- Pruebas que conviene añadir algún día: `reducir()` con un lote mixto de
  originales; que el relleno es determinista; tocar en la esquina de las dos
  paredes y en 3 × 3 y 8 × 8; salir de la pantalla con un POST en curso; varias
  de la lista.

## Salió al ejecutar el rework 5b (la puerta)

### Lo decidido

- **Lo que decidió el dueño:**
  - La puerta se pidió al probar la pantalla: va en la pared, como las ventanas
    y los cuadros; se puede mover; no se guarda. Es una casilla más, fuera del
    departamento, y es donde apareces al entrar, como en Habbo.
  - La casilla de dentro que queda frente a la puerta se puede tapar con un
    mueble: entonces apareces en la puerta y no pasas hasta moverlo.
  - La casilla de la puerta sólo la pisas tú: los gachamones no.
  - La puerta también sirve para salir al pueblo, además del botón «Pueblo».
  - Sin camino, tu avatar no va (lo decidió ese mismo día, sobre el plan
    anterior): vale también desde la puerta y hacia ella.
  - Se sale desde el menú de la puerta («Mover» y «Salir»): de lo que le
    propuso el plan, esto lo eligió él expresamente. (Cambiado por el modo
    construcción: ahora se sale tocando la puerta; ver el rework 5c.)
  - Pidió meter en este plan un arreglo de «Ampliar»: uno que llega como
    segundo clic de un doble clic no cobra.
- **Lo que el plan propuso y el dueño aprobó** (se le enseñó con el plan):
  - Nace en la pared izquierda, en el tramo de más adelante; el día del cambio,
    en el primer tramo con la entrada libre de lo que dejó el alcalde.
  - No suma comodidad, no se vende y no aparece en «Guardados».
  - Si no hay camino al salir, no se sale y se dice.
  - Las frases: `Puerta`, `🚪 Salir` y `Salir`, `La puerta no se guarda.`,
    `No hay camino hasta la puerta.` (`🚪 Salir` y `Salir` dejaron de usarse con
    el modo construcción: ver el rework 5c.)
- **Lo que se decidió al construir** (se puede cambiar):
  - El día del cambio, si con las camas que deja puestas el alcalde ninguna
    entrada queda libre (pasa con 21 o 24 gachamones vivos), corre la cama que
    la tapa a un sitio de cama que le sobre, y la puerta queda con la entrada
    libre; con los demás planteles todo queda como antes. Lo añadió la revisión
    final, para que se cumpla lo aprobado; en el diseño va como propuesta.
  - La puerta es un mueble más del catálogo, de pared y de un tramo, con su
    marca propia; el cliente la reconoce por esa marca que manda el servidor,
    nunca por su clave.
  - Quien está en la casilla de la puerta se pinta en su umbral (un poco por
    detrás de la línea de la pared), para que se le vea de pie en el vano.
  - Si estabas en la puerta y la mueves, sigues en ella en su sitio nuevo; si
    estabas dentro, no te mueves.
  - La puerta no lleva ícono: no se vende ni se guarda, y ninguna pantalla lo
    pide.
  - El arreglo de «Ampliar» ignora el clic de confirmar que llega como segundo
    (o tercero…) de una ráfaga en el mismo sitio; un clic normal y el teclado
    confirman como siempre. Sólo en la pregunta de ampliar.
  - Tocar otra cosa mientras caminas a la puerta cancela la salida: tocar la
    pieza, tomar algo en la mano o mandar cualquier petición. Elegir a un
    gachamon desde la lista no (tocarlo en el dibujo, sí): diferencia pequeña,
    anotada.

### Lo que sigue (decidido por el dueño, sin plan ni construir)

- **Un modo construcción** para mover muebles, puertas y ventanas, de forma que
  fuera de él un toque sobre un mueble haga su acción (hoy sólo la puerta tiene
  una: salir). Decidido por el dueño el 2026-11-16; tendrá su propio plan y
  cambia la regla del diseño que decía que decorar no tiene modos. (Hecho: ver
  el rework 5c.)

### Pendiente

- **Con la entrada tapada por un mueble alto, la puerta no se puede tocar en el
  dibujo**, y tu avatar, que está en su umbral, queda tapado por ese mueble. Es
  consecuencia de dos cosas aprobadas: que la entrada se puede tapar, y que en el
  dibujo los muebles se tocan antes que la pared (su silueta de toque es tan alta
  como la pared). Se deshace tocando el mueble que estorba y moviéndolo; mientras
  tanto se sale con el botón «Pueblo» o con «Salir» desde la lista. Queda por
  resolver, con el modo construcción. (Resuelto en parte por el modo
  construcción: viviendo, lo que no tiene acción ya no le quita el toque a la
  puerta, y «Salir» ya no está en la lista; el mueble alto que tapa a quien
  está en la puerta sigue pendiente, ver el rework 5c.)
- Un departamento hecho antes de este plan no tiene puerta. En producción no hay
  ninguno: todos nacen el día del cambio o después, ya con ella. La pantalla
  funciona también sin puerta (se entra como antes y no hay «Salir»).
- El dibujo de la puerta es de relleno (un marco con un hueco oscuro y la palabra
  PUERTA).
- Los gachamones no usan la puerta. Visitar el departamento de otra persona y
  entrar por su puerta es del proyecto de la gente en vivo.
- La Tienda usa la misma pieza de pregunta que «Ampliar» y tiene el mismo riesgo
  teórico del doble clic que cae en confirmar; allí no se tocó.
- Buscar el tramo para la puerta da un error claro si todas las paredes tuvieran
  algo colgado; con las reglas de hoy no puede pasar el día del cambio (sólo hay
  camas).
- Un «Ampliar» que se ignora por llegar pegado a otro clic no avisa de nada: si
  confirmas enseguida sin mover el ratón, ese clic no hace nada y hay que
  esperar un momento y volver a tocar. No se pierde dinero.
- El arreglo del doble clic de «Ampliar» no cubre el doble toque de un
  teléfono: ahí cada toque cuenta como un clic suelto, así que el segundo puede
  confirmar. No se ha comprobado en un aparato; a lo sumo confirma una vez,
  nunca dos.
- Qué cancela una salida en curso no es parejo: tocar la pieza, tomar algo en la
  mano o mandar una petición la cancelan, pero abrir «Ampliar», «Guardados» o
  «Mover» de la lista, no (ni elegir a un gachamon desde la lista). Se unifica
  en el modo construcción. (Resuelto por el modo construcción: ahora es una sola
  regla; ver el rework 5c.)
- Al mover la puerta se ofrecen también los tramos con la entrada tapada por un
  mueble; si estabas en la puerta, te vas con ella y quedas detrás de ese
  mueble. El dueño decidió el 2026-11-16 que no se ofrezcan: al moverla sólo se
  marcan los tramos con la entrada libre. Lo hace el plan del modo
  construcción. (Resuelto: ver el rework 5c.)
- Con un 8 × 8 lleno de camas, el alcalde dejaría la entrada tapada: no le
  sobra ningún sitio donde correr la cama. No puede pasar con el tope de 25
  gachamones de antes.

## Salió al ejecutar el rework 5c (el modo construcción)

### Lo decidido

- **Lo que decidió el dueño** (2026-11-16):
  - Lo pidió con la puerta recién puesta en pantalla, para que en el modo
    normal sólo se use la acción de cada mueble y no haya choques como con la
    puerta, que al tocarla podía moverse o salir. Se le recomendó dejarlo para
    más adelante (él mismo había descartado un modo «Decorar» al principio) y
    eligió hacerlo ahora.
  - Hay un modo construcción para mover muebles, puertas y ventanas; en el modo
    normal, un toque sobre un mueble sólo hace su acción.
  - El botón se llama `🔨 Construir` y, dentro del modo, `✔ Listo`.
  - «Guardados» y «Ampliar» están sólo dentro del modo.
  - En el modo normal, tocar la puerta te saca directo: caminas hasta ella y
    sales al pueblo, sin menú; si mientras caminas tocas otra cosa, no sales; si
    ya estás en la puerta, sales al momento.
  - En el modo normal, tocar un mueble sin acción propia no hace nada: no lo
    elige; si se pisa (una alfombra), caminas hasta ahí; y no le quita el toque
    a la puerta cuando está delante de ella.
  - En el modo construcción a los gachamones no se les toca: el toque pasa al
    mueble que tengan detrás. En el modo normal, su menú sigue como hoy («Mover»
    y «Acariciar»).
  - La carta del alcalde nombra el botón: dice que se entra a «Construir».
  - Al mover la puerta sólo se ofrecen los tramos con la entrada libre.
- **Lo que decidió el dueño tras la revisión final** (2026-11-17):
  - Tocar tu propio avatar parado en la puerta te saca: estando en ella, un
    toque sobre ti es un toque en la puerta. Se le preguntó y lo dejó como está
    («Dejarlo como está»).
  - La Tienda nombra «Construir», como la carta: al comprar un mueble dice
    `Compraste {nombre}. Quedó en tus guardados: en tu casa, entra a
    «Construir».`
- **Lo que el plan propuso y el dueño aprobó** (se le enseñó con el plan):
  - Las frases: `Modo construcción`, `Toca un mueble para moverlo, girarlo o
    guardarlo.` y `Modo construcción terminado.` («Apruebo las tres»).
  - Siempre se entra en el modo normal; el modo no se recuerda.
  - El botón va bajo la pieza; en el modo, ahí mismo se lee «Modo construcción»
    y quedan, abiertos mientras dure, la bandeja de guardados y «Ampliar». La
    pieza se enmarca.
  - Tocar el suelo es caminar en los dos modos.
  - En el modo, la puerta trae sólo `✋ Mover`: `🚪 Salir` y `Salir` dejan de
    usarse; se sale tocando la puerta o con «Pueblo».
  - La lista para teclado y lector de pantalla sigue al modo: en el normal trae
    «Tus gachamones»; en el de construcción, además, «Muebles puestos» y
    «Guardados».
  - «✔ Listo» deja todo recogido: suelta lo que lleves en la mano, cierra el
    menú y cierra lo de ampliar, sin cobrar nada.
  - Los cuidados, «A todos», «Mochila» y «Pueblo» siguen en los dos modos.
  - Con una petición en camino no se cambia de modo.
- **Lo que se decidió al construir** (se puede cambiar):
  - Qué recibe un toque en el modo normal lo decide una función pura
    (`proyeccion.queSeUsa`), que no sabe de puertas: la pantalla le dice qué
    mueble tiene acción (hoy, el que trae la marca `puerta`). `queSeToco` es la
    del modo construcción.
  - Un mueble sin acción no deja pasar el toque al suelo que tenga detrás:
    tocarlo no hace nada, ni siquiera caminar.
  - Dónde se ofrece la puerta al moverla lo filtra el cliente
    (`casillas.conLaEntradaLibre`); el servidor sigue aceptando cualquier tramo
    libre.
  - El botón del modo es siempre el mismo nodo (cambia lo que dice), para que el
    foco no se pierda; «✔ Listo» va resaltado. No se puede usar, y lo dice con
    `aria-disabled`, hasta que la pieza está lista para tocarse.
  - El marco del modo es un trazo discontinuo con los colores de aviso del tema.
  - Con algo en la mano (un gachamon que se mueve), el toque sigue siendo el
    sitio adonde va, también en el modo normal: por eso a un gachamon no se le
    puede llevar a la puerta ni se sale sin querer al soltarlo sobre ella.
  - Dentro del modo, bajo la pieza, van por este orden: el botón con «Modo
    construcción», la bandeja de guardados con «Ampliar» y la línea del tamaño.
    En el computador la bandeja y «Ampliar» van lado a lado.
  - Al entrar al modo, la bandeja y «Ampliar» se traen a la vista, sin
    animación, dejando sitio al aviso del pie.
  - Al abrir lo de ampliar, su panel se trae a la vista (en un teléfono se abre
    más abajo que su botón), y al abrirse la pregunta de un lado, la pregunta.
    El sitio que se le deja al aviso del pie sale de una variable del tema,
    pensada para el aviso en dos líneas.
  - Un toque sobre lo que flota (el globo, la evolución, las medallas) no hace
    la acción de un mueble: tocar el globo que queda sobre la puerta no te saca.
    El suelo de debajo se sigue caminando y a un gachamon se le sigue eligiendo.
  - El segundo clic de un doble clic se ignora también en la bandeja y en el
    «Ampliar» que abre el panel, como en el de confirmar: al entrar al modo la
    página se desliza y ese clic caía en lo que quedaba debajo. El «Ampliar» que
    abre el panel dice si está abierto.
  - `ampliar` no manda nada sin su pregunta a la vista: lo de ampliar abierto y
    la pregunta abierta, la de ese lado.
  - Al pulsar el botón del modo el foco acaba en él, siempre.
  - Fuera del modo, las secciones de muebles de la lista se esconden, no se
    destruyen.
  - Qué cancela una salida en curso, una sola regla: cualquier clic fuera de la
    pieza la cancela (también un cuidado que todavía espera), en un solo sitio;
    tocar la pieza también, salvo la propia puerta, y mandar una petición.
    «Ver ficha», «Mochila» y «Pueblo» dejan la pantalla.

### Lo que resolvió de la puerta

- La puerta que no se podía tocar con un mueble delante: en el modo normal, lo
  que no tiene acción ya no le quita el toque.
- Qué cancela una salida ya no es dispar: es la regla de arriba.
- Al mover la puerta ya no se ofrecen los tramos con la entrada tapada.
- Se sale tocando la puerta, no desde su menú; «Salir» ya no está en los menús
  ni en la lista.

### Pendiente

- Quien está en la puerta queda tapado por un mueble alto que tenga delante (se
  pinta detrás); con el arte de relleno, del todo.
- El toque sobre un mueble va por la silueta de su caja, tan alta como la pared,
  y no por lo que se ve de su dibujo: en el modo normal, tocar el suelo que se ve
  detrás de un mueble bajo no hace nada.
- Un gachamon parado delante de la puerta se lleva el toque antes que ella: es
  el orden aprobado (los gachamones primero).
- Hoy la única acción propia de un mueble es la de la puerta. Las demás llegan
  con los muebles que se usan solos y con los objetos para jugar. Cuando
  lleguen: la pantalla trata hoy cualquier acción como la de la puerta, sin
  mirar de qué mueble es.
- Construyendo, la puerta con un mueble justo delante no se puede elegir en el
  dibujo: el toque es del mueble. Se elige en la lista, o moviendo antes el
  mueble.
- El modo no se recuerda entre visitas.
- Lo de «Ampliar» anotado en el rework 5b (un clic ignorado no avisa; el doble
  toque en un teléfono) sigue igual.
- Con la pantalla atrasada (otra pestaña, o la respuesta y la relectura perdidas
  y después el otro lado), ampliar cobra el precio de ahora y no el de la
  pregunta: lo que se manda no lleva lo que mide la pieza ni lo que cuesta. Es
  de antes de este plan.
- Con lo de ampliar abierto no se ven «Mochila» ni «Pueblo» (ya era así).
- La página sólo tiene tema claro: lo nuevo va con las variables de color del
  tema.
- Viviendo y sin gachamones, la lista para teclado queda como una raya suelta.
- Con muchos tipos de mueble guardados, en el computador el último asoma cortado
  junto a «Ampliar» (la fila se desliza).
- Dos pruebas nuevas de la puerta casi repiten dos de antes puestas al día; se
  pueden fundir en una limpieza.

### Pruebas

- Las pruebas de JavaScript se corren con `node --test tests/js/*.test.mjs`: en
  este Node, `node --test tests/js/` falla.

## Salió al ejecutar el rework 6 (partir sin gachamon)

### Lo decidido

- **Lo que decidió el dueño:**
  - Se parte sin gachamon y sin huevo; quien empieza después del día del cambio
    tiene 0 monedas y 0 gemas; quien ya jugaba, también quien viene de Discord,
    conserva lo suyo.
  - El primero se gana en la primera aventura: fija, vas tú solo con tu avatar,
    se une siempre, con un diálogo sin opciones, y se abre cuando ya pusiste la
    segunda cama.
  - La entrada es: avatar, tu departamento (poner la segunda cama), la primera
    aventura y el nombre. El lugar «Aventura» del mapa abre sólo esa aventura, y
    toda la página tiene que funcionar sin ningún gachamon.
  - El primero se sortea entre las diez del huevo, con sus pesos: como el huevo
    de antes («Las 10 del huevo, con sus pesos»).
  - La guía es el paso que toca, bajo la pieza: mientras no tengas gachamon, en
    tu departamento se lee siempre el paso siguiente («El paso que toca, bajo la
    pieza»).
  - El nombre es un campo con un nombre sugerido, que cambias o dejas («Un campo
    con un nombre sugerido»).
  - Los muebles se pueden comprar sin gachamon; los objetos y los cosméticos
    siguen pidiendo uno («Sí, los muebles sí»).
  - Vincular se queda como está («Dejarlo así»): una cuenta web de antes del
    cambio, sin gachamon, que vincula después con una identidad de Discord que
    nunca jugó deja atrás sus 50 monedas y 50 gemas, igual que su departamento.
  - Las medallas de persona ganadas y sin pagar se pagan el día del cambio, una
    sola vez, y la carta lo dice («Pagarlas el día del cambio»; se le
    propusieron tres opciones: pagarlas ese día, dejarlo para más adelante o no
    pagarlas).
- **Lo que el plan propuso y el dueño aprobó** (se le enseñó con el plan:
  «Apruebo, ejecútalo»; las frases, «Apruebo todas»):
  - Quién hace la primera aventura: cualquiera que no tenga ningún gachamon
    vivo. Quien empieza; quien tenía una cuenta con avatar y el huevo sin
    romper; y quien se quedó sin ninguno antes del día del cambio. Estos dos
    últimos conservan sus monedas y sus gemas.
  - Quién «empieza»: aquel cuyo monedero nace después del día del cambio. El día
    del cambio le deja monedero a todo el que ya estaba, así que desde entonces
    monedero nuevo es persona nueva: nace en 0 y 0.
  - La aventura no guarda nada hasta el encuentro: si cierras la página antes,
    empieza de nuevo; si la cierras después, el gachamon ya es tuyo y vuelves al
    paso del nombre.
  - Al terminar vuelves a tu departamento con él, y es el que sale contigo.
  - Sin gachamon: el pueblo y los lugares se ven con tu avatar solo y sin
    cuidados; la mochila se ve; la ficha y el ropero no se abren; la Tienda
    vende muebles.
  - El lugar «Aventura», cuando ya tienes gachamon, sigue diciendo
    `Esto se abre más adelante.`
  - El huevo desaparece de la página. El dibujo del huevo de la pantalla de
    inicio de sesión se queda, como adorno, hasta que haya otro. En Discord,
    `/huevo` sigue siendo el aviso de hoy.
  - El primero necesita cama, como todos: ya no hay ningún gachamon que no la
    pida.
  - Con cuánto nació cada monedero queda anotado en él (una columna nueva), para
    que el reporte de conciliación siga cuadrando.
  - Las frases (letra por letra):
    - La guía, en el departamento, sin cama libre: `Pon tu segunda cama: entra a
      «Construir», tócala en los guardados y después toca una casilla.` Con cama
      libre: `Ya hay cama para un gachamon. Sal al pueblo y ve a «Aventura».`
    - En «Aventura», sin cama libre: `Antes pon tu segunda cama en tu
      departamento: sin cama, nadie se queda contigo.`
    - El título de la pantalla: `La primera aventura`.
    - El diálogo, antes del encuentro: `Sales del pueblo por el sendero. Hoy vas
      tú solo.` · `Entre los matorrales, algo se mueve.` · `No huye. Se queda
      mirándote.` Para avanzar: `Seguir`. Para el encuentro: `Acercarte`.
    - El diálogo, después: `Sale de su escondite: es {especie}.` · `Le tiendes
      la mano. La huele… y se queda a tu lado.` · `Desde hoy vive contigo.`
      Para terminar: `Volver a casa`.
    - Si ya tienes uno: `Ya tienes un gachamon. La primera aventura es sólo la
      de partida.`
    - El nombre: el título `¡Se vino contigo!` y, bajo el campo, `Le puedes
      dejar este nombre o escribir otro.` La etiqueta `¿Cómo se va a llamar?` y
      el botón `Ponerle este nombre` son los de antes.
    - La bienvenida: `🏠 Empezar de cero` y la nota `Si empiezas de cero y un
      gachamon se va contigo, ya no podrás traer los de Discord.`
    - La carta del alcalde, a quien no le queda ninguno: `Te dejé tu cama puesta
      y otra guardada: ponla y ve a «Aventura», que ahí te espera un gachamon.`
  - Las que aprobó después, en la ejecución: `Para eso tienes que estar en la
    aventura.` (lo que contesta la ruta de la primera aventura si no estás en el
    lugar), `Así te verán en el pueblo.` (en la pantalla donde se crea el avatar)
    y `Tenías medallas ganadas y sin cobrar: te pagué {gemas}.` (en la carta del
    alcalde, sólo para quien cobre algo). En las tres eligió entre opciones que
    se le propusieron.
- **Lo que se decidió al construir** (se puede cambiar):
  - Con cuánto se empieza:
    - La marca del día del cambio se escribe al empezar su transacción; por eso
      el día del cambio le dice a las claras a `economia._asegurar_monedero` que
      esa persona ya estaba (50 y 50), y cualquier otro monedero nuevo sigue la
      regla de la marca. La regla y la clave de la marca viven en `db`
      (`db.PARTIDA_DE_UN_MONEDERO_NUEVO`, `db.CAMBIO_DE_LA_VIVIENDA`), porque lo
      que rellena `db` al arrancar tiene que seguir la misma.
    - Cada monedero anota con cuánto nació (`monederos.partida`); el reporte de
      conciliación cuenta con eso, y sobre una base que aún no tiene la columna
      cuenta 50 por monedero.
    - En las pruebas web toda cuenta nueva parte en 0: el servicio corre el día
      del cambio al arrancar, también sobre una base vacía.
  - El primero se gana:
    - Lo crea `nacer.encontrar_al_primero`; nace activo, pidiendo cama y con el
      nombre de su especie (por eso «espera nombre», igual que el del huevo).
    - Qué se ofrece y qué se avisa en «Aventura» depende de la persona y vive en
      `web/pueblo.py`; el dato del lugar en `pueblo.json` no cambió.
    - El nombre sugerido es siempre el mismo para ese gachamon y sólo se manda
      mientras espera nombre.
    - El encuentro te lleva a tu casa; por eso un segundo intento que llega tarde
      (un doble clic, otra pestaña) contesta que no estás en el lugar, y la
      pantalla vuelve a leer el estado.
    - Dos encuentros a la vez dejan un solo gachamon: con la cama justa, al
      segundo lo para la cama; con cama de sobra, el índice de «una sola activa».
  - Retirar el huevo:
    - `db.crear` sigue siendo la primitiva de siempre (las pruebas de reglas la
      usan); lo que ya no existe es ninguna ruta ni función de `nacer` que cree
      un gachamon sin pedir cama. Una prueba recorre el código que no es de
      pruebas para vigilarlo.
    - Comprar un mueble ya no comprueba que tu gachamon activo siga siendo el
      mismo (un mueble es del departamento): cobra su precio una vez, con o sin
      gachamon.
    - El «nunca caben menos que los que ya tienes» de la Incubadora se quitó.
    - Las medallas de la persona se pagan al encontrar al primero. Si ese pago
      se corta y la persona reintenta, se le paga entonces, pero sólo si lo que
      tiene es un único gachamon vivo, sin nombre y nacido después del día del
      cambio (`nacer.es_el_primero_sin_nombre`): quien ya jugaba no cobra nada por
      pedir esa ruta.
    - En las pruebas web, el servicio hace el día del cambio un día antes de la
      fecha de las pruebas, como en producción, donde el cambio es anterior a
      todo.
  - La página sin gachamon:
    - Sin gachamon, la Incubadora se trata como la ficha y el ropero: el botón
      «Tu plantel» no se ve y pedir esa vista deja donde estás.
    - Sin gachamon, si intentas comprar un objeto o un cosmético, o usar algo de
      la mochila, se lee la frase del servidor y te quedas en la pantalla (antes
      te devolvía al lugar sin decir nada). Con gachamon, ese aviso sigue
      queriendo decir que tu gachamon cambió, y se vuelve a decidir.
    - En el lugar, sin gachamon: la escena, tu avatar solo, el aviso del lugar si
      lo tiene y las salidas; sin ficha, sin cuidados y sin globo. En el mapa,
      caminas tú solo.
    - `lugar.js` y `mapa.js` ganaron sus primeras pruebas de JavaScript.
  - La primera aventura en pantalla:
    - El botón que lleva a la aventura desde su lugar dice `La primera aventura`,
      con un ícono de brújula, y sólo se ofrece con la cama puesta; sin ella, el
      lugar dice su aviso.
    - Ante cualquier rechazo del encuentro, la pantalla vuelve a leer el estado:
      si ya tienes al gachamon, pasas al paso del nombre; sólo si sigues sin él
      se lee la frase del servidor, con «Volver».
    - El segundo clic de un doble clic no avanza el diálogo (así no se salta la
      frase que dice qué gachamon es); el teclado y un clic suelto, sí.
    - Mientras carga la aventura se ve el aro de espera de la página (no hay
      frase de carga).
    - Para salir antes del encuentro y para reintentar se usan «Volver» y «Volver
      a intentarlo», que ya existían.
    - La escena de la aventura es la del lugar: el dibujo del fondo y del avatar
      viven en un solo sitio (`lugar.js` los exporta) y las dos pantallas los
      usan.
    - La guía va en una banda justo bajo el dibujo, en los dos modos, y cambia
      sola al poner la cama.
  - Pagar las medallas el día del cambio:
    - El pago va dentro del cambio de cada persona, en su misma transacción,
      después de asegurarle el monedero y de devolverle lo de casas y tickets. La
      lógica vive en un solo sitio (`economia._pagar_logros_de_persona_en`), que
      usan el día del cambio y la ruta de la primera aventura.
    - Cuánto se le pagó queda en lo que guarda su carta (`gemas_por_medallas`).
    - Este pago no queda en el registro de operaciones, igual que cualquier otra
      medalla: queda la medalla anotada y la suma en la carta.
    - Una especie que no esté en el catálogo no cuenta como rara y no tumba nada
      (`logros.hechos_de_la_persona`), la misma regla del resto del arranque.

### Lo que resuelve de lo que dejaron pendiente los planes anteriores

- El huevo en la página y el que nacía de él sin pedir cama: ya no hay huevo, y
  todo gachamon pide cama.
- El monedero de quien empieza: nace en 0 y 0 después del día del cambio.
- «Sin gachamon se va al huevo»: la página funciona sin ningún gachamon. Se ve
  el pueblo, se compran muebles y se ve la mochila; los objetos, los cosméticos,
  la ficha y el ropero siguen pidiendo uno, y lo dicen.
- El «nunca menos» de lo que caben en la Incubadora.
- Las medallas de persona ganadas y sin pagar (la de un recluta, la de diez y la
  de haber tenido una rara): una migración anterior sumó los marcadores pero sólo
  mudó las medallas ya anotadas, y con el bot en pausa ninguna ruta se las pagaba
  a quien ya tenía gachamones. Ahora las paga el día del cambio.

### Lo que queda

- **Para el día de publicar:**
  - **Volver atrás tras el primer arranque exige restaurar la copia de la base,
    no sólo el código**: después del primer arranque con este código, el código
    de antes ya no arranca sobre esa base (no conoce la forma nueva de
    `monederos`).
  - **La conciliación no cuadra tras el día del cambio**, por algo anterior a
    este plan: lo que el cambio devuelve por casas y tickets no queda en el
    registro de operaciones. Cuadra sumándole lo que dicen las cartas del alcalde.
    Hay que resolverlo, o dejarlo dicho en el reporte, antes de publicar.
  - **En el ensayo sobre la copia de la base**, contar quién tiene 21 o 24
    gachamones vivos (el día del cambio corre una cama para dejar la entrada
    libre) y comparar las especies que hay en la base con el catálogo.
- El aviso del arranque (el resumen del cambio) no dice cuántas gemas se pagaron
  por medallas.
- Fuera del arranque quedan sitios que buscan una especie en el catálogo dando
  por hecho que está (la simulación, las aventuras, competir, los retratos…):
  con una especie que se quitara del catálogo fallarían. Hoy no hay ninguna
  quitada.
- Quien sólo tuviera cosas en el ropero y ningún monedero nacería en 0 al
  devolvérsele un cosmético retirado; en producción esa devolución ya corrió y no
  puede darse.
- Si el pago de las medallas del primero se corta y la persona recarga la página
  en vez de reintentar, esa medalla queda sin pagar (la misma ventana que tenía
  el huevo).
- La comprobación «estás en el lugar» está ya copiada en cuatro rutas (tienda,
  incubadora, departamento, aventura).
- La Tienda, sin gachamon, enseña los objetos con su precio activo aunque no se
  puedan comprar; y sus descripciones hablan de «tu gachamon activo».
- El dibujo del huevo sigue en la pantalla de inicio de sesión y en la marca de
  la barra, como adorno.
- El texto alternativo del retrato en el paso del nombre sigue diciendo «Tu
  gachamon recién nacido, …» (no hay frase aprobada).
- No hay frase de carga para la aventura.
- Quien pulse «Seguir» muy rápido pierde el clic repetido.
- Qué se pinta en los lienzos (la escena, el fondo) no lo cubre ninguna prueba de
  JavaScript.
- La Incubadora entera se retira en un plan posterior; hasta entonces, sin
  gachamon, no se abre.

### Pruebas

- Las pruebas de JavaScript se corren con `node --test tests/js/*.test.mjs`: en
  este Node, `node --test tests/js/` falla.

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
