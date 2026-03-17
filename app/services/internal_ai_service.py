import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings

class InternalAiService:
    def __init__(self):
        self.base_url = f'{settings.AI_SERVICE_URL}/api/v1/ai'
        self.timeout = settings.AI_SERVICE_TIMEOUT_SECONDS
        self.headers = {
            'X-AI-Service-Token': settings.AI_SERVICE_TOKEN or ''
        }

    async def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f'{self.base_url}{endpoint}',
                json=data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def get_menu_analysis(self, sales_data: List[Dict], lineup_data: List[Dict]) -> Dict[str, Any]:
        return await self._post('/analyze/menu-engineering', {
            'sales_data': sales_data,
            'lineup_data': lineup_data
        })

    async def get_churn_analysis(self, point_data: List[Dict]) -> Dict[str, Any]:
        return await self._post('/analyze/customer-churn', {
            'point_data': point_data
        })

    async def get_anomaly_analysis(self, receipt_data: List[Dict]) -> Dict[str, Any]:
        return await self._post('/analyze/operational-anomalies', {
            'receipt_data': receipt_data
        })
