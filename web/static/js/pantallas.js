// Qué pantalla toca, según lo que contestó el servidor. Puro: no toca la página.
//
// `sesion` es lo de /api/sesion (null sin sesión), `cuenta` lo de /api/cuenta y
// `estado` lo de /api/estado (null mientras la cuenta sea nueva). El orden de
// las preguntas es el del juego: sin avatar no se ve nada más, y una muerte
// pendiente se cuenta antes que el huevo o el bautizo. `vista` es lo que se
// pidió ver cuando todo está en orden: con `'pueblo'`, el mapa en vez del
// lugar donde estás; con `'tienda'`, la tienda, si el lugar donde estás la
// ofrece (si no, el lugar); con `'mochila'`, la mochila. Con otra, el lugar.
export function siguiente(sesion, cuenta, estado, vista) {
  if (!sesion) return 'sesion';
  if (!cuenta || cuenta.estado === 'nueva') return 'bienvenida';
  if (!estado || !estado.avatar) return 'avatar';
  if (estado.difunto) return 'difunto';
  if (!estado.gachamon) return 'huevo';
  if (estado.gachamon.espera_nombre) return 'bautizo';
  if (vista === 'pueblo') return 'pueblo';
  if (vista === 'tienda') return ofreceLaTienda(estado.lugar) ? 'tienda' : 'lugar';
  if (vista === 'mochila') return 'mochila';
  return 'lugar';
}

// Si en ese lugar (`estado.lugar`) se puede comprar.
export function ofreceLaTienda(lugar) {
  return Boolean(lugar) && Array.isArray(lugar.ofrece) && lugar.ofrece.includes('tienda');
}

// Si falla la petición de entrar al lugar al que se acaba de llegar: si el
// servidor contestó que no (un 4xx: sin sesión, la cuenta o el gachamon
// cambiados, un lugar que ya no existe) toca volver a decidir la pantalla; lo
// demás (sin red, un 5xx) deja quedarse en el mapa e intentarlo otra vez.
export function trasFallarLaLlegada(error) {
  const estado = error ? error.estado : undefined;
  return typeof estado === 'number' && estado >= 400 && estado < 500 ? 'decidir' : 'reintentar';
}

// Si esta página es de otra versión que el servidor, se recarga para traer la
// suya; pero una sola vez por versión (`yaRecargada` es la última por la que
// se recargó), por si algo en el camino siguiera sirviendo una portada vieja.
export function hayQueRecargar(propia, delServidor, yaRecargada) {
  const esVersion = (valor) => typeof valor === 'string' && valor !== '';
  return esVersion(propia) && esVersion(delServidor) && propia !== delServidor && yaRecargada !== delServidor;
}

export const NO_DISPONIBLE = 'El juego no está disponible ahora mismo.';

// Qué se enseña si falla una de las tres lecturas del arranque (sesión, cuenta
// y estado): sin sesión (401, en cualquiera) toca entrar; con el servicio
// caído (503, sea nuestro o del túnel) se dice que no está disponible; lo
// demás, con su mensaje si lo trae. Las dos últimas ofrecen reintentar.
export function trasUnFalloAlArrancar(error) {
  const estado = error ? error.estado : undefined;
  if (estado === 401) return { pantalla: 'sesion', mensaje: null };
  if (estado === 503) return { pantalla: 'noCarga', mensaje: NO_DISPONIBLE };
  const mensaje = error && typeof error.mensaje === 'string' && error.mensaje ? error.mensaje : null;
  return { pantalla: 'noCarga', mensaje };
}

// Quien empezó de cero puede traer todavía los de Discord, mientras no le
// nazca nada aquí: el servidor da el código hasta entonces.
export function puedeTraerDeDiscord(cuenta) {
  return Boolean(cuenta) && cuenta.estado === 'web' && !cuenta.tiene_gachamones;
}

// Mientras se espera a que el código se escriba en Discord: si la cuenta ya no
// es la de antes (se vinculó, o cambió en otra pestaña), toca volver a decidir.
export function cambioLaCuenta(antes, ahora) {
  return ahora.estado !== antes.estado
    || Boolean(ahora.tiene_gachamones) !== Boolean(antes.tiene_gachamones);
}
