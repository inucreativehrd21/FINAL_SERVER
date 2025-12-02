# Blue-Green 무중단 배포 설정 체크리스트

## 📋 현재 상태 (2025-12-01)

### ✅ 완료된 설정

#### 1. Docker 환경 구성
- [x] `docker-compose.blue.yml` - Blue 환경 설정
- [x] `docker-compose.green.yml` - Green 환경 설정
- [x] 공유 리소스: MySQL DB, Redis
- [x] 현재 활성 환경: **Green** (포트 8002, 3002)

#### 2. 배포 스크립트
- [x] `scripts/blue-green-deploy.sh` - 7단계 무중단 배포 자동화
- [x] 실행 권한 설정 완료
- [x] 헬스체크 로직 포함
- [x] 롤백 메커니즘 구현

#### 3. Nginx 리버스 프록시
- [x] `nginx/nginx.conf` - 메인 설정
- [x] `nginx/upstream.blue.conf` - Blue 환경 upstream
- [x] `nginx/upstream.green.conf` - Green 환경 upstream
- [x] `nginx/conf.d/upstream.conf` - 현재 활성 upstream (Green)
- [x] 동적 upstream 전환 설정

#### 4. CI/CD 파이프라인
- [x] `.github/workflows/deploy.yml` - GitHub Actions 워크플로우
- [x] main 브랜치 push 시 자동 배포
- [x] 수동 트리거 지원 (workflow_dispatch)
- [x] Git 저장소 연결: https://github.com/inucreativehrd21/FINAL_SERVER.git

#### 5. RAG 챗봇 통합
- [x] Django 모델: `ChatSession`, `ChatMessage`, `ChatBookmark`
- [x] API 엔드포인트: `/api/v1/chatbot/`
  - `POST /api/v1/chatbot/chat/` - 채팅
  - `GET /api/v1/chatbot/sessions/` - 세션 목록
  - `GET /api/v1/chatbot/sessions/<id>/` - 세션 상세
  - `DELETE /api/v1/chatbot/sessions/<id>/delete/` - 세션 삭제
  - `GET /api/v1/chatbot/bookmarks/` - 북마크 목록
  - `POST /api/v1/chatbot/bookmark/` - 북마크 생성
  - `DELETE /api/v1/chatbot/bookmark/<id>/` - 북마크 삭제
- [x] Runpod RAG 서버 URL 설정: `https://oljz12gfyn7riy-8080.proxy.runpod.net`
- [x] 데이터베이스 마이그레이션 완료
- [x] Django Admin 인터페이스 구성

#### 6. 버그 수정
- [x] backend_green 재시작 루프 해결
  - admin.py 파일의 null bytes 오류 수정
  - RUNPOD_RAG_URL에 https:// 프로토콜 추가
- [x] 헬스체크 curl 오류 해결
  - curl → Python urllib로 변경 (Blue/Green 모두)

#### 7. 컨테이너 상태
```
✅ hint_system_backend_green    (healthy)  포트 8002
✅ hint_system_frontend_green   (healthy)  포트 3002
✅ hint_system_db               (healthy)  포트 3307
✅ hint_system_redis            (running)  포트 6379
✅ hint_system_nginx            (running)  포트 80, 443
```

---

## ⚠️ 아직 설정이 필요한 항목

### 1. GitHub Secrets 설정 (필수)

GitHub Actions 자동 배포를 위해 다음 시크릿을 설정해야 합니다:

**설정 위치:** https://github.com/inucreativehrd21/FINAL_SERVER/settings/secrets/actions

#### 필요한 시크릿:

| Secret 이름 | 설명 | 예시 값 |
|------------|------|--------|
| `EC2_HOST` | EC2 인스턴스 IP 주소 또는 도메인 | `3.37.186.224` |
| `EC2_USERNAME` | SSH 접속 사용자명 | `ec2-user` |
| `EC2_SSH_KEY` | EC2 접속용 프라이빗 SSH 키 전체 내용 | `-----BEGIN RSA PRIVATE KEY-----`<br>`MIIEpAIBAAKCA...`<br>`-----END RSA PRIVATE KEY-----` |

#### 설정 방법:
1. GitHub 저장소로 이동
2. **Settings** → **Secrets and variables** → **Actions** 클릭
3. **New repository secret** 버튼 클릭
4. 각 시크릿의 Name과 Value 입력 후 저장

---

### 2. 초기 배포 테스트 (권장)

GitHub Actions를 사용하기 전에 EC2 서버에서 수동으로 배포를 테스트하는 것을 권장합니다:

```bash
cd /home/ec2-user/FINAL_SERVER
./scripts/blue-green-deploy.sh
```

**이 명령이 수행하는 작업:**
1. 현재 활성 환경 확인 (Green)
2. 새로운 환경 결정 (Blue)
3. 최신 코드 pull (`git pull origin main`)
4. Blue 환경 컨테이너 빌드 및 시작
5. 헬스체크 수행 (Backend + Frontend)
6. Nginx upstream을 Blue로 전환 (무중단)
7. 이전 Green 환경 컨테이너 중지
8. `.active_env` 파일 업데이트

**예상 결과:**
- Green → Blue로 전환
- 모든 트래픽이 Blue 환경으로 라우팅
- 이전 Green 컨테이너 중지

---

### 3. 프론트엔드 챗봇 인터페이스 통합 테스트

챗봇 기능이 제대로 동작하는지 확인:

#### 테스트 항목:
- [ ] 프론트엔드에서 챗봇 UI 렌더링 확인
- [ ] 채팅 메시지 전송 테스트 (`POST /api/v1/chatbot/chat/`)
- [ ] Runpod RAG 서버 응답 확인
- [ ] 채팅 세션 생성/조회 테스트
- [ ] 채팅 히스토리 저장 확인
- [ ] 북마크 기능 테스트

#### API 테스트 예시 (cURL):

**1. 채팅 전송 (인증 토큰 필요):**
```bash
curl -X POST http://3.37.186.224/api/v1/chatbot/chat/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Python에서 리스트 컴프리헨션이 뭐야?",
    "session_id": null
  }'
```

**2. 세션 목록 조회:**
```bash
curl -X GET http://3.37.186.224/api/v1/chatbot/sessions/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 🚀 Blue-Green 배포 사용 방법

### 방법 1: GitHub Actions 자동 배포 (권장)

1. **코드 수정 후 커밋 & 푸시:**
```bash
git add .
git commit -m "feat: 새로운 기능 추가"
git push origin main
```

2. **GitHub Actions가 자동으로:**
   - EC2에 SSH 접속
   - `blue-green-deploy.sh` 스크립트 실행
   - 무중단 배포 수행
   - 배포 결과 확인 가능

3. **배포 진행 상황 확인:**
   - https://github.com/inucreativehrd21/FINAL_SERVER/actions

### 방법 2: 수동 배포

```bash
ssh ec2-user@3.37.186.224
cd /home/ec2-user/FINAL_SERVER
./scripts/blue-green-deploy.sh
```

---

## 📊 Blue-Green 배포 동작 원리

### 현재 상태:
```
[사용자] → [Nginx] → [Green Environment]
                       ├─ backend_green  (8002)
                       └─ frontend_green (3002)

[Blue Environment] - 중지됨
```

### 배포 시 전환:
```
1단계: Blue 환경 시작
[사용자] → [Nginx] → [Green Environment] ← 현재 서비스 중

[Blue Environment] ← 새 버전 시작
├─ backend_blue  (8001)
└─ frontend_blue (3001)

2단계: 헬스체크 통과 후 Nginx 전환 (무중단)
[사용자] → [Nginx] → [Blue Environment] ← 서비스 전환!
                     ├─ backend_blue  (8001)
                     └─ frontend_blue (3001)

[Green Environment] ← 중지 예정

3단계: 이전 환경 정리
[사용자] → [Nginx] → [Blue Environment]
                     ├─ backend_blue  (8001)
                     └─ frontend_blue (3001)

[Green Environment] - 중지됨
```

### 다음 배포 시:
- Blue → Green으로 다시 전환
- 이렇게 반복하면서 무중단 배포 수행

---

## 🔍 트러블슈팅

### 배포 실패 시 확인 사항:

1. **컨테이너 상태 확인:**
```bash
sudo docker ps -a --filter "name=hint_system"
```

2. **로그 확인:**
```bash
# Backend 로그
sudo docker logs hint_system_backend_green --tail 100
sudo docker logs hint_system_backend_blue --tail 100

# Frontend 로그
sudo docker logs hint_system_frontend_green --tail 100
sudo docker logs hint_system_frontend_blue --tail 100
```

3. **헬스체크 수동 테스트:**
```bash
# Backend (Green)
curl http://localhost:8002/api/v1/

# Backend (Blue)
curl http://localhost:8001/api/v1/

# Frontend (Green)
curl http://localhost:3002/

# Frontend (Blue)
curl http://localhost:3001/
```

4. **Nginx 설정 테스트:**
```bash
sudo docker exec hint_system_nginx nginx -t
```

5. **현재 활성 환경 확인:**
```bash
cat /home/ec2-user/FINAL_SERVER/.active_env
```

---

## 📝 환경 변수 확인

`.env` 파일에 다음 변수들이 올바르게 설정되어 있는지 확인:

```bash
# Django
DJANGO_SECRET_KEY=...
DEBUG=True
ALLOWED_HOSTS=...

# Database
DB_NAME=hint_system
DB_USER=hint_user
DB_PASSWORD=...
DB_HOST=db
DB_PORT=3306

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# RunPod RAG 챗봇
RUNPOD_RAG_URL=https://oljz12gfyn7riy-8080.proxy.runpod.net

# Frontend
VITE_API_BASE_URL=http://3.37.186.224/api/v1

# CORS
CORS_ALLOWED_ORIGINS=...
```

---

## ✅ 최종 체크리스트

배포 전에 다음 항목을 모두 확인하세요:

- [ ] GitHub Secrets 3개 모두 설정 완료
- [ ] 수동 배포 테스트 1회 이상 성공
- [ ] 모든 컨테이너 healthy 상태 확인
- [ ] Nginx upstream 전환 정상 동작 확인
- [ ] 챗봇 API 엔드포인트 테스트 완료
- [ ] Runpod RAG 서버 연결 테스트 완료
- [ ] 프론트엔드 챗봇 UI 정상 작동 확인
- [ ] .env 파일 모든 필수 변수 설정 확인

---

## 📞 문제 발생 시

1. **배포 스크립트 로그 확인**
2. **Docker 컨테이너 로그 확인**
3. **Nginx 로그 확인:** `/var/log/nginx/`
4. **GitHub Actions 로그 확인**
5. **롤백이 필요한 경우:**
   - 이전 환경 컨테이너가 아직 남아있다면 Nginx upstream만 되돌리기
   - 완전히 중지된 경우 수동으로 이전 환경 재시작

---

**작성일:** 2025-12-01
**마지막 업데이트:** 2025-12-01
**담당자:** Claude Code
