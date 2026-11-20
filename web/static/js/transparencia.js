// Lo transparente de un dibujo no se toca: ¿se ve algo de él en ese punto?
//
// `seVe(imagen, caja, x, y)`: la imagen se pinta estirada en `caja` (`{x, y,
// ancho, alto}`, en las mismas medidas que el punto) y sin suavizar, como los
// retratos, que son dibujos de cuadros. Fuera de la caja no se ve. Dentro, se
// ve si el píxel de su dibujo bajo el punto no es del todo transparente (alfa
// mayor que cero). Sin imagen (no cargó o todavía no llega: se ve su
// recuadro), cuenta la caja entera; y también si sus píxeles no se pueden leer.
//
// Los píxeles de cada imagen se leen una sola vez, en un lienzo que nunca entra
// en la página, y se guardan con ella; si cambia su dibujo (otra dirección), se
// leen otra vez. Las imágenes son de la misma página, así que se pueden leer.

// Imagen → `{fuente, ancho, alto, alfa}`: el alfa de cada píxel, fila a fila
// (`null` si no se pudo leer), de la dirección que tenía al leerlo.
const mascaras = new WeakMap();

function leerAlfa(imagen, ancho, alto) {
  try {
    const lienzo = document.createElement('canvas');
    lienzo.width = ancho;
    lienzo.height = alto;
    const ctx = lienzo.getContext('2d');
    ctx.drawImage(imagen, 0, 0);
    const { data } = ctx.getImageData(0, 0, ancho, alto);
    const alfa = new Uint8Array(ancho * alto);
    for (let k = 0; k < alfa.length; k += 1) alfa[k] = data[k * 4 + 3];
    return alfa;
  } catch {
    // Un lienzo que no deja leer lo suyo: como si el dibujo no tuviera nada transparente.
    return null;
  }
}

function mascaraDe(imagen) {
  const fuente = imagen.currentSrc || imagen.src;
  let mascara = mascaras.get(imagen);
  if (!mascara || mascara.fuente !== fuente) {
    const ancho = imagen.naturalWidth;
    const alto = imagen.naturalHeight;
    mascara = { fuente, ancho, alto, alfa: leerAlfa(imagen, ancho, alto) };
    mascaras.set(imagen, mascara);
  }
  return mascara;
}

export function seVe(imagen, caja, x, y) {
  if (!(x >= caja.x && x <= caja.x + caja.ancho && y >= caja.y && y <= caja.y + caja.alto)) return false;
  if (!imagen || !(imagen.naturalWidth > 0 && imagen.naturalHeight > 0)) return true;
  const { ancho, alto, alfa } = mascaraDe(imagen);
  if (!alfa) return true;
  // El borde de abajo y el de la derecha son todavía del último píxel.
  const u = Math.min(ancho - 1, Math.floor(((x - caja.x) / caja.ancho) * ancho));
  const v = Math.min(alto - 1, Math.floor(((y - caja.y) / caja.alto) * alto));
  return alfa[v * ancho + u] > 0;
}
