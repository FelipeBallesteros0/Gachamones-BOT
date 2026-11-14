import test from 'node:test';
import assert from 'node:assert/strict';

// Lo justo de un navegador para armar una fila sin pantalla: elementos que
// apuntan sus hijos, sus atributos y sus clases, y un lienzo que se deja pintar.
class Nodo {}
class Elemento extends Nodo {
  constructor(etiqueta) {
    super();
    this.etiqueta = etiqueta;
    this.atributos = {};
    this.hijos = [];
    this.style = {};
    this.clases = [];
    this.classList = { add: (...nombres) => this.clases.push(...nombres) };
  }

  setAttribute(nombre, valor) { this.atributos[nombre] = valor; }

  append(...nodos) { this.hijos.push(...nodos); }

  // Un contexto que acepta todo lo que se le pida pintar.
  getContext() { return new Proxy({}, { get: () => () => {} }); }
}
globalThis.Node = Nodo;
globalThis.document = {
  createElement: (etiqueta) => new Elemento(etiqueta),
  createTextNode: (texto) => Object.assign(new Nodo(), { texto }),
};
globalThis.window = { devicePixelRatio: 2 };

const { filaDeArticulo } = await import('../../web/static/js/articulos.js');
const { el } = await import('../../web/static/js/dom.js');

test('con una ruta de arte, el ícono es su lienzo, como siempre', () => {
  const fila = filaDeArticulo({
    id: 'una-pieza', icono: 'iconos/objetos/una-pieza.png', nombre: 'Una pieza', lineas: [], accion: null,
  });
  assert.equal(fila.etiqueta, 'li');
  assert.equal(fila.atributos['data-fila'], 'una-pieza');
  const [dibujo] = fila.hijos;
  assert.equal(dibujo.etiqueta, 'canvas');
  assert.equal(dibujo.atributos['aria-hidden'], 'true');
  assert.deepEqual([dibujo.width, dibujo.height, dibujo.style.width, dibujo.style.height], [96, 96, '48px', '48px']);
  assert.deepEqual(dibujo.clases, ['articulo-icono']);
});

test('con un nodo ya hecho por ícono, la fila lo usa tal cual', () => {
  const retrato = el('img', { class: 'articulo-icono retrato-plantel', src: '/gachamon/retrato/pulpo.png', alt: '' });
  const fila = filaDeArticulo({ id: 7, icono: retrato, nombre: 'Bruma', lineas: [], accion: null });
  const [primero, texto] = fila.hijos;
  assert.equal(primero, retrato);
  assert.deepEqual(retrato.clases, []);
  assert.deepEqual(retrato.atributos, { class: 'articulo-icono retrato-plantel', src: '/gachamon/retrato/pulpo.png', alt: '' });
  assert.equal(texto.atributos.class, 'articulo-texto');
  assert.equal(fila.atributos['data-fila'], '7');
});
