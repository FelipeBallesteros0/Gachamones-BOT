// Cómo se pinta la pieza del departamento en su lienzo, de atrás hacia
// adelante: las dos paredes del fondo, tramo a tramo; el suelo, casilla a
// casilla; lo colgado en la pared; y, en el orden de `ordenDePintado`, lo que
// se pisa, los muebles, los gachamones (el que sale contigo, con su marca
// encima) y tu avatar, que en la puerta se ve de pie en su umbral. Encima de
// todo, y translúcidas, las marcas: dónde se puede poner lo que llevas en la
// mano y la huella de lo elegido. No sabe de red ni de reloj: pinta la escena
// que le dan.
//
// La pieza no es pixel art: sus dibujos se pintan con suavizado. El avatar y
// los retratos sí lo son, y se pintan sin él. Un dibujo que no se pudo cargar
// se ve como su recuadro con su nombre (`faltante`), nunca con el de otra
// pieza; uno que todavía no llega no se pinta.

import { faltante, pintarPieza } from './arte.js';
import { dibujarAvatar } from './avatar.js';
import {
  cajaDelGachamon, cajaDelMueble, ordenDePintado, proyectar, recuadroDe, rutaDelMueble, umbralDe,
} from './proyeccion.js';

const SUELO = 'suelo';
const PARED = 'pared';

const DIBUJO_DEL_SUELO = 'pieza/suelo.png';
const PARED_IZQUIERDA = 'pieza/pared-izquierda.png';
const PARED_DERECHA = 'pieza/pared-derecha.png';
const SOMBRA = 'efectos/sombra.png';
const MARCA = 'efectos/marca.png';

// Una casilla del suelo y un tramo de pared tienen la forma de lo más chico
// que se pone ahí.
const UNA_CASILLA = { capa: SUELO, ancho: 1, fondo: 1 };
const UN_TRAMO = { capa: PARED, ancho: 1, fondo: 1 };

// Lo que mide tu avatar de alto, en anchos de casilla.
const ALTO_DEL_AVATAR = 0.7;
// La sombra de un gachamon, a lo ancho de su caja; de alto, la mitad.
const ANCHO_DE_LA_SOMBRA = 0.6;
// La marca del que sale contigo, a lo ancho de su caja, y lo que la separa de su cabeza.
const LADO_DE_LA_MARCA = 0.28;
const SOBRE_LA_CABEZA = 0.06;

const LIBRE = 'rgba(70, 200, 110, 0.35)';
const BORDE_DEL_LIBRE = 'rgba(25, 135, 60, 0.95)';
const ELEGIDO = 'rgba(47, 111, 237, 0.3)';
const BORDE_DEL_ELEGIDO = '#2f6fed';

// Todo el arte que pide pintar esa pieza (sin el avatar ni los retratos).
export function rutasDeLaPieza(depto) {
  const muebles = depto.puestos.map((p) => rutaDelMueble(p.clave, p.capa, p.x, p.y, p.giro));
  return [...new Set([DIBUJO_DEL_SUELO, PARED_IZQUIERDA, PARED_DERECHA, SOMBRA, MARCA, ...muebles])];
}

// Un dibujo en su caja: el de `cargadas` si ya llegó (o su recuadro, si no se
// pudo); si todavía no llega, nada.
function pintar(ctx, cargadas, ruta, caja) {
  const cargada = cargadas.get(ruta);
  if (cargada) pintarPieza(ctx, cargada, caja.x, caja.y, caja.ancho, caja.alto);
}

// El rectángulo de casillas que cubre un mueble puesto, como lo pide `ordenDePintado`.
function dondeEsta(puesto) {
  const r = recuadroDe(puesto.casillas);
  return { i: r.i0, j: r.j0, a: r.i1 - r.i0, f: r.j1 - r.j0 };
}

// El retrato de un gachamon en su caja, de pie sobre su sombra, levantado lo
// que diga `g.sube` (un salto: la sombra se queda en el suelo). Es un dibujo
// de cuadros: sin suavizar, y sin deformarlo. Encima del que sale contigo, su
// marca.
function pintarGachamon(ctx, m, cargadas, g) {
  const caja = cajaDelGachamon(m, g.i, g.j);
  const pies = caja.y + caja.alto;
  const [centro] = proyectar(m, g.i + 0.5, g.j + 0.5);
  const sombra = caja.ancho * ANCHO_DE_LA_SOMBRA;
  pintar(ctx, cargadas, SOMBRA, { x: centro - sombra / 2, y: pies - sombra / 4, ancho: sombra, alto: sombra / 2 });
  const sube = g.sube || 0;
  let cabeza = caja.y - sube;
  const cargada = cargadas.get(g.retrato);
  if (cargada && !cargada.imagen) {
    faltante(ctx, caja.x, caja.y - sube, caja.ancho, caja.alto, g.retrato);
  } else if (cargada) {
    const { imagen } = cargada;
    const escala = Math.min(caja.ancho / imagen.naturalWidth, caja.alto / imagen.naturalHeight);
    const ancho = imagen.naturalWidth * escala;
    const alto = imagen.naturalHeight * escala;
    cabeza = pies - sube - alto;
    ctx.save();
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(imagen, centro - ancho / 2, pies - sube - alto, ancho, alto);
    ctx.restore();
  }
  if (g.activo) {
    const lado = caja.ancho * LADO_DE_LA_MARCA;
    pintar(ctx, cargadas, MARCA, {
      x: centro - lado / 2, y: cabeza - lado - caja.ancho * SOBRE_LA_CABEZA, ancho: lado, alto: lado,
    });
  }
}

// Dónde se pinta tu avatar: donde está, salvo en la casilla de la puerta, que
// queda fuera de la pieza: ahí, en su umbral (`umbralDe`); a medio paso entre
// ella y la casilla de enfrente, en la línea que los une.
function dondeSePinta({ i, j }) {
  if (i >= 0 && j >= 0) return [i, j];
  const enLaIzquierda = i < 0;
  const umbral = umbralDe(enLaIzquierda ? [-1, j] : [i, -1]);
  const enfrente = enLaIzquierda ? [0, j] : [i, 0];
  // Lo que le falta para llegar a la de enfrente: 1 en la puerta.
  const falta = enLaIzquierda ? -i : -j;
  return [0, 1].map((k) => enfrente[k] + (umbral[k] - enfrente[k]) * falta);
}

// Una casilla `(i, j)` del suelo, o un tramo de pared (`(-1, j)`, la
// izquierda; `(i, -1)`, la derecha), pintada encima de todo.
function marcar(ctx, m, [i, j], relleno, borde) {
  let esquinas;
  if (i === -1) esquinas = [[0, j, 0], [0, j + 1, 0], [0, j + 1, m.pared], [0, j, m.pared]];
  else if (j === -1) esquinas = [[i, 0, 0], [i + 1, 0, 0], [i + 1, 0, m.pared], [i, 0, m.pared]];
  else esquinas = [[i, j, 0], [i + 1, j, 0], [i + 1, j + 1, 0], [i, j + 1, 0]];
  ctx.beginPath();
  esquinas.forEach(([a, b, h], n) => {
    const [x, y] = proyectar(m, a, b, h);
    if (n === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.closePath();
  ctx.fillStyle = relleno;
  ctx.fill();
  if (borde) {
    ctx.lineWidth = 2;
    ctx.strokeStyle = borde;
    ctx.stroke();
  }
}

// `escena`: `{depto, cargadas, gachamones, tu, libres, elegido}`. `depto` es lo
// que contesta `GET departamento`; `cargadas`, el arte que ya llegó, por ruta
// (`{ruta, imagen}`, con las capas del avatar y los retratos); `gachamones`,
// `[{id, i, j, retrato, activo, sube}]`; `tu`, `{i, j, pose, espejo, avatar}` o
// `null` (tú puedes estar en la casilla de la puerta, fuera de la pieza);
// `libres` y `elegido`, listas de casillas o tramos `[i, j]` (o `null`). Las
// posiciones pueden tener decimales: alguien a medio paso.
export function dibujarPieza(ctx, m, escena) {
  const { depto, cargadas } = escena;
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  // Se pinta muy reducida (en 8 × 8, la casilla de 512 ocupa unos 41 píxeles
  // de pantalla): con la calidad de siempre, un dibujo con detalle saldría con dientes.
  ctx.imageSmoothingQuality = 'high';

  for (let y = 0; y < depto.fondo; y += 1) pintar(ctx, cargadas, PARED_IZQUIERDA, cajaDelMueble(m, UN_TRAMO, -1, y, 0));
  for (let x = 0; x < depto.ancho; x += 1) pintar(ctx, cargadas, PARED_DERECHA, cajaDelMueble(m, UN_TRAMO, x, -1, 0));
  for (let j = 0; j < depto.fondo; j += 1) {
    for (let i = 0; i < depto.ancho; i += 1) pintar(ctx, cargadas, DIBUJO_DEL_SUELO, cajaDelMueble(m, UNA_CASILLA, i, j, 0));
  }

  const delMueble = (p) => () => pintar(ctx, cargadas, rutaDelMueble(p.clave, p.capa, p.x, p.y, p.giro),
    cajaDelMueble(m, p, p.x, p.y, p.giro));
  const cosas = [];
  for (const p of depto.puestos) {
    if (p.capa === PARED) delMueble(p)();
    else cosas.push({ tipo: p.capa === SUELO ? SUELO : 'mueble', ...dondeEsta(p), pintar: delMueble(p) });
  }
  for (const g of escena.gachamones || []) {
    cosas.push({ tipo: 'gachamon', i: g.i, j: g.j, pintar: () => pintarGachamon(ctx, m, cargadas, g) });
  }
  const { tu } = escena;
  if (tu) {
    const [i, j] = dondeSePinta(tu);
    cosas.push({
      tipo: 'tu',
      i,
      j,
      pintar: () => {
        const [x, y] = proyectar(m, i + 0.5, j + 0.5);
        dibujarAvatar(ctx, cargadas, tu.avatar, tu.pose, x, y, ALTO_DEL_AVATAR * m.tw, tu.espejo);
      },
    });
  }
  for (const cosa of ordenDePintado(cosas)) cosa.pintar();

  for (const sitio of escena.libres || []) marcar(ctx, m, sitio, LIBRE, BORDE_DEL_LIBRE);
  for (const casilla of escena.elegido || []) marcar(ctx, m, casilla, ELEGIDO, BORDE_DEL_ELEGIDO);
  ctx.restore();
}
