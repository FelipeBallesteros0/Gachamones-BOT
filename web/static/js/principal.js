// Arranca el cliente: pregunta quién eres, cómo va tu cuenta y tu juego, y
// pinta la pantalla que toque.

import { pedir } from './api.js';
import { el } from './dom.js';
import * as entrada from './entrada.js';
import { siguiente } from './pantallas.js';

const contenedor = document.getElementById('juego');

// Provisional: la pantalla del lugar llega en la tarea siguiente.
function lugar(destino, seguir, { sesion, estado }) {
  const { gachamon } = estado;
  destino.append(
    entrada.barra(sesion.usuario),
    el('div', { class: 'cuerpo' },
      el('h1', { tabindex: '-1' }, `${gachamon.nombre} te espera`),
      el('div', { class: 'escena' }, el('img', { class: 'retrato', src: gachamon.retrato, alt: gachamon.nombre })),
      el('p', { class: 'entradilla' }, `Muy pronto podrás cuidar a ${gachamon.nombre} desde aquí.`),
    ),
  );
}

const PANTALLAS = {
  sesion: entrada.sesion,
  bienvenida: entrada.bienvenida,
  avatar: entrada.avatar,
  difunto: entrada.difunto,
  huevo: entrada.huevo,
  bautizo: entrada.bautizo,
  lugar,
  noCarga: entrada.noCarga,
};

async function leer() {
  let sesion;
  try {
    sesion = await pedir('GET', 'sesion');
  } catch (error) {
    if (error && error.estado === 401) return { sesion: null, cuenta: null, estado: null };
    throw error;
  }
  const cuenta = await pedir('GET', 'cuenta');
  const estado = cuenta.estado === 'nueva' ? null : await pedir('GET', 'estado');
  return { sesion, cuenta, estado };
}

// Si una pantalla revienta por un fallo nuestro, no se queda a medias ni en
// blanco: se ofrece volver a intentarlo.
function averia(error) {
  console.error(error);
  contenedor.replaceChildren();
  contenedor.dataset.pantalla = 'noCarga';
  entrada.noCarga(contenedor, seguir, { mensaje: null });
}

function pintar(pantalla, datos) {
  contenedor.replaceChildren();
  contenedor.dataset.pantalla = pantalla;
  try {
    const hecho = PANTALLAS[pantalla](contenedor, seguir, datos);
    if (hecho && typeof hecho.catch === 'function') hecho.catch(averia);
  } catch (error) {
    averia(error);
  }
  window.scrollTo(0, 0);
  // Quien usa un lector de pantalla oye dónde está.
  const titulo = contenedor.querySelector('h1');
  if (titulo) titulo.focus({ preventScroll: true });
}

// Cada decisión lleva su número: si mientras se pregunta empieza otra, la vieja
// ya no pinta nada.
let vuelta = 0;
let conocido = { sesion: null, cuenta: null };

async function seguir(estadoNuevo) {
  const esta = ++vuelta;
  let datos;
  const traeEstado = estadoNuevo && typeof estadoNuevo === 'object' && 'gachamon' in estadoNuevo;
  if (traeEstado && conocido.sesion && conocido.cuenta) {
    // Una acción acaba de devolver el estado: la sesión y la cuenta son las mismas.
    datos = { ...conocido, estado: estadoNuevo };
  } else {
    try {
      datos = await leer();
    } catch (error) {
      if (esta === vuelta) pintar('noCarga', { mensaje: error && error.mensaje });
      return;
    }
  }
  if (esta !== vuelta) return;
  conocido = { sesion: datos.sesion, cuenta: datos.cuenta };
  pintar(siguiente(datos.sesion, datos.cuenta, datos.estado), datos);
}

// Al volver con «atrás» desde Rowino, la página puede salir de la caché del
// navegador tal como estaba: se vuelve a preguntar.
window.addEventListener('pageshow', (evento) => {
  if (evento.persisted) seguir();
});

seguir();
