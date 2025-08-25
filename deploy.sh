#!/bin/bash

# EC2 배포 스크립트
set -e

echo "LET AI Server 배포 시작..."

# Git 저장소 확인 및 최신 코드 가져오기
if [ -d ".git" ]; then
    echo "📥 최신 코드 가져오는 중..."
    git fetch origin
    git reset --hard origin/main
    echo "✅ 최신 코드 업데이트 완료"
else
    echo "❌ Git 저장소가 아닙니다. git clone으로 프로젝트를 가져오세요."
    exit 1
fi

# 환경변수 파일 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다. .env.example을 참고하여 생성하세요."
    exit 1
fi

# Docker가 설치되어 있는지 확인
if ! command -v docker &> /dev/null; then
    echo "Docker가 설치되어 있지 않습니다."
    echo "다음 명령어로 Docker를 설치하세요:"
    echo "curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
    exit 1
fi

# Docker Compose가 설치되어 있는지 확인
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose가 설치되어 있지 않습니다."
    echo "다음 명령어로 Docker Compose를 설치하세요:"
    echo "sudo curl -L \"https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose"
    echo "sudo chmod +x /usr/local/bin/docker-compose"
    exit 1
fi

# 기존 컨테이너 중지 및 제거
echo "기존 컨테이너 정리 중..."
docker-compose down --remove-orphans

# 새로운 이미지 빌드
echo "🔨 Docker 이미지 빌드 중..."
docker-compose build --no-cache

# 컨테이너 시작
echo "🏃 서비스 시작 중..."
docker-compose up -d

# 서비스 상태 확인
echo "⏳ 서비스 시작 대기 중..."
sleep 10

# 헬스 체크
if curl -f http://127.0.0.1:8001/health > /dev/null 2>&1; then
    echo "서비스가 성공적으로 시작되었습니다!"
    echo "서비스 URL: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8001"
    echo "헬스 체크: http://127.0.0.1:8001/health"
    echo "API 문서: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8001/docs"
else
    echo "❌ 서비스 시작에 실패했습니다. 로그를 확인하세요:"
    echo "docker-compose logs"
    exit 1
fi

echo "🎉 배포 완료!"