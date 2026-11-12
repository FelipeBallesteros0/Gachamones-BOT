/* Boceto desechable de la pantalla principal de Gachamon:
   estás siempre "en un lugar", con tu gachamon en grande, y el pueblo sirve para moverte.
   No es código del juego. */
(function () {
  'use strict';

  var raiz = document.querySelector('[data-juego]');
  if (!raiz || !window.GM) return;

  var $ = function (s) { return raiz.querySelector(s); };
  var vistaLugar = $('.gj-lugar'), vistaMapa = $('.gj-mapa');
  var escena = $('.gj-escena'), bicho = $('.gj-bicho'), globo = $('.gj-globo');
  var titulo = $('.gj-donde'), acciones = $('.gj-acciones'), aviso = $('.gj-aviso');
  var sombra = $('.gj-visita');

  /* ---------- los lugares por dentro ---------- */
  var ESCENAS = {
    casa: {
      clase: 'interior', pared: '#f3e2c0', piso: '#b98a5a', ventana: true,
      cosas: [['🌱', 12, 28, 20], ['🌱', 23, 28, 20], ['🛋️', 80, 47, 44], ['🖼️', 62, 15, 26]],
      acciones: ['🌱 Huerto', '🛋️ Muebles', '📬 Buzón'],
      llegada: 'Hogar, dulce hogar. Pío.'
    },
    refugio: {
      clase: 'interior', pared: '#d8d2c6', piso: '#8d8478',
      cosas: [['🛏️', 66, 62, 46], ['🕯️', 16, 50, 24]],
      acciones: ['🛏️ Descansar'],
      llegada: 'Aquí huele a sopa, pío.'
    },
    incubadora: {
      clase: 'interior', pared: '#fdf0cf', piso: '#d9b36a',
      cosas: [['🥚', 12, 60, 34], ['🥚', 72, 58, 30], ['🥚', 84, 64, 26]],
      acciones: ['🔄 Cambiar de activo', '🥚 Pedir huevo'],
      llegada: 'Shhh… están durmiendo.'
    },
    tienda: {
      clase: 'interior', pared: '#dfeaf7', piso: '#8fa3b8',
      cosas: [['🧪', 10, 24, 26], ['🎩', 24, 24, 26], ['🧴', 38, 24, 26], ['🏷️', 74, 26, 26], ['🧺', 78, 64, 40]],
      acciones: ['🧪 Objetos', '🎩 Cosméticos', '🏠 Casas'],
      llegada: '¡Pío! ¿Hay porotos verdes?'
    },
    plaza: {
      clase: 'exterior', pared: '#bfe3f2', piso: '#86c46f',
      cosas: [['⛲', 68, 56, 54], ['🌳', 8, 44, 50]],
      acciones: ['👀 Mirar a los demás'], parteB: true,
      llegada: '¡Mira cuántos amigos, pío!'
    },
    barrio: {
      clase: 'exterior', pared: '#bfe3f2', piso: '#86c46f',
      cosas: [['🏡', 6, 40, 56], ['🏠', 68, 42, 54]],
      acciones: ['🚪 Visitar', '🎁 Regalar'], parteB: true,
      llegada: '¿A quién visitamos?'
    },
    estadio: {
      clase: 'exterior', pared: '#bfe3f2', piso: '#c9b48a',
      cosas: [['🏟️', 58, 34, 70], ['🏁', 10, 58, 34]],
      acciones: ['🏁 Carrera', '🤼 Sumo', '🗿 Tótem', '🌀 Laberinto'], parteB: true,
      llegada: '¡Hoy gano yo, pío!'
    },
    cementerio: {
      clase: 'exterior', pared: '#c9c4dc', piso: '#93ac86',
      cosas: [['🕯️', 14, 60, 28], ['🌫️', 66, 30, 50]],
      acciones: ['🕯️ Recordar'], parteB: true,
      llegada: 'Pío… aquí hace frío.'
    },
    portal: {
      clase: 'exterior', pared: '#bfe3f2', piso: '#86c46f',
      cosas: [['⛰️', 60, 30, 70], ['🧭', 12, 58, 34]],
      acciones: ['🧭 Salir de aventura'], parteB: true,
      llegada: '¿Vamos al bosque? ¡Pío!'
    }
  };

  var E = { lugar: 'casa', comida: 62, animo: 70, aseo: 34, caricia: 0, globoHasta: 0, visita: 0 };
  var ENFRIAMIENTO = 12000; /* en el boceto, 12 s; en el juego sería más largo */

  function ahora() { return Date.now(); }
  function tope(v) { return Math.max(0, Math.min(100, v)); }

  function pintarBarras() {
    ['comida', 'animo', 'aseo'].forEach(function (k) {
      var b = $('.gj-b-' + k), n = $('.gj-n-' + k), v = Math.round(E[k]);
      b.style.width = v + '%';
      b.className = 'gj-b-' + k + (v < 40 ? ' baja' : v < 65 ? ' media' : '');
      n.textContent = v;
    });
  }

  function decir(texto, ms) {
    globo.textContent = texto;
    globo.classList.add('visible');
    E.globoHasta = ahora() + (ms || 3600);
  }

  function saltar() {
    bicho.classList.remove('salta');
    void bicho.offsetWidth;
    bicho.classList.add('salta');
  }

  function fraseSuelta() {
    var bajas = [];
    if (E.comida < 40) bajas.push('Tengo hambre… ¿hay porotos verdes?');
    if (E.aseo < 40) bajas.push('Estoy sucia. Pío.');
    if (E.animo < 40) bajas.push('Quiero jugar…');
    if (bajas.length) return bajas[Math.floor(Math.random() * bajas.length)];
    var sueltas = ['¿Cómo estás?', 'Vi un ovni anoche. Pío.', '¿Jugamos?', 'Qué lindo día, pío.'];
    if (E.lugar === 'casa') sueltas.push('VENTANA');
    return sueltas[Math.floor(Math.random() * sueltas.length)];
  }

  function hablarSola() {
    if (vistaLugar.classList.contains('oculta')) return;
    var f = fraseSuelta();
    if (f === 'VENTANA') {
      decir('Creo que hay alguien en la ventana…', 4200);
      E.visita = ahora() + 4200;
      sombra.classList.add('visible');
    } else {
      decir(f);
    }
  }

  /* ---------- cuidados ---------- */
  var CUIDADOS = {
    alimentar: function () { E.comida = tope(E.comida + 25); decir('¡Ñam! Pío.'); },
    jugar: function () { E.animo = tope(E.animo + 15); E.comida = tope(E.comida - 5); decir('¡Otra vez, otra vez!'); },
    entrenar: function () { E.animo = tope(E.animo - 5); E.comida = tope(E.comida - 8); decir('Uf… ¡más fuerte, pío!'); },
    limpiar: function () { E.aseo = 100; decir('¡Reluciente! Pío.'); }
  };
  raiz.querySelectorAll('[data-cuidado]').forEach(function (b) {
    b.addEventListener('click', function () {
      CUIDADOS[b.getAttribute('data-cuidado')]();
      saltar();
      pintarBarras();
    });
  });

  /* ---------- la caricia ---------- */
  function corazones() {
    for (var i = 0; i < 6; i++) {
      (function (i) {
        var c = document.createElement('span');
        c.className = 'gj-corazon';
        c.textContent = '❤';
        c.style.left = (38 + Math.random() * 30) + '%';
        c.style.animationDelay = (i * 90) + 'ms';
        c.style.fontSize = (14 + Math.random() * 10) + 'px';
        escena.appendChild(c);
        setTimeout(function () { c.remove(); }, 1600 + i * 90);
      })(i);
    }
  }
  bicho.addEventListener('click', function () {
    var t = ahora();
    if (t < E.caricia) {
      /* antes de tiempo: no pasa nada, apenas se mueve */
      bicho.classList.remove('nada');
      void bicho.offsetWidth;
      bicho.classList.add('nada');
      return;
    }
    E.caricia = t + ENFRIAMIENTO;
    E.animo = tope(E.animo + 8);
    corazones();
    saltar();
    decir('Pío pío… ♥');
    pintarBarras();
  });

  /* ---------- entrar a un lugar ---------- */
  function entrar(id, conFrase) {
    var s = ESCENAS[id];
    E.lugar = id;
    titulo.textContent = '📍 ' + window.GM.LUGARES[id].nombre;
    escena.className = 'gj-escena ' + s.clase;
    escena.style.setProperty('--pared', s.pared);
    escena.style.setProperty('--piso', s.piso);
    $('.gj-ventana').style.display = s.ventana ? '' : 'none';
    var viejas = escena.querySelectorAll('.gj-cosa');
    for (var v = 0; v < viejas.length; v++) viejas[v].remove();
    s.cosas.forEach(function (c) {
      var e = document.createElement('span');
      e.className = 'gj-cosa';
      e.textContent = c[0];
      e.style.left = c[1] + '%'; e.style.top = c[2] + '%'; e.style.fontSize = c[3] + 'px';
      escena.insertBefore(e, escena.firstChild);
    });
    acciones.innerHTML = s.acciones.map(function (a) { return '<button type="button" class="gj-chip">' + a + '</button>'; }).join('');
    aviso.textContent = s.parteB ? 'Este lugar se abre en la parte B.' : '';
    vistaMapa.classList.add('oculta');
    vistaLugar.classList.remove('oculta');
    if (conFrase) decir(s.llegada, 3600);
  }

  acciones.addEventListener('click', function (e) {
    if (e.target.classList.contains('gj-chip')) decir('(Eso todavía no está en el boceto.)', 2200);
  });
  raiz.querySelectorAll('[data-nav]').forEach(function (b) {
    b.addEventListener('click', function () {
      var a = b.getAttribute('data-nav');
      if (a === 'pueblo') {
        globo.classList.remove('visible');
        vistaLugar.classList.add('oculta');
        vistaMapa.classList.remove('oculta');
      } else {
        decir('(Eso todavía no está en el boceto.)', 2200);
      }
    });
  });

  /* ---------- el pueblo ---------- */
  var cfg = {};
  for (var k in window.GM.MAPAS.b) cfg[k] = window.GM.MAPAS.b[k];
  cfg.alLlegar = function (id) { setTimeout(function () { entrar(id, true); }, 350); };
  window.GM.instancias.juego = window.GM.crearMapa(vistaMapa, cfg);

  /* ---------- el avatar de relleno, en grande ---------- */
  (function () {
    var c = $('.gj-avatar'), x = c.getContext('2d'), s = 4;
    x.setTransform(s, 0, 0, s, c.width / 2, c.height - 4);
    x.fillStyle = 'rgba(0,0,0,.2)'; x.beginPath(); x.ellipse(0, 0, 8, 2.5, 0, 0, 7); x.fill();
    x.fillStyle = '#2f3e63'; x.fillRect(-5, -9, 4, 9); x.fillRect(1, -9, 4, 9);
    x.fillStyle = '#d9534f'; x.fillRect(-6, -20, 12, 12);
    x.fillStyle = '#b9403c'; x.fillRect(-8, -19, 3, 9); x.fillRect(5, -19, 3, 9);
    x.fillStyle = '#f2c79b'; x.fillRect(-6, -31, 12, 11);
    x.fillStyle = '#4a2f1b'; x.fillRect(-7, -33, 14, 5); x.fillRect(-7, -31, 3, 6);
    x.fillStyle = '#1d1d1f'; x.fillRect(0, -26, 2, 2); x.fillRect(4, -26, 1.5, 2);
  })();

  /* ---------- reloj ---------- */
  setInterval(function () {
    var t = ahora();
    if (t > E.globoHasta) globo.classList.remove('visible');
    if (E.visita && t > E.visita) { E.visita = 0; sombra.classList.remove('visible'); }
    var falta = Math.max(0, E.caricia - t);
    $('.gj-espera').textContent = falta ? 'Otra caricia en ' + Math.ceil(falta / 1000) + ' s' : 'Tócala para acariciarla';
  }, 250);
  setInterval(function () { if (ahora() > E.globoHasta + 2500) hablarSola(); }, 1000);

  pintarBarras();
  entrar('casa', false);
  setTimeout(function () { decir('Estoy sucia. Pío.', 4000); }, 900);
})();
