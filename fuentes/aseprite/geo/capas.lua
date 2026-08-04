-- Las nueve capas propias de Geo: tres caras y seis sombreros, 128x128.
--
-- Van aparte del cuerpo porque el sistema las apila: un cuerpo x tres ánimos x
-- siete sombreros son 21 retratos por forma. Y van propias de Geo, no globales,
-- porque Geo ya está en 128 y las globales siguen en 256: mezclarlas sería un
-- `ValueError` a media generación.
--
--   Aseprite.exe --batch --script fuentes/aseprite/geo/capas.lua

local LIENZO = 128
local RAIZ = "/home/felipe/tamagotchi-bot/"

-- El hueco que dejan libre los cinco cuerpos. Las caras viven dentro.
local CARA = { x0 = 50, y0 = 53, x1 = 76, y1 = 76 }
-- Los cinco cuerpos tienen el filo de arriba entre y=44 (adulto grande) y y=52
-- (cría). Un sombrero se apoya en las CINCO sólo si su base cae en 52 o algo
-- por debajo: apoyado en 44 se posa en el adulto grande y flota trece píxeles
-- sobre la cría. Por eso la base va aquí y no más arriba.
local POSA = 54
-- La cinta es la excepción: no se apoya encima, ciñe la frente, y tiene que
-- caber entre el filo de la piedra y los ojos (y=58).
local FRENTE = 50

local function px(r, g, b) return app.pixelColor.rgba(r, g, b, 255) end

local NEGRO  = px(0x2A, 0x2D, 0x33)
local HUNDIDO = px(0x45, 0x4A, 0x52)
-- El filo de luz de las cuencas va en un gris medio, no en el más claro de la
-- paleta: a casi blanco, la boca salía como una barra encendida que se comía
-- la ficha entera.
local LUZ    = px(0x9C, 0xA4, 0xAE)

local function lienzo()
  return Image(LIENZO, LIENZO, ColorMode.RGB)
end

-- El cuerpo va en perspectiva caballera, así que la tapa donde se posan los
-- sombreros no está encima del frente: está corrida `CABALLERA` píxeles arriba
-- y a la derecha. Los sombreros se dibujan centrados y se corren aquí, en un
-- solo sitio, en vez de meter el desplazamiento en las coordenadas de cada uno.
local CABALLERA = 3

local function correr(img, dx, dy)
  local salida = Image(LIENZO, LIENZO, ColorMode.RGB)
  for y = 0, LIENZO - 1 do
    for x = 0, LIENZO - 1 do
      local ax, ay = x - dx, y - dy
      if ax >= 0 and ay >= 0 and ax < LIENZO and ay < LIENZO then
        salida:drawPixel(x, y, img:getPixel(ax, ay))
      end
    end
  end
  return salida
end

local function guardar(img, carpeta, archivo)
  if carpeta == "sombreros" then
    img = correr(img, CABALLERA, -CABALLERA)
  end
  local sprite = Sprite(LIENZO, LIENZO, ColorMode.RGB)
  sprite.cels[1].image = img
  sprite.cels[1].position = Point(0, 0)
  sprite:saveAs(RAIZ .. "fuentes/aseprite/geo/" .. carpeta .. "_" .. archivo .. ".aseprite")
  sprite:saveCopyAs(RAIZ .. "fuentes/" .. carpeta .. "/geo/" .. archivo .. ".png")
  sprite:close()
  print("hecho " .. carpeta .. "/" .. archivo)
end

local function rect(img, x0, y0, x1, y1, c)
  for y = y0, y1 do for x = x0, x1 do img:drawPixel(x, y, c) end end
end

-- --- Caras ----------------------------------------------------------------
-- «Los ojos van hundidos en la piedra, muy separados, y la boca es una grieta
-- recta.» Lo hundido se hace con un hueco oscuro y un filo de luz DEBAJO: la
-- luz viene de arriba, así que el fondo de una cuenca se ilumina por abajo.

-- Ojos anchos y **muy separados**, que es lo que pide el brief, y sobre todo
-- grandes: el hueco de la cara mide 27x24 y el adulto grande 105 de ancho, así
-- que unos ojos pequeños se pierden dentro de la piedra. Ocupan el hueco casi
-- entero de lado a lado.
-- Los ojos van en y=58 y no más arriba para dejar libre la franja 49-55, que
-- es la única altura donde una cinta se apoya en las CINCO formas: los cinco
-- cuerpos tienen el filo de arriba entre y=44 y y=52.
local OJO_IZQ, OJO_DER, OJO_Y, OJO_W, OJO_H = 51, 67, 58, 10, 9
-- Más corta que antes: una grieta, no una raja de lado a lado.
local BOCA_X0, BOCA_X1, BOCA_Y = 57, 70, 71

local function cuenca(img, ox, oy, ancho, alto)
  rect(img, ox, oy, ox + ancho - 1, oy + alto - 1, HUNDIDO)
  rect(img, ox + 1, oy + 1, ox + ancho - 2, oy + alto - 2, NEGRO)
  -- El filo de luz va DEBAJO: la luz cae de arriba, así que el fondo de una
  -- cuenca se ilumina por abajo. Es lo que la hace parecer hundida y no pegada.
  for x = ox + 1, ox + ancho - 2 do img:drawPixel(x, oy + alto - 1, LUZ) end
end

local function boca(img, tipo)
  for x = BOCA_X0, BOCA_X1 do
    local dy = 0
    local extremo = (x < BOCA_X0 + 3 or x > BOCA_X1 - 3)
    if tipo == "sonrisa" and extremo then dy = -1 end
    if tipo == "pena" and extremo then dy = 1 end
    -- Una sola fila oscura y un filo de luz fino: es una grieta en la piedra.
    img:drawPixel(x, BOCA_Y + dy, NEGRO)
    img:drawPixel(x, BOCA_Y + dy + 1, LUZ)
  end
end

local function cara_feliz()
  local img = lienzo()
  -- ^ ^ : dos cuencas en pico, contentas. Trazo de dos píxeles para que se vea.
  for _, ox in ipairs({ OJO_IZQ, OJO_DER }) do
    for i = 0, 4 do
      for g = 0, 1 do
        img:drawPixel(ox + i, OJO_Y + 5 - i + g, NEGRO)
        img:drawPixel(ox + OJO_W - 1 - i, OJO_Y + 5 - i + g, NEGRO)
      end
      img:drawPixel(ox + i, OJO_Y + 7 - i, LUZ)
      img:drawPixel(ox + OJO_W - 1 - i, OJO_Y + 7 - i, LUZ)
    end
  end
  boca(img, "sonrisa")
  return img
end

local function cara_normal()
  local img = lienzo()
  -- o o : cuencas redondeadas, la mirada de siempre.
  cuenca(img, OJO_IZQ, OJO_Y, OJO_W, OJO_H)
  cuenca(img, OJO_DER, OJO_Y, OJO_W, OJO_H)
  boca(img, "recta")
  return img
end

local function cara_mal()
  local img = lienzo()
  -- x x : dos aspas, que en piedra son dos esquirlas.
  for _, ox in ipairs({ OJO_IZQ, OJO_DER }) do
    for i = 0, OJO_H - 2 do
      for g = 0, 1 do
        img:drawPixel(ox + i + g, OJO_Y + i, NEGRO)
        img:drawPixel(ox + OJO_W - 2 - i + g, OJO_Y + i, NEGRO)
      end
    end
    img:drawPixel(ox + OJO_W // 2 - 1, OJO_Y + OJO_H - 1, LUZ)
    img:drawPixel(ox + OJO_W // 2, OJO_Y + OJO_H - 1, LUZ)
  end
  boca(img, "pena")
  return img
end

-- --- Sombreros ------------------------------------------------------------
-- Todos se apoyan alrededor de y=POSA, que es donde pasa la coronilla de las
-- cinco formas. Ninguno baja del hueco de la cara.

local function aureola()
  local img = lienzo()
  local oro, oro2 = px(0xF2, 0xD5, 0x5C), px(0xC9, 0xA3, 0x2E)
  -- Una elipse hueca vista casi de canto. Antes era una raya recta y parecía
  -- un palo flotando; el anillo es lo que la hace leerse como aureola.
  local cx, cy, rx, ry = 64, 45, 19, 5
  for a = 0, 359 do
    local rad = math.rad(a)
    local x = math.floor(cx + rx * math.cos(rad) + 0.5)
    local y = math.floor(cy + ry * math.sin(rad) + 0.5)
    img:drawPixel(x, y, math.sin(rad) > 0 and oro2 or oro)
    img:drawPixel(x, y + 1, oro2)
  end
  return img
end

local function chistera()
  local img = lienzo()
  local negro, brillo = px(0x24, 0x24, 0x2A), px(0x3E, 0x3E, 0x48)
  local cinta = px(0x8E, 0x2B, 0x2B)
  rect(img, 44, POSA - 4, 84, POSA, negro)          -- ala
  rect(img, 53, POSA - 22, 75, POSA - 5, negro)     -- copa
  rect(img, 53, POSA - 10, 75, POSA - 6, cinta)     -- cinta
  for y = POSA - 21, POSA - 11 do img:drawPixel(55, y, brillo) end
  return img
end

local function cinta()
  local img = lienzo()
  -- Un **lazo de raso**, de los de pelo: dos bucles, el nudo en medio y dos
  -- cabos largos colgando, con la punta cortada en pico. Tres rojos para el
  -- raso —brillo, cuerpo y pliegue—, que es lo que le da el satinado.
  local raso  = px(0xC8, 0x2A, 0x3C)
  local raso2 = px(0x96, 0x1C, 0x2C)
  local luz   = px(0xE8, 0x5A, 0x66)

  -- Cargado a la derecha y algo alto: los bucles pasan por encima del ojo
  -- derecho —que va de x=67 a x=76, y de y=58 a y=66— pero por arriba, y los
  -- dos cabos cuelgan ya fuera de esa franja.
  local nx, ny = 79, FRENTE - 3

  -- Los dos bucles. Cada uno es un triángulo redondeado que sale del nudo, con
  -- el filo de arriba iluminado y el pliegue de abajo en el rojo hondo.
  for lado = 0, 1 do
    local dir = (lado == 0) and -1 or 1
    for i = 1, 13 do
      local alto = math.floor(7 * math.sin(i / 13 * math.pi)) + 1
      for g = -alto, alto do
        local x, y = nx + dir * i, ny + g
        if g < -alto + 2 then img:drawPixel(x, y, luz)
        elseif g > alto - 2 then img:drawPixel(x, y, raso2)
        else img:drawPixel(x, y, raso) end
      end
      -- El hueco del bucle: la tela da la vuelta y por dentro se ve el fondo.
      if i > 4 and i < 11 then
        local hueco = math.floor(3 * math.sin((i - 4) / 7 * math.pi))
        for g = -hueco, hueco do
          img:drawPixel(nx + dir * i, ny + g, 0)
        end
      end
    end
  end

  -- El nudo, que es lo que ata los dos bucles y los cabos.
  rect(img, nx - 3, ny - 4, nx + 3, ny + 4, raso)
  rect(img, nx - 3, ny - 4, nx + 3, ny - 3, luz)
  rect(img, nx - 3, ny + 3, nx + 3, ny + 4, raso2)

  -- Los dos cabos, largos y algo separados, con la punta en pico.
  for cabo = 0, 1 do
    local dx = (cabo == 0) and -3 or 3
    local largo = (cabo == 0) and 26 or 20
    for i = 0, largo do
      local x = nx + dx + math.floor(i * (cabo == 0 and -0.16 or 0.20))
      local y = ny + 5 + i
      local ancho = 3
      -- La punta se corta en pico, como la tela al bies.
      if i > largo - 4 then ancho = 3 - (i - (largo - 4)) end
      for g = -ancho, ancho do
        if g <= -ancho + 1 then img:drawPixel(x + g, y, luz)
        elseif g >= ancho - 1 then img:drawPixel(x + g, y, raso2)
        else img:drawPixel(x + g, y, raso) end
      end
    end
  end
  return img
end


local function corona()
  local img = lienzo()
  local oro, oro2 = px(0xE9, 0xBC, 0x4E), px(0xB4, 0x8A, 0x28)
  local joya = px(0xC0, 0x39, 0x39)
  rect(img, 48, POSA - 6, 80, POSA, oro)
  for x = 48, 80 do img:drawPixel(x, POSA, oro2) end
  for i, x in ipairs({ 50, 58, 66, 74 }) do
    local alto = (i % 2 == 0) and 10 or 14
    rect(img, x, POSA - 6 - alto, x + 4, POSA - 7, oro)
    img:drawPixel(x + 2, POSA - 7 - alto, joya)
  end
  return img
end

local function cuernos()
  local img = lienzo()
  local hueso, sombra = px(0xDC, 0xD3, 0xAE), px(0xA9, 0x9F, 0x7C)
  for lado = 0, 1 do
    local dir = (lado == 0) and -1 or 1
    local x = (lado == 0) and 56 or 72
    for i = 0, 13 do
      local ancho = math.max(1, 4 - math.floor(i / 4))
      local cx = x + dir * math.floor(i * 0.9)
      for g = 0, ancho - 1 do
        img:drawPixel(cx + dir * g, POSA - 2 - i, i < 9 and hueso or sombra)
      end
    end
  end
  return img
end

local function laurel()
  local img = lienzo()
  local verde, verde2 = px(0x6C, 0x93, 0x40), px(0x4E, 0x6E, 0x2A)
  -- Dos ramas que abrazan la coronilla, con hojas de verdad. Las de antes eran
  -- cuatro píxeles sueltos y no se leían como nada.
  for lado = 0, 1 do
    local dir = (lado == 0) and -1 or 1
    for i = 0, 11 do
      local x = 64 + dir * (4 + i * 2)
      local y = POSA + 1 - math.floor(i * i * 0.09)
      -- El tallo
      img:drawPixel(x, y, verde2)
      img:drawPixel(x, y + 1, verde2)
      -- Una hoja cada dos pasos, hacia afuera
      if i % 2 == 0 then
        for h = 0, 3 do
          local ancho = (h == 0 or h == 3) and 1 or 2
          for g = 0, ancho - 1 do
            img:drawPixel(x + dir * h, y - 2 - g, verde)
          end
        end
        img:drawPixel(x + dir * 2, y - 3, verde2)
      end
    end
  end
  return img
end

guardar(cara_feliz(),  "caras", "face_1")
guardar(cara_normal(), "caras", "face_2")
guardar(cara_mal(),    "caras", "face_3")

guardar(aureola(),  "sombreros", "aureola")
guardar(chistera(), "sombreros", "chistera")
guardar(cinta(),    "sombreros", "cinta")
guardar(corona(),   "sombreros", "corona")
guardar(cuernos(),  "sombreros", "cuernos")
guardar(laurel(),   "sombreros", "laurel")
