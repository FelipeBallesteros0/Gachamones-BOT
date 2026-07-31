---
name: cluster-43
description: "Skill for the Cluster_43 area of Gachamones-BOT. 4 symbols across 1 files."
---

# Cluster_43

4 symbols | 1 files | Cohesion: 55%

## When to Use

- Understanding how _contar_acreditadas, _resolver_recompensa, _registrar_recompensa work
- Modifying cluster_43-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `economia.py` | _contar_acreditadas, _resolver_recompensa, _registrar_recompensa, _replay_competencia |

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `_contar_acreditadas` | Function | `economia.py` | 122 |
| `_resolver_recompensa` | Function | `economia.py` | 133 |
| `_registrar_recompensa` | Function | `economia.py` | 150 |
| `_replay_competencia` | Function | `economia.py` | 277 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Tests | 1 calls |

## How to Explore

1. `context({name: "_contar_acreditadas"})` — see callers and callees
2. `query({search_query: "cluster_43"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings (source→sink data flows), when indexed with `--pdg`
