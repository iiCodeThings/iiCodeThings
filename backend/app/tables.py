from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class LlmModel(Base):
    __tablename__ = "llm_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    api_key: Mapped[str] = mapped_column(String(512), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    supports_vision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ChatSession(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False, default="新对话")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pinned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    session: Mapped["ChatSession"] = relationship(back_populates="messages")
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    message: Mapped["Message"] = relationship(back_populates="attachments")
