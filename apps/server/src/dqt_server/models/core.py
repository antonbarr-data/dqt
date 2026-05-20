from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dqt_server.db.engine import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    engine: Mapped[str] = mapped_column(String, nullable=False)
    host: Mapped[str] = mapped_column(String, nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    db_name: Mapped[str] = mapped_column(String, nullable=False, default="default")
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    password: Mapped[str | None] = mapped_column(String, nullable=True)
    secure: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    table_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    datasets: Mapped[list[Dataset]] = relationship("Dataset", back_populates="source")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    schema_name: Mapped[str] = mapped_column(String, nullable=False, default="default")
    row_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    check_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    source: Mapped[Source] = relationship("Source", back_populates="datasets")
    check_runs: Mapped[list[CheckRun]] = relationship(
        "CheckRun", back_populates="dataset", cascade="all, delete-orphan"
    )
    incidents: Mapped[list[Incident]] = relationship(
        "Incident", back_populates="dataset", cascade="all, delete-orphan"
    )


class CheckRun(Base):
    __tablename__ = "check_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(String, ForeignKey("datasets.id"), nullable=False)
    column_name: Mapped[str | None] = mapped_column(String, nullable=True)
    detector_slug: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String, nullable=True)
    plain_english: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ran_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    dataset: Mapped[Dataset] = relationship("Dataset", back_populates="check_runs")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(String, ForeignKey("datasets.id"), nullable=False)
    column_name: Mapped[str | None] = mapped_column(String, nullable=True)
    detector_slug: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dataset: Mapped[Dataset] = relationship("Dataset", back_populates="incidents")


class ColumnCheck(Base):
    __tablename__ = "column_checks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String, ForeignKey("datasets.id"), nullable=False)
    column_name: Mapped[str] = mapped_column(String, nullable=False)
    detector_slug: Mapped[str] = mapped_column(String, nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    rationale: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"

    fqn: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False, default="ratio")
    dataset: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    owners: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class CheckSchedule(Base):
    __tablename__ = "check_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cadence: Mapped[str] = mapped_column(String, nullable=False)  # hourly|daily|weekly|monthly
    run_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    days_of_week: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    day_of_month: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class LineageEdgeRecord(Base):
    __tablename__ = "lineage_edges"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    upstream_node: Mapped[str] = mapped_column(String, nullable=False)
    upstream_label: Mapped[str] = mapped_column(String, nullable=False, default="")
    downstream_node: Mapped[str] = mapped_column(String, nullable=False)
    downstream_label: Mapped[str] = mapped_column(String, nullable=False, default="")
    kind: Mapped[str] = mapped_column(String, nullable=False, default="column_lineage")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
