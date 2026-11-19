import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as c from '../../web/static/js/caminantes.js';
import { laPuerta, noSePisan } from '../../web/static/js/casillas.js';

// Una pieza de 3 × 3 con la cama en la fila del medio, a la izquierda, y la
// puerta en la pared de la derecha, en su primer tramo (su casilla es (0, -1)
// y la de enfrente, (0, 0)):
//
//          i=0    i=1    i=2
//   j=-1  puerta
//   j=0    ·      ·      ·
//   j=1   cama   cama    ·
//   j=2    ·      ·      ·
const CAMA = { id: 1, clave: 'cama_sencilla', ancho: 2, fondo: 1, capa: 'bulto', x: 0, y: 1, giro: 0, casillas: [[0, 1], [1, 1]] };
const PUERTA = { id: 2, clave: 'puerta', ancho: 1, fondo: 1, capa: 'pared', puerta: true, x: 0, y: -1, giro: 0, casillas: [[0, -1]] };
const maceta = (i, j) => ({ id: 3, clave: 'maceta', ancho: 1, fondo: 1, capa: 'bulto', x: i, y: j, giro: 0, casillas: [[i, j]] });

function pieza(puestos = [CAMA, PUERTA], plantel = [{ id: 10 }, { id: 20 }]) {
  return { ancho: 3, fondo: 3, casillas: 9, puestos, guardados: [], plantel };
}

// Alguien en (i, j), con lo que le queda por pisar; por defecto, al paso de un gachamon.
const andando = (i, j, ruta = [], porSegundo = 2) => ({ i, j, ruta, espejo: false, porSegundo });
const dondeEsta = (quien) => [quien.i, quien.j];
const ordenadas = (casillas) => [...casillas].sort();

// Un azar que da esos valores por turnos y cuenta cuántas veces se le pidió.
function azarDe(...valores) {
  const azar = () => {
    azar.veces += 1;
    return valores[(azar.veces - 1) % valores.length];
  };
  azar.veces = 0;
  return azar;
}

test('un caminante empieza quieto en su casilla, mirando a la derecha, a su paso; sin casilla no hay', () => {
  assert.deepEqual(c.caminanteEn([1, 2], 2), { i: 1, j: 2, ruta: [], espejo: false, porSegundo: 2 });
  assert.equal(c.caminanteEn(null, 3), null);
  assert.equal(c.caminanteEn(undefined, 3), null);
});

test('al entrar, tú en la puerta y cada gachamon en un sitio de entrada libre y distinto', () => {
  const d = pieza();
  const { tu, enPieza } = c.repartir(d, null, new Map());
  assert.deepEqual(tu, { i: 0, j: -1, ruta: [], espejo: false, porSegundo: 3 });
  assert.deepEqual([...enPieza.keys()], [10, 20]);
  const casillas = [...enPieza.values()].map(dondeEsta);
  // El primer sitio de entrada, (2, 2), queda libre: tú entras por la puerta.
  assert.deepEqual(casillas, [[1, 2], [2, 1]]);
  const tapadas = noSePisan(d);
  for (const [i, j] of casillas) assert.ok(!tapadas.has(`${i},${j}`), `${i},${j}`);
  for (const g of enPieza.values()) assert.deepEqual([g.ruta, g.porSegundo], [[], 2]);
  // Sin puerta, tú entras por el primer sitio de entrada.
  const sinPuerta = c.repartir(pieza([CAMA]), null, new Map());
  assert.deepEqual(dondeEsta(sinPuerta.tu), [2, 2]);
  assert.deepEqual([...sinPuerta.enPieza.values()].map(dondeEsta), [[1, 2], [2, 1]]);
});

test('al repartir, el que ya estaba se reubica, el que llega entra por su sitio y el que se fue ya no está', () => {
  const d = pieza();
  // 10 quedó sobre la cama; 30 ya no vive contigo; 20 acaba de llegar.
  const antes = new Map([[10, andando(1, 1)], [30, andando(2, 0)]]);
  const { tu, enPieza } = c.repartir(d, andando(2, 2, [], 3), antes);
  assert.deepEqual(dondeEsta(tu), [2, 2]);
  assert.deepEqual([...enPieza.keys()], [10, 20]);
  assert.deepEqual(dondeEsta(enPieza.get(10)), [1, 0]);
  assert.deepEqual(dondeEsta(enPieza.get(20)), [2, 1]);
});

test('reubicar: sobre un mueble aparece en la libre más cercana; caminando, termina su paso y rehace el resto', () => {
  const d = pieza();
  const ocupado = noSePisan(d);
  // Sobre la cama: a la libre más cercana, sin caminar.
  const sobreLaCama = c.reubicar(d, andando(1, 1), ocupado);
  assert.deepEqual([...dondeEsta(sobreLaCama), sobreLaCama.ruta], [1, 0, []]);
  // Donde se pisa, se queda.
  assert.deepEqual(dondeEsta(c.reubicar(d, andando(2, 2), ocupado)), [2, 2]);
  // Una maceta nueva en medio del camino: el paso que da se termina y el resto se rehace, rodeándola.
  const conMaceta = pieza([maceta(1, 1)]);
  const rodea = c.reubicar(conMaceta, andando(0, 0, [[0, 1], [1, 1], [2, 1]]), noSePisan(conMaceta));
  assert.deepEqual(rodea.ruta, [[0, 1], [0, 2], [1, 2], [2, 2], [2, 1]]);
  // Si ya no se llega (la fila del medio queda tapada), termina el paso y se queda ahí.
  const partida = pieza([CAMA, maceta(2, 2)]);
  const corta = c.reubicar(partida, andando(2, 0, [[2, 1], [2, 2], [1, 2]]), noSePisan(partida));
  assert.deepEqual(corta.ruta, [[2, 1]]);
  // Si el paso que da ya no se pisa, no lo da: aparece donde estaba.
  const sinPaso = c.reubicar(conMaceta, andando(1, 0.25, [[1, 1], [1, 2]]), noSePisan(conMaceta));
  assert.deepEqual([...dondeEsta(sinPaso), sinPaso.ruta], [1, 0, []]);
  // La casilla de la puerta sólo se pisa con `puerta`; sin ella, a la de dentro más cercana.
  assert.deepEqual(dondeEsta(c.reubicar(d, andando(0, -1, [], 3), ocupado, laPuerta(d))), [0, -1]);
  assert.deepEqual(dondeEsta(c.reubicar(d, andando(0, -1), ocupado)), [0, 0]);
  // Sin casilla que se pise, `null`.
  assert.equal(c.reubicar({ ancho: 1, fondo: 1, puestos: [] }, andando(0, 0), new Set(['0,0'])), null);
});

test('reubicarte: tú entras por la puerta, sigues en ella si se movió y, sin sitio dentro, vas a ella', () => {
  const d = pieza();
  const ocupado = noSePisan(d);
  const puerta = laPuerta(d);
  assert.deepEqual(c.reubicarte(d, null, ocupado, puerta, [2, 2]), { i: 0, j: -1, ruta: [], espejo: false, porSegundo: 3 });
  assert.deepEqual(c.reubicarte(d, null, ocupado, null, [2, 2]), { i: 2, j: 2, ruta: [], espejo: false, porSegundo: 3 });
  assert.equal(c.reubicarte(d, null, ocupado, null, undefined), null);
  // Estabas entrando por la puerta de antes (tercer tramo) y ahora está en el primero: sigues en ella.
  const enLaDeAntes = c.reubicarte(d, andando(2, -1, [[2, 0]], 3), ocupado, puerta, [2, 2]);
  assert.deepEqual([...dondeEsta(enLaDeAntes), enLaDeAntes.ruta], [0, -1, []]);
  // Dentro, como cualquiera.
  assert.deepEqual(dondeEsta(c.reubicarte(d, andando(1, 1, [], 3), ocupado, puerta, [2, 2])), [1, 0]);
  // Si dentro no queda casilla que se pise, a la puerta.
  const llena = { ancho: 1, fondo: 1, puestos: [] };
  const fuera = c.reubicarte(llena, andando(0, 0, [], 3), new Set(['0,0']), { celda: [0, -1], dentro: [0, 0] }, undefined);
  assert.deepEqual(fuera, { i: 0, j: -1, ruta: [], espejo: false, porSegundo: 3 });
});

test('avanzar anda casilla tras casilla a su paso, mira hacia donde va y no se pasa del final', () => {
  const quien = andando(0, 0, [[1, 0], [1, 1]]);
  // A dos casillas por segundo, un cuarto de segundo es medio paso.
  c.avanzar(quien, 0.25);
  assert.deepEqual([quien.i, quien.j, quien.ruta.length, quien.espejo], [0.5, 0, 2, false]);
  // Con tiempo de sobra llega a la última y ahí se queda; ir hacia `j` es mirar a la izquierda.
  c.avanzar(quien, 10);
  assert.deepEqual([quien.i, quien.j, quien.ruta, quien.espejo], [1, 1, [], true]);
  c.avanzar(quien, 1);
  assert.deepEqual([quien.i, quien.j, quien.espejo], [1, 1, true]);
});

test('rutaHasta rodea los muebles, va a la puerta sólo con ella y da null sin camino', () => {
  const d = pieza();
  const puerta = laPuerta(d);
  // Rodea la cama.
  assert.deepEqual(c.rutaHasta(d, andando(0, 2), [0, 0]), [[1, 2], [2, 2], [2, 1], [2, 0], [1, 0], [0, 0]]);
  // A medio paso, lo termina y desde ahí va.
  assert.deepEqual(c.rutaHasta(d, andando(0.5, 0, [[1, 0], [2, 0]]), [2, 2]), [[1, 0], [2, 0], [2, 1], [2, 2]]);
  // A la puerta sólo con ella, por la casilla de enfrente; y desde ella, también.
  assert.equal(c.rutaHasta(d, andando(1, 0), [0, -1]), null);
  assert.deepEqual(c.rutaHasta(d, andando(1, 0, [], 3), [0, -1], puerta), [[0, 0], [0, -1]]);
  assert.deepEqual(c.rutaHasta(d, andando(0, -1, [], 3), [2, 0], puerta), [[0, 0], [1, 0], [2, 0]]);
  // Ya está ahí: nada que andar. Si ya va justo ahí, sólo le queda ese paso.
  assert.deepEqual(c.rutaHasta(d, andando(2, 2), [2, 2]), []);
  assert.deepEqual(c.rutaHasta(d, andando(1.5, 0, [[2, 0]]), [2, 0]), [[2, 0]]);
  // Sobre un mueble, sin camino que llegue, o sin nadie que camine: null.
  assert.equal(c.rutaHasta(d, andando(2, 2), [1, 1]), null);
  const partida = pieza([CAMA, maceta(2, 1), PUERTA]);
  assert.equal(c.rutaHasta(partida, andando(0, 2), [0, 0]), null);
  assert.equal(c.rutaHasta(d, null, [0, 0]), null);
  // No mueve a nadie: eso lo hace quien llama.
  const quieto = andando(0, 2);
  c.rutaHasta(d, quieto, [0, 0]);
  assert.deepEqual([...dondeEsta(quieto), quieto.ruta], [0, 2, []]);
});

test('noSePisanConGente cuenta los muebles, a ti y a los demás (donde estáis y adonde vais) y deja fuera a salvo', () => {
  const d = pieza();
  const tu = andando(0, 0, [[1, 0], [2, 0]], 3);
  const enPieza = new Map([[10, andando(1, 2)], [20, andando(2.4, 1, [[2, 2]])]]);
  assert.deepEqual(ordenadas(c.noSePisanConGente(d, tu, enPieza, 10)), ['0,0', '0,1', '1,1', '2,0', '2,1', '2,2']);
  assert.deepEqual(ordenadas(c.noSePisanConGente(d, tu, enPieza, 20)), ['0,0', '0,1', '1,1', '1,2', '2,0']);
  assert.deepEqual(ordenadas(c.noSePisanConGente(d, null, enPieza, 10)), ['0,1', '1,1', '2,1', '2,2']);
});

test('casillasDelGachamon da las que se pisan con camino desde donde está (o adonde va), menos ésa', () => {
  // La fila del medio, tapada: la pieza queda partida en dos.
  const d = pieza([CAMA, maceta(2, 1), PUERTA]);
  assert.deepEqual(c.casillasDelGachamon(d, andando(0, 0)), [{ x: 1, y: 0 }, { x: 2, y: 0 }]);
  assert.deepEqual(c.casillasDelGachamon(d, andando(1, 0, [[2, 0]])), [{ x: 0, y: 0 }, { x: 1, y: 0 }]);
  assert.deepEqual(c.casillasDelGachamon(d, andando(1, 2)), [{ x: 0, y: 2 }, { x: 2, y: 2 }]);
});

test('unPaseo: uno que está quieto da un paso a una vecina libre, pidiendo a azar quién y hacia dónde', () => {
  const d = pieza();
  const tu = andando(0, -1, [], 3);
  const losDos = () => new Map([[10, andando(1, 2)], [20, andando(2, 1)]]);
  let azar = azarDe(0, 0);
  const gente = losDos();
  assert.deepEqual(c.unPaseo(d, d.plantel, gente, tu, null, azar), { id: 10, ruta: [[2, 2]] });
  assert.equal(azar.veces, 2);
  // No mueve a nadie: eso lo hace quien llama.
  assert.deepEqual(gente.get(10).ruta, []);
  azar = azarDe(0.5, 0.5);
  assert.deepEqual(c.unPaseo(d, d.plantel, losDos(), tu, null, azar), { id: 20, ruta: [[2, 0]] });
  assert.equal(azar.veces, 2);
  // Con cualquier azar: un solo paso, a una casilla de al lado que nadie pisa, y nunca el elegido.
  const valores = [0, 0.2, 0.4, 0.6, 0.8, 0.99];
  for (const quien of valores) {
    for (const donde of valores) {
      const conElegido = losDos();
      const elDeAhora = azarDe(quien, donde);
      const paseo = c.unPaseo(d, d.plantel, conElegido, tu, 20, elDeAhora);
      assert.equal(paseo.id, 10);
      assert.equal(elDeAhora.veces, 2);
      assert.equal(paseo.ruta.length, 1);
      const [[i, j]] = paseo.ruta;
      assert.equal(Math.abs(i - 1) + Math.abs(j - 2), 1, `${i},${j}`);
      assert.ok(!c.noSePisanConGente(d, tu, conElegido, 10).has(`${i},${j}`), `${i},${j}`);
    }
  }
});

test('unPaseo: a azar se le pide primero quién y después hacia dónde', () => {
  const d = pieza();
  const tu = andando(0, -1, [], 3);
  const losDos = () => new Map([[10, andando(1, 2)], [20, andando(2, 1)]]);
  // Con valores distintos en cada turno, cambiar el orden cambia a quién le toca y adónde va.
  assert.deepEqual(c.unPaseo(d, d.plantel, losDos(), tu, null, azarDe(0, 0.99)), { id: 10, ruta: [[0, 2]] });
  assert.deepEqual(c.unPaseo(d, d.plantel, losDos(), tu, null, azarDe(0.99, 0)), { id: 20, ruta: [[2, 2]] });
});

test('unPaseo: sin nadie quieto da null sin pedir azar, y sin vecina libre da null', () => {
  const d = pieza();
  const tu = andando(0, -1, [], 3);
  // 10 ya camina, 20 es el elegido y 30 no tiene casilla.
  const enPieza = new Map([[10, andando(1, 2, [[2, 2]])], [20, andando(2, 1)]]);
  const azar = azarDe(0);
  assert.equal(c.unPaseo(d, [{ id: 10 }, { id: 20 }, { id: 30 }], enPieza, tu, 20, azar), null);
  assert.equal(azar.veces, 0);
  // Encerrado entre la cama, la pared y tú: no hay paso, y no se pide hacia dónde.
  const encerrado = new Map([[10, andando(0, 0)], [20, andando(1, 2)]]);
  const otro = azarDe(0);
  assert.equal(c.unPaseo(d, d.plantel, encerrado, andando(1, 0, [], 3), null, otro), null);
  assert.equal(otro.veces, 1);
});

// Uno de los muebles que se usan solos, como lo manda el servidor: con su marca
// `uso` (la pantalla sólo mira si la trae, no cuál es). Los demás la traen en `null`.
const queSeUsaSolo = (i, j, id = 4, uso = 'comida') => ({
  id, clave: 'refrigerador', ancho: 1, fondo: 1, capa: 'bulto', uso, x: i, y: j, giro: 0, casillas: [[i, j]],
});
const sinMarca = (puesto) => ({ ...puesto, uso: null });

// Una pieza de 4 × 4 con la puerta en la pared de la derecha, en su primer
// tramo, dos de los muebles que se usan solos, en (1, 1) y en (2, 3), y una
// maceta sin marca en (3, 1). Los lados de (1, 1), en el orden en que se
// cuentan, son (1, 2), (2, 1), (1, 0) y (0, 1); los de (2, 3), (3, 3), (2, 2) y
// (1, 3):
//
//          i=0    i=1    i=2    i=3
//   j=-1  puerta
//   j=0    ·      ·      ·      ·
//   j=1    ·     uso     ·    maceta
//   j=2    ·      ·      ·      ·
//   j=3    ·      ·     uso     ·
function conMuebles(plantel = [{ id: 10 }, { id: 20 }]) {
  const puestos = [PUERTA, queSeUsaSolo(1, 1, 4), queSeUsaSolo(2, 3, 5, 'fuerza'), sinMarca(maceta(3, 1))];
  return { ancho: 4, fondo: 4, casillas: 16, puestos, guardados: [], plantel };
}

// Si esa casilla está pegada por un lado (no en diagonal) a alguno de los muebles marcados.
const alLadoDeUnoMarcado = (d, [i, j]) => d.puestos.some((p) => p.uso
  && p.casillas.some(([a, b]) => Math.abs(a - i) + Math.abs(b - j) === 1));

test('unPaseoAUnMueble: uno quieto va hasta el lado de un mueble marcado, pidiendo a azar quién, a cuál y a qué casilla', () => {
  const d = conMuebles();
  const tu = andando(0, -1, [], 3);
  const losDos = () => new Map([[10, andando(0, 3)], [20, andando(3, 0)]]);
  // Con valores distintos en cada turno, cambiar el orden cambia a quién le toca, a qué mueble o a qué lado.
  let azar = azarDe(0, 0.99, 0.5);
  const gente = losDos();
  assert.deepEqual(c.unPaseoAUnMueble(d, d.plantel, gente, tu, null, azar), { id: 10, ruta: [[1, 3], [1, 2], [2, 2]] });
  assert.equal(azar.veces, 3);
  // No mueve a nadie: eso lo hace quien llama.
  assert.deepEqual([...dondeEsta(gente.get(10)), gente.get(10).ruta], [0, 3, []]);
  azar = azarDe(0.99, 0, 0.5);
  assert.deepEqual(c.unPaseoAUnMueble(d, d.plantel, losDos(), tu, null, azar), { id: 20, ruta: [[2, 0], [1, 0]] });
  assert.equal(azar.veces, 3);
});

test('unPaseoAUnMueble: con cualquier azar, acaba pegado a un mueble marcado y nunca sobre un mueble, sobre ti, sobre otro ni en la puerta', () => {
  const d = conMuebles([{ id: 10 }, { id: 20 }, { id: 30 }]);
  // Tú, a un lado de (1, 1); 20, el elegido, a otro; y 30, camino de un tercero.
  const tu = andando(1, 0, [], 3);
  const gente = () => new Map([[10, andando(0, 3)], [20, andando(2, 1)], [30, andando(0, 2, [[0, 1]])]]);
  const tapadas = noSePisan(d);
  const valores = [0, 0.3, 0.6, 0.99];
  const llegadas = new Set();
  for (const quien of valores) {
    for (const cual of valores) {
      for (const donde of valores) {
        const enPieza = gente();
        const azar = azarDe(quien, cual, donde);
        const paseo = c.unPaseoAUnMueble(d, d.plantel, enPieza, tu, 20, azar);
        assert.equal(paseo.id, 10);
        assert.equal(azar.veces, 3);
        const fin = paseo.ruta.at(-1);
        llegadas.add(String(fin));
        assert.ok(alLadoDeUnoMarcado(d, fin), String(fin));
        assert.ok(fin[0] >= 0 && fin[1] >= 0, String(fin));                 // dentro: nunca en la puerta
        assert.ok(!c.noSePisanConGente(d, tu, enPieza, 10).has(String(fin)), String(fin));
        // Un camino de verdad: casilla a casilla, desde donde está, sin pisar lo que no se pisa.
        let antes = [0, 3];
        for (const paso of paseo.ruta) {
          assert.equal(Math.abs(paso[0] - antes[0]) + Math.abs(paso[1] - antes[1]), 1, String(paso));
          assert.ok(!tapadas.has(String(paso)), String(paso));
          antes = paso;
        }
      }
    }
  }
  // Va a los lados libres de los dos: ni a (1, 0) (tú), ni a (2, 1) (el elegido), ni a (0, 1) (adonde va 30).
  assert.deepEqual([...llegadas].sort(), ['1,2', '1,3', '2,2', '3,3']);
});

test('unPaseoAUnMueble: un mueble marcado sin un lado adonde ir no se elige', () => {
  // (0, 0) sólo tiene un lado en la pieza, (1, 0), y estás tú; (2, 2) tiene libres (2, 1) y (1, 2).
  const d = pieza([CAMA, PUERTA, queSeUsaSolo(0, 0, 4), queSeUsaSolo(2, 2, 5)], [{ id: 10 }]);
  const tu = andando(1, 0, [], 3);
  for (const cual of [0, 0.5, 0.99]) {
    const paseo = c.unPaseoAUnMueble(d, d.plantel, new Map([[10, andando(2, 0)]]), tu, null, azarDe(0, cual, 0));
    assert.deepEqual(paseo, { id: 10, ruta: [[2, 1]] });
  }
});

test('unPaseoAUnMueble: sin muebles marcados o sin nadie quieto da null sin pedir azar', () => {
  const tu = andando(0, -1, [], 3);
  const gente = new Map([[10, andando(1, 2)], [20, andando(2, 1)]]);
  // Ninguno trae la marca: la pieza de siempre, y una maceta con la marca en `null`.
  for (const d of [pieza(), pieza([CAMA, PUERTA, sinMarca(maceta(2, 2))])]) {
    const azar = azarDe(0);
    assert.equal(c.unPaseoAUnMueble(d, d.plantel, gente, tu, null, azar), null);
    assert.equal(azar.veces, 0);
  }
  // 10 ya camina y 20 es el elegido.
  const d = conMuebles();
  const azar = azarDe(0);
  const nadie = new Map([[10, andando(0, 3, [[0, 2]])], [20, andando(3, 0)]]);
  assert.equal(c.unPaseoAUnMueble(d, d.plantel, nadie, tu, 20, azar), null);
  assert.equal(azar.veces, 0);
});

test('unPaseoAUnMueble: con el mueble rodeado, sin camino hasta él o ya a su lado, null tras pedir sólo quién', () => {
  // (0, 0) sólo tiene un lado en la pieza, (1, 0): la cama, la pared y la puerta le tapan los otros.
  const rincon = pieza([CAMA, PUERTA, queSeUsaSolo(0, 0)], [{ id: 10 }, { id: 20 }]);
  const casos = [
    // Ese lado lo pisas tú.
    [rincon, andando(1, 0, [], 3), new Map([[10, andando(2, 2)]])],
    // Ese lado lo pisa otro, o es adonde va.
    [rincon, andando(0, -1, [], 3), new Map([[10, andando(2, 2)], [20, andando(1, 0)]])],
    [rincon, andando(0, -1, [], 3), new Map([[10, andando(2, 2)], [20, andando(2, 0, [[1, 0]])]])],
    // Ya está en él: no cuenta como ir.
    [rincon, andando(0, -1, [], 3), new Map([[10, andando(1, 0)]])],
    // La fila del medio, tapada: desde abajo no hay camino a sus lados, (0, 0) y (2, 0).
    [pieza([CAMA, PUERTA, maceta(2, 1), queSeUsaSolo(1, 0)]), andando(0, -1, [], 3), new Map([[10, andando(1, 2)]])],
  ];
  for (const [d, tu, enPieza] of casos) {
    const azar = azarDe(0);
    assert.equal(c.unPaseoAUnMueble(d, d.plantel, enPieza, tu, null, azar), null);
    assert.equal(azar.veces, 1);
  }
});

test('es puro: no toca la página, ni la red, ni el reloj, ni Math.random, y sólo importa lo puro', () => {
  const codigo = readFileSync(new URL('../../web/static/js/caminantes.js', import.meta.url), 'utf8')
    .replace(/\/\/.*$/gm, '');
  for (const prohibido of ['document', 'window', 'fetch', 'Date', 'performance', 'Math\\.random', 'setTimeout',
    'requestAnimationFrame']) {
    assert.ok(!new RegExp(`\\b${prohibido}\\b`).test(codigo), prohibido);
  }
  const importa = [...codigo.matchAll(/from '([^']+)'/g)].map((m) => m[1]);
  assert.ok(importa.length > 0);
  for (const modulo of importa) assert.ok(['./casillas.js', './proyeccion.js'].includes(modulo), modulo);
});
