-- Las quince caras de Geo: tres ánimos por cada una de las cinco formas.
--
-- Van por forma y no por especie porque los cinco cuerpos son dibujos
-- distintos, no el mismo agrandado: la cría es una bola, el niño y el
-- adolescente son cubos en tres cuartos y los dos adultos son pedruscos con
-- patas. Los ojos no caen en el mismo sitio en ninguno, y una sola cara para
-- las cinco obligaría a dejarles a todas el hueco donde le conviene a la peor.
--
-- Los cuerpos vienen pintados, con contorno negro y sombreado suave, así que
-- las cuencas llevan su propio contorno negro para no parecer pegatinas.
--
-- **Y van en perspectiva caballera, no de frente.** Los cuerpos están en tres
-- cuartos, con su cara superior a la vista y la profundidad subiendo a 45
-- grados hacia la derecha. Una cara dibujada con los ejes del lienzo —cuencas
-- rectas, los dos ojos a la misma altura— se pega encima como una calcomanía y
-- delata que no pertenece al volumen. Aquí las cuencas y la boca se inclinan
-- sobre ese mismo eje (SESGO) y el ojo de la derecha, que se va hacia el fondo,
-- sube (SUBIDA) y se estrecha (FUGA).
--
--   Aseprite.exe --batch --script fuentes/aseprite/geo/caras.lua

local LIENZO = 256
local RAIZ = "/home/felipe/tamagotchi-bot/"

local function px(r, g, b) return app.pixelColor.rgba(r, g, b, 255) end

-- Cuánto se inclina cada rasgo sobre el eje de 45 grados. A 1.0 sería la
-- caballera pura, pero sobre un rasgo de 32 px de alto eso son 32 px de vuelco
-- y la cara sale caída; 0.45 la posa sobre el plano sin deformarla.
local SESGO = 0.45
-- El ojo que se va hacia el fondo sube y se encoge un poco de ancho. No es
-- escorzo de verdad —la caballera no acorta— pero es lo que hace que los dos
-- ojos se lean sobre la misma superficie y no flotando cada uno por su lado.
local SUBIDA = 9
local FUGA = 0.86

local BORDE  = px(0x0D, 0x0F, 0x12)   -- el negro del contorno de los cuerpos
local HUECO  = px(0x1E, 0x22, 0x28)   -- el fondo de la cuenca
local FONDO  = px(0x4A, 0x50, 0x58)   -- el filo iluminado, abajo de la cuenca

-- Dónde va la cara en cada forma. Medido sobre los cuerpos: el centro de la
-- mirada, el tamaño del ojo, la separación entre los dos y la altura de la
-- boca. El adolescente la lleva más abajo porque tiene liquen arriba a la
-- derecha, y el niño algo más arriba porque su cubo es más alto de frente.
local FORMAS = {
  { archivo = "cria",          cx = 126, oy = 102, ow = 34, oh = 32, hueco = 44,
    boca_y = 154, boca_w = 44 },
  { archivo = "niño",          cx = 145, oy = 104, ow = 34, oh = 32, hueco = 46,
    boca_y = 156, boca_w = 44 },
  { archivo = "adolecente",    cx = 132, oy = 120, ow = 34, oh = 32, hueco = 46,
    boca_y = 172, boca_w = 44 },
  { archivo = "adulto",        cx = 125, oy = 100, ow = 34, oh = 32, hueco = 46,
    boca_y = 152, boca_w = 44 },
  { archivo = "adulto_grande", cx = 124, oy = 112, ow = 34, oh = 32, hueco = 46,
    boca_y = 164, boca_w = 44 },
}

local function lienzo() return Image(LIENZO, LIENZO, ColorMode.RGB) end

-- Rectángulo de esquinas comidas: una cuenca picada en la piedra, ni un óvalo
-- perfecto ni un cuadrado duro.
local function cuenca(img, x0, y0, w, h)
  local rx, ry = w / 2, h / 2
  local cx, cy = x0 + rx - 0.5, y0 + ry - 0.5
  for y = y0 - 2, y0 + h + 1 do
    for x = x0 - 8, x0 + w + 8 do
      -- Se evalúa la forma en el sistema del PLANO, no en el del lienzo: se
      -- deshace la inclinación antes de preguntar si el punto cae dentro.
      local xs = x + (y - cy) * SESGO
      local u = math.abs((xs - cx) / rx)
      local v = math.abs((y - cy) / ry)
      local d = u ^ 2.6 + v ^ 2.6
      if d <= 1.0 then
        -- El filo de luz va abajo: la luz cae de arriba, así que el fondo de
        -- una cuenca se ilumina por debajo. Es lo que la hace parecer hundida.
        img:drawPixel(x, y, (y > cy + ry * 0.55) and FONDO or HUECO)
      elseif d <= 1.35 then
        img:drawPixel(x, y, BORDE)
      end
    end
  end
end

local function aspa(img, x0, y0, w, h)
  local grosor = 5
  for i = 0, h - 1 do
    local t = i / (h - 1)
    local vuelco = math.floor((h / 2 - i) * SESGO)
    for g = 0, grosor - 1 do
      local a = math.floor(x0 + t * (w - grosor)) + g - vuelco
      local b = math.floor(x0 + (1 - t) * (w - grosor)) + g - vuelco
      img:drawPixel(a, y0 + i, BORDE)
      img:drawPixel(b, y0 + i, BORDE)
    end
  end
end

local function arco(img, x0, y0, w, h)
  -- Se recorre el trazo y se **une cada punto con el anterior**. Pintando
  -- columna a columna con la inclinación puesta, la x salta más de un píxel por
  -- fila y el arco sale a rayas, como un peine.
  local grosor = 6
  local px_ant, py_ant
  for i = 0, w - 1 do
    local t = i / (w - 1)
    local y = y0 + math.floor(h * math.abs(t - 0.5) * 2)
    local x = x0 + i - math.floor((h / 2 - (y - y0)) * SESGO)
    if px_ant then
      local pasos = math.max(math.abs(x - px_ant), math.abs(y - py_ant))
      for k = 1, pasos do
        local ax = math.floor(px_ant + (x - px_ant) * k / pasos + 0.5)
        local ay = math.floor(py_ant + (y - py_ant) * k / pasos + 0.5)
        for g = 0, grosor - 1 do img:drawPixel(ax, ay + g, BORDE) end
        img:drawPixel(ax, ay + grosor, FONDO)
      end
    end
    for g = 0, grosor - 1 do img:drawPixel(x, y + g, BORDE) end
    img:drawPixel(x, y + grosor, FONDO)
    px_ant, py_ant = x, y
  end
end

local function boca(img, f, tipo)
  -- Afinada en las puntas y sin filo de luz de lado a lado: con grosor
  -- constante y una raya clara debajo salía una barra de buzón, no una boca.
  local x0 = f.cx - f.boca_w // 2
  for i = 0, f.boca_w - 1 do
    local t = i / (f.boca_w - 1)
    local extremo = math.abs(t - 0.5) * 2
    local grosor = math.max(2, 4 - math.floor(extremo * 3))
    local curva = math.floor(7 * extremo ^ 1.7)
    -- La boca se va con el plano: el extremo derecho, que se aleja, sube.
    local dy = -math.floor((t - 0.5) * f.boca_w * SESGO * 0.5)
    if tipo == "sonrisa" then dy = dy - curva
    elseif tipo == "pena" then dy = dy + curva end
    for g = 0, grosor - 1 do
      img:drawPixel(x0 + i, f.boca_y + dy + g, BORDE)
    end
    if extremo < 0.75 then
      img:drawPixel(x0 + i, f.boca_y + dy + grosor, FONDO)
    end
  end
end

local function guardar(img, forma, archivo)
  local sprite = Sprite(LIENZO, LIENZO, ColorMode.RGB)
  sprite.cels[1].image = img
  sprite.cels[1].position = Point(0, 0)
  sprite:saveAs(RAIZ .. "fuentes/aseprite/geo/cara_" .. forma .. "_" .. archivo .. ".aseprite")
  sprite:saveCopyAs(RAIZ .. "fuentes/caras/geo/" .. forma .. "/" .. archivo .. ".png")
  sprite:close()
  print("hecho caras/geo/" .. forma .. "/" .. archivo)
end

for _, f in ipairs(FORMAS) do
  local izq = f.cx - f.hueco // 2 - f.ow
  local der = f.cx + f.hueco // 2
  local ow2 = math.floor(f.ow * FUGA)      -- el ojo del fondo, más estrecho
  local oy2 = f.oy - SUBIDA                -- y más alto

  -- feliz: ^ ^
  local img = lienzo()
  arco(img, izq, f.oy + 6, f.ow, 14)
  arco(img, der, oy2 + 6, ow2, 14)
  boca(img, f, "sonrisa")
  guardar(img, f.archivo, "face_1")

  -- normal: o o
  img = lienzo()
  cuenca(img, izq, f.oy, f.ow, f.oh)
  cuenca(img, der, oy2, ow2, f.oh)
  boca(img, f, "recta")
  guardar(img, f.archivo, "face_2")

  -- mal: x x
  img = lienzo()
  aspa(img, izq, f.oy, f.ow, f.oh)
  aspa(img, der, oy2, ow2, f.oh)
  boca(img, f, "pena")
  guardar(img, f.archivo, "face_3")
end
