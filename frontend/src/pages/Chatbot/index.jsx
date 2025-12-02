import React, { useState, useRef, useEffect } from 'react'
import api from '../../services/api'
import './Chatbot.css'

function Chatbot() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '안녕하세요! 코딩에 대해 궁금한 것을 자유롭게 물어보세요.'
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [questionHistory, setQuestionHistory] = useState([])
  const [bookmarks, setBookmarks] = useState([])
  const [currentSessionId, setCurrentSessionId] = useState(null) // 🔧 추가: 세션 ID 관리
  const messagesEndRef = useRef(null)

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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const fetchBookmarks = async () => {
    try {
      const response = await api.get('/chatbot/bookmarks/')
      setBookmarks(response.data.data || [])
    } catch (error) {
      console.error('Failed to fetch bookmarks:', error)
    }
  }

  const handleExampleQuestion = (question) => {
    setInput(question)
  }

  const handleNewChat = () => {
    setMessages([
      {
        role: 'assistant',
        content: '안녕하세요! 코딩에 대해 궁금한 것을 자유롭게 물어보세요.'
      }
    ])
    setInput('')
    setCurrentSessionId(null) // 🔧 추가: 세션 ID 초기화
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])

    // 질문 기록에 추가 (최대 10개)
    setQuestionHistory(prev => {
      const newHistory = [input, ...prev.filter(q => q !== input)]
      return newHistory.slice(0, 10)
    })

    const currentInput = input
    setInput('')
    setLoading(true)

    try {
      // 🔧 개선: session_id 전송
      const response = await api.post('/chatbot/chat/', {
        message: currentInput,
        session_id: currentSessionId  // 기존 세션 ID 전송 (없으면 null)
      })

      if (response.data.success) {
        // 🔧 개선: 첫 응답 시 session_id 저장
        if (!currentSessionId && response.data.session_id) {
          setCurrentSessionId(response.data.session_id)
        }

        const assistantMessage = {
          role: 'assistant',
          content: response.data.data.response,
          sources: response.data.data.sources || []
        }

        setMessages(prev => [...prev, assistantMessage])
      } else {
        // 에러 메시지 표시
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

  const handleDeleteHistory = (index) => {
    setQuestionHistory(prev => prev.filter((_, i) => i !== index))
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

  // 답변 본문 포맷팅 함수 (출처 제거 + 가독성 개선)
  const formatAnswerContent = (content) => {
    // 1. "📚 참고:" 섹션 제거
    const parts = content.split(/📚\s*참고[:：]\s*/i)
    let text = parts[0].trim()

    // 2. 불릿 포인트(•, -, *, ·) 앞뒤로 줄바꿈 추가
    text = text.replace(/([.!?])\s*([•\-\*·])\s*/g, '$1\n\n$2 ')
    text = text.replace(/^([•\-\*·])\s*/gm, '$1 ')

    // 3. 숫자 리스트 (1., 2., **1단계:, 등) 포맷팅
    text = text.replace(/([.!?])\s*(\d+[.)]\s*|[*]{0,2}\d+단계[:：])/g, '$1\n\n$2')

    // 4. 단락 구분 (두 줄바꿈을 유지)
    text = text.replace(/\n\s*\n/g, '\n\n')

    return text
  }

  return (
    <div className="chatbot-page">
      <div className="chat-section">
        <div className="chat-header">
          <div className="bot-icon">🤖</div>
          <p>안녕하세요! 코딩에 대해 궁금한 것을 자유롭게 물어보세요.</p>
        </div>

        {/* 예시 질문 */}
        <div className="example-questions">
          <div className="example-label">💡 예시 질문</div>
          {exampleQuestions.map((question, index) => (
            <button
              key={index}
              className="example-btn"
              onClick={() => handleExampleQuestion(question)}
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

                {/* Sources 렌더링 (객체 타입 안전 처리 + URL 링크) */}
                {message.sources && message.sources.length > 0 && (
                  <div className="message-sources">
                    <ul>
                      {message.sources.map((source, idx) => (
                        <li key={idx}>
                          {/* 문자열 또는 객체 타입 처리 */}
                          {typeof source === 'string' ? (
                            // 문자열인 경우
                            <span className="source-content">{source}</span>
                          ) : (
                            // 객체인 경우
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
                                  title={source.url}
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

      <div className="history-section">
        {/* 질문 기록 */}
        <div className="sidebar-block">
          <div className="history-header">
            <span>📝 내 최근 질문 기록</span>
          </div>

          <div className="history-list">
            {questionHistory.length === 0 ? (
              <div className="no-history">
                <p>아직 질문 기록이 없습니다.</p>
              </div>
            ) : (
              questionHistory.slice(0, 5).map((question, index) => (
                <div key={index} className="history-item" onClick={() => handleExampleQuestion(question)}>
                  <div className="history-icon">💬</div>
                  <div className="history-question">{question}</div>
                  <button
                    className="history-delete-btn"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDeleteHistory(index)
                    }}
                    title="삭제"
                  >
                    🗑️
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 북마크 */}
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
}

export default Chatbot
