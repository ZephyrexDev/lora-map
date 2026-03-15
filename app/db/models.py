"""SQLAlchemy ORM models for the LoRa Coverage Planner.

These models define the current schema state used for application queries.
Schema evolution is handled by the migration system in ``schema.py``.
"""

from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Tower(Base):
    __tablename__ = "towers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[str | None] = mapped_column(String)
    params: Mapped[dict] = mapped_column(JSON, nullable=False)
    geotiff: Mapped[bytes | None] = mapped_column(LargeBinary)
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("(datetime('now'))"))
    updated_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("(datetime('now'))"))


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tower_id: Mapped[str] = mapped_column(ForeignKey("towers.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'processing'"))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("(datetime('now'))"))


class TowerPath(Base):
    __tablename__ = "tower_paths"
    __table_args__ = (
        UniqueConstraint("tower_a_id", "tower_b_id"),
        Index("idx_tower_paths_tower_a", "tower_a_id"),
        Index("idx_tower_paths_tower_b", "tower_b_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tower_a_id: Mapped[str] = mapped_column(ForeignKey("towers.id", ondelete="CASCADE"), nullable=False)
    tower_b_id: Mapped[str] = mapped_column(ForeignKey("towers.id", ondelete="CASCADE"), nullable=False)
    path_loss_db: Mapped[float | None] = mapped_column(Float)
    has_los: Mapped[int | None] = mapped_column(Integer)
    distance_km: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'pending'"))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("(datetime('now'))"))

    tower_a: Mapped[Tower] = relationship(foreign_keys=[tower_a_id])
    tower_b: Mapped[Tower] = relationship(foreign_keys=[tower_b_id])


class Simulation(Base):
    __tablename__ = "simulations"
    __table_args__ = (
        UniqueConstraint("tower_id", "client_hardware", "client_antenna", "terrain_model"),
        Index("idx_simulations_tower_id", "tower_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tower_id: Mapped[str] = mapped_column(ForeignKey("towers.id", ondelete="CASCADE"), nullable=False)
    client_hardware: Mapped[str] = mapped_column(String, nullable=False)
    client_antenna: Mapped[str] = mapped_column(String, nullable=False)
    terrain_model: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'bare_earth'"))
    status: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'pending'"))
    geotiff: Mapped[bytes | None] = mapped_column(LargeBinary)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("(datetime('now'))"))


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("(datetime('now'))"))
