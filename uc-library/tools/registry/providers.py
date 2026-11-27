"""Read imported exact provider identities through the registry ORM."""
import hashlib
from pathlib import Path
import orm
import schema
from adapter import resolve_db

LIBRARY = Path(__file__).resolve().parents[2]


def definitions(manifest_sha256, database=None):
    db = resolve_db(LIBRARY, database)
    unit = orm.Unit(db)
    try:
        schema.require_current(unit.raw)
        source = unit.session.get(orm.ProviderImport, manifest_sha256)
        if source is None or hashlib.sha256(source.document.encode()).hexdigest() != manifest_sha256:
            raise ValueError('Required provider import is absent or its provenance is corrupt')
        rows = unit.session.query(orm.ProviderDefinition).filter_by(import_sha256=manifest_sha256).all()
        if not rows:
            raise ValueError('Empty provider import')
        return [dict(elf_sha256=r.elf,original_mangled=r.mangled,
                     original_address=r.address,original_size=r.size,
                     section_index=r.section,vendor=r.library) for r in rows]
    finally:
        unit.close()


def reference(manifest_sha256, database=None):
    rows = definitions(manifest_sha256, database)
    return dict(kind='sqlite_provider_import', database=str(resolve_db(LIBRARY,database)),
                table='provider_definitions', import_sha256=manifest_sha256,
                definitions=len(rows), interpretation='Exact original provider ownership; not readiness')
