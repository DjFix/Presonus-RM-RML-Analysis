"""Read-only immutable reference guard: provenance hashes and saved fingerprints.

Payload hashes were checked at capture. Runtime never rehashes AST/GCC gigabytes.
"""
import json,os,pathlib
from context_runtime import ContextError,sha,fingerprint,snapshot_path,snapshot_aliases

def require(v,msg):
    if not v:raise ContextError(msg)
def verify_references(root,receipt,manifest,copy_root):
    nodes={};resolved={};compiler_cache={}
    def node(batch,expected=None,known=None):
        if batch in nodes:
            require(fingerprint(batch/'SNAPSHOT.json')==nodes[batch][4] and (expected is None or expected==nodes[batch][3]),'Reference lineage manifest changed');return nodes[batch]
        require(batch.resolve()==batch and batch.is_relative_to(root/'temp/recovery-work'),'Unsafe reference lineage batch');path=batch/'SNAPSHOT.json';require(path.resolve()==path and path.is_file() and path.stat().st_nlink==1,'Unsafe reference lineage receipt');digest=sha(path)
        if expected:require(digest==expected,'Reference lineage manifest hash changed')
        if batch not in nodes:
            d=known if known is not None else json.loads(path.read_text());require(d.get('version')==1,'Unsupported reference lineage version');images=batch/'IMAGES.json';require(images.resolve()==images and images.is_file() and json.loads(images.read_text())==d['images'],'Reference image provenance changed');files=dict(d['files']);files.update({'external/'+p.lstrip('/'):v for p,v in d.get('external',{}).items()});snapshot_aliases(files);aliases={str(snapshot_path(pathlib.Path('/__snapshot_lexical_root__'),p)):p for p in files};nodes[batch]=(d,files,aliases,digest,fingerprint(path))
        require(nodes[batch][3]==digest,'Reference lineage changed while loading');return nodes[batch]
    def leaf(batch,path,stack):
        key=(batch,path)
        if key in resolved:return resolved[key]
        require(key not in stack,'Cyclic snapshot reference lineage');d,files,aliases,_,_=node(batch);require(path in files,'Reference not bound by manifest');digest=files[path];reference=d.get('references',{}).get(path);candidate=snapshot_path(batch/'snapshot',path,allow_leaf_symlink=bool(reference))
        if reference:
            value=reference.get('fingerprint');require(isinstance(value,list) and len(value)==5 and all(isinstance(x,int) and not isinstance(x,bool) for x in value),'Invalid saved reference fingerprint')
            if reference.get('kind')=='compiler_observation':
                from snapshot_observations import validate_record
                target=validate_record(root,path,digest,reference['provenance'],compiler_cache,payload_hash=False)
            else:
                reuse=d.get('reuse');require(isinstance(reuse,dict),'Missing reference origin manifest');relative=pathlib.Path(reuse['batch']);require(not relative.is_absolute() and '..' not in relative.parts,'Unsafe reference origin path');prior=root/relative;require(prior!=batch,'Cyclic reference origin');_,oldfiles,oldaliases,_,_=node(prior,reuse['manifest_sha256']);alias=str(snapshot_path(pathlib.Path('/__snapshot_lexical_root__'),path));require(alias in oldaliases and oldfiles[oldaliases[alias]]==digest,'Reference digest differs from recorded origin');target=leaf(prior,oldaliases[alias],stack|{key})
            require(str(target)==reference.get('target') and candidate.parent.resolve()==candidate.parent and candidate.is_symlink() and os.readlink(candidate)==str(target),'Unsafe direct reference link')
            require(target.resolve()==target and target.is_file() and target.stat().st_nlink==1 and fingerprint(target)==value and os.path.samefile(candidate,target),'Changed/nonphysical snapshot leaf')
        else:
            target=candidate;require(target.resolve()==target and target.is_file() and target.stat().st_nlink==1,'Unsafe direct snapshot copy')
        resolved[key]=target;return target
    node(receipt.parent,known=manifest)
    for path in manifest.get('references',{}):leaf(receipt.parent,path,set())
    for batch,(_,_,_,digest,stamp) in nodes.items():require(fingerprint(batch/'SNAPSHOT.json')==stamp and sha(batch/'SNAPSHOT.json')==digest,'Reference manifest changed during guard')
    return {'reference_count':len(manifest.get('references',{})),'manifest_count':len(nodes),'payload_hashes_recomputed':0}

def immutable_mounts(root,output,snapshot):
    """Keep direct compiler leaves and pinned report/receipt metadata visible RO."""
    prefix='temp/recovery-work/dependency-graph/refresh';origins=set();receipts=set()
    for record in snapshot.get('references',{}).values():
        if record.get('kind')=='compiler_observation':
            origins.add(pathlib.Path(record['target']).parents[2]);receipts.add((root/record['provenance']['report']['path']).parent)
    # Generic reused leaves can terminate in an ancestor's compiler reference.
    # Preserve its canonical metadata through selective child overlays instead
    # of hiding reports absent from the new snapshot's ordinary files.
    manifests = [snapshot]
    seen = {output.resolve()}
    provenance = {}
    inherited_origins = set()
    reference_targets = set()
    while manifests:
        current = manifests.pop()
        for record in current.get('references', {}).values():
            reference_targets.add(pathlib.Path(record['target']))
            if record.get('kind') != 'compiler_observation':
                continue
            target = pathlib.Path(record['target'])
            origin = target.parents[2]
            require(origin.parent == root / prefix and origin.name.isdecimal()
                    and origin.resolve() == origin and origin.is_dir(),
                    'Unsafe inherited compiler capture origin')
            inherited_origins.add(origin)
            for field in ('state', 'report', 'receipt'):
                reference = record['provenance'][field]
                relative = pathlib.Path(reference['path'])
                require(not relative.is_absolute() and '..' not in relative.parts,
                        'Unsafe compiler metadata mount path')
                target = root / relative
                require(target.resolve() == target and target.is_file() and target.stat().st_nlink == 1,
                        'Unsafe compiler metadata mount leaf')
                expected = reference['sha256']
                require(target not in provenance or provenance[target] == expected,
                        'Conflicting compiler metadata mount hashes')
                provenance[target] = expected
        reuse = current.get('reuse')
        if reuse:
            relative = pathlib.Path(reuse['batch'])
            require(not relative.is_absolute() and '..' not in relative.parts,
                    'Unsafe compiler metadata lineage path')
            batch = root / relative
            require(batch.resolve() == batch and batch.is_relative_to(root / 'temp/recovery-work')
                    and batch not in seen, 'Unsafe/cyclic compiler metadata lineage')
            seen.add(batch)
            manifest = batch / 'SNAPSHOT.json'
            require(manifest.resolve() == manifest and manifest.is_file() and manifest.stat().st_nlink == 1,
                    'Unsafe compiler metadata lineage manifest')
            stamp = fingerprint(manifest)
            require(sha(manifest) == reuse['manifest_sha256'], 'Compiler metadata lineage hash mismatch')
            value = json.loads(manifest.read_text())
            require(value.get('version') == 1 and fingerprint(manifest) == stamp,
                    'Compiler metadata lineage changed')
            manifests.append(value)
    origins.update(inherited_origins)
    receipts.update(target.parent for target in provenance if target.parent.parent == root / prefix)
    for target, expected in sorted(provenance.items()):
        stamp = fingerprint(target)
        require(sha(target) == expected and fingerprint(target) == stamp,
                'Compiler metadata mount hash mismatch')
    result=[]
    for relative in snapshot['mounts']:
        if relative!=prefix or not origins:
            result.append((output/'snapshot'/relative,root/relative));continue
        for child in sorted((output/'snapshot'/relative).iterdir()):
            destination=root/relative/child.name
            if destination in origins:continue
            if destination in receipts:
                for entry in sorted(child.iterdir()):result.append((entry,destination/entry.name))
            else:result.append((child,destination))
    result.extend((origin,origin) for origin in sorted(origins))
    verified_mounts = []
    preserved_aliases = {}
    for source, destination in result:
        require(source.exists() and destination.exists(),
                'Read-only evidence mount path missing: ' + str(source) + ' -> ' + str(destination))
        resolved = destination.resolve()
        if destination.is_symlink() and resolved in reference_targets:
            # Docker follows a destination symlink. Overlaying a fresh copy at
            # this alias would replace the verified ancestor inode for every
            # reference using it. Keep its physical target visible read-only
            # through the runner's repository mount.
            relative = str(destination.relative_to(root))
            expected = snapshot.get('files', {}).get(relative)
            require(resolved.is_relative_to(root) and resolved.is_file()
                    and resolved.stat().st_nlink == 1 and expected,
                    'Unsafe immutable reference mount alias: ' + relative)
            stamp = fingerprint(resolved)
            require(sha(resolved) == expected and fingerprint(resolved) == stamp,
                    'Immutable reference mount alias changed: ' + relative)
            preserved_aliases[relative] = resolved
            continue
        verified_mounts.append((source, destination))
    # Only emitted mounts can shadow a physical leaf. Several historical
    # destinations can independently resolve to the same verified leaf.
    overlays = [destination.resolve() for source, destination in verified_mounts
                if source != destination]
    for relative, target in preserved_aliases.items():
        require(not any(target.is_relative_to(destination) for destination in overlays),
                'Immutable reference mount target shadowed: ' + relative)
    return verified_mounts
