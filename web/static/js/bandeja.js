// La bandeja de los guardados de tu departamento, abierta bajo la pieza
// mientras dura el modo construcción: un botón por tipo de mueble guardado,
// con su ícono, su nombre, cuántos hay y cuánto ocupa (tocarlo toma el
// primero de ese tipo, el que se pone), marcado (`aria-pressed`) el que
// llevas en la mano. Si no queda nada guardado, lo dice. El segundo clic de
// un doble clic no cuenta.
//
// `bandejaDeGuardados({tomar, focoDeReserva, signal})` arma su nodo una vez
// (`nodo`) y lo deja al día con lo que le pasa la pantalla: no habla con el
// servidor ni decide qué está elegido ni qué llevas en la mano. `tomar(tipo)`
// es lo que hace la pantalla al tocar el botón de un tipo (su clave);
// `focoDeReserva`, el botón adonde va el foco que estaba en un tipo que ya no
// queda; y la `signal` de la pantalla deja de oír sus botones al dejarla.
// `pintar(guardados, {enCamino})` la rehace con esos guardados: lo que nace
// mientras una petición va (`enCamino`) nace sin poderse usar, y el foco que
// estaba en un tipo vuelve al de ese mismo tipo. `marcar(tipo)` dice qué tipo
// llevas en la mano (su clave, o `null`), y `pintar` lo marca también en lo
// que rehace. Todo texto entra por `el` o por `textContent`.

import { lienzoDePieza } from './arte.js';
import { el } from './dom.js';
import { cuantoOcupa } from './lista.js';

const ROTULO_DE_GUARDADOS = 'Guardados · toca uno y después una casilla';
const NADA_GUARDADO = 'No queda nada guardado.';
// El ícono de cada mueble de la bandeja, en píxeles de pantalla.
const LADO_DEL_ICONO = 40;

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

export function bandejaDeGuardados({ tomar, focoDeReserva, signal }) {
  const nodo = el('div', { class: 'bandeja' });

  // El botón de cada tipo de la bandeja, por su clave.
  const tiposEnLaBandeja = new Map();
  // La clave de lo que llevas en la mano, o `null`.
  let enLaMano = null;

  function marcar(tipo) {
    enLaMano = tipo;
    for (const [clave, boton] of tiposEnLaBandeja) boton.setAttribute('aria-pressed', String(clave === enLaMano));
  }

  function pintar(guardados, { enCamino }) {
    const conFoco = [...tiposEnLaBandeja].find(([, boton]) => boton === document.activeElement);
    tiposEnLaBandeja.clear();
    const rotulo = el('p', { class: 'rotulo', id: 'departamento-guardados' }, ROTULO_DE_GUARDADOS);
    const tipos = porTipo(guardados);
    if (!tipos.length) {
      nodo.replaceChildren(rotulo, el('p', { class: 'bandeja-vacia' }, NADA_GUARDADO));
    } else {
      const botones = tipos.map(({ primero, cuantos }) => {
        const icono = lienzoDePieza(primero.icono, LADO_DEL_ICONO, LADO_DEL_ICONO);
        icono.classList.add('bandeja-icono');
        const boton = el('button', {
          type: 'button', class: 'bandeja-tipo', 'aria-pressed': 'false', 'aria-disabled': enCamino ? 'true' : null,
        },
          icono,
          el('span', { class: 'bandeja-nombre' }, `${primero.nombre} × ${cuantos}`),
          el('span', { class: 'bandeja-ocupa' }, cuantoOcupa(primero)));
        // El segundo clic de un doble clic no cuenta: el primero, en «Construir»,
        // desliza la página, y el segundo puede caer aquí. Un clic suelto (1) y
        // el teclado (0), sí.
        boton.addEventListener('click', (clic) => {
          if (clic.detail > 1) return;
          tomar(primero.clave);
        }, { signal });
        tiposEnLaBandeja.set(primero.clave, boton);
        return boton;
      });
      nodo.replaceChildren(rotulo,
        el('div', { class: 'bandeja-tipos', role: 'group', 'aria-labelledby': 'departamento-guardados' }, botones));
    }
    marcar(enLaMano);
    if (conFoco) (tiposEnLaBandeja.get(conFoco[0]) || focoDeReserva).focus({ preventScroll: true });
  }

  return { nodo, pintar, marcar };
}
