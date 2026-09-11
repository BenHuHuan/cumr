# Foot contact and terrain

The default solver enables `solver.contact_stabilization`. It works with the
single-motion SMPL-X/SOMA solver, the streaming batch solver and the Character
solver. Sources without semantic foot groups (for example uniform NR surfaces)
report `no_foot_probes`; their existing surface and collision constraints remain
available.

This adapts the speed/height contact gates, interval-mean targets and filtered
support-height idea described in
[robot_retargeter](https://github.com/ccrpRepo/robot_retargeter/tree/f1418972319287c1b93af0f7a3b445f613cff5e4).
The implementation is written for UMR's surface correspondences and QP solver;
it does not replace correspondence learning with skeleton IK.

## What changes

- Several points spread across each mapped sole act as independent probes.
  A planted toe can remain constrained while the heel lifts. Sole selection uses
  both source and robot reference surfaces, rather than treating an ankle as the
  bottom of the foot.
- Contact requires both low surface clearance and low speed. A wider exit gate
  adds hysteresis; very short contact intervals are rejected. Speed is windowed
  path length divided by elapsed time, so oscillating motion cannot cancel out.
  All durations use seconds and the effective FPS after stride selection.
- Each continuous contact interval has a fixed world-space target, projected
  onto the terrain. Weights ramp at touchdown/liftoff and are normalized per foot.
  In the single-motion solver these constraints also participate in the initial
  solve, and replace the height-only foot anchors during swing.
- A final QP pass restores contact after LQR smoothing or bidirectional selection.
  Its interval targets are rebased once onto the fitted robot foot trajectories,
  so differing human/robot sole widths do not impose the human foot's geometry.
  It tracks the filtered robot surface and pose, retains joint bounds and the
  configured ground/self/object collision constraints, and adds stance targets.
  A penalty on changes in the correction preserves the filtered motion's frame
  increments, reducing abrupt changes in joint motion at contact transitions.
  Streaming solvers collect probe trajectories across chunks before building one
  full-sequence contact plan; anchors do not reset at chunk boundaries.
- An optional bounded low-pass support-height correction compensates small
  source height offsets. It holds the correction during flight to preserve jumps.
  Leave it off for human/object or scene interactions, where moving only the
  body would change the relationship to the object.
- Contact settings and the heightfield's contents participate in result cache
  validation. Existing results are regenerated when these inputs change.

UMR already scales source motion using source/robot height, supports configured
knee lower bounds (the G1 config uses 0.1 radians), joint limits, self collision,
temporal smoothing and bidirectional initialization. The reference project's
per-bone scaling and two-bone knee reconstruction are not applied on top of UMR:
those would deform the source surface used by its learned correspondence. Keep
robot-specific knee limits in `robot.joint_limits` to prevent straight-knee
singularities without introducing a second skeleton mapping.

## Configuration

Place overrides inside your robot config. Defaults are shown in
[`humanoid_retarget_defaults.json`](../humanoid_retarget_defaults.json).

```json
{
  "solver": {
    "contact_stabilization": {
      "enabled": true,
      "height_enter": 0.035,
      "height_exit": 0.055,
      "speed_enter": 0.18,
      "speed_exit": 0.30,
      "speed_window_seconds": 0.067,
      "min_contact_seconds": 0.067,
      "blend_seconds": 0.067,
      "points_per_foot": 6,
      "position_cost": 100000.0,
      "projection_iters": 8,
      "projection_pose_cost": 1.0,
      "projection_velocity_cost": 500.0,
      "height_adaptation": false,
      "height_filter_seconds": 0.1,
      "height_max_correction": 0.05,
      "tolerance": 0.003
    }
  }
}
```

Heights are metres; speeds are metres/second. `position_cost` is a squared-error
cost, distributed across each foot's active probes. `projection_iters: 0` skips
the final pass; batch/Character need that pass for stance locking.
`enabled: false` restores the original contact behavior. Terrain configuration
is independent of stance locking.

`projection_velocity_cost` controls smoothing of the correction across frames.
Larger values preserve the original joint motion more closely, with a possible
increase in foot drift. The final pass can still change joint acceleration/jerk;
compare those metrics along with contact error when tuning a new robot or motion.

Use lower speed thresholds for deliberately sliding motions. For floating source
data, check its coordinate frame and floor alignment first; increasing the height
threshold enough to catch an airborne foot will incorrectly label it as support.
`height_adaptation` only corrects offsets inside the detection and correction
bounds; it does not infer arbitrary terrain or recover missing contacts.

## Terrain

The default surface is `z = 0`. An explicit plane can represent a ramp:

```json
{
  "solver": {
    "contact_stabilization": {
      "terrain": {"type": "plane", "height": 0.0, "slope": [0.1, 0.0]}
    }
  }
}
```

Here `z = height + slope[0] * x + slope[1] * y`. For nonplanar terrain use:

```json
{
  "solver": {
    "contact_stabilization": {
      "terrain": {"type": "heightfield", "path": "terrain.npz"}
    }
  }
}
```

`terrain.npz` contains `heights` (a finite `[ny, nx]` array), `origin_xy` (the
world XY position of sample `[0, 0]`) and `cell_size` (positive scalar or `[dx, dy]`).
Rows increase along world Y and columns along world X. At least two samples per
axis are required. Outside the grid, the floor is the minimum sampled elevation;
optional `outside_height` may lower that floor.

Coordinates are in the **scaled, Z-up robot retarget world**, after source
alignment/scaling. The source motion must already describe steps on that terrain;
this feature does not plan new footsteps or convert a flat walk into stair climbing.
Static heightfields represent a single height per XY location, not overhangs or
moving platforms. GRAIL's existing object/scene collision path remains separate.

The same terrain is queried by detection and ground constraints and embedded into
the saved `.terrain.floating_mjcf.xml` for visualization. Explicit terrain replaces
world floor planes in the generated scene. It does not edit the original robot
MJCF. Heightfields use MuJoCo's own triangulation and ray intersections. The inline
heightfield format is verified with MuJoCo 3.3.7.

## Inspect the result

Alongside `motion.npz`, the solver writes:

- `motion.contact.json`: effective settings/signature, measured stance slip
  (tangential speed), anchor error, support-height error, and penetration before
  and after projection. With no detected support, contact metrics are `null`.
- `motion.contact.npz`: frame IDs, FPS, probe slot IDs, foot labels, contact masks,
  fixed targets (and the original `source_targets`), weights, source speeds, height offsets and actual robot probe
  positions before/after correction.

`tolerance` is a reporting threshold, not a promise of exact contact. Stance
constraints are soft because source/robot foot dimensions and multiple simultaneous
contacts can conflict. Check measured errors and the motion; increase iterations
or adjust contact detection/costs where needed. Ground hard constraints operate on
the configured surface samples or collision geoms. This is kinematic retargeting;
it does not establish friction-cone feasibility or dynamic balance.

```bash
python -m unittest discover -s tests -v
python scripts/humanoid_retarget_pipeline.py \
  --config robot_configs/humanoid_retarget_unitree_g1_example.json \
  --force-retarget --skip-view

# Compare an old result and a stabilized result of the same source frames/robot.
# --plot is optional and requires matplotlib.
python scripts/compare_contact_results.py \
  --baseline output/baseline.npz --result output/stabilized.npz \
  --out output/comparison.json --plot output/comparison.png
```

## Validation on the included G1 motion

The [published evidence bundle](validation/README.md) includes portable robot
trajectories, probe diagnostics, parameter snapshots, checksums, the original
UMR rerun check and commands to replay or rebuild the experiment.

A CPU comparison used `dance1_subject2` source frames 300–599 at 30 FPS,
4096 correspondence slots trained for 500 epochs, the G1 example config, and
the defaults above. Baseline and stabilized motion were evaluated with the same
1936 probe-contact samples. MuJoCo version: 3.3.7.

| Metric | Original contact behavior | Stabilized |
| --- | ---: | ---: |
| Mean stance slip | 15.85 cm/s | 1.65 cm/s |
| Stance slip, 95th percentile | 38.61 cm/s | 6.77 cm/s |
| Support-height error, 95th percentile | 34.55 mm | 2.03 mm |
| Scalar-joint jerk, 95th percentile (rad/frame³) | 0.0550 | 0.0628 |

Mean slip fell 89.6%; joint jerk increased about 14%. This demonstrates the
contact/smoothness tradeoff, rather than a guarantee for all sequences. The final
maximum terrain penetration across sampled robot surface slots was below 0.001 mm
in this run. A 30-frame, stride-2, seven-frame-chunk bidirectional batch run,
a 12-frame Character smoke run, and a 12-frame heightfield run also completed.
The unit tests cover false contacts, hysteresis, heel/toe independence, frame-rate
handling, height correction during flight, terrain/scene agreement, cache
invalidation, and constrained IK with joint limits.
