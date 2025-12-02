#!/bin/bash

# Blue-Green 무중단 배포 스크립트
# 새 버전을 별도 컨테이너로 띄우고, 헬스체크 후 트래픽 전환

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="/home/ec2-user/FINAL_SERVER"
ACTIVE_ENV_FILE="$PROJECT_DIR/.active_env"

cd $PROJECT_DIR

echo "=========================================="
echo -e "${BLUE}Blue-Green 무중단 배포 시작${NC}"
echo "=========================================="

# 현재 활성 환경 확인
if [ -f "$ACTIVE_ENV_FILE" ]; then
    CURRENT_ENV=$(cat $ACTIVE_ENV_FILE)
else
    # 초기 배포시 Blue를 기본으로
    CURRENT_ENV="blue"
    echo "blue" > $ACTIVE_ENV_FILE
fi

echo -e "${YELLOW}현재 활성 환경: ${CURRENT_ENV}${NC}"

# 새로 배포할 환경 결정
if [ "$CURRENT_ENV" == "blue" ]; then
    NEW_ENV="green"
    NEW_BACKEND_PORT=8002
    NEW_FRONTEND_PORT=3002
    OLD_BACKEND_PORT=8001
    OLD_FRONTEND_PORT=3001
else
    NEW_ENV="blue"
    NEW_BACKEND_PORT=8001
    NEW_FRONTEND_PORT=3001
    OLD_BACKEND_PORT=8002
    OLD_FRONTEND_PORT=3002
fi

echo -e "${YELLOW}새로 배포할 환경: ${NEW_ENV}${NC}"
echo ""

# Step 1: 최신 코드 pull
echo -e "${YELLOW}[1/8] Pulling latest code...${NC}"
git pull origin main

# Step 2: 공유 인프라 확인 및 시작 (DB, Redis)
echo -e "${YELLOW}[2/8] Ensuring base infrastructure is running...${NC}"
sudo docker-compose -f docker-compose.base.yml up -d
echo -e "${GREEN}✓ Base infrastructure ready (DB, Redis)${NC}"
sleep 5

# Step 3: 새 환경 컨테이너 빌드 및 시작
echo -e "${YELLOW}[3/8] Building and starting ${NEW_ENV} environment...${NC}"
echo -e "${BLUE}Note: Base infrastructure (DB, Redis) remains running during build${NC}"
sudo docker-compose -f docker-compose.${NEW_ENV}.yml up -d --build

# Step 4: 새 컨테이너가 준비될 때까지 대기
echo -e "${YELLOW}[4/8] Waiting for ${NEW_ENV} containers to be ready...${NC}"
sleep 20

# Step 5: 헬스체크
echo -e "${YELLOW}[5/8] Health checking ${NEW_ENV} environment...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0

# Backend 헬스체크
echo -n "Checking backend on port ${NEW_BACKEND_PORT}... "
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s http://localhost:${NEW_BACKEND_PORT}/api/v1/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}✗ FAILED${NC}"
        echo -e "${RED}Backend health check failed. Rolling back...${NC}"
        sudo docker-compose -f docker-compose.${NEW_ENV}.yml down
        exit 1
    fi
    sleep 2
done

# Frontend 헬스체크
RETRY_COUNT=0
echo -n "Checking frontend on port ${NEW_FRONTEND_PORT}... "
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s http://localhost:${NEW_FRONTEND_PORT}/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}✗ FAILED${NC}"
        echo -e "${RED}Frontend health check failed. Rolling back...${NC}"
        sudo docker-compose -f docker-compose.${NEW_ENV}.yml down
        exit 1
    fi
    sleep 2
done

echo -e "${GREEN}All health checks passed!${NC}"
echo ""

# Step 6: Nginx upstream 설정 변경
echo -e "${YELLOW}[6/8] Switching Nginx upstream to ${NEW_ENV}...${NC}"

# Nginx upstream 설정 파일 교체 (호스트에서 직접 - conf.d가 마운트되어 있음)
sudo cp nginx/upstream.${NEW_ENV}.conf nginx/conf.d/upstream.conf

# Nginx 설정 테스트
if sudo docker exec hint_system_nginx nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration test passed${NC}"
else
    echo -e "${RED}✗ Nginx configuration test failed${NC}"
    echo -e "${RED}Rolling back...${NC}"
    sudo cp nginx/upstream.${CURRENT_ENV}.conf nginx/conf.d/upstream.conf
    sudo docker-compose -f docker-compose.${NEW_ENV}.yml down
    exit 1
fi

# Step 7: Nginx reload (무중단)
echo -e "${YELLOW}[7/8] Reloading Nginx...${NC}"
sudo docker exec hint_system_nginx nginx -s reload
echo -e "${GREEN}✓ Nginx reloaded successfully${NC}"

# 짧은 대기 후 트래픽이 새 환경으로 흐르는지 확인
sleep 3

# Step 8: 이전 환경 컨테이너 중지 (DB/Redis는 유지)
echo -e "${YELLOW}[8/8] Stopping old ${CURRENT_ENV} environment...${NC}"
echo -e "${BLUE}Note: Only stopping ${CURRENT_ENV} app containers (DB, Redis remain running)${NC}"
sudo docker-compose -f docker-compose.${CURRENT_ENV}.yml down

# 활성 환경 업데이트
echo "$NEW_ENV" > $ACTIVE_ENV_FILE

echo ""
echo "=========================================="
echo -e "${GREEN}✓ 무중단 배포 완료!${NC}"
echo "=========================================="
echo -e "활성 환경: ${GREEN}${NEW_ENV}${NC}"
echo -e "Backend: http://localhost:${NEW_BACKEND_PORT}"
echo -e "Frontend: http://localhost:${NEW_FRONTEND_PORT}"
echo ""

# 최종 상태 확인
echo "Running containers:"
sudo docker ps --filter "name=hint_system" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
