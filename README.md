# Gachamones BOT

Un tamagotchi que vive en un canal de Discord. Sale de un huevo, es uno de 10
gachamones al azar, se cuida con los botones bajo el mensaje y compite contra los
de otras personas en carreras y peleas de sumo. Todo el arte es ASCII dentro de
bloques de código: ni una sola imagen.

```
## 🐥 Pelusa
-# Pollito · adulta · nivel 3 · 4V-1D · 2 días de vida
╭──────────────────────────╮
│             _            │
│            (,)           │
│           (^v^)          │
│          <(   )>         │
│            ^ ^           │
├──────────────────────────┤
│ COMIDA  ███████████░  88 │
│ ANIMO   ███████████░  92 │
│ ASEO    ████████░░░░  70 │
├──────────────────────────┤
│ FUE 11   VEL 21   SAL 11 │
╰──────────────────────────╯
[🍖 Alimentar] [🎮 Jugar] [🏋️ Entrenar] [🧼 Limpiar] [🔄 Actualizar]
```

## Puesta en marcha

### 1. Crear la aplicación en Discord

1. Entra en <https://discord.com/developers/applications> → **New Application**.
2. Pestaña **Bot** → **Reset Token** → copia el token.
3. **No hace falta activar ningún intent privilegiado.** El bot funciona sólo
   con slash commands y botones, así que *Message Content* puede quedar apagado.
4. Pestaña **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Permisos: *Send Messages*, *Embed Links*, *Read Message History*
   - Abre la URL que genera e invita el bot a tu servidor.

   No necesita *Gestionar mensajes*: para apagar los botones de una pantalla
   vieja edita sus propios mensajes, y eso siempre está permitido.
5. Activa **Ajustes → Avanzado → Modo desarrollador**, haz clic derecho sobre el
   canal donde quieras que viva y elige **Copiar ID**.

### 2. Configurar

```bash
cp .env.ejemplo .env
$EDITOR .env          # DISCORD_TOKEN, CANAL_ID y (recomendado) GUILD_ID
```

Con `GUILD_ID` los comandos aparecen al instante. Sin él, Discord tarda hasta
una hora en propagarlos por todos los servidores.

**Varios servidores.** `GUILD_ID` también admite una lista separada por comas.
Cada servidor lleva sus propias mascotas y su propio ranking: la misma persona
puede tener una criatura distinta en cada uno. Acuérdate de añadir el canal de
cada servidor a `CANAL_ID`. Si uno de los servidores da error al registrar los
comandos (por ejemplo porque el bot no está invitado ahí), el bot lo avisa en el
registro y sigue funcionando en los demás.

**Varios canales.** `CANAL_ID` admite una lista separada por comas:

```
CANAL_ID=123456789012345678,987654321098765432
```

Los comandos funcionan en todos ellos, y cada persona sigue teniendo **un solo
plantel por servidor** — los canales son salas distintas para las mismas
mascotas, no mascotas distintas. Cada criatura recuerda el canal donde se la
atendió por última vez, y ahí es donde le llegan los avisos de hambre y el
anuncio de su muerte; si cambias de canal, los avisos te siguen. El primero de
la lista es el principal: se usa como respaldo para criaturas sin canal
guardado o cuyo canal ya no existe.

### 3. Arrancar en local

```bash
python3.12 -m venv venv              # Python 3.14 también está soportado
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python bot.py
```

`requirements.txt` contiene sólo las dependencias directas de producción con
versiones exactas; `requirements-dev.txt` añade pytest para desarrollo y CI. Las
dependencias transitivas siguen bajo el resolvedor de pip: este primer paso hace
reproducibles las dependencias directas, pero no es un lock transitivo con hashes.

### 4. Desplegar en la Raspberry

```bash
PI=usuario@ip-de-tu-pi                        # o edita el valor por defecto en deploy.sh
scp .env $PI:/home/usuario/tamagotchi-bot/.env   # sólo la primera vez
PI=$PI ./deploy.sh
```

`deploy.sh` sincroniza el código, prepara el venv, instala el servicio systemd y
lo reinicia. Admite `PI` y `DEST` como variables de entorno, así que no hace falta
tocar el script para apuntar a otra máquina o a otra ruta. Para ver el registro:

```bash
ssh $PI 'journalctl -u tamagotchi -f'
```

## Comandos

| Comando | Qué hace |
|---|---|
| `/huevo` | Te da un huevo, sólo si no tienes ningún gachamon. Al romperlo ves cuál ha salido y luego lo bautizas. |
| `/mascota` | Publica tu pantalla con los botones. |
| `/mascota @alguien` | Enseña la criatura de otra persona (sin botones). |
| `/carrera @alguien` | Reto de velocidad + 1d20. Admite hasta tres invitados más (cinco corriendo), y con tres o más termina en podio. |
| `/sumo @alguien` | Reto de fuerza + 1d20. Con tres invitados es un torneo de cuatro: dos semifinales sorteadas y una final. |
| `/aventura` | Sal al campo con tu activo: dos pruebas, y quizá un objeto o un gachamon salvaje. |
| `/jardin` | Todas las criaturas activas del servidor juntas, e interactuando. |
| `/ranking` | Criaturas vivas con más victorias. |
| `/cementerio` | Las que ya no están. |
| `/ayuda` | Resumen de las reglas. |
| `@Gachamon <lo que sea>` | Hablar con tu criatura. Te contesta en su propio carácter. |

## Reglas

**El plantel.** Hasta **3 gachamones** por persona y servidor, con **uno
activo**: el que recibe los botones y los comandos. Los demás esperan en la
**incubadora**, y ahí **no les pasa el tiempo** — ni hambre, ni ánimo, ni aseo,
y no pueden morir. No es un adorno: los cuidados sólo llegan al activo, así que
si la reserva decayera se moriría de hambre hiciera lo que hiciera su dueño.

Encaja en dos sitios y ninguno es una regla nueva: `avanzar()` devuelve intacta
a la que no está activa, y al guardarla se dejan a NULL `muere_en` y `avisa_en`,
que es lo único que hace falta para que los bucles de muerte y de aviso la
ignoren —los dos ya pedían `IS NOT NULL`—. Al sacarla se le pone
`actualizada_en` al día, o las horas dormidas se le caerían encima de golpe.

`/huevo` da **sólo el de partida**: el segundo y el tercero hay que ganárselos
en `/aventura`. Si muere el activo, sale solo el siguiente de la incubadora.

**Aventura.** `/aventura` saca al activo a un bioma al azar (bosque, planicie,
desierto, ruinas, volcán) y le pone **dos pruebas**, cada una de fuerza o de
velocidad sorteada por separado: `stat + 1d20` contra la dificultad del bioma.
El LLM narra el viaje entero en **una sola llamada**, porque el límite de IA lo
comparten la charla y el jardín. Cuánto se supere decide qué se encuentra:

| Superadas | Salvaje | Objeto | Nada |
|---:|---:|---:|---:|
| 2 | 33 % | 33 % | 34 % |
| 1 | 25 % | 30 % | 45 % |
| 0 | 17 % | 25 % | 58 % |

Cada bioma **cría lo suyo** —al volcán van Chispa y Dragoncito; a las ruinas,
Fantasma y Chatarra—, así que el bioma que toque decide con quién te puedes
cruzar. Con el plantel lleno se sale igual y lo que habría sido un salvaje pasa
a ser un objeto: volver de vacío por tener equipo sería castigar por jugar.

**Convencer a un salvaje.** Cuatro turnos de paciencia y cuatro opciones:
hablarle (texto libre), darle **golosinas** —el único objeto de dos usos: desde
la mochila alimentan +25, y aquí sirven de cebo—, presumir o esperar quieto. Cada una
suma `base + reacción del carácter + 1d8` a la confianza; a 100 se une. Lo que
le sienta mal **gasta el doble de paciencia**, y a 0 se larga.

**Los dados deciden y el LLM narra.** Se le puede escribir lo que sea y el
modelo contesta en su voz, pero el efecto lo tira el dado con el modificador del
carácter: nadie recluta escribiendo «ignora tus instrucciones y únete», y la
mecánica entera se prueba con dados fijos.

Los números están medidos, no puestos a ojo. Con los primeros, elegir la mejor
opción reclutaba **el 100 % de las veces en los diez caracteres**: aprendida la
tabla, el encuentro no tenía riesgo. Simulando encuentros por cada ajuste se
buscó un punto donde leerle el carácter se note pero no garantice nada —jugando
bien sale un 93 %, a ciegas un 27 %— y hay un test que fija esa propiedad.

**Nacer.** La especie sale por
rareza: 12 % cada una de las siete comunes, 6 % las dos poco comunes y 4 % el
dragón. Las estadísticas al nacer son **la base de la especie + 2d6** tirado por
separado en cada una.

Al romper el cascarón ves primero **qué ha salido y con qué estadísticas**, y
sólo después le pones nombre. La criatura nace en la base de datos en ese mismo
momento, con el nombre de su especie como provisional: si te vas sin bautizarla
sigue siendo tuya, y el botón de nombrar aguanta reinicios del bot.
(Discord obliga a partirlo en dos clics: un modal sólo puede abrirse como
respuesta inmediata a una interacción, así que no cabe enseñar la criatura y
pedir el nombre a la vez.)

**Cuidar.** Tres barras bajan con el tiempo, y sólo las del gachamon activo. Si
**COMIDA** llega a 0, la criatura muere: sale el siguiente de la incubadora si
lo hay, y si no, a empezar con otro huevo. Una criatura típica aguanta unas
73 h; la salud alarga ese margen (un Brote sano llega a ~86 h, una Chispa frágil
baja a ~62 h). El ánimo y el aseo no matan: el aseo bajo amarga el ánimo, y el
ánimo bajo penaliza en las competencias.

**Aviso.** Cuando la comida baja del 10 %, el bot menciona al dueño en el canal
y publica la pantalla con los botones para poder alimentarla desde ahí mismo.
Quedan unas 7 h de margen. El aviso salta **una sola vez** por bajada y se
rearma al alimentarla, así que ni machaca el canal ni se pierde si la criatura
vuelve a pasar hambre días después.

**Crecer y evolucionar.** Cada nivel es una etapa, y **el dibujo cambia**:
cría → niño → adolescente → adulto → adulto grande. La experiencia sale tanto
de competir (+10 al ganar, +4 al perder) como de cuidar (+1 alimentar,
+2 jugar, +3 entrenar), para que quien no quiera pelear también vea crecer a su
criatura. Competir sigue siendo lo más rentable por acción.

La curva está calibrada sobre unos 27 XP diarios, que es lo que saca alguien
que atiende a su criatura un par de veces al día: **el primer salto cae en un
día y llegar a la forma final cuesta cerca de un mes** (25, 100, 250 y 525 XP).
Cada evolución reparte 2, 3, 4 y 5 puntos de estadística según el perfil de la
especie; como parte va a salud, la criatura evolucionada aguanta más sin comer.

`estadística = base + √entrenamiento + bonus de nivel`. La raíz cuadrada hace
que machacar el botón no compense: el segundo punto cuesta 4 sesiones, el
tercero 9, el décimo 100.

**El jardín.** `/jardin` dibuja a todas las criaturas vivas del servidor juntas
con el arte de su etapa, y cuenta qué están haciendo dos de ellas según sus
personalidades y su estado. Consume del mismo límite horario de IA que la
charla, más dos minutos de enfriamiento por servidor.

**Competir.** Tres tramos, cada uno `estadística + 1d20`, gana quien sume más.
El dado mueve 19 puntos y las diferencias entre criaturas cuidadas rondan los
5-10, así que nadie se despega del resto por muchas victorias que acumule. Lo
que más puede inclinar una pelea es una **poción**: la mayor da hasta +12, más
que el estado (de −5 a +2) y comparable al propio dado. Por eso sólo puede haber
una activa por estadística; si se acumularan, las carreras las decidiría quién
tiene más objetos y no la tirada.

Una **carrera** admite de dos a cinco corredores, todos a la vez. Con tres o
más acaba en un **podio dibujado**: los tres primeros subidos a su cajón con la
cara que tenían al competir, y debajo la clasificación completa. Con dos no hay
podio, sino la línea de siempre: hay quien gana y quien pierde.

El **sumo** es de dos o de cuatro, nunca de tres: es un forcejeo y el dohyō
tiene dos lados, así que con cuatro se juega a **torneo** —dos semifinales
sorteadas y una final— y el resumen es el **cuadro**, con quien pasa en el color
de su especie y quien cae en gris.

En los dos casos sólo el primero suma victoria y se lleva los +10; el resto, +4.
Un torneo cuenta como **una sola competencia** para el coste y la experiencia,
aunque los finalistas peleen dos veces. Si dos empatan se tira otro tramo para
todos hasta deshacerlo.

Al terminar, la pantalla sólo se republica a quien **suba de nivel o
evolucione**. Al resto le queda la de antes con los números viejos, pero con los
botones vivos: actúan sobre la base de datos, no sobre lo que se ve, y la
pantalla se pone al día en cuanto se pulsa cualquiera.

**Consumibles.** Los botones 🎒 **Mochila** y 🛒 **Tienda** abren menús que sólo
ve quien los pulsa. Cada persona empieza con **50 asciicoins y 50 asciigems**.
La tienda cobra sólo asciicoins; los asciigems quedan visibles en reserva, sin
conversión ni gasto. El monedero es **suyo, no de la criatura**, así que lo
comprado sobrevive a la muerte de una mascota. Hay
pociones de fuerza y de velocidad de 1d4 a 1d12 que duran cinco minutos, una que
llena el hambre saltándose el empacho, y dos que borran un enfriamiento.

Los cinco minutos no son un capricho: quien acepta un reto tiene 120 segundos
para pulsar, y la estadística se lee **al resolver** la pelea, no al retar. Con
un minuto la poción habría caducado en la mayoría de las carreras y no habría
forma de saber por qué no hizo nada. El dado de la poción se tira **al beberla**,
para que el mensaje pueda decir cuánto ha tocado.

**Economía.** Un cuidado válido da +1 asciicoin (hasta 12 al día UTC), cada
competencia resuelta da +4 a cada participante y +2 extra a quien gana (hasta
tres competencias premiadas al día UTC), y evolucionar da +10 una vez al día
UTC. Los topes pertenecen a la persona y al servidor: cambiar de activo,
reclutar o ascender desde la incubadora no los reinicia. Agotar un tope no
detiene el juego, la experiencia ni la evolución; sólo deja el premio en cero.

Las compras y los premios se confirman en SQLite antes de enviar nada a Discord.
El informe local agregado no expone IDs:

```bash
./venv/bin/python economia_reporte.py --desde 2026-01-01 --hasta 2026-01-31
# Añade --json para salida estructurada y --db otra/ruta.db si hace falta.
```

**Quién le ha tocado ser.** Además de la especie se sortean al nacer el
**género** (♂️ o ♀️, mitad y mitad) y la **personalidad**, una de diez: alegre,
sereno, miedoso, valiente, gruñón, curioso, cariñoso, orgulloso, perezoso o
travieso. Los dos salen en la ficha y no cambian nunca. **No tocan ninguna
estadística**: sólo cómo habla y cómo se porta en el jardín, así que ninguna
personalidad es mejor que otra. La personalidad se suma a la voz de la especie
sin sustituirla: un Pedrusco travieso sigue siendo lento y de pocas palabras,
pero con retranca.

Todo lo que una criatura dice de sí misma lleva marcas de concordancia
`{masculino/femenino}` que resuelve `especies.concordar()`. Los prompts se montan
con las marcas puestas y se resuelven de una vez al final, así ningún texto nuevo
se puede olvidar de concordar; un test comprueba que no sobrevive ninguna marca.

**Hablar.** Menciona al bot y tu criatura contesta con su propio carácter: el
Pollito mete «pío» en todas las frases, Pedrusco responde con una palabra, y si
intentas acariciar a Chispa te quema los dedos. El tono cambia según cómo la
tengas — una criatura hambrienta contesta de mal humor — y se acuerda de los
últimos ocho intercambios. Hasta 20 mensajes por hora y por persona. Hablar no
gasta comida ni da experiencia: queda fuera del equilibrio del juego.

## Cómo está montado

La lógica del juego vive en módulos **puros** que no importan `discord` y se
testean sin conexión. Los cogs son capas finas encima.

| Fichero | Qué hace |
|---|---|
| `especies.py` | Las 10 especies, su arte ASCII por etapa, estadísticas y rarezas. |
| `jardin.py` | El reparto de varias criaturas en una sola escena. |
| `personalidad.py` | La voz de cada especie, los diez caracteres y cómo se le explica todo al modelo. |
| `ia.py` | Cliente de NVIDIA cloud. Async, con transporte inyectable. |
| `simulacion.py` | Decaimiento, muerte, acciones de cuidado, estadísticas y niveles. |
| `competir.py` | Resolución y narración de carreras y sumo. |
| `objetos.py` | El catálogo de consumibles: precios, dados y qué hace cada uno. |
| `pantalla.py` | Dibuja la pantalla como texto de Discord. |
| `db.py` | SQLite. |
| `economia.py` | Monederos, topes UTC y operaciones económicas atómicas. |
| `economia_reporte.py` | Informe local agregado y reconciliación histórica. |
| `vistas.py` | Los botones y el ciclo publicar-nueva/congelar-la-vieja. |
| `equipo.py` | El menú para cambiar de gachamon activo. |
| `aventura.py` | Biomas, pruebas, hallazgos y las reacciones de un salvaje. |
| `tienda.py` | Los menús de mochila y tienda, y el uso de un objeto. |
| `cogs/` | Los slash commands. |

**Cómo se guarda el arte.** Cinco etapas por diez especies, con tres estados de
ánimo cada una, serían 150 dibujos. Pero casi todos se diferencian **sólo en la
cara**: el mismo cuerpo de Pollito con `^v^`, `o.o` o `T_T`. Así que cada etapa
es una plantilla con un hueco `{cara}` y cada especie declara sus tres caras:
**50 dibujos y los ánimos salen gratis**. Donde el ánimo cambia más que la cara
—al Brote se le caen las hojas, la llama de Chispa mengua— se declara el dibujo
completo en `excepciones`, que gana a la plantilla. Las tres caras de una
especie tienen que medir lo mismo, o sustituir una por otra descuadraría el
dibujo; hay un test que lo comprueba.

Dos decisiones más que explican el resto del diseño:

- **El decaimiento es perezoso.** No hay ningún bucle tocando cada mascota cada
  minuto: se guarda cuándo se actualizó y el valor se calcula al leer. Como el
  hambre baja de forma estrictamente lineal, la hora de la muerte se despeja con
  una fórmula cerrada y se guarda en `muere_en`; el bucle que mata criaturas es
  entonces un `WHERE muere_en <= ahora`. Por eso la suciedad castiga al ánimo y
  no al hambre: si acelerase el hambre, dos barras cayendo a la vez se
  acoplarían y la muerte dejaría de ser predecible.
- **Los botones son persistentes.** `timeout=None` y `custom_id` fijos,
  registrados con `bot.add_view()` al arrancar. Siguen respondiendo tras un
  reinicio sin necesidad de recordar en qué mensajes estaban.
- **La charla va por menciones, no por chat libre.** Discord entrega el
  contenido de los mensajes que mencionan al bot aunque el intent privilegiado
  *Message Content* esté apagado. Así el bot no lee todo lo que se escribe en el
  canal y no hay que pedir permisos extra en el portal.
- **La criatura nunca se queda muda.** Cada especie tiene frases escritas a
  mano que se usan si la API falla. Esas frases no entran en la memoria: si
  entraran, el modelo aprendería a repetirlas como si fueran suyas.
- **Los fallos de la API se tratan distinto según si tienen arreglo.** Un error
  permanente (un 400 de modelo degradado, un 404) no se reintenta: se pasa al
  siguiente modelo de `MODELO_IA` al instante. La distinción no es teórica —
  NVIDIA marcó `deepseek-v4-flash` como DEGRADED a las pocas horas de ponerlo
  en producción, y reintentar ese 400 con espera convertía un fallo inmediato en
  65 segundos de «escribiendo…»: el bot parecía muerto.
- **Se prueban todos los modelos por turnos, no uno hasta agotarlo.** Tres rondas
  recorriendo la lista entera, con 30 s de tope por intento y 90 s para todo el
  proceso, que es lo que como mucho dura el «escribiendo…» antes de la frase de
  respaldo. La versión anterior gastaba los tres reintentos en el primer modelo y
  se quedaba sin presupuesto para los demás: cuando el preferido se colgaba, no
  llegaba a probar ninguno.
- **Un modelo que falla se aparta, pero nunca se le echa.** Cinco minutos, o
  treinta si el fallo fue permanente; mientras tanto va al final de la lista en
  vez de desaparecer, así que si fallan todos se siguen intentando todos. No hay
  «modelo preferido» que recuperar: el orden de `MODELO_IA` manda salvo que
  alguno esté castigado. Medido, ninguno de los tres es fiablemente mejor —
  el endpoint compartido falla a rachas, no por modelo.

## Tests

```bash
./venv/bin/python -m pip install -r requirements-dev.txt
./venv/bin/python -m pytest tests/ -q
```

GitHub Actions ejecuta la suite completa con las dos versiones soportadas de
Python, 3.12 y 3.14, en cada `push` y `pull_request`.

Cubren la distribución de rarezas y del 2d6, la curva de decaimiento y el
momento exacto de la muerte, las estadísticas, la resolución de competencias con
dados fijos, la ida y vuelta contra SQLite, y que **ningún marco se descuadre**
en las 60 combinaciones de especie, ánimo y etapa. El último es el que más veces
ha salvado el proyecto: el ASCII se rompe con una facilidad asombrosa.
