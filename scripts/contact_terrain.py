"""Shared support surface for contact detection, IK and the saved MuJoCo scene."""
from __future__ import annotations

import copy
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np


class ContactTerrain:
    """A plane or a static heightfield, in scaled, Z-up retarget world metres.

    Heightfield NPZ: heights[ny, nx], origin_xy[2], cell_size (scalar or [2]).
    Rows increase in world Y. MuJoCo itself samples the heightfield, so the
    optimizer and viewer use exactly the same triangle tessellation.
    """

    def __init__(self, config=None):
        self.config = dict(config or {})
        self.kind = self.config.get("type", "plane")
        allowed = {"type", "height", "slope"} if self.kind == "plane" else {"type", "path", "outside_height"}
        if set(self.config) - allowed:
            raise ValueError(f"Unknown terrain settings: {sorted(set(self.config) - allowed)}")
        self.height = float(self.config.get("height", 0.0))
        self.slope = np.asarray(self.config.get("slope", [0.0, 0.0]), dtype=float)
        if self.slope.shape != (2,) or not np.isfinite(self.slope).all() or not np.isfinite(self.height):
            raise ValueError("Terrain height and slope[2] must be finite")
        self.asset = ET.Element("asset")
        self.worldbody = ET.Element("worldbody")
        if self.kind == "plane":
            normal = np.r_[-self.slope, 1.0]
            normal /= np.linalg.norm(normal)
            ET.SubElement(self.worldbody, "geom", name="umr_ground", type="plane",
                          size="10 10 0.1", pos=f"0 0 {self.height:.12g}",
                          zaxis=" ".join(map(str, normal)), rgba="0.35 0.4 0.45 1")
        elif self.kind == "heightfield":
            with np.load(Path(self.config["path"]), allow_pickle=False) as archive:
                heights = np.asarray(archive["heights"], dtype=float)
                origin = np.asarray(archive["origin_xy"], dtype=float)
                cell = np.broadcast_to(np.asarray(archive["cell_size"], dtype=float), (2,)).copy()
            if (heights.ndim != 2 or min(heights.shape) < 2 or origin.shape != (2,)
                    or not np.isfinite(heights).all() or not np.isfinite(origin).all()
                    or not np.isfinite(cell).all() or np.any(cell <= 0)):
                raise ValueError("Invalid terrain heights, origin_xy or cell_size")
            ny, nx = heights.shape
            lo, hi = float(heights.min()), float(heights.max())
            span = max(hi - lo, 1e-6)
            half_size = cell * [nx - 1, ny - 1] / 2
            center = origin + half_size
            self.height = float(self.config.get("outside_height", lo))
            if not np.isfinite(self.height) or self.height > lo:
                raise ValueError("outside_height must be finite and no higher than the heightfield minimum")
            # XML elevation rows run from +Y to -Y (opposite to hfield_data).
            elevation = ((heights - lo) / span)[::-1]
            ET.SubElement(self.asset, "hfield", name="umr_ground_heightfield",
                          nrow=str(ny), ncol=str(nx),
                          size=f"{half_size[0]:.12g} {half_size[1]:.12g} {span:.12g} 0.1",
                          elevation=" ".join(f"{v:.12g}" for v in elevation.flat))
            ET.SubElement(self.worldbody, "geom", name="umr_ground", type="hfield",
                          hfield="umr_ground_heightfield", pos=f"{center[0]:.12g} {center[1]:.12g} {lo:.12g}",
                          rgba="0.35 0.4 0.45 1")
            ET.SubElement(self.worldbody, "geom", name="umr_ground_background", type="plane",
                          size="10 10 0.1", pos=f"0 0 {self.height:.12g}", rgba="0.3 0.35 0.4 1")
            root = ET.Element("mujoco")
            root.extend([copy.deepcopy(self.asset), copy.deepcopy(self.worldbody)])
            self.model = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"))
            # Restore absolute elevation even for constant fields (MuJoCo normalizes).
            self.model.hfield_data[:] = ((heights - lo) / span).ravel()
            self.data = mujoco.MjData(self.model)
            mujoco.mj_forward(self.model, self.data)
            self.ray_top = hi + 1.0
            self.epsilon = min(float(cell.min()) * 1e-3, 1e-4)
        else:
            raise ValueError(f"Unknown contact terrain type: {self.kind!r}")

    def heights(self, xy):
        xy = np.asarray(xy, dtype=float)
        if xy.shape[-1] != 2 or not np.isfinite(xy).all():
            raise ValueError("Terrain query must contain finite XY points")
        if self.kind == "plane":
            return self.height + xy @ self.slope
        output = np.empty(xy.shape[:-1], dtype=float)
        geom = np.empty(1, dtype=np.int32)
        direction = np.array([0.0, 0.0, -1.0])
        for i, point in enumerate(xy.reshape(-1, 2)):
            distance = mujoco.mj_ray(self.model, self.data, np.r_[point, self.ray_top],
                                     direction, None, True, -1, geom)
            output.flat[i] = self.ray_top - distance if distance >= 0 else self.height
        return output

    def sample(self, points):
        points = np.asarray(points, dtype=float)
        xy = points[..., :2]
        height = self.heights(xy)
        if self.kind == "plane":
            gradients = np.broadcast_to(self.slope, xy.shape)
        else:
            gradients = np.empty_like(xy)
            for axis in range(2):
                offset = np.zeros(2)
                offset[axis] = self.epsilon
                gradients[..., axis] = (self.heights(xy + offset) - self.heights(xy - offset)) / (2 * self.epsilon)
        normals = np.concatenate([-gradients, np.ones((*height.shape, 1))], axis=-1)
        normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
        return height, normals

    def clearance(self, points):
        return np.asarray(points)[..., 2] - self.heights(np.asarray(points)[..., :2])

    def attach(self, robot_xml, output_xml):
        """Replace world floor planes; leave articulated robot geoms untouched."""
        tree = ET.parse(robot_xml)
        root = tree.getroot()
        world = root.find("worldbody")
        if world is None:
            raise ValueError("Robot MJCF has no worldbody")
        for geom in list(world.findall("geom")):
            if geom.get("type") == "plane":
                world.remove(geom)
        asset = root.find("asset")
        if asset is None:
            asset = ET.SubElement(root, "asset")
        asset.extend(copy.deepcopy(list(self.asset)))
        world.extend(copy.deepcopy(list(self.worldbody)))
        tree.write(output_xml, encoding="unicode")
        return Path(output_xml)
