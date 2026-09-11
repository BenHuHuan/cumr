# Developing CUMR

Read [AGENTS.md](AGENTS.md), [ARCHITECTURE.md](ARCHITECTURE.md) and the relevant
[mandatory contract](docs/architecture/CONTRACTS.md) before a change. These rules
apply to human and model-assisted contributions. GLM, Kimi, Claude, Codex and
Grok receive the same generated guide; no model has a separate architecture policy.

## Environment and commands

Use the Python 3.12 environment and dependencies in the main README. The existing
Conda environment can still be named `umr`; a project rename does not require
reinstalling the environment or renaming inherited UMR entrypoints.

```bash
conda activate umr
make agents       # regenerate the six compatibility/model guides from AGENTS.md
make check        # guide consistency, declared architecture boundaries and docs
make test         # regression tests; no licensed SMPL-X weights required
make evidence     # replay the published FK measurements; no retraining
make test-all     # check + tests + evidence replay
```

Override the interpreter when needed: `make PYTHON=/path/to/python test-all`.
Equivalent direct commands are in the [Makefile](Makefile). `make check` uses
only the standard library, and can run before installing numerical dependencies.
It is not a whole-project type checker or a proof of all runtime invariants.

## Development rules

1. Define the requested outcome and identify its owner: config, source adapter,
   correspondence, contact, terrain, solver, pipeline, assets or evidence.
2. Preserve unrelated local changes. Avoid broad formatting, surprise dependency
   upgrades, new fallback behavior and duplicated implementations.
3. Reuse existing owners and public helpers. New modules are named for their
   responsibility. Do not create another catch-all `utils` layer or a second
   source of configuration truth.
4. Keep source comments and API documentation in English. User-facing support
   claims must describe their evidence level and actual limits.
5. Fix the cause of a failed check. Do not weaken thresholds, remove assertions
   or update a frozen measurement merely to make the gate pass.
6. Add tests for numerical, state, cache and contract changes. Choose a failure
   the test can detect. Pure wording edits do not need new unit tests.
7. Document structural decisions through [ADRs](docs/adr/README.md), including
   owner, compatibility, rejected alternatives and verification. Routine fixes
   within an existing contract do not require an ADR or a separate approval loop.

## Validation by change type

| Change | Required local evidence |
| --- | --- |
| Wording, model guides, developer docs | `make check`; regenerate guides when AGENTS.md changes. |
| Contract checker or CI | Checker negative tests and `make test-all`. |
| Robot/config/source adapter | `make test-all`; relevant model/FK and short integration check. |
| Contact/solver/cache/frame behavior | `make test-all`; relevant motion, chunk or terrain run; report numeric differences. |
| New quality/performance claim | A separately identified experiment with inputs, environment, baselines, raw outputs and limitations. |

Do not launch long training or broad benchmarks for a wording change. CI runs
contract checks, regression tests and metric replay without SMPL-X weights.
Licensed-model integration runs are local and must be reported separately.

## Commits, reviews and publication

Prefer focused Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
The PR description states the problem, resulting behavior, contract/ADR impact,
exact validation commands and remaining limitations. Use the PR template.
Commit, publish or send external messages only within the user's authorization;
an instruction file is not authorization. Existing explicit authorization does
not need to be requested again.

Before a publication, inspect staged files, preserve upstream history and
licenses, check LFS assets, and verify remote CI for the pushed commit. Report
failures or unavailable checks accurately. Branch protection and required status
settings are repository-admin choices; documenting a gate does not enable them.

## Source of these rules

The organization of owners, contracts, ADRs and evidence requirements is informed
by [UniLab](docs/development/unilab_reference.md). CUMR uses its existing Conda,
JSON, MuJoCo and Git LFS workflow; it does not adopt UniLab's RL runtime or Hydra
configuration system as part of this governance change.
