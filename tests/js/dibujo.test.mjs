import test from 'node:test';
import assert from 'node:assert/strict';
import {
  COLORES_DE_PIEL, COLORES_DE_PELO, COLORES_DE_ROPA, dibujarAvatar, dibujarHuevo,
} from '../../web/static/js/dibujo.js';

const lienzo = () => {
  const trazos = [];
  let color = null;
  return {
    trazos,
    set fillStyle(valor) { color = valor; },
    get fillStyle() { return color; },
    fillRect: (...caja) => trazos.push([color, ...caja]),
    save() {}, restore() {}, translate() {}, scale() {}, beginPath() {}, ellipse() {}, fill() {},
  };
};
const base = { piel: 'media', pelo: 'corto', color_de_pelo: 'castano', ropa: 'poleron', genero: 'macho' };
const pintar = (cambios = {}) => {
  const ctx = lienzo();
  dibujarAvatar(ctx, { ...base, ...cambios }, 4);
  return JSON.stringify(ctx.trazos);
};

test('hay un color para cada clave del catálogo', () => {
  assert.deepEqual(Object.keys(COLORES_DE_PIEL), ['clara', 'media', 'tostada', 'oscura']);
  assert.deepEqual(Object.keys(COLORES_DE_PELO), ['negro', 'castano', 'rubio', 'rojo', 'cano', 'azul']);
  assert.deepEqual(Object.keys(COLORES_DE_ROPA), ['poleron', 'camisa', 'vestido', 'overol']);
});

test('cada elección cambia el dibujo', () => {
  const normal = pintar();
  for (const cambio of [
    { piel: 'oscura' }, { pelo: 'largo' }, { pelo: 'rapado' }, { pelo: 'rizado' },
    { pelo: 'coleta' }, { color_de_pelo: 'azul' }, { ropa: 'vestido' }, { ropa: 'overol' },
  ]) {
    assert.notEqual(pintar(cambio), normal, JSON.stringify(cambio));
  }
});

test('una clave desconocida no revienta el dibujo', () => {
  assert.doesNotThrow(() => pintar({ piel: 'verde', pelo: 'cresta', ropa: 'armadura' }));
});

// Las cinco elecciones se ven: la del género también, no sólo las cuatro de arriba.
test('el género también cambia el dibujo', () => {
  assert.notEqual(pintar({ genero: 'hembra' }), pintar());
});

test('el huevo se dibuja con las mismas herramientas, y roto se ve distinto', () => {
  const entero = lienzo();
  const roto = lienzo();
  dibujarHuevo(entero, 4, false);
  dibujarHuevo(roto, 4, true);
  assert.notEqual(JSON.stringify(roto.trazos), JSON.stringify(entero.trazos));
});
