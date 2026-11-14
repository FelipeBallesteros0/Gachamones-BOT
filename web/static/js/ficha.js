// La ficha completa del gachamon activo: quién es (retrato, nombre y título,
// especie, etapa y nivel, género, carácter y sombrero), su experiencia, sus
// cuatro estadísticas con el efecto que tengan encima y las medallas, las suyas
// y las tuyas. De aquí se abre el ropero.
//
// `ficha(contenedor, estado, seguir)` pinta la pantalla y pide la ficha
// (`GET ficha`). Las reglas son del servidor: cada número, qué medallas hay,
// cuáles tienes y cuánto llevas; aquí se pinta lo que dice. Mirar no cambia
// nada, así que no se manda nada. Sin sesión o sin gachamon (un 409) se vuelve
// a decidir la pantalla con `seguir`, como en la mochila; y también si la ficha
// que llega es de otro gachamon que el del estado (cambió en otra pestaña o en
// Discord): el ropero viste al que enseña la pantalla. Una respuesta que llega
// cuando ya se dejó la pantalla no pinta. La cabecera y la espera son las de
// `articulos.js`. Todo texto entra por `el` o por `textContent`.

import { olvidarLasQueFaltan } from './arte.js';
import { GEMAS, cabeceraConSaldos, linea, listaQueSePide } from './articulos.js';
import { el } from './dom.js';

const CARGANDO = 'Cargando la ficha…';

// Cómo se ve y cómo se dice el género.
const GENEROS = {
  macho: { simbolo: '♂', nombre: 'Macho' },
  hembra: { simbolo: '♀', nombre: 'Hembra' },
};

// Las palabras que pone la propia pantalla concuerdan con el gachamon:
// masculino salvo para una hembra.
function segun(genero, masculino, femenino) {
  return genero === 'hembra' ? femenino : masculino;
}

// El carácter llega como se dice en una frase («tímido»); aquí va solo, tras el
// género: «♂ Macho · Tímido».
function conMayuscula(texto) {
  const palabra = String(texto || '');
  return palabra.charAt(0).toUpperCase() + palabra.slice(1);
}

// «+3 · 4 min»: lo que suma y cuánto le queda, en minutos redondeados hacia arriba.
function textoDelEfecto({ bonus, segundos }) {
  return `+${bonus} · ${Math.max(1, Math.ceil((Number(segundos) || 0) / 60))} min`;
}

export function ficha(contenedor, estado, seguir) {
  // El arte que no cargó en otra pantalla se pide de nuevo.
  olvidarLasQueFaltan();
  let vivo = true;

  // Deja la ficha y que se decida otra pantalla: con lo que se le pase, o
  // preguntando todo otra vez.
  function irse(estadoNuevo, opciones) {
    vivo = false;
    seguir(estadoNuevo, opciones);
  }

  // Si la pantalla ya no está en la página (se pintó otra), ya no pinta.
  function sigueAqui() {
    if (vivo && !cuerpo.isConnected) vivo = false;
    return vivo;
  }

  // --- la pantalla -------------------------------------------------------------------

  const { cabecera, titulo, ponerSaldos } = cabeceraConSaldos('📋', 'Ficha');
  // Hasta que llega la ficha no hay ficha: hay una frase.
  const espera = el('div', { class: 'espera-tienda' });
  const contenido = el('div', { class: 'ficha-completa', hidden: true });
  const volver = el('button', { type: 'button', class: 'boton boton-volver' }, 'Volver');
  volver.addEventListener('click', () => irse());
  const cuerpo = el('div', { class: 'cuerpo cuerpo-tienda cuerpo-ficha' }, espera, contenido, volver);
  contenedor.append(cabecera, cuerpo);

  // --- quién es ------------------------------------------------------------------------

  // El retrato no se lee: su nombre va al lado, en el título.
  function retratoDe(g) {
    const sinRetrato = el('span', { class: 'retrato-sin', 'aria-hidden': 'true', hidden: true }, g.emoji);
    const retrato = el('img', {
      class: 'retrato-ficha', src: g.retrato, alt: '', draggable: 'false',
    });
    retrato.addEventListener('error', () => {
      retrato.hidden = true;
      sinRetrato.hidden = false;
    });
    return el('div', { class: 'ficha-retrato' }, retrato, sinRetrato);
  }

  // «Experiencia: 40 de 100 para el nivel 3», con su barra.
  function experiencia({ nivel, xp, para_subir: paraSubir }) {
    const lleno = paraSubir > 0 ? Math.min(100, Math.max(0, (xp / paraSubir) * 100)) : 0;
    const relleno = el('span', { class: 'medidor-relleno' });
    relleno.style.width = `${lleno}%`;
    return el('div', { class: 'ficha-experiencia' },
      linea(`Experiencia: ${xp} de ${paraSubir} para el nivel ${nivel + 1}`, 'ficha-experiencia-texto'),
      el('span', { class: 'medidor-pista', 'aria-hidden': 'true' }, relleno));
  }

  // El ropero se abre desde arriba, con lo que lleva puesto: a la vista sin
  // tener que bajar por las medallas.
  function botonAlRopero() {
    const boton = el('button', { type: 'button', class: 'boton boton-chico principal boton-ropero' },
      el('span', { 'aria-hidden': 'true' }, '👒'), 'Ropero');
    boton.addEventListener('click', () => irse(estado, { vista: 'ropero' }));
    return boton;
  }

  // Con sombrero, «Ropero» va justo tras «Lleva …»; sin él, tras la experiencia.
  function quienEs(g, detalle) {
    const genero = Object.hasOwn(GENEROS, g.genero) ? GENEROS[g.genero] : null;
    const comoEs = el('p', { class: 'ficha-genero' },
      genero ? [el('span', { 'aria-hidden': 'true' }, `${genero.simbolo} `), `${genero.nombre} · `] : null,
      conMayuscula(detalle.caracter));
    const vestido = detalle.sombrero
      ? el('div', { class: 'ficha-vestido' }, linea(`Lleva ${detalle.sombrero}`, 'ficha-sombrero'), botonAlRopero())
      : null;
    return el('section', { class: 'ficha-quien', 'aria-labelledby': 'ficha-nombre' },
      retratoDe(g),
      el('div', { class: 'ficha-quien-texto' },
        el('h2', { class: 'ficha-nombre', id: 'ficha-nombre' },
          g.nombre, g.titulo ? el('span', { class: 'titulo-del-gachamon' }, ` ${g.titulo}`) : null),
        linea(`${g.nombre_especie} ${g.nombre_etapa} · nivel ${g.nivel}`, 'ficha-especie'),
        comoEs,
        vestido),
      experiencia(detalle.experiencia),
      vestido ? null : el('div', { class: 'ficha-al-ropero' }, botonAlRopero()));
  }

  // --- las estadísticas --------------------------------------------------------------

  function estadistica(e) {
    return el('li', { class: 'ficha-estadistica' },
      el('span', { class: 'ficha-estadistica-nombre' }, e.nombre),
      el('span', { class: 'ficha-estadistica-valor' }, String(e.valor)),
      e.efecto ? el('span', { class: 'ficha-efecto' }, textoDelEfecto(e.efecto)) : null);
  }

  function estadisticas(lista) {
    return el('section', { class: 'ficha-seccion', 'aria-labelledby': 'ficha-estadisticas' },
      el('h2', { class: 'ficha-subtitulo', id: 'ficha-estadisticas' }, 'Estadísticas'),
      el('ul', { class: 'ficha-estadisticas' }, lista.map(estadistica)));
  }

  // --- las medallas ----------------------------------------------------------------------

  // Una medalla: su nombre, cómo se gana, sus gemas y, si lo trae, su progreso.
  // La conseguida lleva delante su marca, que se ve, y para el lector, que la tiene.
  function medalla(m) {
    return el('li', { class: m.tiene ? 'ficha-medalla conseguida' : 'ficha-medalla' },
      el('span', { class: 'ficha-medalla-marca', 'aria-hidden': 'true' }, m.tiene ? '✓' : ''),
      el('div', { class: 'ficha-medalla-texto' },
        el('p', { class: 'ficha-medalla-nombre' },
          m.nombre, m.tiene ? el('span', { class: 'solo-lector' }, ', conseguida') : null),
        linea(m.como, 'ficha-medalla-como')),
      el('div', { class: 'ficha-medalla-lado' },
        el('span', { class: 'ficha-medalla-gemas' },
          el('span', { 'aria-hidden': 'true' }, `${GEMAS.simbolo} ${m.gemas}`),
          el('span', { class: 'solo-lector' }, GEMAS.cuantas(m.gemas))),
        m.progreso
          ? el('span', { class: 'ficha-medalla-progreso' }, `${m.progreso.hecho}/${m.progreso.meta}`)
          : null));
  }

  function medallas(g, { del_gachamon: delGachamon, tuyas }) {
    return el('section', { class: 'ficha-seccion ficha-de-medallas', 'aria-labelledby': 'ficha-medallas' },
      el('h2', { class: 'ficha-subtitulo', id: 'ficha-medallas' }, `Medallas de ${g.nombre}`),
      el('ul', { class: 'ficha-medallas' }, delGachamon.map(medalla)),
      el('h2', { class: 'ficha-subtitulo' }, 'Tuyas'),
      el('ul', { class: 'ficha-medallas' }, tuyas.map(medalla)),
      linea(`Las de ${g.nombre} se van con ${segun(g.genero, 'él', 'ella')} si se muere; las tuyas se quedan.`,
        'ficha-pie'));
  }

  // --- lo que llega -----------------------------------------------------------------------

  const laFicha = listaQueSePide({
    ruta: 'ficha',
    espera,
    lista: contenido,
    cargando: CARGANDO,
    titulo,
    sigueAqui,
    irse: () => irse(),
    alLlegar(leida, trasReintentar) {
      if (!estado.gachamon || leida.gachamon.id !== estado.gachamon.id) {
        irse();
        return;
      }
      ponerSaldos(leida.saldos);
      const g = leida.gachamon;
      contenido.replaceChildren(
        el('div', { class: 'ficha-columna' }, quienEs(g, leida.detalle), estadisticas(leida.detalle.estadisticas)),
        medallas(g, leida.medallas),
      );
      if (trasReintentar) titulo.focus({ preventScroll: true });
    },
  });

  ponerSaldos(estado.saldos);
  return laFicha.cargar();
}
