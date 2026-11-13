import test from 'node:test';
import assert from 'node:assert/strict';

// Lo justo de un navegador para armar la caja del código sin pantalla:
// elementos que apuntan sus hijos y sus oyentes, y un portapapeles que anota
// lo que se le manda.
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
const copiado = [];
Object.defineProperty(globalThis, 'navigator', {
  value: { clipboard: { writeText: async (texto) => { copiado.push(texto); } } },
  configurable: true,
});
globalThis.window = { isSecureContext: true };

const { cajaDelCodigo } = await import('../../web/static/js/entrada.js');

function textos(nodo) {
  if (!(nodo instanceof Elemento)) return [nodo.texto];
  return nodo.hijos.flatMap(textos);
}

function buscar(nodo, etiqueta) {
  if (!(nodo instanceof Elemento)) return [];
  const propios = nodo.etiqueta === etiqueta ? [nodo] : [];
  return [...propios, ...nodo.hijos.flatMap((hijo) => buscar(hijo, etiqueta))];
}

const caja = () => cajaDelCodigo('AXF55QQU', 10, document.createElement('span'));

test('el botón copia sólo el código: Discord no acepta el comando pegado entero', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  copiado.length = 0;
  const botones = buscar(caja(), 'button');
  assert.equal(botones.length, 1);
  await botones[0].oyentes.click[0]();
  assert.deepEqual(copiado, ['AXF55QQU']);
});

test('el botón dice lo que copia', () => {
  assert.deepEqual(textos(buscar(caja(), 'button')[0]), ['Copiar código']);
});

test('el comando se enseña sin el código pegado', () => {
  const nodo = caja();
  assert.deepEqual(buscar(nodo, 'code').map((codigo) => textos(codigo).join('')), ['/vincular']);
  assert.ok(textos(nodo).includes('AXF55QQU'));
  assert.ok(!textos(nodo).join('').includes('/vincular AXF55QQU'));
});

test('dice cuánto dura, en singular cuando es un minuto', () => {
  assert.ok(textos(caja()).some((texto) => texto.startsWith('Dura 10 minutos')));
  const deUno = cajaDelCodigo('AXF55QQU', 1, document.createElement('span'));
  assert.ok(textos(deUno).some((texto) => texto.startsWith('Dura 1 minuto ')));
});
