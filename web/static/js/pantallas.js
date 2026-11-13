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
