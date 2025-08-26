import asyncio
import httpx
import calendar
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)

class MealDataService:
    def __init__(self):
        self.spring_url = os.getenv("SPRING_SERVER_URL", "http://localhost:8080")
        self.timeout = float(os.getenv("SPRING_API_TIMEOUT", 30.0))
    
    async def get_monthly_meal_data(self, token: str, year: int, month: int) -> Dict[str, Any]:
        """
        Spring API에서 월간 급식 데이터를 수집합니다.
        """
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # 1. 월별 평균 평점 조회
                monthly_rating = await self._get_monthly_rating(client, headers, year, month)
                
                # 2. 메뉴 순위 정보 조회  
                menu_ranks = await self._get_menu_rankings(client, headers)
                
                # 3. 월별 식사율 조회
                meal_rates = await self._get_meal_participation_rates(client, headers)
                
                # 4. 전체 급식 통계를 위한 데이터 (개별 사용자 데이터 제외)
                user_daily_data = []  # 급식 피드백에서는 개별 사용자 데이터 불필요
                
                # 5. 월간 메뉴 조회
                monthly_menus = await self._get_monthly_menus(client, headers, year, month)
                
                # 6. 월별 통계 조회
                monthly_stats = await self._get_monthly_statistics(client, headers, year, month)
                
                # 7. 낮은 참여율 분석
                low_participation = await self._get_low_participation_analysis(client, headers, year, month)
                
                # 종합 데이터 구성
                comprehensive_data = {
                    "monthly_statistics": monthly_stats,
                    "monthly_menus": monthly_menus,
                    "monthly_rating": monthly_rating,
                    "menu_rankings": menu_ranks,
                    "meal_participation_rates": meal_rates,
                    "user_daily_data": user_daily_data,
                    "low_participation_analysis": low_participation
                }
                
                logger.info(f"종합 급식 데이터 수집 완료: {year}년 {month}월")
                return comprehensive_data
                
            except Exception as e:
                logger.error(f"급식 데이터 수집 중 오류 발생: {str(e)}")
                raise
    
    async def _get_monthly_rating(self, client: httpx.AsyncClient, headers: Dict[str, str], year: int, month: int) -> Dict[str, Any]:
        """월별 평균 평점 조회"""
        try:
            response = await client.get(
                f"{self.spring_url}/meal-rating/monthly/{year}/{month}",
                headers=headers
            )
            response.raise_for_status()
            
            # BaseResponse<Double> 구조에서 data 추출
            api_response = response.json()
            return {
                "average_rating": api_response.get("data", 0.0),
                "status": api_response.get("status", ""),
                "message": api_response.get("message", "")
            }
        except Exception as e:
            logger.error(f"월별 평점 조회 실패: {str(e)}")
            return {"average_rating": 0.0}
    
    async def _get_menu_rankings(self, client: httpx.AsyncClient, headers: Dict[str, str]) -> Dict[str, Any]:
        """메뉴 순위 정보 조회 - 페이징 처리"""
        try:
            all_menus = []
            page = 1  # 1부터 시작
            
            while True:
                response = await client.get(
                    f"{self.spring_url}/menu-rank",
                    headers=headers,
                    params={"page": page, "reverse": "true"}
                )
                response.raise_for_status()
                
                data = response.json()
                if not data.get("data", {}).get("menus"):
                    break
                    
                page_data = data["data"]
                current_menus = page_data["menus"]
                all_menus.extend(current_menus)
                
                # 마지막 페이지인지 확인 - 응답에서 받은 메뉴가 없거나 현재 페이지가 총 페이지보다 클 때
                total = page_data.get("total", 0)
                current_page = page_data.get("page", page)
                page_size = page_data.get("size", len(current_menus))
                
                if not current_menus or (page_size > 0 and current_page >= (total + page_size - 1) // page_size):
                    break
                    
                page += 1
            
            return {
                "data": {
                    "menus": all_menus,
                    "total": len(all_menus)
                },
                "status": 200,
                "message": "메뉴 순위 조회 성공"
            }
            
        except Exception as e:
            logger.error(f"메뉴 순위 조회 실패: {str(e)}")
            return {}
    
    async def _get_meal_participation_rates(self, client: httpx.AsyncClient, headers: Dict[str, str]) -> Dict[str, Any]:
        """월별 식사율 조회"""
        try:
            response = await client.get(
                f"{self.spring_url}/eater/month/meal-rate/all",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"식사율 조회 실패: {str(e)}")
            return {}
    
    async def _get_user_daily_data(self, client: httpx.AsyncClient, headers: Dict[str, str], user_id: str, year: int, month: int) -> List[Dict[str, Any]]:
        """사용자별 일일 데이터 수집 (한 달치)"""
        user_daily_data = []
        
        # 해당 월의 일수 계산
        _, last_day = calendar.monthrange(year, month)
        
        for day in range(1, last_day + 1):
            try:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                response = await client.get(
                    f"{self.spring_url}/eater/user/{user_id}/date/{date_str}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    daily_data = response.json()
                    daily_data["date"] = date_str
                    user_daily_data.append(daily_data)
                    
            except Exception as e:
                logger.warning(f"일일 데이터 조회 실패 ({year}-{month:02d}-{day:02d}): {str(e)}")
                continue
        
        logger.info(f"사용자 {user_id}의 일일 데이터 {len(user_daily_data)}개 수집 완료")
        return user_daily_data
    
    async def _get_monthly_menus(self, client: httpx.AsyncClient, headers: Dict[str, str], year: int, month: int) -> Dict[str, Any]:
        """월간 메뉴 조회 - 조식/중식/석식 각각 호출"""
        try:
            all_menus = {}
            meal_types = ["조식", "중식", "석식"]  # 한국어 엔드포인트 사용
            
            for meal_type in meal_types:
                try:
                    response = await client.get(
                        f"{self.spring_url}/mealMenu/{meal_type}",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        menu_data = response.json()
                        all_menus[meal_type] = menu_data
                        logger.info(f"{meal_type} 메뉴 조회 성공")
                    else:
                        logger.warning(f"{meal_type} 메뉴 조회 실패: {response.status_code}")
                        all_menus[meal_type] = {}
                        
                except Exception as e:
                    logger.error(f"{meal_type} 메뉴 조회 중 오류: {str(e)}")
                    all_menus[meal_type] = {}
            
            return all_menus
            
        except Exception as e:
            logger.error(f"월간 메뉴 조회 실패: {str(e)}")
            return {}
    
    async def _get_monthly_statistics(self, client: httpx.AsyncClient, headers: Dict[str, str], year: int, month: int) -> Dict[str, Any]:
        """월별 통계 조회"""
        try:
            response = await client.get(
                f"{self.spring_url}/statistics/monthly/{year}/{month}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"월별 통계 조회 실패: {str(e)}")
            return {}
    
    async def _get_low_participation_analysis(self, client: httpx.AsyncClient, headers: Dict[str, str], year: int, month: int) -> Dict[str, Any]:
        """낮은 참여율 분석"""
        try:
            period = f"{year:04d}-{month:02d}"
            response = await client.get(
                f"{self.spring_url}/statistics/meal/analysis/low-participation",
                headers=headers,
                params={"period": period}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"낮은 참여율 분석 실패: {str(e)}")
            return {}

# 전역 서비스 인스턴스
meal_data_service = MealDataService()