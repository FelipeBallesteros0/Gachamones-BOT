# Gachamones BOT

Un tamagotchi que vive en un canal de Discord. Sale de un huevo, es uno de 10
gachamones al azar —hay 25 en total; los otros 15 se encuentran por ahí—, se cuida con los botones bajo el mensaje y compite contra los
de otras personas en carreras, peleas de sumo, asaltos al tótem y laberintos de
ecos. Todo el arte es ASCII dentro de bloques de código: ni una sola imagen.

```
## 🐥 Pelusa
-# Piollito · adulta · nivel 3 · 4V-1D · 2 días de vida
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
│     FUE 11   VEL 21      │
│     SAL 11   ING  9      │
╰──────────────────────────╯
[🍖 Alimentar] [🎮 Jugar] [🏋️ Entrenar] [🧼 Limpiar] [🔄 Actualizar]
```

Son **cuatro estadísticas** —fuerza, velocidad, salud e ingenio— y salen en
dos filas porque en una sola no caben sin recortar los números. Las cuatro se
tiran al nacer, sobre la base de la especie.

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
versiones exactas; `requirements-dev.txt` añade pytest para CI y pre-commit para
desarrollo. Las dependencias transitivas siguen bajo el resolvedor de pip: este
primer paso hace reproducibles las dependencias directas, pero no es un lock
transitivo con hashes.

### 4. Desplegar en la Raspberry

```bash
PI=usuario@ip-de-tu-pi                        # o edita el valor por defecto
scp .env $PI:/home/usuario/tamagotchi-bot/.env   # sólo la primera vez
./actualizar-pi.sh
```

Hay **dos scripts y no hacen lo mismo**:

| | De dónde saca el código | Cuándo usarlo |
|---|---|---|
| `actualizar-pi.sh` | **De GitHub**, con un `git pull` en la propia Pi | Lo normal |
| `deploy.sh` | De la carpeta desde la que lo lanzas | Probar en la Pi algo sin commitear |

`actualizar-pi.sh` es el que evita el desfase de desplegar una copia local que no
está al día con `main`: **avisa si tienes commits sin subir**, copia la base de
datos antes de tocar nada (guarda las 5 últimas), pone la Pi en el commit de
`main`, corre la suite allí y **sólo reinicia si pasa**. La primera vez convierte
el directorio en un clon de git; el `.env`, la base y el `venv` están en
`.gitignore`, así que no los toca.

```bash
./actualizar-pi.sh              # lo normal
SIN_TESTS=1 ./actualizar-pi.sh  # sin correr la suite en la Pi (~50 s)
RAMA=otra ./actualizar-pi.sh    # otra rama
```

Los dos admiten `PI` y `DEST` como variables de entorno. Para ver el registro:

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
| `/totem @alguien` | Asalto al tótem: una fase de velocidad, otra de fuerza y otra de salud, cada una `estadística + 1d20`. Cada fase reparte puestos y gana quien más sume. De dos a cinco. |
| `/laberinto @alguien` | Laberinto de Ecos: **SEÑALES**, **TRAZADO** y **NO PERDERSE**, las tres con ingenio. Cada fase se juega contra un eco común y gana quien más puertas abre. De dos a cinco. |
| `/aventura` | Sal al campo con tu activo: dos decisiones —fuerza, velocidad o volverse— y quizá un objeto o un gachamon salvaje. |
| `/jardin` | Todas las criaturas activas del servidor juntas, e interactuando. |
| `/ranking` | Criaturas vivas con más victorias. |
| `/cementerio` | Las que ya no están. |
| `/ayuda` | Resumen de las reglas. |
| `@Gachamon <lo que sea>` | Hablar con tu criatura. Te contesta en su propio carácter. |

## Reglas

**El plantel.** Hasta **10 gachamones** por persona y servidor, con **uno
activo**: el que recibe los botones y los comandos. Los demás esperan en la
**incubadora**, y ahí **no les pasa el tiempo** — ni hambre, ni ánimo, ni aseo,
y no pueden morir. No es un adorno: los cuidados sólo llegan al activo, así que
si la reserva decayera se moriría de hambre hiciera lo que hiciera su dueño.

Encaja en dos sitios y ninguno es una regla nueva: `avanzar()` devuelve intacta
a la que no está activa, y al guardarla se dejan a NULL `muere_en` y `avisa_en`,
que es lo único que hace falta para que los bucles de muerte y de aviso la
ignoren —los dos ya pedían `IS NOT NULL`—. Al sacarla se le pone
`actualizada_en` al día, o las horas dormidas se le caerían encima de golpe.

`/huevo` da **sólo el de partida**: los demás hay que ganárselos en
`/aventura`. Si muere el activo, sale solo el siguiente de la incubadora.

**Aventura.** `/aventura` **te saca a ti con tu gachamon activo** a un bioma al
azar —hay **diez**: planicie, ciénaga, bosque, arrecife, chatarral, desierto,
cumbre, ruinas, cavernas y volcán— y os planta delante una escena
con **tres salidas**: fuerza, velocidad o volverse. Las dos primeras tiran
`stat + 1d20` contra la dificultad del bioma y **cuestan lo mismo**: si una fuera
más barata, la otra no la elegiría nadie y la decisión sería un adorno. Volver no
arriesga nada, pero tampoco cuenta como nodo superado.

**La espera de 37 minutos es de la persona, no del gachamon**, y por eso vive en
`cooldowns_persona` y no en `cooldowns`. Es la única que lo hace: cuidar y
competir son del gachamon —es él quien come y quien pelea—, pero a la aventura
vas tú. Atada al gachamon era un agujero: con varios en el plantel se salía
varias veces seguidas cambiando de activo entre viaje y viaje.

Son **dos decisiones**. Acertar lleva a la escena siguiente; fallar cierra el
viaje ahí mismo, así que un viaje jugado trae **un fallo como mucho**. Si vuelve
con vida gana **+4 XP por el viaje**; morir por el desgaste no da XP.

Las escenas **las inventa el LLM** (JSON validado antes de usarlo: si falta una
opción o una etiqueta no cabe en un botón de Discord, se descarta) y hay escenas
escritas por bioma de respaldo, para que la aventura no se quede muda al agotar
el límite de IA. El viaje se narra al final en **una sola llamada** más.

**Y se narra de los dos**: «Felipe y Pelusa salen al Bosque», con tu nombre
visible de Discord. Los botones ya te hablaban a ti —«Colarte por la ventana»,
«Seguir tu camino»—, así que contar que el gachamon iba solo era la ficción
contradiciendo a la mecánica. Como el plural obliga a conjugar, el guardia de
`usa_formas_de_vosotros` hubo que ampliarlo: era una lista cerrada de palabras y
no pillaba «cruzáis» ni «llegaréis», que es lo primero que soltó el modelo. Ahora
mira también las terminaciones `-áis` y `-éis`, y si se le escapa una, se publica
el texto escrito en vez de la narración.

Lo hondo que se llegue decide qué se encuentra:

| Nodos superados | Salvaje | Objeto | Nada |
|---:|---:|---:|---:|
| 2 | 55 % | 25 % | 20 % |
| 1 | — | 55 % | 45 % |
| 0 | — | 30 % | 70 % |

El salvaje **sólo aparece llegando al fondo**: es el gachamon dormido dentro del
cofre, y quedarse a medias no puede pagar lo mismo. El 55 está medido, no puesto
a ojo: sobre 40 000 aventuras con criaturas recién nacidas, el árbol termina con
los dos nodos el 46 % de las veces, así que deja el encuentro en el **25 % de las
aventuras**, exactamente donde estaba antes del árbol. Concentrar el premio al
fondo no podía colarse como una subida de dificultad.

Cada bioma **cría lo suyo** —al volcán van Pyro y Tsushimon; a las ruinas,
Duskhouse y Re-bot—, así que el bioma que toque decide con quién te puedes
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

Los números están medidos, no puestos a ojo. Simulando encuentros por cada
ajuste, con el listón de confianza en 90 sale **100 % jugando la mejor opción y
42 % pulsando a ciegas**.

Que jugando bien salga siempre es **deliberado**. Antes el listón estaba en 100 y
la tasa a ciegas era del 27 %, que costaba demasiado; bajarlo un 10 % la sube al
42 % y, de paso, deja el reclutamiento asegurado para quien se sepa la tabla de
caracteres. Se aceptó ese coste a cambio de que unirse fuera más fácil.

Lo que no puede perderse es que **leerle el carácter se note**, y eso sí lo fija
un test: si alguien toca las reacciones y a ciegas empieza a salir tan bien como
jugando bien, la mecánica se habrá quedado en una tirada disfrazada.

Medido de punta a punta —viaje y encuentro, 40 000 aventuras—, el árbol acaba
reclutando **más** que las dos tiradas de antes, porque llegar al fondo sube
también la confianza de partida:

| | Encuentro | Recluta |
|---|---:|---:|
| antes, estadística sorteada | 25,3 % | 3,5 % |
| árbol, eligiendo bien | 25,0 % | 5,5 % |
| árbol, pulsando a lo loco | 11,3 % | 2,7 % |

La última fila es la que justifica el árbol: quien se vuelve a la primera se
encuentra la mitad de cosas. Ahí es donde la decisión pesa.

**Al unirse no trae nombre.** Se guarda ya en la incubadora —para que un
formulario cerrado o una conexión caída no cuesten el gachamon recién
convencido—, pero con el nombre vacío no puede activarse: `db.activar` lo
rechaza, el menú del plantel lo lista como «sin nombrar» y pulsarlo abre el
bautizo. Es lo que se pidió, «no entra al equipo hasta nombrarlo», sin que un
despiste te lo cueste.

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
73 h; la salud alarga ese margen (una Magora sana llega a ~86 h, un Pyro frágil
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
+2 jugar, +3 entrenar) y de volver con vida de una aventura (+4), para que quien
no quiera pelear también vea crecer a su criatura. Competir sigue siendo lo más
rentable por acción.

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

El **asalto al tótem** es de dos a cinco y no basta con llegar: hay que tomar el
tótem y conservarlo. Son tres fases y cada una pone a prueba una estadística
entera —**AL CENTRO** velocidad, **FORCEJEO** fuerza y **HUIDA** salud—, sin
mezclas. Lo que cambia es el recuento: en cada fase se reparten **puntos de
colocación**, tantos como asaltantes al primero y uno al último, y gana quien
más sume de las tres. Por eso lo gana el gachamon **completo** y no el
especialista: quien arrasa en una fase se queda atrás en las otras dos.

Si dos empatan a puestos manda lo acumulado en bruto de esas tres fases. Sólo si
también eso empata se juega otro **FORCEJEO**, y ése desempata **dentro** del
empate: tiran sólo los que siguen empatados, no reparte puestos ni suma al bruto
oficial, así que nadie de fuera adelanta por él. Si a la vez hay dos empates y
uno se deshace antes, el otro sigue tirando por su cuenta sin tocar al primero.

Las tres estadísticas dejan **veta**, porque las tres se han jugado de verdad,
pero el **entrenamiento sigue siendo un punto** por competencia como en las
otras dos modalidades —el coste, el enfriamiento y la experiencia son los
mismos—. Se lo lleva la más atrasada de las tres, así que asaltar a menudo
equilibra al gachamon en vez de multiplicar su progreso.

El **laberinto de ecos** es de dos a cinco y es el único donde el adversario no
es el rival, sino el terreno. Son tres fases con **ingenio** —**SEÑALES** el
ingenio a secas, **TRAZADO** 70 % ingenio y 30 % velocidad, **NO PERDERSE**
70 % ingenio y 30 % salud—, y en cada una el pasillo devuelve un **eco**: la
base del participante del medio más su propio 1d20, uno solo para toda la fase.
Abre la puerta quien **supera** al eco; igualarlo no basta, así que una fase
puede acabar sin que cruce nadie y eso también es parte del juego.

Gana quien más **puertas** abre. Que el eco salga de la mediana y no del
promedio es lo que impide invitar a alguien flojo para bajarlo: un participante
débil no mueve la mediana, así que no le regala puertas a nadie. Sólo el
ingenio deja **veta** aquí, y el punto de entrenamiento va también al ingenio,
que es la única estadística que ningún cuidado sube.

En las cuatro modalidades sólo el primero suma victoria y se lleva los +10; el
resto, +4. Un torneo cuenta como **una sola competencia** para el coste y la
experiencia, aunque los finalistas peleen dos veces.

Los empates se deshacen distinto en cada modalidad. En la **carrera** se corre
otro tramo **para todos**, porque allí el marcador es la suma y un tramo más la
cambia. En el **sumo** se repite el intercambio empatado entre los dos que
pelean. En el **asalto al tótem** se juega otro **FORCEJEO** sólo **entre los
que siguen exactamente empatados**: quien ya quedó por delante no vuelve a
tirar, así que un desempate ajeno no le puede cambiar el puesto. El **laberinto**
lo deshace igual, con otra tirada de **SEÑALES** entre los empatados y sin eco:
un desempate no es una fase, así que no reparte puertas ni suma al bruto
oficial. En los cuatro casos hay un tope de intentos y, si aun así no se
deshace, decide el orden en que se entró al reto.

Al terminar, la pantalla sólo se republica a quien **suba de nivel o
evolucione**. Al resto le queda la de antes con los números viejos, pero con los
botones vivos: actúan sobre la base de datos, no sobre lo que se ve, y la
pantalla se pone al día en cuanto se pulsa cualquiera.

**Consumibles.** Los botones 🎒 **Mochila** y 🛒 **Tienda** abren menús que sólo
ve quien los pulsa. Cada persona empieza con **50 asciicoins y 50 asciigems**.
En la tienda se compra todo, cada moneda en su desplegable: los consumibles con
asciicoins y los cosméticos con asciigems, sin conversión entre las dos. Los
cosméticos van a tu **ropero** y se ponen y se quitan con 🎨 **Personalizar**. El
monedero es **suyo, no de la criatura**, así que lo comprado sobrevive a la
muerte de una mascota. Hay
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
sin sustituirla: un Geo travieso sigue siendo lento y de pocas palabras,
pero con retranca.

Todo lo que una criatura dice de sí misma lleva marcas de concordancia
`{masculino/femenino}` que resuelve `especies.concordar()`. Los prompts se montan
con las marcas puestas y se resuelven de una vez al final, así ningún texto nuevo
se puede olvidar de concordar; un test comprueba que no sobrevive ninguna marca.

**Hablar.** Menciona al bot y tu criatura contesta con su propio carácter: el
Piollito mete «pío» en todas las frases, Geo responde con una palabra, y si
intentas acariciar a Pyro te quema los dedos. El tono cambia según cómo la
tengas — una criatura hambrienta contesta de mal humor — y se acuerda de los
últimos ocho intercambios. Hasta 20 mensajes por hora y por persona. Hablar no
gasta comida ni da experiencia: queda fuera del equilibrio del juego.

## Cómo está montado

La lógica del juego vive en módulos **puros** que no importan `discord` y se
testean sin conexión. Los cogs son capas finas encima.

| Fichero | Qué hace |
|---|---|
| `especies.py` | Las 25 especies, su arte ASCII por etapa, estadísticas y rarezas. |
| `jardin.py` | El reparto de varias criaturas en una sola escena. |
| `personalidad.py` | La voz de cada especie, los diez caracteres y cómo se le explica todo al modelo. |
| `ia.py` | Cliente de IA (NVIDIA y DeepSeek). Async, con transporte inyectable. |
| `simulacion.py` | Decaimiento, muerte, acciones de cuidado, estadísticas y niveles. |
| `competir.py` | Resolución y narración de carreras, sumo, asaltos al tótem y laberintos de ecos. |
| `objetos.py` | El catálogo de consumibles: precios, dados y qué hace cada uno. |
| `pantalla.py` | Dibuja la pantalla como texto de Discord. |
| `db.py` | SQLite. |
| `economia.py` | Monederos, topes UTC y operaciones económicas atómicas. |
| `economia_reporte.py` | Informe local agregado y reconciliación histórica. |
| `vistas.py` | Los botones y el ciclo publicar-nueva/congelar-la-vieja. |
| `equipo.py` | El menú para cambiar de gachamon activo. |
| `aventura.py` | Biomas, el árbol de decisiones, hallazgos y las reacciones de un salvaje. |
| `tienda.py` | Los menús de mochila y tienda, y el uso de un objeto. |
| `cogs/` | Los slash commands. |

**Cómo se guarda el arte.** Cinco etapas por veinticinco especies, con tres
estados de ánimo cada una, serían 375 dibujos. Pero casi todos se diferencian
**sólo en la cara**: el mismo cuerpo de Piollito con `^v^`, `o.o` o `T_T`. Así
que cada etapa es una plantilla con un hueco `{cara}` y cada especie declara sus
tres caras: **125 dibujos y los ánimos salen gratis**. Donde el ánimo cambia más que la cara
—a Magora se le caen las hojas, la llama de Pyro mengua— se declara el dibujo
completo en `excepciones`, que gana a la plantilla. Las tres caras de una
especie tienen que medir lo mismo, o sustituir una por otra descuadraría el
dibujo; hay un test que lo comprueba.

**El catálogo.** Veinticinco especies repartidas en diez biomas, pero **del
huevo sólo salen diez**: las de siempre. Las quince nuevas hay que
encontrárselas en `/aventura`, para que el comienzo sea conocido y el catálogo
grande sea lo que se descubre jugando.

**El peso es la probabilidad en el huevo, y sólo eso.** Las quince que no salen
de él llevan peso 0 en vez de arrastrar un número que no significa nada, y las
diez que sí salen suman 100 entre ellas — cada peso se lee como un porcentaje,
y el Tsushimon es uno de cada veinticinco huevos.

**En el campo pesa la rareza, no el peso del huevo.** `tirar_salvaje` sortea
dentro del bioma con `PESO_EN_EL_CAMPO`, que reparte 12/6/4 — el mismo reparto
que el huevo, para que «raro» signifique lo mismo en los dos sitios. No puede
leer `Especie.peso` justamente porque vale 0 en quince especies: las dejaría sin
aparecer nunca en ningún sitio.

Antes era uniforme y una rara salía tanto como sus vecinas: su rareza sólo se
notaba en los 30 puntos de estadísticas. Ahora un Tsushimon pasa del 33 % al
14 % de su bioma, y encontrar una rara **concreta** cuesta unas 280 aventuras
—173 h de juego— en vez de 120. Sólo cambia donde el bioma mezcla rarezas: en
las Ruinas las tres son «poco común» y allí reparte igual que siempre. Diecisiete son
comunes, cinco poco comunes y tres raras; los pesos suman 100 exactos —17 × 4,5
+ 5 × 3,5 + 3 × 2,0— y hay un test que lo comprueba, porque es justo lo que se
descuadra al añadir especies a mano. Comunes y poco comunes reparten **24 puntos
exactos** entre las tres estadísticas y las raras **30**: ninguna es mejor que
otra dentro de su rareza, sólo distinta.

Al triplicar el catálogo, encontrar una rara **concreta** bajó del 4 % al 2 %,
pero las tres juntas siguen saliendo el 6 % de las veces.

Y ninguna se llama distinto de mayor. El campo que guardaba ese segundo nombre
se quitó en vez de dejarlo repitiendo el primero: un campo que siempre vale lo
mismo que otro es ruido.

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
- **Cada modelo lleva su proveedor delante** (`deepseek:deepseek-v4-pro`), y
  cada proveedor su URL, su clave y sus campos propios. Antes había una sola URL
  y una sola clave globales, así que la cadena de recambio sólo podía saltar
  entre modelos del mismo sitio: o todo gratis o todo de pago. Sin prefijo se
  asume NVIDIA, y los modelos de un proveedor sin clave se saltan solos, para
  que dejar DeepSeek escrito antes de pagar no cueste un intento contra un 401.
- **Hay que apagar el razonamiento, y cada proveedor lo apaga a su manera.**
  NVIDIA con `chat_template_kwargs`, DeepSeek con un `thinking` de primer nivel.
  No es un ajuste fino: en DeepSeek viene encendido en `high` por defecto, se
  cobra como salida, y v4-pro se comería los 1200 tokens de `MAX_TOKENS`
  razonando sin llegar a contestar. Ese fallo exacto ya lo sabe describir
  `pedir()` por lo que costó descubrirlo con el razonador de NVIDIA.

## Tests

### Desarrollo local

Instala las dependencias de desarrollo, ejecuta la suite e instala el hook local:

```bash
./venv/bin/python -m pip install -r requirements-dev.txt
./venv/bin/python -m pytest tests/ -q
./venv/bin/python -m pre_commit install
```

Para comprobar manualmente los mismos gates del hook sobre todo el repositorio:

```bash
./venv/bin/python -m pre_commit run --all-files
```

GitHub Actions ejecuta la suite completa con las dos versiones soportadas de
Python, 3.12 y 3.14, en cada `push` y `pull_request`.

Cubren la distribución de rarezas y del 2d6, la curva de decaimiento y el
momento exacto de la muerte, las estadísticas, la resolución de competencias con
dados fijos, la ida y vuelta contra SQLite, y que **ningún marco se descuadre**
en las 60 combinaciones de especie, ánimo y etapa. El último es el que más veces
ha salvado el proyecto: el ASCII se rompe con una facilidad asombrosa.
