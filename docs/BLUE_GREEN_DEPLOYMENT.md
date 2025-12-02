# Blue-Green 무중단 배포 가이드

## 📋 개요

이 프로젝트는 **Blue-Green 배포 전략**을 사용하여 **완전한 무중단 배포**를 구현합니다.

### 무중단 배포란?

사용자는 배포가 진행되는 동안에도 **서비스 중단을 전혀 체감하지 못합니다**. 새 버전(Green)이 완전히 준비되고 검증된 후에만 트래픽이 전환됩니다.

## 🎯 Blue-Green 배포 동작 방식

```
┌─────────────────────────────────────────────────────────────┐
│                    배포 프로세스                              │
└─────────────────────────────────────────────────────────────┘

1. 현재 상태: Blue 환경에서 서비스 제공 중
   Users → Nginx → Blue (Port 8001, 3001)

2. 새 버전 빌드: Green 환경에 새 코드 배포
   Users → Nginx → Blue (Port 8001, 3001)  ← 계속 서비스 제공
                  Green (Port 8002, 3002)  ← 빌드 및 시작

3. 헬스체크: Green 환경이 정상 작동하는지 확인
   Users → Nginx → Blue (Port 8001, 3001)  ← 계속 서비스 제공
                  Green (Port 8002, 3002)  ← 헬스체크 완료 ✓

4. 트래픽 전환: Nginx upstream을 Green으로 전환 (무중단)
   Users → Nginx → Green (Port 8002, 3002)  ← 트래픽 전환
                  Blue (Port 8001, 3001)   ← 대기

5. 이전 버전 종료: Blue 환경 컨테이너 종료
   Users → Nginx → Green (Port 8002, 3002)  ← 서비스 제공

✅ 다음 배포 시에는 Blue와 Green이 역할 교체
```

## 🔧 핵심 구성 요소

### 1. Docker Compose 파일 분리

#### [docker-compose.blue.yml](docker-compose.blue.yml)
- Backend: 포트 8001
- Frontend: 포트 3001
- Blue 환경 전용 설정

#### [docker-compose.green.yml](docker-compose.green.yml)
- Backend: 포트 8002
- Frontend: 포트 3002
- Green 환경 전용 설정

#### 공유 리소스
- **Database (MySQL)**: 두 환경이 공유
- **Redis**: 두 환경이 공유
- **Volumes**: static, media 파일 공유

### 2. Nginx 동적 Upstream 설정

#### [nginx/upstream.blue.conf](nginx/upstream.blue.conf)
```nginx
upstream backend {
    server host.docker.internal:8001;  # Blue backend
}

upstream frontend {
    server host.docker.internal:3001;  # Blue frontend
}
```

#### [nginx/upstream.green.conf](nginx/upstream.green.conf)
```nginx
upstream backend {
    server host.docker.internal:8002;  # Green backend
}

upstream frontend {
    server host.docker.internal:3002;  # Green frontend
}
```

### 3. 배포 스크립트

#### [scripts/blue-green-deploy.sh](scripts/blue-green-deploy.sh)
무중단 배포를 자동화하는 메인 스크립트:

1. **현재 활성 환경 확인** (`.active_env` 파일)
2. **최신 코드 Pull**
3. **새 환경 빌드 및 시작**
4. **헬스체크 수행** (30회 재시도, 2초 간격)
5. **Nginx upstream 전환**
6. **Nginx 리로드** (무중단)
7. **이전 환경 종료**

#### [scripts/healthcheck.sh](scripts/healthcheck.sh)
서비스 헬스체크 유틸리티 스크립트

## 🚀 사용 방법

### 자동 배포 (GitHub Actions)

```bash
# main 브랜치에 Push하면 자동으로 Blue-Green 배포 실행
git add .
git commit -m "feat: 새로운 기능 추가"
git push origin main
```

### 수동 배포 (서버에서 직접)

```bash
# EC2 인스턴스에 접속
ssh ec2-user@<EC2_IP>

# 프로젝트 디렉토리로 이동
cd /home/ec2-user/FINAL_SERVER

# Blue-Green 배포 실행
./scripts/blue-green-deploy.sh
```

## 📊 배포 프로세스 상세

### 1단계: 환경 확인
```bash
현재 활성 환경: blue
새로 배포할 환경: green
```

### 2단계: 코드 업데이트
```bash
[1/7] Pulling latest code...
Already up to date.
```

### 3단계: 새 환경 빌드
```bash
[2/7] Building and starting green environment...
Building backend_green... ✓
Building frontend_green... ✓
Starting containers... ✓
```

### 4단계: 대기
```bash
[3/7] Waiting for green containers to be ready...
Waiting 20 seconds...
```

### 5단계: 헬스체크
```bash
[4/7] Health checking green environment...
Checking backend on port 8002... ✓ OK
Checking frontend on port 3002... ✓ OK
All health checks passed!
```

### 6단계: 트래픽 전환
```bash
[5/7] Switching Nginx upstream to green...
✓ Nginx configuration test passed

[6/7] Reloading Nginx...
✓ Nginx reloaded successfully
```

### 7단계: 이전 환경 정리
```bash
[7/7] Stopping old blue environment...
Stopping hint_system_backend_blue... done
Stopping hint_system_frontend_blue... done
```

### 완료!
```bash
✓ 무중단 배포 완료!
활성 환경: green
Backend: http://localhost:8002
Frontend: http://localhost:3002
```

## 🔍 현재 상태 확인

### 활성 환경 확인
```bash
cat /home/ec2-user/FINAL_SERVER/.active_env
# 출력: blue 또는 green
```

### 실행 중인 컨테이너 확인
```bash
sudo docker ps --filter "name=hint_system"
```

출력 예시:
```
NAME                          STATUS         PORTS
hint_system_backend_green     Up 5 minutes   0.0.0.0:8002->8000/tcp
hint_system_frontend_green    Up 5 minutes   0.0.0.0:3002->3000/tcp
hint_system_db                Up 2 hours     0.0.0.0:3307->3306/tcp
hint_system_redis             Up 2 hours     0.0.0.0:6379->6379/tcp
hint_system_nginx             Up 2 hours     0.0.0.0:80->80/tcp
```

### Nginx 현재 Upstream 확인
```bash
sudo docker exec hint_system_nginx cat /etc/nginx/conf.d/upstream.conf
```

## 🛡️ 안전장치

### 1. 헬스체크 실패 시 자동 롤백
새 환경의 헬스체크가 실패하면:
- 새 환경 컨테이너 자동 종료
- 기존 환경 계속 서비스 제공
- 에러 메시지 출력 및 배포 중단

```bash
Backend health check failed. Rolling back...
Stopping green environment...
✗ Deployment failed
```

### 2. Nginx 설정 검증
Nginx 설정 테스트 실패 시:
- 이전 upstream 설정으로 복원
- 새 환경 종료
- 배포 중단

```bash
✗ Nginx configuration test failed
Rolling back...
```

### 3. 단계별 검증
각 단계마다 실패 시 즉시 중단되어 서비스 영향 최소화

## 📈 모니터링

### 실시간 로그 확인
```bash
# Blue 환경 로그
sudo docker-compose -f docker-compose.blue.yml logs -f

# Green 환경 로그
sudo docker-compose -f docker-compose.green.yml logs -f

# Nginx 로그
sudo docker logs -f hint_system_nginx
```

### 헬스체크 수동 실행
```bash
# Backend 헬스체크 (포트 8001 또는 8002)
./scripts/healthcheck.sh backend 8001 /api/v1/

# Frontend 헬스체크 (포트 3001 또는 3002)
./scripts/healthcheck.sh frontend 3001 /
```

## 🔄 롤백

### 즉시 롤백 (이전 환경으로)

만약 Green으로 전환 후 문제 발견:

```bash
cd /home/ec2-user/FINAL_SERVER

# 현재 활성 환경 확인
CURRENT_ENV=$(cat .active_env)  # 예: green

# 반대 환경 시작
if [ "$CURRENT_ENV" == "green" ]; then
    sudo docker-compose -f docker-compose.blue.yml up -d
    # Nginx upstream을 blue로 전환
    sudo docker cp nginx/upstream.blue.conf hint_system_nginx:/etc/nginx/conf.d/upstream.conf
    sudo docker exec hint_system_nginx nginx -s reload
    echo "blue" > .active_env
else
    sudo docker-compose -f docker-compose.green.yml up -d
    sudo docker cp nginx/upstream.green.conf hint_system_nginx:/etc/nginx/conf.d/upstream.conf
    sudo docker exec hint_system_nginx nginx -s reload
    echo "green" > .active_env
fi

# Green 환경 종료
sudo docker-compose -f docker-compose.green.yml down
```

### Git 롤백

```bash
# 이전 커밋으로 롤백 후 재배포
git log --oneline -10
./scripts/rollback.sh <commit-hash>
```

## ⚙️ 고급 설정

### 배포 타임아웃 조정

`scripts/blue-green-deploy.sh` 파일에서:
```bash
MAX_RETRIES=30  # 헬스체크 최대 재시도 (기본: 30회)
sleep 2         # 재시도 간격 (기본: 2초)
```

### 대기 시간 조정
```bash
sleep 20  # 컨테이너 시작 후 대기 시간 (기본: 20초)
sleep 3   # Nginx 리로드 후 대기 시간 (기본: 3초)
```

## 🎭 테스트

### 로컬에서 Blue-Green 배포 테스트

```bash
# 1. Blue 환경 시작
sudo docker-compose -f docker-compose.blue.yml up -d

# 2. Green 환경 시작
sudo docker-compose -f docker-compose.green.yml up -d

# 3. 두 환경 모두 정상 작동 확인
curl http://localhost:8001/api/v1/  # Blue backend
curl http://localhost:8002/api/v1/  # Green backend

# 4. 정리
sudo docker-compose -f docker-compose.blue.yml down
sudo docker-compose -f docker-compose.green.yml down
```

## 📚 참고 자료

- [Blue-Green 배포 패턴](https://martinfowler.com/bliki/BlueGreenDeployment.html)
- [Docker Compose 네트워크](https://docs.docker.com/compose/networking/)
- [Nginx Upstream 설정](https://nginx.org/en/docs/http/ngx_http_upstream_module.html)

## 🤝 기여

배포 프로세스 개선 아이디어가 있다면 Issue 또는 PR을 열어주세요!

## ⚠️ 주의사항

1. **데이터베이스 마이그레이션**: Blue와 Green이 같은 DB를 공유하므로 스키마 변경 시 주의 필요
2. **세션 관리**: Redis를 공유하므로 세션 호환성 유지 필요
3. **Static/Media 파일**: 볼륨을 공유하므로 파일명 충돌 주의
4. **포트 충돌**: Blue/Green 환경이 동시에 실행되므로 포트 중복 주의

---

**무중단 배포로 사용자 경험을 극대화하세요!** 🚀
