/* Boceto desechable del mapa de Gachamon: dos formas de llevarlo al celular.
   No es código del juego. */
(function () {
  'use strict';

  var EMOJI = '"Segoe UI Emoji","Apple Color Emoji","Noto Color Emoji",sans-serif';
  var TEXTO = 'system-ui,-apple-system,"Segoe UI",sans-serif';

  var IMG = {};
  ['pollito', 'chispa', 'slime', 'michi', 'pedrusco'].forEach(function (n) {
    var i = new Image();
    i.src = '/files/' + n + '.png';
    IMG[n] = i;
  });

  var LUGARES = {
    casa: {
      nombre: 'Tu casa', emoji: '🏠', tipo: 'casa', pared: '#f6e7c8', techo: '#c8553d',
      desc: 'Tus muebles, tu huerto y los gachamones que viven contigo.',
      chips: ['🌱 Huerto', '🛋️ Muebles', '📬 Buzón'],
      frase: 'Hogar, dulce hogar. Pío.'
    },
    refugio: {
      nombre: 'Refugio', emoji: '🏚️', tipo: 'casa', pared: '#d9d2c4', techo: '#6f7f8f',
      desc: 'Donde vive quien todavía no tiene casa propia.',
      chips: ['🛏️ Descansar'],
      frase: 'Aquí huele a sopa, pío.'
    },
    incubadora: {
      nombre: 'Incubadora', emoji: '🥚', tipo: 'casa', pared: '#fdf3d7', techo: '#e6a93a',
      desc: 'Tu plantel: los gachamones que esperan su turno.',
      chips: ['🔄 Cambiar de activo', '🥚 Huevo'],
      frase: 'Shhh… están durmiendo.'
    },
    tienda: {
      nombre: 'Tienda', emoji: '🛒', tipo: 'casa', pared: '#e8f1fb', techo: '#3f7fd0',
      desc: 'Objetos, cosméticos y casas.',
      chips: ['🧪 Objetos', '🎩 Cosméticos', '🏠 Casas'],
      frase: '¡Pío! ¿Hay porotos verdes?'
    },
    plaza: {
      nombre: 'Plaza', emoji: '⛲', tipo: 'plaza',
      desc: 'Los gachamones de todos, juntos.',
      chips: ['👀 Mirar', '💬 Conversar'],
      frase: '¡Mira cuántos amigos, pío!'
    },
    barrio: {
      nombre: 'Barrio', emoji: '🏘️', tipo: 'casa', pared: '#f3dfe6', techo: '#9a5fb0',
      desc: 'Las casas de los demás.',
      chips: ['🚪 Visitar', '🎁 Regalar'],
      frase: '¿A quién visitamos?'
    },
    estadio: {
      nombre: 'Estadio', emoji: '🏟️', tipo: 'estadio',
      desc: 'Carrera, sumo, asalto al tótem y laberinto de ecos.',
      chips: ['🏁 Carrera', '🤼 Sumo', '🗿 Tótem', '🌀 Laberinto', '🏆 Ranking'],
      frase: '¡Hoy gano yo, pío!'
    },
    cementerio: {
      nombre: 'Cementerio', emoji: '🕯️', tipo: 'cementerio',
      desc: 'Los que ya no están.',
      chips: ['🕯️ Recordar'],
      frase: 'Pío… aquí hace frío.'
    },
    portal: {
      nombre: 'Aventura', emoji: '🧭', tipo: 'portal',
      desc: 'La salida del pueblo: de aquí se parte a los diez biomas.',
      chips: ['🧭 Salir de aventura'],
      frase: '¿Vamos al bosque? ¡Pío!'
    }
  };

  var MAPAS = {
    /* A — todo el pueblo cabe en la pantalla */
    a: {
      zoom: 1, ancho: 300, vel: 110, hueco: 22, escala: 0.85, altoG: 26,
      desliza: false, hojaDinamica: true, inicio: 'casa', semilla: 11,
      nodos: {
        borde: [40, 520], casa: [92, 520], k0: [157, 520], refugio: [222, 520],
        k1: [157, 425], incubadora: [56, 425], tienda: [246, 425],
        plaza: [157, 322], barrio: [250, 322],
        k2: [157, 225], estadio: [60, 225], cementerio: [250, 225],
        portal: [157, 135], afuera: [157, 52]
      },
      aristas: [
        ['borde', 'casa'], ['casa', 'k0'], ['k0', 'refugio'], ['k0', 'k1'],
        ['k1', 'incubadora'], ['k1', 'tienda'], ['k1', 'plaza'],
        ['plaza', 'barrio'], ['plaza', 'k2'],
        ['k2', 'estadio'], ['k2', 'cementerio'], ['k2', 'portal'], ['portal', 'afuera']
      ],
      estanques: [[62, 320, 34, 19]],
      arboles: [
        [22, 560], [280, 562], [124, 468], [196, 470], [22, 470], [284, 470],
        [104, 372], [196, 372], [22, 270], [108, 268], [205, 268], [286, 268],
        [22, 168], [110, 170], [204, 170], [288, 165], [40, 90], [88, 74], [226, 74], [270, 92]
      ],
      ociosos: [
        { img: 'chispa', nodo: 'plaza', dx: -15, dy: 10, alto: 22, dir: 1 },
        { img: 'slime', nodo: 'plaza', dx: 17, dy: -4, alto: 20, dir: -1 },
        { img: 'pedrusco', nodo: 'refugio', dx: 26, dy: -1, alto: 20, dir: -1 },
        { img: 'michi', nodo: 'barrio', dx: -24, dy: 13, alto: 22, dir: 1 }
      ],
      lejos: null
    },
    /* B — el pueblo es más ancho que la pantalla y la cámara sigue al avatar */
    b: {
      zoom: 580 / 430, ancho: 690, vel: 115, hueco: 26, escala: 1, altoG: 30,
      desliza: true, hojaDinamica: false, inicio: 'casa', semilla: 5,
      nodos: {
        incubadora: [75, 170], u1: [165, 170], tienda: [220, 170], ptop: [300, 170],
        estadio: [390, 170], u3: [485, 170], cementerio: [545, 170], portal: [640, 170],
        afuera: [640, 62],
        borde: [30, 330], casa: [75, 330], l1: [165, 330], l2: [300, 330],
        barrio: [395, 330], l3: [485, 330], refugio: [575, 330],
        plaza: [300, 250]
      },
      aristas: [
        ['incubadora', 'u1'], ['u1', 'tienda'], ['tienda', 'ptop'], ['ptop', 'estadio'],
        ['estadio', 'u3'], ['u3', 'cementerio'], ['cementerio', 'portal'], ['portal', 'afuera'],
        ['borde', 'casa'], ['casa', 'l1'], ['l1', 'l2'], ['l2', 'barrio'], ['barrio', 'l3'], ['l3', 'refugio'],
        ['u1', 'l1'], ['ptop', 'plaza'], ['plaza', 'l2'], ['u3', 'l3']
      ],
      estanques: [[235, 392, 40, 16]],
      arboles: [
        [30, 395], [120, 400], [160, 385], [340, 392], [420, 400], [520, 390], [610, 398], [665, 385],
        [118, 250], [210, 255], [360, 248], [440, 252], [530, 250], [620, 255], [30, 250],
        [30, 108], [120, 104], [165, 110], [262, 106], [330, 104], [440, 106], [600, 108]
      ],
      ociosos: [
        { img: 'chispa', nodo: 'plaza', dx: -16, dy: 10, alto: 26, dir: 1 },
        { img: 'slime', nodo: 'plaza', dx: 17, dy: -3, alto: 24, dir: -1 },
        { img: 'pedrusco', nodo: 'refugio', dx: 30, dy: -1, alto: 24, dir: -1 },
        { img: 'michi', nodo: 'barrio', dx: 30, dy: 16, alto: 26, dir: -1 }
      ],
      lejos: true
    }
  };

  function limitar(v, a, b) { return Math.max(a, Math.min(b, v)); }

  function crearMapa(raiz, cfg) {
    var canvas = raiz.querySelector('canvas');
    var hoja = raiz.querySelector('.gm-hoja');
    var ctx = canvas.getContext('2d');
    var VW = 300, VH = 580;
    var dpr = Math.max(1, window.devicePixelRatio || 1);
    canvas.width = Math.round(VW * dpr);
    canvas.height = Math.round(VH * dpr);

    var z = cfg.zoom, W = cfg.ancho, H = VH / z, VWU = VW / z;
    var maxCam = Math.max(0, W - VWU);
    var N = cfg.nodos, ady = {};
    Object.keys(N).forEach(function (k) { ady[k] = []; });
    cfg.aristas.forEach(function (par) {
      var a = par[0], b = par[1];
      var d = Math.hypot(N[a][0] - N[b][0], N[a][1] - N[b][1]);
      ady[a].push([b, d]);
      ady[b].push([a, d]);
    });

    var semilla = cfg.semilla || 7;
    function azar() { semilla = (semilla * 1664525 + 1013904223) % 4294967296; return semilla / 4294967296; }
    var matas = [];
    for (var m = 0; m < Math.round(W * H / 800); m++) matas.push([azar() * W, 44 / z + azar() * (H - 44 / z)]);

    function ruta(desde, hasta) {
      var dist = {}, previo = {}, visto = {};
      Object.keys(N).forEach(function (k) { dist[k] = Infinity; });
      dist[desde] = 0;
      for (;;) {
        var u = null;
        for (var k in dist) if (!visto[k] && (u === null || dist[k] < dist[u])) u = k;
        if (u === null || dist[u] === Infinity || u === hasta) break;
        visto[u] = true;
        for (var i = 0; i < ady[u].length; i++) {
          var v = ady[u][i][0], d = ady[u][i][1];
          if (dist[u] + d < dist[v]) { dist[v] = dist[u] + d; previo[v] = u; }
        }
      }
      var camino = [], c = hasta;
      while (c !== undefined) { camino.unshift(c); c = previo[c]; }
      return { camino: camino, largo: dist[hasta] };
    }

    var ini = N[cfg.inicio];
    var S = {
      x: ini[0], y: ini[1], en: cfg.inicio, desde: cfg.inicio, cola: [], destino: null,
      mov: false, dir: 1, t: 0, rastro: [],
      gx: ini[0] - cfg.hueco, gy: ini[1], gdir: 1, gmov: false,
      globo: null, cam: 0, sigue: true, llegadas: 0
    };
    for (var r = cfg.hueco + 2; r >= 0; r -= 2) S.rastro.push({ x: ini[0] - r, y: ini[1] });
    S.globo = { texto: '¿A dónde vamos? Pío.', hasta: 4 };

    /* ---------- hoja de llegada ---------- */
    function cerrarHoja() { hoja.classList.remove('abierta'); }
    function abrirHoja(id) {
      var L = LUGARES[id];
      hoja.innerHTML =
        '<button class="gm-x" type="button" aria-label="Cerrar">×</button>' +
        '<div class="gm-ht">' + L.emoji + ' ' + L.nombre + '</div>' +
        '<div class="gm-hd">' + L.desc + '</div>' +
        '<div class="gm-chips">' + L.chips.map(function (c) { return '<span>' + c + '</span>'; }).join('') + '</div>';
      var arriba = !!cfg.hojaDinamica && S.y * z > 330;
      hoja.style.transition = 'none';
      hoja.classList.remove('abierta');
      hoja.classList.toggle('arriba', arriba);
      void hoja.offsetHeight;
      hoja.style.transition = '';
      window.requestAnimationFrame(function () { hoja.classList.add('abierta'); });
      var x = hoja.querySelector('.gm-x');
      if (x) x.onclick = function (e) { e.stopPropagation(); cerrarHoja(); };
    }

    function llegar() {
      var L = LUGARES[S.destino];
      if (!L) return;
      S.llegadas++;
      if (cfg.alLlegar) { S.globo = null; cfg.alLlegar(S.destino); return; }
      S.globo = { texto: L.frase, hasta: S.t + 3.4 };
      abrirHoja(S.destino);
    }

    function ir(id) {
      if (!LUGARES[id] || !N[id]) return;
      cerrarHoja();
      if (!S.mov) {
        S.cola = ruta(S.en, id).camino.slice(1);
      } else {
        var hacia = S.cola[0];
        var a = ruta(hacia, id), b = ruta(S.desde, id);
        var da = Math.hypot(N[hacia][0] - S.x, N[hacia][1] - S.y) + a.largo;
        var db = Math.hypot(N[S.desde][0] - S.x, N[S.desde][1] - S.y) + b.largo;
        if (da <= db) { S.cola = a.camino; }
        else { S.cola = b.camino; S.desde = hacia; }
      }
      S.destino = id;
      S.sigue = true;
      S.globo = null;
      S.mov = S.cola.length > 0;
      if (!S.mov) llegar();
    }

    function paso(dt) {
      S.t += dt;
      if (S.mov) {
        var queda = cfg.vel * dt;
        while (queda > 0 && S.cola.length) {
          var obj = N[S.cola[0]], dx = obj[0] - S.x, dy = obj[1] - S.y, d = Math.hypot(dx, dy);
          if (Math.abs(dx) > 0.01) S.dir = dx > 0 ? 1 : -1;
          if (d <= queda) {
            S.x = obj[0]; S.y = obj[1]; queda -= d;
            S.desde = S.cola.shift(); S.en = S.desde;
          } else {
            S.x += dx / d * queda; S.y += dy / d * queda; queda = 0;
          }
          S.rastro.push({ x: S.x, y: S.y });
        }
        if (S.rastro.length > 400) S.rastro.splice(0, S.rastro.length - 400);
        if (!S.cola.length) { S.mov = false; llegar(); }
      }
      /* el gachamon va por el mismo rastro, un trecho más atrás */
      var acc = 0, px = S.x, py = S.y, gx = S.rastro[0].x, gy = S.rastro[0].y;
      for (var i = S.rastro.length - 1; i >= 0; i--) {
        var p = S.rastro[i], dd = Math.hypot(p.x - px, p.y - py);
        if (acc + dd >= cfg.hueco) {
          var f = dd > 0 ? (cfg.hueco - acc) / dd : 0;
          gx = px + (p.x - px) * f; gy = py + (p.y - py) * f;
          break;
        }
        acc += dd; px = p.x; py = p.y;
      }
      var mdx = gx - S.gx;
      S.gmov = Math.hypot(gx - S.gx, gy - S.gy) > 0.02;
      if (Math.abs(mdx) > 0.02) S.gdir = mdx > 0 ? 1 : -1;
      S.gx = gx; S.gy = gy;

      if (cfg.desliza && S.sigue) {
        var objetivo = limitar(S.x - VWU / 2, 0, maxCam);
        S.cam += (objetivo - S.cam) * Math.min(1, dt * 5);
      }
    }

    /* ---------- dibujo ---------- */
    function rr(x, y, w, h, radio) {
      ctx.beginPath();
      ctx.moveTo(x + radio, y);
      ctx.arcTo(x + w, y, x + w, y + h, radio);
      ctx.arcTo(x + w, y + h, x, y + h, radio);
      ctx.arcTo(x, y + h, x, y, radio);
      ctx.arcTo(x, y, x + w, y, radio);
      ctx.closePath();
    }
    function elipse(x, y, rx, ry) { ctx.beginPath(); ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2); }
    function pastilla(x, y, txt) {
      ctx.font = '700 9px ' + TEXTO;
      var w = ctx.measureText(txt).width + 12;
      ctx.fillStyle = 'rgba(20,24,28,.84)';
      rr(x - w / 2, y - 7, w, 14, 7); ctx.fill();
      ctx.fillStyle = '#fff'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(txt, x, y + 0.5);
    }
    function emoji(x, y, e, t) {
      ctx.font = t + 'px ' + EMOJI;
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = '#000';
      ctx.fillText(e, x, y);
    }
    function arbol(x, y) {
      ctx.fillStyle = 'rgba(0,0,0,.18)'; elipse(x, y, 7, 2.5); ctx.fill();
      ctx.fillStyle = '#6b4a2b'; ctx.fillRect(x - 1.5, y - 8, 3, 8);
      ctx.fillStyle = '#3f8f4f'; elipse(x, y - 13, 8, 8); ctx.fill();
      ctx.fillStyle = '#57a862'; elipse(x - 2, y - 15, 5, 5); ctx.fill();
    }

    function topeDe(id) {
      var t = LUGARES[id].tipo;
      return t === 'plaza' ? 39 : t === 'estadio' ? 61 : t === 'cementerio' ? 56 : t === 'portal' ? 52 : 68;
    }

    function dibujarLugar(id) {
      var L = LUGARES[id], x = N[id][0], y = N[id][1];
      if (L.tipo === 'plaza') {
        ctx.fillStyle = '#eadfc4'; elipse(x, y, 30, 30); ctx.fill();
        ctx.strokeStyle = '#cdb98f'; ctx.lineWidth = 2; ctx.stroke();
        ctx.fillStyle = '#fff'; elipse(x, y - 1, 11, 11); ctx.fill();
        ctx.fillStyle = '#7cc4ea'; elipse(x, y - 1, 8.5, 8.5); ctx.fill();
        ctx.fillStyle = '#d7eefb'; elipse(x, y - 2, 3, 3); ctx.fill();
      } else if (L.tipo === 'estadio') {
        ctx.fillStyle = 'rgba(0,0,0,.18)'; elipse(x, y - 9, 38, 7); ctx.fill();
        ctx.fillStyle = '#c9cbd6'; elipse(x, y - 30, 36, 22); ctx.fill();
        ctx.fillStyle = '#e9eaf1'; elipse(x, y - 32, 36, 20); ctx.fill();
        ctx.fillStyle = '#6fbf73'; elipse(x, y - 32, 23, 11); ctx.fill();
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 1; elipse(x, y - 32, 15, 6); ctx.stroke();
        ctx.fillStyle = '#d9534f'; ctx.fillRect(x - 30, y - 60, 1.5, 12); ctx.fillRect(x - 28.5, y - 60, 7, 4);
        ctx.fillStyle = '#3f7fd0'; ctx.fillRect(x + 28.5, y - 60, 1.5, 12); ctx.fillRect(x + 30, y - 60, 7, 4);
      } else if (L.tipo === 'cementerio') {
        ctx.fillStyle = '#93ac86'; rr(x - 31, y - 46, 62, 38, 5); ctx.fill();
        ctx.strokeStyle = '#5d6b57'; ctx.lineWidth = 1.5; ctx.stroke();
        var tumbas = [[-18, -30], [0, -34], [18, -30], [-9, -16], [10, -16]];
        for (var i = 0; i < tumbas.length; i++) {
          var tx = x + tumbas[i][0], ty = y + tumbas[i][1];
          ctx.fillStyle = 'rgba(0,0,0,.18)'; elipse(tx, ty + 6, 5, 1.6); ctx.fill();
          ctx.fillStyle = '#c9ccd1'; rr(tx - 4, ty - 5, 8, 11, 3.5); ctx.fill();
          ctx.fillStyle = '#9aa0a8'; ctx.fillRect(tx - 2, ty - 1, 4, 1.2);
        }
      } else if (L.tipo === 'portal') {
        ctx.fillStyle = '#8f857c'; ctx.fillRect(x - 21, y - 34, 8, 36); ctx.fillRect(x + 13, y - 34, 8, 36);
        ctx.fillStyle = '#a79c92'; ctx.fillRect(x - 21, y - 34, 3, 36); ctx.fillRect(x + 13, y - 34, 3, 36);
        ctx.fillStyle = '#75695f'; rr(x - 25, y - 44, 50, 11, 3); ctx.fill();
        emoji(x, y - 38, L.emoji, 11);
      } else {
        var w = 60, h = 34, bx = x - w / 2, by = y - 8 - h;
        ctx.fillStyle = 'rgba(0,0,0,.18)'; elipse(x, y - 7, w / 2 + 4, 5); ctx.fill();
        ctx.fillStyle = L.pared; ctx.fillRect(bx, by, w, h);
        ctx.fillStyle = 'rgba(0,0,0,.08)'; ctx.fillRect(bx, by, w, 4);
        ctx.fillStyle = L.techo;
        ctx.beginPath(); ctx.moveTo(bx - 5, by + 2); ctx.lineTo(x, by - 18); ctx.lineTo(bx + w + 5, by + 2); ctx.closePath(); ctx.fill();
        ctx.fillStyle = '#5b3a24'; rr(x - 6, y - 8 - 17, 12, 17, 2); ctx.fill();
        ctx.fillStyle = '#e9c46a'; ctx.fillRect(x + 2.5, y - 8 - 8, 1.6, 1.6);
        ctx.fillStyle = '#9fd3f0'; ctx.fillRect(bx + 7, by + 10, 10, 9);
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 1; ctx.strokeRect(bx + 7, by + 10, 10, 9);
        emoji(bx + w - 13, by + 17, L.emoji, 13);
      }
      pastilla(x, y - topeDe(id), L.nombre);
    }

    function avatar(x, y, dir, mov, t) {
      var s = cfg.escala;
      ctx.save();
      ctx.translate(x, y);
      ctx.scale(s * dir, s);
      ctx.fillStyle = 'rgba(0,0,0,.22)'; elipse(0, 0, 8, 3); ctx.fill();
      var k = mov ? Math.sin(t * 14) : 0;
      var bote = mov ? -Math.abs(Math.sin(t * 14)) * 1.2 : 0;
      ctx.fillStyle = '#2f3e63';
      ctx.fillRect(-5, -9, 4, 9 - Math.max(0, k) * 3);
      ctx.fillRect(1, -9, 4, 9 - Math.max(0, -k) * 3);
      ctx.translate(0, bote);
      ctx.fillStyle = '#d9534f'; ctx.fillRect(-6, -20, 12, 12);
      ctx.fillStyle = '#b9403c'; ctx.fillRect(-8, -19 + k * 1.5, 3, 9); ctx.fillRect(5, -19 - k * 1.5, 3, 9);
      ctx.fillStyle = '#f2c79b'; ctx.fillRect(-6, -31, 12, 11);
      ctx.fillStyle = '#4a2f1b'; ctx.fillRect(-7, -33, 14, 5); ctx.fillRect(-7, -31, 3, 6);
      ctx.fillStyle = '#1d1d1f'; ctx.fillRect(0, -26, 2, 2); ctx.fillRect(4, -26, 1.5, 2);
      ctx.restore();
    }

    function gachamon(img, x, y, dir, mov, t, alto) {
      if (!img || !img.complete || !img.naturalWidth) return;
      var h = alto, w = img.naturalWidth / img.naturalHeight * h;
      var salto = mov ? -Math.abs(Math.sin(t * 10)) * 5 : -Math.abs(Math.sin(t * 2.2)) * 1.2;
      ctx.fillStyle = 'rgba(0,0,0,.22)'; elipse(x, y, w * 0.36, 3); ctx.fill();
      ctx.save();
      ctx.translate(x, y + salto);
      ctx.scale(-dir, 1);
      ctx.drawImage(img, -w / 2, -h, w, h);
      ctx.restore();
    }

    function dibujarGlobo() {
      if (!S.globo || S.t > S.globo.hasta) return;
      ctx.font = '600 8.5px ' + TEXTO;
      var palabras = S.globo.texto.split(' '), lineas = [''];
      for (var i = 0; i < palabras.length; i++) {
        var prueba = (lineas[lineas.length - 1] + ' ' + palabras[i]).trim();
        if (ctx.measureText(prueba).width > 96 && lineas[lineas.length - 1]) lineas.push(palabras[i]);
        else lineas[lineas.length - 1] = prueba;
      }
      var w = 0;
      for (var j = 0; j < lineas.length; j++) w = Math.max(w, ctx.measureText(lineas[j]).width);
      w += 14;
      var h = lineas.length * 11 + 8;
      var bx = limitar(S.gx - w / 2, S.cam + 4, S.cam + VWU - w - 4);
      var by = Math.max(S.gy - cfg.altoG - 12 - h, 44 / z);
      var cola = limitar(S.gx, bx + 8, bx + w - 8);
      ctx.fillStyle = '#fff'; ctx.strokeStyle = '#1d1d1f'; ctx.lineWidth = 1.2;
      rr(bx, by, w, h, 6); ctx.fill(); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(cola - 4, by + h - 0.8); ctx.lineTo(cola, by + h + 6); ctx.lineTo(cola + 4, by + h - 0.8); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(cola - 4, by + h); ctx.lineTo(cola, by + h + 6); ctx.lineTo(cola + 4, by + h); ctx.stroke();
      ctx.fillStyle = '#1d1d1f'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      for (var l = 0; l < lineas.length; l++) ctx.fillText(lineas[l], bx + w / 2, by + 4 + 11 * l + 6);
    }

    function trazarCaminos() {
      ctx.beginPath();
      for (var i = 0; i < cfg.aristas.length; i++) {
        var a = N[cfg.aristas[i][0]], b = N[cfg.aristas[i][1]];
        ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]);
      }
      ctx.stroke();
    }

    function dibujarLejos() {
      /* el cielo y los biomas, allá al fondo */
      ctx.fillStyle = '#bfe3f2'; ctx.fillRect(0, 0, W, 56);
      ctx.fillStyle = '#9fb7c9';
      ctx.beginPath(); ctx.moveTo(505, 62); ctx.lineTo(560, 34); ctx.lineTo(612, 62); ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.beginPath(); ctx.moveTo(549, 40); ctx.lineTo(560, 34); ctx.lineTo(571, 40); ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#8b6f66';
      ctx.beginPath(); ctx.moveTo(606, 64); ctx.lineTo(652, 33); ctx.lineTo(690, 64); ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#e4572e';
      ctx.beginPath(); ctx.moveTo(644, 39); ctx.lineTo(652, 33); ctx.lineTo(659, 39); ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#74b45f';
      var lomas = [[60, 66, 90, 20], [215, 68, 110, 22], [380, 66, 100, 20], [520, 70, 90, 16], [660, 72, 70, 14]];
      for (var i = 0; i < lomas.length; i++) { elipse(lomas[i][0], lomas[i][1], lomas[i][2], lomas[i][3]); ctx.fill(); }
      ctx.fillStyle = '#86c46f'; ctx.fillRect(0, 70, W, 20);
    }

    function flecha(x, sentido) {
      ctx.fillStyle = 'rgba(20,24,28,.6)'; elipse(x, 300, 12, 12); ctx.fill();
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 2.4; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.beginPath(); ctx.moveTo(x - 3 * sentido, 294); ctx.lineTo(x + 3 * sentido, 300); ctx.lineTo(x - 3 * sentido, 306); ctx.stroke();
    }

    var ordenLugares = Object.keys(LUGARES).filter(function (id) { return N[id]; })
      .sort(function (a, b) { return N[a][1] - N[b][1]; });

    function dibujar() {
      var e = dpr * z;
      ctx.setTransform(e, 0, 0, e, -S.cam * e, 0);
      ctx.fillStyle = '#86c46f'; ctx.fillRect(0, 0, W, H);
      if (cfg.lejos) dibujarLejos();
      ctx.fillStyle = '#76b662';
      for (var i = 0; i < matas.length; i++) ctx.fillRect(matas[i][0], matas[i][1], 3, 1.6);
      for (var p = 0; p < cfg.estanques.length; p++) {
        var q = cfg.estanques[p];
        ctx.fillStyle = '#5aa9d6'; elipse(q[0], q[1], q[2], q[3]); ctx.fill();
        ctx.fillStyle = '#8ccbee'; elipse(q[0] - 5, q[1] - 3, q[2] * 0.55, q[3] * 0.45); ctx.fill();
      }
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.strokeStyle = '#b89460'; ctx.lineWidth = 17; trazarCaminos();
      ctx.strokeStyle = '#e3c995'; ctx.lineWidth = 13; trazarCaminos();

      for (var l = 0; l < ordenLugares.length; l++) dibujarLugar(ordenLugares[l]);
      for (var a = 0; a < cfg.arboles.length; a++) arbol(cfg.arboles[a][0], cfg.arboles[a][1]);

      for (var o = 0; o < cfg.ociosos.length; o++) {
        var oc = cfg.ociosos[o], n = N[oc.nodo];
        gachamon(IMG[oc.img], n[0] + oc.dx, n[1] + oc.dy, oc.dir, false, S.t + o * 1.3, oc.alto);
      }

      if (S.mov && S.destino) {
        var d = N[S.destino], tope = topeDe(S.destino) + 12 + Math.abs(Math.sin(S.t * 5)) * 4;
        ctx.fillStyle = '#ffd23f'; ctx.strokeStyle = '#1d1d1f'; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(d[0] - 6, d[1] - tope - 8); ctx.lineTo(d[0] + 6, d[1] - tope - 8); ctx.lineTo(d[0], d[1] - tope); ctx.closePath();
        ctx.fill(); ctx.stroke();
      }

      if (S.gy <= S.y) {
        gachamon(IMG.pollito, S.gx, S.gy, S.gdir, S.gmov, S.t, cfg.altoG);
        avatar(S.x, S.y, S.dir, S.mov, S.t);
      } else {
        avatar(S.x, S.y, S.dir, S.mov, S.t);
        gachamon(IMG.pollito, S.gx, S.gy, S.gdir, S.gmov, S.t, cfg.altoG);
      }
      dibujarGlobo();

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (cfg.desliza) {
        if (S.cam < maxCam - 2) flecha(VW - 18, 1);
        if (S.cam > 2) flecha(18, -1);
      }
    }

    /* ---------- toques ---------- */
    function tocar(wx, wy) {
      var mejor = null, md = Infinity;
      for (var id in LUGARES) {
        if (!N[id]) continue;
        var cx = N[id][0], cy = LUGARES[id].tipo === 'plaza' ? N[id][1] : N[id][1] - 30;
        var dx = Math.abs(wx - cx), dy = Math.abs(wy - cy);
        if (dx < 40 && dy < 42 && dx + dy < md) { md = dx + dy; mejor = id; }
      }
      if (mejor) ir(mejor); else cerrarHoja();
    }

    var abajo = null;
    canvas.addEventListener('pointerdown', function (e) {
      abajo = { x: e.clientX, y: e.clientY, cam: S.cam, arrastra: false };
      if (canvas.setPointerCapture) { try { canvas.setPointerCapture(e.pointerId); } catch (err) { /* da igual */ } }
    });
    canvas.addEventListener('pointermove', function (e) {
      if (!abajo) return;
      var dx = e.clientX - abajo.x;
      if (Math.abs(dx) > 8 || Math.abs(e.clientY - abajo.y) > 8) abajo.arrastra = true;
      if (abajo.arrastra && cfg.desliza) { S.sigue = false; S.cam = limitar(abajo.cam - dx / z, 0, maxCam); }
    });
    canvas.addEventListener('pointerup', function (e) {
      if (!abajo) return;
      var a = abajo; abajo = null;
      if (a.arrastra) return;
      var caja = canvas.getBoundingClientRect(), k = VW / (caja.width || VW);
      tocar((e.clientX - caja.left) * k / z + S.cam, (e.clientY - caja.top) * k / z);
    });
    canvas.addEventListener('pointercancel', function () { abajo = null; });

    var antes = null;
    function cuadro(ahora) {
      var dt = antes === null ? 0 : Math.min(0.05, (ahora - antes) / 1000);
      antes = ahora;
      paso(dt);
      dibujar();
      window.requestAnimationFrame(cuadro);
    }
    window.requestAnimationFrame(cuadro);

    return { S: S, ir: ir, paso: paso, dibujar: dibujar, tocar: tocar, ruta: ruta };
  }

  window.GM = { crearMapa: crearMapa, MAPAS: MAPAS, LUGARES: LUGARES, instancias: {} };
  var raices = document.querySelectorAll('[data-gm]');
  for (var i = 0; i < raices.length; i++) {
    var nombre = raices[i].getAttribute('data-gm');
    window.GM.instancias[nombre] = crearMapa(raices[i], MAPAS[nombre]);
  }
})();
