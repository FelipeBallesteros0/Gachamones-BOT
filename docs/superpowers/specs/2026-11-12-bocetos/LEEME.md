# Bocetos del 2026-11-12

Dos bocetos **desechables** que Felipe probó en el navegador mientras se
acordaba el diseño de `../2026-11-12-gachamon-web-parte-a-design.md`. Sirven
para ver cómo se comportan las cosas, no como base del código.

| Archivo | Qué muestra |
|---|---|
| `mapa.html` + `mapa.js` | Las dos formas de llevar el pueblo al celular. Felipe eligió la B, el pueblo ancho que se recorre. |
| `principal.html` + `juego.js` | La pantalla principal: estás en un lugar con tu gachamon en grande, lo acaricias, lo cuidas y sales al pueblo. Usa el motor de `mapa.js`. |

Son fragmentos de HTML pensados para el servidor de bocetos con el que se
mostraron, no páginas completas. Piden las imágenes en `/files/`:
`pollito.png`, `chispa.png`, `slime.png`, `michi.png` y `pedrusco.png` son
retratos armados con `retrato._armar` y reducidos a 96 px de alto;
`pollito_g.png` es el retrato del Piollito adulto a tamaño completo. No se
guardan aquí porque salen de `fuentes/`.

Lo que conviene mirar en el código:

- `mapa.js`: el pueblo descrito como datos (`nodos`, `aristas`, lugares), el
  camino más corto, el cambio de rumbo a mitad de camino, el gachamon que sigue
  el rastro del avatar a una distancia fija, y la cámara que sigue y se
  arrastra.
- `juego.js`: la caricia con enfriamiento, los globos por necesidad y por
  lugar, y el paso del pueblo a la escena de un lugar.

Medido en el boceto B: la caminata más larga dura unos 6 segundos.
