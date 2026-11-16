// Las cuentas de la rejilla del departamento: qué ocupa un mueble, qué cabe
// dónde y por dónde se camina. Es puro: sin pantalla, sin reloj, sin red; el
// azar entra como función. El servidor manda: esto sirve para dibujar y para no
// proponer lo imposible, nunca para decidir.

const SUELO = 'suelo';
const PARED = 'pared';

const clave = (i, j) => `${i},${j}`;

// Las casillas de un mueble puesto en (x, y): la regla de `departamento.huella`.
// Salen ordenadas por i y después por j, como llegan las de un mueble puesto.
export function huellaDe(forma, x, y, giro) {
  const salida = [];
  if (forma.capa === PARED) {
    const alLoLargoDeY = x === -1 && y !== -1;
    for (let k = 0; k < forma.ancho; k += 1) {
      salida.push(alLoLargoDeY ? [x, y + k] : [x + k, y]);
    }
    return salida;
  }
  const girada = giro % 2 !== 0;
  const largo = girada ? forma.fondo : forma.ancho;
  const hondo = girada ? forma.ancho : forma.fondo;
  for (let i = 0; i < largo; i += 1) {
    for (let j = 0; j < hondo; j += 1) salida.push([x + i, y + j]);
  }
  return salida;
}

function cabeEnLaPieza(depto, forma, casillas) {
  if (forma.capa === PARED) {
    return casillas.every(([i, j]) => (j === -1 && i >= 0 && i < depto.ancho) || (i === -1 && j >= 0 && j < depto.fondo));
  }
  return casillas.every(([i, j]) => i >= 0 && i < depto.ancho && j >= 0 && j < depto.fondo);
}

// La regla de `departamento.problema_al_poner`.
export function problemaAlPoner(depto, pieza, x, y, giro) {
  const casillas = huellaDe(pieza, x, y, giro);
  if (!cabeEnLaPieza(depto, pieza, casillas)) return 'no_cabe';
  const mias = new Set(casillas.map(([i, j]) => clave(i, j)));
  for (const otra of depto.puestos) {
    if (otra.id === pieza.id || otra.capa !== pieza.capa) continue;
    if (huellaDe(otra, otra.x, otra.y, otra.giro).some(([i, j]) => mias.has(clave(i, j)))) return 'ocupado';
  }
  return null;
}

export function giroParaPoner(depto, pieza, x, y, giro) {
  for (let paso = 0; paso < 4; paso += 1) {
    const probado = (giro + paso) % 4;
    if (problemaAlPoner(depto, pieza, x, y, probado) === null) return probado;
  }
  return null;
}

export function dondeCabe(depto, pieza, giro) {
  const sitios = [];
  const probar = (x, y) => {
    const g = giroParaPoner(depto, pieza, x, y, giro);
    if (g !== null) sitios.push({ x, y, giro: g });
  };
  if (pieza.capa === PARED) {
    for (let x = 0; x < depto.ancho; x += 1) probar(x, -1);
    for (let y = 0; y < depto.fondo; y += 1) probar(-1, y);
    return sitios;
  }
  for (let y = 0; y < depto.fondo; y += 1) {
    for (let x = 0; x < depto.ancho; x += 1) probar(x, y);
  }
  return sitios;
}

export function ocupadas(depto) {
  const hay = new Set();
  for (const p of depto.puestos) {
    if (p.capa === PARED) continue;
    for (const [i, j] of p.casillas) hay.add(clave(i, j));
  }
  return hay.size;
}

// Las casillas con un mueble que no se pisa: sobre lo del suelo se camina.
export function noSePisan(depto) {
  const hay = new Set();
  for (const p of depto.puestos) {
    if (p.capa === SUELO || p.capa === PARED) continue;
    for (const [i, j] of p.casillas) hay.add(clave(i, j));
  }
  return hay;
}

const VECINAS = [[0, 1], [1, 0], [0, -1], [-1, 0]];

function vecinasDe(ancho, fondo, [i, j]) {
  return VECINAS.map(([di, dj]) => [i + di, j + dj])
    .filter(([a, b]) => a >= 0 && a < ancho && b >= 0 && b < fondo);
}

export function camino(ancho, fondo, ocupado, desde, hasta) {
  if (ocupado.has(clave(...hasta)) || clave(...desde) === clave(...hasta)) return [];
  const vino = new Map([[clave(...desde), null]]);
  const cola = [desde];
  for (let n = 0; n < cola.length; n += 1) {
    const actual = cola[n];
    for (const vecina of vecinasDe(ancho, fondo, actual)) {
      const k = clave(...vecina);
      if (vino.has(k) || ocupado.has(k)) continue;
      vino.set(k, actual);
      if (k === clave(...hasta)) {
        const ruta = [];
        for (let paso = vecina; clave(...paso) !== clave(...desde); paso = vino.get(clave(...paso))) ruta.unshift(paso);
        return ruta;
      }
      cola.push(vecina);
    }
  }
  return [];
}

// Todas las casillas de la pieza en orden de lectura: fila a fila (j), y en cada fila por i.
function enOrdenDeLectura(ancho, fondo) {
  const todas = [];
  for (let j = 0; j < fondo; j += 1) {
    for (let i = 0; i < ancho; i += 1) todas.push([i, j]);
  }
  return todas;
}

export function libreMasCercana(ancho, fondo, ocupado, desde) {
  let mejor = null;
  let distancia = Infinity;
  for (const [i, j] of enOrdenDeLectura(ancho, fondo)) {
    if (ocupado.has(clave(i, j))) continue;
    const d = Math.abs(i - desde[0]) + Math.abs(j - desde[1]);
    if (d < distancia) { mejor = [i, j]; distancia = d; }
  }
  return mejor;
}

export function pasoSuelto(ancho, fondo, ocupado, desde, azar) {
  const libres = vecinasDe(ancho, fondo, desde).filter(([i, j]) => !ocupado.has(clave(i, j)));
  if (!libres.length) return desde;
  return libres[Math.min(libres.length - 1, Math.floor(azar() * libres.length))];
}

export function sitiosDeEntrada(ancho, fondo, ocupado, cuantos) {
  const libres = enOrdenDeLectura(ancho, fondo)
    .filter(([i, j]) => !ocupado.has(clave(i, j)))
    .sort((a, b) => (b[0] + b[1]) - (a[0] + a[1]) || a[0] - b[0]);
  if (!libres.length) return [];
  return Array.from({ length: cuantos }, (_, n) => libres[n % libres.length]);
}

export function lineaDeEstado(depto) {
  return `${depto.ancho} × ${depto.fondo} · ${ocupadas(depto)} de ${depto.casillas} casillas`
    + ` · camas ${depto.camas} · gachamones ${depto.gachamones}`
    + ` · comodidad ${depto.comodidad} de ${depto.tope}`;
}

export function nombreDelSitio(x, y) {
  if (x === -1) return `pared izquierda, tramo ${y + 1}`;
  if (y === -1) return `pared derecha, tramo ${x + 1}`;
  return `fila ${y + 1}, columna ${x + 1}`;
}
