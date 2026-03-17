from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.resource_data import MenuLineupSnapshot, PosDailySalesSnapshot, ReceiptTransactionSnapshot
from app.models.user import User

router = APIRouter()


class WorkflowRunRequest(BaseModel):
    workflow_name: str
    store_id: Optional[str] = None
    params: Optional[dict[str, Any]] = None


class AgentControlRequest(BaseModel):
    agent_name: str
    command: str


@router.post("/workflows/run")
async def run_workflow(
    request: WorkflowRunRequest,
    current_user: User = Depends(require_roles(["hq_admin", "marketer", "supervisor"])),
    db: AsyncSession = Depends(get_db),
):
    dry_run = bool((request.params or {}).get("dry_run", True))
    steps = ["ingest", "analyze", "publish"] if request.workflow_name == "resource_sync" else ["analysis", "strategy", "execution"]
    return {
        "workflow_id": f"WF-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "workflow_name": request.workflow_name,
        "store_id": request.store_id,
        "status": "running" if not dry_run else "dry_run",
        "steps": steps,
        "dry_run": dry_run,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status")
async def get_agent_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    latest_sales_date = (await db.execute(select(func.max(PosDailySalesSnapshot.sales_date)))).scalar_one_or_none()
    latest_receipt_date = (await db.execute(select(func.max(ReceiptTransactionSnapshot.sales_date)))).scalar_one_or_none()
    menu_count = int((await db.execute(select(func.count()).select_from(MenuLineupSnapshot))).scalar_one() or 0)

    now = datetime.now(timezone.utc)
    sales_heartbeat = _heartbeat_from_date(latest_sales_date, now)
    receipt_heartbeat = _heartbeat_from_date(latest_receipt_date, now)
    menu_heartbeat = now.isoformat() if menu_count > 0 else None

    return {
        "agents": [
            {
                "agent_name": "analysis_agent",
                "status": "healthy" if latest_sales_date else "down",
                "last_heartbeat": sales_heartbeat,
                "dataset": "pos_daily_sales",
            },
            {
                "agent_name": "strategy_agent",
                "status": "healthy" if latest_receipt_date else "degraded",
                "last_heartbeat": receipt_heartbeat,
                "dataset": "receipt_listing",
            },
            {
                "agent_name": "execution_agent",
                "status": "healthy" if menu_count > 0 else "degraded",
                "last_heartbeat": menu_heartbeat,
                "dataset": "menu_lineup",
            },
        ],
        "resource_health": {
            "latest_sales_date": latest_sales_date.isoformat() if latest_sales_date else None,
            "latest_receipt_date": latest_receipt_date.isoformat() if latest_receipt_date else None,
            "menu_row_count": menu_count,
        },
    }


@router.post("/control")
async def control_agent(
    request: AgentControlRequest,
    current_user: User = Depends(require_roles(["hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    return {
        "agent_name": request.agent_name,
        "command": request.command,
        "status": "accepted",
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }


def _heartbeat_from_date(value: Optional[Any], now: datetime) -> Optional[str]:
    if value is None:
        return None
    heartbeat = datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=9)
    if heartbeat > now:
        heartbeat = now
    return heartbeat.isoformat()
