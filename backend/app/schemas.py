from pydantic import BaseModel
from typing import Optional, List


# --- Workflow Schemas ---

class AnalyzeRequest(BaseModel):
    repo_url: str


class JobResponse(BaseModel):
    id: str
    repo_url: str
    repo_owner: str
    repo_name: str
    status: str
    error_message: Optional[str] = None
    total_files: int = 0
    analyzed_files: int = 0
    created_at: str
    completed_at: Optional[str] = None
    workspace_id: Optional[str] = None
    progress_message: Optional[str] = None


class MetricResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    data_type: str = "number"
    suggested_source: Optional[str] = None
    display_order: int = 0
    created_at: str


class JobMetricsResponse(BaseModel):
    job: JobResponse
    metrics: List[MetricResponse]
    workspace_id: Optional[str] = None


# --- Dashboard Schemas ---

class WorkspaceResponse(BaseModel):
    id: str
    name: str
    repo_url: str
    description: Optional[str] = None
    created_at: str
    updated_at: str
    metric_count: int = 0


class WorkspaceDetailResponse(BaseModel):
    id: str
    name: str
    repo_url: str
    description: Optional[str] = None
    created_at: str
    updated_at: str
    dashboard_config: Optional[str] = None
    metrics: List[MetricResponse]


class MetricEntryCreate(BaseModel):
    value: str
    notes: Optional[str] = None


class MetricEntryResponse(BaseModel):
    id: str
    metric_id: str
    value: Optional[str] = None
    recorded_at: str
    notes: Optional[str] = None
