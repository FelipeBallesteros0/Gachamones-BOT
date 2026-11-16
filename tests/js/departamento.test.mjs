import test from 'node:test';
import assert from 'node:assert/strict';
import { medir, proyectar } from '../../web/static/js/proyeccion.js';

// Lo justo de un navegador para pintar el departamento sin pantalla, tocar sus
// botones y su lienzo: elementos con sus hijos (y quién los contiene), su
// texto, atributos, clases y oyentes, que se buscan con selectores sencillos
// (etiqueta, `.clase`, `[atributo]`, `[atributo=valor]`, juntos y uno dentro
// de otro); un lienzo que mide 380 × 310 y se deja pintar; y un reloj y unos
// cuadros de animación que no corren solos.
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

// Los oyentes de un elemento o del documento, que se quitan solos con su `signal`.
function escuchar(oyentes, tipo, oyente, opciones) {
  const signal = opciones && opciones.signal;
  if (signal && signal.aborted) return;
  (oyentes[tipo] ||= []).push(oyente);
  if (signal) signal.addEventListener('abort', () => { oyentes[tipo] = oyentes[tipo].filter((o) => o !== oyente); });
}

const LIENZO = { left: 10, top: 60, width: 380, height: 310 };

function cumpleSimple(nodo, simple) {
  return (simple.match(/^[a-z0-9]+|\.[\w-]+|\[[^\]]+\]/g) || []).every((parte) => {
    if (parte.startsWith('.')) return nodo.classList.contains(parte.slice(1));
    if (parte.startsWith('[')) {
      const [nombre, valor] = parte.slice(1, -1).split('=');
      if (valor === undefined) return Object.hasOwn(nodo.atributos, nombre);
      return nodo.getAttribute(nombre) === valor.replace(/^["']|["']$/g, '');
    }
    return nodo.etiqueta === parte;
  });
}

class Elemento extends Nodo {
  constructor(etiqueta) {
    super();
    this.etiqueta = etiqueta;
    this.atributos = {};
    this.oyentes = {};
    this.hijos = [];
    this.style = { setProperty() {} };
    this.isConnected = true;
  }

  setAttribute(nombre, valor) { this.atributos[nombre] = String(valor); }

  getAttribute(nombre) { return Object.hasOwn(this.atributos, nombre) ? this.atributos[nombre] : null; }

  removeAttribute(nombre) { delete this.atributos[nombre]; }

  get hidden() { return Object.hasOwn(this.atributos, 'hidden'); }

  set hidden(valor) {
    if (valor) this.atributos.hidden = '';
    else delete this.atributos.hidden;
  }

  // Las clases son las del atributo `class`, como en un navegador.
  get classList() {
    const leer = () => String(this.atributos.class || '').split(/\s+/).filter(Boolean);
    const escribir = (lista) => { this.atributos.class = lista.join(' '); };
    const add = (...nombres) => escribir([...new Set([...leer(), ...nombres])]);
    const remove = (...nombres) => escribir(leer().filter((c) => !nombres.includes(c)));
    return {
      add,
      remove,
      contains: (nombre) => leer().includes(nombre),
      toggle: (nombre, poner) => {
        const quiere = poner === undefined ? !leer().includes(nombre) : Boolean(poner);
        if (quiere) add(nombre);
        else remove(nombre);
        return quiere;
      },
    };
  }

  get textContent() { return this.hijos.map((h) => h.textContent).join(''); }

  set textContent(texto) { this.replaceChildren(...(texto === '' ? [] : [new Texto(String(texto))])); }

  addEventListener(tipo, oyente, opciones) { escuchar(this.oyentes, tipo, oyente, opciones); }

  append(...nodos) {
    for (const nodo of nodos) nodo.padre = this;
    this.hijos.push(...nodos);
  }

  replaceChildren(...nodos) {
    this.hijos = [];
    this.append(...nodos);
  }

  remove() {
    if (this.padre) this.padre.hijos = this.padre.hijos.filter((h) => h !== this);
    this.padre = null;
  }

  cumple(selector) {
    return selector.split(',').some((s) => {
      const cadena = s.trim().split(/\s+/);
      if (!cumpleSimple(this, cadena.at(-1))) return false;
      let k = cadena.length - 2;
      for (let p = this.padre; p && k >= 0; p = p.padre) if (p instanceof Elemento && cumpleSimple(p, cadena[k])) k -= 1;
      return k < 0;
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

  getBoundingClientRect() {
    const { left, top, width, height } = this.etiqueta === 'canvas' ? LIENZO : { left: 0, top: 0, width: 0, height: 0 };
    return { left, top, width, height, x: left, y: top, right: left + width, bottom: top + height };
  }

  // Un contexto que acepta todo lo que se le pida pintar.
  getContext() { return new Proxy({}, { get: () => () => {} }); }
}

// Lo que corre con el tiempo se apunta y no corre solo.
let marcas = 0;
const pendientes = new Map();
const apuntar = (hacer) => { marcas += 1; pendientes.set(marcas, hacer); return marcas; };
const olvidar = (marca) => { pendientes.delete(marca); };
globalThis.setTimeout = apuntar;
globalThis.clearTimeout = olvidar;
globalThis.setInterval = apuntar;
globalThis.clearInterval = olvidar;
globalThis.requestAnimationFrame = apuntar;
globalThis.cancelAnimationFrame = olvidar;
globalThis.ResizeObserver = class {
  observe() {}

  disconnect() {}
};
globalThis.Node = Nodo;

// Lo que dicen las preferencias del aparato: sólo si se pidió menos movimiento.
let reducido = false;
globalThis.window = {
  devicePixelRatio: 1,
  matchMedia: (consulta) => ({
    matches: reducido && consulta.includes('reduce'), media: consulta, addEventListener() {}, removeEventListener() {},
  }),
  addEventListener() {},
};

// Deja correr todo lo que ya está en camino (respuestas, promesas encadenadas).
async function asentar() {
  for (let vuelta = 0; vuelta < 20; vuelta += 1) await new Promise((listo) => { setImmediate(listo); });
}

// Un documento nuevo para cada pantalla: así los oyentes de una prueba no oyen la siguiente.
function nuevoDocumento() {
  const oyentes = {};
  const documento = {
    hidden: false,
    activeElement: null,
    body: null,
    createElement: (etiqueta) => new Elemento(etiqueta),
    createTextNode: (texto) => new Texto(texto),
    addEventListener: (tipo, oyente, opciones) => escuchar(oyentes, tipo, oyente, opciones),
    async dispara(tipo) {
      for (const oyente of [...(oyentes[tipo] || [])]) oyente({ type: tipo });
      await asentar();
    },
  };
  globalThis.document = documento;
  return documento;
}

nuevoDocumento();
const { departamento } = await import('../../web/static/js/departamento.js');

// Un servidor de mentira para `pedir`: apunta cada petición como `[ruta, cuerpo]`
// («GET departamento») y contesta lo que se le haya dicho para esa ruta. Un
// `Error` es quedarse sin red; un objeto con `estado` numérico, un «no» del
// juego con ese código. `retiene` deja en camino la próxima petición a esa
// ruta hasta que se suelta con lo que contesta.
function crearServidor() {
  const pedidos = [];
  const respuestas = new Map();
  const retenidas = new Map();

  function contestar(cuerpo) {
    if (cuerpo instanceof Error) throw new TypeError('Failed to fetch');
    if (cuerpo && typeof cuerpo.estado === 'number') {
      const { estado, clave, mensaje } = cuerpo;
      return { ok: false, status: estado, headers: { get: () => null }, json: async () => ({ detail: { clave, mensaje } }) };
    }
    return { ok: true, status: 200, headers: { get: () => null }, json: async () => cuerpo };
  }

  globalThis.fetch = async (url, opciones) => {
    const ruta = `${opciones.method} ${String(url).replace(/^\/gachamon\/api\//, '')}`;
    pedidos.push([ruta, opciones.body ? JSON.parse(opciones.body) : undefined]);
    if (retenidas.has(ruta)) {
      const espera = retenidas.get(ruta);
      retenidas.delete(ruta);
      return contestar(await espera);
    }
    if (!respuestas.has(ruta)) return contestar({ estado: 404, clave: 'no_existe', mensaje: 'Eso no existe.' });
    return contestar(respuestas.get(ruta));
  };

  return {
    pedidos,
    responde: (ruta, cuerpo) => { respuestas.set(ruta, cuerpo); },
    falla: (ruta) => { respuestas.set(ruta, new Error('sin red')); },
    retiene(ruta) {
      let soltar;
      retenidas.set(ruta, new Promise((listo) => { soltar = listo; }));
      return async (cuerpo) => {
        soltar(cuerpo);
        await asentar();
      };
    },
  };
}

// --- lo que se pinta ---------------------------------------------------------------

const CAMA_ID = 21;
const GUARDADA_ID = 22;
const MACETA_ID = 23;

const CAMA = { clave: 'cama_sencilla', nombre: 'Cama sencilla', icono: 'iconos/muebles/cama_sencilla.png', capa: 'bulto', cama: true, ancho: 2, fondo: 1 };
const MACETA = { clave: 'maceta', icono: 'iconos/muebles/maceta.png', capa: 'bulto', cama: false, ancho: 1, fondo: 1 };

const PELUSA = {
  id: 7, nombre: 'Pelusa', espera_nombre: false, se_nombro_solo: false, especie: 'pollito', nombre_especie: 'Pollito',
  emoji: '🐣', etapa: 'bebe', nombre_etapa: 'cría', nivel: 3, genero: 'hembra',
  barras: { comida: 62, animo: 80, aseo: 45 }, cara: 'feliz', desfallecido: false,
  retrato: '/gachamon/retrato/pollito/bebe/feliz/sin.png', esperas: {}, titulo: null,
};

const ESTADO = {
  ahora: '2026-11-16T12:00:00+00:00',
  avatar: { nombre: 'Feli', genero: 'hembra', piel: 'clara', pelo: 'largo', color_de_pelo: 'rojo', ropa: 'camisa' },
  gachamon: PELUSA,
  saldos: { monedas: 130, gemas: 2 },
  globos: [],
  lugar: { clave: 'casa', nombre: 'Tu casa', abre: null, aviso: null, ofrece: ['departamento'] },
};

// Un 3 × 3 con la cama sencilla en (0, 0), a lo ancho, y otra guardada.
const DEPTO = {
  ancho: 3, fondo: 3, casillas: 9, comodidad: 82, tope: 100, camas: 1, gachamones: 1,
  plantel: [{ ...PELUSA, activo: true }], cabe_otro: false, ampliar: { ancho: 45, fondo: 45 },
  puestos: [{ id: CAMA_ID, ...CAMA, x: 0, y: 0, giro: 0, casillas: [[0, 0], [1, 0]] }],
  guardados: [{ id: GUARDADA_ID, ...CAMA }],
  saldos: { monedas: 130, gemas: 2 },
};

// El mismo, con una maceta en (2, 2).
const CON_MACETA = {
  ...DEPTO,
  puestos: [...DEPTO.puestos, { id: MACETA_ID, ...MACETA, nombre: 'Maceta', x: 2, y: 2, giro: 0, casillas: [[2, 2]] }],
};

// Monta la pantalla con lo que contesta `GET departamento` y espera a que se asiente.
async function abrir(depto, estado = ESTADO, { movimientoReducido = false } = {}) {
  const documento = nuevoDocumento();
  reducido = movimientoReducido;
  const servidor = crearServidor();
  servidor.responde('GET departamento', depto);
  const pantalla = new Elemento('main');
  const seguido = [];
  departamento(pantalla, estado, (...argumentos) => { seguido.push(argumentos); });
  await asentar();
  return { pantalla, pedidos: servidor.pedidos, servidor, seguido, documento };
}

const uno = (raiz, selector) => raiz.querySelector(selector);
const todos = (raiz, selector) => raiz.querySelectorAll(selector);

// El texto de lo que cumple el selector (o de la raíz, sin él); `null` si no hay.
function texto(raiz, selector) {
  const nodo = selector === undefined ? raiz : uno(raiz, selector);
  return nodo ? nodo.textContent : null;
}

const boton = (raiz, que) => todos(raiz, 'button').find((b) => b.textContent.includes(que)) || null;

async function tocar(nodo) {
  for (const oyente of [...(nodo.oyentes.click || [])]) oyente({ type: 'click' });
  await asentar();
}

// Un toque en ese píxel del lienzo, contado desde su esquina.
async function tocarEn(pantalla, x, y) {
  const lienzo = uno(pantalla, 'canvas');
  const caja = lienzo.getBoundingClientRect();
  for (const oyente of [...(lienzo.oyentes.click || [])]) {
    oyente({ type: 'click', clientX: caja.left + x, clientY: caja.top + y, preventDefault() {} });
  }
  await asentar();
}

// La pieza que se ve, medida como la mide la pantalla: su tamaño sale de la línea de abajo.
function medidaDe(pantalla) {
  const [, ancho, fondo] = texto(pantalla, '.pieza-linea').match(/^(\d+) × (\d+)/).map(Number);
  return { m: medir(LIENZO.width, LIENZO.height, ancho, fondo), ancho, fondo };
}

async function tocarCasilla(pantalla, i, j) {
  const { m } = medidaDe(pantalla);
  await tocarEn(pantalla, ...proyectar(m, i + 0.5, j + 0.5));
}

// A media altura de ese tramo: `(-1, j)` en la pared izquierda, `(i, -1)` en la derecha.
async function tocarTramo(pantalla, i, j) {
  const { m } = medidaDe(pantalla);
  const punto = i === -1 ? proyectar(m, 0, j + 0.5, m.pared / 2) : proyectar(m, i + 0.5, 0, m.pared / 2);
  await tocarEn(pantalla, ...punto);
}

// --- las pruebas ---------------------------------------------------------------------

test('al entrar pide el departamento y dice cómo está', async () => {
  const { pantalla, pedidos } = await abrir(DEPTO);
  assert.deepEqual(pedidos.map(([ruta]) => ruta), ['GET departamento']);
  assert.equal(texto(pantalla, '.pieza-linea'), '3 × 3 · 2 de 9 casillas · camas 1 · gachamones 1 · comodidad 82 de 100');
  assert.equal(uno(pantalla, 'canvas').getAttribute('aria-hidden'), 'true');
  assert.match(texto(pantalla, 'h1'), /Tu casa/);
});

test('si no carga lo dice y deja volver a intentarlo', async () => {
  const { pantalla, pedidos, servidor } = await abrir(new Error('sin red'));
  assert.equal(texto(pantalla, '[role=alert]'), 'No hubo respuesta. Revisa tu conexión.');
  servidor.responde('GET departamento', DEPTO);
  await tocar(boton(pantalla, 'Volver a intentarlo'));
  assert.equal(pedidos.length, 2);
  assert.equal(texto(pantalla, '.pieza-linea').startsWith('3 × 3'), true);
});

test('un 409 al leer se va de la pantalla', async () => {
  const { seguido } = await abrir({ estado: 409, clave: 'no_estas_ahi', mensaje: 'Para eso tienes que estar en tu departamento.' });
  assert.equal(seguido.length, 1);
});

test('al volver a la pestaña se vuelve a leer', async () => {
  const { pantalla, pedidos, servidor, documento } = await abrir(DEPTO);
  servidor.responde('GET departamento', CON_MACETA);
  await documento.dispara('visibilitychange');
  assert.equal(pedidos.length, 2);
  assert.equal(texto(pantalla, '.pieza-linea').startsWith('3 × 3 · 3 de 9'), true);
});

test('tocar fuera de la pieza no hace nada', async () => {
  const { pantalla, pedidos } = await abrir(DEPTO);
  await tocarEn(pantalla, 2, 2);                                        // una esquina del lienzo
  assert.equal(pedidos.length, 1);
  assert.equal(texto(pantalla, '[role=status].aviso'), '');
});
