# Gachamon en la web — Parte A: cuidar y pasear

Diseño acordado con Felipe el 2026-11-12. Describe **qué** se construye y
**por qué**; el plan de tareas se escribe después, a partir de este documento.

En todo el texto, lo que decidió Felipe va marcado **[Felipe]** y lo que elegí
yo sin que él lo pidiera va marcado **[propuesta]**. Lo primero no se cambia sin
preguntarle; lo segundo se puede discutir.

## 1. Qué es esto y por qué

Gachamon vive hoy dentro de un canal de Discord. Felipe quiere sacarlo de ahí:
que se juegue en `rowino.online`, en una pestaña nueva, y después desde una app
de Android. Y quiere lo que Discord no deja hacer: acariciar al gachamon
tocándolo, un pueblo con lugares por el que te mueves, un avatar propio, y ver
al gachamon caminando contigo.

Es más de un proyecto. El orden acordado **[Felipe]**:

1. **El juego en la web.** Se entrega en dos partes:
   - **Parte A, cuidar y pasear** — este documento.
   - **Parte B, competir y explorar** — estadio, aventura, plaza, barrio y
     cementerio. Tendrá su propio diseño.
2. **App de Android y notificaciones.** Al terminar se apaga el bot de Discord.
3. **Pueblo compartido en vivo.** Ver a los demás caminando, retarlos y
   regalarles en persona.
4. **Eventos.** El visitante de la ventana y los que vengan.

Mientras la parte B no exista, quien viene de Discord **sigue jugando allá lo
que falte, sobre los mismos datos**. Quien nace en la web no tiene Discord
adonde ir: para esa persona la parte B simplemente todavía no existe (sección
5.2). El bot no se apaga hasta el final del proyecto 2, porque hoy el aviso de
hambre llega por Discord y sin él los gachamones se mueren sin que nadie se
entere.

La sección 8 guarda lo que Felipe ya dijo sobre los proyectos 2 a 4, para que
no se pierda.

## 2. Lo que decidió Felipe

- **Pantalla de entrada.** Al entrar ves el estado de tu gachamon y él te habla
  en un globo de texto: una necesidad («quiero jugar», «estoy sucio»), una
  charla («¿cómo estás?») o algo que depende de dónde estás.
- **Traspaso.** Los gachamones y sus dueños se pasan a `rowino.online`.
- **Un solo mundo.** El único servidor activo es Robot House. Ese es el pueblo
  de la web; los planteles de otros servidores no se traspasan.
- **El pueblo.** Un mapa general como el de Pokémon Stadium o Gran Turismo 7.
  Entre dos bocetos eligió el **pueblo ancho que se recorre**: es más grande
  que la pantalla y la cámara sigue al avatar.
- **Moverse.** Tocas un lugar y se ve a tu avatar y a tu gachamon caminando
  hasta ahí.
- **Avatar.** Eliges pelo, color de piel, ropa, nombre y género.
- **Arte.** Hay un dibujante en el proyecto. Por ahora todo va con arte de
  relleno.
- **Caricia.** Tocar al gachamon le sube el ánimo y salen corazones. Tiene
  enfriamiento: al segundo intento no salen corazones y no pasa nada.
- **Se abandona el ASCII.** Todo se muestra con dibujos. Los objetos ligados al
  ASCII desaparecen y a quien los tenía se le devuelve su valor.
- **Monedas.** Las asciicoins y las asciigems pasan a llamarse **monedas** y
  **gemas**.
- **Acceso.** Gachamon queda abierto a toda persona registrada en Rowino, sin
  que Felipe apruebe nada. Quien ya jugaba en Discord vincula esa identidad a
  su cuenta de Rowino en vez de empezar de cero.
- **Sin avisos no hay muerte.** Mientras no existan las notificaciones, el
  gachamon de una cuenta sin Discord no muere de hambre: se queda con la
  comida en 0 y de mal ánimo, pero vivo.
- **Pantalla principal.** Aprobó el boceto de la sección 5.3 tal como está.
- **En el computador** el pueblo se ve completo.

Felipe aceptó además estas cinco decisiones técnicas que le propuse:

- El código de la web vive **en este repositorio**, al lado de las reglas del
  juego, y corre en la Raspberry como **un servicio aparte de Rowino**.
- Se entra **con la sesión de Rowino**: el juego reconoce la misma cookie.
- Discord se vincula con **un código**: la web lo da y se escribe en Discord
  con un comando nuevo, `/vincular`.
- La web y el bot **leen y escriben la misma base de datos** mientras conviven.
- La parte visual se hace **sin frameworks ni paso de compilación**: un lienzo
  para el pueblo y HTML normal para lo demás.

## 3. Metas, no metas y lo que sería un fracaso

### Metas de la parte A

1. Cualquier cuenta registrada en Rowino entra a `rowino.online/gachamon` y
   juega el ciclo de cuidado completo sin tocar Discord.
2. Quien jugaba en Discord vincula su cuenta y encuentra **todo como lo dejó**:
   plantel, casas, muebles, huerto, mochila, ropero y saldo.
3. La web y el bot conviven sobre los mismos datos sin pisarse.
4. Hay un pueblo que se recorre con el avatar y el gachamon, y los lugares de
   la parte A funcionan.
5. Existen la caricia, los globos de texto y la conversación con el gachamon.
6. Todo el arte es de relleno y **se reemplaza cambiando archivos**, sin tocar
   código.
7. Las monedas cambian de nombre y se retiran los objetos ASCII devolviendo su
   valor.

### No son metas de la parte A

- Las competencias, la aventura, la plaza, el barrio y el cementerio. Son la
  parte B y, hasta entonces, se juegan en Discord.
- Las notificaciones y la app de Android (proyecto 2).
- Ver a otros jugadores en el pueblo (proyecto 3).
- Los eventos, incluido el visitante de la ventana (proyecto 4).
- Apagar el bot.
- El arte definitivo.
- Un chat de texto entre jugadores. **[propuesta]** No está previsto en ningún
  proyecto: Felipe no lo pidió y evita tener que moderar.

### Lo que sería un fracaso aunque funcione

- Que alguien pierda un gachamon, un objeto o saldo al pasarse a la web.
- Que la web y Discord apliquen reglas distintas. Las reglas viven en un solo
  sitio y las dos caras las usan. Hay **una sola excepción**, decidida por
  Felipe y con fecha de término: la de la muerte por hambre (sección 5.8).
- Que el juego se sienta como un panel de botones. La razón de todo esto es que
  el gachamon parezca vivo y que los lugares sean lugares.
- Que cambiar un dibujo obligue a editar código, o que una pieza que falta se
  sustituya en silencio por la de otra especie u otra etapa.
- Que un globo anuncie algo que no está pasando.

## 4. Restricciones

**Dónde corre.** Una Raspberry Pi con Ubuntu 24.04 y Python 3.12. Rowino es una
app FastAPI en el puerto 8000 y sale a internet por un túnel de Cloudflare. El
bot corre en la misma máquina como servicio `tamagotchi`, con su base SQLite
`tamagotchi.db` en el directorio del repositorio.

**Este repositorio.** Es público, tiene CI con Python 3.12 y 3.14, y recibe PRs
de otra persona. `AGENTS.md` manda. Lo que más pesa aquí:

- Los módulos puros del juego no importan `discord`. La web tampoco puede
  arrastrar esa librería.
- SQLite sigue síncrono; `db.py` posee el esquema y las transacciones; las
  mutaciones de juego o de dinero van bajo `BEGIN IMMEDIATE`.
- Dependencias directas con versión exacta, y ninguna nueva sin necesidad.
- Tiempo y azar inyectados en las pruebas.
- Nada de push, merge ni despliegue sin autorización de Felipe.

**Lo que ya existe y sirve.** La lógica del juego está en módulos sin Discord:
`simulacion`, `economia`, `db`, `especies`, `personalidad`, `ia`, `casas`,
`huerto`, `objetos`, `cosmeticos`, `logros`, `retrato`. Importan `discord`, y
por tanto **la web no puede importarlos**: `vistas`, `tienda`, `equipo`,
`comun` y todo `cogs/`. Si la web necesita lógica que hoy está atrapada en uno
de esos, se extrae a un módulo puro y la usan los dos.

**Identidad.** Todo el estado de una persona cuelga del par
`usuario_id` + `guild_id`, los dos guardados como texto.

**Rowino.** Vive fuera de este repositorio. Lo que hay que saber de él:

- **Sesión.** Una cookie `session` firmada con `itsdangerous`
  (`URLSafeSerializer(SECRET_KEY, salt="session")`) que lleva `{"uid": …}`. La
  clave está en el `.env` de Rowino.
- **Usuarios.** Tabla `users` de `rowino.db`: `id` entero, `username` único, y
  las marcas `approved`, `blocked`, `is_admin`. Una cuenta sin aprobar **sí**
  puede iniciar sesión; lo que Rowino le niega es generar imágenes. Una cuenta
  bloqueada no entra a nada.
- **Dónde está la base.** En la Pi, `rowino.db` vive junto al código de Rowino,
  en `~/rowino_web/`. Rowino y el bot corren con el mismo usuario de la
  máquina, así que el servicio nuevo puede leerla.
- **Entrar y registrarse.** `/login` y `/register`. Hoy, al terminar, mandan
  siempre a `/generar`: no aceptan una dirección de retorno.
- **Su código.** La copia de trabajo es `~/rowino` en el computador de Felipe,
  con git y sin remoto; la app es `rowino_web/`, tiene su propia suite de
  pytest y sus textos usan voseo. Se despliega con rsync sin borrar nada en el
  destino y con respaldo previo. **No se reinicia Rowino con trabajos de
  generación en curso**: se pierden.
- **Caché.** Cloudflare guarda `/static` durante cuatro horas.

**El túnel.** Se configura con un archivo en la Pi,
`/etc/cloudflared/config.yml`, que hoy reparte por nombre de host: todo
`rowino.online` va a Rowino. Cambiarlo pide `sudo` y reiniciar el túnel, lo que
corta unos segundos todos los sitios que salen por él.

**Pantalla.** Primero el celular en vertical. También tiene que verse bien en
la pestaña de un computador.

## 5. El diseño

### 5.1 Cómo encajan las piezas

```
                 rowino.online
                       │
               túnel de Cloudflare
              ┌────────┴─────────┐
        /gachamon/*          todo lo demás
              │                   │
   servicio gachamon-web      Rowino (:8000)
   (nuevo, en este repo)          │
              │               rowino.db ◄─── sólo lectura,
              │                              para saber quién eres
              ▼
        tamagotchi.db ◄──── bot de Discord (servicio tamagotchi)
```

- **Un paquete nuevo, `web/`,** con un servidor FastAPI y los archivos del
  cliente. Corre como servicio `gachamon-web`, escuchando sólo en la propia
  máquina, desde **el mismo directorio y el mismo entorno virtual que el bot**.
  Así un despliegue actualiza los dos a la vez y no pueden quedar con reglas
  distintas. **[propuesta]**
- **La ruta.** El túnel manda `rowino.online/gachamon/*` al servicio nuevo con
  una regla por ruta puesta antes de la regla general de Rowino. Si la regla
  por ruta diera problemas, el plan B es que Rowino reenvíe esa ruta. Hay que
  comprobarlo en la Pi antes de dar nada por hecho. **[propuesta]**
- **Rowino cambia poco:** un enlace «Gachamon» en su menú, visible para toda
  cuenta con sesión, y que el inicio de sesión y el registro acepten volver a
  `/gachamon/` al terminar —sólo a direcciones del propio sitio—. Esos cambios
  **son parte de este trabajo** **[propuesta]**: se hacen en `~/rowino`, con
  sus pruebas y con sus reglas de despliegue.
- **El túnel se prueba primero.** La regla por ruta es lo primero que se
  comprueba en la Pi, antes de ordenar el resto, porque de ella depende cuánto
  hay que tocar Rowino. Tocar el túnel pide la autorización de Felipe en el
  momento.
- **Quién eres.** El servicio lee la cookie `session`, la verifica con la misma
  clave que Rowino —la recibe por variable de entorno, nunca en el
  repositorio— y consulta `rowino.db` en modo de sólo lectura para saber el
  nombre de usuario y si la cuenta está bloqueada. No depende de que Rowino
  esté en marcha. Sin sesión válida, la página manda a iniciar sesión.
  **[propuesta]**
- **Los datos.** El servicio usa `db.py` y `economia.py` tal cual, contra el
  mismo `tamagotchi.db` que el bot. Toda mutación pasa por las funciones que ya
  existen y que ya se serializan con `BEGIN IMMEDIATE`. El servicio **no guarda
  estado del juego en memoria**: si lo hiciera, lo que cambie el bot no lo
  vería.
- **La forma de la API.** Una lectura de «estado» devuelve de una vez lo que la
  pantalla necesita: avatar, lugar, gachamon activo con sus barras ya
  avanzadas al instante de la consulta, esperas, saldos y las frases para los
  globos. Cada acción devuelve el estado nuevo. Cada acción lleva un
  identificador de evento generado por el cliente, porque las operaciones de
  `economia` ya son idempotentes por evento y así un toque doble o un reintento
  no cobra ni premia dos veces. El cliente refresca el estado cada cierto
  tiempo y al volver a la pestaña. **[propuesta]**

### 5.2 Cuentas, vinculación y avatar

**Identidad web.** Una cuenta de Rowino que nunca jugó en Discord recibe una
identidad propia, con el `guild_id` de Robot House —que el servicio lee de su
configuración—. Su `usuario_id` tiene que ser una cadena que **nunca pueda ser
un id de Discord**. **[propuesta]** el número de la cuenta de Rowino en
negativo (`"-12"`), con una sola función pura que responda «¿esta identidad es
de la web?». El esquema no cambia y una identidad web es una persona más, salvo por la
excepción de la muerte por hambre (sección 5.8).

**Vincular.** La primera vez que alguien entra, antes de cualquier otra cosa,
la web pregunta si ya jugaba en Discord.

- Si dice que sí, la web le muestra un código de un solo uso que caduca en
  pocos minutos. Lo escribe en Robot House con `/vincular <código>`. El bot
  sabe con certeza quién lo escribió, así que deja anotado que esa cuenta de
  Rowino **es** esa persona de Discord. Desde ahí la web actúa con el
  `usuario_id` de Discord y todo su estado aparece intacto.
- Si dice que no, se crea su identidad web y empieza de cero.

Reglas de la vinculación **[propuesta]**:

- Una cuenta de Rowino va con una sola identidad, y una identidad de Discord
  con una sola cuenta de Rowino.
- Sólo se puede vincular **mientras la identidad web no tenga gachamones**.
  Vincular después obligaría a fundir dos planteles, y eso no se construye. La
  pantalla lo explica con claridad antes de dejar empezar de cero.
- Deshacer o corregir un vínculo es cosa de Felipe, a mano.
- `/vincular` responde sólo a quien lo escribe, limita los intentos y no revela
  si un código existe.

**Quien nace en la web no pasa por Discord.** **[propuesta]** Es una
consecuencia de lo anterior y es deliberada: Discord es lo que se está dejando
atrás, así que no se construye nada para que una identidad web pueda usarse
desde el bot ni vincularse más tarde. Para esa persona, durante la parte A:

- Los lugares de la parte B están cerrados, sin alternativa.
- Tiene un solo gachamon, porque los demás sólo se consiguen en la aventura.
- Gana monedas cuidando y evolucionando, y nada más.

Los lugares cerrados se lo dicen con claridad, sin mandarla a Discord.

**El bot y las identidades web.** El bot recorre a todas las criaturas del
servidor para matar, avisar, pintar el jardín y armar el ranking, así que se va
a cruzar con gachamones cuyo dueño no existe en Discord. Regla: **el bot nunca
menciona a una identidad web**, y donde muestre al dueño usa el nombre de su
avatar. El aviso de hambre y el anuncio de muerte no se publican en el canal
para esas criaturas. Hay que revisar todos los sitios del bot que dan por hecho
un dueño de Discord.

**Avatar.** Después de vincular o empezar, y antes de ver el juego, se crea el
avatar **[Felipe]**: pelo, color de piel, ropa, nombre y género.

- El **nombre** es el que mostrará el juego en lugar del nombre de Discord, y
  el que verán los demás cuando exista el pueblo compartido. Pasa por la misma
  validación que el nombre de un gachamon.
- El **género** sirve para que los textos que hablan de la persona concuerden.
  **[propuesta]** dos opciones, las mismas que entiende hoy
  `especies.concordar`.
- **[propuesta]** el pelo se elige por forma y por color; la piel, por tono; la
  ropa, por conjunto completo. Con el arte de relleno bastan pocas opciones de
  cada una; el catálogo crece cuando el dibujante entregue piezas.
- **[propuesta]** el avatar se puede cambiar después desde el propio juego.
- El avatar es de la persona, no del gachamon: sobrevive a todo su plantel.

**Primer gachamon.** Quien llega sin plantel pasa por el huevo, igual que hoy:
se rompe, se ve qué salió con sus estadísticas, y se bautiza.

### 5.3 La pantalla principal: siempre estás en un lugar

Aprobada por Felipe sobre un boceto que funcionaba.

**La idea.** No hay un menú. Estás siempre en un lugar del pueblo, con tu
avatar y tu gachamon activo dibujados en grande dentro de ese lugar. El pueblo
es la forma de ir de un lugar a otro.

De arriba hacia abajo, en un celular en vertical:

| Franja | Qué muestra |
|---|---|
| Cabecera | El lugar donde estás, tus monedas y tus gemas. |
| Escena | El fondo del lugar, tu avatar, tu gachamon en grande y su globo de texto. |
| Ficha | Nombre, especie, etapa y nivel, y las tres barras: comida, ánimo y aseo. |
| Cuidados | Alimentar, jugar, entrenar y limpiar. |
| Del lugar | Las acciones propias de donde estás. |
| Navegación | Pueblo, mochila y hablar. |

- **Los cuatro cuidados van contigo a todos lados**, igual que la mochila y
  hablarle. No hay que volver a casa para darle de comer. **[propuesta,
  aprobada en el boceto]**
- Cada cuidado enseña su espera cuando la tiene. Las reglas, los
  enfriamientos, la experiencia y los premios son los de hoy, sin tocar.
- La ficha se abre para ver el resto: las cuatro estadísticas, experiencia,
  género, carácter, título, efectos activos y medallas.
- **Al abrir el juego apareces donde quedaste** la última vez. **[propuesta,
  aprobada en el boceto]**
- Subir de nivel y evolucionar se celebran en la escena, y al evolucionar
  cambia el dibujo.
- Si el gachamon activo murió mientras no estabas, lo primero que ves es eso:
  quién era y cuánto vivió. Después sale el siguiente de la incubadora, o el
  huevo si no queda ninguno, como ya hacen las reglas.
- **En un computador** el pueblo se ve completo (sección 5.4) **[Felipe]**.
  La pantalla de un lugar aprovecha el ancho: la escena a un lado, y la
  ficha, los cuidados y las acciones al otro. **[propuesta]**

### 5.4 El pueblo

Elegido por Felipe entre dos bocetos que funcionaban.

- **En el celular**, el pueblo es **más ancho que la pantalla**. La cámara
  sigue al avatar y se puede arrastrar para mirar. Unas flechas avisan cuando
  hay más pueblo hacia un lado.
- **En un computador se ve el pueblo completo** **[Felipe]**: cabe entero en
  la pantalla, sin cámara que seguir ni nada que arrastrar. Es el mismo
  pueblo y los mismos caminos; lo único que cambia es cuánto se ve de una vez.
- Los lugares están unidos por **caminos**. Tocas un lugar y el avatar va por
  el camino más corto.
- **El gachamon te sigue**, un trecho detrás, por el mismo camino. Avanza a
  saltitos y mira hacia donde se mueve.
- Sobre el destino hay una marca mientras caminas. Si tocas otro lugar a mitad
  de camino, cambias de rumbo desde donde estás.
- **Un segundo toque te lleva de inmediato.** **[propuesta]** En el boceto, la
  caminata más larga duraba seis segundos; es agradable la primera vez y un
  estorbo la décima.
- Al llegar, **entras**: la pantalla pasa a la escena del lugar y el gachamon
  dice algo sobre él.
- El pueblo, sus caminos y sus lugares se describen **en datos, no en código**:
  dónde está cada lugar, qué caminos los unen y qué dibujo lleva cada uno.
  Agregar un lugar o redibujar el pueblo no toca la lógica.

Los nueve lugares **[propuesta, aprobada en los bocetos]**:

| Lugar | Qué es en el juego de hoy | Parte |
|---|---|---|
| Tu casa | Casas propias, muebles, huerto, buzón | A |
| Refugio | Donde vive quien no cabe en una casa | A |
| Incubadora | El plantel y el cambio de activo | A |
| Tienda | Objetos, cosméticos, casas y muebles | A |
| Plaza | `/jardin` | B |
| Barrio | `/visitar` y regalar | B |
| Estadio | Las cuatro competencias y el ranking | B |
| Cementerio | `/cementerio` | B |
| Salida a la aventura | `/aventura` | B |

Los lugares de la parte B **están en el pueblo desde el primer día** y se puede
caminar hasta ellos, pero al entrar avisan que se abren más adelante. A quien
tiene Discord vinculado le recuerdan que, por ahora, eso se juega allá; a quien
nació en la web, sólo que todavía no está.

### 5.5 Los lugares de la parte A

Las reglas de todo esto ya existen en `economia`, `casas`, `huerto`, `objetos`
y `cosmeticos`. Lo nuevo es la pantalla.

**Tu casa.**
- Con una casa, entras a ella. Con varias —se pueden tener hasta tres— eliges a
  cuál. Sin ninguna, el lugar es un sitio vacío que te manda a la tienda, y tu
  hogar es el refugio.
- La escena es el interior de **esa** casa, con los muebles que tiene puestos y
  los gachamones que viven en ella.
- Acciones: el **huerto** de esa casa (plantar, regar, cosechar y cocinar),
  los **muebles** (colocar y retirar), **mudar** gachamones entre tus casas y
  el refugio, y el **buzón** con los regalos recibidos.

**Refugio.** Quiénes de los tuyos viven ahí y cómo va tu reloj del refugio. No
se amuebla ni tiene huerto.

**Incubadora.** Tu plantel entero, el cambio de gachamon activo, el bautizo de
los que llegaron sin nombre y el huevo de partida para quien no tiene ninguno.

**Tienda.** Objetos con monedas; cosméticos con gemas; casas para comprar,
mejorar y vender; muebles. De los cosméticos quedan sólo los sombreros y los
títulos (sección 5.8).

**En cualquier lugar.**
- **Mochila:** usar lo que llevas.
- **Ropero:** poner y quitar el sombrero y el título del gachamon activo.
  **[propuesta]** se abre desde la ficha.
- **Hablar:** sección 5.7.

### 5.6 La caricia

**[Felipe]** Tocas a tu gachamon en la escena. Sube el ánimo, salen corazones
y él reacciona. Tiene enfriamiento. Si lo tocas antes de tiempo, no salen
corazones y no pasa nada.

- La caricia es una regla del juego, no un adorno del cliente: el servidor
  decide si cuenta y guarda el enfriamiento **por gachamon**, junto a los
  demás.
- **[propuesta]** No da experiencia ni monedas y no cuenta para el tope diario.
  Si diera, sería una máquina de premios pegada a un dedo.
- **[propuesta]** Antes de tiempo el gachamon apenas se mueve y la pantalla
  dice cuánto falta, pero no aparece ningún mensaje de error.
- **[propuesta]** De partida, +5 de ánimo cada 20 minutos. Son dos constantes y
  se ajustan jugando. El criterio: que acariciar sea un gesto de cariño y no
  reemplace a **jugar**, que es lo que de verdad levanta el ánimo y entrena la
  velocidad.

### 5.7 Los globos y la conversación

Son dos cosas distintas.

**Los globos son lo que el gachamon dice por su cuenta** **[Felipe]**. Por
orden de prioridad:

1. **Una necesidad**, cuando una barra está baja: hambre, mugre o ganas de
   jugar.
2. **Algo del lugar**, al llegar.
3. **Charla suelta**, de vez en cuando: «¿cómo estás?», «vi un ovni».

- **[propuesta]** Los globos son **frases escritas, no inteligencia
  artificial**. Tienen que aparecer al instante y sin costo, y un globo cada
  medio minuto por jugador agotaría el límite de IA en una tarde.
- Las frases viven en un módulo puro con las marcas de concordancia de siempre
  y pasan por el mismo test que impide que una marca llegue sin resolver.
- **[propuesta]** Hay un fondo común de frases y cada especie puede tener las
  suyas, que mandan sobre las comunes. Así el Piollito sigue diciendo «pío»
  sin exigir veinticinco juegos completos de frases desde el primer día.
- No se repite la misma frase dos veces seguidas, y el gachamon no habla sin
  parar: entre un globo y otro pasa un rato.
- **El globo de la ventana no entra en la parte A.** Pertenece al evento del
  proyecto 4, y un globo no anuncia lo que no está pasando.

**Hablar es la conversación de hoy**, la de mencionar al bot. Se le escribe y
contesta con la voz de su especie y su carácter, usando la IA. Mismas reglas:
el historial reciente, el límite por persona y por hora, las frases de respaldo
cuando la IA falla, y el ingenio que se entrena hablándole bien. Lo que el bot
hace hoy dentro de `cogs/charla.py` se extrae a una función sin Discord que
usan los dos.

### 5.8 Lo que cambia en el juego

Estos cambios son de las reglas, así que **se ven también en Discord** mientras
el bot siga vivo.

**Monedas y gemas.** **[Felipe]** Todo texto que vea un jugador dice «monedas»
y «gemas»: la web, el bot y el manual publicado. **[propuesta]** Los nombres
internos del código y de la base pueden quedarse como están; renombrarlos es un
cambio grande que no le da nada al jugador.

**Se retiran los objetos ASCII.** **[Felipe]** el principio; **[propuesta]** el
detalle, que Felipe revisó y aprobó:

| Cosmético | Qué pasa | Devolución |
|---|---|---|
| Marcos (3) | Se retiran: son bordes hechos con caracteres | 50 gemas por cada uno |
| Tintes (8) | Se retiran: son los colores de texto de Discord | 20 gemas por cada uno |
| Sombreros (6) | Se quedan: ya tienen dibujo | — |
| Títulos (6) | Se quedan: son texto | — |

- Salen del catálogo y de la tienda.
- Una migración recorre los roperos una sola vez: por cada marco o tinte que
  alguien tenga acredita su precio en gemas, lo saca del ropero y se lo quita a
  cualquier gachamon que lo lleve puesto.
- La devolución deja su registro contable, va fuera de cualquier tope y **no
  puede pagarse dos veces** aunque la migración se repita.
- Antes de correrla se respalda la base.

**Sin avisos no hay muerte.** **[Felipe]** Quien nace en la web no tiene
Discord que le avise del hambre, y las notificaciones llegan recién en el
proyecto 2. Hasta entonces, su gachamon **no muere de hambre**: la comida
llega a 0 y ahí se queda, de mal ánimo, pero vivo.

- **A quién alcanza.** Sólo a los gachamones de una identidad web. Quien
  vinculó su cuenta de Discord sigue recibiendo el aviso allá y su gachamon
  muere como hoy. **[propuesta]**
- **Cómo encaja.** Igual que la incubadora: a esas criaturas no se les guarda
  instante de muerte ni de aviso, que es lo único que miran los bucles del
  bot. Las barras siguen bajando con las reglas de siempre. **[propuesta]**
- **No es una ventaja.** Descuidar al gachamon no da nada: alimentar no
  cuesta monedas, y las reglas de hoy ya castigan el hambre —por debajo de
  30 de comida pone mala cara, y por debajo de 20 no puede competir ni salir
  de aventura—. No hace falta inventar un castigo nuevo. **[propuesta]**
- **Se ve.** Con la comida en 0 la ficha y los globos dicen que está
  desfallecido y pide comer. El juego no lo presenta como inmortalidad.
  **[propuesta]**
- **Termina.** La excepción se acaba cuando esa persona tenga notificaciones
  (proyecto 2). Ese día el reloj del hambre **empieza a contar desde ese
  momento**: nadie muere de golpe por el hambre que traía acumulada.
  **[propuesta]**
- Es una regla duradera mientras dure, así que entra en `AGENTS.md`.

**Todo con dibujos.** **[Felipe]** La web no enseña ASCII en ningún sitio.

- Las once especies que ya tienen sus cinco formas dibujadas usan sus capas de
  `fuentes/`, armadas como hoy.
- Las otras catorce llevan un **dibujo de relleno** que se nota que lo es, con
  el color y el nombre de la especie, hasta que el dibujante las entregue.
- El bot sigue pintando como hoy mientras exista. No se le quita el ASCII: se
  apaga entero al final del proyecto 2.

**Cosas nuevas que se guardan:** la cuenta web y su vínculo, los códigos de
vinculación pendientes, el avatar, el lugar donde está cada persona y el
enfriamiento de la caricia.

**`AGENTS.md`** se actualiza en el mismo cambio que introduzca cada regla
duradera nueva.

### 5.9 El arte de relleno y cómo se reemplaza

El dibujante trabaja en paralelo y no toca código. Para eso hay un **contrato
de arte**: un documento, en este repositorio, que dice para cada pieza cómo se
llama el archivo, dónde va, qué tamaño tiene y qué cuadros lleva. Lo escribe
quien construye, junto con las piezas de relleno, y es parte de la entrega.

Lo que el contrato tiene que cubrir:

| Pieza | Notas |
|---|---|
| Gachamones | El formato de capas de hoy: cuerpo por especie y forma, tres caras, sombreros. No cambia. |
| Avatar | Por capas: cuerpo según el tono de piel, pelo según forma y color, ropa según conjunto. Quieto y caminando. Se dibuja mirando a un lado y se refleja para el otro. |
| Pueblo | El fondo y el dibujo de cada lugar. |
| Escenas | El fondo de cada lugar por dentro. |
| Muebles | Cada mueble, para verlo puesto en la casa. |
| Objetos y cosméticos | El ícono de cada uno, para la tienda, la mochila y el ropero. |
| Efectos | Los corazones de la caricia y las celebraciones. |

Reglas del relleno:

- **El relleno se nota.** Nadie debe confundirlo con arte terminado.
- **Si falta un archivo, se ve el relleno de esa pieza**, nunca el dibujo de
  otra especie, otra etapa u otro objeto. Y queda anotado en el registro.
- **Reemplazar es cambiar el archivo.** Un test recorre el contrato y avisa de
  lo que falta y de lo que no mide lo que debe.
- Como Cloudflare guarda los archivos estáticos cuatro horas, cada dibujo se
  pide con una marca de versión, para que un cambio se vea al momento.
- El gachamon camina **a saltitos con su retrato de siempre**. No hay que
  dibujar una caminata por especie y por forma.

### 5.10 Pruebas

- **Reglas nuevas** —caricia, globos, vinculación, devolución de cosméticos y
  la excepción de la muerte por hambre—:
  en módulos puros, con pytest, con el tiempo y el azar inyectados.
- **El servidor web:** pruebas contra una base temporal, con una sesión
  fabricada con una clave de prueba. Tienen que cubrir que nadie actúa sobre el
  gachamon de otro y que repetir un evento no paga dos veces.
- **La convivencia:** una prueba con dos conexiones a la misma base, una
  haciendo de bot y otra de web, que se cruzan.
- **El cliente:** la lógica que se puede probar sin pantalla —el camino más
  corto, el seguimiento del gachamon, la cámara— se prueba aparte del dibujo.
- La CI sigue corriendo todo en 3.12 y 3.14.

### 5.11 Puesta en marcha

En este orden, para poder parar en cualquier paso:

1. Respaldo de la base.
2. Se despliegan los cambios de reglas y el bot: el nombre de las monedas, la
   devolución de marcos y tintes y `/vincular`.
3. Se levanta el servicio web **sin enlace en Rowino**. Felipe lo prueba con su
   propia cuenta, vinculada a su identidad de Discord.
4. Se agrega el enlace «Gachamon» al menú de Rowino y se avisa en el canal.

Los scripts de despliegue de este repositorio pasan a actualizar y reiniciar
los dos servicios.

## 6. Lo que queda para quien construye

- Las rutas exactas de la API y la forma de cada respuesta.
- El esquema de las tablas nuevas y sus migraciones.
- Cómo se extrae de `vistas`, `tienda`, `equipo`, `comun` y `cogs` la lógica
  que la web necesita y hoy vive pegada a Discord.
- Si se activa el modo WAL de SQLite para que conviva mejor con dos procesos.
- La forma exacta del identificador de una identidad web.
- Los números de partida de la caricia y el ritmo de los globos.
- Cómo se ve el relleno, cuántas opciones de avatar trae y los tamaños del
  contrato de arte.
- El detalle de cada pantalla que este documento no fija, incluido cómo se
  reparte la pantalla de un lugar en un computador y a partir de qué ancho se
  deja de mover la cámara.
- Cómo se protege la API de peticiones que no vengan de la propia página.

## 7. Riesgos conocidos

- **Registro abierto.** Cualquiera puede crearse una cuenta y hablarle al
  gachamon, y eso gasta IA. Hay un límite por persona; **[propuesta]** se
  agrega un tope global por hora para que muchas cuentas no agoten el servicio
  entre todas.
- **La regla por ruta del túnel** está sin probar en esta Pi.
- **Dos procesos sobre una base SQLite.** Las transacciones ya están pensadas
  para la concurrencia, pero hasta hoy había un solo proceso.
- **El repositorio es público.** Este documento lo será cuando se suba.

## 8. Lo que viene después

Dicho por Felipe en la misma conversación. No se construye en la parte A.

**Proyecto 2 — app de Android y notificaciones.** La app avisa cuando el
gachamon tiene hambre y cuando encontró algo relacionado con un evento.
**[propuesta]** la app es el mismo juego de la web empaquetado como app
instalable. Con las notificaciones termina la excepción de la muerte por
hambre (sección 5.8).

**Proyecto 3 — pueblo compartido en vivo.**
- Ves el avatar y el gachamon de los demás conectados, caminando por el mapa.
- Hay un tope de jugadores visibles para no saturar la imagen.
- Al tocar a otra persona puedes retarla o regalarle algo.
- El regalo en persona **entra directo al inventario si el otro acepta**.
- Aceptado por Felipe como propuesta: el reto incluye las cuatro competencias;
  no hay chat; el tope ronda los doce visibles, los más cercanos; a quien retas
  le salta un aviso para aceptar; desde el estadio se puede retar a alguien
  desconectado; el buzón queda para cuando pasas por la casa de alguien que no
  está.

**Proyecto 4 — eventos.** En tu casa puede aparecer en la ventana un gachamon
que **sólo se consigue así**, atraído por los porotos del balcón. Tu gachamon
te avisa con un globo: «creo que hay alguien en la ventana». **[propuesta]** se
le convence con el mismo juego de confianza y recelo de los salvajes.

## 9. Los bocetos

Los dos bocetos que Felipe probó están en `2026-11-12-bocetos/`. Son
desechables: sirven para ver cómo se comporta el pueblo y la pantalla
principal, no como base del código.
