// La pantalla principal: el lugar del pueblo donde estás, con su dibujo de
// fondo y, si lo tiene, su aviso. Ahí ves a tu gachamon en grande, te habla en
// un globo, lo acaricias y lo cuidas, y de ahí sales al pueblo, abres su ficha
// completa o la mochila o, donde el lugar tiene la tienda, entras a comprar, y
// donde tiene la incubadora, a tu plantel. Sin ningún gachamon, el lugar se
// ve con tu avatar solo, su aviso y sus salidas: sin ficha, sin globo y sin
// cuidados, y dónde estás es el título de la pantalla; y donde el lugar ofrece
// la primera aventura («Aventura»), se sale a ella como a comprar, salvo
// mientras el lugar avise de lo que falta para ella (la cama).
//
// `lugar(contenedor, estado, seguir, llegando)` pinta la pantalla con el
// estado ya leído y la mantiene al día: vuelve a pedir el estado cada 30
// segundos y al volver a la pestaña, baja sola las cuentas de espera de los
// cuidados y hace hablar al gachamon de vez en cuando. Con `llegando` (se
// acaba de llegar caminando), su primer globo sale enseguida y habla del
// lugar, salvo que necesite algo. Si lo que llega pide otra pantalla (hay uno
// sin nombre, ya no es el mismo, llegó uno o ya no está) se lo pasa a
// `seguir`. Todo lo que temporiza se detiene en cuanto la pantalla deja de
// estar en la página.
//
// Las reglas son del servidor: en qué lugar estás y qué se avisa ahí, y las
// barras, que se pintan con lo que dice el estado sin simular el paso del
// tiempo; lo único que corre aquí son las cuentas de espera. Todo texto entra
// por `el` o por `textContent`. Lo que hace igual que tu departamento (los
// cuidados, las barras, las esperas y qué se celebra y qué se avisa tras un
// cuidado o una caricia) está en `cuidados.js`. La escena (el fondo del lugar
// y tu monigote) la comparte con la pantalla de la primera aventura: por eso
// se exporta (`fondoDeLaEscena`, `monigoteDeLaEscena`).

import { conReintentos, nuevoEvento, pedir } from './api.js';
import { cargar, faltante, lienzoDePieza, olvidarLasQueFaltan } from './arte.js';
import { lienzoDelAvatar } from './avatar.js';
import {
  BARRAS, CUIDADOS, avisoDeLaEvolucion, avisoDeMedalla, botonDeCuidado, contarCuidado, faltaPara, medidorDe,
  pintarMedidores, ponerEsperas, segun, trasAcariciar, trasCuidar,
} from './cuidados.js';
import { el } from './dom.js';
import {
  ofreceLaAventura, ofreceLaIncubadora, ofreceLaTienda, siguiente,
} from './pantallas.js';
import { cuantasGemas, cuantasMonedas, elegirGlobo } from './tiempo.js';

const PEDIR_ESTADO_CADA_MS = 30_000;
const PRIMER_GLOBO_MS = 2500;
// Al llegar caminando, el gachamon dice algo del lugar casi en cuanto entras.
const PRIMER_GLOBO_AL_LLEGAR_MS = 600;
const GLOBO_CADA_MS = [20_000, 40_000];
const GLOBO_DURA_MS = 7000;
const AVISO_DURA_MS = 5000;
const GANANCIA_DURA_MS = 2400;
const CELEBRACION_DURA_MS = 4500;
const MEDALLA_DURA_MS = 6000;
const CORAZONES = 6;
const CORAZON_DURA_MS = 1600;
const ALGO_SALIO_MAL = 'Algo salió mal. Vuelve a intentarlo.';

// --- la escena de un lugar: la de esta pantalla y la de la primera aventura -----------

// Lo que mide de alto el avatar en la escena, en píxeles de pantalla: en el
// computador se ve más grande.
const ALTO_DEL_AVATAR = 126;
const ALTO_DEL_AVATAR_EN_COMPUTADOR = 168;
const DENSIDAD_MAXIMA = 3;

// El fondo de la escena de cada lugar, una pieza del contrato del arte.
const escenaDe = (clave) => `escenas/${clave}.png`;

// El dibujo del lugar en el lienzo `lienzo` del fondo de la escena.
// `poner(clave)` pone el de ese lugar: si cambió el lugar, el dibujo del
// anterior se quita en el acto y el nuevo se pinta en cuanto llega; uno que
// llega tarde, de un lugar que ya no es, o cuando `sigue()` ya es falso (se
// dejó la pantalla), no se pinta. El dibujo cubre toda la escena sin
// deformarse: si la escena no tiene su forma, se recorta lo que sobra por los
// lados o por arriba y abajo, por igual. Con los píxeles de la pantalla y sin
// suavizar, que es un dibujo de cuadros. Si no cargó, su recuadro deja ver la
// pared y el piso de debajo. La escena cambia de tamaño al girar el teléfono
// o la ventana: el fondo se vuelve a pintar a su medida (lo que escucha para
// eso se deja con `signal` o con `parar()`).
export function fondoDeLaEscena(lienzo, { sigue, signal }) {
  // La pieza del lugar donde estás, cuando ya llegó: `{ruta, imagen}`, con
  // `imagen` en `null` si no se pudo cargar.
  let rutaDelFondo = null;
  let piezaDelFondo = null;
  let observador = null;

  function dibujar() {
    const ancho = lienzo.clientWidth;
    const alto = lienzo.clientHeight;
    if (!ancho || !alto) return;
    const densidad = Math.min(Math.max(window.devicePixelRatio || 1, 1), DENSIDAD_MAXIMA);
    const anchoReal = Math.round(ancho * densidad);
    const altoReal = Math.round(alto * densidad);
    // Cambiar el tamaño borra el lienzo: sólo si de verdad cambia.
    if (lienzo.width !== anchoReal) lienzo.width = anchoReal;
    if (lienzo.height !== altoReal) lienzo.height = altoReal;
    const ctx = lienzo.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, anchoReal, altoReal);
    if (!piezaDelFondo) return;
    const { imagen } = piezaDelFondo;
    if (!imagen) {
      faltante(ctx, 0, 0, anchoReal, altoReal, piezaDelFondo.ruta);
      return;
    }
    const escala = Math.max(anchoReal / imagen.naturalWidth, altoReal / imagen.naturalHeight);
    const anchoVisto = anchoReal / escala;
    const altoVisto = altoReal / escala;
    ctx.drawImage(imagen,
      (imagen.naturalWidth - anchoVisto) / 2, (imagen.naturalHeight - altoVisto) / 2, anchoVisto, altoVisto,
      0, 0, anchoReal, altoReal);
  }

  function poner(clave) {
    const ruta = escenaDe(clave);
    if (ruta === rutaDelFondo) return;
    rutaDelFondo = ruta;
    piezaDelFondo = null;
    dibujar();
    cargar(ruta).then((cargada) => {
      if (!sigue() || cargada.ruta !== rutaDelFondo) return;
      piezaDelFondo = cargada;
      dibujar();
    });
  }

  if (typeof ResizeObserver === 'function') {
    observador = new ResizeObserver(dibujar);
    observador.observe(lienzo);
  } else {
    window.addEventListener('resize', dibujar, { signal });
  }

  return {
    poner,
    parar() {
      if (observador) observador.disconnect();
    },
  };
}

// Tu avatar quieto en el lienzo `lienzo` de la escena, con el avatar que dé
// `avatarDe()`; en el computador, más grande. Devuelve con qué pintarlo, y se
// vuelve a pintar solo al cruzar el ancho del computador (lo que escucha para
// eso se deja con `signal`).
export function monigoteDeLaEscena(lienzo, avatarDe, signal) {
  const ancho = window.matchMedia('(min-width: 900px)');
  const pintar = () => lienzoDelAvatar(
    lienzo, avatarDe(), ancho.matches ? ALTO_DEL_AVATAR_EN_COMPUTADOR : ALTO_DEL_AVATAR,
  );
  ancho.addEventListener('change', pintar, { signal });
  return pintar;
}

// --- la pantalla del lugar ---------------------------------------------------------------

function mensajeDe(error) {
  return error && typeof error.mensaje === 'string' && error.mensaje ? error.mensaje : ALGO_SALIO_MAL;
}

// Mientras se está aquí hay sesión y la cuenta ya no es nueva, así que la
// pantalla la decide sólo el estado, con la misma regla de siempre.
function pideOtraPantalla(estado) {
  return siguiente(true, { estado: 'en juego' }, estado) !== 'lugar';
}

// Si de ese lugar (`estado.lugar`) se sale ya a la primera aventura: el
// servidor la ofrece a quien no tiene ningún gachamon y, mientras le falta la
// cama, el lugar lo avisa y todavía no hay encuentro.
function seSaleALaAventura(lugarDondeEsta) {
  return ofreceLaAventura(lugarDondeEsta) && !lugarDondeEsta.aviso;
}

// De qué gachamon es la pantalla: el que sale contigo, o `null` sin ninguno.
function idDelGachamon(estado) {
  return estado.gachamon ? estado.gachamon.id : null;
}

// Vuelve a lanzar una animación de CSS aunque ya estuviera puesta.
function animar(nodo, clase) {
  nodo.classList.remove(clase);
  void nodo.offsetWidth;
  nodo.classList.add(clase);
}

export function lugar(contenedor, estado, seguir, llegando = false) {
  // El arte que no cargó en otra pantalla se pide de nuevo.
  olvidarLasQueFaltan();
  const id = idDelGachamon(estado);
  // Sin gachamon no se arma nada de lo suyo: si llega uno, es otra pantalla.
  const conGachamon = Boolean(estado.gachamon);
  let actual = estado;
  let ultimoAhora = -Infinity;
  let vivo = true;

  // Lo que corre por su cuenta, para pararlo todo de una vez.
  const temporizadores = new Set();
  const oyentes = new AbortController();
  let cadaSegundo = null;
  let cadaTanto = null;
  // El fondo de la escena (se pone al pintar el lugar).
  let elFondo = null;

  function luego(ms, hacer) {
    const marca = setTimeout(() => {
      temporizadores.delete(marca);
      if (vivo) hacer();
    }, ms);
    temporizadores.add(marca);
    return marca;
  }

  function cancelar(marca) {
    clearTimeout(marca);
    temporizadores.delete(marca);
  }

  function parar() {
    vivo = false;
    for (const marca of temporizadores) clearTimeout(marca);
    temporizadores.clear();
    clearInterval(cadaSegundo);
    clearInterval(cadaTanto);
    oyentes.abort();
    if (elFondo) elFondo.parar();
  }

  // Deja la pantalla y que se decida otra: con el estado que llegó, o
  // preguntando todo otra vez.
  function irse(estadoNuevo) {
    parar();
    seguir(estadoNuevo);
  }

  // --- la cabecera: dónde estás y lo que tienes ---------------------------------

  const donde = el('span', {});
  const monedasVisibles = el('span', { 'aria-hidden': 'true' });
  const monedasLeidas = el('span', { class: 'solo-lector' });
  const gemasVisibles = el('span', { 'aria-hidden': 'true' });
  const gemasLeidas = el('span', { class: 'solo-lector' });
  const ganancia = el('span', { class: 'ganancia', role: 'status' });
  // Con gachamon, el título de la pantalla es su nombre, en la ficha; sin él,
  // dónde estás.
  const cabecera = el('header', { class: 'barra barra-lugar' },
    el(conGachamon ? 'span' : 'h1', { class: 'donde', tabindex: conGachamon ? null : '-1' },
      el('span', { 'aria-hidden': 'true' }, '📍'), donde),
    el('span', { class: 'saldos' },
      el('span', { class: 'saldo saldo-monedas' }, monedasVisibles, monedasLeidas, ganancia),
      el('span', { class: 'saldo' }, gemasVisibles, gemasLeidas)));

  // --- la escena ------------------------------------------------------------------

  // El dibujo del lugar va encima de la pared, el piso y la ventana de
  // siempre, y debajo de todo lo demás.
  const fondo = el('canvas', { class: 'escena-fondo', 'aria-hidden': 'true' });
  const monigote = el('canvas', { class: 'monigote-lugar', 'aria-hidden': 'true' });
  const primero = estado.gachamon;
  const retrato = el('img', {
    class: 'retrato', src: primero && primero.retrato, alt: primero && primero.nombre, draggable: 'false',
  });
  const sinRetrato = el('span', { class: 'retrato-sin', 'aria-hidden': 'true', hidden: true }, primero && primero.emoji);
  retrato.addEventListener('error', () => {
    retrato.hidden = true;
    sinRetrato.hidden = false;
  });
  retrato.addEventListener('load', () => {
    retrato.hidden = false;
    sinRetrato.hidden = true;
  });
  const gachamon = el('button', { type: 'button', class: 'gachamon' }, retrato, sinRetrato);
  const globo = el('p', { class: 'globo', 'aria-live': 'polite' });
  // La zona está siempre; el aviso de la evolución entra y sale de ella. Las
  // medallas nuevas van abajo, una por línea, para no tapar a la evolución.
  const celebracion = el('div', { class: 'celebracion', role: 'status' });
  const medallas = el('div', { class: 'medallas', role: 'status' });
  const escena = el('div', { class: 'escena escena-lugar' },
    fondo,
    el('span', { class: 'ventana', 'aria-hidden': 'true' }),
    monigote,
    conGachamon ? [gachamon, globo, celebracion, medallas] : null);

  // --- la ficha -------------------------------------------------------------------

  // El nombre y, si lleva uno, su título («Pelusa la Invicta»), que llega ya
  // concordado.
  const nombreDelGachamon = el('span', {});
  const tituloDelGachamon = el('span', { class: 'titulo-del-gachamon' });
  const titulo = el('h1', { tabindex: '-1' }, nombreDelGachamon, tituloDelGachamon);
  const insignia = el('p', { class: 'insignia', hidden: true });
  const detalle = el('p', { class: 'ficha-detalle' });
  const medidores = BARRAS.map(medidorDe);
  // La ficha completa (estadísticas, experiencia, medallas…) se abre aparte.
  const aLaFicha = el('button', { type: 'button', class: 'boton boton-chico boton-ver-ficha' }, 'Ver ficha');
  aLaFicha.addEventListener('click', () => {
    parar();
    seguir(actual, { vista: 'ficha' });
  });
  const ficha = el('section', { class: 'ficha', 'aria-label': 'Ficha' },
    el('div', { class: 'ficha-cabeza' }, titulo, insignia, aLaFicha),
    detalle,
    el('div', { class: 'medidores' }, medidores.map((m) => m.nodo)));

  // Bajo la ficha, primero lo que hay que saber de este lugar (que abre más
  // adelante, que cerró…), en su franja: no es un error, y se queda mientras el
  // servidor lo diga; sin aviso, no hay franja.
  const franjaDelLugar = el('p', { class: 'franja-del-lugar', hidden: true });

  // Después, lo que contesta el juego, o, si no hay nada que decir, la pista de
  // que se le puede acariciar.
  const aviso = el('p', { class: 'aviso-lugar', 'aria-live': 'polite' });
  const pista = el('p', { class: 'pista-lugar' });
  const avisos = el('div', { class: 'avisos-lugar' }, aviso, pista);
  const bajoLaFicha = el('div', { class: 'bajo-la-ficha' }, franjaDelLugar, conGachamon ? avisos : null);

  // --- los cuidados ---------------------------------------------------------------

  const cuidados = CUIDADOS.map((datos) => {
    const cuidado = botonDeCuidado(datos);
    cuidado.nodo.addEventListener('click', () => cuidar(cuidado));
    return cuidado;
  });

  // --- comprar, tu plantel o la aventura (donde se ofrece), la mochila e ir al pueblo ----

  // Se ve sólo mientras el lugar donde estás tenga la tienda.
  const aComprar = el('button', { type: 'button', class: 'boton principal boton-comprar', hidden: true },
    el('span', { 'aria-hidden': 'true' }, '🛒'), 'Comprar');
  aComprar.addEventListener('click', () => {
    parar();
    seguir(actual, { vista: 'tienda' });
  });

  // En el mismo sitio, sólo mientras el lugar donde estás tenga la incubadora.
  const aTuPlantel = el('button', { type: 'button', class: 'boton principal boton-plantel', hidden: true },
    el('span', { 'aria-hidden': 'true' }, '🥚'), 'Tu plantel');
  aTuPlantel.addEventListener('click', () => {
    parar();
    seguir(actual, { vista: 'incubadora' });
  });

  // En el mismo sitio, sólo mientras se pueda salir a la primera aventura.
  const aLaAventura = el('button', { type: 'button', class: 'boton principal boton-aventura', hidden: true },
    el('span', { 'aria-hidden': 'true' }, '🧭'), 'La primera aventura');
  aLaAventura.addEventListener('click', () => {
    parar();
    seguir(actual, { vista: 'aventura' });
  });

  const alPueblo = el('button', { type: 'button', class: 'boton boton-pueblo' },
    el('span', { 'aria-hidden': 'true' }, '🗺️'), 'Pueblo');
  alPueblo.addEventListener('click', () => {
    parar();
    seguir(actual, { vista: 'pueblo' });
  });

  // La mochila se abre desde cualquier lugar.
  const aLaMochila = el('button', { type: 'button', class: 'boton boton-mochila' },
    el('span', { 'aria-hidden': 'true' }, '🎒'), 'Mochila');
  aLaMochila.addEventListener('click', () => {
    parar();
    seguir(actual, { vista: 'mochila' });
  });

  const cuerpo = el('div', { class: conGachamon ? 'cuerpo cuerpo-lugar' : 'cuerpo cuerpo-lugar sin-gachamon' },
    escena,
    conGachamon ? ficha : null,
    bajoLaFicha,
    conGachamon
      ? el('div', { class: 'cuidados', role: 'group', 'aria-label': 'Cuidados' }, cuidados.map((c) => c.nodo))
      : null,
    el('div', { class: 'salidas-lugar' }, aComprar, aTuPlantel, aLaAventura, aLaMochila, alPueblo));
  contenedor.append(cabecera, cuerpo);

  // --- pintar lo que dice el estado -----------------------------------------------

  // Cuándo se acaba cada espera, en la hora de este teléfono.
  const hasta = {};

  function aplicar(nuevo) {
    if (!vivo || !nuevo) return;
    const cuando = Date.parse(nuevo.ahora);
    // Llegó después que otro más nuevo (una lectura que se cruzó con una acción).
    if (cuando < ultimoAhora) return;
    if (pideOtraPantalla(nuevo) || idDelGachamon(nuevo) !== id) {
      irse(nuevo);
      return;
    }
    if (!Number.isNaN(cuando)) ultimoAhora = cuando;
    actual = nuevo;
    pintar();
  }

  function pintar() {
    const g = actual.gachamon;
    donde.textContent = actual.lugar.nombre;
    elFondo.poner(actual.lugar.clave);
    const avisoDelLugar = actual.lugar.aviso || '';
    if (franjaDelLugar.textContent !== avisoDelLugar) franjaDelLugar.textContent = avisoDelLugar;
    franjaDelLugar.hidden = !avisoDelLugar;
    // Sin gachamon, lo de bajo la escena es sólo el aviso: sin él, no queda un hueco.
    bajoLaFicha.hidden = !g && !avisoDelLugar;
    aComprar.hidden = !ofreceLaTienda(actual.lugar);
    // Sin gachamon no hay plantel que ver.
    aTuPlantel.hidden = !g || !ofreceLaIncubadora(actual.lugar);
    aLaAventura.hidden = !seSaleALaAventura(actual.lugar);

    const { monedas, gemas } = actual.saldos;
    monedasVisibles.textContent = `🪙 ${monedas}`;
    monedasLeidas.textContent = cuantasMonedas(monedas);
    gemasVisibles.textContent = `💎 ${gemas}`;
    gemasLeidas.textContent = cuantasGemas(gemas);

    // Lo demás es del gachamon: sin él, no hay más que pintar.
    if (!g) return;
    escena.dataset.etapa = g.etapa;

    // Sólo si cambió: volver a poner la misma dirección haría parpadear.
    if (retrato.getAttribute('src') !== g.retrato) retrato.setAttribute('src', g.retrato);
    retrato.alt = g.nombre;
    sinRetrato.textContent = g.emoji;
    gachamon.setAttribute('aria-label', `Acariciar a ${g.nombre}`);
    gachamon.classList.toggle('decaido', Boolean(g.desfallecido));

    nombreDelGachamon.textContent = g.nombre;
    tituloDelGachamon.textContent = g.titulo ? ` ${g.titulo}` : '';
    insignia.textContent = segun(g.genero, 'Desfallecido', 'Desfallecida');
    insignia.hidden = !g.desfallecido;
    detalle.textContent = `${g.nombre_especie} ${g.nombre_etapa} · nivel ${g.nivel}`;
    pintarMedidores(medidores, g.barras);

    ponerEsperas(hasta, g.esperas);

    // Un globo no dice lo que ya no pasa: si lo que pedía ya no está, se calla.
    if (globo.classList.contains('visible')
        && !actual.globos.some((gl) => gl.texto === globo.textContent)) {
      callarGlobo();
    }
    contar();
  }

  // Cada segundo: las cuentas de los cuidados y la pista de la caricia.
  function contar() {
    if (!vivo) return;
    if (!cuerpo.isConnected) {
      parar();
      return;
    }
    const g = actual.gachamon;
    if (!g) return;
    for (const c of cuidados) contarCuidado(c, faltaPara(hasta, c.accion));
    const sePuede = faltaPara(hasta, 'acariciar') === 0;
    const texto = sePuede ? `Toca a ${g.nombre} para acariciar${segun(g.genero, 'lo', 'la')}.` : '';
    if (pista.textContent !== texto) pista.textContent = texto;
    pista.hidden = Boolean(aviso.textContent);
  }

  // --- lo que se dice bajo la ficha ---------------------------------------------------

  let avisoHasta = null;

  function avisar(texto, esError = false) {
    cancelar(avisoHasta);
    aviso.textContent = texto;
    aviso.classList.toggle('es-error', esError);
    pista.hidden = true;
    avisoHasta = luego(AVISO_DURA_MS, callarAviso);
  }

  function callarAviso() {
    cancelar(avisoHasta);
    aviso.textContent = '';
    aviso.classList.remove('es-error');
    pista.hidden = false;
  }

  // Lo que ninguna acción espera: sin sesión o sin gachamon se vuelve a decidir
  // la pantalla; lo demás se dice bajo la ficha y el botón queda listo.
  function fallo(error) {
    if (error && (error.estado === 401 || error.clave === 'sin_gachamon')) {
      irse();
      return;
    }
    avisar(mensajeDe(error), true);
  }

  // --- el globo -----------------------------------------------------------------------

  let anterior = null;
  let globoHasta = null;

  // `alLlegar` vale sólo para el primer globo tras llegar caminando: los que
  // siguen son la charla de siempre.
  function hablar(alLlegar = false) {
    luego(GLOBO_CADA_MS[0] + Math.random() * (GLOBO_CADA_MS[1] - GLOBO_CADA_MS[0]), hablar);
    if (document.hidden || celebracion.hasChildNodes()) return;
    const elegido = elegirGlobo(actual.globos, anterior, Math.random, alLlegar);
    if (!elegido) return;
    anterior = elegido.texto;
    cancelar(globoHasta);
    globo.textContent = elegido.texto;
    globo.classList.add('visible');
    globoHasta = luego(GLOBO_DURA_MS, callarGlobo);
  }

  // El texto se va un poco después que el globo, para que no se vea vacío
  // mientras se desvanece; y vacío, el lector de pantalla no lo vuelve a leer.
  function callarGlobo() {
    cancelar(globoHasta);
    globo.classList.remove('visible');
    globoHasta = luego(250, () => { globo.textContent = ''; });
  }

  // --- los gestos ---------------------------------------------------------------------

  function corazones() {
    for (let i = 0; i < CORAZONES; i += 1) {
      const corazon = lienzoDePieza('efectos/corazon.png', 32, 32);
      const lado = `${Math.round(24 + Math.random() * 8)}px`;
      corazon.classList.add('corazon');
      corazon.style.width = lado;
      corazon.style.height = lado;
      corazon.style.left = `${48 + Math.random() * 30}%`;
      corazon.style.animationDelay = `${i * 90}ms`;
      escena.append(corazon);
      luego(CORAZON_DURA_MS + i * 90, () => corazon.remove());
    }
  }

  // Saltar (cuenta) o titubear (todavía no): uno quita al otro.
  function gesto(clase) {
    gachamon.classList.remove('salta', 'titubea');
    animar(gachamon, clase);
  }

  retrato.addEventListener('animationend', (evento) => {
    if (evento.animationName === 'salta' || evento.animationName === 'titubea') {
      gachamon.classList.remove('salta', 'titubea');
    }
  });

  let gananciaHasta = null;

  function ganar(monedas) {
    cancelar(gananciaHasta);
    ganancia.textContent = `+${cuantasMonedas(monedas)}`;
    animar(ganancia, 'visible');
    gananciaHasta = luego(GANANCIA_DURA_MS, () => {
      ganancia.classList.remove('visible');
      ganancia.textContent = '';
    });
  }

  let celebracionHasta = null;

  function celebrar(g) {
    callarGlobo();
    cancelar(celebracionHasta);
    celebracion.replaceChildren(avisoDeLaEvolucion(g));
    celebracionHasta = luego(CELEBRACION_DURA_MS, () => celebracion.replaceChildren());
  }

  // Una medalla nueva: su aviso se queda un rato y se va solo.
  function medalla(texto) {
    const nodo = avisoDeMedalla(texto);
    medallas.append(nodo);
    luego(MEDALLA_DURA_MS, () => nodo.remove());
  }

  // --- acariciar y cuidar ---------------------------------------------------------------

  // Cada acción suma uno: una lectura del estado que se cruzó con una acción
  // ya no se pinta, porque lo que trae la acción es más nuevo.
  let acciones = 0;
  let acariciando = false;

  // La caricia no lleva evento que la haga repetible, así que no se reintenta
  // sola: si falla o se corta se dice, y se vuelve a pedir el estado, porque
  // pudo haber contado igual.
  async function acariciar() {
    if (acariciando) return;
    acariciando = true;
    acciones += 1;
    let fallida = false;
    try {
      const respuesta = await pedir('POST', 'acariciar');
      if (!vivo) return;
      const g = respuesta.estado && respuesta.estado.gachamon;
      trasAcariciar(respuesta, g, {
        corazones,
        saltar: () => gesto('salta'),
        titubear: () => gesto('titubea'),
        avisar,
      });
      aplicar(respuesta.estado);
    } catch (error) {
      fallida = true;
      if (vivo) fallo(error);
    } finally {
      acariciando = false;
    }
    if (fallida) releer();
  }

  async function cuidar(cuidado) {
    const { accion, nodo } = cuidado;
    if (nodo.classList.contains('esperando') || faltaPara(hasta, accion) > 0) return;
    acciones += 1;
    nodo.classList.add('esperando');
    nodo.setAttribute('aria-busy', 'true');
    contar();
    callarAviso();
    // Un toque, un evento: los reintentos de este toque llevan el mismo.
    const evento = nuevoEvento();
    // La etapa que se veía al tocar: si la que llega es otra, evolucionó,
    // aunque la respuesta sea la de un reintento, que no trae la marca.
    const etapaAntes = actual.gachamon.etapa;
    let fallido = false;
    try {
      // Si mientras se espera para repetirlo se dejó la pantalla, no se insiste.
      const respuesta = await conReintentos(
        () => pedir('POST', 'cuidar', { accion, evento_id: evento }),
        () => vivo,
      );
      if (!vivo) return;
      aplicar(respuesta.estado);
      if (!vivo) return;
      trasCuidar(respuesta, etapaAntes, {
        saltar: () => gesto('salta'),
        ganar,
        celebrar: () => celebrar(actual.gachamon),
        medalla,
        avisar,
      });
    } catch (error) {
      fallido = true;
      if (vivo) fallo(error);
    } finally {
      nodo.classList.remove('esperando');
      nodo.removeAttribute('aria-busy');
      if (vivo) contar();
    }
    // Agotados los reintentos, pudo haber llegado igual: manda el estado.
    if (fallido) releer();
  }

  gachamon.addEventListener('click', acariciar);

  // --- mantenerse al día ------------------------------------------------------------------

  let leyendo = false;

  async function releer() {
    if (!vivo || leyendo || document.hidden) return;
    leyendo = true;
    const antes = acciones;
    try {
      const nuevo = await pedir('GET', 'estado');
      const enCurso = acariciando || cuidados.some((c) => c.nodo.classList.contains('esperando'));
      if (vivo && antes === acciones && !enCurso) aplicar(nuevo);
    } catch (error) {
      if (vivo && error && error.estado === 401) irse();
      // Sin red o sin túnel: la próxima vuelta lo intenta otra vez.
    } finally {
      leyendo = false;
    }
  }

  document.addEventListener('visibilitychange', () => {
    if (!cuerpo.isConnected) {
      parar();
      return;
    }
    if (document.hidden) return;
    clearInterval(cadaTanto);
    cadaTanto = setInterval(releer, PEDIR_ESTADO_CADA_MS);
    releer();
  }, { signal: oyentes.signal });

  // Tu avatar, que en el computador se ve más grande, y el fondo de la escena,
  // que se vuelve a pintar a su medida: los de la escena de un lugar.
  const repintarMonigote = monigoteDeLaEscena(monigote, () => actual.avatar, oyentes.signal);
  elFondo = fondoDeLaEscena(fondo, { sigue: () => vivo, signal: oyentes.signal });

  aplicar(estado);
  repintarMonigote();
  cadaSegundo = setInterval(contar, 1000);
  cadaTanto = setInterval(releer, PEDIR_ESTADO_CADA_MS);
  // Sin gachamon no hay quién hable.
  if (!conGachamon) return;
  if (llegando) luego(PRIMER_GLOBO_AL_LLEGAR_MS, () => hablar(true));
  else luego(PRIMER_GLOBO_MS, hablar);
}
