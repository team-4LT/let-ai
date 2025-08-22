from typing import Dict, Any
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

import logging

logger = logging.getLogger(__name__)
from ai_exercise_service.src.ai.exercise.graph.exercise_analysis_graph import exercise_analysis_graph, ExerciseAnalysisState

class ExerciseAnalysisService:
    """운동 분석 서비스"""
    
    def __init__(self):
        self.graph = exercise_analysis_graph
    
    async def analyze_user_fitness(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        사용자 체력 분석 및 개인 맞춤 운동 계획 생성
        
        Args:
            user_data: 사용자 기본 정보
            
        Returns:
            종합 운동 분석 결과
        """
        try:
            logger.info(f"사용자 체력 분석 시작: {user_data.get('user_id', 'unknown')}")
            
            # 초기 상태 생성
            initial_state = ExerciseAnalysisState()
            initial_state.user_data = user_data
            
            # 그래프 실행
            result = await asyncio.to_thread(self.graph.invoke, initial_state)
            
            # 에러 체크
            if result.error_message:
                logger.error(f"운동 분석 중 오류: {result.error_message}")
                return {
                    "success": False,
                    "error": result.error_message,
                    "analysis_result": {}
                }
            
            logger.info("사용자 체력 분석 완료")
            return {
                "success": True,
                "error": "",
                "analysis_result": result.analysis_result
            }
            
        except Exception as e:
            logger.error(f"운동 분석 서비스 오류: {str(e)}")
            return {
                "success": False,
                "error": f"분석 중 오류 발생: {str(e)}",
                "analysis_result": {}
            }
    
    async def get_quick_recommendations(self, fitness_level: str, goals: list, available_time: int) -> Dict[str, Any]:
        """
        빠른 운동 추천
        
        Args:
            fitness_level: 체력 수준 (beginner/intermediate/advanced)
            goals: 운동 목표 리스트
            available_time: 이용 가능 시간 (분)
            
        Returns:
            간단한 운동 추천 결과
        """
        try:
            logger.info("빠른 운동 추천 생성 시작")
            
            quick_user_data = {
                "fitness_level": fitness_level,
                "goals": goals,
                "available_time": available_time,
                "age": 25,  # 기본값
                "weight": 70,  # 기본값
                "height": 170  # 기본값
            }
            
            # 간소화된 분석 실행
            result = await self.analyze_user_fitness(quick_user_data)
            
            if result["success"]:
                # 빠른 추천을 위한 요약 생성
                analysis_result = result["analysis_result"]
                exercise_plan = analysis_result.get("exercise_plan", {})
                
                quick_recommendations = {
                    "recommended_exercises": [],
                    "session_duration": available_time,
                    "weekly_frequency": exercise_plan.get("program_overview", {}).get("weekly_sessions", 3),
                    "difficulty_level": fitness_level,
                    "primary_focus": goals[0] if goals else "전반적 체력 증진"
                }
                
                # 첫 주차 운동만 추출
                weekly_plans = exercise_plan.get("weekly_plans", {})
                if "week_1" in weekly_plans:
                    week1_workouts = weekly_plans["week_1"].get("workouts", [])
                    if week1_workouts:
                        first_workout = week1_workouts[0]
                        quick_recommendations["recommended_exercises"] = first_workout.get("exercises", [])
                
                return {
                    "success": True,
                    "quick_recommendations": quick_recommendations
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"빠른 추천 생성 오류: {str(e)}")
            return {
                "success": False,
                "error": f"추천 생성 중 오류: {str(e)}",
                "quick_recommendations": {}
            }

# 전역 서비스 인스턴스
exercise_analysis_service = ExerciseAnalysisService()