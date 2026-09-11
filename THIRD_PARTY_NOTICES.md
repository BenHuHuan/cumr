# Attribution and modification notices

## Original UMR

Re_UMR derives from [hanyang9/UMR](https://github.com/hanyang9/UMR) at
[`d6bb76123d19afb7c2c1c84162d1af1f142a61ed`](https://github.com/hanyang9/UMR/tree/d6bb76123d19afb7c2c1c84162d1af1f142a61ed).
The original Git history is retained. The learned surface correspondence,
retargeting framework, original adapters, robot configurations, datasets and
viewer are the upstream authors' work. In particular, SMPL-X NPZ support and the
GRAIL runtime overlay predate this fork and are not Re_UMR contributions.

Original paper: Hanyang Cao, Yuetong Fang, Taesoo Kwon, Runyi Yu, Ji Ma, Jing Tan,
Yangchen Zhou, Baoze Du, Yi Gu, Yukang Gao, Ruoli Dai, Lei Han and Renjing Xu,
*Unified Motion Retargeting for Humanoids with Learned Point Cloud
Correspondence*, 2026, [arXiv:2609.02134](https://arxiv.org/abs/2609.02134).
Please retain this citation when using the original method.

The pinned upstream snapshot has no repository-wide license file. Re_UMR does
not assign a new blanket license to those materials. Existing notices and
provider-specific terms continue to apply.

## Re_UMR modifications

Maintainer: **Huan Hu** ([BenHuHuan](https://github.com/BenHuHuan)).
The 2026-09-11 changes add `contact_stabilization.py`, `contact_terrain.py`,
contact integration in single-motion/batch/Character solvers and their pipelines,
cache validation, comparison/reproduction tools, tests, TienKung adapters and
the associated documentation. See [CHANGELOG.md](CHANGELOG.md) and the preserved
Git diff/history for the exact modified files.

The original UMR authors are not presented as authors of this extension or as
endorsing its evaluation. Our software citation is separate from the UMR paper.

## Contact-design reference

[ccrpRepo/robot_retargeter](https://github.com/ccrpRepo/robot_retargeter), inspected
at [`f1418972319287c1b93af0f7a3b445f613cff5e4`](https://github.com/ccrpRepo/robot_retargeter/tree/f1418972319287c1b93af0f7a3b445f613cff5e4),
describes combined speed/height contact gates, front/rear foot probes,
interval-mean fixed contact targets, and filtered support-height correction.
Those ideas informed this implementation. Re_UMR implements them in UMR's
surface correspondence/QP formulation and adds hysteresis, independent surface
probes, terrain queries and a correction after smoothing. The reference
repository's skeleton IK pipeline and per-bone/two-bone reconstruction are not
vendored into this repository. Its contributors retain credit for that design.

## TienKung models

The added robot source descriptions and meshes are from
[Open-X-Humanoid/TienKung_URDF](https://github.com/Open-X-Humanoid/TienKung_URDF),
revision [`5c221783fb92fcc4af891ef1dc0502963caf2266`](https://github.com/Open-X-Humanoid/TienKung_URDF/tree/5c221783fb92fcc4af891ef1dc0502963caf2266).
Their [OpenAtom Open Hardware License 1.0](assets/tienkung/LICENSE) is reproduced
unchanged. Original attribution belongs to Open-X-Humanoid and its contributors.

**UMR adaptations modify the model descriptions and two meshes.** Original
URDFs, native MJCF sources and STLs are preserved. The generated `model.xml`
adapters and two OBJ conversions carry the modifications detailed in
[assets/tienkung/README.md](assets/tienkung/README.md), including pelvis inertia,
limit reconciliation, floating roots, ground alignment and STL-to-OBJ conversion.

## Body models, other assets and evidence

SMPL-X body-model weights require obtaining the provider's models under its
terms and are not distributed. Re_UMR does not publish the locally installed
weights or baked GRAIL weights. The original sample-data guides identify the
source datasets. Existing robot assets and bundled third-party code retain
their upstream attribution and terms, including the bundled Three.js license.

The added validation bundle contains robot trajectories, contact probe
diagnostics, configuration snapshots, metrics and figures from our reruns of
the included sample. It contains no SMPL-X model weights or trained
correspondence checkpoints. Its protocol and limitations are documented in
[docs/validation/README.md](docs/validation/README.md).
