// Tu departamento: su pieza, en vista isométrica por casillas, con
// sus muebles, tu avatar y tus gachamones, que caminan por ella.
//
// `departamento(contenedor, estado, seguir, { azar, llegando, cuenta })` pide la pieza
// al servidor (`GET departamento`) al entrar, y la pinta en su lienzo; debajo,
// una línea dice cómo está. Cada 30 segundos y al volver a la pestaña la
// vuelve a pedir, y con ella el estado (`GET estado`), como el lugar: con él
// se renuevan los saldos y lo que dice el que sale contigo. Al entrar
// apareces en la puerta y tus gachamones se reparten por la pieza. Tocar una
// casilla que se pisa lleva a tu avatar hasta ella, caminando; con menos
// movimiento, aparece ahí. Tus gachamones dan un paso solos de vez en cuando
// (cuándo y hacia dónde lo dice `azar`, que se inyecta; si no, `Math.random`)
// y, si tienes puesto alguno de los muebles que se usan solos, a veces uno va
// hasta el lado de uno de ellos y se queda ahí un rato (es sólo del dibujo: no
// se guarda ni se manda); nada de eso con menos movimiento o mientras llevas
// algo en la mano. Quién está en qué casilla y por dónde camina lo cuenta
// `caminantes.js`; aquí se guarda y se anima. Si lo que llega pide otra
// pantalla (ya no estás en tu departamento, ya no hay sesión) se lo pasa a
// `seguir`; sin ningún gachamon, tu departamento se sigue viendo, y justo bajo
// el dibujo se lee la guía (`estado.guia`): el paso que te toca, en los dos
// modos, al día con cada estado que llega. Bajo la guía, si tu cuenta
// (`cuenta`, la que lleva `principal.js`; sin ella, nada) todavía puede traer
// los de Discord, el mismo enlace de la pantalla del avatar (`enlaceADiscord`,
// de `entrada.js`): su paso del código va en lugar de todo lo de tu
// departamento, «Volver» lo deja como estaba y, si la cuenta cambia (se
// vinculó), se deja la pantalla y se vuelve a decidir. Se va en cuanto llega
// un estado con gachamon.
//
// La pieza tiene dos modos, y siempre se entra en el normal: el modo es de la
// pantalla, no se guarda ni se manda. El botón de bajo el dibujo, «🔨
// Construir», entra al de construcción (mientras llega el arte de la pieza no
// se puede usar, y lo dice); dentro, ese mismo botón dice «✔ Listo», a su lado
// se lee «Modo construcción», la pieza se enmarca y debajo quedan abiertas la
// bandeja de los guardados (`bandeja.js`) y «Ampliar», que fuera del modo no se
// ven: viviendo, la pantalla es para cuidar, caminar y salir. Con una petición
// en camino no se cambia de modo. Viviendo (el normal), un toque sobre un
// mueble hace su acción y nada más (`queSeUsa`): hoy la única es la de la
// puerta, que te lleva caminando hasta ella y, al llegar, al pueblo, como
// «Pueblo» (si ya estás en ella, al momento; sin camino no se sale y se dice);
// un mueble sin acción no hace nada, y lo que se pisa se camina; un toque sobre
// lo que flota (el globo, la evolución, las medallas) no hace la acción de
// ningún mueble. Tocar a un gachamon lo elige (se marca dónde está) y encima
// sale su menú (`menu.js`), con «Mover» y «Acariciar»; lo transparente de su
// retrato no es él: el toque pasa a lo que tiene detrás. Construyendo, a los
// gachamones no se les toca (el toque va a lo que tienen detrás, `queSeToco`):
// tocar un mueble lo elige y encima sale su menú, con «Mover», «Girar» (no lo
// de pared) y «Guardar» (no la puerta), y al mover la puerta sólo se ofrecen
// los tramos con la entrada libre. En los dos modos, tocar el suelo es caminar.
// Entrar al modo suelta lo que llevas en la mano, deja de elegir al gachamon y
// cancela la salida; «Listo» lo deja todo recogido: suelta lo que llevas, deja
// de elegir el mueble y cierra lo de ampliar (con su pregunta, sin cobrar nada)
// y el «¿Dónde?» de la lista. Al pulsar el botón del modo el foco acaba en él,
// y lo que se esconde no se lo lleva. Ir a salir se cancela con cualquier clic
// fuera de la pieza, tocando la pieza (salvo otra vez la puerta) o mandando una
// petición. Lo que llevas en la mano (el mueble que mueves, el que sacas de la
// bandeja, o el gachamon que mueves, que va sólo adonde tiene camino) marca
// dónde va, y el toque siguiente dice dónde: en un sitio marcado se pone (el
// gachamon camina hasta ahí, y eso no se manda); en cualquier otro, se suelta.
// En la bandeja y en el «Ampliar» que abre lo de ampliar (que dice si está
// abierto), el segundo clic de un doble clic no cuenta. «Ampliar» cambia lo de
// la derecha por lo que cuesta crecer por cada lado (`ampliar.js`), y lo trae a
// la vista; tocar un lado no cobra: pregunta antes (y la trae a la vista), como
// la Tienda, el segundo clic de un doble clic no confirma, y sólo cobra con su
// pregunta a la vista.
//
// A la derecha (`plantel.js`), la ficha del último gachamon que tocaste —al
// entrar, la del que sale contigo—, con sus cuidados, «Acariciar», «Ver
// ficha» y «Salir con …», y «A todos»; debajo, «Mochila» y «Pueblo». Todo eso
// está en los dos modos. Cuidarlo y acariciarlo se mandan con su
// id, y se avisa como en el lugar (`cuidados.js`); «A todos» vuelve a leer la
// pieza, y «Salir con …» la trae. El que sale contigo lleva su marca, y su
// globo sale sobre él, como en el lugar; con `llegando` (se acaba de llegar
// caminando), el primero sale enseguida y habla del lugar, salvo que
// necesite algo. Lo que flota sobre la pieza (el
// globo, los corazones, la ganancia, la evolución y las medallas) lo arma
// `flotantes.js`.
//
// Debajo de todo, la lista (`lista.js`): lo mismo que se hace en el dibujo,
// con botones, para quien no usa el dibujo, y que sigue al modo: viviendo
// trae tus gachamones; construyendo, además, los muebles puestos y los
// guardados. Elegir ahí a un gachamon es tocarlo sin su menú; «Mover»,
// «Poner», «Girar» y «Guardar» hacen lo mismo que el menú y la bandeja, y lo
// que sale bien sin decirse con texto (poner, mover, girar, guardar) se le
// vuelve a decir a quien no ve el dibujo: cómo quedó la pieza. El foco no se
// pierde: vuelve a ese mismo mueble, en la lista donde haya quedado.
//
// El servidor manda: la pieza se pinta como llega, y lo que se calcula aquí
// (por dónde se camina, qué se tocó, qué cabe dónde) sirve sólo para dibujar y
// para no proponer lo imposible. Poner, guardar, salir y acariciar se mandan
// una vez; cada cuidado, que mueve monedas, lleva un evento por toque (el
// mismo en sus reintentos), y ampliar, el de lo que se ve (el lado y lo que
// mide la pieza: el mismo hasta que crece). Lo que sale bien no se dice: se ve;
// ampliar, los cuidados, salir y lo que no se puede dicen la frase del
// servidor; sin respuesta, se dice y la pieza se vuelve a leer. Mientras una
// petición va, lo que la mandó espera y no sale otra. Cómo se manda, se espera
// y se relee lo lleva `transporte.js`; aquí se decide qué se manda (y si se
// reintenta) y qué se pinta con lo que llega. El lienzo sólo se mira
// (`aria-hidden`); los menús, la bandeja, la ficha, lo de ampliar y la lista
// son botones de verdad, y lo que no se puede usar lleva `aria-disabled`. Todo
// texto entra por `el` o por `textContent`. Lo que corre (el cuadro de
// animación, los relojes, la relectura y los oyentes) se detiene al salir, y
// una respuesta que llega tarde no pinta; una lectura que se tiró por una
// acción más nueva se vuelve a pedir al acabarla. Lo que devuelve la pantalla
// no acaba mientras se está en ella: lo que reviente al prepararla o al pintar
// lo que llega lo hace fallar, y `principal.js` lo lleva a la avería.

import { conReintentos, nuevoEvento, pedir } from './api.js';
import { panelDeAmpliar } from './ampliar.js';
import { cargar, olvidarLasQueFaltan } from './arte.js';
import { cabeceraConSaldos, listaQueSePide, zonaDeAviso } from './articulos.js';
import { cargarAvatar, poseAlCaminar } from './avatar.js';
import { bandejaDeGuardados } from './bandeja.js';
import {
  avanzar, casillasDelGachamon, repartir, rutaHasta, unPaseo, unPaseoAUnMueble,
} from './caminantes.js';
import { conLaEntradaLibre, dondeCabe, giroParaPoner, laPuerta, lineaDeEstado } from './casillas.js';
import { trasAcariciar, trasCuidar } from './cuidados.js';
import { el } from './dom.js';
import { enlaceADiscord } from './entrada.js';
import { loQueFlota } from './flotantes.js';
import { listaDelDepartamento } from './lista.js';
import { menuDeLaPieza } from './menu.js';
import { siguiente } from './pantallas.js';
import {
  ANCHO_DEL_ARTE_DE_UNA_CASILLA, dibujarPieza, dondeSePintaElGachamon, rutasDeLaPieza,
} from './pieza.js';
import { panelDelPlantel } from './plantel.js';
import {
  cajaDelGachamon, cajaDelMueble, casillaEn, medir, queSeToco, queSeUsa, tramoEn,
} from './proyeccion.js';
import { seVe } from './transparencia.js';
import { transporte } from './transporte.js';

const VISTA = 'departamento';
const PEDIR_CADA_MS = 30_000;
const DENSIDAD_MAXIMA = 3;
// Cada cuánto da un paso solo alguno de tus gachamones: entre 4 y 9 segundos.
const UN_PASEO_CADA_MS = [4_000, 9_000];
// Con alguno de los muebles que se usan solos puesto, la parte de los paseos
// que van hasta uno de ellos, y lo que se queda a su lado el que llega.
const A_UN_MUEBLE = 1 / 3;
const SE_QUEDA_MS = 6_000;
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

const CARGANDO = 'Cargando tu departamento…';
const TOCA_LA_CASILLA = 'Toca la casilla donde lo quieres.';
const TOCA_LA_PARED = 'Toca la pared donde lo quieres.';
const NO_CABE = 'Ahí no cabe.';
const NO_HAY_CAMINO = 'No hay camino hasta la puerta.';
// El botón del modo, lo que se lee a su lado mientras dura, lo que se dice al
// entrar y, sólo al lector de pantalla, al terminar.
const CONSTRUIR = ['🔨', 'Construir'];
const LISTO = ['✔', 'Listo'];
const EN_OBRA = 'Modo construcción';
const TOCA_UN_MUEBLE = 'Toca un mueble para moverlo, girarlo o guardarlo.';
const OBRA_TERMINADA = 'Modo construcción terminado.';

// Mientras se está aquí hay sesión y la cuenta ya no es nueva, así que la
// pantalla la decide sólo el estado, con la regla de siempre (sin ningún
// gachamon, tu departamento se sigue viendo mientras estés en él).
function pideOtraPantalla(estado) {
  return siguiente(true, { estado: 'en juego' }, estado, VISTA) !== VISTA;
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

export function departamento(contenedor, estado, seguir, { azar = Math.random, llegando = false, cuenta = null } = {}) {
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
  // El menú de lo elegido (`menu.js`) va encima del lienzo, junto a él;
  // encima, lo que flota: el globo, sobre el que sale contigo, y la evolución
  // y las medallas. La ganancia asoma bajo el saldo.
  const menu = menuDeLaPieza({
    lienzo,
    mover: moverLoElegido,
    girar,
    guardar,
    moverGachamon: moverAlGachamon,
    acariciar,
    soltarElegido: () => elegir(null),
    signal,
  });
  const escenario = el('div', { class: 'pieza-escenario' }, lienzo, menu.nodo);
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
  const conIcono = (clase, icono, texto, atributos = {}) => el('button', { type: 'button', class: clase, ...atributos },
    el('span', { 'aria-hidden': 'true' }, icono), texto);
  // Bajo el dibujo, el botón del modo («Construir» o «Listo»: el mismo botón,
  // que cambia lo que dice) y, mientras dura el modo, a su lado, «Modo
  // construcción». Nace sin poderse usar: se puede cuando la pieza está lista
  // para tocarse.
  const iconoDelModo = el('span', { 'aria-hidden': 'true' }, CONSTRUIR[0]);
  const textoDelModo = el('span', {}, CONSTRUIR[1]);
  const alModo = el('button', { type: 'button', class: 'boton boton-chico boton-construir', 'aria-disabled': 'true' },
    iconoDelModo, textoDelModo);
  const rotuloDeObra = el('p', { class: 'rotulo-de-obra', hidden: true }, EN_OBRA);
  const obra = el('div', { class: 'pieza-obra' }, alModo, rotuloDeObra);
  // Debajo, y sólo mientras dura el modo, lo que se usa en él: la bandeja de
  // los guardados (`bandeja.js`), abierta, y «Ampliar». El foco que estaba en
  // un tipo que se acaba pasa al botón del modo.
  const bandeja = bandejaDeGuardados({ tomar: tomarDeLaBandeja, focoDeReserva: alModo, signal });
  // El «Ampliar» que abre lo de ampliar dice si está abierto (el que cobra
  // está en su pregunta).
  const alAmpliar = conIcono('boton boton-ampliar', '📐', 'Ampliar', { 'aria-expanded': 'false' });
  const herramientas = el('div', { class: 'obra-herramientas', hidden: true }, bandeja.nodo, alAmpliar);
  // Justo bajo el dibujo, a quien todavía no tiene ningún gachamon, la guía:
  // el paso que le toca, como lo dice el servidor. Se queda (no se borra sola),
  // en los dos modos, y cambia con cada estado que llega; se anuncia cuando cambia.
  const guia = el('p', { class: 'pieza-guia', role: 'status', hidden: true });
  // Mientras no llega, en su lugar se lee la espera (o por qué no llegó).
  const pieza = el('div', { class: 'pieza', hidden: true }, escenario, guia, obra, herramientas, linea);
  const espera = el('div', { class: 'espera-tienda' });

  const aviso = zonaDeAviso();
  aviso.nodo.classList.add('aviso');
  const { avisar } = aviso;
  // Cuándo vuelve la indicación de dónde tocar tras otro aviso (ver `decir`).
  let volverAIndicar = null;

  const aLaMochila = conIcono('boton boton-mochila', '🎒', 'Mochila');
  const alPueblo = conIcono('boton boton-pueblo', '🗺️', 'Pueblo');
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
    delPlantel, el('div', { class: 'salidas-lugar' }, aLaMochila, alPueblo));
  // Lo de ampliar: «Ampliar», en su pregunta, crece por ese lado; «Volver» lo
  // cierra y deja el foco en el «Ampliar» que lo abre.
  const panelAmpliar = panelDeAmpliar({
    alConfirmar: ampliar,
    alVolver: () => {
      ampliando = false;
      ponerAmpliar();
      alAmpliar.focus({ preventScroll: true });
    },
    signal,
  });
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
    espera, pieza, derecha, panelAmpliar.nodo, lista.nodo, aviso.nodo);
  contenedor.append(cabecera, cuerpo);

  // Bajo la guía, a quien todavía no tiene ningún gachamon y puede traer los de
  // Discord, el enlace de la pantalla del avatar: su paso del código va en
  // lugar de lo que hay en el cuerpo. Si la cuenta cambia, se deja la pantalla.
  const traer = estado.gachamon ? null : enlaceADiscord(cuerpo, () => irse(), cuenta);
  if (traer) pieza.insertBefore(traer, obra);

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

  // Al pueblo: lo que hace «Pueblo», y tocar la puerta al llegar a ella.
  function irAlPueblo() {
    parar();
    seguir(actual, { vista: 'pueblo' });
  }

  aLaMochila.addEventListener('click', () => {
    parar();
    seguir(actual, { vista: 'mochila' });
  }, { signal });
  alPueblo.addEventListener('click', irAlPueblo, { signal });

  // Cada estado que llega se pregunta lo mismo que al entrar: si ya no toca
  // esta pantalla, se va. Un globo no dice lo que ya no pasa: si lo que pedía
  // ya no está, se calla. La guía dice lo que diga el estado, o se va; el
  // enlace a Discord se va si ya tienes un gachamon.
  function aplicarEstado(nuevo) {
    if (pideOtraPantalla(nuevo)) {
      irse(nuevo);
      return false;
    }
    actual = nuevo;
    ponerSaldos(nuevo.saldos);
    flota.callarSiYaNoPasa(Array.isArray(nuevo.globos) ? nuevo.globos : []);
    ponerGuia(nuevo.guia);
    if (traer) traer.hidden = Boolean(nuevo.gachamon);
    return true;
  }

  // Sólo si cambió: volver a poner el mismo texto lo anunciaría otra vez.
  function ponerGuia(laQueToca) {
    const dice = laQueToca && typeof laQueToca.texto === 'string' ? laQueToca.texto : '';
    if (guia.textContent !== dice) guia.textContent = dice;
    guia.hidden = !dice;
  }

  // --- lo que hay en la pieza ------------------------------------------------------------

  let depto = null;
  // El arte que ya llegó, por ruta: el de la pieza, las capas del avatar y los
  // retratos (por su dirección).
  const cargadas = new Map();
  const retratosPedidos = new Set();
  // Ya llegó lo justo para pintar la primera vez.
  let listo = false;

  // Tu avatar (un caminante de `caminantes.js`, o `null` si no queda casilla
  // que se pise) y cuánto lleva andando (para el paso); `saliendo`, si va
  // camino de la puerta a salir por ella. Tus gachamones en la pieza, por id:
  // el que no tiene casilla no está. Los que están saltando, por id: cuánto
  // llevan del salto, en segundos. Los que van solos al lado de uno de los
  // muebles que se usan solos, por id: la casilla adonde van; y los que ya
  // llegaron y se quedan ahí un rato, por id: `{casilla, marca}`, con el reloj
  // que los suelta.
  let tu = null;
  let andado = 0;
  let saliendo = false;
  let enPieza = new Map();
  const saltos = new Map();
  const vanAUnMueble = new Map();
  const seQuedan = new Map();

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
  // En el modo construcción (si no, viviendo). Siempre se entra viviendo.
  // Mientras dura, la bandeja está abierta.
  let construyendo = false;
  // Si lo de ampliar está abierto (su pregunta es suya, de `ampliar.js`).
  let ampliando = false;

  // Lo que se manda al servidor y cómo se vuelve a leer la pieza
  // (`transporte.js`): mientras una petición va (`envios.enCamino`) no sale
  // otra, y lo que la mandó (`envios.origen`) espera hasta que vuelve.
  const envios = transporte({
    pedir,
    sigueAqui,
    hayPieza: () => Boolean(depto),
    esperar,
    dejarDeEsperar,
    decir,
    anunciar: lista.anunciar,
    irse,
    pintar: pintarLoQueLlega,
    aplicarEstado,
    aplicarDepto,
  });
  const { mandar, enviar, releer } = envios;

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

  // Tú y tus gachamones, en la pieza que llegó (`repartir`). Si ibas a salir y
  // la pieza nueva te dejó parado, ya no sales: se sale sólo llegando. El que
  // ya no está en la pieza deja de saltar.
  function ponerEnLaPieza() {
    ({ tu, enPieza } = repartir(depto, tu, enPieza));
    if (!tu || tu.ruta.length === 0) saliendo = false;
    for (const id of saltos.keys()) if (!enPieza.has(id)) saltos.delete(id);
  }

  // Un gachamon en la mano: las casillas donde puede ir (`casillasDelGachamon`).
  function manoDelGachamon(id) {
    const quien = enPieza.get(id);
    if (!quien) return null;
    return { gachamon: id, mueble: null, tipo: null, sitios: casillasDelGachamon(depto, quien) };
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
    // La puerta sólo se lleva a donde se puede entrar por ella.
    return { mueble: puesto, tipo: null, sitios: puesto.puerta ? conLaEntradaLibre(depto, sitios) : sitios };
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
    ponerEnLaPieza();
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
    pintarLaLista();
  }

  // La lista, al día con la pieza y con el modo.
  function pintarLaLista() {
    if (depto) lista.pintar(depto, visto, construyendo);
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
    // La casilla no se pinta más ancha que su arte en píxeles del aparato.
    m = medir(caja.width, caja.height, depto.ancho, depto.fondo, ANCHO_DEL_ARTE_DE_UNA_CASILLA / densidad);
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
    if (salirSiLlegaste()) return;
    for (const quien of enPieza.values()) avanzar(quien, dt);
    alLlegarAlMueble();
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

  // Quien camina, hasta esa casilla (`rutaHasta`; con `puerta`, sólo tú). Con
  // menos movimiento, aparece ahí. Sin camino (lo cierran los muebles) no va:
  // sigue como estaba. Dice si va (o ya está ahí).
  function caminarHasta(quien, [i, j], puerta = null) {
    const ruta = rutaHasta(depto, quien, [i, j], puerta);
    if (ruta === null) return false;
    if (ruta.length === 0) return true;
    if (quieto()) {
      quien.ruta = [];
      quien.i = i;
      quien.j = j;
      dibujar();
      return true;
    }
    quien.ruta = ruta;
    pedirCuadro();
    return true;
  }

  // Tocar la puerta, viviendo: caminas hasta ella y, al llegar, al pueblo; si
  // ya estás en ella, o con menos movimiento, enseguida. Sin camino no se sale,
  // y se dice. Mientras una petición va, no se sale.
  function salirPorLaPuerta() {
    const puerta = depto && laPuerta(depto);
    if (envios.enCamino || !puerta) return;
    if (!caminarHasta(tu, puerta.celda, puerta)) {
      decir(NO_HAY_CAMINO, true);
      return;
    }
    saliendo = true;
    salirSiLlegaste();
  }

  // Si ibas saliendo y ya no caminas: en la puerta, al pueblo; si te cortaron
  // el paso antes de llegar, te quedas. Dice si saliste.
  function salirSiLlegaste() {
    if (!saliendo || !tu || tu.ruta.length > 0) return false;
    saliendo = false;
    const puerta = laPuerta(depto);
    if (!puerta || tu.i !== puerta.celda[0] || tu.j !== puerta.celda[1]) return false;
    irAlPueblo();
    return true;
  }

  // Cada tanto, uno de tus gachamones que está quieto da un paso hacia una
  // casilla de al lado que esté libre (`unPaseo`); el que tiene su menú
  // abierto se queda. Con menos movimiento, o mientras llevas algo en la mano,
  // nadie se mueve. Aquí se le pide a `azar` cuándo; quién y hacia dónde, allí.
  // Si hay puesto alguno de los muebles que se usan solos (los que traen la
  // marca `uso`), tras cuándo se le pide una vez más si este paseo va hasta
  // uno de ellos (va con menos de `A_UN_MUEBLE`): si va, `unPaseoAUnMueble` le
  // pide quién, a cuál y a qué lado; si no tiene adónde ir (o no va), el paso
  // suelto de siempre. Sin ninguno puesto, no se le pide nada más. El que
  // llega al lado de uno se queda ahí `SE_QUEDA_MS`, sin que le toque ningún
  // paseo.
  function programarUnPaseo() {
    luego(UN_PASEO_CADA_MS[0] + azar() * (UN_PASEO_CADA_MS[1] - UN_PASEO_CADA_MS[0]), darUnPaseo);
  }

  function darUnPaseo() {
    programarUnPaseo();
    if (!listo || quieto() || enLaMano || document.hidden) return;
    const pasean = depto.plantel.filter((g) => !seQueda(g.id));
    const vaAUnMueble = depto.puestos.some((p) => p.uso) && azar() < A_UN_MUEBLE;
    const aUnMueble = vaAUnMueble ? unPaseoAUnMueble(depto, pasean, enPieza, tu, elegidoG, azar) : null;
    const paseo = aUnMueble || unPaseo(depto, pasean, enPieza, tu, elegidoG, azar);
    if (!paseo) return;
    enPieza.get(paseo.id).ruta = paseo.ruta;
    if (aUnMueble) vanAUnMueble.set(paseo.id, paseo.ruta.at(-1));
    pedirCuadro();
  }

  // Si se queda junto al mueble al que llegó: mientras dure su rato y siga en
  // esa casilla. Al que mandas a otro sitio, o el que la pieza que llega
  // cambia de casilla, ya no se queda.
  function seQueda(id) {
    const rato = seQuedan.get(id);
    const quien = enPieza.get(id);
    return Boolean(rato && quien) && quien.i === rato.casilla[0] && quien.j === rato.casilla[1];
  }

  // En cada cuadro, los que iban al lado de un mueble y ya no caminan: el que
  // llegó se queda ahí un rato; el que acabó en otro sitio (la pieza que llegó
  // le cortó el paso, o lo mandaste tú a otro) o ya no está, ya no va.
  function alLlegarAlMueble() {
    for (const [id, [i, j]] of vanAUnMueble) {
      const quien = enPieza.get(id);
      if (quien && quien.ruta.length > 0) continue;
      vanAUnMueble.delete(id);
      if (quien && quien.i === i && quien.j === j) quedarseAlLado(id, [i, j]);
    }
  }

  function quedarseAlLado(id, casilla) {
    if (seQuedan.has(id)) cancelar(seQuedan.get(id).marca);
    seQuedan.set(id, { casilla, marca: luego(SE_QUEDA_MS, () => seQuedan.delete(id)) });
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

  // Ir a salir se cancela con cualquier clic en la pantalla que no sea sobre
  // la pieza, en un solo sitio: en captura, antes de lo que haga lo que se
  // pulsó, y aunque no haga nada (un cuidado que todavía espera). El toque
  // sobre la pieza lo decide su oyente.
  cuerpo.addEventListener('click', (evento) => {
    if (evento.target !== lienzo) saliendo = false;
  }, { capture: true, signal });

  // Tocar la pieza mientras vas a salir te deja dentro, salvo que lo tocado
  // sea otra vez la puerta. Con algo en la mano, el toque dice dónde va; si
  // no, depende del modo. Mientras una petición va, lo elegido se queda como
  // está: sólo se camina.
  lienzo.addEventListener('click', (evento) => {
    if (!listo || !m || !sigueAqui()) return;
    saliendo = false;
    const caja = lienzo.getBoundingClientRect();
    const x = evento.clientX - caja.left;
    const y = evento.clientY - caja.top;
    if (enLaMano) ponerLoQueLlevasEn(x, y);
    else if (construyendo) tocarConstruyendo(x, y);
    else tocarViviendo(x, y, flota.cubre(evento.clientX, evento.clientY));
  }, { signal });

  // Si en ese punto se ve algo del gachamon `g`, tal como se pinta (con su
  // salto): lo transparente de su retrato deja pasar el toque a lo de detrás.
  function seLeVe(g, x, y) {
    const donde = dondeSePintaElGachamon(m, cargadas, g);
    return seVe(donde.imagen, donde, x, y);
  }

  // Viviendo, el toque es de lo que tiene acción (hoy, sólo la puerta: te
  // saca), de un gachamon donde se le ve (tocarlo lo elige, y tocarlo otra vez
  // deja de elegirlo) o del suelo (se camina; también sobre lo que se pisa).
  // Ningún mueble se elige: el que no tiene acción no hace nada. Lo que no es
  // un gachamon deja de elegir al que lo estaba. Un toque que cae sobre lo que
  // flota y se ve (`sobreLoQueFlota`: el globo, la evolución, las medallas) no
  // hace la acción de ningún mueble: no iba para él.
  function tocarViviendo(x, y, sobreLoQueFlota) {
    const tocado = queSeUsa(m, depto, losDeLaPieza(), x, y, (puesto) => Boolean(puesto.puerta), seLeVe);
    if (tocado && tocado.tipo === 'gachamon') {
      if (!envios.enCamino) elegirGachamon(tocado.id === elegidoG ? null : tocado.id);
      return;
    }
    if (!envios.enCamino) elegir(null);
    if (!tocado) return;
    if (tocado.tipo !== 'accion') caminarHasta(tu, [tocado.i, tocado.j], laPuerta(depto));
    else if (!sobreLoQueFlota) salirPorLaPuerta();
  }

  // Construyendo, a los gachamones no se les toca: el toque va a lo que tengan
  // detrás. Tocar un mueble lo elige, y tocarlo otra vez deja de elegirlo; lo
  // que se pisa (una alfombra, el felpudo) además se camina. Tocar el suelo es
  // caminar, y lo elegido deja de estarlo; tocar fuera o una pared vacía,
  // también.
  function tocarConstruyendo(x, y) {
    const tocado = queSeToco(m, depto, [], x, y);
    const casilla = tocado && tocado.tipo === 'casilla' ? [tocado.i, tocado.j] : null;
    if (!envios.enCamino) {
      let id = null;
      if (tocado && tocado.tipo === 'mueble') id = tocado.id;
      else if (casilla && tocado.mueble !== undefined) id = tocado.mueble;
      elegir(id === elegido ? null : id);
    }
    if (casilla) caminarHasta(tu, casilla, laPuerta(depto));
  }

  // --- el modo ---------------------------------------------------------------------------

  // Lo que se ve del modo: lo que dice su botón, «Modo construcción», el marco
  // y, debajo, la bandeja y «Ampliar».
  function ponerElModo() {
    const [icono, texto] = construyendo ? LISTO : CONSTRUIR;
    iconoDelModo.textContent = icono;
    textoDelModo.textContent = texto;
    alModo.classList.toggle('principal', construyendo);
    rotuloDeObra.hidden = !construyendo;
    pieza.classList.toggle('construyendo', construyendo);
    herramientas.hidden = !construyendo;
  }

  // Entrar o salir del modo, con su botón, que se queda con el foco. Las dos
  // cosas sueltan lo que llevas en la mano (sin ponerlo). Al entrar, deja de
  // estar elegido el gachamon (su ficha sigue a la derecha), se abren la
  // bandeja y «Ampliar» (y se traen a la vista: en un computador pueden quedar
  // bajo el borde de la ventana), la lista trae los muebles y se dice qué
  // hacer; si ibas a salir, ya no (como con cualquier clic fuera de la pieza).
  // Al terminar, deja de estar elegido el mueble, se cierran lo de ampliar (con
  // su pregunta, sin mandar nada) y el «¿Dónde?» de la lista, y se le dice a
  // quien no ve la pieza. Con una petición en camino, nada.
  alModo.addEventListener('click', () => {
    if (envios.enCamino || !listo) return;
    soltar();
    construyendo = !construyendo;
    elegidoG = null;
    if (!construyendo) {
      elegido = null;
      ampliando = false;
      panelAmpliar.cerrarLaPregunta();
    }
    ponerElModo();
    ponerBandeja();
    ponerAmpliar();
    pintarLaLista();
    verLoElegido();
    // El foco acaba en él, siempre: hay navegadores donde pulsar un botón no
    // lo enfoca, y lo que tenía el foco (un menú, la bandeja, lo de ampliar,
    // el «¿Dónde?») puede haberse escondido o haberlo mandado al título.
    alModo.focus({ preventScroll: true });
    if (construyendo) herramientas.scrollIntoView({ block: 'nearest' });
    decir(construyendo ? TOCA_UN_MUEBLE : '');
    lista.anunciar(construyendo ? '' : OBRA_TERMINADA);
  }, { signal });

  // --- el menú de lo elegido -------------------------------------------------------------

  // El menú está abierto sobre lo elegido mientras no llevas nada en la mano
  // (ni va en camino lo que pusiste tocando la pieza). El foco que estaba en un
  // menú que se cierra espera en el título.
  function ponerMenu() {
    const cerrado = enLaMano || envios.origen === escenario || !listo || !m;
    const puesto = cerrado ? null : elPuesto(elegido);
    const quien = cerrado ? null : enPieza.get(elegidoG);
    const g = quien ? depto.plantel.find((p) => p.id === elegidoG) : null;
    if (puesto) {
      menu.pintar({ puesto, caja: cajaDelMueble(m, puesto, puesto.x, puesto.y, puesto.giro) });
    } else if (g) {
      menu.pintar({ gachamon: g, caja: cajaDelGachamon(m, quien.i, quien.j) });
    } else {
      if (menu.contiene(document.activeElement)) titulo.focus({ preventScroll: true });
      menu.cerrar();
    }
  }

  // Mover a un gachamon: lo tomas en la mano y se marcan las casillas que se pisan.
  function moverAlGachamon() {
    if (envios.enCamino || !enPieza.has(elegidoG)) return;
    tomar(manoDelGachamon(elegidoG));
  }

  function moverLoElegido() {
    const puesto = elPuesto(elegido);
    if (envios.enCamino || !puesto) return;
    tomar(manoAlDia({ mueble: puesto, tipo: null }));
  }

  // Girar un mueble puesto (desde su menú o desde la lista): el giro siguiente
  // con el que cabe en su mismo sitio; si no cabe de ninguna otra forma, no se
  // manda nada.
  function girar(id, boton) {
    const puesto = elPuesto(id);
    if (envios.enCamino || !puesto) return;
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
    if (envios.enCamino || !puesto) return;
    enviar(boton, () => pedir('POST', 'departamento/guardar', { mueble_id: puesto.id }), () => { elegido = null; });
  }

  // --- lo que pide la lista --------------------------------------------------------------

  // Elegir a un gachamon desde la lista es lo mismo que tocarlo, sin su menú:
  // su ficha queda a la derecha y en la pieza no queda nada elegido.
  function verDesdeLaLista(id) {
    if (envios.enCamino || !depto || !depto.plantel.some((g) => g.id === id)) return;
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
    if (envios.enCamino || !mueble) return;
    poner(mueble, sitio, boton);
  }

  // --- los guardados ---------------------------------------------------------------------

  // En la bandeja, cuál llevas en la mano: el tipo que salió de ella, si salió.
  function marcarLoQueLlevas() {
    bandeja.marcar(enLaMano ? enLaMano.tipo : null);
  }

  // La bandeja, abierta mientras dura el modo, al día con los guardados. Antes
  // de rehacerla se le dice qué llevas en la mano, que puede haber cambiado
  // con la pieza que llegó: lo marca en lo que rehace.
  function ponerBandeja() {
    if (!construyendo || !depto) return;
    marcarLoQueLlevas();
    bandeja.pintar(depto.guardados, { enCamino: envios.enCamino });
  }

  // Elegir uno de la bandeja lo pone en la mano, empezando por el giro 0;
  // elegir el que ya llevas lo suelta. Si no cabe en ningún sitio no se toma:
  // se dice, y lo elegido y lo que llevabas en la mano quedan como estaban.
  function tomarDeLaBandeja(tipo) {
    if (envios.enCamino) return;
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

  // --- ampliar ---------------------------------------------------------------------------

  // Lo de ampliar (`ampliar.js`) va en lugar de lo de la derecha mientras está
  // abierto, y el «Ampliar» que lo abre dice si lo está.
  function ponerAmpliar() {
    derecha.hidden = ampliando;
    alAmpliar.setAttribute('aria-expanded', String(ampliando));
    panelAmpliar.pintar(depto, { abierto: ampliando });
  }

  // «Ampliar», bajo la pieza mientras dura el modo, lo abre; «Volver» y
  // «Listo» lo cierran. Lo que abre va en lugar de lo de la derecha, que en un
  // teléfono queda más abajo: se trae a la vista. El segundo clic de un doble
  // clic no cuenta, como en la bandeja.
  alAmpliar.addEventListener('click', (clic) => {
    if (clic.detail > 1) return;
    ampliando = true;
    ponerAmpliar();
    panelAmpliar.traerALaVista();
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
  // cobre dos veces. Sólo con su pregunta a la vista: lo de ampliar abierto y
  // la pregunta abierta, la de ese lado. Mientras va, la pregunta espera; salga
  // como salga, se cierra: para ampliar otra vez se vuelve a preguntar.
  function ampliar(eje, boton) {
    if (envios.enCamino || !sigueAqui()) return;
    if (!ampliando || !panelAmpliar.preguntaAbiertaEn(eje)) return;
    const evento = eventoDeAmpliar(eje);
    panelAmpliar.cerrarLaPregunta();
    enviar(boton, () => conReintentos(() => pedir('POST', 'departamento/ampliar', { eje, evento_id: evento }), sigueAqui), null)
      .then(() => { if (sigueAqui()) ponerAmpliar(); });
  }

  // --- mandar lo que se hace -------------------------------------------------------------

  // Los botones que mandan algo o te lo ponen en la mano (y los de la pregunta
  // de ampliar), y el del modo, que no cambia mientras una petición va.
  const queMandan = () => cuerpo.querySelectorAll(
    '.menu-de-la-pieza button, .bandeja-tipo, .boton-lado, .ampliar .pregunta button, .boton-construir',
  );

  // Lo que pasa en la pantalla cuando sale una petición (`esperar`, que el
  // transporte llama con lo que la mandó) y cuando vuelve (`dejarDeEsperar`).
  // Al salir, si ibas a salir por la puerta, ya no; lo que la mandó espera y
  // lo demás que manda algo no se puede usar. Los de la ficha y «A todos» los
  // pone su panel (`panel.ocupar`), que sabe además cuáles esperan a que se
  // acabe su espera; los de la lista, la lista. Lo que aparece mientras tanto
  // nace sin poderse usar.
  function esperar(origen) {
    saliendo = false;
    origen.setAttribute('aria-busy', 'true');
    origen.classList.add(origen === escenario ? 'en-camino' : 'esperando');
    for (const boton of queMandan()) if (boton !== origen) boton.setAttribute('aria-disabled', 'true');
    panel.ocupar(origen);
    lista.ocupar(origen);
    panelAmpliar.ocupar(origen);
  }

  function dejarDeEsperar(origen) {
    origen.removeAttribute('aria-busy');
    origen.classList.remove('en-camino', 'esperando');
    for (const boton of queMandan()) boton.removeAttribute('aria-disabled');
    panel.ocupar(null);
    lista.ocupar(null);
    panelAmpliar.ocupar(null);
    ponerMenu();
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
    if (envios.enCamino || !g || panel.falta(accion) > 0) return;
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
    if (envios.enCamino || !g) return;
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
    if (envios.enCamino || !depto || !depto.plantel.length) return;
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
    if (envios.enCamino || !g) return;
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

  // Cada 30 segundos y al volver a la pestaña se vuelve a leer la pieza
  // (`releer`, del transporte).
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
    // Ya se puede tocar la pieza: también entrar al modo.
    if (!envios.enCamino) alModo.removeAttribute('aria-disabled');
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
  // no estás en tu departamento, se va.
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
