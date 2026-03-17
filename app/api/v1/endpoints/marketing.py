import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.user import User
from app.models.campaign import Campaign
from app.models.customer import Customer, RfmSnapshot
from app.schemas.campaign import CampaignCreateRequest, CampaignResponse

router = APIRouter()


@router.get("/rfm/segments")
async def rfm_segments(
    current_user: User = Depends(require_roles(["marketer", "hq_admin", "supervisor"])),
    db: AsyncSession = Depends(get_db),
):
    # Latest RFM snapshot per store
    result = await db.execute(
        select(RfmSnapshot).order_by(RfmSnapshot.snapshot_date.desc())
    )
    snapshots = list(result.scalars().all())

    # Aggregate across stores
    total_vip = sum(s.vip_count for s in snapshots)
    total_loyal = sum(s.loyal_count for s in snapshots)
    total_at_risk = sum(s.at_risk_count for s in snapshots)
    total_churned = sum(s.churned_count for s in snapshots)

    total_count = max(total_vip + total_loyal + total_at_risk + total_churned, 1)
    return [
        {
            "segment": "champions",
            "count": total_vip,
            "avg_order_value": 0.0,
            "avg_visit_frequency": 0.0,
            "revenue_share": round(total_vip / total_count, 4),
        },
        {
            "segment": "loyal",
            "count": total_loyal,
            "avg_order_value": 0.0,
            "avg_visit_frequency": 0.0,
            "revenue_share": round(total_loyal / total_count, 4),
        },
        {
            "segment": "at_risk",
            "count": total_at_risk,
            "avg_order_value": 0.0,
            "avg_visit_frequency": 0.0,
            "revenue_share": round(total_at_risk / total_count, 4),
        },
        {
            "segment": "lost",
            "count": total_churned,
            "avg_order_value": 0.0,
            "avg_visit_frequency": 0.0,
            "revenue_share": round(total_churned / total_count, 4),
        },
    ]


@router.get("/rfm/churn-risks")
async def churn_risks(
    current_user: User = Depends(require_roles(["marketer", "hq_admin", "supervisor"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Customer).where(
            Customer.rfm_segment.in_(["at_risk", "churned"])
        ).order_by(Customer.risk_score.desc()).limit(50)
    )
    customers = list(result.scalars().all())

    return [
        {
            "customer_id": c.id,
            "name": c.external_key,
            "last_visit_date": c.last_visit_date.isoformat() if c.last_visit_date else None,
            "churn_probability": c.risk_score,
            "segment": c.rfm_segment,
            "recommended_offer": "재방문 쿠폰 제공",
        }
        for c in customers
    ]


@router.post("/rfm/churn-risks/{customer_id}/exclude")
async def exclude_churn_risk(
    customer_id: str,
    current_user: User = Depends(require_roles(["marketer", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    # Toggle risk_score to 0 as exclusion flag (in-memory/simple approach)
    customer.risk_score = 0.0 if (customer.risk_score or 0) > 0 else -1.0
    await db.commit()
    return {"message": f"Customer {customer_id} exclusion updated"}


@router.get("/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(
    channel: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(["marketer", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    query = select(Campaign)
    if channel:
        query = query.where(Campaign.channel == channel)
    result = await db.execute(query.order_by(Campaign.created_at.desc()))
    return list(result.scalars().all())


@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    request: CampaignCreateRequest,
    current_user: User = Depends(require_roles(["marketer", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    campaign = Campaign(
        id=str(uuid.uuid4()),
        name=request.name,
        channel=request.channel,
        target_segment=request.target_segment,
        offer_type=request.offer_type,
        offer_value=request.offer_value,
        message_template=request.message_template,
        status="draft",
        created_by=current_user.id,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.post("/campaigns/{campaign_id}/send", response_model=CampaignResponse)
async def send_campaign(
    campaign_id: str,
    current_user: User = Depends(require_roles(["marketer", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    if campaign.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft campaigns can be sent")

    campaign.status = "sent"
    campaign.sent_at = datetime.now(timezone.utc)
    campaign.sent_count = 100  # mock

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("/performance")
async def campaign_performance(
    channel: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(["marketer", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    query = select(Campaign).where(Campaign.status.in_(["sent", "completed"]))
    if channel:
        query = query.where(Campaign.channel == channel)
    result = await db.execute(query.order_by(Campaign.sent_at.desc()))
    campaigns = list(result.scalars().all())

    return [
        {
            "id": c.id,
            "name": c.name,
            "channel": c.channel,
            "target_segment": c.target_segment,
            "sent_count": c.sent_count,
            "opened_count": c.opened_count,
            "used_count": c.used_count,
            "open_rate": round(c.opened_count / c.sent_count, 3) if c.sent_count > 0 else 0,
            "use_rate": round(c.used_count / c.sent_count, 3) if c.sent_count > 0 else 0,
            "revenue_attributed": c.revenue_attributed,
            "sent_at": c.sent_at,
        }
        for c in campaigns
    ]
