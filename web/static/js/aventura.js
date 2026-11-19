// La primera aventura: donde quien todavía no tiene ningún gachamon gana el
// primero. Se llega desde el lugar «Aventura», que la ofrece, como a la Tienda
// desde el suyo (`seguir` con la vista `'aventura'`).
//
// `aventura(contenedor, estado, seguir)` pinta la escena del lugar donde estás,
// con tu avatar (el fondo y el monigote son los de la escena del lugar, que
// exporta `lugar.js`), y pide lo que dice la aventura (`GET aventura`): si se
// puede y las frases de antes. Las frases las manda el servidor y entran tal
// cual. Mientras llegan, la tarjeta dice «Cargando la aventura…», con el aro de
// siempre; si no llegan, se dice por qué y el botón la vuelve a pedir. Si
// al llegar ya no se puede (ya tienes uno, o la cama ya no está libre), se
// vuelve a decidir la pantalla: el lugar lo dice.
//
// El diálogo va de a una frase, en una zona que se anuncia (`role="status"`),
// con un solo botón que avanza y que se queda con el foco: «Seguir» y, tras la
// tercera, «Acercarte», que manda el encuentro (`POST aventura/primera`) una
// sola vez: mientras va, otro toque no manda nada (no se apaga con `disabled`,
// para no perder el foco), y el segundo clic de un doble clic no cuenta (así
// ninguno se salta una frase). Con la respuesta se ve a tu gachamon (su
// retrato: quién es lo dice la frase) y las frases de después, y tras la
// última, «Volver a tu departamento», que sigue con el estado que llegó (toca
// el paso del nombre). Sin respuesta se dice lo de siempre y «Acercarte» se
// puede volver a pulsar. Ante cualquier «no» del encuentro (un 409) se vuelve
// a leer el estado y se sigue con él: lo normal es que ya lo tengas (un doble
// clic, otra pestaña: el encuentro ya te llevó a tu departamento); si tampoco
// se deja leer (un 401 o un 409), se vuelve a decidir. Sólo si sigues sin
// ninguno se dice la frase del servidor y queda «Volver». Antes del encuentro,
// «Volver» deja la aventura sin guardar nada. Lo que entra en la escena lo
// anima el estilo, que con movimiento reducido no anima nada. Al salir se deja
// de escuchar, y una respuesta que llega tarde no pinta ni llama a `seguir`.
// Todo texto entra por `el` o por `textContent`.

import { pedir } from './api.js';
import { olvidarLasQueFaltan } from './arte.js';
import { hayQueDecidirDeNuevo, mensajeDe, zonaDeAviso } from './articulos.js';
import { el } from './dom.js';
import { fondoDeLaEscena, monigoteDeLaEscena } from './lugar.js';

const TITULO = 'La primera aventura';
const SEGUIR = 'Seguir';
const ACERCARTE = 'Acercarte';
const VOLVER_A_TU_DEPARTAMENTO = 'Volver a tu departamento';
const SIN_RESPUESTA = 'No hubo respuesta. Revisa tu conexión.';
const CARGANDO = 'Cargando la aventura…';

export function aventura(contenedor, estado, seguir) {
  // El arte que no cargó en otra pantalla se pide de nuevo.
  olvidarLasQueFaltan();
  let vivo = true;
  const oyentes = new AbortController();

  // Lo que se lee: las frases de antes o, tras el encuentro, las de después, y
  // en cuál vas. `encontrado` es el estado que contestó el encuentro.
  let frases = [];
  let cual = 0;
  let encontrado = null;
  // Mientras el encuentro va (o se relee el estado tras un «no»), no sale otro;
  // y mientras se pide la aventura, no se pide otra vez.
  let enCamino = false;
  let leyendo = false;
  // Lo que hace ahora el botón que avanza, o `null` si no se ve.
  let alAvanzar = null;

  const aviso = zonaDeAviso();

  function parar() {
    vivo = false;
    aviso.parar();
    oyentes.abort();
    elFondo.parar();
  }

  // Deja la aventura y que se decida otra pantalla: con el estado que llegó, o
  // preguntando todo otra vez.
  function irse(estadoNuevo) {
    parar();
    seguir(estadoNuevo);
  }

  // Si la pantalla ya no está en la página (se pintó otra), se para todo.
  function sigueAqui() {
    if (vivo && !cuerpo.isConnected) parar();
    return vivo;
  }

  // --- la cabecera y la escena: el lugar, tú y, tras el encuentro, él ---------------------

  const titulo = el('h1', { class: 'donde', tabindex: '-1' }, TITULO);
  const cabecera = el('header', { class: 'barra barra-lugar' }, titulo);

  const fondo = el('canvas', { class: 'escena-fondo', 'aria-hidden': 'true' });
  const monigote = el('canvas', { class: 'monigote-lugar', 'aria-hidden': 'true' });
  const escena = el('div', { class: 'escena escena-lugar escena-aventura' },
    fondo,
    el('span', { class: 'ventana', 'aria-hidden': 'true' }),
    monigote);
  // El fondo del lugar y tu avatar, los mismos de la escena del lugar.
  const elFondo = fondoDeLaEscena(fondo, { sigue: sigueAqui, signal: oyentes.signal });
  elFondo.poner(estado.lugar.clave);
  monigoteDeLaEscena(monigote, () => estado.avatar, oyentes.signal)();

  // --- el diálogo ---------------------------------------------------------------------

  const frase = el('p', { class: 'aventura-frase', role: 'status' });
  const avanzar = el('button', { type: 'button', class: 'boton principal boton-avanzar', hidden: true });
  // El segundo clic de un doble clic no cuenta, como en tu departamento: si no,
  // tras «Seguir» o tras el encuentro, cuando el botón ya dice otra cosa, se
  // saltaría una frase. Un clic suelto y el teclado (que no cuenta clics), sí.
  avanzar.addEventListener('click', (evento) => {
    if (evento && evento.detail > 1) return;
    if (alAvanzar) alAvanzar();
  }, { signal: oyentes.signal });
  const volver = el('button', { type: 'button', class: 'boton boton-volver' }, 'Volver');
  volver.addEventListener('click', () => {
    if (!enCamino) irse();
  }, { signal: oyentes.signal });
  const dialogo = el('div', { class: 'aventura-dialogo' }, frase, avanzar, volver);

  const cuerpo = el('div', { class: 'cuerpo cuerpo-aventura' }, escena, dialogo, aviso.nodo);
  contenedor.append(cabecera, cuerpo);

  // El botón que avanza dice `texto` y hace `hacer`; se queda con el foco.
  function boton(texto, hacer) {
    avanzar.textContent = texto;
    alAvanzar = hacer;
    avanzar.hidden = false;
    avanzar.focus({ preventScroll: true });
  }

  // La frase en la que vas y, en el botón, lo que sigue: otra frase o, tras la
  // última, el encuentro (antes) o volver a tu departamento (después).
  function mostrar() {
    const ultima = cual >= frases.length - 1;
    frase.textContent = frases[cual] || '';
    frase.classList.remove('es-error');
    if (!ultima) boton(SEGUIR, otraFrase);
    else if (encontrado) boton(VOLVER_A_TU_DEPARTAMENTO, () => irse(encontrado));
    else boton(ACERCARTE, acercarte);
  }

  function otraFrase() {
    cual += 1;
    mostrar();
  }

  // Mientras el encuentro va, el botón espera y no se puede volver.
  function esperar(si) {
    avanzar.classList.toggle('esperando', si);
    if (si) {
      avanzar.setAttribute('aria-busy', 'true');
      volver.setAttribute('aria-disabled', 'true');
    } else {
      avanzar.removeAttribute('aria-busy');
      volver.removeAttribute('aria-disabled');
    }
  }

  function dejarDeEsperar() {
    enCamino = false;
    esperar(false);
  }

  // --- lo que dice la aventura -----------------------------------------------------------

  // Mientras llega, la tarjeta lo dice como lo dicen las demás pantallas su
  // carga, con el aro de siempre: se lee y se anuncia (la frase está en la zona
  // que se anuncia, y nada alrededor la calla). Al llegar o al fallar, se va.
  function esperarLaAventura(si) {
    frase.classList.toggle('esperando', si);
    // Al volver a intentarlo, lo que decía por qué no llegó ya no vale.
    frase.classList.remove('es-error');
    frase.textContent = si ? CARGANDO : '';
  }

  async function leer() {
    if (leyendo) return;
    leyendo = true;
    esperarLaAventura(true);
    let leida;
    try {
      leida = await pedir('GET', 'aventura');
    } catch (error) {
      leyendo = false;
      if (!sigueAqui()) return;
      esperarLaAventura(false);
      if (hayQueDecidirDeNuevo(error)) {
        irse();
        return;
      }
      // No llegó: se dice por qué, y el botón la vuelve a pedir.
      frase.textContent = mensajeDe(error);
      frase.classList.add('es-error');
      boton('Volver a intentarlo', leer);
      return;
    }
    leyendo = false;
    if (!sigueAqui()) return;
    esperarLaAventura(false);
    const primera = leida && leida.primera;
    // Ya tienes uno, o la cama ya no está libre: lo dice el lugar.
    if (!primera || !primera.puede) {
      irse();
      return;
    }
    frases = Array.isArray(primera.antes) ? primera.antes : [];
    cual = 0;
    mostrar();
  }

  // --- el encuentro ----------------------------------------------------------------------

  async function acercarte() {
    if (enCamino) return;
    enCamino = true;
    esperar(true);
    aviso.avisar('');
    let respuesta;
    try {
      respuesta = await pedir('POST', 'aventura/primera');
    } catch (error) {
      if (!sigueAqui()) return;
      if (error && error.estado === 409) {
        await trasUnNo(error);
        return;
      }
      dejarDeEsperar();
      if (error && error.estado === 401) {
        irse();
        return;
      }
      // Pudo haber llegado igual: si se vuelve a pulsar y ya lo tienes, el
      // servidor dice que no y se sigue con el estado.
      aviso.avisar(error && error.clave === null ? SIN_RESPUESTA : mensajeDe(error), true);
      avanzar.focus({ preventScroll: true });
      return;
    }
    if (!sigueAqui()) return;
    dejarDeEsperar();
    encontrado = respuesta.estado;
    volver.hidden = true;
    verAlGachamon(encontrado && encontrado.gachamon);
    frases = Array.isArray(respuesta.despues) ? respuesta.despues : [];
    cual = 0;
    mostrar();
  }

  // Cualquier «no» del encuentro: se relee el estado y se sigue con él si ya
  // tienes uno. Si sigues sin ninguno, se dice la frase del servidor y sólo
  // queda volver al lugar.
  async function trasUnNo(no) {
    let releido;
    try {
      releido = await pedir('GET', 'estado');
    } catch (error) {
      if (!sigueAqui()) return;
      dejarDeEsperar();
      // Sin sesión, o el servidor tampoco deja leer: se vuelve a decidir.
      if (hayQueDecidirDeNuevo(error)) {
        irse();
        return;
      }
      aviso.avisar(error && error.clave === null ? SIN_RESPUESTA : mensajeDe(error), true);
      avanzar.focus({ preventScroll: true });
      return;
    }
    if (!sigueAqui()) return;
    if (releido && releido.gachamon) {
      irse(releido);
      return;
    }
    // El botón que avanza se va: no queda ningún encuentro que mandar.
    esperar(false);
    alAvanzar = null;
    avanzar.hidden = true;
    frase.textContent = mensajeDe(no);
    volver.focus({ preventScroll: true });
    enCamino = false;
  }

  // Su retrato en la escena, del tamaño de su etapa. Quién es lo dice la frase:
  // el dibujo no se lee. Si no carga, su emoji.
  function verAlGachamon(g) {
    if (!g) return;
    escena.dataset.etapa = g.etapa;
    const retrato = el('img', { class: 'retrato', src: g.retrato, alt: '', draggable: 'false' });
    const sinRetrato = el('span', { class: 'retrato-sin', hidden: true }, g.emoji);
    retrato.addEventListener('error', () => {
      retrato.hidden = true;
      sinRetrato.hidden = false;
    });
    escena.append(el('div', { class: 'aventura-gachamon', 'aria-hidden': 'true' }, retrato, sinRetrato));
  }

  return leer();
}
