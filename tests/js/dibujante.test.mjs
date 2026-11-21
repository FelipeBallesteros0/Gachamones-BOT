import test from 'node:test';
import assert from 'node:assert/strict';

// Las fechas, en una zona fija: así «el {fecha}» sale igual en cualquier máquina.
process.env.TZ = 'UTC';

// Lo justo de un navegador para montar la página del dibujante sin pantalla y
// tocar sus botones: elementos con sus hijos, su texto, atributos (`hidden` es el
// atributo), clases y oyentes, que se buscan por etiqueta, por `.clase`, por
// `[atributo]` o por `[atributo=valor]`.
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

class Elemento extends Nodo {
  constructor(etiqueta) {
    super();
    this.etiqueta = etiqueta;
    this.atributos = {};
    this.oyentes = {};
    this.hijos = [];
    this.style = {};
    this.checked = false;
    this.files = null;
    this.value = '';
    this.abiertoElSelector = 0;
    const clases = () => String(this.atributos.class || '').split(/\s+/).filter(Boolean);
    this.classList = {
      add: (...nombres) => { this.atributos.class = [...new Set([...clases(), ...nombres])].join(' '); },
      remove: (...nombres) => { this.atributos.class = clases().filter((c) => !nombres.includes(c)).join(' '); },
      contains: (nombre) => clases().includes(nombre),
      toggle: (nombre, poner) => {
        const sí = poner === undefined ? !clases().includes(nombre) : poner;
        if (sí) this.classList.add(nombre);
        else this.classList.remove(nombre);
        return sí;
      },
    };
  }

  get hidden() { return Object.hasOwn(this.atributos, 'hidden'); }

  set hidden(valor) {
    if (valor) this.atributos.hidden = '';
    else delete this.atributos.hidden;
  }

  setAttribute(nombre, valor) { this.atributos[nombre] = String(valor); }

  getAttribute(nombre) { return Object.hasOwn(this.atributos, nombre) ? this.atributos[nombre] : null; }

  removeAttribute(nombre) { delete this.atributos[nombre]; }

  addEventListener(tipo, oyente) { (this.oyentes[tipo] ||= []).push(oyente); }

  dispatch(tipo) {
    for (const oyente of this.oyentes[tipo] || []) oyente({ type: tipo, target: this });
  }

  // Un `<input type="file">` abre el selector de archivos; el resto, su clic.
  click() {
    if (this.etiqueta === 'input' && this.atributos.type === 'file') this.abiertoElSelector += 1;
    else this.dispatch('click');
  }

  get textContent() { return this.hijos.map((h) => h.textContent).join(''); }

  set textContent(texto) { this.replaceChildren(...(texto === '' ? [] : [new Texto(String(texto))])); }

  append(...nodos) {
    for (const nodo of nodos) nodo.padre = this;
    this.hijos.push(...nodos);
  }

  replaceChildren(...nodos) {
    this.hijos = [];
    this.append(...nodos);
  }

  cumple(selector) {
    if (selector.startsWith('.')) return this.classList.contains(selector.slice(1));
    const atributo = /^\[([^=\]]+)(?:="([^"]*)")?\]$/.exec(selector);
    if (atributo) {
      const [, nombre, valor] = atributo;
      return Object.hasOwn(this.atributos, nombre) && (valor === undefined || this.atributos[nombre] === valor);
    }
    return this.etiqueta === selector;
  }

  querySelectorAll(selector) {
    return this.hijos.filter((h) => h instanceof Elemento)
      .flatMap((h) => [...(h.cumple(selector) ? [h] : []), ...h.querySelectorAll(selector)]);
  }

  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }

  focus() {}
}

globalThis.Node = Nodo;
globalThis.document = {
  createElement: (etiqueta) => new Elemento(etiqueta),
  createTextNode: (texto) => new Texto(texto),
};

const {
  avisoDeMedida, estadoDe, fecha, medidaDe, montar, renglonDelHistorial,
} = await import('../../web/static/js/dibujante.js');
const { urlDeArte } = await import('../../web/static/js/arte.js');

// --- las frases ---------------------------------------------------------------------

const SUBIDA = (letra) => `/monsteropolis/arte-subido/${letra.repeat(64)}.png`;
const CUANDO = '2026-11-20T15:04:00+00:00';

test('la medida es una sola, la exacta, también en la familia de la pieza', () => {
  assert.equal(medidaDe({ ancho: 32, alto: 32 }), '32 × 32 px');
  assert.equal(medidaDe({ ancho: 512, alto: 256 }), '512 × 256 px');
});

test('una pieza es provisional o dice quién la subió y cuándo', () => {
  assert.equal(estadoDe({ subida: null }), 'Provisional');
  assert.equal(estadoDe({ subida: { direccion: SUBIDA('a'), quien: 'ana', cuando: CUANDO } }),
    'Subida por ana el 20/11/2026 15:04');
  assert.equal(fecha('2026-01-02T03:04:05+00:00'), '02/01/2026 03:04');
});

test('el aviso de otra medida nombra las dos medidas', () => {
  assert.equal(avisoDeMedida({ ancho: 1024, alto: 1536, medida_cambiada: null }), null);
  assert.equal(avisoDeMedida({ ancho: 1024, alto: 1536, medida_cambiada: { ancho: 512, alto: 768 } }),
    'Lo subido mide 512 × 768 px y este lugar pide 1024 × 1536 px: hay que volver a subirlo.');
});

test('cada renglón del historial dice qué se hizo, quién, cuándo y lo que mide', () => {
  assert.equal(renglonDelHistorial({ accion: 'subir', quien: 'ana', cuando: CUANDO, ancho: 32, alto: 32 }),
    'Subir · ana · 20/11/2026 15:04 · 32 × 32 px');
  assert.equal(renglonDelHistorial({ accion: 'anterior', quien: 'luis', cuando: CUANDO, ancho: 32, alto: 32 }),
    'Volver a la anterior · luis · 20/11/2026 15:04 · 32 × 32 px');
  assert.equal(renglonDelHistorial({ accion: 'provisional', quien: 'ana', cuando: CUANDO, ancho: null, alto: null }),
    'Volver al provisional · ana · 20/11/2026 15:04');
});

// --- la página ------------------------------------------------------------------------

const CORAZON = {
  ruta: 'efectos/corazon.png', ancho: 32, alto: 32, subida: null, medida_cambiada: null,
};
const ESTRELLA = {
  ruta: 'efectos/estrella.png', ancho: 32, alto: 32,
  subida: { direccion: SUBIDA('b'), original: SUBIDA('y'), quien: 'ana', cuando: CUANDO },
  medida_cambiada: null,
};
const SUELO = {
  ruta: 'pieza/suelo.png', ancho: 1024, alto: 512,
  subida: { direccion: SUBIDA('c'), original: SUBIDA('z'), quien: 'luis', cuando: CUANDO },
  medida_cambiada: null,
};
const MACETA = {
  ruta: 'pieza/muebles/maceta-se.png', ancho: 1024, alto: 1536,
  subida: null, medida_cambiada: { ancho: 512, alto: 640 },
};
const PIEZAS = {
  grupos: [
    { clave: 'efectos', nombre: 'Efectos', familia: 'efectos', piezas: [CORAZON, ESTRELLA] },
    { clave: 'pieza/paredes-y-suelo', nombre: 'Paredes y suelo', familia: 'pieza', piezas: [SUELO] },
    { clave: 'pieza/muebles/maceta', nombre: 'Maceta', familia: 'pieza', piezas: [MACETA] },
  ],
};

// Un servidor de mentira: cada petición («POST subir?ruta=…») contesta lo que se le
// dijo con `responde` (y su estado), o falla como una red caída con `falla`.
// `retiene` deja en camino la próxima a esa ruta hasta que se suelta.
function servidorDeMentira() {
  const pedidos = [];
  const respuestas = new Map();
  const caidas = new Set();
  const retenidas = new Map();
  globalThis.fetch = async (url, opciones) => {
    assert.ok(String(url).startsWith('/monsteropolis_dibujante/api/'), url);
    const ruta = `${opciones.method} ${String(url).slice('/monsteropolis_dibujante/api/'.length)}`;
    pedidos.push({ ruta, opciones });
    if (caidas.has(ruta)) throw new Error('sin red');
    if (retenidas.has(ruta)) {
      const espera = retenidas.get(ruta);
      retenidas.delete(ruta);
      await espera;
    }
    const [estado, datos] = respuestas.get(ruta) || [404, { detail: { clave: 'no_existe', mensaje: 'Eso no existe.' } }];
    return { ok: estado < 400, status: estado, json: async () => datos };
  };
  return {
    pedidos,
    responde: (ruta, datos, estado = 200) => { respuestas.set(ruta, [estado, datos]); caidas.delete(ruta); },
    falla: (ruta) => { caidas.add(ruta); },
    retiene(ruta) {
      let soltar;
      retenidas.set(ruta, new Promise((listo) => { soltar = listo; }));
      return () => soltar();
    },
  };
}

const esperar = () => new Promise((listo) => setTimeout(listo, 0));
const textos = (raiz, selector) => raiz.querySelectorAll(selector).map((n) => n.textContent);
const tarjeta = (raiz, ruta) => raiz.querySelectorAll('.dib-pieza')
  .find((t) => t.querySelector('img').getAttribute('alt') === ruta);
const boton = (nodo, que) => nodo.querySelectorAll('button').find((b) => b.textContent === que) || null;
const aviso = (nodo) => nodo.querySelector('[role="status"]');
const tocar = async (nodo) => { nodo.click(); await esperar(); };

async function abrir(piezas = PIEZAS) {
  const servidor = servidorDeMentira();
  servidor.responde('GET piezas', piezas);
  const raiz = new Elemento('main');
  await montar(raiz);
  return { raiz, servidor };
}

// Elige un archivo en el `<input type="file">` de la tarjeta, como lo hace quien sube.
async function elegir(nodo, archivo) {
  const entrada = nodo.querySelector('[type="file"]');
  entrada.files = archivo === null ? [] : [archivo];
  entrada.value = 'C:\\fakepath\\x.png';
  entrada.dispatch('change');
  await esperar();
  return entrada;
}

test('la página tiene su título, la descarga de todo y el filtro de lo que falta', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  assert.deepEqual(servidor.pedidos.map((p) => p.ruta), ['GET piezas']);
  assert.equal(raiz.querySelector('h1').textContent, 'Arte de Criópolis');
  const descarga = raiz.querySelector('a');
  assert.equal(descarga.textContent, 'Descargar lo subido');
  assert.equal(descarga.getAttribute('href'), '/monsteropolis_dibujante/api/copia.zip');
  assert.ok(descarga.getAttribute('download') !== null);
  const filtro = raiz.querySelector('label');
  assert.equal(filtro.textContent, 'Sólo lo que falta');
  assert.equal(filtro.querySelector('input').getAttribute('type'), 'checkbox');
});

test('las piezas van por grupos, cada una con su imagen, su nombre, su medida y quién la subió', { timeout: 2000 }, async () => {
  const { raiz } = await abrir();
  assert.deepEqual(textos(raiz, 'summary'), ['Efectos', 'Paredes y suelo', 'Maceta']);
  const grupos = raiz.querySelectorAll('details');
  assert.deepEqual(grupos.map((g) => g.querySelectorAll('.dib-pieza').length), [2, 1, 1]);

  const corazon = tarjeta(raiz, 'efectos/corazon.png');
  // Lo provisional se ve con su dibujo de siempre; lo subido, por su dirección.
  assert.equal(corazon.querySelector('img').getAttribute('src'), urlDeArte('efectos/corazon.png'));
  assert.equal(tarjeta(raiz, 'efectos/estrella.png').querySelector('img').getAttribute('src'), SUBIDA('b'));
  assert.ok(corazon.textContent.includes('efectos/corazon.png'));
  assert.equal(corazon.querySelector('.dib-medida').textContent, '32 × 32 px');
  assert.equal(corazon.querySelector('.dib-estado').textContent, 'Provisional');
  assert.deepEqual(corazon.querySelectorAll('button').map((b) => b.textContent),
    ['Subir', 'Historial', 'Volver a la anterior', 'Volver al provisional']);
  const entrada = corazon.querySelector('[type="file"]');
  assert.equal(entrada.getAttribute('accept'), 'image/png');

  const suelo = tarjeta(raiz, 'pieza/suelo.png');
  assert.equal(suelo.querySelector('.dib-medida').textContent, '1024 × 512 px');
  assert.equal(suelo.querySelector('.dib-estado').textContent, 'Subida por luis el 20/11/2026 15:04');
  // Cada imagen dice de qué pieza es.
  for (const imagen of raiz.querySelectorAll('img')) assert.ok(imagen.getAttribute('alt'));
  // Lo que cambia se anuncia, y de entrada no dice nada; pero el aviso ya está en la
  // página, sin `hidden`, para que un lector de pantalla lea su primer mensaje.
  for (const t of raiz.querySelectorAll('.dib-pieza')) {
    assert.equal(aviso(t).textContent, '');
    assert.equal(aviso(t).hidden, false);
  }
});

test('lo subido con una medida vieja se ve provisional y lo dice', { timeout: 2000 }, async () => {
  const { raiz } = await abrir();
  const maceta = tarjeta(raiz, 'pieza/muebles/maceta-se.png');
  assert.equal(maceta.querySelector('.dib-estado').textContent, 'Provisional');
  assert.equal(maceta.querySelector('.dib-cambiada').textContent,
    'Lo subido mide 512 × 640 px y este lugar pide 1024 × 1536 px: hay que volver a subirlo.');
  assert.equal(maceta.querySelector('img').getAttribute('src'), urlDeArte('pieza/muebles/maceta-se.png'));
  assert.equal(tarjeta(raiz, 'efectos/corazon.png').querySelector('.dib-cambiada').hidden, true);
});

test('Subir abre el selector y manda el PNG elegido tal cual, con la cabecera del juego', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  const corazon = tarjeta(raiz, 'efectos/corazon.png');
  const subida = { ...CORAZON, subida: { direccion: SUBIDA('d'), quien: 'ana', cuando: CUANDO } };
  servidor.responde('POST subir?ruta=efectos%2Fcorazon.png', subida);
  await tocar(boton(corazon, 'Subir'));
  const entrada = corazon.querySelector('[type="file"]');
  assert.equal(entrada.abiertoElSelector, 1);

  const archivo = { nombre: 'corazon.png', es: 'un File' };
  await elegir(corazon, archivo);
  const pedido = servidor.pedidos.at(-1);
  assert.equal(pedido.ruta, 'POST subir?ruta=efectos%2Fcorazon.png');
  assert.equal(pedido.opciones.body, archivo);
  assert.deepEqual(pedido.opciones.headers, { 'Content-Type': 'image/png', 'X-Gachamon': '1' });
  assert.equal(pedido.opciones.credentials, 'same-origin');

  assert.equal(aviso(corazon).textContent, 'Listo: ya se ve en el juego.');
  assert.equal(aviso(corazon).classList.contains('es-error'), false);
  assert.equal(aviso(corazon).hidden, false);
  assert.equal(corazon.querySelector('img').getAttribute('src'), SUBIDA('d'));
  assert.equal(corazon.querySelector('.dib-estado').textContent, 'Subida por ana el 20/11/2026 15:04');
  // Se puede volver a elegir el mismo archivo.
  assert.equal(entrada.value, '');
});

test('si no se elige nada, no se manda nada', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  await elegir(tarjeta(raiz, 'efectos/corazon.png'), null);
  assert.deepEqual(servidor.pedidos.map((p) => p.ruta), ['GET piezas']);
});

test('lo que el servidor rechaza se dice con su mensaje y no cambia nada', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  const corazon = tarjeta(raiz, 'efectos/corazon.png');
  const mensaje = 'La imagen mide 31 × 31 px y esta pieza pide 32 × 32 px.';
  servidor.responde('POST subir?ruta=efectos%2Fcorazon.png', { detail: { clave: 'no_vale', mensaje } }, 400);
  await elegir(corazon, { nombre: 'mal.png' });
  assert.equal(aviso(corazon).textContent, mensaje);
  assert.equal(aviso(corazon).classList.contains('es-error'), true);
  assert.equal(corazon.querySelector('.dib-estado').textContent, 'Provisional');
  assert.equal(corazon.querySelector('img').getAttribute('src'), urlDeArte('efectos/corazon.png'));
});

test('sin red se dice como en el juego, y una respuesta que no es del juego también', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  const corazon = tarjeta(raiz, 'efectos/corazon.png');
  servidor.falla('POST subir?ruta=efectos%2Fcorazon.png');
  await elegir(corazon, { nombre: 'x.png' });
  assert.equal(aviso(corazon).textContent, 'No hay conexión con el juego. Revisa tu internet y vuelve a intentarlo.');
  servidor.responde('POST subir?ruta=efectos%2Fcorazon.png', null, 502);
  await elegir(corazon, { nombre: 'x.png' });
  assert.equal(aviso(corazon).textContent, 'El juego no contestó. Vuelve a intentarlo en un momento.');
});

test('volver a la anterior y al provisional mandan la pieza y lo que se pide', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  const estrella = tarjeta(raiz, 'efectos/estrella.png');
  const anterior = { ...ESTRELLA, subida: { direccion: SUBIDA('e'), quien: 'luis', cuando: CUANDO } };
  servidor.responde('POST volver', anterior);
  await tocar(boton(estrella, 'Volver a la anterior'));
  const pedido = servidor.pedidos.at(-1);
  assert.equal(pedido.ruta, 'POST volver');
  assert.deepEqual(JSON.parse(pedido.opciones.body), { ruta: 'efectos/estrella.png', a: 'anterior' });
  assert.deepEqual(pedido.opciones.headers, { 'Content-Type': 'application/json', 'X-Gachamon': '1' });
  assert.equal(estrella.querySelector('img').getAttribute('src'), SUBIDA('e'));
  assert.equal(estrella.querySelector('.dib-estado').textContent, 'Subida por luis el 20/11/2026 15:04');
  // Lo que quedó se anuncia.
  assert.equal(aviso(estrella).textContent, 'Subida por luis el 20/11/2026 15:04');

  servidor.responde('POST volver', { ...ESTRELLA, subida: null });
  await tocar(boton(estrella, 'Volver al provisional'));
  assert.deepEqual(JSON.parse(servidor.pedidos.at(-1).opciones.body), { ruta: 'efectos/estrella.png', a: 'provisional' });
  assert.equal(estrella.querySelector('img').getAttribute('src'), urlDeArte('efectos/estrella.png'));
  assert.equal(estrella.querySelector('.dib-estado').textContent, 'Provisional');
  assert.equal(aviso(estrella).textContent, 'Provisional');
});

test('volver a la anterior desde el provisional dice lo que dice el servidor', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  const corazon = tarjeta(raiz, 'efectos/corazon.png');
  servidor.responde('POST volver', { detail: { clave: 'no_vale', mensaje: 'No hay una imagen anterior.' } }, 400);
  await tocar(boton(corazon, 'Volver a la anterior'));
  assert.equal(aviso(corazon).textContent, 'No hay una imagen anterior.');
  assert.equal(aviso(corazon).classList.contains('es-error'), true);
});

test('mientras una pieza espera al servidor, sus otros botones no mandan nada y lo dicen', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  const estrella = tarjeta(raiz, 'efectos/estrella.png');
  servidor.responde('POST volver', { ...ESTRELLA, subida: null });
  const soltar = servidor.retiene('POST volver');
  const provisional = boton(estrella, 'Volver al provisional');
  provisional.click();
  await esperar();
  assert.equal(provisional.getAttribute('aria-busy'), 'true');
  for (const que of ['Subir', 'Volver a la anterior', 'Volver al provisional']) {
    assert.equal(boton(estrella, que).getAttribute('aria-disabled'), 'true', que);
  }
  await tocar(boton(estrella, 'Volver a la anterior'));
  await tocar(boton(estrella, 'Subir'));
  assert.equal(estrella.querySelector('[type="file"]').abiertoElSelector, 0);
  assert.equal(servidor.pedidos.filter((p) => p.ruta === 'POST volver').length, 1);
  // Las demás piezas siguen a mano.
  assert.equal(boton(tarjeta(raiz, 'efectos/corazon.png'), 'Subir').getAttribute('aria-disabled'), null);
  soltar();
  await esperar();
  await esperar();
  assert.equal(provisional.getAttribute('aria-busy'), null);
  for (const que of ['Subir', 'Volver a la anterior', 'Volver al provisional']) {
    assert.equal(boton(estrella, que).getAttribute('aria-disabled'), null, que);
  }
  // Nunca con `disabled`: el foco no se pierde.
  for (const b of estrella.querySelectorAll('button')) assert.equal(b.getAttribute('disabled'), null);
});

test('el historial se abre y se cierra, y dice todo lo que le pasó a la pieza', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  const estrella = tarjeta(raiz, 'efectos/estrella.png');
  servidor.responde('GET historial?ruta=efectos%2Festrella.png', {
    ruta: 'efectos/estrella.png',
    historial: [
      { accion: 'provisional', direccion: null, ancho: null, alto: null, quien: 'ana', cuando: CUANDO },
      { accion: 'subir', direccion: SUBIDA('b'), ancho: 32, alto: 32, quien: 'luis', cuando: CUANDO },
    ],
  });
  const historial = boton(estrella, 'Historial');
  const lista = estrella.querySelector('ol');
  assert.equal(lista.hidden, true);
  assert.equal(historial.getAttribute('aria-expanded'), 'false');
  assert.equal(historial.getAttribute('aria-controls'), lista.getAttribute('id'));

  await tocar(historial);
  assert.equal(servidor.pedidos.at(-1).ruta, 'GET historial?ruta=efectos%2Festrella.png');
  assert.equal(lista.hidden, false);
  assert.equal(historial.getAttribute('aria-expanded'), 'true');
  assert.deepEqual(textos(lista, 'li'), [
    'Volver al provisional · ana · 20/11/2026 15:04',
    'Subir · luis · 20/11/2026 15:04 · 32 × 32 px',
  ]);
  const miniaturas = lista.querySelectorAll('img');
  assert.equal(miniaturas.length, 1);
  assert.equal(miniaturas[0].getAttribute('src'), SUBIDA('b'));
  assert.equal(miniaturas[0].getAttribute('alt'), 'efectos/estrella.png');
  // El provisional, sin imagen, deja su sitio vacío: los renglones quedan alineados.
  assert.equal(lista.querySelectorAll('.dib-miniatura').length, 2);
  // Una imagen que ya no se guarda no deja el dibujo roto del navegador.
  miniaturas[0].dispatch('error');
  assert.equal(miniaturas[0].classList.contains('dib-sin-imagen'), true);

  await tocar(historial);
  assert.equal(lista.hidden, true);
  assert.equal(historial.getAttribute('aria-expanded'), 'false');
});

test('con el historial abierto, lo que cambia la pieza se ve también en él', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  const corazon = tarjeta(raiz, 'efectos/corazon.png');
  servidor.responde('GET historial?ruta=efectos%2Fcorazon.png', { ruta: 'efectos/corazon.png', historial: [] });
  await tocar(boton(corazon, 'Historial'));
  assert.deepEqual(textos(corazon.querySelector('ol'), 'li'), []);
  servidor.responde('POST subir?ruta=efectos%2Fcorazon.png',
    { ...CORAZON, subida: { direccion: SUBIDA('d'), quien: 'ana', cuando: CUANDO } });
  servidor.responde('GET historial?ruta=efectos%2Fcorazon.png', {
    ruta: 'efectos/corazon.png',
    historial: [{ accion: 'subir', direccion: SUBIDA('d'), ancho: 32, alto: 32, quien: 'ana', cuando: CUANDO }],
  });
  await elegir(corazon, { nombre: 'x.png' });
  await esperar();
  assert.deepEqual(textos(corazon.querySelector('ol'), 'li'), ['Subir · ana · 20/11/2026 15:04 · 32 × 32 px']);
});

test('si releer el historial falla tras una subida que salió bien, lo dicho sigue siendo «Listo»', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  const corazon = tarjeta(raiz, 'efectos/corazon.png');
  const historial = [{ accion: 'subir', direccion: SUBIDA('d'), ancho: 32, alto: 32, quien: 'ana', cuando: CUANDO }];
  servidor.responde('GET historial?ruta=efectos%2Fcorazon.png', { ruta: 'efectos/corazon.png', historial });
  await tocar(boton(corazon, 'Historial'));
  servidor.responde('POST subir?ruta=efectos%2Fcorazon.png',
    { ...CORAZON, subida: { direccion: SUBIDA('d'), quien: 'ana', cuando: CUANDO } });
  servidor.falla('GET historial?ruta=efectos%2Fcorazon.png');
  await elegir(corazon, { nombre: 'x.png' });
  await esperar();
  assert.equal(servidor.pedidos.at(-1).ruta, 'GET historial?ruta=efectos%2Fcorazon.png');
  assert.equal(aviso(corazon).textContent, 'Listo: ya se ve en el juego.');
  assert.equal(aviso(corazon).classList.contains('es-error'), false);
  assert.equal(corazon.querySelector('.dib-estado').textContent, 'Subida por ana el 20/11/2026 15:04');
  // Abrir el historial a mano sí dice que no llegó.
  await tocar(boton(corazon, 'Historial'));
  await tocar(boton(corazon, 'Historial'));
  assert.equal(aviso(corazon).textContent, 'No hay conexión con el juego. Revisa tu internet y vuelve a intentarlo.');
  assert.equal(aviso(corazon).classList.contains('es-error'), true);
});

test('«Sólo lo que falta» deja a la vista las piezas provisionales y sus grupos', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  const filtro = raiz.querySelector('label').querySelector('input');
  const vistas = () => raiz.querySelectorAll('.dib-pieza').filter((t) => !t.hidden)
    .map((t) => t.querySelector('img').getAttribute('alt'));
  const gruposVistos = () => raiz.querySelectorAll('details').filter((g) => !g.hidden)
    .map((g) => g.querySelector('summary').textContent);
  assert.equal(vistas().length, 4);

  filtro.checked = true;
  filtro.dispatch('change');
  // La maceta tiene puesta una de medida vieja: se ve el provisional, así que falta.
  assert.deepEqual(vistas(), ['efectos/corazon.png', 'pieza/muebles/maceta-se.png']);
  assert.deepEqual(gruposVistos(), ['Efectos', 'Maceta']);

  // Lo que se sube con el filtro puesto no desaparece de las manos de quien lo subió.
  servidor.responde('POST subir?ruta=efectos%2Fcorazon.png',
    { ...CORAZON, subida: { direccion: SUBIDA('d'), quien: 'ana', cuando: CUANDO } });
  await elegir(tarjeta(raiz, 'efectos/corazon.png'), { nombre: 'x.png' });
  assert.deepEqual(vistas(), ['efectos/corazon.png', 'pieza/muebles/maceta-se.png']);

  filtro.checked = false;
  filtro.dispatch('change');
  assert.equal(vistas().length, 4);
  assert.deepEqual(gruposVistos(), ['Efectos', 'Paredes y suelo', 'Maceta']);
  filtro.checked = true;
  filtro.dispatch('change');
  assert.deepEqual(vistas(), ['pieza/muebles/maceta-se.png']);
});

test('si las piezas no llegan, lo dice con la frase del servidor o la de sin red', { timeout: 2000 }, async () => {
  const servidor = servidorDeMentira();
  servidor.falla('GET piezas');
  const raiz = new Elemento('main');
  await montar(raiz);
  assert.equal(raiz.querySelector('h1').textContent, 'Arte de Criópolis');
  const estado = raiz.querySelector('[role="status"]');
  assert.equal(estado.textContent, 'No hay conexión con el juego. Revisa tu internet y vuelve a intentarlo.');
  assert.equal(estado.classList.contains('es-error'), true);
  assert.equal(raiz.querySelectorAll('.dib-pieza').length, 0);

  servidorDeMentira();   // sin respuesta para `GET piezas`: el 404 de quien perdió el permiso
  const otra = new Elemento('main');
  await montar(otra);
  assert.equal(otra.querySelector('[role="status"]').textContent, 'Eso no existe.');
});

// --- las descargas --------------------------------------------------------------------

const enlaces = (nodo) => nodo.querySelectorAll('a');
const enlace = (nodo, que) => enlaces(nodo).find((a) => a.textContent === que) || null;

test('cada pieza ofrece descargar su provisional, también la que tiene una imagen subida', { timeout: 2000 }, async () => {
  const { raiz } = await abrir();
  for (const pieza of [CORAZON, ESTRELLA, SUELO, MACETA]) {
    const descarga = enlace(tarjeta(raiz, pieza.ruta), 'Descargar el provisional');
    assert.ok(descarga, pieza.ruta);
    assert.equal(descarga.getAttribute('href'),
      `/monsteropolis_dibujante/api/provisional?ruta=${encodeURIComponent(pieza.ruta)}`);
    assert.ok(descarga.getAttribute('download') !== null);
    assert.ok(descarga.classList.contains('boton'));
  }
});

test('descargar la imagen subida apunta al original', { timeout: 2000 }, async () => {
  const { raiz } = await abrir();
  // Sin imagen subida el enlace no se ve ni lleva dirección.
  for (const pieza of [CORAZON, MACETA]) {
    const sin = enlace(tarjeta(raiz, pieza.ruta), 'Descargar la imagen subida');
    assert.ok(sin === null || (sin.hidden && sin.getAttribute('href') === null), pieza.ruta);
  }
  const estrella = enlace(tarjeta(raiz, ESTRELLA.ruta), 'Descargar la imagen subida');
  assert.equal(estrella.getAttribute('href'), SUBIDA('y'));
  assert.equal(estrella.getAttribute('download'), 'subida-efectos-estrella.png');
  const suelo = enlace(tarjeta(raiz, SUELO.ruta), 'Descargar la imagen subida');
  assert.equal(suelo.getAttribute('href'), SUBIDA('z'));
  assert.equal(suelo.getAttribute('download'), 'subida-pieza-suelo.png');
});

test('la descarga de lo subido sigue a la pieza al subir y al volver al provisional', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  const corazon = tarjeta(raiz, CORAZON.ruta);
  const nueva = { ...CORAZON, subida: { direccion: SUBIDA('d'), original: SUBIDA('w'), quien: 'ana', cuando: CUANDO } };
  servidor.responde('POST subir?ruta=efectos%2Fcorazon.png', nueva);
  await elegir(corazon, { name: 'x.png' });
  const subida = enlace(corazon, 'Descargar la imagen subida');
  assert.equal(subida.getAttribute('href'), SUBIDA('w'));
  assert.equal(subida.hidden, false);
  servidor.responde('POST volver', CORAZON);
  await tocar(boton(corazon, 'Volver al provisional'));
  const oculto = enlace(corazon, 'Descargar la imagen subida');
  assert.equal(oculto.hidden, true);
  assert.equal(oculto.getAttribute('href'), null);
});

test('arriba dice «Descargar lo subido»', { timeout: 2000 }, async () => {
  const { raiz } = await abrir();
  const cabeza = raiz.querySelector('.dib-cabeza');
  assert.equal(enlace(cabeza, 'Descargar lo que se ve'), null);
  const copia = enlace(cabeza, 'Descargar lo subido');
  assert.equal(copia.getAttribute('href'), '/monsteropolis_dibujante/api/copia.zip');
});

test('arriba se ofrecen los provisionales, junto a lo subido', { timeout: 2000 }, async () => {
  const { raiz } = await abrir();
  const cabeza = raiz.querySelector('.dib-cabeza');
  assert.deepEqual(enlaces(cabeza).map((a) => a.textContent),
    ['Descargar lo subido', 'Descargar los provisionales']);
  const todos = enlace(cabeza, 'Descargar los provisionales');
  assert.equal(todos.getAttribute('href'), '/monsteropolis_dibujante/api/provisionales.zip');
  assert.ok(todos.getAttribute('download') !== null);
});

test('las descargas son enlaces y no mandan nada con fetch', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  for (const a of enlaces(raiz)) assert.ok(!/^https?:/.test(a.getAttribute('href')));
  assert.deepEqual(servidor.pedidos.map((p) => p.ruta), ['GET piezas']);
});
