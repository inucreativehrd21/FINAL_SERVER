import React, { useState, useEffect } from 'react'
import Editor from '@monaco-editor/react'
import api from '../../services/api'
import './AdminPanel.css'
import './AdminPanelTestcases.css'
import ModelsTab from './tabs/ModelsTab'
import UsersTab from './tabs/UsersTab'
import ProblemsTab from './tabs/ProblemsTab'
import TestCasesTab from './tabs/TestCasesTab'
import SolutionsTab from './tabs/SolutionsTab'

function AdminPanel() {
  const [activeTab, setActiveTab] = useState('models')
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState('')
  const [temperature, setTemperature] = useState(0.7)
  const [currentUser, setCurrentUser] = useState(null)
  const [users, setUsers] = useState([])
  const [problems, setProblems] = useState([])
  const [problemProposals, setProblemProposals] = useState([])
  const [testCaseProposals, setTestCaseProposals] = useState([])
  const [solutionProposals, setSolutionProposals] = useState([])
  const [statistics, setStatistics] = useState(null)
  const [loading, setLoading] = useState(false)
  const [selectedProposal, setSelectedProposal] = useState(null)
  const [selectedProblemProposal, setSelectedProblemProposal] = useState(null)
  const [selectedSolution, setSelectedSolution] = useState(null)
  const [testCode, setTestCode] = useState('# 여기에 테스트 코드를 작성하세요\n\n')
  const [testOutput, setTestOutput] = useState('')
  const [testLoading, setTestLoading] = useState(false)
  const [reviewComment, setReviewComment] = useState('')

  // AI 설정 관련 상태
  const [aiMode, setAiMode] = useState('api')
  const [apiKey, setApiKey] = useState('')
  const [modelName, setModelName] = useState('Qwen/Qwen2.5-Coder-7B-Instruct')
  const [isModelLoaded, setIsModelLoaded] = useState(false)
  const [aiConfigLoading, setAiConfigLoading] = useState(false)

  useEffect(() => {
    fetchCurrentUser()
    fetchModels()
    fetchUsers()
    fetchProblems()
    fetchStatistics()
    fetchProblemProposals()
    fetchTestCaseProposals()
    fetchSolutionProposals()
    fetchAIConfig()
  }, [])

  const fetchCurrentUser = async () => {
    try {
      const response = await api.get('/admin/current-user/')
      if (response.data.success) {
        setCurrentUser(response.data.data)
      }
    } catch (error) {
      console.error('Failed to fetch current user:', error)
    }
  }

  const fetchModels = async () => {
    try {
      const response = await api.get('/admin/models/')
      setModels(response.data.data || [
        { id: 'gpt-4', name: 'GPT-4', provider: 'OpenAI' },
        { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'OpenAI' },
        { id: 'claude-3', name: 'Claude 3', provider: 'Anthropic' }
      ])

      // 현재 설정된 모델 가져오기
      const configResponse = await api.get('/admin/config/')
      setSelectedModel(configResponse.data.data?.model || 'gpt-3.5-turbo')
      setTemperature(configResponse.data.data?.temperature || 0.7)
    } catch (error) {
      console.error('Failed to fetch models:', error)
      // 기본값 설정
      setModels([
        { id: 'gpt-4', name: 'GPT-4', provider: 'OpenAI' },
        { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'OpenAI' },
        { id: 'claude-3', name: 'Claude 3', provider: 'Anthropic' }
      ])
      setSelectedModel('gpt-3.5-turbo')
    }
  }

  const fetchUsers = async () => {
    try {
      const response = await api.get('/admin/users/')
      setUsers(response.data.data || [])
    } catch (error) {
      console.error('Failed to fetch users:', error)
    }
  }

  const fetchProblems = async () => {
    try {
      const response = await api.get('/admin/problems/')
      setProblems(response.data.data || [])
    } catch (error) {
      console.error('Failed to fetch problems:', error)
    }
  }

  const fetchStatistics = async () => {
    try {
      const response = await api.get('/admin/statistics/')
      setStatistics(response.data.data || {
        total_users: 0,
        total_problems: 0
      })
    } catch (error) {
      console.error('Failed to fetch statistics:', error)
      setStatistics({
        total_users: 0,
        total_problems: 0
      })
    }
  }

  const fetchProblemProposals = async () => {
    try {
      const response = await api.get('/coding-test/problems/proposals/')
      setProblemProposals(response.data.data || [])
    } catch (error) {
      console.error('Failed to fetch problem proposals:', error)
    }
  }

  const fetchTestCaseProposals = async () => {
    try {
      const response = await api.get('/coding-test/test-cases/')
      setTestCaseProposals(response.data.data || [])
    } catch (error) {
      console.error('Failed to fetch test case proposals:', error)
    }
  }

  const fetchSolutionProposals = async () => {
    try {
      const response = await api.get('/coding-test/solutions/')
      setSolutionProposals(response.data.data || [])
    } catch (error) {
      console.error('Failed to fetch solution proposals:', error)
    }
  }

  const fetchAIConfig = async () => {
    try {
      const response = await api.get('/coding-test/ai-config/')
      if (response.data.success) {
        const config = response.data.data
        setAiMode(config.mode)
        setApiKey(config.api_key || '')
        setModelName(config.model_name)
        setIsModelLoaded(config.is_model_loaded)
      }
    } catch (error) {
      console.error('Failed to fetch AI config:', error)
    }
  }

  const handleUpdateAIConfig = async () => {
    setAiConfigLoading(true)
    try {
      const response = await api.post('/coding-test/ai-config/update/', {
        mode: aiMode,
        api_key: apiKey,
        model_name: modelName
      })

      if (response.data.success) {
        alert('AI 모델 설정이 업데이트되었습니다.')
        fetchAIConfig()
      } else {
        alert('설정 업데이트에 실패했습니다: ' + response.data.message)
      }
    } catch (error) {
      console.error('Failed to update AI config:', error)
      alert('설정 업데이트에 실패했습니다.')
    } finally {
      setAiConfigLoading(false)
    }
  }

  const handleLoadModel = async () => {
    setAiConfigLoading(true)
    try {
      const response = await api.post('/coding-test/ai-config/load-model/')

      if (response.data.success) {
        alert('모델 로드가 시작되었습니다. 완료까지 시간이 걸릴 수 있습니다.')
        fetchAIConfig()
      } else {
        alert('모델 로드에 실패했습니다: ' + response.data.message)
      }
    } catch (error) {
      console.error('Failed to load model:', error)
      alert('모델 로드에 실패했습니다.')
    } finally {
      setAiConfigLoading(false)
    }
  }

  const handleUnloadModel = async () => {
    setAiConfigLoading(true)
    try {
      const response = await api.post('/coding-test/ai-config/unload-model/')

      if (response.data.success) {
        alert('모델이 언로드되었습니다.')
        fetchAIConfig()
      } else {
        alert('모델 언로드에 실패했습니다: ' + response.data.message)
      }
    } catch (error) {
      console.error('Failed to unload model:', error)
      alert('모델 언로드에 실패했습니다.')
    } finally {
      setAiConfigLoading(false)
    }
  }

  const handleSaveConfig = async () => {
    setLoading(true)
    try {
      await api.post('/admin/config/', {
        model: selectedModel,
        temperature: temperature
      })
      alert('설정이 저장되었습니다.')
    } catch (error) {
      console.error('Failed to save config:', error)
      alert('설정 저장에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('정말로 이 사용자를 삭제하시겠습니까?')) {
      return
    }

    try {
      await api.delete(`/auth/users/${userId}/delete/`)
      fetchUsers()
      fetchStatistics() // 통계도 갱신
      alert('사용자가 삭제되었습니다.')
    } catch (error) {
      console.error('Failed to delete user:', error)
      alert(error.response?.data?.message || '사용자 삭제에 실패했습니다.')
    }
  }

  const handleToggleUserStatus = async (userId, currentStatus) => {
    try {
      await api.patch(`/admin/users/${userId}/`, {
        is_active: !currentStatus
      })
      fetchUsers()
    } catch (error) {
      console.error('Failed to toggle user status:', error)
      alert('사용자 상태 변경에 실패했습니다.')
    }
  }

  const handleToggleUserRole = async (userId, currentIsStaff) => {
    if (!window.confirm(`정말로 이 사용자의 권한을 ${currentIsStaff ? '일반 사용자로' : '관리자로'} 변경하시겠습니까?`)) {
      return
    }

    try {
      await api.patch(`/admin/users/${userId}/`, {
        is_staff: !currentIsStaff
      })
      fetchUsers()
      alert('권한이 변경되었습니다.')
    } catch (error) {
      console.error('Failed to toggle user role:', error)
      if (error.response?.data?.message) {
        alert(error.response.data.message)
      } else {
        alert('권한 변경에 실패했습니다.')
      }
    }
  }

  const handleSelectProposal = async (proposal) => {
    setSelectedProposal(proposal)
    setReviewComment('')
    setTestOutput('')

    // Load problem solution_code for testing
    try {
      const response = await api.get(`/coding-test/problems/${proposal.problem_id}/`)
      const problem = response.data

      // Try to get solution_code from various possible sources
      if (problem.solution_code) {
        setTestCode(problem.solution_code)
      } else if (problem.solutions && problem.solutions.length > 0) {
        // Use the first solution's solution_code
        const firstSolution = problem.solutions[0]
        if (firstSolution && firstSolution.solution_code) {
          setTestCode(firstSolution.solution_code)
        }
      } else if (problem.template) {
        // Fallback to template if solution_code is not available
        setTestCode(problem.template)
      } else {
        setTestCode('# 솔루션 코드를 불러올 수 없습니다.\n# 테스트 코드를 직접 작성해주세요.')
      }
    } catch (error) {
      console.error('Failed to load problem code:', error)
      setTestCode('# 솔루션 코드를 불러오는 중 오류가 발생했습니다.\n# 테스트 코드를 직접 작성해주세요.')
    }
  }

  const handleTestProposal = async () => {
    if (!selectedProposal) return

    setTestLoading(true)
    setTestOutput('코드 실행 중...\n')

    try {
      const response = await api.post('/coding-test/execute/', {
        problem_id: selectedProposal.problem_id,
        code: testCode,
        language: 'python',
        custom_inputs: [selectedProposal.input_data]
      })

      if (response.data.success) {
        const results = response.data.data.results
        let output = '=== 테스트 실행 결과 ===\n\n'

        // 모든 테스트 케이스 결과 표시
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
            const expectedOutput = isProposedTest ? selectedProposal.expected_output : (result.expected_output || '')
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

  const handleApproveProposal = async () => {
    if (!selectedProposal) return

    if (!window.confirm('이 테스트 케이스를 승인하시겠습니까?')) {
      return
    }

    try {
      await api.post(`/coding-test/test-cases/${selectedProposal.id}/approve/`, {
        review_comment: reviewComment
      })
      alert('테스트 케이스가 승인되었습니다.')
      setSelectedProposal(null)
      fetchTestCaseProposals()
    } catch (error) {
      console.error('Failed to approve proposal:', error)
      alert('승인에 실패했습니다.')
    }
  }

  const handleRejectProposal = async () => {
    if (!selectedProposal) return

    if (!reviewComment.trim()) {
      alert('거부 사유를 입력해주세요.')
      return
    }

    if (!window.confirm('이 테스트 케이스를 거부하시겠습니까?')) {
      return
    }

    try {
      await api.post(`/coding-test/test-cases/${selectedProposal.id}/reject/`, {
        review_comment: reviewComment
      })
      alert('테스트 케이스가 거부되었습니다.')
      setSelectedProposal(null)
      fetchTestCaseProposals()
    } catch (error) {
      console.error('Failed to reject proposal:', error)
      alert('거부에 실패했습니다.')
    }
  }

  const handleSelectProblemProposal = async (proposal) => {
    setSelectedProblemProposal(proposal)
    setReviewComment('')
    setTestOutput('')
    setTestCode(proposal.solution_code || '# 솔루션 코드가 없습니다.')
  }

  const handleTestProblemProposal = async () => {
    if (!selectedProblemProposal) return

    setTestLoading(true)
    setTestOutput('코드 실행 중...\n')

    try {
      const response = await api.post('/coding-test/execute/', {
        problem_id: selectedProblemProposal.problem_id,
        code: testCode,
        language: selectedProblemProposal.language || 'python',
        custom_inputs: selectedProblemProposal.test_cases?.map(tc => tc.input) || []
      })

      if (response.data.success) {
        const results = response.data.data.results
        let output = '=== 문제 제안 테스트 결과 ===\n\n'

        results.forEach((result, idx) => {
          const testCase = selectedProblemProposal.test_cases?.[idx]
          output += `[테스트 ${idx + 1}]\n`
          output += `입력: ${result.input || '(없음)'}\n`

          if (result.error) {
            output += `에러: ${result.error}\n\n`
          } else {
            output += `실제 출력: ${result.output || '(출력 없음)'}\n`
            output += `예상 출력: ${testCase?.output || '(없음)'}\n`
            const actualOutput = result.output?.trim() || ''
            const expectedOutput = testCase?.output?.trim() || ''
            const isMatch = actualOutput === expectedOutput
            output += `결과: ${isMatch ? '✅ 통과' : '❌ 실패'}\n\n`
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

  const handleApproveProblemProposal = async () => {
    if (!selectedProblemProposal) return

    if (!window.confirm('이 문제 제안을 승인하시겠습니까?')) {
      return
    }

    try {
      await api.post(`/coding-test/problems/proposals/${selectedProblemProposal.id}/approve/`, {
        review_comment: reviewComment
      })
      alert('문제 제안이 승인되었습니다.')
      setSelectedProblemProposal(null)
      fetchProblemProposals()
    } catch (error) {
      console.error('Failed to approve problem proposal:', error)
      alert('승인에 실패했습니다.')
    }
  }

  const handleRejectProblemProposal = async () => {
    if (!selectedProblemProposal) return

    if (!reviewComment.trim()) {
      alert('거부 사유를 입력해주세요.')
      return
    }

    if (!window.confirm('이 문제 제안을 거부하시겠습니까?')) {
      return
    }

    try {
      await api.post(`/coding-test/problems/proposals/${selectedProblemProposal.id}/reject/`, {
        review_comment: reviewComment
      })
      alert('문제 제안이 거부되었습니다.')
      setSelectedProblemProposal(null)
      fetchProblemProposals()
    } catch (error) {
      console.error('Failed to reject problem proposal:', error)
      alert('거부에 실패했습니다.')
    }
  }

  const handleSelectSolution = async (solution) => {
    setSelectedSolution(solution)
    setReviewComment('')
    setTestOutput('')
    setTestCode(solution.solution_code)
  }

  const handleTestSolution = async () => {
    if (!selectedSolution) return

    setTestLoading(true)
    setTestOutput('코드 실행 중...\n')

    try {
      const response = await api.post('/coding-test/execute/', {
        problem_id: selectedSolution.problem_id,
        code: testCode,
        language: selectedSolution.language || 'python',
      })

      if (response.data.success) {
        const results = response.data.data.results
        let output = '=== 솔루션 실행 결과 ===\n\n'

        results.forEach((result, idx) => {
          output += `[테스트 ${idx + 1}]\n`
          output += `[입력]\n${result.input || '(없음)'}\n\n`
          if (result.error) {
            output += `[에러]\n${result.error}\n\n`
          } else {
            output += `[출력]\n${result.output || '(출력 없음)'}\n\n`
            output += `[예상 출력]\n${result.expected_output || '(없음)'}\n\n`
            const actualOutput = result.output?.trim() || ''
            const expectedOutput = result.expected_output?.trim() || ''
            output += `[결과] ${actualOutput === expectedOutput ? '✅ 통과' : '❌ 실패'}\n\n`
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

  const handleApproveSolution = async () => {
    if (!selectedSolution) return

    if (!window.confirm('이 솔루션을 승인하시겠습니까?')) {
      return
    }

    try {
      await api.post(`/coding-test/solutions/${selectedSolution.id}/approve/`, {
        review_comment: reviewComment
      })
      alert('솔루션이 승인되었습니다.')
      setSelectedSolution(null)
      fetchSolutionProposals()
    } catch (error) {
      console.error('Failed to approve solution:', error)
      alert('승인에 실패했습니다.')
    }
  }

  const handleRejectSolution = async () => {
    if (!selectedSolution) return

    if (!reviewComment.trim()) {
      alert('거부 사유를 입력해주세요.')
      return
    }

    if (!window.confirm('이 솔루션을 거부하시겠습니까?')) {
      return
    }

    try {
      await api.post(`/coding-test/solutions/${selectedSolution.id}/reject/`, {
        review_comment: reviewComment
      })
      alert('솔루션이 거부되었습니다.')
      setSelectedSolution(null)
      fetchSolutionProposals()
    } catch (error) {
      console.error('Failed to reject solution:', error)
      alert('거부에 실패했습니다.')
    }
  }

  return (
    <div className="admin-panel">
      <div className="admin-header">
        <h1>관리자 패널</h1>
      </div>

      <div className="admin-layout">
        {/* 왼쪽 사이드바 - 통계 */}
        <div className="admin-sidebar">
          {statistics && (
            <>
              <div className="stat-box-sidebar">
                <div className="stat-label-sidebar">총 사용자</div>
                <div className="stat-value-sidebar">{statistics.total_users || 0}</div>
              </div>
              <div className="stat-box-sidebar">
                <div className="stat-label-sidebar">총 문제</div>
                <div className="stat-value-sidebar">{statistics.total_problems || 0}</div>
              </div>
            </>
          )}
        </div>

        {/* 오른쪽 메인 영역 */}
        <div className="admin-main">
          <div className="admin-tabs">
            <button
              className={activeTab === 'models' ? 'active' : ''}
              onClick={() => setActiveTab('models')}
            >
              모델 설정
            </button>
            <button
              className={activeTab === 'users' ? 'active' : ''}
              onClick={() => setActiveTab('users')}
            >
              사용자 관리
            </button>
            <button
              className={activeTab === 'problems' ? 'active' : ''}
              onClick={() => setActiveTab('problems')}
            >
              문제 승인
              {problemProposals.filter(p => p.status === 'pending').length > 0 && (
                <span className="notification-badge">
                  {problemProposals.filter(p => p.status === 'pending').length}
                </span>
              )}
            </button>
            <button
              className={activeTab === 'testcases' ? 'active' : ''}
              onClick={() => setActiveTab('testcases')}
            >
              테스트 케이스 승인
              {testCaseProposals.filter(p => p.status === 'pending').length > 0 && (
                <span className="notification-badge">
                  {testCaseProposals.filter(p => p.status === 'pending').length}
                </span>
              )}
            </button>
            <button
              className={activeTab === 'solutions' ? 'active' : ''}
              onClick={() => setActiveTab('solutions')}
            >
              솔루션 승인
              {solutionProposals.filter(p => p.status === 'pending').length > 0 && (
                <span className="notification-badge">
                  {solutionProposals.filter(p => p.status === 'pending').length}
                </span>
              )}
            </button>
          </div>

          <div className="admin-content">
        {activeTab === 'models' && (
          <ModelsTab
            aiMode={aiMode}
            setAiMode={setAiMode}
            apiKey={apiKey}
            setApiKey={setApiKey}
            modelName={modelName}
            setModelName={setModelName}
            isModelLoaded={isModelLoaded}
            aiConfigLoading={aiConfigLoading}
            handleUpdateAIConfig={handleUpdateAIConfig}
            handleLoadModel={handleLoadModel}
            handleUnloadModel={handleUnloadModel}
          />
        )}

        {activeTab === 'users' && (
          <UsersTab
            users={users}
            currentUserId={currentUser?.id}
            handleToggleUserStatus={handleToggleUserStatus}
            handleToggleUserRole={handleToggleUserRole}
            handleDeleteUser={handleDeleteUser}
          />
        )}

        {activeTab === 'problems' && (
          <ProblemsTab
            problemProposals={problemProposals}
            selectedProposal={selectedProblemProposal}
            setSelectedProposal={setSelectedProblemProposal}
            handleSelectProposal={handleSelectProblemProposal}
            testCode={testCode}
            setTestCode={setTestCode}
            testOutput={testOutput}
            testLoading={testLoading}
            handleTestProposal={handleTestProblemProposal}
            reviewComment={reviewComment}
            setReviewComment={setReviewComment}
            handleApproveProposal={handleApproveProblemProposal}
            handleRejectProposal={handleRejectProblemProposal}
          />
        )}

        {activeTab === 'testcases' && (
          <TestCasesTab
            testCaseProposals={testCaseProposals}
            selectedProposal={selectedProposal}
            setSelectedProposal={setSelectedProposal}
            handleSelectProposal={handleSelectProposal}
            testCode={testCode}
            setTestCode={setTestCode}
            testOutput={testOutput}
            testLoading={testLoading}
            handleTestProposal={handleTestProposal}
            reviewComment={reviewComment}
            setReviewComment={setReviewComment}
            handleApproveProposal={handleApproveProposal}
            handleRejectProposal={handleRejectProposal}
          />
        )}

        {activeTab === 'solutions' && (
          <SolutionsTab
            solutionProposals={solutionProposals}
            selectedSolution={selectedSolution}
            setSelectedSolution={setSelectedSolution}
            handleSelectSolution={handleSelectSolution}
            testCode={testCode}
            setTestCode={setTestCode}
            testOutput={testOutput}
            testLoading={testLoading}
            handleTestSolution={handleTestSolution}
            reviewComment={reviewComment}
            setReviewComment={setReviewComment}
            handleApproveSolution={handleApproveSolution}
            handleRejectSolution={handleRejectSolution}
          />
        )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default AdminPanel
