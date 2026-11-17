import test from 'node:test';
import assert from 'node:assert/strict';

// Lo justo de un navegador para pintar la tienda sin pantalla y tocar sus
// botones: elementos con sus hijos (y quién los contiene), atributos, clases y
// oyentes, que se buscan por etiqueta, por `.clase` o por `[atributo]`, y un
// lienzo que se deja pintar.
class Nodo {}
class Elemento extends Nodo {
  constructor(etiqueta) {
    super();
    this.etiqueta = etiqueta;
    this.atributos = {};
    this.oyentes = {};
    this.hijos = [];
    this.padre = null;
    this.style = {};
    this.isConnected = true;
    const clases = new Set();
    this.classList = {
      add: (...nombres) => nombres.forEach((n) => clases.add(n)),
      remove: (...nombres) => nombres.forEach((n) => clases.delete(n)),
      contains: (nombre) => clases.has(nombre),
      toggle: (nombre, poner) => (poner ? clases.add(nombre) : clases.delete(nombre)),
    };
  }

  setAttribute(nombre, valor) { this.atributos[nombre] = valor; }

  addEventListener(tipo, oyente) { (this.oyentes[tipo] ||= []).push(oyente); }

  append(...nodos) {
    for (const nodo of nodos) nodo.padre = this;
    this.hijos.push(...nodos);
  }

  replaceChildren(...nodos) {
    this.hijos = [];
    this.append(...nodos);
  }

  get dataset() {
    return { fila: this.atributos['data-fila'] };
  }

  cumple(selector) {
    return selector.split(',').map((s) => s.trim()).some((s) => {
      if (s.startsWith('.')) return String(this.atributos.class || '').split(' ').includes(s.slice(1));
      if (s.startsWith('[')) return Object.hasOwn(this.atributos, s.slice(1, -1));
      return this.etiqueta === s;
    });
  }

  querySelectorAll(selector) {
    return this.hijos.filter((h) => h instanceof Elemento)
      .flatMap((h) => [...(h.cumple(selector) ? [h] : []), ...h.querySelectorAll(selector)]);
  }

  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }

  closest(selector) {
    for (let nodo = this; nodo; nodo = nodo.padre) if (nodo.cumple(selector)) return nodo;
    return null;
  }

  contains(nodo) {
    return this.hijos.some((h) => h === nodo || (h instanceof Elemento && h.contains(nodo)));
  }

  focus() {}

  // Un contexto que acepta todo lo que se le pida pintar.
  getContext() { return new Proxy({}, { get: () => () => {} }); }
}
globalThis.Node = Nodo;
globalThis.document = {
  createElement: (etiqueta) => new Elemento(etiqueta),
  createTextNode: (texto) => Object.assign(new Nodo(), { texto }),
  activeElement: null,
};
globalThis.window = { devicePixelRatio: 1 };

const { tienda } = await import('../../web/static/js/tienda.js');

function textos(nodo) {
  if (!(nodo instanceof Elemento)) return [nodo.texto];
  return nodo.hijos.flatMap(textos);
}

const mueble = (clave, nombre, precio, tienes) => ({
  clave, nombre, precio, comodidad: 2, icono: `iconos/muebles/${clave}.png`, tienes,
});

function catalogo(felpudos) {
  return {
    saldos: { monedas: 200, gemas: 0 },
    objetos: [],
    cosmeticos: [],
    muebles: { lista: [mueble('felpudo', 'Felpudo', 30, felpudos), mueble('maceta', 'Maceta', 50, 0)] },
  };
}

// Un servidor de mentira para `pedir`: apunta cada petición y contesta lo que
// diga `contestar(peticion)`.
function servidor(contestar) {
  const pedidas = [];
  globalThis.fetch = async (url, opciones) => {
    const pedida = { url, metodo: opciones.method, cuerpo: opciones.body ? JSON.parse(opciones.body) : null };
    pedidas.push(pedida);
    const datos = contestar(pedida);
    return { ok: true, status: 200, headers: { get: () => null }, json: async () => datos };
  };
  return pedidas;
}

async function tiendaPintada() {
  const contenedor = new Elemento('main');
  assert.equal(await tienda(contenedor, { saldos: { monedas: 200, gemas: 0 } }, () => {}), true);
  return contenedor;
}

const filasDeMuebles = (contenedor) => contenedor.querySelectorAll('section')
  .find((s) => s.atributos.id === 'tienda-muebles').querySelectorAll('li');

test('la tienda tiene tres secciones, sin casas: objetos, cosméticos y muebles', { timeout: 2000 }, async () => {
  servidor(() => catalogo(0));
  const contenedor = await tiendaPintada();
  const secciones = contenedor.querySelectorAll('section').map((s) => s.atributos.id);
  assert.deepEqual(secciones, ['tienda-objetos', 'tienda-cosmeticos', 'tienda-muebles']);
  const pestanas = contenedor.querySelectorAll('.pestana').map((b) => textos(b).join(''));
  assert.deepEqual(pestanas, ['Objetos', 'Cosméticos', 'Muebles']);
});

test('cada mueble se puede comprar, también el que ya tienes, y dice cuántos tienes', { timeout: 2000 }, async () => {
  servidor(() => catalogo(2));
  const contenedor = await tiendaPintada();
  const filas = filasDeMuebles(contenedor);
  assert.deepEqual(filas.map((f) => f.dataset.fila), ['mueble:felpudo', 'mueble:maceta']);
  for (const fila of filas) {
    assert.equal(fila.atributos.class, 'articulo', fila.dataset.fila);   // ninguna apagada
    assert.equal(fila.querySelectorAll('.boton-precio').length, 1, fila.dataset.fila);
    assert.ok(!textos(fila).includes('Ya lo tienes'), fila.dataset.fila);
  }
  const [felpudo, maceta] = filas.map(textos);
  assert.ok(felpudo.includes('Tienes 2'));
  assert.ok(!maceta.some((t) => String(t).startsWith('Tienes')));
  // Ya no hay aviso de que los muebles piden casa.
  assert.equal(contenedor.querySelectorAll('.aviso-de-seccion').length, 0);
});

test('comprar otro del que ya tienes manda el mueble y su evento, y la fila cuenta uno más', { timeout: 2000 }, async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const mensaje = 'Compraste Felpudo. Quedó en tus guardados: en tu casa, entra a «Construir».';
  const pedidas = servidor((pedida) => (pedida.metodo === 'GET'
    ? catalogo(2)
    : { ok: true, clave: null, mensaje, tienda: catalogo(3) }));
  const contenedor = await tiendaPintada();
  const [felpudo] = filasDeMuebles(contenedor);
  felpudo.querySelector('.boton-precio').oyentes.click[0]();
  const [si] = felpudo.querySelectorAll('.principal');
  await si.oyentes.click[0]();

  const compra = pedidas.find((p) => p.metodo === 'POST');
  assert.ok(compra.url.endsWith('/tienda/comprar'), compra.url);
  assert.equal(compra.cuerpo.que, 'mueble');
  assert.equal(compra.cuerpo.clave, 'felpudo');
  assert.equal(typeof compra.cuerpo.evento_id, 'string');
  const [despues] = filasDeMuebles(contenedor);
  assert.ok(textos(despues).includes('Tienes 3'));
  assert.equal(despues.querySelectorAll('.boton-precio').length, 1);
  assert.equal(contenedor.querySelector('.aviso-tienda').textContent, mensaje);
});
