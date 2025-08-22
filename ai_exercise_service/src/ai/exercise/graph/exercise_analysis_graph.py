from typing import Dict, Any, List
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

logger = logging.getLogger(__name__)

class ExerciseAnalysisState:
    """운동 분석 상태 관리"""
    def __init__(self):
        self.user_data: Dict[str, Any] = {}
        self.exercise_recommendations: List[Dict[str, Any]] = []
        self.analysis_result: Dict[str, Any] = {}
        self.error_message: str = ""

# LLM 초기화
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def collect_user_data_node(state: ExerciseAnalysisState) -> ExerciseAnalysisState:
    """사용자 데이터 수집 노드"""
    try:
        logger.info("운동 분석용 사용자 데이터 수집 시작")
        
        # 사용자 기본 정보 수집 (실제로는 API에서 받아올 데이터)
        user_data = {
            "age": state.user_data.get("age", 20),
            "weight": state.user_data.get("weight", 70),
            "height": state.user_data.get("height", 170),
            "fitness_level": state.user_data.get("fitness_level", "beginner"),
            "goals": state.user_data.get("goals", ["체중감량", "근력증가"]),
            "available_time": state.user_data.get("available_time", 30),  # 분
            "medical_conditions": state.user_data.get("medical_conditions", [])
        }
        
        state.user_data = user_data
        logger.info("사용자 데이터 수집 완료")
        return state
        
    except Exception as e:
        logger.error(f"사용자 데이터 수집 실패: {str(e)}")
        state.error_message = f"데이터 수집 오류: {str(e)}"
        return state

def analyze_fitness_level_node(state: ExerciseAnalysisState) -> ExerciseAnalysisState:
    """체력 수준 분석 노드"""
    try:
        logger.info("체력 수준 분석 시작")
        
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "당신은 전문 피트니스 트레이너입니다. 사용자의 기본 정보를 바탕으로 체력 수준과 운동 능력을 분석하세요."
             "\n\n분석 기준:"
             "\n- BMI 계산 및 체형 분석"
             "\n- 나이별 권장 운동 강도"
             "\n- 체력 수준에 따른 운동 계획"
             "\n- 건강 상태 고려사항"),
            ("human", 
             "사용자 정보:\n{user_data}\n\n"
             "위 정보를 바탕으로 다음 JSON 형식으로 분석 결과를 제공해주세요:\n"
             "{{\n"
             "  \"bmi\": BMI수치,\n"
             "  \"body_type\": \"저체중/정상/과체중/비만\",\n"
             "  \"fitness_assessment\": \"초급/중급/고급\",\n"
             "  \"recommended_intensity\": \"낮음/보통/높음\",\n"
             "  \"weekly_frequency\": 주당운동횟수,\n"
             "  \"session_duration\": 회당운동시간분,\n"
             "  \"focus_areas\": [\"중점운동영역들\"],\n"
             "  \"precautions\": [\"주의사항들\"]\n"
             "}}")
        ])
        
        chain = analysis_prompt | llm
        result = chain.invoke({"user_data": str(state.user_data)})
        
        # JSON 파싱
        import json
        try:
            analysis_json = json.loads(result.content)
            state.user_data["fitness_analysis"] = analysis_json
            logger.info("체력 수준 분석 완료")
        except json.JSONDecodeError:
            logger.warning("JSON 파싱 실패, 기본값 사용")
            state.user_data["fitness_analysis"] = {
                "bmi": 23.5,
                "body_type": "정상",
                "fitness_assessment": "중급",
                "recommended_intensity": "보통",
                "weekly_frequency": 3,
                "session_duration": 45,
                "focus_areas": ["전신운동", "유산소"],
                "precautions": ["준비운동 필수"]
            }
        
        return state
        
    except Exception as e:
        logger.error(f"체력 수준 분석 실패: {str(e)}")
        state.error_message = f"체력 분석 오류: {str(e)}"
        return state

def generate_exercise_plan_node(state: ExerciseAnalysisState) -> ExerciseAnalysisState:
    """운동 계획 생성 노드"""
    try:
        logger.info("개인맞춤 운동 계획 생성 시작")
        
        # 기본 운동 목록 (실제로는 Spring API에서 가져올 수 있음)
        sample_exercises = [
            {"name": "푸시업", "category": "근력운동", "difficulty": "중급", "calories_per_minute": 8},
            {"name": "스쿼트", "category": "근력운동", "difficulty": "초급", "calories_per_minute": 6},
            {"name": "런닝", "category": "유산소", "difficulty": "중급", "calories_per_minute": 12},
            {"name": "플랭크", "category": "코어", "difficulty": "중급", "calories_per_minute": 5},
            {"name": "버피", "category": "전신", "difficulty": "고급", "calories_per_minute": 15}
        ]
        
        plan_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "당신은 개인 트레이너입니다. 사용자의 체력 분석 결과와 이용 가능한 운동들을 바탕으로 "
             "맞춤형 운동 계획을 수립하세요."
             "\n\n계획 수립 기준:"
             "\n- 사용자의 체력 수준과 목표에 맞는 운동 선택"
             "\n- 점진적 강도 증가 원칙"
             "\n- 다양한 근육군 균형적 발달"
             "\n- 부상 방지를 위한 안전성 고려"),
            ("human",
             "사용자 분석 결과:\n{analysis_data}\n\n"
             "이용 가능한 운동 목록:\n{exercise_list}\n\n"
             "위 정보를 바탕으로 4주간의 운동 계획을 다음 JSON 형식으로 작성해주세요:\n"
             "{{\n"
             "  \"program_overview\": {{\n"
             "    \"duration_weeks\": 4,\n"
             "    \"weekly_sessions\": 주당횟수,\n"
             "    \"session_duration_minutes\": 회당시간,\n"
             "    \"primary_goals\": [\"주요목표들\"],\n"
             "    \"difficulty_progression\": \"점진적증가방식\"\n"
             "  }},\n"
             "  \"weekly_plans\": {{\n"
             "    \"week_1\": {{\n"
             "      \"focus\": \"1주차집중영역\",\n"
             "      \"workouts\": [\n"
             "        {{\n"
             "          \"day\": \"월요일\",\n"
             "          \"exercises\": [\n"
             "            {{\"name\": \"운동명\", \"sets\": 세트수, \"reps\": \"반복수또는시간\", \"rest_seconds\": 휴식시간}}\n"
             "          ]\n"
             "        }}\n"
             "      ]\n"
             "    }},\n"
             "    \"week_2\": {{...}},\n"
             "    \"week_3\": {{...}},\n"
             "    \"week_4\": {{...}}\n"
             "  }},\n"
             "  \"nutrition_tips\": [\"영양관리팁들\"],\n"
             "  \"progress_tracking\": {{\"measurement_points\": [\"측정지표들\"]}},\n"
             "  \"safety_guidelines\": [\"안전수칙들\"]\n"
             "}}")
        ])
        
        chain = plan_prompt | llm
        result = chain.invoke({
            "analysis_data": str(state.user_data["fitness_analysis"]),
            "exercise_list": str(sample_exercises)
        })
        
        # JSON 파싱
        import json
        try:
            plan_json = json.loads(result.content)
            state.exercise_recommendations = plan_json
            logger.info("운동 계획 생성 완료")
        except json.JSONDecodeError:
            logger.warning("운동 계획 JSON 파싱 실패, 기본값 사용")
            state.exercise_recommendations = {
                "program_overview": {
                    "duration_weeks": 4,
                    "weekly_sessions": 3,
                    "session_duration_minutes": 45,
                    "primary_goals": ["체력증진", "근력강화"],
                    "difficulty_progression": "점진적 강도 증가"
                },
                "safety_guidelines": ["충분한 준비운동", "본인 페이스 유지", "무리하지 않기"]
            }
        
        return state
        
    except Exception as e:
        logger.error(f"운동 계획 생성 실패: {str(e)}")
        state.error_message = f"운동 계획 생성 오류: {str(e)}"
        return state

def create_final_report_node(state: ExerciseAnalysisState) -> ExerciseAnalysisState:
    """최종 보고서 생성 노드"""
    try:
        logger.info("최종 운동 분석 보고서 생성 시작")
        
        report_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "당신은 피트니스 전문가입니다. 사용자의 체력 분석과 운동 계획을 바탕으로 "
             "종합적인 피트니스 보고서를 작성하세요."
             "\n\n보고서 작성 원칙:"
             "\n- 전문적이면서도 이해하기 쉬운 설명"
             "\n- 실행 가능한 구체적 가이드라인"
             "\n- 동기부여가 되는 긍정적 메시지"
             "\n- 안전한 운동을 위한 주의사항 강조"),
            ("human",
             "사용자 기본 정보:\n{user_data}\n\n"
             "체력 분석 결과:\n{fitness_analysis}\n\n"
             "운동 계획:\n{exercise_plan}\n\n"
             "위 모든 정보를 종합하여 다음 JSON 형식의 종합 피트니스 보고서를 작성해주세요:\n"
             "{{\n"
             "  \"executive_summary\": \"전체요약\",\n"
             "  \"user_profile\": {{\n"
             "    \"current_status\": \"현재상태평가\",\n"
             "    \"strengths\": [\"강점들\"],\n"
             "    \"improvement_areas\": [\"개선영역들\"]\n"
             "  }},\n"
             "  \"fitness_goals\": {{\n"
             "    \"short_term\": [\"단기목표들\"],\n"
             "    \"long_term\": [\"장기목표들\"],\n"
             "    \"success_metrics\": [\"성공지표들\"]\n"
             "  }},\n"
             "  \"recommended_program\": {{\n"
             "    \"program_type\": \"프로그램유형\",\n"
             "    \"key_benefits\": [\"주요효과들\"],\n"
             "    \"expected_timeline\": \"예상기간\"\n"
             "  }},\n"
             "  \"lifestyle_recommendations\": {{\n"
             "    \"daily_habits\": [\"일상습관권장사항들\"],\n"
             "    \"nutrition_focus\": [\"영양관리포인트들\"],\n"
             "    \"recovery_tips\": [\"회복관리팁들\"]\n"
             "  }},\n"
             "  \"motivation_message\": \"격려메시지\",\n"
             "  \"next_steps\": [\"다음단계행동계획들\"]\n"
             "}}")
        ])
        
        chain = report_prompt | llm
        result = chain.invoke({
            "user_data": str(state.user_data),
            "fitness_analysis": str(state.user_data.get("fitness_analysis", {})),
            "exercise_plan": str(state.exercise_recommendations)
        })
        
        # JSON 파싱
        import json
        import pandas as pd
        try:
            report_json = json.loads(result.content)
            state.analysis_result = {
                "user_analysis": state.user_data,
                "exercise_plan": state.exercise_recommendations,
                "comprehensive_report": report_json,
                "generated_at": str(pd.Timestamp.now())
            }
            logger.info("최종 보고서 생성 완료")
        except json.JSONDecodeError:
            logger.warning("보고서 JSON 파싱 실패, 기본 보고서 생성")
            state.analysis_result = {
                "user_analysis": state.user_data,
                "exercise_plan": state.exercise_recommendations,
                "comprehensive_report": {
                    "executive_summary": "개인 맞춤형 운동 계획이 수립되었습니다.",
                    "motivation_message": "꾸준한 운동으로 건강한 삶을 만들어보세요!"
                }
            }
        
        return state
        
    except Exception as e:
        logger.error(f"최종 보고서 생성 실패: {str(e)}")
        state.error_message = f"보고서 생성 오류: {str(e)}"
        return state

# 그래프 구성
def create_exercise_analysis_graph():
    """운동 분석 LangGraph 생성"""
    workflow = StateGraph(ExerciseAnalysisState)
    
    # 노드 추가
    workflow.add_node("collect_data", collect_user_data_node)
    workflow.add_node("analyze_fitness", analyze_fitness_level_node)
    workflow.add_node("generate_plan", generate_exercise_plan_node)
    workflow.add_node("create_report", create_final_report_node)
    
    # 엣지 설정
    workflow.set_entry_point("collect_data")
    workflow.add_edge("collect_data", "analyze_fitness")
    workflow.add_edge("analyze_fitness", "generate_plan")
    workflow.add_edge("generate_plan", "create_report")
    workflow.add_edge("create_report", END)
    
    return workflow.compile()

# 전역 그래프 인스턴스
exercise_analysis_graph = create_exercise_analysis_graph()