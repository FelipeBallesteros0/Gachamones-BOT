-- Los seis sombreros propios de Geo, 256x256.
--
-- Uno por cosmético y el mismo para las cinco formas, al revés que las caras.
-- Se apoyan alrededor de y=POSA, que es donde pasa la coronilla: los cinco
-- cuerpos la tienen entre y=18 y y=36, así que un sombrero apoyado ahí se posa
-- en todos. **Se hunde un poco en la piedra a propósito**: los cuerpos llenan
-- el lienzo de arriba abajo y no dejan aire encima, así que un sombrero que
-- flotara por encima se saldría del lienzo.
--
--   Aseprite.exe --batch --script fuentes/aseprite/geo/sombreros.lua

local LIENZO = 256
local RAIZ = "/home/felipe/tamagotchi-bot/"
local POSA = 50          -- donde apoya la base del sombrero
local CX = 128

local function px(r, g, b) return app.pixelColor.rgba(r, g, b, 255) end
local BORDE = px(0x0D, 0x0F, 0x12)   -- el mismo negro que contornea los cuerpos

local function lienzo() return Image(LIENZO, LIENZO, ColorMode.RGB) end

local function rect(img, x0, y0, x1, y1, c)
  for y = y0, y1 do for x = x0, x1 do img:drawPixel(x, y, c) end end
end

-- Contornea de negro lo que ya esté pintado, como los cuerpos.
local function contornear(img)
  local marcas = {}
  for y = 0, LIENZO - 1 do
    for x = 0, LIENZO - 1 do
      if app.pixelColor.rgbaA(img:getPixel(x, y)) == 0 then
        local toca = false
        for _, d in ipairs({ {1,0}, {-1,0}, {0,1}, {0,-1} }) do
          local ax, ay = x + d[1], y + d[2]
          if ax >= 0 and ay >= 0 and ax < LIENZO and ay < LIENZO
              and app.pixelColor.rgbaA(img:getPixel(ax, ay)) ~= 0 then
            toca = true
          end
        end
        if toca then marcas[#marcas + 1] = { x, y } end
      end
    end
  end
  for _, p in ipairs(marcas) do img:drawPixel(p[1], p[2], BORDE) end
end

local function guardar(img, archivo)
  contornear(img)
  local sprite = Sprite(LIENZO, LIENZO, ColorMode.RGB)
  sprite.cels[1].image = img
  sprite.cels[1].position = Point(0, 0)
  sprite:saveAs(RAIZ .. "fuentes/aseprite/geo/sombrero_" .. archivo .. ".aseprite")
  sprite:saveCopyAs(RAIZ .. "fuentes/sombreros/geo/" .. archivo .. ".png")
  sprite:close()
  print("hecho sombreros/geo/" .. archivo)
end

-- --- Aureola ---------------------------------------------------------------
local img = lienzo()
do
  local oro, oro2 = px(0xF2, 0xD5, 0x5C), px(0xC0, 0x9A, 0x28)
  local rx, ry, cy = 52, 13, 20
  for a = 0, 719 do
    local rad = math.rad(a / 2)
    local x = math.floor(CX + rx * math.cos(rad) + 0.5)
    local y = math.floor(cy + ry * math.sin(rad) + 0.5)
    for g = 0, 4 do
      img:drawPixel(x, y + g, (g < 2 and math.sin(rad) < 0) and oro or oro2)
    end
  end
end
guardar(img, "aureola")

-- --- Chistera --------------------------------------------------------------
img = lienzo()
do
  local negro, luz = px(0x26, 0x26, 0x2E), px(0x44, 0x44, 0x52)
  local banda = px(0x8E, 0x24, 0x28)
  rect(img, 60, POSA - 12, 196, POSA + 2, negro)       -- ala
  rect(img, 60, POSA - 12, 196, POSA - 9, luz)
  rect(img, 88, 2, 168, POSA - 13, negro)              -- copa
  rect(img, 88, POSA - 32, 168, POSA - 20, banda)      -- cinta
  rect(img, 94, 6, 100, POSA - 34, luz)                -- brillo del raso
end
guardar(img, "chistera")

-- --- Cinta: un lazo de raso -----------------------------------------------
img = lienzo()
do
  local raso, hondo = px(0xC8, 0x2A, 0x3C), px(0x8E, 0x18, 0x28)
  local luz = px(0xE8, 0x5A, 0x66)
  -- Cargado a la derecha, para que los cabos cuelguen fuera de la cara.
  local nx, ny = 178, POSA - 6
  for lado = 0, 1 do
    local dir = (lado == 0) and -1 or 1
    for i = 1, 30 do
      local alto = math.floor(17 * math.sin(i / 30 * math.pi)) + 2
      for g = -alto, alto do
        local x, y = nx + dir * i, ny + g
        if g < -alto + 4 then img:drawPixel(x, y, luz)
        elseif g > alto - 4 then img:drawPixel(x, y, hondo)
        else img:drawPixel(x, y, raso) end
      end
      -- El hueco del bucle, que es lo que lo hace lazo y no pegote.
      if i > 9 and i < 26 then
        local hueco = math.floor(8 * math.sin((i - 9) / 17 * math.pi))
        for g = -hueco, hueco do img:drawPixel(nx + dir * i, ny + g, 0) end
      end
    end
  end
  rect(img, nx - 7, ny - 10, nx + 7, ny + 10, raso)          -- el nudo
  rect(img, nx - 7, ny - 10, nx + 7, ny - 6, luz)
  rect(img, nx - 7, ny + 6, nx + 7, ny + 10, hondo)
  for cabo = 0, 1 do
    local dx = (cabo == 0) and -7 or 7
    local largo = (cabo == 0) and 66 or 50
    for i = 0, largo do
      local x = nx + dx + math.floor(i * (cabo == 0 and -0.18 or 0.22))
      local y = ny + 11 + i
      local ancho = 7
      if i > largo - 8 then ancho = 7 - (i - (largo - 8)) end   -- punta al bies
      for g = -ancho, ancho do
        if g <= -ancho + 2 then img:drawPixel(x + g, y, luz)
        elseif g >= ancho - 2 then img:drawPixel(x + g, y, hondo)
        else img:drawPixel(x + g, y, raso) end
      end
    end
  end
end
guardar(img, "cinta")

-- --- Corona ----------------------------------------------------------------
img = lienzo()
do
  local oro, oro2 = px(0xE9, 0xBC, 0x4E), px(0xA8, 0x7E, 0x22)
  local joya = px(0xC0, 0x39, 0x39)
  rect(img, 72, POSA - 16, 184, POSA, oro)
  rect(img, 72, POSA - 5, 184, POSA, oro2)
  for i, x in ipairs({ 76, 104, 132, 160 }) do
    local alto = (i % 2 == 0) and 24 or 34
    rect(img, x, POSA - 16 - alto, x + 20, POSA - 17, oro)
    rect(img, x + 6, POSA - 20 - alto, x + 14, POSA - 13 - alto, joya)
  end
end
guardar(img, "corona")

-- --- Cuernos ---------------------------------------------------------------
img = lienzo()
do
  local hueso, sombra = px(0xDC, 0xD3, 0xAE), px(0x9E, 0x95, 0x72)
  for lado = 0, 1 do
    local dir = (lado == 0) and -1 or 1
    local x = CX + dir * 26
    for i = 0, 40 do
      local ancho = math.max(2, 11 - math.floor(i / 4))
      local cx = x + dir * math.floor(i * 0.85)
      for g = 0, ancho - 1 do
        img:drawPixel(cx + dir * g, POSA - 4 - i, (g < ancho - 3) and hueso or sombra)
      end
    end
  end
end
guardar(img, "cuernos")

-- --- Laurel ----------------------------------------------------------------
img = lienzo()
do
  local verde, verde2 = px(0x6C, 0x93, 0x40), px(0x46, 0x66, 0x26)
  for lado = 0, 1 do
    local dir = (lado == 0) and -1 or 1
    for i = 0, 13 do
      local x = CX + dir * (12 + i * 6)
      local y = POSA - 2 - math.floor(i * i * 0.28)
      rect(img, x - 1, y, x + 1, y + 3, verde2)               -- el tallo
      if i % 2 == 0 then                                      -- la hoja
        for h = 0, 9 do
          local ancho = math.floor(4 * math.sin((h + 1) / 11 * math.pi)) + 1
          for g = -ancho, ancho do
            img:drawPixel(x + dir * h, y - 5 + g, (g < 0) and verde or verde2)
          end
        end
      end
    end
  end
end
guardar(img, "laurel")
