// La mochila: lo que llevas, cada cosa con cuántas te quedan, y usarlo en dos
// toques: el primero pregunta y el segundo lo usa. La placa pide además el
// nombre nuevo, ahí mismo.
//
// `mochila(contenedor, estado, seguir)` pinta la pantalla y pide la lista
// (`GET mochila`). Las reglas son del servidor: qué llevas, qué se usa desde
// aquí (`uso`) y por qué no (`nota`); aquí se pinta lo que dice, y el nombre
// se manda tal cual, que lo valida él. Cada uso lleva su evento (el mismo en
// sus reintentos) y su respuesta trae la lista y el estado al día, con los que
// se repinta. Si un uso se queda sin respuesta pudo haberse hecho igual: lo
// que se veía ya no vale, y la lista se vuelve a pedir. Si lo que contesta
// pide otra pantalla (sin sesión, tu gachamon cambió) se vuelve a decidir con
// `seguir`. Al salir se deja de temporizar, y una respuesta que llega tarde no
// pinta ni llama a `seguir`. La cabecera, las filas, la pregunta, el aviso y
// la espera son los de `articulos.js`, como en la tienda. Todo texto entra por
// `el` o por `textContent`.

import { conReintentos, nuevoEvento, pedir } from './api.js';
import { olvidarLasQueFaltan } from './arte.js';
import {
  cabeceraConSaldos, cajaDePregunta, filaDeArticulo, hayQueDecidirDeNuevo, linea, listaQueSePide,
  mensajeDe, pideOtraPantalla, zonaDeAviso,
} from './articulos.js';
import { el } from './dom.js';

const CARGANDO = 'Cargando la mochila…';
const VACIA = 'Tu mochila está vacía. Lo que compres en la tienda aparece aquí.';
const SIN_RESPUESTA = 'No hubo respuesta. Revisa tu conexión.';

// Lo que se usa poniéndole un nombre nuevo al gachamon (la placa).
const CON_NOMBRE = 'con_nombre';

export function mochila(contenedor, estado, seguir) {
  // El arte que no cargó en otra pantalla se pide de nuevo.
  olvidarLasQueFaltan();
  let vivo = true;
  // Lo que contesta el juego, abajo de lo que se ve.
  const aviso = zonaDeAviso();
  const { avisar } = aviso;

  function parar() {
    vivo = false;
    aviso.parar();
  }

  // Deja la mochila y que se decida otra pantalla: con el estado que llegó, o
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

  // --- la pantalla -------------------------------------------------------------------

  const { cabecera, titulo, ponerSaldos } = cabeceraConSaldos('🎒', 'Mochila');
  // Hasta que llega la lista no hay lista: hay una frase.
  const espera = el('div', { class: 'espera-tienda' });
  // La lista, o la frase de la mochila vacía.
  const filas = el('ul', { class: 'articulos' });
  const vacia = el('p', { class: 'mochila-vacia' }, VACIA);
  const contenido = el('div', { class: 'contenido-mochila', hidden: true }, filas, vacia);
  const volver = el('button', { type: 'button', class: 'boton boton-volver' }, 'Volver');
  volver.addEventListener('click', () => irse());
  const cuerpo = el('div', { class: 'cuerpo cuerpo-tienda cuerpo-mochila' }, espera, contenido, aviso.nodo, volver);
  contenedor.append(cabecera, cuerpo);

  // --- lo que llevas: cada fila y, si se usa desde aquí, su botón -------------------

  // Cada botón «Usar», por la clave de su fila: `{sitio, boton, objeto}`.
  const usables = new Map();
  // La pregunta abierta: `{caja, cerrar}`; sólo una a la vez.
  let abierta = null;
  // Mientras un uso está en camino no sale otro.
  let enCamino = false;

  // «Poción de comida × 2», con espacios que no se cortan: la cantidad no se
  // queda sola en otra línea. Debajo, lo que hace o, si no se usa desde aquí,
  // por qué.
  function filaDe(objeto) {
    let accion = null;
    if (objeto.uso) {
      const boton = el('button', { type: 'button', class: 'boton-usar' }, 'Usar');
      accion = el('div', { class: 'accion' }, boton);
      const usable = { sitio: accion, boton, objeto };
      usables.set(objeto.clave, usable);
      boton.addEventListener('click', () => preguntar(usable));
    }
    return filaDeArticulo({
      id: objeto.clave,
      icono: objeto.icono,
      nombre: `${objeto.nombre} × ${objeto.cantidad}`,
      lineas: [objeto.nota ? linea(objeto.nota, 'articulo-nota') : linea(objeto.descripcion, 'articulo-detalle')],
      accion,
    });
  }

  // Pinta la lista entera y cierra la pregunta abierta. El foco que estaba en
  // una fila vuelve a esa misma fila.
  function ponerLaLista(objetos) {
    const conFoco = document.activeElement && filas.contains(document.activeElement)
      ? document.activeElement.closest('[data-fila]') : null;
    abierta = null;
    usables.clear();
    filas.replaceChildren(...objetos.map(filaDe));
    filas.hidden = !objetos.length;
    vacia.hidden = Boolean(objetos.length);
    if (conFoco) volverALaFila(conFoco.dataset.fila);
  }

  // El foco va al botón de esa fila; si ya no está (se usó la última), al título.
  function enfocarLaFila(clave) {
    const fila = [...filas.querySelectorAll('[data-fila]')].find((nodo) => nodo.dataset.fila === clave);
    const destino = fila ? fila.querySelector('button') : null;
    (destino || titulo).focus({ preventScroll: true });
  }

  // Tras repintar, el foco que se quedó sin sitio vuelve a la misma fila.
  function volverALaFila(clave) {
    const activo = document.activeElement;
    if (activo && activo !== document.body && activo.isConnected) return;
    enfocarLaFila(clave);
  }

  const laLista = listaQueSePide({
    ruta: 'mochila',
    espera,
    lista: contenido,
    cargando: CARGANDO,
    titulo,
    sigueAqui,
    irse,
    alLlegar(leida, trasReintentar) {
      ponerLaLista(leida.objetos);
      if (trasReintentar) (filas.querySelector('button') || titulo).focus({ preventScroll: true });
    },
  });

  // --- usar en dos toques ------------------------------------------------------------

  function cerrarLaPregunta() {
    if (abierta) abierta.cerrar();
    abierta = null;
  }

  // El primer toque: el botón se cambia por la pregunta, «¿Usar?» con «Usar» y
  // «No», y el foco va a la pregunta, que se lee; no al botón que confirma,
  // para que una tecla que se queda apretada no lo gaste. Con la placa, en vez
  // de la pregunta, el campo del nombre nuevo (con `nombre` ya escrito, si lo
  // hay), que es donde va el foco; Enter en él también lo confirma.
  function preguntar(usable, nombre = '') {
    if (enCamino) return;
    cerrarLaPregunta();
    const { sitio, boton, objeto } = usable;
    const desistir = () => {
      if (enCamino) return;
      cerrarLaPregunta();
      boton.focus({ preventScroll: true });
    };
    let pregunta = '¿Usar?';
    let confirmar = 'Usar';
    let campo = null;
    if (objeto.uso === CON_NOMBRE) {
      campo = el('input', {
        id: 'mochila-nombre', class: 'texto', name: 'nombre', type: 'text',
        autocomplete: 'off', autocapitalize: 'words', spellcheck: 'false', enterkeyhint: 'done',
      });
      campo.value = nombre;
      pregunta = el('form', { class: 'campo pregunta-campo' },
        el('label', { class: 'etiqueta', for: 'mochila-nombre' }, 'Nuevo nombre'),
        campo);
      pregunta.addEventListener('submit', (evento) => {
        evento.preventDefault();
        mandar(usable, si, no, campo);
      });
      confirmar = 'Cambiar nombre';
    }
    const {
      caja, cabeza, si, no,
    } = cajaDePregunta(pregunta, confirmar, {
      alConfirmar: () => mandar(usable, si, no, campo),
      alDesistir: desistir,
    });
    sitio.replaceChildren(caja);
    sitio.classList.add('abierta');
    abierta = {
      caja,
      cerrar() {
        sitio.replaceChildren(boton);
        sitio.classList.remove('abierta');
      },
    };
    (campo || cabeza).focus({ preventScroll: true });
  }

  // El segundo toque: lo usa. Mientras va, esa fila espera y ningún otro botón
  // usa nada. Un toque, un evento: sus reintentos llevan el mismo.
  async function mandar(usable, si, no, campo) {
    if (enCamino) return;
    enCamino = true;
    const { clave } = usable.objeto;
    const datos = campo ? { clave, nombre: campo.value } : { clave };
    usable.sitio.closest('[data-fila]').classList.add('en-camino');
    si.classList.add('esperando');
    si.setAttribute('aria-busy', 'true');
    no.setAttribute('aria-disabled', 'true');
    if (campo) campo.readOnly = true;
    for (const boton of filas.querySelectorAll('.boton-usar')) boton.setAttribute('aria-disabled', 'true');
    avisar('');
    const evento = nuevoEvento();
    let respuesta;
    try {
      respuesta = await conReintentos(() => pedir('POST', 'mochila/usar', { ...datos, evento_id: evento }), sigueAqui);
    } catch (error) {
      if (!sigueAqui()) return;
      enCamino = false;
      if (hayQueDecidirDeNuevo(error)) {
        irse();
        return;
      }
      // Pudo haberse usado igual: lo que se ve ya no vale. Se dice, y la
      // lista se vuelve a pedir; si tampoco llega, la mochila no carga.
      avisar(error && error.clave === null ? SIN_RESPUESTA : mensajeDe(error), true);
      if (await laLista.releer()) enfocarLaFila(clave);
      return;
    }
    if (!sigueAqui()) return;
    enCamino = false;
    if (respuesta.estado && pideOtraPantalla(respuesta.estado, 'mochila')) {
      irse(respuesta.estado);
      return;
    }
    if (respuesta.estado) ponerSaldos(respuesta.estado.saldos);
    ponerLaLista(respuesta.mochila.objetos);
    avisar(respuesta.mensaje, !respuesta.ok);
    // Un «no» a la placa (un nombre que no vale, el mismo de antes) deja el
    // campo abierto con lo que se escribió, para corregirlo.
    if (!respuesta.ok && campo && usables.has(clave)) preguntar(usables.get(clave), datos.nombre);
    else volverALaFila(clave);
  }

  ponerSaldos(estado.saldos);
  return laLista.cargar();
}
