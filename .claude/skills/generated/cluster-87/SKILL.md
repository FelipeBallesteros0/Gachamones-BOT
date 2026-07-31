---
name: cluster-87
description: "Skill for the Cluster_87 area of Gachamones-BOT. 8 symbols across 1 files."
---

# Cluster_87

8 symbols | 1 files | Cohesion: 64%

## When to Use

- Understanding how texto_recibo_cuidado, alimentar, jugar work
- Modifying cluster_87-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `vistas.py` | alimentar, jugar, entrenar, limpiar, actualizar (+3) |

## Entry Points

Start here when exploring this area:

- **`texto_recibo_cuidado`** (Function) — `vistas.py:273`
- **`alimentar`** (Method) — `vistas.py:71`
- **`jugar`** (Method) — `vistas.py:76`
- **`entrenar`** (Method) — `vistas.py:81`
- **`limpiar`** (Method) — `vistas.py:86`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `texto_recibo_cuidado` | Function | `vistas.py` | 273 |
| `alimentar` | Method | `vistas.py` | 71 |
| `jugar` | Method | `vistas.py` | 76 |
| `entrenar` | Method | `vistas.py` | 81 |
| `limpiar` | Method | `vistas.py` | 86 |
| `actualizar` | Method | `vistas.py` | 91 |
| `_ejecutar` | Function | `vistas.py` | 201 |
| `_congelar_pulsada` | Function | `vistas.py` | 292 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Alimentar → Criatura` | cross_community | 6 |
| `Alimentar → _fecha` | cross_community | 6 |
| `Jugar → Criatura` | cross_community | 6 |
| `Jugar → _fecha` | cross_community | 6 |
| `Entrenar → Criatura` | cross_community | 6 |
| `Entrenar → _fecha` | cross_community | 6 |
| `Limpiar → Criatura` | cross_community | 6 |
| `Limpiar → _fecha` | cross_community | 6 |
| `Actualizar → Criatura` | cross_community | 6 |
| `Actualizar → _fecha` | cross_community | 6 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cogs | 3 calls |
| Tests | 3 calls |
| Cluster_62 | 1 calls |

## How to Explore

1. `context({name: "texto_recibo_cuidado"})` — see callers and callees
2. `query({search_query: "cluster_87"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings (source→sink data flows), when indexed with `--pdg`
