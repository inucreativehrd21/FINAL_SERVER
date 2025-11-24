/**
 * 애플리케이션 상수 정의
 */

// 문제 난이도 레벨
export const PROBLEM_LEVELS = {
  1: { label: '매우 쉬움', color: '#10b981' },
  2: { label: '쉬움', color: '#3b82f6' },
  3: { label: '보통', color: '#f59e0b' },
  4: { label: '어려움', color: '#ef4444' },
  5: { label: '매우 어려움', color: '#dc2626' },
}

// 힌트 레벨
export const HINT_LEVELS = {
  SMALL: { value: 'small', label: '소 힌트', description: '간단한 방향 제시' },
  MEDIUM: { value: 'medium', label: '중 힌트', description: '구체적인 접근 방법' },
  LARGE: { value: 'large', label: '대 힌트', description: '상세한 해결 가이드' },
}

// 사용자 성향
export const USER_TENDENCIES = {
  PERFECTIONIST: { value: 'perfectionist', label: '완벽주의형', description: '한 번에 정답을 맞추는 스타일' },
  ITERATIVE: { value: 'iterative', label: '반복형', description: '여러 번 실행하며 오류를 수정하는 스타일' },
  UNKNOWN: { value: 'unknown', label: '미분류', description: '데이터 부족' },
}

// 사용자 역할
export const USER_ROLES = {
  USER: 'user',
  ADMIN: 'admin',
}

// API 엔드포인트
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login/',
    SIGNUP: '/auth/signup/',
    LOGOUT: '/auth/logout/',
    REFRESH: '/auth/refresh/',
    USER: '/auth/user/',
  },
  CODING_TEST: {
    PROBLEMS: '/coding-test/problems/',
    EXECUTE: '/coding-test/execute/',
    HINTS: '/coding-test/hints/',
    BOOKMARKS: '/coding-test/bookmarks/',
    SUBMISSIONS: '/coding-test/submissions/',
  },
  CHATBOT: {
    CHAT: '/chatbot/chat/',
    HISTORY: '/chatbot/history/',
    BOOKMARKS: '/chatbot/bookmarks/',
    RATINGS: '/chatbot/ratings/',
  },
  MYPAGE: {
    PROFILE: '/mypage/profile/',
    BOOKMARKS: '/mypage/bookmarks/',
    STATISTICS: '/mypage/statistics/',
    RATING: '/mypage/rating/',
  },
  ADMIN: {
    HINTS: '/admin/hints/',
    CHATBOT: '/admin/chatbot/',
    MODELS: '/admin/models/',
  },
}

// Monaco Editor 설정
export const MONACO_OPTIONS = {
  minimap: { enabled: false },
  fontSize: 14,
  lineNumbers: 'on',
  scrollBeyondLastLine: false,
  automaticLayout: true,
  tabSize: 4,
  wordWrap: 'on',
}

// 코드 실행 타임아웃 (초)
export const CODE_EXECUTION_TIMEOUT = 5

// 페이지 크기
export const PAGE_SIZE = 20
