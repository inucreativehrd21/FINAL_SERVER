import React from 'react'
import Editor from '@monaco-editor/react'
import './TestCasesTab.css'

function TestCasesTab({
  testCaseProposals,
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
  return (
    <div className="testcases-section">
      <div className="section-header">
        <h3>테스트 케이스 제안 목록</h3>
        <div className="filter-tabs">
          <button className="filter-btn active">
            승인 대기 ({testCaseProposals.filter(p => p.status === 'pending').length})
          </button>
          <button className="filter-btn">
            승인됨 ({testCaseProposals.filter(p => p.status === 'approved').length})
          </button>
          <button className="filter-btn">
            거부됨 ({testCaseProposals.filter(p => p.status === 'rejected').length})
          </button>
        </div>
      </div>

      <div className="testcases-layout">
        <div className="proposals-list">
          {testCaseProposals.filter(p => p.status === 'pending').length === 0 ? (
            <div className="empty-state">
              <p>승인 대기 중인 제안이 없습니다.</p>
            </div>
          ) : (
            testCaseProposals
              .filter(p => p.status === 'pending')
              .map((proposal) => (
                <div
                  key={proposal.id}
                  className={`proposal-item ${selectedProposal?.id === proposal.id ? 'selected' : ''}`}
                  onClick={() => handleSelectProposal(proposal)}
                >
                  <div className="proposal-header">
                    <span className="proposal-problem">문제 #{proposal.problem_id}</span>
                    <span className={`proposal-status ${proposal.status}`}>
                      {proposal.status_display}
                    </span>
                  </div>
                  <div className="proposal-meta">
                    <span>제안자: {proposal.proposed_by_username}</span>
                    <span>{new Date(proposal.created_at).toLocaleDateString()}</span>
                  </div>
                  {proposal.description && (
                    <div className="proposal-description">{proposal.description}</div>
                  )}
                </div>
              ))
          )}
        </div>

        {selectedProposal && (
          <div className="proposal-detail">
            <div className="detail-header">
              <h3>제안 상세 정보</h3>
              <button
                className="close-detail-btn"
                onClick={() => setSelectedProposal(null)}
              >
                ✕
              </button>
            </div>

            <div className="detail-content">
              <div className="detail-section">
                <h4>문제 정보</h4>
                <p>문제 ID: #{selectedProposal.problem_id}</p>
                <p>제안자: {selectedProposal.proposed_by_username}</p>
                <p>제안일: {new Date(selectedProposal.created_at).toLocaleString()}</p>
              </div>

              {selectedProposal.description && (
                <div className="detail-section">
                  <h4>설명</h4>
                  <p>{selectedProposal.description}</p>
                </div>
              )}

              <div className="detail-section">
                <h4>입력 데이터</h4>
                <pre className="code-block">{selectedProposal.input_data}</pre>
              </div>

              <div className="detail-section">
                <h4>예상 출력</h4>
                <pre className="code-block">{selectedProposal.expected_output}</pre>
              </div>

              <div className="detail-section">
                <h4>테스트 코드 작성</h4>
                <p className="section-hint">제안된 테스트 케이스를 검증하기 위해 코드를 작성하고 실행하세요.</p>
                <div className="test-editor">
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

export default TestCasesTab
