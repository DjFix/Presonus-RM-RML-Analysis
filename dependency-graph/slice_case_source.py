"""AST ranges from existing source, for reading; not reconstructed CPP output."""
import hashlib
import json
import os
import pathlib
import sys

from clang import cindex as ci
from full_source_graph import arguments

ROOT = pathlib.Path(os.environ['DEPENDENCY_GRAPH_ROOT'])
run = pathlib.Path(sys.argv[1])
output = run / 'case-source-excerpts.json'
assert not output.exists()
rows = json.loads((run/'compile_commands.json').read_text())
row = rows[0]
os.chdir(row['directory'])
tu = ci.Index.create().parse(row['file'],args=arguments(row))
assert not [d for d in tu.diagnostics if d.severity >= ci.Diagnostic.Error]
wanted = {'_ZNK8Presonus5Panel16ControlRegistrar5countEv',
          '_ZNK8Presonus5Panel16ControlRegistrar2atEi',
          '_ZNK4Core11ConstVectorIPN8Presonus5Panel12ControlGroupEE5countEv',
          '_ZNK4Core11ConstVectorIPN8Presonus5Panel12ControlGroupEE2atEi',
          '_ZN4Core11ConstVectorIPN8Presonus5Panel12ControlGroupEE8getErrorEv'}
found = {}


def visit(cur):
    if cur.location.file and not str(cur.location.file).startswith(str(ROOT)+'/'):
        return
    for ref in (cur, cur.referenced):
        if not ref or ref.kind.name not in ('FUNCTION_DECL','CXX_METHOD'):
            continue
        name = ref.mangled_name
        if name not in wanted:
            continue
        definition = ref.get_definition()
        if not definition or not definition.location.file:
            continue
        path = pathlib.Path(str(definition.location.file))
        first,last = definition.extent.start.line,definition.extent.end.line
        text = ''.join(path.read_text().splitlines(keepends=True)[first-1:last])
        found[name] = {'path':str(path.relative_to(ROOT)),'first_line':first,'last_line':last,
                       'source_sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),
                       'excerpt':text,'current_source_type':ref.type.spelling}
    for child in cur.get_children():visit(child)


visit(tu.cursor)
assert set(found)==wanted,(wanted-set(found))
output.write_text(json.dumps({'scope':'Existing source excerpts; current port types, not original return declarations',
                             'functions':found},indent=2)+'\n')
print(json.dumps({'functions':len(found),'source_lines':sum(x['last_line']-x['first_line']+1 for x in found.values())}))
