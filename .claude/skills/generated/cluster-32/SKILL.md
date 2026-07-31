---
name: cluster-32
description: "Skill for the Cluster_32 area of Gachamones-BOT. 6 symbols across 2 files."
---

# Cluster_32

6 symbols | 2 files | Cohesion: 33%

## When to Use

- Understanding how criatura_activa_en, espera_en, poner_cooldown_en work
- Modifying cluster_32-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `db.py` | criatura_activa_en, espera_en, poner_cooldown_en, efecto_activo_en |
| `economia.py` | _fecha_economica, ejecutar_competencia |

## Entry Points

Start here when exploring this area:

- **`criatura_activa_en`** (Function) — `db.py:339`
- **`espera_en`** (Function) — `db.py:565`
- **`poner_cooldown_en`** (Function) — `db.py:577`
- **`efecto_activo_en`** (Function) — `db.py:682`
- **`ejecutar_competencia`** (Function) — `economia.py:325`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `criatura_activa_en` | Function | `db.py` | 339 |
| `espera_en` | Function | `db.py` | 565 |
| `poner_cooldown_en` | Function | `db.py` | 577 |
| `efecto_activo_en` | Function | `db.py` | 682 |
| `ejecutar_competencia` | Function | `economia.py` | 325 |
| `_fecha_economica` | Function | `economia.py` | 95 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Disputar → Tasa_hambre_por_hora` | cross_community | 6 |
| `Carrera → Criatura` | cross_community | 6 |
| `Carrera → _fecha` | cross_community | 6 |
| `Sumo → Criatura` | cross_community | 6 |
| `Sumo → _fecha` | cross_community | 6 |
| `On_submit → Criatura` | cross_community | 6 |
| `On_submit → _fecha` | cross_community | 6 |
| `Alimentar → Criatura` | cross_community | 6 |
| `Alimentar → _fecha` | cross_community | 6 |
| `Jugar → Criatura` | cross_community | 6 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Tests | 4 calls |
| Cogs | 4 calls |
| Cluster_42 | 2 calls |

## How to Explore

1. `context({name: "criatura_activa_en"})` — see callers and callees
2. `query({search_query: "cluster_32"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings (source→sink data flows), when indexed with `--pdg`
