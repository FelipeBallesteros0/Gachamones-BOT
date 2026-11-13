// Arranca el cliente: pregunta quién eres, cómo va tu cuenta y tu juego, y
// pinta la pantalla que toque.

import { pedir, versiones } from './api.js';
import * as entrada from './entrada.js';
import { lugar } from './lugar.js';
import { pueblo } from './mapa.js';
import { mochila } from './mochila.js';
import { hayQueRecargar, siguiente, trasUnFalloAlArrancar } from './pantallas.js';
import { tienda } from './tienda.js';

const contenedor = document.getElementById('juego');

// La versión del servidor por la que esta pestaña ya se recargó una vez.
const RECARGADA = 'gachamon-recargada';

const PANTALLAS = {
  sesion: entrada.sesion,
  bienvenida: entrada.bienvenida,
  avatar: entrada.avatar,
  difunto: entrada.difunto,
  huevo: entrada.huevo,
  bautizo: entrada.bautizo,
  lugar: (destino, seguir, { estado, llegando }) => lugar(destino, estado, seguir, llegando),
  pueblo: (destino, seguir, { estado }) => pueblo(destino, estado, seguir),
  tienda: (destino, seguir, { estado }) => tienda(destino, estado, seguir),
  mochila: (destino, seguir, { estado }) => mochila(destino, estado, seguir),
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

// Tras un despliegue, los archivos de esta página ya no existen en el servidor:
// al cambiar de pantalla, y una sola vez por versión, se recarga y anota que
// lo hizo. Sin `sessionStorage` no se puede anotar, y no se recarga.
function recargarSiEsDeOtraVersion() {
  const { propia, delServidor } = versiones();
  try {
    if (!hayQueRecargar(propia, delServidor, sessionStorage.getItem(RECARGADA))) return false;
    sessionStorage.setItem(RECARGADA, delServidor);
  } catch {
    return false;
  }
  location.reload();
  return true;
}

// Cada decisión lleva su número: si mientras se pregunta empieza otra, la vieja
// ya no pinta nada.
let vuelta = 0;
let conocido = { sesion: null, cuenta: null };

// `opciones.vista` (`'pueblo'`, `'tienda'`, `'mochila'` o nada) es lo que se
// quiere ver si todo está en orden, y `opciones.llegando`, que se acaba de
// llegar caminando. Valen sólo para esta llamada: `seguir()` a secas vuelve
// al lugar.
async function seguir(estadoNuevo, opciones) {
  const { vista, llegando } = opciones || {};
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
  if (recargarSiEsDeOtraVersion()) return;
  pintar(siguiente(datos.sesion, datos.cuenta, datos.estado, vista), { ...datos, llegando: llegando === true });
}

// Al volver con «atrás» desde Rowino, la página puede salir de la caché del
// navegador tal como estaba: se vuelve a preguntar.
window.addEventListener('pageshow', (evento) => {
  if (evento.persisted) seguir();
});

seguir();
