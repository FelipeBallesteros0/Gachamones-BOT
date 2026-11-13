// La pantalla principal: estás en el hogar de tu gachamon, lo ves en grande,
// te habla en un globo, lo acaricias y lo cuidas.
//
// `lugar(contenedor, estado, seguir)` pinta la pantalla con el estado ya leído
// y la mantiene al día: vuelve a pedir el estado cada 30 segundos y al volver
// a la pestaña, baja sola las cuentas de espera de los cuidados y hace hablar
// al gachamon de vez en cuando. Si lo que llega pide otra pantalla (se murió,
// hay uno sin nombre, ya no es el mismo) se lo pasa a `seguir`. Todo lo que
// temporiza se detiene en cuanto la pantalla deja de estar en la página.
//
// Las reglas son del servidor: las barras se pintan con lo que dice el estado,
// sin simular el paso del tiempo, y lo único que corre aquí son las cuentas
// de espera. Todo texto entra por `el` o por `textContent`.

import { nuevoEvento, pedir } from './api.js';
import { lienzoDelAvatar } from './avatar.js';
import { el } from './dom.js';
import { siguiente } from './pantallas.js';
import {
  avisoDelCuidado, avisosDeMedallas, cuantasGemas, cuantasMonedas, elegirGlobo, formatoEspera,
  nombreDelHogar, seCelebraLaEvolucion,
} from './tiempo.js';

const PEDIR_ESTADO_CADA_MS = 30_000;
const PRIMER_GLOBO_MS = 2500;
const GLOBO_CADA_MS = [20_000, 40_000];
const GLOBO_DURA_MS = 7000;
const AVISO_DURA_MS = 5000;
const GANANCIA_DURA_MS = 2400;
const CELEBRACION_DURA_MS = 4500;
const MEDALLA_DURA_MS = 6000;
const CORAZONES = 6;
const CORAZON_DURA_MS = 1600;
// Lo que mide de alto el avatar en la escena, en píxeles de pantalla: en el
// computador se ve más grande.
const ALTO_DEL_AVATAR = 126;
const ALTO_DEL_AVATAR_EN_COMPUTADOR = 168;
// Un cuidado que no llegó se repite con el mismo evento: el servidor no lo
// aplica ni lo paga dos veces. Éstas son las pausas antes de cada reintento.
const REINTENTOS_MS = [800, 2000];
const ALGO_SALIO_MAL = 'Algo salió mal. Vuelve a intentarlo.';

const CUIDADOS = [
  { accion: 'alimentar', icono: '🍖', nombre: 'Alimentar' },
  { accion: 'jugar', icono: '🎮', nombre: 'Jugar' },
  { accion: 'entrenar', icono: '🏋️', nombre: 'Entrenar' },
  { accion: 'limpiar', icono: '🧼', nombre: 'Limpiar' },
];

const BARRAS = [
  { clave: 'comida', icono: '🍖', nombre: 'Comida' },
  { clave: 'animo', icono: '😊', nombre: 'Ánimo' },
  { clave: 'aseo', icono: '🧼', nombre: 'Aseo' },
];

// Por debajo de 40 el gachamon lo pide (`globos.UMBRAL_NECESIDAD`).
function nivelDeBarra(valor) {
  if (valor < 40) return 'bajo';
  if (valor < 65) return 'medio';
  return 'alto';
}

// Las palabras que pone la propia pantalla concuerdan con el gachamon:
// masculino salvo para una hembra.
function segun(genero, masculino, femenino) {
  return genero === 'hembra' ? femenino : masculino;
}

function mensajeDe(error) {
  return error && typeof error.mensaje === 'string' && error.mensaje ? error.mensaje : ALGO_SALIO_MAL;
}

function pausa(ms) {
  return new Promise((listo) => { setTimeout(listo, ms); });
}

// Mientras se está aquí hay sesión y la cuenta ya no es nueva, así que la
// pantalla la decide sólo el estado, con la misma regla de siempre.
function pideOtraPantalla(estado) {
  return siguiente(true, { estado: 'en juego' }, estado) !== 'lugar';
}

// Vuelve a lanzar una animación de CSS aunque ya estuviera puesta.
function animar(nodo, clase) {
  nodo.classList.remove(clase);
  void nodo.offsetWidth;
  nodo.classList.add(clase);
}

export function lugar(contenedor, estado, seguir) {
  const id = estado.gachamon.id;
  let actual = estado;
  let ultimoAhora = -Infinity;
  let vivo = true;

  // Lo que corre por su cuenta, para pararlo todo de una vez.
  const temporizadores = new Set();
  const oyentes = new AbortController();
  let cadaSegundo = null;
  let cadaTanto = null;

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
  const cabecera = el('header', { class: 'barra barra-lugar' },
    el('span', { class: 'donde' }, el('span', { 'aria-hidden': 'true' }, '📍'), donde),
    el('span', { class: 'saldos' },
      el('span', { class: 'saldo saldo-monedas' }, monedasVisibles, monedasLeidas, ganancia),
      el('span', { class: 'saldo' }, gemasVisibles, gemasLeidas)));

  // --- la escena ------------------------------------------------------------------

  const monigote = el('canvas', { class: 'monigote-lugar', 'aria-hidden': 'true' });
  const retrato = el('img', {
    class: 'retrato', src: estado.gachamon.retrato, alt: estado.gachamon.nombre, draggable: 'false',
  });
  const sinRetrato = el('span', { class: 'retrato-sin', 'aria-hidden': 'true', hidden: true }, estado.gachamon.emoji);
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
    el('span', { class: 'ventana', 'aria-hidden': 'true' }),
    monigote,
    gachamon,
    globo,
    celebracion,
    medallas);

  // --- la ficha -------------------------------------------------------------------

  const titulo = el('h1', { tabindex: '-1' });
  const insignia = el('p', { class: 'insignia', hidden: true });
  const detalle = el('p', { class: 'ficha-detalle' });
  const medidores = BARRAS.map(({ clave, icono, nombre }) => {
    const cifra = el('span', { class: 'medidor-cifra' });
    const relleno = el('span', { class: 'medidor-relleno' });
    const nodo = el('div', { class: 'medidor' },
      el('span', { class: 'medidor-nombre' }, el('span', { 'aria-hidden': 'true' }, icono), ` ${nombre}`),
      cifra,
      el('span', { class: 'medidor-pista', 'aria-hidden': 'true' }, relleno));
    return { clave, nodo, cifra, relleno };
  });
  const ficha = el('section', { class: 'ficha', 'aria-label': 'Ficha' },
    el('div', { class: 'ficha-cabeza' }, titulo, insignia),
    detalle,
    el('div', { class: 'medidores' }, medidores.map((m) => m.nodo)));

  // Bajo la ficha: lo que contesta el juego, o, si no hay nada que decir, la
  // pista de que se le puede acariciar.
  const aviso = el('p', { class: 'aviso-lugar', 'aria-live': 'polite' });
  const pista = el('p', { class: 'pista-lugar' });
  const avisos = el('div', { class: 'avisos-lugar' }, aviso, pista);

  // --- los cuidados ---------------------------------------------------------------

  const cuidados = CUIDADOS.map(({ accion, icono, nombre }) => {
    const espera = el('span', { class: 'cuidado-espera' });
    const nodo = el('button', { type: 'button', class: 'cuidado' },
      el('span', { class: 'cuidado-icono', 'aria-hidden': 'true' }, icono),
      el('span', { class: 'cuidado-nombre' }, nombre),
      espera);
    const cuidado = { accion, nombre, nodo, espera };
    nodo.addEventListener('click', () => cuidar(cuidado));
    return cuidado;
  });

  const cuerpo = el('div', { class: 'cuerpo cuerpo-lugar' },
    escena,
    ficha,
    avisos,
    el('div', { class: 'cuidados', role: 'group', 'aria-label': 'Cuidados' }, cuidados.map((c) => c.nodo)));
  contenedor.append(cabecera, cuerpo);

  // --- pintar lo que dice el estado -----------------------------------------------

  // Cuándo se acaba cada espera, en la hora de este teléfono.
  const hasta = {};

  function faltaPara(accion) {
    const fin = hasta[accion];
    return typeof fin === 'number' ? Math.max(0, Math.ceil((fin - Date.now()) / 1000)) : 0;
  }

  function aplicar(nuevo) {
    if (!vivo || !nuevo) return;
    const cuando = Date.parse(nuevo.ahora);
    // Llegó después que otro más nuevo (una lectura que se cruzó con una acción).
    if (cuando < ultimoAhora) return;
    if (pideOtraPantalla(nuevo) || nuevo.gachamon.id !== id) {
      irse(nuevo);
      return;
    }
    if (!Number.isNaN(cuando)) ultimoAhora = cuando;
    actual = nuevo;
    pintar();
  }

  function pintar() {
    const g = actual.gachamon;
    donde.textContent = nombreDelHogar(actual.hogar);
    escena.dataset.hogar = actual.hogar;
    escena.dataset.etapa = g.etapa;

    const { monedas, gemas } = actual.saldos;
    monedasVisibles.textContent = `🪙 ${monedas}`;
    monedasLeidas.textContent = cuantasMonedas(monedas);
    gemasVisibles.textContent = `💎 ${gemas}`;
    gemasLeidas.textContent = cuantasGemas(gemas);

    // Sólo si cambió: volver a poner la misma dirección haría parpadear.
    if (retrato.getAttribute('src') !== g.retrato) retrato.setAttribute('src', g.retrato);
    retrato.alt = g.nombre;
    sinRetrato.textContent = g.emoji;
    gachamon.setAttribute('aria-label', `Acariciar a ${g.nombre}`);
    gachamon.classList.toggle('decaido', Boolean(g.desfallecido));

    titulo.textContent = g.nombre;
    insignia.textContent = segun(g.genero, 'Desfallecido', 'Desfallecida');
    insignia.hidden = !g.desfallecido;
    detalle.textContent = `${g.nombre_especie} ${g.nombre_etapa} · nivel ${g.nivel}`;
    for (const m of medidores) {
      const valor = Number(g.barras[m.clave]) || 0;
      m.cifra.textContent = String(valor);
      m.relleno.style.width = `${valor}%`;
      m.relleno.dataset.nivel = nivelDeBarra(valor);
    }

    const ahora = Date.now();
    for (const [accion, segundos] of Object.entries(g.esperas || {})) {
      hasta[accion] = ahora + Math.max(0, Number(segundos) || 0) * 1000;
    }

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
    for (const c of cuidados) {
      const falta = faltaPara(c.accion);
      const texto = formatoEspera(falta);
      if (c.espera.textContent !== texto) c.espera.textContent = texto;
      const ocupado = c.nodo.classList.contains('esperando');
      c.nodo.setAttribute('aria-disabled', String(ocupado || falta > 0));
      if (falta > 0) c.nodo.setAttribute('aria-label', `${c.nombre}, disponible en ${texto}`);
      else c.nodo.removeAttribute('aria-label');
    }
    const g = actual.gachamon;
    const sePuede = faltaPara('acariciar') === 0;
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

  function hablar() {
    luego(GLOBO_CADA_MS[0] + Math.random() * (GLOBO_CADA_MS[1] - GLOBO_CADA_MS[0]), hablar);
    if (document.hidden || celebracion.hasChildNodes()) return;
    const elegido = elegirGlobo(actual.globos, anterior, Math.random);
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
      const corazon = el('span', {
        class: 'corazon',
        'aria-hidden': 'true',
        style: `left: ${48 + Math.random() * 30}%; font-size: ${16 + Math.random() * 12}px; animation-delay: ${i * 90}ms`,
      }, '❤');
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
    celebracion.replaceChildren(el('p', { class: 'celebracion-texto' },
      `✨ ¡${g.nombre} ha evolucionado! Ahora es ${g.nombre_etapa}.`));
    celebracionHasta = luego(CELEBRACION_DURA_MS, () => celebracion.replaceChildren());
  }

  // Una medalla nueva: su aviso se queda un rato y se va solo.
  function medalla(texto) {
    const nodo = el('p', { class: 'medalla' }, texto);
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
      if (respuesta.ok) {
        corazones();
        gesto('salta');
      } else if (respuesta.espera > 0 && g) {
        // Antes de tiempo no hay corazones ni error: apenas se mueve.
        gesto('titubea');
        avisar(`Podrás acariciar${segun(g.genero, 'lo', 'la')} en ${formatoEspera(respuesta.espera)}.`);
      }
      aplicar(respuesta.estado);
    } catch (error) {
      fallida = true;
      if (vivo) fallo(error);
    } finally {
      acariciando = false;
    }
    if (fallida) releer();
  }

  async function conReintentos(hacer) {
    for (let intento = 0; ; intento += 1) {
      try {
        return await hacer();
      } catch (error) {
        // Sólo se repite lo que no llegó a ser una respuesta del juego.
        const noLlego = error && error.clave === null && error.estado !== 401;
        if (!noLlego || intento >= REINTENTOS_MS.length) throw error;
        await pausa(REINTENTOS_MS[intento]);
        // Si mientras tanto se dejó la pantalla, no se insiste.
        if (!vivo) throw error;
      }
    }
  }

  async function cuidar(cuidado) {
    const { accion, nodo } = cuidado;
    if (nodo.classList.contains('esperando') || faltaPara(accion) > 0) return;
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
      const respuesta = await conReintentos(() => pedir('POST', 'cuidar', { accion, evento_id: evento }));
      if (!vivo) return;
      aplicar(respuesta.estado);
      if (!vivo) return;
      if (respuesta.ok) {
        gesto('salta');
        if (respuesta.monedas > 0) ganar(respuesta.monedas);
      }
      if (seCelebraLaEvolucion(respuesta, etapaAntes)) celebrar(actual.gachamon);
      for (const texto of avisosDeMedallas(respuesta)) medalla(texto);
      // La frase del juego se lee siempre: «Se ha empachado» también cuenta.
      const frase = avisoDelCuidado(respuesta);
      if (frase) avisar(frase);
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

  // En el computador el monigote se ve más grande.
  const ancho = window.matchMedia('(min-width: 900px)');
  const repintarMonigote = () => lienzoDelAvatar(
    monigote, actual.avatar, ancho.matches ? ALTO_DEL_AVATAR_EN_COMPUTADOR : ALTO_DEL_AVATAR,
  );
  ancho.addEventListener('change', repintarMonigote, { signal: oyentes.signal });

  aplicar(estado);
  repintarMonigote();
  cadaSegundo = setInterval(contar, 1000);
  cadaTanto = setInterval(releer, PEDIR_ESTADO_CADA_MS);
  luego(PRIMER_GLOBO_MS, hablar);
}
