// Tu casa: la pieza de tu departamento, en vista isométrica por casillas, con
// sus muebles, tu avatar y tus gachamones, que caminan por ella.
//
// `departamento(contenedor, estado, seguir, { azar, llegando })` pide la pieza
// al servidor (`GET departamento`) al entrar, y la pinta en su lienzo; debajo,
// una línea dice cómo está. Cada 30 segundos y al volver a la pestaña la
// vuelve a pedir, y con ella el estado (`GET estado`), como el lugar: con él
// se renuevan los saldos y lo que dice el que sale contigo. Al
// entrar, tú y tus gachamones os repartís por los sitios de entrada (tú, el
// primero; ellos, en el orden en que llegan). Tocar una casilla que se pisa
// lleva a tu avatar hasta ella, de casilla en casilla; con menos movimiento,
// aparece ahí. Tus gachamones dan un paso solos de vez en cuando (cuándo y
// hacia dónde lo dice `azar`, que se inyecta; si no, `Math.random`), salvo
// con menos movimiento o mientras llevas algo en la mano. Dónde está parado
// cada uno es sólo del dibujo: no se guarda ni se manda. Si lo que llega pide
// otra pantalla (ya no estás en tu casa, ya no hay sesión) se lo pasa a
// `seguir`; sin ningún gachamon, tu casa se sigue viendo.
//
// Los muebles y los gachamones se tocan, sin modos: tocar uno lo elige (se
// marca dónde está) y encima sale su menú: el de un mueble, con «Mover»,
// «Girar» y «Guardar»; el de un gachamon, con «Mover» y «Acariciar». Lo que
// llevas en la mano (el mueble que mueves, el que sacas de la bandeja de
// «Guardados», bajo la pieza, o el gachamon que mueves) marca dónde va, y el
// toque siguiente dice dónde: en un sitio marcado se pone (el gachamon camina
// hasta ahí, y eso no se manda); en cualquier otro, se suelta. «Ampliar»
// cambia lo de la derecha por lo que cuesta crecer por cada lado; tocar un
// lado no cobra: pregunta antes, como la Tienda.
//
// A la derecha (`plantel.js`), la ficha del último gachamon que tocaste —al
// entrar, la del que sale contigo—, con sus cuidados, «Acariciar», «Ver
// ficha» y «Salir con …», y «A todos». Cuidarlo y acariciarlo se mandan con su
// id, y se avisa como en el lugar (`cuidados.js`); «A todos» vuelve a leer la
// pieza, y «Salir con …» la trae. El que sale contigo lleva su marca, y su
// globo sale sobre él, como en el lugar; con `llegando` (se acaba de llegar
// caminando), el primero sale enseguida y habla del lugar, salvo que
// necesite algo. Lo que flota sobre la pieza (el
// globo, los corazones, la ganancia, la evolución y las medallas) lo arma
// `flotantes.js`.
//
// Debajo de todo, y siempre a la vista, la lista (`lista.js`): lo mismo que se
// hace en el dibujo, con botones, para quien no usa el dibujo. Elegir ahí a un
// gachamon es tocarlo sin su menú; «Mover», «Poner», «Girar» y «Guardar» hacen
// lo mismo que el menú y la bandeja, y lo que sale bien sin decirse con texto
// (poner, mover, girar, guardar) se le vuelve a decir a quien no ve el dibujo:
// cómo quedó la pieza. El foco no se pierde: vuelve a ese mismo mueble, en la
// lista donde haya quedado.
//
// El servidor manda: la pieza se pinta como llega, y lo que se calcula aquí
// (por dónde se camina, qué se tocó, qué cabe dónde) sirve sólo para dibujar y
// para no proponer lo imposible. Poner, guardar, salir y acariciar se mandan
// una vez; cada cuidado, que mueve monedas, lleva un evento por toque (el
// mismo en sus reintentos), y ampliar, el de lo que se ve (el lado y lo que
// mide la pieza: el mismo hasta que crece). Lo que sale bien no se dice: se ve;
// ampliar, los cuidados, salir y lo que no se puede dicen la frase del
// servidor; sin respuesta, se dice y la pieza se vuelve a leer. Mientras una
// petición va, lo que la mandó espera y no sale otra. El lienzo sólo se mira
// (`aria-hidden`); los menús, la bandeja, la ficha, lo de ampliar y la lista
// son botones de verdad, y lo que no se puede usar lleva `aria-disabled`. Todo
// texto entra por `el` o por `textContent`. Lo que corre (el cuadro de
// animación, los relojes, la relectura y los oyentes) se detiene al salir, y
// una respuesta que llega tarde no pinta; una lectura que se tiró por una
// acción más nueva se vuelve a pedir al acabarla. Lo que devuelve la pantalla
// no acaba mientras se está en ella: lo que reviente al prepararla o al pintar
// lo que llega lo hace fallar, y `principal.js` lo lleva a la avería.

import { conReintentos, nuevoEvento, pedir } from './api.js';
import { cargar, lienzoDePieza, olvidarLasQueFaltan } from './arte.js';
import {
  MONEDAS, cabeceraConSaldos, cajaDePregunta, hayQueDecidirDeNuevo, listaQueSePide, mensajeDe, zonaDeAviso,
} from './articulos.js';
import { cargarAvatar, poseAlCaminar } from './avatar.js';
import {
  camino, dondeCabe, giroParaPoner, libreMasCercana, lineaDeEstado, noSePisan, pasoSuelto, sitiosDeEntrada,
} from './casillas.js';
import { trasAcariciar, trasCuidar } from './cuidados.js';
import { el } from './dom.js';
import { loQueFlota } from './flotantes.js';
import { cuantoOcupa, listaDelDepartamento } from './lista.js';
import { ofreceElDepartamento, siguiente } from './pantallas.js';
import { dibujarPieza, rutasDeLaPieza } from './pieza.js';
import { panelDelPlantel } from './plantel.js';
import {
  cajaDelGachamon, cajaDelMueble, casillaEn, medir, queSeToco, tramoEn,
} from './proyeccion.js';

const VISTA = 'departamento';
const PEDIR_CADA_MS = 30_000;
const DENSIDAD_MAXIMA = 3;
// Lo que anda tu avatar, y lo que anda un gachamon, en casillas por segundo.
const CASILLAS_POR_SEGUNDO = 3;
const PASOS_DEL_GACHAMON = 2;
// Cada cuánto da un paso solo alguno de tus gachamones: entre 4 y 9 segundos.
const UN_PASEO_CADA_MS = [4_000, 9_000];
// El salto de un gachamon al que se cuida: lo que dura y lo que sube, en anchos de casilla.
const UN_SALTO_DURA_S = 0.45;
const ALTURA_DEL_SALTO = 0.22;
// Las cuatro posiciones de un mueble.
const GIROS = 4;
// Lo de pared va en las paredes; lo demás, en el suelo.
const PARED = 'pared';
// Lo que dura otro aviso mientras llevas algo en la mano, antes de que vuelva
// la indicación de dónde tocar: lo mismo que dura cualquier aviso.
const UN_AVISO_DURA_MS = 6_000;
// El ícono de cada mueble de la bandeja, en píxeles de pantalla.
const LADO_DEL_ICONO = 40;
// Lo que el menú deja hasta el mueble y hasta el borde de la pieza, en píxeles.
const MARGEN_DEL_MENU = 6;

const CARGANDO = 'Cargando tu departamento…';
const SIN_RESPUESTA = 'No hubo respuesta. Revisa tu conexión.';
const TOCA_LA_CASILLA = 'Toca la casilla donde lo quieres.';
const TOCA_LA_PARED = 'Toca la pared donde lo quieres.';
const NO_CABE = 'Ahí no cabe.';
const ROTULO_DE_GUARDADOS = 'Guardados · toca uno y después una casilla';
const NADA_GUARDADO = 'No queda nada guardado.';
const ROTULO_DE_AMPLIAR = 'Ampliar el departamento';
const YA_NO_CRECE = 'Tu departamento ya no puede crecer más.';
// La pregunta antes de crecer, como la de la Tienda: el coste es el que manda
// el servidor, dicho con la palabra («45 monedas», «1 moneda»).
const preguntaDeAmpliar = (coste) => `¿Ampliar por ${MONEDAS.cuantas(coste)}?`;

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

// Mientras se está aquí hay sesión y la cuenta ya no es nueva, así que la
// pantalla la decide sólo el estado, con la regla de siempre; pero sin ningún
// gachamon tu casa se sigue viendo mientras estés en ella: el huevo es cosa de
// la entrada, y a esta pantalla se llega con uno.
function pideOtraPantalla(estado) {
  const toca = siguiente(true, { estado: 'en juego' }, estado, VISTA);
  if (toca === 'huevo') return !ofreceElDepartamento(estado.lugar);
  return toca !== VISTA;
}

// El retrato de un gachamon no es una pieza del contrato: es la dirección que
// trae su ficha. Nunca falla: `{ruta, imagen}`, con `imagen` en `null` si no
// cargó (se pinta su recuadro).
function cargarRetrato(direccion) {
  return new Promise((listo) => {
    const imagen = new Image();
    imagen.onload = () => listo({ ruta: direccion, imagen });
    imagen.onerror = () => listo({ ruta: direccion, imagen: null });
    imagen.src = direccion;
  });
}

// Alguien que camina por la pieza en esa casilla, a tantas casillas por
// segundo: dónde está (con decimales a medio paso), las casillas que le quedan
// por pisar y si mira a la izquierda. `null` si no hay casilla.
function caminanteEn(sitio, porSegundo) {
  return sitio ? { i: sitio[0], j: sitio[1], ruta: [], espejo: false, porSegundo } : null;
}

export function departamento(contenedor, estado, seguir, { azar = Math.random, llegando = false } = {}) {
  // El arte que no cargó en otra pantalla se pide de nuevo.
  olvidarLasQueFaltan();
  const menosMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)');
  const quieto = () => menosMovimiento.matches;

  let vivo = true;
  // Lo que devuelve la pantalla no acaba mientras se está en ella: acaba bien
  // al dejarla, y falla si algo revienta al preparar la pieza o al pintar lo
  // que llega después (`reventar`); `principal.js` lo lleva a la avería.
  let terminar;
  const mientrasSeVe = new Promise((bien, mal) => { terminar = { bien, mal }; });
  const oyentes = new AbortController();
  const { signal } = oyentes;
  let observador = null;
  let cuadroPedido = null;
  let cadaTanto = null;
  let cadaSegundo = null;
  // Lo que se hace al rato (el globo, los paseos, lo que se borra solo), para pararlo todo de una vez.
  const temporizadores = new Set();

  function luego(ms, hacer) {
    const marca = setTimeout(() => {
      temporizadores.delete(marca);
      if (sigueAqui()) hacer();
    }, ms);
    temporizadores.add(marca);
    return marca;
  }

  function cancelar(marca) {
    clearTimeout(marca);
    temporizadores.delete(marca);
  }

  // --- la cabecera, la pieza, lo que se dice y lo de la derecha --------------------------

  const { cabecera, titulo, ponerSaldos } = cabeceraConSaldos('📍', estado.lugar.nombre);

  const lienzo = el('canvas', { class: 'pieza-lienzo', 'aria-hidden': 'true' });
  // El menú de lo elegido va encima del lienzo, junto a él; encima, lo que
  // flota: el globo, sobre el que sale contigo, y la evolución y las medallas.
  // La ganancia asoma bajo el saldo.
  const menu = el('div', { class: 'menu-de-la-pieza', role: 'group', hidden: true });
  const escenario = el('div', { class: 'pieza-escenario' }, lienzo, menu);
  const flota = loQueFlota({
    escenario,
    luego,
    cancelar,
    azar,
    puedeHablar,
    dondeHabla,
    globos: () => actual.globos,
  });
  escenario.append(flota.globo, flota.celebracion, flota.medallas);
  const saldoDeMonedas = cabecera.querySelector('.saldo');
  if (saldoDeMonedas) saldoDeMonedas.append(flota.ganancia);
  const linea = el('p', { class: 'pieza-linea' });
  const bandeja = el('div', { class: 'bandeja', id: 'departamento-bandeja', hidden: true });
  // Mientras no llega, en su lugar se lee la espera (o por qué no llegó).
  const pieza = el('div', { class: 'pieza', hidden: true }, escenario, linea, bandeja);
  const espera = el('div', { class: 'espera-tienda' });

  const aviso = zonaDeAviso();
  aviso.nodo.classList.add('aviso');
  const { avisar } = aviso;
  // Cuándo vuelve la indicación de dónde tocar tras otro aviso (ver `decir`).
  let volverAIndicar = null;

  const conIcono = (clase, icono, texto, atributos = {}) => el('button', { type: 'button', class: clase, ...atributos },
    el('span', { 'aria-hidden': 'true' }, icono), texto);
  const aLosGuardados = conIcono('boton boton-guardados', '📦', 'Guardados',
    { 'aria-expanded': 'false', 'aria-controls': 'departamento-bandeja' });
  const alAmpliar = conIcono('boton boton-ampliar', '📐', 'Ampliar');
  const aLaMochila = conIcono('boton boton-mochila', '🎒', 'Mochila');
  const alPueblo = conIcono('boton boton-pueblo', '🗺️', 'Pueblo');
  // Guardados y Ampliar son de la pieza: se ven cuando llega, como la ficha
  // del elegido y «A todos», que van arriba.
  const deLaPieza = el('div', { class: 'acciones-departamento', hidden: true }, aLosGuardados, alAmpliar);
  const panel = panelDelPlantel({
    cuidar,
    acariciar: (boton) => {
      const g = elVisto();
      if (g) acariciar(g.id, boton);
    },
    salir: salirCon,
    verFicha: verLaFicha,
    aTodos: cuidarATodos,
  });
  const delPlantel = el('div', { class: 'plantel-departamento', hidden: true }, panel.ficha, panel.aTodos);
  const derecha = el('div', { class: 'lado-departamento' },
    delPlantel, deLaPieza, el('div', { class: 'salidas-lugar' }, aLaMochila, alPueblo));
  const panelAmpliar = el('div', { class: 'ampliar', hidden: true });
  // La lista, como la ficha: se ve cuando llega la pieza.
  const lista = listaDelDepartamento({
    ver: verDesdeLaLista,
    sitios: dondeVa,
    noCabe: () => decir(NO_CABE, true),
    poner: ponerDesdeLaLista,
    girar,
    guardar,
  });
  lista.nodo.hidden = true;

  // Lo que contesta el juego va al final, después de la lista: su regla
  // pegajosa lo deja al pie de la ventana, como en la Tienda, se actúe desde
  // donde se actúe.
  const cuerpo = el('div', { class: 'cuerpo cuerpo-departamento' },
    espera, pieza, derecha, panelAmpliar, lista.nodo, aviso.nodo);
  contenedor.append(cabecera, cuerpo);

  function parar() {
    vivo = false;
    if (cuadroPedido !== null) cancelAnimationFrame(cuadroPedido);
    cuadroPedido = null;
    clearInterval(cadaTanto);
    clearInterval(cadaSegundo);
    clearTimeout(volverAIndicar);
    for (const marca of temporizadores) clearTimeout(marca);
    temporizadores.clear();
    aviso.parar();
    oyentes.abort();
    if (observador) observador.disconnect();
    terminar.bien();
  }

  // Algo reventó al pintar: la pantalla no se queda a medias; falla lo que
  // devuelve (y llega a la avería) y se para todo.
  function reventar(error) {
    terminar.mal(error);
    parar();
  }

  // Lo que llega se pinta con `pintar()`; si al pintarlo algo revienta, no se
  // lo traga nadie: llega a la avería, como en la primera carga.
  function pintarLoQueLlega(pintar) {
    try {
      pintar();
    } catch (error) {
      reventar(error);
    }
  }

  // Deja la pantalla y que se decida otra: con el estado que llegó, o
  // preguntando todo otra vez.
  function irse(estadoNuevo) {
    parar();
    seguir(estadoNuevo);
  }

  // Si la pantalla ya no está en la página (se pintó otra), se para todo.
  function sigueAqui() {
    if (vivo && !cuerpo.isConnected) parar();
    return vivo;
  }

  // El estado del juego, el último que llegó: con él se sale al pueblo o a la mochila.
  let actual = estado;

  aLaMochila.addEventListener('click', () => {
    parar();
    seguir(actual, { vista: 'mochila' });
  }, { signal });
  alPueblo.addEventListener('click', () => {
    parar();
    seguir(actual, { vista: 'pueblo' });
  }, { signal });

  // Cada estado que llega se pregunta lo mismo que al entrar: si ya no toca
  // esta pantalla, se va. Un globo no dice lo que ya no pasa: si lo que pedía
  // ya no está, se calla.
  function aplicarEstado(nuevo) {
    if (pideOtraPantalla(nuevo)) {
      irse(nuevo);
      return false;
    }
    actual = nuevo;
    ponerSaldos(nuevo.saldos);
    flota.callarSiYaNoPasa(Array.isArray(nuevo.globos) ? nuevo.globos : []);
    return true;
  }

  // --- lo que hay en la pieza ------------------------------------------------------------

  let depto = null;
  // El arte que ya llegó, por ruta: el de la pieza, las capas del avatar y los
  // retratos (por su dirección).
  const cargadas = new Map();
  const retratosPedidos = new Set();
  // Ya llegó lo justo para pintar la primera vez.
  let listo = false;

  // Tu avatar (un caminante, o `null` si no queda casilla que se pise) y
  // cuánto lleva andando (para el paso). Tus gachamones en la pieza, por id:
  // el que no tiene casilla no está. Los que están saltando, por id: cuánto
  // llevan del salto, en segundos.
  let tu = null;
  let andado = 0;
  let enPieza = new Map();
  const saltos = new Map();

  // Lo elegido en la pieza: un mueble puesto (su id) o un gachamon (su id), o
  // ninguno; nunca los dos. Su menú sale sobre él.
  let elegido = null;
  let elegidoG = null;
  // El gachamon cuya ficha se ve a la derecha (su id); `null` es el que sale contigo.
  let visto = null;
  // Lo que llevas en la mano, o `null`: `{mueble, sitios, tipo}`. `sitios`
  // son los de `dondeCabe`, `{x, y, giro}`; `tipo` es la clave de lo que salió
  // de la bandeja (se pone el primero guardado de ese tipo), o `null` si es un
  // mueble puesto que mueves. Un gachamon que mueves es `{gachamon, sitios,
  // mueble: null, tipo: null}`, con las casillas que se pisan como `sitios`.
  let enLaMano = null;
  let bandejaAbierta = false;
  let ampliando = false;
  // La pregunta abierta en lo de ampliar, o `null`: `{eje, coste, mide}`, el
  // lado y lo que costaba y medía la pieza al abrirla. Sólo hay una.
  let preguntaAbierta = null;

  // Mientras una petición va no sale otra; lo que la mandó espera hasta que vuelve.
  let enCamino = false;
  let origenEnEspera = null;
  // Cada acción que cambia la pieza suma uno: una lectura que salió antes ya
  // no se pinta, porque lo que trae la acción es más nuevo.
  let acciones = 0;

  const elPuesto = (id) => (depto && id !== null ? depto.puestos.find((p) => p.id === id) : null) || null;

  // Pide ese arte y vuelve a pintar cuando llega. Nunca falla: lo que no carga
  // se pinta como su recuadro.
  function traerArte(rutas) {
    return Promise.all(rutas.map(cargar)).then((llegadas) => {
      for (const llegada of llegadas) cargadas.set(llegada.ruta, llegada);
      if (listo && sigueAqui()) pintarLoQueLlega(dibujar);
    });
  }

  function traerAvatar() {
    return cargarAvatar(actual.avatar).then((capas) => {
      for (const [r, capa] of capas) cargadas.set(r, capa);
    });
  }

  // Los retratos que todavía no se pidieron; se vuelve a pintar cuando llegan.
  function traerRetratos() {
    const nuevos = depto.plantel.map((g) => g.retrato).filter((r) => !retratosPedidos.has(r));
    for (const r of nuevos) retratosPedidos.add(r);
    return Promise.all(nuevos.map(cargarRetrato)).then((llegados) => {
      for (const llegado of llegados) cargadas.set(llegado.ruta, llegado);
      if (listo && sigueAqui()) pintarLoQueLlega(dibujar);
    });
  }

  // Quien camina, en la pieza que llegó (`ocupado`, lo que no se pisa): si
  // quedó sobre un mueble (o fuera), aparece en la casilla libre más cercana,
  // sin caminar. Si iba caminando, el paso que está dando se termina si esa
  // casilla se sigue pisando (si no, aparece) y el resto del camino se rehace;
  // si ya no se llega, se queda ahí. `null` si no queda casilla que se pise.
  function reubicar(quien, ocupado) {
    const sePisa = ([i, j]) => i >= 0 && j >= 0 && i < depto.ancho && j < depto.fondo && !ocupado.has(`${i},${j}`);
    if (quien.ruta.length > 0) {
      const [paso, ...resto] = quien.ruta;
      if (sePisa(paso)) {
        if (!resto.every(sePisa)) {
          const destino = quien.ruta.at(-1);
          quien.ruta = [paso, ...(sePisa(destino) ? camino(depto.ancho, depto.fondo, ocupado, paso, destino) : [])];
        }
        return quien;
      }
      quien.ruta = [];
    }
    const aqui = [Math.round(quien.i), Math.round(quien.j)];
    const donde = sePisa(aqui) ? aqui : libreMasCercana(depto.ancho, depto.fondo, ocupado, aqui);
    if (!donde) return null;
    [quien.i, quien.j] = donde;
    return quien;
  }

  // Tú y tus gachamones, en la pieza que llegó: el que ya estaba se reubica;
  // el que todavía no estaba (al entrar, uno que llega, o el que no tenía
  // casilla) entra por su sitio de entrada: tú el primero, ellos en el orden
  // de `plantel`. El que ya no vive contigo se va.
  function repartir() {
    const ocupado = noSePisan(depto);
    const entrada = sitiosDeEntrada(depto.ancho, depto.fondo, ocupado, depto.plantel.length + 1);
    tu = tu ? reubicar(tu, ocupado) : caminanteEn(entrada[0], CASILLAS_POR_SEGUNDO);
    const antes = enPieza;
    enPieza = new Map();
    depto.plantel.forEach((g, n) => {
      const ya = antes.get(g.id);
      const quien = ya ? reubicar(ya, ocupado) : caminanteEn(entrada[n + 1], PASOS_DEL_GACHAMON);
      if (quien) enPieza.set(g.id, quien);
    });
    for (const id of saltos.keys()) if (!enPieza.has(id)) saltos.delete(id);
  }

  // Las casillas donde un gachamon puede ir: las que se pisan, menos donde ya
  // está (o adonde ya va).
  function manoDelGachamon(id) {
    const quien = enPieza.get(id);
    if (!quien) return null;
    const ocupado = noSePisan(depto);
    const [aquiI, aquiJ] = quien.ruta.length > 0 ? quien.ruta.at(-1) : [quien.i, quien.j];
    const sitios = [];
    for (let y = 0; y < depto.fondo; y += 1) {
      for (let x = 0; x < depto.ancho; x += 1) {
        if (!ocupado.has(`${x},${y}`) && (x !== aquiI || y !== aquiJ)) sitios.push({ x, y });
      }
    }
    return { gachamon: id, mueble: null, tipo: null, sitios };
  }

  // Lo que llevas en la mano, al día con la pieza que hay; `null` si ya no está.
  // Lo que mueves no cuenta el sitio donde ya está.
  function manoAlDia(mano) {
    if (mano.gachamon !== undefined) return manoDelGachamon(mano.gachamon);
    const { mueble, tipo } = mano;
    if (tipo !== null) {
      const guardado = depto.guardados.find((g) => g.clave === tipo);
      return guardado ? { mueble: guardado, tipo, sitios: dondeCabe(depto, guardado, 0) } : null;
    }
    const puesto = elPuesto(mueble.id);
    if (!puesto) return null;
    const sitios = dondeCabe(depto, puesto, puesto.giro).filter((s) => s.x !== puesto.x || s.y !== puesto.y);
    return { mueble: puesto, tipo: null, sitios };
  }

  // Pone la pieza que llegó: su línea, los saldos, tú y tus gachamones (en la
  // entrada si todavía no estabais), lo elegido y lo que llevas en la mano si
  // siguen ahí, la ficha de la derecha, la bandeja y lo de ampliar. Devuelve
  // cuándo llega su arte.
  function aplicarDepto(nuevo) {
    depto = nuevo;
    linea.textContent = lineaDeEstado(nuevo);
    ponerSaldos(nuevo.saldos);
    actual = { ...actual, saldos: nuevo.saldos };
    repartir();
    if (!elPuesto(elegido)) elegido = null;
    if (!enPieza.has(elegidoG)) elegidoG = null;
    if (enLaMano) {
      enLaMano = manoAlDia(enLaMano);
      if (!enLaMano) decir('');
    }
    panel.leidas(nuevo.plantel);
    pintarElPanel();
    if (listo && medirLienzo()) dibujar();
    ponerMenu();
    flota.colocarElGlobo();
    ponerBandeja();
    ponerAmpliar();
    return Promise.all([traerArte(rutasDeLaPieza(nuevo)), traerRetratos()]);
  }

  // --- tus gachamones ----------------------------------------------------------------------

  // El gachamon cuya ficha se ve: el último que tocaste, si sigue contigo; si
  // no, el que sale contigo. `null` si no vive ninguno.
  function elVisto() {
    if (!depto) return null;
    return depto.plantel.find((g) => g.id === visto) || depto.plantel.find((g) => g.activo)
      || depto.plantel[0] || null;
  }

  // Su ficha a la derecha y, en la lista, quién la tiene a la vista.
  function pintarElPanel() {
    const g = elVisto();
    visto = g ? g.id : null;
    panel.pintar(g);
    if (depto) lista.pintar(depto, visto);
  }

  // La ficha de uno, recién llegada con lo que contestó una acción: sus barras,
  // sus esperas y su retrato. Si sale contigo o no lo dice la pieza.
  function alDia(g) {
    if (!g || !depto || !depto.plantel.some((p) => p.id === g.id)) return;
    depto = { ...depto, plantel: depto.plantel.map((p) => (p.id === g.id ? { ...g, activo: p.activo } : p)) };
    panel.leidas([g]);
    pintarElPanel();
    traerRetratos();
    dibujar();
  }

  const elQueSale = () => (depto ? depto.plantel.find((g) => g.activo) || null : null);

  // El retrato que se pinta de cada uno (su dirección), por id: el último que
  // llegó. Cuando le cambia la cara se sigue pintando el de antes hasta que
  // llegue el nuevo (si no, en ese rato se vería sólo su sombra).
  const retratoPintado = new Map();

  function retratoDe(g) {
    if (cargadas.has(g.retrato)) retratoPintado.set(g.id, g.retrato);
    return retratoPintado.get(g.id) || g.retrato;
  }

  // Tus gachamones como los pinta y los toca la pieza: los que tienen casilla.
  function losDeLaPieza() {
    if (!depto) return [];
    return depto.plantel.filter((g) => enPieza.has(g.id)).map((g) => {
      const quien = enPieza.get(g.id);
      return { id: g.id, i: quien.i, j: quien.j, retrato: retratoDe(g), activo: g.activo, sube: subeDe(g.id) };
    });
  }

  // Lo que sube ahora el que salta, en píxeles de pantalla.
  function subeDe(id) {
    if (!saltos.has(id) || !m) return 0;
    return Math.sin((Math.PI * saltos.get(id)) / UN_SALTO_DURA_S) * ALTURA_DEL_SALTO * m.tw;
  }

  // --- el lienzo -------------------------------------------------------------------------

  // La medida de la pieza en píxeles de pantalla (`medir`) y cuántos píxeles
  // del lienzo hay en cada uno.
  let m = null;
  let escala = [1, 1];

  // Mide el lienzo como se ve, le da los píxeles del aparato y vuelve a medir la pieza.
  function medirLienzo() {
    const caja = lienzo.getBoundingClientRect();
    if (!depto || !caja.width || !caja.height) return false;
    const densidad = Math.min(Math.max(window.devicePixelRatio || 1, 1), DENSIDAD_MAXIMA);
    const anchoReal = Math.round(caja.width * densidad);
    const altoReal = Math.round(caja.height * densidad);
    // Cambiar el tamaño borra el lienzo: sólo si de verdad cambia.
    if (lienzo.width !== anchoReal) lienzo.width = anchoReal;
    if (lienzo.height !== altoReal) lienzo.height = altoReal;
    escala = [anchoReal / caja.width, altoReal / caja.height];
    m = medir(caja.width, caja.height, depto.ancho, depto.fondo);
    return true;
  }

  // Encima de todo, las marcas: dónde va lo que llevas en la mano y dónde
  // está lo elegido (la huella del mueble, o la casilla del gachamon).
  function dibujar() {
    if (!listo || !m) return;
    const ctx = lienzo.getContext('2d');
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, lienzo.width, lienzo.height);
    ctx.setTransform(escala[0], 0, 0, escala[1], 0, 0);
    const puesto = elPuesto(elegido);
    const quien = enPieza.get(elegidoG);
    let marcado = null;
    if (puesto) marcado = puesto.casillas;
    else if (quien) marcado = [[Math.round(quien.i), Math.round(quien.j)]];
    dibujarPieza(ctx, m, {
      depto,
      cargadas,
      gachamones: losDeLaPieza(),
      tu: tu && {
        i: tu.i, j: tu.j, pose: poseAlCaminar(andado, tu.ruta.length > 0), espejo: tu.espejo, avatar: actual.avatar,
      },
      libres: enLaMano ? enLaMano.sitios.map((s) => [s.x, s.y]) : [],
      elegido: marcado,
    });
  }

  // --- caminar ---------------------------------------------------------------------------

  // Sólo se anima mientras algo se mueve; parado, el lienzo se queda como está.
  function pedirCuadro() {
    if (vivo && cuadroPedido === null) cuadroPedido = requestAnimationFrame(cuadro);
  }

  const seMueve = () => (tu && tu.ruta.length > 0) || saltos.size > 0
    || [...enPieza.values()].some((quien) => quien.ruta.length > 0);

  let antes = null;

  function cuadro(ahora) {
    cuadroPedido = null;
    if (!sigueAqui()) return;
    // Una pestaña que estuvo dormida recibe todo el tiempo de una vez: llega sin pasarse.
    const dt = antes === null ? 0 : (ahora - antes) / 1000;
    antes = ahora;
    andado += dt;
    if (tu) avanzar(tu, dt);
    for (const quien of enPieza.values()) avanzar(quien, dt);
    for (const [id, t] of saltos) {
      if (t + dt >= UN_SALTO_DURA_S) saltos.delete(id);
      else saltos.set(id, t + dt);
    }
    dibujar();
    // Lo que flota sobre un gachamon lo sigue.
    if (elegidoG !== null) ponerMenu();
    flota.colocarElGlobo();
    if (seMueve()) {
      pedirCuadro();
    } else {
      antes = null;
      andado = 0;
    }
  }

  // Lo que anda quien camina en `dt` segundos, casilla tras casilla, sin pasarse de la última.
  function avanzar(quien, dt) {
    let queda = quien.porSegundo * dt;
    while (quien.ruta.length > 0 && queda > 0) {
      const [hastaI, hastaJ] = quien.ruta[0];
      const di = hastaI - quien.i;
      const dj = hastaJ - quien.j;
      // Ir hacia `j` o volver por `i` es ir hacia la izquierda de la pantalla.
      if (di !== dj) quien.espejo = di < dj;
      const falta = Math.abs(di) + Math.abs(dj);
      if (falta <= queda) {
        quien.i = hastaI;
        quien.j = hastaJ;
        quien.ruta.shift();
        queda -= falta;
      } else {
        const enI = Math.min(queda, Math.abs(di));
        quien.i += Math.sign(di) * enI;
        quien.j += Math.sign(dj) * (queda - enI);
        queda = 0;
      }
    }
  }

  // Quien camina, hasta esa casilla, por el camino más corto. A medio paso, se
  // termina el paso y desde ahí se va al nuevo destino. Sin camino (lo cierran
  // los muebles) o con menos movimiento, aparece ahí.
  function caminarHasta(quien, [i, j]) {
    const ocupado = noSePisan(depto);
    if (!quien || ocupado.has(`${i},${j}`)) return;
    const desde = quien.ruta.length > 0 ? quien.ruta[0] : [quien.i, quien.j];
    if (quien.ruta.length === 0 && desde[0] === i && desde[1] === j) return;
    const pasos = camino(depto.ancho, depto.fondo, ocupado, desde, [i, j]);
    const yaVaAhi = desde[0] === i && desde[1] === j;
    if (quieto() || (pasos.length === 0 && !yaVaAhi)) {
      quien.ruta = [];
      quien.i = i;
      quien.j = j;
      dibujar();
      return;
    }
    quien.ruta = quien.ruta.length > 0 ? [quien.ruta[0], ...pasos] : pasos;
    pedirCuadro();
  }

  // Lo que no pisa un gachamon que da un paso solo: los muebles, y donde
  // estáis (o adonde vais) tú y los demás.
  function noSePisanConGente(salvo) {
    const ocupado = noSePisan(depto);
    const pisar = (quien) => {
      for (const [i, j] of [[Math.round(quien.i), Math.round(quien.j)], ...quien.ruta.slice(-1)]) ocupado.add(`${i},${j}`);
    };
    if (tu) pisar(tu);
    for (const [id, quien] of enPieza) if (id !== salvo) pisar(quien);
    return ocupado;
  }

  // Cada tanto, uno de tus gachamones que está quieto da un paso hacia una
  // casilla de al lado que esté libre; el que tiene su menú abierto se queda.
  // Con menos movimiento, o mientras llevas algo en la mano, nadie se mueve.
  function programarUnPaseo() {
    luego(UN_PASEO_CADA_MS[0] + azar() * (UN_PASEO_CADA_MS[1] - UN_PASEO_CADA_MS[0]), darUnPaseo);
  }

  function darUnPaseo() {
    programarUnPaseo();
    if (!listo || quieto() || enLaMano || document.hidden) return;
    const quietos = depto.plantel.map((g) => g.id)
      .filter((id) => id !== elegidoG && enPieza.has(id) && enPieza.get(id).ruta.length === 0);
    if (!quietos.length) return;
    const id = quietos[Math.min(quietos.length - 1, Math.floor(azar() * quietos.length))];
    const quien = enPieza.get(id);
    const [i, j] = pasoSuelto(depto.ancho, depto.fondo, noSePisanConGente(id), [quien.i, quien.j], azar);
    if (i === quien.i && j === quien.j) return;
    quien.ruta = [[i, j]];
    pedirCuadro();
  }

  // Un saltito del que recibió lo que le hiciste; con menos movimiento, no.
  function saltar(id) {
    if (quieto() || !enPieza.has(id)) return;
    saltos.set(id, 0);
    pedirCuadro();
  }

  // --- elegir, y lo que llevas en la mano ------------------------------------------------

  const indicacionDe = (mano) => (mano.mueble && mano.mueble.capa === PARED ? TOCA_LA_PARED : TOCA_LA_CASILLA);

  // Lo que se dice en la zona de aviso. Un aviso se borra solo al rato; pero
  // mientras llevas algo en la mano lo dicho no se borra solo (se le quita a la
  // zona su borrado, `aviso.parar`): la indicación de dónde tocar se queda hasta
  // que lo pongas o lo sueltes, y otro aviso la sustituye un rato y después
  // vuelve ella.
  function decir(texto, esError = false) {
    clearTimeout(volverAIndicar);
    avisar(texto, esError);
    if (!enLaMano) return;
    aviso.parar();
    if (texto !== indicacionDe(enLaMano)) volverAIndicar = setTimeout(indicar, UN_AVISO_DURA_MS);
  }

  function indicar() {
    if (sigueAqui() && enLaMano) decir(indicacionDe(enLaMano));
  }

  // Lo que se ve de lo elegido y de lo que llevas en la mano: las marcas, el
  // menú y, en la bandeja, cuál llevas.
  function verLoElegido() {
    dibujar();
    ponerMenu();
    marcarLoQueLlevas();
  }

  // Elegir un mueble (o nada) deja de elegir al gachamon que lo estaba.
  function elegir(id) {
    if (elegido === id && elegidoG === null) return;
    elegido = id;
    elegidoG = null;
    verLoElegido();
  }

  // Elegir a un gachamon lo deja también en la ficha de la derecha; dejar de
  // elegirlo (`null`) no cambia la ficha. Su menú tapa el globo, que se calla.
  function elegirGachamon(id) {
    elegido = null;
    elegidoG = id;
    if (id !== null) {
      visto = id;
      pintarElPanel();
      const sale = elQueSale();
      if (sale && sale.id === id && flota.hablando()) flota.callarGlobo();
    }
    verLoElegido();
  }

  // Lo tomas en la mano y se marcan sus sitios; si no cabe en ninguno, se dice
  // y no lo tomas.
  function tomar(mano) {
    if (!mano || !mano.sitios.length) {
      decir(NO_CABE, true);
      return;
    }
    enLaMano = mano;
    decir(indicacionDe(mano));
    verLoElegido();
  }

  // Lo sueltas sin ponerlo: lo que movías (un mueble o un gachamon) deja de
  // estar elegido.
  function soltar() {
    if (!enLaMano) return;
    if (enLaMano.tipo === null) {
      elegido = null;
      elegidoG = null;
    }
    enLaMano = null;
    decir('');
    verLoElegido();
  }

  // Con algo en la mano, el toque es sólo un sitio (una casilla o un tramo de
  // pared, sin mirar lo que haya dibujado encima, tampoco a un gachamon): si
  // está marcado, ahí se pone, con el giro con el que cabe, o ahí camina el
  // gachamon (que sigue elegido); si no, se suelta.
  function ponerLoQueLlevasEn(x, y) {
    const { mueble, sitios } = enLaMano;
    const sitio = mueble && mueble.capa === PARED
      ? tramoEn(m, x, y, depto.ancho, depto.fondo)
      : casillaEn(m, x, y, depto.ancho, depto.fondo);
    const destino = sitio && sitios.find((s) => s.x === sitio[0] && s.y === sitio[1]);
    if (!destino) {
      soltar();
      return;
    }
    if (enLaMano.gachamon !== undefined) {
      const quien = enPieza.get(enLaMano.gachamon);
      enLaMano = null;
      decir('');
      caminarHasta(quien, [destino.x, destino.y]);
      verLoElegido();
      return;
    }
    enLaMano = null;
    poner(mueble, destino, escenario);
    verLoElegido();
  }

  // Tocar un mueble o un gachamon lo elige, y tocarlo otra vez deja de
  // elegirlo; lo que se pisa (una alfombra, el felpudo) además se camina.
  // Tocar el suelo es caminar, y lo elegido deja de estarlo; tocar fuera o una
  // pared vacía, también.
  lienzo.addEventListener('click', (evento) => {
    if (!listo || !m || !sigueAqui()) return;
    const caja = lienzo.getBoundingClientRect();
    const x = evento.clientX - caja.left;
    const y = evento.clientY - caja.top;
    if (enLaMano) {
      ponerLoQueLlevasEn(x, y);
      return;
    }
    const tocado = queSeToco(m, depto, losDeLaPieza(), x, y);
    // Mientras una petición va, lo elegido se queda como está: sólo se camina.
    if (tocado && tocado.tipo === 'gachamon') {
      if (!enCamino) elegirGachamon(tocado.id === elegidoG ? null : tocado.id);
      return;
    }
    const casilla = tocado && tocado.tipo === 'casilla' ? [tocado.i, tocado.j] : null;
    if (!enCamino) {
      let id = null;
      if (tocado && tocado.tipo === 'mueble') id = tocado.id;
      else if (casilla && tocado.mueble !== undefined) id = tocado.mueble;
      elegir(id === elegido ? null : id);
    }
    if (casilla) caminarHasta(tu, casilla);
  }, { signal });

  // --- el menú de lo elegido -------------------------------------------------------------

  // Para qué está hecho el menú («mueble 21», «gachamon 8»), o `null`.
  let menuDe = null;

  function botonDelMenu(icono, texto, alTocar) {
    const boton = icono ? conIcono('boton boton-chico', icono, texto)
      : el('button', { type: 'button', class: 'boton boton-chico' }, texto);
    boton.addEventListener('click', () => alTocar(boton), { signal });
    return boton;
  }

  function hacerElMenu(puesto) {
    const botones = [botonDelMenu('✋', 'Mover', moverLoElegido)];
    // Lo de pared no se gira.
    if (puesto.capa !== PARED) botones.push(botonDelMenu('🔄', 'Girar', (boton) => girar(puesto.id, boton)));
    botones.push(botonDelMenu('📦', 'Guardar', (boton) => guardar(puesto.id, boton)));
    menu.replaceChildren(el('p', { class: 'menu-nombre' }, puesto.nombre), el('div', { class: 'menu-botones' }, botones));
    menu.setAttribute('aria-label', puesto.nombre);
    menuDe = `mueble ${puesto.id}`;
  }

  // El de un gachamon: moverlo (sólo en el dibujo) y acariciarlo.
  function hacerElMenuDelGachamon(g) {
    const botones = [
      botonDelMenu('✋', 'Mover', moverAlGachamon),
      botonDelMenu(null, 'Acariciar', (boton) => acariciar(g.id, boton)),
    ];
    menu.replaceChildren(el('p', { class: 'menu-nombre' }, g.nombre), el('div', { class: 'menu-botones' }, botones));
    menu.setAttribute('aria-label', g.nombre);
    menuDe = `gachamon ${g.id}`;
  }

  // Sobre lo elegido (`caja`, donde se pinta), centrado, y nunca fuera de la
  // pieza. Si arriba no cabe entero, se queda pegado arriba aunque tape algo;
  // si así taparía más de la mitad, va debajo.
  function colocarElMenu(caja) {
    const lado = lienzo.getBoundingClientRect();
    const ancho = menu.offsetWidth || 0;
    const alto = menu.offsetHeight || 0;
    const izquierda = Math.min(Math.max(caja.x + caja.ancho / 2, ancho / 2 + MARGEN_DEL_MENU),
      lado.width - ancho / 2 - MARGEN_DEL_MENU);
    // `top` es el borde de abajo del menú.
    let abajo = caja.y - MARGEN_DEL_MENU;
    const pegadoArriba = alto + MARGEN_DEL_MENU;
    if (abajo < pegadoArriba) {
      abajo = pegadoArriba - abajo > caja.alto / 2 ? caja.y + caja.alto + MARGEN_DEL_MENU + alto : pegadoArriba;
    }
    abajo = Math.max(Math.min(abajo, lado.height - MARGEN_DEL_MENU), pegadoArriba);
    menu.style.left = `${izquierda}px`;
    menu.style.top = `${abajo}px`;
  }

  // El menú está abierto sobre lo elegido mientras no llevas nada en la mano
  // (ni va en camino lo que pusiste tocando la pieza). El foco que estaba en un
  // menú que se cierra espera en el título.
  function ponerMenu() {
    const cerrado = enLaMano || origenEnEspera === escenario || !listo || !m;
    const puesto = cerrado ? null : elPuesto(elegido);
    const quien = cerrado ? null : enPieza.get(elegidoG);
    const g = quien ? depto.plantel.find((p) => p.id === elegidoG) : null;
    if (!puesto && !g) {
      if (menu.contains(document.activeElement)) titulo.focus({ preventScroll: true });
      menu.hidden = true;
      menuDe = null;
      return;
    }
    if (puesto) {
      if (menuDe !== `mueble ${puesto.id}`) hacerElMenu(puesto);
      menu.hidden = false;
      colocarElMenu(cajaDelMueble(m, puesto, puesto.x, puesto.y, puesto.giro));
      return;
    }
    if (menuDe !== `gachamon ${g.id}`) hacerElMenuDelGachamon(g);
    menu.hidden = false;
    colocarElMenu(cajaDelGachamon(m, quien.i, quien.j));
  }

  menu.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape') elegir(null);
  }, { signal });

  // Mover a un gachamon: lo tomas en la mano y se marcan las casillas que se pisan.
  function moverAlGachamon() {
    if (enCamino || !enPieza.has(elegidoG)) return;
    tomar(manoDelGachamon(elegidoG));
  }

  function moverLoElegido() {
    const puesto = elPuesto(elegido);
    if (enCamino || !puesto) return;
    tomar(manoAlDia({ mueble: puesto, tipo: null }));
  }

  // Girar un mueble puesto (desde su menú o desde la lista): el giro siguiente
  // con el que cabe en su mismo sitio; si no cabe de ninguna otra forma, no se
  // manda nada.
  function girar(id, boton) {
    const puesto = elPuesto(id);
    if (enCamino || !puesto) return;
    const giro = giroParaPoner(depto, puesto, puesto.x, puesto.y, (puesto.giro + 1) % GIROS);
    if (giro === null || giro === puesto.giro) {
      decir(NO_CABE, true);
      return;
    }
    poner(puesto, { x: puesto.x, y: puesto.y, giro }, boton);
  }

  // Guardarlo (desde su menú o desde la lista): tras guardar no queda ningún mueble elegido.
  function guardar(id, boton) {
    const puesto = elPuesto(id);
    if (enCamino || !puesto) return;
    enviar(boton, () => pedir('POST', 'departamento/guardar', { mueble_id: puesto.id }), () => { elegido = null; });
  }

  // --- lo que pide la lista --------------------------------------------------------------

  // Elegir a un gachamon desde la lista es lo mismo que tocarlo, sin su menú:
  // su ficha queda a la derecha y en la pieza no queda nada elegido.
  function verDesdeLaLista(id) {
    if (enCamino || !depto || !depto.plantel.some((g) => g.id === id)) return;
    elegido = null;
    elegidoG = null;
    visto = id;
    pintarElPanel();
    verLoElegido();
  }

  // Dónde cabe ese mueble, puesto o guardado (`{x, y, giro}`): lo mismo que se
  // marca al llevarlo en la mano (lo que se mueve, sin el sitio donde ya está).
  function dondeVa(id) {
    const puesto = elPuesto(id);
    if (puesto) return manoAlDia({ mueble: puesto, tipo: null }).sitios;
    const guardado = depto && depto.guardados.find((g) => g.id === id);
    return guardado ? dondeCabe(depto, guardado, 0) : [];
  }

  // Ponerlo en ese sitio, con su giro: lo mismo que tocar ahí con él en la mano.
  function ponerDesdeLaLista(id, sitio, boton) {
    const mueble = elPuesto(id) || (depto && depto.guardados.find((g) => g.id === id));
    if (enCamino || !mueble) return;
    poner(mueble, sitio, boton);
  }

  // --- los guardados ---------------------------------------------------------------------

  // El botón de cada tipo de la bandeja, por su clave.
  const tiposEnLaBandeja = new Map();

  function marcarLoQueLlevas() {
    for (const [tipo, boton] of tiposEnLaBandeja) {
      boton.setAttribute('aria-pressed', String(Boolean(enLaMano) && enLaMano.tipo === tipo));
    }
  }

  // La bandeja, con un botón por tipo de mueble guardado. El foco que estaba
  // en uno vuelve al de ese mismo tipo; si ya no queda, al botón que la abre.
  function ponerBandeja() {
    bandeja.hidden = !bandejaAbierta;
    aLosGuardados.setAttribute('aria-expanded', String(bandejaAbierta));
    if (!bandejaAbierta || !depto) return;
    const conFoco = [...tiposEnLaBandeja].find(([, boton]) => boton === document.activeElement);
    tiposEnLaBandeja.clear();
    const rotulo = el('p', { class: 'rotulo', id: 'departamento-guardados' }, ROTULO_DE_GUARDADOS);
    const tipos = porTipo(depto.guardados);
    if (!tipos.length) {
      bandeja.replaceChildren(rotulo, el('p', { class: 'bandeja-vacia' }, NADA_GUARDADO));
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
        boton.addEventListener('click', () => tomarDeLaBandeja(primero.clave), { signal });
        tiposEnLaBandeja.set(primero.clave, boton);
        return boton;
      });
      bandeja.replaceChildren(rotulo,
        el('div', { class: 'bandeja-tipos', role: 'group', 'aria-labelledby': 'departamento-guardados' }, botones));
    }
    marcarLoQueLlevas();
    if (conFoco) (tiposEnLaBandeja.get(conFoco[0]) || aLosGuardados).focus({ preventScroll: true });
  }

  // Elegir uno de la bandeja lo pone en la mano, empezando por el giro 0;
  // elegir el que ya llevas lo suelta. Si no cabe en ningún sitio no se toma:
  // se dice, y lo elegido y lo que llevabas en la mano quedan como estaban.
  function tomarDeLaBandeja(tipo) {
    if (enCamino) return;
    if (enLaMano && enLaMano.tipo === tipo) {
      soltar();
      return;
    }
    const mano = manoAlDia({ mueble: null, tipo });
    if (!mano || !mano.sitios.length) {
      decir(NO_CABE, true);
      return;
    }
    elegido = null;
    elegidoG = null;
    tomar(mano);
  }

  // Abrir o cerrar la bandeja; al abrirla se trae a la vista (en un computador
  // puede quedar bajo el borde de la ventana) y al cerrarla se suelta lo que
  // salió de ella.
  aLosGuardados.addEventListener('click', () => {
    bandejaAbierta = !bandejaAbierta;
    if (!bandejaAbierta && enLaMano && enLaMano.tipo !== null) soltar();
    ponerBandeja();
    if (bandejaAbierta) bandeja.scrollIntoView({ block: 'nearest' });
  }, { signal });

  // --- ampliar ---------------------------------------------------------------------------

  // Para qué está hecho lo de ampliar (lo que mide la pieza, lo que cuesta cada
  // lado y la pregunta abierta), o `null`: si no cambia, no se rehace, y el
  // foco no se mueve (un lector de pantalla no vuelve a leer nada).
  let ampliarDe = null;

  // El botón de crecer por ese lado, o `null` si no está (no crece por ahí, o
  // en su lugar está su pregunta).
  const botonDelLado = (eje) => [...panelAmpliar.querySelectorAll('.boton-lado')]
    .find((b) => b.getAttribute('data-eje') === eje) || null;

  // Lo de ampliar va en lugar de lo de la derecha: un botón por cada lado que
  // todavía puede crecer, con lo que suma y lo que cuesta, y «Volver». Tocar
  // un lado no cobra: en su lugar sale la pregunta de la Tienda, con «Ampliar»
  // y «No»; sólo una a la vez. La pregunta vale mientras la pieza mida y cueste
  // lo que medía y costaba al abrirla: si llega otra, se cierra, para que no se
  // cobre algo distinto de lo que se ve. Lo que nace mientras una petición va
  // no se puede usar. El foco que estaba en él vuelve a lo mismo: el rótulo, ese
  // lado (su botón, también si estaba en su pregunta) o, si ya no puede crecer
  // por ahí, «Volver».
  function ponerAmpliar() {
    derecha.hidden = ampliando;
    panelAmpliar.hidden = !ampliando;
    if (!ampliando || !depto) return;
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
    const conFoco = panelAmpliar.contains(document.activeElement) ? document.activeElement : null;
    const ocupado = enCamino ? 'true' : null;
    const rotulo = el('h2', { class: 'rotulo', id: 'departamento-ampliar', tabindex: '-1' }, ROTULO_DE_AMPLIAR);
    const volver = el('button', { type: 'button', class: 'boton boton-volver' }, 'Volver');
    volver.addEventListener('click', () => {
      ampliando = false;
      preguntaAbierta = null;
      ponerAmpliar();
      alAmpliar.focus({ preventScroll: true });
    }, { signal });
    let opciones;
    if (lados.length) {
      opciones = el('div', { class: 'ampliar-lados', role: 'group', 'aria-labelledby': 'departamento-ampliar' },
        lados.map(({ eje, que, casillas, coste }) => {
          if (preguntaAbierta && preguntaAbierta.eje === eje) {
            const { caja, si, no } = cajaDePregunta(preguntaDeAmpliar(coste), 'Ampliar', {
              alConfirmar: () => ampliar(eje, si),
              alDesistir: () => desistirDeAmpliar(eje),
            });
            caja.setAttribute('data-eje', eje);
            if (ocupado) for (const boton of [si, no]) boton.setAttribute('aria-disabled', ocupado);
            return caja;
          }
          // Se ve con el símbolo y se lee con la palabra, como los saldos.
          const boton = el('button', {
            type: 'button', class: 'boton boton-lado', 'data-eje': eje, 'aria-disabled': ocupado,
          },
            el('span', {}, `+ ${que} (${casillas} casillas) · `,
              el('span', { 'aria-hidden': 'true' }, `${coste} ${MONEDAS.simbolo}`),
              el('span', { class: 'solo-lector' }, MONEDAS.cuantas(coste))));
          boton.addEventListener('click', () => preguntarPorAmpliar(eje), { signal });
          return boton;
        }));
    } else {
      opciones = el('p', { class: 'ampliar-tope' }, YA_NO_CRECE);
    }
    panelAmpliar.replaceChildren(rotulo, opciones, volver);
    if (conFoco) {
      const deUnLado = conFoco.closest('[data-eje]');
      const eje = deUnLado && deUnLado.getAttribute('data-eje');
      (conFoco.classList.contains('rotulo') ? rotulo : (eje && botonDelLado(eje)) || volver).focus({ preventScroll: true });
    }
  }

  // El primer toque en un lado: en su lugar sale la pregunta, con lo que cuesta
  // ahora, y la que hubiera abierta se cierra. El foco va a la pregunta, que se
  // lee; no a «Ampliar», para que una tecla que se queda apretada no cobre.
  function preguntarPorAmpliar(eje) {
    if (enCamino || !depto) return;
    preguntaAbierta = { eje, coste: depto.ampliar[eje], mide: `${depto.ancho} × ${depto.fondo}` };
    ponerAmpliar();
    const caja = panelAmpliar.querySelector('.pregunta');
    if (caja) caja.querySelector('.pregunta-texto').focus({ preventScroll: true });
  }

  // «No» (o Escape): se cierra sin mandar nada y el foco vuelve al botón que la abrió.
  function desistirDeAmpliar(eje) {
    if (enCamino) return;
    preguntaAbierta = null;
    ponerAmpliar();
    const boton = botonDelLado(eje);
    if (boton) boton.focus({ preventScroll: true });
  }

  alAmpliar.addEventListener('click', () => {
    ampliando = true;
    ponerAmpliar();
    const rotulo = panelAmpliar.querySelector('h2');
    if (rotulo) rotulo.focus({ preventScroll: true });
  }, { signal });

  // El evento de crecer por un lado es el de lo que se ve: el lado y lo que
  // mide la pieza ahora («ancho 3 × 3»). Se crea la primera vez y vale
  // mientras la pieza mida lo mismo: si la respuesta se perdió y la relectura
  // también, el toque siguiente lleva el mismo evento, y si el primero entró,
  // el servidor contesta con la pieza de ahora sin cobrar otra vez. Un «no»
  // (te faltan monedas, ya es el máximo) no se anota, así que repetirlo no
  // estorba. Cuando la pieza crece, el toque siguiente estrena otro.
  const eventosDeAmpliar = new Map();

  function eventoDeAmpliar(eje) {
    const loQueSeVe = `${eje} ${depto.ancho} × ${depto.fondo}`;
    if (!eventosDeAmpliar.has(loQueSeVe)) {
      const evento = nuevoEvento();
      eventosDeAmpliar.set(loQueSeVe, evento);
    }
    return eventosDeAmpliar.get(loQueSeVe);
  }

  // Crecer por ese lado: lo que hace «Ampliar» en su pregunta. Cuesta monedas:
  // lleva el evento de lo que se ve, y sus reintentos el mismo, para que no se
  // cobre dos veces. Mientras va, la pregunta espera; salga como salga, se
  // cierra: para ampliar otra vez se vuelve a preguntar.
  function ampliar(eje, boton) {
    if (enCamino || !sigueAqui()) return;
    const evento = eventoDeAmpliar(eje);
    preguntaAbierta = null;
    enviar(boton, () => conReintentos(() => pedir('POST', 'departamento/ampliar', { eje, evento_id: evento }), sigueAqui), null)
      .then(() => { if (sigueAqui()) ponerAmpliar(); });
  }

  // --- mandar lo que se hace -------------------------------------------------------------

  // Los botones que mandan algo o te lo ponen en la mano (y los de la pregunta de ampliar).
  const queMandan = () => cuerpo.querySelectorAll('.menu-de-la-pieza button, .bandeja-tipo, .boton-lado, .ampliar .pregunta button');

  // Los de la ficha y «A todos» los pone su panel (`panel.ocupar`), que sabe
  // además cuáles esperan a que se acabe su espera; los de la lista, la lista.
  // Lo que aparece mientras tanto nace sin poderse usar.
  function esperar(origen) {
    enCamino = true;
    origenEnEspera = origen;
    origen.setAttribute('aria-busy', 'true');
    origen.classList.add(origen === escenario ? 'en-camino' : 'esperando');
    for (const boton of queMandan()) if (boton !== origen) boton.setAttribute('aria-disabled', 'true');
    panel.ocupar(origen);
    lista.ocupar(origen);
  }

  function dejarDeEsperar() {
    enCamino = false;
    origenEnEspera.removeAttribute('aria-busy');
    origenEnEspera.classList.remove('en-camino', 'esperando');
    origenEnEspera = null;
    for (const boton of queMandan()) boton.removeAttribute('aria-disabled');
    panel.ocupar(null);
    lista.ocupar(null);
    ponerMenu();
  }

  // Manda lo que hace `hacer()` y, con lo que contesta el servidor, pone el
  // estado y hace `alContestar(respuesta)`; lo que reviente al pintarlo llega
  // a la avería. Sin respuesta, pudo haber llegado igual: se dice y la pieza
  // se vuelve a leer. Al acabar, si se tiró una lectura mientras iba, se pide
  // otra.
  async function mandar(origen, hacer, alContestar) {
    if (enCamino) return;
    acciones += 1;
    esperar(origen);
    decir('');
    lista.anunciar('');
    let respuesta;
    try {
      respuesta = await hacer();
    } catch (error) {
      if (!sigueAqui()) return;
      dejarDeEsperar();
      if (hayQueDecidirDeNuevo(error)) {
        irse();
        return;
      }
      decir(error && error.clave === null ? SIN_RESPUESTA : mensajeDe(error), true);
      quedaPorLeer = false;
      releer({ trasUnaAccion: true });
      return;
    }
    if (!sigueAqui()) return;
    dejarDeEsperar();
    pintarLoQueLlega(() => {
      if (respuesta.estado && !aplicarEstado(respuesta.estado)) return;
      alContestar(respuesta);
    });
    leerLoQueQuedo();
  }

  // Lo que cambia la pieza: se pinta la que contesta el servidor. `siSaleBien()`
  // deja elegido lo que toque. Un «no» se dice con su frase y la pieza queda
  // como dice el servidor. Lo que sale bien sin frase (poner, mover, girar,
  // guardar) se ve en el dibujo; a quien no lo ve, la lista le vuelve a decir
  // cómo quedó la pieza.
  function enviar(origen, hacer, siSaleBien) {
    return mandar(origen, hacer, (respuesta) => {
      if (respuesta.ok && siSaleBien) siSaleBien();
      aplicarDepto(respuesta.departamento);
      decir(respuesta.mensaje, !respuesta.ok);
      if (respuesta.ok && !respuesta.mensaje) lista.anunciar(lineaDeEstado(depto));
    });
  }

  // Lo que se pone (o se mueve, o se gira) queda elegido, y ningún gachamon.
  function poner(mueble, { x, y, giro }, origen) {
    enviar(origen, () => pedir('POST', 'departamento/poner', { mueble_id: mueble.id, x, y, giro }),
      () => {
        elegido = mueble.id;
        elegidoG = null;
      });
  }

  // --- lo que se le hace a tus gachamones ------------------------------------------------

  // Un cuidado al que se ve en la ficha. Mueve monedas: cada toque lleva su
  // evento, y sus reintentos el mismo, para que no cuente dos veces. Con lo
  // que contesta cambian sus barras y sus esperas, y se avisa como en el lugar.
  function cuidar(accion, boton) {
    const g = elVisto();
    if (enCamino || !g || panel.falta(accion) > 0) return;
    const evento = nuevoEvento();
    const gachamonId = g.id;
    const etapaAntes = g.etapa;
    mandar(boton, () => conReintentos(
      () => pedir('POST', 'cuidar', { accion, evento_id: evento, gachamon_id: gachamonId }),
      sigueAqui,
    ), (respuesta) => {
      alDia(respuesta.gachamon);
      // La evolución se mira en quien recibió el cuidado, que no siempre es el que sale contigo.
      const recibido = { ...respuesta, estado: { gachamon: respuesta.gachamon || null } };
      trasCuidar(recibido, etapaAntes, {
        saltar: () => saltar(gachamonId),
        ganar: flota.ganar,
        celebrar: () => { if (respuesta.gachamon) flota.celebrar(respuesta.gachamon); },
        medalla: flota.medalla,
        avisar: (frase) => decir(frase),
      });
    });
  }

  // La caricia no lleva evento que la haga repetible, así que no se reintenta
  // sola (como en el lugar): si se corta, se dice y se vuelve a leer la pieza.
  // Corazones si se pudo; si todavía no, cuándo se podrá.
  function acariciar(id, boton) {
    const g = depto && depto.plantel.find((p) => p.id === id);
    if (enCamino || !g) return;
    mandar(boton, () => pedir('POST', 'acariciar', { gachamon_id: id }), (respuesta) => {
      alDia(respuesta.gachamon);
      trasAcariciar(respuesta, respuesta.gachamon || g, {
        corazones: () => corazonesSobre(id),
        saltar: () => saltar(id),
        // En la pieza no titubea: basta con decir cuándo.
        titubear: () => {},
        avisar: (frase) => decir(frase),
      });
    });
  }

  // «A todos»: un cuidado a cada uno que puede recibirlo. Mueve monedas, como
  // cada cuidado: un evento por toque. Se dice la frase del juego y se vuelve
  // a leer la pieza, que trae cómo quedaron.
  function cuidarATodos(accion, boton) {
    if (enCamino || !depto || !depto.plantel.length) return;
    const evento = nuevoEvento();
    mandar(boton, () => conReintentos(
      () => pedir('POST', 'cuidar/todos', { accion, evento_id: evento }),
      sigueAqui,
    ), (respuesta) => {
      trasCuidar({ ...respuesta, estado: null }, null, {
        saltar: () => { for (const id of respuesta.tocados || []) saltar(id); },
        ganar: flota.ganar,
        celebrar: () => {},
        medalla: flota.medalla,
        avisar: (frase) => decir(frase),
      });
      releer({ trasUnaAccion: true });
    });
  }

  // Salir con el que se ve: el servidor contesta con su frase y la pieza.
  function salirCon(boton) {
    const g = elVisto();
    if (enCamino || !g) return;
    enviar(boton, () => pedir('POST', 'departamento/salir', { gachamon_id: g.id }), null);
  }

  // Su ficha completa; al volver, se vuelve aquí.
  function verLaFicha() {
    const g = elVisto();
    if (!g) return;
    parar();
    seguir(actual, { vista: 'ficha', gachamonId: g.id });
  }

  // --- lo que flota sobre la pieza --------------------------------------------------------

  // Los corazones salen de la cabeza del que se acarició y suben.
  function corazonesSobre(id) {
    const quien = enPieza.get(id);
    if (!quien || !m) return;
    flota.corazones(cajaDelGachamon(m, quien.i, quien.j));
  }

  // El que sale contigo habla si está en la pieza y no tiene su menú encima.
  function puedeHablar() {
    const sale = elQueSale();
    return Boolean(sale) && enPieza.has(sale.id) && elegidoG !== sale.id;
  }

  // Dónde está la cabeza del que sale contigo (su caja en la pieza), lo que
  // sube si salta y lo que mide la pieza en pantalla; `null` si no está en ella.
  function dondeHabla() {
    const sale = elQueSale();
    const quien = sale && enPieza.get(sale.id);
    if (!quien || !m) return null;
    return { caja: cajaDelGachamon(m, quien.i, quien.j), sube: subeDe(sale.id), lado: lienzo.getBoundingClientRect() };
  }

  // --- mantenerse al día -----------------------------------------------------------------

  // Las lecturas que salieron: sólo se pinta la última.
  let lecturas = 0;
  let leyendo = false;
  // Una lectura que se tiró porque hubo una acción más nueva se vuelve a
  // pedir: al acabar esa acción o, si ya acabó, enseguida. Lo que trae una
  // acción no siempre es todo (un cuidado trae sólo al que lo recibió).
  let quedaPorLeer = false;

  function leerAlAcabar() {
    quedaPorLeer = true;
    if (!enCamino) leerLoQueQuedo();
  }

  function leerLoQueQuedo() {
    if (!quedaPorLeer) return;
    quedaPorLeer = false;
    releer();
  }

  // Cada relectura trae el estado, como en el lugar, y la pieza: si el estado
  // ya pide otra pantalla, se va con él; si no, se pinta la pieza. Una
  // relectura que falla no borra la pieza ni dice nada: la próxima vuelta lo
  // intenta otra vez. Sin sesión, o si ya no estás en tu casa, se va.
  // Mientras una acción va no se lee: lo que traiga es más nuevo. La de tras
  // una acción sin respuesta sale aunque haya otra en camino. La espera de la
  // red va aparte de lo que se pinta: lo que reviente al pintar no lo calla el
  // fallo de la red, llega a la avería.
  async function releer({ trasUnaAccion = false } = {}) {
    if (!sigueAqui() || !depto || enCamino) return;
    if (!trasUnaAccion && (leyendo || document.hidden)) return;
    leyendo = true;
    const esta = ++lecturas;
    const hechas = acciones;
    let leido;
    try {
      leido = await Promise.all([pedir('GET', 'estado'), pedir('GET', 'departamento')]);
    } catch (error) {
      if (sigueAqui() && hayQueDecidirDeNuevo(error)) irse();
      return;
    } finally {
      if (esta === lecturas) leyendo = false;
    }
    if (!sigueAqui() || esta !== lecturas) return;
    if (hechas !== acciones) {
      leerAlAcabar();
      return;
    }
    const [estadoNuevo, nuevo] = leido;
    pintarLoQueLlega(() => {
      if (aplicarEstado(estadoNuevo)) aplicarDepto(nuevo);
    });
  }

  document.addEventListener('visibilitychange', () => {
    if (!sigueAqui() || document.hidden) return;
    clearInterval(cadaTanto);
    cadaTanto = setInterval(releer, PEDIR_CADA_MS);
    releer();
  }, { signal });

  // --- la primera vez --------------------------------------------------------------------

  // Con lo que llega la primera vez se pinta en cuanto está su arte (el arte
  // nunca falla: lo que no carga se dibuja como su recuadro).
  async function prepararLaPieza(leido) {
    await Promise.all([aplicarDepto(leido), traerAvatar()]);
    if (!sigueAqui()) return;
    listo = true;
    deLaPieza.hidden = false;
    delPlantel.hidden = false;
    lista.nodo.hidden = false;
    // Las cuentas de las esperas bajan solas; tus gachamones pasean y el que
    // sale contigo habla de vez en cuando.
    cadaSegundo = setInterval(() => { if (sigueAqui()) panel.contar(); }, 1000);
    programarUnPaseo();
    flota.empezarAHablar(llegando);

    // Girar el teléfono o cambiar el tamaño de la ventana vuelve a medir la pieza.
    const reencuadrar = () => {
      if (sigueAqui() && medirLienzo()) {
        dibujar();
        ponerMenu();
      }
    };
    if (typeof ResizeObserver === 'function') {
      observador = new ResizeObserver(reencuadrar);
      observador.observe(lienzo);
    } else {
      window.addEventListener('resize', reencuadrar, { signal });
    }
    reencuadrar();
  }

  // La pieza común de la tienda y la mochila: mientras no llega se lee la
  // espera; si no llega, su mensaje y «Volver a intentarlo». Sin sesión o si ya
  // no estás en tu casa, se va.
  const laPieza = listaQueSePide({
    ruta: 'departamento',
    espera,
    lista: pieza,
    cargando: CARGANDO,
    titulo,
    sigueAqui,
    irse,
    // Si algo revienta al prepararla, la primera vez o tras «Volver a
    // intentarlo», llega a la avería.
    alLlegar: (leido) => { prepararLaPieza(leido).catch(reventar); },
  });

  if (!aplicarEstado(estado)) return mientrasSeVe;
  cadaTanto = setInterval(releer, PEDIR_CADA_MS);
  laPieza.cargar().catch(reventar);
  return mientrasSeVe;
}
