// Tus gachamones, al lado de la pieza de tu departamento: la ficha del que
// está elegido (su nombre, la chapa «Sale contigo» si es el que sale contigo,
// «Especie etapa · nivel N», sus tres barras, sus cuatro cuidados con lo que
// les falta, «Acariciar», «Ver ficha» y, si no es el que sale contigo, «Salir
// con …») y, debajo, «A todos». Sin ningún gachamon, en lugar de la ficha se
// dice que todavía no vive ninguno, y «A todos» no está.
//
// `panelDelPlantel(acciones)` arma los nodos una vez y los deja al día con lo
// que le pasa la pantalla: no habla con el servidor ni decide quién está
// elegido. `acciones` es lo que hace la pantalla cuando se toca cada cosa:
// `{cuidar(accion, boton), acariciar(boton), salir(boton), verFicha(),
// aTodos(accion, boton)}`. Lo que es igual en la pantalla de un lugar (los
// cuidados, las barras, las cuentas de las esperas) viene de `cuidados.js`.
// Todo texto entra por `el` o por `textContent`.

import {
  BARRAS, CUIDADOS, botonDeCuidado, contarCuidado, faltaPara, medidorDe, pintarMedidores, ponerEsperas,
} from './cuidados.js';
import { el } from './dom.js';

const NINGUNO = 'Todavía no vive ningún gachamon contigo.';
const SALE_CONTIGO = 'Sale contigo';
const A_TODOS = 'A todos';
// Lo que dice cada botón de «A todos», por cuidado.
const A_TODOS_DICE = {
  alimentar: 'Alimentar a todos',
  jugar: 'Jugar con todos',
  entrenar: 'Entrenar con todos',
  limpiar: 'Bañar a todos',
};

export function panelDelPlantel(acciones) {
  // --- la ficha del elegido ----------------------------------------------------------

  const nombre = el('span', {});
  const titulo = el('span', { class: 'titulo-del-gachamon' });
  const cabeza = el('h2', { class: 'ficha-elegido-nombre', id: 'departamento-elegido', tabindex: '-1' }, nombre, titulo);
  const chapa = el('span', { class: 'chapa-sale-contigo' }, SALE_CONTIGO);
  const verFicha = el('button', { type: 'button', class: 'boton boton-chico boton-ver-ficha' }, 'Ver ficha');
  verFicha.addEventListener('click', () => acciones.verFicha());
  // El nombre y «Ver ficha» están siempre; la chapa va entre los dos sólo en
  // la del que sale contigo.
  const lineaDeCabeza = el('div', { class: 'ficha-cabeza' }, cabeza, verFicha);
  const detalle = el('p', { class: 'ficha-detalle' });
  const medidores = BARRAS.map(medidorDe);
  const cuidados = CUIDADOS.map((datos) => {
    const cuidado = botonDeCuidado(datos);
    cuidado.nodo.addEventListener('click', () => acciones.cuidar(cuidado.accion, cuidado.nodo));
    return cuidado;
  });
  const acariciar = el('button', { type: 'button', class: 'boton boton-chico boton-acariciar' }, 'Acariciar');
  acariciar.addEventListener('click', () => acciones.acariciar(acariciar));
  const salir = el('button', { type: 'button', class: 'boton boton-chico principal boton-salir-con' });
  salir.addEventListener('click', () => acciones.salir(salir));
  // «Acariciar» está siempre; «Salir con …», sólo en la de otro.
  const accionesDelElegido = el('div', { class: 'acciones-elegido' }, acariciar);
  const ficha = el('section', { class: 'ficha-elegido', 'aria-labelledby': 'departamento-elegido' });

  // --- a todos -----------------------------------------------------------------------

  const aTodos = el('div', { class: 'a-todos', role: 'group', 'aria-label': A_TODOS, hidden: true });
  const paraTodos = CUIDADOS.map(({ accion, icono }) => {
    const boton = el('button', { type: 'button', class: 'boton boton-a-todos' },
      el('span', { 'aria-hidden': 'true' }, icono), A_TODOS_DICE[accion]);
    boton.addEventListener('click', () => acciones.aTodos(accion, boton));
    return boton;
  });
  const deATodos = [el('p', { class: 'rotulo', 'aria-hidden': 'true' }, A_TODOS), el('div', { class: 'a-todos-botones' }, paraTodos)];

  // --- lo que se pinta -----------------------------------------------------------------

  // Cuándo se acaba cada espera de cada gachamon (por su id), en la hora de este teléfono.
  const esperas = new Map();
  // El que se enseña, y si hay una petición en camino (y qué la mandó).
  let visto = null;
  let enCamino = false;
  let origen = null;

  const hastaDe = (id) => esperas.get(id) || {};

  // Lo que le falta a ese cuidado del que se enseña, en segundos.
  function falta(accion) {
    return visto ? faltaPara(hastaDe(visto.id), accion) : 0;
  }

  // Las esperas recién leídas de esos gachamones (lo demás se cuenta desde la última lectura).
  function leidas(lista) {
    for (const g of lista) {
      const hasta = {};
      ponerEsperas(hasta, g.esperas);
      esperas.set(g.id, hasta);
    }
  }

  // Lo que le falta a cada cuidado del que se enseña. Mientras una petición va,
  // los botones que mandan algo (salvo el que la mandó, que espera) no se pueden usar.
  function contar() {
    if (!visto) return;
    for (const c of cuidados) {
      contarCuidado(c, faltaPara(hastaDe(visto.id), c.accion));
      if (enCamino && c.nodo !== origen) c.nodo.setAttribute('aria-disabled', 'true');
    }
    for (const boton of [acariciar, salir, ...paraTodos]) {
      if (enCamino && boton !== origen) boton.setAttribute('aria-disabled', 'true');
      else boton.removeAttribute('aria-disabled');
    }
  }

  // `quien` es el que se enseña (su ficha corta, con `activo`), o `null` si no
  // vive ninguno. Lo que se ve siempre se queda en su sitio (sacar del
  // documento lo que tiene el foco se lo quita): sólo entran o salen la chapa
  // y «Salir con …» cuando cambia si es el que sale contigo. El foco que
  // estaba en lo que se quita espera en su nombre.
  function pintar(quien) {
    visto = quien;
    const conFoco = ficha.contains(document.activeElement) ? document.activeElement : null;
    if (!quien) {
      ficha.replaceChildren(el('p', { class: 'ficha-elegido-vacia' }, NINGUNO));
      aTodos.replaceChildren();
      aTodos.hidden = true;
      return;
    }
    nombre.textContent = quien.nombre;
    titulo.textContent = quien.titulo ? ` ${quien.titulo}` : '';
    if (quien.activo && !lineaDeCabeza.contains(chapa)) lineaDeCabeza.insertBefore(chapa, verFicha);
    if (!quien.activo && lineaDeCabeza.contains(chapa)) chapa.remove();
    detalle.textContent = `${quien.nombre_especie} ${quien.nombre_etapa} · nivel ${quien.nivel}`;
    pintarMedidores(medidores, quien.barras);
    if (salir.textContent !== `Salir con ${quien.nombre}`) salir.textContent = `Salir con ${quien.nombre}`;
    if (!quien.activo && !accionesDelElegido.contains(salir)) accionesDelElegido.append(salir);
    if (quien.activo && accionesDelElegido.contains(salir)) salir.remove();
    if (!ficha.contains(cabeza)) {
      ficha.replaceChildren(lineaDeCabeza, detalle,
        el('div', { class: 'medidores' }, medidores.map((m) => m.nodo)),
        el('div', { class: 'cuidados-elegido', role: 'group', 'aria-label': 'Cuidados' }, cuidados.map((c) => c.nodo)),
        accionesDelElegido);
    }
    if (!aTodos.hasChildNodes()) aTodos.replaceChildren(...deATodos);
    aTodos.hidden = false;
    contar();
    if (conFoco && !ficha.contains(conFoco)) cabeza.focus({ preventScroll: true });
  }

  // Una petición sale (`desde`, el botón que la mandó o lo que sea) o vuelve (`null`).
  function ocupar(desde) {
    enCamino = desde !== null;
    origen = desde;
    contar();
  }

  return { ficha, aTodos, leidas, pintar, contar, falta, ocupar };
}
