"""
Seed script: creates sample data for development.
Run: python -m scripts.seed_data
"""
import asyncio
import uuid
from datetime import datetime, date, timezone

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.store import Store, StoreSupervisorAssignment
from app.models.sales import SalesKpi
from app.models.customer import Customer, RfmSnapshot
from app.models.agent_status import AgentStatus
from app.models.alert import Alert
from app.models.action import Action
from app.db.database import Base

engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # --- Stores ---
        stores = [
            Store(
                id=str(uuid.uuid4()),
                name=f"AgentGo 강남점",
                region="서울",
                address="서울시 강남구 테헤란로 123",
                size="대형",
                open_time="08:00",
                close_time="22:00",
                seats=80,
                service_type="카페",
                is_active=True,
            ),
            Store(
                id=str(uuid.uuid4()),
                name=f"AgentGo 홍대점",
                region="서울",
                address="서울시 마포구 홍익로 45",
                size="중형",
                open_time="09:00",
                close_time="23:00",
                seats=50,
                service_type="카페",
                is_active=True,
            ),
            Store(
                id=str(uuid.uuid4()),
                name=f"AgentGo 부산서면점",
                region="부산",
                address="부산시 부산진구 서면로 88",
                size="중형",
                open_time="08:00",
                close_time="21:00",
                seats=40,
                service_type="카페",
                is_active=True,
            ),
            Store(
                id=str(uuid.uuid4()),
                name=f"AgentGo 대전둔산점",
                region="대전",
                address="대전시 서구 둔산로 200",
                size="소형",
                open_time="09:00",
                close_time="20:00",
                seats=20,
                service_type="카페",
                is_active=True,
            ),
            Store(
                id=str(uuid.uuid4()),
                name=f"AgentGo 광주충장점",
                region="광주",
                address="광주시 동구 충장로 77",
                size="소형",
                open_time="09:00",
                close_time="21:00",
                seats=24,
                service_type="카페",
                is_active=True,
            ),
        ]
        for store in stores:
            db.add(store)
        await db.flush()

        # --- Users ---
        hq_admin = User(
            id=str(uuid.uuid4()),
            email="admin@itcen.com",
            name="본사관리자",
            hashed_password=hash_password("1234"),
            role="hq_admin",
            is_active=True,
        )
        supervisor = User(
            id=str(uuid.uuid4()),
            email="sv@itcen.com",
            name="슈퍼바이저김",
            hashed_password=hash_password("1234"),
            role="supervisor",
            is_active=True,
        )
        owner1 = User(
            id=str(uuid.uuid4()),
            email="owner1@itcen.com",
            name="강남점주",
            hashed_password=hash_password("1234"),
            role="store_owner",
            store_id=stores[0].id,
            is_active=True,
        )
        marketer = User(
            id=str(uuid.uuid4()),
            email="marketer@itcen.com",
            name="마케터박",
            hashed_password=hash_password("1234"),
            role="marketer",
            is_active=True,
        )

        for user in [hq_admin, supervisor, owner1, marketer]:
            db.add(user)
        await db.flush()

        # --- SV Assignments ---
        for store in stores[:3]:
            db.add(StoreSupervisorAssignment(
                id=str(uuid.uuid4()),
                store_id=store.id,
                supervisor_id=supervisor.id,
            ))
        await db.flush()

        # --- Sales KPIs ---
        today = date.today()
        for store in stores:
            kpi = SalesKpi(
                id=str(uuid.uuid4()),
                store_id=store.id,
                date=today,
                revenue=1_850_000.0,
                transaction_count=142,
                avg_order_value=13_028.0,
                cancel_count=5,
                cancel_rate=0.035,
                seat_turnover=4.2,
            )
            db.add(kpi)
            # Hourly
            for hour in [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]:
                db.add(SalesKpi(
                    id=str(uuid.uuid4()),
                    store_id=store.id,
                    date=today,
                    hour=hour,
                    revenue=float(80_000 + (hour % 4) * 30_000),
                    transaction_count=8 + hour % 5,
                    avg_order_value=10_000.0,
                    cancel_count=0,
                    cancel_rate=0.0,
                ))

        # --- RFM Snapshots ---
        for store in stores:
            db.add(RfmSnapshot(
                id=str(uuid.uuid4()),
                store_id=store.id,
                snapshot_date=today,
                vip_count=45,
                loyal_count=120,
                at_risk_count=80,
                churned_count=35,
                vip_sales_share=0.42,
                loyal_sales_share=0.35,
                at_risk_sales_share=0.16,
                churned_sales_share=0.07,
            ))

        # --- Customers ---
        for store in stores[:2]:
            for i in range(5):
                db.add(Customer(
                    id=str(uuid.uuid4()),
                    store_id=store.id,
                    external_key=f"cust_{store.id[:8]}_{i:03d}",
                    rfm_segment="at_risk" if i % 2 == 0 else "vip",
                    visit_count=10 + i,
                    last_visit_date=today,
                    avg_order_value=12_000.0 + i * 500,
                    total_ltv=500_000.0 + i * 10_000,
                    risk_score=0.7 + i * 0.05,
                    days_since_last_visit=30 + i * 5,
                ))

        # --- Agent Statuses ---
        agents = [
            ("kpi_agent", "KPI 집계 에이전트", "healthy", 85.0, 0.001),
            ("anomaly_agent", "이상 탐지 에이전트", "healthy", 120.0, 0.002),
            ("rfm_agent", "RFM 분류 에이전트", "healthy", 95.0, 0.0),
            ("briefing_agent", "브리핑 생성 에이전트", "degraded", 450.0, 0.05),
            ("ocr_agent", "OCR 처리 에이전트", "healthy", 300.0, 0.01),
            ("campaign_agent", "캠페인 추천 에이전트", "healthy", 110.0, 0.003),
        ]
        for agent_name, display_name, status_val, latency, err_rate in agents:
            db.add(AgentStatus(
                id=str(uuid.uuid4()),
                agent_name=agent_name,
                display_name=display_name,
                status=status_val,
                latency_ms=latency,
                error_rate=err_rate,
                last_heartbeat=datetime.now(timezone.utc),
            ))

        # --- Alerts ---
        alerts_data = [
            (stores[0].id, "cancel", "P0", "취소율 급등 감지", "오후 2시 기준 취소율이 8.5%로 정상 범위(3%) 초과"),
            (stores[1].id, "discount", "P1", "할인 남용 의심", "직원 코드 반복 사용으로 비정상 할인 패턴 감지"),
            (stores[2].id, "review", "P2", "리뷰 평점 하락", "최근 7일 평균 평점 3.2점 (이전 4.1점)"),
        ]
        for store_id, alert_type, severity, title, desc in alerts_data:
            db.add(Alert(
                id=str(uuid.uuid4()),
                store_id=store_id,
                alert_type=alert_type,
                severity=severity,
                title=title,
                description=desc,
                detected_at=datetime.now(timezone.utc),
                anomaly_score=0.85,
                status="new",
            ))

        # --- Actions ---
        actions_data = [
            (stores[0].id, hq_admin.id, "취소율 개선 조치", "주방 속도 개선 및 직원 교육 실시", "운영", "P0"),
            (stores[0].id, hq_admin.id, "피크타임 인력 추가", "점심 피크타임(12-14시) 파트타임 1명 추가 배치", "인력", "P1"),
            (stores[1].id, hq_admin.id, "할인 정책 점검", "POS 할인 코드 접근 권한 재설정", "보안", "P0"),
        ]
        for store_id, created_by, title, desc, category, priority in actions_data:
            db.add(Action(
                id=str(uuid.uuid4()),
                store_id=store_id,
                created_by=created_by,
                title=title,
                description=desc,
                category=category,
                priority=priority,
                status="pending",
                ai_basis="AI 이상 탐지 기반 자동 생성",
                expected_impact="취소율 3% 이하로 복구 예상",
            ))

        await db.commit()
        print("Seed data created successfully!")
        print(f"\nTest accounts:")
        print(f"  HQ Admin:   admin@itcen.com / 1234")
        print(f"  Supervisor: sv@itcen.com / 1234")
        print(f"  Owner:      owner1@itcen.com / 1234")
        print(f"  Marketer:   marketer@itcen.com / 1234")


if __name__ == "__main__":
    asyncio.run(seed())
