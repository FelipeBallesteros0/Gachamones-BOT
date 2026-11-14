// La incubadora: tu plantel entero, cada gachamon con su retrato, y sacar a
// otro de un toque o ponerle nombre a un recluta ahí mismo. Sacar no se
// pregunta antes: no cuesta nada y se deshace con otro toque.
//
// `incubadora(contenedor, estado, seguir)` pinta la pantalla y pide el plantel
// (`GET incubadora`). Las reglas son del servidor: quién está, quién es el
// activo, a quién se puede sacar y qué nombre vale; aquí se pinta lo que dice,
// y el nombre se manda tal cual. Cada toque manda el gachamon de su fila (el
// mismo en sus reintentos), y mientras uno está en camino no sale otro. Sacar
// contesta con el plantel y el estado al día, con los que se repinta, y su
// frase se dice en la zona de aviso. Bautizar contesta con el estado, y el
// plantel se vuelve a pedir sin esconder el que se ve; un bautizo que ya
// estaba hecho (llegó un envío anterior) es un sí. Si un toque se queda sin
// respuesta pudo haberse hecho igual: lo que se veía ya no vale, y el plantel
// se vuelve a pedir. Si lo que contesta pide otra pantalla (sin sesión, ya no
// estás en la incubadora, un difunto) se vuelve a decidir con `seguir`; y
// también si el plantel que llega tiene otro activo que el del estado (cambió
// en otra pestaña o en Discord). Al salir se deja de temporizar, y una
// respuesta que llega tarde no pinta ni llama a `seguir`. La cabecera, las
// filas, la pregunta, el aviso y la espera son los de `articulos.js`, como en
// la mochila. Todo texto entra por `el` o por `textContent`.

import { conReintentos, pedir } from './api.js';
import { olvidarLasQueFaltan } from './arte.js';
import {
  cabeceraConSaldos, cajaDePregunta, filaDeArticulo, hayQueDecidirDeNuevo, linea, listaQueSePide,
  mensajeDe, pideOtraPantalla, zonaDeAviso,
} from './articulos.js';
import { el } from './dom.js';

const CARGANDO = 'Cargando la incubadora…';
const SIN_RESPUESTA = 'No hubo respuesta. Revisa tu conexión.';
const SIN_NOMBRE = 'Sin nombre';
// Lo más largo que puede ser un nombre, como en el bautizo de siempre.
const LARGO_DEL_NOMBRE = 24;

function idDelGachamon(estado) {
  return estado && estado.gachamon ? estado.gachamon.id : null;
}

const nombreDe = (g) => (g.sin_nombre ? SIN_NOMBRE : g.nombre);

export function incubadora(contenedor, estado, seguir) {
  // El arte que no cargó en otra pantalla se pide de nuevo.
  olvidarLasQueFaltan();
  let vivo = true;
  // Lo que contesta el juego, abajo de lo que se ve.
  const aviso = zonaDeAviso();
  const { avisar } = aviso;
  // El activo que enseña el estado: el plantel que llega tiene que decir lo mismo.
  let gachamonId = idDelGachamon(estado);
  // Mientras un toque está en camino no sale otro.
  let enCamino = false;

  function parar() {
    vivo = false;
    aviso.parar();
  }

  // Deja la incubadora y que se decida otra pantalla: con el estado que llegó,
  // o preguntando todo otra vez.
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

  const { cabecera, titulo, ponerSaldos } = cabeceraConSaldos('🥚', 'Incubadora');
  // Hasta que llega el plantel no hay lista: hay una frase.
  const espera = el('div', { class: 'espera-tienda' });
  const filas = el('ul', { class: 'articulos' });
  // Bajo la lista, con un solo gachamon, para qué sirve esto; y siempre, cuántos caben.
  const soloUno = el('p', { class: 'incubadora-nota', hidden: true });
  const caben = el('p', { class: 'incubadora-nota' });
  const contenido = el('div', { class: 'contenido-incubadora', hidden: true }, filas, soloUno, caben);
  const volver = el('button', { type: 'button', class: 'boton boton-volver' }, 'Volver');
  volver.addEventListener('click', () => irse());
  const cuerpo = el('div', { class: 'cuerpo cuerpo-tienda cuerpo-incubadora' }, espera, contenido, aviso.nodo, volver);
  contenedor.append(cabecera, cuerpo);

  // --- cada gachamon: el activo, los que se pueden sacar y los que esperan nombre -------

  // Las filas con «Ponerle nombre», por el id de su gachamon: `{sitio, boton, gachamon}`.
  const sinNombre = new Map();
  // El campo del nombre abierto: `{cerrar}`; sólo uno a la vez.
  let abierta = null;
  // El último plantel pintado, para dejarlo como estaba si un nombre no vale.
  let ultimo = null;

  // Se ve «Sacar» o «Ponerle nombre» y se oye a quién: «Sacar a Pelusa»,
  // «Ponerle nombre a Pollito». Cada fila, distinta.
  function boton(queHace, clase, aQuien) {
    const nodo = el('button', { type: 'button', class: clase },
      queHace, el('span', { class: 'solo-lector' }, ` a ${aQuien}`));
    return { nodo, sitio: el('div', { class: 'accion' }, nodo) };
  }

  // El retrato no se lee: su nombre va al lado.
  function filaDe(g) {
    let accion;
    if (g.activo) {
      accion = el('div', { class: 'accion' }, el('span', { class: 'marca-activo' }, 'Activo'));
    } else if (g.sin_nombre) {
      const { nodo, sitio } = boton('Ponerle nombre', 'boton-nombrar', g.nombre_especie);
      const fila = { sitio, boton: nodo, gachamon: g };
      sinNombre.set(g.id, fila);
      nodo.addEventListener('click', () => preguntarElNombre(fila));
      accion = sitio;
    } else {
      const { nodo, sitio } = boton('Sacar', 'boton-sacar', g.nombre);
      nodo.addEventListener('click', () => sacar(g, nodo));
      accion = sitio;
    }
    const retrato = el('img', {
      class: 'articulo-icono retrato-plantel', src: g.retrato, alt: '', draggable: 'false',
    });
    return filaDeArticulo({
      id: g.id,
      icono: retrato,
      nombre: nombreDe(g),
      lineas: [linea(`${g.nombre_especie} ${g.nombre_etapa} · nivel ${g.nivel}`, 'articulo-detalle')],
      accion,
    });
  }

  // Pinta el plantel entero y cierra el campo abierto. El foco que estaba en
  // una fila vuelve a esa misma fila.
  function ponerElPlantel(leido) {
    const conFoco = document.activeElement && filas.contains(document.activeElement)
      ? document.activeElement.closest('[data-fila]') : null;
    ultimo = leido;
    abierta = null;
    sinNombre.clear();
    ponerSaldos(leido.saldos);
    filas.replaceChildren(...leido.plantel.map(filaDe));
    const [unico] = leido.plantel;
    soloUno.hidden = leido.plantel.length !== 1;
    soloUno.textContent = leido.plantel.length === 1
      ? `Aquí esperan los gachamones que no son el activo. Ahora sólo tienes a ${nombreDe(unico)}.`
      : '';
    caben.textContent = `Caben ${leido.maximo} gachamones.`;
    if (conFoco) volverALaFila(conFoco.dataset.fila);
  }

  // Tras sacar a uno sin respuesta, el activo pudo pasar a ser ése: hasta la
  // siguiente lectura, también vale.
  let pudoSalir = null;

  // El plantel que llega tiene que tener de activo al del estado (o al que se
  // sacó sin respuesta); si no, se vuelve a decidir.
  function esElMismoActivo(leido) {
    const activo = leido.plantel.find((g) => g.activo);
    if (activo && activo.id === pudoSalir) gachamonId = activo.id;
    pudoSalir = null;
    if (!activo || activo.id !== gachamonId) {
      irse();
      return false;
    }
    return true;
  }

  // El foco va al botón de esa fila; si ya no tiene (es el activo), al título.
  function enfocarLaFila(id) {
    const fila = [...filas.querySelectorAll('[data-fila]')].find((nodo) => nodo.dataset.fila === String(id));
    const destino = fila ? fila.querySelector('button') : null;
    (destino || titulo).focus({ preventScroll: true });
  }

  // Tras repintar, el foco que se quedó sin sitio vuelve a la misma fila.
  function volverALaFila(id) {
    const activo = document.activeElement;
    if (activo && activo !== document.body && activo.isConnected) return;
    enfocarLaFila(id);
  }

  const laLista = listaQueSePide({
    ruta: 'incubadora',
    espera,
    lista: contenido,
    cargando: CARGANDO,
    titulo,
    sigueAqui,
    irse,
    alLlegar(leido, trasReintentar) {
      if (!esElMismoActivo(leido)) return;
      ponerElPlantel(leido);
      if (trasReintentar) (filas.querySelector('button') || titulo).focus({ preventScroll: true });
    },
  });

  // Mientras va un toque, su fila espera, su botón dice que espera y ningún
  // otro botón manda nada.
  function esperar(pulsado) {
    pulsado.closest('[data-fila]').classList.add('en-camino');
    pulsado.classList.add('esperando');
    pulsado.setAttribute('aria-busy', 'true');
    for (const otro of filas.querySelectorAll('.boton-sacar, .boton-nombrar')) otro.setAttribute('aria-disabled', 'true');
    avisar('');
  }

  // --- sacar a otro ------------------------------------------------------------------

  async function sacar(g, nodo) {
    if (enCamino) return;
    enCamino = true;
    const datos = { gachamon_id: g.id };
    cerrarElCampo();
    esperar(nodo);
    let respuesta;
    try {
      respuesta = await conReintentos(() => pedir('POST', 'incubadora/sacar', datos), sigueAqui);
    } catch (error) {
      if (!sigueAqui()) return;
      enCamino = false;
      if (hayQueDecidirDeNuevo(error)) {
        irse();
        return;
      }
      // Pudo haberse hecho igual: lo que se ve ya no vale. Se dice, y el
      // plantel se vuelve a pedir; si tampoco llega, la incubadora no carga.
      avisar(error && error.clave === null ? SIN_RESPUESTA : mensajeDe(error), true);
      pudoSalir = g.id;
      if (await laLista.releer() && sigueAqui()) enfocarLaFila(g.id);
      return;
    }
    if (!sigueAqui()) return;
    enCamino = false;
    if (pideOtraPantalla(respuesta.estado, 'incubadora')) {
      irse(respuesta.estado);
      return;
    }
    gachamonId = idDelGachamon(respuesta.estado);
    ponerElPlantel(respuesta.incubadora);
    avisar(respuesta.mensaje, !respuesta.ok);
    volverALaFila(g.id);
  }

  // --- ponerle nombre a un recluta ---------------------------------------------------

  function cerrarElCampo() {
    if (abierta) abierta.cerrar();
    abierta = null;
  }

  // «Ponerle nombre»: el botón se cambia por el campo «¿Cómo se va a llamar?»
  // (con `nombre` ya escrito, si lo hay), con «Ponerle este nombre» y «No»,
  // como la placa de la mochila. El foco va al campo; Enter en él también lo
  // confirma.
  function preguntarElNombre(fila, nombre = '') {
    if (enCamino) return;
    cerrarElCampo();
    const { sitio, boton: elBoton } = fila;
    const desistir = () => {
      if (enCamino) return;
      cerrarElCampo();
      elBoton.focus({ preventScroll: true });
    };
    const campo = el('input', {
      id: 'incubadora-nombre', class: 'texto', name: 'nombre', type: 'text', maxlength: LARGO_DEL_NOMBRE,
      autocomplete: 'off', autocapitalize: 'words', spellcheck: 'false', enterkeyhint: 'done',
    });
    campo.value = nombre;
    const pregunta = el('form', { class: 'campo pregunta-campo' },
      el('label', { class: 'etiqueta', for: 'incubadora-nombre' }, '¿Cómo se va a llamar?'),
      campo);
    pregunta.addEventListener('submit', (evento) => {
      evento.preventDefault();
      bautizar(fila, si, no, campo);
    });
    const { caja, si, no } = cajaDePregunta(pregunta, 'Ponerle este nombre', {
      alConfirmar: () => bautizar(fila, si, no, campo),
      alDesistir: desistir,
    });
    sitio.replaceChildren(caja);
    sitio.classList.add('abierta');
    abierta = {
      cerrar() {
        sitio.replaceChildren(elBoton);
        sitio.classList.remove('abierta');
      },
    };
    campo.focus({ preventScroll: true });
  }

  // «Ponerle este nombre». Un toque en camino a la vez: un segundo envío no
  // sale, y si aun así el servidor dice que ya lo tiene, está hecho.
  async function bautizar(fila, si, no, campo) {
    if (enCamino) return;
    enCamino = true;
    const { id } = fila.gachamon;
    const datos = { nombre: campo.value, gachamon_id: id };
    esperar(si);
    no.setAttribute('aria-disabled', 'true');
    campo.readOnly = true;
    let respuesta;
    try {
      respuesta = await conReintentos(() => pedir('POST', 'bautizar', datos), sigueAqui);
    } catch (error) {
      if (!sigueAqui()) return;
      if (error && error.clave === 'ya_bautizado') {
        await alDiaTrasBautizar(id);
        return;
      }
      enCamino = false;
      if (hayQueDecidirDeNuevo(error)) {
        irse();
        return;
      }
      if (error && error.estado === 422) {
        // El nombre no vale: se dice, y el campo sigue abierto con lo que se
        // escribió, para corregirlo.
        ponerElPlantel(ultimo);
        avisar(mensajeDe(error), true);
        if (sinNombre.has(id)) preguntarElNombre(sinNombre.get(id), datos.nombre);
        return;
      }
      // Pudo haberse hecho igual: se dice, y el plantel se vuelve a pedir.
      avisar(error && error.clave === null ? SIN_RESPUESTA : mensajeDe(error), true);
      if (await laLista.releer() && sigueAqui()) enfocarLaFila(id);
      return;
    }
    if (!sigueAqui()) return;
    if (pideOtraPantalla(respuesta, 'incubadora')) {
      enCamino = false;
      irse(respuesta);
      return;
    }
    gachamonId = idDelGachamon(respuesta);
    await alDiaTrasBautizar(id);
  }

  // Tras un bautizo, el plantel al día sin esconder el que se ve: la fila
  // sigue esperando hasta que llega. Si no llega, como tras un toque sin
  // respuesta, se vuelve a pedir a la vista.
  async function alDiaTrasBautizar(id) {
    let leido;
    try {
      leido = await conReintentos(() => pedir('GET', 'incubadora'), sigueAqui);
    } catch (error) {
      if (!sigueAqui()) return;
      enCamino = false;
      if (hayQueDecidirDeNuevo(error)) {
        irse();
        return;
      }
      if (await laLista.releer() && sigueAqui()) enfocarLaFila(id);
      return;
    }
    if (!sigueAqui()) return;
    enCamino = false;
    if (!esElMismoActivo(leido)) return;
    ponerElPlantel(leido);
    volverALaFila(id);
  }

  ponerSaldos(estado.saldos);
  return laLista.cargar();
}
