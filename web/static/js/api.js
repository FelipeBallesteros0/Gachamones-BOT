// La única puerta al servidor del juego.
//
// Todo lo que no sale bien se lanza como `{estado, clave, mensaje}`: `mensaje`
// es siempre una frase que se le puede enseñar a quien juega, y `clave` es
// null cuando la respuesta no es del juego (la red se cayó, el túnel no
// contestó): entonces lo que toca es ofrecer reintentar.

const BASE = '/gachamon/api/';

const SIN_RED = 'No hay conexión con el juego. Revisa tu internet y vuelve a intentarlo.';
const SIN_RESPUESTA = 'El juego no contestó. Vuelve a intentarlo en un momento.';

export async function pedir(metodo, ruta, cuerpo) {
  const opciones = { method: metodo, headers: {}, credentials: 'same-origin' };
  if (metodo !== 'GET') opciones.headers['X-Gachamon'] = '1';
  if (cuerpo !== undefined) {
    opciones.headers['Content-Type'] = 'application/json';
    opciones.body = JSON.stringify(cuerpo);
  }

  let respuesta;
  try {
    respuesta = await fetch(BASE + ruta, opciones);
  } catch {
    throw { estado: 0, clave: null, mensaje: SIN_RED };
  }

  let datos = null;
  try {
    datos = await respuesta.json();
  } catch {
    datos = null;
  }
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
