# Rework 4 · La vivienda por casillas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que cada persona tenga un solo departamento por casillas —con sus muebles puestos o guardados, sus camas y su comodidad— en vez de casas compradas, refugio e intemperie, y que el día del cambio nadie pierda nada.

**Architecture:** Primero el departamento como módulo puro (`departamento.py`: el catálogo con la forma de cada mueble, qué cabe dónde, la comodidad, las camas, cuánto cuesta ampliar). Después su sitio en la base, y el ritmo del tiempo pasa a salir de él. Encima van las reglas (comprar, poner, guardar, ampliar), el límite de las camas, y el día del cambio: un paso de una sola vez, en una transacción, que convierte lo de cada quien y le deja escrita su carta del alcalde. Al final salen de la página y del código las casas, el refugio, la intemperie y el huerto por casa. La pantalla del departamento no es de este plan: aquí queda todo listo en el servidor, con sus rutas.

**Tech Stack:** Python 3.12, FastAPI, SQLite síncrono, JavaScript sin framework, pytest y `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-14-gachamon-rework-1-departamento-design.md` (secciones 3, 4.1 a 4.3, 6, 8 y 9). Inventario del código de hoy, con archivo y línea: `.superpowers/sdd/2026-11-15-gachamon-rework-4-reconocimiento/inventario.md` (no va en el repo).

**Dónde encaja.** Es el plan 4 de **8** del proyecto 1 del rework: (1) nadie muere — hecho; (2) el tiempo para todos — hecho; (3) el bot en pausa — hecho; (4) la vivienda por casillas y el día del cambio; (5) partir sin gachamon; (6) el departamento en pantalla; (7) los muebles que se usan solos; (8) el pueblo sin Refugio ni Incubadora y los documentos. Todos se juntan en la rama `rework/1-departamento` y **se publican juntos al final**.

**Lo que no entra, y dónde va.** Partir sin gachamon, sin huevo y con el monedero en 0, la primera aventura y que todo funcione sin ningún gachamon (tienda, mochila, ropero, estado): plan 5. **Mientras tanto el huevo sigue existiendo y el que nace de él no pide cama.** La pantalla del departamento (dibujar la pieza, mover, girar, la carta en pantalla, «Salir con él»): plan 6. El refrigerador, la consola, la ducha y las pesas: plan 7. Quitar del mapa el Refugio y la Incubadora y llamar «Tu departamento» a «Tu casa»: plan 8. El balcón y el huerto nuevo: proyecto 2.

## Global Constraints

- Nada se sube, se fusiona ni se despliega: todo queda en la rama local `rework/1-departamento`.
- Los módulos de juego no importan `discord`; `web/` no importa `discord` ni nada que lo importe; `db.py` no importa `economia.py`. `departamento.py` es puro: sólo importa `simulacion`.
- Cada cambio de estado va en su transacción `BEGIN IMMEDIATE`, dentro de `db.py`, `economia.py` o `nacer.py`. `web/` es un adaptador fino: ninguna ruta acepta un identificador de persona y el servicio no guarda estado del juego en memoria.
- **El servidor manda**: qué mueble hay en qué casilla lo valida y lo guarda el servidor.
- **Lo que mueve monedas lleva un evento** (comprar un mueble, ampliar): repetirlo devuelve lo de la primera vez y no cobra ni entrega otra vez. Poner y guardar se pueden repetir tal cual.
- **Antes de cambiar lo que fija el ritmo de alguien** (poner o guardar un mueble, ampliar) se pone al día y se guarda a todos sus gachamones vivos, en esa misma transacción: el ritmo se aplica hacia atrás a todo el tiempo sin guardar.
- Una devolución no es una ganancia: no pasa por el tope diario ni por `operaciones_economia`.
- **No se borra ninguna tabla ni columna**: `casas_propias`, `mobiliario`, `huerto`, `hogar`, `buzon` y `criaturas.casa_id` siguen en el esquema, y `_migrar_casas` sigue corriendo (una base vieja tiene que poder llegar hasta el día del cambio).
- Sin dependencias nuevas. Dominio determinista: el tiempo y el azar se inyectan en las pruebas.
- Nunca se abre `tamagotchi.db` ni `.env`; las pruebas usan bases temporales e ids sintéticos (`"u1"`, `"g1"`…). El repo es público: sin IPs, ids de personas ni secretos.
- Antes de editar un símbolo, GitNexus `impact` (si devuelve CRITICAL con una lista de símbolos del JavaScript que no tiene que ver, es una resolución de nombre equivocada: se contrasta con `git grep` y se anota). El índice se refresca sólo con `node .gitnexus/run.cjs analyze --index-only`.
- Cada commit: `./venv/bin/python -m pre_commit run --all-files && git diff --check && git add -A && git diff --cached --check && git commit -m "…"`, y termina con la línea de coautoría de la sesión que lo escribe.
- A quien juega se le dice «monedas» y «gemas»; la comodidad nunca se enseña con `%`.
- **Regla de las pruebas de este plan.** Una prueba de una regla que se va (comprar o vender una casa, mudar, el refugio, la intemperie, el ticket, plantar, regar, cosechar, el mueble «uno de cada») se **borra** con ella. Si además era la única que llegaba a algo que se queda (el monedero, los eventos, cocinar, el buzón, `_migrar_casas`), se **reescribe** contra lo que se queda. Las tareas 7 y 8, que son las que borran, miden la cobertura **por ramas** antes y después y dicen en su informe, archivo por archivo, cuántas borraron y cuántas reescribieron.
- **Frases nuevas** (se le enseñan a Felipe al confirmar el plan; van tal cual; `{monedas}` lleva su palabra con `obj.nombre_de_monedas`):
  - Tienda, al comprar un mueble: `Compraste {nombre}. Quedó en tus guardados.`
  - Hacer algo del departamento sin estar en él: `Para eso tienes que estar en tu departamento.`
  - Poner donde no cabe: `Ahí no cabe.` · Poner donde hay otra cosa: `Ahí ya hay algo.` · Un mueble que no es tuyo: `Ese mueble no es tuyo.`
  - Guardar una cama que hace falta: `Esa cama hace falta: sin ella alguien se queda sin dónde dormir.`
  - Ampliar: `Tu departamento ahora mide {ancho} × {fondo}.` · Ya en el máximo: `Por ese lado tu departamento ya no puede crecer.`
  - Aviso del lugar «Refugio», que sigue en el mapa hasta el plan 8: `El refugio cerró. Ahora cada quien vive en su departamento.`
  - La carta del alcalde. Título `Carta del alcalde`, firma `El alcalde`, y estas líneas en este orden (cada una sólo si le toca a esa persona):
    1. `El pueblo cambió, y vengo a contarte qué te toca.`
    2. `Desde hoy todos vivimos en el mismo edificio. Tu departamento mide {ancho} × {fondo} casillas, y lo puedes ampliar.`
    3. Con gachamones: `Te dejé puestas {camas} camas: una para ti y una para cada gachamon.` · Sin ninguno: `Te dejé tu cama puesta y otra guardada, para cuando llegue un gachamon.`
    4. Una casa: `Te devolví lo que costó tu casa: {monedas}.` · Varias: `Te devolví lo que costaron tus casas: {monedas}.`
    5. Un mueble: `Tu mueble está en guardados: ponlo donde quieras.` · Varios: `Tus {n} muebles están en guardados: ponlos donde quieras.`
    6. `Coseché lo que tenías plantado y lo dejé en tu mochila. El huerto vuelve más adelante.`
    7. `El refugio cerró. Te devolví {monedas} por tus tickets.`
    8. `Lo que te esperaba en el buzón ya está en tu mochila.`
    9. Una por cada recluta que se puso nombre solo (`{especie}` es el nombre de su especie, en minúsculas): `Tu {especie} ahora se llama {nombre}. Se puso el nombre solo, y se lo puedes cambiar una vez.`
    10. `Y dos cosas más: ya ningún gachamon muere, y a todos les pasa el tiempo, no sólo al que sale contigo.`
- **Lo que este plan decide en nombre de Felipe** (propuestas; se le enseñan con el plan):
  1. **El plan se parte en dos.** Éste es la vivienda y el día del cambio; «partir sin gachamon» (sin huevo, monedero en 0, la primera aventura) pasa a ser el plan 5, y el corte queda en ocho planes.
  2. **El día del cambio, el reloj de todos los gachamones vivos parte de ese momento**: a nadie se le cobra el tiempo que pasó desde la última vez que se guardó. (El plan 2 ya lo hacía con los que dormían; aquí vale para todos, y evita cerrar la cuenta de cada uno con las reglas de la intemperie.)
  3. Cada casa se devuelve al precio de catálogo de **la casa que es hoy** (una pequeña mejorada a grande vuelve como grande: 1200).
  4. El día del cambio **se quitan las filas ya convertidas** (las casas, los muebles viejos, lo plantado): así nada vale dos veces. La vuelta atrás es restaurar la copia de antes.
  5. Los muebles viejos pasan tal cual a guardados. La «Cama grande» de antes cuenta como cama si se pone.
  6. La carta dice también, en una línea, que ya nadie muere y que el tiempo pasa para todos.
  7. Para poner, guardar y ampliar hay que **estar en tu departamento** (el lugar «Tu casa»), igual que comprar pide estar en la Tienda.
  8. El lugar «Refugio» sigue en el mapa hasta el plan 8, vacío y con su aviso de que cerró.
  9. El ticket del refugio sale del catálogo; la semilla deja de venderse y de salir como botín (las que tengas se quedan).
  10. Abrir o cerrar la casa a las visitas (`hogar.publica`) se va con las casas: vuelve con los estados de puerta del proyecto 4. El buzón se queda como está, en pausa.

## Review Focus

1. **Poner un mueble en los bordes**: girado junto a la pared, saliéndose por una casilla, sobre otro de su capa, un mueble encima de la alfombra (vale), dos cosas que se pisan una sobre otra (no vale), algo de pared en el suelo y al revés, moverlo o girarlo sobre su propio sitio. → Tasks 1, 3 y 6.
2. **La cama que hace falta**: no se guarda la tuya ni la que deja a un gachamon sin la suya; una que sobra sí. Y reclutar sin cama libre no crea al gachamon ni cuenta como reclutado. → Tasks 1, 3 y 4.
3. **La misma petición dos veces**: comprar o ampliar con el mismo evento no cobra ni entrega otra vez; el mismo evento para otra cosa es un error; poner o guardar repetido deja lo mismo; un fallo a medias no cobra. → Tasks 3 y 6.
4. **El día del cambio fuera del caso feliz**: dos veces; dos arranques a la vez (el bot y la web); un fallo a medias; una base nueva; alguien sin ningún gachamon vivo; alguien con 25; la misma persona en dos servidores; un regalo del buzón que es un ticket. → Task 5.
5. **El pasado no se reescribe**: poner o guardar un mueble que cambia la comodidad no cambia el ánimo del tiempo que ya pasó; y el ritmo ya no mira casas, refugio ni intemperie. → Tasks 2 y 3.

**Sobre las pruebas de este plan.** Las ayudas (la base temporal, `T0`, `nacer(...)`, `con_monedas(...)`, `borrar_la_marca(...)`, el cliente web y `con_gachamon`) son las de las pruebas vecinas (`tests/test_casas.py`, `tests/test_db.py:247-294`, `tests/ayudas_web.py`). Lo que manda son los nombres de las pruebas nuevas y sus aserciones. En las pruebas, `P = dep.Pieza` y `depto(*piezas, ancho=3, fondo=3)` arma un `dep.Departamento`.

---

### Task 1: El departamento, puro

**Files:**
- Create: `departamento.py`, `tests/test_departamento.py`

**Interfaces:**
- Produces (todo en `departamento.py`, que se importa como `dep`):
  - Capas: `SUELO = "suelo"` (lo que se pisa), `BULTO = "bulto"` (ocupa la casilla), `PARED = "pared"`. Motivos: `NO_ES_TUYO = "no_es_tuyo"`, `NO_CABE = "no_cabe"`, `OCUPADO = "ocupado"`. Ejes: `ANCHO = "ancho"`, `FONDO = "fondo"`.
  - `LADO_INICIAL = 3`, `LADO_MAXIMO = 8`, `PRECIO_POR_CASILLA = 15`, `COMODIDAD_BASE = 80`, `MAXIMO_DE_GACHAMONES = 31` (en 8 × 8 caben 32 camas, menos la tuya).
  - `@dataclass(frozen=True) class Mueble(clave: str, nombre: str, emoji: str, precio: int, comodidad: int, ancho: int = 1, fondo: int = 1, capa: str = BULTO, cama: bool = False)`. En lo de pared, `ancho` son sus tramos.
  - `MUEBLES: dict[str, Mueble]`: los catorce de `casas.MUEBLES`, con su nombre, emoji, precio y comodidad de hoy, más `cama_sencilla` («Cama sencilla», 🛏️, 85, comodidad 2). Formas:

    | Clave | Forma | Capa | | Clave | Forma | Capa |
    |---|---|---|---|---|---|---|
    | `felpudo` | 1 × 1 | suelo | | `fuente` | 2 × 2 | bulto |
    | `maceta` | 1 × 1 | bulto | | `chimenea` | 2 × 1 | bulto |
    | `cuadro` | 1 tramo | pared | | `calefactor` | 1 × 1 | bulto |
    | `estanteria` | 2 × 1 | bulto | | `cama` | 2 × 1 | bulto, cama |
    | `lampara` | 1 × 1 | bulto | | `ventanal` | 2 tramos | pared |
    | `alfombra` | 2 × 2 | suelo | | `biblioteca` | 2 × 1 | bulto |
    | `cortinas` | 2 tramos | pared | | `cama_sencilla` | 2 × 1 | bulto, cama |
    | `cojines` | 1 × 1 | bulto | | | | |
  - `@dataclass(frozen=True) class Pieza(id: int, clave: str, x: int | None = None, y: int | None = None, giro: int = 0)`, con `.puesta -> bool` (tiene posición).
  - `@dataclass(frozen=True) class Departamento(ancho: int = 3, fondo: int = 3, piezas: tuple[Pieza, ...] = ())`, con `.casillas`, `.puestas`, `.guardadas`, `.camas_puestas`, `.comodidad` y `.pieza(pieza_id: int) -> Pieza | None`.
  - `DE_PARTIDA: Departamento`: 3 × 3 con una `cama_sencilla` puesta en (0, 0) y otra guardada (ids 0: son de mentira hasta que la base las cree).
  - `huella(mueble: Mueble, x: int, y: int, giro: int) -> frozenset[tuple[int, int]]`. En el suelo las casillas van de (0, 0) a (ancho − 1, fondo − 1); con giro 0 o 2 el mueble ocupa `ancho × fondo` desde (x, y), con 1 o 3 ocupa `fondo × ancho`. Las dos paredes del fondo son la fila `y = −1` y la columna `x = −1`: algo de pared puesto en (x, −1) ocupa los tramos (x, −1)…(x + ancho − 1, −1), y en (−1, y) los (−1, y)…(−1, y + ancho − 1). El giro no cambia lo de pared.
  - `problema_al_poner(depto: Departamento, pieza_id: int, x: int, y: int, giro: int) -> str | None`: `NO_ES_TUYO` si la pieza no está en el departamento o su clave ya no está en el catálogo; `NO_CABE` si alguna casilla de su huella queda fuera (un mueble de suelo, en la pared; algo de pared, en el suelo, en la esquina (−1, −1) o más allá del largo del muro); `OCUPADO` si su huella pisa la de otra pieza puesta **de su misma capa**. La pieza no choca consigo misma.
  - `cama_libre(depto: Departamento, vivos: int) -> bool`: `camas_puestas >= vivos + 2`. `puede_guardarse(depto: Departamento, pieza_id: int, vivos: int) -> bool`: falso sólo si la pieza es una cama puesta y al guardarla quedarían menos de `vivos + 1`.
  - `tope_de_comodidad(casillas: int) -> int`: `100 + (casillas - 9) * 50 // 55`. `Departamento.comodidad`: `COMODIDAD_BASE` más la comodidad de cada **tipo** de mueble puesto, una vez, sin pasar del tope; una clave que ya no está en el catálogo no suma.
  - `alivio_de_animo(comodidad: int) -> float`: la cuenta de hoy (`casas.alivio_de_animo`) con sus dos extremos fijos: 1.0 en 75 y 0.75 de 150 en adelante. `ritmo_de(depto: Departamento) -> sim.Ritmo`: `sim.Ritmo(animo=alivio_de_animo(depto.comodidad))`.
  - `coste_de_ampliar(depto: Departamento, eje: str) -> int | None`: 15 por cada casilla que suma (`ANCHO` suma `fondo` casillas, `FONDO` suma `ancho`); `None` si ese lado ya mide 8.
  - `tamano_para(camas: int) -> tuple[int, int]`: el primero de 3 × 3, 4 × 3, 4 × 4, 5 × 4… 8 × 8 con al menos `2 * camas + 5` casillas; si ninguno alcanza, (8, 8).
  - `acomodar_camas(ancho: int, fondo: int, cuantas: int) -> tuple[tuple[int, int, int], ...]`: dónde deja el alcalde `cuantas` camas de 2 × 1 en un departamento vacío, como (x, y, giro).

- [ ] **Step 1: Escribir las pruebas que fallan**, en `tests/test_departamento.py`:

```python
def test_el_catalogo_son_los_catorce_de_siempre_y_la_cama_sencilla():
    assert set(dep.MUEBLES) == set(cas.MUEBLES) | {"cama_sencilla"}
    for clave, viejo in cas.MUEBLES.items():
        nuevo = dep.MUEBLES[clave]
        assert (nuevo.nombre, nuevo.emoji, nuevo.precio, nuevo.comodidad) == (viejo.nombre, viejo.emoji, viejo.precio, viejo.comodidad)
    sencilla = dep.MUEBLES["cama_sencilla"]
    assert (sencilla.nombre, sencilla.precio, sencilla.comodidad) == ("Cama sencilla", 85, 2)
    assert {c for c, m in dep.MUEBLES.items() if m.cama} == {"cama", "cama_sencilla"}

@pytest.mark.parametrize("clave, ancho, fondo, capa", FORMAS)   # la tabla de arriba, las quince filas
def test_cada_mueble_ocupa_lo_que_dice_el_diseno(clave, ancho, fondo, capa):
    m = dep.MUEBLES[clave]
    assert (m.ancho, m.fondo, m.capa) == (ancho, fondo, capa)

def test_un_mueble_alargado_cambia_de_casillas_al_girar():
    cama = dep.MUEBLES["cama_sencilla"]
    assert dep.huella(cama, 1, 1, 0) == {(1, 1), (2, 1)} == dep.huella(cama, 1, 1, 2)
    assert dep.huella(cama, 1, 1, 1) == {(1, 1), (1, 2)} == dep.huella(cama, 1, 1, 3)
    assert len(dep.huella(dep.MUEBLES["fuente"], 0, 0, 1)) == 4

def test_lo_de_pared_ocupa_tramos_de_una_de_las_dos_paredes():
    cortinas = dep.MUEBLES["cortinas"]
    assert dep.huella(cortinas, 1, -1, 0) == {(1, -1), (2, -1)}
    assert dep.huella(cortinas, -1, 0, 3) == {(-1, 0), (-1, 1)}

def test_cabe_dentro_y_no_se_sale():
    d = depto(P(1, "cama_sencilla"))
    assert dep.problema_al_poner(d, 1, 1, 0, 0) is None
    assert dep.problema_al_poner(d, 1, 2, 0, 0) == dep.NO_CABE      # se sale por una casilla
    assert dep.problema_al_poner(d, 1, 2, 0, 1) is None             # girada, sí
    assert dep.problema_al_poner(d, 1, 0, 2, 1) == dep.NO_CABE
    assert dep.problema_al_poner(d, 1, 0, -1, 0) == dep.NO_CABE     # un mueble de suelo no va en la pared

def test_dos_bultos_no_comparten_casilla_pero_uno_va_sobre_la_alfombra():
    d = depto(P(1, "alfombra", 0, 0), P(2, "maceta"), P(3, "felpudo"), P(4, "lampara", 2, 2))
    assert dep.problema_al_poner(d, 2, 1, 1, 0) is None             # encima de la alfombra
    assert dep.problema_al_poner(d, 3, 1, 1, 0) == dep.OCUPADO      # dos cosas que se pisan, no
    assert dep.problema_al_poner(d, 3, 2, 2, 0) is None             # el felpudo bajo la lámpara
    assert dep.problema_al_poner(d, 2, 2, 2, 0) == dep.OCUPADO      # donde está la lámpara

def test_moverse_o_girar_en_su_sitio_no_choca_consigo_mismo():
    d = depto(P(1, "cama_sencilla", 0, 0, 0))
    assert dep.problema_al_poner(d, 1, 0, 0, 1) is None
    assert dep.problema_al_poner(d, 1, 1, 0, 0) is None

def test_la_pared_tiene_sus_tramos():
    d = depto(P(1, "cortinas"), P(2, "cuadro", 0, -1), P(3, "ventanal"))
    assert dep.problema_al_poner(d, 1, 1, -1, 0) is None
    assert dep.problema_al_poner(d, 1, 0, -1, 0) == dep.OCUPADO     # el cuadro está en el tramo 0
    assert dep.problema_al_poner(d, 1, 2, -1, 0) == dep.NO_CABE     # se sale del muro
    assert dep.problema_al_poner(d, 3, -1, 1, 0) is None            # la otra pared
    assert dep.problema_al_poner(d, 1, 1, 1, 0) == dep.NO_CABE      # lo de pared no va en el suelo
    assert dep.problema_al_poner(d, 2, -1, -1, 0) == dep.NO_CABE    # la esquina no es de nadie

def test_lo_que_no_es_tuyo_o_ya_no_existe_no_se_pone():
    assert dep.problema_al_poner(depto(), 9, 0, 0, 0) == dep.NO_ES_TUYO
    assert dep.problema_al_poner(depto(P(1, "ya_no_existe")), 1, 0, 0, 0) == dep.NO_ES_TUYO

def test_las_camas_puestas_son_las_que_cuentan():
    d = depto(P(1, "cama_sencilla", 0, 0), P(2, "cama", 0, 1), P(3, "cama_sencilla"))
    assert d.camas_puestas == 2
    assert dep.cama_libre(d, vivos=0) and not dep.cama_libre(d, vivos=1)

def test_no_se_guarda_la_cama_que_deja_a_alguien_sin_la_suya():
    d = depto(P(1, "cama_sencilla", 0, 0), P(2, "cama_sencilla", 0, 1), P(3, "cama_sencilla", 0, 2), P(4, "maceta", 2, 0))
    assert dep.puede_guardarse(d, 1, vivos=1)                       # sobra una
    assert not dep.puede_guardarse(d, 1, vivos=2)
    assert dep.puede_guardarse(d, 4, vivos=2)                       # una maceta, siempre
    assert not dep.puede_guardarse(depto(P(1, "cama_sencilla", 0, 0)), 1, vivos=0)   # la tuya no

def test_la_comodidad_parte_de_80_y_cada_tipo_suma_una_vez():
    assert depto().comodidad == 80
    assert depto(P(1, "felpudo", 0, 0), P(2, "felpudo", 1, 0), P(3, "maceta", 2, 0), P(4, "cuadro"), P(5, "ya_no_existe", 2, 2)).comodidad == 85

def test_el_tope_depende_de_las_casillas():
    assert [dep.tope_de_comodidad(n) for n in (9, 12, 16, 64)] == [100, 102, 106, 150]
    todo = tuple(P(i, clave, 0, 0) for i, clave in enumerate(dep.MUEBLES, 1))   # la cuenta no mira choques
    assert dep.Departamento(3, 3, todo).comodidad == 100
    assert dep.Departamento(8, 8, todo).comodidad == 150

def test_la_comodidad_alivia_el_animo_como_siempre():
    assert dep.alivio_de_animo(75) == 1.0 and dep.alivio_de_animo(150) == 0.75 == dep.alivio_de_animo(200)
    for comodidad in (75, 80, 100, 125, 150):
        assert dep.alivio_de_animo(comodidad) == pytest.approx(cas.alivio_de_animo(comodidad))
    assert dep.ritmo_de(depto()) == sim.Ritmo(animo=dep.alivio_de_animo(80))

def test_ampliar_cuesta_15_por_casilla_y_para_en_8():
    assert dep.coste_de_ampliar(depto(), dep.ANCHO) == 45 == dep.coste_de_ampliar(depto(), dep.FONDO)
    assert dep.coste_de_ampliar(dep.Departamento(4, 3), dep.FONDO) == 60
    assert dep.coste_de_ampliar(dep.Departamento(8, 3), dep.ANCHO) is None

def test_de_3x3_a_8x8_son_825_monedas():
    d, total = dep.Departamento(), 0
    while (eje := dep.ANCHO if d.ancho <= d.fondo else dep.FONDO) and dep.coste_de_ampliar(d, eje):
        total += dep.coste_de_ampliar(d, eje)
        d = dep.Departamento(d.ancho + (eje == dep.ANCHO), d.fondo + (eje == dep.FONDO))
    assert (d.ancho, d.fondo, total) == (8, 8, 825)

def test_el_alcalde_da_el_primer_tamano_de_la_serie_en_que_caben():
    assert [dep.tamano_para(c) for c in (1, 2, 3, 4, 6, 26, 40)] == [(3, 3), (3, 3), (4, 3), (4, 4), (5, 4), (8, 8), (8, 8)]

@pytest.mark.parametrize("camas", range(1, 30))
def test_las_camas_del_alcalde_caben_todas_y_no_se_pisan(camas):
    ancho, fondo = dep.tamano_para(camas)
    d = dep.Departamento(ancho, fondo, tuple(P(i, "cama_sencilla") for i in range(camas)))
    sitios = dep.acomodar_camas(ancho, fondo, camas)
    assert len(sitios) == camas
    for i, (x, y, giro) in enumerate(sitios):
        assert dep.problema_al_poner(d, i, x, y, giro) is None
        d = dep.Departamento(ancho, fondo, tuple(replace(p, x=x, y=y, giro=giro) if p.id == i else p for p in d.piezas))
    assert d.camas_puestas == camas

def test_el_departamento_de_partida_trae_tu_cama_puesta_y_otra_guardada():
    d = dep.DE_PARTIDA
    assert (d.ancho, d.fondo) == (3, 3)
    assert [(p.clave, p.puesta) for p in d.piezas] == [("cama_sencilla", True), ("cama_sencilla", False)]
    assert d.camas_puestas == 1 and d.comodidad == 82
```

- [ ] **Step 2: Verlas fallar.** Run: `./venv/bin/python -m pytest tests/test_departamento.py -q` — Expected: FAIL al importar (`No module named 'departamento'`).

- [ ] **Step 3: Implementar `departamento.py`** con las firmas de arriba. Lo único que las pruebas no fijan es cómo reparte `acomodar_camas`: por filas, de a dos columnas (cama en (x, y) con giro 0 para x = 0, 2, 4…); si el ancho es impar, la última columna se llena con camas giradas (giro 1), de a dos filas. `casas.py` no se toca: las pruebas lo usan para comparar.

- [ ] **Step 4: Verlas pasar.** Run: `./venv/bin/python -m pytest tests/test_departamento.py -q` — Expected: PASS.

- [ ] **Step 5: Commit** — `feat(reglas): el departamento por casillas, como módulo puro`.

---

### Task 2: El departamento en la base, y el ritmo sale de él

**Files:**
- Modify: `db.py` (esquema, persistencia, `_avanzar_en`), `tests/test_casas.py`, `tests/test_migracion_casas.py` (sólo las pruebas del ritmo por casa en la base)
- Create: `tests/test_db_departamento.py`

**Interfaces:**
- Consumes: `departamento.py` (Task 1).
- Produces (en `db.py`):
  - En `SCHEMA_TABLAS`:

    ```sql
    CREATE TABLE IF NOT EXISTS departamentos (
        usuario_id TEXT NOT NULL, guild_id TEXT NOT NULL,
        ancho INTEGER NOT NULL DEFAULT 3 CHECK (ancho BETWEEN 3 AND 8),
        fondo INTEGER NOT NULL DEFAULT 3 CHECK (fondo BETWEEN 3 AND 8),
        creado_en TEXT NOT NULL,
        PRIMARY KEY (usuario_id, guild_id));
    CREATE TABLE IF NOT EXISTS muebles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id TEXT NOT NULL, guild_id TEXT NOT NULL, mueble TEXT NOT NULL,
        x INTEGER, y INTEGER,                         -- las dos vacías: guardado
        giro INTEGER NOT NULL DEFAULT 0 CHECK (giro BETWEEN 0 AND 3),
        CHECK ((x IS NULL) = (y IS NULL)));
    ```
    y en `SCHEMA_INDICES`, un índice de `muebles` por `(usuario_id, guild_id)`.
  - `departamento_de(usuario_id: str, guild_id: str, ahora: datetime) -> dep.Departamento` (`BEGIN IMMEDIATE`) y `_departamento_en(con, usuario_id, guild_id, ahora) -> dep.Departamento`: lo lee y, **si no existe, lo crea** como `dep.DE_PARTIDA` (la fila y sus dos camas). Las piezas vuelven ordenadas por id.
  - `departamento_leido(usuario_id: str, guild_id: str) -> dep.Departamento` y `_departamento_leido(con, usuario_id, guild_id) -> dep.Departamento`: **sin escribir**; sin fila devuelven `dep.DE_PARTIDA`.
  - `anadir_mueble_en(con, usuario_id: str, guild_id: str, clave: str, x: int | None = None, y: int | None = None, giro: int = 0) -> int` (el id nuevo), `poner_mueble_en(con, mueble_id: int, x: int, y: int, giro: int) -> None`, `guardar_mueble_en(con, mueble_id: int) -> None`, `ampliar_en(con, usuario_id: str, guild_id: str, eje: str) -> None` (suma 1 a `ancho` o a `fondo`).
  - `asentar_el_plantel_en(con, usuario_id: str, guild_id: str, ahora: datetime) -> list[sim.Criatura]`: pone al día **y guarda** a cada gachamon vivo de esa persona.
  - `_avanzar_en` toma el ritmo de `dep.ritmo_de(_departamento_leido(con, criatura.usuario_id, criatura.guild_id))`. Ya no lee `hogar`, las casas ni `casa_id`.

- [ ] **Step 1: Escribir las pruebas que fallan**, en `tests/test_db_departamento.py`:

```python
def test_el_departamento_nace_al_mirarlo_con_tu_cama_puesta_y_otra_guardada():
    d = db.departamento_de("u1", "g1", T0)
    assert (d.ancho, d.fondo) == (3, 3)
    assert [(p.clave, p.x, p.y, p.giro) for p in d.piezas] == [("cama_sencilla", 0, 0, 0), ("cama_sencilla", None, None, 0)]
    assert all(p.id > 0 for p in d.piezas)
    assert db.departamento_de("u1", "g1", T0) == d                  # no nace dos veces

def test_leer_sin_crear_da_el_de_partida_y_no_escribe():
    assert db.departamento_leido("u9", "g1") == dep.DE_PARTIDA
    assert filas("departamentos") == [] and filas("muebles") == []

def test_un_mueble_llega_guardado_se_pone_y_se_vuelve_a_guardar():
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db._departamento_en(con, "u1", "g1", T0)
        uno = db.anadir_mueble_en(con, "u1", "g1", "felpudo")
        otro = db.anadir_mueble_en(con, "u1", "g1", "felpudo")      # puede haber varios iguales
        db.poner_mueble_en(con, uno, 2, 1, 3)
    d = db.departamento_leido("u1", "g1")
    assert uno != otro and d.pieza(uno) == dep.Pieza(uno, "felpudo", 2, 1, 3) and not d.pieza(otro).puesta
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db.guardar_mueble_en(con, uno)
    assert db.departamento_leido("u1", "g1").pieza(uno) == dep.Pieza(uno, "felpudo")

def test_ampliar_suma_una_columna_o_una_fila_y_no_mueve_nada():
    antes = db.departamento_de("u1", "g1", T0)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db.ampliar_en(con, "u1", "g1", dep.ANCHO)
        db.ampliar_en(con, "u1", "g1", dep.FONDO)
        db.ampliar_en(con, "u1", "g1", dep.FONDO)
    despues = db.departamento_leido("u1", "g1")
    assert (despues.ancho, despues.fondo, despues.piezas) == (4, 5, antes.piezas)

def test_el_esquema_no_admite_media_posicion_ni_un_tamano_imposible():
    for sql in ("INSERT INTO muebles (usuario_id, guild_id, mueble, x) VALUES ('u1', 'g1', 'felpudo', 1)",
                "INSERT INTO muebles (usuario_id, guild_id, mueble, giro) VALUES ('u1', 'g1', 'felpudo', 4)",
                "INSERT INTO departamentos (usuario_id, guild_id, ancho, creado_en) VALUES ('u1', 'g1', 9, 'x')"):
        with pytest.raises(sqlite3.IntegrityError), db.conectar() as con:
            con.execute(sql)

def test_el_departamento_es_de_cada_persona_y_de_cada_servidor():
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db._departamento_en(con, "u1", "g1", T0)
        db.anadir_mueble_en(con, "u1", "g1", "maceta")
    assert len(db.departamento_leido("u1", "g1").piezas) == 3
    assert db.departamento_leido("u1", "g2") == dep.DE_PARTIDA == db.departamento_leido("u2", "g1")

def test_el_ritmo_sale_del_departamento():
    c = nacer("Ana")
    con_muebles_puestos("u1", "chimenea", "biblioteca")              # 82 + 6 + 7
    tarde = T0 + timedelta(hours=10)
    d = db.departamento_leido("u1", "g1")
    assert d.comodidad == 95
    assert db.avanzar(c, tarde) == sim.avanzar(c, tarde, dep.ritmo_de(d))
    assert db.avanzar(c, tarde).animo > sim.avanzar(c, tarde).animo

def test_el_ritmo_ya_no_mira_casas_ni_refugio():
    c = nacer("Ana")
    with db.conectar() as con:      # lo que antes era «a la intemperie»: el refugio vencido y sin casa
        con.execute("INSERT INTO hogar (usuario_id, guild_id, refugio_hasta) VALUES ('u1', 'g1', ?)", ((T0 - timedelta(days=30)).isoformat(),))
    tarde = T0 + timedelta(days=30)
    assert db.avanzar(c, tarde) == sim.avanzar(c, tarde, dep.ritmo_de(dep.DE_PARTIDA))
    assert db.avanzar(c, tarde).hambre == 0                          # ya no hay suelo de 25

def test_asentar_guarda_a_todos_los_vivos_a_esa_hora():
    ana, bea = nacer("Ana"), nacer("Bea", activa=False)
    tarde = T0 + timedelta(hours=5)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        asentados = db.asentar_el_plantel_en(con, "u1", "g1", tarde)
    assert {c.id for c in asentados} == {ana.id, bea.id}
    for c in (ana, bea):
        assert db.por_id(c.id).actualizada_en == tarde and db.por_id(c.id).hambre < c.hambre
```

- [ ] **Step 2: Verlas fallar.** Run: `./venv/bin/python -m pytest tests/test_db_departamento.py -q` — Expected: FAIL (`db` no tiene `departamento_de`).

- [ ] **Step 3: Implementar en `db.py`** las tablas, las funciones y el cambio de `_avanzar_en`. `asentar_el_plantel_en` usa la misma función de guardado que ya usa `economia._cuidar_en`.

- [ ] **Step 4: Las pruebas viejas del ritmo.** En `tests/test_casas.py` («Lo que el hogar le hace») y `tests/test_migracion_casas.py`, las pruebas que afirmaban, **a través de la base** (`db.avanzar`, `db.plantel_al_dia`, un cuidado), que el ritmo sale de la casa, del refugio o de la intemperie se borran: esa regla es la que este paso cambia, y las dos pruebas nuevas del ritmo la reemplazan. Las que prueban `casas.ritmo_de` o `casas.comodidad_de` como funciones puras se quedan hasta la Task 8.

- [ ] **Step 5: Verlas pasar y la suite entera.** Run: `./venv/bin/python -m pytest tests/ -q -p no:cacheprovider` — Expected: PASS, sin avisos nuevos.

- [ ] **Step 6: Commit** — `feat(base): el departamento de cada quien, y el ritmo del tiempo sale de él`.

---

### Task 3: Comprar, poner, guardar y ampliar

**Files:**
- Modify: `economia.py`, `db.py` (se van `mobiliario`, `_mobiliario`, `comprar_mueble_en`, `colocar_mueble_en`), `web/tienda.py`, `web/arte.py`, `web/static/datos/arte.json`, `web/static/js/tienda.js` (sólo la parte de muebles), `herramientas/rellenos.py` si hace falta para el dibujo nuevo, y las pruebas que usaban las reglas viejas de muebles (`tests/test_casas.py`, `tests/test_motivos.py`, `tests/test_acciones_unicas.py`, `tests/test_migracion_casas.py`, `tests/test_web_tienda.py`, `tests/test_arte.py`, `tests/js/`)
- Create: `tests/test_economia_departamento.py`

**Interfaces:**
- Consumes: Tasks 1 y 2.
- Produces (en `economia.py`):
  - `@dataclass(frozen=True) class ResultadoDepartamento(ok: bool = False, departamento: dep.Departamento | None = None, motivo: str | None = None, saldo: int = 0, coste: int = 0, mueble_id: int | None = None, replay: bool = False)`.
  - `comprar_mueble(usuario_id: str, guild_id: str, mueble: dep.Mueble, ahora: datetime | None = None, evento_id: str | None = None) -> ResultadoDepartamento`: cobra y lo deja **guardado**; se puede comprar el mismo las veces que se quiera. `ValueError` si el mueble no es el del catálogo. Evento: acción `"mueble"`, solicitud la clave, resultado `{"mueble_id": …}`. Motivo `"faltan_monedas"` (con `coste` y `saldo`). No escribe en `operaciones_economia`, como hoy.
  - `poner_mueble(usuario_id: str, guild_id: str, mueble_id: int, x: int, y: int, giro: int, ahora: datetime | None = None) -> ResultadoDepartamento`: poner, mover y girar son esto mismo. Motivos: los de `dep.problema_al_poner`.
  - `guardar_mueble(usuario_id: str, guild_id: str, mueble_id: int, ahora: datetime | None = None) -> ResultadoDepartamento`: motivos `dep.NO_ES_TUYO` y `"hace_falta"` (`dep.puede_guardarse` con los vivos de esa persona). Guardar lo ya guardado sale bien y no cambia nada.
  - `ampliar_departamento(usuario_id: str, guild_id: str, eje: str, ahora: datetime | None = None, evento_id: str | None = None) -> ResultadoDepartamento`: `ValueError` si el eje no es `dep.ANCHO` ni `dep.FONDO`. Evento: acción `"ampliar"`, solicitud el eje, resultado `{"ancho": …, "fondo": …, "coste": …}`. Motivos `"ya_es_el_maximo"` y `"faltan_monedas"`.
  - Las cuatro crean el departamento si falta (`db._departamento_en`). `poner_mueble`, `guardar_mueble` y `ampliar_departamento`, **cuando van a cambiar algo**, llaman antes a `db.asentar_el_plantel_en`.
  - Se van de `economia.py`: el `comprar_mueble` de antes, `colocar_mueble`, `retirar_mueble`, `_estado_de_la_casa`, `_recibo_mueble` y `ResultadoMueble`.
- Produces (web): `GET /tienda` → `muebles: {"lista": [{clave, nombre, precio, comodidad, icono, tienes}]}` (`tienes` = cuántos tiene, puestos o guardados; se van `tienes_casa` y `tuyo`); `POST /tienda/comprar` con `que: "mueble"` llama a la regla nueva y contesta la frase nueva. `web/arte.py` saca los iconos de muebles de `dep.MUEBLES` (uno más: `cama_sencilla`, con su dibujo de relleno).

- [ ] **Step 1: Escribir las pruebas que fallan**, en `tests/test_economia_departamento.py` (`FELPUDO = dep.MUEBLES["felpudo"]`, etc.; `puesto("u1", clave, x, y, giro=0) -> int` añade un mueble ya puesto por la base):

```python
def test_comprar_un_mueble_cobra_y_lo_deja_guardado():
    con_monedas(100)
    hecho = economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1")
    assert (hecho.ok, hecho.saldo, hecho.replay) == (True, 70, False)
    assert not hecho.departamento.pieza(hecho.mueble_id).puesta
    assert filas("operaciones_economia") == []

def test_se_puede_comprar_dos_veces_el_mismo():
    con_monedas(100)
    a = economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1")
    b = economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e2")
    assert a.mueble_id != b.mueble_id and b.saldo == 40

def test_repetir_la_compra_con_el_mismo_evento_no_cobra_ni_entrega_otra_vez():
    con_monedas(100)
    a = economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1")
    b = economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1")
    assert (b.ok, b.replay, b.mueble_id, b.saldo) == (True, True, a.mueble_id, 70)
    assert len(db.departamento_leido("u1", "g1").piezas) == 3

def test_el_mismo_evento_para_otro_mueble_es_un_error():
    con_monedas(200)
    economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1")
    with pytest.raises(RuntimeError):
        economia.comprar_mueble("u1", "g1", MACETA, T0, evento_id="e1")

def test_sin_monedas_no_se_compra_ni_se_gasta_el_evento():
    con_monedas(10)
    hecho = economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1")
    assert (hecho.ok, hecho.motivo, hecho.coste, hecho.saldo) == (False, "faltan_monedas", 30, 10)
    con_monedas(30)
    assert economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1").ok

def test_poner_mover_y_girar():
    cama = db.departamento_de("u1", "g1", T0).guardadas[0].id
    assert economia.poner_mueble("u1", "g1", cama, 1, 1, 0, T0).ok
    hecho = economia.poner_mueble("u1", "g1", cama, 0, 1, 1, T0)       # la mueve y la gira
    assert hecho.ok and hecho.departamento.pieza(cama) == dep.Pieza(cama, "cama_sencilla", 0, 1, 1)
    assert economia.poner_mueble("u1", "g1", cama, 0, 1, 1, T0).departamento == hecho.departamento   # repetir deja lo mismo

@pytest.mark.parametrize("x, y, giro, motivo", [(2, 2, 0, dep.NO_CABE), (0, 0, 0, dep.OCUPADO), (-1, 0, 0, dep.NO_CABE)])
def test_no_se_pone_donde_no_cabe_ni_donde_hay_algo(x, y, giro, motivo):
    antes = db.departamento_de("u1", "g1", T0)
    hecho = economia.poner_mueble("u1", "g1", antes.guardadas[0].id, x, y, giro, T0)
    assert (hecho.ok, hecho.motivo) == (False, motivo)
    assert db.departamento_leido("u1", "g1") == antes

def test_el_mueble_de_otro_no_se_pone_ni_se_guarda():
    ajeno = db.departamento_de("u2", "g1", T0).guardadas[0].id
    assert economia.poner_mueble("u1", "g1", ajeno, 1, 1, 0, T0).motivo == dep.NO_ES_TUYO
    assert economia.guardar_mueble("u1", "g1", ajeno, T0).motivo == dep.NO_ES_TUYO
    assert not db.departamento_leido("u2", "g1").pieza(ajeno).puesta

def test_guardar_no_destruye_y_repetirlo_no_cambia_nada():
    maceta = puesto("u1", "maceta", 2, 2)
    assert economia.guardar_mueble("u1", "g1", maceta, T0).ok
    hecho = economia.guardar_mueble("u1", "g1", maceta, T0)
    assert hecho.ok and hecho.departamento.pieza(maceta) == dep.Pieza(maceta, "maceta")

def test_la_cama_que_hace_falta_no_se_guarda():
    nacer("Ana")
    d = db.departamento_de("u1", "g1", T0)
    tuya, otra = d.puestas[0].id, d.guardadas[0].id
    economia.poner_mueble("u1", "g1", otra, 0, 1, 0, T0)               # ya son dos: tú y Ana
    assert economia.guardar_mueble("u1", "g1", tuya, T0).motivo == "hace_falta"
    tercera = puesto("u1", "cama", 0, 2)
    assert economia.guardar_mueble("u1", "g1", tuya, T0).ok            # ahora sobra una
    assert economia.guardar_mueble("u1", "g1", tercera, T0).motivo == "hace_falta"

def test_ampliar_cobra_15_por_casilla_y_no_mueve_lo_puesto():
    con_monedas(200)
    antes = db.departamento_de("u1", "g1", T0)
    hecho = economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id="e1")
    assert (hecho.ok, hecho.coste, hecho.saldo) == (True, 45, 155)
    assert (hecho.departamento.ancho, hecho.departamento.fondo, hecho.departamento.piezas) == (4, 3, antes.piezas)
    assert economia.ampliar_departamento("u1", "g1", dep.FONDO, T0, evento_id="e2").coste == 60

def test_repetir_ampliar_con_el_mismo_evento_no_cobra_dos_veces():
    con_monedas(200)
    economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id="e1")
    otra = economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id="e1")
    assert (otra.ok, otra.replay, otra.saldo, otra.departamento.ancho) == (True, True, 155, 4)

def test_ampliar_sin_monedas_o_ya_en_8_no_cambia_nada():
    con_monedas(44)
    assert economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id="e1").motivo == "faltan_monedas"
    con_monedas(9999)
    for i in range(5):
        assert economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id=f"a{i}").ok
    tope = economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id="a9")
    assert (tope.ok, tope.motivo, tope.departamento.ancho) == (False, "ya_es_el_maximo", 8)

def test_si_falla_a_medias_ampliar_no_cobra():
    con_monedas(200)
    db.departamento_de("u1", "g1", T0)
    rompe("BEFORE UPDATE ON departamentos")          # un disparador que aborta, como el de `operaciones_economia` en las pruebas vecinas
    with pytest.raises(sqlite3.DatabaseError):
        economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id="e1")
    assert economia.saldos("u1", "g1").asciicoins == 200 and filas("acciones_unicas") == []

def test_poner_un_mueble_no_cambia_el_animo_del_tiempo_ya_pasado():
    c = nacer("Ana")
    chimenea = guardado("u1", "chimenea")
    tarde = T0 + timedelta(hours=10)
    esperado = sim.avanzar(c, tarde, dep.ritmo_de(db.departamento_leido("u1", "g1")))   # con la comodidad de antes
    economia.poner_mueble("u1", "g1", chimenea, 1, 1, 0, tarde)
    ahora_es = db.por_id(c.id)
    assert ahora_es.actualizada_en == tarde and ahora_es.animo == pytest.approx(esperado.animo)

def test_guardar_y_ampliar_tambien_asientan_antes():
    c = nacer("Ana"); con_monedas(100)
    maceta = puesto("u1", "maceta", 2, 2)
    economia.guardar_mueble("u1", "g1", maceta, T0 + timedelta(hours=1))
    assert db.por_id(c.id).actualizada_en == T0 + timedelta(hours=1)
    economia.ampliar_departamento("u1", "g1", dep.FONDO, T0 + timedelta(hours=2), evento_id="e1")
    assert db.por_id(c.id).actualizada_en == T0 + timedelta(hours=2)
```

  Y en `tests/test_web_tienda.py`, en lugar de las cinco pruebas de muebles de hoy:

```python
def test_la_tienda_vende_muebles_de_a_varios(cliente):
    con_gachamon(cliente); ir(cliente, "tienda"); con_monedas_web(cliente, 200)
    for evento in ("m1", "m2"):
        r = cliente.post("/gachamon/api/tienda/comprar", json={"que": "mueble", "clave": "felpudo", "evento_id": evento}, headers=CABECERA).json()
        assert (r["ok"], r["mensaje"]) == (True, "Compraste Felpudo. Quedó en tus guardados.")
    felpudo = next(m for m in r["tienda"]["muebles"]["lista"] if m["clave"] == "felpudo")
    assert felpudo["tienes"] == 2 and "tuyo" not in felpudo and "tienes_casa" not in r["tienda"]["muebles"]

def test_la_cama_sencilla_esta_a_la_venta_por_85(cliente):
    con_gachamon(cliente); ir(cliente, "tienda")
    lista = cliente.get("/gachamon/api/tienda").json()["muebles"]["lista"]
    assert next(m for m in lista if m["clave"] == "cama_sencilla")["precio"] == 85

def test_un_mueble_no_pide_tener_casa(cliente): ...          # con 30 monedas y sin casa: se compra
def test_sin_monedas_el_mueble_dice_cuantas_faltan(cliente): ...   # ok False, clave "faltan_monedas", «Te faltan 20 monedas.»
```

- [ ] **Step 2: Verlas fallar.** Run: `./venv/bin/python -m pytest tests/test_economia_departamento.py -q` — Expected: FAIL (`economia` no tiene `ResultadoDepartamento`).

- [ ] **Step 3: Implementar las cuatro reglas** en `economia.py` y quitar las viejas de muebles; quitar de `db.py` sus cuatro funciones de `mobiliario` (la tabla se queda, y `db._casas_de` y `db.vender_la_casa_en`, que la leen, también, hasta la Task 8).

- [ ] **Step 4: La Tienda.** `web/tienda.py`: `_muebles(jugador)`, `_pieza` y `_del_mueble` con lo de arriba; se va `_NO_DEL_MUEBLE`. `web/arte.py`, `arte.json` y el dibujo de relleno de `cama_sencilla`; `tests/test_arte.py` cuenta una pieza más. `tienda.js`: la lista de muebles enseña cuántos tienes y siempre deja comprar; con su prueba en `tests/js/`.

- [ ] **Step 5: Las pruebas viejas de muebles.** Se borran las de `comprar_mueble`, `colocar_mueble` y `retirar_mueble` de antes («uno de cada», los huecos, el mueble que no cabe y se guarda). Las pruebas de casas que siguen vivas hasta la Task 8 y necesitaban un mueble colocado lo montan con una fila de `mobiliario` escrita a mano; si su única razón de ser era el mueble viejo, se borran. El informe las lista.

- [ ] **Step 6: Verlas pasar y la suite entera** (Python y JavaScript). Run: `./venv/bin/python -m pytest tests/ -q -p no:cacheprovider` — Expected: PASS.

- [ ] **Step 7: Commit** — `feat(reglas): comprar, poner, guardar y ampliar en el departamento`.

---

### Task 4: Las camas mandan

**Files:**
- Modify: `db.py` (`crear`, fuera `MAXIMO_PLANTEL`), `nacer.py` (`unir_recluta`), `web/incubadora.py`, `nombres.py` (el comentario), `tests/test_db.py`, `tests/test_marcador.py`, `tests/test_nombres.py`, `tests/test_web_incubadora.py`, `tests/test_nacer.py`
- Create: `tests/test_camas.py`

**Interfaces:**
- Consumes: Tasks 1 y 2.
- Produces:
  - `db.SinCamaLibre(ValueError)`.
  - `db.crear(..., *, cuenta_vigente: bool = False, se_nombro_solo: bool = False, pide_cama: bool = False)`: con `pide_cama`, dentro de su transacción, si `not dep.cama_libre(_departamento_leido(...), vivos)` lanza `SinCamaLibre` **antes** de insertar y de apuntar nada. Se van `db.MAXIMO_PLANTEL` y su comprobación.
  - `db.hay_cama_libre(usuario_id: str, guild_id: str) -> bool`.
  - `nacer.unir_recluta` pasa `pide_cama=True` y deja salir `db.SinCamaLibre`. `nacer.romper_el_huevo` no la pide (el huevo se va en el plan 5).
  - `GET /incubadora`: `"maximo"` pasa a ser cuántos gachamones caben hoy: las camas puestas menos la tuya, y nunca menos de los que ya tiene (el que nació del huevo todavía no tiene su cama).

- [ ] **Step 1: Escribir las pruebas que fallan**, en `tests/test_camas.py`:

```python
def recluta(rng=1):
    return nacer_.unir_recluta("u1", "g1", especie="pulpo", stats=STATS, genero=esp.MACHO, caracter=esp.CARACTER_POR_DEFECTO, ahora=T0, rng=random.Random(rng))

def test_un_recluta_pide_una_cama_libre():
    nacer("Ana")                                   # del huevo: tú y Ana, con una sola cama puesta
    with pytest.raises(db.SinCamaLibre):
        recluta()
    poner_camas("u1", 2)                           # ya son tres: la tuya, la de Ana y una libre
    assert recluta().nombre
    with pytest.raises(db.SinCamaLibre):
        recluta(2)

def test_sin_cama_libre_no_nace_nadie_ni_cuenta_como_reclutado():
    nacer("Ana")
    antes = (filas("criaturas"), filas("marcador_persona"))
    with pytest.raises(db.SinCamaLibre):
        recluta()
    assert (filas("criaturas"), filas("marcador_persona")) == antes

def test_las_camas_guardadas_no_cuentan():
    nacer("Ana")
    for _ in range(3):
        guardado("u1", "cama_sencilla")
    assert not db.hay_cama_libre("u1", "g1")

def test_el_que_nace_del_huevo_todavia_no_pide_cama():
    assert nacer_.romper_el_huevo("u1", "g1", T0, random.Random(1)).id

def test_ya_no_hay_tope_de_25():
    for i in range(27):
        db.crear("u1", "g1", "pulpo", f"N{i}", STATS, T0, activa=(i == 0))
    assert len(db.plantel("u1", "g1")) == 27 and not hasattr(db, "MAXIMO_PLANTEL")

def test_hay_mas_nombres_que_gachamones_caben():
    assert dep.MAXIMO_DE_GACHAMONES == 31       # y en tests/test_nombres.py, la cuenta de nombres se compara con esto

def test_la_incubadora_dice_cuantos_caben_por_las_camas(cliente):
    con_gachamon(cliente); ir(cliente, "incubadora")
    assert cliente.get("/gachamon/api/incubadora").json()["maximo"] == 1     # el del huevo, que aún no tiene cama
    poner_camas(USUARIO_WEB, 3, guild=PUEBLO)                                # ya son cuatro puestas
    assert cliente.get("/gachamon/api/incubadora").json()["maximo"] == 3
```

- [ ] **Step 2: Verlas fallar.** Run: `./venv/bin/python -m pytest tests/test_camas.py -q` — Expected: FAIL (`db` no tiene `SinCamaLibre`).

- [ ] **Step 3: Implementar** lo de arriba. Las pruebas que fijaban el tope de 25 (`tests/test_db.py:859-877`, `tests/test_marcador.py:243`, `tests/test_web_incubadora.py:104,149`) se cambian por las nuevas; `tests/test_nombres.py:15` compara con `dep.MAXIMO_DE_GACHAMONES + 1`. Las pruebas de `unir_recluta` que reclutaban sin camas ponen antes las que hagan falta.

- [ ] **Step 4: Verlas pasar y la suite entera.** Run: `./venv/bin/python -m pytest tests/ -q -p no:cacheprovider` — Expected: PASS.

- [ ] **Step 5: Commit** — `feat(reglas): el límite de gachamones son las camas puestas`.

---

### Task 5: El día del cambio

**Files:**
- Modify: `economia.py` (`el_dia_del_cambio`, `poner_al_dia`), `db.py` (la tabla `cartas` y sus tres funciones)
- Create: `tests/test_dia_del_cambio.py`

**Interfaces:**
- Consumes: Tasks 1, 2 y 4 (`dep.tamano_para`, `dep.acomodar_camas`, `db._departamento_en`, `db.anadir_mueble_en`, `db.ampliar_en`…); de hoy, `db._una_sola_vez`, `_asegurar_monedero`, `db.guardar_en_la_mochila_en` y, de `huerto.py`, `color_sembrado`, `tirar_color`, `tirar_cuantos`, `tirar_arcoiris`, `clave_de_poroto`, `ARCOIRIS`.
- Produces:
  - En `db.py`: la tabla `cartas (usuario_id TEXT NOT NULL, guild_id TEXT NOT NULL, carta TEXT NOT NULL, contenido TEXT NOT NULL, escrita_en TEXT NOT NULL, vista_en TEXT, PRIMARY KEY (usuario_id, guild_id, carta))` (`contenido` es JSON); `guardar_carta_en(con, usuario_id: str, guild_id: str, carta: str, contenido: dict, ahora: datetime) -> None`; `carta_sin_ver(usuario_id: str, guild_id: str, carta: str) -> dict | None`; `marcar_carta_vista(usuario_id: str, guild_id: str, carta: str, ahora: datetime) -> None`.
  - En `economia.py`: `CAMBIO_DE_LA_VIVIENDA = "la_vivienda_por_casillas"` (la marca de `cambios_hechos` y la clave de la carta); `PRECIO_DE_LAS_CASAS_DE_ANTES = {"pequena": 200, "mediana": 500, "grande": 1200}` y `PRECIO_DEL_TICKET_DE_ANTES = 40`, escritos como literales (no se leen de `casas.py` ni de `objetos.py`, que cambian en la Task 8); `@dataclass(frozen=True) class ResumenDelCambio(personas: int = 0, camas: int = 0, monedas: int = 0)` (a cuántas personas tocó, cuántas camas regaló entre puestas y guardadas, y cuántas monedas devolvió); `el_dia_del_cambio(ahora: datetime, rng: random.Random | None = None) -> ResumenDelCambio`.
  - `poner_al_dia(ahora)`: `db.inicializar(ahora)` → `el_dia_del_cambio(ahora)` → `devolver_cosmeticos_retirados(ahora)`; sigue devolviendo el `ResumenDevolucion`. Si el cambio tocó a alguien, deja una línea en el registro con las tres cifras del resumen (sin ids de personas).
  - **Qué hace `el_dia_del_cambio`**, todo bajo un único `BEGIN IMMEDIATE` y sólo si `db._una_sola_vez(con, CAMBIO_DE_LA_VIVIENDA, ahora)` dice que es la primera vez (si no, devuelve `ResumenDelCambio()` sin tocar nada). «Cada persona» es cada pareja (usuario, servidor) con alguna fila en `criaturas`, `monederos`, `inventario`, `casas_propias`, `mobiliario`, `huerto`, `hogar`, `avatares`, `cuentas_web` o `buzon` (por `para_usuario`), recorridas en orden. Para cada una:
    1. **El buzón**: cada regalo sin recoger va a su mochila (+1 de ese objeto) y queda `recogido = 1`.
    2. **El huerto**: cada bancal plantado se cosecha como si estuviera maduro (la cuenta de `economia.cosechar` de hoy, con el `rng`: color heredado o sorteado, de 2 a 4 porotos, y un arcoíris que sustituye a uno), los porotos van a la mochila y la fila se borra.
    3. **Los tickets**: cada `ticket_refugio` de la mochila vuelve en 40 monedas y sale de la mochila (también el que acaba de llegar del buzón).
    4. **Las casas**: por cada fila de `casas_propias`, el precio de su clave en monedas; las filas se borran y a sus gachamones se les vacía `casa_id`. Una clave que no esté en la tabla de precios no paga, y deja un aviso en el registro.
    5. **El departamento**: se crea con `dep.tamano_para(vivos + 1)` y `vivos + 1` camas sencillas puestas donde dice `dep.acomodar_camas`; a quien no tiene ningún gachamon vivo, además, otra cama sencilla guardada.
    6. **Los muebles**: cada fila de `mobiliario` pasa a `muebles` como guardado, con su misma clave, y la fila vieja se borra.
    7. **La carta**: `guardar_carta_en(..., CAMBIO_DE_LA_VIVIENDA, contenido, ahora)` con `{"ancho", "fondo", "camas", "vivos", "casas": [claves], "monedas_por_casas", "muebles": n, "cosecha": {objeto: cuántos}, "tickets": n, "monedas_por_tickets", "regalos": n, "nombres": [{"especie": clave de la especie, "nombre": …}]}`; `nombres` son sus gachamones vivos con `se_nombro_solo = 1` (como todo se publica junto, ese día son justo los reclutas que esperaban nombre).
    Y al final, para todos: `actualizada_en = ahora` en cada gachamon vivo. Las monedas se suman al monedero (`_asegurar_monedero` antes) sin pasar por `operaciones_economia`. Las gemas no se tocan.

- [ ] **Step 1: Escribir las pruebas que fallan**, en `tests/test_dia_del_cambio.py`. La base «de antes» se monta **con filas escritas a mano** en las tablas viejas (`casa_de_antes(usuario, clave) -> id`, `mueble_de_antes(usuario, clave, colocado)`, `plantado(usuario, casa_id, bancal, sembrado)`, `en_la_mochila(usuario, objeto, cuantos)`, `regalo(para, objeto, de_nombre, recogido=0)`), no con las reglas viejas, que se van en la Task 8. `T1 = T0 + timedelta(days=30)`; `MONEDAS_DE_ANTES` y `GEMAS_DE_ANTES` son las 50 y 50 con que nace hoy un monedero; `mochila(usuario, guild="g1")` devuelve lo que hay en su mochila como diccionario.

```python
CAMBIO = economia.CAMBIO_DE_LA_VIVIENDA

def el_cambio(ahora=T1, semilla=7):
    borrar_la_marca(CAMBIO)                 # la base de pruebas nace con la marca puesta
    return economia.el_dia_del_cambio(ahora, random.Random(semilla))

def test_a_cada_quien_su_departamento_con_una_cama_por_gachamon_mas_la_suya():
    for nombre in ("Ana", "Bea", "Cy"):
        nacer(nombre, activa=(nombre == "Ana"))
    assert el_cambio() == economia.ResumenDelCambio(personas=1, camas=4, monedas=0)
    d = db.departamento_leido("u1", "g1")
    assert (d.ancho, d.fondo, d.camas_puestas, d.guardadas) == (4, 4, 4, ())
    assert not db.hay_cama_libre("u1", "g1")

def test_a_quien_no_le_queda_ninguno_le_toca_lo_de_quien_empieza():
    con_monedas(5)                          # una persona con monedero y sin gachamones
    el_cambio()
    d = db.departamento_leido("u1", "g1")
    assert [(p.clave, p.puesta) for p in d.piezas] == [("cama_sencilla", True), ("cama_sencilla", False)]

def test_las_casas_se_devuelven_enteras_y_fuera_del_tope():
    ana = nacer("Ana"); con_monedas(10)
    vive_en(ana, casa_de_antes("u1", "mediana")); casa_de_antes("u1", "grande")
    assert el_cambio().monedas == 1700
    assert economia.saldos("u1", "g1") == economia.Saldos(1710, GEMAS_DE_ANTES)
    assert filas("casas_propias") == [] == filas("operaciones_economia")
    assert db.por_id(ana.id).casa_id is None

def test_los_muebles_de_antes_quedan_guardados():
    mueble_de_antes("u1", "chimenea", colocado=1); mueble_de_antes("u1", "cama", colocado=0)
    el_cambio()
    d = db.departamento_leido("u1", "g1")
    assert sorted(p.clave for p in d.guardadas) == ["cama", "cama_sencilla", "chimenea"]
    assert d.camas_puestas == 1 and filas("mobiliario") == []

def test_lo_plantado_se_cosecha_solo_aunque_no_estuviera_maduro():
    casa = casa_de_antes("u1", "pequena")
    plantado("u1", casa, 1, "poroto_rojo", cuando=T1 - timedelta(minutes=1))
    el_cambio()
    hay = mochila("u1")
    assert 2 <= hay.get("poroto_rojo", 0) + hay.get("poroto_arcoiris", 0) <= 4
    assert hay.get("poroto_arcoiris", 0) <= 1 and filas("huerto") == []

def test_cada_ticket_del_refugio_vuelve_en_40_monedas():
    con_monedas(0); en_la_mochila("u1", "ticket_refugio", 2)
    el_cambio()
    assert economia.saldos("u1", "g1").asciicoins == 80 and "ticket_refugio" not in mochila("u1")

def test_los_regalos_del_buzon_llegan_solos_y_un_ticket_regalado_tambien_se_devuelve():
    con_monedas(0)
    regalo("u1", "golosinas", "Ana"); regalo("u1", "ticket_refugio", "Ana"); regalo("u1", "golosinas", "Bea", recogido=1)
    el_cambio()
    assert mochila("u1") == {"golosinas": 1} and economia.saldos("u1", "g1").asciicoins == 40
    assert db.buzon_de("u1", "g1") == []

def test_el_reloj_de_todos_parte_del_dia_del_cambio():
    ana = nacer("Ana"); dejar_con_hambre(ana, 60.0)    # guardada por última vez en T0, hace 30 días
    el_cambio()
    ahora_es = db.por_id(ana.id)
    assert (ahora_es.actualizada_en, ahora_es.hambre) == (T1, 60.0)

def test_quien_no_tenia_nada_que_devolver_conserva_su_monedero():
    nacer("Ana"); con_monedas(37)
    el_cambio()
    assert economia.saldos("u1", "g1") == economia.Saldos(37, GEMAS_DE_ANTES)

def test_la_carta_cuenta_lo_que_le_toco_a_cada_quien():
    ana = nacer("Ana"); marcar_que_se_nombro_solo(ana)
    casa = casa_de_antes("u1", "mediana"); mueble_de_antes("u1", "maceta", colocado=1)
    en_la_mochila("u1", "ticket_refugio", 1); regalo("u1", "golosinas", "Bea")
    el_cambio()
    assert db.carta_sin_ver("u1", "g1", CAMBIO) == {
        "ancho": 3, "fondo": 3, "camas": 2, "vivos": 1, "casas": ["mediana"], "monedas_por_casas": 500,
        "muebles": 1, "cosecha": {}, "tickets": 1, "monedas_por_tickets": 40, "regalos": 1,
        "nombres": [{"especie": "pulpo", "nombre": "Ana"}],
    }
    db.marcar_carta_vista("u1", "g1", CAMBIO, T1)
    assert db.carta_sin_ver("u1", "g1", CAMBIO) is None

def test_el_cambio_corre_una_sola_vez():
    casa_de_antes("u1", "pequena"); con_monedas(0)
    el_cambio()
    casa_de_antes("u1", "grande")                      # si corriera otra vez, la devolvería
    assert economia.el_dia_del_cambio(T1 + timedelta(hours=1)) == economia.ResumenDelCambio()
    assert economia.saldos("u1", "g1").asciicoins == 200 and len(filas("casas_propias")) == 1

def test_dos_arranques_a_la_vez_hacen_un_solo_cambio():      # dos hilos, como tests/test_db.py:273-282
    casa_de_antes("u1", "pequena"); con_monedas(0); borrar_la_marca(CAMBIO)
    en_dos_hilos(lambda: economia.el_dia_del_cambio(T1, random.Random(1)))
    assert economia.saldos("u1", "g1").asciicoins == 200 and len(db.departamento_leido("u1", "g1").piezas) == 2

def test_si_algo_falla_a_medias_no_queda_nada_hecho_ni_la_marca():
    casa_de_antes("u1", "pequena"); con_monedas(0)
    rompe("BEFORE INSERT ON cartas")
    borrar_la_marca(CAMBIO)
    with pytest.raises(sqlite3.DatabaseError):
        economia.el_dia_del_cambio(T1, random.Random(1))
    assert economia.saldos("u1", "g1").asciicoins == 0 and len(filas("casas_propias")) == 1
    assert filas("departamentos") == [] and CAMBIO not in marcas()

def test_en_una_base_nueva_no_hay_a_quien_cambiar():
    assert el_cambio() == economia.ResumenDelCambio()

def test_vale_para_cada_servidor_por_separado():
    casa_de_antes("u1", "pequena", guild="g1"); casa_de_antes("u1", "grande", guild="g2")
    el_cambio()
    assert (economia.saldos("u1", "g1").asciicoins, economia.saldos("u1", "g2").asciicoins) == (MONEDAS_DE_ANTES + 200, MONEDAS_DE_ANTES + 1200)

def test_veinticinco_gachamones_caben():
    for i in range(25):
        db.crear("u1", "g1", "pulpo", f"N{i}", STATS, T0, activa=(i == 0))
    el_cambio()
    d = db.departamento_leido("u1", "g1")
    assert (d.ancho, d.fondo, d.camas_puestas) == (8, 8, 26)

def test_una_casa_de_clave_desconocida_no_paga_y_no_tumba_el_cambio():
    casa_de_antes("u1", "palacio"); con_monedas(0)
    el_cambio()
    assert economia.saldos("u1", "g1").asciicoins == 0 and filas("casas_propias") == []

def test_el_arranque_hace_el_cambio():
    casa_de_antes("u1", "pequena"); con_monedas(0); borrar_la_marca(CAMBIO)
    economia.poner_al_dia(T1)
    assert economia.saldos("u1", "g1").asciicoins == 200
```

- [ ] **Step 2: Verlas fallar.** Run: `./venv/bin/python -m pytest tests/test_dia_del_cambio.py -q` — Expected: FAIL (`economia` no tiene `CAMBIO_DE_LA_VIVIENDA`).

- [ ] **Step 3: Implementar** la tabla `cartas` con sus tres funciones, y `el_dia_del_cambio` y `poner_al_dia` como dice Interfaces.

- [ ] **Step 4: Verlas pasar y la suite entera.** Run: `./venv/bin/python -m pytest tests/ -q -p no:cacheprovider` — Expected: PASS.

- [ ] **Step 5: Commit** — `feat(reglas): el día del cambio: a cada quien su departamento, sus camas y lo que se le devuelve`.

---

### Task 6: Las rutas del departamento y la carta

**Files:**
- Create: `web/departamento.py`, `web/carta.py`, `tests/test_web_departamento.py`, `tests/test_web_carta.py`
- Modify: `web/app.py` (montar los dos routers), `web/pueblo.py` (`OFRECE`), `web/estado.py` (el campo `carta`), `tests/js/` si `pantallas.js` necesita saber que «departamento» no cambia de pantalla

**Interfaces:**
- Consumes: Tasks 1 a 5; de `web/tienda.py`, `datos_y_evento`, `dicho_si`, `dicho_no`, `no_se_entiende`, `evento_usado`.
- Produces (prefijo `/gachamon/api`; las que escriben llevan `con_cabecera`):
  - `pueblo.OFRECE["casa"] = ("departamento",)`, y en `web/departamento.py` `en_el_departamento(jugador) -> None`: 409 `no_estas_ahi` con la frase nueva si el lugar guardado no ofrece `departamento`. La piden las cuatro rutas.
  - `GET /departamento` → `{ancho, fondo, casillas, comodidad, tope, camas, gachamones, cabe_otro, ampliar: {ancho: coste | null, fondo: coste | null}, puestos: [{id, clave, nombre, icono, x, y, giro, capa, cama, casillas: [[x, y], …]}], guardados: [{id, clave, nombre, icono, capa, cama, ancho, fondo}], saldos: {monedas, gemas}}`. Lo crea si es la primera vez que se mira. Una pieza cuya clave ya no está en el catálogo no se lista.
  - `POST /departamento/poner {mueble_id, x, y, giro}`, `POST /departamento/guardar {mueble_id}`, `POST /departamento/ampliar {eje, evento_id}` → `{ok, clave, mensaje, departamento, estado}`. Un «no» del juego es un 200 con `ok: false`, la clave del motivo y su frase; lo que la pantalla nunca pide (algo que no es un entero, un giro fuera de 0–3, un eje que no existe, un evento que no vale) es un 422. Poner y guardar bien contestan `mensaje: null`.
  - `web/carta.py`: `lineas_de(contenido: dict) -> list[str]` (las frases del plan, en su orden; un recluta cuya especie ya no esté en el catálogo no lleva línea); `GET /carta` → `{"carta": null}` o `{"carta": {"titulo": "Carta del alcalde", "lineas": [...], "firma": "El alcalde"}}`; `POST /carta/vista` → la marca vista y contesta `{"carta": null}`.
  - `estado.armar(...)` gana `"carta": bool`: si tiene una carta sin ver.

- [ ] **Step 1: Escribir las pruebas que fallan.** En `tests/test_web_departamento.py` (`en_casa(cliente)` deja la cuenta en el lugar `casa`; `API = "/gachamon/api"`):

```python
def test_tu_departamento_de_partida(cliente):
    con_gachamon(cliente); en_casa(cliente)
    d = cliente.get(f"{API}/departamento").json()
    assert (d["ancho"], d["fondo"], d["casillas"], d["comodidad"], d["tope"]) == (3, 3, 9, 82, 100)
    assert (d["camas"], d["gachamones"], d["cabe_otro"], d["ampliar"]) == (1, 1, False, {"ancho": 45, "fondo": 45})
    assert [(p["clave"], p["x"], p["y"], p["casillas"]) for p in d["puestos"]] == [("cama_sencilla", 0, 0, [[0, 0], [1, 0]])]
    assert [(g["clave"], g["cama"], g["ancho"], g["fondo"]) for g in d["guardados"]] == [("cama_sencilla", True, 2, 1)]

def test_fuera_de_tu_departamento_no_se_toca(cliente):
    con_gachamon(cliente); ir(cliente, "tienda")
    for metodo, ruta, cuerpo in ((cliente.get, "departamento", None), (cliente.post, "departamento/guardar", {"mueble_id": 1})):
        r = metodo(f"{API}/{ruta}", **({"json": cuerpo, "headers": CABECERA} if cuerpo else {}))
        assert r.status_code == 409 and "Para eso tienes que estar en tu departamento." in r.text

def test_poner_guardar_y_sus_noes(cliente):
    con_gachamon(cliente); en_casa(cliente)
    cama = cliente.get(f"{API}/departamento").json()["guardados"][0]["id"]
    poner = lambda **c: cliente.post(f"{API}/departamento/poner", json={"mueble_id": cama, **c}, headers=CABECERA).json()
    assert (poner(x=2, y=2, giro=0)["clave"], poner(x=2, y=2, giro=0)["mensaje"]) == ("no_cabe", "Ahí no cabe.")
    assert poner(x=0, y=0, giro=0)["mensaje"] == "Ahí ya hay algo."
    bien = poner(x=0, y=1, giro=0)
    assert (bien["ok"], bien["mensaje"], bien["departamento"]["camas"], bien["departamento"]["cabe_otro"]) == (True, None, 2, False)
    no = cliente.post(f"{API}/departamento/guardar", json={"mueble_id": cama}, headers=CABECERA).json()
    assert (no["ok"], no["clave"], no["mensaje"]) == (False, "hace_falta", "Esa cama hace falta: sin ella alguien se queda sin dónde dormir.")
    ajeno = cliente.post(f"{API}/departamento/guardar", json={"mueble_id": 9999}, headers=CABECERA).json()
    assert ajeno["mensaje"] == "Ese mueble no es tuyo."

@pytest.mark.parametrize("cuerpo", [{"mueble_id": "1", "x": 0, "y": 0, "giro": 0}, {"mueble_id": 1, "x": 0.5, "y": 0, "giro": 0},
                                     {"mueble_id": 1, "x": 0, "y": 0, "giro": 4}, {"mueble_id": True, "x": 0, "y": 0, "giro": 0}, {}])
def test_lo_que_la_pantalla_nunca_pide_es_un_422(cliente, cuerpo):
    con_gachamon(cliente); en_casa(cliente)
    assert cliente.post(f"{API}/departamento/poner", json=cuerpo, headers=CABECERA).status_code == 422

def test_ampliar_cobra_una_vez_por_evento(cliente):
    con_gachamon(cliente); en_casa(cliente); con_monedas_web(cliente, 100)
    ampliar = lambda eje, evento: cliente.post(f"{API}/departamento/ampliar", json={"eje": eje, "evento_id": evento}, headers=CABECERA)
    r = ampliar("ancho", "a1").json()
    assert (r["ok"], r["mensaje"], r["estado"]["saldos"]["monedas"]) == (True, "Tu departamento ahora mide 4 × 3.", 55)
    assert ampliar("ancho", "a1").json()["estado"]["saldos"]["monedas"] == 55
    assert ampliar("fondo", "a1").status_code == 409                                  # el mismo evento para otra cosa
    assert ampliar("fondo", "a2").json()["mensaje"] == "Te faltan 5 monedas."
    assert ampliar("arriba", "a3").status_code == 422

def test_en_8_ya_no_crece(cliente): ...     # con el departamento en 8 × 3: ok False, clave "ya_es_el_maximo", «Por ese lado tu departamento ya no puede crecer.», y `ampliar.ancho` es null

def test_cada_quien_ve_y_toca_solo_lo_suyo(cliente): ...   # dos cuentas: el id de un mueble de la otra da «Ese mueble no es tuyo.» y no lo mueve
```

  En `tests/test_web_carta.py`:

```python
TODO = {"ancho": 4, "fondo": 3, "camas": 3, "vivos": 2, "casas": ["mediana", "grande"], "monedas_por_casas": 1700, "muebles": 2,
        "cosecha": {"poroto_rojo": 3}, "tickets": 1, "monedas_por_tickets": 40, "regalos": 1, "nombres": [{"especie": "pulpo", "nombre": "Brisa"}]}

def test_la_carta_dice_todo_lo_que_toco_en_su_orden():
    assert carta.lineas_de(TODO) == [
        "El pueblo cambió, y vengo a contarte qué te toca.",
        "Desde hoy todos vivimos en el mismo edificio. Tu departamento mide 4 × 3 casillas, y lo puedes ampliar.",
        "Te dejé puestas 3 camas: una para ti y una para cada gachamon.",
        "Te devolví lo que costaron tus casas: 1700 monedas.",
        "Tus 2 muebles están en guardados: ponlos donde quieras.",
        "Coseché lo que tenías plantado y lo dejé en tu mochila. El huerto vuelve más adelante.",
        "El refugio cerró. Te devolví 40 monedas por tus tickets.",
        "Lo que te esperaba en el buzón ya está en tu mochila.",
        "Tu pulpo ahora se llama Brisa. Se puso el nombre solo, y se lo puedes cambiar una vez.",
        "Y dos cosas más: ya ningún gachamon muere, y a todos les pasa el tiempo, no sólo al que sale contigo.",
    ]

def test_a_quien_no_le_toco_nada_la_carta_le_dice_lo_justo():
    nada = {**TODO, "ancho": 3, "camas": 1, "vivos": 0, "casas": [], "monedas_por_casas": 0, "muebles": 0, "cosecha": {}, "tickets": 0, "monedas_por_tickets": 0, "regalos": 0, "nombres": []}
    assert carta.lineas_de(nada) == [
        "El pueblo cambió, y vengo a contarte qué te toca.",
        "Desde hoy todos vivimos en el mismo edificio. Tu departamento mide 3 × 3 casillas, y lo puedes ampliar.",
        "Te dejé tu cama puesta y otra guardada, para cuando llegue un gachamon.",
        "Y dos cosas más: ya ningún gachamon muere, y a todos les pasa el tiempo, no sólo al que sale contigo.",
    ]

def test_una_casa_y_un_mueble_van_en_singular():
    lineas = carta.lineas_de({**TODO, "casas": ["pequena"], "monedas_por_casas": 200, "muebles": 1})
    assert "Te devolví lo que costó tu casa: 200 monedas." in lineas and "Tu mueble está en guardados: ponlo donde quieras." in lineas

def test_la_carta_se_ve_una_vez(cliente):
    con_gachamon(cliente)
    assert cliente.get(f"{API}/carta").json() == {"carta": None} and cliente.get(f"{API}/estado").json()["carta"] is False
    con_carta(cliente, TODO)                                    # la escribe en la base para esa cuenta
    vista = cliente.get(f"{API}/carta").json()["carta"]
    assert (vista["titulo"], vista["firma"], len(vista["lineas"])) == ("Carta del alcalde", "El alcalde", 10)
    assert cliente.get(f"{API}/estado").json()["carta"] is True
    assert cliente.post(f"{API}/carta/vista", headers=CABECERA).json() == {"carta": None}
    assert cliente.get(f"{API}/carta").json() == {"carta": None}

def test_la_carta_de_otro_no_es_la_tuya(cliente): ...          # la cuenta 2 no ve ni marca la carta de la cuenta 1
```

- [ ] **Step 2: Verlas fallar.** Run: `./venv/bin/python -m pytest tests/test_web_departamento.py tests/test_web_carta.py -q` — Expected: FAIL (404 en las rutas, `web.carta` no existe).

- [ ] **Step 3: Implementar** `web/departamento.py` y `web/carta.py` como dice Interfaces, montarlos en `web/app.py`, y el campo `carta` del estado. Comprobar que el cliente de hoy sigue enseñando la pantalla del lugar cuando «Tu casa» ofrece `departamento` (y, si no, dejarlo así con su prueba en `tests/js/`).

- [ ] **Step 4: Verlas pasar y la suite entera** (Python y JavaScript). Run: `./venv/bin/python -m pytest tests/ -q -p no:cacheprovider` — Expected: PASS.

- [ ] **Step 5: Commit** — `feat(web): las rutas del departamento y la carta del alcalde`.

---

### Task 7: La página sin casas ni refugio

**Files:**
- Modify: `web/tienda.py`, `web/estado.py`, `web/pueblo.py`, `web/mochila.py`, `globos.py` (las frases del lugar `refugio`), `web/static/js/tienda.js`, `web/static/js/compras.js`, `web/static/js/lugar.js`, `web/static/js/tiempo.js`, `web/static/estilo.css` (las reglas de `data-hogar`), y sus pruebas: `tests/test_web_tienda.py`, `tests/test_web_refugio.py`, `tests/test_web_lugar.py`, `tests/test_pueblo.py`, `tests/test_web_mochila.py`, `tests/test_web_estado.py`, `tests/test_globos.py`, `tests/test_web_cliente.py`, `tests/js/`

**Interfaces:**
- Produces:
  - `GET /tienda` ya no trae `casas`; se va `POST /tienda/casa` con sus frases. La Tienda no lista el ticket del refugio.
  - `estado.armar(...)` ya no trae `hogar` ni `lugar.refugio`; quien no tiene lugar guardado parte en `casa`.
  - `web/pueblo.py`: `de_partida() -> str` (siempre `"casa"`); `aviso(clave: str) -> str | None`: en `refugio`, la frase nueva; en un lugar que abre después, `Esto se abre más adelante.`; si no, `None`. Se van `sin_casa` y `a_la_intemperie`.
  - En el lugar `refugio` el gachamon no dice frases del lugar (cerró); la clave sigue en `globos.DEL_LUGAR` mientras el lugar exista.
  - La mochila ya no trata el ticket.
  - El cliente: la Tienda sin casas; el lugar sin `data-hogar`, sin «quién vive en el refugio» y sin `dondeVive`.

- [ ] **Step 1: Medir.** Cobertura **por ramas** de la suite sobre los archivos de producción, antes de tocar nada; se guarda fuera del repo para comparar al final.

- [ ] **Step 2: Escribir las pruebas que fallan** (en los archivos de hoy, en lugar de las que caen):

```python
def test_la_tienda_ya_no_vende_casas(cliente):
    con_gachamon(cliente); ir(cliente, "tienda")
    assert "casas" not in cliente.get(f"{API}/tienda").json()
    assert cliente.post(f"{API}/tienda/casa", json={"accion": "comprar", "casa": "pequena", "evento_id": "c1"}, headers=CABECERA).status_code in (404, 405)

def test_la_tienda_no_vende_el_ticket_del_refugio(cliente):
    con_gachamon(cliente); ir(cliente, "tienda")
    assert "ticket_refugio" not in {o["clave"] for o in cliente.get(f"{API}/tienda").json()["objetos"]}

def test_el_estado_no_habla_de_hogar_ni_de_refugio(cliente):
    con_gachamon(cliente)
    estado = cliente.get(f"{API}/estado").json()
    assert "hogar" not in estado and "refugio" not in estado["lugar"]
    assert (estado["lugar"]["clave"], estado["lugar"]["aviso"]) == ("casa", None)

def test_el_refugio_sigue_en_el_mapa_pero_cerro(cliente):
    con_gachamon(cliente)
    lugar = ir(cliente, "refugio")["lugar"]
    assert (lugar["aviso"], lugar["ofrece"]) == ("El refugio cerró. Ahora cada quien vive en su departamento.", [])
    assert "refugio" not in lugar

def test_el_aviso_de_un_lugar_ya_no_mira_el_hogar():
    assert pueblo.aviso("plaza") == "Esto se abre más adelante."
    assert pueblo.aviso("tienda") is None and pueblo.aviso("casa") is None and pueblo.de_partida() == "casa"

def test_en_el_refugio_cerrado_el_gachamon_no_dice_frases_de_refugio():
    assert "refugio" in globos.DEL_LUGAR and not globos.DEL_LUGAR["refugio"]
```

- [ ] **Step 3: Verlas fallar.** Run: `./venv/bin/python -m pytest tests/test_web_tienda.py tests/test_web_lugar.py tests/test_web_refugio.py tests/test_pueblo.py -q` — Expected: FAIL en las nuevas.

- [ ] **Step 4: Implementar** lo de arriba, servidor y cliente. Con las casas se van del cliente `preguntaDeVenta`, `preguntaDeMejora`, `loQueTraeLaCasa` y `quienesViven`, con sus pruebas de `tests/js/`.

- [ ] **Step 5: Las pruebas viejas**, con la regla de las pruebas del plan: se borran las de comprar, mejorar y vender casas por la web, las del lugar Refugio con sus inquilinos y su estancia, las del aviso de la intemperie y de «sin casa», y las del ticket en la Tienda y en la mochila. Lo que quede sin otra prueba (un evento reutilizado, un 422 de la Tienda, el aviso de un lugar que abre después) se reescribe contra lo que se queda.

- [ ] **Step 6: Medir otra vez y comparar.** Ninguna rama de un archivo que se queda puede haber perdido su cobertura; el informe trae la comparación y, archivo por archivo, cuántas pruebas se borraron y cuántas se reescribieron.

- [ ] **Step 7: La suite entera** (Python y JavaScript). Run: `./venv/bin/python -m pytest tests/ -q -p no:cacheprovider` — Expected: PASS.

- [ ] **Step 8: Commit** — `refactor(web): la página sin casas ni refugio`.

---

### Task 8: Fuera las reglas de antes

**Files:**
- Delete: `casas.py`; de `web/static/arte/`, los dibujos que queden huérfanos (los iconos de las casas y el del ticket)
- Modify: `economia.py`, `db.py`, `identidad.py`, `huerto.py`, `objetos.py`, `aventura.py` (sólo si nombra lo que se va), `web/tienda.py` (`donde_sirve`), `web/arte.py`, `web/static/datos/arte.json`, `tests/test_departamento.py` (deja de comparar con `casas`), y las pruebas de lo que se va: `tests/test_casas.py`, `tests/test_migracion_casas.py`, `tests/test_motivos.py`, `tests/test_acciones_unicas.py`, `tests/test_usar_objeto.py`, `tests/test_identidad.py`, `tests/test_arte.py`, `tests/test_aventura.py`
- Create: `tests/test_cocina.py`, `tests/test_buzon.py` (las pruebas de cocinar, de las sopaipillas y del buzón que hoy viven en `tests/test_casas.py`), `tests/test_sin_casas.py`

**Interfaces:**
- Se van:
  - de `economia.py`: `comprar_casa`, `vender_casa`, `mudar_gachamon` y sus tres resultados; `plantar`, `regar`, `cosechar`, `_huerto_abierto`, `_bancal_de` y `ResultadoHuerto`; lo del ticket en `_usar`, `_aplicar_objeto` y `_no_haria_nada`;
  - de `db.py`: `_primera_casa_con_sitio` (un gachamon nace con `casa_id` vacío), `hogar_de`, `_hogar_de`, `alargar_el_refugio_en`, `_hay_hogar`, `_hogar_leido`, `_casas_de`, `hogar_leido`, `estancia_empezada`, `abrir_o_cerrar_la_casa`, `vender_la_casa_en`, `anadir_casa_en`, `mejorar_casa_en`, `inquilinos_de`, `inquilinos_en`, `acoger_a_los_sin_casa_en`, `mudar_criatura_en`, `huerto_de`, `_huerto_de`, `plantar_en`, `regar_en` y `arrancar_en`;
  - `identidad.sin_plazo_de_refugio`; de `huerto.py`, `BANCALES`, `bancales_de`, `Bancal`, `plantables` y las horas de cultivo; de `objetos.py`, `ticket_refugio` y el campo `dias_de_refugio`; de `web/tienda.py`, `HUERTO`, `REFUGIO` y sus ramas en `donde_sirve`, `se_le_vende` y `_nota`.
- Se quedan: las tablas y columnas viejas y `db._migrar_casas`; `economia.cocinar` con lo que usa; el buzón (`mandar_regalo`, `buzon_de`, `recoger_del_buzon`, `regalar`), en pausa; `sim.Criatura.casa_id` y `db.CAMPOS` (quitarlos toca la función que escribe cada fila); `sim.Ritmo.suelo_de_hambre`.
- Cambia: `objetos.CATALOGO["semilla"].se_vende` es `False` (ni se vende ni sale de botín; la mochila la sigue enseñando).

- [ ] **Step 1: Medir** la cobertura por ramas, como en la Task 7.

- [ ] **Step 2: Escribir las pruebas que fallan**, en `tests/test_sin_casas.py`:

```python
def test_ya_no_hay_modulo_de_casas_ni_quien_lo_importe():
    assert not (RAIZ / "casas.py").exists()
    for archivo in archivos_de_produccion():                 # los .py que sigue git, sin tests/
        assert not re.search(r"^\s*(import casas|from casas )", archivo.read_text(), re.M), archivo

@pytest.mark.parametrize("modulo, nombre", [
    (economia, "comprar_casa"), (economia, "vender_casa"), (economia, "mudar_gachamon"), (economia, "plantar"),
    (economia, "regar"), (economia, "cosechar"), (db, "hogar_leido"), (db, "_hogar_leido"), (db, "_casas_de"),
    (db, "alargar_el_refugio_en"), (identidad, "sin_plazo_de_refugio"), (huerto, "BANCALES"), (huerto, "Bancal"),
])
def test_las_reglas_de_antes_se_fueron(modulo, nombre):
    assert not hasattr(modulo, nombre)

def test_no_se_fue_ninguna_tabla_ni_columna_de_antes():
    for tabla in ("casas_propias", "mobiliario", "huerto", "hogar", "buzon"):
        assert tabla in tablas()
    assert "casa_id" in columnas("criaturas")

def test_el_ticket_ya_no_existe_y_la_semilla_ni_se_vende_ni_sale_de_botin():
    assert "ticket_refugio" not in obj.CATALOGO and not obj.CATALOGO["semilla"].se_vende
    rng = random.Random(1)
    assert all(av.tirar_objeto(rng).clave not in ("semilla", "ticket_refugio") for _ in range(2000))

def test_una_base_de_antes_todavia_llega_hasta_el_cambio():
    # con tests/test_migracion_casas.py: `volver_al_esquema_viejo()` + una casa de las de «una por persona» + `economia.poner_al_dia(T1)`
    # → la casa se devolvió en monedas y la persona tiene su departamento.
    ...

def test_un_gachamon_nace_sin_casa():
    assert nacer("Ana").casa_id is None
```

- [ ] **Step 3: Verlas fallar.** Run: `./venv/bin/python -m pytest tests/test_sin_casas.py -q` — Expected: FAIL.

- [ ] **Step 4: Borrar** lo de la lista, y con ello sus pruebas, por la regla de las pruebas del plan. Antes de borrar cada símbolo, `git grep` de quién lo llama: si algo de producción todavía lo usa, la tarea para y lo dice. De `tests/test_casas.py` se salvan, mudándose, las pruebas de cocinar y de las sopaipillas (`tests/test_cocina.py`) y las del buzón que no dependan de abrir o cerrar la casa (`tests/test_buzon.py`); las de `_migrar_casas` se quedan en `tests/test_migracion_casas.py`, afirmando sobre las filas de `casas_propias` en vez de sobre `Hogar`. Las dos pruebas de `tests/test_departamento.py` que comparaban con `casas` pasan a comparar con los valores escritos: el nombre, el emoji, el precio y la comodidad de los catorce, y el alivio en 75, 80, 100, 125 y 150.

- [ ] **Step 5: El arte.** `web/arte.py` deja de pedir iconos de casas y el del ticket; `arte.json` se regenera; los dibujos huérfanos se borran con `git rm`; `tests/test_arte.py` cuenta lo que queda.

- [ ] **Step 6: Medir otra vez y comparar**, como en la Task 7: ninguna rama de lo que se queda pierde su cobertura (`cocinar`, el buzón, el monedero, los eventos, `_migrar_casas`, `usar_objeto` con los demás objetos, `tirar_objeto`).

- [ ] **Step 7: La suite entera.** Run: `./venv/bin/python -m pytest tests/ -q -p no:cacheprovider` — Expected: PASS, sin avisos nuevos. Y `git grep -n "refugio\|intemperie\|casas\." -- '*.py' ':!tests'`: lo que quede tiene que ser del esquema, de `_migrar_casas`, del día del cambio o del lugar del mapa; el informe lo lista.

- [ ] **Step 8: Commit** — `refactor(reglas): fuera las casas, el refugio, la intemperie y el huerto por casa`.

---

### Task 9: Los documentos

**Files:**
- Modify: `AGENTS.md`, `README.md`, `docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md`

**Interfaces:**
- `AGENTS.md`, «Invariantes del dominio»: salen los que ya no son verdad (el tope del plantel por `db.MAXIMO_PLANTEL`; el refugio, `MAXIMO_CASAS`, cada gachamon en una casa, el aforo, el reloj del refugio, vender y mejorar casas, «se tiene un mueble de cada», el refugio no se amuebla, la intemperie, visitar; el huerto por casa y vender una casa con lo plantado; `identidad.sin_plazo_de_refugio`; el ticket que no alargaría la estancia) y entran, concisos y sin SHAs:
  - cada persona tiene un solo departamento por servidor, que parte en 3 × 3 y se amplía por filas o columnas hasta 8 × 8;
  - el servidor manda sobre qué mueble hay en qué casilla; el catálogo y sus formas viven en `departamento.py`, que es puro;
  - tener un mueble no es tenerlo puesto; guardar nunca destruye; se puede tener más de uno de cada;
  - hacen falta tantas camas puestas como gachamones vivos más una, la tuya: reclutar pide una cama libre y una cama que hace falta no se guarda (mientras exista el huevo, el que nace de él no la pide);
  - la comodidad es una puntuación: parte de 80, cada tipo de mueble puesto suma una vez y el tope depende de las casillas; frena el ánimo de todos los que viven ahí y no toca el hambre;
  - antes de cambiar lo que fija el ritmo (poner, guardar, ampliar) se pone al día y se guarda a todos los vivos, en la misma transacción;
  - ampliar se compra en el departamento; lo demás, en la Tienda; lo que se compra llega a guardados;
  - el día del cambio corre una sola vez, con su marca en `cambios_hechos` en la misma transacción, y deja a cada persona una carta que se ve una vez;
  - las casas, el refugio, la intemperie y el huerto por casa ya no existen; sus tablas siguen en el esquema, sin uso.
- `README.md`: donde cuenta las casas, el refugio, los muebles y el huerto, lo que es verdad ahora, sin reescribir secciones enteras.
- El documento de pendientes gana la sección **«Salió al ejecutar el rework 4 (la vivienda por casillas)»**, con la voz de las anteriores y sin SHAs, números de tarea ni ids. El controlador le pasa al implementador un archivo de notas con lo decidido durante la ejecución; como mínimo trae: lo decidido; **el día de publicar** (hay que tomar y guardar aparte la copia de la base de antes; qué línea deja el arranque en el registro; la carta); **si hubiera que volver atrás** (restaurar esa copia es la única vuelta limpia: el cambio borra las filas convertidas y paga las devoluciones; arrancar el código de antes sobre la base ya cambiada dejaría a la gente sin casas y con las monedas; y la segunda trampa de toda marca: una base restaurada a medias); lo pendiente para los planes que siguen (el huevo que no pide cama, comprar sin gachamon, la pantalla, el lugar Refugio, las tablas viejas sin uso).

- [ ] **Step 1: Escribir** los tres documentos con lo de arriba y las notas del controlador.
- [ ] **Step 2: Comprobar** que cada invariante nuevo de `AGENTS.md` es verdad en el código (`git grep` de cada símbolo que nombra) y que no queda ninguno que hable de lo que se fue.
- [ ] **Step 3: La verificación completa.** Run: `./venv/bin/python -m pre_commit run --all-files` — Expected: PASS.
- [ ] **Step 4: Commit** — `docs: la vivienda por casillas, en la política, el README y los pendientes`.
