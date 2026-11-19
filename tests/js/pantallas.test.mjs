import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as pantallas from '../../web/static/js/pantallas.js';

const {
  cambioLaCuenta, hayQueRecargar, puedeTraerDeDiscord, siguiente, trasFallarLaLlegada, trasUnFalloAlArrancar,
} = pantallas;

const sesion = { usuario: 'felipe' };
const gachamon = { nombre: 'Pelusa', espera_nombre: false };
const avatar = { nombre: 'Feli' };
const estado = (cambios = {}) => ({ avatar, gachamon, ...cambios });
// Un jugador con su gachamon, listo para ver el lugar.
const cuenta = { estado: 'web' };
const jugando = estado();

// Los lugares, como los manda el servidor: tu casa, la Tienda, uno cerrado y
// «Aventura» a quien no tiene gachamon (con la primera aventura).
const casa = { clave: 'casa', nombre: 'Tu casa', ofrece: ['departamento'] };
const laTienda = { clave: 'tienda', nombre: 'Tienda', ofrece: ['tienda'] };
const cerrado = { clave: 'estadio', nombre: 'Estadio', ofrece: [] };
const laAventura = { clave: 'aventura', nombre: 'Aventura', ofrece: ['aventura'] };
// Quien todavía no tiene ningún gachamon, parado en `lugar`.
const sinGachamon = (lugar, cambios = {}) => estado({ gachamon: null, globos: [], lugar, ...cambios });

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
  const todo = estado({ avatar: null, gachamon: null });
  assert.equal(siguiente(sesion, { estado: 'vinculada' }, todo), 'avatar');
});

test('sin gachamon ya no se va al huevo: se sigue al departamento', () => {
  for (const laCuenta of [cuenta, { estado: 'vinculada' }]) {
    assert.equal(siguiente(sesion, laCuenta, sinGachamon(casa)), 'departamento');
  }
  // En la Tienda: su lugar, o la tienda si se pide.
  assert.equal(siguiente(sesion, cuenta, sinGachamon(laTienda)), 'lugar');
  assert.equal(siguiente(sesion, cuenta, sinGachamon(laTienda), 'tienda'), 'tienda');
  // Un lugar cerrado se ve como cualquiera.
  assert.equal(siguiente(sesion, cuenta, sinGachamon(cerrado)), 'lugar');
  // El pueblo y la mochila, estés donde estés.
  for (const lugar of [casa, laTienda, cerrado]) {
    assert.equal(siguiente(sesion, cuenta, sinGachamon(lugar), 'pueblo'), 'pueblo', lugar.clave);
    assert.equal(siguiente(sesion, cuenta, sinGachamon(lugar), 'mochila'), 'mochila', lugar.clave);
  }
});

test('sin gachamon, la ficha y el ropero dejan donde estás', () => {
  for (const vista of ['ficha', 'ropero']) {
    assert.equal(siguiente(sesion, cuenta, sinGachamon(casa), vista), 'departamento', vista);
    assert.equal(siguiente(sesion, cuenta, sinGachamon(laTienda), vista), 'lugar', vista);
    assert.equal(siguiente(sesion, cuenta, sinGachamon(cerrado), vista), 'lugar', vista);
    assert.equal(siguiente(sesion, cuenta, estado({ gachamon: null }), vista), 'lugar', vista);
    // Con gachamon se abren, como siempre.
    assert.equal(siguiente(sesion, cuenta, { ...jugando, lugar: casa }, vista), vista, vista);
  }
});

test('la incubadora ya no es una pantalla: pedirla deja donde estás', () => {
  // Con quién sales se elige en tu departamento. Ni un lugar que todavía la
  // ofreciera (lo que mandaba el servidor de antes) la abre.
  assert.equal(Object.hasOwn(pantallas, 'ofreceLaIncubadora'), false);
  const laIncubadora = { clave: 'incubadora', nombre: 'Incubadora', ofrece: ['incubadora'] };
  for (const elEstado of [{ ...jugando, lugar: laIncubadora }, sinGachamon(laIncubadora)]) {
    assert.equal(siguiente(sesion, cuenta, elEstado, 'incubadora'), 'lugar');
    assert.equal(siguiente(sesion, cuenta, elEstado), 'lugar');
  }
  assert.equal(siguiente(sesion, cuenta, { ...jugando, lugar: casa }, 'incubadora'), 'departamento');
  assert.equal(siguiente(sesion, cuenta, sinGachamon(casa), 'incubadora'), 'departamento');
  assert.equal(siguiente(sesion, cuenta, { ...jugando, lugar: laTienda }, 'incubadora'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, jugando, 'incubadora'), 'lugar');
});

test('la aventura se abre sólo donde se ofrece', () => {
  assert.equal(siguiente(sesion, cuenta, sinGachamon(laAventura), 'aventura'), 'aventura');
  // Sin pedirla, el lugar.
  assert.equal(siguiente(sesion, cuenta, sinGachamon(laAventura)), 'lugar');
  // Donde no se ofrece, el lugar (o tu departamento).
  assert.equal(siguiente(sesion, cuenta, sinGachamon({ ...laAventura, ofrece: [] }), 'aventura'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, sinGachamon(laTienda), 'aventura'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, sinGachamon(cerrado), 'aventura'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, sinGachamon(casa), 'aventura'), 'departamento');
  assert.equal(siguiente(sesion, cuenta, estado({ gachamon: null }), 'aventura'), 'lugar');
  // A quien tiene gachamon el servidor no se la ofrece: «Aventura» es su lugar de siempre.
  assert.equal(siguiente(sesion, cuenta, { ...jugando, lugar: { ...laAventura, ofrece: [] } }, 'aventura'), 'lugar');
  // Lo de antes del juego va antes.
  assert.equal(siguiente(sesion, cuenta, sinGachamon(laAventura, { carta: true }), 'aventura'), 'carta');
  assert.equal(siguiente(sesion, cuenta, sinGachamon(laAventura, { avatar: null }), 'aventura'), 'avatar');
  // Lo que la ofrece, como la tienda.
  const { ofreceLaAventura } = pantallas;
  assert.equal(ofreceLaAventura(laAventura), true);
  assert.equal(ofreceLaAventura({ ofrece: ['tienda', 'aventura'] }), true);
  assert.equal(ofreceLaAventura({ ofrece: [] }), false);
  assert.equal(ofreceLaAventura(laTienda), false);
  assert.equal(ofreceLaAventura({ clave: 'aventura', nombre: 'Aventura' }), false);
  assert.equal(ofreceLaAventura(null), false);
  assert.equal(ofreceLaAventura(undefined), false);
});

test('el que espera nombre va al nombre antes que a nada', () => {
  const esperando = { nombre: 'Pollito', espera_nombre: true };
  const vistas = [undefined, 'pueblo', 'tienda', 'incubadora', 'aventura', 'mochila', 'ficha', 'ropero', 'departamento'];
  for (const lugar of [undefined, casa, laTienda, cerrado, laAventura, { clave: 'x', nombre: 'X', ofrece: ['incubadora'] }]) {
    for (const vista of vistas) {
      assert.equal(siguiente(sesion, cuenta, estado({ gachamon: esperando, lugar }), vista), 'bautizo',
        `${lugar && lugar.clave} ${vista}`);
    }
  }
});

test('el huevo no sale nunca', () => {
  // Los casos de las pruebas de hoy, cruzados: sin sesión, cuentas de cada
  // tipo, estados con y sin cada cosa, en cada lugar y pidiendo cada vista.
  const recluta = { id: 7, nombre_especie: 'Pulpito', retrato: '/gachamon/retrato/pulpo/bebe/feliz/sin.png' };
  const difunto = { nombre: 'Viejo', nombre_especie: 'Pollito', dias: 3 };
  const gachamones = [gachamon, null, { nombre: 'Piollito', espera_nombre: true }];
  const lugares = [undefined, casa, laTienda, cerrado, laAventura, { clave: 'x', nombre: 'X', ofrece: ['incubadora', 'tienda'] }];
  const extras = [{}, { carta: true }, { avatar: null }, { sin_nombre: recluta }, { difunto }, { sin_nombre: null }];
  const estados = [null];
  for (const g of gachamones) for (const lugar of lugares) for (const extra of extras) estados.push(estado({ gachamon: g, lugar, ...extra }));
  const vistas = [undefined, 'lugar', 'pueblo', 'tienda', 'incubadora', 'aventura', 'mochila', 'ficha', 'ropero', 'departamento', 'huevo', 'otra cosa'];
  // Ni la incubadora, que se fue: con quién sales se elige en tu departamento.
  const pantallas = new Set(['sesion', 'bienvenida', 'avatar', 'carta', 'bautizo', 'pueblo', 'departamento', 'lugar',
    'tienda', 'aventura', 'mochila', 'ficha', 'ropero']);
  let vistos = 0;
  for (const laSesion of [null, sesion]) {
    for (const laCuenta of [null, { estado: 'nueva' }, cuenta, { estado: 'vinculada' }]) {
      for (const elEstado of estados) {
        for (const vista of vistas) {
          const toca = siguiente(laSesion, laCuenta, elEstado, vista);
          assert.notEqual(toca, 'huevo');
          assert.ok(pantallas.has(toca), toca);
          vistos += 1;
        }
      }
    }
  }
  assert.ok(vistos > 1000, vistos);
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
  // Sin gachamon ya no hay huevo antes: también se ve.
  assert.equal(siguiente(sesion, { estado: 'web' }, estado({ gachamon: null }), 'pueblo'), 'pueblo');
  assert.equal(siguiente(sesion, { estado: 'web' }, estado({ avatar: null, gachamon: null }), 'pueblo'), 'avatar');
  assert.equal(siguiente(null, null, null, 'pueblo'), 'sesion');
});

test('la tienda sólo se abre donde el lugar la ofrece', () => {
  const en = (ofrece) => ({ ...jugando, lugar: { clave: 'x', nombre: 'X', ofrece } });
  assert.equal(siguiente(sesion, cuenta, en(['tienda']), 'tienda'), 'tienda');
  assert.equal(siguiente(sesion, cuenta, en([]), 'tienda'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, { ...jugando, lugar: { clave: 'x', nombre: 'X' } }, 'tienda'), 'lugar');
  assert.equal(siguiente(sesion, cuenta, en([]), 'mochila'), 'mochila');
  assert.equal(siguiente(sesion, cuenta, en(['tienda']), 'otra cosa'), 'lugar');
});

test('en «Tu casa» la pantalla es el departamento', () => {
  const en = (ofrece) => ({ ...jugando, lugar: { clave: 'x', nombre: 'X', ofrece } });
  const enCasa = { ...jugando, lugar: { clave: 'casa', nombre: 'Tu casa', ofrece: ['departamento'] } };
  for (const vista of [undefined, 'lugar', 'tienda', 'incubadora', 'departamento', 'otra cosa']) {
    assert.equal(siguiente(sesion, cuenta, enCasa, vista), 'departamento');
  }
  for (const vista of ['pueblo', 'mochila', 'ficha', 'ropero']) assert.equal(siguiente(sesion, cuenta, enCasa, vista), vista);
  assert.equal(siguiente(sesion, cuenta, en([]), undefined), 'lugar');
  assert.equal(siguiente(sesion, cuenta, en(['tienda']), 'departamento'), 'lugar');
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
    assert.equal(siguiente(sesion, cuenta, enLaTienda({ avatar: null, gachamon: null }), vista), 'avatar', vista);
    // Sin gachamon ya no hay huevo antes: se abre.
    assert.equal(siguiente(sesion, cuenta, enLaTienda({ gachamon: null }), vista), vista, vista);
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
    assert.equal(siguiente(sesion, cuenta, estado({ avatar: null, gachamon: null }), vista), 'avatar', vista);
    // Sin gachamon ya no hay huevo antes, y no hay ficha ni ropero que abrir: el lugar.
    assert.equal(siguiente(sesion, cuenta, estado({ gachamon: null }), vista), 'lugar', vista);
    assert.equal(
      siguiente(sesion, cuenta, estado({ gachamon: { nombre: 'Piollito', espera_nombre: true } }), vista),
      'bautizo', vista,
    );
  }
});

// El recluta que esperaba nombre cuando no quedaba ninguna activa (`estado.sin_nombre`).
const recluta = { id: 7, nombre_especie: 'Pulpito', retrato: '/gachamon/retrato/pulpo/bebe/feliz/sin.png' };

test('un `sin_nombre` que todavía mande un servidor viejo no abre ninguna pantalla', () => {
  // Sin gachamon, como cualquiera que no tiene ninguno: el lugar o tu departamento.
  assert.equal(siguiente(sesion, cuenta, estado({ gachamon: null, sin_nombre: recluta })), 'lugar');
  assert.equal(siguiente(sesion, { estado: 'vinculada' }, estado({ gachamon: null, sin_nombre: recluta })), 'lugar');
  assert.equal(siguiente(sesion, cuenta, sinGachamon(casa, { sin_nombre: recluta })), 'departamento');
  assert.equal(siguiente(sesion, cuenta, estado({ gachamon: null, sin_nombre: null })), 'lugar');
  // Con un gachamon activo, nada cambia.
  assert.equal(siguiente(sesion, cuenta, estado({ sin_nombre: recluta })), 'lugar');
  // Ninguna vista lleva al bautizo: cada una abre lo suyo, y sin gachamon la
  // ficha, el ropero y la incubadora no se abren.
  const enLaIncubadora = estado({
    gachamon: null, sin_nombre: recluta, lugar: { clave: 'x', nombre: 'X', ofrece: ['incubadora', 'tienda'] },
  });
  for (const vista of ['pueblo', 'tienda', 'mochila']) {
    assert.equal(siguiente(sesion, cuenta, enLaIncubadora, vista), vista, vista);
  }
  for (const vista of ['ficha', 'ropero', 'incubadora']) {
    assert.equal(siguiente(sesion, cuenta, enLaIncubadora, vista), 'lugar', vista);
  }
  // Y el avatar, antes que todo.
  assert.equal(siguiente(sesion, cuenta, estado({ gachamon: null, sin_nombre: recluta, avatar: null })), 'avatar');
});

test('un `difunto` que todavía mande un servidor viejo no abre ninguna pantalla', () => {
  const viejo = { difunto: { nombre: 'Viejo', nombre_especie: 'Pollito', dias: 3 } };
  const lugar = { clave: 'x', nombre: 'X', ofrece: ['tienda', 'incubadora'] };
  // Sin nadie más, o con un recluta sin nombre, al lugar; con el relevo, también.
  assert.equal(siguiente(sesion, cuenta, estado({ ...viejo, gachamon: null })), 'lugar');
  assert.equal(siguiente(sesion, cuenta, estado({ ...viejo, gachamon: null, sin_nombre: recluta })), 'lugar');
  assert.equal(
    siguiente(sesion, cuenta, estado({ ...viejo, gachamon: { nombre: 'Piollito', espera_nombre: true } })),
    'bautizo',
  );
  assert.equal(siguiente(sesion, { estado: 'vinculada' }, estado(viejo)), 'lugar');
  for (const vista of ['pueblo', 'tienda', 'mochila', 'ficha', 'ropero']) {
    assert.equal(siguiente(sesion, cuenta, estado({ ...viejo, lugar }), vista), vista, vista);
  }
});

test('cada pantalla que puede tocar tiene su sitio en la tabla de principal.js, también la de la aventura', () => {
  // Lo que `siguiente` puede devolver, recorriendo cuentas, estados, lugares y vistas.
  const gachamones = [gachamon, null, { nombre: 'Piollito', espera_nombre: true }];
  const lugares = [undefined, casa, laTienda, cerrado, laAventura, { clave: 'x', nombre: 'X', ofrece: ['incubadora'] }];
  const extras = [{}, { carta: true }, { avatar: null }];
  const vistas = [undefined, 'pueblo', 'tienda', 'incubadora', 'aventura', 'mochila', 'ficha', 'ropero', 'departamento'];
  const tocan = new Set();
  for (const laSesion of [null, sesion]) {
    for (const laCuenta of [null, { estado: 'nueva' }, cuenta]) {
      tocan.add(siguiente(laSesion, laCuenta, null));
      for (const g of gachamones) {
        for (const lugar of lugares) {
          for (const extra of extras) {
            for (const vista of vistas) tocan.add(siguiente(laSesion, laCuenta, estado({ gachamon: g, lugar, ...extra }), vista));
          }
        }
      }
    }
  }
  assert.ok(tocan.has('aventura'));
  // Las filas de la tabla de pantallas de `principal.js`.
  const principal = readFileSync(new URL('../../web/static/js/principal.js', import.meta.url), 'utf8');
  const tabla = principal.match(/const PANTALLAS = \{([\s\S]*?)\n\};/);
  assert.ok(tabla, 'no está la tabla de pantallas');
  const filas = new Set([...tabla[1].matchAll(/^\s*(\w+):/gm)].map(([, nombre]) => nombre));
  for (const pantalla of tocan) assert.ok(filas.has(pantalla), pantalla);
});

test('lo que el cliente ofrece en un lugar lleva la clave de un lugar del pueblo', () => {
  const pueblo = JSON.parse(readFileSync(new URL('../../web/static/datos/pueblo.json', import.meta.url), 'utf8'));
  for (const clave of ['tienda', 'aventura']) assert.ok(Object.hasOwn(pueblo.lugares, clave), clave);
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

test('la carta se ve antes que nada', () => {
  for (const vista of [undefined, 'tienda', 'mochila', 'pueblo']) {
    assert.equal(siguiente(sesion, cuenta, { ...jugando, carta: true }, vista), 'carta');
  }
  assert.equal(siguiente(sesion, cuenta, { ...jugando, carta: true, gachamon: null }, undefined), 'carta');   // también sin gachamon
  assert.equal(siguiente(sesion, cuenta, { ...jugando, carta: false }, undefined), 'lugar');
  assert.equal(siguiente(sesion, cuenta, { ...jugando, carta: true, avatar: null }, undefined), 'avatar');   // primero, tener avatar
});
