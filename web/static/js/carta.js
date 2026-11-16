// La carta del alcalde: se enseña una vez, al entrar, a quien tenga una sin
// leer (el servidor la escribe el día del cambio de la vivienda).
//
// `carta(contenedor, estado, seguir)` pinta la pantalla y pide la carta
// (`GET carta`): lo que dice —el título, las líneas y la firma— es del
// servidor, y entra como texto. «Entendido» la marca como vista
// (`POST carta/vista`) y vuelve a decidir la pantalla con `seguir`. Si la carta
// ya no está, se sigue de largo sin enseñar nada. Si al marcarla no hay
// respuesta, se dice y la carta se queda, para volver a intentarlo: no se
// pierde. Marcarla dos veces no cambia nada, así que no lleva evento. Sin
// sesión (un 401) o con un 409 se vuelve a decidir. Una respuesta que llega
// cuando ya se dejó la pantalla no pinta. La espera de la carta, su mensaje de
// error y la zona de avisos son los de `articulos.js`. Todo texto entra por
// `el` o por `textContent`.

import { pedir } from './api.js';
import {
  hayQueDecidirDeNuevo, listaQueSePide, mensajeDe, zonaDeAviso,
} from './articulos.js';
import { el } from './dom.js';

const SIN_RESPUESTA = 'No hubo respuesta. Revisa tu conexión.';

export function carta(contenedor, estado, seguir) {
  let vivo = true;
  let enCamino = false;
  const aviso = zonaDeAviso();

  // Deja la carta y que se decida otra pantalla.
  function irse() {
    vivo = false;
    aviso.parar();
    seguir();
  }

  // Si la pantalla ya no está en la página (se pintó otra), ya no pinta.
  function sigueAqui() {
    if (vivo && !cuerpo.isConnected) {
      vivo = false;
      aviso.parar();
    }
    return vivo;
  }

  const titulo = el('h1', { class: 'donde', tabindex: '-1' });
  const cabecera = el('header', { class: 'barra barra-lugar' }, titulo);
  const espera = el('div', { class: 'espera-tienda' });
  const papel = el('article', { class: 'carta', hidden: true });
  const cuerpo = el('div', { class: 'cuerpo cuerpo-carta' }, espera, papel, aviso.nodo);
  contenedor.append(cabecera, cuerpo);

  async function entendido(boton) {
    if (enCamino) return;
    enCamino = true;
    boton.setAttribute('aria-busy', 'true');
    aviso.avisar('');
    try {
      await pedir('POST', 'carta/vista');
    } catch (error) {
      if (!sigueAqui()) return;
      enCamino = false;
      boton.setAttribute('aria-busy', 'false');
      if (hayQueDecidirDeNuevo(error)) {
        irse();
        return;
      }
      aviso.avisar(error && error.clave === null ? SIN_RESPUESTA : mensajeDe(error), true);
      return;
    }
    if (!sigueAqui()) return;
    irse();
  }

  function leer({ carta: leida }) {
    // Ya no hay carta: nada que enseñar.
    if (!leida) {
      irse();
      return;
    }
    titulo.textContent = leida.titulo;
    const boton = el('button', { type: 'button', class: 'boton principal' }, 'Entendido');
    boton.addEventListener('click', () => entendido(boton));
    papel.replaceChildren(
      ...leida.lineas.map((linea) => el('p', { class: 'carta-linea' }, linea)),
      el('p', { class: 'carta-firma' }, leida.firma),
      boton,
    );
    titulo.focus({ preventScroll: true });
  }

  const laCarta = listaQueSePide({
    ruta: 'carta', espera, lista: papel, cargando: '', titulo, sigueAqui, irse, alLlegar: leer,
  });
  return laCarta.cargar();
}
