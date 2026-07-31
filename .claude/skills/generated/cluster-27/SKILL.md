---
name: cluster-27
description: "Skill for the Cluster_27 area of Gachamones-BOT. 6 symbols across 1 files."
---

# Cluster_27

6 symbols | 1 files | Cohesion: 56%

## When to Use

- Understanding how podio work
- Modifying cluster_27-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `competir.py` | _pieza_del_podio, _fila_del_podio, _dibujo_del_podio, _fila_puesto, podio (+1) |

## Entry Points

Start here when exploring this area:

- **`podio`** (Function) — `competir.py:590`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `podio` | Function | `competir.py` | 590 |
| `_pieza_del_podio` | Function | `competir.py` | 518 |
| `_fila_del_podio` | Function | `competir.py` | 540 |
| `_dibujo_del_podio` | Function | `competir.py` | 558 |
| `_fila_puesto` | Function | `competir.py` | 573 |
| `_nota_de_desempates` | Function | `competir.py` | 621 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Resumen → Pintar` | cross_community | 5 |
| `Resumen → _pieza_del_podio` | cross_community | 4 |

## How to Explore

1. `context({name: "podio"})` — see callers and callees
2. `query({search_query: "cluster_27"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings (source→sink data flows), when indexed with `--pdg`
