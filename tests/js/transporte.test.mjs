import test from 'node:test';
import assert from 'node:assert/strict';
import { conReintentos } from '../../web/static/js/api.js';
import { lineaDeEstado } from '../../web/static/js/casillas.js';
import { transporte } from '../../web/static/js/transporte.js';

// La pestaña: si se ve o no. Lo único del navegador que mira el transporte.
globalThis.document = { hidden: false };

// Deja correr todo lo que ya está en camino (respuestas, promesas encadenadas).
async function asentar() {
  for (let vuelta = 0; vuelta < 20; vuelta += 1) await new Promise((listo) => { setImmediate(listo); });
}

// Lo que lanza `pedir` cuando no sale bien (`api.js`): sin red, la clave es `null`.
const SIN_RED = { estado: 0, clave: null, mensaje: 'No hay conexión con el juego. Revisa tu internet y vuelve a intentarlo.' };
const NO_CABE = { estado: 400, clave: 'no_cabe', mensaje: 'Ahí no cabe.' };
const SIN_SESION = { estado: 401, clave: 'sin_sesion', mensaje: 'Tienes que entrar de nuevo.' };
const OTRA_PANTALLA = { estado: 409, clave: 'no_estas_ahi', mensaje: 'Para eso tienes que estar en tu departamento.' };

const SIN_RESPUESTA = 'No hubo respuesta. Revisa tu conexión.';

const ESTADO = { lugar: { clave: 'casa', nombre: 'Tu departamento' }, saldos: { monedas: 130, gemas: 2 } };
const pieza = (comodidad) => ({
  ancho: 3, fondo: 3, casillas: 9, camas: 1, gachamones: 1, comodidad, tope: 100, puestos: [], guardados: [], plantel: [],
});
const PIEZA = pieza(82);
const OTRA_PIEZA = pieza(90);
// Una pieza que revienta al ponerla.
const ROTA = { ...pieza(82), rota: true };

// Lo que mandó la petición (para el transporte es sólo algo que espera).
const GUARDAR = { boton: 'Guardar' };
const BANAR = { boton: 'Bañar' };

// Un transporte con un servidor de mentira y una pantalla de mentira que
// apunta, en orden, todo lo que el transporte le pide (`hechos`).
//
// El servidor contesta a cada `«MÉTODO ruta»` lo que se le diga (`responde`;
// una función, lo que dé en cada vuelta): un objeto con `estado` numérico se
// lanza, como lanza `pedir` lo que no sale bien. `retiene` deja en camino la
// próxima petición a esa ruta hasta soltarla con lo que contesta.
//
// La pantalla sigue ahí (`pantalla.sigue`), ya tiene su pieza
// (`pantalla.conPieza`) y el estado que llega no pide otra pantalla
// (`pantalla.otraPantalla`) hasta que una prueba diga lo contrario. Lo que
// revienta al pintar lo recoge `pintar`, como la avería de la pantalla. Cada
// vez que se le pide esperar o dejar de esperar, la pantalla mira qué dice el
// transporte que va en camino (`alEsperar`): lo que pinta lo lee de ahí.
function montar({ conPieza = true } = {}) {
  const pedidos = [];
  const respuestas = new Map([['GET estado', ESTADO], ['GET departamento', PIEZA]]);
  const retenidas = new Map();
  const hechos = [];
  const alEsperar = [];
  const pantalla = { sigue: true, conPieza, otraPantalla: false };

  async function pedir(metodo, ruta, cuerpo) {
    const clave = `${metodo} ${ruta}`;
    pedidos.push(cuerpo === undefined ? [clave] : [clave, cuerpo]);
    let contesta;
    if (retenidas.has(clave)) {
      const espera = retenidas.get(clave);
      retenidas.delete(clave);
      contesta = await espera;
    } else {
      contesta = respuestas.get(clave);
      if (typeof contesta === 'function') contesta = contesta();
    }
    if (contesta && typeof contesta.estado === 'number') throw contesta;
    return contesta;
  }

  const envios = transporte({
    pedir,
    sigueAqui: () => pantalla.sigue,
    hayPieza: () => pantalla.conPieza,
    esperar: (origen) => {
      hechos.push(['esperar', origen]);
      alEsperar.push([envios.enCamino, envios.origen]);
    },
    dejarDeEsperar: (origen) => {
      hechos.push(['dejarDeEsperar', origen]);
      alEsperar.push([envios.enCamino, envios.origen]);
    },
    decir: (texto, esError = false) => { hechos.push(['decir', texto, esError]); },
    anunciar: (texto) => { hechos.push(['anunciar', texto]); },
    irse: (...argumentos) => { hechos.push(['irse', ...argumentos]); },
    pintar: (pintarlo) => {
      hechos.push(['pintar']);
      try {
        pintarlo();
      } catch (error) {
        hechos.push(['reventó', error.message]);
      }
    },
    aplicarEstado: (estado) => {
      hechos.push(['estado', estado]);
      return !pantalla.otraPantalla;
    },
    aplicarDepto: (depto) => {
      hechos.push(['pieza', depto]);
      if (depto && depto.rota) throw new Error('rota');
    },
  });

  return {
    envios,
    pedir,
    pedidos,
    hechos,
    alEsperar,
    pantalla,
    responde: (ruta, contesta) => { respuestas.set(ruta, contesta); },
    retiene(ruta) {
      let soltar;
      retenidas.set(ruta, new Promise((listo) => { soltar = listo; }));
      return async (contesta) => {
        soltar(contesta);
        await asentar();
      };
    },
  };
}

const rutas = (pedidos) => pedidos.map(([ruta]) => ruta);
const lecturas = (pedidos) => pedidos.filter(([ruta]) => ruta === 'GET departamento').length;
// Lo que pasa en la pantalla al salir una petición: espera, y se calla lo dicho.
const alMandar = (origen) => [['esperar', origen], ['decir', '', false], ['anunciar', '']];
// Lo que pasa al volver a leer: el estado y, si no pide otra pantalla, la pieza.
const alLeer = (depto = PIEZA) => [['pintar'], ['estado', ESTADO], ['pieza', depto]];

// --- mandar ----------------------------------------------------------------------------

test('mientras una petición va, lo que la mandó espera, se calla lo dicho y no sale otra', async () => {
  const {
    envios, pedir, pedidos, hechos, alEsperar, retiene,
  } = montar();
  assert.equal(envios.enCamino, false);
  assert.equal(envios.origen, null);
  const soltar = retiene('POST departamento/guardar');
  const contestadas = [];
  envios.mandar(GUARDAR, () => pedir('POST', 'departamento/guardar', { mueble_id: 23 }), (r) => contestadas.push(r));
  await asentar();
  assert.equal(envios.enCamino, true);
  assert.equal(envios.origen, GUARDAR);
  assert.deepEqual(hechos, alMandar(GUARDAR));
  envios.mandar(BANAR, () => pedir('POST', 'cuidar', {}), (r) => contestadas.push(r));   // no sale
  await asentar();
  assert.deepEqual(rutas(pedidos), ['POST departamento/guardar']);
  assert.deepEqual(hechos, alMandar(GUARDAR));
  const CONTESTA = { ok: true, mensaje: null };
  await soltar(CONTESTA);
  assert.equal(envios.enCamino, false);
  assert.equal(envios.origen, null);
  assert.deepEqual(hechos.slice(3), [['dejarDeEsperar', GUARDAR], ['pintar']]);   // sin estado, no se pone ninguno
  assert.deepEqual(contestadas, [CONTESTA]);
  assert.deepEqual(rutas(pedidos), ['POST departamento/guardar']);                 // y no se relee nada
  // Cuando la pantalla espera y deja de esperar, el transporte ya dice lo nuevo (con eso cierra el menú).
  assert.deepEqual(alEsperar, [[true, GUARDAR], [false, null]]);
  await envios.mandar(BANAR, () => pedir('POST', 'cuidar', {}), (r) => contestadas.push(r));   // ahora sí
  assert.deepEqual(rutas(pedidos), ['POST departamento/guardar', 'POST cuidar']);
});

test('lo que contesta con el estado lo pone antes que lo demás; si el estado pide otra pantalla, no se hace lo demás', async () => {
  const {
    envios, pedir, hechos, responde, pantalla,
  } = montar();
  const CONTESTA = { ok: true, mensaje: 'Pelusa quedó reluciente.', estado: ESTADO };
  responde('POST cuidar', CONTESTA);
  await envios.mandar(BANAR, () => pedir('POST', 'cuidar', {}), (r) => { hechos.push(['contesta', r]); });
  assert.deepEqual(hechos.slice(3), [['dejarDeEsperar', BANAR], ['pintar'], ['estado', ESTADO], ['contesta', CONTESTA]]);
  hechos.length = 0;
  pantalla.otraPantalla = true;
  await envios.mandar(BANAR, () => pedir('POST', 'cuidar', {}), (r) => { hechos.push(['contesta', r]); });
  assert.deepEqual(hechos.slice(3), [['dejarDeEsperar', BANAR], ['pintar'], ['estado', ESTADO]]);
});

test('sin respuesta lo dice y vuelve a leer la pieza, aunque la pestaña no se vea', async () => {
  const {
    envios, pedir, pedidos, hechos, responde,
  } = montar();
  responde('POST cuidar', SIN_RED);
  document.hidden = true;
  try {
    await envios.mandar(BANAR, () => pedir('POST', 'cuidar', {}), () => assert.fail('no contestó'));
    await asentar();
  } finally {
    document.hidden = false;
  }
  assert.deepEqual(rutas(pedidos), ['POST cuidar', 'GET estado', 'GET departamento']);
  assert.deepEqual(hechos, [...alMandar(BANAR), ['dejarDeEsperar', BANAR], ['decir', SIN_RESPUESTA, true], ...alLeer()]);
  assert.equal(envios.enCamino, false);
});

test('un «no» del juego se dice con su frase, y también se vuelve a leer la pieza', async () => {
  const {
    envios, pedir, pedidos, hechos, responde,
  } = montar();
  responde('POST departamento/poner', NO_CABE);
  await envios.mandar(GUARDAR, () => pedir('POST', 'departamento/poner', {}), () => assert.fail('dijo que no'));
  await asentar();
  assert.deepEqual(rutas(pedidos), ['POST departamento/poner', 'GET estado', 'GET departamento']);
  assert.deepEqual(hechos, [...alMandar(GUARDAR), ['dejarDeEsperar', GUARDAR], ['decir', 'Ahí no cabe.', true], ...alLeer()]);
});

test('sin sesión, o con un «no» que cambia la pantalla, se va: sin decir nada más ni volver a leer', async () => {
  for (const error of [SIN_SESION, OTRA_PANTALLA]) {
    const {
      envios, pedir, pedidos, hechos, responde,
    } = montar();
    responde('POST cuidar', error);
    await envios.mandar(BANAR, () => pedir('POST', 'cuidar', {}), () => assert.fail('se fue'));
    await asentar();
    assert.deepEqual(rutas(pedidos), ['POST cuidar'], error.clave);
    assert.deepEqual(hechos, [...alMandar(BANAR), ['dejarDeEsperar', BANAR], ['irse']], error.clave);   // a decidir de nuevo
  }
});

test('si se deja la pantalla mientras la petición va, lo que llega no pinta, no dice nada ni vuelve a leer', async () => {
  for (const llega of [{ ok: true, mensaje: null, estado: ESTADO }, SIN_RED, OTRA_PANTALLA]) {
    const {
      envios, pedir, pedidos, hechos, retiene, pantalla,
    } = montar();
    const soltar = retiene('POST departamento/guardar');
    envios.mandar(GUARDAR, () => pedir('POST', 'departamento/guardar', {}), () => assert.fail('ya no está'));
    await asentar();
    pantalla.sigue = false;                                               // se fue a la mochila
    await soltar(llega);
    assert.deepEqual(hechos, alMandar(GUARDAR));
    assert.deepEqual(rutas(pedidos), ['POST departamento/guardar']);
  }
});

test('mientras se reintenta la petición sigue en camino: no sale otra, y lo que la mandó espera hasta la última vuelta', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const {
    envios, pedir, pedidos, hechos, responde, pantalla,
  } = montar();
  const CONTESTA = { ok: true, mensaje: 'Pelusa quedó reluciente.', estado: ESTADO };
  const vueltas = [SIN_RED, SIN_RED, CONTESTA];
  responde('POST cuidar', () => vueltas.shift());
  const contestadas = [];
  // Como lo manda la pantalla: con su evento, el mismo en cada vuelta, y mientras siga ahí.
  const cuidar = () => conReintentos(() => pedir('POST', 'cuidar', { accion: 'limpiar', evento_id: 'e-12345678' }), () => pantalla.sigue);
  envios.mandar(BANAR, cuidar, (r) => contestadas.push(r));
  await asentar();
  envios.mandar(GUARDAR, () => pedir('POST', 'departamento/guardar', {}), () => assert.fail('no sale'));
  t.mock.timers.tick(800);
  await asentar();
  assert.equal(envios.enCamino, true);
  t.mock.timers.tick(2000);
  await asentar();
  assert.deepEqual(pedidos, Array(3).fill(['POST cuidar', { accion: 'limpiar', evento_id: 'e-12345678' }]));
  assert.deepEqual(contestadas, [CONTESTA]);
  assert.deepEqual(hechos, [...alMandar(BANAR), ['dejarDeEsperar', BANAR], ['pintar'], ['estado', ESTADO]]);
  assert.equal(envios.enCamino, false);
});

test('si se deja la pantalla entre un reintento y otro, no se insiste ni se dice nada', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const {
    envios, pedir, pedidos, hechos, responde, pantalla,
  } = montar();
  responde('POST cuidar', SIN_RED);
  const cuidar = () => conReintentos(() => pedir('POST', 'cuidar', { accion: 'limpiar', evento_id: 'e-12345678' }), () => pantalla.sigue);
  envios.mandar(BANAR, cuidar, () => assert.fail('no llegó'));
  await asentar();
  pantalla.sigue = false;
  t.mock.timers.tick(800);
  await asentar();
  assert.deepEqual(rutas(pedidos), ['POST cuidar']);
  assert.deepEqual(hechos, alMandar(BANAR));
});

// --- enviar: lo que contesta con la pieza --------------------------------------------------

test('enviar: lo que sale bien deja elegido lo que toque, pone la pieza que contesta y dice su frase', async () => {
  const {
    envios, pedir, hechos, responde,
  } = montar();
  const CONTESTA = { ok: true, clave: null, mensaje: 'Ahora sales con Rulo.', departamento: OTRA_PIEZA, estado: ESTADO };
  responde('POST departamento/salir', CONTESTA);
  await envios.enviar(BANAR, () => pedir('POST', 'departamento/salir', { gachamon_id: 8 }), () => { hechos.push(['elegir']); });
  assert.deepEqual(hechos.slice(3), [
    ['dejarDeEsperar', BANAR], ['pintar'], ['estado', ESTADO], ['elegir'], ['pieza', OTRA_PIEZA], ['decir', 'Ahora sales con Rulo.', false],
  ]);
});

test('enviar: lo que sale bien sin frase se le vuelve a decir a quien no ve el dibujo, con cómo quedó la pieza', async () => {
  const {
    envios, pedir, hechos, responde,
  } = montar();
  responde('POST departamento/guardar', { ok: true, clave: null, mensaje: null, departamento: OTRA_PIEZA, estado: ESTADO });
  await envios.enviar(GUARDAR, () => pedir('POST', 'departamento/guardar', { mueble_id: 23 }), null);   // sin nada que elegir
  assert.deepEqual(hechos.slice(3), [
    ['dejarDeEsperar', GUARDAR], ['pintar'], ['estado', ESTADO], ['pieza', OTRA_PIEZA], ['decir', null, false],
    ['anunciar', lineaDeEstado(OTRA_PIEZA)],
  ]);
});

test('enviar: un «no» no elige nada, pone la pieza como dice el servidor y dice su frase como un error', async () => {
  const {
    envios, pedir, hechos, responde,
  } = montar();
  responde('POST departamento/poner', { ok: false, clave: 'no_cabe', mensaje: 'Ahí no cabe.', departamento: PIEZA, estado: ESTADO });
  await envios.enviar(GUARDAR, () => pedir('POST', 'departamento/poner', {}), () => { hechos.push(['elegir']); });
  assert.deepEqual(hechos.slice(3), [
    ['dejarDeEsperar', GUARDAR], ['pintar'], ['estado', ESTADO], ['pieza', PIEZA], ['decir', 'Ahí no cabe.', true],
  ]);
});

// --- releer --------------------------------------------------------------------------------

test('releer trae el estado y la pieza, y pone primero el estado; si pide otra pantalla, la pieza no se pone', async () => {
  const {
    envios, pedidos, hechos, pantalla,
  } = montar();
  await envios.releer();
  assert.deepEqual(rutas(pedidos), ['GET estado', 'GET departamento']);
  assert.deepEqual(hechos, alLeer());
  hechos.length = 0;
  pantalla.otraPantalla = true;
  await envios.releer();
  assert.deepEqual(hechos, [['pintar'], ['estado', ESTADO]]);
});

test('releer no lee sin la pieza, tras dejar la pantalla, con la pestaña escondida ni con una petición en camino', async () => {
  const sinPieza = montar({ conPieza: false });
  await sinPieza.envios.releer();
  await sinPieza.envios.releer({ trasUnaAccion: true });
  assert.deepEqual(sinPieza.pedidos, []);

  const fuera = montar();
  fuera.pantalla.sigue = false;
  await fuera.envios.releer({ trasUnaAccion: true });
  assert.deepEqual(fuera.pedidos, []);

  const escondida = montar();
  document.hidden = true;
  try {
    await escondida.envios.releer();
    assert.deepEqual(escondida.pedidos, []);
    await escondida.envios.releer({ trasUnaAccion: true });               // la de tras una acción sin respuesta, sí
    assert.deepEqual(rutas(escondida.pedidos), ['GET estado', 'GET departamento']);
  } finally {
    document.hidden = false;
  }

  const {
    envios, pedir, pedidos, retiene,
  } = montar();
  const soltar = retiene('POST cuidar');
  envios.mandar(BANAR, () => pedir('POST', 'cuidar', {}), () => {});
  await asentar();
  await envios.releer();
  await envios.releer({ trasUnaAccion: true });
  assert.deepEqual(rutas(pedidos), ['POST cuidar']);                       // lo que traiga la acción es más nuevo
  await soltar({ ok: true, mensaje: null });
});

test('mientras va una lectura no sale otra, salvo la de tras una acción sin respuesta; de las dos se pinta sólo la última', async () => {
  const {
    envios, pedidos, hechos, retiene, responde,
  } = montar();
  const soltar = retiene('GET departamento');
  envios.releer();
  await asentar();
  envios.releer();                                                        // la de cada 30 segundos: va otra
  await asentar();
  assert.equal(lecturas(pedidos), 1);
  responde('GET departamento', OTRA_PIEZA);
  await envios.releer({ trasUnaAccion: true });
  assert.equal(lecturas(pedidos), 2);
  assert.deepEqual(hechos, alLeer(OTRA_PIEZA));
  await soltar(PIEZA);                                                    // la primera llega tarde: no se pinta
  assert.deepEqual(hechos, alLeer(OTRA_PIEZA));
  await envios.releer();                                                  // y ya no queda ninguna en camino
  assert.equal(lecturas(pedidos), 3);
});

test('si se deja la pantalla mientras va una lectura, lo que llega no se pinta', async () => {
  const {
    envios, hechos, retiene, pantalla,
  } = montar();
  const soltar = retiene('GET departamento');
  envios.releer();
  await asentar();
  pantalla.sigue = false;
  await soltar(OTRA_PIEZA);
  assert.deepEqual(hechos, []);
});

test('una relectura que falla no dice ni pinta nada, y la siguiente lee; sin sesión o con un 409 se va, si sigue ahí', async () => {
  const {
    envios, pedidos, hechos, responde, retiene, pantalla,
  } = montar();
  responde('GET departamento', SIN_RED);
  await envios.releer();
  assert.deepEqual(hechos, []);
  responde('GET departamento', PIEZA);
  await envios.releer();
  assert.equal(lecturas(pedidos), 2);
  assert.deepEqual(hechos, alLeer());
  hechos.length = 0;
  responde('GET estado', SIN_SESION);
  await envios.releer();
  assert.deepEqual(hechos, [['irse']]);
  hechos.length = 0;
  const soltar = retiene('GET estado');
  envios.releer();
  await asentar();
  pantalla.sigue = false;
  await soltar(OTRA_PANTALLA);
  assert.deepEqual(hechos, []);
});

test('una lectura que salió antes que una acción no se pinta: se vuelve a pedir al acabar la acción', async () => {
  const {
    envios, pedir, pedidos, hechos, retiene, responde,
  } = montar();
  const soltarLaLectura = retiene('GET departamento');
  envios.releer();
  await asentar();
  const soltarLaAccion = retiene('POST departamento/guardar');
  envios.mandar(GUARDAR, () => pedir('POST', 'departamento/guardar', {}), () => { hechos.push(['contesta']); });
  await asentar();
  await soltarLaLectura(PIEZA);                                           // trae lo de antes de la acción: se tira
  assert.equal(lecturas(pedidos), 1);                                     // y con la acción en camino no se relee
  assert.deepEqual(hechos, alMandar(GUARDAR));
  responde('GET departamento', OTRA_PIEZA);
  await soltarLaAccion({ ok: true, mensaje: null });
  assert.equal(lecturas(pedidos), 2);
  assert.deepEqual(hechos.slice(3), [['dejarDeEsperar', GUARDAR], ['pintar'], ['contesta'], ...alLeer(OTRA_PIEZA)]);
});

test('si la acción ya acabó cuando llega la lectura que se tira, se vuelve a pedir enseguida', async () => {
  const {
    envios, pedir, pedidos, hechos, retiene, responde,
  } = montar();
  const soltar = retiene('GET departamento');
  envios.releer();
  await asentar();
  responde('POST departamento/guardar', { ok: true, mensaje: null });
  await envios.mandar(GUARDAR, () => pedir('POST', 'departamento/guardar', {}), () => {});
  await asentar();
  assert.equal(lecturas(pedidos), 1);
  responde('GET departamento', OTRA_PIEZA);
  await soltar(PIEZA);
  assert.equal(lecturas(pedidos), 2);
  assert.deepEqual(hechos.slice(-3), alLeer(OTRA_PIEZA));
  assert.equal(hechos.filter(([que]) => que === 'pieza').length, 1);
});

test('si la acción se queda sin respuesta, la lectura que se tiró no se pide dos veces', async () => {
  const {
    envios, pedir, pedidos, retiene, responde,
  } = montar();
  const soltarLaLectura = retiene('GET departamento');
  envios.releer();
  await asentar();
  const soltarLaAccion = retiene('POST cuidar');
  envios.mandar(BANAR, () => pedir('POST', 'cuidar', {}), () => {});
  await asentar();
  await soltarLaLectura(PIEZA);                                           // se tira: queda por leer
  await soltarLaAccion(SIN_RED);                                          // se relee por no haber respuesta
  assert.equal(lecturas(pedidos), 2);
  responde('POST cuidar', { ok: true, mensaje: null });
  await envios.mandar(BANAR, () => pedir('POST', 'cuidar', {}), () => {});
  await asentar();
  assert.equal(lecturas(pedidos), 2);                                     // la que quedaba ya se leyó
});

test('lo que revienta al pintar va por `pintar`, no se toma por un fallo de la red', async () => {
  const {
    envios, pedir, pedidos, hechos, responde,
  } = montar();
  responde('GET departamento', ROTA);
  await envios.releer();
  assert.deepEqual(hechos, [...alLeer(ROTA), ['reventó', 'rota']]);
  hechos.length = 0;
  responde('POST cuidar', { ok: true, mensaje: null });
  await envios.mandar(BANAR, () => pedir('POST', 'cuidar', {}), () => { throw new Error('al contestar'); });
  await asentar();
  assert.deepEqual(hechos, [...alMandar(BANAR), ['dejarDeEsperar', BANAR], ['pintar'], ['reventó', 'al contestar']]);
  assert.equal(envios.enCamino, false);
  assert.equal(lecturas(pedidos), 1);
});
