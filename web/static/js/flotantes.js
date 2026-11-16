// Lo que flota sobre la pieza de tu departamento: el globo de lo que dice el
// que sale contigo, los corazones de una caricia, la ganancia de monedas bajo
// el saldo, el aviso de que evolucionó y los de las medallas nuevas. Se ven y
// duran como en el lugar (que tiene su propia copia de este pegamento).
//
// `loQueFlota({escenario, luego, cancelar, azar, puedeHablar, dondeHabla,
// globos})` arma sus nodos (`ganancia`, `globo`, `celebracion` y `medallas`),
// que la pantalla pone en su sitio; los corazones los suelta en `escenario`.
// No sabe de la pieza ni de quién está dónde: la pantalla le dice si el que
// sale contigo puede hablar ahora (`puedeHablar()`), dónde está su cabeza
// (`dondeHabla()`: `{caja, sube, lado}`, o `null` si no está en la pieza) y
// qué puede decir (`globos()`). Lo que se hace al rato va por los relojes de
// la pantalla (`luego`, `cancelar`), que lo paran todo al salir. Todo texto
// entra por `el` o por `textContent`.

import { MONEDAS } from './articulos.js';
import { lienzoDePieza } from './arte.js';
import { avisoDeLaEvolucion, avisoDeMedalla } from './cuidados.js';
import { el } from './dom.js';
import { elegirGlobo } from './tiempo.js';

// El globo, los corazones, la ganancia, la evolución y las medallas duran lo
// que en el lugar.
const PRIMER_GLOBO_MS = 2500;
const GLOBO_CADA_MS = [20_000, 40_000];
const GLOBO_DURA_MS = 7000;
const CORAZONES = 6;
const CORAZON_DURA_MS = 1600;
const GANANCIA_DURA_MS = 2400;
const CELEBRACION_DURA_MS = 4500;
const MEDALLA_DURA_MS = 6000;
// Lo que el globo deja hasta la cabeza del que habla.
const SOBRE_LA_CABEZA = 12;
// Lo que el globo deja hasta el borde de la pieza, en píxeles: lo mismo que el
// menú de lo elegido.
const MARGEN_DEL_GLOBO = 6;

// Vuelve a lanzar una animación de CSS aunque ya estuviera puesta.
function animar(nodo, clase) {
  nodo.classList.remove(clase);
  void nodo.offsetWidth;
  nodo.classList.add(clase);
}

export function loQueFlota({ escenario, luego, cancelar, azar, puedeHablar, dondeHabla, globos }) {
  // «+1 moneda»: asoma un momento bajo el saldo, como en el lugar.
  const ganancia = el('span', { class: 'ganancia', role: 'status' });
  // El globo, sobre el que sale contigo; la evolución arriba y las medallas
  // abajo, como en el lugar.
  const globo = el('p', { class: 'globo', 'aria-live': 'polite' });
  const celebracion = el('div', { class: 'celebracion', role: 'status' });
  const medallas = el('div', { class: 'medallas', role: 'status' });

  // --- lo que se ve cuando se le hace algo -------------------------------------------------

  let gananciaHasta = null;

  function ganar(monedas) {
    cancelar(gananciaHasta);
    ganancia.textContent = `+${MONEDAS.cuantas(monedas)}`;
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

  // Los corazones salen de la cabeza del que se acarició (`caja`, donde se
  // pinta) y suben.
  function corazones(caja) {
    for (let n = 0; n < CORAZONES; n += 1) {
      const corazon = lienzoDePieza('efectos/corazon.png', 32, 32);
      const lado = Math.round(20 + azar() * 8);
      corazon.classList.add('corazon');
      corazon.style.width = `${lado}px`;
      corazon.style.height = `${lado}px`;
      corazon.style.left = `${caja.x + caja.ancho * (0.2 + azar() * 0.6) - lado / 2}px`;
      corazon.style.top = `${caja.y + caja.alto * 0.2}px`;
      corazon.style.animationDelay = `${n * 90}ms`;
      escenario.append(corazon);
      luego(CORAZON_DURA_MS + n * 90, () => corazon.remove());
    }
  }

  // --- el globo ------------------------------------------------------------------------------

  let anterior = null;
  let globoHasta = null;

  // Cada 20 a 40 segundos el que sale contigo dice algo de `globos()`, si
  // puede hablar y no se está celebrando nada.
  function hablar() {
    luego(GLOBO_CADA_MS[0] + azar() * (GLOBO_CADA_MS[1] - GLOBO_CADA_MS[0]), hablar);
    if (document.hidden || celebracion.hasChildNodes() || !puedeHablar()) return;
    const dicho = elegirGlobo(globos(), anterior, azar);
    if (!dicho) return;
    anterior = dicho.texto;
    cancelar(globoHasta);
    globo.textContent = dicho.texto;
    globo.classList.add('visible');
    colocarElGlobo();
    globoHasta = luego(GLOBO_DURA_MS, callarGlobo);
  }

  // Empieza a hablar al rato de entrar.
  function empezarAHablar() {
    luego(PRIMER_GLOBO_MS, hablar);
  }

  // El texto se va un poco después que el globo, para que no se vea vacío
  // mientras se desvanece; y vacío, el lector de pantalla no lo vuelve a leer.
  function callarGlobo() {
    cancelar(globoHasta);
    globo.classList.remove('visible');
    globoHasta = luego(250, () => { globo.textContent = ''; });
  }

  const hablando = () => globo.classList.contains('visible');

  // Un globo no dice lo que ya no pasa: si lo que pedía ya no está entre los
  // que se pueden decir (`lista`), se calla.
  function callarSiYaNoPasa(lista) {
    if (hablando() && !lista.some((g) => g.texto === globo.textContent)) callarGlobo();
  }

  // Sobre la cabeza del que sale contigo, y nunca fuera de la pieza. Si ya no
  // está en la pieza, se calla.
  function colocarElGlobo() {
    if (!hablando()) return;
    const donde = dondeHabla();
    if (!donde) {
      callarGlobo();
      return;
    }
    const { caja, sube, lado } = donde;
    const ancho = globo.offsetWidth || 0;
    const alto = globo.offsetHeight || 0;
    globo.style.left = `${Math.min(Math.max(caja.x + caja.ancho / 2, ancho / 2 + MARGEN_DEL_GLOBO),
      lado.width - ancho / 2 - MARGEN_DEL_GLOBO)}px`;
    globo.style.top = `${Math.max(caja.y - sube, alto + SOBRE_LA_CABEZA)}px`;
  }

  return {
    ganancia,
    globo,
    celebracion,
    medallas,
    ganar,
    celebrar,
    medalla,
    corazones,
    empezarAHablar,
    callarGlobo,
    callarSiYaNoPasa,
    colocarElGlobo,
    hablando,
  };
}
