"""SQLAlchemy mappings and guarded sessions; no implicit schema creation/migration."""
import pathlib
import sqlite3
from sqlalchemy import Column, Integer, Text, Table, ForeignKey, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import NullPool

class Base(DeclarativeBase):
    pass

# These legacy singleton-like tables have no physical key. Keep them Core-only;
# assigning an invented mapper identity could hide duplicate source rows.
provenance = Table('provenance',Base.metadata,Column('json',Text,nullable=False))
schema_info = Table('schema_info',Base.metadata,Column('version',Integer,nullable=False),Column('complete',Integer,nullable=False))
workflow_info = Table('workflow_info',Base.metadata,Column('version',Integer,nullable=False),Column('baseline_sha256',Text,nullable=False),Column('baseline_path',Text,nullable=False))

class Registry(Base):
    __tablename__='registries'
    status=Column(Text,primary_key=True)
    metadata_json=Column('metadata',Text,nullable=False)
class SourceSet(Base):
    __tablename__='source_sets'
    id=Column(Text,primary_key=True)
class SourceVersion(Base):
    __tablename__='source_versions'
    id=Column(Integer,primary_key=True)
    path=Column(Text,nullable=False)
    digest_json=Column(Text,nullable=False)
    __table_args__=(UniqueConstraint('path','digest_json'),)
class SourceMember(Base):
    __tablename__='source_members'
    set_id=Column(Text,ForeignKey('source_sets.id'),primary_key=True)
    ordinal=Column(Integer,primary_key=True)
    version_id=Column(Integer,ForeignKey('source_versions.id'))
class Record(Base):
    __tablename__='records'
    id=Column(Integer,primary_key=True)
    status=Column(Text,ForeignKey('registries.status'))
    ordinal=Column(Integer,nullable=False)
    elf=Column(Text,nullable=False)
    mangled=Column(Text,nullable=False)
    proof=Column(Text)
    metadata_json=Column('metadata',Text,nullable=False)
    __table_args__=(UniqueConstraint('elf','mangled'),UniqueConstraint('status','ordinal'))
class RecordSet(Base):
    __tablename__='record_sets'
    record_id=Column(Integer,ForeignKey('records.id'),primary_key=True)
    field=Column(Text,primary_key=True)
    set_id=Column(Text,ForeignKey('source_sets.id'))
class WorkState(Base):
    __tablename__='work_state'
    record_id=Column(Integer,ForeignKey('records.id'),primary_key=True)
    revision=Column(Integer,nullable=False,default=0)
    assignment=Column(Text)
    blocker=Column(Text)
class Stage(Base):
    __tablename__='stages'
    record_id=Column(Integer,ForeignKey('records.id'),primary_key=True)
    stage=Column(Text,primary_key=True)
    proof=Column(Text,nullable=False)
    proof_sha256=Column(Text,nullable=False)
    domain=Column(Text,nullable=False)
class Request(Base):
    __tablename__='requests'
    request_id=Column(Text,primary_key=True)
    digest=Column(Text,nullable=False)
    result=Column(Text,nullable=False)
class EvidenceCheck(Base):
    __tablename__='evidence_checks'
    request_id=Column(Text,ForeignKey('requests.request_id'),primary_key=True)
    path=Column(Text,primary_key=True)
    sha256=Column(Text,nullable=False)
    fingerprint=Column(Text,nullable=False)
class Journal(Base):
    __tablename__='journal'
    sequence=Column(Integer,primary_key=True)
    request_id=Column(Text,ForeignKey('requests.request_id'),nullable=False)
    record_id=Column(Integer,ForeignKey('records.id'),nullable=False)
    actor=Column(Text,nullable=False)
    timestamp=Column(Text,nullable=False)
    reason=Column(Text,nullable=False)
    previous_revision=Column(Integer,nullable=False)
    new_revision=Column(Integer,nullable=False)
    previous_state=Column(Text,nullable=False)
    new_state=Column(Text,nullable=False)
    bindings=Column(Text,nullable=False)

class Unit:
    """One SQLAlchemy-owned transaction shared with efficient sqlite cursors.

    Session flushes actual ORM writes into the same BEGIN IMMEDIATE transaction.
    The externally owned Connection alone commits/rolls back. Raw SQL paths must
    not independently commit. Read units use URI mode=ro and deferred BEGIN.
    """
    def __init__(self,db,write=False):
        path=pathlib.Path(db).resolve()
        def creator():
            raw=sqlite3.connect(path.as_uri()+('?mode=rw' if write else '?mode=ro'),uri=True,isolation_level=None)
            raw.row_factory=sqlite3.Row
            raw.execute('PRAGMA foreign_keys=ON')
            return raw
        self.engine=create_engine('sqlite+pysqlite://',creator=creator,poolclass=NullPool)
        self.connection=self.engine.connect()
        self.connection.exec_driver_sql('BEGIN IMMEDIATE' if write else 'BEGIN')
        self.raw=self.connection.connection.driver_connection
        self.session=Session(bind=self.connection,join_transaction_mode='rollback_only',expire_on_commit=False)
    def commit(self):
        self.session.flush()
        self.connection.commit()
    def rollback(self):
        self.session.rollback()
        self.connection.rollback()
    def close(self):
        self.session.close()
        self.connection.close()
        self.engine.dispose()
