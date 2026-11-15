"""Repeated build references retain a final symlink-resolution barrier."""
from pathlib import Path
import tempfile
import unittest
from refresh_publish import BuildPaths
from context_runtime import ContextError


class BuildPathTests(unittest.TestCase):
    def test_retargeted_alias_fails_before_fact_return(self):
        base=Path(__file__).resolve().parents[1]/'temp/test-work'
        base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as folder:
            root=Path(folder);a=root/'a';b=root/'b';alias=root/'alias'
            a.write_text('a');b.write_text('b');alias.symlink_to(a)
            paths=BuildPaths()
            self.assertEqual(paths.resolve(alias),a)
            self.assertEqual(paths.resolve(alias),a)
            paths.verify()
            alias.unlink();alias.symlink_to(b)
            with self.assertRaises(ContextError):paths.verify()

    def test_missing_build_output_is_still_supported(self):
        paths=BuildPaths();missing=Path(__file__).resolve().parents[1]/'temp/test-work/nonexistent/build/object.o'
        self.assertEqual(paths.resolve(missing),missing.resolve())
        paths.verify()


if __name__=='__main__':unittest.main()
