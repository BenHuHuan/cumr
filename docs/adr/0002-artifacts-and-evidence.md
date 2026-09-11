# ADR-0002: Compatible artifacts and replayable evidence

- Status: Accepted
- Date: 2026-09-11
- Owner: CUMR maintainers
- Contracts: C02, C06, C07, C08

## Context

Retarget results are consumed by viewers, comparison tools and existing users.
Cached correspondence/contact data depends on frame and configuration semantics.
CUMR also publishes a measured baseline and stabilized result, including a
contact/smoothness tradeoff. A rename must not silently alter either API or data.

## Decision

Retain the existing final-qpos metadata, coordinate/unit conventions and UMR
overlay identifiers. Incompatible numerical or format changes require explicit
migration or cache invalidation. Publish experiment inputs, effective config,
environment, original revision, raw robot/probe outputs and artifact checksums.
New results use separately identified experiments; preserve the original bundle.

Keep body-model weights, working outputs and training caches out of Git.
Keep robot meshes under Git LFS and preserve third-party source/license files.
Preserve the original UMR citation; identify Huan Hu's extension separately as
CUMR. A branding-only update may correct descriptive names and URLs without
changing numerical outputs or their checksums.

## Alternatives considered

- Rename all inherited APIs together with the title: rejected because existing
  callers and licensed overlay manifests would no longer be compatible.
- Publish only a percentage or plot: rejected because its inputs, definitions
  and baseline could not be independently replayed.
- Update golden metrics whenever code changes: rejected because that could hide
  regressions and erase the provenance of earlier claims.

## Consequences and verification

The contact-disabled baseline must remain identifiable separately from the
already contact-aware trajectory before final projection. Evidence replay
requires no licensed SMPL-X weights. New benchmarks must disclose limitations,
including contact residuals and smoothness costs. Kinematic feasibility does
not imply dynamic/hardware success.

- [Published protocol and limitations](../validation/README.md)
- [Frozen artifact manifest](../validation/g1_dance_300_599/manifest.json)
- [Replay and full-run tool](../../scripts/reproduce_contact_validation.py)
- [Artifact and guard tests](../../tests/test_architecture_contracts.py)
