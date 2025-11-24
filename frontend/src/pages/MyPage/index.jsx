import React, { useState, useEffect } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { updateUser, logout } from '../../store/authSlice'
import api from '../../services/api'
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from 'recharts'
import './MyPage.css'

function MyPage() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const user = useSelector((state) => state.auth.user)
  const [activeTab, setActiveTab] = useState('dashboard')
  const [previousTab, setPreviousTab] = useState('dashboard')
  const [stats, setStats] = useState(null)
  const [solvedProblems, setSolvedProblems] = useState([])
  const [bookmarks, setBookmarks] = useState([])
  const [userBadges, setUserBadges] = useState([])
  const [allBadges, setAllBadges] = useState([])
  const [hoveredBadge, setHoveredBadge] = useState(null)
  const [goalProgress, setGoalProgress] = useState(0)
  const [editMode, setEditMode] = useState(false)
  const [formData, setFormData] = useState({
    email: user?.email || '',
    bio: user?.bio || ''
  })
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  })

  useEffect(() => {
    fetchUserStats()
    fetchSolvedProblems()
    fetchBookmarks()
    fetchBadges()
    fetchGoalProgress()
  }, [])

  const fetchUserStats = async () => {
    try {
      const response = await api.get('/auth/user/')
      setStats(response.data.data)
    } catch (error) {
      console.error('Failed to fetch user stats:', error)
    }
  }

  const fetchSolvedProblems = async () => {
    try {
      const response = await api.get('/coding-test/solved/')
      setSolvedProblems(response.data.data || [])
    } catch (error) {
      console.error('Failed to fetch solved problems:', error)
    }
  }

  const fetchBookmarks = async () => {
    try {
      const response = await api.get('/chatbot/bookmarks/')
      setBookmarks(response.data.data || [])
    } catch (error) {
      console.error('Failed to fetch bookmarks:', error)
    }
  }

  const fetchBadges = async () => {
    try {
      const statsRes = await api.get('/mypage/statistics/')
      if (statsRes.data.success) {
        const { metrics, badges } = statsRes.data.data
        const validBadges = (badges || []).filter(b => b && b.badge_id)
        setUserBadges(validBadges)
        setStats(prevStats => ({
          ...prevStats,
          metrics: metrics
        }))
      }

      // 새로운 API: 모든 뱃지 + 진행 상황
      const allBadgesRes = await api.get('/coding-test/user-badges/')
      if (allBadgesRes.data.success) {
        setAllBadges(allBadgesRes.data.data || [])
      }
    } catch (error) {
      console.error('Failed to fetch badges:', error)
    }
  }

  const fetchGoalProgress = async () => {
    try {
      // TODO: 실제 목표 API 엔드포인트로 변경 필요
      // const response = await api.get('/mypage/goal-progress/')
      // setGoalProgress(response.data.data.progress || 0)

      // 임시: solved_count 기반 계산 (예: 목표가 100개 문제라고 가정)
      const targetGoal = 100
      const currentProgress = stats?.solved_count || user?.solved_count || 0
      const percentage = Math.min(100, Math.round((currentProgress / targetGoal) * 100))
      setGoalProgress(percentage)
    } catch (error) {
      console.error('Failed to fetch goal progress:', error)
    }
  }

  const handleUpdateProfile = async (e) => {
    e.preventDefault()

    try {
      const response = await api.put('/auth/user/update/', formData)
      dispatch(updateUser(response.data.data))
      setEditMode(false)
      alert('프로필이 업데이트되었습니다.')
    } catch (error) {
      console.error('Failed to update profile:', error)
      alert('프로필 업데이트에 실패했습니다.')
    }
  }

  const handleChangePassword = async (e) => {
    e.preventDefault()

    if (passwordData.newPassword !== passwordData.confirmPassword) {
      alert('새 비밀번호가 일치하지 않습니다.')
      return
    }

    try {
      await api.post('/auth/user/password/', {
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword
      })

      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      })

      alert('비밀번호가 변경되었습니다.')
    } catch (error) {
      console.error('Failed to change password:', error)
      alert('비밀번호 변경에 실패했습니다.')
    }
  }

  const handleDeleteAccount = async () => {
    if (!window.confirm('정말로 계정을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
      return
    }

    try {
      await api.delete('/auth/user/delete/')
      dispatch(logout())
      alert('계정이 삭제되었습니다.')
    } catch (error) {
      console.error('Failed to delete account:', error)
      alert('계정 삭제에 실패했습니다.')
    }
  }

  return (
    <div className="mypage">
      <div className="mypage-header">
        <h1>마이페이지</h1>
      </div>

      <div className="mypage-layout">
        {/* 왼쪽 사이드바 - 프로필 */}
        <aside className="profile-sidebar">
          <div className="profile-avatar-large">
            {user?.username?.charAt(0).toUpperCase() || 'U'}
          </div>

          <div className="profile-detail-list">
            <div className="profile-detail-row">
              <span className="detail-label">이름</span>
              <span className="detail-value">{user?.name || user?.username || '-'}</span>
            </div>

            <div className="profile-detail-row">
              <span className="detail-label">아이디</span>
              <span className="detail-value">{user?.username || '-'}</span>
            </div>

            <div className="profile-detail-row">
              <span className="detail-label">이메일</span>
              <span className="detail-value">{user?.email || '-'}</span>
            </div>

            <div className="profile-detail-row">
              <span className="detail-label">주소</span>
              <span className="detail-value">{user?.address || '-'}</span>
            </div>
          </div>

          <button
            className="profile-settings-btn"
            onClick={() => setActiveTab('settings')}
          >
            개인 정보 수정
          </button>

          <button
            className="profile-withdraw-btn"
            onClick={handleDeleteAccount}
          >
            탈퇴하기
          </button>
        </aside>

        {/* 오른쪽 메인 컨텐츠 */}
        <main className="mypage-main">
          {activeTab === 'dashboard' && (
            <>
              {/* 상단 통계 바 */}
              <div className="stats-bar">
                <div className="stat-box">
                  <div className="stat-label">레이팅</div>
                  <div className="stat-value">{stats?.rating || user?.rating || 0}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">해결한 문제수</div>
                  <div className="stat-value">{stats?.solved_count || user?.solved_count || 0}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">시도한 문제</div>
                  <div className="stat-value">{stats?.attempted_count || user?.attempted_count || 0}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">정답률</div>
                  <div className="stat-value">
                    {stats?.solved_count && stats?.attempted_count
                      ? Math.round((stats.solved_count / stats.attempted_count) * 100)
                      : 0}%
                  </div>
                </div>
              </div>

              {/* 중단 - 파이 차트, 방사형 그래프 & 버튼들 */}
              <div className="middle-section">
                <div className="charts-container">
                  <div className="pie-chart-section">
                    <h3>목표 대비 완료 비율</h3>
                    <svg viewBox="0 0 200 200" className="pie-chart">
                      <circle cx="100" cy="100" r="80" fill="none" stroke="#e0e0e0" strokeWidth="40" />
                      <circle
                        cx="100"
                        cy="100"
                        r="80"
                        fill="none"
                        stroke="#ff7f7f"
                        strokeWidth="40"
                        strokeDasharray={`${(goalProgress / 100) * 502.4} 502.4`}
                        transform="rotate(-90 100 100)"
                      />
                      <text x="100" y="110" textAnchor="middle" fontSize="36" fontWeight="bold" fill="#333">
                        {goalProgress}%
                      </text>
                    </svg>
                  </div>

                  <div className="radar-chart-section">
                    <h3>나의 코딩 지표</h3>
                    <ResponsiveContainer width="100%" height={300}>
                      <RadarChart
                        data={[
                          {
                            subject: '문법 정확도',
                            value: Math.max(0, 100 - (stats?.metrics?.avg_syntax_errors || 0) * 20),
                            fullMark: 100
                          },
                          {
                            subject: '테스트 통과율',
                            value: stats?.metrics?.avg_test_pass_rate || 0,
                            fullMark: 100
                          },
                          {
                            subject: '코드 품질',
                            value: stats?.metrics?.avg_code_quality_score || 0,
                            fullMark: 100
                          },
                          {
                            subject: '패턴 일치도',
                            value: stats?.metrics?.avg_algorithm_pattern_match || 0,
                            fullMark: 100
                          },
                          {
                            subject: 'PEP8 준수',
                            value: Math.max(0, 100 - (stats?.metrics?.avg_pep8_violations || 0) * 5),
                            fullMark: 100
                          },
                          {
                            subject: '코드 간결성',
                            value: Math.max(0, 100 - (stats?.metrics?.avg_code_complexity || 0) * 5),
                            fullMark: 100
                          }
                        ]}
                        margin={{ top: 40, right: 80, bottom: 40, left: 80 }}
                      >
                        <PolarGrid gridType="polygon" />
                        <PolarAngleAxis
                          dataKey="subject"
                          tick={{ fontSize: 11, fill: '#333', fontWeight: 500 }}
                        />
                        <PolarRadiusAxis angle={60} domain={[0, 100]} tick={{ fontSize: 9 }} />
                        <Radar
                          name="지표"
                          dataKey="value"
                          stroke="#333"
                          fill="#333"
                          fillOpacity={0.3}
                          strokeWidth={2}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                    <div className="chart-legend">
                      <small>각 지표는 0-100점 척도로 표시됩니다</small>
                    </div>
                  </div>
                </div>

                <div className="action-buttons-section">
                  <button
                    className="action-card goal-card"
                    onClick={() => navigate('/app/roadmap')}
                  >
                    <span className="action-icon">🎯</span>
                    <span className="action-text">목표관리</span>
                  </button>

                  <button
                    className="action-card-small badge-card"
                    onClick={() => {
                      setPreviousTab('dashboard')
                      setActiveTab('badges')
                    }}
                  >
                    획득한 뱃지
                  </button>

                  <button
                    className="action-card-small bookmark-card"
                    onClick={() => {
                      setPreviousTab('dashboard')
                      setActiveTab('bookmarks')
                    }}
                  >
                    북마크
                  </button>
                </div>
              </div>

              {/* 하단 - 문제 리스트 */}
              <div className="problems-list-section">
                <h3>📋 내가 푼 문제리스트</h3>
                <div className="problems-table-container">
                  {solvedProblems.length === 0 ? (
                    <div className="empty-state-table">
                      <p>아직 해결한 문제가 없습니다.</p>
                    </div>
                  ) : (
                    <table className="problems-table">
                      <thead>
                        <tr>
                          <th>📄</th>
                          <th>문제명</th>
                          <th>해결일</th>
                          <th>🗑️</th>
                        </tr>
                      </thead>
                      <tbody>
                        {solvedProblems.slice(0, 3).map((problem, index) => (
                          <tr key={problem.id}>
                            <td>📄</td>
                            <td>{problem.title}</td>
                            <td>{problem.solved_at ? new Date(problem.solved_at).toLocaleDateString() : '-'}</td>
                            <td>
                              <button className="delete-icon-btn" title="삭제">🗑️</button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </>
          )}

          {activeTab === 'settings' && (
            <div className="settings-content">
              <h2>개인 정보 수정</h2>

              <div className="profile-card">
                <div className="profile-header">
                  <div className="profile-avatar">
                    {user?.username?.charAt(0).toUpperCase() || 'U'}
                  </div>
                  <div className="profile-info">
                    <h2>{user?.username}</h2>
                    <p className="rating">레이팅: {user?.rating || 0}점</p>
                  </div>
                </div>

                {!editMode ? (
                  <div className="profile-details">
                    <div className="detail-item">
                      <strong>이메일:</strong>
                      <span>{user?.email || '등록되지 않음'}</span>
                    </div>
                    <div className="detail-item">
                      <strong>가입일:</strong>
                      <span>{user?.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}</span>
                    </div>
                    <div className="detail-item">
                      <strong>소개:</strong>
                      <span>{user?.bio || '소개글이 없습니다.'}</span>
                    </div>

                    <button
                      className="edit-btn"
                      onClick={() => setEditMode(true)}
                    >
                      프로필 수정
                    </button>
                  </div>
                ) : (
                  <form onSubmit={handleUpdateProfile} className="edit-form">
                    <div className="form-group">
                      <label>이메일</label>
                      <input
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData({...formData, email: e.target.value})}
                        placeholder="이메일을 입력하세요"
                      />
                    </div>

                    <div className="form-group">
                      <label>소개</label>
                      <textarea
                        value={formData.bio}
                        onChange={(e) => setFormData({...formData, bio: e.target.value})}
                        placeholder="자기소개를 입력하세요"
                        rows="4"
                      />
                    </div>

                    <div className="form-actions">
                      <button type="submit" className="save-btn">저장</button>
                      <button
                        type="button"
                        className="cancel-btn"
                        onClick={() => setEditMode(false)}
                      >
                        취소
                      </button>
                    </div>
                  </form>
                )}
              </div>

              <div className="password-section">
                <h3>비밀번호 변경</h3>
                <form onSubmit={handleChangePassword} className="password-form">
                  <div className="form-group">
                    <label>현재 비밀번호</label>
                    <input
                      type="password"
                      value={passwordData.currentPassword}
                      onChange={(e) => setPasswordData({...passwordData, currentPassword: e.target.value})}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label>새 비밀번호</label>
                    <input
                      type="password"
                      value={passwordData.newPassword}
                      onChange={(e) => setPasswordData({...passwordData, newPassword: e.target.value})}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label>새 비밀번호 확인</label>
                    <input
                      type="password"
                      value={passwordData.confirmPassword}
                      onChange={(e) => setPasswordData({...passwordData, confirmPassword: e.target.value})}
                      required
                    />
                  </div>

                  <button type="submit" className="save-btn">비밀번호 변경</button>
                </form>
              </div>
            </div>
          )}

          {activeTab === 'goals' && (() => {
            navigate('/roadmap')
            return (
              <div className="goals-content">
                <h2>목표 관리</h2>
                <div className="empty-state">
                  <p>로드맵 페이지로 이동 중...</p>
                </div>
              </div>
            )
          })()}

          {activeTab === 'badges' && (
            <div className="badges-section">
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                <button
                  className="back-btn"
                  onClick={() => setActiveTab(previousTab)}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#000',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer', 
                    marginBottom: '2rem'
                  }}
                >
                  ← 뒤로가기
                </button>
                <h2>획득한 뱃지 ({allBadges.filter(b => b.earned).length}/{allBadges.length}개)</h2>
              </div>

              {(() => {
                const badgeGroups = {
                  '기본': ['first_problem', 'problem_streak_7', 'problem_streak_30', 'problems_10', 'problems_50', 'problems_100', 'all_easy', 'speed_master', 'hello_world', 'attendance_3days'],
                  '문법 마스터': ['korean_grammar', 'syntax_typo_monster', 'syntax_racer', 'syntax_careful', 'syntax_perfect'],
                  '코딩 실력': ['skill_newbie', 'skill_steady', 'skill_master', 'skill_genius'],
                  '논리 사고': ['logic_action_first', 'logic_trial_error', 'logic_king'],
                  '특수': ['no_hint_10', 'perfect_coder', 'persistence_king', 'all_rounder'],
                  '유머': ['unbreakable', 'night_owl', 'hint_collector', 'button_mania']
                }

                return Object.entries(badgeGroups).map(([category, badgeTypes]) => {
                  const categoryBadges = allBadges.filter(b => badgeTypes.includes(b.badge_type))
                  if (categoryBadges.length === 0) return null

                  return (
                    <div key={category} className="badge-category">
                      <h4 className="category-title">{category}</h4>
                      <div className="badge-row">
                        {categoryBadges.map(badge => {
                          const isEarned = badge.earned
                          const progress = badge.progress || {}
                          const showProgressBar = progress.condition_type === 'count' && progress.target > 0

                          return (
                            <div
                              key={badge.badge_id}
                              className={`badge-card-inline ${isEarned ? 'earned' : 'locked'}`}
                              onMouseEnter={() => setHoveredBadge(badge.badge_id)}
                              onMouseLeave={() => setHoveredBadge(null)}
                            >
                              <div className="badge-icon-inline">
                                {isEarned ? badge.icon : '🔒'}
                              </div>
                              <div className="badge-info-inline">
                                <div className="badge-name-inline">{badge.name}</div>
                                {isEarned && badge.earned_at && (
                                  <div className="badge-earned-date-inline">
                                    {new Date(badge.earned_at).toLocaleDateString()}
                                  </div>
                                )}
                                {!isEarned && showProgressBar && (
                                  <div className="badge-progress-bar">
                                    <div
                                      className="badge-progress-fill"
                                      style={{ width: `${progress.percentage}%` }}
                                    />
                                    <span className="badge-progress-text">
                                      {progress.current}/{progress.target}
                                    </span>
                                  </div>
                                )}
                              </div>

                              {/* 툴팁 */}
                              {hoveredBadge === badge.badge_id && (
                                <div className="badge-tooltip">
                                  <div className="tooltip-title">{badge.name}</div>
                                  <div className="tooltip-condition">
                                    {progress.condition_description || badge.description}
                                  </div>
                                  {isEarned && badge.earned_at && (
                                    <div className="tooltip-earned">
                                      획득일: {new Date(badge.earned_at).toLocaleDateString()}
                                    </div>
                                  )}
                                  {!isEarned && showProgressBar && (
                                    <div className="tooltip-progress">
                                      진행: {progress.current}/{progress.target} ({progress.percentage}%)
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )
                })
              })()}

              {allBadges.length === 0 && (
                <div className="empty-state">
                  <p>뱃지 정보를 불러오는 중...</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'bookmarks' && (
            <div className="bookmarks-section">
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                <button
                  className="back-btn"
                  onClick={() => setActiveTab(previousTab)}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#000',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer', 
                    marginBottom: '2rem'
                  }}
                >
                  ← 뒤로가기
                </button>
                <h2>북마크 ({bookmarks.length}개)</h2>
              </div>
              {bookmarks.length === 0 ? (
                <div className="empty-state">
                  <p>저장된 북마크가 없습니다.</p>
                  <p className="hint">챗봇 응답을 북마크해보세요!</p>
                </div>
              ) : (
                <div className="bookmarks-grid">
                  {bookmarks.map((bookmark) => (
                    <div key={bookmark.id} className="bookmark-item">
                      <p>{bookmark.content}</p>
                      <div className="bookmark-date">
                        {bookmark.created_at ? new Date(bookmark.created_at).toLocaleDateString() : ''}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default MyPage
