import json
import sqlite3
import unittest

from context_runtime import ContextError
from native_graph import key,byte_address
from native_context import require_nonempty, select, target_key


class NativeContextTests(unittest.TestCase):
    def test_thumb_function_bit_never_rounds_down_odd_data_address(self):
        self.assertEqual(byte_address(4097,'STT_FUNC'),4096)
        self.assertEqual(byte_address(4097,'STT_OBJECT'),4097)
        self.assertEqual(byte_address(4097,'STT_NOTYPE'),4097)

    def original(self,elf='a'*64,address=4096):
        return {'elf':elf,'mangled':'_Z3foov','address':address,'size':4,'section_json':'12'}

    def test_identity_separates_elf_and_ranges(self):
        self.assertNotEqual(target_key(self.original()),target_key(self.original('b'*64)))
        self.assertNotEqual(target_key(self.original()),target_key(self.original(address=4100)))
        self.assertNotEqual(key('a'*64,'f',1,4,12),key('a'*64,'f',1,4,13))

    def test_empty_research_and_metadata_only_packets_rejected(self):
        original=self.original(); ident=target_key(original)
        packet={'mode':'research','originals':[{'original':original}],'native_context':{'bodies':{ident:{}}}}
        with self.assertRaises(ContextError):require_nonempty(packet)
        packet['native_context']['bodies'][ident]={'instructions':[{'mnemonic':'bx'}],'bytes_sha256':'a'*64,'size':4,'file_offset':128}
        require_nonempty(packet)
        packet['originals'].append({'original':self.original('b'*64)})
        with self.assertRaises(ContextError):require_nonempty(packet)

    def test_correspondences_not_treated_as_calls_and_cross_elf_calls_block(self):
        c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
        c.executescript('''CREATE TABLE nodes(id,kind,label,elf,metadata);
          CREATE TABLE edges(src,dst,kind,site,metadata);
          CREATE TABLE symbol_resolution(symbol_id,strategy,provider_id,binding_status,evidence_json);''')
        c.executemany('INSERT INTO nodes VALUES(?,?,?,?,?)',[('a','NativeFunction','f','elf-a','{}'),('b','NativeFunction','f','elf-b','{}')])
        c.execute('INSERT INTO edges VALUES(?,?,?,?,?)',('a','b','ELF_NAME_CORRESPONDENCE',-1,'{}'))
        nodes,edges=select(c,['a']);self.assertEqual(set(nodes),{'a'});self.assertEqual(edges,[])
        c.execute('INSERT INTO edges VALUES(?,?,?,?,?)',('a','b','ELF_CALLS',4096,'{}'))
        with self.assertRaises(ContextError):select(c,['a'])
        c.close()
