# Re_UMR: Contact-Stabilized Unified Motion Retargeting

**Re_UMR** is Huan Hu's extension of [UMR](https://github.com/hanyang9/UMR),
adding stance-foot stabilization, static terrain contact, reproducible contact
measurements, and TienKung 2 Dex / 2 Pro / 3 robot adapters.
The original learned surface correspondence and retargeting framework is by
**Cao et al. (2026)**. Please [cite both UMR and Re_UMR](#citation) when using
this extension. Upstream history is preserved from
[`d6bb761`](https://github.com/hanyang9/UMR/commit/d6bb76123d19afb7c2c1c84162d1af1f142a61ed).

[Installation](#installation) · [Quick start](#quick-start) ·
[Robots](#supported-robots) · [Evidence and reproduction](docs/validation/README.md) ·
[Contact settings](docs/contact_stabilization.md) · [Changes](CHANGELOG.md)

## What Re_UMR adds

| Addition | Implementation and scope |
| --- | --- |
| Reduce stance-foot sliding | Speed + height contact detection, hysteresis, independent sole probes, fixed targets per contact interval, and contact correction after smoothing. |
| Preserve support across chunks | Shared final correction for single-motion, batch and Character paths; intervals span chunk boundaries. |
| Contact with static terrain | Planes, ramps and heightfields use matching detection, constraints and saved MuJoCo scenes. Optional bounded height adaptation holds its offset during flight. |
| Inspect and reproduce results | Per-motion contact diagnostics, matched-mask comparisons, published robot trajectories/probes, checksums and a reproduction script. |
| Three TienKung body models | 2 Dex (31 joints), 2 Pro (30 joints), 3 (25 joints), with bundled meshes, MJCF adapters, T-poses and joint limits. |

The contact design draws on
[ccrpRepo/robot_retargeter](https://github.com/ccrpRepo/robot_retargeter/tree/f1418972319287c1b93af0f7a3b445f613cff5e4).
It is implemented for UMR's surface-based QP solver. Robot assets come from
[Open-X-Humanoid/TienKung_URDF](https://github.com/Open-X-Humanoid/TienKung_URDF/tree/5c221783fb92fcc4af891ef1dc0502963caf2266).
See [attribution and modification notices](THIRD_PARTY_NOTICES.md).

## Measured improvement

**One controlled example, not a dataset-wide benchmark:** Unitree G1,
`dance1_subject2`, source frames 300–599, 30 FPS, 4096 slots trained for 500 epochs,
CPU execution. Both trajectories use identical source-derived contact masks
and probes (1936 active samples).

| Metric | Upstream UMR (our rerun) | Re_UMR |
| --- | ---: | ---: |
| Mean stance slip ↓ | 15.85 cm/s | **1.65 cm/s** |
| Stance slip, P95 ↓ | 38.61 cm/s | **6.77 cm/s** |
| Support-height error, P95 ↓ | 34.55 mm | **2.03 mm** |
| Joint jerk, P95 ↓ | **0.0550 rad/frame³** | 0.0628 rad/frame³ |

Mean stance slip decreased **89.6%**, with a **14.2% increase in joint jerk**.
The unmodified upstream retarget script was rerun at the pinned commit; its
`qpos` was bitwise identical to Re_UMR with stabilization disabled for this clip.
This is our evaluation, not a benchmark reported by the original UMR authors.

![Measured stance slip and support-height errors](docs/validation/g1_dance_300_599/comparison.png)

[Raw metrics](docs/validation/g1_dance_300_599/comparison.json) ·
[Inputs, environment and checksums](docs/validation/g1_dance_300_599/manifest.json) ·
[Protocol, limitations and reproduction](docs/validation/README.md)

Nineteen automated tests pass, including independent URDF forward-kinematics
checks for the new models. Each TienKung adapter completed a 24-frame CPU
integration run. Those reduced-training runs still exceed the 3 mm support-height
tolerance; they establish pipeline support, not final motion quality.
[See the TienKung reports](docs/validation/tienkung/summary.json).

Contact constraints are soft and evaluated on surface samples. These results do
not establish dynamic balance, friction feasibility, or perfect contact for all
motions. Terrain must be supplied and the source motion must already match it;
Re_UMR does not plan new footsteps. SMPL-X model weights remain user-provided.

## Original UMR framework

UMR learns ordered source–robot surface correspondence in canonical poses, then
optimizes robot motion from matched surface positions, orientations and
kinematic constraints. Correspondence is reused for the same source template
and robot. SMPL-X NPZ support, GRAIL's runtime overlay, original source adapters,
LQR smoothing and bidirectional initialization are inherited from UMR.

<details>
<summary>Original UMR paper, authors and project links</summary>

<p align="center">
  Hanyang Cao<sup>1,2,*</sup>,
  Yuetong Fang<sup>1,2,*</sup>,
  Taesoo Kwon<sup>3,*</sup>,
  Runyi Yu<sup>2,4</sup>,
  Ji Ma<sup>5</sup>,
  Jing Tan<sup>1,2</sup>,<br>
  Yangchen Zhou<sup>1</sup>,
  Baoze Du<sup>2</sup>,
  Yi Gu<sup>1</sup>,
  Yukang Gao<sup>1,2</sup>,
  Ruoli Dai<sup>2</sup>,
  Lei Han<sup>2,†</sup>,
  Renjing Xu<sup>1,†</sup>
</p>

<p align="center">
  <sup>1</sup>HKUST (Guangzhou)&nbsp;&nbsp;
  <sup>2</sup>Noitom Robotics&nbsp;&nbsp;
  <sup>3</sup>Hanyang University&nbsp;&nbsp;
  <sup>4</sup>HKUST&nbsp;&nbsp;
  <sup>5</sup>HKU
</p>

<p align="center">
  <sup>*</sup>Equal contribution&nbsp;&nbsp;&nbsp;
  <sup>†</sup>Corresponding authors
</p>

<p align="center">
  <a href="https://hanyang9.github.io/UMR/"><img src="https://img.shields.io/badge/Project-Page-2ea44f" alt="Project Page"></a>
  <a href="https://arxiv.org/abs/2609.02134"><img src="https://img.shields.io/badge/arXiv-2609.02134-b31b1b" alt="arXiv"></a>
</p>

</details>

## Supported Motion Sources

UMR samples the moving exterior surface, so any source with surface-level motion
information can be integrated through the same formulation.

| Motion source | Dataset | Adapter guide |
| --- | --- | --- |
| BONES-SEED / SOMA | [BONES-SEED](https://huggingface.co/datasets/bones-studio/seed) | [`sample_data/bones-seed/README.md`](sample_data/bones-seed/README.md) |
| GRAIL | [NVIDIA GRAIL](https://huggingface.co/datasets/nvidia/PhysicalAI-Robotics-Locomanipulation-GRAIL) | [`sample_data/grail/README.md`](sample_data/grail/README.md) |
| OmniContact | [Paper and dataset](https://huggingface.co/papers/2606.26201) | [`sample_data/omnicontact/README.md`](sample_data/omnicontact/README.md) |
| LAFAN1 / SMPL-X | [LAFAN1](https://github.com/ubisoft/ubisoft-laforge-animation-dataset) | [`sample_data/lafan1_smplx/README.md`](sample_data/lafan1_smplx/README.md) |
| OMOMO | [OMOMO](https://github.com/lijiaman/omomo_release) | [`sample_data/omomo/README.md`](sample_data/omomo/README.md) |
| Humanoid Character | [MimicKit](https://github.com/xbpeng/MimicKit) | [`sample_data/humanoid_character/README.md`](sample_data/humanoid_character/README.md) |
| AdaPT body+racket | [AdaPT](https://humanoidtennis.github.io/AdaPT/) | [`sample_data/adapt/README.md`](sample_data/adapt/README.md) |
| NR FBX/BVH | FBX/BVH motion | [`sample_data/nr/README.md`](sample_data/nr/README.md) |

> **OmniContact support.** An internal development version of UMR was used to produce the Unitree G1 retargeting data released by [OmniContact](https://omnicontact.github.io/). OmniContact provides the source motions as BVH, while UMR uses SMPL-X inputs. The internal BVH-to-SMPL-X converter is not included in this repository, so the current release does not directly support these BVH files.

For LAFAN1, use [`lafan_to_smplx`](https://github.com/jaraujo98/lafan_to_smplx)
to convert BVH motion to SMPL-X before retargeting. Each adapter guide documents
the expected local layout.

## Installation

```bash
git clone https://github.com/BenHuHuan/Re_UMR.git
cd Re_UMR
git lfs install
git lfs pull

conda create -n umr python=3.12 pip -y
conda activate umr
python -m pip install --index-url https://download.pytorch.org/whl/cu121 torch==2.4.1
python -m pip install -r requirements-umr.txt
```

### SMPL-X Body Models

SMPL-X body-model files are not distributed with this repository. Download
them from the official SMPL-X provider after accepting its terms. Both `.pkl`
and `.npz` models are supported; place at least the neutral model at:

```text
smpl/SMPLX_NEUTRAL.pkl
# or
smpl/SMPLX_NEUTRAL.npz
```

Add `SMPLX_MALE` and `SMPLX_FEMALE` in either format when a sequence requires
those genders. The NPZ path has been tested with both neutral SMPL-X motion and
female OMOMO motion.

The GRAIL example applies its bundled G1-SMPL-X template and pose-corrective
overlay to the user-provided neutral SMPL-X model at runtime; the derived baked
SMPL-X weights are not distributed.

## Quick Start

Retarget the included LAFAN1-derived SMPL-X motion:

```bash
python scripts/humanoid_retarget_pipeline.py \
  --config robot_configs/humanoid_retarget_unitree_g1_example.json
```

The first run builds/trains correspondence; later runs reuse it. For a run without
a viewer, append `--skip-view`. On a CPU-only system, set
`retarget.smplx_device` and `correspondence.train.device` to `cpu` in the config.

The default configuration uses the included LAFAN1-derived SMPL-X sequence
`sample_data/lafan1_smplx/dance1_subject2.npz`. It builds or reuses the learned
point-cloud correspondence, runs correspondence-guided retargeting, and opens
the MuJoCo viewer.

Foot-contact stabilization is enabled by default: speed/height detection,
continuous-stance anchors, and a final contact correction after trajectory
smoothing reduce support-foot sliding. Plane/heightfield terrain and per-motion
contact diagnostics are also available. See
[`docs/contact_stabilization.md`](docs/contact_stabilization.md) for configuration,
terrain coordinates, tuning and validation.

## Supported Robots

Ready-to-run robot configurations are included for:

| Robot | Configuration |
| --- | --- |
| Unitree G1 | [`unitree_g1`](robot_configs/humanoid_retarget_unitree_g1_example.json) |
| Unitree H2 | [`unitree_h2`](robot_configs/humanoid_retarget_unitree_h2_example.json) |
| EngineAI T800 | [`engineai_t800`](robot_configs/humanoid_retarget_engineai_t800_example.json) |
| Booster K1 | [`booster_k1`](robot_configs/humanoid_retarget_booster_k1_example.json) |
| HighTorque PiPlusPro | [`hightorque_pipluspro`](robot_configs/humanoid_retarget_hightorque_pipluspro_example.json) |
| MimicKit Humanoid | [`mimickit_humanoid`](robot_configs/humanoid_retarget_mimickit_humanoid_example.json) |
| TienKung 2 Dex (31 body joints) | [`tiangong2dex`](robot_configs/humanoid_retarget_tiangong2dex_example.json) |
| TienKung 2 Pro (30 body joints) | [`tiangong2pro`](robot_configs/humanoid_retarget_tiangong2pro_example.json) |
| TienKung 3 (25 body joints) | [`tiangong3`](robot_configs/humanoid_retarget_tiangong3_example.json) |

Select any configuration with `--config`, for example:

```bash
python scripts/humanoid_retarget_pipeline.py \
  --config robot_configs/humanoid_retarget_tiangong3_example.json
```

TienKung models include the required meshes, floating-base MJCF adapters,
T-poses and joint limits. See [`assets/tienkung/README.md`](assets/tienkung/README.md)
for upstream provenance, conversion details and the scope of each body model.
They use the same foot-contact and terrain options described above.

To add another robot, copy the example config in `robot_configs/` and update
its name and MJCF path. Prepare the robot T-pose in
[UMR Studio](https://hanyang9.github.io/UMR/umr_studio.html): load the robot
asset folder, select its MJCF, adjust it into a T-pose, and click **Copy T-pose
Config**. Paste the copied `tpose_qpos` into the new robot config, then run the
pipeline with that config. No manual human-robot mapping is required.

The same surface-based formulation is exposed for other motion representations
and interaction settings:

```bash
# BONES-SEED SOMA motion
python scripts/humanoid_retarget_pipeline.py \
  --config robot_configs/humanoid_retarget_unitree_g1_example.json \
  --defaults humanoid_retarget_defaults_bones_seed.json

# Humanoid Character spin-kick
python scripts/humanoid_retarget_pipeline_character.py \
  --config robot_configs/humanoid_retarget_unitree_g1_example.json

# GRAIL human-scene interaction
python scripts/humanoid_retarget_pipeline_hsi_hoi.py \
  --config robot_configs/humanoid_retarget_unitree_g1_example.json \
  --defaults humanoid_retarget_defaults_hsi_hoi_grail.json

# OmniContact human-object interaction (pre-converted SMPL-X input)
python scripts/humanoid_retarget_pipeline_hsi_hoi.py \
  --config robot_configs/humanoid_retarget_unitree_g1_example.json \
  --defaults humanoid_retarget_defaults_hsi_hoi_standard.json

# OMOMO human-object interaction
python scripts/humanoid_retarget_pipeline_hsi_hoi.py \
  --config robot_configs/humanoid_retarget_unitree_g1_example.json \
  --defaults humanoid_retarget_defaults_hsi_hoi_standard.json \
  --data sample_data/omomo \
  --seq-key sub1_plasticbox_015

# NR FBX/BVH human motion
python scripts/humanoid_retarget_pipeline_nr.py \
  --config robot_configs/humanoid_retarget_unitree_g1_example.json

# AdaPT body+racket correspondence and retargeting
python scripts/humanoid_retarget_pipeline_adapt.py
```

## Visualize a Result

Results contain the final robot `qpos` and the metadata required by the GLFW
MuJoCo viewer:

```bash
python scripts/visualize_robot_retarget_result.py \
  --result output/unitree_g1_retarget/dance1_subject2_smplx_unitree_g1.npz \
  --play
```

## Batch Retargeting

Run the SMPL-X/LAFAN batch pipeline with:

```bash
python scripts/humanoid_retarget_pipeline_batch.py \
  --config robot_configs/humanoid_retarget_unitree_g1_example.json \
  --batch-config humanoid_retarget_defaults_batch.json
```

BONES-SEED uses its own batch defaults:

```bash
python scripts/humanoid_retarget_pipeline_batch.py \
  --config robot_configs/humanoid_retarget_unitree_g1_example.json \
  --batch-config humanoid_retarget_defaults_batch_bones_seed.json
```

Add `--motion-folder sample_data/bones-seed/motions_proportional/bvh` for the
actor-proportional subset. BONES-SEED associates each `Axxx` motion with its
matching shape and reuses one correspondence per source-template/robot pair.

Batch defaults use **bidirectional warm start with dynamic programming** to
reduce sensitivity to occasional singularities. This mode is recommended for
large-scale retargeting.

| Option | Meaning |
| --- | --- |
| `--motion-folder PATH` | Select the input directory. |
| `--recursive` / `--pattern GLOB` | Control motion discovery. |
| `--workers N` | Set parallel retargeting jobs. |
| `--correspondence-workers N` | Set parallel correspondence preparation jobs. |
| `--retarget-gpus` | Control GPU assignment. |
| `--force-retarget` | Rebuild existing results. |

Results are saved under `output/batch_retarget/<robot-name>/`;
`batch_summary.json` records each clip status.

## Configuration

`--config` selects the target robot. Robot-specific `tpose_qpos`, joint limits,
and model paths belong in this file. `--defaults` selects source- and
task-specific settings.

| Defaults | Source |
| --- | --- |
| `humanoid_retarget_defaults.json` | SMPL/SMPL-X |
| `humanoid_retarget_defaults_bones_seed.json` | BONES-SEED / SOMA |
| `humanoid_retarget_defaults_humanoid_character.json` | Humanoid Character |
| `humanoid_retarget_defaults_hsi_hoi_grail.json` | GRAIL |
| `humanoid_retarget_defaults_hsi_hoi_standard.json` | OmniContact / OMOMO |
| `humanoid_retarget_defaults_nr.json` | NR FBX/BVH |
| `robot_configs/humanoid_retarget_defaults_adapt.json` | AdaPT SMPL-X+racket |

### Surface Objective Weights

Surface weights are defined on the motion source, not per robot:

| Source/task | Parameter file |
| --- | --- |
| SMPL/SMPL-X and SOMA | [`retarget_body_segment_surface.py`](scripts/retarget_body_segment_surface.py) |
| Humanoid Character | [`retarget_body_segment_surface_character.py`](scripts/retarget_body_segment_surface_character.py) |
| HSI/HOI and NR | [`retarget_body_segment_surface_hoi_hsi.py`](scripts/retarget_body_segment_surface_hoi_hsi.py) |
| AdaPT body+racket | [`retarget_body_segment_surface_adapt.py`](scripts/retarget_body_segment_surface_adapt.py) |

Each segment specifies `sample_slots`, `point_cost`, and `normal_cost`. Robots
sharing the same source/task use the same values; only the robot config changes.
Interaction defaults give more weight to end-effector preservation. These
settings work well for G1 and generally transfer to other robots, but may not be
optimal for every embodiment.

## Data Preparation Notes

- For HSI/HOI, convex-decompose concave objects with
  [CoACD](https://github.com/SarahWeiii/CoACD) before retargeting. MuJoCo treats
  a single mesh collision geom as its convex hull.
- BONES-SEED motion and SOMA-X asset placement is documented in the
  [BONES-SEED guide](sample_data/bones-seed/README.md); `py-soma-x` is included
  in the requirements.
- NR FBX/BVH input requires Node.js 18 or newer. The bundled minimal Three.js
  code is used only for FBX mesh parsing, not visualization.

## Citation

Please cite **both** the original UMR method and this software extension when
using Re_UMR. The software citation identifies this repository; it is not a
separate peer-reviewed paper and has no assigned DOI.

**Original UMR — Cao et al.:**

```bibtex
@misc{cao2026unifiedmotionretargetinghumanoids,
  title={Unified Motion Retargeting for Humanoids with Learned Point Cloud Correspondence},
  author={Hanyang Cao and Yuetong Fang and Taesoo Kwon and Runyi Yu and Ji Ma and Jing Tan and Yangchen Zhou and Baoze Du and Yi Gu and Yukang Gao and Ruoli Dai and Lei Han and Renjing Xu},
  year={2026},
  eprint={2609.02134},
  archivePrefix={arXiv},
  primaryClass={cs.RO},
  url={https://arxiv.org/abs/2609.02134},
}
```

**Re_UMR — Huan Hu:**

```bibtex
@software{hu2026reumr,
  author = {Huan Hu},
  title = {{Re\_UMR}: Contact-Stabilized Unified Motion Retargeting},
  year = {2026},
  url = {https://github.com/BenHuHuan/Re_UMR},
  note = {Software extension of UMR; cite Cao et al. (2026) for the original method}
}
```

Machine-readable metadata: [`CITATION.cff`](CITATION.cff).
Both BibTeX entries: [`CITATIONS.bib`](CITATIONS.bib).
When reporting experiments, also record the exact Re_UMR commit used.

## Attribution and asset terms

The original UMR authors retain credit for the base framework and paper.
Contact-design references and TienKung model provenance are documented in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). Existing datasets and robot
assets retain their upstream terms; the TienKung OpenAtom license is included.
This fork does not relicense upstream materials. SMPL-X model weights are not
included and must be obtained from their official provider.
