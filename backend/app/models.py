from sqlalchemy import Column, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(Text, primary_key=True)
    repo_url = Column(Text, nullable=False)
    repo_owner = Column(Text, nullable=False)
    repo_name = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="pending")
    error_message = Column(Text)
    total_files = Column(Integer, default=0)
    analyzed_files = Column(Integer, default=0)
    created_at = Column(Text, nullable=False)
    completed_at = Column(Text)
    workspace_id = Column(Text, ForeignKey("workspaces.id"))
    progress_message = Column(Text)

    workspace = relationship("Workspace", back_populates="analysis_job")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    repo_url = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    analysis_job = relationship("AnalysisJob", back_populates="workspace", uselist=False)
    metrics = relationship("Metric", back_populates="workspace", cascade="all, delete-orphan")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Text, primary_key=True)
    workspace_id = Column(Text, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    category = Column(Text)
    data_type = Column(Text, nullable=False, default="number")
    suggested_source = Column(Text)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(Text, nullable=False)

    workspace = relationship("Workspace", back_populates="metrics")
    entries = relationship("MetricEntry", back_populates="metric", cascade="all, delete-orphan")


class MetricEntry(Base):
    __tablename__ = "metric_entries"

    id = Column(Text, primary_key=True)
    metric_id = Column(Text, ForeignKey("metrics.id", ondelete="CASCADE"), nullable=False)
    value = Column(Text)
    recorded_at = Column(Text, nullable=False)
    notes = Column(Text)

    metric = relationship("Metric", back_populates="entries")
