import React, { useState } from 'react'
import Editor from '@monaco-editor/react'
import '../../AdminPanelTestcases.css'
import './ProblemsTab.css'

function ProblemsTab({
  problemProposals,
  selectedProposal,
  setSelectedProposal,
  testCode,
  setTestCode,
  testOutput,
  testLoading,
  reviewComment,
  setReviewComment,
  handleSelectProposal,
  handleTestProposal,
  handleApproveProposal,
  handleRejectProposal
}) {
  const [activeFilter, setActiveFilter] = useState('pending')

  const filteredProposals = problemProposals.filter(p => p.status === activeFilter)

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
        <h3>문제 제안 목록</h3>
        <div className="filter-tabs">
          <button
            className={`filter-btn ${activeFilter === 'pending' ? 'active' : ''}`}
            onClick={() => setActiveFilter('pending')}
          >
            승인 대기 ({problemProposals.filter(p => p.status === 'pending').length})
          </button>
          <button
            className={`filter-btn ${activeFilter === 'approved' ? 'active' : ''}`}
            onClick={() => setActiveFilter('approved')}
          >
            승인됨 ({problemProposals.filter(p => p.status === 'approved').length})
          </button>
          <button
            className={`filter-btn ${activeFilter === 'rejected' ? 'active' : ''}`}
            onClick={() => setActiveFilter('rejected')}
          >
            거부됨 ({problemProposals.filter(p => p.status === 'rejected').length})
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
            filteredProposals.map((proposal) => (
              <div
                key={proposal.id}
                className={`proposal-item ${selectedProposal?.id === proposal.id ? 'selected' : ''}`}
                onClick={() => handleSelectProposal(proposal)}
              >
                <div className="proposal-header">
                  <span className="proposal-problem">{proposal.title}</span>
                  <span className={`proposal-status ${proposal.status}`}>
                    {proposal.status_display}
                  </span>
                </div>
                <div className="proposal-meta">
                  <span>제안자: {proposal.proposed_by_username}</span>
                  <span>{new Date(proposal.created_at).toLocaleDateString()}</span>
                </div>
                <div className="proposal-meta">
                  <span>난이도: 레벨 {proposal.level}</span>
                  <span>언어: {proposal.language}</span>
                </div>
                {proposal.description && (
                  <div className="proposal-description">
                    {proposal.description.length > 80
                      ? proposal.description.substring(0, 80) + '...'
                      : proposal.description}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {selectedProposal && (
          <div className="proposal-detail">
            <div className="detail-header">
              <h3>문제 제안 상세 정보</h3>
              <button
                className="close-detail-btn"
                onClick={() => setSelectedProposal(null)}
              >
                ✕
              </button>
            </div>

            <div className="detail-content">
              <div className="detail-section">
                <h4>기본 정보</h4>
                <p>문제 ID: {selectedProposal.problem_id}</p>
                <p>제목: {selectedProposal.title}</p>
                {selectedProposal.step_title && <p>단계 제목: {selectedProposal.step_title}</p>}
                <p>난이도: 레벨 {selectedProposal.level}</p>
                <p>언어: {selectedProposal.language}</p>
                <p>제안자: {selectedProposal.proposed_by_username}</p>
                <p>제안일: {new Date(selectedProposal.created_at).toLocaleString()}</p>
                {selectedProposal.tags && selectedProposal.tags.length > 0 && (
                  <p>태그: {selectedProposal.tags.join(', ')}</p>
                )}
              </div>

              <div className="detail-section">
                <h4>문제 설명</h4>
                <pre className="code-block" style={{whiteSpace: 'pre-wrap', background: '#f5f5f5', color: '#333'}}>
                  {selectedProposal.description}
                </pre>
              </div>

              {selectedProposal.input_description && (
                <div className="detail-section">
                  <h4>입력 설명</h4>
                  <pre className="code-block" style={{whiteSpace: 'pre-wrap', background: '#f5f5f5', color: '#333'}}>
                    {selectedProposal.input_description}
                  </pre>
                </div>
              )}

              {selectedProposal.output_description && (
                <div className="detail-section">
                  <h4>출력 설명</h4>
                  <pre className="code-block" style={{whiteSpace: 'pre-wrap', background: '#f5f5f5', color: '#333'}}>
                    {selectedProposal.output_description}
                  </pre>
                </div>
              )}

              {selectedProposal.test_cases && selectedProposal.test_cases.length > 0 && (
                <div className="detail-section">
                  <h4>테스트 케이스</h4>
                  {selectedProposal.test_cases.map((tc, idx) => (
                    <div key={idx} style={{marginBottom: '1rem'}}>
                      <p style={{fontWeight: 600, color: '#667eea'}}>테스트 케이스 {idx + 1}</p>
                      <p style={{fontSize: '0.9rem', color: '#666'}}>입력:</p>
                      <pre className="code-block" style={{marginBottom: '0.5rem'}}>{tc.input}</pre>
                      <p style={{fontSize: '0.9rem', color: '#666'}}>예상 출력:</p>
                      <pre className="code-block">{tc.output}</pre>
                    </div>
                  ))}
                </div>
              )}

              <div className="detail-section">
                <h4>참조 솔루션 코드</h4>
                <p className="section-hint">제안된 문제의 참조 솔루션을 검토하고 테스트하세요.</p>
                <div className="test-editor">
                  <Editor
                    height="400px"
                    defaultLanguage={selectedProposal.language === 'cpp' ? 'cpp' : selectedProposal.language}
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
                  className="tc-test-btn"
                  onClick={handleTestProposal}
                  disabled={testLoading}
                >
                  {testLoading ? '실행 중...' : '▶ 테스트 실행'}
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
                  placeholder="승인 또는 거부 사유를 입력하세요"
                  value={reviewComment}
                  onChange={(e) => setReviewComment(e.target.value)}
                  rows="4"
                />
              </div>

              <div className="detail-actions">
                <button
                  className="tc-reject-btn"
                  onClick={handleRejectProposal}
                >
                  거부
                </button>
                <button
                  className="tc-approve-btn"
                  onClick={handleApproveProposal}
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

export default ProblemsTab
