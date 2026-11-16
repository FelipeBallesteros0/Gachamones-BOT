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
// El servidor manda: la pieza se pinta como llega, y lo que se calcula aquí
// (por dónde se camina, qué se tocó) sirve sólo para dibujar. El lienzo sólo se
// mira (`aria-hidden`); lo que dice va en la línea. Todo texto entra por `el` o
// por `textContent`. Lo que corre (el cuadro de animación, la relectura y los
// oyentes) se detiene al salir, y una respuesta que llega tarde no pinta.

import { pedir } from './api.js';
import { cargar, olvidarLasQueFaltan } from './arte.js';
import { cabeceraConSaldos, hayQueDecidirDeNuevo, mensajeDe, pideOtraPantalla, zonaDeAviso } from './articulos.js';
import { cargarAvatar, poseAlCaminar } from './avatar.js';
import { camino, lineaDeEstado, noSePisan, sitiosDeEntrada } from './casillas.js';
import { el } from './dom.js';
import { dibujarPieza, rutasDeLaPieza } from './pieza.js';
import { medir, queSeToco } from './proyeccion.js';

const VISTA = 'departamento';
const PEDIR_CADA_MS = 30_000;
const DENSIDAD_MAXIMA = 3;
// Lo que anda tu avatar, en casillas por segundo.
const CASILLAS_POR_SEGUNDO = 3;

const CARGANDO = 'Cargando…';
const SIN_RESPUESTA = 'No hubo respuesta. Revisa tu conexión.';

// Por qué no llegó la pieza: si el juego no contestó, que no hubo respuesta;
// si contestó que no, su frase.
function porQueNoLlego(error) {
  return error && error.clave === null ? SIN_RESPUESTA : mensajeDe(error);
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

  // --- la cabecera, la pieza, lo que se dice y las salidas ------------------------------

  const { cabecera, titulo, ponerSaldos } = cabeceraConSaldos('📍', estado.lugar.nombre);

  const lienzo = el('canvas', { class: 'pieza-lienzo', 'aria-hidden': 'true' });
  const linea = el('p', { class: 'pieza-linea' });
  // Mientras no llega, en su lugar se lee la espera (o por qué no llegó).
  const pieza = el('div', { class: 'pieza', hidden: true }, lienzo, linea);
  const espera = el('div', { class: 'espera-tienda' });

  const aviso = zonaDeAviso();
  aviso.nodo.classList.add('aviso');

  const aLaMochila = el('button', { type: 'button', class: 'boton boton-mochila' },
    el('span', { 'aria-hidden': 'true' }, '🎒'), 'Mochila');
  const alPueblo = el('button', { type: 'button', class: 'boton boton-pueblo' },
    el('span', { 'aria-hidden': 'true' }, '🗺️'), 'Pueblo');

  const cuerpo = el('div', { class: 'cuerpo cuerpo-departamento' },
    espera, pieza, aviso.nodo, el('div', { class: 'salidas-lugar' }, aLaMochila, alPueblo));
  contenedor.append(cabecera, cuerpo);

  function parar() {
    vivo = false;
    if (cuadroPedido !== null) cancelAnimationFrame(cuadroPedido);
    cuadroPedido = null;
    clearInterval(cadaTanto);
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

  // --- la pieza que llega ---------------------------------------------------------------

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

  // Pone la pieza que llegó: su línea, los saldos y, si todavía no estabas en
  // ella, tu avatar en la entrada. Devuelve cuándo llega su arte.
  function aplicarDepto(nuevo) {
    depto = nuevo;
    linea.textContent = lineaDeEstado(nuevo);
    ponerSaldos(nuevo.saldos);
    actual = { ...actual, saldos: nuevo.saldos };
    if (!tu) {
      const [entrada] = sitiosDeEntrada(nuevo.ancho, nuevo.fondo, noSePisan(nuevo), 1);
      if (entrada) tu = { i: entrada[0], j: entrada[1] };
    }
    if (listo && medirLienzo()) dibujar();
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

  function dibujar() {
    if (!listo || !m) return;
    const ctx = lienzo.getContext('2d');
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, lienzo.width, lienzo.height);
    ctx.setTransform(escala[0], 0, 0, escala[1], 0, 0);
    dibujarPieza(ctx, m, {
      depto,
      cargadas,
      gachamones: [],
      tu: tu && { i: tu.i, j: tu.j, pose: poseAlCaminar(andado, ruta.length > 0), espejo, avatar: actual.avatar },
      libres: [],
      elegido: null,
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

  // Tocar una casilla que se pisa es caminar hasta ella; lo demás, de momento, no hace nada.
  lienzo.addEventListener('click', (evento) => {
    if (!listo || !m || !sigueAqui()) return;
    const caja = lienzo.getBoundingClientRect();
    const tocado = queSeToco(m, depto, [], evento.clientX - caja.left, evento.clientY - caja.top);
    if (tocado && tocado.tipo === 'casilla') caminarHasta([tocado.i, tocado.j]);
  }, { signal });

  // --- mantenerse al día -----------------------------------------------------------------

  // Cada acción que cambia la pieza suma uno: una lectura que salió antes ya
  // no se pinta, porque lo que trae la acción es más nuevo.
  let acciones = 0;
  let leyendo = false;

  // Una relectura que falla no borra la pieza ni dice nada: la próxima vuelta
  // lo intenta otra vez. Sin sesión, o si ya no estás en tu casa, se va.
  async function releer() {
    if (!sigueAqui() || leyendo || !depto || document.hidden) return;
    leyendo = true;
    const hechas = acciones;
    try {
      const nuevo = await pedir('GET', 'departamento');
      if (sigueAqui() && hechas === acciones) aplicarDepto(nuevo);
    } catch (error) {
      if (sigueAqui() && hayQueDecidirDeNuevo(error)) irse();
    } finally {
      leyendo = false;
    }
  }

  document.addEventListener('visibilitychange', () => {
    if (!sigueAqui() || document.hidden) return;
    clearInterval(cadaTanto);
    cadaTanto = setInterval(releer, PEDIR_CADA_MS);
    releer();
  }, { signal });

  // --- la primera vez --------------------------------------------------------------------

  // Como la tienda y la mochila: mientras no llega se lee la espera; si no
  // llega, por qué y «Volver a intentarlo», que la pide otra vez con el foco
  // esperando en el título. Sin sesión o si ya no estás en tu casa, se va.
  async function primeraLectura(trasReintentar = false) {
    espera.hidden = false;
    espera.replaceChildren(el('p', { class: 'espera-tienda-texto', role: 'status' }, CARGANDO));
    let leido;
    try {
      leido = await pedir('GET', 'departamento');
    } catch (error) {
      if (!sigueAqui()) return;
      if (hayQueDecidirDeNuevo(error)) {
        irse();
        return;
      }
      const reintentar = el('button', { type: 'button', class: 'boton boton-chico principal' }, 'Volver a intentarlo');
      reintentar.addEventListener('click', () => {
        // El botón se borra al reintentar: el foco espera en el título.
        titulo.focus({ preventScroll: true });
        primeraLectura(true);
      }, { signal });
      espera.replaceChildren(
        el('p', { class: 'espera-tienda-texto es-error', role: 'alert' }, porQueNoLlego(error)), reintentar);
      if (trasReintentar) reintentar.focus({ preventScroll: true });
      return;
    }
    if (!sigueAqui()) return;
    espera.replaceChildren();
    espera.hidden = true;
    pieza.hidden = false;
    // El arte nunca falla: lo que no carga se dibuja como su recuadro.
    await Promise.all([aplicarDepto(leido), traerAvatar()]);
    if (!sigueAqui()) return;
    listo = true;

    // Girar el teléfono o cambiar el tamaño de la ventana vuelve a medir la pieza.
    const reencuadrar = () => {
      if (sigueAqui() && medirLienzo()) dibujar();
    };
    if (typeof ResizeObserver === 'function') {
      observador = new ResizeObserver(reencuadrar);
      observador.observe(lienzo);
    } else {
      window.addEventListener('resize', reencuadrar, { signal });
    }
    reencuadrar();
  }

  if (!aplicarEstado(estado)) return undefined;
  cadaTanto = setInterval(releer, PEDIR_CADA_MS);
  return primeraLectura();
}
