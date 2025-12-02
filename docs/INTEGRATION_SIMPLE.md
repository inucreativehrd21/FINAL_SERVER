# 팀원 코드 통합 계획 (간소화)

**작성일:** 2025-12-02
**전제:** Hint AI는 RunPod에서 독립 실행 (RAG 챗봇처럼)
**목표:** 프론트/백엔드/DB만 설정하여 Hint AI와 통신

---

## 🎯 통합 범위

### ✅ 해야 할 것
1. **DB 스키마 업데이트** - 새 테이블 및 필드 추가
2. **백엔드 API 추가** - Hint AI와 통신하는 엔드포인트
3. **프론트엔드 페이지 통합** - 새 기능 UI
4. **환경변수 설정** - Hint AI URL 연결

### ❌ 하지 않을 것
- Hint Service 배포 (이미 RunPod에서 실행 중)
- LangGraph 로직 작성 (팀원이 이미 구현)
- vLLM 설정 (RunPod에서 관리)

---

## 📦 Phase 1: DB 스키마 통합 (필수)

### 1.1 마이그레이션 파일 복사

```bash
# 6개 마이그레이션 복사
cp /home/ec2-user/TEAMMATE_REPO/backend/apps/coding_test/migrations/0014_*.py \
   /home/ec2-user/FINAL_SERVER/backend/apps/coding_test/migrations/

cp /home/ec2-user/TEAMMATE_REPO/backend/apps/coding_test/migrations/0015_*.py \
   /home/ec2-user/FINAL_SERVER/backend/apps/coding_test/migrations/

cp /home/ec2-user/TEAMMATE_REPO/backend/apps/coding_test/migrations/0016_*.py \
   /home/ec2-user/FINAL_SERVER/backend/apps/coding_test/migrations/

cp /home/ec2-user/TEAMMATE_REPO/backend/apps/coding_test/migrations/0017_*.py \
   /home/ec2-user/FINAL_SERVER/backend/apps/coding_test/migrations/

cp /home/ec2-user/TEAMMATE_REPO/backend/apps/coding_test/migrations/0018_*.py \
   /home/ec2-user/FINAL_SERVER/backend/apps/coding_test/migrations/

cp /home/ec2-user/TEAMMATE_REPO/backend/apps/coding_test/migrations/0019_*.py \
   /home/ec2-user/FINAL_SERVER/backend/apps/coding_test/migrations/
```

### 1.2 models.py 병합

**핵심 변경사항:**
1. **ProblemStatus** - 사용자별 문제 진행 상태 (별점 0-3)
2. **HintEvaluation** - 힌트 품질 평가 저장
3. **Submission** - 12개 메트릭 필드 추가
4. **HintRequest** - Hint AI 요청/응답 필드 추가

```bash
# TEAMMATE_REPO의 models.py를 참고하여 FINAL_SERVER의 models.py에 추가
# 자동 복사 금지! 수동으로 모델 정의 추가
```

### 1.3 마이그레이션 실행

```bash
# DB 백업 먼저!
docker exec hint_system_db mysqldump -u hint_user -p hint_system > backup.sql

# 마이그레이션
python manage.py migrate coding_test 0014
python manage.py migrate coding_test 0015
python manage.py migrate coding_test 0016
python manage.py migrate coding_test 0017
python manage.py migrate coding_test 0018
python manage.py migrate coding_test 0019

# 확인
python manage.py showmigrations coding_test
```

---

## 🔌 Phase 2: 백엔드 Hint AI 통신 설정

### 2.1 필요한 파일만 복사

```bash
# hint_proxy.py - Hint AI와 HTTP 통신 담당
cp /home/ec2-user/TEAMMATE_REPO/backend/apps/coding_test/hint_proxy.py \
   /home/ec2-user/FINAL_SERVER/backend/apps/coding_test/

# submission_api.py - 12-메트릭 제출 처리
cp /home/ec2-user/TEAMMATE_REPO/backend/apps/coding_test/submission_api.py \
   /home/ec2-user/FINAL_SERVER/backend/apps/coding_test/
```

**hint_proxy.py 핵심 로직:**
```python
# RunPod Hint AI로 HTTP POST 요청
response = requests.post(
    f"{settings.RUNPOD_HINT_URL}/api/v1/hint",
    json={
        "problem_id": problem_id,
        "user_code": user_code,
        "star_count": star_count,
        # ... 기타 데이터
    },
    timeout=30
)

# 응답 받아서 HintRequest DB에 저장
hint_request = HintRequest.objects.create(
    user=request.user,
    problem=problem,
    user_code=user_code,
    hint_content=response.json()['hint'],
    hint_branch=response.json()['hint_branch'],
    # ...
)
```

### 2.2 urls.py에 라우트 추가

```python
# FINAL_SERVER/backend/apps/coding_test/urls.py

from .hint_proxy import hint_proxy_view
from .submission_api import submission_create_view

urlpatterns = [
    # 기존 라우트 유지...

    # Hint AI 통신
    path('hints/request/', hint_proxy_view, name='hint_request'),

    # 새 제출 API (12-메트릭)
    path('submit/', submission_create_view, name='submit'),

    # 문제 상태 조회
    path('problem-statuses/', problem_status_list, name='problem_statuses'),
]
```

### 2.3 환경변수 설정

```bash
# .env에 추가

# Hint AI RunPod URL (팀원이 제공)
RUNPOD_HINT_URL=https://xxxxx-8080.proxy.runpod.net

# 필요시 인증 키 (있다면)
RUNPOD_HINT_API_KEY=
```

### 2.4 views.py 수정 (settings 추가)

```python
# FINAL_SERVER/backend/config/settings.py

# Hint AI Configuration
RUNPOD_HINT_URL = os.environ.get('RUNPOD_HINT_URL', '')
```

---

## 🎨 Phase 3: 프론트엔드 통합

### 3.1 새 페이지/컴포넌트 비교

**현재 vs 팀원:**
- AdminPanel: 있음 vs **업데이트**
- Chatbot: 있음 vs 동일
- CodingTest: 있음 vs **업데이트** (힌트 버튼 추가)
- KakaoCallback: 없음 vs **추가**
- Problems: 있음 vs **업데이트** (별점 표시)
- 기타: 대부분 동일

### 3.2 중요 변경사항 확인

```bash
# CodingTest 페이지 비교 (힌트 요청 로직)
diff /home/ec2-user/FINAL_SERVER/frontend/src/pages/CodingTest/index.jsx \
     /home/ec2-user/TEAMMATE_REPO/frontend/src/pages/CodingTest/index.jsx

# Problems 페이지 비교 (별점 표시)
diff /home/ec2-user/FINAL_SERVER/frontend/src/pages/Problems/index.jsx \
     /home/ec2-user/TEAMMATE_REPO/frontend/src/pages/Problems/index.jsx
```

### 3.3 힌트 요청 로직 예시

```javascript
// CodingTest/index.jsx

const handleHintRequest = async () => {
  try {
    const response = await api.post('/coding-test/hints/request/', {
      problem_id: currentProblem.id,
      user_code: code,
      hint_level: 'medium'
    })

    if (response.data.success) {
      setHint(response.data.hint)
      setHintBranch(response.data.hint_branch)  // A, B, C, D, E, F
      // 힌트 표시
    }
  } catch (error) {
    console.error('Hint request failed:', error)
  }
}
```

### 3.4 별점 표시 로직 예시

```javascript
// Problems/index.jsx

const ProblemCard = ({ problem, userStatus }) => (
  <div className="problem-card">
    <h3>{problem.title}</h3>
    <div className="stars">
      {/* 0-3 별 표시 */}
      {'⭐'.repeat(userStatus?.star_count || 0)}
      {'☆'.repeat(3 - (userStatus?.star_count || 0))}
    </div>
    {userStatus?.status === 'solved' && (
      <span className="badge">✓ Solved</span>
    )}
  </div>
)
```

---

## 🧪 Phase 4: 통합 테스트

### 4.1 Hint AI 통신 테스트

```bash
# 1. Hint AI RunPod 상태 확인
curl https://[HINT_AI_URL]/health

# 예상 응답:
# {"status": "healthy", "model": "ready"}

# 2. Django에서 힌트 요청 테스트
curl -X POST http://localhost:8000/api/v1/coding-test/hints/request/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "problem_id": 1,
    "user_code": "def solution():\n    pass",
    "hint_level": "medium"
  }'

# 예상 응답:
# {
#   "success": true,
#   "hint": "함수의 반환값을 확인해보세요...",
#   "hint_branch": "B",
#   "static_metrics": {...},
#   "llm_metrics": {...}
# }
```

### 4.2 제출 및 별점 테스트

```bash
# 1. 코드 제출
curl -X POST http://localhost:8000/api/v1/coding-test/submit/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "problem_id": 1,
    "code": "def solution(n):\n    return n * 2"
  }'

# 예상 응답:
# {
#   "success": true,
#   "result": "passed",
#   "star_count": 2,  # 0-3 stars
#   "metrics": {
#     "test_pass_rate": 100,
#     "code_quality_score": 75,
#     # ... 12개 메트릭
#   }
# }

# 2. 문제 상태 조회
curl http://localhost:8000/api/v1/coding-test/problem-statuses/ \
  -H "Authorization: Bearer $TOKEN"

# 예상 응답:
# [
#   {
#     "problem_id": 1,
#     "status": "solved",
#     "star_count": 2,
#     "best_score": 75
#   }
# ]
```

---

## 🚀 Phase 5: 배포

### 5.1 통합 순서

```bash
# 1. 백엔드 통합
cd /home/ec2-user/FINAL_SERVER

# models.py 수정 (수동)
# - ProblemStatus 추가
# - HintEvaluation 추가
# - Submission 필드 추가
# - HintRequest 필드 추가

# 마이그레이션 복사
cp /home/ec2-user/TEAMMATE_REPO/backend/apps/coding_test/migrations/0014_*.py backend/apps/coding_test/migrations/
# ... 0015-0019 동일

# API 파일 복사
cp /home/ec2-user/TEAMMATE_REPO/backend/apps/coding_test/hint_proxy.py backend/apps/coding_test/
cp /home/ec2-user/TEAMMATE_REPO/backend/apps/coding_test/submission_api.py backend/apps/coding_test/

# urls.py 수정 (수동)
# serializers.py 수정 (수동)

# 2. 프론트엔드 통합
# CodingTest/index.jsx 업데이트 (힌트 요청 로직)
# Problems/index.jsx 업데이트 (별점 표시)
# KakaoCallback 추가 (있다면)

# 3. 환경변수 설정
echo "RUNPOD_HINT_URL=https://xxxxx-8080.proxy.runpod.net" >> .env

# 4. 의존성 추가
echo "langgraph>=0.0.30" >> backend/requirements.txt
echo "langchain-core>=0.1.0" >> backend/requirements.txt

# 5. Git 커밋
git add -A
git commit -m "Integrate teammate repo: Hint AI, 12-metrics, ProblemStatus"

# 6. 배포
git push origin main
# → 자동으로 무중단 배포 실행
```

### 5.2 배포 후 확인

```bash
# 1. 마이그레이션 상태
docker exec hint_system_backend_green python manage.py showmigrations coding_test

# 2. Hint AI 연결 테스트
docker exec hint_system_backend_green python manage.py shell
>>> from apps.coding_test.hint_proxy import test_hint_connection
>>> test_hint_connection()
# 성공 시: "Hint AI connection OK"

# 3. 프론트엔드 접속
# - 문제 목록에서 별점 표시 확인
# - 코딩 테스트에서 힌트 버튼 클릭 → 힌트 표시 확인
# - 제출 후 별점 업데이트 확인
```

---

## 📋 체크리스트

### Phase 1: DB (완료 시 ✓)
- [ ] 마이그레이션 파일 6개 복사
- [ ] models.py 병합 (ProblemStatus, HintEvaluation, 필드 추가)
- [ ] DB 백업
- [ ] 마이그레이션 실행 (0014-0019)
- [ ] 테이블 생성 확인

### Phase 2: 백엔드 (완료 시 ✓)
- [ ] hint_proxy.py 복사
- [ ] submission_api.py 복사
- [ ] urls.py 라우트 추가
- [ ] serializers.py 업데이트
- [ ] .env에 RUNPOD_HINT_URL 추가
- [ ] requirements.txt 업데이트

### Phase 3: 프론트엔드 (완료 시 ✓)
- [ ] CodingTest 페이지 힌트 로직 추가
- [ ] Problems 페이지 별점 표시 추가
- [ ] KakaoCallback 추가 (필요시)
- [ ] App.jsx 라우트 업데이트

### Phase 4: 테스트 (완료 시 ✓)
- [ ] Hint AI 연결 테스트
- [ ] 힌트 요청 → 응답 확인
- [ ] 제출 → 12-메트릭 계산 확인
- [ ] 별점 업데이트 확인
- [ ] 기존 기능 회귀 테스트

### Phase 5: 배포 (완료 시 ✓)
- [ ] Git 커밋
- [ ] Git push
- [ ] 무중단 배포 완료
- [ ] 프로덕션 검증

---

## 🔑 핵심 요약

**통합 핵심:**
1. **DB**: 6개 마이그레이션 적용 → ProblemStatus, HintEvaluation, 12-메트릭
2. **백엔드**: hint_proxy.py → RunPod Hint AI와 HTTP 통신
3. **프론트엔드**: 힌트 버튼, 별점 표시
4. **연결**: RUNPOD_HINT_URL 환경변수로 통신

**Hint AI는 이미 RunPod에서 실행 중** ✅
- 우리는 HTTP POST로 요청만 보내면 됨
- RAG 챗봇과 동일한 구조
- 독립적으로 운영됨

**예상 소요 시간:** 2-3일
- Phase 1-2: 1일
- Phase 3: 1일
- Phase 4-5: 1일

---

**작성:** Claude Code
**버전:** 간소화 v1.0
**날짜:** 2025-12-02
