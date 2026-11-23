import copy
import json
import unittest
from unittest.mock import patch

import native_candidate_guard_v3 as v3
from context_runtime import ContextError
from native_candidate_ownership import OWNER, canonical, canonical_matches, checkpoint_id, digest, pack_guard, read_checkpoint, unpack_guard


def seal():
    row = "Node α K 🚦"
    support = ["z", "α", "a", "α"]
    data = {
        "version": 1,
        "scope": "affected_current_function_candidate_completeness",
        "affected_ids": [f"{row} {i}" for i in range(30)],
        "native": {"sha256": "a"*64},
        "native_inputs": [{"path": "ELF.bin", "sha256": "b"*64}],
        "native_nodes": {"native:f": {"id": "native:f", "metadata": {"range": [123, 56]}}},
        "expected": [{"src": "native:f", "dst": f"{row} 0", "properties": "encoded name only; not ABI proof"}],
        "sources": [{"properties": {"id": f"{row} {i}", "mangled": "_Z1fv"}, "owners": support} for i in range(30)],
    }
    data["seal_sha256"] = digest(data)
    return data


class CodecV3(unittest.TestCase):
    def setUp(self):
        self.cap = patch.object(v3, "MAX_CHUNK", 256)
        self.cap.start()
        self.addCleanup(self.cap.stop)
        self.seal = seal()
        self.envelope = pack_guard(self.seal, bounded=True)
        self.assertGreater(len(self.envelope["chunks"]), 2)

    def test_exact_logical_identity_and_shared_lists(self):
        actual = unpack_guard(self.envelope)
        self.assertEqual(actual, self.seal)
        self.assertEqual(canonical(actual), canonical(self.seal))
        self.assertEqual(self.envelope["logical_sha256"], digest(self.seal))
        self.assertTrue(canonical_matches(canonical(self.envelope), self.seal))
        self.assertIs(actual["sources"][0]["owners"], actual["sources"][-1]["owners"])

    def test_fail_closed_on_corrupt_missing_reordered_duplicate_chunks(self):
        def corrupt(value):
            value["chunks"][0]["data"] = "A" + value["chunks"][0]["data"][1:]

        def remove(value):
            value["chunks"].pop()

        def reverse(value):
            value["chunks"].reverse()

        def duplicate(value):
            value["chunks"].append(value["chunks"][0])

        def reindex(value):
            value["chunks"][:2] = reversed(value["chunks"][:2])
            for i, chunk in enumerate(value["chunks"]):
                chunk["index"] = i
            value["chunk_manifest_sha256"] = v3.manifest_digest(value["chunks"])

        for change in (corrupt, remove, reverse, duplicate, reindex):
            with self.subTest(change=change.__name__):
                value = copy.deepcopy(self.envelope)
                change(value)
                with self.assertRaises(ContextError):
                    unpack_guard(value)

    def test_missing_chunk_with_forged_manifest_cannot_resume(self):
        value = copy.deepcopy(self.envelope)
        removed = value["chunks"].pop()
        value["packed_bytes"] -= removed["bytes"]
        value["chunk_manifest_sha256"] = v3.manifest_digest(value["chunks"])
        with self.assertRaises(ContextError):
            unpack_guard(value)
        self.assertEqual(unpack_guard(self.envelope), self.seal)

    def test_compressed_payload_bound_and_logical_digest(self):
        for field, wrong in (("logical_bytes",1), ("packed_bytes",1), ("logical_sha256","0"*64)):
            with self.subTest(field=field):
                value = dict(self.envelope, **{field:wrong})
                with self.assertRaises(ContextError):
                    unpack_guard(value)

    def test_checkpoint_resume_and_compatibility(self):
        logical = self.seal["seal_sha256"]
        native = self.seal["native"]["sha256"]
        checkpoint = checkpoint_id("delta", logical, native)
        record = dict(id=checkpoint, contract_version=1, owner=OWNER, state="committed",
                      source_delta_sha256="delta", seal_sha256=logical, native_generation=native,
                      journal_sha256=digest(dict(before=[],after=[],orphan_before=[],orphan_after=[])),
                      before_json="[]",after_json="[]",orphan_before_json="[]",orphan_after_json="[]")

        class OfflineCheckpoint:
            def run(self, query, **params):
                assert params["id"] == checkpoint
                return [{"p": record}]

        for stored in (self.seal, pack_guard(self.seal), self.envelope):
            record["seal_json"] = canonical(stored)
            self.assertEqual(read_checkpoint(OfflineCheckpoint(),checkpoint,include_seal=True)[3],self.seal)
        wrong = dict(self.envelope, chunk_manifest_sha256="0"*64)
        record["seal_json"] = canonical(wrong)
        with self.assertRaises(ContextError):
            read_checkpoint(OfflineCheckpoint(),checkpoint,include_seal=True)
        record.update(state="verified",seal_json=canonical(self.envelope))
        self.assertEqual(read_checkpoint(OfflineCheckpoint(),checkpoint,include_seal=True)[0]["state"],"verified")


if __name__ == "__main__":
    unittest.main()
