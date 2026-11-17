import test from 'node:test';
import assert from 'node:assert/strict';
import { nombreDelSitio, noSePisan, sitiosDeEntrada } from '../../web/static/js/casillas.js';
import {
  casillaEn, medir, proyectar, tramoEn,
} from '../../web/static/js/proyeccion.js';

// Lo justo de un navegador para pintar el departamento sin pantalla, tocar sus
// botones y su lienzo: elementos con sus hijos (y quién los contiene), su
// texto, atributos, clases y oyentes, que se buscan con selectores sencillos
// (etiqueta, `.clase`, `[atributo]`, `[atributo=valor]`, juntos y uno dentro
// de otro); un lienzo que mide 380 × 310, no está en la esquina de la página y
// apunta lo que se pinta en él; imágenes que cargan solas; y un reloj y unos
// cuadros de animación que no corren solos.
class Nodo {
  constructor() { this.padre = null; }
}

class Texto extends Nodo {
  constructor(texto) {
    super();
    this.texto = texto;
  }

  get textContent() { return this.texto; }
}

// Los oyentes de un elemento o del documento, que se quitan solos con su `signal`.
function escuchar(oyentes, tipo, oyente, opciones) {
  const signal = opciones && opciones.signal;
  if (signal && signal.aborted) return;
  (oyentes[tipo] ||= []).push(oyente);
  if (signal) signal.addEventListener('abort', () => { oyentes[tipo] = oyentes[tipo].filter((o) => o !== oyente); });
}

// Dónde está el lienzo en la página: un toque se cuenta desde su esquina.
const LIENZO = { left: 12, top: 40, width: 380, height: 310 };

// Saca un nodo de donde esté. Como en un navegador, quitar del documento el
// nodo enfocado (o lo que lo contiene) deja el foco en el cuerpo, aunque se
// vuelva a meter enseguida.
function sacar(nodo) {
  const foco = document.activeElement;
  if (foco && (nodo === foco || (nodo instanceof Elemento && nodo.contains(foco)))) document.activeElement = document.body;
  if (nodo.padre) nodo.padre.hijos = nodo.padre.hijos.filter((h) => h !== nodo);
  nodo.padre = null;
}

function cumpleSimple(nodo, simple) {
  return (simple.match(/^[a-z0-9]+|\.[\w-]+|\[[^\]]+\]/g) || []).every((parte) => {
    if (parte.startsWith('.')) return nodo.classList.contains(parte.slice(1));
    if (parte.startsWith('[')) {
      const [nombre, valor] = parte.slice(1, -1).split('=');
      if (valor === undefined) return Object.hasOwn(nodo.atributos, nombre);
      return nodo.getAttribute(nombre) === valor.replace(/^["']|["']$/g, '');
    }
    return nodo.etiqueta === parte;
  });
}

class Elemento extends Nodo {
  constructor(etiqueta) {
    super();
    this.etiqueta = etiqueta;
    this.atributos = {};
    this.oyentes = {};
    this.hijos = [];
    this.style = { setProperty() {} };
    this.dataset = {};
    this.isConnected = true;
  }

  setAttribute(nombre, valor) { this.atributos[nombre] = String(valor); }

  getAttribute(nombre) { return Object.hasOwn(this.atributos, nombre) ? this.atributos[nombre] : null; }

  removeAttribute(nombre) { delete this.atributos[nombre]; }

  get hidden() { return Object.hasOwn(this.atributos, 'hidden'); }

  set hidden(valor) {
    if (valor) this.atributos.hidden = '';
    else delete this.atributos.hidden;
  }

  // Las clases son las del atributo `class`, como en un navegador.
  get classList() {
    const leer = () => String(this.atributos.class || '').split(/\s+/).filter(Boolean);
    const escribir = (lista) => { this.atributos.class = lista.join(' '); };
    const add = (...nombres) => escribir([...new Set([...leer(), ...nombres])]);
    const remove = (...nombres) => escribir(leer().filter((c) => !nombres.includes(c)));
    return {
      add,
      remove,
      contains: (nombre) => leer().includes(nombre),
      toggle: (nombre, poner) => {
        const quiere = poner === undefined ? !leer().includes(nombre) : Boolean(poner);
        if (quiere) add(nombre);
        else remove(nombre);
        return quiere;
      },
    };
  }

  get textContent() { return this.hijos.map((h) => h.textContent).join(''); }

  set textContent(texto) { this.replaceChildren(...(texto === '' ? [] : [new Texto(String(texto))])); }

  addEventListener(tipo, oyente, opciones) { escuchar(this.oyentes, tipo, oyente, opciones); }

  append(...nodos) {
    for (const nodo of nodos) {
      if (nodo.padre) sacar(nodo);
      nodo.padre = this;
      this.hijos.push(nodo);
    }
  }

  replaceChildren(...nodos) {
    for (const hijo of [...this.hijos]) sacar(hijo);
    this.append(...nodos);
  }

  insertBefore(nuevo, referencia) {
    if (nuevo.padre) sacar(nuevo);
    nuevo.padre = this;
    const donde = referencia ? this.hijos.indexOf(referencia) : -1;
    if (donde < 0) this.hijos.push(nuevo);
    else this.hijos.splice(donde, 0, nuevo);
    return nuevo;
  }

  remove() {
    if (this.padre) sacar(this);
  }

  cumple(selector) {
    return selector.split(',').some((s) => {
      const cadena = s.trim().split(/\s+/);
      if (!cumpleSimple(this, cadena.at(-1))) return false;
      let k = cadena.length - 2;
      for (let p = this.padre; p && k >= 0; p = p.padre) if (p instanceof Elemento && cumpleSimple(p, cadena[k])) k -= 1;
      return k < 0;
    });
  }

  querySelectorAll(selector) {
    return this.hijos.filter((h) => h instanceof Elemento)
      .flatMap((h) => [...(h.cumple(selector) ? [h] : []), ...h.querySelectorAll(selector)]);
  }

  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }

  closest(selector) {
    for (let nodo = this; nodo; nodo = nodo.padre) if (nodo.cumple(selector)) return nodo;
    return null;
  }

  contains(nodo) {
    return this.hijos.some((h) => h === nodo || (h instanceof Elemento && h.contains(nodo)));
  }

  hasChildNodes() { return this.hijos.length > 0; }

  // Un desplegable vale lo que su opción elegida (la primera, si no se eligió
  // otra), como en un navegador.
  get value() {
    if (this.etiqueta !== 'select') return this.valor ?? '';
    const opciones = this.querySelectorAll('option');
    const elegida = opciones.find((o) => o.getAttribute('value') === this.valor) || opciones[0];
    return elegida ? elegida.getAttribute('value') : '';
  }

  set value(valor) { this.valor = String(valor); }

  focus() { document.activeElement = this; }

  scrollIntoView() {}

  getBoundingClientRect() {
    const { left, top, width, height } = this.etiqueta === 'canvas' ? LIENZO : { left: 0, top: 0, width: 0, height: 0 };
    return { left, top, width, height, x: left, y: top, right: left + width, bottom: top + height };
  }

  // Un contexto (uno por lienzo) que acepta todo lo que se le pida pintar y lo
  // apunta en `trazos` como `[nombre, argumentos]`.
  getContext() {
    if (!this.contexto) {
      const trazos = [];
      this.trazos = trazos;
      this.contexto = new Proxy({}, {
        get: (_, nombre) => (...argumentos) => { trazos.push([nombre, argumentos]); },
        set: () => true,
      });
    }
    return this.contexto;
  }
}

// Una imagen que carga sola en cuanto se le da su dirección, salvo si la
// dirección contiene algo retenido (`retenerImagenes`): ésa espera a que se suelte.
const imagenesRetenidas = new Map();
globalThis.Image = class {
  constructor() {
    this.naturalWidth = 48;
    this.naturalHeight = 84;
  }

  get src() { return this.direccion; }

  set src(direccion) {
    this.direccion = direccion;
    const trozo = [...imagenesRetenidas.keys()].find((t) => String(direccion).includes(t));
    if (trozo !== undefined) imagenesRetenidas.get(trozo).push(this);
    else queueMicrotask(() => { if (this.onload) this.onload(); });
  }
};

// Las imágenes cuya dirección contiene `trozo` no cargan hasta que se llama a
// lo que devuelve.
function retenerImagenes(trozo) {
  imagenesRetenidas.set(trozo, []);
  return async () => {
    const esperando = imagenesRetenidas.get(trozo) || [];
    imagenesRetenidas.delete(trozo);
    for (const imagen of esperando) if (imagen.onload) imagen.onload();
    await asentar();
  };
}

// Lo que corre con el tiempo se apunta y no corre solo: lo de `setTimeout` y
// los cuadros de animación, sólo cuando una prueba los hace correr; lo de
// `setInterval`, nunca.
const RELOJ = 'reloj';
const INTERVALO = 'intervalo';
const ANIMACION = 'animación';
let marcas = 0;
let horaDelReloj = 0;
const pendientes = new Map();
const apuntar = (tipo) => (hacer, ms = 0) => {
  marcas += 1;
  pendientes.set(marcas, { tipo, hacer, cuando: horaDelReloj + ms });
  return marcas;
};
const olvidar = (marca) => { pendientes.delete(marca); };
globalThis.setTimeout = apuntar(RELOJ);
globalThis.clearTimeout = olvidar;
globalThis.setInterval = apuntar(INTERVALO);
globalThis.clearInterval = olvidar;
globalThis.requestAnimationFrame = apuntar(ANIMACION);
globalThis.cancelAnimationFrame = olvidar;

// Hace pasar `ms` milisegundos del reloj: corre, en orden, lo que se apuntó con
// `setTimeout` y vence en ese rato (también lo que se apunte mientras tanto).
async function correrReloj(ms) {
  const hasta = horaDelReloj + ms;
  for (;;) {
    const vencidas = [...pendientes].filter(([, { tipo, cuando }]) => tipo === RELOJ && cuando <= hasta)
      .sort(([a, pa], [b, pb]) => pa.cuando - pb.cuando || a - b);
    if (!vencidas.length) break;
    const [marca, { hacer, cuando }] = vencidas[0];
    pendientes.delete(marca);
    horaDelReloj = cuando;
    hacer();
    await asentar();
  }
  horaDelReloj = hasta;
}

const cuadrosPendientes = () => [...pendientes.values()].filter(({ tipo }) => tipo === ANIMACION).length;

// Hace correr los cuadros pedidos durante `ms` milisegundos, uno cada 16, como
// un navegador: cada cuadro recibe la hora y el que pide otro lo tiene en el
// siguiente. Si ya no queda ninguno pedido, se para.
let horaDelCuadro = 0;
async function correrCuadros(ms) {
  const hasta = horaDelCuadro + ms;
  while (horaDelCuadro < hasta) {
    const tanda = [...pendientes].filter(([, { tipo }]) => tipo === ANIMACION);
    if (!tanda.length) break;
    horaDelCuadro += 16;
    for (const [marca, { hacer }] of tanda) {
      pendientes.delete(marca);
      hacer(horaDelCuadro);
    }
  }
  await asentar();
}

globalThis.ResizeObserver = class {
  observe() {}

  disconnect() {}
};
globalThis.Node = Nodo;

// Lo que dicen las preferencias del aparato: sólo si se pidió menos movimiento.
let reducido = false;
globalThis.window = {
  devicePixelRatio: 1,
  matchMedia: (consulta) => ({
    matches: reducido && consulta.includes('reduce'), media: consulta, addEventListener() {}, removeEventListener() {},
  }),
  addEventListener() {},
};

// Deja correr todo lo que ya está en camino (respuestas, promesas encadenadas).
async function asentar() {
  for (let vuelta = 0; vuelta < 20; vuelta += 1) await new Promise((listo) => { setImmediate(listo); });
}

// Un documento nuevo para cada pantalla: así los oyentes de una prueba no oyen la siguiente.
function nuevoDocumento() {
  const oyentes = {};
  const documento = {
    hidden: false,
    activeElement: null,
    body: new Elemento('body'),
    createElement: (etiqueta) => new Elemento(etiqueta),
    createTextNode: (texto) => new Texto(texto),
    addEventListener: (tipo, oyente, opciones) => escuchar(oyentes, tipo, oyente, opciones),
    async dispara(tipo) {
      for (const oyente of [...(oyentes[tipo] || [])]) oyente({ type: tipo });
      await asentar();
    },
  };
  globalThis.document = documento;
  return documento;
}

nuevoDocumento();
const { departamento } = await import('../../web/static/js/departamento.js');

// Un servidor de mentira para `pedir`: apunta cada petición como `[ruta, cuerpo]`
// («GET departamento») y contesta lo que se le haya dicho para esa ruta. Un
// `Error` es quedarse sin red; un objeto con `estado` numérico, un «no» del
// juego con ese código. `retiene` deja en camino la próxima petición a esa
// ruta hasta que se suelta con lo que contesta.
function crearServidor() {
  const pedidos = [];
  const respuestas = new Map();
  const retenidas = new Map();

  function contestar(cuerpo) {
    if (cuerpo instanceof Error) throw new TypeError('Failed to fetch');
    if (cuerpo && typeof cuerpo.estado === 'number') {
      const { estado, clave, mensaje } = cuerpo;
      return { ok: false, status: estado, headers: { get: () => null }, json: async () => ({ detail: { clave, mensaje } }) };
    }
    return { ok: true, status: 200, headers: { get: () => null }, json: async () => cuerpo };
  }

  globalThis.fetch = async (url, opciones) => {
    const ruta = `${opciones.method} ${String(url).replace(/^\/gachamon\/api\//, '')}`;
    pedidos.push([ruta, opciones.body ? JSON.parse(opciones.body) : undefined]);
    if (retenidas.has(ruta)) {
      const espera = retenidas.get(ruta);
      retenidas.delete(ruta);
      return contestar(await espera);
    }
    if (!respuestas.has(ruta)) return contestar({ estado: 404, clave: 'no_existe', mensaje: 'Eso no existe.' });
    return contestar(respuestas.get(ruta));
  };

  return {
    pedidos,
    responde: (ruta, cuerpo) => { respuestas.set(ruta, cuerpo); },
    falla: (ruta) => { respuestas.set(ruta, new Error('sin red')); },
    retiene(ruta) {
      let soltar;
      retenidas.set(ruta, new Promise((listo) => { soltar = listo; }));
      return async (cuerpo) => {
        soltar(cuerpo);
        await asentar();
      };
    },
  };
}

// --- lo que se pinta ---------------------------------------------------------------

const PUERTA_ID = 20;
const CAMA_ID = 21;
const GUARDADA_ID = 22;
const MACETA_ID = 23;
const CUADRO_ID = 24;
const FELPUDO_ID = 25;

const CAMA = { clave: 'cama_sencilla', nombre: 'Cama sencilla', icono: 'iconos/muebles/cama_sencilla.png', capa: 'bulto', cama: true, ancho: 2, fondo: 1 };
const MACETA = { clave: 'maceta', icono: 'iconos/muebles/maceta.png', capa: 'bulto', cama: false, ancho: 1, fondo: 1 };
const CUADRO = { clave: 'cuadro', nombre: 'Cuadro', icono: 'iconos/muebles/cuadro.png', capa: 'pared', cama: false, ancho: 1, fondo: 1 };
const FELPUDO = { clave: 'felpudo', nombre: 'Felpudo', icono: 'iconos/muebles/felpudo.png', capa: 'suelo', cama: false, ancho: 1, fondo: 1 };
// La puerta, como la manda el servidor: de pared, de un tramo, sin ícono y con su marca.
const PUERTA = { clave: 'puerta', nombre: 'Puerta', icono: null, capa: 'pared', cama: false, puerta: true, ancho: 1, fondo: 1 };

const PELUSA = {
  id: 7, nombre: 'Pelusa', espera_nombre: false, se_nombro_solo: false, especie: 'pollito', nombre_especie: 'Pollito',
  emoji: '🐣', etapa: 'bebe', nombre_etapa: 'cría', nivel: 3, genero: 'hembra',
  barras: { comida: 62, animo: 80, aseo: 45 }, cara: 'feliz', desfallecido: false,
  retrato: '/gachamon/retrato/pollito/bebe/feliz/sin.png', esperas: {}, titulo: null,
};

const ESTADO = {
  ahora: '2026-11-16T12:00:00+00:00',
  avatar: { nombre: 'Feli', genero: 'hembra', piel: 'clara', pelo: 'largo', color_de_pelo: 'rojo', ropa: 'camisa' },
  gachamon: PELUSA,
  saldos: { monedas: 130, gemas: 2 },
  globos: [],
  lugar: { clave: 'casa', nombre: 'Tu casa', abre: null, aviso: null, ofrece: ['departamento'] },
};

// Un 3 × 3 con la cama sencilla en (0, 0), a lo ancho, y otra guardada; y la
// puerta donde nace, en el tramo de más adelante de la pared izquierda, (-1, 2):
// la casilla de dentro que le queda enfrente es (0, 2).
const DEPTO = {
  ancho: 3, fondo: 3, casillas: 9, comodidad: 82, tope: 100, camas: 1, gachamones: 1,
  plantel: [{ ...PELUSA, activo: true }], cabe_otro: false, ampliar: { ancho: 45, fondo: 45 },
  puestos: [{ id: CAMA_ID, ...CAMA, x: 0, y: 0, giro: 0, casillas: [[0, 0], [1, 0]] },
    { id: PUERTA_ID, ...PUERTA, x: -1, y: 2, giro: 0, casillas: [[-1, 2]] }],
  guardados: [{ id: GUARDADA_ID, ...CAMA }],
  saldos: { monedas: 130, gemas: 2 },
};

// Ese mismo departamento sin su puerta, como eran antes de ella: tu avatar entra
// en el primer sitio de entrada, la esquina de delante.
const sinPuerta = (depto) => ({ ...depto, puestos: depto.puestos.filter((p) => !p.puerta) });
const SIN_PUERTA = sinPuerta(DEPTO);

// Una copia del departamento con ese puesto de más.
const conPuesto = (depto, puesto) => ({ ...depto, puestos: [...depto.puestos, puesto] });

// Una copia del departamento con el puesto de ese id cambiado (`cambios`, lo que cambia de él).
const moverPuesto = (depto, id, cambios) => ({ ...depto, puestos: depto.puestos.map((p) => (p.id === id ? { ...p, ...cambios } : p)) });

// El mismo, con una maceta en (2, 2).
const CON_MACETA = {
  ...DEPTO,
  puestos: [...DEPTO.puestos, { id: MACETA_ID, ...MACETA, nombre: 'Maceta', x: 2, y: 2, giro: 0, casillas: [[2, 2]] }],
};

const LA_MACETA = { id: MACETA_ID, ...MACETA, nombre: 'Maceta' };

// El mismo, con la maceta guardada.
const SIN_MACETA = { ...DEPTO, guardados: [...DEPTO.guardados, LA_MACETA] };

// El 3 × 3 con la cama puesta y un cuadro guardado (y nada más guardado).
const CON_UN_CUADRO_GUARDADO = { ...DEPTO, guardados: [{ id: CUADRO_ID, ...CUADRO }] };

// El mismo, con el cuadro colgado en el tercer tramo de la pared derecha (en
// el segundo, la cama lo tapa).
const CON_UN_CUADRO_COLGADO = {
  ...DEPTO,
  puestos: [...DEPTO.puestos, { id: CUADRO_ID, ...CUADRO, x: 2, y: -1, giro: 0, casillas: [[2, -1]] }],
  guardados: [],
};

// Un 3 × 3 sin dos casillas libres juntas (macetas en (2, 1), (0, 1) y (1, 2)):
// la cama sencilla guardada no cabe en ningún sitio; el cuadro guardado, sí.
const SIN_SITIO_PARA_LA_CAMA = {
  ...DEPTO,
  puestos: [...DEPTO.puestos,
    { ...LA_MACETA, x: 2, y: 1, giro: 0, casillas: [[2, 1]] },
    { ...LA_MACETA, id: 26, x: 0, y: 1, giro: 0, casillas: [[0, 1]] },
    { ...LA_MACETA, id: 27, x: 1, y: 2, giro: 0, casillas: [[1, 2]] }],
  guardados: [{ id: GUARDADA_ID, ...CAMA }, { id: CUADRO_ID, ...CUADRO }],
};

// El de siempre, después de crecer una columna: una fila más cuesta ahora 60 (4 casillas).
const CUATRO_POR_TRES = { ...DEPTO, ancho: 4, casillas: 12, ampliar: { ancho: 45, fondo: 60 } };

// Lo que contestan poner, guardar y ampliar cuando sale bien.
const BIEN = (depto) => ({ ok: true, clave: null, mensaje: null, departamento: depto, estado: ESTADO });

const RULO = {
  id: 8, nombre: 'Rulo', espera_nombre: false, se_nombro_solo: false, especie: 'slime', nombre_especie: 'Gelatín',
  emoji: '🟢', etapa: 'bebe', nombre_etapa: 'cría', nivel: 2, genero: 'macho',
  barras: { comida: 50, animo: 70, aseo: 30 }, cara: 'feliz', desfallecido: false,
  retrato: '/gachamon/retrato/slime/bebe/feliz/sin.png', esperas: {}, titulo: null,
};

// El 3 × 3 de siempre con dos gachamones: Pelusa, que sale contigo, y Rulo.
const CON_DOS = { ...DEPTO, gachamones: 2, plantel: [{ ...PELUSA, activo: true }, { ...RULO, activo: false }] };

// El mismo, cuando ya sales con Rulo.
const CON_RULO_ACTIVO = { ...CON_DOS, plantel: [{ ...PELUSA, activo: false }, { ...RULO, activo: true }] };

// Monta la pantalla con lo que contesta `GET departamento` (y `GET estado`, el
// mismo estado con que se monta) y espera a que se asiente. `antes(servidor)`
// prepara el servidor antes de montarla. `hecho` es lo que devuelve la pantalla
// (lo que `principal.js` manda a la avería si falla). `azar` es el de la
// pantalla (cuándo y hacia dónde caminan solos, qué dice el globo): fijo, para
// que cada prueba dé siempre lo mismo. `llegando`, que se llegó caminando.
async function abrir(depto, estado = ESTADO, {
  movimientoReducido = false, antes = () => {}, azar = () => 0.5, llegando = false,
} = {}) {
  const documento = nuevoDocumento();
  reducido = movimientoReducido;
  // Lo que dejó pendiente otra prueba no corre en ésta.
  pendientes.clear();
  imagenesRetenidas.clear();
  const servidor = crearServidor();
  servidor.responde('GET departamento', depto);
  servidor.responde('GET estado', estado);
  antes(servidor);
  const pantalla = new Elemento('main');
  const seguido = [];
  const hecho = departamento(pantalla, estado, (...argumentos) => { seguido.push(argumentos); }, { azar, llegando });
  if (hecho && typeof hecho.catch === 'function') hecho.catch(() => {});
  await asentar();
  return { pantalla, pedidos: servidor.pedidos, servidor, seguido, documento, hecho };
}

// Cómo acaba lo que devolvió la pantalla, sin esperarlo para siempre:
// `'bien'`, `'avería'` o `'sigue'` (todavía no acaba).
async function comoAcaba(hecho) {
  return Promise.race([
    Promise.resolve(hecho).then(() => 'bien', () => 'avería'),
    asentar().then(() => 'sigue'),
  ]);
}

const uno = (raiz, selector) => raiz.querySelector(selector);
const todos = (raiz, selector) => raiz.querySelectorAll(selector);

// El texto de lo que cumple el selector (o de la raíz, sin él); `null` si no hay.
function texto(raiz, selector) {
  const nodo = selector === undefined ? raiz : uno(raiz, selector);
  return nodo ? nodo.textContent : null;
}

const boton = (raiz, que) => todos(raiz, 'button').find((b) => b.textContent.includes(que)) || null;

// El texto de cada botón, sin su emoji.
const rotulos = (raiz) => todos(raiz, 'button').map((b) => b.textContent.replace(/^[^\p{L}+]+/u, '').trim());

// El menú abierto sobre la pieza, o `null` si no hay ninguno abierto.
function menu(pantalla) {
  const abierto = uno(pantalla, '.menu-de-la-pieza');
  return abierto && !abierto.hidden ? abierto : null;
}

// El lienzo de la pieza (los íconos de la bandeja también son lienzos).
const lienzoDe = (pantalla) => uno(pantalla, '.pieza-lienzo');

async function tocar(nodo) {
  for (const oyente of [...(nodo.oyentes.click || [])]) oyente({ type: 'click' });
  await asentar();
}

// Un clic con su `detail`, como lo cuenta un navegador: 1, un clic suelto; 2, el
// segundo de un doble clic en el mismo sitio; 0, el que hace el teclado (Enter o espacio).
async function clicar(nodo, detail) {
  for (const oyente of [...(nodo.oyentes.click || [])]) oyente({ type: 'click', detail });
  await asentar();
}

// La fila de ese mueble en la lista (en «Muebles puestos» o en «Guardados»).
const fila = (raiz, id) => uno(raiz, `li[data-fila=${id}]`);

// Deja elegida en el desplegable la opción con ese texto, como quien la
// elige: cambia su valor y avisa del cambio.
function elegir(select, textoDeLaOpcion) {
  const opcion = todos(select, 'option').find((o) => o.textContent === textoDeLaOpcion);
  assert.ok(opcion, `no hay opción «${textoDeLaOpcion}»`);
  select.value = opcion.getAttribute('value');
  for (const oyente of [...(select.oyentes.change || [])]) oyente({ type: 'change' });
}

// Una tecla pulsada en ese nodo, que sube por los que lo contienen como en un navegador.
async function teclear(nodo, tecla) {
  for (let n = nodo; n; n = n.padre) {
    for (const oyente of [...((n.oyentes && n.oyentes.keydown) || [])]) oyente({ type: 'keydown', key: tecla, preventDefault() {} });
  }
  await asentar();
}

// Un toque en ese píxel del lienzo, contado desde su esquina.
async function tocarEn(pantalla, x, y) {
  const lienzo = lienzoDe(pantalla);
  const caja = lienzo.getBoundingClientRect();
  for (const oyente of [...(lienzo.oyentes.click || [])]) {
    oyente({ type: 'click', clientX: caja.left + x, clientY: caja.top + y, preventDefault() {} });
  }
  await asentar();
}

// La pieza que se ve, medida como la mide la pantalla: su tamaño sale de la línea de abajo.
function medidaDe(pantalla) {
  const [, ancho, fondo] = texto(pantalla, '.pieza-linea').match(/^(\d+) × (\d+)/).map(Number);
  return { m: medir(LIENZO.width, LIENZO.height, ancho, fondo), ancho, fondo };
}

async function tocarCasilla(pantalla, i, j) {
  const { m } = medidaDe(pantalla);
  await tocarEn(pantalla, ...proyectar(m, i + 0.5, j + 0.5));
}

// A media altura de ese tramo: `(-1, j)` en la pared izquierda, `(i, -1)` en la derecha.
async function tocarTramo(pantalla, i, j) {
  const { m } = medidaDe(pantalla);
  const punto = i === -1 ? proyectar(m, 0, j + 0.5, m.pared / 2) : proyectar(m, i + 0.5, 0, m.pared / 2);
  await tocarEn(pantalla, ...punto);
}

// Un toque `altos` altos de casilla por encima del centro de esa casilla: donde
// se ve el cuerpo de quien está parado en ella, y lo que tiene detrás.
async function tocarSobre(pantalla, i, j, altos) {
  const { m } = medidaDe(pantalla);
  await tocarEn(pantalla, ...proyectar(m, i + 0.5, j + 0.5, altos * m.th));
}

// Entra al modo construcción con el botón que hay bajo la pieza («Construir»),
// y lo termina con el mismo botón, que entonces dice «Listo». Como un clic de
// verdad, el botón toma el foco antes de oír el toque.
async function pulsarElModo(pantalla, dice) {
  const alModo = boton(pantalla, dice);
  assert.ok(alModo, `no hay «${dice}»`);
  alModo.focus();
  await tocar(alModo);
}

const construir = (pantalla) => pulsarElModo(pantalla, 'Construir');
const terminar = (pantalla) => pulsarElModo(pantalla, 'Listo');

// Dónde está en la pieza lo que se pintó con los pies en ese punto del lienzo,
// en sus coordenadas (las que se le pasan a `dibujarPieza`, que pinta a cada uno
// con los pies en el centro de su casilla), a la décima: sin redondear a la
// casilla, para ver también dónde se pinta lo que no está en el suelo (el umbral
// de la puerta). El avatar se pinta en píxeles enteros: la décima se lo traga.
function enLaPieza(pantalla, x, y) {
  const { m } = medidaDe(pantalla);
  const u = (x - m.ox) / (m.tw / 2);
  const v = (y - m.oy) / (m.th / 2);
  const aLaDecima = (n) => Math.round(n * 10) / 10 + 0;                 // y sin -0
  return [aLaDecima((v + u) / 2 - 0.5), aLaDecima((v - u) / 2 - 0.5)];
}

// Dónde pintó la pantalla a tu avatar la última vez que pintó la pieza: lo que
// queda bajo los pies de su cuerpo, que están 4 de sus 84 píxeles sobre el borde
// de abajo (el contrato del arte). `null` si esa vez no lo pintó.
function dondeEstas(pantalla) {
  const cuerpo = pintados(pantalla, '/avatar/cuerpo/').at(-1);
  if (!cuerpo) return null;
  const [, [, x, y, ancho, alto]] = cuerpo;
  return enLaPieza(pantalla, x + ancho / 2, y + alto * (80 / 84));
}

// Dónde pintó la pantalla a cada gachamon la última vez, como `dondeEstas`: sus
// pies están un cuarto de alto de casilla bajo el centro de su casilla.
function dondeEstanLosGachamones(pantalla) {
  const { m } = medidaDe(pantalla);
  return pintados(pantalla, '/gachamon/retrato/')
    .map(([, [, x, y, ancho, alto]]) => enLaPieza(pantalla, x + ancho / 2, y + alto - m.th / 4));
}

// Hace que la pantalla vuelva a leer la pieza, como al volver a la pestaña (la
// del documento de ahora: el de la última pantalla que se abrió).
async function releer() {
  await document.dispara('visibilitychange');
}

// El sitio de entrada del gachamon `n` de su plantel: tú vas en el primero.
function dondeEsta(depto, n) {
  return sitiosDeEntrada(depto.ancho, depto.fondo, noSePisan(depto), depto.plantel.length + 1)[n + 1];
}

// Toca la casilla donde entró el gachamon `n` de su plantel.
async function tocarA(pantalla, depto, n) {
  await tocarCasilla(pantalla, ...dondeEsta(depto, n));
}

// La pregunta abierta en lo de ampliar, o `null` si no hay ninguna.
const preguntaDeAmpliar = (pantalla) => uno(pantalla, '.ampliar .pregunta');

// Crecer por ese lado («+ columna», «+ fila»): se toca su botón y, en la
// pregunta que sale, «Ampliar».
async function ampliarPor(pantalla, lado) {
  await tocar(boton(pantalla, lado));
  await tocar(boton(preguntaDeAmpliar(pantalla), 'Ampliar'));
}

// Lo que hay en lo de ampliar, en el orden de la página: el botón de cada lado
// («+ fila», «+ columna») y la pregunta («pregunta»).
const enLoDeAmpliar = (pantalla) => todos(uno(pantalla, '.ampliar'), '.boton-lado, .pregunta')
  .map((n) => (n.classList.contains('pregunta') ? 'pregunta' : n.textContent.split(' (')[0]));

// Desde ahora, cada nodo que recibe el foco (también el cuerpo, cuando el que lo
// tenía sale de la página), en orden.
function historialDelFoco(documento) {
  const vistos = [];
  let actual = documento.activeElement;
  Object.defineProperty(documento, 'activeElement', {
    configurable: true,
    get: () => actual,
    set: (nodo) => { actual = nodo; vistos.push(nodo); },
  });
  return vistos;
}

// Lo que se pintó en el lienzo de la pieza la última vez: desde el último borrado.
function ultimoCuadro(pantalla) {
  const trazos = lienzoDe(pantalla).trazos || [];
  const desde = trazos.map(([nombre]) => nombre).lastIndexOf('clearRect');
  return trazos.slice(desde + 1);
}

// Las veces que se pintó ese dibujo (por un trozo de su dirección) la última vez.
const pintados = (pantalla, trozo) => ultimoCuadro(pantalla)
  .filter(([nombre, [imagen]]) => nombre === 'drawImage' && String(imagen && imagen.src).includes(trozo));

// Las casillas que se marcaron la última vez, en el orden en que se pintan: primero
// dónde puede ir lo que llevas en la mano y al final dónde está lo elegido. Cada
// marca empieza en la esquina de arriba de su casilla, medio alto de casilla
// sobre su centro.
function casillasMarcadas(pantalla) {
  const { m, ancho, fondo } = medidaDe(pantalla);
  return ultimoCuadro(pantalla).filter(([nombre]) => nombre === 'moveTo')
    .map(([, [x, y]]) => casillaEn(m, x, y + m.th / 2, ancho, fondo));
}

const enOrden = (casillas) => [...casillas].sort(([a, b], [c, d]) => a - c || b - d);

// Los sitios que se marcaron la última vez, como `casillasMarcadas` pero sin
// confundir un tramo de pared con la casilla de delante (las dos marcas empiezan
// en la misma esquina): cada marca es un trazo de cuatro esquinas, y su centro
// cae en su tramo (`[-1, j]`, la pared izquierda; `[i, -1]`, la derecha), a media
// altura de la pared, o en su casilla del suelo.
function sitiosMarcados(pantalla) {
  const { m, ancho, fondo } = medidaDe(pantalla);
  const trazos = ultimoCuadro(pantalla);
  return trazos.flatMap(([nombre, punto], n) => {
    if (nombre !== 'moveTo') return [];
    const esquinas = [punto, ...trazos.slice(n + 1, n + 4).map(([, otro]) => otro)];
    const [x, y] = [0, 1].map((k) => esquinas.reduce((suma, esquina) => suma + esquina[k], 0) / esquinas.length);
    return [tramoEn(m, x, y, ancho, fondo) || casillaEn(m, x, y, ancho, fondo)];
  });
}

// Dónde se pintó a cada gachamon en todos los cuadros desde que se abrió la
// pantalla, no sólo en el último, como `dondeEstanLosGachamones`.
function dondeSePintaronLosGachamones(pantalla) {
  const { m } = medidaDe(pantalla);
  return (lienzoDe(pantalla).trazos || [])
    .filter(([nombre, [imagen]]) => nombre === 'drawImage' && String(imagen && imagen.src).includes('/gachamon/retrato/'))
    .map(([, [, x, y, ancho, alto]]) => enLaPieza(pantalla, x + ancho / 2, y + alto - m.th / 4));
}

// Un azar que no se queda en una elección: da, por turnos, 0, 1/7, 2/7 … 6/7 y
// vuelta a empezar. Siete no es múltiplo de los tres que pide cada paseo (cuándo,
// quién y hacia dónde), así que cada uno de ellos va pasando por todos los valores.
function azarQueRecorre() {
  let n = 0;
  return () => {
    const valor = (n % 7) / 7;
    n += 1;
    return valor;
  };
}

// La casilla donde la pantalla pintó la última vez ese retrato: la que queda
// bajo sus pies, que están un cuarto de alto de casilla bajo el centro de la
// casilla. `null` si no lo pintó.
function dondeSePinto(pantalla, retrato) {
  const pintado = pintados(pantalla, retrato).at(-1);
  if (!pintado) return null;
  const [, [, x, y, ancho, alto]] = pintado;
  const { m, ancho: a, fondo: f } = medidaDe(pantalla);
  return casillaEn(m, x + ancho / 2, y + alto - m.th / 4, a, f);
}

// --- las pruebas ---------------------------------------------------------------------

test('al entrar pide el departamento y dice cómo está', async () => {
  const { pantalla, pedidos } = await abrir(DEPTO);
  assert.deepEqual(pedidos.map(([ruta]) => ruta), ['GET departamento']);
  assert.equal(texto(pantalla, '.pieza-linea'), '3 × 3 · 2 de 9 casillas · camas 1 · gachamones 1 · comodidad 82 de 100');
  assert.equal(uno(pantalla, 'canvas').getAttribute('aria-hidden'), 'true');
  assert.match(texto(pantalla, 'h1'), /Tu casa/);
});

test('si no carga lo dice y deja volver a intentarlo', async () => {
  const { pantalla, pedidos, servidor } = await abrir(new Error('sin red'));
  assert.equal(texto(pantalla, '[role=alert]'), 'No hay conexión con el juego. Revisa tu internet y vuelve a intentarlo.');
  servidor.responde('GET departamento', DEPTO);
  await tocar(boton(pantalla, 'Volver a intentarlo'));
  assert.equal(pedidos.length, 2);
  assert.equal(texto(pantalla, '.pieza-linea').startsWith('3 × 3'), true);
});

test('un 409 al leer se va de la pantalla', async () => {
  const { seguido } = await abrir({ estado: 409, clave: 'no_estas_ahi', mensaje: 'Para eso tienes que estar en tu departamento.' });
  assert.equal(seguido.length, 1);
});

test('al volver a la pestaña se vuelve a leer', async () => {
  const { pantalla, pedidos, servidor, documento } = await abrir(DEPTO);
  servidor.responde('GET departamento', CON_MACETA);
  await documento.dispara('visibilitychange');
  assert.deepEqual(pedidos.map(([ruta]) => ruta), ['GET departamento', 'GET estado', 'GET departamento']);   // y con la pieza, el estado
  assert.equal(texto(pantalla, '.pieza-linea').startsWith('3 × 3 · 3 de 9'), true);
});

test('tocar fuera de la pieza no hace nada', async () => {
  const { pantalla, pedidos } = await abrir(DEPTO);
  await tocarEn(pantalla, 2, 2);                                        // una esquina del lienzo
  assert.equal(pedidos.length, 1);
  assert.equal(texto(pantalla, '[role=status].aviso'), '');
  assert.deepEqual(dondeEstas(pantalla), [-0.6, 2]);                    // no se movió: sigue en la puerta
  assert.equal(cuadrosPendientes(), 0);                                 // ni echó a andar
  assert.equal(menu(pantalla), null);
});

test('tocar una casilla que se pisa lleva ahí a tu avatar, contando el toque desde la esquina del lienzo', async () => {
  const { pantalla, pedidos } = await abrir(DEPTO, ESTADO, { movimientoReducido: true });   // no camina: aparece
  assert.deepEqual(dondeEstas(pantalla), [-0.6, 2]);                    // la entrada: la puerta
  await tocarCasilla(pantalla, 0, 2);
  assert.deepEqual(dondeEstas(pantalla), [0, 2]);
  assert.equal(pedidos.length, 1);                                      // dónde estás no se manda
});

// --- mientras carga, y lo que llega tarde o no llega -------------------------------

test('mientras carga dice «Cargando tu departamento…», como la tienda y la mochila', async () => {
  const { pantalla } = await abrir(DEPTO, ESTADO, { antes: (servidor) => { servidor.retiene('GET departamento'); } });
  assert.equal(texto(pantalla, '.espera-tienda-texto'), 'Cargando tu departamento…');
  assert.equal(uno(pantalla, '.pieza').hidden, true);
});

test('si sales mientras la pieza viene en camino, lo que llega no pinta ni vuelve a llamar a seguir', async () => {
  let soltar;
  const { pantalla, seguido } = await abrir(DEPTO, ESTADO, { antes: (servidor) => { soltar = servidor.retiene('GET departamento'); } });
  await tocar(boton(pantalla, 'Mochila'));
  assert.equal(seguido.length, 1);
  await soltar(DEPTO);
  assert.equal(seguido.length, 1);
  assert.equal(uno(pantalla, '.pieza').hidden, true);
  assert.equal(texto(pantalla, '.pieza-linea'), '');
  assert.deepEqual(lienzoDe(pantalla).trazos || [], []);
});

test('si sales mientras una relectura viene en camino, lo que llega no pinta ni vuelve a llamar a seguir', async () => {
  const { pantalla, servidor, seguido, documento } = await abrir(DEPTO);
  const soltar = servidor.retiene('GET departamento');
  await documento.dispara('visibilitychange');
  await tocar(boton(pantalla, 'Mochila'));
  await soltar(CON_MACETA);
  assert.equal(seguido.length, 1);
  assert.equal(texto(pantalla, '.pieza-linea').startsWith('3 × 3 · 2 de 9'), true);
});

test('una relectura que falla no borra la pieza ni dice nada', async () => {
  const { pantalla, pedidos, servidor, documento, seguido } = await abrir(DEPTO);
  servidor.falla('GET departamento');
  await documento.dispara('visibilitychange');
  assert.deepEqual(pedidos.map(([ruta]) => ruta), ['GET departamento', 'GET estado', 'GET departamento']);
  assert.equal(uno(pantalla, '.pieza').hidden, false);
  assert.equal(texto(pantalla, '.pieza-linea'), '3 × 3 · 2 de 9 casillas · camas 1 · gachamones 1 · comodidad 82 de 100');
  assert.equal(texto(pantalla, '[role=status].aviso'), '');
  assert.equal(seguido.length, 0);
});

test('lo que reviente al preparar la pieza llega a la avería, también tras «Volver a intentarlo»', async () => {
  const ROTO = { ...DEPTO, puestos: null };                              // una pieza que no se puede pintar
  const primera = await abrir(ROTO);
  assert.equal(await comoAcaba(primera.hecho), 'avería');
  const { pantalla, servidor, hecho } = await abrir(new Error('sin red'));
  servidor.responde('GET departamento', ROTO);
  await tocar(boton(pantalla, 'Volver a intentarlo'));
  assert.equal(await comoAcaba(hecho), 'avería');
});

// --- caminar ---------------------------------------------------------------------------

test('tu avatar camina hasta la casilla tocada y, al llegar, deja de pedir cuadros', async () => {
  const { pantalla } = await abrir(SIN_PUERTA);                          // entras en la esquina de delante, (2, 2)
  await tocarCasilla(pantalla, 0, 2);
  assert.deepEqual(dondeEstas(pantalla), [2, 2]);                       // todavía no se movió: camina
  assert.equal(cuadrosPendientes(), 1);
  await correrCuadros(1000);                                            // dos casillas, a tres por segundo
  assert.deepEqual(dondeEstas(pantalla), [0, 2]);
  assert.equal(cuadrosPendientes(), 0);
});

test('tocar otra casilla a mitad de camino cambia el destino', async () => {
  const { pantalla } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 0, 2);
  await correrCuadros(200);                                             // a medio primer paso
  await tocarCasilla(pantalla, 2, 0);
  await correrCuadros(3000);
  assert.deepEqual(dondeEstas(pantalla), [2, 0]);
  assert.equal(cuadrosPendientes(), 0);
});

test('un mueble que llega donde estás te deja en la casilla libre más cercana, sin caminar', async () => {
  const { pantalla, servidor, documento } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);        // estás en (2, 2)
  servidor.responde('GET departamento', CON_MACETA);                     // y ahí llega la maceta
  await documento.dispara('visibilitychange');
  assert.deepEqual(dondeEstas(pantalla), [2, 1]);
  assert.equal(cuadrosPendientes(), 0);
});

test('un mueble que llega en tu camino lo corta: terminas el paso y te quedas ahí', async () => {
  const { pantalla, servidor, documento } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  await tocarCasilla(pantalla, 0, 2);                                    // de (2, 2) a (0, 2), por (1, 2)
  await correrCuadros(100);
  servidor.responde('GET departamento', { ...DEPTO, puestos: [...DEPTO.puestos, { ...LA_MACETA, x: 0, y: 2, giro: 0, casillas: [[0, 2]] }] });
  await documento.dispara('visibilitychange');
  await correrCuadros(3000);
  assert.deepEqual(dondeEstas(pantalla), [1, 2]);
  assert.equal(cuadrosPendientes(), 0);
});

// --- los muebles (se eligen tocándolos en el modo construcción) --------------------

test('tocar un mueble abre su menú, y tocarlo otra vez lo cierra', async () => {
  const { pantalla, pedidos } = await abrir(CON_MACETA);
  await construir(pantalla);
  assert.equal(menu(pantalla), null);
  await tocarCasilla(pantalla, 2, 2);
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Maceta');
  assert.deepEqual(rotulos(menu(pantalla)), ['Mover', 'Girar', 'Guardar']);
  await tocarCasilla(pantalla, 2, 2);
  assert.equal(menu(pantalla), null);
  await tocarCasilla(pantalla, 0, 0); await tocarCasilla(pantalla, 2, 0);           // elegir la cama y tocar el suelo
  assert.equal(menu(pantalla), null);
  assert.equal(pedidos.length, 1);                                                  // nada de esto habla con el servidor
});

test('guardar un mueble lo manda y no dice nada si sale bien', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_MACETA);
  servidor.responde('POST departamento/guardar', BIEN(SIN_MACETA));
  await construir(pantalla);
  await tocarCasilla(pantalla, 2, 2);
  await tocar(boton(menu(pantalla), 'Guardar'));
  assert.deepEqual(pedidos.at(-1), ['POST departamento/guardar', { mueble_id: MACETA_ID }]);
  assert.equal(texto(pantalla, '[role=status].aviso'), '');
  assert.equal(texto(pantalla, '.pieza-linea').startsWith('3 × 3 · 2 de 9'), true);
  assert.equal(menu(pantalla), null);
});

test('lo que el servidor rechaza se dice con su frase y nada cambia', async () => {
  const { pantalla, servidor } = await abrir(DEPTO);
  servidor.responde('POST departamento/guardar', { ok: false, clave: 'hace_falta', mensaje: 'Esa cama hace falta: sin ella alguien se queda sin dónde dormir.', departamento: DEPTO, estado: ESTADO });
  await construir(pantalla);
  await tocarCasilla(pantalla, 0, 0);
  await tocar(boton(menu(pantalla), 'Guardar'));
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Esa cama hace falta: sin ella alguien se queda sin dónde dormir.');
  assert.equal(texto(pantalla, '.pieza-linea'), '3 × 3 · 2 de 9 casillas · camas 1 · gachamones 1 · comodidad 82 de 100');
});

test('girar manda el giro siguiente que cabe, en su mismo sitio', async () => {
  const { pantalla, pedidos, servidor } = await abrir(DEPTO);            // la cama en (0, 0) con giro 0
  servidor.responde('POST departamento/poner', BIEN(DEPTO));
  await construir(pantalla);
  await tocarCasilla(pantalla, 1, 0);                                    // la otra casilla de la cama también es la cama
  await tocar(boton(menu(pantalla), 'Girar'));
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: CAMA_ID, x: 0, y: 0, giro: 1 }]);
});

test('mover: se toca dónde, y tocar donde no cabe lo suelta', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_MACETA);
  servidor.responde('POST departamento/poner', BIEN(CON_MACETA));
  await construir(pantalla);
  await tocarCasilla(pantalla, 2, 2); await tocar(boton(menu(pantalla), 'Mover'));
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Toca la casilla donde lo quieres.');
  await tocarCasilla(pantalla, 0, 0);                                    // ahí está la cama: se suelta
  assert.equal(pedidos.length, 1);
  await tocarCasilla(pantalla, 2, 0);                                    // ya no hay nada en la mano: es caminar
  assert.equal(pedidos.length, 1);
  await tocarCasilla(pantalla, 2, 2); await tocar(boton(menu(pantalla), 'Mover'));
  await tocarCasilla(pantalla, 2, 0);
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: MACETA_ID, x: 2, y: 0, giro: 0 }]);
});

test('poner uno guardado donde no cabe como viene lo prueba girado', async () => {
  const { pantalla, pedidos, servidor } = await abrir(DEPTO);            // una cama guardada
  servidor.responde('POST departamento/poner', BIEN(DEPTO));
  await tocar(boton(pantalla, 'Guardados'));
  assert.match(texto(uno(pantalla, '.bandeja'), 'button'), /Cama sencilla.*× 1.*2 casillas/s);
  await tocar(boton(uno(pantalla, '.bandeja'), 'Cama sencilla'));
  await tocarCasilla(pantalla, 2, 1);                                    // a lo ancho se sale: va girada
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: GUARDADA_ID, x: 2, y: 1, giro: 1 }]);
});

test('lo de pared se pone tocando la pared', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_UN_CUADRO_GUARDADO);
  servidor.responde('POST departamento/poner', BIEN(CON_UN_CUADRO_GUARDADO));
  await tocar(boton(pantalla, 'Guardados'));
  assert.match(texto(uno(pantalla, '.bandeja'), 'button'), /Cuadro.*en la pared/s);
  await tocar(boton(uno(pantalla, '.bandeja'), 'Cuadro'));
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Toca la pared donde lo quieres.');
  await tocarTramo(pantalla, 1, -1);
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: CUADRO_ID, x: 1, y: -1, giro: 0 }]);
});

test('sin guardados, la bandeja lo dice', async () => {
  const { pantalla } = await abrir({ ...DEPTO, guardados: [] });
  await tocar(boton(pantalla, 'Guardados'));
  assert.match(texto(pantalla, '.bandeja'), /No queda nada guardado\./);
});

test('ampliar lleva el evento de lo que se ve y enseña lo que cuesta: cuando la pieza crece, el toque siguiente estrena otro', async () => {
  const { pantalla, pedidos, servidor } = await abrir(DEPTO);
  await tocar(boton(pantalla, 'Ampliar'));
  assert.match(texto(pantalla, '.ampliar'), /\+ columna \(3 casillas\) · 45/);
  servidor.responde('POST departamento/ampliar', { ok: true, clave: null, mensaje: 'Tu departamento ahora mide 4 × 3.', departamento: CUATRO_POR_TRES, estado: ESTADO });
  await ampliarPor(pantalla, '+ columna');
  const [ruta, cuerpo] = pedidos.at(-1);
  assert.equal(ruta, 'POST departamento/ampliar');
  assert.equal(cuerpo.eje, 'ancho'); assert.match(cuerpo.evento_id, /^[\w-]{8,64}$/);
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Tu departamento ahora mide 4 × 3.');
  assert.match(texto(pantalla, '.ampliar'), /\+ fila \(4 casillas\) · 60/);
  await ampliarPor(pantalla, '+ columna');
  assert.notEqual(pedidos.at(-1)[1].evento_id, cuerpo.evento_id);        // la pieza creció: otro toque, otro evento
});

test('si la respuesta de ampliar se pierde y la relectura también, el toque siguiente lleva el mismo evento y no cobra otra vez', async () => {
  const { pantalla, pedidos, servidor } = await abrir(DEPTO);
  await tocar(boton(pantalla, 'Ampliar'));
  servidor.falla('POST departamento/ampliar');                           // llega o no: la respuesta no vuelve
  servidor.falla('GET departamento');                                    // y la relectura tampoco
  await ampliarPor(pantalla, '+ columna');
  await correrReloj(800); await correrReloj(2000);                       // los dos reintentos
  const ampliados = () => pedidos.filter(([ruta]) => ruta === 'POST departamento/ampliar');
  assert.equal(ampliados().length, 3);
  const [, primero] = ampliados()[0];
  assert.deepEqual(ampliados().map(([, c]) => c.evento_id), [primero.evento_id, primero.evento_id, primero.evento_id]);
  assert.equal(texto(pantalla, '[role=status].aviso'), 'No hubo respuesta. Revisa tu conexión.');
  assert.ok(pedidos.slice(pedidos.lastIndexOf(ampliados().at(-1))).some(([ruta]) => ruta === 'GET departamento'));   // se relee…
  assert.match(texto(pantalla, '.ampliar'), /\+ columna \(3 casillas\) · 45/);      // …no llega: se ve lo de antes
  assert.equal(preguntaDeAmpliar(pantalla), null);                                  // sin la pregunta
  assert.equal(boton(pantalla, '+ columna').getAttribute('aria-disabled'), null);   // y se puede tocar otra vez
  servidor.responde('POST departamento/ampliar', { ok: true, clave: null, mensaje: 'Tu departamento ahora mide 4 × 3.', departamento: CUATRO_POR_TRES, estado: ESTADO });
  await ampliarPor(pantalla, '+ columna');
  assert.equal(ampliados().length, 4);
  assert.deepEqual(ampliados().at(-1)[1], { eje: 'ancho', evento_id: primero.evento_id });   // si el primero entró, es una repetición
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Tu departamento ahora mide 4 × 3.');
  await ampliarPor(pantalla, '+ columna');                               // ya con la pieza de 4 × 3
  assert.notEqual(ampliados().at(-1)[1].evento_id, primero.evento_id);
});

test('en 8 × 8 ya no se ofrece crecer', async () => {
  const { pantalla } = await abrir({ ...DEPTO, ancho: 8, fondo: 8, casillas: 64, ampliar: { ancho: null, fondo: null } });
  await tocar(boton(pantalla, 'Ampliar'));
  assert.equal(texto(pantalla, '.ampliar p'), 'Tu departamento ya no puede crecer más.');
});

test('sin respuesta lo dice y vuelve a leer', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_MACETA);
  servidor.falla('POST departamento/guardar');
  await construir(pantalla);
  await tocarCasilla(pantalla, 2, 2);
  await tocar(boton(menu(pantalla), 'Guardar'));
  assert.equal(texto(pantalla, '[role=status].aviso'), 'No hubo respuesta. Revisa tu conexión.');
  assert.equal(pedidos.at(-1)[0], 'GET departamento');
});

test('una lectura que salió antes que una acción no pisa lo que la acción dejó', async () => {
  const { pantalla, pedidos, servidor, documento } = await abrir(CON_MACETA);
  const soltar = servidor.retiene('GET departamento');
  await documento.dispara('visibilitychange');                           // sale una lectura, y se queda en camino
  servidor.responde('POST departamento/guardar', BIEN(SIN_MACETA));
  await construir(pantalla);
  await tocarCasilla(pantalla, 2, 2);
  await tocar(boton(menu(pantalla), 'Guardar'));
  servidor.responde('GET departamento', SIN_MACETA);                     // el servidor ya tiene lo que dejó la acción
  await soltar(CON_MACETA);                                              // llega tarde, con la maceta todavía puesta
  assert.equal(texto(pantalla, '.pieza-linea').startsWith('3 × 3 · 2 de 9'), true);
  assert.equal(pedidos.filter(([ruta]) => ruta === 'GET departamento').length, 3);   // la que se tiró se vuelve a pedir
});

test('mientras una petición va, no sale otra', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_MACETA);
  const soltar = servidor.retiene('POST departamento/guardar');
  await construir(pantalla);
  await tocarCasilla(pantalla, 2, 2);
  const guardar = boton(menu(pantalla), 'Guardar');
  await tocar(guardar); await tocar(guardar);
  assert.equal(pedidos.filter(([ruta]) => ruta === 'POST departamento/guardar').length, 1);
  assert.equal(guardar.getAttribute('aria-busy'), 'true');
  await soltar(BIEN(SIN_MACETA));
});

// --- lo que el encargo dice y no prueba lo de arriba ----------------------------------

test('tocar algo que se pisa lo elige y camina hasta ahí', async () => {
  const CON_FELPUDO = { ...DEPTO, puestos: [...DEPTO.puestos, { id: FELPUDO_ID, ...FELPUDO, x: 0, y: 2, giro: 0, casillas: [[0, 2]] }] };
  const { pantalla } = await abrir(CON_FELPUDO, ESTADO, { movimientoReducido: true });
  await construir(pantalla);
  await tocarCasilla(pantalla, 0, 2);
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Felpudo');
  assert.deepEqual(dondeEstas(pantalla), [0, 2]);
});

test('lo colgado se elige tocándolo en la pared, y no se gira', async () => {
  const { pantalla } = await abrir(CON_UN_CUADRO_COLGADO);
  await construir(pantalla);
  await tocarTramo(pantalla, 2, -1);
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Cuadro');
  assert.deepEqual(rotulos(menu(pantalla)), ['Mover', 'Guardar']);
  await tocar(boton(menu(pantalla), 'Mover'));
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Toca la pared donde lo quieres.');
});

test('lo que llevas en la mano se ve en la bandeja, y tocarlo otra vez lo suelta', async () => {
  const { pantalla, pedidos } = await abrir(CON_UN_CUADRO_GUARDADO);
  await tocar(boton(pantalla, 'Guardados'));
  await tocar(boton(uno(pantalla, '.bandeja'), 'Cuadro'));
  assert.equal(boton(uno(pantalla, '.bandeja'), 'Cuadro').getAttribute('aria-pressed'), 'true');
  await tocar(boton(uno(pantalla, '.bandeja'), 'Cuadro'));
  assert.equal(boton(uno(pantalla, '.bandeja'), 'Cuadro').getAttribute('aria-pressed'), 'false');
  await tocarTramo(pantalla, 1, -1);                                     // ya no hay nada en la mano
  assert.equal(pedidos.length, 1);
});

test('lo que se pone desde guardados queda puesto y elegido', async () => {
  const { pantalla, servidor } = await abrir(CON_UN_CUADRO_GUARDADO);
  servidor.responde('POST departamento/poner', BIEN(CON_UN_CUADRO_COLGADO));
  await tocar(boton(pantalla, 'Guardados'));
  await tocar(boton(uno(pantalla, '.bandeja'), 'Cuadro'));
  await tocarTramo(pantalla, 2, -1);
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Cuadro');
  assert.equal(texto(pantalla, '[role=status].aviso'), '');
  assert.match(texto(pantalla, '.bandeja'), /No queda nada guardado\./);
});

// --- ronda de arreglo 1 --------------------------------------------------------------

test('tomar de la bandeja algo que no cabe en ningún sitio lo dice y deja elegido lo que estaba', async () => {
  const { pantalla, pedidos, servidor } = await abrir(SIN_SITIO_PARA_LA_CAMA);
  servidor.responde('POST departamento/guardar', BIEN(SIN_SITIO_PARA_LA_CAMA));
  await construir(pantalla);
  await tocarCasilla(pantalla, 2, 1);                                    // la maceta, elegida
  await tocar(boton(pantalla, 'Guardados'));
  await tocar(boton(uno(pantalla, '.bandeja'), 'Cama sencilla'));         // no cabe en ningún sitio
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Ahí no cabe.');
  assert.equal(boton(uno(pantalla, '.bandeja'), 'Cama sencilla').getAttribute('aria-pressed'), 'false');
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Maceta');           // sigue elegida, y su menú sirve
  await tocar(boton(menu(pantalla), 'Guardar'));
  assert.deepEqual(pedidos.at(-1), ['POST departamento/guardar', { mueble_id: MACETA_ID }]);
});

test('tomar de la bandeja algo que no cabe en ningún sitio no te quita lo que llevabas en la mano', async () => {
  const { pantalla, pedidos, servidor } = await abrir(SIN_SITIO_PARA_LA_CAMA);
  servidor.responde('POST departamento/poner', BIEN(SIN_SITIO_PARA_LA_CAMA));
  await tocar(boton(pantalla, 'Guardados'));
  await tocar(boton(uno(pantalla, '.bandeja'), 'Cuadro'));                // el cuadro, en la mano
  await tocar(boton(uno(pantalla, '.bandeja'), 'Cama sencilla'));         // la cama no cabe
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Ahí no cabe.');
  assert.equal(boton(uno(pantalla, '.bandeja'), 'Cuadro').getAttribute('aria-pressed'), 'true');
  assert.equal(boton(uno(pantalla, '.bandeja'), 'Cama sencilla').getAttribute('aria-pressed'), 'false');
  await correrReloj(7000);                                               // ese aviso pasa y vuelve la indicación
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Toca la pared donde lo quieres.');
  await tocarTramo(pantalla, 2, -1);                                     // y el toque todavía pone
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: CUADRO_ID, x: 2, y: -1, giro: 0 }]);
});

test('la indicación de dónde tocar se queda mientras lleves algo en la mano, y se va al soltarlo', async () => {
  const { pantalla, pedidos } = await abrir(CON_MACETA);
  await construir(pantalla);
  await tocarCasilla(pantalla, 2, 2); await tocar(boton(menu(pantalla), 'Mover'));
  await correrReloj(7000);                                               // más que lo que dura un aviso
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Toca la casilla donde lo quieres.');
  await tocarCasilla(pantalla, 0, 0);                                    // ahí está la cama: se suelta
  assert.equal(texto(pantalla, '[role=status].aviso'), '');
  assert.equal(pedidos.length, 1);
});

// --- los gachamones --------------------------------------------------------------------

test('la ficha de la derecha es la del que sale contigo, y se cambia tocando a otro', async () => {
  const { pantalla } = await abrir(CON_DOS);                             // Pelusa (sale contigo) y Rulo
  assert.match(texto(pantalla, '.ficha-elegido'), /Pelusa.*Sale contigo/s);
  assert.equal(boton(pantalla, 'Salir con'), null);
  assert.equal(menu(pantalla), null);
  await tocarA(pantalla, CON_DOS, 1);
  assert.match(texto(pantalla, '.ficha-elegido'), /Rulo/);
  assert.doesNotMatch(texto(pantalla, '.ficha-elegido'), /Sale contigo/);
  assert.notEqual(boton(pantalla, 'Salir con Rulo'), null);
  assert.deepEqual(rotulos(menu(pantalla)), ['Mover', 'Acariciar']);
});

test('cuidar al elegido manda su id y un evento, y cambia sus barras', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_DOS);
  await tocarA(pantalla, CON_DOS, 1);
  servidor.responde('POST cuidar', { ok: true, mensaje: 'Rulo quedó reluciente.', espera: 600, monedas: 1, evoluciono: false, logros: [],
    gachamon: { ...RULO, barras: { ...RULO.barras, aseo: 100 }, esperas: { ...RULO.esperas, limpiar: 600 } }, estado: ESTADO });
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Bañar'));
  const [ruta, cuerpo] = pedidos.at(-1);
  assert.equal(ruta, 'POST cuidar');
  assert.deepEqual([cuerpo.accion, cuerpo.gachamon_id], ['limpiar', RULO.id]); assert.match(cuerpo.evento_id, /^[\w-]{8,64}$/);
  assert.equal(boton(uno(pantalla, '.ficha-elegido'), 'Bañar').getAttribute('aria-disabled'), 'true');
  assert.match(texto(pantalla, '[role=status].aviso'), /Rulo quedó reluciente\./);
});

test('acariciar al elegido manda su id', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_DOS);
  servidor.responde('POST acariciar', { ok: true, mensaje: null, espera: 60, estado: ESTADO });
  await tocarA(pantalla, CON_DOS, 1);
  await tocar(boton(menu(pantalla), 'Acariciar'));
  assert.deepEqual(pedidos.at(-1), ['POST acariciar', { gachamon_id: RULO.id }]);
});

test('mover a un gachamon no habla con el servidor', async () => {
  const { pantalla, pedidos } = await abrir(CON_DOS, ESTADO, { movimientoReducido: true });   // no camina: aparece
  await tocarA(pantalla, CON_DOS, 1);
  await tocar(boton(menu(pantalla), 'Mover'));
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Toca la casilla donde lo quieres.');
  await tocarCasilla(pantalla, 0, 2);
  assert.equal(pedidos.length, 1);
  await tocarA(pantalla, CON_DOS, 0);                                    // se elige a Pelusa…
  assert.match(texto(pantalla, '.ficha-elegido'), /Pelusa/);
  await tocarCasilla(pantalla, 0, 2);                                    // …y Rulo está donde se le dejó: tocarlo lo elige
  assert.match(texto(pantalla, '.ficha-elegido'), /Rulo/);
});

test('a todos manda su evento, dice lo que contesta el juego y vuelve a leer', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_DOS);
  servidor.responde('POST cuidar/todos', { ok: true, a_cuantos: 2, de_cuantos: 2, tocados: [PELUSA.id, RULO.id], mensaje: 'Jugaste con 2 de 2.', monedas: 2, logros: [], estado: ESTADO });
  await tocar(boton(pantalla, 'Jugar con todos'));
  const [ruta, cuerpo] = pedidos.at(-3);
  assert.equal(ruta, 'POST cuidar/todos'); assert.equal(cuerpo.accion, 'jugar'); assert.match(cuerpo.evento_id, /^[\w-]{8,64}$/);
  assert.deepEqual(pedidos.slice(-2).map(([r]) => r), ['GET estado', 'GET departamento']);   // vuelve a leer el estado y la pieza
  assert.match(texto(pantalla, '[role=status].aviso'), /Jugaste con 2 de 2\./);
});

test('salir con otro lo manda y lo deja como el que sale contigo', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_DOS);
  await tocarA(pantalla, CON_DOS, 1);
  servidor.responde('POST departamento/salir', { ok: true, clave: null, mensaje: 'Ahora sales con Rulo.', departamento: CON_RULO_ACTIVO, estado: { ...ESTADO, gachamon: RULO } });
  await tocar(boton(pantalla, 'Salir con Rulo'));
  assert.deepEqual(pedidos.at(-1), ['POST departamento/salir', { gachamon_id: RULO.id }]);
  assert.match(texto(pantalla, '.ficha-elegido'), /Rulo.*Sale contigo/s);
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Ahora sales con Rulo.');
});

test('ver ficha abre la de ese gachamon', async () => {
  const { pantalla, seguido } = await abrir(CON_DOS);
  await tocarA(pantalla, CON_DOS, 1);
  await tocar(boton(pantalla, 'Ver ficha'));
  assert.deepEqual(seguido.at(-1)[1], { vista: 'ficha', gachamonId: RULO.id });
});

test('poner un mueble donde está parado uno lo corre a un lado', async () => {
  const { pantalla, servidor, documento } = await abrir(CON_DOS);
  const [i, j] = dondeEsta(CON_DOS, 1);                                  // donde está Rulo
  const conMaceta = { ...CON_DOS, puestos: [...CON_DOS.puestos, { id: MACETA_ID, ...MACETA, nombre: 'Maceta', x: i, y: j, giro: 0, casillas: [[i, j]] }] };
  servidor.responde('GET departamento', conMaceta);
  await documento.dispara('visibilitychange');
  await tocarCasilla(pantalla, i, j);                                    // viviendo, Rulo se tocaría antes que la maceta…
  assert.equal(menu(pantalla), null);                                    // …y ahí ya no está
  assert.doesNotMatch(texto(pantalla, '.ficha-elegido'), /Rulo/);
  await construir(pantalla);
  await tocarCasilla(pantalla, i, j);
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Maceta');         // ahí está la maceta
});

test('sin ningún gachamon la pieza se ve igual y lo dice', async () => {
  const { pantalla } = await abrir({ ...DEPTO, gachamones: 0, plantel: [] }, { ...ESTADO, gachamon: null, globos: [] });
  assert.equal(texto(pantalla, '.ficha-elegido'), 'Todavía no vive ningún gachamon contigo.');
  assert.equal(boton(pantalla, 'Alimentar a todos'), null);
  assert.notEqual(boton(pantalla, 'Ampliar'), null);
});

// --- lo que el encargo dice de los gachamones y no prueba lo de arriba -----------------

test('cada gachamon está en la pieza donde entró, y sólo el que sale contigo lleva su marca', async () => {
  const { pantalla } = await abrir(CON_DOS);
  assert.deepEqual(dondeSePinto(pantalla, PELUSA.retrato), dondeEsta(CON_DOS, 0));
  assert.deepEqual(dondeSePinto(pantalla, RULO.retrato), dondeEsta(CON_DOS, 1));
  const marcas = pintados(pantalla, 'efectos/marca.png');
  assert.equal(marcas.length, 1);
  const [, [, x, , ancho]] = marcas[0];
  const [, [, xPelusa, , anchoPelusa]] = pintados(pantalla, PELUSA.retrato).at(-1);
  assert.ok(Math.abs((x + ancho / 2) - (xPelusa + anchoPelusa / 2)) < 1e-6);   // encima de Pelusa
});

test('al salir con otro, la marca pasa a él', async () => {
  const { pantalla, servidor } = await abrir(CON_DOS);
  await tocarA(pantalla, CON_DOS, 1);
  servidor.responde('POST departamento/salir', { ok: true, clave: null, mensaje: 'Ahora sales con Rulo.', departamento: CON_RULO_ACTIVO, estado: { ...ESTADO, gachamon: RULO } });
  await tocar(boton(pantalla, 'Salir con Rulo'));
  const marcas = pintados(pantalla, 'efectos/marca.png');
  assert.equal(marcas.length, 1);
  const [, [, x, , ancho]] = marcas[0];
  const [, [, xRulo, , anchoRulo]] = pintados(pantalla, RULO.retrato).at(-1);
  assert.ok(Math.abs((x + ancho / 2) - (xRulo + anchoRulo / 2)) < 1e-6);   // encima de Rulo
});

test('caminan solos de vez en cuando, con el azar que se les da', async () => {
  const { pantalla } = await abrir(sinPuerta(CON_DOS), ESTADO, { azar: () => 0 });   // el primero, cada 4 s, al primer sitio libre
  await correrReloj(3999);
  assert.equal(cuadrosPendientes(), 0);
  await correrReloj(1);
  assert.equal(cuadrosPendientes(), 1);
  await correrCuadros(1000);
  assert.deepEqual(dondeSePinto(pantalla, PELUSA.retrato), [1, 1]);      // de (1, 2), sin pisarte a ti en (2, 2)
  assert.deepEqual(dondeSePinto(pantalla, RULO.retrato), dondeEsta(CON_DOS, 1));
  assert.equal(cuadrosPendientes(), 0);
});

test('con menos movimiento, o con algo en la mano, se quedan quietos', async () => {
  const quietos = await abrir(CON_DOS, ESTADO, { movimientoReducido: true, azar: () => 0 });
  await correrReloj(20_000);
  assert.equal(cuadrosPendientes(), 0);
  assert.deepEqual(dondeSePinto(quietos.pantalla, PELUSA.retrato), dondeEsta(CON_DOS, 0));
  const { pantalla } = await abrir(CON_DOS, ESTADO, { azar: () => 0 });
  await tocar(boton(pantalla, 'Guardados'));
  await tocar(boton(uno(pantalla, '.bandeja'), 'Cama sencilla'));        // la cama, en la mano
  await correrReloj(20_000);
  assert.equal(cuadrosPendientes(), 0);
  assert.deepEqual(dondeSePinto(pantalla, PELUSA.retrato), dondeEsta(CON_DOS, 0));
});

test('el globo sale sobre el que sale contigo y se anuncia', async () => {
  const { pantalla } = await abrir(CON_DOS, { ...ESTADO, globos: [{ tipo: 'suelta', texto: '¡Qué día tan bonito!' }] });
  assert.equal(texto(pantalla, '.globo'), '');
  await correrReloj(2500);
  assert.equal(texto(pantalla, '.globo'), '¡Qué día tan bonito!');
  assert.equal(uno(pantalla, '.globo').getAttribute('aria-live'), 'polite');
});

test('la ficha del elegido dice cómo está y cuánto le falta a cada cuidado, también al lector', async () => {
  const conEspera = { ...CON_DOS, plantel: [CON_DOS.plantel[0], { ...CON_DOS.plantel[1], esperas: { jugar: 600 } }] };
  const { pantalla } = await abrir(conEspera);
  await tocarA(pantalla, conEspera, 1);
  const ficha = uno(pantalla, '.ficha-elegido');
  assert.match(texto(ficha), /Gelatín cría · nivel 2/);
  assert.deepEqual(todos(ficha, '.medidor-cifra').map((c) => c.textContent), ['50', '70', '30']);
  const jugar = boton(ficha, 'Jugar');
  assert.equal(jugar.getAttribute('aria-disabled'), 'true');
  assert.equal(jugar.getAttribute('aria-label'), 'Jugar, disponible en 10 min');
  assert.equal(boton(ficha, 'Alimentar').getAttribute('aria-disabled'), 'false');
  assert.notEqual(boton(ficha, 'Acariciar'), null);
});

test('acariciar antes de tiempo dice cuándo; si se pudo, le salen corazones', async () => {
  const { pantalla, servidor } = await abrir(CON_DOS);
  await tocarA(pantalla, CON_DOS, 1);
  servidor.responde('POST acariciar', { ok: false, espera: 120, gachamon: RULO, estado: ESTADO });
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Acariciar'));
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Podrás acariciarlo en 2 min.');
  assert.equal(todos(pantalla, '.corazon').length, 0);
  servidor.responde('POST acariciar', { ok: true, espera: 0, gachamon: RULO, estado: ESTADO });
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Acariciar'));
  assert.ok(todos(pantalla, '.pieza-escenario .corazon').length > 0);
});

test('cuidar a uno que no sale contigo celebra su evolución, y no la de otro', async () => {
  const ADULTA = { ...PELUSA, etapa: 'adulto', nombre_etapa: 'adulta' };
  const { pantalla, servidor } = await abrir(CON_DOS, { ...ESTADO, gachamon: ADULTA });
  await tocarA(pantalla, CON_DOS, 1);
  servidor.responde('POST cuidar', { ok: true, mensaje: 'Juegan un rato.', espera: 600, monedas: 1, evoluciono: false, logros: [],
    gachamon: RULO, estado: { ...ESTADO, gachamon: ADULTA } });
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Jugar'));
  assert.equal(texto(pantalla, '.celebracion'), '');                    // la etapa de Pelusa no es la de Rulo
  const NINO = { ...RULO, etapa: 'nino', nombre_etapa: 'niño' };
  servidor.responde('POST cuidar', { ok: true, mensaje: 'Come con ganas.', espera: 600, monedas: 1, evoluciono: true, logros: [],
    gachamon: NINO, estado: { ...ESTADO, gachamon: ADULTA } });
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Alimentar'));
  assert.equal(texto(pantalla, '.celebracion'), '✨ ¡Rulo ha evolucionado! Ahora es niño.');
});

test('mientras un cuidado va, no sale otro', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_DOS);
  const soltar = servidor.retiene('POST cuidar');
  const banar = boton(uno(pantalla, '.ficha-elegido'), 'Bañar');
  await tocar(banar); await tocar(banar);
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Jugar'));
  assert.equal(pedidos.filter(([ruta]) => ruta === 'POST cuidar').length, 1);
  assert.equal(banar.getAttribute('aria-busy'), 'true');
  assert.equal(boton(uno(pantalla, '.ficha-elegido'), 'Jugar').getAttribute('aria-disabled'), 'true');
  await soltar({ ok: true, mensaje: 'Pelusa quedó reluciente.', espera: 600, monedas: 0, evoluciono: false, logros: [], gachamon: PELUSA, estado: ESTADO });
  assert.equal(boton(uno(pantalla, '.ficha-elegido'), 'Jugar').getAttribute('aria-disabled'), 'false');
});

test('con un mueble en la mano, tocar a un gachamon es tocar su casilla', async () => {
  const conMacetaGuardada = { ...CON_DOS, guardados: [LA_MACETA] };
  const { pantalla, pedidos, servidor } = await abrir(conMacetaGuardada);
  servidor.responde('POST departamento/poner', BIEN(conMacetaGuardada));
  await tocar(boton(pantalla, 'Guardados'));
  await tocar(boton(uno(pantalla, '.bandeja'), 'Maceta'));
  await tocarA(pantalla, conMacetaGuardada, 1);                          // donde está Rulo
  const [i, j] = dondeEsta(conMacetaGuardada, 1);
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: MACETA_ID, x: i, y: j, giro: 0 }]);
});

test('mover a un gachamon a donde no se pisa lo suelta, y se queda donde estaba', async () => {
  const { pantalla } = await abrir(CON_DOS, ESTADO, { movimientoReducido: true });
  await tocarA(pantalla, CON_DOS, 1);
  await tocar(boton(menu(pantalla), 'Mover'));
  await tocarCasilla(pantalla, 0, 0);                                    // la cama
  assert.equal(texto(pantalla, '[role=status].aviso'), '');
  assert.equal(menu(pantalla), null);
  assert.deepEqual(dondeSePinto(pantalla, RULO.retrato), dondeEsta(CON_DOS, 1));
});

test('si no queda ninguna casilla que se pise no se pinta a nadie, y la ficha sigue', async () => {
  const LLENO = {
    ...CON_DOS,
    puestos: [...CON_DOS.puestos,
      ...[[2, 0], [0, 1], [1, 1], [2, 1], [0, 2], [1, 2], [2, 2]].map(([x, y], n) => ({ ...LA_MACETA, id: 40 + n, x, y, giro: 0, casillas: [[x, y]] }))],
  };
  const { pantalla } = await abrir(sinPuerta(LLENO));
  assert.equal(dondeSePinto(pantalla, PELUSA.retrato), null);
  assert.equal(dondeSePinto(pantalla, RULO.retrato), null);
  assert.equal(dondeEstas(pantalla), null);
  assert.match(texto(pantalla, '.ficha-elegido'), /Pelusa.*Sale contigo/s);
  const conPuerta = await abrir(LLENO);                                  // con puerta, a ti se te ve en ella
  assert.deepEqual(dondeEstanLosGachamones(conPuerta.pantalla), []);
  assert.deepEqual(dondeEstas(conPuerta.pantalla), [-0.6, 2]);
});

// --- ronda de arreglo 1 de los gachamones ----------------------------------------------

test('volver a leer la pieza no le quita el foco a la ficha del elegido', async () => {
  const { pantalla, documento, servidor } = await abrir(CON_DOS);
  const ficha = uno(pantalla, '.ficha-elegido');
  const ver = boton(ficha, 'Ver ficha');
  ver.focus();
  await documento.dispara('visibilitychange');                           // la misma pieza
  assert.equal(documento.activeElement, ver);
  const acariciar = boton(ficha, 'Acariciar');
  acariciar.focus();
  const conHambre = { ...CON_DOS, plantel: [{ ...CON_DOS.plantel[0], barras: { ...PELUSA.barras, comida: 30 } }, CON_DOS.plantel[1]] };
  servidor.responde('GET departamento', conHambre);
  await documento.dispara('visibilitychange');                           // datos nuevos del mismo
  assert.equal(texto(ficha, '.medidor-cifra'), '30');
  assert.equal(documento.activeElement, acariciar);
  await tocarA(pantalla, CON_DOS, 1);                                     // Rulo, con «Salir con Rulo»
  const salir = boton(ficha, 'Salir con Rulo');
  salir.focus();
  await documento.dispara('visibilitychange');
  assert.equal(documento.activeElement, salir);
});

test('al salir con él, el foco que estaba en «Salir con …» pasa a su nombre', async () => {
  const { pantalla, documento, servidor } = await abrir(CON_DOS);
  await tocarA(pantalla, CON_DOS, 1);
  servidor.responde('POST departamento/salir', { ok: true, clave: null, mensaje: 'Ahora sales con Rulo.', departamento: CON_RULO_ACTIVO, estado: { ...ESTADO, gachamon: RULO } });
  const salir = boton(pantalla, 'Salir con Rulo');
  salir.focus();
  await tocar(salir);
  assert.equal(documento.activeElement, uno(pantalla, '.ficha-elegido-nombre'));
});

test('al cambiarle la cara se sigue pintando su retrato de antes hasta que llega el nuevo', async () => {
  const { pantalla, servidor } = await abrir(CON_DOS);
  await tocarA(pantalla, CON_DOS, 1);
  const CONTENTO = { ...RULO, cara: 'contento', retrato: '/gachamon/retrato/slime/bebe/contento/sin.png' };
  const soltar = retenerImagenes('/contento/');
  servidor.responde('POST cuidar', { ok: true, mensaje: 'Juegan un rato.', espera: 600, monedas: 0, evoluciono: false, logros: [],
    gachamon: CONTENTO, estado: ESTADO });
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Jugar'));
  assert.deepEqual(dondeSePinto(pantalla, RULO.retrato), dondeEsta(CON_DOS, 1));   // el de antes, mientras llega
  assert.equal(dondeSePinto(pantalla, CONTENTO.retrato), null);
  await soltar();
  assert.equal(dondeSePinto(pantalla, RULO.retrato), null);
  assert.deepEqual(dondeSePinto(pantalla, CONTENTO.retrato), dondeEsta(CON_DOS, 1));
});

// --- sin el dibujo: la lista -----------------------------------------------------------

test('cada mueble puesto está en la lista con su sitio y sus botones', async () => {
  const { pantalla } = await abrir(CON_MACETA);
  const filas = todos(pantalla, '.lista-puestos li');
  assert.deepEqual(filas.map((f) => texto(f, '.mueble-nombre')),
    ['Cama sencilla, en fila 1, columna 1', 'Puerta, en la pared izquierda, tramo 3', 'Maceta, en fila 3, columna 3']);
  assert.deepEqual(filas.map((f) => rotulos(f)), [['Mover', 'Girar', 'Guardar'], ['Mover'], ['Mover', 'Girar', 'Guardar']]);
  assert.deepEqual(rotulos(uno(pantalla, '.lista-guardados li')), ['Poner']);
});

test('mover desde la lista: se elige el sitio en un desplegable', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_MACETA);
  servidor.responde('POST departamento/poner', BIEN(CON_MACETA));
  await tocar(boton(fila(pantalla, MACETA_ID), 'Mover'));
  const sitios = todos(pantalla, '.donde option').map((o) => o.textContent);
  assert.ok(sitios.includes('fila 1, columna 3'));
  assert.ok(!sitios.includes('fila 1, columna 1') && !sitios.includes('fila 3, columna 3'));   // la cama, y donde ya está
  elegir(uno(pantalla, '.donde select'), 'fila 2, columna 3');
  await tocar(boton(pantalla, 'Ponerlo ahí'));
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: MACETA_ID, x: 2, y: 1, giro: 0 }]);
});

test('poner desde la lista uno que sólo cabe girado', async () => {
  const { pantalla, pedidos, servidor } = await abrir(DEPTO);
  servidor.responde('POST departamento/poner', BIEN(DEPTO));
  await tocar(boton(fila(pantalla, GUARDADA_ID), 'Poner'));
  elegir(uno(pantalla, '.donde select'), 'fila 1, columna 3');
  await tocar(boton(pantalla, 'Ponerlo ahí'));
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: GUARDADA_ID, x: 2, y: 0, giro: 1 }]);
});

test('lo de pared se ofrece en sus tramos y no se gira', async () => {
  const { pantalla } = await abrir(CON_UN_CUADRO_GUARDADO);
  await tocar(boton(fila(pantalla, CUADRO_ID), 'Poner'));
  const sitios = todos(pantalla, '.donde option').map((o) => o.textContent);
  assert.deepEqual(sitios, ['pared derecha, tramo 1', 'pared derecha, tramo 2', 'pared derecha, tramo 3',
                            'pared izquierda, tramo 1', 'pared izquierda, tramo 2']);   // en el 3 está la puerta
});

test('tras guardar, el foco sigue en ese mueble y se vuelve a decir cómo quedó la pieza', async () => {
  const { pantalla, servidor, documento } = await abrir(CON_MACETA);
  servidor.responde('POST departamento/guardar', BIEN(SIN_MACETA));
  await tocar(boton(fila(pantalla, MACETA_ID), 'Guardar'));
  assert.equal(fila(pantalla, MACETA_ID).closest('.lista-guardados') !== null, true);
  assert.equal(fila(pantalla, MACETA_ID).contains(documento.activeElement), true);
  assert.equal(texto(pantalla, '.solo-lector[role=status]'), '3 × 3 · 2 de 9 casillas · camas 1 · gachamones 1 · comodidad 82 de 100');
});

test('los gachamones se eligen también desde la lista, y se les acaricia desde su ficha', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_DOS);
  const botones = todos(pantalla, '.lista-gachamones button');
  assert.deepEqual(botones.map((b) => [b.textContent.trim(), b.getAttribute('aria-pressed')]), [['Pelusa', 'true'], ['Rulo', 'false']]);
  await tocar(botones[1]);
  assert.match(texto(pantalla, '.ficha-elegido'), /Rulo/);
  servidor.responde('POST acariciar', { ok: true, mensaje: null, espera: 60, estado: ESTADO });
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Acariciar'));
  assert.deepEqual(pedidos.at(-1), ['POST acariciar', { gachamon_id: RULO.id }]);
});

// --- lo que el encargo dice de la lista y no prueba lo de arriba -----------------------

// La maceta, de (2, 2) a (2, 1).
const MACETA_MOVIDA = {
  ...DEPTO,
  puestos: [...DEPTO.puestos, { id: MACETA_ID, ...MACETA, nombre: 'Maceta', x: 2, y: 1, giro: 0, casillas: [[2, 1]] }],
};

test('mover desde la lista: el foco vuelve a ese mueble, el ¿Dónde? se cierra y se vuelve a decir cómo quedó', async () => {
  const { pantalla, servidor, documento } = await abrir(CON_MACETA);
  servidor.responde('POST departamento/poner', BIEN(MACETA_MOVIDA));
  await tocar(boton(fila(pantalla, MACETA_ID), 'Mover'));
  assert.equal(documento.activeElement, uno(pantalla, '.donde select'));                 // a elegir el sitio
  const deQue = uno(pantalla, `[id=${uno(pantalla, '.donde select').getAttribute('aria-describedby')}]`);
  assert.equal(texto(deQue), 'Maceta, en fila 3, columna 3');                            // y se dice de qué mueble
  elegir(uno(pantalla, '.donde select'), 'fila 2, columna 3');
  await tocar(boton(pantalla, 'Ponerlo ahí'));
  assert.equal(texto(fila(pantalla, MACETA_ID), '.mueble-nombre'), 'Maceta, en fila 2, columna 3');
  assert.equal(uno(pantalla, '.donde select'), null);
  assert.equal(documento.activeElement, boton(fila(pantalla, MACETA_ID), 'Mover'));
  assert.equal(texto(pantalla, '.solo-lector[role=status]'), '3 × 3 · 3 de 9 casillas · camas 1 · gachamones 1 · comodidad 82 de 100');
  assert.equal(texto(pantalla, '[role=status].aviso'), '');                             // bien no sale texto
});

test('girar desde la lista manda el giro siguiente que cabe; lo colgado dice su pared y no se gira', async () => {
  const { pantalla, pedidos, servidor } = await abrir(DEPTO);
  servidor.responde('POST departamento/poner', BIEN(DEPTO));
  await tocar(boton(fila(pantalla, CAMA_ID), 'Girar'));
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: CAMA_ID, x: 0, y: 0, giro: 1 }]);
  const colgado = await abrir(CON_UN_CUADRO_COLGADO);
  const cuadro = fila(colgado.pantalla, CUADRO_ID);
  assert.equal(texto(cuadro, '.mueble-nombre'), 'Cuadro, en la pared derecha, tramo 3');
  assert.deepEqual(rotulos(cuadro), ['Mover', 'Guardar']);
});

test('desde la lista, lo que no cabe en ningún sitio lo dice y no pregunta dónde', async () => {
  const { pantalla, pedidos } = await abrir(SIN_SITIO_PARA_LA_CAMA);
  await tocar(boton(fila(pantalla, GUARDADA_ID), 'Poner'));
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Ahí no cabe.');
  assert.equal(uno(pantalla, '.donde select'), null);
  assert.equal(pedidos.length, 1);
});

test('Escape cierra el ¿Dónde? y el foco vuelve a lo que lo abrió', async () => {
  const { pantalla, documento } = await abrir(CON_MACETA);
  const mover = boton(fila(pantalla, MACETA_ID), 'Mover');
  await tocar(mover);
  assert.equal(mover.getAttribute('aria-expanded'), 'true');
  await teclear(uno(pantalla, '.donde select'), 'Escape');
  assert.equal(uno(pantalla, '.donde select'), null);
  assert.equal(mover.getAttribute('aria-expanded'), 'false');
  assert.equal(documento.activeElement, mover);
});

test('si el servidor no lo deja poner ahí, lo dice y el ¿Dónde? sigue abierto', async () => {
  const { pantalla, servidor, documento } = await abrir(CON_MACETA);
  servidor.responde('POST departamento/poner', { ok: false, clave: 'ocupado', mensaje: 'Ahí ya hay algo.', departamento: CON_MACETA, estado: ESTADO });
  await tocar(boton(fila(pantalla, MACETA_ID), 'Mover'));
  const ahi = boton(pantalla, 'Ponerlo ahí');
  ahi.focus();
  await tocar(ahi);
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Ahí ya hay algo.');
  assert.notEqual(uno(pantalla, '.donde select'), null);
  assert.equal(documento.activeElement, ahi);
  assert.equal(texto(pantalla, '.solo-lector[role=status]'), '');                       // no salió bien: no se anuncia
});

test('volver a leer la pieza no le quita el foco a la lista ni dice nada', async () => {
  const { pantalla, documento } = await abrir(CON_MACETA);
  const girar = boton(fila(pantalla, MACETA_ID), 'Girar');
  girar.focus();
  // Ni se le quita ni se le vuelve a dar (un lector de pantalla lo volvería a leer cada 30 segundos).
  let enfocado = 0;
  girar.focus = () => { enfocado += 1; documento.activeElement = girar; };
  await documento.dispara('visibilitychange');
  assert.equal(documento.activeElement, girar);
  assert.equal(enfocado, 0);
  await tocar(boton(fila(pantalla, MACETA_ID), 'Mover'));
  const select = uno(pantalla, '.donde select');
  elegir(select, 'fila 2, columna 3');
  await documento.dispara('visibilitychange');
  assert.equal(uno(pantalla, '.donde select'), select);
  assert.equal(documento.activeElement, select);
  assert.equal(todos(select, 'option').find((o) => o.getAttribute('value') === select.value).textContent, 'fila 2, columna 3');
  assert.equal(texto(pantalla, '.solo-lector[role=status]'), '');
});

test('mientras una petición va, la lista espera: lo que la mandó, ocupado, y lo demás no se puede usar', async () => {
  const CON_MACETA_Y_DOS = { ...CON_MACETA, gachamones: 2, plantel: CON_DOS.plantel };
  const { pantalla, pedidos, servidor } = await abrir(CON_MACETA_Y_DOS);
  const soltar = servidor.retiene('POST departamento/guardar');
  const guardar = boton(fila(pantalla, MACETA_ID), 'Guardar');
  await tocar(guardar);
  assert.equal(guardar.getAttribute('aria-busy'), 'true');
  for (const b of [boton(fila(pantalla, CAMA_ID), 'Mover'), boton(fila(pantalla, GUARDADA_ID), 'Poner'), ...todos(pantalla, '.lista-gachamones button')]) {
    assert.equal(b.getAttribute('aria-disabled'), 'true');
  }
  await tocar(boton(fila(pantalla, CAMA_ID), 'Mover'));
  await tocar(todos(pantalla, '.lista-gachamones button')[1]);
  assert.equal(uno(pantalla, '.donde select'), null);                                   // no se abre
  assert.match(texto(pantalla, '.ficha-elegido'), /Pelusa/);                            // ni cambia la ficha
  await soltar(BIEN({ ...CON_DOS }));
  assert.equal(boton(fila(pantalla, CAMA_ID), 'Mover').getAttribute('aria-disabled'), null);
  assert.equal(pedidos.filter(([ruta]) => ruta === 'POST departamento/guardar').length, 1);
});

test('elegir a un gachamon desde la lista no abre su menú, y tocarlo en la pieza lo marca en la lista', async () => {
  const { pantalla } = await abrir(CON_DOS);
  await tocar(todos(pantalla, '.lista-gachamones button')[1]);
  assert.equal(menu(pantalla), null);
  assert.deepEqual(todos(pantalla, '.lista-gachamones button').map((b) => b.getAttribute('aria-pressed')), ['false', 'true']);
  await tocarA(pantalla, CON_DOS, 0);                                                    // Pelusa, en la pieza
  assert.deepEqual(todos(pantalla, '.lista-gachamones button').map((b) => b.getAttribute('aria-pressed')), ['true', 'false']);
});

test('lo que sale bien desde el dibujo también se le dice a quien no lo ve; lo que ya tiene su frase, no', async () => {
  const { pantalla, servidor } = await abrir(CON_MACETA);
  servidor.responde('POST departamento/guardar', BIEN(SIN_MACETA));
  await construir(pantalla);
  await tocarCasilla(pantalla, 2, 2);
  await tocar(boton(menu(pantalla), 'Guardar'));
  assert.equal(texto(pantalla, '.solo-lector[role=status]'), '3 × 3 · 2 de 9 casillas · camas 1 · gachamones 1 · comodidad 82 de 100');
  await tocar(boton(pantalla, 'Ampliar'));
  servidor.responde('POST departamento/ampliar', { ok: true, clave: null, mensaje: 'Tu departamento ahora mide 4 × 3.',
    departamento: { ...SIN_MACETA, ancho: 4, casillas: 12 }, estado: ESTADO });
  await ampliarPor(pantalla, '+ columna');
  assert.equal(texto(pantalla, '.solo-lector[role=status]'), '');                       // ésa ya se dice con su frase
});

test('lo que se pone desde la lista queda elegido, y el gachamon que lo estaba deja de estarlo', async () => {
  const HABLA = { ...ESTADO, globos: [{ tipo: 'suelta', texto: '¡Qué día tan bonito!' }] };
  const PUESTA = { ...CON_DOS, puestos: [...CON_DOS.puestos, { id: GUARDADA_ID, ...CAMA, x: 2, y: 0, giro: 1, casillas: [[2, 0], [2, 1]] }], guardados: [] };
  const { pantalla, servidor } = await abrir(CON_DOS, HABLA);
  servidor.responde('POST departamento/poner', { ...BIEN(PUESTA), estado: HABLA });
  await tocarA(pantalla, CON_DOS, 0);                                                    // Pelusa, con su menú encima
  await tocar(boton(fila(pantalla, GUARDADA_ID), 'Poner'));
  await tocar(boton(pantalla, 'Ponerlo ahí'));
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Cama sencilla');
  await correrReloj(2500);
  assert.equal(texto(pantalla, '.globo'), '¡Qué día tan bonito!');                       // sin su menú encima, habla
});

// --- lo que no se puede usar, también lo que aparece después; la ficha, siempre con nombre --

test('lo que aparece mientras una petición va (la bandeja, lo de ampliar) nace sin poderse usar', async () => {
  const { pantalla, servidor } = await abrir(CON_DOS);
  const soltar = servidor.retiene('POST cuidar');
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Bañar'));                         // un cuidado en camino
  await tocar(boton(pantalla, 'Guardados'));                                             // la bandeja aparece ahora
  assert.equal(boton(uno(pantalla, '.bandeja'), 'Cama sencilla').getAttribute('aria-disabled'), 'true');
  await tocar(boton(pantalla, 'Ampliar'));                                               // y lo de ampliar, también
  assert.equal(boton(pantalla, '+ columna').getAttribute('aria-disabled'), 'true');
  assert.equal(boton(pantalla, '+ fila').getAttribute('aria-disabled'), 'true');
  await tocar(boton(pantalla, '+ columna'));                                             // y tocarlo no pregunta
  assert.equal(preguntaDeAmpliar(pantalla), null);
  await soltar({ ok: true, mensaje: 'Pelusa quedó reluciente.', espera: 600, monedas: 0, evoluciono: false, logros: [], gachamon: PELUSA, estado: ESTADO });
  assert.equal(boton(pantalla, '+ columna').getAttribute('aria-disabled'), null);
  assert.equal(boton(uno(pantalla, '.bandeja'), 'Cama sencilla').getAttribute('aria-disabled'), null);
});

test('sin ningún gachamon, la ficha sigue nombrada por algo que está en la página', async () => {
  const SIN_NADIE = { ...DEPTO, gachamones: 0, plantel: [] };
  const { pantalla, servidor, documento } = await abrir(SIN_NADIE, { ...ESTADO, gachamon: null, globos: [] });
  const ficha = uno(pantalla, '.ficha-elegido');
  const suNombre = () => uno(pantalla, `[id=${ficha.getAttribute('aria-labelledby')}]`);
  assert.equal(texto(suNombre()), 'Todavía no vive ningún gachamon contigo.');
  servidor.responde('GET departamento', DEPTO);                                          // llega uno
  await documento.dispara('visibilitychange');
  assert.equal(texto(suNombre()), 'Pelusa');
  servidor.responde('GET departamento', SIN_NADIE);                                      // y se va
  await documento.dispara('visibilitychange');
  assert.equal(texto(suNombre()), 'Todavía no vive ningún gachamon contigo.');
});

// --- la tanda de arreglos de la revisión final ---------------------------------------------

const DE_CASA = { tipo: 'lugar', texto: 'Qué calentito se está aquí.' };
const SUELTA = { tipo: 'suelta', texto: '¡Qué día tan bonito!' };

test('al llegar caminando, el que sale contigo dice enseguida algo del lugar, como en el lugar', async () => {
  const { pantalla } = await abrir(CON_DOS, { ...ESTADO, globos: [DE_CASA, SUELTA] }, { llegando: true });
  assert.equal(texto(pantalla, '.globo'), '');
  await correrReloj(600);
  assert.equal(texto(pantalla, '.globo'), 'Qué calentito se está aquí.');
});

test('sin llegar caminando, habla al rato y no dice lo del lugar', async () => {
  const { pantalla } = await abrir(CON_DOS, { ...ESTADO, globos: [DE_CASA, SUELTA] });
  await correrReloj(600);
  assert.equal(texto(pantalla, '.globo'), '');
  await correrReloj(1900);
  assert.equal(texto(pantalla, '.globo'), '¡Qué día tan bonito!');
});

test('cada relectura trae también el estado: lo que dice el que sale contigo se renueva, y los saldos', async () => {
  const HAMBRE = { tipo: 'necesidad', texto: 'Tengo hambre.' };
  const { pantalla, pedidos, servidor, documento } = await abrir(CON_DOS, { ...ESTADO, globos: [SUELTA] });
  await correrReloj(2500);
  assert.equal(texto(pantalla, '.globo'), '¡Qué día tan bonito!');
  servidor.responde('GET estado', { ...ESTADO, saldos: { monedas: 7, gemas: 2 }, globos: [HAMBRE] });
  servidor.responde('GET departamento', { ...CON_DOS, saldos: { monedas: 7, gemas: 2 } });
  await documento.dispara('visibilitychange');
  assert.deepEqual(pedidos.slice(1).map(([ruta]) => ruta).sort(), ['GET departamento', 'GET estado']);
  assert.equal(uno(pantalla, '.globo').classList.contains('visible'), false);   // lo que decía ya no pasa: se calla
  assert.match(texto(pantalla, '.saldo'), /7 monedas/);
  await correrReloj(31_000);                                             // la vuelta siguiente de la charla
  assert.equal(texto(pantalla, '.globo'), 'Tengo hambre.');
});

test('si el estado que trae una relectura pide otra pantalla, la del departamento se va con él', async () => {
  const { servidor, documento, seguido } = await abrir(DEPTO);
  const enLaTienda = { ...ESTADO, lugar: { clave: 'tienda', nombre: 'Tienda', abre: null, aviso: null, ofrece: ['tienda'] } };
  servidor.responde('GET estado', enLaTienda);
  await documento.dispara('visibilitychange');
  assert.equal(seguido.length, 1);
  assert.equal(seguido[0][0], enLaTienda);
});

test('la ficha del elegido dice «Desfallecido» o «Desfallecida» mientras lo esté, como la del lugar', async () => {
  const sinComer = (g) => ({ ...g, desfallecido: true, barras: { ...g.barras, comida: 0 } });
  const DESFALLECIDOS = { ...CON_DOS, plantel: [{ ...sinComer(PELUSA), activo: true }, { ...sinComer(RULO), activo: false }] };
  const { pantalla, servidor, documento } = await abrir(DESFALLECIDOS);
  const ficha = uno(pantalla, '.ficha-elegido');
  assert.equal(texto(ficha, '.insignia'), 'Desfallecida');                // Pelusa
  assert.equal(uno(ficha, '.insignia').hidden, false);
  await tocarA(pantalla, DESFALLECIDOS, 1);
  assert.equal(texto(ficha, '.insignia'), 'Desfallecido');                // Rulo
  assert.equal(uno(ficha, '.insignia').hidden, false);
  servidor.responde('GET departamento', CON_DOS);                          // ya comieron
  await documento.dispara('visibilitychange');
  assert.equal(uno(ficha, '.insignia').hidden, true);
});

test('una lectura que se tira por una acción más nueva se vuelve a pedir al acabar esa acción', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_DOS);
  servidor.responde('POST cuidar/todos', { ok: true, a_cuantos: 2, de_cuantos: 2, tocados: [PELUSA.id, RULO.id], mensaje: 'Jugaste con 2 de 2.', monedas: 2, logros: [], estado: ESTADO });
  const soltarLaLectura = servidor.retiene('GET departamento');
  await tocar(boton(pantalla, 'Jugar con todos'));                       // su relectura sale y se queda en camino
  const soltarElCuidado = servidor.retiene('POST cuidar');
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Alimentar'));      // otro cuidado, a Pelusa, antes de que llegue
  const jugo = (g) => ({ ...g, barras: { ...g.barras, animo: 100 }, esperas: { jugar: 1800 } });
  const JUGARON = { ...CON_DOS, plantel: [{ ...jugo(PELUSA), activo: true }, { ...jugo(RULO), activo: false }] };
  await soltarLaLectura(JUGARON);                                        // llega, pero hubo una acción más nueva: se tira
  servidor.responde('GET departamento', JUGARON);
  await soltarElCuidado({ ok: true, mensaje: 'Pelusa comió con ganas.', espera: 600, monedas: 1, evoluciono: false, logros: [],
    gachamon: { ...jugo(PELUSA), esperas: { jugar: 1800, alimentar: 600 } }, estado: ESTADO });
  assert.equal(pedidos.filter(([ruta]) => ruta === 'GET departamento').length, 3);   // al entrar, la que se tiró y otra
  await tocar(boton(uno(pantalla, '.lista-gachamones'), 'Rulo'));
  const ficha = uno(pantalla, '.ficha-elegido');
  assert.deepEqual(todos(ficha, '.medidor-cifra').map((c) => c.textContent), ['50', '100', '30']);   // Rulo, al día
  assert.equal(boton(ficha, 'Jugar').getAttribute('aria-disabled'), 'true');
});

test('lo que devuelve la pantalla no acaba mientras se está en ella, y acaba bien al irse', async () => {
  const { pantalla, hecho } = await abrir(DEPTO);
  assert.equal(await comoAcaba(hecho), 'sigue');
  await tocar(boton(pantalla, 'Mochila'));
  assert.equal(await comoAcaba(hecho), 'bien');
});

test('lo que reviente al pintar lo que trae una relectura llega a la avería, como en la primera carga', async () => {
  const { servidor, documento, hecho } = await abrir(DEPTO);
  servidor.responde('GET departamento', { ...DEPTO, puestos: null });   // una pieza que no se puede pintar
  await documento.dispara('visibilitychange');
  assert.equal(await comoAcaba(hecho), 'avería');
});

test('lo que reviente al pintar lo que contesta una acción llega a la avería, como en la primera carga', async () => {
  const { pantalla, servidor, hecho } = await abrir(CON_MACETA);
  servidor.responde('POST departamento/guardar', BIEN({ ...SIN_MACETA, puestos: null }));
  await construir(pantalla);
  await tocarCasilla(pantalla, 2, 2);
  await tocar(boton(menu(pantalla), 'Guardar'));
  assert.equal(await comoAcaba(hecho), 'avería');
});

// --- lo que decidió el dueño al ver el plan terminado: ampliar pregunta antes de cobrar --

test('tocar «+ columna» no manda nada: enseña la pregunta con lo que cuesta, en palabras', async () => {
  const { pantalla, pedidos, documento } = await abrir(DEPTO);
  await tocar(boton(pantalla, 'Ampliar'));
  await tocar(boton(pantalla, '+ columna'));
  assert.equal(pedidos.length, 1);                                                       // sólo la lectura de al entrar
  assert.equal(texto(preguntaDeAmpliar(pantalla), '.pregunta-texto'), '¿Ampliar por 45 monedas?');
  assert.deepEqual(rotulos(preguntaDeAmpliar(pantalla)), ['Ampliar', 'No']);
  assert.equal(documento.activeElement, uno(preguntaDeAmpliar(pantalla), '.pregunta-texto'));   // se lee; no se confirma con una tecla
  assert.deepEqual(enLoDeAmpliar(pantalla), ['+ fila', '+ columna', 'pregunta']);          // bajo su lado, que sigue a la vista
  const barata = await abrir({ ...DEPTO, ampliar: { ancho: 1, fondo: 45 } });            // el coste lo manda el servidor
  await tocar(boton(barata.pantalla, 'Ampliar'));
  await tocar(boton(barata.pantalla, '+ columna'));
  assert.equal(texto(preguntaDeAmpliar(barata.pantalla), '.pregunta-texto'), '¿Ampliar por 1 moneda?');
});

test('«No» y Escape cierran la pregunta sin mandar nada, y el foco vuelve al botón que la abrió', async () => {
  const { pantalla, pedidos, documento } = await abrir(DEPTO);
  await tocar(boton(pantalla, 'Ampliar'));
  await tocar(boton(pantalla, '+ columna'));
  await tocar(boton(preguntaDeAmpliar(pantalla), 'No'));
  assert.equal(preguntaDeAmpliar(pantalla), null);
  assert.equal(documento.activeElement, boton(pantalla, '+ columna'));
  assert.equal(boton(pantalla, '+ columna').getAttribute('aria-expanded'), 'false');
  await tocar(boton(pantalla, '+ fila'));
  await teclear(uno(preguntaDeAmpliar(pantalla), '.pregunta-texto'), 'Escape');
  assert.equal(preguntaDeAmpliar(pantalla), null);
  assert.equal(documento.activeElement, boton(pantalla, '+ fila'));
  assert.equal(boton(pantalla, '+ fila').getAttribute('aria-expanded'), 'false');
  assert.equal(pedidos.length, 1);
});

test('un doble toque en «Ampliar» manda una sola petición; mientras va, la pregunta espera', async () => {
  const { pantalla, pedidos, servidor } = await abrir(DEPTO);
  const ampliados = () => pedidos.filter(([ruta]) => ruta === 'POST departamento/ampliar');
  await tocar(boton(pantalla, 'Ampliar'));
  await tocar(boton(pantalla, '+ columna'));
  assert.equal(ampliados().length, 0);
  assert.equal(todos(pantalla, '.ampliar .pregunta').length, 1);
  const soltar = servidor.retiene('POST departamento/ampliar');
  const ampliar = boton(preguntaDeAmpliar(pantalla), 'Ampliar');
  await tocar(ampliar); await tocar(ampliar);
  assert.equal(ampliados().length, 1);
  assert.equal(ampliar.getAttribute('aria-busy'), 'true');
  assert.equal(boton(preguntaDeAmpliar(pantalla), 'No').getAttribute('aria-disabled'), 'true');
  assert.equal(boton(pantalla, '+ fila').getAttribute('aria-disabled'), 'true');
  assert.equal(boton(pantalla, '+ columna').getAttribute('aria-disabled'), 'true');
  await teclear(uno(preguntaDeAmpliar(pantalla), '.pregunta-texto'), 'Escape');         // mientras va, no se cierra
  await tocar(boton(pantalla, '+ columna'));                                             // ni tocando su lado
  assert.notEqual(preguntaDeAmpliar(pantalla), null);
  await soltar({ ok: true, clave: null, mensaje: 'Tu departamento ahora mide 4 × 3.', departamento: CUATRO_POR_TRES, estado: ESTADO });
  assert.equal(ampliados().length, 1);
});

test('tras ampliar bien la pregunta ya no está: para ampliar otra vez hay que tocar y confirmar de nuevo', async () => {
  const { pantalla, pedidos, servidor, documento } = await abrir(DEPTO);
  servidor.responde('POST departamento/ampliar', { ok: true, clave: null, mensaje: 'Tu departamento ahora mide 4 × 3.', departamento: CUATRO_POR_TRES, estado: ESTADO });
  await tocar(boton(pantalla, 'Ampliar'));
  await tocar(boton(pantalla, '+ columna'));
  const ampliar = boton(preguntaDeAmpliar(pantalla), 'Ampliar');
  ampliar.focus();
  await tocar(ampliar);
  assert.equal(preguntaDeAmpliar(pantalla), null);
  assert.equal(documento.activeElement, boton(pantalla, '+ columna'));                  // el foco, en el lado por el que creció
  await tocar(boton(pantalla, '+ fila'));
  assert.equal(texto(preguntaDeAmpliar(pantalla), '.pregunta-texto'), '¿Ampliar por 60 monedas?');   // lo que cuesta ahora
  assert.equal(pedidos.filter(([ruta]) => ruta === 'POST departamento/ampliar').length, 1);
});

test('si el servidor dice que no, se ve su frase y la pregunta se cierra', async () => {
  const { pantalla, servidor } = await abrir(DEPTO);
  servidor.responde('POST departamento/ampliar', { ok: false, clave: 'faltan_monedas', mensaje: 'Te faltan 15 monedas.', departamento: DEPTO, estado: ESTADO });
  await tocar(boton(pantalla, 'Ampliar'));
  await ampliarPor(pantalla, '+ columna');
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Te faltan 15 monedas.');
  assert.equal(preguntaDeAmpliar(pantalla), null);
  assert.equal(boton(pantalla, '+ columna').getAttribute('aria-expanded'), 'false');
});

test('sólo hay una pregunta abierta: la del otro lado cierra la primera, y «Volver» la cierra', async () => {
  const { pantalla, pedidos } = await abrir(CUATRO_POR_TRES);
  await tocar(boton(pantalla, 'Ampliar'));
  await tocar(boton(pantalla, '+ columna'));
  assert.equal(texto(preguntaDeAmpliar(pantalla), '.pregunta-texto'), '¿Ampliar por 45 monedas?');
  await tocar(boton(pantalla, '+ fila'));
  assert.equal(todos(pantalla, '.ampliar .pregunta').length, 1);
  assert.equal(texto(preguntaDeAmpliar(pantalla), '.pregunta-texto'), '¿Ampliar por 60 monedas?');
  assert.deepEqual(enLoDeAmpliar(pantalla), ['+ fila', 'pregunta', '+ columna']);
  assert.equal(boton(pantalla, '+ columna').getAttribute('aria-expanded'), 'false');
  await tocar(boton(pantalla, 'Volver'));
  await tocar(boton(pantalla, 'Ampliar'));
  assert.equal(preguntaDeAmpliar(pantalla), null);
  assert.equal(pedidos.length, 1);
});

test('mientras otra petición va, la pregunta abierta no se puede usar', async () => {
  const { pantalla, pedidos, servidor } = await abrir(CON_MACETA);
  await tocar(boton(pantalla, 'Ampliar'));
  await tocar(boton(pantalla, '+ columna'));
  const soltar = servidor.retiene('POST departamento/guardar');
  await tocar(boton(fila(pantalla, MACETA_ID), 'Guardar'));                              // desde la lista, que sigue a la vista
  const ampliar = boton(preguntaDeAmpliar(pantalla), 'Ampliar');
  assert.equal(ampliar.getAttribute('aria-disabled'), 'true');
  assert.equal(boton(preguntaDeAmpliar(pantalla), 'No').getAttribute('aria-disabled'), 'true');
  await tocar(ampliar);
  assert.equal(pedidos.filter(([ruta]) => ruta === 'POST departamento/ampliar').length, 0);
  await soltar(BIEN(SIN_MACETA));                                                        // la misma pieza, del mismo tamaño
  assert.equal(boton(preguntaDeAmpliar(pantalla), 'Ampliar').getAttribute('aria-disabled'), null);
});

test('la pregunta se queda mientras la pieza mida y cueste lo mismo, sin volver a darle el foco; si llega otra, se cierra', async () => {
  const { pantalla, pedidos, servidor, documento } = await abrir(DEPTO);
  await tocar(boton(pantalla, 'Ampliar'));
  await tocar(boton(pantalla, '+ fila'));
  const pregunta = uno(preguntaDeAmpliar(pantalla), '.pregunta-texto');
  // Ni se le quita ni se le vuelve a dar (un lector de pantalla la volvería a leer cada 30 segundos).
  let enfocada = 0;
  pregunta.focus = () => { enfocada += 1; documento.activeElement = pregunta; };
  await documento.dispara('visibilitychange');                                           // la misma pieza
  assert.equal(uno(preguntaDeAmpliar(pantalla), '.pregunta-texto'), pregunta);
  assert.equal(documento.activeElement, pregunta);
  assert.equal(enfocada, 0);
  servidor.responde('GET departamento', CUATRO_POR_TRES);                               // creció por otro lado (otra pestaña)
  await documento.dispara('visibilitychange');
  assert.equal(preguntaDeAmpliar(pantalla), null);                                       // lo que costaba ya no es lo que cuesta
  assert.match(texto(pantalla, '.ampliar'), /\+ fila \(4 casillas\) · 60/);
  assert.equal(documento.activeElement, boton(pantalla, '+ fila'));
  assert.equal(pedidos.filter(([ruta]) => ruta === 'POST departamento/ampliar').length, 0);
});

// --- ronda de arreglo 1: la pregunta, bajo su lado --------------------------------------

test('con la pregunta abierta, el rótulo de su lado sigue en la página, justo antes de ella, y dice que está abierta', async () => {
  const { pantalla } = await abrir(DEPTO);
  await tocar(boton(pantalla, 'Ampliar'));
  assert.deepEqual(['+ fila', '+ columna'].map((l) => boton(pantalla, l).getAttribute('aria-expanded')), ['false', 'false']);
  await tocar(boton(pantalla, '+ fila'));
  assert.deepEqual(enLoDeAmpliar(pantalla), ['+ fila', 'pregunta', '+ columna']);
  assert.match(texto(boton(pantalla, '+ fila')), /\+ fila \(3 casillas\) · 45/);         // lo que se compra, con lo que cuesta
  assert.equal(texto(preguntaDeAmpliar(pantalla), '.pregunta-texto'), '¿Ampliar por 45 monedas?');
  assert.deepEqual(['+ fila', '+ columna'].map((l) => boton(pantalla, l).getAttribute('aria-expanded')), ['true', 'false']);
});

test('dos toques seguidos en el botón de un lado no mandan nada: el segundo cierra la pregunta', async () => {
  const { pantalla, pedidos, documento } = await abrir(DEPTO);
  await tocar(boton(pantalla, 'Ampliar'));
  await tocar(boton(pantalla, '+ columna'));
  await tocar(boton(pantalla, '+ columna'));                             // donde cae el segundo clic: su mismo botón
  assert.equal(preguntaDeAmpliar(pantalla), null);
  assert.equal(boton(pantalla, '+ columna').getAttribute('aria-expanded'), 'false');
  assert.equal(documento.activeElement, boton(pantalla, '+ columna'));
  assert.equal(pedidos.length, 1);                                       // sólo la lectura de al entrar
});

test('al abrir la pregunta el foco va derecho a su texto, y se queda en ella si el panel se rehace con ella abierta', async () => {
  const { pantalla, servidor, documento } = await abrir(DEPTO);
  await tocar(boton(pantalla, 'Ampliar'));
  boton(pantalla, '+ fila').focus();
  const focos = historialDelFoco(documento);
  await tocar(boton(pantalla, '+ fila'));
  const suTexto = uno(preguntaDeAmpliar(pantalla), '.pregunta-texto');
  const enfocados = focos.filter((n) => n !== documento.body);
  assert.ok(enfocados.length > 0);
  assert.ok(enfocados.every((n) => n === suTexto), enfocados.map((n) => n.textContent));   // ni «Volver» ni otra cosa
  servidor.responde('GET departamento', { ...DEPTO, ampliar: { ancho: 50, fondo: 45 } });   // cambia sólo el otro lado
  await documento.dispara('visibilitychange');
  assert.match(texto(pantalla, '.ampliar'), /\+ columna \(3 casillas\) · 50/);               // el panel se rehízo…
  assert.equal(texto(preguntaDeAmpliar(pantalla), '.pregunta-texto'), '¿Ampliar por 45 monedas?');   // …con ella abierta
  assert.equal(documento.activeElement, uno(preguntaDeAmpliar(pantalla), '.pregunta-texto'));
  boton(preguntaDeAmpliar(pantalla), 'No').focus();
  servidor.responde('GET departamento', { ...DEPTO, ampliar: { ancho: 55, fondo: 45 } });
  await documento.dispara('visibilitychange');
  assert.equal(documento.activeElement, boton(preguntaDeAmpliar(pantalla), 'No'));          // en la misma parte
});

// --- lo que pidió el dueño en el plan de la puerta: un doble clic no cobra ------------------

// Lo que contesta crecer una fila cuando sale bien.
const CRECIO_UNA_FILA = { ok: true, clave: null, mensaje: 'Tu departamento ahora mide 3 × 4.', departamento: { ...DEPTO, fondo: 4, casillas: 12 }, estado: ESTADO };

test('un «Ampliar» que llega como segundo clic de un doble clic no cobra, y la pregunta sigue abierta; el clic siguiente, sí', async () => {
  const { pantalla, pedidos, servidor } = await abrir(DEPTO);
  servidor.responde('POST departamento/ampliar', CRECIO_UNA_FILA);
  const ampliados = () => pedidos.filter(([ruta]) => ruta === 'POST departamento/ampliar');
  await tocar(boton(pantalla, 'Ampliar'));
  await tocar(boton(pantalla, '+ columna'));                                             // una pregunta abierta en un lado
  await clicar(boton(pantalla, '+ fila'), 1);                                            // un doble clic en el otro: el primero la cambia de sitio…
  await clicar(boton(preguntaDeAmpliar(pantalla), 'Ampliar'), 2);                        // …y el segundo cae en «Ampliar»
  assert.equal(ampliados().length, 0);
  assert.equal(boton(pantalla, '+ fila').getAttribute('aria-expanded'), 'true');          // sigue abierta, la de ese lado
  assert.equal(texto(preguntaDeAmpliar(pantalla), '.pregunta-texto'), '¿Ampliar por 45 monedas?');
  await clicar(boton(preguntaDeAmpliar(pantalla), 'Ampliar'), 1);                        // un clic suelto confirma
  assert.deepEqual(ampliados().map(([, cuerpo]) => cuerpo.eje), ['fondo']);
});

test('con el teclado, «Ampliar» confirma como siempre', async () => {
  const { pantalla, pedidos, servidor } = await abrir(DEPTO);
  servidor.responde('POST departamento/ampliar', CRECIO_UNA_FILA);
  await tocar(boton(pantalla, 'Ampliar'));
  await tocar(boton(pantalla, '+ fila'));
  await clicar(boton(preguntaDeAmpliar(pantalla), 'Ampliar'), 0);                        // Enter o espacio
  assert.equal(pedidos.filter(([ruta]) => ruta === 'POST departamento/ampliar').length, 1);
});

// --- lo que decidió el dueño al ver el plan terminado: sin camino, no va -------------------

// Un 3 × 3 sin la cama ni la puerta, con macetas en (1, 2) y (2, 1): la esquina de delante, (2, 2),
// se pisa, pero los muebles la cierran; a las demás que se pisan se llega. Tú entras en esa esquina
// (y no sales de ahí) y Pelusa en (0, 2). Es la única casilla que se puede cerrar sin que un
// mueble alto quede pegado delante de ella: su silueta la rozaría y el toque sería del mueble.
const CON_LA_ESQUINA_CERRADA = {
  ...DEPTO,
  puestos: [{ ...LA_MACETA, x: 1, y: 2, giro: 0, casillas: [[1, 2]] },
    { ...LA_MACETA, id: 26, x: 2, y: 1, giro: 0, casillas: [[2, 1]] }],
};

test('tocar una casilla a la que no hay camino no mueve a tu avatar, ni caminando ni apareciendo, y no dice nada', async () => {
  for (const movimientoReducido of [false, true]) {
    const { pantalla, pedidos } = await abrir(CON_LA_ESQUINA_CERRADA, ESTADO, { movimientoReducido });
    assert.deepEqual(dondeEstas(pantalla), [2, 2]);                       // encerrado en la esquina
    await tocarCasilla(pantalla, 0, 0);
    assert.equal(cuadrosPendientes(), 0);                                // no echa a andar
    assert.deepEqual(dondeEstas(pantalla), [2, 2]);                       // ni aparece ahí
    assert.equal(menu(pantalla), null);
    assert.equal(texto(pantalla, '[role=status].aviso'), '');
    assert.equal(pedidos.length, 1);
  }
});

test('con menos movimiento, quien tiene camino aparece en su destino; quien no, no va', async () => {
  const { pantalla, servidor, documento } = await abrir({ ...CON_LA_ESQUINA_CERRADA, puestos: [] }, ESTADO, { movimientoReducido: true });
  await tocarCasilla(pantalla, 0, 2);                                    // de (2, 2), sin nada en medio
  assert.deepEqual(dondeEstas(pantalla), [0, 2]);
  assert.equal(cuadrosPendientes(), 0);                                  // no camina: aparece
  servidor.responde('GET departamento', CON_LA_ESQUINA_CERRADA);         // llegan las macetas: la esquina queda cerrada
  await documento.dispara('visibilitychange');
  assert.deepEqual(dondeEstas(pantalla), [0, 2]);
  await tocarCasilla(pantalla, 2, 2);
  assert.deepEqual(dondeEstas(pantalla), [0, 2]);                        // no va
});

test('mover a un gachamon marca sólo las casillas a las que tiene camino, y tocar una sin camino lo suelta sin moverlo', async () => {
  const { pantalla, pedidos } = await abrir(CON_LA_ESQUINA_CERRADA, ESTADO, { movimientoReducido: true });
  assert.deepEqual(dondeSePinto(pantalla, PELUSA.retrato), [0, 2]);
  await tocarA(pantalla, CON_LA_ESQUINA_CERRADA, 0);
  await tocar(boton(menu(pantalla), 'Mover'));
  const marcadas = casillasMarcadas(pantalla);
  assert.deepEqual(enOrden(marcadas.slice(0, -1)), [[0, 0], [0, 1], [1, 0], [1, 1], [2, 0]]);   // sin (2, 2), que los muebles cierran
  assert.deepEqual(marcadas.at(-1), [0, 2]);                             // y dónde está ella, elegida
  await tocarCasilla(pantalla, 2, 2);
  assert.equal(menu(pantalla), null);                                    // la suelta, como fuera de lo marcado
  assert.equal(texto(pantalla, '[role=status].aviso'), '');
  assert.deepEqual(dondeSePinto(pantalla, PELUSA.retrato), [0, 2]);       // y se queda donde estaba
  await tocarA(pantalla, CON_LA_ESQUINA_CERRADA, 0);
  await tocar(boton(menu(pantalla), 'Mover'));
  await tocarCasilla(pantalla, 1, 1);                                    // a una con camino, sí va (aparece)
  assert.deepEqual(dondeSePinto(pantalla, PELUSA.retrato), [1, 1]);
  assert.equal(pedidos.length, 1);
});

// --- la puerta: apareces en ella al entrar y por ella sales ---------------------------------

test('al entrar apareces en la puerta', async () => {
  const { pantalla } = await abrir(DEPTO);
  assert.deepEqual(dondeEstas(pantalla), [-0.6, 2]);                   // su umbral
});

test('sin puerta se entra como antes', async () => {
  const { pantalla } = await abrir(SIN_PUERTA);
  assert.deepEqual(dondeEstas(pantalla), [2, 2]);
  assert.equal(todos(pantalla, '.lista-puestos li').some((f) => /Salir/.test(f.textContent)), false);
});

test('desde la puerta se camina hacia adentro por la casilla de enfrente', async () => {
  const { pantalla } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 2, 2);
  await correrCuadros(5000);
  assert.deepEqual(dondeEstas(pantalla), [2, 2]);
});

test('con la entrada tapada te quedas en la puerta, y puedes mover lo que estorba', async () => {
  const tapada = conPuesto(DEPTO, { id: MACETA_ID, ...MACETA, nombre: 'Maceta', x: 0, y: 2, giro: 0, casillas: [[0, 2]] });
  const { pantalla, pedidos, servidor } = await abrir(tapada);
  await tocarCasilla(pantalla, 2, 2);
  await correrCuadros(5000);
  assert.deepEqual(dondeEstas(pantalla), [-0.6, 2]);                   // no va
  servidor.responde('POST departamento/poner', BIEN(conPuesto(DEPTO, { id: MACETA_ID, ...MACETA, nombre: 'Maceta', x: 2, y: 0, giro: 0, casillas: [[2, 0]] })));
  await construir(pantalla);                                             // desde la puerta, entrando al modo
  await tocarCasilla(pantalla, 0, 2); await tocar(boton(menu(pantalla), 'Mover')); await tocarCasilla(pantalla, 2, 0);
  assert.equal(pedidos.at(-1)[0], 'POST departamento/poner');
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  assert.deepEqual(dondeEstas(pantalla), [2, 2]);                      // ahora sí
});

test('el menú de la puerta trae mover, y nada más', async () => {
  const { pantalla } = await abrir(DEPTO);
  await construir(pantalla);
  await tocarTramo(pantalla, -1, 2);
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Puerta');
  assert.deepEqual(rotulos(menu(pantalla)), ['Mover']);
});

test('salir desde la puerta lleva al pueblo al momento', async () => {
  const { pantalla, seguido, pedidos } = await abrir(DEPTO);
  await tocarTramo(pantalla, -1, 2);                                    // viviendo, tocarla es salir
  assert.deepEqual(seguido.at(-1)[1], { vista: 'pueblo' });
  assert.equal(pedidos.filter(([ruta]) => ruta.startsWith('POST')).length, 0);
});

test('salir desde dentro camina hasta la puerta y entonces va al pueblo', async () => {
  const { pantalla, seguido } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  await tocarTramo(pantalla, -1, 2);
  assert.equal(seguido.length, 0);                                     // todavía va caminando
  await correrCuadros(5000);
  assert.deepEqual(seguido.at(-1)[1], { vista: 'pueblo' });
});

test('tocar otra cosa mientras caminas a la puerta cancela la salida', async () => {
  const { pantalla, seguido } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  await tocarTramo(pantalla, -1, 2);
  assert.equal(cuadrosPendientes(), 1);                                // echas a andar hacia ella
  await correrCuadros(100);
  await tocarCasilla(pantalla, 2, 1);
  await correrCuadros(5000);
  assert.equal(seguido.length, 0);
  assert.deepEqual(dondeEstas(pantalla), [2, 1]);
});

test('sin camino hasta la puerta no se sale y se dice', async () => {
  const { pantalla, seguido, servidor } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  // Las macetas te encierran en la esquina de delante; delante de la puerta no hay
  // nada (con un mueble delante, la prueba de «viviendo, la puerta se toca…»).
  const encerrado = [[1, 2], [2, 1]].reduce((d, [x, y], n) => conPuesto(d, { ...LA_MACETA, id: 30 + n, x, y, giro: 0, casillas: [[x, y]] }), DEPTO);
  servidor.responde('GET departamento', encerrado);
  await releer(pantalla);
  await tocarTramo(pantalla, -1, 2);
  await correrCuadros(5000);
  assert.equal(seguido.length, 0);
  assert.equal(texto(pantalla, '[role=status].aviso'), 'No hay camino hasta la puerta.');
  assert.deepEqual(dondeEstas(pantalla), [2, 2]);
});

test('con menos movimiento se sale sin caminar', async () => {
  const { pantalla, seguido } = await abrir(DEPTO, ESTADO, { movimientoReducido: true });
  await tocarCasilla(pantalla, 2, 2);
  await tocarTramo(pantalla, -1, 2);
  assert.deepEqual(seguido.at(-1)[1], { vista: 'pueblo' });
});

test('mover la puerta estando en ella te lleva con ella; estando dentro, no', async () => {
  // Al tramo 3 de la pared derecha, que da a (2, 0), libre.
  const movida = moverPuesto(DEPTO, PUERTA_ID, { x: 2, y: -1, casillas: [[2, -1]] });
  let { pantalla, pedidos, servidor } = await abrir(DEPTO);
  servidor.responde('POST departamento/poner', BIEN(movida));
  await construir(pantalla);                                            // viviendo, tocarla te sacaría
  await tocarTramo(pantalla, -1, 2); await tocar(boton(menu(pantalla), 'Mover')); await tocarTramo(pantalla, 2, -1);
  assert.deepEqual(pedidos.at(-1), ['POST departamento/poner', { mueble_id: PUERTA_ID, x: 2, y: -1, giro: 0 }]);
  assert.deepEqual(dondeEstas(pantalla), [2, -0.6]);
  ({ pantalla, servidor } = await abrir(DEPTO));
  servidor.responde('POST departamento/poner', BIEN(movida));
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  await construir(pantalla);
  await tocarTramo(pantalla, -1, 2); await tocar(boton(menu(pantalla), 'Mover')); await tocarTramo(pantalla, 2, -1);
  assert.deepEqual(dondeEstas(pantalla), [2, 2]);
});

test('en la lista, la puerta se mueve, pero no se gira ni se guarda; sin el dibujo se sale con «Pueblo»', async () => {
  const { pantalla, seguido } = await abrir(DEPTO);
  const fila_ = fila(pantalla, PUERTA_ID);
  assert.equal(texto(fila_, '.mueble-nombre'), 'Puerta, en la pared izquierda, tramo 3');
  assert.deepEqual(rotulos(fila_), ['Mover']);
  await tocar(boton(pantalla, 'Pueblo'));
  assert.deepEqual(seguido.at(-1)[1], { vista: 'pueblo' });
});

// El 3 × 3 de siempre, con su cama y su puerta, y macetas en (1, 2) y (2, 1): Pelusa
// entra en (0, 2), la casilla de enfrente de la puerta, y desde ahí, con tu avatar
// en (1, 1), sólo puede dar un paso a (0, 1) y volver. Si el paseo contara con la
// puerta, desde (0, 2) la puerta sería uno de sus dos pasos posibles.
const DELANTE_DE_LA_PUERTA = [[1, 2], [2, 1]]
  .reduce((d, [x, y], n) => conPuesto(d, { ...LA_MACETA, id: 30 + n, x, y, giro: 0, casillas: [[x, y]] }), DEPTO);

test('los gachamones no llegan a la puerta', async () => {
  const { pantalla } = await abrir(DELANTE_DE_LA_PUERTA, ESTADO, { azar: azarQueRecorre() });
  assert.deepEqual(dondeEstanLosGachamones(pantalla), [[0, 2]]);         // en la casilla de enfrente
  await tocarCasilla(pantalla, 1, 1); await correrCuadros(5000);          // tú entras y le dejas sitio
  assert.deepEqual(dondeEstas(pantalla), [1, 1]);
  for (let n = 0; n < 40; n += 1) {
    await correrReloj(9000);
    await correrCuadros(1000);                                          // y da los pasos que echó a andar
  }
  const pintada = dondeSePintaronLosGachamones(pantalla);
  const vista = new Set(pintada.map(String));
  assert.ok(vista.has('0,1') && vista.has('0,2'), [...vista].join(' '));  // paseó: fue a (0, 1) y volvió
  assert.ok(pintada.every(([i, j]) => i >= 0 && j >= 0), [...vista].join(' '));   // y nunca en la puerta ni en su umbral
  assert.equal(dondeEstanLosGachamones(pantalla).length, 1);
});

test('a un gachamon no se le puede llevar a la puerta', async () => {
  const { pantalla, pedidos, seguido } = await abrir(DEPTO, ESTADO, { movimientoReducido: true });
  assert.deepEqual(dondeSePinto(pantalla, PELUSA.retrato), [1, 2]);       // tú, en la puerta
  await tocarA(pantalla, DEPTO, 0);
  await tocar(boton(menu(pantalla), 'Mover'));
  const marcados = sitiosMarcados(pantalla);
  assert.deepEqual(enOrden(marcados.slice(0, -1)), [[0, 1], [0, 2], [1, 1], [2, 0], [2, 1], [2, 2]]);   // sin la puerta
  assert.deepEqual(marcados.at(-1), [1, 2]);                              // y dónde está ella, elegida
  await tocarTramo(pantalla, -1, 2);                                      // el tramo de la puerta
  assert.equal(menu(pantalla), null);                                     // la suelta, como fuera de lo marcado
  assert.deepEqual(sitiosMarcados(pantalla), []);
  assert.deepEqual(dondeSePinto(pantalla, PELUSA.retrato), [1, 2]);       // sin moverla
  assert.deepEqual(dondeEstas(pantalla), [-0.6, 2]);
  assert.equal(seguido.length, 0);                                        // y sin salir
  assert.equal(pedidos.length, 1);
});

// Los tramos que se ofrecen al mover la puerta de ese departamento, en el dibujo
// («Mover» en su menú: lo que se marca) y en la lista («¿Dónde?»), comprobando
// que son los mismos, con sus nombres. Dónde está ella se marca aparte, elegida.
async function tramosParaLaPuerta(depto) {
  const enElDibujo = await abrir(depto);
  await construir(enElDibujo.pantalla);
  await tocarTramo(enElDibujo.pantalla, -1, 2);
  await tocar(boton(menu(enElDibujo.pantalla), 'Mover'));
  const marcados = sitiosMarcados(enElDibujo.pantalla);
  assert.deepEqual(marcados.at(-1), [-1, 2]);                             // dónde está ella, elegida
  const enLaLista = await abrir(depto);
  await construir(enLaLista.pantalla);
  await tocar(boton(fila(enLaLista.pantalla, PUERTA_ID), 'Mover'));
  const ofrecidos = todos(enLaLista.pantalla, '.donde option').map((o) => o.textContent);
  assert.deepEqual(marcados.slice(0, -1).map(([x, y]) => nombreDelSitio(x, y)), ofrecidos);   // los mismos que en el dibujo
  return { marcados: enOrden(marcados.slice(0, -1)), ofrecidos };
}

test('al mover la puerta sólo se ofrecen los tramos con la entrada libre', async () => {
  // En `DEPTO` la cama tapa (0, 0) y (1, 0): de los tramos libres de las dos paredes
  // (menos el suyo), los dos primeros de la derecha y el primero de la izquierda dan a ella.
  const enDepto = await tramosParaLaPuerta(DEPTO);
  assert.deepEqual(enDepto.marcados, [[-1, 1], [2, -1]]);
  assert.deepEqual(enDepto.ofrecidos, ['pared derecha, tramo 3', 'pared izquierda, tramo 2']);
  // Con el cuadro colgado en el tramo 3 de la pared derecha, que da a (2, 0), libre: ni
  // el suyo ni el del cuadro.
  const conCuadro = await tramosParaLaPuerta(CON_UN_CUADRO_COLGADO);
  assert.deepEqual(conCuadro.marcados, [[-1, 1]]);
  assert.deepEqual(conCuadro.ofrecidos, ['pared izquierda, tramo 2']);
  // Con un mueble de bulto delante de cada uno de esos dos, no cabe en ningún sitio.
  const tapados = [[2, 0], [0, 1]].reduce((d, [x, y], n) => conPuesto(d, { ...LA_MACETA, id: 30 + n, x, y, giro: 0, casillas: [[x, y]] }), DEPTO);
  const { pantalla, pedidos } = await abrir(tapados);
  await construir(pantalla);
  await tocarTramo(pantalla, -1, 2);
  await tocar(boton(menu(pantalla), 'Mover'));
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Ahí no cabe.');
  assert.deepEqual(sitiosMarcados(pantalla), [[-1, 2]]);                  // nada que tocar: sólo ella, elegida
  await tocar(boton(fila(pantalla, PUERTA_ID), 'Mover'));                 // y en la lista, tampoco
  assert.equal(uno(pantalla, '.donde select'), null);
  assert.equal(pedidos.length, 1);
});

// --- lo que el encargo de la puerta dice y no prueba lo de arriba ---------------------------

test('entrando por la puerta se te ve pasar de su umbral a la casilla de enfrente, sin saltos', async () => {
  const { pantalla } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 0, 2);
  await correrCuadros(150);                                             // a medio paso
  const [i, j] = dondeEstas(pantalla);
  assert.ok(i > -0.6 && i < 0, String(i));
  assert.equal(j, 2);
});

test('con menos movimiento, sin camino tampoco se entra ni se sale: ni caminando ni apareciendo', async () => {
  const tapada = conPuesto(DEPTO, { id: MACETA_ID, ...MACETA, nombre: 'Maceta', x: 0, y: 2, giro: 0, casillas: [[0, 2]] });
  const desdeLaPuerta = await abrir(tapada, ESTADO, { movimientoReducido: true });
  await tocarCasilla(desdeLaPuerta.pantalla, 2, 2);
  assert.deepEqual(dondeEstas(desdeLaPuerta.pantalla), [-0.6, 2]);       // no entra
  const desdeDentro = await abrir(DEPTO, ESTADO, { movimientoReducido: true });
  await tocarCasilla(desdeDentro.pantalla, 2, 2);
  const encerrado = [[1, 2], [2, 1]].reduce((d, [x, y], n) => conPuesto(d, { ...LA_MACETA, id: 30 + n, x, y, giro: 0, casillas: [[x, y]] }), DEPTO);
  desdeDentro.servidor.responde('GET departamento', encerrado);           // la esquina de delante, cerrada
  await releer(desdeDentro.pantalla);
  await tocarTramo(desdeDentro.pantalla, -1, 2);
  assert.equal(desdeDentro.seguido.length, 0);                          // no sale
  assert.deepEqual(dondeEstas(desdeDentro.pantalla), [2, 2]);             // ni aparece en ella
  assert.equal(texto(desdeDentro.pantalla, '[role=status].aviso'), 'No hay camino hasta la puerta.');
});

test('mientras va una petición no se sale por la puerta', async () => {
  const { pantalla, seguido, servidor } = await abrir(DEPTO);
  const soltar = servidor.retiene('POST cuidar');
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Bañar'));          // un cuidado en camino
  await tocarTramo(pantalla, -1, 2);                                     // estás en ella: sin la petición, saldrías al momento
  await correrCuadros(5000);
  assert.equal(seguido.length, 0);
  await soltar({ ok: true, mensaje: 'Pelusa quedó reluciente.', espera: 600, monedas: 0, evoluciono: false, logros: [], gachamon: PELUSA, estado: ESTADO });
  await tocarTramo(pantalla, -1, 2);
  assert.deepEqual(seguido.at(-1)[1], { vista: 'pueblo' });
});

test('hacer otra cosa mientras caminas a la puerta (cuidar, tomar algo de los guardados) también cancela la salida', async () => {
  const { pantalla, seguido, servidor } = await abrir(DEPTO);
  servidor.responde('POST cuidar', { ok: true, mensaje: 'Pelusa quedó reluciente.', espera: 600, monedas: 0, evoluciono: false, logros: [], gachamon: PELUSA, estado: ESTADO });
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  await tocarTramo(pantalla, -1, 2);                                      // echas a andar hacia la puerta…
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Bañar'));
  await correrCuadros(5000);
  assert.equal(seguido.length, 0);
  assert.deepEqual(dondeEstas(pantalla), [-0.6, 2]);                     // llegó a la puerta, y se quedó
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  await tocarTramo(pantalla, -1, 2);
  await tocar(boton(pantalla, 'Guardados'));
  await tocar(boton(uno(pantalla, '.bandeja'), 'Cama sencilla'));
  await correrCuadros(5000);
  assert.equal(seguido.length, 0);
});

test('si la puerta cambia de sitio mientras estás en ella (en otra pestaña), sigues en ella; si estás dentro, no te mueves', async () => {
  const movida = moverPuesto(DEPTO, PUERTA_ID, { x: 2, y: -1, casillas: [[2, -1]] });
  const { pantalla, servidor } = await abrir(DEPTO);
  servidor.responde('GET departamento', movida);
  await releer(pantalla);
  assert.deepEqual(dondeEstas(pantalla), [2, -0.6]);
  await tocarCasilla(pantalla, 1, 1); await correrCuadros(5000);       // entras por la de enfrente, (2, 0)
  assert.deepEqual(dondeEstas(pantalla), [1, 1]);
  servidor.responde('GET departamento', DEPTO);
  await releer(pantalla);
  assert.deepEqual(dondeEstas(pantalla), [1, 1]);
});

test('la puerta no está entre los guardados', async () => {
  const { pantalla } = await abrir(DEPTO);
  await tocar(boton(pantalla, 'Guardados'));
  assert.deepEqual(todos(uno(pantalla, '.bandeja'), 'button').map((b) => texto(b, '.bandeja-nombre')), ['Cama sencilla × 1']);
  assert.deepEqual(todos(pantalla, '.lista-guardados li').map((f) => texto(f, '.mueble-nombre')), ['Cama sencilla']);
});

test('si dentro ya no queda casilla que se pise, te quedas en la puerta', async () => {
  const { pantalla, servidor } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  const lleno = [[2, 0], [0, 1], [1, 1], [2, 1], [0, 2], [1, 2], [2, 2]]
    .reduce((d, [x, y], n) => conPuesto(d, { ...LA_MACETA, id: 40 + n, x, y, giro: 0, casillas: [[x, y]] }), DEPTO);
  servidor.responde('GET departamento', lleno);
  await releer(pantalla);
  assert.deepEqual(dondeEstas(pantalla), [-0.6, 2]);
});

test('si lo que llega te para camino de la puerta, ya no sales, tampoco después', async () => {
  const { pantalla, seguido, servidor } = await abrir(DEPTO, ESTADO, { azar: () => 0 });
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  await tocarTramo(pantalla, -1, 2);                                      // echas a andar hacia la puerta…
  assert.equal(cuadrosPendientes(), 1);
  const lleno =[[2, 0], [0, 1], [1, 1], [2, 1], [0, 2], [1, 2], [2, 2]]
    .reduce((d, [x, y], n) => conPuesto(d, { ...LA_MACETA, id: 40 + n, x, y, giro: 0, casillas: [[x, y]] }), DEPTO);
  servidor.responde('GET departamento', lleno);
  await releer(pantalla);                                                 // …la pieza se llena y quedas en la puerta, sin llegar
  servidor.responde('GET departamento', DEPTO);
  await releer(pantalla);                                                 // se vacía
  await correrReloj(9000); await correrCuadros(5000);                     // y un gachamon da un paso
  assert.equal(seguido.length, 0);
  assert.deepEqual(dondeEstas(pantalla), [-0.6, 2]);
});

// --- el modo construcción: viviendo, tocar un mueble hace su acción; construyendo, se mueve --

const CUIDADO_HECHO = { ok: true, mensaje: 'Pelusa quedó reluciente.', espera: 600, monedas: 0, evoluciono: false, logros: [], gachamon: PELUSA, estado: ESTADO };

test('se entra en modo normal, con «Construir» bajo la pieza', async () => {
  const { pantalla } = await abrir(DEPTO);
  const alModo = boton(pantalla, 'Construir');
  assert.notEqual(alModo, null);
  assert.equal(boton(pantalla, 'Listo'), null);
  assert.ok(alModo.classList.contains('boton-construir'));
  assert.equal(texto(alModo, 'span[aria-hidden=true]'), '🔨');            // el emoji no se lee
  const pieza = uno(pantalla, '.pieza');
  assert.equal(pieza.hidden, false);
  assert.equal(pieza.classList.contains('construyendo'), false);
  assert.equal(uno(pantalla, '.rotulo-de-obra').hidden, true);
  // Dentro de la pieza, entre el dibujo y la línea del tamaño.
  const partes = ['pieza-escenario', 'boton-construir', 'pieza-linea'];
  assert.deepEqual(todos(pieza, partes.map((c) => `.${c}`).join(', ')).map((n) => partes.find((c) => n.classList.contains(c))), partes);
});

test('«Construir» entra al modo y «Listo» lo termina', async () => {
  const { pantalla, documento, pedidos } = await abrir(DEPTO);
  const pieza = uno(pantalla, '.pieza');
  const rotulo = uno(pantalla, '.rotulo-de-obra');
  const alModo = boton(pantalla, 'Construir');
  alModo.focus();
  const focos = historialDelFoco(documento);
  await tocar(alModo);
  assert.equal(boton(pantalla, 'Listo'), alModo);                        // el mismo botón, que ahora dice otra cosa
  assert.equal(boton(pantalla, 'Construir'), null);
  assert.equal(texto(alModo, 'span[aria-hidden=true]'), '✔');
  assert.equal(pieza.classList.contains('construyendo'), true);
  assert.equal(rotulo.hidden, false);
  assert.equal(texto(rotulo), 'Modo construcción');
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Toca un mueble para moverlo, girarlo o guardarlo.');
  assert.equal(documento.activeElement, alModo);
  await tocar(alModo);
  assert.equal(boton(pantalla, 'Construir'), alModo);
  assert.equal(boton(pantalla, 'Listo'), null);
  assert.equal(texto(alModo, 'span[aria-hidden=true]'), '🔨');
  assert.equal(pieza.classList.contains('construyendo'), false);
  assert.equal(rotulo.hidden, true);
  assert.equal(texto(pantalla, '[role=status].aviso'), '');              // lo de entrar ya no se dice
  assert.equal(texto(pantalla, '.solo-lector[role=status]'), 'Modo construcción terminado.');
  assert.equal(documento.activeElement, alModo);
  assert.ok(focos.every((n) => n === alModo), focos.map((n) => n.textContent));   // el foco nunca se fue a otro sitio
  assert.equal(pedidos.length, 1);                                       // el modo no se manda
});

test('viviendo, tocar un mueble no lo elige', async () => {
  const { pantalla, pedidos } = await abrir(CON_MACETA);
  await tocarA(pantalla, CON_MACETA, 0);                                // Pelusa, con su menú: deja de estarlo
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Pelusa');
  for (const [i, j] of [[2, 2], [0, 0]]) {                              // la maceta y la cama (en (1, 0) se toca a Pelusa, delante)
    await tocarCasilla(pantalla, i, j);
    assert.equal(menu(pantalla), null, `${i}, ${j}`);
    assert.deepEqual(casillasMarcadas(pantalla), []);
    assert.deepEqual(dondeEstas(pantalla), [-0.6, 2]);                  // no se mueve: sigue en la puerta
    assert.equal(cuadrosPendientes(), 0);                               // ni echa a andar
  }
  assert.equal(pedidos.length, 1);
  const colgado = await abrir(CON_UN_CUADRO_COLGADO);
  await tocarTramo(colgado.pantalla, 2, -1);                            // el cuadro
  assert.equal(menu(colgado.pantalla), null);
  assert.deepEqual(sitiosMarcados(colgado.pantalla), []);
  assert.deepEqual(dondeEstas(colgado.pantalla), [-0.6, 2]);
  assert.equal(cuadrosPendientes(), 0);
});

test('viviendo, lo que se pisa se camina y no se elige', async () => {
  const conFelpudo = conPuesto(DEPTO, { id: FELPUDO_ID, ...FELPUDO, x: 0, y: 2, giro: 0, casillas: [[0, 2]] });
  const { pantalla } = await abrir(conFelpudo);
  await tocarA(pantalla, conFelpudo, 0);                                // Pelusa, con su menú: deja de estarlo
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Pelusa');
  await tocarCasilla(pantalla, 0, 2);
  assert.equal(menu(pantalla), null);
  await correrCuadros(1000);
  assert.deepEqual(dondeEstas(pantalla), [0, 2]);
  assert.deepEqual(casillasMarcadas(pantalla), []);
});

test('viviendo, tocar la puerta te saca', async () => {
  const { pantalla, seguido, pedidos } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);        // dentro, en la esquina de delante
  await tocarTramo(pantalla, -1, 2);
  assert.equal(menu(pantalla), null);                                   // sin menú
  assert.equal(seguido.length, 0);                                      // caminas hasta ella…
  await correrCuadros(5000);
  assert.equal(seguido.length, 1);                                      // …y al llegar, sales
  const conPueblo = await abrir(DEPTO);
  await tocar(boton(conPueblo.pantalla, 'Pueblo'));
  assert.deepEqual(seguido, conPueblo.seguido);                         // lo mismo que con «Pueblo»
  assert.equal(pedidos.filter(([ruta]) => ruta.startsWith('POST')).length, 0);
});

test('viviendo, en la puerta y tocándola, sales al momento', async () => {
  const { pantalla, seguido } = await abrir(DEPTO);                     // recién entrado: estás en ella
  await tocarTramo(pantalla, -1, 2);
  assert.deepEqual(seguido.at(-1)[1], { vista: 'pueblo' });             // sin correr ningún cuadro
});

test('viviendo, la puerta se toca aunque tenga un mueble delante, y sin camino no se sale', async () => {
  const tapada = conPuesto(DEPTO, { id: MACETA_ID, ...MACETA, nombre: 'Maceta', x: 0, y: 2, giro: 0, casillas: [[0, 2]] });
  const { pantalla, seguido, servidor } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  servidor.responde('GET departamento', tapada);                        // la maceta, en la casilla de enfrente
  await releer(pantalla);
  await tocarTramo(pantalla, -1, 2);
  assert.equal(menu(pantalla), null);                                   // la maceta no se elige: el toque es de la puerta
  assert.equal(texto(pantalla, '[role=status].aviso'), 'No hay camino hasta la puerta.');
  await correrCuadros(5000);
  assert.equal(seguido.length, 0);
  assert.deepEqual(dondeEstas(pantalla), [2, 2]);
  await construir(pantalla);                                            // construyendo, ese mismo toque es de la maceta:
  await tocarTramo(pantalla, -1, 2);                                    // está delante de verdad
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Maceta');
});

test('construyendo, tocar la puerta no saca: sale su menú, sólo con «Mover»', async () => {
  const { pantalla, seguido } = await abrir(DEPTO);                     // estás en ella: viviendo, saldrías al momento
  await construir(pantalla);
  await tocarTramo(pantalla, -1, 2);
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Puerta');
  assert.deepEqual(rotulos(menu(pantalla)), ['Mover']);
  await correrCuadros(5000);
  assert.equal(seguido.length, 0);
});

test('construyendo, un mueble trae Mover, Girar y Guardar, y lo de pared no trae Girar', async () => {
  const { pantalla } = await abrir(CON_UN_CUADRO_COLGADO);
  await construir(pantalla);
  await tocarCasilla(pantalla, 0, 0);
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Cama sencilla');
  assert.deepEqual(rotulos(menu(pantalla)), ['Mover', 'Girar', 'Guardar']);
  await tocarTramo(pantalla, 2, -1);
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Cuadro');
  assert.deepEqual(rotulos(menu(pantalla)), ['Mover', 'Guardar']);
});

test('construyendo, a un gachamon no se le toca: el toque va al mueble de detrás', async () => {
  const [i, j] = dondeEsta(CON_DOS, 1);                                 // Rulo, en (2, 1): delante de la cama
  const viviendo = await abrir(CON_DOS, ESTADO, { movimientoReducido: true });
  assert.deepEqual(dondeSePinto(viviendo.pantalla, RULO.retrato), [i, j]);
  await tocarSobre(viviendo.pantalla, i, j, 1);                         // a la altura de su cuerpo
  assert.equal(texto(menu(viviendo.pantalla), '.menu-nombre'), 'Rulo');  // viviendo, el toque es suyo
  const { pantalla } = await abrir(CON_DOS, ESTADO, { movimientoReducido: true });
  await construir(pantalla);
  await tocarSobre(pantalla, i, j, 1);                                  // el mismo toque, construyendo
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Cama sencilla');
  assert.doesNotMatch(texto(pantalla, '.ficha-elegido'), /Rulo/);
  const [pi, pj] = dondeEsta(CON_DOS, 0);                               // Pelusa, en (1, 2): detrás, sólo suelo
  await tocarCasilla(pantalla, pi, pj);
  assert.equal(menu(pantalla), null);
  assert.deepEqual(dondeEstas(pantalla), [pi, pj]);                     // caminas hasta ahí (aparece)
  assert.match(texto(pantalla, '.ficha-elegido'), /Pelusa/);
});

test('entrar al modo deja de elegir al gachamon y suelta lo que llevas', async () => {
  const conMenu = await abrir(CON_DOS);
  await tocarA(conMenu.pantalla, CON_DOS, 1);
  assert.equal(texto(menu(conMenu.pantalla), '.menu-nombre'), 'Rulo');
  await construir(conMenu.pantalla);
  assert.equal(menu(conMenu.pantalla), null);
  assert.deepEqual(casillasMarcadas(conMenu.pantalla), []);              // ni su marca
  assert.match(texto(conMenu.pantalla, '.ficha-elegido'), /Rulo/);       // su ficha sigue a la derecha
  const { pantalla, pedidos } = await abrir(CON_DOS, ESTADO, { movimientoReducido: true });
  await tocarA(pantalla, CON_DOS, 1);
  await tocar(boton(menu(pantalla), 'Mover'));                           // Rulo, en la mano
  assert.ok(casillasMarcadas(pantalla).length > 1);
  await construir(pantalla);
  assert.deepEqual(casillasMarcadas(pantalla), []);                      // nada marcado
  assert.equal(menu(pantalla), null);
  assert.equal(texto(pantalla, '[role=status].aviso'), 'Toca un mueble para moverlo, girarlo o guardarlo.');
  await tocarCasilla(pantalla, 0, 2);                                    // el toque siguiente ya no lo lleva: caminas tú
  assert.deepEqual(dondeEstas(pantalla), [0, 2]);
  assert.deepEqual(dondeSePinto(pantalla, RULO.retrato), dondeEsta(CON_DOS, 1));
  assert.equal(pedidos.length, 1);
});

test('«Listo» suelta lo que llevas y cierra el menú', async () => {
  const { pantalla, pedidos } = await abrir(DEPTO);
  await construir(pantalla);
  await tocarCasilla(pantalla, 0, 0);                                    // la cama, con su menú
  await terminar(pantalla);
  assert.equal(menu(pantalla), null);
  assert.deepEqual(casillasMarcadas(pantalla), []);
  await construir(pantalla);
  await tocarCasilla(pantalla, 0, 0);
  await tocar(boton(menu(pantalla), 'Mover'));                           // la cama, en la mano
  assert.ok(casillasMarcadas(pantalla).length > 1);
  await terminar(pantalla);
  assert.deepEqual(casillasMarcadas(pantalla), []);                      // nada marcado
  assert.equal(menu(pantalla), null);
  assert.equal(texto(pantalla, '[role=status].aviso'), '');              // ni la indicación de dónde tocar
  await tocarCasilla(pantalla, 2, 1);                                    // el toque siguiente es caminar, no poner
  assert.equal(pedidos.filter(([ruta]) => ruta.startsWith('POST')).length, 0);
});

test('entrar al modo cancela la salida', async () => {
  const { pantalla, seguido } = await abrir(DEPTO);
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  await tocarTramo(pantalla, -1, 2);                                     // echas a andar hacia la puerta…
  await correrCuadros(100);
  await construir(pantalla);                                             // …y a medio camino entras al modo
  await correrCuadros(5000);
  assert.equal(seguido.length, 0);
  assert.deepEqual(dondeEstas(pantalla), [-0.6, 2]);                     // llegas a la puerta, y te quedas
});

test('con una petición en camino no se cambia de modo', async () => {
  const { pantalla, servidor } = await abrir(DEPTO);
  const pieza = uno(pantalla, '.pieza');
  const alModo = boton(pantalla, 'Construir');
  const soltar = servidor.retiene('POST cuidar');
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Bañar'));          // un cuidado sin contestar
  assert.equal(alModo.getAttribute('aria-disabled'), 'true');
  await tocar(alModo);
  assert.equal(boton(pantalla, 'Listo'), null);                          // no entra
  assert.equal(pieza.classList.contains('construyendo'), false);
  assert.equal(uno(pantalla, '.rotulo-de-obra').hidden, true);
  await soltar(CUIDADO_HECHO);
  assert.equal(alModo.getAttribute('aria-disabled'), null);
  await construir(pantalla);
  const otra = servidor.retiene('POST cuidar');
  await tocar(boton(uno(pantalla, '.ficha-elegido'), 'Jugar'));
  assert.equal(alModo.getAttribute('aria-disabled'), 'true');
  await tocar(alModo);
  assert.equal(boton(pantalla, 'Construir'), null);                      // ni sale
  assert.equal(pieza.classList.contains('construyendo'), true);
  assert.equal(texto(pantalla, '.solo-lector[role=status]'), '');
  await otra(CUIDADO_HECHO);
  assert.equal(alModo.getAttribute('aria-disabled'), null);
});

test('la relectura no te saca del modo', async () => {
  const { pantalla, servidor } = await abrir(DEPTO);
  await construir(pantalla);
  await tocarCasilla(pantalla, 0, 0);
  servidor.responde('GET departamento', CON_MACETA);                     // llega otra pieza, con la cama donde estaba
  await releer(pantalla);
  assert.equal(texto(pantalla, '.pieza-linea').startsWith('3 × 3 · 3 de 9'), true);
  assert.equal(uno(pantalla, '.pieza').classList.contains('construyendo'), true);
  assert.notEqual(boton(pantalla, 'Listo'), null);
  assert.equal(texto(menu(pantalla), '.menu-nombre'), 'Cama sencilla');
});

test('elegir a un gachamon desde la lista cancela la salida', async () => {
  const { pantalla, seguido } = await abrir(CON_DOS);
  await tocarCasilla(pantalla, 2, 2); await correrCuadros(5000);
  await tocarTramo(pantalla, -1, 2);                                     // echas a andar hacia la puerta…
  await correrCuadros(100);
  await tocar(boton(uno(pantalla, '.lista-gachamones'), 'Rulo'));        // …y a medio camino eliges a Rulo en la lista
  await correrCuadros(5000);
  assert.equal(seguido.length, 0);
  assert.match(texto(pantalla, '.ficha-elegido'), /Rulo/);
  assert.deepEqual(dondeEstas(pantalla), [-0.6, 2]);                     // llegas a la puerta, y te quedas
});
