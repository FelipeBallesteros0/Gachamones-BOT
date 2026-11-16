// Lo que la pantalla de un lugar y la de tu departamento hacen igual con un
// gachamon: los cuatro cuidados y sus botones, sus tres barras, las cuentas de
// sus esperas y cómo se rotulan, y lo que decide qué se celebra y qué se avisa
// tras un cuidado o una caricia. Cada pantalla pone sus propios nodos alrededor
// y le pasa aquí lo que hace (saltar, ganar, celebrar, avisar…). Todo texto
// entra por `el` o por `textContent`.

import { lienzoDePieza } from './arte.js';
import { el } from './dom.js';
import {
  avisoDelCuidado, avisosDeMedallas, formatoEspera, seCelebraLaEvolucion,
} from './tiempo.js';

export const CUIDADOS = [
  { accion: 'alimentar', icono: '🍖', nombre: 'Alimentar' },
  { accion: 'jugar', icono: '🎮', nombre: 'Jugar' },
  { accion: 'entrenar', icono: '🏋️', nombre: 'Entrenar' },
  { accion: 'limpiar', icono: '🧼', nombre: 'Bañar' },
];

export const BARRAS = [
  { clave: 'comida', icono: '🍖', nombre: 'Comida' },
  { clave: 'animo', icono: '😊', nombre: 'Ánimo' },
  { clave: 'aseo', icono: '🧼', nombre: 'Aseo' },
];

// Por debajo de 40 el gachamon lo pide (`globos.UMBRAL_NECESIDAD`).
function nivelDeBarra(valor) {
  if (valor < 40) return 'bajo';
  if (valor < 65) return 'medio';
  return 'alto';
}

// Las palabras que pone la propia pantalla concuerdan con el gachamon:
// masculino salvo para una hembra.
export function segun(genero, masculino, femenino) {
  return genero === 'hembra' ? femenino : masculino;
}

// --- las barras -------------------------------------------------------------------

// El medidor de una barra: su nombre, su cifra y su pista.
export function medidorDe({ clave, icono, nombre }) {
  const cifra = el('span', { class: 'medidor-cifra' });
  const relleno = el('span', { class: 'medidor-relleno' });
  const nodo = el('div', { class: 'medidor' },
    el('span', { class: 'medidor-nombre' }, el('span', { 'aria-hidden': 'true' }, icono), ` ${nombre}`),
    cifra,
    el('span', { class: 'medidor-pista', 'aria-hidden': 'true' }, relleno));
  return { clave, nodo, cifra, relleno };
}

export function pintarMedidores(medidores, barras) {
  for (const m of medidores) {
    const valor = Number(barras[m.clave]) || 0;
    m.cifra.textContent = String(valor);
    m.relleno.style.width = `${valor}%`;
    m.relleno.dataset.nivel = nivelDeBarra(valor);
  }
}

// --- las esperas ------------------------------------------------------------------

// Cuándo se acaba cada espera, en la hora de este teléfono: `hasta[accion]`,
// a partir de los segundos que dice el servidor.
export function ponerEsperas(hasta, esperas) {
  const ahora = Date.now();
  for (const [accion, segundos] of Object.entries(esperas || {})) {
    hasta[accion] = ahora + Math.max(0, Number(segundos) || 0) * 1000;
  }
}

export function faltaPara(hasta, accion) {
  const fin = hasta[accion];
  return typeof fin === 'number' ? Math.max(0, Math.ceil((fin - Date.now()) / 1000)) : 0;
}

// --- los botones de los cuidados --------------------------------------------------

// El botón de un cuidado, con su ícono, su nombre y lo que le queda de espera.
export function botonDeCuidado({ accion, icono, nombre }) {
  const espera = el('span', { class: 'cuidado-espera' });
  const nodo = el('button', { type: 'button', class: 'cuidado' },
    el('span', { class: 'cuidado-icono', 'aria-hidden': 'true' }, icono),
    el('span', { class: 'cuidado-nombre' }, nombre),
    espera);
  return { accion, nombre, nodo, espera };
}

// Lo que le falta a un cuidado (`falta`, en segundos): se lee en el botón y en
// su nombre para el lector, y mientras falte, o mientras contesta el servidor,
// no se puede usar.
export function contarCuidado(c, falta) {
  const texto = formatoEspera(falta);
  if (c.espera.textContent !== texto) c.espera.textContent = texto;
  const ocupado = c.nodo.classList.contains('esperando');
  c.nodo.setAttribute('aria-disabled', String(ocupado || falta > 0));
  if (falta > 0) c.nodo.setAttribute('aria-label', `${c.nombre}, disponible en ${texto}`);
  else c.nodo.removeAttribute('aria-label');
}

// --- lo que se dice tras un cuidado o una caricia ---------------------------------

// El aviso de que evolucionó.
export function avisoDeLaEvolucion(g) {
  return el('p', { class: 'celebracion-texto' },
    `✨ ¡${g.nombre} ha evolucionado! Ahora es ${g.nombre_etapa}.`);
}

// El aviso de una medalla nueva.
export function avisoDeMedalla(texto) {
  return el('p', { class: 'medalla' },
    lienzoDePieza('efectos/estrella.png', 20, 20), texto);
}

// Tras un cuidado que contestó el juego: si salió, el salto y las monedas
// ganadas; la evolución; una línea por medalla nueva; y la frase del juego.
// `respuesta` es la de `POST cuidar`, con quien lo recibió en
// `respuesta.estado.gachamon`; `etapaAntes`, la etapa que se veía al tocar:
// si la que llega es otra, evolucionó, aunque la respuesta sea la de un
// reintento, que no trae la marca.
export function trasCuidar(respuesta, etapaAntes, { saltar, ganar, celebrar, medalla, avisar }) {
  if (respuesta.ok) {
    saltar();
    if (respuesta.monedas > 0) ganar(respuesta.monedas);
  }
  if (seCelebraLaEvolucion(respuesta, etapaAntes)) celebrar();
  for (const texto of avisosDeMedallas(respuesta)) medalla(texto);
  // La frase del juego se lee siempre: «Se ha empachado» también cuenta.
  const frase = avisoDelCuidado(respuesta);
  if (frase) avisar(frase);
}

// Tras una caricia que contestó el juego: si se pudo, corazones y el salto;
// si todavía no, apenas se mueve y se dice cuándo se podrá. `g` es el
// gachamon que se quiso acariciar.
export function trasAcariciar(respuesta, g, { corazones, saltar, titubear, avisar }) {
  if (respuesta.ok) {
    corazones();
    saltar();
  } else if (respuesta.espera > 0 && g) {
    // Antes de tiempo no hay corazones ni error: apenas se mueve.
    titubear();
    avisar(`Podrás acariciar${segun(g.genero, 'lo', 'la')} en ${formatoEspera(respuesta.espera)}.`);
  }
}
