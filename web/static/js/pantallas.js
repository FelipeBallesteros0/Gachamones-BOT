// Qué pantalla toca, según lo que contestó el servidor. Puro: no toca la página.
//
// `sesion` es lo de /api/sesion (null sin sesión), `cuenta` lo de /api/cuenta y
// `estado` lo de /api/estado (null mientras la cuenta sea nueva). El orden de
// las preguntas es el del juego: sin avatar no se ve nada más, y una muerte
// pendiente se cuenta antes que el huevo o el bautizo.
export function siguiente(sesion, cuenta, estado) {
  if (!sesion) return 'sesion';
  if (!cuenta || cuenta.estado === 'nueva') return 'bienvenida';
  if (!estado || !estado.avatar) return 'avatar';
  if (estado.difunto) return 'difunto';
  if (!estado.gachamon) return 'huevo';
  if (estado.gachamon.espera_nombre) return 'bautizo';
  return 'lugar';
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
