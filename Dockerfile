FROM python:3.11-slim

WORKDIR /app

# 시스템 종속성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 종속성 복사 및 설치
COPY ai_exercise_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 프로젝트 복사 (Python 경로 문제 해결)
COPY . /app/

# 작업 디렉토리를 ai_exercise_service로 변경
WORKDIR /app/ai_exercise_service

# 포트 노출
EXPOSE 8001

# 애플리케이션 시작
CMD ["python", "main.py"]