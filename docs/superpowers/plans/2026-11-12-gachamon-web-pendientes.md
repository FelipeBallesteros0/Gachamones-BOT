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

- Mientras la suite corre en la Pi durante un despliegue, la web vieja sirve
  los archivos estáticos nuevos: quien cargue la página en esos minutos recibe
  el cliente nuevo con el servidor viejo, y si el cliente nuevo espera algo que
  el servidor viejo no manda, ve la pantalla de «no carga» hasta el reinicio.
  Es del guion de despliegue, no del juego: se cierra probando en un árbol aparte
  antes de cambiar el de producción.

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

## Para el plan 4 (los lugares y la apertura)

- Los avisos de «abre pronto» de la incubadora y la tienda se quitan cambiando
  `abre` a `ya` en `web/static/datos/pueblo.json`.
- Hay frases que caducan al abrir un lugar (`globos.py`), y hay que cambiarlas
  en la misma tarea que lo abra:
  - Tienda: «Los estantes están vacíos todavía.», «Dicen que abrirá pronto.» y
    la del pollito «Pío, los estantes están vacíos.»; quedan dudosas las de
    «madera y pintura fresca».
  - Incubadora: «Todo está quietito, como si durmiera.».
  - Las que presuponen lugares vacíos: el eco de la plaza y del estadio, y «Qué
    tranquilo está el barrio.».
- «Me gustan estos faroles.» (barrio) presupone un dibujo con faroles: depende
  del arte definitivo del barrio. «Aquí da el sol a todas horas.» sería falsa si
  un día hay noche.
- La navegación del lugar gana la mochila y hablar (hoy sólo está «Pueblo»).
- El contrato de arte (`web/arte.py`, `docs/arte/contrato.md`) gana los íconos y
  los muebles.
- En «Tu casa» sin casa propia el gachamon no dice frases del lugar (sólo su
  charla de siempre). Si se quieren frases propias para ese caso, son texto
  nuevo por decidir.
- Quien tiene casa pero su gachamon activo no cabe en ella y agotó la estancia
  del refugio lee en el Refugio «Las casas se compran en la tienda.», que para
  él debería hablar de mudarlo o de una casa más grande.
- Los estáticos versionados no llevan `Cache-Control` propio; con uno
  inmutable, el mapa no repetiría sus peticiones en cada visita.
- El contrato de arte tiene dos efectos que el juego todavía no dibuja (el
  corazón y la estrella).

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
