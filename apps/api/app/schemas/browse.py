from datetime import datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class BrowseRequest(BaseModel):
    url: AnyHttpUrl = Field(max_length=2048)


class BrowseJob(BaseModel):
    job_id: str
    url: str
    requested_at: datetime
    idempotency_key: str | None = None


class BrowseAccepted(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(alias="jobId")
    status: Literal["queued", "duplicate"]
    deduplicated: bool
