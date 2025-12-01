#!/bin/bash

# 헬스체크 스크립트
# 특정 포트의 서비스가 정상 작동하는지 확인

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 파라미터: 서비스명, 포트, 경로
SERVICE_NAME=$1
PORT=$2
PATH=${3:-"/"}
MAX_RETRIES=${4:-30}

if [ -z "$SERVICE_NAME" ] || [ -z "$PORT" ]; then
    echo "Usage: $0 <service_name> <port> [path] [max_retries]"
    echo "Example: $0 backend 8001 /api/v1/ 30"
    exit 1
fi

echo -e "${YELLOW}Checking ${SERVICE_NAME} on port ${PORT}...${NC}"

RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s http://localhost:${PORT}${PATH} > /dev/null 2>&1; then
        echo -e "${GREEN}✓ ${SERVICE_NAME} is healthy!${NC}"
        exit 0
    fi

    RETRY_COUNT=$((RETRY_COUNT+1))
    echo -n "."
    sleep 2
done

echo ""
echo -e "${RED}✗ ${SERVICE_NAME} health check failed after ${MAX_RETRIES} retries${NC}"
exit 1
