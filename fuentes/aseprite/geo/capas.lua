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

local function guardar(img, carpeta, archivo)
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
  -- Una **cinta de tela con una rosa**, no una banda de karate. La cinta es
  -- estrecha y de raso; el peso está en la flor, que va a un lado.
  local raso, raso2 = px(0xD8, 0x62, 0x8E), px(0xA8, 0x3C, 0x66)
  local petalo = px(0xD8, 0x3C, 0x50)
  local petalo2 = px(0xA8, 0x24, 0x38)
  local corazon = px(0xF0, 0x8A, 0x9A)
  local hoja, hoja2 = px(0x4E, 0x8E, 0x46), px(0x36, 0x66, 0x30)

  -- La cinta: tres píxeles de tela, con el brillo del raso arriba y el pliegue
  -- oscuro abajo. Con dos parecía un hilo, y la flor encima un chupachups.
  for x = 47, 81 do
    img:drawPixel(x, FRENTE, raso)
    img:drawPixel(x, FRENTE + 1, raso)
    img:drawPixel(x, FRENTE + 2, raso2)
  end

  -- Los dos cabos que cuelgan por el lado izquierdo, uno más largo, con la
  -- punta en pico como la tela cortada al bies.
  for i = 0, 8 do
    local x = 49 - math.floor(i * 0.45)
    img:drawPixel(x, FRENTE + 3 + i, raso)
    img:drawPixel(x + 1, FRENTE + 3 + i, raso2)
  end
  for i = 0, 5 do
    local x = 53 + math.floor(i * 0.5)
    img:drawPixel(x, FRENTE + 3 + i, raso)
    img:drawPixel(x + 1, FRENTE + 3 + i, raso2)
  end

  -- La rosa, encima de la cinta y a la derecha. Se dibuja como una espiral de
  -- pétalos que se cierra: es el remolino, y no lo redondo, lo que hace que se
  -- lea rosa en vez de bola roja.
  local rx, ry = 71, FRENTE - 2
  for dy = -5, 5 do
    for dx = -5, 5 do
      local d = dx * dx + dy * dy
      if d <= 27 then
        img:drawPixel(rx + dx, ry + dy, (d > 16) and petalo2 or petalo)
      end
    end
  end
  -- La espiral: tres arcos que giran hacia dentro.
  local espiral = {
    { -3, -1 }, { -2, -2 }, { -1, -3 }, { 1, -3 }, { 2, -2 }, { 3, -1 },
    { 3, 1 }, { 2, 2 }, { 0, 3 }, { -2, 2 },
  }
  for i, p in ipairs(espiral) do
    img:drawPixel(rx + p[1], ry + p[2], (i % 2 == 0) and petalo2 or corazon)
  end
  img:drawPixel(rx, ry, corazon)
  img:drawPixel(rx - 1, ry - 1, corazon)
  img:drawPixel(rx + 1, ry, petalo2)

  -- Dos hojas asomando por debajo de la flor, hacia los lados.
  for i = 0, 4 do
    img:drawPixel(rx - 6 - i, ry + 4 + math.floor(i / 2), hoja)
    img:drawPixel(rx - 6 - i, ry + 5 + math.floor(i / 2), hoja2)
    img:drawPixel(rx + 6 + i, ry + 4 + math.floor(i / 2), hoja)
    img:drawPixel(rx + 6 + i, ry + 5 + math.floor(i / 2), hoja2)
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
