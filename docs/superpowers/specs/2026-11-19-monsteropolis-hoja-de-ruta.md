# Monsteropolis — la hoja de ruta

Gachamon se convierte en **Monsteropolis**. La visión es el documento de diseño
del dueño («Monsteropolis», versión 1.23), que no vive en este repo. Este
archivo dice **en qué orden se construye** y **qué cambia respecto de lo
publicado**. Corrige y reemplaza la sección 12 del diseño del rediseño
(`2026-11-14-gachamon-rework-1-departamento-design.md`) y el renglón «siguen sin
hacer» de los pendientes.

Escrito el 2026-11-19, con el rediseño (el proyecto 1) ya publicado. Cada
proyecto tendrá su propio diseño en esta carpeta antes de construirse; aquí no
se fija ningún detalle que ese diseño tenga que decidir. Antes de escribir cada
diseño se vuelve a leer el documento del dueño, que sigue cambiando.

## Reglas que valen para todo

- La ciudad se llama Monsteropolis y sus habitantes son **criaturas**, nunca
  «monstruos»: esa palabra sólo existe dentro del nombre propio.
- La criatura nunca muere. No hay cría entre jugadores. Las criaturas no se
  compran: llegan de afuera, por amistad, o de eventos.
- **Sin IA en nada**: lo que se narra y lo que una criatura contesta sale de
  frases escritas y de un sorteo reproducible (misma entrada, misma salida), y
  todo se prueba sin red.
- Canvas 2D con módulos de JavaScript propios, sin bibliotecas de dibujo; el
  servidor sigue siendo el de este repo, con SQLite.
- El juego sigue en la misma página; un dominio propio queda para después.

## Quién decidió qué

- **Del documento de diseño del dueño**: la visión entera, las reglas de arriba
  y el orden de los proyectos 1b a 6.
- **Del dueño, preguntado el 2026-11-19**:
  - después de una tanda corta van primero las herramientas del dibujante;
  - el nombre se cambia dentro del juego pronto, antes de las aventuras, en un
    plan propio cuyos textos aprueba él;
  - la comodidad se construye como dice su documento, tal cual, sin revisión
    previa de números; reemplaza lo que eligió el 2026-11-18 (un mueble sostiene
    su barra en 40, sin acumular);
  - el logro de haber estado desde el principio paga 5 gemas, no 25;
  - en un computador la página aprovecha toda la pantalla, sin franjas a los
    lados;
  - la limpieza técnica que quedó anotada se hace;
  - entran a la cola el huerto en el balcón, el cementerio para explorar, la
    Plaza y el Barrio, y el arte de verdad;
  - las tres herramientas del dibujante (abajo, proyecto A).
- **Propuesto aquí, no decidido por el dueño**: adelantar el contador de
  afinidad (se junta por días: mientras antes cuente, antes sirve), juntar los
  ajustes del departamento en un proyecto (1c) y dejar la aplicación de
  teléfono, que su documento no nombra, para el final.

## El orden

| | Proyecto | Qué trae |
|---|---|---|
| 0 | Tanda corta (hecha en su rama) | Las 5 gemas, la pantalla completa en un computador y la limpieza técnica |
| A | Herramientas del dibujante | El botón de Monsteropolis en la portada del sitio, la página para subir imágenes y el tablero del arte |
| B | El nombre | Monsteropolis y «criaturas» en toda la página |
| 1b | Aventuras y reclutar | Las salidas afuera con energía, y unirse por amistad, sin IA |
| 1c | El departamento según el documento | La comodidad como piso, los muebles que se acumulan, la consola que se juega, la cama de cada criatura, liberar y el contador de afinidad |
| 2 | Balcón y huerto | El balcón de 4 casillas pegado a una pared; sin balcón no hay huerto |
| 3 | El pueblo y sus lugares | Todo en isométrico; el edificio de viviendas con sus pasillos; el municipio y su alcalde; el cementerio para explorar; qué son la Plaza y el Barrio |
| 4 | Gente en vivo | Ver a otros, globos de texto, visitas; departamentos libres, con contraseña o con timbre |
| 5 | Objetos para jugar e intercambio | La mesa de gato, el atril, los teletransportadores, los cableados y los muebles nuevos |
| 6 | Competir y conversar | Las batallas que se preparan y no se dirigen, y conversar sin IA; se apaga el bot |

Después, sin orden todavía: los eventos y los huevos sellados, la evolución por
afinidad y por evento, y la aplicación de teléfono. El arte de verdad no es un
proyecto: entra pieza a pieza por las herramientas del proyecto A.

## Lo que cambia respecto de lo publicado

| Tema | Hoy en la página | Lo que dice el documento del dueño | Proyecto |
|---|---|---|---|
| El nombre | «Gachamon» y «gachamones» en todos los textos | Monsteropolis y «criaturas» | B |
| La comodidad | Parte de 80; cada tipo de mueble suma una vez; sólo frena la caída del ánimo | Parte de 0; cada pieza puesta suma; es un piso para la comida, el ánimo y el aseo | 1c |
| Los muebles que se usan solos | Uno basta y sostiene su barra en 40; dos no hacen más | Cada unidad suma 30 de piso a su barra, y se acumulan | 1c |
| La consola | Un mueble sin juego | Dos consolas que se juegan en su propia pantalla | 1c y 5 |
| La cama | Una cama que hace falta no se guarda | Es la cama de una criatura: guardarla avisa, y la criatura se va para siempre | 1c |
| Liberar | No existe | Se libera desde el departamento, con una despedida según la afinidad | 1c |
| La afinidad | No existe | Un punto por cada día en que se la cuidó; el nivel es la raíz de esos días, hasta 10 | 1c |
| La evolución | Por nivel | Por afinidad y por evento | después |
| Las zonas de afuera | Diez | Nueve (no nombra las Cavernas) | 1b |
| La energía | No existe | Cada salida la gasta; vuelve con el tiempo o con la vida en la ciudad | 1b |
| Narrar y conversar | El bot usaba un modelo de lenguaje | Frases escritas, sin IA | 1b y 6 |
| El primer cuidado | El logro de haber estado desde el principio paga 25 gemas | 5 gemas (lo dijo el dueño el 2026-11-19; no es del documento) | 0 |

### La comodidad, como quedó escrita

Se construye tal cual, por decisión del dueño:

- la comodidad sale sólo de las piezas puestas, cada una con la suya, se repitan
  o no; parte de 0;
- su tope depende de las casillas: `100 + 50 × √((casillas − 9) ÷ 55)`, 100 en
  3 × 3 y 150 en 8 × 8;
- fija un piso para la comida, el ánimo y el aseo de todas las criaturas del
  departamento: `90 × √(comodidad ÷ 150)`;
- cada mueble que se usa solo suma 30 al piso de su barra, y se acumulan hasta
  un tope propio, `90 × √(comodidad ÷ 150)`;
- el piso de cada barra es `min(90, piso de la comodidad + piso de sus
  muebles)`;
- nunca se enseña con «%».

Lo que su diseño tiene que medir y contarle al dueño, sin frenar la
construcción: con el piso alto casi nunca hace falta cuidar, y cuidar es lo que
hoy da monedas y hace crecer.

## Cada proyecto, en corto

### 0 · Tanda corta

- El logro de haber estado desde el principio pasa de 25 gemas a 5. Lo ya pagado
  no se toca.
- En un computador la página ocupa toda la ventana.
- Limpieza que no ve quien juega: los documentos generados que nombran funciones
  que ya no existen, un router que importa de otro, un comentario viejo, sacar el
  «transporte» de la pantalla del departamento a su módulo y dejar en el repo la
  herramienta para levantar una página de prueba.

### A · Herramientas del dibujante

Pedido del dueño el 2026-11-19. Son tres cosas, y dos viven en la aplicación del
sitio, que es otro repo:

- un botón de Monsteropolis en la portada del sitio;
- un botón que sólo ven el dueño y el dibujante, con una página donde se suben
  las imágenes que reemplazan a los recuadros provisionales. Las piezas, sus
  nombres y sus medidas son las del contrato del arte (`web/arte.py`);
- un tablero como el que el sitio ya tiene para otro proyecto —tarjetas,
  calendario, hoja de ruta e historial—, con las imágenes que el dibujante tiene
  que hacer.

Por decidir en su diseño: quién puede subir y cómo lo sabe la página; si una
imagen subida se ve en el juego al momento o cuando el dueño la aprueba; dónde
se guarda para que un despliegue no la borre; y cómo llega al repo.

### B · El nombre

Monsteropolis en el título y «criatura» en cada frase que hoy dice «gachamon»,
con sus concordancias. Todas las frases las aprueba el dueño. Por decidir en su
diseño: la dirección de la página y los nombres internos (claves, tablas y
archivos), que en principio no cambian.

### 1b · Aventuras y reclutar

Las salidas a las zonas de afuera, en solitario, con energía; el encuentro con
una criatura salvaje, que se une por amistad si hay cama libre; y todo narrado
con frases escritas. La mecánica de confianza y recelo no cambia; «hablar» se
abre en temas, cada uno con su reacción según el carácter. Por decidir en su
diseño: las cifras de la energía, si las Cavernas siguen, y qué se hace con la
regla de cambiarle el nombre una vez a un recluta.

### 1c · El departamento según el documento

La comodidad y los muebles que se acumulan (arriba); la consola pasa a ser la
que se juega; cada cama es de una criatura y guardarla la despide, con aviso;
liberar criaturas; y el contador de días cuidados de la afinidad, que empieza a
contar aunque sus efectos lleguen después. Por decidir en su diseño: cómo se
reparte una cama a cada criatura que ya vive ahí, y las frases de despedida.

### 2 a 6

Como en la tabla. De lo que el dueño ya había dicho de ellos sigue valiendo la
sección 12 del diseño del rediseño, salvo donde su documento dice otra cosa: el
atril ya no pide marcos comprados (el dibujo se cuelga como cuadro) y las
batallas del proyecto 6 se preparan y no se dirigen.

## Lo que queda abierto

- Cómo se entrena el ingenio cuando conversar ya no lo juzga un modelo.
- El nombre y la identidad de quien organiza los torneos.
- Si hay tope de cableados por departamento, y sus precios.
- Los precios y la comodidad de los muebles nuevos que su documento deja «por
  definir».
