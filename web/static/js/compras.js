// Lo que la tienda dice con palabras: la pregunta antes de cada compra, de
// vender y de mejorar una casa, y lo que se cuenta de cada casa. Puro: no toca
// la página. Los precios y lo que hay en cada casa los da el servidor; aquí
// sólo se dicen, con «moneda» y «gema» en singular cuando es una.

import { cuantasGemas, cuantasMonedas } from './tiempo.js';

// «¿Comprar por 10 monedas?». `moneda` es `'monedas'` o `'gemas'`.
export function preguntaDeCompra(precio, moneda) {
  const cuanto = moneda === 'gemas' ? cuantasGemas(precio) : cuantasMonedas(precio);
  return `¿Comprar por ${cuanto}?`;
}

// «casa pequeña»: dentro de una frase, el nombre va en minúscula.
const enLaFrase = (casa) => String(casa.nombre).toLowerCase();

// «Sus 2 muebles…» o «Su mueble…», según cuántos.
function cuantosHay(cantidad, uno, varios) {
  return cantidad === 1 ? uno : varios;
}

// La lista como se dice: «a», «a y b», «a, b y c».
function enumerar(partes) {
  if (partes.length <= 1) return partes.join('');
  return `${partes.slice(0, -1).join(', ')} y ${partes[partes.length - 1]}`;
}

// Con una de `casas.tuyas`: el precio de la venta y lo que pasa con lo que hay
// dentro, nombrando sólo lo que hay.
export function preguntaDeVenta(casa) {
  const pregunta = `¿Vender tu ${enLaFrase(casa)} por ${cuantasMonedas(casa.dan)}?`;
  const partes = [];
  if (casa.muebles > 0) {
    partes.push(cuantosHay(casa.muebles, 'su mueble queda guardado',
      `sus ${casa.muebles} muebles quedan guardados`));
  }
  if (casa.viven > 0) {
    partes.push(cuantosHay(casa.viven, 'su gachamon se va al refugio',
      `sus ${casa.viven} gachamones se van al refugio`));
  }
  if (casa.plantados > 0) partes.push('lo plantado se pierde');
  if (!partes.length) return pregunta;
  const consecuencias = enumerar(partes);
  return `${pregunta} ${consecuencias[0].toUpperCase()}${consecuencias.slice(1)}.`;
}

// Con una de `casas.tuyas` y una de sus `mejoras`.
export function preguntaDeMejora(casa, mejora) {
  return `¿Mejorar tu ${enLaFrase(casa)} a ${enLaFrase(mejora)} por ${cuantasMonedas(mejora.cuesta)}?`;
}

// Con una de `casas.a_la_venta`: cuántos caben, sus huecos para muebles y, si
// tiene, sus bancales.
export function loQueTraeLaCasa(casa) {
  const partes = [
    cuantosHay(casa.aforo, 'Cabe 1 gachamon', `Caben ${casa.aforo} gachamones`),
    cuantosHay(casa.huecos, '1 hueco para muebles', `${casa.huecos} huecos para muebles`),
  ];
  if (casa.bancales > 0) partes.push(cuantosHay(casa.bancales, '1 bancal', `${casa.bancales} bancales`));
  return partes.join(' · ');
}

// Con una de `casas.tuyas`: cuántos viven en ella y cuántos caben.
export function quienesViven(casa) {
  let viven = 'No vive nadie';
  if (casa.viven > 0) viven = cuantosHay(casa.viven, 'Vive 1 gachamon', `Viven ${casa.viven} gachamones`);
  return `${viven} · ${cuantosHay(casa.aforo, 'cabe 1', `caben ${casa.aforo}`)}`;
}
