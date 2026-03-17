import re
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models.resource_data import MenuLineupSnapshot, PosDailySalesSnapshot, ResourceStore
from app.models.user import User
from app.services.resource_metrics_service import ResourceMetricsService

router = APIRouter()


class CommandParseRequest(BaseModel):
    command: str


class CommandValidateRequest(BaseModel):
    intent: str
    entities: dict[str, Any]


class CommandParseResponse(BaseModel):
    intent: str
    entities: dict[str, Any]
    confidence: float
    raw_command: str


class ValidationResponse(BaseModel):
    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class SimulationResponse(BaseModel):
    margin_impact: float
    sales_impact: float
    recommendation: str
    details: dict[str, Any]


@router.post("/parse", response_model=CommandParseResponse)
async def parse_command(
    request: CommandParseRequest,
    current_user: User = Depends(require_roles(["store_owner", "hq_admin", "supervisor", "marketer"])),
    db: AsyncSession = Depends(get_db),
):
    store_key = await _resolve_store_key(db, current_user)
    command = request.command.strip()
    menu_name = await _extract_menu_name(db, store_key, command)
    price_match = re.search(r"(\d[\d,]*)\s*원", command)
    target_price = int(price_match.group(1).replace(",", "")) if price_match else None

    if "매출" in command or "실적" in command:
        intent = "query_sales"
        confidence = 0.93
    elif "취소율" in command or "환불" in command:
        intent = "query_cancel_rate"
        confidence = 0.91
    elif "마진" in command or "원가" in command:
        intent = "query_menu_margin"
        confidence = 0.89
    elif "가격" in command and (target_price or menu_name):
        intent = "simulate_price_update"
        confidence = 0.87
    else:
        intent = "unknown"
        confidence = 0.2

    entities: dict[str, Any] = {"store_key": store_key}
    if menu_name:
        entities["menu_name"] = menu_name
    if target_price is not None:
        entities["target_price"] = target_price

    return CommandParseResponse(
        intent=intent,
        entities=entities,
        confidence=confidence,
        raw_command=command,
    )


@router.post("/validate", response_model=ValidationResponse)
async def validate_command(
    request: CommandValidateRequest,
    current_user: User = Depends(require_roles(["store_owner", "hq_admin", "supervisor", "marketer"])),
    db: AsyncSession = Depends(get_db),
):
    errors: list[str] = []
    warnings: list[str] = []
    store_key = request.entities.get("store_key") or await _resolve_store_key(db, current_user)

    if request.intent == "unknown":
        errors.append("질문 의도를 해석하지 못했습니다.")

    if request.intent in {"query_menu_margin", "simulate_price_update"}:
        menu_name = request.entities.get("menu_name")
        if not menu_name:
            errors.append("대상 메뉴를 찾지 못했습니다.")
        else:
            menu_row = await _get_menu_row(db, store_key, str(menu_name))
            if menu_row is None:
                errors.append("DB에 적재된 메뉴 정보에서 해당 메뉴를 찾지 못했습니다.")

    if request.intent == "simulate_price_update":
        target_price = request.entities.get("target_price")
        if not isinstance(target_price, (int, float)) or float(target_price) <= 0:
            errors.append("시뮬레이션 가격이 올바르지 않습니다.")
        elif float(target_price) < 1000:
            warnings.append("가격이 너무 낮습니다. 입력값을 다시 확인하세요.")

    if request.intent == "query_sales" and store_key is None:
        errors.append("조회 가능한 매장 데이터가 없습니다.")

    return ValidationResponse(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


@router.post("/simulate", response_model=SimulationResponse)
async def simulate_command(
    body: dict[str, Any],
    current_user: User = Depends(require_roles(["store_owner", "hq_admin", "supervisor", "marketer"])),
    db: AsyncSession = Depends(get_db),
):
    intent = body.get("intent") or body.get("action") or "unknown"
    entities = body.get("entities") if isinstance(body.get("entities"), dict) else body
    store_key = entities.get("store_key") or await _resolve_store_key(db, current_user)

    if intent == "query_sales":
        metrics = await ResourceMetricsService(db).get_owner_dashboard_metrics(store_key=store_key)
        return SimulationResponse(
            margin_impact=0.0,
            sales_impact=round(metrics["revenue_vs_yesterday"], 2),
            recommendation="전일 대비 증감을 기준으로 객수와 객단가를 함께 확인하세요.",
            details=metrics,
        )

    if intent == "query_cancel_rate":
        metrics = await ResourceMetricsService(db).get_owner_dashboard_metrics(store_key=store_key)
        return SimulationResponse(
            margin_impact=round(-(metrics["cancel_rate"] or 0.0), 4),
            sales_impact=round(-((metrics["cancel_rate"] or 0.0) * (metrics["today_revenue"] or 0.0)), 2),
            recommendation="환불 금액과 피크 시간대 운영 이슈를 먼저 점검하는 편이 맞습니다.",
            details={
                "store_key": metrics["store_key"],
                "store_name": metrics["store_name"],
                "latest_date": metrics["latest_date"],
                "cancel_rate": metrics["cancel_rate"],
                "today_revenue": metrics["today_revenue"],
                "transaction_count": metrics["transaction_count"],
            },
        )

    if intent == "query_menu_margin":
        menu_name = entities.get("menu_name")
        menu_row = await _get_menu_row(db, store_key, str(menu_name) if menu_name else None)
        if menu_row is None:
            menu_row = await _get_lowest_margin_menu(db, store_key)
        if menu_row is None:
            return SimulationResponse(
                margin_impact=0.0,
                sales_impact=0.0,
                recommendation="매뉴 라인업 데이터가 아직 적재되지 않았습니다.",
                details={},
            )
        cost_rate = float(menu_row.cost_rate or 0.0)
        return SimulationResponse(
            margin_impact=round((1 - cost_rate) * 100, 2),
            sales_impact=0.0,
            recommendation="원가율이 높은 메뉴는 가격 조정 또는 구성 변경을 검토하세요.",
            details={
                "store_key": store_key,
                "menu_name": menu_row.menu_name,
                "sales_price": menu_row.sales_price,
                "cost_amount": menu_row.cost_amount,
                "cost_rate": menu_row.cost_rate,
            },
        )

    if intent == "simulate_price_update":
        menu_name = entities.get("menu_name")
        target_price = float(entities.get("target_price") or 0.0)
        menu_row = await _get_menu_row(db, store_key, str(menu_name) if menu_name else None)
        if menu_row is None:
            return SimulationResponse(
                margin_impact=0.0,
                sales_impact=0.0,
                recommendation="시뮬레이션 대상 메뉴를 찾지 못했습니다.",
                details={},
            )
        current_price = float(menu_row.sales_price or 0.0)
        cost_amount = float(menu_row.cost_amount or 0.0)
        current_margin_rate = ((current_price - cost_amount) / current_price) if current_price > 0 else 0.0
        predicted_margin_rate = ((target_price - cost_amount) / target_price) if target_price > 0 else current_margin_rate
        price_change_pct = ((target_price - current_price) / current_price) if current_price > 0 else 0.0
        sales_impact = round(-(price_change_pct * 0.35), 4)
        return SimulationResponse(
            margin_impact=round(predicted_margin_rate - current_margin_rate, 4),
            sales_impact=sales_impact,
            recommendation="가격 조정 시 예상 판매량 감소와 마진 개선을 함께 보세요.",
            details={
                "store_key": store_key,
                "menu_name": menu_row.menu_name,
                "current_price": current_price,
                "target_price": target_price,
                "cost_amount": cost_amount,
                "current_margin_rate": round(current_margin_rate, 4),
                "predicted_margin_rate": round(predicted_margin_rate, 4),
            },
        )

    return SimulationResponse(
        margin_impact=0.0,
        sales_impact=0.0,
        recommendation="해석 가능한 질문으로 다시 요청하세요.",
        details={},
    )


async def _resolve_store_key(db: AsyncSession, current_user: User) -> Optional[str]:
    if current_user.store_id:
        direct = (
            await db.execute(
                select(ResourceStore.store_key)
                .where(ResourceStore.store_key == current_user.store_id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if direct:
            return direct

    return (
        await db.execute(
            select(ResourceStore.store_key)
            .where(ResourceStore.source_kind == "pos_daily_sales")
            .order_by(ResourceStore.store_name.asc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _extract_menu_name(db: AsyncSession, store_key: Optional[str], command: str) -> Optional[str]:
    if not store_key:
        return None
    names = list(
        (
            await db.execute(
                select(MenuLineupSnapshot.menu_name)
                .where(
                    MenuLineupSnapshot.store_key == store_key,
                    MenuLineupSnapshot.menu_name.is_not(None),
                )
                .limit(100)
            )
        ).scalars().all()
    )
    for name in names:
        if name and name in command:
            return name
    return None


async def _get_menu_row(db: AsyncSession, store_key: Optional[str], menu_name: Optional[str]) -> Optional[MenuLineupSnapshot]:
    if not store_key or not menu_name:
        return None
    result = await db.execute(
        select(MenuLineupSnapshot)
        .where(
            MenuLineupSnapshot.store_key == store_key,
            MenuLineupSnapshot.menu_name == menu_name,
        )
        .order_by(MenuLineupSnapshot.row_number.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_lowest_margin_menu(db: AsyncSession, store_key: Optional[str]) -> Optional[MenuLineupSnapshot]:
    if not store_key:
        return None
    result = await db.execute(
        select(MenuLineupSnapshot)
        .where(
            MenuLineupSnapshot.store_key == store_key,
            MenuLineupSnapshot.menu_name.is_not(None),
        )
        .order_by(MenuLineupSnapshot.cost_rate.desc().nullslast())
        .limit(1)
    )
    return result.scalar_one_or_none()
