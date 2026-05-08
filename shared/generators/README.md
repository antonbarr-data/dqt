# Shared Generators

Code-generation scripts that produce TypeScript and Python from shared sources.
Implemented in Phase 2+ as the library and config files they depend on are built.

| Script | Source | Output | Make target |
|--------|--------|--------|-------------|
| `scales_to_ts.py` | `packages/dqt/src/dqt/algorithms/_scales.py` | `shared/generated/stat-scales.ts` | `make stats-scales` |
| `engines_to_ts.py` | `packages/dqt/src/dqt/adapters/*/config.py` | `shared/generated/engines.ts` | `make engines` |
| `enums_to_ts.py` | `shared/config/*.config.json` | `shared/generated/enums.ts` | `make enums` |
| `enums_to_python.py` | `shared/config/*.config.json` | `shared/generated/enums.py` | `make enums` |

All output files are git-ignored. Run `make gen` to regenerate everything.
