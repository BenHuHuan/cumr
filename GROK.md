<!-- Generated from AGENTS.md by scripts/sync_agent_guides.py; do not edit this copy. -->

# CUMR Agent Guide

This is the canonical repository guide for GLM, Kimi, Claude, Codex, Grok and
other coding agents. `AGENT.md`, `GLM.md`, `KIMI.md`, `CLAUDE.md`, `CODEX.md` and
`GROK.md` are generated copies; edit this file and run `make agents`.

## Working agreement

- Follow the user's authorized scope and higher-priority host instructions.
  Repository rules do not override them or require repeated permission for
  work already authorized. Ask only when missing information changes the result;
  continue independent work while awaiting an answer.
- Read [ARCHITECTURE.md](ARCHITECTURE.md), the relevant
  [contracts](docs/architecture/CONTRACTS.md), and the owning code/config/tests
  before implementation. Inspect `git status` and preserve unrelated work.
- Fix behavior in its owner module. Make the smallest complete change; avoid
  unrelated refactors, global formatting and duplicated solver/config logic.
- Use `rg` for search. Use Python 3.12 in the installed CUMR environment; the
  documented `umr` Conda environment and existing script names remain compatible.
- Keep comments, public docstrings and developer rules in English. Match the
  user's language in conversation. Report facts, assumptions and limitations
  separately; do not turn a smoke run into a performance or hardware claim.
- If multiple agents are explicitly authorized, give overlapping files one
  writer and consolidate results before editing. These files do not themselves
  authorize agent spawning, external messages, publication or destructive work.

## Mandatory architecture contracts

- **C01 Ownership:** contact math and terrain must not import CLI, pipeline,
  training or source-model code. Existing owner modules live under `scripts/`;
  that directory is not evidence that all its files are entrypoints.
- **C02 Coordinates:** retarget world is Z-up/metres; root quaternions use wxyz.
  Convert source frames explicitly once. Durations use seconds and effective FPS.
- **C03 Configuration:** robot identity/T-pose/limits belong in robot configs;
  source defaults and shared solver settings keep their own owners. Resolve
  file paths using the shared configuration helpers, not the shell's cwd.
- **C04 Contact:** single-motion, batch and Character share the final contact
  correction. Preserve interval continuity, swing release and heel/toe freedom.
  Retain joint bounds and enabled collision constraints after smoothing.
- **C05 Terrain:** detection, optimization and visualization use the same
  terrain. Parse assets/build bindings before frame loops; do not mutate source MJCF.
- **C06 Artifacts:** preserve final `qpos`/FPS/frame/joint metadata and cache
  signatures. Contract changes require migration/invalidation, not silent reuse.
- **C07 Assets:** keep licensed SMPL-X weights, caches and logs out of Git.
  Preserve upstream sources/licenses; use Git LFS for tracked robot meshes.
- **C08 Evidence:** retain raw measurements, configs, hashes and tradeoffs.
  A support claim must state whether it is unit-tested, smoke-tested or measured.
  Preserve the original UMR citation and Huan Hu's separate CUMR citation.

## Change and validation workflow

1. Identify the owning contract and relevant existing ADR. Add an ADR for a new
   structural decision; routine fixes do not need one. Update implementation,
   tests, contract and migration together when an interface changes.
2. Run focused checks while iterating. Run `make check` for docs/governance changes;
   run `make test-all` for code, configs, models, artifacts or numerical claims.
   Use `PYTHON=/path/to/python` if the environment is not activated.
3. Do not remove a check, relax a numerical tolerance or rewrite golden evidence
   just to hide a failure. Document a justified contract change and its evidence.
4. Commit/push only within the user's authorization. For publication, inspect
   staged files, preserve upstream history, and verify CI on the actual pushed
   commit. Never claim a queued or failed CI run passed.
5. Report the change, commands/results, relevant evidence and remaining limits.

Commands and contribution details: [CONTRIBUTING.md](CONTRIBUTING.md).
Architecture precedent and differences: [UniLab reference](docs/development/unilab_reference.md).
