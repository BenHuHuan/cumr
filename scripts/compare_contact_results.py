#!/usr/bin/env python3
"""Compare two robot motions using the same detected stance intervals/probes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from contact_stabilization import ContactPlan, contact_metrics
from contact_terrain import ContactTerrain
from smpl_surface_retarget_common import set_qpos, template_points_to_world, qpos_temporal_summary


def compare(baseline_path, result_path):
    with np.load(result_path.with_suffix(".contact.npz"), allow_pickle=False) as data:
        plan = ContactPlan(data["slot_ids"], data["labels"], data["active"], data["targets"],
                           data["weights"], data["source_speeds"], data["height_offsets"])
        probe_template = {"geom_ids": data["probe_geom_ids"], "local_pos": data["probe_local_pos"]}
        expected_frames = data["frame_ids"]
        fps = float(data["fps"])
    metadata = json.loads(result_path.with_suffix(".contact.json").read_text())
    terrain = ContactTerrain(metadata["terrain"])
    with np.load(result_path, allow_pickle=True) as result:
        model = mujoco.MjModel.from_xml_path(str(result["robot_xml"].item()))
        expected_joints = result["robot_joint_names"]
        expected_source = str(result["source_data"].item())
        expected_sequence = str(result["source_sequence_key"].item())
    data_mj = mujoco.MjData(model)
    report, traces = {}, {}
    for label, path in (("baseline", baseline_path), ("stabilized", result_path)):
        with np.load(path, allow_pickle=True) as data:
            if (not np.array_equal(data["frame_ids"], expected_frames)
                    or not np.array_equal(data["robot_joint_names"], expected_joints)
                    or str(data["source_data"].item()) != expected_source
                    or str(data["source_sequence_key"].item()) != expected_sequence
                    or not np.isclose(float(data["fps"].item()), fps)):
                raise ValueError("Comparison requires the same source sequence, robot joints, FPS and frames")
            qpos = data["qpos"]
        points = []
        for q in qpos:
            set_qpos(model, data_mj, q)
            points.append(template_points_to_world(data_mj, probe_template, np.arange(len(plan.slot_ids))))
        points = np.asarray(points)
        report[label] = contact_metrics(points, plan, fps, terrain)
        report[label]["joint_temporal"] = qpos_temporal_summary(qpos, np.arange(7, model.nq))
        delta = np.diff(points, axis=0)
        _, normal = terrain.sample(plan.targets[:-1])
        tangent = delta - np.sum(delta * normal, axis=-1, keepdims=True) * normal
        mask = plan.active[1:] & plan.active[:-1]
        speed = np.linalg.norm(tangent, axis=-1) * fps
        mean_speed = np.sum(speed * mask, axis=1) / np.maximum(mask.sum(axis=1), 1)
        mean_speed[~mask.any(axis=1)] = np.nan
        height = np.abs(terrain.clearance(points))
        mean_height = np.sum(height * plan.active, axis=1) / np.maximum(plan.active.sum(axis=1), 1)
        mean_height[~plan.active.any(axis=1)] = np.nan
        traces[label] = (mean_speed, mean_height)
    old = report["baseline"]["stance_slip_mean_m_s"]
    new = report["stabilized"]["stance_slip_mean_m_s"]
    report["mean_slip_reduction_percent"] = 100 * (1 - new / old) if old and new is not None else None
    report["frame_range"] = [int(expected_frames[0]), int(expected_frames[-1])]
    report["fps"] = fps
    return report, traces


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--plot", type=Path, help="Optional PNG/SVG/PDF (requires matplotlib)")
    args = parser.parse_args()
    report, traces = compare(args.baseline, args.result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 1, figsize=(10, 5.5), sharex=True)
        for label, (speed, height) in traces.items():
            axes[0].plot(np.arange(1, len(speed) + 1) / report["fps"], speed * 100, label=label)
            axes[1].plot(np.arange(len(height)) / report["fps"], height * 1000, label=label)
        axes[0].set_ylabel("Stance slip (cm/s)")
        axes[1].set_ylabel("Support height error (mm)")
        axes[1].set_xlabel("Time in clip (s)")
        axes[0].legend()
        for axis in axes:
            axis.grid(alpha=.2)
        fig.suptitle("Contact comparison — identical source frames and contact masks")
        fig.tight_layout()
        args.plot.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.plot, dpi=160)
        plt.close(fig)


if __name__ == "__main__":
    main()
