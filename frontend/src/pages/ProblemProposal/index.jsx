import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import api from '../../services/api';
import './ProblemProposal.css';

const ProblemProposal = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    problem_id: '',
    title: '',
    step_title: '',
    description: '',
    input_description: '',
    output_description: '',
    level: 1,
    tags: [],
    solution_code: '',
    language: 'python',
    test_cases: [
      { input_data: '', expected_output: '', is_example: true }
    ]
  });
  const [tagInput, setTagInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 난이도 레벨 이름 매핑 (1~26)
  const getLevelName = (level) => {
    const levels = {
      1: 'Bronze 5', 2: 'Bronze 4', 3: 'Bronze 3', 4: 'Bronze 2', 5: 'Bronze 1',
      6: 'Silver 5', 7: 'Silver 4', 8: 'Silver 3', 9: 'Silver 2', 10: 'Silver 1',
      11: 'Gold 5', 12: 'Gold 4', 13: 'Gold 3', 14: 'Gold 2', 15: 'Gold 1',
      16: 'Platinum 5', 17: 'Platinum 4', 18: 'Platinum 3', 19: 'Platinum 2', 20: 'Platinum 1',
      21: 'Diamond 5', 22: 'Diamond 4', 23: 'Diamond 3', 24: 'Diamond 2', 25: 'Diamond 1',
      26: 'Ruby 1'
    };
    return levels[level] || `Level ${level}`;
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !formData.tags.includes(tagInput.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, tagInput.trim()]
      }));
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(tag => tag !== tagToRemove)
    }));
  };

  const handleAddTestCase = () => {
    setFormData(prev => ({
      ...prev,
      test_cases: [...prev.test_cases, { input_data: '', expected_output: '', is_example: false }]
    }));
  };

  const handleRemoveTestCase = (index) => {
    if (formData.test_cases.length > 1) {
      setFormData(prev => ({
        ...prev,
        test_cases: prev.test_cases.filter((_, i) => i !== index)
      }));
    }
  };

  const handleTestCaseChange = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      test_cases: prev.test_cases.map((tc, i) =>
        i === index ? { ...tc, [field]: value } : tc
      )
    }));
  };

  const handleSubmit = async () => {
    // Validation
    if (!formData.problem_id.trim()) {
      alert('문제 ID를 입력해주세요.');
      return;
    }
    if (!formData.title.trim()) {
      alert('문제 제목을 입력해주세요.');
      return;
    }
    if (!formData.description.trim()) {
      alert('문제 설명을 입력해주세요.');
      return;
    }
    if (!formData.solution_code.trim()) {
      alert('참조 솔루션 코드를 입력해주세요.');
      return;
    }
    if (formData.test_cases.some(tc => !tc.input_data.trim() || !tc.expected_output.trim())) {
      alert('모든 테스트 케이스의 입력과 출력을 입력해주세요.');
      return;
    }

    if (!window.confirm('이 문제를 제안하시겠습니까?')) {
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await api.post('/coding-test/problems/propose/', formData);

      if (response.data.success) {
        alert('문제가 제안되었습니다! 관리자 승인을 기다려주세요.');
        navigate('/app/problems');
      } else {
        alert('문제 제안에 실패했습니다: ' + JSON.stringify(response.data.errors));
      }
    } catch (error) {
      alert('에러 발생: ' + (error.response?.data?.message || error.message));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="problem-proposal-page">
      <button className="back-btn" onClick={() => navigate('/app/problems')}>← 돌아가기</button>
      <div className="proposal-header">
        <h1>문제 제안하기</h1>
        <p className="header-description">
          새로운 코딩 테스트 문제를 제안하세요. 관리자 승인 후 시스템에 추가됩니다.
        </p>
      </div>

      <div className="proposal-form">
        <div className="form-row">
          <div className="form-section half">
            <label htmlFor="problem-id">문제 ID *</label>
            <input
              id="problem-id"
              type="text"
              className="text-input"
              value={formData.problem_id}
              onChange={(e) => handleChange('problem_id', e.target.value)}
              placeholder="예: PROB001"
            />
          </div>

          <div className="form-section half">
            <label htmlFor="level">난이도 *</label>
            <select
              id="level"
              className="select-input"
              value={formData.level}
              onChange={(e) => handleChange('level', parseInt(e.target.value))}
            >
              {[...Array(26)].map((_, i) => (
                <option key={i + 1} value={i + 1}>
                  {getLevelName(i + 1)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-section">
          <label htmlFor="title">문제 제목 *</label>
          <input
            id="title"
            type="text"
            className="text-input"
            value={formData.title}
            onChange={(e) => handleChange('title', e.target.value)}
            placeholder="예: 두 수의 합"
          />
        </div>

        <div className="form-section">
          <label htmlFor="step-title">단계 제목 (선택)</label>
          <input
            id="step-title"
            type="text"
            className="text-input"
            value={formData.step_title}
            onChange={(e) => handleChange('step_title', e.target.value)}
            placeholder="예: 기초 문제 풀기"
          />
        </div>

        <div className="form-section">
          <label htmlFor="description">문제 설명 *</label>
          <textarea
            id="description"
            className="textarea-input"
            value={formData.description}
            onChange={(e) => handleChange('description', e.target.value)}
            placeholder="문제에 대한 상세한 설명을 입력하세요..."
            rows={6}
          />
        </div>

        <div className="form-section">
          <label htmlFor="input-desc">입력 설명 *</label>
          <textarea
            id="input-desc"
            className="textarea-input"
            value={formData.input_description}
            onChange={(e) => handleChange('input_description', e.target.value)}
            placeholder="입력 형식에 대한 설명..."
            rows={3}
          />
        </div>

        <div className="form-section">
          <label htmlFor="output-desc">출력 설명 *</label>
          <textarea
            id="output-desc"
            className="textarea-input"
            value={formData.output_description}
            onChange={(e) => handleChange('output_description', e.target.value)}
            placeholder="출력 형식에 대한 설명..."
            rows={3}
          />
        </div>

        <div className="form-section">
          <label>태그</label>
          <div className="tags-input-container">
            <div className="tags-list">
              {formData.tags.map((tag, idx) => (
                <span key={idx} className="tag-item">
                  {tag}
                  <button
                    type="button"
                    className="tag-remove"
                    onClick={() => handleRemoveTag(tag)}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            <div className="tag-input-row">
              <input
                type="text"
                className="text-input"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                placeholder="태그 입력 후 Enter 또는 추가 버튼 클릭"
              />
              <button type="button" className="add-tag-btn" onClick={handleAddTag}>
                추가
              </button>
            </div>
          </div>
        </div>

        <div className="form-section">
          <label htmlFor="language">프로그래밍 언어 *</label>
          <select
            id="language"
            className="select-input"
            value={formData.language}
            onChange={(e) => handleChange('language', e.target.value)}
          >
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="java">Java</option>
            <option value="cpp">C++</option>
          </select>
        </div>

        <div className="form-section">
          <label>참조 솔루션 코드 *</label>
          <p className="section-hint">이 문제의 정답 코드를 작성해주세요.</p>
          <div className="editor-wrapper">
            <Editor
              height="400px"
              language={formData.language === 'cpp' ? 'cpp' : formData.language}
              value={formData.solution_code}
              onChange={(value) => handleChange('solution_code', value || '')}
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
        </div>

        <div className="form-section">
          <div className="section-header">
            <label>테스트 케이스 *</label>
            <button type="button" className="add-testcase-btn" onClick={handleAddTestCase}>
              + 테스트 케이스 추가
            </button>
          </div>

          {formData.test_cases.map((testCase, index) => (
            <div key={index} className="test-case-item">
              <div className="test-case-header">
                <h4>테스트 케이스 {index + 1}</h4>
                <div className="test-case-controls">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={testCase.is_example}
                      onChange={(e) => handleTestCaseChange(index, 'is_example', e.target.checked)}
                    />
                    <span>예제로 표시</span>
                  </label>
                  {formData.test_cases.length > 1 && (
                    <button
                      type="button"
                      className="remove-testcase-btn"
                      onClick={() => handleRemoveTestCase(index)}
                    >
                      삭제
                    </button>
                  )}
                </div>
              </div>

              <div className="test-case-fields">
                <div className="field-group">
                  <label>입력 데이터</label>
                  <textarea
                    className="textarea-input"
                    value={testCase.input_data}
                    onChange={(e) => handleTestCaseChange(index, 'input_data', e.target.value)}
                    placeholder="예: 1 2"
                    rows={3}
                  />
                </div>

                <div className="field-group">
                  <label>예상 출력</label>
                  <textarea
                    className="textarea-input"
                    value={testCase.expected_output}
                    onChange={(e) => handleTestCaseChange(index, 'expected_output', e.target.value)}
                    placeholder="예: 3"
                    rows={3}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="form-actions">
          <button
            className="pp-cancel-btn"
            onClick={() => navigate('/app/problems')}
          >
            취소
          </button>
          <button
            className="pp-submit-btn"
            onClick={handleSubmit}
            disabled={isSubmitting}
          >
            {isSubmitting ? '제안 중...' : '문제 제안하기'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProblemProposal;
