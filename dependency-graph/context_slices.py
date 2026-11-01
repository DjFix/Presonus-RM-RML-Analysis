"""AST-backed source ranges for an arbitrary selected packet, without new CPP."""
import hashlib
import json
import os
import pathlib
import sys

from clang import cindex as ci
from full_source_graph import arguments

ROOT=pathlib.Path(os.environ['DEPENDENCY_GRAPH_ROOT'])
packet_dir=pathlib.Path(sys.argv[1])
packet=json.loads((packet_dir/'context.json').read_text())
dest=packet_dir/'source-slices.json'
assert not dest.exists()
wanted={v['metadata'].get('mangled'):key for key,v in packet['nodes'].items()
        if key in packet['call_functions'] and v['metadata'].get('mangled')}
sources=set(packet.get('slice_translation_units',[]))
for key in packet['roots']:
    meta=packet['nodes'][key]['metadata']
    path=meta.get('definition_location',{}).get('path') or meta.get('path')
    if path:sources.add(path)
for key in packet['call_functions']:
    meta=packet['nodes'].get(key,{}).get('metadata',{})
    path=meta.get('definition_location',{}).get('path')
    if path and path.endswith(('.cpp','.cc','.cxx','.c')):sources.add(path)
rows=[]
for path in ('temp/core-upstream/root-integration-01/compile_commands.json',
             'temp/core-upstream/root-integration-01/upstream-core/build/compile_commands.json'):
    rows+=json.loads((ROOT/path).read_text())
found={};diagnostics=[]


def visit(cur):
    if cur.location.file and not str(cur.location.file).startswith(str(ROOT)+'/'):return
    for ref in (cur,cur.referenced):
        if not ref or ref.kind.name not in ('FUNCTION_DECL','CXX_METHOD','CONSTRUCTOR','DESTRUCTOR','CONVERSION_FUNCTION'):continue
        name=ref.mangled_name
        if name not in wanted:continue
        definition=ref.get_definition()
        if not definition or not definition.location.file:continue
        path=pathlib.Path(str(definition.location.file))
        if not path.is_relative_to(ROOT):continue
        first,last=definition.extent.start.line,definition.extent.end.line
        text=''.join(path.read_text().splitlines(keepends=True)[first-1:last])
        found[wanted[name]]={'path':str(path.relative_to(ROOT)),'first_line':first,'last_line':last,
                            'source_sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),
                            'excerpt':text,'mangled':name,'current_source_type':ref.type.spelling}
    for child in cur.get_children():visit(child)


for row in rows:
    if str(pathlib.Path(row['file']).relative_to(ROOT)) not in sources:continue
    os.chdir(row['directory'])
    tu=ci.Index.create().parse(row['file'],args=arguments(row))
    errors=[str(d) for d in tu.diagnostics if d.severity>=ci.Diagnostic.Error]
    if errors:
        diagnostics.append({'source':row['file'],'errors':errors});continue
    visit(tu.cursor)
missing=sorted(set(packet['call_functions'])-set(found))
result={'functions':found,'missing_bodies':missing,'diagnostics':diagnostics,
        'source_lines':sum(v['last_line']-v['first_line']+1 for v in found.values()),
        'scope':'Existing source excerpts; original return declarations/layout remain independently unresolved'}
dest.write_text(json.dumps(result,indent=2)+'\n')
lines=['# Selected existing source bodies','',result['scope'],'']
for key,item in sorted(found.items()):
    lines+=['## '+item['mangled'],'',f"`{item['path']}:{item['first_line']}`",'','```cpp',item['excerpt'].rstrip(),'```','']
if missing:lines+=['## Unavailable bodies','',*['- `'+x+'`' for x in missing]]
(packet_dir/'SOURCE_SLICES.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'functions':len(found),'source_lines':result['source_lines'],'missing_bodies':len(missing)}))
