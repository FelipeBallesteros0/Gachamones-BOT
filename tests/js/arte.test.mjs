import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Lo justo de la `Image` del navegador: carga sola, salvo lo que tenga «falta»
// en la dirección o esté en `cortadas` (la red cortada un momento), que da
// error. Cuenta las que se crean y apunta cada dirección que se le pide.
const pedidas = [];
const cortadas = new Set();
let creadas = 0;
class ImagenDeMentira {
  constructor() { creadas += 1; }

  set src(url) {
    pedidas.push(url);
    this.url = url;
    const falla = url.includes('falta') || cortadas.has(url);
    queueMicrotask(() => (falla ? this.onerror?.() : this.onload?.()));
  }
}
globalThis.Image = ImagenDeMentira;

const {
  cargar, esRutaDeArte, faltante, olvidarLasQueFaltan, pintarPieza, urlDeArte,
} = await import('../../web/static/js/arte.js');

function lienzoDeMentira() {
  const hecho = [];
  const ctx = new Proxy({}, {
    get: (_, nombre) => (...args) => { hecho.push([nombre, ...args]); },
    set: (_, nombre, valor) => { hecho.push(['=' + String(nombre), valor]); return true; },
  });
  return { ctx, hecho };
}

const escrito = (hecho) => hecho.filter(([n]) => n === 'fillText').map(([, texto]) => texto);

test('la dirección de una pieza sale de la carpeta del arte, junto a la de los guiones', () => {
  const url = urlDeArte('efectos/corazon.png');
  assert.ok(url.endsWith('/arte/efectos/corazon.png'), url);
  assert.ok(!url.includes('..'), url);
  // En Node el módulo es un archivo: la dirección es la del archivo de verdad.
  assert.equal(url, new URL('../../web/static/arte/efectos/corazon.png', import.meta.url).href);
});

test('una pieza que carga trae su imagen', { timeout: 2000 }, async () => {
  const cargada = await cargar('efectos/corazon.png');
  assert.equal(cargada.ruta, 'efectos/corazon.png');
  assert.ok(cargada.imagen instanceof ImagenDeMentira);
  assert.equal(cargada.imagen.url, urlDeArte('efectos/corazon.png'));
});

test('una pieza que no carga no rechaza: trae la imagen en null', { timeout: 2000 }, async () => {
  assert.deepEqual(await cargar('efectos/falta.png'), { ruta: 'efectos/falta.png', imagen: null });
});

test('lo ya pedido no se vuelve a pedir, tampoco lo que falló', { timeout: 2000 }, async () => {
  for (const ruta of ['efectos/estrella.png', 'efectos/falta-otra.png']) {
    const primera = cargar(ruta);
    assert.equal(cargar(ruta), primera);
    await primera;
    assert.equal(cargar(ruta), primera);
    assert.equal(pedidas.filter((url) => url === urlDeArte(ruta)).length, 1, ruta);
  }
});

const vecesPedida = (ruta) => pedidas.filter((url) => url === urlDeArte(ruta)).length;

test('una pieza que no cargó se vuelve a pedir sólo cuando se olvidan las que faltan', { timeout: 2000 }, async () => {
  const ruta = 'pueblo/fondo.png';
  cortadas.add(urlDeArte(ruta));
  assert.deepEqual(await cargar(ruta), { ruta, imagen: null });
  // Mientras nadie la olvide, se recuerda que falta y no se pide otra vez.
  assert.deepEqual(await cargar(ruta), { ruta, imagen: null });
  assert.equal(vecesPedida(ruta), 1);

  // Vuelve la red: tras olvidar las que faltan, se pide de nuevo y esta vez carga.
  cortadas.delete(urlDeArte(ruta));
  olvidarLasQueFaltan();
  const otraVez = await cargar(ruta);
  assert.equal(vecesPedida(ruta), 2);
  assert.equal(otraVez.ruta, ruta);
  assert.ok(otraVez.imagen instanceof ImagenDeMentira);
});

test('olvidar las que faltan no toca las que cargaron ni las que están en camino', { timeout: 2000 }, async () => {
  const cargo = 'escenas/plaza.png';
  const primera = cargar(cargo);
  assert.ok((await primera).imagen instanceof ImagenDeMentira);
  olvidarLasQueFaltan();
  assert.equal(cargar(cargo), primera);
  assert.equal(vecesPedida(cargo), 1);

  const enCamino = 'escenas/barrio.png';
  const pedida = cargar(enCamino);
  olvidarLasQueFaltan();
  assert.equal(cargar(enCamino), pedida);
  await pedida;
  assert.equal(vecesPedida(enCamino), 1);
});

test('si ni siquiera se puede crear la imagen, tampoco rechaza', { timeout: 2000 }, async () => {
  globalThis.Image = class { constructor() { throw new Error('sin imágenes'); } };
  try {
    assert.deepEqual(await cargar('efectos/marca.png'), { ruta: 'efectos/marca.png', imagen: null });
  } finally {
    globalThis.Image = ImagenDeMentira;
  }
});

test('pintarPieza dibuja la imagen en su caja', () => {
  const imagen = new ImagenDeMentira();
  const { ctx, hecho } = lienzoDeMentira();
  pintarPieza(ctx, { ruta: 'efectos/corazon.png', imagen }, 10, 20, 32, 32);
  assert.deepEqual(hecho.filter(([n]) => n === 'drawImage'), [['drawImage', imagen, 10, 20, 32, 32]]);
  assert.deepEqual(escrito(hecho), []);
});

test('pintarPieza sin imagen escribe el nombre del archivo, y no dibuja otra cosa', () => {
  const { ctx, hecho } = lienzoDeMentira();
  pintarPieza(ctx, { ruta: 'pueblo/lugares/plaza.png', imagen: null }, 0, 0, 160, 160);
  assert.equal(hecho.filter(([n]) => n === 'drawImage').length, 0);
  assert.equal(escrito(hecho).join(''), 'pueblo/lugares/plaza.png');
  assert.ok(escrito(hecho).includes('plaza.png'));
});

test('el recuadro es rayado, cabe en su caja y deja el lienzo como estaba', () => {
  const { ctx, hecho } = lienzoDeMentira();
  faltante(ctx, 5, 7, 48, 84, 'avatar/pelo/rizado-castano-paso2.png');
  // La ruta entera, partida en líneas: el nombre del archivo queda en una.
  assert.deepEqual(escrito(hecho), ['avatar/', 'pelo/', 'rizado-castano-paso2.png']);
  for (const [, , x, y, maximo] of hecho.filter(([n]) => n === 'fillText')) {
    assert.ok(x >= 5 && x <= 53 && y >= 7 && y <= 91, `${x}, ${y}`);
    assert.ok(maximo > 0 && maximo <= 48, String(maximo));
  }
  // Rayas: líneas que se cruzan en diagonal dentro de la caja, y nada la tapa entera.
  assert.ok(hecho.some(([n]) => n === 'clip'));
  assert.ok(hecho.filter(([n]) => n === 'lineTo').length >= 4);
  assert.ok(!hecho.some(([n, , , ancho, alto]) => n === 'fillRect' && ancho >= 48 && alto >= 84));
  const cuantas = (nombre) => hecho.filter(([n]) => n === nombre).length;
  assert.equal(cuantas('save'), cuantas('restore'));
});

test('si la ruta cabe en una línea, no se parte', () => {
  const { ctx, hecho } = lienzoDeMentira();
  faltante(ctx, 0, 0, 1380, 860, 'pueblo/fondo.png');
  assert.deepEqual(escrito(hecho), ['pueblo/fondo.png']);
});

// --- sólo se piden rutas con forma de pieza del contrato -------------------------

// Lo que no es una pieza: salirse de la carpeta, otra raíz, otra dirección,
// consultas, fragmentos, codificaciones, vacío o algo que no es un texto.
const RARAS = [
  '../../x.png', 'avatar/../../x.png', '\\x.png', '/x.png', 'https://x/y.png', 'a?b.png',
  'a%2e%2e/b.png', 'efectos/corazon.png#x', 'efectos//corazon.png', 'efectos/corazon.PNG',
  'avatar/cuerpo/-quieto.png', 'avatar/pelo/--quieto.png', '', 42, null, undefined,
  // No es un texto, aunque al pasarlo a texto lo parezca.
  ['efectos/corazon.png'],
];

test('una ruta rara no arma ninguna dirección', () => {
  for (const ruta of RARAS) {
    assert.equal(esRutaDeArte(ruta), false, String(ruta));
    assert.equal(urlDeArte(ruta), null, String(ruta));
  }
});

test('una ruta rara se ve como pieza que falta sin pedir nada ni quedar guardada', { timeout: 2000 }, async () => {
  const antes = { creadas, pedidas: pedidas.length };
  for (const ruta of RARAS) {
    const primera = cargar(ruta);
    assert.deepEqual(await primera, { ruta, imagen: null }, String(ruta));
    // No se guarda: otra llamada es otra promesa, no la memoria de lo ya pedido.
    assert.notEqual(cargar(ruta), primera, String(ruta));
  }
  assert.deepEqual({ creadas, pedidas: pedidas.length }, antes);
});

test('todas las piezas del contrato pasan el filtro', () => {
  const contrato = JSON.parse(readFileSync(new URL('../../web/static/datos/arte.json', import.meta.url), 'utf8'));
  assert.equal(contrato.piezas.length, 199);
  for (const { ruta } of contrato.piezas) {
    assert.ok(esRutaDeArte(ruta), ruta);
    assert.ok(urlDeArte(ruta).endsWith(`/web/static/arte/${ruta}`), ruta);
  }
});
