import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatoEspera, elegirGlobo, dondeVive, cuantasMonedas, cuantasGemas, avisoDelCuidado,
  avisosDeMedallas, seCelebraLaEvolucion,
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

const delLugar = { tipo: 'lugar', texto: 'Aquí huele a pan.' };

test('al llegar habla del lugar, salvo que necesite algo', () => {
  for (const azar of [primero, ultimo]) {
    assert.equal(elegirGlobo([charla, delLugar, charlaOtra], null, azar, true), delLugar);
    assert.equal(elegirGlobo([charla, delLugar, pide], null, azar, true), pide);
  }
});

test('si no está llegando, del lugar no dice nada', () => {
  for (const azar of [primero, ultimo]) {
    assert.notEqual(elegirGlobo([charla, delLugar, charlaOtra], null, azar), delLugar);
    assert.notEqual(elegirGlobo([charla, delLugar, charlaOtra], null, azar, false), delLugar);
  }
  assert.equal(elegirGlobo([delLugar], null, primero), null);
});

test('dónde vive se dice en minúscula y con su preposición', () => {
  assert.equal(dondeVive('propia'), 'vive en tu casa');
  assert.equal(dondeVive('refugio'), 'vive en el refugio');
  assert.equal(dondeVive('intemperie'), 'vive a la intemperie');
  assert.equal(dondeVive('otra cosa'), '');
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

const conEtapa = (etapa) => ({ gachamon: { etapa } });

test('la evolución se celebra cuando el servidor lo dice', () => {
  assert.equal(seCelebraLaEvolucion({ evoluciono: true, estado: conEtapa('nino') }, 'bebe'), true);
  // Aunque la etapa que había no se supiera.
  assert.equal(seCelebraLaEvolucion({ evoluciono: true, estado: conEtapa('nino') }, undefined), true);
});

test('la evolución se celebra también si la etapa cambió aunque el servidor no lo diga', () => {
  // Un reintento del mismo cuidado: el servidor contesta sin la marca.
  assert.equal(seCelebraLaEvolucion({ evoluciono: false, estado: conEtapa('nino') }, 'bebe'), true);
});

test('sin marca y con la misma etapa no hay nada que celebrar', () => {
  assert.equal(seCelebraLaEvolucion({ evoluciono: false, estado: conEtapa('bebe') }, 'bebe'), false);
  assert.equal(seCelebraLaEvolucion({ evoluciono: false, estado: { gachamon: null } }, 'bebe'), false);
  assert.equal(seCelebraLaEvolucion({ evoluciono: false }, 'bebe'), false);
  assert.equal(seCelebraLaEvolucion({ evoluciono: false, estado: conEtapa('nino') }, undefined), false);
  assert.equal(seCelebraLaEvolucion(null, 'bebe'), false);
});

test('cada medalla nueva dice su nombre y sus gemas, en singular cuando es una', () => {
  assert.deepEqual(avisosDeMedallas({ logros: [
    { nombre: 'De la alfa', gemas: 25 }, { nombre: 'Uno suelto', gemas: 1 },
  ] }), ['🏅 De la alfa · +25 gemas', '🏅 Uno suelto · +1 gema']);
});

test('sin medallas, o con algo que no lo es, no se dice nada', () => {
  assert.deepEqual(avisosDeMedallas({ logros: [] }), []);
  assert.deepEqual(avisosDeMedallas({}), []);
  assert.deepEqual(avisosDeMedallas(null), []);
  assert.deepEqual(avisosDeMedallas({ logros: 'De la alfa' }), []);
  assert.deepEqual(avisosDeMedallas({ logros: [null, { nombre: 7, gemas: 1 }, { nombre: 'X' },
    { nombre: '', gemas: 2 }, { nombre: 'Bien', gemas: 3 }] }), ['🏅 Bien · +3 gemas']);
});
