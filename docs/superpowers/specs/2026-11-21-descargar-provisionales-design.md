# Descargar los provisionales y lo subido — diseño corto

## Para qué

El dibujante necesita los provisionales a tamaño real para guiarse al dibujar
cada pieza, y poder bajar también las imágenes ya subidas. Hoy la página del
dibujante sólo los enseña en miniatura y sólo baja un zip con lo subido.

## Lo que decidió el dueño (2026-11-21)

- Por pieza y todos juntos: cada pieza gana «Descargar el provisional», y arriba
  «Descargar los provisionales» baja un zip con todos, en carpetas por grupo.
- Cada provisional baja como PNG en la medida exacta que pide su pieza; los
  muebles del departamento (la familia `pieza`), al doble.
- «Que también pueda descargar los otros dibujos que no son placeholders»: cada
  pieza con una imagen subida gana «Descargar la imagen subida».
- Siempre baja el provisional del repo, aunque la pieza tenga una imagen subida.
- Sólo con el permiso del dibujante.

## Enfoques

- **Rutas del servidor para los provisionales (elegido):** un solo lugar decide
  la medida (el doble en los muebles) y el nombre del archivo, y el zip se arma
  como el de lo subido.
- **Enlaces directos a los archivos del juego:** no pueden dar el doble ni un zip.
- La imagen subida ya tiene dirección propia: su botón es un enlace de descarga
  a ella, sin ruta nueva.

## Cómo es

- `GET /monsteropolis_dibujante/api/provisional?ruta=…`: el PNG del provisional
  de esa pieza, como descarga. En la familia `pieza`, ampliado al doble sin
  suavizar: es una guía para dibujar encima, y subido tal cual se acepta y se
  reduce a la medida de la pieza (sin prometer los mismos píxeles).
- `GET /monsteropolis_dibujante/api/provisionales.zip`: todos, cada uno en la
  carpeta de su grupo.
- Las dos, sólo con el permiso (a los demás, el 404 de siempre) y sin caché.
- En la página: los botones nuevos por pieza y el de arriba, junto a
  «Descargar lo que se ve».

## Lo que no entra

- Cambiar medidas, el historial o lo que ve quien juega.

## Para publicar

Va en la rama de la página congelada y se despliega con el permiso del dueño.
