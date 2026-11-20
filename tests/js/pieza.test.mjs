import test from 'node:test';
import assert from 'node:assert/strict';
import { dibujarPieza, dondeSePintaElGachamon } from '../../web/static/js/pieza.js';
import { cajaDelGachamon, medir, proyectar } from '../../web/static/js/proyeccion.js';

// Un contexto de lienzo que acepta todo lo que se le pida y lo apunta en
// `trazos` como `[nombre, argumentos]`.
function lienzo() {
  const trazos = [];
  const ctx = new Proxy({}, {
    get: (_, nombre) => (...argumentos) => { trazos.push([nombre, argumentos]); },
    set: () => true,
  });
  return { ctx, trazos };
}

const M = medir(380, 310, 3, 3);
const PIEZA = { ancho: 3, fondo: 3, puestos: [] };
const RETRATO = '/monsteropolis/retrato/pollito/bebe/feliz/sin.png';
// Un retrato más alto que ancho, como los de la página, y otro más ancho que alto.
const ALTO = { naturalWidth: 48, naturalHeight: 84 };
const ANCHO = { naturalWidth: 120, naturalHeight: 60 };

// Pinta la pieza vacía con ese gachamon y devuelve lo que se pintó.
function pintarCon(g, cargadas) {
  const { ctx, trazos } = lienzo();
  dibujarPieza(ctx, M, { depto: PIEZA, cargadas, gachamones: [g], tu: null });
  return trazos;
}

const conRetrato = (imagen) => new Map([[RETRATO, { ruta: RETRATO, imagen }]]);
const cerca = (a, b) => Math.abs(a - b) < 1e-9;

test('dondeSePintaElGachamon da el rectángulo de su `drawImage`, con y sin salto', () => {
  for (const imagen of [ALTO, ANCHO]) {
    for (const sube of [0, 17.5]) {
      const g = { id: 1, i: 1, j: 2, retrato: RETRATO, activo: false, sube };
      const cargadas = conRetrato(imagen);
      const dibujos = pintarCon(g, cargadas).filter(([nombre, [img]]) => nombre === 'drawImage' && img === imagen);
      assert.equal(dibujos.length, 1);
      const [, [, x, y, ancho, alto]] = dibujos[0];
      assert.deepEqual(dondeSePintaElGachamon(M, cargadas, g), { x, y, ancho, alto, imagen });
    }
  }
});

test('el dibujo de un gachamon cabe en su caja sin deformarse, centrado en su casilla y con los pies levantados lo que salta', () => {
  const caja = cajaDelGachamon(M, 1, 2);
  const [centro] = proyectar(M, 1.5, 2.5);
  const quieto = dondeSePintaElGachamon(M, conRetrato(ALTO), { i: 1, j: 2, retrato: RETRATO });
  assert.ok(cerca(quieto.alto, caja.alto) && cerca(quieto.ancho, caja.alto * 48 / 84));
  assert.ok(cerca(quieto.x + quieto.ancho / 2, centro) && cerca(quieto.y + quieto.alto, caja.y + caja.alto));
  const saltando = dondeSePintaElGachamon(M, conRetrato(ALTO), { i: 1, j: 2, retrato: RETRATO, sube: 20 });
  assert.deepEqual([saltando.x, saltando.ancho, saltando.alto], [quieto.x, quieto.ancho, quieto.alto]);
  assert.ok(cerca(saltando.y, quieto.y - 20));
  const ancho = dondeSePintaElGachamon(M, conRetrato(ANCHO), { i: 1, j: 2, retrato: RETRATO });
  assert.ok(cerca(ancho.ancho, caja.ancho) && cerca(ancho.alto, caja.ancho / 2));
  assert.ok(cerca(ancho.x, caja.x) && cerca(ancho.y + ancho.alto, caja.y + caja.alto));
});

test('sin su imagen (no cargó o todavía no llega), el rectángulo es su recuadro entero, con el salto, y su imagen `null`', () => {
  const caja = cajaDelGachamon(M, 1, 2);
  const g = { id: 1, i: 1, j: 2, retrato: RETRATO, activo: false, sube: 12 };
  const recuadro = { x: caja.x, y: caja.y - 12, ancho: caja.ancho, alto: caja.alto, imagen: null };
  const fallida = new Map([[RETRATO, { ruta: RETRATO, imagen: null }]]);
  assert.deepEqual(dondeSePintaElGachamon(M, fallida, g), recuadro);
  assert.deepEqual(dondeSePintaElGachamon(M, new Map(), g), recuadro);
  // El que no cargó se ve como su recuadro, justo ahí; el que todavía no llega, no se pinta.
  const recortes = pintarCon(g, fallida).filter(([nombre]) => nombre === 'rect');
  assert.deepEqual(recortes.map(([, argumentos]) => argumentos), [[recuadro.x, recuadro.y, recuadro.ancho, recuadro.alto]]);
  assert.deepEqual(pintarCon(g, new Map()).filter(([nombre]) => nombre === 'rect' || nombre === 'drawImage'), []);
});
