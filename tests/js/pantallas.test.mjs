import test from 'node:test';
import assert from 'node:assert/strict';
import { siguiente } from '../../web/static/js/pantallas.js';

const sesion = { usuario: 'felipe' };
const gachamon = { nombre: 'Pelusa', espera_nombre: false };
const avatar = { nombre: 'Feli' };
const estado = (cambios = {}) => ({ avatar, gachamon, difunto: null, ...cambios });

test('sin sesión, a entrar', () => {
  assert.equal(siguiente(null, null, null), 'sesion');
});

test('una cuenta nueva ve la bienvenida', () => {
  assert.equal(siguiente(sesion, { estado: 'nueva' }, null), 'bienvenida');
});

test('con cuenta y sin avatar, al avatar', () => {
  for (const cuenta of [{ estado: 'web' }, { estado: 'vinculada' }]) {
    assert.equal(siguiente(sesion, cuenta, estado({ avatar: null })), 'avatar');
  }
});

test('el avatar va antes que cualquier otra cosa del juego', () => {
  const todo = estado({ avatar: null, difunto: { nombre: 'Viejo' }, gachamon: null });
  assert.equal(siguiente(sesion, { estado: 'vinculada' }, todo), 'avatar');
});

test('un difunto pendiente se cuenta antes de seguir', () => {
  assert.equal(siguiente(sesion, { estado: 'web' }, estado({ difunto: { nombre: 'Viejo' } })), 'difunto');
  assert.equal(
    siguiente(sesion, { estado: 'web' }, estado({ difunto: { nombre: 'Viejo' }, gachamon: null })),
    'difunto',
  );
});

test('sin gachamon, al huevo', () => {
  assert.equal(siguiente(sesion, { estado: 'web' }, estado({ gachamon: null })), 'huevo');
});

test('el que espera nombre va al bautizo', () => {
  const sinNombre = estado({ gachamon: { nombre: 'Piollito', espera_nombre: true } });
  assert.equal(siguiente(sesion, { estado: 'web' }, sinNombre), 'bautizo');
});

test('con todo en su sitio, al lugar', () => {
  assert.equal(siguiente(sesion, { estado: 'web' }, estado()), 'lugar');
  assert.equal(siguiente(sesion, { estado: 'vinculada' }, estado()), 'lugar');
});
