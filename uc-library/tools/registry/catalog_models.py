"""SQLAlchemy mappings preserving the original additive catalog schema."""
from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Integer, Table, Text
from orm import Base

# Original singleton table has no physical primary key; retain it as a Core
# Table, rather than inventing a key during adoption.
catalog_info = Table('catalog_info', Base.metadata,
                     Column('version', Integer, nullable=False),
                     Column('imported_at', Text, nullable=False))

class CatalogInput(Base):
    __tablename__ = 'catalog_inputs'
    path = Column(Text, primary_key=True)
    sha256 = Column(Text, nullable=False)
    metadata_json = Column('metadata', Text, nullable=False)

class CatalogSymbol(Base):
    __tablename__ = 'catalog_symbols'
    anchor = Column(Text, primary_key=True)
    elf = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    firmware = Column(Text, nullable=False)
    mangled = Column(Text, nullable=False)
    demangled = Column(Text, nullable=False)
    address = Column(Integer, nullable=False)
    size = Column(Integer, nullable=False)
    section_json = Column(Text, nullable=False)
    kind = Column(Text, nullable=False)
    binding = Column(Text, nullable=False)
    policy = Column(Text, nullable=False)
    __table_args__ = (Index('catalog_name', 'elf', 'mangled'),
                      Index('catalog_range', 'elf', 'section_json', 'address', 'size'))

class CatalogRow(Base):
    __tablename__ = 'catalog_rows'
    input_path = Column(Text, ForeignKey('catalog_inputs.path'), primary_key=True)
    ordinal = Column(Integer, primary_key=True)
    anchor = Column(Text, ForeignKey('catalog_symbols.anchor'))
    raw = Column(Text, nullable=False)
    __table_args__ = (Index('catalog_row_anchor', 'anchor'),)

class CatalogTask(Base):
    __tablename__ = 'catalog_tasks'
    anchor = Column(Text, ForeignKey('catalog_symbols.anchor'), primary_key=True)
    revision = Column(Integer, nullable=False)
    state = Column(Text, nullable=False)
    owner = Column(Text)
    batch = Column(Text)
    notes = Column(Text, nullable=False)
    __table_args__ = (CheckConstraint("state IN ('todo','assigned','in_progress','blocked','done')"),)

class CatalogRequest(Base):
    __tablename__ = 'catalog_requests'
    request_id = Column(Text, primary_key=True)
    digest = Column(Text, nullable=False)
    result = Column(Text, nullable=False)

class CatalogJournal(Base):
    __tablename__ = 'catalog_journal'
    sequence = Column(Integer, primary_key=True)
    request_id = Column(Text, ForeignKey('catalog_requests.request_id'), nullable=False)
    anchor = Column(Text, ForeignKey('catalog_symbols.anchor'), nullable=False)
    actor = Column(Text, nullable=False)
    timestamp = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    previous_revision = Column(Integer, nullable=False)
    new_revision = Column(Integer, nullable=False)
    previous_state = Column(Text, nullable=False)
    new_state = Column(Text, nullable=False)

TABLES = (catalog_info, CatalogInput.__table__, CatalogSymbol.__table__,
          CatalogRow.__table__, CatalogTask.__table__, CatalogRequest.__table__,
          CatalogJournal.__table__)
