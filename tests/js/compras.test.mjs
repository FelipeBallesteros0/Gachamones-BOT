import test from 'node:test';
import assert from 'node:assert/strict';
import {
  loQueTraeLaCasa, preguntaDeCompra, preguntaDeMejora, preguntaDeVenta, quienesViven,
} from '../../web/static/js/compras.js';

test('la pregunta dice el precio con su moneda, en singular cuando es una', () => {
  assert.equal(preguntaDeCompra(10, 'monedas'), '¿Comprar por 10 monedas?');
  assert.equal(preguntaDeCompra(1, 'monedas'), '¿Comprar por 1 moneda?');
  assert.equal(preguntaDeCompra(60, 'gemas'), '¿Comprar por 60 gemas?');
  assert.equal(preguntaDeCompra(1, 'gemas'), '¿Comprar por 1 gema?');
});

test('vender dice lo que pasa con lo que hay dentro, y sólo con lo que hay', () => {
  const casa = { nombre: 'Casa pequeña', dan: 160, muebles: 2, viven: 3, plantados: 1 };
  assert.equal(preguntaDeVenta(casa),
    '¿Vender tu casa pequeña por 160 monedas? Sus 2 muebles quedan guardados, sus 3 gachamones se van al refugio y lo plantado se pierde.');
  assert.equal(preguntaDeVenta({ ...casa, muebles: 1, viven: 1, plantados: 0 }),
    '¿Vender tu casa pequeña por 160 monedas? Su mueble queda guardado y su gachamon se va al refugio.');
  assert.equal(preguntaDeVenta({ ...casa, muebles: 0, viven: 0, plantados: 0 }),
    '¿Vender tu casa pequeña por 160 monedas?');
});

test('vender nombra cada cosa sola, y lo primero que dice empieza en mayúscula', () => {
  const vacia = { nombre: 'Casa grande', dan: 960, muebles: 0, viven: 0, plantados: 0 };
  assert.equal(preguntaDeVenta({ ...vacia, plantados: 4 }),
    '¿Vender tu casa grande por 960 monedas? Lo plantado se pierde.');
  assert.equal(preguntaDeVenta({ ...vacia, viven: 2, plantados: 1 }),
    '¿Vender tu casa grande por 960 monedas? Sus 2 gachamones se van al refugio y lo plantado se pierde.');
  assert.equal(preguntaDeVenta({ ...vacia, muebles: 5 }),
    '¿Vender tu casa grande por 960 monedas? Sus 5 muebles quedan guardados.');
  assert.equal(preguntaDeVenta({ ...vacia, dan: 1 }), '¿Vender tu casa grande por 1 moneda?');
});

test('mejorar dice de qué a qué y por cuánto', () => {
  assert.equal(preguntaDeMejora({ nombre: 'Casa pequeña' }, { nombre: 'Casa mediana', cuesta: 340 }),
    '¿Mejorar tu casa pequeña a casa mediana por 340 monedas?');
});

test('una casa a la venta dice cuántos caben, sus huecos para muebles y sus bancales', () => {
  assert.equal(loQueTraeLaCasa({ aforo: 3, huecos: 3, bancales: 1 }),
    'Caben 3 gachamones · 3 huecos para muebles · 1 bancal');
  assert.equal(loQueTraeLaCasa({ aforo: 1, huecos: 1, bancales: 7 }),
    'Cabe 1 gachamon · 1 hueco para muebles · 7 bancales');
  assert.equal(loQueTraeLaCasa({ aforo: 6, huecos: 6, bancales: 0 }),
    'Caben 6 gachamones · 6 huecos para muebles');
});

test('una casa tuya dice cuántos viven en ella y cuántos caben', () => {
  assert.equal(quienesViven({ viven: 0, aforo: 3 }), 'No vive nadie · caben 3');
  assert.equal(quienesViven({ viven: 1, aforo: 3 }), 'Vive 1 gachamon · caben 3');
  assert.equal(quienesViven({ viven: 4, aforo: 3 }), 'Viven 4 gachamones · caben 3');
  assert.equal(quienesViven({ viven: 1, aforo: 1 }), 'Vive 1 gachamon · cabe 1');
});
