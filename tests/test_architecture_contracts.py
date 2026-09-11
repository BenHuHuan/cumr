"""Negative tests for declared boundaries, plus the published result contract."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_architecture_contracts import python_boundary_errors, shared_contact_errors, protected_path_errors
from sync_agent_guides import GUIDES, expected_guide, check_guides


class ArchitectureContractTests(unittest.TestCase):
    def test_low_level_imports_reject_hidden_reverse_dependencies(self):
        source = "import numpy as np\ndef detect():\n    import humanoid_retarget_pipeline as run\n"
        errors = python_boundary_errors(source, "contact.py", ["numpy"])
        self.assertTrue(any("humanoid_retarget_pipeline" in error for error in errors))
        self.assertEqual(python_boundary_errors("from pathlib import Path\nimport numpy\n", "contact.py", ["numpy"]), [])
        self.assertTrue(python_boundary_errors("from . import hidden\n", "contact.py", ["numpy"]))

    def test_dynamic_import_bypass_is_rejected(self):
        for source in ("from importlib import import_module as load\nload('torch')",
                       "from builtins import __import__ as load\nload('torch')"):
            with self.subTest(source=source):
                self.assertTrue(python_boundary_errors(source, "contact.py", ["numpy"]))

    def test_missing_final_correction_is_rejected(self):
        self.assertTrue(shared_contact_errors("def main():\n    save(qpos)\n", "batch.py"))
        self.assertEqual(shared_contact_errors("def main():\n    base.finalize_contact_motion()\n", "batch.py"), [])
        self.assertTrue(shared_contact_errors("def unused():\n    finalize_contact_motion()\ndef main():\n    pass\n", "batch.py"))

    def test_agent_guide_drift_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("# Test canonical guide\n")
            for name in GUIDES:
                (root / name).write_text(expected_guide(root))
            self.assertEqual(check_guides(root), [])
            (root / "KIMI.md").write_text("a conflicting policy\n")
            self.assertEqual(len(check_guides(root)), 1)
            self.assertIn("KIMI.md", check_guides(root)[0])

    def test_private_artifact_paths_are_rejected(self):
        policy = json.loads((ROOT / "docs/architecture/contracts.json").read_text())
        paths = ["smpl/SMPLX_NEUTRAL.npz", "output/train/checkpoint.npz", "assets/run.floating_mjcf.xml"]
        self.assertEqual(len(protected_path_errors(paths, policy["protected_git_patterns"])), len(paths))
        self.assertEqual(protected_path_errors(["docs/validation/result.npz", "assets/robot/mesh.STL"],
                                               policy["protected_git_patterns"]), [])

    def test_published_outputs_preserve_shape_time_and_quaternion_contract(self):
        policy = json.loads((ROOT / "docs/architecture/contracts.json").read_text())
        directory = ROOT / "docs/validation/g1_dance_300_599"
        for name in ("baseline", "stabilized"):
            with self.subTest(result=name), np.load(directory / f"{name}.npz", allow_pickle=False) as data:
                self.assertTrue(set(policy["robot_output_required_fields"]).issubset(data.files))
                qpos = data["qpos"]
                self.assertEqual(qpos.shape, (len(data["frame_ids"]), 7 + len(data["robot_joint_names"])))
                self.assertTrue(np.isfinite(qpos).all())
                self.assertGreater(data["fps"].item(), 0)
                self.assertTrue((np.diff(data["frame_ids"]) > 0).all())
                np.testing.assert_allclose(np.linalg.norm(qpos[:, 3:7], axis=1), 1, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
