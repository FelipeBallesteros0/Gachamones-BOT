import test from 'node:test';
import assert from 'node:assert/strict';
import { pedir, nuevoEvento } from '../../web/static/js/api.js';

const EVENTO_VALIDO = /^[A-Za-z0-9-]{8,64}$/;

// Una respuesta de `fetch` con lo justo: estado y, si lo hay, un cuerpo JSON.
const respuesta = (estado, cuerpo) => ({
  ok: estado >= 200 && estado < 300,
  status: estado,
  json: async () => {
    if (cuerpo === undefined) throw new SyntaxError('no es JSON');
    return cuerpo;
  },
});

const conFetch = (contestar) => {
  const llamadas = [];
  globalThis.fetch = async (url, opciones) => {
    llamadas.push({ url, opciones });
    return contestar(url, opciones);
  };
  return llamadas;
};

test('leer es un GET a la api del juego, sin la cabecera del juego', async () => {
  const llamadas = conFetch(() => respuesta(200, { usuario: 'felipe' }));
  assert.deepEqual(await pedir('GET', 'sesion'), { usuario: 'felipe' });
  const [{ url, opciones }] = llamadas;
  assert.equal(url, '/gachamon/api/sesion');
  assert.equal(opciones.method, 'GET');
  assert.equal(new Headers(opciones.headers).get('X-Gachamon'), null);
  assert.equal(opciones.body, undefined);
});

test('lo que cambia algo lleva la cabecera del juego y el cuerpo en JSON', async () => {
  const llamadas = conFetch(() => respuesta(200, { ok: true }));
  await pedir('POST', 'bautizar', { nombre: 'Pelusa' });
  await pedir('PUT', 'avatar', { nombre: 'Feli' });
  await pedir('POST', 'huevo');
  for (const { opciones } of llamadas) {
    assert.equal(new Headers(opciones.headers).get('X-Gachamon'), '1', opciones.method);
  }
  const [bautizo, avatar, huevo] = llamadas;
  assert.equal(bautizo.url, '/gachamon/api/bautizar');
  assert.equal(new Headers(bautizo.opciones.headers).get('Content-Type'), 'application/json');
  assert.deepEqual(JSON.parse(bautizo.opciones.body), { nombre: 'Pelusa' });
  assert.equal(avatar.opciones.method, 'PUT');
  assert.equal(huevo.opciones.body, undefined);
});

test('un error del servidor llega con su estado, su clave y su mensaje', async () => {
  conFetch(() => respuesta(409, {
    detail: { clave: 'cuenta_cambio', mensaje: 'Tu cuenta cambió mientras tanto. Vuelve a entrar.' },
  }));
  await assert.rejects(pedir('POST', 'huevo'), {
    estado: 409, clave: 'cuenta_cambio', mensaje: 'Tu cuenta cambió mientras tanto. Vuelve a entrar.',
  });
});

test('si la red se cae, el error no trae clave y sí una frase para quien juega', async () => {
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch'); };
  await assert.rejects(pedir('GET', 'estado'), (error) => {
    assert.equal(error.clave, null);
    assert.equal(error.estado, 0);
    assert.ok(error.mensaje.length > 0);
    assert.doesNotMatch(error.mensaje, /fetch|TypeError/);
    return true;
  });
});

test('una respuesta de error que no es del juego tampoco trae clave', async () => {
  conFetch(() => respuesta(502));
  await assert.rejects(pedir('GET', 'estado'), (error) => {
    assert.equal(error.estado, 502);
    assert.equal(error.clave, null);
    assert.ok(error.mensaje.length > 0);
    return true;
  });
});

test('cada evento nuevo vale para cuidar y no se repite', () => {
  const vistos = new Set();
  for (let i = 0; i < 50; i += 1) {
    const evento = nuevoEvento();
    assert.match(evento, EVENTO_VALIDO);
    vistos.add(evento);
  }
  assert.equal(vistos.size, 50);
});

test('sin randomUUID (una página sin https) el evento sigue valiendo', () => {
  Object.defineProperty(globalThis.crypto, 'randomUUID', {
    value: undefined, configurable: true, writable: true,
  });
  try {
    const uno = nuevoEvento();
    assert.match(uno, EVENTO_VALIDO);
    assert.notEqual(nuevoEvento(), uno);
  } finally {
    delete globalThis.crypto.randomUUID;
  }
});
