from datetime import date
from typing import Any, Optional

from pydantic import BaseModel


class ResourceStoreSummary(BaseModel):
    store_key: str
    latest_file_name: Optional[str] = None
    file_count: int
    date_start: Optional[date] = None
    date_end: Optional[date] = None


class ResourceSourceCatalog(BaseModel):
    source_kind: str
    label: str
    description: str
    stores: list[ResourceStoreSummary]


class ResourceCatalogResponse(BaseModel):
    sources: list[ResourceSourceCatalog]


class ResourceDatasetResponse(BaseModel):
    source_kind: str
    store_key: str
    headers: list[str]
    rows: list[dict[str, Any]]
    summary: dict[str, Any]


class ResourceImportResponse(BaseModel):
    source_kind: str
    store_key: Optional[str] = None
    imported_count: int
    message: str
