/**
 * Helper functions
 */

/**
 * 시간을 사람이 읽기 쉬운 형태로 변환
 */
export const formatDuration = (seconds) => {
  if (seconds < 60) {
    return `${seconds}초`
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${minutes}분 ${secs}초`
  } else {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}시간 ${minutes}분`
  }
}

/**
 * 날짜를 상대적 시간으로 변환
 */
export const formatRelativeTime = (dateString) => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) {
    return '방금 전'
  } else if (diffMins < 60) {
    return `${diffMins}분 전`
  } else if (diffHours < 24) {
    return `${diffHours}시간 전`
  } else if (diffDays < 7) {
    return `${diffDays}일 전`
  } else {
    return date.toLocaleDateString('ko-KR')
  }
}

/**
 * 문제 태그를 색상으로 매핑
 */
export const getTagColor = (tag) => {
  const colors = {
    '구현': '#3b82f6',
    '수학': '#f59e0b',
    '그리디': '#10b981',
    '동적계획법': '#8b5cf6',
    '그래프': '#ef4444',
    '문자열': '#06b6d4',
    '자료구조': '#ec4899',
  }
  return colors[tag] || '#6b7280'
}

/**
 * 로컬 스토리지에 데이터 저장
 */
export const saveToLocalStorage = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch (error) {
    console.error('Failed to save to localStorage:', error)
  }
}

/**
 * 로컬 스토리지에서 데이터 불러오기
 */
export const loadFromLocalStorage = (key, defaultValue = null) => {
  try {
    const item = localStorage.getItem(key)
    return item ? JSON.parse(item) : defaultValue
  } catch (error) {
    console.error('Failed to load from localStorage:', error)
    return defaultValue
  }
}

/**
 * 클립보드에 텍스트 복사
 */
export const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (error) {
    console.error('Failed to copy to clipboard:', error)
    return false
  }
}

/**
 * 코드 실행 결과 파싱
 */
export const parseExecutionResult = (result) => {
  if (!result) return null

  return {
    success: result.success || false,
    output: result.output || '',
    error: result.error || null,
    executionTime: result.execution_time || 0,
  }
}

/**
 * 에러 메시지 추출
 */
export const extractErrorMessage = (error) => {
  if (error.response?.data?.error?.message) {
    return error.response.data.error.message
  } else if (error.response?.data?.message) {
    return error.response.data.message
  } else if (error.message) {
    return error.message
  } else {
    return '알 수 없는 오류가 발생했습니다.'
  }
}
