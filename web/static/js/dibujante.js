// La página del dibujante (`/monsteropolis_dibujante/`): las piezas del arte por
// grupos, cada una con su imagen de ahora, su nombre, lo que tiene que medir y
// si se ve el recuadro provisional o una imagen subida (por quién y cuándo).
// Desde cada pieza se sube un PNG, se vuelve a la anterior o al provisional y se
// mira su historial; cada una baja su provisional y, si la tiene, su imagen subida,
// y arriba se descarga todo lo subido o todos los provisionales. Las criaturas (miles
// de capas) van plegadas por especie y se piden al abrirlas. Sólo la ven el dueño y
// el dibujante: a los demás, el servidor les contesta que no existe.
//
// Es una herramienta para dos personas: clara antes que bonita. Qué vale, qué
// medida se pide y qué queda puesto lo decide el servidor; aquí sólo se enseña.

import { urlDeArte } from './arte.js';
import { el } from './dom.js';

const BASE = '/monsteropolis_dibujante/api/';

// Las mismas frases que `api.js` para cuando no llega una respuesta del juego.
const SIN_RED = 'No hay conexión con el juego. Revisa tu internet y vuelve a intentarlo.';
const SIN_RESPUESTA = 'El juego no contestó. Vuelve a intentarlo en un momento.';

const LISTO = 'Listo: ya se ve en el juego.';
const BOTONES = {
  subir: 'Subir',
  historial: 'Historial',
  anterior: 'Volver a la anterior',
  provisional: 'Volver al provisional',
};

// Lo que contesta la api del dibujante; si no sale bien, lanza `{mensaje}` con
// la frase del servidor o, si la respuesta no es del juego, la de siempre.
async function pedir(metodo, ruta, cuerpo, tipo) {
  const opciones = { method: metodo, headers: {}, credentials: 'same-origin' };
  if (cuerpo !== undefined) {
    opciones.headers['Content-Type'] = tipo;
    opciones.body = cuerpo;
  }
  if (metodo !== 'GET') opciones.headers['X-Gachamon'] = '1';
  let respuesta;
  try {
    respuesta = await fetch(BASE + ruta, opciones);
  } catch {
    throw { mensaje: SIN_RED };
  }
  let datos = null;
  try {
    datos = await respuesta.json();
  } catch {
    datos = null;
  }
  if (respuesta.ok && datos !== null && typeof datos === 'object') return datos;
  const detalle = datos && typeof datos.detail === 'object' ? datos.detail : null;
  throw { mensaje: detalle && typeof detalle.mensaje === 'string' ? detalle.mensaje : SIN_RESPUESTA };
}

// --- las frases -----------------------------------------------------------------------

const dosCifras = (n) => String(n).padStart(2, '0');

// «20/11/2026 15:04», en la hora de quien mira.
export function fecha(iso) {
  const cuando = new Date(iso);
  if (Number.isNaN(cuando.getTime())) return String(iso);
  return `${dosCifras(cuando.getDate())}/${dosCifras(cuando.getMonth() + 1)}/${cuando.getFullYear()} `
    + `${dosCifras(cuando.getHours())}:${dosCifras(cuando.getMinutes())}`;
}

// Lo que tiene que medir el PNG: una sola medida.
export function medidaDe(pieza) {
  return `${pieza.ancho} × ${pieza.alto} px`;
}

export function estadoDe(pieza) {
  if (!pieza.subida) return 'Provisional';
  return `Subida por ${pieza.subida.quien} el ${fecha(pieza.subida.cuando)}`;
}

// Lo que tiene puesto con una medida que el contrato ya no pide: no se sirve.
export function avisoDeMedida(pieza) {
  const medida = pieza.medida_cambiada;
  if (!medida) return null;
  return `Lo subido mide ${medida.ancho} × ${medida.alto} px y este lugar pide ${pieza.ancho} × ${pieza.alto} px: hay que volver a subirlo.`;
}

// Un renglón del historial: lo que se hizo (con el nombre de su botón), quién, cuándo y lo que mide.
export function renglonDelHistorial(renglon) {
  const partes = [BOTONES[renglon.accion] || renglon.accion, renglon.quien, fecha(renglon.cuando)];
  if (renglon.ancho && renglon.alto) partes.push(`${renglon.ancho} × ${renglon.alto} px`);
  return partes.join(' · ');
}

const DESCARGAS = {
  provisional: 'Descargar el provisional',
  subida: 'Descargar la imagen subida',
  provisionales: 'Descargar los provisionales',
};

// El nombre con que baja una pieza: su ruta, con guiones en vez de barras.
const nombreDe = (prefijo, ruta) => `${prefijo}-${ruta.replaceAll('/', '-')}`;

// Lo que se ve de un lugar: lo subido; si no, lo que lo cubre; si no, su provisional chico; si no, el del juego.
function imagenDe(pieza) {
  if (pieza.subida) return pieza.subida.direccion;
  if (pieza.cubierta) return pieza.cubierta.direccion;
  return pieza.miniatura || urlDeArte(pieza.ruta);
}

// Lo que se le pide al lugar de una criatura que no sea de su forma (lo comparten otras casillas).
const esCompartida = (pieza) => Boolean(pieza.criatura) && pieza.criatura.nivel !== 'forma';

// Lo que se pide dibujar: ni lo hecho, ni lo cubierto, ni lo que comparten otras casillas.
const sePide = (pieza) => !pieza.subida && !pieza.cubierta && !esCompartida(pieza);

const ORIENTACIONES = {
  se: 'se · de frente, hacia abajo a la derecha',
  so: 'so · de frente, hacia abajo a la izquierda',
  no: 'no · de espaldas, hacia arriba a la izquierda',
  ne: 'ne · de espaldas, hacia arriba a la derecha',
};

const ETAPAS = [
  ['bebe', 'Cría'], ['nino', 'Niño'], ['adolescente', 'Adolescente'], ['adulto', 'Adulto'],
  ['adulto_grande', 'Adulto grande'],
];

const CUBIERTAS = { especie: 'Usa la de toda la especie.', comun: 'Usa la común.' };

const NOTAS_DE_ESTADO = {
  encendido: 'El dibujo de siempre es el apagado; éste es el encendido.',
  atravesable: 'La de siempre es la sólida; ésta es la que se puede atravesar.',
};

const NOTAS_DE_OBJETO = {
  mayordomo: 'Alto como tu avatar: unos 717 px del original, de pie en el centro de la casilla.',
  balcon: 'La tira de 4 × 1 casillas que queda por fuera de la pared, con su baranda. '
    + 'Como lo de pared: «se» va en la pared izquierda y «so», en la derecha.',
};

const NOTAS_DE_CRIATURAS = [
  'Cada capa mide 1024 × 1024 y se apila con las demás de su etapa en el mismo lienzo. De espaldas no lleva cara.',
  'El provisional es la capa de frente de hoy, ampliada: dice dónde va y de qué tamaño, no cómo se ve de lado ni de espaldas.',
];

// Las notas de un lugar, según su estado y su objeto.
function notasDe(pieza) {
  const notas = [];
  if (NOTAS_DE_ESTADO[pieza.estado]) notas.push(NOTAS_DE_ESTADO[pieza.estado]);
  if (NOTAS_DE_OBJETO[pieza.objeto]) notas.push(NOTAS_DE_OBJETO[pieza.objeto]);
  return notas;
}

// El título de la tarjeta de una capa de criatura.
function tituloDeCapa(criatura) {
  const orientacion = ORIENTACIONES[criatura.orientacion] || criatura.orientacion;
  if (criatura.capa === 'cuerpo') return `Cuerpo · ${orientacion}`;
  if (criatura.capa === 'cara') return `Cara ${criatura.cual} · ${orientacion}`;
  return `${criatura.nombre_del_sombrero || criatura.cual} · ${orientacion}`;
}

const resumenDe = (grupo) => `${grupo.nombre} · ${grupo.hechas} de ${grupo.total}`;

// --- una pieza ------------------------------------------------------------------------

let historiales = 0;

// La tarjeta de una pieza. Sus botones no se rehacen nunca (el foco se queda donde
// estaba): lo que cambia se escribe en su sitio. Devuelve el nodo, su vista de ahora y
// cómo ponerle otra. `contexto.especie` es el nombre de la especie de una capa de criatura
// y `contexto.alCambiar(antes, ahora)` avisa de lo que salió bien.
function tarjeta(pieza, familia, contexto = {}) {
  let actual = pieza;
  let ocupada = false;
  historiales += 1;

  const imagen = el('img', {
    class: familia === 'pieza' || familia === 'criaturas' ? 'dib-imagen' : 'dib-imagen dib-cuadros',
    src: imagenDe(pieza), alt: pieza.ruta, loading: 'lazy', decoding: 'async',
  });
  const estado = el('p', { class: 'dib-estado' });
  const cambiada = el('p', { class: 'dib-cambiada' });
  const cubierta = el('p', { class: 'dib-cubierta' });
  const aviso = el('p', { class: 'dib-aviso', role: 'status' });
  const lista = el('ol', { class: 'dib-historial', id: `dib-historial-${historiales}`, hidden: true });
  // Se abre con «Subir»: no se ve ni se enfoca, pero no va con `hidden`, que en algún
  // navegador de teléfono no deja abrir el selector desde el botón.
  const archivo = el('input', {
    type: 'file', accept: 'image/png', class: 'dib-archivo', tabindex: '-1', 'aria-hidden': 'true',
    onchange: alElegir,
  });

  const boton = (texto, alTocar, extra = {}) => el(
    'button', { type: 'button', class: 'boton boton-chico', onclick: alTocar, ...extra }, texto,
  );
  const subir = boton(BOTONES.subir, () => { if (!ocupada) archivo.click(); });
  const verHistorial = boton(BOTONES.historial, alternarHistorial, {
    'aria-expanded': 'false', 'aria-controls': lista.getAttribute('id'),
  });
  const anterior = boton(BOTONES.anterior, () => volver('anterior', anterior));
  const provisional = boton(BOTONES.provisional, () => volver('provisional', provisional));
  const queMandan = [subir, anterior, provisional];
  // Descargar no manda nada: son enlaces de verdad, con el aspecto de los botones.
  const bajarProvisional = el('a', {
    class: 'boton boton-chico',
    href: `${BASE}provisional?ruta=${encodeURIComponent(pieza.ruta)}`,
    download: nombreDe('provisional', pieza.ruta),
  }, DESCARGAS.provisional);
  const bajarSubida = el('a', { class: 'boton boton-chico', download: nombreDe('subida', pieza.ruta) },
    DESCARGAS.subida);

  function avisar(texto, esError) {
    aviso.textContent = texto;
    aviso.classList.toggle('es-error', esError);
  }

  function pintar() {
    imagen.setAttribute('src', imagenDe(actual));
    estado.textContent = estadoDe(actual);
    const medida = avisoDeMedida(actual);
    cambiada.textContent = medida || '';
    cambiada.hidden = !medida;
    cubierta.textContent = actual.cubierta ? CUBIERTAS[actual.cubierta.por] : '';
    cubierta.hidden = !actual.cubierta;
    bajarSubida.hidden = !actual.subida;
    if (actual.subida) bajarSubida.setAttribute('href', actual.subida.original);
    else bajarSubida.removeAttribute('href');
  }

  // Mientras espera al servidor, lo que manda algo no se puede usar (sigue enfocable).
  function esperando(pulsado) {
    ocupada = pulsado !== null;
    for (const b of queMandan) {
      if (ocupada) b.setAttribute('aria-disabled', 'true');
      else b.removeAttribute('aria-disabled');
      if (b === pulsado) b.setAttribute('aria-busy', 'true');
      else b.removeAttribute('aria-busy');
    }
  }

  async function cambiar(pulsado, peticion, alSalirBien) {
    esperando(pulsado);
    try {
      const antes = actual;
      actual = await peticion();
      pintar();
      avisar(alSalirBien(), false);
      // Lo de fuera se entera sin esperarlo: lo que salió bien no depende de ello.
      if (contexto.alCambiar) contexto.alCambiar(antes, actual);
      // Lo que salió bien sigue dicho aunque releer el historial falle.
      if (!lista.hidden) await leerHistorial({ avisarSiFalla: false });
    } catch (error) {
      avisar(error && error.mensaje ? error.mensaje : SIN_RESPUESTA, true);
    } finally {
      esperando(null);
    }
  }

  async function alElegir() {
    const elegido = archivo.files && archivo.files[0];
    // Así se puede volver a elegir el mismo archivo.
    archivo.value = '';
    if (!elegido || ocupada) return;
    const ruta = `subir?ruta=${encodeURIComponent(actual.ruta)}`;
    await cambiar(subir, () => pedir('POST', ruta, elegido, 'image/png'), () => LISTO);
  }

  async function volver(a, pulsado) {
    if (ocupada) return;
    // Una capa de la especie o común la usan otras casillas: antes de quitarla se pregunta.
    if (esCompartida(actual)) {
      const frase = actual.criatura.nivel === 'comun'
        ? 'Esta capa la usan todas las especies que no tienen la suya. ¿Seguir?'
        : `Esta capa la usan todas las etapas de ${contexto.especie} que no tienen la suya. ¿Seguir?`;
      if (!globalThis.confirm(frase)) return;
    }
    const cuerpo = JSON.stringify({ ruta: actual.ruta, a });
    await cambiar(pulsado, () => pedir('POST', 'volver', cuerpo, 'application/json'), () => estadoDe(actual));
  }

  async function leerHistorial({ avisarSiFalla = true } = {}) {
    try {
      const { historial } = await pedir('GET', `historial?ruta=${encodeURIComponent(actual.ruta)}`);
      lista.replaceChildren(...historial.map((renglon) => {
        // El provisional no tiene imagen: su sitio queda vacío, y los renglones alineados.
        let miniatura = el('span', { class: 'dib-miniatura', 'aria-hidden': 'true' });
        if (renglon.direccion) {
          // Una imagen que ya no se guarda deja su sitio vacío, sin el dibujo roto.
          miniatura = el('img', {
            class: 'dib-miniatura', src: renglon.direccion, alt: actual.ruta, loading: 'lazy',
            onerror: () => { miniatura.classList.add('dib-sin-imagen'); },
          });
        }
        return el('li', {}, miniatura, renglonDelHistorial(renglon));
      }));
    } catch (error) {
      if (avisarSiFalla) avisar(error && error.mensaje ? error.mensaje : SIN_RESPUESTA, true);
    }
  }

  async function alternarHistorial() {
    const abrir = lista.hidden;
    lista.hidden = !abrir;
    verHistorial.setAttribute('aria-expanded', String(abrir));
    if (abrir) await leerHistorial();
  }

  pintar();
  const nodo = el('li', { class: 'dib-pieza' },
    el('div', { class: 'dib-marco' }, imagen),
    el('p', { class: 'dib-ruta' }, pieza.ruta),
    pieza.criatura ? el('p', { class: 'dib-titulo' }, tituloDeCapa(pieza.criatura)) : null,
    el('p', { class: 'dib-medida' }, medidaDe(pieza)),
    notasDe(pieza).map((nota) => el('p', { class: 'dib-nota' }, nota)),
    estado, cambiada, cubierta,
    el('div', { class: 'dib-botones' }, subir, verHistorial, anterior, provisional,
      bajarProvisional, bajarSubida),
    archivo, aviso, lista);
  return {
    nodo,
    vista: () => actual,
    poner(vista) {
      actual = vista;
      pintar();
    },
  };
}

// --- las criaturas --------------------------------------------------------------------

const enlaceDeDescarga = (texto, href) => el('a', { class: 'boton boton-chico', href, download: true }, texto);

// Una sección plegada, cerrada y vacía: su contenido se arma la primera vez que se abre.
function plegado(titulo, armar, clase = 'dib-etapa') {
  let armado = false;
  const cuerpo = el('div', { class: 'dib-capas' });
  const nodo = el('details', {
    class: clase,
    ontoggle: () => {
      if (armado || nodo.getAttribute('open') === null) return;
      armado = true;
      armar(cuerpo);
    },
  }, el('summary', {}, titulo), cuerpo);
  return nodo;
}

// --- la página ------------------------------------------------------------------------

export async function montar(raiz) {
  const titulo = el('h1', {}, 'Arte de Criópolis');
  const estado = el('p', { class: 'cargando', role: 'status' }, 'Cargando…');
  raiz.replaceChildren(titulo, estado);
  let datos;
  try {
    datos = await pedir('GET', 'piezas');
  } catch (error) {
    estado.textContent = error.mensaje;
    estado.classList.add('es-error');
    return;
  }

  // Sólo se filtra al tocar el filtro: lo que se acaba de subir no se esfuma de
  // las manos de quien lo subió. Lo que se arma después nace ya filtrado.
  const filtro = el('input', { type: 'checkbox', onchange: () => refiltrar() });
  const escondida = (vista) => filtro.checked && !sePide(vista);

  // Los grupos que no son criaturas: sus tarjetas, armadas de entrada.
  const grupos = datos.grupos.filter((g) => g.familia !== 'criaturas').map((grupo) => {
    const resumen = el('summary', {}, resumenDe(grupo));
    const estadoDelGrupo = { ...grupo };
    const tarjetas = grupo.piezas.map((pieza) => tarjeta(pieza, grupo.familia, {
      // Lo hecho de un grupo sale de lo que cambia aquí: la cuenta del servidor, al día.
      alCambiar: (antes, ahora) => {
        estadoDelGrupo.hechas += Number(Boolean(ahora.subida)) - Number(Boolean(antes.subida));
        resumen.textContent = resumenDe(estadoDelGrupo);
      },
    }));
    const nodo = el('details', { class: 'dib-grupo' }, resumen,
      el('ul', { class: 'dib-piezas' }, tarjetas.map((t) => t.nodo)));
    return { nodo, tarjetas };
  });

  // Las especies y las capas comunes: plegadas, sin tarjetas hasta abrirlas.
  const especies = datos.grupos.filter((g) => g.familia === 'criaturas').map((grupo) => {
    const esp = {
      grupo: { ...grupo }, cargada: false, pidiendo: false, pedidas: 0,
      vistas: new Map(), tarjetas: new Map(), secciones: [],
    };
    esp.resumen = el('summary', {}, resumenDe(esp.grupo));
    esp.contenido = el('div', { class: 'dib-contenido' });
    const clave = encodeURIComponent(grupo.clave);
    esp.nodo = el('details', { class: 'dib-grupo dib-especie', ontoggle: () => alAbrir(esp) },
      esp.resumen,
      el('div', { class: 'dib-especie-cuerpo' },
        el('div', { class: 'dib-descargas' },
          enlaceDeDescarga(`Descargar lo subido de ${grupo.nombre}`, `${BASE}copia.zip?grupo=${clave}`),
          enlaceDeDescarga(`Descargar los provisionales de ${grupo.nombre}`, `${BASE}provisionales.zip?grupo=${clave}`)),
        esp.contenido));
    return esp;
  });

  // Un grupo recién llegado de `piezas?grupo=…`: sus números y las vistas de lo ya armado.
  function ponerAlDia(esp, g) {
    esp.grupo = { ...g };
    esp.resumen.textContent = resumenDe(esp.grupo);
    for (const vista of g.piezas) {
      esp.vistas.set(vista.ruta, vista);
      const armada = esp.tarjetas.get(vista.ruta);
      if (armada) armada.poner(vista);
    }
  }

  async function traer(esp) {
    const { grupos: recibidos } = await pedir('GET', `piezas?grupo=${encodeURIComponent(esp.grupo.clave)}`);
    return recibidos[0];
  }

  // Cada petición que trae los números de una especie lleva el suyo: dos cambios seguidos
  // pueden contestar en desorden, y sólo vale la última que se pidió.
  const numerar = (esp) => {
    esp.pedidas += 1;
    return esp.pedidas;
  };

  // Una especie abierta vuelve a contar sus hechas y sus casillas cubiertas.
  async function refrescar(esp) {
    const numero = numerar(esp);
    try {
      const recibido = await traer(esp);
      if (numero === esp.pedidas) ponerAlDia(esp, recibido);
    } catch {
      // Lo que se cambió salió bien; los números se arreglan al volver a abrir la página.
    }
  }

  // Las especies sin abrir sólo tienen su resumen: lo ponen al día con la lista general, que
  // trae `hechas` y `total` de cada grupo.
  async function refrescarLasCerradas() {
    const cerradas = especies.filter((esp) => !esp.cargada).map((esp) => [esp, numerar(esp)]);
    if (!cerradas.length) return;
    try {
      const { grupos: recibidos } = await pedir('GET', 'piezas');
      for (const [esp, numero] of cerradas) {
        const g = recibidos.find((r) => r.clave === esp.grupo.clave);
        if (!g || numero !== esp.pedidas) continue;
        esp.grupo = { ...esp.grupo, hechas: g.hechas, total: g.total };
        esp.resumen.textContent = resumenDe(esp.grupo);
      }
    } catch {
      // Igual que arriba: lo que se cambió salió bien.
    }
  }

  // Lo que se cambió en una capa: la especie vuelve a contar sus hechas y sus casillas cubiertas,
  // y una capa común puede cambiar lo hecho de todas: las abiertas se vuelven a pedir enteras y
  // las demás, su resumen.
  async function alCambiarUnaCapa(esp, antes) {
    if (!antes.criatura || antes.criatura.nivel !== 'comun') {
      await refrescar(esp);
      return;
    }
    await Promise.all([...especies.filter((otra) => otra.cargada).map(refrescar), refrescarLasCerradas()]);
  }

  function lista(esp, rutas, familia) {
    return el('ul', { class: 'dib-piezas' }, rutas.map((ruta) => {
      const armada = tarjeta(esp.vistas.get(ruta), familia, {
        especie: esp.grupo.nombre,
        alCambiar: (antes, ahora) => {
          esp.vistas.set(ahora.ruta, ahora);
          alCambiarUnaCapa(esp, antes);
        },
      });
      armada.nodo.hidden = escondida(armada.vista());
      esp.tarjetas.set(ruta, armada);
      return armada.nodo;
    }));
  }

  // Una sección plegada que se acaba de armar: con el filtro puesto, nace filtrada, y su especie
  // se vuelve a mirar en ese momento (sin plegados abiertos y vacíos).
  function seccionNueva(esp, nodo, rutas) {
    const seccion = { nodo, rutas };
    esp.secciones.push(seccion);
    filtrarSeccion(esp, seccion);
    filtrarEspecie(esp);
    return nodo;
  }

  // El cuerpo, las caras y los sombreros (plegados) de una lista de lugares.
  function capas(esp, rutas, cuerpo) {
    const de = (capa) => rutas.filter((ruta) => esp.vistas.get(ruta).criatura.capa === capa);
    for (const [capa, nombre] of [['cuerpo', 'Cuerpo'], ['cara', 'Caras']]) {
      const delas = de(capa);
      if (delas.length) cuerpo.append(el('h3', {}, nombre), lista(esp, delas, 'criaturas'));
    }
    const sombreros = de('sombrero');
    if (sombreros.length) {
      cuerpo.append(seccionNueva(esp,
        plegado('Sombreros', (dentro) => dentro.append(lista(esp, sombreros, 'criaturas')), 'dib-sombreros'),
        sombreros));
    }
  }

  function armarEspecie(esp) {
    const rutas = [...esp.vistas.keys()];
    const criatura = (ruta) => esp.vistas.get(ruta).criatura;
    const notas = NOTAS_DE_CRIATURAS.map((nota) => el('p', { class: 'dib-nota' }, nota));
    if (esp.grupo.clave === 'criaturas/comun') {
      const cuerpo = el('div', { class: 'dib-capas' });
      capas(esp, rutas, cuerpo);
      esp.contenido.replaceChildren(...notas, cuerpo);
      return;
    }
    const secciones = ETAPAS.map(([etapa, nombre]) => [nombre, rutas.filter((r) => criatura(r).nivel === 'forma'
      && criatura(r).etapa === etapa)]);
    secciones.push([`Para todas las etapas de ${esp.grupo.nombre}`, rutas.filter((r) => criatura(r).nivel === 'especie')]);
    esp.contenido.replaceChildren(...notas, ...secciones.filter(([, delas]) => delas.length).map(
      ([nombre, delas]) => seccionNueva(esp, plegado(nombre, (cuerpo) => capas(esp, delas, cuerpo)), delas),
    ));
  }

  async function alAbrir(esp) {
    if (esp.nodo.getAttribute('open') === null || esp.cargada || esp.pidiendo) return;
    esp.pidiendo = true;
    esp.contenido.replaceChildren(el('p', { class: 'cargando', role: 'status' }, 'Cargando las capas…'));
    try {
      const numero = numerar(esp);
      const recibido = await traer(esp);
      ponerAlDia(esp, recibido);
      // Ya cargada: lo que se arma se filtra con lo que trae.
      esp.cargada = true;
      armarEspecie(esp);
      // Si mientras llegaba una capa común pidió otros números, lo armado puede ser viejo.
      if (numero !== esp.pedidas) refrescar(esp);
    } catch (error) {
      // En su sitio, con el aviso de error de la página; al volver a abrirla se vuelve a pedir.
      esp.cargada = false;
      esp.contenido.replaceChildren(el('p', { class: 'es-error', role: 'status' },
        error && error.mensaje ? error.mensaje : SIN_RESPUESTA));
    } finally {
      esp.pidiendo = false;
    }
  }

  function filtrarSeccion(esp, seccion) {
    seccion.nodo.hidden = filtro.checked && !seccion.rutas.some((r) => sePide(esp.vistas.get(r)));
  }

  // Sin abrir no se sabe qué hay dentro: se esconde si ya está todo hecho. Las capas comunes son
  // todas compartidas, que el filtro esconde: se esconden siempre, abiertas o no.
  function filtrarEspecie(esp) {
    esp.nodo.hidden = filtro.checked && (esp.grupo.clave === 'criaturas/comun' || (esp.cargada
      ? ![...esp.vistas.values()].some(sePide)
      : esp.grupo.hechas === esp.grupo.total));
  }

  function refiltrar() {
    for (const grupo of grupos) {
      for (const t of grupo.tarjetas) t.nodo.hidden = escondida(t.vista());
      grupo.nodo.hidden = grupo.tarjetas.every((t) => t.nodo.hidden);
    }
    for (const esp of especies) {
      for (const t of esp.tarjetas.values()) t.nodo.hidden = escondida(t.vista());
      for (const seccion of esp.secciones) filtrarSeccion(esp, seccion);
      filtrarEspecie(esp);
    }
  }

  raiz.replaceChildren(
    el('header', { class: 'dib-cabeza' },
      titulo,
      el('div', { class: 'dib-descargas' },
        el('a', { class: 'boton boton-chico', href: `${BASE}copia.zip`, download: true }, 'Descargar lo subido'),
        el('a', { class: 'boton boton-chico', href: `${BASE}provisionales.zip`, download: true },
          DESCARGAS.provisionales))),
    el('label', { class: 'dib-filtro' }, filtro, 'Sólo lo que falta'),
    el('div', { class: 'dib-grupos' }, grupos.map((g) => g.nodo)),
    ...(especies.length ? [el('section', { class: 'dib-criaturas' },
      el('h2', {}, 'Criaturas'),
      el('div', { class: 'dib-grupos' }, especies.map((e) => e.nodo)))] : []),
  );
}

const pagina = typeof document !== 'undefined' && typeof document.getElementById === 'function'
  ? document.getElementById('dibujante') : null;
if (pagina) montar(pagina);
