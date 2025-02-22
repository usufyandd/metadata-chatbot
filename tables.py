from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    DateTime,
    Boolean,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    DateTime,
    Boolean,
    Text,
    UUID,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    password_salt = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    folders = relationship("Folder", back_populates="owner")
    documents = relationship("Document", back_populates="owner")
    chat_sessions = relationship("ChatSession", back_populates="user")


class Folder(Base):
    __tablename__ = "folders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    parent_id = Column(
        UUID(as_uuid=True), ForeignKey("folders.id"), nullable=True
    )
    owner_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )  # Folder Owner
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Metadata
    size = Column(Integer, default=0)  # Total size in bytes
    file_count = Column(Integer, default=0)  # Number of files in the folder
    folder_count = Column(Integer, default=0)  # Number of subfolders
    access_type = Column(String, default="private")  # "private" or "public"
    tags = Column(Text, nullable=True)  # JSON or comma-separated tags

    # Relationships
    parent = relationship(
        "Folder", remote_side=[id], back_populates="children"
    )
    children = relationship(
        "Folder", remote_side=[parent_id], back_populates="parent"
    )

    owner = relationship("User", back_populates="folders")
    
    documents = relationship(
        "Document", back_populates="folder", cascade="all, delete-orphan"
    )

    files = relationship(
        "Files", back_populates="folder", cascade="all, delete-orphan"
    )


class Files(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True, unique=True)
    name = Column(String, nullable=False, doc="Name of the uploaded file.")
    path = Column(String, nullable=False, doc="File storage path on the server.")
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id"), nullable=False, doc="Reference to the folder containing this file.")
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, doc="User who uploaded the file.")

    folder = relationship("Folder", back_populates="files", doc="Relationship linking the file to its folder.")

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folder_id = Column(
        UUID(as_uuid=True), ForeignKey("folders.id"), nullable=False
    )
    owner_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    filename = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)  # File path (local/S3)
    file_type = Column(String, nullable=False)  # "pdf", "docx", etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Metadata
    description = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)  # File size in bytes
    checksum = Column(String, nullable=True)  # MD5/SHA256 hash for integrity
    version = Column(String, nullable=True, default="1.0")
    last_accessed_at = Column(DateTime, nullable=True)
    tags = Column(Text, nullable=True)  # JSON or comma-separated tags

    # Relationships
    folder = relationship("Folder", back_populates="documents")
    owner = relationship("User", back_populates="documents")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False
    )
    sender = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    session = relationship("ChatSession", back_populates="messages")
