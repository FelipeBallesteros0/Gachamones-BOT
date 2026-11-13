// Lo que la pantalla principal dice con palabras: cuánto falta, qué globo toca,
// cómo se llama el hogar y cuántas monedas. Puro: no toca la página.

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

// La misma regla que `globos.elegir` del servidor: una necesidad antes que la
// charla, y sin repetir `anterior` (un texto) mientras su grupo tenga otra
// frase; nunca se salta de grupo para no repetir. `azar()` da un número en
// [0, 1), como `Math.random`.
export function elegirGlobo(globos, anterior, azar) {
  const lista = Array.isArray(globos) ? globos : [];
  const necesidades = lista.filter((g) => g.tipo === 'necesidad');
  const candidatas = necesidades.length ? necesidades : lista.filter((g) => g.tipo === 'suelta');
  if (!candidatas.length) return null;
  const otras = candidatas.filter((g) => g.texto !== anterior);
  const entre = otras.length ? otras : candidatas;
  return entre[Math.min(entre.length - 1, Math.floor(azar() * entre.length))];
}

const HOGARES = {
  propia: 'Tu casa',
  refugio: 'Refugio',
  intemperie: 'A la intemperie',
};

// `estado.hogar` del servidor (`casas.PROPIA`, `REFUGIO` o `INTEMPERIE`).
export function nombreDelHogar(hogar) {
  return Object.hasOwn(HOGARES, hogar) ? HOGARES[hogar] : 'Tu hogar';
}

// «1 moneda», «2 monedas», «0 monedas»: en singular sólo cuando es una.
export function cuantasMonedas(cantidad) {
  return `${cantidad} ${Math.abs(cantidad) === 1 ? 'moneda' : 'monedas'}`;
}

export function cuantasGemas(cantidad) {
  return `${cantidad} ${Math.abs(cantidad) === 1 ? 'gema' : 'gemas'}`;
}
