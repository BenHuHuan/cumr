# UniLab precedents adopted by CUMR

Inspected [BenHuHuan/UniLab](https://github.com/BenHuHuan/UniLab) at
[`9e3bb6b814d694d52bfff0f074d0a2b8ede6f032`](https://github.com/BenHuHuan/UniLab/tree/9e3bb6b814d694d52bfff0f074d0a2b8ede6f032)
on 2026-09-11. This is a reference for development organization, not a CUMR
runtime dependency. CUMR's rules were written for its actual UMR-derived code.

| UniLab source | Principle retained | CUMR application |
| --- | --- | --- |
| [AGENTS.md](https://github.com/BenHuHuan/UniLab/blob/9e3bb6b814d694d52bfff0f074d0a2b8ede6f032/AGENTS.md) | Short durable guide; inspect owners, preserve unrelated work, report evidence. | One canonical guide with generated GLM/Kimi/Claude/Codex/Grok and singular AGENT copies. |
| [CONTRIBUTING.md](https://github.com/BenHuHuan/UniLab/blob/9e3bb6b814d694d52bfff0f074d0a2b8ede6f032/CONTRIBUTING.md) | Focused iteration, complete final checks, explicit contract impact. | `make check`, `make test-all`, validation matrix and PR template. |
| [ADR-0001](https://github.com/BenHuHuan/UniLab/blob/9e3bb6b814d694d52bfff0f074d0a2b8ede6f032/docs/sphinx/source/adr/ADR-0001-runtime-model-and-layer-boundaries.md) | Fix behavior in its owning layer; keep dependencies directional. | Protect contact/config/terrain/model owners from orchestration dependencies; preserve shared final correction. |
| [ADR-0003](https://github.com/BenHuHuan/UniLab/blob/9e3bb6b814d694d52bfff0f074d0a2b8ede6f032/docs/sphinx/source/adr/ADR-0003-task-owner-and-config-compose-contract.md) | Config identity has one declared owner and composition must preserve it. | Robot JSON owns identity and limits; source defaults and solver settings keep separate owners, with shared path resolution. |
| [Architecture boundaries](https://github.com/BenHuHuan/UniLab/blob/9e3bb6b814d694d52bfff0f074d0a2b8ede6f032/docs/sphinx/source/en/4-developer_guide/1-architecture/3-layer_boundaries.md) | Asset/metadata work belongs to preparation, not hot loops. | Build meshes, terrain and slot bindings before per-frame retargeting. |
| [ADR template](https://github.com/BenHuHuan/UniLab/blob/9e3bb6b814d694d52bfff0f074d0a2b8ede6f032/docs/sphinx/source/adr/ADR-TEMPLATE.md) | Record decisions, alternatives, consequences and concrete evidence. | Small ADR index and template linked to CUMR contracts and tests. |

CUMR does not introduce UniLab's `uni_rl`/`unisim` runtime, RL IPC, Hydra owner
YAML, `uv` environment or external asset hub. Its current owners live under
`scripts/`, which contains both libraries and entrypoints; the existing Conda,
JSON and Git LFS workflow remains in use. The numerical retargeting method and
published results are unchanged by this governance work.

The root [AGENTS.md](../../AGENTS.md) is authoritative. Model-specific files
contain the same generated guide, not independent policies. If a client does
not automatically load its named Markdown file, explicitly supply that file
or AGENTS.md as project context. File presence does not install or configure a
model, guarantee automatic loading, or create tool permissions.

Static enforcement is intentionally scoped: declared imports, shared contact
call sites, guide synchronization, protected Git paths, documentation links and
evidence hashes. Semantic requirements also depend on numerical tests, integration
runs and review. A Markdown MUST is not a security sandbox or a complete program
proof. Changes to repository branch-protection settings are outside this setup.
