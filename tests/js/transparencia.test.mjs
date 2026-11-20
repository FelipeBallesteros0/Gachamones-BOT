import test from 'node:test';
import assert from 'node:assert/strict';

// Lo justo de un documento: lienzos que leen los píxeles de lo que se les
// pinta con `alfaDe(imagen, u, v)` y apuntan cada lectura en `leidas`; con
// `noDejaLeer`, leer falla, como un lienzo de otra página.
let alfaDe = () => 255;
let noDejaLeer = false;
const leidas = [];
globalThis.document = {
  createElement(etiqueta) {
    assert.equal(etiqueta, 'canvas');
    let pintada = null;
    const contexto = {
      drawImage(imagen) { pintada = imagen; },
      getImageData(x0, y0, ancho, alto) {
        if (noDejaLeer) throw new Error('El lienzo no deja leer sus píxeles.');
        leidas.push(pintada);
        const data = new Uint8ClampedArray(ancho * alto * 4);
        for (let v = 0; v < alto; v += 1) for (let u = 0; u < ancho; u += 1) data[(v * ancho + u) * 4 + 3] = alfaDe(pintada, u, v);
        return { width: ancho, height: alto, data };
      },
    };
    return { width: 0, height: 0, getContext: () => contexto };
  },
};

const { seVe } = await import('../../web/static/js/transparencia.js');

// Un dibujo de 4 × 2 en el que sólo se ven dos píxeles: (1, 0), apenas, y (3, 1).
const VISIBLES = new Map([['1,0', 1], ['3,1', 255]]);
const dosPuntos = (imagen, u, v) => VISIBLES.get(`${u},${v}`) || 0;
const imagen = (src) => ({ src, naturalWidth: 4, naturalHeight: 2 });
// Pintado al quíntuple en (10, 20): cada píxel, un cuadro de 10 × 10.
const CAJA = { x: 10, y: 20, ancho: 40, alto: 20 };

test('fuera de su caja no se ve; dentro, sólo donde el píxel de su dibujo no es del todo transparente', () => {
  alfaDe = dosPuntos;
  const dibujo = imagen('/gachamon/retrato/a.png');
  assert.equal(seVe(dibujo, CAJA, 15, 25), false);                     // (0, 0): transparente
  assert.equal(seVe(dibujo, CAJA, 25, 25), true);                      // (1, 0): alfa 1 ya se ve
  assert.equal(seVe(dibujo, CAJA, 29.9, 29.9), true);
  assert.equal(seVe(dibujo, CAJA, 30, 25), false);                     // (2, 0)
  assert.equal(seVe(dibujo, CAJA, 45, 35), true);                      // (3, 1)
  assert.equal(seVe(dibujo, CAJA, 50, 40), true);                      // su esquina de abajo, todavía (3, 1)
  for (const [x, y] of [[9.9, 25], [25, 19.9], [50.1, 35], [45, 40.1]]) assert.equal(seVe(dibujo, CAJA, x, y), false);
});

test('sin imagen (se ve su recuadro), cuenta su caja entera', () => {
  for (const sinDibujo of [null, { src: '/gachamon/retrato/vacio.png', naturalWidth: 0, naturalHeight: 0 }]) {
    assert.equal(seVe(sinDibujo, CAJA, 15, 25), true);
    assert.equal(seVe(sinDibujo, CAJA, 50, 40), true);
    assert.equal(seVe(sinDibujo, CAJA, 51, 40), false);
  }
});

test('los píxeles de una imagen se leen una vez, y otra vez sólo si cambia su dibujo', () => {
  alfaDe = dosPuntos;
  leidas.length = 0;
  const dibujo = imagen('/gachamon/retrato/b.png');
  for (let vez = 0; vez < 3; vez += 1) {
    seVe(dibujo, CAJA, 15, 25);
    seVe(dibujo, CAJA, 45, 35);
  }
  seVe(dibujo, CAJA, 5, 5);                                            // fuera de la caja ni se mira
  assert.deepEqual(leidas, [dibujo]);
  const otro = imagen('/gachamon/retrato/c.png');
  seVe(otro, CAJA, 15, 25);
  assert.deepEqual(leidas, [dibujo, otro]);
  // El mismo `<img>` con otro dibujo: lo que se ve ahora es el nuevo.
  alfaDe = () => 255;
  dibujo.currentSrc = '/gachamon/retrato/d.png';
  assert.equal(seVe(dibujo, CAJA, 15, 25), true);
  assert.deepEqual(leidas, [dibujo, otro, dibujo]);
});

test('si sus píxeles no se pueden leer, cuenta su caja entera', () => {
  alfaDe = dosPuntos;
  noDejaLeer = true;
  try {
    const dibujo = imagen('/gachamon/retrato/e.png');
    assert.equal(seVe(dibujo, CAJA, 15, 25), true);
    assert.equal(seVe(dibujo, CAJA, 9, 25), false);
  } finally {
    noDejaLeer = false;
  }
});
