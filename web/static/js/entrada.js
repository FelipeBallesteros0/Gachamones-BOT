// Las pantallas de la entrada: desde que se abre la página hasta tener un
// gachamon con nombre.
//
// Cada una recibe el contenedor (ya vacío), `seguir` y lo que se leyó del
// servidor (`{sesion, cuenta, estado}`). `seguir()` pide que se vuelva a
// decidir la pantalla; `seguir(estado)`, lo mismo con el estado que acaba de
// devolver una acción, sin volver a preguntarlo. Todo texto entra por `el` o
// por `textContent`.

import { pedir } from './api.js';
import {
  COLORES_DE_PELO, COLORES_DE_PIEL, COLORES_DE_ROPA, dibujarAvatar, dibujarHuevo,
} from './dibujo.js';
import { el } from './dom.js';
import { cambioLaCuenta, puedeTraerDeDiscord, siguiente } from './pantallas.js';

const PREGUNTAR_CADA_MS = 3000;
const ALGO_SALIO_MAL = 'Algo salió mal. Vuelve a intentarlo.';

// --- piezas comunes ----------------------------------------------------------

export function barra(usuario) {
  return el('header', { class: 'barra' },
    el('span', { class: 'marca' }, 'Gachamon'),
    usuario ? el('span', { class: 'quien' }, usuario) : null);
}

function titulo(texto) {
  return el('h1', { tabindex: '-1' }, texto);
}

function ventana() {
  return el('span', { class: 'ventana', 'aria-hidden': 'true' });
}

function mensajeDe(error) {
  return error && typeof error.mensaje === 'string' && error.mensaje ? error.mensaje : ALGO_SALIO_MAL;
}

function avisoVacio() {
  return el('p', { class: 'error', role: 'alert', hidden: true });
}

function avisar(aviso, texto) {
  aviso.textContent = texto;
  aviso.hidden = false;
}

function callar(aviso) {
  aviso.textContent = '';
  aviso.hidden = true;
}

// Lo que ninguna pantalla espera: sin sesión se vuelve a decidir (toca entrar);
// lo demás se enseña junto al botón, que queda listo para reintentar.
async function fallo(error, aviso, seguir) {
  if (error && error.estado === 401) {
    await seguir();
    return;
  }
  avisar(aviso, mensajeDe(error));
}

// Un botón que espera al servidor no admite un segundo toque.
async function conEspera(pulsado, trabajo) {
  if (pulsado.disabled) return;
  pulsado.disabled = true;
  pulsado.classList.add('esperando');
  pulsado.setAttribute('aria-busy', 'true');
  try {
    await trabajo();
  } finally {
    pulsado.disabled = false;
    pulsado.classList.remove('esperando');
    pulsado.removeAttribute('aria-busy');
  }
}

function pausa(ms) {
  return new Promise((listo) => { setTimeout(listo, ms); });
}

function boton(texto, clase, accion) {
  const nodo = el('button', { type: 'button', class: clase }, texto);
  nodo.addEventListener('click', () => conEspera(nodo, accion));
  return nodo;
}

// --- los lienzos ---------------------------------------------------------------

// Un <canvas> de `ancho`×`alto` píxeles de pantalla, con la densidad del
// teléfono para que el dibujo no salga borroso.
function lienzo(ancho, alto, clase) {
  const densidad = Math.min(Math.max(window.devicePixelRatio || 1, 1), 3);
  return el('canvas', {
    class: clase,
    width: Math.round(ancho * densidad),
    height: Math.round(alto * densidad),
    style: `width: ${ancho}px; height: ${alto}px`,
    'aria-hidden': 'true',
  });
}

// Borra y dibuja con los pies a `pie` píxeles del borde de abajo. La escala es
// entera para que los cuadros del dibujo caigan justos sobre los píxeles.
function pintarLienzo(nodo, unidad, pie, dibujar) {
  const densidad = nodo.width / parseFloat(nodo.style.width);
  const escala = Math.max(1, Math.round(unidad * densidad));
  const ctx = nodo.getContext('2d');
  ctx.clearRect(0, 0, nodo.width, nodo.height);
  ctx.save();
  ctx.translate(Math.round(nodo.width / 2), Math.round(nodo.height - pie * densidad));
  dibujar(ctx, escala);
  ctx.restore();
}

function pintarAvatar(nodo, avatar) {
  pintarLienzo(nodo, 4, 8, (ctx, escala) => dibujarAvatar(ctx, avatar, escala));
}

function pintarHuevo(nodo, roto) {
  pintarLienzo(nodo, 4, 8, (ctx, escala) => dibujarHuevo(ctx, escala, roto));
}

// --- sesion: hay que entrar a Rowino ------------------------------------------

export function sesion(contenedor) {
  const dibujo = lienzo(112, 140, 'huevo meciendose');
  pintarHuevo(dibujo, false);
  contenedor.append(
    barra(null),
    el('div', { class: 'cuerpo' },
      el('div', { class: 'escena', 'aria-hidden': 'true' }, ventana(), dibujo),
      titulo('Tu gachamon te espera'),
      el('p', { class: 'entradilla' },
        'Cuídalo, juega con él y míralo crecer, desde el celular o el computador.'),
      el('p', {}, 'Para jugar, entra con tu cuenta de Rowino. Después, vuelve a rowino.online/gachamon.'),
      el('a', { class: 'boton principal', href: '/login' }, 'Entrar a Rowino'),
      el('p', { class: 'nota' }, '¿No tienes cuenta? ', el('a', { href: '/register' }, 'Créala en Rowino'), '.'),
    ),
  );
}

// --- bienvenida: ¿ya jugabas en Discord? ---------------------------------------

function minutosYSegundos(ms) {
  const total = Math.ceil(ms / 1000);
  const minutos = Math.floor(total / 60);
  const segundos = String(total % 60).padStart(2, '0');
  return `${minutos}:${segundos}`;
}

// Lo que se sabe de una cuenta que todavía no eligió cómo empezar.
const CUENTA_NUEVA = { estado: 'nueva', tiene_gachamones: false };

export function bienvenida(contenedor, seguir, { sesion: quien, cuenta }) {
  const zona = el('div', { class: 'zona' });
  contenedor.append(
    barra(quien.usuario),
    el('div', { class: 'cuerpo' },
      titulo(`¡Hola, ${quien.usuario}!`),
      el('p', { class: 'entradilla' }, '¿Ya jugabas a Gachamon en Discord?'),
      zona,
    ),
  );
  const pedirCodigo = pasoDelCodigo({
    mostrar: (...nodos) => zona.replaceChildren(...nodos),
    volver: () => elegir(),
    textoVolver: 'Volver a elegir',
    seguir,
    cuenta: cuenta || CUENTA_NUEVA,
  });
  elegir();

  function elegir() {
    const aviso = avisoVacio();
    const empezar = opcion('🥚', 'Empezar de cero', 'Nunca jugué, o quiero empezar de nuevo aquí.');
    const traer = opcion('💬', 'Ya jugaba en Discord', 'Trae tus gachamones con un código.');
    empezar.addEventListener('click', () => conEspera(empezar, async () => {
      callar(aviso);
      try {
        await pedir('POST', 'cuenta/empezar');
        await seguir();
      } catch (error) {
        await fallo(error, aviso, seguir);
      }
    }));
    traer.addEventListener('click', () => conEspera(traer, () => pedirCodigo(aviso)));
    zona.replaceChildren(
      el('div', { class: 'opciones' }, empezar, traer),
      el('p', { class: 'nota' },
        'Si empiezas de cero y nace tu gachamon, ya no podrás traer los de Discord.'),
      aviso,
    );
  }

  function opcion(icono, nombre, explicacion) {
    return el('button', { type: 'button', class: 'opcion' },
      el('span', { class: 'opcion-icono', 'aria-hidden': 'true' }, icono),
      el('span', { class: 'opcion-titulo' }, nombre),
      el('span', { class: 'opcion-texto' }, explicacion));
  }
}

// --- traer los de Discord: el paso del código -----------------------------------

// Pedir el código, enseñarlo con su aviso y esperar a que se escriba en
// Discord. Es uno solo para la bienvenida y para el enlace de las pantallas del
// avatar y del huevo: `mostrar(...nodos)` pone lo suyo en pantalla, y el botón
// `textoVolver` llama a `volver()`, que deja la de antes. Si mientras tanto la
// cuenta deja de ser `cuenta` (se vinculó, o cambió en otra pestaña), se vuelve
// a decidir con `seguir()`. Devuelve `pedirCodigo(aviso)`; en `aviso` se dice
// un fallo que deja reintentar.
function pasoDelCodigo({ mostrar, volver, textoVolver, seguir, cuenta }) {
  async function pedirCodigo(aviso) {
    callar(aviso);
    try {
      mostrarCodigo(await pedir('POST', 'cuenta/codigo'));
    } catch (error) {
      if (error && (error.clave === 'con_gachamones' || error.clave === 'ya_vinculada')) {
        // La cuenta ya no puede traerlos (otra pestaña, otro teléfono): se
        // explica y se deja seguir hasta donde toque.
        mostrar(
          el('p', { class: 'alerta', role: 'alert' }, error.mensaje),
          boton('Seguir', 'boton principal', () => seguir()),
        );
        return;
      }
      await fallo(error, aviso, seguir);
    }
  }

  function mostrarCodigo({ codigo, minutos }) {
    const vence = Date.now() + minutos * 60 * 1000;
    const comando = `/vincular ${codigo}`;
    const quedan = el('span', {});
    const espera = el('span', {}, 'Esperando a que lo escribas en Discord…');
    const atras = el('button', { type: 'button', class: 'boton' }, textoVolver);
    const caja = el('div', { class: 'codigo-caja' },
      el('p', { class: 'codigo-etiqueta' }, 'Tu código'),
      el('p', { class: 'codigo' }, codigo),
      el('p', {}, 'En Discord, en el servidor Robot House, escribe:'),
      el('p', { class: 'comando' }, el('code', {}, comando), botonCopiar(comando)),
      el('p', { class: 'dura' }, `Dura ${minutos} ${minutos === 1 ? 'minuto' : 'minutos'} · `, quedan),
    );
    mostrar(
      caja,
      el('div', { class: 'alerta', role: 'note' },
        el('strong', {}, 'No se lo pases a nadie. '),
        'Este código da acceso a tus gachamones: escríbelo tú, desde tu propia cuenta de Discord.'),
      el('p', { class: 'esperando-vinculo', role: 'status' },
        el('span', { class: 'pulso', 'aria-hidden': 'true' }), espera),
      atras,
    );

    let reloj = null;
    let pregunta = null;
    const sigueAqui = () => caja.isConnected;
    const parar = () => {
      clearInterval(reloj);
      clearTimeout(pregunta);
    };

    const contar = () => {
      if (!sigueAqui()) {
        parar();
        return;
      }
      const falta = vence - Date.now();
      if (falta <= 0) {
        parar();
        caducado();
        return;
      }
      quedan.textContent = `quedan ${minutosYSegundos(falta)}`;
    };

    const preguntar = async () => {
      if (!sigueAqui() || Date.now() >= vence) return;
      try {
        const ahora = await pedir('GET', 'cuenta');
        if (cambioLaCuenta(cuenta, ahora)) {
          parar();
          await seguir();
          return;
        }
        espera.textContent = 'Esperando a que lo escribas en Discord…';
      } catch (error) {
        if (error && error.estado === 401) {
          parar();
          await seguir();
          return;
        }
        espera.textContent = 'Se cortó la conexión. Sigo intentando…';
      }
      if (sigueAqui()) pregunta = setTimeout(preguntar, PREGUNTAR_CADA_MS);
    };

    atras.addEventListener('click', () => {
      parar();
      volver();
    });
    reloj = setInterval(contar, 1000);
    pregunta = setTimeout(preguntar, PREGUNTAR_CADA_MS);
    contar();
  }

  function caducado() {
    const aviso = avisoVacio();
    const otro = el('button', { type: 'button', class: 'boton principal' }, 'Pedir otro código');
    otro.addEventListener('click', () => conEspera(otro, () => pedirCodigo(aviso)));
    const atras = el('button', { type: 'button', class: 'boton' }, textoVolver);
    atras.addEventListener('click', () => volver());
    mostrar(
      el('div', { class: 'codigo-caja', role: 'status' },
        el('p', { class: 'codigo-etiqueta' }, 'Código caducado'),
        el('p', {}, 'El código dejó de servir sin que lo usaras. Pide otro cuando tengas Discord a mano.')),
      aviso,
      otro,
      atras,
    );
  }

  return pedirCodigo;
}

// El enlace discreto de las pantallas del avatar y del huevo: quien tocó
// «Empezar de cero» viniendo de Discord todavía puede traer los suyos mientras
// no le nazca nada aquí. Abre el mismo paso del código en lugar de `cuerpo`, y
// «Volver» lo deja todo como estaba (también lo que se hubiera elegido).
function enlaceADiscord(cuerpo, seguir, cuenta) {
  if (!puedeTraerDeDiscord(cuenta)) return null;
  const aviso = avisoVacio();
  const enlace = el('button', { type: 'button', class: 'enlace' },
    '¿Ya jugabas en Discord? Trae tus gachamones.');
  let antes = null;
  const pedirCodigo = pasoDelCodigo({
    mostrar: (...nodos) => {
      if (!antes) antes = [...cuerpo.childNodes];
      const cabeza = titulo('Trae tus gachamones');
      cuerpo.replaceChildren(cabeza, ...nodos);
      window.scrollTo(0, 0);
      cabeza.focus({ preventScroll: true });
    },
    volver: () => {
      cuerpo.replaceChildren(...antes);
      antes = null;
      enlace.focus();
    },
    textoVolver: 'Volver',
    seguir,
    cuenta,
  });
  enlace.addEventListener('click', () => conEspera(enlace, () => pedirCodigo(aviso)));
  return el('div', { class: 'traer' }, enlace, aviso);
}

function botonCopiar(texto) {
  if (!navigator.clipboard || !window.isSecureContext) return null;
  const nodo = el('button', { type: 'button', class: 'boton boton-chico' }, 'Copiar');
  nodo.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(texto);
      nodo.textContent = 'Copiado';
    } catch {
      nodo.textContent = 'No se pudo copiar';
    }
    setTimeout(() => { nodo.textContent = 'Copiar'; }, 2000);
  });
  return nodo;
}

// --- avatar: cómo te verán en el pueblo -----------------------------------------

// Grupo del catálogo → campo del avatar, con su título y, si se elige por color,
// las muestras.
const GRUPOS_DEL_AVATAR = [
  ['generos', 'genero', 'Género', null],
  ['pieles', 'piel', 'Piel', COLORES_DE_PIEL],
  ['pelos', 'pelo', 'Peinado', null],
  ['colores_de_pelo', 'color_de_pelo', 'Color de pelo', COLORES_DE_PELO],
  ['ropas', 'ropa', 'Ropa', COLORES_DE_ROPA],
];

function grupoDeOpciones(campo, leyenda, lista, muestras) {
  return el('fieldset', { class: 'grupo' },
    el('legend', {}, leyenda),
    el('div', { class: 'eleccion' }, lista.map((opcion, i) => el('label', { class: 'chip' },
      el('input', { type: 'radio', name: campo, value: opcion.clave, checked: i === 0 }),
      muestras ? el('span', {
        class: 'muestra',
        style: `background: ${Object.hasOwn(muestras, opcion.clave) ? muestras[opcion.clave] : '#9aa0a8'}`,
        'aria-hidden': 'true',
      }) : null,
      el('span', {}, opcion.nombre)))));
}

export async function avatar(contenedor, seguir, { sesion: quien, cuenta }) {
  const cuerpo = el('div', { class: 'cuerpo' },
    titulo('Crea tu avatar'),
    el('p', { class: 'entradilla' }, 'Así te verán en el pueblo, al lado de tu gachamon.'));
  const cargando = el('p', { class: 'cargando', role: 'status' }, 'Cargando las opciones…');
  cuerpo.append(cargando);
  contenedor.append(barra(quien.usuario), cuerpo);

  let opciones;
  try {
    opciones = await pedir('GET', 'avatar/opciones');
  } catch (error) {
    if (error && error.estado === 401) {
      await seguir();
      return;
    }
    cargando.replaceWith(reintento(mensajeDe(error), seguir));
    return;
  }

  const monigote = lienzo(96, 168, 'monigote');
  const placa = el('span', { class: 'placa', hidden: true });
  const nombre = el('input', {
    id: 'avatar-nombre', class: 'texto', name: 'nombre', type: 'text', maxlength: 24,
    required: true, autocomplete: 'nickname', autocapitalize: 'words', spellcheck: 'false',
    enterkeyhint: 'done',
  });
  const aviso = avisoVacio();
  const guardar = el('button', { type: 'submit', class: 'boton principal' }, 'Guardar mi avatar');
  const formulario = el('form', { class: 'formulario' },
    el('div', { class: 'campo' },
      el('label', { class: 'etiqueta', for: 'avatar-nombre' }, 'Tu nombre'),
      nombre),
    GRUPOS_DEL_AVATAR
      .filter(([grupo]) => Array.isArray(opciones[grupo]) && opciones[grupo].length)
      .map(([grupo, campo, leyenda, muestras]) => grupoDeOpciones(campo, leyenda, opciones[grupo], muestras)),
    aviso,
    guardar,
  );

  const elegido = () => {
    const datos = new FormData(formulario);
    const avatarElegido = { nombre: String(datos.get('nombre') || '') };
    for (const [, campo] of GRUPOS_DEL_AVATAR) avatarElegido[campo] = String(datos.get(campo) || '');
    return avatarElegido;
  };
  const repintar = () => {
    const actual = elegido();
    pintarAvatar(monigote, actual);
    const visible = actual.nombre.trim();
    placa.textContent = visible;
    placa.hidden = !visible;
  };

  formulario.addEventListener('input', repintar);
  formulario.addEventListener('change', repintar);
  formulario.addEventListener('submit', (evento) => {
    evento.preventDefault();
    conEspera(guardar, async () => {
      callar(aviso);
      try {
        await pedir('PUT', 'avatar', elegido());
        await seguir();
      } catch (error) {
        await fallo(error, aviso, seguir);
      }
    });
  });

  cargando.replaceWith(
    el('div', { class: 'vista-avatar' },
      el('div', { class: 'escena', 'aria-hidden': 'true' }, ventana(), placa, monigote)),
    formulario,
  );
  const traer = enlaceADiscord(cuerpo, seguir, cuenta);
  if (traer) cuerpo.append(traer);
  repintar();
}

function reintento(texto, seguir) {
  return el('div', { class: 'reintento' },
    el('p', { class: 'error', role: 'alert' }, texto),
    boton('Volver a intentarlo', 'boton principal', () => seguir()));
}

// --- huevo: el gachamon de partida ----------------------------------------------

// Si la cuenta cambió entre medias (se vinculó en otra pestaña) o si le falta el
// avatar, no es un error que enseñar: hay que volver a decidir.
const HUEVO_YA_NO_TOCA = new Set(['cuenta_cambio', 'sin_avatar']);

export function huevo(contenedor, seguir, { sesion: quien, cuenta }) {
  const dibujo = lienzo(112, 140, 'huevo meciendose');
  pintarHuevo(dibujo, false);
  const aviso = avisoVacio();
  const romper = el('button', { type: 'button', class: 'boton principal' }, 'Romper el huevo');
  romper.addEventListener('click', () => conEspera(romper, async () => {
    callar(aviso);
    dibujo.classList.replace('meciendose', 'temblando');
    try {
      const estado = await pedir('POST', 'huevo');
      pintarHuevo(dibujo, true);
      await pausa(700);
      await seguir(estado);
    } catch (error) {
      dibujo.classList.replace('temblando', 'meciendose');
      if (error && error.clave === 'ya_tienes') {
        await yaTiene(error);
        return;
      }
      if (error && HUEVO_YA_NO_TOCA.has(error.clave)) {
        await seguir();
        return;
      }
      await fallo(error, aviso, seguir);
    }
  }));

  // Ya tiene uno: se mira el estado otra vez. Si ahora toca otra pantalla (ya
  // tiene gachamon, o hay una muerte que contar), se sigue con él; si no —un
  // recluta sin nombre en la incubadora—, el huevo se queda con la frase del
  // servidor y el botón listo, en vez de volver a pintarse en silencio.
  async function yaTiene(error) {
    let estado;
    try {
      estado = await pedir('GET', 'estado');
    } catch (otro) {
      await fallo(otro, aviso, seguir);
      return;
    }
    if (siguiente(quien, cuenta, estado) !== 'huevo') {
      await seguir(estado);
      return;
    }
    avisar(aviso, mensajeDe(error));
  }

  const cuerpo = el('div', { class: 'cuerpo' },
    titulo('Un huevo para ti'),
    el('p', { class: 'entradilla' }, 'Algo se mueve dentro. ¿Qué gachamon saldrá?'),
    el('div', { class: 'escena', 'aria-hidden': 'true' }, ventana(), dibujo),
    aviso,
    romper,
  );
  const traer = enlaceADiscord(cuerpo, seguir, cuenta);
  if (traer) cuerpo.append(traer);
  contenedor.append(barra(quien.usuario), cuerpo);
}

// --- bautizo: el recién nacido y su nombre -------------------------------------

const BAUTIZO_YA_NO_TOCA = new Set(['sin_gachamon', 'ya_bautizado']);

function conMayuscula(texto) {
  return texto ? texto[0].toUpperCase() + texto.slice(1) : '';
}

export function bautizo(contenedor, seguir, { sesion: quien, estado }) {
  const nacido = estado.gachamon;
  const retrato = el('img', {
    class: 'retrato', src: nacido.retrato, alt: `Tu gachamon recién nacido, ${nacido.nombre_especie}`,
  });
  retrato.addEventListener('error', () => {
    retrato.replaceWith(el('span', { class: 'retrato-sin', role: 'img', 'aria-label': nacido.nombre_especie }, nacido.emoji));
  });
  const nombre = el('input', {
    id: 'bautizo-nombre', class: 'texto', name: 'nombre', type: 'text', maxlength: 24,
    required: true, autocomplete: 'off', autocapitalize: 'words', spellcheck: 'false',
    enterkeyhint: 'done',
  });
  const aviso = avisoVacio();
  const bautizar = el('button', { type: 'submit', class: 'boton principal' }, 'Ponerle este nombre');
  const formulario = el('form', { class: 'formulario' },
    el('div', { class: 'campo' },
      el('label', { class: 'etiqueta', for: 'bautizo-nombre' }, '¿Cómo se va a llamar?'),
      nombre),
    aviso,
    bautizar,
  );
  formulario.addEventListener('submit', (evento) => {
    evento.preventDefault();
    conEspera(bautizar, async () => {
      callar(aviso);
      try {
        await seguir(await pedir('POST', 'bautizar', { nombre: nombre.value }));
      } catch (error) {
        if (error && BAUTIZO_YA_NO_TOCA.has(error.clave)) {
          await seguir();
          return;
        }
        await fallo(error, aviso, seguir);
        nombre.focus();
      }
    });
  });

  contenedor.append(
    barra(quien.usuario),
    el('div', { class: 'cuerpo' },
      titulo('¡Nació tu gachamon!'),
      el('div', { class: 'escena' }, ventana(), retrato),
      el('div', { class: 'nacido' },
        el('p', { class: 'nacido-especie' },
          el('span', { 'aria-hidden': 'true' }, nacido.emoji), ' ', nacido.nombre_especie),
        el('p', { class: 'nacido-detalle' }, `${conMayuscula(nacido.nombre_etapa)} · ${nacido.genero}`)),
      formulario,
    ),
  );
}

// --- difunto: quién era y cuánto vivió -----------------------------------------

function cuantoVivio(dias) {
  if (dias < 1) return 'Vivió menos de un día';
  if (dias === 1) return 'Vivió 1 día';
  return `Vivió ${dias} días`;
}

export function difunto(contenedor, seguir, { sesion: quien, estado }) {
  const muerto = estado.difunto;
  const aviso = avisoVacio();
  // Sin relevo no se promete nada: puede tocar un huevo o un recluta sin nombre.
  const despues = estado.gachamon ? ` Ahora te acompaña ${estado.gachamon.nombre}.` : '';
  contenedor.append(
    barra(quien.usuario),
    el('div', { class: 'cuerpo' },
      titulo(`Adiós, ${muerto.nombre}`),
      el('div', { class: 'escena afuera' },
        el('div', { class: 'lapida' },
          el('span', { class: 'lapida-nombre' }, muerto.nombre),
          el('span', {}, muerto.nombre_especie),
          el('span', { class: 'lapida-dias' }, cuantoVivio(muerto.dias)))),
      el('p', { class: 'entradilla' }, `${muerto.nombre} ha muerto.${despues}`),
      aviso,
      boton('Seguir jugando', 'boton principal', async () => {
        callar(aviso);
        try {
          await seguir(await pedir('POST', 'difunto/visto'));
        } catch (error) {
          await fallo(error, aviso, seguir);
        }
      }),
    ),
  );
}

// --- cuando no se pudo ni decidir la pantalla -----------------------------------

export function noCarga(contenedor, seguir, { mensaje }) {
  contenedor.append(
    barra(null),
    el('div', { class: 'cuerpo' },
      titulo('No se pudo cargar el juego'),
      el('p', { class: 'entradilla' }, mensaje || ALGO_SALIO_MAL),
      boton('Volver a intentarlo', 'boton principal', () => seguir()),
    ),
  );
}
