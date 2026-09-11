# TienKung models for CUMR

These assets come from [Open-X-Humanoid/TienKung_URDF](https://github.com/Open-X-Humanoid/TienKung_URDF)
at revision [`5c221783fb92fcc4af891ef1dc0502963caf2266`](https://github.com/Open-X-Humanoid/TienKung_URDF/tree/5c221783fb92fcc4af891ef1dc0502963caf2266),
imported on 2026-09-11. Upstream names use `tiangong`; CUMR uses those same
identifiers. The meshes and original model descriptions are covered by the
upstream [OpenAtom Open Hardware License 1.0](LICENSE), reproduced unchanged.
Original attribution belongs to Open-X-Humanoid and the upstream contributors.

| Robot | CUMR identifier | Actuated body joints | Original description |
| --- | --- | ---: | --- |
| TienKung 2 Dex | `tiangong2dex` | 31 | `tiangong2dex_urdf/tiangong2dex_torq.xml` and `urdf/tiangong2dex.urdf` |
| TienKung 2 Pro | `tiangong2pro` | 30 | `tiangong2pro_urdf/tiangong2pro_torq.xml` and `urdf/tiangong2.0_pro_urdf.urdf` |
| TienKung 3 | `tiangong3` | 25 | `tiangong3_urdf/urdf/tiangong3.urdf` |

Each model also has a floating base (6 velocity DOFs, 7 position coordinates).
These configurations target the upstream body models. Separate articulated
hand variants are not included; the Dex name does not imply finger DOFs.
TienKung 3's supplied URDF has four joints per arm, without wrist joints.

## CUMR modifications

**The `model.xml` files and two OBJ meshes are CUMR adaptations, not unchanged
upstream releases.** Original URDFs, 2-series `source.xml`, and STL meshes are
preserved alongside the adapters. Only meshes referenced by these body models
are included.

- For 2 Dex and 2 Pro, replace the undefined `visualgeom` material reference
  with the existing default material. Restore the omitted pelvis mass and
  full inertia tensor from the corresponding URDF, avoiding mass inferred
  from overlapping visual and collision meshes.
- Intersect the 2-series MJCF and URDF position limits. Several Dex MJCF
  limits extend beyond its URDF limits; CUMR respects the narrower interval.
- Convert TienKung 3's URDF with MuJoCo 3.3.7, retaining visual geometry,
  collision geometry, fixed sensor links, joint axes, limits and inertias.
  Add a floating pelvis, floor, named visual/collision groups and torque
  actuators bounded by URDF effort limits. This is a kinematic retargeting
  adapter; no actuator dynamics or tracking controller have been calibrated.
- Convert TienKung 3's `pelvis.STL` and `waist_pitch_link.STL` into OBJ because
  they exceed MuJoCo's 200000-triangle STL limit. Preserve all triangles and
  vertex coordinates; no mesh decimation is applied.
- Set each model's initial root height so its lowest sole vertex is at z=0.
  Upstream 2-series XML places the ankle joint origin at z=0 instead.
- Configure horizontal T-poses using approximately +85/-85 degree shoulder
  roll, accounting for the model's +5/-5 degree shoulder mounting rotation.
  Center correspondence on `waist_yaw_link`; match the SMPL center to the
  same fraction of standing height. Robot configs prevent knee and elbow
  hyperextension while retaining the remaining model limits.

Rebuild the adapters and converted OBJ meshes from the bundled sources:

```bash
conda activate umr
python assets/tienkung/rebuild_models.py
```

The generated models use relative mesh paths. STL and OBJ files follow the
repository's Git LFS rules. No external ROS installation is needed at runtime.

## Run

```bash
python scripts/humanoid_retarget_pipeline.py \
  --config robot_configs/humanoid_retarget_tiangong2dex_example.json
python scripts/humanoid_retarget_pipeline.py \
  --config robot_configs/humanoid_retarget_tiangong2pro_example.json
python scripts/humanoid_retarget_pipeline.py \
  --config robot_configs/humanoid_retarget_tiangong3_example.json
```

These configs inherit the standard pipeline defaults, including foot-contact
stabilization and terrain support. The first run trains correspondence for
the selected robot and source template; G1 correspondence cannot be reused.
Append `--skip-view` for a run without a viewer. On a CPU-only machine, set
`retarget.smplx_device` and `correspondence.train.device` to `cpu` in a copy
of the config.

Validate the adapters against the original URDF kinematics:

```bash
python -m unittest discover -s tests -p 'test_tienkung_models.py' -v
```

Integration validation also ran all three configurations through dataset
construction, 100 CPU training epochs with 512 points, and retargeting frames
300–323 of `dance1_subject2`, including final contact correction. Outputs had
finite, normalized floating-base poses and respected configured joint limits.
This short run verifies pipeline integration, not final motion quality:
support-height residuals with these reduced training settings still exceed
the 3 mm contact tolerance. Production defaults remain 4096 points and 500
epochs. Local smoke outputs and diagnostics are in
`output/tienkung_validation/summary.json` (generated, not distributed).
The publication includes a portable copy of these reports in
[`docs/validation/tienkung`](../../docs/validation/tienkung/summary.json).
