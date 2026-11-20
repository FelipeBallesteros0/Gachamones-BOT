import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Lo justo de un navegador para abrir el pueblo sin pantalla, tocar sus
// botones y hacerlo caminar: elementos con sus hijos, su texto, atributos,
// clases y oyentes, que se buscan con selectores sencillos (etiqueta,
// `.clase`, `[atributo]`); un lienzo de 390 × 300 que apunta cada imagen que
// se pinta en él; imágenes que cargan solas y dicen de dónde vienen; los datos
// del pueblo de verdad; y unos cuadros de animación que no corren solos.
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

function escuchar(oyentes, tipo, oyente, opciones) {
  const signal = opciones && opciones.signal;
  if (signal && signal.aborted) return;
  (oyentes[tipo] ||= []).push(oyente);
  if (signal) signal.addEventListener('abort', () => { oyentes[tipo] = oyentes[tipo].filter((o) => o !== oyente); });
}

function sacar(nodo) {
  if (nodo.padre) nodo.padre.hijos = nodo.padre.hijos.filter((h) => h !== nodo);
  nodo.padre = null;
}

// Las imágenes que se pintaron en el lienzo, por su dirección, en orden.
const pintadas = [];

class Elemento extends Nodo {
  constructor(etiqueta) {
    super();
    this.etiqueta = etiqueta;
    this.atributos = {};
    this.oyentes = {};
    this.hijos = [];
    this.style = { setProperty() {} };
    this.dataset = {};
    this.isConnected = true;
    // El lienzo del mapa tiene su tamaño en la página; lo demás no se mide.
    this.clientWidth = etiqueta === 'canvas' ? 390 : 0;
    this.clientHeight = etiqueta === 'canvas' ? 300 : 0;
  }

  setAttribute(nombre, valor) { this.atributos[nombre] = String(valor); }

  getAttribute(nombre) { return Object.hasOwn(this.atributos, nombre) ? this.atributos[nombre] : null; }

  removeAttribute(nombre) { delete this.atributos[nombre]; }

  get hidden() { return Object.hasOwn(this.atributos, 'hidden'); }

  set hidden(valor) {
    if (valor) this.atributos.hidden = '';
    else delete this.atributos.hidden;
  }

  get classList() {
    const leer = () => String(this.atributos.class || '').split(/\s+/).filter(Boolean);
    const escribir = (lista) => { this.atributos.class = lista.join(' '); };
    return {
      add: (...nombres) => escribir([...new Set([...leer(), ...nombres])]),
      remove: (...nombres) => escribir(leer().filter((c) => !nombres.includes(c))),
      contains: (nombre) => leer().includes(nombre),
      toggle: (nombre, poner) => {
        const quiere = poner === undefined ? !leer().includes(nombre) : Boolean(poner);
        if (quiere) escribir([...new Set([...leer(), nombre])]);
        else escribir(leer().filter((c) => c !== nombre));
        return quiere;
      },
    };
  }

  get textContent() { return this.hijos.map((h) => h.textContent).join(''); }

  set textContent(texto) { this.replaceChildren(...(texto === '' ? [] : [new Texto(String(texto))])); }

  addEventListener(tipo, oyente, opciones) { escuchar(this.oyentes, tipo, oyente, opciones); }

  append(...nodos) {
    for (const nodo of nodos) {
      sacar(nodo);
      nodo.padre = this;
      this.hijos.push(nodo);
    }
  }

  replaceChildren(...nodos) {
    for (const hijo of [...this.hijos]) sacar(hijo);
    this.append(...nodos);
  }

  cumple(selector) {
    if (selector.startsWith('.')) return this.classList.contains(selector.slice(1));
    if (selector.startsWith('[')) return Object.hasOwn(this.atributos, selector.slice(1, -1));
    return this.etiqueta === selector;
  }

  querySelectorAll(selector) {
    return this.hijos.filter((h) => h instanceof Elemento)
      .flatMap((h) => [...(h.cumple(selector) ? [h] : []), ...h.querySelectorAll(selector)]);
  }

  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }

  focus() { document.activeElement = this; }

  getBoundingClientRect() { return { left: 0, top: 0, width: this.clientWidth, height: this.clientHeight }; }

  // Un contexto que acepta todo, mide el texto y apunta las imágenes que pinta.
  getContext() {
    return new Proxy({}, {
      get: (_, nombre) => {
        if (nombre === 'measureText') return (texto) => ({ width: String(texto).length * 7 });
        if (nombre === 'drawImage') return (imagen) => { pintadas.push(String(imagen.src)); };
        return () => {};
      },
      set: () => true,
    });
  }
}
globalThis.Node = Nodo;

// Las direcciones de todas las imágenes que se pidieron, en orden.
const pedidas = [];
globalThis.Image = class {
  constructor() {
    this.naturalWidth = 48;
    this.naturalHeight = 48;
  }

  get src() { return this.direccion; }

  set src(direccion) {
    this.direccion = direccion;
    pedidas.push(String(direccion));
    queueMicrotask(() => { if (this.onload) this.onload(); });
  }
};

// Los cuadros de animación se apuntan y corren sólo cuando la prueba lo dice.
let marcas = 0;
const cuadros = new Map();
globalThis.requestAnimationFrame = (hacer) => {
  marcas += 1;
  cuadros.set(marcas, hacer);
  return marcas;
};
globalThis.cancelAnimationFrame = (marca) => { cuadros.delete(marca); };

// Hace correr los cuadros pedidos, uno cada 16 ms, hasta que no se pida ninguno más.
let hora = 0;
async function caminarHastaParar() {
  for (let vuelta = 0; vuelta < 2000 && cuadros.size; vuelta += 1) {
    const tanda = [...cuadros];
    cuadros.clear();
    hora += 16;
    for (const [, hacer] of tanda) hacer(hora);
  }
  await asentar();
}

globalThis.ResizeObserver = class {
  observe() {}

  disconnect() {}
};
globalThis.window = {
  devicePixelRatio: 1,
  matchMedia: (consulta) => ({ matches: false, media: consulta, addEventListener() {}, removeEventListener() {} }),
  addEventListener() {},
};

async function asentar() {
  for (let vuelta = 0; vuelta < 20; vuelta += 1) await new Promise((listo) => { setImmediate(listo); });
}

globalThis.document = {
  hidden: false,
  activeElement: null,
  body: null,
  createElement: (etiqueta) => new Elemento(etiqueta),
  createTextNode: (texto) => new Texto(texto),
  addEventListener() {},
};

const { pueblo } = await import('../../web/static/js/mapa.js');

// El servidor de mentira: los datos del pueblo de verdad y, al llegar a un
// lugar, el estado que le toca. Apunta cada petición al juego como `[ruta, cuerpo]`.
const DATOS_DEL_PUEBLO = JSON.parse(readFileSync(new URL('../../web/static/datos/pueblo.json', import.meta.url), 'utf8'));
function crearServidor(alLlegar) {
  const pedidos = [];
  globalThis.fetch = async (url, opciones = {}) => {
    const direccion = String(url);
    if (direccion.endsWith('/datos/pueblo.json')) {
      return { ok: true, status: 200, json: async () => DATOS_DEL_PUEBLO };
    }
    const ruta = `${opciones.method} ${direccion.replace(/^\/monsteropolis\/api\//, '')}`;
    const cuerpo = opciones.body ? JSON.parse(opciones.body) : undefined;
    pedidos.push([ruta, cuerpo]);
    return { ok: true, status: 200, headers: { get: () => null }, json: async () => alLlegar(cuerpo) };
  };
  return pedidos;
}

const AVATAR = {
  nombre: 'Ana', genero: 'hembra', piel: 'clara', pelo: 'largo', color_de_pelo: 'rojo', ropa: 'camisa',
};
const CASA = { clave: 'casa', nombre: 'Tu departamento', abre: 'ya', aviso: null, ofrece: ['departamento'] };
const RETRATO = '/monsteropolis/retrato/pollito/bebe/feliz/sin.png';
const PELUSA = {
  id: 5, nombre: 'Pelusa', emoji: '🐤', retrato: RETRATO, etapa: 'bebe', espera_nombre: false,
};
const estadoEnCasa = (gachamon) => ({
  ahora: '2026-11-17T12:00:00+00:00',
  avatar: AVATAR,
  saldos: { monedas: 0, gemas: 0 },
  gachamon,
  globos: [],
  lugar: CASA,
  carta: false,
});

// Abre el pueblo y espera a que esté listo. Lo que pide pasar a otra pantalla
// queda en `seguidos`.
async function abrir(estado) {
  pintadas.length = 0;
  pedidas.length = 0;
  cuadros.clear();
  const pedidos = crearServidor(({ lugar }) => ({ ...estado, lugar: { ...CASA, clave: lugar } }));
  const contenedor = new Elemento('main');
  const seguidos = [];
  await pueblo(contenedor, estado, (...argumentos) => { seguidos.push(argumentos); });
  await asentar();
  return { contenedor, seguidos, pedidos };
}

const delRetrato = (direccion) => direccion.includes('/retrato/');
const deLaSombra = (direccion) => direccion.endsWith('efectos/sombra.png');
const delAvatar = (direccion) => direccion.includes('/arte/avatar/');

test('sin gachamon, el pueblo se abre y caminas tú solo', { timeout: 5000 }, async () => {
  const { contenedor, seguidos, pedidos } = await abrir(estadoEnCasa(null));
  // Se ve: el título, la lista de lugares para ir, y en el lienzo tu avatar.
  assert.equal(contenedor.querySelector('h1').textContent, '🗺️Pueblo');
  assert.equal(contenedor.querySelector('.ir-a').hidden, false);
  assert.equal(contenedor.querySelectorAll('.lugar-del-pueblo').length, Object.keys(DATOS_DEL_PUEBLO.lugares).length);
  // Estás en tu departamento: «Volver» dice adónde, y en la lista está marcado con el 📍, que va en su
  // propia marca (el estilo la pone en la esquina, fuera del nombre) y que el lector no lee: sólo el nombre
  // y que es donde estás.
  assert.equal(contenedor.querySelector('.boton-volver').textContent, 'Volver a tu departamento');
  const [aqui, ...losDemas] = contenedor.querySelectorAll('.lugar-del-pueblo');
  assert.equal(aqui.textContent, '📍Tu departamento');
  assert.equal(aqui.getAttribute('aria-current'), 'location');
  const [marca, nombre] = aqui.hijos;
  assert.equal(marca.etiqueta, 'span');
  assert.equal(marca.getAttribute('class'), 'lugar-del-pueblo-aqui');
  assert.equal(marca.getAttribute('aria-hidden'), 'true');
  assert.equal(marca.textContent, '📍');
  assert.equal(nombre.textContent, 'Tu departamento');
  for (const otro of losDemas) {
    assert.equal(otro.getAttribute('aria-current'), null);
    assert.equal(otro.querySelectorAll('.lugar-del-pueblo-aqui').length, 0);
  }
  assert.ok(pintadas.some(delAvatar), 'no se pintó el avatar');
  // Ningún retrato que pedir ni que pintar, ni la sombra del que camina detrás.
  assert.deepEqual(pedidas.filter(delRetrato), []);
  assert.deepEqual(pintadas.filter(delRetrato), []);
  assert.deepEqual(pintadas.filter(deLaSombra), []);
  // A la Tienda, caminando: llega, le dice al servidor dónde está y entra.
  const [aLaTienda] = contenedor.querySelectorAll('.lugar-del-pueblo')
    .filter((boton) => boton.textContent === DATOS_DEL_PUEBLO.lugares.tienda.nombre);
  pintadas.length = 0;
  for (const oyente of aLaTienda.oyentes.click) oyente({ type: 'click' });
  await caminarHastaParar();
  assert.ok(pintadas.some(delAvatar), 'no caminó');
  assert.deepEqual(pintadas.filter(delRetrato), []);
  assert.deepEqual(pintadas.filter(deLaSombra), []);
  assert.deepEqual(pedidos, [['POST lugar', { lugar: 'tienda' }]]);
  assert.equal(seguidos.length, 1);
  assert.equal(seguidos[0][0].gachamon, null);
  assert.deepEqual(seguidos[0][1], { llegando: true });
});

test('con gachamon, camina detrás de ti con su retrato y su sombra, como siempre', { timeout: 5000 }, async () => {
  const { contenedor, seguidos, pedidos } = await abrir(estadoEnCasa(PELUSA));
  assert.equal(contenedor.querySelector('.ir-a').hidden, false);
  assert.deepEqual(pedidas.filter(delRetrato), [RETRATO]);
  assert.ok(pintadas.some(delAvatar), 'no se pintó el avatar');
  assert.deepEqual(pintadas.filter(delRetrato), [RETRATO]);
  assert.equal(pintadas.filter(deLaSombra).length, 1);
  const [aLaTienda] = contenedor.querySelectorAll('.lugar-del-pueblo')
    .filter((boton) => boton.textContent === DATOS_DEL_PUEBLO.lugares.tienda.nombre);
  pintadas.length = 0;
  for (const oyente of aLaTienda.oyentes.click) oyente({ type: 'click' });
  await caminarHastaParar();
  // En cada cuadro, los dos.
  const cuantos = pintadas.filter(delRetrato).length;
  assert.ok(cuantos > 10, cuantos);
  assert.equal(pintadas.filter(deLaSombra).length, cuantos);
  assert.deepEqual(pedidos, [['POST lugar', { lugar: 'tienda' }]]);
  assert.equal(seguidos.length, 1);
  assert.equal(seguidos[0][0].gachamon.id, PELUSA.id);
  assert.deepEqual(seguidos[0][1], { llegando: true });
});
