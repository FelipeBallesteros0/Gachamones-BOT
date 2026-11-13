// La lógica del pueblo, sin pantalla: el camino más corto, la caminata del
// avatar, el gachamon que lo sigue por su rastro, la cámara y qué lugar se
// tocó. Puro: no toca la página ni el reloj; el tiempo le llega como `dt`, en
// segundos.
//
// Todo sale de los datos del pueblo (`pueblo.json`): `ancho` y `alto`,
// `velocidad` (unidades por segundo), `hueco` (lo que el gachamon va detrás),
// `lugares`, `nodos` (clave → [x, y]) y `aristas` (pares de nodos). Cada lugar
// se para en el nodo de su misma clave; hay nodos que no son lugares.

const ANCHO_DEL_PUEBLO_ENTERO = 900; // en píxeles: desde aquí se ve todo
const SUAVIDAD_DE_LA_CAMARA = 5;
const MARGEN_DE_LAS_FLECHAS = 2;
const TOQUE_A_LO_ANCHO = 40; // un lugar se toca a menos de esto de su nodo
const DIBUJO_ARRIBA = 70; // un lugar se dibuja de esto por encima de su nodo…
const DIBUJO_ABAJO = 12; // …a esto por debajo
const ALTO_DEL_SALTO = 5;
const SEGUNDOS_POR_SALTO = 0.18;
const CASI_NADA = 1e-9;

function limitar(valor, minimo, maximo) {
  return Math.max(minimo, Math.min(maximo, valor));
}

function distancia(ax, ay, bx, by) {
  return Math.hypot(bx - ax, by - ay);
}

// Los vecinos de cada nodo y lo que hay hasta cada uno:
// `{a: {b: 90, c: 45}, b: {a: 90}, c: {a: 45}}`.
export function armarGrafo(datos) {
  const grafo = {};
  for (const nodo of Object.keys(datos.nodos)) grafo[nodo] = {};
  for (const [a, b] of datos.aristas) {
    const [ax, ay] = datos.nodos[a];
    const [bx, by] = datos.nodos[b];
    const largo = distancia(ax, ay, bx, by);
    grafo[a][b] = largo;
    grafo[b][a] = largo;
  }
  return grafo;
}

// El camino más corto de un nodo a otro, con los dos extremos, y su largo.
// Si no hay camino (o un nodo no existe), `{camino: [], largo: Infinity}`.
export function ruta(grafo, desde, hasta) {
  const sinCamino = { camino: [], largo: Infinity };
  if (!Object.hasOwn(grafo, desde) || !Object.hasOwn(grafo, hasta)) return sinCamino;
  const largos = new Map([[desde, 0]]);
  const previo = new Map();
  const cerrados = new Set();
  for (;;) {
    let actual = null;
    for (const [nodo, largo] of largos) {
      if (!cerrados.has(nodo) && (actual === null || largo < largos.get(actual))) actual = nodo;
    }
    if (actual === null) return sinCamino;
    if (actual === hasta) break;
    cerrados.add(actual);
    for (const [vecino, tramo] of Object.entries(grafo[actual])) {
      const largo = largos.get(actual) + tramo;
      if (!largos.has(vecino) || largo < largos.get(vecino)) {
        largos.set(vecino, largo);
        previo.set(vecino, actual);
      }
    }
  }
  const camino = [hasta];
  while (camino[0] !== desde) camino.unshift(previo.get(camino[0]));
  return { camino, largo: largos.get(hasta) };
}

// El avatar parado en `lugar`, mirando a la derecha, con el gachamon `hueco`
// más a la izquierda. `en` es el último nodo alcanzado (lugar o cruce) y `t`,
// los segundos que lleva caminados. Además de lo que lee la pantalla, guarda:
// `cola`, los nodos que le faltan (el primero es al que va); `desde`, el otro
// extremo del tramo en que está (al que volvería), y `rastro`, las esquinas
// por las que pasó hace poco, de la más vieja a la más nueva.
export function crearPaseo(datos, grafo, lugar) {
  const [x, y] = datos.nodos[lugar];
  return {
    datos,
    grafo,
    x,
    y,
    mira: 1,
    caminando: false,
    destino: null,
    en: lugar,
    gx: x - datos.hueco,
    gy: y,
    gmira: 1,
    gcaminando: false,
    t: 0,
    cola: [],
    desde: lugar,
    rastro: [[x - datos.hueco, y], [x, y]],
  };
}

function anotarEsquina(paseo) {
  const ultima = paseo.rastro[paseo.rastro.length - 1];
  if (!ultima || ultima[0] !== paseo.x || ultima[1] !== paseo.y) paseo.rastro.push([paseo.x, paseo.y]);
}

function hastaElNodo(paseo, nodo) {
  const [nx, ny] = paseo.datos.nodos[nodo];
  return distancia(paseo.x, paseo.y, nx, ny);
}

// Fija el destino. Parado en ese mismo lugar: `'llego'`, sin moverse. Parado
// en otro: sale por el camino más corto. Caminando: cambia de rumbo desde
// donde está, siguiendo hasta el nodo al que iba o volviendo al que dejó, lo
// que dé el camino total más corto (si da lo mismo, sigue). Lo que no es un
// lugar, o un lugar al que no se llega: `'nada'`.
export function ir(paseo, lugar) {
  const { datos, grafo } = paseo;
  if (!Object.hasOwn(datos.lugares, lugar)) return 'nada';
  if (!paseo.caminando) {
    if (lugar === paseo.en) return 'llego';
    const { camino } = ruta(grafo, paseo.en, lugar);
    if (!camino.length) return 'nada';
    paseo.cola = camino.slice(1);
  } else if (lugar !== paseo.destino) {
    const hacia = paseo.cola[0];
    const seguir = ruta(grafo, hacia, lugar);
    const volver = ruta(grafo, paseo.desde, lugar);
    const porSeguir = hastaElNodo(paseo, hacia) + seguir.largo;
    const porVolver = hastaElNodo(paseo, paseo.desde) + volver.largo;
    if (!Number.isFinite(Math.min(porSeguir, porVolver))) return 'nada';
    if (porSeguir <= porVolver) {
      paseo.cola = seguir.camino;
    } else {
      anotarEsquina(paseo);
      paseo.cola = volver.camino;
      paseo.desde = hacia;
    }
  }
  paseo.destino = lugar;
  paseo.caminando = true;
  return 'camina';
}

function pararEnElDestino(paseo) {
  paseo.cola = [];
  paseo.caminando = false;
  paseo.destino = null;
}

// Pone al gachamon `hueco` detrás del avatar, contado por el rastro, y olvida
// las esquinas que ya quedaron más atrás que él. Mira hacia donde lleva el
// tramo del rastro en que está.
function seguirElRastro(paseo) {
  const { rastro } = paseo;
  let falta = paseo.datos.hueco;
  let [ax, ay] = [paseo.x, paseo.y];
  let [gx, gy] = [ax, ay];
  let haciaX = 0;
  let i = rastro.length - 1;
  for (; i >= 0; i -= 1) {
    const [bx, by] = rastro[i];
    const tramo = distancia(ax, ay, bx, by);
    if (tramo > 0 && tramo >= falta) {
      gx = ax + ((bx - ax) / tramo) * falta;
      gy = ay + ((by - ay) / tramo) * falta;
      haciaX = ax - bx;
      break;
    }
    falta -= tramo;
    [ax, ay] = [bx, by];
    [gx, gy] = [ax, ay];
  }
  rastro.splice(0, Math.max(0, i));
  paseo.gcaminando = distancia(paseo.gx, paseo.gy, gx, gy) > CASI_NADA;
  if (Math.abs(haciaX) > CASI_NADA) paseo.gmira = Math.sign(haciaX);
  paseo.gx = gx;
  paseo.gy = gy;
}

// Mueve al avatar `velocidad × dt` por su camino y al gachamon por el rastro.
// Un `dt` grande llega al destino sin pasarse; uno nulo o negativo no hace
// nada. Devuelve `true` sólo en el paso en que llega.
export function avanzar(paseo, dt) {
  if (!(dt > 0)) return false;
  let llego = false;
  if (paseo.caminando) {
    const { nodos, velocidad } = paseo.datos;
    let queda = velocidad * dt;
    let andado = 0;
    while (queda > 0 && paseo.cola.length) {
      const [nx, ny] = nodos[paseo.cola[0]];
      const dx = nx - paseo.x;
      const dy = ny - paseo.y;
      const tramo = Math.hypot(dx, dy);
      if (Math.abs(dx) > CASI_NADA) paseo.mira = Math.sign(dx);
      if (tramo <= queda) {
        paseo.x = nx;
        paseo.y = ny;
        queda -= tramo;
        andado += tramo;
        paseo.en = paseo.cola.shift();
        paseo.desde = paseo.en;
        anotarEsquina(paseo);
      } else {
        paseo.x += (dx / tramo) * queda;
        paseo.y += (dy / tramo) * queda;
        andado += queda;
        queda = 0;
      }
    }
    paseo.t += andado / velocidad;
    if (!paseo.cola.length) {
      pararEnElDestino(paseo);
      llego = true;
    }
  }
  seguirElRastro(paseo);
  return llego;
}

// Lo deja en el destino de inmediato, como si hubiera hecho el resto del
// camino: el gachamon queda `hueco` detrás, sobre el último tramo, y quieto.
// `false` si no tenía destino.
export function llegarYa(paseo) {
  if (paseo.destino === null) return false;
  const { nodos } = paseo.datos;
  for (const nodo of paseo.cola) {
    const [nx, ny] = nodos[nodo];
    if (Math.abs(nx - paseo.x) > CASI_NADA) paseo.mira = Math.sign(nx - paseo.x);
    paseo.x = nx;
    paseo.y = ny;
    paseo.en = nodo;
    paseo.desde = nodo;
    anotarEsquina(paseo);
  }
  pararEnElDestino(paseo);
  seguirElRastro(paseo);
  paseo.gcaminando = false;
  return true;
}

// Cuánto sube el gachamon en este instante: un saltito cada 0,18 s al caminar.
export function salto(t, caminando) {
  return caminando ? ALTO_DEL_SALTO * Math.abs(Math.sin((Math.PI * t) / SEGUNDOS_POR_SALTO)) : 0;
}

// Desde 900 px de ancho se ve el pueblo entero; más angosto, se llena lo alto
// y se ve un trozo. `anchoVista` es cuánto pueblo cabe a lo ancho.
export function encuadre(anchoPx, altoPx, datos) {
  const completo = anchoPx >= ANCHO_DEL_PUEBLO_ENTERO;
  const escala = completo ? Math.min(anchoPx / datos.ancho, altoPx / datos.alto) : altoPx / datos.alto;
  return { escala, completo, anchoVista: anchoPx / escala };
}

// La cámara es la x del lado izquierdo de lo que se ve, en unidades del
// pueblo: nunca negativa ni tan grande que se vea más allá del pueblo.
function camaraMaxima(anchoVista, datos) {
  return Math.max(0, datos.ancho - anchoVista);
}

export function camaraHacia(x, anchoVista, datos) {
  return limitar(x - anchoVista / 2, 0, camaraMaxima(anchoVista, datos));
}

export function acercarCamara(camara, objetivo, dt) {
  return camara + (objetivo - camara) * Math.min(1, SUAVIDAD_DE_LA_CAMARA * dt);
}

export function arrastrarCamara(camaraAlTocar, dxPx, escala, anchoVista, datos) {
  return limitar(camaraAlTocar - dxPx / escala, 0, camaraMaxima(anchoVista, datos));
}

export function flechas(camara, anchoVista, datos) {
  return {
    izquierda: camara > MARGEN_DE_LAS_FLECHAS,
    derecha: camara < camaraMaxima(anchoVista, datos) - MARGEN_DE_LAS_FLECHAS,
  };
}

// El lugar tocado en un punto del pueblo: entre los que tienen su nodo a menos
// de 40 unidades a lo ancho y cuyo dibujo contiene ese alto, el de nodo más
// cercano al punto. `null` si no se tocó ninguno.
export function lugarEn(datos, x, y) {
  let elegido = null;
  let menor = Infinity;
  for (const lugar of Object.keys(datos.lugares)) {
    const [nx, ny] = datos.nodos[lugar];
    if (Math.abs(x - nx) >= TOQUE_A_LO_ANCHO || y < ny - DIBUJO_ARRIBA || y > ny + DIBUJO_ABAJO) continue;
    const lejos = distancia(x, y, nx, ny);
    if (lejos < menor) {
      elegido = lugar;
      menor = lejos;
    }
  }
  return elegido;
}
