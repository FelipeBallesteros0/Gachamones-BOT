import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatoEspera, elegirGlobo, nombreDelHogar, cuantasMonedas, cuantasGemas, avisoDelCuidado,
} from '../../web/static/js/tiempo.js';

test('la espera se lee como la diría una persona', () => {
  assert.equal(formatoEspera(0), '');
  assert.equal(formatoEspera(-5), '');
  assert.equal(formatoEspera(1), '1 s');
  assert.equal(formatoEspera(59), '59 s');
  assert.equal(formatoEspera(60), '1 min');
  assert.equal(formatoEspera(61), '2 min');
  assert.equal(formatoEspera(19 * 60), '19 min');
  assert.equal(formatoEspera(3600), '1 h');
  assert.equal(formatoEspera(3900), '1 h 5 min');
  assert.equal(formatoEspera(113 * 60), '1 h 53 min');
});

test('la espera redondea hacia arriba, como la del bot', () => {
  assert.equal(formatoEspera(0.4), '1 s');
  assert.equal(formatoEspera(3599), '1 h');
});

const pide = { tipo: 'necesidad', texto: 'Tengo hambre.' };
const pideOtra = { tipo: 'necesidad', texto: 'Estoy sucia.' };
const charla = { tipo: 'suelta', texto: '¿Cómo estás?' };
const charlaOtra = { tipo: 'suelta', texto: 'Qué lindo día.' };
const primero = () => 0;
const ultimo = () => 0.999;

test('una necesidad va antes que la charla', () => {
  for (const azar of [primero, ultimo]) {
    assert.equal(elegirGlobo([charla, pide, charlaOtra], null, azar), pide);
  }
});

test('no repite el anterior si hay otro del mismo tipo', () => {
  assert.equal(elegirGlobo([pide, pideOtra], pide.texto, primero), pideOtra);
  assert.equal(elegirGlobo([charla, charlaOtra], charlaOtra.texto, ultimo), charla);
});

test('con una sola frase la repite, y sin frases no dice nada', () => {
  assert.equal(elegirGlobo([charla], charla.texto, primero), charla);
  assert.equal(elegirGlobo([], null, primero), null);
});

test('el azar elige entre las candidatas', () => {
  assert.equal(elegirGlobo([charla, charlaOtra], null, primero), charla);
  assert.equal(elegirGlobo([charla, charlaOtra], null, ultimo), charlaOtra);
});

test('para evitar repetir no salta de la necesidad a la charla', () => {
  assert.equal(elegirGlobo([pide, charla], pide.texto, primero), pide);
});

test('el hogar tiene un nombre que se entiende', () => {
  assert.equal(nombreDelHogar('propia'), 'Tu casa');
  assert.equal(nombreDelHogar('refugio'), 'Refugio');
  assert.equal(nombreDelHogar('intemperie'), 'A la intemperie');
});

test('un cuidado que sale bien dice su frase', () => {
  assert.equal(avisoDelCuidado({ ok: true, mensaje: 'Juegan un rato. Está encantada.' }),
    'Juegan un rato. Está encantada.');
  assert.equal(avisoDelCuidado({ ok: true, mensaje: 'Se ha empachado. No tenía nada de hambre.' }),
    'Se ha empachado. No tenía nada de hambre.');
});

test('un cuidado que la regla no deja también dice su frase', () => {
  assert.equal(avisoDelCuidado({ ok: false, mensaje: 'Tu gachamon ya no está entre nosotros.' }),
    'Tu gachamon ya no está entre nosotros.');
});

test('sin frase, sólo el que no salió dice algo: «Todavía no.»', () => {
  assert.equal(avisoDelCuidado({ ok: false, mensaje: '' }), 'Todavía no.');
  assert.equal(avisoDelCuidado({ ok: false }), 'Todavía no.');
  assert.equal(avisoDelCuidado({ ok: true, mensaje: '' }), '');
  assert.equal(avisoDelCuidado({ ok: true }), '');
});

test('un mensaje que no es una frase cuenta como si no hubiera', () => {
  for (const mensaje of [null, 7, ['Ñam.'], { texto: 'Ñam.' }, '   ']) {
    assert.equal(avisoDelCuidado({ ok: true, mensaje }), '');
    assert.equal(avisoDelCuidado({ ok: false, mensaje }), 'Todavía no.');
  }
});

test('las monedas y las gemas van en singular cuando es una', () => {
  assert.equal(cuantasMonedas(1), '1 moneda');
  assert.equal(cuantasMonedas(2), '2 monedas');
  assert.equal(cuantasMonedas(0), '0 monedas');
  assert.equal(cuantasGemas(1), '1 gema');
  assert.equal(cuantasGemas(30), '30 gemas');
});
