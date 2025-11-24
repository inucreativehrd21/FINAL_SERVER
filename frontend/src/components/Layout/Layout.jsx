/**
 * 메인 레이아웃 컴포넌트
 */
import React from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { logout } from '@store/authSlice'
import './Layout.css'

const Layout = () => {
  const { user } = useSelector((state) => state.auth)
  const dispatch = useDispatch()
  const navigate = useNavigate()

  const handleLogout = () => {
    dispatch(logout())
    navigate('/')
  }

  const handleLogoClick = () => {
    navigate('/')
  }

  return (
    <div className="layout">
      <nav className="top-navbar">
        <div className="nav-left">
          <div className="navbar-brand" onClick={handleLogoClick}>
            <span className="logo-symbol">π</span>
          </div>
          <NavLink to="/app/problems" className="nav-link">
            문제 선택
          </NavLink>
          <NavLink to="/app/chatbot" className="nav-link">
            문답 챗봇
          </NavLink>
        </div>

        <div className="nav-right">
          <NavLink to="/app/mypage" className="nav-link">
            마이페이지
          </NavLink>
          {(user?.is_staff || user?.is_superuser) && (
            <NavLink to="/app/admin" className="nav-link admin">
              관리자
            </NavLink>
          )}
          <button onClick={handleLogout} className="logout-btn">
            로그아웃
          </button>
        </div>
      </nav>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}

export default Layout
