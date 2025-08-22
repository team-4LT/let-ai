import asyncio
import httpx
from typing import Dict, Any, List
import logging
from datetime import datetime
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../..', '.env'))

logger = logging.getLogger(__name__)

# LangGraph 임포트
from ai.exercise.graph.exercise_recommendation_graph import exercise_recommendation_graph, ExerciseRecommendationState

class ExerciseRecommendationService:
    """사용자 칼로리 기반 운동 추천 서비스 - LangGraph 기반"""
    
    def __init__(self):
        self.spring_url = "http://localhost:8080"
        self.timeout = 30.0
        self.graph = exercise_recommendation_graph
    
    async def recommend_exercises_auto(self, user_id: str, token: str) -> Dict[str, Any]:
        """
        사용자의 오늘 칼로리 섭취량을 자동으로 가져와서 운동 추천
        
        Args:
            user_id: 사용자 ID
            token: 인증 토큰
            
        Returns:
            운동 추천 결과
        """
        try:
            logger.info(f"자동 운동 추천 시작: 사용자 {user_id}")
            
            # 1. 오늘 칼로리 섭취량 가져오기
            daily_calories = await self._get_today_calories(user_id, token)
            
            # 2. Spring에서 운동 목록 가져오기
            exercises = await self._get_exercises_from_spring(token)
            
            # 3. LangGraph를 통한 AI 기반 운동 추천
            recommendation = await self._ai_recommend_exercises(daily_calories, exercises, user_id)
            
            logger.info(f"자동 운동 추천 완료: 사용자 {user_id}, 칼로리 {daily_calories}")
            return {
                "success": True,
                "user_id": user_id,
                "daily_calories": daily_calories,
                "data_source": "auto_fetched",
                "recommendation": recommendation
            }
            
        except Exception as e:
            logger.error(f"자동 운동 추천 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "recommendation": {}
            }

    async def recommend_exercises_by_calories(self, user_id: str, token: str, daily_calories: float) -> Dict[str, Any]:
        """
        사용자가 오늘 먹은 칼로리를 기반으로 운동 추천
        
        Args:
            user_id: 사용자 ID
            token: 인증 토큰  
            daily_calories: 오늘 섭취한 칼로리
            
        Returns:
            운동 추천 결과
        """
        try:
            logger.info(f"칼로리 기반 운동 추천 시작: 사용자 {user_id}, 칼로리 {daily_calories}")
            
            # 1. Spring에서 운동 목록 가져오기
            exercises = await self._get_exercises_from_spring(token)
            
            # 2. LangGraph를 통한 AI 기반 운동 추천
            recommendation = await self._ai_recommend_exercises(daily_calories, exercises, user_id)
            
            logger.info(f"운동 추천 완료: 사용자 {user_id}")
            return {
                "success": True,
                "user_id": user_id,
                "daily_calories": daily_calories,
                "recommendation": recommendation
            }
            
        except Exception as e:
            logger.error(f"운동 추천 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "recommendation": {}
            }
    
    async def _get_today_calories(self, user_id: str, token: str) -> float:
        """Spring API에서 사용자의 오늘 칼로리 섭취량 조회"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            today = datetime.now().strftime("%Y-%m-%d")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.spring_url}/eater/user/{user_id}/date/{today}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    api_response = response.json()
                    # Spring API 응답 구조 확인: {"data": {...}} 또는 직접 데이터
                    data = api_response.get("data", api_response)
                    
                    # 다양한 칼로리 필드명 시도
                    calories = (data.get("totalCalorieIntake") or 
                              data.get("totalCalories") or 
                              data.get("calories") or 
                              data.get("calorie") or 
                              data.get("total_calories") or 0)
                    
                    if isinstance(calories, (int, float)) and calories > 0:
                        logger.info(f"사용자 {user_id}의 오늘({today}) 칼로리: {calories}kcal")
                        return float(calories)
                    else:
                        logger.info(f"사용자 {user_id}의 오늘({today}) 식사 기록 없거나 칼로리 0: {data}")
                        # 식사 기록이 없을 때 0 반환
                        return 0.0
                        
                elif response.status_code == 404:
                    logger.info(f"사용자 {user_id}의 오늘({today}) 식사 기록 없음")
                    return 0.0
                else:
                    logger.warning(f"칼로리 조회 실패: {response.status_code}")
                    return 0.0
                    
        except Exception as e:
            logger.error(f"오늘 칼로리 조회 실패: {str(e)}")
            # 기본값 반환 (평균 성인 하루 권장 칼로리)
            return 2000.0
    
    async def _get_exercises_from_spring(self, token: str) -> List[Dict[str, Any]]:
        """Spring API에서 운동 목록 조회"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.spring_url}/exercises",
                    headers=headers
                )
                response.raise_for_status()
                api_response = response.json()
                # Spring API 응답 구조: {"data": [...]}
                exercises = api_response.get("data", [])
                
                logger.info(f"Spring에서 운동 {len(exercises)}개 조회 완료")
                return exercises
                
        except Exception as e:
            logger.error(f"운동 목록 조회 실패: {str(e)}")
            # 기본 운동 목록 반환
            return [
                {"id": 1, "name": "걷기", "category": "유산소", "calories_per_minute": 5, "difficulty": "초급"},
                {"id": 2, "name": "조깅", "category": "유산소", "calories_per_minute": 10, "difficulty": "중급"},
                {"id": 3, "name": "런닝", "category": "유산소", "calories_per_minute": 15, "difficulty": "고급"},
                {"id": 4, "name": "푸시업", "category": "근력", "calories_per_minute": 8, "difficulty": "중급"},
                {"id": 5, "name": "스쿼트", "category": "근력", "calories_per_minute": 6, "difficulty": "초급"},
                {"id": 6, "name": "플랭크", "category": "코어", "calories_per_minute": 4, "difficulty": "중급"},
                {"id": 7, "name": "버피", "category": "전신", "calories_per_minute": 12, "difficulty": "고급"},
                {"id": 8, "name": "자전거", "category": "유산소", "calories_per_minute": 8, "difficulty": "중급"}
            ]
    
    async def _ai_recommend_exercises(self, daily_calories: float, exercises: List[Dict[str, Any]], user_id: str) -> Dict[str, Any]:
        """LangGraph를 사용한 AI 기반 운동 추천"""
        try:
            logger.info(f"LangGraph 기반 운동 추천 시작: 사용자 {user_id}, 칼로리 {daily_calories}")
            
            # 식사별 상세 정보 (실제로는 Spring API에서 가져올 수 있음)
            meal_breakdown = [
                {"type": "조식", "calories": daily_calories * 0.3 if daily_calories > 0 else 0},
                {"type": "중식", "calories": daily_calories * 0.4 if daily_calories > 0 else 0},
                {"type": "석식", "calories": daily_calories * 0.3 if daily_calories > 0 else 0}
            ]
            
            # LangGraph 상태 초기화
            initial_state: ExerciseRecommendationState = {
                "request_params": {
                    "user_id": user_id,
                    "analysis_date": datetime.now().strftime("%Y-%m-%d")
                },
                "user_calorie_data": {
                    "daily_calories": daily_calories,
                    "meal_breakdown": meal_breakdown
                },
                "available_exercises": exercises,
                "calorie_analysis": {},
                "exercise_selection": {},
                "final_recommendation": {},
                "error_message": ""
            }
            
            # LangGraph 실행
            result = await self.graph.ainvoke(initial_state)
            
            # 에러 체크
            if result["error_message"]:
                logger.error(f"LangGraph 실행 중 오류: {result['error_message']}")
                # 기본 응답 반환
                return self._create_fallback_recommendation(daily_calories, exercises)
            
            # 최종 추천 결과 반환
            final_recommendation = result["final_recommendation"]
            logger.info(f"LangGraph 운동 추천 완료: 사용자 {user_id}")
            
            return final_recommendation
            
        except Exception as e:
            logger.error(f"AI 운동 추천 실패: {str(e)}")
            # 오류 시 기본 추천 반환
            return self._create_fallback_recommendation(daily_calories, exercises)
    
    def _create_fallback_recommendation(self, daily_calories: float, exercises: List[Dict[str, Any]]) -> Dict[str, Any]:
        """AI 추천 실패시 사용할 기본 추천"""
        try:
            import random
            
            # 간단한 추천 로직
            if daily_calories <= 800:
                selected_exercises = [
                    {
                        "id": 1,
                        "title": "목 스트레칭",
                        "category": "STRETCH",
                        "recommended_duration": 3,
                        "description": "목과 어깨 긴장 완화",
                        "method": "천천히 목을 좌우로 돌려주세요",
                        "expected_calories": 9
                    }
                ]
                total_burn = 9
            elif daily_calories <= 1500:
                selected_exercises = [
                    {
                        "id": 2,
                        "title": "가벼운 걷기",
                        "category": "MOVING", 
                        "recommended_duration": 10,
                        "description": "실내에서 가볍게 걷기",
                        "method": "10분간 편안하게 걸어보세요",
                        "expected_calories": 50
                    }
                ]
                total_burn = 50
            else:
                selected_exercises = [
                    {
                        "id": 3,
                        "title": "빠른 걷기",
                        "category": "MOVING",
                        "recommended_duration": 15,
                        "description": "적극적인 칼로리 소모 걷기",
                        "method": "15분간 빠르게 걸어보세요",
                        "expected_calories": 100
                    }
                ]
                total_burn = 100
            
            # 메시지 생성 - 지정된 형식으로만
            message = f"오늘은 {int(daily_calories)}kcal 섭취하셨네요! 이 운동을 통해 {total_burn}kcal만큼 운동해 보아요!"
            
            return {
                "message": message,
                "recommended_exercises": selected_exercises
            }
            
        except Exception as e:
            logger.error(f"기본 추천 생성 실패: {str(e)}")
            return {
                "message": f"오늘은 {int(daily_calories)}kcal 섭취하셨네요! 이 운동을 통해 15kcal만큼 운동해 보아요!",
                "recommended_exercises": [
                    {
                        "id": 1,
                        "title": "간단한 스트레칭",
                        "category": "STRETCH",
                        "recommended_duration": 5,
                        "description": "전신 스트레칭",
                        "method": "5분간 편안하게 스트레칭해보세요",
                        "expected_calories": 15
                    }
                ]
            }

# 전역 서비스 인스턴스
exercise_recommendation_service = ExerciseRecommendationService()