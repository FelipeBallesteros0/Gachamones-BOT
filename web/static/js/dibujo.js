// El arte de relleno que se dibuja en un <canvas>: el monigote del avatar y el
// huevo. Puro: recibe el contexto y no toca la página.
//
// Las dos funciones dibujan con el origen en el suelo, centradas: quien llama
// hace `translate` hasta donde van los pies. Una unidad del dibujo mide
// `escala` píxeles del lienzo. Sólo se usan `fillStyle`, `fillRect`,
// `beginPath`, `ellipse`, `fill`, `save`, `restore`, `translate` y `scale`.

// Un color por clave del catálogo del servidor (avatar.py), en su mismo orden.
export const COLORES_DE_PIEL = {
  clara: '#f6d5bd',
  media: '#e8b48a',
  tostada: '#c68a5c',
  oscura: '#8a5636',
};

export const COLORES_DE_PELO = {
  negro: '#2a2523',
  castano: '#6b4226',
  rubio: '#e2b552',
  rojo: '#c2502a',
  cano: '#d4d4da',
  azul: '#3a6fd8',
};

export const COLORES_DE_ROPA = {
  poleron: '#d9534f',
  camisa: '#4f9d69',
  vestido: '#8f6ad8',
  overol: '#3f6fb5',
};

const POR_DEFECTO = { piel: '#e8b48a', pelo: '#6b4226', ropa: '#9aa0a8' };
const OJOS = '#1d1d1f';
const ZAPATOS = '#3a3a3c';
const BLANCO = '#f5f3ee';
const MEJILLAS = 'rgba(232, 96, 110, 0.45)';
const SOMBRA_EN_EL_SUELO = 'rgba(0, 0, 0, 0.2)';

// Una clave del catálogo es una propiedad propia; cualquier otra cosa (también
// `constructor` o `__proto__`) cae en el color por defecto.
function colorDe(tabla, clave, defecto) {
  return Object.hasOwn(tabla, clave) ? tabla[clave] : defecto;
}

// El mismo color más oscuro: `factor` 0,8 deja el 80 % de cada canal.
function oscurecer(hex, factor) {
  const n = parseInt(hex.slice(1), 16);
  const canal = (desplazamiento) => Math.round(((n >> desplazamiento) & 255) * factor);
  return `rgb(${canal(16)}, ${canal(8)}, ${canal(0)})`;
}

function rect(ctx, color, x, y, ancho, alto) {
  ctx.fillStyle = color;
  ctx.fillRect(x, y, ancho, alto);
}

function sombraEnElSuelo(ctx, radio) {
  ctx.fillStyle = SOMBRA_EN_EL_SUELO;
  ctx.beginPath();
  ctx.ellipse(0, 0, radio, 2.5, 0, 0, Math.PI * 2);
  ctx.fill();
}

// --- la ropa: cada conjunto pinta piernas, tronco y brazos -----------------

function brazos(ctx, manga, piel, largoDeManga = 9) {
  for (const x of [-8, 5]) {
    rect(ctx, piel, x, -19, 3, 11);
    rect(ctx, manga, x, -19, 3, largoDeManga);
  }
}

function piernas(ctx, color) {
  rect(ctx, color, -5, -9, 4, 9);
  rect(ctx, color, 1, -9, 4, 9);
  rect(ctx, ZAPATOS, -5, -2, 4, 2);
  rect(ctx, ZAPATOS, 1, -2, 4, 2);
}

function poleron(ctx, color, piel) {
  piernas(ctx, '#2f3e63');
  rect(ctx, color, -6, -20, 12, 12);
  rect(ctx, oscurecer(color, 0.75), -4, -20, 8, 1.5);
  rect(ctx, BLANCO, -2, -18.5, 0.75, 3);
  rect(ctx, BLANCO, 1.25, -18.5, 0.75, 3);
  rect(ctx, oscurecer(color, 0.85), -3, -13, 6, 3);
  brazos(ctx, oscurecer(color, 0.85), piel);
}

function camisa(ctx, color, piel) {
  piernas(ctx, '#4b4f5c');
  rect(ctx, color, -6, -20, 12, 12);
  rect(ctx, BLANCO, -3, -20, 2.5, 2);
  rect(ctx, BLANCO, 0.5, -20, 2.5, 2);
  for (const y of [-17, -14, -11]) rect(ctx, oscurecer(color, 0.6), -0.5, y, 1, 1);
  rect(ctx, ZAPATOS, -6, -9, 12, 1);
  brazos(ctx, oscurecer(color, 0.9), piel, 6);
}

function vestido(ctx, color, piel) {
  rect(ctx, piel, -4, -9, 3, 9);
  rect(ctx, piel, 1, -9, 3, 9);
  rect(ctx, ZAPATOS, -4, -2, 3, 2);
  rect(ctx, ZAPATOS, 1, -2, 3, 2);
  rect(ctx, color, -6, -20, 12, 7);
  rect(ctx, color, -7, -13, 14, 7);
  rect(ctx, oscurecer(color, 0.75), -6, -14, 12, 1);
  rect(ctx, oscurecer(color, 0.8), -7, -7, 14, 1);
  brazos(ctx, oscurecer(color, 0.85), piel, 4);
}

function overol(ctx, color, piel) {
  piernas(ctx, color);
  rect(ctx, BLANCO, -6, -20, 12, 12);
  rect(ctx, color, -6, -11, 12, 3);
  rect(ctx, color, -4, -16, 8, 6);
  rect(ctx, color, -5, -20, 2, 5);
  rect(ctx, color, 3, -20, 2, 5);
  rect(ctx, '#e0a100', -4, -16, 1, 1);
  rect(ctx, '#e0a100', 3, -16, 1, 1);
  rect(ctx, oscurecer(color, 0.8), -2, -14, 4, 2);
  brazos(ctx, BLANCO, piel, 5);
}

const ROPAS = { poleron, camisa, vestido, overol };

// --- el pelo: mira hacia la derecha, así que la nuca queda a la izquierda ---

const PELOS = {
  corto(ctx, color) {
    rect(ctx, color, -7, -33, 14, 5);
    rect(ctx, color, -7, -31, 3, 6);
  },
  largo(ctx, color) {
    rect(ctx, color, -7, -33, 14, 5);
    rect(ctx, color, -8, -31, 4, 13);
    rect(ctx, color, 5, -29, 2, 3);
  },
  rizado(ctx, color) {
    rect(ctx, color, -8, -33, 16, 5);
    rect(ctx, color, -7, -35, 4, 2);
    rect(ctx, color, -2, -36, 4, 3);
    rect(ctx, color, 3, -35, 4, 2);
    rect(ctx, color, -9, -31, 4, 8);
    rect(ctx, color, 6, -31, 2, 3);
  },
  coleta(ctx, color, lazo) {
    rect(ctx, color, -7, -33, 14, 5);
    rect(ctx, color, -7, -31, 3, 5);
    rect(ctx, color, -11, -30, 3, 9);
    rect(ctx, lazo, -9, -31, 2, 2);
  },
  rapado(ctx, color) {
    rect(ctx, color, -6.5, -32, 13, 2.5);
    rect(ctx, color, -7, -31, 1.5, 4);
  },
};

function cara(ctx, genero) {
  rect(ctx, OJOS, 0, -26, 2, 2);
  rect(ctx, OJOS, 4, -26, 1.5, 2);
  if (genero === 'hembra') {
    rect(ctx, OJOS, -1, -27, 1, 1);
    rect(ctx, OJOS, 5.5, -27, 1, 1);
    rect(ctx, MEJILLAS, -1, -23.5, 2, 1);
    rect(ctx, MEJILLAS, 4, -23.5, 2, 1);
  }
}

// El monigote de relleno, con los pies en el origen. Cambia con las cinco
// elecciones del avatar; una clave que no conoce se dibuja con lo de por defecto.
export function dibujarAvatar(ctx, avatar, escala) {
  const piel = colorDe(COLORES_DE_PIEL, avatar.piel, POR_DEFECTO.piel);
  const pelo = colorDe(COLORES_DE_PELO, avatar.color_de_pelo, POR_DEFECTO.pelo);
  const ropa = colorDe(COLORES_DE_ROPA, avatar.ropa, POR_DEFECTO.ropa);
  const vestirse = Object.hasOwn(ROPAS, avatar.ropa) ? ROPAS[avatar.ropa] : ROPAS.poleron;
  const peinarse = Object.hasOwn(PELOS, avatar.pelo) ? PELOS[avatar.pelo] : PELOS.corto;

  ctx.save();
  ctx.scale(escala, escala);
  sombraEnElSuelo(ctx, 9);
  vestirse(ctx, ropa, piel);
  rect(ctx, piel, -6, -31, 12, 11);
  peinarse(ctx, pelo, ropa);
  cara(ctx, avatar.genero);
  ctx.restore();
}

// --- el huevo de partida ----------------------------------------------------

const CASCARA = '#fbf4e6';
const CONTORNO = '#c9b089';
const MANCHAS = [
  ['#8cc7e8', -4, -19, 2.6, 2.1],
  ['#f2a7b8', 4, -10, 3, 2.2],
  ['#a6d98c', 3.5, -22, 1.8, 1.5],
  ['#f6cf6b', -5, -8, 1.7, 1.3],
];
const GRIETA = [[-8, -15], [-6, -16], [-4, -15], [-2, -14], [0, -15], [2, -16], [4, -15], [6, -14]];

function ovalo(ctx, color, x, y, radioX, radioY) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.ellipse(x, y, radioX, radioY, 0, 0, Math.PI * 2);
  ctx.fill();
}

// El huevo, con la base en el origen; `roto` le pinta la grieta.
export function dibujarHuevo(ctx, escala, roto) {
  ctx.save();
  ctx.scale(escala, escala);
  sombraEnElSuelo(ctx, 11);
  ovalo(ctx, CONTORNO, 0, -14.5, 12, 15);
  ovalo(ctx, CASCARA, 0, -14.5, 11, 14);
  for (const [color, x, y, radioX, radioY] of MANCHAS) ovalo(ctx, color, x, y, radioX, radioY);
  ovalo(ctx, 'rgba(255, 255, 255, 0.75)', -5, -20, 1.8, 3.4);
  if (roto) {
    for (const [x, y] of GRIETA) rect(ctx, '#5b4a33', x, y, 2, 1);
  }
  ctx.restore();
}
