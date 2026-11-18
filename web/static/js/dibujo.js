// El arte de relleno que se dibuja en un <canvas>: el huevo. Puro: recibe el
// contexto y no toca la página. El avatar no se dibuja con código: se apila
// con capas de archivo, en `avatar.js`.
//
// Dibuja con el origen en el suelo, centrado: quien llama hace `translate`
// hasta donde va la base. Una unidad del dibujo mide `escala` píxeles del
// lienzo. Sólo se usan `fillStyle`, `beginPath`, `ellipse`, `fill`, `save`,
// `restore` y `scale`.

const SOMBRA_EN_EL_SUELO = 'rgba(0, 0, 0, 0.2)';

function sombraEnElSuelo(ctx, radio) {
  ctx.fillStyle = SOMBRA_EN_EL_SUELO;
  ctx.beginPath();
  ctx.ellipse(0, 0, radio, 2.5, 0, 0, Math.PI * 2);
  ctx.fill();
}

// --- el huevo de la pantalla de entrar ----------------------------------------

const CASCARA = '#fbf4e6';
const CONTORNO = '#c9b089';
const MANCHAS = [
  ['#8cc7e8', -4, -19, 2.6, 2.1],
  ['#f2a7b8', 4, -10, 3, 2.2],
  ['#a6d98c', 3.5, -22, 1.8, 1.5],
  ['#f6cf6b', -5, -8, 1.7, 1.3],
];

function ovalo(ctx, color, x, y, radioX, radioY) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.ellipse(x, y, radioX, radioY, 0, 0, Math.PI * 2);
  ctx.fill();
}

// El huevo, entero, con la base en el origen.
export function dibujarHuevo(ctx, escala) {
  ctx.save();
  ctx.scale(escala, escala);
  sombraEnElSuelo(ctx, 11);
  ovalo(ctx, CONTORNO, 0, -14.5, 12, 15);
  ovalo(ctx, CASCARA, 0, -14.5, 11, 14);
  for (const [color, x, y, radioX, radioY] of MANCHAS) ovalo(ctx, color, x, y, radioX, radioY);
  ovalo(ctx, 'rgba(255, 255, 255, 0.75)', -5, -20, 1.8, 3.4);
  ctx.restore();
}
