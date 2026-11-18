// La primera aventura: donde quien todavía no tiene ningún gachamon gana el
// primero. Se llega desde el lugar «Aventura», que la ofrece, como a la Tienda
// desde el suyo (`seguir` con la vista `'aventura'`).
//
// `aventura(contenedor, estado, seguir)` pinta la escena del lugar donde estás,
// con tu avatar, y pide lo que dice la aventura (`GET aventura`): si se puede y
// las frases de antes. Las frases las manda el servidor y entran tal cual.
// Mientras llegan, el diálogo espera (`aria-busy`); si no llegan, se dice por
// qué y el botón la vuelve a pedir. Si al llegar ya no se puede (ya tienes uno,
// o la cama ya no está libre), se vuelve a decidir la pantalla: el lugar lo dice.
//
// El diálogo va de a una frase, en una zona que se anuncia (`role="status"`),
// con un solo botón que avanza y que se queda con el foco: «Seguir» y, tras la
// tercera, «Acercarte», que manda el encuentro (`POST aventura/primera`) una
// sola vez: mientras va, otro toque no manda nada (no se apaga con `disabled`,
// para no perder el foco). Con la respuesta se ve a tu gachamon (su retrato:
// quién es lo dice la frase) y las frases de después, y tras la última,
// «Volver a casa», que sigue con el estado que llegó (toca el paso del nombre).
// Sin respuesta se dice lo de siempre y «Acercarte» se puede volver a pulsar.
// Ante cualquier «no» del encuentro (un 409) se vuelve a leer el estado y se
// sigue con él: lo normal es que ya lo tengas (un doble clic, otra pestaña: el
// encuentro ya te llevó a casa). Sólo si sigues sin ninguno se dice la frase
// del servidor y queda «Volver». Antes del encuentro, «Volver» deja la aventura
// sin guardar nada. Lo que entra en la escena lo anima el estilo, que con
// movimiento reducido no anima nada. Al salir se deja de escuchar, y una
// respuesta que llega tarde no pinta ni llama a `seguir`. Todo texto entra por
// `el` o por `textContent`.

import { pedir } from './api.js';
import { cargar, faltante, olvidarLasQueFaltan } from './arte.js';
import { hayQueDecidirDeNuevo, mensajeDe, zonaDeAviso } from './articulos.js';
import { lienzoDelAvatar } from './avatar.js';
import { el } from './dom.js';

const TITULO = 'La primera aventura';
const SEGUIR = 'Seguir';
const ACERCARTE = 'Acercarte';
const VOLVER_A_CASA = 'Volver a casa';
const SIN_RESPUESTA = 'No hubo respuesta. Revisa tu conexión.';
// Lo que mide de alto el avatar en la escena, en píxeles de pantalla, como en el lugar.
const ALTO_DEL_AVATAR = 126;
const ALTO_DEL_AVATAR_EN_COMPUTADOR = 168;
const DENSIDAD_MAXIMA = 3;

// El fondo de la escena de cada lugar, una pieza del contrato del arte (el mismo del lugar).
const escenaDe = (clave) => `escenas/${clave}.png`;

export function aventura(contenedor, estado, seguir) {
  // El arte que no cargó en otra pantalla se pide de nuevo.
  olvidarLasQueFaltan();
  let vivo = true;
  const oyentes = new AbortController();
  let observador = null;

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
    if (observador) observador.disconnect();
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

  // --- el diálogo ---------------------------------------------------------------------

  const frase = el('p', { class: 'aventura-frase', role: 'status' });
  const avanzar = el('button', { type: 'button', class: 'boton principal boton-avanzar', hidden: true });
  avanzar.addEventListener('click', () => {
    if (alAvanzar) alAvanzar();
  }, { signal: oyentes.signal });
  const volver = el('button', { type: 'button', class: 'boton boton-volver' }, 'Volver');
  volver.addEventListener('click', () => {
    if (!enCamino) irse();
  }, { signal: oyentes.signal });
  const dialogo = el('div', { class: 'aventura-dialogo', 'aria-busy': 'true' }, frase, avanzar, volver);

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
  // última, el encuentro (antes) o volver a casa (después).
  function mostrar() {
    const ultima = cual >= frases.length - 1;
    frase.textContent = frases[cual] || '';
    frase.classList.remove('es-error');
    if (!ultima) boton(SEGUIR, otraFrase);
    else if (encontrado) boton(VOLVER_A_CASA, () => irse(encontrado));
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

  async function leer() {
    if (leyendo) return;
    leyendo = true;
    dialogo.setAttribute('aria-busy', 'true');
    let leida;
    try {
      leida = await pedir('GET', 'aventura');
    } catch (error) {
      leyendo = false;
      if (!sigueAqui()) return;
      dialogo.removeAttribute('aria-busy');
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
    dialogo.removeAttribute('aria-busy');
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
      if (error && error.estado === 401) {
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

  // --- el fondo de la escena y tu avatar ----------------------------------------------------

  // La pieza del lugar, cuando ya llegó: `{ruta, imagen}`, con `imagen` en
  // `null` si no se pudo cargar (se ve su recuadro).
  let piezaDelFondo = null;

  // El dibujo cubre toda la escena sin deformarse, como en el lugar: se
  // recorta por igual lo que sobra; sin suavizar, que es un dibujo de cuadros.
  function dibujarFondo() {
    const ancho = fondo.clientWidth;
    const alto = fondo.clientHeight;
    if (!ancho || !alto || !piezaDelFondo) return;
    const densidad = Math.min(Math.max(window.devicePixelRatio || 1, 1), DENSIDAD_MAXIMA);
    const anchoReal = Math.round(ancho * densidad);
    const altoReal = Math.round(alto * densidad);
    if (fondo.width !== anchoReal) fondo.width = anchoReal;
    if (fondo.height !== altoReal) fondo.height = altoReal;
    const ctx = fondo.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, anchoReal, altoReal);
    const { imagen } = piezaDelFondo;
    if (!imagen) {
      faltante(ctx, 0, 0, anchoReal, altoReal, piezaDelFondo.ruta);
      return;
    }
    const escala = Math.max(anchoReal / imagen.naturalWidth, altoReal / imagen.naturalHeight);
    const anchoVisto = anchoReal / escala;
    const altoVisto = altoReal / escala;
    ctx.drawImage(imagen,
      (imagen.naturalWidth - anchoVisto) / 2, (imagen.naturalHeight - altoVisto) / 2, anchoVisto, altoVisto,
      0, 0, anchoReal, altoReal);
  }

  cargar(escenaDe(estado.lugar.clave)).then((cargada) => {
    if (!sigueAqui()) return;
    piezaDelFondo = cargada;
    dibujarFondo();
  });
  // La escena cambia de tamaño al girar el teléfono o la ventana.
  if (typeof ResizeObserver === 'function') {
    observador = new ResizeObserver(dibujarFondo);
    observador.observe(fondo);
  } else {
    window.addEventListener('resize', dibujarFondo, { signal: oyentes.signal });
  }

  // En el computador el monigote se ve más grande.
  const ancho = window.matchMedia('(min-width: 900px)');
  const repintarMonigote = () => lienzoDelAvatar(
    monigote, estado.avatar, ancho.matches ? ALTO_DEL_AVATAR_EN_COMPUTADOR : ALTO_DEL_AVATAR,
  );
  ancho.addEventListener('change', repintarMonigote, { signal: oyentes.signal });
  repintarMonigote();

  return leer();
}
