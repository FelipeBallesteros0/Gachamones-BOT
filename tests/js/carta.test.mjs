import test from 'node:test';
import assert from 'node:assert/strict';

// Lo justo de un navegador para pintar la ficha sin pantalla y tocar sus
// botones: elementos con sus hijos (y quién los contiene), su texto,
// atributos, clases y oyentes, que se buscan por etiqueta, por `.clase` o por
// `[atributo]`; lienzos que se dejan pintar e imágenes que cargan solas.
class Nodo {
  constructor() { this.padre = null; }
}

class Texto extends Nodo {
  constructor(texto) {
    super();
    this.texto = texto;
  }

  get textContent() { return this.texto; }
}

class Elemento extends Nodo {
  constructor(etiqueta) {
    super();
    this.etiqueta = etiqueta;
    this.atributos = {};
    this.oyentes = {};
    this.hijos = [];
    this.style = {};
    this.isConnected = true;
    const clases = () => String(this.atributos.class || '').split(/\s+/).filter(Boolean);
    this.classList = {
      add: (...nombres) => { this.atributos.class = [...new Set([...clases(), ...nombres])].join(' '); },
      remove: (...nombres) => { this.atributos.class = clases().filter((c) => !nombres.includes(c)).join(' '); },
      contains: (nombre) => clases().includes(nombre),
      toggle: () => {},
    };
  }

  setAttribute(nombre, valor) { this.atributos[nombre] = String(valor); }

  getAttribute(nombre) { return Object.hasOwn(this.atributos, nombre) ? this.atributos[nombre] : null; }

  addEventListener(tipo, oyente) { (this.oyentes[tipo] ||= []).push(oyente); }

  get textContent() { return this.hijos.map((h) => h.textContent).join(''); }

  set textContent(texto) { this.replaceChildren(...(texto === '' ? [] : [new Texto(String(texto))])); }

  append(...nodos) {
    for (const nodo of nodos) nodo.padre = this;
    this.hijos.push(...nodos);
  }

  replaceChildren(...nodos) {
    this.hijos = [];
    this.append(...nodos);
  }

  cumple(selector) {
    if (selector.startsWith('.')) return String(this.atributos.class || '').split(/\s+/).includes(selector.slice(1));
    if (selector.startsWith('[')) return Object.hasOwn(this.atributos, selector.slice(1, -1));
    return this.etiqueta === selector;
  }

  querySelectorAll(selector) {
    return this.hijos.filter((h) => h instanceof Elemento)
      .flatMap((h) => [...(h.cumple(selector) ? [h] : []), ...h.querySelectorAll(selector)]);
  }

  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }

  contains(nodo) {
    return this.hijos.some((h) => h === nodo || (h instanceof Elemento && h.contains(nodo)));
  }

  focus() {}

  // Un contexto que acepta todo lo que se le pida pintar.
  getContext() { return new Proxy({}, { get: () => () => {}, set: () => true }); }
}

globalThis.Node = Nodo;
globalThis.document = {
  createElement: (etiqueta) => new Elemento(etiqueta),
  createTextNode: (texto) => new Texto(texto),
  activeElement: null,
};
globalThis.window = { devicePixelRatio: 1 };
globalThis.Image = class {
  set src(direccion) {
    this.direccion = direccion;
    queueMicrotask(() => { if (this.onload) this.onload(); });
  }
};

const { carta } = await import('../../web/static/js/carta.js');

// Un servidor de mentira para `pedir`: cada ruta («GET carta») contesta lo que
// se le dijo con `responde`, o falla como una red caída con `falla`.
function servidorDeMentira() {
  const pedidos = [];
  const respuestas = new Map();
  const caidas = new Set();
  globalThis.fetch = async (url, opciones) => {
    const ruta = `${opciones.method} ${String(url).replace(/^\/gachamon\/api\//, '')}`;
    pedidos.push([ruta]);
    if (caidas.has(ruta)) throw new Error('sin red');
    return { ok: true, status: 200, headers: { get: () => null }, json: async () => respuestas.get(ruta) };
  };
  return {
    pedidos,
    servidor: {
      responde: (ruta, datos) => { respuestas.set(ruta, datos); caidas.delete(ruta); },
      falla: (ruta) => { caidas.add(ruta); },
    },
  };
}

const todos = (raiz, selector) => raiz.querySelectorAll(selector);
const texto = (raiz, selector) => {
  const nodo = raiz.querySelector(selector);
  return nodo ? nodo.textContent : null;
};
const estado = (raiz) => raiz.querySelectorAll('[role]').find((n) => n.atributos.role === 'status') || null;
const boton = (raiz, que) => raiz.querySelectorAll('button').find((b) => b.textContent.includes(que)) || null;
const tocar = async (nodo) => {
  for (const oyente of nodo.oyentes.click) oyente({ type: 'click' });
  await new Promise((listo) => setTimeout(listo, 0));
};

// Pinta la carta con lo que contesta `GET carta` y espera a que llegue.
async function abrir(respuesta) {
  const { pedidos, servidor } = servidorDeMentira();
  servidor.responde('GET carta', respuesta);
  const pantalla = new Elemento('main');
  const seguido = [];
  await carta(pantalla, { carta: true }, (...argumentos) => { seguido.push(argumentos); });
  return { pantalla, pedidos, servidor, seguido };
}

const LA_CARTA = { carta: { titulo: 'Carta del alcalde', lineas: ['Una.', 'Dos.'], firma: 'El alcalde' } };

test('la carta se lee entera y se cierra con Entendido', { timeout: 2000 }, async () => {
  const { pantalla, pedidos, servidor, seguido } = await abrir(LA_CARTA);
  assert.equal(texto(pantalla, 'h1'), 'Carta del alcalde');
  assert.deepEqual(todos(pantalla, '.carta-linea').map((p) => p.textContent), ['Una.', 'Dos.']);
  assert.equal(texto(pantalla, '.carta-firma'), 'El alcalde');
  servidor.responde('POST carta/vista', { carta: null });
  await tocar(boton(pantalla, 'Entendido'));
  assert.deepEqual(pedidos.map(([ruta]) => ruta), ['GET carta', 'POST carta/vista']);
  assert.equal(seguido.length, 1);
});

test('si ya no hay carta, se sigue de largo', { timeout: 2000 }, async () => {
  const { seguido, pantalla } = await abrir({ carta: null });
  assert.equal(seguido.length, 1);
  assert.equal(boton(pantalla, 'Entendido'), null);
});

test('si no se pudo marcar, la carta sigue ahí y se puede volver a intentar', { timeout: 2000 }, async () => {
  const { pantalla, servidor, seguido } = await abrir(LA_CARTA);
  servidor.falla('POST carta/vista');
  await tocar(boton(pantalla, 'Entendido'));
  assert.equal(seguido.length, 0);
  assert.equal(estado(pantalla).textContent, 'No hubo respuesta. Revisa tu conexión.');
  assert.notEqual(boton(pantalla, 'Entendido'), null);
  assert.deepEqual(todos(pantalla, '.carta-linea').map((p) => p.textContent), ['Una.', 'Dos.']);
  assert.notEqual(boton(pantalla, 'Entendido').getAttribute('aria-busy'), 'true');
});

test('mientras se marca, un segundo toque no manda otra petición', { timeout: 2000 }, async () => {
  const { pantalla, pedidos, servidor, seguido } = await abrir(LA_CARTA);
  servidor.responde('POST carta/vista', { carta: null });
  const entendido = boton(pantalla, 'Entendido');
  await Promise.all([tocar(entendido), tocar(entendido)]);
  assert.equal(pedidos.filter(([ruta]) => ruta === 'POST carta/vista').length, 1);
  assert.equal(seguido.length, 1);
});

test('si no carga, lo dice y ofrece volver a intentarlo', { timeout: 2000 }, async () => {
  const { pedidos, servidor } = servidorDeMentira();
  servidor.falla('GET carta');
  const pantalla = new Elemento('main');
  const seguido = [];
  await carta(pantalla, { carta: true }, (...argumentos) => { seguido.push(argumentos); });
  assert.notEqual(boton(pantalla, 'Volver a intentarlo'), null);
  assert.match(pantalla.textContent, /No hay conexión con el juego/);
  servidor.responde('GET carta', LA_CARTA);
  await tocar(boton(pantalla, 'Volver a intentarlo'));
  assert.equal(texto(pantalla, 'h1'), 'Carta del alcalde');
  assert.equal(pedidos.length, 2);
  assert.equal(seguido.length, 0);
});

test('las líneas de la carta entran como texto, no como página', { timeout: 2000 }, async () => {
  const { pantalla } = await abrir({ carta: { titulo: 'T', lineas: ['<b>hola</b>'], firma: 'F' } });
  assert.equal(texto(pantalla, '.carta-linea'), '<b>hola</b>');
  assert.equal(todos(pantalla, 'b').length, 0);
});
