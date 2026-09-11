# Changes from upstream UMR

## 2026-09-11 — Initial Re_UMR publication

Based on upstream UMR `d6bb76123d19afb7c2c1c84162d1af1f142a61ed`.

### Contact and terrain

- Add speed/height contact gates, hysteresis, minimum stance duration and
  independent sole probes; preserve continuous targets through chunk boundaries.
- Restore stance contact after smoothing/bidirectional selection with a shared
  constrained QP, fitted-robot anchors and a temporal correction penalty.
- Add planes, slopes and MuJoCo-consistent heightfields to detection, ground
  constraints and generated scenes. Add optional bounded support-height filtering.
- Write contact diagnostics and include contact/terrain inputs in cache checks.
- Integrate the final correction in single-motion, batch and Character paths.

### Robot adapters

- Add TienKung 2 Dex, 2 Pro and 3 body-model configurations, source descriptions,
  referenced meshes, floating-base MJCF, T-poses and limits.
- Provide a reproducible model conversion script, license and modification notices.

### Evidence and documentation

- Publish the 300-frame G1 comparison, raw robot/probe outputs, checksums and
  configs; independently rerun the pinned upstream code to verify the baseline.
- Record 89.6% mean-slip reduction and a 14.2% joint-jerk increase on that clip.
- Publish TienKung integration reports, including unresolved support-height errors
  from the reduced-training smoke runs.
- Add 19 automated tests, a metric replay/full-run script, README attribution,
  original UMR citation and separate Re_UMR software citation for Huan Hu.

### Inherited capabilities

Correspondence learning, original source/robot adapters, SMPL-X PKL/NPZ loading,
GRAIL overlays, LQR filtering, bidirectional initialization and visualization
already exist upstream and are not claimed as new here.
