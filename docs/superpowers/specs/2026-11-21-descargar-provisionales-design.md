# Descargar los provisionales y lo subido — diseño corto

## Para qué

El dibujante necesita los provisionales a tamaño real para guiarse al dibujar
cada pieza, y poder bajar también las imágenes ya subidas. Hoy la página del
dibujante sólo los enseña en miniatura y sólo baja un zip con lo subido.

## Lo que decidió el dueño (2026-11-21)

- Por pieza y todos juntos: cada pieza gana «Descargar el provisional», y arriba
  «Descargar los provisionales» baja un zip con todos, en carpetas por grupo.
- Cada provisional baja como PNG en la medida exacta que pide su pieza, también
  los muebles del departamento (la familia `pieza`): un solo tamaño para todo lo
  que toca el dibujante, y lo que sube sólo vale a esa medida.
- «Que también pueda descargar los otros dibujos que no son placeholders»: cada
  pieza con una imagen subida gana «Descargar la imagen subida».
- Siempre baja el provisional del repo, aunque la pieza tenga una imagen subida.
- Sólo con el permiso del dibujante.

## Enfoques

- **Rutas del servidor para los provisionales (elegido):** un solo lugar decide
  el nombre del archivo, y el zip se arma
  como el de lo subido.
- **Enlaces directos a los archivos del juego:** no pueden dar un zip ni el nombre de cada descarga.
- La imagen subida ya tiene dirección propia: su botón es un enlace de descarga
  a ella, sin ruta nueva.

## Cómo es

- `GET /monsteropolis_dibujante/api/provisional?ruta=…`: el PNG del provisional
  de esa pieza, como descarga: el archivo del repo, tal cual y en su medida
  exacta, también en la familia `pieza`.
- `GET /monsteropolis_dibujante/api/provisionales.zip`: todos, cada uno en la
  carpeta de su grupo.
- Las dos, sólo con el permiso (a los demás, el 404 de siempre) y sin caché.
- En la página: los botones nuevos por pieza y el de arriba, junto a
  «Descargar lo que se ve».

## Lo que no entra

- Cambiar el historial o lo que ve quien juega. Lo ya subido antes (guardado a
  la medida exacta) sigue viéndose igual.

## Una sola medida

La familia `pieza` deja de aceptar el doble al subir: un PNG al doble se
rechaza con la frase de medida de siempre, que nombra una sola. La página ya no
anuncia el doble. Los originales de `fuentes/pieza/` y su herramienta de
reducción no cambian: son los originales del repo.

## Para publicar

Va en la rama de la página congelada y se despliega con el permiso del dueño.
