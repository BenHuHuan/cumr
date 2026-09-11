# Architecture decision records

ADRs record durable structural decisions. The mandatory contribution rules are
in [CONTRACTS.md](../architecture/CONTRACTS.md). Routine fixes within those rules
do not need a new ADR.

| ADR | Status | Decision |
| --- | --- | --- |
| [0001](0001-owner-boundaries.md) | Accepted | Logical owners, one contact implementation and one canonical agent guide. |
| [0002](0002-artifacts-and-evidence.md) | Accepted | Public artifact compatibility and frozen, replayable evidence. |

For a new decision, copy [TEMPLATE.md](TEMPLATE.md), choose the next number,
describe the existing owner/contract and add the verification and migration.
If superseding a decision, link both records. Keep the index current. Do not
reclassify an invariant as optional merely to suppress a failing test.
