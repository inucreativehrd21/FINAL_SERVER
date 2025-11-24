import React from 'react'
import './UsersTab.css'

function UsersTab({ users, currentUserId, handleToggleUserStatus, handleToggleUserRole, handleDeleteUser }) {
  return (
    <div className="users-section">
      <div className="section-header">
        <h3>사용자 목록 ({users.length}명)</h3>
        <p className="section-hint">사용자 계정을 활성화/비활성화하거나 삭제할 수 있습니다. 관리자 권한을 부여/제거할 수 있습니다.</p>
      </div>

      <div className="users-table">
        <table>
          <thead>
            <tr>
              <th>사용자명</th>
              <th>이메일</th>
              <th>레이팅</th>
              <th>권한</th>
              <th>상태</th>
              <th>관리</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 ? (
              <tr>
                <td colSpan="6" className="empty-cell">
                  등록된 사용자가 없습니다.
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id}>
                  <td>{user.username}</td>
                  <td>{user.email || '-'}</td>
                  <td>{user.rating || 0}</td>

                  {/* 권한 */}
                  <td>
                    <span className={`role-badge ${user.is_staff ? 'admin' : 'user'}`}>
                      {user.is_staff ? '관리자' : '일반'}
                    </span>
                  </td>

                  {/* 활성 상태 */}
                  <td>
                    <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                      {user.is_active ? '활성' : '비활성'}
                    </span>
                  </td>

                  {/* 관리 버튼 */}
                  <td>
                    <div className="table-actions">
                      <button
                        className="action-btn toggle"
                        onClick={() => handleToggleUserStatus(user.id, user.is_active)}
                      >
                        {user.is_active ? '비활성화' : '활성화'}
                      </button>
                      <button
                        className={`action-btn role ${user.id === currentUserId ? 'disabled' : ''}`}
                        onClick={() => handleToggleUserRole(user.id, user.is_staff)}
                        disabled={user.id === currentUserId}
                        title={user.id === currentUserId ? '자신의 권한은 변경할 수 없습니다' : ''}
                      >
                        {user.is_staff ? '권한 제거' : '관리자 부여'}
                      </button>
                      <button
                        className="action-btn delete"
                        onClick={() => handleDeleteUser(user.id)}
                      >
                        삭제
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

    </div>
  )
}

export default UsersTab
