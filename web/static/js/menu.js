// El menú de lo elegido en la pieza de tu departamento: sale encima de lo
// elegido, junto al lienzo, con su nombre, y se llama como él. El de un
// mueble trae «Mover», «Girar» (no lo de pared) y «Guardar» (no la puerta);
// el de un gachamon, «Mover» (sólo en el dibujo) y «Acariciar». Va centrado
// sobre lo elegido y nunca fuera de la pieza: si arriba no cabe entero, se
// queda pegado arriba aunque tape algo; si así taparía más de la mitad, va
// debajo. Escape deja de elegirlo.
//
// `menuDeLaPieza({lienzo, mover, girar, guardar, moverGachamon, acariciar,
// soltarElegido, signal})` arma su nodo una vez (`nodo`, escondido) y lo deja
// al día con lo que le pasa la pantalla: no habla con el servidor, ni decide
// qué está elegido ni si el menú va abierto. `lienzo` es el lienzo de la
// pieza, junto al que va; lo demás, lo que hace la pantalla con cada botón y
// con Escape: `mover(boton)` y `moverGachamon(boton)`, lo elegido, desde ese
// botón; `girar(id, boton)`, `guardar(id, boton)` y `acariciar(id, boton)`,
// ese mueble o ese gachamon, desde ese botón; `soltarElegido()`, que deje de
// estar elegido. Lo deja de oír la `signal` de la pantalla, al dejarla.
//
// `pintar({puesto, caja})` o `pintar({gachamon, caja})` lo abre sobre ese
// mueble puesto o ese gachamon, cuya caja (`caja`, donde se pinta) le dice
// dónde ponerse; sólo se rehace si cambió para qué está hecho. `cerrar()` lo
// esconde, y `contiene(nodo)` dice si ese nodo está dentro (el foco que estaba
// en un menú que se cierra lo lleva la pantalla a otro sitio). Todo texto
// entra por `el` o por `textContent`.

import { el } from './dom.js';

// Lo de pared no se gira.
const PARED = 'pared';
// Lo que el menú deja hasta el mueble y hasta el borde de la pieza, en píxeles.
const MARGEN_DEL_MENU = 6;

export function menuDeLaPieza({
  lienzo, mover, girar, guardar, moverGachamon, acariciar, soltarElegido, signal,
}) {
  const nodo = el('div', { class: 'menu-de-la-pieza', role: 'group', hidden: true });

  // Para qué está hecho el menú («mueble 21», «gachamon 8»), o `null`.
  let menuDe = null;

  function botonDelMenu(icono, texto, alTocar) {
    const boton = icono
      ? el('button', { type: 'button', class: 'boton boton-chico' }, el('span', { 'aria-hidden': 'true' }, icono), texto)
      : el('button', { type: 'button', class: 'boton boton-chico' }, texto);
    boton.addEventListener('click', () => alTocar(boton), { signal });
    return boton;
  }

  function hacerElMenu(puesto) {
    const botones = [botonDelMenu('✋', 'Mover', mover)];
    // Lo de pared no se gira; la puerta no se guarda.
    if (puesto.capa !== PARED) botones.push(botonDelMenu('🔄', 'Girar', (boton) => girar(puesto.id, boton)));
    if (!puesto.puerta) botones.push(botonDelMenu('📦', 'Guardar', (boton) => guardar(puesto.id, boton)));
    nodo.replaceChildren(el('p', { class: 'menu-nombre' }, puesto.nombre), el('div', { class: 'menu-botones' }, botones));
    nodo.setAttribute('aria-label', puesto.nombre);
    menuDe = `mueble ${puesto.id}`;
  }

  // El de un gachamon: moverlo (sólo en el dibujo) y acariciarlo.
  function hacerElMenuDelGachamon(g) {
    const botones = [
      botonDelMenu('✋', 'Mover', moverGachamon),
      botonDelMenu(null, 'Acariciar', (boton) => acariciar(g.id, boton)),
    ];
    nodo.replaceChildren(el('p', { class: 'menu-nombre' }, g.nombre), el('div', { class: 'menu-botones' }, botones));
    nodo.setAttribute('aria-label', g.nombre);
    menuDe = `gachamon ${g.id}`;
  }

  // Sobre lo elegido (`caja`, donde se pinta), centrado, y nunca fuera de la
  // pieza. Si arriba no cabe entero, se queda pegado arriba aunque tape algo;
  // si así taparía más de la mitad, va debajo.
  function colocarElMenu(caja) {
    const lado = lienzo.getBoundingClientRect();
    const ancho = nodo.offsetWidth || 0;
    const alto = nodo.offsetHeight || 0;
    const izquierda = Math.min(Math.max(caja.x + caja.ancho / 2, ancho / 2 + MARGEN_DEL_MENU),
      lado.width - ancho / 2 - MARGEN_DEL_MENU);
    // `top` es el borde de abajo del menú.
    let abajo = caja.y - MARGEN_DEL_MENU;
    const pegadoArriba = alto + MARGEN_DEL_MENU;
    if (abajo < pegadoArriba) {
      abajo = pegadoArriba - abajo > caja.alto / 2 ? caja.y + caja.alto + MARGEN_DEL_MENU + alto : pegadoArriba;
    }
    abajo = Math.max(Math.min(abajo, lado.height - MARGEN_DEL_MENU), pegadoArriba);
    nodo.style.left = `${izquierda}px`;
    nodo.style.top = `${abajo}px`;
  }

  // Abierto sobre ese mueble puesto o ese gachamon.
  function pintar({ puesto = null, gachamon = null, caja }) {
    if (puesto) {
      if (menuDe !== `mueble ${puesto.id}`) hacerElMenu(puesto);
    } else if (menuDe !== `gachamon ${gachamon.id}`) {
      hacerElMenuDelGachamon(gachamon);
    }
    nodo.hidden = false;
    colocarElMenu(caja);
  }

  function cerrar() {
    nodo.hidden = true;
    menuDe = null;
  }

  const contiene = (otro) => nodo.contains(otro);

  nodo.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape') soltarElegido();
  }, { signal });

  return { nodo, pintar, cerrar, contiene };
}
