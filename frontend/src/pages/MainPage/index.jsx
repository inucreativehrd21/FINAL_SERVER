import { useNavigate } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { useState, useEffect } from 'react'
import { logout } from '../../store/authSlice'
import api from '../../services/api'
import climbingImg from '../../assets/images/climbing.jpg'
import './MainPage.css'

function MainPage() {
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { isAuthenticated, user } = useSelector((state) => state.auth)
  const [roadmap, setRoadmap] = useState(null)
  const [roadmapProblems, setRoadmapProblems] = useState([])
  const [loadingRoadmap, setLoadingRoadmap] = useState(true)

  const handleLogout = () => {
    dispatch(logout())
    navigate('/')
  }

  useEffect(() => {
    if (isAuthenticated) {
      fetchRoadmap()
    } else {
      setLoadingRoadmap(false)
    }
  }, [isAuthenticated])

  const fetchRoadmap = async () => {
    setLoadingRoadmap(true)
    try {
      const response = await api.get('/coding-test/roadmap/')
      if (response.data.success) {
        setRoadmap(response.data.data.roadmap)
        setRoadmapProblems(response.data.data.problems.slice(0, 1)) // 현재 풀어야 할 문제 1개만 표시
      } else {
        setRoadmap(null)
        setRoadmapProblems([])
      }
    } catch (error) {
      console.error('Failed to fetch roadmap:', error)
      setRoadmap(null)
      setRoadmapProblems([])
    } finally {
      setLoadingRoadmap(false)
    }
  }

  const scrollToSection = (sectionId) => {
    const section = document.getElementById(sectionId)
    section?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleNavClick = (path) => {
    if (!isAuthenticated && (path === '/app/problems' || path === '/app/chatbot')) {
      if (window.confirm('로그인이 필요한 서비스입니다. 로그인 페이지로 이동하시겠습니까?')) {
        navigate('/login')
      }
    } else {
      navigate(path)
    }
  }

  const handleProblemClick = (problemId) => {
    navigate(`/app/coding-test/${problemId}`)
  }

  const navigationCards = [
    {
      id: 'problems',
      title: '코딩 테스트 문제 선택',
      icon: '📝',
      description: '난이도별, 태그별 문제를 선택하여 풀어보세요',
      path: '/app/problems',
      color: '#667eea'
    },
    {
      id: 'chatbot',
      title: '문답 챗봇',
      icon: '🤖',
      description: 'Python, Git 문서 기반 질의응답',
      path: '/app/chatbot',
      color: '#f093fb'
    },
    {
      id: 'mypage',
      title: '마이페이지',
      icon: '👤',
      description: '내 정보 및 학습 기록 확인',
      path: '/app/mypage',
      color: '#4facfe'
    }
  ]

  // 관리자 권한이 있는 경우 관리자 탭 추가
  if (user?.is_staff || user?.is_superuser) {
    navigationCards.push({
      id: 'admin',
      title: '관리자',
      icon: '⚙️',
      description: '시스템 관리 및 설정',
      path: '/app/admin',
      color: '#fa709a'
    })
  }

  return (
    <div className="main-page">
      {/* 간단한 헤더 - Layout과 완전히 동일한 디자인 */}
      <header className="landing-header">
        <div className="nav-left">
          <div className="logo" onClick={() => navigate('/')}>
            π
          </div>
          {isAuthenticated && (
            <>
              <button className="nav-btn" onClick={() => handleNavClick('/app/problems')}>문제 선택</button>
              <button className="nav-btn" onClick={() => handleNavClick('/app/chatbot')}>문답 챗봇</button>
            </>
          )}
        </div>
        <div className="nav-right">
          {!isAuthenticated ? (
            <>
              <button className="nav-btn" onClick={() => navigate('/login')}>로그인</button>
              <button className="nav-btn" onClick={() => navigate('/signup')}>회원가입</button>
            </>
          ) : (
            <>
              <button className="nav-btn" onClick={() => navigate('/app/mypage')}>마이페이지</button>
              {(user?.is_staff || user?.is_superuser) && (
                <button className="nav-btn admin" onClick={() => navigate('/app/admin')}>관리자</button>
              )}
              <button className="logout-btn" onClick={handleLogout}>
                로그아웃
              </button>
            </>
          )}
        </div>
      </header>

      {/* 섹션 1: Hero - PLAN + START (항상 표시) */}
      <section id="hero" className="hero-section">
        <div className="fireworks-bg"></div>
        <div className="hero-content">
          <h1 className="hero-title">
            <span className="hero-letter">P</span>
            <span className="hero-bracket">[</span>
            <span className="hero-letter">A</span>
            <span className="hero-letter">I</span>
            <span className="hero-bracket">]</span>
          </h1>
          {!isAuthenticated && (
            <button className="start-btn" onClick={() => navigate('/login')}>
              START
            </button>
          )}

          {/* 로딩 중 */}
          {isAuthenticated && loadingRoadmap && (
            <div className="no-roadmap-section">
              <div className="no-roadmap-card">
                <div className="no-roadmap-icon">⏳</div>
                <h3>로드맵을 불러오는 중...</h3>
              </div>
            </div>
          )}

          {/* 로드맵이 있는 경우 */}
          {isAuthenticated && !loadingRoadmap && roadmap && (
                <div className="roadmap-section">
                  <div className="section-header">
                    <h2>나의 추천 학습 로드맵</h2>
                    <p>맞춤화된 학습 경로를 따라 문제를 풀어보세요</p>
                  </div>
                  <div className="roadmap-progress">
                    <div className="progress-info">
                      <span>전체 진행률: {roadmap.current_step} / {roadmap.recommended_problems.length} 문제</span>
                      <span className="progress-percentage">{Math.round(roadmap.progress_percentage)}%</span>
                    </div>
                    <div className="progress-bar">
                      <div className="progress-fill" style={{ width: `${roadmap.progress_percentage}%` }}></div>
                    </div>
                  </div>
                  {roadmapProblems.length > 0 && (
                    <div className="roadmap-problems">
                      {roadmapProblems.map((problem, index) => {
                        const isCompleted = index < roadmap.current_step
                        const isCurrent = index === roadmap.current_step
                        return (
                          <div
                            key={problem.problem_id}
                            className={`roadmap-problem-card ${isCompleted ? 'completed' : ''} ${isCurrent ? 'current' : ''}`}
                            onClick={() => handleProblemClick(problem.problem_id)}
                          >
                            <div className="problem-number">
                              {isCompleted ? '✓' : index + 1}
                            </div>
                            <div className="problem-info">
                              <h4>{problem.title}</h4>
                              <div className="problem-meta">
                                <span className="difficulty">Level {problem.level}</span>
                                {problem.tags && problem.tags.length > 0 && (
                                  <span className="tags">{problem.tags.slice(0, 2).join(', ')}</span>
                                )}
                              </div>
                            </div>
                            {isCurrent && <span className="current-badge">진행 중</span>}
                          </div>
                        )
                      })}
                    </div>
                  )}
                  <button className="view-all-btn" onClick={() => navigate('/app/roadmap')}>
                    전체 로드맵 보기 →
                  </button>
                </div>
              )}

          {/* 로드맵이 없는 경우 */}
          {isAuthenticated && !loadingRoadmap && !roadmap && (
            <div className="no-roadmap-section">
              <div className="no-roadmap-card">
                <div className="no-roadmap-icon">🗺️</div>
                <h3>아직 학습 로드맵이 없습니다</h3>
                <p>설문조사를 완료하여 맞춤 학습 로드맵을 생성하세요</p>
                <button className="survey-btn" onClick={() => navigate('/app/survey')}>
                  설문조사 시작하기
                </button>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* 섹션 2: 소개 - OF/BY/FOR THE DEVELOPER (항상 표시) */}
      <section id="intro" className="intro-section">
        <div className="intro-content">
          <div className="intro-text">
            <h2 className="intro-title">
              <span className="text-of">OF</span> <span className="text-gray">THE DEVELOPER,</span><br/>
              <span className="text-by">BY</span> <span className="text-gray">THE DEVELOPER,</span><br/>
              <span className="text-for">FOR</span> <span className="text-gray">THE DEVELOPER</span>
            </h2>
            <p className="intro-subtitle">개발자를 위한 단 하나의 서비스</p>
          </div>
          <div className="intro-image">
            <img src={climbingImg} alt="Rock Climbing" />
          </div>
        </div>
      </section>

      {/* 섹션 3: 기능 카드 (항상 표시) */}
      <section id="features" className="features-section">
        <div className="feature-grid">
          <div className="feature-card white">
            <h3>맞춤형 힌트</h3>
            <p>AI가 당신의 학습 성향을 분석하여 최적의 힌트를 제공합니다.</p>
          </div>
          <div className="feature-card gray">
            <h3>단계별 학습</h3>
            <p>대/중/소 3단계 힌트로 스스로 문제를 해결하는 능력을 키웁니다.</p>
          </div>
          <div className="feature-card dark">
            <h3>RAG 챗봇</h3>
            <p>Python, Git 공식 문서 기반 질의응답으로 학습을 돕습니다.</p>
          </div>
          <div className="feature-card dark">
            <h3>성과 추적</h3>
            <p>문제풀이 기록과 레이팅으로 성장을 확인하세요.</p>
          </div>
        </div>
      </section>
    </div>
  )
}

export default MainPage
