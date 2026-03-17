import uuid
import random
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.dependencies import get_current_user, require_roles
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.models.store import Store
from app.models.alert import Alert
from app.models.notice import Notice
from app.models.agent_status import AgentStatus
from app.schemas.alert import AlertResponse, AlertUpdateRequest
from app.schemas.notice import NoticeResponse, NoticeDistributeRequest
from app.services.resource_metrics_service import ResourceMetricsService

router = APIRouter()


@router.get("/control-tower/overview")
async def control_tower_overview(
    current_user: User = Depends(require_roles(["hq_admin", "supervisor"])),
    db: AsyncSession = Depends(get_db),
):
    metrics_service = ResourceMetricsService(db)
    overview = await metrics_service.get_hq_overview()
    agent_result = await db.execute(select(AgentStatus))
    agents = list(agent_result.scalars().all())
    return {
        **overview,
        "agents": {
            "total": len(agents),
            "healthy": sum(1 for a in agents if a.status == "healthy"),
            "degraded": sum(1 for a in agents if a.status == "degraded"),
            "down": sum(1 for a in agents if a.status == "down"),
        },
    }


@router.get("/control-tower/agents")
async def list_agents(
    current_user: User = Depends(require_roles(["hq_admin", "supervisor"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AgentStatus))
    agents = list(result.scalars().all())
    return [
        {
            "id": a.id,
            "agent_name": a.agent_name,
            "display_name": a.display_name,
            "status": a.status,
            "latency_ms": a.latency_ms,
            "error_rate": a.error_rate,
            "last_heartbeat": a.last_heartbeat,
            "error_message": a.error_message,
        }
        for a in agents
    ]


@router.post("/control-tower/agents/{agent_name}/refresh")
async def refresh_agent(
    agent_name: str,
    current_user: User = Depends(require_roles(["hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AgentStatus).where(AgentStatus.agent_name == agent_name))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    # Mock: randomize status
    statuses = ["healthy", "healthy", "healthy", "degraded", "down"]
    agent.status = random.choice(statuses)
    agent.latency_ms = round(random.uniform(50, 500), 2)
    agent.error_rate = round(random.uniform(0, 0.1), 3)
    agent.last_heartbeat = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(agent)
    return {"agent_name": agent_name, "status": agent.status, "latency_ms": agent.latency_ms}


@router.get("/alerts", response_model=List[AlertResponse])
async def list_alerts(
    alert_status: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = Query(None),
    store_id: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(["hq_admin", "supervisor"])),
    db: AsyncSession = Depends(get_db),
):
    query = select(Alert)
    if alert_status:
        query = query.where(Alert.status == alert_status)
    if severity:
        query = query.where(Alert.severity == severity)
    if store_id:
        query = query.where(Alert.store_id == store_id)
    result = await db.execute(query.order_by(Alert.detected_at.desc()))
    return list(result.scalars().all())


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    current_user: User = Depends(require_roles(["hq_admin", "supervisor"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.patch("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    request: AlertUpdateRequest,
    current_user: User = Depends(require_roles(["hq_admin", "supervisor"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.status = request.status
    if request.resolution_comment:
        alert.resolution_comment = request.resolution_comment
    if request.status == "resolved":
        alert.resolved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("/notices", response_model=List[NoticeResponse])
async def list_notices(
    current_user: User = Depends(require_roles(["hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Notice).order_by(Notice.created_at.desc()))
    return list(result.scalars().all())


@router.post("/notices/upload", response_model=NoticeResponse, status_code=status.HTTP_201_CREATED)
async def upload_notice(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(["hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    import os
    notice_id = str(uuid.uuid4())
    notice_dir = os.path.join(settings.UPLOAD_DIR, "notices")
    os.makedirs(notice_dir, exist_ok=True)
    file_path = os.path.join(notice_dir, f"{notice_id}_{file.filename}")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    notice = Notice(
        id=notice_id,
        title=file.filename,
        file_url=file_path,
        uploaded_by=current_user.id,
        ocr_status="preprocessing",
    )
    db.add(notice)
    await db.commit()
    await db.refresh(notice)
    return notice


@router.get("/notices/{notice_id}", response_model=NoticeResponse)
async def get_notice(
    notice_id: str,
    current_user: User = Depends(require_roles(["hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Notice).where(Notice.id == notice_id))
    notice = result.scalar_one_or_none()
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found")
    return notice


@router.post("/notices/{notice_id}/distribute", response_model=NoticeResponse)
async def distribute_notice(
    notice_id: str,
    request: NoticeDistributeRequest,
    current_user: User = Depends(require_roles(["hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Notice).where(Notice.id == notice_id))
    notice = result.scalar_one_or_none()
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found")

    notice.distributed_to = request.store_ids
    notice.distributed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(notice)
    return notice
