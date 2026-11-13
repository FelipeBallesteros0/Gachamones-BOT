// El pueblo: un mapa en un <canvas> por el que tu avatar camina, con tu
// gachamon detrás, hasta el lugar que toques, y entra.
//
// `pueblo(contenedor, estado, seguir)` pinta la pantalla y la mantiene viva
// hasta que se sale. No decide nada del pueblo: lee `datos/pueblo.json`, le
// pasa los toques a `pueblo.js` y dibuja lo que éste le diga. Al llegar le
// dice al servidor dónde está (`POST lugar`) y pasa a la pantalla de ese lugar
// con el estado que vuelve.
//
// El lienzo sólo se mira: debajo hay un botón por lugar que hace lo mismo que
// tocarlo, para el teclado y el lector de pantalla. Todo texto entra por `el`,
// por `textContent` o, en el lienzo, por `fillText`. Lo que corre (el cuadro
// de animación y los oyentes) se detiene al salir, y una respuesta que llega
// tarde no pinta ni llama a `seguir`.

import { pedir } from './api.js';
import { cargar, olvidarLasQueFaltan, pintarPieza } from './arte.js';
import { cargarAvatar, dibujarAvatar, poseAlCaminar } from './avatar.js';
import { el } from './dom.js';
import { trasFallarLaLlegada } from './pantallas.js';
import {
  acercarCamara, armarGrafo, arrastrarCamara, avanzar, camaraHacia, crearPaseo, encuadre, flechas, ir,
  llegarYa, lugarEn, salto,
} from './pueblo.js';
import { cuantasGemas, cuantasMonedas } from './tiempo.js';

// Lo que mide cada cosa, en unidades del pueblo (las de `pueblo.json`).
const LADO_DEL_LUGAR = 80;
const ALTO_DEL_AVATAR = 42;
const ALTO_DEL_GACHAMON = 30;
const LADO_DE_LA_SOMBRA = 24;
const LADO_DE_LA_MARCA = 16;
const VAIVEN_DE_LA_MARCA = 3;
const SEGUNDOS_DEL_VAIVEN = 1.1;
// El nombre de un lugar va en una pastilla que empieza esto bajo su nodo.
const ETIQUETA_BAJO_EL_NODO = 6;
// Su letra, en píxeles de pantalla: crece con el mapa, sin pasarse.
const LETRA_POR_UNIDAD = 9;
const LETRA_MINIMA = 11;
const LETRA_MAXIMA = 15;
const LETRA = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
const LETRA_DE_EMOJI = '"Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif';
// Un toque que se mueve más que esto hacia algún lado ya es un arrastre.
const ARRASTRE_PX = 8;
// La cámara se da por llegada a menos de esto de donde va.
const CAMARA_QUIETA = 0.05;
const DENSIDAD_MAXIMA = 3;
const ESPERA_MAXIMA_MS = 15_000;

const FONDO = 'pueblo/fondo.png';
const MARCA = 'efectos/marca.png';
const SOMBRA = 'efectos/sombra.png';
const dibujoDelLugar = (clave) => `pueblo/lugares/${clave}.png`;

const CARGANDO = 'Cargando el pueblo…';
const NO_SE_PUDO_CARGAR = 'No se pudo cargar el pueblo. Revisa tu conexión.';
const ENTRANDO = 'Entrando…';
const NO_SE_PUDO_ENTRAR = 'No se pudo entrar. Revisa tu conexión.';

// --- lo que se pide una vez ------------------------------------------------------

// Los datos del pueblo se piden una vez por página; si fallan, la próxima vez
// se piden de nuevo. La dirección sale de la de este módulo: así lleva la
// versión de los estáticos, igual que el arte. Si el servidor contesta con un
// error, lo que se lanza lleva su `estado`.
let pedidoDelPueblo = null;

function leerElPueblo() {
  if (!pedidoDelPueblo) {
    pedidoDelPueblo = pedirElPueblo();
    pedidoDelPueblo.catch(() => { pedidoDelPueblo = null; });
  }
  return pedidoDelPueblo;
}

async function pedirElPueblo() {
  const corte = new AbortController();
  const reloj = setTimeout(() => corte.abort(), ESPERA_MAXIMA_MS);
  try {
    const respuesta = await fetch(new URL('../datos/pueblo.json', import.meta.url), {
      credentials: 'same-origin', signal: corte.signal,
    });
    if (!respuesta.ok) {
      throw Object.assign(new Error(`pueblo.json: ${respuesta.status}`), { estado: respuesta.status });
    }
    return await respuesta.json();
  } finally {
    clearTimeout(reloj);
  }
}

// El servidor contestó que ese archivo no está: no es la conexión, es que esta
// página es de una versión anterior.
function contestoQueNo(error) {
  const estado = error ? error.estado : undefined;
  return typeof estado === 'number' && estado >= 400 && estado < 500;
}

// El retrato del gachamon no es una pieza del contrato: es la dirección que
// trae el estado. Nunca rechaza; `null` si no cargó.
function cargarRetrato(direccion) {
  return new Promise((listo) => {
    const imagen = new Image();
    imagen.onload = () => listo(imagen);
    imagen.onerror = () => listo(null);
    imagen.src = direccion;
  });
}

// --- el lienzo ---------------------------------------------------------------------

function limitar(valor, minimo, maximo) {
  return Math.max(minimo, Math.min(maximo, valor));
}

// Un rectángulo con los extremos redondos, con lo que tiene cualquier navegador.
function trazarPastilla(ctx, x, y, ancho, alto) {
  const radio = alto / 2;
  ctx.beginPath();
  ctx.moveTo(x + radio, y);
  ctx.arcTo(x + ancho, y, x + ancho, y + alto, radio);
  ctx.arcTo(x + ancho, y + alto, x, y + alto, radio);
  ctx.arcTo(x, y + alto, x, y, radio);
  ctx.arcTo(x, y, x + ancho, y, radio);
  ctx.closePath();
}

export function pueblo(contenedor, estado, seguir) {
  // El arte que no cargó en otra pantalla se pide de nuevo.
  olvidarLasQueFaltan();
  const aqui = estado.lugar || { clave: null };
  const menosMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)');
  const quieto = () => menosMovimiento.matches;

  let vivo = true;
  const oyentes = new AbortController();
  const { signal } = oyentes;
  let observador = null;
  let cuadroPedido = null;

  function parar() {
    vivo = false;
    if (cuadroPedido !== null) cancelAnimationFrame(cuadroPedido);
    cuadroPedido = null;
    oyentes.abort();
    if (observador) observador.disconnect();
  }

  // Deja el mapa y que se decida otra pantalla.
  function irse(estadoNuevo, opciones) {
    parar();
    seguir(estadoNuevo, opciones);
  }

  // --- la cabecera: estás en el pueblo, con lo que tienes ----------------------------

  const { monedas, gemas } = estado.saldos;
  const titulo = el('h1', { class: 'donde', tabindex: '-1' }, el('span', { 'aria-hidden': 'true' }, '🗺️'), 'Pueblo');
  const cabecera = el('header', { class: 'barra barra-lugar' },
    titulo,
    el('span', { class: 'saldos' },
      el('span', { class: 'saldo' },
        el('span', { 'aria-hidden': 'true' }, `🪙 ${monedas}`),
        el('span', { class: 'solo-lector' }, cuantasMonedas(monedas))),
      el('span', { class: 'saldo' },
        el('span', { 'aria-hidden': 'true' }, `💎 ${gemas}`),
        el('span', { class: 'solo-lector' }, cuantasGemas(gemas)))));

  // --- el mapa ---------------------------------------------------------------------

  const lienzo = el('canvas', { class: 'mapa-lienzo', 'aria-hidden': 'true' });
  // Las flechas sólo mueven lo que se ve del lienzo: para el teclado y el
  // lector de pantalla está la lista de lugares.
  const flecha = (lado, simbolo) => el('button', {
    type: 'button', class: `mapa-flecha mapa-flecha-${lado}`, tabindex: '-1', 'aria-hidden': 'true', hidden: true,
  }, simbolo);
  const flechaIzquierda = flecha('izquierda', '‹');
  const flechaDerecha = flecha('derecha', '›');
  const aviso = el('p', { class: 'mapa-aviso', role: 'status' });
  const espera = el('div', { class: 'mapa-espera' });
  const mapa = el('div', { class: 'mapa' }, lienzo, flechaIzquierda, flechaDerecha, aviso, espera);

  // --- debajo: volver sin moverse, o ir a un lugar ------------------------------------

  // Dice adónde («Volver al refugio») cuando llegan los datos del pueblo; hasta
  // entonces, o si no llegan, «Volver» a secas.
  const volver = el('button', { type: 'button', class: 'boton boton-volver' }, 'Volver');
  const lista = el('ul', { class: 'lugares-del-pueblo' });
  // Sin los datos del pueblo no hay lugares que listar.
  const irA = el('section', { class: 'ir-a', hidden: true },
    el('h2', { class: 'ir-a-titulo' }, '¿Adónde vamos?'),
    lista);
  const rumbo = el('p', { class: 'solo-lector', role: 'status' });
  const cuerpo = el('div', { class: 'cuerpo cuerpo-pueblo' }, volver, irA, rumbo);
  contenedor.append(cabecera, mapa, cuerpo);

  // --- el estado del mapa --------------------------------------------------------------

  let datos = null;
  let paseo = null;
  let porAltura = [];
  let piezas = null;
  let listo = false;
  let entrando = false;
  // Cuánto pueblo se ve y a qué escala (lo de `encuadre`, más `altoVista`);
  // `densidad`, los píxeles del lienzo por píxel de pantalla, y `unidad`, los
  // que mide una unidad del pueblo.
  const vista = {
    escala: 1, completo: true, anchoVista: 1, altoVista: 1, densidad: 1, unidad: 1,
  };
  // La cámara (la x del pueblo en el borde izquierdo) va hacia `objetivo`;
  // mientras `siguiendo`, el objetivo es el avatar.
  let camara = 0;
  let objetivo = 0;
  let siguiendo = true;
  let antes = null;

  function avisar(texto, esError = false) {
    aviso.textContent = texto;
    aviso.classList.toggle('es-error', esError);
  }

  // Si la pantalla ya no está en la página (se pintó otra), se para todo.
  function sigueAqui() {
    if (vivo && !mapa.isConnected) parar();
    return vivo;
  }

  // El pueblo se mueve si es más ancho que lo que se ve; en el computador se
  // ve entero y no hay cámara.
  function sePuedeMover() {
    return !vista.completo && vista.anchoVista < datos.ancho;
  }

  function camaraEnElAvatar() {
    return camaraHacia(paseo.x, vista.anchoVista, datos);
  }

  // El punto del pueblo que queda en la esquina de arriba a la izquierda del
  // lienzo: la cámara o, si sobra lienzo, lo que deja el pueblo al centro.
  function origen() {
    const x = vista.anchoVista >= datos.ancho ? (datos.ancho - vista.anchoVista) / 2 : camara;
    const y = vista.altoVista > datos.alto ? (datos.alto - vista.altoVista) / 2 : 0;
    return [x, y];
  }

  // Mide el lienzo, le da los píxeles de la pantalla y vuelve a encuadrar. La
  // caminata no se toca; la cámara vuelve al avatar o se queda donde estaba.
  function medir() {
    const ancho = lienzo.clientWidth;
    const alto = lienzo.clientHeight;
    if (!ancho || !alto) return false;
    const densidad = limitar(window.devicePixelRatio || 1, 1, DENSIDAD_MAXIMA);
    const anchoReal = Math.round(ancho * densidad);
    const altoReal = Math.round(alto * densidad);
    // Cambiar el tamaño borra el lienzo: sólo si de verdad cambia.
    if (lienzo.width !== anchoReal) lienzo.width = anchoReal;
    if (lienzo.height !== altoReal) lienzo.height = altoReal;
    Object.assign(vista, encuadre(ancho, alto, datos));
    vista.altoVista = alto / vista.escala;
    vista.densidad = anchoReal / ancho;
    vista.unidad = vista.escala * vista.densidad;
    objetivo = siguiendo
      ? camaraEnElAvatar()
      : arrastrarCamara(objetivo, 0, vista.escala, vista.anchoVista, datos);
    camara = objetivo;
    return true;
  }

  // --- dibujar ---------------------------------------------------------------------

  // Dónde cae en el lienzo un punto del pueblo, con la cámara de ahora.
  function aLienzo() {
    const u = vista.unidad;
    const [x0, y0] = origen();
    const izquierda = Math.round(-x0 * u);
    const arriba = Math.round(-y0 * u);
    return [(x) => izquierda + x * u, (y) => arriba + y * u];
  }

  // La pastilla con el nombre de un lugar, en píxeles del lienzo: la misma
  // cuenta sirve para dibujarla y para saber si se tocó. Deja puesta su letra.
  function pastilla(ctx, [enX, enY], clave) {
    const [nx, ny] = datos.nodos[clave];
    const d = vista.densidad;
    const tam = Math.round(limitar(LETRA_POR_UNIDAD * vista.escala, LETRA_MINIMA, LETRA_MAXIMA) * d);
    const texto = datos.lugares[clave].nombre;
    ctx.font = `700 ${tam}px ${LETRA}`;
    const alto = Math.round(tam * 1.6);
    const ancho = Math.round(ctx.measureText(texto).width + tam * 1.2);
    return {
      texto, ancho, alto, x: Math.round(enX(nx) - ancho / 2), y: Math.round(enY(ny + ETIQUETA_BAJO_EL_NODO)),
    };
  }

  function dibujar() {
    const ctx = lienzo.getContext('2d');
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, lienzo.width, lienzo.height);

    const u = vista.unidad;
    const enLienzo = aLienzo();
    const [enX, enY] = enLienzo;
    // Una caja del pueblo, con los bordes en píxeles enteros del lienzo.
    const caja = (x, y, ancho, alto) => {
      const a = Math.round(enX(x));
      const b = Math.round(enY(y));
      return [a, b, Math.round(enX(x + ancho)) - a, Math.round(enY(y + alto)) - b];
    };

    pintarPieza(ctx, piezas.fondo, ...caja(0, 0, datos.ancho, datos.alto));
    // Cada lugar se apoya en su nodo: el centro de su borde de abajo.
    for (const clave of porAltura) {
      const [nx, ny] = datos.nodos[clave];
      pintarPieza(ctx, piezas.lugares.get(clave),
        ...caja(nx - LADO_DEL_LUGAR / 2, ny - LADO_DEL_LUGAR, LADO_DEL_LUGAR, LADO_DEL_LUGAR));
    }
    for (const clave of porAltura) etiqueta(ctx, pastilla(ctx, enLienzo, clave));

    if (paseo.caminando && paseo.destino !== null) {
      const [nx, ny] = datos.nodos[paseo.destino];
      const vaiven = quieto()
        ? 0
        : (VAIVEN_DE_LA_MARCA * (1 - Math.cos((2 * Math.PI * paseo.t) / SEGUNDOS_DEL_VAIVEN))) / 2;
      pintarPieza(ctx, piezas.marca, ...caja(
        nx - LADO_DE_LA_MARCA / 2, ny - LADO_DEL_LUGAR - LADO_DE_LA_MARCA - vaiven,
        LADO_DE_LA_MARCA, LADO_DE_LA_MARCA,
      ));
    }

    // El de más abajo tapa al otro; si están a la par, el avatar va delante.
    // El gachamon pisa su sombra, que se queda en el suelo cuando él salta (la
    // del avatar ya viene en su dibujo).
    const figuras = [
      [paseo.gy, () => {
        pintarPieza(ctx, piezas.sombra, ...caja(
          paseo.gx - LADO_DE_LA_SOMBRA / 2, paseo.gy - LADO_DE_LA_SOMBRA / 2,
          LADO_DE_LA_SOMBRA, LADO_DE_LA_SOMBRA,
        ));
        dibujarGachamon(ctx, enX(paseo.gx), enY(paseo.gy), u);
      }],
      [paseo.y, () => dibujarAvatar(ctx, piezas.capas, estado.avatar, poseAlCaminar(paseo.t, paseo.caminando),
        enX(paseo.x), enY(paseo.y), ALTO_DEL_AVATAR * u, paseo.mira < 0)],
    ];
    figuras.sort((a, b) => a[0] - b[0]);
    for (const [, figura] of figuras) figura();
  }

  // El nombre de un lugar en su pastilla clara (la letra ya la puso `pastilla`).
  function etiqueta(ctx, { texto, x, y, ancho, alto }) {
    const d = vista.densidad;
    trazarPastilla(ctx, x, y, ancho, alto);
    ctx.fillStyle = 'rgba(255, 255, 255, 0.92)';
    ctx.fill();
    ctx.lineWidth = d;
    ctx.strokeStyle = 'rgba(29, 29, 31, 0.25)';
    ctx.stroke();
    ctx.fillStyle = '#1d1d1f';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(texto, x + ancho / 2, y + alto / 2 + d / 2);
  }

  // El retrato de siempre, con los pies en (x, y), levantado lo que diga
  // `salto`. Los retratos miran a la izquierda: se da vuelta cuando va a la
  // derecha. Sin retrato, su emoji.
  function dibujarGachamon(ctx, x, y, u) {
    const alto = Math.round(ALTO_DEL_GACHAMON * u);
    const sube = quieto() ? 0 : salto(paseo.t, paseo.gcaminando) * u;
    const retrato = piezas.retrato;
    if (!retrato) {
      ctx.font = `${alto}px ${LETRA_DE_EMOJI}`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillStyle = '#1d1d1f';
      ctx.fillText(estado.gachamon.emoji || '', x, y - sube);
      return;
    }
    const ancho = Math.round((alto * retrato.naturalWidth) / retrato.naturalHeight);
    const izquierda = Math.round(x - ancho / 2);
    const arriba = Math.round(y - alto - sube);
    ctx.save();
    if (paseo.gmira > 0) {
      ctx.translate(izquierda * 2 + ancho, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(retrato, izquierda, arriba, ancho, alto);
    ctx.restore();
  }

  function ponerFlechas() {
    const hay = sePuedeMover()
      ? flechas(camara, vista.anchoVista, datos)
      : { izquierda: false, derecha: false };
    if (flechaIzquierda.hidden === hay.izquierda) flechaIzquierda.hidden = !hay.izquierda;
    if (flechaDerecha.hidden === hay.derecha) flechaDerecha.hidden = !hay.derecha;
  }

  // --- el cuadro de animación ---------------------------------------------------------

  // Sólo se anima mientras algo se mueve; parado, el lienzo se queda como está.
  function pedirCuadro() {
    if (vivo && listo && cuadroPedido === null) cuadroPedido = requestAnimationFrame(cuadro);
  }

  function cuadro(ahora) {
    cuadroPedido = null;
    if (!sigueAqui()) return;
    // Una pestaña que estuvo dormida recibe todo el tiempo de una vez:
    // `avanzar` llega sin pasarse.
    const dt = antes === null ? 0 : (ahora - antes) / 1000;
    antes = ahora;
    if (avanzar(paseo, dt)) llegar(paseo.en);
    if (siguiendo && sePuedeMover()) objetivo = camaraEnElAvatar();
    camara = quieto() ? objetivo : acercarCamara(camara, objetivo, dt);
    if (Math.abs(objetivo - camara) < CAMARA_QUIETA) camara = objetivo;
    dibujar();
    ponerFlechas();
    if (paseo.caminando || paseo.gcaminando || camara !== objetivo) pedirCuadro();
    else antes = null;
  }

  // --- tocar un lugar y llegar ---------------------------------------------------------

  function tocarLugar(clave) {
    if (!vivo || !paseo || entrando) return;
    // El mismo destino otra vez: ya.
    if (paseo.caminando && clave === paseo.destino) {
      llegarYa(paseo);
      pedirCuadro();
      llegar(paseo.en);
      return;
    }
    const resultado = ir(paseo, clave);
    if (resultado === 'nada') return;
    avisar('');
    siguiendo = true;
    if (resultado === 'llego') {
      llegar(clave);
      return;
    }
    if (quieto()) {
      llegarYa(paseo);
      pedirCuadro();
      llegar(paseo.en);
      return;
    }
    rumbo.textContent = `Caminando. Destino: ${datos.lugares[clave].nombre}.`;
    pedirCuadro();
  }

  // Mientras se espera al servidor, al entrar a un lugar o al volver, se ve
  // la misma espera y no se puede tocar nada: ni caminar ni volver.
  function esperarAlServidor() {
    entrando = true;
    volver.setAttribute('aria-disabled', 'true');
    rumbo.textContent = '';
    avisar(ENTRANDO);
  }

  // Le dice al servidor dónde llegaste y entra con el estado que vuelve.
  async function llegar(clave) {
    if (entrando) return;
    esperarAlServidor();
    try {
      const nuevo = await pedir('POST', 'lugar', { lugar: clave });
      if (!sigueAqui()) return;
      irse(nuevo, { llegando: true });
    } catch (error) {
      if (!sigueAqui()) return;
      // Volver a decidir: la pantalla se va y no se reactiva.
      if (trasFallarLaLlegada(error) === 'decidir') {
        irse();
        return;
      }
      // Se queda en el mapa: se puede tocar el lugar otra vez o volver.
      entrando = false;
      volver.removeAttribute('aria-disabled');
      avisar(NO_SE_PUDO_ENTRAR, true);
    }
  }

  // Volver al lugar donde estás es volver a decidir con lo que diga el
  // servidor ahora: las esperas, las barras y los saldos llegan al día.
  volver.addEventListener('click', () => {
    if (!vivo || entrando) return;
    esperarAlServidor();
    irse();
  }, { signal });

  // --- mover la cámara a mano ---------------------------------------------------------

  // Medio ancho de lo que se ve hacia ese lado (`-1`, izquierda; `1`, derecha).
  function mirarHacia(lado) {
    if (!listo || !sePuedeMover()) return;
    siguiendo = false;
    objetivo = arrastrarCamara(objetivo, -lado * (vista.anchoVista / 2) * vista.escala,
      vista.escala, vista.anchoVista, datos);
    pedirCuadro();
  }

  flechaIzquierda.addEventListener('click', () => mirarHacia(-1), { signal });
  flechaDerecha.addEventListener('click', () => mirarHacia(1), { signal });

  // El lugar bajo el puntero: el de la pastilla con su nombre, que se toca
  // entera (la de encima si se pisan), o el que diga `lugarEn` por su dibujo.
  function lugarTocado(evento) {
    const rect = lienzo.getBoundingClientRect();
    const px = (evento.clientX - rect.left) * vista.densidad;
    const py = (evento.clientY - rect.top) * vista.densidad;
    const ctx = lienzo.getContext('2d');
    const enLienzo = aLienzo();
    for (let i = porAltura.length - 1; i >= 0; i -= 1) {
      const { x, y, ancho, alto } = pastilla(ctx, enLienzo, porAltura[i]);
      if (px >= x && px <= x + ancho && py >= y && py <= y + alto) return porAltura[i];
    }
    const [x0, y0] = origen();
    return lugarEn(datos, x0 + (evento.clientX - rect.left) / vista.escala,
      y0 + (evento.clientY - rect.top) / vista.escala);
  }

  // Un toque que no se arrastra es tocar lo que haya debajo; arrastrar mueve
  // la cámara y deja de seguir al avatar hasta el próximo lugar que se toque.
  let toque = null;

  lienzo.addEventListener('pointerdown', (evento) => {
    if (!listo || !evento.isPrimary || (evento.pointerType === 'mouse' && evento.button !== 0)) return;
    toque = { id: evento.pointerId, x: evento.clientX, y: evento.clientY, camara, arrastra: false };
    try {
      lienzo.setPointerCapture(evento.pointerId);
    } catch {
      // Sin captura también se puede tocar.
    }
  }, { signal });

  lienzo.addEventListener('pointermove', (evento) => {
    if (!listo) return;
    if (!toque || evento.pointerId !== toque.id) {
      // Con el ratón, la mano dice qué se puede tocar.
      if (evento.pointerType === 'mouse') {
        lienzo.classList.toggle('sobre-un-lugar', Boolean(lugarTocado(evento)));
      }
      return;
    }
    const dx = evento.clientX - toque.x;
    if (Math.abs(dx) > ARRASTRE_PX || Math.abs(evento.clientY - toque.y) > ARRASTRE_PX) toque.arrastra = true;
    if (toque.arrastra && sePuedeMover()) {
      siguiendo = false;
      objetivo = arrastrarCamara(toque.camara, dx, vista.escala, vista.anchoVista, datos);
      camara = objetivo;
      pedirCuadro();
    }
  }, { signal });

  lienzo.addEventListener('pointerup', (evento) => {
    if (!toque || evento.pointerId !== toque.id) return;
    const { arrastra } = toque;
    toque = null;
    if (arrastra) return;
    const clave = lugarTocado(evento);
    if (clave) tocarLugar(clave);
  }, { signal });

  lienzo.addEventListener('pointercancel', () => { toque = null; }, { signal });

  // --- preparar --------------------------------------------------------------------

  function armarElPueblo(leidos) {
    datos = leidos;
    const claves = Object.keys(datos.lugares);
    const estasEnUnLugar = Object.hasOwn(datos.lugares, aqui.clave);
    const inicio = estasEnUnLugar ? aqui.clave : claves[0];
    paseo = crearPaseo(datos, armarGrafo(datos), inicio);
    const hacia = estasEnUnLugar ? datos.lugares[aqui.clave].hacia : null;
    if (typeof hacia === 'string' && hacia.trim()) volver.textContent = `Volver ${hacia}`;
    porAltura = [...claves].sort((a, b) => datos.nodos[a][1] - datos.nodos[b][1]);
    // Para que en el computador el mapa tenga la forma del pueblo, y lo de
    // debajo, su mismo ancho.
    for (const nodo of [mapa, cuerpo]) {
      nodo.style.setProperty('--ancho-del-pueblo', String(datos.ancho));
      nodo.style.setProperty('--alto-del-pueblo', String(datos.alto));
    }
    lista.replaceChildren(...claves.map((clave) => {
      const estasAqui = clave === aqui.clave;
      const boton = el('button', {
        type: 'button', class: 'lugar-del-pueblo', 'aria-current': estasAqui ? 'location' : null,
      }, estasAqui ? el('span', { 'aria-hidden': 'true' }, '📍') : null, datos.lugares[clave].nombre);
      boton.addEventListener('click', () => tocarLugar(clave), { signal });
      return el('li', {}, boton);
    }));
    irA.hidden = false;
  }

  // Dice que el pueblo no cargó, y devuelve el botón de reintentar.
  function mostrarFallo() {
    const reintentar = el('button', { type: 'button', class: 'boton boton-chico' }, 'Volver a intentarlo');
    reintentar.addEventListener('click', () => {
      // El botón se borra al reintentar: el foco espera en el título.
      titulo.focus({ preventScroll: true });
      preparar(true);
    }, { signal });
    espera.replaceChildren(el('p', { class: 'mapa-espera-texto es-error', role: 'alert' }, NO_SE_PUDO_CARGAR), reintentar);
    return reintentar;
  }

  // Tras reintentar, el foco pasa del título a lo que haya ahora, salvo que
  // quien juega ya lo haya llevado a otra parte.
  function enfocarTrasReintentar(nodo) {
    const activo = document.activeElement;
    if (nodo && (!activo || activo === titulo || activo === document.body)) nodo.focus({ preventScroll: true });
  }

  async function preparar(trasReintentar = false) {
    espera.replaceChildren(el('p', { class: 'mapa-espera-texto', role: 'status' }, CARGANDO));
    let leidos;
    try {
      leidos = await leerElPueblo();
    } catch (error) {
      if (!sigueAqui()) return;
      // Se decide de nuevo, y ahí `seguir` ve la versión nueva y recarga.
      if (contestoQueNo(error)) {
        irse();
        return;
      }
      const reintentar = mostrarFallo();
      if (trasReintentar) enfocarTrasReintentar(reintentar);
      return;
    }
    if (!sigueAqui()) return;
    if (!datos) armarElPueblo(leidos);
    if (trasReintentar) {
      enfocarTrasReintentar(lista.querySelector('[aria-current]') || lista.querySelector('button'));
    }
    // El arte nunca falla: lo que no carga se dibuja como su recuadro.
    const claves = Object.keys(datos.lugares);
    const [fondo, marca, sombra, lugares, capas, retrato] = await Promise.all([
      cargar(FONDO),
      cargar(MARCA),
      cargar(SOMBRA),
      Promise.all(claves.map((clave) => cargar(dibujoDelLugar(clave)))),
      cargarAvatar(estado.avatar),
      cargarRetrato(estado.gachamon.retrato),
    ]);
    if (!sigueAqui()) return;
    piezas = {
      fondo, marca, sombra, capas, retrato, lugares: new Map(claves.map((clave, i) => [clave, lugares[i]])),
    };
    espera.replaceChildren();
    espera.hidden = true;
    listo = true;

    // Girar el teléfono o cambiar el tamaño de la ventana reencuadra sin
    // perder la caminata.
    const reencuadrar = () => {
      if (sigueAqui() && medir()) {
        dibujar();
        ponerFlechas();
      }
    };
    if (typeof ResizeObserver === 'function') {
      observador = new ResizeObserver(reencuadrar);
      observador.observe(lienzo);
    } else {
      window.addEventListener('resize', reencuadrar, { signal });
    }
    reencuadrar();
    // Si se tocó un lugar de la lista mientras cargaba el arte, ya camina.
    pedirCuadro();
  }

  return preparar();
}
