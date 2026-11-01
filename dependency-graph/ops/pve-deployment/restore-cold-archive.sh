#!/bin/bash
# Execute inside CT125 only; Root approved this exact cold archive/hash.
set -euo pipefail
archive=/home/rs/memgraph-migration/memgraph-source-1aff112c942a.tgz
expected=1aff112c942ac3052fe1c9c0799f309a7c778b166a44efdaab95aaef9dd6b934
printf '%s  %s\n' "$expected" "$archive" | sha256sum -c -
# Validate tar names and links before extraction into an empty staging directory.
python3 - "$archive" <<'PY'
import sys,tarfile,pathlib,posixpath
with tarfile.open(sys.argv[1]) as tf:
 for m in tf:
  p=pathlib.PurePosixPath(m.name)
  if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0]!='data':
   raise SystemExit('unexpected archive path: '+m.name)
  if m.issym() or m.islnk():
   target = posixpath.normpath(posixpath.join(posixpath.dirname(m.name),m.linkname) if m.issym() else m.linkname)
   if target != 'data' and not target.startswith('data/'):
    raise SystemExit('link escapes data directory: '+m.name+' -> '+m.linkname)
  elif not (m.isfile() or m.isdir()):
   raise SystemExit('unsupported archive member: '+m.name)
print('Archive paths/type checks passed')
PY
systemctl stop memgraph-compose
stamp=$(date -u +%Y%m%dT%H%M%SZ)
preserved=/srv/memgraph/data-empty-before-migration-$stamp
[[ ! -e "$preserved" ]]
mv /srv/memgraph/data "$preserved"
mkdir -m 0755 /srv/memgraph/restore-staging-$stamp
tar --numeric-owner -xzf "$archive" -C /srv/memgraph/restore-staging-$stamp
mv /srv/memgraph/restore-staging-$stamp/data /srv/memgraph/data
chown -R 101:103 /srv/memgraph/data
printf 'preserved_empty=%s\nrestored_archive=%s\n' "$preserved" "$archive"
du -sh /srv/memgraph/data "$preserved"
ls -ln /srv/memgraph/data/snapshots
systemctl start memgraph-compose
docker compose -f /opt/memgraph/compose.yaml ps
