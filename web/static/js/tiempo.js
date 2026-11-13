// Lo que la pantalla principal dice con palabras: cuánto falta, qué globo toca,
// dónde vive el gachamon, cuántas monedas y qué contestó un cuidado (su frase,
// si evolucionó y sus medallas). Puro: no toca la página.

// Segundos que faltan, como lo diría una persona y como lo dice el bot
// (`pantalla.formato_espera`): por debajo del minuto en segundos; desde ahí,
// en minutos redondeando hacia arriba, y desde la hora en horas y minutos.
export function formatoEspera(segundos) {
  const total = Math.ceil(Number(segundos) || 0);
  if (total <= 0) return '';
  if (total < 60) return `${total} s`;
  const minutos = Math.ceil(total / 60);
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  return resto ? `${horas} h ${resto} min` : `${horas} h`;
}

// La regla de `globos.elegir` del servidor, más la llegada: una necesidad
// antes que nada; si no hay y se acaba de llegar caminando (`llegando`), una
// frase del lugar, y si no, la charla. Las del lugar no salen nunca fuera de
// la llegada. No repite `anterior` (un texto) mientras su grupo tenga otra
// frase, y nunca se salta de grupo para no repetir. `azar()` da un número en
// [0, 1), como `Math.random`.
export function elegirGlobo(globos, anterior, azar, llegando = false) {
  const lista = Array.isArray(globos) ? globos : [];
  const deTipo = (tipo) => lista.filter((g) => g.tipo === tipo);
  const grupos = [deTipo('necesidad'), llegando ? deTipo('lugar') : [], deTipo('suelta')];
  const candidatas = grupos.find((grupo) => grupo.length);
  if (!candidatas) return null;
  const otras = candidatas.filter((g) => g.texto !== anterior);
  const entre = otras.length ? otras : candidatas;
  return entre[Math.min(entre.length - 1, Math.floor(azar() * entre.length))];
}

const DONDE_VIVE = {
  propia: 'vive en tu casa',
  refugio: 'vive en el refugio',
  intemperie: 'vive a la intemperie',
};

// Para la línea de la ficha, tras el nivel. `hogar` es `estado.hogar` del
// servidor (`casas.PROPIA`, `REFUGIO` o `INTEMPERIE`); otro, nada.
export function dondeVive(hogar) {
  return Object.hasOwn(DONDE_VIVE, hogar) ? DONDE_VIVE[hogar] : '';
}

// Lo que se dice bajo la ficha tras un cuidado: la frase del juego, salga bien
// («Se ha empachado…») o no; sin frase, «Todavía no.» sólo si no salió.
export function avisoDelCuidado(respuesta) {
  const mensaje = respuesta ? respuesta.mensaje : null;
  const frase = typeof mensaje === 'string' ? mensaje.trim() : '';
  if (frase) return frase;
  return respuesta && respuesta.ok ? '' : 'Todavía no.';
}

// «1 moneda», «2 monedas», «0 monedas»: en singular sólo cuando es una.
export function cuantasMonedas(cantidad) {
  return `${cantidad} ${Math.abs(cantidad) === 1 ? 'moneda' : 'monedas'}`;
}

export function cuantasGemas(cantidad) {
  return `${cantidad} ${Math.abs(cantidad) === 1 ? 'gema' : 'gemas'}`;
}

// Si tras un cuidado se celebra la evolución: cuando el servidor lo dice, o
// cuando la etapa que llega no es la que había (un reintento del mismo cuidado
// contesta sin la marca, pero la etapa ya es otra).
export function seCelebraLaEvolucion(respuesta, etapaAntes) {
  if (!respuesta) return false;
  if (respuesta.evoluciono === true) return true;
  const g = respuesta.estado ? respuesta.estado.gachamon : null;
  return Boolean(g && etapaAntes && g.etapa !== etapaAntes);
}

// Un aviso por cada medalla nueva que trae un cuidado: «🏅 De la alfa · +25
// gemas». Lo que no tenga nombre y gemas no se dice.
export function avisosDeMedallas(respuesta) {
  const logros = respuesta && Array.isArray(respuesta.logros) ? respuesta.logros : [];
  return logros
    .filter((l) => l && typeof l.nombre === 'string' && l.nombre && Number.isFinite(l.gemas))
    .map((l) => `🏅 ${l.nombre} · +${cuantasGemas(l.gemas)}`);
}
