import uuid
from datetime import datetime
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
from app.services.campaign_simulation_service import CampaignSimulationService
from app.services.campaign_uplift_service import CampaignUpliftService

router = APIRouter()
DEFAULT_CAMPAIGN_STORE_KEY = "[CJ]광화문점"
SEGMENT_COUNT_ATTR = {
    "champions": "vip_count",
    "loyal": "loyal_count",
    "at_risk": "at_risk_count",
    "lost": "churned_count",
}
SEGMENT_MENU_PRESET = {
    "champions": {"menu_name": "광동의점심상(2인)", "menu_price": 78000.0, "margin_rate": 0.31, "daily_avg_qty": 7.0},
    "loyal": {"menu_name": "특선런치 A코스", "menu_price": 55000.0, "margin_rate": 0.33, "daily_avg_qty": 8.0},
    "at_risk": {"menu_name": "셰프의 마파박스", "menu_price": 39000.0, "margin_rate": 0.36, "daily_avg_qty": 14.0},
    "lost": {"menu_name": "셰프의 새우박스", "menu_price": 42000.0, "margin_rate": 0.34, "daily_avg_qty": 11.0},
}


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

    sent_count = await _resolve_target_count(db, campaign.target_segment)
    uplift_service = CampaignUpliftService(db)
    bep_service = CampaignSimulationService(db)
    uplift_result = None
    bep_result = None
    try:
        uplift_result = await uplift_service.predict_uplift(
            store_key=DEFAULT_CAMPAIGN_STORE_KEY,
            segment_name=campaign.target_segment,
            channel=campaign.channel,
            target_customers=sent_count,
            discount_rate=float(campaign.offer_value or 0.0) / 100,
        )
    except Exception:
        uplift_result = None
    try:
        menu_preset = SEGMENT_MENU_PRESET.get(campaign.target_segment, SEGMENT_MENU_PRESET["at_risk"])
        bep_result = await bep_service.simulate_bep(
            store_key=DEFAULT_CAMPAIGN_STORE_KEY,
            segment_name=campaign.target_segment,
            channel=campaign.channel,
            offer_type=campaign.offer_type,
            offer_value=float(campaign.offer_value or 0.0),
            target_customers=sent_count,
            promo_days=max(_campaign_days(campaign), 7),
            fixed_cost=50000.0,
            menu_name=menu_preset["menu_name"],
            menu_price=menu_preset["menu_price"],
            margin_rate=menu_preset["margin_rate"],
            daily_avg_qty=menu_preset["daily_avg_qty"],
        )
    except Exception:
        bep_result = None

    campaign.status = "sent"
    campaign.sent_at = datetime.utcnow()
    campaign.sent_count = sent_count
    campaign.opened_count = (
        round(sent_count * uplift_result["expected_redemption_rate"] * 4.1)
        if uplift_result
        else round(sent_count * 0.42)
    )
    campaign.used_count = (
        uplift_result["expected_incremental_orders"]
        if uplift_result
        else round(sent_count * 0.11)
    )
    campaign.revisit_count = campaign.used_count
    campaign.revenue_attributed = (
        float(bep_result["expected_incremental_revenue"])
        if bep_result
        else float(campaign.used_count * 39000)
    )

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


@router.get("/campaigns/simulate-bep")
async def campaign_simulate_bep(
    store_key: str = Query(...),
    segment_name: str = Query(...),
    channel: str = Query(...),
    offer_type: str = Query(...),
    offer_value: float = Query(...),
    target_customers: int = Query(...),
    promo_days: int = Query(...),
    fixed_cost: float = Query(...),
    menu_name: str = Query(...),
    menu_price: float = Query(...),
    margin_rate: float = Query(...),
    daily_avg_qty: float = Query(...),
    current_user: User = Depends(require_roles(["marketer", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = CampaignSimulationService(db)
    return await service.simulate_bep(
        store_key=store_key,
        segment_name=segment_name,
        channel=channel,
        offer_type=offer_type,
        offer_value=offer_value,
        target_customers=target_customers,
        promo_days=promo_days,
        fixed_cost=fixed_cost,
        menu_name=menu_name,
        menu_price=menu_price,
        margin_rate=margin_rate,
        daily_avg_qty=daily_avg_qty,
    )


@router.get("/campaigns/predict-uplift")
async def campaign_predict_uplift(
    store_key: str = Query(...),
    segment_name: str = Query(...),
    channel: str = Query(...),
    target_customers: int = Query(...),
    discount_rate: float = Query(...),
    current_user: User = Depends(require_roles(["marketer", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = CampaignUpliftService(db)
    return await service.predict_uplift(
        store_key=store_key,
        segment_name=segment_name,
        channel=channel,
        target_customers=target_customers,
        discount_rate=discount_rate,
    )


async def _resolve_target_count(db: AsyncSession, target_segment: str) -> int:
    latest_snapshot = (
        await db.execute(select(RfmSnapshot).order_by(RfmSnapshot.snapshot_date.desc()).limit(1))
    ).scalar_one_or_none()
    attr_name = SEGMENT_COUNT_ATTR.get(target_segment, "at_risk_count")
    if latest_snapshot and hasattr(latest_snapshot, attr_name):
        return max(1, int(getattr(latest_snapshot, attr_name) or 0))
    return 100


def _campaign_days(campaign: Campaign) -> int:
    if campaign.start_date and campaign.end_date:
        return max((campaign.end_date - campaign.start_date).days + 1, 1)
    return 7
