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
- Durante un despliegue, mientras corre la suite en la Pi, la web vieja sirve
  los archivos estáticos nuevos. Se cierra probando en un árbol aparte antes de
  cambiar el de producción.
- `globos.elegir` no lo usa nadie en el servidor: la regla vive otra vez en
  `tiempo.js`.

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
