import test from 'node:test';
import assert from 'node:assert/strict';
import { el } from '../../web/static/js/dom.js';

// Lo justo de un documento para `el`: elementos que apuntan sus atributos y
// sus oyentes, y nodos de texto.
class Nodo {}
class Elemento extends Nodo {
  constructor(etiqueta) {
    super();
    this.etiqueta = etiqueta;
    this.atributos = {};
    this.oyentes = {};
    this.hijos = [];
  }

  setAttribute(nombre, valor) { this.atributos[nombre] = valor; }

  addEventListener(tipo, oyente) { (this.oyentes[tipo] ||= []).push(oyente); }

  append(...nodos) { this.hijos.push(...nodos); }
}
globalThis.Node = Nodo;
globalThis.document = {
  createElement: (etiqueta) => new Elemento(etiqueta),
  createTextNode: (texto) => Object.assign(new Nodo(), { texto }),
};

test('un on… con una función se escucha como evento y no es un atributo', () => {
  const pulsar = () => {};
  const nodo = el('button', { onclick: pulsar, class: 'boton' }, 'Hola');
  assert.deepEqual(nodo.oyentes, { click: [pulsar] });
  assert.deepEqual(nodo.atributos, { class: 'boton' });
  assert.equal(nodo.hijos[0].texto, 'Hola');
});

test('un on… que no es una función es un error, y no un manejador en línea', () => {
  for (const [nombre, valor] of [['onclick', 'alert(1)'], ['onerror', 1], ['onClick', 'x()'],
    ['ONLOAD', 'x()'], ['onclick', true], ['onclick', {}]]) {
    assert.throws(() => el('img', { [nombre]: valor }), TypeError, nombre);
  }
});

test('un on… vacío se salta como cualquier otro atributo', () => {
  for (const valor of [null, undefined, false]) {
    const nodo = el('button', { onclick: valor });
    assert.deepEqual(nodo.oyentes, {});
    assert.deepEqual(nodo.atributos, {});
  }
});
