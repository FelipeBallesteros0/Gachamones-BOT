// La página del dibujante (`/monsteropolis_dibujante/`): las piezas del arte por
// grupos, cada una con su imagen de ahora, su nombre, lo que tiene que medir y
// si se ve el recuadro provisional o una imagen subida (por quién y cuándo).
// Desde cada pieza se sube un PNG, se vuelve a la anterior o al provisional y se
// mira su historial; arriba se descarga todo lo subido. Sólo la ven el dueño y
// el dibujante: a los demás, el servidor les contesta que no existe.
//
// Es una herramienta para dos personas: clara antes que bonita. Qué vale, qué
// medida se pide y qué queda puesto lo decide el servidor; aquí sólo se enseña.

import { urlDeArte } from './arte.js';
import { el } from './dom.js';

const BASE = '/monsteropolis_dibujante/api/';

// Las mismas frases que `api.js` para cuando no llega una respuesta del juego.
const SIN_RED = 'No hay conexión con el juego. Revisa tu internet y vuelve a intentarlo.';
const SIN_RESPUESTA = 'El juego no contestó. Vuelve a intentarlo en un momento.';

const LISTO = 'Listo: ya se ve en el juego.';
const BOTONES = {
  subir: 'Subir',
  historial: 'Historial',
  anterior: 'Volver a la anterior',
  provisional: 'Volver al provisional',
};

// Lo que contesta la api del dibujante; si no sale bien, lanza `{mensaje}` con
// la frase del servidor o, si la respuesta no es del juego, la de siempre.
async function pedir(metodo, ruta, cuerpo, tipo) {
  const opciones = { method: metodo, headers: {}, credentials: 'same-origin' };
  if (cuerpo !== undefined) {
    opciones.headers['Content-Type'] = tipo;
    opciones.body = cuerpo;
  }
  if (metodo !== 'GET') opciones.headers['X-Gachamon'] = '1';
  let respuesta;
  try {
    respuesta = await fetch(BASE + ruta, opciones);
  } catch {
    throw { mensaje: SIN_RED };
  }
  let datos = null;
  try {
    datos = await respuesta.json();
  } catch {
    datos = null;
  }
  if (respuesta.ok && datos !== null && typeof datos === 'object') return datos;
  const detalle = datos && typeof datos.detail === 'object' ? datos.detail : null;
  throw { mensaje: detalle && typeof detalle.mensaje === 'string' ? detalle.mensaje : SIN_RESPUESTA };
}

// --- las frases -----------------------------------------------------------------------

const dosCifras = (n) => String(n).padStart(2, '0');

// «20/11/2026 15:04», en la hora de quien mira.
export function fecha(iso) {
  const cuando = new Date(iso);
  if (Number.isNaN(cuando.getTime())) return String(iso);
  return `${dosCifras(cuando.getDate())}/${dosCifras(cuando.getMonth() + 1)}/${cuando.getFullYear()} `
    + `${dosCifras(cuando.getHours())}:${dosCifras(cuando.getMinutes())}`;
}

// Lo que tiene que medir el PNG; en la familia de la pieza vale también su original, al doble.
export function medidaDe(pieza) {
  const exacta = `${pieza.ancho} × ${pieza.alto} px`;
  if (!pieza.original) return exacta;
  return `${exacta} o ${pieza.original.ancho} × ${pieza.original.alto} px`;
}

export function estadoDe(pieza) {
  if (!pieza.subida) return 'Provisional';
  return `Subida por ${pieza.subida.quien} el ${fecha(pieza.subida.cuando)}`;
}

// Lo que tiene puesto con una medida que el contrato ya no pide: no se sirve.
export function avisoDeMedida(pieza) {
  const medida = pieza.medida_cambiada;
  if (!medida) return null;
  return `Lo subido mide ${medida.ancho} × ${medida.alto} px y esta pieza ahora pide otra medida: se ve el provisional.`;
}

// Un renglón del historial: lo que se hizo (con el nombre de su botón), quién, cuándo y lo que mide.
export function renglonDelHistorial(renglon) {
  const partes = [BOTONES[renglon.accion] || renglon.accion, renglon.quien, fecha(renglon.cuando)];
  if (renglon.ancho && renglon.alto) partes.push(`${renglon.ancho} × ${renglon.alto} px`);
  return partes.join(' · ');
}

const imagenDe = (pieza) => (pieza.subida ? pieza.subida.direccion : urlDeArte(pieza.ruta));

// --- una pieza ------------------------------------------------------------------------

let historiales = 0;

// La tarjeta de una pieza. Sus botones no se rehacen nunca (el foco se queda donde
// estaba): lo que cambia se escribe en su sitio. Devuelve el nodo y si falta.
function tarjeta(pieza, familia) {
  let actual = pieza;
  let ocupada = false;
  historiales += 1;

  const imagen = el('img', {
    class: familia === 'pieza' ? 'dib-imagen' : 'dib-imagen dib-cuadros',
    src: imagenDe(pieza), alt: pieza.ruta, loading: 'lazy', decoding: 'async',
  });
  const estado = el('p', { class: 'dib-estado' });
  const cambiada = el('p', { class: 'dib-cambiada' });
  const aviso = el('p', { class: 'dib-aviso', role: 'status' });
  const lista = el('ol', { class: 'dib-historial', id: `dib-historial-${historiales}`, hidden: true });
  // Se abre con «Subir»: no se ve ni se enfoca, pero no va con `hidden`, que en algún
  // navegador de teléfono no deja abrir el selector desde el botón.
  const archivo = el('input', {
    type: 'file', accept: 'image/png', class: 'dib-archivo', tabindex: '-1', 'aria-hidden': 'true',
    onchange: alElegir,
  });

  const boton = (texto, alTocar, extra = {}) => el(
    'button', { type: 'button', class: 'boton boton-chico', onclick: alTocar, ...extra }, texto,
  );
  const subir = boton(BOTONES.subir, () => { if (!ocupada) archivo.click(); });
  const verHistorial = boton(BOTONES.historial, alternarHistorial, {
    'aria-expanded': 'false', 'aria-controls': lista.getAttribute('id'),
  });
  const anterior = boton(BOTONES.anterior, () => volver('anterior', anterior));
  const provisional = boton(BOTONES.provisional, () => volver('provisional', provisional));
  const queMandan = [subir, anterior, provisional];

  function avisar(texto, esError) {
    aviso.textContent = texto;
    aviso.classList.toggle('es-error', esError);
  }

  function pintar() {
    imagen.setAttribute('src', imagenDe(actual));
    estado.textContent = estadoDe(actual);
    const medida = avisoDeMedida(actual);
    cambiada.textContent = medida || '';
    cambiada.hidden = !medida;
  }

  // Mientras espera al servidor, lo que manda algo no se puede usar (sigue enfocable).
  function esperando(pulsado) {
    ocupada = pulsado !== null;
    for (const b of queMandan) {
      if (ocupada) b.setAttribute('aria-disabled', 'true');
      else b.removeAttribute('aria-disabled');
      if (b === pulsado) b.setAttribute('aria-busy', 'true');
      else b.removeAttribute('aria-busy');
    }
  }

  async function cambiar(pulsado, peticion, alSalirBien) {
    esperando(pulsado);
    try {
      actual = await peticion();
      pintar();
      avisar(alSalirBien(), false);
      // Lo que salió bien sigue dicho aunque releer el historial falle.
      if (!lista.hidden) await leerHistorial({ avisarSiFalla: false });
    } catch (error) {
      avisar(error && error.mensaje ? error.mensaje : SIN_RESPUESTA, true);
    } finally {
      esperando(null);
    }
  }

  async function alElegir() {
    const elegido = archivo.files && archivo.files[0];
    // Así se puede volver a elegir el mismo archivo.
    archivo.value = '';
    if (!elegido || ocupada) return;
    const ruta = `subir?ruta=${encodeURIComponent(actual.ruta)}`;
    await cambiar(subir, () => pedir('POST', ruta, elegido, 'image/png'), () => LISTO);
  }

  async function volver(a, pulsado) {
    if (ocupada) return;
    const cuerpo = JSON.stringify({ ruta: actual.ruta, a });
    await cambiar(pulsado, () => pedir('POST', 'volver', cuerpo, 'application/json'), () => estadoDe(actual));
  }

  async function leerHistorial({ avisarSiFalla = true } = {}) {
    try {
      const { historial } = await pedir('GET', `historial?ruta=${encodeURIComponent(actual.ruta)}`);
      lista.replaceChildren(...historial.map((renglon) => {
        // El provisional no tiene imagen: su sitio queda vacío, y los renglones alineados.
        let miniatura = el('span', { class: 'dib-miniatura', 'aria-hidden': 'true' });
        if (renglon.direccion) {
          // Una imagen que ya no se guarda deja su sitio vacío, sin el dibujo roto.
          miniatura = el('img', {
            class: 'dib-miniatura', src: renglon.direccion, alt: actual.ruta, loading: 'lazy',
            onerror: () => { miniatura.classList.add('dib-sin-imagen'); },
          });
        }
        return el('li', {}, miniatura, renglonDelHistorial(renglon));
      }));
    } catch (error) {
      if (avisarSiFalla) avisar(error && error.mensaje ? error.mensaje : SIN_RESPUESTA, true);
    }
  }

  async function alternarHistorial() {
    const abrir = lista.hidden;
    lista.hidden = !abrir;
    verHistorial.setAttribute('aria-expanded', String(abrir));
    if (abrir) await leerHistorial();
  }

  pintar();
  const nodo = el('li', { class: 'dib-pieza' },
    el('div', { class: 'dib-marco' }, imagen),
    el('p', { class: 'dib-ruta' }, pieza.ruta),
    el('p', { class: 'dib-medida' }, medidaDe(pieza)),
    estado, cambiada,
    el('div', { class: 'dib-botones' }, subir, verHistorial, anterior, provisional),
    archivo, aviso, lista);
  return { nodo, falta: () => !actual.subida };
}

// --- la página ------------------------------------------------------------------------

export async function montar(raiz) {
  const titulo = el('h1', {}, 'Arte de Criópolis');
  const estado = el('p', { class: 'cargando', role: 'status' }, 'Cargando…');
  raiz.replaceChildren(titulo, estado);
  let datos;
  try {
    datos = await pedir('GET', 'piezas');
  } catch (error) {
    estado.textContent = error.mensaje;
    estado.classList.add('es-error');
    return;
  }

  const grupos = datos.grupos.map((grupo) => {
    const tarjetas = grupo.piezas.map((pieza) => tarjeta(pieza, grupo.familia));
    const nodo = el('details', { class: 'dib-grupo' },
      el('summary', {}, grupo.nombre),
      el('ul', { class: 'dib-piezas' }, tarjetas.map((t) => t.nodo)));
    return { nodo, tarjetas };
  });

  // Sólo se filtra al tocar el filtro: lo que se acaba de subir no se esfuma de
  // las manos de quien lo subió.
  const filtro = el('input', {
    type: 'checkbox',
    onchange: () => {
      for (const grupo of grupos) {
        for (const t of grupo.tarjetas) t.nodo.hidden = filtro.checked && !t.falta();
        grupo.nodo.hidden = grupo.tarjetas.every((t) => t.nodo.hidden);
      }
    },
  });

  raiz.replaceChildren(
    el('header', { class: 'dib-cabeza' },
      titulo,
      el('a', { class: 'boton boton-chico', href: `${BASE}copia.zip`, download: true }, 'Descargar lo que se ve')),
    el('label', { class: 'dib-filtro' }, filtro, 'Sólo lo que falta'),
    el('div', { class: 'dib-grupos' }, grupos.map((g) => g.nodo)),
  );
}

const pagina = typeof document !== 'undefined' && typeof document.getElementById === 'function'
  ? document.getElementById('dibujante') : null;
if (pagina) montar(pagina);
