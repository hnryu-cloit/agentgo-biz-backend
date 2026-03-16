from fastapi import APIRouter, Depends, HTTPException
from typing import List, Any, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class CommandParseRequest(BaseModel):
    command: str

class CommandParseResponse(BaseModel):
    intent: str
    entities: dict
    confidence: float
    structured_request: dict
    failure_reason: Optional[str] = None

class ValidationResponse(BaseModel):
    is_valid: bool
    errors: List[str] = []
    correction_guide: Optional[str] = None

@router.post('/parse', response_model=CommandParseResponse)
async def parse_command(request: CommandParseRequest):
    # Mock natural language parsing
    if '치킨' in request.command:
        return CommandParseResponse(
            intent='update_price',
            entities={'menu': '양념치킨', 'price': 20000},
            confidence=0.95,
            structured_request={'action': 'update_price', 'item_id': 101, 'new_price': 20000}
        )
    return CommandParseResponse(
        intent='unknown',
        entities={},
        confidence=0.1,
        structured_request={},
        failure_reason='모호한 명령입니다.'
    )

@router.post('/validate', response_model=ValidationResponse)
async def validate_command(structured_request: dict):
    # Mock validation
    if structured_request.get('item_id') == 101:
        return ValidationResponse(is_valid=True)
    return ValidationResponse(is_valid=False, errors=['존재하지 않는 메뉴입니다.'], correction_guide='메뉴 이름을 다시 확인해주세요.')

@router.post('/simulate')
async def simulate_command(structured_request: dict):
    # Mock simulation of POS change impact
    return {
        'status': 'success',
        'impact': {
            'margin_change': -0.05,
            'sales_change': 0.12,
            'current_margin': 0.35,
            'predicted_margin': 0.30
        },
        'comparison': {
            'current_price': 18000,
            'proposed_price': 20000
        }
    }
