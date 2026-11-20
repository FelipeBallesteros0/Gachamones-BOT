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

const { ficha } = await import('../../web/static/js/ficha.js');

// Un servidor de mentira para `pedir`: apunta cada petición como «GET ficha…»
// y contesta lo que diga `contestar(ruta)`.
function servidor(contestar) {
  const pedidas = [];
  globalThis.fetch = async (url, opciones) => {
    const ruta = `${opciones.method} ${String(url).replace(/^\/monsteropolis\/api\//, '')}`;
    pedidas.push(ruta);
    const datos = contestar(ruta);
    return { ok: true, status: 200, headers: { get: () => null }, json: async () => datos };
  };
  return pedidas;
}

const PELUSA = {
  id: 7, nombre: 'Pelusa', especie: 'pollito', nombre_especie: 'Pollito', emoji: '🐣', etapa: 'bebe',
  nombre_etapa: 'cría', nivel: 3, genero: 'hembra', retrato: '/monsteropolis/retrato/pollito/bebe/feliz/sin.png', titulo: null,
};
const RULO = {
  id: 8, nombre: 'Rulo', especie: 'slime', nombre_especie: 'Gelatín', emoji: '🟢', etapa: 'bebe',
  nombre_etapa: 'cría', nivel: 2, genero: 'macho', retrato: '/monsteropolis/retrato/slime/bebe/feliz/sin.png', titulo: null,
};
// El estado de la página: sales con Pelusa.
const ESTADO = { gachamon: PELUSA, saldos: { monedas: 130, gemas: 2 } };

// Lo que contesta `GET ficha` de ese gachamon.
function laFichaDe(g, { esElActivo, sombrero = null }) {
  return {
    gachamon: g,
    es_el_activo: esElActivo,
    detalle: {
      caracter: 'alegre',
      sombrero,
      experiencia: { nivel: g.nivel, xp: 10, para_subir: 50 },
      estadisticas: [{ clave: 'fuerza', nombre: 'Fuerza', valor: 5, efecto: null }],
    },
    medallas: { del_gachamon: [], tuyas: [] },
    saldos: { monedas: 130, gemas: 2 },
  };
}

// Pinta la ficha (de `gachamonId`, si se da) y espera a que llegue.
async function abrir(gachamonId) {
  const contenedor = new Elemento('main');
  const seguido = [];
  const pintada = await ficha(contenedor, ESTADO, (...argumentos) => { seguido.push(argumentos); }, gachamonId);
  return { contenedor, seguido, pintada };
}

const texto = (raiz, selector) => {
  const nodo = raiz.querySelector(selector);
  return nodo ? nodo.textContent : null;
};
const boton = (raiz, que) => raiz.querySelectorAll('button').find((b) => b.textContent.includes(que)) || null;

test('con un gachamon pide la ficha de ése; sin él, la del que sale contigo', { timeout: 2000 }, async () => {
  const pedidas = servidor((ruta) => (ruta === 'GET ficha?gachamon_id=8'
    ? laFichaDe(RULO, { esElActivo: false })
    : laFichaDe(PELUSA, { esElActivo: true })));
  const deRulo = await abrir(RULO.id);
  assert.deepEqual(pedidas, ['GET ficha?gachamon_id=8']);
  assert.equal(deRulo.pintada, true);
  assert.equal(texto(deRulo.contenedor, '.ficha-nombre'), 'Rulo');
  assert.deepEqual(deRulo.seguido, []);                                  // es la que se pidió: se queda
  const deLaQueSale = await abrir();
  assert.deepEqual(pedidas.slice(1), ['GET ficha']);
  assert.equal(texto(deLaQueSale.contenedor, '.ficha-nombre'), 'Pelusa');
});

test('la de uno que no sale contigo no ofrece el ropero; la del que sale contigo, sí', { timeout: 2000 }, async () => {
  servidor(() => laFichaDe(RULO, { esElActivo: false }));
  const sinSombrero = await abrir(RULO.id);
  assert.equal(boton(sinSombrero.contenedor, 'Ropero'), null);
  servidor(() => laFichaDe(RULO, { esElActivo: false, sombrero: 'Gorro de lana' }));
  const conSombrero = await abrir(RULO.id);
  assert.match(texto(conSombrero.contenedor, '.ficha-sombrero'), /Lleva Gorro de lana/);
  assert.equal(boton(conSombrero.contenedor, 'Ropero'), null);
  servidor(() => laFichaDe(PELUSA, { esElActivo: true }));
  const laQueSale = await abrir(PELUSA.id);
  assert.notEqual(boton(laQueSale.contenedor, 'Ropero'), null);
  servidor(() => laFichaDe(PELUSA, { esElActivo: true, sombrero: 'Gorro de lana' }));
  const laQueSaleConSombrero = await abrir();
  assert.notEqual(boton(laQueSaleConSombrero.contenedor, 'Ropero'), null);
});

test('«Volver» vuelve a decidir la pantalla, sin pedir otra vista', { timeout: 2000 }, async () => {
  servidor(() => laFichaDe(RULO, { esElActivo: false }));
  const { contenedor, seguido } = await abrir(RULO.id);
  for (const oyente of boton(contenedor, 'Volver').oyentes.click) oyente({ type: 'click' });
  // `seguir()` sin estado: se vuelve a leer y, en casa, toca el departamento.
  assert.deepEqual(seguido, [[undefined, undefined]]);
});
