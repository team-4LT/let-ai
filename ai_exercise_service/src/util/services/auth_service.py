from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends
import httpx
import logging
import jwt
import os

logger = logging.getLogger(__name__)

security = HTTPBearer()

class AuthService:
    def __init__(self):
        self.spring_url = os.getenv("SPRING_SERVER_URL", "http://localhost:8080")
        self.timeout = float(os.getenv("SPRING_API_TIMEOUT", 30.0))
    
    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
        """
        Spring 서버의 /users/me API로 토큰을 검증합니다.
        """
        token = credentials.credentials
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.spring_url}/users/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    logger.info("토큰 검증 성공")
                    return token
                else:
                    logger.warning(f"토큰 검증 실패: {response.status_code}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="유효하지 않은 토큰입니다",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                    
        except httpx.RequestError as e:
            logger.error(f"인증 서버 연결 실패: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="인증 서버에 연결할 수 없습니다"
            )
        except Exception as e:
            logger.error(f"토큰 검증 중 오류: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="토큰 검증 중 오류가 발생했습니다"
            )
    
    async def get_user_id_from_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
        """
        Spring 서버의 /users/me API에서 사용자 ID를 가져옵니다.
        """
        token = credentials.credentials
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.spring_url}/users/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    # Spring API 응답 구조: {"data": {"userId": 12, ...}}
                    data = user_data.get("data", {})
                    user_id = data.get("userId") or data.get("id") or data.get("user_id")
                    
                    if not user_id:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="사용자 정보에서 ID를 찾을 수 없습니다"
                        )
                    
                    return str(user_id)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="유효하지 않은 토큰입니다"
                    )
                    
        except httpx.RequestError as e:
            logger.error(f"사용자 정보 조회 실패: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="사용자 정보 서버에 연결할 수 없습니다"
            )
        except Exception as e:
            logger.error(f"사용자 ID 추출 실패: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="사용자 정보 처리 중 오류가 발생했습니다"
            )

# 전역 인증 서비스 인스턴스
auth_service = AuthService()