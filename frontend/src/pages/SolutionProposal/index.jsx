import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import api from '../../services/api';
import './SolutionProposal.css';

const SolutionProposal = () => {
  const navigate = useNavigate();
  const [problems, setProblems] = useState([]);
  const [selectedProblemId, setSelectedProblemId] = useState('');
  const [selectedProblem, setSelectedProblem] = useState(null);
  const [solutionCode, setSolutionCode] = useState('');
  const [language, setLanguage] = useState('python');
  const [description, setDescription] = useState('');
  const [isReference, setIsReference] = useState(true);
  const [testOutput, setTestOutput] = useState('');
  const [isTestingCode, setIsTestingCode] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    // Load problems
    fetch('/problems.json')
      .then(res => res.json())
      .then(data => setProblems(data))
      .catch(err => console.error('문제 로딩 실패:', err));
  }, []);

  useEffect(() => {
    if (selectedProblemId) {
      const problem = problems.find(p => p.problem_id === selectedProblemId);
      setSelectedProblem(problem);

      // Set default template code
      if (problem) {
        setSolutionCode(`# ${problem.title} 솔루션\n# 문제 ID: ${problem.problem_id}\n\ndef solution():\n    # 여기에 솔루션 코드를 작성하세요\n    pass\n\nif __name__ == "__main__":\n    solution()`);
      }
    }
  }, [selectedProblemId, problems]);

  const handleTestSolution = async () => {
    if (!solutionCode.trim()) {
      alert('솔루션 코드를 입력해주세요.');
      return;
    }

    if (!selectedProblemId) {
      alert('문제를 선택해주세요.');
      return;
    }

    setIsTestingCode(true);
    setTestOutput('');

    try {
      const response = await api.post('/api/coding-test/execute/', {
        problem_id: selectedProblemId,
        code: solutionCode,
        language: language,
      });

      if (response.data.success) {
        const results = response.data.data.results;
        let output = '=== 솔루션 테스트 결과 ===\n\n';

        results.forEach((result, idx) => {
          output += `[테스트 ${idx + 1}]\n`;
          output += `입력: ${result.input || '(없음)'}\n`;
          if (result.error) {
            output += `에러: ${result.error}\n\n`;
          } else {
            output += `출력: ${result.output || '(출력 없음)'}\n`;
            output += `예상: ${result.expected_output || '(없음)'}\n`;
            const actualOutput = result.output?.trim() || '';
            const expectedOutput = result.expected_output?.trim() || '';
            output += `결과: ${actualOutput === expectedOutput ? '✅ 통과' : '❌ 실패'}\n\n`;
          }
        });

        setTestOutput(output);
      } else {
        setTestOutput(`실행 실패:\n${response.data.error || '알 수 없는 오류'}`);
      }
    } catch (error) {
      setTestOutput(`에러 발생: ${error.response?.data?.error || error.message}`);
    } finally {
      setIsTestingCode(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedProblemId) {
      alert('문제를 선택해주세요.');
      return;
    }

    if (!solutionCode.trim()) {
      alert('솔루션 코드를 입력해주세요.');
      return;
    }

    if (window.confirm('이 솔루션을 제안하시겠습니까?')) {
      setIsSubmitting(true);

      try {
        const response = await api.post('/api/coding-test/solutions/propose/', {
          problem_id: selectedProblemId,
          solution_code: solutionCode,
          language: language,
          description: description,
          is_reference: isReference,
        });

        if (response.data.success) {
          alert('솔루션이 제안되었습니다! 관리자 승인을 기다려주세요.');
          navigate('/problems');
        } else {
          alert('솔루션 제안에 실패했습니다: ' + JSON.stringify(response.data.errors));
        }
      } catch (error) {
        alert('에러 발생: ' + (error.response?.data?.message || error.message));
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  return (
    <div className="solution-proposal-page">
      <button className="back-btn" onClick={() => navigate('/app/problems')}>← 돌아가기</button>
      <div className="proposal-header">
        <h1>솔루션 제안하기</h1>
        <p className="header-description">
          문제에 대한 참조 솔루션을 제안하세요. 관리자 승인 후 시스템에 추가됩니다.
        </p>
      </div>

      <div className="proposal-form">
        <div className="form-section">
          <label htmlFor="problem-select">문제 선택 *</label>
          <select
            id="problem-select"
            className="problem-select"
            value={selectedProblemId}
            onChange={(e) => setSelectedProblemId(e.target.value)}
          >
            <option value="">-- 문제를 선택하세요 --</option>
            {problems.map((problem) => (
              <option key={problem.problem_id} value={problem.problem_id}>
                [{problem.problem_id}] {problem.title} (레벨 {problem.level})
              </option>
            ))}
          </select>
        </div>

        {selectedProblem && (
          <div className="problem-info">
            <h3>{selectedProblem.title}</h3>
            <p className="problem-description">{selectedProblem.description}</p>
            <div className="problem-io">
              <div>
                <strong>입력:</strong>
                <p>{selectedProblem.input_description}</p>
              </div>
              <div>
                <strong>출력:</strong>
                <p>{selectedProblem.output_description}</p>
              </div>
            </div>
          </div>
        )}

        <div className="form-section">
          <label htmlFor="language-select">프로그래밍 언어 *</label>
          <select
            id="language-select"
            className="language-select"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="java">Java</option>
            <option value="cpp">C++</option>
          </select>
        </div>

        <div className="form-section">
          <label>솔루션 코드 *</label>
          <p className="section-hint">문제를 해결하는 솔루션 코드를 작성하고, 아래 버튼으로 테스트하세요.</p>
          <div className="editor-wrapper">
            <Editor
              height="500px"
              language={language === 'cpp' ? 'cpp' : language}
              value={solutionCode}
              onChange={(value) => setSolutionCode(value || '')}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
              }}
            />
          </div>
          <button
            className="sp-test-btn"
            onClick={handleTestSolution}
            disabled={isTestingCode || !solutionCode.trim()}
          >
            {isTestingCode ? '테스트 중...' : '솔루션 실행 및 테스트'}
          </button>

          {testOutput && (
            <div className="test-result">
              <div className="test-result-header">실행 결과</div>
              <pre className="test-result-content">{testOutput}</pre>
            </div>
          )}
        </div>

        <div className="form-section">
          <label htmlFor="description">설명 (선택)</label>
          <p className="section-hint">이 솔루션의 접근 방법이나 알고리즘에 대해 설명해주세요.</p>
          <textarea
            id="description"
            className="description-input"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="예: 동적 프로그래밍을 사용한 최적화된 솔루션입니다..."
            rows={4}
          />
        </div>

        <div className="form-section">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={isReference}
              onChange={(e) => setIsReference(e.target.checked)}
            />
            <span>참조 솔루션으로 추가 (승인 시 문제 JSON에 포함)</span>
          </label>
        </div>

        <div className="form-actions">
          <button
            className="sp-cancel-btn"
            onClick={() => navigate('/problems')}
          >
            취소
          </button>
          <button
            className="sp-submit-btn"
            onClick={handleSubmit}
            disabled={isSubmitting || !selectedProblemId || !solutionCode.trim()}
          >
            {isSubmitting ? '제안 중...' : '솔루션 제안하기'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SolutionProposal;
