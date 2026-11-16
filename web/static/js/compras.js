// Lo que la tienda dice con palabras: la pregunta antes de cada compra. Puro:
// no toca la página. Los precios los da el servidor; aquí sólo se dicen, con
// «moneda» y «gema» en singular cuando es una.

import { cuantasGemas, cuantasMonedas } from './tiempo.js';

// «¿Comprar por 10 monedas?». `moneda` es `'monedas'` o `'gemas'`.
export function preguntaDeCompra(precio, moneda) {
  const cuanto = moneda === 'gemas' ? cuantasGemas(precio) : cuantasMonedas(precio);
  return `¿Comprar por ${cuanto}?`;
}
