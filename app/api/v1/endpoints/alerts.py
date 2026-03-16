from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.user import User
from app.models.alert import Alert

router = APIRouter()

@router.get("/anomalies")
async def get_anomalies(
    store_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Alert)
    if store_id:
        query = query.where(Alert.store_id == store_id)
    
    result = await db.execute(query.order_by(Alert.detected_at.desc()))
    alerts = result.scalars().all()
    
    return [
        {
            "id": a.id,
            "alert_type": a.alert_type,
            "score": a.score,
            "detected_at": a.detected_at,
            "status": a.status,
            "recommended_action": a.recommended_action,
            "evidence": a.evidence
        }
        for a in alerts
    ]

@router.post("/{alert_id}/status")
async def update_alert_status(
    alert_id: str,
    status: str,
    comment: Optional[str] = None,
    current_user: User = Depends(require_roles(["supervisor", "hq_admin", "store_owner"])),
    db: AsyncSession = Depends(get_db),
):
    if status not in ["new", "in_progress", "resolved"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = status
    await db.commit()
    return {"id": alert_id, "status": status, "updated_at": "2026-03-15T10:00:00Z"}
