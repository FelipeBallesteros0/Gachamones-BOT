import test from 'node:test';
import assert from 'node:assert/strict';
import * as p from '../../web/static/js/proyeccion.js';

const CAMA = { clave: 'cama_sencilla', ancho: 2, fondo: 1, capa: 'bulto' };
const ALFOMBRA = { clave: 'alfombra', ancho: 2, fondo: 2, capa: 'suelo' };
const MACETA = { clave: 'maceta', ancho: 1, fondo: 1, capa: 'bulto' };
const FELPUDO = { clave: 'felpudo', ancho: 1, fondo: 1, capa: 'suelo' };
const CUADRO = { clave: 'cuadro', ancho: 1, fondo: 1, capa: 'pared' };
const CORTINAS = { clave: 'cortinas', ancho: 2, fondo: 1, capa: 'pared' };

function depto(puestos, ancho = 3, fondo = 3) {
  return { ancho, fondo, casillas: ancho * fondo, comodidad: 80, tope: 100, camas: 0, gachamones: 0, puestos, guardados: [] };
}

const cerca = (a, b) => Math.abs(a - b) < 1e-9;

test('la casilla se ajusta al tamaño de la pieza', () => {
  assert.ok(Math.abs(p.medir(380, 310, 3, 3).tw - 110.4) < 1e-6);
  assert.equal(p.medir(380, 310, 8, 8).tw, 44);
  const m = p.medir(380, 310, 4, 2);
  assert.deepEqual([m.th, m.pared], [m.tw / 2, m.tw]);
  assert.ok(cerca(m.ox, 190 - 2 * m.tw / 4));
});

test('toda la pieza cabe en el lienzo, del 3 × 3 al 8 × 8', () => {
  for (let ancho = 3; ancho <= 8; ancho += 1) for (let fondo = 3; fondo <= 8; fondo += 1) {
    const m = p.medir(380, 310, ancho, fondo);
    const esquinas = [p.proyectar(m, 0, 0, m.pared), p.proyectar(m, ancho, 0, m.pared), p.proyectar(m, 0, fondo, m.pared),
                      p.proyectar(m, ancho, 0), p.proyectar(m, 0, fondo), p.proyectar(m, ancho, fondo)];
    for (const [x, y] of esquinas) assert.ok(x >= 0 && x <= 380 && y >= 0 && y <= 310, `${ancho}×${fondo}`);
  }
});

test('el centro de cada casilla cae en su casilla', () => {
  for (const [ancho, fondo] of [[3, 3], [8, 8], [8, 3], [4, 7]]) {
    const m = p.medir(1040, 520, ancho, fondo);
    for (let i = 0; i < ancho; i += 1) for (let j = 0; j < fondo; j += 1) {
      const [x, y] = p.proyectar(m, i + 0.5, j + 0.5);
      assert.deepEqual(p.casillaEn(m, x, y, ancho, fondo), [i, j]);
    }
  }
});

test('fuera de la pieza no hay casilla', () => {
  const m = p.medir(380, 310, 3, 3);
  for (const [i, j] of [[-0.2, 1], [1, -0.2], [3.1, 1], [1, 3.1], [-5, -5]]) {
    const [x, y] = p.proyectar(m, i, j);
    assert.equal(p.casillaEn(m, x, y, 3, 3), null);
  }
});

test('las paredes tienen sus tramos', () => {
  const m = p.medir(380, 310, 4, 3);
  let [x, y] = p.proyectar(m, 0, 1.5, m.pared / 2);          // pared izquierda, a media altura, tramo 1
  assert.deepEqual(p.tramoEn(m, x, y, 4, 3), [-1, 1]);
  [x, y] = p.proyectar(m, 2.5, 0, m.pared / 2);              // pared derecha, tramo 2
  assert.deepEqual(p.tramoEn(m, x, y, 4, 3), [2, -1]);
  [x, y] = p.proyectar(m, 1.5, 1.5);                         // el suelo no es pared
  assert.equal(p.tramoEn(m, x, y, 4, 3), null);
  [x, y] = p.proyectar(m, 0, 3.5, m.pared / 2);              // más allá del largo de la pared
  assert.equal(p.tramoEn(m, x, y, 4, 3), null);
  [x, y] = p.proyectar(m, 2.5, 0, m.pared * 1.2);            // por encima de la pared
  assert.equal(p.tramoEn(m, x, y, 4, 3), null);
});

test('el dibujo de un mueble cubre su huella y sobresale hacia arriba', () => {
  const m = p.medir(1040, 520, 4, 4);
  const caja = p.cajaDelMueble(m, CAMA, 1, 2, 0);                      // ocupa (1, 2) y (2, 2)
  assert.ok(cerca(caja.x, p.proyectar(m, 1, 3)[0]));                    // la esquina izquierda de la huella
  assert.ok(cerca(caja.ancho, 3 * m.tw / 2));                           // (ancho + fondo) medias casillas
  assert.ok(cerca(caja.y + caja.alto, p.proyectar(m, 3, 3)[1]));        // el borde de abajo, en la esquina de delante
  assert.ok(cerca(caja.alto, 3 * m.th / 2 + m.pared));
  const girada = p.cajaDelMueble(m, CAMA, 1, 2, 1);                     // ocupa (1, 2) y (1, 3)
  assert.ok(cerca(girada.ancho, caja.ancho) && cerca(girada.alto, caja.alto));
  assert.ok(cerca(p.cajaDelMueble(m, ALFOMBRA, 0, 0, 0).alto, 4 * m.th / 2));   // lo que se pisa no sobresale
});

test('lo de pared se pinta sobre sus tramos', () => {
  const m = p.medir(1040, 520, 4, 4);
  const derecha = p.cajaDelMueble(m, CUADRO, 2, -1, 0);
  assert.ok(cerca(derecha.x, m.ox + m.tw) && cerca(derecha.ancho, m.tw / 2));
  assert.ok(cerca(derecha.y, m.oy + m.th - m.pared) && cerca(derecha.alto, m.pared + m.th / 2));
  const izquierda = p.cajaDelMueble(m, CORTINAS, -1, 1, 0);             // tramos 1 y 2 de la izquierda
  assert.ok(cerca(izquierda.x, m.ox - 3 * m.tw / 2) && cerca(izquierda.ancho, m.tw));
  assert.ok(cerca(izquierda.y, m.oy + m.th / 2 - m.pared) && cerca(izquierda.alto, m.pared + m.th));
});

test('cada mueble pide el dibujo de hacia dónde mira', () => {
  assert.equal(p.rutaDelMueble('maceta', 'bulto', 1, 1, 0), 'pieza/muebles/maceta-se.png');
  assert.equal(p.rutaDelMueble('maceta', 'bulto', 1, 1, 3), 'pieza/muebles/maceta-ne.png');
  assert.equal(p.rutaDelMueble('cuadro', 'pared', 2, -1, 0), 'pieza/muebles/cuadro-so.png');
  assert.equal(p.rutaDelMueble('cuadro', 'pared', -1, 2, 2), 'pieza/muebles/cuadro-se.png');
});

const antes = (orden, x, y) => orden.indexOf(x) < orden.indexOf(y);

test('lo de atrás se pinta antes', () => {
  const alfombra = { tipo: 'suelo', i: 2, j: 2, a: 2, f: 2 };
  const maceta = { tipo: 'mueble', i: 1, j: 0, a: 1, f: 1 };
  const detras = { tipo: 'gachamon', i: 0, j: 0 }, delante = { tipo: 'gachamon', i: 1, j: 1 };
  const tu = { tipo: 'tu', i: 3, j: 3 };
  const orden = p.ordenDePintado([tu, delante, maceta, detras, alfombra]);
  assert.equal(orden.length, 5);
  assert.equal(orden[0], alfombra);                                  // lo que se pisa, primero, aunque esté delante
  assert.ok(antes(orden, detras, maceta) && antes(orden, maceta, delante) && antes(orden, delante, tu));
});

test('junto a un mueble largo, quien está delante de su cara se pinta después', () => {
  const cama = { tipo: 'mueble', i: 0, j: 0, a: 1, f: 2 };           // girada: a lo largo del fondo
  const alLado = { tipo: 'gachamon', i: 1, j: 0 };                   // la cuenta del boceto lo pintaba debajo
  const alPie = { tipo: 'gachamon', i: 0, j: 2 };
  const fuente = { tipo: 'mueble', i: 2, j: 2, a: 2, f: 2 };
  const juntoALaFuente = { tipo: 'tu', i: 4, j: 2 };
  const orden = p.ordenDePintado([juntoALaFuente, alPie, fuente, alLado, cama]);
  assert.ok(antes(orden, cama, alLado) && antes(orden, cama, alPie));
  assert.ok(antes(orden, fuente, juntoALaFuente) && antes(orden, alLado, fuente));
});

test('dos en la misma casilla o a medio paso no lo dejan sin terminar', () => {
  const g = { tipo: 'gachamon', i: 1, j: 1 }, tu = { tipo: 'tu', i: 1, j: 1 };
  assert.deepEqual(p.ordenDePintado([tu, g]), [g, tu]);
  const cruzando = [{ tipo: 'gachamon', i: 1.5, j: 1 }, { tipo: 'gachamon', i: 1, j: 1.5 }, { tipo: 'mueble', i: 2, j: 2 }];
  assert.equal(p.ordenDePintado(cruzando).length, 3);
});

// Un 4 × 4 con una maceta en (2, 2), un felpudo en (3, 0), un cuadro en el tramo 1 de la pared derecha
// y un gachamon parado en (1, 1), justo detrás de la maceta.
const PIEZA = depto([{ id: 7, ...MACETA, x: 2, y: 2, giro: 0, casillas: [[2, 2]] },
                     { id: 9, ...FELPUDO, x: 3, y: 0, giro: 0, casillas: [[3, 0]] },
                     { id: 11, ...CUADRO, x: 1, y: -1, giro: 0, casillas: [[1, -1]] }], 4, 4);
const GENTE = [{ id: 3, i: 1, j: 1 }];
const M = p.medir(1040, 520, 4, 4);
const toco = (i, j, h = 0) => p.queSeToco(M, PIEZA, GENTE, ...p.proyectar(M, i, j, h));

test('se toca lo que se ve', () => {
  assert.deepEqual(toco(0.5, 3.5), { tipo: 'casilla', i: 0, j: 3 });
  assert.deepEqual(toco(1.5, 1.5), { tipo: 'gachamon', id: 3 });                    // sus pies
  assert.deepEqual(toco(1.5, 1.5, 0.5 * M.tw), { tipo: 'gachamon', id: 3 });        // su cabeza, sobre la casilla de atrás
  assert.deepEqual(toco(2.5, 2.5), { tipo: 'mueble', id: 7 });                      // el pie de la maceta
  assert.deepEqual(toco(2.95, 2.05, 0.5 * M.tw), { tipo: 'mueble', id: 7 });        // su costado, a media altura
  assert.deepEqual(toco(2.5, 2.5, 0.75 * M.tw), { tipo: 'gachamon', id: 3 });       // donde se cruzan, el gachamon
  assert.deepEqual(toco(3.5, 0.5), { tipo: 'casilla', i: 3, j: 0, mueble: 9 });     // lo que se pisa
  assert.deepEqual(toco(1.5, 0, M.pared / 2), { tipo: 'mueble', id: 11 });          // el cuadro
  assert.deepEqual(toco(3.5, 0, M.pared / 2), { tipo: 'tramo', i: 3, j: -1 });
  assert.equal(p.queSeToco(M, PIEZA, GENTE, 2, 2), null);                           // una esquina del lienzo
});

test('de dos gachamones que se tapan, el de delante', () => {
  const dos = [{ id: 1, i: 1, j: 1 }, { id: 2, i: 2, j: 2 }];
  const punto = p.proyectar(M, 2.5, 2.5, 0.6 * M.tw);                               // la cabeza del de delante, sobre el de atrás
  assert.deepEqual(p.queSeToco(M, depto([], 4, 4), dos, ...punto), { tipo: 'gachamon', id: 2 });
  assert.deepEqual(p.queSeToco(M, depto([], 4, 4), dos.slice().reverse(), ...punto), { tipo: 'gachamon', id: 2 });
});

test('la esquina vacía del recuadro de un mueble no es el mueble', () => {
  const caja = p.cajaDelMueble(M, MACETA, 2, 2, 0);
  const ahi = p.queSeToco(M, PIEZA, [], caja.x + 2, caja.y + 2);
  assert.ok(ahi === null || ahi.tipo !== 'mueble' || ahi.id !== 7);
});

test('quien está en la puerta se pinta en su umbral', () => {
  assert.deepEqual(p.umbralDe([-1, 2]), [-0.6, 2]);
  assert.deepEqual(p.umbralDe([1, -1]), [1, -0.6]);
  const m = p.medir(380, 310, 3, 3);
  const [x, y] = p.proyectar(m, -0.6 + 0.5, 2 + 0.5);
  const caja = p.cajaDelMueble(m, { ancho: 1, fondo: 1, capa: 'pared' }, -1, 2, 0);
  assert.ok(x >= caja.x && x <= caja.x + caja.ancho);
  assert.ok(y <= caja.y + caja.alto && y >= caja.y + caja.alto - m.th);
});

test('en la puerta se pinta antes que lo que tiene delante', () => {
  const tu = { tipo: 'tu', i: -0.6, j: 2 };
  const maceta = { tipo: 'mueble', i: 0, j: 2, a: 1, f: 1 };
  assert.deepEqual(p.ordenDePintado([maceta, tu]), [tu, maceta]);
});
