// Lo de ampliar tu departamento, que va en lugar de lo de la derecha mientras
// está abierto: un botón por cada lado que todavía puede crecer, con lo que
// suma y lo que cuesta (si ya no crece por ninguno, lo dice), y «Volver».
// Tocar un lado no cobra: debajo de su botón, que sigue a la vista (así se lee
// qué se compra) y dice que está abierta, sale la pregunta de la Tienda, con
// «Ampliar» y «No»; sólo una a la vez. Tocar su botón otra vez, «No» o Escape
// la cierran sin mandar nada, y el foco vuelve a ese botón. El segundo clic
// (o el tercero…) de una ráfaga no confirma. La pregunta vale mientras la
// pieza mida y cueste lo que medía y costaba al abrirla: si llega otra, se
// cierra, para que no se cobre algo distinto de lo que se ve.
//
// `panelDeAmpliar({alConfirmar, alVolver, signal})` arma su nodo una vez
// (`nodo`, escondido) y lo deja al día con lo que le pasa la pantalla: no
// habla con el servidor ni decide si está abierto. `alConfirmar(eje, boton)`
// es lo que hace la pantalla con «Ampliar» en la pregunta de ese lado
// (`'ancho'`, una columna; `'fondo'`, una fila), desde ese botón; `alVolver()`,
// con «Volver», que antes cierra la pregunta; y la `signal` de la pantalla
// deja de oír sus botones al dejarla.
//
// - `pintar(depto, {abierto})`: la pieza que llegó y si está abierto (si no,
//   se esconde). Abierto, se rehace sólo si cambió lo que mide la pieza, lo
//   que cuesta cada lado o la pregunta abierta; si no, el foco no se mueve (un
//   lector de pantalla no vuelve a leer nada). El foco que estaba en él vuelve
//   a lo mismo: el rótulo; la misma parte de la pregunta, si sigue abierta; su
//   texto, si se acaba de abrir desde su botón; el botón de ese lado; o, si ya
//   no puede crecer por ahí, «Volver».
// - `traerALaVista()`: lo trae a la vista y le da el foco a su rótulo.
// - `preguntaAbiertaEn(eje)`: si la pregunta abierta es la de ese lado.
// - `cerrarLaPregunta()`: la cierra sin rehacer nada; se ve cerrada la próxima
//   vez que se pinte.
// - `ocupar(desde)`: una petición sale (`desde`, lo que la mandó) o vuelve
//   (`null`). Mientras va, tocar un lado o cerrar la pregunta no hace nada, y
//   lo que nace, nace sin poderse usar (lo que ya estaba lo apaga la pantalla).
//
// Todo texto entra por `el` o por `textContent`.

import { MONEDAS, cajaDePregunta } from './articulos.js';
import { el } from './dom.js';

const ROTULO_DE_AMPLIAR = 'Ampliar el departamento';
const YA_NO_CRECE = 'Tu departamento ya no puede crecer más.';
// La pregunta antes de crecer, como la de la Tienda: el coste es el que manda
// el servidor, dicho con la palabra («N monedas», «1 moneda»).
const preguntaDeAmpliar = (coste) => `¿Ampliar por ${MONEDAS.cuantas(coste)}?`;

export function panelDeAmpliar({ alConfirmar, alVolver, signal }) {
  const nodo = el('div', { class: 'ampliar', hidden: true });

  // La pieza que llegó y si está abierto, como los dice la pantalla; si una
  // petición va.
  let depto = null;
  let abierto = false;
  let enCamino = false;
  // La pregunta abierta, o `null`: `{eje, coste, mide}`, el lado y lo que
  // costaba y medía la pieza al abrirla. Sólo hay una.
  let preguntaAbierta = null;
  // Para qué está hecho (lo que mide la pieza, lo que cuesta cada lado y la
  // pregunta abierta), o `null`: si no cambia, no se rehace, y el foco no se
  // mueve (un lector de pantalla no vuelve a leer nada).
  let ampliarDe = null;
  // Las partes de la pregunta que se ve (`{eje, cabeza, si, no}`), o `null`:
  // si el panel se rehace con ella abierta, el foco vuelve a la misma parte.
  let partesDeLaPregunta = null;

  // El botón de crecer por ese lado, o `null` si ya no crece por ahí.
  const botonDelLado = (eje) => [...nodo.querySelectorAll('.boton-lado')]
    .find((b) => b.getAttribute('data-eje') === eje) || null;

  // Abierto y con la pieza, lo de ampliar al día con ella. Lo que nace
  // mientras una petición va no se puede usar.
  function rehacer() {
    if (!abierto || !depto) return;
    const mide = `${depto.ancho} × ${depto.fondo}`;
    const lados = [
      { eje: 'fondo', que: 'fila', casillas: depto.ancho, coste: depto.ampliar.fondo },
      { eje: 'ancho', que: 'columna', casillas: depto.fondo, coste: depto.ampliar.ancho },
    ].filter(({ coste }) => coste !== null && coste !== undefined);
    if (preguntaAbierta) {
      const lado = lados.find(({ eje }) => eje === preguntaAbierta.eje);
      if (!lado || lado.coste !== preguntaAbierta.coste || mide !== preguntaAbierta.mide) preguntaAbierta = null;
    }
    const para = `${mide} ${lados.map(({ eje, coste }) => `${eje} ${coste}`).join(' ')} ${preguntaAbierta ? preguntaAbierta.eje : '-'}`;
    if (para === ampliarDe) return;
    ampliarDe = para;
    const conFoco = nodo.contains(document.activeElement) ? document.activeElement : null;
    const antes = partesDeLaPregunta;
    const parte = antes && conFoco ? ['cabeza', 'si', 'no'].find((k) => antes[k] === conFoco) : undefined;
    partesDeLaPregunta = null;
    const ocupado = enCamino ? 'true' : null;
    const rotulo = el('h2', { class: 'rotulo', id: 'departamento-ampliar', tabindex: '-1' }, ROTULO_DE_AMPLIAR);
    const volver = el('button', { type: 'button', class: 'boton boton-volver' }, 'Volver');
    volver.addEventListener('click', () => {
      preguntaAbierta = null;
      alVolver();
    }, { signal });
    let opciones;
    if (lados.length) {
      opciones = el('div', { class: 'ampliar-lados', role: 'group', 'aria-labelledby': 'departamento-ampliar' },
        lados.flatMap(({ eje, que, casillas, coste }) => {
          const abierta = Boolean(preguntaAbierta) && preguntaAbierta.eje === eje;
          // Se ve con el símbolo y se lee con la palabra, como los saldos.
          const boton = el('button', {
            type: 'button',
            class: 'boton boton-lado',
            'data-eje': eje,
            'aria-expanded': String(abierta),
            'aria-disabled': ocupado,
          },
            el('span', {}, `+ ${que} (${casillas} casillas) · `,
              el('span', { 'aria-hidden': 'true' }, `${coste} ${MONEDAS.simbolo}`),
              el('span', { class: 'solo-lector' }, MONEDAS.cuantas(coste))));
          boton.addEventListener('click', () => preguntar(eje), { signal });
          if (!abierta) return [boton];
          const {
            caja, cabeza, si, no,
          } = cajaDePregunta(preguntaDeAmpliar(coste), 'Ampliar', {
            // El segundo clic (o el tercero…) de una ráfaga en el mismo sitio no
            // confirma: un doble clic en el otro lado mueve los botones, y ese
            // segundo clic puede caer aquí. Un clic suelto (1) y el teclado (0), sí.
            alConfirmar: (clic) => {
              if (clic.detail > 1) return;
              alConfirmar(eje, si);
            },
            alDesistir: () => desistir(eje),
          });
          caja.setAttribute('data-eje', eje);
          if (ocupado) for (const suyo of [si, no]) suyo.setAttribute('aria-disabled', ocupado);
          partesDeLaPregunta = {
            eje, cabeza, si, no,
          };
          return [boton, caja];
        }));
    } else {
      opciones = el('p', { class: 'ampliar-tope' }, YA_NO_CRECE);
    }
    nodo.replaceChildren(rotulo, opciones, volver);
    if (conFoco) {
      const deUnLado = conFoco.closest('[data-eje]');
      const eje = deUnLado && deUnLado.getAttribute('data-eje');
      const suPregunta = partesDeLaPregunta && partesDeLaPregunta.eje === eje ? partesDeLaPregunta : null;
      const yaEstaba = Boolean(antes) && antes.eje === eje;
      let destino = (eje && botonDelLado(eje)) || volver;
      if (conFoco.classList.contains('rotulo')) destino = rotulo;
      else if (suPregunta && parte) destino = suPregunta[parte];
      else if (suPregunta && !yaEstaba) destino = suPregunta.cabeza;
      destino.focus({ preventScroll: true });
    }
  }

  // El primer toque en un lado: debajo de su botón sale la pregunta, con lo
  // que cuesta ahora, y la que hubiera abierta se cierra; tocarlo otra vez la
  // cierra (un doble clic abre y cierra, y no cobra). El foco va a la pregunta,
  // que se lee; no a «Ampliar», para que una tecla que se queda apretada no
  // cobre.
  function preguntar(eje) {
    if (enCamino || !depto) return;
    if (preguntaAbierta && preguntaAbierta.eje === eje) {
      desistir(eje);
      return;
    }
    preguntaAbierta = { eje, coste: depto.ampliar[eje], mide: `${depto.ancho} × ${depto.fondo}` };
    rehacer();
    if (!partesDeLaPregunta) return;
    partesDeLaPregunta.cabeza.focus({ preventScroll: true });
    // En un teléfono puede abrirse bajo el borde de la ventana: se trae a la vista.
    const pregunta = nodo.querySelector('.pregunta');
    if (pregunta) pregunta.scrollIntoView({ block: 'nearest' });
  }

  // «No», Escape o su botón otra vez: se cierra sin mandar nada y el foco
  // vuelve al botón que la abrió.
  function desistir(eje) {
    if (enCamino) return;
    preguntaAbierta = null;
    rehacer();
    const boton = botonDelLado(eje);
    if (boton) boton.focus({ preventScroll: true });
  }

  function pintar(nuevo, { abierto: estaAbierto }) {
    depto = nuevo;
    abierto = estaAbierto;
    nodo.hidden = !abierto;
    rehacer();
  }

  // Al abrirlo: en un teléfono queda más abajo que la pieza.
  function traerALaVista() {
    nodo.scrollIntoView({ block: 'nearest' });
    const rotulo = nodo.querySelector('h2');
    if (rotulo) rotulo.focus({ preventScroll: true });
  }

  const preguntaAbiertaEn = (eje) => Boolean(preguntaAbierta) && preguntaAbierta.eje === eje;

  function cerrarLaPregunta() {
    preguntaAbierta = null;
  }

  function ocupar(desde) {
    enCamino = desde !== null;
  }

  return {
    nodo, pintar, traerALaVista, preguntaAbiertaEn, cerrarLaPregunta, ocupar,
  };
}
