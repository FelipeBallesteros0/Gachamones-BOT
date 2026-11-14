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
- La web deja apuntada cada muerte que registra (tabla `muertes_por_anunciar`) y
  el bucle del bot la anuncia en su siguiente vuelta, hasta quince minutos
  después.
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
- `Mascota._avisar_hambrientas` lee la lista, espera envíos a Discord y guarda
  la fila entera: con la web escribiendo a la vez, un cuidado hecho en esos
  segundos se pisaría. Bastaría un `UPDATE` sólo de `avisada`.
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
  reintentar; quien la abre en ese rato no recibe la portada. Si el despliegue
  se corta por otra cosa (se cae la conexión, falla `pip`), la web se queda
  parada hasta el siguiente despliegue o hasta arrancarla a mano.
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
- Una muerte que descubra `usar_objeto` se guarda, pero no queda apuntada para
  que el bot la anuncie (igual que en los cuidados): en la web la ruta ya pasa
  antes por la comprobación que sí la apunta.
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
  desde Discord, una muerte que leyó otra pestaña), el cuidado le cae al relevo.
  La mochila lo cerró mandando el gachamon que enseña la pantalla.
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
  «Nombre no válido. Ese es el nombre de su especie. Ponle uno propio.», y
  elegir en el menú del plantel a una activa que ya había muerto sin registrar
  registra su muerte y contesta «Ese gachamon no es tuyo o ya no está.».

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

### Pruebas

- La ayuda de pruebas `con_gachamon` rompe el huevo con azar real: si sale una
  especie rara, nacer paga una medalla de 20 gemas. Se arregló la prueba de la
  tienda que fallaba por eso, fijando la especie, pero la causa sigue en la
  ayuda.
- Faltan pruebas de: una medalla «tuya» con progreso en la ficha; el ropero con
  títulos en «ya lo lleva», «lo lleva otro» y «ya no lo tienes»; y que mirar el
  Refugio no crea la fila del hogar. También una ayuda de pruebas
  (`vinculada_sin_gachamon`) repite pasos de otras.

## Para el plan 6 (tu casa)

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

- **Cerrar la excepción de la muerte por hambre pide dos cosas.** Cambiar
  `identidad.sin_aviso_de_hambre` y, además, poner al día el reloj de quien
  sale de ella: un gachamon que lleve días en 0 no puede morir en el siguiente
  `avanzar` con una fecha de muerte en el pasado (diseño, 5.8, «Termina»).

## Detalles que se dejaron como están

- `/vincular` sale en el manual de todos los servidores, aunque sólo funciona
  en el que hace de pueblo. Hoy hay un solo servidor activo.
- `db.canjear_codigo_de_vinculo` lanza si el código trae un carácter suelto de
  un par sustituto de Unicode. Discord no entrega esa entrada; endurecerlo
  cuando la web empiece a llamar a esa función o a otra parecida.
- `intentos_de_vinculo` sólo se limpia para quien vuelve a intentar.
