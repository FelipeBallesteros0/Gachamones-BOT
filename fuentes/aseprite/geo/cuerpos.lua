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

-- Las cinco formas. El borde de arriba apenas sube (48 -> 40) y lo que crece
-- de verdad es el ancho: así una sola imagen de sombrero se apoya bien en las
-- cinco, y además es como crece en el arte ASCII, a lo ancho.
-- Siempre **más ancho que alto**, que es lo que dice el brief y lo que separa
-- un canto rodado de un huevo o de un iglú.
local FORMAS = {
  { nombre = "cria",          x0 = 42, x1 = 86,  y0 = 52, y1 = 88,  semilla = 11,
    grietas = 0, liquen = 0, patas = false },
  { nombre = "niño",          x0 = 36, x1 = 92,  y0 = 50, y1 = 92,  semilla = 23,
    grietas = 1, liquen = 0, patas = false },
  { nombre = "adolecente",    x0 = 29, x1 = 99,  y0 = 48, y1 = 96,  semilla = 37,
    grietas = 2, liquen = 2, patas = false },
  { nombre = "adulto",        x0 = 21, x1 = 107, y0 = 46, y1 = 100, semilla = 51,
    grietas = 3, liquen = 3, patas = true },
  { nombre = "adulto_grande", x0 = 12, x1 = 116, y0 = 44, y1 = 106, semilla = 67,
    grietas = 4, liquen = 5, patas = true },
}

local function en_la_cara(x, y)
  return x >= CARA.x0 and x <= CARA.x1 and y >= CARA.y0 and y <= CARA.y1
end

local function dibujar(forma)
  local img = Image(LIENZO, LIENZO, ColorMode.RGB)
  local r = azar(forma.semilla)

  local cx = (forma.x0 + forma.x1) / 2
  local rx = (forma.x1 - forma.x0) / 2
  local suelo = forma.y1
  local ry = forma.y1 - forma.y0

  -- 1. La silueta. **Superelipse**, no elipse: con exponente 3,2 sale un
  -- rectángulo de esquinas comidas, que es lo que dice el arte ASCII de Geo
  -- (`,---.` sobre `` `---' ``) y lo que hace que se lea piedra y no huevo.
  -- Base plana abajo: está asentado, no flotando. El temblor de la arista sale
  -- de dos senos desfasados redondeados a entero, y es la «arista gastada».
  local N = 2.6
  local FACETA = 3   -- ancho de cada plano del contorno
  local techo = {}
  for x = forma.x0, forma.x1 do
    -- El contorno se evalúa en escalones de tres píxeles, no en cada columna.
    -- Eso da planos rectos con saltos limpios —piedra tallada— en vez de una
    -- curva suave, que a esta resolución se lee como cúpula o casco.
    local xf = forma.x0 + math.floor((x - forma.x0) / FACETA) * FACETA
    local t = math.abs((xf - cx) / rx)
    local v = (1 - math.min(1, t ^ N)) ^ (1 / N)
    -- Ondulación LENTA. Con la frecuencia alta que tenía antes salían dientes
    -- de muela en vez de aristas gastadas: el desgaste de un canto rodado son
    -- dos o tres lomas anchas, no quince picos.
    local desgaste = math.floor(2.0 * math.sin(xf * 0.085 + forma.semilla)
                              + 1.2 * math.sin(xf * 0.041 + forma.semilla * 3))
    local y = math.floor(suelo - ry * v) + desgaste
    -- El hueco de la cara tiene que caer SOBRE la piedra en las cinco formas,
    -- también en la cría. Se garantiza aquí, bajando el techo donde haga falta,
    -- en vez de confiar en que la geometría salga bien: confiar fallaba.
    if x >= CARA.x0 and x <= CARA.x1 then
      y = math.min(y, CARA.y0 - 1)
    end
    techo[x] = math.min(y, suelo)
  end

  local dentro = {}
  for x = forma.x0, forma.x1 do
    dentro[x] = {}
    for y = techo[x], suelo do
      dentro[x][y] = true
    end
  end

  -- 2. Relleno en bandas SÓLIDAS que siguen el contorno de arriba, con la luz
  -- cayendo desde el cielo. El damero queda sólo como transición estrecha
  -- entre dos tonos: llenar áreas grandes con damero de dos grises parecidos
  -- se lee como el cuadriculado de la transparencia, no como sombra.
  -- Rampa de cinco tonos, todos sólidos. **Nada de damero**: dos grises
  -- vecinos alternados píxel a píxel se leen exactamente igual que el
  -- cuadriculado con que se pinta la transparencia, y la piedra parecía tener
  -- agujeros. Con cinco escalones sólidos hay volumen de sobra.
  for x = forma.x0, forma.x1 do
    local fondo = suelo - techo[x]
    for y = techo[x], suelo do
      local hondo = (y - techo[x]) / math.max(1, fondo)
      local c
      if hondo < 0.06 then
        c = C.brillo          -- el filo por donde entra la luz
      elseif hondo < 0.28 then
        c = C.veta
      elseif hondo < 0.55 then
        c = C.claro
      elseif hondo < 0.82 then
        c = C.base
      else
        c = C.sombra
      end
      img:drawPixel(x, y, px(c))
    end
  end

  -- 3. Las vetas: líneas finas que acompañan al contorno, no diagonales
  -- rectas. De un gris apenas más claro que su fondo — antes eran goterones
  -- blancos y parecían nieve encima de la piedra.
  local vetas = 1 + math.floor(rx / 26)
  for v = 1, vetas do
    local altura = 0.50 + v * 0.16 + r() * 0.06
    for x = forma.x0, forma.x1 do
      local fondo = suelo - techo[x]
      local y = math.floor(techo[x] + fondo * altura)
             + math.floor(1.5 * math.sin(x * 0.07 + v * 2 + forma.semilla))
      if dentro[x] and dentro[x][y] and not en_la_cara(x, y) then
        img:drawPixel(x, y, px(C.veta))
      end
    end
  end

  -- 4. Motas sueltas. Son lo que hace que se lea «piedra» y no «huevo».
  local motas = math.floor((forma.x1 - forma.x0) * 1.6)
  for _ = 1, motas do
    local x = forma.x0 + math.floor(r() * (forma.x1 - forma.x0))
    local y = forma.y0 + math.floor(r() * (suelo - forma.y0))
    if dentro[x] and dentro[x][y] and not en_la_cara(x, y) then
      img:drawPixel(x, y, px(r() < 0.5 and C.veta or C.sombra))
    end
  end

  -- 5. Fracturas: bajan desde la arista de arriba, torciéndose. Aparecen a
  -- partir del niño y se multiplican con la edad.
  for f = 1, forma.grietas do
    local x = forma.x0 + math.floor((f / (forma.grietas + 1)) * (forma.x1 - forma.x0))
    local y = techo[x] + 1
    local largo = math.floor((suelo - y) * (0.4 + r() * 0.4))
    for paso = 1, largo do
      if dentro[x] and dentro[x][y] and not en_la_cara(x, y) then
        img:drawPixel(x, y, px(C.contorno))
      end
      y = y + 1
      if r() < 0.34 then x = x + (r() < 0.5 and -1 or 1) end
    end
  end

  -- 6. Líquenes en las juntas, o sea abajo y en los flancos, donde se
  -- acumula la humedad. Manchas pequeñas de dos verdes, nunca en la cara.
  for l = 1, forma.liquen do
    local lado = (l % 2 == 0) and forma.x0 + 3 or forma.x1 - 3
    local x = lado + math.floor(r() * 10) - 5
    local y = suelo - 2 - math.floor(r() * (suelo - forma.y0) * 0.45)
    for dy = 0, 2 do
      for dx = -2, 2 do
        local ax, ay = x + dx, y + dy
        if dentro[ax] and dentro[ax][ay] and not en_la_cara(ax, ay)
            and (dx * dx + dy * dy) <= 5 then
          img:drawPixel(ax, ay, px(r() < 0.6 and C.liquen or C.liquen2))
        end
      end
    end
  end

  -- 7. Las patas: dos bloques cortos y macizos que asoman por debajo. No son
  -- piernas, son apoyos, y sólo las tienen las dos formas mayores.
  if forma.patas then
    local ancho = 15
    for _, lado in ipairs({ forma.x0 + rx * 0.45, forma.x1 - rx * 0.45 }) do
      local izq = math.floor(lado - ancho / 2)
      for x = izq, izq + ancho - 1 do
        -- Arrancan un píxel POR ENCIMA del suelo para que queden pegadas al
        -- cuerpo; separadas parecían tacos flotando debajo de la piedra.
        for y = suelo - 1, suelo + 5 do
          dentro[x] = dentro[x] or {}
          dentro[x][y] = true
          img:drawPixel(x, y, px(y > suelo + 3 and C.sombra or C.base))
        end
      end
    end
  end

  -- 8. El contorno, al final: todo píxel con tinta que toque el vacío. Es lo
  -- que le da el borde limpio de pixelart en vez de una mancha.
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
