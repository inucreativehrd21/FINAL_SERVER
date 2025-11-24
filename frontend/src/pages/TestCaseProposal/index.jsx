import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import api from '../../services/api'
import './TestCaseProposal.css'

function TestCaseProposal() {
  const navigate = useNavigate()
  const [problems, setProblems] = useState([])
  const [formData, setFormData] = useState({
    problem_id: '',
    input_data: '',
    expected_output: '',
    description: ''
  })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState({ type: '', text: '' })
  const [testCode, setTestCode] = useState('# 여기에 테스트용 코드를 작성하세요\n\n')
  const [testOutput, setTestOutput] = useState('')
  const [testLoading, setTestLoading] = useState(false)

  useEffect(() => {
    // Load problems for selection
    fetch('/problems.json')
      .then(response => response.json())
      .then(data => setProblems(data))
      .catch(error => console.error('Failed to load problems:', error))
  }, [])

  useEffect(() => {
    // Load template when problem is selected
    if (formData.problem_id) {
      const problem = problems.find(p => p.problem_id === formData.problem_id)
      if (problem && problem.template) {
        setTestCode(problem.template)
      }
    }
  }, [formData.problem_id, problems])

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleTestCode = async () => {
    setTestLoading(true)
    setTestOutput('코드 실행 중...\n')

    try {
      const response = await api.post('/coding-test/execute/', {
        problem_id: formData.problem_id,
        code: testCode,
        language: 'python',
        custom_inputs: formData.input_data ? [formData.input_data] : []
      })

      if (response.data.success) {
        const results = response.data.data.results
        let output = '=== 테스트 실행 결과 ===\n\n'

        results.forEach((result, idx) => {
          // 마지막 결과가 제안된 테스트 케이스인지 확인
          const isProposedTest = idx === results.length - 1

          output += `[테스트 ${idx + 1}${isProposedTest ? ' - 제안된 테스트 케이스' : ' - 기존 테스트 케이스'}]\n`
          output += `입력: ${result.input || '(없음)'}\n`

          if (result.error) {
            output += `에러: ${result.error}\n\n`
          } else {
            output += `실제 출력: ${result.output || '(출력 없음)'}\n`

            // 제안된 테스트 케이스의 경우 제안된 예상 출력 사용, 기존 테스트는 원래 예상 출력 사용
            const expectedOutput = isProposedTest ? (formData.expected_output || '') : (result.expected_output || '')
            output += `예상 출력: ${expectedOutput}\n`

            const actualOutput = result.output?.trim() || ''
            const expectedTrim = expectedOutput.trim()
            const isMatch = actualOutput === expectedTrim

            if (isProposedTest) {
              output += `결과: ${isMatch ? '✅ 일치 - 제안된 테스트 케이스가 올바릅니다' : '❌ 불일치 - 테스트 케이스를 확인해주세요'}\n\n`
            } else {
              output += `결과: ${isMatch ? '✅ 통과' : '❌ 실패'}\n\n`
            }
          }
        })

        setTestOutput(output)
      } else {
        setTestOutput(`[오류]\n${response.data.data.error || '알 수 없는 오류'}`)
      }
    } catch (error) {
      console.error('Test execution error:', error)
      setTestOutput(`[실행 오류]\n${error.response?.data?.message || error.message}`)
    } finally {
      setTestLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMessage({ type: '', text: '' })

    try {
      const response = await api.post('/coding-test/test-cases/propose/', formData)

      if (response.data.success) {
        setMessage({
          type: 'success',
          text: '테스트 케이스가 성공적으로 제안되었습니다. 관리자의 승인을 기다려주세요.'
        })
        // Reset form
        setFormData({
          problem_id: '',
          input_data: '',
          expected_output: '',
          description: ''
        })
        setTestCode('# 여기에 테스트용 코드를 작성하세요\n\n')
        setTestOutput('')
      }
    } catch (error) {
      console.error('Failed to propose test case:', error)
      setMessage({
        type: 'error',
        text: error.response?.data?.message || '테스트 케이스 제안에 실패했습니다.'
      })
    } finally {
      setLoading(false)
    }
  }

  const selectedProblem = problems.find(p => p.problem_id === formData.problem_id)

  return (
    <div className="test-case-proposal-page">
      <div className="proposal-header">
        <button className="back-btn" onClick={() => navigate('/app/problems')}>
          ← 돌아가기
        </button>
        <h1>테스트 케이스 제안</h1>
        <p>문제에 대한 새로운 테스트 케이스를 제안해주세요. 관리자의 승인 후 사용됩니다.</p>
      </div>

      <div className="proposal-content">
        <form onSubmit={handleSubmit} className="proposal-form">
          <div className="form-group">
            <label htmlFor="problem_id">문제 선택 *</label>
            <select
              id="problem_id"
              name="problem_id"
              value={formData.problem_id}
              onChange={handleInputChange}
              required
            >
              <option value="">문제를 선택하세요</option>
              {problems.map(problem => (
                <option key={problem.problem_id} value={problem.problem_id}>
                  #{problem.problem_id} - {problem.title}
                </option>
              ))}
            </select>
          </div>

          {selectedProblem && (
            <div className="problem-info">
              <h3>선택된 문제: {selectedProblem.title}</h3>
              <p className="problem-description">{selectedProblem.description}</p>
              <div className="existing-examples">
                <h4>기존 예제:</h4>
                {selectedProblem.examples?.map((example, idx) => (
                  <div key={idx} className="example-item">
                    <div className="example-label">예제 {idx + 1}</div>
                    <div className="example-io">
                      <div>
                        <strong>입력:</strong>
                        <pre>{example.input}</pre>
                      </div>
                      <div>
                        <strong>출력:</strong>
                        <pre>{example.output}</pre>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="input_data">입력 데이터 *</label>
            <textarea
              id="input_data"
              name="input_data"
              value={formData.input_data}
              onChange={handleInputChange}
              placeholder="테스트 케이스 입력 데이터를 입력하세요"
              rows="6"
              required
            />
            <small>여러 줄의 입력은 줄바꿈으로 구분하세요</small>
          </div>

          <div className="form-group">
            <label htmlFor="expected_output">예상 출력 *</label>
            <textarea
              id="expected_output"
              name="expected_output"
              value={formData.expected_output}
              onChange={handleInputChange}
              placeholder="예상되는 출력 결과를 입력하세요"
              rows="6"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">설명 (선택)</label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              placeholder="이 테스트 케이스가 필요한 이유나 검증하려는 케이스를 설명해주세요"
              rows="4"
            />
          </div>

          {formData.problem_id && formData.input_data && formData.expected_output && (
            <div className="test-code-section">
              <div className="test-code-header">
                <h3>테스트 코드 작성 (선택)</h3>
                <p>제안하는 테스트 케이스가 올바른지 확인하기 위해 코드를 작성하고 실행해보세요.</p>
              </div>

              <div className="test-code-editor">
                <Editor
                  height="300px"
                  defaultLanguage="python"
                  theme="vs-dark"
                  value={testCode}
                  onChange={(value) => setTestCode(value || '')}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    tabSize: 4,
                    wordWrap: 'on',
                  }}
                />
              </div>

              <button
                type="button"
                className="tcp-test-code-btn"
                onClick={handleTestCode}
                disabled={testLoading}
              >
                {testLoading ? '실행 중...' : '▶ 테스트 코드 실행'}
              </button>

              {testOutput && (
                <div className="test-output">
                  <div className="test-output-header">실행 결과</div>
                  <pre className="test-output-content">{testOutput}</pre>
                </div>
              )}
            </div>
          )}

          {message.text && (
            <div className={`message ${message.type}`}>
              {message.text}
            </div>
          )}

          <div className="form-actions">
            <button
              type="button"
              className="tcp-cancel-btn"
              onClick={() => navigate('/app/problems')}
            >
              취소
            </button>
            <button
              type="submit"
              className="tcp-submit-btn"
              disabled={loading || !formData.problem_id}
            >
              {loading ? '제안 중...' : '테스트 케이스 제안하기'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default TestCaseProposal
