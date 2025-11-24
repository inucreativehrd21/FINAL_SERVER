import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import './Survey.css'

function Survey() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    programming_experience: 'intermediate',
    learning_goals: [],
    interested_topics: [],
    preferred_difficulty: 'medium',
    daily_problem_goal: 2
  })

  const learningGoalOptions = [
    '알고리즘 마스터',
    '자료구조 이해',
    '코딩테스트 준비',
    '문제 해결 능력 향상',
    '프로그래밍 실력 향상'
  ]

  const topicOptions = [
    '배열', '문자열', '정렬', '탐색',
    'DP', '그리디', '그래프', 'DFS/BFS',
    '해시', '스택/큐', '트리', '이분탐색'
  ]

  const handleGoalToggle = (goal) => {
    setFormData(prev => ({
      ...prev,
      learning_goals: prev.learning_goals.includes(goal)
        ? prev.learning_goals.filter(g => g !== goal)
        : [...prev.learning_goals, goal]
    }))
  }

  const handleTopicToggle = (topic) => {
    setFormData(prev => ({
      ...prev,
      interested_topics: prev.interested_topics.includes(topic)
        ? prev.interested_topics.filter(t => t !== topic)
        : [...prev.interested_topics, topic]
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (formData.learning_goals.length === 0) {
      alert('학습 목표를 최소 1개 이상 선택해주세요.')
      return
    }

    if (formData.interested_topics.length === 0) {
      alert('관심 분야를 최소 1개 이상 선택해주세요.')
      return
    }

    setLoading(true)
    try {
      const response = await api.post('/coding-test/survey/', formData)

      if (response.data.success) {
        alert('설문조사가 완료되었습니다! 맞춤 로드맵이 생성되었습니다.')
        navigate('/app/roadmap')
      } else {
        alert('설문조사 제출에 실패했습니다: ' + response.data.message)
      }
    } catch (error) {
      console.error('Survey submission error:', error)
      alert('설문조사 제출 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="survey-page">
      <div className="survey-header">
        <h1>학습 설문조사</h1>
        <p>당신에게 맞춤화된 학습 로드맵을 만들어드립니다</p>
      </div>

      <form className="survey-form" onSubmit={handleSubmit}>
        {/* 프로그래밍 경험 */}
        <div className="survey-section">
          <h3>프로그래밍 경험</h3>
          <p className="section-description">현재 프로그래밍 경험 수준을 선택해주세요</p>

          <div className="radio-group">
            <label className={`radio-option ${formData.programming_experience === 'beginner' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="programming_experience"
                value="beginner"
                checked={formData.programming_experience === 'beginner'}
                onChange={(e) => setFormData({...formData, programming_experience: e.target.value})}
              />
              <div className="option-content">
                <div className="option-title">초급 (0-1년)</div>
                <div className="option-description">프로그래밍을 이제 막 시작했어요</div>
              </div>
            </label>

            <label className={`radio-option ${formData.programming_experience === 'intermediate' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="programming_experience"
                value="intermediate"
                checked={formData.programming_experience === 'intermediate'}
                onChange={(e) => setFormData({...formData, programming_experience: e.target.value})}
              />
              <div className="option-content">
                <div className="option-title">중급 (1-3년)</div>
                <div className="option-description">기본적인 프로그래밍은 할 수 있어요</div>
              </div>
            </label>

            <label className={`radio-option ${formData.programming_experience === 'advanced' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="programming_experience"
                value="advanced"
                checked={formData.programming_experience === 'advanced'}
                onChange={(e) => setFormData({...formData, programming_experience: e.target.value})}
              />
              <div className="option-content">
                <div className="option-title">고급 (3년 이상)</div>
                <div className="option-description">다양한 프로젝트 경험이 있어요</div>
              </div>
            </label>
          </div>
        </div>

        {/* 학습 목표 */}
        <div className="survey-section">
          <h3>학습 목표</h3>
          <p className="section-description">달성하고 싶은 목표를 모두 선택해주세요 (중복 선택 가능)</p>

          <div className="checkbox-grid">
            {learningGoalOptions.map(goal => (
              <label
                key={goal}
                className={`checkbox-option ${formData.learning_goals.includes(goal) ? 'selected' : ''}`}
              >
                <input
                  type="checkbox"
                  checked={formData.learning_goals.includes(goal)}
                  onChange={() => handleGoalToggle(goal)}
                />
                <span>{goal}</span>
              </label>
            ))}
          </div>
        </div>

        {/* 관심 분야 */}
        <div className="survey-section">
          <h3>관심 분야</h3>
          <p className="section-description">학습하고 싶은 주제를 모두 선택해주세요 (중복 선택 가능)</p>

          <div className="checkbox-grid">
            {topicOptions.map(topic => (
              <label
                key={topic}
                className={`checkbox-option ${formData.interested_topics.includes(topic) ? 'selected' : ''}`}
              >
                <input
                  type="checkbox"
                  checked={formData.interested_topics.includes(topic)}
                  onChange={() => handleTopicToggle(topic)}
                />
                <span>{topic}</span>
              </label>
            ))}
          </div>
        </div>

        {/* 선호 난이도 */}
        <div className="survey-section">
          <h3>선호 난이도</h3>
          <p className="section-description">학습하고 싶은 문제의 난이도를 선택해주세요</p>

          <div className="radio-group">
            <label className={`radio-option ${formData.preferred_difficulty === 'easy' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="preferred_difficulty"
                value="easy"
                checked={formData.preferred_difficulty === 'easy'}
                onChange={(e) => setFormData({...formData, preferred_difficulty: e.target.value})}
              />
              <div className="option-content">
                <div className="option-title">쉬움 (Level 1-5)</div>
                <div className="option-description">기초부터 차근차근 배우고 싶어요</div>
              </div>
            </label>

            <label className={`radio-option ${formData.preferred_difficulty === 'medium' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="preferred_difficulty"
                value="medium"
                checked={formData.preferred_difficulty === 'medium'}
                onChange={(e) => setFormData({...formData, preferred_difficulty: e.target.value})}
              />
              <div className="option-content">
                <div className="option-title">중간 (Level 6-10)</div>
                <div className="option-description">적당한 난이도로 실력을 키우고 싶어요</div>
              </div>
            </label>

            <label className={`radio-option ${formData.preferred_difficulty === 'hard' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="preferred_difficulty"
                value="hard"
                checked={formData.preferred_difficulty === 'hard'}
                onChange={(e) => setFormData({...formData, preferred_difficulty: e.target.value})}
              />
              <div className="option-content">
                <div className="option-title">어려움 (Level 11-15)</div>
                <div className="option-description">도전적인 문제로 성장하고 싶어요</div>
              </div>
            </label>
          </div>
        </div>

        {/* 하루 목표 문제 수 */}
        <div className="survey-section">
          <h3>하루 목표 문제 수</h3>
          <p className="section-description">매일 풀고 싶은 문제 개수를 선택해주세요</p>

          <div className="number-selector">
            <button
              type="button"
              className="number-btn"
              onClick={() => setFormData(prev => ({...prev, daily_problem_goal: Math.max(1, prev.daily_problem_goal - 1)}))}
            >
              -
            </button>
            <div className="number-display">{formData.daily_problem_goal}개</div>
            <button
              type="button"
              className="number-btn"
              onClick={() => setFormData(prev => ({...prev, daily_problem_goal: Math.min(10, prev.daily_problem_goal + 1)}))}
            >
              +
            </button>
          </div>
        </div>

        <button type="submit" className="submit-btn" disabled={loading}>
          {loading ? '제출 중...' : '설문 완료 및 로드맵 생성'}
        </button>
      </form>
    </div>
  )
}

export default Survey
