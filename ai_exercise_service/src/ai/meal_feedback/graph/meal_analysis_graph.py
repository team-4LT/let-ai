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

logger = logging.getLogger(__name__)
from ai_exercise_service.src.util.services.meal_data_service import meal_data_service

class MealAnalysisState(TypedDict):
    """급식 분석 상태 관리"""
    request_params: Dict[str, Any]
    raw_meal_data: Dict[str, Any]
    processed_data: Dict[str, Any]
    nutritional_analysis: Dict[str, Any]
    final_report: Dict[str, Any]
    error_message: str

# LLM 초기화 - 더 창의적인 응답을 위해 temperature 증가
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

async def collect_meal_data_node(state: MealAnalysisState) -> Dict[str, Any]:
    """급식 데이터 수집 노드"""
    try:
        logger.info("급식 데이터 수집 시작")
        
        token = state["request_params"].get("token")
        year = state["request_params"].get("year")
        month = state["request_params"].get("month")
        
        # Spring API에서 월간 급식 데이터 수집
        raw_data = await meal_data_service.get_monthly_meal_data(token, year, month)
        
        logger.info(f"급식 데이터 수집 완료: {year}년 {month}월")
        return {"raw_meal_data": raw_data}
        
    except Exception as e:
        logger.error(f"급식 데이터 수집 실패: {str(e)}")
        return {"error_message": f"데이터 수집 오류: {str(e)}"}

def process_meal_data_node(state: MealAnalysisState) -> Dict[str, Any]:
    """급식 데이터 전처리 노드"""
    try:
        logger.info("급식 데이터 전처리 시작")
        
        processing_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "당신은 데이터 분석 전문 영양사입니다. 급식 데이터를 정확히 분석하여 친근한 말투로 맞춤형 피드백을 작성하세요."
             "\n\n중요 규칙:"
             "\n- 반드시 제공된 실제 데이터의 수치와 메뉴명을 정확히 사용할 것"
             "\n- 일반적인 조언 금지 - 오직 이 데이터에서 나온 구체적 분석만"
             "\n- 친근한 말투: '~에요', '~예요', '~어요' 사용"
             "\n- 인사말 금지, 바로 내용으로 시작"
             "\n\n분석 필수사항:"
             "\n- 정확한 참여율 수치 언급"
             "\n- 구체적인 메뉴명과 점수 언급"  
             "\n- 학년별 차이점 구체적 분석"
             "\n- 특정 날짜의 특이사항 언급"
             "\n- 급식량 평가 분석 (FEW/SUITABLE/MUCH 비율과 식사별 특성)"
             "\n- 데이터 기반 개선안 제시"),
            ("human",
             "급식 데이터:\n{raw_data}\n\n"
             "위 급식 데이터를 정확히 분석해서 친근한 말투('~에요', '~예요')로 맞춤형 피드백을 작성해주세요.\n\n"
             "반드시 포함해야 할 내용:\n"
             "1. 실제 데이터의 구체적인 수치 (참여율, 칼로리, 인기 메뉴 점수 등)\n"
             "2. 실제 메뉴명을 언급한 구체적 분석\n"
             "3. 학년별 참여율 차이에 대한 구체적 언급\n"
             "4. 날짜별 패턴이나 특이사항\n"
             "5. 급식량 평가 분석 (FEW/SUITABLE/MUCH 비율, 식사별 급식량 특성)\n"
             "6. 데이터 기반의 실질적 개선 제안\n\n"
             "중요: 매번 다른 관점으로 분석하고, 일반적인 조언 대신 이 데이터에서만 나올 수 있는 "
             "구체적이고 특별한 인사이트를 제공해주세요. 실제 수치와 메뉴명을 정확히 활용하세요.")
        ])
        
        chain = processing_prompt | llm
        result = chain.invoke({"raw_data": str(state["raw_meal_data"])})
        
        # 자연스러운 텍스트 피드백 저장
        feedback_text = result.content.strip()
        logger.info("급식 피드백 생성 완료")
        
        # AI가 생성한 실제 피드백 저장 (하드코딩된 값 제거)
        processed_data = {
            "feedback_message": feedback_text
        }
        return {"processed_data": processed_data}
        
    except Exception as e:
        logger.error(f"급식 데이터 전처리 실패: {str(e)}")
        return {"error_message": f"데이터 전처리 오류: {str(e)}"}

def analyze_nutrition_node(state: MealAnalysisState) -> Dict[str, Any]:
    """영양 분석 노드"""
    try:
        logger.info("영양 상태 분석 시작")
        
        nutrition_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "당신은 영양학 전문가입니다. 급식 메뉴 데이터를 바탕으로 영양 균형과 품질을 분석하세요."
             "\n\n분석 기준:"
             "\n- 5대 영양소 균형 (탄수화물, 단백질, 지방, 비타민, 무기질)"
             "\n- 연령대별 권장 영양소 충족도"
             "\n- 식품군별 다양성 평가"
             "\n- 건강한 식습관 형성 기여도"),
            ("human",
             "급식 메뉴 및 운영 데이터:\n{meal_data}\n\n"
             "전처리된 분석 데이터:\n{processed_data}\n\n"
             "위 데이터를 바탕으로 영양학적 분석을 다음 JSON 형식으로 제공해주세요:\n"
             "{{\n"
             "  \"nutritional_balance\": {{\n"
             "    \"overall_score\": 전체영양점수1to10,\n"
             "    \"carbohydrate_ratio\": 탄수화물비율퍼센트,\n"
             "    \"protein_ratio\": 단백질비율퍼센트,\n"
             "    \"fat_ratio\": 지방비율퍼센트,\n"
             "    \"balance_assessment\": \"균형상태평가\"\n"
             "  }},\n"
             "  \"calorie_analysis\": {{\n"
             "    \"estimated_daily_calories\": 일일제공칼로리추정,\n"
             "    \"age_appropriate\": \"연령대적절성평가\",\n"
             "    \"portion_size_assessment\": \"분량적절성평가\"\n"
             "  }},\n"
             "  \"food_group_diversity\": {{\n"
             "    \"grain_products\": \"곡물류제공현황\",\n"
             "    \"vegetables\": \"채소류제공현황\",\n"
             "    \"proteins\": \"단백질식품제공현황\",\n"
             "    \"dairy\": \"유제품제공현황\",\n"
             "    \"fruits\": \"과일류제공현황\",\n"
             "    \"diversity_score\": 다양성점수1to10\n"
             "  }},\n"
             "  \"health_impact\": {{\n"
             "    \"positive_aspects\": [\"건강에좋은점들\"],\n"
             "    \"improvement_areas\": [\"개선필요영역들\"],\n"
             "    \"nutritional_goals\": [\"영양목표달성현황들\"]\n"
             "  }},\n"
             "  \"seasonal_considerations\": {{\n"
             "    \"seasonal_foods\": [\"계절식품활용현황\"],\n"
             "    \"freshness_indicators\": \"신선도지표평가\"\n"
             "  }}\n"
             "}}")
        ])
        
        chain = nutrition_prompt | llm
        result = chain.invoke({
            "meal_data": str(state["raw_meal_data"]),
            "processed_data": str(state["processed_data"])
        })
        
        # JSON 파싱 (마크다운 제거 후)
        import json
        try:
            # ```json...``` 마크다운 제거
            content = result.content.strip()
            if content.startswith("```json"):
                content = content[7:]  # ```json 제거
            if content.endswith("```"):
                content = content[:-3]  # ``` 제거
            content = content.strip()
            
            nutrition_json = json.loads(content)
            logger.info("영양 분석 완료")
            return {"nutritional_analysis": nutrition_json}
        except json.JSONDecodeError as e:
            logger.warning(f"영양 분석 JSON 파싱 실패: {result.content[:200]}... 오류: {e}")
            nutritional_analysis = {
                "nutritional_balance": {
                    "overall_score": 7,
                    "balance_assessment": "대체로 균형 잡힌 구성"
                },
                "calorie_analysis": {
                    "estimated_daily_calories": 650,
                    "age_appropriate": "적절한 수준"
                },
                "health_impact": {
                    "positive_aspects": ["다양한 식재료 사용", "균형 잡힌 메뉴 구성"],
                    "improvement_areas": ["채소 섭취 증진 필요"]
                }
            }
            return {"nutritional_analysis": nutritional_analysis}
        
    except Exception as e:
        logger.error(f"영양 분석 실패: {str(e)}")
        return {"error_message": f"영양 분석 오류: {str(e)}"}

def generate_improvement_recommendations_node(state: MealAnalysisState) -> Dict[str, Any]:
    """개선 방안 제안 노드 - 단순화버전"""
    try:
        logger.info("급식 개선 방안 생성 시작")
        
        # JSON 요구하지 않고 직접 AI가 생성한 피드백 사용
        feedback_message = state["processed_data"].get("feedback_message", "급식 데이터를 분석한 결과입니다.")
        
        final_report = {
            "message": feedback_message
        }
        
        logger.info("급식 개선 방안 생성 완료 - AI 피드백 직접 사용")
        return {"final_report": final_report}
        
    except Exception as e:
        logger.error(f"개선 방안 생성 실패: {str(e)}")
        return {"error_message": f"개선 방안 생성 오류: {str(e)}"}

# 그래프 구성
def create_meal_analysis_graph():
    """급식 분석 LangGraph 생성"""
    workflow = StateGraph(MealAnalysisState)
    
    # 노드 추가
    workflow.add_node("collect_meal_data", collect_meal_data_node)
    workflow.add_node("process_data", process_meal_data_node)
    workflow.add_node("analyze_nutrition", analyze_nutrition_node)
    workflow.add_node("generate_recommendations", generate_improvement_recommendations_node)
    
    # 엣지 설정
    workflow.set_entry_point("collect_meal_data")
    workflow.add_edge("collect_meal_data", "process_data")
    workflow.add_edge("process_data", "analyze_nutrition")
    workflow.add_edge("analyze_nutrition", "generate_recommendations")
    workflow.add_edge("generate_recommendations", END)
    
    return workflow.compile()

# 전역 그래프 인스턴스
meal_analysis_graph = create_meal_analysis_graph()