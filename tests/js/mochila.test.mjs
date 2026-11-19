import test from 'node:test';
import assert from 'node:assert/strict';

// Lo justo de un navegador para pintar la mochila sin pantalla y tocar sus
// botones (el mismo de la tienda): elementos con sus hijos (y quién los
// contiene), atributos, clases y oyentes, que se buscan por etiqueta, por
// `.clase` o por `[atributo]`, y un lienzo que se deja pintar.
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

  removeAttribute(nombre) { delete this.atributos[nombre]; }

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

  focus() { document.activeElement = this; }

  // Un contexto que acepta todo lo que se le pida pintar.
  getContext() { return new Proxy({}, { get: () => () => {}, set: () => true }); }
}
globalThis.Node = Nodo;
globalThis.document = {
  createElement: (etiqueta) => new Elemento(etiqueta),
  createTextNode: (texto) => Object.assign(new Nodo(), { texto }),
  activeElement: null,
};
globalThis.window = { devicePixelRatio: 1 };

const { mochila } = await import('../../web/static/js/mochila.js');

// Un «no» del juego, para que el servidor de mentira lo conteste con su código.
const NO = Symbol('no');
const noDelJuego = (estado, clave, mensaje) => ({ [NO]: { estado, clave, mensaje } });

// Un servidor de mentira para `pedir`: apunta cada petición y contesta lo que
// diga `contestar(peticion)` (o, con `noDelJuego`, ese error).
function servidor(contestar) {
  const pedidas = [];
  globalThis.fetch = async (url, opciones) => {
    const pedida = { url, metodo: opciones.method, cuerpo: opciones.body ? JSON.parse(opciones.body) : null };
    pedidas.push(pedida);
    const datos = contestar(pedida);
    if (datos && datos[NO]) {
      const { estado, clave, mensaje } = datos[NO];
      return {
        ok: false, status: estado, headers: { get: () => null }, json: async () => ({ detail: { clave, mensaje } }),
      };
    }
    return { ok: true, status: 200, headers: { get: () => null }, json: async () => datos };
  };
  return pedidas;
}

// Lo que llevas: dos pociones, que se usan al momento.
const LLEVAS = {
  objetos: [{
    clave: 'pocion_comida', nombre: 'Poción de comida', descripcion: 'Deja la comida a 100.',
    icono: 'iconos/objetos/pocion_comida.png', cantidad: 2, uso: 'al_momento', nota: null,
  }],
};

// Abre la mochila con `estado`, toca «Usar» y lo confirma. Lo que pide pasar a
// otra pantalla queda en `seguidos`.
async function usarLaPocion(estado) {
  const contenedor = new Elemento('main');
  const seguidos = [];
  assert.equal(await mochila(contenedor, estado, (...argumentos) => { seguidos.push(argumentos); }), true);
  const laFila = () => contenedor.querySelector('ul').querySelectorAll('li')[0];
  laFila().querySelector('.boton-usar').oyentes.click[0]();
  const [si] = laFila().querySelectorAll('.principal');
  await si.oyentes.click[0]();
  return { contenedor, seguidos, fila: laFila() };
}

const PIDE_UN_GACHAMON = 'Para usar eso hace falta un gachamon.';

test('sin gachamon, «Usar» dice la frase del servidor y te deja en la mochila', { timeout: 2000 }, async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const pedidas = servidor((pedida) => (pedida.metodo === 'GET'
    ? LLEVAS
    : noDelJuego(409, 'sin_gachamon', PIDE_UN_GACHAMON)));
  const { contenedor, seguidos, fila } = await usarLaPocion({ saldos: { monedas: 0, gemas: 0 }, gachamon: null });
  // Se pidió sin decir a qué gachamon, porque no hay ninguno.
  const uso = pedidas.find((p) => p.metodo === 'POST');
  assert.ok(uso.url.endsWith('/mochila/usar'), uso.url);
  assert.equal(uso.cuerpo.clave, 'pocion_comida');
  assert.ok(!Object.hasOwn(uso.cuerpo, 'gachamon_id'));
  // No se vuelve a decidir: se dice la frase, como un «no».
  assert.deepEqual(seguidos, []);
  const aviso = contenedor.querySelector('.aviso-tienda');
  assert.equal(aviso.textContent, PIDE_UN_GACHAMON);
  assert.ok(aviso.classList.contains('es-error'));
  // La lista se queda (no se vuelve a pedir) y la fila vuelve a tener su «Usar», sin nada esperando.
  assert.deepEqual(pedidas.map((p) => p.metodo), ['GET', 'POST']);
  assert.equal(fila.querySelectorAll('.boton-usar').length, 1);
  assert.equal(fila.querySelectorAll('.pregunta').length, 0);
  assert.ok(!fila.classList.contains('en-camino'));
  for (const boton of contenedor.querySelectorAll('.boton-usar')) {
    assert.ok(!Object.hasOwn(boton.atributos, 'aria-disabled'));
  }
});

test('con gachamon, ese mismo «no» quiere decir que tu gachamon cambió: se vuelve a decidir', { timeout: 2000 }, async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const pedidas = servidor((pedida) => (pedida.metodo === 'GET'
    ? LLEVAS
    : noDelJuego(409, 'sin_gachamon', 'Tu gachamon ya no es el mismo. Mira otra vez.')));
  const { contenedor, seguidos } = await usarLaPocion({ saldos: { monedas: 40, gemas: 0 }, gachamon: { id: 5 } });
  assert.equal(pedidas.find((p) => p.metodo === 'POST').cuerpo.gachamon_id, 5);
  assert.deepEqual(seguidos, [[undefined]]);
  assert.ok(!contenedor.querySelector('.aviso-tienda').textContent);
});

// --- la placa: la pregunta dice de quién es el nombre que cambia ---------------------

// Lo que llevas: la poción y dos placas, que se usan escribiendo un nombre.
const PLACA = {
  clave: 'placa', nombre: 'Placa con nombre', descripcion: 'Le cambia el nombre a tu gachamon activo.',
  icono: 'iconos/objetos/placa.png', cantidad: 2, uso: 'con_nombre', nota: null,
};
const CON_LA_PLACA = { objetos: [...LLEVAS.objetos, PLACA] };

// El estado de quien sale con `gachamon` (o con nadie), en la mochila.
const conGachamon = (gachamon) => ({ saldos: { monedas: 40, gemas: 0 }, avatar: { nombre: 'Feli' }, gachamon });

// El texto que se ve dentro de un elemento, con el de sus hijos.
const textoDe = (nodo) => nodo.hijos.map((h) => (h instanceof Elemento ? textoDe(h) : h.texto)).join('');

// Abre la mochila con `estado` y devuelve cómo tocar «Usar» en una fila y la
// pregunta que abre esa fila.
async function abrirLaMochila(estado) {
  const contenedor = new Elemento('main');
  assert.equal(await mochila(contenedor, estado, () => {}), true);
  const fila = (clave) => contenedor.querySelector('ul').querySelectorAll('li')
    .find((li) => li.atributos['data-fila'] === clave);
  const tocarUsar = (clave) => fila(clave).querySelector('.boton-usar').oyentes.click[0]();
  const pregunta = (clave) => fila(clave).querySelector('.pregunta');
  return { contenedor, tocarUsar, pregunta };
}

test('la placa pregunta el nombre nuevo del que sale contigo, y lo demás de la pregunta sigue igual', { timeout: 2000 }, async () => {
  servidor(() => CON_LA_PLACA);
  const { tocarUsar, pregunta } = await abrirLaMochila(conGachamon({ id: 5, nombre: 'Pelusa' }));
  tocarUsar('placa');
  const caja = pregunta('placa');
  const etiqueta = caja.querySelector('label');
  assert.equal(textoDe(etiqueta), 'Nuevo nombre de Pelusa');
  assert.equal(etiqueta.atributos.for, 'mochila-nombre');
  // El campo, vacío y con el foco; el botón que confirma, «Cambiar nombre»; y «No».
  const campo = caja.querySelector('input');
  assert.equal(campo.atributos.id, 'mochila-nombre');
  assert.equal(campo.value, '');
  assert.equal(document.activeElement, campo);
  assert.deepEqual(caja.querySelectorAll('button').map(textoDe), ['Cambiar nombre', 'No']);
});

test('sin gachamon la pregunta de la placa sigue diciendo sólo «Nuevo nombre»', { timeout: 2000 }, async () => {
  servidor(() => CON_LA_PLACA);
  const { tocarUsar, pregunta } = await abrirLaMochila(conGachamon(null));
  tocarUsar('placa');
  assert.equal(textoDe(pregunta('placa').querySelector('label')), 'Nuevo nombre');
});

test('si llega un estado con otro saliendo contigo, la placa pregunta por el nombre de ése', { timeout: 2000 }, async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  // Mientras tanto, en otra pestaña, sales con Rulo: el estado que trae la
  // poción ya lo dice. Y después, la placa le cambia el nombre a Rulo.
  let respuestas = 0;
  const pedidas = servidor((pedida) => {
    if (pedida.metodo === 'GET') return CON_LA_PLACA;
    respuestas += 1;
    if (respuestas === 1) {
      return {
        ok: true, clave: null, mensaje: 'Rulo come. Comida +40 (ahora 100).',
        estado: conGachamon({ id: 7, nombre: 'Rulo' }), mochila: CON_LA_PLACA,
      };
    }
    return {
      ok: true, clave: null, mensaje: 'Rulo pasa a llamarse Nube.',
      estado: conGachamon({ id: 7, nombre: 'Nube' }), mochila: CON_LA_PLACA,
    };
  });
  const { tocarUsar, pregunta } = await abrirLaMochila(conGachamon({ id: 5, nombre: 'Pelusa' }));
  tocarUsar('pocion_comida');
  await pregunta('pocion_comida').querySelector('.principal').oyentes.click[0]();
  tocarUsar('placa');
  assert.equal(textoDe(pregunta('placa').querySelector('label')), 'Nuevo nombre de Rulo');
  // Lo que se escribe va al que dice la pregunta.
  pregunta('placa').querySelector('input').value = 'Nube';
  await pregunta('placa').querySelector('.principal').oyentes.click[0]();
  assert.equal(pedidas.at(-1).cuerpo.gachamon_id, 7);
  // Y la siguiente placa ya dice su nombre nuevo.
  tocarUsar('placa');
  assert.equal(textoDe(pregunta('placa').querySelector('label')), 'Nuevo nombre de Nube');
});

test('un «no» a la placa deja la pregunta abierta con el nombre del que sale contigo según el estado que llegó', { timeout: 2000 }, async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  servidor((pedida) => (pedida.metodo === 'GET' ? CON_LA_PLACA : {
    ok: false, clave: 'mismo_nombre', mensaje: 'Ya se llama así.',
    estado: conGachamon({ id: 7, nombre: 'Rulo' }), mochila: CON_LA_PLACA,
  }));
  const { tocarUsar, pregunta } = await abrirLaMochila(conGachamon({ id: 5, nombre: 'Pelusa' }));
  tocarUsar('placa');
  pregunta('placa').querySelector('input').value = 'Pelusa';
  await pregunta('placa').querySelector('.principal').oyentes.click[0]();
  const abierta = pregunta('placa');
  assert.equal(textoDe(abierta.querySelector('label')), 'Nuevo nombre de Rulo');
  assert.equal(abierta.querySelector('input').value, 'Pelusa');     // con lo que se escribió
});
