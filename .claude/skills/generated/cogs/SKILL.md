---
name: cogs
description: "Skill for the Cogs area of Gachamones-BOT. 95 symbols across 18 files."
---

# Cogs

95 symbols | 18 files | Cohesion: 67%

## When to Use

- Working with code in `cogs/`
- Understanding how como_se_llama, ahora_utc, ascender_de_la_incubadora work
- Modifying cogs-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `cogs/competencias.py` | _invitados_validos, carrera, sumo, _retar, Competencias (+12) |
| `db.py` | ahora_utc, _a_criatura, _a_valores, ascender_de_la_incubadora, plantel (+10) |
| `cogs/aventura.py` | aventura, __init__, _refrescar_botones, texto, golosinas (+9) |
| `tests/test_db.py` | test_alimentar_aleja_la_hora_de_la_muerte, test_una_criatura_muerta_no_vuelve_a_salir_como_pendiente, test_el_aviso_de_hambre_se_dispara_una_sola_vez, test_alimentarla_hace_que_vuelva_a_avisar_mas_adelante, test_una_criatura_muerta_no_genera_avisos (+6) |
| `cogs/mascota.py` | huevo, mascota, revisar_muertes, _canal_de, _avisar_hambrientas (+1) |
| `cogs/social.py` | _tabla, jardin_cmd, ranking, cementerio, Social (+1) |
| `cogs/charla.py` | on_message, _va_conmigo, _formatear, _limite_alcanzado, cog_unload |
| `vistas.py` | on_submit, congelar, _canal_anterior, responder_pantalla, publicar_pantalla |
| `simulacion.py` | tasa_hambre_por_hora, momento_de_aviso, momento_de_muerte, avanzar |
| `tests/test_simulacion.py` | test_momento_de_muerte_coincide_con_la_simulacion, test_el_aviso_salta_al_llegar_al_umbral, test_el_aviso_deja_margen_de_reaccion |

## Entry Points

Start here when exploring this area:

- **`como_se_llama`** (Function) — `competir.py:473`
- **`ahora_utc`** (Function) — `db.py:289`
- **`ascender_de_la_incubadora`** (Function) — `db.py:358`
- **`plantel`** (Function) — `db.py:375`
- **`guardar`** (Function) — `db.py:507`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `Aventura` | Class | `cogs/aventura.py` | 262 |
| `Competencias` | Class | `cogs/competencias.py` | 251 |
| `Mascota` | Class | `cogs/mascota.py` | 85 |
| `Social` | Class | `cogs/social.py` | 169 |
| `como_se_llama` | Function | `competir.py` | 473 |
| `ahora_utc` | Function | `db.py` | 289 |
| `ascender_de_la_incubadora` | Function | `db.py` | 358 |
| `plantel` | Function | `db.py` | 375 |
| `guardar` | Function | `db.py` | 507 |
| `pendientes_de_aviso` | Function | `db.py` | 551 |
| `esperas` | Function | `db.py` | 591 |
| `efectos_activos` | Function | `db.py` | 700 |
| `vivas_del_servidor` | Function | `db.py` | 717 |
| `ranking` | Function | `db.py` | 733 |
| `cementerio` | Function | `db.py` | 824 |
| `tasa_hambre_por_hora` | Function | `simulacion.py` | 353 |
| `momento_de_aviso` | Function | `simulacion.py` | 362 |
| `momento_de_muerte` | Function | `simulacion.py` | 376 |
| `avanzar` | Function | `simulacion.py` | 386 |
| `test_no_se_puede_invitar_al_mismo_dos_veces` | Function | `tests/test_carga.py` | 232 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Revisar_muertes → Tasa_hambre_por_hora` | intra_community | 7 |
| `Callback → Tasa_hambre_por_hora` | cross_community | 7 |
| `Golosinas → Tasa_hambre_por_hora` | cross_community | 7 |
| `Carrera → Tasa_hambre_por_hora` | intra_community | 7 |
| `Sumo → Tasa_hambre_por_hora` | intra_community | 7 |
| `Presumir → Tasa_hambre_por_hora` | cross_community | 7 |
| `Esperar → Tasa_hambre_por_hora` | cross_community | 7 |
| `On_submit → Tasa_hambre_por_hora` | cross_community | 7 |
| `Aventura → Tasa_hambre_por_hora` | intra_community | 6 |
| `Disputar → Tasa_hambre_por_hora` | cross_community | 6 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Tests | 79 calls |
| Cluster_62 | 2 calls |
| Cluster_33 | 1 calls |

## How to Explore

1. `context({name: "como_se_llama"})` — see callers and callees
2. `query({search_query: "cogs"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings (source→sink data flows), when indexed with `--pdg`
