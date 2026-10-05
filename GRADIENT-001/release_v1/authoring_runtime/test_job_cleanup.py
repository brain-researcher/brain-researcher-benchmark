"""Source-free mocks only: no real Docker call, process signal or source analysis."""
import json
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import job_cleanup as cleanup


class CleanupTests(unittest.TestCase):
    def fixture(self, root):
        jobs = root / "jobs"
        job = jobs / "one-job"
        task = root / "GRADIENT-HELDOUT-001"
        folder = job / "GRADIENT-HELDOUT-001__jRw7Nak"
        folder.mkdir(parents=True)
        (folder / "config.json").write_text(json.dumps({"trial_name": folder.name,
            "trials_dir": str(job), "task": {"path": str(task)},
            "environment": {"import_path": "release_environment:ReleaseDocker"}}))
        return jobs, job, task, folder

    def test_broad_and_outside_paths_refused_without_docker(self):
        with patch.object(cleanup, "docker") as docker:
            for path in (Path("/"), cleanup.ROOT, cleanup.JOBS, cleanup.ROOT / "elsewhere" / "job"):
                self.assertEqual(cleanup.cleanup_job(path)["status"], "refused_or_failed")
            docker.assert_not_called()

    def test_job_symlink_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            jobs, job, task, _ = self.fixture(root)
            (jobs / "alias").symlink_to(job, target_is_directory=True)
            with patch.object(cleanup, "JOBS", jobs), patch.object(cleanup, "TASK", task), patch.object(cleanup, "docker") as docker:
                self.assertEqual(cleanup.cleanup_job(jobs / "alias")["status"], "refused_or_failed")
                docker.assert_not_called()

    def test_trial_identity_mismatch_refused_before_query(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs, job, task, folder = self.fixture(Path(directory))
            value = json.loads((folder / "config.json").read_text())
            value["trial_name"] = "unrelated"
            (folder / "config.json").write_text(json.dumps(value))
            with patch.object(cleanup, "JOBS", jobs), patch.object(cleanup, "TASK", task), patch.object(cleanup, "docker") as docker:
                self.assertEqual(cleanup.cleanup_job(job)["status"], "refused_or_failed")
                docker.assert_not_called()

    def test_exact_project_derivation_and_long_name_bound(self):
        self.assertEqual(cleanup.projects_for_trial("GRADIENT-HELDOUT-001__jRw7Nak"),
            ["gradient-heldout-001__jrw7nak__env", "gradient-heldout-001__jrw7nak__verifier__trial"])
        self.assertLessEqual(len(cleanup.projects_for_trial("GRADIENT-HELDOUT-001__" + "x"*32)[1]), 63)
        with self.assertRaises(ValueError): cleanup.projects_for_trial("other__x")

    def test_wrong_container_label_prevents_all_removal(self):
        identity = "a" * 64
        with tempfile.TemporaryDirectory() as directory:
            jobs, job, task, _ = self.fixture(Path(directory))
            def fake(args):
                if args[0] == "ps": return identity
                if args[0] == "inspect": return json.dumps([{"Id": identity, "Config": {"Labels": {cleanup.LABEL: "other"}}}])
                raise AssertionError("unexpected mutation")
            with patch.object(cleanup, "JOBS", jobs), patch.object(cleanup, "TASK", task), patch.object(cleanup, "docker", side_effect=fake) as docker:
                result = cleanup.cleanup_job(job)
                self.assertEqual(result["status"], "refused_or_failed")
                self.assertFalse(any(call.args[0][0] == "rm" for call in docker.call_args_list))

    def test_foreign_network_attachment_prevents_removal(self):
        network = "b" * 64
        with tempfile.TemporaryDirectory() as directory:
            jobs, job, task, folder = self.fixture(Path(directory))
            project = cleanup.projects_for_trial(folder.name)[0]
            def fake(args):
                if args[0] == "ps": return ""
                if args[:2] == ["network", "ls"]: return network if args[-1].endswith(project) else ""
                if args[:2] == ["network", "inspect"]:
                    return json.dumps([{"Id": network, "Labels": {cleanup.LABEL: project}, "Containers": {"c"*64: {}}}])
                raise AssertionError("unexpected mutation")
            with patch.object(cleanup, "JOBS", jobs), patch.object(cleanup, "TASK", task), patch.object(cleanup, "docker", side_effect=fake):
                result = cleanup.cleanup_job(job)
                self.assertEqual(result["status"], "refused_or_failed")
                self.assertEqual(result["removed_containers"], [])
                self.assertEqual(result["removed_networks"], [])

    def test_owned_container_and_network_only(self):
        container, network = "a"*64, "b"*64
        with tempfile.TemporaryDirectory() as directory:
            jobs, job, task, folder = self.fixture(Path(directory))
            project = cleanup.projects_for_trial(folder.name)[0]
            alive = {"container": True, "network": True}
            def fake(args):
                if args[0] == "ps": return container if args[-1].endswith(project) and alive["container"] else ""
                if args[:2] == ["network", "ls"]: return network if args[-1].endswith(project) and alive["network"] else ""
                if args[0] == "inspect":
                    return json.dumps([{"Id": container, "Config": {"Labels": {cleanup.LABEL: project, "com.docker.compose.service": "main"}}}])
                if args[:2] == ["network", "inspect"]:
                    return json.dumps([{"Id": network, "Labels": {cleanup.LABEL: project}, "Containers": {container: {}} if alive["container"] else {}}])
                if args == ["rm", "-f", container]: alive["container"] = False; return container
                if args == ["network", "rm", network]: alive["network"] = False; return network
                raise AssertionError(args)
            with patch.object(cleanup, "JOBS", jobs), patch.object(cleanup, "TASK", task), patch.object(cleanup, "docker", side_effect=fake):
                result = cleanup.cleanup_job(job)
                self.assertEqual(result["status"], "cleaned")
                self.assertEqual(result["removed_containers"], [{"id": container, "project": project}])
                self.assertEqual(result["removed_networks"], [{"id": network, "project": project}])

    def test_termination_escalates_exact_owned_group(self):
        child = Mock(pid=987654, returncode=None)
        child.poll.return_value = None
        def wait(timeout):
            if timeout != 5: raise subprocess.TimeoutExpired("owned", timeout)
            child.returncode = -9
            child.poll.return_value = -9
            return -9
        child.wait.side_effect = wait
        with patch.object(cleanup.os, "getpgid", return_value=child.pid), patch.object(cleanup.os, "getsid", return_value=child.pid), patch.object(cleanup.os, "killpg") as kill:
            result = cleanup.terminate_process(child)
        self.assertEqual(result["status"], "terminated")
        self.assertEqual([call.args for call in kill.call_args_list], [(child.pid, signal.SIGINT), (child.pid, signal.SIGTERM), (child.pid, signal.SIGKILL)])
        self.assertEqual([call.kwargs["timeout"] for call in child.wait.call_args_list], [30, 15, 5])

    def test_termination_refuses_shared_session(self):
        child = Mock(pid=987654, returncode=None)
        child.poll.return_value = None
        with patch.object(cleanup.os, "getpgid", return_value=111), patch.object(cleanup.os, "killpg") as kill:
            self.assertEqual(cleanup.terminate_process(child)["status"], "refused_or_failed")
            kill.assert_not_called()

    def test_already_exited_never_signals(self):
        child = Mock(pid=987654, returncode=0)
        child.poll.return_value = 0
        with patch.object(cleanup.os, "killpg") as kill:
            self.assertEqual(cleanup.terminate_process(child)["status"], "already_exited")
            kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
