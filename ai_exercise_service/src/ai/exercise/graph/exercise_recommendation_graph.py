from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))

# .env 파일 로드
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../..', '.env'))

import logging
import json
import random

logger = logging.getLogger(__name__)

class ExerciseRecommendationState(TypedDict):
    """운동 추천 상태 관리"""
    request_params: Dict[str, Any]
    user_calorie_data: Dict[str, Any]
    available_exercises: List[Dict[str, Any]]
    calorie_analysis: Dict[str, Any]
    exercise_selection: Dict[str, Any]
    final_recommendation: Dict[str, Any]
    error_message: str

# LLM 초기화
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

def analyze_calorie_intake_node(state: ExerciseRecommendationState) -> Dict[str, Any]:
    """칼로리 섭취량 분석 노드"""
    try:
        logger.info("칼로리 섭취량 분석 시작")
        
        daily_calories = state["user_calorie_data"].get("daily_calories", 0)
        meal_breakdown = state["user_calorie_data"].get("meal_breakdown", [])
        
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "당신은 영양학 전문가입니다. 사용자의 일일 칼로리 섭취량을 분석하여 운동 필요성을 평가하세요."
             "\n\n분석 기준:"
             "\n- 성인 기초대사율: 1500kcal"
             "\n- 권장 일일 칼로리: 1800-2200kcal"
             "\n- 운동을 통한 칼로리 소모 필요성 판단"
             "\n- 사용자의 건강상태 고려"),
            ("human",
             "오늘 총 섭취 칼로리: {daily_calories}kcal\n"
             "식사별 상세 내역: {meal_breakdown}\n\n"
             "위 데이터를 분석하여 다음 JSON 형식으로 평가해주세요:\n"
             "{{\n"
             "  \"intake_status\": \"매우부족/부족/적정/과다/매우과다\",\n"
             "  \"target_burn_calories\": 권장소모칼로리,\n"
             "  \"analysis_reason\": \"상세한 분석 이유\",\n"
             "  \"health_advice\": \"건강 관리 조언\",\n"
             "  \"exercise_intensity\": \"가벼움/보통/적극적\",\n"
             "  \"recommended_duration\": 권장운동시간분\n"
             "}}")
        ])
        
        chain = analysis_prompt | llm
        result = chain.invoke({
            "daily_calories": daily_calories,
            "meal_breakdown": str(meal_breakdown)
        })
        
        # JSON 파싱
        try:
            analysis_json = json.loads(result.content)
            logger.info("칼로리 분석 완료")
            return {"calorie_analysis": analysis_json}
        except json.JSONDecodeError:
            logger.warning("칼로리 분석 JSON 파싱 실패, 기본값 사용")
            # 기본 분석 로직
            if daily_calories == 0:
                intake_status = "매우부족"
                target_burn = 0
                intensity = "가벼움"
                duration = 10
            elif daily_calories <= 800:
                intake_status = "매우부족" 
                target_burn = 30
                intensity = "가벼움"
                duration = 15
            elif daily_calories <= 1500:
                intake_status = "부족"
                target_burn = 50
                intensity = "보통"
                duration = 20
            elif daily_calories <= 2000:
                intake_status = "적정"
                target_burn = 100
                intensity = "보통"
                duration = 25
            else:
                intake_status = "과다"
                target_burn = 150 + (daily_calories - 2000) * 0.3
                intensity = "적극적"
                duration = 30
                
            analysis_json = {
                "intake_status": intake_status,
                "target_burn_calories": target_burn,
                "analysis_reason": f"{daily_calories}kcal 섭취로 {intake_status} 상태",
                "health_advice": "균형잡힌 식단과 적절한 운동을 권장합니다",
                "exercise_intensity": intensity,
                "recommended_duration": duration
            }
            return {"calorie_analysis": analysis_json}
            
    except Exception as e:
        logger.error(f"칼로리 분석 실패: {str(e)}")
        return {"error_message": f"칼로리 분석 오류: {str(e)}"}

def select_exercises_node(state: ExerciseRecommendationState) -> Dict[str, Any]:
    """운동 선택 노드"""
    try:
        logger.info("AI 운동 선택 시작")
        
        analysis = state["calorie_analysis"]
        exercises = state["available_exercises"]
        daily_calories = state["user_calorie_data"].get("daily_calories", 0)
        
        selection_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "당신은 전문 피트니스 트레이너입니다. 사용자의 칼로리 분석 결과를 바탕으로 "
             "가장 적합한 운동을 선택하여 추천하세요."
             "\n\n선택 기준:"
             "\n- 칼로리 소모 목표 달성"
             "\n- 운동 강도와 사용자 상태 적합성"
             "\n- 실현 가능한 운동 시간과 난이도"
             "\n- 다양한 운동 부위 고려"),
            ("human",
             "칼로리 분석 결과:\n{analysis}\n\n"
             "이용 가능한 운동 목록:\n{exercises}\n\n"
             "위 분석과 운동 목록을 바탕으로 최적의 운동 조합을 다음 JSON 형식으로 추천해주세요.\n"
             "운동 데이터 구조: id, category(MOVING/STRETCH/ETC), duration(분), title, description, method\n\n"
             "{{\n"
             "  \"selected_exercises\": [\n"
             "    {{\n"
             "      \"id\": 운동ID,\n"
             "      \"title\": \"운동제목\",\n"
             "      \"category\": \"MOVING/STRETCH/ETC\",\n"
             "      \"recommended_duration\": 추천시간분,\n"
             "      \"description\": \"운동설명\",\n"
             "      \"method\": \"실행방법\",\n"
             "      \"expected_calories\": 예상소모칼로리,\n"
             "      \"selection_reason\": \"선택이유\"\n"
             "    }}\n"
             "  ],\n"
             "  \"total_expected_burn\": 총예상소모칼로리,\n"
             "  \"total_duration\": 총운동시간분,\n"
             "  \"workout_balance\": \"운동균형평가\",\n"
             "  \"difficulty_level\": \"초급/중급/고급\"\n"
             "}}")
        ])
        
        chain = selection_prompt | llm
        result = chain.invoke({
            "analysis": str(analysis),
            "exercises": str(exercises)
        })
        
        # JSON 파싱
        try:
            selection_json = json.loads(result.content)
            logger.info("AI 운동 선택 완료")
            return {"exercise_selection": selection_json}
        except json.JSONDecodeError:
            logger.warning("운동 선택 JSON 파싱 실패, 기본 선택 사용")
            # 기본 운동 선택 로직
            return {"exercise_selection": _fallback_exercise_selection(analysis, exercises, daily_calories)}
            
    except Exception as e:
        logger.error(f"운동 선택 실패: {str(e)}")
        return {"error_message": f"운동 선택 오류: {str(e)}"}

def generate_final_recommendation_node(state: ExerciseRecommendationState) -> Dict[str, Any]:
    """최종 추천 생성 노드"""
    try:
        logger.info("최종 운동 추천 생성 시작")
        
        daily_calories = state["user_calorie_data"].get("daily_calories", 0)
        analysis = state["calorie_analysis"]
        selection = state["exercise_selection"]
        
        recommendation_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "당신은 친근한 피트니스 코치입니다. 사용자에게 따뜻하고 격려하는 톤으로 "
             "운동 추천 메시지를 작성하세요."
             "\n\n메시지 스타일:"
             "\n- 친근하고 격려하는 톤"
             "\n- 구체적인 칼로리 수치 포함"
             "\n- 실행 가능한 동기부여"
             "\n- 간결하지만 따뜻한 표현"),
            ("human",
             "사용자 칼로리 섭취: {daily_calories}kcal\n"
             "분석 결과: {analysis}\n"
             "선택된 운동: {selection}\n\n"
             "위 정보를 바탕으로 다음 형식으로만 메시지를 작성해주세요.\n"
             "정확한 형식: \"오늘은 XXXkcal 섭취하셨네요! 이 운동을 통해 XXkcal만큼 운동해 보아요!\"\n"
             "섭취 칼로리가 0인 경우에도: \"오늘은 0kcal 섭취하셨네요! 이 운동을 통해 XXkcal만큼 운동해 보아요!\"\n"
             "반드시 이 형식만 사용하고 다른 문구는 추가하지 마세요.")
        ])
        
        chain = recommendation_prompt | llm
        result = chain.invoke({
            "daily_calories": daily_calories,
            "analysis": str(analysis),
            "selection": str(selection)
        })
        
        # 메시지 생성
        message = result.content.strip()
        
        # 최종 추천 결과 구성
        final_recommendation = {
            "message": message,
            "recommended_exercises": selection.get("selected_exercises", [])
        }
        
        logger.info("최종 운동 추천 생성 완료")
        return {"final_recommendation": final_recommendation}
        
    except Exception as e:
        logger.error(f"최종 추천 생성 실패: {str(e)}")
        return {"error_message": f"최종 추천 생성 오류: {str(e)}"}

def _fallback_exercise_selection(analysis: Dict[str, Any], exercises: List[Dict[str, Any]], daily_calories: float) -> Dict[str, Any]:
    """AI 파싱 실패시 사용할 기본 운동 선택 로직"""
    try:
        target_burn = analysis.get("target_burn_calories", 50)
        intensity = analysis.get("exercise_intensity", "보통")
        
        # 카테고리별 분류
        moving_exercises = [ex for ex in exercises if ex.get("category") == "MOVING"]
        stretch_exercises = [ex for ex in exercises if ex.get("category") == "STRETCH"]
        etc_exercises = [ex for ex in exercises if ex.get("category") == "ETC"]
        
        selected_exercises = []
        total_burn = 0
        total_duration = 0
        
        # 강도에 따른 운동 선택
        if intensity == "가벼움":
            # 스트레칭 중심
            if stretch_exercises:
                selected = random.sample(stretch_exercises, min(2, len(stretch_exercises)))
                for ex in selected:
                    duration = ex.get("duration", 3)
                    calories = duration * 3
                    selected_exercises.append({
                        "id": ex.get("id"),
                        "title": ex.get("title"),
                        "category": ex.get("category"),
                        "recommended_duration": duration,
                        "description": ex.get("description"),
                        "method": ex.get("method"),
                        "expected_calories": calories,
                        "selection_reason": "가벼운 강도에 적합한 스트레칭"
                    })
                    total_burn += calories
                    total_duration += duration
                    
        elif intensity == "보통":
            # 유산소 + 스트레칭
            if moving_exercises:
                selected = random.sample(moving_exercises, min(1, len(moving_exercises)))
                for ex in selected:
                    duration = ex.get("duration", 5)
                    calories = duration * 8
                    selected_exercises.append({
                        "id": ex.get("id"),
                        "title": ex.get("title"),
                        "category": ex.get("category"),
                        "recommended_duration": duration,
                        "description": ex.get("description"),
                        "method": ex.get("method"),
                        "expected_calories": calories,
                        "selection_reason": "적절한 칼로리 소모를 위한 유산소 운동"
                    })
                    total_burn += calories
                    total_duration += duration
            
            if stretch_exercises:
                selected = random.sample(stretch_exercises, min(2, len(stretch_exercises)))
                for ex in selected:
                    duration = ex.get("duration", 3)
                    calories = duration * 3
                    selected_exercises.append({
                        "id": ex.get("id"),
                        "title": ex.get("title"),
                        "category": ex.get("category"),
                        "recommended_duration": duration,
                        "description": ex.get("description"),
                        "method": ex.get("method"),
                        "expected_calories": calories,
                        "selection_reason": "근육 이완을 위한 스트레칭"
                    })
                    total_burn += calories
                    total_duration += duration
                    
        else:  # 적극적
            # 유산소 중심
            if moving_exercises:
                selected = random.sample(moving_exercises, min(2, len(moving_exercises)))
                for ex in selected:
                    duration = ex.get("duration", 7)
                    calories = duration * 10
                    selected_exercises.append({
                        "id": ex.get("id"),
                        "title": ex.get("title"),
                        "category": ex.get("category"),
                        "recommended_duration": duration,
                        "description": ex.get("description"),
                        "method": ex.get("method"),
                        "expected_calories": calories,
                        "selection_reason": "높은 칼로리 소모를 위한 적극적 운동"
                    })
                    total_burn += calories
                    total_duration += duration
        
        # 운동이 없으면 기본 운동 추가
        if not selected_exercises:
            default_ex = exercises[0] if exercises else {
                "id": 1, "title": "걷기", "category": "MOVING", "duration": 5,
                "description": "기본적인 유산소 운동", "method": "5분간 편안하게 걸어보세요"
            }
            duration = default_ex.get("duration", 5)
            calories = duration * 5
            selected_exercises.append({
                "id": default_ex.get("id"),
                "title": default_ex.get("title"),
                "category": default_ex.get("category"),
                "recommended_duration": duration,
                "description": default_ex.get("description"),
                "method": default_ex.get("method"),
                "expected_calories": calories,
                "selection_reason": "기본 건강 유지 운동"
            })
            total_burn = calories
            total_duration = duration
        
        return {
            "selected_exercises": selected_exercises,
            "total_expected_burn": total_burn,
            "total_duration": total_duration,
            "workout_balance": "균형잡힌 운동 구성",
            "difficulty_level": "초급" if intensity == "가벼움" else ("중급" if intensity == "보통" else "고급")
        }
        
    except Exception as e:
        logger.error(f"기본 운동 선택 실패: {str(e)}")
        return {
            "selected_exercises": [{
                "id": 1,
                "title": "걷기 5분",
                "category": "MOVING", 
                "recommended_duration": 5,
                "description": "가장 기본적인 운동",
                "method": "편안하게 5분간 걸어보세요",
                "expected_calories": 25,
                "selection_reason": "기본 운동"
            }],
            "total_expected_burn": 25,
            "total_duration": 5,
            "workout_balance": "기본 운동",
            "difficulty_level": "초급"
        }

# 그래프 구성
def create_exercise_recommendation_graph():
    """운동 추천 LangGraph 생성"""
    workflow = StateGraph(ExerciseRecommendationState)
    
    # 노드 추가
    workflow.add_node("analyze_calorie_intake", analyze_calorie_intake_node)
    workflow.add_node("select_exercises", select_exercises_node)
    workflow.add_node("generate_final_recommendation", generate_final_recommendation_node)
    
    # 엣지 설정
    workflow.set_entry_point("analyze_calorie_intake")
    workflow.add_edge("analyze_calorie_intake", "select_exercises")
    workflow.add_edge("select_exercises", "generate_final_recommendation")
    workflow.add_edge("generate_final_recommendation", END)
    
    return workflow.compile()

# 전역 그래프 인스턴스
exercise_recommendation_graph = create_exercise_recommendation_graph()