"""Validate pinned upstream source availability without granting binary readiness."""
import hashlib
import json
from pathlib import Path


def load_source_providers(library, policy):
    relative=policy.get('source_exclusions_fragment')
    if not relative:
        return {},{}
    path=(library/relative).resolve()
    assert path.is_relative_to(library)
    raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==policy['source_exclusions_sha256'],'source-provider fragment changed'
    data=json.loads(raw)
    assert data['upstream_commit']==policy['selected_commit']
    repository=next(parent for parent in (library,*library.parents) if (parent/policy['submodule']/'core').is_dir())
    upstream=(repository/policy['submodule']).resolve()
    cache={}
    source_list_raw=(library/policy['source_files_manifest']).read_bytes()
    assert hashlib.sha256(source_list_raw).hexdigest()==policy['source_files_manifest_sha256']
    source_list=json.loads(source_list_raw)
    assert source_list['commit']==policy['selected_commit']
    for item in source_list['files']:
        source=(upstream/item['path']).resolve()
        assert source.is_relative_to(upstream) and source.is_file()
        contents=source.read_bytes()
        assert len(contents)==item['size'] and hashlib.sha256(contents).hexdigest()==item['sha256'],'pinned upstream file changed'
        assert hashlib.sha1(b'blob '+str(len(contents)).encode()+b'\0'+contents).hexdigest()==item['git_blob_sha1'],'upstream Git blob identity mismatch'
        cache[source]=contents
    def verify_node(node):
        source=(upstream/node['path']).resolve()
        assert source in cache,'source API outside the pinned source manifest'
        contents=cache[source]
        if node.get('source_sha256'):
            assert hashlib.sha256(contents).hexdigest()==node['source_sha256'],'upstream file changed'
        bodies=0
        if node.get('definition_extent_sha256'):
            start,end=node['definition_extent_start'],node['definition_extent_end']
            assert 0<=start<end<=len(contents),'invalid source definition extent'
            assert hashlib.sha256(contents[start:end]).hexdigest()==node['definition_extent_sha256'],'upstream body extent changed'
            bodies+=1
        return bodies+sum(verify_node(child) for child in node.get('generic_definitions',[]))
    providers={}
    for entry in data['functions']:
        assert entry['upstream_commit']==policy['selected_commit']
        assert entry['skip_manual_reconstruction'] is True
        assert entry.get('original_function_verified') is False and entry.get('hardware_verified') is False
        nodes=entry['upstream']
        assert nodes,'source API needs actual declaration provenance'
        bodies=0
        for node in nodes:
            bodies+=verify_node(node)
        assert not entry['source_body_available'] or bodies,'body availability lacks a verified source extent'
        key=(entry['original_elf_sha256'],entry['mangled'],entry['original_address'],entry['original_size'])
        assert key not in providers,'duplicate original source-provider mapping'
        providers[key]=entry
    return providers,dict(fragment=str(relative),sha256=policy['source_exclusions_sha256'],
                          upstream_commit=policy['selected_commit'],records=len(providers),
                          source_files_checked=len(cache),binary_behavior_verified=False)
