# Gachamon web — pendientes que dejó el plan 1

Lo que el plan 1 («reglas y bot») encontró y no le tocaba arreglar. Quien
escriba el plan 2 o el proyecto 2 parte de aquí.

## Para el plan 2 (servidor web y pantalla principal)

- **Crear un gachamon y mirar la cuenta, en la misma transacción.**
  `db.crear` no consulta `cuentas_web`. Si la web resuelve `db.cuenta_web()`
  fuera de la transacción en la que crea la criatura, puede nacer un gachamon
  de la identidad web justo después de vincular, y queda huérfano.
- **«Sin gachamones» no es «sin estado».** Al vincular, una identidad web
  vacía de gachamones puede haber dejado un monedero, un reloj del refugio o
  una compra. Esas filas quedan huérfanas. Decidir si la web impide llegar a
  ese punto o si se limpian.
- **El código de vinculación se puede pedir con engaños.** Quien convenza a
  otra persona de escribir su código en Discord se queda con los gachamones de
  esa persona en la web. Avisarlo donde la web muestra el código y en la
  descripción de `/vincular`.
- **«Desfallecido».** Con la comida en 0, la ficha y los globos tienen que
  decir que el gachamon está desfallecido y pide comer (diseño, 5.8).
- **La secuencia de arranque vive en `bot.py`.** `db.inicializar()` seguido de
  `economia.devolver_cosmeticos_retirados()` está escrito dentro de un módulo
  que importa `discord`. El servicio web necesita lo mismo: sacarlo a una
  función sin Discord y probarla.
- **La prueba del reintento por colisión.** Ninguna prueba pasa `rng` a
  `db.pedir_codigo_de_vinculo`; añadirla cuando la web empiece a llamarla.
- **La regla por ruta del túnel sólo se comprobó en seco.** Aplicarla pide
  `sudo`, reiniciar el túnel y la autorización de Felipe. Ver
  `../specs/2026-11-12-tunel-regla-por-ruta.md`.

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
