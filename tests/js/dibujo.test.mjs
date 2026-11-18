import test from 'node:test';
import assert from 'node:assert/strict';
import { dibujarHuevo } from '../../web/static/js/dibujo.js';

// Un contexto con sólo las herramientas que dice `dibujo.js`; apunta cada óvalo con su color.
const lienzo = () => {
  const trazos = [];
  let color = null;
  return {
    trazos,
    set fillStyle(valor) { color = valor; },
    get fillStyle() { return color; },
    ellipse: (...forma) => trazos.push([color, ...forma]),
    save() {}, restore() {}, scale() {}, beginPath() {}, fill() {},
  };
};

test('el huevo de la pantalla de entrar se dibuja entero y siempre igual, con las herramientas que dice dibujo.js', () => {
  const uno = lienzo();
  const otro = lienzo();
  dibujarHuevo(uno, 4);
  dibujarHuevo(otro, 4);
  assert.ok(uno.trazos.length > 0);
  assert.deepEqual(otro.trazos, uno.trazos);
  // Ya no hay huevo roto: sólo se le dice dónde y a qué escala.
  assert.equal(dibujarHuevo.length, 2);
});
