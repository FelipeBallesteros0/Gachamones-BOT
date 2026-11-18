// Quién está en qué casilla de la pieza y hacia dónde camina: tu avatar y tus
// gachamones. Es puro, como `casillas.js`: sin pantalla, sin reloj, sin red.
// Dónde está cada uno lo guarda la pantalla (`departamento.js`) y entra por
// parámetro, y el azar entra como función. Dónde está parado cada uno es sólo
// del dibujo: no se guarda ni se manda.
//
// Un caminante es `{i, j, ruta, espejo, porSegundo}`: dónde está (con
// decimales a medio paso), las casillas que le quedan por pisar, si mira a la
// izquierda y cuántas casillas anda por segundo. Lo que lo reubica o lo hace
// andar lo cambia a él mismo y lo devuelve; lo que sólo cuenta (`rutaHasta`,
// `unPaseo`) no mueve a nadie: lo mueve quien llama.
//
// Al entrar apareces en la puerta, una casilla más, fuera de la pieza (sin
// puerta, en el primero de los sitios de entrada), y tus gachamones se
// reparten por los sitios de entrada, en el orden en que llegan. Se camina de
// casilla en casilla por el camino más corto, rodeando lo que no se pisa; si
// los muebles cierran el paso, no se va. A la puerta sólo vas tú, por la
// casilla de enfrente. Un gachamon que da un paso solo va a una casilla de al
// lado que esté libre: ni bajo un mueble, ni donde estáis (o adonde vais) tú
// y los demás.

import { camino, laPuerta, libreMasCercana, noSePisan, pasoSuelto, sitiosDeEntrada } from './casillas.js';

// Lo que anda tu avatar, y lo que anda un gachamon, en casillas por segundo.
const CASILLAS_POR_SEGUNDO = 3;
const PASOS_DEL_GACHAMON = 2;

// Alguien que camina por la pieza en esa casilla, a tantas casillas por
// segundo: dónde está (con decimales a medio paso), las casillas que le quedan
// por pisar y si mira a la izquierda. `null` si no hay casilla.
export function caminanteEn(sitio, porSegundo) {
  return sitio ? { i: sitio[0], j: sitio[1], ruta: [], espejo: false, porSegundo } : null;
}

// Quien camina, en la pieza que llegó (`ocupado`, lo que no se pisa): si
// quedó sobre un mueble (o fuera), aparece en la casilla libre más cercana,
// sin caminar. Si iba caminando, el paso que está dando se termina si esa
// casilla se sigue pisando (si no, aparece) y el resto del camino se rehace;
// si ya no se llega, se queda ahí. Con `puerta` (sólo tú), su casilla se
// pisa, y a medio paso entre ella y la de enfrente se está en ella. `null` si
// no queda casilla que se pise.
export function reubicar(depto, quien, ocupado, puerta = null) {
  const esLaPuerta = ([i, j]) => puerta !== null && i === puerta.celda[0] && j === puerta.celda[1];
  const sePisa = ([i, j]) => esLaPuerta([i, j])
    || (i >= 0 && j >= 0 && i < depto.ancho && j < depto.fondo && !ocupado.has(`${i},${j}`));
  if (quien.ruta.length > 0) {
    const [paso, ...resto] = quien.ruta;
    if (sePisa(paso)) {
      if (!resto.every(sePisa)) {
        const destino = quien.ruta.at(-1);
        quien.ruta = [paso, ...(sePisa(destino) ? camino(depto.ancho, depto.fondo, ocupado, paso, destino, puerta) : [])];
      }
      return quien;
    }
    quien.ruta = [];
  }
  const fuera = quien.i < 0 || quien.j < 0;
  const aqui = puerta && fuera ? puerta.celda : [Math.round(quien.i), Math.round(quien.j)];
  const donde = sePisa(aqui) ? aqui : libreMasCercana(depto.ancho, depto.fondo, ocupado, aqui);
  if (!donde) return null;
  [quien.i, quien.j] = donde;
  return quien;
}

// Tú (`tu`, o `null` si todavía no estabas), en la pieza que llegó
// (`entrada`, tu sitio de entrada si no hay puerta). Al entrar apareces en la
// puerta. Si estabas en ella (o entrando o saliendo por ella) y ahora está en
// otro sitio, sigues en ella, donde esté; si estabas dentro, te reubicas como
// cualquiera, y si dentro ya no queda casilla que se pise, vas a la puerta.
export function reubicarte(depto, tu, ocupado, puerta, entrada) {
  const enLaPuerta = () => caminanteEn(puerta && puerta.celda, CASILLAS_POR_SEGUNDO);
  if (!tu) return puerta ? enLaPuerta() : caminanteEn(entrada, CASILLAS_POR_SEGUNDO);
  const fuera = tu.i < 0 || tu.j < 0;
  const suPuerta = tu.i < 0 ? [-1, tu.j] : [tu.i, -1];
  if (fuera && !(puerta && suPuerta[0] === puerta.celda[0] && suPuerta[1] === puerta.celda[1])) {
    tu.ruta = [];
    if (puerta) [tu.i, tu.j] = puerta.celda;
  }
  return reubicar(depto, tu, ocupado, puerta) || enLaPuerta();
}

// Tú y tus gachamones, en la pieza que llegó (`enPiezaAntes`, los que había,
// por id): el que ya estaba se reubica; el que todavía no estaba (al entrar,
// uno que llega, o el que no tenía casilla) entra por su sitio de entrada: tú
// el primero, ellos en el orden de `depto.plantel`. Con puerta, tú entras por
// ella y el primer sitio se queda libre: ellos entran donde siempre. El que ya
// no vive contigo se va. Devuelve `{tu, enPieza}`: tú (o `null`, si no queda
// casilla que se pise) y, por id, los que tienen casilla.
export function repartir(depto, tu, enPiezaAntes) {
  const ocupado = noSePisan(depto);
  const entrada = sitiosDeEntrada(depto.ancho, depto.fondo, ocupado, depto.plantel.length + 1);
  const tuAhora = reubicarte(depto, tu, ocupado, laPuerta(depto), entrada[0]);
  const enPieza = new Map();
  depto.plantel.forEach((g, n) => {
    const ya = enPiezaAntes.get(g.id);
    const quien = ya ? reubicar(depto, ya, ocupado) : caminanteEn(entrada[n + 1], PASOS_DEL_GACHAMON);
    if (quien) enPieza.set(g.id, quien);
  });
  return { tu: tuAhora, enPieza };
}

// Lo que anda quien camina en `dt` segundos, casilla tras casilla, sin pasarse de la última.
export function avanzar(quien, dt) {
  let queda = quien.porSegundo * dt;
  while (quien.ruta.length > 0 && queda > 0) {
    const [hastaI, hastaJ] = quien.ruta[0];
    const di = hastaI - quien.i;
    const dj = hastaJ - quien.j;
    // Ir hacia `j` o volver por `i` es ir hacia la izquierda de la pantalla.
    if (di !== dj) quien.espejo = di < dj;
    const falta = Math.abs(di) + Math.abs(dj);
    if (falta <= queda) {
      quien.i = hastaI;
      quien.j = hastaJ;
      quien.ruta.shift();
      queda -= falta;
    } else {
      const enI = Math.min(queda, Math.abs(di));
      quien.i += Math.sign(di) * enI;
      quien.j += Math.sign(dj) * (queda - enI);
      queda = 0;
    }
  }
}

// La ruta con la que quien camina llega a esa casilla por el camino más
// corto; con `puerta` (sólo tú), también hasta su casilla y desde ella, por la
// de enfrente. A medio paso, se termina el paso y desde ahí se va: la ruta
// empieza por él. `[]` si ya está ahí, parado; `null` si no va (no hay quien
// camine, la casilla no se pisa o los muebles le cierran el paso).
export function rutaHasta(depto, quien, [i, j], puerta = null) {
  const ocupado = noSePisan(depto);
  if (!quien || ocupado.has(`${i},${j}`)) return null;
  const desde = quien.ruta.length > 0 ? quien.ruta[0] : [quien.i, quien.j];
  if (quien.ruta.length === 0 && desde[0] === i && desde[1] === j) return [];
  const pasos = camino(depto.ancho, depto.fondo, ocupado, desde, [i, j], puerta);
  const yaVaAhi = desde[0] === i && desde[1] === j;
  if (pasos.length === 0 && !yaVaAhi) return null;
  return quien.ruta.length > 0 ? [quien.ruta[0], ...pasos] : pasos;
}

// Lo que no pisa un gachamon que da un paso solo: los muebles, y donde
// estáis (o adonde vais) tú y los demás (`enPieza`, por id), salvo él mismo
// (`salvo`, su id).
export function noSePisanConGente(depto, tu, enPieza, salvo) {
  const ocupado = noSePisan(depto);
  const pisar = (quien) => {
    for (const [i, j] of [[Math.round(quien.i), Math.round(quien.j)], ...quien.ruta.slice(-1)]) ocupado.add(`${i},${j}`);
  };
  if (tu) pisar(tu);
  for (const [id, quien] of enPieza) if (id !== salvo) pisar(quien);
  return ocupado;
}

// Las casillas donde un gachamon puede ir, como `{x, y}`: las que se pisan y a
// las que tiene camino desde donde está (o adonde ya va), menos ésa (`camino`
// no da ninguno hasta donde ya se está).
export function casillasDelGachamon(depto, quien) {
  const ocupado = noSePisan(depto);
  const aqui = quien.ruta.length > 0 ? quien.ruta.at(-1) : [quien.i, quien.j];
  const sitios = [];
  for (let y = 0; y < depto.fondo; y += 1) {
    for (let x = 0; x < depto.ancho; x += 1) {
      if (camino(depto.ancho, depto.fondo, ocupado, aqui, [x, y]).length > 0) sitios.push({ x, y });
    }
  }
  return sitios;
}

// El paso que da solo uno de tus gachamones (los de `plantel` que tienen
// casilla en `enPieza`) que está quieto, salvo el elegido (`elegidoG`, que
// tiene su menú abierto): hacia una casilla de al lado que esté libre. A
// `azar` se le pide quién y, si tiene adónde ir, hacia dónde. `{id, ruta}`, o
// `null` si nadie está quieto o el que tocó no tiene adónde ir.
export function unPaseo(depto, plantel, enPieza, tu, elegidoG, azar) {
  const quietos = plantel.map((g) => g.id)
    .filter((id) => id !== elegidoG && enPieza.has(id) && enPieza.get(id).ruta.length === 0);
  if (!quietos.length) return null;
  const id = quietos[Math.min(quietos.length - 1, Math.floor(azar() * quietos.length))];
  const quien = enPieza.get(id);
  const [i, j] = pasoSuelto(depto.ancho, depto.fondo, noSePisanConGente(depto, tu, enPieza, id), [quien.i, quien.j], azar);
  if (i === quien.i && j === quien.j) return null;
  return { id, ruta: [[i, j]] };
}
