import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, BigInteger
from sqlalchemy.orm import relationship

from .db import Base


class File(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    original_name = Column(String, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    chunks = relationship("Chunk", back_populates="file", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True)  # SHA-256 hash string
    file_id = Column(String, ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    index = Column(Integer, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)

    file = relationship("File", back_populates="chunks")
    locations = relationship("ChunkLocation", back_populates="chunk", cascade="all, delete-orphan")


class StorageNode(Base):
    __tablename__ = "storage_nodes"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    base_url = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    locations = relationship("ChunkLocation", back_populates="node")


class ChunkLocation(Base):
    __tablename__ = "chunk_locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(String, ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String, ForeignKey("storage_nodes.id", ondelete="CASCADE"), nullable=False)

    chunk = relationship("Chunk", back_populates="locations")
    node = relationship("StorageNode", back_populates="locations")

