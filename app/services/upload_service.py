import uuid
import os
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.upload_job import UploadJob
from app.core.config import settings

DEFAULT_PIPELINE_STAGES = {
    "normalize": "pending",
    "kpi_aggregate": "pending",
    "margin_guard": "pending",
    "rfm": "pending",
    "anomaly_detect": "pending",
    "briefing_schedule": "pending",
}


class UploadService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job(
        self,
        user_id: str,
        store_id: str,
        data_type: str,
        original_filename: str,
        file_path: str,
        file_size_bytes: int,
    ) -> UploadJob:
        job_id = str(uuid.uuid4())
        job = UploadJob(
            id=job_id,
            user_id=user_id,
            store_id=store_id,
            data_type=data_type,
            original_filename=original_filename,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            status="pending",
            pipeline_stages=DEFAULT_PIPELINE_STAGES.copy(),
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def advance_pipeline_mock(self, job_id: str) -> UploadJob:
        result = await self.db.execute(select(UploadJob).where(UploadJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return None

        stages = job.pipeline_stages or DEFAULT_PIPELINE_STAGES.copy()
        stage_order = ["normalize", "kpi_aggregate", "margin_guard", "rfm", "anomaly_detect", "briefing_schedule"]

        # Advance first pending stage to completed
        advanced = False
        for stage in stage_order:
            if stages.get(stage) == "pending":
                stages[stage] = "completed"
                advanced = True
                break

        job.pipeline_stages = stages

        # Check if all completed
        all_done = all(stages.get(s) == "completed" for s in stage_order)
        if all_done:
            job.status = "completed"
            job.quality_score = 0.92
        elif advanced:
            job.status = "processing"

        await self.db.commit()
        await self.db.refresh(job)
        return job
