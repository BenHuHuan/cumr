# Mandatory architecture contracts

These are contribution requirements for CUMR, including AI-assisted changes.
Their scope is implementation and review inside the repository. They do not
override user authorization or higher-priority host instructions.

## C01 — Ownership and dependencies

Contact detection/anchors/metrics are owned by `contact_stabilization.py`.
Terrain is owned by `contact_terrain.py`. Configuration is owned by
`humanoid_retarget_config.py`. None may import pipeline or retarget entrypoints.
Contact math stays independent of MuJoCo, Torch and SMPL-X; terrain may use
MuJoCo but must not load body models or training code. Source model loading
must not import pipeline/contact solving. New shared behavior goes to its owner,
not a copied implementation in each entrypoint.

**Gate:** AST import allowlists in `contracts.json`, including imports inside
functions; final-correction call-site checks for all three supported solvers.
Aliases and dynamic imports cannot be used to evade a boundary. Dynamic import
mechanisms are not permitted in the protected low-level modules.

## C02 — Coordinates, units and time

- Retarget/terrain world uses metres and Z-up. Canonical SMPL surfaces use Y-up;
  native Character surfaces may use Z-up. Explicit source conversion owns this
  difference; no silent double conversion or inferred axis from robot names.
- Free-root position is `qpos[:3]`; orientation is normalized **wxyz** at
  `qpos[3:7]`. Scalar joint values occupy the remaining model-defined addresses.
- Speeds use metres/second and the effective FPS after stride selection.
  Contact/filter durations use seconds. Preserve source `frame_ids` in outputs.
- Terrain NPZ is `heights[ny,nx]`, `origin_xy[2]`, positive scalar or `[dx,dy]`
  cell size; rows increase along world Y. Query MuJoCo's actual triangulation.

**Gate:** native-Z-up/SMPL-Y-up probe tests, FPS/stride tests, MuJoCo terrain tests,
and published artifact checks/replay. New source adapters add a frame test.

## C03 — Configuration identity and ownership

Robot config owns the robot name, MJCF, center, T-pose, limits and optional
robot-specific correspondence alignment. Source defaults own source adapters
and source-specific objective settings. Shared solver defaults own contact
parameters; `ContactSettings` validates effective contact settings.

Use shared config load/resolve helpers. `--defaults` composition must preserve
the declaring config's paths; subprocesses and cache decisions must see the same
effective values. Do not add another independent precedence resolver. Do not
encode new robot-name branches in generic contact/terrain/solver code.

**Gate:** config helpers, contact validation/signature tests, TienKung config/FK
tests, and the actual reproduction path. A new composition feature requires a
test spanning owner-relative paths and the subprocess or stage that consumes it.

## C04 — Contact lifecycle and solver constraints

Detect support from both speed and terrain clearance with hysteresis and minimum
duration. Keep independent sole probes so toe support can coexist with heel lift.
Use fixed targets for a continuous interval; release targets in swing and do not
reset intervals at chunk boundaries. Optional height correction holds during
flight and must not shift a tracked body away from its object/scene interaction.

The single-motion, batch and Character paths must call the shared
`finalize_contact_motion`. Contact correction follows the trajectory selection
and filtering applicable to that path. Preserve active scalar-joint bounds and
configured terrain/self/object constraints; do not add an unconstrained qpos
filter after the final correction. Soft contact residuals must be reported.

**Gate:** shared call-site guard; stance, swing, heel/toe, flight and constrained
IK tests; metric replay. Sequence/chunk changes additionally require a relevant
streaming smoke run, because static call presence cannot prove lifecycle order.

## C05 — Terrain and model preparation

Detection, optimization and saved visualization use one support-surface
definition. Build terrain, bindings, mesh metadata and collision caches on
preparation paths, outside per-frame loops. Materialize generated scenes separately
from original MJCF. Static heightfield support does not imply overhangs, moving
platforms, terrain inference or footstep planning.

**Gate:** terrain/scene agreement tests; independent model FK and mesh tests;
review of preparation versus frame-loop code. New terrain capability requires
matching query/scene tests before support is advertised.

## C06 — Output and cache compatibility

Final robot output contains finite `qpos[T,nq]`, positive FPS, corresponding
source frame IDs, model/joint ordering and source identity. Final trajectories
respect configured joint bounds and unit root quaternions. Contact sidecars
contain the probe bindings and common masks required to compare the same frames.
Keep the legacy public field names and UMR overlay identifiers compatible.

Contact signatures include effective settings, terrain contents and a semantic
version. A behavior change that invalidates cached results must change the
signature inputs/version and add an invalidation test. Existing cache keys are
not a universal content hash of all code/assets; a change to inputs outside
their coverage must explicitly force rebuilding or extend compatibility checks.

**Gate:** published final-output shapes/metadata checked against the required
fields in `contracts.json`; cache invalidation tests and metric replay. Review
and document migration for format changes; never silently reinterpret old data.

## C07 — Assets, provenance and publication

Do not track SMPL-X body-model weights, generated floating MJCF, training caches,
local logs, credentials or private datasets. Existing explicitly published
validation artifacts are separate from those caches. Robot meshes use Git LFS.
Retain upstream names, sources, attribution and license text verbatim; adapt into
separate files with modification notices and reproducible conversion scripts.

**Gate:** protected-path checks against Git's tracked and unignored file list;
LFS checks before asset publication; numerical model tests. Local licensed model
files may exist under ignored `smpl/` paths and are not an error by themselves.

## C08 — Evidence, naming and claims

CUMR is the extension's name; UMR remains the name of Cao et al.'s original
method. Preserve both citations and all model/reference provenance. Public URLs
and software citation refer to `BenHuHuan/cumr`; inherited API/environment names
remain compatible.

Published comparisons retain data/configs/probes, source revision, input hashes,
environment and metric definitions. Compare identical robots, source frames,
FPS and support masks. State smoothness/contact tradeoffs and distinguish unit
coverage, integration smoke, measured motion quality and hardware validation.
Golden evidence cannot be silently replaced to satisfy a changed algorithm.
Create a separately identified experiment for new numerical claims.

**Gate:** evidence checksums and FK metric replay; 19 numerical/model regression
tests at the initial publication; current test suite additionally checks the
architecture guard itself. A Markdown rule or a green smoke test alone does not
establish support quality or dynamic feasibility.
