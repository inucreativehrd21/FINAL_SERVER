import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import './Roadmap.css'

function Roadmap() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [roadmaps, setRoadmaps] = useState([])
  const [activeRoadmap, setActiveRoadmap] = useState(null)
  const [activeProblems, setActiveProblems] = useState([])
  const [userBadges, setUserBadges] = useState([])
  const [userGoals, setUserGoals] = useState([])
  const [allBadges, setAllBadges] = useState([])

  useEffect(() => {
    fetchAllRoadmaps()
    fetchBadges()
    fetchGoals()
  }, [])

  const fetchAllRoadmaps = async () => {
    setLoading(true)
    try {
      // 모든 로드맵 조회
      const roadmapsResponse = await api.get('/coding-test/roadmaps/')
      if (roadmapsResponse.data.success) {
        const roadmapsList = roadmapsResponse.data.data || []
        setRoadmaps(roadmapsList)

        // 활성화된 로드맵의 상세 정보 조회
        const activeRoadmapData = roadmapsList.find(r => r.is_active)
        if (activeRoadmapData) {
          const detailResponse = await api.get('/coding-test/roadmap/')
          if (detailResponse.data.success) {
            setActiveRoadmap(detailResponse.data.data.roadmap)
            setActiveProblems(detailResponse.data.data.problems)
          }
        }
      }
    } catch (error) {
      console.error('Failed to fetch roadmaps:', error)
      if (error.response?.status === 404) {
        setRoadmaps([])
      }
    } finally {
      setLoading(false)
    }
  }

  const fetchBadges = async () => {
    try {
      const [allBadgesRes, userBadgesRes] = await Promise.all([
        api.get('/coding-test/badges/'),
        api.get('/coding-test/user-badges/')
      ])

      if (allBadgesRes.data.success) {
        setAllBadges(allBadgesRes.data.data)
      }
      if (userBadgesRes.data.success) {
        setUserBadges(userBadgesRes.data.data)
      }
    } catch (error) {
      console.error('Failed to fetch badges:', error)
    }
  }

  const fetchGoals = async () => {
    try {
      const response = await api.get('/coding-test/user-goals/')
      if (response.data.success) {
        setUserGoals(response.data.data)
      }
    } catch (error) {
      console.error('Failed to fetch goals:', error)
    }
  }

  const handleDeleteRoadmap = async (roadmapId) => {
    if (!window.confirm('이 로드맵을 삭제하시겠습니까?')) return

    try {
      const response = await api.delete(`/coding-test/roadmaps/${roadmapId}/delete/`)
      if (response.data.success) {
        alert('로드맵이 삭제되었습니다.')
        fetchAllRoadmaps()
      }
    } catch (error) {
      console.error('Failed to delete roadmap:', error)
      alert('로드맵 삭제에 실패했습니다.')
    }
  }

  const handleActivateRoadmap = async (roadmapId) => {
    try {
      const response = await api.post(`/coding-test/roadmaps/${roadmapId}/activate/`)
      if (response.data.success) {
        alert('로드맵이 활성화되었습니다.')
        fetchAllRoadmaps()
      }
    } catch (error) {
      console.error('Failed to activate roadmap:', error)
      alert('로드맵 활성화에 실패했습니다.')
    }
  }

  const handleProblemClick = (problemId) => {
    navigate(`/app/coding-test/${problemId}`)
  }

  const getProgressColor = (percentage) => {
    if (percentage >= 80) return '#4caf50'
    if (percentage >= 50) return '#ff9800'
    return '#667eea'
  }

  if (loading) {
    return (
      <div className="roadmap-page">
        <div className="loading">로드맵을 불러오는 중...</div>
      </div>
    )
  }

  if (roadmaps.length === 0) {
    return (
      <div className="roadmap-page">
        <div className="no-roadmap">
          <h2>아직 로드맵이 없습니다</h2>
          <p>설문조사를 완료하여 맞춤 로드맵을 생성하세요</p>
          <button className="survey-btn" onClick={() => navigate('/app/survey')}>
            설문조사 하러 가기
          </button>
        </div>
      </div>
    )
  }

  const progressPercentage = activeRoadmap?.progress_percentage || 0

  return (
    <div className="roadmap-page">
      <div className="roadmap-header">
        <h1>나의 학습 로드맵</h1>
        <p>맞춤화된 학습 경로를 따라 성장하세요</p>
        <button className="create-roadmap-btn" onClick={() => navigate('/app/survey')}>
          + 새 로드맵 생성
        </button>
      </div>

      {/* 모든 로드맵 목록 */}
      <div className="all-roadmaps-section">
        <h3>내 로드맵 목록 ({roadmaps.length}개)</h3>
        <div className="roadmaps-grid">
          {roadmaps.map((roadmap) => (
            <div key={roadmap.id} className={`roadmap-card ${roadmap.is_active ? 'active' : ''}`}>
              <div className="roadmap-card-header">
                <h4>로드맵 #{roadmap.id}</h4>
                {roadmap.is_active && <span className="active-badge">활성화됨</span>}
              </div>
              <div className="roadmap-card-info">
                <div className="roadmap-stat">
                  <span className="label">진행률:</span>
                  <span className="value">{Math.round(roadmap.progress_percentage)}%</span>
                </div>
                <div className="roadmap-stat">
                  <span className="label">진행:</span>
                  <span className="value">{roadmap.current_step} / {roadmap.total_problems}</span>
                </div>
                <div className="roadmap-stat">
                  <span className="label">생성일:</span>
                  <span className="value">{new Date(roadmap.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <div className="roadmap-progress-bar">
                <div
                  className="roadmap-progress-fill"
                  style={{
                    width: `${roadmap.progress_percentage}%`,
                    background: getProgressColor(roadmap.progress_percentage)
                  }}
                ></div>
              </div>
              <div className="roadmap-card-actions">
                {!roadmap.is_active && (
                  <button
                    className="activate-btn"
                    onClick={() => handleActivateRoadmap(roadmap.id)}
                  >
                    활성화
                  </button>
                )}
                <button
                  className="delete-roadmap-btn"
                  onClick={() => handleDeleteRoadmap(roadmap.id)}
                >
                  삭제
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 활성화된 로드맵의 상세 정보 */}
      {activeRoadmap && (
        <>
          {/* 전체 진행률 */}
          <div className="progress-overview">
            <div className="progress-card">
              <h3>활성화된 로드맵 진행률</h3>
              <div className="progress-circle">
                <svg viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="45" fill="none" stroke="#e0e0e0" strokeWidth="8" />
                  <circle
                    cx="50"
                    cy="50"
                    r="45"
                    fill="none"
                    stroke={getProgressColor(progressPercentage)}
                    strokeWidth="8"
                    strokeDasharray={`${progressPercentage * 2.827} 282.7`}
                    strokeLinecap="round"
                    transform="rotate(-90 50 50)"
                  />
                </svg>
                <div className="progress-text">{Math.round(progressPercentage)}%</div>
              </div>
              <p className="progress-info">
                {activeRoadmap.current_step} / {activeRoadmap.recommended_problems.length} 문제 완료
              </p>
            </div>
          </div>

          {/* 목표 현황 */}
          {userGoals.length > 0 && (
            <div className="goals-section">
              <h3>진행 중인 목표</h3>
              <div className="goals-grid">
                {userGoals.map(goal => (
                  <div key={goal.id} className={`goal-card ${goal.is_completed ? 'completed' : ''}`}>
                    <div className="goal-header">
                      <h4>{goal.goal_name}</h4>
                      {goal.is_completed && <span className="completed-badge">✓ 완료</span>}
                    </div>
                    <div className="goal-progress">
                      <div className="goal-bar">
                        <div
                          className="goal-fill"
                          style={{ width: `${goal.progress_percentage}%` }}
                        />
                      </div>
                      <span className="goal-text">
                        {goal.current_value} / {goal.target_value}
                      </span>
                    </div>
                    <p className="goal-description">{goal.goal_description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 추천 문제 목록 */}
          <div className="recommended-problems">
            <h3>활성화된 로드맵의 추천 문제 ({activeProblems.length}개)</h3>
            <div className="problems-grid">
              {activeProblems.map((problem, index) => {
                const isCompleted = index < activeRoadmap.current_step
                const isCurrent = index === activeRoadmap.current_step

                return (
                  <div
                    key={problem.problem_id}
                    className={`problem-card ${isCompleted ? 'completed' : ''} ${isCurrent ? 'current' : ''}`}
                    onClick={() => handleProblemClick(problem.problem_id)}
                  >
                    <div className="problem-number">
                      {isCompleted ? '✓' : index + 1}
                    </div>
                    <div className="problem-content">
                      <h4>{problem.title}</h4>
                      {problem.step_title && (
                        <p className="problem-category">{problem.step_title}</p>
                      )}
                      <div className="problem-meta">
                        <span className="difficulty">Level {problem.level}</span>
                        {problem.tags && problem.tags.length > 0 && (
                          <span className="tags">
                            {problem.tags.slice(0, 2).join(', ')}
                          </span>
                        )}
                      </div>
                    </div>
                    {isCurrent && <div className="current-indicator">현재 진행 중</div>}
                  </div>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default Roadmap
