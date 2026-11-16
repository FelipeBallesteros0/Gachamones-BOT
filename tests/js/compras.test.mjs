import test from 'node:test';
import assert from 'node:assert/strict';
import * as compras from '../../web/static/js/compras.js';

const { preguntaDeCompra } = compras;

test('la pregunta dice el precio con su moneda, en singular cuando es una', () => {
  assert.equal(preguntaDeCompra(10, 'monedas'), '¿Comprar por 10 monedas?');
  assert.equal(preguntaDeCompra(1, 'monedas'), '¿Comprar por 1 moneda?');
  assert.equal(preguntaDeCompra(60, 'gemas'), '¿Comprar por 60 gemas?');
  assert.equal(preguntaDeCompra(1, 'gemas'), '¿Comprar por 1 gema?');
});

test('la tienda ya no habla de casas: sólo pregunta antes de comprar', () => {
  assert.deepEqual(Object.keys(compras), ['preguntaDeCompra']);
});
