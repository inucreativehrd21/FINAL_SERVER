import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import api from '../../services/api'
import { loginSuccess } from '../../store/authSlice'
import './Login.css'

function Login() {
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await api.post('/auth/login/', {
        username: formData.username,
        password: formData.password,
      })

      const { user, tokens } = response.data.data

      // 토큰 저장
      localStorage.setItem('accessToken', tokens.access)
      localStorage.setItem('refreshToken', tokens.refresh)

      // Redux에 사용자 정보 저장
      dispatch(loginSuccess(user))

      // 메인으로 이동
      navigate('/')
    } catch (err) {
      console.error('Login error:', err)
      setError(
        err.response?.data?.message || '로그인에 실패했습니다.'
      )
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleKakaoLogin = () => {
    // 카카오 OAuth URL 생성
    const KAKAO_REST_API_KEY = 'f933dc8a2d5af1ac9a9258cb66196bdf'
    const REDIRECT_URI = 'http://3.37.186.224/auth/kakao/callback'

    const kakaoAuthUrl = `https://kauth.kakao.com/oauth/authorize?client_id=${KAKAO_REST_API_KEY}&redirect_uri=${REDIRECT_URI}&response_type=code`

    // 카카오 로그인 페이지로 리다이렉트
    window.location.href = kakaoAuthUrl
  }

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-logo" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>π</div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="error-message">{error}</div>}

          <div className="input-group">
            <span className="input-icon">👤</span>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              placeholder="ID"
              required
            />
          </div>

          <div className="input-group">
            <span className="input-icon">🔒</span>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Password"
              required
            />
          </div>

          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? '처리중...' : '로그인'}
          </button>

          <div className="divider">or</div>

          <button type="button" className="kakao-btn" onClick={handleKakaoLogin}>
            💬 카카오 로그인
          </button>
        </form>

        <div className="login-links">
          <button onClick={() => navigate('/signup')}>회원가입</button>
          <span>|</span>
          <button onClick={() => alert('아이디 찾기 기능은 추후 구현 예정입니다.')}>아이디 찾기</button>
          <span>|</span>
          <button onClick={() => alert('비밀번호 찾기 기능은 추후 구현 예정입니다.')}>비밀번호 찾기</button>
        </div>
      </div>
    </div>
  )
}

export default Login
