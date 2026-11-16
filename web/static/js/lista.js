// La lista de tu departamento, bajo la pieza y sus paneles: todo lo que se
// hace tocando el dibujo, con botones de verdad, para quien no usa el dibujo
// (con el teclado, con un lector de pantalla). Siempre está a la vista: no es
// un modo.
//
// - «Tus gachamones»: un botón por cada uno, marcado (`aria-pressed`) el que
//   tiene su ficha a la vista. Elegirlo es lo mismo que tocarlo en la pieza,
//   sin su menú.
// - «Muebles puestos»: cada uno con su nombre y su sitio, y «Mover», «Girar»
//   (no lo de pared) y «Guardar»; la puerta, «Mover» y «Salir».
// - «Guardados»: cada mueble guardado, de a uno, con su nombre, cuánto ocupa
//   y «Poner».
// - «Mover» y «Poner» abren «¿Dónde?» en la fila de ese mueble: un
//   desplegable con los sitios donde cabe (al mover, sin el sitio donde ya
//   está) y «Ponerlo ahí». Si no cabe en ninguno no se abre, y la pantalla lo
//   dice. Se cierra con Escape, pulsando otra vez lo que lo abrió o cuando ese
//   mueble cambia de sitio; si cambia lo que cabe, sus sitios se rehacen.
// - Un `role="status"` que no se ve (`anunciar`), donde la pantalla le vuelve
//   a decir a quien no ve el dibujo cómo quedó la pieza.
//
// `listaDelDepartamento(acciones)` arma los nodos una vez y los deja al día
// con lo que le pasa la pantalla (`pintar(depto, visto)`, con el id del que
// tiene su ficha a la vista): no habla con el servidor ni decide qué está
// elegido. `acciones` es lo que hace la pantalla: `{ver(id), sitios(id),
// noCabe(), poner(id, sitio, boton), girar(id, boton), guardar(id, boton),
// salir()}`; `sitios(id)` son los `{x, y, giro}` donde cabe ese mueble. Lo
// que queda en su sitio no se mueve (sacar del documento lo que tiene el foco
// se lo quita); si el foco estaba en algo que se fue, vuelve a ese mismo
// mueble, en la lista donde haya quedado. Mientras una petición va (`ocupar`),
// lo que no la mandó no se puede usar. Todo texto entra por `el` o por
// `textContent`.

import { nombreDelSitio } from './casillas.js';
import { el } from './dom.js';

const TUS_GACHAMONES = 'Tus gachamones';
const PUESTOS = 'Muebles puestos';
const GUARDADOS = 'Guardados';
const DONDE = '¿Dónde?';
const NADA_GUARDADO = 'No queda nada guardado.';
// Lo de pared va en las paredes y no se gira.
const PARED = 'pared';
// Lo que se hace con cada botón de una fila, para devolverle el foco al mismo.
const MOVER = 'mover';
const GIRAR = 'girar';
const GUARDAR = 'guardar';
const SALIR = 'salir';
const PONER = 'poner';
const SITIO = 'sitio';
const AHI = 'ahi';

// Cuánto ocupa un mueble, como se dice bajo su nombre (en la lista y en la bandeja).
export function cuantoOcupa(mueble) {
  if (mueble.capa === PARED) return 'en la pared';
  const casillas = mueble.ancho * mueble.fondo;
  return casillas === 1 ? '1 casilla' : `${casillas} casillas`;
}

// El nombre de un mueble puesto con su sitio: «Maceta, en fila 3, columna 3»,
// «Cuadro, en la pared derecha, tramo 2».
function nombreConSitio(puesto) {
  const sitio = nombreDelSitio(puesto.x, puesto.y);
  return puesto.capa === PARED ? `${puesto.nombre}, en la ${sitio}` : `${puesto.nombre}, en ${sitio}`;
}

const claveDelSitio = ({ x, y, giro }) => `${x},${y},${giro}`;

export function listaDelDepartamento(acciones) {
  // Mientras una petición va, y qué la mandó. Si la mandó un botón de la
  // fila de un mueble, a qué mueble y qué botón vuelve el foco después.
  let enCamino = false;
  let origen = null;
  let trasLaPeticion = null;

  // Un botón de la lista. Lo que nace mientras una petición va, nace sin poderse usar.
  function botonDeLaLista(texto, alTocar, atributos = {}) {
    const boton = el('button', {
      type: 'button', class: 'boton boton-chico', 'aria-disabled': enCamino ? 'true' : null, ...atributos,
    }, texto);
    boton.addEventListener('click', () => alTocar(boton));
    return boton;
  }

  const anuncio = el('p', { class: 'solo-lector', role: 'status' });

  // --- tus gachamones ----------------------------------------------------------------

  const deGachamones = el('div', { class: 'lista-gachamones-botones' });
  const gachamones = el('div', { class: 'lista-gachamones', role: 'group', 'aria-label': TUS_GACHAMONES, hidden: true },
    el('p', { class: 'rotulo', 'aria-hidden': 'true' }, TUS_GACHAMONES), deGachamones);
  // El botón de cada uno, por id, en el orden en que están.
  let botonesDeGachamon = new Map();

  function ponerGachamones(plantel, visto) {
    const ids = plantel.map((g) => g.id);
    if (ids.join() !== [...botonesDeGachamon.keys()].join()) {
      botonesDeGachamon = new Map(plantel.map((g) => [g.id,
        botonDeLaLista(g.nombre, () => acciones.ver(g.id), { 'aria-pressed': 'false' })]));
      deGachamones.replaceChildren(...botonesDeGachamon.values());
    }
    for (const g of plantel) {
      const boton = botonesDeGachamon.get(g.id);
      if (boton.textContent !== g.nombre) boton.textContent = g.nombre;
      boton.setAttribute('aria-pressed', String(g.id === visto));
    }
    gachamones.hidden = !plantel.length;
  }

  // --- los muebles -------------------------------------------------------------------

  // Una lista de muebles («Muebles puestos» o «Guardados»): su sección, con su
  // rótulo, lo que dice si está vacía (`vacio`, si dice algo) y sus filas por
  // id, en el orden en que están.
  function seccion(clase, rotulo, vacio = null) {
    const id = `${clase}-rotulo`;
    const ul = el('ul', { class: 'lista-muebles' });
    const vacia = vacio ? el('p', { class: 'lista-vacia', hidden: true }, vacio) : null;
    const titulo = el('h2', { class: 'rotulo', id, tabindex: '-1' }, rotulo);
    const nodo = el('section', { class: clase, 'aria-labelledby': id }, titulo, ul, vacia);
    return { nodo, ul, vacia, titulo, filas: new Map() };
  }

  const puestos = seccion('lista-puestos', PUESTOS);
  const guardados = seccion('lista-guardados', GUARDADOS, NADA_GUARDADO);

  // La fila de un mueble: su nombre (y lo que haya debajo) y sus botones, en un
  // grupo que se llama como el mueble. `abre` es el botón que abre «¿Dónde?».
  function filaDe(id, textos, botones, abre) {
    const etiquetas = textos.map((_, n) => `lista-mueble-${id}-${n}`).join(' ');
    textos.forEach((texto, n) => texto.setAttribute('id', `lista-mueble-${id}-${n}`));
    const li = el('li', { class: 'lista-fila', 'data-fila': id },
      el('div', { class: 'mueble-texto' }, textos),
      el('div', { class: 'lista-botones', role: 'group', 'aria-labelledby': etiquetas }, botones));
    return { id, li, abre, primero: botones[0] };
  }

  function filaPuesta(puesto) {
    const nombre = el('p', { class: 'mueble-nombre' });
    const mover = botonDeLaLista('Mover', () => abrirDonde(puesto.id, MOVER),
      { 'data-accion': MOVER, 'aria-expanded': 'false' });
    const botones = [mover];
    if (puesto.capa !== PARED) {
      botones.push(botonDeLaLista('Girar', (boton) => acciones.girar(puesto.id, boton), { 'data-accion': GIRAR }));
    }
    // La puerta no se guarda: por ella se sale.
    if (puesto.puerta) botones.push(botonDeLaLista('Salir', () => acciones.salir(), { 'data-accion': SALIR }));
    else botones.push(botonDeLaLista('Guardar', (boton) => acciones.guardar(puesto.id, boton), { 'data-accion': GUARDAR }));
    const fila = filaDe(puesto.id, [nombre], botones, mover);
    fila.pintar = (p) => {
      const texto = nombreConSitio(p);
      if (nombre.textContent !== texto) nombre.textContent = texto;
      fila.sitio = claveDelSitio(p);
    };
    return fila;
  }

  function filaGuardada(guardado) {
    const nombre = el('p', { class: 'mueble-nombre' });
    const ocupa = el('p', { class: 'mueble-ocupa' });
    const poner = botonDeLaLista('Poner', () => abrirDonde(guardado.id, PONER),
      { 'data-accion': PONER, 'aria-expanded': 'false' });
    const fila = filaDe(guardado.id, [nombre, ocupa], [poner], poner);
    fila.pintar = (g) => {
      if (nombre.textContent !== g.nombre) nombre.textContent = g.nombre;
      if (ocupa.textContent !== cuantoOcupa(g)) ocupa.textContent = cuantoOcupa(g);
    };
    return fila;
  }

  // Las filas de esa lista al día con `muebles`: las que siguen se quedan
  // donde están; sólo si cambia cuáles hay o su orden se vuelven a poner.
  function ponerFilas(lista, muebles, hacer) {
    const antes = [...lista.filas.keys()];
    const filas = new Map(muebles.map((m) => [m.id, lista.filas.get(m.id) || hacer(m)]));
    for (const m of muebles) filas.get(m.id).pintar(m);
    for (const [id, fila] of lista.filas) if (!filas.has(id)) fila.li.remove();
    lista.filas = filas;
    if (antes.join() !== [...filas.keys()].join()) lista.ul.replaceChildren(...[...filas.values()].map((f) => f.li));
    if (lista.vacia) lista.vacia.hidden = muebles.length > 0;
  }

  // --- ¿dónde? -------------------------------------------------------------------------

  // Lo que está abierto: de qué mueble, si se mueve o se pone, desde qué
  // sitio se abrió (al mover), sus sitios y sus nodos.
  let donde = null;

  // El desplegable se llama «¿Dónde?» y se describe con el nombre de ese mueble.
  function hacerElDonde(id, modo, sitios, fila) {
    const select = el('select', {
      class: 'donde-sitio', id: 'lista-donde-sitio', 'data-accion': SITIO, 'aria-describedby': `lista-mueble-${id}-0`,
    });
    const ahi = botonDeLaLista('Ponerlo ahí', (boton) => {
      const sitio = donde && donde.sitios[Number(select.value)];
      if (sitio) acciones.poner(id, sitio, boton);
    }, { class: 'boton boton-chico principal', 'data-accion': AHI });
    const caja = el('div', { class: 'donde', id: 'lista-donde' },
      el('label', { class: 'rotulo', for: 'lista-donde-sitio' }, DONDE), select, ahi);
    caja.addEventListener('keydown', (evento) => {
      if (evento.key === 'Escape') cerrarDonde();
    });
    select.addEventListener('change', () => {
      const sitio = donde && donde.sitios[Number(select.value)];
      if (sitio) donde.elegido = claveDelSitio(sitio);
    });
    donde = { id, modo, fila, desde: fila.sitio, sitios: [], elegido: null, caja, select };
    ponerSitios(sitios);
    fila.li.append(caja);
    fila.abre.setAttribute('aria-expanded', 'true');
    fila.abre.setAttribute('aria-controls', 'lista-donde');
  }

  // Las opciones del desplegable; la elegida sigue elegida si todavía cabe ahí.
  function ponerSitios(sitios) {
    donde.sitios = sitios;
    donde.select.replaceChildren(...sitios.map((s, n) => el('option', { value: String(n) }, nombreDelSitio(s.x, s.y))));
    const sigue = sitios.findIndex((s) => claveDelSitio(s) === donde.elegido);
    donde.select.value = String(Math.max(sigue, 0));
    donde.elegido = claveDelSitio(sitios[Math.max(sigue, 0)]);
  }

  // Se cierra; si el foco estaba dentro, vuelve a lo que lo abrió.
  function cerrarDonde() {
    if (!donde) return;
    const { caja, fila } = donde;
    const conFoco = caja.contains(document.activeElement);
    donde = null;
    caja.remove();
    fila.abre.setAttribute('aria-expanded', 'false');
    fila.abre.removeAttribute('aria-controls');
    if (conFoco) fila.abre.focus();
  }

  // Pulsar «Mover» o «Poner» lo abre en esa fila, con el foco en el
  // desplegable; pulsarlo otra vez lo cierra. Si no cabe en ningún sitio, lo
  // dice la pantalla y no se abre.
  function abrirDonde(id, modo) {
    if (enCamino) return;
    const abierto = donde && donde.id === id && donde.modo === modo;
    cerrarDonde();
    if (abierto) return;
    const fila = (modo === MOVER ? puestos : guardados).filas.get(id);
    if (!fila) return;
    const sitios = acciones.sitios(id);
    if (!sitios.length) {
      acciones.noCabe();
      return;
    }
    hacerElDonde(id, modo, sitios, fila);
    donde.select.focus();
  }

  // Con la pieza nueva: si ese mueble ya no está donde estaba (se puso, se
  // movió o se guardó) o ya no cabe en ningún sitio, se cierra; si cambia
  // dónde cabe, se rehacen sus sitios.
  function ponerElDonde() {
    if (!donde) return;
    const fila = (donde.modo === MOVER ? puestos : guardados).filas.get(donde.id);
    const sigue = fila === donde.fila && (donde.modo !== MOVER || fila.sitio === donde.desde);
    const sitios = sigue ? acciones.sitios(donde.id) : [];
    if (!sitios.length) {
      cerrarDonde();
      return;
    }
    if (sitios.map(claveDelSitio).join() !== donde.sitios.map(claveDelSitio).join()) ponerSitios(sitios);
  }

  // --- el foco ----------------------------------------------------------------------------

  const nodo = el('div', { class: 'lista-departamento' }, anuncio, gachamones, puestos.nodo, guardados.nodo);

  // Dónde está `foco` (si no se dice, lo que tiene el foco), si está en la
  // lista: en el botón de un gachamon, o en la fila de un mueble (y en cuál de
  // sus botones).
  function dondeEsta(foco = document.activeElement) {
    if (!foco || !nodo.contains(foco)) return null;
    for (const [id, boton] of botonesDeGachamon) if (boton === foco) return { gachamon: id };
    for (const lista of [puestos, guardados]) {
      for (const [id, fila] of lista.filas) {
        if (fila.li.contains(foco)) return { mueble: id, accion: foco.getAttribute('data-accion'), lista };
      }
    }
    return null;
  }

  // Si el foco se fue con lo que se quitó, vuelve a lo mismo: el botón de ese
  // gachamon (o el primero), o ese mueble en la lista donde haya quedado, en
  // el mismo botón si lo tiene (si no, en el que abre «¿Dónde?»). Si ese
  // mueble ya no está, al rótulo de su lista.
  function devolverElFoco(antes) {
    if (antes.gachamon !== undefined) {
      const boton = botonesDeGachamon.get(antes.gachamon) || botonesDeGachamon.values().next().value;
      if (boton) boton.focus();
      return;
    }
    const fila = puestos.filas.get(antes.mueble) || guardados.filas.get(antes.mueble);
    if (!fila) {
      antes.lista.titulo.focus();
      return;
    }
    const mismo = antes.accion && fila.li.querySelector(`[data-accion=${antes.accion}]`);
    (mismo || fila.abre || fila.primero).focus();
  }

  // --- lo que hace la pantalla ------------------------------------------------------------

  // `depto` es la pieza que llegó; `visto`, el id del que tiene su ficha a la
  // vista. Tras lo que mandó la fila de un mueble, el foco que se perdió (o
  // que nunca llegó al botón: en algunos navegadores tocar un botón no lo
  // enfoca) va a ese mueble; si no, el que se fue con lo que se quitó vuelve.
  function pintar(depto, visto) {
    const antes = dondeEsta();
    const vuelta = trasLaPeticion;
    trasLaPeticion = null;
    ponerGachamones(depto.plantel, visto);
    ponerFilas(puestos, depto.puestos, filaPuesta);
    ponerFilas(guardados, depto.guardados, filaGuardada);
    ponerElDonde();
    const foco = document.activeElement;
    if (vuelta && (!foco || foco === document.body)) devolverElFoco(vuelta);
    else if (antes && !nodo.contains(foco)) devolverElFoco(antes);
  }

  // Una petición sale (`desde`, el botón que la mandó o lo que sea) o vuelve (`null`).
  function ocupar(desde) {
    enCamino = desde !== null;
    origen = desde;
    if (desde !== null) {
      const deUnaFila = dondeEsta(desde);
      trasLaPeticion = deUnaFila && deUnaFila.mueble !== undefined ? deUnaFila : null;
    }
    for (const boton of nodo.querySelectorAll('button')) {
      if (enCamino && boton !== origen) boton.setAttribute('aria-disabled', 'true');
      else boton.removeAttribute('aria-disabled');
    }
  }

  function anunciar(texto) {
    anuncio.textContent = texto;
  }

  return { nodo, pintar, ocupar, anunciar };
}
