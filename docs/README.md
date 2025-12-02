# 📚 Documentation Index

이 디렉토리는 프로젝트의 모든 문서를 포함합니다.

**마지막 업데이트:** 2025-12-02

---

## 📋 문서 분류

### 🚀 배포 및 인프라
- [**BLUE_GREEN_DEPLOYMENT.md**](./BLUE_GREEN_DEPLOYMENT.md) - Blue/Green 무중단 배포 구조 설명
- [**CI_CD_SETUP.md**](./CI_CD_SETUP.md) - GitHub Actions CI/CD 파이프라인 설정
- [**DEPLOYMENT_CHECKLIST.md**](./DEPLOYMENT_CHECKLIST.md) - 배포 전 체크리스트
- [**ZERO_DOWNTIME_ANALYSIS.md**](./ZERO_DOWNTIME_ANALYSIS.md) - 무중단 배포 검증 및 분석

### 🤖 챗봇 통합
- [**RAG_CHATBOT_INTEGRATION_SUMMARY.md**](./RAG_CHATBOT_INTEGRATION_SUMMARY.md) - RAG 챗봇 통합 완료 보고서
- [**CHATBOT_TIMEOUT_FIX.md**](./CHATBOT_TIMEOUT_FIX.md) - Gunicorn 타임아웃 해결 가이드

### 🔧 팀원 레포 통합
- [**INTEGRATION_COMPLETE.md**](./INTEGRATION_COMPLETE.md) - **⭐ 팀원 레포 통합 완료 보고서 (최신)**
  - DB 마이그레이션
  - Hint AI 구조
  - 12-메트릭 시스템
  - 별점 시스템
  - 트러블슈팅 가이드
- [**INTEGRATION_SIMPLE.md**](./INTEGRATION_SIMPLE.md) - 간소화된 통합 계획 (참고용)

### 📖 기타
- [**COMPATIBILITY_REPORT.md**](./COMPATIBILITY_REPORT.md) - 시스템 호환성 리포트
- [**QUICKSTART.md**](./QUICKSTART.md) - 빠른 시작 가이드

---

## 🎯 주요 문서 바로가기

### 신규 개발자를 위한 필독 문서
1. [**QUICKSTART.md**](./QUICKSTART.md) - 프로젝트 시작하기
2. [**INTEGRATION_COMPLETE.md**](./INTEGRATION_COMPLETE.md) - 최신 시스템 구조
3. [**BLUE_GREEN_DEPLOYMENT.md**](./BLUE_GREEN_DEPLOYMENT.md) - 배포 프로세스

### 운영/배포 담당자를 위한 문서
1. [**DEPLOYMENT_CHECKLIST.md**](./DEPLOYMENT_CHECKLIST.md) - 배포 체크리스트
2. [**CI_CD_SETUP.md**](./CI_CD_SETUP.md) - CI/CD 설정
3. [**ZERO_DOWNTIME_ANALYSIS.md**](./ZERO_DOWNTIME_ANALYSIS.md) - 무중단 배포 검증

### 문제 해결 가이드
1. [**CHATBOT_TIMEOUT_FIX.md**](./CHATBOT_TIMEOUT_FIX.md) - Gunicorn 타임아웃 문제
2. [**INTEGRATION_COMPLETE.md**](./INTEGRATION_COMPLETE.md) - 트러블슈팅 섹션 참고

---

## 📊 프로젝트 구조

```
FINAL_SERVER/
├── backend/              # Django 백엔드
│   ├── apps/
│   │   ├── coding_test/  # 코딩 테스트 앱
│   │   │   ├── models.py           # 12-메트릭, ProblemStatus, HintEvaluation
│   │   │   ├── hint_proxy.py       # RunPod 힌트 AI 통신
│   │   │   ├── submission_api.py   # 12-메트릭 제출 API
│   │   │   ├── code_analyzer.py    # 정적 코드 분석
│   │   │   ├── code_executor.py    # 코드 실행 엔진
│   │   │   └── data/               # 문제 데이터 (79MB)
│   │   ├── chatbot/      # RAG 챗봇 앱
│   │   └── users/        # 사용자 관리
│   └── config/           # Django 설정
├── frontend/             # React 프론트엔드
│   └── src/
│       └── pages/
│           ├── CodingTest/    # 힌트 요청, COH
│           ├── Problems/      # 별점 시스템 (0-3⭐)
│           ├── Chatbot/       # RAG 챗봇 UI
│           └── KakaoCallback/ # OAuth 콜백
├── scripts/              # 배포 스크립트
│   ├── blue-green-deploy.sh
│   └── health-check.sh
├── docs/                 # 📚 모든 문서 (여기!)
└── .github/workflows/    # CI/CD 설정
```

---

## 🔍 문서 검색 팁

### 키워드로 문서 찾기
```bash
# 전체 문서에서 키워드 검색
grep -r "키워드" /home/ec2-user/FINAL_SERVER/docs/

# 예시: "RunPod" 관련 정보 찾기
grep -r "RunPod" /home/ec2-user/FINAL_SERVER/docs/
```

### 최신 문서 확인
```bash
# 최근 수정된 문서 찾기
ls -lt /home/ec2-user/FINAL_SERVER/docs/*.md | head -5
```

---

## 📝 문서 작성 가이드

새 문서를 작성할 때는 다음 형식을 따라주세요:

```markdown
# 제목

**작성일:** YYYY-MM-DD
**작성자:** 이름
**버전:** 1.0

## 개요
간단한 설명

## 주요 내용
상세 설명

## 관련 문서
- [문서1](./문서1.md)
- [문서2](./문서2.md)
```

---

## 🗂️ 아카이브

더 이상 사용하지 않는 레포지토리는 `/home/ec2-user/archives/`에 보관됩니다:
- `TEAMMATE_REPO/` - 통합 완료 후 아카이브
- `EC2_SERVER_INTEGRATION/` - 구 통합 테스트
- `testrag/` - RAG 테스트

---

## ✨ 최신 업데이트

### 2025-12-02
- ✅ 팀원 레포 통합 완료
- ✅ 12-메트릭 시스템 추가
- ✅ 별점 시스템 (0-3⭐) 구현
- ✅ Hint AI (RunPod) 연동
- ✅ COH (Chaining of Hints) 구현
- ✅ 문서 정리 및 통합

### 2025-12-01
- ✅ RAG 챗봇 RunPod 연동
- ✅ Gunicorn 타임아웃 문제 해결 (120초)

### 2025-11-24
- ✅ Blue/Green 무중단 배포 구현
- ✅ CI/CD 파이프라인 설정

---

**문서 관리자:** Claude Code
**문의:** GitHub Issues
