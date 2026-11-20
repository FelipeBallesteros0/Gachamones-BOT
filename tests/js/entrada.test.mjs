import test from 'node:test';
import assert from 'node:assert/strict';

// Lo justo de un navegador para armar la caja del código, la bienvenida y el
// bautizo sin pantalla: elementos que apuntan sus hijos, sus clases y sus
// oyentes, y un portapapeles que anota lo que se le manda.
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

  replaceChildren(...nodos) { this.hijos = [...nodos]; }

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

const entrada = await import('../../web/static/js/entrada.js');
const {
  avatar, bautizo, bienvenida, cajaDelCodigo, MUESTRAS,
} = entrada;

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

// --- la bienvenida y el huevo, que ya no está ----------------------------------------

const NOTA_DE_EMPEZAR = 'Si empiezas de cero y un gachamon se va contigo, ya no podrás traer los de Discord.';

test('la bienvenida dice «Empezar de cero», con su casa y su nota nueva', () => {
  const contenedor = new Elemento('main');
  bienvenida(contenedor, async () => {}, {
    sesion: { usuario: 'ana' }, cuenta: { estado: 'nueva', tiene_gachamones: false },
  });
  const [empezar, traer, ...otros] = buscar(contenedor, 'button');
  assert.deepEqual(otros, []);
  assert.deepEqual(textos(empezar), ['🏠', 'Empezar de cero', 'Nunca jugué, o quiero empezar de nuevo aquí.']);
  assert.deepEqual(textos(traer), ['💬', 'Ya jugaba en Discord', 'Trae tus gachamones con un código.']);
  const notas = buscar(contenedor, 'p').filter((p) => p.atributos.class === 'nota');
  assert.deepEqual(notas.map((p) => textos(p).join('')), [NOTA_DE_EMPEZAR]);
  // Ni el huevo ni la nota de antes.
  const todo = textos(contenedor).join(' ');
  assert.ok(!todo.includes('🥚'), todo);
  assert.ok(!todo.includes('nace tu gachamon'), todo);
});

test('la pantalla del avatar dice cómo te verán en el pueblo, sin dar por hecho un gachamon', { timeout: 2000 }, async () => {
  // Las opciones no llegan (sin sesión): lo de arriba ya está pintado y se vuelve a decidir.
  globalThis.fetch = async () => ({
    ok: false, status: 401, headers: { get: () => null },
    json: async () => ({ detail: { clave: 'sin_sesion', mensaje: 'Entra a Rowino para jugar.' } }),
  });
  const contenedor = new Elemento('main');
  const seguidos = [];
  await avatar(contenedor, async (...argumentos) => { seguidos.push(argumentos); }, {
    sesion: { usuario: 'ana' }, cuenta: { estado: 'web', tiene_gachamones: false },
  });
  const entradillas = buscar(contenedor, 'p').filter((p) => p.atributos.class === 'entradilla');
  assert.deepEqual(entradillas.map((p) => textos(p).join('')), ['Así te verán en el pueblo.']);
  assert.ok(!textos(contenedor).join(' ').includes('gachamon'));
  assert.deepEqual(seguidos, [[]]);
});

test('no existe la pantalla del huevo', async () => {
  assert.ok(!Object.hasOwn(entrada, 'huevo'));
  for (const pantalla of ['sesion', 'bienvenida', 'avatar', 'bautizo', 'noCarga']) {
    assert.equal(typeof entrada[pantalla], 'function', pantalla);
  }
  // Y nada de la entrada pide romper un huevo ni lo ofrece.
  const { readFileSync } = await import('node:fs');
  const codigo = readFileSync(new URL('../../web/static/js/entrada.js', import.meta.url), 'utf8');
  assert.doesNotMatch(codigo, /pedir\(\s*'POST',\s*'huevo'/);
  for (const frase of ['Romper el huevo', 'Un huevo para ti']) assert.ok(!codigo.includes(frase), frase);
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
  genero: 'hembra', emoji: '🐙', retrato: '/monsteropolis/retrato/pulpo/bebe/feliz/sin.png',
};
// El recluta que esperaba nombre sin ninguna activa: un servidor viejo lo mandaba en `sin_nombre`.
const recluta = { id: 7, nombre_especie: 'Pollito', retrato: '/monsteropolis/retrato/pollito/bebe/feliz/sin.png' };
const ESPERA_EN_LA_INCUBADORA = 'Este Pollito espera en la incubadora y todavía no tiene nombre.';

test('el bautizo es siempre el del activo: un `sin_nombre` de un servidor viejo no lo cambia', { timeout: 2000 }, async () => {
  const despues = { avatar: {}, gachamon: { ...nacido, nombre: 'Bruma', espera_nombre: false } };
  const pedidas = servidor(() => ({ estado: 200, datos: despues }));
  const { contenedor, seguido } = await bautizarCon({ avatar: {}, gachamon: nacido, sin_nombre: recluta }, 'Bruma');
  assert.ok(!textos(contenedor).includes(ESPERA_EN_LA_INCUBADORA));
  assert.deepEqual(buscar(contenedor, 'img').map((img) => img.atributos.src), [nacido.retrato]);
  assert.equal(pedidas.length, 1);
  assert.equal(pedidas[0].metodo, 'POST');
  assert.ok(pedidas[0].url.endsWith('/bautizar'), pedidas[0].url);
  assert.deepEqual(pedidas[0].cuerpo, { nombre: 'Bruma' });
  // Lo que contesta es el estado: con él se decide la pantalla.
  assert.deepEqual(seguido, [despues]);
});

test('el bautizo del recién nacido no manda gachamon_id: es el de la activa, como siempre', { timeout: 2000 }, async () => {
  const pedidas = servidor(() => ({ estado: 200, datos: { gachamon: { ...nacido, nombre: 'Bruma' } } }));
  const { contenedor } = await bautizarCon({ avatar: {}, gachamon: nacido, sin_nombre: null }, 'Bruma');
  assert.ok(!textos(contenedor).includes(ESPERA_EN_LA_INCUBADORA));
  assert.deepEqual(pedidas[0].cuerpo, { nombre: 'Bruma' });
  assert.ok(!Object.hasOwn(pedidas[0].cuerpo, 'gachamon_id'));
});

// --- el paso del nombre del que se vino contigo de la primera aventura -------------

const ETIQUETA = '¿Cómo se va a llamar?';
const SE_PUEDE_DEJAR = 'Le puedes dejar este nombre o escribir otro.';

// Pinta el paso del nombre con ese gachamon y da el campo, su formulario y lo
// que se pasó a `seguir` cuando se mande.
function pasoDelNombre(gachamon) {
  const contenedor = new Elemento('main');
  let seguir;
  const seguido = new Promise((listo) => { seguir = async (...args) => listo(args); });
  bautizo(contenedor, seguir, { sesion: { usuario: 'ana' }, estado: { avatar: {}, gachamon } });
  const [campo] = buscar(contenedor, 'input');
  const [formulario] = buscar(contenedor, 'form');
  return { contenedor, campo, formulario, seguido };
}

test('el paso del nombre trae el sugerido escrito y dice que se puede dejar', () => {
  const { contenedor, campo, formulario } = pasoDelNombre({ ...nacido, sugerido: 'Bruma' });
  const todo = textos(contenedor);
  assert.deepEqual(buscar(contenedor, 'h1').map((h) => textos(h).join('')), ['¡Se vino contigo!']);
  assert.ok(!todo.includes('¡Nació tu gachamon!'));
  // El campo, con el sugerido ya escrito.
  assert.equal(campo.value, 'Bruma');
  assert.deepEqual(buscar(formulario, 'label').map((l) => textos(l).join('')), [ETIQUETA]);
  // Debajo del campo, la nota, que se le lee a quien está en el campo.
  const [nota] = buscar(formulario, 'p').filter((p) => textos(p).join('') === SE_PUEDE_DEJAR);
  assert.ok(nota, todo.join(' | '));
  const campoYSuNota = buscar(formulario, 'div').find((d) => d.hijos.includes(campo));
  assert.ok(campoYSuNota.hijos.indexOf(nota) > campoYSuNota.hijos.indexOf(campo));
  assert.equal(campo.atributos['aria-describedby'], nota.atributos.id);
  // El botón de siempre.
  assert.deepEqual(buscar(formulario, 'button').map((b) => textos(b).join('')), ['Ponerle este nombre']);

  // Sin nombre sugerido, el campo vacío, como antes, y sin la nota.
  const sinSugerido = pasoDelNombre({ ...nacido, sugerido: null });
  assert.ok(!sinSugerido.campo.value);
  assert.ok(!textos(sinSugerido.contenedor).includes(SE_PUEDE_DEJAR));
  assert.equal(sinSugerido.campo.atributos['aria-describedby'], undefined);
  assert.deepEqual(buscar(sinSugerido.contenedor, 'h1').map((h) => textos(h).join('')), ['¡Se vino contigo!']);
});

test('el retrato del paso del nombre se lee como «Tu nuevo gachamon», con su especie', () => {
  const { contenedor } = pasoDelNombre({ ...nacido, sugerido: 'Bruma' });
  const [retrato] = buscar(contenedor, 'img');
  assert.equal(retrato.atributos.alt, 'Tu nuevo gachamon, Pulpito');
});

test('con el sugerido tal cual, «Ponerle este nombre» lo manda', { timeout: 2000 }, async () => {
  const despues = { avatar: {}, gachamon: { ...nacido, nombre: 'Bruma', espera_nombre: false, sugerido: null } };
  const pedidas = servidor(() => ({ estado: 200, datos: despues }));
  const { formulario, seguido } = pasoDelNombre({ ...nacido, sugerido: 'Bruma' });
  formulario.oyentes.submit[0]({ preventDefault() {} });                 // sin tocar el campo
  assert.deepEqual(await seguido, [despues]);
  assert.equal(pedidas.length, 1);
  assert.ok(pedidas[0].url.endsWith('/bautizar'), pedidas[0].url);
  assert.deepEqual(pedidas[0].cuerpo, { nombre: 'Bruma' });
});

test('si ya tiene nombre o ya no hay a quién bautizar, se vuelve a decidir sin enseñar un error', { timeout: 2000 }, async () => {
  for (const [clave, mensaje] of [['ya_bautizado', 'Tu gachamon ya tiene nombre.'], ['sin_gachamon', 'No tienes ningún gachamon vivo.']]) {
    servidor(() => ({ estado: 409, datos: { detail: { clave, mensaje } } }));
    const { contenedor, seguido } = await bautizarCon({ avatar: {}, gachamon: nacido }, 'Bruma');
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
