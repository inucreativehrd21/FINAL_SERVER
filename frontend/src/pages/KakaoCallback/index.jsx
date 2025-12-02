import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import api from '../../services/api'
import { loginSuccess } from '../../store/authSlice'
import './KakaoCallback.css'

function KakaoCallback() {
  const navigate = useNavigate()
  const location = useLocation()
  const dispatch = useDispatch()
  const [error, setError] = useState('')

  useEffect(() => {
    const handleKakaoCallback = async () => {
      // URL에서 인가 코드 추출
      const params = new URLSearchParams(location.search)
      const code = params.get('code')
      const errorParam = params.get('error')

      if (errorParam) {
        setError('카카오 로그인이 취소되었습니다.')
        setTimeout(() => navigate('/login'), 2000)
        return
      }

      if (!code) {
        setError('인가 코드를 받지 못했습니다.')
        setTimeout(() => navigate('/login'), 2000)
        return
      }

      try {
        // 백엔드에 인가 코드 전송
        const response = await api.post('/auth/kakao/login/', { code })

        const { user, tokens } = response.data.data

        // 토큰 저장
        localStorage.setItem('accessToken', tokens.access)
        localStorage.setItem('refreshToken', tokens.refresh)

        // Redux에 사용자 정보 저장
        dispatch(loginSuccess(user))

        // 메인으로 이동
        navigate('/')
      } catch (err) {
        console.error('Kakao login error:', err)
        setError(
          err.response?.data?.message || '카카오 로그인에 실패했습니다.'
        )
        setTimeout(() => navigate('/login'), 2000)
      }
    }

    handleKakaoCallback()
  }, [location, navigate, dispatch])

  return (
    <div className="kakao-callback-page">
      <div className="kakao-callback-container">
        {error ? (
          <div className="error-box">
            <div className="error-icon">⚠️</div>
            <h2>로그인 실패</h2>
            <p>{error}</p>
            <p className="redirect-text">로그인 페이지로 이동합니다...</p>
          </div>
        ) : (
          <div className="loading-box">
            <div className="spinner"></div>
            <h2>카카오 로그인 중...</h2>
            <p>잠시만 기다려 주세요.</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default KakaoCallback
