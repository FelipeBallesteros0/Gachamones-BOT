// El único cargador del arte: las piezas de `web/static/arte/` que describe el
// contrato (`datos/arte.json`). Cada pieza se pide una sola vez, y la que no
// llega se dibuja como un recuadro rayado con su nombre, nunca con el dibujo
// de otra.

// La forma de una pieza del contrato: carpetas y nombre en minúsculas, cifras
// y `_`, con palabras unidas por un solo `-`, y `.png` al final. Nada de `..`,
// `\`, `%`, `?`, `#`, `:` ni barra al principio: con una ruta así no se sale
// de `arte/`. Las rutas se arman con claves que llegan del servidor, y este
// cargador es la única puerta del arte.
const PALABRAS = '[a-z0-9_]+(?:-[a-z0-9_]+)*';
const FORMA_DE_PIEZA = new RegExp(`^${PALABRAS}(?:/${PALABRAS})*\\.png$`);

export function esRutaDeArte(ruta) {
  return typeof ruta === 'string' && FORMA_DE_PIEZA.test(ruta);
}

// La dirección se arma desde la de este módulo: así lleva la versión de los
// estáticos (`/gachamon/static/<versión>/arte/…`) sin escribirla a mano. Con
// una ruta que no tiene forma de pieza no hay dirección: `null`.
export function urlDeArte(ruta) {
  if (!esRutaDeArte(ruta)) return null;
  return new URL(`../arte/${ruta}`, import.meta.url).href;
}

// Ruta → promesa de `{ruta, imagen}`. Guarda también las que fallaron, para no
// volver a pedir en cada cuadro una imagen que no existe.
const pedidas = new Map();

// La pieza ya cargada; `imagen` es `null` si no se pudo. Nunca rechaza. Una
// ruta sin forma de pieza no se pide ni se guarda: es una pieza que falta.
export function cargar(ruta) {
  if (!esRutaDeArte(ruta)) return Promise.resolve({ ruta, imagen: null });
  if (!pedidas.has(ruta)) {
    pedidas.set(ruta, new Promise((listo) => {
      try {
        const imagen = new Image();
        imagen.onload = () => listo({ ruta, imagen });
        imagen.onerror = () => listo({ ruta, imagen: null });
        imagen.src = urlDeArte(ruta);
      } catch {
        listo({ ruta, imagen: null });
      }
    }));
  }
  return pedidas.get(ruta);
}

// --- el recuadro de una pieza que falta ---------------------------------------

const RAYAS = 'rgba(214, 40, 120, 0.6)';
const BORDE = '#d62878';
const TINTA = '#1d1d1f';
const CONTORNO_DE_LA_TINTA = 'rgba(255, 255, 255, 0.9)';
// Lo que mide de ancho una letra de `monospace` respecto de su tamaño.
const ANCHO_DE_LETRA = 0.6;
const INTERLINEA = 1.25;

// La ruta en las líneas que hagan falta para que quepa en `util` con letra de
// `tam`: entera si cabe; si no, cortada después de cada «/», así que el nombre
// del archivo queda siempre entero en la última.
function lineasDe(ruta, util, tam) {
  const texto = String(ruta);
  if (texto.length * ANCHO_DE_LETRA * tam <= util) return [texto];
  return texto.match(/[^/]*\/|[^/]+$/g) || [texto];
}

// Un rectángulo con rayas diagonales y la ruta entera de la pieza en letra
// pequeña. Las rayas dejan ver lo que haya debajo (las otras capas de un
// avatar siguen en su sitio). Sólo usa primitivas del lienzo.
export function faltante(ctx, x, y, ancho, alto, ruta) {
  const grosor = Math.max(1, Math.round(Math.min(ancho, alto) / 32));
  const paso = grosor * 5;
  ctx.save();
  ctx.beginPath();
  ctx.rect(x, y, ancho, alto);
  ctx.clip();

  ctx.strokeStyle = RAYAS;
  ctx.lineWidth = grosor;
  ctx.beginPath();
  for (let d = paso / 2 - alto; d < ancho; d += paso) {
    ctx.moveTo(x + d, y + alto);
    ctx.lineTo(x + d + alto, y);
  }
  ctx.stroke();
  // Medio borde queda fuera del recorte: se ve de `grosor` y por dentro.
  ctx.strokeStyle = BORDE;
  ctx.lineWidth = grosor * 2;
  ctx.strokeRect(x, y, ancho, alto);

  // Letra pequeña: a lo más un décimo de la caja, y menos si no cabe.
  const margen = grosor * 2;
  const util = Math.max(1, ancho - margen * 2);
  const tamMaximo = Math.min(ancho, alto) / 10;
  const lineas = lineasDe(ruta, util, tamMaximo);
  const masLarga = Math.max(...lineas.map((linea) => linea.length));
  const tam = Math.max(1, Math.min(
    tamMaximo,
    util / (masLarga * ANCHO_DE_LETRA),
    (alto - margen * 2) / (lineas.length * INTERLINEA),
  ));
  ctx.font = `${tam}px monospace`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  ctx.lineWidth = Math.max(1, tam / 4);
  ctx.strokeStyle = CONTORNO_DE_LA_TINTA;
  ctx.fillStyle = TINTA;
  const centro = x + ancho / 2;
  const primera = y + alto / 2 - ((lineas.length - 1) * tam * INTERLINEA) / 2;
  lineas.forEach((linea, i) => {
    const altura = primera + i * tam * INTERLINEA;
    ctx.strokeText(linea, centro, altura, util);
    ctx.fillText(linea, centro, altura, util);
  });
  ctx.restore();
}

// Una pieza en su caja: su imagen, o el recuadro si no cargó.
export function pintarPieza(ctx, cargada, x, y, ancho, alto) {
  if (cargada && cargada.imagen) ctx.drawImage(cargada.imagen, x, y, ancho, alto);
  else faltante(ctx, x, y, ancho, alto, cargada ? cargada.ruta : '');
}
