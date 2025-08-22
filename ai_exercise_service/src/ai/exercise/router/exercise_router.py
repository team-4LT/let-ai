from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))

from ai_exercise_service.src.util.services.auth_service import auth_service
from ai_exercise_service.src.ai.exercise.service.exercise_recommendation_service import exercise_recommendation_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exercises", tags=["Exercises"])


@router.post("/recommend")
async def recommend_exercises_auto(
    user_id: str = Depends(auth_service.get_user_id_from_token),
    token: str = Depends(auth_service.verify_token)
):
    """
    사용자의 오늘 칼로리 섭취량을 자동으로 가져와서 운동 추천 (권장)
    """
    try:
        logger.info(f"자동 운동 추천 요청: 사용자 {user_id}")
        
        result = await exercise_recommendation_service.recommend_exercises_auto(
            user_id, token
        )
        
        if result["success"]:
            logger.info("자동 운동 추천 완료")
            return result
        else:
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )
            
    except Exception as e:
        logger.error(f"자동 운동 추천 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"자동 운동 추천 중 오류가 발생했습니다: {str(e)}"
        )
