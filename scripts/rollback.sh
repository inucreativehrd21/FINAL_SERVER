#!/bin/bash

# 롤백 스크립트
# 이전 버전으로 되돌리기

set -e

echo "=========================================="
echo "Starting rollback..."
echo "=========================================="

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 프로젝트 디렉토리
PROJECT_DIR="/home/ec2-user/FINAL_SERVER"

cd $PROJECT_DIR

# 커밋 해시 입력 받기
if [ -z "$1" ]; then
    echo "Recent commits:"
    git log --oneline -10
    echo ""
    echo -e "${YELLOW}Usage: ./rollback.sh <commit-hash>${NC}"
    echo "Example: ./rollback.sh abc123"
    exit 1
fi

COMMIT_HASH=$1

echo -e "${YELLOW}[1/5] Rolling back to commit: $COMMIT_HASH${NC}"
git checkout $COMMIT_HASH

echo -e "${YELLOW}[2/5] Stopping containers...${NC}"
sudo docker-compose down

echo -e "${YELLOW}[3/5] Rebuilding containers...${NC}"
sudo docker-compose up -d --build

echo -e "${YELLOW}[4/5] Waiting for services...${NC}"
sleep 15

echo -e "${YELLOW}[5/5] Checking status...${NC}"
sudo docker-compose ps

echo ""
echo "=========================================="
echo -e "${GREEN}Rollback completed!${NC}"
echo "=========================================="
echo ""
echo "To return to the latest version, run:"
echo "  git checkout main"
echo "  git pull origin main"
echo "  sudo docker-compose up -d --build"
