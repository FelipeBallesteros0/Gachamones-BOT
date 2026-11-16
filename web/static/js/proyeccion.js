// La geometría de la pieza del departamento en vista isométrica: medir la
// casilla, proyectar, saber qué hay bajo un punto, dónde se pinta cada dibujo,
// quién tapa a quién y qué se tocó. Es puro: sin pantalla, sin reloj, sin red.
// El servidor manda: esto sirve para dibujar y para no proponer lo imposible.
import { huellaDe } from './casillas.js';

export const ORIENTACIONES = ['se', 'so', 'no', 'ne'];

const SUELO = 'suelo';
const PARED = 'pared';
const MARGEN_LADOS = 28;
const MARGEN_VERTICAL = 34;
const MARGEN_ARRIBA = 16;

// La casilla más grande que deja ver la pieza entera con sus paredes.
export function medir(anchoPx, altoPx, ancho, fondo) {
  const suma = ancho + fondo;
  const tw = Math.min(2 * (anchoPx - MARGEN_LADOS) / suma, (altoPx - MARGEN_VERTICAL) / (1 + suma / 4));
  const pared = tw;
  return { tw, th: tw / 2, pared, ox: anchoPx / 2 - (ancho - fondo) * tw / 4, oy: MARGEN_ARRIBA + pared };
}

export function proyectar(m, i, j, h = 0) {
  return [m.ox + (i - j) * m.tw / 2, m.oy + (i + j) * m.th / 2 - h];
}

// Las coordenadas del suelo (sin redondear) bajo un punto de la pantalla.
function sueloBajo(m, x, y) {
  const u = (x - m.ox) / (m.tw / 2);
  const v = (y - m.oy) / (m.th / 2);
  return [(v + u) / 2, (v - u) / 2];
}

export function casillaEn(m, x, y, ancho, fondo) {
  const [a, b] = sueloBajo(m, x, y);
  const i = Math.floor(a);
  const j = Math.floor(b);
  if (i < 0 || j < 0 || i >= ancho || j >= fondo) return null;
  return [i, j];
}

export function tramoEn(m, x, y, ancho, fondo) {
  const u = (x - m.ox) / (m.tw / 2);
  if (u < 0) {
    const j = -u;
    const h = m.oy + j * m.th / 2 - y;
    if (j < 0 || j >= fondo || h < 0 || h > m.pared) return null;
    return [-1, Math.floor(j)];
  }
  const i = u;
  const h = m.oy + i * m.th / 2 - y;
  if (i >= ancho || h < 0 || h > m.pared) return null;
  return [Math.floor(i), -1];
}

// El rectángulo de casillas que cubre una huella: [i0, i1) × [j0, j1).
export function recuadroDe(casillas) {
  let i0 = Infinity, j0 = Infinity, i1 = -Infinity, j1 = -Infinity;
  for (const [i, j] of casillas) {
    i0 = Math.min(i0, i);
    j0 = Math.min(j0, j);
    i1 = Math.max(i1, i + 1);
    j1 = Math.max(j1, j + 1);
  }
  return { i0, j0, i1, j1 };
}

export function cajaDelMueble(m, forma, x, y, giro) {
  const r = recuadroDe(huellaDe(forma, x, y, giro));
  if (forma.capa === PARED) {
    const tramos = Math.max(r.i1 - r.i0, r.j1 - r.j0);
    const izquierda = x === -1;
    const [px] = izquierda ? proyectar(m, 0, r.j0 + tramos) : proyectar(m, r.i0, 0);
    const [, arriba] = izquierda ? proyectar(m, 0, r.j0) : proyectar(m, r.i0, 0);
    return { x: px, y: arriba - m.pared, ancho: tramos * m.tw / 2, alto: m.pared + tramos * m.th / 2 };
  }
  const medias = (r.i1 - r.i0) + (r.j1 - r.j0);
  const alto = medias * m.th / 2 + (forma.capa === SUELO ? 0 : m.pared);
  const [izquierda] = proyectar(m, r.i0, r.j1);
  const [, abajo] = proyectar(m, r.i1, r.j1);
  return { x: izquierda, y: abajo - alto, ancho: medias * m.tw / 2, alto };
}

// Dónde se pinta quien está en la casilla de la puerta: de pie en el vano, no
// detrás de la pared.
export function umbralDe([i, j]) {
  return i === -1 ? [-0.6, j] : [i, -0.6];
}

export function cajaDelGachamon(m, i, j) {
  const [cx, cy] = proyectar(m, i + 0.5, j + 0.5);
  const lado = 0.8 * m.tw;
  return { x: cx - lado / 2, y: cy + m.th / 4 - lado, ancho: lado, alto: lado };
}

export function rutaDelMueble(clave, capa, x, y, giro) {
  let orientacion;
  if (capa === PARED) orientacion = y === -1 ? 'so' : 'se';
  else orientacion = ORIENTACIONES[giro];
  return `pieza/muebles/${clave}-${orientacion}.png`;
}

const hasta = (c) => ({ i: c.i + (c.a ?? 1), j: c.j + (c.f ?? 1) });

// A va antes que B si A acaba donde B empieza (o antes) en algún eje y B no
// cumple lo mismo respecto de A.
function tapaA(a, b) {
  const ea = hasta(a);
  const eb = hasta(b);
  const antes = (ea.i <= b.i || ea.j <= b.j);
  const despues = (eb.i <= a.i || eb.j <= a.j);
  return antes && !despues;
}

export function ordenDePintado(cosas) {
  const salida = cosas.filter((c) => c.tipo === SUELO);
  const resto = cosas.filter((c) => c.tipo !== SUELO);
  const cuenta = (c) => c.i + c.j + ((c.a ?? 1) + (c.f ?? 1)) / 2;
  const mejor = (lista) => lista.reduce((a, b) => {
    if (cuenta(b) !== cuenta(a)) return cuenta(b) < cuenta(a) ? b : a;
    const ra = a.tipo === 'tu' ? 1 : 0;
    const rb = b.tipo === 'tu' ? 1 : 0;
    return rb < ra ? b : a;
  });
  while (resto.length > 0) {
    const libres = resto.filter((c) => !resto.some((otra) => otra !== c && tapaA(otra, c)));
    const elegida = mejor(libres.length > 0 ? libres : resto);
    resto.splice(resto.indexOf(elegida), 1);
    salida.push(elegida);
  }
  return salida;
}

const dentro = (caja, x, y) => x >= caja.x && x <= caja.x + caja.ancho && y >= caja.y && y <= caja.y + caja.alto;

// ¿Cae el punto en la caja que se levanta m.pared sobre la huella? Bajar por la
// pantalla es avanzar por la diagonal del suelo.
function enLaSilueta(m, r, x, y) {
  const [i0, j0] = sueloBajo(m, x, y);
  const bajo = Math.max(0, r.i0 - i0, r.j0 - j0);
  const alto = Math.min(m.pared / m.th, r.i1 - i0, r.j1 - j0);
  return bajo < alto;
}

const delanteDeTodo = (candidatos) => ordenDePintado(candidatos).at(-1);

export function queSeToco(m, depto, gachamones, x, y) {
  const tocados = gachamones
    .filter((g) => dentro(cajaDelGachamon(m, g.i, g.j), x, y))
    .map((g) => ({ tipo: 'gachamon', i: g.i, j: g.j, id: g.id }));
  if (tocados.length > 0) return { tipo: 'gachamon', id: delanteDeTodo(tocados).id };

  const muebles = [];
  for (const puesto of depto.puestos) {
    if (puesto.capa === SUELO || puesto.capa === PARED) continue;
    const r = recuadroDe(huellaDe(puesto, puesto.x, puesto.y, puesto.giro));
    if (enLaSilueta(m, r, x, y)) muebles.push({ tipo: 'mueble', i: r.i0, j: r.j0, a: r.i1 - r.i0, f: r.j1 - r.j0, id: puesto.id });
  }
  if (muebles.length > 0) return { tipo: 'mueble', id: delanteDeTodo(muebles).id };

  const tramo = tramoEn(m, x, y, depto.ancho, depto.fondo);
  if (tramo) {
    const colgado = depto.puestos.find((p) => p.capa === PARED && p.casillas.some(([i, j]) => i === tramo[0] && j === tramo[1]));
    return colgado ? { tipo: 'mueble', id: colgado.id } : { tipo: 'tramo', i: tramo[0], j: tramo[1] };
  }

  const casilla = casillaEn(m, x, y, depto.ancho, depto.fondo);
  if (casilla) {
    const pisado = depto.puestos.find((p) => p.capa === SUELO && p.casillas.some(([i, j]) => i === casilla[0] && j === casilla[1]));
    const salida = { tipo: 'casilla', i: casilla[0], j: casilla[1] };
    if (pisado) salida.mueble = pisado.id;
    return salida;
  }
  return null;
}
