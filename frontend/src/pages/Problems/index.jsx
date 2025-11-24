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
  const [filters, setFilters] = useState({
    statusFilter: 'all', // 'all', 'solved', 'unsolved', 'in_progress'
    categories: [],
    levels: [],
    tags: [],
  })
  const [expandedSection, setExpandedSection] = useState('levels') // 'levels' or 'tags' - 기본으로 levels 열림

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

    // 사용자의 제출 기록 로드
    fetchSubmissions()
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

  const getProblemStatus = (problemId) => {
    const problemSubmissions = submissions.filter(s => s.problem_id === problemId)

    // 성공한 제출이 있으면 solved
    const hasSuccess = problemSubmissions.some(s => s.result === 'success')
    if (hasSuccess) return 'solved'

    // 제출 기록이 있으면 in_progress
    if (problemSubmissions.length > 0) return 'in_progress'

    // localStorage에 저장된 코드가 있는지 확인
    if (user) {
      const storageKey = `user_${user.id}_problem_${problemId}_code`
      const savedCode = localStorage.getItem(storageKey)
      if (savedCode && savedCode.trim() !== '') {
        return 'in_progress'
      }
    }

    return 'unsolved'
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

  const handleTagChange = (tag) => {
    setFilters(prev => ({
      ...prev,
      tags: prev.tags.includes(tag)
        ? prev.tags.filter(t => t !== tag)
        : [...prev.tags, tag]
    }))
  }

  const handleSelectAllCategories = (e) => {
    if (e.target.checked) {
      const allCategories = [...new Set(problems.map(p => p.step_title).filter(Boolean))]
      setFilters(prev => ({ ...prev, categories: allCategories }))
    } else {
      setFilters(prev => ({ ...prev, categories: [] }))
    }
  }

  const handleSearch = () => {
    // 검색 로직은 이미 filteredProblems에서 처리됨
  }

  const filteredProblems = problems.filter(problem => {
    // 상태 필터 (전체/푼 문제/안 푼 문제/푸는 중)
    const status = getProblemStatus(problem.problem_id)
    if (filters.statusFilter === 'solved' && status !== 'solved') return false
    if (filters.statusFilter === 'unsolved' && status !== 'unsolved') return false
    if (filters.statusFilter === 'in_progress' && status !== 'in_progress') return false

    const matchesCategory = filters.categories.length === 0 || filters.categories.includes(problem.step_title)
    const matchesLevel = filters.levels.length === 0 || filters.levels.includes(problem.level)
    const matchesTags = filters.tags.length === 0 || (problem.tags && filters.tags.some(tag => problem.tags.includes(tag)))

    return matchesCategory && matchesLevel && matchesTags
  })

  const allCategories = [...new Set(problems.map(p => p.step_title).filter(Boolean))]

  // 실제 문제 데이터에서 사용된 태그만 추출
  const allTags = [...new Set(problems.flatMap(p => p.tags || []))].filter(Boolean).sort()

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
                checked={filters.statusFilter === 'solved'}
                onChange={() => setFilters(prev => ({ ...prev, statusFilter: 'solved' }))}
              />
              내가 푼 문제
            </label>
            <label className="filter-checkbox">
              <input
                type="radio"
                name="statusFilter"
                checked={filters.statusFilter === 'unsolved'}
                onChange={() => setFilters(prev => ({ ...prev, statusFilter: 'unsolved' }))}
              />
              안 푼 문제
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
            onClick={() => setExpandedSection(expandedSection === 'tags' ? null : 'tags')}
          >
            <span>소분류</span>
            <span className={`accordion-icon ${expandedSection === 'tags' ? 'expanded' : ''}`}>▼</span>
          </div>
          {expandedSection === 'tags' && (
            <div className="filter-options filter-options-wrap accordion-content">
              {allTags.map((tag, index) => (
                <label key={index} className="filter-checkbox">
                  <input
                    type="checkbox"
                    checked={filters.tags.includes(tag)}
                    onChange={() => handleTagChange(tag)}
                  />
                  {tag}
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
                <td colSpan="5" className="loading-cell">문제를 불러오는 중...</td>
              </tr>
            ) : filteredProblems.length === 0 ? (
              <tr>
                <td colSpan="5" className="empty-cell">조건에 맞는 문제가 없습니다.</td>
              </tr>
            ) : (
              filteredProblems.map((problem, index) => (
                <tr key={problem.problem_id}>
                  <td>{problem.problem_id}</td>
                  <td className="problem-title-cell">{problem.title}</td>
                  <td>{problem.level}</td>
                  <td>{problem.step_title || '-'}</td>
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
