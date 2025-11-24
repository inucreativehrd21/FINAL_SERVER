import React, { useState } from 'react'
import Editor from '@monaco-editor/react'
import '../../AdminPanelTestcases.css'
import './SolutionsTab.css'

function SolutionsTab({
  solutionProposals,
  selectedSolution,
  setSelectedSolution,
  testCode,
  setTestCode,
  testOutput,
  testLoading,
  reviewComment,
  setReviewComment,
  handleSelectSolution,
  handleTestSolution,
  handleApproveSolution,
  handleRejectSolution
}) {
  const [activeFilter, setActiveFilter] = useState('pending')

  const filteredProposals = solutionProposals.filter(p => p.status === activeFilter)

  const getFilterLabel = (status) => {
    switch(status) {
      case 'pending': return '승인 대기'
      case 'approved': return '승인됨'
      case 'rejected': return '거부됨'
      default: return status
    }
  }

  return (
    <div className="testcases-section">
      <div className="section-header">
        <h3>솔루션 제안 목록</h3>
        <div className="filter-tabs">
          <button
            className={`filter-btn ${activeFilter === 'pending' ? 'active' : ''}`}
            onClick={() => setActiveFilter('pending')}
          >
            승인 대기 ({solutionProposals.filter(p => p.status === 'pending').length})
          </button>
          <button
            className={`filter-btn ${activeFilter === 'approved' ? 'active' : ''}`}
            onClick={() => setActiveFilter('approved')}
          >
            승인됨 ({solutionProposals.filter(p => p.status === 'approved').length})
          </button>
          <button
            className={`filter-btn ${activeFilter === 'rejected' ? 'active' : ''}`}
            onClick={() => setActiveFilter('rejected')}
          >
            거부됨 ({solutionProposals.filter(p => p.status === 'rejected').length})
          </button>
        </div>
      </div>

      <div className="testcases-layout">
        <div className="proposals-list">
          {filteredProposals.length === 0 ? (
            <div className="empty-state">
              <p>{getFilterLabel(activeFilter)} 중인 제안이 없습니다.</p>
            </div>
          ) : (
            filteredProposals.map((solution) => (
              <div
                key={solution.id}
                className={`proposal-item ${selectedSolution?.id === solution.id ? 'selected' : ''}`}
                onClick={() => handleSelectSolution(solution)}
              >
                <div className="proposal-header">
                  <span className="proposal-problem">#{solution.problem_id}</span>
                  <span className={`proposal-status ${solution.status}`}>
                    {solution.status_display}
                  </span>
                </div>
                <div className="proposal-meta">
                  <span>제안자: {solution.proposed_by_username}</span>
                  <span>{new Date(solution.created_at).toLocaleDateString()}</span>
                </div>
                {solution.description && (
                  <div className="proposal-description">
                    {solution.description.length > 80
                      ? solution.description.substring(0, 80) + '...'
                      : solution.description}
                  </div>
                )}
                <div className="proposal-meta">
                  <span>언어: {solution.language}</span>
                  {solution.is_reference && <span>참조 솔루션</span>}
                </div>
              </div>
            ))
          )}
        </div>

        {selectedSolution && (
          <div className="proposal-detail">
            <div className="detail-header">
              <h3>솔루션 상세</h3>
              <button
                className="close-detail-btn"
                onClick={() => setSelectedSolution(null)}
              >
                ×
              </button>
            </div>

            <div className="detail-content">
              <div className="detail-section">
                <h4>문제 정보</h4>
                <p>문제 ID: #{selectedSolution.problem_id}</p>
                <p>제안자: {selectedSolution.proposed_by_username}</p>
                <p>제안일: {new Date(selectedSolution.created_at).toLocaleString()}</p>
                <p>언어: {selectedSolution.language}</p>
                <p>참조 솔루션: {selectedSolution.is_reference ? '예' : '아니오'}</p>
              </div>

              {selectedSolution.description && (
                <div className="detail-section">
                  <h4>설명</h4>
                  <p>{selectedSolution.description}</p>
                </div>
              )}

              <div className="detail-section">
                <h4>솔루션 코드</h4>
                <p className="section-hint">제안된 솔루션을 검토하고 테스트하세요.</p>
                <div className="test-editor">
                  <Editor
                    height="400px"
                    defaultLanguage={selectedSolution.language === 'cpp' ? 'cpp' : selectedSolution.language}
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
                  className="sol-test-btn"
                  onClick={handleTestSolution}
                  disabled={testLoading}
                >
                  {testLoading ? '실행 중...' : '솔루션 실행'}
                </button>

                {testOutput && (
                  <div className="test-result">
                    <div className="test-result-header">실행 결과</div>
                    <pre className="test-result-content">{testOutput}</pre>
                  </div>
                )}
              </div>

              <div className="detail-section">
                <h4>검토 의견</h4>
                <textarea
                  className="review-comment-input"
                  placeholder="승인 또는 거부 사유를 입력하세요."
                  value={reviewComment}
                  onChange={(e) => setReviewComment(e.target.value)}
                  rows="4"
                />
              </div>

              <div className="detail-actions">
                <button
                  className="sol-reject-btn"
                  onClick={handleRejectSolution}
                >
                  거부
                </button>
                <button
                  className="sol-approve-btn"
                  onClick={handleApproveSolution}
                >
                  승인
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default SolutionsTab
