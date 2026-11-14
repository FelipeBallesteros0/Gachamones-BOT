import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  cambioLaCuenta, hayQueRecargar, ofreceLaIncubadora, puedeTraerDeDiscord, siguiente, trasFallarLaLlegada,
  trasUnFalloAlArrancar,
} from '../../web/static/js/pantallas.js';

const sesion = { usuario: 'felipe' };
const gachamon = { nombre: 'Pelusa', espera_nombre: false };
const avatar = { nombre: 'Feli' };
const estado = (cambios = {}) => ({ avatar, gachamon, difunto: null, ...cambios });
// Un jugador con su gachamon, listo para ver el lugar.
const cuenta = { estado: 'web' };
const jugando = estado();

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

test('el pueblo sólo se ve cuando todo lo demás está en orden', () => {
  assert.equal(siguiente(sesion, { estado: 'web' }, estado(), 'pueblo'), 'pueblo');
  assert.equal(siguiente(sesion, { estado: 'web' }, estado()), 'lugar');
  assert.equal(siguiente(sesion, { estado: 'web' }, estado({ difunto: { nombre: 'Viejo' } }), 'pueblo'), 'difunto');
  assert.equal(siguiente(sesion, { estado: 'web' }, estado({ gachamon: null }), 'pueblo'), 'huevo');
  assert.equal(siguiente(null, null, null, 'pueblo'), 'sesion');
});

test('la tienda sólo se abre donde el lugar la ofrece', () => {
  const en = (ofrece) => ({ ...jugando, lugar: { clave: 'x', nombre: 'X', ofrece } });
  assert.equal(siguiente(sesion, cuenta, en(['tienda']), 'tienda'), 'tienda');
  assert.equal(siguiente(sesion, cuenta, en([]), 'tienda'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, { ...jugando, lugar: { clave: 'x', nombre: 'X' } }, 'tienda'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, en([]), 'mochila'), 'mochila');
  assert.equal(siguiente(sesion, cuenta, en(['tienda']), 'otra cosa'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, { ...jugando, difunto: { nombre: 'Pelusa' } }, 'tienda'), 'difunto');
});

test('lo que va antes del juego gana a la tienda y a la mochila', () => {
  // Parado en la tienda: si se pudiera, se abriría.
  const enLaTienda = (cambios = {}) => ({
    ...jugando, lugar: { clave: 'x', nombre: 'X', ofrece: ['tienda'] }, ...cambios,
  });
  for (const vista of ['tienda', 'mochila']) {
    assert.equal(siguiente(null, null, null, vista), 'sesion', vista);
    assert.equal(siguiente(sesion, { estado: 'nueva' }, null, vista), 'bienvenida', vista);
    assert.equal(siguiente(sesion, cuenta, enLaTienda({ avatar: null }), vista), 'avatar', vista);
    assert.equal(siguiente(sesion, cuenta, enLaTienda({ difunto: { nombre: 'Viejo' } }), vista), 'difunto', vista);
    assert.equal(siguiente(sesion, cuenta, enLaTienda({ gachamon: null }), vista), 'huevo', vista);
    assert.equal(
      siguiente(sesion, cuenta, enLaTienda({ gachamon: { nombre: 'Piollito', espera_nombre: true } }), vista),
      'bautizo', vista,
    );
    assert.equal(siguiente(sesion, cuenta, enLaTienda(), vista), vista);
  }
});

test('la ficha y el ropero se abren con todo en orden, estés donde estés, como la mochila', () => {
  const en = (ofrece) => ({ ...jugando, lugar: { clave: 'x', nombre: 'X', ofrece } });
  for (const vista of ['ficha', 'ropero']) {
    assert.equal(siguiente(sesion, cuenta, jugando, vista), vista, vista);
    assert.equal(siguiente(sesion, cuenta, en([]), vista), vista, vista);
    assert.equal(siguiente(sesion, cuenta, en(['tienda']), vista), vista, vista);
  }
});

test('lo que va antes del juego gana a la ficha y al ropero', () => {
  for (const vista of ['ficha', 'ropero']) {
    assert.equal(siguiente(null, null, null, vista), 'sesion', vista);
    assert.equal(siguiente(sesion, { estado: 'nueva' }, null, vista), 'bienvenida', vista);
    assert.equal(siguiente(sesion, cuenta, estado({ avatar: null }), vista), 'avatar', vista);
    assert.equal(siguiente(sesion, cuenta, estado({ difunto: { nombre: 'Viejo' } }), vista), 'difunto', vista);
    assert.equal(siguiente(sesion, cuenta, estado({ gachamon: null }), vista), 'huevo', vista);
    assert.equal(
      siguiente(sesion, cuenta, estado({ gachamon: { nombre: 'Piollito', espera_nombre: true } }), vista),
      'bautizo', vista,
    );
  }
});

test('la incubadora se ofrece sólo donde el lugar la tiene', () => {
  assert.equal(ofreceLaIncubadora({ ofrece: ['incubadora'] }), true);
  assert.equal(ofreceLaIncubadora({ ofrece: ['tienda', 'incubadora'] }), true);
  assert.equal(ofreceLaIncubadora({ ofrece: [] }), false);
  assert.equal(ofreceLaIncubadora({ ofrece: ['tienda'] }), false);
  assert.equal(ofreceLaIncubadora({ clave: 'x', nombre: 'X' }), false);
  assert.equal(ofreceLaIncubadora(null), false);
  assert.equal(ofreceLaIncubadora(undefined), false);
});

test('la incubadora sólo se abre donde el lugar la ofrece', () => {
  const en = (ofrece) => ({ ...jugando, lugar: { clave: 'x', nombre: 'X', ofrece } });
  assert.equal(siguiente(sesion, cuenta, en(['incubadora']), 'incubadora'), 'incubadora');
  assert.equal(siguiente(sesion, cuenta, en([]), 'incubadora'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, en(['tienda']), 'incubadora'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, { ...jugando, lugar: { clave: 'x', nombre: 'X' } }, 'incubadora'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, jugando, 'incubadora'), 'lugar');
  // Estar en la incubadora no abre nada solo, ni la tienda.
  assert.equal(siguiente(sesion, cuenta, en(['incubadora'])), 'lugar');
  assert.equal(siguiente(sesion, cuenta, en(['incubadora']), 'tienda'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, en(['incubadora']), 'mochila'), 'mochila');
});

test('lo que va antes del juego gana a la incubadora', () => {
  const enLaIncubadora = (cambios = {}) => ({
    ...jugando, lugar: { clave: 'x', nombre: 'X', ofrece: ['incubadora'] }, ...cambios,
  });
  const vista = 'incubadora';
  assert.equal(siguiente(null, null, null, vista), 'sesion');
  assert.equal(siguiente(sesion, { estado: 'nueva' }, null, vista), 'bienvenida');
  assert.equal(siguiente(sesion, cuenta, enLaIncubadora({ avatar: null }), vista), 'avatar');
  assert.equal(siguiente(sesion, cuenta, enLaIncubadora({ difunto: { nombre: 'Viejo' } }), vista), 'difunto');
  assert.equal(siguiente(sesion, cuenta, enLaIncubadora({ gachamon: null }), vista), 'huevo');
  assert.equal(
    siguiente(sesion, cuenta, enLaIncubadora({ gachamon: { nombre: 'Piollito', espera_nombre: true } }), vista),
    'bautizo',
  );
});

// El recluta que espera nombre cuando no queda ninguna activa (`estado.sin_nombre`).
const recluta = { id: 7, nombre_especie: 'Pulpito', retrato: '/gachamon/retrato/pulpo/bebe/feliz/sin.png' };

test('sin gachamon y con un recluta sin nombre, al bautizo y no al huevo', () => {
  assert.equal(siguiente(sesion, cuenta, estado({ gachamon: null, sin_nombre: recluta })), 'bautizo');
  assert.equal(siguiente(sesion, { estado: 'vinculada' }, estado({ gachamon: null, sin_nombre: recluta })), 'bautizo');
  // Sin recluta, el huevo de siempre.
  assert.equal(siguiente(sesion, cuenta, estado({ gachamon: null, sin_nombre: null })), 'huevo');
  // Con un gachamon activo, el recluta espera en la incubadora sin cambiar nada.
  assert.equal(siguiente(sesion, cuenta, estado({ sin_nombre: recluta })), 'lugar');
  // Ninguna vista se salta el bautizo.
  for (const vista of ['pueblo', 'tienda', 'mochila', 'ficha', 'ropero', 'incubadora']) {
    const enLaIncubadora = estado({
      gachamon: null, sin_nombre: recluta, lugar: { clave: 'x', nombre: 'X', ofrece: ['incubadora', 'tienda'] },
    });
    assert.equal(siguiente(sesion, cuenta, enLaIncubadora, vista), 'bautizo', vista);
  }
});

test('una muerte pendiente se cuenta antes que el bautizo del recluta', () => {
  const todo = estado({ gachamon: null, sin_nombre: recluta, difunto: { nombre: 'Viejo' } });
  assert.equal(siguiente(sesion, cuenta, todo), 'difunto');
  assert.equal(siguiente(sesion, cuenta, todo, 'incubadora'), 'difunto');
  // Y el avatar, antes que todo.
  assert.equal(siguiente(sesion, cuenta, { ...todo, avatar: null }), 'avatar');
});

test('lo que el cliente ofrece en un lugar lleva la clave de un lugar del pueblo', () => {
  const pueblo = JSON.parse(readFileSync(new URL('../../web/static/datos/pueblo.json', import.meta.url), 'utf8'));
  for (const clave of ['tienda', 'incubadora']) assert.ok(Object.hasOwn(pueblo.lugares, clave), clave);
});

test('si falla la llegada: si el servidor dice que no se decide de nuevo; lo demás se reintenta', () => {
  assert.equal(trasFallarLaLlegada({ estado: 401, clave: 'sin_sesion' }), 'decidir');
  assert.equal(trasFallarLaLlegada({ estado: 409, clave: 'sin_cuenta' }), 'decidir');
  assert.equal(trasFallarLaLlegada({ estado: 422, clave: 'lugar' }), 'decidir');
  assert.equal(trasFallarLaLlegada({ estado: 404, clave: null }), 'decidir');
  assert.equal(trasFallarLaLlegada({ estado: 0, clave: null }), 'reintentar');
  assert.equal(trasFallarLaLlegada({ estado: 500, clave: null }), 'reintentar');
  assert.equal(trasFallarLaLlegada({ estado: 503, clave: 'servicio' }), 'reintentar');
  assert.equal(trasFallarLaLlegada(undefined), 'reintentar');
});

test('se recarga cuando el servidor ya es de otra versión, y una sola vez por versión', () => {
  assert.equal(hayQueRecargar('aaa', 'bbb', null), true);
  assert.equal(hayQueRecargar('aaa', 'bbb', 'bbb'), false);
  assert.equal(hayQueRecargar('aaa', 'ccc', 'bbb'), true);
  assert.equal(hayQueRecargar('aaa', 'aaa', null), false);
  assert.equal(hayQueRecargar(null, 'bbb', null), false);
  assert.equal(hayQueRecargar('aaa', null, null), false);
  assert.equal(hayQueRecargar('aaa', '', null), false);
  assert.equal(hayQueRecargar('', 'bbb', null), false);
});

test('al arrancar, un 401 en cualquiera de las tres lecturas lleva a entrar', () => {
  for (const mensaje of ['Entra a Rowino para jugar.', undefined]) {
    assert.deepEqual(trasUnFalloAlArrancar({ estado: 401, clave: 'sin_sesion', mensaje }),
      { pantalla: 'sesion', mensaje: null });
  }
});

test('al arrancar, un 503 dice que el juego no está disponible, sea nuestro o del túnel', () => {
  const esperado = { pantalla: 'noCarga', mensaje: 'El juego no está disponible ahora mismo.' };
  assert.deepEqual(trasUnFalloAlArrancar({
    estado: 503, clave: 'servicio', mensaje: 'El juego no está disponible ahora mismo.',
  }), esperado);
  assert.deepEqual(trasUnFalloAlArrancar({
    estado: 503, clave: null, mensaje: 'El juego no contestó. Vuelve a intentarlo en un momento.',
  }), esperado);
});

test('al arrancar, lo demás se enseña con su mensaje para reintentar', () => {
  assert.deepEqual(trasUnFalloAlArrancar({ estado: 0, clave: null, mensaje: 'Sin red.' }),
    { pantalla: 'noCarga', mensaje: 'Sin red.' });
  assert.deepEqual(trasUnFalloAlArrancar({ estado: 500, clave: null, mensaje: '' }),
    { pantalla: 'noCarga', mensaje: null });
  assert.deepEqual(trasUnFalloAlArrancar(new Error('se rompió')), { pantalla: 'noCarga', mensaje: null });
  assert.deepEqual(trasUnFalloAlArrancar(undefined), { pantalla: 'noCarga', mensaje: null });
});

test('se ofrece traer los de Discord sólo a una cuenta web sin gachamones', () => {
  assert.equal(puedeTraerDeDiscord({ estado: 'web', tiene_gachamones: false }), true);
  assert.equal(puedeTraerDeDiscord({ estado: 'web', tiene_gachamones: true }), false);
  assert.equal(puedeTraerDeDiscord({ estado: 'vinculada', tiene_gachamones: false }), false);
  assert.equal(puedeTraerDeDiscord({ estado: 'nueva', tiene_gachamones: false }), false);
  assert.equal(puedeTraerDeDiscord(null), false);
});

test('mientras se espera el código, la cuenta cambió si se vinculó o si cambió por otro lado', () => {
  const web = { estado: 'web', tiene_gachamones: false };
  assert.equal(cambioLaCuenta(web, { ...web }), false);
  assert.equal(cambioLaCuenta(web, { estado: 'vinculada', tiene_gachamones: true }), true);
  assert.equal(cambioLaCuenta(web, { estado: 'vinculada', tiene_gachamones: false }), true);
  assert.equal(cambioLaCuenta(web, { estado: 'web', tiene_gachamones: true }), true);
  const nueva = { estado: 'nueva', tiene_gachamones: false };
  assert.equal(cambioLaCuenta(nueva, { ...nueva }), false);
  assert.equal(cambioLaCuenta(nueva, web), true);
});
