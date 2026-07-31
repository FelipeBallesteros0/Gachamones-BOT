---
name: cluster-62
description: "Skill for the Cluster_62 area of Gachamones-BOT. 7 symbols across 1 files."
---

# Cluster_62

7 symbols | 1 files | Cohesion: 52%

## When to Use

- Understanding how render_lapida, render_evolucion, render_huevo work
- Modifying cluster_62-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pantalla.py` | _fila, _fila_stats, _lineas_arte, _formato_edad, render_lapida (+2) |

## Entry Points

Start here when exploring this area:

- **`render_lapida`** (Function) — `pantalla.py:257`
- **`render_evolucion`** (Function) — `pantalla.py:282`
- **`render_huevo`** (Function) — `pantalla.py:355`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `render_lapida` | Function | `pantalla.py` | 257 |
| `render_evolucion` | Function | `pantalla.py` | 282 |
| `render_huevo` | Function | `pantalla.py` | 355 |
| `_fila` | Function | `pantalla.py` | 48 |
| `_fila_stats` | Function | `pantalla.py` | 103 |
| `_lineas_arte` | Function | `pantalla.py` | 123 |
| `_formato_edad` | Function | `pantalla.py` | 165 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Render_lapida → _fila` | intra_community | 3 |
| `Render_lapida → _c` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Tests | 5 calls |

## How to Explore

1. `context({name: "render_lapida"})` — see callers and callees
2. `query({search_query: "cluster_62"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings (source→sink data flows), when indexed with `--pdg`
