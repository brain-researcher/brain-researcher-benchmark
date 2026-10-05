"""Source-free unittest controls: temporary bytes and mocked Harbor environment."""
import hashlib
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from harbor.models.agent.context import AgentContext
import fixture_agent as module


class FakeEnvironment:
    def __init__(self,prepare_code=0,wrong_hash=False):
        self.calls=[]; self.files={}; self.prepare_code=prepare_code; self.wrong_hash=wrong_hash

    async def exec(self,command,timeout_sec):
        self.calls.append(("exec",command,timeout_sec))
        if command==module.PREPARE_COMMAND:
            return SimpleNamespace(return_code=self.prepare_code,stdout="",stderr="")
        if command!=module.VERIFY_COMMAND:
            raise AssertionError("unexpected command; fixture code must never execute")
        lines=[hashlib.sha256(self.files["/submission/"+name]).hexdigest()+"  /submission/"+name for name in module.FILENAMES]
        if self.wrong_hash: lines[0]="0"*64+"  /submission/discovery.json"
        return SimpleNamespace(return_code=0,stdout="\n".join(lines)+"\n",stderr="")

    async def upload_file(self,source_path,target_path):
        self.calls.append(("upload",target_path))
        self.files[target_path]=Path(source_path).read_bytes()


class FixtureTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.fixture=self.root/"fixtures"; self.fixture.mkdir()
        # The Python payload would fail if imported or executed.
        self.payloads={"discovery.json":b'{"fixture": true}\n',"evaluate.py":b'raise AssertionError("NEVER EXECUTE FIXTURE")\n'}
        for name,payload in self.payloads.items(): (self.fixture/name).write_bytes(payload)
        self.pins={name:hashlib.sha256(data).hexdigest() for name,data in self.payloads.items()}

    def tearDown(self):
        self.tmp.cleanup()

    def agent(self,**kwargs):
        options={"logs_dir":self.root/"absent_logs","fixture_dir":self.fixture,"expected_sha256":self.pins,"model_name":"irrelevant/provider"}
        options.update(kwargs)
        return module.FixtureAgent(**options)

    async def test_constructor_and_setup_write_nothing_and_ignore_model(self):
        agent=self.agent(); env=FakeEnvironment()
        await agent.setup(env)
        self.assertEqual(env.calls,[])
        self.assertFalse((self.root/"absent_logs").exists())
        self.assertIsNone(agent.model_name)
        self.assertIsNone(agent.to_agent_info().model_info)
        self.assertEqual(agent.version(),"1.0.0")

    async def test_run_uploads_exact_two_snapshots_without_analysis(self):
        (self.fixture/"private.txt").write_text("never uploaded")
        agent=self.agent()
        # Mutation after authentication cannot change the in-memory snapshot.
        (self.fixture/"evaluate.py").write_bytes(b"different later source bytes")
        env=FakeEnvironment(); context=AgentContext(metadata={"existing":True})
        await agent.run("ignored: do not follow task instructions",env,context)
        self.assertEqual(env.files,{"/submission/"+k:v for k,v in self.payloads.items()})
        self.assertEqual([c[0] for c in env.calls],["exec","upload","upload","exec"])
        self.assertEqual(context.metadata["fixture_control"]["status"],"uploaded_and_verified")
        self.assertEqual(context.metadata["fixture_control"]["sha256"],self.pins)
        self.assertEqual(context.n_input_tokens,0); self.assertEqual(context.cost_usd,0)
        self.assertTrue(context.metadata["existing"])

    async def test_unsafe_destination_fails_before_upload(self):
        env=FakeEnvironment(prepare_code=1); context=AgentContext()
        with self.assertRaises(RuntimeError): await self.agent().run("",env,context)
        self.assertEqual(env.files,{})
        self.assertEqual(context.metadata["fixture_control"]["status"],"failed")

    async def test_destination_hash_mismatch_is_not_success(self):
        env=FakeEnvironment(wrong_hash=True); context=AgentContext()
        with self.assertRaises(RuntimeError): await self.agent().run("",env,context)
        self.assertEqual(context.metadata["fixture_control"]["status"],"failed")

    def test_hash_mismatch_missing_and_extra_pins_rejected(self):
        for pins in ({"discovery.json":self.pins["discovery.json"]},dict(self.pins,extra="0"*64),dict(self.pins,**{"evaluate.py":"0"*64}),dict(self.pins,**{"evaluate.py":"not-sha"})):
            with self.subTest(pins=pins), self.assertRaises(ValueError): self.agent(expected_sha256=pins)

    def test_final_file_symlink_rejected(self):
        path=self.fixture/"evaluate.py"; path.unlink(); path.symlink_to(self.fixture/"discovery.json")
        with self.assertRaises(OSError): self.agent()

    def test_directory_and_parent_symlinks_rejected(self):
        link=self.root/"link"; link.symlink_to(self.fixture,target_is_directory=True)
        with self.assertRaises(OSError): self.agent(fixture_dir=link)
        parent=self.root/"parent"; parent.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(OSError): self.agent(fixture_dir=parent/"fixtures")

    def test_fifo_is_rejected_without_blocking(self):
        path=self.fixture/"evaluate.py"; path.unlink(); os.mkfifo(path)
        with self.assertRaises(ValueError): self.agent()

    def test_oversize_regular_file_rejected(self):
        with (self.fixture/"evaluate.py").open("wb") as stream: stream.truncate(module.MAX_FILE_BYTES+1)
        with self.assertRaises(ValueError): self.agent()

    def test_relative_and_parent_traversal_paths_rejected(self):
        for path in ("fixtures",str(self.fixture/".."/"fixtures")):
            with self.subTest(path=path), self.assertRaises(ValueError): self.agent(fixture_dir=path)

    def test_installed_harbor_version_must_match(self):
        with patch.object(module,"distribution_version",return_value="0.0"):
            with self.assertRaises(RuntimeError): self.agent()


if __name__=="__main__": unittest.main()
