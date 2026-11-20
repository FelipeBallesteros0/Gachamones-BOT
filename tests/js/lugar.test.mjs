import test from 'node:test';
import assert from 'node:assert/strict';

// Lo justo de un navegador para pintar la pantalla de un lugar sin pantalla y
// tocar sus botones: elementos con sus hijos (y quién los contiene), su texto,
// atributos, clases y oyentes, que se buscan con selectores sencillos
// (etiqueta, `.clase`, `[atributo]`); lienzos que aceptan todo lo que se les
// pida pintar; imágenes que cargan solas; y un reloj que no corre solo (lo que
// se programa se apunta y no se hace: el globo, las cuentas de cada segundo).
class Nodo {
  constructor() { this.padre = null; }

  get parentElement() { return this.padre; }
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

  hasChildNodes() { return this.hijos.length > 0; }

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

  // Un contexto que acepta todo lo que se le pida pintar.
  getContext() {
    return new Proxy({}, { get: () => () => {}, set: () => true });
  }

  // Un toque: lo oyen sus oyentes de `click`, que pueden ser asíncronos.
  async tocar() {
    for (const oyente of [...(this.oyentes.click || [])]) await oyente({ type: 'click' });
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

// Lo que corre con el tiempo se apunta y no corre: lo de `setTimeout` como
// `'reloj'` y lo de `setInterval` como `'intervalo'`, con sus milisegundos.
let marcas = 0;
const pendientes = new Map();
const apuntar = (tipo) => (hacer, ms = 0) => {
  marcas += 1;
  pendientes.set(marcas, { tipo, hacer, ms });
  return marcas;
};
const olvidar = (marca) => { pendientes.delete(marca); };
globalThis.setTimeout = apuntar('reloj');
globalThis.clearTimeout = olvidar;
globalThis.setInterval = apuntar('intervalo');
globalThis.clearInterval = olvidar;
// Los milisegundos de lo que hay programado con `setTimeout`.
const relojes = () => [...pendientes.values()].filter(({ tipo }) => tipo === 'reloj').map(({ ms }) => ms);

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

// Un documento nuevo para cada pantalla: así los oyentes de una prueba no oyen la siguiente.
function nuevoDocumento() {
  const oyentes = {};
  const documento = {
    hidden: false,
    activeElement: null,
    body: new Elemento('body'),
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
const { lugar, monigoteDeLaEscena } = await import('../../web/static/js/lugar.js');

// Un servidor de mentira para `pedir`: apunta cada petición como `[ruta, cuerpo]`
// («GET estado») y contesta lo que se le haya dicho para esa ruta.
function crearServidor() {
  const pedidos = [];
  const respuestas = new Map();
  globalThis.fetch = async (url, opciones) => {
    const ruta = `${opciones.method} ${String(url).replace(/^\/monsteropolis\/api\//, '')}`;
    pedidos.push([ruta, opciones.body ? JSON.parse(opciones.body) : undefined]);
    if (!respuestas.has(ruta)) {
      return {
        ok: false, status: 404, headers: { get: () => null },
        json: async () => ({ detail: { clave: 'no_existe', mensaje: 'Eso no existe.' } }),
      };
    }
    const cuerpo = respuestas.get(ruta);
    return { ok: true, status: 200, headers: { get: () => null }, json: async () => cuerpo };
  };
  return { pedidos, responde: (ruta, cuerpo) => { respuestas.set(ruta, cuerpo); } };
}

// --- lo que manda el servidor ---------------------------------------------------------

const AVATAR = {
  nombre: 'Ana', genero: 'hembra', piel: 'clara', pelo: 'largo', color_de_pelo: 'rojo', ropa: 'camisa',
};
const ESTADIO = {
  clave: 'estadio', nombre: 'Estadio', abre: 'despues', aviso: 'Esto se abre más adelante.', ofrece: [],
};
const TIENDA = { clave: 'tienda', nombre: 'Tienda', abre: 'ya', aviso: null, ofrece: ['tienda'] };
const PELUSA = {
  id: 5, nombre: 'Pelusa', titulo: null, nombre_especie: 'Pollito', nombre_etapa: 'bebé', etapa: 'bebe',
  nivel: 3, genero: 'hembra', emoji: '🐤', retrato: '/monsteropolis/retrato/pollito/bebe/feliz/sin.png',
  barras: { comida: 80, animo: 70, aseo: 60 }, esperas: {}, desfallecido: false, espera_nombre: false,
  sugerido: null,
};
const GUIA = { clave: 'aventura', texto: 'Ya hay cama para un gachamon. Sal al pueblo y ve a «Aventura».' };

// El estado de quien no tiene ningún gachamon, parado en `lugarDondeEsta`, a
// los `segundos` de las doce.
const sinGachamon = (lugarDondeEsta, segundos = 0, cambios = {}) => ({
  ahora: `2026-11-17T12:00:${String(segundos).padStart(2, '0')}+00:00`,
  persona: { usuario: 'web:1', vinculada: false },
  avatar: AVATAR,
  saldos: { monedas: 0, gemas: 0 },
  gachamon: null,
  globos: [],
  lugar: lugarDondeEsta,
  carta: false,
  guia: GUIA,
  ...cambios,
});

// Y el de quien sale con Pelusa.
const conPelusa = (lugarDondeEsta, segundos = 0, cambios = {}) => sinGachamon(lugarDondeEsta, segundos, {
  saldos: { monedas: 40, gemas: 5 },
  gachamon: PELUSA,
  globos: [{ tipo: 'suelta', texto: 'Pío.' }],
  guia: null,
  ...cambios,
});

// Abre la pantalla con ese estado (con `llegando`, como si se acabara de
// llegar caminando). Lo que pide pasar a otra pantalla queda en `seguidos`; lo
// que programaron las pantallas de antes se olvida.
async function abrir(estado, llegando = false) {
  pendientes.clear();
  const documento = nuevoDocumento();
  const servidor = crearServidor();
  const contenedor = new Elemento('main');
  const seguidos = [];
  assert.doesNotThrow(() => lugar(contenedor, estado, (...argumentos) => { seguidos.push(argumentos); }, llegando));
  await asentar();
  return {
    contenedor, seguidos, servidor, documento,
  };
}

const visibles = (nodo) => nodo.querySelectorAll('button').filter((b) => !b.hidden).map((b) => b.textContent);
const conEtiqueta = (nodo, trozo) => [nodo, ...nodo.querySelectorAll('[aria-label]')]
  .filter((n) => String(n.getAttribute('aria-label') || '').includes(trozo));

// --- sin gachamon ------------------------------------------------------------------------

test('sin gachamon, el lugar se ve con tu avatar solo, su aviso y sus salidas, sin ficha ni cuidados', { timeout: 2000 }, async () => {
  const { contenedor, seguidos, servidor } = await abrir(sinGachamon(ESTADIO));
  // Dónde estás es el título de la pantalla: ahí va el foco al llegar.
  const titulos = contenedor.querySelectorAll('h1');
  assert.equal(titulos.length, 1);
  assert.equal(titulos[0].textContent, '📍Estadio');
  assert.equal(titulos[0].getAttribute('tabindex'), '-1');
  // El aviso del lugar, en su franja.
  const franja = contenedor.querySelector('.franja-del-lugar');
  assert.equal(franja.hidden, false);
  assert.equal(franja.textContent, 'Esto se abre más adelante.');
  // La escena con tu avatar, y nada que dé por hecho un gachamon.
  assert.ok(contenedor.querySelector('.escena-lugar'));
  assert.ok(contenedor.querySelector('.monigote-lugar'));
  for (const selector of ['.gachamon', 'img', '.globo', '.celebracion', '.medallas', '.ficha', '.ficha-detalle',
    '.medidor', '.cuidados', '.cuidado', '.avisos-lugar', '.pista-lugar']) {
    assert.equal(contenedor.querySelector(selector), null, selector);
  }
  for (const frase of ['Ver ficha', 'caricia', 'acariciar', 'Acariciar']) {
    assert.ok(!contenedor.textContent.includes(frase), frase);
    assert.deepEqual(conEtiqueta(contenedor, frase), [], frase);
  }
  // Los saldos de la cabecera.
  assert.ok(contenedor.querySelector('.saldos').textContent.includes('🪙 0'));
  // Sus salidas: la mochila y el pueblo; aquí no hay tienda.
  assert.deepEqual(visibles(contenedor.querySelector('.salidas-lugar')), ['🎒Mochila', '🗺️Pueblo']);
  // En el computador se ordena sin el hueco de la ficha y los cuidados.
  assert.equal(contenedor.querySelector('.cuerpo-lugar').getAttribute('class'), 'cuerpo cuerpo-lugar sin-gachamon');
  // Nada lo saca de aquí ni se pidió nada.
  assert.deepEqual(seguidos, []);
  assert.deepEqual(servidor.pedidos, []);
  // Y se sale al pueblo como siempre.
  const [alPueblo] = contenedor.querySelectorAll('.boton-pueblo');
  await alPueblo.tocar();
  assert.equal(seguidos.length, 1);
  assert.deepEqual(seguidos[0][1], { vista: 'pueblo' });
});

test('sin gachamon, en la Tienda se puede entrar a comprar', { timeout: 2000 }, async () => {
  const { contenedor, seguidos } = await abrir(sinGachamon(TIENDA));
  assert.equal(contenedor.querySelector('.franja-del-lugar').hidden, true);
  assert.deepEqual(visibles(contenedor.querySelector('.salidas-lugar')), ['🛒Comprar', '🎒Mochila', '🗺️Pueblo']);
  await contenedor.querySelector('.boton-comprar').tocar();
  assert.equal(seguidos.length, 1);
  assert.equal(seguidos[0][0].gachamon, null);
  assert.deepEqual(seguidos[0][1], { vista: 'tienda' });
});

test('sin gachamon, lo que se relee se pinta, y si llega uno se vuelve a decidir', { timeout: 2000 }, async () => {
  const { contenedor, seguidos, servidor, documento } = await abrir(sinGachamon(ESTADIO));
  servidor.responde('GET estado', sinGachamon(ESTADIO, 30, { saldos: { monedas: 7, gemas: 0 } }));
  await documento.dispara('visibilitychange');
  assert.deepEqual(servidor.pedidos.map(([ruta]) => ruta), ['GET estado']);
  assert.ok(contenedor.querySelector('.saldos').textContent.includes('🪙 7'));
  assert.deepEqual(seguidos, []);
  // Ya tiene uno (lo trajo de la aventura en otra pestaña): esta pantalla ya no es la suya.
  const conUno = conPelusa(ESTADIO, 45);
  servidor.responde('GET estado', conUno);
  await documento.dispara('visibilitychange');
  assert.deepEqual(seguidos, [[conUno]]);
});

const INCUBADORA = { clave: 'incubadora', nombre: 'Incubadora', abre: 'ya', aviso: null, ofrece: ['incubadora'] };

test('ningún lugar tiene el botón «Tu plantel»: con quién sales se elige en tu departamento', { timeout: 2000 }, async () => {
  // Ni la Tienda, ni un lugar que todavía ofreciera la incubadora (lo que
  // mandaba el servidor de antes), con gachamon o sin él.
  for (const estado of [conPelusa(TIENDA), conPelusa(INCUBADORA), sinGachamon(INCUBADORA)]) {
    const { contenedor, seguidos } = await abrir(estado);
    assert.equal(contenedor.querySelector('.boton-plantel'), null, estado.lugar.clave);
    assert.ok(!contenedor.textContent.includes('Tu plantel'), estado.lugar.clave);
    assert.deepEqual(seguidos, []);
  }
  const enLaTienda = await abrir(conPelusa(TIENDA));
  assert.deepEqual(visibles(enLaTienda.contenedor.querySelector('.salidas-lugar')), ['🛒Comprar', '🎒Mochila', '🗺️Pueblo']);
  const enLaIncubadora = await abrir(conPelusa(INCUBADORA));
  assert.deepEqual(visibles(enLaIncubadora.contenedor.querySelector('.salidas-lugar')), ['🎒Mochila', '🗺️Pueblo']);
});

test('sin gachamon no se programa ningún globo; con gachamon, el primero', { timeout: 2000 }, async () => {
  for (const llegando of [false, true]) {
    await abrir(sinGachamon(ESTADIO), llegando);
    assert.deepEqual(relojes(), [], `llegando: ${llegando}`);
  }
  await abrir(conPelusa(ESTADIO));
  assert.deepEqual(relojes(), [2500]);
  await abrir(conPelusa(ESTADIO), true);
  assert.deepEqual(relojes(), [600]);
});

test('sin gachamon y sin aviso no queda hueco bajo la escena', { timeout: 2000 }, async () => {
  // En la Tienda no hay aviso: bajo la escena no queda nada que se vea.
  const enLaTienda = await abrir(sinGachamon(TIENDA));
  assert.equal(enLaTienda.contenedor.querySelector('.bajo-la-ficha').hidden, true);
  // Con aviso, se ve.
  const enElEstadio = await abrir(sinGachamon(ESTADIO));
  assert.equal(enElEstadio.contenedor.querySelector('.bajo-la-ficha').hidden, false);
  // Si el aviso llega o se va con una relectura, la franja sale o se esconde.
  enElEstadio.servidor.responde('GET estado', sinGachamon({ ...ESTADIO, aviso: null }, 30));
  await enElEstadio.documento.dispara('visibilitychange');
  assert.equal(enElEstadio.contenedor.querySelector('.bajo-la-ficha').hidden, true);
  // Con gachamon, la franja de abajo está siempre, como hoy (lleva lo que contesta el juego).
  const conUno = await abrir(conPelusa(TIENDA));
  assert.equal(conUno.contenedor.querySelector('.bajo-la-ficha').hidden, false);
});

// --- «Aventura», a quien todavía no tiene ningún gachamon -----------------------------------

const SIN_CAMA = 'Antes pon tu segunda cama en tu departamento: sin cama, nadie se queda contigo.';
// «Aventura» como la ve quien no tiene gachamon: con la cama libre, sin aviso; sin ella, con el suyo.
const AVENTURA = { clave: 'aventura', nombre: 'Aventura', abre: 'despues', aviso: null, ofrece: ['aventura'] };
const AVENTURA_SIN_CAMA = { ...AVENTURA, aviso: SIN_CAMA };

test('en «Aventura», con la cama libre, se sale a la primera aventura como a comprar en la Tienda', { timeout: 2000 }, async () => {
  const { contenedor, seguidos } = await abrir(sinGachamon(AVENTURA));
  assert.deepEqual(visibles(contenedor.querySelector('.salidas-lugar')), ['🧭La primera aventura', '🎒Mochila', '🗺️Pueblo']);
  await contenedor.querySelector('.boton-aventura').tocar();
  assert.equal(seguidos.length, 1);
  assert.equal(seguidos[0][0].lugar, AVENTURA);
  assert.deepEqual(seguidos[0][1], { vista: 'aventura' });
});

test('en «Aventura», sin la cama, el lugar dice su aviso y no hay a qué salir', { timeout: 2000 }, async () => {
  const { contenedor, servidor, documento, seguidos } = await abrir(sinGachamon(AVENTURA_SIN_CAMA, 0, {
    guia: { clave: 'cama', texto: 'Pon tu segunda cama: entra a «Construir», tócala en los guardados y después toca una casilla.' },
  }));
  assert.equal(contenedor.querySelector('.franja-del-lugar').textContent, SIN_CAMA);
  assert.deepEqual(visibles(contenedor.querySelector('.salidas-lugar')), ['🎒Mochila', '🗺️Pueblo']);
  // La pusiste en otra pestaña: con la relectura, el aviso se va y se puede salir.
  servidor.responde('GET estado', sinGachamon(AVENTURA, 30));
  await documento.dispara('visibilitychange');
  assert.equal(contenedor.querySelector('.franja-del-lugar').hidden, true);
  assert.deepEqual(visibles(contenedor.querySelector('.salidas-lugar')), ['🧭La primera aventura', '🎒Mochila', '🗺️Pueblo']);
  assert.deepEqual(seguidos, []);
  // Con gachamon, «Aventura» es un lugar cerrado más: no ofrece nada.
  const conUno = await abrir(conPelusa({ ...AVENTURA, aviso: 'Esto se abre más adelante.', ofrece: [] }));
  assert.deepEqual(visibles(conUno.contenedor.querySelector('.salidas-lugar')), ['🎒Mochila', '🗺️Pueblo']);
});

// --- con gachamon, como siempre -------------------------------------------------------------

test('con gachamon, el lugar trae su ficha, sus cuidados y su globo, como siempre', { timeout: 2000 }, async () => {
  const { contenedor, seguidos, servidor } = await abrir(conPelusa(ESTADIO));
  // El nombre del gachamon es el título; el lugar va en la cabecera.
  const titulos = contenedor.querySelectorAll('h1');
  assert.equal(titulos.length, 1);
  assert.equal(titulos[0].textContent, 'Pelusa');
  assert.equal(contenedor.querySelector('.donde').etiqueta, 'span');
  assert.equal(contenedor.querySelector('.donde').textContent, '📍Estadio');
  // Su ficha: el detalle, las tres barras y «Ver ficha».
  const ficha = contenedor.querySelector('.ficha');
  assert.ok(ficha);
  assert.equal(ficha.querySelector('.ficha-detalle').textContent, 'Pollito bebé · nivel 3');
  assert.deepEqual(ficha.querySelectorAll('.medidor-cifra').map((c) => c.textContent), ['80', '70', '60']);
  assert.deepEqual(visibles(ficha), ['Ver ficha']);
  // En la escena, tu avatar y él, que se acaricia tocándolo; y su globo.
  assert.ok(contenedor.querySelector('.monigote-lugar'));
  const elGachamon = contenedor.querySelector('.gachamon');
  assert.equal(elGachamon.getAttribute('aria-label'), 'Acariciar a Pelusa');
  assert.equal(elGachamon.querySelector('img').getAttribute('src'), PELUSA.retrato);
  assert.ok(contenedor.querySelector('.globo'));
  // El aviso del lugar, y bajo él la pista de la caricia.
  assert.equal(contenedor.querySelector('.franja-del-lugar').textContent, 'Esto se abre más adelante.');
  assert.equal(contenedor.querySelector('.pista-lugar').textContent, 'Toca a Pelusa para acariciarla.');
  // Los cuatro cuidados.
  const cuidados = contenedor.querySelectorAll('.cuidado');
  assert.deepEqual(cuidados.map((c) => c.querySelector('.cuidado-nombre').textContent),
    ['Alimentar', 'Jugar', 'Entrenar', 'Bañar']);
  assert.deepEqual(visibles(contenedor.querySelector('.salidas-lugar')), ['🎒Mochila', '🗺️Pueblo']);
  assert.equal(contenedor.querySelector('.cuerpo-lugar').getAttribute('class'), 'cuerpo cuerpo-lugar');
  // Un cuidado le llega al servidor con su evento, y se dice lo que contesta.
  servidor.responde('POST cuidar', {
    ok: true, clave: null, mensaje: 'Pelusa come.', monedas: 2, estado: conPelusa(ESTADIO, 10),
  });
  await cuidados[0].tocar();
  const [[ruta, cuerpo]] = servidor.pedidos;
  assert.equal(ruta, 'POST cuidar');
  assert.equal(cuerpo.accion, 'alimentar');
  assert.equal(typeof cuerpo.evento_id, 'string');
  assert.equal(contenedor.querySelector('.aviso-lugar').textContent, 'Pelusa come.');
  assert.deepEqual(seguidos, []);
  // «Ver ficha» abre la suya.
  await ficha.querySelector('.boton-ver-ficha').tocar();
  assert.equal(seguidos.length, 1);
  assert.deepEqual(seguidos[0][1], { vista: 'ficha' });
});

// --- tu avatar en la escena, en el computador ---------------------------------------------

// Una escena de `alto` píxeles con el lienzo del avatar dentro, en un teléfono o
// en un computador, con un `ResizeObserver` que se puede disparar a mano.
function escenaDe(alto, { computador }) {
  const observados = [];
  const ResizeObserverDeAntes = globalThis.ResizeObserver;
  const matchMediaDeAntes = window.matchMedia;
  globalThis.ResizeObserver = class {
    constructor(avisar) {
      this.avisar = avisar;
      this.conectado = false;
      observados.push(this);
    }

    observe(nodo) {
      this.nodo = nodo;
      this.conectado = true;
    }

    disconnect() { this.conectado = false; }
  };
  window.matchMedia = (consulta) => ({
    matches: computador && consulta === '(min-width: 900px)', media: consulta, addEventListener() {}, removeEventListener() {},
  });
  const escena = new Elemento('div');
  escena.clientHeight = alto;
  const lienzo = new Elemento('canvas');
  escena.append(lienzo);
  const oyentes = new AbortController();
  const pintar = monigoteDeLaEscena(lienzo, () => AVATAR, oyentes.signal);
  globalThis.ResizeObserver = ResizeObserverDeAntes;
  window.matchMedia = matchMediaDeAntes;
  return { escena, lienzo, pintar, oyentes, observados };
}

test('en el computador, tu avatar crece con la escena desde que ésta pasa de 560 px; en el teléfono, no', async () => {
  // Lo de siempre: 126 px en el teléfono y 168 en el computador, también con la escena alta en el teléfono.
  for (const [alto, computador, mide] of [[976, false, '126px'], [400, true, '168px'], [560, true, '168px']]) {
    const { lienzo, pintar } = escenaDe(alto, { computador });
    pintar();
    assert.equal(lienzo.style.height, mide, `${alto} px, ${computador ? 'computador' : 'teléfono'}`);
  }
  // Desde ahí, el 30 % del alto de la escena (293 px con una de 976; el avatar se pinta a medios pasos de
  // su dibujo, que mide 84 de alto: 84 × 3,5).
  const { lienzo, pintar } = escenaDe(976, { computador: true });
  pintar();
  assert.equal(lienzo.style.height, '294px');
  await asentar();
});

test('tu avatar se vuelve a pintar cuando la escena cambia de alto, y deja de mirarla al salir', async () => {
  const {
    escena, lienzo, pintar, oyentes, observados,
  } = escenaDe(976, { computador: true });
  pintar();
  const [observador] = observados;
  assert.equal(observador.nodo, escena);
  assert.equal(observador.conectado, true);
  // La ventana crece: la escena mide 1336 y el avatar, el 30 % (401 px, que se pintan a medios pasos
  // de su dibujo: 84 × 5).
  escena.clientHeight = 1336;
  observador.avisar();
  assert.equal(lienzo.style.height, '420px');
  // Al salir de la pantalla ya no mira la escena.
  oyentes.abort();
  assert.equal(observador.conectado, false);
  await asentar();
});

// --- lo transparente del retrato no se acaricia -------------------------------------------

// Desde ahora, los lienzos que cree ese documento leen sus píxeles como si lo
// que se les pinta tuviera, en cada punto `(u, v)` de su dibujo, el alfa
// `alfa(u, v)`; lo demás que se les pida, lo aceptan sin más.
function conPixeles(documento, alfa) {
  const crear = documento.createElement;
  documento.createElement = (etiqueta) => {
    const nodo = crear(etiqueta);
    if (etiqueta !== 'canvas') return nodo;
    const contexto = new Proxy({}, {
      get: (_, nombre) => {
        if (nombre !== 'getImageData') return () => {};
        return (x0, y0, ancho, alto) => {
          const data = new Uint8ClampedArray(ancho * alto * 4);
          for (let v = 0; v < alto; v += 1) for (let u = 0; u < ancho; u += 1) data[(v * ancho + u) * 4 + 3] = alfa(u, v);
          return { width: ancho, height: alto, data };
        };
      },
      set: () => true,
    });
    nodo.getContext = () => contexto;
    return nodo;
  };
}

// El retrato de la escena, puesto como lo pondría el navegador: su dibujo mide
// 48 × 84 y la mitad de arriba es transparente; su caja mide 200 × 200 y está
// en (100, 50) de la página, pero lo que la mueve (respirar) la estira un 2 %
// a lo ancho y la encoge un 3 % a lo alto, con los pies quietos. El CSS encaja
// el dibujo en su caja sin deformarlo, centrado y apoyado abajo: se ve de
// x = 141,7 a x = 258,3 y de y = 56 a y = 250.
function ponerElRetrato(contenedor, documento) {
  conPixeles(documento, (u, v) => (v < 42 ? 0 : 255));
  const retrato = contenedor.querySelector('.retrato');
  Object.assign(retrato, {
    naturalWidth: 48, naturalHeight: 84, offsetWidth: 200, offsetHeight: 200, complete: true,
  });
  retrato.getBoundingClientRect = () => ({
    left: 98, top: 56, width: 204, height: 194, right: 302, bottom: 250, x: 98, y: 56,
  });
  return retrato;
}

// Un clic de puntero en ese punto de la página: lo cuenta el navegador con `detail` 1.
async function clicDePuntero(nodo, x, y) {
  for (const oyente of [...(nodo.oyentes.click || [])]) await oyente({ type: 'click', detail: 1, clientX: x, clientY: y });
  await asentar();
}

// Uno de teclado (Intro o espacio): sin punto y con `detail` 0.
async function clicDeTeclado(nodo) {
  for (const oyente of [...(nodo.oyentes.click || [])]) await oyente({ type: 'click', detail: 0, clientX: 0, clientY: 0 });
  await asentar();
}

const caricias = (servidor) => servidor.pedidos.filter(([ruta]) => ruta === 'POST acariciar').length;

test('un clic de puntero en lo transparente del retrato no acaricia; en lo que se ve, sí; y uno de teclado, también', { timeout: 2000 }, async () => {
  const { contenedor, servidor, documento } = await abrir(conPelusa(ESTADIO));
  ponerElRetrato(contenedor, documento);
  servidor.responde('POST acariciar', { ok: true, mensaje: null, espera: 60, estado: conPelusa(ESTADIO, 10) });
  const boton = contenedor.querySelector('.gachamon');
  await clicDePuntero(boton, 120, 200);                                 // al lado del dibujo, dentro del botón
  await clicDePuntero(boton, 296, 240);
  await clicDePuntero(boton, 200, 80);                                  // entre las orejas: la mitad de arriba
  assert.equal(caricias(servidor), 0);
  await clicDePuntero(boton, 200, 220);                                 // su cuerpo
  assert.equal(caricias(servidor), 1);
  await clicDePuntero(boton, 143, 249);                                 // la esquina de abajo de su dibujo
  assert.equal(caricias(servidor), 2);
  await clicDeTeclado(boton);
  assert.equal(caricias(servidor), 3);
  // Su nombre accesible no cambia.
  assert.equal(boton.getAttribute('aria-label'), 'Acariciar a Pelusa');
});

test('si el retrato no cargó (se ve su emoji), un clic de puntero en cualquier parte del botón acaricia, como siempre', { timeout: 2000 }, async () => {
  const { contenedor, servidor, documento } = await abrir(conPelusa(ESTADIO));
  const retrato = ponerElRetrato(contenedor, documento);
  servidor.responde('POST acariciar', { ok: true, mensaje: null, espera: 60, estado: conPelusa(ESTADIO, 10) });
  for (const oyente of [...(retrato.oyentes.error || [])]) oyente({ type: 'error' });
  Object.assign(retrato, { naturalWidth: 0, naturalHeight: 0 });
  assert.equal(retrato.hidden, true);
  await clicDePuntero(contenedor.querySelector('.gachamon'), 120, 70);
  assert.equal(caricias(servidor), 1);
});

// --- el retrato apretado y el retrato ancho -----------------------------------------------

// El retrato de 48 × 84, con la mitad de arriba transparente, en su caja de
// 200 × 200 en (100, 50) de la página, sin respirar: el dibujo se ve de
// x = 142,9 a x = 257,1, y su mitad de abajo empieza en y = 150.
function ponerElRetratoQuieto(contenedor, documento) {
  const retrato = ponerElRetrato(contenedor, documento);
  retrato.getBoundingClientRect = () => ({
    left: 100, top: 50, width: 200, height: 200, right: 300, bottom: 250, x: 100, y: 50,
  });
  return retrato;
}

// Mientras dura `hacer`, los estilos calculados del navegador: el retrato
// tiene la escala `escala` y los demás, ninguna.
async function conEscala(retrato, escala, hacer) {
  const deAntes = window.getComputedStyle;
  window.getComputedStyle = (nodo) => ({ scale: nodo === retrato ? escala : 'none' });
  try {
    await hacer();
  } finally {
    window.getComputedStyle = deAntes;
  }
}

test('en el teléfono el clic llega con el retrato apretado (encogido un 3 %): se mide sobre el dibujo sin apretar', { timeout: 2000 }, async () => {
  const { contenedor, servidor, documento } = await abrir(conPelusa(ESTADIO));
  const retrato = ponerElRetratoQuieto(contenedor, documento);
  servidor.responde('POST acariciar', { ok: true, mensaje: null, espera: 60, estado: conPelusa(ESTADIO, 10) });
  const boton = contenedor.querySelector('.gachamon');
  // Apretado, con los pies y el centro quietos, su caja mide 194 × 194 en (103, 56).
  retrato.getBoundingClientRect = () => ({
    left: 103, top: 56, width: 194, height: 194, right: 297, bottom: 250, x: 103, y: 56,
  });
  await conEscala(retrato, '0.97', async () => {
    await clicDePuntero(boton, 143.5, 200);                            // el borde izquierdo de su dibujo
    await clicDePuntero(boton, 200, 151);                              // el borde de arriba de lo que se ve
    assert.equal(caricias(servidor), 2);
    await clicDePuntero(boton, 141, 200);                              // justo al lado
    await clicDePuntero(boton, 200, 148);                              // justo encima: transparente
    assert.equal(caricias(servidor), 2);
  });
  // Sin apretar (con el ratón, el clic llega ya suelto), la caja es la que se mide.
  ponerElRetratoQuieto(contenedor, documento);
  await conEscala(retrato, 'none', async () => {
    await clicDePuntero(boton, 143.5, 200);
    await clicDePuntero(boton, 141, 200);
    assert.equal(caricias(servidor), 3);
  });
});

test('un retrato más ancho que alto va apoyado abajo: el hueco de arriba de su caja no acaricia', { timeout: 2000 }, async () => {
  const { contenedor, servidor, documento } = await abrir(conPelusa(ESTADIO));
  servidor.responde('POST acariciar', { ok: true, mensaje: null, espera: 60, estado: conPelusa(ESTADIO, 10) });
  conPixeles(documento, () => 255);                                     // todo su dibujo se ve
  // De 84 × 48, en su caja de 200 × 200 en (100, 50): ocupa todo el ancho y
  // 114,3 de alto, de y = 135,7 a y = 250.
  const retrato = contenedor.querySelector('.retrato');
  Object.assign(retrato, {
    naturalWidth: 84, naturalHeight: 48, offsetWidth: 200, offsetHeight: 200, complete: true,
  });
  retrato.getBoundingClientRect = () => ({
    left: 100, top: 50, width: 200, height: 200, right: 300, bottom: 250, x: 100, y: 50,
  });
  const boton = contenedor.querySelector('.gachamon');
  await clicDePuntero(boton, 200, 60);                                  // el hueco de arriba
  await clicDePuntero(boton, 200, 134);
  assert.equal(caricias(servidor), 0);
  await clicDePuntero(boton, 200, 137);                                 // el borde de arriba de su dibujo
  await clicDePuntero(boton, 101, 249);                                 // sus esquinas de abajo
  await clicDePuntero(boton, 299, 249);
  assert.equal(caricias(servidor), 3);
});
