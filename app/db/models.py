import uuid
from datetime import datetime

from sqlalchemy import (
    BIGINT,
    JSON,
    UUID,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"), nullable=False)

    oauths: Mapped[list["UserOAuth"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    songs: Mapped[list["Song"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    playlists: Mapped[list["Playlist"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserOAuth(Base):
    __tablename__ = "user_oauths"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_uid: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="oauths")

    __table_args__ = (
        UniqueConstraint("provider", "provider_uid", name="uq_user_oauth_provider_uid"),
        Index("idx_user_oauths_user", "user_id"),
    )


class Song(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "songs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    extracted_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_used: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    lyrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_instrumental: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, server_default=text("NULL"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))
    music_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    likes_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="songs")
    playlist_items: Mapped[list["PlaylistItem"]] = relationship(back_populates="song", cascade="all, delete-orphan")
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="song", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("source_type IN ('image', 'voice', 'prompt')", name="ck_songs_source_type"),
        CheckConstraint("status IN ('pending', 'processing', 'done', 'failed')", name="ck_songs_status"),
        Index("idx_songs_user", "user_id"),
        Index("idx_songs_status", "status"),
        Index(
            "idx_songs_plaza",
            "is_public",
            text("published_at DESC"),
            postgresql_where=text("is_public = TRUE AND deleted_at IS NULL"),
        ),
        Index("idx_songs_active", "user_id", postgresql_where=text("deleted_at IS NULL")),
    )


class Playlist(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, server_default=text("NULL"))
    cover_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="playlists")
    items: Mapped[list["PlaylistItem"]] = relationship(back_populates="playlist", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_playlists_user", "user_id"),
        Index(
            "idx_one_default_playlist",
            "user_id",
            unique=True,
            postgresql_where=text("is_default = TRUE AND deleted_at IS NULL"),
        ),
    )


class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    playlist_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("playlists.id", ondelete="CASCADE"))
    song_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("songs.id", ondelete="CASCADE"))
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    playlist: Mapped["Playlist"] = relationship(back_populates="items")
    song: Mapped["Song"] = relationship(back_populates="playlist_items")

    __table_args__ = (
        UniqueConstraint("playlist_id", "song_id", name="uq_playlist_song"),
        Index("idx_playlist_items_playlist", "playlist_id"),
        Index("idx_playlist_items_song", "song_id"),
    )


class Favorite(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    song_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("songs.id", ondelete="CASCADE"))

    user: Mapped["User"] = relationship(back_populates="favorites")
    song: Mapped["Song"] = relationship(back_populates="favorites")

    __table_args__ = (
        Index("idx_favorites_user", "user_id"),
        Index("idx_favorites_song", "song_id"),
        Index(
            "idx_favorites_user_song_active",
            "user_id",
            "song_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
