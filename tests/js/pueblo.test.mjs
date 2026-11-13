import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as p from '../../web/static/js/pueblo.js';

const datos = JSON.parse(readFileSync(new URL('../../web/static/datos/pueblo.json', import.meta.url), 'utf8'));
const grafo = p.armarGrafo(datos);
const lugares = Object.keys(datos.lugares);
const cerca = (a, b, margen = 0.01) => assert.ok(Math.abs(a - b) <= margen, `${a} no es ${b}`);

function caminar(paseo, segundos, paso = 0.05) {
  let llegadas = 0;
  for (let t = 0; t < segundos - 1e-9; t += paso) if (p.avanzar(paseo, paso)) llegadas += 1;
  return llegadas;
}

test('el camino más corto', () => {
  assert.deepEqual(p.ruta(grafo, 'casa', 'tienda'), { camino: ['casa', 'l1', 'u1', 'tienda'], largo: 305 });
  assert.deepEqual(p.ruta(grafo, 'casa', 'plaza'), { camino: ['casa', 'l1', 'l2', 'plaza'], largo: 305 });
  assert.deepEqual(p.ruta(grafo, 'plaza', 'plaza'), { camino: ['plaza'], largo: 0 });
});

test('la caminata más larga dura unos seis segundos', () => {
  let maximo = 0;
  for (const a of lugares) for (const b of lugares) maximo = Math.max(maximo, p.ruta(grafo, a, b).largo);
  assert.equal(maximo, 725);
  cerca(maximo / datos.velocidad, 6.3, 0.05);
});

test('se llega una vez, al lugar, y el gachamon queda detrás', () => {
  const paseo = p.crearPaseo(datos, grafo, 'casa');
  assert.deepEqual([paseo.x, paseo.y, paseo.gx, paseo.gy, paseo.caminando], [75, 330, 75 - 26, 330, false]);
  assert.equal(p.ir(paseo, 'tienda'), 'camina');
  assert.equal(paseo.destino, 'tienda');
  assert.equal(caminar(paseo, 305 / 115 + 0.2), 1);
  assert.deepEqual([paseo.x, paseo.y, paseo.caminando, paseo.destino, paseo.en], [220, 170, false, null, 'tienda']);
  cerca(Math.hypot(paseo.x - paseo.gx, paseo.y - paseo.gy), 26, 0.5);
});

test('a medio camino va por el camino, a su velocidad, y el gachamon por el mismo rastro', () => {
  const paseo = p.crearPaseo(datos, grafo, 'casa');
  p.ir(paseo, 'tienda');
  caminar(paseo, 1);
  cerca(paseo.x, 75 + 90, 0.01);
  cerca(paseo.y, 330 - 25, 0.01);
  assert.equal(paseo.caminando, true);
  cerca(paseo.gx, 165 - 1, 0.6);
  cerca(paseo.gy, 330, 0.6);
  assert.equal(paseo.gcaminando, true);
});

test('mira hacia donde camina', () => {
  const paseo = p.crearPaseo(datos, grafo, 'refugio');
  p.ir(paseo, 'barrio');
  caminar(paseo, 0.5);
  assert.equal(paseo.mira, -1);
  assert.equal(paseo.gmira, -1);
});

test('cambiar de rumbo a mitad de camino: seguir o volver, lo más corto', () => {
  const sigue = p.crearPaseo(datos, grafo, 'casa');
  p.ir(sigue, 'tienda');
  caminar(sigue, 0.5);
  assert.equal(p.ir(sigue, 'refugio'), 'camina');
  caminar(sigue, 0.1);
  assert.ok(sigue.x > 132.5 && sigue.y === 330);
  assert.equal(caminar(sigue, 10), 1);
  assert.deepEqual([sigue.x, sigue.y, sigue.en], [575, 330, 'refugio']);

  const vuelve = p.crearPaseo(datos, grafo, 'casa');
  p.ir(vuelve, 'tienda');
  caminar(vuelve, 0.2);
  assert.equal(p.ir(vuelve, 'casa'), 'camina');
  assert.equal(caminar(vuelve, 1), 1);
  assert.deepEqual([vuelve.x, vuelve.y, vuelve.en], [75, 330, 'casa']);
});

test('tocar donde ya estás es llegar, y un lugar que no existe no hace nada', () => {
  const paseo = p.crearPaseo(datos, grafo, 'plaza');
  assert.equal(p.ir(paseo, 'plaza'), 'llego');
  assert.equal(paseo.caminando, false);
  assert.equal(p.ir(paseo, 'portal'), 'nada');
  assert.equal(p.ir(paseo, 'u1'), 'nada');
  assert.equal(p.avanzar(paseo, 1), false);
});

test('el segundo toque te lleva de inmediato', () => {
  const paseo = p.crearPaseo(datos, grafo, 'casa');
  assert.equal(p.llegarYa(paseo), false);
  p.ir(paseo, 'aventura');
  caminar(paseo, 1);
  assert.equal(p.llegarYa(paseo), true);
  assert.deepEqual([paseo.x, paseo.y, paseo.caminando, paseo.destino, paseo.en], [640, 170, false, null, 'aventura']);
  cerca(Math.hypot(paseo.x - paseo.gx, paseo.y - paseo.gy), 26, 0.5);
  assert.equal(p.avanzar(paseo, 1), false);
});

test('muchos toques seguidos nunca lo sacan de un camino', () => {
  const paseo = p.crearPaseo(datos, grafo, 'casa');
  const enUnCamino = () => datos.aristas.some(([a, b]) => {
    const [ax, ay] = datos.nodos[a], [bx, by] = datos.nodos[b];
    const largo = Math.hypot(bx - ax, by - ay);
    return Math.abs(Math.hypot(paseo.x - ax, paseo.y - ay) + Math.hypot(paseo.x - bx, paseo.y - by) - largo) < 0.01;
  });
  let semilla = 7;
  const azar = () => { semilla = (semilla * 1664525 + 1013904223) % 4294967296; return semilla / 4294967296; };
  for (let i = 0; i < 400; i += 1) {
    p.ir(paseo, lugares[Math.floor(azar() * lugares.length)]);
    caminar(paseo, azar() * 1.5, 0.03);
    assert.ok(enUnCamino(), `fuera del camino en ${paseo.x}, ${paseo.y}`);
  }
});

test('el gachamon salta sólo cuando camina', () => {
  assert.equal(p.salto(1.23, false), 0);
  assert.equal(p.salto(0, true), 0);
  cerca(p.salto(0.09, true), 5, 0.01);
  cerca(p.salto(0.18, true), 0, 0.01);
  assert.ok(p.salto(0.27, true) > 0);
});

test('en el teléfono se ve un trozo y en el computador el pueblo entero', () => {
  const telefono = p.encuadre(390, 559, datos);
  cerca(telefono.escala, 1.3, 0.001);
  assert.equal(telefono.completo, false);
  cerca(telefono.anchoVista, 300, 0.01);
  const compu = p.encuadre(1000, 645, datos);
  cerca(compu.escala, 1000 / 690, 0.001);
  assert.equal(compu.completo, true);
  assert.ok(compu.anchoVista >= 690 - 1e-6);
  assert.equal(p.encuadre(900, 2000, datos).completo, true);
  assert.equal(p.encuadre(899, 559, datos).completo, false);
});

test('la cámara sigue al avatar sin salirse del pueblo', () => {
  assert.equal(p.camaraHacia(75, 300, datos), 0);
  assert.equal(p.camaraHacia(300, 300, datos), 150);
  assert.equal(p.camaraHacia(640, 300, datos), 390);
  assert.equal(p.camaraHacia(300, 800, datos), 0);
  cerca(p.acercarCamara(0, 100, 0.1), 50);
  assert.equal(p.acercarCamara(0, 100, 1), 100);
});

test('arrastrar mueve la cámara, y las flechas dicen si queda pueblo', () => {
  assert.equal(p.arrastrarCamara(100, -130, 1.3, 300, datos), 200);
  assert.equal(p.arrastrarCamara(100, 1300, 1.3, 300, datos), 0);
  assert.equal(p.arrastrarCamara(100, -1300, 1.3, 300, datos), 390);
  assert.deepEqual(p.flechas(0, 300, datos), { izquierda: false, derecha: true });
  assert.deepEqual(p.flechas(200, 300, datos), { izquierda: true, derecha: true });
  assert.deepEqual(p.flechas(390, 300, datos), { izquierda: true, derecha: false });
  assert.deepEqual(p.flechas(0, 800, datos), { izquierda: false, derecha: false });
});

test('qué lugar se tocó', () => {
  assert.equal(p.lugarEn(datos, 75, 300), 'casa');
  assert.equal(p.lugarEn(datos, 75, 338), 'casa');
  assert.equal(p.lugarEn(datos, 300, 215), 'plaza');
  assert.equal(p.lugarEn(datos, 232, 250), null);
  assert.equal(p.lugarEn(datos, 75, 240), null);
  assert.equal(p.lugarEn(datos, 165, 150), null);
});

// Lo que el encargo dejaba abierto y se decidió así.

// Un triángulo: de `a` a `b` derecho, y `c` a la misma distancia de los dos.
// `d` es un lugar al que no llega ningún camino.
const triangulo = {
  ancho: 300, alto: 100, velocidad: 100, hueco: 10,
  lugares: { a: { nombre: 'A' }, b: { nombre: 'B' }, c: { nombre: 'C' }, d: { nombre: 'D' } },
  nodos: { a: [0, 0], b: [100, 0], c: [50, 50], d: [300, 0] },
  aristas: [['a', 'b'], ['a', 'c'], ['b', 'c']],
};

test('una pestaña que estuvo dormida llega de una vez, sin pasarse; sin tiempo no pasa nada', () => {
  const paseo = p.crearPaseo(datos, grafo, 'casa');
  p.ir(paseo, 'aventura');
  caminar(paseo, 1);
  const visto = () => [paseo.x, paseo.y, paseo.gx, paseo.gy, paseo.t, paseo.caminando, paseo.gcaminando, paseo.en];
  const antes = visto();
  assert.equal(antes[6], true);
  for (const dt of [0, -1, Number.NaN]) assert.equal(p.avanzar(paseo, dt), false);
  assert.deepEqual(visto(), antes);
  assert.equal(p.avanzar(paseo, 1000), true);
  assert.deepEqual([paseo.x, paseo.y, paseo.caminando, paseo.destino, paseo.en], [640, 170, false, null, 'aventura']);
  cerca(Math.hypot(paseo.x - paseo.gx, paseo.y - paseo.gy), 26, 0.5);
  cerca(paseo.t, 725 / 115);
  assert.equal(p.avanzar(paseo, 1000), false);
});

test('«en» es el último nodo alcanzado, sea lugar o cruce', () => {
  const paseo = p.crearPaseo(datos, grafo, 'casa');
  assert.equal(paseo.en, 'casa');
  p.ir(paseo, 'tienda');
  caminar(paseo, 1);
  assert.equal(paseo.en, 'l1');
});

// De `a` a `b` hay dos caminos igual de cortos, por `x` y por `y`. Desde `a`
// se elige uno y desde `m` el otro, porque `y` ya se conocía por `k`.
const rombo = {
  ancho: 400, alto: 300, velocidad: 100, hueco: 10,
  lugares: { a: { nombre: 'A' }, b: { nombre: 'B' } },
  nodos: { a: [0, 150], k: [0, 100], m: [100, 150], x: [200, 250], y: [200, 50], b: [300, 150] },
  aristas: [['a', 'k'], ['a', 'm'], ['k', 'y'], ['m', 'x'], ['m', 'y'], ['x', 'b'], ['y', 'b']],
};

test('pedir otra vez el mismo destino no cambia el camino, aunque haya otro igual de corto', () => {
  const grafoR = p.armarGrafo(rombo);
  const desdeA = p.ruta(grafoR, 'a', 'b');
  const desdeM = p.ruta(grafoR, 'm', 'b');
  assert.deepEqual(desdeA.camino.slice(1), ['m', 'y', 'b']);
  assert.deepEqual(desdeM.camino, ['m', 'x', 'b']);
  const una = p.crearPaseo(rombo, grafoR, 'a');
  const otra = p.crearPaseo(rombo, grafoR, 'a');
  p.ir(una, 'b');
  p.ir(otra, 'b');
  p.avanzar(una, 0.5);
  p.avanzar(otra, 0.5);
  assert.equal(p.ir(otra, 'b'), 'camina');
  p.avanzar(una, 1);
  p.avanzar(otra, 1);
  assert.ok(otra.y < 150, `cambió de camino: ${otra.y}`);
  assert.deepEqual([otra.x, otra.y, otra.gx, otra.gy, otra.destino], [una.x, una.y, una.gx, una.gy, una.destino]);
});

test('si seguir y volver cuestan lo mismo, sigue', () => {
  const paseo = p.crearPaseo(triangulo, p.armarGrafo(triangulo), 'a');
  p.ir(paseo, 'b');
  p.avanzar(paseo, 0.5);
  assert.equal(paseo.x, 50);
  assert.equal(p.ir(paseo, 'c'), 'camina');
  p.avanzar(paseo, 0.1);
  assert.deepEqual([paseo.x, paseo.y], [60, 0]);
});

test('a donde no llega ningún camino no se va', () => {
  const grafoT = p.armarGrafo(triangulo);
  assert.deepEqual(p.ruta(grafoT, 'a', 'd'), { camino: [], largo: Infinity });
  const paseo = p.crearPaseo(triangulo, grafoT, 'a');
  assert.equal(p.ir(paseo, 'd'), 'nada');
  assert.equal(paseo.caminando, false);
  p.ir(paseo, 'b');
  p.avanzar(paseo, 0.5);
  assert.equal(p.ir(paseo, 'd'), 'nada');
  assert.equal(paseo.destino, 'b');
});

test('al dar la vuelta, el gachamon sigue hasta donde se dio la vuelta y queda detrás', () => {
  const paseo = p.crearPaseo(datos, grafo, 'casa');
  p.ir(paseo, 'tienda');
  caminar(paseo, 0.5);
  cerca(paseo.x, 132.5);
  p.ir(paseo, 'casa');
  caminar(paseo, 0.1);
  cerca(paseo.x, 121);
  cerca(paseo.gx, 118);
  assert.equal(paseo.gmira, 1);
  caminar(paseo, 0.2);
  cerca(paseo.x, 98);
  cerca(paseo.gx, 124);
  assert.equal(paseo.gmira, -1);
});

test('el rastro no crece aunque se camine mucho ni se dé la vuelta mil veces', () => {
  const paseo = p.crearPaseo(datos, grafo, 'casa');
  for (let i = 0; i < 20; i += 1) {
    p.ir(paseo, 'aventura');
    caminar(paseo, 7);
    p.ir(paseo, 'casa');
    caminar(paseo, 7);
  }
  assert.ok(paseo.rastro.length <= 4, `${paseo.rastro.length} puntos`);
  p.ir(paseo, 'tienda');
  caminar(paseo, 0.5);
  for (let i = 0; i < 1000; i += 1) {
    p.ir(paseo, i % 2 ? 'tienda' : 'casa');
    p.avanzar(paseo, 0.03);
  }
  assert.ok(paseo.rastro.length <= 12, `${paseo.rastro.length} puntos`);
  assert.ok(Math.hypot(paseo.x - paseo.gx, paseo.y - paseo.gy) <= 26 + 1e-6);
});

test('al llegar de inmediato, los dos miran hacia donde iban y el gachamon está quieto', () => {
  const paseo = p.crearPaseo(datos, grafo, 'refugio');
  p.ir(paseo, 'barrio');
  assert.equal(p.llegarYa(paseo), true);
  assert.deepEqual([paseo.x, paseo.y, paseo.mira, paseo.gmira, paseo.gcaminando], [395, 330, -1, -1, false]);
  cerca(paseo.gx, 395 + 26);
  cerca(paseo.gy, 330);
});

test('si se toca entre dos lugares, es el más cercano; la cámara no se sale aunque el pueblo quepa entero', () => {
  const dos = { ancho: 300, alto: 200, lugares: { a: {}, b: {} }, nodos: { a: [100, 100], b: [130, 100] } };
  assert.equal(p.lugarEn(dos, 110, 90), 'a');
  assert.equal(p.lugarEn(dos, 120, 90), 'b');
  assert.equal(p.arrastrarCamara(100, -130, 1.3, 800, datos), 0);
  assert.equal(p.camaraHacia(-50, 300, datos), 0);
});
