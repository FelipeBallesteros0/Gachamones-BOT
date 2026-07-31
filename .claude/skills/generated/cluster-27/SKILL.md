---
name: cluster-27
description: "Skill for the Cluster_27 area of Gachamones-BOT. 9 symbols across 1 files."
---

# Cluster_27

9 symbols | 1 files | Cohesion: 100%

## When to Use

- Understanding how fotogramas_carrera, fotogramas_sumo work
- Modifying cluster_27-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `competir.py` | _cabecera, _acumulados, _pista, _fila_corredor, _anchos_del_dado (+4) |

## Entry Points

Start here when exploring this area:

- **`fotogramas_carrera`** (Function) — `competir.py:401`
- **`fotogramas_sumo`** (Function) — `competir.py:438`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `fotogramas_carrera` | Function | `competir.py` | 401 |
| `fotogramas_sumo` | Function | `competir.py` | 438 |
| `_cabecera` | Function | `competir.py` | 323 |
| `_acumulados` | Function | `competir.py` | 336 |
| `_pista` | Function | `competir.py` | 344 |
| `_fila_corredor` | Function | `competir.py` | 354 |
| `_anchos_del_dado` | Function | `competir.py` | 367 |
| `_fila_dado` | Function | `competir.py` | 383 |
| `_dohyo` | Function | `competir.py` | 431 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Fotogramas_carrera → Fila` | intra_community | 3 |
| `Fotogramas_carrera → Pintar` | intra_community | 3 |
| `Fotogramas_carrera → _pista` | intra_community | 3 |

## How to Explore

1. `context({name: "fotogramas_carrera"})` — see callers and callees
2. `query({search_query: "cluster_27"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings (source→sink data flows), when indexed with `--pdg`
