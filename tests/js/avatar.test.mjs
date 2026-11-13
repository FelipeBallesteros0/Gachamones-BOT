import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  POSES, capasDelAvatar, poseAlCaminar, dibujarAvatar, cargarAvatar, lienzoDelAvatar,
} from '../../web/static/js/avatar.js';

const contrato = JSON.parse(readFileSync(new URL('../../web/static/datos/arte.json', import.meta.url), 'utf8'));
const rutas = new Set(contrato.piezas.map((p) => p.ruta));
const feli = { nombre: 'Feli', genero: 'macho', piel: 'media', pelo: 'corto', color_de_pelo: 'castano', ropa: 'poleron' };

test('las capas se apilan cuerpo, ropa y pelo', () => {
  assert.deepEqual(capasDelAvatar(feli, 'quieto'), [
    'avatar/cuerpo/media-quieto.png', 'avatar/ropa/poleron-quieto.png', 'avatar/pelo/corto-castano-quieto.png',
  ]);
  assert.deepEqual(capasDelAvatar({ ...feli, piel: 'oscura', pelo: 'coleta', color_de_pelo: 'azul', ropa: 'vestido' }, 'paso2'), [
    'avatar/cuerpo/oscura-paso2.png', 'avatar/ropa/vestido-paso2.png', 'avatar/pelo/coleta-azul-paso2.png',
  ]);
});

test('toda combinación del catálogo cae en una pieza del contrato', () => {
  const partes = (prefijo) => [...rutas].filter((r) => r.startsWith(prefijo)).map((r) => r.slice(prefijo.length, -4));
  const pieles = new Set(partes('avatar/cuerpo/').map((p) => p.split('-')[0]));
  const ropas = new Set(partes('avatar/ropa/').map((p) => p.split('-')[0]));
  const pelos = new Set(partes('avatar/pelo/').map((p) => p.split('-').slice(0, 2).join('-')));
  assert.equal(pieles.size * ropas.size * pelos.size, 4 * 4 * 30);
  for (const piel of pieles) for (const ropa of ropas) for (const pelo of pelos) for (const pose of POSES) {
    const [forma, color] = pelo.split('-');
    for (const ruta of capasDelAvatar({ ...feli, piel, ropa, pelo: forma, color_de_pelo: color }, pose)) {
      assert.ok(rutas.has(ruta), ruta);
    }
  }
});

test('el género no cambia el dibujo', () => {
  assert.deepEqual(capasDelAvatar({ ...feli, genero: 'hembra' }, 'quieto'), capasDelAvatar(feli, 'quieto'));
});

test('quieto no da pasos, y caminando alterna', () => {
  assert.equal(poseAlCaminar(5, false), 'quieto');
  assert.equal(poseAlCaminar(0, true), 'paso1');
  assert.equal(poseAlCaminar(0.19, true), 'paso2');
  assert.equal(poseAlCaminar(0.37, true), 'paso1');
});

function lienzoDeMentira() {
  const hecho = [];
  const ctx = new Proxy({}, {
    get: (_, nombre) => (...args) => { hecho.push([nombre, ...args]); },
    set: (_, nombre, valor) => { hecho.push(['=' + String(nombre), valor]); return true; },
  });
  return { ctx, hecho };
}

test('se dibujan las tres capas en orden, y la que falta se ve como faltante', () => {
  const capas = new Map(capasDelAvatar(feli, 'quieto').map((ruta, i) => [ruta, { ruta, imagen: i === 1 ? null : { ruta } }]));
  const { ctx, hecho } = lienzoDeMentira();
  dibujarAvatar(ctx, capas, feli, 'quieto', 100, 200, 84, false);
  const imagenes = hecho.filter(([n]) => n === 'drawImage').map(([, imagen]) => imagen.ruta);
  assert.deepEqual(imagenes, ['avatar/cuerpo/media-quieto.png', 'avatar/pelo/corto-castano-quieto.png']);
  assert.ok(hecho.some(([n, texto]) => n === 'fillText' && String(texto).includes('poleron-quieto.png')));
});

test('con espejo se da vuelta', () => {
  const capas = new Map(capasDelAvatar(feli, 'quieto').map((ruta) => [ruta, { ruta, imagen: { ruta } }]));
  const { ctx, hecho } = lienzoDeMentira();
  dibujarAvatar(ctx, capas, feli, 'quieto', 100, 200, 84, true);
  assert.ok(hecho.some(([n, sx]) => n === 'scale' && sx === -1));
});

// --- dónde cae y cómo se pinta ------------------------------------------------

const enteras = (capas) => new Map([...capas].map((ruta) => [ruta, { ruta, imagen: { ruta } }]));

test('los pies caen en (x, y), a lo alto pedido y con el ancho de 48 × 84', () => {
  const { ctx, hecho } = lienzoDeMentira();
  dibujarAvatar(ctx, enteras(capasDelAvatar(feli, 'paso1')), feli, 'paso1', 100, 200, 168, false);
  const cajas = hecho.filter(([n]) => n === 'drawImage').map(([, , ...caja]) => caja);
  // Los pies están a 4 de los 84 píxeles del borde de abajo (el contrato).
  assert.deepEqual(cajas, [[52, 40, 96, 168], [52, 40, 96, 168], [52, 40, 96, 168]]);
});

test('las capas se pintan sin suavizar, y el lienzo queda como estaba', () => {
  const { ctx, hecho } = lienzoDeMentira();
  dibujarAvatar(ctx, enteras(capasDelAvatar(feli, 'quieto')), feli, 'quieto', 100, 200, 84, true);
  const apagado = hecho.findIndex(([n, valor]) => n === '=imageSmoothingEnabled' && valor === false);
  assert.ok(apagado >= 0 && apagado < hecho.findIndex(([n]) => n === 'drawImage'));
  const cuantas = (nombre) => hecho.filter(([n]) => n === nombre).length;
  assert.equal(cuantas('save'), cuantas('restore'));
});

test('el recuadro de una capa que falta no sale al revés con el espejo', () => {
  const capas = new Map(capasDelAvatar(feli, 'quieto').map((ruta, i) => [ruta, { ruta, imagen: i === 2 ? null : { ruta } }]));
  const { ctx, hecho } = lienzoDeMentira();
  dibujarAvatar(ctx, capas, feli, 'quieto', 100, 200, 84, true);
  // El espejo dura hasta el restore que cierra el save donde se puso; ningún
  // texto se escribe mientras dura.
  let profundidad = 0;
  let volteadoEn = null;
  let alReves = false;
  for (const [n, sx] of hecho) {
    if (n === 'save') profundidad += 1;
    if (n === 'restore') {
      if (volteadoEn === profundidad) volteadoEn = null;
      profundidad -= 1;
    }
    if (n === 'scale' && sx === -1) volteadoEn = profundidad;
    if (n === 'fillText' && volteadoEn !== null) alReves = true;
  }
  assert.ok(hecho.some(([n, sx]) => n === 'scale' && sx === -1));
  assert.ok(hecho.some(([n]) => n === 'fillText'));
  assert.equal(alReves, false);
});

test('una capa que ni siquiera está en el mapa se ve como faltante', () => {
  const { ctx, hecho } = lienzoDeMentira();
  dibujarAvatar(ctx, new Map(), feli, 'quieto', 100, 200, 84, false);
  assert.equal(hecho.filter(([n]) => n === 'drawImage').length, 0);
  assert.ok(hecho.some(([n, texto]) => n === 'fillText' && String(texto).includes('media-quieto.png')));
});

// --- cargar: imágenes de mentira que cargan solas, salvo las que la prueba retiene --

const retenidas = new Set();
const esperando = [];
class ImagenDeMentira {
  set src(url) {
    this.url = url;
    if ([...retenidas].some((fragmento) => url.includes(fragmento))) esperando.push(this);
    else queueMicrotask(() => this.onload());
  }
}
globalThis.Image = ImagenDeMentira;
globalThis.window = { devicePixelRatio: 3 };

function soltar(fragmento) {
  retenidas.delete(fragmento);
  for (const imagen of esperando.filter((i) => i.url.includes(fragmento))) {
    esperando.splice(esperando.indexOf(imagen), 1);
    imagen.onload();
  }
}

const unRato = () => new Promise((listo) => { setImmediate(listo); });

test('cargarAvatar trae las nueve capas, tres por pose', { timeout: 2000 }, async () => {
  const capas = await cargarAvatar(feli);
  const esperadas = POSES.flatMap((pose) => capasDelAvatar(feli, pose));
  assert.equal(esperadas.length, 9);
  assert.deepEqual([...capas.keys()].sort(), [...esperadas].sort());
  for (const [ruta, cargada] of capas) {
    assert.equal(cargada.ruta, ruta);
    assert.ok(cargada.imagen.url.endsWith(`/arte/${ruta}`), cargada.imagen.url);
  }
});

function lienzoDePrueba() {
  const { ctx, hecho } = lienzoDeMentira();
  return { lienzo: { width: 300, height: 150, style: {}, getContext: () => ctx }, hecho };
}

const pintadas = (hecho) => hecho.filter(([n]) => n === 'drawImage').map(([, imagen]) => imagen.url.split('/arte/')[1]);

// [densidad, alto pedido] → [ancho, alto] del lienzo en píxeles del teléfono y
// en píxeles de pantalla. Cada dos píxeles del dibujo, un número entero del
// teléfono: el mismo tamaño que el monigote de antes en cualquier pantalla.
const MEDIDAS = [
  [3, 168, [288, 504, '96px', '168px']],
  [3, 126, [216, 378, '72px', '126px']],
  [2, 126, [144, 252, '72px', '126px']],
  [1, 126, [72, 126, '72px', '126px']],
  [1.25, 168, [120, 210, '96px', '168px']],
  [2.625, 126, [192, 336, `${192 / 2.625}px`, '128px']],
];

test('el lienzo mide lo mismo que antes, y las capas lo llenan entero', { timeout: 2000 }, async () => {
  try {
    for (const [densidad, alto, esperado] of MEDIDAS) {
      globalThis.window.devicePixelRatio = densidad;
      const { lienzo, hecho } = lienzoDePrueba();
      await lienzoDelAvatar(lienzo, feli, alto);
      assert.deepEqual([lienzo.width, lienzo.height, lienzo.style.width, lienzo.style.height], esperado, `${densidad}, ${alto}`);
      const caja = [0, 0, esperado[0], esperado[1]];
      assert.deepEqual(hecho.filter(([n]) => n === 'drawImage').map(([, , ...resto]) => resto), [caja, caja, caja]);
      assert.deepEqual(pintadas(hecho), capasDelAvatar(feli, 'quieto'));
    }
  } finally {
    globalThis.window.devicePixelRatio = 3;
  }
});

test('mientras cargan se queda lo anterior, y gana la última elección', { timeout: 2000 }, async () => {
  const { lienzo, hecho } = lienzoDePrueba();
  await lienzoDelAvatar(lienzo, feli, 168);
  const antes = hecho.length;

  const primera = { ...feli, piel: 'clara', ropa: 'overol', pelo: 'rizado', color_de_pelo: 'rubio' };
  const ultima = { ...feli, piel: 'tostada', ropa: 'camisa', pelo: 'largo', color_de_pelo: 'rojo' };
  retenidas.add('clara-quieto').add('overol-quieto').add('rizado-rubio-quieto');
  retenidas.add('tostada-quieto').add('camisa-quieto').add('largo-rojo-quieto');
  const pintandoPrimera = lienzoDelAvatar(lienzo, primera, 168);
  const pintandoUltima = lienzoDelAvatar(lienzo, ultima, 168);

  // Nada llegó: el lienzo no se toca, sigue lo de antes.
  soltar('clara-quieto');
  soltar('tostada-quieto');
  soltar('camisa-quieto');
  await unRato();
  assert.equal(hecho.length, antes);
  assert.equal(lienzo.width, 288);

  // Llega la última entera: se cambia de una vez, las tres capas juntas.
  soltar('largo-rojo-quieto');
  await pintandoUltima;
  assert.deepEqual(pintadas(hecho.slice(antes)), capasDelAvatar(ultima, 'quieto'));
  assert.ok(hecho.slice(antes).some(([n]) => n === 'clearRect'));

  // La primera llega tarde y no pisa a la última.
  const despues = hecho.length;
  soltar('overol-quieto');
  soltar('rizado-rubio-quieto');
  await pintandoPrimera;
  assert.equal(hecho.length, despues);
});
