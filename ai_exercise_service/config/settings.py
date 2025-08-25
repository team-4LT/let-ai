from pydantic_settings import BaseSettings
from typing import Literal
import os

class Settings(BaseSettings):
    # API 설정
    openai_api_key: str = "your-api-key"
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    
    # Spring 서버 설정
    spring_server_url: str = "http://localhost:8080"
    spring_api_timeout: float = 30.0
    
    # 비즈니스 로직 설정
    min_calorie_intake: float = 800.0
    max_calorie_intake: float = 5000.0
    min_burn_rate: float = 0.05  # 5%
    max_burn_rate: float = 0.25  # 25%
    
    class Config:
        env_file = "../.env"
        case_sensitive = False

# 전역 설정 인스턴스
settings = Settings()