// Lo común a las pantallas que enseñan una lista de cosas —la tienda y la
// mochila—: la cabecera con los saldos, la fila de cada cosa, la pregunta del
// primer toque, la zona donde se dice lo que contestó el juego, la espera de
// la lista y qué hacer con un error. Cada pantalla pone lo suyo encima. Todo
// texto entra por `el` o por `textContent`.

import { conReintentos, pedir } from './api.js';
import { lienzoDePieza } from './arte.js';
import { el } from './dom.js';
import { siguiente } from './pantallas.js';
import { cuantasGemas, cuantasMonedas } from './tiempo.js';

const LADO_DEL_ICONO = 48;
const AVISO_DURA_MS = 6000;
const ALGO_SALIO_MAL = 'Algo salió mal. Vuelve a intentarlo.';

// Las dos monedas del juego: cómo se ven y cómo se dicen.
export const MONEDAS = { simbolo: '🪙', palabra: 'monedas', cuantas: cuantasMonedas };
export const GEMAS = { simbolo: '💎', palabra: 'gemas', cuantas: cuantasGemas };

export function mensajeDe(error) {
  return error && typeof error.mensaje === 'string' && error.mensaje ? error.mensaje : ALGO_SALIO_MAL;
}

// Sin sesión (401) o con un «no» que cambia la pantalla (409: sin gachamon, ya
// no estás en la tienda, eso no se te vende…), se decide de nuevo.
export function hayQueDecidirDeNuevo(error) {
  return Boolean(error) && (error.estado === 401 || error.estado === 409);
}

// Mientras se está en la pantalla de `vista` hay sesión y la cuenta ya no es
// nueva, así que la pantalla la decide sólo el estado, con la regla de siempre.
export function pideOtraPantalla(estado, vista) {
  return siguiente(true, { estado: 'en juego' }, estado, vista) !== vista;
}

// La cabecera: el nombre de la pantalla en el `h1`, con su ícono, que no se
// lee, y lo que tienes, que se ve con su símbolo y se lee con su palabra.
export function cabeceraConSaldos(icono, nombre) {
  const monedasVisibles = el('span', { 'aria-hidden': 'true' });
  const monedasLeidas = el('span', { class: 'solo-lector' });
  const gemasVisibles = el('span', { 'aria-hidden': 'true' });
  const gemasLeidas = el('span', { class: 'solo-lector' });
  const titulo = el('h1', { class: 'donde', tabindex: '-1' }, el('span', { 'aria-hidden': 'true' }, icono), nombre);
  const cabecera = el('header', { class: 'barra barra-lugar' },
    titulo,
    el('span', { class: 'saldos' },
      el('span', { class: 'saldo' }, monedasVisibles, monedasLeidas),
      el('span', { class: 'saldo' }, gemasVisibles, gemasLeidas)));

  function ponerSaldos({ monedas, gemas }) {
    monedasVisibles.textContent = `${MONEDAS.simbolo} ${monedas}`;
    monedasLeidas.textContent = cuantasMonedas(monedas);
    gemasVisibles.textContent = `${GEMAS.simbolo} ${gemas}`;
    gemasLeidas.textContent = cuantasGemas(gemas);
  }

  return { cabecera, titulo, ponerSaldos };
}

export const linea = (texto, clase) => el('p', { class: clase }, texto);

// Una fila: el ícono, el nombre, lo que se dice de ella y, a la derecha, lo
// que se puede hacer. `apagada`, lo que no se puede comprar; `debajo`, lo que
// va a lo ancho bajo todo lo demás.
export function filaDeArticulo({ id, icono, nombre, lineas, accion, apagada = false, debajo = null }) {
  const dibujo = lienzoDePieza(icono, LADO_DEL_ICONO, LADO_DEL_ICONO);
  dibujo.classList.add('articulo-icono');
  return el('li', { class: apagada ? 'articulo apagado' : 'articulo', 'data-fila': id },
    dibujo,
    el('div', { class: 'articulo-texto' }, el('p', { class: 'articulo-nombre' }, nombre), lineas),
    accion,
    debajo);
}

// La pregunta del primer toque, que va en lugar del botón: arriba lo que se
// pregunta (`pregunta`, un texto que recibe el foco para leerse, o un nodo ya
// hecho) y debajo el botón que lo confirma y «No». Escape es «No».
export function cajaDePregunta(pregunta, confirmar, { alConfirmar, alDesistir }) {
  const cabeza = typeof pregunta === 'string'
    ? el('p', { class: 'pregunta-texto', tabindex: '-1' }, pregunta)
    : pregunta;
  const si = el('button', { type: 'button', class: 'boton boton-chico principal' }, confirmar);
  const no = el('button', { type: 'button', class: 'boton boton-chico' }, 'No');
  const caja = el('div', { class: 'pregunta' }, cabeza, el('div', { class: 'pregunta-botones' }, si, no));
  si.addEventListener('click', alConfirmar);
  no.addEventListener('click', alDesistir);
  caja.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape') alDesistir();
  });
  return { caja, cabeza, si, no };
}

// Lo que contesta el juego: se queda abajo de lo que se ve mientras se recorre
// la lista, para que se lea aunque se haya tocado lo de más abajo, y se borra
// solo al rato. `parar()` al dejar la pantalla.
export function zonaDeAviso() {
  const nodo = el('p', { class: 'aviso-tienda', role: 'status' });
  let hasta = null;

  function avisar(texto, esError = false) {
    clearTimeout(hasta);
    nodo.textContent = texto || '';
    nodo.classList.toggle('es-error', Boolean(texto) && esError);
    if (texto) hasta = setTimeout(() => avisar(''), AVISO_DURA_MS);
  }

  return { nodo, avisar, parar: () => clearTimeout(hasta) };
}

// La lista de una pantalla, que se pide a `ruta`. Mientras no está, `lista` se
// esconde y en su lugar, en `espera`, se lee `cargando`; si no llega, su
// mensaje y «Volver a intentarlo», que la pide otra vez con el foco esperando
// en `titulo`. Sin sesión o con un 409 se va (`irse`). Con lo que llega,
// `espera` se esconde, `lista` se ve y se llama a `alLlegar(leido,
// trasReintentar)`. Si entretanto se dejó la pantalla (`sigueAqui()` es
// falso), ya no se pinta nada.
//
// `cargar()` la pide la primera vez. `releer()` es para después de una acción
// que no tuvo respuesta: pudo haber llegado igual, así que lo que se veía ya
// no vale; la lista se esconde y se vuelve a pedir, con reintentos. Las dos
// dan `true` si la lista quedó pintada.
export function listaQueSePide({ ruta, espera, lista, cargando, titulo, sigueAqui, irse, alLlegar }) {
  let enCurso = false;

  async function pedirla({ trasReintentar = false, conReintento = false } = {}) {
    if (enCurso) return false;
    enCurso = true;
    // El foco no se queda en lo que se esconde: espera en el título.
    if (lista.contains(document.activeElement)) titulo.focus({ preventScroll: true });
    lista.hidden = true;
    espera.hidden = false;
    espera.replaceChildren(el('p', { class: 'espera-tienda-texto', role: 'status' }, cargando));
    let leido;
    try {
      const unaVez = () => pedir('GET', ruta);
      leido = await (conReintento ? conReintentos(unaVez, sigueAqui) : unaVez());
    } catch (error) {
      if (!sigueAqui()) return false;
      if (hayQueDecidirDeNuevo(error)) {
        irse();
        return false;
      }
      const reintentar = el('button', { type: 'button', class: 'boton boton-chico principal' }, 'Volver a intentarlo');
      reintentar.addEventListener('click', () => {
        // El botón se borra al reintentar: el foco espera en el título.
        titulo.focus({ preventScroll: true });
        pedirla({ trasReintentar: true });
      });
      espera.replaceChildren(el('p', { class: 'espera-tienda-texto es-error', role: 'alert' }, mensajeDe(error)), reintentar);
      if (trasReintentar || conReintento) reintentar.focus({ preventScroll: true });
      return false;
    } finally {
      enCurso = false;
    }
    if (!sigueAqui()) return false;
    espera.replaceChildren();
    espera.hidden = true;
    lista.hidden = false;
    alLlegar(leido, trasReintentar);
    return true;
  }

  return {
    cargar: () => pedirla(),
    releer: () => pedirla({ conReintento: true }),
  };
}
