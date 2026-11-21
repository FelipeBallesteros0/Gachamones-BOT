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
    { clave: 'efectos', nombre: 'Efectos', familia: 'efectos', total: 2, hechas: 1, piezas: [CORAZON, ESTRELLA] },
    {
      clave: 'pieza/paredes-y-suelo', nombre: 'Paredes y suelo', familia: 'pieza', total: 1, hechas: 1, piezas: [SUELO],
    },
    { clave: 'pieza/muebles/maceta', nombre: 'Maceta', familia: 'pieza', total: 1, hechas: 0, piezas: [MACETA] },
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
  assert.deepEqual(textos(raiz, 'summary'),
    ['Efectos · 1 de 2', 'Paredes y suelo · 1 de 1', 'Maceta · 0 de 1']);
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
  assert.deepEqual(gruposVistos(), ['Efectos · 1 de 2', 'Maceta · 0 de 1']);

  // Lo que se sube con el filtro puesto no desaparece de las manos de quien lo subió.
  servidor.responde('POST subir?ruta=efectos%2Fcorazon.png',
    { ...CORAZON, subida: { direccion: SUBIDA('d'), quien: 'ana', cuando: CUANDO } });
  await elegir(tarjeta(raiz, 'efectos/corazon.png'), { nombre: 'x.png' });
  assert.deepEqual(vistas(), ['efectos/corazon.png', 'pieza/muebles/maceta-se.png']);

  filtro.checked = false;
  filtro.dispatch('change');
  assert.equal(vistas().length, 4);
  assert.deepEqual(gruposVistos(), ['Efectos · 2 de 2', 'Paredes y suelo · 1 de 1', 'Maceta · 0 de 1']);
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

// --- las criaturas ----------------------------------------------------------------------

const ORIENTACION = {
  se: 'se · de frente, hacia abajo a la derecha',
  so: 'so · de frente, hacia abajo a la izquierda',
  no: 'no · de espaldas, hacia arriba a la izquierda',
  ne: 'ne · de espaldas, hacia arriba a la derecha',
};

// Una capa de criatura como la cuenta el servidor.
function capa(ruta, criatura, resto = {}) {
  return {
    ruta, ancho: 1024, alto: 1024, subida: null, medida_cambiada: null, objeto: null, estado: null,
    miniatura: `/monsteropolis_dibujante/api/provisional?ruta=${ruta}&miniatura=1`,
    criatura: {
      nivel: 'forma', etapa: null, capa: 'cuerpo', cual: null, nombre_del_sombrero: null, orientacion: 'se', ...criatura,
    },
    cubierta: null,
    ...resto,
  };
}
const HECHA = (letra) => ({ direccion: SUBIDA(letra), original: SUBIDA(letra), quien: 'ana', cuando: CUANDO });

const CUERPO_BEBE = ['se', 'so', 'no', 'ne'].map((o) => capa(`criaturas/pulpo/bebe/cuerpo-${o}.png`,
  { etapa: 'bebe', orientacion: o }));
const CARA_BEBE = ['se', 'so'].map((o) => capa(`criaturas/pulpo/bebe/cara-feliz-${o}.png`,
  { etapa: 'bebe', capa: 'cara', cual: 'feliz', orientacion: o },
  o === 'se' ? { cubierta: { por: 'especie', direccion: SUBIDA('k') } } : {}));
const GORRO_BEBE = capa('criaturas/pulpo/bebe/sombrero-gorro-se.png',
  { etapa: 'bebe', capa: 'sombrero', cual: 'gorro', nombre_del_sombrero: 'Gorro', orientacion: 'se' });
const CUERPO_NINO = capa('criaturas/pulpo/nino/cuerpo-se.png', { etapa: 'nino' });
const CARA_ESPECIE = capa('criaturas/pulpo/cara-feliz-se.png',
  { nivel: 'especie', capa: 'cara', cual: 'feliz' }, { subida: HECHA('m') });
const CARA_COMUN = capa('criaturas/comun/cara-feliz-se.png', { nivel: 'comun', capa: 'cara', cual: 'feliz' });

const PULPO = [...CUERPO_BEBE, ...CARA_BEBE, GORRO_BEBE, CUERPO_NINO, CARA_ESPECIE];
const GRUPO_PULPO = { clave: 'criaturas/pulpo', nombre: 'Octopul', familia: 'criaturas', total: 10, hechas: 1 };
const GRUPO_DRAGON = { clave: 'criaturas/dragoncito', nombre: 'Dragoncito', familia: 'criaturas', total: 10, hechas: 10 };
const GRUPO_COMUN = {
  clave: 'criaturas/comun', nombre: 'Capas comunes a todas las especies', familia: 'criaturas', total: 1, hechas: 0,
};
const CON_CRIATURAS = {
  grupos: [...PIEZAS.grupos, GRUPO_PULPO, GRUPO_DRAGON, GRUPO_COMUN],
};

async function abrirConCriaturas() {
  const { raiz, servidor } = await abrir(CON_CRIATURAS);
  servidor.responde('GET piezas?grupo=criaturas%2Fpulpo', { grupos: [{ ...GRUPO_PULPO, piezas: PULPO }] });
  servidor.responde('GET piezas?grupo=criaturas%2Fcomun', { grupos: [{ ...GRUPO_COMUN, piezas: [CARA_COMUN] }] });
  return { raiz, servidor };
}

const grupoDe = (raiz, resumen) => raiz.querySelectorAll('details')
  .find((d) => d.querySelector('summary').textContent === resumen);
const abrirDetalle = async (detalle) => {
  detalle.setAttribute('open', '');
  detalle.dispatch('toggle');
  await esperar();
  await esperar();
};
const hijoDetalle = (detalle, titulo) => detalle.querySelectorAll('details')
  .find((d) => d.querySelector('summary').textContent === titulo);
const hayCriaturas = (raiz) => raiz.querySelectorAll('img').filter((i) => i.getAttribute('alt').startsWith('criaturas/'));

async function especieAbierta() {
  const hecho = await abrirConCriaturas();
  const pulpo = grupoDe(hecho.raiz, 'Octopul · 1 de 10');
  await abrirDetalle(pulpo);
  return { ...hecho, pulpo };
}

test('cada grupo dice cuántas tiene hechas', { timeout: 2000 }, async () => {
  const { raiz } = await abrirConCriaturas();
  assert.deepEqual(textos(raiz, 'summary'), [
    'Efectos · 1 de 2', 'Paredes y suelo · 1 de 1', 'Maceta · 0 de 1',
    'Octopul · 1 de 10', 'Dragoncito · 10 de 10', 'Capas comunes a todas las especies · 0 de 1',
  ]);
  assert.equal(raiz.querySelector('h2').textContent, 'Criaturas');
  // Las especies van bajo «Criaturas»; los demás grupos, arriba.
  const criaturas = raiz.querySelector('.dib-criaturas');
  assert.deepEqual(textos(criaturas, 'summary'),
    ['Octopul · 1 de 10', 'Dragoncito · 10 de 10', 'Capas comunes a todas las especies · 0 de 1']);
});

test('una especie no se pide ni se arma hasta abrirla', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrirConCriaturas();
  assert.deepEqual(servidor.pedidos.map((p) => p.ruta), ['GET piezas']);
  assert.equal(hayCriaturas(raiz).length, 0);
  assert.equal(raiz.querySelectorAll('.dib-pieza').filter((t) => t.textContent.includes('criaturas/')).length, 0);
});

test('al abrir una especie se pide una sola vez', { timeout: 2000 }, async () => {
  const { raiz, servidor, pulpo } = await especieAbierta();
  assert.deepEqual(servidor.pedidos.map((p) => p.ruta), ['GET piezas', 'GET piezas?grupo=criaturas%2Fpulpo']);
  pulpo.removeAttribute('open');
  pulpo.dispatch('toggle');
  await abrirDetalle(pulpo);
  assert.equal(servidor.pedidos.filter((p) => p.ruta.startsWith('GET piezas?grupo=')).length, 1);
  // Las demás siguen sin pedirse.
  assert.equal(grupoDe(raiz, 'Dragoncito · 10 de 10').querySelectorAll('.dib-pieza').length, 0);
});

test('mientras pide una especie dice «Cargando las capas…»', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrirConCriaturas();
  const soltar = servidor.retiene('GET piezas?grupo=criaturas%2Fpulpo');
  const pulpo = grupoDe(raiz, 'Octopul · 1 de 10');
  pulpo.setAttribute('open', '');
  pulpo.dispatch('toggle');
  await esperar();
  assert.deepEqual(textos(pulpo, '[role="status"]'), ['Cargando las capas…']);
  soltar();
  await esperar();
  await esperar();
  assert.deepEqual(textos(pulpo, '[role="status"]').filter((t) => t === 'Cargando las capas…'), []);
});

test('las secciones de una etapa se arman al abrirlas', { timeout: 2000 }, async () => {
  const { pulpo } = await especieAbierta();
  // Una por etapa que tiene capas, y la de toda la especie; todas cerradas y sin tarjetas.
  assert.deepEqual(pulpo.querySelectorAll('details').map((d) => d.querySelector('summary').textContent),
    ['Cría', 'Niño', 'Para todas las etapas de Octopul']);
  assert.equal(pulpo.querySelectorAll('.dib-pieza').length, 0);
  assert.equal(pulpo.querySelectorAll('img').length, 0);

  const cria = hijoDetalle(pulpo, 'Cría');
  await abrirDetalle(cria);
  assert.deepEqual(textos(cria, 'h3'), ['Cuerpo', 'Caras']);
  assert.deepEqual(textos(cria, 'summary'), ['Cría', 'Sombreros']);
  assert.equal(cria.querySelectorAll('.dib-pieza').length, 6);
  // Los sombreros, plegados, se arman al abrirlos; las demás etapas siguen sin armar.
  const sombreros = hijoDetalle(cria, 'Sombreros');
  assert.equal(sombreros.querySelectorAll('.dib-pieza').length, 0);
  await abrirDetalle(sombreros);
  assert.equal(sombreros.querySelectorAll('.dib-pieza').length, 1);
  assert.equal(hijoDetalle(pulpo, 'Niño').querySelectorAll('.dib-pieza').length, 0);

  const titulos = (nodo) => nodo.querySelectorAll('.dib-titulo').map((t) => t.textContent);
  assert.deepEqual(titulos(sombreros), [`Gorro · ${ORIENTACION.se}`]);
  assert.deepEqual(titulos(cria).slice(0, 4), CUERPO_BEBE.map((c) => `Cuerpo · ${ORIENTACION[c.criatura.orientacion]}`));
  assert.deepEqual(titulos(cria).slice(4),
    [`Cara feliz · ${ORIENTACION.se}`, `Cara feliz · ${ORIENTACION.so}`, `Gorro · ${ORIENTACION.se}`]);
});

test('una capa de espaldas no ofrece cara', { timeout: 2000 }, async () => {
  const { pulpo } = await especieAbierta();
  const cria = hijoDetalle(pulpo, 'Cría');
  await abrirDetalle(cria);
  const caras = cria.querySelectorAll('.dib-pieza').filter((t) => t.querySelector('.dib-titulo').textContent.startsWith('Cara'));
  assert.equal(caras.length, 2);
  for (const t of caras) assert.ok(!/cara-.*-(no|ne)\.png/.test(t.querySelector('img').getAttribute('alt')));
  const cuerpos = cria.querySelectorAll('.dib-pieza').filter((t) => t.querySelector('.dib-titulo').textContent.startsWith('Cuerpo'));
  assert.equal(cuerpos.length, 4);
});

test('una casilla cubierta lo dice y enseña la que la cubre', { timeout: 2000 }, async () => {
  const { pulpo } = await especieAbierta();
  const cria = hijoDetalle(pulpo, 'Cría');
  await abrirDetalle(cria);
  const cubierta = tarjeta(cria, 'criaturas/pulpo/bebe/cara-feliz-se.png');
  assert.equal(cubierta.querySelector('img').getAttribute('src'), SUBIDA('k'));
  assert.equal(cubierta.querySelector('.dib-cubierta').textContent, 'Usa la de toda la especie.');
  assert.equal(cubierta.querySelector('.dib-cubierta').hidden, false);
  const sola = tarjeta(cria, 'criaturas/pulpo/bebe/cara-feliz-so.png');
  assert.equal(sola.querySelector('.dib-cubierta').hidden, true);
  // Sin capa subida ni cubierta, el provisional chico que manda el servidor.
  assert.equal(sola.querySelector('img').getAttribute('src'), CARA_BEBE[1].miniatura);
});

test('lo común dice «Usa la común.» y una capa subida enseña la suya', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrirConCriaturas();
  const otra = capa('criaturas/pulpo/nino/cara-feliz-se.png', { etapa: 'nino', capa: 'cara', cual: 'feliz' },
    { cubierta: { por: 'comun', direccion: SUBIDA('n') } });
  servidor.responde('GET piezas?grupo=criaturas%2Fpulpo', { grupos: [{ ...GRUPO_PULPO, piezas: [otra, CARA_ESPECIE] }] });
  const pulpo = grupoDe(raiz, 'Octopul · 1 de 10');
  await abrirDetalle(pulpo);
  const nino = hijoDetalle(pulpo, 'Niño');
  await abrirDetalle(nino);
  assert.equal(nino.querySelector('.dib-cubierta').textContent, 'Usa la común.');
  assert.equal(nino.querySelector('img').getAttribute('src'), SUBIDA('n'));
  // La capa de la especie, ya subida, se ve con su imagen.
  const especie = hijoDetalle(pulpo, 'Para todas las etapas de Octopul');
  await abrirDetalle(especie);
  assert.equal(especie.querySelector('img').getAttribute('src'), SUBIDA('m'));
});

test('las capas no se pintan como cuadros', { timeout: 2000 }, async () => {
  const { raiz, pulpo } = await especieAbierta();
  const cria = hijoDetalle(pulpo, 'Cría');
  await abrirDetalle(cria);
  for (const imagen of cria.querySelectorAll('.dib-imagen')) assert.equal(imagen.classList.contains('dib-cuadros'), false);
  assert.equal(tarjeta(raiz, 'pieza/suelo.png').querySelector('img').classList.contains('dib-cuadros'), false);
  assert.equal(tarjeta(raiz, 'efectos/corazon.png').querySelector('img').classList.contains('dib-cuadros'), true);
});

test('el encendido, el mayordomo y el balcón llevan su nota', { timeout: 2000 }, async () => {
  const lugar = (ruta, objeto, estado) => ({
    ruta, ancho: 1024, alto: 1536, subida: null, medida_cambiada: null, objeto, estado,
    miniatura: '/x', criatura: null, cubierta: null,
  });
  const piezas = [
    lugar('pieza/muebles/lampara-encendido-se.png', 'lampara', 'encendido'),
    lugar('pieza/muebles/puerta_cristal-atravesable-se.png', 'puerta_cristal', 'atravesable'),
    lugar('pieza/muebles/mayordomo-se.png', 'mayordomo', null),
    lugar('pieza/muebles/balcon-se.png', 'balcon', null),
    lugar('pieza/muebles/lampara-se.png', 'lampara', null),
  ];
  const { raiz } = await abrir({ grupos: [{ clave: 'pieza/muebles/x', nombre: 'X', familia: 'pieza', total: 5, hechas: 0, piezas }] });
  const notas = (ruta) => textos(tarjeta(raiz, ruta), '.dib-nota');
  assert.deepEqual(notas(piezas[0].ruta), ['El dibujo de siempre es el apagado; éste es el encendido.']);
  assert.deepEqual(notas(piezas[1].ruta), ['La de siempre es la sólida; ésta es la que se puede atravesar.']);
  assert.deepEqual(notas(piezas[2].ruta), ['Alto como tu avatar: unos 717 px del original, de pie en el centro de la casilla.']);
  assert.deepEqual(notas(piezas[3].ruta), ['La tira de 4 × 1 casillas que queda por fuera de la pared, con su baranda. '
    + 'Como lo de pared: «se» va en la pared izquierda y «so», en la derecha.']);
  assert.deepEqual(notas(piezas[4].ruta), []);
});

test('las criaturas llevan sus dos notas', { timeout: 2000 }, async () => {
  const { pulpo } = await especieAbierta();
  assert.deepEqual(textos(pulpo, '.dib-nota'), [
    'Cada capa mide 1024 × 1024 y se apila con las demás de su etapa en el mismo lienzo. De espaldas no lleva cara.',
    'El provisional es la capa de frente de hoy, ampliada: dice dónde va y de qué tamaño, no cómo se ve de lado ni de espaldas.',
  ]);
});

test('volver atrás una capa compartida pide confirmación y, si se cancela, no manda nada', { timeout: 2000 }, async () => {
  const { servidor, pulpo } = await especieAbierta();
  const especie = hijoDetalle(pulpo, 'Para todas las etapas de Octopul');
  await abrirDetalle(especie);
  const compartida = tarjeta(especie, CARA_ESPECIE.ruta);
  const preguntas = [];
  let respuesta = false;
  globalThis.confirm = (texto) => { preguntas.push(texto); return respuesta; };
  try {
    const antes = servidor.pedidos.length;
    await tocar(boton(compartida, 'Volver a la anterior'));
    await tocar(boton(compartida, 'Volver al provisional'));
    assert.deepEqual(preguntas, Array(2).fill(
      'Esta capa la usan todas las etapas de Octopul que no tienen la suya. ¿Seguir?'));
    assert.equal(servidor.pedidos.length, antes);
    assert.equal(compartida.querySelector('.dib-estado').textContent, 'Subida por ana el 20/11/2026 15:04');

    // Una de forma no pregunta nada.
    const cria = hijoDetalle(pulpo, 'Cría');
    await abrirDetalle(cria);
    servidor.responde('POST volver', CUERPO_BEBE[0]);
    await tocar(boton(tarjeta(cria, CUERPO_BEBE[0].ruta), 'Volver a la anterior'));
    assert.equal(preguntas.length, 2);

    // Al aceptar, se manda.
    respuesta = true;
    servidor.responde('POST volver', { ...CARA_ESPECIE, subida: null });
    servidor.responde('GET piezas?grupo=criaturas%2Fpulpo', {
      grupos: [{ ...GRUPO_PULPO, hechas: 0, piezas: PULPO.map((p) => (p === CARA_ESPECIE ? { ...p, subida: null } : p)) }],
    });
    await tocar(boton(compartida, 'Volver al provisional'));
    await esperar();
    assert.equal(preguntas.length, 3);
    assert.deepEqual(JSON.parse(servidor.pedidos.find((p) => p.ruta === 'POST volver' && JSON.parse(p.opciones.body).ruta === CARA_ESPECIE.ruta).opciones.body),
      { ruta: CARA_ESPECIE.ruta, a: 'provisional' });
    // Y los números de la especie quedan al día.
    assert.equal(pulpo.querySelector('summary').textContent, 'Octopul · 0 de 10');
  } finally {
    delete globalThis.confirm;
  }
});

test('una capa común pide su propia confirmación y deja al día lo cubierto de las especies abiertas', { timeout: 2000 }, async () => {
  const { raiz, servidor, pulpo } = await especieAbierta();
  const comun = grupoDe(raiz, 'Capas comunes a todas las especies · 0 de 1');
  await abrirDetalle(comun);
  const cria = hijoDetalle(pulpo, 'Cría');
  await abrirDetalle(cria);
  const sola = tarjeta(cria, 'criaturas/pulpo/bebe/cara-feliz-so.png');
  assert.equal(sola.querySelector('.dib-cubierta').hidden, true);
  const preguntas = [];
  globalThis.confirm = (texto) => { preguntas.push(texto); return true; };
  try {
    servidor.responde('POST subir?ruta=criaturas%2Fcomun%2Fcara-feliz-se.png', { ...CARA_COMUN, subida: HECHA('q') });
    await elegir(tarjeta(comun, CARA_COMUN.ruta), { nombre: 'x.png' });
    assert.deepEqual(preguntas, []);
    servidor.responde('POST volver', CARA_COMUN);
    servidor.responde('GET piezas?grupo=criaturas%2Fcomun', { grupos: [{ ...GRUPO_COMUN, piezas: [CARA_COMUN] }] });
    servidor.responde('GET piezas?grupo=criaturas%2Fpulpo', {
      grupos: [{
        ...GRUPO_PULPO,
        piezas: PULPO.map((p) => (p === CARA_BEBE[1] ? { ...p, cubierta: { por: 'comun', direccion: SUBIDA('q') } } : p)),
      }],
    });
    await tocar(boton(tarjeta(comun, CARA_COMUN.ruta), 'Volver a la anterior'));
    await esperar();
    assert.deepEqual(preguntas, ['Esta capa la usan todas las especies que no tienen la suya. ¿Seguir?']);
    // La casilla cubierta de otra sección ya armada no se queda con lo viejo.
    assert.equal(tarjeta(cria, 'criaturas/pulpo/bebe/cara-feliz-so.png').querySelector('.dib-cubierta').textContent,
      'Usa la común.');
    assert.equal(tarjeta(cria, 'criaturas/pulpo/bebe/cara-feliz-so.png').querySelector('img').getAttribute('src'), SUBIDA('q'));
  } finally {
    delete globalThis.confirm;
  }
});

test('«sólo lo que falta» esconde lo cubierto y lo compartido', { timeout: 2000 }, async () => {
  const { raiz, pulpo } = await especieAbierta();
  const cria = hijoDetalle(pulpo, 'Cría');
  await abrirDetalle(cria);
  const especie = hijoDetalle(pulpo, 'Para todas las etapas de Octopul');
  await abrirDetalle(especie);
  const filtro = raiz.querySelector('label').querySelector('input');
  filtro.checked = true;
  filtro.dispatch('change');
  const vistas = (nodo) => nodo.querySelectorAll('.dib-pieza').filter((t) => !t.hidden)
    .map((t) => t.querySelector('img').getAttribute('alt'));
  // La cubierta no falta, y la capa de toda la especie no se pide aquí.
  assert.ok(!vistas(cria).includes('criaturas/pulpo/bebe/cara-feliz-se.png'));
  assert.ok(vistas(cria).includes('criaturas/pulpo/bebe/cara-feliz-so.png'));
  assert.deepEqual(vistas(especie), []);
  assert.equal(especie.hidden, true);
  // La especie sin abrir, con todo hecho, se esconde; la que falta algo se queda.
  assert.equal(grupoDe(raiz, 'Dragoncito · 10 de 10').hidden, true);
  assert.equal(pulpo.hidden, false);
  assert.equal(grupoDe(raiz, 'Capas comunes a todas las especies · 0 de 1').hidden, false);
  filtro.checked = false;
  filtro.dispatch('change');
  assert.equal(grupoDe(raiz, 'Dragoncito · 10 de 10').hidden, false);
  assert.equal(especie.hidden, false);
});

test('cada especie ofrece sus dos descargas', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrirConCriaturas();
  const pulpo = grupoDe(raiz, 'Octopul · 1 de 10');
  const subido = enlace(pulpo, 'Descargar lo subido de Octopul');
  const provisionales = enlace(pulpo, 'Descargar los provisionales de Octopul');
  assert.equal(subido.getAttribute('href'), '/monsteropolis_dibujante/api/copia.zip?grupo=criaturas%2Fpulpo');
  assert.equal(provisionales.getAttribute('href'),
    '/monsteropolis_dibujante/api/provisionales.zip?grupo=criaturas%2Fpulpo');
  assert.ok(subido.getAttribute('download') !== null && provisionales.getAttribute('download') !== null);
  assert.deepEqual(servidor.pedidos.map((p) => p.ruta), ['GET piezas']);
  // Los de arriba no cambian.
  assert.equal(enlace(raiz.querySelector('.dib-cabeza'), 'Descargar lo subido')
    .getAttribute('href'), '/monsteropolis_dibujante/api/copia.zip');
});

test('si una especie no carga, lo dice en su sitio y al volver a abrirla la pide otra vez', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrirConCriaturas();
  const pulpo = grupoDe(raiz, 'Octopul · 1 de 10');
  servidor.falla('GET piezas?grupo=criaturas%2Fpulpo');
  await abrirDetalle(pulpo);
  const mensaje = pulpo.querySelector('[role="status"]');
  assert.equal(mensaje.textContent, 'No hay conexión con el juego. Revisa tu internet y vuelve a intentarlo.');
  assert.equal(mensaje.classList.contains('es-error'), true);
  assert.equal(pulpo.querySelectorAll('.dib-pieza').length, 0);
  // Un estado que no es 200.
  servidor.responde('GET piezas?grupo=criaturas%2Fpulpo', null, 502);
  pulpo.removeAttribute('open');
  pulpo.dispatch('toggle');
  await abrirDetalle(pulpo);
  assert.equal(pulpo.querySelector('[role="status"]').textContent, 'El juego no contestó. Vuelve a intentarlo en un momento.');
  // Y al volver a abrirla se vuelve a pedir.
  servidor.responde('GET piezas?grupo=criaturas%2Fpulpo', { grupos: [{ ...GRUPO_PULPO, piezas: PULPO }] });
  pulpo.removeAttribute('open');
  pulpo.dispatch('toggle');
  await abrirDetalle(pulpo);
  assert.equal(servidor.pedidos.filter((p) => p.ruta === 'GET piezas?grupo=criaturas%2Fpulpo').length, 3);
  assert.deepEqual(pulpo.querySelectorAll('details').map((d) => d.querySelector('summary').textContent),
    ['Cría', 'Niño', 'Para todas las etapas de Octopul']);
  assert.equal(pulpo.querySelectorAll('.es-error').length, 0);
});

test('los números del resumen siguen a lo que se sube en una pieza de arriba', { timeout: 2000 }, async () => {
  const { raiz, servidor } = await abrir();
  servidor.responde('POST subir?ruta=efectos%2Fcorazon.png',
    { ...CORAZON, subida: { direccion: SUBIDA('d'), original: SUBIDA('w'), quien: 'ana', cuando: CUANDO } });
  await elegir(tarjeta(raiz, CORAZON.ruta), { name: 'x.png' });
  assert.equal(raiz.querySelector('summary').textContent, 'Efectos · 2 de 2');
  servidor.responde('POST volver', { ...ESTRELLA, subida: null });
  await tocar(boton(tarjeta(raiz, ESTRELLA.ruta), 'Volver al provisional'));
  assert.equal(raiz.querySelector('summary').textContent, 'Efectos · 1 de 2');
});

test('las frases son las aprobadas', { timeout: 2000 }, async () => {
  assert.deepEqual(['se', 'so', 'no', 'ne'].map((o) => ORIENTACION[o]), [
    'se · de frente, hacia abajo a la derecha', 'so · de frente, hacia abajo a la izquierda',
    'no · de espaldas, hacia arriba a la izquierda', 'ne · de espaldas, hacia arriba a la derecha',
  ]);
  const nombres = { bebe: 'Cría', nino: 'Niño', adolescente: 'Adolescente', adulto: 'Adulto', adulto_grande: 'Adulto grande' };
  const todas = ['bebe', 'nino', 'adolescente', 'adulto', 'adulto_grande'].map((etapa) => capa(
    `criaturas/pulpo/${etapa}/cuerpo-se.png`, { etapa }));
  const { raiz, servidor } = await abrirConCriaturas();
  servidor.responde('GET piezas?grupo=criaturas%2Fpulpo', { grupos: [{ ...GRUPO_PULPO, piezas: todas }] });
  const otro = grupoDe(raiz, 'Octopul · 1 de 10');
  await abrirDetalle(otro);
  assert.deepEqual(otro.querySelectorAll('details').map((d) => d.querySelector('summary').textContent), Object.values(nombres));
});
