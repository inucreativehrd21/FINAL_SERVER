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
  const [outputMode, setOutputMode] = useState(2) // 1: 전체 출력, 2: 간단 출력 (기본: 간단 출력)
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
  // 힌트 방식(api/langgraph)은 관리자 설정에서 결정됨

  // COH (Chain of Hint) 관련 상태
  const [cohStatus, setCohStatus] = useState(null) // COH 상태 정보
  const [blockedComponents, setBlockedComponents] = useState([]) // 차단된 구성요소

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

      // 힌트 방식은 관리자 설정(백엔드)에서 결정됨 - 항상 기본 엔드포인트 호출
      const response = await api.post('/coding-test/hints/', {
        problem_id: problemId,
        user_code: code,
        preset: hintConfig.preset, // 힌트 프리셋
        custom_components: hintConfig.components, // 커스텀 구성 요소
        previous_hints: previousHints // Chain of Hints
      })

      if (response.data.success) {
        const newHint = response.data.data.hint
        setHint(newHint)

        // COH 상태 업데이트
        if (response.data.data.coh_status) {
          setCohStatus(response.data.data.coh_status)
        }
        if (response.data.data.blocked_components) {
          setBlockedComponents(response.data.data.blocked_components)
        }

        // 힌트 이력에 추가 (COH 정보 포함)
        const newHintEntry = {
          id: Date.now(),
          timestamp: new Date().toISOString(),
          level: hintConfig.preset,
          config: { ...hintConfig },
          hint_text: newHint,
          user_code_at_request: code,
          method: response.data.data.method || 'api', // 서버에서 사용한 방식
          hint_branch: response.data.data.hint_branch || null, // LangGraph 분기
          // COH 관련 정보
          coh_status: response.data.data.coh_status || null,
          hint_level: response.data.data.hint_level || null,
          coh_depth: response.data.data.coh_depth || 0,
          blocked_components: response.data.data.blocked_components || []
        }
        setHintHistory(prev => [...prev, newHintEntry])

        // 힌트 받은 후 자동으로 '힌트 보기' 탭으로 전환하고 최신 힌트 펼치기
        setActiveHintTab('history')
        setExpandedHintId(newHintEntry.id)
      } else {
        const errorMsg = response.data.error || '힌트를 가져오는데 실패했습니다.'
        setHint(`오류: ${errorMsg}`)
      }
    } catch (error) {
      console.error('Hint request error:', error)
      const errorMsg = error.response?.data?.error || error.message || '힌트 요청 중 오류가 발생했습니다.'
      setHint(`오류: ${errorMsg}`)
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
        code: code
      })

      if (response.data.success) {
        const { all_passed, passed_count, total_count, total_score, star_count, problem_status, test_results } = response.data

        // 별점 표시 함수
        const renderStars = (count) => {
          return '⭐'.repeat(count) + '☆'.repeat(3 - count)
        }

        // 제출 결과 출력
        let output = ''

        if (all_passed) {
          output += `✅ 모든 테스트 통과!\n`
          output += `별점: ${renderStars(star_count)} (${star_count}/3)\n`
          output += `종합 점수: ${total_score}/100\n\n`

          if (problem_status) {
            output += `문제 상태: ${problem_status.status_display}\n`
            output += `최고 점수: ${problem_status.best_score}/100\n`
            output += `최고 별점: ${renderStars(problem_status.star_count)} (${problem_status.star_count}/3)\n\n`
          }
        } else {
          output += `❌ 일부 테스트 실패\n`
          output += `통과: ${passed_count}/${total_count}\n`
          output += `종합 점수: ${total_score}/100\n`
          output += `별점: ${renderStars(0)} (테스트 통과 시 부여)\n\n`
        }

        // 테스트 결과 상세 (입출력 값은 숨김)
        output += `=== 테스트 결과 ===\n`
        test_results.forEach(test => {
          const icon = test.passed ? '✅' : '❌'
          output += `${icon} Test #${test.test_number}: ${test.description} - ${test.passed ? 'Pass' : 'Fail'}\n`
          if (!test.passed && test.error) {
            output += `   오류: ${test.error}\n`
          }
        })

        setOutput(output)
      } else {
        setOutput(`[제출 실패]\n${response.data.error || '알 수 없는 오류'}`)
      }
    } catch (error) {
      console.error('Submit error:', error)
      setOutput(`[제출 오류]\n${error.response?.data?.error || error.message}`)
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
              onChange={(value) => {
                const newCode = value || ''
                setCode(newCode)
                // 코드 변경 시 자동 저장 (사용자별, 문제별)
                if (problemId && user) {
                  const storageKey = `user_${user.id}_problem_${problemId}_code`
                  localStorage.setItem(storageKey, newCode)
                }
              }}
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

            {/* 터미널 하단 액션 버튼 */}
            <div className="terminal-footer">
              <button
                className="terminal-action-btn hint-toggle-btn"
                onClick={() => setShowHintModal(!showHintModal)}
              >
                💡 힌트
              </button>
              <div className="terminal-actions">
                <button
                  className="terminal-action-btn run-btn"
                  onClick={handleRunCode}
                  disabled={loading}
                >
                  {loading ? '실행 중...' : '실행'}
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

      {/* 힌트 팝업 */}
      {showHintModal && (
        <div className="hint-popup">
          <div className="hint-popup-header">
            <h4>💡 힌트</h4>
            <button className="hint-popup-close" onClick={() => setShowHintModal(false)}>×</button>
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
                  {/* COH 상태 표시 */}
                  {cohStatus && (
                    <div className="coh-status-section">
                      <div className="coh-status-badge">
                        <span className="coh-level-name">{cohStatus.level_name}</span>
                        <span className="coh-hint-level">레벨 {cohStatus.hint_level}/9</span>
                      </div>
                      {cohStatus.can_get_more_detailed && (
                        <p className="coh-hint-message">
                          💡 {cohStatus.next_level_hint}
                        </p>
                      )}
                      {!cohStatus.can_get_more_detailed && (
                        <p className="coh-hint-message coh-max">
                          ✨ 이미 가장 상세한 힌트 레벨입니다.
                        </p>
                      )}
                    </div>
                  )}

                  <div className="hint-preset-section">
                    <h4>힌트 프리셋 (💡 요약 설명 방식만 변경됩니다)</h4>
                    <div className="preset-buttons">
                      <button
                        className={`preset-btn ${hintConfig.preset === '초급' ? 'active' : ''}`}
                        onClick={() => {
                          // 초급 (레벨 4): 모든 구성요소 허용
                          setHintConfig({
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
                          setCohStatus(null)
                          setBlockedComponents([]) // 초급: 차단 없음
                        }}
                      >
                        초급
                      </button>
                      <button
                        className={`preset-btn ${hintConfig.preset === '중급' ? 'active' : ''}`}
                        onClick={() => {
                          // 중급 (레벨 7): code_example, step_by_step 차단 (libraries는 허용)
                          setHintConfig({
                            preset: '중급',
                            components: {
                              summary: true,
                              libraries: true,
                              code_example: false,
                              step_by_step: false,
                              complexity_hint: true,
                              edge_cases: false,
                              improvements: false
                            }
                          })
                          setCohStatus(null)
                          setBlockedComponents(['code_example', 'step_by_step'])
                        }}
                      >
                        중급
                      </button>
                      <button
                        className={`preset-btn ${hintConfig.preset === '고급' ? 'active' : ''}`}
                        onClick={() => {
                          // 고급 (레벨 9): libraries, code_example, step_by_step 차단
                          setHintConfig({
                            preset: '고급',
                            components: {
                              summary: true,
                              libraries: false,
                              code_example: false,
                              step_by_step: false,
                              complexity_hint: true,
                              edge_cases: true,
                              improvements: true
                            }
                          })
                          setCohStatus(null)
                          setBlockedComponents(['libraries', 'code_example', 'step_by_step'])
                        }}
                      >
                        고급
                      </button>
                    </div>
                  </div>

                  <div className="hint-custom-section">
                    <h4>힌트 구성 요소 (💡 요약은 항상 포함됩니다)</h4>
                    <div className="hint-options">
                      {[
                        // 순서: 차단되는 것들을 위에 배치 (위에서부터 차단됨)
                        { key: 'code_example', label: '코드 예시' },      // 중급/고급 차단
                        { key: 'step_by_step', label: '단계별 방법' },    // 중급/고급 차단
                        { key: 'libraries', label: '라이브러리' },        // 고급에서만 차단
                        { key: 'complexity_hint', label: '복잡도 힌트' }, // 항상 허용
                        { key: 'edge_cases', label: '엣지 케이스' },      // 항상 허용
                        { key: 'improvements', label: '개선 사항' }       // 항상 허용
                      ].map(({ key, label }) => {
                        const isBlocked = blockedComponents.includes(key)
                        return (
                          <div key={key} className={`hint-option ${isBlocked ? 'blocked' : ''}`}>
                            <input
                              type="checkbox"
                              id={`hint-${key}`}
                              checked={hintConfig.components[key]}
                              disabled={isBlocked}
                              onChange={(e) => {
                                setHintConfig(prev => ({
                                  ...prev,
                                  components: {
                                    ...prev.components,
                                    [key]: e.target.checked
                                  }
                                }))
                              }}
                            />
                            <label htmlFor={`hint-${key}`}>
                              {label}
                              {isBlocked && <span className="blocked-icon">🔒</span>}
                            </label>
                          </div>
                        )
                      })}
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
                                {historyItem.coh_status?.level_name || historyItem.level || '커스텀'}
                              </span>
                              {historyItem.hint_level && (
                                <span className="hint-history-coh-level">
                                  Lv.{historyItem.hint_level}
                                </span>
                              )}
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
                                {/* COH 정보 표시 */}
                                {historyItem.coh_status && (
                                  <div className="hint-history-coh-info">
                                    <span className="coh-badge">
                                      {historyItem.coh_status.level_name}
                                    </span>
                                    <span className="coh-detail">
                                      레벨 {historyItem.hint_level}/9
                                      {historyItem.coh_depth > 0 && ` (COH ${historyItem.coh_depth})`}
                                    </span>
                                    {/* summary 외의 차단된 구성요소만 표시 */}
                                    {historyItem.blocked_components?.filter(c => c !== 'summary').length > 0 && (
                                      <span className="coh-blocked">
                                        🔒 차단됨: {historyItem.blocked_components.filter(c => c !== 'summary').join(', ')}
                                      </span>
                                    )}
                                  </div>
                                )}
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

          <div className="hint-popup-footer">
            {activeHintTab === 'request' && (
              <button
                className="hint-request-btn"
                onClick={handleRequestHint}
                disabled={hintLoading}
              >
                {hintLoading ? '힌트 생성 중...' : '💡 힌트 요청'}
              </button>
            )}
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
