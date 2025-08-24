import asyncio
from typing import Dict, Any
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

import logging

logger = logging.getLogger(__name__)
from ai.meal_feedback.graph.meal_analysis_graph import meal_analysis_graph, MealAnalysisState

class DietFeedbackService:
    """급식 피드백 서비스"""
    
    def __init__(self):
        self.graph = meal_analysis_graph
    
    async def generate_comprehensive_feedback(self, year: int, month: int, token: str) -> Dict[str, Any]:
        """
        LangGraph를 사용한 종합적인 급식 피드백 생성
        
        Args:
            year: 분석 대상 연도
            month: 분석 대상 월
            token: 인증 토큰
            
        Returns:
            종합 급식 분석 결과
        """
        try:
            logger.info(f"종합 급식 분석 시작: {year}년 {month}월")
            
            # 초기 상태 생성
            initial_state: MealAnalysisState = {
                "request_params": {
                    "year": year,
                    "month": month,
                    "token": token
                },
                "raw_meal_data": {},
                "processed_data": {},
                "nutritional_analysis": {},
                "final_report": {},
                "error_message": ""
            }
            
            # 그래프 실행 (비동기)
            result = await self.graph.ainvoke(initial_state)
            
            # 에러 체크
            if result["error_message"]:
                logger.error(f"급식 분석 중 오류: {result['error_message']}")
                return {
                    "success": False,
                    "error": result["error_message"],
                    "feedback_result": {}
                }
            
            logger.info("종합 급식 분석 완료")
            return {
                "success": True,
                "error": "",
                "feedback_result": result["final_report"]
            }
            
        except Exception as e:
            logger.error(f"급식 피드백 서비스 오류: {str(e)}")
            return {
                "success": False,
                "error": f"분석 중 오류 발생: {str(e)}",
                "feedback_result": {}
            }

# 전역 서비스 인스턴스
diet_feedback_service = DietFeedbackService()

async def generate_diet_feedback_sync(year: int, month: int, token: str):
    """
    기존 호환성을 위한 래퍼 함수
    """
    try:
        result = await diet_feedback_service.generate_comprehensive_feedback(year, month, token)
        
        if result["success"]:
            return result["feedback_result"]
        else:
            # 오류 발생시 기본 응답
            return {
                "analysis_period": f"{year}년 {month}월",
                "error": result["error"],
                "message": "데이터 분석 중 오류가 발생했습니다."
            }
            
    except Exception as e:
        logger.error(f"래퍼 함수 오류: {str(e)}")
        return {
            "analysis_period": f"{year}년 {month}월",
            "error": str(e),
            "message": "시스템 오류가 발생했습니다."
        }