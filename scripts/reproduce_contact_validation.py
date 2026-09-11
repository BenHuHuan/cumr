#!/usr/bin/env python3
"""Replay the published G1 evidence, or rebuild the 300-frame experiment."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

from compare_contact_results import compare

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/validation/g1_dance_300_599"
UPSTREAM = "d6bb76123d19afb7c2c1c84162d1af1f142a61ed"


def verify_evidence():
    manifest = json.loads((EVIDENCE / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        with (EVIDENCE / name).open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"Evidence checksum mismatch: {name}; run git lfs pull first")
    return manifest


def run_experiment(out_dir, slots=None, upstream_checkout=None):
    from humanoid_retarget_pipeline import (
        _absolutize_merged_config_paths, _clean_config, load_pipeline_config,
    )

    if upstream_checkout is not None:
        revision = subprocess.check_output(
            ["git", "-C", str(upstream_checkout), "rev-parse", "HEAD"], text=True,
        ).strip()
        if revision != UPSTREAM:
            raise ValueError(f"Upstream checkout must be at {UPSTREAM}, got {revision}")
    configs = {}
    for name in ("baseline", "stabilized"):
        config = load_pipeline_config(EVIDENCE / f"{name}_config.json")
        _absolutize_merged_config_paths(config, config, config)
        config["correspondence"]["dataset"]["out"] = str(out_dir / "correspondence.npz")
        config["correspondence"]["train"]["out_dir"] = str(out_dir / "correspondence_train")
        if slots is not None:
            config["correspondence"]["slots"] = str(slots)
        config["retarget"]["out"] = str(out_dir / f"{name}.npz")
        config_path = out_dir / f"{name}_config.json"
        config_path.write_text(json.dumps(_clean_config(config), indent=2) + "\n")
        configs[name] = config_path
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/humanoid_retarget_pipeline.py"),
             "--config", str(config_path), "--skip-view", "--force-retarget"],
            cwd=ROOT, check=True,
        )
    baseline = out_dir / "baseline.npz"
    if upstream_checkout is not None:
        upstream_result = out_dir / "upstream.npz"
        actual_slots = slots or out_dir / "correspondence_train/correspondence_slots_final.npz"
        subprocess.run(
            [sys.executable, str(upstream_checkout / "scripts/retarget_smpl_to_humanoid_surface_vector.py"),
             "--config", str(configs["baseline"]), "--slots", str(actual_slots),
             "--data", str(ROOT / "sample_data/lafan1_smplx"), "--seq-key", "dance1_subject2",
             "--start", "300", "--max-frames", "300", "--out", str(upstream_result)],
            cwd=ROOT, check=True,
        )
        with np.load(baseline, allow_pickle=False) as disabled, np.load(upstream_result, allow_pickle=False) as original:
            error = float(np.max(np.abs(disabled["qpos"] - original["qpos"])))
        (out_dir / "upstream_check.json").write_text(json.dumps({
            "upstream_commit": UPSTREAM, "max_absolute_qpos_difference": error,
            "qpos_bitwise_equal": error == 0.0,
        }, indent=2) + "\n")
        baseline = upstream_result
    return baseline, out_dir / "stabilized.npz"


def check_metrics(actual, expected, prefix=""):
    for key, value in expected.items():
        if isinstance(value, dict):
            check_metrics(actual[key], value, prefix + key + ".")
        elif value is None:
            if actual[key] is not None:
                raise AssertionError(f"{prefix}{key}: expected no contact metric")
        else:
            np.testing.assert_allclose(actual[key], value, rtol=1e-6, atol=1e-8,
                                       err_msg=prefix + key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Build/train/retarget; requires licensed SMPL-X")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "output/reproduced_contact_validation")
    parser.add_argument("--slots", type=Path, help="Reuse compatible trained slots when using --run")
    parser.add_argument("--upstream-checkout", type=Path,
                        help=f"With --run, also rerun upstream code at {UPSTREAM[:7]}")
    args = parser.parse_args()
    if not args.run and (args.slots or args.upstream_checkout):
        parser.error("--slots and --upstream-checkout require --run")
    out_dir = args.out_dir.resolve()
    slots = args.slots.resolve() if args.slots else None
    upstream = args.upstream_checkout.resolve() if args.upstream_checkout else None
    os.chdir(ROOT)  # Published model/source metadata uses repository-relative paths.
    verify_evidence()
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.run:
        baseline, result = run_experiment(out_dir, slots, upstream)
    else:
        baseline, result = EVIDENCE / "baseline.npz", EVIDENCE / "stabilized.npz"
    report, traces = compare(baseline, result)
    if not args.run:
        check_metrics(report, json.loads((EVIDENCE / "comparison.json").read_text()))
    (out_dir / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    # Framewise traces are also exportable without a plotting dependency.
    for name, (speed, height) in traces.items():
        rows = np.column_stack((np.arange(len(height)) / report["fps"], np.r_[np.nan, speed], height))
        np.savetxt(out_dir / f"{name}_traces.csv", rows, delimiter=",",
                   header="time_s,mean_stance_slip_m_s,mean_support_height_error_m", comments="")
    print(json.dumps(report, indent=2))
    print(f"{'Experiment completed' if args.run else 'Evidence checksums and metrics verified'}: {out_dir}")


if __name__ == "__main__":
    main()
