// Arranca el cliente: pregunta quién eres, cómo va tu cuenta y tu juego, y
// pinta la pantalla que toque.

import { pedir } from './api.js';
import * as entrada from './entrada.js';
import { lugar } from './lugar.js';
import { siguiente, trasUnFalloAlArrancar } from './pantallas.js';

const contenedor = document.getElementById('juego');

const PANTALLAS = {
  sesion: entrada.sesion,
  bienvenida: entrada.bienvenida,
  avatar: entrada.avatar,
  difunto: entrada.difunto,
  huevo: entrada.huevo,
  bautizo: entrada.bautizo,
  lugar: (destino, seguir, { estado }) => lugar(destino, estado, seguir),
  noCarga: entrada.noCarga,
};

const SIN_SESION = { sesion: null, cuenta: null, estado: null };

// Las tres lecturas del arranque. Si una falla, `trasUnFalloAlArrancar` dice
// qué toca: un 401 en cualquiera de ellas es ir a entrar.
async function leer() {
  const sesion = await pedir('GET', 'sesion');
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
      const fallo = trasUnFalloAlArrancar(error);
      if (fallo.pantalla !== 'sesion') {
        if (esta === vuelta) pintar('noCarga', { mensaje: fallo.mensaje });
        return;
      }
      datos = SIN_SESION;
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
