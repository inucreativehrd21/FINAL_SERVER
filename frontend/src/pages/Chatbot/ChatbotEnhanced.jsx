import React, { useState, useRef, useEffect } from 'react'
import api from '../../services/api'
import './ChatbotEnhanced.css'

/**
 * 향상된 챗봇 페이지 (탭 구조 + 개인화 기능)
 *
 * 탭 구조:
 * 1. 대화 - 기존 챗봇 UI
 * 2. 세션 - 대화 세션 관리
 * 3. 히스토리 - 전체 대화 기록 (카테고리 필터)
 * 4. 통계 - 사용 패턴 분석
 */
function ChatbotEnhanced() {
  const [activeTab, setActiveTab] = useState('chat') // chat | sessions | history | analytics
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '안녕하세요! 코딩에 대해 궁금한 것을 자유롭게 물어보세요.'
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const messagesEndRef = useRef(null)

  // 세션 관리
  const [sessions, setSessions] = useState([])
  const [loadingSessions, setLoadingSessions] = useState(false)

  // 히스토리
  const [history, setHistory] = useState([])
  const [historyCategory, setHistoryCategory] = useState(null)
  const [historyLimit] = useState(20)
  const [historyOffset, setHistoryOffset] = useState(0)
  const [historyTotal, setHistoryTotal] = useState(0)
  const [loadingHistory, setLoadingHistory] = useState(false)

  // 통계
  const [analytics, setAnalytics] = useState(null)
  const [loadingAnalytics, setLoadingAnalytics] = useState(false)

  // 북마크
  const [bookmarks, setBookmarks] = useState([])

  const exampleQuestions = [
    '파이썬에서 리스트와 튜플의 차이가 뭔가요?',
    'HTML에서 <div>와 <span>은 어떤 차이가 있나요?',
    'overfitting(과적합)을 줄이는 방법'
  ]

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    fetchBookmarks()
  }, [])

  // 탭 변경 시 데이터 로드
  useEffect(() => {
    if (activeTab === 'sessions') {
      fetchSessions()
    } else if (activeTab === 'history') {
      fetchHistory()
    } else if (activeTab === 'analytics') {
      fetchAnalytics()
    }
  }, [activeTab, historyCategory, historyOffset])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // === API 호출 함수들 ===

  const fetchBookmarks = async () => {
    try {
      const response = await api.get('/chatbot/bookmarks/')
      setBookmarks(response.data.data || [])
    } catch (error) {
      console.error('Failed to fetch bookmarks:', error)
    }
  }

  const fetchSessions = async () => {
    setLoadingSessions(true)
    try {
      const response = await api.get('/chatbot/sessions/')
      setSessions(response.data.data || [])
    } catch (error) {
      console.error('Failed to fetch sessions:', error)
    } finally {
      setLoadingSessions(false)
    }
  }

  const fetchHistory = async () => {
    setLoadingHistory(true)
    try {
      const params = {
        limit: historyLimit,
        offset: historyOffset
      }
      if (historyCategory) {
        params.category = historyCategory
      }

      const response = await api.get('/chatbot/history/', { params })
      setHistory(response.data.results || [])
      setHistoryTotal(response.data.count || 0)
    } catch (error) {
      console.error('Failed to fetch history:', error)
    } finally {
      setLoadingHistory(false)
    }
  }

  const fetchAnalytics = async () => {
    setLoadingAnalytics(true)
    try {
      const response = await api.get('/chatbot/analytics/', {
        params: { days: 30 }
      })
      setAnalytics(response.data)
    } catch (error) {
      console.error('Failed to fetch analytics:', error)
    } finally {
      setLoadingAnalytics(false)
    }
  }

  // === 대화 기능 ===

  const handleNewChat = () => {
    setMessages([
      {
        role: 'assistant',
        content: '안녕하세요! 코딩에 대해 궁금한 것을 자유롭게 물어보세요.'
      }
    ])
    setInput('')
    setCurrentSessionId(null)
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])

    const currentInput = input
    setInput('')
    setLoading(true)

    try {
      const response = await api.post('/chatbot/chat/', {
        message: currentInput,
        session_id: currentSessionId
      })

      if (response.data.success) {
        if (!currentSessionId && response.data.session_id) {
          setCurrentSessionId(response.data.session_id)
        }

        const assistantMessage = {
          role: 'assistant',
          content: response.data.data.response,
          sources: response.data.data.sources || [],
          related_questions: response.data.data.related_questions || [], // NEW!
          message_id: response.data.message_id // 피드백용
        }

        setMessages(prev => [...prev, assistantMessage])
      } else {
        const errorMessage = {
          role: 'assistant',
          content: `오류: ${response.data.error || '알 수 없는 오류가 발생했습니다.'}`
        }
        setMessages(prev => [...prev, errorMessage])
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      const errorMessage = {
        role: 'assistant',
        content: '죄송합니다. 응답을 생성하는 중 오류가 발생했습니다.'
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleBookmark = async (messageIndex) => {
    const message = messages[messageIndex]
    if (message.role !== 'assistant') return

    try {
      await api.post('/chatbot/bookmark/', {
        content: message.content,
        sources: message.sources
      })

      alert('북마크에 추가되었습니다.')
      fetchBookmarks()
    } catch (error) {
      console.error('Failed to bookmark:', error)
      alert('북마크 추가에 실패했습니다.')
    }
  }

  const handleCopy = (content) => {
    navigator.clipboard.writeText(content)
    alert('클립보드에 복사되었습니다.')
  }

  const handleDeleteBookmark = async (bookmarkId) => {
    try {
      await api.delete(`/chatbot/bookmark/${bookmarkId}/`)
      fetchBookmarks()
    } catch (error) {
      console.error('Failed to delete bookmark:', error)
      alert('북마크 삭제에 실패했습니다.')
    }
  }

  // NEW: 피드백 제출
  const handleFeedback = async (messageId, isHelpful) => {
    try {
      await api.post('/chatbot/feedback/', {
        message_id: messageId,
        is_helpful: isHelpful
      })
      alert(isHelpful ? '도움이 되었다는 피드백을 저장했습니다.' : '피드백을 저장했습니다.')
    } catch (error) {
      console.error('Failed to submit feedback:', error)
      alert('피드백 저장에 실패했습니다.')
    }
  }

  // NEW: 관련 질문 클릭
  const handleRelatedQuestion = (question) => {
    setInput(question)
  }

  // === 세션 관리 ===

  const handleLoadSession = async (sessionId) => {
    try {
      const response = await api.get(`/chatbot/sessions/${sessionId}/`)
      const sessionData = response.data.data

      // 메시지 로드
      const loadedMessages = sessionData.messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        sources: msg.sources || [],
        message_id: msg.id
      }))

      setMessages(loadedMessages)
      setCurrentSessionId(sessionId)
      setActiveTab('chat')
    } catch (error) {
      console.error('Failed to load session:', error)
      alert('세션 로드에 실패했습니다.')
    }
  }

  const handleDeleteSession = async (sessionId) => {
    if (!confirm('이 세션을 삭제하시겠습니까?')) return

    try {
      await api.delete(`/chatbot/sessions/${sessionId}/delete/`)
      fetchSessions()
    } catch (error) {
      console.error('Failed to delete session:', error)
      alert('세션 삭제에 실패했습니다.')
    }
  }

  // 답변 본문 포맷팅
  const formatAnswerContent = (content) => {
    const parts = content.split(/📚\s*참고[:：]\s*/i)
    let text = parts[0].trim()
    text = text.replace(/([.!?])\s*([•\-\*·])\s*/g, '$1\n\n$2 ')
    text = text.replace(/^([•\-\*·])\s*/gm, '$1 ')
    text = text.replace(/([.!?])\s*(\d+[.)]\s*|[*]{0,2}\d+단계[:：])/g, '$1\n\n$2')
    text = text.replace(/\n\s*\n/g, '\n\n')
    return text
  }

  // === 렌더링 함수들 ===

  const renderChatTab = () => (
    <div className="chat-tab">
      <div className="chat-section">
        <div className="chat-header">
          <div className="bot-icon">🤖</div>
          <p>안녕하세요! 코딩에 대해 궁금한 것을 자유롭게 물어보세요.</p>
        </div>

        <div className="example-questions">
          <div className="example-label">💡 예시 질문</div>
          {exampleQuestions.map((question, index) => (
            <button
              key={index}
              className="example-btn"
              onClick={() => setInput(question)}
            >
              {question}
            </button>
          ))}
        </div>

        <div className="messages-container">
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              <div className="message-avatar">
                {message.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-content">
                <div className="message-text" style={{ whiteSpace: 'pre-wrap', lineHeight: '1.8' }}>
                  {message.role === 'assistant'
                    ? formatAnswerContent(message.content)
                    : message.content
                  }
                </div>

                {/* Sources */}
                {message.sources && message.sources.length > 0 && (
                  <div className="message-sources">
                    <ul>
                      {message.sources.map((source, idx) => (
                        <li key={idx}>
                          {typeof source === 'string' ? (
                            <span className="source-content">{source}</span>
                          ) : (
                            <>
                              <span className="source-content">
                                {source.content?.substring(0, 150) || source.chunk_id || 'Source'}
                                {source.content && source.content.length > 150 && '...'}
                              </span>
                              {source.url && (
                                <a
                                  href={source.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="source-link"
                                >
                                  🔗 원본 보기
                                </a>
                              )}
                              {source.score && (
                                <span className="source-score">
                                  (관련도: {(source.score * 100).toFixed(0)}%)
                                </span>
                              )}
                            </>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* NEW: Related Questions */}
                {message.related_questions && message.related_questions.length > 0 && (
                  <div className="related-questions">
                    <div className="related-label">💡 관련 질문:</div>
                    {message.related_questions.map((question, idx) => (
                      <button
                        key={idx}
                        className="related-question-btn"
                        onClick={() => handleRelatedQuestion(question)}
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                )}

                {message.role === 'assistant' && (
                  <div className="message-actions">
                    <button
                      className="action-btn"
                      onClick={() => handleBookmark(index)}
                      title="북마크"
                    >
                      ⭐
                    </button>
                    <button
                      className="action-btn"
                      onClick={() => handleCopy(message.content)}
                      title="복사"
                    >
                      📋
                    </button>
                    {/* NEW: Feedback buttons */}
                    {message.message_id && (
                      <>
                        <button
                          className="action-btn feedback-positive"
                          onClick={() => handleFeedback(message.message_id, true)}
                          title="도움이 되었어요"
                        >
                          👍
                        </button>
                        <button
                          className="action-btn feedback-negative"
                          onClick={() => handleFeedback(message.message_id, false)}
                          title="도움이 안되었어요"
                        >
                          👎
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="message assistant">
              <div className="message-avatar">🤖</div>
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="질문을 입력하세요."
            disabled={loading}
          />
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={loading || !input.trim()}
          >
            전송
          </button>
        </div>

        <button className="new-chat-btn" onClick={handleNewChat}>
          새로운 대화 시작
        </button>
      </div>

      {/* Sidebar: Bookmarks */}
      <div className="history-section">
        <div className="sidebar-block">
          <div className="history-header">
            <span>⭐ 북마크 ({bookmarks.length})</span>
          </div>

          <div className="history-list">
            {bookmarks.length === 0 ? (
              <div className="no-history">
                <p>저장된 북마크가 없습니다.</p>
              </div>
            ) : (
              bookmarks.map((bookmark) => (
                <div key={bookmark.id} className="bookmark-item-mini">
                  <div className="bookmark-content-mini">{bookmark.content}</div>
                  <div className="bookmark-actions-mini">
                    <button
                      className="action-btn-mini"
                      onClick={() => handleCopy(bookmark.content)}
                      title="복사"
                    >
                      📋
                    </button>
                    <button
                      className="action-btn-mini delete"
                      onClick={() => handleDeleteBookmark(bookmark.id)}
                      title="삭제"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )

  const renderSessionsTab = () => (
    <div className="sessions-tab">
      <div className="tab-header">
        <h2>💬 대화 세션 관리</h2>
        <p>이전 대화를 불러오거나 삭제할 수 있습니다.</p>
      </div>

      {loadingSessions ? (
        <div className="loading-state">세션 로딩 중...</div>
      ) : sessions.length === 0 ? (
        <div className="empty-state">
          <p>저장된 세션이 없습니다.</p>
        </div>
      ) : (
        <div className="sessions-list">
          {sessions.map((session) => (
            <div key={session.id} className="session-item">
              <div className="session-info">
                <div className="session-title">{session.title}</div>
                <div className="session-meta">
                  {new Date(session.created_at).toLocaleDateString()} • {session.messages?.length || 0}개 메시지
                </div>
              </div>
              <div className="session-actions">
                <button
                  className="session-btn load"
                  onClick={() => handleLoadSession(session.id)}
                >
                  불러오기
                </button>
                <button
                  className="session-btn delete"
                  onClick={() => handleDeleteSession(session.id)}
                >
                  삭제
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )

  const renderHistoryTab = () => (
    <div className="history-tab">
      <div className="tab-header">
        <h2>📚 전체 대화 기록</h2>
        <div className="history-filters">
          <label>카테고리:</label>
          <select
            value={historyCategory || ''}
            onChange={(e) => {
              setHistoryCategory(e.target.value || null)
              setHistoryOffset(0)
            }}
          >
            <option value="">전체</option>
            <option value="git">Git</option>
            <option value="python">Python</option>
            <option value="general">General</option>
            <option value="unknown">Unknown</option>
          </select>
        </div>
      </div>

      {loadingHistory ? (
        <div className="loading-state">기록 로딩 중...</div>
      ) : history.length === 0 ? (
        <div className="empty-state">
          <p>대화 기록이 없습니다.</p>
        </div>
      ) : (
        <>
          <div className="history-list-full">
            {history.map((item) => (
              <div key={item.id} className="history-item-full">
                <div className="history-question">
                  <strong>Q:</strong> {item.question}
                </div>
                <div className="history-answer">
                  <strong>A:</strong> {item.answer.substring(0, 200)}...
                </div>
                <div className="history-meta">
                  <span className="history-category">{item.category}</span>
                  <span className="history-date">
                    {new Date(item.created_at).toLocaleDateString()}
                  </span>
                  {item.is_helpful !== null && (
                    <span className="history-feedback">
                      {item.is_helpful ? '👍 도움됨' : '👎'}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div className="pagination">
            <button
              disabled={historyOffset === 0}
              onClick={() => setHistoryOffset(prev => Math.max(0, prev - historyLimit))}
            >
              이전
            </button>
            <span>
              {historyOffset + 1} - {Math.min(historyOffset + historyLimit, historyTotal)} / {historyTotal}
            </span>
            <button
              disabled={historyOffset + historyLimit >= historyTotal}
              onClick={() => setHistoryOffset(prev => prev + historyLimit)}
            >
              다음
            </button>
          </div>
        </>
      )}
    </div>
  )

  const renderAnalyticsTab = () => {
    if (loadingAnalytics) {
      return <div className="loading-state">통계 로딩 중...</div>
    }

    if (!analytics || !analytics.has_data) {
      return (
        <div className="empty-state">
          <p>아직 통계 데이터가 없습니다. 챗봇을 사용해보세요!</p>
        </div>
      )
    }

    return (
      <div className="analytics-tab">
        <div className="tab-header">
          <h2>📊 사용 통계 (최근 30일)</h2>
        </div>

        <div className="analytics-cards">
          {/* Peak Time */}
          {analytics.peak_time && (
            <div className="analytics-card">
              <div className="card-icon">⏰</div>
              <div className="card-content">
                <div className="card-label">주 사용 시간</div>
                <div className="card-value">
                  {analytics.peak_time.label} ({analytics.peak_time.hour_range})
                </div>
                <div className="card-detail">
                  {analytics.peak_time.usage_count}회 사용
                </div>
              </div>
            </div>
          )}

          {/* Favorite Category */}
          {analytics.favorite_category && (
            <div className="analytics-card">
              <div className="card-icon">📚</div>
              <div className="card-content">
                <div className="card-label">선호 주제</div>
                <div className="card-value">{analytics.favorite_category.name}</div>
              </div>
            </div>
          )}

          {/* Weekly Stats */}
          {analytics.weekly_stats && (
            <div className="analytics-card">
              <div className="card-icon">📈</div>
              <div className="card-content">
                <div className="card-label">이번 주 활동</div>
                <div className="card-value">
                  {analytics.weekly_stats.this_week}개 질문
                </div>
                <div className={`card-detail ${analytics.weekly_stats.growth >= 0 ? 'positive' : 'negative'}`}>
                  지난주 대비 {analytics.weekly_stats.growth >= 0 ? '+' : ''}{analytics.weekly_stats.growth}%
                </div>
              </div>
            </div>
          )}

          {/* Total Questions */}
          <div className="analytics-card">
            <div className="card-icon">💬</div>
            <div className="card-content">
              <div className="card-label">총 질문 수</div>
              <div className="card-value">{analytics.total_questions}개</div>
              <div className="card-detail">
                평균 응답 시간: {analytics.avg_response_time}초
              </div>
            </div>
          </div>
        </div>

        {/* Category Stats */}
        {analytics.category_stats && (
          <div className="category-stats">
            <h3>카테고리별 분포</h3>
            <div className="category-bars">
              {Object.entries(analytics.category_stats).map(([category, data]) => (
                <div key={category} className="category-bar">
                  <div className="category-name">{category}</div>
                  <div className="category-progress">
                    <div
                      className="category-fill"
                      style={{ width: `${data.percentage}%` }}
                    />
                  </div>
                  <div className="category-stats-text">
                    {data.count}개 ({data.percentage}%)
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="chatbot-enhanced">
      {/* Tab Navigation */}
      <div className="tab-navigation">
        <button
          className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          💬 대화
        </button>
        <button
          className={`tab-btn ${activeTab === 'sessions' ? 'active' : ''}`}
          onClick={() => setActiveTab('sessions')}
        >
          📂 세션
        </button>
        <button
          className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          📚 히스토리
        </button>
        <button
          className={`tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          📊 통계
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'chat' && renderChatTab()}
        {activeTab === 'sessions' && renderSessionsTab()}
        {activeTab === 'history' && renderHistoryTab()}
        {activeTab === 'analytics' && renderAnalyticsTab()}
      </div>
    </div>
  )
}

export default ChatbotEnhanced
