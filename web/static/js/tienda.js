// La Tienda del pueblo: lo que se vende en cuatro secciones —objetos,
// cosméticos, casas y muebles— y comprar en dos toques: el primero pregunta y
// el segundo compra.
//
// `tienda(contenedor, estado, seguir)` pinta la pantalla y pide el catálogo
// (`GET tienda`). Las reglas son del servidor: qué se vende, a quién, a
// cuánto y qué ya es tuyo; aquí se pinta lo que dice, sin calcular precios ni
// permisos. Cada compra lleva su evento (el mismo en sus reintentos) y su
// respuesta trae el catálogo y el estado al día, con los que se repinta. Si una
// compra se queda sin respuesta pudo haber llegado igual: lo que se veía ya no
// vale, y el catálogo se vuelve a pedir; si tampoco llega, la tienda no carga.
// Si lo que contesta pide otra pantalla (sin sesión, ya no estás en la tienda,
// tu gachamon cambió) se vuelve a decidir con `seguir`. Al salir se deja de
// temporizar, y una respuesta que llega tarde no pinta ni llama a `seguir`.
// La cabecera, las filas, la pregunta, el aviso y la espera del catálogo son
// los de `articulos.js`, que comparte con la mochila. Todo texto entra por
// `el` o por `textContent`.

import { conReintentos, nuevoEvento, pedir } from './api.js';
import { olvidarLasQueFaltan } from './arte.js';
import {
  GEMAS, MONEDAS, cabeceraConSaldos, cajaDePregunta, filaDeArticulo as fila, hayQueDecidirDeNuevo,
  linea, listaQueSePide, mensajeDe, pideOtraPantalla, zonaDeAviso,
} from './articulos.js';
import {
  loQueTraeLaCasa, preguntaDeCompra, preguntaDeMejora, preguntaDeVenta, quienesViven,
} from './compras.js';
import { el } from './dom.js';

const CARGANDO = 'Cargando la tienda…';
const SIN_RESPUESTA = 'No hubo respuesta. Revisa tu conexión.';
const MUEBLES_SIN_CASA = 'Los muebles van en una casa, y todavía no tienes.';

const SECCIONES = [
  { clave: 'objetos', nombre: 'Objetos' },
  { clave: 'cosmeticos', nombre: 'Cosméticos' },
  { clave: 'casas', nombre: 'Casas' },
  { clave: 'muebles', nombre: 'Muebles' },
];

// Lo que se dice de cada cosmético bajo su nombre, según su tipo.
const TIPO_DE_COSMETICO = { sombrero: 'Sombrero', titulo: 'Título' };

// Los cosméticos se pagan con gemas (`GEMAS`); lo demás, con monedas (`MONEDAS`).

// La sección que se veía la última vez, mientras dure la página.
let seccionVista = SECCIONES[0].clave;

export function tienda(contenedor, estado, seguir) {
  // El arte que no cargó en otra pantalla se pide de nuevo.
  olvidarLasQueFaltan();
  let vivo = true;
  // Lo que contesta la tienda, abajo de lo que se ve.
  const aviso = zonaDeAviso();
  const { avisar } = aviso;

  function parar() {
    vivo = false;
    aviso.parar();
  }

  // Deja la tienda y que se decida otra pantalla: con el estado que llegó, o
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

  // --- la cabecera: dónde estás y lo que tienes ------------------------------------

  const { cabecera, titulo, ponerSaldos } = cabeceraConSaldos('🛒', 'Tienda');

  // --- las pestañas y sus secciones ------------------------------------------------

  const secciones = new Map(SECCIONES.map(({ clave, nombre }) => [clave, {
    pestana: el('button', { type: 'button', class: 'pestana', 'aria-controls': `tienda-${clave}` }, nombre),
    nodo: el('section', { class: 'seccion-tienda', id: `tienda-${clave}`, 'aria-label': nombre }),
  }]));
  if (!secciones.has(seccionVista)) seccionVista = SECCIONES[0].clave;
  for (const [clave, { pestana }] of secciones) pestana.addEventListener('click', () => elegir(clave));

  // Se ve una sección a la vez. Una pregunta abierta en otra se cierra.
  function elegir(clave) {
    if (!enCamino) cerrarLaPregunta();
    seccionVista = clave;
    for (const [esta, { pestana, nodo }] of secciones) {
      pestana.setAttribute('aria-pressed', String(esta === clave));
      nodo.hidden = esta !== clave;
    }
  }

  // Hasta que llega el catálogo no hay estante: hay una frase.
  const espera = el('div', { class: 'espera-tienda' });
  const estante = el('div', { class: 'estante', hidden: true },
    el('div', { class: 'pestanas', role: 'group', 'aria-label': 'Secciones de la tienda' },
      [...secciones.values()].map((s) => s.pestana)),
    [...secciones.values()].map((s) => s.nodo));
  const volver = el('button', { type: 'button', class: 'boton boton-volver' }, 'Volver');
  volver.addEventListener('click', () => irse());
  const cuerpo = el('div', { class: 'cuerpo cuerpo-tienda' }, espera, estante, aviso.nodo, volver);
  contenedor.append(cabecera, cuerpo);

  // --- lo que se puede comprar: cada fila con su botón -------------------------------

  // La pregunta abierta: `{cerrar}`; sólo una a la vez.
  let abierta = null;
  // Mientras una compra está en camino no sale otra.
  let enCamino = false;

  // `compra` es `{id, ruta, cuerpo, pregunta, confirmar}`: a qué ruta va, con
  // qué cuerpo, qué se pregunta antes y qué dice el botón que lo confirma.
  function botonQuePregunta(contenido, clase, compra) {
    const boton = el('button', { type: 'button', class: clase }, contenido);
    const sitio = el('div', { class: 'accion' }, boton);
    const oferta = { sitio, boton, compra };
    boton.addEventListener('click', () => preguntar(oferta));
    return sitio;
  }

  // «🪙 10», y para el lector «Comprar por 10 monedas».
  function botonDePrecio(moneda, precio, verbo, compra) {
    return botonQuePregunta([
      el('span', { 'aria-hidden': 'true' }, `${moneda.simbolo} ${precio}`),
      el('span', { class: 'solo-lector' }, `${verbo} por ${moneda.cuantas(precio)}`),
    ], 'boton-precio', compra);
  }

  // El precio de lo que no se puede comprar: se ve, pero no es un botón.
  function precioQuieto(moneda, precio) {
    return el('div', { class: 'accion' },
      el('span', { class: 'precio-quieto' },
        el('span', { 'aria-hidden': 'true' }, `${moneda.simbolo} ${precio}`),
        el('span', { class: 'solo-lector' }, `Cuesta ${moneda.cuantas(precio)}`)));
  }

  const yaLoTienes = () => el('div', { class: 'accion' }, el('span', { class: 'ya-lo-tienes' }, 'Ya lo tienes'));

  const lista = (filas) => el('ul', { class: 'articulos' }, filas);

  function filaDeObjeto(o) {
    const id = `objeto:${o.clave}`;
    const lineas = [linea(o.descripcion, 'articulo-detalle')];
    if (o.nota) lineas.push(linea(o.nota, 'articulo-nota'));
    if (o.tienes > 0) lineas.push(linea(`Tienes ${o.tienes}`, 'articulo-tienes'));
    const accion = o.se_vende
      ? botonDePrecio(MONEDAS, o.precio, 'Comprar', {
        id, ruta: 'tienda/comprar', cuerpo: { que: 'objeto', clave: o.clave },
        pregunta: preguntaDeCompra(o.precio, MONEDAS.palabra), confirmar: 'Comprar',
      })
      : precioQuieto(MONEDAS, o.precio);
    return fila({ id, icono: o.icono, nombre: o.nombre, lineas, accion, apagada: !o.se_vende });
  }

  function filaDeCosmetico(c) {
    const id = `cosmetico:${c.clave}`;
    const tipo = Object.hasOwn(TIPO_DE_COSMETICO, c.tipo) ? TIPO_DE_COSMETICO[c.tipo] : null;
    const accion = c.tuyo
      ? yaLoTienes()
      : botonDePrecio(GEMAS, c.precio, 'Comprar', {
        id, ruta: 'tienda/comprar', cuerpo: { que: 'cosmetico', clave: c.clave },
        pregunta: preguntaDeCompra(c.precio, GEMAS.palabra), confirmar: 'Comprar',
      });
    return fila({ id, icono: c.icono, nombre: c.nombre, lineas: tipo ? [linea(tipo, 'articulo-detalle')] : [], accion });
  }

  // Sin casa, los muebles se ven pero no se compran.
  function filaDeMueble(m, hayCasa) {
    const id = `mueble:${m.clave}`;
    let accion;
    if (m.tuyo) accion = yaLoTienes();
    else if (!hayCasa) accion = precioQuieto(MONEDAS, m.precio);
    else {
      accion = botonDePrecio(MONEDAS, m.precio, 'Comprar', {
        id, ruta: 'tienda/comprar', cuerpo: { que: 'mueble', clave: m.clave },
        pregunta: preguntaDeCompra(m.precio, MONEDAS.palabra), confirmar: 'Comprar',
      });
    }
    return fila({
      id, icono: m.icono, nombre: m.nombre, lineas: [linea(`Comodidad +${m.comodidad}`, 'articulo-detalle')],
      accion, apagada: !hayCasa && !m.tuyo,
    });
  }

  // Lo que se puede hacer con una casa tuya, una cosa por línea: cada mejora
  // con su precio, y venderla.
  function subfila(id, texto, accion) {
    return el('div', { class: 'subfila', 'data-fila': id }, texto ? el('p', { class: 'subfila-texto' }, texto) : null, accion);
  }

  function filaDeTuCasa(casa) {
    const id = `tuya:${casa.id}`;
    const mejoras = casa.mejoras.map((mejora) => {
      const queHace = `Mejorar a ${mejora.nombre.toLowerCase()}`;
      return subfila(`${id}:${mejora.clave}`, queHace, botonDePrecio(MONEDAS, mejora.cuesta, queHace, {
        id: `${id}:${mejora.clave}`, ruta: 'tienda/casa',
        cuerpo: { accion: 'mejorar', casa: mejora.clave, casa_id: casa.id },
        pregunta: preguntaDeMejora(casa, mejora), confirmar: 'Mejorar',
      }));
    });
    const vender = subfila(`${id}:vender`, null, botonQuePregunta('Vender', 'boton-vender', {
      id: `${id}:vender`, ruta: 'tienda/casa', cuerpo: { accion: 'vender', casa_id: casa.id },
      pregunta: preguntaDeVenta(casa), confirmar: 'Vender',
    }));
    return fila({
      id, icono: casa.icono, nombre: casa.nombre, lineas: [linea(quienesViven(casa), 'articulo-detalle')],
      accion: null, debajo: el('div', { class: 'casa-acciones' }, mejoras, vender),
    });
  }

  function filaDeCasaALaVenta(casa, sePuede) {
    const id = `casa:${casa.clave}`;
    const accion = sePuede
      ? botonDePrecio(MONEDAS, casa.precio, 'Comprar', {
        id, ruta: 'tienda/casa', cuerpo: { accion: 'comprar', casa: casa.clave },
        pregunta: preguntaDeCompra(casa.precio, MONEDAS.palabra), confirmar: 'Comprar',
      })
      : precioQuieto(MONEDAS, casa.precio);
    return fila({
      id, icono: casa.icono, nombre: casa.nombre, lineas: [linea(loQueTraeLaCasa(casa), 'articulo-detalle')],
      accion, apagada: !sePuede,
    });
  }

  function casas({ maximo, puedes_otra: sePuede, tuyas, a_la_venta: aLaVenta }) {
    const subtitulo = (texto) => (tuyas.length ? el('h2', { class: 'tienda-subtitulo' }, texto) : null);
    return [
      subtitulo('Tus casas'),
      tuyas.length ? lista(tuyas.map(filaDeTuCasa)) : null,
      subtitulo('A la venta'),
      sePuede ? null : el('p', { class: 'aviso-de-seccion' }, `Ya tienes ${maximo} casas, que es el máximo.`),
      lista(aLaVenta.map((casa) => filaDeCasaALaVenta(casa, sePuede))),
    ];
  }

  function muebles({ tienes_casa: hayCasa, lista: todos }) {
    return [
      hayCasa ? null : el('p', { class: 'aviso-de-seccion' }, MUEBLES_SIN_CASA),
      lista(todos.map((m) => filaDeMueble(m, hayCasa))),
    ];
  }

  // Pinta el catálogo entero, las cuatro secciones: las que no se ven también,
  // para que cambiar de pestaña no pierda nada. Cierra la pregunta abierta. El
  // foco que estaba en una fila vuelve a esa misma fila.
  function ponerCatalogo(nuevo) {
    const conFoco = document.activeElement && estante.contains(document.activeElement)
      ? document.activeElement.closest('[data-fila]') : null;
    abierta = null;
    ponerSaldos(nuevo.saldos);
    // Primero lo que se te vende, cada grupo en el orden del catálogo: lo que
    // todavía no se vende aquí no tapa lo que sí.
    const objetos = [...nuevo.objetos.filter((o) => o.se_vende), ...nuevo.objetos.filter((o) => !o.se_vende)];
    secciones.get('objetos').nodo.replaceChildren(lista(objetos.map(filaDeObjeto)));
    secciones.get('cosmeticos').nodo.replaceChildren(lista(nuevo.cosmeticos.map(filaDeCosmetico)));
    secciones.get('casas').nodo.replaceChildren(...casas(nuevo.casas).filter(Boolean));
    secciones.get('muebles').nodo.replaceChildren(...muebles(nuevo.muebles).filter(Boolean));
    if (conFoco) volverALaFila(conFoco.dataset.fila);
  }

  // --- comprar en dos toques -----------------------------------------------------------

  function cerrarLaPregunta() {
    if (abierta) abierta.cerrar();
    abierta = null;
  }

  // El primer toque: el botón se cambia por la pregunta, con «Comprar» (o lo
  // que se haga) y «No». El foco va a la pregunta, que se lee; no al botón que
  // confirma, para que una tecla que se queda apretada no compre.
  function preguntar(oferta) {
    if (enCamino) return;
    cerrarLaPregunta();
    const { sitio, boton, compra } = oferta;
    const desistir = () => {
      if (enCamino) return;
      cerrarLaPregunta();
      boton.focus({ preventScroll: true });
    };
    const {
      caja, cabeza: texto, si, no,
    } = cajaDePregunta(compra.pregunta, compra.confirmar, {
      alConfirmar: () => mandar(oferta, si, no),
      alDesistir: desistir,
    });
    sitio.replaceChildren(caja);
    sitio.classList.add('abierta');
    abierta = {
      cerrar() {
        sitio.replaceChildren(boton);
        sitio.classList.remove('abierta');
      },
    };
    texto.focus({ preventScroll: true });
  }

  // El foco va al botón de esa fila; si ya no está (la mejora hecha), al de la
  // fila que la contenía (su casa), y si tampoco, a la pestaña de la sección.
  function enfocarLaFila(id) {
    const filas = [...estante.querySelectorAll('[data-fila]')];
    let buscada = id;
    let destino = null;
    while (buscada && !destino) {
      const nodo = filas.find((n) => n.dataset.fila === buscada);
      destino = nodo ? nodo.querySelector('button') : null;
      // «tuya:3:mediana» está dentro de «tuya:3».
      buscada = buscada.includes(':') ? buscada.slice(0, buscada.lastIndexOf(':')) : '';
    }
    (destino || secciones.get(seccionVista).pestana).focus({ preventScroll: true });
  }

  // Tras repintar, el foco que se quedó sin sitio vuelve a la misma fila.
  function volverALaFila(id) {
    const activo = document.activeElement;
    if (activo && activo !== document.body && activo.isConnected) return;
    enfocarLaFila(id);
  }

  // El segundo toque: manda la compra. Mientras va, esa fila espera y ningún
  // otro botón compra. Un toque, un evento: sus reintentos llevan el mismo.
  async function mandar(oferta, si, no) {
    if (enCamino) return;
    enCamino = true;
    const { id, ruta, cuerpo: datos } = oferta.compra;
    oferta.sitio.closest('[data-fila]').classList.add('en-camino');
    si.classList.add('esperando');
    si.setAttribute('aria-busy', 'true');
    no.setAttribute('aria-disabled', 'true');
    for (const boton of estante.querySelectorAll('.boton-precio, .boton-vender')) {
      boton.setAttribute('aria-disabled', 'true');
    }
    avisar('');
    const evento = nuevoEvento();
    let respuesta;
    try {
      respuesta = await conReintentos(() => pedir('POST', ruta, { ...datos, evento_id: evento }), sigueAqui);
    } catch (error) {
      if (!sigueAqui()) return;
      enCamino = false;
      if (hayQueDecidirDeNuevo(error)) {
        irse();
        return;
      }
      // Pudo haber llegado igual: lo que se ve ya no vale y no se vuelve a
      // pintar. Se dice, y el catálogo se vuelve a pedir; si tampoco llega,
      // la tienda no carga.
      avisar(error && error.clave === null ? SIN_RESPUESTA : mensajeDe(error), true);
      if (await laLista.releer()) enfocarLaFila(id);
      return;
    }
    if (!sigueAqui()) return;
    enCamino = false;
    if (respuesta.estado && pideOtraPantalla(respuesta.estado, 'tienda')) {
      irse(respuesta.estado);
      return;
    }
    // También un «no» (te faltan, ya lo tienes, reintenta…) trae el catálogo
    // al día: no hace falta pedirlo.
    ponerCatalogo(respuesta.tienda);
    avisar(respuesta.mensaje, !respuesta.ok);
    volverALaFila(id);
  }

  // --- el catálogo -------------------------------------------------------------------

  const laLista = listaQueSePide({
    ruta: 'tienda',
    espera,
    lista: estante,
    cargando: CARGANDO,
    titulo,
    sigueAqui,
    irse,
    alLlegar(leido, trasReintentar) {
      ponerCatalogo(leido);
      elegir(seccionVista);
      if (trasReintentar) secciones.get(seccionVista).pestana.focus({ preventScroll: true });
    },
  });

  ponerSaldos(estado.saldos);
  return laLista.cargar();
}
