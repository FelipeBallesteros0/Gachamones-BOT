# Gachamones BOT

Un tamagotchi que se juega en una página web: **rowino.online/gachamon**. Sale
de un huevo, es uno de 10 gachamones al azar —hay 25 en total; los otros 15 se
encuentran por ahí—, se cuida, se viste, vive en un departamento y se pasea por un
pueblo. Nació como bot de Discord, y por eso este repositorio todavía lleva el
bot: **el juego de Discord está en pausa**. Hoy el bot sólo atiende `/vincular`,
que es la forma de llevar a la página los gachamones de quien jugaba allí, y a
todo lo demás contesta que el juego se mudó.

Son **cuatro estadísticas** —fuerza, velocidad, salud e ingenio— y se tiran al
nacer, sobre la base de la especie.

## Puesta en marcha

### 1. Crear la aplicación en Discord

1. Entra en <https://discord.com/developers/applications> → **New Application**.
2. Pestaña **Bot** → **Reset Token** → copia el token.
3. **No hace falta activar ningún intent privilegiado.** El bot funciona sólo
   con slash commands, así que *Message Content* puede quedar apagado.
4. Pestaña **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Permisos: *Send Messages*, *Read Message History*
   - Abre la URL que genera e invita el bot a tu servidor.

   No necesita *Gestionar mensajes*: edita y borra sólo sus propios mensajes
   del manual, y eso siempre está permitido.
5. Activa **Ajustes → Avanzado → Modo desarrollador**, haz clic derecho sobre el
   canal donde quieras que viva y elige **Copiar ID**.

### 2. Configurar

```bash
cp .env.ejemplo .env
$EDITOR .env          # DISCORD_TOKEN, CANAL_ID y (recomendado) GUILD_ID
```

Con `GUILD_ID` los comandos aparecen al instante. Sin él, Discord tarda hasta
una hora en propagarlos por todos los servidores. `CANAL_INFO_ID` es el canal
del manual (opcional) y `URL_GACHAMON`, también opcional, la dirección de la
página que dice el aviso: sin ella vale la pública, `https://rowino.online/gachamon`.

**Varios servidores.** `GUILD_ID` también admite una lista separada por comas.
Cada servidor lleva sus propios gachamones: la misma persona puede tener un
plantel distinto en cada uno. Acuérdate de añadir el canal de
cada servidor a `CANAL_ID`. Si uno de los servidores da error al registrar los
comandos (por ejemplo porque el bot no está invitado ahí), el bot lo avisa en el
registro y sigue funcionando en los demás.

**Varios canales.** `CANAL_ID` admite una lista separada por comas:

```
CANAL_ID=123456789012345678,987654321098765432
```

Los comandos funcionan en todos ellos, y cada persona sigue teniendo **un solo
plantel por servidor**: el bot sólo contesta en esos canales.

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
`main`, corre la suite allí y **sólo reinicia si pasa** (si no, la Pi vuelve al
commit en el que estaba, no reinicia el bot y vuelve a arrancar la web). La suite usa un temporal
en memoria (`--basetemp=/dev/shm/...`) que se borra al terminar, y para ello
instala `requirements-dev.txt` (con `SIN_TESTS=1` instala sólo
`requirements.txt`). La primera vez convierte
el directorio en un clon de git; el `.env`, la base y el `venv` están en
`.gitignore`, así que no los toca.

```bash
SIN_TESTS=1 ./actualizar-pi.sh  # lo habitual, con la CI ya en verde
./actualizar-pi.sh              # corriendo además la suite en la Pi
RAMA=otra ./actualizar-pi.sh    # otra rama
```

La forma habitual es `SIN_TESTS=1 ./actualizar-pi.sh`, cuando la integración
continua ya pasó en las dos versiones de Python: la web se para unos segundos;
con la suite en la Raspberry, unos minutos. Si el despliegue se corta después
de pararla (falla `pip`, se cae la conexión) y la Pi se entera, hace lo mismo
que con la suite en rojo: vuelve al commit en el que estaba, que es el código
que corre el bot, y reinicia la web con él. Un corte que llega cuando el bloque
remoto y la suite ya terminaron bien, o que la Pi no detecta, puede dejar la web
parada: por eso, si el guion termina con error, su última línea es el comando
exacto para arrancarla a mano.

`deploy.sh` también copia la base de datos (misma rotación de 5) antes de reiniciar, y no corre la suite. Su `rsync --delete` no toca la base ni su diario (`*.db`, `*.db-journal`, `*.db-wal`, `*.db-shm`).

Los dos guiones instalan y habilitan las dos unidades (`tamagotchi` y
`gachamon-web`), reinician **primero el bot y después la web**, y terminan
comprobando cada servicio por separado (`systemctl is-active tamagotchi` y
`systemctl is-active gachamon-web`) y preguntándole a la web por su salud
(`curl` a `/gachamon/api/salud`, con reintentos durante unos diez segundos): si
algún servicio no queda activo o la web no contesta, el guion falla.

Los dos admiten `PI` y `DEST` como variables de entorno. Para ver el registro:

```bash
ssh $PI 'journalctl -u tamagotchi -u gachamon-web -f'
```

## La web

Junto al bot corre un segundo servicio, la web del juego: una aplicación FastAPI
(`web.app:app`) que cuelga toda de `/gachamon`. Es otro adaptador fino sobre los
mismos módulos y la misma base `tamagotchi.db`; no importa `discord`, no guarda
estado del juego en memoria y sabe quién eres sólo por la cookie de sesión de
Rowino.

El juego se ve como un pueblo: un mapa con nueve lugares por el que caminas con
tu avatar y tu gachamon detrás. En todos puedes cuidarlo y acariciarlo; hoy están
abiertos tu casa, la Incubadora y la tienda, y los demás avisan de que
abren más adelante (el Refugio sigue en el mapa, cerrado: ya nadie vive en él). En la
Tienda del pueblo se compran objetos, cosméticos (con gemas) y muebles, con el mismo
dinero de siempre; lo que todavía no se puede usar en la
página no se le vende a nadie. La mochila se abre
desde cualquier lugar y sirve para usar lo que llevas. Desde cualquier lugar
también se abre la ficha completa de tu gachamon, con sus medallas y los efectos
que lleva activos, y el ropero, donde le pones y le quitas el sombrero y el
título. La Incubadora enseña tu plantel: ahí sacas a otro gachamon para que sea
el activo, y dice cuántos caben según las camas.

En local:

```bash
./venv/bin/python -m uvicorn web.app:app --port 8010
```

Se abre en `http://127.0.0.1:8010/gachamon/`. Sin una base de Rowino a mano
nadie puede entrar: `RUTA_ROWINO_BD` dice dónde está.

Variables del `.env` (explicadas en `.env.ejemplo`):

- `ROWINO_SECRET_KEY`: la misma `SECRET_KEY` con la que Rowino firma su cookie.
  Sin ella nadie puede entrar. Nunca se escribe en el repositorio.
- `RUTA_ROWINO_BD`: la base de Rowino, de donde se lee quién es la cookie. Por
  defecto, `../rowino_web/rowino.db` junto al repositorio.
- `GUILD_WEB` (opcional): el servidor que hace de pueblo; sólo ahí funciona
  `/vincular`. Vacío, vale el primero de `GUILD_ID`.
- `URL_GACHAMON` (opcional): la dirección de la página que el bot pone en sus
  avisos. Sin ella, la pública.

Si falta la clave o la base de Rowino no se puede leer, la web no pide que
entres: contesta 503 («El juego no está disponible ahora mismo.»), y al
arrancar deja en el registro un aviso por cada cosa que falta.

En producción lo lleva la unidad `gachamon-web.service`, que escucha sólo en
`127.0.0.1:8010`, y se publica como `rowino.online/gachamon` detrás del túnel,
con una regla por ruta. Quien jugaba en Discord entra con su cuenta de Rowino, elige «Ya jugaba en
Discord», pide su código, escribe `/vincular` en el canal del juego y encuentra a
sus gachamones.

### Arte

El arte del pueblo, de las escenas de cada lugar, del avatar y de los íconos son
archivos de `web/static/arte/`, y quien dibuja no necesita tocar código: el
contrato, con el nombre y el tamaño exacto de cada pieza, está en
`docs/arte/contrato.md`. Hoy todo ese arte es de relleno (lleva «RELLENO»
escrito) y se reemplaza guardando el archivo nuevo con el mismo nombre y el
mismo tamaño. Los íconos (de objetos, cosméticos y muebles) salen de los
catálogos del juego y miden 48 × 48: un objeto nuevo añade el suyo.

Para regenerar los rellenos que falten:

```bash
./venv/bin/python -m herramientas.rellenos
```

Sólo escribe los archivos que no existen, así que un dibujo de verdad nunca se
pisa. Con `--todo` rehace **todas** las piezas, también los dibujos de verdad
que ya hubieran reemplazado a su relleno: vuelven a ser relleno. Al correr la
suite, `tests/test_arte.py` falla si falta una pieza o si alguna no mide lo que
dice el contrato.

## Comandos

El bot ya no tiene el juego: tiene tres comandos, y sólo `/vincular` hace algo.

| Comando | Qué hace |
|---|---|
| `/vincular <código>` | Une esta cuenta de Discord con la tuya de rowino.online. Sólo vale en el servidor de la página (`GUILD_WEB`). |
| `/mascota` | Contesta, sólo a ti, que el juego se mudó a la página. |
| `/huevo` | Lo mismo: se quedó porque es lo que la gente escribe de memoria. |

Además, quien menciona al bot en su canal, y quien pulsa un botón, un menú o un
formulario de un mensaje viejo, recibe ese mismo aviso; también quien usa un
comando que ya no existe. En un servidor que no es el de la página el aviso dice
que el juego está en pausa y que lo de cada quien sigue guardado.

El bot también mantiene una sola página de manual en el canal que le indiques
con `CANAL_INFO_ID`: dice que el juego se mudó, dónde está, cómo vincular y en
qué canal del juego de ese servidor se escribe `/vincular`. En un servidor que
no es el de la página, la página es el aviso de la pausa. Se edita en el sitio y
nunca se republica, así que un arranque sin cambios no toca el canal; las otras
páginas del manual de antes las borra. Un servidor sin ese canal se queda sin
ella.

## Reglas

Son las reglas que la página ya tiene. Las que esperan su pantalla están más
abajo, en [En pausa](#en-pausa).

**El plantel.** Sin tope fijo: lo limitan las camas de tu departamento (más abajo). Hay **uno activo**: el que sale contigo. **A todos les pasa el
tiempo**, sean o no el activo: la comida, el ánimo y el aseo les bajan al mismo
ritmo, con el ritmo de tu departamento. Cambiar de activo sólo cambia quién sale contigo: no toca el reloj de
nadie, así que ir y volver no ahorra ni duplica nada.

Un cuidado le cae a un gachamon concreto: al que se elige o, si no se elige, al
activo. Las esperas son de cada gachamon; el tope diario de monedas es uno solo
por persona. Existe también cuidar **a todos** de una vez: le hace un cuidado a
cada gachamon que puede recibirlo y paga como esos mismos cuidados hechos de a
uno. Esa regla vive en el servidor de la web, que todavía no tiene el botón.

El huevo da **sólo el de partida**: los demás hay que ganárselos en las
aventuras, que están en pausa. Si una persona se quedó sin activo vivo porque el
suyo murió antes, el primero que siga vivo sale solo al arrancar el bot o la web.
El remiendo de antes sigue ahí por si acaso: también sale al entrar a la web, al
romper el huevo, al poner nombre o al cambiar de activo. Sólo cambia la marca de
quién sale contigo: su reloj sigue donde estaba.

**El departamento.** Cada persona tiene **uno solo** por servidor, hecho de
casillas: parte en 3 × 3 y se amplía por una fila o una columna, a 15 monedas por
casilla, hasta 8 × 8. Los muebles ocupan casillas y giran en cuatro posiciones;
puede haber varios iguales, y cada uno está puesto o guardado (guardar nunca lo
destruye). Lo que compras en la Tienda llega a guardados, y ampliar se compra
estando en tu departamento. Las **camas** son el límite de gachamones: hacen
falta tantas camas puestas como gachamones vivos más una, la tuya; reclutar pide
una cama libre y una cama que hace falta no se guarda. La **comodidad** es una
puntuación (no un porcentaje): parte de 80, cada tipo de mueble puesto suma una
vez y el tope crece con las casillas. Frena el ánimo de todos los que viven ahí y
no toca el hambre. Las casas, el refugio, la intemperie y el huerto se fueron:
el día del cambio se convirtió una sola vez lo que cada persona tenía (le
devolvimos lo que habían costado sus casas y sus tickets, y se cosechó lo
plantado), y una carta del alcalde se lo cuenta una vez. El huerto está cerrado
hasta que vuelva con el balcón, y la pantalla del departamento todavía no existe:
las reglas y sus rutas están en el servidor.

**Nacer.** La especie sale por rareza: 12 % cada una de las siete comunes, 6 %
las dos poco comunes y 4 % el dragón. Las estadísticas al nacer son **la base de
la especie + 2d6** tirado por separado en cada una.

Al romper el cascarón ves primero **qué ha salido y con qué estadísticas**, y
sólo después le pones nombre. La criatura nace en la base de datos en ese mismo
momento, con el nombre de su especie como provisional: si te vas sin bautizarla
sigue siendo tuya.

**Cuidar.** Tres barras bajan con el tiempo, en todos los gachamones vivos. Si
**COMIDA** llega a 0, la criatura **no se muere**: se queda en 0 hasta que le
des de comer. Una criatura típica tarda unas 73 h en vaciarla; la salud alarga
ese margen (una Magora sana llega a ~86 h, un Pyro frágil baja a ~62 h). El
ánimo y el aseo tampoco matan: el aseo bajo amarga el ánimo, y el ánimo bajo
penaliza en las competencias, que están [en pausa](#en-pausa). Los que murieron
antes siguen guardados.

**Crecer y evolucionar.** Cada nivel es una etapa, y **el dibujo cambia**:
cría → niño → adolescente → adulto → adulto grande. La experiencia sale tanto
de competir (+10 al ganar, +4 al perder) como de cuidar (+1 alimentar,
+2 jugar, +3 entrenar) y de volver de una aventura (+4), para que quien
no quiera pelear también vea crecer a su criatura. Competir sigue siendo lo más
rentable por acción. Hoy en la página sólo se gana cuidando: competir y las
aventuras están [en pausa](#en-pausa).

La curva está calibrada sobre unos 27 XP diarios, que es lo que saca alguien
que atiende a su criatura un par de veces al día: **el primer salto cae en un
día y llegar a la forma final cuesta cerca de un mes** (25, 100, 250 y 525 XP).
Cada evolución reparte 2, 3, 4 y 5 puntos de estadística según el perfil de la
especie; como parte va a salud, la criatura evolucionada aguanta más sin comer.

`estadística = base + √entrenamiento + bonus de nivel`. La raíz cuadrada hace
que machacar el botón no compense: el segundo punto cuesta 4 sesiones, el
tercero 9, el décimo 100.

**Consumibles.** La Mochila y la Tienda de la página guardan y venden lo que
usas. Cada persona empieza con **50 monedas y 50 gemas**. En la tienda se compra
todo, cada moneda en lo suyo: los consumibles con monedas y los cosméticos con
gemas, sin conversión entre las dos. Los cosméticos van a tu **ropero**. El
monedero es **suyo, no de la criatura**: lo comprado es de la persona y sirve
para cualquiera de sus gachamones. Hay pociones de fuerza y de velocidad de 1d4
a 1d12 que duran cinco minutos y sirven para competir, que está
[en pausa](#en-pausa); una que llena el hambre saltándose el empacho, y
dos que borran un enfriamiento. Lo que todavía no se puede usar en la página (lo
que sirve para competir) no se vende a nadie, y la semilla ya no se vende.

**Economía.** Un cuidado válido da +1 moneda (hasta 12 al día UTC), cada
competencia resuelta da +4 a cada participante y +2 extra a quien gana (hasta
tres competencias premiadas al día UTC; competir está [en pausa](#en-pausa)), y
evolucionar da +10 una vez al día
UTC. Los topes pertenecen a la persona y al servidor: cambiar de activo,
reclutar o evolucionar no los reinicia. Agotar un tope no
detiene el juego, la experiencia ni la evolución; sólo deja el premio en cero.

Las compras y los premios se confirman en SQLite antes de contestar nada. El
informe local agregado no expone IDs:

```bash
./venv/bin/python economia_reporte.py --desde 2026-01-01 --hasta 2026-01-31
# Añade --json para salida estructurada y --db otra/ruta.db si hace falta.
```

**Quién le ha tocado ser.** Además de la especie se sortean al nacer el
**género** (♂️ o ♀️, mitad y mitad) y la **personalidad**, una de diez: alegre,
sereno, miedoso, valiente, gruñón, curioso, cariñoso, orgulloso, perezoso o
travieso. Los dos salen en la ficha y no cambian nunca. **No tocan ninguna
estadística**: sólo cómo habla, así que ninguna personalidad es mejor que otra.
La personalidad se suma a la voz de la especie sin sustituirla: un Geo travieso
sigue siendo lento y de pocas palabras, pero con retranca.

Todo lo que una criatura dice de sí misma lleva marcas de concordancia
`{masculino/femenino}` que resuelve `especies.concordar()`. Los prompts se montan
con las marcas puestas y se resuelven de una vez al final, así ningún texto nuevo
se puede olvidar de concordar; un test comprueba que no sobrevive ninguna marca.

## En pausa

Estas reglas siguen en el código y en sus pruebas, pero hoy no se pueden jugar
en ningún sitio: esperan su pantalla en la página. Volverán.

- **Aventuras.** Se sale con el activo a uno de diez biomas, y se plantan dos
  escenas con tres salidas: volverse o una de dos de las cuatro sendas (fuerza,
  velocidad, salud o ingenio), cada una `estadística + 1d20` contra la dificultad
  del bioma. Acertar lleva a la escena siguiente; fallar cierra el viaje. Lo
  hondo que se llegue decide qué se encuentra (un gachamon salvaje, un objeto o
  nada) y volver da +4 XP. La espera de 37 minutos es de la persona, no del
  gachamon. Las escenas las inventa el modelo de lenguaje, con escenas escritas
  por bioma de respaldo.
- **Reclutar.** Al salvaje hay que convencerlo en cuatro turnos de paciencia:
  hablarle, darle golosinas, presumir o esperar quieto. Cada opción suma a la
  confianza según el carácter de ambos más 1d8; a 100 se une, y a paciencia 0 se
  larga. Los dados deciden y el modelo sólo narra. Al unirse se pone un nombre él
  solo (`nombres.py`) y su dueño se lo puede cambiar una vez.
- **Competir.** Tres tramos, cada uno `estadística + 1d20`; gana quien sume más.
  Hay cuatro modalidades: la carrera (de dos a cinco), el sumo (de dos o de
  cuatro, con torneo), el asalto al tótem (de dos a cinco) y el laberinto de
  ecos (de dos a cinco, sólo con ingenio). Sólo el primero suma victoria y se
  lleva los +10 de XP; el resto, +4. Una poción activa puede inclinar la pelea:
  dura cinco minutos y su dado se tira al beberla, por eso sólo puede haber una
  activa por estadística. Cada modalidad deshace los empates a su manera, con un
  tope de intentos.
- **Conversar.** El gachamon contesta con su propio carácter y se acuerda de los
  últimos ocho intercambios, con un máximo de 20 mensajes por hora y por
  persona. Hablar no gasta comida ni da experiencia, y si se escribe con cuidado
  entrena el ingenio.
- **El ranking y el cementerio** (las criaturas vivas con más victorias, y las
  que ya no están) también esperan su pantalla.

Los detalles de cada una están en `aventura.py`, `competir.py`, `ia.py` y
`personalidad.py`. Mientras tanto no cuentan nada de lo que no pasa: la página
sólo promete lo que ya puede hacer.

## Cómo está montado

La lógica del juego vive en módulos **puros** que no importan `discord` y se
testean sin conexión. `web/` es un adaptador fino encima, y el bot, que ya sólo
vincula, es otro (`cogs/mudanza.py`).

| Fichero | Qué hace |
|---|---|
| `especies.py` | Las 25 especies, su arte ASCII por etapa, estadísticas y rarezas. |
| `personalidad.py` | La voz de cada especie, los diez caracteres y cómo se le explica todo al modelo. |
| `ia.py` | Cliente de IA (NVIDIA y DeepSeek). Async, con transporte inyectable. Hoy sin uso: conversar está en pausa. |
| `simulacion.py` | Decaimiento, acciones de cuidado, estadísticas y niveles. |
| `competir.py` | Resolución y narración de carreras, sumo, asaltos al tótem y laberintos de ecos (en pausa). |
| `objetos.py` | El catálogo de consumibles: precios, dados y qué hace cada uno. |
| `pantalla.py` | Los marcos de texto que usan `aventura.py` y `competir.py`. |
| `db.py` | SQLite. |
| `economia.py` | Monederos, topes UTC y operaciones económicas atómicas. |
| `economia_reporte.py` | Informe local agregado y reconciliación histórica. |
| `aventura.py` | Biomas, el árbol de decisiones, hallazgos y las reacciones de un salvaje (en pausa). |
| `retrato.py` | Qué criaturas tienen retrato en imagen y cuál les toca. |
| `cogs/mudanza.py` | El bot: `/vincular`, los avisos y la página del manual. |
| `web/` | El servicio de la página. |
| `fuentes/` | Las capas de los retratos: cuerpos, caras y sombreros. |

**Cómo se guarda el arte.** Cinco etapas por veinticinco especies, con tres
estados de ánimo cada una, serían 375 dibujos. Pero casi todos se diferencian
**sólo en la cara**: el mismo cuerpo de Piollito con `^v^`, `o.o` o `T_T`. Así
que cada etapa es una plantilla con un hueco `{cara}` y cada especie declara sus
tres caras: **125 dibujos y los ánimos salen gratis**. Donde el ánimo cambia más que la cara
—a Magora se le caen las hojas, la llama de Pyro mengua— se declara el dibujo
completo en `excepciones`, que gana a la plantilla. Las tres caras de una
especie tienen que medir lo mismo, o sustituir una por otra descuadraría el
dibujo; hay un test que lo comprueba.

**Los retratos en imagen.** Las especies que tienen dibujadas sus cinco formas
enseñan un PNG en vez del arte ASCII; el resto sigue en ASCII. Quién entra lo decide una
sola tupla, `retrato.CON_ETAPAS_COMPLETAS`.

En el repositorio viven **sólo las capas**, en `fuentes/`: un cuerpo por especie
y forma, tres caras y un cosmético por sombrero, todos sobre el mismo lienzo de
256×256, así que componer es apilar. El retrato **se arma en el momento de
enseñarlo**: se apilan las tres capas, se recorta a la caja que comparten las
veintiuna combinaciones de esa forma —para que cambiar de humor o de sombrero no
mueva al bicho— y se amplía al doble.

Cada capa se busca **de lo concreto a lo general**: por forma, por especie y
global. Lo de por forma hace falta cuando los cinco cuerpos de una especie son
dibujos distintos y no el mismo agrandado, porque entonces ni los ojos ni la
coronilla caen donde antes. Lo que no se puede es mezclar tamaños **dentro de
una misma especie**: apilar capas que no miden lo mismo revienta, y hay un test
que lo vigila.

Antes se guardaban los 1155 retratos ya compuestos, y se dejaron de guardar
cuando la cuenta empezó a doler: eran 27 MB camino de los 180 según se
redibujaban las especies, y se clonaban enteros en cada despliegue. Componer al
vuelo se pudo gracias a **Pillow**, y esa es la única razón de que sea
dependencia: medido en la Raspberry, apilar tres capas de 256×256 cuesta **1,7 s
en Python puro y 72 ms con Pillow**. Encima hay una caché en memoria de los
últimos 128 retratos armados, porque la misma combinación se pide una y otra vez.

**El catálogo.** Veinticinco especies repartidas en diez biomas, pero **del
huevo sólo salen diez**: las de siempre. Las quince nuevas hay que
encontrárselas en las aventuras (hoy en pausa), para que el comienzo sea conocido
y el catálogo grande sea lo que se descubre jugando.

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

El decaimiento es **perezoso**. No hay ningún bucle tocando cada mascota cada
minuto: se guarda cuándo se actualizó y el valor se calcula al leer. Como el
hambre baja de forma estrictamente lineal, basta con saber cuándo se
actualizó para saber cuánta lleva perdida. Por eso la suciedad castiga al
ánimo y no al hambre: si acelerase el hambre, dos barras cayendo a la vez se
acoplarían y la comida dejaría de ser predecible.

### La IA (en pausa)

`ia.py` y `personalidad.py` siguen en el repositorio para cuando conversar y las
escenas de las aventuras vuelvan a la página. Lo que ya está decidido:

- **La criatura nunca se queda muda.** Cada especie tiene frases escritas a
  mano que se usan si la API falla. Esas frases no entran en la memoria: si
  entraran, el modelo aprendería a repetirlas como si fueran suyas.
- **Los fallos de la API se tratan distinto según si tienen arreglo.** Un error
  permanente (un 400 de modelo degradado, un 404) no se reintenta: se pasa al
  siguiente modelo de `MODELO_IA` al instante.
- **Se prueban todos los modelos por turnos, no uno hasta agotarlo.** Tres rondas
  recorriendo la lista entera, con 30 s de tope por intento y 90 s para todo el
  proceso.
- **Un modelo que falla se aparta, pero nunca se le echa.** Cinco minutos, o
  treinta si el fallo fue permanente; mientras tanto va al final de la lista en
  vez de desaparecer, así que si fallan todos se siguen intentando todos.
- **Cada modelo lleva su proveedor delante** (`deepseek:deepseek-v4-pro`), y
  cada proveedor su URL, su clave y sus campos propios. Sin prefijo se asume
  NVIDIA, y los modelos de un proveedor sin clave se saltan solos.
- **Hay que apagar el razonamiento, y cada proveedor lo apaga a su manera.**
  NVIDIA con `chat_template_kwargs`, DeepSeek con un `thinking` de primer nivel:
  en DeepSeek viene encendido en `high` por defecto, se cobra como salida, y
  v4-pro se comería los 1200 tokens de `MAX_TOKENS` razonando sin llegar a
  contestar.

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

Cubren la distribución de rarezas y del 2d6, la curva de decaimiento, las
estadísticas, la resolución de competencias con dados fijos, la ida y vuelta
contra SQLite, y que **ningún marco se descuadre** en las 60 combinaciones de
especie, ánimo y etapa. El último es el que más veces ha salvado el proyecto: el
ASCII se rompe con una facilidad asombrosa.
