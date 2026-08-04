-- Los cinco cuerpos de Geo, en pixelart de 128x128.
--
-- Se dibuja por procedimiento y no a mano porque son miles de píxeles, pero
-- **es determinista**: el mismo script da el mismo PNG, así que volver a
-- generarlo no ensucia el repositorio ni engaña a `componer.py --comprobar`.
--
-- De la descripción del brief: canto rodado gris más ancho que alto, aristas
-- gastadas, vetas más claras; al crecer, fracturas, líquenes en las juntas y
-- dos patas cortas y macizas. Sin cuello, sin brazos, sin cola: un bloque.
--
-- **Pedrusco, no lápida.** La primera versión salía lápida y el motivo era la
-- geometría, no el color: base plana, flancos verticales, silueta simétrica y
-- sombreado en bandas horizontales son las cuatro señas de una losa clavada en
-- el suelo. Aquí la silueta es un polígono irregular de facetas rectas, con la
-- panza más ancha que la base, distinta a izquierda y derecha, y la luz entra
-- en diagonal para que las caras se lean como planos y no como estratos.
--
--   Aseprite.exe --batch --script fuentes/aseprite/geo/cuerpos.lua

local LIENZO = 128
local RAIZ = "/home/felipe/tamagotchi-bot/"

-- El hueco de la cara. Aquí no entra ni una veta ni una mota: los ojos los
-- pone otra capa encima y necesitan superficie limpia donde apoyarse.
local CARA = { x0 = 50, y0 = 53, x1 = 76, y1 = 76 }

-- Paleta corta a propósito: seis tonos y un verde. Con más, deja de leerse
-- como pixelart y empieza a parecer una foto mal escalada.
local C = {
  contorno = { r = 0x33, g = 0x37, b = 0x3D },
  sombra   = { r = 0x53, g = 0x59, b = 0x61 },
  base     = { r = 0x6E, g = 0x75, b = 0x7E },
  claro    = { r = 0x87, g = 0x8F, b = 0x99 },
  veta     = { r = 0xA8, g = 0xB0, b = 0xBA },
  brillo   = { r = 0xC6, g = 0xCD, b = 0xD6 },
  liquen   = { r = 0x6F, g = 0x8F, b = 0x4A },
  liquen2  = { r = 0x53, g = 0x6E, b = 0x30 },
}

local function px(c) return app.pixelColor.rgba(c.r, c.g, c.b, 255) end

-- Un generador propio y con semilla: `math.random` cambiaría entre versiones y
-- el dibujo dejaría de ser reproducible.
local function azar(semilla)
  local s = semilla % 2147483648
  return function()
    s = (1103515245 * s + 12345) % 2147483648
    return s / 2147483648
  end
end

-- **Perspectiva caballera.** La cara de delante se dibuja en verdadera forma y
-- la profundidad se arrastra a 45 grados hacia arriba y a la derecha. Así el
-- pedrusco deja de ser una silueta recortada y pasa a ser un volumen con tres
-- planos: frente, tapa y costado.
--
-- El fondo (`hondo`) está atado por dos sitios y por eso es corto:
--   * la cara va sobre el FRENTE, y el hueco empieza en y=53, así que el
--     frente no puede empezar más abajo de ahí;
--   * la tapa sube `hondo` píxeles por encima del frente, y ahí es donde se
--     posan los sombreros, que son una sola imagen para las cinco formas.
--
-- Las cinco formas. La cima del volumen queda entre y=44 y y=46 —una banda
-- estrecha a propósito— y lo que crece es el ancho, como en el arte ASCII.
local FORMAS = {
  { nombre = "cria",          cx = 64, rx = 23, alto = 42, hondo = 5, suelo = 88,  semilla = 11,
    grietas = 0, liquen = 0, patas = false },
  { nombre = "niño",          cx = 63, rx = 29, alto = 47, hondo = 6, suelo = 92,  semilla = 23,
    grietas = 1, liquen = 1, patas = false },
  { nombre = "adolecente",    cx = 65, rx = 36, alto = 51, hondo = 7, suelo = 96,  semilla = 37,
    grietas = 2, liquen = 2, patas = false },
  { nombre = "adulto",        cx = 63, rx = 44, alto = 56, hondo = 8, suelo = 100, semilla = 51,
    grietas = 3, liquen = 3, patas = true },
  { nombre = "adulto_grande", cx = 64, rx = 52, alto = 62, hondo = 8, suelo = 106, semilla = 67,
    grietas = 4, liquen = 5, patas = true },
}

local VERTICES = 9   -- facetas del contorno; pocas y rectas, que es lo que le
                     -- da cara de piedra partida en vez de cúpula lisa.

local function en_la_cara(x, y)
  return x >= CARA.x0 and x <= CARA.x1 and y >= CARA.y0 and y <= CARA.y1
end

-- El contorno de arriba: un polígono irregular, no media elipse. Cada vértice
-- se sale de su sitio una cantidad distinta, así que los dos flancos salen
-- diferentes y la piedra deja de ser simétrica.
local function contorno(forma)
  local r = azar(forma.semilla)
  -- El frente ocupa el hueco que deja la profundidad: el arrastre a 45 grados
  -- se lleva `hondo` hacia arriba y otro tanto hacia la derecha, y entre los
  -- dos completan la caja que ocupa el bicho.
  local rxf = forma.rx - forma.hondo / 2
  local cxf = forma.cx - forma.hondo / 2
  local altof = forma.alto - forma.hondo
  local vs = {}
  for k = 0, VERTICES do
    local t = k / VERTICES
    local ang = math.pi * (1 - t)
    -- La panza va más ancha que la base: cerca del suelo el radio se recoge,
    -- de modo que el canto se apoya en dos puntos y no en todo el flanco.
    local altura = math.sin(ang)
    local recogida = 1 - 0.22 * (1 - altura) ^ 2
    -- Irregular, pero con la mano contenida: con el temblor muy suelto un
    -- flanco se dispara y la piedra sale en forma de cuña.
    local rr = (0.88 + r() * 0.22) * recogida
    local ra = 0.86 + r() * 0.22
    vs[#vs + 1] = {
      x = cxf + rxf * math.cos(ang) * rr,
      y = forma.suelo - altof * altura * ra,
    }
  end
  vs[1].y = forma.suelo
  vs[#vs].y = forma.suelo

  -- Se recorre el polígono uniendo vértices con rectas: cada tramo es una
  -- faceta plana, y el quiebro entre dos se ve como arista. Se apunta **de qué
  -- faceta viene cada columna**, porque de ahí sale luego su tono: una cara
  -- vuelta hacia el cielo recibe más luz que una casi vertical.
  local techo, faceta, pendiente = {}, {}, {}
  for i = 1, #vs - 1 do
    local a, b = vs[i], vs[i + 1]
    local dx, dy = b.x - a.x, b.y - a.y
    pendiente[i] = (math.abs(dx) < 0.5) and 99 or math.abs(dy / dx)
    local x0, x1 = math.floor(a.x + 0.5), math.floor(b.x + 0.5)
    if x1 < x0 then x0, x1 = x1, x0; a, b = b, a end
    for x = x0, x1 do
      local u = (x1 == x0) and 0 or (x - x0) / (x1 - x0)
      local y = math.floor(a.y + (b.y - a.y) * u + 0.5)
      if techo[x] == nil or y < techo[x] then techo[x] = y; faceta[x] = i end
    end
  end

  -- El hueco de la cara tiene que caer SOBRE la piedra en las cinco formas,
  -- también en la cría. Se garantiza aquí en vez de confiar en la geometría.
  for x = CARA.x0, CARA.x1 do
    if techo[x] == nil or techo[x] > CARA.y0 - 1 then
      techo[x] = CARA.y0 - 1
      faceta[x] = faceta[x] or 1
    end
  end
  return techo, faceta, pendiente
end

local function dibujar(forma)
  local img = Image(LIENZO, LIENZO, ColorMode.RGB)
  local r = azar(forma.semilla + 900)
  local techo, faceta, pendiente = contorno(forma)

  local izq, der = LIENZO, 0
  for x = 0, LIENZO - 1 do
    if techo[x] then
      if x < izq then izq = x end
      if x > der then der = x end
    end
  end

  -- La cara de delante, en verdadera forma.
  local frente = {}
  for x = izq, der do
    if techo[x] then
      frente[x] = {}
      for y = techo[x], forma.suelo do frente[x][y] = true end
    end
  end

  -- 1. El VOLUMEN, en perspectiva caballera: se arrastra el frente a 45 grados
  -- arriba y a la derecha, y lo que barre por el camino son la tapa y el
  -- costado. Tres planos, cada uno de un tono liso —eso es lo que se lee como
  -- volumen; un degradado sólo se lee como mancha.
  local dentro = {}
  for x = izq, der do
    if frente[x] then
      for y = techo[x], forma.suelo do
        for t = 0, forma.hondo do
          local ax, ay = x + t, y - t
          if ax >= 0 and ax < LIENZO and ay >= 0 then
            dentro[ax] = dentro[ax] or {}
            dentro[ax][ay] = true
          end
        end
      end
    end
  end

  -- El borde derecho del frente, para saber qué queda de costado.
  local derecha = {}
  for x = izq, der do
    if frente[x] then
      for y in pairs(frente[x]) do
        if derecha[y] == nil or x > derecha[y] then derecha[y] = x end
      end
    end
  end

  local ancho = der - izq

  local function tono_de_faceta(i)
    local p = pendiente[i] or 1
    if p < 0.30 then return C.claro       -- casi plana
    elseif p < 0.75 then return C.claro
    else return C.base end                -- casi vertical: le llega menos luz
  end

  -- La junta entre los dos flancos del frente: quebrada, no recta, para que no
  -- parta la piedra en dos mitades limpias.
  local junta = {}
  local jx = izq + ancho * (0.52 + r() * 0.12)
  for y = 0, LIENZO - 1 do
    junta[y] = math.floor(jx)
    if y % 4 == 0 then jx = jx + (r() * 3 - 1.2) end
  end

  for x = 0, LIENZO - 1 do
    if dentro[x] then
      for y in pairs(dentro[x]) do
        local c
        if frente[x] and frente[x][y] then
          -- El frente: mira de canto a la luz, así que va en los tonos medios,
          -- con las facetas del contorno marcando planos y el asiento oscuro.
          local fondo = forma.suelo - techo[x]
          local capa = math.max(3, math.floor(fondo * 0.42))
          if y - techo[x] < capa then c = tono_de_faceta(faceta[x])
          elseif y > forma.suelo - 4 then c = C.sombra
          elseif x < junta[y] then c = C.claro
          else c = C.base end
        elseif techo[x] ~= nil and y < techo[x] then
          c = C.brillo                    -- la tapa: mira al cielo
        else
          -- Todo lo demás del arrastre es costado, incluida la franja a la
          -- derecha del frente, donde ya no hay contorno que consultar. Con la
          -- condición al revés esa franja se iba a la tapa y el bicho salía
          -- envuelto en una capucha clara.
          c = C.sombra
        end
        img:drawPixel(x, y, px(c))
      end
    end
  end

  -- La arista donde se doblan frente y tapa. Sin ella los dos planos se tocan
  -- por un cambio de tono y el volumen no acaba de leerse.
  for x = izq, der do
    if techo[x] then
      img:drawPixel(x, techo[x], px(C.veta))
    end
  end
  for y = 0, LIENZO - 1 do
    if derecha[y] then img:drawPixel(derecha[y], y, px(C.base)) end
  end

  -- 2. Aristas internas: desde algunos vértices del contorno baja un quiebro
  -- hacia dentro, y lo que queda a un lado se oscurece un paso. Es lo que
  -- convierte una mancha gris en un bloque con caras.
  local aristas = 2 + math.floor(forma.rx / 24)
  for a = 1, aristas do
    local x = izq + math.floor((a / (aristas + 1)) * ancho + (r() * 10 - 5))
    if frente[x] then
      local y = techo[x]
      local caida = math.floor((forma.suelo - y) * (0.45 + r() * 0.35))
      local sesgo = (r() < 0.5) and -1 or 1
      for paso = 1, caida do
        if frente[x] and frente[x][y] and not en_la_cara(x, y) then
          img:drawPixel(x, y, px(C.sombra))
        end
        y = y + 1
        if paso % 3 == 0 then x = x + sesgo end
      end
    end
  end

  -- 3. Vetas: trazos CORTOS y torcidos, no rayas de lado a lado. Cruzando el
  -- bloque entero parecían arañazos o lluvia; a trozos parecen mineral.
  local vetas = 2 + math.floor(forma.rx / 18)
  for _ = 1, vetas do
    local x = izq + 3 + math.floor(r() * (ancho - 6))
    local y = math.floor(forma.suelo - forma.alto * (0.2 + r() * 0.55))
    local largo = 4 + math.floor(r() * (forma.rx * 0.4))
    local sube = (r() < 0.5)
    for paso = 1, largo do
      if frente[x] and frente[x][y] and not en_la_cara(x, y) then
        img:drawPixel(x, y, px(C.veta))
      end
      x = x + 1
      if paso % 2 == 0 then y = y + (sube and -1 or 1) end
    end
  end

  -- 4. Motas sueltas. Son lo que hace que se lea «piedra» y no «huevo».
  for _ = 1, math.floor(ancho * 1.5) do
    local x = izq + math.floor(r() * ancho)
    local y = math.floor(r() * LIENZO)
    if frente[x] and frente[x][y] and not en_la_cara(x, y) then
      img:drawPixel(x, y, px(r() < 0.5 and C.veta or C.sombra))
    end
  end

  -- 5. Fracturas: bajan desde la arista de arriba, torciéndose.
  for f = 1, forma.grietas do
    local x = izq + math.floor((f / (forma.grietas + 1)) * ancho)
    if frente[x] then
      local y = techo[x] + 1
      local largo = math.floor((forma.suelo - y) * (0.4 + r() * 0.4))
      for _ = 1, largo do
        if frente[x] and frente[x][y] and not en_la_cara(x, y) then
          img:drawPixel(x, y, px(C.contorno))
        end
        y = y + 1
        if r() < 0.34 then x = x + (r() < 0.5 and -1 or 1) end
      end
    end
  end

  -- 6. Líquenes en las juntas: abajo y en los flancos, donde se acumula la
  -- humedad. Manchas pequeñas de dos verdes, nunca en la cara.
  for l = 1, forma.liquen do
    local x = (l % 2 == 0) and izq + 4 + math.floor(r() * 8)
                            or der - 4 - math.floor(r() * 8)
    local y = forma.suelo - 2 - math.floor(r() * forma.alto * 0.4)
    for dy = 0, 2 do
      for dx = -2, 2 do
        local ax, ay = x + dx, y + dy
        if frente[ax] and frente[ax][ay] and not en_la_cara(ax, ay)
            and (dx * dx + dy * dy) <= 5 then
          img:drawPixel(ax, ay, px(r() < 0.6 and C.liquen or C.liquen2))
        end
      end
    end
  end

  -- 7. Las patas: dos bloques cortos y macizos que asoman por debajo. No son
  -- piernas, son apoyos, y sólo las tienen las dos formas mayores.
  if forma.patas then
    local w = 15
    for _, centro in ipairs({ izq + ancho * 0.28, der - ancho * 0.28 }) do
      local x0 = math.floor(centro - w / 2)
      for x = x0, x0 + w - 1 do
        for y = forma.suelo - 1, forma.suelo + 5 do
          dentro[x] = dentro[x] or {}
          dentro[x][y] = true
          img:drawPixel(x, y, px(y > forma.suelo + 3 and C.sombra or C.base))
        end
      end
    end
  end

  -- 8. El contorno, al final: todo píxel con tinta que toque el vacío.
  local borde = {}
  for x = 0, LIENZO - 1 do
    for y = 0, LIENZO - 1 do
      if dentro[x] and dentro[x][y] then
        local fuera = false
        for _, d in ipairs({ { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } }) do
          local ax, ay = x + d[1], y + d[2]
          if ax < 0 or ay < 0 or ax >= LIENZO or ay >= LIENZO
              or not (dentro[ax] and dentro[ax][ay]) then
            fuera = true
          end
        end
        if fuera then borde[#borde + 1] = { x, y } end
      end
    end
  end
  for _, p in ipairs(borde) do
    img:drawPixel(p[1], p[2], px(C.contorno))
  end

  return img
end

for _, forma in ipairs(FORMAS) do
  local sprite = Sprite(LIENZO, LIENZO, ColorMode.RGB)
  sprite.cels[1].image = dibujar(forma)
  sprite.cels[1].position = Point(0, 0)
  sprite:saveAs(RAIZ .. "fuentes/aseprite/geo/geo_body_" .. forma.nombre .. ".aseprite")
  sprite:saveCopyAs(RAIZ .. "fuentes/cuerpos/geo_body_" .. forma.nombre .. ".png")
  sprite:close()
  print("hecho " .. forma.nombre)
end
