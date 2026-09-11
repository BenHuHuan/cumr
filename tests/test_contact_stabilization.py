"""Run with: python -m unittest discover -s tests -v"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from contact_stabilization import (ContactSettings, build_contact_plan, detect_contacts,
                                   point_speeds, support_height_offsets, contact_metrics,
                                   select_support_probes, rebase_contact_targets, contact_signature)
from contact_terrain import ContactTerrain
import retarget_smpl_to_humanoid_surface_vector as retarget


class ContactDetectionTests(unittest.TestCase):
    def setUp(self):
        self.settings = ContactSettings(enabled=True)
        self.terrain = ContactTerrain()

    def test_fast_low_foot_and_slow_airborne_foot_are_not_locked(self):
        points = np.zeros((30, 3, 3))
        points[:, 0, 0] = np.arange(30) / 30  # 1 m/s, on floor
        points[:, 1, 2] = .15  # stationary in air
        points[:, 2, 2] = .01  # stationary sole
        active, _ = detect_contacts(points, 30, self.terrain, self.settings)
        self.assertFalse(active[:, :2].any())
        self.assertTrue(active[:, 2].all())

    def test_window_does_not_cancel_oscillation(self):
        points = np.zeros((40, 1, 3))
        points[::2, 0, 0] = .05
        self.assertGreater(point_speeds(points, 30, .2).min(), 1)

    def test_fps_and_stride_have_same_speed_units(self):
        points = np.zeros((60, 1, 3))
        points[:, 0, 0] = np.arange(60) / 60 * .12
        np.testing.assert_allclose(point_speeds(points, 60, .067), .12)
        np.testing.assert_allclose(point_speeds(points[::2], 30, .067), .12)

    def test_hysteresis_short_contact_and_liftoff(self):
        p = np.zeros((20, 1, 3))
        p[:, 0, 2] = [.04] * 3 + [.03] * 3 + [.04] * 3 + [.06] * 3 + [.03] + [.1] * 7
        s = ContactSettings(enabled=True, speed_enter=10, speed_exit=10)
        active, _ = detect_contacts(p, 30, self.terrain, s)
        self.assertFalse(active[:3].any())
        self.assertTrue(active[3:9].all())
        self.assertFalse(active[9:].any())

    def test_toe_can_pivot_while_heel_lifts(self):
        p = np.zeros((40, 2, 3))
        p[:, 1, 2] = np.linspace(0, .2, 40)
        active, _ = detect_contacts(p, 30, self.terrain, self.settings)
        self.assertTrue(active[:, 0].all())
        self.assertFalse(active[-10:, 1].any())

    def test_interval_targets_are_fixed_and_released(self):
        p = np.zeros((60, 1, 3))
        p[:20, 0, 0] = np.linspace(0, .01, 20)
        p[20:40, 0, 0] = np.linspace(.01, .3, 20)
        p[20:40, 0, 2] = .2
        p[40:, 0, 0] = .3
        plan = build_contact_plan(p, np.array([0]), np.array(['leftFoot']), 30, self.terrain, self.settings)
        np.testing.assert_allclose(np.diff(plan.targets[3:15, 0], axis=0), 0)
        self.assertFalse(plan.active[25:35].any())
        self.assertGreater(plan.targets[-1, 0, 0], .25)
        np.testing.assert_allclose(plan.targets[plan.active, 2], 0)

    def test_height_filter_holds_correction_during_flight(self):
        p = np.zeros((30, 1, 3))
        p[:15, 0, 2] = .03
        p[15:, 0, 2] = .5
        active = np.zeros((30, 1), dtype=bool)
        active[:15] = True
        offsets = support_height_offsets(p, active, 30, self.terrain, self.settings)
        np.testing.assert_allclose(offsets[15:], offsets[14])
        self.assertLess(offsets.max(), .031)

    def test_empty_and_single_frame_do_not_invent_support(self):
        plan = build_contact_plan(np.zeros((1, 2, 3)), np.array([], dtype=int),
                                  np.array([]), 30, self.terrain, self.settings)
        self.assertEqual(plan.active.shape, (1, 0))
        self.assertIsNone(contact_metrics(np.zeros((1, 0, 3)), plan, 30, self.terrain)['stance_slip_mean_m_s'])
        active, _ = detect_contacts(np.zeros((1, 1, 3)), 30, self.terrain, self.settings)
        self.assertFalse(active.any())

    def test_bad_configuration_fails_early(self):
        for config in ({'typo': 1}, {'speed_exit': .1}, {'position_cost': float('nan')},
                       {'points_per_foot': 1}, {'projection_iters': 1.5}):
            with self.assertRaises(ValueError):
                ContactSettings.from_config(config)

    def test_native_z_up_and_smpl_y_up_select_same_sole(self):
        robot = np.array([[0,0,0], [.1,0,0], [0,.05,0], [.1,.05,0], [0,0,.1]])
        source_z = robot.copy()
        source_y = source_z[:, [0,2,1]]
        groups = {'leftFoot': np.arange(5)}
        ids_z, _ = select_support_probes(source_z, robot, groups, 4, source_height_axis=2)
        ids_y, _ = select_support_probes(source_y, robot, groups, 4)
        np.testing.assert_array_equal(ids_y, ids_z)
        self.assertNotIn(4, ids_z)

    def test_robot_targets_preserve_width_and_stay_fixed(self):
        source = np.zeros((10, 2, 3))
        source[:,1,0] = .1
        plan = build_contact_plan(source, np.arange(2), np.array(['leftFoot']*2), 30, self.terrain, self.settings)
        robot = source.copy()
        robot[:,1,0] = .2
        robot[:,:,2] = .01
        rebase_contact_targets(plan, robot, self.terrain)
        np.testing.assert_allclose(plan.targets[:,1,0] - plan.targets[:,0,0], .2)
        np.testing.assert_allclose(np.diff(plan.targets,axis=0), 0)
        np.testing.assert_allclose(plan.targets[:,:,2], 0)

    def test_signature_tracks_terrain_content_and_explicit_disable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'map.npz'
            np.savez(path, heights=np.zeros((2,2)), origin_xy=[0,0], cell_size=1)
            config = {'enabled': True, 'terrain': {'type':'heightfield', 'path':str(path)}}
            before = contact_signature(config, Path)
            np.savez(path, heights=np.ones((2,2)), origin_xy=[0,0], cell_size=1)
            self.assertNotEqual(before, contact_signature(config, Path))
            self.assertNotEqual(contact_signature({'enabled':True}, Path), contact_signature({'enabled':False}, Path))


class TerrainTests(unittest.TestCase):
    def test_slope_height_and_constraint_gradient(self):
        terrain = ContactTerrain({'height': .2, 'slope': [.1, -.2]})
        p = np.array([[2., 1., .25]])
        h, n = terrain.sample(p)
        np.testing.assert_allclose(h, .2)
        np.testing.assert_allclose(n / n[:, 2:3], [[-.1, .2, 1]])
        np.testing.assert_allclose(terrain.clearance(p), .05)

    def test_heightfield_and_saved_scene_agree(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            np.savez(path/'terrain.npz', heights=[[0., .2, .2], [.4, .6, .6]],
                     origin_xy=[-1., -1.], cell_size=[1., 2.])
            terrain = ContactTerrain({'type': 'heightfield', 'path': str(path/'terrain.npz')})
            xy = np.array([[-1,-1],[0,-1],[-1,1],[0,1],[-.5,0],[2,2]])
            expected = np.array([0,.2,.4,.6,.3,0])
            np.testing.assert_allclose(terrain.heights(xy), expected, atol=1e-7)
            (path/'robot.xml').write_text('<mujoco><worldbody><geom name="floor" type="plane" size="1 1 .1"/></worldbody></mujoco>')
            terrain.attach(path/'robot.xml', path/'scene.xml')
            model = mujoco.MjModel.from_xml_path(str(path/'scene.xml'))
            data = mujoco.MjData(model)
            mujoco.mj_forward(model, data)
            measured = []
            for point in xy:
                d = mujoco.mj_ray(model, data, np.r_[point, 2.], np.array([0.,0.,-1.]),
                                  None, True, -1, np.empty(1, dtype=np.int32))
                measured.append(2 - d)
            np.testing.assert_allclose(measured, expected, atol=1e-7)
            self.assertIsNone(ET.parse(path/'scene.xml').find('.//geom[@name="floor"]'))


class ConstrainedSolverTests(unittest.TestCase):
    def test_contact_projection_reduces_drift_with_joint_and_floor_constraints(self):
        xml = '''<mujoco><worldbody><body pos="0 0 .05"><freejoint/>
        <geom name="sole" type="box" size=".12 .2 .05" mass="1"/>
        <body pos="0 0 .2"><joint name="arm" type="hinge" range="-.3 .3"/>
        <geom type="sphere" size=".02" mass=".1"/></body>
        </body></worldbody></mujoco>'''
        model = mujoco.MjModel.from_xml_string(xml)
        data = mujoco.MjData(model)
        local = np.array([[-.1,-.15,-.05], [.1,-.15,-.05], [-.1,.15,-.05], [.1,.15,-.05]])
        template = {'geom_ids': np.zeros(4, dtype=int), 'local_pos': local}
        ground = local + [0,0,.05]
        settings = ContactSettings(enabled=True)
        terrain = ContactTerrain()
        source = np.broadcast_to(ground, (30,4,3)).copy()
        source[:,:,0] += (np.linspace(0, .025, 30))[:,None]
        plan = build_contact_plan(source, np.arange(4), np.array(['leftFoot']*4), 30, terrain, settings)
        with patch.object(sys, 'argv', ['retarget', '--config', str(Path(__file__).resolve().parents[1]/'robot_configs/humanoid_retarget_unitree_g1_example.json')]):
            args = retarget.parse_args()
        args.ground_contact_anchor_cost = 0
        args.ground_contact_map_cost = 0
        args.self_contact_map_cost = 0
        args.ground_penetration_max_points = 0
        q = model.qpos0.copy()
        q[7] = .2
        q[2] += .015
        joint_qpos, joint_dofs, _, _ = retarget.common.scalar_qpos_joint_addrs(model)
        limits, _ = retarget.common.build_scalar_joint_limits(model, {'arm': (-.1, .1)})
        before, after = [], []
        for t in range(len(source)):
            q[0] = source[t,0,0] - ground[0,0]
            retarget.common.set_qpos(model, data, q)
            before.append(retarget.common.template_points_to_world(data, template, np.arange(4)))
            result, _ = retarget.solve_frame_body_segment_qp(
                model, data, q, None, None, source[t], None, None, np.arange(4),
                np.zeros(4, dtype=int), np.ones(4)*10, None, None, None, None, None,
                template, joint_qpos, joint_dofs, args, joint_limits_by_qpos=limits,
                iters=8, contact_frame=plan.frame(t), contact_settings=settings, terrain=terrain,
                qpos_reference=q,
            )
            self.assertTrue(np.isfinite(result).all())
            self.assertAlmostEqual(np.linalg.norm(result[3:7]), 1, places=6)
            self.assertLessEqual(abs(result[7]), .100001)
            retarget.common.set_qpos(model, data, result)
            after.append(retarget.common.template_points_to_world(data, template, np.arange(4)))
        before = contact_metrics(np.array(before), plan, 30, terrain)
        after = contact_metrics(np.array(after), plan, 30, terrain)
        self.assertLess(after['stance_slip_mean_m_s'], before['stance_slip_mean_m_s']*.02)
        self.assertLess(after['support_height_p95_m'], .0001)
        self.assertLess(after['max_probe_penetration_m'], .00001)


if __name__ == '__main__':
    unittest.main()
