import React, { useState, useEffect } from 'react'
import api from '../../../../services/api'
import './MetricsValidationTab.css'

export default function MetricsValidationTab() {
  // localStorage 키
  const STORAGE_KEY = 'metrics_validation_sessions'
  const STORAGE_ACTIVE_ID = 'metrics_validation_active_session'
  const STORAGE_NEXT_ID = 'metrics_validation_next_session_id'

  // localStorage에서 세션 불러오기
  const loadSessionsFromStorage = () => {
    try {
      const savedSessions = localStorage.getItem(STORAGE_KEY)
      const savedActiveId = localStorage.getItem(STORAGE_ACTIVE_ID)
      const savedNextId = localStorage.getItem(STORAGE_NEXT_ID)

      if (savedSessions) {
        return {
          sessions: JSON.parse(savedSessions),
          activeSessionId: savedActiveId ? parseInt(savedActiveId) : 1,
          nextSessionId: savedNextId ? parseInt(savedNextId) : 2
        }
      }
    } catch (error) {
      console.error('Failed to load sessions from localStorage:', error)
    }
    return null
  }

  // 문제 목록
  const [problems, setProblems] = useState([])
  const [loadingProblems, setLoadingProblems] = useState(true)

  // 여러 문제 세션 관리 (localStorage에서 복원 시도)
  const initialData = loadSessionsFromStorage() || {
    sessions: [
      {
        id: 1,
        code: '',
        problemId: '',
        problemTitle: '',
        preset: '초급',
        starCount: 0,  // 시뮬레이션용 별점 (0-3) → hint_purpose 자동 결정
        customComponents: {
          summary: true,  // 항상 포함
          libraries: true,
          code_example: true,
          step_by_step: false,
          complexity_hint: false,
          edge_cases: false,
          improvements: false
        },
        userMetrics: {
          // 정적 지표 (6개)
          syntax_errors: 0,
          test_pass_rate: 0,
          code_complexity: 0,
          code_quality_score: 0,
          algorithm_pattern_match: 0,
          pep8_violations: 0,
          // LLM 지표 (6개)
          algorithm_efficiency: 0,
          code_readability: 0,
          design_pattern_fit: 0,
          edge_case_handling: 0,
          code_conciseness: 0,
          function_separation: 0
        },
        history: [],
        // COH (Chain of Hint) 관련 상태
        cohStatus: null,
        blockedComponents: []
      }
    ],
    activeSessionId: 1,
    nextSessionId: 2
  }

  const [sessions, setSessions] = useState(initialData.sessions)
  const [activeSessionId, setActiveSessionId] = useState(initialData.activeSessionId)
  const [nextSessionId, setNextSessionId] = useState(initialData.nextSessionId)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // LLM-as-Judge 평가 상태
  const [evaluating, setEvaluating] = useState(false)
  const [evaluationResult, setEvaluationResult] = useState(null)
  const [evaluationError, setEvaluationError] = useState('')

  // 휴먼 평가 상태
  const [humanScores, setHumanScores] = useState({
    hint_relevance: 0,
    educational_value: 0,
    difficulty_appropriateness: 0,
    code_accuracy: 0,
    completeness: 0
  })
  const [humanComment, setHumanComment] = useState('')
  const [savingEvaluation, setSavingEvaluation] = useState(false)
  const [saveMessage, setSaveMessage] = useState('')

  // 평가 이력 상태
  const [showEvaluationHistory, setShowEvaluationHistory] = useState(false)
  const [evaluationHistory, setEvaluationHistory] = useState([])
  const [evaluationStats, setEvaluationStats] = useState(null)
  const [loadingHistory, setLoadingHistory] = useState(false)

  // COH 전체 단계 생성 상태
  const [cohAllSteps, setCohAllSteps] = useState([])  // [{depth: 0, hint: ..., coh_status: ...}, ...]
  const [generatingCoh, setGeneratingCoh] = useState(false)
  const [cohProgress, setCohProgress] = useState('')  // "1/3", "2/3", "3/3"

  const activeSession = sessions.find(s => s.id === activeSessionId)

  // 세션 데이터가 변경될 때마다 localStorage에 저장
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
      localStorage.setItem(STORAGE_ACTIVE_ID, activeSessionId.toString())
      localStorage.setItem(STORAGE_NEXT_ID, nextSessionId.toString())
    } catch (error) {
      console.error('Failed to save sessions to localStorage:', error)
    }
  }, [sessions, activeSessionId, nextSessionId])

  // 문제 목록 불러오기
  useEffect(() => {
    const fetchProblems = async () => {
      try {
        const response = await api.get('/coding-test/problems/')
        if (response.data.success) {
          setProblems(response.data.data)
        }
      } catch (err) {
        console.error('Failed to fetch problems:', err)
      } finally {
        setLoadingProblems(false)
      }
    }
    fetchProblems()
  }, [])

  // 문제 선택 핸들러
  const handleProblemSelect = (e) => {
    const selectedProblemId = e.target.value
    const selectedProblem = problems.find(p => p.problem_id === selectedProblemId)

    updateSession({
      problemId: selectedProblemId,
      problemTitle: selectedProblem ? selectedProblem.title : ''
    })
  }

  // 프리셋 변경 (요약 설명 방식만 변경, 차단 구성요소 설정)
  const handlePresetChange = (preset) => {
    // 프리셋별 차단 구성요소 및 기본 선택값 설정
    let blockedComponents = []
    let defaultComponents = {
      summary: true,
      libraries: true,
      code_example: true,
      step_by_step: false,
      complexity_hint: false,
      edge_cases: false,
      improvements: false
    }

    if (preset === '초급') {
      // 초급 (레벨 4): 모든 구성요소 허용
      blockedComponents = []
      defaultComponents = {
        summary: true,
        libraries: true,
        code_example: true,
        step_by_step: false,
        complexity_hint: false,
        edge_cases: false,
        improvements: false
      }
    } else if (preset === '중급') {
      // 중급 (레벨 7): code_example, step_by_step 차단 (libraries는 허용)
      blockedComponents = ['code_example', 'step_by_step']
      defaultComponents = {
        summary: true,
        libraries: true,
        code_example: false,
        step_by_step: false,
        complexity_hint: true,
        edge_cases: false,
        improvements: false
      }
    } else if (preset === '고급') {
      // 고급 (레벨 9): libraries, code_example, step_by_step 차단
      blockedComponents = ['libraries', 'code_example', 'step_by_step']
      defaultComponents = {
        summary: true,
        libraries: false,
        code_example: false,
        step_by_step: false,
        complexity_hint: true,
        edge_cases: true,
        improvements: true
      }
    }

    updateSession({
      preset,
      customComponents: defaultComponents,
      cohStatus: null,  // 프리셋 변경 시 COH 상태 리셋
      blockedComponents
    })
  }

  // 커스텀 구성 변경 (프리셋은 유지)
  const handleComponentToggle = (component) => {
    updateSession({
      customComponents: {
        ...activeSession.customComponents,
        [component]: !activeSession.customComponents[component]
      }
    })
  }

  // 사용자 지표 변경
  const handleUserMetricChange = (metricKey, value) => {
    updateSession({
      userMetrics: {
        ...activeSession.userMetrics,
        [metricKey]: parseFloat(value) || 0
      }
    })
  }

  // 세션 추가
  const handleAddSession = () => {
    const newSession = {
      id: nextSessionId,
      code: '',
      problemId: '',
      problemTitle: '',
      preset: '초급',
      starCount: 0,  // 시뮬레이션용 별점 (0-3) → hint_purpose 자동 결정
      customComponents: {
        summary: true,  // 항상 포함
        libraries: true,
        code_example: true,
        step_by_step: false,
        complexity_hint: false,
        edge_cases: false,
        improvements: false
      },
      userMetrics: {
        // 정적 지표 (6개)
        syntax_errors: 0,
        test_pass_rate: 0,
        code_complexity: 0,
        code_quality_score: 0,
        algorithm_pattern_match: 0,
        pep8_violations: 0,
        // LLM 지표 (6개)
        algorithm_efficiency: 0,
        code_readability: 0,
        design_pattern_fit: 0,
        edge_case_handling: 0,
        code_conciseness: 0,
        function_separation: 0
      },
      history: [],
      // COH (Chain of Hint) 관련 상태
      cohStatus: null,
      blockedComponents: []
    }
    setSessions([...sessions, newSession])
    setActiveSessionId(nextSessionId)
    setNextSessionId(nextSessionId + 1)
  }

  // 세션 삭제
  const handleDeleteSession = (sessionId) => {
    if (sessions.length === 1) {
      alert('최소 1개의 세션은 유지해야 합니다.')
      return
    }

    const newSessions = sessions.filter(s => s.id !== sessionId)
    setSessions(newSessions)

    if (activeSessionId === sessionId) {
      setActiveSessionId(newSessions[0].id)
    }
  }

  // 세션 데이터 업데이트
  const updateSession = (updates) => {
    setSessions(sessions.map(s =>
      s.id === activeSessionId ? { ...s, ...updates } : s
    ))
  }

  // 검증 실행
  const handleValidate = async () => {
    if (!activeSession.code.trim()) {
      setError('코드를 입력해주세요.')
      return
    }

    if (!activeSession.problemId) {
      setError('문제를 선택해주세요.')
      return
    }

    setLoading(true)
    setError('')

    try {
      // 이전 힌트 이력 생성 (Chain of Hints)
      const previousHints = activeSession.history.map((item, index) => ({
        hint_text: item.hint,
        level: item.preset,
        timestamp: item.timestamp
      }))

      // star_count에서 hint_purpose 자동 계산
      // 0: completion, 1-2: optimization, 3: optimal
      const starCount = activeSession.starCount || 0
      const autoHintPurpose = starCount === 0 ? 'completion'
        : starCount < 3 ? 'optimization'
        : 'optimal'

      const payload = {
        code: activeSession.code,
        problem_id: activeSession.problemId,
        preset: activeSession.preset,
        star_count: starCount,  // 시뮬레이션용 별점 (0-3)
        hint_purpose: autoHintPurpose,  // star_count에서 자동 계산
        custom_components: activeSession.customComponents,
        previous_hints: previousHints,
        user_metrics: activeSession.userMetrics  // 사용자 평균 지표 (힌트 생성 시 10% 반영)
      }

      const response = await api.post('/coding-test/admin/validate-metrics/', payload)

      if (response.data.success) {
        const result = response.data.data

        // COH 상태 업데이트
        const newCohStatus = result.coh_status || null
        const newBlockedComponents = result.blocked_components || []

        // 히스토리에 추가 (COH 정보 포함)
        const newHistoryItem = {
          static_metrics: result.static_metrics,
          llm_metrics: result.llm_metrics,
          hint: result.hint,
          hint_purpose: result.hint_purpose,  // 'completion', 'optimization', 'optimal'
          hint_branch: result.hint_branch || '',  // 'A', 'B', 'C', 'D', 'E1', 'E2', 'F'
          current_star_count: result.current_star_count || 0,
          is_logic_complete: result.is_logic_complete || false,
          purpose_context: result.purpose_context || '',
          weak_metrics: result.weak_metrics || null,  // optimization인 경우만
          hint_components: result.hint_components || null,
          selected_components: result.selected_components || [],
          unselected_components: result.unselected_components || [],
          totalScore: result.total_score,
          preset: result.preset || activeSession.preset,
          timestamp: new Date().toLocaleString('ko-KR'),
          // COH 관련 정보
          coh_status: newCohStatus,
          hint_level: result.hint_level || null,
          coh_depth: result.coh_depth || 0,
          blocked_components: newBlockedComponents
        }

        updateSession({
          history: [...activeSession.history, newHistoryItem],
          cohStatus: newCohStatus,
          blockedComponents: newBlockedComponents
        })
      } else {
        setError(response.data.error || '검증 실패')
      }
    } catch (err) {
      console.error('Validation error:', err)
      setError(err.response?.data?.error || '검증 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  // 세션 초기화
  const handleClearSession = () => {
    updateSession({
      code: '',
      history: []
    })
    setError('')
    setEvaluationResult(null)
    setEvaluationError('')
    setCohAllSteps([])  // COH 단계도 초기화
    setCohProgress('')
  }

  // COH 전체 9단계 생성 (고급 기본 → 고급 COH1 → 중급 기본 → ... → 초급 COH3)
  // 각 프리셋별 단계: 고급(2) + 중급(3) + 초급(4) = 총 9단계
  const handleGenerateAllCohSteps = async () => {
    if (!activeSession.code.trim()) {
      setError('코드를 입력해주세요.')
      return
    }

    if (!activeSession.problemId) {
      setError('문제를 선택해주세요.')
      return
    }

    setGeneratingCoh(true)
    setError('')
    setCohAllSteps([])

    const steps = []

    // star_count에서 hint_purpose 자동 계산
    const starCount = activeSession.starCount || 0
    const autoHintPurpose = starCount === 0 ? 'completion'
      : starCount < 3 ? 'optimization'
      : 'optimal'

    // 각 프리셋별 COH 단계 정의
    // 현재 선택된 프리셋의 단계만 실행
    const allStepsConfig = {
      '고급': [
        // 고급: 레벨 9 → 8 (2단계)
        { preset: '고급', expectedLevel: 9, cohDepth: 0, stepName: '고급 기본' },
        { preset: '고급', expectedLevel: 8, cohDepth: 1, stepName: '고급 COH1' }
      ],
      '중급': [
        // 중급: 레벨 7 → 6 → 5 (3단계)
        { preset: '중급', expectedLevel: 7, cohDepth: 0, stepName: '중급 기본' },
        { preset: '중급', expectedLevel: 6, cohDepth: 1, stepName: '중급 COH1' },
        { preset: '중급', expectedLevel: 5, cohDepth: 2, stepName: '중급 COH2' }
      ],
      '초급': [
        // 초급: 레벨 4 → 3 → 2 → 1 (4단계)
        { preset: '초급', expectedLevel: 4, cohDepth: 0, stepName: '초급 기본' },
        { preset: '초급', expectedLevel: 3, cohDepth: 1, stepName: '초급 COH1' },
        { preset: '초급', expectedLevel: 2, cohDepth: 2, stepName: '초급 COH2' },
        { preset: '초급', expectedLevel: 1, cohDepth: 3, stepName: '초급 COH3' }
      ]
    }

    // 선택된 프리셋의 단계만 가져오기
    const selectedPreset = activeSession.preset || '초급'
    const allSteps = allStepsConfig[selectedPreset] || allStepsConfig['초급']
    const totalSteps = allSteps.length

    try {
      // 각 프리셋별로 이전 힌트 리셋 (프리셋 변경 시 COH 리셋)
      let currentPreset = null
      let previousHints = []

      for (let i = 0; i < totalSteps; i++) {
        const stepConfig = allSteps[i]
        setCohProgress(`${i + 1}/${totalSteps} 단계 생성 중... (${stepConfig.stepName})`)

        // 프리셋이 변경되면 이전 힌트 리셋 (COH가 0부터 다시 시작)
        if (currentPreset !== stepConfig.preset) {
          currentPreset = stepConfig.preset
          previousHints = []
        }

        const payload = {
          code: activeSession.code,
          problem_id: activeSession.problemId,
          preset: stepConfig.preset,
          star_count: starCount,
          hint_purpose: autoHintPurpose,
          custom_components: activeSession.customComponents,
          previous_hints: previousHints,
          user_metrics: activeSession.userMetrics
        }

        const response = await api.post('/coding-test/admin/validate-metrics/', payload)

        if (response.data.success) {
          const result = response.data.data

          const stepData = {
            stepIndex: i + 1,
            stepName: stepConfig.stepName,
            preset: stepConfig.preset,
            expectedLevel: stepConfig.expectedLevel,
            actualLevel: result.hint_level || stepConfig.expectedLevel,
            hint: result.hint,
            coh_status: result.coh_status || null,
            coh_depth: result.coh_depth || stepConfig.cohDepth,
            blocked_components: result.blocked_components || [],
            hint_purpose: result.hint_purpose,
            static_metrics: result.static_metrics,
            llm_metrics: result.llm_metrics,
            total_score: result.total_score,
            timestamp: new Date().toLocaleString('ko-KR')
          }

          steps.push(stepData)
          setCohAllSteps([...steps])

          // 다음 단계를 위해 previous_hints 업데이트 (같은 프리셋 내에서만)
          previousHints = [...previousHints, {
            hint_text: result.hint,
            level: stepConfig.preset,
            timestamp: stepData.timestamp
          }]
        } else {
          setError(`${stepConfig.stepName} 생성 실패: ${response.data.error || '알 수 없는 오류'}`)
          break
        }
      }

      setCohProgress(`완료! (${selectedPreset} ${totalSteps}단계 모두 생성됨)`)
      setTimeout(() => setCohProgress(''), 3000)
    } catch (err) {
      console.error('COH generation error:', err)
      setError(err.response?.data?.error || 'COH 생성 중 오류가 발생했습니다.')
    } finally {
      setGeneratingCoh(false)
    }
  }

  // LLM-as-Judge 평가 실행
  const handleEvaluateHint = async () => {
    if (!latestResult || !latestResult.hint) {
      setEvaluationError('평가할 힌트가 없습니다.')
      return
    }

    setEvaluating(true)
    setEvaluationError('')
    setEvaluationResult(null)

    try {
      const selectedProblem = problems.find(p => p.problem_id === activeSession.problemId)

      const payload = {
        problem_id: activeSession.problemId,
        problem_title: selectedProblem?.title || '',
        problem_description: selectedProblem?.description || '',
        user_code: activeSession.code,
        generated_hint: latestResult.hint,
        hint_level: latestResult.preset,
        hint_purpose: latestResult.hint_purpose || 'completion'
      }

      const response = await api.post('/coding-test/admin/evaluate-hint/', payload)

      if (response.data.success) {
        setEvaluationResult(response.data.data)
      } else {
        setEvaluationError(response.data.error || '평가 실패')
      }
    } catch (err) {
      console.error('Evaluation error:', err)
      setEvaluationError(err.response?.data?.error || '평가 중 오류가 발생했습니다.')
    } finally {
      setEvaluating(false)
    }
  }

  // 평가 저장 (휴먼 or LLM)
  const handleSaveEvaluation = async (evaluationType) => {
    if (!latestResult || !latestResult.hint) {
      setSaveMessage('저장할 힌트가 없습니다.')
      return
    }

    const scores = evaluationType === 'llm' ? evaluationResult?.scores : humanScores
    if (!scores || Object.values(scores).every(v => v === 0)) {
      setSaveMessage('평가 점수를 입력해주세요.')
      return
    }

    setSavingEvaluation(true)
    setSaveMessage('')

    try {
      const selectedProblem = problems.find(p => p.problem_id === activeSession.problemId)

      const payload = {
        evaluation_type: evaluationType,
        problem_id: activeSession.problemId,
        problem_title: selectedProblem?.title || '',
        user_code: activeSession.code,
        hint_text: latestResult.hint,
        hint_level: latestResult.preset,
        hint_purpose: latestResult.hint_purpose || 'completion',
        scores: scores,
        feedback: evaluationType === 'llm' ? evaluationResult?.feedback : {},
        overall_comment: evaluationType === 'llm' ? evaluationResult?.overall_feedback : humanComment,
        model_used: evaluationType === 'llm' ? 'gpt-4o' : ''
      }

      const response = await api.post('/coding-test/admin/evaluations/save/', payload)

      if (response.data.success) {
        setSaveMessage(`${evaluationType === 'llm' ? 'LLM' : '휴먼'} 평가가 저장되었습니다! (평균: ${response.data.data.average_score.toFixed(2)}점)`)
        // 휴먼 평가 초기화
        if (evaluationType === 'human') {
          setHumanScores({
            hint_relevance: 0,
            educational_value: 0,
            difficulty_appropriateness: 0,
            code_accuracy: 0,
            completeness: 0
          })
          setHumanComment('')
        }
      } else {
        setSaveMessage(response.data.error || '저장 실패')
      }
    } catch (err) {
      console.error('Save evaluation error:', err)
      setSaveMessage(err.response?.data?.error || '저장 중 오류가 발생했습니다.')
    } finally {
      setSavingEvaluation(false)
    }
  }

  // 평가 이력 조회
  const handleLoadEvaluationHistory = async () => {
    setLoadingHistory(true)
    try {
      const response = await api.get('/coding-test/admin/evaluations/')

      if (response.data.success) {
        setEvaluationHistory(response.data.data)
        setEvaluationStats(response.data.stats)
        setShowEvaluationHistory(true)
      }
    } catch (err) {
      console.error('Load evaluation history error:', err)
    } finally {
      setLoadingHistory(false)
    }
  }

  const getScoreColor = (score) => {
    if (score >= 80) return '#4caf50'
    if (score >= 60) return '#ff9800'
    return '#f44336'
  }

  const getMetricColor = (value, max = 5) => {
    const percentage = (value / max) * 100
    if (percentage >= 80) return '#4caf50'
    if (percentage >= 60) return '#ff9800'
    return '#f44336'
  }

  // 최신 검증 결과 (맨 마지막 항목)
  const latestResult = activeSession.history.length > 0
    ? activeSession.history[activeSession.history.length - 1]
    : null

  return (
    <div className="metrics-validation-tab">
      <div className="validation-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2>📊 메트릭 & 힌트 검증</h2>
            <p>12개 지표 생성 검증 · 지표 기반 힌트 퀄리티 검증 · Chain of Hints 동작 검증</p>
          </div>
          <button
            onClick={handleLoadEvaluationHistory}
            disabled={loadingHistory}
            style={{
              padding: '10px 20px',
              backgroundColor: '#673ab7',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: loadingHistory ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 'bold'
            }}
          >
            {loadingHistory ? '로딩...' : '📋 평가 이력 보기'}
          </button>
        </div>
      </div>

      {/* 평가 이력 모달 */}
      {showEvaluationHistory && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: '#fff',
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '900px',
            width: '90%',
            maxHeight: '80vh',
            overflow: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ margin: 0 }}>📋 힌트 평가 이력</h3>
              <button
                onClick={() => setShowEvaluationHistory(false)}
                style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer' }}
              >
                ×
              </button>
            </div>

            {/* 통계 */}
            {evaluationStats && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px', marginBottom: '20px' }}>
                <div style={{ padding: '16px', backgroundColor: '#e3f2fd', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1976d2' }}>{evaluationStats.total_count}</div>
                  <div style={{ fontSize: '12px', color: '#666' }}>전체 평가</div>
                </div>
                <div style={{ padding: '16px', backgroundColor: '#e8f5e9', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#388e3c' }}>{evaluationStats.human_count}</div>
                  <div style={{ fontSize: '12px', color: '#666' }}>휴먼 평가</div>
                </div>
                <div style={{ padding: '16px', backgroundColor: '#fff3e0', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#f57c00' }}>{evaluationStats.llm_count}</div>
                  <div style={{ fontSize: '12px', color: '#666' }}>LLM 평가</div>
                </div>
                <div style={{ padding: '16px', backgroundColor: '#fce4ec', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#c2185b' }}>{evaluationStats.human_avg_score}</div>
                  <div style={{ fontSize: '12px', color: '#666' }}>휴먼 평균</div>
                </div>
                <div style={{ padding: '16px', backgroundColor: '#f3e5f5', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#7b1fa2' }}>{evaluationStats.llm_avg_score}</div>
                  <div style={{ fontSize: '12px', color: '#666' }}>LLM 평균</div>
                </div>
              </div>
            )}

            {/* 지표별 평균 */}
            {evaluationStats?.metric_averages && (
              <div style={{ marginBottom: '20px', padding: '16px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
                <h4 style={{ margin: '0 0 12px 0' }}>📊 지표별 평균 점수</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
                  {[
                    { key: 'hint_relevance', label: '관련성' },
                    { key: 'educational_value', label: '교육적 가치' },
                    { key: 'difficulty_appropriateness', label: '난이도' },
                    { key: 'code_accuracy', label: '코드 정확성' },
                    { key: 'completeness', label: '완전성' }
                  ].map(({ key, label }) => (
                    <div key={key} style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '18px', fontWeight: 'bold', color: evaluationStats.metric_averages[key] >= 4 ? '#4caf50' : evaluationStats.metric_averages[key] >= 3 ? '#ff9800' : '#f44336' }}>
                        {evaluationStats.metric_averages[key]}
                      </div>
                      <div style={{ fontSize: '11px', color: '#666' }}>{label}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 평가 목록 */}
            <div style={{ maxHeight: '400px', overflow: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ backgroundColor: '#f5f5f5' }}>
                    <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>유형</th>
                    <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>문제</th>
                    <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>레벨</th>
                    <th style={{ padding: '10px', textAlign: 'center', borderBottom: '1px solid #ddd' }}>평균</th>
                    <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>평가일</th>
                  </tr>
                </thead>
                <tbody>
                  {evaluationHistory.map(ev => (
                    <tr key={ev.id}>
                      <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '12px',
                          backgroundColor: ev.evaluation_type === 'human' ? '#e8f5e9' : '#fff3e0',
                          color: ev.evaluation_type === 'human' ? '#388e3c' : '#f57c00'
                        }}>
                          {ev.evaluation_type === 'human' ? '휴먼' : 'LLM'}
                        </span>
                      </td>
                      <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>{ev.problem_id}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>{ev.hint_level}</td>
                      <td style={{ padding: '10px', borderBottom: '1px solid #eee', textAlign: 'center' }}>
                        <span style={{
                          fontWeight: 'bold',
                          color: ev.average_score >= 4 ? '#4caf50' : ev.average_score >= 3 ? '#ff9800' : '#f44336'
                        }}>
                          {ev.average_score.toFixed(1)}
                        </span>
                      </td>
                      <td style={{ padding: '10px', borderBottom: '1px solid #eee', fontSize: '12px', color: '#666' }}>
                        {ev.created_at}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {evaluationHistory.length === 0 && (
                <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                  아직 저장된 평가가 없습니다.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 세션 탭 */}
      <div className="session-tabs">
        {sessions.map(session => (
          <div
            key={session.id}
            className={`session-tab ${activeSessionId === session.id ? 'active' : ''}`}
            onClick={() => setActiveSessionId(session.id)}
          >
            <span>{session.problemTitle || `세션 ${session.id}`}</span>
            {sessions.length > 1 && (
              <button
                className="session-delete-btn"
                onClick={(e) => {
                  e.stopPropagation()
                  handleDeleteSession(session.id)
                }}
              >
                ×
              </button>
            )}
          </div>
        ))}
        <button className="session-add-btn" onClick={handleAddSession}>
          + 새 세션
        </button>
      </div>

      <div className="validation-container">
        {/* 좌측: 입력 영역 */}
        <div className="input-section">
          <h3>힌트 요청 설정</h3>

          <div className="input-group">
            <label>문제 선택 *</label>
            <select
              value={activeSession.problemId}
              onChange={handleProblemSelect}
              className="input-field"
              disabled={loadingProblems}
            >
              <option value="">문제를 선택하세요</option>
              {problems.map(problem => (
                <option key={problem.problem_id} value={problem.problem_id}>
                  {problem.problem_id}. {problem.title}
                </option>
              ))}
            </select>
          </div>

          <div className="input-group">
            <label>작성 코드 *</label>
            <textarea
              value={activeSession.code}
              onChange={(e) => updateSession({ code: e.target.value })}
              placeholder="Python 코드를 입력하세요..."
              className="code-input"
              rows={12}
            />
          </div>

          <div className="input-group">
            <label>현재 별점 (시뮬레이션) → 힌트 목적 자동 결정</label>
            <div className="star-select">
              {[0, 1, 2, 3].map(star => (
                <button
                  key={star}
                  className={`star-btn ${activeSession.starCount === star ? 'active' : ''}`}
                  onClick={() => updateSession({ starCount: star })}
                  style={{
                    padding: '8px 16px',
                    margin: '0 4px',
                    border: activeSession.starCount === star ? '2px solid #4caf50' : '1px solid #ddd',
                    borderRadius: '4px',
                    backgroundColor: activeSession.starCount === star ? '#e8f5e9' : '#fff',
                    cursor: 'pointer',
                    fontSize: '14px'
                  }}
                >
                  {'⭐'.repeat(star) || '☆'} {star}개
                </button>
              ))}
            </div>
            <div style={{ marginTop: '8px', padding: '10px', backgroundColor: '#e3f2fd', borderRadius: '4px', fontSize: '13px' }}>
              <strong>자동 결정된 힌트 목적:</strong>{' '}
              {activeSession.starCount === 0 ? (
                <span style={{ color: '#1976d2' }}>💡 completion (코드 완성)</span>
              ) : activeSession.starCount < 3 ? (
                <span style={{ color: '#ff9800' }}>⚡ optimization (최적화)</span>
              ) : (
                <span style={{ color: '#4caf50' }}>🌟 optimal (다른 풀이 제안)</span>
              )}
            </div>
          </div>

          {/* COH 상태 표시 */}
          {activeSession.cohStatus && (
            <div className="coh-status-section" style={{ backgroundColor: '#e3f2fd', padding: '12px', borderRadius: '8px', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                <span className="coh-level-name" style={{ fontWeight: 'bold', color: '#1976d2' }}>
                  {activeSession.cohStatus.level_name}
                </span>
                <span className="coh-hint-level" style={{ fontSize: '13px', color: '#666' }}>
                  레벨 {activeSession.cohStatus.hint_level}/9
                </span>
              </div>
              {activeSession.cohStatus.can_get_more_detailed ? (
                <p style={{ fontSize: '13px', color: '#333', margin: 0 }}>
                  💡 {activeSession.cohStatus.next_level_hint}
                </p>
              ) : (
                <p style={{ fontSize: '13px', color: '#4caf50', margin: 0 }}>
                  ✨ 이미 가장 상세한 힌트 레벨입니다.
                </p>
              )}
            </div>
          )}

          <div className="preset-section">
            <label>힌트 프리셋 (💡 요약 설명 방식만 변경됩니다)</label>
            <div className="preset-buttons">
              {['초급', '중급', '고급'].map(preset => (
                <button
                  key={preset}
                  className={`preset-btn ${activeSession.preset === preset ? 'active' : ''}`}
                  onClick={() => handlePresetChange(preset)}
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>

          <div className="custom-components-section">
            <label>힌트 구성 요소 (💡 요약은 항상 포함됩니다)</label>
            <div className="component-checkboxes">
              {/* 순서: 차단되는 것들을 위에 배치 (위에서부터 차단됨) */}
              {[
                { key: 'code_example', label: '코드 예시' },      // 중급/고급 차단
                { key: 'step_by_step', label: '단계별 설명' },    // 중급/고급 차단
                { key: 'libraries', label: '라이브러리' },        // 고급에서만 차단
                { key: 'complexity_hint', label: '복잡도' },      // 항상 허용
                { key: 'edge_cases', label: '엣지 케이스' },      // 항상 허용
                { key: 'improvements', label: '개선사항' }        // 항상 허용
              ].map(({ key, label }) => {
                const isBlocked = activeSession.blockedComponents?.includes(key)
                return (
                  <div
                    key={key}
                    className="component-checkbox"
                    style={{ opacity: isBlocked ? 0.5 : 1 }}
                  >
                    <input
                      type="checkbox"
                      id={`${activeSessionId}-${key}`}
                      checked={activeSession.customComponents[key]}
                      disabled={isBlocked}
                      onChange={() => handleComponentToggle(key)}
                    />
                    <label htmlFor={`${activeSessionId}-${key}`}>
                      {label}
                      {isBlocked && <span style={{ marginLeft: '4px' }}>🔒</span>}
                    </label>
                  </div>
                )
              })}
            </div>
          </div>

          <div className="user-metrics-section">
            <label>사용자 지표 (12개) - 수동 설정 가능</label>
            <p style={{ fontSize: '12px', color: '#666', marginTop: '4px', marginBottom: '12px' }}>
              💡 이 지표 값을 기준으로 힌트가 생성됩니다. 원하는 값으로 수정 가능합니다.
            </p>

            <div className="metrics-input-grid">
              <div className="metrics-group">
                <h5>📋 정적 지표 (6개)</h5>
                <div className="metric-input-row">
                  <label htmlFor="syntax_errors">문법 오류 (개)</label>
                  <input
                    type="number"
                    id="syntax_errors"
                    min="0"
                    value={activeSession.userMetrics?.syntax_errors || 0}
                    onChange={(e) => handleUserMetricChange('syntax_errors', e.target.value)}
                    className="metric-input"
                  />
                </div>
                <div className="metric-input-row">
                  <label htmlFor="test_pass_rate">테스트 통과율 (%)</label>
                  <input
                    type="number"
                    id="test_pass_rate"
                    min="0"
                    max="100"
                    value={activeSession.userMetrics?.test_pass_rate || 0}
                    onChange={(e) => handleUserMetricChange('test_pass_rate', e.target.value)}
                    className="metric-input"
                  />
                </div>
                <div className="metric-input-row">
                  <label htmlFor="code_complexity">코드 복잡도 (1-10)</label>
                  <input
                    type="number"
                    id="code_complexity"
                    min="0"
                    max="10"
                    value={activeSession.userMetrics?.code_complexity || 0}
                    onChange={(e) => handleUserMetricChange('code_complexity', e.target.value)}
                    className="metric-input"
                  />
                </div>
                <div className="metric-input-row">
                  <label htmlFor="code_quality_score">코드 품질 (0-100)</label>
                  <input
                    type="number"
                    id="code_quality_score"
                    min="0"
                    max="100"
                    value={activeSession.userMetrics?.code_quality_score || 0}
                    onChange={(e) => handleUserMetricChange('code_quality_score', e.target.value)}
                    className="metric-input"
                  />
                </div>
                <div className="metric-input-row">
                  <label htmlFor="algorithm_pattern_match">알고리즘 패턴 매치 (0-5)</label>
                  <input
                    type="number"
                    id="algorithm_pattern_match"
                    min="0"
                    max="5"
                    step="0.1"
                    value={activeSession.userMetrics?.algorithm_pattern_match || 0}
                    onChange={(e) => handleUserMetricChange('algorithm_pattern_match', e.target.value)}
                    className="metric-input"
                  />
                </div>
                <div className="metric-input-row">
                  <label htmlFor="pep8_violations">PEP8 위반 (개)</label>
                  <input
                    type="number"
                    id="pep8_violations"
                    min="0"
                    value={activeSession.userMetrics?.pep8_violations || 0}
                    onChange={(e) => handleUserMetricChange('pep8_violations', e.target.value)}
                    className="metric-input"
                  />
                </div>
              </div>

              <div className="metrics-group">
                <h5>🤖 LLM 지표 (6개)</h5>
                <div className="metric-input-row">
                  <label htmlFor="algorithm_efficiency">알고리즘 효율성 (0-5)</label>
                  <input
                    type="number"
                    id="algorithm_efficiency"
                    min="0"
                    max="5"
                    step="0.1"
                    value={activeSession.userMetrics?.algorithm_efficiency || 0}
                    onChange={(e) => handleUserMetricChange('algorithm_efficiency', e.target.value)}
                    className="metric-input"
                  />
                </div>
                <div className="metric-input-row">
                  <label htmlFor="code_readability">코드 가독성 (0-5)</label>
                  <input
                    type="number"
                    id="code_readability"
                    min="0"
                    max="5"
                    step="0.1"
                    value={activeSession.userMetrics?.code_readability || 0}
                    onChange={(e) => handleUserMetricChange('code_readability', e.target.value)}
                    className="metric-input"
                  />
                </div>
                <div className="metric-input-row">
                  <label htmlFor="design_pattern_fit">디자인 패턴 적합성 (0-5)</label>
                  <input
                    type="number"
                    id="design_pattern_fit"
                    min="0"
                    max="5"
                    step="0.1"
                    value={activeSession.userMetrics?.design_pattern_fit || 0}
                    onChange={(e) => handleUserMetricChange('design_pattern_fit', e.target.value)}
                    className="metric-input"
                  />
                </div>
                <div className="metric-input-row">
                  <label htmlFor="edge_case_handling">엣지 케이스 처리 (0-5)</label>
                  <input
                    type="number"
                    id="edge_case_handling"
                    min="0"
                    max="5"
                    step="0.1"
                    value={activeSession.userMetrics?.edge_case_handling || 0}
                    onChange={(e) => handleUserMetricChange('edge_case_handling', e.target.value)}
                    className="metric-input"
                  />
                </div>
                <div className="metric-input-row">
                  <label htmlFor="code_conciseness">코드 간결성 (0-5)</label>
                  <input
                    type="number"
                    id="code_conciseness"
                    min="0"
                    max="5"
                    step="0.1"
                    value={activeSession.userMetrics?.code_conciseness || 0}
                    onChange={(e) => handleUserMetricChange('code_conciseness', e.target.value)}
                    className="metric-input"
                  />
                </div>
                <div className="metric-input-row">
                  <label htmlFor="function_separation">함수 분리 (0-5)</label>
                  <input
                    type="number"
                    id="function_separation"
                    min="0"
                    max="5"
                    step="0.1"
                    value={activeSession.userMetrics?.function_separation || 0}
                    onChange={(e) => handleUserMetricChange('function_separation', e.target.value)}
                    className="metric-input"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="action-buttons">
            <button
              onClick={handleValidate}
              disabled={loading || generatingCoh || !activeSession.code.trim() || !activeSession.problemId}
              className="btn-validate"
            >
              {loading ? '검증 중...' : '💡 힌트 생성'}
            </button>
            <button
              onClick={handleGenerateAllCohSteps}
              disabled={loading || generatingCoh || !activeSession.code.trim() || !activeSession.problemId}
              className="btn-validate"
              style={{
                backgroundColor: generatingCoh ? '#ccc' : '#673ab7',
                marginLeft: '8px'
              }}
            >
              {generatingCoh ? cohProgress || 'COH 생성 중...' : '🔗 COH 전체 단계 생성'}
            </button>
            <button
              onClick={handleClearSession}
              disabled={loading || generatingCoh}
              className="btn-clear"
            >
              🗑️ 초기화
            </button>
          </div>

          {error && (
            <div className="error-message">
              ❌ {error}
            </div>
          )}
        </div>

        {/* 우측: 결과 & 힌트 영역 */}
        <div className="results-wrapper">
          {/* 검증 결과 */}
          <div className="result-section">
            <h3>검증 결과</h3>

            {!latestResult ? (
              <div className="result-empty">
                <p>검증 결과가 없습니다.</p>
                <p>코드를 입력하고 검증을 시작하세요.</p>
              </div>
            ) : (
              <>
                {/* 종합 점수 */}
                <div className="total-score-card">
                  <h4>종합 점수</h4>
                  <div className="score-display" style={{ color: getScoreColor(latestResult.totalScore) }}>
                    {latestResult.totalScore.toFixed(1)}
                    <span className="score-suffix">/100</span>
                  </div>
                  <div className="score-bar">
                    <div
                      className="score-fill"
                      style={{
                        width: `${latestResult.totalScore}%`,
                        backgroundColor: getScoreColor(latestResult.totalScore)
                      }}
                    />
                  </div>
                </div>

                {/* 12개 지표 */}
                <div className="metrics-card">
                  <h4>📋 정적 지표 (6개)</h4>
                  <div className="metrics-grid">
                    <div className="metric-item">
                      <span className="metric-label">문법 오류</span>
                      <span
                        className="metric-value"
                        style={{ color: latestResult.static_metrics.syntax_errors === 0 ? '#4caf50' : '#f44336' }}
                      >
                        {latestResult.static_metrics.syntax_errors}개
                      </span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">테스트 통과율</span>
                      <span
                        className="metric-value"
                        style={{ color: getMetricColor(latestResult.static_metrics.test_pass_rate, 100) }}
                      >
                        {latestResult.static_metrics.test_pass_rate}%
                      </span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">실행 시간</span>
                      <span
                        className="metric-value"
                        style={{ color: (latestResult.static_metrics.execution_time || 0) <= 100 ? '#4caf50' : '#ff9800' }}
                      >
                        {(latestResult.static_metrics.execution_time || 0).toFixed(2)}ms
                      </span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">메모리 사용량</span>
                      <span
                        className="metric-value"
                        style={{ color: (latestResult.static_metrics.memory_usage || 0) <= 1000 ? '#4caf50' : '#ff9800' }}
                      >
                        {(latestResult.static_metrics.memory_usage || 0).toFixed(2)}KB
                      </span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">코드 품질</span>
                      <span
                        className="metric-value"
                        style={{ color: getMetricColor(latestResult.static_metrics.code_quality_score, 100) }}
                      >
                        {latestResult.static_metrics.code_quality_score}/100
                      </span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">PEP8 위반</span>
                      <span
                        className="metric-value"
                        style={{ color: latestResult.static_metrics.pep8_violations === 0 ? '#4caf50' : '#ff9800' }}
                      >
                        {latestResult.static_metrics.pep8_violations}개
                      </span>
                    </div>
                  </div>
                </div>

                <div className="metrics-card">
                  <h4>🤖 LLM 지표 (6개)</h4>
                  <div className="metrics-grid">
                    <div className="metric-item">
                      <span className="metric-label">알고리즘 효율성</span>
                      <span
                        className="metric-value"
                        style={{ color: getMetricColor(latestResult.llm_metrics.algorithm_efficiency) }}
                      >
                        {latestResult.llm_metrics.algorithm_efficiency}/5
                      </span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">코드 가독성</span>
                      <span
                        className="metric-value"
                        style={{ color: getMetricColor(latestResult.llm_metrics.code_readability) }}
                      >
                        {latestResult.llm_metrics.code_readability}/5
                      </span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">엣지 케이스</span>
                      <span
                        className="metric-value"
                        style={{ color: getMetricColor(latestResult.llm_metrics.edge_case_handling) }}
                      >
                        {latestResult.llm_metrics.edge_case_handling}/5
                      </span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">코드 간결성</span>
                      <span
                        className="metric-value"
                        style={{ color: getMetricColor(latestResult.llm_metrics.code_conciseness) }}
                      >
                        {latestResult.llm_metrics.code_conciseness}/5
                      </span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">테스트 커버리지</span>
                      <span
                        className="metric-value"
                        style={{ color: getMetricColor(latestResult.llm_metrics.test_coverage_estimate || 3) }}
                      >
                        {latestResult.llm_metrics.test_coverage_estimate || 3}/5
                      </span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">보안 인식</span>
                      <span
                        className="metric-value"
                        style={{ color: getMetricColor(latestResult.llm_metrics.security_awareness || 3) }}
                      >
                        {latestResult.llm_metrics.security_awareness || 3}/5
                      </span>
                    </div>
                  </div>
                </div>

                {/* 분기 정보 및 별점 */}
                {latestResult.hint_branch && (
                  <div className="hint-purpose-card" style={{ backgroundColor: '#f5f5f5', padding: '16px', borderRadius: '8px', marginTop: '16px' }}>
                    <h4 style={{ margin: '0 0 12px 0' }}>
                      🔀 힌트 분기: <span style={{ color: '#1976d2' }}>{latestResult.hint_branch}</span>
                    </h4>
                    <div style={{ fontSize: '14px', color: '#333', marginBottom: '8px' }}>
                      <strong>별점:</strong> {'⭐'.repeat(latestResult.current_star_count || 0) || '☆'} ({latestResult.current_star_count || 0}/3)
                    </div>
                    <div style={{ fontSize: '14px', color: '#333', marginBottom: '8px' }}>
                      <strong>로직 완성:</strong> {latestResult.is_logic_complete ? '✅ 테스트 통과' : '❌ 테스트 미통과'}
                    </div>
                    {latestResult.purpose_context && (
                      <div style={{ fontSize: '13px', color: '#666', backgroundColor: '#fff', padding: '10px', borderRadius: '4px', marginTop: '8px' }}>
                        {latestResult.purpose_context}
                      </div>
                    )}
                  </div>
                )}

                {/* 힌트 목적 및 약한 메트릭 */}
                {latestResult.hint_purpose && (
                  <div className="hint-purpose-card">
                    <h4>
                      {latestResult.hint_purpose === 'completion' ? '💡 완료 목적'
                        : latestResult.hint_purpose === 'optimization' ? '⚡ 최적화 목적'
                        : '🌟 최적 달성'}
                    </h4>
                    <p style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>
                      {latestResult.hint_purpose === 'completion'
                        ? '코드를 동작하게 만들기 (문법 오류 수정 또는 다음 단계 로직)'
                        : latestResult.hint_purpose === 'optimization'
                          ? '코드를 효율적으로 만들기 (약한 메트릭 개선)'
                          : '별 3개 달성! 다른 풀이 방법 제안'}
                    </p>

                    {latestResult.hint_purpose === 'optimization' && latestResult.weak_metrics && latestResult.weak_metrics.length > 0 && (
                      <div style={{ marginTop: '12px' }}>
                        <strong style={{ fontSize: '13px' }}>약한 메트릭 (개선 필요):</strong>
                        <ul style={{ marginTop: '8px', paddingLeft: '20px', fontSize: '13px', color: '#f44336' }}>
                          {latestResult.weak_metrics.map((wm, idx) => (
                            <li key={idx}>
                              {wm.description} (점수: {wm.score.toFixed(2)})
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* 구성 안내 */}
                    {(latestResult.selected_components?.length > 0 || latestResult.unselected_components?.length > 0) && (
                      <div style={{ marginTop: '12px', padding: '10px', backgroundColor: '#e3f2fd', borderRadius: '4px' }}>
                        <strong style={{ fontSize: '13px' }}>📋 구성 안내:</strong>
                        {latestResult.selected_components?.length > 0 && (
                          <p style={{ fontSize: '12px', color: '#1976d2', marginTop: '4px' }}>
                            → 선택: {latestResult.selected_components.join(', ')}
                          </p>
                        )}
                        {latestResult.unselected_components?.length > 0 && (
                          <p style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                            → 미선택: {latestResult.unselected_components.join(', ')}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          {/* COH 전체 단계 비교 뷰 */}
          {cohAllSteps.length > 0 && (
            <div className="coh-comparison-section" style={{
              marginBottom: '20px',
              padding: '20px',
              backgroundColor: '#f3e5f5',
              borderRadius: '12px',
              border: '2px solid #ce93d8'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, color: '#7b1fa2' }}>
                  🔗 Chain of Hints - 전체 단계 비교
                </h3>
                <button
                  onClick={() => setCohAllSteps([])}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: 'transparent',
                    color: '#7b1fa2',
                    border: '1px solid #7b1fa2',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '13px'
                  }}
                >
                  ✕ 닫기
                </button>
              </div>

              <p style={{ fontSize: '13px', color: '#666', marginBottom: '16px' }}>
                💡 Chain of Hints는 이전 힌트를 기반으로 점점 더 상세한 힌트를 제공합니다.
                아래에서 각 단계별 힌트 변화를 비교해 보세요.
              </p>

              {/* 9단계 힌트 카드 */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {cohAllSteps.map((step, idx) => {
                  // 프리셋별 색상
                  const presetColors = {
                    '고급': '#9c27b0',    // 보라색
                    '중급': '#ff9800',    // 주황색
                    '초급': '#4caf50'     // 초록색
                  }
                  const borderColor = presetColors[step.preset] || '#2196f3'

                  // summary 제외한 차단된 구성요소
                  const filteredBlockedComponents = (step.blocked_components || []).filter(c => c !== 'summary')

                  return (
                  <div
                    key={idx}
                    style={{
                      backgroundColor: '#fff',
                      borderRadius: '8px',
                      padding: '16px',
                      border: `2px solid ${borderColor}`,
                      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                    }}
                  >
                    {/* 단계 헤더 */}
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '12px',
                      paddingBottom: '12px',
                      borderBottom: '1px solid #eee'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: '32px',
                          height: '32px',
                          borderRadius: '50%',
                          backgroundColor: borderColor,
                          color: '#fff',
                          fontWeight: 'bold',
                          fontSize: '14px'
                        }}>
                          {step.stepIndex || idx + 1}
                        </span>
                        <div>
                          <div style={{ fontWeight: 'bold', fontSize: '15px', color: '#333' }}>
                            {step.stepName || `단계 ${idx + 1}`}
                          </div>
                          <div style={{ fontSize: '12px', color: '#666' }}>
                            레벨: {step.actualLevel || step.hint_level}/9 · COH 깊이: {step.coh_depth}
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        {step.coh_status?.level_name && (
                          <span style={{
                            padding: '4px 10px',
                            backgroundColor: '#e3f2fd',
                            borderRadius: '12px',
                            fontSize: '12px',
                            color: '#1976d2',
                            fontWeight: '500'
                          }}>
                            {step.coh_status.level_name}
                          </span>
                        )}
                        <span style={{
                          padding: '4px 10px',
                          backgroundColor: borderColor + '20',
                          borderRadius: '12px',
                          fontSize: '12px',
                          color: borderColor,
                          fontWeight: '500'
                        }}>
                          {step.preset}
                        </span>
                      </div>
                    </div>

                    {/* 차단된 구성요소 표시 (summary 제외) */}
                    {filteredBlockedComponents.length > 0 && (
                      <div style={{
                        marginBottom: '12px',
                        padding: '8px 12px',
                        backgroundColor: '#ffebee',
                        borderRadius: '4px',
                        fontSize: '12px',
                        color: '#c62828'
                      }}>
                        🔒 차단된 구성요소: {filteredBlockedComponents.join(', ')}
                      </div>
                    )}

                    {/* 힌트 내용 */}
                    <div style={{
                      fontSize: '14px',
                      lineHeight: '1.7',
                      color: '#333',
                      whiteSpace: 'pre-wrap'
                    }}>
                      {step.hint.split('\n').map((line, i) => (
                        <p key={i} style={{ margin: '0 0 8px 0' }}>{line}</p>
                      ))}
                    </div>

                    {/* 메트릭 요약 (축소된 형태) */}
                    <details style={{ marginTop: '12px' }}>
                      <summary style={{
                        cursor: 'pointer',
                        fontSize: '13px',
                        color: '#666',
                        padding: '8px',
                        backgroundColor: '#f9f9f9',
                        borderRadius: '4px'
                      }}>
                        📊 메트릭 정보 보기
                      </summary>
                      <div style={{
                        marginTop: '8px',
                        padding: '12px',
                        backgroundColor: '#f9f9f9',
                        borderRadius: '4px',
                        fontSize: '12px'
                      }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                          <div>종합 점수: <strong>{step.total_score?.toFixed(1) || 'N/A'}</strong></div>
                          <div>테스트 통과율: <strong>{step.static_metrics?.test_pass_rate || 0}%</strong></div>
                          <div>알고리즘 효율성: <strong>{step.llm_metrics?.algorithm_efficiency || 0}/5</strong></div>
                        </div>
                      </div>
                    </details>
                  </div>
                  )
                })}
              </div>

              {/* 단계별 변화 요약 */}
              {cohAllSteps.length === 9 && (
                <div style={{
                  marginTop: '16px',
                  padding: '16px',
                  backgroundColor: '#fff',
                  borderRadius: '8px',
                  border: '1px solid #ce93d8'
                }}>
                  <h4 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#7b1fa2' }}>
                    📈 9단계 힌트 시스템 요약
                  </h4>
                  <div style={{ fontSize: '13px', color: '#666', lineHeight: '1.8' }}>
                    <p style={{ margin: '0 0 8px 0' }}>
                      <strong style={{ color: '#9c27b0' }}>고급 (1-2단계):</strong> 소크라테스식 질문으로 스스로 답을 찾게 유도
                    </p>
                    <p style={{ margin: '0 0 8px 0' }}>
                      <strong style={{ color: '#ff9800' }}>중급 (3-5단계):</strong> 개념적 힌트, 알고리즘/자료구조 방향 제시
                    </p>
                    <p style={{ margin: '0 0 8px 0' }}>
                      <strong style={{ color: '#4caf50' }}>초급 (6-9단계):</strong> 구체적인 함수명, 코드 예시까지 상세 안내
                    </p>
                    <p style={{ margin: 0, color: '#7b1fa2' }}>
                      💡 같은 프리셋에서 힌트를 반복 요청하면 COH가 증가하여 더 상세한 힌트를 받을 수 있습니다.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 힌트 영역 */}
          <div className="hint-section">
            <h3>생성된 힌트</h3>

            {!latestResult && cohAllSteps.length === 0 ? (
              <div className="hint-empty">
                <p>아직 생성된 힌트가 없습니다.</p>
                <p>문제와 코드를 입력하고 힌트를 생성하세요.</p>
              </div>
            ) : !latestResult && cohAllSteps.length > 0 ? (
              <div className="hint-empty">
                <p>위의 COH 비교 뷰에서 전체 단계를 확인하세요.</p>
              </div>
            ) : (
              <>
                {/* 최신 힌트 */}
                <div className="hint-card">
                  <div className="hint-header">
                    <h4>💡 최신 힌트</h4>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <span className="hint-preset-badge">{latestResult.preset}</span>
                      {latestResult.coh_status && (
                        <>
                          <span style={{ fontSize: '12px', padding: '2px 8px', backgroundColor: '#e3f2fd', borderRadius: '4px', color: '#1976d2' }}>
                            {latestResult.coh_status.level_name}
                          </span>
                          <span style={{ fontSize: '11px', color: '#666' }}>
                            Lv.{latestResult.hint_level}/9
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  {/* COH 상세 정보 */}
                  {latestResult.coh_status && (
                    <div style={{ padding: '8px 12px', backgroundColor: '#f5f5f5', borderRadius: '4px', marginBottom: '12px', fontSize: '13px' }}>
                      <span>
                        <strong>COH 깊이:</strong> {latestResult.coh_depth || 0}
                      </span>
                      {latestResult.blocked_components && latestResult.blocked_components.filter(c => c !== 'summary').length > 0 && (
                        <span style={{ marginLeft: '16px', color: '#f44336' }}>
                          <strong>🔒 차단됨:</strong> {latestResult.blocked_components.filter(c => c !== 'summary').join(', ')}
                        </span>
                      )}
                    </div>
                  )}
                  <div className="hint-content">
                    {latestResult.hint.split('\n').map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                  </div>
                </div>

                {/* LLM-as-Judge 평가 섹션 */}
                <div className="evaluation-section" style={{ marginTop: '16px', padding: '16px', backgroundColor: '#fff3e0', borderRadius: '8px', border: '1px solid #ffcc80' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <h4 style={{ margin: 0, color: '#e65100' }}>🤖 LLM-as-Judge 평가</h4>
                    <button
                      onClick={handleEvaluateHint}
                      disabled={evaluating || !latestResult}
                      style={{
                        padding: '8px 16px',
                        backgroundColor: evaluating ? '#ccc' : '#ff9800',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: evaluating ? 'not-allowed' : 'pointer',
                        fontSize: '14px',
                        fontWeight: 'bold'
                      }}
                    >
                      {evaluating ? '평가 중...' : '⚖️ 힌트 평가하기'}
                    </button>
                  </div>

                  {evaluationError && (
                    <div style={{ padding: '10px', backgroundColor: '#ffebee', color: '#c62828', borderRadius: '4px', marginBottom: '12px' }}>
                      ❌ {evaluationError}
                    </div>
                  )}

                  {evaluationResult && (
                    <div className="evaluation-result">
                      {/* 평균 점수 */}
                      <div style={{ textAlign: 'center', padding: '16px', backgroundColor: '#fff', borderRadius: '8px', marginBottom: '16px' }}>
                        <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>평균 점수</div>
                        <div style={{
                          fontSize: '48px',
                          fontWeight: 'bold',
                          color: evaluationResult.average_score >= 4 ? '#4caf50' : evaluationResult.average_score >= 3 ? '#ff9800' : '#f44336'
                        }}>
                          {evaluationResult.average_score.toFixed(2)}
                          <span style={{ fontSize: '20px', color: '#999' }}>/5</span>
                        </div>
                      </div>

                      {/* 5개 지표 점수 */}
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginBottom: '16px' }}>
                        {[
                          { key: 'hint_relevance', label: '힌트 관련성', icon: '🎯' },
                          { key: 'educational_value', label: '교육적 가치', icon: '📚' },
                          { key: 'difficulty_appropriateness', label: '난이도 적절성', icon: '📊' },
                          { key: 'code_accuracy', label: '코드 정확성', icon: '✅' },
                          { key: 'completeness', label: '완전성', icon: '🔗' }
                        ].map(({ key, label, icon }) => (
                          <div key={key} style={{
                            padding: '12px',
                            backgroundColor: '#fff',
                            borderRadius: '6px',
                            border: '1px solid #eee'
                          }}>
                            <div style={{ fontSize: '13px', color: '#666', marginBottom: '6px' }}>
                              {icon} {label}
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <div style={{
                                fontSize: '24px',
                                fontWeight: 'bold',
                                color: evaluationResult.scores[key] >= 4 ? '#4caf50' : evaluationResult.scores[key] >= 3 ? '#ff9800' : '#f44336'
                              }}>
                                {evaluationResult.scores[key]}
                              </div>
                              <div style={{ flex: 1, height: '8px', backgroundColor: '#eee', borderRadius: '4px' }}>
                                <div style={{
                                  width: `${(evaluationResult.scores[key] / 5) * 100}%`,
                                  height: '100%',
                                  backgroundColor: evaluationResult.scores[key] >= 4 ? '#4caf50' : evaluationResult.scores[key] >= 3 ? '#ff9800' : '#f44336',
                                  borderRadius: '4px'
                                }} />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* 상세 피드백 */}
                      <div style={{ backgroundColor: '#fff', borderRadius: '6px', padding: '12px', border: '1px solid #eee' }}>
                        <h5 style={{ margin: '0 0 12px 0', color: '#333' }}>📝 상세 피드백</h5>
                        {Object.entries(evaluationResult.feedback).map(([key, feedback]) => (
                          <div key={key} style={{ marginBottom: '10px', paddingBottom: '10px', borderBottom: '1px solid #f5f5f5' }}>
                            <strong style={{ fontSize: '13px', color: '#1976d2' }}>
                              {key === 'hint_relevance' ? '힌트 관련성' :
                               key === 'educational_value' ? '교육적 가치' :
                               key === 'difficulty_appropriateness' ? '난이도 적절성' :
                               key === 'code_accuracy' ? '코드 정확성' :
                               key === 'completeness' ? '완전성' : key}:
                            </strong>
                            <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#666' }}>{feedback}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {!evaluationResult && !evaluationError && (
                    <div style={{ textAlign: 'center', padding: '20px', color: '#999', fontSize: '14px' }}>
                      💡 GPT-4o를 사용하여 생성된 힌트의 품질을 5개 지표로 평가합니다.<br/>
                      <span style={{ fontSize: '12px' }}>힌트 관련성, 교육적 가치, 난이도 적절성, 코드 정확성, 완전성</span>
                    </div>
                  )}

                  {/* LLM 평가 저장 버튼 */}
                  {evaluationResult && (
                    <button
                      onClick={() => handleSaveEvaluation('llm')}
                      disabled={savingEvaluation}
                      style={{
                        width: '100%',
                        padding: '12px',
                        marginTop: '12px',
                        backgroundColor: savingEvaluation ? '#ccc' : '#ff9800',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: savingEvaluation ? 'not-allowed' : 'pointer',
                        fontSize: '14px',
                        fontWeight: 'bold'
                      }}
                    >
                      {savingEvaluation ? '저장 중...' : '💾 LLM 평가 결과 저장'}
                    </button>
                  )}
                </div>

                {/* 휴먼 평가 섹션 */}
                <div className="human-evaluation-section" style={{ marginTop: '16px', padding: '16px', backgroundColor: '#e8f5e9', borderRadius: '8px', border: '1px solid #a5d6a7' }}>
                  <h4 style={{ margin: '0 0 16px 0', color: '#2e7d32' }}>👤 휴먼 평가</h4>

                  {/* 5개 지표 점수 입력 */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginBottom: '16px' }}>
                    {[
                      { key: 'hint_relevance', label: '힌트 관련성', icon: '🎯' },
                      { key: 'educational_value', label: '교육적 가치', icon: '📚' },
                      { key: 'difficulty_appropriateness', label: '난이도 적절성', icon: '📊' },
                      { key: 'code_accuracy', label: '코드 정확성', icon: '✅' },
                      { key: 'completeness', label: '완전성', icon: '🔗' }
                    ].map(({ key, label, icon }) => (
                      <div key={key} style={{
                        padding: '12px',
                        backgroundColor: '#fff',
                        borderRadius: '6px',
                        border: '1px solid #c8e6c9'
                      }}>
                        <div style={{ fontSize: '13px', color: '#666', marginBottom: '8px' }}>
                          {icon} {label}
                        </div>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          {[1, 2, 3, 4, 5].map(score => (
                            <button
                              key={score}
                              onClick={() => setHumanScores({ ...humanScores, [key]: score })}
                              style={{
                                flex: 1,
                                padding: '8px',
                                border: humanScores[key] === score ? '2px solid #4caf50' : '1px solid #ddd',
                                borderRadius: '4px',
                                backgroundColor: humanScores[key] === score ? '#e8f5e9' : '#fff',
                                cursor: 'pointer',
                                fontWeight: humanScores[key] === score ? 'bold' : 'normal',
                                color: humanScores[key] === score ? '#2e7d32' : '#666'
                              }}
                            >
                              {score}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* 평균 점수 표시 */}
                  {Object.values(humanScores).some(v => v > 0) && (
                    <div style={{ textAlign: 'center', padding: '12px', backgroundColor: '#fff', borderRadius: '6px', marginBottom: '12px' }}>
                      <span style={{ fontSize: '14px', color: '#666' }}>평균: </span>
                      <span style={{
                        fontSize: '24px',
                        fontWeight: 'bold',
                        color: (() => {
                          const validScores = Object.values(humanScores).filter(v => v > 0)
                          const avg = validScores.length > 0 ? validScores.reduce((a, b) => a + b, 0) / validScores.length : 0
                          return avg >= 4 ? '#4caf50' : avg >= 3 ? '#ff9800' : '#f44336'
                        })()
                      }}>
                        {(() => {
                          const validScores = Object.values(humanScores).filter(v => v > 0)
                          return validScores.length > 0 ? (validScores.reduce((a, b) => a + b, 0) / validScores.length).toFixed(2) : '0'
                        })()}
                      </span>
                      <span style={{ fontSize: '14px', color: '#999' }}>/5</span>
                    </div>
                  )}

                  {/* 종합 의견 */}
                  <div style={{ marginBottom: '12px' }}>
                    <label style={{ fontSize: '13px', color: '#666', display: 'block', marginBottom: '6px' }}>
                      종합 의견 (선택사항)
                    </label>
                    <textarea
                      value={humanComment}
                      onChange={(e) => setHumanComment(e.target.value)}
                      placeholder="힌트에 대한 의견을 작성해주세요..."
                      style={{
                        width: '100%',
                        padding: '10px',
                        border: '1px solid #c8e6c9',
                        borderRadius: '6px',
                        minHeight: '80px',
                        resize: 'vertical',
                        fontSize: '14px'
                      }}
                    />
                  </div>

                  {/* 휴먼 평가 저장 버튼 */}
                  <button
                    onClick={() => handleSaveEvaluation('human')}
                    disabled={savingEvaluation || Object.values(humanScores).every(v => v === 0)}
                    style={{
                      width: '100%',
                      padding: '12px',
                      backgroundColor: savingEvaluation || Object.values(humanScores).every(v => v === 0) ? '#ccc' : '#4caf50',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: savingEvaluation || Object.values(humanScores).every(v => v === 0) ? 'not-allowed' : 'pointer',
                      fontSize: '14px',
                      fontWeight: 'bold'
                    }}
                  >
                    {savingEvaluation ? '저장 중...' : '💾 휴먼 평가 저장'}
                  </button>
                </div>

                {/* 저장 메시지 */}
                {saveMessage && (
                  <div style={{
                    marginTop: '12px',
                    padding: '12px',
                    backgroundColor: saveMessage.includes('저장되었습니다') ? '#e8f5e9' : '#ffebee',
                    color: saveMessage.includes('저장되었습니다') ? '#2e7d32' : '#c62828',
                    borderRadius: '6px',
                    textAlign: 'center'
                  }}>
                    {saveMessage}
                  </div>
                )}

                {/* 힌트 히스토리 - Accordion 형태 */}
                {activeSession.history.length > 1 && (
                  <div className="history-card">
                    <h4>📜 이전 힌트 ({activeSession.history.length - 1}개)</h4>
                    <div className="history-accordion">
                      {activeSession.history.slice(0, -1).reverse().map((item, index) => {
                        const historyNumber = activeSession.history.length - 1 - index
                        return (
                          <details key={index} className="history-accordion-item">
                            <summary className="history-accordion-summary">
                              <div className="history-summary-left">
                                <span className="history-number">#{historyNumber}</span>
                                <span className="history-preset-tag">
                                  {item.coh_status?.level_name || item.preset}
                                </span>
                                {item.hint_level && (
                                  <span style={{ fontSize: '11px', color: '#1976d2', padding: '1px 4px', backgroundColor: '#e3f2fd', borderRadius: '2px' }}>
                                    Lv.{item.hint_level}
                                  </span>
                                )}
                                <span className="history-timestamp">{item.timestamp}</span>
                              </div>
                              <span
                                className="history-score-badge"
                                style={{ backgroundColor: getScoreColor(item.totalScore) }}
                              >
                                {item.totalScore.toFixed(0)}점
                              </span>
                            </summary>
                            <div className="history-accordion-content">
                              {/* 생성 조건 */}
                              <div className="hint-generation-conditions">
                                <h5>🔧 생성 조건</h5>

                                {/* COH 정보 */}
                                {item.coh_status && (
                                  <div className="condition-item" style={{ backgroundColor: '#e3f2fd', padding: '8px', borderRadius: '4px', marginBottom: '8px' }}>
                                    <strong>🔗 COH 상태:</strong>
                                    <span style={{ marginLeft: '8px' }}>
                                      {item.coh_status.level_name} (레벨 {item.hint_level}/9, COH 깊이: {item.coh_depth || 0})
                                    </span>
                                    {item.blocked_components && item.blocked_components.length > 0 && (
                                      <span style={{ display: 'block', marginTop: '4px', color: '#f44336', fontSize: '12px' }}>
                                        🔒 차단된 구성요소: {item.blocked_components.join(', ')}
                                      </span>
                                    )}
                                  </div>
                                )}

                                <div className="condition-item">
                                  <strong>코딩 목적:</strong>
                                  <span className="condition-badge">
                                    {item.hint_purpose === 'completion' ? '💡 완료 (코드 동작)' : '⚡ 최적화 (성능 개선)'}
                                  </span>
                                </div>

                                {item.hint_purpose === 'optimization' && item.weak_metrics && item.weak_metrics.length > 0 && (
                                  <div className="condition-item">
                                    <strong>약한 메트릭:</strong>
                                    <ul className="weak-metrics-list">
                                      {item.weak_metrics.map((wm, idx) => (
                                        <li key={idx}>{wm.description} (점수: {wm.score.toFixed(2)})</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                <div className="condition-item">
                                  <strong>힌트 프리셋:</strong>
                                  <span>{item.preset}</span>
                                </div>

                                {item.hint_components && (
                                  <div className="condition-item">
                                    <strong>포함된 구성 요소:</strong>
                                    <div className="components-list">
                                      {Object.entries(item.hint_components).filter(([key, val]) => val).map(([key]) => (
                                        <span key={key} className="component-tag">
                                          {key === 'summary' ? '요약' :
                                           key === 'libraries' ? '라이브러리' :
                                           key === 'code_example' ? '코드 예시' :
                                           key === 'step_by_step' ? '단계별 설명' :
                                           key === 'complexity_hint' ? '복잡도' :
                                           key === 'edge_cases' ? '엣지 케이스' :
                                           key === 'improvements' ? '개선사항' : key}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                <div className="condition-item">
                                  <strong>📊 정적 지표 (6개):</strong>
                                  <div className="metrics-mini-grid">
                                    <span>문법 오류: <strong>{item.static_metrics.syntax_errors}개</strong></span>
                                    <span>테스트 통과율: <strong>{item.static_metrics.test_pass_rate}%</strong></span>
                                    <span>실행 시간: <strong>{(item.static_metrics.execution_time || 0).toFixed(2)}ms</strong></span>
                                    <span>메모리: <strong>{(item.static_metrics.memory_usage || 0).toFixed(2)}KB</strong></span>
                                    <span>코드 품질: <strong>{item.static_metrics.code_quality_score}/100</strong></span>
                                    <span>PEP8 위반: <strong>{item.static_metrics.pep8_violations}개</strong></span>
                                  </div>
                                </div>

                                <div className="condition-item">
                                  <strong>🤖 LLM 지표 (6개):</strong>
                                  <div className="metrics-mini-grid">
                                    <span>알고리즘 효율성: <strong>{item.llm_metrics.algorithm_efficiency}/5</strong></span>
                                    <span>코드 가독성: <strong>{item.llm_metrics.code_readability}/5</strong></span>
                                    <span>엣지 케이스: <strong>{item.llm_metrics.edge_case_handling}/5</strong></span>
                                    <span>코드 간결성: <strong>{item.llm_metrics.code_conciseness}/5</strong></span>
                                    <span>테스트 커버리지: <strong>{item.llm_metrics.test_coverage_estimate || 3}/5</strong></span>
                                    <span>보안 인식: <strong>{item.llm_metrics.security_awareness || 3}/5</strong></span>
                                  </div>
                                </div>
                              </div>

                              {/* 생성된 힌트 */}
                              <div className="hint-content-history">
                                <h5>💡 생성된 힌트</h5>
                                <div className="hint-text">
                                  {item.hint.split('\n').map((line, i) => (
                                    <p key={i}>{line}</p>
                                  ))}
                                </div>
                              </div>
                            </div>
                          </details>
                        )
                      })}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
