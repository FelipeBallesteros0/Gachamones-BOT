import test from 'node:test';
import assert from 'node:assert/strict';
import { dibujarHuevo } from '../../web/static/js/dibujo.js';

const lienzo = () => {
  const trazos = [];
  let color = null;
  return {
    trazos,
    set fillStyle(valor) { color = valor; },
    get fillStyle() { return color; },
    fillRect: (...caja) => trazos.push([color, ...caja]),
    save() {}, restore() {}, translate() {}, scale() {}, beginPath() {}, ellipse() {}, fill() {},
  };
};

test('el huevo se dibuja con las mismas herramientas, y roto se ve distinto', () => {
  const entero = lienzo();
  const roto = lienzo();
  dibujarHuevo(entero, 4, false);
  dibujarHuevo(roto, 4, true);
  assert.notEqual(JSON.stringify(roto.trazos), JSON.stringify(entero.trazos));
});
