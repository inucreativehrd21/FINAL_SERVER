#!/bin/bash

# 배포 스크립트
# EC2 인스턴스에서 실행되는 자동 배포 스크립트

set -e  # 에러 발생시 스크립트 중단

echo "=========================================="
echo "Starting deployment..."
echo "=========================================="

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 프로젝트 디렉토리
PROJECT_DIR="/home/ec2-user/FINAL_SERVER"

# 프로젝트 디렉토리로 이동
cd $PROJECT_DIR

echo -e "${YELLOW}[1/6] Pulling latest code from GitHub...${NC}"
git pull origin main

echo -e "${YELLOW}[2/6] Checking .env file...${NC}"
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ .env file exists${NC}"

echo -e "${YELLOW}[3/6] Stopping existing containers...${NC}"
sudo docker-compose down

echo -e "${YELLOW}[4/6] Building and starting containers...${NC}"
sudo docker-compose up -d --build

echo -e "${YELLOW}[5/6] Waiting for services to be ready...${NC}"
sleep 15

echo -e "${YELLOW}[6/6] Checking container status...${NC}"
sudo docker-compose ps

# 헬스 체크
echo ""
echo "=========================================="
echo "Health Check"
echo "=========================================="

# Backend 헬스 체크
echo -n "Backend: "
if curl -f -s http://localhost:8000/api/v1/ > /dev/null; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
fi

# Frontend 헬스 체크
echo -n "Frontend: "
if curl -f -s http://localhost:3000/ > /dev/null; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
fi

# Database 헬스 체크
echo -n "Database: "
if sudo docker-compose exec -T db mysqladmin ping -h localhost -u root -p"$DB_PASSWORD" --silent > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAILED (check manually)${NC}"
fi

# Redis 헬스 체크
echo -n "Redis: "
if sudo docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Deployment completed!${NC}"
echo "=========================================="

# 최근 로그 출력
echo ""
echo "Recent logs:"
echo "=========================================="
sudo docker-compose logs --tail=30
