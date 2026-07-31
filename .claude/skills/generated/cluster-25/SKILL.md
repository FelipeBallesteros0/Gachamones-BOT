---
name: cluster-25
description: "Skill for the Cluster_25 area of Gachamones-BOT. 4 symbols across 1 files."
---

# Cluster_25

4 symbols | 1 files | Cohesion: 75%

## When to Use

- Understanding how resolver, tirar, acumulados work
- Modifying cluster_25-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `competir.py` | resolver, tirar, acumulados, _torneo |

## Entry Points

Start here when exploring this area:

- **`resolver`** (Function) — `competir.py:185`
- **`tirar`** (Function) — `competir.py:199`
- **`acumulados`** (Function) — `competir.py:207`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `resolver` | Function | `competir.py` | 185 |
| `tirar` | Function | `competir.py` | 199 |
| `acumulados` | Function | `competir.py` | 207 |
| `_torneo` | Function | `competir.py` | 272 |

## How to Explore

1. `context({name: "resolver"})` — see callers and callees
2. `query({search_query: "cluster_25"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings (source→sink data flows), when indexed with `--pdg`
