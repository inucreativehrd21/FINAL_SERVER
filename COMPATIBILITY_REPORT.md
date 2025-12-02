# RunPod API ↔ EC2 Django 서버 호환성 보고서

**작성일:** 2025-12-02
**RunPod API:** `serve_unified.py` (LangGraph/Optimized RAG)
**EC2 서버:** FINAL_SERVER (Django + React)

---

## ✅ 호환성 요약

**결론**: 현재 EC2 Django 서버는 새로운 RunPod API와 **기본적으로 호환됩니다**.

몇 가지 개선사항만 적용하면 완벽하게 동작합니다.

---

## 1. 요청/응답 구조 비교

### 요청 구조 (Django → RunPod)

| 필드 | Django에서 전송 | RunPod API 기대값 | 호환성 |
|------|----------------|------------------|--------|
| **question** | ✅ `message` | ✅ `question` | ✅ 호환 |
| **user_id** | ✅ `str(request.user.id)` | ✅ `user_id` | ✅ 호환 |
| **chat_history** | ✅ `[{"role": "...", "content": "..."}]` | ✅ `List[ChatMessage]` | ✅ 호환 |
| **session_id** | ✅ `str(session.id)` | ✅ `Optional[session_id]` | ✅ 호환 |

### 응답 구조 (RunPod → Django)

| 필드 | Django 기대값 | RunPod API 제공 | 호환성 |
|------|-------------|----------------|--------|
| **success** | ✅ `bool` | ✅ `bool` | ✅ 호환 |
| **answer** | ✅ `str` | ✅ `str` | ✅ 호환 |
| **sources** | ✅ `list` | ✅ `List[Source]` | ⚠️ 구조 확인 필요 |
| **metadata** | ✅ `dict` (optional) | ✅ `Optional[Dict]` | ✅ 호환 |
| **error** | ✅ `str` (error 시) | ✅ `Optional[str]` | ✅ 호환 |

---

## 2. Sources 필드 구조 차이

### 기존 기대 형식 (이전 RunPod API)

```json
{
    "chunk_id": "python_797",
    "content": "문서 내용...",
    "score": 0.95
}
```

### 새 RunPod API 형식 (`serve_unified.py`)

```json
{
    "content": "문서 내용...",
    "url": "https://git-scm.com/docs/git-rebase",
    "score": null
}
```

**차이점:**
- ❌ `chunk_id` 필드 없음 → ✅ `url` 필드 추가
- ✅ `content`, `score` 필드는 동일

**영향:**
- Django에서 sources를 JSONField로 저장하므로 문제없음
- 프론트엔드에서 sources 렌더링 시 객체 타입 확인 필요

---

## 3. 수정이 필요한 부분

### 🔧 수정 1: 프론트엔드 Sources 렌더링

**파일:** `frontend/src/pages/Chatbot/index.jsx`

**현재 코드 (177-179줄):**
```javascript
{message.sources.map((source, idx) => (
    <li key={idx}>{source}</li>  // ⚠️ source가 객체면 [object Object] 표시
))}
```

**수정 후:**
```javascript
{message.sources.map((source, idx) => (
    <li key={idx}>
        {typeof source === 'string'
            ? source
            : (source.content?.substring(0, 100) || source.chunk_id || 'Source')}
        {source.url && (
            <a href={source.url} target="_blank" rel="noopener noreferrer" className="source-link">
                🔗
            </a>
        )}
    </li>
))}
```

### 🔧 수정 2: 환경변수 호환성

**파일:** `backend/apps/chatbot/views.py`

**현재 코드 (29줄):**
```python
RUNPOD_RAG_URL = os.environ.get('RUNPOD_RAG_URL', '')
```

**수정 후:**
```python
# RUNPOD_RAG_URL 또는 RUNPOD_CHATBOT_URL 지원
RUNPOD_RAG_URL = (
    os.environ.get('RUNPOD_RAG_URL') or
    os.environ.get('RUNPOD_CHATBOT_URL', '')
)
```

### 🔧 수정 3 (선택): 프론트엔드에서 session_id 전송

**파일:** `frontend/src/pages/Chatbot/index.jsx`

**현재 코드 (75-78줄):**
```javascript
const response = await api.post('/chatbot/chat/', {
    message: input,
    history: messages  // ⚠️ Django가 사용하지 않음
})
```

**권장 수정:**
```javascript
const response = await api.post('/chatbot/chat/', {
    message: input,
    session_id: currentSessionId  // 기존 세션 ID 전송
})

// 응답에서 session_id 저장
if (response.data.success && !currentSessionId) {
    setCurrentSessionId(response.data.session_id)
}
```

**이유:**
- Django가 `history` 필드를 사용하지 않고 DB에서 자동 조회
- `session_id` 전송으로 대화 지속성 향상

---

## 4. 완전한 데이터 흐름

```
사용자 브라우저
    ↓
    [React] 메시지 입력
    ↓
    POST /api/v1/chatbot/chat/
    {
        "message": "git rebase란?",
        "session_id": 123  (선택사항)
    }
    ↓
EC2 Django Backend
    ├─ 1. JWT 인증 확인
    ├─ 2. ChatSession 조회/생성
    ├─ 3. ChatMessage(user) DB 저장
    ├─ 4. Chat history 구성 (최근 10개)
    │
    ├─ 5. RunPod 호출:
    │   POST https://xxxxx-8080.proxy.runpod.net/api/v1/chat
    │   {
    │       "question": "git rebase란?",
    │       "user_id": "1",
    │       "chat_history": [
    │           {"role": "user", "content": "..."},
    │           {"role": "assistant", "content": "..."}
    │       ],
    │       "session_id": "123"
    │   }
    │
    ├─ 6. RunPod 응답:
    │   {
    │       "success": true,
    │       "answer": "git rebase는 커밋 히스토리를...",
    │       "sources": [
    │           {
    │               "content": "rebase는 한 브랜치의 변경사항을...",
    │               "url": "https://git-scm.com/docs/git-rebase",
    │               "score": null
    │           }
    │       ],
    │       "metadata": {
    │           "rag_type": "langgraph",
    │           "workflow": ["intent_classifier", "query_router", ...],
    │           "response_time": 8.5
    │       }
    │   }
    │
    ├─ 7. ChatMessage(assistant) DB 저장
    │   - content: "git rebase는 커밋 히스토리를..."
    │   - sources: [{content, url, score}, ...]
    │   - metadata: {rag_type, workflow, response_time}
    │
    └─ 8. 프론트엔드로 응답:
        {
            "success": true,
            "session_id": 123,
            "message_id": 456,
            "data": {
                "response": "git rebase는 커밋 히스토리를...",
                "sources": [{content, url, score}, ...]
            }
        }
        ↓
사용자 브라우저
    └─ [React] 답변 표시 + 출처 링크 표시
```

---

## 5. 테스트 시나리오

### 테스트 1: 기본 채팅

```bash
# 1. 로그인
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}' \
  | jq -r '.access')

# 2. 채팅 (새 세션)
curl -X POST http://localhost:8000/api/v1/chatbot/chat/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "git rebase란?"}' \
  | jq '.'

# 예상 응답:
{
  "success": true,
  "session_id": 1,
  "message_id": 2,
  "data": {
    "response": "git rebase는...",
    "sources": [
      {
        "content": "...",
        "url": "https://...",
        "score": null
      }
    ]
  }
}
```

### 테스트 2: 세션 지속

```bash
# 3. 같은 세션에서 추가 질문
curl -X POST http://localhost:8000/api/v1/chatbot/chat/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "예시 보여줘", "session_id": 1}' \
  | jq '.'
```

### 테스트 3: 에러 처리

```bash
# RunPod 서버 다운 시
{
  "success": false,
  "error": "RAG 서버에 연결할 수 없습니다."
}
```

---

## 6. 환경변수 설정

### Backend `.env`

```bash
# RunPod RAG 서버 URL
RUNPOD_RAG_URL=https://oljz12gfyn7riy-8080.proxy.runpod.net

# 또는
RUNPOD_CHATBOT_URL=https://oljz12gfyn7riy-8080.proxy.runpod.net

# Django Secret Key
SECRET_KEY=your-django-secret-key

# Database
DB_NAME=hint_system
DB_USER=hint_user
DB_PASSWORD=your_password
DB_HOST=db
DB_PORT=3306
```

---

## 7. 배포 체크리스트

### RunPod 설정
- [x] RAG 서버 실행 (`python serve_unified.py --rag-type langgraph --port 8080`)
- [x] 포트 8080 Public 설정
- [x] Health check 성공 (`curl /api/v1/health`)
- [x] Public URL 확인

### EC2 Django 설정
- [ ] 환경변수 설정 (`RUNPOD_RAG_URL`)
- [ ] 코드 수정 (선택사항):
  - [ ] Sources 렌더링 개선
  - [ ] 환경변수 호환성
  - [ ] Session ID 전송
- [ ] Docker 재시작
- [ ] API 테스트

---

## 8. 문제 해결

### 문제 1: Sources가 [object Object]로 표시됨

**원인:** 프론트엔드에서 객체를 문자열로 렌더링

**해결:** 수정 1 적용

### 문제 2: RunPod 연결 실패

**에러:**
```
{
  "success": false,
  "error": "RAG 서버에 연결할 수 없습니다."
}
```

**해결:**
```bash
# RunPod 서버 실행 확인
curl https://xxxxx-8080.proxy.runpod.net/api/v1/health

# 환경변수 확인
docker-compose exec backend env | grep RUNPOD
```

### 문제 3: 답변이 비어있음

**원인:** RunPod API 응답 파싱 오류

**확인:**
```python
# Django 로그 확인
docker-compose logs -f backend | grep RAG

# RunPod 서버 로그 확인
tail -f /workspace/testrag/experiments/rag_pipeline/server.log
```

---

## 9. 성능 최적화

### 타임아웃 설정

**Django views.py (117줄):**
```python
response = requests.post(
    f"{RUNPOD_RAG_URL}/api/v1/chat",
    json=payload,
    timeout=60  # LangGraph는 7-10초 소요
)
```

**권장:**
- Optimized RAG: `timeout=30`
- LangGraph RAG: `timeout=90`

### 비동기 처리 (선택사항)

프로덕션 환경에서는 Celery로 비동기 처리:

```python
@shared_task
def process_rag_request(question, user_id, chat_history):
    # RunPod 호출
    response = requests.post(...)
    return response.json()
```

---

## 10. 결론

**현재 상태:**
✅ Django 서버와 RunPod API는 기본적으로 호환됩니다.

**필수 수정사항:**
- 없음 (현재 상태로도 동작 가능)

**권장 수정사항:**
1. **프론트엔드 Sources 렌더링** - 사용자 경험 개선
2. **환경변수 호환성** - 유연성 향상
3. **Session ID 전송** - 대화 지속성 향상

**다음 단계:**
1. 권장 수정사항 적용 (선택)
2. 통합 테스트 실행
3. 프로덕션 배포

---

**작성:** Claude Code
**날짜:** 2025-12-02
**버전:** 1.0
