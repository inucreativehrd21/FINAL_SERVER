import React, { useState, useEffect } from 'react';
import api from '../../../../services/api';
import './styles.css';

const ProblemDataValidationTab = () => {
  const [problems, setProblems] = useState([]);
  const [selectedProblemId, setSelectedProblemId] = useState('');
  const [validationResult, setValidationResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedTests, setExpandedTests] = useState(new Set());
  const [expandedSolutions, setExpandedSolutions] = useState(new Set());

  // 문제 목록 로드
  useEffect(() => {
    loadProblems();
  }, []);

  const loadProblems = async () => {
    try {
      const response = await api.get('/coding-test/admin/problem-data/list/');
      if (response.data.success) {
        setProblems(response.data.data);
      }
    } catch (err) {
      console.error('Failed to load problems:', err);
      setError('문제 목록을 불러오는데 실패했습니다.');
    }
  };

  const handleValidate = async () => {
    if (!selectedProblemId) {
      setError('문제를 선택해주세요.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setValidationResult(null);

    try {
      const response = await api.post('/coding-test/admin/problem-data/validate/', {
        problem_id: selectedProblemId
      });

      if (response.data.success) {
        setValidationResult(response.data.data);
      }
    } catch (err) {
      console.error('Validation failed:', err);
      setError(err.response?.data?.error || '검증 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleTest = (testId) => {
    setExpandedTests(prev => {
      const newSet = new Set(prev);
      if (newSet.has(testId)) {
        newSet.delete(testId);
      } else {
        newSet.add(testId);
      }
      return newSet;
    });
  };

  const toggleSolution = (solutionIdx) => {
    setExpandedSolutions(prev => {
      const newSet = new Set(prev);
      if (newSet.has(solutionIdx)) {
        newSet.delete(solutionIdx);
      } else {
        newSet.add(solutionIdx);
      }
      return newSet;
    });
  };

  const renderTestResult = (result, index) => {
    const isCorrect = result.is_correct;
    const isExpanded = expandedTests.has(index);

    return (
      <div key={index} className={`test-result ${isCorrect ? 'pass' : 'fail'}`}>
        <div
          className="test-header clickable"
          onClick={() => toggleTest(index)}
        >
          <div className="test-header-left">
            <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
            <span className="test-label">{result.label}</span>
          </div>
          <span className={`test-status ${isCorrect ? 'pass' : 'fail'}`}>
            {isCorrect ? '✓ PASS' : '✗ FAIL'}
          </span>
        </div>

        {isExpanded && (
          <div className="test-details">
            <div className="test-io">
              <div className="io-section">
                <strong>입력:</strong>
                <pre className="io-content">{result.input || '(없음)'}</pre>
              </div>

              <div className="io-section">
                <strong>기대 출력:</strong>
                <pre className="io-content expected">{result.expected_output}</pre>
              </div>

              <div className="io-section">
                <strong>실제 출력:</strong>
                <pre className={`io-content actual ${isCorrect ? 'correct' : 'incorrect'}`}>
                  {result.actual_output || '(출력 없음)'}
                </pre>
              </div>
            </div>

            {result.error && (
              <div className="error-section">
                <strong>에러:</strong>
                <pre className="error-content">{result.error}</pre>
              </div>
            )}

            <div className="metrics">
              <span>실행 시간: {result.execution_time?.toFixed(3)}s</span>
              <span>메모리: {result.memory_usage?.toFixed(2)}MB</span>
            </div>
          </div>
        )}
      </div>
    );
  };

  const selectedProblem = problems.find(p => p.problem_id === selectedProblemId);

  return (
    <div className="problem-data-validation-tab">
      <div className="validation-header">
        <h2>문제 데이터 검증</h2>
        <p className="description">
          problems_final_output.json 파일의 각 문제 데이터를 검증합니다.
          solution_code를 examples와 hidden_test_cases에 대해 실행하여 결과를 확인할 수 있습니다.
        </p>
      </div>

      <div className="problem-selector-section">
        <div className="selector-group">
          <label htmlFor="problem-select">문제 선택:</label>
          <select
            id="problem-select"
            value={selectedProblemId}
            onChange={(e) => setSelectedProblemId(e.target.value)}
            disabled={isLoading}
          >
            <option value="">-- 문제를 선택하세요 --</option>
            {problems.map(problem => (
              <option key={problem.problem_id} value={problem.problem_id}>
                {problem.problem_id} - {problem.title} (Lv.{problem.level})
              </option>
            ))}
          </select>

          <button
            className="validate-button"
            onClick={handleValidate}
            disabled={!selectedProblemId || isLoading}
          >
            {isLoading ? '검증 중...' : '검증 실행'}
          </button>
        </div>

        {selectedProblem && (
          <div className="problem-info">
            <div className="info-item">
              <span className="info-label">Solution Code:</span>
              <span className={`info-value ${selectedProblem.has_solution ? 'yes' : 'no'}`}>
                {selectedProblem.has_solution ? '있음' : '없음'}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">Examples:</span>
              <span className="info-value">{selectedProblem.examples_count}개</span>
            </div>
            <div className="info-item">
              <span className="info-label">Hidden Tests:</span>
              <span className="info-value">{selectedProblem.hidden_tests_count}개</span>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="error-message">
          <strong>오류:</strong> {error}
        </div>
      )}

      {validationResult && (
        <div className="validation-results">
          <div className="results-header">
            <h3>{validationResult.title} 검증 결과</h3>
            <div className="statistics">
              <span className="stat solutions">
                솔루션 수: {validationResult.solutions_count}개
              </span>
              <span className="stat total">
                총 테스트: {validationResult.overall_statistics.total_tests}
              </span>
              <span className="stat pass">
                통과: {validationResult.overall_statistics.passed_tests}
              </span>
              <span className="stat fail">
                실패: {validationResult.overall_statistics.failed_tests}
              </span>
              <span className="stat rate">
                성공률: {validationResult.overall_statistics.pass_rate}%
              </span>
            </div>
          </div>

          {validationResult.solution_results.map((solution, solIdx) => {
            const isSolutionExpanded = expandedSolutions.has(solIdx);
            return (
              <div key={`solution-${solIdx}`} className="solution-validation-block">
                <div
                  className="solution-header clickable"
                  onClick={() => toggleSolution(solIdx)}
                >
                  <div className="solution-header-left">
                    <span className="toggle-icon">{isSolutionExpanded ? '▼' : '▶'}</span>
                    <h3>{solution.solution_name}</h3>
                  </div>
                  <div className="solution-statistics">
                    <span className="stat total">
                      총 테스트: {solution.statistics.total_tests}
                    </span>
                    <span className="stat pass">
                      통과: {solution.statistics.passed_tests}
                    </span>
                    <span className="stat fail">
                      실패: {solution.statistics.failed_tests}
                    </span>
                    <span className="stat rate">
                      성공률: {solution.statistics.pass_rate}%
                    </span>
                  </div>
                </div>

                {isSolutionExpanded && (
                  <>
                    <div className="solution-code-section">
                      <h4>Solution Code</h4>
                      <pre className="solution-code">{solution.solution_code}</pre>
                    </div>

                    {solution.example_results.length > 0 && (
                      <div className="results-section">
                        <h4>예제 테스트 결과 ({solution.example_results.length}개)</h4>
                        <div className="test-results-container">
                          {solution.example_results.map((result, idx) =>
                            renderTestResult(result, `solution-${solIdx}-example-${idx}`)
                          )}
                        </div>
                      </div>
                    )}

                    {solution.hidden_results.length > 0 && (
                      <div className="results-section">
                        <h4>숨겨진 테스트 결과 ({solution.hidden_results.length}개)</h4>
                        <div className="test-results-container">
                          {solution.hidden_results.map((result, idx) =>
                            renderTestResult(result, `solution-${solIdx}-hidden-${idx}`)
                          )}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ProblemDataValidationTab;
