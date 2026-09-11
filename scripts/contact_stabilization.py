"""Offline stance detection and interval anchors for surface-based retargeting.

Algorithmic inspiration: ccrpRepo/robot_retargeter (contact speed/height gates,
interval-mean targets and support-height filtering). This implementation operates
on UMR surface correspondences and adds hysteresis and post-filter projection.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import hashlib
import json
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class ContactSettings:
    enabled: bool = False
    height_enter: float = 0.035
    height_exit: float = 0.055
    speed_enter: float = 0.18
    speed_exit: float = 0.30
    speed_window_seconds: float = 0.067
    min_contact_seconds: float = 0.067
    blend_seconds: float = 0.067
    points_per_foot: int = 6
    position_cost: float = 100000.0
    height_adaptation: bool = False
    height_filter_seconds: float = 0.1
    height_max_correction: float = 0.05
    projection_iters: int = 8
    projection_pose_cost: float = 1.0
    projection_velocity_cost: float = 500.0
    tolerance: float = 0.003

    @classmethod
    def from_config(cls, config):
        raw = dict(config or {})
        raw.pop("terrain", None)
        valid = {field.name for field in fields(cls)}
        unknown = set(raw) - valid
        if unknown:
            raise ValueError(f"Unknown contact_stabilization settings: {sorted(unknown)}")
        obj = cls(**raw)
        if not isinstance(obj.enabled, bool) or not isinstance(obj.height_adaptation, bool):
            raise ValueError("enabled and height_adaptation must be JSON booleans")
        for name in valid - {"enabled", "height_adaptation"}:
            value = getattr(obj, name)
            if not np.isfinite(value) or value < 0:
                raise ValueError(f"contact_stabilization.{name} must be finite and nonnegative")
        if obj.height_exit < obj.height_enter or obj.speed_exit < obj.speed_enter:
            raise ValueError("Contact exit thresholds must be >= enter thresholds")
        if int(obj.points_per_foot) != obj.points_per_foot or obj.points_per_foot < 2:
            raise ValueError("points_per_foot must be an integer >= 2 (heel and toe)")
        if int(obj.projection_iters) != obj.projection_iters:
            raise ValueError("projection_iters must be an integer")
        if obj.enabled and obj.position_cost <= 0:
            raise ValueError("Enabled contact stabilization needs a positive position_cost")
        return obj


def contact_signature(config, resolve_path):
    """Invalidate cached motion when contact settings or terrain samples change."""
    raw = dict(config or {})
    payload = asdict(ContactSettings.from_config(raw))
    terrain = dict(raw.get("terrain") or {})
    if terrain.get("path"):
        path = Path(resolve_path(terrain["path"]))
        terrain["path"] = str(path.resolve())
        terrain["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    payload["terrain"] = terrain
    payload["version"] = 2
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def point_speeds(points, fps, window_seconds):
    """Windowed path length / time; oscillation cannot cancel to zero speed."""
    points = np.asarray(points, dtype=float)
    if points.ndim != 3 or points.shape[-1] != 3 or not np.isfinite(points).all():
        raise ValueError("Contact points must be finite [frames, probes, 3]")
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError("Contact FPS must be positive")
    n = len(points)
    if n <= 1:
        return np.zeros(points.shape[:2])
    half = max(1, int(round(window_seconds * fps / 2)))
    lo = np.maximum(np.arange(n) - half, 0)
    hi = np.minimum(np.arange(n) + half, n - 1)
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=-1)
    cumulative = np.vstack([np.zeros((1, points.shape[1])), np.cumsum(lengths, axis=0)])
    return (cumulative[hi] - cumulative[lo]) * fps / (hi - lo)[:, None]


def intervals(mask):
    edges = np.diff(np.r_[False, mask, False].astype(np.int8))
    return zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1))


def detect_contacts(points, fps, terrain, settings):
    speed = point_speeds(points, fps, settings.speed_window_seconds)
    height = terrain.clearance(points)
    enter = (height <= settings.height_enter) & (speed <= settings.speed_enter)
    stay = (height <= settings.height_exit) & (speed <= settings.speed_exit)
    # Do not label deeply underground points as support.
    valid = height >= -settings.height_exit
    state = np.zeros_like(enter)
    for t in range(len(points)):
        previous = state[t - 1] if t else np.zeros(points.shape[1], dtype=bool)
        state[t] = (enter[t] | (previous & stay[t])) & valid[t]
    min_frames = max(1, int(np.ceil(settings.min_contact_seconds * fps)))
    for probe in range(state.shape[1]):
        for start, end in intervals(state[:, probe]):
            if end - start < min_frames:
                state[start:end, probe] = False
    return state, speed


def select_support_probes(source_template, robot_points, groups, count, source_height_axis=1):
    """Spread probes over each mapped sole, retaining separate heel/toe contacts.

    source_template is UMR's Y-up centered reference; robot_points is Z-up.
    Prefer points low on both surfaces rather than assuming ankle == sole.
    """
    ids, labels = [], []
    for name in ("leftFoot", "rightFoot"):
        candidates = np.asarray(groups.get(name, []), dtype=np.int32)
        if not len(candidates):
            continue
        robot_height = robot_points[candidates, 2]
        candidates = candidates[robot_height <= robot_height.min() + 0.03]
        source_height = source_template[candidates, source_height_axis]
        candidates = candidates[source_height <= source_height.min() + 0.035]
        if not len(candidates):
            continue
        xy = robot_points[candidates, :2]
        chosen = [int(np.argmin(source_template[candidates, source_height_axis]))]
        distance = np.full(len(candidates), np.inf)
        for _ in range(min(int(count), len(candidates)) - 1):
            distance = np.minimum(distance, np.linalg.norm(xy - xy[chosen[-1]], axis=1))
            distance[chosen] = -1
            chosen.append(int(np.argmax(distance)))
        ids.extend(candidates[chosen])
        labels.extend([name] * len(chosen))
    return np.asarray(ids, dtype=np.int32), np.asarray(labels)


def support_height_offsets(points, active, fps, terrain, settings):
    heights = terrain.clearance(points)
    offsets = np.zeros(len(points), dtype=float)
    alpha = 1.0 - np.exp(-1.0 / max(fps * settings.height_filter_seconds, 1e-12))
    previous = 0.0
    for t in range(len(points)):
        if np.any(active[t]):
            target = float(heights[t, active[t]].min())
            target = np.clip(target, -settings.height_max_correction, settings.height_max_correction)
            previous += alpha * (target - previous)
        # Hold the actual correction during flight; do not flatten jumps.
        offsets[t] = previous
    return offsets


@dataclass
class ContactPlan:
    slot_ids: np.ndarray
    labels: np.ndarray
    active: np.ndarray
    targets: np.ndarray
    weights: np.ndarray
    speeds: np.ndarray
    height_offsets: np.ndarray

    def frame(self, index):
        active = self.active[index]
        return {"slot_ids": self.slot_ids[active], "targets": self.targets[index, active],
                "weights": self.weights[index, active]}


def build_contact_plan(source_slots, slot_ids, labels, fps, terrain, settings):
    points = np.asarray(source_slots[:, slot_ids], dtype=float)
    active, speeds = detect_contacts(points, fps, terrain, settings)
    offsets = np.zeros(len(points))
    if settings.height_adaptation:
        offsets = support_height_offsets(points, active, fps, terrain, settings)
        points = points.copy()
        points[:, :, 2] -= offsets[:, None]
    targets = points.copy()
    weights = np.zeros(active.shape)
    blend = max(1, int(round(settings.blend_seconds * fps)))
    for probe in range(len(slot_ids)):
        for start, end in intervals(active[:, probe]):
            target = points[start:end, probe].mean(axis=0)
            target[2] = terrain.heights(target[:2])
            targets[start:end, probe] = target
            ramp = np.minimum(np.arange(1, end - start + 1), np.arange(end - start, 0, -1)) / blend
            weights[start:end, probe] = np.minimum(ramp, 1.0)
    # Each foot has a fixed total weight, independent of correspondence density.
    for label in np.unique(labels):
        group = labels == label
        count = np.maximum(active[:, group].sum(axis=1), 1)
        weights[:, group] /= count[:, None]
    return ContactPlan(slot_ids, labels, active, targets, weights, speeds, offsets)


def contact_metrics(points, plan, fps, terrain):
    """Measure actual FK, never target trajectories; use only consecutive stance frames."""
    consecutive = plan.active[1:] & plan.active[:-1]
    displacement = np.diff(points, axis=0)
    _height, normals = terrain.sample(plan.targets[:-1])
    tangent = displacement - np.sum(displacement * normals, axis=-1, keepdims=True) * normals
    delta = np.linalg.norm(tangent, axis=-1)
    slip = delta[consecutive] * fps
    errors = np.linalg.norm(points - plan.targets, axis=-1)[plan.active]
    clearance = terrain.clearance(points)
    support_height = np.abs(clearance[plan.active])
    return {
        "contact_samples": int(plan.active.sum()),
        "stance_slip_mean_m_s": float(slip.mean()) if slip.size else None,
        "stance_slip_p95_m_s": float(np.percentile(slip, 95)) if slip.size else None,
        "anchor_error_p95_m": float(np.percentile(errors, 95)) if errors.size else None,
        "support_height_p95_m": float(np.percentile(support_height, 95)) if support_height.size else None,
        "max_probe_penetration_m": float(np.maximum(-clearance, 0).max(initial=0)),
    }


def rebase_contact_targets(plan, robot_points, terrain):
    """Use the fitted robot's interval means for the final lock.

    Source/robot sole widths differ. Source-space anchors guide the initial
    retarget, but imposing that geometry rigidly during final projection creates
    conflicting targets. Rebase once before projection, never once per frame.
    """
    for probe in range(len(plan.slot_ids)):
        for start, end in intervals(plan.active[:, probe]):
            target = np.asarray(robot_points[start:end, probe]).mean(axis=0)
            target[2] = terrain.heights(target[:2])
            plan.targets[start:end, probe] = target
