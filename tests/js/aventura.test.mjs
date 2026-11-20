import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Lo justo de un navegador para pintar la primera aventura sin pantalla y tocar
// sus botones: elementos con sus hijos (y quién los contiene), su texto,
// atributos, clases y oyentes, que se buscan con selectores sencillos
// (etiqueta, `.clase`, `[atributo]`); el foco, que se apunta en el documento;
// lienzos que aceptan todo lo que se les pida pintar; imágenes que cargan
// solas; y un reloj que no corre solo (lo que se programa se apunta y no se hace).
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

  remove() { sacar(this); }

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

  // Si se ve: ni él ni nada de lo que lo contiene está escondido.
  get seVe() {
    for (let nodo = this; nodo; nodo = nodo.padre) if (nodo.hidden) return false;
    return true;
  }

  focus() { document.activeElement = this; }

  // Un contexto que acepta todo lo que se le pida pintar.
  getContext() {
    return new Proxy({}, { get: () => () => {}, set: () => true });
  }

  // Un toque: lo oyen sus oyentes de `click`, que pueden ser asíncronos.
  async tocar() {
    for (const oyente of [...(this.oyentes.click || [])]) oyente({ type: 'click' });
    await asentar();
  }

  // Un clic con su `detail`, como lo cuenta un navegador: 1, un clic suelto; 2, el
  // segundo de un doble clic en el mismo sitio; 0, el que hace el teclado.
  async clicar(detail) {
    for (const oyente of [...(this.oyentes.click || [])]) oyente({ type: 'click', detail });
    await asentar();
  }
}
globalThis.Node = Nodo;

// Una imagen que carga sola en cuanto se le da su dirección.
globalThis.Image = class {
  constructor() {
    this.naturalWidth = 48;
    this.naturalHeight = 84;
  }

  get src() { return this.direccion; }

  set src(direccion) {
    this.direccion = direccion;
    queueMicrotask(() => { if (this.onload) this.onload(); });
  }
};

// Lo que corre con el tiempo se apunta y no corre (el corte de las peticiones,
// lo que se borra solo).
let marcas = 0;
const pendientes = new Map();
globalThis.setTimeout = (hacer, ms = 0) => {
  marcas += 1;
  pendientes.set(marcas, { hacer, ms });
  return marcas;
};
globalThis.clearTimeout = (marca) => { pendientes.delete(marca); };
globalThis.setInterval = globalThis.setTimeout;
globalThis.clearInterval = globalThis.clearTimeout;

globalThis.ResizeObserver = class {
  observe() {}

  disconnect() {}
};
globalThis.window = {
  devicePixelRatio: 1,
  matchMedia: (consulta) => ({ matches: false, media: consulta, addEventListener() {}, removeEventListener() {} }),
  addEventListener() {},
};

// Deja correr todo lo que ya está en camino (respuestas, promesas encadenadas).
async function asentar() {
  for (let vuelta = 0; vuelta < 20; vuelta += 1) await new Promise((listo) => { setImmediate(listo); });
}

// Un documento nuevo para cada pantalla: así el foco de una prueba no es el de la siguiente.
function nuevoDocumento() {
  const documento = {
    hidden: false,
    activeElement: null,
    body: new Elemento('body'),
    createElement: (etiqueta) => new Elemento(etiqueta),
    createTextNode: (texto) => new Texto(texto),
    addEventListener() {},
  };
  globalThis.document = documento;
  return documento;
}

nuevoDocumento();
const { aventura } = await import('../../web/static/js/aventura.js');

// Un servidor de mentira para `pedir`: apunta cada petición («GET aventura») y
// contesta lo que se le haya dicho para esa ruta. Un `Error` es quedarse sin
// red; un objeto con `estado` numérico, un «no» del juego con ese código.
// `retiene` deja en camino la próxima petición a esa ruta hasta que se suelta
// con lo que contesta.
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
    const ruta = `${opciones.method} ${String(url).replace(/^\/monsteropolis\/api\//, '')}`;
    pedidos.push(ruta);
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

// --- lo que manda el servidor ---------------------------------------------------------

const AVATAR = {
  nombre: 'Ana', genero: 'hembra', piel: 'clara', pelo: 'largo', color_de_pelo: 'rojo', ropa: 'camisa',
};
const AVENTURA = { clave: 'aventura', nombre: 'Aventura', abre: 'despues', aviso: null, ofrece: ['aventura'] };
const CASA = { clave: 'casa', nombre: 'Tu departamento', abre: 'ya', aviso: null, ofrece: ['departamento'] };
const ANTES = [
  'Sales del pueblo por el sendero. Hoy vas tú solo.',
  'Entre los matorrales, algo se mueve.',
  'No huye. Se queda mirándote.',
];
// Pollito es hembra: el servidor ya manda la frase concordada.
const DESPUES = [
  'Sale de su escondite: es una Pollito.',
  'Le tiendes la mano. La huele… y se queda a tu lado.',
  'Desde hoy vive contigo.',
];
const SIN_CAMA = 'Antes pon tu segunda cama en tu departamento: sin cama, nadie se queda contigo.';
const SE_PUEDE = { primera: { puede: true, motivo: null, antes: ANTES } };

// Quien todavía no tiene ningún gachamon, parado en «Aventura» con la cama libre.
const sinGachamon = (cambios = {}) => ({
  ahora: '2026-11-18T12:00:00+00:00',
  persona: { usuario: 'web:1', vinculada: false },
  avatar: AVATAR,
  saldos: { monedas: 0, gemas: 0 },
  gachamon: null,
  globos: [],
  lugar: AVENTURA,
  carta: false,
  guia: { clave: 'aventura', texto: 'Ya hay cama para un gachamon. Sal al pueblo y ve a «Aventura».' },
  ...cambios,
});

// El que se vino contigo, recién encontrado: espera su nombre.
const POLLITO = {
  id: 9, nombre: 'Pollito', espera_nombre: true, se_nombro_solo: false, sugerido: 'Bruma', especie: 'pollito',
  nombre_especie: 'Pollito', emoji: '🐤', etapa: 'bebe', nombre_etapa: 'cría', nivel: 1, genero: 'hembra',
  barras: { comida: 100, animo: 100, aseo: 100 }, cara: 'feliz', desfallecido: false,
  retrato: '/monsteropolis/retrato/pollito/bebe/feliz/sin.png', esperas: {}, titulo: null,
};
// Y el estado que contesta el encuentro: con él, en tu departamento y sin guía.
const CON_EL_PRIMERO = sinGachamon({ gachamon: POLLITO, lugar: CASA, guia: null });
const ENCONTRADO = { estado: CON_EL_PRIMERO, despues: DESPUES };

// Abre la pantalla con el estado de quien está en «Aventura» (o el que se le
// pase) y espera a que llegue lo que dice la aventura. `antes(servidor)`
// prepara el servidor antes de abrirla. Lo que pide pasar a otra pantalla queda
// en `seguidos`.
async function abrir({ estado = sinGachamon(), antes = (servidor) => servidor.responde('GET aventura', SE_PUEDE) } = {}) {
  pendientes.clear();
  const documento = nuevoDocumento();
  const servidor = crearServidor();
  antes(servidor);
  const contenedor = new Elemento('main');
  const seguidos = [];
  const hecho = aventura(contenedor, estado, (...argumentos) => { seguidos.push(argumentos); });
  if (hecho && typeof hecho.catch === 'function') hecho.catch(() => {});
  await asentar();
  return {
    contenedor, seguidos, servidor, documento,
  };
}

// La frase del diálogo (lo que se anuncia), el botón que avanza y «Volver».
const frase = (contenedor) => contenedor.querySelector('.aventura-frase');
const avanza = (contenedor) => contenedor.querySelector('.boton-avanzar');
const volver = (contenedor) => contenedor.querySelector('.boton-volver');
// Lo que dice el botón que avanza, si se ve.
const queDice = (contenedor) => (avanza(contenedor).seVe ? avanza(contenedor).textContent : null);
const posts = (servidor) => servidor.pedidos.filter((ruta) => ruta.startsWith('POST'));

// Toca «Seguir» hasta llegar a «Acercarte» (la tercera frase de antes).
async function hastaAcercarte(contenedor) {
  for (let vuelta = 0; vuelta < 5 && queDice(contenedor) === 'Seguir'; vuelta += 1) await avanza(contenedor).tocar();
  assert.equal(queDice(contenedor), 'Acercarte');
}

// --- las pruebas ------------------------------------------------------------------------

test('el diálogo va de a una frase y termina en «Acercarte»', { timeout: 2000 }, async () => {
  const { contenedor, servidor, seguidos } = await abrir();
  // El título, la escena del lugar y tu avatar; todavía ningún gachamon.
  const titulos = contenedor.querySelectorAll('h1');
  assert.equal(titulos.length, 1);
  assert.equal(titulos[0].textContent, 'La primera aventura');
  assert.equal(titulos[0].getAttribute('tabindex'), '-1');
  assert.ok(contenedor.querySelector('.escena-lugar'));
  assert.ok(contenedor.querySelector('.escena-fondo'));
  assert.ok(contenedor.querySelector('.monigote-lugar'));
  assert.equal(contenedor.querySelector('.aventura-gachamon'), null);
  assert.equal(contenedor.querySelector('img'), null);
  // Lo que se dice se anuncia.
  assert.equal(frase(contenedor).getAttribute('role'), 'status');
  // De a una frase, con «Seguir»; tras la tercera, «Acercarte».
  assert.equal(frase(contenedor).textContent, ANTES[0]);
  assert.equal(queDice(contenedor), 'Seguir');
  await avanza(contenedor).tocar();
  assert.equal(frase(contenedor).textContent, ANTES[1]);
  assert.equal(queDice(contenedor), 'Seguir');
  await avanza(contenedor).tocar();
  assert.equal(frase(contenedor).textContent, ANTES[2]);
  assert.equal(queDice(contenedor), 'Acercarte');
  // Hasta aquí no se guardó nada: sólo se leyó la aventura.
  assert.deepEqual(servidor.pedidos, ['GET aventura']);
  assert.deepEqual(seguidos, []);
  // Antes del encuentro se puede volver, sin mandar nada.
  assert.equal(volver(contenedor).seVe, true);
  assert.equal(volver(contenedor).textContent, 'Volver');
  // Las frases son las que manda el servidor: el cliente no las lleva escritas.
  const codigo = readFileSync(new URL('../../web/static/js/aventura.js', import.meta.url), 'utf8');
  for (const escrita of [...ANTES, ...DESPUES.slice(1), 'Sale de su escondite']) assert.ok(!codigo.includes(escrita), escrita);
});

test('acercarte manda el encuentro una sola vez', { timeout: 2000 }, async () => {
  const { contenedor, servidor } = await abrir();
  await hastaAcercarte(contenedor);
  const soltar = servidor.retiene('POST aventura/primera');
  // Un doble toque: el segundo llega con el primero en camino.
  await avanza(contenedor).tocar();
  await avanza(contenedor).tocar();
  assert.deepEqual(posts(servidor), ['POST aventura/primera']);
  // Mientras va, el botón espera (y no se apaga: sigue con el foco) y no se puede volver.
  assert.equal(avanza(contenedor).getAttribute('aria-busy'), 'true');
  assert.equal(avanza(contenedor).getAttribute('disabled'), null);
  assert.equal(volver(contenedor).getAttribute('aria-disabled'), 'true');
  await volver(contenedor).tocar();
  await soltar(ENCONTRADO);
  // Llegó: una sola petición, y el diálogo sigue con lo de después.
  assert.deepEqual(posts(servidor), ['POST aventura/primera']);
  assert.equal(avanza(contenedor).getAttribute('aria-busy'), null);
  assert.equal(frase(contenedor).textContent, DESPUES[0]);
});

test('tras el encuentro se ve al gachamon, sus tres frases y «Volver a tu departamento», que sigue con el estado recibido', { timeout: 2000 }, async () => {
  const { contenedor, servidor, seguidos } = await abrir();
  servidor.responde('POST aventura/primera', ENCONTRADO);
  await hastaAcercarte(contenedor);
  await avanza(contenedor).tocar();
  // Su retrato, en la escena, del tamaño de su etapa; lo que es lo dice la frase.
  const suyo = contenedor.querySelector('.aventura-gachamon');
  assert.ok(suyo);
  assert.equal(suyo.querySelector('img').getAttribute('src'), POLLITO.retrato);
  assert.equal(contenedor.querySelector('.escena-lugar').dataset.etapa, 'bebe');
  // Las tres frases de después, con «Seguir», y tras la última «Volver a tu departamento».
  assert.equal(frase(contenedor).textContent, DESPUES[0]);
  assert.equal(queDice(contenedor), 'Seguir');
  await avanza(contenedor).tocar();
  assert.equal(frase(contenedor).textContent, DESPUES[1]);
  assert.equal(queDice(contenedor), 'Seguir');
  await avanza(contenedor).tocar();
  assert.equal(frase(contenedor).textContent, DESPUES[2]);
  assert.equal(queDice(contenedor), 'Volver a tu departamento');
  // Ya no se vuelve al lugar: el gachamon ya es tuyo.
  assert.equal(volver(contenedor).seVe, false);
  assert.deepEqual(seguidos, []);
  await avanza(contenedor).tocar();
  // Sigue con el estado que llegó (toca el nombre), sin volver a preguntar nada.
  assert.equal(seguidos.length, 1);
  assert.equal(seguidos[0][0], CON_EL_PRIMERO);
  assert.equal(seguidos[0][1], undefined);
  assert.deepEqual(servidor.pedidos, ['GET aventura', 'POST aventura/primera']);
});

test('la frase del encuentro se dice tal como la manda el servidor, con «un» o con «una»', { timeout: 2000 }, async () => {
  // El género lo resuelve el servidor: el cliente no toca la frase.
  const OCTOPUL = {
    ...POLLITO, id: 10, nombre: 'Octopul', especie: 'pulpo', nombre_especie: 'Octopul', genero: 'macho',
  };
  for (const [gachamon, primera] of [
    [OCTOPUL, 'Sale de su escondite: es un Octopul.'],
    [{ ...OCTOPUL, genero: 'hembra' }, 'Sale de su escondite: es una Octopul.'],
  ]) {
    const { contenedor, servidor } = await abrir();
    servidor.responde('POST aventura/primera', {
      estado: sinGachamon({ gachamon, lugar: CASA, guia: null }), despues: [primera, ...DESPUES.slice(1)],
    });
    await hastaAcercarte(contenedor);
    await avanza(contenedor).tocar();
    assert.equal(frase(contenedor).textContent, primera, gachamon.genero);
  }
  // Y no lleva escrita ninguna forma de la frase ni marca de género.
  const codigo = readFileSync(new URL('../../web/static/js/aventura.js', import.meta.url), 'utf8');
  for (const escrita of ['escondite', ': es un', ': es una', '{un/una}']) assert.ok(!codigo.includes(escrita), escrita);
});

test('sin cama se dice y no se manda nada más', { timeout: 2000 }, async () => {
  // La cama dejó de estar libre entre que se abrió y el encuentro: el servidor
  // dice que no; se relee el estado y, como sigues sin ninguno, se dice su frase.
  const { contenedor, servidor, seguidos, documento } = await abrir();
  servidor.responde('POST aventura/primera', { estado: 409, clave: 'sin_cama', mensaje: SIN_CAMA });
  servidor.responde('GET estado', sinGachamon({ lugar: { ...AVENTURA, aviso: SIN_CAMA }, guia: null }));
  await hastaAcercarte(contenedor);
  await avanza(contenedor).tocar();
  assert.deepEqual(servidor.pedidos, ['GET aventura', 'POST aventura/primera', 'GET estado']);
  assert.equal(frase(contenedor).textContent, SIN_CAMA);
  // No queda «Acercarte» que volver a pulsar: sólo volver al lugar, con el foco.
  assert.equal(avanza(contenedor).seVe, false);
  assert.equal(volver(contenedor).seVe, true);
  assert.equal(volver(contenedor).getAttribute('aria-disabled'), null);
  assert.equal(documento.activeElement, volver(contenedor));
  assert.deepEqual(seguidos, []);
  await avanza(contenedor).tocar();                                    // aunque le llegue un toque, no manda nada
  assert.deepEqual(posts(servidor), ['POST aventura/primera']);
  await volver(contenedor).tocar();
  assert.deepEqual(seguidos, [[undefined]]);                           // al lugar, preguntando todo otra vez
  assert.deepEqual(posts(servidor), ['POST aventura/primera']);

  // Si al llegar ya no hay cama libre, ni se empieza: se vuelve al lugar, que lo avisa.
  const sinLaCama = await abrir({
    antes: (servidor) => servidor.responde('GET aventura', { primera: { puede: false, motivo: 'sin_cama', antes: ANTES } }),
  });
  assert.deepEqual(sinLaCama.servidor.pedidos, ['GET aventura']);
  assert.deepEqual(sinLaCama.seguidos, [[undefined]]);
});

test('sin respuesta se puede volver a intentar', { timeout: 2000 }, async () => {
  const { contenedor, servidor, seguidos } = await abrir();
  servidor.falla('POST aventura/primera');
  await hastaAcercarte(contenedor);
  await avanza(contenedor).tocar();
  // Se dice lo de siempre; la frase y «Acercarte» se quedan, listos para otro toque.
  assert.equal(contenedor.querySelector('.aviso-tienda').textContent, 'No hubo respuesta. Revisa tu conexión.');
  assert.equal(contenedor.querySelector('.aviso-tienda').getAttribute('role'), 'status');
  assert.equal(frase(contenedor).textContent, ANTES[2]);
  assert.equal(queDice(contenedor), 'Acercarte');
  assert.equal(avanza(contenedor).getAttribute('aria-busy'), null);
  assert.equal(volver(contenedor).getAttribute('aria-disabled'), null);
  assert.deepEqual(seguidos, []);
  // Otra vez, ahora con respuesta.
  servidor.responde('POST aventura/primera', ENCONTRADO);
  await avanza(contenedor).tocar();
  assert.deepEqual(posts(servidor), ['POST aventura/primera', 'POST aventura/primera']);
  assert.equal(frase(contenedor).textContent, DESPUES[0]);
  assert.equal(contenedor.querySelector('.aviso-tienda').textContent, '');
});

test('el foco queda en el botón que avanza', { timeout: 2000 }, async () => {
  const { contenedor, servidor, documento } = await abrir();
  // En cuanto llega la primera frase, y en cada paso.
  assert.equal(documento.activeElement, avanza(contenedor));
  await avanza(contenedor).tocar();
  assert.equal(documento.activeElement, avanza(contenedor));
  await avanza(contenedor).tocar();
  assert.equal(documento.activeElement, avanza(contenedor));
  // Sin respuesta, se queda en «Acercarte»…
  servidor.falla('POST aventura/primera');
  await avanza(contenedor).tocar();
  assert.equal(documento.activeElement, avanza(contenedor));
  assert.equal(queDice(contenedor), 'Acercarte');
  // …y con ella, en el que sigue con lo de después, hasta «Volver a tu departamento».
  servidor.responde('POST aventura/primera', ENCONTRADO);
  await avanza(contenedor).tocar();
  assert.equal(documento.activeElement, avanza(contenedor));
  await avanza(contenedor).tocar();
  await avanza(contenedor).tocar();
  assert.equal(queDice(contenedor), 'Volver a tu departamento');
  assert.equal(documento.activeElement, avanza(contenedor));
});

// --- lo que el encargo no nombra y la decisión 14 pide ------------------------------------

test('un «no» del encuentro cuando ya lo tienes (doble clic, otra pestaña) relee el estado y sigue con él', { timeout: 2000 }, async () => {
  // El primero ya terminó (en otra pestaña): el encuentro te llevó a tu departamento, y
  // este llega tarde. No se enseña la frase: se sigue al nombre.
  const { contenedor, servidor, seguidos } = await abrir();
  servidor.responde('POST aventura/primera', {
    estado: 409, clave: 'no_estas_ahi', mensaje: 'Para eso tienes que estar en la aventura.',
  });
  servidor.responde('GET estado', CON_EL_PRIMERO);
  await hastaAcercarte(contenedor);
  await avanza(contenedor).tocar();
  assert.deepEqual(servidor.pedidos, ['GET aventura', 'POST aventura/primera', 'GET estado']);
  assert.equal(seguidos.length, 1);
  assert.equal(seguidos[0][0], CON_EL_PRIMERO);
  assert.notEqual(frase(contenedor).textContent, 'Para eso tienes que estar en la aventura.');
  // Lo mismo con cualquier otro «no» (ya lo tenías).
  const otra = await abrir();
  otra.servidor.responde('POST aventura/primera', {
    estado: 409, clave: 'ya_tienes', mensaje: 'Ya tienes un gachamon. La primera aventura es sólo la de partida.',
  });
  otra.servidor.responde('GET estado', CON_EL_PRIMERO);
  await hastaAcercarte(otra.contenedor);
  await avanza(otra.contenedor).tocar();
  assert.equal(otra.seguidos.length, 1);
  assert.equal(otra.seguidos[0][0], CON_EL_PRIMERO);
});

test('si la aventura no carga, lo dice y deja volver a intentarlo', { timeout: 2000 }, async () => {
  const { contenedor, servidor, seguidos, documento } = await abrir({ antes: (servidor) => servidor.falla('GET aventura') });
  assert.equal(frase(contenedor).textContent, 'No hay conexión con el juego. Revisa tu internet y vuelve a intentarlo.');
  assert.equal(queDice(contenedor), 'Volver a intentarlo');
  assert.equal(documento.activeElement, avanza(contenedor));
  servidor.responde('GET aventura', SE_PUEDE);
  await avanza(contenedor).tocar();
  assert.deepEqual(servidor.pedidos, ['GET aventura', 'GET aventura']);
  assert.equal(frase(contenedor).textContent, ANTES[0]);
  assert.equal(queDice(contenedor), 'Seguir');
  assert.deepEqual(seguidos, []);
});

// --- ronda 1 de arreglos ------------------------------------------------------------------

const leerElCodigo = (nombre) => readFileSync(new URL(`../../web/static/js/${nombre}`, import.meta.url), 'utf8');

test('la escena es la del lugar: la primera aventura la pinta con lo que exporta lugar.js, sin copiarlo', () => {
  const deLaAventura = leerElCodigo('aventura.js');
  const delLugar = leerElCodigo('lugar.js');
  // El fondo y el monigote de la escena viven en lugar.js, que los usa él mismo…
  for (const nombre of ['fondoDeLaEscena', 'monigoteDeLaEscena']) {
    assert.ok(new RegExp(`^export function ${nombre}\\(`, 'm').test(delLugar), `lugar.js no exporta ${nombre}`);
    assert.ok(delLugar.match(new RegExp(`\\b${nombre}\\(`, 'g')).length >= 2, `lugar.js no usa ${nombre}`);
    // …y la aventura los toma de ahí.
    assert.ok(deLaAventura.match(new RegExp(`\\b${nombre}\\(`, 'g')), `aventura.js no usa ${nombre}`);
  }
  const importa = deLaAventura.match(/^import \{([^}]*)\} from '\.\/lugar\.js';$/m);
  assert.ok(importa, 'aventura.js no importa nada de lugar.js');
  for (const nombre of ['fondoDeLaEscena', 'monigoteDeLaEscena']) assert.ok(importa[1].includes(nombre), nombre);
  // La aventura no lleva por su cuenta ni los altos del avatar, ni el dibujo del fondo, ni su pieza.
  for (const copia of ['ALTO_DEL_AVATAR', 'DENSIDAD_MAXIMA', 'escenas/', 'drawImage', 'matchMedia', 'ResizeObserver',
    'lienzoDelAvatar', 'faltante(']) {
    assert.ok(!deLaAventura.includes(copia), copia);
  }
});

const CARGANDO = 'Cargando la aventura…';

test('mientras llega la aventura, la tarjeta dice «Cargando la aventura…» con el aro de siempre, y deja de esperar al llegar', { timeout: 2000 }, async () => {
  let soltar;
  const { contenedor, servidor } = await abrir({ antes: (s) => { soltar = s.retiene('GET aventura'); } });
  const dialogo = contenedor.querySelector('.aventura-dialogo');
  assert.ok(frase(contenedor).classList.contains('esperando'));
  // Se lee y se anuncia, como la carga de las demás pantallas: en la zona que se
  // anuncia, y sin nada alrededor que la calle mientras tanto (`aria-busy`).
  assert.equal(frase(contenedor).textContent, CARGANDO);
  assert.equal(frase(contenedor).getAttribute('role'), 'status');
  assert.equal(dialogo.getAttribute('aria-busy'), null);
  assert.equal(avanza(contenedor).seVe, false);
  await soltar(SE_PUEDE);
  assert.ok(!frase(contenedor).classList.contains('esperando'));
  assert.equal(frase(contenedor).textContent, ANTES[0]);
  // Si no llega, deja de esperar y dice por qué (la carga se va); al volver a
  // intentarlo, espera otra vez y lo dice otra vez.
  const sinRed = await abrir({ antes: (s) => s.falla('GET aventura') });
  assert.ok(!frase(sinRed.contenedor).classList.contains('esperando'));
  assert.equal(frase(sinRed.contenedor).textContent, 'No hay conexión con el juego. Revisa tu internet y vuelve a intentarlo.');
  const otraVez = sinRed.servidor.retiene('GET aventura');
  await avanza(sinRed.contenedor).tocar();
  assert.ok(frase(sinRed.contenedor).classList.contains('esperando'));
  assert.equal(frase(sinRed.contenedor).textContent, CARGANDO);
  await otraVez(SE_PUEDE);
  assert.ok(!frase(sinRed.contenedor).classList.contains('esperando'));
  assert.equal(frase(sinRed.contenedor).textContent, ANTES[0]);
  assert.deepEqual(servidor.pedidos, ['GET aventura']);
});

test('un doble clic no se salta ninguna frase: el segundo clic no cuenta, tampoco tras el encuentro', { timeout: 2000 }, async () => {
  const { contenedor, servidor } = await abrir();
  servidor.responde('POST aventura/primera', ENCONTRADO);
  // En «Seguir»: el segundo clic de un doble clic no pasa a la frase siguiente.
  await avanza(contenedor).clicar(1);
  assert.equal(frase(contenedor).textContent, ANTES[1]);
  await avanza(contenedor).clicar(2);
  assert.equal(frase(contenedor).textContent, ANTES[1]);
  await avanza(contenedor).clicar(1);
  assert.equal(queDice(contenedor), 'Acercarte');
  // En «Acercarte»: la respuesta llega antes que el segundo clic, que ya caería en «Seguir»; no cuenta,
  // y la frase que dice quién es se lee.
  await avanza(contenedor).clicar(1);
  assert.equal(frase(contenedor).textContent, DESPUES[0]);
  await avanza(contenedor).clicar(2);
  assert.equal(frase(contenedor).textContent, DESPUES[0]);
  assert.deepEqual(posts(servidor), ['POST aventura/primera']);
  // Un clic suelto y el teclado (que no cuenta clics), como siempre.
  await avanza(contenedor).clicar(1);
  assert.equal(frase(contenedor).textContent, DESPUES[1]);
  await avanza(contenedor).clicar(0);
  assert.equal(frase(contenedor).textContent, DESPUES[2]);
});

test('si al releer tras un «no» el servidor también dice que no (409) o no hay sesión (401), se vuelve a decidir', { timeout: 2000 }, async () => {
  for (const [codigo, clave] of [[409, 'cuenta_cambio'], [401, 'sin_sesion']]) {
    const { contenedor, servidor, seguidos } = await abrir();
    servidor.responde('POST aventura/primera', {
      estado: 409, clave: 'no_estas_ahi', mensaje: 'Para eso tienes que estar en la aventura.',
    });
    servidor.responde('GET estado', { estado: codigo, clave, mensaje: 'Eso no.' });
    await hastaAcercarte(contenedor);
    await avanza(contenedor).tocar();
    assert.deepEqual(servidor.pedidos, ['GET aventura', 'POST aventura/primera', 'GET estado'], clave);
    assert.deepEqual(seguidos, [[undefined]], clave);
    assert.equal(contenedor.querySelector('.aviso-tienda').textContent, '', clave);
  }
});
