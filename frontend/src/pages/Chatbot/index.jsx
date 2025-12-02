/**
 * Chatbot Component (개선 버전)
 *
 * 개선사항:
 * 1. Sources 객체 타입 안전 렌더링
 * 2. Session ID 전송으로 대화 지속성 향상
 * 3. URL 링크 지원
 *
 * 복사 위치: frontend/src/pages/Chatbot/index.jsx
 *
 * 주요 변경사항:
 * - handleSend 함수에서 session_id 전송
 * - sources 렌더링 개선 (객체 타입 처리 + URL 링크)
 */

import { useState, useEffect, useRef } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import ReactMarkdown from 'react-markdown'
import api from '../../services/api'
import './Chatbot.css'

const Chatbot = () => {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const [questionHistory, setQuestionHistory] = useState([])
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    // 사용자 메시지 추가
    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])

    // 질문 기록 추가
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
      console.error('Chatbot error:', error)
      const errorMessage = {
        role: 'assistant',
        content: '서버와의 통신 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
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

  const handleNewChat = () => {
    setMessages([])
    setCurrentSessionId(null)
    setInput('')
  }

  const handleQuestionClick = (question) => {
    setInput(question)
  }

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <h2>AI 챗봇</h2>
        <button onClick={handleNewChat} className="new-chat-btn">
          새 대화
        </button>
      </div>

      <div className="chatbot-messages">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h3>무엇을 도와드릴까요?</h3>
            <p>개발 관련 질문을 자유롭게 해주세요.</p>
          </div>
        )}

        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            <div className="message-content">
              <ReactMarkdown>{message.content}</ReactMarkdown>

              {/* 🔧 개선: Sources 렌더링 (객체 타입 안전 처리 + URL 링크) */}
              {message.sources && message.sources.length > 0 && (
                <div className="sources">
                  <h4>참고 자료:</h4>
                  <ul>
                    {message.sources.map((source, idx) => (
                      <li key={idx}>
                        {/* 문자열 또는 객체 타입 처리 */}
                        {typeof source === 'string' ? (
                          // 문자열인 경우
                          <span>{source}</span>
                        ) : (
                          // 객체인 경우
                          <>
                            <span className="source-content">
                              {source.content?.substring(0, 100) || source.chunk_id || 'Source'}
                              {source.content && source.content.length > 100 && '...'}
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
            </div>
          </div>
        ))}

        {loading && (
          <div className="message assistant">
            <div className="message-content loading">
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

      {/* 질문 기록 */}
      {questionHistory.length > 0 && (
        <div className="question-history">
          <h4>최근 질문:</h4>
          <div className="history-items">
            {questionHistory.map((question, idx) => (
              <button
                key={idx}
                onClick={() => handleQuestionClick(question)}
                className="history-item"
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 입력 영역 */}
      <div className="chatbot-input">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="질문을 입력하세요..."
          disabled={loading}
          rows={3}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || loading}
          className="send-btn"
        >
          {loading ? '전송 중...' : '전송'}
        </button>
      </div>
    </div>
  )
}

export default Chatbot
