from unittest import TestCase
from unittest.mock import patch

import native_candidate_guard_v3 as codec
from context_runtime import ContextError
from native_candidate_ownership import pack_guard, unpack_guard


def example():
    return {
        "version": 1,
        "affected_ids": [f"fixture:long-id:{index:05d}:" + "x" * 512 for index in range(15)],
        "sources": [],
        "native_nodes": {},
        "expected": [],
        "native_inputs": [],
    }


class MaintenanceGuardTest(TestCase):
    def test_maintenance_profile_only_changes_total_raw_budget(self):
        seal = example()
        with patch.object(codec, "MAX_PACKED", 4096), patch.object(codec, "MAX_CHUNK", 1024):
            with self.assertRaisesRegex(ContextError, "total raw chunks exceed"):
                pack_guard(seal, bounded=True)
            with self.assertRaisesRegex(ContextError, "requires bounded"):
                pack_guard(seal, maintenance=True)
            envelope = pack_guard(seal, bounded=True, maintenance=True)
            self.assertEqual(envelope["guard_codec"], codec.MAINTENANCE_CODEC)
            self.assertEqual(unpack_guard(envelope), seal)
            self.assertEqual(codec.sized_digest(seal)[1], envelope["logical_sha256"])
            with self.assertRaisesRegex(ContextError, "aggregate bounds"):
                codec.unpack(dict(envelope, guard_codec=codec.CODEC))
            with patch.object(codec, "MAX_MAINTENANCE_PACKED", 4096):
                with self.assertRaisesRegex(ContextError, "aggregate bounds"):
                    codec.unpack(envelope)
            bad = dict(envelope, chunks=[dict(envelope["chunks"][0], bytes=1025), *envelope["chunks"][1:]])
            with self.assertRaisesRegex(ContextError, "native guard chunk"):
                codec.unpack(bad)
            bad = dict(envelope, chunks=list(reversed(envelope["chunks"])))
            with self.assertRaisesRegex(ContextError, "reordered"):
                codec.unpack(bad)

    def test_large_single_record_remains_rejected_in_each_profile(self):
        with patch.object(codec, "MAX_CHUNK", 256):
            for maintenance in (False, True):
                with self.assertRaisesRegex(ContextError, "affected_ids record exceeds"):
                    pack_guard(example(), bounded=True, maintenance=maintenance)
