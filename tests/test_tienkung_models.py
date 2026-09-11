"""Check shipped adapters against independent URDF FK and UMR conventions."""
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation
import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_correspondence_ae_dataset import SUPPORTED_ROBOT_SAMPLE_SPECS
from humanoid_retarget_config import load_config, resolve_path
from mujoco_geom_surface import geom_local_mesh, surface_geom_ids


def urdf_forward(urdf, positions, root_transform):
    """URDF origin RPY then local joint rotation, independent of MJCF import."""
    frames = {"pelvis": root_transform}
    remaining = list(urdf.findall("joint"))
    while remaining:
        advanced = False
        for joint in remaining[:]:
            parent = joint.find("parent").get("link")
            if parent not in frames:
                continue
            origin = joint.find("origin")
            transform = np.eye(4)
            transform[:3, 3] = np.fromstring(origin.get("xyz", "0 0 0"), sep=" ")
            rpy = np.fromstring(origin.get("rpy", "0 0 0"), sep=" ")
            transform[:3, :3] = Rotation.from_euler("xyz", rpy).as_matrix()
            if joint.get("type") == "revolute":
                axis = np.fromstring(joint.find("axis").get("xyz"), sep=" ")
                angle = positions[joint.get("name")]
                transform[:3, :3] @= Rotation.from_rotvec(axis * angle).as_matrix()
            frames[joint.find("child").get("link")] = frames[parent] @ transform
            remaining.remove(joint)
            advanced = True
        if not advanced:
            raise ValueError("Disconnected URDF tree")
    return frames


class TienKungModelsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.robots = {}
        for name, count in (("tiangong2dex", 31), ("tiangong2pro", 30), ("tiangong3", 25)):
            config = load_config(ROOT / "robot_configs" / f"humanoid_retarget_{name}_example.json")
            path = resolve_path(config["robot"]["xml"], config)
            model = mujoco.MjModel.from_xml_path(str(path))
            urdf = ET.parse(next((path.parent / "urdf").glob("*.urdf"))).getroot()
            cls.robots[name] = (config, model, urdf, count)

    def test_floating_root_joint_limits_and_pelvis_mass(self):
        for name, (config, model, urdf, count) in self.robots.items():
            with self.subTest(robot=name):
                self.assertEqual((model.nq, model.nv, model.nu), (count + 7, count + 6, count))
                free = np.flatnonzero(model.jnt_type == mujoco.mjtJoint.mjJNT_FREE)
                np.testing.assert_array_equal(free, [0])
                self.assertEqual(model.jnt_bodyid[0], model.body("pelvis").id)
                joints = urdf.findall("joint[@type='revolute']")
                self.assertEqual(len(joints), count)
                for joint in joints:
                    jid = model.joint(joint.get("name")).id
                    limits = joint.find("limit")
                    expected = [float(limits.get("lower")), float(limits.get("upper"))]
                    np.testing.assert_allclose(model.jnt_range[jid], expected, atol=6e-6)
                    self.assertTrue(model.jnt_limited[jid])
                    tpose = config["robot"]["tpose_qpos"][joint.get("name")]
                    self.assertTrue(expected[0] <= tpose <= expected[1])
                mass = float(urdf.find("./link[@name='pelvis']/inertial/mass").get("value"))
                self.assertAlmostEqual(model.body("pelvis").mass[0], mass, delta=5e-5)

    def test_articulated_kinematics_match_urdf(self):
        for name, (_, model, urdf, _) in self.robots.items():
            with self.subTest(robot=name):
                data = mujoco.MjData(model)
                positions = {}
                for jid in range(1, model.njnt):
                    low, high = model.jnt_range[jid]
                    value = np.clip(0.12 * np.sin(jid), low + 1e-3, high - 1e-3)
                    positions[model.joint(jid).name] = value
                    data.qpos[model.jnt_qposadr[jid]] = value
                mujoco.mj_forward(model, data)
                base = np.eye(4)
                base[:3, 3] = data.xpos[model.body("pelvis").id]
                expected = urdf_forward(urdf, positions, base)
                articulated_links = {j.find("child").get("link")
                                     for j in urdf.findall("joint[@type='revolute']")}
                for body_name, transform in expected.items():
                    # The native Dex MJCF places its fixed radar differently
                    # from the URDF. Keep the upstream MJCF sensor frames.
                    if name != "tiangong3" and body_name not in articulated_links:
                        continue
                    bid = model.body(body_name).id
                    np.testing.assert_allclose(data.xpos[bid], transform[:3, 3], atol=2e-5,
                                               err_msg=f"{name}/{body_name} translation")
                    np.testing.assert_allclose(data.xmat[bid].reshape(3, 3), transform[:3, :3],
                                               atol=2e-5, err_msg=f"{name}/{body_name} rotation")

    def test_tpose_ground_and_correspondence_center(self):
        for name, (config, model, _, _) in self.robots.items():
            with self.subTest(robot=name):
                data = mujoco.MjData(model)
                robot = config["robot"]
                for joint, value in robot["tpose_qpos"].items():
                    data.qpos[model.joint(joint).qposadr] = value
                mujoco.mj_forward(model, data)
                sole_heights = []
                for side, sign in (("l", 1), ("r", -1)):
                    shoulder = data.xpos[model.body(f"shoulder_roll_{side}_link").id]
                    elbow = data.xpos[model.body(f"elbow_pitch_{side}_link").id]
                    self.assertAlmostEqual(shoulder[2], elbow[2], delta=2e-6)
                    self.assertGreater(sign * (elbow[1] - shoulder[1]), 0.24)
                    gid = model.geom(f"ankle_roll_{side}_link_visual").id
                    vertices, _ = geom_local_mesh(model, gid)
                    world = vertices @ data.geom_xmat[gid].reshape(3, 3).T + data.geom_xpos[gid]
                    sole_heights.append(world[:, 2].min())
                # Upstream sole meshes have small left/right asymmetries.
                self.assertAlmostEqual(min(sole_heights), 0, delta=2e-5)
                self.assertLess(max(sole_heights), 0.002)
                bounds = []
                for gid in surface_geom_ids(model):
                    vertices, _ = geom_local_mesh(model, int(gid))
                    world = vertices @ data.geom_xmat[gid].reshape(3, 3).T + data.geom_xpos[gid]
                    bounds.append((world[:, 2].min(), world[:, 2].max()))
                low, high = np.min(bounds, axis=0)[0], np.max(bounds, axis=0)[1]
                center = data.xpos[model.body("waist_yaw_link").id, 2]
                ratio = config["correspondence"]["dataset"]["bbox_center_ratio"]
                self.assertAlmostEqual((center - low) / (high - low), ratio, places=6)
                spec = SUPPORTED_ROBOT_SAMPLE_SPECS[name]
                self.assertEqual(spec.tpose_qpos, robot["tpose_qpos"])
                self.assertEqual(spec.root_body_name, robot["point_cloud_center"])
                self.assertTrue(config["solver"]["contact_stabilization"]["enabled"])

    def test_oversized_mesh_conversion_preserves_triangles(self):
        directory = ROOT / "assets/tienkung/tiangong3/meshes"
        for name in ("pelvis", "waist_pitch_link"):
            with self.subTest(mesh=name):
                source = trimesh.load_mesh(directory / f"{name}.STL", process=False)
                converted = trimesh.load_mesh(directory / f"{name}.obj", process=False)
                self.assertGreater(len(source.faces), 200000)
                self.assertEqual(len(converted.faces), len(source.faces))
                np.testing.assert_allclose(source.triangles, converted.triangles, atol=1e-8)


if __name__ == "__main__":
    unittest.main()
