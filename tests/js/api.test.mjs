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

// El error de una red caída, para comparar: un corte tiene que ser igual.
const errorDeRed = async () => {
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch'); };
  return pedir('GET', 'estado').catch((error) => error);
};

// Deja correr las promesas pendientes (setImmediate no está simulado).
const dejarCorrer = () => new Promise((listo) => { setImmediate(listo); });

test('una petición que no vuelve nunca se corta a los 15 segundos, como sin red', { timeout: 5000 }, async (t) => {
  const sinRed = await errorDeRed();
  t.mock.timers.enable({ apis: ['setTimeout'] });
  // Ni contesta ni atiende a que se le pida parar.
  globalThis.fetch = () => new Promise(() => {});
  let terminada = false;
  const peticion = pedir('POST', 'cuidar', { accion: 'jugar', evento_id: 'evento-de-prueba' });
  peticion.catch(() => {}).finally(() => { terminada = true; });
  t.mock.timers.tick(14_999);
  await dejarCorrer();
  assert.equal(terminada, false, 'cortó antes de tiempo');
  t.mock.timers.tick(1);
  await assert.rejects(peticion, (error) => {
    assert.deepEqual(error, sinRed);
    assert.equal(error.clave, null);
    return true;
  });
});

test('al cortar, la petición de verdad se cancela', { timeout: 5000 }, async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  let senal = null;
  globalThis.fetch = (url, opciones) => new Promise((_, rechazar) => {
    senal = opciones.signal;
    senal.addEventListener('abort', () => rechazar(new DOMException('cortada', 'AbortError')));
  });
  const peticion = pedir('GET', 'estado');
  t.mock.timers.tick(15_000);
  await assert.rejects(peticion, { estado: 0, clave: null });
  assert.equal(senal.aborted, true);
});

test('un cuerpo que no termina de llegar también se corta', { timeout: 5000 }, async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  globalThis.fetch = async () => ({ ok: true, status: 200, json: () => new Promise(() => {}) });
  const peticion = pedir('GET', 'estado');
  await dejarCorrer();
  t.mock.timers.tick(15_000);
  await assert.rejects(peticion, { estado: 0, clave: null });
});

test('una respuesta a tiempo desarma el corte', { timeout: 5000 }, async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const llamadas = conFetch(() => respuesta(200, { ok: true }));
  assert.deepEqual(await pedir('GET', 'estado'), { ok: true });
  t.mock.timers.tick(15_000);
  assert.equal(llamadas[0].opciones.signal.aborted, false);
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
