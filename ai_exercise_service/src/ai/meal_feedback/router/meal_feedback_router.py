from fastapi import APIRouter, Depends, HTTPException
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))

from ai_exercise_service.src.util.services.auth_service import auth_service
from ai_exercise_service.src.ai.meal_feedback.service.diet_feedback_service import generate_diet_feedback_sync
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/meal-feedback", tags=["Meal Feedback"])

@router.post("/{year}/{month}")
async def get_diet_feedback(
    year: int,
    month: int,
    token: str = Depends(auth_service.verify_token)
):
    """
    월간 급식 데이터 기반 AI 피드백 생성
    """
    try:
        logger.info(f"급식 피드백 요청: {year}년 {month}월")
        
        # AI 피드백 생성
        feedback = await generate_diet_feedback_sync(year, month, token)
        
        logger.info(f"급식 피드백 생성 완료")
        return feedback
        
    except Exception as e:
        logger.error(f"급식 피드백 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"급식 피드백 생성 중 오류가 발생했습니다: {str(e)}"
        )