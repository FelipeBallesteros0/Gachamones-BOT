import test from 'node:test';
import assert from 'node:assert/strict';
import * as c from '../../web/static/js/casillas.js';

const CAMA = { clave: 'cama_sencilla', ancho: 2, fondo: 1, capa: 'bulto' };
const ALFOMBRA = { clave: 'alfombra', ancho: 2, fondo: 2, capa: 'suelo' };
const MACETA = { clave: 'maceta', ancho: 1, fondo: 1, capa: 'bulto' };
const FELPUDO = { clave: 'felpudo', ancho: 1, fondo: 1, capa: 'suelo' };
const CUADRO = { clave: 'cuadro', ancho: 1, fondo: 1, capa: 'pared' };
const CORTINAS = { clave: 'cortinas', ancho: 2, fondo: 1, capa: 'pared' };

function depto(puestos, ancho = 3, fondo = 3) {
  return { ancho, fondo, casillas: ancho * fondo, comodidad: 80, tope: 100, camas: 0, gachamones: 0, puestos, guardados: [] };
}

test('la huella es la del servidor', () => {
  assert.deepEqual(c.huellaDe(CAMA, 1, 1, 0), [[1, 1], [2, 1]]);
  assert.deepEqual(c.huellaDe(CAMA, 1, 1, 1), [[1, 1], [1, 2]]);
  assert.deepEqual(c.huellaDe(CAMA, 1, 1, 2), c.huellaDe(CAMA, 1, 1, 0));
  assert.deepEqual(c.huellaDe(ALFOMBRA, 0, 0, 3), [[0, 0], [0, 1], [1, 0], [1, 1]]);
  assert.deepEqual(c.huellaDe(CORTINAS, 1, -1, 3), [[1, -1], [2, -1]]);
  assert.deepEqual(c.huellaDe(CORTINAS, -1, 0, 0), [[-1, 0], [-1, 1]]);
});

test('lo que el servidor rechazaría no cabe', () => {
  const d = depto([{ id: 1, ...ALFOMBRA, x: 0, y: 0, giro: 0, casillas: [[0, 0], [0, 1], [1, 0], [1, 1]] },
                   { id: 4, ...MACETA, x: 2, y: 2, giro: 0, casillas: [[2, 2]] },
                   { id: 5, ...CORTINAS, x: 0, y: -1, giro: 0, casillas: [[0, -1], [1, -1]] }]);
  const maceta = { id: 2, ...MACETA }, felpudo = { id: 3, ...FELPUDO }, cama = { id: 6, ...CAMA }, cuadro = { id: 7, ...CUADRO };
  assert.equal(c.problemaAlPoner(d, maceta, 1, 1, 0), null);
  assert.equal(c.problemaAlPoner(d, felpudo, 1, 1, 0), 'ocupado');
  assert.equal(c.problemaAlPoner(d, felpudo, 2, 2, 0), null);
  assert.equal(c.problemaAlPoner(d, maceta, 2, 2, 0), 'ocupado');
  assert.equal(c.problemaAlPoner(d, cama, 2, 0, 0), 'no_cabe');
  assert.equal(c.problemaAlPoner(d, cama, 2, 0, 1), null);
  assert.equal(c.problemaAlPoner(d, cama, 0, -1, 0), 'no_cabe');
  assert.equal(c.problemaAlPoner(d, cuadro, 1, -1, 0), 'ocupado');
  assert.equal(c.problemaAlPoner(d, cuadro, 2, -1, 0), null);
  assert.equal(c.problemaAlPoner(d, cuadro, -1, 3, 0), 'no_cabe');
  assert.equal(c.problemaAlPoner(d, cuadro, -1, -1, 0), 'no_cabe');
  assert.equal(c.problemaAlPoner(d, cuadro, 1, 1, 0), 'no_cabe');
  assert.equal(c.problemaAlPoner(d, d.puestos[1], 2, 2, 1), null);
});

test('dónde cabe y con qué giro', () => {
  const d = depto([{ id: 1, ...CAMA, x: 0, y: 0, giro: 0, casillas: [[0, 0], [1, 0]] }]);
  const otra = { id: 2, ...CAMA };
  assert.equal(c.giroParaPoner(d, otra, 0, 1, 0), 0);
  assert.equal(c.giroParaPoner(d, otra, 2, 0, 0), 1);
  assert.equal(c.giroParaPoner(d, otra, 0, 0, 0), null);
  assert.deepEqual(c.dondeCabe(d, otra, 0), [
    { x: 2, y: 0, giro: 1 }, { x: 0, y: 1, giro: 0 }, { x: 1, y: 1, giro: 0 },
    { x: 2, y: 1, giro: 1 }, { x: 0, y: 2, giro: 0 }, { x: 1, y: 2, giro: 0 },
  ]);
  assert.deepEqual(c.dondeCabe(d, { id: 3, ...CORTINAS }, 0), [
    { x: 0, y: -1, giro: 0 }, { x: 1, y: -1, giro: 0 }, { x: -1, y: 0, giro: 0 }, { x: -1, y: 1, giro: 0 },
  ]);
});

test('las casillas ocupadas no cuentan dos veces la de la alfombra', () => {
  const d = depto([{ id: 1, ...ALFOMBRA, x: 0, y: 0, giro: 0, casillas: [[0, 0], [0, 1], [1, 0], [1, 1]] },
                   { id: 2, ...MACETA, x: 1, y: 1, giro: 0, casillas: [[1, 1]] },
                   { id: 3, ...CORTINAS, x: 0, y: -1, giro: 0, casillas: [[0, -1], [1, -1]] }]);
  assert.equal(c.ocupadas(d), 4);
  assert.deepEqual([...c.noSePisan(d)], ['1,1']);
});

test('el camino rodea los muebles', () => {
  const muro = new Set(['1,0', '1,1']);
  assert.deepEqual(c.camino(3, 3, muro, [0, 0], [2, 0]), [[0, 1], [0, 2], [1, 2], [2, 2], [2, 1], [2, 0]]);
  assert.deepEqual(c.camino(3, 3, new Set(), [0, 0], [0, 0]), []);
  assert.deepEqual(c.camino(3, 3, muro, [0, 0], [1, 1]), []);
  assert.deepEqual(c.camino(3, 3, new Set(['1,0', '1,1', '1,2']), [0, 0], [2, 0]), []);
});

test('quien queda bajo un mueble se corre a la libre más cercana', () => {
  const muro = new Set(['1,1']);
  assert.deepEqual(c.libreMasCercana(3, 3, muro, [0, 0]), [0, 0]);
  assert.deepEqual(c.libreMasCercana(3, 3, muro, [1, 1]), [1, 0]);
  const todo = new Set(); for (let i = 0; i < 3; i += 1) for (let j = 0; j < 3; j += 1) todo.add(`${i},${j}`);
  assert.equal(c.libreMasCercana(3, 3, todo, [1, 1]), null);
  assert.deepEqual(c.libreMasCercana(3, 3, new Set(), [7, 7]), [2, 2]);
});

test('un gachamon suelto da un paso a una vecina que se pise', () => {
  assert.deepEqual(c.pasoSuelto(3, 3, new Set(['1,0']), [0, 0], () => 0), [0, 1]);
  assert.deepEqual(c.pasoSuelto(3, 3, new Set(['1,0', '0,1']), [0, 0], () => 0.99), [0, 0]);
});

test('al entrar se reparten desde el frente', () => {
  const cama = new Set(['0,0', '1,0']);
  assert.deepEqual(c.sitiosDeEntrada(3, 3, cama, 3), [[2, 2], [1, 2], [2, 1]]);
  const casiTodo = new Set(['0,0', '1,0', '2,0', '0,1', '1,1', '2,1', '0,2', '1,2']);
  assert.deepEqual(c.sitiosDeEntrada(3, 3, casiTodo, 3), [[2, 2], [2, 2], [2, 2]]);
  assert.deepEqual(c.sitiosDeEntrada(3, 3, new Set([...casiTodo, '2,2']), 3), []);
});

test('la línea bajo la pieza', () => {
  const d = { ancho: 4, fondo: 4, casillas: 16, comodidad: 88, tope: 106, camas: 4, gachamones: 3,
              puestos: [{ id: 1, ...CAMA, x: 0, y: 0, giro: 0, casillas: [[0, 0], [1, 0]] }] };
  assert.equal(c.lineaDeEstado(d), '4 × 4 · 2 de 16 casillas · camas 4 · gachamones 3 · comodidad 88 de 106');
});

test('cada sitio tiene su nombre', () => {
  assert.equal(c.nombreDelSitio(1, 0), 'fila 1, columna 2');
  assert.equal(c.nombreDelSitio(-1, 2), 'pared izquierda, tramo 3');
  assert.equal(c.nombreDelSitio(0, -1), 'pared derecha, tramo 1');
});
