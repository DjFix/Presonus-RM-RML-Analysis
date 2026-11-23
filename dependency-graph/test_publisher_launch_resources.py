"""Check resource arguments on the publication and compiler entry points."""
import json
import pathlib
import shlex
import tempfile
import unittest
from unittest.mock import patch

import refresh_graph


class PublisherLaunchResources(unittest.TestCase):
    def docker_argv(self, out, label, analysis=False):
        with patch.object(refresh_graph, "run") as run, patch.object(
            refresh_graph, "memgraph_network", return_value="test-network"
        ):
            refresh_graph.docker(["test-command"], out, label, analysis=analysis)
        return shlex.split(run.call_args.args[0][-1])

    def test_publication_and_resume_inherit_host_memory(self):
        for label in ("publish", "resume-123"):
            with self.subTest(label=label):
                argv = self.docker_argv(pathlib.Path("."), label)
                self.assertEqual(argv[:2], ["docker", "run"])
                self.assertFalse(any(arg.split("=")[0] in ("-m", "--memory") for arg in argv))

    def test_extraction_uses_computed_compiler_profile(self):
        with tempfile.TemporaryDirectory() as scratch:
            out = pathlib.Path(scratch)
            (out / "units.json").write_text("[{}]")
            profile = {"builder_jobs": 2, "resources": {"available_memory_bytes": 8 * 1024**3}}
            with patch.object(refresh_graph, "choose_compiler_limits", return_value=profile):
                argv = self.docker_argv(out, "extract", analysis=True)
            recorded = json.loads((out / "compiler-host-resources.json").read_text())
            self.assertEqual(recorded["docker_memory"], "6144m")
            self.assertIn("--memory=" + recorded["docker_memory"], argv)
