// El transporte de tu departamento: cómo se manda al servidor lo que se hace
// en la pieza, cómo se espera, qué pasa si no contesta y cómo se vuelve a
// leer la pieza. No guarda nada de la pantalla: sólo lo que va en camino,
// cuántas acciones y lecturas salieron y si queda una lectura por pedir. Lo
// demás lo pide a quien lo usa (`departamento.js`), que es quien pinta, quien
// dice y quien se va. Del navegador sólo mira si la pestaña se ve
// (`document.hidden`).
//
// `transporte({pedir, sigueAqui, hayPieza, esperar, dejarDeEsperar, decir,
// anunciar, irse, pintar, aplicarEstado, aplicarDepto})` devuelve
// `{mandar, enviar, releer}` y, para leer, `enCamino` (si va una petición) y
// `origen` (lo que la mandó, o `null`):
//
// - `pedir(metodo, ruta)` lee del servidor (`api.js`); `sigueAqui()` dice si
//   la pantalla sigue en la página, y `hayPieza()`, si ya llegó la primera
//   pieza (sin ella no se relee).
// - `esperar(origen)` y `dejarDeEsperar(origen)`: lo que la pantalla hace
//   cuando sale una petición y cuando vuelve (lo que la mandó espera y lo
//   demás no se puede usar). Cuando se llaman, `enCamino` y `origen` ya dicen
//   lo nuevo.
// - `decir(texto, esError)` dice algo en la zona de aviso, y `anunciar(texto)`
//   se lo dice sólo a quien no ve el dibujo.
// - `irse()` deja la pantalla y que se decida otra.
// - `pintar(hacer)` pinta lo que llega: lo que reviente ahí no lo calla el
//   transporte, llega a la avería. Con `aplicarEstado(estado)` (falso si pide
//   otra pantalla) y `aplicarDepto(depto)` se pone lo que llega.
//
// Mientras una petición va no sale otra. Al salir una, se calla lo dicho. Sin
// respuesta pudo haber llegado igual: se dice y la pieza se vuelve a leer;
// un «no» del juego se dice con su frase y también se relee; sin sesión, o
// con un «no» que cambia la pantalla (`hayQueDecidirDeNuevo`), se va. Lo que
// llega cuando la pantalla ya no está no pinta, no dice nada y no relee.
// Quien manda decide si se reintenta: lo que lleva evento pasa por
// `conReintentos` antes de llegar aquí, y para el transporte sigue siendo una
// sola petición hasta la última vuelta.
//
// Cada relectura trae el estado y la pieza, y sólo se pinta la última. Una
// relectura que falla no dice nada (la próxima vuelta lo intenta otra vez).
// Mientras una acción va no se lee, y una lectura que salió antes que una
// acción no se pinta: lo que trae la acción es más nuevo. Se vuelve a pedir al
// acabar esa acción o, si ya acabó, enseguida.

import { hayQueDecidirDeNuevo, mensajeDe } from './articulos.js';
import { lineaDeEstado } from './casillas.js';

const SIN_RESPUESTA = 'No hubo respuesta. Revisa tu conexión.';

export function transporte({
  pedir, sigueAqui, hayPieza, esperar, dejarDeEsperar, decir, anunciar, irse, pintar, aplicarEstado, aplicarDepto,
}) {
  // Mientras una petición va no sale otra; lo que la mandó espera hasta que vuelve.
  let enCamino = false;
  let origen = null;
  // Cada acción que cambia la pieza suma uno: una lectura que salió antes ya
  // no se pinta, porque lo que trae la acción es más nuevo.
  let acciones = 0;
  // Las lecturas que salieron: sólo se pinta la última.
  let lecturas = 0;
  let leyendo = false;
  // Una lectura que se tiró porque hubo una acción más nueva se vuelve a
  // pedir: al acabar esa acción o, si ya acabó, enseguida. Lo que trae una
  // acción no siempre es todo (un cuidado trae sólo al que lo recibió).
  let quedaPorLeer = false;

  function saleLaPeticion(desde) {
    enCamino = true;
    origen = desde;
    esperar(desde);
  }

  function vuelveLaPeticion() {
    const desde = origen;
    enCamino = false;
    origen = null;
    dejarDeEsperar(desde);
  }

  // Manda lo que hace `hacer()` y, con lo que contesta el servidor, pone el
  // estado y hace `alContestar(respuesta)`; lo que reviente al pintarlo llega
  // a la avería. Sin respuesta, pudo haber llegado igual: se dice y la pieza
  // se vuelve a leer. Al acabar, si se tiró una lectura mientras iba, se pide
  // otra.
  async function mandar(desde, hacer, alContestar) {
    if (enCamino) return;
    acciones += 1;
    saleLaPeticion(desde);
    decir('');
    anunciar('');
    let respuesta;
    try {
      respuesta = await hacer();
    } catch (error) {
      if (!sigueAqui()) return;
      vuelveLaPeticion();
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
    vuelveLaPeticion();
    pintar(() => {
      if (respuesta.estado && !aplicarEstado(respuesta.estado)) return;
      alContestar(respuesta);
    });
    leerLoQueQuedo();
  }

  // Lo que cambia la pieza: se pinta la que contesta el servidor. `siSaleBien()`
  // deja elegido lo que toque. Un «no» se dice con su frase y la pieza queda
  // como dice el servidor. Lo que sale bien sin frase (poner, mover, girar,
  // guardar) se ve en el dibujo; a quien no lo ve, se le vuelve a decir cómo
  // quedó la pieza.
  function enviar(desde, hacer, siSaleBien) {
    return mandar(desde, hacer, (respuesta) => {
      if (respuesta.ok && siSaleBien) siSaleBien();
      aplicarDepto(respuesta.departamento);
      decir(respuesta.mensaje, !respuesta.ok);
      if (respuesta.ok && !respuesta.mensaje) anunciar(lineaDeEstado(respuesta.departamento));
    });
  }

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
  // intenta otra vez. Sin sesión, o si ya no estás en tu departamento, se va.
  // Mientras una acción va no se lee: lo que traiga es más nuevo. La de tras
  // una acción sin respuesta sale aunque haya otra en camino. La espera de la
  // red va aparte de lo que se pinta: lo que reviente al pintar no lo calla el
  // fallo de la red, llega a la avería.
  async function releer({ trasUnaAccion = false } = {}) {
    if (!sigueAqui() || !hayPieza() || enCamino) return;
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
    pintar(() => {
      if (aplicarEstado(estadoNuevo)) aplicarDepto(nuevo);
    });
  }

  return {
    mandar,
    enviar,
    releer,
    get enCamino() { return enCamino; },
    get origen() { return origen; },
  };
}
