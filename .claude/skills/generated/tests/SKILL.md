---
name: tests
description: "Skill for the Tests area of Gachamones-BOT. 665 symbols across 41 files."
---

# Tests

665 symbols | 41 files | Cohesion: 72%

## When to Use

- Working with code in `tests/`
- Understanding how render, xp_para_subir, xp_acumulada_para work
- Modifying tests-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `tests/test_ia.py` | criatura, respuesta_de, correr, test_una_respuesta_buena_llega_limpia, test_el_prompt_y_el_historial_llegan_en_orden (+58) |
| `tests/test_competir.py` | competidor, combate, espera_error, test_son_tres_tramos_y_cada_uno_es_stat_mas_1d20, test_gana_quien_suma_mas_no_quien_gana_mas_tramos (+53) |
| `tests/test_db.py` | bd_temporal, test_migracion_de_una_base_de_datos_antigua, test_migracion_pone_macho_y_un_caracter_al_azar_a_las_de_antes, test_la_migracion_no_le_cambia_el_caracter_a_quien_ya_lo_tiene, test_migracion_añade_canal_id_sin_perder_criaturas (+49) |
| `tests/test_simulacion.py` | test_la_curva_cumple_lo_prometido, test_pasado_el_ultimo_nivel_se_sigue_subiendo, criatura, test_avanzar_en_dos_tramos_da_lo_mismo_que_en_uno, test_una_criatura_muerta_ya_no_cambia (+45) |
| `tests/test_pantalla.py` | sin_color, lineas_del_marco, criatura, comprobar_marco, test_todas_las_especies_en_todos_los_estados_cuadran (+41) |
| `tests/test_aventura.py` | criatura, test_el_bioma_se_sortea_y_salen_todos, test_son_dos_pruebas_de_stat_mas_1d20, test_cada_prueba_sortea_su_estadistica, test_la_prueba_usa_la_estadistica_que_toca (+32) |
| `tests/test_personalidad.py` | criatura, test_el_prompt_lleva_nombre_especie_y_dueño, test_el_prompt_incluye_la_muletilla_y_el_contacto, test_cada_especie_genera_un_prompt_distinto, test_las_reglas_prohiben_decir_numeros_y_romper_el_personaje (+27) |
| `db.py` | conectar, inicializar, _columnas, _migrar_monederos, crear (+22) |
| `tests/test_carga.py` | bd_temporal, test_el_enfriamiento_de_competir_frena_a_todos, reto_de, test_si_una_baja_deja_al_sumo_en_tres_no_se_juega, test_un_torneo_al_que_faltan_dos_se_juega_como_un_sumo_normal (+22) |
| `tests/test_tienda.py` | bd_temporal, test_la_pocion_de_comida_llena_y_se_guarda, con_hambre, test_las_golosinas_alimentan_lo_que_dicen, test_las_golosinas_no_pasan_de_cien (+18) |

## Entry Points

Start here when exploring this area:

- **`render`** (Function) — `pantalla.py:182`
- **`xp_para_subir`** (Function) — `simulacion.py:288`
- **`xp_acumulada_para`** (Function) — `simulacion.py:295`
- **`sin_color`** (Function) — `tests/test_pantalla.py:12`
- **`lineas_del_marco`** (Function) — `tests/test_pantalla.py:16`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `Competidor` | Class | `competir.py` | 54 |
| `ResultadoAccion` | Class | `simulacion.py` | 435 |
| `Saldos` | Class | `economia.py` | 27 |
| `Objeto` | Class | `objetos.py` | 31 |
| `EncuentroView` | Class | `cogs/aventura.py` | 77 |
| `HablarModal` | Class | `cogs/aventura.py` | 246 |
| `NombrarView` | Class | `vistas.py` | 170 |
| `Salvaje` | Class | `aventura.py` | 245 |
| `Encuentro` | Class | `aventura.py` | 329 |
| `Criatura` | Class | `simulacion.py` | 174 |
| `Prueba` | Class | `aventura.py` | 117 |
| `Salida` | Class | `aventura.py` | 134 |
| `ErrorIA` | Class | `ia.py` | 74 |
| `ErrorPermanente` | Class | `ia.py` | 82 |
| `ErrorTransitorio` | Class | `ia.py` | 78 |
| `Bloque` | Class | `jardin.py` | 24 |
| `render` | Function | `pantalla.py` | 182 |
| `xp_para_subir` | Function | `simulacion.py` | 288 |
| `xp_acumulada_para` | Function | `simulacion.py` | 295 |
| `sin_color` | Function | `tests/test_pantalla.py` | 12 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Callback → Tasa_hambre_por_hora` | cross_community | 7 |
| `Golosinas → Tasa_hambre_por_hora` | cross_community | 7 |
| `Abrir_mochila → _asegurar_monedero` | cross_community | 7 |
| `Abrir_tienda → _asegurar_monedero` | cross_community | 7 |
| `Presumir → Tasa_hambre_por_hora` | cross_community | 7 |
| `Esperar → Tasa_hambre_por_hora` | cross_community | 7 |
| `On_submit → Tasa_hambre_por_hora` | cross_community | 7 |
| `Abrir_mochila → Conectar` | cross_community | 6 |
| `Abrir_tienda → Conectar` | cross_community | 6 |
| `Cambiar_activo → Concordar` | cross_community | 6 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cogs | 66 calls |
| Cluster_33 | 11 calls |
| Cluster_62 | 9 calls |
| Cluster_28 | 9 calls |
| Cluster_43 | 2 calls |
| Cluster_26 | 2 calls |
| Cluster_87 | 1 calls |

## How to Explore

1. `context({name: "render"})` — see callers and callees
2. `query({search_query: "tests"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings (source→sink data flows), when indexed with `--pdg`
