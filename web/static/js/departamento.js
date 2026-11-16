// Tu casa: la pieza de tu departamento, en vista isométrica por casillas, con
// sus muebles, y tu avatar, que camina por ella.
//
// `departamento(contenedor, estado, seguir)` pide la pieza al servidor
// (`GET departamento`) al entrar, cada 30 segundos y al volver a la pestaña, y
// la pinta en su lienzo; debajo, una línea dice cómo está. Tocar una casilla
// que se pisa lleva a tu avatar hasta ella, de casilla en casilla; con menos
// movimiento, aparece ahí. Dónde estás parado es sólo del dibujo: no se guarda
// ni se manda. Si lo que llega pide otra pantalla (ya no estás en tu casa, ya
// no hay sesión) se lo pasa a `seguir`.
//
// Los muebles se tocan, sin modos: tocar uno lo elige (su huella se marca) y
// encima sale su menú, con «Mover», «Girar» y «Guardar». Lo que llevas en la
// mano (el que mueves, o el que sacas de la bandeja de «Guardados», bajo la
// pieza) marca dónde cabe, y el toque siguiente dice dónde va: en un sitio
// marcado se pone; en cualquier otro, se suelta. «Ampliar» cambia lo de la
// derecha por lo que cuesta crecer por cada lado.
//
// El servidor manda: la pieza se pinta como llega, y lo que se calcula aquí
// (por dónde se camina, qué se tocó, qué cabe dónde) sirve sólo para dibujar y
// para no proponer lo imposible. Poner y guardar se mandan una vez; ampliar,
// que cuesta monedas, lleva un evento por toque (el mismo en sus reintentos).
// Lo que sale bien no se dice: se ve; ampliar y lo que no se puede dicen la
// frase del servidor; sin respuesta, se dice y la pieza se vuelve a leer.
// Mientras una petición va, lo que la mandó espera y no sale otra. El lienzo
// sólo se mira (`aria-hidden`); el menú, la bandeja y lo de ampliar son botones
// de verdad. Todo texto entra por `el` o por `textContent`. Lo que corre (el
// cuadro de animación, la relectura y los oyentes) se detiene al salir, y una
// respuesta que llega tarde no pinta.

import { conReintentos, nuevoEvento, pedir } from './api.js';
import { cargar, lienzoDePieza, olvidarLasQueFaltan } from './arte.js';
import {
  MONEDAS, cabeceraConSaldos, hayQueDecidirDeNuevo, listaQueSePide, mensajeDe, pideOtraPantalla, zonaDeAviso,
} from './articulos.js';
import { cargarAvatar, poseAlCaminar } from './avatar.js';
import {
  camino, dondeCabe, giroParaPoner, libreMasCercana, lineaDeEstado, noSePisan, sitiosDeEntrada,
} from './casillas.js';
import { el } from './dom.js';
import { dibujarPieza, rutasDeLaPieza } from './pieza.js';
import {
  cajaDelMueble, casillaEn, medir, queSeToco, tramoEn,
} from './proyeccion.js';

const VISTA = 'departamento';
const PEDIR_CADA_MS = 30_000;
const DENSIDAD_MAXIMA = 3;
// Lo que anda tu avatar, en casillas por segundo.
const CASILLAS_POR_SEGUNDO = 3;
// Las cuatro posiciones de un mueble.
const GIROS = 4;
// Lo de pared va en las paredes; lo demás, en el suelo.
const PARED = 'pared';
// Lo que dura otro aviso mientras llevas algo en la mano, antes de que vuelva
// la indicación de dónde tocar: lo mismo que dura cualquier aviso.
const UN_AVISO_DURA_MS = 6_000;
// El ícono de cada mueble de la bandeja, en píxeles de pantalla.
const LADO_DEL_ICONO = 40;
// Lo que el menú deja hasta el mueble y hasta el borde de la pieza, en píxeles.
const MARGEN_DEL_MENU = 6;

const CARGANDO = 'Cargando tu departamento…';
const SIN_RESPUESTA = 'No hubo respuesta. Revisa tu conexión.';
const TOCA_LA_CASILLA = 'Toca la casilla donde lo quieres.';
const TOCA_LA_PARED = 'Toca la pared donde lo quieres.';
const NO_CABE = 'Ahí no cabe.';
const ROTULO_DE_GUARDADOS = 'Guardados · toca uno y después una casilla';
const NADA_GUARDADO = 'No queda nada guardado.';
const ROTULO_DE_AMPLIAR = 'Ampliar el departamento';
const YA_NO_CRECE = 'Tu departamento ya no puede crecer más.';

// Cuánto ocupa un mueble, como se dice bajo su nombre en la bandeja.
function cuantoOcupa(mueble) {
  if (mueble.capa === PARED) return 'en la pared';
  const casillas = mueble.ancho * mueble.fondo;
  return casillas === 1 ? '1 casilla' : `${casillas} casillas`;
}

// Los guardados, uno por tipo de mueble en el orden en que llegan: el primero
// de cada tipo (el que se pone) y cuántos hay.
function porTipo(guardados) {
  const tipos = new Map();
  for (const guardado of guardados) {
    if (!tipos.has(guardado.clave)) tipos.set(guardado.clave, { primero: guardado, cuantos: 0 });
    tipos.get(guardado.clave).cuantos += 1;
  }
  return [...tipos.values()];
}

export function departamento(contenedor, estado, seguir) {
  // El arte que no cargó en otra pantalla se pide de nuevo.
  olvidarLasQueFaltan();
  const menosMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)');
  const quieto = () => menosMovimiento.matches;

  let vivo = true;
  const oyentes = new AbortController();
  const { signal } = oyentes;
  let observador = null;
  let cuadroPedido = null;
  let cadaTanto = null;

  // --- la cabecera, la pieza, lo que se dice y lo de la derecha --------------------------

  const { cabecera, titulo, ponerSaldos } = cabeceraConSaldos('📍', estado.lugar.nombre);

  const lienzo = el('canvas', { class: 'pieza-lienzo', 'aria-hidden': 'true' });
  // El menú del mueble elegido va encima del lienzo, junto al mueble.
  const menu = el('div', { class: 'menu-de-la-pieza', role: 'group', hidden: true });
  const escenario = el('div', { class: 'pieza-escenario' }, lienzo, menu);
  const linea = el('p', { class: 'pieza-linea' });
  const bandeja = el('div', { class: 'bandeja', id: 'departamento-bandeja', hidden: true });
  // Mientras no llega, en su lugar se lee la espera (o por qué no llegó).
  const pieza = el('div', { class: 'pieza', hidden: true }, escenario, linea, bandeja);
  const espera = el('div', { class: 'espera-tienda' });

  const aviso = zonaDeAviso();
  aviso.nodo.classList.add('aviso');
  const { avisar } = aviso;
  // Cuándo vuelve la indicación de dónde tocar tras otro aviso (ver `decir`).
  let volverAIndicar = null;

  const conIcono = (clase, icono, texto, atributos = {}) => el('button', { type: 'button', class: clase, ...atributos },
    el('span', { 'aria-hidden': 'true' }, icono), texto);
  const aLosGuardados = conIcono('boton boton-guardados', '📦', 'Guardados',
    { 'aria-expanded': 'false', 'aria-controls': 'departamento-bandeja' });
  const alAmpliar = conIcono('boton boton-ampliar', '📐', 'Ampliar');
  const aLaMochila = conIcono('boton boton-mochila', '🎒', 'Mochila');
  const alPueblo = conIcono('boton boton-pueblo', '🗺️', 'Pueblo');
  // Guardados y Ampliar son de la pieza: se ven cuando llega.
  const deLaPieza = el('div', { class: 'acciones-departamento', hidden: true }, aLosGuardados, alAmpliar);
  const derecha = el('div', { class: 'lado-departamento' },
    deLaPieza, el('div', { class: 'salidas-lugar' }, aLaMochila, alPueblo));
  const panelAmpliar = el('div', { class: 'ampliar', hidden: true });

  const cuerpo = el('div', { class: 'cuerpo cuerpo-departamento' },
    espera, pieza, aviso.nodo, derecha, panelAmpliar);
  contenedor.append(cabecera, cuerpo);

  function parar() {
    vivo = false;
    if (cuadroPedido !== null) cancelAnimationFrame(cuadroPedido);
    cuadroPedido = null;
    clearInterval(cadaTanto);
    clearTimeout(volverAIndicar);
    aviso.parar();
    oyentes.abort();
    if (observador) observador.disconnect();
  }

  // Deja la pantalla y que se decida otra: con el estado que llegó, o
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

  // El estado del juego, el último que llegó: con él se sale al pueblo o a la mochila.
  let actual = estado;

  aLaMochila.addEventListener('click', () => {
    parar();
    seguir(actual, { vista: 'mochila' });
  }, { signal });
  alPueblo.addEventListener('click', () => {
    parar();
    seguir(actual, { vista: 'pueblo' });
  }, { signal });

  // Cada estado que llega se pregunta lo mismo que al entrar: si ya no toca
  // esta pantalla, se va.
  function aplicarEstado(nuevo) {
    if (pideOtraPantalla(nuevo, VISTA)) {
      irse(nuevo);
      return false;
    }
    actual = nuevo;
    ponerSaldos(nuevo.saldos);
    return true;
  }

  // --- lo que hay en la pieza ------------------------------------------------------------

  let depto = null;
  // El arte que ya llegó, por ruta: el de la pieza, las capas del avatar.
  const cargadas = new Map();
  // Ya llegó lo justo para pintar la primera vez.
  let listo = false;

  // Tu avatar: la casilla donde está (con decimales a medio paso), las que le
  // quedan por pisar, hacia dónde mira y cuánto lleva andando (para el paso).
  let tu = null;
  let ruta = [];
  let espejo = false;
  let andado = 0;

  // El mueble puesto que está elegido (su id), o `null`.
  let elegido = null;
  // Lo que llevas en la mano, o `null`: `{mueble, sitios, tipo}`. `sitios`
  // son los de `dondeCabe`, `{x, y, giro}`; `tipo` es la clave de lo que salió
  // de la bandeja (se pone el primero guardado de ese tipo), o `null` si es un
  // mueble puesto que mueves.
  let enLaMano = null;
  let bandejaAbierta = false;
  let ampliando = false;

  // Mientras una petición va no sale otra; lo que la mandó espera hasta que vuelve.
  let enCamino = false;
  let origenEnEspera = null;
  // Cada acción que cambia la pieza suma uno: una lectura que salió antes ya
  // no se pinta, porque lo que trae la acción es más nuevo.
  let acciones = 0;

  const elPuesto = (id) => (depto && id !== null ? depto.puestos.find((p) => p.id === id) : null) || null;

  // Pide ese arte y vuelve a pintar cuando llega. Nunca falla: lo que no carga
  // se pinta como su recuadro.
  function traerArte(rutas) {
    return Promise.all(rutas.map(cargar)).then((llegadas) => {
      for (const llegada of llegadas) cargadas.set(llegada.ruta, llegada);
      if (listo && sigueAqui()) dibujar();
    });
  }

  function traerAvatar() {
    return cargarAvatar(actual.avatar).then((capas) => {
      for (const [r, capa] of capas) cargadas.set(r, capa);
    });
  }

  // Tu avatar, en la pieza que llegó: si quedó sobre un mueble (o fuera),
  // aparece en la casilla libre más cercana, sin caminar. Si iba caminando, el
  // paso que está dando se termina si esa casilla se sigue pisando (si no,
  // aparece) y el resto del camino se rehace; si ya no se llega, se queda ahí.
  function reubicarte() {
    const ocupado = noSePisan(depto);
    const sePisa = ([i, j]) => i >= 0 && j >= 0 && i < depto.ancho && j < depto.fondo && !ocupado.has(`${i},${j}`);
    if (ruta.length > 0) {
      const [paso, ...resto] = ruta;
      if (sePisa(paso)) {
        if (!resto.every(sePisa)) {
          const destino = ruta.at(-1);
          ruta = [paso, ...(sePisa(destino) ? camino(depto.ancho, depto.fondo, ocupado, paso, destino) : [])];
        }
        return;
      }
      ruta = [];
    }
    const aqui = [Math.round(tu.i), Math.round(tu.j)];
    const donde = sePisa(aqui) ? aqui : libreMasCercana(depto.ancho, depto.fondo, ocupado, aqui);
    tu = donde && { i: donde[0], j: donde[1] };
  }

  // Lo que llevas en la mano, al día con la pieza que hay; `null` si ya no está.
  // Lo que mueves no cuenta el sitio donde ya está.
  function manoAlDia({ mueble, tipo }) {
    if (tipo !== null) {
      const guardado = depto.guardados.find((g) => g.clave === tipo);
      return guardado ? { mueble: guardado, tipo, sitios: dondeCabe(depto, guardado, 0) } : null;
    }
    const puesto = elPuesto(mueble.id);
    if (!puesto) return null;
    const sitios = dondeCabe(depto, puesto, puesto.giro).filter((s) => s.x !== puesto.x || s.y !== puesto.y);
    return { mueble: puesto, tipo: null, sitios };
  }

  // Pone la pieza que llegó: su línea, los saldos, tu avatar (en la entrada si
  // todavía no estabas), lo elegido y lo que llevas en la mano si siguen ahí,
  // la bandeja y lo de ampliar. Devuelve cuándo llega su arte.
  function aplicarDepto(nuevo) {
    depto = nuevo;
    linea.textContent = lineaDeEstado(nuevo);
    ponerSaldos(nuevo.saldos);
    actual = { ...actual, saldos: nuevo.saldos };
    if (tu) {
      reubicarte();
    } else {
      const [entrada] = sitiosDeEntrada(nuevo.ancho, nuevo.fondo, noSePisan(nuevo), 1);
      if (entrada) tu = { i: entrada[0], j: entrada[1] };
    }
    if (!elPuesto(elegido)) elegido = null;
    if (enLaMano) {
      enLaMano = manoAlDia(enLaMano);
      if (!enLaMano) decir('');
    }
    if (listo && medirLienzo()) dibujar();
    ponerMenu();
    ponerBandeja();
    ponerAmpliar();
    return traerArte(rutasDeLaPieza(nuevo));
  }

  // --- el lienzo -------------------------------------------------------------------------

  // La medida de la pieza en píxeles de pantalla (`medir`) y cuántos píxeles
  // del lienzo hay en cada uno.
  let m = null;
  let escala = [1, 1];

  // Mide el lienzo como se ve, le da los píxeles del aparato y vuelve a medir la pieza.
  function medirLienzo() {
    const caja = lienzo.getBoundingClientRect();
    if (!depto || !caja.width || !caja.height) return false;
    const densidad = Math.min(Math.max(window.devicePixelRatio || 1, 1), DENSIDAD_MAXIMA);
    const anchoReal = Math.round(caja.width * densidad);
    const altoReal = Math.round(caja.height * densidad);
    // Cambiar el tamaño borra el lienzo: sólo si de verdad cambia.
    if (lienzo.width !== anchoReal) lienzo.width = anchoReal;
    if (lienzo.height !== altoReal) lienzo.height = altoReal;
    escala = [anchoReal / caja.width, altoReal / caja.height];
    m = medir(caja.width, caja.height, depto.ancho, depto.fondo);
    return true;
  }

  // Encima de todo, las marcas: dónde cabe lo que llevas en la mano y la
  // huella de lo elegido.
  function dibujar() {
    if (!listo || !m) return;
    const ctx = lienzo.getContext('2d');
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, lienzo.width, lienzo.height);
    ctx.setTransform(escala[0], 0, 0, escala[1], 0, 0);
    const puesto = elPuesto(elegido);
    dibujarPieza(ctx, m, {
      depto,
      cargadas,
      gachamones: [],
      tu: tu && { i: tu.i, j: tu.j, pose: poseAlCaminar(andado, ruta.length > 0), espejo, avatar: actual.avatar },
      libres: enLaMano ? enLaMano.sitios.map((s) => [s.x, s.y]) : [],
      elegido: puesto ? puesto.casillas : null,
    });
  }

  // --- caminar ---------------------------------------------------------------------------

  // Sólo se anima mientras algo se mueve; parado, el lienzo se queda como está.
  function pedirCuadro() {
    if (vivo && cuadroPedido === null) cuadroPedido = requestAnimationFrame(cuadro);
  }

  let antes = null;

  function cuadro(ahora) {
    cuadroPedido = null;
    if (!sigueAqui()) return;
    // Una pestaña que estuvo dormida recibe todo el tiempo de una vez: llega sin pasarse.
    const dt = antes === null ? 0 : (ahora - antes) / 1000;
    antes = ahora;
    avanzar(dt);
    dibujar();
    if (ruta.length > 0) {
      pedirCuadro();
    } else {
      antes = null;
      andado = 0;
    }
  }

  // Lo que anda en `dt` segundos, casilla tras casilla, sin pasarse de la última.
  function avanzar(dt) {
    andado += dt;
    let queda = CASILLAS_POR_SEGUNDO * dt;
    while (ruta.length > 0 && queda > 0) {
      const [hastaI, hastaJ] = ruta[0];
      const di = hastaI - tu.i;
      const dj = hastaJ - tu.j;
      // Ir hacia `j` o volver por `i` es ir hacia la izquierda de la pantalla.
      if (di !== dj) espejo = di < dj;
      const falta = Math.abs(di) + Math.abs(dj);
      if (falta <= queda) {
        tu = { i: hastaI, j: hastaJ };
        ruta.shift();
        queda -= falta;
      } else {
        const enI = Math.min(queda, Math.abs(di));
        tu = { i: tu.i + Math.sign(di) * enI, j: tu.j + Math.sign(dj) * (queda - enI) };
        queda = 0;
      }
    }
  }

  // Hasta esa casilla, por el camino más corto. A medio paso, se termina el
  // paso y desde ahí se va al nuevo destino. Sin camino (lo cierran los
  // muebles) o con menos movimiento, aparece ahí.
  function caminarHasta([i, j]) {
    const ocupado = noSePisan(depto);
    if (!tu || ocupado.has(`${i},${j}`)) return;
    const desde = ruta.length > 0 ? ruta[0] : [tu.i, tu.j];
    if (ruta.length === 0 && desde[0] === i && desde[1] === j) return;
    const pasos = camino(depto.ancho, depto.fondo, ocupado, desde, [i, j]);
    const yaVaAhi = desde[0] === i && desde[1] === j;
    if (quieto() || (pasos.length === 0 && !yaVaAhi)) {
      ruta = [];
      tu = { i, j };
      dibujar();
      return;
    }
    ruta = ruta.length > 0 ? [ruta[0], ...pasos] : pasos;
    pedirCuadro();
  }

  // --- elegir, y lo que llevas en la mano ------------------------------------------------

  const indicacionDe = (mano) => (mano.mueble.capa === PARED ? TOCA_LA_PARED : TOCA_LA_CASILLA);

  // Lo que se dice en la zona de aviso. Un aviso se borra solo al rato; pero
  // mientras llevas algo en la mano lo dicho no se borra solo (se le quita a la
  // zona su borrado, `aviso.parar`): la indicación de dónde tocar se queda hasta
  // que lo pongas o lo sueltes, y otro aviso la sustituye un rato y después
  // vuelve ella.
  function decir(texto, esError = false) {
    clearTimeout(volverAIndicar);
    avisar(texto, esError);
    if (!enLaMano) return;
    aviso.parar();
    if (texto !== indicacionDe(enLaMano)) volverAIndicar = setTimeout(indicar, UN_AVISO_DURA_MS);
  }

  function indicar() {
    if (sigueAqui() && enLaMano) decir(indicacionDe(enLaMano));
  }

  // Lo que se ve de lo elegido y de lo que llevas en la mano: las marcas, el
  // menú y, en la bandeja, cuál llevas.
  function verLoElegido() {
    dibujar();
    ponerMenu();
    marcarLoQueLlevas();
  }

  function elegir(id) {
    if (elegido === id) return;
    elegido = id;
    verLoElegido();
  }

  // Lo tomas en la mano y se marcan sus sitios; si no cabe en ninguno, se dice
  // y no lo tomas.
  function tomar(mano) {
    if (!mano || !mano.sitios.length) {
      decir(NO_CABE, true);
      return;
    }
    enLaMano = mano;
    decir(indicacionDe(mano));
    verLoElegido();
  }

  // Lo sueltas sin ponerlo: lo que movías deja de estar elegido.
  function soltar() {
    if (!enLaMano) return;
    if (enLaMano.tipo === null) elegido = null;
    enLaMano = null;
    decir('');
    verLoElegido();
  }

  // Con algo en la mano, el toque es sólo un sitio (una casilla o un tramo de
  // pared, sin mirar lo que haya dibujado encima): si está marcado, ahí se
  // pone, con el giro con el que cabe; si no, se suelta.
  function ponerLoQueLlevasEn(x, y) {
    const { mueble, sitios } = enLaMano;
    const sitio = mueble.capa === PARED
      ? tramoEn(m, x, y, depto.ancho, depto.fondo)
      : casillaEn(m, x, y, depto.ancho, depto.fondo);
    const destino = sitio && sitios.find((s) => s.x === sitio[0] && s.y === sitio[1]);
    if (!destino) {
      soltar();
      return;
    }
    enLaMano = null;
    poner(mueble, destino, escenario);
    verLoElegido();
  }

  // Tocar un mueble lo elige, y tocarlo otra vez deja de elegirlo; lo que se
  // pisa (una alfombra, el felpudo) además se camina. Tocar el suelo es
  // caminar, y lo elegido deja de estarlo; tocar fuera o una pared vacía,
  // también.
  lienzo.addEventListener('click', (evento) => {
    if (!listo || !m || !sigueAqui()) return;
    const caja = lienzo.getBoundingClientRect();
    const x = evento.clientX - caja.left;
    const y = evento.clientY - caja.top;
    if (enLaMano) {
      ponerLoQueLlevasEn(x, y);
      return;
    }
    const tocado = queSeToco(m, depto, [], x, y);
    const casilla = tocado && tocado.tipo === 'casilla' ? [tocado.i, tocado.j] : null;
    // Mientras una petición va, lo elegido se queda como está: sólo se camina.
    if (!enCamino) {
      let id = null;
      if (tocado && tocado.tipo === 'mueble') id = tocado.id;
      else if (casilla && tocado.mueble !== undefined) id = tocado.mueble;
      elegir(id === elegido ? null : id);
    }
    if (casilla) caminarHasta(casilla);
  }, { signal });

  // --- el menú del mueble elegido --------------------------------------------------------

  // El mueble para el que está hecho el menú (su id), o `null`.
  let menuDe = null;

  function botonDelMenu(icono, texto, alTocar) {
    const boton = conIcono('boton boton-chico', icono, texto);
    boton.addEventListener('click', () => alTocar(boton), { signal });
    return boton;
  }

  function hacerElMenu(puesto) {
    const botones = [botonDelMenu('✋', 'Mover', moverLoElegido)];
    // Lo de pared no se gira.
    if (puesto.capa !== PARED) botones.push(botonDelMenu('🔄', 'Girar', girarLoElegido));
    botones.push(botonDelMenu('📦', 'Guardar', guardarLoElegido));
    menu.replaceChildren(el('p', { class: 'menu-nombre' }, puesto.nombre), el('div', { class: 'menu-botones' }, botones));
    menu.setAttribute('aria-label', puesto.nombre);
    menuDe = puesto.id;
  }

  // Sobre el mueble, centrado, y nunca fuera de la pieza. Si arriba no cabe
  // entero, se queda pegado arriba aunque tape algo del mueble; si así taparía
  // más de la mitad, va debajo.
  function colocarElMenu(puesto) {
    const caja = cajaDelMueble(m, puesto, puesto.x, puesto.y, puesto.giro);
    const lado = lienzo.getBoundingClientRect();
    const ancho = menu.offsetWidth || 0;
    const alto = menu.offsetHeight || 0;
    const izquierda = Math.min(Math.max(caja.x + caja.ancho / 2, ancho / 2 + MARGEN_DEL_MENU),
      lado.width - ancho / 2 - MARGEN_DEL_MENU);
    // `top` es el borde de abajo del menú.
    let abajo = caja.y - MARGEN_DEL_MENU;
    const pegadoArriba = alto + MARGEN_DEL_MENU;
    if (abajo < pegadoArriba) {
      abajo = pegadoArriba - abajo > caja.alto / 2 ? caja.y + caja.alto + MARGEN_DEL_MENU + alto : pegadoArriba;
    }
    abajo = Math.max(Math.min(abajo, lado.height - MARGEN_DEL_MENU), pegadoArriba);
    menu.style.left = `${izquierda}px`;
    menu.style.top = `${abajo}px`;
  }

  // El menú está abierto sobre lo elegido mientras no llevas nada en la mano
  // (ni va en camino lo que pusiste tocando la pieza). El foco que estaba en un
  // menú que se cierra espera en el título.
  function ponerMenu() {
    const puesto = enLaMano || origenEnEspera === escenario ? null : elPuesto(elegido);
    if (!puesto || !listo || !m) {
      if (menu.contains(document.activeElement)) titulo.focus({ preventScroll: true });
      menu.hidden = true;
      menuDe = null;
      return;
    }
    if (menuDe !== puesto.id) hacerElMenu(puesto);
    menu.hidden = false;
    colocarElMenu(puesto);
  }

  menu.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape') elegir(null);
  }, { signal });

  function moverLoElegido() {
    const puesto = elPuesto(elegido);
    if (enCamino || !puesto) return;
    tomar(manoAlDia({ mueble: puesto, tipo: null }));
  }

  // El giro siguiente con el que cabe en su mismo sitio; si no cabe de ninguna
  // otra forma, no se manda nada.
  function girarLoElegido(boton) {
    const puesto = elPuesto(elegido);
    if (enCamino || !puesto) return;
    const giro = giroParaPoner(depto, puesto, puesto.x, puesto.y, (puesto.giro + 1) % GIROS);
    if (giro === null || giro === puesto.giro) {
      decir(NO_CABE, true);
      return;
    }
    poner(puesto, { x: puesto.x, y: puesto.y, giro }, boton);
  }

  function guardarLoElegido(boton) {
    const puesto = elPuesto(elegido);
    if (enCamino || !puesto) return;
    enviar(boton, () => pedir('POST', 'departamento/guardar', { mueble_id: puesto.id }), () => { elegido = null; });
  }

  // --- los guardados ---------------------------------------------------------------------

  // El botón de cada tipo de la bandeja, por su clave.
  const tiposEnLaBandeja = new Map();

  function marcarLoQueLlevas() {
    for (const [tipo, boton] of tiposEnLaBandeja) {
      boton.setAttribute('aria-pressed', String(Boolean(enLaMano) && enLaMano.tipo === tipo));
    }
  }

  // La bandeja, con un botón por tipo de mueble guardado. El foco que estaba
  // en uno vuelve al de ese mismo tipo; si ya no queda, al botón que la abre.
  function ponerBandeja() {
    bandeja.hidden = !bandejaAbierta;
    aLosGuardados.setAttribute('aria-expanded', String(bandejaAbierta));
    if (!bandejaAbierta || !depto) return;
    const conFoco = [...tiposEnLaBandeja].find(([, boton]) => boton === document.activeElement);
    tiposEnLaBandeja.clear();
    const rotulo = el('p', { class: 'rotulo', id: 'departamento-guardados' }, ROTULO_DE_GUARDADOS);
    const tipos = porTipo(depto.guardados);
    if (!tipos.length) {
      bandeja.replaceChildren(rotulo, el('p', { class: 'bandeja-vacia' }, NADA_GUARDADO));
    } else {
      const botones = tipos.map(({ primero, cuantos }) => {
        const icono = lienzoDePieza(primero.icono, LADO_DEL_ICONO, LADO_DEL_ICONO);
        icono.classList.add('bandeja-icono');
        const boton = el('button', { type: 'button', class: 'bandeja-tipo', 'aria-pressed': 'false' },
          icono,
          el('span', { class: 'bandeja-nombre' }, `${primero.nombre} × ${cuantos}`),
          el('span', { class: 'bandeja-ocupa' }, cuantoOcupa(primero)));
        boton.addEventListener('click', () => tomarDeLaBandeja(primero.clave), { signal });
        tiposEnLaBandeja.set(primero.clave, boton);
        return boton;
      });
      bandeja.replaceChildren(rotulo,
        el('div', { class: 'bandeja-tipos', role: 'group', 'aria-labelledby': 'departamento-guardados' }, botones));
    }
    marcarLoQueLlevas();
    if (conFoco) (tiposEnLaBandeja.get(conFoco[0]) || aLosGuardados).focus({ preventScroll: true });
  }

  // Elegir uno de la bandeja lo pone en la mano, empezando por el giro 0;
  // elegir el que ya llevas lo suelta. Si no cabe en ningún sitio no se toma:
  // se dice, y lo elegido y lo que llevabas en la mano quedan como estaban.
  function tomarDeLaBandeja(tipo) {
    if (enCamino) return;
    if (enLaMano && enLaMano.tipo === tipo) {
      soltar();
      return;
    }
    const mano = manoAlDia({ mueble: null, tipo });
    if (!mano || !mano.sitios.length) {
      decir(NO_CABE, true);
      return;
    }
    elegido = null;
    tomar(mano);
  }

  // Abrir o cerrar la bandeja; al abrirla se trae a la vista (en un computador
  // puede quedar bajo el borde de la ventana) y al cerrarla se suelta lo que
  // salió de ella.
  aLosGuardados.addEventListener('click', () => {
    bandejaAbierta = !bandejaAbierta;
    if (!bandejaAbierta && enLaMano && enLaMano.tipo !== null) soltar();
    ponerBandeja();
    if (bandejaAbierta) bandeja.scrollIntoView({ block: 'nearest' });
  }, { signal });

  // --- ampliar ---------------------------------------------------------------------------

  // Lo de ampliar va en lugar de lo de la derecha: un botón por cada lado que
  // todavía puede crecer, con lo que suma y lo que cuesta, y «Volver». El foco
  // que estaba en él vuelve a lo mismo: el rótulo, ese lado o, si ya no puede
  // crecer por ahí, «Volver».
  function ponerAmpliar() {
    derecha.hidden = ampliando;
    panelAmpliar.hidden = !ampliando;
    if (!ampliando || !depto) return;
    const conFoco = panelAmpliar.contains(document.activeElement) ? document.activeElement : null;
    const lados = [
      { eje: 'fondo', que: 'fila', casillas: depto.ancho, coste: depto.ampliar.fondo },
      { eje: 'ancho', que: 'columna', casillas: depto.fondo, coste: depto.ampliar.ancho },
    ].filter(({ coste }) => coste !== null && coste !== undefined);
    const rotulo = el('h2', { class: 'rotulo', id: 'departamento-ampliar', tabindex: '-1' }, ROTULO_DE_AMPLIAR);
    const volver = el('button', { type: 'button', class: 'boton boton-volver' }, 'Volver');
    volver.addEventListener('click', () => {
      ampliando = false;
      ponerAmpliar();
      alAmpliar.focus({ preventScroll: true });
    }, { signal });
    let opciones;
    if (lados.length) {
      opciones = el('div', { class: 'ampliar-lados', role: 'group', 'aria-labelledby': 'departamento-ampliar' },
        lados.map(({ eje, que, casillas, coste }) => {
          // Se ve con el símbolo y se lee con la palabra, como los saldos.
          const boton = el('button', { type: 'button', class: 'boton boton-lado', 'data-eje': eje },
            el('span', {}, `+ ${que} (${casillas} casillas) · `,
              el('span', { 'aria-hidden': 'true' }, `${coste} ${MONEDAS.simbolo}`),
              el('span', { class: 'solo-lector' }, MONEDAS.cuantas(coste))));
          boton.addEventListener('click', () => ampliar(eje, boton), { signal });
          return boton;
        }));
    } else {
      opciones = el('p', { class: 'ampliar-tope' }, YA_NO_CRECE);
    }
    panelAmpliar.replaceChildren(rotulo, opciones, volver);
    if (conFoco) {
      const eje = conFoco.getAttribute('data-eje');
      const mismo = eje && [...panelAmpliar.querySelectorAll('button')].find((b) => b.getAttribute('data-eje') === eje);
      (conFoco.classList.contains('rotulo') ? rotulo : mismo || volver).focus({ preventScroll: true });
    }
  }

  alAmpliar.addEventListener('click', () => {
    ampliando = true;
    ponerAmpliar();
    const rotulo = panelAmpliar.querySelector('h2');
    if (rotulo) rotulo.focus({ preventScroll: true });
  }, { signal });

  // Crecer por ese lado. Cuesta monedas: cada toque lleva su evento, y sus
  // reintentos el mismo, para que no se cobre dos veces.
  function ampliar(eje, boton) {
    if (enCamino) return;
    const evento = nuevoEvento();
    enviar(boton, () => conReintentos(() => pedir('POST', 'departamento/ampliar', { eje, evento_id: evento }), sigueAqui), null);
  }

  // --- mandar lo que se hace -------------------------------------------------------------

  // Los botones que mandan algo o te lo ponen en la mano.
  const queMandan = () => cuerpo.querySelectorAll('.menu-de-la-pieza button, .bandeja-tipo, .boton-lado');

  function esperar(origen) {
    enCamino = true;
    origenEnEspera = origen;
    origen.setAttribute('aria-busy', 'true');
    origen.classList.add(origen === escenario ? 'en-camino' : 'esperando');
    for (const boton of queMandan()) if (boton !== origen) boton.setAttribute('aria-disabled', 'true');
  }

  function dejarDeEsperar() {
    enCamino = false;
    origenEnEspera.removeAttribute('aria-busy');
    origenEnEspera.classList.remove('en-camino', 'esperando');
    origenEnEspera = null;
    for (const boton of queMandan()) boton.removeAttribute('aria-disabled');
    ponerMenu();
  }

  // Manda lo que hace `hacer()` y pinta la pieza que contesta el servidor.
  // `siSaleBien()` deja elegido lo que toque. Un «no» se dice con su frase y
  // la pieza queda como dice el servidor; sin respuesta, pudo haber llegado
  // igual: se dice y la pieza se vuelve a leer.
  async function enviar(origen, hacer, siSaleBien) {
    if (enCamino) return;
    acciones += 1;
    esperar(origen);
    decir('');
    let respuesta;
    try {
      respuesta = await hacer();
    } catch (error) {
      if (!sigueAqui()) return;
      dejarDeEsperar();
      if (hayQueDecidirDeNuevo(error)) {
        irse();
        return;
      }
      decir(error && error.clave === null ? SIN_RESPUESTA : mensajeDe(error), true);
      releer({ trasUnaAccion: true });
      return;
    }
    if (!sigueAqui()) return;
    dejarDeEsperar();
    if (respuesta.estado && !aplicarEstado(respuesta.estado)) return;
    if (respuesta.ok && siSaleBien) siSaleBien();
    aplicarDepto(respuesta.departamento);
    decir(respuesta.mensaje, !respuesta.ok);
  }

  // Lo que se pone (o se mueve, o se gira) queda elegido.
  function poner(mueble, { x, y, giro }, origen) {
    enviar(origen, () => pedir('POST', 'departamento/poner', { mueble_id: mueble.id, x, y, giro }),
      () => { elegido = mueble.id; });
  }

  // --- mantenerse al día -----------------------------------------------------------------

  // Las lecturas que salieron: sólo se pinta la última.
  let lecturas = 0;
  let leyendo = false;

  // Una relectura que falla no borra la pieza ni dice nada: la próxima vuelta
  // lo intenta otra vez. Sin sesión, o si ya no estás en tu casa, se va.
  // Mientras una acción va no se lee: lo que traiga es más nuevo. La de tras
  // una acción sin respuesta sale aunque haya otra en camino.
  async function releer({ trasUnaAccion = false } = {}) {
    if (!sigueAqui() || !depto || enCamino) return;
    if (!trasUnaAccion && (leyendo || document.hidden)) return;
    leyendo = true;
    const esta = ++lecturas;
    const hechas = acciones;
    try {
      const nuevo = await pedir('GET', 'departamento');
      if (sigueAqui() && esta === lecturas && hechas === acciones) aplicarDepto(nuevo);
    } catch (error) {
      if (sigueAqui() && hayQueDecidirDeNuevo(error)) irse();
    } finally {
      if (esta === lecturas) leyendo = false;
    }
  }

  document.addEventListener('visibilitychange', () => {
    if (!sigueAqui() || document.hidden) return;
    clearInterval(cadaTanto);
    cadaTanto = setInterval(releer, PEDIR_CADA_MS);
    releer();
  }, { signal });

  // --- la primera vez --------------------------------------------------------------------

  // Con lo que llega la primera vez se pinta en cuanto está su arte (el arte
  // nunca falla: lo que no carga se dibuja como su recuadro).
  async function prepararLaPieza(leido) {
    await Promise.all([aplicarDepto(leido), traerAvatar()]);
    if (!sigueAqui()) return;
    listo = true;
    deLaPieza.hidden = false;

    // Girar el teléfono o cambiar el tamaño de la ventana vuelve a medir la pieza.
    const reencuadrar = () => {
      if (sigueAqui() && medirLienzo()) {
        dibujar();
        ponerMenu();
      }
    };
    if (typeof ResizeObserver === 'function') {
      observador = new ResizeObserver(reencuadrar);
      observador.observe(lienzo);
    } else {
      window.addEventListener('resize', reencuadrar, { signal });
    }
    reencuadrar();
  }

  // Lo que devuelve la pantalla acaba cuando la pieza queda preparada, la
  // primera vez o tras «Volver a intentarlo»: si algo revienta al prepararla,
  // falla, y `principal.js` lo lleva a la avería.
  let terminar;
  const preparada = new Promise((bien, mal) => { terminar = { bien, mal }; });

  // La pieza común de la tienda y la mochila: mientras no llega se lee la
  // espera; si no llega, su mensaje y «Volver a intentarlo». Sin sesión o si ya
  // no estás en tu casa, se va.
  const laPieza = listaQueSePide({
    ruta: 'departamento',
    espera,
    lista: pieza,
    cargando: CARGANDO,
    titulo,
    sigueAqui,
    irse,
    alLlegar: (leido) => { prepararLaPieza(leido).then(terminar.bien, terminar.mal); },
  });

  if (!aplicarEstado(estado)) return undefined;
  cadaTanto = setInterval(releer, PEDIR_CADA_MS);
  laPieza.cargar().catch(terminar.mal);
  return preparada;
}
