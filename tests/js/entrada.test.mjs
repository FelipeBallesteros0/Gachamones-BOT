import test from 'node:test';
import assert from 'node:assert/strict';

// Lo justo de un navegador para armar la caja del código y el bautizo sin
// pantalla: elementos que apuntan sus hijos, sus clases y sus oyentes, y un
// portapapeles que anota lo que se le manda.
class Nodo {}
class Elemento extends Nodo {
  constructor(etiqueta) {
    super();
    this.etiqueta = etiqueta;
    this.atributos = {};
    this.oyentes = {};
    this.hijos = [];
    const clases = new Set();
    this.classList = {
      add: (...nombres) => nombres.forEach((n) => clases.add(n)),
      remove: (...nombres) => nombres.forEach((n) => clases.delete(n)),
      contains: (nombre) => clases.has(nombre),
    };
  }

  setAttribute(nombre, valor) { this.atributos[nombre] = valor; }

  removeAttribute(nombre) { delete this.atributos[nombre]; }

  addEventListener(tipo, oyente) { (this.oyentes[tipo] ||= []).push(oyente); }

  append(...nodos) { this.hijos.push(...nodos); }

  focus() {}
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

const { bautizo, cajaDelCodigo, MUESTRAS } = await import('../../web/static/js/entrada.js');

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

// --- el bautizo -------------------------------------------------------------------

// Un servidor de mentira para `pedir`: apunta cada petición y contesta lo que
// diga `contestar` (`{estado, datos}`).
function servidor(contestar) {
  const pedidas = [];
  globalThis.fetch = async (url, opciones) => {
    pedidas.push({ url, metodo: opciones.method, cuerpo: JSON.parse(opciones.body) });
    const { estado, datos } = contestar();
    return {
      ok: estado < 400, status: estado, headers: { get: () => null }, json: async () => datos,
    };
  };
  return pedidas;
}

// Pinta el bautizo, escribe `nombre` en su campo y lo manda; da lo que se le
// pasó a `seguir` (que es lo último que hace el envío).
async function bautizarCon(estado, nombre) {
  const contenedor = new Elemento('main');
  let seguir;
  const seguido = new Promise((listo) => { seguir = async (...args) => listo(args); });
  bautizo(contenedor, seguir, { sesion: { usuario: 'ana' }, estado });
  const [campo] = buscar(contenedor, 'input');
  campo.value = nombre;
  const [formulario] = buscar(contenedor, 'form');
  formulario.oyentes.submit[0]({ preventDefault() {} });
  return { contenedor, seguido: await seguido };
}

const nacido = {
  id: 3, nombre: 'Pulpito', espera_nombre: true, nombre_especie: 'Pulpito', nombre_etapa: 'bebé',
  genero: 'hembra', emoji: '🐙', retrato: '/gachamon/retrato/pulpo/bebe/feliz/sin.png',
};
const recluta = { id: 7, nombre_especie: 'Pollito', retrato: '/gachamon/retrato/pollito/bebe/feliz/sin.png' };
const conRecluta = { avatar: {}, gachamon: null, difunto: null, sin_nombre: recluta };
const ESPERA_EN_LA_INCUBADORA = 'Este Pollito espera en la incubadora y todavía no tiene nombre.';

test('el bautizo de un recluta dice que espera en la incubadora, enseña su retrato y manda su id', { timeout: 2000 }, async () => {
  const despues = { ...conRecluta, gachamon: { ...nacido, id: 7, nombre: 'Bruma', espera_nombre: false } };
  const pedidas = servidor(() => ({ estado: 200, datos: despues }));
  const { contenedor, seguido } = await bautizarCon(conRecluta, 'Bruma');
  assert.ok(textos(contenedor).includes(ESPERA_EN_LA_INCUBADORA));
  assert.deepEqual(buscar(contenedor, 'img').map((img) => img.atributos.src), [recluta.retrato]);
  assert.equal(pedidas.length, 1);
  assert.equal(pedidas[0].metodo, 'POST');
  assert.ok(pedidas[0].url.endsWith('/bautizar'), pedidas[0].url);
  assert.deepEqual(pedidas[0].cuerpo, { nombre: 'Bruma', gachamon_id: 7 });
  // Lo que contesta es el estado: con él se decide la pantalla.
  assert.deepEqual(seguido, [despues]);
});

test('el bautizo del recién nacido no manda gachamon_id: es el de la activa, como siempre', { timeout: 2000 }, async () => {
  const pedidas = servidor(() => ({ estado: 200, datos: { gachamon: { ...nacido, nombre: 'Bruma' } } }));
  const { contenedor } = await bautizarCon({ avatar: {}, gachamon: nacido, difunto: null, sin_nombre: null }, 'Bruma');
  assert.ok(!textos(contenedor).includes(ESPERA_EN_LA_INCUBADORA));
  assert.deepEqual(pedidas[0].cuerpo, { nombre: 'Bruma' });
  assert.ok(!Object.hasOwn(pedidas[0].cuerpo, 'gachamon_id'));
});

test('si el recluta ya tiene nombre o ya no está, se vuelve a decidir sin enseñar un error', { timeout: 2000 }, async () => {
  for (const [clave, mensaje] of [['ya_bautizado', 'Ese gachamon ya tiene nombre.'], ['no_esta', 'Ese gachamon ya no está.']]) {
    servidor(() => ({ estado: 409, datos: { detail: { clave, mensaje } } }));
    const { contenedor, seguido } = await bautizarCon(conRecluta, 'Bruma');
    assert.deepEqual(seguido, [], clave);
    assert.ok(!textos(contenedor).includes(mensaje), clave);
  }
});

// Las muestras de color de las opciones: una por cada piel, color de pelo y
// ropa que tiene dibujo en el contrato del arte, y ninguna de más.
test('cada opción que se elige por color tiene su muestra', async () => {
  const { readFileSync } = await import('node:fs');
  const contrato = JSON.parse(readFileSync(new URL('../../web/static/datos/arte.json', import.meta.url), 'utf8'));
  const claves = (prefijo, parte) => [...new Set(contrato.piezas
    .filter((p) => p.ruta.startsWith(prefijo))
    .map((p) => p.ruta.slice(prefijo.length).split('-')[parte]))].sort();
  assert.deepEqual(Object.keys(MUESTRAS.piel).sort(), claves('avatar/cuerpo/', 0));
  assert.deepEqual(Object.keys(MUESTRAS.color_de_pelo).sort(), claves('avatar/pelo/', 1));
  assert.deepEqual(Object.keys(MUESTRAS.ropa).sort(), claves('avatar/ropa/', 0));
  for (const tabla of Object.values(MUESTRAS)) {
    for (const color of Object.values(tabla)) assert.match(color, /^#[0-9a-f]{6}$/);
  }
});
