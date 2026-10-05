"""Host adapter controls, no image/model/scientific source execution."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent))
import release_environment as runtime


class RuntimeTests(unittest.TestCase):
    def test_capture_rejects_symlink_before_transfer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'real').write_text('x')
            (root/'link').symlink_to(root/'real')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                runtime.authenticate_capture(root)

    def test_capture_detects_change_and_enforces_cap(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root/'evaluate.py'
            path.write_text('print(1)')
            before = runtime.authenticate_capture(root)
            path.write_text('print(2)')
            self.assertNotEqual(before, runtime.authenticate_capture(root))
            with self.assertRaisesRegex(ValueError, '8 MiB'):
                runtime.authenticate_capture(root, limit=1)

    def test_failed_agent_teardown_blocks_verifier(self):
        with patch.object(runtime, 'docker_metadata', return_value='abcdef'):
            with self.assertRaisesRegex(ValueError, 'still has a running'):
                runtime.require_stopped('owned-trial')

    def test_exact_project_name_and_stopped_success(self):
        self.assertEqual(runtime.project_name('GRADIENT-001__AbC__env'), 'gradient-001__abc__env')
        with patch.object(runtime, 'docker_metadata', return_value=''):
            runtime.require_stopped('owned-trial')

    def test_failed_post_start_certification_cleans_exact_environment(self):
        env = object.__new__(runtime.ReleaseDocker)
        env._role = 'agent'
        env._approval_path = Path('/unused')
        env._image = {'id':'sha256:fixture', 'layers':[]}
        env._trial = Path('/unused-trial')
        with patch.object(runtime, 'authenticate', return_value={}), \
             patch.object(runtime, 'docker_metadata', return_value=json.dumps(env._image)), \
             patch.object(runtime.DockerEnvironment, 'start', new_callable=AsyncMock) as start, \
             patch.object(runtime.DockerEnvironment, 'stop', new_callable=AsyncMock) as stop, \
             patch.object(env, '_certify_started', side_effect=ValueError('bad actual settings')):
            with self.assertRaisesRegex(ValueError, 'bad actual settings'):
                asyncio.run(env.start(False))
            start.assert_awaited_once_with(force_build=False)
            stop.assert_awaited_once_with(env, delete=True)


if __name__ == '__main__':
    unittest.main()
