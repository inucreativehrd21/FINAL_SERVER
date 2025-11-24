import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import Editor from '@monaco-editor/react'
import api from '../../services/api'
import Chatbot from '../Chatbot'
import './CodingTest.css'

function CodingTest() {
  const { problemId } = useParams()
  const navigate = useNavigate()
  const { user } = useSelector((state) => state.auth)
  const [problem, setProblem] = useState(null)
  const [code, setCode] = useState('# 여기에 코드를 작성하세요\n\n')
  const [output, setOutput] = useState('')
  const [loading, setLoading] = useState(false)
  const [customInputs, setCustomInputs] = useState([]) // 사용자가 추가한 입력들
  const [newInput, setNewInput] = useState('') // 새 입력 필드
  const [outputMode, setOutputMode] = useState(1) // 1: 전체 출력, 2: 간단 출력
  const [executionResults, setExecutionResults] = useState(null) // 다중 실행 결과
  const [hint, setHint] = useState('') // 힌트 응답
  const [hintLoading, setHintLoading] = useState(false) // 힌트 로딩 상태
  const [hintLevel, setHintLevel] = useState(3) // 힌트 레벨 (1=초급, 2=중급, 3=고급)
  const [showHintModal, setShowHintModal] = useState(false) // 힌트 모달 표시 여부
  const [hintConfig, setHintConfig] = useState({
    preset: '초급',
    components: {
      summary: true,
      libraries: true,
      code_example: true,
      step_by_step: false,
      complexity_hint: false,
      edge_cases: false,
      improvements: false
    }
  })
  const [isChatbotOpen, setIsChatbotOpen] = useState(false) // 챗봇 열림 상태
  const [activeHintTab, setActiveHintTab] = useState('request') // 'request' 또는 'history'
  const [hintHistory, setHintHistory] = useState([]) // 힌트 이력 저장
  const [expandedHintId, setExpandedHintId] = useState(null) // 펼쳐진 힌트 ID (아코디언)

  // 리사이저 상태
  const [leftWidth, setLeftWidth] = useState(50) // 좌측 패널 너비 (%)
  const [editorHeight, setEditorHeight] = useState(65) // 에디터 높이 (%) - 터미널 높이 증가
  const [isResizingHorizontal, setIsResizingHorizontal] = useState(false)
  const [isResizingVertical, setIsResizingVertical] = useState(false)

  useEffect(() => {
    if (problemId) {
      fetch('/problems.json')
        .then(response => response.json())
        .then(data => {
          const foundProblem = data.find(p => p.problem_id === problemId)
          if (foundProblem) {
            setProblem(foundProblem)

            // localStorage에서 저장된 코드 불러오기 (사용자별로 분리)
            const storageKey = user ? `user_${user.id}_problem_${problemId}_code` : `problem_${problemId}_code`
            const savedCode = localStorage.getItem(storageKey)

            if (savedCode) {
              // 저장된 코드가 있으면 그걸 사용
              setCode(savedCode)
            } else if (foundProblem.template) {
              // 저장된 코드가 없으면 템플릿 사용
              setCode(foundProblem.template)
            }
          } else {
            setOutput('문제를 찾을 수 없습니다.')
          }
        })
        .catch(error => {
          console.error('Failed to load problem:', error)
          setOutput('문제를 불러오는데 실패했습니다.')
        })
    }
  }, [problemId, user])

  // 수평 리사이저
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isResizingHorizontal) {
        const newWidth = (e.clientX / window.innerWidth) * 100
        if (newWidth > 20 && newWidth < 80) {
          setLeftWidth(newWidth)
        }
      }
    }

    const handleMouseUp = () => {
      setIsResizingHorizontal(false)
    }

    if (isResizingHorizontal) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizingHorizontal])

  // 수직 리사이저
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isResizingVertical) {
        const container = document.querySelector('.code-panel')
        if (container) {
          const rect = container.getBoundingClientRect()
          const newHeight = ((e.clientY - rect.top) / rect.height) * 100
          if (newHeight > 20 && newHeight < 80) {
            setEditorHeight(newHeight)
          }
        }
      }
    }

    const handleMouseUp = () => {
      setIsResizingVertical(false)
    }

    if (isResizingVertical) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizingVertical])

  const handleAddCustomInput = () => {
    if (newInput.trim()) {
      setCustomInputs([...customInputs, newInput])
      setNewInput('')
    }
  }

  const handleRemoveCustomInput = (index) => {
    setCustomInputs(customInputs.filter((_, i) => i !== index))
  }

  const handleRunCode = async () => {
    // '코드 실행' 버튼 클릭 시 코드 저장 (사용자별로 분리)
    if (problemId && code && user) {
      const storageKey = `user_${user.id}_problem_${problemId}_code`
      localStorage.setItem(storageKey, code)
    }

    setLoading(true)
    setOutput('코드 실행 중...\n')
    setExecutionResults(null)

    try {
      const response = await api.post('/coding-test/execute/', {
        problem_id: problemId,
        code: code,
        language: 'python',
        custom_inputs: customInputs
      })

      if (response.data.success) {
        const results = response.data.data.results
        setExecutionResults(results)

        // 출력 모드에 따라 다르게 표시
        if (outputMode === 1) {
          // Mode 1: 전체 출력 (에러 코드 포함)
          let fullOutput = ''
          results.forEach((result, idx) => {
            fullOutput += `=== ${result.label} 실행 결과 ===\n`
            fullOutput += `[입력]\n${result.input || '(없음)'}\n\n`
            if (result.error) {
              fullOutput += `[에러]\n${result.error}\n\n`
            } else {
              fullOutput += `[출력]\n${result.output || '(출력 없음)'}\n\n`
            }
            if (result.expected_output !== null) {
              fullOutput += `[예상 출력]\n${result.expected_output}\n`
              fullOutput += `[결과] ${result.is_correct ? '✅ 정답' : '❌ 오답'}\n`
            }
            fullOutput += '\n'
          })
          setOutput(fullOutput)
        } else {
          // Mode 2: 간단 출력 (정답 여부와 에러 코드만)
          let simpleOutput = '=== 실행 결과 요약 ===\n\n'
          results.forEach((result) => {
            if (result.expected_output !== null) {
              simpleOutput += `${result.is_correct ? '✅' : '❌'} ${result.label}\n`
            } else {
              // 커스텀 입력 (예상 출력 없음)
              simpleOutput += `${result.error ? '❌' : '✅'} ${result.label}\n`
            }
          })
          setOutput(simpleOutput)
        }
      } else {
        setOutput(`[오류]\n${response.data.data.error || '알 수 없는 오류'}`)
      }
    } catch (error) {
      console.error('Code execution error:', error)
      setOutput(`[실행 오류]\n${error.response?.data?.message || error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const toggleOutputMode = () => {
    setOutputMode(outputMode === 1 ? 2 : 1)

    // 이미 실행 결과가 있으면 모드에 맞게 다시 포맷팅
    if (executionResults) {
      if (outputMode === 1) {
        // 현재 Mode 1이면 Mode 2로 전환 (간단 출력)
        let simpleOutput = '=== 실행 결과 요약 ===\n\n'
        executionResults.forEach((result) => {
          if (result.expected_output !== null) {
            simpleOutput += `${result.is_correct ? '✅' : '❌'} ${result.label}\n`
          } else {
            // 커스텀 입력 (예상 출력 없음)
            simpleOutput += `${result.error ? '❌' : '✅'} ${result.label}\n`
          }
        })
        setOutput(simpleOutput)
      } else {
        // 현재 Mode 2이면 Mode 1로 전환
        let fullOutput = ''
        executionResults.forEach((result, idx) => {
          fullOutput += `=== ${result.label} 실행 결과 ===\n`
          fullOutput += `[입력]\n${result.input || '(없음)'}\n\n`
          if (result.error) {
            fullOutput += `[에러]\n${result.error}\n\n`
          } else {
            fullOutput += `[출력]\n${result.output || '(출력 없음)'}\n\n`
          }
          if (result.expected_output !== null) {
            fullOutput += `[예상 출력]\n${result.expected_output}\n`
            fullOutput += `[결과] ${result.is_correct ? '✅ 정답' : '❌ 오답'}\n`
          }
          fullOutput += '\n'
        })
        setOutput(fullOutput)
      }
    }
  }

  const handleRequestHint = async () => {
    setHintLoading(true)
    setHint('')

    try {
      // 이전 힌트 이력 준비
      const previousHints = hintHistory.map(h => ({
        hint_text: h.hint_text,
        level: h.level,
        timestamp: h.timestamp
      }))

      const response = await api.post('/coding-test/hints/', {
        problem_id: problemId,
        user_code: code,
        hint_config: hintConfig, // 커스텀 힌트 구성 전송
        previous_hints: previousHints // Chain of Hints
      })

      if (response.data.success) {
        const newHint = response.data.data.hint
        setHint(newHint)

        // 힌트 이력에 추가
        const newHintEntry = {
          id: Date.now(),
          timestamp: new Date().toISOString(),
          level: hintConfig.preset,
          config: { ...hintConfig },
          hint_text: newHint,
          user_code_at_request: code
        }
        setHintHistory(prev => [...prev, newHintEntry])

        // 힌트 받은 후 자동으로 '힌트 보기' 탭으로 전환하고 최신 힌트 펼치기
        setActiveHintTab('history')
        setExpandedHintId(newHintEntry.id)
      } else {
        setHint('힌트를 가져오는데 실패했습니다.')
      }
    } catch (error) {
      console.error('Hint request error:', error)
      setHint('힌트 요청 중 오류가 발생했습니다.')
    } finally {
      setHintLoading(false)
    }
  }

  const handleSubmit = async () => {
    setLoading(true)
    setOutput('제출 중...\n')

    try {
      const response = await api.post('/coding-test/submit/', {
        problem_id: problemId,
        code: code,
        language: 'python'
      })

      const result = response.data.data
      if (result.passed) {
        setOutput(`✅ 정답입니다!\n통과한 테스트: ${result.passed_tests}/${result.total_tests}`)
      } else {
        setOutput(`❌ 오답입니다.\n통과한 테스트: ${result.passed_tests}/${result.total_tests}\n\n${result.error || ''}`)
      }
    } catch (error) {
      console.error('Submit error:', error)
      setOutput(`[제출 오류]\n${error.response?.data?.message || error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleBack = () => {
    navigate('/app/problems')
  }

  if (!problemId || !problem) {
    return (
      <div className="coding-test-fullpage">
        <div className="error-container">
          <h2>문제를 찾을 수 없습니다</h2>
          <button onClick={handleBack} className="back-btn">문제 목록으로 돌아가기</button>
        </div>
      </div>
    )
  }

  return (
    <div className="coding-test-fullpage">
      <div className="coding-test-content">
        <div className="problem-panel" style={{ width: `${leftWidth}%` }}>
          <div className="problem-panel-header">
            <button onClick={handleBack} className="back-btn">← 문제 목록</button>
            <h2>#{problem.problem_id} - {problem.title}</h2>
          </div>
          <div className="problem-header-info">
            {problem.step_title && (
              <div className="problem-category">{problem.step_title}</div>
            )}
            <div className="problem-level">Level {problem.level}</div>
          </div>

          <div className="problem-section">
            <h3>문제 설명</h3>
            <p>{problem.description}</p>
          </div>

          {problem.input_description && (
            <div className="problem-section">
              <h3>입력</h3>
              <p>{problem.input_description}</p>
            </div>
          )}

          {problem.output_description && (
            <div className="problem-section">
              <h3>출력</h3>
              <p>{problem.output_description}</p>
            </div>
          )}

          {problem.examples && problem.examples.length > 0 && (
            <div className="problem-section">
              <h3>예제</h3>
              {problem.examples.map((example, index) => (
                <div key={index} className="example">
                  <div className="example-label">예제 입력 {index + 1}</div>
                  <pre className="example-content">{example.input}</pre>
                  <div className="example-label">예제 출력 {index + 1}</div>
                  <pre className="example-content">{example.output}</pre>
                </div>
              ))}
            </div>
          )}

          <div className="problem-section">
            <h3>커스텀 입력 추가</h3>
            <div className="custom-input-area">
              <textarea
                placeholder="테스트할 입력을 추가하세요 (여러 줄 가능)"
                value={newInput}
                onChange={(e) => setNewInput(e.target.value)}
                rows="3"
              />
              <button onClick={handleAddCustomInput} className="add-input-btn">
                + 입력 추가
              </button>
            </div>

            {customInputs.length > 0 && (
              <div className="custom-inputs-list">
                <h4>추가된 커스텀 입력 ({customInputs.length}개)</h4>
                {customInputs.map((input, index) => (
                  <div key={index} className="custom-input-item">
                    <div className="custom-input-label">커스텀 입력 {index + 1}</div>
                    <pre className="custom-input-content">{input}</pre>
                    <button
                      onClick={() => handleRemoveCustomInput(index)}
                      className="remove-input-btn"
                    >
                      삭제
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {problem.tags && problem.tags.length > 0 && (
            <div className="problem-section">
              <h3>태그</h3>
              <div className="tags">
                {problem.tags.map((tag, index) => (
                  <span key={index} className="tag">{tag}</span>
                ))}
              </div>
            </div>
          )}

          {problem.url && (
            <div className="problem-section">
              <a href={problem.url} target="_blank" rel="noopener noreferrer" className="problem-link">
                원본 문제 보기 →
              </a>
            </div>
          )}
        </div>

        {/* 수평 리사이저 */}
        <div
          className="resizer horizontal"
          onMouseDown={() => setIsResizingHorizontal(true)}
        />

        <div className="code-panel" style={{ width: `${100 - leftWidth}%` }}>
          <div className="editor-section" style={{ height: `${editorHeight}%` }}>
            <div className="editor-header">
              <span>Python 3</span>
            </div>
            <Editor
              height="calc(100% - 32px)"
              defaultLanguage="python"
              theme="vs-dark"
              value={code}
              onChange={(value) => setCode(value || '')}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                roundedSelection: false,
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 4,
                wordWrap: 'on',
              }}
            />
          </div>

          {/* 수직 리사이저 */}
          <div
            className="resizer vertical"
            onMouseDown={() => setIsResizingVertical(true)}
          />

          <div className="terminal-section" style={{ height: `${100 - editorHeight}%` }}>
            <div className="terminal-header">
              <span>실행 결과</span>
              {executionResults && (
                <button
                  className="output-mode-toggle"
                  onClick={toggleOutputMode}
                  title={outputMode === 1 ? '간단한 결과로 보기' : '전체 결과로 보기'}
                >
                  {outputMode === 1 ? '📋 간단히 보기' : '📄 전체 보기'}
                </button>
              )}
            </div>
            <pre className="terminal-content">
              {output || '코드를 실행하면 결과가 여기에 표시됩니다.'}
            </pre>

            {/* 터미널 하단 우측 버튼 영역 */}
            <div className="terminal-footer">
              <div className="terminal-actions">
                <button
                  className="terminal-action-btn hint-btn"
                  onClick={() => setShowHintModal(true)}
                  disabled={hintLoading}
                >
                  {hintLoading ? '힌트 생성 중...' : '💡 힌트'}
                </button>
                <button
                  className="terminal-action-btn run-btn"
                  onClick={handleRunCode}
                  disabled={loading}
                >
                  {loading ? '실행 중...' : '▶ 실행'}
                </button>
                <button
                  className="terminal-action-btn submit-btn"
                  onClick={handleSubmit}
                  disabled={loading}
                >
                  제출
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 힌트 미니 모달 */}
      {showHintModal && (
        <div className="hint-modal-overlay" onClick={() => setShowHintModal(false)}>
          <div className="hint-mini-modal" onClick={(e) => e.stopPropagation()}>
            <div className="hint-modal-header">
              <h3>💡 힌트</h3>
              <button className="hint-modal-close" onClick={() => setShowHintModal(false)}>×</button>
            </div>

            {/* 탭 버튼 */}
            <div className="hint-modal-tabs">
              <button
                className={`hint-tab ${activeHintTab === 'request' ? 'active' : ''}`}
                onClick={() => setActiveHintTab('request')}
              >
                💡 힌트 요청
              </button>
              <button
                className={`hint-tab ${activeHintTab === 'history' ? 'active' : ''}`}
                onClick={() => setActiveHintTab('history')}
              >
                📜 힌트 보기
              </button>
            </div>

            <div className="hint-modal-body">
              {/* 힌트 요청 탭 */}
              {activeHintTab === 'request' && (
                <>
                  <div className="hint-preset-section">
                    <h4>프리셋 선택</h4>
                    <div className="preset-buttons">
                      <button
                        className={`preset-btn ${hintConfig.preset === '초급' ? 'active' : ''}`}
                        onClick={() => setHintConfig({
                          preset: '초급',
                          components: {
                            summary: true, libraries: true, code_example: true,
                            step_by_step: false, complexity_hint: false,
                            edge_cases: false, improvements: false
                          }
                        })}
                      >
                        초급
                      </button>
                      <button
                        className={`preset-btn ${hintConfig.preset === '중급' ? 'active' : ''}`}
                        onClick={() => setHintConfig({
                          preset: '중급',
                          components: {
                            summary: true, libraries: true, code_example: false,
                            step_by_step: false, complexity_hint: false,
                            edge_cases: false, improvements: false
                          }
                        })}
                      >
                        중급
                      </button>
                      <button
                        className={`preset-btn ${hintConfig.preset === '고급' ? 'active' : ''}`}
                        onClick={() => setHintConfig({
                          preset: '고급',
                          components: {
                            summary: true, libraries: false, code_example: false,
                            step_by_step: false, complexity_hint: false,
                            edge_cases: false, improvements: false
                          }
                        })}
                      >
                        고급
                      </button>
                    </div>
                  </div>

                  <div className="hint-custom-section">
                    <h4>커스텀 구성</h4>
                    <div className="hint-options">
                      {[
                        { key: 'summary', label: '요약' },
                        { key: 'libraries', label: '라이브러리' },
                        { key: 'code_example', label: '코드 예시' },
                        { key: 'step_by_step', label: '단계별 방법' },
                        { key: 'complexity_hint', label: '복잡도 힌트' },
                        { key: 'edge_cases', label: '엣지 케이스' },
                        { key: 'improvements', label: '개선 사항' }
                      ].map(({ key, label }) => (
                        <div key={key} className="hint-option">
                          <input
                            type="checkbox"
                            id={`hint-${key}`}
                            checked={hintConfig.components[key]}
                            onChange={(e) => {
                              setHintConfig({
                                preset: null,
                                components: {
                                  ...hintConfig.components,
                                  [key]: e.target.checked
                                }
                              })
                            }}
                          />
                          <label htmlFor={`hint-${key}`}>{label}</label>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* 힌트 보기 탭 */}
              {activeHintTab === 'history' && (
                <div className="hint-history-section">
                  {hintHistory.length === 0 ? (
                    <div className="hint-history-empty">
                      <p>💡 아직 요청한 힌트가 없습니다.</p>
                    </div>
                  ) : (
                    <div className="hint-history-list">
                      {[...hintHistory].reverse().map((historyItem, index) => {
                        const isExpanded = expandedHintId === historyItem.id
                        return (
                          <div key={historyItem.id} className="hint-history-item">
                            <div
                              className="hint-history-header"
                              onClick={() => setExpandedHintId(isExpanded ? null : historyItem.id)}
                            >
                              <span className="hint-history-number">
                                힌트 {hintHistory.length - index}
                              </span>
                              <span className="hint-history-level">
                                {historyItem.level || '커스텀'}
                              </span>
                              <span className="hint-history-time">
                                {new Date(historyItem.timestamp).toLocaleString('ko-KR', {
                                  month: 'short',
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })}
                              </span>
                              <span className="hint-accordion-icon">
                                {isExpanded ? '▼' : '▶'}
                              </span>
                            </div>
                            {isExpanded && (
                              <div className="hint-history-content">
                                {historyItem.hint_text}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="hint-modal-footer">
              <button className="hint-close-btn" onClick={() => setShowHintModal(false)}>
                닫기
              </button>
              {activeHintTab === 'request' && (
                <div className="hint-action-buttons">
                  <button
                    className="hint-request-btn"
                    onClick={handleRequestHint}
                    disabled={hintLoading}
                  >
                    {hintLoading ? '힌트 생성 중...' : '💡 힌트 요청'}
                  </button>
                  <button
                    className="solution-btn"
                    onClick={() => {
                      if (window.confirm('정답을 확인하시겠습니까? 학습 효과가 떨어질 수 있습니다.')) {
                        alert('정답 보기 기능은 준비 중입니다.')
                      }
                    }}
                  >
                    ✅ 정답 보기
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 챗봇 플로팅 버튼 */}
      <button
        className={`chatbot-float-btn ${isChatbotOpen ? 'active' : ''}`}
        onClick={() => setIsChatbotOpen(!isChatbotOpen)}
        title="챗봇 열기/닫기"
      >
        {isChatbotOpen ? '×' : '💬'}
      </button>

      {/* 챗봇 팝업 - 대화 내용만 표시 */}
      {isChatbotOpen && (
        <div className="chatbot-popup">
          <div className="chatbot-header">
            <h4>💬 AI 챗봇</h4>
            <button
              className="chatbot-close-btn"
              onClick={() => setIsChatbotOpen(false)}
            >
              ×
            </button>
          </div>
          <div className="chatbot-messages">
            {/* 챗봇 대화 내용 표시 영역 */}
            <Chatbot compact={true} />
          </div>
        </div>
      )}

    </div>
  )
}

export default CodingTest
