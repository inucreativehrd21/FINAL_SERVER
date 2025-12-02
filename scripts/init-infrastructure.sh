#!/bin/bash

# 초기 인프라 설정 스크립트
# 첫 배포 전에 실행하여 공유 리소스(DB, Redis, Network, Volumes) 생성

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="/home/ec2-user/FINAL_SERVER"
cd $PROJECT_DIR

echo "=========================================="
echo -e "${BLUE}초기 인프라 설정 시작${NC}"
echo "=========================================="
echo ""

# Step 1: 환경 변수 파일 확인
echo -e "${YELLOW}[1/3] Checking .env file...${NC}"
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ .env file exists${NC}"
echo ""

# Step 2: 공유 인프라 시작 (DB, Redis, Networks, Volumes)
echo -e "${YELLOW}[2/3] Starting base infrastructure...${NC}"
echo -e "${BLUE}Creating: MySQL, Redis, Networks, Volumes${NC}"
sudo docker-compose -f docker-compose.base.yml up -d

echo ""
echo -e "${YELLOW}Waiting for database to be ready...${NC}"
sleep 15

# Step 3: DB 헬스체크
echo -e "${YELLOW}[3/3] Health checking database...${NC}"
MAX_RETRIES=20
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if sudo docker exec hint_system_db mysqladmin ping -h localhost --silent; then
        echo -e "${GREEN}✓ Database is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}✗ Database health check failed${NC}"
        exit 1
    fi
    sleep 3
done

echo ""
echo "=========================================="
echo -e "${GREEN}✓ 인프라 설정 완료!${NC}"
echo "=========================================="
echo ""
echo "생성된 리소스:"
sudo docker ps --filter "name=hint_system" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "생성된 볼륨:"
sudo docker volume ls | grep final_server
echo ""
echo "생성된 네트워크:"
sudo docker network ls | grep final_server
echo ""
echo -e "${BLUE}이제 Blue-Green 배포를 시작할 수 있습니다:${NC}"
echo "./scripts/blue-green-deploy.sh"
