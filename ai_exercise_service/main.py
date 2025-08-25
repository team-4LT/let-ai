from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
import os
from dotenv import load_dotenv

# .env 파일 먼저 로드
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Python path 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'src'))

from config.settings import settings
from src.ai.meal_feedback.router.meal_feedback_router import router as meal_feedback_router
from src.ai.exercise.router.exercise_router import router as exercise_router
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LET AI Server",
    description="AI 기반 급식 및 운동 분석 서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """서비스 상태 확인"""
    return {
        "message": "LET AI Server is running",
        "version": "1.0.0",
        "environment": settings.environment
    }

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "service": "LET AI Server"}

# 라우터 등록
app.include_router(meal_feedback_router)
app.include_router(exercise_router)

if __name__ == "__main__":
    logger.info(f"LET AI Server 시작 - {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    )