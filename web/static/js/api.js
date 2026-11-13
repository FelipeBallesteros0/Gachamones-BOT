// La única puerta al servidor del juego.
//
// Todo lo que no sale bien se lanza como `{estado, clave, mensaje}`: `mensaje`
// es siempre una frase que se le puede enseñar a quien juega, y `clave` es
// null cuando la respuesta no es del juego (la red se cayó, el túnel no
// contestó): entonces lo que toca es ofrecer reintentar.
//
// Una petición que no termina en 15 segundos se corta y se lanza igual que una
// red caída: así ningún botón se queda esperando para siempre.

const BASE = '/gachamon/api/';
const ESPERA_MAXIMA_MS = 15_000;

const SIN_RED = 'No hay conexión con el juego. Revisa tu internet y vuelve a intentarlo.';
const SIN_RESPUESTA = 'El juego no contestó. Vuelve a intentarlo en un momento.';

const sinRed = () => ({ estado: 0, clave: null, mensaje: SIN_RED });

// Cada respuesta del juego dice de qué versión es el servidor; ésta es la
// última que se oyó (null mientras ninguna lo haya dicho).
let versionDelServidor = null;

// La versión de una dirección `…/static/<versión>/js/…`; null si no es de esa forma.
export function versionDe(direccion) {
  const hallada = /\/static\/([^/]+)\/js\//.exec(String(direccion));
  return hallada ? hallada[1] : null;
}

// La versión de esta página (la de la dirección de este módulo) y la del servidor.
export function versiones() {
  return { propia: versionDe(import.meta.url), delServidor: versionDelServidor };
}

// Una respuesta sin la cabecera (la de un túnel, una de mentira) no borra la que ya se sabía.
function oirLaVersion(respuesta) {
  const cabeceras = respuesta && respuesta.headers;
  const version = cabeceras && typeof cabeceras.get === 'function' ? cabeceras.get('X-Gachamon-Version') : null;
  if (version) versionDelServidor = version;
}

export async function pedir(metodo, ruta, cuerpo) {
  const corte = new AbortController();
  const opciones = {
    method: metodo, headers: {}, credentials: 'same-origin', signal: corte.signal,
  };
  if (metodo !== 'GET') opciones.headers['X-Gachamon'] = '1';
  if (cuerpo !== undefined) {
    opciones.headers['Content-Type'] = 'application/json';
    opciones.body = JSON.stringify(cuerpo);
  }

  // No basta con cancelar el `fetch`: se compite con el reloj, por si lo que
  // tarda no atiende a la cancelación (el cuerpo, un `fetch` que no la mira).
  let reloj;
  const vencida = new Promise((_, rechazar) => {
    reloj = setTimeout(() => {
      corte.abort();
      rechazar(sinRed());
    }, ESPERA_MAXIMA_MS);
  });

  try {
    let respuesta;
    try {
      respuesta = await Promise.race([fetch(BASE + ruta, opciones), vencida]);
    } catch {
      throw sinRed();
    }
    oirLaVersion(respuesta);

    let datos = null;
    try {
      datos = await Promise.race([respuesta.json(), vencida]);
    } catch {
      if (corte.signal.aborted) throw sinRed();
      datos = null;
    }
    return resultadoDe(respuesta, datos);
  } finally {
    clearTimeout(reloj);
  }
}

// Lo que contestó el servidor: sus datos, o el error con la forma de siempre.
function resultadoDe(respuesta, datos) {
  if (!respuesta.ok) {
    const detalle = datos && typeof datos.detail === 'object' ? datos.detail : null;
    const delJuego = detalle && typeof detalle.clave === 'string' && typeof detalle.mensaje === 'string';
    throw {
      estado: respuesta.status,
      clave: delJuego ? detalle.clave : null,
      mensaje: delJuego ? detalle.mensaje : SIN_RESPUESTA,
    };
  }
  return datos;
}

// Un id de evento para /api/cuidar: entre 8 y 64 de [A-Za-z0-9-]. `randomUUID`
// sólo existe en páginas seguras; sin él se arma uno con 16 bytes al azar.
export function nuevoEvento() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}
