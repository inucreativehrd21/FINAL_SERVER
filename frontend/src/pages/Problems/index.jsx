import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import api from '../../services/api'
import './Problems.css'

function Problems() {
  const navigate = useNavigate()
  const { user } = useSelector((state) => state.auth)
  const [problems, setProblems] = useState([])
  const [loading, setLoading] = useState(true)
  const [submissions, setSubmissions] = useState([])
  const [problemStatuses, setProblemStatuses] = useState([]) // ProblemStatus from backend
  const [filters, setFilters] = useState({
    statusFilter: 'all', // 'all', 'in_progress', 'star_0', 'star_1', 'star_2', 'star_3'
    categories: [],
    levels: [],
  })
  const [expandedSection, setExpandedSection] = useState('levels') // 'levels' or 'categories' - 기본으로 levels 열림
  const [bookmarkedProblems, setBookmarkedProblems] = useState([]) // 북마크된 문제 ID 목록

  useEffect(() => {
    // JSON 파일에서 문제 로드
    fetch('/problems.json')
      .then(response => response.json())
      .then(data => {
        setProblems(data)
        setLoading(false)
      })
      .catch(error => {
        console.error('Failed to load problems:', error)
        setLoading(false)
      })

    // 사용자의 제출 기록 및 ProblemStatus 로드
    fetchSubmissions()
    fetchProblemStatuses()
    fetchBookmarkStatus()
  }, [])

  const fetchSubmissions = async () => {
    try {
      const response = await api.get('/coding-test/submissions/')
      if (response.data.success) {
        setSubmissions(response.data.data || [])
      }
    } catch (error) {
      console.error('Failed to fetch submissions:', error)
    }
  }

  const fetchProblemStatuses = async () => {
    try {
      const response = await api.get('/coding-test/problem-statuses/')
      if (response.data.success) {
        setProblemStatuses(response.data.data || [])
      }
    } catch (error) {
      console.error('Failed to fetch problem statuses:', error)
    }
  }

  const fetchBookmarkStatus = async () => {
    try {
      const response = await api.get('/coding-test/bookmarks/status/')
      if (response.data.success) {
        setBookmarkedProblems(response.data.data || [])
      }
    } catch (error) {
      console.error('Failed to fetch bookmark status:', error)
    }
  }

  const handleToggleBookmark = async (e, problemId) => {
    e.stopPropagation() // 행 클릭 이벤트 방지
    try {
      const response = await api.post('/coding-test/bookmarks/toggle/', {
        problem_id: problemId
      })
      if (response.data.success) {
        if (response.data.data.bookmarked) {
          setBookmarkedProblems(prev => [...prev, problemId])
        } else {
          setBookmarkedProblems(prev => prev.filter(id => id !== problemId))
        }
      }
    } catch (error) {
      console.error('Failed to toggle bookmark:', error)
    }
  }

  const isBookmarked = (problemId) => {
    return bookmarkedProblems.includes(problemId)
  }

  const getProblemStatus = (problemId) => {
    // 1. ProblemStatus에서 별점(star_count) 확인
    const problemStatus = problemStatuses.find(ps => ps.problem_id === problemId)
    if (problemStatus && problemStatus.star_count !== undefined) {
      // 별점이 있으면 star_1, star_2, star_3 반환
      const starCount = problemStatus.star_count || 0
      if (starCount >= 1) {
        return `star_${starCount}`
      }
    }

    // 2. 제출 기록 또는 localStorage에 저장된 코드가 있으면 '푸는 중'
    const problemSubmissions = submissions.filter(s => s.problem_id === problemId)
    if (problemSubmissions.length > 0) return 'in_progress'

    // 3. localStorage에 저장된 코드가 있는지 확인
    if (user) {
      const storageKey = `user_${user.id}_problem_${problemId}_code`
      const savedCode = localStorage.getItem(storageKey)
      if (savedCode && savedCode.trim() !== '') {
        return 'in_progress'
      }
    }

    // 4. 아무것도 없으면 0별 (시도한 적 없음)
    return 'star_0'
  }

  const handleProblemClick = (problemId) => {
    navigate(`/app/coding-test/${problemId}`)
  }

  const handleCategoryChange = (category) => {
    setFilters(prev => ({
      ...prev,
      categories: prev.categories.includes(category)
        ? prev.categories.filter(c => c !== category)
        : [...prev.categories, category]
    }))
  }

  const handleLevelChange = (level) => {
    setFilters(prev => ({
      ...prev,
      levels: prev.levels.includes(level)
        ? prev.levels.filter(l => l !== level)
        : [...prev.levels, level]
    }))
  }

  const handleSearch = () => {
    // 검색 로직은 이미 filteredProblems에서 처리됨
  }

  const filteredProblems = problems.filter(problem => {
    // 상태 필터 (전체/푸는 중/0별/1별/2별/3별)
    const status = getProblemStatus(problem.problem_id)

    if (filters.statusFilter === 'in_progress' && status !== 'in_progress') return false
    if (filters.statusFilter === 'star_0' && status !== 'star_0') return false
    if (filters.statusFilter === 'star_1' && status !== 'star_1') return false
    if (filters.statusFilter === 'star_2' && status !== 'star_2') return false
    if (filters.statusFilter === 'star_3' && status !== 'star_3') return false

    const matchesCategory = filters.categories.length === 0 || filters.categories.includes(problem.category)
    const matchesLevel = filters.levels.length === 0 || filters.levels.includes(problem.level)

    return matchesCategory && matchesLevel
  })

  // 실제 문제 데이터에서 사용된 category 값만 추출 (어려움 순 정렬: 쉬운 것 → 어려운 것)
  const categoryDifficultyOrder = [
    '입출력/기초',
    '수학',
    '문자열',
    '자료구조 (기본)',
    '정렬',
    '탐색',
    '해시/맵',
    '브루트포스/백트래킹',
    '그리디',
    'DP (동적계획법)',
    '그래프 (기본)',
    '분할정복',
    '트리',
    '자료구조 (고급)',
    '기하학',
    '그래프 (고급)',
    '네트워크 플로우',
    '게임 이론',
    '고급 알고리즘',
    '기타/특수'
  ]
  const allCategories = [...new Set(problems.map(p => p.category).filter(Boolean))].sort((a, b) => {
    const indexA = categoryDifficultyOrder.indexOf(a)
    const indexB = categoryDifficultyOrder.indexOf(b)
    // 목록에 없는 카테고리는 맨 뒤로
    if (indexA === -1 && indexB === -1) return a.localeCompare(b)
    if (indexA === -1) return 1
    if (indexB === -1) return -1
    return indexA - indexB
  })

  // 실제 문제 데이터에서 사용된 레벨만 추출
  const allLevels = [...new Set(problems.map(p => p.level))].filter(Boolean).sort((a, b) => a - b)

  return (
    <div className="problems-page">
      <div className="problems-header">
        <h1 className="problems-title">문제리스트</h1>
        <div className="proposal-buttons">
          <button
            className="proposal-btn"
            onClick={() => navigate('/app/problem-proposal')}
          >
            문제 제안하기
          </button>
          <button
            className="proposal-btn"
            onClick={() => navigate('/app/test-case-proposal')}
          >
            테스트 케이스 제안하기
          </button>
          <button
            className="proposal-btn"
            onClick={() => navigate('/app/solution-proposal')}
          >
            솔루션 제안하기
          </button>
        </div>
      </div>

      <div className="filters-container">
        <div className="filter-row">
          <div className="filter-label">대분류</div>
          <div className="filter-options">
            <label className="filter-checkbox">
              <input
                type="radio"
                name="statusFilter"
                checked={filters.statusFilter === 'all'}
                onChange={() => setFilters(prev => ({ ...prev, statusFilter: 'all' }))}
              />
              전체
            </label>
            <label className="filter-checkbox">
              <input
                type="radio"
                name="statusFilter"
                checked={filters.statusFilter === 'in_progress'}
                onChange={() => setFilters(prev => ({ ...prev, statusFilter: 'in_progress' }))}
              />
              푸는 중
            </label>
            <label className="filter-checkbox">
              <input
                type="radio"
                name="statusFilter"
                checked={filters.statusFilter === 'star_0'}
                onChange={() => setFilters(prev => ({ ...prev, statusFilter: 'star_0' }))}
              />
              ☆ 0별
            </label>
            <label className="filter-checkbox">
              <input
                type="radio"
                name="statusFilter"
                checked={filters.statusFilter === 'star_1'}
                onChange={() => setFilters(prev => ({ ...prev, statusFilter: 'star_1' }))}
              />
              ⭐ 1별
            </label>
            <label className="filter-checkbox">
              <input
                type="radio"
                name="statusFilter"
                checked={filters.statusFilter === 'star_2'}
                onChange={() => setFilters(prev => ({ ...prev, statusFilter: 'star_2' }))}
              />
              ⭐⭐ 2별
            </label>
            <label className="filter-checkbox">
              <input
                type="radio"
                name="statusFilter"
                checked={filters.statusFilter === 'star_3'}
                onChange={() => setFilters(prev => ({ ...prev, statusFilter: 'star_3' }))}
              />
              ⭐⭐⭐ 3별
            </label>
          </div>
        </div>

        <div className="filter-row accordion-row">
          <div
            className="filter-label accordion-header"
            onClick={() => setExpandedSection(expandedSection === 'levels' ? null : 'levels')}
          >
            <span>단계</span>
            <span className={`accordion-icon ${expandedSection === 'levels' ? 'expanded' : ''}`}>▼</span>
          </div>
          {expandedSection === 'levels' && (
            <div className="filter-options filter-options-wrap accordion-content">
              {allLevels.map((level) => (
                <label key={level} className="filter-checkbox">
                  <input
                    type="checkbox"
                    checked={filters.levels.includes(level)}
                    onChange={() => handleLevelChange(level)}
                  />
                  {level}단계
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="filter-row accordion-row">
          <div
            className="filter-label accordion-header"
            onClick={() => setExpandedSection(expandedSection === 'categories' ? null : 'categories')}
          >
            <span>분류</span>
            <span className={`accordion-icon ${expandedSection === 'categories' ? 'expanded' : ''}`}>▼</span>
          </div>
          {expandedSection === 'categories' && (
            <div className="filter-options filter-options-wrap accordion-content">
              {allCategories.map((category, index) => (
                <label key={index} className="filter-checkbox">
                  <input
                    type="checkbox"
                    checked={filters.categories.includes(category)}
                    onChange={() => handleCategoryChange(category)}
                  />
                  {category}
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="filter-actions">
          <button className="search-btn" onClick={handleSearch}>
            검색
          </button>
        </div>
      </div>

      <div className="problems-table-wrapper">
        <table className="problems-table">
          <thead>
            <tr>
              <th className="bookmark-col">북마크</th>
              <th>No.</th>
              <th>문제명</th>
              <th>단계</th>
              <th>분류</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="6" className="loading-cell">문제를 불러오는 중...</td>
              </tr>
            ) : filteredProblems.length === 0 ? (
              <tr>
                <td colSpan="6" className="empty-cell">조건에 맞는 문제가 없습니다.</td>
              </tr>
            ) : (
              filteredProblems.map((problem, index) => (
                <tr key={problem.problem_id}>
                  <td className="bookmark-col">
                    <button
                      className={`bookmark-btn ${isBookmarked(problem.problem_id) ? 'bookmarked' : ''}`}
                      onClick={(e) => handleToggleBookmark(e, problem.problem_id)}
                      title={isBookmarked(problem.problem_id) ? '북마크 해제' : '북마크 추가'}
                    >
                      {isBookmarked(problem.problem_id) ? '★' : '☆'}
                    </button>
                  </td>
                  <td>{problem.problem_id}</td>
                  <td className="problem-title-cell">{problem.title}</td>
                  <td>{problem.level}</td>
                  <td>{problem.category || '-'}</td>
                  <td>
                    <button
                      className="action-btn"
                      onClick={() => handleProblemClick(problem.problem_id)}
                    >
                      시작하기
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Problems
