// El ropero: los sombreros y los títulos que tienes, y ponérselos o quitárselos
// al gachamon activo de un toque. No se pregunta antes: no cuesta nada y se
// deshace con otro toque.
//
// `ropero(contenedor, estado, seguir)` pinta la pantalla y pide lo que tienes
// (`GET ropero`). Las reglas son del servidor: qué tienes, qué lleva puesto y
// quién lleva cada pieza; aquí se pinta lo que dice. Cada toque manda la pieza
// y el gachamon que enseña el estado (el mismo en sus reintentos): si el activo
// ya es otro, el servidor no viste al relevo y la pantalla se vuelve a decidir.
// La respuesta trae el ropero y el estado al día, con los que se repinta, y su
// frase se dice en la zona de aviso. Si un toque se queda sin respuesta pudo
// haberse hecho igual: lo que se veía ya no vale, y el ropero se vuelve a
// pedir. Si lo que contesta pide otra pantalla (sin sesión, tu gachamon
// cambió) se vuelve a decidir con `seguir`. Al salir se deja de temporizar, y
// una respuesta que llega tarde no pinta ni llama a `seguir`. La cabecera, las
// filas, el aviso y la espera son los de `articulos.js`, como en la mochila.
// Todo texto entra por `el` o por `textContent`.

import { conReintentos, pedir } from './api.js';
import { olvidarLasQueFaltan } from './arte.js';
import {
  cabeceraConSaldos, filaDeArticulo, hayQueDecidirDeNuevo, linea, listaQueSePide, mensajeDe,
  pideOtraPantalla, zonaDeAviso,
} from './articulos.js';
import { el } from './dom.js';

const CARGANDO = 'Cargando el ropero…';
const VACIO = 'Tu ropero está vacío. Los sombreros y los títulos se compran en la tienda, con gemas.';
const SIN_RESPUESTA = 'No hubo respuesta. Revisa tu conexión.';

// Las secciones, por el tipo de cada pieza.
const SECCIONES = [
  { tipo: 'sombrero', nombre: 'Sombreros' },
  { tipo: 'titulo', nombre: 'Títulos' },
];

// El ícono de cada pieza, una del contrato del arte.
const iconoDe = (clave) => `iconos/cosmeticos/${clave}.png`;

function idDelGachamon(estado) {
  return estado && estado.gachamon ? estado.gachamon.id : null;
}

export function ropero(contenedor, estado, seguir) {
  // El arte que no cargó en otra pantalla se pide de nuevo.
  olvidarLasQueFaltan();
  let vivo = true;
  // Lo que contesta el juego, abajo de lo que se ve.
  const aviso = zonaDeAviso();
  const { avisar } = aviso;
  // El último estado que se conoce, para volver a la ficha con él.
  let actual = estado;
  // El gachamon que enseña el estado, al que va cada toque.
  let gachamonId = idDelGachamon(estado);
  // Mientras un toque está en camino no sale otro.
  let enCamino = false;

  function parar() {
    vivo = false;
    aviso.parar();
  }

  // Deja el ropero y que se decida otra pantalla: con lo que se le pase, o
  // preguntando todo otra vez.
  function irse(estadoNuevo, opciones) {
    parar();
    seguir(estadoNuevo, opciones);
  }

  // Si la pantalla ya no está en la página (se pintó otra), se para todo.
  function sigueAqui() {
    if (vivo && !cuerpo.isConnected) parar();
    return vivo;
  }

  // --- la pantalla -------------------------------------------------------------------

  const { cabecera, titulo, ponerSaldos } = cabeceraConSaldos('👒', 'Ropero');
  // Hasta que llega el ropero no hay lista: hay una frase.
  const espera = el('div', { class: 'espera-tienda' });
  const secciones = SECCIONES.map(({ tipo, nombre }) => {
    const filas = el('ul', { class: 'articulos' });
    const nodo = el('section', { class: 'seccion-ropero' }, el('h2', { class: 'tienda-subtitulo' }, nombre), filas);
    return { tipo, nodo, filas };
  });
  const vacio = el('p', { class: 'ropero-vacio' }, VACIO);
  const contenido = el('div', { class: 'contenido-ropero', hidden: true }, secciones.map((s) => s.nodo), vacio);
  const volver = el('button', { type: 'button', class: 'boton boton-volver' }, 'Volver');
  volver.addEventListener('click', () => irse(actual, { vista: 'ficha' }));
  const cuerpo = el('div', { class: 'cuerpo cuerpo-tienda cuerpo-ropero' }, espera, contenido, aviso.nodo, volver);
  contenedor.append(cabecera, cuerpo);

  // --- cada pieza: la puesta, la que lleva otro y las libres ------------------------

  // Se ve «Poner» o «Quitar» y se oye la pieza: «Poner Corona», «Quitar El
  // Invicto». Cada fila, distinta.
  function boton(queHace, clase, pieza) {
    const nodo = el('button', { type: 'button', class: clase },
      queHace, el('span', { class: 'solo-lector' }, ` ${pieza.nombre}`));
    nodo.addEventListener('click', () => mandar(pieza, nodo));
    return el('div', { class: 'accion' }, nodo);
  }

  function filaDe(pieza, quien) {
    let lineas = [];
    let accion = null;
    if (pieza.puesta) {
      lineas = [linea(`Lo lleva ${quien}.`, 'articulo-tienes')];
      accion = boton('Quitar', 'boton-quitar', pieza);
    } else if (pieza.lo_lleva) {
      lineas = [linea(`Lo lleva ${pieza.lo_lleva}.`, 'articulo-detalle')];
    } else {
      accion = boton('Poner', 'boton-poner', pieza);
    }
    return filaDeArticulo({
      id: pieza.clave,
      icono: iconoDe(pieza.clave),
      nombre: pieza.nombre,
      lineas,
      accion,
      apagada: !pieza.puesta && Boolean(pieza.lo_lleva),
    });
  }

  // Pinta el ropero entero; sin una pieza de un tipo, su sección no sale, y sin
  // ninguna, la frase del ropero vacío. El foco que estaba en una fila vuelve
  // a esa misma fila.
  function ponerElRopero(leido) {
    const conFoco = document.activeElement && contenido.contains(document.activeElement)
      ? document.activeElement.closest('[data-fila]') : null;
    ponerSaldos(leido.saldos);
    for (const { tipo, nodo, filas } of secciones) {
      const piezas = leido.piezas.filter((p) => p.tipo === tipo);
      filas.replaceChildren(...piezas.map((p) => filaDe(p, leido.gachamon.nombre)));
      nodo.hidden = !piezas.length;
    }
    vacio.hidden = Boolean(leido.piezas.length);
    if (conFoco) volverALaFila(conFoco.dataset.fila);
  }

  // El foco va al botón de esa fila; si ya no tiene (la lleva otro), al título.
  function enfocarLaFila(clave) {
    const fila = [...contenido.querySelectorAll('[data-fila]')].find((nodo) => nodo.dataset.fila === clave);
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
    ruta: 'ropero',
    espera,
    lista: contenido,
    cargando: CARGANDO,
    titulo,
    sigueAqui,
    irse: () => irse(),
    alLlegar(leido, trasReintentar) {
      // Lo que llega es de otro gachamon que el del estado: se vuelve a mirar.
      if (leido.gachamon.id !== gachamonId) {
        irse();
        return;
      }
      ponerElRopero(leido);
      if (trasReintentar) (contenido.querySelector('button') || titulo).focus({ preventScroll: true });
    },
  });

  // --- poner y quitar ------------------------------------------------------------------

  // Mientras va, esa fila espera y ningún otro botón manda nada. El cuerpo se
  // arma una vez, con el gachamon de la pantalla, y sus reintentos llevan el mismo.
  async function mandar(pieza, nodo) {
    if (enCamino) return;
    enCamino = true;
    const ruta = pieza.puesta ? 'ropero/quitar' : 'ropero/poner';
    const loQuePide = pieza.puesta ? { tipo: pieza.tipo } : { clave: pieza.clave };
    const datos = { ...loQuePide, gachamon_id: gachamonId };
    nodo.closest('[data-fila]').classList.add('en-camino');
    nodo.classList.add('esperando');
    nodo.setAttribute('aria-busy', 'true');
    for (const otro of contenido.querySelectorAll('.boton-poner, .boton-quitar')) otro.setAttribute('aria-disabled', 'true');
    avisar('');
    let respuesta;
    try {
      respuesta = await conReintentos(() => pedir('POST', ruta, datos), sigueAqui);
    } catch (error) {
      if (!sigueAqui()) return;
      enCamino = false;
      if (hayQueDecidirDeNuevo(error)) {
        irse();
        return;
      }
      // Pudo haberse hecho igual: lo que se ve ya no vale. Se dice, y el
      // ropero se vuelve a pedir; si tampoco llega, el ropero no carga.
      avisar(error && error.clave === null ? SIN_RESPUESTA : mensajeDe(error), true);
      if (await laLista.releer()) enfocarLaFila(pieza.clave);
      return;
    }
    if (!sigueAqui()) return;
    enCamino = false;
    if (respuesta.estado && pideOtraPantalla(respuesta.estado, 'ropero')) {
      irse(respuesta.estado);
      return;
    }
    if (respuesta.estado) {
      actual = respuesta.estado;
      gachamonId = idDelGachamon(respuesta.estado);
    }
    ponerElRopero(respuesta.ropero);
    avisar(respuesta.mensaje, !respuesta.ok);
    volverALaFila(pieza.clave);
  }

  ponerSaldos(estado.saldos);
  return laLista.cargar();
}
