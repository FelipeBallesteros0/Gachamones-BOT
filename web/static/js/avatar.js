// El avatar de la persona, armado con tres capas de archivo que se apilan:
// cuerpo, ropa y pelo (`arte/avatar/…`, 48 × 84, mirando a la derecha). El
// género no cambia el dibujo: sólo decide cómo concuerdan los textos.

import { cargar, faltante } from './arte.js';

export const POSES = ['quieto', 'paso1', 'paso2'];

// Lo que mide cada capa, y a cuántos píxeles del borde de abajo están los
// pies (el contrato del arte).
const ANCHO = 48;
const ALTO = 84;
const PIES = 4;
const PASO_S = 0.18;

// Un campo del avatar, o nada si falta, no es un texto o no hay avatar.
function clave(avatar, campo) {
  const valor = avatar ? avatar[campo] : undefined;
  return typeof valor === 'string' ? valor : '';
}

// Las tres rutas de esa pose, en el orden en que se apilan. Puro y no lanza:
// una clave que el contrato no conoce da una ruta que no existe, y una que
// falta, una ruta sin forma de pieza; las dos se ven como su recuadro.
export function capasDelAvatar(avatar, pose) {
  const [piel, ropa, pelo, color] = ['piel', 'ropa', 'pelo', 'color_de_pelo'].map((campo) => clave(avatar, campo));
  return [
    `avatar/cuerpo/${piel}-${pose}.png`,
    `avatar/ropa/${ropa}-${pose}.png`,
    `avatar/pelo/${pelo}-${color}-${pose}.png`,
  ];
}

// La pose a los `t` segundos: quieto si no se mueve; si se mueve, un paso y
// otro, cada 0,18 s.
export function poseAlCaminar(t, moviendose) {
  if (!moviendose) return 'quieto';
  return Math.floor(t / PASO_S) % 2 === 0 ? 'paso1' : 'paso2';
}

async function cargarCapas(rutas) {
  const cargadas = await Promise.all(rutas.map(cargar));
  return new Map(cargadas.map((cargada) => [cargada.ruta, cargada]));
}

// Las nueve capas del avatar (tres por pose), ya cargadas, por ruta.
export function cargarAvatar(avatar) {
  return cargarCapas(POSES.flatMap((pose) => capasDelAvatar(avatar, pose)));
}

// Apila las tres capas de la pose con los pies en (x, y), a `alto` píxeles de
// alto; con `espejo`, mirando a la izquierda. Sin suavizar: son dibujos de
// cuadros. Una capa que no está en `capas` o no cargó se ve como su recuadro,
// derecho para que se lea, y las demás se pintan igual.
export function dibujarAvatar(ctx, capas, avatar, pose, x, y, alto, espejo) {
  const escala = alto / ALTO;
  const ancho = ANCHO * escala;
  const izquierda = Math.round(x - ancho / 2);
  const arriba = Math.round(y - (ALTO - PIES) * escala);
  ctx.save();
  ctx.imageSmoothingEnabled = false;
  for (const ruta of capasDelAvatar(avatar, pose)) {
    const cargada = capas.get(ruta);
    if (!cargada || !cargada.imagen) {
      faltante(ctx, izquierda, arriba, ancho, alto, ruta);
      continue;
    }
    ctx.save();
    if (espejo) {
      // Da vuelta la caja sobre su eje: queda en el mismo sitio.
      ctx.translate(izquierda * 2 + ancho, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(cargada.imagen, izquierda, arriba, ancho, alto);
    ctx.restore();
  }
  ctx.restore();
}

// La última petición de cada lienzo: la que llega tarde no lo pisa.
const ultimaDe = new WeakMap();

// El avatar quieto en un <canvas> suelto, de unos `alto` píxeles de pantalla.
// Cada dos píxeles del dibujo miden un número entero de píxeles del teléfono:
// es la cuenta del monigote que se dibujaba con código, así que se ve del
// mismo tamaño que antes en cualquier pantalla. Sin suavizar no se emborrona;
// cuando la cuenta da media, un píxel del dibujo mide uno del teléfono más que
// su vecino. Mientras cargan las capas se queda lo que había; cuando llegan,
// se cambia de una vez, y si entretanto se pidió otro avatar, gana el último.
export async function lienzoDelAvatar(lienzo, avatar, alto) {
  const densidad = Math.min(Math.max(window.devicePixelRatio || 1, 1), 3);
  const escala = Math.max(1, Math.round((alto * densidad * 2) / ALTO) / 2);
  // Cambiar el tamaño borra el lienzo: sólo si de verdad cambia.
  if (lienzo.width !== ANCHO * escala || lienzo.height !== ALTO * escala) {
    lienzo.width = ANCHO * escala;
    lienzo.height = ALTO * escala;
    lienzo.style.width = `${(ANCHO * escala) / densidad}px`;
    lienzo.style.height = `${(ALTO * escala) / densidad}px`;
  }
  const turno = {};
  ultimaDe.set(lienzo, turno);
  const capas = await cargarCapas(capasDelAvatar(avatar, 'quieto'));
  if (ultimaDe.get(lienzo) !== turno) return;
  const ctx = lienzo.getContext('2d');
  ctx.clearRect(0, 0, lienzo.width, lienzo.height);
  dibujarAvatar(ctx, capas, avatar, 'quieto', lienzo.width / 2, lienzo.height - PIES * escala, lienzo.height, false);
}
