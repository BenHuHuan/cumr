# ADR-0001: Logical owners and shared contact implementation

- Status: Accepted
- Date: 2026-09-11
- Owner: CUMR maintainers
- Contracts: C01, C03, C04, C05

## Context

CUMR inherits UMR's script-oriented layout. Many modules in `scripts/` are
libraries, and several retarget entrypoints share contact behavior. Without
explicit ownership, future changes can introduce reverse dependencies or
separate implementations that disagree across single, batch and Character runs.
Model-specific instructions can also drift if edited independently.

## Decision

Keep existing public paths and define logical owners in ARCHITECTURE.md.
Protect contact math, terrain, configuration, model loading and geom helpers
from higher-level pipeline dependencies. All three supported solvers retain
the shared final contact correction. Mesh/terrain preparation remains outside
frame loops. Robot/source identities stay in their current configuration owners.

Keep AGENTS.md as one instruction source. Generate the six requested
compatibility/model guides and check their equality in CI. The executable
contract registry covers a bounded subset of architecture rules; behavioral
tests and review remain mandatory for numerical/lifecycle changes.

## Alternatives considered

- Move every module into a new package now: rejected because a naming/governance
  change does not justify breaking imports, scripts and cached workflows.
- Copy contact logic into each entrypoint: rejected because chunk handling and
  final correction would become separate behavioral owners.
- Maintain model guides by hand: rejected because conflicting rules would lack
  a clear source of truth.

## Consequences and compatibility

CUMR branding and the repository name may change while original UMR CLI paths,
protocol identifiers and the existing Python environment remain compatible.
New owner dependencies require a justified contract change and appropriate tests.
The static guard does not establish the runtime ordering of every path; lifecycle
changes still need integration evidence.

## Evidence

- [Owner map](../../ARCHITECTURE.md)
- [Executable contracts](../architecture/contracts.json)
- [Checker](../../scripts/check_architecture_contracts.py)
- [Guide generator](../../scripts/sync_agent_guides.py)
- [Negative tests](../../tests/test_architecture_contracts.py)
- [UniLab precedent](../development/unilab_reference.md)
